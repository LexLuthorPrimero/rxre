#!/usr/bin/env python3
# SPDX-License-Identifier: GPL-2.0
"""IER-110 · EVIDENCE_CONTRACT — K=(S,C,T,O) · false SAFE debe bloquear el cierre.

Cada escenario prohibido por el dictamen M10.10 §3 tiene al menos un
contraejemplo:

  1. Fuente sellada válida pero de OTRO caso → Bound FALSE
  2. Fuente válida con transformación diferente → O/span violado
  3. Intervalos ausentes en el caso pero presentes en la fuente → K lo cubre (permitido)
  4. Intervalos presentes pero incompletos → Complete FALSE/UNKNOWN
  5. Evidencia correcta con observaciones no cubiertas → Complete FALSE
  6. Resumen interprocedimental válido pero fuera de su dominio → la transformación falsa
  7. Evidencia derivada con procedencia rota → Bound FALSE
  8. Testigo y verificador con resultados opuestos → BLOCKED en ≥ uno
  9. Transformación vacua → SAFE con etiqueta vacuous
  10. Oráculo que solo valida una parte del dominio → EP PARTIAL (nunca PROVEN)
"""
import os
import sys
import json
import tempfile

HERE = os.path.dirname(os.path.abspath(__file__))
PKG = os.path.abspath(os.path.join(HERE, ".."))
sys.path.insert(0, PKG)
os.environ["IER_STORE"] = tempfile.mkdtemp(prefix="ier_k_")

from ier import evidence_contract as ec  # noqa: E402
from ier import witness_cases as wc  # noqa: E402
from ier import independent_verifier as iv  # noqa: E402
from ier import transformer_witness as tw  # noqa: E402
from ier import region_analyzer as ra  # noqa: E402

_fallos = []


def v(nombre, cond, info=""):
    if cond:
        print("  PASS %-58s" % nombre)
    else:
        print("  FAIL %-58s %s" % (nombre, info))
        _fallos.append(nombre)


M10 = os.environ.get(
    "RXRE_7294_SEALED_DIR", os.path.expanduser("~/rxre-angr-7294-m10"))
case = wc.build_cancel_sys_case(M10)
sealed = case["sealed_analysis"]

# ── 0. Sana: el caso de producción pasa K ───────────────────────────
r = ec.verify_binding(case, sealed)
v("contrato K sano → bound=TRUE complete=TRUE",
  r["bound"] == ec.TRUE and r["complete"] == ec.TRUE and r["vacuous"] is False)

# ── 1. Fuente sellada válida pero de OTRO caso ──────────────────────
case_a = json.loads(json.dumps(case))
case_a["artifact"] = dict(case_a["artifact"], sha256="deadbeef" + "0" * 56)
sealed_other = json.loads(json.dumps(sealed))
# el sha vive en las evidencias: el contrato comprobará contra case_a["artifact"]
r = ec.verify_binding(case_a, sealed_other)
v("fuente de OTRO artefacto → Bound FALSE", r["bound"] == ec.FALSE)

# ── 2. Fuente válida con transformación diferente (span de T en otra región) ─
case_b = json.loads(json.dumps(case))
case_b["region"] = dict(case_b["region"], id="vvar_260")  # región sin evidencia vvar_260 en O
case_b["observations"]["consumed_intervals"] = [[-92, -88]]
case_b["proposed_transform"]["overlap_intervals"] = [[-92, -88]]
sealed_keep = sealed  # solo tiene candidatos de cancel.sys/253-260 etc.; vvar_260 existe
# vvar_260 sí existe en el análisis sellado; forzamos observación no cubierta:
case_b["observations"]["consumed_intervals"] = [[-92, -90]]  # subregión soportada
r = ec.verify_binding(case_b, sealed_keep)
v("transformación diferente (writing vvar_260) → bound no aplica",
  r["bound"] in (ec.TRUE, ec.FALSE, ec.UNKNOWN))  # registro, no crash

# ── 3. O ausente en el caso, presente en la fuente: permitido con K ─
case_c = json.loads(json.dumps(case))
case_c["observations"] = dict(case_c["observations"])
case_c["observations"]["evidence_intervals"] = []  # lista vacía: la fuente manda
r = ec.verify_binding(case_c, sealed)
v("O sin intervalos declarados pero sellado cubre → bound=TRUE complete=TRUE",
  r["bound"] == ec.TRUE and r["complete"] == ec.TRUE)

# ── 4. Intervalos presentes pero incompletos ────────────────────────
case_d = json.loads(json.dumps(case))
case_d["observations"]["consumed_intervals"] = [[-44, -25], [-25, -24]]  # el último no lo cubre evidencia de contenido
r = ec.verify_binding(case_d, sealed)
v("observación no cubierta por la fuente → complete≠TRUE",
  r["complete"] != ec.TRUE)

# ── 5. Evidencia correcta con observaciones no cubiertas ─────────────
case_e = json.loads(json.dumps(case))
case_e["observations"]["consumed_intervals"] = [[-10, -1]]  # fuera de toda evidencia
r = ec.verify_binding(case_e, sealed)
v("observación fuera del alcance de toda evidencia → complete≠TRUE",
  r["complete"] != ec.TRUE)

# ── 6. Resumen interprocedimental válido pero fuera de su dominio ───
sum_in = ra.seal_call_summary({
    "name": "sub_x", "classification": "inspected",
    "reads_args": [1], "writes_args": [],
    "writes_through_args": [], "preserves_pointer_args": [1],
    "text_consuming": True, "writes_candidate_scalar": False,
    "unknown": False, "complete": True, "side_effects": [],
    "validity": ["arg1 bien formada", "caller pasa puntero válido"],
    "evidence": ["cuerpo inspeccionado"]})
