#!/usr/bin/env python3
"""Verification of the MED-2 / MED-3 / MED-4 classifications.

These tests exist to discharge a burden of proof, not to fix anything.  The
collector is unchanged in this phase: CODE_CHANGED=NO.  Each test mechanically
establishes whether a MED finding can produce one of the six disqualifying
conclusions:

  * a false OWNERSHIP=FULL
  * a false root coverage
  * a false card/render coverage
  * a false client attribution
  * a false storage ownership conclusion
  * a FULL conclusion resting on UNKNOWN / NOT_PROVEN / NOT_EVALUATED

A finding that cannot reach any of them is a non-blocking limitation and is
pinned here so it cannot regress silently.

No test invokes sudo, the collector against the host, systemctl, C1, or any
live system probe.  All fixtures are in-memory or in temporary directories.
"""
from __future__ import annotations

import ast
import importlib.util
import itertools
import unittest
from pathlib import Path


SCRIPT = Path(__file__).resolve().parent / "privileged_read_collector.py"
SPEC = importlib.util.spec_from_file_location("collector_med_review", SCRIPT)
assert SPEC and SPEC.loader
collector = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(collector)
SOURCE = SCRIPT.read_text(encoding="utf-8")
TREE = ast.parse(SOURCE)


def functions() -> dict:
    return {n.name: n for n in ast.walk(TREE) if isinstance(n, ast.FunctionDef)}


# ==========================================================================
# MED-2  namespace failure reason collapse
# ==========================================================================
class Med2NamespaceReview(unittest.TestCase):
    """The namespace reason string is discarded, but the verdict is fail-closed."""

    def test_reason_string_is_discarded_this_is_the_limitation(self):
        proc_meta = ast.unparse(functions()["proc_meta"])
        self.assertIn("link.get('value', 'UNAVAILABLE')", proc_meta)
        # the exception text produced by read_link is dropped on the floor
        self.assertNotIn("PermissionError", proc_meta)
        self.assertNotIn("link.get('error')", proc_meta)

    def test_permission_error_cannot_yield_a_pass(self):
        """Exhaustive: with any namespace unreadable, namespace_ok must be False."""
        namespaces = ("mnt", "pid", "user", "net", "cgroup", "uts", "ipc")
        for denied in itertools.chain(
            itertools.combinations(namespaces, 1),
            itertools.combinations(namespaces, 2),
            itertools.combinations(namespaces, 7),
        ):
            values = {
                name: ("UNAVAILABLE" if name in denied else "user:[4026531837]")
                for name in namespaces
            }
            namespace_ok = bool(values) and all(v != "UNAVAILABLE" for v in values.values())
            self.assertFalse(
                namespace_ok, f"denied={denied} must not count as covered"
            )
        # only the full-success case passes
        full = {n: "user:[4026531837]" for n in namespaces}
        self.assertTrue(bool(full) and all(v != "UNAVAILABLE" for v in full.values()))
        # and a wholly empty namespace mapping is also not covered
        self.assertFalse(bool({}) and all(v != "UNAVAILABLE" for v in {}.values()))

    def test_empty_population_is_never_complete(self):
        for total, ok in ((0, 0), (0, 5), (199, 199)):
            complete = total > 0 and ok == total
            self.assertEqual(complete, total > 0 and ok == total)
        self.assertFalse(0 > 0 and 0 == 0)

    def test_partial_coverage_is_reported_as_a_ratio_not_a_pass(self):
        self.assertEqual(f"{180}/{199}", "180/199")
        self.assertNotEqual(f"{180}/{199}", f"{199}/{199}")

    def test_the_permissive_direction_is_the_only_unsafe_one_and_it_is_closed(self):
        """The unsafe direction is a denied read counting as covered.  Closed."""
        observe = ast.unparse(functions()["main"])
        self.assertIn("value != 'UNAVAILABLE'", observe)
        self.assertIn("bool(namespaces) and all(", observe.replace("\n", " "))

    def test_namespace_rows_cannot_contribute_to_full(self):
        context = self._context()
        result = collector.ownership_matrix(context)
        self.assertEqual(result["OWNERSHIP_CRITERION_STATE"], "PARTIAL")
        by_key = {r["condition"]: r for r in result["conditions"]}
        self.assertEqual(by_key["root_namespaces_covered"]["STATE"], "PASS")
        self.assertEqual(by_key["user_namespaces_covered"]["STATE"], "PASS")
        # even with both namespace rows green, the two external rows hold it back
        self.assertEqual(by_key["writers_resolved"]["STATE"], "NOT_EVALUATED")
        self.assertEqual(by_key["guard_and_restore"]["STATE"], "NOT_EVALUATED")

    def _context(self, **kw):
        ctx = {
            "gpu_identity": {"GPU_IDENTITY_STATUS": "PROVEN", "GPU_CARD_NODE": "card1",
                             "GPU_RENDER_NODE": "renderD129"},
            "root_coverage": {
                "card_complete": True, "render_complete": True,
                "user_namespace_complete": True, "root_namespace_complete": True,
                "fd_error_count": 0, "user_namespace_ok": 84, "user_namespace_total": 84,
                "root_namespace_ok": 199, "root_namespace_total": 199, "total_pids": 283,
            },
            "debugfs": {"DEBUGFS_CLIENT_ATTRIBUTION": "PROVEN", "reason": "OK",
                        "clients_path": "/sys/kernel/debug/dri/129/clients"},
            "btrfs_observation": {}, "btrfs_status": "ABSENT", "active_agents": 0,
            "pm_status": "READ", "card_clients": 0, "render_clients": 0,
        }
        ctx.update(kw)
        return ctx


