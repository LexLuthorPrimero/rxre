#!/usr/bin/env python3
# SPDX-License-Identifier: GPL-2.0
"""IER-112 · RXRE_ANGR_ADAPTER — verificación de la verificación.

Cubre los criterios M11.4:
  Ib  identidad de binario validada
  If  función y callsite validados
  Ic  argumento y región vinculados
  Ir  reglas de admisión preservadas
  Pv  procedencia verificada
  D   determinismo
  A   abstención segura ante cualquier incertidumbre

Integración con el AIL real de cancel.sys (ail_pr_head.json) cuando esté disponible,
y con el análisis sellado de M10 cuando esté disponible.  Sin Internet.
"""
import os
import sys
import json
import tempfile

HERE = os.path.dirname(os.path.abspath(__file__))
PKG = os.path.abspath(os.path.join(HERE, ".."))
sys.path.insert(0, PKG)
os.environ["IER_STORE"] = tempfile.mkdtemp(prefix="ier_ad_")

from ier import rxre_angr_adapter as rvm  # noqa: E402

_fallos = []


def v(nombre, cond, info=""):
    if cond:
        print("  PASS %-60s" % nombre)
    else:
        print("  FAIL %-60s %s" % (nombre, info))
        _fallos.append(nombre)


SEALED_DIR = os.environ.get(
    "RXRE_7294_SEALED_DIR", os.path.expanduser("~/rxre-angr-7294-m10"))
AIL_PATH = os.path.join(SEALED_DIR, "ail_pr_head.json")
CANCEL_PATH = os.path.join(
    SEALED_DIR, "binaries/tests/x86_64/windows/cancel.sys")
CANCEL_SHA256 = "bca61fba97ea68566b55c2860a8798650424cd59fec5eaf9aff02e0ec4a3a4d7"


def sealed_analysis():
    return {
        "capability": "region_analyzer",
        "capability_version": "RYI-REGION-ANALYZER-1",
        "operational_status": "PASS",
        "epistemic_status": "PARTIAL",
        "artifact": {"path": "binaries/tests/x86_64/windows/cancel.sys",
                     "sha256": CANCEL_SHA256,
                     "function": "0x140005234", "kind": "PE"},
        "artifact_sha256": CANCEL_SHA256,
        "candidates": [
            {"candidate_id": "vvar_253",
             "region": {"id": "vvar_253", "base": -44, "size": 20,
                        "interval": [-44, -24], "storage": "frame:-44:20",
                        "provenance": "AIL(AFTER_SSA_LEVEL1)",
                        "sha256": "00112233445566778899aabbccddeeff00112233445566778899aabbccddeeff"},
             "decision": "ABSTAIN",
             "evidence": [{"id": "ev-001", "category": "WRITE_ONLY",
                           "interval": [-44, -26], "confidence": "HIGH",
                           "provenance": {"artifact_sha256": CANCEL_SHA256,
                                          "function": "0x140005234"}},
                          {"id": "ev-002", "category": "READ_MODIFY_WRITE",
                           "interval": [-44, -26],
                           "confidence": "HIGH",
                           "provenance": {"artifact_sha256": CANCEL_SHA256,
                                          "function": "0x140005234"}}]},
        ],
        "oracle": {"independent": True, "result": "PASS"},
    }


FULL_SUMMARY = {
    "binary": {"sha256": CANCEL_SHA256,
               "architecture": "PE-x86_64"},
    "function": {"entry": 0x1400035f4, "size": 204, "identity": "sub_1400035f4"},
    "callsite": {"caller": 0x140005234, "instruction": 0x1400052c9, "argument_index": 1,
                 "arguments": [
                     {"pos": 0, "kind": "rcx", "role": "table",
                      "observed_value": "0x1400027f4", "provenance": "AIL"},
                     {"pos": 1, "kind": "rdx", "role": "buffer",
                      "observed_value": "0x1400052ac", "provenance": "AIL"},
                 ]},
    "region": {"storage_id": "frame:-44:20", "start": -44, "end": -24,
               "address_space": "stack"},
    "effects": {
        "reads": [
            {"target": "arg1", "span": 19, "termination": "NUL",
             "frequency": "byte-wise"},
        ],
        "writes": [],
        "termination": {"rule": "byte-compare-NUL", "proof": ["objdump"]},
        "return_relation": {"relation": "pointer_derived_from_a0",
                            "proof": ["add rax,r9"]},
    },
    "coverage": {"completeness": "complete", "scope_statement": "read-only",
                 "unresolved_paths": []},
    "oracle": {"binding": "SEAL: rxre-m10-7-sub_1400035f4",
               "verified_by": ["objdump -d 0x1400035f4..0x1400036c2"]},
}

CASE = {
    "artifact": {"path": CANCEL_PATH,
                 "sha256": CANCEL_SHA256,
                 "function": "0x140005234"},
    "function": {"addr": 0x1400035f4},
    "callsite": {"caller": 0x140005234, "instruction": 0x1400052c9, "argument_index": 1,
                 "arguments": [
                     {"pos": 0, "hex": "0x1400027f4"},
                     {"pos": 1, "hex": "0x1400052ac"},
                 ]},
    "region": {"storage_id": "frame:-44:20", "base": -44, "size": 20, "id": "vvar_253"},
    "sealed": None,
}

print()

# ── integración: caso real + AIL real ─────────────────────────────
try:
    ail = rvm.load_ail(AIL_PATH)
    v("AIL carga correcta", ail is not None and len(ail.get("ail_nodes", [])) > 0)
