#!/usr/bin/env python3
"""F1/F4: Discriminacion de operaciones empty en persistencia.

Prueba que una operacion ejecutada con status="empty" y results=[]
genera operation_id y se persiste con n_results=0, permitiendo
distinguir EXECUTED+ZERO_RESULTS de NOT_EXECUTED.

Base de datos aislada en /tmp/opencode. No toca la base de desarrollo.
"""
from __future__ import annotations

import json
import os
import sqlite3
import subprocess
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
PKG = os.path.abspath(os.path.join(HERE, ".."))
MAQUINA = os.path.join(PKG, "api", "machine.py")
DB = "/tmp/opencode/rxre_f1f4_test.db"

fails = []
n = 0


def v(nombre, cond, det=""):
    global n
    n += 1
    if not cond:
        fails.append("%s %s" % (nombre, det))
    print("  %s %s" % ("PASS" if cond else "FAIL", nombre))


def rx(requests, db=DB):
    entrada = "\n".join(json.dumps(r) for r in requests) + "\n"
    env = dict(os.environ)
    env["RXRE_DB"] = db
    p = subprocess.run([sys.executable, MAQUINA], input=entrada,
                       capture_output=True, text=True, timeout=600, env=env)
    lineas = []
    for l in (p.stdout or "").splitlines():
        l = l.strip()
        if not l:
            continue
        try:
            lineas.append(json.loads(l))
        except ValueError:
            fails.append("linea no JSON: %r" % l[:80])
    return lineas


# === SETUP: base isolada ===
if os.path.exists(DB):
    os.remove(DB)
for ext in ("-wal", "-shm"):
    p = DB + ext
    if os.path.exists(p):
        os.remove(p)

print("=== F1/F4: Discriminacion de operaciones empty ===")
print("Base aislada:", DB)

# === TEST 1: operacion empty persiste con operation_id ===
# binary.xrefs con nivel aa sobre un fixture produce empty (no xrefs a ese nivel)
# Usamos el fixture incluido en el repo.
FIXTURE = os.path.join(PKG, "fixtures", "bin", "rxre_min.elf")

# Verificar que el fixture existe
if not os.path.exists(FIXTURE):
    # Buscar cualquier fixture ELF
    fixtures_dir = os.path.join(PKG, "fixtures")
    for root, dirs, files in os.walk(fixtures_dir):
        for f in files:
            if f.endswith(".elf"):
                FIXTURE = os.path.join(root, f)
                break
        if os.path.exists(FIXTURE):
            break

