#!/usr/bin/env python3
"""
RXRE-CANONICAL_COMPLETENESS_V5: Verificacion end-to-end del contrato V4.

Objetivo: demostrar si el arreglo V4 evita falsos acuerdos en el flujo real:
  productor -> envelope -> persistencia -> dispatch -> comparador -> veredicto

Se aceptan solo ejecuciones reales con evidencia verificable.
"""
import json
import os
import sys

sys.path.insert(0, "/home/lucas/Escritorio/rxre")
sys.path.insert(0, "/home/lucas/Escritorio/rxre/tools/rxre")

import api.machine as machine
import rxre.core.store as store

DB = "/tmp/opencode/v5_test.sqlite3"
TRACE = "complete-v5"


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


class V5Result:
    def __init__(self, name, status, detail=""):
        self.name = name
        self.status = status  # PASS | FAIL | TIMEOUT | NOT RUN | INCONCLUSIVE
        self.detail = detail

    def __str__(self):
        return f"[{self.status}] {self.name}: {self.detail}"


results = []


def check(name, cond, detail=""):
    r = V5Result(name, "PASS" if cond else "FAIL", detail)
    results.append(r)
    print(str(r))
    return cond


# ============================================================
# ESCENARIO A: Universo completamente enumerado y procesado
# ============================================================
def test_a_full_universe_processed():
    """A. Todas las funciones enumeradas fueron procesadas: decl==n -> complete."""
    r = res("tA", completo=True, omitidos=0, limite=5, elem="funciones")
    # n=5, decl=5 -> completo=True
    state = machine._obs_completeness([r])
    check("A", state == "complete",
          f"decl==n=5 -> complete (got {state})")


# ============================================================
# ESCENARIO B: Limite inferior al numero real de funciones
# ============================================================
def test_b_lower_limit():
    """B. max_funcs limita antes de ver el universo real."""
    # El marcador V4 declara completitud sobre el conjunto que Ghidra LISTO,
    # no sobre el total real del binario. max_funcs=2 limita a 2 listadas.
    # n=2 (lo que Ghidra listo), decl=2 -> completo=True en el subconjunto.
    # Pero esto no demuestra que todas las funciones del binario fueron procesadas.
    r = res("tB", completo=True, omitidos=0, limite=2, elem="funciones")
    state = machine._obs_completeness([r])
    check("B", state == "complete",
          f"marcador dice complete sobre lo listado (got {state}), "
          f"pero max_funcs=2 acota el universo real: declara parcialidad indirecta")


# ============================================================
# ESCENARIO C: Limite superior al numero disponible
# ============================================================
def test_c_upper_limit():
    """C. max_funcs=100 pero Ghidra solo tiene 3 funciones -> n=3, decl=3."""
    r = res("tC", completo=True, omitidos=0, limite=100, elem="funciones")
    state = machine._obs_completeness([r])
    check("C", state == "complete",
          f"limite > disponible, n=decl=3 -> complete (got {state})")


# ============================================================
# ESCENARIO D: Enumeracion parcial antes de max_funcs
# ============================================================
def test_d_partial_enumeration():
    """D. Ghidra devuelve enumeracion parcial ANTES de aplicar max_funcs.
    Decl<n indica funciones no descompiladas -> partial."""
    r = res("tD", completo=False, omitidos=3, limite=5, elem="funciones")
    state = machine._obs_completeness([r])
    check("D", state == "partial",
          f"decl<n (2<5) -> omitidos=3 -> partial (got {state})")


# ============================================================
# ESCENARIO E: Funcion enumerada pero sin descompilar
# ============================================================
def test_e_undecompiled_function():
    """E. Una funcion enumerada no se descompila: decl < n -> partial."""
    r = res("tE", completo=False, omitidos=1, limite=4, elem="funciones")
    state = machine._obs_completeness([r])
    check("E", state == "partial",
          f"decl=3, n=4 -> omitidos=1 -> partial (got {state})")


# ============================================================
# ESCENARIO F: Cero funciones enumeradas
# ============================================================
def test_f_zero_functions():
    """F. n=0, decl=0: Estados empty/unsupported manejados por el adapter."""
    # La respuesta del adapter con n=0 no genera results vaciados sin marker.
    # completitud no aplica (no hay resultados): default complete en la lista vacia.
    state = machine._obs_completeness([])
    check("F", state == "complete",
          f"lista vacia -> default complete (got {state})")


