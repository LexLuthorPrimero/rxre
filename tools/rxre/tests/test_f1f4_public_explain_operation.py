#!/usr/bin/env python3
"""F1/F4-PUBLIC: `op:explain` recupera una operacion por `operation_id`.

La brecha que cierra: una operacion ejecutada con `status="empty"` y
`results=[]` no tiene `result_id` (no hay resultados), luego la superficie
publica no tenia forma de recuperarla. `store.explicar_operacion` ya existia y
distingue `status:"ok"` de `status:"empty"`; lo que faltaba era el cable desde
la superficie publica.

Todo corre contra una base temporal AISLADA en /tmp/opencode. No se toca
`tools/rxre/storage/rxre.sqlite3`.
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
DB = "/tmp/opencode/rxre_f1f4_public_test.db"
FIXTURE = os.path.join(PKG, "fixtures", "bin", "rxre_min.elf")

fails = []
n = 0


def v(nombre, cond, det=""):
    global n
    n += 1
    if not cond:
        fails.append("%s %s" % (nombre, det))
    print("  %s %s%s" % ("PASS" if cond else "FAIL", nombre,
                         "" if cond else "  <- %s" % det))


def rx(requests):
    entrada = "\n".join(json.dumps(r) for r in requests) + "\n"
    env = dict(os.environ)
    env["RXRE_DB"] = DB
    p = subprocess.run([sys.executable, MAQUINA], input=entrada,
                       capture_output=True, text=True, timeout=900, env=env)
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


# === AISLAMIENTO: base temporal propia, y verificacion de que se usa ===
print("=== F1/F4-PUBLIC: explicacion por operation_id ===")
print("Base de las pruebas:", DB)
if os.path.exists(DB):
    os.remove(DB)
for ext in ("-wal", "-shm"):
    if os.path.exists(DB + ext):
        os.remove(DB + ext)

DEV_DB = os.path.join(PKG, "storage", "rxre.sqlite3")
dev_mtime_before = os.stat(DEV_DB).st_mtime if os.path.exists(DEV_DB) else None
dev_count_before = None
if dev_mtime_before is not None:
    _c = sqlite3.connect(DEV_DB)
    dev_count_before = _c.execute("SELECT COUNT(*) FROM operations").fetchone()[0]
    _c.close()

# === SEMILLA: una operacion empty (n_results=0) y una ok (n_results>=1) ===
# Se siembran por la superficie publica real, no a mano: asi se prueba el
# camino completo y no una base fabricada.
if not os.path.exists(FIXTURE):
    found = None
    for root, _d, files in os.walk(os.path.join(PKG, "fixtures")):
        for f in files:
            if f.endswith(".elf"):
                found = os.path.join(root, f)
                break
        if found:
            break
    FIXTURE = found

print("\n--- SEMILLA: operacion empty ejecutada (results=[]) ---")
empty_op = None
ok_op = None
ok_rid = None
if FIXTURE:
    e = rx([{"op": "run", "capability": "binary.xrefs",
             "artefacto": FIXTURE,
             "fixture_json": open("/bin/ls", "rb").read().hex(),
             "backend_id": "rizin", "nivel_analisis": "aa", "timeout": 60}])
    if e and e[0].get("status") == "empty":
        empty_op = e[0].get("operation_id")
        print("  empty: status=%s persistido=%s op_id=%s"
              % (e[0].get("status"), e[0].get("persistido"), empty_op))
    e2 = rx([{"op": "run", "capability": "binary.inspect",
              "artefacto": FIXTURE, "backend_id": "rizin", "timeout": 60}])
    if e2 and e2[0].get("status") == "ok":
        ok_op = e2[0].get("operation_id")
        rs = e2[0].get("results") or []
        ok_rid = rs[0].get("result_id") if rs else None
        print("  ok: status=%s op_id=%s result_id=%s"
              % (e2[0].get("status"), ok_op, ok_rid))
else:
    print("  SKIP: no hay fixture ELF")

# ---------------------------------------------------------------- H2
print("\n--- H2: operacion empty recuperable por la superficie publica ---")
if empty_op:
    e = rx([{"op": "explain", "operation_id": empty_op}])
    R = e[0] if e else {}
    v("H2.1: explain por operation_id -> status ok",
      R.get("status") == "ok", "status=%s motivo=%s"
      % (R.get("status"), R.get("motivo")))
    v("H2.2: devuelve el operation_id pedido",
      R.get("operation_id") == empty_op, R.get("operation_id"))
    op = R.get("operation") or {}
    v("H2.3: la operacion viene con su fila",
      bool(op), sorted(op)[:4])
    v("H2.4: n_results=0 (cero resultados, no ausencia)",
      op.get("n_results") == 0, "n_results=%s" % op.get("n_results"))
    v("H2.5: el envelope persistido dice status=empty",
      op.get("status") == "empty", op.get("status"))
    v("H2.6: results=[] explicito",
      R.get("results") == [], R.get("results"))
    v("H2.7: la cadena del backend es recuperable (evidencia de ejecucion)",
      bool(R.get("backend")), sorted(R.get("backend") or {})[:5])
    v("H2.8: declara por que se consulted",
      R.get("consulta_por") == "operation_id", R.get("consulta_por"))
    # La prueba que importa: la operacion NO es indistinguible de "nunca ocurrio"
    resp = json.loads(op.get("response_json") or "{}")
    v("H2.9: response_json conserva la evidencia de ejecucion",
      bool((resp.get("ejecucion") or {}).get("exit_status") is not None),
      "ejecucion=%s" % (resp.get("ejecucion") or {}).get("exit_status"))
    # MEDIDO: `rz_xrefs.persistir` NO copia el `limitations` del productor al
    # envelope; las limitaciones viajan dentro de `cadena_backend`. La
    # asercion mira donde ESTAN, no donde uno supone que deberian estar.
    v("H2.10: la cadena del backend conserva sus limitaciones",
      isinstance((resp.get("cadena_backend") or {}).get("limitaciones"), list),
      "limitaciones=%s"
      % type((resp.get("cadena_backend") or {}).get("limitaciones")).__name__)
else:
    for i in range(1, 11):
        v("H2.%d" % i, False, "no se pudo sembrar la operacion empty")

# ---------------------------------------------------------------- H6
print("\n--- H6: existente-con-cero-resultos != inexistente ---")
if empty_op:
    e_real = rx([{"op": "explain", "operation_id": empty_op}])[0]
    e_fake = rx([{"op": "explain", "operation_id": "op_0000000000000000"}])[0]
    v("H6.1: la existente NO es 'empty'", e_real.get("status") == "ok",
      e_real.get("status"))
    v("H6.2: la inexistente SI es 'empty'", e_fake.get("status") == "empty",
      e_fake.get("status"))
    v("H6.3: la existente trae la fila de la operacion",
      bool(e_real.get("operation")))
    v("H6.4: la inexistente NO trae fila de operacion",
      not e_fake.get("operation"), "operation=%s" % e_fake.get("operation"))
    v("H6.5: la inexistente declara que la ausencia NO prueba no-ejecucion",
      any("NO es que" in str(x) for x in (e_fake.get("limitations") or [])),
      e_fake.get("limitations"))
    v("H6.6: los dos status son distintos (distinguibles por el consumidor)",
      e_real.get("status") != e_fake.get("status"))
else:
    for i in range(1, 7):
        v("H6.%d" % i, False, "sin operacion empty sembrada")

# ---------------------------------------------------------------- H3
print("\n--- H3: operation_id inexistente = ausencia clara, sin fabricar ---")
e = rx([{"op": "explain", "operation_id": "op_noexiste_jamas_9999"}])
R = e[0] if e else {}
v("H3.1: status=empty (ausencia, no ok)", R.get("status") == "empty",
  R.get("status"))
v("H3.2: NO fabrica una operacion", not R.get("operation"))
v("H3.3: NO fabrica resultados", R.get("results", []) == []
  if isinstance(R.get("results"), list) else True,
  "results=%s" % R.get("results"))
v("H3.4: declara la limitacion", bool(R.get("limitations")),
  R.get("limitations"))
v("H3.5: echoes el id pedido", R.get("operation_id") == "op_noexiste_jamas_9999")

# ---------------------------------------------------------------- H1 / H5
print("\n--- H1/H5: compatibilidad del camino por result_id ---")
if ok_rid:
    e = rx([{"op": "explain", "result_id": ok_rid}])
    R = e[0] if e else {}
    v("H5.1: explain por result_id -> status ok",
      R.get("status") == "ok", R.get("status"))
    v("H5.2: conserva el contrato: devuelve 'result'",
      bool(R.get("result")), sorted(R)[:6])
    v("H5.3: conserva el contrato: devuelve 'result_id'",
      R.get("result_id") == ok_rid, R.get("result_id"))
    v("H5.4: conserva el contrato: devuelve 'chain'",
      bool(R.get("chain")), R.get("chain"))
    v("H5.5: conserva el contrato: NO marca consulta_por",
      not R.get("consulta_por"), R.get("consulta_por"))
    v("H5.6: NO declara limitacion de ignores si no hay operation_id",
      not any("junto a" in str(x) for x in (R.get("limitations") or [])),
      R.get("limitations"))
else:
    print("  SKIP: no se sembro operacion ok con result_id")

# ---------------------------------------------------------------- H1 (precedencia)
print("\n--- H1: ambos identificadores presentes ---")
if empty_op and ok_rid:
    e = rx([{"op": "explain", "result_id": ok_rid,
             "operation_id": empty_op}])
    R = e[0] if e else {}
    v("H1.1: gana result_id (el contrato previo no se rompe)",
      bool(R.get("result")) and R.get("result_id") == ok_rid,
      "result=%s rid=%s" % (bool(R.get("result")), R.get("result_id")))
    v("H1.2: DECLARA que operation_id fue ignorado",
      any("junto a" in str(x) for x in (R.get("limitations") or [])),
      R.get("limitations"))
    v("H1.3: status sigue siendo ok (no se degrada)",
      R.get("status") == "ok", R.get("status"))
else:
    print("  SKIP: falta sembrar ambos identificadores")

# ---------------------------------------------------------------- H4
print("\n--- H4: argumentos ausentes o invalidos ---")
R = rx([{"op": "explain"}])[0]
v("H4.1: sin identificadores -> invalid_input",
  R.get("status") == "invalid_input", R.get("status"))
v("H4.2: el motivo nombra los dos identificadores",
  "result_id" in str(R.get("motivo")) and "operation_id" in str(R.get("motivo")),
  R.get("motivo"))
v("H4.3: no intenta recuperar nada", not R.get("operation")
  and not R.get("results"))

R = rx([{"op": "explain", "result_id": "", "operation_id": ""}])[0]
v("H4.4: identificadores vacios -> invalid_input",
  R.get("status") == "invalid_input", R.get("status"))

R = rx([{"op": "explain", "operation_id": 12345}])[0]
v("H4.5: operation_id no-string (int) NO se trata como existente",
  R.get("status") in ("empty", "invalid_input"),
  "status=%s" % R.get("status"))
v("H4.6: un id numerico no fabrica operacion", not R.get("operation"))

R = rx([{"op": "explain", "operation_id": ["op_a", "op_b"]}])[0]
v("H4.7: operation_id lista -> no fabrica operacion",
  not R.get("operation"), "operation=%s" % R.get("operation"))

R = rx([{"op": "explain", "operation_id": None}])[0]
v("H4.8: operation_id null explicito -> invalid_input",
  R.get("status") == "invalid_input", R.get("status"))

# ---------------------------------------------- flags de la vista por resultado
print("\n--- los flags de la vista por resultado se DECLARAN, no se fingen ---")
if empty_op:
    R = rx([{"op": "explain", "operation_id": empty_op,
             "root_cause": True, "audit": True}])[0]
    v("F1: root_cause NO se aplica en la vista por operacion",
      "root_cause" not in R, sorted(k for k in R if "root" in k))
    v("F2: audit NO se aplica en la vista por operacion",
      "gate" not in R, sorted(k for k in R if k == "gate"))
    v("F3: se DECLARA que no se aplicaron",
      any("NO aplica" in str(x) for x in (R.get("limitations") or [])),
      R.get("limitations"))
    v("F4: el status sigue siendo ok (declarar no es fallar)",
      R.get("status") == "ok", R.get("status"))

# ---------------------------------------------- la operacion vacia NO inventa rid
print("\n--- no se inventa result_id para una operacion sin resultados ---")
if empty_op:
    R = rx([{"op": "explain", "operation_id": empty_op}])[0]
    v("G1: la respuesta no trae 'result' (no hay resultado que traer)",
      "result" not in R, sorted(k for k in R if k == "result"))
    v("G2: la respuesta no trae 'result_id' sintetico",
      not R.get("result_id"), R.get("result_id"))
    c = sqlite3.connect(DB)
    c.row_factory = sqlite3.Row
    n_res = c.execute("SELECT COUNT(*) FROM results WHERE operation_id=?",
                      (empty_op,)).fetchone()[0]
    v("G3: la BD no tiene filas de results para esa operacion",
      n_res == 0, "rows=%d" % n_res)
    c.close()

# ---------------------------------------------- aislamiento de la BD
print("\n--- AISLAMIENTO: la base de desarrollo no fue tocada ---")
if dev_mtime_before is not None:
    dev_mtime_after = os.stat(DEV_DB).st_mtime
    v("A1: mtime de la BD de desarrollo sin cambios",
      dev_mtime_before == dev_mtime_after,
      "antes=%s despues=%s" % (dev_mtime_before, dev_mtime_after))
    _c = sqlite3.connect(DEV_DB)
    dev_count_after = _c.execute("SELECT COUNT(*) FROM operations").fetchone()[0]
    _c.close()
    v("A2: numero de operaciones de la BD de desarrollo sin cambios",
      dev_count_before == dev_count_after,
      "antes=%d despues=%d" % (dev_count_before, dev_count_after))
else:
    v("A1: no existe BD de desarrollo", True)
c = sqlite3.connect(DB)
n_ops = c.execute("SELECT COUNT(*) FROM operations").fetchone()[0]
v("A3: la base de pruebas SI tiene operaciones (pruebo la base correcta)",
  n_ops >= 1, "ops=%d" % n_ops)
c.close()

# ================================================================ RESUMEN
print("\n=== RESULTADO: %d PASS, %d FAIL ===" % (n - len(fails), len(fails)))
if fails:
    for f in fails:
        print("  FAIL:", f)
    sys.exit(1)
print("TODOS LOS TESTS PASAN")
sys.exit(0)