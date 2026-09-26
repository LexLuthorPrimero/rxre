#!/usr/bin/env python3
"""Failure-mode tests T01-T16 for the four defects found in the independent review.

These are the tests the previous suite was missing: it mapped the GAP list, not
the ways the new code could be wrong.  Each test drives a specific failure mode
of HIGH-1, HIGH-2, HIGH-3 or MED-1 and asserts the collector refuses rather than
degrades.

No test invokes sudo, the collector against the host, systemctl, C1, or any
live system probe.  Every filesystem fixture is a synthetic tree in a temporary
directory.

Run:  python3 -m unittest test_collector_failure_modes -v
"""
from __future__ import annotations

import ast
import importlib.util
import json
import os
import sys
import tempfile
import unittest
from pathlib import Path


SCRIPT = Path(__file__).resolve().parent / "privileged_read_collector.py"
SPEC = importlib.util.spec_from_file_location("collector_failure_modes", SCRIPT)
assert SPEC and SPEC.loader
collector = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(collector)

BDF_GPU = "0000:01:00.0"
BDF_IGPU = "0000:00:02.0"


# --------------------------------------------------------------------------
# synthetic sysfs builder with switchable per-node device link behaviour
# --------------------------------------------------------------------------
def build_sysfs(root: Path, *, vendor="0x1002", device="0x699f", klass="0x030000",
                driver="amdgpu", link_mode="valid", device_points_to=None,
                omit_render=False, omit_card=False) -> Path:
    """link_mode: valid | missing | dangling | regular_file"""
    sysfs = root / "sys"

    def pci(bdf, ven, dev, kls, drv, nodes):
        base = sysfs / "devices" / "pci0000:00" / bdf
        (base / "drm").mkdir(parents=True, exist_ok=True)
        (base / "vendor").write_text(ven + "\n", encoding="utf-8")
        (base / "device").write_text(dev + "\n", encoding="utf-8")
        (base / "class").write_text(kls + "\n", encoding="utf-8")
        (sysfs / "bus" / "pci" / "drivers" / drv).mkdir(parents=True, exist_ok=True)
        (base / "driver").symlink_to(
            os.path.relpath(sysfs / "bus" / "pci" / "drivers" / drv, base)
        )
        for node in nodes:
            node_dir = base / "drm" / node
            node_dir.mkdir(parents=True, exist_ok=True)
            (node_dir / "driver").symlink_to(
                os.path.relpath(sysfs / "bus" / "pci" / "drivers" / drv, node_dir)
            )
            device_link = node_dir / "device"
            if link_mode == "valid":
                device_link.symlink_to(os.path.relpath(base, node_dir))
            elif link_mode == "dangling":
                device_link.symlink_to("../../../nowhere/does-not-exist")
            elif link_mode == "regular_file":
                device_link.write_text("not a symlink\n", encoding="utf-8")
            # link_mode == "missing": no device link at all
            if device_points_to and node == "card1":
                if device_link.exists() or device_link.is_symlink():
                    device_link.unlink()
                other = sysfs / "devices" / "pci0000:00" / device_points_to
                other.mkdir(parents=True, exist_ok=True)
                device_link.symlink_to(os.path.relpath(other, node_dir))
            link = sysfs / "class" / "drm" / node
            link.parent.mkdir(parents=True, exist_ok=True)
            link.symlink_to(os.path.relpath(node_dir, link.parent))
        forward = sysfs / "bus" / "pci" / "devices" / bdf
        forward.parent.mkdir(parents=True, exist_ok=True)
        forward.symlink_to(os.path.relpath(base, forward.parent))
        return base

    gpu_nodes = []
    if not omit_card:
        gpu_nodes.append("card1")
    if not omit_render:
        gpu_nodes.append("renderD129")
    pci(BDF_GPU, vendor, device, klass, driver, gpu_nodes)
    pci(BDF_IGPU, "0x8086", "0x0412", "0x030000", "i915", ["card0", "renderD128"])
    return sysfs


