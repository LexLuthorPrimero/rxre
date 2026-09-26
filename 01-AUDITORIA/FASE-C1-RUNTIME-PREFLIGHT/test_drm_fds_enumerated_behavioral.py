#!/usr/bin/env python3
"""Behavioral tests for drm_fds_enumerated scoring.

The row used to be scored on ``fd_error_count == 0`` -- a global error proxy.
That proxy could not distinguish three materially different worlds, and it made
a benign /proc race look like an isolation failure:

    0 errors, 0 DRM fds on the whole host          -> PASS
    0 errors, 12 DRM fds, every fdinfo empty      -> PASS
    0 errors, 12 DRM fds, all fully attributed    -> PASS
    1 vanished process mid-sweep                   -> FAIL

The row is now scored on per-client DRM attribution facts exported by
``root_coverage``.  These tests drive the real decision function and the real
``ownership_matrix``, and they assert on the state *and* the reason, because a
state without a discriminating reason is exactly the defect being fixed.
"""

import importlib.util
import json
import os
import tempfile
import unittest
from pathlib import Path
from unittest import mock

COLLECTOR_PATH = "privileged_read_collector.py"
BUNDLE = "R1-20260926T030435Z.json"
CARD = "/dev/dri/card1"
RENDER = "/dev/dri/renderD129"

# A complete sweep with nothing found and nothing wrong.
QUIET = {
    "drm_fds_found": 0,
    "drm_fdinfo_read": 0,
    "drm_client_id_seen": 0,
    "drm_pdev_seen": 0,
    "drm_pasid_seen": 0,
    "fd_universe_blocked_pids": 0,
    "fd_race_pids": 0,
}

# A sweep in which every DRM fd is read and fully attributed.
FULLY_ATTRIBUTED = dict(
    QUIET,
    drm_fds_found=12,
    drm_fdinfo_read=12,
    drm_client_id_seen=12,
    drm_pdev_seen=12,
    drm_pasid_seen=12,
)


def load_collector():
    spec = importlib.util.spec_from_file_location("drmfd_collector", COLLECTOR_PATH)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


COLLECTOR = load_collector()


def base_coverage():
    """The real R1-4 root_coverage, so the tests run against a real shape."""
    if os.path.exists(BUNDLE):
        return json.load(open(BUNDLE))["ownership"]["root_coverage"]
    return {}


def context(coverage, proven=True):
    return {
        "root_coverage": coverage,
        "gpu_identity": {
            "GPU_IDENTITY_STATUS": "PROVEN" if proven else "UNKNOWN",
            "GPU_CARD_NODE": CARD.split("/")[-1],
            "GPU_RENDER_NODE": RENDER.split("/")[-1],
        },
        "debugfs": {
            "DEBUGFS_CLIENT_ATTRIBUTION": "PROVEN",
            "reason": "MINOR_DERIVED_AND_DRIVER_CONFIRMED",
            "clients_path": "/sys/kernel/debug/dri/129/clients",
        },
        "btrfs_observation": {"status": "DEFERRED"},
        "btrfs_status": "ABSENT",
        "active_agents": 5,
        "pm_status": "READ",
        "card_clients": 8,
        "render_clients": 4,
    }


def score(**overrides):
    coverage = dict(base_coverage())
    coverage.update(overrides)
    return COLLECTOR.drm_fd_enumeration_state(coverage, gpu_proven=True)


def row(**overrides):
    coverage = dict(base_coverage())
    coverage.update(overrides)
    result = COLLECTOR.ownership_matrix(context(coverage))
    return next(c for c in result["conditions"] if c["condition"] == "drm_fds_enumerated")


