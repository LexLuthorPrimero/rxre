#!/usr/bin/env python3
"""Behavioral tests for DEFECT-06 (G-06 summary must derive from read state).

DEFECT-06: gap_results["G-06"]["summary"] was a string literal that asserted
observation unconditionally:

    "IRQ/affinity/queue/read-ahead/asynchronous-depth values observed; ..."

In R1 run 4 every one of the 16 queue reads was ERROR (wrong base path, see
DEFECT-05), yet the summary still claimed the values had been observed.  The
G-06 *status* was UNKNOWN, which is correct, so no false PASS was produced --
but the prose contradicted the bundle's own data.

THE TEST EXECUTES THE REAL CONSTRUCTION
---------------------------------------
The G-06 entry is located inside the real `gap_results = {...}` assignment in
the real main(), and that exact AST node is compiled and evaluated against
supplied state.  Pre-fix that node *is* a literal, so evaluating it reproduces
the defect faithfully; post-fix it is a call and evaluating it runs the real
derivation.  No test reads the source as text.

REQUIRED CASES
--------------
A. all reads OK            -> the summary may speak of observed values
B. some read ERROR         -> the summary must not claim the values were observed
C. all reads ERROR         -> the summary must state that nothing was observed
D. state UNKNOWN / absent  -> the summary must stay not-observed
"""

import ast
import importlib.util
import unittest

COLLECTOR_PATH = "privileged_read_collector.py"
GAP_ID = "G-06"
# Phrases that assert observation.  A summary carrying any of them while reads
# are failing is the defect.
CLAIM_PHRASES = ("values observed", "were observed", "observed;")
NEGATIVE_STATES = ("ERROR", "UNKNOWN", "NOT_EVALUATED", "NOT_AVAILABLE", "SKIPPED")


def load_collector():
    spec = importlib.util.spec_from_file_location("d06_collector", COLLECTOR_PATH)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


COLLECTOR = load_collector()

with open(COLLECTOR_PATH, encoding="utf-8") as _handle:
    TREE = ast.parse(_handle.read())
MAIN = next(n for n in TREE.body if isinstance(n, ast.FunctionDef) and n.name == "main")
GAP_RESULTS = next(
    n
    for n in ast.walk(MAIN)
    if isinstance(n, ast.Assign)
    and isinstance(n.targets[0], ast.Name)
    and n.targets[0].id == "gap_results"
)


def gap_entry_node(gap_id=GAP_ID):
    """The real AST node that builds one gap_results entry."""
    for key, value in zip(GAP_RESULTS.value.keys, GAP_RESULTS.value.values):
        if isinstance(key, ast.Constant) and key.value == gap_id:
            return value
    raise AssertionError("%s not present in the real gap_results" % gap_id)


def free_names(node):
    return {
        n.id
        for n in ast.walk(node)
        if isinstance(n, ast.Name) and isinstance(n.ctx, ast.Load)
    }


def build_gap_entry(namespace, gap_id=GAP_ID):
    """Execute the real construction of one gap_results entry."""
    return eval(
        compile(ast.Expression(gap_entry_node(gap_id)), "<gap-%s>" % gap_id, "eval"),
        {},
        namespace,
    )


def read(value, status="OK"):
    return {"status": status, "value": value, "bytes": len(value), "truncated": False}


def queue_payload(statuses):
    """statuses: dict name -> 'OK' | 'ERROR' | 'UNKNOWN'."""
    queue = {}
    for name, state in statuses.items():
        if state == "OK":
            queue[name] = read("0\n")
        else:
            queue[name] = {"status": state, "error": "synthetic %s" % state}
    return {"STORAGE_METRICS": "READ", "block_sysfs": "/sys/class/block/sdb/queue", "queue": queue}


def irq_payload(state="OK", count=4):
    selected = []
    for index in range(count):
        selected.append(
            {
                "irq": str(20 + index),
                "line": " %d: 0 0 0 0 IR-PCI-MSI-0000:00:1f.2" % (20 + index),
                "smp_affinity_list": "0-7" if state == "OK" else "",
                "effective_affinity_list": "0-7" if state == "OK" else "",
                "node": "0" if state == "OK" else "",
            }
        )
    return {"irq_line_count": 40, "selected": selected, "selection_keywords": ["amdgpu", "sdb"]}


