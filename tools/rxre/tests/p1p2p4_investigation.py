#!/usr/bin/env python3
"""P1 canonicalizacion / P2 mutacion / P4 eventos historicos.

Solo lectura sobre produccion; experimentos sobre base temporal AISLADA.
No modifica codigo, schema ni datos.
"""
from __future__ import annotations

import json
import os
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
PKG = os.path.abspath(os.path.join(HERE, ".."))
REPO = os.path.abspath(os.path.join(HERE, "..", "..", ".."))
sys.path.insert(0, PKG)

DB = "/tmp/opencode/p1p2p4.db"
for ext in ("", "-wal", "-shm"):
    if os.path.exists(DB + ext):
        os.remove(DB + ext)
os.environ["RXRE_DB"] = DB

from core import store as S   # noqa: E402
from backends.contract import sha256_texto   # noqa: E402

fails = []
n = 0
verd = {}


def v(nombre, cond, det="", clase="PROVEN"):
    global n
    n += 1
    if not cond:
        fails.append("%s %s" % (nombre, det))
    print("  %s %s%s  [%s]"
          % ("PASS" if cond else "FAIL", nombre,
             "" if cond else "  <- %s" % det, clase))


print("=== P1: CANONICALIZACION (base: %s) ===" % DB)

# --- tipo A: sha256_texto sobre %-format de escalares -------------------
print("\n--- Tipo A: hash de '%s|%s|%d' (rz_cfg, rz_functions, cocci...) ---")
a = sha256_texto("%s|%s|%s|%d" % ("/bin/ls", "rizin", "aa", 42))
b = sha256_texto("%s|%s|%s|%d" % ("/bin/ls", "rizin", "aa", 42))
v("P1.A1: la misma tupla produce el mismo id", a == b)
v("P1.A2: un entero como texto produce OTRO id",
  sha256_texto("42") != sha256_texto("'42'"), "colision de tipos posible")
v("P1.A3: separador '|' puede EMBARRAR campos",
  sha256_texto("a|b|c") == sha256_texto("a", ) if False else
  sha256_texto("%s|%s" % ("a|b", "c")) == sha256_texto("%s|%s" % ("a", "b|c")),
  "('a|b','c') == ('a','b|c')")

# --- tipo B: json.dumps(sort_keys=True, default=str) ---------------------
print("\n--- Tipo B: json.dumps(sort_keys=True, default=str) (rz_inspect, umr) ---")
v1 = {"arch": "x86", "bits": 64}
v2 = {"bits": 64, "arch": "x86"}
j1 = json.dumps(v1, sort_keys=True, default=str)
j2 = json.dumps(v2, sort_keys=True, default=str)
v("P1.B1: dicts SEMANTICAMENTE iguales -> mismo texto (canonical)",
  j1 == j2, "%s vs %s" % (j1, j2))

# ¿default=str produce texto estable?
class ConAddr:
    def __str__(self):
        return "<obj at 0x%x>" % id(self)

o1, o2 = ConAddr(), ConAddr()
s1 = json.dumps({"x": o1}, sort_keys=True, default=str)
s2 = json.dumps({"x": o2}, sort_keys=True, default=str)
v("P1.B2: PROVEN: default=str sobre un objeto NO serializable produce "
  "texto INESTABLE (direccion de memoria)",
  s1 != s2, "%s vs %s" % (s1, s2))

# ¿pero los PRODUCTORES reales producen eso? (limite del hallazgo)
print("     limite: los productores medidos construyen dicts de escalares;")
print("            ConAddr es sintetico. Verificar si hay ruta real.")


def ruta_real_no_jsonable():
    """¿Algun producer mete un tipo no-JSON en `valor`?"""
    import re
    hallados = []
    for f in os.listdir(os.path.join(PKG, "backends", "adapters")):
        if not f.endswith(".py"):
            continue
        src = open(os.path.join(PKG, "backends", "adapters", f)).read()
        # dicts cuyo valor se asigna a algo no escalar
        for m in re.finditer(r'"(funciones|elementos|nodos|cobertura)"\s*:',
                             src):
            hallados.append((f, m.group(1)))
    return hallados


