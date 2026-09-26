#!/usr/bin/env python3
"""Behavioral tests for DEFECT-05 (storage whole-disk attribute base).

DEFECT-05: resolve_block_device() correctly resolves the parent disk and already
computes `parent_sysfs` (e.g. /sys/class/block/sdb).  Both consumers of
whole-disk attributes ignored it and used ROOT_BLOCK_SYSFS, which names the
*partition* (/sys/class/block/sdb3):

  * read_queue()      -> /sys/class/block/sdb3/queue   (does not exist)
  * device_realpath   -> /sys/class/block/sdb3/device  (does not exist)

`queue/` and `device/` exist only on whole-disk nodes in sysfs.  In R1 run 4
this produced 416 ERROR reads (16 initial + 400 across 25 samples) and empty
model/vendor/state, while the very same attributes were readable one level up.

WHAT THIS TEST DOES NOT DO
--------------------------
No grep, no inspect.getsource(), no assertion that a name exists in the source.
The tests execute the real read_queue(), resolve_block_device(),
resolve_storage_identity() and storage_identity_snapshot() against sysfs trees.

TWO TREES, BOTH REAL
--------------------
1. The live host tree, when it presents the same topology.  Read-only, no sudo.
2. A replica built from the host's *observed* node set and values: sdb is a
   whole disk carrying queue/ (16 attributes) and device/ (vendor, model, state,
   host); sdb3 is a partition carrying only `partition`.  It always runs, so the
   defect is demonstrated even on a host without this disk.

The replica reproduces the exact condition that makes the defect real: a
partition symlink whose realpath contains "/block/" and whose parent directory
is a whole-disk node.
"""

import importlib.util
import os
import shutil
import tempfile
import unittest
from pathlib import Path

COLLECTOR_PATH = "privileged_read_collector.py"
LIVE_ROOT = Path("/sys/class/block")
# Values read from the live host on 2026-09-26 (kalm, HOST-C).  Used only to
# make the replica realistic; no assertion depends on these exact strings.
LIVE_PARTITION = "sdb3"
LIVE_DISK = "sdb"
REPLICA_DISK = LIVE_DISK
# The 13 queue attributes this kernel actually exposes under
# /sys/class/block/sdb/queue, with the values read from the live host on
# 2026-09-26 (kalm, HOST-C, kernel 7.1.3-200.nobara.fc44).
REPLICA_QUEUE = {
    "scheduler": "none mq-deadline kyber adios [bfq] \n",
    "read_ahead_kb": "8192\n",
    "rq_affinity": "0\n",
    "nomerges": "0\n",
    "async_depth": "2\n",
    "nr_requests": "256\n",
    "rotational": "1\n",
    "logical_block_size": "512\n",
    "physical_block_size": "4096\n",
    "max_sectors_kb": "1280\n",
    "write_cache": "write back\n",
    "add_random": "0\n",
    "iostats": "1\n",
}
# Attributes read_queue() asks for that this kernel does not expose at all.
# They are absent on the real disk node, so reading them from the correct base
# still yields ERROR.  These are genuine absences, NOT path errors, and the
# tests keep the two apart.
REPLICA_ABSENT = ("write_same", "daemon", "rq_affinity_control")
REQUESTED_QUEUE = tuple(REPLICA_QUEUE) + REPLICA_ABSENT
REPLICA_DEVICE = {
    "vendor": "ATA     \n",
    "model": "WDC WD5000LPCX-0\n",
    "state": "running\n",
    "host": "\n",
}


def load_collector():
    spec = importlib.util.spec_from_file_location("d05_collector", COLLECTOR_PATH)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


COLLECTOR = load_collector()


def statuses(queue_payload):
    return {name: value.get("status") for name, value in queue_payload["queue"].items()}


