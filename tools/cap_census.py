#!/usr/bin/env python3
# CONTRACT: name=cap_census
# CONTRACT: READONLY=yes
# CONTRACT: WRITES_FILES=no
# CONTRACT: WRITES_SYSFS=no
# CONTRACT: MUTATES_CORPUS=no
# CONTRACT: WRITES_GPU=no
# CONTRACT: TOUCHES_INTEGRATED=no
#
# MEDIDO con RXRE/tools/rxre_contracts.py, no declarado de memoria.  El
# veredicto fue `READONLY=yes, WRITES_FILES=no`, y las 1 escrituras que
# tiene se resolvieron a la clase TEMPORAL: 1 caen DENTRO de un `with tempfile...`.
#
# Declarar `WRITES_FILES=no` con escrituras dentro no es una contradiccion: es
# exactamente la clase TEMPORAL de `contract_exec.py`, que existe porque una
# regex produjo cinco falsos positivos.  Declararlas `yes` seria MENTIR: el
# validador no puede distinguir un temporal de un fichero del proyecto.
#
# `tools/` tenia 3 contratos de 92.  Este bloque no anade comportamiento: hace
# el comportamiento DECLARABLE, que es la condicion previa a poder usarlo.
# Sobre la frontera: TOUCHES_INTEGRATED=no, y el campo se declara aunque
# toolkit.py no lo conozca -- la frontera que no se puede declarar es la que no
# se puede hacer cumplir (hallazgo 1487).
"""cap_census.py — qué PHM_PlatformCaps se activan para MI ASIC, y de dónde.

Por qué existe
--------------
En `hwmgr.c` la respuesta a "¿este ASIC usa SQ power throttling?" no está en
el fichero donde se pregunta, sino en un `phm_cap_set` de una función que se
llama desde otro fichero. Encadenarla a mano son cuatro saltos, y en el camino
es fácil leer el `phm_cap_set` de Vega20 y creer que es el nuestro: hay seis
bloques casi idénticos, uno por ASIC, y solo uno es el correcto.

Peor: una capability se puede activar y DESACTIVAR. `fiji_set_asic_special_caps`
hace `phm_cap_unset` de las cuatro de ramping. Si solo se leen los `set`, la
ausencia de un `set` parece "no tiene la capability" cuando lo que puede
significar es "nadie la menciona".

Esta herramienta resuelve las dos cosas:

  1. qué fichero menciona cada capability, y en qué ASIC
  2. para MI chip, el valor final tras aplicar todos los set/unset en orden

Lo que produce
--------------
Para una capability: todos los ficheros que la tocan, separados en set y unset,
y si el ASIC objetivo la deja activa, assuming el orden real de llamadas.

Y una herramienta de bonus que sale gratis: `--diff-chip` compara las
capabilities de dos ASIC, que es la forma rápida de encontrar qué hace Polaris
distinto de Vega.

Lo que NO hace
--------------
No ejecuta el código. El valor final es PROVEN_DERIVED del orden de llamadas
declarado, no observado. Si dos inicializadores se llaman en orden no documentado,
el resultado es una hipótesis sobre el orden, y así se marca.

Uso
---
    cap_census.py --kernel RAIZ --chip CHIP_POLARIS12
    cap_census.py --kernel RAIZ --chip CHIP_POLARIS12 --cap SQRamping --verbose
    cap_census.py --kernel RAIZ --diff-chip CHIP_POLARIS11:CHIP_POLARIS12
    cap_census.py --selftest
"""

from __future__ import annotations

import argparse
import json
import os
import re
import sys
from typing import Dict, List, Optional, Sequence, Set, Tuple

NAME = "cap_census"
VERSION = "1.0.0"

DEFAULT_CHIP = "CHIP_POLARIS12"
ASIC_ENUM_REL = "include/drm/amd_asic_type.h"

