#!/usr/bin/env python3
"""Independence of three DRM fdinfo properties, in the producer and the consumer.

The producer used to keep ONE per-node count fed by
any(fdinfo_attribution(...).values()) over a three-key tuple.  That fused a DRM
client, a PCI device address and a PASID -- three relations from three domains
-- into a single property, and a per-node completeness term was then built from
it.  The composite is gone.

The three properties:

    drm-client-id   presence of the client key     unit FD
    drm-pdev        presence of the PCI address     unit FD
    pasid           presence of the PASID key       unit FD

Unit is FD for all three.  One drm_file can be reached through several FDs, so
none of these counts is a client count.

Nothing here may be collapsed with any(), all(), a conjunction, or a global
reading of "attributable".  These tests are behavioural: they drive the real
functions and the real consumer.  A textual scan of the source would not detect
a composite predicate, and is not used.
"""
import importlib.util
import itertools
import unittest
from pathlib import Path

_spec = importlib.util.spec_from_file_location(
    "node_field_collector", str(Path(__file__).with_name("privileged_read_collector.py"))
)
collector = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(collector)

CARD = "/dev/dri/card1"
RENDER = "/dev/dri/renderD129"

# The producer's own per-node key names, one per property.
DOMAIN_KEY = {
    "drm-client-id": "drm_client_id",
    "drm-pdev": "drm_pdev",
    "pasid": "pasid",
}
DOMAINS = tuple(DOMAIN_KEY)


def per_node_key(node, domain):
    return "%s_%s_fds" % (node, DOMAIN_KEY[domain])


# --------------------------------------------------------------------- producer

def fd(node, text):
    return {"resource": node, "fdinfo": text}


def keys(*names):
    return "".join("%s:\tx\n" % n for n in names)


class ProducerIndependence(unittest.TestCase):
    """One count per key, computed without reference to the others."""

    def test_each_key_is_counted_on_its_own(self):
        clients = [
            fd(CARD, keys("drm-driver", "drm-client-id")),
            fd(CARD, keys("drm-driver", "drm-pdev")),
            fd(CARD, keys("drm-driver", "pasid")),
        ]
        counts = collector.node_field_presence_counts(clients, (CARD, RENDER))
        self.assertEqual(counts["drm_fds"][CARD], 3)
        self.assertEqual(counts["drm-client-id"][CARD], 1)
        self.assertEqual(counts["drm-pdev"][CARD], 1)
        self.assertEqual(counts["pasid"][CARD], 1)

    def test_a_key_never_contributes_to_another(self):
        """Only drm-pdev present: the other two must see nothing."""
        clients = [fd(CARD, keys("drm-driver", "drm-pdev"))] * 4
        counts = collector.node_field_presence_counts(clients, (CARD, RENDER))
        self.assertEqual(counts["drm-pdev"][CARD], 4)
        self.assertEqual(counts["drm-client-id"][CARD], 0)
        self.assertEqual(counts["pasid"][CARD], 0)

    def test_the_three_domains_stay_in_separate_keys(self):
        """A key present on one node must not appear under another name."""
        clients = [fd(CARD, keys("drm-pdev")), fd(RENDER, keys("pasid"))]
        counts = collector.node_field_presence_counts(clients, (CARD, RENDER))
        self.assertEqual(counts["drm-pdev"][CARD], 1)
        self.assertEqual(counts["drm-pdev"][RENDER], 0)
        self.assertEqual(counts["pasid"][RENDER], 1)
        self.assertEqual(counts["pasid"][CARD], 0)
        self.assertEqual(counts["drm-client-id"][CARD], 0)
        self.assertEqual(counts["drm-client-id"][RENDER], 0)

    def test_node_completeness_does_not_depend_on_any_of_the_three(self):
        """Falsifier: the completeness term is coverage and nothing else."""
        for text in ("", keys("drm-pdev"), keys("pasid"), keys("drm-client-id"),
                     keys("drm-client-id", "drm-pdev", "pasid")):
            counts = collector.node_field_presence_counts([fd(CARD, text)], (CARD, RENDER))
            self.assertTrue(collector.node_coverage_complete(root_visibility_complete=True),
                            "node completeness moved with fdinfo content %r" % (text,))
            self.assertEqual(counts["drm_fds"][CARD], 1)

    def test_no_aggregate_symbol_of_the_three_domains_is_exported(self):
        """No exported name may group the three domains into one set again."""
        offenders = [name for name in dir(collector)
                     if "ATTRIBUTION" in name.upper() and "FIELD" in name.upper()]
        self.assertEqual(offenders, [], offenders)


