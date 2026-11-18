#!/usr/bin/env python3
# SPDX-License-Identifier: GPL-2.0
"""IER-108 · TRANSFORMER_WITNESS — testigo independiente de transformación.

Cubre:
  - Las 6 condiciones de la conjunción SAFE = B ∧ W ∧ O ∧ L ∧ C ∧ D.
  - Al menos un contraejemplo por condición (cada condición hace fallar SAFE).
  - Consumo de artefactos sellados + rechazo de sellos rotos.
  - Construcción del caso cancel.sys desde artefactos sellados M10.5–M10.7.
  - Estados epistémico/operativo separados; PROVEN exige oráculo independiente.
  - Determinismo.

Nunca usa angr ni el guard como oráculo.
"""
import os
import sys
import json
import tempfile

HERE = os.path.dirname(os.path.abspath(__file__))
PKG = os.path.abspath(os.path.join(HERE, ".."))
sys.path.insert(0, PKG)
os.environ["IER_STORE"] = tempfile.mkdtemp(prefix="ier_tw_")

from ier import transformer_witness as tw  # noqa: E402
from ier import witness_cases as wc  # noqa: E402
from ier import region_analyzer as ra  # noqa: E402

_fallos = []


def v(nombre, cond, info=""):
    if cond:
        print("  PASS %-56s" % nombre)
    else:
        print("  FAIL %-56s %s" % (nombre, info))
        _fallos.append(nombre)


# ── caso reducido reutilizable (sintético) ─────────────────────────
ENC = [0xd8, 0xfd, 0xd7, 0xe6, 0xfc, 0xe0, 0xf2, 0xea, 0xd6,
       0xf8, 0xf1, 0xf9, 0xfe, 0xea, 0xcb, 0xd9, 0xd1, 0xc7, 0xa3]


def base_case():
    return {
        "case_id": "synthetic-1",
        "artifact": {"path": "/f", "sha256": "ab12" + "0" * 60, "kind": "PE"},
        "region": {"id": "vvar_253", "base": -44, "size": 20,
                   "storage": "frame:-44:20"},
        "original_sequence": {"ops": [
            {"op": "store_const_bytes", "offset": 0, "bytes": ENC},
            {"op": "rmw_xor", "offset": 0, "size": 18, "index_base": 145},
            {"op": "store_const", "offset": 18, "value": 0}]},
        "proposed_transform": {"kind": "inline_copy",
                               "ops": [
            {"op": "store_const_bytes", "offset": 0, "bytes": ENC},
            {"op": "rmw_xor", "offset": 0, "size": 18, "index_base": 145},
            {"op": "store_const", "offset": 18, "value": 0}],
            "storage_writes": ["frame:-44:20"],
            "overlap_intervals": [[-44, -25]]},
        "intervals_written_original": [[-44, -25]],
        "intervals_written_transform": [[-44, -25]],
        "observations": {
            "consumed_intervals": [[-44, -25]],
            "evidence_intervals": [
                {"id": "ev-rmw", "interval": [-44, -26], "category": "READ_MODIFY_WRITE"},
                {"id": "ev-term", "interval": [-26, -25], "category": "WRITE_ONLY"},
                {"id": "ev-call", "interval": [-44, -24], "category": "TEXTUAL_READ"}],
            "unobserved_bytes": [[-25, -24]]},
        "order_check": {
            "original": [("write", "frame:-44:20"), ("rmw_xor", "frame:-44:20"),
                         ("write", "frame:-44:20"), ("call", "sub_x")],
            "transform": [("write", "frame:-44:20"), ("rmw_xor", "frame:-44:20"),
                          ("write", "frame:-44:20"), ("call", "sub_x")]},
        "lineage": {
            "allowed_storage_writes": ["frame:-44:20"],
            "must_not_overlap": [
                {"id": "vvar_271", "interval": [-48, -32], "live_during_transform": False}]},
        "independent_oracle": {"tool": "gcc 11 xor_decode", "result": "PASS"},
        "domain": {"artifact_sha256": "ab12" + "0" * 60, "function": "0x140005234",
                   "scope": "fold de construcción; usos posteriores inalterados",
                   "limits": ["transformación concreta inline_copy", "vía AIL BEFORE_SSA"]},
    }


def fresh():
    return base_case()


print()

# ── case completo → SAFE + PARTIAL ─────────────────────────────────
res = tw.evaluate(fresh())
v("case completo → SAFE_TO_TRANSFORM", res["verdict"] == tw.SAFE)
v("todas las condiciones TRUE",
  all(c["value"] == tw.TRUE for c in res["conditions"].values()))
v("oráculo independiente → PARTIAL (no PROVEN sin física externa completa)",
  res["epistemic_status"] == tw.EP_PARTIAL)

# ── B falla: bytes difieren → BLOCKED ──────────────────────────────
bad = fresh()
bad["proposed_transform"]["ops"][0]["bytes"] = list(ENC)
bad["proposed_transform"]["ops"][0]["bytes"][0] = 0x00
res = tw.evaluate(bad)
v("B contraejemplo (byte distinto) → BLOCKED", res["verdict"] == tw.BLOCKED)
v("B falla identificada",
  res["conditions"]["B"]["value"] == tw.FALSE)

# ── W falla: transformación omite el terminador (byte consumido) → BLOCKED
bad = fresh()
bad["proposed_transform"]["overlap_intervals"] = [[-44, -26]]
bad["intervals_written_transform"] = [[-44, -26]]
res = tw.evaluate(bad)
v("W contraejemplo (falta terminador) → BLOCKED", res["verdict"] == tw.BLOCKED)
v("W falla identificada",
  res["conditions"]["W"]["value"] == tw.FALSE)