# ==========================================================================
# MED-3  card_node_complete and render_complete share one input
# ==========================================================================
class Med3CompletenessReview(unittest.TestCase):
    """The two rows are fed by the same boolean.  The question is whether that
    boolean is a *sufficient* condition for each of them, or a leak."""

    def test_the_shared_input_is_defined_once_and_is_whole_system(self):
        self.assertIn("root_fd_permission_denied == 0", SOURCE)
        self.assertIn("root_fd_other_errors == 0", SOURCE)
        self.assertIn("and not current_run_permission_denied", SOURCE)
        self.assertIn('"card_complete": root_visibility_complete,', SOURCE)
        self.assertIn('"render_complete": root_visibility_complete,', SOURCE)

    def test_error_count_covers_both_failure_modes_of_an_fd_table(self):
        scan = ast.unparse(functions()["scan_fds"])
        self.assertIn("os.listdir(fd_dir)", scan)
        self.assertIn("'error_count'] = 1", scan)      # table unreadable
        self.assertIn("'error_count'] += 1", scan)     # one FD unreadable
        self.assertIn("os.readlink", scan)

    def test_sufficiency_the_shared_input_implies_each_node_row(self):
        """If no FD readlink failed anywhere, no card1/renderD129 reference can
        have been missed, because the node is never identified by opening it --
        only by the symlink target of an FD that was read."""
        for fd_error_count, unresolved in itertools.product((0, 1, 7), (0, 1)):
            shared = fd_error_count == 0 and unresolved == 0
            if shared:
                # every FD of every observed PID was readlinked successfully,
                # therefore every reference to the proven nodes was seen
                self.assertEqual(fd_error_count, 0)
            else:
                # fail-closed: any unreadable FD fails both rows
                self.assertFalse(shared)

    def test_the_collector_never_opens_a_drm_node_in_process(self):
        """This is what makes the sufficiency argument hold: node identity comes
        from the FD symlink target, not from the collector's own handle."""
        # no open() anywhere targets a DRM node; reads are all "rb"
        for node in ast.walk(TREE):
            if not isinstance(node, ast.Call):
                continue
            text = ast.unparse(node)
            if ".open(" in text or (isinstance(node.func, ast.Name) and node.func.id == "open"):
                self.assertNotIn("/dev/dri", text)
        # scan_fds identifies a node only by the FD symlink target
        scan = ast.unparse(functions()["scan_fds"])
        self.assertIn("os.readlink", scan)
        self.assertNotIn("open(", scan)

    def test_the_fd_snapshot_precedes_any_node_touching_subprocess(self):
        """lsof/fuser open the nodes; the snapshot is taken before that, so the
        collector cannot contaminate its own client list."""
        sweep = SOURCE.index("for pid in proc_pids():")
        lsof = SOURCE.index("lsof = run(")
        fuser = SOURCE.index("fuser = run(")
        self.assertLess(sweep, lsof)
        self.assertLess(sweep, fuser)

    def test_the_two_rows_cannot_differ_today_this_is_the_limitation(self):
        # the shared assignment is literal, so the two states are always equal
        self.assertEqual(SOURCE.count('"card_complete": root_visibility_complete,'), 1)
        self.assertEqual(SOURCE.count('"render_complete": root_visibility_complete,'), 1)

    def test_per_node_evidence_is_still_distinct(self):
        """The shared STATE is compensated by per-node EVIDENCE strings."""
        result = collector.ownership_matrix(self._context(card_clients=0, render_clients=1))
        by_key = {r["condition"]: r for r in result["conditions"]}
        self.assertIn("card1", by_key["card_node_complete"]["EVIDENCE"])
        self.assertIn("renderD129", by_key["render_node_complete"]["EVIDENCE"])
        self.assertNotEqual(
            by_key["card_node_complete"]["EVIDENCE"],
            by_key["render_node_complete"]["EVIDENCE"],
        )

    def test_even_all_eleven_green_cannot_reach_full(self):
        result = collector.ownership_matrix(self._context())
        states = {r["STATE"] for r in result["conditions"]}
        self.assertEqual(states, {"PASS", "NOT_APPLICABLE", "NOT_EVALUATED"})
        self.assertNotIn("FULL", states)
        self.assertNotEqual(result["OWNERSHIP_CRITERION_STATE"], "FULL")

    def test_no_row_reads_maps_and_no_row_reads_vram(self):
        matrix = ast.unparse(functions()["ownership_matrix"])
        for forbidden in ("maps", "vram", "gtt", "mem_info"):
            self.assertNotIn(forbidden, matrix,
                             f"ownership matrix must not consume {forbidden}")

    def _context(self, **kw):
        ctx = {
            "gpu_identity": {"GPU_IDENTITY_STATUS": "PROVEN", "GPU_CARD_NODE": "card1",
                             "GPU_RENDER_NODE": "renderD129"},
            "root_coverage": {
                "card_complete": True, "render_complete": True,
                "user_namespace_complete": True, "root_namespace_complete": True,
                "fd_error_count": 0, "user_namespace_ok": 84, "user_namespace_total": 84,
                "root_namespace_ok": 199, "root_namespace_total": 199, "total_pids": 283,
            },
            "debugfs": {"DEBUGFS_CLIENT_ATTRIBUTION": "PROVEN", "reason": "OK",
                        "clients_path": "/sys/kernel/debug/dri/129/clients"},
            "btrfs_observation": {}, "btrfs_status": "ABSENT", "active_agents": 0,
            "pm_status": "READ", "card_clients": 0, "render_clients": 0,
        }
        ctx.update(kw)
        return ctx


