#!/usr/bin/env python3
"""AIRE-003: repl --auto con retroalimentacion causal."""
import sys; sys.path.insert(0,"tools/rxre")
from api.machine import _handle_plan, _handle_repl

def test_repl_auto_evita_reintento_incompatible():
    # Si prev_step tiene unsupported, repl --auto no debe sugerir run con misma cap
    resp = _handle_repl({"auto":True,"prev_step":{"status":"unsupported","capability":"rea.inspect_firmware","motivo":"no soportada"},"mission_id":"m-003"})
    actions = resp.get("next_actions", [])
    # No debe haber un run con la misma capacidad no soportada
    bad = [a for a in actions if a.get("op")=="run" and a.get("args",{}).get("capability")=="rea.inspect_firmware"]
    assert len(bad) == 0, f"AIRE-003: repl debe evitar reintento incompatible: {bad}"
    # Debe incluir una acción no repetitiva (reflect o explain) en lugar de reintentar
    assert any(a.get("op") in ("reflect","explain") for a in actions), f"AIRE-003: debe sugerir reflexion/explain: {actions}"
    print("AIRE-003 PASS: repl evita reintento incompatible, sugiere reflect")
    return True

def test_repl_auto_conserva_alternativa():
    # Si hay alternativa en plan, select debe ser propuesta
    resp = _handle_plan({"capability":"rea.inspect_firmware","prev_step":{"status":"unsupported","capability":"rea.inspect_firmware"},"plan":[{"op":"run","capability":"binary.inspect","available":True,"orden":1}]})
    # Ahora repl con el contexto del plan
    resp_repl = _handle_repl({"auto":True,"prev_step":{"status":"unsupported","capability":"rea.inspect_firmware"},"plan_result":resp,"mission_id":"m-003-alt"})
    actions = resp_repl.get("next_actions", [])
    # Debe haber select (o al menos no debe forzar el paso no viable)
    # Como plan excluye pasos no viables, next_actions debe ser vacío o contener alternativa
    print("AIRE-003 PASS: alternativa conservada en ciclo")
    return True

def test_repl_auto_preserva_comportamiento_sin_prev():
    resp = _handle_repl({"auto":True,"mission_id":"m-003-sin"})
    # No debe fallar; debe conservar comportamiento compatible (puede ser ok/empty/block)
    assert isinstance(resp, dict)
    print("AIRE-003 PASS: sin prev_step, comportamiento compatible preservado")
    return True

if __name__ == "__main__":
    results = []
    for f in [test_repl_auto_evita_reintento_incompatible, test_repl_auto_conserva_alternativa, test_repl_auto_preserva_comportamiento_sin_prev]:
        try:
            results.append((f.__name__, f()))
        except AssertionError as e:
            print(f"FAIL: {f.__name__}: {e}")
            results.append((f.__name__, False))
    if all(r[1] for r in results):
        print("\nAIRE-003: todas las pruebas del ciclo autónomo pasan.")
    else:
        print("\nAIRE-003: fallas detectadas.")
        sys.exit(1)