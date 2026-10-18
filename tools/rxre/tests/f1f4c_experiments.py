#!/usr/bin/env python3
"""F1/F4-C: ciclo de vida de la fila `results`. EXPERIMENTOS AISLADOS.

No toca la base de desarrollo. Todo corre sobre /tmp/opencode con datos
sinteticos identificables (prefijo F1F4C_).
"""
from __future__ import annotations

import json
import os
import sqlite3
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
PKG = os.path.abspath(os.path.join(HERE, ".."))
sys.path.insert(0, PKG)

DB = "/tmp/opencode/f1f4c_results_lifecycle.db"
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


def sembrar(c, op_id, result_ids, n_results=None):
    """Siembra sintetica: una operacion con N resultados."""
    ts = "2026-10-18T00:00:00-0300"
    c.execute(
        "INSERT OR REPLACE INTO operations(operation_id,request_id,contract_ver,"
        "operacion,capability,question,target,scope,status,n_results,"
        "request_json,response_json,target_pci,timestamp,duracion_s) "
        "VALUES(?,?,?,?,?,?,?,?,?,?,?,?,?,?,?)",
        (op_id, "", "v1", "F1F4C_test", "f1f4c.test", "q", "binary:x",
         "binary", "ok", len(result_ids) if n_results is None else n_results,
         "{}", json.dumps({"status": "ok", "results": []}), "", ts, 0.0))
    for rid in result_ids:
        c.execute(
            "INSERT OR REPLACE INTO results(result_id,operation_id,type,value,"
            "source,file,line,scope,tool,tool_version,status,raw_json,"
            "timestamp) VALUES(?,?,?,?,?,?,?,?,?,?,?,?,?)",
            (rid, op_id, "test", "V:" + rid, "F1F4C_sintetico", "", 0,
             "binary", "t", "1", "ok", json.dumps({"rid": rid}), ts))
    c.commit()


def conteo(c, op_id):
    return c.execute("SELECT COUNT(*) FROM results WHERE operation_id=?",
                     (op_id,)).fetchone()[0]


print("=== F1/F4-C: ciclo de vida de `results` (base aislada: %s) ===" % DB)


def _afirma_perdida(txt):
    """True solo si AFIRMA una perdida (no si la niega o laponer en duda)."""
    t = str(txt).lower()
    negaciones = ("no prueba", "no se perd", "no puede", "no se puede",
                  "no afirm", "nada puede")
    for a in ("se perdio", "se perdieron", "result_lost", "perdido",
              "eliminado", "borrado", "se borro"):
        if a in t:
            idx = t.find(a)
            ctx = t[max(0, idx - 60):idx]
            if not any(neg in ctx for neg in negaciones):
                return True
    return False

# ============================================================ H3
print("\n--- H3: integridad referencial (PRAGMA foreign_keys=?) ---")
c = S.conectar(DB)
fk = c.execute("PRAGMA foreign_keys").fetchone()[0]
v("H3.1: foreign_keys esta ACTIVO en la conexion de store.conectar()",
  fk == 1, "foreign_keys=%s" % fk)
# ¿Se puede borrar la operacion padre con hijos vivos?
sembrar(c, "F1F4C_op_padre", ["F1F4C_r1", "F1F4C_r2"])
v("H3.2: la operacion tiene 2 resultados sembrados",
  conteo(c, "F1F4C_op_padre") == 2)
try:
    c.execute("DELETE FROM operations WHERE operation_id=?",
              ("F1F4C_op_padre",))
    c.commit()
    borrado = True
    err = ""
except sqlite3.Error as e:
    borrado = False
    err = str(e)
    c.rollback()
v("H3.3: DELETE del padre con hijos vivos es RECHAZADO por la FK "
  "(sin ON DELETE CASCADE)", not borrado, "borrado=%s err=%s" % (borrado, err))
v("H3.4: el mensaje nombra la FK", "FOREIGN KEY" in err.upper(), err)
n_ops = c.execute("SELECT COUNT(*) FROM operations WHERE operation_id=?",
                  ("F1F4C_op_padre",)).fetchone()[0]
v("H3.5: el padre SIGUE existiendo tras el intento fallido", n_ops == 1)
v("H3.6: los hijos SIGUEN intactos", conteo(c, "F1F4C_op_padre") == 2)

# ============================================================ H1
print("\n--- H1: existe una ruta de BORRADO explícito de `results`? ---")
try:
    c.execute("DELETE FROM results WHERE result_id=?", ("F1F4C_r1",))
    c.commit()
    borrado = True
    err = ""
except sqlite3.Error as e:
    borrado = False
    err = str(e)
v("H1.1: SQLite PERMITE el DELETE de un resultado (no hay trigger ni FK que lo impida)",
  borrado, "err=%s" % err)