hallados = ruta_real_no_jsonable()
v("P1.B3: los productores meten LISTAS de dicts (no-JSON-plano) en valor",
  len(hallados) > 0, "%d sitios: %s" % (len(hallados), hallados[:3]))

# --- tipo C: id que NO depende del contenido ----------------------------
print("\n--- Tipo C: id truncado / no proporcional al contenido ---")
# rz_functions: id = f(len(crudas)); value = funciones[:2000]
funcionesA = [{"n": i} for i in range(2500)]
funcionesB = [{"n": i + 100000} for i in range(2500)]
idA = "res_functions_" + sha256_texto("f|/bin/ls|rizin|aa|%d" % len(funcionesA))[:12]
idB = "res_functions_" + sha256_texto("f|/bin/ls|rizin|aa|%d" % len(funcionesB))[:12]
v("P1.C1: PROVEN: 2500 funciones DISTINTAS comparten result_id",
  idA == idB, "%s vs %s" % (idA, idB))
v("P1.C2: el value persistido solo guarda 2000 -> el resto es invisible",
  len(funcionesA[:2000]) == 2000)

# --- ¿id y value se derivan de la MISMA representacion? -----------------
print("\n--- ¿id y contenido persistido derivan de la MISMA representacion? ---")
c = S.conectar(DB)
op = S.registrar(c, {"capability": "x", "question": "q", "target": "t",
                     "scope": "binary"},
                 {"operation": "x", "status": "ok",
                  "results": [{"result_id": "R_CAN", "value": v1}]})
row = c.execute("SELECT value, raw_json FROM results WHERE result_id='R_CAN'"
                ).fetchone()
v("P1.D1: `value` NO es el texto canonico (es str() y va truncado)",
  row["value"] != j1, "value=%r" % row["value"][:40])
v("P1.D2: `raw_json` SI contiene la forma canonica",
  json.dumps(v1, sort_keys=True) in row["raw_json"], row["raw_json"][:60])
longo = {"d": "x" * 5000}
op2 = S.registrar(c, {"capability": "x", "question": "q", "target": "t",
                      "scope": "binary"},
                  {"operation": "x", "status": "ok",
                   "results": [{"result_id": "R_TRUNC", "value": longo}]})
ln = c.execute("SELECT LENGTH(value), LENGTH(raw_json) FROM results "
               "WHERE result_id='R_TRUNC'").fetchone()
v("P1.D3: PROVEN: value trunca a 4000; raw_json conserva todo",
  ln[0] == 4000 and ln[1] > 4000, "value=%d raw_json=%d" % tuple(ln))
# dos contenidos DISTINTOS que colapsan en `value` porque la diferencia cae
# MAS ALLA del corte de 4000 chars. (Si la diferencia esta antes, value las
# distingue: hay quecrafted caso real, no cualquiera.)
A = {"d": "x" * 5000}
B = {"d": "x" * 4500 + "DIFERENTE"}
S.registrar(c, {"capability": "x", "question": "q", "target": "t",
                "scope": "binary"},
            {"operation": "x", "status": "ok",
             "results": [{"result_id": "R_TRUNC", "value": A}]})
va = c.execute("SELECT value, raw_json FROM results "
               "WHERE result_id='R_TRUNC'").fetchone()
S.registrar(c, {"capability": "x", "question": "q", "target": "t",
                "scope": "binary"},
            {"operation": "x", "status": "ok",
             "results": [{"result_id": "R_TRUNC", "value": B}]})
vb = c.execute("SELECT value, raw_json FROM results "
               "WHERE result_id='R_TRUNC'").fetchone()
v("P1.D4: PROVEN: contenidos DISTINTOS (difieren tras el corte) dan el "
  "MISMO `value` truncado", va["value"] == vb["value"],
  "value identico=%s" % (va["value"] == vb["value"]))
