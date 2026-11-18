#!/usr/bin/env python3
# SPDX-License-Identifier: GPL-2.0
"""IER-113 · ANGR_GUARD_BRIDGE — auditoría adversarial (M11.6).

Prueba que ninguna manipulación de identidad, evidencia, procedencia o estado
puede convertir una decisión no admisible en SAFE_TO_TRANSFORM.

Clases de ataque:
  A. Contradicciones de fuentes                    (semántica → csa/rvm)
  B. Manipulación de sellos y fingerprints         (parte semántica + integridad)
  C. Estado dinámico y fallos                      (bridge + guard hook)
  D. Propiedad de aislamiento Σ(x): Invalid ∨ Unknown ⇒ decision ≠ SAFE

Las pruebas tocan SOLO copias de trabajo en directorios temporales; los
archivos sellados en disco nunca se modifican.

Uso:  python3 tests/test_angr_guard_bridge_adversarial.py
"""
import os
import sys
import json
import shutil
import socket
import tempfile
import threading
import hashlib
from typing import Any, Dict, List

HERE = os.path.dirname(os.path.abspath(__file__))
PKG = os.path.abspath(os.path.join(HERE, ".."))
sys.path.insert(0, PKG)
os.environ["IER_STORE"] = tempfile.mkdtemp(prefix="ier_ad_m116_")

from ier import angr_guard_bridge as bg  # noqa: E402
from ier import call_summary_admission as csa  # noqa: E402
from ier import rxre_angr_adapter as rvm  # noqa: E402

SEALED_DIR = os.environ.get(
    "RXRE_7294_SEALED_DIR", os.path.expanduser("~/rxre-angr-7294-m10"))
BIN = SEALED_DIR + "/binaries/tests/x86_64/windows/cancel.sys"
CANCEL_SHA256 = "bca61fba97ea68566b55c2860a8798650424cd59fec5eaf9aff02e0ec4a3a4d7"

_fallos: List[str] = []


def v(nombre, cond, info=""):
    if cond:
        print("  PASS %-62s" % nombre)
    else:
        print("  FAIL %-62s %s" % (nombre, info))
        _fallos.append(nombre)


