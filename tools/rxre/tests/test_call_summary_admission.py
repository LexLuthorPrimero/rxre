#!/usr/bin/env python3
# SPDX-License-Identifier: GPL-2.0
"""IER-111 · CALL_SUMMARY_ADMISSION — admisión de resúmenes interprocedimentales v2.

Cubre la tabla §6 del dictamen M11.3:

  1. Helper completo, lectura textual demostrada → SAFE_TO_TRANSFORM
  2. Helper que lee bytes sin terminación demostrada → ABSTAIN
  3. Helper que modifica el buffer → nunca asume SAFE, evalúa efectos
  4. Helper con lectura escalar incompatible → PRESERVE_SCALAR (no SAFE)
  5. Resumen de otro binario → BLOCKED
  6. Callsite o argumento diferente → BLOCKED
  7. CFG incompleto → ABSTAIN
  8. Evidencia contradictoria material → BLOCKED
  9. Dirección de carga no resuelta pero disjunta demostrada → no contamina
  10. Dirección no resuelta con posible solapamiento → ABSTAIN
  + SELLOS ROTOS
  + STATES indeterminados
"""
import os
import sys
import json
import copy
import hashlib

HERE = os.path.dirname(os.path.abspath(__file__))
PKG = os.path.abspath(os.path.join(HERE, ".."))
sys.path.insert(0, PKG)
os.environ["IER_STORE"] = "/tmp/ier_amitest_%d" % os.getpid()

from ier import call_summary_admission as csa  # noqa: E402

_fallos = []


def v(nombre, cond, info=""):
    if cond:
        print("  PASS %-60s" % nombre)
    else:
        print("  FAIL %-60s %s" % (nombre, info))
        _fallos.append(nombre)


FULL_SUMMARY = {
    "binary": {"sha256": "bca61fba97ea68566b55c2860a8798650424cd59fec5eaf9aff02e0ec4a3a4d7",
               "architecture": "PE-x86_64"},
    "function": {"entry": 0x1400035f4, "size": 204, "identity": "sub_1400035f4"},
    "callsite": {"caller": 0x140005234, "instruction": 0x1400052c9, "argument_index": 1,
                 "arguments": [
                     {"pos": 0, "kind": "rcx", "role": "table", "observed_value": "0x1400027f4", "provenance": "AIL"},
                     {"pos": 1, "kind": "rdx", "role": "buffer", "observed_value": "0x1400052ac", "provenance": "AIL"},
                 ]},
    "region": {"storage_id": "frame:-44:20", "start": -44, "end": -24, "address_space": "stack"},
    "effects": {
        "reads": [
            {"target": "arg1", "span": 19, "termination": "NUL", "frequency": "loop-bytewise"},
            {"target": "arg0", "span": 8, "termination": "entry_end", "frequency": "per-entry"},
        ],
        "writes": [],
        "read_order": ["arg1[0]", "arg1[1]"],
        "termination": {"rule": "byte-compare-hit or NUL",
                        "proof": ["objdump 0x1400035f4..0x1400036c2: movzx+cmp; ret en 0x1400036c3"]},
        "return_relation": {"relation": "pointer_derived_from_a0",
                            "proof": ["add rax,r9"]},
    },
    "coverage": {"completeness": "complete",
                 "scope_statement": "read-only w.r.t. args; args preserved",
                 "unresolved_paths": []},
    "oracle": {"binding": "SEAL: rxre-m10-7-sub_1400035f4",
               "verified_by": ["objdump -d 0x1400035f4..0x1400036c2"]},
}

