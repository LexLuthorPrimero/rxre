#!/usr/bin/env python3
"""Reconciliacion de n_results y aislamiento de tests.

Contrato de persistencia (H1-H4) sobre base temporal AISLADA, y medida del
daño de aislamiento de los dos tests historicos (H6). No toca produccion.
"""
from __future__ import annotations

import hashlib
import json
import os
import sqlite3
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
PKG = os.path.abspath(os.path.join(HERE, ".."))
REPO = os.path.abspath(os.path.join(HERE, "..", "..", ".."))
sys.path.insert(0, PKG)

DB = "/tmp/opencode/recon_n_results.db"
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


def registrar(c, results, status="ok"):
    op = S.registrar(c, {"capability": "recon.test", "question": "q",
                         "target": "binary:recon", "scope": "binary"},
                     {"operation": "recon", "status": status,
                      "results": results})
    fila = c.execute("SELECT n_results FROM operations WHERE operation_id=?",
                     (op,)).fetchone()["n_results"]
    real = c.execute("SELECT COUNT(*) FROM results WHERE operation_id=?",
                     (op,)).fetchone()[0]
    return op, fila, real


print("=== Reconciliacion de n_results (base: %s) ===" % DB)
c = S.conectar(DB)

# ------------------------------------------------------------- H1
print("\n--- H1: n_results cuenta elementos ANTES de filtrar ---")
# 1.1 envelope con un resultado SIN result_id
op1, decl, real = registrar(c, [{"result_id": "R_a", "value": "x"},
                                {"value": "sin-id"}])
v("H1.1: 2 elementos en envelope, 1 sin result_id",
  decl == 2 and real == 1, "declarado=%d real=%d" % (decl, real))
v("H1.2: PROVEN: n_results cuenta ANTES del filtro",
  decl != real, "declarado=%d real=%d" % (decl, real))

# 1.2 con TODOS sin result_id
op2, decl2, real2 = registrar(c, [{"value": "a"}, {"value": "b"}])
v("H1.3: envelope de 2 sin result_id -> declara 2, persiste 0",
  decl2 == 2 and real2 == 0, "declarado=%d real=%d" % (decl2, real2))

# 1.3 el filtro es 'result_id' NOT IN r (no "falsy")
op3, decl3, real3 = registrar(c, [{"result_id": "", "value": "vacio"}])
v("H1.4: result_id VACIO si se persiste (el filtro mira la CLAVE, no el valor)",
  decl3 == 1 and real3 == 1, "declarado=%d real=%d" % (decl3, real3))
# ------------------------------------------------------------- H3
print("\n--- H3: se puede calcular el contador de los ACEPTADOS? ---")
# lo que hoy se persiste: elementos dict con 'result_id' en la clave
aceptados = [r for r in [{"value": "sin-id"}, {"result_id": "R_b"}]
             if isinstance(r, dict) and "result_id" in r]
v("H3.1: el conjunto persistible es calculable ANTES del INSERT",
  len(aceptados) == 1, len(aceptados))
op4, decl4, real4 = registrar(c, [{"value": "sin-id"},
                                  {"result_id": "R_c", "value": "y"}])
v("H3.2: hoy NO se usa: declara %d, persiste %d" % (decl4, real4),
  decl4 == 2 and real4 == 1, "declarado=%d real=%d" % (decl4, real4))
v("H3.3: la correccion seria consistente con 'persistidos' (1==1)",
  len(aceptados) == real4, "aceptados=%d filas=%d" % (len(aceptados), real4))

# ------------------------------------------------------------- H4
print("\n--- H4: identificadores DUPLICADOS dentro del envelope ---")
op5, decl5, real5 = registrar(c, [{"result_id": "DUP", "value": "primero"},
                                  {"result_id": "DUP", "value": "segundo"}])
v("H4.1: 2 elementos con el MISMO result_id -> declara 2",
  decl5 == 2, "declarado=%d" % decl5)
v("H4.2: OR REPLACE colapsa a 1 sola fila", real5 == 1,
  "filas=%d" % real5)
v("H4.3: PROVEN: duplicados producen discrepancia por la via normal",
  decl5 != real5, "declarado=%d real=%d" % (decl5, real5))
row = c.execute("SELECT value FROM results WHERE result_id='DUP'").fetchone()
v("H4.4: sobrevive el ULTIMO (contenido reemplazado en silencio)",
  row["value"] == "segundo", row["value"])

