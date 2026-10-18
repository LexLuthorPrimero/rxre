#!/usr/bin/env python3
"""Adversarial: interrupcion en el punto de persistencia de un run.

Verifica que una excepcion entre ejecutar el backend y persistir el evento
no deje a la base en estado parcial prohibido, y que la BD pueda reabrirse
con integridad. Sin modificar la implementacion: el fallo se inyecta con
un monkeypatch desde este mismo script.

Contrato probado (derivado de api/machine.py _handle_run):
- 'run' exitoso           -> execution_events fila persistida, persistido=1
- fallo previo al evento-> NO debe quedar evento con exit_status NULL
- fallo tras INSERT antes de commit -> el evento NO debe persistir
                              (la conexion se cierra sin commit)
- tras reabrir, los eventos previos siguen intactos
"""
import json
import os
import sqlite3
import sys

import api.machine as machine
import rxre.backends.dispatch as dispatch
import rxre.core.store as store

CLI = "/home/lucas/Escritorio/rxre/rxre"
TMP_DB = "/tmp/rxre_adv_interrupcion.sqlite3"
if os.path.exists(TMP_DB):
    os.unlink(TMP_DB)
os.environ["RXRE_DB"] = TMP_DB


def open_db():
    return store.conectar()


def reset_db():
    if os.path.exists(TMP_DB):
        os.unlink(TMP_DB)
    conn = open_db()
    conn.close()


def run_jsonl(req, timeout=10):
    p = subprocess_run(req)
    try:
        return json.loads(p.stdout.decode())
    except Exception:
        return {}


def subprocess_run(req):
    import subprocess
    p = subprocess.run([CLI], input=req.encode(), capture_output=True,
                    timeout=timeout, env={**os.environ, "RXRE_DB": TMP_DB})
    return p


def sql(c, q, args=()):
    cur = c.execute(q, args)
    c.commit()
    return cur.fetchall()


def test_interrupcion_recuperacion():
    reset_db()
    conn = open_db()
    try:
        # ---------- CASO CONTROL (run exitoso) ----------
        resp = machine.procesar_linea('{"op":"run","capability":"binary.inspect",'
                                      '"artefacto":"/bin/ls"}')
        assert resp.get("status") == "ok", resp
        conn2 = open_db()
        eventos = sql(conn2,
                     "SELECT evento_id, op, exit_status, persistido FROM execution_events")
        assert len(eventos) >= 1, "run exitoso no persistio evento"
        assert all(e[2] is not None for e in eventos), "exit_status NULL en evento"
        conn2.close()

        # ---------- CASO INTERRUMPIDO: fallo antes de registrar ----------
        # Patch: dispatch.ejecutar lanza tras recibir los params (no ejecuta).
        def lanzar_dispatch(capability, params):
            raise RuntimeError("fallo inyectado antes del evento")
        orig_ejecutar = dispatch.ejecutar
        dispatch.ejecutar = lanzar_dispatch
        try:
            resp2 = machine.procesar_linea('{"op":"run","capability":"binary.xrefs",'
                                         '"artefacto":"/bin/ls"}')
        finally:
            dispatch.ejecutar = orig_ejecutar
        assert resp2.get("status") in ("error", "blocked"), resp2
        # No debe quedar evento asociado a esa operacion
        conn3 = open_db()
        filas = sql(conn3,
                   "SELECT evento_id FROM execution_events WHERE op='run' "
                   "AND capability='binary.xrefs'")
        assert filas == [], "evento huérfano tras fallo antes del evento"
        conn3.close()

        # ---------- CASO INTERRUPIDO: fallo tras INSERT antes de commit ----------
        # Patch: registrar_evento hace el INSERT, luego lanza.
        import time
        orig_registrar = store.registrar_evento

        def registrar_parcial(con, op, capability, env, lecciones):
            evento_id = "ev_" + str(time.time())
            con.execute(
                "INSERT OR REPLACE INTO execution_events"
                "(evento_id, op, capability, exit_status, operation_id, "
                "result_id, persistido, n_lessons, limitations, "
                "timestamp, trace_id, lecciones_json) VALUES(?,?,?,?,?,?,?,?,?,?,?,?)",
                (evento_id, op, capability, env.get("ejecucion", {}).get("exit_status", 1),
                 1, 0, len(lecciones or []), "[]",
                 time.strftime("%Y-%m-%dT%H:%M:%S%z"),
                 env.get("trace_id", ""), "[]"))
            raise RuntimeError("fallo tras INSERT, antes de commit")

        store.registrar_evento = registrar_parcial
        try:
            resp3 = machine.procesar_linea('{"op":"run","capability":"binary.callgraph",'
                                        '"artefacto":"/bin/ls"}')
        finally:
            store.registrar_evento = orig_registrar
        # El backend fue exitoso y los RESULTADOS se persistieron: `persistido`
        # refleja ese hecho (contrato de dispatch/AGUA: "hay fila en la tabla").
        # Lo que fallo fue el EVENTO DE AUDITORIA, informado aparte por
        # `persistencia_fallida` + limitacion; el evento no queda.
        assert resp3.get("status") == "ok", resp3
        assert resp3.get("persistido") is True
        assert resp3.get("persistencia_fallida") is True, \
            "la respuesta debe explicitar el fallo de persistencia"
        assert any("persistencia" in str(l) for l in resp3.get("limitations", [])), resp3
        conn4 = open_db()
        filas = sql(conn4,
                   "SELECT evento_id FROM execution_events WHERE capability='binary.callgraph'")
        assert filas == [], "evento parcial persistido tras fallo interrumpido"
        conn4.close()

        # ---------- REABRIR BD y verificar integridad ----------
        conn5 = open_db()
        ok = conn5.execute("PRAGMA integrity_check").fetchone()[0]
        assert ok == "ok", f"integrity_check fallo: {ok}"
        # Los eventos del caso control siguen intactos
        conn6 = open_db()
        n_ok = sql(conn6,
                  "SELECT COUNT(*) FROM execution_events WHERE op='run' AND persistido=1")[0][0]
        assert n_ok >= 1, "evento del run exitoso perdido"
        conn6.close()
    finally:
        conn.close()


if __name__ == "__main__":
    test_interrupcion_recuperacion()
    print("PASS test_interrupcion_recuperacion")
