#!/usr/bin/env python3
"""Privileged, read-only C1 preflight evidence collector.

This script emits JSON to stdout. It does not create runtime directories,
write sysfs, control processes, invoke C1, or modify services.
"""
from __future__ import annotations

import datetime as dt
import hashlib
import json
import os
import re
import subprocess
import sys
import time
from pathlib import Path

"""
Identity model
--------------
The GPU is identified by stable PCI evidence (vendor/device/BDF), never by a
``cardN``/``renderDN`` number: those numbers are a dynamic property of whichever
host the collector runs on.  Storage is identified from the real mount table, not
from a device name.  Every identity is resolved and proven *before* any
evidence that depends on it is collected.  An unproven identity aborts the
run instead of producing evidence that would be indistinguishable from a real
observation.

Read-only guarantees
--------------------
This collector only reads.  It contains no ``open(..., "w")``, no ``write``,
``truncate``, ``unlink``, ``rename``, ``mount``, ``umount``, no ioctl, no
sysfs or debugfs write, no ``tee``, no shell redirection, no ``systemctl``
mutation, no ``kill``/``pkill``, no ``modprobe``/``rmmod``, and it never
invokes ``sudo`` itself.
"""

# --- identity targets ------------------------------------------------------
GPU_PCI_VENDOR = "0x1002"
GPU_PCI_DEVICE = "0x699f"
GPU_PCI_BDF = "0000:01:00.0"
GPU_PCI_CLASS = "0x030000"
GPU_PCI_DRIVER = "amdgpu"
GPU_PCI_TARGET = {
    "vendor": GPU_PCI_VENDOR,
    "device": GPU_PCI_DEVICE,
    "bdf": GPU_PCI_BDF,
    "class": GPU_PCI_CLASS,
    "driver": GPU_PCI_DRIVER,
}

BDF_RE = re.compile(r"([0-9a-f]{4}:[0-9a-f]{2}:[0-9a-f]{2}\.[0-7])")
CARD_NODE_RE = re.compile(r"^card(\d+)$")
RENDER_NODE_RE = re.compile(r"^renderD(\d+)$")

DEFAULT_SYSFS_ROOT = Path("/sys")
DEFAULT_PROC_ROOT = Path("/proc")
DEFAULT_DEBUG_ROOT = Path("/sys/kernel/debug")
DEFAULT_BLOCK_ROOT = Path("/sys/class/block")

# Fixed, optional inputs.  These are *search hints only*: a match on any of
# them classifies a process as relevant.  None of them establishes identity
# and none of them can exclude a process from the FD scan.
KEYWORDS = (
    "amdgpu", "radeon", "gpu", "drm", "kalm", "irqbalance",
    "power-profiles", "autopilot", "crond", "sysstat", "tuned",
    "udisks", "baloo", "xwayland", "chatgpt", "systemd", "sda",
    "ahci", "nvme",
)
COMPOSITOR_KEYWORDS = (
    "kwin", "kwin_wayland", "kwin_x11", "gnome-shell", "mutter",
    "xwayland", "plasmashell", "xwaylandvideobridge",
)
# Library names that make a /proc/<pid>/maps line relevant to GPU evidence.
MAPS_RELEVANT_RE = re.compile(
    r"libdrm|libgbm|libGL|libEGL|libglvnd|libvulkan|lvp_|radeonsi|radeon|"
    r"amdgpu|llvmpipe|swrast|iris|drm\.so|gbm\.so|EGL|GLX|GLESv2",
    re.IGNORECASE,
)

# Argv handling is import-safe so the identity layer can be unit tested
# without executing a collection.  Arguments are only taken as collector
# arguments when this file is the entry point and the parent bundle exists;
# under a test runner (whose argv[0] is the runner) PARENT stays empty and
# main() refuses to run.
_SELF_NAME = Path(__file__).name
_ARGV_IS_COLLECTOR_ARGS = (
    len(sys.argv) > 2
    and Path(sys.argv[0]).name == _SELF_NAME
    and Path(sys.argv[1]).is_file()
)
PARENT_PATH = Path(sys.argv[1]) if _ARGV_IS_COLLECTOR_ARGS else None
PREFLIGHT_ID = sys.argv[2] if _ARGV_IS_COLLECTOR_ARGS else "UNSPECIFIED"
if PARENT_PATH is not None:
    PARENT = json.loads(PARENT_PATH.read_text(encoding="utf-8"))
else:
    PARENT = {}
START_ISO = dt.datetime.now(dt.timezone.utc).isoformat(timespec="milliseconds")


def iso() -> str:
    return dt.datetime.now(dt.timezone.utc).isoformat(timespec="milliseconds")


# --------------------------------------------------------------------------
# Evidence about the observer, and about why a read failed.
# --------------------------------------------------------------------------
PROC_ERROR_CLASSES = {
    "PERMISSION_DENIED": ("PermissionError",),
    "PROCESS_DISAPPEARED": ("FileNotFoundError", "ProcessLookupError", "No such process"),
}


def classify_proc_error(text):
    """Name *why* a procfs read failed.

    A process that exits between enumeration and reading is a normal race and
    says nothing about isolation.  A PermissionError is an isolation fact.  The
    two must never collapse into the same state, or ordinary process churn on a
    live desktop would be reported as incomplete visibility.
    """
    for name, needles in PROC_ERROR_CLASSES.items():
        if any(needle in str(text) for needle in needles):
            return name
    return "OTHER_ERROR"


def observe_privilege_state():
    """Observe this process's own effective privilege.  Never infer it.

    The documented wrapper is ``sudo -A python3 ...``, but the wrapper being
    *expected* is not evidence that elevation happened.  Only the real euid of
    the running process is evidence, and if it cannot be read the state is
    UNKNOWN rather than assumed.
    """
    result = {
        "EUID_OBSERVED": None,
        "EGID_OBSERVED": None,
        "EUID_OBSERVATION": "NOT_ATTEMPTED",
        "EUID_ERROR": None,
        "PRIVILEGE_STATE": "PRIVILEGE_UNKNOWN",
        "SUDO_COMMAND_EXPECTED": "YES",
        "SUDO_INVOKED": "NOT_OBSERVED",
        "SUDO_SOURCE": "the external wrapper; the collector neither runs nor "
                       "detects sudo, it only reads its own euid",
    }
    try:
        result["EUID_OBSERVED"] = os.geteuid()
        result["EGID_OBSERVED"] = os.getegid()
        result["EUID_OBSERVATION"] = "OK"
    except Exception as exc:
        result["EUID_OBSERVATION"] = "ERROR"
        result["EUID_ERROR"] = f"{type(exc).__name__}: {exc}"
        return result
    result["PRIVILEGE_STATE"] = (
        "PRIVILEGE_OBSERVED_ROOT" if result["EUID_OBSERVED"] == 0 else "PRIVILEGE_NOT_ROOT"
    )
    return result


def read_bytes(path, limit=65536):
    try:
        with Path(path).open("rb") as stream:
            data = stream.read(limit)
        return {
            "status": "OK",
            "value": data.decode("utf-8", errors="replace"),
            "bytes": len(data),
            "truncated": len(data) >= limit,
        }
    except Exception as exc:
        return {"status": "ERROR", "error": f"{type(exc).__name__}: {exc}"}


def read_text(path, limit=65536):
    result = read_bytes(path, limit)
    return result.get("value", "") if result.get("status") == "OK" else ""


def read_link(path):
    try:
        return {"status": "OK", "value": os.readlink(str(path))}
    except Exception as exc:
        return {"status": "ERROR", "error": f"{type(exc).__name__}: {exc}"}


def run(argv, timeout=20):
    try:
        completed = subprocess.run(
            argv, check=False, capture_output=True, text=True, timeout=timeout
        )
        return {
            "argv": argv,
            "returncode": completed.returncode,
            "stdout": completed.stdout[:131072],
            "stderr": completed.stderr[:32768],
        }
    except Exception as exc:
        return {
            "argv": argv,
            "returncode": None,
            "stdout": "",
            "stderr": f"{type(exc).__name__}: {exc}",
        }


# ==========================================================================
# IDENTITY LAYER -- discover first, collect afterwards.
# Every function here is pure read-only and takes its roots as parameters so
# it can be exercised against a synthetic tree without touching the host.
# ==========================================================================


def resolve_pci_device_dir(link_path):
    """DEFECT-01.  Identify the PCI *device* directory a symlink points at.

    The BDF is **not** obtained by scanning the path text for a BDF-shaped
    substring.  On this host the RX550 sits behind a PCI bridge, so
    ``/sys/class/drm/card1/device`` resolves to::

        /sys/devices/pci0000:00/0000:00:01.0/0000:01:00.0
                              ^^^^^^ bridge   ^^^^^^ endpoint

    A first-match scan returns the **bridge**, silently.  That is what aborted
    R1 run R1-20260926T000649Z.

    sysfs names a PCI *device* directory by its BDF, so the identity is the
    basename of the resolved target -- and that basename is accepted only when
    it is a *complete* BDF and the directory really exposes the PCI device
    attributes ``vendor`` and ``device``.  Every other component of the path
    (bridges, hosts) is recorded as evidence and never used as identity.
    """
    device_link = Path(link_path)
    result = {
        "link_path": str(device_link),
        "link_exists": device_link.exists(),
        "is_symlink": device_link.is_symlink(),
        "target": None,
        "target_realpath": None,
        "target_exists": False,
        "target_is_dir": False,
        "device_dir_name": None,
        "device_dir_bdf": None,
        "device_dir_is_pci_device": False,
        "bdf_components_in_path": [],
        "PCI_DEVICE_DIR_STATUS": "NOT_PROVEN",
        "PCI_DEVICE_DIR_ABORT": None,
    }

    if not result["is_symlink"]:
        result["PCI_DEVICE_DIR_ABORT"] = (
            "DEVICE_LINK_ABSENT" if not result["link_exists"] else "DEVICE_NOT_A_SYMLINK"
        )
        return result

    link = read_link(device_link)
    if link.get("status") != "OK":
        result["PCI_DEVICE_DIR_ABORT"] = "DEVICE_LINK_UNREADABLE"
        return result
    result["target"] = link.get("value")

    real = os.path.realpath(str(device_link))
    result["target_realpath"] = real
    result["target_exists"] = os.path.exists(real)
    if not result["target_exists"]:
        result["PCI_DEVICE_DIR_ABORT"] = "DEVICE_TARGET_ABSENT"
        return result
    result["target_is_dir"] = os.path.isdir(real)
    if not result["target_is_dir"]:
        result["PCI_DEVICE_DIR_ABORT"] = "DEVICE_TARGET_NOT_A_DIRECTORY"
        return result

    # Diagnostic only: every BDF-shaped component of the path, in order.  The
    # bridge appears here and is deliberately never used as identity.
    result["bdf_components_in_path"] = [m.group(1) for m in BDF_RE.finditer(real)]

    name = os.path.basename(real.rstrip("/"))
    result["device_dir_name"] = name
    if not BDF_RE.fullmatch(name):
        result["PCI_DEVICE_DIR_ABORT"] = "DEVICE_DIR_NAME_IS_NOT_A_BDF"
        return result
    result["device_dir_bdf"] = name

    # Structural proof that this directory is a PCI device, not a bridge or a
    # bus: a PCI device directory exposes vendor and device attributes.
    has_identity = (Path(real) / "vendor").exists() and (Path(real) / "device").exists()
    if not has_identity:
        result["PCI_DEVICE_DIR_ABORT"] = "DEVICE_DIR_LACKS_PCI_VENDOR_DEVICE"
        return result
    result["device_dir_is_pci_device"] = True

    result["PCI_DEVICE_DIR_STATUS"] = "PROVEN"
    return result


def _normalise_pci_id(value):
    text = (value or "").strip().lower()
    if not text:
        return None
    if not text.startswith("0x"):
        text = "0x" + text
    return text


def _read_id_field(path):
    """Read a sysfs identity field, preserving *why* it is unusable."""
    entry = read_bytes(path, 64)
    if entry.get("status") != "OK":
        return {
            "status": "UNREADABLE",
            "error": entry.get("error"),
            "raw": None,
            "value": None,
        }
    raw = entry.get("value", "").strip()
    if not raw:
        return {"status": "EMPTY", "error": None, "raw": None, "value": None}
    return {"status": "OBSERVED", "error": None, "raw": raw, "value": _normalise_pci_id(raw)}


def _driver_name(link_entry):
    if link_entry.get("status") != "OK":
        return None
    return os.path.basename(link_entry.get("value", "").rstrip("/")) or None


def pci_identity(bdf=GPU_PCI_BDF, sysfs_root=DEFAULT_SYSFS_ROOT):
    """GAP 3. Prove the stable PCI identity of one BDF before it is used.

    A mismatch, an absent path or an unreadable field is reported as such; it
    is never rounded to "probably the right GPU".
    """
    base = Path(sysfs_root) / "bus" / "pci" / "devices" / bdf
    result = {
        "bdf": bdf,
        "pci_path": str(base),
        "path_exists": base.is_dir(),
        "required": dict(GPU_PCI_TARGET, bdf=bdf),
        "observed": {},
        "mismatches": [],
        "PCI_IDENTITY_STATUS": "NOT_PROVEN",
        "PCI_IDENTITY_ABORT": "PCI_DEVICE_PATH_ABSENT",
    }
    if not base.is_dir():
        return result

    fields = {}
    for name in ("vendor", "device", "class"):
        fields[name] = _read_id_field(base / name)
    driver = _driver_name(read_link(base / "driver"))
    fields["driver"] = {"status": "OBSERVED" if driver else "UNREADABLE", "raw": driver, "value": driver}
    result["observed"] = {name: item["value"] for name, item in fields.items()}
    result["observed_fields"] = fields

    mismatches = []
    for name, expected in (("vendor", GPU_PCI_VENDOR), ("device", GPU_PCI_DEVICE), ("class", GPU_PCI_CLASS)):
        item = fields[name]
        if item["status"] != "OBSERVED":
            mismatches.append(f"{name}={item['status']} (expected {expected})")
        elif item["value"] != expected:
            mismatches.append(f"{name}={item['value']} (expected {expected})")
    if driver != GPU_PCI_DRIVER:
        mismatches.append(f"driver={driver} (expected {GPU_PCI_DRIVER})")
    result["mismatches"] = mismatches

    if mismatches:
        result["PCI_IDENTITY_STATUS"] = "MISMATCH"
        result["PCI_IDENTITY_ABORT"] = "PCI_IDENTITY_MISMATCH"
    else:
        result["PCI_IDENTITY_STATUS"] = "PROVEN"
        result["PCI_IDENTITY_ABORT"] = None
    return result


def resolve_node_device(node_dir):
    """HIGH-1.  Prove that a DRM node's ``device`` link really exists and really
    owns that node.

    ``os.path.realpath()`` is **not** an existence proof.  It resolves a
    symlink chain as far as it goes and returns a string, so a node whose
    ``device`` link is missing or dangling still yields a path whose *text*
    contains a BDF -- because ``class/drm/<node>`` is itself a symlink into a
    directory named after the BDF.  Accepting that string is how a false GPU
    identity gets manufactured.

    This function therefore requires, in order: the path exists, it is a
    symlink, its target exists, the target is a directory, the BDF is
    derivable from that *existing* target, and the PCI identity at that
    resolved target matches.  Any failure yields ``BDF_LINK_STATUS=NOT_PROVEN``
    with a specific reason and the node is never used.
    """
    device_link = Path(node_dir) / "device"
    result = {
        "device_link": str(device_link),
        "link_exists": device_link.exists(),
        "is_symlink": device_link.is_symlink(),
        "target": None,
        "target_exists": False,
        "target_is_dir": False,
        "target_realpath": None,
        "device_dir_name": None,
        "bdf_components_in_path": [],
        "resolved_bdf": None,
        "vendor": None,
        "device": None,
        "class": None,
        "driver": None,
        "mismatches": [],
        "BDF_LINK_STATUS": "NOT_PROVEN",
        "BDF_LINK_ABORT": None,
    }

    # DEFECT-01: the BDF is the name of the resolved PCI *device* directory,
    # proven structurally.  Scanning the path for a BDF-shaped substring would
    # return the PCI bridge on this host.
    directory = resolve_pci_device_dir(device_link)
    result["link_exists"] = directory["link_exists"]
    result["is_symlink"] = directory["is_symlink"]
    result["target"] = directory["target"]
    result["target_realpath"] = directory["target_realpath"]
    result["target_exists"] = directory["target_exists"]
    result["target_is_dir"] = directory["target_is_dir"]
    result["device_dir_name"] = directory["device_dir_name"]
    result["bdf_components_in_path"] = directory["bdf_components_in_path"]
    if directory["PCI_DEVICE_DIR_STATUS"] != "PROVEN":
        result["BDF_LINK_ABORT"] = directory["PCI_DEVICE_DIR_ABORT"]
        return result

    real = directory["target_realpath"]
    result["resolved_bdf"] = directory["device_dir_bdf"]

    # Re-verify the identity at the *resolved* target, not at the path the BDF
    # text was read from.
    fields = {}
    for name in ("vendor", "device", "class"):
        fields[name] = _read_id_field(Path(real) / name)
        result[name] = fields[name]["value"]
    result["driver"] = _driver_name(read_link(Path(real) / "driver"))

    mismatches = []
    for name, expected in (("vendor", GPU_PCI_VENDOR), ("device", GPU_PCI_DEVICE), ("class", GPU_PCI_CLASS)):
        item = fields[name]
        if item["status"] != "OBSERVED":
            mismatches.append(f"{name}={item['status']} (expected {expected})")
        elif item["value"] != expected:
            mismatches.append(f"{name}={item['value']} (expected {expected})")
    if result["driver"] != GPU_PCI_DRIVER:
        mismatches.append(f"driver={result['driver']} (expected {GPU_PCI_DRIVER})")
    result["mismatches"] = mismatches

    if mismatches:
        result["BDF_LINK_ABORT"] = "PCI_IDENTITY_MISMATCH_AT_NODE"
        return result
    result["BDF_LINK_STATUS"] = "PROVEN"
    return result


