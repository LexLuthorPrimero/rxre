#!/usr/bin/env python3
"""Behavioral tests for DEFECT-04 (root_coverage -> ownership_matrix contract).

DEFECT-04: main() emits the live-sweep PID total into root_coverage under the
UPPERCASE record name "TOTAL_PIDS", while ownership_matrix() reads it under the
accumulator's own name "total_pids".  Every run therefore died with
    KeyError: 'total_pids'
at the first read, before any ownership verdict could be produced.

Fix A1 (authorized 2026-09-26): root_coverage now emits BOTH names from the
same accumulator cell, so TOTAL_PIDS == total_pids by construction for a given
run.  TOTAL_PIDS is retained because COLLECTOR-CHANGE-RECORD-20260925.md:58
documents it as part of the emitted root_coverage schema.

WHAT THIS TEST DOES *NOT* DO
----------------------------
It never calls inspect.getsource(), never greps the source for a string, and
never asserts that a name appears in the implementation.  A test that passes
merely because the expected name is present in the text is exactly the
tautology that let test_T31 report green coverage over a live defect.

WHAT IT DOES
------------
The producer is a dict literal built inside main(), a ~500-line procedural
function that cannot be invoked without root, /proc sweeping and a live window.
So the producer is *executed*, not read: the real Dict node is taken from the
real module's AST, compiled, and evaluated against a representative live
accumulator.  Its output is then handed to the *real* ownership_matrix, which
runs unmodified.  Both sides of the contract are therefore live code.

Resulting discrimination, all obtained by execution:
  * pre-fix producer shape  -> KeyError('total_pids')
  * post-fix producer shape -> 10 criteria (clients_pasid_attributable retired),
    OWNERSHIP_CRITERION_STATE=PARTIAL
  * drop "total_pids"       -> KeyError('total_pids')
  * drop "TOTAL_PIDS"       -> emitted-schema contract broken, caught by
                               the producer contract assertion
  * two different accumulators -> both names move together, so the equality
                               is structural and not a coincidental constant

No sudo, no /proc sweep, no system access of any kind.
"""

import ast
import importlib.util
import unittest

COLLECTOR_PATH = "privileged_read_collector.py"
ACCUMULATOR_NAME = "coverage"
PRODUCER_NAME = "root_coverage"
CONSUMER_NAME = "ownership_matrix"

# Keys whose removal is a distinct, separately-detectable regression.
UPPERCASE_RECORD_KEY = "TOTAL_PIDS"
LOWERCASE_CONTRACT_KEY = "total_pids"
# R1: scope of the POOLED fd-presence counters, emitted as data so a
# consumer can read it instead of inferring it.  Added 2026-09-26.
FD_PRESENCE_SCOPE_KEY = "fd_presence_scope"

# The exact free names the real producer literal closes over.  Kept explicit so
# that if the producer ever starts depending on a new main() local, the guard
# test fails loudly instead of the evaluation silently binding nothing.
#
# card_attributable and render_attributable were added by the card-render
# attribution correction: each row is now the shared completeness term conjoined
# with the attributability of its own node.  This guard did its job -- it named
# the two new dependencies instead of letting them bind silently -- so the set is
# widened here rather than the guard weakened.
# The per-node attribution term is gone: the composite that produced
# card_attributable/render_attributable mixed three relations from three domains
# into one predicate.  Completeness is now the sweep term alone, and the three
# fdinfo keys are counted per key.  Widened here rather than the guard weakened.
PRODUCER_FREE_NAMES = {
    "coverage", "root_fd_error_count", "root_visibility_complete",
    "node_presence", "node_coverage_complete", "card_target", "render_target",
}