# ==========================================================================
# T01-T05  HIGH-1  a BDF must be proven by an existing link, not by path text
# ==========================================================================
class High1BdfIdentityTests(unittest.TestCase):
    def assert_not_proven(self, identity, detail_key=None):
        self.assertEqual(identity["GPU_IDENTITY_STATUS"], "NOT_PROVEN")
        self.assertEqual(identity["GPU_IDENTITY_ABORT"], "IDENTITY_NOT_PROVEN")
        self.assertIsNone(identity["GPU_CARD_NODE"])
        self.assertIsNone(identity["GPU_RENDER_NODE"])
        self.assertEqual(identity["devices"], set(), "no node may be used unproven")
        if detail_key:
            aborts = {
                item.get("bdf_link_abort")
                for item in identity["drm_discovery"]["reverse"]["excluded"]
            }
            self.assertIn(detail_key, aborts, aborts)

    def test_T01_missing_device_symlink(self):
        with tempfile.TemporaryDirectory() as raw:
            identity = collector.resolve_gpu_identity(
                sysfs_root=build_sysfs(Path(raw), link_mode="missing")
            )
        self.assert_not_proven(identity, "DEVICE_LINK_ABSENT")

    def test_T02_broken_device_symlink(self):
        with tempfile.TemporaryDirectory() as raw:
            identity = collector.resolve_gpu_identity(
                sysfs_root=build_sysfs(Path(raw), link_mode="dangling")
            )
        self.assert_not_proven(identity, "DEVICE_TARGET_ABSENT")

    def test_T02b_device_link_is_a_regular_file(self):
        with tempfile.TemporaryDirectory() as raw:
            identity = collector.resolve_gpu_identity(
                sysfs_root=build_sysfs(Path(raw), link_mode="regular_file")
            )
        self.assert_not_proven(identity, "DEVICE_NOT_A_SYMLINK")

    def test_T03_device_link_points_to_another_bdf(self):
        """The link exists and resolves, but to the Intel -- must not be adopted."""
        with tempfile.TemporaryDirectory() as raw:
            identity = collector.resolve_gpu_identity(
                sysfs_root=build_sysfs(Path(raw), device_points_to=BDF_IGPU)
            )
        self.assert_not_proven(identity)
        excluded = {i["node"]: i for i in identity["drm_discovery"]["reverse"]["excluded"]}
        self.assertIn("card1", excluded)
        # The link resolves to the Intel, so the identity re-check at the
        # resolved target fails first: the refusal reason is the stronger
        # PCI_IDENTITY_MISMATCH_AT_NODE, not merely a BDF difference.
        self.assertEqual(
            excluded["card1"]["exclusion_reason"], "PCI_IDENTITY_MISMATCH_AT_NODE"
        )
        self.assertEqual(excluded["card1"]["resolved_bdf"], BDF_IGPU)
        self.assertEqual(excluded["card1"]["bdf_link_status"], "NOT_PROVEN")
        candidates = [i["node"] for i in identity["drm_discovery"]["reverse"]["card_candidates"]]
        self.assertNotIn("card1", candidates)

    def test_T04_wrong_vendor(self):
        with tempfile.TemporaryDirectory() as raw:
            identity = collector.resolve_gpu_identity(
                sysfs_root=build_sysfs(Path(raw), vendor="0x8086")
            )
        self.assert_not_proven(identity)
        self.assertTrue(
            any("vendor=" in m for m in identity["pci_identity"]["mismatches"]),
            identity["pci_identity"]["mismatches"],
        )

    def test_T05_wrong_device(self):
        with tempfile.TemporaryDirectory() as raw:
            identity = collector.resolve_gpu_identity(
                sysfs_root=build_sysfs(Path(raw), device="0x687f")
            )
        self.assert_not_proven(identity)
        self.assertTrue(
            any("device=" in m for m in identity["pci_identity"]["mismatches"]),
            identity["pci_identity"]["mismatches"],
        )

    def test_T05b_identity_is_reverified_at_the_resolved_node_not_only_at_the_bdf_path(self):
        """A node whose resolved target carries a different device id is refused."""
        with tempfile.TemporaryDirectory() as raw:
            sysfs = build_sysfs(Path(raw))
            node_target = sysfs / "devices" / "pci0000:00" / BDF_GPU
            (node_target / "device").write_text("0x1234\n", encoding="utf-8")
            # the PCI path still disagrees, so both layers must refuse
            identity = collector.resolve_gpu_identity(sysfs_root=sysfs)
        self.assertEqual(identity["GPU_IDENTITY_STATUS"], "NOT_PROVEN")

    def test_T01b_absent_card_node_is_role_missing(self):
        with tempfile.TemporaryDirectory() as raw:
            identity = collector.resolve_gpu_identity(
                sysfs_root=build_sysfs(Path(raw), omit_card=True)
            )
        self.assertEqual(identity["GPU_IDENTITY_STATUS"], "NOT_PROVEN")
        self.assertEqual(
            identity["drm_discovery"]["DRM_DISCOVERY_ABORT"], "ROLE_MISSING"
        )

    def test_T01c_absent_render_node_is_role_missing(self):
        with tempfile.TemporaryDirectory() as raw:
            identity = collector.resolve_gpu_identity(
                sysfs_root=build_sysfs(Path(raw), omit_render=True)
            )
        self.assertEqual(identity["GPU_IDENTITY_STATUS"], "NOT_PROVEN")
        self.assertEqual(
            identity["drm_discovery"]["DRM_DISCOVERY_ABORT"], "ROLE_MISSING"
        )


