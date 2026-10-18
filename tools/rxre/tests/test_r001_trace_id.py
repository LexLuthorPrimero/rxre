#!/usr/bin/env python3
"""RXRE-TRACE-ID-001 - prueba de correlacion por llamada (trace_id).

VERIFICA el criterio final de exito de la directiva: 4 llamadas IDENTICAS
(misma entrada funcional) producen 4 identidades de ejecucion distintas
(trace_id), conservando el mismo result_id determinista.

Politica explicita (RXRE-TRACE-ID-001):
  * nuevo trace_id  -> llamada nueva (agente genera uuid por invocacion)
  * mismo trace_id  -> reintento del mismo intento (el agente lo reutiliza)

La prueba usa DB temporal (aislado): NO toca el live rxre.sqlite3.
"""
import json, os, sys, sqlite3, subprocess, tempfile, uuid

REPO = "/home/lucas/Escritorio/rxre"
PKG = os.path.join(REPO, "tools")
RXRE = os.path.join(PKG, "rxre")
for p in (PKG, RXRE):
    if p not in sys.path:
        sys.path.insert(0, p)
MACHINE = os.path.join(RXRE, "api", "machine.py")

ok = []


def v(desc, cond, det=""):
    ok.append(bool(cond))
    print(("PASS " if cond else "FAIL ") + desc +
          (" -> " + str(det)[:160] if det else ""))


def _env(db, tid):
    e = {**os.environ, "PYTHONPATH": PKG + ":" + RXRE, "RXRE_DB": db}
    if tid is None:
        e.pop("RXRE_TRACE_ID", None)        # backward compat: no trace
    else:
        e["RXRE_TRACE_ID"] = tid
    return e


def run(tid, db, extra=None):
    """Invoca machine.py como un agente real, propagando RXRE_TRACE_ID por el
    entorno del comando (NO altera los argumentos funcionales)."""
    req = {"op": "run", "capability": "binary.inspect",
           "artefacto": "/bin/ls", "db_path": db}
    if extra:
        req.update(extra)
    r = subprocess.run([sys.executable, "-B", MACHINE],
                       input=(json.dumps(req) + "\n").encode(),
                       capture_output=True, timeout=120, env=_env(db, tid))
    try:
        return json.loads(r.stdout.strip().splitlines()[0])
    except Exception:
        v("machine.py responde JSON", False, r.stdout[:120] + r.stderr[:80])
        return None


def ev_rows(db):
    rx = sqlite3.connect(db)
    rx.row_factory = sqlite3.Row
    rows = [dict(r) for r in rx.execute(
        "SELECT evento_id, op, capability, exit_status, operation_id, "
        "result_id, trace_id, persistido, timestamp FROM execution_events "
        "ORDER BY timestamp")]
    rx.close()
    return rows


def ev_trace(db, tid):
    rx = sqlite3.connect(db)
    rx.row_factory = sqlite3.Row
    rows = [dict(r) for r in rx.execute(
        "SELECT evento_id, result_id, operation_id, trace_id, timestamp "
        "FROM execution_events WHERE trace_id=? ORDER BY timestamp", (tid,))]
    rx.close()
    return rows


# ---- Experimento decisivo: 4 llamadas, misma entrada, distinto trace_id ----
print("=== RXRE-TRACE-ID-001: 4 llamadas identicas, 4 trace_id distintos ===")
DB = tempfile.mktemp(suffix=".sqlite3")
tids = ["t" + uuid.uuid4().hex[:16] for _ in range(4)]
resps = [run(t, DB) for t in tids]

for i, r in enumerate(resps):
    v("llamada %d responde ok" % i, r and r.get("status") == "ok",
      r.get("status") if r else None)
    v("llamada %d propaga trace_id en response" % i,
      r and r.get("trace_id") == tids[i], r.get("trace_id"))

rids = set((r.get("results") or [{}])[0].get("result_id")
           for r in resps if r)
v("C1: mismo result_id determinista en 4 llamadas", len(rids) == 1, rids)

rows = ev_rows(DB)
traced = [r for r in rows if r["trace_id"] is not None]
v("C2: 4 execution_events con trace_id distintos", len(traced) == 4, len(traced))
v("C2: 4 trace_id distintos entre si",
  len(set(r["trace_id"] for r in traced)) == 4,
  [r["trace_id"] for r in traced])
