#!/usr/bin/env python3
"""Behavioral tests for the fdinfo path in scan_fds().

DEFECT (fixed here): scan_fds() built the fdinfo path from ``fd_path.parent``,
where ``fd_path`` is ``/proc/<pid>/fd/<n>``.  ``fd_path.parent`` is therefore
``/proc/<pid>/fd``, and the path it produced was::

    /proc/<pid>/fd/fdinfo/<n>      <- never exists

The real procfs layout puts ``fdinfo`` as a *sibling* of ``fd``::

    /proc/<pid>/fd/<n>             symlink to the opened file
    /proc/<pid>/fdinfo/<n>         the FD's info

So every DRM client was recorded with an empty ``fdinfo`` string, and the
failure was invisible twice over: the path did not exist, and ``read_text()``
returns ``""`` on any error without recording it.

These tests build a synthetic ``/proc`` with the real layout and assert on
*content that must arrive*, not on the presence of a field name.  They also pin
the route itself, so a regression to the old parent cannot pass silently.
"""

import importlib.util
import os
import tempfile
import unittest
from pathlib import Path

COLLECTOR_PATH = "privileged_read_collector.py"
CARD = "/dev/dri/card1"
RENDER = "/dev/dri/renderD129"
OTHER = "/dev/dri/card0"

# Content shaped like a real amdgpu DRM fdinfo, including the drm-* fields the
# collector's own capability matrix and docstring name.
FDINFO_AMDGPU = (
    "pos:\t0\n"
    "flags:\t02100002\n"
    "mnt_id:\t40\n"
    "ino:\t441\n"
    "drm-driver:\tamdgpu\n"
    "drm-client-id:\t71\n"
    "drm-pdev:\t0000:01:00.0\n"
    "drm-memory-vram:\t0 KiB\n"
    "drm-memory-gtt:\t2184 KiB\n"
    "pasid:\t43\n"
)


def load_collector():
    spec = importlib.util.spec_from_file_location("fdinfo_collector", COLLECTOR_PATH)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


COLLECTOR = load_collector()


def build_proc(root, pid, fds):
    """Create a procfs-shaped tree.

    ``fds`` maps an fd number to ``(target, fdinfo_text_or_None)``.  A symlink
    is created at ``<root>/<pid>/fd/<n>`` and, when text is given, the file is
    created at the real sibling location ``<root>/<pid>/fdinfo/<n>``.
    """
    fd_dir = Path(root) / str(pid) / "fd"
    fd_dir.mkdir(parents=True, exist_ok=True)
    made = []
    for number, (target, text) in fds.items():
        os.symlink(target, fd_dir / str(number))
        if text is not None:
            info = Path(root) / str(pid) / "fdinfo" / str(number)
            info.parent.mkdir(parents=True, exist_ok=True)
            info.write_text(text)
            made.append(info)
    return made


class FdinfoContentArrivesTests(unittest.TestCase):
    """The content of a real fdinfo must reach the caller."""

    def test_fdinfo_content_is_read_for_a_matching_device(self):
        with tempfile.TemporaryDirectory() as raw:
            build_proc(raw, 1923, {13: (CARD, FDINFO_AMDGPU)})
            result = COLLECTOR.scan_fds(1923, {CARD}, proc_root=Path(raw))
        self.assertEqual(result["status"], "OK")
        self.assertEqual(len(result["matched"]), 1)
        record = result["matched"][0]
        self.assertEqual(record["fd"], 13)
        self.assertEqual(record["target"], CARD)
        self.assertEqual(record["fdinfo"], FDINFO_AMDGPU)

    def test_the_named_drm_fields_survive_into_the_record(self):
        with tempfile.TemporaryDirectory() as raw:
            build_proc(raw, 1923, {13: (CARD, FDINFO_AMDGPU)})
            record = COLLECTOR.scan_fds(1923, {CARD}, proc_root=Path(raw))["matched"][0]
        for field in ("drm-driver", "drm-client-id", "drm-pdev", "pasid"):
            self.assertIn(field, record["fdinfo"])
        self.assertIn("drm-client-id:\t71", record["fdinfo"])
        self.assertIn("pasid:\t43", record["fdinfo"])

    def test_a_clean_read_produces_no_errors(self):
        with tempfile.TemporaryDirectory() as raw:
            build_proc(raw, 1923, {13: (CARD, FDINFO_AMDGPU)})
            result = COLLECTOR.scan_fds(1923, {CARD}, proc_root=Path(raw))
        self.assertEqual(result["error_count"], 0)
        self.assertEqual(result["errors"], [])

    def test_several_clients_on_two_nodes_are_all_read(self):
        fds = {13: (CARD, FDINFO_AMDGPU), 14: (RENDER, FDINFO_AMDGPU), 15: (RENDER, FDINFO_AMDGPU)}
        with tempfile.TemporaryDirectory() as raw:
            build_proc(raw, 1825, fds)
            result = COLLECTOR.scan_fds(1825, {CARD, RENDER}, proc_root=Path(raw))
        self.assertEqual(len(result["matched"]), 3)
        self.assertTrue(all(m["fdinfo"] == FDINFO_AMDGPU for m in result["matched"]))
        self.assertEqual(result["error_count"], 0)