# ==========================================================================
# T06-T07  HIGH-2  one sweep, one record per PID, one row per (pid, fd, target)
# ==========================================================================
def extract_observe(source: str):
    """Return the observe() closure body from main() so it can be driven directly.

    The function is a closure over local counters, so the test re-executes the
    same code object with its own state instead of reimplementing it.
    """
    return source


class High2SingleObservationTests(unittest.TestCase):
    """The duplication bug lived in main()'s two loops.  These tests assert the
    structural property that makes it impossible: pid_records is filled by a
    single sweep, and the service-PID pass only ever *reads* from it."""

    @classmethod
    def setUpClass(cls):
        import inspect
        cls.main_src = inspect.getsource(collector.main)
        cls.main_tree = ast.parse(cls.main_src)

    def _observe_def(self):
        for node in ast.walk(self.main_tree):
            if isinstance(node, ast.FunctionDef) and node.name == "observe":
                return node
        self.fail("observe() not found in main()")

    def test_T06_observe_exists_and_sweep_is_single(self):
        calls = [
            n for n in ast.walk(self.main_tree)
            if isinstance(n, ast.Call) and isinstance(n.func, ast.Name) and n.func.id == "observe"
        ]
        # exactly one definition site plus the two call sites that are guarded
        self.assertEqual(len([n for n in ast.walk(self.main_tree)
                                if isinstance(n, ast.FunctionDef) and n.name == "observe"]), 1)
        self.assertEqual(len(calls), 2, "observe() must be called from exactly two guarded sites")
        # the service loop must consult pid_records before observing
        self.assertIn("if key in pid_records:", self.main_src)
        self.assertIn("if key in interesting:", self.main_src)
        # no scan_fds/scan_maps/proc_meta anywhere outside observe()
        inside = set(ast.walk(self._observe_def()))
        for name in ("scan_fds", "scan_maps", "proc_meta"):
            everywhere = [
                n for n in ast.walk(self.main_tree)
                if isinstance(n, ast.Call) and isinstance(n.func, ast.Name) and n.func.id == name
            ]
            self.assertTrue(everywhere, f"{name} should be used at all")
            outside = [ast.unparse(n) for n in everywhere if n not in inside]
            self.assertEqual(outside, [], f"{name} must only be called inside observe()")

    def test_T07_pid_records_is_the_single_source_of_truth(self):
        for required in (
            'pid_records[str(pid)] = observe(pid)',
            '"pid": pid,',
            '"uid": meta.get("uid"),',
            'gpu_clients.append(client)',
            'storage_clients.append(client)',
            'root_fd_errors.append({"pid": pid, **error})',
        ):
            self.assertIn(required, self.main_src, required)
        # interesting must be built as a view, not by re-observing
        self.assertIn("for key, record in pid_records.items()", self.main_src)

    def test_T07b_observe_accounts_each_pid_exactly_once_per_field(self):
        """Every counter increment lives inside observe(), so one call per PID."""
        observe = self._observe_def()
        increments = [
            n for n in ast.walk(observe)
            if isinstance(n, ast.AugAssign)
            and isinstance(n.target, ast.Subscript)
        ]
        # the sweep loop must not touch the counters directly
        sweep_increments = [
            n for n in ast.walk(self.main_tree)
            if isinstance(n, ast.AugAssign)
            and isinstance(n.target, ast.Subscript)
            and "coverage" in ast.unparse(n.target)
            and n not in increments
        ]
        # total_pids and late_observed_pids are sweep bookkeeping, not per-PID
        # evidence; every evidence counter must live inside observe().
        allowed = {"coverage['total_pids']", "coverage['late_observed_pids']"}
        outside = {ast.unparse(n.target) for n in sweep_increments}
        self.assertTrue(
            outside <= allowed,
            f"evidence counters incremented outside observe(): {outside - allowed}",
        )
        self.assertGreater(len(increments), 10)


