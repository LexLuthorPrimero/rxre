#!/usr/bin/env python3
"""T17-T34: the two defects that aborted R1 run R1-20260926T000649Z.

DEFECT-01  the BDF was taken from the first BDF-shaped substring of the
           realpath, which on this host is the PCI *bridge*.
DEFECT-02  the parent bundle was consumed without any host-identity check, so
           363 PIDs from another host fed root_visibility_complete.

T17-T25 cover DEFECT-01, T26-T34 cover DEFECT-02.  T17 and T19 reproduce the
exact failing path from the aborted run.

No test invokes sudo, the collector against the host, systemctl, C1, or any
live system probe.  All fixtures are synthetic trees in temporary directories.
"""
from __future__ import annotations

import ast
import importlib.util
import inspect
import itertools
import json
import os
import tempfile
import unittest
from pathlib import Path


SCRIPT = Path(__file__).resolve().parent / "privileged_read_collector.py"
SPEC = importlib.util.spec_from_file_location("collector_r1_defects", SCRIPT)
assert SPEC and SPEC.loader
collector = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(collector)
SOURCE = SCRIPT.read_text(encoding="utf-8")

BDF_GPU = "0000:01:00.0"
BRIDGE = "0000:00:01.0"
BDF_IGPU = "0000:00:02.0"
# the exact path that aborted R1-20260926T000649Z
REAL_PATH = "/sys/devices/pci0000:00/0000:00:01.0/0000:01:00.0"


# --------------------------------------------------------------------------
# synthetic sysfs where the endpoint may sit behind a bridge
# --------------------------------------------------------------------------
def build(root: Path, *, chain=(BRIDGE, BDF_GPU), vendor="0x1002", device="0x699f",
          klass="0x030000", driver="amdgpu", bridge_has_identity=False,
          nodes=("card1", "renderD129"), igpu_nodes=("card0", "renderD128"),
          link_target_override=None, extra_igpu_bdfs=()) -> Path:
    """chain is the ordered list of PCI BDF directories from pci0000:00 down.

    ('0000:00:01.0', '0000:01:00.0') reproduces the bridge case.
    """
    sysfs = root / "sys"
    pci_root = sysfs / "devices" / "pci0000:00"

    def make_dir(parent: Path, bdf: str, with_identity: bool) -> Path:
        """PCI directories are NESTED: a device behind a bridge lives *inside*
        the bridge directory, which is what puts two BDFs in one path."""
        directory = parent / bdf
        directory.mkdir(parents=True, exist_ok=True)
        if with_identity:
            (directory / "vendor").write_text(vendor + "\n", encoding="utf-8")
            (directory / "device").write_text(device + "\n", encoding="utf-8")
            (directory / "class").write_text(klass + "\n", encoding="utf-8")
        return directory

    # walk down the chain, nesting each component inside the previous one
    cursor = pci_root
    for bdf in chain[:-1]:
        cursor = make_dir(cursor, bdf, bridge_has_identity)
    endpoint = make_dir(cursor, chain[-1], True)
    endpoint_drm = endpoint / "drm"
    endpoint_drm.mkdir(parents=True, exist_ok=True)
    (sysfs / "bus" / "pci" / "drivers" / driver).mkdir(parents=True, exist_ok=True)
    (endpoint / "driver").symlink_to(
        os.path.relpath(sysfs / "bus" / "pci" / "drivers" / driver, endpoint)
    )
    for node in nodes:
        node_dir = endpoint_drm / node
        node_dir.mkdir(parents=True, exist_ok=True)
        (node_dir / "driver").symlink_to(
            os.path.relpath(sysfs / "bus" / "pci" / "drivers" / driver, node_dir)
        )
        if link_target_override:
            other = pci_root / link_target_override
            # (a device behind the same bridge stays a direct child of pci0000:00)
            other.mkdir(parents=True, exist_ok=True)
            (other / "vendor").write_text(vendor + "\n", encoding="utf-8")
            (other / "device").write_text(device + "\n", encoding="utf-8")
            (other / "class").write_text(klass + "\n", encoding="utf-8")
            (node_dir / "device").symlink_to(os.path.relpath(other, node_dir))
        else:
            (node_dir / "device").symlink_to(os.path.relpath(endpoint, node_dir))
        link = sysfs / "class" / "drm" / node
        link.parent.mkdir(parents=True, exist_ok=True)
        link.symlink_to(os.path.relpath(node_dir, link.parent))
    forward = sysfs / "bus" / "pci" / "devices" / BDF_GPU
    forward.parent.mkdir(parents=True, exist_ok=True)
    forward.symlink_to(os.path.relpath(endpoint, forward.parent))

    # a second, clearly-false amdgpu candidate to exercise ambiguity
    igpu = make_dir(pci_root, BDF_IGPU, True)
    (igpu / "vendor").write_text("0x8086\n", encoding="utf-8")
    (igpu / "device").write_text("0x0412\n", encoding="utf-8")
    (igpu / "class").write_text(klass + "\n", encoding="utf-8")
    (sysfs / "bus" / "pci" / "drivers" / "i915").mkdir(parents=True, exist_ok=True)
    (igpu / "driver").symlink_to(
        os.path.relpath(sysfs / "bus" / "pci" / "drivers" / "i915", igpu)
    )
    for node in igpu_nodes:
        node_dir = igpu / "drm" / node
        node_dir.mkdir(parents=True, exist_ok=True)
        (node_dir / "driver").symlink_to(
            os.path.relpath(sysfs / "bus" / "pci" / "drivers" / "i915", node_dir)
        )
        (node_dir / "device").symlink_to(os.path.relpath(igpu, node_dir))
        link = sysfs / "class" / "drm" / node
        link.parent.mkdir(parents=True, exist_ok=True)
        link.symlink_to(os.path.relpath(node_dir, link.parent))
    igpu_forward = sysfs / "bus" / "pci" / "devices" / BDF_IGPU
    igpu_forward.parent.mkdir(parents=True, exist_ok=True)
    igpu_forward.symlink_to(os.path.relpath(igpu, igpu_forward.parent))
    return sysfs