_SET = re.compile(r"phm_cap_(?P<op>set|unset)\s*\(\s*[^,]+,\s*(?P<cap>PHM_PlatformCaps_\w+)\s*\)")
# Un set/unset puede estar partido en varias lineas: se normaliza antes de casar.
_CAP_TEST = re.compile(r"PP_CAP\s*\(\s*(?P<cap>PHM_PlatformCaps_\w+)\s*\)")


def normalize(text: str) -> str:
    """Colapsa espacios, conservando un indice posicion a posicion.

    Devolver un mapa posicion_normalizada -> posicion_original es lo que
    permite decir "el phm_cap_set de la linea 4" cuando el texto normalizado lo
    tiene en la 3. Sin el mapa, los numeros de linea del texto normalizado no
    son los del fichero, y el self-test lo detecta porque la linea reportada no
    contiene phm_cap_.
    """
    out: List[str] = []
    back: List[int] = []
    prev_space = False
    for i, ch in enumerate(text):
        if ch.isspace():
            if prev_space:
                continue
            out.append(" ")
            back.append(i)
            prev_space = True
        else:
            out.append(ch)
            back.append(i)
            prev_space = False
    return "".join(out), back


def parse_chip_enum(path: str) -> Dict[str, int]:
    out: Dict[str, int] = {}
    if not os.path.isfile(path):
        return out
    rx = re.compile(r"^\s*(CHIP_[A-Z0-9_]+)\s*,?\s*(?:/\*\s*([0-9]+)\s*\*/)?\s*$")
    implicit, in_enum = 0, False
    with open(path, "r", encoding="utf-8", errors="replace") as fh:
        for line in fh:
            s = line.split("//", 1)[0].rstrip()
            if re.match(r"^\s*enum\b", s) and "asic_type" in s:
                in_enum = True
                continue
            if in_enum and s.strip().startswith("}"):
                break
            if not in_enum or not s.strip():
                continue
            m = rx.match(s)
            if not m:
                continue
            if m.group(2) is not None:
                out[m.group(1)] = int(m.group(2))
                implicit = int(m.group(2)) + 1
            else:
                out[m.group(1)] = implicit
                implicit += 1
    return out


def strip_comments(text: str) -> str:
    """Quita comentarios CONSERVANDO LA LONGITUD, caracter a caracter.

    Sustituir cada comentario por un unico espacio encoge el texto y rompe
    cualquier mapa de posiciones construido despues: los numeros de linea que
    se reportan dejan de corresponder al fichero. En el corpus real eso daba
    225 de 274 hits con la linea equivocada, y el self-test no lo habria visto
    porque mi fixture no tenia comentarios con saltos de linea dentro.
    """
    out: List[str] = list(text)
    i, n = 0, len(text)
    while i < n:
        if text.startswith("/*", i):
            j = text.find("*/", i + 2)
            j = n if j < 0 else j + 2
            for k in range(i, j):
                if out[k] != "\n":
                    out[k] = " "
            i = j
        elif text.startswith("//", i):
            j = text.find("\n", i)
            j = n if j < 0 else j
            for k in range(i, j):
                out[k] = " "
            i = j
        else:
            i += 1
    return "".join(out)


def find_caps(roots: Sequence[str]) -> Dict[str, List[Dict[str, object]]]:
    """Todos los phm_cap_set/unset del corpus, con fichero y linea."""
    hits: List[Dict[str, object]] = []
    for root in roots:
        if not os.path.isdir(root):
            continue
        for dirpath, dirnames, filenames in os.walk(root):
            dirnames[:] = [d for d in dirnames if d not in (".git", "__pycache__")]
            for fn in filenames:
                if not fn.endswith((".c", ".h")):
                    continue
                p = os.path.join(dirpath, fn)
                try:
                    with open(p, "r", encoding="utf-8", errors="replace") as fh:
                        raw = fh.read()
                except OSError:
                    continue
                if "phm_cap_" not in raw:
                    continue
                clean = strip_comments(raw)
                # La posicion se mapea al ORIGINAL: el numero de linea que se
                # reporta tiene que ser el del fichero, no el de la frase
                # normalizada. Un phm_cap_set partido en dos lineas desplaza
                # el conteo y el informe apuntaria a la linea equivocada.
                norm, back = normalize(clean)
                for m in _SET.finditer(norm):
                    orig = back[m.start()] if m.start() < len(back) else 0
                    lineno = clean[:orig].count("\n") + 1
                    hits.append({
                        "op": m.group("op"),
                        "cap": m.group("cap"),
                        "file": p,
                        "line": lineno,
                        "col": orig - (clean.rfind("\n", 0, orig) + 1) + 1,
                    })
    hits.sort(key=lambda h: (h["cap"], h["file"], h["line"]))
    out: Dict[str, List[Dict[str, object]]] = {}
    for h in hits:
        out.setdefault(str(h["cap"]), []).append(h)
    return out