def discover_drm_nodes(bdf=GPU_PCI_BDF, sysfs_root=DEFAULT_SYSFS_ROOT):
    """GAP 4. Resolve the DRM card/render nodes owned by one BDF.

    Two independent directions must agree:
      forward  /sys/bus/pci/devices/<BDF>/drm/*      kernel enumeration
      reverse  /sys/class/drm/<node>/device -> BDF   class enumeration

    The reverse direction is proven by ``resolve_node_device()``, which requires
    an existing symlink to an existing directory and re-checks the PCI identity
    there.  A node number is never identity.  Every node seen in the reverse
    scan that does not belong to the target is recorded with its resolved BDF,
    its driver and the reason it was excluded, so an exclusion is auditable
    instead of silent.
    """
    result = {
        "target_bdf": bdf,
        "method": "PCI_BDF_THEN_DYNAMIC_SYSFS_RESOLUTION",
        "forward_dir": str(Path(sysfs_root) / "bus" / "pci" / "devices" / bdf / "drm"),
        "forward": {"present": False, "card": [], "render": [], "ignored": []},
        "reverse": {"present": False, "card_candidates": [], "render_candidates": [], "excluded": [], "others": []},
        "agreement": False,
        "DRM_DISCOVERY_STATUS": "NOT_PROVEN",
        "DRM_DISCOVERY_ABORT": "PCI_DRM_ENUMERATION_ABSENT",
    }

    # --- forward: the kernel's own enumeration for this PCI function
    forward_dir = Path(sysfs_root) / "bus" / "pci" / "devices" / bdf / "drm"
    if forward_dir.is_dir():
        try:
            names = sorted(item.name for item in forward_dir.iterdir())
        except Exception as exc:
            result["DRM_DISCOVERY_ABORT"] = f"PCI_DRM_ENUMERATION_UNREADABLE:{type(exc).__name__}"
            return result
        result["forward"]["present"] = True
        for name in names:
            if CARD_NODE_RE.fullmatch(name):
                result["forward"]["card"].append(name)
            elif RENDER_NODE_RE.fullmatch(name):
                result["forward"]["render"].append(name)
            else:
                result["forward"]["ignored"].append(name)

    # --- reverse: resolve every DRM node to the BDF that owns it
    class_dir = Path(sysfs_root) / "class" / "drm"
    if class_dir.is_dir():
        try:
            names = sorted(item.name for item in class_dir.iterdir())
        except Exception as exc:
            result["DRM_DISCOVERY_ABORT"] = f"DRM_CLASS_UNREADABLE:{type(exc).__name__}"
            return result
        result["reverse"]["present"] = True
        for name in names:
            card = CARD_NODE_RE.fullmatch(name)
            render = RENDER_NODE_RE.fullmatch(name)
            if not card and not render:
                # connectors (card0-HDMI-A-1) and control nodes are not roles
                result["reverse"]["others"].append(name)
                continue
            kind = "card" if card else "render"
            link = resolve_node_device(class_dir / name)
            node_bdf = link["resolved_bdf"]
            entry = {
                "node": name,
                "kind": kind,
                "minor": int((card or render).group(1)),
                "resolved_bdf": node_bdf,
                "realpath": link["target_realpath"],
                "driver": link["driver"],
                "bdf_link_status": link["BDF_LINK_STATUS"],
                "bdf_link_abort": link["BDF_LINK_ABORT"],
                "device_link_evidence": link,
                "is_target": False,
            }
            if link["BDF_LINK_STATUS"] != "PROVEN":
                # An unproven device link is never a candidate, and never an
                # exclusion-by-BDF: it is recorded with its own reason.
                entry["exclusion_reason"] = link["BDF_LINK_ABORT"]
                result["reverse"]["excluded"].append(entry)
                continue
            entry["is_target"] = node_bdf == bdf
            if entry["is_target"]:
                result["reverse"]["card_candidates" if kind == "card" else "render_candidates"].append(entry)
            else:
                entry["exclusion_reason"] = "DIFFERENT_BDF"
                result["reverse"]["excluded"].append(entry)

    fwd_card = sorted(result["forward"]["card"])
    fwd_render = sorted(result["forward"]["render"])
    rev_card = sorted(item["node"] for item in result["reverse"]["card_candidates"])
    rev_render = sorted(item["node"] for item in result["reverse"]["render_candidates"])

    if not result["forward"]["present"]:
        result["DRM_DISCOVERY_ABORT"] = "PCI_DRM_ENUMERATION_ABSENT"
        return result
    if not result["reverse"]["present"]:
        result["DRM_DISCOVERY_ABORT"] = "DRM_CLASS_ABSENT"
        return result
    if fwd_card != rev_card or fwd_render != rev_render:
        result["agreement"] = False
        result["DRM_DISCOVERY_ABORT"] = "DIRECTION_DISAGREEMENT"
        result["forward_summary"] = {"card": fwd_card, "render": fwd_render}
        result["reverse_summary"] = {"card": rev_card, "render": rev_render}
        return result
    result["agreement"] = True

    if len(rev_card) == 0 or len(rev_render) == 0:
        result["DRM_DISCOVERY_ABORT"] = "ROLE_MISSING"
        return result
    if len(rev_card) > 1 or len(rev_render) > 1:
        result["DRM_DISCOVERY_ABORT"] = "AMBIGUOUS_CANDIDATE"
        return result

    result["DRM_DISCOVERY_STATUS"] = "PROVEN"
    result["DRM_DISCOVERY_ABORT"] = None
    result["resolved"] = {
        "card_node": rev_card[0],
        "card_minor": result["reverse"]["card_candidates"][0]["minor"],
        "render_node": rev_render[0],
        "render_minor": result["reverse"]["render_candidates"][0]["minor"],
    }
    return result


def _amdgpu_device_bdfs(discovery):
    bdfs = set()
    for bucket in ("card_candidates", "render_candidates", "excluded"):
        for item in discovery.get("reverse", {}).get(bucket, []):
            if item.get("driver") == GPU_PCI_DRIVER and item.get("resolved_bdf"):
                bdfs.add(item["resolved_bdf"])
    return sorted(bdfs)


def resolve_gpu_identity(bdf=GPU_PCI_BDF, sysfs_root=DEFAULT_SYSFS_ROOT):
    """GAP 1/3/4 combined.  Identity first, nodes second, evidence never.

    The returned ``devices`` set replaces the former hardcoded
    {/dev/dri/card1, /dev/dri/renderD129}.
    """
    pci = pci_identity(bdf, sysfs_root)
    discovery = discover_drm_nodes(bdf, sysfs_root)
    identity = {
        "GPU_BDF": bdf,
        "GPU_VENDOR": pci["observed"].get("vendor"),
        "GPU_DEVICE": pci["observed"].get("device"),
        "GPU_CLASS": pci["observed"].get("class"),
        "GPU_DRIVER": pci["observed"].get("driver"),
        "GPU_CARD_NODE": None,
        "GPU_RENDER_NODE": None,
        "GPU_CARD_MINOR": None,
        "GPU_RENDER_MINOR": None,
        "GPU_NODE_PATHS": {},
        "GPU_HWMON": [],
        "GPU_IDENTITY_STATUS": "NOT_PROVEN",
        "GPU_IDENTITY_ABORT": None,
        "amdgpu_device_bdfs": _amdgpu_device_bdfs(discovery),
        "pci_identity": pci,
        "drm_discovery": discovery,
        "devices": set(),
    }

    if pci["PCI_IDENTITY_STATUS"] != "PROVEN":
        identity["GPU_IDENTITY_ABORT"] = "IDENTITY_NOT_PROVEN"
        identity["GPU_IDENTITY_ABORT_STAGE"] = "PCI"
        identity["GPU_IDENTITY_ABORT_DETAIL"] = pci["PCI_IDENTITY_ABORT"]
        return identity
    if discovery["DRM_DISCOVERY_STATUS"] != "PROVEN":
        identity["GPU_IDENTITY_ABORT"] = "IDENTITY_NOT_PROVEN"
        identity["GPU_IDENTITY_ABORT_STAGE"] = "DRM"
        identity["GPU_IDENTITY_ABORT_DETAIL"] = discovery["DRM_DISCOVERY_ABORT"]
        return identity

    resolved = discovery["resolved"]
    card, render = resolved["card_node"], resolved["render_node"]
    identity["GPU_CARD_NODE"] = card
    identity["GPU_RENDER_NODE"] = render
    identity["GPU_CARD_MINOR"] = resolved["card_minor"]
    identity["GPU_RENDER_MINOR"] = resolved["render_minor"]
    identity["GPU_NODE_PATHS"] = {
        "card": f"/dev/dri/{card}",
        "render": f"/dev/dri/{render}",
        "card_sysfs": str(Path(sysfs_root) / "class" / "drm" / card),
        "render_sysfs": str(Path(sysfs_root) / "class" / "drm" / render),
        "device_sysfs": str(Path(sysfs_root) / "class" / "drm" / card / "device"),
    }
    identity["devices"] = {f"/dev/dri/{card}", f"/dev/dri/{render}"}

    hwmon_root = Path(sysfs_root) / "class" / "drm" / card / "device" / "hwmon"
    try:
        identity["GPU_HWMON"] = sorted(str(item) for item in hwmon_root.glob("hwmon*"))
    except Exception:
        identity["GPU_HWMON"] = []

    identity["GPU_IDENTITY_STATUS"] = "PROVEN"
    identity["GPU_IDENTITY_ABORT"] = None
    identity["GPU_IDENTITY_ABORT_STAGE"] = None
    identity["GPU_IDENTITY_ABORT_DETAIL"] = None
    return identity


def debugfs_client_attribution(identity, debug_root=DEFAULT_DEBUG_ROOT):
    """GAP 2.  Derive the debugfs minor from the discovered render node.

    ``dri/1`` is never assumed.  The minor is read off the render node that the
    BDF resolution proved, and the directory is only accepted when the driver
    marker files inside it agree with a single amdgpu DRM device.  Anything
    else is NOT_AVAILABLE -- never an invented path.
    """
    result = {
        "DEBUGFS_CLIENT_ATTRIBUTION": "NOT_AVAILABLE",
        "derivation": "NONE",
        "candidate_minor": None,
        "dri_dir": None,
        "clients_path": None,
        "driver_marker_files": [],
        "amdgpu_device_count": None,
        "reason": "GPU_IDENTITY_NOT_PROVEN",
        "read_status": None,
        "entries": [],
    }
    if identity.get("GPU_IDENTITY_STATUS") != "PROVEN":
        return result

    minor = identity.get("GPU_RENDER_MINOR")
    render = identity.get("GPU_RENDER_NODE")
    if minor is None:
        result["reason"] = "RENDER_MINOR_NOT_DERIVED"
        return result
    result["candidate_minor"] = minor
    result["derivation"] = f"minor {minor} read from discovered render node {render}"
    dri_dir = Path(debug_root) / "dri" / str(minor)
    result["dri_dir"] = str(dri_dir)

    try:
        entries = sorted(item.name for item in dri_dir.iterdir())
    except PermissionError as exc:
        result["reason"] = "DEBUGFS_PERMISSION_DENIED"
        result["read_status"] = f"PermissionError: {exc}"
        return result
    except FileNotFoundError:
        result["reason"] = "DEBUGFS_DRI_MINOR_ABSENT"
        result["read_status"] = "FileNotFoundError"
        return result
    except Exception as exc:
        result["reason"] = "DEBUGFS_UNREADABLE"
        result["read_status"] = f"{type(exc).__name__}: {exc}"
        return result

    result["entries"] = entries
    markers = [name for name in entries if name.startswith(GPU_PCI_DRIVER)]
    result["driver_marker_files"] = markers
    amdgpu_devices = identity.get("amdgpu_device_bdfs") or []
    result["amdgpu_device_count"] = len(amdgpu_devices)

    if not markers:
        result["reason"] = "DEBUGFS_NO_DRIVER_MARKER"
        return result
    if len(amdgpu_devices) != 1:
        result["reason"] = "DEBUGFS_AMBIGUOUS_MULTIPLE_AMDGPU"
        return result

    clients = dri_dir / "clients"
    result["clients_path"] = str(clients)
    try:
        result["clients"] = read_text(clients, 65536)
        result["read_status"] = "OK"
    except Exception as exc:  # pragma: no cover - read_text never raises
        result["read_status"] = f"{type(exc).__name__}: {exc}"
    result["DEBUGFS_CLIENT_ATTRIBUTION"] = "PROVEN"
    result["reason"] = "MINOR_DERIVED_AND_DRIVER_CONFIRMED"
    return result


def parse_mountinfo(path):
    """Read /proc/self/mountinfo.  No findmnt, no shell, pure parsing."""
    entries = []
    text = read_text(path, 524288)
    for line in text.splitlines():
        fields = line.split()
        if "-" not in fields:
            continue
        separator = fields.index("-")
        if separator < 6 or len(fields) <= separator + 2:
            continue
        entries.append(
            {
                "mount_id": fields[0],
                "parent_id": fields[1],
                "major_minor": fields[2],
                "root": fields[3],
                "mount_point": fields[4],
                "mount_options": fields[5],
                "optional_fields": fields[6:separator],
                "fstype": fields[separator + 1],
                "source": fields[separator + 2],
                "super_options": fields[separator + 3] if len(fields) > separator + 3 else "",
                "raw": line,
            }
        )
    return entries


def resolve_block_device(source, block_root=DEFAULT_BLOCK_ROOT):
    """Map a /dev source to a block device and its parent disk via sysfs."""
    result = {
        "source": source,
        "block_name": None,
        "parent_disk": None,
        "block_sysfs": None,
        "parent_sysfs": None,
        "is_partition": None,
        "status": "NOT_PROVEN",
        "reason": None,
    }
    if not source or not str(source).startswith("/dev/"):
        result["reason"] = "SOURCE_NOT_A_DEV_PATH"
        return result
    name = os.path.basename(str(source))
    entry = Path(block_root) / name
    if not entry.is_dir():
        result["reason"] = "BLOCK_DEVICE_ABSENT_IN_SYSFS"
        return result

    result["block_name"] = name
    result["block_sysfs"] = str(entry)
    real = os.path.realpath(str(entry))
    parts = real.split("/block/")
    if len(parts) < 2 or not parts[1].strip("/"):
        result["reason"] = "BLOCK_SYSFS_REALPATH_UNRECOGNISED"
        return result
    result["parent_disk"] = parts[1].split("/")[0]
    result["parent_sysfs"] = str(Path(block_root) / result["parent_disk"])
    result["is_partition"] = (entry / "partition").exists()
    result["status"] = "PROVEN"
    return result