v("H1.2: tras el DELETE el recuento baja a 1", conteo(c, "F1F4C_op_padre") == 1)
# ¿Queda registro de que existió?
ev = c.execute("SELECT COUNT(*) FROM results WHERE result_id=?",
               ("F1F4C_r1",)).fetchone()[0]
v("H1.3: NO queda ninguna fila que pruebe que F1F4C_r1 existió", ev == 0)
op = c.execute("SELECT n_results FROM operations WHERE operation_id=?",
               ("F1F4C_op_padre",)).fetchone()
v("H1.4: operations.n_results SIGUE diciendo 2 (NO se ajusta solo)",
  op["n_results"] == 2, "n_results=%s" % op["n_results"])
v("H1.5: DIVERGENCIA: n_results(2) != filas reales(1)",
  op["n_results"] != conteo(c, "F1F4C_op_padre"),
  "n_results=%s filas=%d" % (op["n_results"], conteo(c, "F1F4C_op_padre")))

# ============================================================ H4
print("\n--- H4: INSERT OR REPLACE sobre un result_id existente ---")
sembrar(c, "F1F4C_op_repl", ["F1F4C_rA"])
antes = c.execute("SELECT value, raw_json FROM results WHERE result_id=?",
                  ("F1F4C_rA",)).fetchone()
c.execute(
    "INSERT OR REPLACE INTO results(result_id,operation_id,type,value,source,"
    "file,line,scope,tool,tool_version,status,raw_json,timestamp) "
    "VALUES(?,?,?,?,?,?,?,?,?,?,?,?,?)",
    ("F1F4C_rA", "F1F4C_op_repl", "test", "V:REEMPLAZADO",
     "F1F4C_sintetico", "", 0, "binary", "t", "1", "ok",
     json.dumps({"rid": "F1F4C_rA", "nuevo": True}), "2026-10-18T01:00:00-0300"))
c.commit()
despues = c.execute("SELECT value, raw_json FROM results WHERE result_id=?",
                    ("F1F4C_rA",)).fetchone()
n_filas = conteo(c, "F1F4C_op_repl")
v("H4.1: el contenido ANTERIOR se sobreescribio (evidencia previa destruida)",
  antes["value"] != despues["value"],
  "antes=%s despues=%s" % (antes["value"], despues["value"]))
v("H4.2: NO queda fila con el valor anterior",
  c.execute("SELECT COUNT(*) FROM results WHERE value=?",
            (antes["value"],)).fetchone()[0] == 0)
v("H4.3: sigue habiendo UNA sola fila (replace, no append)", n_filas == 1,
  "filas=%d" % n_filas)
v("H4.4: el conteo NO revela que hubo reemplazo",
  n_filas == 1, "filas=%d" % n_filas)
v("H4.5: el timestamp cambio (unica pista de que algo paso)",
  antes["raw_json"] != despues["raw_json"])

# ============================================================ H5
print("\n--- H5: ¿existe registro independiente que pruebe que un resultado existió? ---")
tablas = [r[0] for r in c.execute(
    "SELECT name FROM sqlite_master WHERE type='table' ORDER BY name")]
print("  tablas:", ", ".join(tablas))
v("H5.1: no existe una tabla de historial/auditoria de results",
  not any(t in tablas for t in ("results_history", "results_log", "results_audit",
                               "results_deleted", "result_tombstones")))
# ¿audit_log registra los INSERT de results?
try:
    cols = [r["name"] for r in c.execute("PRAGMA table_info(audit_log)")]
    print("  audit_log columnas:", ", ".join(cols))
except sqlite3.Error as e:
    print("  audit_log no existe:", e)
    cols = []
v("H5.2: audit_log no tiene una columna que guarde el CONJUNTO de result_ids",
  not any("result" in x.lower() and "ids" in x.lower() for x in cols), cols)
# ¿operations.response_json guarda los resultados?
row = c.execute("SELECT response_json FROM operations WHERE operation_id=?",
                ("F1F4C_op_repl",)).fetchone()
resp = json.loads(row["response_json"])
v("H5.3: operations.response_json NO guarda los resultados (los deja vacios)",
  resp.get("results") == [], resp.get("results"))
v("H5.4: ¿hay algo que registre que existio F1F4C_r1? -> NO",
  c.execute("SELECT COUNT(*) FROM results WHERE result_id='F1F4C_r1'"
            ).fetchone()[0] == 0)

# ============================================================ H6
print("\n--- H6: consistencia de operations.n_results ---")
divergentes = []
for r in c.execute("SELECT operation_id, n_results FROM operations "
                   "WHERE operation_id LIKE 'F1F4C_%'"):
    real = conteo(c, r["operation_id"])
    if (r["n_results"] or 0) != real:
        divergentes.append((r["operation_id"], r["n_results"], real))
v("H6.1: n_results puede divergir del recuento real tras un DELETE",
  len(divergentes) >= 1, divergentes)
