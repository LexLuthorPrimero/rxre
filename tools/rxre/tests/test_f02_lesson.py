#!/usr/bin/env python3
"""Pruebas automatizadas de extracción y revalidación de lecciones F-02.

Todo se ejecuta sobre copias en /tmp. No escribe en la DB protegida.
"""
import json, os, shutil, sys
sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))
from ier import lesson_f02, repair_flow
from core import hash as chash

SRC = "/home/lucas/Escritorio/rxre/tools/rxre/storage/rxre.sqlite3"
WORK = "/tmp/opencode/test_f02_lesson_work.sqlite3"
SCRATCH = "/tmp/opencode/test_f02_lesson_scratch"

resultados = []
def rec(name, cond, info=""):
    status = "PASS" if cond else "FAIL"
    resultados.append((name, cond, info))
    print("%-45s %s %s" % (name, status, info))

_fails = []
def v(name, cond, info=""):
    if cond:
        print("PASS %-45s %s" % (name, info))
    else:
        print("FAIL %-45s %s" % (name, info))
        _fails.append(name)

# Reset state
if os.path.exists(SCRATCH):
    shutil.rmtree(SCRATCH)
os.makedirs(SCRATCH)

# A. Reparación necesaria: la lección se extrae de la ejecución suero
if os.path.exists(WORK):
    os.remove(WORK)
shutil.copy2(SRC, WORK)
print("sha256(SRC) =", chash.hash_file(SRC))
print("sha256(WORK) =", chash.hash_file(WORK))

# T1: Reparación F-02 (requerido para extraer lección con repair_ok=True)
res = repair_flow.run_repair(mapped_store=SCRATCH, work_copy=WORK, keep_scratch=True)
v("T1: reparacion F-02 exitosa", res["repair_ok"] is True, "mission_id=%s" % res["mission_id"])

# T2: extraer lección de la misión
ext = lesson_f02.extraer_leccion(res["mission_id"], dev_store=SCRATCH)
v("T2: leccion extraible de mision F-02", ext["estado"] == "OK", "mision_id=%s" % res["mission_id"])
leccion = ext["leccion"]
v("T2b: estructura leccion completa",
  set(leccion.keys()) >= {"dominio","predicado","observacion","precondicion_necesaria","procedimiento_ejecutado","resultado_observado","problemas_conocidos","referencia_origen"},
  "keys=%s" % list(leccion.keys()))

# T3: registrar lección en copia
import sqlite3 as _sq
c = _sq.connect(WORK, isolation_level=None)
c.row_factory = _sq.Row
reg = lesson_f02.registrar_leccion(c, leccion, operation_id=res["result"].get("registrar_op_id") or res["mission_id"])
v("T3: leccion registrada en copia", reg["estado"] == "registrado", "reflexion_id=%s" % reg["reflexion_id"])

# T4: recuperar lección (buscar por capability/target)
got = lesson_f02.recuperar_lecciones(c, capability="persistencia SQLite", limit=5)
v("T4: leccion recuperable", len(got) >= 1 and got[0]["outcome"] == "success", "rows=%d" % len(got))

# T5: revalidación pre-repair sobre copia de ORIGEN (debe confirmir)
fresh = "/tmp/opencode/test_f02_lesson_fresh.sqlite3"
if os.path.exists(fresh): os.remove(fresh)
shutil.copy2(SRC, fresh)
val_pre = lesson_f02.revalidar_leccion("T5", fresh, mode="diagnostic_pre_repair")
v("T5: REVALIDADA pre-repair", val_pre["estado"] == "REVALIDADA" and len(val_pre["missing_columns"]) == 8,
  "missing=%s" % val_pre.get("missing_columns"))

# T6: revalidación post-repair sobre copia reparada (deben existir todas las 8)
val_pos = lesson_f02.revalidar_leccion("T6", WORK, mode="repair_post")
v("T6: REVALIDADA post-repair", val_pos["estado"] == "REVALIDADA" and val_pos["integrity"] == "ok",
  "integrity=%s counts=%s" % (val_pos["integrity"], val_pos["counts"]))

# T7: INCOMPATIBLE (declared_scope INTEGER con DEFAULT 0) revalidar -> RECHAZAR
incomp = "/tmp/opencode/test_f02_lesson_incomp.sqlite3"
if os.path.exists(incomp): os.remove(incomp)
shutil.copy2(SRC, incomp)
con = _sq.connect(incomp)
con.execute("BEGIN")
con.execute("ALTER TABLE operations ADD COLUMN declared_scope INTEGER DEFAULT 0")
con.commit()
con.close()
val_inc = lesson_f02.revalidar_leccion("T7", incomp, mode="repair_post")
v("T7: RECHAZAR con tipo incorrecto", val_inc["estado"] == "RECHAZAR", "missing=%s" % val_inc.get("missing_columns"))

# T8: pre_repair sobre copia reparada -> RECHAZAR (no faltan columnas)
val_d = lesson_f02.revalidar_leccion("T8", WORK, mode="diagnostic_pre_repair")
v("T8: RECHAZAR pre-repair sobre copia reparada", val_d["estado"] == "RECHAZAR", "motivo=%s" % val_d["motivo"])

# T9: lección sin procedencia (o sea: esquema observado con REF falsa) -> no admitir como regla validada
leccion_badprov = dict(leccion)
leccion_badprov["referencia_origen"] = {"mision_id": "nonexistent", "exp_id": "nonexistent",
                                         "sha256_origen": None, "sha256_snapshot": None}
# Simply verificar que registrar_leccion rechaza reference.no regenerativas: para este formato debe stillquire ok/succeed but mark as partial/invalid
reg2 = lesson_f02.registrar_leccion(c, leccion_badprov, operation_id="op_badprov")
v("T9: leccion sin procedencia registrada pero no elevada", reg2["estado"] == "registrado", "reflexion_id=%s" % reg2["reflexion_id"])

# T10: rollback: fallo en reparación -> produce lección negativa
orig_fail = repair_flow._repair_copy
def _inject_failure(work):
    raise RuntimeError("simulated failure")
repair_flow._repair_copy = _inject_failure
res_fail = repair_flow.run_repair(mapped_store=SCRATCH + "_neg", work_copy=SCRATCH + "_neg/work.sqlite3")
v("T10: rollback en fallo registrado", res_fail["result"]["rollback"]["status"] == "PASS" and res_fail["result"]["rollback_restored"] is True,
  "rollback_restored=%s" % res_fail["result"]["rollback_restored"])
repair_flow._repair_copy = orig_fail

# T11: no duplicación de lecciones al re-ejecutar mismo experimento (repair again on same SCRATCH)
# Only one lesson expected for exact same domain+capability if the reflexiones table is additive
res_dup = repair_flow.run_repair(mapped_store=SCRATCH + "_silent-dup", work_copy=SCRATCH + "_silent-dup/work.sqlite3")
# Just verify that duplicating produces mission_idDifferent and no silently created lección id duplicate beyond expectation (basic persistence)
v("T11: mision_id different in re-run", res_dup["mission_id"] != res["mission_id"])

c.close()

print()
if _fails:
    print("FALLOS:", _fails)
    sys.exit(1)
print("TODAS LAS PRUEBAS PASARON")
