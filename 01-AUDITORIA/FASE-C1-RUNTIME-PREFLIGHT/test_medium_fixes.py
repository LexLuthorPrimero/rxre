#!/usr/bin/env python3
"""P35-P47 and the realistic bridge fixture.

Closes the five MEDIUM findings of R1-COLLECTOR-INDEPENDENT-REVIEW-2:
  MED-1/2  a real PCI bridge HAS vendor/device; the class check is the barrier,
           and the realistic fixture is the one that must be tested
  MED-3    observe privilege instead of asserting SUDO_INVOKED=YES
  MED-4/5  bundle identity requires host AND kernel; malformed metadata is
           classified, not fatal
  LOW-2    a PID that vanished mid-sweep is not the same state as a denied read

No test invokes sudo, the collector against the host, systemctl, C1, or any live
system probe.  All fixtures are synthetic trees or in-memory.
"""
from __future__ import annotations

import ast
import importlib.util
import inspect
import json
import os
import tempfile
import unittest
from pathlib import Path
from unittest import mock


SCRIPT = Path(__file__).resolve().parent / "privileged_read_collector.py"
SPEC = importlib.util.spec_from_file_location("collector_medium_fixes", SCRIPT)
assert SPEC and SPEC.loader
collector = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(collector)
SOURCE = SCRIPT.read_text(encoding="utf-8")

_ROOT_VISIBILITY = None


def root_visibility_expression():
    """The real ``root_visibility_complete`` assignment inside main().

    Located by AST and returned unevaluated, so a test can supply the counters
    it closes over.  The node is cached because the source does not change
    during a run.
    """
    global _ROOT_VISIBILITY
    if _ROOT_VISIBILITY is None:
        tree = ast.parse(SOURCE)
        main = next(
            n for n in tree.body
            if isinstance(n, ast.FunctionDef) and n.name == "main"
        )
        _ROOT_VISIBILITY = next(
            n for n in ast.walk(main)
            if isinstance(n, ast.Assign)
            and isinstance(n.targets[0], ast.Name)
            and n.targets[0].id == "root_visibility_complete"
        )
    return _ROOT_VISIBILITY


def root_visibility_complete(**overrides):
    """Evaluate the collector's own visibility boolean against given counters.

    ``root_fd_disappeared`` is accepted and defaulted even though the real
    expression never reads it.  That is the point: the result must be
    invariant to the vanished-PID count, and the test asserts exactly that.
    """
    namespace = {
        "root_fd_permission_denied": 0,
        "root_fd_other_errors": 0,
        "current_run_permission_denied": [],
        "unresolved_prior": [],
        "root_fd_disappeared": 0,
    }
    namespace.update(overrides)
    expression = ast.Expression(root_visibility_expression().value)
    ast.fix_missing_locations(expression)
    return eval(compile(expression, "<root_visibility_complete>", "eval"),
                {"len": len}, namespace)

HOST = "kalm"
KERNEL = "7.1.3-200.nobara.fc44.x86_64"
BRIDGE_BDF = "0000:00:01.0"
GPU_BDF = "0000:01:00.0"

# a REAL PCI bridge on this host, read-only on 2026-09-26
REAL_BRIDGE = {"bdf": BRIDGE_BDF, "vendor": "0x8086", "device": "0x0c01", "class": "0x060400"}
REAL_ENDPOINT = {"bdf": GPU_BDF, "vendor": "0x1002", "device": "0x699f", "class": "0x030000"}


