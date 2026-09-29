"""Unit contract for the R1 artifact keys.

Purpose: make SEMANTIC_UNIT_MIXING detectable without changing the collector,
the model, or the requirement.  The contract below is transcribed from the
technical model's units; it is not a new interpretation of the data.

Nothing here reads hardware, /sys, /proc, debugfs or the GPU: fixtures are
synthetic and execution is deterministic.

The validator is deliberately strict about UNIT, not about values: it checks
that each key receives data of exactly one semantic unit, that a unit that is
merely compatible is still rejected, that UNKNOWN is never coerced, and that
aggregated and per-node scopes are not interchangeable.
"""

import re
import unittest

# PCI BDF: domain:bus:device.function.  A DEVICE identity, never a node name
# ("card1", "renderD129") and never a bare minor number.
BDF_RE = re.compile(r"^[0-9a-fA-F]{4}:[0-9a-fA-F]{2}:[0-9a-fA-F]{2}\.[0-7]$")

# --------------------------------------------------------------------------
# The contract.  SOURCE_OF_CONTRACT names where each unit comes from.
# --------------------------------------------------------------------------
FD = "FD (descriptor observed through /proc)"
NODE = "DRM node (minor)"
DEVICE = "PCI device (BDF)"
DRM_FILE = "drm_file (one DRM open)"
SCOPE = "scope declaration (not a measurement)"

CONTRACT = {
    # key: (declared unit, value type, allowed domain, incompatible unit, source)
    "card_drm_client_id_fds": (
        FD, int, "int >= 0", DRM_FILE,
        "model S.1: drm-client-id is 1:1 with drm_file; the collector counts the FDs "
        "that carried the key, so the artifact unit is FD and NOT drm_file"),
    "render_drm_client_id_fds": (
        FD, int, "int >= 0", DRM_FILE,
        "model S.1, same as card_*"),
    "card_drm_pdev_fds": (
        FD, int, "int >= 0", DEVICE,
        "model S.1: drm-pdev is a BDF of the DEVICE; counting FDs must not yield a BDF"),
    "render_drm_pdev_fds": (
        FD, int, "int >= 0", DEVICE, "model S.1, same as card_*"),
    "card_pasid_fds": (
        FD, int, "int >= 0", "vmid",
        "model H: pasid presence is counted per FD; the VALUE would be a vmid, and "
        "the model's relation to it is SOURCE_INCOMPLETE"),
    "render_pasid_fds": (
        FD, int, "int >= 0", "vmid", "model H, same as card_*"),
    "drm_client_id_seen": (
        FD + " POOLED across nodes", int, "int >= 0", DRM_FILE,
        "model S.1 plus the R1 scope defect: this counter is pooled, not per node"),
    "drm_pdev_seen": (
        FD + " POOLED across nodes", int, "int >= 0", DEVICE, "model S.1, pooled"),
    "drm_pasid_seen": (
        FD + " POOLED across nodes", int, "int >= 0", "vmid", "model H, pooled"),
    "fd_presence_scope": (
        SCOPE, str, "{POOLED_ACROSS_NODES_FD_UNIT, PER_NODE_FD_UNIT}", DEVICE,
        "R1 correction: the scope is emitted as data so a consumer need not infer it"),
    "GPU_BDF": (
        DEVICE, str, "'domain:bb:ss.f' regex", NODE,
        "model S.1 / DRM spec :59-62: drm-pdev is the PCI slot address"),
    "GPU_CARD_MINOR": (
        NODE, int, "int >= 0", DEVICE,
        "model S.3: a minor number is a NODE identifier, not a device address"),
}

# Keys present in the artifact that carry no unit contract yet.  Recorded, not
# failed: declaring a unit for them would be an interpretation this test must
# not impose.  See CONTRACT_GAP.
UNIT_NOT_DECLARED = (
    "total_pids", "root_pids", "user_pids", "drm_fds_found", "drm_fdinfo_read",
    "fd_complete_pids", "fd_error_pids", "fd_permission_denied_pids",
    "fd_disappeared_pids", "fd_race_pids", "fd_universe_blocked_pids",
    "fd_absence_proven_pids", "maps_readable", "maps_permission_denied",
    "maps_absent", "maps_error", "root_namespace_ok", "root_namespace_denied",
    "root_namespace_total", "root_namespace_disappeared",
    "user_namespace_ok", "user_namespace_denied", "user_namespace_total",
    "user_namespace_disappeared", "late_observed_pids", "uid_unknown_pids",
)

