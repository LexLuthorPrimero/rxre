#!/usr/bin/env python3
# SPDX-License-Identifier: GPL-2.0
"""core/target.py — Target identification and ASIC-aware routing.

This module provides:
  - TargetIdentity: an immutable representation of a compute target (PCI vendor/device,
    ASIC, GFX generation, etc.)
  - get_current_target(): returns the identity read at 0000:01:00.0,
    or None on mismatch/absence (never a synthetic RX550).
  - get_capabilities_for_target(target): returns the subset of RXRE capabilities
    that are relevant for the given target.
  - target_provenance(target): returns the provenance of how the target was
    determined.

The routing logic ensures that capabilities are only considered relevant if they
are explicitly mapped to the target or have no target restrictions (i.e., are
target-agnostic). This prevents silent exclusion of candidates and makes target
mismatch reasons explicit.

This module does not perform semantic interpretation of hardware; it only
determines which capabilities are applicable to a given target based on
evidence such as PCI IDs and kernel source mappings.

Example usage:
    from rxre.core.target import get_current_target, get_capabilities_for_target
    target = get_current_target()
    capabilities = get_capabilities_for_target(target)
"""

from __future__ import annotations

import dataclasses
import os
from typing import Any, List, Optional, Tuple

from . import capabilities as caps

# Known target to capability mapping.
# Each capability is identified by its "capability" key in the CAPACIDADES list.
# This mapping declares which capabilities are relevant for which GFX generation.
# If a capability is not listed for a target, it is considered not relevant.
# Capabilities not listed for any target are considered target-agnostic (always relevant).
_KNOWN_TARGETS = {"gfx_8_0", "gfx_9_0", "gc_9_0", "si_2_0"}

# ---------------------------------------------------------------------------
# Target identity representation
# ---------------------------------------------------------------------------


@dataclasses.dataclass(frozen=True, eq=True)
class TargetIdentity:
    """Immutable identity of a compute target.

    Fields:
        vendor: PCI vendor ID (e.g., "1002" for AMD)
        device: PCI device ID (e.g., "699f" for RX550)
        revision: PCI revision ID (e.g., "c7")
        asic: ASIC name (e.g., "Polaris12")
        gfx_generation: GFX generation (e.g., "gfx_8_0")
        provenance: list of evidence strings describing how this identity was
            determined (e.g., ["PCI 1002:699f", "kernel mapping Polaris12->gfx_8_0"])
    """
    vendor: str
    device: str
    revision: str
    asic: str
    gfx_generation: str
    provenance: Tuple[str, ...] = dataclasses.field(default_factory=tuple)
    bdf: str = "unknown"
    subsystem_vendor: str = "unknown"
    subsystem_device: str = "unknown"

    def __post_init__(self):
        # Ensure provenance is a tuple for immutability
        if not isinstance(self.provenance, tuple):
            object.__setattr__(self, 'provenance', tuple(self.provenance))

    def with_provenance(self, *evidence: str) -> 'TargetIdentity':
        """Return a new TargetIdentity with additional provenance evidence."""
        new_provenance = self.provenance + evidence
        return dataclasses.replace(self, provenance=new_provenance)

    def is_unknown(self) -> bool:
        """Return True if any core field is unknown (placeholder)."""
        return any(not field or field == "unknown" for field in
                   (self.bdf, self.vendor, self.device, self.revision,
                    self.subsystem_vendor, self.subsystem_device,
                    self.asic, self.gfx_generation))


# ---------------------------------------------------------------------------
# Target detection
# ---------------------------------------------------------------------------


EXPECTED_BDF = "0000:01:00.0"
EXPECTED_REVISION = "c7"
EXPECTED_SUBSYSTEM = ("1002", "0b04")


def _pci_hex(node: str, name: str, width: int) -> str:
    """Read one sysfs identity field; absence is explicit, never a default."""
    try:
        with open(os.path.join(node, name), "r", encoding="ascii") as f:
            return f"{int(f.read().strip(), 16):0{width}x}"
    except (OSError, ValueError):
        return "unknown"