class RouteIsTheRealOneTests(unittest.TestCase):
    """Pin the route, so the old parent cannot come back unnoticed."""

    def test_the_tree_never_contains_fd_slash_fdinfo(self):
        """If fd/fdinfo existed the old code would pass for the wrong reason."""
        with tempfile.TemporaryDirectory() as raw:
            build_proc(raw, 1923, {13: (CARD, FDINFO_AMDGPU)})
            self.assertFalse((Path(raw) / "1923" / "fd" / "fdinfo").exists())
            self.assertTrue((Path(raw) / "1923" / "fdinfo" / "13").exists())

    def test_the_recorded_failure_path_is_the_sibling_location(self):
        """The error record carries the path that was actually attempted."""
        with tempfile.TemporaryDirectory() as raw:
            build_proc(raw, 1923, {13: (CARD, None)})
            result = COLLECTOR.scan_fds(1923, {CARD}, proc_root=Path(raw))
        self.assertEqual(result["error_count"], 1)
        attempted = result["errors"][0]["path"]
        self.assertEqual(attempted, str(Path(raw) / "1923" / "fdinfo" / "13"))
        self.assertNotIn("/fd/fdinfo/", attempted)


class ReadFailureIsVisibleTests(unittest.TestCase):
    """A failed fdinfo read must be counted, not swallowed."""

    def test_a_missing_fdinfo_is_counted_and_classified(self):
        with tempfile.TemporaryDirectory() as raw:
            build_proc(raw, 1923, {13: (CARD, None)})
            result = COLLECTOR.scan_fds(1923, {CARD}, proc_root=Path(raw))
        self.assertEqual(result["error_count"], 1)
        self.assertEqual(len(result["errors"]), 1)
        error = result["errors"][0]
        self.assertEqual(error["fd"], 13)
        self.assertEqual(error["stage"], "fdinfo")
        self.assertIn(error["reason"], ("PROCESS_DISAPPEARED", "OTHER_ERROR"))
        self.assertIn("FileNotFoundError", error["error"])

    def test_a_missing_fdinfo_still_records_the_client(self):
        """Losing the fdinfo must not lose the client itself."""
        with tempfile.TemporaryDirectory() as raw:
            build_proc(raw, 1923, {13: (CARD, None)})
            result = COLLECTOR.scan_fds(1923, {CARD}, proc_root=Path(raw))
        self.assertEqual(len(result["matched"]), 1)
        self.assertEqual(result["matched"][0]["target"], CARD)
        self.assertEqual(result["matched"][0]["fdinfo"], "")

    def test_several_failures_accumulate(self):
        fds = {13: (CARD, None), 14: (CARD, None), 15: (CARD, FDINFO_AMDGPU)}
        with tempfile.TemporaryDirectory() as raw:
            build_proc(raw, 1825, fds)
            result = COLLECTOR.scan_fds(1825, {CARD}, proc_root=Path(raw))
        self.assertEqual(result["error_count"], 2)
        self.assertEqual(len(result["errors"]), 2)
        self.assertEqual(
            [m["fdinfo"] for m in result["matched"]],
            ["", "", FDINFO_AMDGPU],
        )

    def test_an_unreadable_fdinfo_is_visible(self):
        if os.geteuid() == 0:
            self.skipTest("running as root: mode 000 does not deny open()")
        with tempfile.TemporaryDirectory() as raw:
            info = build_proc(raw, 1923, {13: (CARD, FDINFO_AMDGPU)})[0]
            os.chmod(info, 0o000)
            try:
                result = COLLECTOR.scan_fds(1923, {CARD}, proc_root=Path(raw))
            finally:
                os.chmod(info, 0o644)
        self.assertEqual(result["error_count"], 1)
        self.assertEqual(result["errors"][0]["reason"], "PERMISSION_DENIED")
        self.assertEqual(result["errors"][0]["stage"], "fdinfo")

    def test_the_error_sample_is_still_capped_at_twelve(self):
        fds = {n: (CARD, None) for n in range(1, 21)}
        with tempfile.TemporaryDirectory() as raw:
            build_proc(raw, 1825, fds)
            result = COLLECTOR.scan_fds(1825, {CARD}, proc_root=Path(raw))
        self.assertEqual(result["error_count"], 20)
        self.assertEqual(len(result["errors"]), 12)


