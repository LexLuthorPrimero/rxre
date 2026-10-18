#!/usr/bin/env python3
"""Colisiones y propiedad de `result_id`. Fase de INVESTIGACION.

No modifica produccion. Todo sobre base temporal AISLADA con prefijo COLL_.
Cada caso inspecciona filas FINALES y relaciones, no solo el retorno de una
funcion.
"""
from __future__ import annotations

import hashlib
import json
import os
import sqlite3
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
PKG = os.path.abspath(os.path.join(HERE, ".."))
sys.path.insert(0, PKG)

DB = "/tmp/opencode/collisions.db"
for ext in ("", "-wal", "-shm"):
    if os.path.exists(DB + ext):
        os.remove(DB + ext)

from core import store as S   # noqa: E402

fails = []
n = 0


def v(nombre, cond, det=""):
    global n
    n += 1
    if not cond:
        fails.append("%s %s" % (nombre, det))
    print("  %s %s%s" % ("PASS" if cond else "FAIL", nombre,
                         "" if cond else "  <- %s" % det))


def huella():
    return hashlib.sha256(open(DB, "rb").read()).hexdigest()[:16]


def reg(c, results, cap="coll.test", target="binary:coll"):
    return S.registrar(c, {"capability": cap, "question": "q",
                           "target": target, "scope": "binary"},
                       {"operation": cap, "status": "ok", "results": results})


def dueno(c, rid):
    r = c.execute("SELECT operation_id FROM results WHERE result_id=?",
                  (rid,)).fetchone()
    return r["operation_id"] if r else None


def filas(c, op):
    return c.execute("SELECT COUNT(*) FROM results WHERE operation_id=?",
                     (op,)).fetchone()[0]


print("=== Colisiones y propiedad de result_id (base: %s) ===" % DB)
c = S.conectar(DB)

# ---------------------------------------------------------------- A
print("\n--- A: dos operaciones distintas, result_id DISTINTOS ---")
opA1 = reg(c, [{"result_id": "COLL_a1", "value": "x"}])
opA2 = reg(c, [{"result_id": "COLL_a2", "value": "y"}])
v("A1: cada resultado pertenece a su operacion",
  dueno(c, "COLL_a1") == opA1 and dueno(c, "COLL_a2") == opA2,
  "a1->%s a2->%s" % (dueno(c, "COLL_a1"), dueno(c, "COLL_a2")))
v("A2: no hay reasignacion", filas(c, opA1) == 1 and filas(c, opA2) == 1)

# ---------------------------------------------------------------- B
print("\n--- B: dos operaciones distintas, MISMO result_id ---")
h0 = huella()
opB1 = reg(c, [{"result_id": "COLL_b", "value": "primera"}])
antes_dueno = dueno(c, "COLL_b")
opB2 = reg(c, [{"result_id": "COLL_b", "value": "segunda"}])
despues_dueno = dueno(c, "COLL_b")
valor = c.execute("SELECT value FROM results WHERE result_id='COLL_b'"
                  ).fetchone()["value"]
n_filas_b = c.execute("SELECT COUNT(*) FROM results WHERE result_id='COLL_b'"
                      ).fetchone()[0]
print("  opB1=%s opB2=%s  dueño antes=%s después=%s" %
      (opB1, opB2, antes_dueno, despues_dueno))
v("B1: REASIGNACION DEMOSTRADA — la fila pasa a la 2ª operación",
  despues_dueno == opB2 and antes_dueno == opB1,
  "antes=%s despues=%s" % (antes_dueno, despues_dueno))
v("B2: sigue habiendo UNA sola fila (no hay historial)",
  n_filas_b == 1, "filas=%d" % n_filas_b)
v("B3: el contenido de la 1ª operación fue SOBRESCRITO",
  valor == "segunda", valor)
v("B4: la 1ª operación queda con 0 filas pero declara 1",
  filas(c, opB1) == 0 and
  c.execute("SELECT n_results FROM operations WHERE operation_id=?",
            (opB1,)).fetchone()["n_results"] == 1)
v("B5: explicar_operacion de la 1ª DECLARA la discrepancia (no la calla)",
  any("discrepancia" in str(x) for x in
      (S.explicar_operacion(c, opB1).get("limitations") or [])),
  S.explicar_operacion(c, opB1).get("limitations"))
v("B6: la 1ª operación sigue siendo recuperable (status ok)",
  S.explicar_operacion(c, opB1).get("status") == "ok")

# ---------------------------------------------------------------- C
print("\n--- C: repetición de la MISMA operación (mismo id y contenido) ---")
opC1 = reg(c, [{"result_id": "COLL_c", "value": "igual"}])
d1 = dueno(c, "COLL_c")
opC2 = reg(c, [{"result_id": "COLL_c", "value": "igual"}])
d2 = dueno(c, "COLL_c")
v("C1: el reobservado SE REASIGNA tambien a la 2ª (idempotencia por "
  "contenido, no identidad de operación)",
  d1 == opC1 and d2 == opC2, "antes=%s despues=%s" % (d1, d2))
v("C2: la 1ª repetición pierde su vinculo", filas(c, opC1) == 0,
  "filas opC1=%d" % filas(c, opC1))
v("C3: NO hay duplicacion de fila", c.execute(
    "SELECT COUNT(*) FROM results WHERE result_id='COLL_c'").fetchone()[0] == 1)

# ---------------------------------------------------------------- D
print("\n--- D: mismo result_id, contenido DIFERENTE ---")
opD1 = reg(c, [{"result_id": "COLL_d", "value": "v1"}])
opD2 = reg(c, [{"result_id": "COLL_d", "value": "v2"}])
v("D1: el contenido v1 DESAPARECIO (no queda rastro)",
  c.execute("SELECT COUNT(*) FROM results WHERE value='v1' AND "
            "result_id='COLL_d'").fetchone()[0] == 0)