class AttributionExtractionTests(unittest.TestCase):
    """fdinfo_attribution reports presence, never a value, never a guess."""

    def test_all_three_fields_are_found(self):
        text = "drm-driver:\tamdgpu\ndrm-client-id:\t71\ndrm-pdev:\t0000:01:00.0\npasid:\t43\n"
        self.assertEqual(
            COLLECTOR.fdinfo_attribution(text),
            {"drm-client-id": True, "drm-pdev": True, "pasid": True},
        )

    def test_no_field_is_reported_when_none_is_present(self):
        self.assertEqual(
            COLLECTOR.fdinfo_attribution("pos:\t0\nflags:\t02100002\n"),
            {"drm-client-id": False, "drm-pdev": False, "pasid": False},
        )

    def test_empty_and_none_do_not_raise(self):
        for value in ("", None):
            self.assertEqual(
                COLLECTOR.fdinfo_attribution(value),
                {"drm-client-id": False, "drm-pdev": False, "pasid": False},
            )

    def test_a_partial_fdinfo_reports_only_what_it_has(self):
        got = COLLECTOR.fdinfo_attribution("drm-client-id:\t71\n")
        self.assertEqual(got, {"drm-client-id": True, "drm-pdev": False, "pasid": False})


class RequiredCasesTests(unittest.TestCase):
    """The seven cases the authorization requires to be distinguishable."""

    def test_1_complete_sweep_with_no_drm_fds_is_pass(self):
        state, reason = score(**QUIET)
        self.assertEqual(state, "PASS")
        self.assertIn("0 DRM fds found", reason)

    def test_2_complete_sweep_with_attributed_clients_is_pass(self):
        state, reason = score(**FULLY_ATTRIBUTED)
        self.assertEqual(state, "PASS")
        self.assertIn("12 DRM fd(s) all attributed", reason)

    def test_3_clients_found_but_fdinfo_unreadable_is_partial(self):
        state, reason = score(**dict(QUIET, drm_fds_found=12, drm_fdinfo_read=0))
        self.assertEqual(state, "PARTIAL")
        self.assertIn("fdinfo unreadable on 12/12", reason)

    def test_4_fdinfo_read_without_attribution_fields_is_partial(self):
        state, reason = score(**dict(QUIET, drm_fds_found=12, drm_fdinfo_read=12))
        self.assertEqual(state, "PARTIAL")
        self.assertIn("drm-client-id absent on 12/12", reason)
        self.assertIn("drm-pdev absent on 12/12", reason)
        self.assertIn("pasid absent on 12/12", reason)

    def test_5_a_vanished_process_does_not_by_itself_break_the_row(self):
        """A vanished PID alongside fully attributed clients stays PASS.

        The clients were all read and all attributed, so what is known about
        them is complete.  The vanished PID is still reported, but V3 forbids
        calling it benign: its absence of a DRM resource is not proven, and this
        row makes no claim about it either way.
        """
        state, reason = score(
            **dict(FULLY_ATTRIBUTED, fd_race_pids=1, fd_error_count=1)
        )
        self.assertEqual(state, "PASS")
        self.assertIn("1 PID(s) vanished", reason)
        self.assertNotIn("benign", reason)
        self.assertNotIn("absence", reason)

    def test_6_a_permission_error_is_partial_when_clients_were_seen(self):
        state, reason = score(
            **dict(FULLY_ATTRIBUTED, fd_universe_blocked_pids=1, fd_error_count=1)
        )
        self.assertEqual(state, "PARTIAL")
        self.assertIn("universe not enumerable", reason)

    def test_7_a_mixture_of_attributed_and_incomplete_is_partial(self):
        state, reason = score(
            **dict(QUIET, drm_fds_found=12, drm_fdinfo_read=12, drm_client_id_seen=10,
                   drm_pdev_seen=12, drm_pasid_seen=12)
        )
        self.assertEqual(state, "PARTIAL")
        self.assertIn("drm-client-id absent on 2/12", reason)