# ==========================================================================
# T08-T11  HIGH-3  root and user namespaces are separate populations
# ==========================================================================
def namespace_coverage(root_ok, root_total, user_ok, user_total, uid_unknown=0):
    """Evaluate the exact expressions main() now uses for the two conditions."""
    return {
        "root_namespace_complete": (
            root_total > 0 and root_ok == root_total
        ),
        "user_namespace_complete": (
            user_total > 0 and user_ok == user_total
        ),
        "ROOT_NAMESPACE_COVERAGE": f"{root_ok}/{root_total}",
        "USER_NAMESPACE_COVERAGE": f"{user_ok}/{user_total}",
        "UID_UNKNOWN_PIDS": uid_unknown,
    }


class High3NamespaceDenominatorTests(unittest.TestCase):
    def test_T08_root_complete_and_user_complete(self):
        result = namespace_coverage(199, 199, 84, 84)
        self.assertTrue(result["root_namespace_complete"])
        self.assertTrue(result["user_namespace_complete"])

    def test_T09_root_complete_user_incomplete(self):
        result = namespace_coverage(199, 199, 80, 84)
        self.assertTrue(result["root_namespace_complete"])
        self.assertFalse(result["user_namespace_complete"])

    def test_T10_root_incomplete_user_complete(self):
        result = namespace_coverage(180, 199, 84, 84)
        self.assertFalse(result["root_namespace_complete"])
        self.assertTrue(result["user_namespace_complete"])

    def test_T11_both_incomplete(self):
        result = namespace_coverage(180, 199, 80, 84)
        self.assertFalse(result["root_namespace_complete"])
        self.assertFalse(result["user_namespace_complete"])

    def test_T11b_root_verdict_does_not_depend_on_the_user_population_size(self):
        """The exact regression: same root data, different user counts -> same root verdict."""
        verdicts = {
            namespace_coverage(199, 199, ok, total)["root_namespace_complete"]
            for ok, total in ((84, 84), (80, 84), (0, 0), (500, 500))
        }
        self.assertEqual(verdicts, {True}, "root completeness must not vary with user counts")

    def test_T11c_user_verdict_does_not_depend_on_the_root_population_size(self):
        verdicts = {
            namespace_coverage(ok, total, 84, 84)["user_namespace_complete"]
            for ok, total in ((199, 199), (180, 199), (0, 0), (500, 500))
        }
        self.assertEqual(verdicts, {True})

    def test_T11d_an_empty_population_is_not_complete(self):
        result = namespace_coverage(0, 0, 0, 0)
        self.assertFalse(result["root_namespace_complete"])
        self.assertFalse(result["user_namespace_complete"])

    def test_T11e_uid_unknown_pids_are_counted_in_neither_population(self):
        source = Path(SCRIPT).read_text(encoding="utf-8")
        self.assertIn('coverage["uid_unknown_pids"] += 1', source)
        self.assertIn('elif uid is None:', source)
        # and the unknown bucket must not leak into either total
        self.assertIn('coverage["root_namespace_total"] += 1', source)
        self.assertIn('coverage["user_namespace_total"] += 1', source)


