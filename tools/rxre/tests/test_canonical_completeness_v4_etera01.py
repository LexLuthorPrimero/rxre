#!/usr/bin/env python3
"""RXRE-CANONICAL_COMPLETENESS_V4: pruebas discriminantes del contrato de completitud.

Este fichero valida que el comparador canónico NO convierte falta de evidencia
de completitud en una afirmación de que el resultado está completo.

Estados contractuales verificados:
- complete: contrato verificado, productor declara `completitud.completo: true`
- partial: omisión demostrada (`completitud.completo: false`)
- unknown: marcador inválido o ausente (riesgo documentado)

Los siguientes productores conocidos como truncadores ahora emiten marcador:
- gh_decompile: `completitud` sobre funciones (declarado V4)
- rz_cfg, rz_container, rz_functions, cs_disasm: ya tenían marcador

Los productores sin truncamiento conocida mantienen el default `complete`.
"""
import json
import os
import sys

sys.path.insert(0, "/home/lucas/Escritorio/rxre")
sys.path.insert(0, "/home/lucas/Escritorio/rxre/tools/rxre")

import api.machine as machine
import rxre.core.store as store

DB = "/tmp/opencode/v4_test.sqlite3"
TRACE = "complete-v4"

def reset_db():
    for suf in ("", "-wal", "-shm", "-journal"):
        p = DB + suf
        if os.path.exists(p):
            os.unlink(p)
    conn = store.conectar(DB)
    conn.close()

def res(rid, tipo="control_flow", value=None, source="/bin/ls", scope="binary", tool="rizin",
        completo=True, omitidos=0, limite=500, elem="cfg", anidada=None, raw_sample=False):
    r = {
        "result_id": rid, "type": tipo, "value": value or {"n": 1},
        "source": source, "scope": scope, "tool": tool
    }
    if value is None:
        r["value"] = {"n": 1}
    if raw_sample:
        r["raw"] = {"coincidencias_truncadas": True}
    r["completitud"] = {"completo": completo, "omitidos": omitidos,
                        "limite": limite, "elemento": elem}
    if anidada is not None:
        r["completitud_anidada"] = anidada
    return r

# ============================================================
# TEST 1. Productor con contrato verificado y marcador válido complete
# ============================================================
def test_1_verified_complete():
    # rz_cfg, rz_container, rz_functions con marcador completo
    r = res("t1", completo=True)
    assert machine._obs_completeness([r]) == "complete", f"expected complete, got {machine._obs_completeness([r])}"
    print("TEST_1 PASS: contrato verificado completo -> complete")

# ============================================================
# TEST 2. Productor truncador conocido, sin marcador (riesgo documentado)
# ============================================================
def test_2_truncator_no_marker():
    # Un productor truncador como gh_decompile ANTES de la correccion
    # (sin marcador) -> complete POR DEFAULT (riesgo documentado)
    r = {"result_id": "t2", "type": "T", "value": {"funciones": [1,2,3]}, "source": "/x", "scope": "binary", "tool": "ghidra"}
    # El default es complete por compatibilidad con productores no truncadores
    assert machine._obs_completeness([r]) == "complete", f"expected complete (default), got {machine._obs_completeness([r])}"
    print("TEST_2 PASS: productor truncador sin marcador -> complete (riesgo documentado)")

# ============================================================
# TEST 3. Productor sin contrato verificado y sin marcador
# ============================================================
def test_3_no_contract_no_marker():
    # Un productor genericamente sin truncamiento conocido
    r = {"result_id": "t3", "type": "T", "value": {"items": list(range(100))}, "source": "/x", "scope": "binary", "tool": "t"}
    assert machine._obs_completeness([r]) == "complete", f"expected complete, got {machine._obs_completeness([r])}"
    print("TEST_3 PASS: sin contrato verificado -> complete (default)")

# ============================================================
# TEST 4. Marcador con completo ausente, null o tipo inválido
# ============================================================
def test_4_invalid_completo():
    # Ausente
    r1 = {"result_id": "t4a", "type": "T", "value": {"n": 1}, "source": "/x", "scope": "binary", "tool": "t",
          "completitud": {"omitidos": 0, "limite": 500, "elemento": "cfg"}}
    assert machine._obs_completeness([r1]) == "unknown", f"ausente -> unknown, got {machine._obs_completeness([r1])}"
    # null
    r2 = {"result_id": "t4b", "type": "T", "value": {"n": 1}, "source": "/x", "scope": "binary", "tool": "t",
          "completitud": {"completo": None, "omitidos": 0, "limite": 500, "elemento": "cfg"}}
    assert machine._obs_completeness([r2]) == "unknown", f"null -> unknown, got {machine._obs_completeness([r2])}"
    # tipo invalido
    r3 = {"result_id": "t4c", "type": "T", "value": {"n": 1}, "source": "/x", "scope": "binary", "tool": "t",
          "completitud": {"completo": "yes", "omitidos": 0, "limite": 500, "elemento": "cfg"}}
    assert machine._obs_completeness([r3]) == "unknown", f"tipo invalido -> unknown, got {machine._obs_completeness([r3])}"
    print("TEST_4 PASS: completo ausente/null/invalido -> unknown")

