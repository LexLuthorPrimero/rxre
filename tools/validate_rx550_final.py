#!/usr/bin/env python3
"""Read-only validation of the RX 550 host contract.

This tool never writes sysfs, starts/stops services, changes kernel parameters,
runs a workload, or invokes a benchmark.  It identifies the target by PCI BDF and
vendor/device, then records versions, runtime renderers, PM/DPM readbacks,
bounded boot-journal signals, service state, storage identity, and Git metadata.

Exit codes:
  0  target PCI identity was found (individual checks may still be NOT_AVAILABLE)
  2  target PCI identity was not found
  3  an unexpected internal error occurred
"""
from __future__ import annotations

import argparse
import datetime as dt
import glob
import json
import os
import platform
import re
import subprocess
import sys
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[1]
TARGET_VENDOR = 0x1002
TARGET_DEVICE = 0x699F
TARGET_PCI = f"{TARGET_VENDOR:04x}:{TARGET_DEVICE:04x}"
TARGET_BDF = "0000:01:00.0"


def read(path: str | Path) -> str | None:
    try:
        return Path(path).read_text(encoding="utf-8", errors="replace").strip()
    except (OSError, UnicodeError):
        return None


def command(argv: list[str], env: dict[str, str] | None = None) -> dict[str, Any]:
    try:
        p = subprocess.run(
            argv,
            capture_output=True,
            text=True,
            timeout=30,
            env=env,
            check=False,
        )
        return {
            "available": True,
            "returncode": p.returncode,
            "stdout": p.stdout,
            "stderr": p.stderr,
        }
    except FileNotFoundError:
        return {"available": False, "returncode": None, "stdout": "", "stderr": "NOT_AVAILABLE"}
    except (OSError, subprocess.SubprocessError) as exc:
        return {"available": False, "returncode": None, "stdout": "", "stderr": type(exc).__name__}


def first(pattern: str, text: str) -> str | None:
    match = re.search(pattern, text, re.IGNORECASE | re.MULTILINE)
    return match.group(1).strip() if match else None


def target_gpu() -> dict[str, Any]:
    devices = Path("/sys/bus/pci/devices")
    found: list[dict[str, Any]] = []
    for device in sorted(devices.glob("*")):
        vendor = read(device / "vendor")
        device_id = read(device / "device")
        if not vendor or not device_id:
            continue
        try:
            vendor_i = int(vendor, 16)
            device_i = int(device_id, 16)
        except ValueError:
            continue
        if (vendor_i, device_i) != (TARGET_VENDOR, TARGET_DEVICE):
            continue
        real = str(device.resolve())
        driver_link = device / "driver"
        driver = driver_link.resolve().name if driver_link.is_symlink() else None
        drm_cards = sorted(Path(real).glob("drm/card[0-9]*"))
        card = drm_cards[0].name if drm_cards else None
        hwmons = sorted((device / "hwmon").glob("hwmon[0-9]*"))
        by_path = sorted(Path("/dev/dri/by-path").glob(f"pci-{device.name}-render"))
        found.append({
            "pci_id": f"{vendor_i:04x}:{device_i:04x}",
            "bdf": device.name,
            "driver": driver,
            "drm_card": card,
            "hwmon": hwmons[0].name if hwmons else None,
            "render_node": str(by_path[0].resolve()) if by_path else None,
            "sysfs_device": str(device),
        })
    if not found:
        return {"status": "NOT_AVAILABLE", "matches": []}
    exact = [g for g in found if g["bdf"] == TARGET_BDF]
    selected = dict(exact[0] if exact else found[0])
    selected["status"] = "OBSERVED"
    selected["matches"] = [dict(g) for g in found]
    return selected