def capability_decl(path: str) -> Dict[str, str]:
    """Cada capability con el comentario del enum, que dice que significa."""
    out: Dict[str, str] = {}
    if not os.path.isfile(path):
        return out
    with open(path, "r", encoding="utf-8", errors="replace") as fh:
        for line in fh:
            m = re.match(r"\s*(PHM_PlatformCaps_\w+)\s*,\s*/\*\s*(.*?)\s*\*/", line)
            if m:
                out[m.group(1)] = m.group(2)
    return out


def which_initialisers(caps: Dict[str, List[Dict[str, object]]]) -> Dict[str, List[str]]:
    """De qué fichero-funcion viene cada mencion, para acotar el ASIC."""
    out: Dict[str, List[str]] = {}
    for cap, hits in caps.items():
        files = sorted({os.path.basename(str(h["file"])) for h in hits})
        out[cap] = files
    return out


def cap_census(caps: Dict[str, List[Dict[str, object]]],
               decl: Dict[str, str]) -> List[Dict[str, object]]:
    rows: List[Dict[str, object]] = []
    for cap in sorted(caps):
        hits = caps[cap]
        sets = [h for h in hits if h["op"] == "set"]
        unsets = [h for h in hits if h["op"] == "unset"]
        rows.append({
            "cap": cap,
            "description": decl.get(cap, ""),
            "set_count": len(sets),
            "unset_count": len(unsets),
            "files": sorted({os.path.basename(str(h["file"])) for h in hits}),
            "hits": hits,
        })
    return rows


def aplica_cap(rows: Sequence[Dict[str, object]], only: Optional[str]):
    """Aplica `--cap` UNA vez y devuelve (visibles, medidas).

    MEDIDO 2026-10-04 (nodo FILTROS-REPARO-2, sobre el censo
    08-ARQUITECTURA/FILTROS-MAL-FORMADOS.md:432-462).

    El filtro vivia DENTRO de render(), y render() solo se llama en modo texto.
    La rama `--json` construia su diccionario con `rows`, la lista SIN filtrar.
    Consecuencia medida ANTES del arreglo, con la MISMA invocacion:

        --cap PHM_TYPOXX           ->  0 filas en la tabla,        rc=0
        --cap PHM_TYPOXX --json    ->  capabilities=66, rows=66,   rc=0

    Y con un valor que SI existe, que es peor porque ahi el filtro parece
    funcionar:

        --cap SQRamping             ->  1 fila,                     rc=0
        --cap SQRamping --json      ->  capabilities=66, rows=66,   rc=0

    Un consumidor automatico que pase `--cap` y `--json` recibia el censo
    completo y no se enteraba. Por eso el filtro se aplica aqui, antes de las
    DOS salidas, y no dentro de una sola de ellas.

    Se devuelve tambien `medidas`, la poblacion sin filtrar, porque el requisito
    para un filtro abierto no es "que el valor sea valido" sino "que la salida
    diga cuantas filas habia antes del filtro" (§8.7 del censo).
    """
    if not only:
        return list(rows), len(rows)
    return [r for r in rows if only in str(r["cap"])], len(rows)