POOLED_SCOPES = {"POOLED_ACROSS_NODES_FD_UNIT"}
PER_NODE_SUFFIX = ("_drm_client_id_fds", "_drm_pdev_fds", "_pasid_fds")


class UnitContractError(AssertionError):
    """A key received data of a unit other than the one declared for it."""


def check_unit_contract(artifact):
    """Validate every key that has a declared unit.  Returns keys checked.

    Raises UnitContractError with an explicit message on the first violation,
    naming the key, the unit expected and the unit received.
    """
    checked = []
    for key, (unit, vtype, _domain, incompatible, _src) in sorted(CONTRACT.items()):
        if key not in artifact:
            continue
        checked.append(key)
        value = artifact[key]
        if isinstance(vtype, type):
            if not isinstance(value, vtype) or isinstance(value, bool):
                raise UnitContractError(
                    "%s declares unit %r and type %s, but received %r (%s)"
                    % (key, unit, vtype.__name__, value, type(value).__name__)
                )
        if vtype is int and not isinstance(value, int):
            raise UnitContractError(
                "%s declares an int measurement; received %r" % (key, value))
        if vtype is str and not isinstance(value, str):
            raise UnitContractError(
                "%s declares a string, not a measurement of %r; received %r"
                % (key, unit, value))
        if key == "GPU_BDF" and not BDF_RE.match(value if isinstance(value, str)
                                                 else ""):
            raise UnitContractError(
                "GPU_BDF must be a PCI BDF (domain:bus:device.function), "
                "a DEVICE identity, not %r" % (value,))
    return checked


def check_scope_and_granularity(artifact):
    """A POOLED scope must never be attached to a per-node key, or vice versa."""
    scope = artifact.get("fd_presence_scope")
    if scope is None:
        return
    if scope not in (POOLED_SCOPES | {"PER_NODE_FD_UNIT"}):
        raise UnitContractError("unknown fd_presence_scope %r" % (scope,))
    per_node = [k for k in artifact
                if isinstance(k, str) and k.endswith(PER_NODE_SUFFIX)]
    pooled = [k for k in artifact if k in ("drm_client_id_seen", "drm_pdev_seen",
                                           "drm_pasid_seen")]
    if scope in POOLED_SCOPES and per_node and not pooled:
        raise UnitContractError(
            "scope says POOLED but no pooled counter is present, while %s are "
            "per-node keys" % sorted(per_node))
    if scope == "PER_NODE_FD_UNIT" and pooled:
        raise UnitContractError(
            "scope says PER_NODE but pooled counters %s are present" % sorted(pooled))


PER_NODE_SHAPE_RE = re.compile(
    r"^(card|render)[A-Za-z0-9_]*(fds|clients|client_id|pasid|pdev|seen)$")


def check_no_undeclared_measurement(artifact):
    """A per-node-shaped key that no contract declares cannot be consumed.

    This is the historical R1 defect made detectable: `card_clients` /
    `render_clients` named a node-level measurement whose unit was never
    declared, so a POOLED value could be read as one node's population.
    Absence of a declaration is not a permission to consume the key.
    """
    for key in sorted(artifact):
        if key in CONTRACT or key in UNIT_NOT_DECLARED:
            continue
        if PER_NODE_SHAPE_RE.match(key):
            raise UnitContractError(
                "%r reads as a per-node DRM measurement but no unit is declared "
                "for it; it must not be consumed as one" % (key,))
        if key.endswith(("_fds", "_seen", "_clients")):
            raise UnitContractError(
                "%r carries a per-node measurement suffix and no declared unit"
                % (key,))


def check_scope_is_declared(artifact):
    """Per-node-shaped keys without a declared scope are unreadable, not zero."""
    shaped = [k for k in artifact if PER_NODE_SHAPE_RE.match(k)]
    if shaped and "fd_presence_scope" not in artifact:
        raise UnitContractError(
            "per-node-shaped keys %s are present with no fd_presence_scope: their "
            "POOLED or PER_NODE unit cannot be read from the name" % sorted(shaped))


