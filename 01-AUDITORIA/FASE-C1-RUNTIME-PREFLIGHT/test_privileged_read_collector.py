#!/usr/bin/env python3
"""Unit tests for the privileged read-only collector's identity layer.

No test invokes sudo, the collector itself, systemctl, C1, or a live system
probe.  Every test builds a synthetic sysfs/procfs/debugfs tree in a temporary
directory and points the resolution functions at it, so the real host is never
used as a fixture and the collector is never executed.

Run:  python3 -m unittest test_privileged_read_collector -v
"""
from __future__ import annotations

import ast
import importlib.util
import json
import os
import tempfile
import unittest
from pathlib import Path
from unittest import mock


SCRIPT = Path(__file__).resolve().parent / "privileged_read_collector.py"
SPEC = importlib.util.spec_from_file_location("collector_under_test", SCRIPT)
assert SPEC and SPEC.loader
collector = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(collector)

BDF_GPU = "0000:01:00.0"
BDF_IGPU = "0000:00:02.0"
MOUNTINFO = "{mid} {pid} {majmin} / / rw,relatime shared:1 - ext4 {source} rw\n"


# --------------------------------------------------------------------------
# synthetic tree builders
# --------------------------------------------------------------------------
def add_pci_device(sysfs: Path, bdf: str, vendor: str, device: str, klass: str,
                   driver: str | None, drm_nodes: dict[str, str]) -> Path:
    """Build a sysfs-faithful PCI device with DRM nodes.

    Mirrors the real kernel layout: <pci>/driver -> bus/pci/drivers/<drv>,
    <pci>/drm/<node>/device -> back to the PCI device, and
    /sys/class/drm/<node> -> <pci>/drm/<node>.  The 'device' symlink matters:
    without it the collector could only guess the BDF from the path text and
    could not read the per-node driver.
    """
    base = sysfs / "devices" / "pci0000:00" / bdf
    (base / "drm").mkdir(parents=True, exist_ok=True)
    (base / "vendor").write_text(vendor + "\n", encoding="utf-8")
    (base / "device").write_text(device + "\n", encoding="utf-8")
    (base / "class").write_text(klass + "\n", encoding="utf-8")
    if driver:
        (sysfs / "bus" / "pci" / "drivers" / driver).mkdir(parents=True, exist_ok=True)
        driver_link = sysfs / "bus" / "pci" / "drivers" / driver / bdf
        driver_link.parent.mkdir(parents=True, exist_ok=True)
        if not driver_link.exists():
            driver_link.symlink_to(os.path.relpath(base, driver_link.parent))
        (base / "driver").symlink_to(os.path.relpath(sysfs / "bus" / "pci" / "drivers" / driver, base))
    for node, subdir in drm_nodes.items():
        node_dir = base / "drm" / subdir
        node_dir.mkdir(parents=True, exist_ok=True)
        if driver:
            (node_dir / "driver").symlink_to(
                os.path.relpath(sysfs / "bus" / "pci" / "drivers" / driver, node_dir)
            )
        # <pci>/drm/<node>/device -> the PCI device itself
        (node_dir / "device").symlink_to(os.path.relpath(base, node_dir))
        link = sysfs / "class" / "drm" / node
        link.parent.mkdir(parents=True, exist_ok=True)
        if not link.exists():
            link.symlink_to(os.path.relpath(node_dir, link.parent))
    # forward enumeration: bus/pci/devices/<bdf> -> the same directory
    forward = sysfs / "bus" / "pci" / "devices" / bdf
    forward.parent.mkdir(parents=True, exist_ok=True)
    if not forward.exists():
        forward.symlink_to(os.path.relpath(base, forward.parent))
    return base


def build_sysfs(tmp: Path, *, target_vendor="0x1002", target_device="0x699f",
                target_class="0x030000", target_driver="amdgpu",
                gpu_nodes=("card1", "renderD129"), igpu_nodes=("card0", "renderD128"),
                extra_gpu_card=None, omit_target=False) -> Path:
    """HOST-C-like tree by default; parameters perturb identity or node names."""
    sysfs = tmp / "sys"
    if not omit_target:
        nodes = {node: node for node in gpu_nodes}
        if extra_gpu_card:
            nodes[extra_gpu_card] = extra_gpu_card
        add_pci_device(sysfs, BDF_GPU, target_vendor, target_device, target_class,
                       target_driver, nodes)
    add_pci_device(sysfs, BDF_IGPU, "0x8086", "0x0412", "0x030000", "i915",
                   {node: node for node in igpu_nodes})
    return sysfs


def build_storage(tmp: Path, source: str = "/dev/sdb3", fstype: str = "ext4",
                  extra_mount: str | None = None, disk: str = "sdb",
                  partitions=("sdb1", "sdb2", "sdb3", "sdb4"),
                  neighbours=("sda", "sda2", "zram0")) -> tuple[Path, Path]:
    """Fake /proc/self/mountinfo and /sys/class/block.  Returns (proc, block)."""
    proc = tmp / "proc"
    (proc / "self").mkdir(parents=True, exist_ok=True)
    line = MOUNTINFO.format(mid=44, pid=1, majmin="8:19", source=source)
    if extra_mount:
        line += MOUNTINFO.format(mid=45, pid=1, majmin="0:52", source=extra_mount)
    (proc / "self" / "mountinfo").write_text(line, encoding="utf-8")

    block = tmp / "sys" / "class" / "block"
    block.mkdir(parents=True, exist_ok=True)
    ata = tmp / "sys" / "devices" / "pci0000:00" / "0000:00:1f.2" / "ata5"

    def make(name: str, container: str) -> Path:
        """container is the full parent path below ata/, including block/."""
        target = ata / container / name
        target.mkdir(parents=True, exist_ok=True)
        (target / "device").mkdir(exist_ok=True)
        link = block / name
        if not link.exists():
            link.symlink_to(os.path.relpath(target, block))
        return target

    disk_dir = make(disk, "host4/target4:0:0/4:0:0:0/block")
    for name in partitions:
        if name == disk:
            continue
        # a partition lives *inside* its parent disk directory, as in real sysfs
        part_dir = make(name, f"host4/target4:0:0/4:0:0:0/block/{disk}")
        (part_dir / "partition").write_text("1\n", encoding="utf-8")
    for name in neighbours:
        make(name, "host2/target2:0:0/2:0:0:0/block")
    del disk_dir
    return proc, block


