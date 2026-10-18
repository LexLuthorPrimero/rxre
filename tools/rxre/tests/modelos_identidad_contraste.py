#!/usr/bin/env python3
"""Contraste de los TRES modelos de identidad de result_id.

Solo lectura sobre produccion; experimentos sobre base temporal AISLADA.
No modifica codigo ni schema.
"""
from __future__ import annotations

import os
import sqlite3
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
PKG = os.path.abspath(os.path.join(HERE, ".."))
sys.path.insert(0, PKG)

DB = "/tmp/opencode/modelos_identidad.db"
for ext in ("", "-wal", "-shm"):
    if os.path.exists(DB + ext):
        os.remove(DB + ext)

from core import store as S   # noqa: E402

fails = []
n = 0
obs = {}


def v(nombre, cond, det=""):
    global n
    n += 1
    if not cond:
        fails.append("%s %s" % (nombre, det))
    print("  %s %s%s" % ("PASS" if cond else "FAIL", nombre,
                         "" if cond else "  <- %s" % det))


def reg(c, results, tag):
    op = S.registrar(c, {"capability": "modelo.test", "question": "q",
                         "target": "binary:%s" % tag, "scope": "binary"},
                     {"operation": "modelo", "status": "ok", "results": results})
    return op


print("=== Modelos de identidad de result_id (base: %s) ===" % DB)
c = S.conectar(DB)

# --- 1. mismo contenido en dos operaciones -------------------------------
print("\n--- 1. mismo contenido, dos operaciones (id determinista) ---")
# Dos artefactos IGUALES producen el MISMO result_id (determinismo)
contenido = {"file_format": "elf64", "arch": "x86", "bits": 64}
op1 = reg(c, [{"result_id": "MOD_1", "value": contenido}], "a")
op2 = reg(c, [{"result_id": "MOD_1", "value": contenido}], "b")
dueno = c.execute("SELECT operation_id FROM results WHERE result_id='MOD_1'"
                  ).fetchone()["operation_id"]
print("  op1=%s op2=%s dueño real=%s" % (op1, op2, dueno))
v("1.1: la fila la posee la SEGUNDA observacion", dueno == op2)
v("1.2: la PRIMERA queda sin fila (0 filas, declara 1)",
  c.execute("SELECT COUNT(*) FROM results WHERE operation_id=?",
            (op1,)).fetchone()[0] == 0 and
  c.execute("SELECT n_results FROM operations WHERE operation_id=?",
            (op1,)).fetchone()["n_results"] == 1)
v("1.3: solo hay UNA fila: no hay historial de observaciones",
  c.execute("SELECT COUNT(*) FROM results WHERE result_id='MOD_1'"
            ).fetchone()[0] == 1)
obs["mismo_contenido_2_ops"] = (op1, op2, dueno)

# --- 2. contenido DISTINTO con el MISMO identificador ---------------------
print("\n--- 2. contenido distinto, mismo result_id ---")
op3 = reg(c, [{"result_id": "MOD_1", "value": {"arch": "ARM"}}], "c")
val = c.execute("SELECT value FROM results WHERE result_id='MOD_1'"
                ).fetchone()["value"]
print("  valor tras la 3a: %s | dueño: %s" % (val, c.execute(
    "SELECT operation_id FROM results WHERE result_id='MOD_1'"
).fetchone()["operation_id"]))
v("2.1: el contenido ANTERIOR fue destruido sin dejar rastro",
  "ARM" in val and "x86" not in val, val)
v("2.2: el dueño cambio otra vez",
  c.execute("SELECT operation_id FROM results WHERE result_id='MOD_1'"
            ).fetchone()["operation_id"] == op3)
v("2.3: MOD_2 (contenido anterior) no existe ya en ninguna forma",
  c.execute("SELECT COUNT(*) FROM results WHERE result_id='MOD_2'"
            ).fetchone()[0] == 0)

# --- 3. repeticion de la MISMA operacion ---------------------------------
print("\n--- 3. repeticion identica (mismo id, mismo contenido) ---")
opA = reg(c, [{"result_id": "MOD_R", "value": {"k": 1}}], "ra")
d1 = c.execute("SELECT operation_id FROM results WHERE result_id='MOD_R'"
               ).fetchone()["operation_id"]
opB = reg(c, [{"result_id": "MOD_R", "value": {"k": 1}}], "rb")
d2 = c.execute("SELECT operation_id FROM results WHERE result_id='MOD_R'"
               ).fetchone()["operation_id"]
v("3.1: la repeticion TAMBIEN reasigna (idempotencia es de contenido, "
  "no de operacion)", d1 == opA and d2 == opB, "antes=%s despues=%s" % (d1, d2))
v("3.2: no hay duplicacion de fila",
  c.execute("SELECT COUNT(*) FROM results WHERE result_id='MOD_R'"
            ).fetchone()[0] == 1)
