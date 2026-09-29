"""TASK A — executable assertions for DETERMINED_ABSENT.

The classifier is pure: five explicit inputs, no closure, no globals, no I/O.
These tests pin the rule that absence is only ever claimed when the evidence
that could falsify presence is complete, and that every other outcome stays
NOT_DETERMINED with a reason.

Synthetic only. No host, no /proc, no privilege. PROCESS_SCOPE is
UNDEFINED_BY_REQUIREMENT and PROCESS_NODE_COMPLETENESS is NOT_AVAILABLE; nothing
here closes either.
"""

import unittest

import privileged_read_collector as C


class AbsenceProofConditions(unittest.TestCase):
    """Each condition is a separate, individually falsifiable requirement."""

    def test_all_conditions_met_proves_absence(self):
        state, reason = C.classify_fd_absence("OK", [], 0, 0, "GONE")
        self.assertEqual(state, C.DETERMINED_ABSENT)
        self.assertEqual(reason,
                         "TABLE_READ_TARGETS_RESOLVED_NO_DRM_FD_THEN_GONE")

    def test_an_unreadable_fd_table_never_proves_absence(self):
        for status in ("EPERM", "ENOENT", "ABSENT", "ERROR", "", None):
            state, reason = C.classify_fd_absence(status, [], 0, 0, "GONE")
            self.assertEqual(state, C.NOT_DETERMINED)
            self.assertEqual(reason, "FD_TABLE_UNREADABLE")

    def test_any_fd_error_never_proves_absence(self):
        state, reason = C.classify_fd_absence(
            "OK", [{"error": "FileNotFoundError: /proc/1/fd/3"}], 0, 0, "GONE")
        self.assertEqual(state, C.NOT_DETERMINED)
        self.assertEqual(reason, "FD_ERROR_PRESENT")

    def test_an_unresolved_fd_target_never_proves_absence(self):
        """A target that could not be read might be the very node in question."""
        state, reason = C.classify_fd_absence("OK", [], 1, 0, "GONE")
        self.assertEqual(state, C.NOT_DETERMINED)
        self.assertEqual(reason, "FD_TARGET_UNRESOLVED")

    def test_a_drm_fd_seen_anywhere_never_proves_absence(self):
        """drm_fds_found is counted PID-wide: a DRM FD to any device blocks the
        proof.  Conservative on purpose; narrowing it needs per-node evidence
        this classifier does not have."""
        for found in (1, 3, 12):
            state, reason = C.classify_fd_absence("OK", [], 0, found, "GONE")
            self.assertEqual(state, C.NOT_DETERMINED)
            self.assertEqual(reason, "DRM_FD_PRESENT")

    def test_a_liveness_recheck_that_is_not_gone_never_proves_absence(self):
        for state_in, expected in (("ALIVE", "LIVENESS_ALIVE_CLAIMS_NOTHING"),
                                   ("UNKNOWN", "LIVENESS_UNKNOWN"),
                                   (None, "LIVENESS_None_CLAIMS_NOTHING")):
            state, reason = C.classify_fd_absence("OK", [], 0, 0, state_in)
            self.assertEqual(state, C.NOT_DETERMINED)
            self.assertEqual(reason, expected)

    def test_the_first_failing_condition_is_the_one_reported(self):
        """Reason ordering is fixed, so the report is a diagnosis and not a list."""
        _, r1 = C.classify_fd_absence("EPERM", ["e"], 3, 9, "ALIVE")
        self.assertEqual(r1, "FD_TABLE_UNREADABLE")
        _, r2 = C.classify_fd_absence("OK", ["e"], 3, 9, "GONE")
        self.assertEqual(r2, "FD_ERROR_PRESENT")
        _, r3 = C.classify_fd_absence("OK", [], 3, 9, "GONE")
        self.assertEqual(r3, "FD_TARGET_UNRESOLVED")
        _, r4 = C.classify_fd_absence("OK", [], 0, 9, "GONE")
        self.assertEqual(r4, "DRM_FD_PRESENT")

    def test_every_non_absent_outcome_carries_a_reason(self):
        cases = [("EPERM", [], 0, 0, "GONE"), ("OK", ["e"], 0, 0, "GONE"),
                 ("OK", [], 1, 0, "GONE"), ("OK", [], 0, 1, "GONE"),
                 ("OK", [], 0, 0, "ALIVE"), ("OK", [], 0, 0, None)]
        for args in cases:
            state, reason = C.classify_fd_absence(*args)
            self.assertEqual(state, C.NOT_DETERMINED)
            self.assertTrue(reason.strip(), "%r produced no reason" % (args,))


class AbsentIsPerPairNotUniversal(unittest.TestCase):
    """DETERMINED_ABSENT is a determination about one observation, not a claim
    about the system, and it is independent of PRESENT and NOT_DETERMINED."""

    def test_absent_is_not_a_global_not_present_statement(self):
        state, _ = C.classify_fd_absence("OK", [], 0, 0, "GONE")
        self.assertNotIn("NOT_PRESENT", state)
        self.assertNotIn("ABSENT", state.replace("DETERMINED_ABSENT", ""))

    def test_the_three_states_are_distinct_constants(self):
        self.assertEqual(len({C.DETERMINED_ABSENT, C.NOT_DETERMINED}), 2)
        self.assertTrue(C.DETERMINED_ABSENT.startswith("DETERMINED_"))

    def test_an_empty_fd_table_that_was_really_read_is_still_gated_by_liveness(self):
        """Zero file descriptors is not absence by itself: the process must also
        be observed gone, otherwise it may hold a resource opened after the
        sweep."""
        state, reason = C.classify_fd_absence("OK", [], 0, 0, "ALIVE")
        self.assertEqual(state, C.NOT_DETERMINED)
        self.assertIn("CLAIMS_NOTHING", reason)


class ClassifierIsPure(unittest.TestCase):
    """No closure, no globals, no I/O: the function receives everything."""

    def test_it_is_a_module_level_function_with_five_parameters(self):
        import inspect
        sig = inspect.signature(C.classify_fd_absence)
        self.assertEqual(list(sig.parameters),
                         ["fd_status", "fd_errors", "unresolved_target_count",
                          "drm_fds_found", "liveness_state"])
        self.assertEqual(C.classify_fd_absence.__module__, C.__name__)

    def test_it_does_not_mutate_its_inputs(self):
        errors = [{"error": "x"}]
        before = repr(errors)
        C.classify_fd_absence("OK", errors, 0, 0, "GONE")
        self.assertEqual(repr(errors), before)

    def test_repeated_calls_are_stable(self):
        first = C.classify_fd_absence("OK", [], 0, 0, "GONE")
        second = C.classify_fd_absence("OK", [], 0, 0, "GONE")
        self.assertEqual(first, second)

    def test_absence_proven_pids_does_not_exist_as_a_closure_counter(self):
        """The integration must not add a nonlocal to observe()."""
        self.assertNotIn("absence_proven_pids", dir(C))


if __name__ == "__main__":
    unittest.main()