class UnaffectedBranchesTests(unittest.TestCase):
    """The fix must not disturb the other two branches of scan_fds."""

    def test_a_device_outside_the_set_is_still_only_listed(self):
        with tempfile.TemporaryDirectory() as raw:
            build_proc(raw, 1825, {13: (OTHER, FDINFO_AMDGPU)})
            result = COLLECTOR.scan_fds(1825, {CARD}, proc_root=Path(raw))
        self.assertEqual(result["matched"], [])
        self.assertEqual([d["target"] for d in result["drm_nodes_any"]], [OTHER])
        self.assertEqual(result["error_count"], 0)

    def test_an_unrelated_file_does_not_trigger_any_drm_record(self):
        with tempfile.TemporaryDirectory() as raw:
            fd_dir = Path(raw) / "9" / "fd"
            fd_dir.mkdir(parents=True)
            os.symlink("/etc/passwd", fd_dir / "3")
            result = COLLECTOR.scan_fds(9, {CARD}, proc_root=Path(raw))
        self.assertEqual(result["matched"], [])
        self.assertEqual(result["drm_nodes_any"], [])
        self.assertEqual(result["error_count"], 0)
        self.assertEqual(result["fd_count"], 1)

    def test_a_readlink_failure_still_classifies_at_the_fd_stage(self):
        """A target that cannot be resolved is tagged 'target', not 'fdinfo'.

        The stage tag is what lets observe() tell the two apart: an fdinfo-stage
        failure means the DRM fd was already matched, so the resource is proven
        and only its characterisation is open, whereas a target-stage failure
        means the FD exists and its identity is unknown, which is lost coverage.
        Asserting the value rather than its absence pins the distinction in both
        directions.
        """
        with tempfile.TemporaryDirectory() as raw:
            fd_dir = Path(raw) / "77" / "fd"
            fd_dir.mkdir(parents=True)
            os.mkfifo(fd_dir / "0")
            import unittest.mock as mock

            with mock.patch.object(os, "readlink", side_effect=PermissionError(13, "denied")):
                result = COLLECTOR.scan_fds(77, {CARD}, proc_root=Path(raw))
        self.assertEqual(result["error_count"], 1)
        self.assertEqual(result["errors"][0]["reason"], "PERMISSION_DENIED")
        self.assertEqual(result["errors"][0]["stage"], "target")
        self.assertNotEqual(result["errors"][0]["stage"], "fdinfo")
        self.assertEqual(result["unresolved_target_count"], 1)


class ShapeContractTests(unittest.TestCase):
    """scan_fds' public shape is unchanged apart from the fdinfo error record."""

    KEYS = {
        "status",
        "fd_count",
        "matched",
        "drm_nodes_any",
        "error_count",
        "errors",
    }

    def test_the_result_keeps_its_documented_keys(self):
        with tempfile.TemporaryDirectory() as raw:
            build_proc(raw, 1923, {13: (CARD, FDINFO_AMDGPU)})
            result = COLLECTOR.scan_fds(1923, {CARD}, proc_root=Path(raw))
        self.assertTrue(self.KEYS.issubset(set(result)))

    def test_the_matched_record_keeps_its_three_fields(self):
        with tempfile.TemporaryDirectory() as raw:
            build_proc(raw, 1923, {13: (CARD, FDINFO_AMDGPU)})
            record = COLLECTOR.scan_fds(1923, {CARD}, proc_root=Path(raw))["matched"][0]
        self.assertEqual(set(record), {"fd", "target", "fdinfo"})
        self.assertIsInstance(record["fdinfo"], str)

    def test_the_truncation_cap_is_still_applied(self):
        oversized = "x" * 20000
        with tempfile.TemporaryDirectory() as raw:
            build_proc(raw, 1923, {13: (CARD, oversized)})
            record = COLLECTOR.scan_fds(1923, {CARD}, proc_root=Path(raw))["matched"][0]
        self.assertEqual(len(record["fdinfo"]), 16384)


if __name__ == "__main__":
    unittest.main(verbosity=2)