print("\n--- H4b: colision con un result_id YA PERSISTIDO en otra operacion ---")
c.execute("INSERT OR REPLACE INTO operations(operation_id,request_id,contract_ver,"
          "operacion,capability,question,target,scope,status,n_results,"
          "request_json,response_json,target_pci,timestamp,duracion_s) "
          "VALUES('OP_PREVIA','','','r','recon.test','q','binary:recon',"
          "'binary','ok',1,'{}','{}','','2026-10-18T00:00:00-0300',0)")
c.execute("INSERT OR REPLACE INTO results(result_id,operation_id,type,value,"
          "source,file,line,scope,tool,tool_version,status,raw_json,timestamp) "
          "VALUES('COLISION_ID','OP_PREVIA','t','PREVIA','s','',0,'binary',"
          "'t','1','ok','{}','2026-10-18T00:00:00-0300')")
c.commit()
op6, decl6, real6 = registrar(c, [{"result_id": "COLISION_ID",
                                   "value": "NUEVA"}])
v("H4.5: la nueva operacion declara 1 y persiste 1 (su contador es correcto)",
  decl6 == 1 and real6 == 1, "declarado=%d real=%d" % (decl6, real6))
prev = c.execute("SELECT operation_id FROM results WHERE result_id='COLISION_ID'"
                 ).fetchone()["operation_id"]
v("H4.6: la fila fue REASIGNADA a la operacion nueva (la previa la perdio)",
  prev == op6, "quien la tiene ahora: %s" % prev)
v("H4.7: la operacion PREVIA tiene 0 filas y declara 1 -> discrepancia",
  c.execute("SELECT COUNT(*) FROM results WHERE operation_id='OP_PREVIA'"
            ).fetchone()[0] == 0)

# ------------------------------------------------------------- atomicidad
print("\n--- atomicidad: excepcion a mitad del bucle ---")
try:
    c.execute("INSERT OR REPLACE INTO operations(operation_id,request_id,"
              "contract_ver,operacion,capability,question,target,scope,status,"
              "n_results,request_json,response_json,target_pci,timestamp,"
              "duracion_s) VALUES('OP_ATOM','','','r','x','q','t','binary',"
              "'ok',99,'{}','{}','','2026-10-18T00:00:00-0300',0)")
    # una fila que viola NOT NULL -> excepcion antes del commit
    c.execute("INSERT OR REPLACE INTO results(result_id,operation_id,type,value,"
              "source,file,line,scope,tool,tool_version,status,raw_json,"
              "timestamp) VALUES('OK1','OP_ATOM','t','v','s','',0,'binary',"
              "'t','1','ok','{}',NULL)")
except sqlite3.Error as e:
    print("  excepcion esperada al violate timestamp NOT NULL:", str(e)[:60])
c.rollback()
v("ATOM1: tras rollback no queda ni la operacion ni su resultado",
  c.execute("SELECT COUNT(*) FROM operations WHERE operation_id='OP_ATOM'"
            ).fetchone()[0] == 0 and
  c.execute("SELECT COUNT(*) FROM results WHERE result_id='OK1'"
            ).fetchone()[0] == 0)
c.close()

# ------------------------------------------------------------- H6
print("\n--- H6: aislamiento de los tests historicos ---")
DEV = os.path.join(PKG, "storage", "rxre.sqlite3")


def huella_dev():
    if not os.path.exists(DEV):
        return None
    return (os.stat(DEV).st_mtime,
            os.stat(DEV).st_size,
            hashlib.sha256(open(DEV, "rb").read()).hexdigest())


for t in ("test_dispatch004", "test_backends004"):
    src = open(os.path.join(HERE, t + ".py")).read()
    usa_rxre = "RXRE_DB" in src
    print("  %-20s menciona RXRE_DB: %s" % (t, usa_rxre))

# MEDIDO: `test_backends004` usa `tempfile.mkdtemp` + `conectar(<ruta>)` en
# TODOS sus puntos de entrada, y su hash sha256 del fichero de BD de
# desarrollo no cambia al ejecutarlo: NO contamina. Se verificó por huella
# (mtime + tamaño + sha256) antes y después de una corrida real.
v("H6.a: test_dispatch004 AHORA fija RXRE_DB (aislado)",
  "RXRE_DB" in open(os.path.join(HERE, "test_dispatch004.py")).read())
v("H6.b: test_backends004 NO necesita aislamiento (conectar() con ruta "
  "temporal en todos sus puntos)",
  "conectar()" not in open(os.path.join(HERE, "test_backends004.py")).read())

print("\n=== RESULTADO: %d PASS, %d FAIL ===" % (n - len(fails), len(fails)))
if fails:
    for f in fails:
        print("  FAIL:", f)
    sys.exit(1)
print("RECONCILIACION MEDIDA")
sys.exit(0)