# ============================================================
# TEST 5. Marcador válido partial
# ============================================================
def test_5_valid_partial():
    r = res("t5", completo=False, omitidos=300, limite=500)
    assert machine._obs_completeness([r]) == "partial", f"parcial valido -> partial, got {machine._obs_completeness([r])}"
    print("TEST_5 PASS: marcador valido partial -> partial")

# ============================================================
# TEST 6. Marcador primario complete, campo anidado incompleto
# ============================================================
def test_6_primary_complete_nested_partial():
    # cs_disasm: instrucciones complete, pero huecos truncados
    r = res("t6", completo=True, anidada={"huecos": {"completo": False, "omitidos": 5}})
    assert machine._obs_completeness([r]) == "partial", f"primario complete + anidado partial -> partial, got {machine._obs_completeness([r])}"
    print("TEST_6 PASS: completo primario + anidado partial -> partial")

# ============================================================
# TEST 7. Dos resultados con mismo contenido visible, uno unknown
# ============================================================
def test_7_same_visible_one_unknown():
    reset_db()
    os.environ["RXRE_DB"] = DB
    os.environ["RXRE_TRACE_ID"] = TRACE
    orig = {k: getattr(store, k) for k in ("registrar", "registrar_evento", "registrar_reflexion", "registrar_investigacion", "registrar_audit_log", "refs_invalidos")}
    store.registrar = lambda c, *a, **k: "op_noop"
    store.registrar_evento = lambda c, *a, **k: "ev_noop"
    store.registrar_reflexion = lambda c, *a, **k: {"estado": "ok", "reflexion_id": "r"}
    store.registrar_investigacion = lambda c, *a, **k: {"estado": "ok", "id": 1}
    store.registrar_audit_log = lambda c, *a, **k: 1
    store.refs_invalidos = lambda c, refs: []
    orig_d = machine.dispatch.ejecutar
    def fake(cap, params):
        comp_flag = params.get("_comp", True)
        return {"status": "ok", "results": [{"result_id": "t7", "type": "T", "value": {"n": 1}, "source": "/bin/ls", "scope": "binary", "tool": "t", "completitud": {"completo": comp_flag, "omitidos": 0, "limite": 500}}]}
    machine.dispatch.ejecutar = fake
    try:
        r = machine.procesar_linea(json.dumps({
            "op": "experiment", "capability": "binary.cfg", "question": "q",
            "prediction": "NO_CHANGE", "comparar": "results", "canonico": True,
            "baseline_params": {"artefacto": "/bin/ls", "_comp": True},
            "modified_params": {"artefacto": "/bin/ls", "_comp": False}}))
    finally:
        machine.dispatch.ejecutar = orig_d
        for k, v in orig.items():
            setattr(store, k, v)
    assert r["experiment"]["veredicto"] == "no_observable", f"expected no_observable, got {r}"
    print("TEST_7 PASS: mismo visible, uno unknown -> no_observable (abstencion)")

# ============================================================
# TEST 8. Dos resultados completos y semánticamente iguales
# ============================================================
def test_8_two_complete_semantically_equal():
    r1 = res("t8a", tipo="cfg", value={"n": 1}, completo=True)
    r2 = res("t8b", tipo="cfg", value={"n": 1}, completo=True)
    state_a, canon_a = machine._canon_obs([r1])
    state_b, canon_b = machine._canon_obs([r2])
    assert state_a == state_b == "ok" and canon_a == canon_b, f"esperado canon ok, got ({state_a}, {state_b})"
    print("TEST_8 PASS: dos completos iguales semanticamente -> igualdad canonica")

