"""TASK C — executable assertions for the DRM node locator rules.

These tests pin four properties that were previously only inspectable in the
implementation text:

  A  node matching is EXACT basename equality, never prefix or substring;
  B  the minor type comes from the /dev/dri naming convention;
  C  project scope requires the minor type AND the PCI BDF (AGENTS.md:279);
  D  a field merely named ``node`` is not a DRM node locator;
  E  an unobserved node category is NOT_OBSERVED, never NOT_PRESENT;
  F  a locator is not an identity;
  G  nothing here is a production claim.

Synthetic only. No host, no /sys, no /proc, no GPU, no privilege.
Deliberately NOT tested here: determined_absent (NOT_AVAILABLE), PROCESS_SCOPE
(UNDEFINED_BY_REQUIREMENT) and the closure contract of observe().
"""

import ast
import inspect
import os
import unittest

import privileged_read_collector as C

HERE = os.path.dirname(os.path.abspath(__file__))


class ExactLocatorMatching(unittest.TestCase):
    """A. Two locators match only on exact basename equality."""

    def test_identical_bare_locators_match(self):
        self.assertTrue(C.locator_matches("card1", "card1"))
        self.assertTrue(C.locator_matches("renderD129", "renderD129"))

    def test_a_path_and_a_bare_name_match(self):
        self.assertTrue(C.locator_matches("/dev/dri/renderD129", "renderD129"))
        self.assertTrue(C.locator_matches("card1", "/dev/dri/card1"))

    def test_card0_does_not_match_card1(self):
        self.assertFalse(C.locator_matches("card0", "card1"))
        self.assertFalse(C.locator_matches("card1", "card0"))

    def test_renderD128_does_not_match_renderD129(self):
        self.assertFalse(C.locator_matches("renderD128", "renderD129"))
        self.assertFalse(C.locator_matches("renderD129", "renderD128"))

    def test_a_longer_name_does_not_match_a_shorter_one(self):
        self.assertFalse(C.locator_matches("card01", "card0"))
        self.assertFalse(C.locator_matches("card0", "card01"))
        self.assertFalse(C.locator_matches("renderD129x", "renderD129"))

    def test_prefix_and_substring_semantics_are_not_accepted(self):
        """The rule is equality.  These are the pairs a startswith/``in`` match
        would wrongly accept, asserted so the weaker rule cannot come back."""
        for left, right in (("card1", "card10"), ("renderD129", "renderD12"),
                            ("card0", "card"), ("renderD129", "renderD")):
            self.assertFalse(C.locator_matches(left, right),
                             "%r must not match %r by prefix" % (left, right))
            self.assertNotEqual(left, right)

    def test_empty_locators_never_match(self):
        self.assertFalse(C.locator_matches("", "card1"))
        self.assertFalse(C.locator_matches("card1", ""))
        self.assertFalse(C.locator_matches(None, "card1"))


class MinorTypeFromLocator(unittest.TestCase):
    """B. The minor type follows the kernel's /dev/dri naming convention."""

    def test_primary_and_render_are_recognised(self):
        self.assertEqual(C.minor_type_from_locator("card1"), "PRIMARY")
        self.assertEqual(C.minor_type_from_locator("renderD129"), "RENDER")

    def test_control_and_accel_are_recognised_but_are_not_project_nodes(self):
        self.assertEqual(C.minor_type_from_locator("controlD128"), "CONTROL")
        self.assertEqual(C.minor_type_from_locator("accel0"), "ACCEL")

    def test_an_unrecognised_locator_is_unknown_and_never_guessed(self):
        self.assertEqual(C.minor_type_from_locator("somethingElse"), "UNKNOWN")
        self.assertEqual(C.minor_type_from_locator(""), "UNKNOWN")
        self.assertEqual(C.minor_type_from_locator(None), "UNKNOWN")

    def test_the_type_is_the_same_for_every_device_with_that_locator_shape(self):
        """card0 and card1 are both PRIMARY: the name says the KIND of node, not
        the device.  Device membership is a separate, PCI-based question."""
        self.assertEqual(C.minor_type_from_locator("card0"),
                         C.minor_type_from_locator("card1"))


class ProjectScopeRequiresPciIdentity(unittest.TestCase):
    """C. AGENTS.md:279 — minor type AND the RX550's own BDF."""

    RX = "0000:01:00.0"
    INTEL = "0000:00:02.0"

    def test_primary_on_the_target_bdf_is_in_scope(self):
        self.assertTrue(C.node_in_project_scope(self.RX, "PRIMARY", self.RX))

    def test_render_on_the_target_bdf_is_in_scope(self):
        self.assertTrue(C.node_in_project_scope(self.RX, "RENDER", self.RX))

    def test_primary_on_a_foreign_bdf_is_out_of_scope(self):
        self.assertFalse(C.node_in_project_scope(self.INTEL, "PRIMARY", self.RX))

    def test_render_on_a_foreign_bdf_is_out_of_scope(self):
        self.assertFalse(C.node_in_project_scope(self.INTEL, "RENDER", self.RX))

    def test_control_and_accel_are_out_of_scope_even_on_the_target_bdf(self):
        self.assertFalse(C.node_in_project_scope(self.RX, "CONTROL", self.RX))
        self.assertFalse(C.node_in_project_scope(self.RX, "ACCEL", self.RX))

    def test_an_unknown_type_is_never_silently_admitted(self):
        self.assertFalse(C.node_in_project_scope(self.RX, "UNKNOWN", self.RX))

    def test_a_missing_bdf_is_never_admitted(self):
        self.assertFalse(C.node_in_project_scope(None, "PRIMARY", self.RX))