def renderer_evidence() -> dict[str, Any]:
    out: dict[str, Any] = {}
    gl = command(["glxinfo", "-B"])
    out["glxinfo_default"] = {
        "status": "OBSERVED" if gl["available"] and gl["returncode"] == 0 else "NOT_AVAILABLE",
        "renderer": first(r"^OpenGL renderer string:\s*(.+)$", gl["stdout"]),
        "vendor": first(r"^OpenGL vendor string:\s*(.+)$", gl["stdout"]),
    }
    env = dict(os.environ)
    env["DRI_PRIME"] = TARGET_PCI
    gl_forced = command(["glxinfo", "-B"], env)
    out["glxinfo_dri_prime_pci"] = {
        "status": "OBSERVED" if gl_forced["available"] and gl_forced["returncode"] == 0 else "NOT_AVAILABLE",
        "renderer": first(r"^OpenGL renderer string:\s*(.+)$", gl_forced["stdout"]),
        "vendor": first(r"^OpenGL vendor string:\s*(.+)$", gl_forced["stdout"]),
    }

    icds = sorted(glob.glob("/usr/share/vulkan/icd.d/radeon_icd*.json"))
    icd = next((p for p in icds if p.endswith("x86_64.json")), icds[0] if icds else None)
    venv = dict(os.environ)
    if icd:
        venv["VK_ICD_FILENAMES"] = icd
        venv.pop("VK_DRIVER_FILES", None)
    vk = command(["vulkaninfo", "--summary"], venv)
    out["vulkan_radv_icd"] = {
        "status": "OBSERVED" if vk["available"] and vk["returncode"] == 0 else "NOT_AVAILABLE",
        "icd": Path(icd).name if icd else None,
        "device_names": re.findall(r"^\s*deviceName\s*=\s*(.+)$", vk["stdout"], re.MULTILINE),
        "device_ids": re.findall(r"^\s*deviceID\s*=\s*(.+)$", vk["stdout"], re.MULTILINE),
    }
    return out


def package_versions() -> dict[str, Any]:
    names = [
        "kernel-core", "mesa-dri-drivers", "mesa-vulkan-drivers", "mesa-libGL",
        "mesa-libEGL", "mesa-libgbm", "libdrm", "llvm-libs", "vulkan-loader",
        "vulkan-tools", "linux-firmware",
    ]
    p = command(["rpm", "-q", *names])
    by_name: dict[str, list[str]] = {}
    for line in p["stdout"].splitlines():
        if "-" not in line:
            continue
        matched = next((n for n in sorted(names, key=len, reverse=True) if line.startswith(n + "-")), None)
        if matched:
            by_name.setdefault(matched, []).append(line[len(matched) + 1:])
    versions: dict[str, str | None] = {}
    for name in names:
        values = by_name.get(name, [])
        versions[name] = next((v for v in values if ".x86_64" in v), values[0] if values else None)
    return {"status": "OBSERVED" if p["available"] and p["returncode"] in (0, 1) else "NOT_AVAILABLE", "packages": versions}


def pm_dpm(gpu: dict[str, Any]) -> dict[str, Any]:
    if not gpu.get("sysfs_device"):
        return {"status": "NOT_AVAILABLE"}
    device = Path(gpu["sysfs_device"])
    hw = device / "hwmon" / (gpu.get("hwmon") or "")
    fields = {
        "power_control": device / "power/control",
        "runtime_status": device / "power/runtime_status",
        "dpm_level": device / "power_dpm_force_performance_level",
        "sclk_states": device / "pp_dpm_sclk",
        "mclk_states": device / "pp_dpm_mclk",
        "power_profile": device / "pp_power_profile_mode",
        "power1_input_uw": hw / "power1_input",
        "power1_cap_uw": hw / "power1_cap",
        "power1_cap_default_uw": hw / "power1_cap_default",
        "power1_cap_max_uw": hw / "power1_cap_max",
        "temp1_input_mc": hw / "temp1_input",
    }
    values = {key: read(path) for key, path in fields.items()}
    return {"status": "OBSERVED" if any(v is not None for v in values.values()) else "NOT_AVAILABLE", "values": values}


def journal_evidence() -> dict[str, Any]:
    kernel = command(["journalctl", "-b", "-k", "--no-pager", "-o", "cat"])
    text = kernel["stdout"] if kernel["available"] else ""
    patterns = {
        "gpu_reset": r"(?i)gpu reset|reset begin|reset success|asic reset",
        "ring_timeout": r"(?i)ring .*timeout|job timeout|gfx (?:hang|timeout)",
        "ra24": r"(?i)RA24|unsupported screen format",
        "amdgpu_error_like": r"(?i)amdgpu.*(?:error|failed|timeout|fault)",
    }
    counts = {name: len(re.findall(pattern, text)) for name, pattern in patterns.items()}
    lines = text.splitlines()
    counts["vm_fault_non_prt"] = sum(
        1 for line in lines
        if re.search(r"(?i)VM fault|GPU fault", line)
        and not re.search(r"(?i)Disabling VM faults because of PRT request", line)
    )
    counts["prt_notice"] = sum(
        1 for line in lines if re.search(r"(?i)Disabling VM faults because of PRT request", line)
    )
    kwin = command(["journalctl", "-b", "_COMM=kwin_wayland", "--no-pager", "-o", "cat"])
    ktext = kwin["stdout"] if kwin["available"] else ""
    return {
        "status": "OBSERVED" if kernel["available"] else "NOT_AVAILABLE",
        "kernel_signal_counts": counts,
        "kwin_permission_denied_count": len(re.findall(r"(?i)permission denied|permiso denegado", ktext)),
        "journal_query_errors": [kernel.get("stderr", ""), kwin.get("stderr", "")],
    }


