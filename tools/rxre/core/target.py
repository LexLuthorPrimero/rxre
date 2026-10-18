#!/usr/bin/env python3
<<<<<<< HEAD
"""RXRE-007 FASE 1. Identidad del target y reparto de capacidades por target.

QUE ES Y QUE NO ES
-----------------
Este modulo IDENTIFICA la pieza de hardware contra la que se esta trabajando.
No interpreta ningun valor. Un target correcto con una lectura mal
interpretada sigue siendo un error; y un target mal identificado con una
lectura correcta tambien. Por eso aqui no hay ningun valor de registro, ni
offset, ni asercion semantica: eso es trabajo del decompilador y del
productor, no del que dice QUE hardware es.

Lo que si hace, y es su trabajo completo:

  1. `get_current_target()` — quien es el target, LEIDO del sistema, con la
     procedencia de cada dato anotada.
  2. `get_capabilities_for_target()` — que preguntas son validas para ese
     target, y una EXCLUSION CONSERVADORA para los que no estan mapeados.
  3. `get_target_provenance()` — por que se eligio este target.

LA EXCLUSION CONSERVADORA
------------------------
Un target sin mapear devuelve `[]`, no "todas". Es la decision de diseño
que mas importa aquí: ante la duda, se responde menos. Si se devolvieran
todas las capacidades para un target desconocido, un fallo de identificacion
pasaria desapercibido y cada lectura seria irrelevante sin que nada lo
dijera. Con `[]` el sistema dice "no se que hacer aqui", que es verdad.

PROCEDENCIA, Y POR QUE NO SE USA UN PROCESO EXTERNO
---------------------------------------------------
La identidad se lee de `/sys/bus/pci/devices/<BDF>/{vendor,device,revision}`.
MEDIDO 2026-10-14 en esta maquina:

    /sys/bus/pci/devices/0000:01:00.0/vendor    -> 0x1002
    /sys/bus/pci/devices/0000:01:00.0/device    -> 0x699f
    /sys/bus/pci/devices/0000:01:00.0/revision  -> 0xc7
    /sys/bus/pci/devices/0000:01:00.0/driver    -> .../pci/drivers/amdgpu

sysfs y no `lspci`: no hay proceso que pueda faltar, no hay texto que
parsear, y el kernel mantiene la ruta viva mientras el device este
enchufado. `lspci` es una segunda fuente, y se usa SOLO como contraste en
`_get_target_from_pci()` cuando se le pasa un BDF explicito.

El nombre del ASIC (`Polaris12`) y la generacion (`gfx_8_0`) NO salen de
sysfs: sysfs no los publica. Salen del mapa `_MAPA_PCI`, y su PROCEDENCIA
lo dice. Un nombre de ASIC escrito sin decir de donde salio es una
afirmacion que parece un hecho; aqui se declara de donde viene.
"""
from __future__ import annotations

import os
import re
from dataclasses import dataclass, field
from typing import Dict, List, Optional, Tuple

from core.capabilities import CAPACIDADES

#: Directorio de PCI en sysfs.
_SYSFS_PCI = "/sys/bus/pci/devices"

#: El UNICO PCI que este proyecto autoriza. Viene de la regla del
#: propietario: la grafica integrada del procesador (0000:00:02.0) no se
#: toca. El modulo no "elige": aplica la lista y dice.
ALLOWED_PCI = ("0000:01:00.0",)


@dataclass(frozen=True)
class TargetIdentity:
    """Identidad de una pieza de hardware.

    frozen=True a proposito: una identidad que se puede mutar en medio de
    una sesion es una identidad que ya no identifica nada. Los seis campos
    son de lectura; para cambiar de target se construye otro.
=======
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
>>>>>>> c682c4a4cf4e2c5c518a90f41e54107a7ecde6db
    """
    vendor: str
    device: str
    revision: str
    asic: str
    gfx_generation: str
<<<<<<< HEAD
    provenance: Tuple[str, ...] = field(default_factory=tuple)

    def __str__(self) -> str:  # pragma: no cover - solo legibilidad
        return ("TargetIdentity(vendor=%s device=%s rev=%s asic=%s gfx=%s)"
                % (self.vendor, self.device, self.revision, self.asic,
                   self.gfx_generation))


#: Mapa PCI -> (asic, generacion). MEDIDO: `1002:699f` es la Lexa PRO /
#: Radeon 550 de este host (`lspci -nn -d 1002:699f`), y la base de datos de
#: UMR de esta maquina nombra a ese ASIC `polaris12` con IPs `gfx_8_0` /
#: `bif_5_1` / `smu_7_1_3`, o sea generacion gfx 8.0.
#:
#: Procedencia: `lspci` para el id, `/usr/share/umr/database/polaris12.asic`
#: para el nombre del ASIC y la generacion. Ninguno de los dos valores sale
#: de este modulo por deduccion.
_MAPA_PCI: Dict[str, Tuple[str, str]] = {
    "1002:699f": ("Polaris12", "gfx_8_0"),
}

#: Rutas de donde se toma cada parte de la identidad. Se exportan para que
#: la procedencia sea un DATO y no un texto pegado en un log.
_PROCEDENCIA_PCI = "sysfs:/sys/bus/pci/devices/{bdf}/{campo}"
_PROCEDENCIA_ASIC = ("mapa declarado en core.target._MAPA_PCI, derivado de "
                     "lspci -nn -d 1002:699f y del nombre del ASIC en "
                     "/usr/share/umr/database/polaris12.asic")


