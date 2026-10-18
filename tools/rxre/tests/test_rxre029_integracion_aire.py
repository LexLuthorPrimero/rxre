#!/usr/bin/env python3
"""RXRE-029: 8 casos de integración AIRE (run -> correlation_result)."""
import sys; sys.path.insert(0,"/home/lucas/Escritorio/rxre"); sys.path.insert(0,"/home/lucas/Escritorio/rxre/tools/rxre")
from api.machine import _handle_run

def test_029():
    # 1. Sin correlacion => comportamiento anterior (None)
    r1 = _handle_run({"op":"run","capability":"research"})
    assert r1.get("correlation_result") is None, "Caso 1 falló: debe ser None sin input"

    # 2. Correlacion valida => resultado presente con tipos
    r2 = _handle_run({"op":"run","capability":"research","correlation_input":{"origen":"WREG32","destino":"WRITTEN_ARG","tipo":"EVIDENCE_SUPPORT","evidencia_favor":["xref.py:285"]}})
    cr = r2.get("correlation_result")
    assert cr is not None and cr.get("tipo") == "EVIDENCE_SUPPORT", "Caso 2 falló: no llega al resultado"
    assert cr.get("estado_epistemico") == "OBSERVED", "Caso 2: debe ser OBSERVED"

    # 3. TEXTUAL_MATCH no asciende a PROVEN
    r3 = _handle_run({"op":"run","capability":"research","correlation_input":{"origen":"WREG32","destino":"ring_write","tipo":"TEXTUAL_MATCH","evidencia_favor":["mismo archivo"]}})
    assert r3["correlation_result"]["estado_epistemico"] != "PROVEN", "Caso 3: TEXTUAL_MATCH no debe ser PROVEN"

    # 4. CONTRADICTION => REFUTED, no apoyo positivo
    r4 = _handle_run({"op":"run","capability":"research","correlation_input":{"origen":"WREG32","destino":"equivalente","tipo":"CONTRADICTION","evidencia_favor":["alternativas"],"evidencia_contra":["chk"]}})
    assert r4["correlation_result"]["estado_epistemico"] == "REFUTED", "Caso 4 falló"

    # 5. UNRESOLVED => HYPOTHESIS (abierto)
    r5 = _handle_run({"op":"run","capability":"research","correlation_input":{"origen":"WREG32_2","destino":"MMIO_32","tipo":"UNRESOLVED","evidencia_favor":[]}})
    assert r5["correlation_result"]["estado_epistemico"] == "HYPOTHESIS", "Caso 5 falló"

    # 6. Entrada vacía / parcial => fallo controlado, sin inventar
    r6 = _handle_run({"op":"run","capability":"research","correlation_input":{"origen":"X"}})
    # tipo por defecto TEXTUAL_MATCH; debe producir resultado, no error
    assert r6["correlation_result"] is not None, "Caso 6: debe producir sin inventar"

    # 7. Procedencia y notas conservadas
    assert "procedencia" in r2["correlation_result"], "Caso 7: procedencia perdida"
    assert r2["correlation_result"]["nota"], "Caso 7: nota perdida"

    # 8. Plan consumo: verificado que _handle_plan NO consume correlation_result de prev_step (interrupción documentada)
    from api.machine import _handle_plan
    plan_resp = _handle_plan({"capability":"research","prev_step":r2,"plan":[{"op":"run","capability":"research","available":True,"orden":1}],"mission_id":"m-029"})
    # No deposita correlation_result en retroalimentacion_causa; esto confirma interrupción
    assert "correlation_result" not in str(plan_resp.get("retroalimentacion_causa","")), "Caso 8: si plan consume, debe ser explícito; actualmente interrupción documentada"

    print("RXRE-029 PASS: 8 casos (sin input, con input, tipos, estados, procedencia, vacío, plan-interrupción)")

if __name__ == "__main__":
    test_029()