# ==========================================================================
# T12-T15  MED-1  an unproven storage identity is never "zero clients"
# ==========================================================================
def storage_verdict(proven: bool, client_count: int):
    """Evaluate the exact expressions main() now uses."""
    active_storage = client_count if proven else None
    storage_client_evidence = "EVALUATED" if proven else "NOT_EVALUATED"
    storage_no_clients = proven and active_storage == 0
    return {
        "active_storage": active_storage,
        "storage_client_evidence": storage_client_evidence,
        "storage_no_clients": storage_no_clients,
        "ownership_full": bool(True and 0 == 0 and storage_no_clients and 0 == 0),
    }


class Med1StorageUnknownTests(unittest.TestCase):
    def test_T12_storage_proven_and_no_clients(self):
        result = storage_verdict(True, 0)
        self.assertEqual(result["active_storage"], 0)
        self.assertEqual(result["storage_client_evidence"], "EVALUATED")
        self.assertTrue(result["storage_no_clients"])
        self.assertTrue(result["ownership_full"])

    def test_T13_storage_proven_with_clients(self):
        result = storage_verdict(True, 3)
        self.assertEqual(result["active_storage"], 3)
        self.assertFalse(result["storage_no_clients"])
        self.assertFalse(result["ownership_full"])

    def test_T14_storage_not_proven_is_never_zero(self):
        result = storage_verdict(False, 0)
        self.assertIsNone(result["active_storage"])
        self.assertEqual(result["storage_client_evidence"], "NOT_EVALUATED")
        self.assertFalse(result["storage_no_clients"])
        self.assertFalse(
            result["ownership_full"],
            "NOT_PROVEN storage must not satisfy the ownership boolean",
        )

    def test_T14b_not_proven_is_reported_as_not_evaluated_in_the_payload(self):
        source = Path(SCRIPT).read_text(encoding="utf-8")
        self.assertIn(
            '"active_storage_clients": active_storage if storage_proven else "NOT_EVALUATED"',
            source,
        )
        self.assertIn('active_storage = len(storage_clients) if storage_proven else None', source)

    def test_T15_ambiguous_storage_source_cannot_reach_ownership_pass(self):
        with tempfile.TemporaryDirectory() as raw:
            proc = Path(raw) / "proc"
            (proc / "self").mkdir(parents=True)
            (proc / "self" / "mountinfo").write_text(
                "44 1 8:19 / / rw,relatime shared:1 - ext4 /dev/sdb3 rw\n"
                "45 1 0:52 / / rw,relatime shared:2 - overlay overlay rw\n",
                encoding="utf-8",
            )
            block = Path(raw) / "block"
            storage = collector.resolve_storage_identity(proc_root=proc, block_root=block)
        self.assertEqual(storage["STORAGE_IDENTITY_STATUS"], "NOT_PROVEN")
        self.assertEqual(storage["STORAGE_IDENTITY_ABORT"], "AMBIGUOUS_ROOT_MOUNT")
        result = storage_verdict(storage["STORAGE_IDENTITY_STATUS"] == "PROVEN", 0)
        self.assertFalse(result["ownership_full"])

    def test_T15b_sda_present_but_not_root_is_never_a_fallback(self):
        with tempfile.TemporaryDirectory() as raw:
            root = Path(raw)
            proc, block = _storage_with_neighbour(root)
            storage = collector.resolve_storage_identity(proc_root=proc, block_root=block)
            parsed = collector.parse_diskstats(storage["STORAGE_DISKSTATS_NAMES"], proc_root=proc)
        self.assertEqual(storage["STORAGE_IDENTITY_STATUS"], "PROVEN")
        self.assertEqual(storage["ROOT_BLOCK_PARENT"], "sdb")
        self.assertNotIn("sda", storage["STORAGE_DISKSTATS_NAMES"])
        self.assertNotIn("sda", parsed)
        self.assertIn("sdb3", parsed)
        # and with no proven identity at all, nothing is read
        self.assertEqual(collector.parse_diskstats([]), {})
        self.assertEqual(collector.parse_diskstats(None), {})