# ==========================================================================
# P35-P38  privilege is observed, never asserted
# ==========================================================================
class PrivilegeEvidenceTests(unittest.TestCase):
    def test_P35_euid_zero_means_observed_root(self):
        with mock.patch.object(os, "geteuid", return_value=0), \
             mock.patch.object(os, "getegid", return_value=0):
            state = collector.observe_privilege_state()
        self.assertEqual(state["EUID_OBSERVED"], 0)
        self.assertEqual(state["EUID_OBSERVATION"], "OK")
        self.assertEqual(state["PRIVILEGE_STATE"], "PRIVILEGE_OBSERVED_ROOT")

    def test_P36_euid_nonzero_means_not_root(self):
        for euid in (1000, 1001, 65534):
            with mock.patch.object(os, "geteuid", return_value=euid), \
                 mock.patch.object(os, "getegid", return_value=euid):
                state = collector.observe_privilege_state()
            self.assertEqual(state["PRIVILEGE_STATE"], "PRIVILEGE_NOT_ROOT", euid)
            self.assertEqual(state["EUID_OBSERVED"], euid)

    def test_P36b_unreadable_euid_is_unknown_not_assumed(self):
        with mock.patch.object(os, "geteuid", side_effect=OSError("no such syscall")):
            state = collector.observe_privilege_state()
        self.assertEqual(state["EUID_OBSERVATION"], "ERROR")
        self.assertEqual(state["PRIVILEGE_STATE"], "PRIVILEGE_UNKNOWN")
        self.assertIsNone(state["EUID_OBSERVED"])
        self.assertIn("OSError", state["EUID_ERROR"])

    def test_P37_payload_does_not_assert_sudo_invoked(self):
        self.assertNotIn('"sudo_invoked": True', SOURCE)
        self.assertNotIn('"SUDO_INVOKED": "YES"', SOURCE)
        self.assertIn('"SUDO_INVOKED": "NOT_OBSERVED"', SOURCE)
        # the abort path carries observed privilege too
        abort_node = next(
            n for n in ast.walk(ast.parse(SOURCE))
            if isinstance(n, ast.FunctionDef) and n.name == "abort_payload"
        )
        abort = ast.unparse(abort_node)
        self.assertIn("observe_privilege_state()", abort)
        self.assertNotIn("sudo_invoked", abort)

    def test_P38_expected_wrapper_is_not_evidence_of_elevation(self):
        with mock.patch.object(os, "geteuid", return_value=1000):
            state = collector.observe_privilege_state()
        self.assertEqual(state["SUDO_COMMAND_EXPECTED"], "YES")
        self.assertEqual(state["SUDO_INVOKED"], "NOT_OBSERVED")
        self.assertNotEqual(state["PRIVILEGE_STATE"], "PRIVILEGE_OBSERVED_ROOT")
        # a non-root run must not report privileged_reads
        main_src = inspect.getsource(collector.main)
        self.assertIn('privilege["PRIVILEGE_STATE"] == "PRIVILEGE_OBSERVED_ROOT"', main_src)

    def test_P38b_collector_never_executes_sudo(self):
        for node in ast.walk(ast.parse(SOURCE)):
            if isinstance(node, ast.Call) and isinstance(node.func, ast.Name) and node.func.id == "run":
                for arg in ast.walk(node):
                    self.assertNotEqual(getattr(arg, "value", None), "sudo")
        self.assertNotIn("subprocess.run([\"sudo\"", SOURCE)


# ==========================================================================
# P39-P43  bundle identity policy
# ==========================================================================
def bundle(metadata):
    return {"metadata": metadata, "ownership": {"clients": [], "fd_visibility_errors": []}}


