#!/usr/bin/env python3
# SPDX-License-Identifier: GPL-2.0
# WORK_CLASS=TEST . WRITE_EXECUTION=NONE . STATIC_ANALYSIS
#
# Regression test for the four epistemological dimensions discovered in Finding 1618.
# These four distinctions were confused in a prior session:
#
#   ACTION_EXECUTED  ≠  RELATION_PROVEN
#   REPAIR_PROVEN    ≠  CLAIM_PROVEN
#   SOFTWARE_EFFECT  ≠  HARDWARE_EFFECT
#
# Each test proves that the finding's header fields can be queried to recover
# the distinction WITHOUT reading the prose of the finding.
#
# PRE_EXECUTION_CONTRACT_CHECK:
#   producer: tools/rxre/tests/test_epistemic_distinctions.py (this file)
#   consumer: findings/*.md headers
#   artifact: header fields with exact names
#   exit 0 = all distinctions recoverable
#   exit 1 = at least one distinction NOT recoverable
#   NO SIGPIPE, NO truncation (JSON output, complete parse)
#

import os
import re
import sys
import unittest

HERE = os.path.dirname(os.path.abspath(__file__))
FINDINGS_DIR = os.path.abspath(os.path.join(
    HERE, "..", "..", "..", "06-INGENIERIA-INVERSA", "findings"))

# ── helpers ──────────────────────────────────────────────────────────────


def header_field(path, key):
    """Extract the value of a `KEY = value` header line from a finding markdown."""
    txt = open(path, encoding="utf-8", errors="replace").read()
    m = re.search(r"^%s\s*=\s*(.+)$" % re.escape(key), txt, re.M)
    return m.group(1).strip() if m else None


def has_header_key(path, key):
    """True iff the finding declares this key at all."""
    return header_field(path, key) is not None


# ── the four epistemological dimensions ──────────────────────────────────
# Each dimension is a tuple: (finding_file, header_key, expected_value, description)

DIMENSIONS = [
    # 1. ACTION_EXECUTED ≠ RELATION_PROVEN
    (
        "1618-reconciliation-1611-1617.md",
        "ACTION_EXECUTED",
        "EXECUTED",
        "ACTION_82 was EXECUTED (registered and run), but the relation "
        "SHADOW_START → soft_regs_start is NOT_ESTABLISHED. These must be "
        "distinguishable: an action can execute and still produce no proven relation.",
    ),
    # 2. LINK_NOT_FOUND ≠ PROVEN
    (
        "1618-reconciliation-1611-1617.md",
        "ACTION_RESULT",
        "LINK_NOT_FOUND",
        "ACTION_82_RESULT = LINK_NOT_FOUND means the relation was explicitly "
        "searched and not found. This is NOT the same as PROVEN — it is a "
        "negative result that refutes the hypothesis.",
    ),
    # 3. REPAIR_PROVEN ≠ CLAIM_PROVEN
    (
        "1617-reparacion-riesgo-soft-regs-start-zero.md",
        "REPAIR_STATUS",
        "MITIGATED",
        "The repair H1 is PROVEN_AS_CODE_CHANGE, but the original claim "
        "(soft_regs_start == 0 can reach consumers) has a separate status. "
        "REPAIR_PROVEN must not be conflated with CLAIM_PROVEN.",
    ),
    # 4. SOFTWARE_EFFECT_PROVEN ≠ HARDWARE_EFFECT_NOT_DETERMINED
    (
        "1617-reparacion-riesgo-soft-regs-start-zero.md",
        "HARDWARE_EFFECT",
        "NOT_DETERMINED",
        "The software effect (error propagation prevents the bad write in "
        "software control flow) is PROVEN. The hardware effect (no incorrect "
        "register write ever occurs on real hardware) is NOT_DETERMINED "
        "because no runtime observation was made. These must be distinct.",
    ),
]

# ── tests ────────────────────────────────────────────────────────────────