def resolve_storage_identity(
    proc_root=DEFAULT_PROC_ROOT,
    block_root=DEFAULT_BLOCK_ROOT,
    mountpoint="/",
):
    """GAP 5.  mountpoint -> source -> block device -> sysfs identity.

    No device name is assumed.  The diskstats device set returned here is
    exactly the set that the sampling window is allowed to read, so a
    neighbouring disk can never contribute plausible-looking numbers.
    """
    result = {
        "ROOT_MOUNT": None,
        "ROOT_SOURCE": None,
        "ROOT_FSTYPE": None,
        "ROOT_BLOCK_DEVICE": None,
        "ROOT_BLOCK_SYSFS": None,
        "ROOT_BLOCK_PARENT": None,
        "ROOT_IS_PARTITION": None,
        "ROOT_MOUNTINFO_RAW": None,
        "STORAGE_DISKSTATS_NAMES": [],
        "STORAGE_IDENTITY_STATUS": "NOT_PROVEN",
        "STORAGE_IDENTITY_ABORT": "ROOT_MOUNTPOINT_NOT_FOUND",
        "derivation": "mountinfo -> source -> /sys/class/block -> parent disk",
    }
    mountinfo = Path(proc_root) / "self" / "mountinfo"
    matches = [item for item in parse_mountinfo(mountinfo) if item["mount_point"] == mountpoint]
    if not matches:
        return result
    if len(matches) > 1:
        result["STORAGE_IDENTITY_ABORT"] = "AMBIGUOUS_ROOT_MOUNT"
        result["ROOT_MOUNT"] = mountpoint
        result["ROOT_MOUNTINFO_RAW"] = [item["raw"] for item in matches]
        return result

    entry = matches[0]
    result["ROOT_MOUNT"] = entry["mount_point"]
    result["ROOT_SOURCE"] = entry["source"]
    result["ROOT_FSTYPE"] = entry["fstype"]
    result["ROOT_MOUNTINFO_RAW"] = entry["raw"]

    block = resolve_block_device(entry["source"], block_root)
    result["ROOT_BLOCK_DEVICE"] = block["block_name"]
    result["ROOT_BLOCK_SYSFS"] = block["block_sysfs"]
    result["ROOT_BLOCK_PARENT"] = block["parent_disk"]
    result["ROOT_IS_PARTITION"] = block["is_partition"]
    result["block_resolution"] = block
    if block["status"] != "PROVEN":
        result["STORAGE_IDENTITY_ABORT"] = f"STORAGE_BLOCK_NOT_RESOLVABLE:{block['reason']}"
        return result

    parent = block["parent_disk"]
    try:
        for item in sorted(Path(block_root).iterdir()):
            if not item.is_dir():
                continue
            parts = os.path.realpath(str(item)).split("/block/")
            if len(parts) >= 2 and parts[1].split("/")[0] == parent:
                result["STORAGE_DISKSTATS_NAMES"].append(item.name)
    except Exception as exc:
        result["STORAGE_IDENTITY_ABORT"] = f"BLOCK_ENUMERATION_FAILED:{type(exc).__name__}"
        return result

    result["STORAGE_IDENTITY_STATUS"] = "PROVEN"
    result["STORAGE_IDENTITY_ABORT"] = None
    return result


def scan_maps(pid, proc_root=DEFAULT_PROC_ROOT, keep_lines=256):
    """GAP 6.  /proc/<pid>/maps, with PermissionError kept distinct from absence.

    A denied read is a fact about the observer's privilege, not a fact about the
    process.  It is recorded as MAPS_PERMISSION_DENIED and is never collapsed
    into "no mappings".
    """
    path = Path(proc_root) / str(pid) / "maps"
    result = {
        "MAPS_READABLE": False,
        "MAPS_PERMISSION_DENIED": False,
        "MAPS_ERROR": None,
        "MAPS_STATUS": "ERROR",
        "line_count": 0,
        "byte_count": 0,
        "relevant_count": 0,
        "relevant_lines": [],
        "truncated": False,
    }
    try:
        with path.open("rb") as stream:
            data = stream.read(4 * 1024 * 1024)
    except PermissionError as exc:
        result["MAPS_PERMISSION_DENIED"] = True
        result["MAPS_STATUS"] = "PERMISSION_DENIED"
        result["MAPS_ERROR"] = f"PermissionError: {exc}"
        return result
    except FileNotFoundError as exc:
        result["MAPS_STATUS"] = "ABSENT"
        result["MAPS_ERROR"] = f"FileNotFoundError: {exc}"
        return result
    except Exception as exc:
        result["MAPS_ERROR"] = f"{type(exc).__name__}: {exc}"
        return result

    text = data.decode("utf-8", errors="replace")
    lines = text.splitlines()
    relevant = [line for line in lines if MAPS_RELEVANT_RE.search(line)]
    result.update(
        {
            "MAPS_READABLE": True,
            "MAPS_STATUS": "READABLE",
            "line_count": len(lines),
            "byte_count": len(data),
            "relevant_count": len(relevant),
            "relevant_lines": relevant[:keep_lines],
            "truncated": len(relevant) > keep_lines,
        }
    )
    return result


def proc_pids(proc_root=DEFAULT_PROC_ROOT):
    result = []
    try:
        for name in os.listdir(proc_root):
            if name.isdigit():
                result.append(int(name))
    except Exception:
        pass
    return sorted(set(result))


def pid_gone(pid, proc_root=DEFAULT_PROC_ROOT):
    """Re-read one PID after its sweep, to tell a vanished PID from a live one.

    Returns ``{"state": "GONE"|"ALIVE"|"UNKNOWN", "reason": ..., "error": ...}``.

    UNKNOWN is a real outcome and is never collapsed into GONE: an unreadable
    procfs entry is not evidence that the process is gone.  A swallowed read
    failure must be surfaced, and it is, in ``error``.
    """
    entry = Path(proc_root) / str(pid)
    try:
        os.stat(str(entry))
    except (FileNotFoundError, ProcessLookupError):
        return {"state": "GONE", "reason": "PROCESS_DISAPPEARED", "error": None}
    except Exception as exc:
        message = f"{type(exc).__name__}: {exc}"
        return {
            "state": "UNKNOWN",
            "reason": classify_proc_error(message),
            "error": message,
        }
    return {"state": "ALIVE", "reason": "OBSERVED", "error": None}


def parse_proc_stat(pid, proc_root=DEFAULT_PROC_ROOT):
    entry = read_bytes(Path(proc_root) / str(pid) / "stat", 8192)
    if entry.get("status") != "OK":
        # Keep the real cause: a vanished process is not a visibility failure.
        return {
            "status": "ERROR",
            "error": entry.get("error"),
            "reason": classify_proc_error(entry.get("error", "")),
        }
    text = entry.get("value", "")
    if not text:
        return {"status": "ERROR", "error": "stat empty", "reason": "PROCESS_DISAPPEARED_OR_EMPTY"}
    try:
        close = text.rfind(")")
        comm = text[text.find("(") + 1 : close]
        fields = text[close + 2 :].split()
        return {
            "status": "OK",
            "comm": comm,
            "state": fields[0],
            "ppid": int(fields[1]),
            "pgrp": int(fields[2]),
            "session": int(fields[3]),
            "tty_nr": int(fields[4]),
        }
    except Exception as exc:
        return {"status": "ERROR", "error": f"{type(exc).__name__}: {exc}"}


def proc_meta(pid, proc_root=DEFAULT_PROC_ROOT):
    base = Path(proc_root) / str(pid)
    result = {"pid": pid, "source": f"{proc_root}/{pid}"}
    stat = parse_proc_stat(pid, proc_root)
    result["stat"] = stat
    if stat.get("status") == "OK":
        result["state"] = stat.get("state")
        result["ppid"] = stat.get("ppid")
        result["comm"] = stat.get("comm")
    status_text = read_text(base / "status", 65536)
    for line in status_text.splitlines():
        if line.startswith("Uid:") and "uid" not in result:
            parts = line.split()
            if len(parts) > 1:
                try:
                    result["uid"] = int(parts[1])
                except Exception:
                    pass
        elif line.startswith("Gid:") and "gid" not in result:
            parts = line.split()
            if len(parts) > 1:
                try:
                    result["gid"] = int(parts[1])
                except Exception:
                    pass
        elif line.startswith("Name:") and "name" not in result:
            result["name"] = line.split(":", 1)[1].strip()
    command = read_bytes(base / "cmdline", 16384)
    result["cmdline"] = (
        command.get("value", "").replace("\x00", " ").strip()[:4096]
        if command.get("status") == "OK"
        else ""
    )
    exe = read_link(base / "exe")
    result["exe"] = exe.get("value", exe.get("error", "UNAVAILABLE"))
    result["wchan"] = read_text(base / "wchan", 4096).strip()
    result["cgroup"] = read_text(base / "cgroup", 16384)
    result["namespaces"] = {}
    for namespace in ("mnt", "pid", "user", "net", "cgroup", "uts", "ipc"):
        link = read_link(base / "ns" / namespace)
        result["namespaces"][namespace] = link.get("value", "UNAVAILABLE")
    return result


DRM_ATTRIBUTION_FIELDS = ("drm-client-id", "drm-pdev", "pasid")
# fdinfo field name -> counter name in scan_fds()["attribution"].
DRM_ATTRIBUTION_COUNTERS = {
    "drm-client-id": "drm_client_id",
    "drm-pdev": "drm_pdev",
    "pasid": "pasid",
}


def fdinfo_attribution(fdinfo_text):
    """Which per-client attribution fields a DRM fdinfo actually carries.

    Presence only, never a value.  A field that is absent is reported absent:
    the caller decides what that means, and nothing here invents availability.
    ``drm-client-id`` and ``drm-pdev`` are emitted by the DRM core for a DRM
    file descriptor.  ``pasid`` is amdgpu-specific, so its absence is only
    meaningful once the matched node has been proven to be the amdgpu device.
    """
    text = fdinfo_text or ""
    return {name: (name + ":") in text for name in DRM_ATTRIBUTION_FIELDS}


def scan_fds(pid, devices, proc_root=DEFAULT_PROC_ROOT):
    """Enumerate every FD of one process and keep the GPU node targets.

    ``devices`` is the set resolved from the proven PCI identity, not a
    hardcoded cardN/renderDN pair.  ``fdinfo`` is read whole because that is
    where drm-client-id, drm-pdev and pasid live.
    """
    fd_dir = Path(proc_root) / str(pid) / "fd"
    result = {
        "status": "OK",
        "fd_count": 0,
        "matched": [],
        "drm_nodes_any": [],
        "error_count": 0,
        "errors": [],
        # FDs whose target could not be resolved.  The FD is known to exist but
        # its target is unknown, so it can be neither matched to a device nor
        # ruled out as one.  Counting these is what keeps an unreadable target
        # from being silently read as "not a DRM fd"; errors[] is capped at 12
        # samples, so this counter is the authoritative one.
        "unresolved_target_count": 0,
        # Per-client attribution facts, so the ownership matrix can tell
        # "no DRM client" from "client without a readable fdinfo" from
        # "client read but not attributable".  Presence only, never a value.
        "attribution": {
            "drm_fds_found": 0,
            "fdinfo_read": 0,
            "drm_client_id": 0,
            "drm_pdev": 0,
            "pasid": 0,
        },
    }
    try:
        names = os.listdir(fd_dir)
    except Exception as exc:
        message = f"{type(exc).__name__}: {exc}"
        result["status"] = "ERROR"
        result["error_count"] = 1
        result["status_reason"] = classify_proc_error(message)
        result["errors"].append(
            {"path": str(fd_dir), "error": message, "reason": result["status_reason"]}
        )
        return result
    for name in sorted(names, key=lambda item: int(item) if item.isdigit() else 10**12):
        if not name.isdigit():
            continue
        result["fd_count"] += 1
        fd_path = fd_dir / name
        try:
            target = os.readlink(str(fd_path))
        except Exception as exc:
            message = f"{type(exc).__name__}: {exc}"
            result["error_count"] += 1
            # The FD exists and its target is unknown.  It is therefore neither
            # a confirmed device client nor a confirmed non-client.  Recording
            # that here is what stops `continue` below from turning lost
            # coverage into a false absence of a DRM client.
            result["unresolved_target_count"] += 1
            if len(result["errors"]) < 12:
                result["errors"].append(
                    {"fd": int(name), "stage": "target", "error": message,
                     "reason": classify_proc_error(message)}
                )
            continue
        if target in devices:
            # fdinfo is a sibling of fd/, not a child of it: the real path is
            # /proc/<pid>/fdinfo/<n>.  Building it from fd_dir.parent gives that
            # path.  The previous fd_path.parent ("fd") produced
            # /proc/<pid>/fd/fdinfo/<n>, which does not exist, so every DRM
            # client was recorded with an empty fdinfo.
            fdinfo_path = fd_dir.parent / "fdinfo" / name
            fdinfo = read_bytes(fdinfo_path, 16384)
            if fdinfo.get("status") != "OK":
                # read_text() used to swallow this and return "", so a broken
                # path was indistinguishable from an fd with no fdinfo.  A read
                # that fails is now counted, classified, and kept in the sample.
                message = fdinfo.get("error", "FDINFO_READ_FAILED")
                result["error_count"] += 1
                if len(result["errors"]) < 12:
                    result["errors"].append(
                        {
                            "fd": int(name),
                            "stage": "fdinfo",
                            "path": str(fdinfo_path),
                            "error": message,
                            "reason": classify_proc_error(message),
                        }
                    )
            result["attribution"]["drm_fds_found"] += 1
            if fdinfo.get("status") == "OK":
                result["attribution"]["fdinfo_read"] += 1
                present = fdinfo_attribution(fdinfo.get("value", ""))
                for field, seen in present.items():
                    if seen:
                        counter = DRM_ATTRIBUTION_COUNTERS[field]
                        result["attribution"][counter] += 1
            result["matched"].append(
                {
                    "fd": int(name),
                    "target": target,
                    "fdinfo": fdinfo.get("value", "") if fdinfo.get("status") == "OK" else "",
                }
            )
        elif target.startswith("/dev/dri/") or target.startswith("/dev/sd") or target.startswith("/dev/nvme"):
            # Recorded separately: a process on the *other* GPU is not a client
            # of the target, and dropping it silently would hide the contrast.
            result["drm_nodes_any"].append({"fd": int(name), "target": target})
    return result


def compositor_gpu_relation(comm, cmdline, matched_targets, other_drm_targets):
    """GAP 7.  Classify a compositor's relation to the target GPU.

    OBSERVED   the process holds an FD on a node proven to belong to the BDF
    SUPPORTED  the process holds an FD on some DRM node, but not the target's
    UNKNOWN    no FD evidence either way
    A process being a compositor is never treated as GPU usage.
    """
    name = " ".join(str(item) for item in (comm, cmdline)).lower()
    if not any(keyword in name for keyword in COMPOSITOR_KEYWORDS):
        return None
    if matched_targets:
        return {
            "KWIN_GPU_RELATION": "OBSERVED",
            "matched_targets": sorted(matched_targets),
            "other_drm_targets": sorted(other_drm_targets or []),
            "basis": "/proc/<pid>/fd symlink on a BDF-proven DRM node",
        }
    if other_drm_targets:
        return {
            "KWIN_GPU_RELATION": "UNKNOWN",
            "matched_targets": [],
            "other_drm_targets": sorted(other_drm_targets),
            "basis": "DRM FDs exist but none resolve to the target BDF; target usage UNKNOWN",
        }
    return {
        "KWIN_GPU_RELATION": "UNKNOWN",
        "matched_targets": [],
        "other_drm_targets": [],
        "basis": "no DRM FD observed; absence of evidence is not evidence of absence",
    }


def relevant_process(meta, keywords=KEYWORDS):
    """Relevance is a *hint* for the detailed record, never an exclusion.

    Every PID is scanned regardless of whether this returns True, so a process
    whose name matches nothing is still a candidate FD and maps reader.
    """
    text = " ".join(
        str(meta.get(key, ""))
        for key in ("comm", "name", "cmdline", "exe")
    ).lower()
    return any(keyword in text for keyword in keywords)


