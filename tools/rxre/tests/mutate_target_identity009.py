#!/usr/bin/env python3
# SPDX-License-Identifier: GPL-2.0
"""Isolated mutation tests for the RXRE-009 PCI identity regression.

Copies the core and the independent fixture test to /tmp/opencode; never edits
live RXRE files. A mutation counts only if it imports and fails an assertion.
"""
import ast
import os
from pathlib import Path
import shutil
import subprocess
import sys
import tempfile

ROOT = Path(__file__).resolve().parents[1]
SOURCE = (ROOT / "core" / "target.py").read_text(encoding="utf-8")
TEST = ROOT / "tests" / "test_target_identity009.py"

MUTATIONS = {
    "M1_restore_fallback": (
        "    return _get_target_from_pci(pci_sys_path)\n",
        "    return _get_target_from_pci(pci_sys_path) or TargetIdentity(\n"
        "        vendor='1002', device='699f', revision='c7',\n"
        "        asic='Polaris12', gfx_generation='gfx_8_0')\n"),
    "M2_wrong_BDF": ('EXPECTED_BDF = "0000:01:00.0"',
                     'EXPECTED_BDF = "0000:00:01.0"'),
    "M3_default_revision": ('    revision = _pci_hex(node, "revision", 2)',
                            '    revision = "c7"'),
    "M4_hide_missing_provenance": (
        '("NOT_OBSERVED" if value == "unknown" else f"0x{value}")',
        'f"0x{value}"'),
    "M5_ignore_subsystem": (
        '    if subdevice not in ("unknown", EXPECTED_SUBSYSTEM[1]):\n        return None',
        '    if False:\n        return None'),
    "M6_route_partial": ('    if target.bdf != "unknown" and (',
                         '    if False and ('),
}


def check(source):
    ast.parse(source)
    with tempfile.TemporaryDirectory(dir="/tmp/opencode", prefix="rxre009-") as tmp:
        dst = Path(tmp)
        (dst / "core").mkdir()
        (dst / "tests").mkdir()
        for name in ("__init__.py", "capabilities.py"):
            shutil.copyfile(ROOT / "core" / name, dst / "core" / name)
        (dst / "core" / "target.py").write_text(source, encoding="utf-8")
        shutil.copyfile(TEST, dst / "tests" / TEST.name)
        env = dict(os.environ, PYTHONDONTWRITEBYTECODE="1")
        smoke = subprocess.run([sys.executable, "-B", "-c", "import core.target"],
                               cwd=dst, env=env, capture_output=True, text=True,
                               timeout=10)
        if smoke.returncode:
            raise RuntimeError("mutant did not import: " + smoke.stderr)
        return subprocess.run([sys.executable, "-B", str(dst / "tests" / TEST.name), "-v"],
                              cwd=dst, env=env, capture_output=True, text=True,
                              timeout=20)


def main():
    baseline = check(SOURCE)
    if baseline.returncode:
        print("INVALID baseline:\n" + baseline.stderr)
        return 2
    killed = 0
    for name, (before, after) in MUTATIONS.items():
        if SOURCE.count(before) != 1:
            print(f"INVALID {name}: mutation site count={SOURCE.count(before)}")
            return 2
        result = check(SOURCE.replace(before, after, 1))
        if result.returncode != 1 or "FAIL:" not in result.stderr:
            print(f"INVALID/SURVIVED {name}: rc={result.returncode}\n{result.stderr}")
            return 1
        killed += 1
        print(f"KILLED {name}")
    print(f"mutation: {killed}/{len(MUTATIONS)} killed, 0 survivors")
    return 0


if __name__ == "__main__":
    sys.exit(main())