def matrix_context(**overrides):
    context = {
        "gpu_identity": {
            "GPU_IDENTITY_STATUS": "PROVEN",
            "GPU_CARD_NODE": "card1",
            "GPU_RENDER_NODE": "renderD129",
        },
        "root_coverage": {
            "card_complete": True,
            "render_complete": True,
            "user_namespace_complete": True,
            "root_namespace_complete": True,
            "fd_error_count": 0,
            "user_namespace_ok": 280,
            "user_namespace_total": 280,
            "root_namespace_ok": 283,
            "root_namespace_total": 283,
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


# ==========================================================================
# 1-2  syntax and importability
# ==========================================================================
class SyntaxAndImportTests(unittest.TestCase):
    def test_01_module_parses_and_imports_without_executing(self):
        source = SCRIPT.read_text(encoding="utf-8")
        ast.parse(source)
        self.assertIsNone(collector.PARENT_PATH, "argv must not be required to import")
        self.assertEqual(collector.PREFLIGHT_ID, "UNSPECIFIED")
        self.assertEqual(collector.GPU_PCI_TARGET["bdf"], BDF_GPU)
        for name in (
            "pci_identity", "discover_drm_nodes", "resolve_gpu_identity",
            "debugfs_client_attribution", "parse_mountinfo", "resolve_block_device",
            "resolve_storage_identity", "scan_maps", "compositor_gpu_relation",
            "ownership_matrix", "abort_payload",
        ):
            self.assertTrue(callable(getattr(collector, name, None)), name)

    def test_02_legacy_static_identifiers_are_gone(self):
        source = SCRIPT.read_text(encoding="utf-8")
        for absent in ('DEVICES = {"/dev/dri/card1"', 'SDA_PREFIX = "/dev/sda"',
                       'Path("/sys/block/sda', '"/dev/dri/card1", "/dev/dri/renderD129"'):
            self.assertNotIn(absent, source, absent)


# ==========================================================================
# 4-6  PCI -> DRM resolution
# ==========================================================================
class PciToDrmResolutionTests(unittest.TestCase):
    def test_04_pci_identity_resolves_to_card_and_render(self):
        with tempfile.TemporaryDirectory() as raw:
            sysfs = build_sysfs(Path(raw))
            identity = collector.resolve_gpu_identity(sysfs_root=sysfs)
        self.assertEqual(identity["GPU_IDENTITY_STATUS"], "PROVEN")
        self.assertEqual(identity["GPU_VENDOR"], "0x1002")
        self.assertEqual(identity["GPU_DEVICE"], "0x699f")
        self.assertEqual(identity["GPU_DRIVER"], "amdgpu")
        self.assertEqual(identity["GPU_CARD_NODE"], "card1")
        self.assertEqual(identity["GPU_RENDER_NODE"], "renderD129")
        self.assertEqual(identity["GPU_CARD_MINOR"], 1)
        self.assertEqual(identity["GPU_RENDER_MINOR"], 129)
        self.assertEqual(
            identity["devices"], {"/dev/dri/card1", "/dev/dri/renderD129"}
        )
        discovery = identity["drm_discovery"]
        self.assertTrue(discovery["agreement"], "forward and reverse must agree")
        excluded = {item["node"] for item in discovery["reverse"]["excluded"]}
        self.assertEqual(excluded, {"card0", "renderD128"}, "Intel must be excluded explicitly")
        for item in discovery["reverse"]["excluded"]:
            self.assertEqual(item["resolved_bdf"], BDF_IGPU)
            self.assertEqual(item["driver"], "i915")

    def test_05_card_index_different_from_card1(self):
        with tempfile.TemporaryDirectory() as raw:
            sysfs = build_sysfs(
                Path(raw), gpu_nodes=("card0", "renderD128"),
                igpu_nodes=("card1", "renderD129"),
            )
            identity = collector.resolve_gpu_identity(sysfs_root=sysfs)
        self.assertEqual(identity["GPU_IDENTITY_STATUS"], "PROVEN")
        self.assertEqual(identity["GPU_CARD_NODE"], "card0")
        self.assertEqual(identity["GPU_CARD_MINOR"], 0)
        self.assertEqual(identity["GPU_RENDER_NODE"], "renderD128")
        self.assertNotIn("/dev/dri/card1", identity["devices"])
        # the Intel card1 is recorded as excluded, never adopted
        excluded = {item["node"]: item["resolved_bdf"] for item in identity["drm_discovery"]["reverse"]["excluded"]}
        self.assertEqual(excluded["card1"], BDF_IGPU)
        self.assertEqual(excluded["renderD129"], BDF_IGPU)

    def test_06_render_minor_different_from_129(self):
        with tempfile.TemporaryDirectory() as raw:
            sysfs = build_sysfs(Path(raw), gpu_nodes=("card2", "renderD137"))
            identity = collector.resolve_gpu_identity(sysfs_root=sysfs)
        self.assertEqual(identity["GPU_IDENTITY_STATUS"], "PROVEN")
        self.assertEqual(identity["GPU_RENDER_MINOR"], 137)
        self.assertEqual(identity["GPU_CARD_MINOR"], 2)
        self.assertIn("/dev/dri/renderD137", identity["devices"])
        self.assertNotIn("/dev/dri/renderD129", identity["devices"])


# ==========================================================================
# 7-8  storage identity
# ==========================================================================
class StorageIdentityTests(unittest.TestCase):
    def test_07_sda_present_but_not_the_root_filesystem(self):
        with tempfile.TemporaryDirectory() as raw:
            proc, block = build_storage(Path(raw), source="/dev/sdb3")
            # a fake /proc/diskstats where sda exists with plausible counters
            diskstats = proc / "diskstats"
            rows = [
                "  8 0 100 0 2000 300 0 0 0 0 100 200 ".split(),
                "  8 16 5 0 500 600 0 0 0 0 50 60 ".split(),
            ]
            lines = []
            for fields in rows:
                parts = list(fields)
                parts.insert(2, "sda" if parts[2] == "0" else "sda2")
                lines.append(" ".join(parts))
            for name, base in (("sdb", 0), ("sdb1", 0), ("sdb2", 0), ("sdb3", 700), ("sdb4", 0), ("zram0", 0)):
                lines.append(
                    f"   8 {['0','16','17','18','19','0'][len(name)-3] if name!='sdb' else '0'} "
                    f"{name} {base*10} 0 {base*100} 5 0 0 0 0 {base} {base*2} 0 {base*3} 0"
                )
            diskstats.write_text("\n".join(lines) + "\n", encoding="utf-8")

            storage = collector.resolve_storage_identity(proc_root=proc, block_root=block)
            parsed = collector.parse_diskstats(storage["STORAGE_DISKSTATS_NAMES"], proc_root=proc)
        self.assertEqual(storage["STORAGE_IDENTITY_STATUS"], "PROVEN")
        self.assertEqual(storage["ROOT_SOURCE"], "/dev/sdb3")
        self.assertEqual(storage["ROOT_BLOCK_DEVICE"], "sdb3")
        self.assertEqual(storage["ROOT_BLOCK_PARENT"], "sdb")
        self.assertTrue(storage["ROOT_IS_PARTITION"])
        self.assertIn("sdb3", storage["STORAGE_DISKSTATS_NAMES"])
        self.assertNotIn("sda", storage["STORAGE_DISKSTATS_NAMES"])
        self.assertNotIn("sda2", storage["STORAGE_DISKSTATS_NAMES"])
        self.assertNotIn("zram0", storage["STORAGE_DISKSTATS_NAMES"])
        self.assertNotIn("sda", parsed, "neighbouring disk must never contribute numbers")
        self.assertNotIn("sda2", parsed)
        self.assertIn("sdb3", parsed)

    def test_08_root_filesystem_on_another_device(self):
        with tempfile.TemporaryDirectory() as raw:
            proc, block = build_storage(
                Path(raw), source="/dev/nvme0n1p3", disk="nvme0n1",
                partitions=("nvme0n1p1", "nvme0n1p2", "nvme0n1p3"),
            )
            storage = collector.resolve_storage_identity(proc_root=proc, block_root=block)
        self.assertEqual(storage["STORAGE_IDENTITY_STATUS"], "PROVEN")
        self.assertEqual(storage["ROOT_SOURCE"], "/dev/nvme0n1p3")
        self.assertEqual(storage["ROOT_BLOCK_PARENT"], "nvme0n1")
        self.assertIn("nvme0n1p3", storage["STORAGE_DISKSTATS_NAMES"])
        self.assertNotIn("sdb3", storage["STORAGE_DISKSTATS_NAMES"])

    def test_08b_stacked_root_mount_is_not_proven(self):
        with tempfile.TemporaryDirectory() as raw:
            proc, block = build_storage(Path(raw), extra_mount="overlay")
            storage = collector.resolve_storage_identity(proc_root=proc, block_root=block)
        self.assertEqual(storage["STORAGE_IDENTITY_STATUS"], "NOT_PROVEN")
        self.assertEqual(storage["STORAGE_IDENTITY_ABORT"], "AMBIGUOUS_ROOT_MOUNT")

    def test_08c_non_dev_source_is_not_proven(self):
        with tempfile.TemporaryDirectory() as raw:
            proc, block = build_storage(Path(raw), source="tmpfs")
            storage = collector.resolve_storage_identity(proc_root=proc, block_root=block)
        self.assertEqual(storage["STORAGE_IDENTITY_STATUS"], "NOT_PROVEN")
        self.assertIn("SOURCE_NOT_A_DEV_PATH", storage["STORAGE_IDENTITY_ABORT"])


# ==========================================================================
# 9-11  abort conditions
# ==========================================================================
class AbortConditionTests(unittest.TestCase):
    def test_09_multiple_card_candidates_for_one_bdf(self):
        with tempfile.TemporaryDirectory() as raw:
            sysfs = build_sysfs(Path(raw), extra_gpu_card="card2")
            identity = collector.resolve_gpu_identity(sysfs_root=sysfs)
        self.assertEqual(identity["GPU_IDENTITY_STATUS"], "NOT_PROVEN")
        self.assertEqual(identity["GPU_IDENTITY_ABORT"], "IDENTITY_NOT_PROVEN")
        self.assertEqual(identity["drm_discovery"]["DRM_DISCOVERY_ABORT"], "AMBIGUOUS_CANDIDATE")
        self.assertEqual(identity["GPU_CARD_NODE"], None)
        self.assertEqual(identity["devices"], set())

    def test_09b_direction_disagreement_is_not_proven(self):
        """A node the kernel enumerates but class/drm does not expose."""
        with tempfile.TemporaryDirectory() as raw:
            sysfs = build_sysfs(Path(raw))
            os.unlink(sysfs / "class" / "drm" / "renderD129")
            identity = collector.resolve_gpu_identity(sysfs_root=sysfs)
        self.assertEqual(identity["GPU_IDENTITY_STATUS"], "NOT_PROVEN")
        self.assertEqual(
            identity["drm_discovery"]["DRM_DISCOVERY_ABORT"], "DIRECTION_DISAGREEMENT"
        )
        self.assertFalse(identity["drm_discovery"]["agreement"])
        self.assertEqual(identity["GPU_RENDER_NODE"], None)

    def test_10_incorrect_pci_identity_aborts_before_any_node_is_used(self):
        with tempfile.TemporaryDirectory() as raw:
            sysfs = build_sysfs(Path(raw), target_device="0x687f")
            identity = collector.resolve_gpu_identity(sysfs_root=sysfs)
        self.assertEqual(identity["pci_identity"]["PCI_IDENTITY_STATUS"], "MISMATCH")
        self.assertEqual(identity["GPU_IDENTITY_STATUS"], "NOT_PROVEN")
        self.assertEqual(identity["GPU_IDENTITY_ABORT_DETAIL"], "PCI_IDENTITY_MISMATCH")
        self.assertEqual(identity["GPU_IDENTITY_ABORT_STAGE"], "PCI")
        self.assertEqual(identity["GPU_CARD_NODE"], None)
        self.assertEqual(identity["devices"], set(), "no node may be used unproven")

    def test_10b_wrong_driver_aborts(self):
        with tempfile.TemporaryDirectory() as raw:
            sysfs = build_sysfs(Path(raw), target_driver="radeonsi")
            identity = collector.resolve_gpu_identity(sysfs_root=sysfs)
        self.assertEqual(identity["GPU_IDENTITY_STATUS"], "NOT_PROVEN")
        self.assertTrue(
            any("driver=" in item for item in identity["pci_identity"]["mismatches"]),
            identity["pci_identity"]["mismatches"],
        )
        self.assertEqual(identity["devices"], set())

    def test_11_absent_identity_aborts(self):
        with tempfile.TemporaryDirectory() as raw:
            sysfs = Path(raw) / "sys"
            sysfs.mkdir()
            identity = collector.resolve_gpu_identity(sysfs_root=sysfs)
        self.assertEqual(identity["GPU_IDENTITY_STATUS"], "NOT_PROVEN")
        self.assertEqual(identity["pci_identity"]["PCI_IDENTITY_ABORT"], "PCI_DEVICE_PATH_ABSENT")
        self.assertEqual(identity["GPU_CARD_NODE"], None)
        self.assertEqual(identity["GPU_RENDER_MINOR"], None)

    def test_11b_absent_gpu_but_present_igpu_is_still_not_proven(self):
        with tempfile.TemporaryDirectory() as raw:
            sysfs = build_sysfs(Path(raw), omit_target=True)
            identity = collector.resolve_gpu_identity(sysfs_root=sysfs)
        self.assertEqual(identity["GPU_IDENTITY_STATUS"], "NOT_PROVEN")
        self.assertEqual(identity["GPU_CARD_NODE"], None)
        self.assertEqual(identity["devices"], set())


# ==========================================================================
# 12  debugfs minor derivation
# ==========================================================================
class DebugfsDerivationTests(unittest.TestCase):
    def _identity(self, raw, render="renderD129"):
        sysfs = build_sysfs(Path(raw), gpu_nodes=("card1", render))
        return collector.resolve_gpu_identity(sysfs_root=sysfs)

    def _debugfs(self, raw, minor, files):
        root = Path(raw) / "debug"
        directory = root / "dri" / str(minor)
        directory.mkdir(parents=True, exist_ok=True)
        for name in files:
            (directory / name).write_text("x\n", encoding="utf-8")
        return root

    def test_12_minor_is_derived_from_the_discovered_render_node(self):
        with tempfile.TemporaryDirectory() as raw:
            identity = self._identity(raw)
            debug = self._debugfs(raw, 129, ["clients", "amdgpu_dfs_stat", "amdgpu_pm_info"])
            result = collector.debugfs_client_attribution(identity, debug_root=debug)
        self.assertEqual(result["DEBUGFS_CLIENT_ATTRIBUTION"], "PROVEN")
        self.assertEqual(result["candidate_minor"], 129)
        self.assertEqual(result["clients_path"], str(debug / "dri" / "129" / "clients"))
        self.assertIn("amdgpu_dfs_stat", result["driver_marker_files"])
        self.assertEqual(result["amdgpu_device_count"], 1)
        self.assertIn("render node renderD129", result["derivation"])

    def test_12b_a_foreign_dri_1_is_never_adopted(self):
        """debugfs carries dri/1 for another device; the RX550 minor is 129."""
        with tempfile.TemporaryDirectory() as raw:
            identity = self._identity(raw)
            debug = self._debugfs(raw, 1, ["clients", "i915_display_info"])
            result = collector.debugfs_client_attribution(identity, debug_root=debug)
        self.assertEqual(result["DEBUGFS_CLIENT_ATTRIBUTION"], "NOT_AVAILABLE")
        self.assertEqual(result["candidate_minor"], 129)
        self.assertEqual(result["reason"], "DEBUGFS_DRI_MINOR_ABSENT")
        self.assertIsNone(result["clients_path"])
        self.assertNotIn("/dri/1/", str(result["clients_path"]))

    def test_12d_own_minor_without_amdgpu_marker_is_refused(self):
        with tempfile.TemporaryDirectory() as raw:
            identity = self._identity(raw)
            debug = self._debugfs(raw, 129, ["clients", "i915_display_info"])
            result = collector.debugfs_client_attribution(identity, debug_root=debug)
        self.assertEqual(result["DEBUGFS_CLIENT_ATTRIBUTION"], "NOT_AVAILABLE")
        self.assertEqual(result["reason"], "DEBUGFS_NO_DRIVER_MARKER")
        self.assertIsNone(result["clients_path"])
        self.assertEqual(result["candidate_minor"], 129)

    def test_12c_minor_follows_a_renumbered_render_node(self):
        with tempfile.TemporaryDirectory() as raw:
            identity = self._identity(raw, render="renderD137")
            debug = self._debugfs(raw, 137, ["clients", "amdgpu_dfs_stat"])
            result = collector.debugfs_client_attribution(identity, debug_root=debug)
        self.assertEqual(result["DEBUGFS_CLIENT_ATTRIBUTION"], "PROVEN")
        self.assertIn("/dri/137/clients", result["clients_path"])


# ==========================================================================
# 13  /proc/<pid>/maps permission handling
# ==========================================================================
class ProcMapsTests(unittest.TestCase):
    def test_13_permission_denied_is_not_absence(self):
        with mock.patch.object(Path, "open", side_effect=PermissionError(13, "denied")):
            result = collector.scan_maps(4242, proc_root=Path("/proc"))
        self.assertTrue(result["MAPS_PERMISSION_DENIED"])
        self.assertFalse(result["MAPS_READABLE"])
        self.assertEqual(result["MAPS_STATUS"], "PERMISSION_DENIED")
        self.assertNotEqual(result["MAPS_STATUS"], "ABSENT")
        self.assertIn("PermissionError", result["MAPS_ERROR"])

    def test_13b_absent_maps_is_reported_as_absent(self):
        with tempfile.TemporaryDirectory() as raw:
            result = collector.scan_maps(1, proc_root=Path(raw))
        self.assertEqual(result["MAPS_STATUS"], "ABSENT")
        self.assertFalse(result["MAPS_PERMISSION_DENIED"])
        self.assertFalse(result["MAPS_READABLE"])

    def test_13c_readable_maps_keep_only_relevant_lines(self):
        with tempfile.TemporaryDirectory() as raw:
            pid_dir = Path(raw) / "1234"
            pid_dir.mkdir()
            (pid_dir / "maps").write_text(
                "7f00-7f10 r-xp 00000000 08:01 10 /usr/lib64/libdrm_amdgpu.so.1\n"
                "7f10-7f20 rw-p 00000000 08:01 11 /usr/lib64/libgbm.so.1\n"
                "7f20-7f30 r--p 00000000 08:01 12 /usr/lib/systemd/systemd\n",
                encoding="utf-8",
            )
            result = collector.scan_maps(1234, proc_root=Path(raw))
        self.assertTrue(result["MAPS_READABLE"])
        self.assertEqual(result["MAPS_STATUS"], "READABLE")
        self.assertEqual(result["line_count"], 3)
        self.assertEqual(result["relevant_count"], 2)
        self.assertTrue(any("libdrm_amdgpu" in line for line in result["relevant_lines"]))
        self.assertFalse(any("systemd" in line for line in result["relevant_lines"]))

    def test_13d_other_errors_do_not_become_permission_denied(self):
        with mock.patch.object(Path, "open", side_effect=OSError(5, "I/O error")):
            result = collector.scan_maps(7, proc_root=Path("/proc"))
        self.assertEqual(result["MAPS_STATUS"], "ERROR")
        self.assertFalse(result["MAPS_PERMISSION_DENIED"])
        self.assertFalse(result["MAPS_READABLE"])


# ==========================================================================
# 14  debugfs absence
# ==========================================================================
class DebugfsAbsenceTests(unittest.TestCase):
    def test_14_absent_debugfs_is_not_available_not_invented(self):
        with tempfile.TemporaryDirectory() as raw:
            identity = collector.resolve_gpu_identity(sysfs_root=build_sysfs(Path(raw)))
            result = collector.debugfs_client_attribution(identity, debug_root=Path(raw) / "no-debugfs")
        self.assertEqual(result["DEBUGFS_CLIENT_ATTRIBUTION"], "NOT_AVAILABLE")
        self.assertEqual(result["reason"], "DEBUGFS_DRI_MINOR_ABSENT")
        self.assertIsNone(result["clients_path"])
        self.assertNotIn("clients", str(result.get("dri_dir")))

    def test_14b_unproven_gpu_identity_short_circuits_debugfs(self):
        identity = {"GPU_IDENTITY_STATUS": "NOT_PROVEN", "GPU_RENDER_MINOR": None}
        with tempfile.TemporaryDirectory() as raw:
            debug = Path(raw) / "debug"
            (debug / "dri" / "129").mkdir(parents=True)
            (debug / "dri" / "129" / "clients").write_text("x\n", encoding="utf-8")
            (debug / "dri" / "129" / "amdgpu_dfs_stat").write_text("x\n", encoding="utf-8")
            result = collector.debugfs_client_attribution(identity, debug_root=debug)
        self.assertEqual(result["DEBUGFS_CLIENT_ATTRIBUTION"], "NOT_AVAILABLE")
        self.assertEqual(result["reason"], "GPU_IDENTITY_NOT_PROVEN")
        self.assertIsNone(result["clients_path"])


# ==========================================================================
# 15  the ownership boolean never replaces the 11-condition matrix
# ==========================================================================
class OwnershipAuthorityTests(unittest.TestCase):
    def test_15_boolean_true_does_not_yield_full(self):
        """Legacy boolean would be True; the matrix must still refuse FULL."""
        result = collector.ownership_matrix(matrix_context())
        self.assertEqual(result["COLLECTOR_OWNERSHIP_BOOLEAN"], "NON_AUTHORITATIVE")
        self.assertEqual(len(result["conditions"]), 11)
        by_key = {row["condition"]: row for row in result["conditions"]}
        self.assertEqual(by_key["writers_resolved"]["STATE"], "NOT_EVALUATED")
        self.assertEqual(by_key["writers_resolved"]["ROUTE"], "R2")
        self.assertEqual(by_key["guard_and_restore"]["STATE"], "NOT_EVALUATED")
        self.assertEqual(by_key["guard_and_restore"]["ROUTE"], "R3")
        self.assertEqual(result["OWNERSHIP_CRITERION_STATE"], "PARTIAL")
        self.assertGreaterEqual(result["not_evaluated_count"], 2)

    def test_15b_boolean_false_does_not_change_the_matrix(self):
        good = collector.ownership_matrix(matrix_context())
        bad_context = matrix_context(
            root_coverage=dict(
                matrix_context()["root_coverage"],
                card_complete=False, render_complete=False, fd_error_count=17,
                root_namespace_complete=False, user_namespace_complete=False,
            )
        )
        bad = collector.ownership_matrix(bad_context)
        self.assertNotEqual(
            [row["STATE"] for row in good["conditions"]],
            [row["STATE"] for row in bad["conditions"]],
        )
        self.assertEqual(len(bad["conditions"]), 11)
        self.assertEqual(bad["OWNERSHIP_CRITERION_STATE"], "PARTIAL")
        by_key = {row["condition"]: row for row in bad["conditions"]}
        self.assertEqual(by_key["card_node_complete"]["STATE"], "FAIL")
        # drm_fds_enumerated is no longer scored on fd_error_count, so a large
        # error count alone does not change it.  What must change is the matrix.
        good_by_key = {
            row["condition"]: row
            for row in collector.ownership_matrix(matrix_context())["conditions"]
        }
        self.assertEqual(
            by_key["drm_fds_enumerated"]["STATE"],
            good_by_key["drm_fds_enumerated"]["STATE"],
        )
        self.assertNotEqual(
            by_key["card_node_complete"]["STATE"],
            good_by_key["card_node_complete"]["STATE"],
        )

    def test_15c_debugfs_not_available_stays_unknown_never_pass(self):
        context = matrix_context(
            debugfs={"DEBUGFS_CLIENT_ATTRIBUTION": "NOT_AVAILABLE",
                     "reason": "DEBUGFS_PERMISSION_DENIED", "clients_path": None}
        )
        result = collector.ownership_matrix(context)
        by_key = {row["condition"]: row for row in result["conditions"]}
        self.assertEqual(by_key["clients_pasid_attributable"]["STATE"], "UNKNOWN")
        self.assertEqual(result["OWNERSHIP_CRITERION_STATE"], "PARTIAL")

    def test_15d_abort_payload_has_no_ownership_evidence(self):
        with tempfile.TemporaryDirectory() as raw:
            sysfs = build_sysfs(Path(raw), target_device="0x687f")
            identity = collector.resolve_gpu_identity(sysfs_root=sysfs)
            payload = collector.abort_payload(
                identity["GPU_IDENTITY_ABORT"], identity["GPU_IDENTITY_ABORT_DETAIL"], "IDENTITY_STAGE_PCI"
            )
        self.assertEqual(payload["COLLECTOR_STATUS"], "ABORTED")
        self.assertNotIn("ownership", payload)
        self.assertFalse(payload["ownership_evidence_collected"])
        json.dumps(payload)  # must stay serialisable


# ==========================================================================
# extra  compositor relation and capability register integrity
# ==========================================================================
class CompositorAndCapabilityTests(unittest.TestCase):
    def test_compositor_relation_never_infers_gpu_usage(self):
        # a compositor holding an FD on the proven node
        observed = collector.compositor_gpu_relation("kwin_wayland", "kwin_wayland", {"/dev/dri/renderD129"}, [])
        self.assertEqual(observed["KWIN_GPU_RELATION"], "OBSERVED")
        # a compositor holding an FD only on the *other* GPU
        other = collector.compositor_gpu_relation("kwin_wayland", "kwin_wayland", [], {"/dev/dri/renderD128"})
        self.assertEqual(other["KWIN_GPU_RELATION"], "UNKNOWN")
        self.assertEqual(other["other_drm_targets"], ["/dev/dri/renderD128"])
        # a compositor with no DRM FD at all
        none = collector.compositor_gpu_relation("kwin_wayland", "kwin_wayland", [], [])
        self.assertEqual(none["KWIN_GPU_RELATION"], "UNKNOWN")
        # a non-compositor is not classified at all
        self.assertIsNone(collector.compositor_gpu_relation("bash", "bash", {"/dev/dri/renderD129"}, []))

    def test_capability_matrix_names_real_code(self):
        source = SCRIPT.read_text(encoding="utf-8")
        tree = ast.parse(source)
        defined = {
            node.name for node in tree.body if isinstance(node, ast.FunctionDef)
        }
        self.assertEqual(len(collector.CAPABILITY_MATRIX), 11)
        for row in collector.CAPABILITY_MATRIX:
            self.assertTrue(row["implemented"], row["capability"])
            self.assertIn(row["source"], defined, f"{row['capability']} names missing {row['source']}")
            for key in ("capability", "source", "dynamic_identity", "privilege", "limitation"):
                self.assertIn(key, row)

    def test_criterion_rows_are_exactly_eleven_and_two_are_external(self):
        self.assertEqual(len(collector.OWNERSHIP_CRITERION_ROWS), 11)
        self.assertEqual(len(collector.OWNERSHIP_EXTERNAL_ROWS), 2)
        self.assertEqual(
            sorted(collector.OWNERSHIP_EXTERNAL_ROWS), ["guard_and_restore", "writers_resolved"]
        )


# ==========================================================================
# extra  GAP 11: read-only proof by AST, not by regex
# ==========================================================================

# ==========================================================================
# extra  GAP 11: read-only proof by AST, not by regex
# ==========================================================================
# The static regex scan used during the review produced false positives on
# prose, JSON keys and string formatting, so the read-only claim is proved on
# the abstract syntax tree instead: only real call targets are inspected.

FORBIDDEN_CALLS = {
    "write", "writelines", "write_text", "write_bytes", "truncate", "unlink",
    "rmdir", "chmod", "chown", "touch", "mkdir", "makedirs", "remove",
    "symlink", "symlink_to", "hardlink_to", "link", "kill", "killpg",
    "setuid", "setgid", "mkstemp", "mkdtemp", "rmtree", "copy", "copy2",
    "copyfile", "move", "utime", "chflags", "lchmod",
}
# str / dict / Path methods that cannot change system state.  They are listed
# explicitly so that a real mutation cannot hide behind a permissive
# exclusion; 'replace' in this collector only strips NUL from a cmdline.
ALLOWED_STR_METHODS = {
    "replace", "startswith", "endswith", "split", "rsplit", "rfind", "find",
    "join", "strip", "lstrip", "rstrip", "format", "get", "read", "count",
    "index", "append", "extend", "update", "keys", "values", "items",
    "setdefault", "clear", "copy", "encode", "decode", "hexdigest", "realpath",
    "read_text", "read_bytes", "readlink", "listdir", "iterdir", "glob",
    # existence checks added with HIGH-1: they read metadata, never mutate
    "is_file", "is_dir", "isdir", "is_symlink", "exists", "stat", "islink",
    "lexists", "resolve", "name",
    "parent", "stem", "with_name", "relative_to", "as_posix", "fspath",
    "isoformat", "timestamp", "monotonic", "sleep", "sorted", "splitlines",
    "split", "rsplit", "lower", "upper", "strip", "lstrip", "rstrip",
    "isdigit", "startswith", "endswith", "join", "replace", "format", "get",
    "keys", "values", "items", "add", "discard", "update", "append",
    "extend", "pop", "count", "index", "find", "rfind", "group", "groups",
    "search", "match", "fullmatch", "finditer", "findall", "compile", "sub",
    "geteuid", "getegid", "getuid", "getgid",
    "basename", "dirname",
    "uname", "access", "now", "utcnow", "today", "fromisoformat", "sha256",
    "format_exc", "print_exception", "dumps", "loads", "open", "min", "max",
    "abs", "round", "len", "sum", "any", "all", "sorted", "reversed", "zip",
    "enumerate", "range",
}
# Bare builtins only.  re.compile() and Path.read_text() are attributes and
# are audited separately by the allowlist test, so they are not listed here.
FORBIDDEN_BUILTINS = {
    "eval", "exec", "compile", "__import__", "input", "breakpoint", "exit",
    "quit", "globals", "locals", "vars", "memoryview",
}
FORBIDDEN_SUBPROCESS_HEADS = {
    "sudo", "su", "kill", "pkill", "killall", "modprobe", "rmmod", "mount",
    "umount", "umount2", "swapon", "swapoff", "tee", "nsenter", "unshare",
    "chown", "chmod", "dd", "shred", "wipefs", "sgdisk", "parted", "fdisk",
    "mkfs", "insmod", "setpci", "nvme", "sh", "bash", "zsh", "env", "eval",
    "systemctl-daemon", "udevadm", "hwclock", "rtcwake", "suspend", "swapoff",
}
# systemctl verbs that only read.  Anything else is a mutation.
READONLY_SYSTEMCTL_VERBS = {
    "show", "status", "list-units", "cat", "is-active", "is-enabled",
    "show-environment", "list-timers", "list-dependencies", "list-unit-files",
    "get-default", "list-jobs",
}
FUSER_KILL_FLAGS = {"-k", "-SIG", "--kill"}
MUTATING_SUBSYSTEMS = {"ioctl", "fcntl", "termios", "pty", "resource", "signal"}
READONLY_SUBSYSTEM_MODULES = {
    "ast", "datetime", "hashlib", "importlib.util", "json", "os", "re",
    "subprocess", "sys", "time", "pathlib", "unittest", "tempfile", "mock",
    "traceback", "__future__",
}


class ReadOnlyProofTests(unittest.TestCase):
    """GAP 11.  Every claim below is derived from the AST of the collector."""

    def setUp(self):
        self.tree = ast.parse(SCRIPT.read_text(encoding="utf-8"))
        self.calls = [
            node for node in ast.walk(self.tree) if isinstance(node, ast.Call)
        ]
        self.run_calls = [
            node for node in self.calls
            if isinstance(node.func, ast.Name) and node.func.id == "run"
        ]

    def test_no_mutating_or_unclassified_attribute_calls(self):
        # The audited run() wrapper is the one place allowed to name
        # subprocess.run; every other attribute call must be classified.
        wrapper = next(
            node for node in self.tree.body
            if isinstance(node, ast.FunctionDef) and node.name == "run"
        )
        wrapper_lines = range(wrapper.lineno, (wrapper.end_lineno or wrapper.lineno) + 1)
        offenders, allowed = [], set()
        for node in self.calls:
            if not isinstance(node.func, ast.Attribute):
                continue
            if node.lineno in wrapper_lines:
                continue
            name = node.func.attr
            if name in FORBIDDEN_CALLS:
                offenders.append((node.lineno, name))
            elif name not in ALLOWED_STR_METHODS:
                offenders.append((node.lineno, f"UNCLASSIFIED:{name}"))
            else:
                allowed.add(name)
        self.assertEqual(offenders, [], f"mutating or unclassified: {offenders}")
        self.assertIn("replace", allowed, "str.replace is expected and accounted for")

    def test_no_dynamic_execution_primitives(self):
        offenders = []
        for node in self.calls:
            if isinstance(node.func, ast.Name) and node.func.id in FORBIDDEN_BUILTINS:
                offenders.append((node.lineno, node.func.id))
        self.assertEqual(offenders, [], f"dynamic execution: {offenders}")

    def test_subprocess_is_only_reached_through_the_readonly_wrapper(self):
        """Every subprocess call must go through run(), which is audited."""
        wrapper = next(
            node for node in self.tree.body
            if isinstance(node, ast.FunctionDef) and node.name == "run"
        )
        wrapper_lines = range(wrapper.lineno, (wrapper.end_lineno or wrapper.lineno) + 1)
        for node in self.calls:
            if node.lineno in wrapper_lines:
                continue  # the audited wrapper itself
            if not (isinstance(node.func, ast.Attribute)
                    and node.func.attr in ("run", "Popen", "call", "check_call",
                                           "check_output", "getoutput", "getstatusoutput")):
                continue
            if isinstance(node.func.value, ast.Name) and node.func.value.id == "subprocess":
                self.fail(f"line {node.lineno}: direct subprocess call bypassing run()")
        self.assertGreater(len(self.run_calls), 0)

    def test_every_open_uses_read_mode_only(self):
        """Covers the builtin open() and Path.open()/io.open() alike."""
        found = 0
        for node in self.calls:
            is_builtin = isinstance(node.func, ast.Name) and node.func.id == "open"
            is_method = isinstance(node.func, ast.Attribute) and node.func.attr == "open"
            if not (is_builtin or is_method):
                continue
            found += 1
            modes = [
                arg.value for arg in node.args
                if isinstance(arg, ast.Constant) and isinstance(arg.value, str)
            ]
            for mode in modes:
                self.assertNotRegex(mode, r"[wax+]", f"line {node.lineno}: {mode!r}")
        self.assertGreater(found, 0, "no open() call found to audit")
        # every file read in the collector is explicitly binary-read
        self.assertTrue(
            any(
                isinstance(node.func, ast.Attribute) and node.func.attr == "open"
                and any(
                    isinstance(arg, ast.Constant) and arg.value == "rb"
                    for arg in node.args
                )
                for node in self.calls
            ),
            "expected an explicit read-binary open",
        )

    def test_subprocess_commands_are_read_only(self):
        self.assertGreater(len(self.run_calls), 0, "no subprocess call found to audit")
        for node in self.run_calls:
            strings = [
                arg.value for arg in ast.walk(node)
                if isinstance(arg, ast.Constant) and isinstance(arg.value, str)
            ]
            heads = [os.path.basename(item) for item in strings]
            for head in heads:
                self.assertNotIn(head, FORBIDDEN_SUBPROCESS_HEADS, f"line {node.lineno}: {head}")
            if "systemctl" in heads:
                verbs = {item for item in strings if item in READONLY_SYSTEMCTL_VERBS}
                self.assertTrue(
                    verbs, f"line {node.lineno}: systemctl without a read-only verb"
                )
            if "fuser" in heads:
                self.assertFalse(
                    FUSER_KILL_FLAGS & set(strings),
                    f"line {node.lineno}: fuser invoked with a signalling flag",
                )

    def test_no_mutating_syscalls_via_os_or_pathlib(self):
        forbidden = {
            "system", "popen", "spawnl", "spawnv", "execv", "fork", "removedirs",
            "rmdir", "symlink", "link", "chmod", "chown", "truncate", "kill",
            "setpriority", "sched_setscheduler", "nice", "sync", "fsync",
            "replace", "rename", "renames", "remove", "unlink", "makedirs",
            "mkdir", "write", "write_text", "write_bytes", "utime", "chflags",
        }
        for node in self.calls:
            if not isinstance(node.func, ast.Attribute):
                continue
            owner = getattr(node.func.value, "id", None)
            if owner not in ("os", "Path"):
                continue
            self.assertNotIn(
                node.func.attr, forbidden,
                f"line {node.lineno}: {owner}.{node.func.attr}",
            )

    def test_sudo_never_appears_as_an_executed_command(self):
        for node in self.run_calls:
            for arg in ast.walk(node):
                if isinstance(arg, ast.Constant) and arg.value == "sudo":
                    self.fail(f"line {node.lineno}: collector invokes sudo")

    def test_no_mutating_subsystem_is_imported(self):
        imported = set()
        for node in ast.walk(self.tree):
            if isinstance(node, ast.Import):
                imported.update(alias.name.split(".")[0] for alias in node.names)
            elif isinstance(node, ast.ImportFrom) and node.module:
                imported.add(node.module.split(".")[0])
        self.assertEqual(imported & MUTATING_SUBSYSTEMS, set())
        self.assertTrue(
            imported <= READONLY_SUBSYSTEM_MODULES,
            f"unexpected imports: {imported - READONLY_SUBSYSTEM_MODULES}",
        )

    def test_read_queue_and_pm_snapshot_degrade_without_identity(self):
        queue = collector.read_queue(None)
        self.assertEqual(queue["STORAGE_METRICS"], "SKIPPED_IDENTITY_NOT_PROVEN")
        self.assertEqual(queue["queue"], {})
        pm = collector.pm_snapshot(None)
        self.assertEqual(pm["PM_METRICS"], "SKIPPED_IDENTITY_NOT_PROVEN")
        self.assertEqual(pm["paths"], {})

    def test_parse_diskstats_with_unproven_storage_reads_nothing(self):
        self.assertEqual(collector.parse_diskstats([]), {})
        self.assertEqual(collector.parse_diskstats(None), {})

    def test_main_refuses_to_run_without_collector_arguments(self):
        """Importing must never turn into a collection."""
        self.assertFalse(collector._ARGV_IS_COLLECTOR_ARGS)
        with self.assertRaises(SystemExit):
            collector.main()


if __name__ == "__main__":
    unittest.main(verbosity=2)