v("C2: 4 evento_id distintos entre si",
  len(set(r["evento_id"] for r in traced)) == 4,
  len(set(r["evento_id"] for r in traced)))
v("C3: join 1:1 trace_id -> evento (cada trace_id 1 fila)",
  all(sum(1 for r in traced if r["trace_id"] == t) == 1 for t in tids), "")
v("C3: todo evento trazado enlazado al result_id comun",
  all(r["result_id"] in rids for r in traced), "")

# ---- Ausencia de trace_id (backward compat: NULL, formula evento_id vieja) ----
print("\n=== Ausencia / backward compat ===")
run(None, DB)
rows2 = ev_rows(DB)
none_rows = [r for r in rows2 if r["trace_id"] is None]
v("llamada sin trace_id -> row con trace_id=NULL",
  len(none_rows) >= 1, len(none_rows))
# la fila sin trace_id no comparte evento_id con filas trazadas (formula distinta)
tr_ids = set(r["evento_id"] for r in traced)
v("fila no-trazada no comparte evento_id con filas trazadas",
  all(r["evento_id"] not in tr_ids for r in none_rows), "")

# ---- Retry: mismo trace_id repetido -> reintento (linkable, distinto de new) ----
print("\n=== Retry vs new call (politica explicita) ===")
DB2 = tempfile.mktemp(suffix=".sqlite3")
T1 = "retry_" + uuid.uuid4().hex[:12]
T2 = "new_" + uuid.uuid4().hex[:12]
run(T1, DB2)          # call 1: crea el resultado (operation_id op_)
run(T1, DB2)          # call 2: COLLISION (result ya existe) -> reintento mismo T1
ev1 = ev_trace(DB2, T1)
v("retry: 2 eventos comparten trace_id T1 (reintento linkable)",
  len(ev1) == 2, len(ev1))
v("retry: ambos eventos comparten result_id (mismo resultado)",
  len(set(e["result_id"] for e in ev1)) == 1, [e["result_id"] for e in ev1])
v("retry: los 2 eventos tienen distinct evento_id (no se colapsan)",
  len(set(e["evento_id"] for e in ev1)) == 2, "")
run(T2, DB2)          # llamada nueva: trace_id distinto
ev2 = ev_trace(DB2, T2)
v("new call: trace_id T2 distinto -> evento linkable", len(ev2) >= 1, len(ev2))
v("retry vs new: T1 != T2 (distinguibles por trace_id)", T1 != T2, "")

# ---- Idempotency de reconstruccion (eventos_por_trace) ----
print("\n=== Reconstruccion por trace_id ===")
from rxre.core import store
c = store.conectar(DB)
cad = store.eventos_por_trace(c, tids[0])
v("eventos_por_trace devuelve el evento con trace_id",
  cad["status"] == "ok" and len(cad["eventos"]) == 1, cad.get("status"))
v("eventos_por_trace empty cuando trace_id inexistente",
  store.eventos_por_trace(c, "nope")["status"] == "empty", "")
v("eventos_por_trace empty cuando trace_id None",
  store.eventos_por_trace(c, None)["status"] == "empty", "")
c.close()

# ---- Idempotency: re-queryar no duplica ni altera ----
print("\n=== Idempotencia de reconstruccion ===")
c = store.conectar(DB)
n_before = c.execute("SELECT COUNT(*) FROM execution_events").fetchone()[0]
_ = store.eventos_por_trace(c, tids[1])
n_after = c.execute("SELECT COUNT(*) FROM execution_events").fetchone()[0]
v("re-query no duplica ni altera filas", n_before == n_after,
  (n_before, n_after))
c.close()

# ---- Persistencia e integridad en DB temporal ----
print("\n=== Integridad en DB temporal ===")
rx = sqlite3.connect(DB)
rx.row_factory = sqlite3.Row
total = rx.execute("SELECT COUNT(*) FROM execution_events WHERE trace_id IS NOT NULL").fetchone()[0]
v("4 filas trazadas persisten en DB", total == 4, total)
v("columna trace_id existe en esquema",
  "trace_id" in {r["name"] for r in rx.execute("PRAGMA table_info(execution_events)")},
  "columna trazada")
rx.close()

for d in (DB, DB2):
    if os.path.exists(d):
        os.unlink(d)

print("\n  %d/%d" % (sum(1 for x in ok if x), len(ok)))
sys.exit(0 if all(ok) else 1)