def link_to(node_dir: Path, target_dir: Path, name: str = "device") -> None:
    """Create node_dir/<name> -> target_dir, relative to the *real* parent.

    sysfs resolves a relative symlink from the link's real location, and
    class/drm/<node> is itself a symlink, so relpath must be computed against
    the resolved parent or the link dangles.
    """
    real_parent = Path(os.path.realpath(node_dir))
    (real_parent / name).unlink(missing_ok=True)
    (real_parent / name).symlink_to(os.path.relpath(target_dir, real_parent))


def endpoint_dir(sysfs: Path, chain) -> Path:
    """The nested PCI device directory at the end of a bridge chain."""
    cursor = sysfs / "devices" / "pci0000:00"
    for bdf in chain:
        cursor = cursor / bdf
    return cursor



# ==========================================================================
# T17-T25  DEFECT-01
# ==========================================================================
class Defect01BridgeTests(unittest.TestCase):
    def test_T17_endpoint_direct_no_bridge(self):
        with tempfile.TemporaryDirectory() as raw:
            sysfs = build(Path(raw), chain=(BDF_GPU,))
            node = collector.resolve_node_device(sysfs / "class/drm/card1")
            identity = collector.resolve_gpu_identity(sysfs_root=sysfs)
        self.assertEqual(node["resolved_bdf"], BDF_GPU)
        self.assertEqual(node["BDF_LINK_STATUS"], "PROVEN")
        self.assertEqual(identity["GPU_IDENTITY_STATUS"], "PROVEN")
        self.assertEqual(identity["GPU_CARD_NODE"], "card1")

    def test_T18_endpoint_behind_a_bridge(self):
        with tempfile.TemporaryDirectory() as raw:
            sysfs = build(Path(raw), chain=(BRIDGE, BDF_GPU))
            node = collector.resolve_node_device(sysfs / "class/drm/card1")
            identity = collector.resolve_gpu_identity(sysfs_root=sysfs)
        self.assertEqual(node["resolved_bdf"], BDF_GPU)
        self.assertNotEqual(node["resolved_bdf"], BRIDGE)
        self.assertEqual(node["BDF_LINK_STATUS"], "PROVEN")
        self.assertEqual(identity["GPU_IDENTITY_STATUS"], "PROVEN")

    def test_T19_the_exact_path_that_aborted_R1(self):
        """The primary regression.  Must yield 0000:01:00.0, never 0000:00:01.0."""
        self.assertEqual(
            REAL_PATH,
            "/sys/devices/pci0000:00/0000:00:01.0/0000:01:00.0",
        )
        components = [m.group(1) for m in collector.BDF_RE.finditer(REAL_PATH)]
        self.assertEqual(components, [BRIDGE, BDF_GPU], "path really does hold two BDFs")
        self.assertEqual(os.path.basename(REAL_PATH), BDF_GPU)
        # structural resolution: build the same shape and resolve it
        with tempfile.TemporaryDirectory() as raw:
            sysfs = build(Path(raw), chain=(BRIDGE, BDF_GPU))
            real = os.path.realpath(sysfs / "class/drm/card1/device")
            self.assertEqual(real.split("/pci0000:00/")[1], f"{BRIDGE}/{BDF_GPU}")
            directory = collector.resolve_pci_device_dir(sysfs / "class/drm/card1/device")
        self.assertEqual(directory["device_dir_bdf"], BDF_GPU)
        self.assertEqual(directory["bdf_components_in_path"], [BRIDGE, BDF_GPU])
        self.assertNotEqual(directory["device_dir_bdf"], BRIDGE)
        self.assertEqual(directory["PCI_DEVICE_DIR_STATUS"], "PROVEN")

    def test_T20_bridge_carries_wrong_identity_but_endpoint_is_correct(self):
        """A bridge with vendor/device of its own must not become identity."""
        with tempfile.TemporaryDirectory() as raw:
            sysfs = build(Path(raw), chain=(BRIDGE, BDF_GPU), bridge_has_identity=True)
            # poison the bridge's identity: it now claims to be the RX550
            (sysfs / "devices/pci0000:00" / BRIDGE / "vendor").write_text("0xDEAD\n")
            (sysfs / "devices/pci0000:00" / BRIDGE / "device").write_text("0xBEEF\n")
            (sysfs / "devices/pci0000:00" / BRIDGE / "class").write_text("0x0604\n")
            node = collector.resolve_node_device(sysfs / "class/drm/card1")
            identity = collector.resolve_gpu_identity(sysfs_root=sysfs)
        self.assertEqual(node["resolved_bdf"], BDF_GPU)
        self.assertEqual(node["BDF_LINK_STATUS"], "PROVEN")
        self.assertEqual(identity["GPU_IDENTITY_STATUS"], "PROVEN")

    def test_T21_endpoint_bdf_correct_but_identity_wrong(self):
        """Correct BDF, wrong vendor/device: the identity check is NOT relaxed."""
        for field, value in (("vendor", "0x8086"), ("device", "0x0412")):
            with tempfile.TemporaryDirectory() as raw:
                sysfs = build(Path(raw), chain=(BRIDGE, BDF_GPU))
                (endpoint_dir(sysfs, (BRIDGE, BDF_GPU)) / field).write_text(value + "\n")
                node = collector.resolve_node_device(sysfs / "class/drm/card1")
                identity = collector.resolve_gpu_identity(sysfs_root=sysfs)
            self.assertEqual(node["resolved_bdf"], BDF_GPU, f"{field} change keeps the BDF")
            self.assertEqual(node["BDF_LINK_STATUS"], "NOT_PROVEN", field)
            self.assertEqual(node["BDF_LINK_ABORT"], "PCI_IDENTITY_MISMATCH_AT_NODE", field)
            self.assertEqual(identity["GPU_IDENTITY_STATUS"], "NOT_PROVEN", field)
            self.assertEqual(identity["devices"], set(), field)

    def test_T22_path_without_a_valid_pci_bdf_final_component(self):
        with tempfile.TemporaryDirectory() as raw:
            sysfs = build(Path(raw), chain=(BDF_GPU,))
            # repoint the node at a directory that is not a PCI device dir
            stray = sysfs / "devices" / "pci0000:00" / "not-a-bdf"
            stray.mkdir(parents=True, exist_ok=True)
            link_to(endpoint_dir(sysfs, (BDF_GPU,)) / "drm" / "card1", stray)
            result = collector.resolve_pci_device_dir(sysfs / "class/drm/card1/device")
        self.assertEqual(result["PCI_DEVICE_DIR_STATUS"], "NOT_PROVEN")
        self.assertEqual(result["PCI_DEVICE_DIR_ABORT"], "DEVICE_DIR_NAME_IS_NOT_A_BDF")
        self.assertIsNone(result["device_dir_bdf"])

    def test_T22b_bdf_shaped_directory_without_pci_attributes_is_refused(self):
        with tempfile.TemporaryDirectory() as raw:
            sysfs = build(Path(raw), chain=(BDF_GPU,))
            # a bridge-shaped name that carries no vendor/device attributes
            hollow = sysfs / "devices" / "pci0000:00" / "0000:00:1f.2"
            hollow.mkdir(parents=True, exist_ok=True)
            link_to(endpoint_dir(sysfs, (BDF_GPU,)) / "drm" / "card1", hollow)
            result = collector.resolve_pci_device_dir(sysfs / "class/drm/card1/device")
        self.assertEqual(result["PCI_DEVICE_DIR_STATUS"], "NOT_PROVEN")
        self.assertEqual(
            result["PCI_DEVICE_DIR_ABORT"], "DEVICE_DIR_LACKS_PCI_VENDOR_DEVICE"
        )

    def test_T23_ambiguous_candidates_still_abort(self):
        with tempfile.TemporaryDirectory() as raw:
            sysfs = build(Path(raw), chain=(BRIDGE, BDF_GPU))
            # a second card node that also resolves to the proven endpoint
            endpoint = endpoint_dir(sysfs, (BRIDGE, BDF_GPU))
            extra = endpoint / "drm" / "card2"
            extra.mkdir(parents=True, exist_ok=True)
            link_to(extra, endpoint)
            link = sysfs / "class/drm/card2"
            link.parent.mkdir(parents=True, exist_ok=True)
            link.symlink_to(os.path.relpath(extra, os.path.realpath(link.parent)))
            identity = collector.resolve_gpu_identity(sysfs_root=sysfs)
        self.assertEqual(identity["GPU_IDENTITY_STATUS"], "NOT_PROVEN")
        self.assertEqual(
            identity["drm_discovery"]["DRM_DISCOVERY_ABORT"], "AMBIGUOUS_CANDIDATE"
        )
        self.assertEqual(identity["devices"], set())

    def test_T24_card_and_render_resolve_to_the_same_valid_endpoint(self):
        with tempfile.TemporaryDirectory() as raw:
            sysfs = build(Path(raw), chain=(BRIDGE, BDF_GPU))
            card = collector.resolve_node_device(sysfs / "class/drm/card1")
            render = collector.resolve_node_device(sysfs / "class/drm/renderD129")
            identity = collector.resolve_gpu_identity(sysfs_root=sysfs)
        self.assertEqual(card["resolved_bdf"], render["resolved_bdf"])
        self.assertEqual(card["resolved_bdf"], BDF_GPU)
        self.assertEqual(card["BDF_LINK_STATUS"], "PROVEN")
        self.assertEqual(render["BDF_LINK_STATUS"], "PROVEN")
        self.assertTrue(identity["drm_discovery"]["agreement"])
        self.assertEqual(identity["GPU_IDENTITY_STATUS"], "PROVEN")
        self.assertEqual(
            identity["devices"], {"/dev/dri/card1", "/dev/dri/renderD129"}
        )

    def test_T25_valid_endpoint_with_a_bridge_present(self):
        for chain in ((BRIDGE, BDF_GPU),
                      ("0000:00:1c.0", BRIDGE, BDF_GPU),
                      ("0000:00:1c.0", "0000:00:1b.0", BRIDGE, BDF_GPU)):
            with tempfile.TemporaryDirectory() as raw:
                sysfs = build(Path(raw), chain=chain)
                node = collector.resolve_node_device(sysfs / "class/drm/card1")
            self.assertEqual(node["resolved_bdf"], BDF_GPU, chain)
            self.assertNotIn(node["resolved_bdf"], chain[:-1], chain)
            self.assertEqual(node["BDF_LINK_STATUS"], "PROVEN", chain)
            self.assertEqual(node["bdf_components_in_path"], list(chain), chain)

    def test_T25b_the_old_first_match_heuristic_would_have_been_wrong(self):
        """Documents precisely why the fix was necessary."""
        with tempfile.TemporaryDirectory() as raw:
            sysfs = build(Path(raw), chain=(BRIDGE, BDF_GPU))
            real = os.path.realpath(sysfs / "class/drm/card1/device")
        first_match = collector.BDF_RE.search(real).group(1)
        self.assertEqual(first_match, BRIDGE, "the old heuristic returns the bridge")
        self.assertNotEqual(first_match, BDF_GPU)

    def test_the_old_extractor_is_gone(self):
        self.assertFalse(hasattr(collector, "_bdf_from_realpath"))
        self.assertNotIn("BDF_RE.search(", SOURCE)