def _map_pci_id_to_asic_gfx(pci_id: str) -> Optional[Tuple[str, str]]:
    """id PCI 'vendor:device' -> (asic, generacion) o None si no se conoce.

    Acepta `0x1002:0x699f`, `1002:699f` y `1002:699F`. La normalizacion es
    deliberada: quien llama puede que venga de sysfs (con 0x) o de `lspci`
    (sin 0x, en minusculas), y que esas dos formas den resultados
    distintos seria un fallo de normalizacion disfrazado de target
    desconocido.
    """
    if not isinstance(pci_id, str) or ":" not in pci_id:
        return None
    vendor, _, device = pci_id.partition(":")
    vendor = vendor.lower().removeprefix("0x").strip()
    device = device.lower().removeprefix("0x").strip()
    if not vendor or not device:
        return None
    return _MAPA_PCI.get("%s:%s" % (vendor, device))


def _get_target_from_pci(bdf: str) -> Optional[TargetIdentity]:
    """Lee la identidad de un BDF concreto desde sysfs. None si no se puede.

    No lanza excepcion si el device no existe: la ausencia de un target es
    una RESPUESTA ("no se"), no un fallo del programa. Un `FileNotFoundError`
    obligaria a que cada consumidor tratara el caso normal como error.
    """
    base = os.path.join(_SYSFS_PCI, bdf)
    try:
        with open(os.path.join(base, "vendor")) as fh:
            vendor = fh.read().strip().lower().removeprefix("0x")
        with open(os.path.join(base, "device")) as fh:
            device = fh.read().strip().lower().removeprefix("0x")
        with open(os.path.join(base, "revision")) as fh:
            revision = fh.read().strip().lower().removeprefix("0x")
    except OSError:
        return None

    par = _map_pci_id_to_asic_gfx("%s:%s" % (vendor, device))
    if par is None:
        return None
    asic, gfx = par

    prov: List[str] = [
        "PCI %s: vendor=%s device=%s rev=%s" % (bdf, vendor, device, revision),
        "vendor/device/revision leidos de " + _PROCEDENCIA_PCI.format(
            bdf=bdf, campo="{vendor,device,revision}"),
        "asic=%s gfx=%s desde %s" % (asic, gfx, _PROCEDENCIA_ASIC),
    ]
    driver = os.path.join(base, "driver")
    if os.path.exists(driver):
        try:
            prov.append("driver en uso: %s" % os.path.basename(
                os.path.realpath(driver)))
        except OSError:
            pass
    return TargetIdentity(vendor=vendor, device=device, revision=revision,
                          asic=asic, gfx_generation=gfx,
                          provenance=tuple(prov))


def _initialize_capability_mapping() -> Dict[str, List[dict]]:
    """Mapa generacion -> capacidades validas para esa generacion.

    Se construye UNA vez y se cachea. Se construye desde `CAPACIDADES` leido
    en el momento, no desde una copia: una capacidad nueva en
    `core.capabilities` entra en el mapa sin tocar este fichero. Un mapa
    escrito a mano se desincroniza del catalogo sin que nada lo note, y un
    mapa desincronizado devuelve capacidades que ya no existen.
    """
    global _MAPA_CAPACIDADES
    mapa: Dict[str, List[dict]] = {}
    for cap in CAPACIDADES:
        mapa.setdefault(cap.get("gfx_generation", ""), []).append(cap)
    _MAPA_CAPACIDADES = mapa
    return mapa


#: Cache del mapa. Lo inicializa `_initialize_capability_mapping()`.
_MAPA_CAPACIDADES: Optional[Dict[str, List[dict]]] = None


def get_current_target(bdf: Optional[str] = None) -> Optional[TargetIdentity]:
    """Target actual, LEIDO del sistema. None si no hay ninguno autorizado.

    Sin `bdf`, recorre `ALLOWED_PCI` en orden y devuelve el primero que
    exista y está mapeado. El orden es el de la allow-list, que es una
    decision del propietario, no un resultado de esta funcion.
    """
    if bdf is not None:
        return _get_target_from_pci(bdf)
    for candidato in ALLOWED_PCI:
        t = _get_target_from_pci(candidato)
        if t is not None:
            return t
    return None


def get_capabilities_for_target(target) -> List[dict]:
    """Capacidades validas para `target`. `[]` si su generacion no est&aacute; mapeada.

    LA EXCLUSION ES EL PUNTO. Una generacion sin mapa devuelve lista vacia.
    No devuelve "todas", y no lanza error: no saber que hacer en un target
    desconocido ES una respuesta valida, y es la unica segura. Devolver
    todas haria que un fallo de identificacion pasara desapercibido, con
    lectura correcta sobre el hardware equivocado.
    """
    if target is None:
        return []
    if _MAPA_CAPACIDADES is None:
        _initialize_capability_mapping()
    gen = getattr(target, "gfx_generation", "") or ""
    caps = (_MAPA_CAPACIDADES or {}).get(gen)
    return list(caps) if caps else []


def get_target_provenance(target) -> Tuple[str, ...]:
    """Por que se eligio este target. Tuple de cadenas no vacias.

    Nunca devuelve `None` ni una tupla vacia para un target existente: una
    identidad sin procedencia es una afirmacion sin respaldo, que es
    exactamente lo que el resto de RXRE no acepta. Para un target que no
    existe, devuelve una sola cadena que lo dice, en vez de una tupla vacia
    que se podria leer como "no hay nada que explicar".
    """
    if target is None:
        return ("sin target: ninguno de los PCI autorizados %s esta presente "
                "o es reconocible en esta maquina" % (ALLOWED_PCI,),)
    prov = tuple(getattr(target, "provenance", ()) or ())
    return prov if prov else ("identidad construida sin procedencia declarada",)
=======
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
>>>>>>> c682c4a4cf4e2c5c518a90f41e54107a7ecde6db