class DiscriminationTests(unittest.TestCase):
    """The point of the fix: worlds that used to collide must now differ."""

    def test_no_clients_and_unattributable_clients_no_longer_collide(self):
        empty = row(**QUIET)
        unattributable = row(**dict(QUIET, drm_fds_found=12, drm_fdinfo_read=0))
        self.assertEqual(empty["STATE"], "PASS")
        self.assertEqual(unattributable["STATE"], "PARTIAL")
        self.assertNotEqual(empty["EVIDENCE"], unattributable["EVIDENCE"])

    def test_unreadable_fdinfo_and_absent_fields_no_longer_collide(self):
        unreadable = row(**dict(QUIET, drm_fds_found=12, drm_fdinfo_read=0))
        absent = row(**dict(QUIET, drm_fds_found=12, drm_fdinfo_read=12))
        self.assertNotEqual(unreadable["EVIDENCE"], absent["EVIDENCE"])
        self.assertIn("fdinfo unreadable", unreadable["EVIDENCE"])
        self.assertNotIn("fdinfo unreadable", absent["EVIDENCE"])

    def test_every_required_case_yields_a_distinct_verdict_pair(self):
        verdicts = {}
        cases = {
            "none": QUIET,
            "full": FULLY_ATTRIBUTED,
            "no_fdinfo": dict(QUIET, drm_fds_found=12, drm_fdinfo_read=0),
            "no_fields": dict(QUIET, drm_fds_found=12, drm_fdinfo_read=12),
            "race": dict(FULLY_ATTRIBUTED, fd_race_pids=1),
            "denied": dict(FULLY_ATTRIBUTED, fd_universe_blocked_pids=1),
            "mixed": dict(QUIET, drm_fds_found=12, drm_fdinfo_read=12, drm_client_id_seen=10,
                          drm_pdev_seen=12, drm_pasid_seen=12),
        }
        for name, coverage in cases.items():
            verdicts[name] = row(**coverage)["EVIDENCE"]
        self.assertEqual(len(set(verdicts.values())), len(verdicts), verdicts)


class PasidHandlingTests(unittest.TestCase):
    """PASID absence is reported, never converted into success."""

    def test_pasid_absent_alone_downgrades_to_partial(self):
        state, reason = score(
            **dict(QUIET, drm_fds_found=4, drm_fdinfo_read=4,
                   drm_client_id_seen=4, drm_pdev_seen=4, drm_pasid_seen=0)
        )
        self.assertEqual(state, "PARTIAL")
        self.assertIn("pasid absent on 4/4", reason)

    def test_pasid_present_on_some_but_not_all_is_partial(self):
        state, reason = score(
            **dict(QUIET, drm_fds_found=4, drm_fdinfo_read=4,
                   drm_client_id_seen=4, drm_pdev_seen=4, drm_pasid_seen=3)
        )
        self.assertEqual(state, "PARTIAL")
        self.assertIn("pasid absent on 1/4", reason)

    def test_a_missing_pdev_is_also_reported(self):
        state, reason = score(
            **dict(QUIET, drm_fds_found=2, drm_fdinfo_read=2,
                   drm_client_id_seen=2, drm_pdev_seen=0, drm_pasid_seen=2)
        )
        self.assertEqual(state, "PARTIAL")
        self.assertIn("drm-pdev absent on 2/2", reason)


class UnobservableCasesTests(unittest.TestCase):
    """Lack of observability must not be promoted to PASS."""

    def test_permission_error_with_no_clients_is_unknown_not_pass(self):
        state, reason = score(**dict(QUIET, fd_universe_blocked_pids=3))
        self.assertEqual(state, "UNKNOWN")
        self.assertIn("universe not enumerable", reason)

    def test_unproven_gpu_identity_is_not_evaluated(self):
        state, _ = COLLECTOR.drm_fd_enumeration_state(QUIET, gpu_proven=False)
        self.assertEqual(state, "NOT_EVALUATED")

    def test_absent_attribution_keys_do_not_crash_and_do_not_pass(self):
        """A coverage dict without the attribution block must still be readable.

        total_pids is a contract key and is read strictly (DEFECT-04), so it
        must be present.  The seven attribution facts are additive and read with
        .get(), so their absence must not raise and must not fake a finding.
        """
        state, reason = COLLECTOR.drm_fd_enumeration_state(
            {"total_pids": 283}, gpu_proven=True
        )
        self.assertEqual(state, "PASS")
        self.assertIn("0 DRM fds found", reason)
        self.assertIn("across 283 PIDs", reason)

    def test_a_missing_total_pids_is_a_loud_failure(self):
        """The DEFECT-04 property survives this change."""
        with self.assertRaises(KeyError):
            COLLECTOR.drm_fd_enumeration_state({}, gpu_proven=True)

    def test_unknown_stays_unknown(self):
        state, _ = score(**dict(QUIET, fd_universe_blocked_pids=1))
        self.assertEqual(state, "UNKNOWN")