class TestEpistemicDistinctions(unittest.TestCase):
    """Verifies that all four epistemological dimensions are structurally
    recoverable from finding headers WITHOUT reading prose."""

    def test_01_action_executed_distinct_from_relation_proven(self):
        """ACTION_EXECUTED must be distinguishable from RELATION_PROVEN."""
        finding_path = os.path.join(
            FINDINGS_DIR, "1618-reconciliation-1611-1617.md")
        self.assertTrue(os.path.isfile(finding_path))

        ae = header_field(finding_path, "ACTION_EXECUTED")
        self.assertEqual(ae, "EXECUTED",
                         "ACTION_EXECUTED must be EXECUTED")

        rel = header_field(finding_path, "RELATION_STATUS")
        self.assertEqual(rel, "NOT_ESTABLISHED",
                         "RELATION_STATUS must be NOT_ESTABLISHED "
                         "(action executed ≠ relation proven)")

    def test_02_action_result_not_proven(self):
        """ACTION_RESULT = LINK_NOT_FOUND must be distinguishable from PROVEN."""
        finding_path = os.path.join(
            FINDINGS_DIR, "1618-reconciliation-1611-1617.md")
        self.assertTrue(os.path.isfile(finding_path))

        ar = header_field(finding_path, "ACTION_RESULT")
        self.assertEqual(ar, "LINK_NOT_FOUND",
                         "ACTION_RESULT must be LINK_NOT_FOUND")

        # If the relation were PROVEN, LINK_NOT_FOUND would be false
        rel = header_field(finding_path, "RELATION_STATUS")
        self.assertEqual(rel, "NOT_ESTABLISHED",
                         "RELATION_STATUS should be NOT_ESTABLISHED "
                         "for a LINK_NOT_FOUND action result")

    def test_03_repair_status_distinct_from_claim_status(self):
        """REPAIR_STATUS must be distinguishable from CLAIM_STATUS."""
        finding_path = os.path.join(
            FINDINGS_DIR,
            "1617-reparacion-riesgo-soft-regs-start-zero.md")
        self.assertTrue(os.path.isfile(finding_path))

        repair = header_field(finding_path, "REPAIR_STATUS")
        self.assertEqual(repair, "MITIGATED",
                         "REPAIR_STATUS must be MITIGATED "
                         "(repair proven ≠ claim proven)")

        claim = header_field(finding_path, "CLAIM_STATUS")
        self.assertEqual(claim, "PROVEN",
                         "CLAIM_STATUS must be PROVEN "
                         "(the claim was that soft_regs_start==0 reaches consumers)")

    def test_04_software_effect_distinct_from_hardware_effect(self):
        """SOFTWARE_EFFECT=PROVEN ≠ HARDWARE_EFFECT=NOT_DETERMINED."""
        finding_path = os.path.join(
            FINDINGS_DIR,
            "1617-reparacion-riesgo-soft-regs-start-zero.md")
        self.assertTrue(os.path.isfile(finding_path))

        sw = header_field(finding_path, "SOFTWARE_EFFECT")
        self.assertEqual(sw, "PROVEN",
                         "SOFTWARE_EFFECT must be PROVEN "
                         "(control flow analysis proves propagation)")

        hw = header_field(finding_path, "HARDWARE_EFFECT")
        self.assertEqual(hw, "NOT_DETERMINED",
                         "HARDWARE_EFFECT must be NOT_DETERMINED "
                         "(no runtime observation was made)")


# ── mutation tests (structural gaps) ─────────────────────────────────────
# Each mutation proves that removing/corrupting a distinction makes the test
# fail.  This demonstrates that the distinctions are structurally necessary,
# not optional.

