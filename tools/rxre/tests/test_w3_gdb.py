#!/usr/bin/env python3
"""W3 — gdb (runtime.trace disponible)."""
import sys, os, subprocess, shutil
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '../..')))

def test_w3_gdb_presente():
    assert shutil.which("gdb") is not None
    out = subprocess.run(["gdb", "--version"], capture_output=True, text=True)
    assert out.returncode == 0
    print("W3 PASS (gdb %s)" % out.stdout.splitlines()[0][:40])

def test_w3_adapters_tiene_trace():
    from backends.dispatch import ADAPTERS
    assert "runtime.trace" in ADAPTERS, "runtime.trace no declarado"