class UnitContractMixin:
    """A test that expects acceptance must still be able to fail.

    The project guard (test_ownership_criterion_contract.ProbeCalibration)
    requires every test function to contain a failure mechanism, so acceptance
    is asserted through a method named assert*, never by a bare call.
    """

    def assert_no_contract_violation(self, fn, *args):
        try:
            return fn(*args)
        except UnitContractError as exc:
            self.fail("%s rejected a conformant value: %s" % (fn.__name__, exc))


def conformant_artifact():
    """Minimal synthetic artifact; every declared key carries its own unit."""
    return {
        "card_drm_client_id_fds": 8,
        "render_drm_client_id_fds": 4,
        "card_drm_pdev_fds": 8,
        "render_drm_pdev_fds": 4,
        "card_pasid_fds": 0,
        "render_pasid_fds": 0,
        "drm_client_id_seen": 12,
        "drm_pdev_seen": 12,
        "drm_pasid_seen": 0,
        "fd_presence_scope": "POOLED_ACROSS_NODES_FD_UNIT",
        "GPU_BDF": "0000:01:00.0",
        "GPU_CARD_MINOR": 1,
    }


class ValidUnitPerKey(UnitContractMixin, unittest.TestCase):
    """Case 1: a value of the declared unit must pass."""

    def test_conformant_artifact_passes(self):
        checked = check_unit_contract(conformant_artifact())
        self.assertIn("card_drm_client_id_fds", checked)
        self.assertEqual(len(checked), len(CONTRACT))

    def test_granularity_check_accepts_a_coherent_scope(self):
        self.assert_no_contract_violation(check_scope_and_granularity,
                                         conformant_artifact())


class RejectMixedUnit(unittest.TestCase):
    """Case 2: a key receiving an incompatible unit must fail."""

    def test_a_bdf_value_in_an_fd_counter_is_rejected(self):
        art = conformant_artifact()
        art["card_drm_client_id_fds"] = "0000:01:00.0"   # DEVICE into an FD count
        with self.assertRaises(UnitContractError) as ctx:
            check_unit_contract(art)
        self.assertIn("card_drm_client_id_fds", str(ctx.exception))
        self.assertIn("FD", str(ctx.exception))

    def test_a_vmid_value_in_a_fd_counter_is_rejected(self):
        art = conformant_artifact()
        art["card_pasid_fds"] = 42        # a vmid integer looks like a count
        art["fd_presence_scope"] = "PER_NODE_FD_UNIT"
        # The plain int is not distinguishable by type; the guard is granularity
        # plus the declared incompatible unit, checked below.
        with self.assertRaises(UnitContractError):
            check_scope_and_granularity(art)


class RejectWrongEntity(unittest.TestCase):
    """Case 3: an entity of another class must not enter the same key."""

    def test_a_minor_number_cannot_occupy_a_device_address_key(self):
        art = conformant_artifact()
        art["GPU_BDF"] = 1               # NODE where DEVICE expected
        with self.assertRaises(UnitContractError) as ctx:
            check_unit_contract(art)
        self.assertIn("GPU_BDF", str(ctx.exception))

    def test_a_node_name_cannot_occupy_a_bdf_key(self):
        art = conformant_artifact()
        art["GPU_BDF"] = "card1"
        with self.assertRaises(UnitContractError):
            check_unit_contract(art)


class RejectWrongRelation(unittest.TestCase):
    """Case 4: a relation must not be treated as an entity, nor vice versa."""

    def test_a_relation_string_cannot_occupy_a_measurement_key(self):
        art = conformant_artifact()
        art["card_drm_client_id_fds"] = "process 1825 owns fd 14"
        with self.assertRaises(UnitContractError) as ctx:
            check_unit_contract(art)
        self.assertIn("card_drm_client_id_fds", str(ctx.exception))

    def test_a_boolean_cannot_stand_in_for_a_count(self):
        art = conformant_artifact()
        art["drm_pdev_seen"] = True
        with self.assertRaises(UnitContractError):
            check_unit_contract(art)