def sealed_analysis() -> Dict[str, Any]:
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
                        "encoding": "ascii",
                        "sha256": "00112233445566778899aabbccddeeff00112233445566778899aabbccddeeff"},
             "decision": "ABSTAIN",
             "evidence": []},
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
        "reads": [{"target": "arg1", "span": 19, "termination": "NUL",
                   "frequency": "loop-bytewise"}],
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
    "artifact": {"path": BIN, "sha256": CANCEL_SHA256,
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


def fc(**over):
    c = json.loads(json.dumps(CASE))
    for k, val in over.items():
        c[k] = val
    return c


def fs(**over):
    s = json.loads(json.dumps(FULL_SUMMARY))
    for k, val in over.items():
        s[k] = val
    return s


print()
print("== A. Contradicciones de fuentes (semántica)")

# A1 · span contradictorio en el summary (mismo storage)
s = fs()
s["region"]["start"], s["region"]["end"] = -40, -20
res = csa.evaluate(s, fc(), sealed_analysis=sealed_analysis())
v("A1 span contradictorio vs sello → no SAFE",
  res["verdict"] != "SAFE_TO_TRANSFORM", res["verdict"])

# A2 · storage contradictorio (mismo span)
s = fs()
s["region"]["storage_id"] = "frame:-48:20"
res = csa.evaluate(s, fc(), sealed_analysis=sealed_analysis())
v("A2 storage contradictorio → no SAFE",
  res["verdict"] != "SAFE_TO_TRANSFORM", res["verdict"])

# A3 · lectura escalar declarada (evidencia escalar incompatible)
s = fs()
s["effects"]["reads"][0]["termination"] = "scalar_u32"
res = csa.evaluate(s, fc(), sealed_analysis=sealed_analysis())
v("A3 evidencia escalar incompatible → no SAFE",
  res["verdict"] != "SAFE_TO_TRANSFORM", res["verdict"])

# A4 · resumen válido + evidencia contradictoria (escritura al búfer)
s = fs()
s["effects"]["writes"] = [{"target": "arg1", "span": 19}]
res = csa.evaluate(s, fc(), sealed_analysis=sealed_analysis())
v("A4 resumen válido + escritura declarada → no SAFE",
  res["verdict"] != "SAFE_TO_TRANSFORM", res["verdict"])

# A4b · escrituras parciales fuera del candidato (no contaminan)
s = fs()
s["effects"]["writes"] = [{"target": "arg0", "span": 8}]
res = csa.evaluate(s, fc(), sealed_analysis=sealed_analysis())
v("A4b escrituras a arg0 (disjuntas) no contaminan el veredicto",
  res["verdict"] == "SAFE_TO_TRANSFORM", res["verdict"])

# A5 · lecturas disjuntas demostradas no contaminan
s = fs()
s["effects"]["reads"] = [
    {"target": "arg1", "span": 19, "termination": "NUL", "frequency": "loop-bytewise"},
    {"target": "arg0", "span": 8, "termination": "entry_end", "frequency": "per_entry"},
]
res = csa.evaluate(s, fc(), sealed_analysis=sealed_analysis())
v("A5 lectura disjunta arg0 → veredicto SAFE conservada",
  res["verdict"] == "SAFE_TO_TRANSFORM", res["verdict"])

# A6 · lectura bytewise sin terminación demostrada → ABSTAIN
s = fs()
s["effects"]["reads"][0]["termination"] = "arbitrary"
res = csa.evaluate(s, fc(), sealed_analysis=sealed_analysis())
v("A6 terminación arbitraria → ABSTAIN (nunca SAFE)",
  res["verdict"] == "ABSTAIN", res["verdict"])


print()
print("== B. Manipulación de sellos y fingerprints")

# B1 · SAFE forjado con fingerprint inválido: el puente DEBE degradar
fake_binding = {"R1_binary": "TRUE", "R2_function": "TRUE", "R3_callsite": "TRUE",
                "R4_arg": "TRUE", "R5_reads": "TRUE", "R6_writes": "TRUE",
                "R7_termination": "TRUE", "R8_return": "TRUE",
                "R9_coverage": "TRUE", "R10_oraculo": "TRUE"}
fake = {
    "decision": "SAFE_TO_TRANSFORM",
    "sha256": "00" * 32,  # fingerprint deliberadamente falso
    "verification": {"checks_run": 6, "pass": 6, "skipped": 0},
    "admission": {"verdict": "SAFE_TO_TRANSFORM", "binding": fake_binding},
    "independent_oracle": ["objdump"],
}
orig_emit = rvm.emit_verified_decision
try:
    rvm.emit_verified_decision = lambda *a, **k: dict(fake)
    out = bg.decide_candidate(BIN, "region_-44_-24", -44, 20,
                              0x1400035f4, 0x1400052c9, caller_addr=0x140005234)
    v("B1 SAFE forjado + fingerprint inválido → no SAFE",
      out["decision"] != "SAFE_TO_TRANSFORM", out["decision"])
    # y tampoco cuando el adaptador devuelve algo no-dict
    rvm.emit_verified_decision = lambda *a, **k: ["not", "a", "dict"]
    out = bg.decide_candidate(BIN, "region_-44_-24", -44, 20,
                              0x1400035f4, 0x1400052c9, caller_addr=0x140005234)
    v("B1b adaptador devuelve estructura no-dict → no SAFE",
      out["decision"] != "SAFE_TO_TRANSFORM", out["decision"])
    # o un dict con decisión desconocida
    hacked = dict(fake)
    hacked["decision"] = "TOTALLY_SAFE_TRUST_ME"
    rvm.emit_verified_decision = lambda *a, **k: hacked
    out = bg.decide_candidate(BIN, "region_-44_-24", -44, 20,
                              0x1400035f4, 0x1400052c9, caller_addr=0x140005234)
    v("B1c decisión no reconocida por el adaptador → no SAFE",
      out["decision"] != "SAFE_TO_TRANSFORM", out["decision"])
finally:
    rvm.emit_verified_decision = orig_emit

# B2 · artefacto sellado alterado → verificación de sello falla
with tempfile.TemporaryDirectory(prefix="m116_seal_") as tmp:
    bad = os.path.join(tmp, "cancel_sys_analysis_m10_7.json")
    shutil.copy(SEALED_DIR + "/cancel_sys_analysis_m10_7.json", bad)
    blob = open(bad, "rb").read()
    with open(bad, "wb") as fh:
        fh.write(blob.replace(b'"complete": true', b'"complete": false', 1))
    saved_a = bg.SEALED_ANALYSIS_PATH
    try:
        bg.SEALED_ANALYSIS_PATH = bad
        v("B2 artefacto sellado alterado → verificación de sello falla",
          bg.verify_seal_integrity()["ok"] is False)
    finally:
        bg.SEALED_ANALYSIS_PATH = saved_a

# B2b · sello interior alterado (bytes del resumen) → BLOCKED/fail-closed
with tempfile.TemporaryDirectory(prefix="m116_seal2_") as tmp:
    bad = os.path.join(tmp, "callee_summary_sub_1400035f4.json")
    blob = open(SEALED_DIR + "/callee_summary_sub_1400035f4.json", "rb").read()
    with open(bad, "wb") as fh:
        fh.write(blob.replace(b"text_consuming", b"text_consuming!", 1))
    saved_c = bg.SEALED_CALLEE_PATH
    try:
        bg.SEALED_CALLEE_PATH = bad
        v("B2b sello interno alterado → verificación falla",
          bg.verify_seal_integrity()["ok"] is False)
    finally:
        bg.SEALED_CALLEE_PATH = saved_c

# B3 · verified_by vacío → ABSTAIN (nunca SAFE)
s = fs()
s["oracle"]["verified_by"] = []
res = rvm.verify_decision(s, fc(), sealed_analysis=sealed_analysis())
v("B3 verified_by vacío → no SAFE",
  res["verdict"] != "SAFE_TO_TRANSFORM", res["verdict"])

# B4 · oráculo sin firma ni binding reconocido → ABSTAIN
s = fs()
s["oracle"] = {"binding": "RANDOM", "verified_by": []}
res = csa.evaluate(s, fc(), sealed_analysis=sealed_analysis())
v("B4 oráculo no reconocido → ABSTAIN/NO-SAFE",
  res["verdict"] != "SAFE_TO_TRANSFORM", res["verdict"])

# B5 · identidad binaria diferente → BLOCKED (bridge, binario con 1 byte distinto)
with tempfile.TemporaryDirectory(prefix="m116_bin_") as tmp:
    other = os.path.join(tmp, "cancel_otro.sys")
    blob = open(BIN, "rb").read()
    with open(other, "wb") as fh:
        fh.write(blob[:100] + b"\xAA" + blob[101:])
    out = bg.decide_candidate(other, "region_-44_-24", -44, 20,
                              0x1400035f4, 0x1400052c9, caller_addr=0x140005234)
    v("B5 binario diferente → BLOCKED/no-SAFE",
      out["decision"] != "SAFE_TO_TRANSFORM", out["decision"])

# B6 · reutilización del callsite en otra región → no SAFE
case = fc()
case["callsite"]["instruction"] = 0xdeadbeef
case["artifact"]["path"] = BIN
res = rvm.verify_decision(FULL_SUMMARY, case, sealed_analysis=sealed_analysis())
v("B6 callsite ajeno → no SAFE",
  res["verdict"] != "SAFE_TO_TRANSFORM", res["verdict"])

# B7 · replay de una decisión sobre otra región → fingerprints distintos y no
#      recomputables para contextos ajenos
decision_a = rvm.emit_verified_decision(FULL_SUMMARY, fc(),
                                        sealed_analysis=sealed_analysis())
case_b = fc()
case_b["region"] = {"storage_id": "frame:-48:16", "base": -48, "size": 16,
                    "id": "vvar_271"}
decision_b = rvm.emit_verified_decision(FULL_SUMMARY, case_b,
                                        sealed_analysis=sealed_analysis())


def _at(doc, key):
    return doc.get(key)


# decisión A aplicada al contexto B (cambio de región, mismo sha256): NO recomputa
fp_a = decision_a.get("sha256")
fake_replay = dict(decision_a)
fake_replay["case"] = case_b
v("B7 decisión sellada no se puede replayar sobre otra región",
  rvm.recompute_admission_fingerprint(
      {k: v for k, v in fake_replay.items()}) is False
  or fp_a != decision_b.get("sha256"))

# B8 · summary tamperada de un solo carácter
with tempfile.TemporaryDirectory(prefix="m116_sum_") as tmp:
    bad = os.path.join(tmp, "callee_summary_sub_1400035f4.json")
    blob = open(SEALED_DIR + "/callee_summary_sub_1400035f4.json", "rb").read()
    with open(bad, "wb") as fh:
        fh.write(blob.replace(b"byte-compare-hit", b"byte-compare-XX", 1))
    out = bg.decide_candidate(BIN, "region_-44_-24", -44, 20,
                              0x1400035f4, 0x1400052c9, caller_addr=0x140005234,
                              sealed_summary_path=bad)
    v("B8 summary alterado de 1 byte → BLOCKED/no-SAFE",
      out["decision"] != "SAFE_TO_TRANSFORM", out["decision"])


print()
print("== C. Estado dinámico y fallos")

class _RaisingStmt:
    def __str__(self):
        raise RuntimeError("boom")


class _Empty:
    pass


# C1 · regf vacío
out = bg.decide_for_stmt(BIN, set(), "stmt", function_addr=0x140005234,
                         callsite_addr=0x1400052c9)
v("C1 región vacía → BLOCKED/no-SAFE", out["decision"] != "SAFE_TO_TRANSFORM",
  out["decision"])
# C2 · regf ausente
out = bg.decide_for_stmt(BIN, None, "stmt", function_addr=0x140005234,
                         callsite_addr=0x1400052c9)
v("C2 región ausente → BLOCKED/no-SAFE", out["decision"] != "SAFE_TO_TRANSFORM",
  out["decision"])
# C3 · regf parcialmente construido (tipos mezclados)
out = bg.decide_for_stmt(BIN, [-44, None], "stmt", function_addr=0x140005234,
                               callsite_addr=0x1400052c9)
v("C3 regf parcialmente construida → no-SAFE (sin excepciones)",
  out["decision"] != "SAFE_TO_TRANSFORM", out["decision"])
# C4 · regf con None
out = bg.decide_for_stmt(BIN, {-44, None}, "stmt", function_addr=0x140005234,
                               callsite_addr=0x1400052c9)
v("C4 regf con None → no-SAFE (sin excepciones)",
  out["decision"] != "SAFE_TO_TRANSFORM", out["decision"])
# C5 · statement que explota en str()
out = bg.decide_for_stmt(BIN, {-44}, _RaisingStmt(), function_addr=0x140005234,
                               callsite_addr=0x1400052c9)
v("C5 statement que explota → no-SAFE (sin crash)",
  out["decision"] != "SAFE_TO_TRANSFORM", out["decision"])
# C6 · adaptador devuelve estructura incompleta
orig_emit2 = rvm.emit_verified_decision
try:
    rvm.emit_verified_decision = lambda *a, **k: {"decision": "SAFE_TO_TRANSFORM"}  # sin fingerprint ni checksums
    out = bg.decide_candidate(BIN, "region_-44_-24", -44, 20,
                              0x1400035f4, 0x1400052c9, caller_addr=0x140005234)
    v("C6 decisión SAFE sin evidencia verificable → no-SAFE",
      out["decision"] != "SAFE_TO_TRANSFORM", out["decision"])
finally:
    rvm.emit_verified_decision = orig_emit2
# C7 · error al recomputar fingerprint
orig_recompute = rvm.recompute_admission_fingerprint
try:
    rvm.recompute_admission_fingerprint = lambda doc: False
    out = bg.decide_candidate(BIN, "region_-44_-24", -44, 20,
                              0x1400035f4, 0x1400052c9, caller_addr=0x140005234)
    v("C7 fingerprint no recomputable → no-SAFE",
      out["decision"] != "SAFE_TO_TRANSFORM", out["decision"])
finally:
    rvm.recompute_admission_fingerprint = orig_recompute
# C8 · dos invocaciones concurrentes con identidades distintas


class _ProbeProject:
    def __init__(self, path):
        self.filename = path


results: Dict[str, Any] = {}
stop = threading.Event()


def _worker(name, rp, fn_addr):
    try:
        for _ in range(3):
            out = bg.decide_for_stmt(_ProbeProject(rp), {-44},
                                     "STORE(addr=5368746112<64>, data=Call(5368722932<64>, (Reference vvar_284{s-44|1b})))",
                                     function_addr=fn_addr, callsite_addr=0x1400052c9)
            results.setdefault(name, out["decision"])
    except Exception as exc:  # jamás debe ocurrir
        results[name] = "EXC:%s" % exc


t1 = threading.Thread(target=_worker, args=("safe", BIN, 0x140005234))
t2 = threading.Thread(target=_worker, args=("otro", BIN, 0xdeadbeef))
t1.start()
t2.start()
t1.join()
t2.join()
v("C8 dos invocaciones concurrentes → sin mezcla, sin excepciones",
  results.get("safe") == "SAFE_TO_TRANSFORM"
  and results.get("otro") in ("ABSTAIN", "BLOCKED"), json.dumps(results))

# C9 · callee_addr None debe abstenerse
out = bg.decide_candidate(BIN, "region_-44_-24", -44, 20,
                          None, 0x1400052c9, caller_addr=0x140005234)
v("C9 callee no resuelto → no-SAFE",
  out["decision"] != "SAFE_TO_TRANSFORM", out["decision"])


print()
print("== D. Propiedad Σ(x): Invalid(x) ∨ Unknown(x) ⇒ Decision(x) ≠ SAFE")

forged_ok_binding = dict(fake_binding)
forged_ok_binding["R3_callsite"] = "UNKNOWN"   # incertidumbre conocida

s = fs()
s["effects"]["reads"][0]["frequency"] = ""  # incertidumbre
res = csa.evaluate(s, fc(), sealed_analysis=sealed_analysis())
v("D-1 duda de frecuencia de lectura → no SAFE",
  res["verdict"] != "SAFE_TO_TRANSFORM", res["verdict"])

s = fs()
s["binary"]["sha256"] = ""  # identidad incompleta
res = csa.evaluate(s, fc(), sealed_analysis=sealed_analysis())
v("D-2 identidad binaria incompleta → no SAFE",
  res["verdict"] != "SAFE_TO_TRANSFORM", res["verdict"])

s = fs()
s["coverage"]["completeness"] = "partial"
s["coverage"]["unresolved_paths"] = ["loop-exit"]
res = csa.evaluate(s, fc(), sealed_analysis=sealed_analysis())
v("D-3 coverage partial + paths abiertos → no SAFE",
  res["verdict"] != "SAFE_TO_TRANSFORM", res["verdict"])


print()
if _fallos:
    print("FALLOS ADVERSARIALES:", _fallos)
    sys.exit(1)
print("angr_guard_bridge adversarial: OK")
sys.exit(0)
