#!/usr/bin/env python3
# SPDX-License-Identifier: GPL-2.0
"""RXRE-015 mutation testing de CONFLICT con nivel CONSUMER.

El oraculo de test_p0_2_consumer015.py es el MODELO de referencia, construido
desde la fuente del kernel.  Las mutaciones atacan al propio test,  que es la
unica forma de demostrar que sus aserciones no son vacias.

Las clases del encargo:
  ignorar target · ignorar lineage · eliminar TU context · eliminar consumer
  context · mezclar consumers · convertir disagreement en conflict · ocultar
  conflict real · elegir primer candidato

Y una no pedida que el dato obliga:  ignorar que el #define de la propia TU
tiene precedencia sobre el de cualquier cabecera.

Todas las mutaciones caen dentro de UN SOLO clasificador (`clasificar`)  o de
las funciones de las que depende.  Esa unificacion no es cosmetica:  con dos
implementaciones,  M5 y M8 sobrevivian porque cambiaban una y las aserciones
miraban la otra.
"""
import ast
import os
import shutil
import subprocess
import sys
import tempfile
from pathlib import Path

ROOT = Path(__file__).resolve().parents[3]
TEST_REL = "tools/rxre/tests/test_p0_2_consumer015.py"
FUENTE = (ROOT / TEST_REL).read_text(encoding="utf-8")

CLAS_AMB = '    if ambig:\n        return "CONFLICT_INTRA_TU"'
CLAS_NOCONS = '    if not cons:\n        return "APLICABLE_SIN_CONSUMER"'
CLAS_NOVALS = '    if len(vals) > 1:\n        return "DISACUERDO_ENTRE_CONSUMERS"'
LOCA_GANA = ('            if s in propio:\n'
             '                continue')
VE_INCL = ('    for h in sorted(includes_de(tu, cab)):')
TARGET = ('                if re.search(r"\\b%s\\b" % chip, txt(p)):\n'
          '                    out.append(p)')

MUTACIONES = {
    # target / lineage
    "M1_target_ignorado": (TARGET, "                out.append(p)"),
    "M2_chip_no_resuelto": (
        "def chip_del_dispositivo(vendor, device):\n    for a, b, c in",
        'def chip_del_dispositivo(vendor, device):\n    return "CHIP_VEGA10"\n'
        "    for a, b, c in"),

    # TU context
    "M3_tu_context_eliminado": (VE_INCL, "    for h in sorted(cab)[:1]:"),
    "M4_primer_candidato_global": (
        "            if s in ve and ve[s] != v:\n"
        '                ambigua.append({"simbolo": s, "valor_previo": ve[s],\n'
        '                                "valor_nuevo": v, "cabecera": h})\n'
        "            ve.setdefault(s, v)",
        "            ve[s] = v\n            break"),

    # consumer context
    "M5_consumer_context_eliminado": (
        CLAS_NOCONS,
        '    if False:\n        return "APLICABLE_SIN_CONSUMER"'),

    # mezclar consumers:  el valor de cualquier cabecera cuenta como visto
    "M6_mezclar_consumers": (
        '    vals = {ve[p][s] for p in cons if p in ve and s in ve[p]}',
        '    vals = {ve[p][s] for p in cons if p in ve and s in ve[p]}\n'
        '    vals |= {v for h, v in defs.get(s, {}).items()}'),

    # disagreement -> conflict
    "M7_disagreement_es_conflict": (
        CLAS_NOCONS,
        '    if len({v for h, v in defs.get(s, {}).items()}) > 1:\n'
        '        return "CONFLICT_INTRA_TU"\n'
        + CLAS_NOCONS),

    # ocultar conflict real
    "M8_conflict_oculto": (CLAS_AMB, "    if False:\n"
                           '        return "CONFLICT_INTRA_TU"'),

    # precedencia del #define local
    "M9_define_local_ignorado": (
        LOCA_GANA,
        '            if s in propio and False:\n'
        '                continue'),

    # y la regla que mas se cuela:  tratar el desacuerdo global como conflicto
    # entre consumers
    "M10_acuerdo_global_por_consumer": (
        CLAS_NOVALS,
        '    if len({v for h, v in defs.get(s, {}).items()}) > 1:\n'
        '        return "DISACUERDO_ENTRE_CONSUMERS"\n' + CLAS_NOVALS),
}


def monta(dst: Path, fuente: str) -> None:
    shutil.copytree(ROOT / "tools/rxre", dst / "tools/rxre",
                    ignore=shutil.ignore_patterns("__pycache__", "github",
                                                  "storage"),
                    dirs_exist_ok=True)
    shutil.copy(ROOT / "tools/reg_resolve.py", dst / "tools/reg_resolve.py")
    (dst / "RESEARCH").symlink_to(ROOT / "RESEARCH")
    (dst / TEST_REL).write_text(fuente, encoding="utf-8")


def corre(fuente: str):
    ast.parse(fuente)
    with tempfile.TemporaryDirectory(dir="/tmp/opencode", prefix="mut15-") as tmp:
        dst = Path(tmp)
        monta(dst, fuente)
        return subprocess.run(
            [sys.executable, "-B", str(dst / TEST_REL)],
            cwd=dst, capture_output=True, text=True, timeout=1800,
            env=dict(os.environ, PYTHONDONTWRITEBYTECODE="1"))


def main():
    base = corre(FUENTE)
    if base.returncode != 0:
        print("INVALID baseline: el modelo debe pasar sus aserciones")
        print(base.stdout[-3000:])
        return 2
    muertos = 0
    for nombre, (antes, despues) in MUTACIONES.items():
        c = FUENTE.count(antes)
        if c != 1:
            print("INVALID %s: sitio count=%d (se requiere 1)" % (nombre, c))
            return 2
        p = corre(FUENTE.replace(antes, despues, 1))
        if p.returncode == 0:
            print("SURVIVED %s   <-- hueco real" % nombre)
            continue
        malos = [l.strip() for l in p.stdout.splitlines() if l.startswith("  [NO ")]
        muertos += 1
        print("KILLED   %-30s %s" % (nombre, (malos[0][6:62] if malos
                                              else "rc=%d" % p.returncode)))
    print("\nmutation: %d/%d killed, %d survivors"
          % (muertos, len(MUTACIONES), len(MUTACIONES) - muertos))
    return 0 if muertos == len(MUTACIONES) else 1


if __name__ == "__main__":
    sys.exit(main())