#!/usr/bin/env python3
# SPDX-License-Identifier: GPL-2.0
"""RXRE-009: a physical identity must come from the addressed PCI function.

Fixture values are independent of core.target: the real target is
0000:01:00.0 / 1002:699f / c7. No hardware writes or RXRE database access.
"""
import pathlib
import sys
import tempfile
import unittest
from unittest.mock import patch

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parents[1]))
from core.target import (_get_target_from_pci, get_current_target,
                         get_capabilities_for_target)


class PhysicalIdentity(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory(dir="/tmp/opencode")
        self.addCleanup(self.temp.cleanup)
        self.root = pathlib.Path(self.temp.name)

    def device(self, bdf, vendor, device, revision):
        node = self.root / bdf
        node.mkdir()
        for name, value in (("vendor", vendor), ("device", device),
                            ("revision", revision),
                            ("subsystem_vendor", "0x1002"),
                            ("subsystem_device", "0x0b04")):
            (node / name).write_text(value + "\n", encoding="ascii")
        return node

    def test_exact_function_and_revision_not_first_amd(self):
        self.device("0000:00:01.0", "0x1002", "0x699f", "0xc8")
        self.device("0000:01:00.0", "0x1002", "0x699f", "0xc7")
        found = _get_target_from_pci(str(self.root))
        self.assertIsNotNone(found)
        self.assertEqual((found.bdf, found.vendor, found.device, found.revision),
                         ("0000:01:00.0", "1002", "699f", "c7"))
        self.assertTrue(any("0000:01:00.0" in p for p in found.provenance))
        self.assertFalse(found.is_unknown())
        self.assertTrue(get_capabilities_for_target(found))

    def test_detection_failure_does_not_invent_board(self):
        with patch("core.target._get_target_from_pci", return_value=None):
            self.assertIsNone(get_current_target())
        self.assertIsNone(get_current_target(str(self.root)))

    def test_wrong_revision_does_not_claim_c7(self):
        self.device("0000:01:00.0", "0x1002", "0x699f", "0xc8")
        found = get_current_target(str(self.root))
        self.assertTrue(found is None or found.revision.lower() != "c7")

    def test_missing_revision_is_explicit_not_defaulted(self):
        node = self.device("0000:01:00.0", "0x1002", "0x699f", "0xc7")
        (node / "revision").unlink()
        found = get_current_target(str(self.root))
        self.assertTrue(found is None or found.is_unknown())
        if found is not None:
            self.assertEqual(found.revision, "unknown")
            self.assertTrue(any("revision" in p.lower() and "NOT_OBSERVED" in p
                                for p in found.provenance))
            self.assertEqual(get_capabilities_for_target(found), [])

    def test_wrong_function_or_subsystem_is_not_our_board(self):
        self.device("0000:02:00.0", "0x1002", "0x699f", "0xc7")
        self.assertIsNone(get_current_target(str(self.root)))
        node = self.device("0000:01:00.0", "0x1002", "0x699f", "0xc7")
        (node / "subsystem_device").write_text("0x0001\n", encoding="ascii")
        self.assertIsNone(get_current_target(str(self.root)))


if __name__ == "__main__":
    unittest.main()
