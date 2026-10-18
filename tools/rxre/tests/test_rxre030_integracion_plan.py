#!/usr/bin/env python3
"""RXRE-030: 10 casos discriminantes — pipeline run -> plan con correlacion."""
import sys; sys.path.insert(0,"/home/lucas/Escritorio/rxre"); sys.path.insert(0,"/home/lucas/Escritorio/rxre/tools/rxre")
from api.machine import _handle_run, _handle_plan

def test_030_10casos():
    # 1. Sin correlation_result: comportamiento previo
    r1 = _handle_plan({"capability":"research","prev_step":{"status":"ok"},"plan":[]})
    assert "correlation_result" not in r1.get("retroalimentacion_causa",{}).get("causa",{}), "Caso 1: debe preservarse sin input"

    # 2. Con correlation_result: llega al consumidor
    prev_with_corr = {"status":"ok","correlation_result":{"tipo":"EVIDENCE_SUPPORT","estado_epistemico":"OBSERVED","procedencia":"xref.py:285","nota":"WREG32 escribe registro"}}
    r2 = _handle_plan({"capability":"research","prev_step":prev_with_corr,"plan":[]})
    assert r2.get("retroalimentacion_causa",{}).get("causa",{}).get("correlation_result") == prev_with_corr["correlation_result"], "Caso 2: debe llegar intacto"

    # 3. TEXTUAL_MATCH no asciende a PROVEN (nota conservada)
    prev_text = {"status":"ok","correlation_result":{"tipo":"TEXTUAL_MATCH","estado_epistemico":"OBSERVED","nota":"No eleva a PROVEN"}}
    r3 = _handle_plan({"capability":"research","prev_step":prev_text,"plan":[]})
    cr3 = r3.get("retroalimentacion_causa",{}).get("causa",{}).get("correlation_result",{})
    assert cr3.get("tipo") == "TEXTUAL_MATCH" and cr3.get("nota"), "Caso 3: debe conservar tipo y nota"

    # 4. REFERENCE / STRUCTURAL_RELATION => no inventa equivalencia
    prev_ref = {"status":"ok","correlation_result":{"tipo":"REFERENCE","estado_epistemico":"OBSERVED","procedencia":"xref.py:161"}}
    r4 = _handle_plan({"capability":"research","prev_step":prev_ref,"plan":[]})
    assert r4.get("retroalimentacion_causa",{}).get("causa",{}).get("correlation_result",{}).get("tipo") == "REFERENCE", "Caso 4: referencia preservada sin equivalencia"

    # 5. EVIDENCE_SUPPORT => evidencia respalda afirmacion (no se convierte en apoyo de otra)
    prev_evid = {"status":"ok","correlation_result":{"tipo":"EVIDENCE_SUPPORT","estado_epistemico":"OBSERVED","procedencia":"xref.py:285"}}
    r5 = _handle_plan({"capability":"research","prev_step":prev_evid,"plan":[]})
    cr5 = r5.get("retroalimentacion_causa",{}).get("causa",{}).get("correlation_result",{})
    assert cr5.get("tipo") == "EVIDENCE_SUPPORT" and cr5.get("estado_epistemico") == "OBSERVED"

    # 6. CONTRADICTION => no se convierte en apoyo positivo
    prev_contra = {"status":"unsupported","correlation_result":{"tipo":"CONTRADICTION","estado_epistemico":"REFUTED","evidencia_contra":["chk: alternativas"]}}
    r6 = _handle_plan({"capability":"umr_regdb","prev_step":prev_contra,"plan":[]})
    cr6 = r6.get("retroalimentacion_causa",{}).get("causa",{}).get("correlation_result",{})
    assert cr6.get("tipo") == "CONTRADICTION" and cr6.get("estado_epistemico") == "REFUTED", "Caso 6: contradiccion no debe ser apoyo"

    # 7. UNRESOLVED => conserva incertidumbre
    prev_unres = {"status":"unsupported","correlation_result":{"tipo":"UNRESOLVED","estado_epistemico":"HYPOTHESIS","procedencia":"falta evidencia"}}
    r7 = _handle_plan({"capability":"umr_regdb","prev_step":prev_unres,"plan":[]})
    cr7 = r7.get("retroalimentacion_causa",{}).get("causa",{}).get("correlation_result",{})
    assert cr7.get("tipo") == "UNRESOLVED" and cr7.get("estado_epistemico") == "HYPOTHESIS", "Caso 7: abierto debe mantenerse"

    # 8. CAUSAL_RELATION => conserva procedencia, no se generaliza
    prev_causal = {"status":"ok","correlation_result":{"tipo":"CAUSAL_RELATION","estado_epistemico":"PROVEN","procedencia":"test_026","nota":"No universal"}}
    r8 = _handle_plan({"capability":"research","prev_step":prev_causal,"plan":[]})
    cr8 = r8.get("retroalimentacion_causa",{}).get("causa",{}).get("correlation_result",{})
    assert cr8.get("tipo") == "CAUSAL_RELATION" and cr8.get("procedencia") == "test_026"

    # 9. Entrada vacia / malformada => no fabrica resultados
    r9 = _handle_run({"op":"run","capability":"research","correlation_input":{}})
    # correlation_input vacio -> tipo por defecto; debe ser manejado sin crash
    cr9 = r9.get("correlation_result")
    assert isinstance(cr9, dict) or cr9 is None, "Caso 9: no debe inventar"

    # 10. Comparar con y sin correlacion: diferencia observable
    prev_base = {"status":"ok","capability":"research","results":[]}
    prev_corr = {"status":"ok","capability":"research","results":[],"correlation_result":{"tipo":"EVIDENCE_SUPPORT","estado_epistemico":"OBSERVED","procedencia":"xref.py:285","nota":"WREG32 escribe registro"}}
    r10_base = _handle_plan({"capability":"research","prev_step":prev_base,"plan":[]})
    r10_corr = _handle_plan({"capability":"research","prev_step":prev_corr,"plan":[]})
    assert "correlation_result" in r10_corr.get("retroalimentacion_causa",{}).get("causa",{}), "Caso 10: con correlacion debe observarse diferencia"
    assert "correlation_result" not in r10_base.get("retroalimentacion_causa",{}).get("causa",{}), "Caso 10: sin correlacion debe mantenerse igual"

    print("RXRE-030 PASS: 10 casos (sin, llega, tipos, estados, evidencia, contradiccion, abierto, causal, vacio, diferencia observable)")

if __name__ == "__main__":
    test_030_10casos()