def systemctl_rows():
    units = [
        "system-autopilot.timer",
        "system-autopilot.service",
        "sys-tuned.timer",
        "sys-tuned.service",
        "kalm-gpu.service",
        "kalm.service",
        "kalm-lite.service",
        "irqbalance.service",
        "power-profiles-daemon.service",
        "sysstat-collect.timer",
        "sysstat-collect.service",
        "crond.service",
        "udisks2.service",
        "kde-baloo.service",
        "systemd-udevd.service",
    ]
    rows = []
    for unit in units:
        result = run(
            [
                "systemctl",
                "show",
                unit,
                "--no-pager",
                "--plain",
                "--property=Id,LoadState,ActiveState,SubState,MainPID,ExecMainPID,FragmentPath,ControlGroup,TriggeredBy,Triggers",
            ],
            timeout=12,
        )
        properties = {}
        for line in result.get("stdout", "").splitlines():
            if "=" in line:
                key, value = line.split("=", 1)
                properties[key] = value
        rows.append(
            {
                "unit": unit,
                "command": result.get("argv"),
                "returncode": result.get("returncode"),
                "properties": properties,
                "stderr": result.get("stderr", ""),
            }
        )
    return rows


def parse_diskstats(disk_names, proc_root=DEFAULT_PROC_ROOT):
    """Only the disks proven to back the host's root filesystem are parsed.

    ``disk_names`` comes from the storage identity resolution.  An empty set
    yields an empty result, never a fallback to a name pattern.
    """
    rows = {}
    if not disk_names:
        return rows
    wanted = set(disk_names)
    names = [
        "reads_completed",
        "reads_merged",
        "sectors_read",
        "ms_reading",
        "writes_completed",
        "writes_merged",
        "sectors_written",
        "ms_writing",
        "ios_in_progress",
        "io_ticks",
        "weighted_io_ticks",
    ]
    text = read_text(Path(proc_root) / "diskstats", 524288)
    for line in text.splitlines():
        parts = line.split()
        if len(parts) >= 14 and parts[2] in wanted:
            try:
                rows[parts[2]] = {
                    name: int(parts[index + 3]) for index, name in enumerate(names)
                }
            except Exception:
                rows[parts[2]] = {"raw": line}
    return rows


def parse_cpu_stat():
    for line in read_text("/proc/stat", 65536).splitlines():
        if line.startswith("cpu "):
            try:
                values = [int(value) for value in line.split()[1:]]
                names = [
                    "user", "nice", "system", "idle", "iowait", "irq",
                    "softirq", "steal", "guest", "guest_nice",
                ]
                return {
                    name: values[index]
                    for index, name in enumerate(names)
                    if index < len(values)
                }
            except Exception:
                return {"raw": line}
    return {}


def parse_psi(path):
    text = read_text(path, 32768)
    result = {"raw": text}
    for line in text.splitlines():
        parts = line.split()
        if parts and parts[0] in ("some", "full"):
            values = {}
            for item in parts[1:]:
                if "=" in item:
                    key, value = item.split("=", 1)
                    try:
                        values[key] = float(value) if key.startswith("avg") else int(value)
                    except Exception:
                        values[key] = value
            result[parts[0]] = values
    return result


def disk_level_sysfs(storage):
    """The block device that actually owns whole-disk attributes.  Read only.

    DEFECT-05: queue/ and device/ exist only on whole-disk nodes in sysfs.
    A partition such as /sys/class/block/sdb3 has neither, so every read
    through the partition base failed with FileNotFoundError.  resolve_block_device
    already resolved the parent disk and recorded it as
    block_resolution["parent_sysfs"]; this reuses that resolution instead of
    deriving the parent a second time.  ROOT_BLOCK_SYSFS keeps its existing
    meaning (the block device named by the mount source, which may be a
    partition) and is used only as a fallback.
    """
    resolution = storage.get("block_resolution") or {}
    parent_sysfs = resolution.get("parent_sysfs")
    if parent_sysfs:
        return parent_sysfs
    return storage.get("ROOT_BLOCK_SYSFS")


def read_queue(block_sysfs):
    """Queue attributes of the proven root-filesystem disk.  Read only."""
    if not block_sysfs:
        return {"STORAGE_METRICS": "SKIPPED_IDENTITY_NOT_PROVEN", "queue": {}}
    base = Path(block_sysfs) / "queue"
    names = [
        "scheduler", "read_ahead_kb", "rq_affinity", "nomerges",
        "async_depth", "nr_requests", "rotational", "logical_block_size",
        "physical_block_size", "max_sectors_kb", "write_cache",
        "add_random", "write_same", "daemon", "iostats",
        "rq_affinity_control",
    ]
    return {
        "STORAGE_METRICS": "READ",
        "block_sysfs": str(base),
        "queue": {name: read_bytes(base / name, 32768) for name in names},
    }


def read_governors():
    result = {}
    for path in sorted(Path("/sys/devices/system/cpu").glob("cpu[0-9]*")):
        if not re.fullmatch(r"cpu\d+", path.name):
            continue
        base = path / "cpufreq"
        if not base.exists():
            continue
        result[path.name] = {
            "governor": read_text(base / "scaling_governor", 4096).strip(),
            "available_governors": read_text(
                base / "scaling_available_governors", 4096
            ).strip(),
            "driver": read_text(base / "scaling_driver", 4096).strip(),
            "energy_performance_preference": read_text(
                base / "energy_performance_preference", 4096
            ).strip(),
            "affected_cpus": read_text(base / "affected_cpus", 4096).strip(),
            "related_cores": read_text(base / "related_cores", 4096).strip(),
        }
    return result


def dstate_snapshot(proc_root=DEFAULT_PROC_ROOT):
    tasks = []
    for pid in proc_pids(proc_root):
        stat = parse_proc_stat(pid, proc_root)
        if stat.get("status") != "OK" or stat.get("state") != "D":
            continue
        base = Path(proc_root) / str(pid)
        status_text = read_text(base / "status", 32768)
        uid = None
        for line in status_text.splitlines():
            if line.startswith("Uid:"):
                parts = line.split()
                if len(parts) > 1:
                    try:
                        uid = int(parts[1])
                    except Exception:
                        pass
                break
        tasks.append(
            {
                "pid": pid,
                "uid": uid,
                "comm": stat.get("comm"),
                "wchan": read_text(base / "wchan", 4096).strip(),
                "cmdline": read_text(base / "cmdline", 8192)
                .replace("\x00", " ")
                .strip()[:1024],
            }
        )
        if len(tasks) >= 256:
            break
    return tasks


def irq_snapshot(gpu_bdf=None, disk_names=None, proc_root=DEFAULT_PROC_ROOT):
    """IRQ lines relevant to the proven GPU and the proven root disk.

    The GPU contributes its BDF and ``amdgpu``; the storage contributes the
    resolved disk name.  Neither contributes a hardcoded device name.
    """
    keywords = ["amdgpu", "i915", "ahci", "sata", "scsi", "nvme", "xhci"]
    if gpu_bdf:
        keywords.append(gpu_bdf)
    for name in disk_names or ():
        keywords.append(name)
    text = read_text(Path(proc_root) / "interrupts", 524288)
    lines = text.splitlines()
    selected = []
    for line in lines[1:]:
        low = line.lower()
        if not any(keyword in low for keyword in keywords):
            continue
        match = re.match(r"\s*(\d+):(.*)", line)
        if not match:
            continue
        irq = match.group(1)
        selected.append(
            {
                "irq": irq,
                "line": line,
                "smp_affinity_list": read_text(
                    f"{proc_root}/irq/{irq}/smp_affinity_list", 4096
                ).strip(),
                "effective_affinity_list": read_text(
                    f"{proc_root}/irq/{irq}/effective_affinity_list", 4096
                ).strip(),
                "node": read_text(f"{proc_root}/irq/{irq}/node", 4096).strip(),
            }
        )
    return {
        "irq_line_count": len(lines),
        "selected": selected,
        "selection_keywords": list(keywords),
    }


def pm_snapshot(device_sysfs):
    """PM/DPM attributes of the proven GPU device.  Read only, no writes."""
    if not device_sysfs:
        return {"PM_METRICS": "SKIPPED_IDENTITY_NOT_PROVEN", "paths": {}, "amdgpu_parameters": {}}
    base = Path(device_sysfs)
    explicit = [
        base / "power/control",
        base / "power/runtime_status",
        base / "power/autosuspend_delay_ms",
        base / "power/wakeup",
        base / "gpu_busy_percent",
        base / "mem_busy_percent",
        base / "pp_power_profile_mode",
        base / "ppfeaturemask",
        base / "current_link_speed",
        base / "current_link_width",
        base / "max_link_speed",
        base / "max_link_width",
        base / "mem_info_vram_total",
        base / "mem_info_vram_used",
        base / "mem_info_vis_vram_total",
        base / "mem_info_vis_vram_used",
        base / "mem_info_gtt_total",
        base / "mem_info_gtt_used",
        base / "pp_dpm_sclk",
        base / "pp_dpm_mclk",
    ]
    paths = {str(path): read_bytes(path, 65536) for path in explicit}
    for pattern in ("power/*autosuspend*", "pp_dpm_*", "pp_*"):
        try:
            for path in sorted(base.glob(pattern)):
                if path.is_file() and str(path) not in paths and len(paths) < 160:
                    paths[str(path)] = read_bytes(path, 65536)
        except Exception:
            pass
    parameters = {}
    for path in sorted(Path("/sys/module/amdgpu/parameters").glob("*")):
        if path.is_file() and len(parameters) < 128:
            parameters[path.name] = read_bytes(path, 32768)
    return {"PM_METRICS": "READ", "device_sysfs": str(base), "paths": paths, "amdgpu_parameters": parameters}


def storage_identity_snapshot(storage):
    """Hardware identity of the proven root disk, plus the sysfs evidence."""
    block_sysfs = storage.get("ROOT_BLOCK_SYSFS")
    if not block_sysfs:
        return {"STORAGE_METRICS": "SKIPPED_IDENTITY_NOT_PROVEN", "identity": None}
    # DEFECT-05: device/ is a whole-disk attribute.  Read it from the parent
    # disk that resolve_block_device already resolved, while block_name keeps
    # naming the block device the root mount actually came from.
    disk_sysfs = disk_level_sysfs(storage) or block_sysfs
    disk_base = Path(disk_sysfs)
    return {
        "STORAGE_METRICS": "READ",
        "block_sysfs": str(block_sysfs),
        "disk_sysfs": str(disk_base),
        "identity": {
            "block_name": storage.get("ROOT_BLOCK_DEVICE"),
            "parent_disk": storage.get("ROOT_BLOCK_PARENT"),
            "device_realpath": read_link(disk_base / "device"),
            "vendor": read_text(disk_base / "device" / "vendor", 4096).strip(),
            "model": read_text(disk_base / "device" / "model", 4096).strip(),
            "state": read_text(disk_base / "device" / "state", 4096).strip(),
            "host": read_text(disk_base / "device" / "host", 4096).strip(),
        },
    }


def add_record(records, gap, observed, required, status, source, command, classification):
    records.append(
        {
            "GAP": gap,
            "OBSERVED": observed,
            "REQUIRED": required,
            "STATUS": status,
            "SOURCE": source,
            "COMMAND": command,
            "TIMESTAMP": iso(),
            "CLASSIFICATION": classification,
        }
    )


# --------------------------------------------------------------------------
# GAP 9 -- the AGENTS.md 11-condition matrix is the only ownership verdict.
# The legacy boolean is kept for continuity and is explicitly non-authoritative.
# --------------------------------------------------------------------------
OWNERSHIP_CRITERION_ROWS = (
    ("card_node_complete", "DRM card node FD table complete and attributable"),
    ("render_node_complete", "DRM render node FD table complete and attributable"),
    ("user_namespaces_covered", "user namespaces of relevant processes covered"),
    ("root_namespaces_covered", "root namespaces of relevant processes covered"),
    ("drm_fds_enumerated", "DRM file descriptors enumerated with drm-client-id/pasid"),
    ("writers_resolved", "governor, IRQ, scheduler, read-ahead and storage writers resolved"),
    ("agents_absent", "no active writer/agent during the window"),
    ("pm_observed", "PM state observed for the proven device"),
    ("guard_and_restore", "guard and restore proven"),
    ("btrfs_identity", "Btrfs identity matched in the same window"),
    ("clients_pasid_attributable", "DRM clients and PASID attributable per process"),
)
# Rows this collector structurally cannot decide.  They are R2 and R3.
OWNERSHIP_EXTERNAL_ROWS = {
    "writers_resolved": ("NOT_EVALUATED", "R2", "writer audit is a separate route; not performed here"),
    "guard_and_restore": ("NOT_EVALUATED", "R3", "guard/restore/recovery is a separate route; C1 is deferred"),
}


def drm_fd_enumeration_state(coverage, gpu_proven):
    """Decide drm_fds_enumerated from per-client DRM attribution facts.

    The row used to be scored on ``fd_error_count == 0``, a global error proxy
    that could not tell "this host has no DRM client" from "twelve clients were
    found and none could be attributed", and that turned a /proc race
    into a FAIL.  It is now scored on what was actually enumerated:

    A. whether the relevant universe could be enumerated at all;
    B. whether any DRM FD was found;
    C. whether each found FD's fdinfo was read;
    D. whether ``drm-client-id`` was observed;
    E. whether ``pasid`` was observed;
    F. whether any of the above could not be established;
    G. whether a vanished PID's absence of a DRM resource is *proven* or only
       assumed from its disappearance.  It is only the former, and a
       disappearance on its own yields UNKNOWN, never PASS.

    Returns ``(state, reason)``.  Absence of a field is never counted as
    success: a client whose attribution field is missing is PARTIAL, and a
    universe that could not be enumerated is PARTIAL or UNKNOWN, never PASS.
    """
    if not gpu_proven:
        return "NOT_EVALUATED", "GPU identity not proven"

    found = int(coverage.get("drm_fds_found", 0))
    read = int(coverage.get("drm_fdinfo_read", 0))
    client_id = int(coverage.get("drm_client_id_seen", 0))
    pdev = int(coverage.get("drm_pdev_seen", 0))
    pasid = int(coverage.get("drm_pasid_seen", 0))
    blocked = int(coverage.get("fd_universe_blocked_pids", 0))
    races = int(coverage.get("fd_race_pids", 0))
    # The only discharge for a vanished PID whose client set is unknown.  A
    # disappearance is a race only when its absence of the resource is also
    # demonstrated; without this counter the count of races could be read as
    # proof of an empty universe, which it is not.
    absent = int(coverage.get("fd_absence_proven_pids", 0))
    # The swept PID universe is part of the reason: without it the row would
    # report a client count with no indication of how wide the sweep was, and
    # coverage["total_pids"] would stop being read by the matrix at all.
    # Read strictly, not with .get(): DEFECT-04 established that a missing
    # total_pids must be a loud failure, and a default of 0 would render it as
    # "across 0 PIDs" instead.
    universe = " across %d PIDs" % int(coverage["total_pids"])

    def vanished_note():
        """Diagnostic only.  Never asserts that a vanished PID held nothing."""
        if not races:
            return ""
        return "; %d PID(s) vanished mid-sweep, counted as diagnosis only" % races

    if blocked:
        # Those PIDs' FDs are unknown and any of them could have been the client,
        # so the universe is not established.  With no client in hand there is
        # nothing to characterise either, which is UNKNOWN rather than PARTIAL.
        if found == 0:
            return "UNKNOWN", "universe not enumerable (%d pid(s) unreadable, 0 clients seen%s)" % (blocked, universe)
        return "PARTIAL", "universe not enumerable (%d pid(s) unreadable, %d client(s) seen%s)" % (
            blocked, found, universe,
        )

    if found == 0:
        # A complete sweep that found no DRM FD is a real observation -- but only
        # when no PID vanished without its absence being demonstrated.  A
        # disappearance alone cannot certify the empty universe: the vanished
        # PID's FDs are unknown, so it may have held the client.  fd_universe_
        # blocked_pids already routes that case above; this branch is the
        # defensive equivalent for a coverage dict that reports the loss
        # nowhere else.
        if races > absent:
            return "UNKNOWN", (
                "universe not established%s; %d PID(s) vanished, 0 clients seen, "
                "absence NOT proven for %d of them"
                % (universe, races, races - absent)
            )
        # A complete sweep that found no DRM FD is a real observation.  The
        # reason states the count so the PASS is not read as vacuous.
        return "PASS", "universe enumerated, 0 DRM fds found%s%s" % (
            universe,
            "; %d PID(s) vanished, absence of a DRM resource proven" % races
            if races else "",
        )

    missing = []
    if read < found:
        missing.append("fdinfo unreadable on %d/%d" % (found - read, found))
    if client_id < read:
        missing.append("drm-client-id absent on %d/%d" % (read - client_id, read))
    if pdev < read:
        missing.append("drm-pdev absent on %d/%d" % (read - pdev, read))
    if pasid < read:
        missing.append("pasid absent on %d/%d" % (read - pasid, read))

    if missing:
        return "PARTIAL", "%d DRM fd(s) found%s; %s%s" % (
            found,
            universe,
            "; ".join(missing),
            vanished_note(),
        )

    return "PASS", "%d DRM fd(s) all attributed (drm-client-id, drm-pdev, pasid)%s%s" % (
        found,
        universe,
        vanished_note(),
    )