def _get_target_from_pci(pci_sys_path: str = "/sys/bus/pci/devices") -> Optional[TargetIdentity]:
    """Read only the addressed RX550 PCI function; never select the first AMD.

    None means no verified match (or insufficient vendor/device evidence).
    A partial identity explicitly says which revision/subsystem fields are
    unknown; such an identity must not authorize physical capability routing.
    """
    node = os.path.join(pci_sys_path, EXPECTED_BDF)
    if not os.path.isdir(node):
        return None
    vendor = _pci_hex(node, "vendor", 4)
    device = _pci_hex(node, "device", 4)
    if (vendor, device) != ("1002", "699f"):
        return None

    revision = _pci_hex(node, "revision", 2)
    subvendor = _pci_hex(node, "subsystem_vendor", 4)
    subdevice = _pci_hex(node, "subsystem_device", 4)
    # A different measured revision or subsystem is a mismatch, not a variant
    # for which the project's known target may be assumed.
    if revision not in ("unknown", EXPECTED_REVISION):
        return None
    if subvendor not in ("unknown", EXPECTED_SUBSYSTEM[0]):
        return None
    if subdevice not in ("unknown", EXPECTED_SUBSYSTEM[1]):
        return None

    asic, gfx_generation = _map_pci_id_to_asic_gfx(vendor, device)
    provenance = [f"sysfs:{node}/vendor=0x{vendor}",
                  f"sysfs:{node}/device=0x{device}"]
    for name, value in (("revision", revision),
                        ("subsystem_vendor", subvendor),
                        ("subsystem_device", subdevice)):
        provenance.append(f"sysfs:{node}/{name}=" +
                          ("NOT_OBSERVED" if value == "unknown" else f"0x{value}"))
    provenance.append(f"kernel mapping:1002:699f -> {asic}/{gfx_generation}")
    return TargetIdentity(vendor=vendor, device=device, revision=revision,
                          asic=asic, gfx_generation=gfx_generation,
                          provenance=tuple(provenance), bdf=EXPECTED_BDF,
                          subsystem_vendor=subvendor,
                          subsystem_device=subdevice)


def _map_pci_id_to_asic_gfx(vendor: str, device: str) -> Tuple[Optional[str], Optional[str]]:
    """Map a PCI vendor/device ID to an ASIC and GFX generation.

    This mapping is based on evidence from the AMDGPU kernel source.
    We only include mappings that are verified for this project's target.

    Returns:
        (asic_name, gfx_generation) or (None, None) if unknown.
    """
    # Known mappings for the RX550 (Polaris12) and other relevant ASICs.
    # Each entry is (vendor, device) -> (asic, gfx_generation)
    # We only include the RX550 for now; other mappings can be added as
    # evidence becomes available.
    MAPPING = {
        ("1002", "699F"): ("Polaris12", "gfx_8_0"),
        # Add other mappings here as they become verified.
        # Example: ("1002", "67df"): ("Polaris11", "gfx_8_0"),  # RX 560
    }
    return MAPPING.get((vendor.upper(), device.upper()), (None, None))


def get_current_target(pci_sys_path: str = "/sys/bus/pci/devices") -> Optional[TargetIdentity]:
    """Return observed identity at 0000:01:00.0 or None on mismatch/absence.

    No synthetic RX550 is returned when the sysfs producer is unavailable.
    A missing revision or subsystem is reported in the partial identity and
    cannot be used as a verified physical target.
    """
    return _get_target_from_pci(pci_sys_path)


# ---------------------------------------------------------------------------
# Capability routing
# ---------------------------------------------------------------------------


# We maintain a mapping from target GFX generation to the set of capability
# names that are known to be relevant for that target.
# This mapping is initialized as empty and will be populated by
# _initialize_capability_mapping().
#
# The mapping is conservative: if a capability is not listed for a target,
# we assume it is not relevant (unless it has no target restrictions,
# which we handle separately).
#
# We avoid circular imports by importing capabilities only inside functions.
_CAPABILITY_MAPPING: dict[str, set[str]] = {}


def _initialize_capability_mapping() -> None:
    """Populate the capability mapping for known targets.

    For now, we assume that all existing capabilities are relevant for the
    known RX550 target (gfx_8_0) because we have no evidence to the contrary.
    This is a starting point; the mapping will be refined as we gain
    evidence about which capabilities are target-specific.

    We do this initialization once at module load time.
    """
    global _CAPABILITY_MAPPING
    if _CAPABILITY_MAPPING:
        return  # Already initialized

    # Import capabilities here to avoid circular imports at module level.
    from . import capabilities as caps

    # Start with an empty mapping for all known targets.
    # We'll add the RX550 target (gfx_8_0) with all capabilities.
    # Other targets can be added as we learn about them.
    _CAPABILITY_MAPPING = {
        "gfx_8_0": {c["capability"] for c in caps.CAPACIDADES},
        # Add other targets here as evidence becomes available.
        # Example: "gfx_9_0": { ... },
    }


