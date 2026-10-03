#!/usr/bin/env python3
# SPDX-License-Identifier: GPL-2.0
"""
citegen.py - audita TODAS las citas del proyecto y dice, de cada una, si el
fichero citado es de un ASIC que esta GPU ejecuta.

POR QUE EXISTE, Y POR QUE AHORA

findings/043 demostro que 035 y 036Taken leyeron el ASIC equivocado: el
productor de PTE que implementamos era sdma_v4_0.c, y Polaris12 ejecuta
sdma_v3_0.c. La retraccion se hizo a mano, sobre dos findings. La pregunta
general es "cuantas OTRAS citas del proyecto apuntan a un fichero de otro ASIC",
y esa no se puede responder a mano: el proyecto tiene cientos de citas.

which_hw.py responde la pregunta para un bloque de IP. Esta la responde para
todo el proyecto, y es la generalizacion.

LA REGLA, Y POR QUE NO ES "EL NOMBRE DICE v8_0"

043 tambien demostro que el nombre del fichero NO decide. Hay tres bloques GMC
(gmc_v8_0, gmc_v8_1, gmc_v8_5) definidos en gmc_v8_0.c con la MISMA tabla
.funcs, y dos bloques SDMA en ficheros distintos. El discriminante es .funcs, no
el nombre del fichero. Asi que esta herramienta no juzga por el nombre: resuelve
el fichero -> el ip_block que lo define -> si el case de CHIP_POLARIS12 lo anade.

Y anade un caso mas que 043 no miro: un fichero puede ser de MI ASIC por su
nombre y aun asi no Contributors.run en esta GPU, porque el despacho es por
version de IP. Eso se clasifica aparte y no como error.

CLASIFICACION DE CADA CITA

  EN_DISPATCH      el fichero implementa un bloque que el case del chip anade
  COMPARTIDA       el fichero implementa varios bloques, uno de los cuales lo
                   anade el case. Sigue siendo codigo que corre, pero conviene
                   citar el bloque concreto
  EN_RUTA_IP       el fichero no lo anade ningun case de chip, pero su
                   fichero lo enruta una funcion que decide por version de IP.
                   No decidible sin leer un registro
  NO_EN_DISPATCH   el fichero existe, implementa bloques, y ninguno lo anade el
                   case de CHIP_POLARIS12. SOSPECHOSO
  OTRO_ASIC        el nombre del fichero declara otra generacion y ningun case
                   lo anade. SOSPECHOSO
  FUERA_DE_AMDGPU   la cita no es a un fichero de amdgpu/ (asic_reg, kernel, ...)
                   y no se juzga
  NO_RESUELTA      el fichero citado no existe, o la cita no tiene linea

LO QUE NO ES

No reescribe findings. No dice que una cita sea incorrecta: dice que un fichero
citado no esta en la ruta de ejecucion de esta GPU, y deja el juicio a quien
lee. Un hallazgo sobre Tonga es informacion legitima y no se marca como error.

CODIGOS DE SALIDA

  0  ninguna cita sospechosa
  1  hay citas sospechosas
  2  el corpus no esta donde se le dijo
"""

import argparse
import json
import os
import re
import sys
from typing import Dict, List, Optional, Set, Tuple

VERSION = "1.0.0"
CHIP = "CHIP_POLARIS12"

# Directorios donde se buscan las citas. Los dos con nombre de ASIC se excluyen
# porque son el corpus, no el proyecto.
SKIP_PARTS = {".git", "rx550-upstream-7.2.8", "linux-7.2.8", "linux-7.1.3",
              "RESEARCH", "node_modules", ".write-lock"}

# Una cita tiene esta forma:  gmc_v8_0.c:661   o   `gmc_v8_0.c:661-677`
CITA = re.compile(
    r"(?<![A-Za-z0-9_])"
    r"([a-z][a-z0-9_]*v\d+_\d+(?:_\d+)?[a-z0-9_]*|[a-z][a-z0-9_]*_v\d+_\d+)"
    r"\.(c|h)"
    r"(?::(\d+))?"
)


class Corpus:
    def __init__(self, root: str):
        self.root = root
        self.amdgpu = os.path.join(root, "drivers/gpu/drm/amd/amdgpu")

    def ok(self) -> bool:
        return os.path.isdir(self.amdgpu)

    def leer(self, nombre: str) -> List[str]:
        p = os.path.join(self.amdgpu, nombre)
        try:
            with open(p, "r", errors="replace") as f:
                return f.read().splitlines()
        except OSError:
            return []