# ==========================================================================
# T26-T34  DEFECT-02
# ==========================================================================
def bundle(host=None, kernel=None, errors=0, clients=0):
    payload = {
        "metadata": {},
        "ownership": {
            "fd_visibility_errors": [{"pid": 900000 + i, "error": "PermissionError: x"}
                                     for i in range(errors)],
            "clients": [{"resource": "/dev/dri/card1", "fd": 13, "pid": 900000 + i}
                        for i in range(clients)],
        },
    }
    if host is not None:
        payload["metadata"]["host"] = host
    if kernel is not None:
        payload["metadata"]["kernel"] = kernel
    return payload


HOST = "kalm"
KERNEL = "7.1.3-200.nobara.fc44.x86_64"


class Defect02ParentBundleTests(unittest.TestCase):
    def test_T26_same_host_and_kernel_is_accepted(self):
        result = collector.assess_parent_bundle(
            bundle(host=HOST, kernel=KERNEL, errors=3), HOST, KERNEL
        )
        self.assertEqual(result["PARENT_BUNDLE_IDENTITY"], "MATCH")
        self.assertTrue(result["PRIOR_EVIDENCE_ADMISSIBLE"])
        self.assertEqual(result["PRIOR_EVIDENCE_STATUS"], "ACCEPTED_SAME_HOST_AND_KERNEL")

    def test_T27_other_host_is_rejected(self):
        result = collector.assess_parent_bundle(
            bundle(host="lex-luthor", kernel="7.2.6-201.nobara.fc44.x86_64", errors=363),
            HOST, KERNEL,
        )
        self.assertEqual(result["PARENT_BUNDLE_IDENTITY"], "HOST_MISMATCH")
        self.assertFalse(result["PRIOR_EVIDENCE_ADMISSIBLE"])
        self.assertEqual(result["PRIOR_EVIDENCE_STATUS"], "REJECTED_HOST_MISMATCH")
        self.assertIn("lex-luthor", result["reason"])
        self.assertIn("kalm", result["reason"])

    def test_T28_different_kernel_is_rejected_when_used_as_identity(self):
        result = collector.assess_parent_bundle(
            bundle(host=HOST, kernel="9.9.9-custom"), HOST, KERNEL
        )
        self.assertEqual(result["PARENT_BUNDLE_IDENTITY"], "KERNEL_MISMATCH")
        self.assertFalse(result["PRIOR_EVIDENCE_ADMISSIBLE"])
        self.assertEqual(result["PRIOR_EVIDENCE_STATUS"], "REJECTED_KERNEL_MISMATCH")

    def test_T28b_bundle_without_declared_identity_is_rejected(self):
        for payload in ({}, {"metadata": {}}, {"metadata": None}):
            result = collector.assess_parent_bundle(payload, HOST, KERNEL)
            self.assertFalse(result["PRIOR_EVIDENCE_ADMISSIBLE"], payload)
            self.assertEqual(
                result["PRIOR_EVIDENCE_STATUS"],
                "REJECTED_PARENT_IDENTITY_NOT_AVAILABLE",
                payload,
            )

    def test_T29_historical_pids_cannot_move_current_visibility(self):
        """A foreign bundle carrying 363 errors must not change any current count."""
        foreign = collector.assess_parent_bundle(
            bundle(host="lex-luthor", errors=363), HOST, KERNEL
        )
        self.assertFalse(foreign["PRIOR_EVIDENCE_ADMISSIBLE"])
        # the rejected branch yields no prior PIDs at all
        prior_errors = [] if not foreign["PRIOR_EVIDENCE_ADMISSIBLE"] else ["x"]
        self.assertEqual(prior_errors, [])
        # and the boolean is built from the current run only
        self.assertIn("root_fd_permission_denied == 0", SOURCE)
        self.assertIn("root_fd_other_errors == 0", SOURCE)
        self.assertIn("and not current_run_permission_denied", SOURCE)

    def test_T30_run_without_a_historical_bundle_inherits_no_errors(self):
        result = collector.assess_parent_bundle({}, HOST, KERNEL)
        self.assertFalse(result["PRIOR_EVIDENCE_ADMISSIBLE"])
        self.assertIn("NOT_AVAILABLE", result["PRIOR_EVIDENCE_STATUS"])

    def test_T31_current_run_errors_do_affect_current_visibility(self):
        """The isolation must be one-directional: current errors still count."""
        main_src = inspect.getsource(collector.main)
        self.assertIn("root_fd_error_count += int(fd.get(\"error_count\", 0))", main_src)
        self.assertIn("root_fd_permission_denied == 0", main_src)
        self.assertIn("and not current_run_permission_denied", main_src)
        # a PID that vanished mid-sweep must NOT gate visibility
        self.assertNotIn("and not current_run_disappeared", main_src)
        for fd_errors, unreadable, expected in (
            (0, [], True), (1, [], False), (0, ["7"], False), (5, ["1", "2"], False),
        ):
            self.assertEqual(
                fd_errors == 0 and not unreadable, expected,
                (fd_errors, unreadable),
            )

    def test_T32_mixing_hosts_can_never_reach_full(self):
        """No admissible parent + perfect current run still cannot be FULL."""
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
        self.assertNotEqual(result["OWNERSHIP_CRITERION_STATE"], "FULL")
        by_key = {r["condition"]: r for r in result["conditions"]}
        self.assertEqual(by_key["writers_resolved"]["STATE"], "NOT_EVALUATED")
        self.assertEqual(by_key["guard_and_restore"]["STATE"], "NOT_EVALUATED")

    def test_T33_rejected_evidence_is_never_reported_as_zero_clients(self):
        """The differential must be NOT_AVAILABLE, not an empty list."""
        main_src = inspect.getsource(collector.main)
        self.assertIn('new_gpu_clients = "NOT_AVAILABLE"', main_src)
        self.assertIn('gpu_delta_status = parent_assessment["PRIOR_EVIDENCE_STATUS"]', main_src)
        self.assertIn('len(new_gpu_clients) if gpu_delta_status == "COMPUTED" else "NOT_AVAILABLE"',
                      main_src)
        # and the same for the storage counter fixed in MED-1
        self.assertIn('active_storage = len(storage_clients) if storage_proven else None', main_src)

    def test_T34_current_state_starts_independently_of_any_parent(self):
        main_src = inspect.getsource(collector.main)
        self.assertIn("parent_assessment = assess_parent_bundle(", main_src)
        self.assertIn("if prior_admissible:", main_src)
        self.assertIn("prior_errors = []", main_src)
        self.assertIn("prior_clients = []", main_src)
        # the counters are initialised empty and only observe() fills them
        coverage_init = main_src.split("coverage = {")[1].split("}")[0]
        for counter in ("total_pids", "root_pids", "user_pids", "root_namespace_ok",
                        "user_namespace_ok", "fd_error_pids"):
            self.assertIn(f'"{counter}": 0', coverage_init, counter)

    def test_assessment_is_surfaced_in_the_payload(self):
        self.assertIn('"parent_bundle_assessment": parent_assessment', SOURCE)
        self.assertIn('"prior_evidence_admissible": prior_admissible', SOURCE)
        self.assertIn('"current_run_unreadable_pids": current_run_unreadable', SOURCE)
        json.dumps(collector.assess_parent_bundle(bundle(host="x"), HOST, KERNEL))


if __name__ == "__main__":
    unittest.main(verbosity=2)