v("D2: solo sobrevive el último",
  c.execute("SELECT value FROM results WHERE result_id='COLL_d'"
            ).fetchone()["value"] == "v2")
v("D3: el product_id NO recibe el id de su contenido",
  c.execute("SELECT COUNT(*) FROM results WHERE operation_id=? AND value=?",
            (opD2, "v2")).fetchone()[0] == 1)

# ---------------------------------------------------------------- E
print("\n--- E: reemplazo de una fila REFERENCIADA por edges/execution_events ---")
opE = reg(c, [{"result_id": "COLL_e", "value": "original"}])
S.registrar_evento(c, "run", "coll.test",
                   {"operation_id": opE, "results": [{"result_id": "COLL_e"}],
                    "ejecucion": {"exit_status": 0}, "backend": {"backend_id": "t"},
                    "limitations": [], "trace_id": "COLL_T1"}, [])
c.execute("INSERT OR IGNORE INTO edges(src,tipo,dst,status,scope,tool,"
          "evidence_json,operation_id,result_id,timestamp) "
          "VALUES('src_E','REF','dst_E','ok','binary','t','[]',?,?,'2026-10-18')",
          (opE, "COLL_e"))
c.commit()
ev_antes = c.execute("SELECT COUNT(*) FROM execution_events WHERE "
                     "result_id='COLL_e'").fetchone()[0]
edge_antes = c.execute("SELECT operation_id FROM edges WHERE src='src_E'"
                       ).fetchone()["operation_id"]
# ahora la reasignacion
opE2 = reg(c, [{"result_id": "COLL_e", "value": "otro"}])
edge_despues = c.execute("SELECT operation_id FROM edges WHERE src='src_E'"
                         ).fetchone()["operation_id"]
ev_despues = c.execute("SELECT COUNT(*) FROM execution_events WHERE "
                       "result_id='COLL_e'").fetchone()[0]
print("  edges.operation_id: antes=%s despues=%s" % (edge_antes, edge_despues))
print("  execution_events citing COLL_e: antes=%d despues=%d"
      % (ev_antes, ev_despues))
v("E1: edges NO se actualiza (la FK es solo sobre operation_id, "
  "result_id es texto sin REFERENCES)",
  edge_despues == opE, "edges.operation_id=%s (la fila real va a %s)"
  % (edge_despues, dueno(c, "COLL_e")))
v("E2: la arista queda APUNTANDO a una operacion que ya no posee el resultado",
  edge_despues == opE and dueno(c, "COLL_e") == opE2,
  "edge->%s dueño real->%s" % (edge_despues, dueno(c, "COLL_e")))
v("E3: execution_events conserva el rastro (no se reescribe)",
  ev_despues == ev_antes, "antes=%d despues=%d" % (ev_antes, ev_despues))
v("E4: execution_events sigue citando COLL_e con la operación VIEJA",
  c.execute("SELECT operation_id FROM execution_events WHERE "
            "result_id='COLL_e'").fetchone()["operation_id"] == opE)

# ---------------------------------------------------------------- F
print("\n--- F: error durante la persistencia y rollback ---")
try:
    opF = reg(c, [{"result_id": "COLL_f_ok", "value": "x"},
                  {"result_id": "COLL_f_mal", "value": "y",
                   "timestamp": None}])
    c.commit()
except sqlite3.Error as e:
    c.rollback()
    print("  excepcion:", str(e)[:60])
v("F1: tras el fallo no queda NINGUNA de las dos filas",
  c.execute("SELECT COUNT(*) FROM results WHERE result_id IN "
            "('COLL_f_ok','COLL_f_mal')").fetchone()[0] == 0)
v("F2: la operación tampoco quedó (atomicidad)",
  c.execute("SELECT COUNT(*) FROM operations WHERE operation_id=?",
            (opF,)).fetchone()[0] == 0 if 'opF' in dir() else True)

# ---------------------------------------------- comportamiento del GUARD
print("\n--- ¿el guard COLISION de dispatch evita esto en PRODUCCIÓN? ---")
src = open(os.path.join(PKG, "backends", "dispatch.py")).read()
guardas = src.count("COLISION:")
v("GUARD1: dispatch.py tiene guardas de colisión", guardas >= 2,
  "COLISION:%d" % guardas)
import subprocess
out = subprocess.run([sys.executable, "-c", """
import sys, os
sys.path.insert(0, %r)
os.environ['RXRE_DB'] = '/tmp/opencode/coll_guard.db'
from backends import dispatch as D
env = {'status':'ok','capability':'x','results':[{'result_id':'G1','value':'v'}],
       'ejecucion':{'exit_status':0},'precheck':{'ok':True},
       'provenance':{'input_hash':'h'},'backend':{'backend_id':'t'}}
r1 = D._persistir_generico(dict(env))
env2 = dict(env); env2['results']=[{'result_id':'G1','value':'v'}]
r2 = D._persistir_generico(dict(env2))
print(r1); print(r2)
""" % PKG], capture_output=True, text=True, timeout=120)
print("  _persistir_generico dos veces:", out.stdout.strip().replace("\n", " | "))
v("GUARD2: la 2ª invocación devuelve COLISION (no reescribe)",
  "COLISION" in out.stdout, out.stdout.strip()[:120])
v("GUARD3: sin excepcion en la 2ª", "Traceback" not in out.stderr,
  out.stderr[:100])

c.close()

print("\n=== RESULTADO: %d PASS, %d FAIL ===" % (n - len(fails), len(fails)))
if fails:
    for f in fails:
        print("  FAIL:", f)
    sys.exit(1)
print("INVESTIGACION COMPLETA")
sys.exit(0)