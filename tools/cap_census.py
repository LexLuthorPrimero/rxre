#!/usr/bin/env python3
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


def render(rows: Sequence[Dict[str, object]], verbose: bool = False,
           only: Optional[str] = None) -> str:
    L = [f"{NAME} {VERSION}"]
    L.append("  UN SET sin unset posterior no prueba que la capability este activa.")
    L.append("  El valor final depende del ORDEN de llamadas, que aqui es declarado, no ejecutado.")
    L.append("")
    L.append(f"  {'capability':<46} {'set':>4} {'unset':>6}  ficheros")
    L.append("  " + "-" * 96)
    for r in rows:
        if only and only not in str(r["cap"]):
            continue
        L.append(f"  {r['cap']:<46} {r['set_count']:>4} {r['unset_count']:>6}  "
                 f"{', '.join(str(f) for f in r['files'])[:44]}")
        if verbose:
            L.append(f"      {r['description'][:100]}")
            for h in r["hits"]:
                mark = "+" if h["op"] == "set" else "-"
                L.append(f"      {mark} {os.path.basename(str(h['file']))}:{h['line']}")
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
    rows = cap_census(caps, decl)

    out = {
        "tool": NAME, "version": VERSION,
        "chip": args.chip,
        "chip_value": enum.get(args.chip),
        "capabilities": len(rows),
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

    print(render(rows, args.verbose, args.cap))
    return 0


def selftest() -> int:
    failures: List[str] = []

    def check(name: str, got, want) -> None:
        if got != want:
            failures.append(f"{name}: obtuve {got!r}, esperaba {want!r}")

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
        # La linea reportada debe ser real, no la de la frase normalizada.
        for cap, hits in caps.items():
            for h in hits:
                with open(src, encoding="utf-8") as fh2:
                    line = fh2.readlines()[int(h["line"]) - 1]
                if "phm_cap_" not in line:
                    failures.append(f"linea incorrecta para {cap}: {h['line']} -> {line!r}")
                    break

    print(f"{NAME} {VERSION} · self-test")
    if failures:
        print(f"  RESULTADO FALLIDO ({len(failures)}):")
        for f in failures:
            print(f"    - {f}")
        return 1
    print("  RESULTADO OK · vectores conocidos reproducidos")
    print("  NOTA: censo declarado por fichero. NO ejecuta la cadena de llamadas.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