# --------------------------------------------------------------------- consumer

def clause(evidence, domain):
    """The count the EVIDENCE string reports for ONE property of ONE node."""
    marker = "%s: " % domain
    start = evidence.index(marker) + len(marker)
    return int(evidence[start:evidence.index(" fd(s)", start)])


def consumer_evidence(node, **per_node):
    """Drive the REAL ownership_matrix and return that node row."""
    coverage = {
        "total_pids": 283, "fd_error_count": 0,
        "card_complete": True, "render_complete": True,
        "root_namespace_complete": True, "user_namespace_complete": True,
        "drm_fds_found": 12, "drm_fdinfo_read": 12,
        "drm_client_id_seen": 12, "drm_pdev_seen": 12, "drm_pasid_seen": 12,
        "fd_universe_blocked_pids": 0, "fd_race_pids": 0,
        "fd_absence_proven_pids": 0,
    }
    for dom in DOMAINS:
        for n in ("card", "render"):
            coverage[per_node_key(n, dom)] = 0
    coverage.update(per_node)
    context = {
        "gpu_identity": {"GPU_IDENTITY_STATUS": "PROVEN",
                         "GPU_CARD_NODE": 1, "GPU_RENDER_NODE": 129},
        "root_coverage": coverage,
        "debugfs": {"DEBUGFS_CLIENT_ATTRIBUTION": "PROVEN", "reason": "ok",
                    "clients_path": "/stub"},
        "btrfs_observation": {}, "btrfs_status": "ABSENT",
        "active_agents": 0, "pm_status": "READ",
        "card_drm_client_id_fds": 0, "render_drm_client_id_fds": 0,
    }
    rows = {r["condition"]: r for r in collector.ownership_matrix(context)["conditions"]}
    return rows["%s_node_complete" % node]


class ConsumerIndependence(unittest.TestCase):
    """A-H, executed against the real consumer.

    A composite predicate cannot survive these: if the consumer folded the three
    with any(), with all(), or by any other route, some assertion here would
    have to fail.
    """

    def test_A_to_F_one_property_moves_only_its_own_clause(self):
        for node in ("card", "render"):
            for changed in DOMAINS:
                others = [d for d in DOMAINS if d != changed]
                raised = consumer_evidence(node, **{per_node_key(node, changed): 7})
                cleared = consumer_evidence(node, **{per_node_key(node, changed): 0})
                self.assertNotEqual(clause(raised["EVIDENCE"], changed),
                                    clause(cleared["EVIDENCE"], changed),
                                    "%s did not move its own clause on %s"
                                    % (changed, node))
                for other in others:
                    self.assertEqual(clause(raised["EVIDENCE"], other),
                                     clause(cleared["EVIDENCE"], other),
                                     "changing %s moved %s on %s"
                                     % (changed, other, node))

    def test_G_two_of_three_are_never_read_as_the_third(self):
        for node in ("card", "render"):
            for absent in DOMAINS:
                others = [d for d in DOMAINS if d != absent]
                both = {per_node_key(node, d): 5 for d in others}
                evidence = consumer_evidence(node, **both)["EVIDENCE"]
                self.assertEqual(clause(evidence, absent), 0,
                                 "two properties were read as the third (%s, %s)"
                                 % (node, absent))
                for other in others:
                    self.assertEqual(clause(evidence, other), 5)

    def test_G_all_three_present_are_reported_separately(self):
        for node in ("card", "render"):
            evidence = consumer_evidence(
                node, **{per_node_key(node, d): 1 for d in DOMAINS})["EVIDENCE"]
            for domain in DOMAINS:
                self.assertEqual(clause(evidence, domain), 1, "%s on %s" % (domain, node))

    def test_H_fdinfo_content_never_moves_the_coverage_state(self):
        for content in ({}, {"card_pasid_fds": 9, "render_pasid_fds": 9}):
            row = consumer_evidence("card", **content)
            self.assertEqual(row["STATE"], "PASS",
                             "fdinfo presence moved the coverage state")

    def test_H_one_node_never_moves_the_other(self):
        render = consumer_evidence("render", card_pasid_fds=4)["EVIDENCE"]
        self.assertEqual(clause(render, "pasid"), 0,
                         "a card property leaked into the render clause")

    def test_H_exhaustive_grid_no_composite_predicate_reaches_the_consumer(self):
        """3x3x3 per node: every clause must equal the input for that property.

        If the consumer combined the three, some cell would report a value that
        was never supplied.  This replaces a textual scan of the source, which
        could not detect a composite and did match a comment.
        """
        for node in ("card", "render"):
            for combo in itertools.product((0, 1), (0, 2), (0, 3)):
                assignment = {per_node_key(node, d): v
                              for d, v in zip(DOMAINS, combo)}
                evidence = consumer_evidence(node, **assignment)["EVIDENCE"]
                for domain, value in zip(DOMAINS, combo):
                    self.assertEqual(
                        clause(evidence, domain), value,
                        "%s reported %d for %s with input %d"
                        % (node, clause(evidence, domain), domain, value))


