#!/usr/bin/env python3
# SPDX-License-Identifier: GPL-2.0
"""Audit selected metadata invariants across an IR expression rewrite.

The module is independent of angr, AIL, and RXRE persistence. A caller supplies
the observed metadata before and after a rewrite, the fields that must survive,
coverage declarations, and evidence references. It detects omissions or
changes; it does not invoke or repair the rewriting engine.

The initial profile is `ail.binaryop.vector_shape`:
`bits`, `vector_count`, and `vector_size` must be preserved when a BinaryOp is
rebuilt. The interface also accepts a caller-defined field list for reuse with
other IR expression metadata.
"""
from __future__ import annotations

import json
from typing import Any, Dict, List

CONTRACT_VERSION = "RXRE-EXPRESSION-METADATA-WITNESS-1"
AIL_BINARYOP_VECTOR_SHAPE = ("bits", "vector_count", "vector_size")


def audit_expression_metadata(case: Dict[str, Any]) -> Dict[str, Any]:
    """Compare declared expression metadata before/after a rewrite.

    Operational `status` describes input handling. `verdict` describes the
    requested invariant check. The epistemic state is capped at `PARTIAL`,
    since the witness trusts the caller's extraction and coverage declarations.
    """
    if not isinstance(case, dict):
        return _invalid("case must be an object")

    before = case.get("before")
    after = case.get("after")
    if not isinstance(before, dict) or not isinstance(after, dict):
        return _invalid("before and after expressions are required objects")
    if not isinstance(before.get("metadata"), dict):
        return _invalid("before.metadata must be an object")
    if not isinstance(after.get("metadata"), dict):
        return _invalid("after.metadata must be an object")
    if not _nonempty_string(case.get("expression_id")):
        return _invalid("expression_id is required")
    if not _nonempty_string(case.get("before_evidence_ref")):
        return _invalid("before_evidence_ref is required")
    if not _nonempty_string(case.get("after_evidence_ref")):
        return _invalid("after_evidence_ref is required")

    fields = case.get("fields", list(AIL_BINARYOP_VECTOR_SHAPE))
    if (not isinstance(fields, list) or not fields or
            any(not _nonempty_string(field) for field in fields) or
            len(set(fields)) != len(fields)):
        return _invalid("fields must be a non-empty array of unique field names")

    unknown = []
    changed = []
    preserved = []
    for field in fields:
        if field not in before["metadata"] or before["metadata"][field] is None:
            unknown.append({"field": field, "reason": "source_value_unknown"})
            continue
        if field not in after["metadata"] or after["metadata"][field] is None:
            changed.append({"field": field, "before": before["metadata"][field],
                            "after": None, "reason": "value_dropped"})
            continue
        try:
            before_value = _canonical(before["metadata"][field])
            after_value = _canonical(after["metadata"][field])
        except (TypeError, ValueError):
            return _invalid("metadata field %r must contain JSON-compatible data" % field)
        if before_value != after_value:
            changed.append({"field": field, "before": before["metadata"][field],
                            "after": after["metadata"][field],
                            "reason": "value_changed"})
        else:
            preserved.append(field)

    coverage_complete = (case.get("before_complete") is True and
                         case.get("after_complete") is True)
    if not coverage_complete or unknown:
        verdict = "BLOCKED"
        epistemic = "NOT_DETERMINED"
    else:
        verdict = "FAIL" if changed else "PASS"
        epistemic = "PARTIAL"

    return {
        "contract": CONTRACT_VERSION,
        "profile": case.get("profile", "custom"),
        "status": "ok",
        "verdict": verdict,
        "epistemic_state": epistemic,
        "scope": {
            "expression_id": case["expression_id"],
            "expression_type_before": before.get("type"),
            "expression_type_after": after.get("type"),
            "fields_checked": list(fields),
            "before_complete": case.get("before_complete") is True,
            "after_complete": case.get("after_complete") is True,
            "before_evidence_ref": case["before_evidence_ref"],
            "after_evidence_ref": case["after_evidence_ref"],
        },
        "preserved": preserved,
        "violations": changed,
        "unknown": unknown,
        "limitations": [
            "Checks only the supplied fields and expression instance.",
            "Does not prove that the rewrite executed or that the extraction is authentic.",
            "PARTIAL is the maximum epistemic state this module can emit.",
        ],
    }


def ail_binaryop_vector_shape_case(before: Dict[str, Any], after: Dict[str, Any],
                                   *, expression_id: str,
                                   before_evidence_ref: str,
                                   after_evidence_ref: str,
                                   before_complete: bool = True,
                                   after_complete: bool = True) -> Dict[str, Any]:
    """Build a case for the AIL BinaryOp vector-shape preservation profile."""
    return {
        "profile": "ail.binaryop.vector_shape",
        "expression_id": expression_id,
        "before": before,
        "after": after,
        "fields": list(AIL_BINARYOP_VECTOR_SHAPE),
        "before_evidence_ref": before_evidence_ref,
        "after_evidence_ref": after_evidence_ref,
        "before_complete": before_complete,
        "after_complete": after_complete,
    }


def _canonical(value: Any) -> str:
    return json.dumps(value, sort_keys=True, separators=(",", ":"),
                      ensure_ascii=False, allow_nan=False)


def _nonempty_string(value: Any) -> bool:
    return isinstance(value, str) and bool(value.strip())


def _invalid(reason: str) -> Dict[str, Any]:
    return {"contract": CONTRACT_VERSION, "status": "error",
            "verdict": "BLOCKED", "epistemic_state": "NOT_DETERMINED",
            "scope": {}, "preserved": [], "violations": [], "unknown": [],
            "error": reason,
            "limitations": ["Malformed input cannot support a metadata conclusion."]}