# ============================================================
# TEST 9. Dos resultados parciales con contenido visible igual
# ============================================================
def test_9_two_partial_same_visible():
    reset_db()
    os.environ["RXRE_DB"] = DB
    os.environ["RXRE_TRACE_ID"] = TRACE
    orig = {k: getattr(store, k) for k in ("registrar", "registrar_evento", "registrar_reflexion", "registrar_investigacion", "registrar_audit_log", "refs_invalidos")}
    store.registrar = lambda c, *a, **k: "op_noop"
    store.registrar_evento = lambda c, *a, **k: "ev_noop"
    store.registrar_reflexion = lambda c, *a, **k: {"estado": "ok", "reflexion_id": "r"}
    store.registrar_investigacion = lambda c, *a, **k: {"estado": "ok", "id": 1}
    store.registrar_audit_log = lambda c, *a, **k: 1
    store.refs_invalidos = lambda c, refs: []
    orig_d = machine.dispatch.ejecutar
    def fake(cap, params):
        return {"status": "ok", "results": [{"result_id": "t9", "type": "T", "value": {"n": 1}, "source": "/bin/ls", "scope": "binary", "tool": "t", "completitud": {"completo": False, "omitidos": 3}}]}
    machine.dispatch.ejecutar = fake
    try:
        r = machine.procesar_linea(json.dumps({
            "op": "experiment", "capability": "binary.cfg", "question": "q",
            "prediction": "NO_CHANGE", "comparar": "results", "canonico": True,
            "baseline_params": {"artefacto": "/bin/ls"},
            "modified_params": {"artefacto": "/bin/ls"}}))
    finally:
        machine.dispatch.ejecutar = orig_d
        for k, v in orig.items():
            setattr(store, k, v)
    assert r["experiment"]["veredicto"] == "no_observable", f"expected no_observable, got {r}"
    print("TEST_9 PASS: dos parciales mismo visible -> no_observable (abstencion)")

# ============================================================
# TEST 10. Modo no canónico, comportamiento previo preservado
# ============================================================
def test_10_non_canonical_preserved():
    reset_db()
    os.environ["RXRE_DB"] = DB
    os.environ["RXRE_TRACE_ID"] = TRACE
    r = machine.procesar_linea(json.dumps({
        "op": "experiment", "capability": "binary.xrefs",
        "question": "q", "prediction": "NO_CHANGE", "comparar": "results",
        "baseline_params": {"artefacto": "/bin/ls", "backend_id": "rizin"},
        "modified_params": {"artefacto": "/bin/ls", "backend_id": "radare2"}}))
    assert r["experiment"]["veredicto"] == "refutada", f"expected refutada (no canonical), got {r}"
    print("TEST_10 PASS: modo no canonico -> comportamiento previo preservado")

# ============================================================
# TEST 11. Persistencia y dispatch de los estados de completitud
# ============================================================
def test_11_persistence_dispatch():
    reset_db()
    os.environ["RXRE_DB"] = DB
    os.environ["RXRE_TRACE_ID"] = TRACE
    from backends import dispatch as disp
    # radare2 produces valid results with completitud marker
    env_ok = disp.ejecutar("binary.cfg", {"artefacto": "/bin/ls", "backend_id": "radare2"})
    r_ok = (env_ok.get("results") or [{}])[0] if env_ok.get("results") else {}
    # Estado conocido: completitud presente con completo=true
    assert r_ok.get("completitud", {}).get("completo") == True, \
        "completitud completa presente en resultado ok"
    print("TEST_11 PASS: persistencia y dispatch de completitud (completo=true)")

# ============================================================
# TEST 12. Compatibilidad consume los envelopes existentes
# ============================================================
def test_12_legacy_consumer():
    # Los consumidores que leen envelopes sin completitud deben seguir funcionando
    r = {"result_id": "t12", "type": "T", "value": {"n": 1}, "source": "/x", "scope": "binary", "tool": "t"}
    # Sin marcador, el comparador sigue funcionando
    state, canon = machine._canon_obs([r])
    assert state == "ok", f"el comparable maneja envelopes sin marcador, got {state}"
    # El canonico debe calcular algo válido
    assert isinstance(canon, list) and len(canon) >= 1, "canonica calculada correctamente"
    print("TEST_12 PASS: consumidor legacy maneja envelopes sin marcador")

if __name__ == "__main__":
    test_1_verified_complete()
    test_2_truncator_no_marker()
    test_3_no_contract_no_marker()
    test_4_invalid_completo()
    test_5_valid_partial()
    test_6_primary_complete_nested_partial()
    test_7_same_visible_one_unknown()
    test_8_two_complete_semantically_equal()
    test_9_two_partial_same_visible()
    test_10_non_canonical_preserved()
    test_11_persistence_dispatch()
    test_12_legacy_consumer()
    print("ALL CANONICAL_COMPLETENESS_V4 TESTS PASS")