class RowIntegrationTests(unittest.TestCase):
    """The real matrix must expose this, not only the helper."""

    def test_the_row_reports_the_reason(self):
        result = row(**dict(QUIET, drm_fds_found=3, drm_fdinfo_read=3,
                            drm_client_id_seen=3, drm_pdev_seen=3, drm_pasid_seen=3))
        self.assertEqual(result["STATE"], "PASS")
        self.assertIn("3 DRM fd(s) all attributed", result["EVIDENCE"])

    def test_the_row_keeps_its_route_and_source(self):
        result = row(**QUIET)
        self.assertEqual(result["ROUTE"], "R1")
        self.assertEqual(result["SOURCE"], "/proc/<pid>/fdinfo")

    def test_the_criterion_row_and_its_description_are_unchanged(self):
        rows = dict(COLLECTOR.OWNERSHIP_CRITERION_ROWS)
        self.assertEqual(len(COLLECTOR.OWNERSHIP_CRITERION_ROWS), 11)
        self.assertEqual(
            rows["drm_fds_enumerated"],
            "DRM file descriptors enumerated with drm-client-id/pasid",
        )

    def test_clients_pasid_attributable_was_not_touched(self):
        """This fix must not leak into the neighbouring row."""
        result = COLLECTOR.ownership_matrix(context(dict(base_coverage(), **QUIET)))
        neighbour = next(
            c for c in result["conditions"] if c["condition"] == "clients_pasid_attributable"
        )
        self.assertEqual(neighbour["STATE"], "PASS")
        self.assertIn("MINOR_DERIVED_AND_DRIVER_CONFIRMED", neighbour["EVIDENCE"])

    def test_the_row_count_is_unchanged(self):
        result = COLLECTOR.ownership_matrix(context(dict(base_coverage(), **QUIET)))
        self.assertEqual(len(result["conditions"]), 11)


class ExportTests(unittest.TestCase):
    """The matrix can only score this if root_coverage carries the facts."""

    REQUIRED = (
        "drm_fds_found",
        "drm_fdinfo_read",
        "drm_client_id_seen",
        "drm_pdev_seen",
        "drm_pasid_seen",
        "fd_universe_blocked_pids",
        "fd_race_pids",
        # The only discharge for a vanished PID whose client set is unknown.
        # drm_fd_enumeration_state reads it with .get(), so a missing export
        # would not raise: it would silently read 0 and turn every unproven
        # disappearance into a PASS.  It belongs in this set for that reason.
        "fd_absence_proven_pids",
    )

    def test_the_accumulator_defines_every_key(self):
        source = open(COLLECTOR_PATH, encoding="utf-8").read()
        init = source.split("coverage = {", 1)[1].split("\n    }", 1)[0]
        for key in self.REQUIRED:
            self.assertIn('"%s"' % key, init)

    def test_root_coverage_exports_every_key(self):
        source = open(COLLECTOR_PATH, encoding="utf-8").read()
        export = source.split("root_coverage = {", 1)[1].split("\n    }", 1)[0]
        for key in self.REQUIRED:
            self.assertIn('"%s"' % key, export)

    def test_scan_fds_reports_attribution_for_each_matched_client(self):
        import tempfile
        from pathlib import Path

        with tempfile.TemporaryDirectory() as raw:
            fd_dir = Path(raw) / "1923" / "fd"
            fd_dir.mkdir(parents=True)
            os.symlink(CARD, fd_dir / "13")
            info = Path(raw) / "1923" / "fdinfo"
            info.mkdir()
            (info / "13").write_text(
                "drm-client-id:\t71\ndrm-pdev:\t0000:01:00.0\npasid:\t43\n"
            )
            result = COLLECTOR.scan_fds(1923, {CARD}, proc_root=Path(raw))
        self.assertEqual(
            result["attribution"],
            {"drm_fds_found": 1, "fdinfo_read": 1, "drm_client_id": 1,
             "drm_pdev": 1, "pasid": 1},
        )

    def test_scan_fds_counts_a_found_but_unreadable_client(self):
        import tempfile
        from pathlib import Path

        with tempfile.TemporaryDirectory() as raw:
            fd_dir = Path(raw) / "1923" / "fd"
            fd_dir.mkdir(parents=True)
            os.symlink(CARD, fd_dir / "13")
            result = COLLECTOR.scan_fds(1923, {CARD}, proc_root=Path(raw))
        self.assertEqual(result["attribution"]["drm_fds_found"], 1)
        self.assertEqual(result["attribution"]["fdinfo_read"], 0)

    def test_a_non_client_file_contributes_no_attribution(self):
        import tempfile
        from pathlib import Path

        with tempfile.TemporaryDirectory() as raw:
            fd_dir = Path(raw) / "9" / "fd"
            fd_dir.mkdir(parents=True)
            os.symlink("/etc/passwd", fd_dir / "3")
            result = COLLECTOR.scan_fds(9, {CARD}, proc_root=Path(raw))
        self.assertEqual(result["attribution"]["drm_fds_found"], 0)