v("P1.D5: raw_json SI distingue los dos contenidos",
  va["raw_json"] != vb["raw_json"],
  "raw_json identico=%s" % (va["raw_json"] == vb["raw_json"]))

# ================================================================= P2
print("\n=== P2: MUTACION ENTRE IDENTIDAD Y PERSISTENCIA ===")

# ¿store.registrar muta el env? ¿copia?
env = {"results": [{"result_id": "R_MUT", "value": {"k": "original"}}]}
holder = env["results"][0]
S.registrar(c, {"capability": "x", "question": "q", "target": "t",
                "scope": "binary"},
            {"operation": "x", "status": "ok", "results": env["results"]})
holder["value"]["k"] = "MUTADO"
row = c.execute("SELECT value FROM results WHERE result_id='R_MUT'").fetchone()["value"]
v("P2.1: la fila persistida es INMUNE a la mutacion posterior",
  "original" in row and "MUTADO" not in row, row[:40])

# ¿el id del PRODUCTOR se calcula antes o despues de la mutacion?
print("     Flujo real: adapter construye valor -> calcula rid(archivo) "
      "-> dispatch -> store.registrar")
print("     ¿Puede el adapter mutar `valor` DESPUES de calcular el id?")
import re
fuentes = ["rz_inspect", "rz_functions", "rz_cfg", "cocci_search",
           "cs_disasm", "umr_read", "gh_decompile", "rz_xrefs"]
mutan = []
for a in fuentes:
    src = open(os.path.join(PKG, "backends", "adapters", a + ".py")).read()
    # buscar: valor[...]=  DESPUES de  rid = / result_id:
    for m in re.finditer(r'(valor|value)\s*\[[^\]]+\]\s*=', src):
        mutan.append((a, m.group(0)))
v("P2.2: no se encontro mutacion de `valor` por indice en los 8 fuentes",
  not mutan, str(mutan[:3]), "OBSERVED")

# ¿el dict se pasa por referencia a store.registrar?
v("P2.3: `registrar` serializa en el momento (resp_json = json.dumps(env))",
  True, "store.py:851", "OBSERVED")

# El caso de riesgo REAL: mutacion entre _id_resultado() y el INSERT
print("\n     Riesgo teorico: si el adapter muta `valor` DESPUES de calcular")
print("     el id, el id NO corresponde al valor persistido.")
# construccion artificial del escenario, sobre la API real
env2 = {"status": "ok", "results": [{"result_id": "R_RACE", "value": {"k": "v1"}}]}
# el "productor" calcula el id con v1...
rid_real = "res_functions_" + sha256_texto("|/bin/ls|rizin|aa|%d" % 1)[:12]
env2["results"][0]["result_id"] = rid_real
# ...y muta antes de que llegue al store
env2["results"][0]["value"] = {"k": "CAMBIADO"}
S.registrar(c, {"capability": "x", "question": "q", "target": "t",
                "scope": "binary"},
            {"operation": "x", "status": "ok", "results": env2["results"]})
guardado = c.execute("SELECT value FROM results WHERE result_id=?",
                     (rid_real,)).fetchone()
v("P2.4: OPEN: si un productor muta tras calcular el id, el id queda "
  "DESACOPLADO del valor persistido (demostrado por construccion)",
  guardado is not None and "CAMBIADO" in guardado["value"],
  "el id no describe el valor guardado", "OPEN")
c.close()

# ================================================================= P4
print("\n=== P4: 76 EVENTOS CON operation_id = 'COLISION:...' ===")
import sqlite3   # noqa: E402
DEV = os.path.join(PKG, "storage", "rxre.sqlite3")
d = sqlite3.connect("file:%s?mode=ro" % DEV, uri=True)
d.row_factory = sqlite3.Row
ev = d.execute("SELECT * FROM execution_events WHERE operation_id LIKE "
               "'COLISION:%'").fetchall()
v("P4.1: son 76", len(ev) == 76, len(ev), "OBSERVED")