class ReplicaTree:
    """A sysfs-shaped tree with one whole disk and one partition on it.

    Layout mirrors the kernel's real arrangement:

        <root>/real/block/sdb/            whole disk
        <root>/real/block/sdb/queue/      16 queue attributes
        <root>/real/block/sdb/device/     vendor, model, state, host
        <root>/real/block/sdb/sdb3/       the partition
        <root>/real/block/sdb/sdb3/partition
        <root>/class/block/sdb   -> symlink
        <root>/class/block/sdb3  -> symlink into sdb/
    """

    def __init__(self):
        self.root = Path(tempfile.mkdtemp(prefix="d05-replica-"))
        block = self.root / "real" / "block"
        disk = block / REPLICA_DISK
        # In sysfs the whole-disk `device` entry is a symlink to the parent
        # device, with vendor/model/state/host behind it.  The replica mirrors
        # that, because storage_identity_snapshot reads it with os.readlink,
        # which fails on a plain directory.
        device = self.root / "real" / "device" / "4:0:0:0"
        device.mkdir(parents=True)
        for name, value in REPLICA_DEVICE.items():
            (device / name).write_text(value)
        (disk / "queue").mkdir(parents=True)
        for name, value in REPLICA_QUEUE.items():
            (disk / "queue" / name).write_text(value)
        os.symlink(os.path.relpath(device, disk), disk / "device")
        partition = disk / LIVE_PARTITION
        partition.mkdir()
        (partition / "partition").write_text("1\n")
        klass = self.root / "class" / "block"
        klass.mkdir(parents=True)
        os.symlink(os.path.relpath(disk, klass), klass / REPLICA_DISK)
        os.symlink(
            os.path.relpath(partition, klass), klass / LIVE_PARTITION
        )
        self.block_root = klass

    def storage(self, source="/dev/%s" % LIVE_PARTITION):
        return self._storage(source)

    def _storage(self, source):
        """Build the same storage dict main() builds, from the real resolver."""
        block = COLLECTOR.resolve_block_device(source, self.block_root)
        return {
            "ROOT_BLOCK_DEVICE": block["block_name"],
            "ROOT_BLOCK_SYSFS": block["block_sysfs"],
            "ROOT_BLOCK_PARENT": block["parent_disk"],
            "ROOT_IS_PARTITION": block["is_partition"],
            "block_resolution": block,
            "STORAGE_IDENTITY_STATUS": block["status"],
            "ROOT_SOURCE": source,
            "STORAGE_DISKSTATS_NAMES": [REPLICA_DISK, LIVE_PARTITION],
        }

    def close(self):
        shutil.rmtree(self.root, ignore_errors=True)


class ReplicaTreeTests(unittest.TestCase):
    """The fixture itself must be a faithful stand-in for the real topology."""

    @classmethod
    def setUpClass(cls):
        cls.tree = ReplicaTree()

    @classmethod
    def tearDownClass(cls):
        cls.tree.close()

    def setUp(self):
        self.storage = self.tree.storage()

    def test_partition_queue_node_is_absent_and_disk_queue_node_is_present(self):
        partition = Path(self.storage["ROOT_BLOCK_SYSFS"]) / "queue"
        disk = Path(self.storage["block_resolution"]["parent_sysfs"]) / "queue"
        self.assertFalse(partition.exists(), "replica is wrong: partition must have no queue/")
        self.assertTrue(disk.is_dir(), "replica is wrong: whole disk must have queue/")
        self.assertEqual(
            sorted(p.name for p in disk.iterdir()), sorted(REPLICA_QUEUE)
        )

    def test_partition_device_node_is_absent_and_disk_device_node_is_present(self):
        partition = Path(self.storage["ROOT_BLOCK_SYSFS"]) / "device"
        disk = Path(self.storage["block_resolution"]["parent_sysfs"]) / "device"
        self.assertFalse(partition.exists())
        self.assertTrue(disk.is_dir())


class ResolutionTests(ReplicaTreeTests):
    """The resolver is already correct and must stay correct."""

    def test_resolver_already_produces_the_parent_disk_sysfs(self):
        self.assertEqual(
            self.storage["block_resolution"]["parent_sysfs"],
            str(self.tree.block_root / REPLICA_DISK),
        )
        self.assertEqual(self.storage["block_resolution"]["parent_disk"], REPLICA_DISK)
        self.assertEqual(self.storage["ROOT_BLOCK_DEVICE"], LIVE_PARTITION)
        self.assertEqual(self.storage["ROOT_BLOCK_SYSFS"], str(self.tree.block_root / LIVE_PARTITION))
        self.assertTrue(self.storage["ROOT_IS_PARTITION"])

    def test_the_partition_base_really_is_the_one_that_fails(self):
        """Reproduces the defect's mechanism on the replica."""
        payload = COLLECTOR.read_queue(self.storage["ROOT_BLOCK_SYSFS"])
        self.assertEqual(set(statuses(payload).values()), {"ERROR"})
        self.assertEqual(len(payload["queue"]), len(REQUESTED_QUEUE))

    def test_the_disk_base_really_is_the_one_that_works(self):
        payload = COLLECTOR.read_queue(self.storage["block_resolution"]["parent_sysfs"])
        got = statuses(payload)
        self.assertEqual(
            {name for name, st in got.items() if st == "ERROR"}, set(REPLICA_ABSENT)
        )
        self.assertEqual(
            {name for name, st in got.items() if st == "OK"}, set(REPLICA_QUEUE)
        )


