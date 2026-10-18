#!/usr/bin/env python3
"""Discriminative test for bottleneck: plan ignores root_cause."""
import sys; sys.path.insert(0, "tools/rxre")
from api.machine import _handle_plan

def test_plan_ignores_root_cause():
    # Plan evalúa pasos sin mirar root_cause del paso anterior
    mission = {
        "id": "m-escala-001",
        "objetivo": "verificar unsupported",
        "steps": [{"op":"run", "capability":"rea.inspect_firmware", "args":{"artefacto":"/fake"}}],
    }
    # Simular que el paso anterior produjo unsupported + root_cause
    prev = {"op":"run", "status":"unsupported", "root_cause":{"tipo":"unsupported_backend", "motivo":"capacidad no soportada"}, "reflexion_sugerida":{"outcome":"failure"}}
    # _handle_plan debería consultar prev; si no lo hace, el cuello es confirmados
    resp = _handle_plan({"mission": mission, "prev_step": prev, "step_index": 0})
    # Si plan no menciona root_cause ni ajusta feasibility, el defecto está demostrado
    plan_text = str(resp)
    has_causal = "root_cause" in plan_text or "unsupported" in plan_text or "infraestructura" in plan_text
    assert not has_causal, f"Plan debería ignorar root_cause por diseño actual, confirmando cuello: {plan_text[:200]}"
    print("CUELLO CONFIRMADO: plan no incorpora root_cause -> siguiente paso no ajustado")
    return True

def test_plan_recibe_causa_prev_step():
    resp = _handle_plan({"capability":"test.cap","prev_step":{"status":"unsupported","root_cause":{"nodo":"dispatch","tipo":"unsupported_backend"},"motivo":"no soportada"}})
    assert "retroalimentacion_causa" in resp, f"AIRE-001: plan debe recibir causa: {resp.keys()}"
    assert resp["retroalimentacion_causa"]["causa"]["status"] == "unsupported"
    assert "nota" in resp["retroalimentacion_causa"]
    print("AIRE-001 PASS: plan recibe retroalimentacion causal sin bloquear")
    return True

if __name__ == "__main__":
    test_plan_ignores_root_cause()