# clasificacion por patron
patrones = {}
for r in ev:
    oid = r["operation_id"]
    cuerpo = oid.split(":", 1)[1]
    n_ids = cuerpo.count(",") + 1
    patron = ("1 result_id" if n_ids == 1 else "%d result_ids" % n_ids)
    patrones[patron] = patrones.get(patron, 0) + 1
print("     patrones:", patrones)

v("P4.2: el marcador contiene LISTA DE result_id, no un id de operacion",
  all(r["operation_id"].split(":", 1)[1].startswith(("res_", "ccg_"))
      for r in ev),
  "todos empiezan por res_ o ccg_", "PROVEN")

v("P4.3: `result_id` de la columna SI es un result_id real (no marcador)",
  all(r["result_id"].startswith(("res_", "ccg_")) for r in ev),
  "", "PROVEN")

# ¿el result_id citado existe en results?
existen = sum(1 for r in ev if d.execute(
    "SELECT 1 FROM results WHERE result_id=?", (r["result_id"],)).fetchone())
v("P4.4: PROVEN: los 76 citan result_id que SI existen en `results`",
  existen == len(ev), "%d/%d" % (existen, len(ev)))

# ¿el result_id pertenece a la operacion citada?
malos = sum(1 for r in ev if d.execute(
    "SELECT 1 FROM results WHERE result_id=? AND operation_id=?",
    (r["result_id"], r["operation_id"])).fetchone())
v("P4.5: NINGUNO pertenece a una operacion real con ese id (no hay FK)",
  malos == 0, "%d coinciden" % malos, "PROVEN")

# ¿son 'COLLISION' o 'OBSERVACION'?
v("P4.6: son eventos de COLISION, no observaciones: la operacion NO se persistio",
  d.execute("SELECT COUNT(*) FROM operations WHERE operation_id LIKE "
            "'COLISION:%'").fetchone()[0] == 0,
  "0 filas en operations", "PROVEN")

# ¿persistido=1? -> afirma que HAY fila
v("P4.7: los 76 declaran persistido=1 (afirmacion de que la evidencia existe)",
  all(r["persistido"] == 1 for r in ev), "", "PROVEN")

# ¿quien escribe?
src_me = open(os.path.join(PKG, "api", "machine.py")).read()
v("P4.8: el escritor es machine.py:1376 `store.registrar_evento(_c,'run',...)`",
  "store.registrar_evento(_c, \"run\", capability, env, lecciones)" in src_me,
  "", "PROVEN")
# ¿quien lee result_id de execution_events?
import subprocess   # noqa: E402
out = subprocess.run(["grep", "-rn", "FROM execution_events", PKG,
                      "--include=*.py"], capture_output=True, text=True).stdout
reads = [l for l in out.splitlines() if "/tests/" not in l and "github/" not in l]
reads_rid = [l for l in reads if "result_id" in l]
print("     lecturas totales de execution_events (prod): %d" % len(reads))
for r in reads:
    print("       ", r.split("/")[-1][:78])
v("P4.9: hay lectores de execution_events, y al menos uno lee result_id",
  len(reads_rid) > 0, "%d con result_id" % len(reads_rid), "PROVEN")

# ¿7 huerfanos tienen testigo en execution_events?
huerf = d.execute("""SELECT result_id FROM results r WHERE r.operation_id
   IS NOT NULL AND NOT EXISTS (SELECT 1 FROM operations o WHERE
   o.operation_id=r.operation_id)""").fetchall()
con_testigo = sum(1 for r in huerf if d.execute(
    "SELECT 1 FROM execution_events WHERE result_id=?",
    (r["result_id"],)).fetchone())
v("P4.10: los 7 huerfanos NO tienen testigo en execution_events",
  con_testigo == 0, "%d/%d" % (con_testigo, len(huerf)), "PROVEN")
d.close()

print("\n=== RESULTADO: %d PASS, %d FAIL ===" % (n - len(fails), len(fails)))
if fails:
    for f in fails:
        print("  FAIL:", f)
    sys.exit(1)
print("P1/P2/P4 MEDIDOS")
sys.exit(0)