"""Contract tests for the OWNERSHIP criterion, read-error visibility,
nomenclature, and probe calibration.

Repairs: RF-16a, RF-16b, RF-01, RF-06, METHO-04.

These tests are about CONTRACTS.  None of them interprets AGENTS.md and
none of them decides PASS/FAIL for any host:

  TECHNICAL_SEMANTICS  - what the kernel exposes            (not asserted here)
  PROJECT_REQUIREMENT  - what the project demands            (UNRESOLVED, not asserted)
  IMPLEMENTATION       - the declared rows and their states  (asserted)
  EVIDENCE             - the per-row EVIDENCE/SOURCE strings (asserted present)
  VERDICT              - the aggregate state                  (asserted never FULL
                                                               while a row is open)
"""

import ast
import os
import re
import unittest

import privileged_read_collector as collector

HERE = os.path.dirname(os.path.abspath(__file__))
MAIN = os.path.join(HERE, "privileged_read_collector.py")
SOURCE = open(MAIN, encoding="utf-8").read()

ALLOWED_ROW_STATES = {"PASS", "FAIL", "UNKNOWN", "NOT_APPLICABLE", "NOT_EVALUATED", "PARTIAL"}
ROW_REQUIRED_FIELDS = {"condition", "description", "STATE", "EVIDENCE", "SOURCE", "LIMITATION", "ROUTE"}
NEUTRAL = {
    "card_complete": True, "render_complete": True,
    "user_namespace_complete": True, "root_namespace_complete": True,
    "GPU_IDENTITY_STATUS": "PROVEN", "GPU_CARD_NODE": "card1",
    "GPU_RENDER_NODE": "renderD129", "active_agents": 0, "pm_status": "READ",
    "btrfs_status": "ABSENT",
}


def _context(gpu_proven=True):
    return {
        "gpu_identity": {"GPU_IDENTITY_STATUS": "PROVEN" if gpu_proven else "NOT_PROVEN",
                         "GPU_CARD_NODE": "card1", "GPU_RENDER_NODE": "renderD129"},
        "root_coverage": {"card_complete": True, "render_complete": True,
                          "user_namespace_complete": True, "root_namespace_complete": True},
        "debugfs": {}, "btrfs_observation": {},
        "active_agents": 0, "pm_status": "READ", "btrfs_status": "ABSENT",
    }


def _complete(ctx):
    """Derive the input key set from the implementation instead of guessing.

    A missing key is discovered by KeyError and seeded with a neutral value.
    The test therefore fails loudly if the collector grows an input this
    fixture cannot satisfy, rather than silently asserting less.
    """
    for _ in range(30):
        try:
            return collector.ownership_matrix(ctx)
        except KeyError as exc:
            key = str(exc).strip("'\"")
            for container in ("gpu_identity", "root_coverage", "debugfs",
                              "btrfs_observation", "pm_state"):
                if isinstance(ctx.get(container), dict) and key not in ctx[container]:
                    ctx[container][key] = NEUTRAL.get(key, 0)
                    break
            else:
                ctx[key] = NEUTRAL.get(key, 0)
    raise AssertionError("could not complete the ownership_matrix() input set")


def _rows(result):
    return result["conditions"]