# ── O falla: observadores reordenados → BLOCKED ────────────────────
bad = fresh()
bad["order_check"]["transform"] = [("call", "sub_x"), ("write", "frame:-44:20"),
                                   ("rmw_xor", "frame:-44:20"), ("write", "frame:-44:20")]
res = tw.evaluate(bad)
v("O contraejemplo (call reordenada) → BLOCKED", res["verdict"] == tw.BLOCKED)

# ── L falla: escribe storage no permitido → BLOCKED ────────────────
bad = fresh()
bad["proposed_transform"]["storage_writes"] = ["frame:-48:16"]
res = tw.evaluate(bad)
v("L contraejemplo (storage ajeno) → BLOCKED", res["verdict"] == tw.BLOCKED)
bad = fresh()
bad["proposed_transform"]["overlap_intervals"] = [[-44, -25]]
bad["lineage"]["must_not_overlap"] = [
    {"id": "vvar_271", "interval": [-48, -32], "live_during_transform": True}]
res = tw.evaluate(bad)
v("L contraejemplo (solape con región viva) → BLOCKED", res["verdict"] == tw.BLOCKED)

# ── C falla: observación sin evidencia que la cubra → ABSTAIN ──────
bad = fresh()
bad["observations"]["evidence_intervals"] = [
    {"id": "ev-rmw", "interval": [-44, -26]}]  # sin evidencia para [-26,-25)
res = tw.evaluate(bad)
v("C falta evidencia para byte consumido → ABSTAIN",
  res["verdict"] == tw.ABSTAIN)
bad = fresh()
bad["observations"]["unobserved_bytes"] = None
res = tw.evaluate(bad)
v("C sin declaración de no observados → ABSTAIN",
  res["verdict"] == tw.ABSTAIN)

# ── D falla: sin dominio → ABSTAIN ─────────────────────────────────
bad = fresh()
del bad["domain"]
res = tw.evaluate(bad)
v("D sin dominio → ABSTAIN", res["verdict"] == tw.ABSTAIN)
bad = fresh()
bad["domain"] = {"function": "0x140005234"}  # faltan artifact/scope/limits
res = tw.evaluate(bad)
v("D dominio incompleto → ABSTAIN", res["verdict"] == tw.ABSTAIN)

# ── modelo no ejecutable → ABSTAIN ─────────────────────────────────
bad = fresh()
bad["original_sequence"]["ops"][1] = {"op": "rmw_xor", "offset": 0, "size": 18}  # sin clave
res = tw.evaluate(bad)
v("key XOR ausente → ABSTAIN", res["verdict"] == tw.ABSTAIN)
bad = fresh()
bad["original_sequence"]["ops"].append({"op": "teleport"})
res = tw.evaluate(bad)
v("op desconocida → ABSTAIN", res["verdict"] == tw.ABSTAIN)

# ── carga sellada: manifiesto roto → rechazo ───────────────────────
tmp = tempfile.mkdtemp(prefix="tw_seal_")
sealed = os.path.join(tmp, "art.json")
with open(sealed, "w") as fh:
    fh.write('{"x": 1}')
manifest = os.path.join(tmp, "SHA256SUMS")
import hashlib
with open(manifest, "w") as fh:
    fh.write("%s  art.json\n" % hashlib.sha256(open(sealed, "rb").read()).hexdigest())
res_ok = tw.load_sealed_json(sealed, manifest)
v("sello válido → carga OK", res_ok == {"x": 1})
with open(sealed, "a") as fh:
    fh.write(" ")
try:
    tw.load_sealed_json(sealed, manifest)
    v("sello roto → rechazo", False)
except ValueError:
    v("sello roto → rechazo", True)

# ── caso real cancel.sys desde evidencia M10 sellada ───────────────
M10 = os.environ.get(
    "RXRE_7294_SEALED_DIR", os.path.expanduser("~/rxre-angr-7294-m10"))
case = wc.build_cancel_sys_case(M10)
res = tw.evaluate(case)
v("cancel.sys → SAFE_TO_TRANSFORM (testigo independiente)",
  res["verdict"] == tw.SAFE, res["verdict"])
v("cancel.sys B=TRUE", res["conditions"]["B"]["value"] == tw.TRUE)
v("cancel.sys W=TRUE", res["conditions"]["W"]["value"] == tw.TRUE)
v("cancel.sys O=TRUE", res["conditions"]["O"]["value"] == tw.TRUE)
v("cancel.sys L=TRUE", res["conditions"]["L"]["value"] == tw.TRUE)
v("cancel.sys C=TRUE", res["conditions"]["C"]["value"] == tw.TRUE)
v("cancel.sys D=TRUE", res["conditions"]["D"]["value"] == tw.TRUE)
v("cancel.sys: evidencia M10.5–M10.7 consumida (sellos verificados)",
  case["manifest_verified"] == ["SHA256SUMS.m10.5", "SHA256SUMS.m10.6", "SHA256SUMS.m10.7"])

# ── PROVEN exige oráculo; sin él, nunca PROVEN ──────────────────────
case_wo = wc.build_cancel_sys_case(M10)
del case_wo["independent_oracle"]
res = tw.evaluate(case_wo)
v("sin oráculo independiente → PARTIAL (nunca PROVEN)",
  res["verdict"] == tw.SAFE and res["epistemic_status"] == tw.EP_PARTIAL)

# ── determinismo ───────────────────────────────────────────────────
def run():
    return json.dumps(tw.evaluate(wc.build_cancel_sys_case(M10)), sort_keys=True)

v("determinismo del testigo", run() == run())

print()
if _fallos:
    print("transformer_witness FALLA:", _fallos)
    sys.exit(1)
print("transformer_witness: OK")
sys.exit(0)