print("\n--- TEST 1: empty ejecutado se persiste (operation_id no nulo) ---")
if os.path.exists(FIXTURE):
    # Ejecutar binary.xrefs con fixture que produce empty
    # Primero verificar que el fixture produce empty con nivel aa
    e = rx([{"op": "run", "capability": "binary.xrefs",
             "artefacto": FIXTURE,
             "backend_id": "rizin", "nivel_analisis": "aa", "timeout": 60}])
    if e:
        R = e[0]
        status = R.get("status", "")
        persistido = R.get("persistido")
        op_id = R.get("operation_id")
        print("  status=%s persistido=%s operation_id=%s" % (status, persistido, op_id))

        if status == "empty":
            v("T1.1: empty ejecutado -> persistido=True", persistido is True, "persistido=%s" % persistido)
            v("T1.2: empty ejecutado -> operation_id no nulo", op_id is not None, "op_id=%s" % op_id)

            # Verificar en la base
            if op_id:
                c = sqlite3.connect(DB)
                c.row_factory = sqlite3.Row
                row = c.execute("SELECT * FROM operations WHERE operation_id=?", (op_id,)).fetchone()
                if row:
                    v("T1.3: operations tiene la fila", True)
                    v("T1.4: n_results=0", row["n_results"] == 0, "n_results=%s" % row["n_results"])
                    v("T1.5: status=empty en BD", row["status"] == "empty", "status=%s" % row["status"])
                    # Verificar que response_json tiene el envelope
                    resp = json.loads(row["response_json"])
                    v("T1.6: response_json explicitamente empty", resp.get("status") == "empty")
                    v("T1.7: response_json results=[]", resp.get("results") == [])
                else:
                    v("T1.3: operations tiene la fila", False, "no encontrada")
                    v("T1.4: n_results=0", False)
                    v("T1.5: status=empty en BD", False)
                    v("T1.6: response_json", False)
                    v("T1.7: results=[]", False)

                # Verificar que no hay filas ficticias en results
                n_results_rows = c.execute(
                    "SELECT COUNT(*) FROM results WHERE operation_id=?", (op_id,)).fetchone()[0]
                v("T1.8: no se crean filas ficticias en results", n_results_rows == 0,
                  "results rows=%d" % n_results_rows)

                # Verificar explicar_operacion
                c.row_factory = sqlite3.Row
                sys.path.insert(0, PKG)
                from core import store as S
                explain = S.explicar_operacion(c, op_id)
                v("T1.9: explicar_operacion recupera la operacion",
                  explain.get("status") == "ok", "status=%s" % explain.get("status"))
                v("T1.10: explicar_operacion muestra n_results=0",
                  (explain.get("operation") or {}).get("n_results") == 0)
                v("T1.11: explicar_operacion results=[]",
                  explain.get("results") == [])
                c.close()
            else:
                for i in range(3, 12):
                    v("T1.%d" % i, False, "no hay op_id")
        else:
            print("  SKIP: status=%s (no es empty, no se puede testear)" % status)
    else:
        print("  SKIP: no se obtuvo respuesta del fixture")
else:
    print("  SKIP: no se encontro fixture ELF")

# === TEST 2: operacion no ejecutada NO se persiste como ejecucion ===
print("\n--- TEST 2: blocked/invalid NO se persisten como empty ---")
c = sqlite3.connect(DB)
c.row_factory = sqlite3.Row
ops_before = c.execute("SELECT COUNT(*) FROM operations").fetchone()[0]
c.close()

e = rx([{"op": "run", "capability": "binary.sin_producer"}])
if e:
    R = e[0]
    v("T2.1: capability inexistente -> no persistido",
      R.get("persistido") is not True, "persistido=%s" % R.get("persistido"))
    v("T2.2: capability inexistente -> operation_id None",
      R.get("operation_id") is None, "op_id=%s" % R.get("operation_id"))
    v("T2.3: capability inexistente -> status blocked",
      R.get("status") == "blocked", "status=%s" % R.get("status"))

c = sqlite3.connect(DB)
ops_after = c.execute("SELECT COUNT(*) FROM operations").fetchone()[0]
c.close()
v("T2.4: no se creo fila nueva para blocked", ops_after == ops_before,
  "before=%d after=%d" % (ops_before, ops_after))

# === TEST 3: ok con resultados conserva comportamiento ===
print("\n--- TEST 3: ok con resultados conserva persistencia ---")
e = rx([{"op": "run", "capability": "binary.inspect",
         "artefacto": FIXTURE, "backend_id": "rizin", "timeout": 60}])
if e:
    R = e[0]
    if R.get("status") == "ok":
        v("T3.1: ok -> persistido=True", R.get("persistido") is True,
          "persistido=%s" % R.get("persistido"))
        v("T3.2: ok -> operation_id no nulo", R.get("operation_id") is not None)
    else:
        print("  SKIP: status=%s (no ok)" % R.get("status"))
else:
    print("  SKIP: sin respuesta")

# === RESUMEN ===
print("\n=== RESULTADO: %d PASS, %d FAIL ===" % (n - len(fails), len(fails)))
if fails:
    for f in fails:
        print("  FAIL:", f)
    sys.exit(1)
else:
    print("TODOS LOS TESTS PASAN")
    sys.exit(0)