v("3.3: la 1a repeticion es irrecuperable como fila propia",
  c.execute("SELECT COUNT(*) FROM results WHERE operation_id=?",
            (opA,)).fetchone()[0] == 0)

# --- 4. referencias desde edges y execution_events ------------------------
print("\n--- 4. referencias externas ---")
opE = reg(c, [{"result_id": "MOD_E", "value": {"e": 1}}], "e")
S.registrar_evento(c, "run", "modelo.test",
                   {"operation_id": opE, "results": [{"result_id": "MOD_E"}],
                    "ejecucion": {"exit_status": 0},
                    "backend": {"backend_id": "t"}, "limitations": [],
                    "trace_id": "MOD_T"}, [])
c.execute("INSERT OR IGNORE INTO edges(src,tipo,dst,status,scope,tool,"
          "evidence_json,operation_id,result_id,timestamp) "
          "VALUES('s4','REF','d4','ok','binary','t','[]',?,'MOD_E','2026')",
          (opE,))
c.commit()
reg(c, [{"result_id": "MOD_E", "value": {"e": 2}}], "e2")
edge_op = c.execute("SELECT operation_id FROM edges WHERE src='s4'"
                    ).fetchone()["operation_id"]
real_op = c.execute("SELECT operation_id FROM results WHERE result_id='MOD_E'"
                    ).fetchone()["operation_id"]
ev_op = c.execute("SELECT operation_id FROM execution_events WHERE "
                  "result_id='MOD_E'").fetchone()["operation_id"]
print("  edges->%s | results dueño real->%s | execution_events->%s"
      % (edge_op, real_op, ev_op))
v("4.1: edges y execution_events NO se reasignan (FK solo sobre operation_id)",
  edge_op == opE and ev_op == opE)
v("4.2: edges queda apuntando a una operacion SIN el resultado",
  edge_op != real_op)
v("4.3: execution_events conserva la observacion ORIGINAL (procedencia intacta)",
  ev_op == opE and real_op != opE)

# --- 5. recuperacion historica de AMBAS observaciones ---------------------
print("\n--- 5. ¿se pueden recuperar las DOS observaciones? ---")
r1 = S.explicar_operacion(c, opE)
r2 = S.explicar_operacion(c, opA)
print("  explicar(opE) status=%s limitations=%s"
      % (r1.get("status"), bool(r1.get("limitations"))))
print("  explicar(opA) status=%s limitations=%s"
      % (r2.get("status"), bool(r2.get("limitations"))))
v("5.1: la observacion ORIGINAL sigue siendo recuperable como operacion",
  r1.get("status") == "ok")
v("5.2: NO puede recuperar SU resultado (fue reasignado)",
  len(r1.get("results") or []) == 0)
v("5.3: la observacion PERDIDA declara la discrepancia (no la calla)",
  any("discrepancia" in str(x) for x in (r1.get("limitations") or [])),
  r1.get("limitations"))
v("5.4: el contenido VIEJO de MOD_E es irrecuperable",
  c.execute("SELECT COUNT(*) FROM results WHERE result_id='MOD_E' AND "
            "value LIKE '%e\": 1%'").fetchone()[0] == 0)
v("5.5: execution_events es el UNICO testigo de que existio la observacion",
  c.execute("SELECT COUNT(*) FROM execution_events WHERE result_id='MOD_E'"
            ).fetchone()[0] == 1)

# --- 6. que dice el codigo, no la intuicion ------------------------------
print("\n--- 6. la intencion declarada por los PRODUCTORES ---")
src = open(os.path.join(PKG, "backends", "adapters", "rz_inspect.py")).read()
i = src.find("def _id_resultado")
doc = src[i:i + 700]
print("  " + doc.split('"""')[1].strip().replace("\n", "\n  ")[:400])
v("6.1: el productor declara que el id NO debe depender solo del texto",
  "no colisiona" in doc or "NO colisiona" in doc)
v("6.2: el productor documenta que OR REPLACE colapsaba filas en silencio",
  "36 filas" in doc or "convertible en" in doc)

c.close()

print("\n=== HALLAZGOS ESTRUCTURALES ===")
print("  - 1 fila por result_id: NO hay historial de observaciones")
print("  - el dueño de un result_id es la ULTIMA observacion")
print("  - el contenido anterior se destruye sin rastro")
print("  - edges/execution_events conservan la procedencia ORIGINAL")
print("  - execution_events es el unico testigo de observacion previa")
print("\n=== RESULTADO: %d PASS, %d FAIL ===" % (n - len(fails), len(fails)))
if fails:
    for f in fails:
        print("  FAIL:", f)
    sys.exit(1)
print("MODELOS CONTRASTADOS")
sys.exit(0)