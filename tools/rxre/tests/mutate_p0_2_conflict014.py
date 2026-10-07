#!/usr/bin/env python3
# SPDX-License-Identifier: GPL-2.0
"""RXRE-014 mutation testing de la semantica de CONFLICT.

El oracle de test_p0_2_conflict014.py es el MODELO de referencia, construido
desde la fuente del kernel.  Por eso las mutaciones atacan al propio test.  Un
mutante cuenta como muerto SOLO si las aserciones lo detectan:  asi se
demuestra que las aserciones no son vacias.

Las siete clases del encargo:
  ignorar target applicability · tratar todos los headers como equivalentes ·
  eliminar lineage filtering · elegir first global candidate ·
  ocultar conflict · borrar candidates · eliminar target provenance

Y una octava, que es la que mas se cuela:  borrar la TRICOTOPIA, y tratar
"no aplicable" como si fuera conflicto.
"""
import ast
import os
import shutil
import subprocess
import sys
import tempfile
from pathlib import Path

ROOT = Path(__file__).resolve().parents[3]
TEST_REL = "tools/rxre/tests/test_p0_2_conflict014.py"
FUENTE = (ROOT / TEST_REL).read_text(encoding="utf-8")

MUTACIONES = {
    # 1 · target applicability ignorada:  todo el corpus es aplicable
    "M1_aplicabilidad_ignorada": (
        '    return sorted({(h, v) for h, v in index.get(sym, []) if h in alcanzable})',
        '    return sorted({(h, v) for h, v in index.get(sym, [])})'),

    # 2 · todos los headers equivalentes:  se exige el token "8_0" en el nombre
    "M2_headers_equivalentes": (
        '            if cand:\n                out.setdefault(cand[0], []).append(p)',
        '            if cand and "8_0" in cand[0]:\n'
        '                out.setdefault(cand[0], []).append(p)'),

    # 3 · lineage filtering eliminado:  el universo de TU es todo el arbol
    "M3_lineage_filtrado_eliminado": (
        '                if re.search(r"\\b%s\\b" % chip, txt(p)):\n'
        '                    out.append(p)',
        '                out.append(p)'),

    # 4 · first global candidate:  elegir el primero sin mirar aplicabilidad
    "M4_primer_candidato_global": (
        '    return sorted({(h, v) for h, v in index.get(sym, []) if h in alcanzable})',
        '    hits = index.get(sym, [])\n'
        '    return sorted(hits)[:1] and [sorted(hits)[0]] or []'),

    # 5 · conflicto oculto:  nunca se declara
    "M5_conflicto_oculto": (
        '    if len({v for _, v in apl}) > 1:\n        return "CONFLICT", apl, sorted({v for _, v in apl}), None',
        '    if False:\n        return "CONFLICT", apl, sorted({v for _, v in apl}), None'),

    # 6 · candidatos borrados:  CONFLICT sin CANDIDATES
    "M6_candidatos_borrados": (
        '        return "CONFLICT", apl, sorted({v for _, v in apl}), None',
        '        return "CONFLICT", apl, [], None'),

    # 7 · target provenance eliminada:  el chip no sale de la tabla
    "M7_provenance_de_target_eliminada": (
        'def chip_del_dispositivo(vendor, device):\n    for a, b, c in',
        'def chip_del_dispositivo(vendor, device):\n    return None\n    for a, b, c in'),

    # 8 · la tricotomia borrada:  "no aplicable" pasa a ser conflicto
    "M8_no_aplicable_tratado_como_conflicto": (
        '    if not apl:\n        return "NO_APLICABLE", apl, [], None',
        '    if not apl:\n        return "CONFLICT", apl, [], None'),

    # 9 · la unidad se toca:  el valor se deriva por >> 2 en vez de * 4
    "M9_unidad_invertida_en_la_derivacion": (
        '      int(r["byte_offset"], 16) == int(r["dword_index"], 16) * 4,',
        '      int(r["byte_offset"], 16) == int(r["dword_index"], 16) >> 2,'),
}


def monta(dst: Path, fuente: str) -> None:
    shutil.copytree(ROOT / "tools/rxre", dst / "tools/rxre",
                    ignore=shutil.ignore_patterns("__pycache__", "github",
                                                  "storage"),
                    dirs_exist_ok=True)
    (dst / "tools").mkdir(exist_ok=True)
    shutil.copy(ROOT / "tools/reg_resolve.py", dst / "tools/reg_resolve.py")
    (dst / "RESEARCH").symlink_to(ROOT / "RESEARCH")
    (dst / TEST_REL).write_text(fuente, encoding="utf-8")


def corre(fuente: str):
    ast.parse(fuente)
    with tempfile.TemporaryDirectory(dir="/tmp/opencode", prefix="mut14-") as tmp:
        dst = Path(tmp)
        monta(dst, fuente)
        return subprocess.run(
            [sys.executable, "-B", str(dst / TEST_REL)],
            cwd=dst, capture_output=True, text=True, timeout=2400,
            env=dict(os.environ, PYTHONDONTWRITEBYTECODE="1"))


def main():
    base = corre(FUENTE)
    if base.returncode != 0:
        print("INVALID baseline: el modelo debe pasar sus propias aserciones")
        print(base.stdout[-3000:])
        return 2
    muertos = 0
    for nombre, (antes, despues) in MUTACIONES.items():
        n = FUENTE.count(antes)
        if n != 1:
            print("INVALID %s: sitio count=%d (se requiere 1)" % (nombre, n))
            return 2
        p = corre(FUENTE.replace(antes, despues, 1))
        if p.returncode == 0:
            print("SURVIVED %s   <-- hueco real" % nombre)
            continue
        malos = [l.strip() for l in p.stdout.splitlines() if l.startswith("  [NO ")]
        muertos += 1
        print("KILLED   %-38s %s" % (nombre, (malos[0][6:66] if malos
                                              else "rc=%d" % p.returncode)))
    print("\nmutation: %d/%d killed, %d survivors"
          % (muertos, len(MUTACIONES), len(MUTACIONES) - muertos))
    return 0 if muertos == len(MUTACIONES) else 1


if __name__ == "__main__":
    sys.exit(main())