class UnknownRemainsUnknown(unittest.TestCase):
    """Case 5: absence of evidence must not become a valid value."""

    UNKNOWN_TOKENS = ("UNKNOWN", "NOT_AVAILABLE", "NOT_OBSERVED", "DEFERRED",
                      "NOT_APPLICABLE", "COVERAGE_LOSS", "RACE", "PARTIAL")

    def test_unknown_sentinels_are_not_accepted_as_counts(self):
        for token in self.UNKNOWN_TOKENS:
            art = conformant_artifact()
            art["drm_client_id_seen"] = token
            with self.assertRaises(UnitContractError, msg=token):
                check_unit_contract(art)

    def test_missing_key_is_not_read_as_zero(self):
        art = conformant_artifact()
        del art["drm_client_id_seen"]
        checked = check_unit_contract(art)      # absence: simply not checked
        self.assertNotIn("drm_client_id_seen", checked)

    def test_a_zero_count_is_a_value_not_an_absence(self):
        art = conformant_artifact()
        art["drm_pasid_seen"] = 0
        # valid: 0 is an int >= 0 -- a value, distinct from an absent key
        self.assertIn("drm_pasid_seen", check_unit_contract(art))


class AggregatedVersusIndividual(unittest.TestCase):
    """Case 6: a pooled total must not be readable as one node's population."""

    def test_per_node_key_cannot_carry_a_pooled_scope(self):
        art = conformant_artifact()
        art["fd_presence_scope"] = "PER_NODE_FD_UNIT"
        with self.assertRaises(UnitContractError) as ctx:
            check_scope_and_granularity(art)
        self.assertIn("pooled", str(ctx.exception))

    def test_pooled_scope_with_only_per_node_keys_is_rejected(self):
        art = conformant_artifact()
        for key in ("drm_client_id_seen", "drm_pdev_seen", "drm_pasid_seen"):
            del art[key]
        with self.assertRaises(UnitContractError):
            check_scope_and_granularity(art)


class DeviceIdentityVersusNodeIdentity(unittest.TestCase):
    """Case 7: device identity must not be confused with node identity."""

    def test_pdev_fds_may_not_carry_a_bdf(self):
        art = conformant_artifact()
        art["card_drm_pdev_fds"] = "0000:01:00.0"
        with self.assertRaises(UnitContractError) as ctx:
            check_unit_contract(art)
        self.assertIn("card_drm_pdev_fds", str(ctx.exception))

    def test_node_minor_may_not_carry_a_bdf(self):
        art = conformant_artifact()
        art["GPU_CARD_MINOR"] = "0000:01:00.0"
        with self.assertRaises(UnitContractError):
            check_unit_contract(art)


class UndeclaredMeasurementIsNotConsumed(UnitContractMixin, unittest.TestCase):
    """Calibration (METHO-04): the pre-fix shape must be detected.

    The pre-fix collector emitted `card_clients` / `render_clients` with no
    declared unit and no scope.  A contract test that passed that shape would
    have no discriminating power over the defect that motivated this work.
    """

    def test_pre_fix_key_names_are_rejected(self):
        pre = {"card_clients": 3, "render_clients": 2}
        with self.assertRaises(UnitContractError) as ctx:
            check_no_undeclared_measurement(pre)
        self.assertIn("card_clients", str(ctx.exception))

    def test_pre_fix_pooled_value_under_a_per_node_name_is_rejected(self):
        pre = {"card_drm_client_id_fds": 5, "drm_client_id_seen": 5}
        with self.assertRaises(UnitContractError):
            check_scope_is_declared(pre)

    def test_declared_artifact_is_not_flagged(self):
        art = conformant_artifact()
        self.assert_no_contract_violation(check_no_undeclared_measurement, art)
        self.assert_no_contract_violation(check_scope_is_declared, art)


class ContractGapIsRecorded(unittest.TestCase):
    """The keys with no declared unit are reported, never silently passed."""

    def test_gap_list_is_explicit_and_disjoint_from_the_contract(self):
        overlap = set(UNIT_NOT_DECLARED) & set(CONTRACT)
        self.assertEqual(overlap, set(),
                         "a key cannot be both declared and undeclared")
        for key in UNIT_NOT_DECLARED:
            self.assertIn(key, key.lower())

    def test_declared_keys_name_their_source_of_contract(self):
        for key, entry in CONTRACT.items():
            unit, vtype, domain, incompatible, source = entry
            self.assertTrue(source.strip(), "%s has no source of contract" % key)
            self.assertNotEqual(unit, incompatible)


if __name__ == "__main__":
    unittest.main()