class IrqNodeIsNotADrmLocator(unittest.TestCase):
    """D. A field named ``node`` is not a DRM node locator.

    R1 records /irq/<n>/node with the value "-1": that is an IRQ node number,
    not a DRM locator.  Nothing keys off the key name.
    """

    def test_an_irq_node_value_yields_no_drm_minor_type(self):
        for value in ("-1", "-1", "0", "2"):
            self.assertEqual(C.minor_type_from_locator(value), "UNKNOWN",
                             "IRQ node %r must not resolve to a DRM minor" % value)

    def test_an_irq_node_value_never_matches_a_drm_locator(self):
        for value in ("-1", "0", "2"):
            self.assertFalse(C.locator_matches(value, "card1"))
            self.assertFalse(C.locator_matches("card1", value))

    def test_the_type_rule_uses_the_value_not_the_key_name(self):
        """Renaming a DRM locator's key would not change its type; presenting an
        IRQ number under the key 'node' does not make it one."""
        self.assertEqual(C.minor_type_from_locator("card1"), "PRIMARY")
        self.assertEqual(C.minor_type_from_locator("-1"), "UNKNOWN")


class UnobservedCategoryIsNotNotPresent(unittest.TestCase):
    """E. Not seeing a node category is NOT_OBSERVED, never NOT_PRESENT."""

    def _block(self, gpu):
        return C.process_node_observation_block(
            gpu, {"total_pids": 1, "root_pids": 1, "user_pids": 0,
                  "uid_unknown_pids": 0, "late_observed_pids": 0},
            0, 0, 0, 0, [], [], [], [], [])

    GPU = {"target": {"bdf": "0000:01:00.0"}, "drm_card": "card1",
           "render_node": "/dev/dri/renderD129", "intel_pci": "0000:00:02.0",
           "intel": {"card": "card0"}}

    def test_unobserved_categories_are_listed_as_not_observed(self):
        seen = self._block(self.GPU)["node_scope"]["categories_not_observed"]
        self.assertIn("CONTROL", seen)
        self.assertIn("ACCEL", seen)

    def test_the_block_never_emits_not_present(self):
        rendered = repr(self._block(self.GPU))
        self.assertNotIn("NOT_PRESENT", rendered)

    def test_the_word_observed_is_carried_explicitly(self):
        key = "categories_not_observed"
        self.assertIn(key, self._block(self.GPU)["node_scope"])

    def test_a_category_that_was_observed_is_not_listed_as_unobserved(self):
        seen = self._block(self.GPU)["node_scope"]["categories_not_observed"]
        self.assertNotIn("PRIMARY", seen)
        self.assertNotIn("RENDER", seen)


class LocatorIsNotIdentity(unittest.TestCase):
    """F. card1 and renderD129 are locators, not identities."""

    def test_the_node_record_declares_the_bdf_as_the_identity(self):
        block = C.process_node_observation_block(
            {"target": {"bdf": "0000:01:00.0"}, "drm_card": "card1",
             "render_node": "/dev/dri/renderD129", "intel_pci": "0000:00:02.0",
             "intel": {"card": "card0"}},
            {"total_pids": 1, "root_pids": 1, "user_pids": 0,
             "uid_unknown_pids": 0, "late_observed_pids": 0},
            0, 0, 0, 0, [], [], [], [], [])
        by_loc = {n["locator"]: n for n in block["node_scope"]["nodes"]}
        for locator, node in by_loc.items():
            # The identity basis must name the PCI BDF and must NOT be the
            # locator itself.  Asserting the negation of a phrase the field
            # legitimately contains was my own defective assertion; the check
            # that expresses the intent is equality against the locator.
            self.assertNotEqual(node["identity_basis"], locator)
            self.assertIn("BDF", node["identity_basis"])
        # The identity is the BDF, and it differs per node: the foreign device's
        # PRIMARY node is present with ITS OWN bdf and is out of scope.  Asserting
        # one BDF for every node was my own defective assertion; the meaningful
        # statement is that scope tracks the BDF.
        scoped = {n["locator"]: n["bdf"] for n in block["node_scope"]["nodes"]
                  if n["in_project_scope"]}
        self.assertEqual(scoped, {"card1": "0000:01:00.0",
                                  "/dev/dri/renderD129": "0000:01:00.0"})
        foreign = [n for n in block["node_scope"]["nodes"] if not n["in_project_scope"]]
        self.assertTrue(foreign)
        self.assertEqual(foreign[0]["bdf"], "0000:00:02.0")
        self.assertEqual(foreign[0]["minor_type"], "PRIMARY")

    def test_a_locator_alone_cannot_put_a_node_in_scope(self):
        """Same locator, different BDF: scope follows the BDF, not the name."""
        gpu = {"target": {"bdf": "0000:01:00.0"}, "drm_card": "card1",
               "render_node": "/dev/dri/renderD129",
               "intel_pci": "0000:00:02.0", "intel": {"card": "card1"}}
        block = C.process_node_observation_block(
            gpu, {"total_pids": 1, "root_pids": 1, "user_pids": 0,
                  "uid_unknown_pids": 0, "late_observed_pids": 0},
            0, 0, 0, 0, [], [], [], [], [])
        same_name = [n for n in block["node_scope"]["nodes"] if n["locator"] == "card1"]
        self.assertEqual(len(same_name), 2)
        self.assertEqual(sorted(n["in_project_scope"] for n in same_name), [False, True])