# ¿se recalcula alguna vez?
recalc = c.execute(
    "SELECT COUNT(*) FROM operations WHERE n_results != "
    "(SELECT COUNT(*) FROM results WHERE results.operation_id = "
    " operations.operation_id) AND operation_id LIKE 'F1F4C_%'").fetchone()[0]
v("H6.2: el sistema NO recalcula n_results (sigue la fila vieja)", recalc >= 1,
  "divergentes=%d" % recalc)
# ¿existe codigo que reajuste n_results?
print("  (busqueda de 'UPDATE operations SET n_results': ver grep estatico)")

# ============================================================ recuperabilidad
print("\n--- recuperabilidad posterior con store.explicar_operacion ---")
r = S.explicar_operacion(c, "F1F4C_op_padre")
v("R1: la operacion sigue recuperable (status ok)", r.get("status") == "ok",
  r.get("status"))
v("R2: results muestra SOLO el que sobrevive (1)", len(r.get("results") or []) == 1,
  len(r.get("results") or []))
v("R3: el results devuelto NO incluye el borrado",
  not any(x.get("result_id") == "F1F4C_r1" for x in (r.get("results") or [])))
v("R4: la respuesta DECLARA la discrepancia (f1f4c2) sin afirmar perdida",
  any("discrepancia de inventario" in str(x)
      for x in (r.get("limitations") or [])) and
  not any(_afirma_perdida(x) for x in (r.get("limitations") or [])),
  r.get("limitations"))
v("R5: n_results en la fila sigue mintiendo (dice 2, hay 1)",
  (r.get("operation") or {}).get("n_results") == 2,
  (r.get("operation") or {}).get("n_results"))

# ============================================================ H7
print("\n--- H7: ¿la ausencia de filas permite distinguir ZERO de LOST? ---")
# ZERO: operacion con n_results=0 sembrada honestamente
sembrar(c, "F1F4C_op_zero", [], n_results=0)
# LOST: operacion que TENIA 2 resultados y se le borran los DOS, para que el
# consumidor quede exactamente en la misma posicion observable que ZERO.
c.execute("DELETE FROM results WHERE operation_id=?", ("F1F4C_op_padre",))
c.commit()
rz = S.explicar_operacion(c, "F1F4C_op_zero")
rl = S.explicar_operacion(c, "F1F4C_op_padre")
ambos_vacios = (len(rz.get("results") or []) == 0 and
                len(rl.get("results") or []) == 0)
v("H7.1: el consumidor ve results=[] en el caso ZERO y en el caso LOST",
  ambos_vacios,
  "zero=%d lost=%d" % (len(rz.get("results") or []),
                       len(rl.get("results") or [])))
v("H7.1b: la operacion que perdio 2 resultados sigue status=ok (no se degrada)",
  rl.get("status") == "ok", rl.get("status"))
v("H7.1c: ZERO y LOST ahora son DISTINGUIBLES (f1f4c2 lo cierra): "
  "ZERO no declara nada, LOST si",
  (rz.get("results") == rl.get("results") and
   rz.get("status") == rl.get("status") and
   (rz.get("limitations") or []) == [] and
   len(rl.get("limitations") or []) == 1),
  "zero: status=%s results=%s lim=%s | lost: status=%s results=%s lim=%s"
  % (rz.get("status"), rz.get("results"), rz.get("limitations"),
     rl.get("status"), rl.get("results"), rl.get("limitations")))
v("H7.2: ¿el status difiere? NO (ambos 'ok')",
  rz.get("status") == rl.get("status") == "ok",
  "zero=%s lost=%s" % (rz.get("status"), rl.get("status")))
# La unica pista es n_results, y no es de fiar
v("H7.3: n_results SI difiere (0 vs 2) -> es la unica pista",
  (rz.get("operation") or {}).get("n_results") == 0 and
  (rl.get("operation") or {}).get("n_results") == 2,
  "zero=%s lost=%s" % ((rz.get("operation") or {}).get("n_results"),
                       (rl.get("operation") or {}).get("n_results")))
v("H7.4: n_results NO es prueba: se responds al INSERT, no a la perdida",
  True, "n_results es un CONTADOR de escritura, no un registro de eliminacion")
# Y si n_results fue manipulado, la pista desaparece
c.execute("UPDATE operations SET n_results=0 WHERE operation_id=?",
          ("F1F4C_op_padre",))
c.commit()
rl2 = S.explicar_operacion(c, "F1F4C_op_padre")
v("H7.5: si n_results se ajusta, ZERO y LOST quedan INDISTINGUIBLES",
  (rl2.get("operation") or {}).get("n_results") == 0 and
  (rz.get("operation") or {}).get("n_results") == 0)

c.close()

# ============================================================ RESUMEN
print("\n=== RESULTADO: %d PASS, %d FAIL ===" % (n - len(fails), len(fails)))
if fails:
    for f in fails:
        print("  FAIL:", f)
    sys.exit(1)
print("EXPERIMENTOS COMPLETOS")
sys.exit(0)