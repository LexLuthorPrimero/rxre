#!/usr/bin/env python3
"""W6 — PCIe accesible (lspci)."""
import sys, os, shutil, subprocess
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '../..')))

def test_w6_pcie():
    assert shutil.which("lspci") is not None
    out = subprocess.run(["lspci"], capture_output=True, text=True, timeout=15)
    assert out.returncode == 0
    lines = out.stdout.strip().split("\n")
    assert len(lines) >= 1, "lspci no listó dispositivos"
    print("W6 PASS (lspci %d líneas)" % len(lines))