def services_evidence() -> dict[str, Any]:
    names = [
        "kalm-gpu.service", "kalm.service", "system-autopilot.timer",
        "sys-tuned.service", "irqbalance.service",
    ]
    active = command(["systemctl", "is-active", *names])
    enabled = command(["systemctl", "is-enabled", *names])
    return {
        "status": "OBSERVED" if active["available"] else "NOT_AVAILABLE",
        "active": dict(zip(names, active["stdout"].splitlines())),
        "enabled": dict(zip(names, enabled["stdout"].splitlines())),
    }


def storage_evidence() -> dict[str, Any]:
    root = command(["findmnt", "-n", "-o", "SOURCE,FSTYPE,OPTIONS", "/"])
    home = command(["findmnt", "-n", "-o", "SOURCE,FSTYPE,OPTIONS", "/home"])
    return {
        "status": "OBSERVED" if root["available"] and root["returncode"] == 0 else "NOT_AVAILABLE",
        "root": root["stdout"].strip() if root["available"] else None,
        "home": home["stdout"].strip() if home["available"] else None,
        "smart_checked": False,
    }


def git_evidence() -> dict[str, Any]:
    def one(argv: list[str]) -> str | None:
        p = command(argv)
        return p["stdout"].strip() if p["available"] and p["returncode"] == 0 else None
    status = command(["git", "status", "--porcelain=v1", "--untracked-files=all"])
    lines = status["stdout"].splitlines() if status["available"] else []
    return {
        "status": "OBSERVED",
        "branch": one(["git", "branch", "--show-current"]),
        "remote": one(["git", "remote"]),
        "worktree_entries": len(lines),
        "commit": one(["git", "rev-parse", "HEAD"]),
    }


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--output", type=Path, help="write the JSON report to this explicit path")
    args = parser.parse_args()

    gpu = target_gpu()
    report: dict[str, Any] = {
        "schema": "rx550-final-validation-1",
        "generated_at": dt.datetime.now(dt.timezone.utc).isoformat(timespec="seconds"),
        "mode": "READ_ONLY/EVIDENCE",
        "writes_to_system": False,
        "benchmarks_executed": False,
        "target": {"pci_id": TARGET_PCI, "expected_bdf": TARGET_BDF},
        "host": {
            "os_release": read("/etc/os-release"),
            "kernel": platform.release(),
            "xDG_session_type": os.environ.get("XDG_SESSION_TYPE"),
            "xDG_current_desktop": os.environ.get("XDG_CURRENT_DESKTOP"),
        },
        "gpu": gpu,
        "packages": package_versions(),
        "renderers": renderer_evidence(),
        "pm_dpm": pm_dpm(gpu),
        "journal": journal_evidence(),
        "services": services_evidence(),
        "storage": storage_evidence(),
        "git": git_evidence(),
        "limitations": [
            "No benchmark, A/B, power-cap write, service change, GPU reset, SMART, or Btrfs write was executed.",
            "A missing tool or inaccessible field remains NOT_AVAILABLE; it is not treated as success.",
            "The presence of a renderer does not prove the cause of a historical performance regime.",
        ],
    }
    report["validation_status"] = "OBSERVED" if gpu.get("status") == "OBSERVED" else "NOT_AVAILABLE"
    text = json.dumps(report, ensure_ascii=False, indent=2, sort_keys=True) + "\n"
    if args.output:
        args.output.parent.mkdir(parents=True, exist_ok=True)
        args.output.write_text(text, encoding="utf-8")
    else:
        sys.stdout.write(text)
    return 0 if gpu.get("status") == "OBSERVED" else 2


if __name__ == "__main__":
    try:
        raise SystemExit(main())
    except Exception as exc:  # noqa: BLE001
        print(json.dumps({"validation_status": "UNKNOWN", "error": type(exc).__name__}), file=sys.stderr)
        raise SystemExit(3)