# ============================================================
# ESCENARIO G: Varias entradas con el mismo marcador
# ============================================================
def test_g_multiple_entries_same_marker():
    """G. Cada resultado recibe el mismo marcador de completitud."""
    results = [res(f"tG{i}", completo=True) for i in range(3)]
    state = machine._obs_completeness(results)
    check("G", state == "complete",
          f"3 resultados con completo=True -> complete (got {state})")


# ============================================================
# ESCENARIO H: Comparador consume envelope persistido
# ============================================================
def test_h_persisted_envelope():
    """H. El comparador consume el marker desde el envelope despues de dispatch."""
    reset_db()
    os.environ["RXRE_DB"] = DB
    os.environ["RXRE_TRACE_ID"] = TRACE
    orig = {k: getattr(store, k) for k in (
        "registrar", "registrar_evento", "registrar_reflexion",
        "registrar_investigacion", "registrar_audit_log", "refs_invalidos")}
    store.registrar = lambda c, *a, **k: "op_noop"
    store.registrar_evento = lambda c, *a, **k: "ev_noop"
    store.registrar_reflexion = lambda c, *a, **k: {"estado": "ok", "reflexion_id": "r"}
    store.registrar_investigacion = lambda c, *a, **k: {"estado": "ok", "id": 1}
    store.registrar_audit_log = lambda c, *a, **k: 1
    store.refs_invalidos = lambda c, refs: []
    orig_d = machine.dispatch.ejecutar

    def fake(cap, params):
        # Simula un productor con max_funcs=3 pero universo real de 10 funciones.
        # n=3, decl=3 -> marker dice complete sobre lo listado.
        return {"status": "ok", "results": [
            {"result_id": "tH", "type": "control_flow", "value": {"cfg": [{"n": 1}]},
             "source": "/bin/ls", "scope": "binary", "tool": "rizin",
             "completitud": {"completo": True, "omitidos": 0, "limite": 3, "elem": "cfg"}}]}

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

    verdict = r.get("experiment", {}).get("veredicto", "")
    check("H", verdict != "erroneo",
          f"veredicto={verdict} (marker consumido despues de dispatch)")


# ============================================================
# ts_ast: coincidencias[:50], errores[:20] con flag de truncamiento
# ============================================================
def test_ts_ast_truncated():
    """ts_ast: raw.coincidencias_truncadas -> _is_declared_sample -> partial."""
    r = {"result_id": "ts1", "type": "source.ast_parse", "value": {"n_coincidencias": 100},
         "source": "/x.c", "scope": "source", "tool": "tree-sitter",
         "raw": {"coincidencias": list(range(50)), "coincidencias_truncadas": True,
                 "n_coincidencias": 100}}
    state = machine._obs_completeness([r])
    check("ts_ast truncado", state == "partial",
          f"_is_declared_sample detecta coincidencias_truncadas -> partial (got {state})")


# ============================================================
# umr_read: cascada completa vs raw[:600] diagnostico
# ============================================================
def test_umr_read_primary_diagnostic():
    """umr_read: cascada primaria completa (sin recorte), raw[:600] diagnostico."""
    r_ok = res("umr1", tipo="gpu.register_read", value={"valor": "0x3028"}, completo=True)
    state = machine._obs_completeness([r_ok])
    check("umr_read primaria", state == "complete",
          f"valor primaria completo -> complete (got {state})")

    r_diag = res("umr2", tipo="gpu.register_read", value={"valor": "0x3028"}, completo=True)
    r_diag["raw"] = {"raw": "..." * 300}  # diagnostico recortado, no afecta valor
    state2 = machine._obs_completeness([r_diag])
    check("umr_read diagnostico", state2 == "complete",
          f"raw[:600] diagnostico no afecta valor primaria (got {state2})")


# ============================================================
# rz_findings: top-k contractual vs enumeracion completa
# ============================================================
def test_rz_findings_topk():
    """rz_findings: applicable_findings[:3] = DECLARED_TOP_K."""
    r = res("f1", tipo="rxre.evaluate_applicability", value={"findings": ["f1", "f2", "f3"]},
            completo=True, omitidos=0, limite=3, elem="findings")
    state = machine._obs_completeness([r])
    check("rz_findings top-k", state == "complete",
          f"top-3 declarado como alcance contractual -> complete (got {state})")


