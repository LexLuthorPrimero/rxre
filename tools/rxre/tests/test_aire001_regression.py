#!/usr/bin/env python3
import sys, tempfile, os; sys.path.insert(0,"tools/rxre")
from api.machine import _handle_discover, _handle_experiment

def test_discover_artefacto_valido():
    with tempfile.NamedTemporaryFile(suffix=".bin", delete=False) as f:
        f.write(b"\x7fELF\x00")
        path = f.name
    try:
        resp = _handle_discover({"op":"discover","artefacto":path})
        assert resp.get("status") in ("ok","empty","blocked")
        print("AIRE-1 PASS: discover con artefacto valido")
    finally:
        os.unlink(path)
    return True

def test_discover_artefacto_ausente():
    resp = _handle_discover({"op":"discover","artefacto":"/ruta/noexiste"})
    assert resp.get("status") == "blocked"
    assert resp.get("precheck") is not None and resp["precheck"]["ok"] is False
    print("AIRE-1 PASS: discover ausente -> blocked + precheck")
    return True

def test_experiment_artefacto_ausente():
    resp = _handle_experiment({"op":"experiment","capability":"fake","question":"q","prediction":"p","baseline_params":{"artefacto":"/inexistente"}})
    assert resp.get("status") in ("blocked","invalid_input")
    print("AIRE-1 PASS: experiment ausente -> bloqueado")
    return True

def test_experiment_sin_artefacto():
    resp = _handle_experiment({"op":"experiment","capability":"test.ok","question":"q","prediction":"p"})
    assert resp.get("status") in ("ok","empty")
    print("AIRE-1 PASS: experiment sin artefacto -> sin regresión")
    return True

if __name__ == "__main__":
    for f in [test_discover_artefacto_valido, test_discover_artefacto_ausente, test_experiment_artefacto_ausente, test_experiment_sin_artefacto]:
        try: f(); res = True
        except Exception as e: print("FAIL:", f.__name__, e); res = False
        if res: print(f.__name__, "PASS")