# Representative live-sweep accumulators, shaped exactly like the accumulator
# literal main() builds at its own definition site.  Two distinct values are
# used so that any "both names hold the same constant" false pass is excluded.
ACCUMULATORS = {
    "primary": {
        "total_pids": 283,
        "root_pids": 199,
        "user_pids": 80,
        "uid_unknown_pids": 4,
        "late_observed_pids": 0,
        "fd_complete_pids": 270,
        "fd_error_pids": 13,
        "fd_permission_denied_pids": 7,
        "fd_disappeared_pids": 5,
        "fd_other_error_pids": 1,
        "maps_readable": 265,
        "maps_permission_denied": 13,
        "maps_absent": 0,
        "maps_error": 5,
        "root_namespace_ok": 199,
        "root_namespace_denied": 0,
        "root_namespace_total": 199,
        "user_namespace_ok": 80,
        "user_namespace_denied": 0,
        "drm_fds_found": 12,
        "drm_fdinfo_read": 11,
        "fd_presence_scope": "POOLED_ACROSS_NODES_FD_UNIT",
        "drm_client_id_seen": 11,
        "drm_pdev_seen": 11,
        "drm_pasid_seen": 11,
        "fd_universe_blocked_pids": 0,
        "fd_race_pids": 1,
        "fd_absence_proven_pids": 0,
        "root_namespace_disappeared": 0,
        "user_namespace_disappeared": 0,
        "user_namespace_total": 80,
    },
    "secondary": {
        "total_pids": 7,
        "root_pids": 3,
        "user_pids": 4,
        "uid_unknown_pids": 0,
        "late_observed_pids": 1,
        "fd_complete_pids": 6,
        "fd_error_pids": 1,
        "fd_permission_denied_pids": 1,
        "fd_disappeared_pids": 0,
        "fd_other_error_pids": 0,
        "maps_readable": 6,
        "maps_permission_denied": 1,
        "maps_absent": 0,
        "maps_error": 0,
        "root_namespace_ok": 3,
        "root_namespace_denied": 0,
        "root_namespace_total": 3,
        "user_namespace_ok": 4,
        "user_namespace_denied": 0,
        "drm_fds_found": 12,
        "drm_fdinfo_read": 11,
        "fd_presence_scope": "POOLED_ACROSS_NODES_FD_UNIT",
        "drm_client_id_seen": 11,
        "drm_pdev_seen": 11,
        "drm_pasid_seen": 11,
        "fd_universe_blocked_pids": 0,
        "fd_race_pids": 1,
        "fd_absence_proven_pids": 0,
        "root_namespace_disappeared": 0,
        "user_namespace_disappeared": 0,
        "user_namespace_total": 4,
    },
}


def _load_collector():
    spec = importlib.util.spec_from_file_location("d04_collector", COLLECTOR_PATH)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def _module_ast():
    with open(COLLECTOR_PATH, encoding="utf-8") as handle:
        return ast.parse(handle.read())


def _main_function(tree):
    for node in tree.body:
        if isinstance(node, ast.FunctionDef) and node.name == "main":
            return node
    raise AssertionError("main() not found in %s" % COLLECTOR_PATH)


def _assignment(function, name):
    for node in ast.walk(function):
        if (
            isinstance(node, ast.Assign)
            and isinstance(node.targets[0], ast.Name)
            and node.targets[0].id == name
        ):
            return node
    raise AssertionError("%s = {...} not found inside %s()" % (name, function.name))


def _literal_keys(assignment):
    return {k.value for k in assignment.value.keys if isinstance(k, ast.Constant)}


def _subscript_keys(assignment, base):
    """Constant keys read as <base>['...'] inside the given assignment."""
    return {
        node.slice.value
        for node in ast.walk(assignment.value)
        if isinstance(node, ast.Subscript)
        and isinstance(node.value, ast.Name)
        and node.value.id == base
        and isinstance(node.slice, ast.Constant)
    }


def _consumer_required_keys(function):
    """Constant keys the consumer reads from its coverage alias via [].

    ownership_matrix() binds `coverage = context['root_coverage']` (a pure
    alias), so its [] reads against `coverage` are reads against the very dict
    main() produces.  The DRM-attribution decision was moved into
    drm_fd_enumeration_state(), which receives the same dict, so its strict []
    reads count as part of the same contract.
    """
    functions = [function]
    for node in TREE.body:
        if isinstance(node, ast.FunctionDef) and node.name == "drm_fd_enumeration_state":
            functions.append(node)
    required = set()
    for func in functions:
        for node in ast.walk(func):
            if (
                isinstance(node, ast.Subscript)
                and isinstance(node.value, ast.Name)
                and node.value.id == "coverage"
                and isinstance(node.slice, ast.Constant)
            ):
                required.add(node.slice.value)
    return required