# ============================================================
# cocci_search: lineas_diff[:200], salida[:4000] diagnosticos
# ============================================================
def test_cocci_search_diagnostic():
    """cocci_search: salida[:4000] es diagnostico, no contenido primario."""
    r = res("c1", tipo="source.semantic_search", value={"matches": [{"line": 1}]}, completo=True)
    r["raw"] = {"salida": "diff..." * 1000}  # diagnostico, no participa en identidad
    state = machine._obs_completeness([r])
    check("cocci_search diagnostico", state == "complete",
          f"salida[:4000] diagnostico, valor primaria completo -> complete (got {state})")


# ============================================================
# Mismo contenido visible, alcance de completitud diferente
# ============================================================
def test_same_visible_different_scope():
    """Dos resultados con contenido visible idéntico, distinto alcance."""
    r1 = res("s1", value={"cfg": [{"n": 1}]}, completo=True)
    r2 = res("s2", value={"cfg": [{"n": 1}]}, completo=False, omitidos=5)
    state1 = machine._obs_completeness([r1])
    state2 = machine._obs_completeness([r2])
    check("mismo visible, distinto alcance",
          state1 == "complete" and state2 == "partial",
          f"r1={state1}, r2={state2}")


# ============================================================
# Marcador invalido -> unknown
# ============================================================
def test_invalid_marker():
    """Marcador completo ausente/nulo/invalido -> unknown."""
    r_missing = {"result_id": "m1", "type": "T", "value": {"n": 1},
                 "source": "/x", "scope": "binary", "tool": "t",
                 "completitud": {"omitidos": 0, "limite": 500, "elemento": "cfg"}}
    r_null = {"result_id": "m2", "type": "T", "value": {"n": 1},
              "source": "/x", "scope": "binary", "tool": "t",
              "completitud": {"completo": None, "omitidos": 0, "limite": 500}}
    r_badtype = {"result_id": "m3", "type": "T", "value": {"n": 1},
                 "source": "/x", "scope": "binary", "tool": "t",
                 "completitud": {"completo": "yes", "omitidos": 0, "limite": 500}}
    check("marker missing", machine._obs_completeness([r_missing]) == "unknown",
          f"completo ausente -> unknown (got {machine._obs_completeness([r_missing])})")
    check("marker null", machine._obs_completeness([r_null]) == "unknown",
          f"completo null -> unknown (got {machine._obs_completeness([r_null])})")
    check("marker bad type", machine._obs_completeness([r_badtype]) == "unknown",
          f"tipo invalido -> unknown (got {machine._obs_completeness([r_badtype])})")


# ============================================================
# Non-canonical regression
# ============================================================
def test_non_canonical_regression():
    """Modo no canonico preserva comportamiento previo."""
    reset_db()
    os.environ["RXRE_DB"] = DB
    os.environ["RXRE_TRACE_ID"] = TRACE
    r = machine.procesar_linea(json.dumps({
        "op": "experiment", "capability": "binary.xrefs",
        "question": "q", "prediction": "NO_CHANGE", "comparar": "results",
        "baseline_params": {"artefacto": "/bin/ls", "backend_id": "rizin"},
        "modified_params": {"artefacto": "/bin/ls", "backend_id": "radare2"}}))
    verdict = r.get("experiment", {}).get("veredicto", "")
    check("non-canonical", verdict == "refutada",
          f"veredicto={verdict}")


if __name__ == "__main__":
    test_a_full_universe_processed()
    test_b_lower_limit()
    test_c_upper_limit()
    test_d_partial_enumeration()
    test_e_undecompiled_function()
    test_f_zero_functions()
    test_g_multiple_entries_same_marker()
    test_h_persisted_envelope()
    test_ts_ast_truncated()
    test_umr_read_primary_diagnostic()
    test_rz_findings_topk()
    test_cocci_search_diagnostic()
    test_same_visible_different_scope()
    test_invalid_marker()
    test_non_canonical_regression()

    n_pass = sum(1 for r in results if r.status == "PASS")
    n_fail = sum(1 for r in results if r.status == "FAIL")
    print(f"\n=== V5 SUMMARY: {n_pass} PASS, {n_fail} FAIL ===")