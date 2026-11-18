#!/usr/bin/env python3
# SPDX-License-Identifier: GPL-2.0
"""Focused, database-free checks for IR expression metadata preservation."""
from __future__ import annotations

import os
import sys

PKG = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
sys.path.insert(0, PKG)

from ier.expression_metadata_witness import (  # noqa: E402
    ail_binaryop_vector_shape_case,
    audit_expression_metadata,
)


BEFORE = {"type": "BinaryOp", "op": "InterleaveLOV",
          "metadata": {"bits": 128, "vector_size": 8, "vector_count": 16}}
LOST = {"type": "BinaryOp", "op": "InterleaveLOV",
        "metadata": {"bits": 128, "vector_size": None, "vector_count": None}}
PRESERVED = {"type": "BinaryOp", "op": "InterleaveLOV",
             "metadata": {"bits": 128, "vector_size": 8, "vector_count": 16}}


for engine in ("ssailification", "dephication"):
    lost = ail_binaryop_vector_shape_case(
        BEFORE, LOST, expression_id="expr:InterleaveLOV:128",
        before_evidence_ref="issue-7013:%s:before" % engine,
        after_evidence_ref="issue-7013:%s:after" % engine)
    report = audit_expression_metadata(lost)
    assert report["status"] == "ok"
    assert report["verdict"] == "FAIL"
    assert report["epistemic_state"] == "PARTIAL"
    assert report["preserved"] == ["bits"]
    assert [item["field"] for item in report["violations"]] == [
        "vector_count", "vector_size"]

    fixed = ail_binaryop_vector_shape_case(
        BEFORE, PRESERVED, expression_id="expr:InterleaveLOV:128",
        before_evidence_ref="regression:%s:before" % engine,
        after_evidence_ref="regression:%s:after" % engine)
    fixed_report = audit_expression_metadata(fixed)
    assert fixed_report["verdict"] == "PASS"
    assert fixed_report["epistemic_state"] == "PARTIAL"
    assert fixed_report["scope"]["fields_checked"] == [
        "bits", "vector_count", "vector_size"]

unknown = ail_binaryop_vector_shape_case(
    {"type": "BinaryOp", "metadata": {"bits": 128, "vector_size": None,
                                           "vector_count": None}},
    LOST, expression_id="expr:unknown",
    before_evidence_ref="source:unknown", after_evidence_ref="rewrite:unknown")
unknown_report = audit_expression_metadata(unknown)
assert unknown_report["verdict"] == "BLOCKED"
assert unknown_report["epistemic_state"] == "NOT_DETERMINED"

incomplete = ail_binaryop_vector_shape_case(
    BEFORE, PRESERVED, expression_id="expr:partial",
    before_evidence_ref="source:partial", after_evidence_ref="rewrite:partial",
    after_complete=False)
assert audit_expression_metadata(incomplete)["verdict"] == "BLOCKED"

custom = audit_expression_metadata({
    "profile": "caller.custom",
    "expression_id": "expr:custom",
    "before": {"type": "Load", "metadata": {"precision": 64, "space": "ram"}},
    "after": {"type": "Load", "metadata": {"precision": 64, "space": "register"}},
    "fields": ["precision", "space"],
    "before_evidence_ref": "source:custom",
    "after_evidence_ref": "rewrite:custom",
    "before_complete": True,
    "after_complete": True,
})
assert custom["verdict"] == "FAIL"
assert custom["violations"][0]["field"] == "space"

malformed = audit_expression_metadata({"expression_id": "x"})
assert malformed["status"] == "error"
assert malformed["epistemic_state"] == "NOT_DETERMINED"

print("PASS: catches dropped vector shape in both rewrite paths and accepts preservation")
print("      abstains on unknown/incomplete evidence and rejects malformed input")