class BundleIdentityPolicyTests(unittest.TestCase):
    def test_P39_same_host_and_kernel_is_accepted(self):
        result = collector.assess_parent_bundle(
            bundle({"host": HOST, "kernel": KERNEL}), HOST, KERNEL
        )
        self.assertEqual(result["PARENT_BUNDLE_IDENTITY"], "MATCH")
        self.assertEqual(result["PARENT_BUNDLE_METADATA"], "READABLE")
        self.assertTrue(result["PRIOR_EVIDENCE_ADMISSIBLE"])
        self.assertEqual(result["OWNERSHIP_EVIDENCE_FROM_PARENT"], "ADMITTED")

    def test_P40_same_host_different_kernel_is_rejected(self):
        result = collector.assess_parent_bundle(
            bundle({"host": HOST, "kernel": "9.9.9"}), HOST, KERNEL
        )
        self.assertEqual(result["PARENT_BUNDLE_IDENTITY"], "KERNEL_MISMATCH")
        self.assertFalse(result["PRIOR_EVIDENCE_ADMISSIBLE"])
        self.assertEqual(result["OWNERSHIP_EVIDENCE_FROM_PARENT"], "NOT_AVAILABLE")

    def test_P41_same_host_kernel_absent_is_rejected_as_incomplete(self):
        result = collector.assess_parent_bundle(bundle({"host": HOST}), HOST, KERNEL)
        self.assertEqual(result["PARENT_BUNDLE_IDENTITY"], "INCOMPLETE")
        self.assertEqual(result["PRIOR_EVIDENCE_STATUS"], "REJECTED_INCOMPLETE_IDENTITY")
        self.assertFalse(result["PRIOR_EVIDENCE_ADMISSIBLE"])
        self.assertIn("no kernel", result["reason"])

    def test_P41b_kernel_present_but_empty_is_also_incomplete(self):
        for value in ("", None, 0, []):
            result = collector.assess_parent_bundle(
                bundle({"host": HOST, "kernel": value}), HOST, KERNEL
            )
            self.assertEqual(result["PARENT_BUNDLE_IDENTITY"], "INCOMPLETE", value)
            self.assertFalse(result["PRIOR_EVIDENCE_ADMISSIBLE"], value)

    def test_P42_different_host_same_kernel_is_rejected(self):
        result = collector.assess_parent_bundle(
            bundle({"host": "lex-luthor", "kernel": KERNEL}), HOST, KERNEL
        )
        self.assertEqual(result["PARENT_BUNDLE_IDENTITY"], "HOST_MISMATCH")
        self.assertFalse(result["PRIOR_EVIDENCE_ADMISSIBLE"])
        self.assertIn("lex-luthor", result["reason"])

    def test_P43_empty_or_absent_metadata_is_rejected_without_crashing(self):
        for payload in ({}, {"metadata": {}}, {"metadata": None}, None, {"other": 1}):
            result = collector.assess_parent_bundle(payload, HOST, KERNEL)
            self.assertFalse(result["PRIOR_EVIDENCE_ADMISSIBLE"], payload)
            self.assertEqual(result["OWNERSHIP_EVIDENCE_FROM_PARENT"], "NOT_AVAILABLE", payload)
            json.dumps(result)

    def test_P43b_malformed_metadata_is_classified_not_fatal(self):
        for payload, kind in (
            ({"metadata": "not-a-dict"}, "str"),
            ({"metadata": ["a", "b"]}, "list"),
            ({"metadata": 7}, "int"),
            ({"metadata": True}, "bool"),
            ("a string", "str"),
            (["a", "list"], "list"),
            (42, "int"),
        ):
            result = collector.assess_parent_bundle(payload, HOST, KERNEL)
            self.assertEqual(result["PARENT_BUNDLE_METADATA"], "INVALID", payload)
            self.assertEqual(result["PARENT_BUNDLE_IDENTITY"], "INVALID", payload)
            self.assertEqual(result["PRIOR_EVIDENCE_STATUS"], "REJECTED_BUNDLE_MALFORMED", payload)
            self.assertFalse(result["PRIOR_EVIDENCE_ADMISSIBLE"], payload)
            self.assertIn(kind, result["reason"], payload)
            self.assertEqual(result["OWNERSHIP_EVIDENCE_FROM_PARENT"], "NOT_AVAILABLE", payload)

    def test_P43c_invalid_metadata_never_yields_an_empty_client_list(self):
        """A rejected bundle must not read as 'no prior clients'."""
        main_src = inspect.getsource(collector.main)
        self.assertIn("if prior_admissible:", main_src)
        self.assertIn("prior_clients = []", main_src)
        self.assertIn('new_gpu_clients = "NOT_AVAILABLE"', main_src)
        # and the btrfs parent_state is gated too
        self.assertIn(
            'PARENT.get("btrfs", {})\n            if parent_assessment["OWNERSHIP_EVIDENCE_FROM_PARENT"] == "ADMITTED"',
            main_src,
        )

    def test_policy_is_stated_not_implicit(self):
        result = collector.assess_parent_bundle(bundle({"host": HOST}), HOST, KERNEL)
        self.assertIn("host must match AND kernel", result["policy"])