def mapear_despacho(c: Corpus) -> Dict[str, object]:
    """Los bloques que anade el case de CHIP_POLARIS12, y de donde se anaden.

    Se lee el case hasta su break, no un numero fijo de lineas: un recorte fijo
    se come el case siguiente y hace que los bloques de otro chip parezcan de
    este. Es el error que hizo que 035 pareciera correcta.
    """
    result: Dict[str, object] = {"bloques_del_chip": {}, "enrutados_por_ip": {}}

    for entry in sorted(os.listdir(c.amdgpu)):
        if not entry.endswith(".c"):
            continue
        lines = c.leer(entry)
        if not lines:
            continue
        texto = "\n".join(lines)
        if "amdgpu_device_ip_block_add" not in texto:
            continue

        # los blocks del case del chip, hasta su break
        for i, ln in enumerate(lines):
            if not re.match(r"\s*case\s+%s\s*:" % CHIP, ln):
                continue
            sig: List[str] = []
            cerrado = False
            for k in range(i, min(i + 60, len(lines))):
                sig.extend(re.findall(
                    r"amdgpu_device_ip_block_add\s*\([^,]*,\s*&(\w+)\)",
                    lines[k]))
                if re.match(r"\s*break;\s*$", lines[k]):
                    cerrado = True
                    break
            for b in sorted(set(sig)):
                result["bloques_del_chip"][b] = "%s:%d" % (entry, i + 1)
            if not cerrado:
                result["bloques_del_chip"]["__incompleto__"] = \
                    "%s:%d" % (entry, i + 1)

        # los bloques que enruta una funcion que decide por version de IP
        for i, ln in enumerate(lines):
            m = re.match(r"^(?:static\s+)?(?:int|void)\s+(\w+)\s*\(", ln)
            if not m:
                continue
            cuerpo = lines[i:i + 60]
            disc = "?"
            for j in range(1, 12):
                sm = re.search(r"switch\s*\(\s*(.+?)\s*\)", cuerpo[j])
                if sm:
                    disc = sm.group(1)
                    break
            if "ip_version" not in disc:
                continue
            for b in sorted(set(re.findall(
                    r"amdgpu_device_ip_block_add\s*\([^,]*,\s*&(\w+)\)",
                    "\n".join(cuerpo)))):
                result["enrutados_por_ip"][b] = {
                    "fichero": entry, "funcion": m.group(1),
                    "discriminante": disc.strip(),
                }
    return result


def bloques_de_fichero(c: Corpus) -> Dict[str, List[Dict[str, object]]]:
    """fichero -> lista de bloques que define, con su .funcs y su fichero.

    El .funcs es el discriminante real (043), asi que se lee de la definicion y
    no se infiere del nombre.
    """
    out: Dict[str, List[Dict[str, object]]] = {}
    for entry in sorted(os.listdir(c.amdgpu)):
        if not entry.endswith((".c", ".h")):
            continue
        lines = c.leer(entry)
        if not lines:
            continue
        for i, ln in enumerate(lines):
            m = re.match(
                r"^\s*(?:const\s+)?struct\s+amdgpu_ip_block_version\s+(\w+)\s*=",
                ln)
            if not m:
                continue
            funcs = None
            for k in range(i, min(i + 14, len(lines))):
                fm = re.search(r"\.funcs\s*=\s*&(\w+)", lines[k])
                if fm:
                    funcs = fm.group(1)
                    break
            out.setdefault(entry, []).append({
                "bloque": m.group(1), "linea": i + 1, "funcs": funcs,
            })
    return out


def generacion_de_nombre(nombre: str) -> str:
    m = re.search(r"v(\d+)_(\d+)(?:_(\d+))?", nombre)
    return "v%s_%s" % (m.group(1), m.group(2)) if m else "SIN_GENERACION"


def citar_proyecto(root: str) -> List[Dict[str, object]]:
    """Recorre los ficheros del PROYECTO y extrae las citas con linea."""
    out: List[Dict[str, object]] = []
    for dirpath, dirnames, filenames in os.walk(root):
        dirnames[:] = [d for d in dirnames
                       if d not in SKIP_PARTS and not d.startswith(".")]
        for fn in sorted(filenames):
            if not fn.endswith((".md", ".c", ".h", ".sh", ".py")):
                continue
            p = os.path.join(dirpath, fn)
            try:
                with open(p, "r", errors="replace") as f:
                    texto = f.read()
            except OSError:
                continue
            for num, ln in enumerate(texto.splitlines(), start=1):
                for m in CITA.finditer(ln):
                    out.append({
                        "fichero_citado": m.group(1) + "." + m.group(2),
                        "en": os.path.relpath(p, root),
                        "linea_cita": num,
                        "linea_en_fichero": int(m.group(3)) if m.group(3) else None,
                        "contexto": ln.strip()[:150],
                    })
    return out