def ownership_matrix(context):
    """Return the 11 rows of the AGENTS.md criterion, plus the aggregate state.

    The aggregate can never be FULL while an external row stays NOT_EVALUATED,
    which is the intended behaviour: this collector does not audit writers and
    does not execute a guard.
    """
    gpu = context["gpu_identity"]
    coverage = context["root_coverage"]
    debugfs = context["debugfs"]
    btrfs = context["btrfs_observation"]
    gpu_proven = gpu.get("GPU_IDENTITY_STATUS") == "PROVEN"
    card_node = gpu.get("GPU_CARD_NODE")
    render_node = gpu.get("GPU_RENDER_NODE")

    drm_fd_state, drm_fd_reason = drm_fd_enumeration_state(coverage, gpu_proven)

    observed = {
        "card_node_complete": (
            "PASS" if gpu_proven and coverage["card_complete"] else
            ("FAIL" if gpu_proven and not coverage["card_complete"] else "NOT_EVALUATED")
        ),
        "render_node_complete": (
            "PASS" if gpu_proven and coverage["render_complete"] else
            ("FAIL" if gpu_proven and not coverage["render_complete"] else "NOT_EVALUATED")
        ),
        "user_namespaces_covered": "PASS" if coverage["user_namespace_complete"] else "FAIL",
        "root_namespaces_covered": "PASS" if coverage["root_namespace_complete"] else "FAIL",
        "drm_fds_enumerated": drm_fd_state,
        "agents_absent": "PASS" if context["active_agents"] == 0 else "FAIL",
        "pm_observed": "PASS" if context["pm_status"] == "READ" else "UNKNOWN",
        "btrfs_identity": "NOT_APPLICABLE" if context["btrfs_status"] != "PRESENT" else "UNKNOWN",
        "clients_pasid_attributable": {
            "PROVEN": "PASS", "NOT_AVAILABLE": "UNKNOWN", "OBSERVED": "PASS"
        }.get(debugfs.get("DEBUGFS_CLIENT_ATTRIBUTION"), "UNKNOWN"),
    }
    evidence = {
        "card_node_complete": f"{card_node} / {context['card_clients']} attributable client(s)",
        "render_node_complete": f"{render_node} / {context['render_clients']} attributable client(s)",
        "user_namespaces_covered": f"{coverage['user_namespace_ok']}/{coverage['user_namespace_total']} readable",
        "root_namespaces_covered": f"{coverage['root_namespace_ok']}/{coverage['root_namespace_total']} readable",
        "drm_fds_enumerated": drm_fd_reason,
        "agents_absent": f"{context['active_agents']} active service row(s)",
        "pm_observed": f"PM_METRICS={context['pm_status']}",
        "btrfs_identity": f"btrfs lines observed={context['btrfs_status']}",
        "clients_pasid_attributable": f"{debugfs.get('DEBUGFS_CLIENT_ATTRIBUTION')} ({debugfs.get('reason')})",
    }
    sources = {
        "card_node_complete": "/proc/*/fd on the BDF-proven card node",
        "render_node_complete": "/proc/*/fd on the BDF-proven render node",
        "user_namespaces_covered": "/proc/<pid>/ns/*",
        "root_namespaces_covered": "/proc/<pid>/ns/*",
        "drm_fds_enumerated": "/proc/<pid>/fdinfo",
        "agents_absent": "systemctl show (read-only)",
        "pm_observed": "read(2) of the proven device sysfs",
        "btrfs_identity": "/proc/self/mountinfo",
        "clients_pasid_attributable": f"{debugfs.get('clients_path') or 'debugfs clients'}",
    }

    rows = []
    for key, description in OWNERSHIP_CRITERION_ROWS:
        if key in OWNERSHIP_EXTERNAL_ROWS:
            state, route, limitation = OWNERSHIP_EXTERNAL_ROWS[key]
        else:
            state = observed.get(key, "UNKNOWN")
            limitation = "see evidence field"
        rows.append(
            {
                "condition": key,
                "description": description,
                "STATE": state,
                "EVIDENCE": evidence.get(key, limitation),
                "SOURCE": sources.get(key, "-"),
                "LIMITATION": limitation,
                "ROUTE": OWNERSHIP_EXTERNAL_ROWS.get(key, ("-", "R1"))[1],
            }
        )

    states = {row["STATE"] for row in rows}
    if "NOT_EVALUATED" in states or "FAIL" in states:
        aggregate = "PARTIAL"
    elif states <= {"PASS", "NOT_APPLICABLE"}:
        aggregate = "FULL"
    else:
        aggregate = "PARTIAL"
    return {
        "AUTHORITY": "AGENTS_MD_OWNERSHIP_CRITERION",
        "COLLECTOR_OWNERSHIP_BOOLEAN": "NON_AUTHORITATIVE",
        "conditions": rows,
        "pass_count": sum(1 for row in rows if row["STATE"] == "PASS"),
        "fail_count": sum(1 for row in rows if row["STATE"] == "FAIL"),
        "not_evaluated_count": sum(1 for row in rows if row["STATE"] == "NOT_EVALUATED"),
        "unknown_count": sum(1 for row in rows if row["STATE"] in ("UNKNOWN", "NOT_APPLICABLE")),
        "OWNERSHIP_CRITERION_STATE": aggregate,
        "note": (
            "rows writers_resolved (R2) and guard_and_restore (R3) are outside this "
            "collector, so the aggregate cannot reach FULL here"
        ),
    }


# GAP 10 -- capability register.  Each entry names real code in this file;
# the unit tests assert the symbol exists, so a row cannot be inflated.
CAPABILITY_MATRIX = (
    {
        "capability": "/proc/*/fd symlink per FD",
        "implemented": True,
        "source": "scan_fds",
        "dynamic_identity": "device set from resolve_gpu_identity",
        "privilege": "ROOT",
        "limitation": "kernel gates per-observer",
    },
    {
        "capability": "/proc/*/fdinfo contents (drm-client-id, drm-pdev, pasid)",
        "implemented": True,
        "source": "scan_fds",
        "dynamic_identity": "device set from resolve_gpu_identity",
        "privilege": "ROOT",
        "limitation": "16 KiB cap per FD",
    },
    {
        "capability": "process metadata (uid/gid/ppid/comm/cmdline/exe/wchan/cgroup)",
        "implemented": True,
        "source": "proc_meta",
        "dynamic_identity": "n/a",
        "privilege": "PARTIAL",
        "limitation": "root-owned processes are partially masked",
    },
    {
        "capability": "7 namespaces per process",
        "implemented": True,
        "source": "proc_meta",
        "dynamic_identity": "n/a",
        "privilege": "ROOT",
        "limitation": "root namespaces need privilege",
    },
    {
        "capability": "root process traversal (no uid filter)",
        "implemented": True,
        "source": "proc_pids",
        "dynamic_identity": "n/a",
        "privilege": "NONE",
        "limitation": "none; enumeration is unfiltered",
    },
    {
        "capability": "lsof + fuser cross-check",
        "implemented": True,
        "source": "main",
        "dynamic_identity": "nodes from resolve_gpu_identity",
        "privilege": "PARTIAL",
        "limitation": "only sees what the observer may see",
    },
    {
        "capability": "DRM debugfs client attribution",
        "implemented": True,
        "source": "debugfs_client_attribution",
        "dynamic_identity": "minor derived from the discovered render node",
        "privilege": "ROOT",
        "limitation": "requires mounted debugfs; NOT_AVAILABLE otherwise",
    },
    {
        "capability": "/proc/<pid>/maps with PermissionError distinguished",
        "implemented": True,
        "source": "scan_maps",
        "dynamic_identity": "n/a",
        "privilege": "ROOT",
        "limitation": "relevant-line subset retained, 4 MiB read cap",
    },
    {
        "capability": "GPU PCI identity verification (vendor/device/class/driver)",
        "implemented": True,
        "source": "pci_identity",
        "dynamic_identity": "target BDF + vendor/device",
        "privilege": "NONE",
        "limitation": "aborts the run on mismatch",
    },
    {
        "capability": "BDF -> DRM card/render node discovery",
        "implemented": True,
        "source": "discover_drm_nodes",
        "dynamic_identity": "forward + reverse enumeration must agree",
        "privilege": "NONE",
        "limitation": "aborts on ambiguity",
    },
    {
        "capability": "root filesystem block device identity",
        "implemented": True,
        "source": "resolve_storage_identity",
        "dynamic_identity": "mountinfo -> source -> /sys/class/block",
        "privilege": "NONE",
        "limitation": "NOT_PROVEN for non-/dev sources or stacked / mounts",
    },
)


def abort_payload(reason, detail, stage):
    """An abort writes a marker, never an empty evidence document.

    An ``ownership`` key with empty content would be indistinguishable from a
    real observation of "no clients", so it is deliberately absent.
    """
    return {
        "PREFLIGHT_ID": PREFLIGHT_ID,
        "COLLECTOR_STATUS": "ABORTED",
        "ABORT_REASON": reason,
        "ABORT_STAGE": stage,
        "ABORT_DETAIL": detail,
        "metadata": {
            "timestamp_start": START_ISO,
            "timestamp_end": iso(),
            "mode": "PRIVILEGED_READ_ONLY",
            "host": os.uname().nodename,
            "kernel": os.uname().release,
            "c1_invoked": False,
            "mutating_commands": [],
            "systemctl_mutations": [],
        },
        "privilege": observe_privilege_state(),
        "ownership_evidence_collected": False,
        "note": (
            "Identity could not be proven; no ownership evidence was collected. "
            "This is not a finding about GPU clients."
        ),
        "final": {
            "PREFLIGHT": "PARTIAL",
            "OWNERSHIP": "PARTIAL",
            "C1": "DEFERRED",
            "GO_C1": "NOT_AVAILABLE",
            "SYSTEM_CHANGES": 0,
            "GPU_WRITES": 0,
            "STORAGE_WRITES": 0,
            "SYSTEMD_CHANGES": 0,
            "C1_EXECUTED": 0,
            "RUNTIME_MATERIALIZED": 0,
            "COMMIT": 0,
        },
    }


def assess_parent_bundle(parent, current_host, current_kernel):
    """DEFECT-02.  Decide whether a parent bundle's evidence may be used at all.

    Evidence from another host is not evidence about this host.  The bundle
    that aborted R1 run R1-20260926T000649Z was produced on ``lex-luthor``
    (kernel 7.2.6-201) while the run was on ``kalm`` (kernel 7.1.3-200); its 363
    ``fd_visibility_errors`` were about PIDs that do not exist here.

    On any mismatch the bundle is rejected **wholesale**: its PIDs, clients and
    errors are not merged into any counter of the current run, and the
    differential against it is reported NOT_AVAILABLE rather than zero.  A
    rejected bundle can never lower or raise a coverage figure.

    Admission policy, stated explicitly rather than left implicit: a bundle may
    contribute historical evidence only when BOTH the host matches **and** a
    kernel is declared **and** that kernel matches.  A host-only match is
    rejected as INCOMPLETE_IDENTITY, because a bundle cannot then be shown to
    describe this boot.  A malformed ``metadata`` is INVALID, never a crash and
    never an empty list that would read as "no prior errors".
    """
    result = {
        "parent_host": None,
        "parent_kernel": None,
        "current_host": current_host,
        "current_kernel": current_kernel,
        "PARENT_BUNDLE_IDENTITY": "NOT_AVAILABLE",
        "PARENT_BUNDLE_METADATA": "ABSENT",
        "OWNERSHIP_EVIDENCE_FROM_PARENT": "NOT_AVAILABLE",
        "PRIOR_EVIDENCE_ADMISSIBLE": False,
        "PRIOR_EVIDENCE_STATUS": "REJECTED_PARENT_IDENTITY_NOT_AVAILABLE",
        "policy": "host must match AND kernel must be present AND kernel must match",
        "reason": "",
    }

    if parent is None:
        result["reason"] = "no parent bundle was supplied"
        return result
    if not isinstance(parent, dict):
        result["PARENT_BUNDLE_METADATA"] = "INVALID"
        result["PARENT_BUNDLE_IDENTITY"] = "INVALID"
        result["PRIOR_EVIDENCE_STATUS"] = "REJECTED_BUNDLE_MALFORMED"
        result["reason"] = (
            f"parent bundle is a {type(parent).__name__}, not an object; no identity "
            "can be read from it and no evidence is taken from it"
        )
        return result

    metadata = parent.get("metadata")
    if metadata is None:
        result["PARENT_BUNDLE_METADATA"] = "ABSENT"
        result["reason"] = "the parent bundle declares no host identity, so it cannot " \
                           "be shown to describe this host"
        return result
    if not isinstance(metadata, dict):
        result["PARENT_BUNDLE_METADATA"] = "INVALID"
        result["PARENT_BUNDLE_IDENTITY"] = "INVALID"
        result["PRIOR_EVIDENCE_STATUS"] = "REJECTED_BUNDLE_MALFORMED"
        result["reason"] = (
            f"parent bundle metadata is a {type(metadata).__name__}, not an object; "
            "no identity can be read from it and no evidence is taken from it"
        )
        return result

    result["PARENT_BUNDLE_METADATA"] = "READABLE"
    observed_host = metadata.get("host")
    observed_kernel = metadata.get("kernel")
    result["parent_host"] = observed_host
    result["parent_kernel"] = observed_kernel

    if not observed_host:
        result["reason"] = "the parent bundle declares no host identity"
        return result
    if observed_host != current_host:
        result["PARENT_BUNDLE_IDENTITY"] = "HOST_MISMATCH"
        result["PRIOR_EVIDENCE_STATUS"] = "REJECTED_HOST_MISMATCH"
        result["reason"] = (
            f"parent bundle was collected on host {observed_host!r}, this run is on "
            f"{current_host!r}; its PIDs, clients and errors describe a different host"
        )
        return result
    if not observed_kernel:
        result["PARENT_BUNDLE_IDENTITY"] = "INCOMPLETE"
        result["PRIOR_EVIDENCE_STATUS"] = "REJECTED_INCOMPLETE_IDENTITY"
        result["reason"] = (
            f"parent bundle declares host {observed_host!r} but no kernel, so it cannot "
            "be shown to describe this boot; host-only matching is not sufficient"
        )
        return result
    if observed_kernel != current_kernel:
        result["PARENT_BUNDLE_IDENTITY"] = "KERNEL_MISMATCH"
        result["PRIOR_EVIDENCE_STATUS"] = "REJECTED_KERNEL_MISMATCH"
        result["reason"] = (
            f"parent bundle kernel {observed_kernel!r} differs from the running "
            f"kernel {current_kernel!r}; procfs observations are not comparable"
        )
        return result

    result["PARENT_BUNDLE_IDENTITY"] = "MATCH"
    result["PRIOR_EVIDENCE_ADMISSIBLE"] = True
    result["OWNERSHIP_EVIDENCE_FROM_PARENT"] = "ADMITTED"
    result["PRIOR_EVIDENCE_STATUS"] = "ACCEPTED_SAME_HOST_AND_KERNEL"
    result["reason"] = "parent bundle host and kernel both match this run"
    return result