class LiveHostTreeTests(unittest.TestCase):
    """Same demonstration against the host's own sysfs.  No sudo, read-only."""

    def setUp(self):
        self.partition = LIVE_ROOT / LIVE_PARTITION
        self.disk = LIVE_ROOT / LIVE_DISK
        if not (self.partition.is_dir() and self.disk.is_dir()):
            self.skipTest("host does not present the %s/%s topology" % (LIVE_DISK, LIVE_PARTITION))

    def test_live_partition_has_no_queue_or_device_node(self):
        self.assertFalse((self.partition / "queue").exists())
        self.assertFalse((self.partition / "device").exists())

    def test_live_disk_carries_the_queue_attributes(self):
        queue = self.disk / "queue"
        self.assertTrue(queue.is_dir())
        for name in REPLICA_QUEUE:
            self.assertTrue((queue / name).exists(), name)

    def test_live_read_queue_from_partition_is_all_error(self):
        payload = COLLECTOR.read_queue(str(self.partition))
        self.assertEqual(set(statuses(payload).values()), {"ERROR"})
        self.assertEqual(len(payload["queue"]), len(REQUESTED_QUEUE))

    def test_live_read_queue_from_disk_recovers_every_exposed_attribute(self):
        payload = COLLECTOR.read_queue(str(self.disk))
        queue = self.disk / "queue"
        for name in REQUESTED_QUEUE:
            expected = "OK" if (queue / name).exists() else "ERROR"
            self.assertEqual(payload["queue"][name]["status"], expected, name)

    def test_live_read_queue_from_disk_beats_the_partition_base(self):
        """The discrimination: the partition base yields nothing readable."""
        partition = COLLECTOR.read_queue(str(self.partition))["queue"]
        disk = COLLECTOR.read_queue(str(self.disk))["queue"]
        ok_partition = sum(1 for v in partition.values() if v["status"] == "OK")
        ok_disk = sum(1 for v in disk.values() if v["status"] == "OK")
        self.assertEqual(ok_partition, 0)
        self.assertEqual(ok_disk, len(REPLICA_QUEUE))

    def test_live_resolve_storage_identity_reports_both_nodes(self):
        storage = COLLECTOR.resolve_storage_identity()
        self.assertEqual(storage["STORAGE_IDENTITY_STATUS"], "PROVEN")
        self.assertEqual(storage["ROOT_BLOCK_DEVICE"], LIVE_PARTITION)
        self.assertEqual(storage["block_resolution"]["parent_sysfs"], str(self.disk))

    def test_live_disk_level_sysfs_picks_the_disk(self):
        storage = COLLECTOR.resolve_storage_identity()
        self.assertEqual(COLLECTOR.disk_level_sysfs(storage), str(self.disk))

    def test_live_identity_snapshot_recovers_the_hardware_strings(self):
        storage = COLLECTOR.resolve_storage_identity()
        snapshot = COLLECTOR.storage_identity_snapshot(storage)
        identity = snapshot["identity"]
        self.assertEqual(identity["device_realpath"]["status"], "OK")
        self.assertTrue(identity["model"], "model must not be empty")
        self.assertTrue(identity["vendor"], "vendor must not be empty")
        self.assertEqual(identity["state"], "running")
        # The block device the root mount came from is still the partition.
        self.assertEqual(identity["block_name"], LIVE_PARTITION)
        self.assertEqual(identity["parent_disk"], LIVE_DISK)

    def test_live_identity_snapshot_has_no_read_errors(self):
        storage = COLLECTOR.resolve_storage_identity()
        identity = COLLECTOR.storage_identity_snapshot(storage)["identity"]
        broken = [
            name
            for name, value in identity.items()
            if isinstance(value, dict) and value.get("status") == "ERROR"
        ]
        self.assertEqual(broken, [])