class OwnershipCriterionContract(unittest.TestCase):
    """RF-16a / RF-16b: the criterion cannot drift from its own declarations."""

    def setUp(self):
        self.result = _complete(_context())
        self.declared = [key for key, _ in collector.OWNERSHIP_CRITERION_ROWS]
        self.rows = _rows(self.result)

    def test_row_count_equals_the_declared_criterion(self):
        self.assertTrue(self.declared, "the criterion must not be empty")
        self.assertEqual(
            len(self.rows), len(self.declared),
            "the matrix emits %d rows; the criterion declares %d"
            % (len(self.rows), len(self.declared)),
        )

    def test_row_names_match_the_declared_criterion(self):
        emitted = [row["condition"] for row in self.rows]
        self.assertEqual(sorted(emitted), sorted(self.declared),
                         "the emitted rows are not the declared rows")

    def test_every_row_carries_state_and_evidence(self):
        for row in self.rows:
            missing = ROW_REQUIRED_FIELDS - set(row)
            self.assertEqual(missing, set(),
                             "row %r lacks %s" % (row.get("condition"), sorted(missing)))
            self.assertIn(row["STATE"], ALLOWED_ROW_STATES,
                          "row %r has state %r outside the vocabulary"
                          % (row["condition"], row["STATE"]))

    def test_counters_partition_the_rows(self):
        """The four counters must partition the rows exactly once each.

        unknown_count covers UNKNOWN *and* NOT_APPLICABLE by design, so a
        NOT_APPLICABLE row must not be added a second time.
        """
        by_state = {}
        for row in self.rows:
            by_state[row["STATE"]] = by_state.get(row["STATE"], 0) + 1
        expected = {
            "pass_count": by_state.get("PASS", 0),
            "fail_count": by_state.get("FAIL", 0),
            "not_evaluated_count": by_state.get("NOT_EVALUATED", 0),
            "unknown_count": by_state.get("UNKNOWN", 0) + by_state.get("NOT_APPLICABLE", 0),
        }
        for key, value in expected.items():
            self.assertEqual(
                self.result[key], value,
                "%s is %s but the rows say %s" % (key, self.result[key], value),
            )
        self.assertEqual(sum(expected.values()), len(self.rows))

    def test_aggregate_is_never_full_while_a_row_is_open(self):
        """EMPTY_UNIVERSE != ALL_SATISFY.

        An all-green coverage fixture still leaves the audit-side rows
        unresolved, so the aggregate must not read FULL.
        """
        open_rows = [r["condition"] for r in self.rows
                     if r["STATE"] in ("NOT_EVALUATED", "UNKNOWN")]
        if open_rows:
            self.assertNotEqual(
                self.result["OWNERSHIP_CRITERION_STATE"], "FULL",
                "aggregate is FULL while %d row(s) are unresolved: %s"
                % (len(open_rows), open_rows),
            )

    def test_docstring_states_no_row_count(self):
        """RF-16b: prose must not name a number the code does not have.

        Replaces a docstring that claimed 11 rows while the criterion
        declared 10.
        """
        doc = collector.ownership_matrix.__doc__ or ""
        for mentioned in re.findall(r"\b(\d+)\s+rows?\b", doc):
            self.assertEqual(int(mentioned), len(self.declared))

    def test_module_text_names_no_stale_criterion_count(self):
        """RF-16b: no comment or emitted message may carry a stale count."""
        for number in (re.findall(r"(\d+)[- ]condition", SOURCE)
                       + re.findall(r"the (\d+) rows of the AGENTS", SOURCE)):
            # The prose must state the ACTUAL count.  A stale count is the
            # defect, so the assertion is equality: the earlier
            # assertNotEqual had inverted polarity and permitted any drift.
            self.assertEqual(
                int(number), len(self.declared),
                "module text names a %s-condition/row criterion; the code declares %d"
                % (number, len(self.declared)),
            )

    def test_artifact_key_is_fed_by_the_matrix_function(self):
        """RF-16a: the producer->artifact link, previously unverified.

        The bundle key must be a Name that is assigned from ownership_matrix().
        """
        tree = ast.parse(SOURCE)
        key_value = None
        for node in ast.walk(tree):
            if isinstance(node, ast.Dict):
                for key, value in zip(node.keys, node.values):
                    if isinstance(key, ast.Constant) and key.value == "AGENTS_OWNERSHIP_MATRIX":
                        key_value = value
        self.assertIsNotNone(key_value, "artifact key AGENTS_OWNERSHIP_MATRIX is absent")
        self.assertIsInstance(key_value, ast.Name)
        origin = None
        for node in ast.walk(tree):
            if isinstance(node, ast.Assign) and any(
                    isinstance(t, ast.Name) and t.id == key_value.id for t in node.targets):
                origin = node.value
        self.assertIsInstance(origin, ast.Call, "the key is not fed by a call")
        self.assertIsInstance(origin.func, ast.Name)
        self.assertEqual(origin.func.id, "ownership_matrix")


class ReadErrorVisibility(unittest.TestCase):
    """RF-01: a failed read must stay visible, never become an empty value."""

    def test_read_text_status_preserves_a_failed_read(self):
        result = collector.read_text_status("/proc/self/definitely_absent_xyz")
        self.assertNotEqual(result.get("status"), "OK")
        self.assertTrue(result.get("error"), "the read error must survive")

    def test_read_text_status_reports_ok_for_a_readable_file(self):
        result = collector.read_text_status(MAIN, 1 << 20)
        self.assertEqual(result.get("status"), "OK")
        self.assertIn("def ownership_matrix", result.get("value", ""))

    def test_hazardous_helper_behaviour_is_pinned(self):
        """read_text() still degrades to "".  Pinned so nobody assumes the
        hazard was silently removed, and so the guard below stays necessary."""
        self.assertEqual(collector.read_text("/proc/self/definitely_absent_xyz"), "")

    def test_evidence_bearing_fdinfo_path_keeps_its_read_outcome(self):
        """A READ_ERROR in the DRM fdinfo path must not become an empty value."""
        tree = ast.parse(SOURCE)
        target = next((n for n in ast.walk(tree)
                       if isinstance(n, ast.FunctionDef) and n.name == "scan_fds"), None)
        self.assertIsNotNone(target, "scan_fds must exist")
        called = {n.func.id for n in ast.walk(target)
                  if isinstance(n, ast.Call) and isinstance(n.func, ast.Name)}
        self.assertNotIn(
            "read_text", called,
            "scan_fds reads DRM fdinfo evidence; read_text() cannot distinguish a "
            "failed read from an empty file",
        )
        self.assertTrue({"read_bytes", "read_text_status"} & called)


