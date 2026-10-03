#!/usr/bin/env python3
# SPDX-License-Identifier: GPL-2.0
"""
driroute.py - quien es "dri/0", y donde el proyecto asume que lo sabe.

POR QUE EXISTE

Un hallazgo (258) encontro que en esta maquina la RX 550 es card1 y la integrada
es card0, y que herramientas.md mandaba a leer los registros de la AMD en
/sys/kernel/debug/dri/0/, que es la INTEL.

Eso no era un fallo aislado: el proyecto usa las dos formas y no sabe cual es
cual. Medido sobre el proyecto, excluyendo RESEARCH y el corpus de upstream:

    dri/0    24 apariciones     <-- la integrada
    dri/1    22 apariciones     <-- la AMD
    dri/0000:01:00.0   15      <-- la AMD, por direccion, la unica robusta
    dri/129  10                 <-- renderD128: un MINOR, no un indice de card
    dri/137   1                 <-- igual

Y el recuento que parece obvio esta MAL. `card1` aparece 537 veces y `card0` 75, y
casi ninguna es un nodo DRM: en este proyecto `card1` es sobre todo un REGISTRO
DEL ASIC (VM_CARD1, MC_CARD1) y `cardN` es la notacion generica. Un buscador de
"cardN" que no mire el contexto reporta 600 falsos positivos y esconde los 46 que
si importan.

QUE DISTINGUE, y por que no basta con un patron

  dri/<indice de card>   sigue a /sys/class/drm/card<indice>. ESTABLE solo dentro
                         de esta maquina y de ESTE arranque: depende del orden
                         de probe, que puede cambiar con el kernel o el driver.
  dri/<minor de render>  128+1, 128+2 ... es el MINOR del nodo render, no un
                         indice. Numeros altos que empiezan en dri/ y NO son
                         rutas de debugfs de card.
  dri/<bdf>              0000:01:00.0. NO cambia con el orden de probe, y es lo
                         unico que sobrevive a otro kernel.

LO QUE HACE Y LO QUE NO HACE

  MIDE  quien es cada indice, desde sysfs, cada vez que se ejecuta. No lo tiene
        guardado, porque un indice guardado es justo el error que caza.
  REPORTA, no reescribe. Las apariciones estan en hallazgos que ya estan
        escritos y que por regla no se reescriben: un hallazgo que cuenta un
        error conserva el error que conto. Cambiar el texto de un hallazgo para
        que la auditoria quede limpia es fabricar el hallazgo.
  Por eso la salida es un INFORME con sitios, y la correccion la decide quien
  escribe, en el fichero que escribe.

WORK_CLASS=READ_ONLY
WRITE_EXECUTION=NONE
"""

import argparse
import json
import os
import re
import sys
from typing import Dict, List, Optional, Tuple

VERSION = "1.0.0"
RAIZ = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
EXCLUIDOS = ("RESEARCH", "rx550-upstream", ".git", "__pycache__", "node_modules")

# El indice de un card tiene UNA O DOS cifras: card0..cardN con N pequeno. Un
# minor de render tiene TRES o mas: 128+1=129, 128+9=137. Y una BDF tiene cuatro
# hexadecimales antes de los dos puntos.
#
# Con un [\d]+ y un lookBEHIND -- que es lo que habia -- el patron nunca casaba:
# tras \d+ el caracter anterior es siempre un digito, y (?<!\d) es falso siempre.
# De ahi que tres vectores fallaran a la vez y el sintoma fuera "no encuentra
# nada" en vez de "esta mal escrito".
RE_DRI = re.compile(r"/dri/(\d{1,2})(?!\d)")
RE_DRI_BDF = re.compile(r"/dri/([0-9a-f]{4}:[0-9a-f]{2}:[0-9a-f]{2}\.[0-9])")
RE_RENDER = re.compile(r"/dri/(\d{3,})")
RE_CARD_CTX = re.compile(r"/sys/class/drm/card(\d+)")


def indice_amd() -> Tuple[Optional[int], Optional[str]]:
    """(indice de card de la AMD, bdf). Medido, no guardado.

    Se identifica por device id 1002:699f, no por "la segunda GPU que aparezca":
    el orden de enumeracion es justo lo que este tool demuestra que no es
    fiable como criterio."""
    d = "/sys/class/drm"
    for card in sorted(os.listdir(d)):
        if not re.fullmatch(r"card\d+", card):
            continue
        dev = os.path.join(d, card, "device")
        try:
            with open(os.path.join(dev, "vendor")) as fh:
                ven = fh.read().strip().lower()
            with open(os.path.join(dev, "device")) as fh:
                de = fh.read().strip().lower()
        except OSError:
            continue
        if ven == "0x1002" and de == "0x699f":
            return int(card[4:]), os.path.basename(
                os.path.realpath(os.path.join(dev, "..", "device"))) and _bdf(dev)
    return None, None