if __name__ == "__main__":
    unittest.main()


# ------------------------------------------- scan_fds -> fdinfo_attribution

def _build_proc(root, pid, fds):
    """A procfs-shaped tree: <root>/<pid>/fd/<n> symlink, <root>/<pid>/fdinfo/<n> text."""
    import os
    fd_dir = Path(root) / str(pid) / "fd"
    info_dir = Path(root) / str(pid) / "fdinfo"
    fd_dir.mkdir(parents=True, exist_ok=True)
    info_dir.mkdir(parents=True, exist_ok=True)
    for number, (target, text) in fds.items():
        os.symlink(target, fd_dir / str(number))
        if text is not None:
            (info_dir / str(number)).write_text(text, encoding="utf-8")


class ScanFdsAccumulation(unittest.TestCase):
    """The scan_fds path, which the node-presence tests do not reach.

    ``node_field_presence_counts`` does its own per-key search, so it never calls
    ``fdinfo_attribution``.  Only ``scan_fds`` does, and it must accumulate one
    counter per key.  If it ever folded the three back into one property, the
    counters below would stop agreeing with the keys actually present.
    """

    ONLY = keys("drm-driver", "drm-client-id")
    ONLY_PDEV = keys("drm-driver", "drm-pdev")
    ONLY_PASID = keys("drm-driver", "pasid")
    ALL_THREE = keys("drm-driver", "drm-client-id", "drm-pdev", "pasid")

    def _attribution(self, text):
        import tempfile
        with tempfile.TemporaryDirectory() as raw:
            _build_proc(raw, 1923, {13: (CARD, text)})
            return collector.scan_fds(1923, {CARD}, proc_root=Path(raw))["attribution"]

    def test_one_key_present_accumulates_only_its_own_counter(self):
        for text, present, absent in (
            (self.ONLY, "drm_client_id", ("drm_pdev", "pasid")),
            (self.ONLY_PDEV, "drm_pdev", ("drm_client_id", "pasid")),
            (self.ONLY_PASID, "pasid", ("drm_client_id", "drm_pdev")),
        ):
            got = self._attribution(text)
            self.assertEqual(got[present], 1, text)
            for key in absent:
                self.assertEqual(got[key], 0,
                                 "%s counted although only %s is present" % (key, present))

    def test_all_three_present_accumulate_three_distinct_counters(self):
        got = self._attribution(self.ALL_THREE)
        for key in ("drm_client_id", "drm_pdev", "pasid"):
            self.assertEqual(got[key], 1, key)
        self.assertEqual(got["drm_fds_found"], 1)
        self.assertEqual(got["fdinfo_read"], 1)

    def test_nothing_present_accumulates_nothing(self):
        got = self._attribution(keys("drm-driver"))
        for key in ("drm_client_id", "drm_pdev", "pasid"):
            self.assertEqual(got[key], 0, key)