def get_capabilities_for_target(target: TargetIdentity) -> List[Dict[str, Any]]:
    """Return the list of RXRE capabilities relevant for the given target.

    A capability is considered relevant if:
      - It has no target restrictions (i.e., it is target-agnostic), OR
      - It is explicitly mapped to the target's GFX generation.

    Target-agnostic capabilities are those that do not appear in the
    _CAPABILITY_MAPPING for any target. Since we currently map all
    capabilities to gfx_8_0, there are none. This will change as we
    add more specific mappings.

    Args:
        target: The TargetIdentity for which to retrieve capabilities.

    Returns:
        A list of capability dicts (from capabilities.CAPACIDADES) that are
        relevant for the target.
    """
    _initialize_capability_mapping()

    if target is None:
        return []
    # Explicitly physical identities must be complete and match this board.
    # Legacy BDF-less identities are only useful for hypothetical/static routing.
    if target.bdf != "unknown" and (
        target.bdf != EXPECTED_BDF or target.is_unknown() or
        target.vendor.lower() != "1002" or target.device.lower() != "699f" or
        target.revision.lower() != EXPECTED_REVISION or
        (target.subsystem_vendor.lower(), target.subsystem_device.lower()) != EXPECTED_SUBSYSTEM
    ):
        return []
    if target.gfx_generation == "unknown":
        return []

    # Get the set of capability names that are relevant for this target's GFX.
    relevant_names = _CAPABILITY_MAPPING.get(target.gfx_generation, set())

    # If we have no mapping for this GFX generation, we return an empty list.
    # This is conservative: we prefer to miss a capability than to incorrectly
    # include one that might not be relevant.
    if not relevant_names:
        return []

    # Import capabilities here to avoid circular imports.
    from . import capabilities as caps

    # Return the capabilities whose names are in the relevant set.
    return [c for c in caps.CAPACIDADES if c["capability"] in relevant_names]


def get_target_provenance(target: TargetIdentity) -> Tuple[str, ...]:
    """Return the provenance of how the target was determined.

    Args:
        target: The TargetIdentity whose provenance is requested.

    Returns:
        A tuple of strings describing the evidence and reasoning used to
        determine the target.
    """
    return target.provenance


# ---------------------------------------------------------------------------
# Self-test
# ---------------------------------------------------------------------------


def _self_test() -> int:
    """Run a simple self-test of the target module.

    Returns:
        0 if all tests pass, non-zero otherwise.
    """
    failures = []

    # Real identity is a runtime precondition, not a self-test fixture.
    target = get_current_target()
    if target is None or target.is_unknown():
        print("TARGET SELF-TEST: no complete physical identity at 0000:01:00.0")
        return 1
    if (target.bdf, target.vendor, target.device, target.revision,
        target.subsystem_vendor, target.subsystem_device) != (
            EXPECTED_BDF, "1002", "699f", EXPECTED_REVISION, *EXPECTED_SUBSYSTEM):
        failures.append("physical identity mismatches the board contract")

    prov = get_target_provenance(target)
    if not all(any(field in p for p in prov) for field in
               ("vendor", "device", "revision", "subsystem_vendor", "subsystem_device")):
        failures.append("sysfs identity provenance is incomplete")

    caps_list = get_capabilities_for_target(target)
    if not isinstance(caps_list, list):
        failures.append("get_capabilities_for_target did not return a list")
    elif len(caps_list) == 0:
        failures.append("get_capabilities_for_target returned an empty list for the known target")

    # Test 4: Each capability in the list is a dict with the expected keys.
    from . import capabilities as caps
    for i, cap in enumerate(caps_list):
        if not isinstance(cap, dict):
            failures.append(f"Item {i} in capabilities list is not a dict: {type(cap)}")
        elif "capability" not in cap:
            failures.append(f"Item {i} in capabilities list has no 'capability' key")

    if failures:
        for f in failures:
            print(f"TARGET SELF-TEST FAILURE: {f}")
        return 1
    else:
        print("TARGET SELF-TEST PASSED")
        return 0


if __name__ == "__main__":
    # When run directly, execute the self-test.
    exit(_self_test())