def identity_payload(model="WDC WD5000LPCX-0", realpath_status="OK"):
    identity = {
        "block_name": "sdb3",
        "parent_disk": "sdb",
        "device_realpath": (
            {"status": "OK", "value": "../../../4:0:0:0"}
            if realpath_status == "OK"
            else {"status": realpath_status, "error": "synthetic"}
        ),
        "vendor": "ATA",
        "model": model,
        "state": "running",
        "host": "",
    }
    return {"STORAGE_METRICS": "READ", "block_sysfs": "/sys/class/block/sdb3", "identity": identity}


OK_QUEUE = {
    "scheduler": "OK",
    "read_ahead_kb": "OK",
    "rq_affinity": "OK",
    "nomerges": "OK",
    "async_depth": "OK",
    "nr_requests": "OK",
    "rotational": "OK",
    "logical_block_size": "OK",
    "physical_block_size": "OK",
    "max_sectors_kb": "OK",
    "write_cache": "OK",
    "add_random": "OK",
    "iostats": "OK",
    "write_same": "OK",
    "daemon": "OK",
    "rq_affinity_control": "OK",
}


def namespace(queue, irq_i=None, irq_f=None, identity=None, g06="UNKNOWN"):
    return {
        "g06": g06,
        "g06_summary": COLLECTOR.g06_summary,
        "queue_initial": queue,
        "irq_initial": irq_i if irq_i is not None else irq_payload(),
        "irq_final": irq_f if irq_f is not None else irq_payload(),
        "storage_identity_evidence": identity if identity is not None else identity_payload(),
    }


class ConstructionIsRealTests(unittest.TestCase):
    """Guards so the harness cannot silently stop exercising the real code."""

    def test_the_entry_is_built_inside_the_real_gap_results(self):
        self.assertIsInstance(gap_entry_node(), ast.Dict)
        self.assertIs(GAP_RESULTS.value.__class__, ast.Dict)

    def test_the_namespace_covers_every_free_name_of_the_real_node(self):
        supplied = set(namespace(queue_payload(OK_QUEUE)))
        self.assertEqual(free_names(gap_entry_node()), supplied)


class CaseA_AllReadsOKTests(unittest.TestCase):
    """A. All reads OK: the summary may speak of observed values."""

    def setUp(self):
        self.entry = build_gap_entry(namespace(queue_payload(OK_QUEUE)))
        self.summary = self.entry["summary"]

    def test_status_is_unchanged_and_still_unknown(self):
        self.assertEqual(self.entry["status"], "UNKNOWN")

    def test_the_summary_may_then_claim_observation(self):
        self.assertTrue(
            any(phrase in self.summary for phrase in CLAIM_PHRASES),
            "with every read OK the summary is allowed to report observed values",
        )

    def test_it_names_the_dimensions_it_claims(self):
        for token in ("queue", "affinity"):
            self.assertIn(token, self.summary)


class CaseB_SomeReadsFailTests(unittest.TestCase):
    """B. At least one read ERROR: the summary must not claim observation."""

    def setUp(self):
        statuses = dict(OK_QUEUE)
        statuses["scheduler"] = "ERROR"
        statuses["daemon"] = "ERROR"
        self.entry = build_gap_entry(namespace(queue_payload(statuses)))
        self.summary = self.entry["summary"]

    def test_the_summary_does_not_claim_the_values_were_observed(self):
        for phrase in CLAIM_PHRASES:
            self.assertNotIn(phrase, self.summary)

    def test_the_summary_reports_the_failing_reads(self):
        self.assertIn("ERROR", self.summary)
        self.assertIn("scheduler", self.summary)

    def test_the_summary_distinguishes_observed_from_failed(self):
        self.assertRegex(self.summary, r"\d+")

    def test_status_remains_unknown(self):
        self.assertEqual(self.entry["status"], "UNKNOWN")