COLLECTOR = _load_collector()
TREE = _module_ast()
MAIN = _main_function(TREE)
PRODUCER = _assignment(MAIN, PRODUCER_NAME)
ACCUMULATOR = _assignment(MAIN, ACCUMULATOR_NAME)
CONSUMER = _load_collector()
CONSUMER_FUNCTION = next(
    node
    for node in TREE.body
    if isinstance(node, ast.FunctionDef) and node.name == CONSUMER_NAME
)


def produce(accumulator, drop=()):
    """Execute the real producer literal and return the dict main() would build."""
    fd_error_count = sum(
        accumulator[k]
        for k in (
            "fd_error_pids",
            "fd_permission_denied_pids",
            "fd_disappeared_pids",
            "fd_other_error_pids",
        )
    )
    namespace = {
        ACCUMULATOR_NAME: accumulator,
        "root_fd_error_count": fd_error_count,
        "root_visibility_complete": False,
        # Per-node, per-key counts.  Keyed BY KEY on purpose: a caller that could
        # read one domain's presence as another's would take a single value, and
        # this mapping makes that impossible without an explicit lookup.
        "node_presence": {
            "drm_fds": {"/dev/dri/card1": 12, "/dev/dri/renderD129": 0},
            "drm-client-id": {"/dev/dri/card1": 12, "/dev/dri/renderD129": 0},
            "drm-pdev": {"/dev/dri/card1": 12, "/dev/dri/renderD129": 0},
            "pasid": {"/dev/dri/card1": 12, "/dev/dri/renderD129": 0},
        },
        # The real function, so the producer literal is evaluated against
        # production behaviour and not against a stand-in.
        "node_coverage_complete": CONSUMER.node_coverage_complete,
        "card_target": "/dev/dri/card1",
        "render_target": "/dev/dri/renderD129",
    }
    built = eval(compile(ast.Expression(PRODUCER.value), "<producer>", "eval"), {}, namespace)
    for key in drop:
        built.pop(key, None)
    return built


def matrix_context(root_coverage):
    """A matrix context whose root_coverage is the given producer output."""
    return {
        "gpu_identity": {
            "GPU_IDENTITY_STATUS": "PROVEN",
            "GPU_CARD_NODE": "card1",
            "GPU_RENDER_NODE": "renderD129",
            "GPU_BDF": "0000:01:00.0",
        },
        PRODUCER_NAME: root_coverage,
        "debugfs": {
            "DEBUGFS_CLIENT_ATTRIBUTION": "PROVEN",
            "reason": "synthetic-fixture",
            "clients_path": "/sys/kernel/debug/dri/1/clients",
        },
        "btrfs_observation": {"status": "DEFERRED"},
        "btrfs_status": "ABSENT",
        "active_agents": 0,
        "pm_status": "READ",
        "card_drm_client_id_fds": 0,
        "render_drm_client_id_fds": 0,
    }


def evidence_for(result, condition):
    for row in result["conditions"]:
        if row["condition"] == condition:
            return row["EVIDENCE"]
    raise AssertionError("condition %r absent from ownership_matrix output" % condition)