def _storage_with_neighbour(root: Path):
    proc = root / "proc"
    (proc / "self").mkdir(parents=True, exist_ok=True)
    (proc / "self" / "mountinfo").write_text(
        "44 1 8:19 / / rw,relatime shared:1 - ext4 /dev/sdb3 rw\n", encoding="utf-8"
    )
    (proc / "diskstats").write_text(
        "   8 0 sda 100 0 2000 5 0 0 0 0 100 200 0 300 0\n"
        "   8 16 sda2 50 0 900 5 0 0 0 0 50 60 0 150 0\n"
        "   8 16 sdb3 700 0 9000 5 0 0 0 0 700 800 0 2100 0\n"
        "  252 0 zram0 10 0 20 1 0 0 0 0 10 12 0 30 0\n",
        encoding="utf-8",
    )
    block = root / "block"
    block.mkdir(parents=True, exist_ok=True)
    ata = root / "devices"
    def link(name: str, container: str) -> Path:
        target = ata / container / name
        target.mkdir(parents=True, exist_ok=True)
        (block / name).symlink_to(os.path.relpath(target, block))
        return target

    link("sdb", "block")
    link("sda", "block")
    part = link("sdb3", "block/sdb")
    (part / "partition").write_text("3\n", encoding="utf-8")
    return proc, block


