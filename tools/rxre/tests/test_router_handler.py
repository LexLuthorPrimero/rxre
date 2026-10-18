#!/usr/bin/env python3
"""ROUTER: mapa estatico ADAPTERS."""
from __future__ import annotations
import os, sys
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

fails = []
n = 0
def v(nombre, cond, det=""):
    global n; n += 1
    if not cond: fails.append("%s %s" % (nombre, det))
    print("  %s %s" % ("PASS" if cond else "FAIL", nombre))

import api.machine as machine

v("R1.1 router en HANDLERS", "router" in machine.HANDLERS)
r = machine._handle_router({"capability": "binary.functions"})
v("R1.2 resolve ok", r.get("status") == "ok")
print("  ROUTER = PARTIAL (mapa estatico, sin resolve real por cap)")
print("  PASS: %d FAIL: %d" % (n - len(fails), len(fails)))