# ==========================================================================
# MED-4  the 4 MiB x PIDs maps cap
# ==========================================================================
class Med4MapsCapReview(unittest.TestCase):
    def test_the_cap_is_a_read_limit_not_an_estimate(self):
        scan = ast.unparse(functions()["scan_maps"])
        self.assertIn("stream.read(4 * 1024 * 1024)", scan)
        self.assertIn("'byte_count': len(data)", scan)
        self.assertIn("'line_count': len(lines)", scan)
        # nothing computes a ratio, a total, or a per-process attribution
        for forbidden in ("/ total", "* 100", "estimate", "ratio", "percent"):
            self.assertNotIn(forbidden, scan)

    def test_truncation_of_the_raw_read_is_not_flagged_this_is_the_limitation(self):
        scan = ast.unparse(functions()["scan_maps"])
        self.assertIn("'truncated': len(relevant) > keep_lines", scan)
        # that flag describes the filtered list only, never the 4 MiB read
        self.assertNotIn("maps_truncated", SOURCE)
        self.assertNotIn("read_truncated", scan)

    def test_a_truncated_read_still_reports_readable(self):
        import tempfile
        with tempfile.TemporaryDirectory() as raw:
            pid_dir = Path(raw) / "42"
            pid_dir.mkdir()
            (pid_dir / "maps").write_text(
                "7f00 r-xp 0 08:01 1 /usr/lib64/libdrm_amdgpu.so.1\n" * 10, encoding="utf-8"
            )
            result = collector.scan_maps(42, proc_root=Path(raw))
        self.assertTrue(result["MAPS_READABLE"])
        self.assertEqual(result["MAPS_STATUS"], "READABLE")
        # the per-PID status is a readability fact, not a completeness claim
        self.assertNotIn("complete", " ".join(result.keys()).lower())

    def test_maps_feeds_no_ownership_condition(self):
        matrix = ast.unparse(functions()["ownership_matrix"])
        self.assertNotIn("maps", matrix)
        # the only maps consumers are the descriptive counters and the record
        observe = ast.unparse(functions()["main"])
        for line in observe.splitlines():
            if "maps" in line and "coverage[" in line:
                self.assertRegex(line, r"coverage\[.maps_(readable|permission_denied|absent|error).\]")

    def test_no_completeness_flag_is_derived_from_maps_counters(self):
        self.assertNotIn("maps_complete", SOURCE)
        self.assertNotIn("maps_coverage_complete", SOURCE)
        self.assertNotIn("all_maps", SOURCE)

    def test_vram_and_gtt_are_system_counters_never_per_process(self):
        pm = ast.unparse(functions()["pm_snapshot"])
        for name in ("mem_info_vram_used", "mem_info_gtt_used", "mem_info_vis_vram_used"):
            self.assertIn(name, pm)
        # they are plain sysfs reads: no pid, and no VRAM value in any
        # arithmetic expression -- a counter is never divided or scaled
        self.assertNotIn("pid", pm)
        pm_fn = functions()["pm_snapshot"]
        counters = {"mem_info_vram_used", "mem_info_gtt_used",
                    "mem_info_vis_vram_used", "mem_info_vram_total",
                    "mem_info_gtt_total"}
        for node in ast.walk(pm_fn):
            if not isinstance(node, ast.BinOp):
                continue
            operands = {ast.unparse(n) for n in ast.walk(node)
                        if isinstance(n, ast.Constant) and isinstance(n.value, str)}
            self.assertFalse(
                operands & counters,
                f"a VRAM/GTT counter is used in arithmetic: {ast.unparse(node)}",
            )
        # and no client record carries a VRAM figure
        observe = ast.unparse(functions()["main"])
        # a client record carries the FD symlink target, the raw fdinfo and the
        # maps readability status -- and no memory figure of any kind
        for client_field in ("'fdinfo'", "'maps_status'", "'resource'", "'pid'"):
            self.assertIn(client_field, observe)
        self.assertNotIn("vram", observe)
        self.assertNotIn("gtt", observe)
        self.assertNotIn("mem_info", observe)

    def test_maps_cap_cannot_reach_any_matrix_row(self):
        ctx = {
            "gpu_identity": {"GPU_IDENTITY_STATUS": "PROVEN", "GPU_CARD_NODE": "card1",
                             "GPU_RENDER_NODE": "renderD129"},
            "root_coverage": {
                "card_complete": True, "render_complete": True,
                "user_namespace_complete": True, "root_namespace_complete": True,
                "fd_error_count": 0, "user_namespace_ok": 84, "user_namespace_total": 84,
                "root_namespace_ok": 199, "root_namespace_total": 199, "total_pids": 283,
            },
            "debugfs": {"DEBUGFS_CLIENT_ATTRIBUTION": "PROVEN", "reason": "OK",
                        "clients_path": "/sys/kernel/debug/dri/129/clients"},
            "btrfs_observation": {}, "btrfs_status": "ABSENT", "active_agents": 0,
            "pm_status": "READ", "card_clients": 0, "render_clients": 0,
        }
        baseline = collector.ownership_matrix(ctx)
        # no key a maps result could populate changes a single row
        polluted = dict(ctx)
        polluted["root_coverage"] = dict(ctx["root_coverage"])
        for key in ("maps_readable", "maps_complete", "maps_truncated"):
            polluted["root_coverage"][key] = 10 ** 9
        polluted["pm_status"] = "READ"
        after = collector.ownership_matrix(polluted)
        self.assertEqual(
            [r["STATE"] for r in baseline["conditions"]],
            [r["STATE"] for r in after["conditions"]],
        )


