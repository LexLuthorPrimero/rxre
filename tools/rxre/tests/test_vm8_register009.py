#!/usr/bin/env python3
# SPDX-License-Identifier: GPL-2.0
"""Independent GFX8 VMID8 register oracle for RXRE-009.

The numeric fixture is checked against the actual included GMC header and the
reg*4 consumer. The RXRE envelope cannot be its own expected-value producer.
"""
import json
import os
from pathlib import Path
import re
import subprocess
import sys
import unittest

ROOT = Path(__file__).resolve().parents[3]
AMD = ROOT / "RESEARCH/working/linux-7.1.3/drivers/gpu/drm/amd"
HEADER = AMD / "include/asic_reg/gmc/gmc_8_1_d.h"
GMC = AMD / "amdgpu/gmc_v8_0.c"
ACCESS = AMD / "amdgpu/amdgpu_reg_access.c"
CLI = ROOT / "tools/rxre/rxre"


class VM8Register(unittest.TestCase):
    def test_source_and_rxre_agree_on_index_and_units(self):
        header = HEADER.read_text()
        gmc = GMC.read_text()
        access = ACCESS.read_text()
        def index(symbol):
            m = re.search(r"^#define\s+" + symbol + r"\s+(0x[0-9a-fA-F]+)\s*$",
                          header, re.M)
            self.assertIsNotNone(m, symbol)
            return int(m.group(1), 16)

        self.assertEqual(index("mmVM_CONTEXT8_PAGE_TABLE_BASE_ADDR"), 0x50e)
        self.assertEqual(index("mmVM_CONTEXT0_PAGE_TABLE_START_ADDR"), 0x557)
        self.assertIn('#include "gmc/gmc_8_1_d.h"', gmc)
        self.assertRegex(gmc, r"reg\s*=\s*mmVM_CONTEXT8_PAGE_TABLE_BASE_ADDR\s*\+\s*vmid\s*-\s*8")
        self.assertRegex(access, r"readl\(.*rmmio\).*\(reg\s*\*\s*4\)")

        env = dict(os.environ, PYTHONDONTWRITEBYTECODE="1")
        run = subprocess.run([sys.executable, "-B", str(CLI), "register",
                              "mmVM_CONTEXT8_PAGE_TABLE_BASE_ADDR", "--gfx", "gfx_8_0",
                              "--timeout", "40"], cwd=ROOT, env=env,
                             capture_output=True, text=True, timeout=50)
        self.assertEqual(run.returncode, 0, run.stderr)
        data = json.loads(run.stdout)
        self.assertEqual(data["status"], "ok")
        self.assertEqual(len(data["results"]), 1)
        result = data["results"][0]
        self.assertEqual(result["verdict"], "DEFINIDO_EN_GENERACION_OBJETIVO")
        self.assertEqual(result["chosen"]["rel"], "include/asic_reg/gmc/gmc_8_1_d.h")
        self.assertEqual(int(result["value"], 16), index("mmVM_CONTEXT8_PAGE_TABLE_BASE_ADDR"))
        self.assertEqual(result["dword_index"], "0x50e")
        self.assertEqual(result["byte_offset"], "0x1438")
        self.assertIn("dword", result["unit"])


if __name__ == "__main__":
    unittest.main()