class ProducerExecutableTests(unittest.TestCase):
    """The producer under test must be live code, not inspected text."""

    def test_producer_node_is_the_real_one_inside_main(self):
        self.assertEqual(PRODUCER.lineno, PRODUCER.value.lineno)
        self.assertEqual(PRODUCER.value.__class__, ast.Dict)
        self.assertTrue(PRODUCER.lineno > MAIN.lineno)

    def test_producer_free_names_are_exactly_the_ones_supplied(self):
        """A new dependency on a main() local must fail, not bind silently."""
        free = {
            node.id
            for node in ast.walk(PRODUCER.value)
            if isinstance(node, ast.Name) and isinstance(node.ctx, ast.Load)
        }
        self.assertEqual(free, PRODUCER_FREE_NAMES)

    def test_every_accumulator_key_the_producer_reads_exists_in_the_real_accumulator(self):
        """Closes the reverse direction: the producer must not KeyError either."""
        read = _subscript_keys(PRODUCER, ACCUMULATOR_NAME)
        self.assertTrue(read)
        self.assertEqual(read - _literal_keys(ACCUMULATOR), set())

    def test_each_fixture_matches_the_real_accumulator_key_set(self):
        real = _literal_keys(ACCUMULATOR)
        for label, accumulator in ACCUMULATORS.items():
            with self.subTest(accumulator=label):
                self.assertEqual(set(accumulator), real)


class ProducerContractTests(unittest.TestCase):
    """DEFECT-04 proper: the producer must satisfy the consumer's contract."""

    def test_producer_supplies_every_key_the_consumer_reads(self):
        """This is the assertion that failed before the fix."""
        required = _consumer_required_keys(CONSUMER_FUNCTION)
        self.assertTrue(required)
        self.assertEqual(
            required - set(produce(ACCUMULATORS["primary"])),
            set(),
            "producer is missing keys the consumer reads with [] -> KeyError at runtime",
        )

    def test_both_names_are_emitted_and_agree(self):
        built = produce(ACCUMULATORS["primary"])
        self.assertIn(UPPERCASE_RECORD_KEY, built)
        self.assertIn(LOWERCASE_CONTRACT_KEY, built)
        self.assertEqual(built[UPPERCASE_RECORD_KEY], built[LOWERCASE_CONTRACT_KEY])

    def test_both_names_track_the_accumulator_rather_than_a_constant(self):
        first = produce(ACCUMULATORS["primary"])
        second = produce(ACCUMULATORS["secondary"])
        self.assertNotEqual(
            first[UPPERCASE_RECORD_KEY], second[UPPERCASE_RECORD_KEY]
        )
        for built, accumulator in ((first, ACCUMULATORS["primary"]), (second, ACCUMULATORS["secondary"])):
            with self.subTest(total_pids=accumulator["total_pids"]):
                self.assertEqual(built[UPPERCASE_RECORD_KEY], accumulator["total_pids"])
                self.assertEqual(built[LOWERCASE_CONTRACT_KEY], accumulator["total_pids"])


class PreFixReproductionTests(unittest.TestCase):
    """The defect must still be demonstrable after the fix."""

    def test_pre_fix_producer_shape_raises_keyerror(self):
        with self.assertRaises(KeyError) as caught:
            CONSUMER.ownership_matrix(
                matrix_context(produce(ACCUMULATORS["primary"], drop=(LOWERCASE_CONTRACT_KEY, FD_PRESENCE_SCOPE_KEY)))
            )
        self.assertEqual(caught.exception.args[0], LOWERCASE_CONTRACT_KEY)

    def test_the_drop_reconstructs_the_pre_fix_shape_faithfully(self):
        """Dropping the added key must yield exactly the pre-fix key set.

        The pre-DEFECT-04 shape had 20 keys.  root_coverage has since grown by
        the DRM-attribution facts added for
        DRM_FDS_ENUMERATED_DOES_NOT_VALIDATE_CLIENT_ID, so the pre-fix shape is
        now the current shape minus those, in both directions: the lowercase
        contract key AND the attribution block.

        fd_absence_proven_pids joined that block for
        AGENTS_V3_RACE_STRICTER_THAN_COLLECTOR: a vanished PID discharges its
        lost coverage only when its absence of a DRM resource is proven.  The two
        *_namespace_disappeared counters joined it for MED-2: they separate a
        vanished PID from a denied read, and are dropped here for the same
        reason -- both are post-DEFECT-04 additions, so the pre-fix shape stays
        20 keys and the DEFECT-04 invariant is unchanged.

        This is the drop-reconstruction set, NOT the DRM attribution set of
        ExportTests.REQUIRED, which is deliberately left at seven keys.
        """
        post = _literal_keys(PRODUCER)
        attribution = {
            "drm_fds_found",
            "drm_fdinfo_read",
            "drm_client_id_seen",
            "drm_pdev_seen",
            "drm_pasid_seen",
            "fd_universe_blocked_pids",
            "fd_race_pids",
            "fd_absence_proven_pids",
            "root_namespace_disappeared",
            "user_namespace_disappeared",
        }
        self.assertTrue(attribution.issubset(post), "attribution block disappeared")
        # Six keys more than before: the three fdinfo domains, per node.  The
        # count is asserted from the names that must have appeared, so the pin
        # says WHY the shape changed instead of just freezing a number.
        for node in ("card", "render"):
            self.assertIn("%s_drm_client_id_fds" % node, post)
            self.assertIn("%s_drm_pdev_fds" % node, post)
            self.assertIn("%s_pasid_fds" % node, post)
        self.assertEqual(len(post), 38)
        per_node = {"%s_%s_fds" % (node, domain)
                    for node in ("card", "render")
                    for domain in ("drm_client_id", "drm_pdev", "pasid")}
        pre = post - attribution - per_node - {LOWERCASE_CONTRACT_KEY, FD_PRESENCE_SCOPE_KEY}
        self.assertEqual(len(pre), 20, "pre-DEFECT-04 shape was 20 keys")
        self.assertNotIn(LOWERCASE_CONTRACT_KEY, pre)
        dropped = produce(
            ACCUMULATORS["primary"],
            drop=(LOWERCASE_CONTRACT_KEY, FD_PRESENCE_SCOPE_KEY) + tuple(attribution) + tuple(per_node)
        )
        self.assertEqual(set(dropped), pre)


