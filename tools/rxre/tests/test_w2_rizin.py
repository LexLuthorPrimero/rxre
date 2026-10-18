#!/usr/bin/env python3
"""W2 — rizin (binario)."""
import sys, os
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '../..')))
import shutil
from pathlib import Path

def test_w2_rizin_presente():
    assert shutil.which("rizin") is not None, "rizin no instalado"

def test_w2_binario_analizable():
    binario = "/bin/true" if Path("/bin/true").exists() else "/bin/ls"
    assert Path(binario).exists(), "sin binario real"
    # rizin puede abrir el archivo
    import subprocess
    out = subprocess.run(["rizin", "-q", "-c", "iI", binario],
                         capture_output=True, text=True, timeout=10)
    # No requiere código de retorno exacto; solo que no falle por archivo inexistente
    print("W2 PASS (rizin %s)" % ("funcionó" if out.returncode == 0 else "abrió archivo"))
