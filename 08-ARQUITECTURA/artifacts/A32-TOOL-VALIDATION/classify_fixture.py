#!/usr/bin/env python3
"""AGENT-32 A32-2: clasifica el FIXTURE de cada selftest.

POR QUE ESTA MEDICION
---------------------
`implgate.py` resulto ROJO y hubo que descubrir que la herramienta era
correcta y su FIXTURE estaba acoplado al corpus vivo: el vector espera que
"999" no exista, y el corpus ya llego a 999. Un selftest asi no es
reproducible: su valor esperado depende de estado mutable del proyecto, y
cualquier otro agente que escriba un hallazgo lo pone rojo sin haber tocado
la herramienta.

Esta pregunta --¿el selftest construye su propio mundo o lee el mio?-- es
distinta de "¿el selftest pasa?", que ya mide TOOLS-STATUS.md, y es la que
decide si ese "VALIDATED" significa algo.

LIMITACION DECLARADA (no la escondo)
------------------------------------
Esto es CLASIFICACION ESTATICA, no ejecucion. Leo el cuerpo de la funcion
selftest y busco dos firmas:
    HERMETICO   crea un directorio temporal propio (tempfile/mkdtemp/tmpdir)
    VIVO        lee rutas del proyecto real (RAIZ/ROOT_SELFTEST/proyecto()/
                findings/ o ficheros del repo) sin directorio temporal
Si no veo ninguna de las dos, es INDETERMINADO: no lo cuento como nada.
Un INDETERMINADO no es un VERDE. Es laabsence de evidencia, que es lo unico
que la honestidad permite afirmar aqui.
"""
import ast
import json
import os
import re

TOOLS = "/home/lucas/Escritorio/RX550-INVESTIGACION/tools"
OUT = "/tmp/opencode/rx550/a32/fixture-clasificacion.json"

HERMETICO_RX = re.compile(r"tempfile|mkdtemp|TemporaryDirectory|mkstemp|tmpdir|scratch|SCRATCH")
VIVO_RX = re.compile(
    r"\bRAIZ\b|ROOT_SELFTEST|proyecto\(\)|findings|06-INGENIERIA|"
    r"AGENTS\.md|EVIDENCE-MATRIX|OPEN-FRONTIERS|NEGATIVE-RESULTS|"
    r"CURRENT-STATE|os\.path\.dirname\(os\.path\.abspath\(__file__\)\)"
)


def cuerpo_selftest(path):
    """Devuelve el texto de la funcion selftest, o None si no hay."""
    txt = open(path, encoding="utf-8", errors="replace").read()
    m = re.search(r"^def selftest\w*\s*\(", txt, re.M)
    if not m:
        return None
    # desde el def hasta el siguiente def de nivel superior
    n = re.search(r"^def \w+", txt[m.end():], re.M)
    fin = m.end() + n.start() if n else len(txt)
    return txt[m.start():fin]


def main():
    filas = []
    for name in sorted(os.listdir(TOOLS)):
        if not name.endswith((".py", ".sh")):
            continue
        p = os.path.join(TOOLS, name)
        try:
            cuerpo = cuerpo_selftest(p)
        except Exception as e:                       # noqa: BLE001
            filas.append({"herramienta": name, "fixture": "ERROR",
                          "detalle": "no se pudo aislar selftest: %s" % e})
            continue
        if cuerpo is None:
            filas.append({"herramienta": name, "fixture": "SIN_SELFTEST",
                          "detalle": "no hay def selftest*"})
            continue
        herm = bool(HERMETICO_RX.search(cuerpo))
        vivo = bool(VIVO_RX.search(cuerpo))
        if herm and not vivo:
            fx = "HERMETICO"
        elif vivo and not herm:
            fx = "ACOPLADO_AL_CORPUS"
        elif herm and vivo:
            fx = "MIXTO"
        else:
            fx = "INDETERMINADO"
        filas.append({
            "herramienta": name, "fixture": fx,
            "bytes_selftest": len(cuerpo),
            "detalle": "temp=%s vivo=%s" % (herm, vivo),
        })

    from collections import Counter
    c = Counter(f["fixture"] for f in filas)
    with open(OUT, "w") as f:
        json.dump({"limitacion": "clasificacion ESTATICA del cuerpo de selftest; "
                                "no prueba ejecucion",
                   "clasificacion": c, "filas": filas}, f, indent=2)

    print("herramientas .py/.sh : %d" % len(filas))
    for k, v in sorted(c.items()):
        print("  %-22s %d" % (k, v))
    print()
    print("=== las acopladas al corpus (el vector puede expirar solo) ===")
    for f in filas:
        if f["fixture"] in ("ACOPLADO_AL_CORPUS", "MIXTO"):
            print("  %-26s %s" % (f["herramienta"], f["fixture"]))
    print("\nartefacto: %s" % OUT)


if __name__ == "__main__":
    main()