DEVICES = {CARD, RENDER}

# Minimal stand-ins for the two /proc readers observe() consumes, so the test
# never touches a host process.
META = {
    "uid": 1000, "ppid": 1, "state": "S", "comm": "probe",
    "cmdline": "probe", "exe": "/usr/bin/probe", "wchan": "-",
    "cgroup": "/", "namespaces": {"mnt": "m", "pid": "p", "user": "u", "net": "n",
                                  "cgroup": "c", "uts": "0", "ipc": "i"},
}
MAPS = {"MAPS_READABLE": True, "MAPS_PERMISSION_DENIED": False,
        "MAPS_STATUS": "READABLE"}

# The locals observe() closes over inside main().  The NONLOCAL counters are
# declared separately by the harness because observe() assigns to them.
CLOSURE_NAMES = (
    "devices", "keywords", "gpu_clients", "storage_clients", "storage_devices",
    "compositor_relations", "root_fd_errors", "pid_records", "coverage",
)
NONLOCAL_NAMES = (
    "root_fd_error_count", "root_fd_permission_denied", "root_fd_disappeared",
    "root_fd_other_errors", "root_process_error_count",
)


def _extract_observe():
    """The verbatim source text of observe() as it stands inside main()."""
    import ast

    source = open(COLLECTOR_PATH, encoding="utf-8").read()
    tree = ast.parse(source)
    main_fn = next(
        n for n in tree.body
        if isinstance(n, ast.FunctionDef) and n.name == "main"
    )
    node = next(
        n for n in ast.walk(main_fn)
        if isinstance(n, ast.FunctionDef) and n.name == "observe"
    )
    return source, node, ast.get_source_segment(source, node)


def _build_observe(closure, doubles=None):
    """Compile the real observe() and bind the locals it closes over.

    observe() is a closure inside main(), and main() must not be run here: it
    reads /proc, runs lsof/fuser/ps and touches storage.  Its source text is
    taken verbatim from the module AST and compiled inside a synthetic
    enclosing function supplying exactly the names it needs, so what executes
    is the shipped code rather than a transcription of it.

    ``doubles`` replaces the /proc readers in the compiled function's own
    globals.  Patching the collector module would not reach them: the extracted
    function's ``__globals__`` is this namespace, not the module.
    """
    _source, _node, raw_body = _extract_observe()
    # get_source_segment dedents the ``def`` line but keeps the body at its
    # original depth, so the whole block is re-indented as one unit.
    body = "\n".join(
        ("    " + line) if line.strip() else line
        for line in raw_body.splitlines()
    )
    harness = "def __harness__(_c):\n"
    for name in NONLOCAL_NAMES:
        harness += "    %s = 0\n" % name
    for name in CLOSURE_NAMES:
        harness += "    %s = _c[%r]\n" % (name, name)
    harness += body + "\n    return observe\n"
    namespace = dict(vars(COLLECTOR))
    namespace.update(doubles or {})
    exec(compile(harness, "<observe-extracted>", "exec"), namespace)
    return namespace["__harness__"](closure)