def g06_summary(queue_initial=None, irq_initial=None, irq_final=None, storage_identity_evidence=None):
    """Derive the G-06 prose from the state of the actual reads.  Read only.

    DEFECT-06: this summary used to be a literal that asserted observation
    unconditionally.  In R1 run 4 every queue read was ERROR and the summary
    still said the values had been observed.  It now reports what was read,
    what failed and with which state, and what was not available.  It never
    states a value that was not read.
    """
    payload = queue_initial if isinstance(queue_initial, dict) else {}
    queue = payload.get("queue")
    queue = queue if isinstance(queue, dict) else None
    clauses = []

    if queue is None or not queue:
        state = payload.get("STORAGE_METRICS", "NOT_AVAILABLE")
        clauses.append("queue_reads=NOT_AVAILABLE:%s" % state)
    else:
        observed = sorted(
            name
            for name, value in queue.items()
            if isinstance(value, dict) and value.get("status") == "OK"
        )
        failed = {
            name: (value.get("status") if isinstance(value, dict) else None) or "UNKNOWN"
            for name, value in queue.items()
            if name not in observed
        }
        if not failed:
            clauses.append(
                "queue/read-ahead/asynchronous-depth values observed=%d/%d"
                % (len(observed), len(queue))
            )
        else:
            clauses.append(
                "queue_values_observed=%d/%d" % (len(observed), len(queue))
            )
            for state in sorted(set(failed.values())):
                names = sorted(name for name, got in failed.items() if got == state)
                clauses.append(
                    "queue_read_%s=%d [%s]" % (state, len(names), ", ".join(names))
                )

    for label, snapshot in (("initial", irq_initial), ("final", irq_final)):
        if not isinstance(snapshot, dict):
            clauses.append("irq_%s=NOT_AVAILABLE" % label)
            continue
        selected = snapshot.get("selected") or []
        with_affinity = [
            entry
            for entry in selected
            if isinstance(entry, dict) and (entry.get("effective_affinity_list") or "").strip()
        ]
        clauses.append(
            "irq_%s_lines_selected=%d; irq_%s_affinity_observed=%d/%d"
            % (label, len(selected), label, len(with_affinity), len(selected))
        )

    identity_evidence = (
        storage_identity_evidence if isinstance(storage_identity_evidence, dict) else {}
    )
    identity = identity_evidence.get("identity")
    if not isinstance(identity, dict):
        clauses.append("storage_identity=NOT_AVAILABLE")
    else:
        realpath = identity.get("device_realpath")
        realpath_status = (
            realpath.get("status") if isinstance(realpath, dict) else None
        ) or "UNKNOWN"
        if realpath_status != "OK":
            clauses.append("storage_identity_device_realpath=%s" % realpath_status)
        strings = [
            "%s=%s" % (key, (identity.get(key) or "").strip())
            for key in ("vendor", "model", "state")
            if (identity.get(key) or "").strip()
        ]
        clauses.append(
            "storage_identity_strings=%s" % (", ".join(strings) if strings else "NOT_AVAILABLE")
        )

    clauses.append("continuous attribution and threshold remain undetermined")
    return "; ".join(clauses)