CASE = {
    "artifact": {"path": "binaries/tests/x86_64/windows/cancel.sys",
                 "sha256": FULL_SUMMARY["binary"]["sha256"],
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

passed = csa.evaluate(FULL_SUMMARY, CASE)
v("helper completo demostradable → SAFE_TO_TRANSFORM",
  passed["verdict"] == "SAFE_TO_TRANSFORM")
v("helper completo: 10/10 reglas",
  passed["rules_passed"] == 10 and passed["rules_failed"] == 0)

# 2. Helper lee bytes sin terminación → ABSTAIN
critic = copy.deepcopy(FULL_SUMMARY)
critic["effects"]["termination"] = {}  # sin regla ni prueba
res = csa.evaluate(critic, CASE)
v("helper sin terminación → ABSTAIN",
  res["verdict"] == "ABSTAIN")
val2 = res["binding"]["R7_termination"]
v("  R7 UNKNOWN (no falso SAFE)", val2 == "UNKNOWN")

# 3. Helper que modifica el buffer → nunca asume SAFE; SAFE solo si efectos compatible
critic = copy.deepcopy(FULL_SUMMARY)
critic["effects"]["writes"] = [
    {"target": "arg1", "span": 2, "into_candidate": True}]
res = csa.evaluate(critic, CASE)
v("helper escribe en candidato → BLOCKED (ruptura material)",
  res["verdict"] == "BLOCKED")

# 4. Helper con lectura escalar incompatible → no SAFE (PRESERVE_SCALAR o ABSTAIN)
critic = copy.deepcopy(FULL_SUMMARY)
critic["effects"]["reads"] = [
    {"target": "arg1", "span": 4, "termination": "u32-read", "frequency": "per-entry"}]
# carga escalar — ninguna regla lo inhibe, el guard lo decide; pero NO es SAFE
# en nuestro contrato, porque read_order mención violación si hay writes:
critic["effects"]["writes"] = [
    {"target": "arg1", "span": 1, "into_candidate": False}]  # writes no en candidato
critic["effects"]["reads"] = [
    {"target": "arg1", "span": 4, "termination": "scalar_load_u32", "frequency": "once"}]
res = csa.evaluate(critic, CASE)
v("read escalar declarado → no SAFE (PRESERVE_SCALAR/ABSTAIN/BLOCKED)",
  res["verdict"] != "SAFE_TO_TRANSFORM")

# 5. Resumen de otro binario → BLOCKED
critic = copy.deepcopy(FULL_SUMMARY)
critic["binary"]["sha256"] = "0" * 64  # otro binario
res = csa.evaluate(critic, CASE)
v("resumen de otro binario → BLOCKED",
  res["verdict"] == "BLOCKED")
v("  R1 FALSE", res["binding"]["R1_binary"] == "FALSE")

# 6. Callsite o argumento diferente → BLOCKED
critic = copy.deepcopy(CASE)
critic["callsite"]["instruction"] = 0x14001000
res = csa.evaluate(FULL_SUMMARY, critic)
v("callsite instruction distinta → BLOCKED",
  res["verdict"] == "BLOCKED")
critic = copy.deepcopy(CASE)
critic["callsite"]["argument_index"] = 0
res = csa.evaluate(FULL_SUMMARY, critic)
v("argument_index distinto → BLOCKED",
  res["verdict"] == "BLOCKED")
critic = copy.deepcopy(FULL_SUMMARY)
critic["callsite"]["argument_index"] = 0
res = csa.evaluate(critic, CASE)
v("summary con argument_index distinto → BLOCKED",
  res["verdict"] == "BLOCKED")

# 7. CFG incompleto / evidencia de cobertura incompleta → ABSTAIN
critic = copy.deepcopy(FULL_SUMMARY)
critic["coverage"]["completeness"] = "partial"
critic["coverage"]["unresolved_paths"] = ["long lock with side effects on globals"]
res = csa.evaluate(critic, CASE)
v("coverage partial con paths no resueltos → ABSTAIN",
  res["verdict"] == "ABSTAIN")

# 8. Evidencia contradictoria material → BLOCKED
critic = copy.deepcopy(FULL_SUMMARY)
# contradiction: declare text_consuming but writes scalar contradictory
critic["effects"]["reads"] = [
    {"target": "arg1", "span": 4, "termination": "bug", "frequency": "loop"}]
critic["effects"]["return_relation"] = {"relation": "unresolved",
                                        "proof": []}
critic["effects"]["writes"] = [
    {"target": "global", "span": 8, "into_candidate": False}]
critic["coverage"]["completeness"] = "opaque"
res = csa.evaluate(critic, CASE)
v("evidencia contradictoria material → BLOCKED o ABSTAIN (nunca SAFE)",
  res["verdict"] in ("BLOCKED", "ABSTAIN"))

# 9. Dirección de carga no resuelta pero disjunta → no contamina
critic = copy.deepcopy(FULL_SUMMARY)
# reads already include a read matching f as terminal, plus a disjoint scalar read elsewhere
critic["effects"]["reads"] = [
    {"target": "arg1", "span": 19, "termination": "NUL", "frequency": "loop-bytewise"},
    {"target": "arg0_table", "span": 8, "termination": "entry_end", "frequency": "per-entry"},
]
res = csa.evaluate(critic, CASE)
v("lectura disjunta del candidato contado como no control → R5 TRUE",
  res["binding"]["R5_reads"] == "TRUE")

# 10. Dirección no resuelta con posible solapamiento → ABSTAIN
critic = copy.deepcopy(FULL_SUMMARY)
critic["coverage"]["completeness"] = "opaque"  # no hay argumento seguro
res = csa.evaluate(critic, CASE)
v("ambiguedad sobre solapamiento → ABSTAIN o BLOCKED (nunca SAFE)",
  res["verdict"] in ("BLOCKED", "ABSTAIN"))

# ── SELLOS ROTOS
critic = copy.deepcopy(FULL_SUMMARY)
critic["oracle"]["verified_by"] = []  # sello sin verificación real
res = csa.evaluate(critic, CASE)
v("sello declarado sin verified_by → ABSTAIN",
  res["verdict"] == "ABSTAIN")
critic = copy.deepcopy(FULL_SUMMARY)
critic["oracle"]["binding"] = "ningún/contrato conocido"
res = csa.evaluate(critic, CASE)
v("sello desconocido sin verified_by → ABSTAIN",
  res["verdict"] == "ABSTAIN")

# ── DETERMINISMO
res_a = csa.evaluate(FULL_SUMMARY, CASE)
res_b = csa.evaluate(FULL_SUMMARY, CASE)
v("determinismo: misma entrada → misma salida",
  json.dumps(res_a, sort_keys=True) == json.dumps(res_b, sort_keys=True))

# ── resumen entero FUNCTIONS mismatch → BLOCKED
critic = copy.deepcopy(FULL_SUMMARY)
critic["function"]["entry"] = 0xdeadbeef
res = csa.evaluate(critic, CASE)
v("función discordante → BLOCKED",
  res["verdict"] == "BLOCKED")

# ── verdicts correctos: no SAFE si falta validación externa
critic = copy.deepcopy(FULL_SUMMARY)
critic["binary"] = {"architecture": "PE-x86_64"}  # sin sha256
res = csa.evaluate(critic, CASE)
v("sello binario sin sha256 → ABSTAIN",
  res["verdict"] == "ABSTAIN")

print()
if _fallos:
    print("CALL_SUMMARY_ADMISSION FALLA:", _fallos)
    sys.exit(1)
print("call_summary_admission: OK")
sys.exit(0)