class CaseC_AllReadsFailTests(unittest.TestCase):
    """C. Every read ERROR: the summary must state nothing was observed."""

    def setUp(self):
        statuses = {name: "ERROR" for name in OK_QUEUE}
        self.entry = build_gap_entry(namespace(queue_payload(statuses)))
        self.summary = self.entry["summary"]

    def test_the_summary_does_not_claim_observation(self):
        for phrase in CLAIM_PHRASES:
            self.assertNotIn(phrase, self.summary)

    def test_the_summary_states_the_reads_did_not_succeed(self):
        lowered = self.summary.lower()
        self.assertTrue(
            any(token in lowered for token in ("error", "failed", "not read", "unread")),
            self.summary,
        )

    def test_it_reports_no_observed_value_count(self):
        self.assertIn("0", self.summary)

    def test_irq_and_identity_failures_are_also_reflected(self):
        entry = build_gap_entry(
            namespace(
                queue_payload({name: "ERROR" for name in OK_QUEUE}),
                irq_i=irq_payload(state="UNKNOWN", count=0),
                identity=identity_payload(model="", realpath_status="ERROR"),
            )
        )
        summary = entry["summary"]
        for phrase in CLAIM_PHRASES:
            self.assertNotIn(phrase, summary)
        self.assertIn("0", summary)


class CaseD_UnknownOrAbsentTests(unittest.TestCase):
    """D. UNKNOWN or absent data: the summary must stay not-observed."""

    def test_unknown_irq_state_is_not_reported_as_observed(self):
        entry = build_gap_entry(
            namespace(queue_payload(OK_QUEUE), irq_i=irq_payload(state="UNKNOWN", count=0))
        )
        for phrase in ("affinity observed",):
            self.assertNotIn(phrase, entry["summary"])

    def test_absent_queue_payload_is_handled(self):
        entry = build_gap_entry(
            namespace({"STORAGE_METRICS": "SKIPPED_IDENTITY_NOT_PROVEN", "queue": {}})
        )
        for phrase in CLAIM_PHRASES:
            self.assertNotIn(phrase, entry["summary"])
        self.assertEqual(entry["status"], "UNKNOWN")

    def test_absent_identity_evidence_is_handled(self):
        """A missing dimension must be named, without discarding truthful ones.

        The queue reads really did succeed here, so the queue claim is allowed to
        stand.  What must not happen is the identity dimension being reported as
        observed, or being dropped silently.
        """
        entry = build_gap_entry(
            namespace(
                queue_payload(OK_QUEUE),
                identity={"STORAGE_METRICS": "SKIPPED_IDENTITY_NOT_PROVEN", "identity": None},
            )
        )
        self.assertIn("storage_identity=NOT_AVAILABLE", entry["summary"])
        self.assertNotIn("storage_identity_strings=", entry["summary"])
        self.assertNotIn("storage_identity_device_realpath=OK", entry["summary"])
        self.assertEqual(entry["status"], "UNKNOWN")

    def test_a_failed_identity_read_is_not_reported_as_a_string(self):
        """The failed read is named, and the strings it did yield are kept.

        Here vendor and state were read successfully while model and the
        device_realpath link were not.  The summary must report the failure and
        still report what was genuinely read, rather than collapsing the whole
        dimension to NOT_AVAILABLE.
        """
        entry = build_gap_entry(
            namespace(
                queue_payload(OK_QUEUE),
                identity=identity_payload(model="", realpath_status="ERROR"),
            )
        )
        summary = entry["summary"]
        self.assertIn("storage_identity_device_realpath=ERROR", summary)
        self.assertIn("vendor=ATA", summary)
        self.assertIn("state=running", summary)
        self.assertNotIn("model=", summary)

    def test_every_negative_state_is_never_silently_dropped(self):
        for state in NEGATIVE_STATES:
            with self.subTest(state=state):
                statuses = dict(OK_QUEUE)
                statuses["read_ahead_kb"] = state
                entry = build_gap_entry(namespace(queue_payload(statuses)))
                self.assertNotIn("read_ahead_kb observed", entry["summary"])


class SummaryIsDerivedTests(unittest.TestCase):
    """The summary must change with the state, not be a constant."""

    def test_two_different_states_produce_two_different_summaries(self):
        healthy = build_gap_entry(namespace(queue_payload(OK_QUEUE)))["summary"]
        broken = build_gap_entry(
            namespace(queue_payload({name: "ERROR" for name in OK_QUEUE}))
        )["summary"]
        self.assertNotEqual(healthy, broken)

    def test_the_summary_never_names_an_invented_value(self):
        """A failing read must not be reported with a value."""
        statuses = dict(OK_QUEUE)
        statuses["read_ahead_kb"] = "ERROR"
        entry = build_gap_entry(namespace(queue_payload(statuses)))
        self.assertNotIn("read_ahead_kb=8192", entry["summary"])
        self.assertNotIn("read_ahead_kb=0", entry["summary"])


if __name__ == "__main__":
    unittest.main(verbosity=2)