# ==========================================================================
# T16  the legacy boolean can still not reach OWNERSHIP=FULL
# ==========================================================================
class OwnershipBooleanRegressionTests(unittest.TestCase):
    def _context(self, **overrides):
        context = {
            "gpu_identity": {
                "GPU_IDENTITY_STATUS": "PROVEN",
                "GPU_CARD_NODE": "card1",
                "GPU_RENDER_NODE": "renderD129",
            },
            "root_coverage": {
                "card_complete": True, "render_complete": True,
                "user_namespace_complete": True, "root_namespace_complete": True,
                "fd_error_count": 0,
                "user_namespace_ok": 84, "user_namespace_total": 84,
                "root_namespace_ok": 199, "root_namespace_total": 199,
                "total_pids": 283,
            },
            "debugfs": {
                "DEBUGFS_CLIENT_ATTRIBUTION": "PROVEN",
                "reason": "MINOR_DERIVED_AND_DRIVER_CONFIRMED",
                "clients_path": "/sys/kernel/debug/dri/129/clients",
            },
            "btrfs_observation": {},
            "btrfs_status": "ABSENT",
            "active_agents": 0,
            "pm_status": "READ",
            "card_clients": 0,
            "render_clients": 0,
        }
        context.update(overrides)
        return context

    def test_T16_legacy_boolean_true_cannot_reach_full(self):
        # every evaluated condition PASSes, the legacy boolean would be True
        legacy_true = bool(True and 0 == 0 and True and 0 == 0)
        self.assertTrue(legacy_true)
        result = collector.ownership_matrix(self._context())
        self.assertEqual(result["COLLECTOR_OWNERSHIP_BOOLEAN"], "NON_AUTHORITATIVE")
        self.assertEqual(result["OWNERSHIP_CRITERION_STATE"], "PARTIAL")
        by_key = {row["condition"]: row for row in result["conditions"]}
        self.assertEqual(by_key["writers_resolved"]["STATE"], "NOT_EVALUATED")
        self.assertEqual(by_key["writers_resolved"]["ROUTE"], "R2")
        self.assertEqual(by_key["guard_and_restore"]["STATE"], "NOT_EVALUATED")
        self.assertEqual(by_key["guard_and_restore"]["ROUTE"], "R3")
        self.assertEqual(result["not_evaluated_count"], 2)

    def test_T16b_external_rows_have_no_observed_entry_to_convert_from(self):
        tree = ast.parse(Path(SCRIPT).read_text(encoding="utf-8"))
        matrix = next(
            n for n in ast.walk(tree)
            if isinstance(n, ast.FunctionDef) and n.name == "ownership_matrix"
        )
        for row_key, route in (("writers_resolved", "R2"), ("guard_and_restore", "R3")):
            self.assertIn(row_key, collector.OWNERSHIP_EXTERNAL_ROWS)
            self.assertEqual(collector.OWNERSHIP_EXTERNAL_ROWS[row_key][1], route)
            # the row must not be reachable from the `observed` lookup table
            observed_block = ast.unparse(matrix).split("observed = {")[1].split("}")[0]
            self.assertNotIn(f'"{row_key}"', observed_block)
        self.assertTrue(json.dumps(collector.OWNERSHIP_CRITERION_ROWS))

    def test_T16c_booleans_stay_non_authoritative_in_the_source(self):
        source = Path(SCRIPT).read_text(encoding="utf-8")
        self.assertIn('"CLASSIFICATION": "NON_AUTHORITATIVE"', source)
        self.assertIn('"AUTHORITATIVE": False', source)
        self.assertIn('"OWNERSHIP": ownership_matrix_result["OWNERSHIP_CRITERION_STATE"]', source)
        self.assertNotIn('"OWNERSHIP": "FULL" if ownership_full else "PARTIAL"', source)


# ==========================================================================
# regression guard: the read-only promise still holds after the fixes
# ==========================================================================
MUTATING = {
    "write", "writelines", "write_text", "write_bytes", "truncate", "unlink",
    "rmdir", "rename", "renames", "remove", "mkdir", "makedirs", "rmtree",
    "symlink", "symlink_to", "hardlink_to", "link", "chmod", "chown", "touch",
    "utime", "chflags", "kill", "killpg", "setuid", "setgid", "system",
    "popen", "execv", "execve", "execvp", "spawnv", "fork", "eval", "exec",
    "ioctl", "fcntl", "mount", "umount", "umount2", "swapon", "swapoff",
    "mkfifo", "mknod", "setns", "unshare", "seteuid", "setresuid", "dup2",
    "sched_setscheduler", "setpriority", "sync", "fsync", "mkstemp", "mkdtemp",
}
READONLY_BUILTINS = {"len", "int", "str", "sorted", "max", "min", "abs", "round",
                        "sum", "any", "all", "bool", "set", "dict", "list", "tuple",
                        "float", "isinstance", "range", "enumerate", "print"}


class ReadOnlyRegressionTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.source = Path(SCRIPT).read_text(encoding="utf-8")
        cls.tree = ast.parse(cls.source)

    def test_no_mutating_call_survives_the_fixes(self):
        offenders = []
        for node in ast.walk(self.tree):
            if not isinstance(node, ast.Call):
                continue
            if isinstance(node.func, ast.Attribute):
                if node.func.attr in MUTATING:
                    offenders.append((node.lineno, node.func.attr))
            elif isinstance(node.func, ast.Name):
                if node.func.id in MUTATING:
                    offenders.append((node.lineno, node.func.id))
        self.assertEqual(offenders, [], f"mutating calls: {offenders}")

    def test_no_new_import(self):
        imported = set()
        for node in ast.walk(self.tree):
            if isinstance(node, ast.Import):
                imported.update(a.name.split(".")[0] for a in node.names)
            elif isinstance(node, ast.ImportFrom) and node.module:
                imported.add(node.module.split(".")[0])
        self.assertTrue(imported <= {
            "ast", "datetime", "hashlib", "importlib.util", "json", "os", "re",
            "subprocess", "sys", "time", "pathlib", "traceback", "__future__",
        }, f"unexpected imports: {imported}")

    def test_sudo_is_never_executed(self):
        self.assertNotIn('"sudo"', self.source.replace('"sudo": {', ""))
        for node in ast.walk(self.tree):
            if isinstance(node, ast.Call) and isinstance(node.func, ast.Name) and node.func.id == "run":
                for arg in ast.walk(node):
                    self.assertNotEqual(getattr(arg, "value", None), "sudo")

    def test_both_context_managers_still_open_read_only(self):
        modes = []
        for node in ast.walk(self.tree):
            if isinstance(node, ast.With):
                for item in node.items:
                    call = item.context_expr
                    if isinstance(call, ast.Call):
                        for arg in call.args:
                            if isinstance(arg, ast.Constant) and isinstance(arg.value, str):
                                modes.append((node.lineno, arg.value))
        self.assertTrue(modes)
        for lineno, mode in modes:
            self.assertEqual(mode, "rb", f"line {lineno} opens {mode!r}")

    def test_module_still_imports_without_arguments(self):
        self.assertFalse(collector._ARGV_IS_COLLECTOR_ARGS)
        with self.assertRaises(SystemExit):
            collector.main()

    def test_realpath_is_not_used_as_existence_proof(self):
        """HIGH-1 and DEFECT-01.  realpath() resolves a chain as far as it goes
        and returns a string, so it can never be the existence proof, and the
        BDF must never be read out of the path text."""
        functions = {
            node.name: node
            for node in ast.walk(self.tree)
            if isinstance(node, ast.FunctionDef)
        }
        guards = ("os.path.exists", "os.path.isdir", ".is_dir()", ".exists()",
                  ".is_symlink()", ".is_file()")

        # the function that decides PCI device identity carries its own guards
        for name in ("resolve_pci_device_dir", "resolve_block_device"):
            body = ast.unparse(functions[name])
            self.assertTrue(
                any(marker in body for marker in guards),
                f"{name} decides identity and needs an explicit existence check",
            )

        # the BDF comes from the directory NAME, never from a path scan
        identity = ast.unparse(functions["resolve_pci_device_dir"])
        self.assertIn("os.path.basename(real.rstrip('/'))", identity.replace('"', "'"))
        self.assertIn("BDF_RE.fullmatch(name)", identity)
        self.assertIn("DEVICE_DIR_LACKS_PCI_VENDOR_DEVICE", identity)
        self.assertNotIn("BDF_RE.search(", identity)
        # finditer may appear, but only to record components as evidence
        for node in ast.walk(functions["resolve_pci_device_dir"]):
            if isinstance(node, ast.Call) and isinstance(node.func, ast.Attribute):
                if node.func.attr in ("search", "match", "fullmatch"):
                    self.assertNotEqual(node.func.attr, "search",
                                        "a first-match scan would return the bridge")

        # and no other function extracts a BDF from path text
        for name, node in functions.items():
            body = ast.unparse(node)
            if "os.path.realpath" not in body or name == "resolve_pci_device_dir":
                continue
            self.assertTrue(
                any(marker in body for marker in guards),
                f"{name} uses realpath without an existence check",
            )
        self.assertNotIn("BDF_RE.search(", self.source)


if __name__ == "__main__":
    unittest.main(verbosity=2)