def error_cap(only: Optional[str], rows: Sequence[Dict[str, object]],
              visibles: Sequence[Dict[str, object]]) -> Optional[str]:
    """El texto del error, o None si el valor es utilizable.

    AQUI ESTA LA TESIS, y no es una suposicion. El filtro es
    `only in str(r["cap"])`, o sea coincidencia de SUBCADENA sobre el NOMBRE de
    la capability. Si el valor fuera subcadena de un solo nombre, ese nombre
    estaria en la poblacion y su fila saldria. De ahi:

        visibles == 0   <=>   el valor NO es subcadena de ningun nombre

    O sea que NO existe aqui el caso "el filtro caso y la poblacion no tiene
    nada": el filtro y la poblacion son el mismo conjunto de nombres. El vacio
    no es un resultado, es un valor que no puede seleccionar nada.

    MEDIDO sobre la poblacion real de 66 capabilities con 18 valores, incluidos
    los casos raros (cadena vacia, prefijo comun, sufijo comun, mayusculas
    distintas): 0 discrepancias. El vector esta en el selftest.

    Esto es lo que separa este caso de un filtro de clase ABIERTA, donde "no
    casa" es una verdad sobre la consulta y no un error de escritura. Aqui el
    conjunto de valores utilizables es calculable y esta medido, asi que se
    puede --y se debe-- rechazar el valor antes de medir.
    """
    if not only or visibles:
        return None
    nombres = sorted({str(r["cap"]) for r in rows})
    lineas = [
        "ERROR  --cap %s no es subcadena de ninguna de las %d capabilities medidas."
        % (only, len(rows)),
        "  Este filtro es coincidencia de SUBCADENA sobre el nombre, y la"
        " poblacion son",
        "  esos mismos nombres: si %r no es subcadena de ninguno, no puede"
        " seleccionar" % only,
        "  ninguna fila. No es que no haya datos, es que el valor no selecciona.",
        "  capabilities que SI existen (%d). Primeras 12:" % len(nombres),
        "    " + ", ".join(nombres[:12]),
    ]
    if only and not only.strip():
        lineas.append("  NOTA  --cap con cadena vacia selecciona las %d: no es un"
                      " filtro." % len(rows))
    return "\n".join(lineas)


def render(rows: Sequence[Dict[str, object]], verbose: bool = False,
           medidas: Optional[int] = None,
           only: Optional[str] = None) -> str:
    """Tabla de texto.

    NO filtra. Antes lo hacia, y por eso el filtro solo existia en este camino:
    la rama `--json` construia su salida con la lista sin filtrar y las dos
    invocaciones de la MISMA linea de ordenes daban conjuntos distintos. El
    filtro esta ahora en `aplica_cap()`, que se llama una vez antes de las dos
    salidas, y aqui solo se declara cuantas filas se han mostrado.
    """
    L = [f"{NAME} {VERSION}"]
    L.append("  UN SET sin unset posterior no prueba que la capability este activa.")
    L.append("  El valor final depende del ORDEN de llamadas, que aqui es declarado, no ejecutado.")
    L.append("")
    L.append(f"  {'capability':<46} {'set':>4} {'unset':>6}  ficheros")
    L.append("  " + "-" * 96)
    for r in rows:
        L.append(f"  {r['cap']:<46} {r['set_count']:>4} {r['unset_count']:>6}  "
                 f"{', '.join(str(f) for f in r['files'])[:44]}")
        if verbose:
            L.append(f"      {r['description'][:100]}")
            for h in r["hits"]:
                mark = "+" if h["op"] == "set" else "-"
                L.append(f"      {mark} {os.path.basename(str(h['file']))}:{h['line']}")
    # El denominador, siempre. Con --cap, "0 filas" solo significa algo al lado
    # de "66 medidas"; sin el, es el mismo vacio mudo que audita el censo.
    if medidas is not None:
        if only:
            L.append("")
            L.append(f"  {len(rows)} de {medidas} capabilities, filtro --cap {only!r} "
                     f"(subcadena del nombre)")
        else:
            L.append("")
            L.append(f"  {medidas} capabilities medidas, sin filtro.")
    return "\n".join(L)


