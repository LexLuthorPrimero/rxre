#!/usr/bin/env python3
"""W4 — memoria accesible (gdb + /proc)."""
import sys, os, shutil
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '../..')))
from pathlib import Path

def test_w4_proc_maps():
    assert shutil.which("gdb") is not None
    assert Path("/proc/self/maps").exists()
    assert Path("/proc/self/mem").exists()
    print("W4 PASS (/proc/self/maps y /proc/self/mem accesibles)")