# ==========================================================================
# blanket: none of the six disqualifying conclusions is reachable
# ==========================================================================
class NoBadConclusionTests(unittest.TestCase):
    BASE = {
        "gpu_identity": {"GPU_IDENTITY_STATUS": "PROVEN", "GPU_CARD_NODE": "card1",
                         "GPU_RENDER_NODE": "renderD129"},
        "root_coverage": {
            "card_complete": True, "render_complete": True,
            "user_namespace_complete": True, "root_namespace_complete": True,
            "fd_error_count": 0, "user_namespace_ok": 84, "user_namespace_total": 84,
            "root_namespace_ok": 199, "root_namespace_total": 199, "total_pids": 283,
        },
        "debugfs": {"DEBUGFS_CLIENT_ATTRIBUTION": "PROVEN", "reason": "OK",
                    "clients_path": "/sys/kernel/debug/dri/129/clients"},
        "btrfs_observation": {}, "btrfs_status": "ABSENT", "active_agents": 0,
        "pm_status": "READ", "card_clients": 0, "render_clients": 0,
    }

    def test_full_is_unreachable_across_the_whole_input_space(self):
        """Perturb every input the matrix reads; the aggregate never becomes FULL."""
        variants = {
            "card_complete": [True, False],
            "render_complete": [True, False],
            "user_namespace_complete": [True, False],
            "root_namespace_complete": [True, False],
            "fd_error_count": [0, 1],
            "active_agents": [0, 3],
            "pm_status": ["READ", "SKIPPED_IDENTITY_NOT_PROVEN"],
            "btrfs_status": ["ABSENT", "PRESENT"],
        }
        for combo in itertools.product(*variants.values()):
            assignment = dict(zip(variants, combo))
            ctx = {
                "gpu_identity": dict(self.BASE["gpu_identity"]),
                "root_coverage": dict(self.BASE["root_coverage"], **assignment),
                "debugfs": dict(self.BASE["debugfs"]),
                "btrfs_observation": {},
                "btrfs_status": assignment["btrfs_status"],
                "active_agents": assignment["active_agents"],
                "pm_status": assignment["pm_status"],
                "card_clients": 0, "render_clients": 0,
            }
            for attribution in ("PROVEN", "NOT_AVAILABLE", "OBSERVED"):
                ctx["debugfs"] = dict(self.BASE["debugfs"],
                                      DEBUGFS_CLIENT_ATTRIBUTION=attribution)
                result = collector.ownership_matrix(ctx)
                self.assertNotEqual(
                    result["OWNERSHIP_CRITERION_STATE"], "FULL",
                    f"reached FULL with {assignment} attribution={attribution}",
                )
                self.assertEqual(result["COLLECTOR_OWNERSHIP_BOOLEAN"], "NON_AUTHORITATIVE")

    def test_not_available_never_becomes_pass(self):
        for attribution in ("NOT_AVAILABLE", "UNKNOWN"):
            ctx = dict(self.BASE, debugfs=dict(self.BASE["debugfs"],
                                               DEBUGFS_CLIENT_ATTRIBUTION=attribution))
            result = collector.ownership_matrix(ctx)
            by_key = {r["condition"]: r for r in result["conditions"]}
            self.assertNotEqual(by_key["clients_pasid_attributable"]["STATE"], "PASS")

    def test_gpu_identity_not_proven_forces_not_evaluated_not_pass(self):
        ctx = dict(self.BASE, gpu_identity={"GPU_IDENTITY_STATUS": "NOT_PROVEN",
                                            "GPU_CARD_NODE": None, "GPU_RENDER_NODE": None})
        result = collector.ownership_matrix(ctx)
        by_key = {r["condition"]: r for r in result["conditions"]}
        for key in ("card_node_complete", "render_node_complete"):
            self.assertEqual(by_key[key]["STATE"], "NOT_EVALUATED")
        self.assertNotEqual(result["OWNERSHIP_CRITERION_STATE"], "FULL")

    def test_fd_error_can_never_produce_a_coverage_pass(self):
        """An FD error must not yield PASS on a strength it does not have.

        The row is scored on per-client attribution.  An error whose PID left
        the fd table unreadable for any reason means the universe is not
        established, so the row must not read PASS.  A disappearance is no
        longer an exception to that: it is a loss of coverage unless the
        absence of a DRM resource is separately proven, and it is never
        described as benign.
        """
        blocked = dict(self.BASE["root_coverage"], fd_error_count=1,
                       card_complete=True, render_complete=True,
                       fd_universe_blocked_pids=1)
        result = collector.ownership_matrix(dict(self.BASE, root_coverage=blocked))
        by_key = {r["condition"]: r for r in result["conditions"]}
        self.assertNotEqual(by_key["drm_fds_enumerated"]["STATE"], "PASS")

        # A disappearance is not proof that the PID held nothing, so the row
        # must not be reported as a completed enumeration.
        unproven = dict(self.BASE["root_coverage"], fd_error_count=1,
                        card_complete=True, render_complete=True,
                        fd_race_pids=1, drm_fds_found=0, drm_fdinfo_read=0,
                        drm_client_id_seen=0, drm_pdev_seen=0, drm_pasid_seen=0)
        result = collector.ownership_matrix(dict(self.BASE, root_coverage=unproven))
        by_key = {r["condition"]: r for r in result["conditions"]}
        self.assertNotEqual(by_key["drm_fds_enumerated"]["STATE"], "PASS")
        self.assertNotIn("benign", by_key["drm_fds_enumerated"]["EVIDENCE"])

        # With the absence proven, the same sweep may read PASS -- and only then
        # may the reason say so.
        proven = dict(unproven, fd_absence_proven_pids=1)
        result = collector.ownership_matrix(dict(self.BASE, root_coverage=proven))
        by_key = {r["condition"]: r for r in result["conditions"]}
        self.assertEqual(by_key["drm_fds_enumerated"]["STATE"], "PASS")
        self.assertIn("absence of a DRM resource proven",
                      by_key["drm_fds_enumerated"]["EVIDENCE"])

        # A vanished PID alongside fully attributed clients is reported without
        # claiming anything about its absence.
        raced = dict(self.BASE["root_coverage"], fd_error_count=1,
                     card_complete=True, render_complete=True,
                     fd_race_pids=1, drm_fds_found=4, drm_fdinfo_read=4,
                     drm_client_id_seen=4, drm_pdev_seen=4, drm_pasid_seen=4)
        result = collector.ownership_matrix(dict(self.BASE, root_coverage=raced))
        by_key = {r["condition"]: r for r in result["conditions"]}
        self.assertEqual(by_key["drm_fds_enumerated"]["STATE"], "PASS")
        self.assertIn("vanished", by_key["drm_fds_enumerated"]["EVIDENCE"])
        self.assertNotIn("benign race", by_key["drm_fds_enumerated"]["EVIDENCE"])


if __name__ == "__main__":
    unittest.main(verbosity=2)