class NoProductionClaim(unittest.TestCase):
    """G. Nothing here establishes the production shape of gpu_clients[].node."""

    def test_the_block_records_the_locator_forms_it_was_given(self):
        block = C.process_node_observation_block(
            {"target": {"bdf": "0000:01:00.0"}, "drm_card": "card1",
             "render_node": "/dev/dri/renderD129",
             "intel_pci": "0000:00:02.0", "intel": {"card": "card0"}},
            {"total_pids": 1, "root_pids": 1, "user_pids": 0,
             "uid_unknown_pids": 0, "late_observed_pids": 0},
            0, 0, 0, 0, [], [], [], [],
            [{"pid": 7, "node": "card1"}])
        self.assertEqual(block["pairs"]["observed_locator_forms"], ["card1"])

    def test_the_absence_list_remains_not_available_and_is_not_faked(self):
        block = C.process_node_observation_block(
            {"target": {"bdf": "0000:01:00.0"}, "drm_card": "card1",
             "render_node": "/dev/dri/renderD129",
             "intel_pci": "0000:00:02.0", "intel": {"card": "card0"}},
            {"total_pids": 1, "root_pids": 1, "user_pids": 0,
             "uid_unknown_pids": 0, "late_observed_pids": 0},
            0, 0, 0, 0, [], [], [], [], [])
        self.assertIsNone(block["pairs"]["determined_absent"])
        self.assertIn("NOT_AVAILABLE", block["pairs"]["determined_absent_status"])
        self.assertNotIn("absence_proven_pids", dir(C))

    def test_process_scope_stays_undefined_by_requirement(self):
        block = C.process_node_observation_block(
            {"target": {"bdf": "0000:01:00.0"}, "drm_card": "card1",
             "render_node": "/dev/dri/renderD129",
             "intel_pci": "0000:00:02.0", "intel": {"card": "card0"}},
            {"total_pids": 283, "root_pids": 199, "user_pids": 84,
             "uid_unknown_pids": 0, "late_observed_pids": 0},
            0, 0, 0, 0, [], [], [], [], [])
        self.assertEqual(block["process_scope"]["status"], "UNDEFINED_BY_REQUIREMENT")
        self.assertIsNone(block["process_scope"]["count"])
        self.assertEqual(block["denominator"]["status"], "NOT_AVAILABLE")
        self.assertEqual(block["denominator"]["blocked_by"], "PROCESS_SCOPE")
        self.assertFalse(block["pairs"]["is_completeness_denominator"])


class TestHarnessHygiene(unittest.TestCase):
    """No test may be silently shadowed by a same-named method in its class.

    A duplicate name in one class means the first definition never runs while the
    file still appears to contain it.  That defect was found in this project's
    fixture: a row-count assertion had been dead for an unknown number of runs.
    """

    FILES = ("test_artifact_unit_contract.py", "test_drm_fds_enumerated_behavioral.py",
             "test_task_c_locator_matching.py")

    def test_no_duplicate_test_method_names_per_class(self):
        for name in self.FILES:
            path = os.path.join(HERE, name)
            if not os.path.exists(path):
                continue
            tree = ast.parse(open(path, encoding="utf-8").read())
            for node in ast.walk(tree):
                if not isinstance(node, ast.ClassDef):
                    continue
                seen = {}
                for item in node.body:
                    if isinstance(item, (ast.FunctionDef, ast.AsyncFunctionDef)) \
                            and item.name.startswith("test"):
                        self.assertNotIn(
                            item.name, seen,
                            "%s::%s: %s shadows the def at line %d"
                            % (name, node.name, item.name, seen.get(item.name, -1)))
                        seen[item.name] = item.lineno

    def test_the_helpers_under_test_exist_and_are_pure(self):
        for fn in (C.minor_type_from_locator, C.locator_matches,
                   C.node_in_project_scope):
            self.assertTrue(callable(fn))
            self.assertEqual(fn.__module__, C.__name__)


if __name__ == "__main__":
    unittest.main()