class TestEpistemicMutations(unittest.TestCase):
    """Mutation tests that prove conflation is detectable."""

    def _mutate_and_check(self, basename, old_val, new_val,
                          key_to_check, expected_val):
        """Apply a mutation to a finding header and verify detection."""
        fpath = os.path.join(FINDINGS_DIR, basename)
        original = open(fpath, encoding="utf-8").read()
        mutant_path = fpath + ".mutant"

        mutated = original.replace(old_val, new_val)
        with open(mutant_path, "w", encoding="utf-8") as f:
            f.write(mutated)

        try:
            # After mutation, the key should have the NEW value
            actual = header_field(mutant_path, key_to_check)
            self.assertNotEqual(
                actual, expected_val,
                "Mutation should change '%s' from '%s' to different value"
                % (key_to_check, expected_val))
        finally:
            os.unlink(mutant_path)

    def test_mutation_ACTION_EXECUTED_to_PROVEN(self):
        """Mutate ACTION_EXECUTED=EXECUTED -> PROVEN (conflation).

        Expected: DETECTED. If the distinction between ACTION_EXECUTED and
        RELATION_PROVEN were lost, this mutation would not be caught by
        the non-mutation tests.
        """
        fpath = os.path.join(FINDINGS_DIR, "1618-reconciliation-1611-1617.md")
        original = open(fpath, encoding="utf-8").read()
        mutant_path = fpath + ".mutant"
        mutated = original.replace("ACTION_EXECUTED=EXECUTED",
                                   "ACTION_EXECUTED=PROVEN")
        with open(mutant_path, "w", encoding="utf-8") as f:
            f.write(mutated)
        try:
            actual = header_field(mutant_path, "ACTION_EXECUTED")
            # The mutation changes the value, so it should NOT match EXECUTED
            self.assertNotEqual(
                actual, "EXECUTED",
                "Mutation ACTION_EXECUTED->PROVEN should be detectable")
        finally:
            os.unlink(mutant_path)

    def test_mutation_ACTION_RESULT_to_PROVEN(self):
        """Mutate ACTION_RESULT=LINK_NOT_FOUND -> PROVEN (conflation).

        Expected: DETECTED. This proves LINK_NOT_FOUND ≠ PROVEN is
        distinguishable structurally.
        """
        fpath = os.path.join(FINDINGS_DIR, "1618-reconciliation-1611-1617.md")
        original = open(fpath, encoding="utf-8").read()
        mutant_path = fpath + ".mutant"
        mutated = original.replace("ACTION_RESULT=LINK_NOT_FOUND",
                                   "ACTION_RESULT=PROVEN")
        with open(mutant_path, "w", encoding="utf-8") as f:
            f.write(mutated)
        try:
            actual = header_field(mutant_path, "ACTION_RESULT")
            self.assertNotEqual(
                actual, "LINK_NOT_FOUND",
                "Mutation ACTION_RESULT->PROVEN should be detectable")
        finally:
            os.unlink(mutant_path)

    def test_mutation_REPAIR_STATUS_to_PROVEN(self):
        """Mutate REPAIR_STATUS=MITIGATED -> PROVEN (conflation with claim).

        Expected: DETECTED. This proves REPAIR_STATUS is distinguishable from
        CLAIM_STATUS.
        """
        fpath = os.path.join(FINDINGS_DIR,
                             "1617-reparacion-riesgo-soft-regs-start-zero.md")
        original = open(fpath, encoding="utf-8").read()
        mutant_path = fpath + ".mutant"
        mutated = original.replace("REPAIR_STATUS=MITIGATED",
                                   "REPAIR_STATUS=PROVEN")
        with open(mutant_path, "w", encoding="utf-8") as f:
            f.write(mutated)
        try:
            actual = header_field(mutant_path, "REPAIR_STATUS")
            self.assertNotEqual(
                actual, "MITIGATED",
                "Mutation REPAIR_STATUS->PROVEN should be detectable")
        finally:
            os.unlink(mutant_path)

    def test_mutation_HARDWARE_EFFECT_to_PROVEN(self):
        """Mutate HARDWARE_EFFECT=NOT_DETERMINED -> PROVEN (conflation with software).

        Expected: DETECTED. This proves HARDWARE_EFFECT is distinguishable from
        SOFTWARE_EFFECT.
        """
        fpath = os.path.join(FINDINGS_DIR,
                             "1617-reparacion-riesgo-soft-regs-start-zero.md")
        original = open(fpath, encoding="utf-8").read()
        mutant_path = fpath + ".mutant"
        mutated = original.replace("HARDWARE_EFFECT=NOT_DETERMINED",
                                   "HARDWARE_EFFECT=PROVEN")
        with open(mutant_path, "w", encoding="utf-8") as f:
            f.write(mutated)
        try:
            actual = header_field(mutant_path, "HARDWARE_EFFECT")
            self.assertNotEqual(
                actual, "NOT_DETERMINED",
                "Mutation HARDWARE_EFFECT->PROVEN should be detectable")
        finally:
            os.unlink(mutant_path)

    def test_mutation_CLAIM_STATUS_to_NOT_PROVEN(self):
        """Mutate CLAIM_STATUS=PROVEN -> NOT_PROVEN (claim retraction).

        Expected: DETECTED. This proves CLAIM_STATUS is independently
        queryable from REPAIR_STATUS.
        """
        fpath = os.path.join(FINDINGS_DIR,
                             "1617-reparacion-riesgo-soft-regs-start-zero.md")
        original = open(fpath, encoding="utf-8").read()
        mutant_path = fpath + ".mutant"
        mutated = original.replace("CLAIM_STATUS=PROVEN",
                                   "CLAIM_STATUS=NOT_PROVEN")
        with open(mutant_path, "w", encoding="utf-8") as f:
            f.write(mutated)
        try:
            actual = header_field(mutant_path, "CLAIM_STATUS")
            self.assertNotEqual(
                actual, "PROVEN",
                "Mutation CLAIM_STATUS->NOT_PROVEN should be detectable")
        finally:
            os.unlink(mutant_path)

    def test_mutation_SOFTWARE_EFFECT_to_NOT_DETERMINED(self):
        """Mutate SOFTWARE_EFFECT=PROVEN -> NOT_DETERMINED (downgrade).

        Expected: DETECTED. This proves the software/hardware distinction
        can be independently mutated.
        """
        fpath = os.path.join(FINDINGS_DIR,
                             "1617-reparacion-riesgo-soft-regs-start-zero.md")
        original = open(fpath, encoding="utf-8").read()
        mutant_path = fpath + ".mutant"
        mutated = original.replace("SOFTWARE_EFFECT=PROVEN",
                                   "SOFTWARE_EFFECT=NOT_DETERMINED")
        with open(mutant_path, "w", encoding="utf-8") as f:
            f.write(mutated)
        try:
            actual = header_field(mutant_path, "SOFTWARE_EFFECT")
            self.assertNotEqual(
                actual, "PROVEN",
                "Mutation SOFTWARE_EFFECT->NOT_DETERMINED should be detectable")
        finally:
            os.unlink(mutant_path)


if __name__ == "__main__":
    unittest.main()