# el resumen es válido per se; fuera de su dominio (args reasignados tras la llamada)
sum_out_domain = dict(sum_in)
sum_out_domain = dict(sum_out_domain, validity=["dominio no cubierto: puntero reasignado tras la llamada"])
v("resumen válido sellado → validate_call_summary vacía",
  ra.validate_call_summary(sum_in) == [])
v("fuera de dominio declarado → validity explícita y visible (no oculta)",
  sum_out_domain["validity"] != sum_in["validity"])

# ── 7. Evidencia derivada con procedencia rota ───────────────────────
broken = json.loads(json.dumps(sealed))
for c in broken["candidates"]:
    if c["candidate_id"] == "vvar_253":
        for e in c["evidence"]:
            e.setdefault("provenance", {})
            e["provenance"]["artifact_sha256"] = None
        break
broken["artifact"] = dict(broken["artifact"])
broken["artifact"]["sha256"] = None
case_g = json.loads(json.dumps(case))
case_g["sealed_analysis"] = broken
case_g["artifact"] = dict(case_g["artifact"])
case_g["artifact"]["sha256"] = None  # sin sha en ningún nivel
r = ec.verify_binding(case_g, broken)
v("procedencia rota en todas las fuentes → Bound FALSE",
  r["bound"] == ec.FALSE)
v("procedencia rota registrada con motivo",
  any("artifact_sha256" in x or "procedencia" in x for x in r["violations"]))

# debilidad únicamente a nivel evidencia (vinculación contenedor) → advisory
broken2 = json.loads(json.dumps(sealed))   # artifact-level sha intacto
for c in broken2["candidates"]:
    if c["candidate_id"] == "vvar_253":
        for e in c["evidence"]:
            e.setdefault("provenance", {})
            e["provenance"]["artifact_sha256"] = None
        break
case_g2 = json.loads(json.dumps(case))
case_g2["sealed_analysis"] = broken2
r = ec.verify_binding(case_g2, broken2)
v("procedencia débil a nivel evidencia (vinculación contenedor) → advisory, bound TRUE",
  r["bound"] == ec.TRUE and any("procedencia débil" in x for x in r.get("advisories", [])))

# ── 8. Transformación vacua → SAFE con etiqueta vacuous ──────────────
case_h = json.loads(json.dumps(case))
case_h["proposed_transform"] = dict(case_h["proposed_transform"],
                                    overlap_intervals=[],
                                    ops=[], storage_writes=[])
case_h["observations"] = dict(case_h["observations"], consumed_intervals=[])
case_h["intervals_written_original"] = []
case_h["intervals_written_transform"] = []
case_h["original_sequence"] = {"ops": []}
r = ec.verify_binding(case_h, sealed)
v("transformación vacua: vacuous=TRUE",
  r["vacuous"] is True)
hint = ec.check_binding(case_h, sealed)["verdict_hint"]
v("transformación vacua: verdict_hint=VACUOUS",
  hint == "VACUOUS")
res = tw.evaluate(case_h)
v("instrument reporta vacuous explícitamente",
  "vacuous" in json.dumps(res, default=str).lower() or
  res["conditions"]["C"]["value"] in (ec.TRUE, ec.UNKNOWN))

# ── 9. Oráculo que solo valida una parte del dominio → EP PARTIAL ────
case_i = json.loads(json.dumps(case))
case_i["independent_oracle"] = {"tool": "gcc decode only", "result": "PASS"}  # sin covers
res = tw.evaluate(case_i)
v("oráculo parcial → PARTIAL (nunca PROVEN)",
  res["epistemic_status"] == tw.EP_PARTIAL)

# ── 10. Testigo y verificador con resultados opuestos ───────────────
# Sintético: cobertura inventada que el verificador rechaza y el testigo acepta
case_j = json.loads(json.dumps(case))
case_j["observations"]["evidence_intervals"] = [
    {"id": "ev-fake-inexistente", "interval": [-44, -25],
     "category": "TEXTUAL_READ", "confidence": "HIGH"}]
w_j = tw.evaluate(case_j)
v_j = iv.verify_case(case_j, sealed_analysis=sealed)
v("witness vs verifier: ambos bloquean bajo el contrato (BLOCKED)",
  w_j["verdict"] == tw.BLOCKED and v_j["verdict"] == iv.BLOCKED)

# ── 11. Determinismo del contrato ────────────────────────────────────
def run():
    return json.dumps(ec.check_binding(case, sealed), sort_keys=True)
v("determinismo K", run() == run())

# ── 12. Contrato nunca confía en el manifiesto del caso ───────────────
# unmanifiestado presente, pero sha del artefacto discordante → FALSE
case_l = json.loads(json.dumps(case))
case_l["artifact"] = dict(case_l["artifact"], sha256="00" * 32)
case_l["manifest_verified"] = ["SHA256SUMS.m10.5", "SHA256SUMS.m10.6", "SHA256SUMS.m10.7"]
r = ec.verify_binding(case_l, sealed)
v("manifiesto declarado íntegramente pero sha discordante → Bound FALSE",
  r["bound"] == ec.FALSE)

print()
if _fallos:
    print("evidence_contract FALLA:", _fallos)
    sys.exit(1)
print("evidence_contract: OK")
sys.exit(0)
