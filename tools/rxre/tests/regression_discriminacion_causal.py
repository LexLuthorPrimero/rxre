#!/usr/bin/env python3
"""Regression tests for causal discrimination of next_actions.
A. unsupported -> next_actions incluye reflect con tipo=infraestructura
B. blocked -> semantica bloqueado conservada
C. invalid_input -> semantica invalida conservada
D. error -> no acciones duplicadas
E. ok -> sin regresión
F. persistencia_fallida independiente del estado
"""
import sys, sqlite3, tempfile, os
sys.path.insert(0, "tools/rxre")

from unittest import mock
import api.machine as machine
import backends.dispatch as dispatch

def run_with_status(status, extra=None):
    """Call _handle_run with a mocked dispatch.ejecutar returning `status`."""
    env = {"status": status, "capability": "test.cap", "results": [], "params": {}}
    if extra:
        env.update(extra)
    # El import en machine es: import rxre.backends.dispatch as dispatch
    # Parchear la ruta correcta:
    with mock.patch("rxre.backends.dispatch.ejecutar", return_value=env):
        return machine._handle_run({"capability": "test.cap", "params": {}})

def test_A_unsupported():
    resp = run_with_status("unsupported", extra={"motivo": "capacidad no soportada"})
    actions = resp.get("next_actions", [])
    reflect_actions = [a for a in actions if a.get("op") == "reflect"]
    assert len(reflect_actions) >= 1, f"A: unsupported debe generar reflect: {actions}"
    assert any(a.get("tipo") == "infraestructura" for a in reflect_actions), \
        f"A: unsupported debe marcar tipo=infraestructura: {reflect_actions}"
    assert resp.get("reflexion_sugerida", {}).get("outcome") == "failure", \
        f"A: outcome debe ser failure: {resp.get('reflexion_sugerida')}"
    print("A PASS: unsupported genera reflect con tipo=infraestructura")
    return True

def test_B_blocked():
    resp = run_with_status("blocked", extra={"motivo": "capacidad no permitida"})
    actions = resp.get("next_actions", [])
    assert any(a.get("op") == "reflect" for a in actions), f"B: blocked debe sugerir reflect: {actions}"
    assert resp.get("root_cause") is not None, "B: blocked debe incluir root_cause"
    assert resp.get("reflexion_sugerida", {}).get("outcome") == "failure", \
        f"B: outcome bloqueado={resp.get('reflexion_sugerida')}"
    # blocked NO debe tener tipo=infraestructura
    for a in actions:
        assert a.get("tipo") != "infraestructura", f"B: blocked no debe ser infraestructura: {a}"
    print("B PASS: blocked conserva su semantica")
    return True

def test_C_invalid_input():
    resp = run_with_status("invalid_input", extra={"motivo": "faltan Parametros"})
    actions = resp.get("next_actions", [])
    assert any(a.get("op") == "reflect" for a in actions), f"C: invalid_input sin reflect: {actions}"
    assert resp.get("reflexion_sugerida", {}).get("outcome") == "failure"
    for a in actions:
        assert a.get("tipo") != "infraestructura", f"C: invalid_input no debe ser infraestructura: {a}"
    print("C PASS: invalid_input conserva su semantica")
    return True

def test_D_error():
    resp = run_with_status("error", extra={"motivo": "timeout"})
    actions = resp.get("next_actions", [])
    reflect_actions = [a for a in actions if a.get("op") == "reflect"]
    # Puede haber más de uno (bloqueo de allow-list + error), pero no duplicados idénticos
    assert len(reflect_actions) >= 1, f"D: error debe incluir al menos un reflect: {reflect_actions}"
    # No duplicados exactos (mismo dict)
    for i in range(len(reflect_actions)-1):
        assert reflect_actions[i] != reflect_actions[i+1], "D: reflect duplicado detectado"
    # Error NO debe ser etiquetado como infraestructura
    for a in actions:
        assert a.get("tipo") != "infraestructura", f"D: error no debe ser infraestructura: {a}"
    print("D PASS: error no duplica acciones idénticas ni usa tipo infra")
    return True

def test_E_ok():
    resp = run_with_status("ok", extra={"results": [{"key": "value"}]})
    reflect_actions = [a for a in resp.get("next_actions", []) if a.get("op") == "reflect"]
    assert len(reflect_actions) == 0, f"E: ok no debe sugerir reflect: {reflect_actions}"
    assert resp.get("status") == "ok", f"E: status debe ser ok: {resp.get('status')}"
    print("E PASS: ok sin regresión")
    return True

def test_F_persistencia_fallida():
    resp = run_with_status("unsupported", extra={"persistencia_fallida": True, "motivo": "fallo db"})
    assert resp.get("persistencia_fallida") is True, f"F: persistencia_fallida debe ser True: {resp}"
    assert resp.get("status") == "unsupported", f"F: status debe ser unsupported: {resp.get('status')}"
    print("F PASS: persistencia_fallida independiente del estado")
    return True

if __name__ == "__main__":
    results = []
    for test in [test_A_unsupported, test_B_blocked, test_C_invalid_input, test_D_error, test_E_ok, test_F_persistencia_fallida]:
        try:
            results.append((test.__name__, test()))
        except AssertionError as e:
            print(f"FAIL: {test.__name__}: {e}")
            results.append((test.__name__, False))
    if all(r[1] for r in results):
        print("\nTodas las regresiones pasan.")
    else:
        print("\nAlgunas regresiones fallaron.")
        sys.exit(1)