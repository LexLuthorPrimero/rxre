#!/usr/bin/env python3
# SPDX-License-Identifier: GPL-2.0
"""RXRE-ECO-001. `audit`: los ocho principios applied a una operacion REAL.

QUE ES Y QUE NO ES.

NO es un plan de trabajo: no decide que investigar. ES la auditoria de una
operacion que ya se ejecutó, con los ocho principios, y su veredicto decide si
esa operacion queda CERRADA.

POR QUE ES UN SUBCOMANDO Y NO UN CAMPO MAS.

Porque §105 termina en `UPDATE KNOWLEDGE`, y entre `BENCHMARK` y ese punto hay
un hueco que nadie cubre: si la operacion fue correcta. El status `ok` del
producer no dice eso. Un resultado puede ser `ok` y no ser atribuible: eso es
lo que este subcomando se encarga de distinguir.

Y se expone como SUBCOMANDO, no como un `--audit` de `run`, por una razon
operativa: auditar sin ejecutar es barato, y cuando es barato deja de usarse.
Separado, obliga a invocarlo DESPUES de una operacion real.

Uso:
    ./rxre audit --resultado <result_id>
    ./rxre audit --desde-fichero <env.json>
    ./rxre audit --principios              # imprime los 8 y su contrato
"""
from __future__ import annotations

import json
import os
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
RAIZ = os.path.dirname(HERE)
if RAIZ not in sys.path:
    sys.path.insert(0, RAIZ)

from backends.adapters import ocho_principios as OP   # noqa: E402


def _principios() -> int:
    """El catalogo de los ocho, con lo que cada uno EXIGE.

    Se imprime el contrato, no la prosa: que puede fallar y con que se.
    """
    filas = [
        ("CUERPO", "observar la realidad",
         "la operacion ejecuto algo real y verificable",
         "resultados con precheck sin pasar, o sin argv"),
        ("MENTE", "comprender las causas",
         "toda afirmacion lleva su porque y hay control negativo",
         "resultados sin ninguna limitacion declarada"),
        ("ALMA", "mantener el proposito",
         "la operacion responde a una pregunta",
         "estructura sin patron y sin sujeto"),
        ("TIERRA", "anclar el conocimiento",
         "cada afirmacion lleva procedencia y hash de entrada",
         "provenance sin input_hash: no se puede repetir"),
        ("FUEGO", "transformar y experimentar",
         "la transformacion esta declarada y es reaplicable",
         "transformacion sin normalizador identificable"),
        ("AIRE", "preservar el flujo",
         "nada se trunca en silencio",
         "total declarado que no cuadra con la lista publicada"),
        ("AGUA", "adaptarse y aprender",
         "lo aprendido queda persistido y es recuperable",
         "operacion no persistida"),
        ("ETER", "integrar y descubrir",
         "el resultado se conecta, o se declara frontera",
         "dato aislado aprobado como si estuviera enlazado"),
    ]
    print("LOS OCHO PRINCIPIOS — QUE EXIGE CADA UNO Y COMO FALLA")
    print()
    for nombre, verbo, exige, falla in filas:
        print("%-8s %s" % (nombre, verbo))
        print("         exige: %s" % exige)
        print("         falla: %s" % falla)
    print()
    print("CONTRATO DE LA AUDITORIA")
    for k, val in OP.nota_8_principios({}).get("contrato", {}).items():
        print("  %-14s %s" % (k, val))
    print()
    print("  SIN evidencia de que un principio se cumple, su veredicto es")
    print("  `not_proven`, NUNCA `ok`. Un principio que no puede fallar no")
    print("  es un principio: es decoracion.")
    return 0


def _cargar_operacion(ruta: str):
    with open(ruta, encoding="utf-8") as fh:
        return json.load(fh)


def main(argv) -> int:
    args = list(argv)
    if "--principios" in args or not args:
        return _principios()

    ruta = None
    if "--desde-fichero" in args:
        i = args.index("--desde-fichero")
        ruta = args[i + 1] if i + 1 < len(args) else None
    if not ruta:
        print("audit: falta --desde-fichero <env.json> o --principios\n"
              "  Para auditar una operacion guardada por el dispatch.\n"
              "  Ver: ./rxre audit --principios", file=sys.stderr)
        return 2
    if not os.path.isfile(ruta):
        print("audit: no existe %s" % ruta, file=sys.stderr)
        return 2

    try:
        env = _cargar_operacion(ruta)
    except (OSError, json.JSONDecodeError) as e:
        print("audit: no se puede leer %s: %s" % (ruta, e), file=sys.stderr)
        return 1

    # El dispatch ya marco si persistio. Si el fichero no lo dice, NO se
    # asume: se deduce de si hay result_id, y se declara como deducido.
    if "persistido" not in env:
        env["persistido"] = any(
            (r or {}).get("result_id") for r in (env.get("results") or []))

    veredicto = OP.gate(env)
    print(json.dumps(veredicto, indent=2, ensure_ascii=False))
    return 0 if veredicto["operacion_cerrada"] else 2


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