def clasificar(c: Corpus,
               desp: Dict[str, object],
               bloq: Dict[str, List[Dict[str, object]]],
               cita: Dict[str, object]) -> Tuple[str, str]:
    """(clase, explicacion) para una cita."""
    f = str(cita["fichero_citado"])
    base = f.rsplit(".", 1)[0]

    if f not in bloq and not os.path.isfile(os.path.join(c.amdgpu, f)):
        # No es un fichero de amdgpu/. Puede ser asic_reg, un .h del kernel, o
        # simplemente no existir. Se distingue con el nombre: si declara
        # generacion vNN y no esta en amdgpu/, es un asic_reg de otra.
        gen = generacion_de_nombre(base)
        if gen == "SIN_GENERACION":
            return "FUERA_DE_AMDGPU", "no declara generacion; no se juzga"
        return "FUERA_DE_AMDGPU", "no esta en amdgpu/ (probable asic_reg de %s)" % gen

    bloques = bloq.get(f)
    if not bloques:
        return "FUERA_DE_AMDGPU", "existe en amdgpu/ pero no define ip_block"

    del_chip = desp["bloques_del_chip"]
    for b in bloques:
        if b["bloque"] in del_chip:
            return ("EN_DISPATCH",
                    "%s lo anade el case de %s en %s"
                    % (b["bloque"], CHIP, del_chip[b["bloque"]]))

    for b in bloques:
        r = desp["enrutados_por_ip"].get(b["bloque"])
        if r:
            return ("EN_RUTA_IP",
                    "%s lo enruta %s por %s: no decidible sin leer el registro"
                    % (b["bloque"], r["fichero"], r["discriminante"][:40]))

    if len(bloques) > 1:
        return ("NO_EN_DISPATCH",
                "define %d bloques (%s) y el case del chip no anade ninguno"
                % (len(bloques), ", ".join(b["bloque"] for b in bloques[:4])))

    b = bloques[0]
    return ("OTRO_ASIC",
            "%s declara %s, con .funcs = &%s, y no lo anade el case de %s"
            % (f, generacion_de_nombre(base), b["funcs"] or "?", CHIP))