class ConsumerContractTests(ReplicaTreeTests):
    """The consumers must use the disk-level base that the resolver supplies."""

    def test_disk_level_sysfs_returns_the_parent_not_the_partition(self):
        base = COLLECTOR.disk_level_sysfs(self.storage)
        self.assertEqual(base, str(self.tree.block_root / REPLICA_DISK))
        self.assertNotEqual(base, self.storage["ROOT_BLOCK_SYSFS"])

    def test_queue_values_are_recovered_through_the_consumer_base(self):
        base = COLLECTOR.disk_level_sysfs(self.storage)
        payload = COLLECTOR.read_queue(base)
        self.assertEqual(payload["STORAGE_METRICS"], "READ")
        got = statuses(payload)
        for name, expected in REPLICA_QUEUE.items():
            self.assertEqual(got[name], "OK", name)
            self.assertEqual(payload["queue"][name]["value"], expected)
        self.assertEqual(
            {name for name, st in got.items() if st == "ERROR"}, set(REPLICA_ABSENT)
        )

    def test_no_spurious_error_remains_from_reading_the_partition(self):
        """Errors that survive must be absent attributes, not wrong-path reads."""
        payload = COLLECTOR.read_queue(COLLECTOR.disk_level_sysfs(self.storage))
        wrong_path = [
            name
            for name, value in payload["queue"].items()
            if value["status"] == "ERROR" and str(LIVE_PARTITION) in value.get("error", "")
        ]
        self.assertEqual(wrong_path, [])

    def test_queue_payload_records_the_disk_base_it_used(self):
        payload = COLLECTOR.read_queue(COLLECTOR.disk_level_sysfs(self.storage))
        self.assertEqual(payload["block_sysfs"], str(self.tree.block_root / REPLICA_DISK / "queue"))

    def test_identity_snapshot_recovers_device_attributes(self):
        snapshot = COLLECTOR.storage_identity_snapshot(self.storage)
        self.assertEqual(snapshot["STORAGE_METRICS"], "READ")
        identity = snapshot["identity"]
        self.assertEqual(identity["device_realpath"]["status"], "OK")
        self.assertEqual(identity["vendor"], "ATA")
        self.assertEqual(identity["model"], "WDC WD5000LPCX-0")
        self.assertEqual(identity["state"], "running")

    def test_identity_snapshot_reports_zero_errors(self):
        identity = COLLECTOR.storage_identity_snapshot(self.storage)["identity"]
        broken = [k for k, v in identity.items() if isinstance(v, dict) and v.get("status") == "ERROR"]
        self.assertEqual(broken, [])

    def test_identity_snapshot_still_names_the_partition(self):
        """No regression: the root block device is still the partition."""
        identity = COLLECTOR.storage_identity_snapshot(self.storage)["identity"]
        self.assertEqual(identity["block_name"], LIVE_PARTITION)
        self.assertEqual(identity["parent_disk"], REPLICA_DISK)


class RegressionTests(ReplicaTreeTests):
    """The other consumers of ROOT_BLOCK_SYSFS keep their existing meaning."""

    def test_root_block_sysfs_is_unchanged_and_still_names_the_partition(self):
        self.assertEqual(self.storage["ROOT_BLOCK_SYSFS"], str(self.tree.block_root / LIVE_PARTITION))

    def test_diskstats_names_are_untouched(self):
        self.assertIn(REPLICA_DISK, self.storage["STORAGE_DISKSTATS_NAMES"])
        self.assertIn(LIVE_PARTITION, self.storage["STORAGE_DISKSTATS_NAMES"])

    def test_disk_level_sysfs_falls_back_when_no_resolution_is_present(self):
        degraded = dict(self.storage)
        degraded.pop("block_resolution")
        self.assertEqual(COLLECTOR.disk_level_sysfs(degraded), self.storage["ROOT_BLOCK_SYSFS"])

    def test_disk_level_sysfs_handles_a_whole_disk_source(self):
        """A non-partition source resolves parent_sysfs to itself."""
        storage = self.tree.storage(source="/dev/%s" % REPLICA_DISK)
        self.assertEqual(
            COLLECTOR.disk_level_sysfs(storage), str(self.tree.block_root / REPLICA_DISK)
        )
        payload = COLLECTOR.read_queue(COLLECTOR.disk_level_sysfs(storage))
        self.assertEqual(
            {n for n, s in statuses(payload).items() if s == "OK"}, set(REPLICA_QUEUE)
        )

    def test_disk_level_sysfs_of_an_unproven_identity_is_none(self):
        self.assertIsNone(COLLECTOR.disk_level_sysfs({}))
        self.assertIsNone(COLLECTOR.disk_level_sysfs({"ROOT_BLOCK_SYSFS": None}))


if __name__ == "__main__":
    unittest.main(verbosity=2)