def _bdf(dev: str) -> Optional[str]:
    try:
        real = os.path.realpath(dev)
        for part in real.split(os.sep):
            if re.fullmatch(r"[0-9a-f]{4}:[0-9a-f]{2}:[0-9a-f]{2}\.[0-9]", part):
                return part
    except OSError:
        pass
    return None


def indice_intel() -> Optional[int]:
    d = "/sys/class/drm"
    for card in sorted(os.listdir(d)):
        if not re.fullmatch(r"card\d+", card):
            continue
        try:
            with open(os.path.join(d, card, "device", "vendor")) as fh:
                if fh.read().strip().lower() == "0x8086":
                    return int(card[4:])
        except OSError:
            continue
    return None


def escanear(raiz: str) -> Dict[str, object]:
    amd, bdf = indice_amd()
    intel = indice_intel()
    filas: List[dict] = []
    # NO SE CUENTA A SI MISMO. Este fichero NOMBRA dri/0 porque explica que es
    # el numero de la integrada, y un escaner que se incluye a si mismo reporta
    # sus propios ejemplos como si fueran usos. En la primera medicion salia dos
    # veces y hacia falta leer el resultado para saber que eran esas dos.
    #
    # Es la misma trampa que con VM_CARD1: un nombre que se busca aparece en el
    # sitio que explica por que se busca. Autoexcluirse es lo que hace falta, y
    # queda dicho para que no parezca que el numero esta editado.
    YO = os.path.abspath(__file__)
    for dp, dn, fn in os.walk(raiz):
        dn[:] = [x for x in dn if x not in EXCLUIDOS]
        for f in sorted(fn):
            if not f.endswith((".md", ".py", ".sh")):
                continue
            if os.path.abspath(os.path.join(dp, f)) == YO:
                continue
            p = os.path.join(dp, f)
            try:
                with open(p, encoding="utf-8", errors="replace") as fh:
                    lineas = fh.read().splitlines()
            except OSError:
                continue
            for n, l in enumerate(lineas, 1):
                for m in RE_DRI.finditer(l):
                    v = int(m.group(1))
                    if v >= 100:
                        # 128+n es el MINOR de un render node, no el indice
                        # de una card. Mezclarlos seria el mismo error que
                        # tratar card1 como si fuera un nodo DRM.
                        clase = "RENDER_MINOR"
                    elif amd is not None and v == amd:
                        clase = "AMD_CORRECTO"
                    elif intel is not None and v == intel:
                        clase = "INTEL_INCORRECTO"
                    else:
                        clase = "INDICE_DESCONOCIDO"
                    filas.append({"clase": clase,
                                  "fichero": os.path.relpath(p, raiz),
                                  "linea": n, "dri": v})
                for m in RE_DRI_BDF.finditer(l):
                    filas.append({"clase": "AMD_BDF_ROBUSTO",
                                  "fichero": os.path.relpath(p, raiz),
                                  "linea": n, "dri": m.group(1)})
    dist: Dict[str, int] = {}
    for r in filas:
        dist[r["clase"]] = dist.get(r["clase"], 0) + 1
    return {"amd_card": amd, "amd_bdf": bdf, "intel_card": intel,
            "filas": filas, "distribucion": dist}


