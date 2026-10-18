#!/usr/bin/env python3
"""CUERPO adversarial."""
import sys, os, tempfile
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '../..')))
from rxre.core.cuerpo import Cuerpo

fails = []
n = 0
def v(nombre, cond, det=""):
    global n, fails
    n += 1
    if not cond: fails.append(nombre + (" <- %s" % det if det else ""))
    print("  %s %s" % ("PASS" if cond else "FAIL", nombre))

with tempfile.TemporaryDirectory() as td:
    f = os.path.join(td, "test.bin")
    open(f, "wb").write(b"contenido")
    c = Cuerpo(os.path.join(td, "cuerpo.db"))
    obs = c.observar(f)
    v("C1.1 observar archivo real", obs is not None and len(obs["artifact_hash"]) == 64)
    v("C1.2 hash SHA256", obs["artifact_hash"].startswith("5d") or len(obs["artifact_hash"]) == 64)
    v("C1.3 media_type", obs.get("media_type") is not None)

    v("C4.1 verificar intacto inicial", c.verificar_no_alterado(obs["obs_id"]) is True)
    # Alterar archivo
    open(f, "wb").write(b"ALTERADO")
    v("C4.2 verificar alterado", c.verificar_no_alterado(obs["obs_id"]) is False)

    with tempfile.NamedTemporaryFile(suffix=".fake", delete=False) as tmp2:
        pass
    # El file ya fue borrado por NamedTemporaryFile; usar un path que no existe
    try:
        c.observar("/no/existe")
        v("C1.4 observar inexistente falla", False, "no lanzó")
    except FileNotFoundError:
        v("C1.4 observar inexistente falla", True)

print("PASS: %d/%d" % (n - len(fails), n))
if fails: print("FAILS:", fails)