def _real_accumulator():
    """The accumulator literal main() builds, with its own default values."""
    import ast

    source = open(COLLECTOR_PATH, encoding="utf-8").read()
    tree = ast.parse(source)
    main_fn = next(
        n for n in tree.body
        if isinstance(n, ast.FunctionDef) and n.name == "main"
    )
    assign = next(
        n for n in ast.walk(main_fn)
        if isinstance(n, ast.Assign)
        and any(getattr(t, "id", None) == "coverage" for t in n.targets)
        and isinstance(n.value, ast.Dict)
    )
    return {
        k.value: ast.literal_eval(v)
        for k, v in zip(assign.value.keys, assign.value.values)
    }


def _accumulate(pid, scan, proc_root, liveness=None):
    """Run the real observe() over one synthetic scan; return (coverage, item)."""
    coverage = _real_accumulator()
    closure = {
        "devices": DEVICES,
        "keywords": COLLECTOR.KEYWORDS,
        "gpu_clients": [],
        "storage_clients": [],
        "storage_devices": set(),
        "compositor_relations": {},
        "root_fd_errors": [],
        "pid_records": {},
        "coverage": coverage,
    }
    doubles = {
        "scan_fds": lambda *a, **k: scan,
        "proc_meta": lambda *a, **k: META,
        "scan_maps": lambda *a, **k: MAPS,
    }
    if liveness is not None:
        doubles["pid_gone"] = lambda *a, **k: liveness
    observe = _build_observe(closure, doubles)
    return coverage, observe(pid, proc_root=proc_root)


def _vanished_before_listdir(raw):
    with mock.patch.object(os, "listdir", side_effect=FileNotFoundError(2, "gone")):
        return COLLECTOR.scan_fds(1923, DEVICES, proc_root=Path(raw))


def _vanished_mid_table(raw):
    fd_dir = Path(raw) / "1923" / "fd"
    fd_dir.mkdir(parents=True)
    os.symlink(CARD, fd_dir / "13")
    os.symlink("/etc/passwd", fd_dir / "3")
    real = os.readlink

    def flaky(path, *a, **k):
        if str(path).endswith("/13"):
            raise FileNotFoundError(2, "No such file or directory")
        return real(path, *a, **k)

    with mock.patch.object(os, "readlink", side_effect=flaky):
        return COLLECTOR.scan_fds(1923, DEVICES, proc_root=Path(raw))


def _vanished_after_proven_drm_fd(raw):
    fd_dir = Path(raw) / "1923" / "fd"
    fd_dir.mkdir(parents=True)
    os.symlink(CARD, fd_dir / "13")
    info = Path(raw) / "1923" / "fdinfo"
    info.mkdir()
    (info / "13").write_text("drm-driver:\tamdgpu\n")
    real_open = Path.open

    def flaky_open(self, *a, **k):
        if "/fdinfo/" in str(self):
            raise FileNotFoundError(2, "No such file or directory")
        return real_open(self, *a, **k)

    with mock.patch.object(Path, "open", new=flaky_open):
        return COLLECTOR.scan_fds(1923, DEVICES, proc_root=Path(raw))


def _clean_table_no_device(raw):
    fd_dir = Path(raw) / "1923" / "fd"
    fd_dir.mkdir(parents=True)
    os.symlink("/etc/passwd", fd_dir / "3")
    return COLLECTOR.scan_fds(1923, DEVICES, proc_root=Path(raw))


GONE = {"state": "GONE", "reason": "PROCESS_DISAPPEARED", "error": None}
ALIVE = {"state": "ALIVE", "reason": "OBSERVED", "error": None}
UNREADABLE = {"state": "UNKNOWN", "reason": "PERMISSION_DENIED",
              "error": "PermissionError: [Errno 13] Permission denied"}