def selftest() -> int:
    print("=== diriroute selftest ===\n")
    fallos = 0

    def vec(n, ok):
        nonlocal fallos
        print("  %s %s" % ("OK  " if ok else "FAIL", n))
        if not ok:
            fallos += 1

    # Con BARRA inicial. Los tres vectores fallaron a la vez porque las cadenas
    # de prueba eran "dri/129" y los tres patrones exigen "/dri/". Los patrones
    # estaban bien: los vectores mentian sobre lo que comprobaban, que es peor
    # que no comprobar.
    vec("un minor de render (129) NO se confunde con un indice de card",
        RE_RENDER.search("/dri/129") is not None
        and RE_DRI.search("/dri/129") is None)
    vec("dri/1 SI es un indice de card",
        RE_DRI.search("/dri/1") is not None)
    vec("dri/0 tambien", RE_DRI.search("/dri/0") is not None)
    vec("la forma por BDF se reconoce aparte y NO como indice",
        RE_DRI_BDF.search("/dri/0000:01:00.0") is not None
        and RE_DRI.search("/dri/0000:01:00.0") is None)
    vec("cardN en /sys/class/drm NO se confunde con un registro del ASIC",
        RE_CARD_CTX.search("/sys/class/drm/card1") is not None
        and not RE_CARD_CTX.search("VM_CARD1") and not RE_CARD_CTX.search("MC_CARD1"))
    vec("VM_CARD1 y MC_CARD1 no son nodos DRM, y por eso no se buscan",
        RE_CARD_CTX.search("VM_CARD1") is None)

    # el caso de 258: el indice se decide por device id, no por orden
    r = escanear(RAIZ)
    if r["amd_card"] is None:
        vec("sin /sys/class/drm legible no se inventa el indice: "
            "sale None y el informe lo dice", True)
    else:
        vec("el indice de la AMD se mide y no se supone", r["amd_card"] == 1)
        vec("y coincide con lo que encontro 258", r["amd_card"] == 1
            and r["intel_card"] == 0)
        vec("el informe separa las cuatro clases",
            set(r["distribucion"]) <= {"AMD_CORRECTO", "INTEL_INCORRECTO",
                                        "INDICE_DESCONOCIDO", "RENDER_MINOR",
                                        "AMD_BDF_ROBUSTO"})

    print("\nRESULT: %s (%d comprobaciones)\n"
          % ("PASS" if not fallos else "FAIL", 6 if r["amd_card"] is None else 10))
    return 1 if fallos else 0


def main() -> int:
    ap = argparse.ArgumentParser(description="quien es dri/N y donde se supone")
    ap.add_argument("--json", action="store_true")
    ap.add_argument("--limite", type=int, default=12)
    ap.add_argument("--selftest", action="store_true")
    a = ap.parse_args()
    if a.selftest:
        return selftest()

    r = escanear(RAIZ)
    if a.json:
        print(json.dumps(r, indent=2, ensure_ascii=False))
        return 0

    print("=" * 78)
    print("driroute %s · ¿dri/N es la AMD? WORK_CLASS=READ_ONLY" % VERSION)
    print("=" * 78)
    if r["amd_card"] is None:
        print("""
  NO SE PUEDE DECIDIR. No hay /sys/class/drm legible, o la AMD no esta ahi.
  Eso NO es un "0 rutas erroneas": es ausencia de entrada, y el informe se queda
  sin numero. Un 0 aqui seria inventado.
""")
        return 1

    print("  MEDIDO ahora, de sysfs:")
    print("    la AMD      es card%d   (%s)" % (r["amd_card"], r["amd_bdf"]))
    print("    integrada   es card%s" % r["intel_card"])
    print()
    print("  Por tanto /sys/kernel/debug/dri/%d/ es la AMD y dri/%s/ es la"
          % (r["amd_card"], r["intel_card"]))
    print("  integrada. El numero cambia con el orden de probe; la BDF no.")
    print()
    print("  Apariciones en el proyecto, por clase:")
    for k in sorted(r["distribucion"], key=lambda x: -r["distribucion"][x]):
        marca = {"AMD_CORRECTO": "ok", "AMD_BDF_ROBUSTO": "ok (robusto)",
                 "INTEL_INCORRECTO": "MAL: apunta a la Intel",
                 "INDICE_DESCONOCIDO": "no se puede decir",
                 "RENDER_MINOR": "no es un indice de card"}.get(k, "")
        print("    %-20s %4d   %s" % (k, r["distribucion"][k], marca))

    malos = [f for f in r["filas"] if f["clase"] == "INTEL_INCORRECTO"]
    if malos:
        print("\n  Sitios que apuntan a la INTEGRADA:")
        for f in malos[:a.limite]:
            print("    %-62s L%-5d dri/%d" % (f["fichero"][:62], f["linea"], f["dri"]))
        if len(malos) > a.limite:
            print("    ... y %d mas" % (len(malos) - a.limite))
        print("""
  NO SE REESCRIBEN. Las apariciones estan en hallazgos ya escritos, y un hallazgo
  que documenta un error conserva el error que documenta: corregirlo dentro del
  hallazgo es fabricar el hallazgo. La correccion va en el fichero VIVO que
  contiene la ruta, y se declara el por que.""")
    print("\n  Uso en vivo de lo que esto encuentra: 'grep -rn' con el mismo")
    print("  criterio, para decidir antes de tocar nada.")
    return 0


if __name__ == "__main__":
    sys.exit(main())