#!/usr/bin/env python3
# SPDX-License-Identifier: GPL-2.0
"""RXRE-012 mutation testing for the P0.1 unit semantics and its warning.

Baseline is test_p003.py plus the independent VM8 oracle, run against a
throwaway copy of tools/ under /tmp/opencode. A mutation counts only if the
mutant imports and makes an assertion fail.

Each mutation targets one of the five required classes:
  UNIDAD, TRANSFORMACION, WARNING, COLISION NO DETECTADA, IDENTIDAD COLAPSADA.
"""
import ast
import os
from pathlib import Path
import shutil
import subprocess
import sys
import tempfile

ROOT = Path(__file__).resolve().parents[3]
SOURCE = (ROOT / "tools/reg_resolve.py").read_text(encoding="utf-8")
VM8 = ROOT / "tools/rxre/tests/test_vm8_register009.py"

MUTATIONS = {
    # ── UNIDAD INCORRECTA ───────────────────────────────────────────────────
    "U1_clase_vuelta_a_byte_offset": (
        'out["unit"] = "dword register index (GFX8 MMIO consumer)"',
        'out["unit"] = "byte offset (contrato del kernel)"'),
    "U2_clase_renombrada": (
        'return "dword_index_de_mm"', 'return "byte_offset_de_mm"'),

    # ── TRANSFORMACION INCORRECTA ──────────────────────────────────────────
    "T1_dividir_en_vez_de_multiplicar": (
        'out["byte_offset"] = hex(val * 4) if val is not None else None',
        'out["byte_offset"] = hex(val >> 2) if val is not None else None'),
    "T2_dword_index_derivado": (
        'out["dword_index"] = hex(val) if val is not None else None',
        'out["dword_index"] = hex(val >> 2) if val is not None else None'),
    "T3_multiplica_por_8": (
        'out["byte_offset"] = hex(val * 4) if val is not None else None',
        'out["byte_offset"] = hex(val * 8) if val is not None else None'),

    # ── WARNING INCORRECTO ──────────────────────────────────────────────────
    "W1_warning_afirma_byte_offset": (
        'out["warning"] = ("value is the dword register index; the MMIO byte "',
        'out["warning"] = ("value IS the byte offset. Doing IO on "'),
    "W2_warning_sin_la_prohibicion": (
        '                          "The value is NOT a byte offset: dividing it by 4 "\n'
        '                          "is not a valid conversion and would name a "\n'
        '                          "different register. "\n',
        ''),
    "W3_warning_sin_la_fuente": (
        '"offset is value * 4 in amdgpu_device_rreg. "', '"offset is value * 4. "'),

    # ── IDENTIDAD COLAPSADA ────────────────────────────────────────────────
    "I1_todos_los_valores_dos": (
        'out["dword_index"] = hex(val) if val is not None else None',
        'out["dword_index"] = hex(val >> 2) if val is not None else None'),

    # ── CONFLICT SUPRIMIDO ──────────────────────────────────────────────────
    "C1_conflict_suprimido": ("    if len(unique_values) > 1:",
                              "    if len(unique_values) > 99:"),
}


def build(dst, source):
    (dst / "tools").mkdir()
    shutil.copytree(ROOT / "tools/rxre", dst / "tools/rxre",
                    ignore=shutil.ignore_patterns("__pycache__", "github", "storage"))
    (dst / "RESEARCH").symlink_to(ROOT / "RESEARCH")
    (dst / "tools/reg_resolve.py").write_text(source, encoding="utf-8")


def run(argv, cwd):
    return subprocess.run([sys.executable, "-B"] + argv, cwd=cwd,
                          env=dict(os.environ, PYTHONDONTWRITEBYTECODE="1",
                                   PYTHONPATH=str(cwd / "tools/rxre")),
                          capture_output=True, text=True, timeout=300)


def check(source):
    ast.parse(source)
    with tempfile.TemporaryDirectory(dir="/tmp/opencode", prefix="rxre012-") as tmp:
        cwd = Path(tmp)
        build(cwd, source)
        p003 = run([str(cwd / "tools/rxre/tests/test_p003.py")], cwd)
        vm8 = run([str(cwd / "tools/rxre/tests/test_vm8_register009.py")], cwd)
        return p003, vm8


def main():
    p003, vm8 = check(SOURCE)
    if p003.returncode or vm8.returncode:
        print("INVALID baseline: el codigo de partida debe estar verde")
        print(p003.stdout[-500:], p003.stderr[-500:])
        print(vm8.stdout[-500:], vm8.stderr[-500:])
        return 2
    killed = 0
    for name, (before, after) in MUTATIONS.items():
        n = SOURCE.count(before)
        if n != 1:
            print(f"INVALID {name}: sitio de mutacion count={n} (se requiere 1)")
            return 2
        a, b = check(SOURCE.replace(before, after, 1))
        if a.returncode == 0 and b.returncode == 0:
            print(f"SURVIVED {name}  <-- hueco real de cobertura")
            continue
        killed += 1
        print(f"KILLED   {name}  (p003 rc={a.returncode}, vm8 rc={b.returncode})")
    total = len(MUTATIONS)
    print(f"\nmutation: {killed}/{total} killed, {total-killed} survivors")
    return 0 if killed == total else 1


if __name__ == "__main__":
    sys.exit(main())