class ObserveExecutionTests(unittest.TestCase):
    """The real observe() runs, so the RACE / COVERAGE_LOSS split is exercised.

    Before the fix a vanished PID was counted only in fd_race_pids and never in
    fd_universe_blocked_pids, which is what let it certify the empty universe.
    These cases pin the corrected split at the point where it is decided.
    """

    def test_the_exercised_text_is_the_shipped_observe(self):
        """Guard: the harness must keep tracking the real source."""
        _source, _node, body = _extract_observe()
        self.assertIn("pid_gone(pid, proc_root)", body)
        self.assertIn("fd_absence_proven_pids", body)
        self.assertIn("unresolved_target_count", body)

    def test_B_vanished_before_its_table_was_listed_is_lost_coverage(self):
        """Case B: disappearance with no evidence whatsoever about the resource."""
        with tempfile.TemporaryDirectory() as raw:
            scan = _vanished_before_listdir(raw)
            self.assertEqual(scan["status_reason"], "PROCESS_DISAPPEARED")
            coverage, _item = _accumulate(1923, scan, Path(raw))
        self.assertEqual(coverage["fd_race_pids"], 1, "the disappearance is still counted")
        self.assertEqual(
            coverage["fd_universe_blocked_pids"], 1,
            "its client set is unknown, so it is lost coverage as well",
        )
        self.assertEqual(coverage["fd_absence_proven_pids"], 0)

    def test_E_an_unreadable_target_is_lost_coverage_not_a_benign_race(self):
        """Case E: the table listed, one FD's target could not be resolved."""
        with tempfile.TemporaryDirectory() as raw:
            scan = _vanished_mid_table(raw)
            self.assertEqual(scan["status"], "OK", "the table itself was read")
            self.assertEqual(scan["unresolved_target_count"], 1)
            coverage, _item = _accumulate(1923, scan, Path(raw))
        self.assertEqual(
            coverage["fd_universe_blocked_pids"], 1,
            "a listed FD whose target is unknown may have been the DRM node",
        )
        self.assertEqual(coverage["fd_absence_proven_pids"], 0)

    def test_C_a_proven_drm_holder_that_vanishes_is_not_lost_coverage(self):
        """Case C: the DRM fd was matched, so only its characterisation is open."""
        with tempfile.TemporaryDirectory() as raw:
            scan = _vanished_after_proven_drm_fd(raw)
            coverage, _item = _accumulate(1923, scan, Path(raw))
        self.assertEqual(coverage["drm_fds_found"], 1, "the resource is proven")
        self.assertEqual(coverage["fd_race_pids"], 1)
        self.assertEqual(
            coverage["fd_universe_blocked_pids"], 0,
            "the node was matched, so the universe was not lost here",
        )
        state, reason = COLLECTOR.drm_fd_enumeration_state(coverage, gpu_proven=True)
        self.assertEqual(state, "PARTIAL")
        self.assertNotIn("benign", reason)

    def test_A_absence_is_proven_only_after_a_clean_scan_and_an_observed_going(self):
        """Case A: every target resolved, no device matched, PID then observed gone."""
        with tempfile.TemporaryDirectory() as raw:
            scan = _clean_table_no_device(raw)
            self.assertEqual(scan["errors"], [])
            coverage, item = _accumulate(1923, scan, Path(raw), liveness=GONE)
        self.assertEqual(coverage["fd_absence_proven_pids"], 1)
        self.assertEqual(coverage["fd_race_pids"], 1)
        self.assertEqual(coverage["fd_universe_blocked_pids"], 0)
        self.assertEqual(item["liveness_recheck"]["state"], "GONE")
        state, reason = COLLECTOR.drm_fd_enumeration_state(coverage, gpu_proven=True)
        self.assertEqual(state, "PASS")
        self.assertIn("absence of a DRM resource proven", reason)

    def test_a_live_pid_is_never_an_absence_proof(self):
        """A clean scan of a still-running PID proves nothing about absence."""
        with tempfile.TemporaryDirectory() as raw:
            scan = _clean_table_no_device(raw)
            coverage, _item = _accumulate(1923, scan, Path(raw), liveness=ALIVE)
        self.assertEqual(coverage["fd_absence_proven_pids"], 0)
        self.assertEqual(coverage["fd_race_pids"], 0)
        self.assertEqual(coverage["fd_universe_blocked_pids"], 0)

    def test_an_unreadable_liveness_recheck_is_lost_coverage_never_absence(self):
        """A swallowed stat failure must not be read as a vanished PID."""
        with tempfile.TemporaryDirectory() as raw:
            scan = _clean_table_no_device(raw)
            coverage, item = _accumulate(1923, scan, Path(raw), liveness=UNREADABLE)
        self.assertEqual(coverage["fd_absence_proven_pids"], 0)
        self.assertEqual(coverage["fd_universe_blocked_pids"], 1)
        self.assertIn("PermissionError", item["liveness_recheck"]["error"])

    def test_a_dirty_scan_is_never_eligible_for_an_absence_proof(self):
        """One unresolved target is enough to disqualify the whole PID."""
        with tempfile.TemporaryDirectory() as raw:
            scan = _vanished_mid_table(raw)
            coverage, _item = _accumulate(1923, scan, Path(raw), liveness=GONE)
        self.assertEqual(coverage["fd_absence_proven_pids"], 0)


