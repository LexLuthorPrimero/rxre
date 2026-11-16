#!/usr/bin/env python3
"""Prueba INTEGRAL del ciclo RXRE EE: investigación → reparación → aprendizaje → revalidación.

Esta prueba no verifica que los módulos existan: verifica que pueden ejecutar el ciclo
completo de extremo a extremo y que los identificadores/hashes persisten correctamente.
"""
import os, sys, json, shutil
sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))
from ier import investigate_f02, repair_flow, lesson_f02, mission

SRC = "/home/lucas/Escritorio/rxre/tools/rxre/storage/rxre.sqlite3"
SCRATCH = "/tmp/opencode/m10-integrated-rxre"
shutil.rmtree(SCRATCH, ignore_errors=True)
os.makedirs(SCRATCH)

results = {}

def check(name, cond, info=""):
    results[name] = {"estado": "PASS" if cond else "FAIL", "info": info}
    print(("PASS" if cond else "FAIL"), name, info)

# 1. Investigate
inv = investigate_f02.run_flow(ier_store=SCRATCH + "/investigate", db_copy=SCRATCH + "/inv.sqlite3")
check("T-int-1: investigación completada",
      inv.get("status") == "PASS_PARTIAL" and inv.get("mision_id"), f"mision_id={inv.get('mision_id')}")
mision = mission.cargar(inv["mision_id"], path=SCRATCH + "/investigate")
check("T-int-2: misión persistida y recuperación",
      mision["mission_id"] == inv["mision_id"] and len(mision.get("experiments", [])) >= 1,
      f"experiments={len(mision.get('experiments', []))}")

# 2. repair_flow
rep = repair_flow.run_repair(mapped_store=SCRATCH + "/repair", work_copy=SCRATCH + "/rep.sqlite3")
check("T-int-3: reparación controlada ejecutada",
      rep.get("repair_ok") is True and rep.get("result", {}).get("repair_id"), f"repair_id={rep.get('result', {}).get('repair_id')}")

# 3. lesson from repair
out = lesson_f02.extraer_leccion(rep["mission_id"], dev_store=SCRATCH + "/repair")
check("T-int-4: lección extraída de la reparación",
      out.get("estado") == "OK" and out.get("leccion", {}).get("referencia_origen", {}).get("mision_id") == rep["mission_id"],
      f"mision_id={rep['mission_id']}")

# 4. registrar lección en la COPIA REPARADA (origg members preserved)
work = rep["work_copy"]
import sqlite3 as _sq
c = _sq.connect(work, isolation_level=None)
c.row_factory = _sq.Row
reg = lesson_f02.registrar_leccion(c, out["leccion"], operation_id=rep["result"].get("registrar_op_id") or rep["mission_id"])
check("T-int-5: lección persistida en copia reparada",
      reg.get("estado") == "registrado" and reg.get("reflexion_id"),
      f"reflexion_id={reg.get('reflexion_id')}")

# 5. Recuperar lección en proceso nuevo
rec = lesson_f02.recuperar_lecciones(c, capability="persistencia SQLite", limit=5)
check("T-int-6: lección recuperable",
      len(rec) >= 1 and rec[0].get("outcome") == "success",
      f"rows={len(rec)}")

# 6. Revalidar lección sobre copia reparada (post)
val_post = lesson_f02.revalidar_leccion(reg["reflexion_id"], work, mode="repair_post")
check("T-int-7: revalidación post-repair",
      val_post.get("estado") == "REVALIDADA" and val_post.get("integrity") == "ok",
      f"integrity={val_post.get('integrity')}")

# 7. Revalidar lección PRE sobre copia FRESH (antes de reparar, cols missing)
fresh = SCRATCH + "/fresh.sqlite3"
shutil.copy2(SRC, fresh)
val_pre = lesson_f02.revalidar_leccion(reg["reflexion_id"], fresh, mode="diagnostic_pre_repair")
check("T-int-8: revalidación pre-repair sobre copia fresca",
      val_pre.get("estado") == "REVALIDADA" and len(val_pre.get("missing_columns", [])) == 8,
      f"missing_columns={val_pre.get('missing_columns')}")

# 8. Revalidar contra exigido incompleto (column incompatible in copy)
bad = SCRATCH + "/bad.sqlite3"
shutil.copy2(SRC, bad)
ctr = _sq.connect(bad)
ctr.execute("BEGIN")
ctr.execute("ALTER TABLE operations ADD COLUMN declared_scope INTEGER DEFAULT 0")
ctr.commit()
ctr.close()
val_bad = lesson_f02.revalidar_leccion(reg["reflexion_id"], bad, mode="repair_post")
check("T-int-9: incompatibilidad registrada como no reutilizable",
      val_bad.get("estado") == "RECHAZAR",
      f"missing={val_bad.get('missing_columns')}")

# 9. Rollback simulado: origen inalterado si fallo inyectado
import ier.repair_flow as _rf
orig_repair_copy = _rf._repair_copy

def _inject_failure(work):
    raise RuntimeError("inyección de fallo para rollback")

_rf._repair_copy = _inject_failure
try:
    rep_fail = repair_flow.run_repair(mapped_store=SCRATCH + "/fail", work_copy=SCRATCH + "/fail.sqlite3", keep_scratch=True)
    _rf._repair_copy = orig_repair_copy
    rb = rep_fail["result"]["rollback"]
    check("T-int-9b: rollback verificable tras fallo inyectado",
          rb.get("status") == "PASS" and rep_fail["repair_ok"] is False,
          f"rollback={rb}")
except Exception:
    _rf._repair_copy = orig_repair_copy
    check("T-int-9b: rollback verificable tras fallo inyectado", False, "exception observed")

# 10. Integridad protegida: no hubo escritura de la DB protegida
check("T-int-10: DB protegida intacta",
      __import__("hashlib").sha256(open(SRC, "rb").read()).hexdigest() ==
      "195f68fb25db674b41408ee8283df952b158528c9ccb58cdb1dc42b0810f8ef2")

c.close()
print()
fails = [k for k, v in results.items() if v["estado"] != "PASS"]
for k, v in results.items():
    print("%-55s %s %s" % (k, v["estado"], v.get("info","")))
print("\nfails:", fails)
sys.exit(0 if not fails else 1)