class ConsumerExecutionTests(unittest.TestCase):
    """The consumer must run to completion on real producer output."""

    def test_ownership_matrix_completes_on_real_producer_output(self):
        for label, accumulator in ACCUMULATORS.items():
            with self.subTest(accumulator=label):
                result = CONSUMER.ownership_matrix(matrix_context(produce(accumulator)))
                self.assertEqual(len(result["conditions"]), 10)
                self.assertIn("OWNERSHIP_CRITERION_STATE", result)

    def test_the_counted_total_reaches_the_evidence_field(self):
        """The value must travel producer -> consumer -> emitted evidence."""
        for label, accumulator in ACCUMULATORS.items():
            with self.subTest(accumulator=label):
                result = CONSUMER.ownership_matrix(matrix_context(produce(accumulator)))
                evidence = evidence_for(result, "drm_fds_enumerated")
                self.assertIn("across %d PIDs" % accumulator["total_pids"], evidence)


class RegressionDiscriminationTests(unittest.TestCase):
    """Removing either key must be caught, each by its own assertion."""

    def test_removing_the_lowercase_contract_key_is_caught(self):
        broken = produce(ACCUMULATORS["primary"], drop=(LOWERCASE_CONTRACT_KEY, FD_PRESENCE_SCOPE_KEY))
        required = _consumer_required_keys(CONSUMER_FUNCTION)
        self.assertNotEqual(required - set(broken), set())
        with self.assertRaises(KeyError):
            CONSUMER.ownership_matrix(matrix_context(broken))

    def test_removing_the_uppercase_record_key_is_caught(self):
        """The documented emitted-schema key must not be silently dropped.

        This is the half of the contract the consumer does not exercise: A1
        keeps TOTAL_PIDS because COLLECTOR-CHANGE-RECORD-20260925.md:58 names it
        as emitted.  Losing it would leave the consumer working while the
        output schema regressed, so it is asserted against the executed
        producer output rather than against source text.
        """
        broken = produce(ACCUMULATORS["primary"], drop=(UPPERCASE_RECORD_KEY,))
        # The consumer still works, which is precisely why this regression needs
        # its own assertion: it is invisible to the execution path.
        CONSUMER.ownership_matrix(matrix_context(broken))
        self.assertNotEqual({UPPERCASE_RECORD_KEY} - set(broken), set())


if __name__ == "__main__":
    unittest.main(verbosity=2)