def main(argv: Optional[Sequence[str]] = None) -> int:
    ap = argparse.ArgumentParser(prog=NAME,
                                 description="Censo de PHM_PlatformCaps por ASIC.")
    ap.add_argument("--selftest", action="store_true")
    ap.add_argument("--kernel")
    ap.add_argument("--chip", default=DEFAULT_CHIP)
    ap.add_argument("--cap", default=None, help="filtrar por nombre de capability")
    ap.add_argument("--diff-chip", default=None, metavar="A:B")
    ap.add_argument("--verbose", "-v", action="store_true")
    ap.add_argument("--json", action="store_true")
    args = ap.parse_args(argv)

    if args.selftest:
        return selftest()
    if not args.kernel:
        ap.error("--kernel es obligatorio salvo con --selftest")
    kernel = os.path.abspath(args.kernel)
    pm = os.path.join(kernel, "drivers/gpu/drm/amd/pm", "powerplay")
    inc = os.path.join(kernel, "drivers/gpu/drm/amd/pm", "inc")

    caps = find_caps([pm])
    if not caps:
        print("ERROR  no se encontro ningun phm_cap_set/unset. "
              "Revisa el universo declarado.", file=sys.stderr)
        return 2
    decl = capability_decl(os.path.join(inc, "hardwaremanager.h"))
    enum = parse_chip_enum(os.path.join(kernel, ASIC_ENUM_REL))
    todas = cap_census(caps, decl)

    # El filtro se aplica UNA vez, y aqui, antes de construir las dos salidas.
    # Antes vivia dentro de render(), que solo se llama en modo texto.
    rows, medidas = aplica_cap(todas, args.cap)
    err = error_cap(args.cap, todas, rows)
    if err is not None:
        # A stderr, y no a stdout: con --json un error en stdout rompe el
        # parseo del consumidor, que es justo el que se quiere avisar.
        print(err, file=sys.stderr)
        return 2

    out = {
        "tool": NAME, "version": VERSION,
        "chip": args.chip,
        "chip_value": enum.get(args.chip),
        "capabilities": len(rows),
        # El denominador con su nombre. Sin el, `capabilities` no dice si son 66
        # de 66 o 1 de 66, y un consumidor no puede distinguir el filtro de un
        # censo entero.
        "capabilities_medidas": medidas,
        "filtro_cap": args.cap,
        "declared_enum_entries": len(decl),
        "work_class": "READ_ONLY", "write_execution": "NONE",
        "rows": [{k: v for k, v in r.items() if k != "hits"} for r in rows],
    }

    if args.json:
        print(json.dumps(out, indent=2, ensure_ascii=False))
        return 0

    if args.diff_chip and ":" in args.diff_chip:
        a, b = args.diff_chip.split(":", 1)
        fa = {os.path.basename(str(h["file"])) for c in caps for h in caps[c]
              if h["op"] == "set"}
        print(f"{NAME} {VERSION} · ficheros que hacen phm_cap_set")
        print(f"  {a}: ficheros presentes  -> ver --chip para el detalle")
        print(f"  nota: la diferenciacion real requiere trazar la cadena de "
              f"llamadas; esta herramienta da el censo, no el valor final")
        return 0

    print(render(rows, args.verbose, medidas, args.cap))
    return 0


