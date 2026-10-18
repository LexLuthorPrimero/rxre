#!/usr/bin/env python3
"""RXRE-013 AGUA: trazabilidad de aplicación de lecciones (sin duplicar).

Reutiliza execution_events (event-log durable, sin tabla nueva) con la
columna `lecciones_json`. Distingue:
  - surfaceada: id aparece en un plan/run
  - candidata_aplicada: run POSTERIOR exit_status=0 (indicio, no prueba).
"""
import json, os, sys, tempfile, shutil

PKG = "/home/lucas/Escritorio/rxre/tools"; RXRE = PKG + "/rxre"
BASE = os.environ.get("RXRE_TEST_TMPDIR", "/var/tmp")
sys.path.insert(0, PKG)
sys.path.insert(0, RXRE)
from rxre.core import store

work = tempfile.mkdtemp(prefix="agua_013_", dir=BASE)
db = os.path.join(work, "agua.sqlite3")
os.environ["RXRE_DB"] = db
c = store.conectar()
store._asegurar_columnas_execution_events(c)

ok = []

rid = store.registrar_reflexion(
    c, feedback="f", reflection="r", outcome="failure",
    capability="binary.inspect", target="binary.inspect", refs=[],
    strategy="usar decode", check_ejecutable="tools/rxre/tests/test_umr_decode003.py").get("reflexion_id")

# H1: plan event persists the id verbatim
eid = store.registrar_evento(c, "plan", "binary.inspect",
    {"persistido": True, "limitations": [],
     "trace_id": "t1",
     "ejecucion": {"exit_status": None}},
    [{"reflexion_id": rid}])
persisted = json.loads(c.execute("SELECT lecciones_json FROM execution_events WHERE evento_id=?", (eid,)).fetchone()[0])
assert rid in persisted, "id no persistido"
info = store.trazar_aplicacion_lecciones(c, "binary.inspect")
one = next(x for x in info["lecciones"] if x["reflexion_id"] == rid)
assert one["veces_surfaceada"] >= 1
assert one["candidate_aplicada"] is False
ok.append("H1: plan event persists leccion id en execution_events.lecciones_json")
ok.append("H1: trazar devuelve surfaceada sin candidate (sin run posterior)")

# H2: capability sin lecciones -> sin_datos
empty = store.trazar_aplicacion_lecciones(c, "binary.decompile")
assert empty["estado"] == "empty", empty
ok.append("H2: capability sin lecciones -> sin_datos")

# H3: candidate solo tras run posterior exit_status=0
store.registrar_evento(c, "run", "binary.inspect",
    {"persistido": True, "limitations": [],
     "ejecucion": {"exit_status": 0}}, [])
info2 = store.trazar_aplicacion_lecciones(c, "binary.inspect")
one2 = next(x for x in info2["lecciones"] if x["reflexion_id"] == rid)
assert one2["candidate_aplicada"] is True
ok.append("H3: run exit_status=0 posterior -> candidate_aplicada True (indicio)")

# NEG: run posterior que falla NO marca candidate por si solo
store.registrar_reflexion(
    c, feedback="g", reflection="h", outcome="failure",
    capability="binary.decompile", refs=[], strategy="s",
    check_ejecutable="tools/rxre/tests/test_umr_decode003.py")
rid2 = c.execute("SELECT reflexion_id FROM reflexiones ORDER BY rowid DESC LIMIT 1").fetchone()[0]
store.registrar_evento(c, "plan", "binary.decompile",
    {"persistido": True, "limitations": [], "ejecucion": {"exit_status": None}},
    [{"reflexion_id": rid2}])
store.registrar_evento(c, "run", "binary.decompile",
    {"persistido": True, "limitations": [], "ejecucion": {"exit_status": 1}}, [])
info3 = store.trazar_aplicacion_lecciones(c, "binary.decompile")
rp = next(x for x in info3["lecciones"] if x["reflexion_id"] == rid2)
assert rp["candidate_aplicada"] is False
ok.append("NEG: run fallido posterior -> candidate_aplicada False")

for o in ok:
    print("PASS", o)
print("=== %d/%d ===" % (len(ok), len(ok)))
shutil.rmtree(work, ignore_errors=True)