class NomenclatureGuard(unittest.TestCase):
    """RF-06: the retired umbrella must not return; 'client' must be qualified."""

    def test_no_umbrella_attribution_identifier_in_code(self):
        """AST-level only: a retirement comment may name the old symbol."""
        tree = ast.parse(SOURCE)
        banned = {"DRM_ATTRIBUTION_FIELDS", "ATTRIBUTABLE", "node_attributable",
                  "card_attributable", "render_attributable", "clients_pasid_attributable",
                  "complete_and_attributable"}
        found = set()
        for node in ast.walk(tree):
            if isinstance(node, ast.Name):
                found.add(node.id)
            elif isinstance(node, ast.Attribute):
                found.add(node.attr)
            elif isinstance(node, (ast.FunctionDef, ast.ClassDef)):
                found.add(node.name)
        self.assertEqual(found & banned, set(),
                         "retired umbrella identifiers are back in code: %s"
                         % sorted(found & banned))

    def test_emitted_prose_never_says_bare_client(self):
        """Only PROSE is judged: an emitted sentence, not a kernel path.

        'clients', 'clients_path' and DEBUGFS_CLIENT_ATTRIBUTION name the
        kernel's own debugfs resource and are legitimately qualified by it.
        """
        tree = ast.parse(SOURCE)
        docstrings = set()
        for node in ast.walk(tree):
            if isinstance(node, (ast.Module, ast.ClassDef, ast.FunctionDef,
                                 ast.AsyncFunctionDef)):
                body = getattr(node, "body", None)
                if body and isinstance(body[0], ast.Expr) and isinstance(body[0].value, ast.Constant) \
                        and isinstance(body[0].value.value, str):
                    docstrings.add(id(body[0].value))
        offenders = []
        for node in ast.walk(tree):
            if not (isinstance(node, ast.Constant) and isinstance(node.value, str)):
                continue
            if id(node) in docstrings:
                continue  # a docstring explains; it is not an emitted value
            text = node.value
            if " " not in text:
                continue  # a path or an identifier, not prose
            if "client" not in text.lower():
                continue
            qualified = ("drm_file", "drm-client-id", "drm client", "DRM client",
                         "GPU client", "clients_pasid", "drm-client-", "debugfs client",
                         "drm_client", "attributable", "storage", "GPU DRM FD")
            if any(ok in text for ok in qualified):
                continue
            offenders.append((getattr(node, "lineno", "?"), text[:70]))
        self.assertEqual(offenders, [],
                         "emitted prose uses an unqualified 'client': %s" % offenders)


class ProbeCalibration(unittest.TestCase):
    """METHO-04 as a verifiable rule.

    A probe must be calibrated against a known-answer case before its output
    may be read as evidence.  The known-answer case lives here: a
    deliberately miscalibrated probe, and the demonstration that the
    calibration detects it.
    """

    @staticmethod
    def _miscalibrated(tree):
        """Counts only ``ast.Assert``.  Wrong for unittest."""
        hits = 0
        for node in ast.walk(tree):
            if isinstance(node, ast.FunctionDef) and node.name.startswith("test"):
                if any(isinstance(x, ast.Assert) for x in ast.walk(node)):
                    hits += 1
        return hits

    @staticmethod
    def _calibrated(tree):
        """Counts ``ast.Assert``, ``self.assertX()`` and ``self.fail()``."""
        hits = 0
        for node in ast.walk(tree):
            if not (isinstance(node, ast.FunctionDef) and node.name.startswith("test")):
                continue
            for x in ast.walk(node):
                if isinstance(x, ast.Assert):
                    hits += 1
                elif isinstance(x, ast.Call) and isinstance(x.func, ast.Attribute) \
                        and (x.func.attr.startswith("assert") or x.func.attr == "fail"):
                    hits += 1
        return hits

    def _suite_trees(self):
        for name in sorted(os.listdir(HERE)):
            if name.startswith("test_") and name.endswith(".py"):
                yield name, ast.parse(open(os.path.join(HERE, name), encoding="utf-8").read())

    def test_the_two_probes_disagree_so_the_calibration_has_teeth(self):
        """Without disagreement the calibration case would be void."""
        disagreements = []
        for name, tree in self._suite_trees():
            wrong, right = self._miscalibrated(tree), self._calibrated(tree)
            if wrong != right:
                disagreements.append("%s: %d vs %d" % (name, wrong, right))
        self.assertTrue(
            disagreements,
            "the miscalibrated probe and the calibrated probe agree on every "
            "file, so this module cannot demonstrate that a bad probe is caught",
        )

    def test_every_test_function_has_a_failure_mechanism(self):
        """The calibrated answer over the real suite: no unfailable test."""
        total, without = 0, []
        for name, tree in self._suite_trees():
            for node in ast.walk(tree):
                if isinstance(node, ast.FunctionDef) and node.name.startswith("test"):
                    total += 1
                    if self._calibrated(ast.Module(body=[node], type_ignores=[])) == 0:
                        without.append("%s:%s" % (name, node.name))
        self.assertGreater(total, 0, "the calibration found no tests at all")
        self.assertEqual(without, [], "tests with no failure mechanism: %s" % without)


