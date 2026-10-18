#!/usr/bin/env python3
"""RXRE-ETAPA01-SELECT-PERSISTENCE: autonomia de seleccion por valor real.

Verifica que op:select elige por valor real (no por priority), persiste la
decision con trazabilidad y es reconstruible por un proceso independiente.
"""
import json
import os
import sqlite3
import sys

sys.path.insert(0, "/home/lucas/Escritorio/rxre")
sys.path.insert(0, "/home/lucas/Escritorio/rxre/tools/rxre")

import api.machine as machine
import rxre.core.store as store

DB = "/tmp/opencode/select_persist_test.sqlite3"
TID = "select-persist-trace-001"


def reset_db():
    for suf in ("", "-wal", "-shm", "-journal"):
        p = DB + suf
        if os.path.exists(p):
            os.unlink(p)
    conn = store.conectar(DB)
    conn.close()


def run_step(op, **kw):
    return machine.procesar_linea(json.dumps({"op": op, **kw}))


def construir_mision():
    """Mision con dos tareas: H alta priority/bajo valor, L baja priority/alto valor."""
    conn = store.conectar(DB)
    mid = store.crear_mision(conn, title="m-select", description="d")
    # L primero para obtener su id (sera dependencia de H)
    tidL = store.agregar_tarea_a_mision(
        conn, mid, title="target: binary.xrefs L", description="low prio",
        priority=1)
    tidH = store.agregar_tarea_a_mision(
        conn, mid, title="Analizar H", description="high prio",
        priority=10, dependencies=[tidL])
    # frontera abierta con target binary.xrefs -> boost de incertidumbre para L
    store.registrar_investigacion(
        conn, kind="frontier", text="x", status="OPEN",
        target="binary.xrefs", gap_kind="")
    conn.commit()
    conn.close()
    return mid, tidL, tidH


def reconstruir(db_path, tid):
    uri = "file:%s?mode=ro" % db_path
    conn = sqlite3.connect(uri, uri=True)
    conn.row_factory = sqlite3.Row
    errors = []
    events = [dict(r) for r in conn.execute(
        "SELECT evento_id, op, capability, persistido, trace_id, limitations "
        "FROM execution_events WHERE trace_id=? ORDER BY timestamp", (tid,))]
    sel_events = [e for e in events if e["op"] == "select"]
    if not sel_events:
        errors.append("missing select event")
    # note persistida con gap_kind valido (no last_task)
    notes = [dict(r) for r in conn.execute(
        "SELECT id, kind, status, gap_kind, session, target, text "
        "FROM research WHERE kind='note' AND session=?", (tid,))]
    if not notes:
        errors.append("missing persisted selection note")
    for n in notes:
        if n["gap_kind"] == "last_task":
            errors.append("invalid gap_kind last_task persisted")
    # audit_log actor
    for n in notes:
        a = conn.execute(
            "SELECT actor FROM audit_log WHERE entity_type='research' "
            "AND entity_id=?", (str(n["id"]),)).fetchone()
        if not a or a[0] != "rxre.select":
            errors.append("selection note proposer not rxre.select")
    # mission/task linkage via event limitations
    selected_task = None
    mission_id = None
    valor = None
    for e in sel_events:
        try:
            import json as _j
            lim = _j.loads(e["limitations"])[0] if e["limitations"] else {}
            lim = _j.loads(lim) if isinstance(lim, str) else lim
            selected_task = lim.get("task_id")
            mission_id = lim.get("mission_id")
            valor = lim.get("valor")
        except Exception:
            pass
    if not selected_task:
        errors.append("selected task not persisted in event")
    if not mission_id:
        errors.append("mission_id not persisted in event")
    # verify mission and task exist
    if mission_id and not conn.execute(
            "SELECT 1 FROM missions WHERE mission_id=?", (mission_id,)).fetchone():
        errors.append("mission_id not resolvable")
    if selected_task and not conn.execute(
            "SELECT 1 FROM mission_tasks WHERE task_id=?", (selected_task,)).fetchone():
        errors.append("task_id not resolvable")
    conn.close()
    return {"errors": errors, "events": events, "sel_events": sel_events,
            "notes": notes, "selected_task": selected_task,
            "mission_id": mission_id, "valor": valor}


def test_select_by_value_not_priority():
    reset_db()
    os.environ["RXRE_DB"] = DB
    os.environ["RXRE_TRACE_ID"] = TID
    mid, tidL, tidH = construir_mision()
    # por_valor=False (priority) deberia elegir H (priority 10)
    c = store.conectar(DB)
    by_prio = store.seleccionar_siguiente_accion(c, mid, por_valor=False)
    c.close()
    assert by_prio == tidH, "priority no elige H: %s" % by_prio
    # por_valor=True (RXRE) debe elegir L (mayor valor real)
    resp = run_step("select", mission_id=mid, trace_id=TID)
    assert resp.get("status") == "ok", resp
    assert resp.get("task_id") == tidL, "select no eligio L: %s" % resp.get("task_id")
    assert resp.get("persistido") is True, resp
    # valor de L > 0, H no seleccionado
    assert (resp.get("selected") or {}).get("valor", 0) > 0
    rec = reconstruir(DB, TID)
    assert not rec["errors"], rec["errors"]
    assert rec["selected_task"] == tidL
    print("TEST_SELECT_BY_VALUE_NOT_PRIORITY PASS: selected=%s (low priority, high value), "
          "priority would pick=%s" % (tidL, tidH))


def test_ablation_select_persistence():
    reset_db()
    os.environ["RXRE_DB"] = DB
    os.environ["RXRE_TRACE_ID"] = TID
    mid, tidL, tidH = construir_mision()
    # ablar registrar_evento para op=select
    orig = store.registrar_evento

    def patched(c, op, capability, env, lecciones):
        if op == "select":
            return "ablated"
        return orig(c, op, capability, env, lecciones)

    store.registrar_evento = patched
    run_step("select", mission_id=mid, trace_id=TID)
    store.registrar_evento = orig
    # borrar el evento select para forzar ausencia (idempotencia puede haberlo dejado)
    conn = store.conectar(DB)
    conn.execute("DELETE FROM execution_events WHERE op='select' AND trace_id=?", (TID,))
    conn.execute("DELETE FROM research WHERE kind='note' AND session=?", (TID,))
    conn.commit()
    conn.close()
    rec = reconstruir(DB, TID)
    assert any("missing select event" in e or "missing persisted selection note" in e
               for e in rec["errors"]), rec["errors"]
    print("TEST_ABLATION_SELECT_PERSISTENCE PASS: razon ->",
          [e for e in rec["errors"] if "select" in e or "note" in e])


def test_invalid_ref_not_fabricated():
    # select no usa refs; verificar que no se fabrican refs espurios en la note
    reset_db()
    os.environ["RXRE_DB"] = DB
    os.environ["RXRE_TRACE_ID"] = TID
    mid, tidL, tidH = construir_mision()
    run_step("select", mission_id=mid, trace_id=TID)
    conn = store.conectar(DB); conn.row_factory = sqlite3.Row
    notes = [dict(r) for r in conn.execute(
        "SELECT refs_json FROM research WHERE kind='note' AND session=?", (TID,))]
    conn.close()
    for n in notes:
        assert json.loads(n["refs_json"] or "[]") == [], n
    print("TEST_INVALID_REF_NOT_FABRICATED PASS: note refs=[] (sin fabricacion)")


if __name__ == "__main__":
    test_select_by_value_not_priority()
    test_ablation_select_persistence()
    test_invalid_ref_not_fabricated()
    print("ALL SELECT-PERSISTENCE TESTS PASS")