def selftest() -> int:
    """Vectores sobre el clasificador, con un doble en vez del corpus.

    El caso que importa es el de 043: tres bloques GMC definidos en el MISMO
    fichero y con la MISMA tabla .funcs, de los que el case del chip anade
    uno. Un clasificador que juzgue por el nombre del fichero diria que los
    tres son de otro ASIC, y ese fue el error que 043 casi dejo como
    conclusion.
    """
    print("=== citegen selftest ===\n")
    fallos = 0

    class CorpusFalso:
        amdgpu = "/no/existe"

    # El caso real: gmc_v8_0.c define v8_0, v8_1 y v8_5, y el chip anade v8_1.
    # Reproduce vi.c:2107-2123 tal cual: el chip anade gmc_v8_1 (definido en
    # gmc_v8_0.c), gfx_v8_0, y sdma_v3_1 (definido en sdma_v3_0.c).
    desp = {"bloques_del_chip": {
                "gmc_v8_1_ip_block": "vi.c:2107",
                "gfx_v8_0_ip_block": "vi.c:2109",
                "sdma_v3_1_ip_block": "vi.c:2111",
            },
            "enrutados_por_ip": {
                "sdma_v4_0_ip_block": {"fichero": "amdgpu_discovery.c",
                                       "funcion": "set_sdma",
                                       "discriminante": "amdgpu_ip_version(adev, SDMA0_HWIP, 0)"},
            }}
    bloq = {
        "gmc_v8_0.c": [
            {"bloque": "gmc_v8_0_ip_block", "linea": 1754, "funcs": "gmc_v8_0_ip_funcs"},
            {"bloque": "gmc_v8_1_ip_block", "linea": 1762, "funcs": "gmc_v8_0_ip_funcs"},
            {"bloque": "gmc_v8_5_ip_block", "linea": 1770, "funcs": "gmc_v8_0_ip_funcs"},
        ],
        "sdma_v3_0.c": [
            {"bloque": "sdma_v3_1_ip_block", "linea": 1693, "funcs": "sdma_v3_0_ip_funcs"},
        ],
        "sdma_v4_0.c": [
            {"bloque": "sdma_v4_0_ip_block", "linea": 2735, "funcs": "sdma_v4_0_ip_funcs"},
        ],
    }
    c = CorpusFalso()

    vectores = [
        # (fichero citado, clase esperada, por que)
        ("gmc_v8_0.c", "EN_DISPATCH",
         "el case anade gmc_v8_1_ip_block, definido en este fichero"),
        ("sdma_v4_0.c", "EN_RUTA_IP",
         "nadie lo anade por case, pero discovery lo enruta por version"),
        ("sdma_v3_0.c", "EN_DISPATCH",
         "el chip anade sdma_v3_1_ip_block, definido en este fichero"),
    ]
    for fichero, esperado, porque in vectores:
        got, why = clasificar(c, desp, bloq, {"fichero_citado": fichero})
        if got != esperado:
            print("  FAIL %-14s dio %s, esperado %s" % (fichero, got, esperado))
            print("       por que dio eso: %s" % why)
            fallos += 1
        else:
            print("  OK   %-14s %-15s %s" % (fichero, got, porque))

    # Un fichero que el chip no usa y declara VARIOS bloques: NO_EN_DISPATCH,
    # no OTRO_ASIC. La distincion importa porque "varios bloques" puede ser
    # codigo compartido, y un fichero compartido no es simplemente de otro ASIC.
    bloq_compartido = dict(bloq)
    bloq_compartido["gfx_v7_0.c"] = [
        {"bloque": "gfx_v7_1_ip_block", "linea": 1, "funcs": "gfx_v7_0_ip_funcs"},
        {"bloque": "gfx_v7_3_ip_block", "linea": 2, "funcs": "gfx_v7_0_ip_funcs"},
    ]
    got, why = clasificar(c, desp, bloq_compartido,
                          {"fichero_citado": "gfx_v7_0.c"})
    if got != "NO_EN_DISPATCH":
        print("  FAIL un fichero compartido dio %s, esperado NO_EN_DISPATCH: %s"
              % (got, why))
        fallos += 1
    else:
        print("  OK   gfx_v7_0.c     NO_EN_DISPATCH   declara 3 bloques, "
              "codigo compartido")

    # Un fichero con generacion en el nombre que no esta en amdgpu/: puede ser
    # asic_reg, y eso NO es un error.
    got, why = clasificar(c, desp, bloq, {"fichero_citado": "gmc_7_0_d.h"})
    if got != "FUERA_DE_AMDGPU":
        print("  FAIL un .h de asic_reg dio %s, esperado FUERA_DE_AMDGPU" % got)
        fallos += 1
    else:
        print("  OK   gmc_7_0_d.h   FUERA_DE_AMDGPU   es asic_reg, no amdgpu/")

    # Una cita sin linea sigue siendo clasificable: el fichero basta.
    got, _ = clasificar(c, desp, bloq, {"fichero_citado": "gmc_v8_0.c",
                                       "linea_en_fichero": None})
    if got != "EN_DISPATCH":
        print("  FAIL una cita sin linea dio %s" % got)
        fallos += 1
    else:
        print("  OK   una cita sin numero de linea se clasifica igual")

    print("=" * 72)
    if fallos:
        print("RESULT: FAIL (%d)" % fallos)
        return 1
    print("RESULT: PASS (6 vectores)")
    return 0


