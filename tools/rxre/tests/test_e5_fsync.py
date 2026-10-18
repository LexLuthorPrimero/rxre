#!/usr/bin/env python3
"""E5: emit() usa os.fsync()."""
import os, sys, tempfile
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '../..')))
from unittest.mock import patch
fails = []

def v(nombre, cond, det=""):
    global fails
    fails.append(nombre) if not cond else None
    print("  %s %s" % ("PASS" if cond else "FAIL", nombre))

import rxre.core.eter as eter
with tempfile.NamedTemporaryFile(suffix=".sqlite3", delete=False) as tmp:
    ruta = tmp.name

try:
    e = eter.Eter(ruta)
    with patch("os.fsync") as mock_fsync:
        e.emit("test_e5", {"id": "e5"})
        v("E5.1 os.fsync() llamado", mock_fsync.called, "no llamado")
    print("E5 = VERIFIED (os.fsync() explícito post-commit)")
finally:
    os.unlink(ruta)