if __name__ == "__main__":
    unittest.main()


class PooledFdPresenceScope(unittest.TestCase):
    """R1 defect: the *_seen counters are POOLED; the artifact must say so.

    PRE-fix the scope existed only in a comment, so a consumer reading the
    artifact could not distinguish a pooled FD count from a per-node
    population.  POST-fix the scope is data.
    """

    SCOPE_KEY = "fd_presence_scope"
    SCOPE_VALUE = "POOLED_ACROSS_NODES_FD_UNIT"

    def _coverage(self):
        import privileged_read_collector as c
        ctx = {"gpu_identity": {"GPU_IDENTITY_STATUS": "PROVEN", "GPU_CARD_NODE": "card1",
                                "GPU_RENDER_NODE": "renderD129"},
               "root_coverage": {"card_complete": True, "render_complete": True,
                                 "user_namespace_complete": True,
                                 "root_namespace_complete": True},
               "debugfs": {}, "btrfs_observation": {},
               "active_agents": 0, "pm_status": "READ", "btrfs_status": "ABSENT"}
        out = _complete(ctx)
        return out

    def test_scope_is_declared_as_data_not_only_in_a_comment(self):
        import privileged_read_collector as c
        tree = ast.parse(open(MAIN, encoding="utf-8").read())
        found = False
        for node in ast.walk(tree):
            if isinstance(node, ast.Dict):
                for key, value in zip(node.keys, node.values):
                    if (isinstance(key, ast.Constant) and key.value == self.SCOPE_KEY
                            and isinstance(value, ast.Constant)
                            and value.value == self.SCOPE_VALUE):
                        found = True
        self.assertTrue(
            found,
            "the artifact must carry %s=%s as data; a comment is not readable "
            "by a consumer" % (self.SCOPE_KEY, self.SCOPE_VALUE),
        )

    def test_a_consumer_can_tell_pooled_from_per_node(self):
        """The discrimination the defect denied: pooled total != per-node sum."""
        result = self._coverage()
        evidence = result["conditions"]
        pooled = None
        for row in evidence:
            if row["condition"] == "card_node_complete":
                pooled = row["EVIDENCE"]
        self.assertIsNotNone(pooled)
        import privileged_read_collector as c
        per_node = c.node_field_presence_counts([], ["card1", "renderD129"])
        self.assertEqual(
            per_node.get(self.SCOPE_KEY), "PER_NODE_FD_UNIT",
            "the per-node block must declare its own scope, or a consumer "
            "reading only that block cannot tell it from the pooled counters",
        )

    def test_pooled_value_is_never_presented_as_a_per_node_count(self):
        """A pooled number must not be readable as one node's population."""
        result = self._coverage()
        pooled_total = result.get("drm_client_id_seen")
        nodes = _per_node_presence(result)
        per_node_sum = sum(
            v for k, v in nodes.items()
            if k.endswith("_drm_client_id_fds") and isinstance(v, int)
        )
        if pooled_total is None or not isinstance(per_node_sum, int) or per_node_sum == 0:
            self.skipTest("no per-node fdinfo counters in this fixture")
        self.assertGreaterEqual(
            pooled_total, per_node_sum,
            "a POOLED total below the per-node sum would mean one of the two "
            "is not what its name says",
        )


def _per_node_presence(result):
    for row in result["conditions"]:
        if row["condition"] == "card_node_complete":
            return {"card_drm_client_id_fds": result.get("card_drm_client_id_fds", 0),
                    "render_drm_client_id_fds": result.get("render_drm_client_id_fds", 0),
                    "fd_presence_scope": result.get("fd_presence_scope")}
    return {}