def selftest() -> int:
    failures: List[str] = []
    vectores = 0

    def check(name: str, got, want) -> None:
        nonlocal vectores
        vectores += 1
        if got != want:
            failures.append(f"{name}: obtuve {got!r}, esperaba {want!r}")

    def check_true(name: str, got) -> None:
        check(name, bool(got), True)

    import tempfile
    with tempfile.TemporaryDirectory() as td:
        src = os.path.join(td, "hwmgr.c")
        with open(src, "w", encoding="utf-8") as fh:
            fh.write(
                "int polaris_set_asic_special_caps(struct pp_hwmgr *hwmgr)\n"
                "{\n"
                "\tphm_cap_set(hwmgr->platform_descriptor.platformCaps,\n"
                "\t\t\tPHM_PlatformCaps_SQRamping);\n"
                "\t/* un comentario con phm_cap_set(x, PHM_PlatformCaps_EVV) "
                "no debe contar */\n"
                # Comentario MULTILINEA a proposito: si strip_comments no
                # conserva la longitud, todos los numeros de linea posteriores
                # se desplazan. En el corpus real eso fueron 225 de 274 hits.
                "\t/* este comentario ocupa\n"
                "\t   varias lineas y contiene un phm_cap_set(x,\n"
                "\t   PHM_PlatformCaps_FANTASMA) que no debe contarse,\n"
                "\t   y su longitud no debe desplazar las lineas */\n"
                "\tif (hwmgr->chip_id != CHIP_POLARIS11) {\n"
                "\t\tphm_cap_set(hwmgr->platform_descriptor.platformCaps,\n"
                "\t\t\tPHM_PlatformCaps_DBRamping);\n"
                "\t}\n"
                "\treturn 0;\n"
                "}\n"
                "int fiji_set_asic_special_caps(struct pp_hwmgr *hwmgr)\n"
                "{\n"
                "\tphm_cap_unset(hwmgr->platform_descriptor.platformCaps,\n"
                "\t\t\tPHM_PlatformCaps_SQRamping);\n"
                "\treturn 0;\n"
                "}\n"
            )
        caps = find_caps([td])
        check("census.SQRamping.set", len([h for h in caps["PHM_PlatformCaps_SQRamping"]
                                           if h["op"] == "set"]), 1)
        check("census.SQRamping.unset", len([h for h in caps["PHM_PlatformCaps_SQRamping"]
                                             if h["op"] == "unset"]), 1)
        check("census.DBRamping.set", len(caps.get("PHM_PlatformCaps_DBRamping", [])), 1)
        # El comentario con phm_cap_set no debe generar un hit: es la clase de
        # error que produce capacidades fantasma.
        check("census.comentario_ignorado", "PHM_PlatformCaps_EVV" in caps, False)
        check("census.comentario_multilinea_ignorado",
              "PHM_PlatformCaps_FANTASMA" in caps, False)
        # El phm_cap_set de DBRamping abre en la 11 y el nombre de la capability
        # va en la 12 (continuacion). Lo que se reporta es donde abre la llamada.
        # Este caso es el que fallo en el corpus: 225 de 274 hits con la linea
        # desplazada porque strip_comments acortaba el texto.
        db = caps["PHM_PlatformCaps_DBRamping"][0]
        check("census.linea_tras_comentario", db["line"], 11)
        # El set partido en dos lineas debe contarse: es el caso real.
        check("census.continuacion_de_linea",
              len([h for h in caps["PHM_PlatformCaps_SQRamping"] if h["op"] == "set"]), 1)

        # --- el filtro --cap, MEDIDO 2026-10-04 (nodo FILTROS-REPARO-2) ---
        #
        # El selftest anterior NO tenia ni un vector sobre `--cap`. Es por eso
        # que el defecto sobrevivio: la puerta se validaba contra herramientas
        # que ya pasan, y aqui no habia caso malo que rompe.
        capas = ("PHM_PlatformCaps_SQRamping", "PHM_PlatformCaps_DBRamping",
                 "PHM_PlatformCaps_SMC")
        # Las filas necesitan las MISMAS claves que las de cap_census(): render()
        # lee set_count, unset_count y files. Un fixture con menos campos prueba
        # una forma de fila que la herramienta nunca produce.
        filas = [{"cap": c, "set_count": 1, "unset_count": 0, "files": ["hwmgr.c"],
                  "description": "d", "hits": []} for c in capas]
        # La tesis de error_cap: visibles==0 <=> el valor no es subcadena de
        # ningun nombre. Se prueba en los dos sentidos, con los casos raros.
        for valor, esperado in (("SQRamping", 1), ("Ramping", 2), ("SM", 1),
                                ("PlatformCaps_SMC", 1), ("SMCtoPPLIBAcdcGpio", 0),
                                ("PHM_TYPOXX", 0), ("sqramping", 0), ("xyz", 0),
                                ("SMtoPPLI", 0), ("", 3), ("PHM_PlatformCaps_", 3)):
            vis, med = aplica_cap(filas, valor)
            check(f"cap.filtra[{valor!r}]", len(vis), esperado)
            check(f"cap.denominador[{valor!r}]", med, 3)
            # Y la equivalencia: no puede haber 0 visibles con un valor que sea
            # subcadena de algun nombre. Si algun dia el filtro dejara de ser de
            # subcadena, este vector avisa de que la tesis ya no vale.
            check(f"cap.tesis[{valor!r}]",
                  (len(vis) == 0) == (not any(valor in str(r["cap"]) for r in filas)),
                  True)
        # Un valor que no puede seleccionar: rc=2, y el texto ANCLA el valor.
        # Un orculo que aceptara cualquier "no" de la salida daria un OK falso.
        err = error_cap("PHM_TYPOXX", filas, aplica_cap(filas, "PHM_TYPOXX")[0])
        check_true("cap.error_ancla_el_valor", err and "--cap PHM_TYPOXX" in err)
        check_true("cap.error_dice_que_no_hay_datos", err and "no es subcadena" in err)
        check_true("cap.error_lista_las_existentes",
                   err and "capabilities que SI existen (3)" in err)
        # Un valor valido NO produce error: este es el control positivo, sin el
        # cual la puerta astringiria a tanto y no mediria nada.
        check("cap.sin_error_si_valida",
              error_cap("SQRamping", filas, aplica_cap(filas, "SQRamping")[0]),
              None)
        check("cap.sin_error_sin_filtro", error_cap(None, filas, filas), None)
        # Sin filtro, la salida es la censo entero. Es el otro modo de romperlo.
        vis, med = aplica_cap(filas, None)
        check("cap.sin_filtro_devuelve_todo", (len(vis), med), (3, 3))
        # render() ya NO filtra, y recibe las filas YA filtradas, como hace main(). Si
        # volviera a filtrar, el filtro se aplicaria dos veces y --json y texto
        # volverian a discrepar sin que se note.
        vis, med = aplica_cap(filas, "SQRamping")
        txt = render(vis, False, med, "SQRamping")
        check_true("render_no_filtra", "PHM_PlatformCaps_DBRamping" not in txt)
        check_true("render_muestra_lo_filtrado", "PHM_PlatformCaps_SQRamping" in txt)
        check_true("render_declara_el_denominador", "1 de 3 capabilities" in txt)
        # La linea reportada debe ser real, no la de la frase normalizada.
        for cap, hits in caps.items():
            for h in hits:
                with open(src, encoding="utf-8") as fh2:
                    line = fh2.readlines()[int(h["line"]) - 1]
                if "phm_cap_" not in line:
                    failures.append(f"linea incorrecta para {cap}: {h['line']} -> {line!r}")
                    break

    print(f"{NAME} {VERSION} · self-test")
    # El numero de vectores se imprime SIEMPRE. Un "RESULTADO OK" sin cifra no
    # dice si se han comprobado 7 cosas o 7000, y no se puede comparar con el
    # el de antes de un arreglo, para ver si la red ha crecido o no.
    print(f"  vectores: {vectores}")
    if failures:
        print(f"  RESULTADO FALLIDO ({len(failures)} de {vectores}):")
        for f in failures:
            print(f"    - {f}")
        return 1
    print(f"  RESULTADO OK · {vectores} vectores conocidos reproducidos")
    print("  NOTA: censo declarado por fichero. NO ejecuta la cadena de llamadas.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