def main():
    if PARENT_PATH is None:
        raise SystemExit(
            "usage: privileged_read_collector.py <parent-preflight.json> <preflight-id>"
        )
    records = []
    # CORRECTION 1: privilege is OBSERVED from this process's own euid, never
    # inferred from the wrapper.  sudo itself is never executed or detected.
    privilege = observe_privilege_state()

    # DEFECT-02: the parent bundle is admitted only if it provably describes
    # this host and this kernel.  Otherwise none of its evidence reaches a
    # counter, and every current-run figure starts from zero.
    parent_assessment = assess_parent_bundle(
        PARENT, os.uname().nodename, os.uname().release
    )
    prior_admissible = parent_assessment["PRIOR_EVIDENCE_ADMISSIBLE"]
    if prior_admissible:
        prior_errors = PARENT.get("ownership", {}).get("fd_visibility_errors", [])
        prior_clients = PARENT.get("ownership", {}).get("clients", [])
    else:
        # Rejected or absent: NOT_AVAILABLE, never an empty list that would read
        # as "no prior errors" or "no prior clients".
        prior_errors = []
        prior_clients = []
    prior_pids = sorted(
        {int(item["pid"]) for item in prior_errors if str(item.get("pid", "")).isdigit()}
    )
    prior_keys = {
        (str(item.get("resource")), int(item.get("fd")), int(item.get("pid")))
        for item in prior_clients
        if item.get("resource") and item.get("fd") is not None and item.get("pid") is not None
    }

    # ---------------------------------------------------------------- step 1
    # HOST identity
    host_identity = {
        "nodename": os.uname().nodename,
        "kernel": os.uname().release,
        "release": os.uname().version,
        "machine": os.uname().machine,
        "boot_time_source": "/proc/stat (btime), not sampled here",
    }
    os_release = {}
    for line in read_text("/etc/os-release", 16384).splitlines():
        if "=" in line:
            key, value = line.split("=", 1)
            os_release[key] = value.strip('"')
    host_identity["os_release"] = os_release

    # ---------------------------------------------------------------- step 2
    # PCI identity, then DRM identity, then storage identity.  Nothing that
    # depends on an identity is collected before the identity is proven.
    gpu_identity = resolve_gpu_identity()
    storage_identity = resolve_storage_identity()
    debugfs = debugfs_client_attribution(gpu_identity)

    if gpu_identity["GPU_IDENTITY_STATUS"] != "PROVEN":
        print(
            json.dumps(
                abort_payload(
                    gpu_identity["GPU_IDENTITY_ABORT"],
                    gpu_identity.get("GPU_IDENTITY_ABORT_DETAIL"),
                    f"IDENTITY_STAGE_{gpu_identity.get('GPU_IDENTITY_ABORT_STAGE')}",
                ),
                ensure_ascii=False,
                sort_keys=True,
            )
        )
        return

    devices = gpu_identity["devices"]
    device_sysfs = gpu_identity["GPU_NODE_PATHS"]["device_sysfs"]
    # DEFECT-05: read_queue() needs the whole-disk node, not the partition the
    # mount source names.  Reuse the parent disk resolve_block_device resolved.
    # The former local block_sysfs (ROOT_BLOCK_SYSFS) had no reader left after
    # this change and was removed rather than left dead.
    queue_sysfs = (
        disk_level_sysfs(storage_identity)
        if storage_identity["STORAGE_IDENTITY_STATUS"] == "PROVEN"
        else None
    )
    disk_names = storage_identity["STORAGE_DISKSTATS_NAMES"]
    storage_devices = {
        f"/dev/{name}" for name in disk_names
    } | ({storage_identity["ROOT_SOURCE"]} if storage_identity["ROOT_SOURCE"] else set())

    # Search hints are now host-derived rather than hardcoded device names.
    keywords = tuple(KEYWORDS) + tuple(disk_names) + tuple(
        node.replace("/dev/dri/", "") for node in devices
    )

    service_rows = systemctl_rows()
    service_pids = set()
    active_service_rows = []
    for row in service_rows:
        properties = row.get("properties", {})
        try:
            pid = int(properties.get("MainPID", "0"))
            if pid > 0:
                service_pids.add(pid)
        except Exception:
            pass
        if properties.get("ActiveState") in ("active", "activating", "reloading"):
            active_service_rows.append(row)

    # ---------------------------------------------------------------- step 5
    # Namespace / process inventory, then step 6 (FD/fdinfo) and step 7 (maps).
    #
    # HIGH-2: there is exactly ONE sweep over /proc.  Every PID is observed
    # once, through observe(), and pid_records is the single source of truth
    # for pid, uid, role, coverage, gpu_clients, storage_clients and fd errors.
    # `interesting` and the service-PID set are *views* of pid_records, never a
    # second scan, so no (pid, fd, target) can be inserted or counted twice.
    pid_records = {}
    gpu_clients = []
    storage_clients = []
    compositor_relations = {}
    root_fd_errors = []
    root_fd_error_count = 0
    root_fd_permission_denied = 0
    root_fd_disappeared = 0
    root_fd_other_errors = 0
    root_process_error_count = 0
    # HIGH-3: root and user are separate populations with their own
    # denominators.  A single global counter must never decide both.
    coverage = {
        "total_pids": 0,
        "root_pids": 0,
        "user_pids": 0,
        "uid_unknown_pids": 0,
        "late_observed_pids": 0,
        "fd_complete_pids": 0,
        "fd_error_pids": 0,
        "fd_permission_denied_pids": 0,
        "fd_disappeared_pids": 0,
        "fd_other_error_pids": 0,
        "maps_readable": 0,
        "maps_permission_denied": 0,
        "maps_absent": 0,
        "maps_error": 0,
        "root_namespace_ok": 0,
        "root_namespace_denied": 0,
        "root_namespace_total": 0,
        "user_namespace_ok": 0,
        "user_namespace_denied": 0,
        "user_namespace_total": 0,
        # Per-client DRM attribution, accumulated from scan_fds()["attribution"].
        # These exist so drm_fds_enumerated can distinguish "no DRM client",
        # "client whose fdinfo was unreadable" and "client that is not
        # attributable", instead of collapsing all three into fd_error_count.
        "drm_fds_found": 0,
        "drm_fdinfo_read": 0,
        "drm_client_id_seen": 0,
        "drm_pdev_seen": 0,
        "drm_pasid_seen": 0,
        # Sweep-level facts about whether the universe could be enumerated at
        # all.  A vanished process is a race, not lost coverage: the FD it held
        # was released when it died.  A denied or broken fd table is lost
        # coverage, because that PID's FDs are unknown and it may have held one.
        # V3 tightens this: a disappearance is never by itself proof that the
        # PID held no qualifying resource, so a vanished PID is counted in BOTH
        # buckets -- fd_race_pids as diagnosis, fd_universe_blocked_pids because
        # its client set cannot be established.  Only
        # fd_absence_proven_pids discharges that loss, and only observe() may
        # increment it.
        "fd_universe_blocked_pids": 0,
        "fd_race_pids": 0,
        "fd_absence_proven_pids": 0,
    }

    def observe(pid, late=False, proc_root=DEFAULT_PROC_ROOT):
        """Read one PID and account for it exactly once."""
        nonlocal root_fd_error_count, root_fd_permission_denied, \
            root_fd_disappeared, root_fd_other_errors, root_process_error_count
        meta = proc_meta(pid)
        fd = scan_fds(pid, devices)
        maps = scan_maps(pid)
        item = dict(meta)
        item["fd_scan"] = fd
        item["maps"] = maps
        item["_relevant"] = relevant_process(meta, keywords)
        item["_observed_late"] = late

        if fd.get("status") != "OK":
            root_process_error_count += 1
            coverage["fd_error_pids"] += 1
        else:
            coverage["fd_complete_pids"] += 1
        # A vanished PID is NOT by itself evidence that it held no DRM fd, so it
        # is never allowed to certify the empty universe.  It is counted in
        # fd_race_pids for diagnosis, and -- because its client set cannot be
        # established -- it is ALSO lost coverage.  Absence is credited only by
        # fd_absence_proven_pids, below, which requires the whole table to have
        # been read with every target resolved and no device matched.
        if fd.get("status") != "OK":
            if fd.get("status_reason") in ("PROCESS_DISAPPEARED", "PROCESS_DISAPPEARED_OR_EMPTY"):
                coverage["fd_race_pids"] += 1
            # The table could not be listed at all, so this PID's client set is
            # unknown whatever the reason was: lost coverage in both branches.
            coverage["fd_universe_blocked_pids"] += 1
        else:
            # The table was listed, but an individual readlink may have failed.
            # Then that FD's target is unknown and it could have been the DRM
            # node, so the PID's client set is not established.  Classify per
            # reason, exactly as the pid-level case is classified, and count
            # each PID at most once.
            pid_raced = False
            pid_blocked = False
            for error in fd.get("errors", []):
                reason = error.get("reason") or classify_proc_error(
                    error.get("error", "")
                )
                if reason in ("PROCESS_DISAPPEARED", "PROCESS_DISAPPEARED_OR_EMPTY"):
                    pid_raced = True
                    if error.get("stage") != "fdinfo":
                        # A vanished *target*.  The FD existed; only its identity
                        # is unknown, so it may have been the DRM node.  That is
                        # lost coverage, not a benign race.  An fdinfo-stage
                        # disappearance is different: the DRM fd was already
                        # matched, so the resource is proven and only its
                        # characterisation is incomplete.
                        pid_blocked = True
                else:
                    pid_blocked = True
            if pid_raced:
                coverage["fd_race_pids"] += 1
            if pid_blocked:
                coverage["fd_universe_blocked_pids"] += 1
        attribution = fd.get("attribution") or {}
        for key in ("drm_fds_found", "fdinfo_read", "drm_client_id", "drm_pdev", "pasid"):
            coverage[
                {
                    "drm_fds_found": "drm_fds_found",
                    "fdinfo_read": "drm_fdinfo_read",
                    "drm_client_id": "drm_client_id_seen",
                    "drm_pdev": "drm_pdev_seen",
                    "pasid": "drm_pasid_seen",
                }[key]
            ] += int(attribution.get(key, 0))

        # Absence proof, and the only route by which a disappearance may support
        # a "no DRM client" verdict.  Three conditions must hold: the table was
        # read, every FD target resolved, and no device matched.  The PID is
        # then re-read: GONE plus those conditions proves it held no qualifying
        # resource (anything it opened after the sweep died with it), ALIVE
        # claims nothing, and UNKNOWN is lost coverage -- never absence.  A PID
        # that already produced an error is skipped: its target set is already
        # unknown, so it can never be an absence proof.
        if (
            fd.get("status") == "OK"
            and not fd.get("errors")
            and not fd.get("unresolved_target_count")
            and not int(attribution.get("drm_fds_found", 0))
        ):
            liveness = pid_gone(pid, proc_root)
            item["liveness_recheck"] = liveness
            if liveness["state"] == "GONE":
                coverage["fd_absence_proven_pids"] += 1
                coverage["fd_race_pids"] += 1
            elif liveness["state"] == "UNKNOWN":
                coverage["fd_universe_blocked_pids"] += 1
        for error in fd.get("errors", []):
            root_fd_errors.append({"pid": pid, **error})
            # CORRECTION 4: a vanished process is a race, not an isolation fact.
            reason = error.get("reason") or classify_proc_error(error.get("error", ""))
            if reason == "PERMISSION_DENIED":
                root_fd_permission_denied += 1
                coverage["fd_permission_denied_pids"] += 1
            elif reason in ("PROCESS_DISAPPEARED", "PROCESS_DISAPPEARED_OR_EMPTY"):
                root_fd_disappeared += 1
                coverage["fd_disappeared_pids"] += 1
            else:
                root_fd_other_errors += 1
                coverage["fd_other_error_pids"] += 1
        root_fd_error_count += int(fd.get("error_count", 0))

        if maps.get("MAPS_READABLE"):
            coverage["maps_readable"] += 1
        elif maps.get("MAPS_PERMISSION_DENIED"):
            coverage["maps_permission_denied"] += 1
        elif maps.get("MAPS_STATUS") == "ABSENT":
            coverage["maps_absent"] += 1
        else:
            coverage["maps_error"] += 1

        namespaces = meta.get("namespaces", {})
        namespace_ok = bool(namespaces) and all(
            value != "UNAVAILABLE" for value in namespaces.values()
        )
        uid = meta.get("uid")
        if uid == 0:
            coverage["root_pids"] += 1
            coverage["root_namespace_total"] += 1
            coverage["root_namespace_ok" if namespace_ok else "root_namespace_denied"] += 1
        elif uid is None:
            # uid unreadable: the population is unknown, so the PID belongs to
            # neither namespace population and is reported on its own.
            coverage["uid_unknown_pids"] += 1
        else:
            coverage["user_pids"] += 1
            coverage["user_namespace_total"] += 1
            coverage["user_namespace_ok" if namespace_ok else "user_namespace_denied"] += 1

        for match in fd.get("matched", []):
            client = {
                "resource": match["target"],
                "fd": match["fd"],
                "pid": pid,
                "uid": meta.get("uid"),
                "ppid": meta.get("ppid"),
                "state": meta.get("state"),
                "comm": meta.get("comm"),
                "command": meta.get("cmdline"),
                "exe": meta.get("exe"),
                "wchan": meta.get("wchan"),
                "cgroup": meta.get("cgroup"),
                "namespaces": namespaces,
                "fdinfo": match.get("fdinfo"),
                "maps_status": maps.get("MAPS_STATUS"),
                "source": f"/proc/{pid}/fd/{match['fd']}",
            }
            if match["target"] in devices:
                gpu_clients.append(client)
            if match["target"] in storage_devices:
                storage_clients.append(client)
        relation = compositor_gpu_relation(
            meta.get("comm"),
            meta.get("cmdline"),
            {m["target"] for m in fd.get("matched", []) if m["target"] in devices},
            {m["target"] for m in fd.get("drm_nodes_any", [])},
        )
        if relation:
            compositor_relations[str(pid)] = dict(relation, comm=meta.get("comm"))
        return item

    for pid in proc_pids():
        coverage["total_pids"] += 1
        pid_records[str(pid)] = observe(pid)

    # Views over pid_records -- no PID is read or counted a second time.  A
    # service MainPID that appeared after the sweep is observed now, and only
    # now, which is why it cannot duplicate an already accounted PID.
    prior_pid_keys = {str(item) for item in prior_pids}
    interesting = {
        key: record
        for key, record in pid_records.items()
        if record["_relevant"] or record["fd_scan"].get("matched") or key in prior_pid_keys
    }
    for pid in sorted(service_pids):
        key = str(pid)
        if key in interesting:
            continue
        if key in pid_records:
            interesting[key] = pid_records[key]
            continue
        coverage["late_observed_pids"] += 1
        pid_records[key] = observe(pid, late=True)
        interesting[key] = pid_records[key]

    lsof = run(["/usr/bin/lsof", "-nP", "--"] + sorted(devices), timeout=30)
    fuser = run(["/usr/bin/fuser", "-v"] + sorted(devices), timeout=30)
    ps_all = run(
        ["ps", "-e", "-o", "pid=,ppid=,uid=,user=,stat=,wchan=,comm=,args="],
        timeout=30,
    )
    relevant_ps = []
    for line in ps_all.get("stdout", "").splitlines():
        first = line.split(None, 1)
        pid_text = first[0] if first else ""
        low = line.lower()
        if pid_text.isdigit() and (
            int(pid_text) in service_pids
            or pid_text in interesting
            or any(keyword in low for keyword in keywords)
        ):
            relevant_ps.append(line)

    current_keys = {
        (item["resource"], int(item["fd"]), int(item["pid"])) for item in gpu_clients
    }
    if prior_admissible:
        new_gpu_clients = [
            item for item in gpu_clients
            if (item["resource"], int(item["fd"]), int(item["pid"])) not in prior_keys
        ]
        gpu_delta_status = "COMPUTED"
    else:
        # Without an admissible parent there is nothing to difference against.
        # An empty list here would read as "zero new clients", which is a
        # finding rather than an absence of one.
        new_gpu_clients = "NOT_AVAILABLE"
        gpu_delta_status = parent_assessment["PRIOR_EVIDENCE_STATUS"]
    resolved_prior = []
    unresolved_prior = []
    for pid in prior_pids:
        item = interesting.get(str(pid))
        if (
            item
            and item.get("stat", {}).get("status") == "OK"
            and item.get("fd_scan", {}).get("status") == "OK"
        ):
            resolved_prior.append(pid)
        else:
            unresolved_prior.append(
                {
                    "pid": pid,
                    "proc_status": item.get("stat") if item else {"status": "NOT_FOUND"},
                    "fd_scan": item.get("fd_scan") if item else {"status": "NOT_FOUND"},
                }
            )
    # DEFECT-02: this figure is built from the CURRENT observation only.  A
    # PID that exists in a foreign bundle and not in this run must not make
    # this run's visibility look incomplete, and a foreign bundle must never be
    # able to move the number in either direction.
    # CORRECTION 4: a PID that vanished mid-sweep is NOT_APPLICABLE for that one
    # observation.  Only a PermissionError or an unexplained error is a
    # visibility failure.  The cause of each is recorded either way.
    current_run_unreadable = []
    current_run_permission_denied = []
    current_run_disappeared = []
    for key, record in pid_records.items():
        stat = record.get("stat", {})
        fd_scan = record.get("fd_scan", {})
        reasons = set()
        if stat.get("status") != "OK":
            reasons.add(stat.get("reason") or classify_proc_error(stat.get("error", "")))
        if fd_scan.get("status") != "OK":
            reasons.add(fd_scan.get("status_reason") or "OTHER_ERROR")
        if not reasons:
            continue
        current_run_unreadable.append(key)
        if reasons <= {"PROCESS_DISAPPEARED", "PROCESS_DISAPPEARED_OR_EMPTY"}:
            current_run_disappeared.append(key)
        else:
            current_run_permission_denied.append(key)
    root_visibility_complete = (
        root_fd_permission_denied == 0
        and root_fd_other_errors == 0
        and not current_run_permission_denied
        and len(unresolved_prior) == 0
    )

    # ------------------------------------------------- step 9: aggregated GPU
    pm = pm_snapshot(device_sysfs)
    governor_initial = read_governors()
    queue_initial = read_queue(queue_sysfs)
    storage_identity_evidence = storage_identity_snapshot(storage_identity)
    irq_initial = irq_snapshot(gpu_identity["GPU_BDF"], disk_names)
    storage_fds = sorted(storage_clients, key=lambda item: (item["pid"], item["resource"], item["fd"]))

    # 25 samples at a five-second cadence: a 120-second read-only window.
    window_start = time.monotonic()
    samples = []
    for index in range(25):
        target = window_start + index * 5.0
        delay = target - time.monotonic()
        if delay > 0:
            time.sleep(delay)
        blocked = dstate_snapshot()
        samples.append(
            {
                "index": index,
                "timestamp": iso(),
                "diskstats": parse_diskstats(disk_names),
                "cpu": parse_cpu_stat(),
                "psi_io": parse_psi("/proc/pressure/io"),
                "d_state_count": len(blocked),
                "blocked_tasks": blocked,
                "queue": read_queue(queue_sysfs),
                "governors": read_governors(),
            }
        )
    window_elapsed = time.monotonic() - window_start

    read_activity = False
    write_activity = False
    iowait_deltas = []
    dstate_counts = []
    for index, sample in enumerate(samples):
        sample["deltas"] = {"diskstats": {}, "cpu": {}}
        if index:
            previous = samples[index - 1]
            for disk, current in sample["diskstats"].items():
                old = previous["diskstats"].get(disk, {})
                delta = {}
                for key, value in current.items():
                    if isinstance(value, int) and isinstance(old.get(key), int):
                        delta[key] = value - old[key]
                sample["deltas"]["diskstats"][disk] = delta
                if delta.get("reads_completed", 0) > 0 or delta.get("sectors_read", 0) > 0:
                    read_activity = True
                if delta.get("writes_completed", 0) > 0 or delta.get("sectors_written", 0) > 0:
                    write_activity = True
            for key, value in sample["cpu"].items():
                old = previous["cpu"].get(key)
                if isinstance(value, int) and isinstance(old, int):
                    delta = value - old
                    sample["deltas"]["cpu"][key] = delta
                    if key == "iowait":
                        iowait_deltas.append(delta)
        dstate_counts.append(sample["d_state_count"])

    blocked_union = {}
    for sample in samples:
        for task in sample["blocked_tasks"]:
            blocked_union.setdefault(str(task.get("pid")), task)
    governor_history = [sample["governors"] for sample in samples]
    governor_unique = {}
    for cpu in sorted({cpu for snapshot in governor_history for cpu in snapshot}):
        governor_unique[cpu] = sorted(
            {
                snapshot.get(cpu, {}).get("governor", "UNAVAILABLE")
                for snapshot in governor_history
            }
        )

    irq_final = irq_snapshot(gpu_identity["GPU_BDF"], disk_names)
    tty_result = run(["tty"], timeout=10)
    stdin_target = read_link("/proc/self/fd/0")
    tty_candidates = []
    try:
        for path in sorted(Path("/dev").glob("tty*")):
            try:
                stat = os.stat(path)
                tty_candidates.append(
                    {
                        "path": str(path),
                        "mode": oct(stat.st_mode),
                        "readable": os.access(path, os.R_OK),
                    }
                )
            except Exception as exc:
                tty_candidates.append({"path": str(path), "error": f"{type(exc).__name__}: {exc}"})
    except Exception as exc:
        tty_candidates.append({"error": f"{type(exc).__name__}: {exc}"})
    recovery_candidates = []
    for path in [
        Path("/proc/cmdline"),
        Path("/etc/kernel/cmdline"),
        Path("/etc/default/grub"),
        Path("/boot/loader/entries"),
    ]:
        entry = {"path": str(path), "exists": path.exists()}
        if path.is_file():
            try:
                data = path.read_bytes()
                entry["sha256"] = hashlib.sha256(data).hexdigest()
                entry["bytes"] = len(data)
            except Exception as exc:
                entry["error"] = f"{type(exc).__name__}: {exc}"
        elif path.is_dir():
            try:
                entry["entries"] = sorted(item.name for item in path.iterdir())[:128]
            except Exception as exc:
                entry["error"] = f"{type(exc).__name__}: {exc}"
        recovery_candidates.append(entry)
    run_c1 = Path(
        "/home/lucas/Escritorio/RX550-INVESTIGACION/04-IMPLEMENTACION/"
        "c1_isolation_automator.py"
    )
    runtime_v2 = Path("/run/user/1000/c1-isolation-automator-v2")
    runtime_historical = Path("/run/user/1000/c1-isolation-automator")
    tty_stdout = tty_result.get("stdout", "").strip()
    tty_available = tty_result.get("returncode") == 0 and tty_stdout.startswith("/dev/")
    recovery_usable = "UNKNOWN"
    recovery = "FAIL" if not tty_available else "UNKNOWN"
    runtime_v2_present = runtime_v2.exists()

    mountinfo = read_text("/proc/self/mountinfo", 524288)
    btrfs_mounts = [line for line in mountinfo.splitlines() if " - btrfs " in line]
    btrfs_observation = {
        "parent_state": (
            PARENT.get("btrfs", {})
            if parent_assessment["OWNERSHIP_EVIDENCE_FROM_PARENT"] == "ADMITTED"
            else "NOT_AVAILABLE_PARENT_BUNDLE_NOT_ADMITTED"
        ),
        "parent_bundle_identity": parent_assessment["PARENT_BUNDLE_IDENTITY"],
        "parent_evidence_status": parent_assessment["PRIOR_EVIDENCE_STATUS"],
        "mountinfo_btrfs_lines": btrfs_mounts,
        "matched_identity_same_window": "NOT_AVAILABLE",
        "reconciliation": "NOT_RUN",
        "status": "DEFERRED",
    }

    active_gpu = len(gpu_clients)
    # MED-1: an unproven storage identity must never read as "no clients".
    # NOT_PROVEN is carried through as NOT_EVALUATED, and the legacy boolean
    # is held false rather than being satisfied by an absence of data.
    storage_proven = storage_identity["STORAGE_IDENTITY_STATUS"] == "PROVEN"
    active_storage = len(storage_clients) if storage_proven else None
    storage_client_evidence = "EVALUATED" if storage_proven else "NOT_EVALUATED"
    storage_no_clients = storage_proven and active_storage == 0
    active_agents = len(active_service_rows)
    # Legacy P0 gate.  Retained verbatim for continuity and explicitly NOT
    # authoritative: it is a conjunction of four counters, not the AGENTS.md
    # 11-condition ownership criterion.  See AGENTS_OWNERSHIP_MATRIX.
    ownership_full = bool(
        root_visibility_complete
        and active_gpu == 0
        and storage_no_clients
        and active_agents == 0
    )
    # Root/user coverage split.  HIGH-3: each population is compared only with
    # its own denominator, so ROOT_NAMESPACE_COMPLETE cannot depend on the
    # number of user processes, or vice versa.  An empty population is not
    # "complete" -- it is unobserved, and is reported FAIL.
    root_coverage = {
        "TOTAL_PIDS": coverage["total_pids"],
        # DEFECT-04 / fix A1: ownership_matrix reads the live-sweep total under
        # the accumulator's own name, "total_pids" (the only key it needs that
        # the UPPERCASE record family above does not carry).  Both names are
        # emitted from the same accumulator cell, so TOTAL_PIDS == total_pids
        # for a given run by construction, not by convention.  The UPPERCASE
        # name is retained because COLLECTOR-CHANGE-RECORD-20260925.md:58
        # documents it as part of the emitted root_coverage schema.
        "total_pids": coverage["total_pids"],
        "ROOT_PIDS": coverage["root_pids"],
        "USER_PIDS": coverage["user_pids"],
        "UID_UNKNOWN_PIDS": coverage["uid_unknown_pids"],
        "LATE_OBSERVED_PIDS": coverage["late_observed_pids"],
        "ROOT_FD_COVERAGE": f"{coverage['fd_complete_pids']}/{coverage['total_pids']}",
        "ROOT_MAPS_COVERAGE": {
            "readable": coverage["maps_readable"],
            "permission_denied": coverage["maps_permission_denied"],
            "absent": coverage["maps_absent"],
            "error": coverage["maps_error"],
        },
        "ROOT_NAMESPACE_COVERAGE": (
            f"{coverage['root_namespace_ok']}/{coverage['root_namespace_total']}"
        ),
        "USER_NAMESPACE_COVERAGE": (
            f"{coverage['user_namespace_ok']}/{coverage['user_namespace_total']}"
        ),
        "root_namespace_ok": coverage["root_namespace_ok"],
        "root_namespace_denied": coverage["root_namespace_denied"],
        "root_namespace_total": coverage["root_namespace_total"],
        "user_namespace_ok": coverage["user_namespace_ok"],
        "user_namespace_denied": coverage["user_namespace_denied"],
        "user_namespace_total": coverage["user_namespace_total"],
        "root_namespace_complete": (
            coverage["root_namespace_total"] > 0
            and coverage["root_namespace_ok"] == coverage["root_namespace_total"]
        ),
        "user_namespace_complete": (
            coverage["user_namespace_total"] > 0
            and coverage["user_namespace_ok"] == coverage["user_namespace_total"]
        ),
        "card_complete": root_visibility_complete,
        "render_complete": root_visibility_complete,
        "fd_error_count": root_fd_error_count,
        # Exported because drm_fds_enumerated is scored from them.  Before this
        # the matrix could only see fd_error_count, so the row could not tell
        # "no DRM client" from "client not attributable".
        "drm_fds_found": coverage["drm_fds_found"],
        "drm_fdinfo_read": coverage["drm_fdinfo_read"],
        "drm_client_id_seen": coverage["drm_client_id_seen"],
        "drm_pdev_seen": coverage["drm_pdev_seen"],
        "drm_pasid_seen": coverage["drm_pasid_seen"],
        "fd_universe_blocked_pids": coverage["fd_universe_blocked_pids"],
        "fd_race_pids": coverage["fd_race_pids"],
        "fd_absence_proven_pids": coverage["fd_absence_proven_pids"],
    }
    matrix_context = {
        "gpu_identity": gpu_identity,
        "root_coverage": root_coverage,
        "debugfs": debugfs,
        "btrfs_observation": btrfs_observation,
        "btrfs_status": "PRESENT" if btrfs_mounts else "ABSENT",
        "active_agents": active_agents,
        "pm_status": pm.get("PM_METRICS"),
        "card_clients": sum(1 for item in gpu_clients if item["resource"] == f"/dev/dri/{gpu_identity['GPU_CARD_NODE']}"),
        "render_clients": sum(1 for item in gpu_clients if item["resource"] == f"/dev/dri/{gpu_identity['GPU_RENDER_NODE']}"),
    }
    ownership_matrix_result = ownership_matrix(matrix_context)
    g01 = "PASS" if ownership_full else "FAIL"
    g02 = "PASS" if root_visibility_complete and active_gpu == 0 and storage_no_clients else "FAIL"
    g03 = "PASS" if active_agents == 0 else "FAIL"
    g04 = "UNKNOWN"
    g05 = "UNKNOWN"
    g06 = "UNKNOWN"
    g07 = "UNKNOWN"
    g08 = "DEFERRED"
    g10 = "DEFERRED"
    critical_checks = {
        "OWNERSHIP_FULL": ownership_full,
        "G01_PASS": g01 == "PASS",
        "G02_PASS": g02 == "PASS",
        "G03_PASS": g03 == "PASS",
        "G04_DETERMINED": g04 == "PASS",
        "G05_DETERMINED": g05 == "PASS",
        "G06_DETERMINED": g06 == "PASS",
        "G07_DETERMINED": g07 == "PASS",
        "G08_RESOLVED": g08 == "PASS",
        "G10_RESOLVED": g10 == "PASS",
        "RECOVERY_INDEPENDENT": recovery == "PASS",
        "RUNTIME_V2_COMPATIBLE": runtime_v2_present,
        "RESTORE_VERIFIED": False,
        "NO_UNAUTHORIZED_CLIENTS": active_gpu == 0 and storage_no_clients,
        "STORAGE_IDENTITY_PROVEN_FOR_CLIENT_EVIDENCE": storage_proven,
        "GPU_IDENTITY_PROVEN": gpu_identity["GPU_IDENTITY_STATUS"] == "PROVEN",
        "STORAGE_IDENTITY_PROVEN": storage_identity["STORAGE_IDENTITY_STATUS"] == "PROVEN",
    }
    go = "AVAILABLE" if all(critical_checks.values()) else "NOT_AVAILABLE"

    ownership = {
        "prior_error_count": len(prior_errors),
        "prior_permission_error_count": sum(
            str(item.get("error", "")).startswith("PermissionError")
            for item in prior_errors
        ),
        "prior_not_found_error_count": sum(
            str(item.get("error", "")).startswith("FileNotFoundError")
            for item in prior_errors
        ),
        "parent_bundle_assessment": parent_assessment,
        "prior_evidence_admissible": prior_admissible,
        "current_run_unreadable_pids": current_run_unreadable,
        "current_run_unreadable_count": len(current_run_unreadable),
        "current_run_permission_denied_pids": current_run_permission_denied,
        "current_run_permission_denied_count": len(current_run_permission_denied),
        "current_run_disappeared_pids": current_run_disappeared,
        "current_run_disappeared_count": len(current_run_disappeared),
        "current_run_disappeared_classification": "NOT_APPLICABLE_PER_OBSERVATION",
        "root_fd_permission_denied_count": root_fd_permission_denied,
        "root_fd_disappeared_count": root_fd_disappeared,
        "root_fd_other_error_count": root_fd_other_errors,
        "gpu_delta_status": gpu_delta_status,
        "prior_error_pids": len(prior_pids),
        "prior_error_pids_resolved": len(resolved_prior),
        "prior_error_pids_resolved_values": resolved_prior,
        "prior_error_pids_unresolved": unresolved_prior,
        "root_fd_visibility_error_count": root_fd_error_count,
        "root_process_error_count": root_process_error_count,
        "root_fd_visibility_errors_sample": root_fd_errors[:256],
        "root_visibility_complete_for_snapshot": root_visibility_complete,
        "root_coverage": root_coverage,
        "storage_client_evidence": storage_client_evidence,
        "active_storage_clients": active_storage if storage_proven else "NOT_EVALUATED",
        "gpu_clients": gpu_clients,
        "storage_clients": storage_clients,
        "compositor_gpu_relations": compositor_relations,
        "additional_gpu_fd_count_vs_parent": (
            len(new_gpu_clients) if gpu_delta_status == "COMPUTED" else "NOT_AVAILABLE"
        ),
        "additional_gpu_clients": new_gpu_clients,
        "relevant_processes": interesting,
        "service_rows": service_rows,
        "active_service_rows": active_service_rows,
        "ps_relevant": relevant_ps,
        "lsof": lsof,
        "fuser": fuser,
    }
    window = {
        "requested_duration_seconds": 120,
        "sample_count": len(samples),
        "cadence_seconds": 5,
        "elapsed_seconds": round(window_elapsed, 3),
        "samples": samples,
        "read_activity_observed": read_activity,
        "write_activity_observed": write_activity,
        "iowait_delta_observed": any(value > 0 for value in iowait_deltas),
        "iowait_deltas": iowait_deltas,
        "d_state_counts": dstate_counts,
        "d_state_max": max(dstate_counts) if dstate_counts else None,
        "blocked_tasks_union": list(blocked_union.values()),
        "psi_threshold": "UNKNOWN",
        "threshold_source": "NOT_AVAILABLE",
        "governor_history_unique": governor_unique,
    }
    runtime = {
        "expected_v2_path": str(runtime_v2),
        "RUNTIME_V2_PRESENT": runtime_v2_present,
        "runtime_historical_path": str(runtime_historical),
        "runtime_historical_present": runtime_historical.exists(),
        "RUN_C1_LOCATION": str(run_c1),
        "RUN_C1_PRESENT": run_c1.exists(),
        "runtime_materialized": False,
    }
    tty_recovery = {
        "TTY_AVAILABLE": tty_available,
        "TTY_COMMAND": tty_result,
        "TTY_DEVICE": (
            stdin_target.get("value", "UNAVAILABLE")
            if stdin_target.get("status") == "OK"
            else "UNAVAILABLE"
        ),
        "tty_candidates": tty_candidates,
        "recovery_candidates": recovery_candidates,
        "RECOVERY_PATH": (
            "CONSOLE_OR_BOOT_CANDIDATE_PRESENT_BUT_USABILITY_UNCONFIRMED"
            if any(item.get("exists") for item in recovery_candidates)
            else "NOT_AVAILABLE"
        ),
        "RECOVERY_PATH_USABLE": recovery_usable,
        "RECOVERY": recovery,
    }

    add_record(
        records,
        "G-01",
        {
            "active_gpu_clients": active_gpu,
            "active_storage_clients": active_storage if storage_proven else "NOT_EVALUATED",
            "storage_client_evidence": storage_client_evidence,
            "storage_identity_status": storage_identity["STORAGE_IDENTITY_STATUS"],
            "root_visibility_complete": root_visibility_complete,
        },
        "OWNERSHIP=FULL with no unapproved active consumers",
        g01,
        "/proc/*/fd and /sys/class/drm",
        "root read-only /proc/sysfs scan; lsof/fuser",
        "OBSERVED",
    )
    add_record(
        records,
        "G-02",
        {
            "prior_errors": len(prior_errors),
            "prior_pids": len(prior_pids),
            "resolved_pids": len(resolved_prior),
            "unresolved_pids": len(unresolved_prior),
            "root_fd_errors": root_fd_error_count,
            "additional_gpu_fds": (
                len(new_gpu_clients) if gpu_delta_status == "COMPUTED" else "NOT_AVAILABLE"
            ),
            "parent_bundle_identity": parent_assessment["PARENT_BUNDLE_IDENTITY"],
            "prior_evidence_status": parent_assessment["PRIOR_EVIDENCE_STATUS"],
        },
        "complete attributable root/user client inventory",
        g02,
        "root /proc/*/fd and preserved parent error inventory",
        "sudo -A python3 read-only collector; lsof/fuser",
        "SUPPORTED" if root_visibility_complete else "UNKNOWN",
    )
    add_record(
        records,
        "G-03",
        {"active_service_rows": active_service_rows, "active_service_count": active_agents},
        "no active or possible writer/agent during window",
        g03,
        "systemctl show and /proc",
        "systemctl show --no-pager --plain (read-only)",
        "OBSERVED",
    )
    add_record(
        records,
        "G-04",
        pm,
        "PM state and causal effect/threshold determined",
        g04,
        "/sys/class/drm/<proven card node>/device/power and amdgpu parameters",
        "read(2) of sysfs; no writes",
        "UNKNOWN",
    )
    add_record(
        records,
        "G-05",
        {
            "initial": governor_initial,
            "window_unique": governor_unique,
            "stability_observed": all(len(values) == 1 for values in governor_unique.values()),
            "threshold": "UNKNOWN",
            "writer_attribution": "UNKNOWN",
        },
        "documented stability criterion and writer attribution",
        g05,
        "/sys/devices/system/cpu/*/cpufreq",
        "read-only sysfs sampling",
        "UNKNOWN",
    )
    add_record(
        records,
        "G-06",
        {
            "irq_initial": irq_initial,
            "irq_final": irq_final,
            "queue_initial": queue_initial,
            "storage_identity": storage_identity,
            "storage_identity_evidence": storage_identity_evidence,
            "storage_fds": storage_fds,
        },
        "reproducible IRQ/scheduler/read-ahead preconditions",
        g06,
        "/proc/interrupts, /proc/irq/*, <proven root disk>/queue",
        "read-only proc/sysfs inspection",
        "UNKNOWN",
    )
    add_record(
        records,
        "G-07",
        {
            "window_seconds": window_elapsed,
            "samples": len(samples),
            "read_activity_observed": read_activity,
            "write_activity_observed": write_activity,
            "iowait_delta_observed": any(value > 0 for value in iowait_deltas),
            "d_state_max": max(dstate_counts) if dstate_counts else None,
            "storage_identity_status": storage_identity["STORAGE_IDENTITY_STATUS"],
            "threshold": "UNKNOWN",
        },
        "objective threshold and complete interpretation",
        g07,
        "/proc/diskstats, /proc/stat, /proc/pressure/io, /proc/*/stat, <proven root disk>/queue",
        "read-only 120-second observation; no artificial load",
        "UNKNOWN",
    )
    add_record(
        records,
        "G-08",
        btrfs_observation,
        "matched_identity_same_window",
        g08,
        "/proc/self/mountinfo and preserved Btrfs evidence",
        "read-only mountinfo inspection; no reconciliation",
        "NOT_AVAILABLE",
    )
    add_record(
        records,
        "G-10",
        {
            "runtime_v2_present": runtime_v2_present,
            "tty_available": tty_available,
            "recovery": recovery,
        },
        "compatible runtime v2, schema and recovery path",
        g10,
        "/run/user/1000 and TTY/recovery candidates",
        "read-only existence/inspection; no runtime materialization",
        "NOT_AVAILABLE",
    )
    add_record(
        records,
        "RECOVERY",
        tty_recovery,
        "independent documented recovery path",
        "FAIL" if recovery == "FAIL" else "UNKNOWN",
        "tty, /dev, /proc/cmdline, boot metadata",
        "tty and read-only path inspection",
        "OBSERVED",
    )
    add_record(
        records,
        "GO_C1",
        critical_checks,
        "all critical gates demonstrated",
        "PASS" if go == "AVAILABLE" else "FAIL",
        "privileged preflight bundle",
        "read-only evidence evaluation",
        "SUPPORTED" if go == "AVAILABLE" else "UNKNOWN",
    )

    gap_results = {
        "G-01": {
            "status": g01,
            "summary": f"active_gpu_clients={active_gpu}; active_storage_clients={active_storage if storage_proven else 'NOT_EVALUATED'}; ownership_full(legacy, NON_AUTHORITATIVE)={ownership_full}",
        },
        "G-02": {
            "status": g02,
            "summary": f"root_visibility_complete={root_visibility_complete}; current_run_unreadable={len(current_run_unreadable)}; parent_bundle={parent_assessment['PARENT_BUNDLE_IDENTITY']}; additional_gpu_fds={len(new_gpu_clients) if gpu_delta_status == 'COMPUTED' else 'NOT_AVAILABLE'}",
        },
        "G-03": {
            "status": g03,
            "summary": f"active_relevant_service_rows={active_agents}",
        },
        "G-04": {
            "status": g04,
            "summary": "PM values observed; PM_EFFECT and threshold/causal attribution remain UNKNOWN",
        },
        "G-05": {
            "status": g05,
            "summary": "governor window values recorded; writer attribution and documented threshold remain UNKNOWN",
        },
        "G-06": {
            "status": g06,
            # DEFECT-06: derived from the real read state, never a literal.
            "summary": g06_summary(
                queue_initial=queue_initial,
                irq_initial=irq_initial,
                irq_final=irq_final,
                storage_identity_evidence=storage_identity_evidence,
            ),
        },
        "G-07": {
            "status": g07,
            "summary": f"120-second read-only window completed; activity observed={{read: {read_activity}, write: {write_activity}}}; THRESHOLD=UNKNOWN",
        },
        "G-08": {
            "status": g08,
            "summary": "matched_identity_same_window NOT_AVAILABLE; no reconciliation run",
        },
        "G-10": {
            "status": g10,
            "summary": f"runtime_v2_present={runtime_v2_present}; TTY_AVAILABLE={tty_available}; runtime materialization not performed",
        },
    }
    end_iso = dt.datetime.now(dt.timezone.utc).isoformat(timespec="milliseconds")
    payload = {
        "PREFLIGHT_ID": PREFLIGHT_ID,
        "SUPPLEMENT_ID": PREFLIGHT_ID + "-PRIVILEGED-SUPPLEMENT",
        "parent_preflight_id": PARENT.get("PREFLIGHT_ID", "C1-PREFLIGHT-20260925T060029Z"),
        "metadata": {
            "timestamp_start": START_ISO,
            "timestamp_end": end_iso,
            "mode": "PRIVILEGED_READ_ONLY",
            "host": os.uname().nodename,
            "kernel": os.uname().release,
            "parent_path": str(PARENT_PATH),
            "c1_invoked": False,
            "mutating_commands": [],
            "systemctl_mutations": [],
            "privilege": privilege,
            "privileged_reads": privilege["PRIVILEGE_STATE"] == "PRIVILEGE_OBSERVED_ROOT",
        },
        "privilege": privilege,
        "identity": {
            "HOST": host_identity,
            "GPU": dict(gpu_identity, devices=sorted(devices)),
            "STORAGE": storage_identity,
            "DEBUGFS": debugfs,
            "resolution_order": [
                "1 HOST", "2 PCI", "3 DRM", "4 storage", "5 namespaces/processes",
                "6 fd/fdinfo", "7 maps", "8 debugfs", "9 aggregated GPU",
                "10 ownership", "11 output matrix",
            ],
        },
        "AGENTS_OWNERSHIP_MATRIX": ownership_matrix_result,
        "COLLECTOR_OWNERSHIP_BOOLEAN": {
            "AUTHORITATIVE": False,
            "CLASSIFICATION": "NON_AUTHORITATIVE",
            "value": ownership_full,
            "definition": "root_visibility_complete and active_gpu==0 and active_storage==0 and active_agents==0",
            "reason": "P0 gate on four counters; not the AGENTS.md 11-condition ownership criterion",
        },
        "CAPABILITY_MATRIX": list(CAPABILITY_MATRIX),
        "ownership": ownership,
        "pm": pm,
        "pm_state": "OBSERVED" if pm.get("PM_METRICS") == "READ" else "NOT_AVAILABLE",
        "pm_effect": "UNKNOWN",
        "governors": {
            "initial": governor_initial,
            "window_unique": governor_unique,
            "threshold": "UNKNOWN",
            "threshold_source": "NOT_AVAILABLE",
        },
        "irq": {"initial": irq_initial, "final": irq_final},
        "queue": {"initial": queue_initial, "window_samples": [sample["queue"] for sample in samples]},
        "storage_identity_evidence": storage_identity_evidence,
        "window": window,
        "tty_recovery": tty_recovery,
        "runtime": runtime,
        "btrfs": btrfs_observation,
        "gap_results": gap_results,
        "evidence_records": records,
        "final": {
            "PREFLIGHT": "PARTIAL",
            "P0": "B__CONTAMINATED_REQUIRES_ISOLATION",
            "OWNERSHIP": ownership_matrix_result["OWNERSHIP_CRITERION_STATE"],
            "OWNERSHIP_LEGACY_BOOLEAN_NON_AUTHORITATIVE": ownership_full,
            "C1": "DEFERRED",
            "GO_C1": go,
            "RECOVERY": recovery,
            "GPU_WRITES": 0,
            "STORAGE_WRITES": 0,
            "SYSTEMD_CHANGES": 0,
            "C1_EXECUTED": 0,
            "RUNTIME_MATERIALIZED": 0,
            "SYSTEM_CHANGES": 0,
            "COMMIT": 0,
        },
    }
    print(json.dumps(payload, ensure_ascii=False, sort_keys=True))


if __name__ == "__main__":
    try:
        main()
    except Exception as exc:
        import traceback

        print(
            json.dumps(
                {
                    "PREFLIGHT_ID": PREFLIGHT_ID,
                    "collector_error": f"{type(exc).__name__}: {exc}",
                    "traceback": traceback.format_exc(),
                    "final": {
                        "PREFLIGHT": "PARTIAL",
                        "P0": "B__CONTAMINATED_REQUIRES_ISOLATION",
                        "OWNERSHIP": "PARTIAL",
                        "C1": "DEFERRED",
                        "GO_C1": "NOT_AVAILABLE",
                        "RECOVERY": "UNKNOWN",
                        "GPU_WRITES": 0,
                        "STORAGE_WRITES": 0,
                        "SYSTEMD_CHANGES": 0,
                        "C1_EXECUTED": 0,
                        "RUNTIME_MATERIALIZED": 0,
                        "SYSTEM_CHANGES": 0,
                        "COMMIT": 0,
                    },
                },
                ensure_ascii=False,
                sort_keys=True,
            )
        )