class LivenessRecheckTests(unittest.TestCase):
    """pid_gone() itself: tri-state, and UNKNOWN is never collapsed into GONE."""

    def test_gone_alive_and_unreadable_are_three_distinct_outcomes(self):
        with tempfile.TemporaryDirectory() as raw:
            self.assertEqual(COLLECTOR.pid_gone(999999, Path(raw))["state"], "GONE")
            Path(raw, "7").mkdir()
            self.assertEqual(COLLECTOR.pid_gone(7, Path(raw))["state"], "ALIVE")
            with mock.patch.object(os, "stat", side_effect=PermissionError(13, "denied")):
                got = COLLECTOR.pid_gone(7, Path(raw))
        self.assertEqual(got["state"], "UNKNOWN")
        self.assertIsNotNone(got["error"], "the failure must be surfaced, not swallowed")
        self.assertEqual(got["reason"], "PERMISSION_DENIED")


class VanishedAbsenceContractTests(unittest.TestCase):
    """A, B and E must be distinguishable, and B/E must never read PASS."""

    def test_B_cannot_produce_a_pass_of_undemonstrated_absence(self):
        state, reason = score(fd_race_pids=1, fd_absence_proven_pids=0)
        self.assertEqual(state, "UNKNOWN")
        self.assertIn("absence NOT proven", reason)

    def test_E_cannot_produce_a_pass_of_undemonstrated_absence(self):
        """E reaches the same verdict through lost coverage, not through races."""
        state, reason = score(fd_race_pids=1, fd_universe_blocked_pids=1)
        self.assertEqual(state, "UNKNOWN")
        self.assertIn("universe not enumerable", reason)

    def test_A_and_B_differ_once_the_evidence_actually_differs(self):
        proven = dict(QUIET, fd_race_pids=1, fd_absence_proven_pids=1)
        unproven = dict(QUIET, fd_race_pids=1, fd_absence_proven_pids=0)
        self.assertNotEqual(proven, unproven)
        a_state, a_reason = score(**proven)
        b_state, b_reason = score(**unproven)
        self.assertNotEqual((a_state, a_reason), (b_state, b_reason))
        self.assertEqual((a_state, b_state), ("PASS", "UNKNOWN"))

    def test_no_absence_is_claimed_when_no_pid_vanished(self):
        state, reason = score(**QUIET)
        self.assertEqual(state, "PASS")
        self.assertNotIn("absence", reason)
        self.assertNotIn("vanished", reason)

    def test_the_row_never_calls_a_vanished_pid_a_benign_race(self):
        for coverage in (
            dict(QUIET, fd_race_pids=1),
            dict(QUIET, fd_race_pids=1, fd_absence_proven_pids=1),
            dict(FULLY_ATTRIBUTED, fd_race_pids=1),
            dict(QUIET, drm_fds_found=1, drm_fdinfo_read=0, fd_race_pids=1),
        ):
            with self.subTest(coverage=sorted(coverage.items())):
                _state, reason = score(**coverage)
                self.assertNotIn("benign", reason)


if __name__ == "__main__":
    unittest.main(verbosity=2)