# ==========================================================================
# P44-P47  a vanished PID is not a denied read
# ==========================================================================
class ProcErrorClassTests(unittest.TestCase):
    def test_P44_error_classification(self):
        cases = {
            "PermissionError: [Errno 13] Permission denied": "PERMISSION_DENIED",
            "FileNotFoundError: [Errno 2] No such file or directory": "PROCESS_DISAPPEARED",
            "ProcessLookupError: [Errno 3]": "PROCESS_DISAPPEARED",
            "OSError: [Errno 5] I/O error": "OTHER_ERROR",
            "": "OTHER_ERROR",
        }
        for text, expected in cases.items():
            self.assertEqual(collector.classify_proc_error(text), expected, text)

    def test_P44b_a_vanished_process_is_not_a_visibility_failure(self):
        """The boolean that feeds card/render coverage must ignore a race.

        root_visibility_complete decides card_complete and render_complete, and
        so the card_node_complete and render_node_complete ownership rows.  A
        process that vanished mid-sweep released its FDs when it died, so the
        count of vanished PIDs must not make visibility incomplete -- while a
        denied or otherwise broken read must.

        The real expression is located in main() and evaluated, using the same
        AST idiom as test_defect06_behavioral.py.  It is not restated here, so
        this test cannot pass while the collector computes something else.
        """
        clean = {
            "root_fd_permission_denied": 0,
            "root_fd_other_errors": 0,
            "current_run_permission_denied": [],
            "unresolved_prior": [],
        }
        self.assertIs(root_visibility_complete(**clean), True)
        for vanished in (0, 1, 5, 500):
            with self.subTest(vanished=vanished):
                self.assertIs(
                    root_visibility_complete(root_fd_disappeared=vanished, **clean),
                    True,
                    "a vanished PID released its FDs when it died; it must not "
                    "reduce root visibility",
                )
        for overrides in (
            {"root_fd_permission_denied": 1},
            {"root_fd_other_errors": 1},
            {"current_run_permission_denied": ["/proc/9/fd"]},
            {"unresolved_prior": ["/proc/5/fd"]},
        ):
            with self.subTest(**overrides):
                self.assertIs(
                    root_visibility_complete(**{**clean, **overrides}),
                    False,
                    "a denied or broken read leaves visibility incomplete",
                )

    def test_P45_existing_pid_with_permission_error_is_denied(self):
        # scan_fds lists the table with os.listdir, so a denied table surfaces
        # there rather than through Path.open.
        with tempfile.TemporaryDirectory() as raw:
            with mock.patch.object(os, "listdir", side_effect=PermissionError(13, "denied")):
                result = collector.scan_fds(1, {"/dev/dri/card1"}, proc_root=Path(raw))
        self.assertEqual(result["status"], "ERROR")
        self.assertEqual(result["status_reason"], "PERMISSION_DENIED")
        self.assertEqual(result["errors"][0]["reason"], "PERMISSION_DENIED")
        self.assertEqual(result["error_count"], 1)

    def test_P46_vanished_pid_is_classified_as_disappeared(self):
        with tempfile.TemporaryDirectory() as raw:
            with mock.patch.object(os, "listdir", side_effect=FileNotFoundError(2, "gone")):
                result = collector.scan_fds(1, {"/dev/dri/card1"}, proc_root=Path(raw))
        self.assertEqual(result["status"], "ERROR")
        self.assertEqual(result["status_reason"], "PROCESS_DISAPPEARED")
        self.assertNotEqual(result["status_reason"], "PERMISSION_DENIED")

    def test_P46b_per_fd_readlink_failure_keeps_its_class(self):
        with tempfile.TemporaryDirectory() as raw:
            fd_dir = Path(raw) / "77" / "fd"
            fd_dir.mkdir(parents=True)
            os.mkfifo(fd_dir / "0")
            with mock.patch.object(os, "readlink", side_effect=PermissionError(13, "denied")):
                result = collector.scan_fds(77, {"/dev/dri/card1"}, proc_root=Path(raw))
        self.assertEqual(result["error_count"], 1)
        self.assertEqual(result["errors"][0]["reason"], "PERMISSION_DENIED")
        # and an unrelated failure is not laundered into PERMISSION_DENIED
        with tempfile.TemporaryDirectory() as raw:
            fd_dir = Path(raw) / "78" / "fd"
            fd_dir.mkdir(parents=True)
            os.mkfifo(fd_dir / "0")
            with mock.patch.object(os, "readlink", side_effect=OSError(22, "Invalid argument")):
                other = collector.scan_fds(78, {"/dev/dri/card1"}, proc_root=Path(raw))
        self.assertEqual(other["errors"][0]["reason"], "OTHER_ERROR")

    def test_P47_a_normal_readable_pid_has_no_error_class(self):
        with tempfile.TemporaryDirectory() as raw:
            pid_dir = Path(raw) / "9"
            (pid_dir / "fd").mkdir(parents=True)
            (pid_dir / "stat").write_text("9 (bash) S 1 9 9 0 -1 4194304 100 0 0 0 1 2 0 0 20 0 1 0 5 0 1\n")
            result = collector.scan_fds(9, {"/dev/dri/card1"}, proc_root=Path(raw))
        self.assertEqual(result["status"], "OK")
        self.assertEqual(result["error_count"], 0)
        self.assertEqual(result["errors"], [])
        self.assertNotIn("status_reason", result)

    def test_P47b_parse_proc_stat_records_the_reason(self):
        with tempfile.TemporaryDirectory() as raw:
            with mock.patch.object(Path, "open", side_effect=FileNotFoundError(2, "gone")):
                gone = collector.parse_proc_stat(5, proc_root=Path(raw))
            with mock.patch.object(Path, "open", side_effect=PermissionError(13, "denied")):
                denied = collector.parse_proc_stat(5, proc_root=Path(raw))
        self.assertEqual(gone["reason"], "PROCESS_DISAPPEARED")
        self.assertEqual(denied["reason"], "PERMISSION_DENIED")
        self.assertNotEqual(gone["reason"], denied["reason"])

    def test_the_boolean_is_built_from_denied_and_other_only(self):
        main_src = inspect.getsource(collector.main)
        self.assertIn("root_fd_permission_denied == 0", main_src)
        self.assertIn("root_fd_other_errors == 0", main_src)
        self.assertIn("and not current_run_permission_denied", main_src)
        self.assertNotIn("and not current_run_disappeared", main_src)
        self.assertIn('"current_run_disappeared_classification": "NOT_APPLICABLE_PER_OBSERVATION"',
                      main_src)


