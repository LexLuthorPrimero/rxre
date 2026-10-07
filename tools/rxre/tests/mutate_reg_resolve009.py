#!/usr/bin/env python3
# SPDX-License-Identifier: GPL-2.0
"""RXRE-009 mutation tests for reg_resolve unit and selection mechanism.

Baseline is the P0.3 suite plus the independent VM8 oracle, both run against a
throwaway copy of tools/ under /tmp/opencode. A mutation counts only if the
mutant imports and makes an assertion fail.
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
    "M1_unit_divide_by_four": ('out["byte_offset"] = hex(val * 4) if val is not None else None',
                               'out["byte_offset"] = hex(val >> 2) if val is not None else None'),
    "M2_claim_byte_offset": ('out["unit"] = "dword register index (GFX8 MMIO consumer)"',
                            'out["unit"] = "byte offset (contrato del kernel)"'),
    "M3_drop_borrowed_header": ('            order.append(os.path.join(base_dir, "gmc", m.group(1)))',
                                '            order.append(os.path.join(base_dir, "gmc", "gmc_9_0_d.h"))'),
    # NOTA MEDIDA: el sitio `if "selection_evidence" not in out` no es un
    # banco de pruebas con este corpus. Con el grafo de includes real, todo
    # header que entra en `in_target` esta incluido por el consumidor, asi que
    # esa rama no puede dispararse; una mutacion ahi sobrevive por
    # construccion y no demuestra nada. Se sustituye por la supresion del
    # conflicto, que si es alcanzable.
    "M4_suppress_conflict": ("    if len(unique_values) > 1:",
                             "    if len(unique_values) > 99:"),
    "M5_ignore_include_edge": ('            if matches:', '            if False:'),
}


def build(dst, source):
    """Mirror the live layout so parents[3] of the suites is this temp root."""
    (dst / "tools").mkdir()
    shutil.copytree(ROOT / "tools/rxre", dst / "tools/rxre",
                    ignore=shutil.ignore_patterns("__pycache__", "github", "storage"))
    (dst / "RESEARCH").symlink_to(ROOT / "RESEARCH")
    target = dst / "tools/reg_resolve.py"
    target.write_text(source, encoding="utf-8")
    return target


def run(argv, cwd):
    return subprocess.run([sys.executable, "-B"] + argv, cwd=cwd,
                          env=dict(os.environ, PYTHONDONTWRITEBYTECODE="1",
                                   PYTHONPATH=str(cwd / "tools/rxre")),
                          capture_output=True, text=True, timeout=300)


def check(source):
    ast.parse(source)
    with tempfile.TemporaryDirectory(dir="/tmp/opencode", prefix="rxre009-reg-") as tmp:
        cwd = Path(tmp)
        build(cwd, source)
        p003 = run([str(cwd / "tools/rxre/tests/test_p003.py")], cwd)
        vm8 = run([str(cwd / "tools/rxre/tests/test_vm8_register009.py")], cwd)
        return p003, vm8


def main():
    p003, vm8 = check(SOURCE)
    if p003.returncode or vm8.returncode:
        print("INVALID baseline")
        print(p003.stdout[-400:], p003.stderr[-400:])
        print(vm8.stdout[-400:], vm8.stderr[-400:])
        return 2
    killed = 0
    for name, (before, after) in MUTATIONS.items():
        if SOURCE.count(before) != 1:
            print(f"INVALID {name}: mutation site count={SOURCE.count(before)}")
            return 2
        a, b = check(SOURCE.replace(before, after, 1))
        if a.returncode == 0 and b.returncode == 0:
            print(f"SURVIVED {name}")
            return 1
        killed += 1
        print(f"KILLED {name} (p003 rc={a.returncode}, vm8 rc={b.returncode})")
    print(f"mutation: {killed}/{len(MUTATIONS)} killed, 0 survivors")
    return 0


if __name__ == "__main__":
    sys.exit(main())