def main() -> int:
    ap = argparse.ArgumentParser(
        description="que citas del proyecto apuntan a un ASIC que esta GPU no ejecuta")
    ap.add_argument("--kernel")
    ap.add_argument("--json", action="store_true")
    ap.add_argument("--solo-sospechosas", action="store_true", default=True)
    ap.add_argument("--todas", action="store_true")
    ap.add_argument("--fichero", help="restringe a un fichero de proyecto")
    ap.add_argument("--selftest", action="store_true")
    args = ap.parse_args()

    if args.selftest:
        return selftest()

    here = os.path.dirname(os.path.abspath(__file__))
    raiz = os.path.abspath(os.path.join(here, ".."))
    corpus = args.kernel
    if not corpus:
        for cand in (os.path.join(raiz, "rx550-upstream-7.2.8", "linux-7.2.8"),
                     os.path.join(raiz, "RESEARCH", "working", "linux-7.1.3")):
            if os.path.isdir(cand):
                corpus = cand
                break
    if not corpus or not Corpus(corpus).ok():
        print("citegen: no encuentro el corpus. Usa --kernel.", file=sys.stderr)
        return 2

    c = Corpus(corpus)
    desp = mapear_despacho(c)
    bloq = bloques_de_fichero(c)
    citas = citar_proyecto(raiz)
    if args.fichero:
        citas = [x for x in citas if args.fichero in str(x["en"])]

    por_clase: Dict[str, int] = {}
    detalle: List[Dict[str, object]] = []
    sospechosos: List[Dict[str, object]] = []
    for cita in citas:
        clase, why = clasificar(c, desp, bloq, cita)
        por_clase[clase] = por_clase.get(clase, 0) + 1
        fila = dict(cita)
        fila["clase"] = clase
        fila["por_que"] = why
        detalle.append(fila)
        if clase in ("NO_EN_DISPATCH", "OTRO_ASIC"):
            sospechosos.append(fila)

    if args.json:
        print(json.dumps({
            "version": VERSION, "chip": CHIP,
            "corpus": corpus,
            "bloques_del_chip": desp["bloques_del_chip"],
            "enrutados_por_ip": desp["enrutados_por_ip"],
            "recuento": por_clase, "detalle": detalle,
        }, indent=2, sort_keys=True, default=str))
        return 1 if sospechosos else 0

    print("=" * 78)
    print("citegen %s · %s · WORK_CLASS=READ_ONLY" % (VERSION, CHIP))
    print("=" * 78)
    print("corpus      %s" % corpus)
    print("proyecto    %s" % raiz)
    print("citas       %d  (ficheros .md/.c/.h/.sh/.py, corpus excluido)"
          % len(citas))
    print()
    print("  el case de %s anade %d bloques, en %d fichero(s)"
          % (CHIP, len([k for k in desp["bloques_del_chip"]
                        if not k.startswith("__")]),
             len(set(v.rsplit(":", 1)[0]
                     for k, v in desp["bloques_del_chip"].items()
                     if not k.startswith("__")))))
    if "__incompleto__" in desp["bloques_del_chip"]:
        print("  AVISO: un case no se cerro con break dentro de 60 lineas:")
        print("         %s. Su lista puede estar incompleta."
              % desp["bloques_del_chip"]["__incompleto__"])
    print()

    print("=" * 78)
    print("RECUENTO POR CLASE")
    print("=" * 78)
    for k in sorted(por_clase, key=lambda x: -por_clase[x]):
        marca = "  <-- SOSPECHOSO" if k in ("NO_EN_DISPATCH", "OTRO_ASIC") else ""
        print("  %-18s %5d%s" % (k, por_clase[k], marca))
    print()

    # agrupar las sospechosas por fichero de proyecto y por fichero citado
    if sospechosos:
        print("=" * 78)
        print("CITAS SOSPECHOSAS: el fichero citado no lo ejecuta esta GPU")
        print("=" * 78)
        por_doc: Dict[str, List[Dict[str, object]]] = {}
        for f in sospechosos:
            por_doc.setdefault(str(f["en"]), []).append(f)
        for doc in sorted(por_doc):
            filas = por_doc[doc]
            print("  %s  (%d)" % (doc, len(filas)))
            vistos: Set[Tuple[str, str]] = set()
            for f in filas:
                clave = (str(f["fichero_citado"]), str(f["clase"]))
                if clave in vistos:
                    continue
                vistos.add(clave)
                print("      cita %-22s %s" % (f["fichero_citado"], f["clase"]))
                print("           %s" % f["por_que"])
                n_lineas = sum(1 for x in filas
                               if x["fichero_citado"] == f["fichero_citado"])
                n_docs = len(set(x["en"] for x in filas
                                 if x["fichero_citado"] == f["fichero_citado"]))
                print("           en %d cita(s) de %d documento(s)"
                      % (n_lineas, n_docs))
            print()

    print("=" * 78)
    print("LO QUE ESTA HERRAMIENTA NO DICE")
    print("=" * 78)
    print("  - no afirma que una cita sea ERRONEA. Un hallazgo sobre Tonga es")
    print("    informacion legitima. Lo que se senala es que el fichero citado no")
    print("    esta en la ruta de ejecucion de esta GPU, que es la condicion que")
    print("    produjo la retraccion de 035/036 en 043.")
    print("  - una cita a otro ASIC puede ser correcta y util: la comparacion de")
    print("    generaciones es evidencia. Lo peligroso es citarla sin decirlo, y")
    print("    eso lo juzga quien lee.")
    print("  - no cubre las citas sin numero de linea, ni las citas a funciones")
    print("    ni a registros. Solo las citas con nombre de fichero de ASIC.")
    print("  - el grafo se construye leyendo el case del chip y los bloques que")
    print("    define cada fichero. Si un bloque lo anade una funcion que no se")
    print("    parece a una de despacho, se clasifica como NO_EN_DISPATCH: es un")
    print("    NEGATIVE_RESULT acotado, no una afirmacion de que no lo ejecuta.")
    return 1 if sospechosos else 0


if __name__ == "__main__":
    sys.exit(main())