# ==========================================================================
# the realistic bridge fixture -- the case T22b failed to represent
# ==========================================================================
class RealisticBridgeTests(unittest.TestCase):
    """A real PCI bridge has vendor AND device.  The barrier against adopting it
    is the PCI class, not a missing attribute."""

    def build(self, root: Path, *, card_points_at="bridge"):
        sysfs = root / "sys"
        pci = sysfs / "devices" / "pci0000:00"
        # the bridge, exactly as this host reports it
        bridge = pci / REAL_BRIDGE["bdf"]
        bridge.mkdir(parents=True)
        (bridge / "vendor").write_text(REAL_BRIDGE["vendor"] + "\n")
        (bridge / "device").write_text(REAL_BRIDGE["device"] + "\n")
        (bridge / "class").write_text(REAL_BRIDGE["class"] + "\n")
        (sysfs / "bus" / "pci" / "drivers" / "i915").mkdir(parents=True)
        (bridge / "driver").symlink_to(
            os.path.relpath(sysfs / "bus" / "pci" / "drivers" / "i915", bridge)
        )
        # the endpoint behind it
        endpoint = bridge / REAL_ENDPOINT["bdf"]
        (endpoint / "drm").mkdir(parents=True)
        (endpoint / "vendor").write_text(REAL_ENDPOINT["vendor"] + "\n")
        (endpoint / "device").write_text(REAL_ENDPOINT["device"] + "\n")
        (endpoint / "class").write_text(REAL_ENDPOINT["class"] + "\n")
        (sysfs / "bus" / "pci" / "drivers" / "amdgpu").mkdir(parents=True)
        (endpoint / "driver").symlink_to(
            os.path.relpath(sysfs / "bus" / "pci" / "drivers" / "amdgpu", endpoint)
        )
        node_dir = endpoint / "drm" / "card1"
        node_dir.mkdir()
        (node_dir / "driver").symlink_to(
            os.path.relpath(sysfs / "bus" / "pci" / "drivers" / "amdgpu", node_dir)
        )
        target = bridge if card_points_at == "bridge" else endpoint
        (node_dir / "device").symlink_to(os.path.relpath(target, node_dir))
        link = sysfs / "class" / "drm" / "card1"
        link.parent.mkdir(parents=True)
        link.symlink_to(os.path.relpath(node_dir, os.path.realpath(link.parent)))
        forward = sysfs / "bus" / "pci" / "devices" / REAL_ENDPOINT["bdf"]
        forward.parent.mkdir(parents=True)
        forward.symlink_to(os.path.relpath(endpoint, forward.parent))
        return sysfs

    def test_the_bridge_really_does_have_vendor_and_device(self):
        """If this ever fails, the fixture no longer represents reality."""
        with tempfile.TemporaryDirectory() as raw:
            sysfs = self.build(Path(raw))
            bridge = sysfs / "devices/pci0000:00" / REAL_BRIDGE["bdf"]
            self.assertTrue((bridge / "vendor").exists())
            self.assertTrue((bridge / "device").exists())
            self.assertEqual((bridge / "class").read_text().strip(), REAL_BRIDGE["class"])
            # so the "no vendor/device" rejection reason cannot be what fires
            node = collector.resolve_node_device(sysfs / "class/drm/card1")
        self.assertEqual(node["BDF_LINK_ABORT"], "PCI_IDENTITY_MISMATCH_AT_NODE")
        self.assertNotEqual(node["BDF_LINK_ABORT"], "DEVICE_DIR_LACKS_PCI_VENDOR_DEVICE")
        self.assertTrue(any("class=" in m for m in node["mismatches"]), node["mismatches"])
        self.assertTrue(any("vendor=" in m for m in node["mismatches"]), node["mismatches"])

    def test_the_bridge_is_never_adopted(self):
        with tempfile.TemporaryDirectory() as raw:
            sysfs = self.build(Path(raw), card_points_at="bridge")
            node = collector.resolve_node_device(sysfs / "class/drm/card1")
            identity = collector.resolve_gpu_identity(sysfs_root=sysfs)
        self.assertEqual(node["BDF_LINK_STATUS"], "NOT_PROVEN")
        # resolved_bdf records what the symlink pointed at -- that is the
        # diagnostic, and it is kept.  What must not happen is adoption.
        self.assertEqual(node["resolved_bdf"], REAL_BRIDGE["bdf"])
        self.assertEqual(node["BDF_LINK_ABORT"], "PCI_IDENTITY_MISMATCH_AT_NODE")
        excluded = {e["node"] for e in identity["drm_discovery"]["reverse"]["excluded"]}
        self.assertIn("card1", excluded)
        self.assertEqual(identity["GPU_CARD_NODE"], None)
        self.assertEqual(identity["GPU_IDENTITY_STATUS"], "NOT_PROVEN")
        self.assertEqual(identity["devices"], set())

    def test_the_real_endpoint_is_still_accepted(self):
        with tempfile.TemporaryDirectory() as raw:
            sysfs = self.build(Path(raw), card_points_at="endpoint")
            node = collector.resolve_node_device(sysfs / "class/drm/card1")
        self.assertEqual(node["resolved_bdf"], REAL_ENDPOINT["bdf"])
        self.assertEqual(node["BDF_LINK_STATUS"], "PROVEN")
        self.assertEqual(node["bdf_components_in_path"],
                         [REAL_BRIDGE["bdf"], REAL_ENDPOINT["bdf"]])

    def test_the_ownership_matrix_is_unchanged_by_all_of_this(self):
        """Guard: none of the four corrections may alter the criterion."""
        ctx = {
            "gpu_identity": {"GPU_IDENTITY_STATUS": "PROVEN", "GPU_CARD_NODE": "card1",
                             "GPU_RENDER_NODE": "renderD129"},
            "root_coverage": {
                "card_complete": True, "render_complete": True,
                "card_drm_client_id_fds": 0,
                "render_drm_client_id_fds": 0,
                "card_drm_pdev_fds": 0,
                "render_drm_pdev_fds": 0,
                "card_pasid_fds": 0,
                "render_pasid_fds": 0,
                "user_namespace_complete": True, "root_namespace_complete": True,
                "fd_error_count": 0, "user_namespace_ok": 84, "user_namespace_total": 84,
                "root_namespace_ok": 199, "root_namespace_total": 199, "total_pids": 283,
            },
            "debugfs": {"DEBUGFS_CLIENT_ATTRIBUTION": "PROVEN", "reason": "OK",
                        "clients_path": "/x"},
            "btrfs_observation": {}, "btrfs_status": "ABSENT", "active_agents": 0,
            "pm_status": "READ", "card_drm_client_id_fds": 0, "render_drm_client_id_fds": 0,
        }
        result = collector.ownership_matrix(ctx)
        self.assertEqual(len(result["conditions"]), 10)
        self.assertNotEqual(result["OWNERSHIP_CRITERION_STATE"], "FULL")
        by_key = {r["condition"]: r for r in result["conditions"]}
        self.assertEqual(by_key["writers_resolved"]["STATE"], "NOT_EVALUATED")
        self.assertEqual(by_key["guard_and_restore"]["STATE"], "NOT_EVALUATED")


if __name__ == "__main__":
    unittest.main(verbosity=2)