except Exception as exc:
    v("AIL carga correcta", False, str(exc))
    ail = None

sealed = sealed_analysis()
res = rvm.emit_verified_decision(FULL_SUMMARY, CASE,
                                 sealed_analysis=sealed,
                                 ail_path=AIL_PATH)
v("Ic+If+Ib: caso real → SAFE_TO_TRANSFORM",
  res["decision"] == "SAFE_TO_TRANSFORM")

# ── adversarial rechazos ──────────────────────────────────────────
# 1) artefacto discordante (otro binario) → BLOCKED
bad_case = json.loads(json.dumps(CASE))
bad_case["artifact"]["sha256"] = "ff" * 32
res = rvm.emit_verified_decision(FULL_SUMMARY, bad_case, sealed_analysis=sealed)
v("binario discordante en caso → BLOCKED",
  res["decision"] == "BLOCKED")

# 2) callsite discordante → BLOCKED
bad_case = json.loads(json.dumps(CASE))
bad_case["callsite"]["instruction"] = 0xdeadbeef
res = rvm.emit_verified_decision(FULL_SUMMARY, bad_case, sealed_analysis=sealed)
v("callsite discordante → BLOCKED",
  res["decision"] == "BLOCKED")

# 3) argumento (arg_pos) discordante → BLOCKED
bad_summary = json.loads(json.dumps(FULL_SUMMARY))
bad_summary["callsite"]["argument_index"] = 0
res = rvm.emit_verified_decision(bad_summary, CASE, sealed_analysis=sealed)
v("argument_index discordante en summary → BLOCKED",
  res["decision"] == "BLOCKED")

# 4) región discordante (otro storage_id) → BLOCKED
bad_summary = json.loads(json.dumps(FULL_SUMMARY))
bad_summary["region"]["storage_id"] = "frame:-48:16"
res = rvm.emit_verified_decision(bad_summary, CASE, sealed_analysis=sealed)
v("storage_id discordante → BLOCKED",
  res["decision"] == "BLOCKED")

# 5) función discordante → BLOCKED
bad_summary = json.loads(json.dumps(FULL_SUMMARY))
bad_summary["function"]["entry"] = 0xdeadbeef
res = rvm.emit_verified_decision(bad_summary, CASE, sealed_analysis=sealed)
v("función discordante → BLOCKED",
  res["decision"] == "BLOCKED")

# 6) sello del summary vacío/inexistente → BLOCKED
bad_summary = json.loads(json.dumps(FULL_SUMMARY))
bad_summary["oracle"]["verified_by"] = []
res = rvm.emit_verified_decision(bad_summary, CASE, sealed_analysis=sealed)
v("sello sin verified_by real → rechazado (BLOCKED)",
  res["decision"] != "SAFE_TO_TRANSFORM")

# 7) sello del artefacto en disco discordante
import tempfile as tmod
bad_path = tmod.mktemp(prefix="cancel_")
with open(bad_path, "wb") as fh:
    fh.write(b"different bytes")
bad_case = json.loads(json.dumps(CASE))
bad_case["artifact"]["path"] = bad_path
bad_case["artifact"]["sha256"] = "aa" + "00" * 31
res = rvm.emit_verified_decision(FULL_SUMMARY, bad_case, sealed_analysis=sealed)
v("artefacto alterado en disco → BLOCKED",
  res["decision"] == "BLOCKED")

# 8) caso sin region → abstenerse o blocked (nunca SAFE)
bad_case = json.loads(json.dumps(CASE))
del bad_case["region"]
res = rvm.emit_verified_decision(FULL_SUMMARY, bad_case, sealed_analysis=sealed)
v("caso sin region → no SAFE",
  res["decision"] != "SAFE_TO_TRANSFORM")

# 9) con data ambigua → abstenerse
bad_summary = json.loads(json.dumps(FULL_SUMMARY))
bad_summary["oracle"] = {"binding": "?", "verified_by": []}
res = rvm.emit_verified_decision(bad_summary, CASE, sealed_analysis=sealed)
v("oráculo ambiguo → no SAFE",
  res["decision"] != "SAFE_TO_TRANSFORM")

# 10) determinismo
res_a = rvm.emit_verified_decision(FULL_SUMMARY, CASE, sealed_analysis=sealed)
res_b = rvm.emit_verified_decision(FULL_SUMMARY, CASE, sealed_analysis=sealed)
v("verificaciones deterministas (misma entrada→ misma salida)",
  json.dumps(res_a, sort_keys=True) == json.dumps(res_b, sort_keys=True))
v("fingerprint sha256 estables",
  res_a.get("sha256") == res_b.get("sha256"))

# 11) emit_verified_decision: fingerprint recomputes
res = rvm.emit_verified_decision(FULL_SUMMARY, CASE, sealed_analysis=sealed)
v("fingerprint recomputable (D determinismo)",
  rvm.recompute_admission_fingerprint(res) is True)

# 12) candidates_from_ail sobre el AIL real
if ail is not None:
    cands = rvm.candidates_from_ail(ail)
    ids = sorted({c["candidate_id"] for c in cands})
    v("candidates_from_ail recoge vvar_* del AIL",
      "vvar_253" in ids, "ids=" + str(ids))

print()
if _fallos:
    print("RXRE_ANGR_ADAPTER FALLA:", _fallos)
    sys.exit(1)
print("rxre_angr_adapter: OK")
sys.exit(0)
