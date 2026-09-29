#!/usr/bin/env python3
"""C1 Isolation Automator v1.1.1.

Runtime-only, auditable orchestration for the already-authorized minimal C1
route.  This file contains no automatic retry and never changes RX550 controls,
Mesa, sysctl, Btrfs, schedulers, IRQ affinity, PM, DPM, or workload parameters.

The active runtime namespace is versioned separately from the preserved
pre-fix legacy namespace.  Legacy artifacts are classified read-only and are
never loaded as active state.

Modes:
  --dry-run  read-only plan; never creates runtime state and never invokes sudo
  --prepare  static/read-only preparation checks; no runtime state and no sudo
  --status   read the last runtime state, if any
  --run      real workflow; requires a TTY, explicit confirmation, and normal
             interactive sudo; intentionally not executed during validation

The real path is fail-safe: an active unit is stopped only after its PRE state
is recorded; every attempted stop is tracked for conditional restoration.
"""
from __future__ import annotations

import argparse
import datetime as dt
import fcntl
import hashlib
import json
import math
import os
import platform
import re
import shlex
import shutil
import signal
import stat as stat_module
import subprocess
import sys
import tempfile
import time
from pathlib import Path
from typing import Any, Callable, Dict, List, Optional, Sequence, Tuple


VERSION = "1.1.1"
RUNTIME_NAMESPACE_VERSION = 2
RUNTIME_SCHEMA_VERSION = 2
LEGACY_RUNTIME_NAMESPACE = "c1-isolation-automator"
RUNTIME_NAMESPACE = "c1-isolation-automator-v2"
PROJECT = Path("/home/lucas/Escritorio/RX550-INVESTIGACION")
IMPLEMENTATION_DIR = PROJECT / "04-IMPLEMENTACION"
WORKLOAD_DIR = PROJECT / "03-EXPERIMENTOS" / "WORKLOAD-SINTETICO"
OBSERVER = WORKLOAD_DIR / "c1_observer.py"
C1_BINARY = WORKLOAD_DIR / "main-graphics"
DOC = IMPLEMENTATION_DIR / "C1-ISOLATION-AUTOMATOR.md"
UID = os.getuid()
RUNTIME_DIR = Path(f"/run/user/{UID}")
LEGACY_STATE_ROOT = RUNTIME_DIR / LEGACY_RUNTIME_NAMESPACE
STATE_ROOT = RUNTIME_DIR / RUNTIME_NAMESPACE
LOCK_PATH = STATE_ROOT / ".lock"
CURRENT_POINTER = STATE_ROOT / "CURRENT"
OBSERVER_JSONL = STATE_ROOT / "c1-observer-v1.jsonl"
RUNTIME_NAMESPACE_ACTIVATED_AT = "2026-09-24T13:38:13-03:00"
LEGACY_RUN_ID = "20260924T154559Z-490709"
LEGACY_MANIFEST_ID = "legacy-c1-isolation-automator-20260924T154559Z-490709-v1"
LEGACY_ROOT_ENTRIES = {".lock", "CURRENT", "runs"}
LEGACY_RUN_ENTRIES = {"state.json", "events.jsonl", "tmp", "cache"}

# The legacy namespace is an immutable, explicitly allowlisted archive.  It is
# never used as an active state root by this version.
HISTORICAL_LEGACY_RUNS: Dict[str, Dict[str, str]] = {
    LEGACY_RUN_ID: {
        "state_sha256": "f368fa91d050267b9fe30fb2e331e87a8a82e43f16f439470cc4b53d167bf99c",
        "events_sha256": "8e7ffbe3693545144037d07727d834422bbb7c8fab81665bc6b7c123bc5d422d",
        "current_sha256": "a06971fcfef0f3fb2f843ed836a7ffc5517a600e345c4838714eb52ab319f31f",
    }
}

EXPECTED_HOST = "lex-luthor"
EXPECTED_KERNEL = "7.2.6-201.nobara.fc44.x86_64"
EXPECTED_BDF = "0000:01:00.0"
EXPECTED_VENDOR = "0x1002"
EXPECTED_DEVICE = "0x699f"
EXPECTED_DRIVER = "amdgpu"
EXPECTED_CARD = "card1"
EXPECTED_RENDER = "renderD129"
EXPECTED_HWMON = "/sys/class/drm/card1/device/hwmon/hwmon2"

EXPECTED_HASHES = {
    "main-graphics": "f278f48c320f3f14edb5d796c75b3df8358e6ca2daf6b9d7d119aa86e0c65e81",
    "src/graphics.cpp": "7f1bf813d577a456d485a55ae01bd684bd746e9a3e03a084db2edcab57943615",
    "c1_observer.py": "0ddae72a65f9c687550be1d491858802c6c133a06b75fa29cc0d30725bd030c1",
    "src/vertex.vert": "18371767808990c9e376db86843a78f7b36c3e0c3593bd27d4d3fc8915899e53",
    "src/fragment.frag": "47a38a3813c0c3c121a60c62b0fd318a1187eb509bb12940b427a8b367180039",
    "src/fragment2.frag": "067adbcde3fecd12f63aa642418811b79bd65512b7ac23eb317f0b538ff23068",
    "Makefile": "82438fbb445a695731f27a4335235047ea0c119ccb9fb9b07a0c7261be7944f2",
}
EXPECTED_BUILD_ID = "c18acae12e6a4ead407ba15c2bed66e057c2676a"
EXPECTED_COMPILER = "GCC 16.2.1"
EXPECTED_CXXFLAGS = "-O2 -std=c++17 -Wall -Wextra"

IO_GUARD_AVG10_MAX = 10.0  # existing proposed operational criterion; not universal
GUARD_SECONDS = 120
T_PRE_SECONDS = 30
T_POST_SECONDS = 30
GUARD_SAMPLE_SECONDS = 5
C1_MAX_SECONDS = 180
SYSTEMCTL_COMMAND_TIMEOUT_SECONDS = 120
PRODUCTION_TTY_REQUIRED = True
ALLOWED_PHASES = {"PRE_CAPTURED", "ABORTED_PRE", "ABORTED_OBSERVER_CHECK", "ISOLATING", "GUARD", "C1", "RESTORING", "COMPLETED"}
ALLOWED_RESULTS = {"IN_PROGRESS", "ABORTED_PRE", "ABORTED_OBSERVER_CHECK", "ABORTED_FAILURE_RESTORE_REQUIRED", "ABORTED_FAILURE_RESTORED", "COMPLETED_RUNTIME_VALIDATED", "COMPLETED_PARTIAL_OR_CONFLICT"}
ALLOWED_GUARD_STATUS = {"NOT_RUN", "PASS", "FAIL", "INTERRUPTED"}
GUARD_SCHEMA_FIELDS = ("status", "reason", "sample_count", "elapsed_seconds", "log")
LEGACY_CLASSIFICATION = "HISTORICAL_LEGACY_RUNTIME"
ACTIVE_CLASSIFICATION = "ACTIVE_INCOMPLETE_RUNTIME"

CONTRACT_VERSION = "c1-isolation-design.v1"
CONTRACT_PENDING = "DEFINED_PENDING_EXECUTION"
CONTRACT_UNKNOWN = "UNKNOWN"
CONTRACT_NOT_AVAILABLE = "NOT_AVAILABLE"
OWNERSHIP_FULL = "FULL"
OWNERSHIP_PARTIAL = "PARTIAL"


def _contract_row(
    resource: str,
    current_owner: str,
    expected_owner: str,
    proof: str,
    fail: str,
    abort: str,
    evidence: str,
    restore_impact: str,
    source: str,
) -> Dict[str, Any]:
    return {
        "resource": resource,
        "current_owner": current_owner,
        "expected_owner": expected_owner,
        "proof": proof,
        "fail": fail,
        "abort": abort,
        "evidence": evidence,
        "restore_impact": restore_impact,
        "source": source,
    }


OWNERSHIP_CONTRACT: Tuple[Dict[str, Any], ...] = (
    _contract_row("card1", "MULTIPLE/UNKNOWN", "C1_EXPERIMENT_ONLY", "identity_plus_complete_client_inventory", "identity_mismatch_or_unapproved_client", "NO_GO_PRE_OR_ABORT_GUARD", "P0", "NO_PROCESS_ACTION", "P0;C1-CODE"),
    _contract_row("renderD129", "MULTIPLE/UNKNOWN", "C1_EXPERIMENT_ONLY", "identity_plus_complete_client_inventory", "identity_mismatch_or_unapproved_client", "NO_GO_PRE_OR_ABORT_GUARD", "P0", "NO_PROCESS_ACTION", "P0;C1-CODE"),
    _contract_row("Xwayland", "OBSERVED_ACCESS_P0", "NO_UNAPPROVED_HANDLE", "pid_fd_client_namespace_recheck", "handle_present_or_inventory_incomplete", "NO_GO_PRE_OR_ABORT_GUARD", "P0", "PROCESS_RESTORE_NOT_DEFINED", "P0"),
    _contract_row("applications", "PARTIAL/UNKNOWN", "C1_AND_INSTRUMENTATION_ONLY", "root_user_process_fd_inventory", "unapproved_application_or_incomplete_inventory", "NO_GO_PRE_OR_ABORT_GUARD", "P0", "NO_STOP_OR_KILL", "P0;C1-CODE"),
    _contract_row("Mesa/RADV", "PROVENANCE_CONFLICT", "TARGET_1002_699F", "icd_maps_driver_argv_provenance", "target_or_provenance_mismatch", "NO_GO_PRE", "DOC-REC", "NO_MESA_MODIFICATION", "C1-DOC;DOC-REC"),
    _contract_row("system-autopilot", "OBSERVED_WRITER", "NO_UNAPPROVED_WRITE", "unit_state_pid_config_and_readback", "active_reappearing_or_unresolved_writer", "NO_GO_PRE_OR_ABORT_GUARD", "P0", "NO_STOP_HERE", "P0;C1-CODE"),
    _contract_row("kalm", "OBSERVED_WRITER", "NO_UNAPPROVED_WRITE", "unit_pid_config_and_irq_readback", "active_polling_write_or_incomplete_scope", "NO_GO_PRE_OR_ABORT_GUARD", "P0", "NO_STOP_HERE", "P0;C1-DOC"),
    _contract_row("kalm-gpu", "POSSIBLE_WRITER", "NO_UNAPPROVED_WRITE", "unit_pid_capability_and_control_readback", "unresolved_capability_write_or_unsafe_unit", "NO_GO_PRE_OR_ABORT_GUARD", "P0", "NO_GPU_OR_PM_MODIFICATION", "P0;C1-CODE"),
    _contract_row("irqbalance", "POSSIBLE_WRITER", "NO_UNAPPROVED_REBALANCE", "unit_pid_config_and_irq_readback", "active_unexplained_migration_or_unknown_author", "NO_GO_PRE_OR_ABORT_GUARD", "P0", "NO_IRQ_MODIFICATION", "P0"),
    _contract_row("runtime_PM", "PARTIALLY_CHARACTERIZED", "STABLE_READBACK_NO_UNAPPROVED_WAKE", "pm_fields_wake_events_and_transitions", "missing_drift_or_unexplained_wake", "NO_GO_PRE_OR_ABORT_GUARD", "P0;OBS", "NO_PM_MODIFICATION", "P0;C1-OBS"),
    _contract_row("governor", "CONFLICT", "STABLE_READBACK_NO_WRITER", "all_policy_snapshots_and_writers", "missing_drift_oscillation_or_unknown_writer", "NO_GO_PRE_OR_ABORT_GUARD", "P0;OBS", "NO_TUNING", "P0;OBS"),
    _contract_row("IRQ", "CONFLICT", "STABLE_READBACK_NO_UNATTRIBUTED_CHANGE", "irq_affinity_snapshots_and_authors", "change_missing_source_or_unexplained_migration", "NO_GO_PRE_OR_ABORT_GUARD", "P0", "NO_IRQ_MODIFICATION", "P0"),
    _contract_row("scheduler", "OBSERVED_WRITER", "STABLE_READBACK_NO_WRITER", "scheduler_priority_renice_snapshots", "change_or_unattributed_renice", "NO_GO_PRE_OR_ABORT_GUARD", "P0", "NO_SCHEDULER_MODIFICATION", "P0"),
    _contract_row("read_ahead", "CONFLICT", "STABLE_READBACK_KNOWN_AUTHOR", "pre_guard_post_value_and_author", "value_change_conflict_or_unknown_author", "NO_GO_PRE_OR_ABORT_GUARD", "P0", "NO_READ_AHEAD_MODIFICATION", "P0"),
    _contract_row("/dev/sda", "OBSERVED_STORAGE", "NO_UNATTRIBUTED_ACTIVITY", "diskstats_psi_actor_and_btrfs_tuple", "unattributed_activity_missing_source_or_unknown_threshold", "NO_GO_PRE_OR_ABORT_GUARD", "P0;OBS;DOC-REC", "NO_SDA_TOUCH", "P0;OBS;DOC-REC"),
    _contract_row("Btrfs", "CONFLICT", "MATCHED_IDENTITY_SAME_WINDOW", "identity_tuple_and_immutable_window_id", "missing_mismatch_or_different_window", "NO_GO_PRE_OR_ABORT_GUARD", "DOC-REC;P0", "NO_PROBE_OR_REPAIR", "DOC-REC;P0"),
)


def ownership_contract() -> List[Dict[str, Any]]:
    return [dict(row) for row in OWNERSHIP_CONTRACT]


def evaluate_ownership_proof(
    proof_records: Optional[Dict[str, Any]] = None,
    runtime_evidence: bool = False,
) -> Dict[str, Any]:
    """Evaluate ownership without allowing static data to claim FULL."""
    result: Dict[str, Any] = {
        "status": OWNERSHIP_PARTIAL,
        "full_proof": False,
        "reason_codes": ["RUNTIME_EVIDENCE_REQUIRED"],
        "required_resources": [row["resource"] for row in OWNERSHIP_CONTRACT],
    }
    if not runtime_evidence:
        return result
    if not isinstance(proof_records, dict) or proof_records.get("evidence_kind") != "RUNTIME_READBACK":
        result["reason_codes"] = ["RUNTIME_READBACK_PROOF_REQUIRED"]
        return result
    by_resource = proof_records.get("resources")
    if not isinstance(by_resource, dict):
        result["reason_codes"] = ["RESOURCE_PROOF_MAP_REQUIRED"]
        return result
    reasons: List[str] = []
    for row in OWNERSHIP_CONTRACT:
        item = by_resource.get(row["resource"])
        if not isinstance(item, dict) or item.get("proof_status") != "PASS" or item.get("proof_source") in {None, "", CONTRACT_UNKNOWN}:
            reasons.append(f"{row['resource']}:PROOF_MISSING_OR_NOT_RUNTIME")
    if reasons:
        result["reason_codes"] = reasons
        return result
    result["status"] = OWNERSHIP_FULL
    result["full_proof"] = True
    result["reason_codes"] = []
    return result


def _system_gate_spec(
    source: str,
    required_fields: Tuple[str, ...],
    restore_impact: str,
) -> Dict[str, Any]:
    return {
        "SOURCE": source,
        "REQUIRED_STATE": "readback_and_attribution_fields_required",
        "FAIL_CONDITION": "missing_drift_unattributed_change_or_unknown",
        "ABORT_CONDITION": "NO_GO_PRE_OR_ABORT_GUARD_BY_PHASE",
        "EVIDENCE": "PRE_GUARD_POST_READBACK_WITH_SOURCE",
        "RESTORE_IMPACT": restore_impact,
        "VALUE": CONTRACT_UNKNOWN,
        "THRESHOLD": CONTRACT_UNKNOWN,
        "THRESHOLD_SOURCE": CONTRACT_NOT_AVAILABLE,
        "required_fields": required_fields,
        "STATUS": CONTRACT_PENDING,
    }


SYSTEM_GATE_CONTRACT: Dict[str, Dict[str, Any]] = {
    "PM": _system_gate_spec("P0;OBS;C1-CODE", ("power_control", "runtime_status", "autosuspend", "wake_events", "writers"), "NO_CHANGE_PLANNED"),
    "GOVERNOR": _system_gate_spec("P0;OBS", ("all_cpu_policies", "writers", "pre_guard_post"), "NO_CHANGE_PLANNED"),
    "IRQ": _system_gate_spec("P0;OBS", ("irq_state", "affinity", "authors", "timestamps"), "NO_CHANGE_PLANNED"),
    "SCHEDULER": _system_gate_spec("P0", ("scheduler", "priority", "renice", "writers"), "NO_CHANGE_PLANNED"),
    "READ_AHEAD": _system_gate_spec("P0", ("value", "author", "pre_guard_post"), "NO_CHANGE_PLANNED"),
    "SDA_ACTIVITY": _system_gate_spec("P0;OBS", ("diskstats", "psi", "device_source", "actor"), "NO_SDA_TOUCH"),
}


def system_gate_contracts() -> Dict[str, Dict[str, Any]]:
    return {name: dict(spec) for name, spec in SYSTEM_GATE_CONTRACT.items()}


def evaluate_system_gate(
    name: str,
    evidence: Optional[Dict[str, Any]] = None,
    runtime_evidence: bool = False,
) -> Dict[str, Any]:
    spec = SYSTEM_GATE_CONTRACT.get(name)
    if spec is None:
        return {
            "CHECK": name,
            "STATUS": "BLOCKED",
            "reason": "UNKNOWN_SYSTEM_GATE",
            "VALUE": CONTRACT_UNKNOWN,
            "THRESHOLD_SOURCE": CONTRACT_NOT_AVAILABLE,
        }
    result = dict(spec)
    result.update({"CHECK": name, "runtime_evidence": bool(runtime_evidence), "evidence": evidence or {}})
    result["STATUS"] = CONTRACT_PENDING
    result["PASS_ALLOWED"] = False
    result["reason"] = "THRESHOLD_UNKNOWN_RUNTIME_EVIDENCE_REQUIRED"
    return result


BTRFS_GATE_CONTRACT: Dict[str, Any] = {
    "CHECK": "BTRFS_IDENTITY",
    "STATUS": "CONFLICT",
    "BTRFS": "CONFLICT",
    "BTRFS_CAUSE": "UNKNOWN",
    "REQUIRED": "matched_identity_same_window",
    "SOURCE": "DOC-REC;P0",
    "VALUE": CONTRACT_UNKNOWN,
    "RUNTIME_EVIDENCE": False,
    "NO_PROBE": True,
}


def btrfs_gate_contract() -> Dict[str, Any]:
    return dict(BTRFS_GATE_CONTRACT)


def evaluate_btrfs_gate(
    evidence: Optional[Dict[str, Any]] = None,
    runtime_evidence: bool = False,
) -> Dict[str, Any]:
    result = btrfs_gate_contract()
    result["RUNTIME_EVIDENCE"] = bool(runtime_evidence)
    result["evidence"] = evidence or {}
    if not runtime_evidence:
        result["reason"] = "NOT_RUN"
        return result
    required = ("source_path", "filesystem_type", "device_or_mount_identity", "observation_window_id", "observation_start", "observation_end")
    if not isinstance(evidence, dict) or any(not evidence.get(field) for field in required):
        result["reason"] = "IDENTITY_TUPLE_INCOMPLETE"
        return result
    if evidence.get("source_path") != "/dev/sda2" or evidence.get("filesystem_type") != "Btrfs" or evidence.get("matched_identity") is not True:
        result["reason"] = "IDENTITY_MISMATCH"
        return result
    result["STATUS"] = "MATCHED"
    result["BTRFS"] = "MATCHED"
    result["reason"] = "MATCHED_IDENTITY_SAME_WINDOW"
    return result


def restore_contract_snapshot() -> Dict[str, Any]:
    return {
        "RESTORE_PLANNED": True,
        "RESTORE_EXECUTED": False,
        "RESTORE_VALIDATED": False,
        "STATUS": "NOT_EXECUTED",
        "FAILURE_STATE": "ABORT_RESTORE",
    }


def restore_contract_transition(contract: Dict[str, Any], event: str, success: bool = True) -> Dict[str, Any]:
    result = dict(contract)
    if event == "EXECUTE":
        result["RESTORE_EXECUTED"] = True
        result["STATUS"] = "RESTORE_IN_PROGRESS"
    elif event == "VALIDATE" and success:
        result["RESTORE_VALIDATED"] = True
        result["STATUS"] = "RESTORE_VALIDATED"
    elif event == "VALIDATE" and not success:
        result["STATUS"] = "ABORT_RESTORE"
    elif event == "FAIL":
        result["STATUS"] = "ABORT_RESTORE"
    elif event == "NOT_NEEDED":
        result["STATUS"] = "RESTORE_NOT_NEEDED"
    return result


def runtime_contract_snapshot(materialized: bool = False, validated: bool = False) -> Dict[str, Any]:
    return {
        "RUNTIME_DESIGNED": True,
        "RUNTIME_MATERIALIZED": bool(materialized),
        "RUNTIME_VALIDATED": bool(validated),
        "namespace": {"path": str(STATE_ROOT), "version": RUNTIME_NAMESPACE_VERSION, "status": "DESIGNED" if not materialized else "MATERIALIZED"},
        "runtime_root": {"path": str(STATE_ROOT), "status": "NOT_MATERIALIZED" if not materialized else "MATERIALIZED"},
        "CURRENT": {"path": str(CURRENT_POINTER), "status": "NOT_MATERIALIZED" if not materialized else "PENDING_READBACK"},
        "state": {"schema_version": RUNTIME_SCHEMA_VERSION, "status": "NOT_MATERIALIZED" if not materialized else "PENDING_READBACK"},
        "JSONL": {"path": str(OBSERVER_JSONL), "status": "NOT_MATERIALIZED" if not materialized else "PENDING_READBACK"},
        "TTY": {"required": True, "status": "NOT_VERIFIED"},
        "RUN-C1": {"required": True, "status": "ABSENT"},
        "sudo": {"required": True, "status": "NOT_VERIFIED"},
    }


def _precheck_spec(
    source: str,
    required_state: str,
    fail_condition: str,
    abort_condition: str,
    evidence: str,
    restore_impact: str,
) -> Dict[str, Any]:
    return {
        "SOURCE": source,
        "REQUIRED_STATE": required_state,
        "FAIL_CONDITION": fail_condition,
        "ABORT_CONDITION": abort_condition,
        "EVIDENCE": evidence,
        "RESTORE_IMPACT": restore_impact,
    }


PRECHECK_CONTRACT_SPECS: Dict[str, Dict[str, Any]] = {
    "host": _precheck_spec("C1-CODE;P0", "hostname=lex-luthor", "mismatch_or_missing", "NO_GO_PRE", "host_snapshot", "NONE"),
    "kernel": _precheck_spec("C1-CODE;P0", "kernel=7.2.6-201.nobara.fc44.x86_64", "mismatch_or_missing", "NO_GO_PRE", "kernel_snapshot", "NONE"),
    "gpu_identity": _precheck_spec("C1-CODE;C1-DOC", "RX550_identity_and_mappings", "mismatch_or_missing", "NO_GO_PRE", "identity_snapshot", "NONE"),
    "gpu_controls_readable": _precheck_spec("C1-CODE", "controls_readable", "missing_or_unsafe", "NO_GO_PRE", "control_snapshot", "NO_CHANGE_PLANNED"),
    "c1_binary": _precheck_spec("C1-CODE", "binary_exists_executable_hash", "missing_or_hash_mismatch", "NO_GO_PRE", "file_and_hash", "NONE"),
    "provenance_hashes": _precheck_spec("C1-CODE;C1-SIDE", "expected_hashes", "mismatch_or_missing", "NO_GO_PRE", "provenance_manifest", "NONE"),
    "build_id": _precheck_spec("C1-CODE;C1-SIDE", "expected_build_id", "mismatch_or_missing", "NO_GO_PRE", "build_id", "NONE"),
    "runtime_tmpfs": _precheck_spec("C1-CODE", "runtime_root_tmpfs", "missing_or_wrong_fs", "NO_GO_PRE", "mount_and_mode", "NO_CREATE_RUNTIME"),
    "jsonl_collision": _precheck_spec("C1-CODE", "observer_jsonl_absent_before_run", "exists_or_unexpected_path", "ABORT_PRE", "path_and_collision", "NO_CREATE_RUNTIME"),
    "dstate": _precheck_spec("C1-DOC;C1-CODE", "D_STATE_COUNT=0", "positive_missing_or_interrupted", "NO_GO_PRE_OR_ABORT_GUARD", "dstate_samples", "RESTORE_TOUCHED_UNITS_IF_GUARD"),
    "procs_blocked": _precheck_spec("C1-CODE", "procs_blocked=0", "positive_or_missing", "NO_GO_PRE_OR_ABORT_GUARD", "proc_stat_samples", "RESTORE_TOUCHED_UNITS_IF_GUARD"),
    "io_guard_criterion": _precheck_spec("C1-CODE;C1-SIDE", "PSI_some_avg10<=10_and_full_avg10<=10", "above_10_nan_missing_or_uncomparable", "NO_GO_PRE_OR_ABORT_GUARD", "psi_samples", "RESTORE_TOUCHED_UNITS_IF_GUARD"),
    "no_existing_c1": _precheck_spec("C1-CODE", "no_C1_or_observer_collision", "collision", "ABORT_PRE", "process_scan", "NONE"),
    "no_incomplete_runtime_state": _precheck_spec("C1-CODE", "no_incomplete_v2_state", "incomplete_or_unknown", "ABORT_RUNTIME", "current_state", "NO_CREATE_RUNTIME"),
    "no_orphan_runtime_runs": _precheck_spec("C1-CODE", "no_orphan_v2_runs", "orphan_or_unsafe", "ABORT_RUNTIME", "runtime_inventory", "NO_CREATE_RUNTIME"),
    "historical_legacy_runtime": _precheck_spec("C1-CODE;C1-SIDE", "legacy_allowlist_preserved", "blocking_or_unrecognized", "ABORT_RUNTIME", "legacy_inventory", "NO_DELETE_LEGACY"),
    "units_readable": _precheck_spec("P0;C1-CODE", "unit_states_safe_and_pre_accounted", "unsafe_missing_or_unresolved_writer", "NO_GO_PRE_OR_ABORT_GUARD", "unit_readback", "RESTORE_TOUCHED_UNITS"),
    "ownership": _precheck_spec("P0;C1-CODE;DESIGN", "OWNERSHIP=FULL_requires_runtime_proof", "partial_unknown_or_static_only", "NO_GO_PRE_OR_ABORT_GUARD", "ownership_contract_and_proof", "NO_PROCESS_ACTION"),
}


def build_precheck_contracts(checks: Dict[str, Dict[str, Any]]) -> Dict[str, Dict[str, Any]]:
    contracts: Dict[str, Dict[str, Any]] = {}
    names = set(PRECHECK_CONTRACT_SPECS) | set(checks)
    for name in sorted(names):
        spec = PRECHECK_CONTRACT_SPECS.get(name, _precheck_spec("DESIGN", "defined_by_existing_check", "status_not_pass", "NO_GO_PRE", "check_detail", "UNKNOWN"))
        item = checks.get(name, {})
        contracts[name] = {
            "CHECK": name,
            "SOURCE": spec["SOURCE"],
            "REQUIRED_STATE": spec["REQUIRED_STATE"],
            "FAIL_CONDITION": spec["FAIL_CONDITION"],
            "ABORT_CONDITION": spec["ABORT_CONDITION"],
            "EVIDENCE": {"status": item.get("status", CONTRACT_UNKNOWN), "detail": item.get("detail")},
            "RESTORE_IMPACT": spec["RESTORE_IMPACT"],
            "STATUS": item.get("status", CONTRACT_UNKNOWN),
        }
    return contracts


def _fallback_spec(
    failure: str,
    pre_classification: str,
    guard_classification: str,
    action: str,
    evidence: str,
    next_pre: str,
    next_guard: str,
) -> Dict[str, Any]:
    return {
        "FAILURE": failure,
        "PRE_CLASSIFICATION": pre_classification,
        "GUARD_CLASSIFICATION": guard_classification,
        "ACTION": action,
        "EVIDENCE": evidence,
        "NEXT_PRE": next_pre,
        "NEXT_GUARD": next_guard,
    }


FALLBACK_CONTRACT_CASES: Dict[str, Dict[str, Any]] = {
    "OWNERSHIP": _fallback_spec("OWNERSHIP", "BLOCKED", "BLOCKED", "no_isolation", "ownership_contract", "NO_GO", "NO_GO"),
    "D_STATE": _fallback_spec("D_STATE", "NO_GO", "ABORT", "no_C1", "dstate_samples", "NO_GO", "RESTORE_PENDING"),
    "PSI": _fallback_spec("PSI", "NO_GO", "ABORT", "no_C1", "psi_samples", "NO_GO", "RESTORE_PENDING"),
    "I_O_GUARD": _fallback_spec("I_O_GUARD", "NO_GO", "ABORT", "no_C1", "io_samples", "NO_GO", "RESTORE_PENDING"),
    "SDA_ACTIVITY": _fallback_spec("SDA_ACTIVITY", "NO_GO", "ABORT", "no_C1_no_sda_touch", "diskstats_psi_actor", "NO_GO", "RESTORE_PENDING"),
    "RUNTIME_ABSENT": _fallback_spec("RUNTIME_ABSENT", "NO_GO", "ABORT", "no_silent_creation", "runtime_contract", "NO_GO_RUNTIME", "ABORT_RUNTIME"),
    "TTY": _fallback_spec("TTY", "NO_GO", "ABORT", "no_auth_bypass", "tty_evidence", "NO_GO", "ABORT_PRE"),
    "RUN_C1": _fallback_spec("RUN_C1", "NO_GO", "ABORT", "no_C1", "confirmation_evidence", "NO_GO", "ABORT_PRE"),
    "SUDO": _fallback_spec("SUDO", "NO_GO", "ABORT", "no_unit_stop", "auth_evidence", "NO_GO_AUTH", "ABORT_C1"),
    "PM": _fallback_spec("PM", "NO_GO", "ABORT", "no_PM_change", "pm_readback", "NO_GO", "RESTORE_PENDING"),
    "GOVERNOR": _fallback_spec("GOVERNOR", "NO_GO", "ABORT", "no_tuning", "governor_readback", "NO_GO", "RESTORE_PENDING"),
    "IRQ": _fallback_spec("IRQ", "NO_GO", "ABORT", "no_IRQ_change", "irq_readback", "NO_GO", "RESTORE_PENDING"),
    "SCHEDULER": _fallback_spec("SCHEDULER", "NO_GO", "ABORT", "no_scheduler_change", "scheduler_readback", "NO_GO", "RESTORE_PENDING"),
    "READ_AHEAD": _fallback_spec("READ_AHEAD", "NO_GO", "ABORT", "no_read_ahead_change", "read_ahead_readback", "NO_GO", "RESTORE_PENDING"),
    "BTRFS": _fallback_spec("BTRFS", "NO_GO", "ABORT", "no_probe_or_repair", "btrfs_tuple_window", "NO_GO", "RESTORE_PENDING"),
    "RESTORE_FAILURE": _fallback_spec("RESTORE_FAILURE", "NO_GO", "ABORT", "no_retry_no_continue", "restore_readback", "ABORT_RESTORE", "RESTORE_UNRESOLVED"),
}


def fallback_contracts() -> Dict[str, Dict[str, Any]]:
    return {name: dict(spec) for name, spec in FALLBACK_CONTRACT_CASES.items()}


def classify_fallback(failure: str, phase: str = "PRE", touched: bool = False) -> Dict[str, Any]:
    spec = FALLBACK_CONTRACT_CASES.get(failure)
    if spec is None:
        return {"FAILURE": failure, "CLASSIFICATION": "BLOCKED", "ACTION": "no_implicit_action", "ABORT": True, "RESTORE": "UNKNOWN", "EVIDENCE": "SOURCE=UNKNOWN", "NEXT_STATE": "BLOCKED"}
    is_guard = phase.upper() == "GUARD"
    classification = spec["GUARD_CLASSIFICATION"] if is_guard else spec["PRE_CLASSIFICATION"]
    restore = "RESTORE_REQUIRED" if is_guard and touched and classification == "ABORT" else "NONE"
    return {
        "FAILURE": failure,
        "CLASSIFICATION": classification,
        "ACTION": spec["ACTION"],
        "ABORT": classification in {"ABORT", "BLOCKED"},
        "RESTORE": restore,
        "EVIDENCE": spec["EVIDENCE"],
        "NEXT_STATE": spec["NEXT_GUARD"] if is_guard else spec["NEXT_PRE"],
    }


def evaluate_execution_gate(
    ownership_proof: Dict[str, Any],
    system_gates: Dict[str, Dict[str, Any]],
    btrfs_gate: Dict[str, Any],
) -> Dict[str, Any]:
    blockers: List[str] = []
    if ownership_proof.get("status") != OWNERSHIP_FULL or not ownership_proof.get("full_proof"):
        blockers.append("OWNERSHIP_NOT_FULL")
    pending_gates = [name for name, item in system_gates.items() if item.get("STATUS") != "PASS"]
    if pending_gates:
        blockers.append("SYSTEM_GATES_PENDING:" + ",".join(sorted(pending_gates)))
    if btrfs_gate.get("STATUS") != "MATCHED":
        blockers.append("BTRFS_GATE_NOT_MATCHED")
    return {
        "GO_C1": "NOT_AVAILABLE" if blockers else "AVAILABLE",
        "STATUS": "BLOCKED" if blockers else "READY_FOR_AUTHORIZATION",
        "BLOCKERS": blockers,
        "RUNTIME_VALIDATION": "NO",
    }


IMPLEMENTATION_PROVENANCE: Dict[str, Dict[str, str]] = {
    "REQ-OWNERSHIP-CONTRACT": {"CODE_LOCATION": "OWNERSHIP_CONTRACT/evaluate_ownership_proof", "TEST": "test_ownership_contract_is_static_partial", "DOCUMENTATION": "C1-ISOLATION-DESIGN-v1.0 §2"},
    "REQ-SYSTEM-GATES": {"CODE_LOCATION": "SYSTEM_GATE_CONTRACT/evaluate_system_gate", "TEST": "test_system_gate_contracts_keep_unknown_thresholds", "DOCUMENTATION": "C1-ISOLATION-DESIGN-v1.0 §3"},
    "REQ-BTRFS-GATE": {"CODE_LOCATION": "BTRFS_GATE_CONTRACT/evaluate_btrfs_gate", "TEST": "test_btrfs_gate_is_conflict_without_runtime_evidence", "DOCUMENTATION": "C1-ISOLATION-DESIGN-v1.0 §5"},
    "REQ-RESTORE-STATE": {"CODE_LOCATION": "restore_contract_snapshot/restore_contract_transition", "TEST": "test_restore_contract_separates_executed_and_validated", "DOCUMENTATION": "C1-ISOLATION-DESIGN-v1.0 §6"},
    "REQ-RUNTIME-STATE": {"CODE_LOCATION": "runtime_contract_snapshot", "TEST": "test_runtime_contract_is_not_materialized", "DOCUMENTATION": "C1-ISOLATION-DESIGN-v1.0 §7"},
    "REQ-PRECHECK-CONTRACT": {"CODE_LOCATION": "PRECHECK_CONTRACT_SPECS/build_precheck_contracts", "TEST": "test_precheck_contract_has_all_required_fields", "DOCUMENTATION": "C1-ISOLATION-DESIGN-v1.0 §8"},
    "REQ-FALLBACK": {"CODE_LOCATION": "FALLBACK_CONTRACT_CASES/classify_fallback", "TEST": "test_fallback_contract_distinguishes_no_go_abort_blocked", "DOCUMENTATION": "C1-ISOLATION-DESIGN-v1.0 §9"},
    "REQ-PROVENANCE": {"CODE_LOCATION": "IMPLEMENTATION_PROVENANCE", "TEST": "test_implementation_provenance_is_complete", "DOCUMENTATION": "C1-ISOLATION-DESIGN-v1.0 §12"},
}


def implementation_provenance() -> Dict[str, Dict[str, str]]:
    result: Dict[str, Dict[str, str]] = {}
    for req_id, record in IMPLEMENTATION_PROVENANCE.items():
        item = dict(record)
        item.setdefault("STATUS", "IMPLEMENTED")
        item.setdefault("RUNTIME_STATUS", CONTRACT_PENDING)
        result[req_id] = item
    return result


# Scope is explicit.  A unit is stopped only if its captured PRE ActiveState
# is active/activating/reloading.  No enable/disable/mask/kill operation exists.
UNIT_SPECS: Tuple[Dict[str, str], ...] = (
    {"scope": "system", "unit": "system-autopilot.timer", "kind": "timer"},
    {"scope": "system", "unit": "system-autopilot.service", "kind": "service"},
    {"scope": "system", "unit": "sys-tuned.timer", "kind": "timer"},
    {"scope": "system", "unit": "sys-tuned.service", "kind": "service"},
    {"scope": "system", "unit": "kalm-gpu.service", "kind": "service"},
    {"scope": "system", "unit": "kalm.service", "kind": "service"},
    {"scope": "system", "unit": "irqbalance.service", "kind": "service"},
    {"scope": "system", "unit": "kalm-lite.service", "kind": "service"},
    {"scope": "system", "unit": "sysstat-collect.timer", "kind": "timer"},
    {"scope": "system", "unit": "sysstat-collect.service", "kind": "service"},
    {"scope": "user", "unit": "kde-baloo.service", "kind": "service"},
)

GPU_CONTROL_PATHS = {
    "power1_cap": "/sys/class/drm/card1/device/hwmon/hwmon2/power1_cap",
    "power_dpm_force_performance_level": "/sys/class/drm/card1/device/power_dpm_force_performance_level",
    "power_control": "/sys/class/drm/card1/device/power/control",
    "runtime_status": "/sys/class/drm/card1/device/power/runtime_status",
    "gpu_busy_percent": "/sys/class/drm/card1/device/gpu_busy_percent",
    "mem_busy_percent": "/sys/class/drm/card1/device/mem_busy_percent",
    "sclk": "/sys/class/drm/card1/device/pp_dpm_sclk",
    "mclk": "/sys/class/drm/card1/device/pp_dpm_mclk",
    "power1_input": "/sys/class/drm/card1/device/hwmon/hwmon2/power1_input",
    "temp1_input": "/sys/class/drm/card1/device/hwmon/hwmon2/temp1_input",
}

INTERRUPTED = False


class AutomatorError(RuntimeError):
    """A protocol or execution error with a controlled abort path."""


class InterruptedRun(AutomatorError):
    """Raised at a safe checkpoint after SIGINT/SIGTERM."""


def now_iso() -> str:
    return dt.datetime.now().astimezone().isoformat(timespec="seconds")


def monotonic() -> float:
    return time.monotonic()


def sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as stream:
        for block in iter(lambda: stream.read(1024 * 1024), b""):
            digest.update(block)
    return digest.hexdigest()


def read_text(path: Path) -> str:
    return path.read_text(encoding="utf-8", errors="replace")


def read_optional(path: Path) -> Dict[str, Any]:
    try:
        return {"status": "OK", "value": read_text(path)}
    except Exception as exc:  # noqa: BLE001 - evidence must retain failure type
        return {"status": "NOT_AVAILABLE", "error": type(exc).__name__, "path": str(path)}


def parse_kv(text: str) -> Dict[str, str]:
    result: Dict[str, str] = {}
    for line in text.splitlines():
        if "=" in line:
            key, value = line.split("=", 1)
            result[key.strip()] = value.strip()
    return result


def run_read_command(
    argv: Sequence[str],
    timeout: int = 10,
    env: Optional[Dict[str, str]] = None,
) -> Dict[str, Any]:
    try:
        result = subprocess.run(
            list(argv),
            capture_output=True,
            text=True,
            timeout=timeout,
            check=False,
            env=env,
        )
        return {
            "argv": list(argv),
            "returncode": result.returncode,
            "stdout": result.stdout,
            "stderr": result.stderr,
        }
    except Exception as exc:  # noqa: BLE001
        return {
            "argv": list(argv),
            "returncode": None,
            "stdout": "",
            "stderr": "",
            "error": f"{type(exc).__name__}: {exc}",
        }


def command_text(argv: Sequence[str]) -> str:
    return " ".join(shlex.quote(str(item)) for item in argv)


def unit_show_argv(scope: str, unit: str) -> List[str]:
    prefix = ["/usr/bin/systemctl"]
    if scope == "user":
        prefix.append("--user")
    return prefix + [
        "show",
        unit,
        "-p",
        "LoadState",
        "-p",
        "ActiveState",
        "-p",
        "SubState",
        "-p",
        "MainPID",
        "-p",
        "NRestarts",
        "-p",
        "UnitFileState",
        "-p",
        "Result",
        "-p",
        "LastTriggerUSec",
        "-p",
        "NextElapseUSecRealtime",
        "-p",
        "ExecMainStartTimestamp",
        "-p",
        "ExecMainExitTimestamp",
        "--no-pager",
    ]


def unit_state(scope: str, unit: str) -> Dict[str, Any]:
    argv = unit_show_argv(scope, unit)
    result = run_read_command(argv)
    parsed = parse_kv(result.get("stdout", ""))
    parsed["_returncode"] = result.get("returncode")
    parsed["_stderr"] = result.get("stderr", "")
    parsed["_argv"] = argv
    parsed["_valid"] = result.get("returncode") == 0 and parsed.get("ActiveState") in {
        "active", "activating", "reloading", "inactive", "failed", "deactivating", "maintenance"
    }
    return parsed


def unit_is_active(state: Dict[str, Any]) -> bool:
    return state.get("_valid") is True and state.get("ActiveState") in {"active", "activating", "reloading"}


def unit_expected_inactive(state: Dict[str, Any]) -> bool:
    return state.get("_valid") is True and state.get("ActiveState") in {"inactive", "failed"}


def unit_unsafe(state: Dict[str, Any]) -> bool:
    return state.get("_valid") is not True or state.get("ActiveState") in {"deactivating", "maintenance"}


def cgroup(pid: int) -> str:
    try:
        return read_text(Path(f"/proc/{pid}/cgroup")).replace("\n", ";")
    except Exception as exc:  # noqa: BLE001
        return f"NOT_AVAILABLE:{type(exc).__name__}"


def dstate_snapshot() -> Dict[str, Any]:
    entries: List[Dict[str, Any]] = []
    incomplete: List[Dict[str, Any]] = []
    for proc_dir in Path("/proc").iterdir():
        if not proc_dir.name.isdigit():
            continue
        pid = int(proc_dir.name)
        try:
            stat_text = read_text(proc_dir / "stat")
            tail = stat_text[stat_text.rfind(")") + 2 :].split()
            state = tail[0]
            if not state.startswith("D"):
                continue
            entries.append(
                {
                    "pid": pid,
                    "comm": read_text(proc_dir / "comm").strip(),
                    "state": state,
                    "ppid": tail[1],
                    "wchan": read_optional(proc_dir / "wchan"),
                    "cgroup": cgroup(pid),
                }
            )
        except Exception as exc:  # noqa: BLE001 - missing evidence fails closed
            incomplete.append({"pid": pid, "error": f"{type(exc).__name__}: {exc}"})
    return {"count": len(entries), "complete": not incomplete, "incomplete": incomplete, "processes": entries}


def procs_snapshot() -> Dict[str, Any]:
    result: Dict[str, Any] = {"procs_running": None, "procs_blocked": None}
    try:
        for line in read_text(Path("/proc/stat")).splitlines():
            fields = line.split()
            if fields and fields[0] in {"procs_running", "procs_blocked"}:
                result[fields[0]] = int(fields[1])
    except Exception as exc:  # noqa: BLE001
        result["error"] = f"{type(exc).__name__}: {exc}"
    return result


def parse_pressure(path: Path) -> Dict[str, Dict[str, float]]:
    result: Dict[str, Dict[str, float]] = {}
    try:
        for line in read_text(path).splitlines():
            fields = line.split()
            if not fields:
                continue
            values: Dict[str, float] = {}
            for item in fields[1:]:
                if "=" in item:
                    key, value = item.split("=", 1)
                    try:
                        values[key] = float(value)
                    except ValueError:
                        values[key] = float("nan")
            result[fields[0]] = values
    except Exception as exc:  # noqa: BLE001
        return {"_error": {"type": type(exc).__name__, "message": str(exc)}}
    return result


def pressure_snapshot() -> Dict[str, Any]:
    return {
        "cpu": parse_pressure(Path("/proc/pressure/cpu")),
        "io": parse_pressure(Path("/proc/pressure/io")),
        "memory": parse_pressure(Path("/proc/pressure/memory")),
    }


def diskstats_snapshot() -> Dict[str, Any]:
    result: Dict[str, Any] = {"status": "NOT_AVAILABLE", "row": None}
    try:
        for line in read_text(Path("/proc/diskstats")).splitlines():
            fields = line.split()
            if len(fields) >= 14 and fields[0:2] == ["8", "0"]:
                result = {
                    "status": "OK",
                    "row": {
                        "reads_completed": int(fields[3]),
                        "sectors_read": int(fields[5]),
                        "writes_completed": int(fields[7]),
                        "sectors_written": int(fields[9]),
                        "io_ticks": int(fields[12]),
                        "weighted_io_time_ms": int(fields[13]),
                    },
                }
                break
    except Exception as exc:  # noqa: BLE001
        result["error"] = f"{type(exc).__name__}: {exc}"
    return result


def gpu_identity() -> Dict[str, Any]:
    bdf = Path("/sys/bus/pci/devices") / EXPECTED_BDF
    card_device = Path("/sys/class/drm/card1/device")
    render_node = card_device / "drm/renderD129"
    hwmon = Path(EXPECTED_HWMON)
    paths = {
        "vendor": bdf / "vendor",
        "device": bdf / "device",
        "driver": bdf / "driver",
    }
    values: Dict[str, Any] = {"bdf": EXPECTED_BDF}
    for key, path in paths.items():
        try:
            values[key] = path.resolve().name if key == "driver" else read_text(path).strip()
        except Exception as exc:  # noqa: BLE001
            values[key] = f"NOT_AVAILABLE:{type(exc).__name__}"
    values["card1_exists"] = Path("/sys/class/drm/card1").exists()
    values["renderD129_exists"] = render_node.exists()
    values["hwmon_exists"] = hwmon.is_dir()
    try:
        expected_resolved = bdf.resolve()
        values["card1_device"] = str(card_device.resolve())
        values["card1_maps_expected_bdf"] = card_device.resolve() == expected_resolved
        values["renderD129_device"] = str(render_node.resolve())
        values["renderD129_maps_expected_bdf"] = render_node.resolve() == expected_resolved / "drm" / "renderD129"
        values["hwmon_device"] = str(hwmon.resolve().parent.parent)
        values["hwmon_maps_expected_bdf"] = hwmon.resolve().parent.parent == expected_resolved
    except Exception as exc:  # noqa: BLE001
        values["mapping_error"] = f"{type(exc).__name__}: {exc}"
        values["card1_maps_expected_bdf"] = False
        values["renderD129_maps_expected_bdf"] = False
        values["hwmon_maps_expected_bdf"] = False
    return values


def active_dpm_line(path: Path) -> str:
    try:
        for line in read_text(path).splitlines():
            if "*" in line:
                return line.strip()
    except Exception as exc:  # noqa: BLE001
        return f"NOT_AVAILABLE:{type(exc).__name__}"
    return "NOT_AVAILABLE"


def gpu_snapshot() -> Dict[str, Any]:
    values: Dict[str, Any] = {"identity": gpu_identity(), "controls": {}, "raw": {}}
    for name, path_string in GPU_CONTROL_PATHS.items():
        path = Path(path_string)
        raw = read_optional(path)
        values["raw"][name] = raw
        if name in {"sclk", "mclk"} and raw.get("status") == "OK":
            values["controls"][name] = active_dpm_line(path)
        else:
            values["controls"][name] = raw.get("value", raw.get("status"))
    return values


def git_head() -> Dict[str, Any]:
    env = os.environ.copy()
    env["GIT_OPTIONAL_LOCKS"] = "0"
    result = run_read_command(
        ["/usr/bin/git", "-C", str(PROJECT), "rev-parse", "HEAD"], env=env
    )
    return {
        "status": "OK" if result.get("returncode") == 0 else "NOT_AVAILABLE",
        "value": result.get("stdout", "").strip() if result.get("returncode") == 0 else None,
        "stderr": result.get("stderr", ""),
    }


def provenance_snapshot() -> Dict[str, Any]:
    files = {
        "main-graphics": C1_BINARY,
        "src/graphics.cpp": WORKLOAD_DIR / "src/graphics.cpp",
        "c1_observer.py": OBSERVER,
        "src/vertex.vert": WORKLOAD_DIR / "src/vertex.vert",
        "src/fragment.frag": WORKLOAD_DIR / "src/fragment.frag",
        "src/fragment2.frag": WORKLOAD_DIR / "src/fragment2.frag",
        "Makefile": WORKLOAD_DIR / "Makefile",
    }
    hashes: Dict[str, Any] = {}
    for name, path in files.items():
        try:
            hashes[name] = {"status": "OK", "sha256": sha256_file(path), "path": str(path)}
        except Exception as exc:  # noqa: BLE001
            hashes[name] = {"status": "NOT_AVAILABLE", "path": str(path), "error": type(exc).__name__}
    build = run_read_command(["/usr/bin/readelf", "-n", str(C1_BINARY)])
    build_match = re.search(r"(?:Build ID|Compilación):\s*([0-9a-fA-F]+)", build.get("stdout", ""))
    return {
        "hashes": hashes,
        "git_head": git_head(),
        "build_id": build_match.group(1) if build_match else None,
        "build_id_expected": EXPECTED_BUILD_ID,
        "compiler": EXPECTED_COMPILER,
        "cxxflags": EXPECTED_CXXFLAGS,
    }


def runtime_state_path() -> Optional[Path]:
    if not os.path.lexists(CURRENT_POINTER):
        return None
    if CURRENT_POINTER.is_symlink():
        return None
    try:
        run_id = read_text(CURRENT_POINTER).strip()
    except Exception:
        return None
    if not re.fullmatch(r"[0-9]{8}T[0-9]{6}Z-[0-9]+", run_id):
        return None
    runs_root = STATE_ROOT / "runs"
    run_dir = runs_root / run_id
    if run_dir.is_symlink() or not run_dir.is_dir():
        return None
    state_path = run_dir / "state.json"
    if state_path.is_symlink() or not state_path.is_file():
        return None
    try:
        if os.path.commonpath([str(STATE_ROOT.resolve()), str(state_path.resolve())]) != str(STATE_ROOT.resolve()):
            return None
    except ValueError:
        return None
    return state_path


def validate_state_summary(summary: Any, label: str, state: Dict[str, Any]) -> Optional[str]:
    if not isinstance(summary, dict):
        return f"invalid {label} summary"
    required = (
        "runtime_namespace",
        "runtime_schema_version",
        "automator_version",
        "automator_sha256",
        "phase",
        "terminal",
        "result",
        "guard",
        "c1",
        "restore",
        "post",
        "error",
        "finished_at",
    )
    for key in required:
        if key not in summary:
            return f"missing {label} summary field={key}"
    for key in ("runtime_namespace", "runtime_schema_version", "automator_version", "automator_sha256"):
        if summary.get(key) != state.get(key):
            return f"{label} summary mismatch field={key}"
    if not isinstance(summary.get("phase"), str) or summary.get("phase") not in ALLOWED_PHASES:
        return f"invalid {label} summary phase"
    if not isinstance(summary.get("terminal"), bool) or not isinstance(summary.get("result"), str) or summary.get("result") not in ALLOWED_RESULTS:
        return f"invalid {label} summary terminal/result"
    guard = summary.get("guard")
    if not isinstance(guard, dict):
        return f"invalid {label} summary guard"
    for guard_label in ("T_GUARD", "T_PRE", "T_POST"):
        if not isinstance(guard.get(guard_label), str) or guard.get(guard_label) not in ALLOWED_GUARD_STATUS:
            return f"invalid {label} summary guard={guard_label}"
    c1 = summary.get("c1")
    if not isinstance(c1, dict) or not isinstance(c1.get("status"), str) or not isinstance(c1.get("executed"), bool) or not isinstance(c1.get("formal_pass"), bool) or not isinstance(c1.get("runtime_validated"), bool):
        return f"invalid {label} summary c1"
    if not isinstance(summary.get("restore"), dict) or not isinstance(summary["restore"].get("status"), str):
        return f"invalid {label} summary restore"
    if not isinstance(summary.get("post"), dict) or not isinstance(summary["post"].get("status"), str):
        return f"invalid {label} summary post"
    if label == "initial_state":
        if summary.get("phase") != "PRE_CAPTURED" or summary.get("terminal") is not False or summary.get("result") != "IN_PROGRESS":
            return "noncanonical initial_state summary"
        if any(guard.get(guard_label) != "NOT_RUN" for guard_label in ("T_GUARD", "T_PRE", "T_POST")):
            return "noncanonical initial guard summary"
        if c1.get("status") != "NOT_RUN" or c1.get("executed") is not False or c1.get("formal_pass") is not False or c1.get("runtime_validated") is not False:
            return "noncanonical initial C1 summary"
        if summary["restore"].get("status") != "NOT_RUN" or summary["post"].get("status") != "NOT_RUN":
            return "noncanonical initial restore/post summary"
        if summary.get("error") is not None or summary.get("finished_at") is not None:
            return "noncanonical initial timestamp/error summary"
        return None
    if summary.get("phase") != state.get("phase") or summary.get("terminal") != state.get("terminal") or summary.get("result") != state.get("result"):
        return "final_state summary terminal/result mismatch"
    for section in ("restore", "post"):
        if summary[section].get("status") != state.get(section, {}).get("status"):
            return f"final_state summary {section} mismatch"
    state_c1 = state.get("c1", {})
    for key in ("status", "executed", "formal_pass", "runtime_validated"):
        if c1.get(key) != state_c1.get(key):
            return f"final_state summary c1 mismatch field={key}"
    if summary.get("error") != state.get("error") or summary.get("finished_at") != state.get("finished_at"):
        return "final_state summary timestamp/error mismatch"
    if not isinstance(summary.get("finished_at"), str) or not summary.get("finished_at"):
        return "missing final_state finished_at"
    return None


def validate_state(state: Any) -> Optional[str]:
    if not isinstance(state, dict):
        return "state is not an object"
    if state.get("schema_version") != RUNTIME_SCHEMA_VERSION:
        return f"schema_version={state.get('schema_version')!r}"
    for key in (
        "automator_version",
        "automator_sha256",
        "script_sha256",
        "contract_version",
        "runtime_contract",
        "restore_contract",
        "contract_manifest",
        "runtime_schema_version",
        "runtime_namespace_version",
        "runtime_namespace",
        "parent_namespace",
        "parent_namespace_path",
        "historical_namespace",
        "historical_namespace_path",
        "legacy_reference",
        "runtime_namespace_activated_at",
        "run_created_at",
        "run_id",
        "phase",
        "terminal",
        "result",
        "pre",
        "guard",
        "c1",
        "restore",
        "post",
        "initial_state",
        "final_state",
    ):
        if key not in state:
            return f"missing key={key}"
    if not isinstance(state.get("automator_version"), str) or not state["automator_version"]:
        return "invalid automator_version"
    if not isinstance(state.get("automator_sha256"), str) or not re.fullmatch(r"[0-9a-f]{64}", state["automator_sha256"]):
        return "invalid automator_sha256"
    if state.get("script_sha256") != state.get("automator_sha256"):
        return "script_sha256 mismatch"
    if state.get("contract_version") != CONTRACT_VERSION:
        return "contract_version mismatch"
    runtime_contract = state.get("runtime_contract")
    if not isinstance(runtime_contract, dict) or runtime_contract.get("RUNTIME_DESIGNED") is not True or not isinstance(runtime_contract.get("RUNTIME_MATERIALIZED"), bool) or not isinstance(runtime_contract.get("RUNTIME_VALIDATED"), bool):
        return "invalid runtime_contract"
    restore_contract = state.get("restore_contract")
    if not isinstance(restore_contract, dict) or restore_contract.get("RESTORE_PLANNED") is not True or not isinstance(restore_contract.get("RESTORE_EXECUTED"), bool) or not isinstance(restore_contract.get("RESTORE_VALIDATED"), bool):
        return "invalid restore_contract"
    manifest = state.get("contract_manifest")
    if not isinstance(manifest, dict) or not all(key in manifest for key in ("ownership", "system_gates", "btrfs", "fallback", "provenance")):
        return "invalid contract_manifest"
    if state.get("runtime_schema_version") != RUNTIME_SCHEMA_VERSION:
        return "invalid runtime_schema_version"
    if state.get("runtime_namespace_version") != RUNTIME_NAMESPACE_VERSION:
        return "invalid runtime_namespace_version"
    if state.get("runtime_namespace") != RUNTIME_NAMESPACE:
        return "invalid runtime_namespace"
    if state.get("parent_namespace") != LEGACY_RUNTIME_NAMESPACE or state.get("historical_namespace") != LEGACY_RUNTIME_NAMESPACE:
        return "invalid parent/historical namespace"
    if state.get("parent_namespace_path") != str(LEGACY_STATE_ROOT) or state.get("historical_namespace_path") != str(LEGACY_STATE_ROOT):
        return "invalid parent/historical namespace path"
    if not isinstance(state.get("runtime_namespace_activated_at"), str) or not state["runtime_namespace_activated_at"]:
        return "invalid runtime_namespace_activated_at"
    if not isinstance(state.get("run_created_at"), str) or not state["run_created_at"]:
        return "invalid run_created_at"
    legacy_reference = state.get("legacy_reference")
    expected_legacy = HISTORICAL_LEGACY_RUNS.get(LEGACY_RUN_ID, {})
    if not isinstance(legacy_reference, dict) or legacy_reference.get("namespace") != LEGACY_RUNTIME_NAMESPACE or legacy_reference.get("path") != str(LEGACY_STATE_ROOT) or legacy_reference.get("manifest_id") != LEGACY_MANIFEST_ID or legacy_reference.get("classification") != LEGACY_CLASSIFICATION or legacy_reference.get("blocking") is not False or legacy_reference.get("state_sha256") != expected_legacy.get("state_sha256") or legacy_reference.get("events_sha256") != expected_legacy.get("events_sha256") or legacy_reference.get("current_sha256") != expected_legacy.get("current_sha256"):
        return "invalid legacy_reference"
    if not isinstance(state.get("phase"), str) or state["phase"] not in ALLOWED_PHASES:
        return "invalid phase"
    if not isinstance(state.get("terminal"), bool):
        return "invalid terminal"
    if not isinstance(state.get("result"), str) or state["result"] not in ALLOWED_RESULTS:
        return "invalid result"
    if not isinstance(state.get("initial_state"), dict):
        return "invalid initial_state"
    summary_error = validate_state_summary(state["initial_state"], "initial_state", state)
    if summary_error:
        return summary_error
    if state.get("terminal") and not isinstance(state.get("final_state"), dict):
        return "missing final_state for terminal run"
    if not state.get("terminal") and state.get("final_state") is not None:
        return "unexpected final_state for nonterminal run"
    if state.get("terminal"):
        summary_error = validate_state_summary(state["final_state"], "final_state", state)
        if summary_error:
            return summary_error
    if not isinstance(state.get("events"), list):
        return "invalid events"
    if not isinstance(state.get("actions"), list) or not isinstance(state.get("units"), dict) or not isinstance(state.get("planned"), dict):
        return "invalid actions/units/planned"
    if not isinstance(state.get("guard"), dict) or not isinstance(state.get("post"), dict):
        return "invalid guard/post object"
    for label in ("T_GUARD", "T_PRE", "T_POST"):
        if label not in state["guard"]:
            return f"missing guard window={label}"
        item = state["guard"][label]
        if not isinstance(item, dict):
            return f"invalid guard window={label}"
        missing = [field for field in GUARD_SCHEMA_FIELDS if field not in item]
        if missing:
            return f"missing guard fields={label}:{','.join(missing)}"
        status = item["status"]
        if not isinstance(status, str) or status not in ALLOWED_GUARD_STATUS:
            return f"invalid guard status={label}"
        reason = item["reason"]
        if reason is not None and not isinstance(reason, str):
            return f"invalid guard reason={label}"
        sample_count = item["sample_count"]
        if isinstance(sample_count, bool) or not isinstance(sample_count, int) or sample_count < 0:
            return f"invalid guard sample_count={label}"
        elapsed_seconds = item["elapsed_seconds"]
        try:
            finite_elapsed = math.isfinite(elapsed_seconds)
        except (TypeError, ValueError, OverflowError):
            finite_elapsed = False
        if (
            isinstance(elapsed_seconds, bool)
            or not isinstance(elapsed_seconds, (int, float))
            or not finite_elapsed
            or elapsed_seconds < 0
        ):
            return f"invalid guard elapsed_seconds={label}"
        log = item["log"]
        if log is not None and not isinstance(log, str):
            return f"invalid guard log={label}"
        if status == "NOT_RUN" and (
            reason is not None or sample_count != 0 or elapsed_seconds != 0 or log is not None
        ):
            return f"invalid NOT_RUN guard values={label}"
        if status != "NOT_RUN" and log is None:
            return f"missing guard log={label}"
    for key in ("pre", "restore", "c1"):
        if not isinstance(state.get(key), dict):
            return f"invalid object={key}"
    if not isinstance(state["pre"].get("ok"), bool) or not isinstance(state["pre"].get("units"), dict) or not isinstance(state["pre"].get("checks"), dict):
        return "invalid pre object"
    if not isinstance(state["restore"].get("status"), str):
        return "invalid restore status"
    if not isinstance(state["c1"].get("status"), str) or not isinstance(state["c1"].get("executed"), bool) or not isinstance(state["c1"].get("formal_pass"), bool):
        return "invalid c1 object"
    if not isinstance(state.get("run_id"), str) or not re.fullmatch(r"[0-9]{8}T[0-9]{6}Z-[0-9]+", state["run_id"]):
        return "invalid run_id"
    return None


def validate_active_writer_compat(state: Any) -> Optional[str]:
    if not isinstance(state, dict):
        return "state is not an object"
    if state.get("automator_version") != VERSION:
        return "ACTIVE_RUNTIME_WRITER_MISMATCH: automator_version"
    try:
        current_hash = sha256_file(Path(__file__).resolve())
    except Exception as exc:  # noqa: BLE001 - compatibility failure must be visible
        return f"ACTIVE_RUNTIME_WRITER_MISMATCH: {type(exc).__name__}"
    if state.get("automator_sha256") != current_hash or state.get("script_sha256") != current_hash:
        return "ACTIVE_RUNTIME_WRITER_MISMATCH: automator_sha256"
    return None


def legacy_state_matches_allowlist(state: Any, events: List[Dict[str, Any]], run_id: str) -> bool:
    """Validate only the known pre-fix artifact shape, never the new schema."""
    if not isinstance(state, dict) or not isinstance(events, list):
        return False
    if state.get("schema_version") != 1 or state.get("automator_version") != "1.0.0":
        return False
    if state.get("run_id") != run_id or state.get("phase") != "ISOLATING":
        return False
    if state.get("terminal") is not True or state.get("result") != "ABORTED_FAILURE_RESTORED":
        return False
    if "TypeError: update_state() got multiple values for argument 'state'" not in str(state.get("error")):
        return False
    if state.get("actions") != [] or state.get("restore", {}).get("status") != "RESTORE_NOT_NEEDED":
        return False
    if state.get("restore", {}).get("attempted_units") != []:
        return False
    c1 = state.get("c1", {})
    if c1.get("executed") is not False or c1.get("formal_pass") is not False:
        return False
    if c1.get("status") != "NOT_RUN" or c1.get("observer_jsonl") is not None:
        return False
    if state.get("post", {}).get("status") != "POST_CONFLICT":
        return False
    if state.get("pre", {}).get("ok") is not True:
        return False
    guard = state.get("guard")
    if not isinstance(guard, dict) or guard.get("status") != "NOT_RUN":
        return False
    if any(guard.get(label) != {} for label in ("T_GUARD", "T_PRE", "T_POST")):
        return False
    if state.get("events") != events:
        return False
    event_names = {str(event.get("event")) for event in events if isinstance(event, dict)}
    forbidden = {"unit_pre", "unit_stop_requested", "unit_isolated", "c1_start", "c1_spawn", "c1_end"}
    return not bool(event_names & forbidden) and "finalize" in event_names


def legacy_runtime_inventory() -> Dict[str, Any]:
    """Read-only, strict inventory of the preserved pre-fix namespace."""
    result: Dict[str, Any] = {
        "namespace": LEGACY_RUNTIME_NAMESPACE,
        "path": str(LEGACY_STATE_ROOT),
        "status": "ABSENT",
        "classification": "NO_LEGACY_RUNTIME",
        "legacy_schema_status": "NOT_APPLICABLE",
        "manifest_id": LEGACY_MANIFEST_ID,
        "preserved": "NOT_APPLICABLE",
        "active_namespace": False,
        "blocking": False,
        "runs": [],
    }
    if not os.path.lexists(LEGACY_STATE_ROOT):
        return result
    try:
        if LEGACY_STATE_ROOT.is_symlink() or not LEGACY_STATE_ROOT.is_dir():
            raise AutomatorError("legacy runtime root is not a real directory")
        st = LEGACY_STATE_ROOT.stat()
        if st.st_uid != UID or (st.st_mode & 0o777) != 0o700:
            raise AutomatorError("legacy runtime root ownership/permissions are not private")
        root_entries = {entry.name for entry in LEGACY_STATE_ROOT.iterdir()}
        if root_entries != LEGACY_ROOT_ENTRIES:
            raise AutomatorError(f"legacy root entry mismatch: {sorted(root_entries)!r}")
        lock_file = LEGACY_STATE_ROOT / ".lock"
        if lock_file.is_symlink() or not lock_file.is_file() or lock_file.stat().st_uid != UID or (lock_file.stat().st_mode & 0o777) != 0o600:
            raise AutomatorError("legacy lock is not a private regular file")
        runs_root = LEGACY_STATE_ROOT / "runs"
        if not os.path.lexists(runs_root):
            if os.path.lexists(LEGACY_STATE_ROOT / "CURRENT"):
                raise AutomatorError("legacy CURRENT exists without runs directory")
            return result
        if runs_root.is_symlink() or not runs_root.is_dir():
            raise AutomatorError("legacy runs path is not a real directory")
        rst = runs_root.stat()
        if rst.st_uid != UID or (rst.st_mode & 0o777) != 0o700:
            raise AutomatorError("legacy runs ownership/permissions are not private")
        current = LEGACY_STATE_ROOT / "CURRENT"
        if current.is_symlink() or not current.is_file() or current.stat().st_uid != UID or (current.stat().st_mode & 0o777) != 0o600:
            raise AutomatorError("legacy CURRENT is not a private regular file")
        expected_current = HISTORICAL_LEGACY_RUNS[LEGACY_RUN_ID]["current_sha256"]
        if read_text(current) != LEGACY_RUN_ID + "\n" or sha256_file(current) != expected_current:
            raise AutomatorError("legacy CURRENT content/hash mismatch")
        children = list(runs_root.iterdir())
        actual_names = {child.name for child in children}
        expected_names = set(HISTORICAL_LEGACY_RUNS)
        if actual_names != expected_names:
            raise AutomatorError(f"legacy run set mismatch: {sorted(actual_names)!r}")
        for child in children:
            run_id = child.name
            expected = HISTORICAL_LEGACY_RUNS[run_id]
            if child.is_symlink() or not child.is_dir():
                raise AutomatorError(f"legacy run is not a real directory: {run_id}")
            cst = child.stat()
            if cst.st_uid != UID or (cst.st_mode & 0o777) != 0o700:
                raise AutomatorError(f"legacy run ownership/permissions are not private: {run_id}")
            run_entries = {entry.name for entry in child.iterdir()}
            if run_entries != LEGACY_RUN_ENTRIES:
                raise AutomatorError(f"legacy run entry mismatch: {run_id}:{sorted(run_entries)!r}")
            for directory_name in ("tmp", "cache"):
                directory = child / directory_name
                if directory.is_symlink() or not directory.is_dir() or directory.stat().st_uid != UID or (directory.stat().st_mode & 0o777) != 0o700:
                    raise AutomatorError(f"legacy {directory_name} is not a private directory: {run_id}")
            state_file = child / "state.json"
            events_file = child / "events.jsonl"
            if state_file.is_symlink() or not state_file.is_file() or state_file.stat().st_uid != UID or (state_file.stat().st_mode & 0o777) != 0o600:
                raise AutomatorError(f"legacy state file missing or unsafe: {run_id}")
            if events_file.is_symlink() or not events_file.is_file() or events_file.stat().st_uid != UID or (events_file.stat().st_mode & 0o777) != 0o644:
                raise AutomatorError(f"legacy events file missing or unsafe: {run_id}")
            state_hash = sha256_file(state_file)
            events_hash = sha256_file(events_file)
            if state_hash != expected["state_sha256"] or events_hash != expected["events_sha256"]:
                raise AutomatorError(f"legacy evidence hash mismatch: {run_id}")
            state = json.loads(read_text(state_file))
            events = [json.loads(line) for line in read_text(events_file).splitlines() if line.strip()]
            if not legacy_state_matches_allowlist(state, events, run_id):
                raise AutomatorError(f"legacy state shape is not allowlisted: {run_id}")
            result["runs"].append(
                {
                    "run_id": run_id,
                    "classification": LEGACY_CLASSIFICATION,
                    "state_sha256": state_hash,
                    "events_sha256": events_hash,
                    "current_sha256": expected_current,
                    "blocking": False,
                }
            )
        result["status"] = LEGACY_CLASSIFICATION
        result["classification"] = LEGACY_CLASSIFICATION
        result["legacy_schema_status"] = "INVALID_LEGACY"
        result["preserved"] = True
        result["blocking"] = False
        return result
    except Exception as exc:  # noqa: BLE001 - unknown legacy data must fail closed
        result["status"] = "LEGACY_RUNTIME_UNRECOGNIZED"
        result["classification"] = "LEGACY_RUNTIME_UNRECOGNIZED"
        result["legacy_schema_status"] = "INVALID_LEGACY_UNRECOGNIZED"
        result["preserved"] = True
        result["blocking"] = True
        result["error"] = f"{type(exc).__name__}: {exc}"
        return result


def load_current_state() -> Tuple[Optional[Path], Optional[Dict[str, Any]]]:
    if os.path.lexists(STATE_ROOT):
        try:
            validate_runtime_layout()
        except AutomatorError as exc:
            return STATE_ROOT, {"_load_error": str(exc)}
    if not os.path.lexists(CURRENT_POINTER):
        return None, None
    path = runtime_state_path()
    if path is None:
        return CURRENT_POINTER, {"_load_error": "CURRENT pointer is malformed, dangling, or points outside state root"}
    try:
        loaded = json.loads(read_text(path))
    except Exception as exc:  # noqa: BLE001
        return path, {"_load_error": f"{type(exc).__name__}: {exc}"}
    error = validate_state(loaded)
    if error is None and loaded.get("run_id") != path.parent.name:
        error = "run_id does not match state directory"
    events_path = path.parent / "events.jsonl"
    if error is None and (events_path.is_symlink() or not events_path.is_file()):
        error = "missing or unsafe events.jsonl"
    if error is None:
        try:
            events = [json.loads(line) for line in read_text(events_path).splitlines() if line.strip()]
            if loaded.get("events") != events:
                error = "state/events.jsonl mismatch"
        except Exception as exc:  # noqa: BLE001
            error = f"events.jsonl: {type(exc).__name__}: {exc}"
    if error:
        return path, {"_load_error": error, "raw_type": type(loaded).__name__}
    compatibility_error = validate_active_writer_compat(loaded)
    if compatibility_error:
        loaded["_compatibility_error"] = compatibility_error
    return path, loaded


def state_is_incomplete(state: Optional[Dict[str, Any]]) -> bool:
    if state is None:
        return False
    if not isinstance(state, dict) or state.get("_load_error") or state.get("_compatibility_error"):
        return True
    if validate_state(state) is not None:
        return True
    if not state.get("terminal", False):
        return True
    if state.get("result") in {"COMPLETED_PARTIAL_OR_CONFLICT", "ABORTED_FAILURE_RESTORE_REQUIRED"}:
        return True
    if state.get("post", {}).get("status") not in {"POST_OK", "NOT_RUN", "MANUAL_INTERVENTION_REQUIRED", "POSTCHECK_FAILED"}:
        return True
    return state.get("restore", {}).get("status") not in {
        "RESTORE_OK",
        "RESTORE_NOT_NEEDED",
        "RESTORE_ABORTED_NO_CHANGES",
    }


def public_runtime_validated(state: Optional[Dict[str, Any]]) -> bool:
    if not isinstance(state, dict) or validate_state(state) is not None or validate_active_writer_compat(state) is not None:
        return False
    guard_ok = all(state.get("guard", {}).get(label, {}).get("status") == "PASS" for label in ("T_GUARD", "T_PRE", "T_POST"))
    c1 = state.get("c1", {})
    formal_checks = c1.get("formal_checks", {})
    pre = state.get("pre", {})
    execution_gate = evaluate_execution_gate(
        pre.get("ownership_proof", {}) if isinstance(pre, dict) else {},
        pre.get("system_gate_contracts", {}) if isinstance(pre, dict) else {},
        pre.get("btrfs_gate", {}) if isinstance(pre, dict) else {},
    )
    return bool(
        state.get("terminal") is True
        and state.get("result") == "COMPLETED_RUNTIME_VALIDATED"
        and c1.get("status") == "EXECUTED"
        and c1.get("executed") is True
        and c1.get("returncode") == 0
        and c1.get("formal_pass") is True
        and isinstance(formal_checks, dict)
        and bool(formal_checks)
        and all(value is True for value in formal_checks.values())
        and c1.get("observer_parse", {}).get("status") == "OK"
        and guard_ok
        and state.get("restore", {}).get("status") in {"RESTORE_OK", "RESTORE_NOT_NEEDED"}
        and state.get("post", {}).get("status") == "POST_OK"
        and execution_gate.get("GO_C1") == "AVAILABLE"
        and state.get("runtime_contract", {}).get("RUNTIME_VALIDATED") is True
    )


def atomic_write_json(path: Path, payload: Dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True, mode=0o700)
    fd, temp_name = tempfile.mkstemp(prefix=f".{path.name}.", dir=str(path.parent), text=True)
    try:
        os.fchmod(fd, 0o600)
        with os.fdopen(fd, "w", encoding="utf-8") as stream:
            json.dump(payload, stream, ensure_ascii=False, sort_keys=True, indent=2)
            stream.write("\n")
            stream.flush()
            os.fsync(stream.fileno())
        os.replace(temp_name, path)
    finally:
        try:
            os.unlink(temp_name)
        except FileNotFoundError:
            pass


def atomic_write_text(path: Path, text: str, mode: int = 0o600) -> None:
    path.parent.mkdir(parents=True, exist_ok=True, mode=0o700)
    fd, temp_name = tempfile.mkstemp(prefix=f".{path.name}.", dir=str(path.parent), text=True)
    try:
        os.fchmod(fd, mode)
        with os.fdopen(fd, "w", encoding="utf-8") as stream:
            stream.write(text)
            stream.flush()
            os.fsync(stream.fileno())
        os.replace(temp_name, path)
    finally:
        try:
            os.unlink(temp_name)
        except FileNotFoundError:
            pass


def append_jsonl(path: Path, payload: Dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True, mode=0o700)
    with path.open("a", encoding="utf-8") as stream:
        stream.write(json.dumps(payload, ensure_ascii=False, sort_keys=True) + "\n")
        stream.flush()
        os.fsync(stream.fileno())


def namespace_paths_separate() -> bool:
    try:
        legacy = os.path.realpath(LEGACY_STATE_ROOT)
        active = os.path.realpath(STATE_ROOT)
        if legacy == active:
            return False
        common = os.path.commonpath([legacy, active])
        return common not in {legacy, active}
    except (OSError, ValueError):
        return False


def fs_type(path: Path) -> Optional[str]:
    target = os.path.realpath(path)
    best_mount = ""
    best_type: Optional[str] = None
    try:
        for line in read_text(Path("/proc/self/mountinfo")).splitlines():
            fields = line.split()
            separator = fields.index("-")
            mount = fields[4].replace("\\040", " ").replace("\\011", "\t").replace("\\134", "\\")
            if target == mount or target.startswith(mount.rstrip("/") + "/"):
                if len(mount) >= len(best_mount):
                    best_mount = mount
                    best_type = fields[separator + 1]
    except Exception:
        return None
    return best_type


def process_scan_for_existing_c1() -> List[Dict[str, Any]]:
    matches: List[Dict[str, Any]] = []
    self_pid = os.getpid()
    for proc_dir in Path("/proc").iterdir():
        if not proc_dir.name.isdigit() or int(proc_dir.name) == self_pid:
            continue
        try:
            cmd = read_text(proc_dir / "cmdline").replace("\x00", " ").strip()
        except Exception:
            continue
        if str(C1_BINARY) in cmd or str(OBSERVER) in cmd:
            matches.append({"pid": int(proc_dir.name), "cmdline": cmd})
    return matches


def finite_number(value: Any) -> bool:
    return isinstance(value, (int, float)) and math.isfinite(float(value))


def io_guard_criterion_ok(some_avg10: Any, full_avg10: Any) -> bool:
    return bool(
        finite_number(some_avg10)
        and finite_number(full_avg10)
        and some_avg10 <= IO_GUARD_AVG10_MAX
        and full_avg10 <= IO_GUARD_AVG10_MAX
    )


def orphan_runtime_runs() -> List[Dict[str, Any]]:
    try:
        validate_runtime_layout()
    except AutomatorError as exc:
        return [{"status": "INVALID", "classification": "ACTIVE_RUNTIME_INVALID", "error": str(exc)}]
    runs_root = STATE_ROOT / "runs"
    if not runs_root.exists():
        return []
    result: List[Dict[str, Any]] = []
    try:
        children = list(runs_root.iterdir())
    except Exception as exc:  # noqa: BLE001
        return [{"status": "INVALID", "classification": "ACTIVE_RUNTIME_INVALID", "error": f"{type(exc).__name__}: {exc}"}]
    for child in children:
        item: Dict[str, Any] = {
            "path": str(child),
            "namespace": RUNTIME_NAMESPACE,
            "classification": ACTIVE_CLASSIFICATION,
        }
        try:
            if child.is_symlink() or not child.is_dir():
                item.update({"status": "INVALID", "reason": "run path is not a real directory"})
                result.append(item)
                continue
            st = child.stat()
            if st.st_uid != UID or (st.st_mode & 0o077):
                item.update({"status": "INVALID", "reason": "run directory ownership/permissions are not private"})
                result.append(item)
                continue
            state_file = child / "state.json"
            events_file = child / "events.jsonl"
            if state_file.is_symlink() or not state_file.is_file() or events_file.is_symlink() or not events_file.is_file():
                item.update({"status": "INCOMPLETE", "reason": "missing or unsafe state/events file"})
                result.append(item)
                continue
            state = json.loads(read_text(state_file))
            events = [json.loads(line) for line in read_text(events_file).splitlines() if line.strip()]
            error = validate_state(state)
            if error is None and state.get("run_id") != child.name:
                error = "run_id does not match run directory"
            if error is None and state.get("events") != events:
                error = "state/events.jsonl mismatch"
            compatibility_error = validate_active_writer_compat(state) if error is None else None
            if compatibility_error:
                item.update({"status": "INCOMPLETE", "classification": "ACTIVE_WRITER_MISMATCH", "reason": compatibility_error})
                result.append(item)
                continue
            if error or state_is_incomplete(state):
                item.update({"status": "INCOMPLETE", "reason": error or "nonterminal/partial state"})
                result.append(item)
        except Exception as exc:  # noqa: BLE001
            item.update({"status": "INVALID", "reason": f"{type(exc).__name__}: {exc}"})
            result.append(item)
    return result


def check_add(checks: Dict[str, Dict[str, Any]], name: str, ok: bool, detail: Any) -> None:
    checks[name] = {"status": "PASS" if ok else "FAIL", "detail": detail}


def collect_precheck() -> Dict[str, Any]:
    checks: Dict[str, Dict[str, Any]] = {}
    hostname = platform.node()
    kernel = platform.release()
    check_add(checks, "host", hostname == EXPECTED_HOST, {"actual": hostname, "expected": EXPECTED_HOST})
    check_add(checks, "kernel", kernel == EXPECTED_KERNEL, {"actual": kernel, "expected": EXPECTED_KERNEL})

    gpu = gpu_snapshot()
    gpu_ok = (
        gpu["identity"].get("vendor") == EXPECTED_VENDOR
        and gpu["identity"].get("device") == EXPECTED_DEVICE
        and gpu["identity"].get("driver") == EXPECTED_DRIVER
        and gpu["identity"].get("card1_exists")
        and gpu["identity"].get("renderD129_exists")
        and gpu["identity"].get("hwmon_exists")
        and gpu["identity"].get("card1_maps_expected_bdf")
        and gpu["identity"].get("renderD129_maps_expected_bdf")
        and gpu["identity"].get("hwmon_maps_expected_bdf")
    )
    check_add(checks, "gpu_identity", gpu_ok, gpu["identity"])
    controls_ok = all(
        gpu.get("raw", {}).get(key, {}).get("status") == "OK"
        for key in ("power1_cap", "power_dpm_force_performance_level", "power_control", "runtime_status")
    )
    check_add(checks, "gpu_controls_readable", controls_ok, gpu.get("controls"))

    binary_ok = C1_BINARY.is_file() and os.access(C1_BINARY, os.X_OK)
    check_add(checks, "c1_binary", binary_ok, {"path": str(C1_BINARY), "executable": binary_ok})

    provenance = provenance_snapshot()
    hash_ok = all(
        provenance["hashes"].get(name, {}).get("sha256") == expected
        for name, expected in EXPECTED_HASHES.items()
    )
    build_ok = provenance.get("build_id") == EXPECTED_BUILD_ID
    check_add(checks, "provenance_hashes", hash_ok, provenance["hashes"])
    check_add(checks, "build_id", build_ok, {"actual": provenance.get("build_id"), "expected": EXPECTED_BUILD_ID})

    tmpfs = fs_type(RUNTIME_DIR)
    check_add(checks, "runtime_tmpfs", tmpfs == "tmpfs", {"path": str(RUNTIME_DIR), "fstype": tmpfs})
    jsonl = OBSERVER_JSONL
    jsonl_exists = os.path.lexists(jsonl)
    check_add(checks, "jsonl_collision", not jsonl_exists, {"path": str(jsonl), "exists": jsonl_exists})

    dstate = dstate_snapshot()
    check_add(checks, "dstate", dstate["count"] == 0 and dstate.get("complete") is True, dstate)
    procs = procs_snapshot()
    check_add(checks, "procs_blocked", procs.get("procs_blocked") == 0, procs)
    pressure = pressure_snapshot()
    io_some = pressure.get("io", {}).get("some", {}).get("avg10")
    io_full = pressure.get("io", {}).get("full", {}).get("avg10")
    io_ok = io_guard_criterion_ok(io_some, io_full)
    check_add(
        checks,
        "io_guard_criterion",
        io_ok,
        {
            "some_avg10": io_some,
            "full_avg10": io_full,
            "max": IO_GUARD_AVG10_MAX,
            "classification": "PROPOSED_OPERATIONAL_NOT_UNIVERSAL",
        },
    )

    duplicate = process_scan_for_existing_c1()
    check_add(checks, "no_existing_c1", not duplicate, duplicate)
    current_path, current_state = load_current_state()
    incomplete = state_is_incomplete(current_state)
    check_add(
        checks,
        "no_incomplete_runtime_state",
        not incomplete,
        {"path": str(current_path) if current_path else None, "incomplete": incomplete},
    )
    orphan_runs = orphan_runtime_runs()
    check_add(checks, "no_orphan_runtime_runs", not orphan_runs, orphan_runs)
    legacy_runtime = legacy_runtime_inventory()
    check_add(
        checks,
        "historical_legacy_runtime",
        not legacy_runtime.get("blocking", False),
        legacy_runtime,
    )

    units: Dict[str, Dict[str, Any]] = {}
    for spec in UNIT_SPECS:
        units[spec["unit"]] = {
            "scope": spec["scope"],
            "kind": spec["kind"],
            "state": unit_state(spec["scope"], spec["unit"]),
        }
        units[spec["unit"]]["pre_active"] = unit_is_active(units[spec["unit"]]["state"])
    check_add(checks, "units_readable", all(not unit_unsafe(units[u["unit"]]["state"]) for u in UNIT_SPECS), units)

    ownership = {
        "status": OWNERSHIP_PARTIAL,
        "reason": "minimal route does not close Xwayland/KWin/ChatGPT; no exclusive ownership claim",
        "contract_version": CONTRACT_VERSION,
        "full_proof": False,
    }
    precheck_contracts = build_precheck_contracts(checks)
    ownership_proof = evaluate_ownership_proof()
    system_gates = system_gate_contracts()
    btrfs_gate = btrfs_gate_contract()
    execution_gate = evaluate_execution_gate(ownership_proof, system_gates, btrfs_gate)
    return {
        "contract_version": CONTRACT_VERSION,
        "ok": all(item["status"] == "PASS" for item in checks.values()),
        "timestamp": now_iso(),
        "hostname": hostname,
        "kernel": kernel,
        "boot_id": read_optional(Path("/proc/sys/kernel/random/boot_id")),
        "checks": checks,
        "precheck_contracts": precheck_contracts,
        "gpu": gpu,
        "provenance": provenance,
        "dstate": dstate,
        "procs": procs,
        "pressure": pressure,
        "diskstats": diskstats_snapshot(),
        "units": units,
        "ownership": ownership,
        "ownership_contract": ownership_contract(),
        "ownership_proof": ownership_proof,
        "system_gate_contracts": system_gates,
        "btrfs_gate": btrfs_gate,
        "execution_gate": execution_gate,
        "runtime_contract": runtime_contract_snapshot(),
        "restore_contract": restore_contract_snapshot(),
        "fallback_contracts": fallback_contracts(),
        "implementation_provenance": implementation_provenance(),
    }


def c1_command() -> List[str]:
    return [
        "/usr/bin/python3",
        str(OBSERVER),
        "--cwd",
        str(WORKLOAD_DIR),
        "--binary-sha256",
        EXPECTED_HASHES["main-graphics"],
        "--build-id",
        EXPECTED_BUILD_ID,
        "--compiler",
        EXPECTED_COMPILER,
        "--cxxflags",
        EXPECTED_CXXFLAGS,
        "--gpu-root",
        "/sys/class/drm/card1/device",
        "--hwmon-root",
        EXPECTED_HWMON,
        "--cpu-root",
        "/sys/devices/system/cpu/cpufreq",
        "--",
        str(C1_BINARY),
        "--width",
        "1920",
        "--height",
        "1080",
        "--layers",
        "4",
        "--textures",
        "4",
        "--tex-size",
        "4096",
        "--fma-iters",
        "4",
        "--msaa",
        "1",
        "--seed",
        "0x13579BDF",
        "--seed-extra",
        "0x2468ACE0",
        "--warmup",
        "5",
        "--duration",
        "20",
    ]


def planned_actions(pre: Dict[str, Any]) -> Dict[str, Any]:
    unit_actions = []
    for spec in UNIT_SPECS:
        unit = spec["unit"]
        entry = pre["units"].get(unit, {})
        if entry.get("pre_active"):
            argv = (["/usr/bin/sudo", "/usr/bin/systemctl"] if spec["scope"] == "system" else ["/usr/bin/systemctl", "--user"]) + ["stop", unit]
            action = "STOP"
        else:
            action = "SKIP_INACTIVE_PRE"
            argv = []
        unit_actions.append({"unit": unit, "scope": spec["scope"], "action": action, "argv": argv})
    return {
        "unit_actions": unit_actions,
        "guard_seconds": GUARD_SECONDS,
        "t_pre_seconds": T_PRE_SECONDS,
        "c1_command": c1_command(),
        "c1_command_text": command_text(c1_command()),
        "t_post_seconds": T_POST_SECONDS,
        "restore": "start only units successfully/attemptfully stopped by this execution when PRE active",
        "postchecks": ["unit PRE/POST comparison", "GPU accessibility/control readback", "runtime state terminal status"],
    }


def provenance_unchanged(pre: Dict[str, Any]) -> Tuple[bool, Dict[str, Any]]:
    current = provenance_snapshot()
    before = pre.get("provenance", {})
    mismatches: List[str] = []
    for name, expected in EXPECTED_HASHES.items():
        actual = current.get("hashes", {}).get(name, {}).get("sha256")
        if actual != expected:
            mismatches.append(f"{name}:{actual!r}!={expected}")
    if current.get("build_id") != EXPECTED_BUILD_ID:
        mismatches.append("build_id")
    if before.get("git_head", {}).get("value") != current.get("git_head", {}).get("value"):
        mismatches.append("git_head")
    return not mismatches, {"mismatches": mismatches, "current": current}


def prelaunch_collision_check() -> Dict[str, Any]:
    processes = process_scan_for_existing_c1()
    jsonl = OBSERVER_JSONL
    jsonl_exists = os.path.lexists(jsonl)
    return {
        "status": "PASS" if not processes and not jsonl_exists else "FAIL",
        "processes": processes,
        "observer_jsonl_exists": jsonl_exists,
    }


def make_run_id() -> str:
    return f"{dt.datetime.now(dt.timezone.utc).strftime('%Y%m%dT%H%M%SZ')}-{os.getpid()}"


def state_summary(state: Dict[str, Any]) -> Dict[str, Any]:
    return {
        "runtime_namespace": state.get("runtime_namespace"),
        "runtime_schema_version": state.get("runtime_schema_version"),
        "automator_version": state.get("automator_version"),
        "automator_sha256": state.get("automator_sha256"),
        "phase": state.get("phase"),
        "terminal": state.get("terminal"),
        "result": state.get("result"),
        "guard": {
            label: state.get("guard", {}).get(label, {}).get("status")
            for label in ("T_GUARD", "T_PRE", "T_POST")
        },
        "c1": {
            "status": state.get("c1", {}).get("status"),
            "executed": state.get("c1", {}).get("executed"),
            "formal_pass": state.get("c1", {}).get("formal_pass"),
            "runtime_validated": state.get("c1", {}).get("runtime_validated"),
        },
        "restore": {"status": state.get("restore", {}).get("status")},
        "post": {"status": state.get("post", {}).get("status")},
        "error": state.get("error"),
        "finished_at": state.get("finished_at"),
    }


def initial_state(run_id: str, run_dir: Path, pre: Dict[str, Any], plan: Dict[str, Any]) -> Dict[str, Any]:
    created_at = now_iso()
    automator_sha256 = sha256_file(Path(__file__).resolve())
    state: Dict[str, Any] = {
        "schema_version": RUNTIME_SCHEMA_VERSION,
        "runtime_schema_version": RUNTIME_SCHEMA_VERSION,
        "runtime_namespace_version": RUNTIME_NAMESPACE_VERSION,
        "runtime_namespace": RUNTIME_NAMESPACE,
        "parent_namespace": LEGACY_RUNTIME_NAMESPACE,
        "parent_namespace_path": str(LEGACY_STATE_ROOT),
        "historical_namespace": LEGACY_RUNTIME_NAMESPACE,
        "historical_namespace_path": str(LEGACY_STATE_ROOT),
        "legacy_reference": {
            "namespace": LEGACY_RUNTIME_NAMESPACE,
            "path": str(LEGACY_STATE_ROOT),
            "manifest_id": LEGACY_MANIFEST_ID,
            "classification": LEGACY_CLASSIFICATION,
            "blocking": False,
            "state_sha256": HISTORICAL_LEGACY_RUNS[LEGACY_RUN_ID]["state_sha256"],
            "events_sha256": HISTORICAL_LEGACY_RUNS[LEGACY_RUN_ID]["events_sha256"],
            "current_sha256": HISTORICAL_LEGACY_RUNS[LEGACY_RUN_ID]["current_sha256"],
        },
        "runtime_namespace_activated_at": RUNTIME_NAMESPACE_ACTIVATED_AT,
        "run_created_at": created_at,
        "automator_version": VERSION,
        "automator_sha256": automator_sha256,
        "script_sha256": automator_sha256,
        "contract_version": CONTRACT_VERSION,
        "runtime_contract": runtime_contract_snapshot(),
        "restore_contract": restore_contract_snapshot(),
        "contract_manifest": {
            "ownership": ownership_contract(),
            "system_gates": system_gate_contracts(),
            "btrfs": btrfs_gate_contract(),
            "fallback": fallback_contracts(),
            "provenance": implementation_provenance(),
        },
        "run_id": run_id,
        "pid": os.getpid(),
        "started_at": created_at,
        "updated_at": created_at,
        "phase": "PRE_CAPTURED",
        "terminal": False,
        "pre": pre,
        "planned": plan,
        "units": {},
        "actions": [],
        "guard": {
            "T_GUARD": {
                "status": "NOT_RUN",
                "reason": None,
                "sample_count": 0,
                "elapsed_seconds": 0.0,
                "log": None,
            },
            "T_PRE": {
                "status": "NOT_RUN",
                "reason": None,
                "sample_count": 0,
                "elapsed_seconds": 0.0,
                "log": None,
            },
            "T_POST": {
                "status": "NOT_RUN",
                "reason": None,
                "sample_count": 0,
                "elapsed_seconds": 0.0,
                "log": None,
            },
        },
        "c1": {
            "status": "NOT_RUN",
            "executed": False,
            "runtime_validated": False,
            "formal_pass": False,
            "command": c1_command(),
            "stdout": None,
            "stderr": None,
            "observer_jsonl": None,
            "returncode": None,
            "formal_checks": {},
            "claims": {
                "A": "NOT_RUN",
                "B": "NOT_RUN_FREQUENCY_EFFECTIVE_NOT_AVAILABLE",
                "C": "NOT_RUN_OWNERSHIP_PARTIAL",
                "D": "NOT_RUN",
            },
        },
        "restore": {"status": "NOT_RUN", "attempted_units": [], "results": {}},
        "post": {"status": "NOT_RUN"},
        "result": "IN_PROGRESS",
        "error": None,
        "events": [],
        "final_state": None,
    }
    state["initial_state"] = state_summary(state)
    return state


def update_state(runtime_state: Dict[str, Any], state_path: Path, events_path: Path, event: str, **fields: Any) -> None:
    runtime_state["updated_at"] = now_iso()
    entry = {"timestamp": runtime_state["updated_at"], "event": event, **fields}
    runtime_state.setdefault("events", []).append(entry)
    append_jsonl(events_path, entry)
    atomic_write_json(state_path, runtime_state)


def safe_update_state(runtime_state: Dict[str, Any], state_path: Path, events_path: Path, event: str, **fields: Any) -> None:
    try:
        update_state(runtime_state, state_path, events_path, event, **fields)
    except Exception as exc:  # noqa: BLE001 - restore must continue after audit write failure
        errors = runtime_state.setdefault("state_write_errors", [])
        errors.append({"timestamp": now_iso(), "event": event, "critical": False, "error": f"{type(exc).__name__}: {exc}"})


def required_update_state(runtime_state: Dict[str, Any], state_path: Path, events_path: Path, event: str, **fields: Any) -> None:
    try:
        update_state(runtime_state, state_path, events_path, event, **fields)
    except Exception as exc:  # noqa: BLE001 - critical pre-C1 evidence must fail closed
        errors = runtime_state.setdefault("state_write_errors", [])
        errors.append({"timestamp": now_iso(), "event": event, "critical": True, "error": f"{type(exc).__name__}: {exc}"})
        raise AutomatorError(f"required state persistence failed during {event}") from exc


def set_signal_handlers() -> None:
    def handler(signum: int, _frame: Any) -> None:
        global INTERRUPTED
        INTERRUPTED = True

    signal.signal(signal.SIGINT, handler)
    signal.signal(signal.SIGTERM, handler)


def check_interrupted() -> None:
    if INTERRUPTED:
        raise InterruptedRun("signal received at safe checkpoint")


def validate_runtime_layout() -> None:
    if not namespace_paths_separate():
        raise AutomatorError("active and legacy runtime namespaces are not separate siblings")
    if not RUNTIME_DIR.is_dir() or RUNTIME_DIR.is_symlink():
        raise AutomatorError(f"runtime directory is not a real directory: {RUNTIME_DIR}")
    if os.path.lexists(STATE_ROOT) and (STATE_ROOT.is_symlink() or not STATE_ROOT.is_dir()):
        raise AutomatorError(f"state root is not a real directory: {STATE_ROOT}")
    if os.path.lexists(STATE_ROOT):
        st = STATE_ROOT.stat()
        if st.st_uid != UID or (st.st_mode & 0o077):
            raise AutomatorError("state root ownership/permissions are not private")
        allowed_root_entries = {".lock", "CURRENT", "c1-observer-v1.jsonl", "runs"}
        root_entries = {entry.name for entry in STATE_ROOT.iterdir()}
        unexpected = root_entries - allowed_root_entries
        if unexpected:
            raise AutomatorError(f"active runtime root has unexpected entries: {sorted(unexpected)!r}")
    runs_root = STATE_ROOT / "runs"
    if os.path.lexists(runs_root) and (runs_root.is_symlink() or not runs_root.is_dir()):
        raise AutomatorError("runtime runs path is not a real directory")
    if os.path.lexists(runs_root):
        st = runs_root.stat()
        if st.st_uid != UID or (st.st_mode & 0o077):
            raise AutomatorError("runtime runs ownership/permissions are not private")
    if os.path.lexists(CURRENT_POINTER) and (CURRENT_POINTER.is_symlink() or not CURRENT_POINTER.is_file()):
        raise AutomatorError("runtime CURRENT path is not a regular file")
    if os.path.lexists(CURRENT_POINTER):
        st = CURRENT_POINTER.stat()
        if st.st_uid != UID or (st.st_mode & 0o077):
            raise AutomatorError("runtime CURRENT ownership/permissions are not private")
    if os.path.lexists(LOCK_PATH) and (LOCK_PATH.is_symlink() or not LOCK_PATH.is_file()):
        raise AutomatorError("runtime lock path is not a regular file")
    if os.path.lexists(LOCK_PATH):
        st = LOCK_PATH.stat()
        if st.st_uid != UID or (st.st_mode & 0o077):
            raise AutomatorError("runtime lock ownership/permissions are not private")
    if os.path.lexists(OBSERVER_JSONL) and (OBSERVER_JSONL.is_symlink() or not OBSERVER_JSONL.is_file()):
        raise AutomatorError("runtime observer JSONL path is not a regular file")


class RuntimeArtifacts:
    """Track only artifacts created by the current authorized initialization."""

    def __init__(self) -> None:
        self.created_files: List[Path] = []
        self.created_dirs: List[Path] = []
        self.current_existed = False
        self.current_before: Optional[bytes] = None
        self.current_changed = False
        self.cleanup_errors: List[str] = []

    @staticmethod
    def _within_active_root(path: Path) -> bool:
        try:
            root = os.path.realpath(STATE_ROOT)
            target = os.path.realpath(path)
            return os.path.commonpath([root, target]) == root and root != os.path.realpath(LEGACY_STATE_ROOT)
        except (OSError, ValueError):
            return False

    def record_file(self, path: Path) -> None:
        if self._within_active_root(path) and path not in self.created_files:
            self.created_files.append(path)

    def record_dir(self, path: Path) -> None:
        if self._within_active_root(path) and path not in self.created_dirs:
            self.created_dirs.append(path)

    def capture_current(self) -> None:
        self.current_existed = os.path.lexists(CURRENT_POINTER)
        if self.current_existed:
            try:
                st = CURRENT_POINTER.lstat()
                if stat_module.S_ISREG(st.st_mode) and st.st_uid == UID:
                    self.current_before = CURRENT_POINTER.read_bytes()
            except OSError as exc:
                self.current_before = None
                self.cleanup_errors.append(f"capture CURRENT: {type(exc).__name__}: {exc}")
        else:
            self.record_file(CURRENT_POINTER)

    def mark_current_changed(self) -> None:
        self.current_changed = True

    @staticmethod
    def _remove_owned_file(path: Path) -> Optional[str]:
        try:
            st = path.lstat()
            if not stat_module.S_ISREG(st.st_mode) or st.st_uid != UID:
                return f"refused unsafe cleanup file: {path}"
            path.unlink()
            return None
        except FileNotFoundError:
            return None
        except OSError as exc:
            return f"cleanup file {path}: {type(exc).__name__}: {exc}"

    @staticmethod
    def _remove_owned_empty_dir(path: Path) -> Optional[str]:
        try:
            st = path.lstat()
            if not stat_module.S_ISDIR(st.st_mode) or st.st_uid != UID:
                return f"refused unsafe cleanup directory: {path}"
            if any(path.iterdir()):
                return f"cleanup directory not empty: {path}"
            path.rmdir()
            return None
        except FileNotFoundError:
            return None
        except OSError as exc:
            return f"cleanup directory {path}: {type(exc).__name__}: {exc}"

    def cleanup(self) -> List[str]:
        """Remove only paths recorded as created by this invocation."""
        errors: List[str] = []
        if self.current_changed:
            if self.current_existed:
                if self.current_before is None:
                    errors.append("cannot restore pre-existing CURRENT safely")
                else:
                    try:
                        atomic_write_text(CURRENT_POINTER, self.current_before.decode("utf-8"))
                    except (OSError, UnicodeError) as exc:
                        errors.append(f"restore CURRENT: {type(exc).__name__}: {exc}")
            else:
                error = self._remove_owned_file(CURRENT_POINTER)
                if error:
                    errors.append(error)
        for path in reversed(self.created_files):
            if path == CURRENT_POINTER and self.current_changed:
                continue
            error = self._remove_owned_file(path)
            if error:
                errors.append(error)
        for path in reversed(self.created_dirs):
            error = self._remove_owned_empty_dir(path)
            if error:
                errors.append(error)
        self.cleanup_errors.extend(errors)
        return errors


class RuntimeLock:
    def __init__(self, artifacts: Optional[RuntimeArtifacts] = None) -> None:
        self.artifacts = artifacts
        self.fd: Optional[int] = None
        self.entered = False

    def _release(self) -> None:
        if self.fd is None:
            return
        try:
            try:
                fcntl.flock(self.fd, fcntl.LOCK_UN)
            except OSError:
                pass
        finally:
            os.close(self.fd)
            self.fd = None

    def cleanup_initialization(self) -> List[str]:
        self._release()
        return self.artifacts.cleanup() if self.artifacts is not None else []

    def __enter__(self) -> "RuntimeLock":
        root_was_absent = not os.path.lexists(STATE_ROOT)
        lock_was_absent = not os.path.lexists(LOCK_PATH)
        try:
            validate_runtime_layout()
            STATE_ROOT.mkdir(parents=True, exist_ok=True, mode=0o700)
            if root_was_absent and self.artifacts is not None:
                self.artifacts.record_dir(STATE_ROOT)
            validate_runtime_layout()
            flags = os.O_CREAT | os.O_RDWR
            if hasattr(os, "O_NOFOLLOW"):
                flags |= os.O_NOFOLLOW
            self.fd = os.open(LOCK_PATH, flags, 0o600)
            if lock_was_absent and self.artifacts is not None:
                self.artifacts.record_file(LOCK_PATH)
            st = os.fstat(self.fd)
            if st.st_uid != UID or (st.st_mode & 0o077):
                raise AutomatorError("runtime lock ownership/permissions are not private")
            try:
                fcntl.flock(self.fd, fcntl.LOCK_EX | fcntl.LOCK_NB)
            except BlockingIOError as exc:
                raise AutomatorError("another automator execution holds the runtime lock") from exc
            os.ftruncate(self.fd, 0)
            os.write(self.fd, f"{os.getpid()}\n".encode())
            os.fsync(self.fd)
            self.entered = True
            return self
        except BaseException as exc:
            self._release()
            cleanup_errors = self.artifacts.cleanup() if self.artifacts is not None else []
            if cleanup_errors:
                print(f"RUNTIME_INITIALIZATION_CLEANUP_ERRORS={json.dumps(cleanup_errors, ensure_ascii=False)}", file=sys.stderr)
            if isinstance(exc, AutomatorError):
                raise
            raise AutomatorError(f"runtime initialization failed: {type(exc).__name__}: {exc}") from exc

    def __exit__(self, _exc_type: Any, _exc: Any, _tb: Any) -> None:
        self._release()


def initialize_authorized_runtime_state(pre: Dict[str, Any], artifacts: RuntimeArtifacts) -> Dict[str, Any]:
    """Create only the v2 artifacts needed before the runtime-dependent observer check."""
    run_id = make_run_id()
    runs_root = STATE_ROOT / "runs"
    runs_root_was_absent = not os.path.lexists(runs_root)
    runs_root.mkdir(exist_ok=True, mode=0o700)
    if runs_root_was_absent:
        artifacts.record_dir(runs_root)
    os.chmod(runs_root, 0o700)
    validate_runtime_layout()

    run_dir = runs_root / run_id
    run_dir.mkdir(exist_ok=False, mode=0o700)
    artifacts.record_dir(run_dir)
    tmp_dir = run_dir / "tmp"
    cache_dir = run_dir / "cache"
    tmp_dir.mkdir(mode=0o700)
    artifacts.record_dir(tmp_dir)
    cache_dir.mkdir(mode=0o700)
    artifacts.record_dir(cache_dir)
    os.chmod(run_dir, 0o700)

    state_path = run_dir / "state.json"
    events_path = run_dir / "events.jsonl"
    artifacts.record_file(state_path)
    artifacts.record_file(events_path)
    plan = planned_actions(pre)
    state = initial_state(run_id, run_dir, pre, plan)
    state["runtime_contract"] = runtime_contract_snapshot(materialized=True, validated=False)
    update_state(state, state_path, events_path, "run_created", root=str(run_dir))
    artifacts.capture_current()
    artifacts.mark_current_changed()
    atomic_write_text(CURRENT_POINTER, run_id + "\n")
    validate_runtime_layout()
    return {
        "run_id": run_id,
        "run_dir": run_dir,
        "state_path": state_path,
        "events_path": events_path,
        "state": state,
    }


def sudo_authenticate() -> Dict[str, Any]:
    if PRODUCTION_TTY_REQUIRED and (not sys.stdin.isatty() or not sys.stdout.isatty()):
        raise AutomatorError("interactive TTY required; normal sudo authentication cannot be requested")
    # Deliberately normal sudo: no -n, no password capture, no bypass.
    try:
        result = subprocess.run(["/usr/bin/sudo", "-v"], check=False)
        return {"command": "sudo -v", "returncode": result.returncode, "status": "OK" if result.returncode == 0 else "FAIL"}
    except Exception as exc:  # noqa: BLE001
        return {"command": "sudo -v", "status": "FAIL", "error": f"{type(exc).__name__}: {exc}"}


def privileged_unit_command(scope: str, verb: str, unit: str) -> List[str]:
    if scope == "user":
        return ["/usr/bin/systemctl", "--user", verb, unit]
    return ["/usr/bin/sudo", "/usr/bin/systemctl", verb, unit]


def run_interactive_command(argv: Sequence[str]) -> Dict[str, Any]:
    try:
        result = subprocess.run(list(argv), check=False, timeout=SYSTEMCTL_COMMAND_TIMEOUT_SECONDS)
        return {"argv": list(argv), "returncode": result.returncode, "status": "OK" if result.returncode == 0 else "FAIL"}
    except subprocess.TimeoutExpired:
        return {"argv": list(argv), "status": "FAIL", "error": "timeout", "manual_intervention_required": True}
    except Exception as exc:  # noqa: BLE001
        return {"argv": list(argv), "status": "FAIL", "error": f"{type(exc).__name__}: {exc}"}


def gpu_control_guard(pre_gpu: Dict[str, Any]) -> Tuple[Dict[str, Any], List[str]]:
    current = gpu_snapshot()
    failures: List[str] = []
    for key in ("power1_cap", "power_dpm_force_performance_level", "power_control"):
        before = pre_gpu.get("controls", {}).get(key)
        after = current.get("controls", {}).get(key)
        if before is None or after is None or str(before).startswith("NOT_AVAILABLE") or str(after).startswith("NOT_AVAILABLE"):
            failures.append(f"GPU control unreadable: {key}: {before!r}->{after!r}")
        elif before != after:
            failures.append(f"GPU control changed: {key}: {before!r}->{after!r}")
    identity = current.get("identity", {})
    if (
        identity.get("vendor") != EXPECTED_VENDOR
        or identity.get("device") != EXPECTED_DEVICE
        or identity.get("driver") != EXPECTED_DRIVER
        or not identity.get("card1_exists")
        or not identity.get("renderD129_exists")
        or not identity.get("hwmon_exists")
        or not identity.get("card1_maps_expected_bdf")
        or not identity.get("renderD129_maps_expected_bdf")
        or not identity.get("hwmon_maps_expected_bdf")
    ):
        failures.append("RX550 identity/accessibility changed or unavailable")
    return current, failures


def guard_sample(pre: Dict[str, Any], touched: List[Dict[str, Any]], sample_index: int = 0) -> Dict[str, Any]:
    dstate = dstate_snapshot()
    procs = procs_snapshot()
    pressure = pressure_snapshot()
    failures: List[str] = []
    if dstate["count"] != 0 or dstate.get("complete") is not True:
        failures.append(f"D-state count={dstate['count']} complete={dstate.get('complete')}")
    if procs.get("procs_blocked") != 0:
        failures.append(f"procs_blocked={procs.get('procs_blocked')}")
    io = pressure.get("io", {})
    some_avg10 = io.get("some", {}).get("avg10")
    full_avg10 = io.get("full", {}).get("avg10")
    if not finite_number(some_avg10) or some_avg10 > IO_GUARD_AVG10_MAX:
        failures.append(f"IO some avg10>{IO_GUARD_AVG10_MAX}: {some_avg10}")
    if not finite_number(full_avg10) or full_avg10 > IO_GUARD_AVG10_MAX:
        failures.append(f"IO full avg10>{IO_GUARD_AVG10_MAX}: {full_avg10}")
    for spec in UNIT_SPECS:
        unit = spec["unit"]
        pre_entry = pre["units"].get(unit, {})
        current = unit_state(spec["scope"], unit)
        if unit_unsafe(current):
            failures.append(f"unit readback unsafe/failed: {unit} state={current.get('ActiveState')}")
        elif pre_entry.get("pre_active"):
            if not unit_expected_inactive(current):
                failures.append(f"isolated unit became active: {unit} {current.get('ActiveState')}")
        elif unit_is_active(current):
            failures.append(f"PRE-inactive unit became active: {unit} {current.get('ActiveState')}")
    gpu, gpu_failures = gpu_control_guard(pre["gpu"])
    failures.extend(gpu_failures)
    return {
        "schema": "c1-guard.v1",
        "sample_index": sample_index,
        "timestamp": now_iso(),
        "mono": monotonic(),
        "dstate": dstate,
        "procs": procs,
        "io_some_avg10": some_avg10,
        "io_full_avg10": full_avg10,
        "gpu": gpu,
        "system_gate_contracts": pre.get("system_gate_contracts", system_gate_contracts()),
        "btrfs_gate": pre.get("btrfs_gate", btrfs_gate_contract()),
        "touched_units": [item["unit"] for item in touched],
        "failures": failures,
        "status": "FAIL" if failures else "PASS",
    }


def run_guard_window(
    label: str,
    seconds: int,
    pre: Dict[str, Any],
    touched: List[Dict[str, Any]],
    run_dir: Path,
    state: Dict[str, Any],
    state_path: Path,
    events_path: Path,
) -> bool:
    guard_log = run_dir / f"{label.lower()}.jsonl"
    started = monotonic()
    sample_count = 0
    status = "PASS"
    reason: Optional[str] = None
    required_update_state(state, state_path, events_path, "window_start", window=label, seconds=seconds)
    try:
        while True:
            check_interrupted()
            sample = guard_sample(pre, touched, sample_count)
            sample_count += 1
            append_jsonl(guard_log, sample)
            if sample["status"] == "FAIL":
                status = "FAIL"
                reason = "; ".join(sample["failures"])
                break
            elapsed = monotonic() - started
            if elapsed >= seconds:
                break
            time.sleep(min(GUARD_SAMPLE_SECONDS, seconds - elapsed))
    except BaseException as exc:  # noqa: BLE001 - state must show interrupted window
        status = "INTERRUPTED"
        reason = f"{type(exc).__name__}: {exc}"
        state["guard"][label] = {
            "status": status,
            "reason": reason,
            "sample_count": sample_count,
            "elapsed_seconds": round(monotonic() - started, 3),
            "log": str(guard_log),
        }
        required_update_state(state, state_path, events_path, "window_end", window=label, status=status, reason=reason, sample_count=sample_count, elapsed_seconds=round(monotonic() - started, 3), log=str(guard_log))
        raise
    elapsed = round(monotonic() - started, 3)
    state["guard"][label] = {
        "status": status,
        "reason": reason,
        "sample_count": sample_count,
        "elapsed_seconds": elapsed,
        "log": str(guard_log),
    }
    required_update_state(state, state_path, events_path, "window_end", window=label, status=status, reason=reason, sample_count=sample_count, elapsed_seconds=elapsed, log=str(guard_log))
    return status == "PASS"


def apply_isolation(
    pre: Dict[str, Any],
    state: Dict[str, Any],
    state_path: Path,
    events_path: Path,
    touched: List[Dict[str, Any]],
) -> None:
    for spec in UNIT_SPECS:
        check_interrupted()
        unit = spec["unit"]
        pre_entry = pre["units"][unit]
        current = unit_state(spec["scope"], unit)
        entry = {
            "unit": unit,
            "scope": spec["scope"],
            "kind": spec["kind"],
            "pre": pre_entry,
            "before_action": current,
            "action": "NOT_STARTED",
            "stop_result": None,
            "readback": None,
        }
        state["units"][unit] = entry
        update_state(state, state_path, events_path, "unit_pre", unit=unit, unit_state=current)
        if not pre_entry.get("pre_active"):
            if unit_unsafe(current):
                entry["action"] = "ABORT_READBACK_INVALID"
                update_state(state, state_path, events_path, "unit_abort", unit=unit, reason="invalid current unit state")
                raise AutomatorError(f"invalid current state for {unit}")
            if unit_is_active(current):
                entry["action"] = "ABORT_PRE_STATE_CHANGED"
                update_state(state, state_path, events_path, "unit_abort", unit=unit, reason="inactive PRE became active")
                raise AutomatorError(f"unit {unit} changed from inactive PRE to active before action")
            entry["action"] = "SKIP_INACTIVE_PRE"
            update_state(state, state_path, events_path, "unit_skip", unit=unit, reason="inactive in PRE")
            continue
        if not unit_is_active(current):
            entry["action"] = "ABORT_PRE_STATE_CHANGED"
            update_state(state, state_path, events_path, "unit_abort", unit=unit, reason="active PRE became inactive before action")
            raise AutomatorError(f"unit {unit} changed from active PRE before action")
        argv = privileged_unit_command(spec["scope"], "stop", unit)
        entry["action"] = "STOP_REQUESTED"
        # Mark before invocation: a failed/partial stop must still be restored.
        touched.append({"unit": unit, "scope": spec["scope"], "pre_active": True})
        update_state(state, state_path, events_path, "unit_stop_requested", unit=unit, argv=argv)
        stop_result = run_interactive_command(argv)
        entry["stop_result"] = stop_result
        if stop_result.get("returncode") != 0:
            if stop_result.get("manual_intervention_required"):
                state["manual_intervention_required"] = {"unit": unit, "phase": "stop", "result": stop_result}
            update_state(state, state_path, events_path, "unit_stop_failed", unit=unit, result=stop_result)
            raise AutomatorError(f"failed to stop {unit}: {stop_result}")
        readback = unit_state(spec["scope"], unit)
        entry["readback"] = readback
        if not unit_expected_inactive(readback):
            update_state(state, state_path, events_path, "unit_readback_failed", unit=unit, readback=readback)
            raise AutomatorError(f"unit {unit} did not become inactive: {readback}")
        update_state(state, state_path, events_path, "unit_isolated", unit=unit, readback=readback)


def restore_units(
    touched: List[Dict[str, Any]],
    state: Dict[str, Any],
    state_path: Path,
    events_path: Path,
) -> Dict[str, Any]:
    results: Dict[str, Any] = {}
    failures: List[str] = []
    contract = state.setdefault("restore_contract", restore_contract_snapshot())
    contract = restore_contract_transition(contract, "EXECUTE" if touched else "NOT_NEEDED")
    state["restore_contract"] = contract
    for item in reversed(touched):
        unit = item["unit"]
        current = unit_state(item["scope"], unit)
        entry: Dict[str, Any] = {"pre_active": item["pre_active"], "before_restore": current}
        if not item["pre_active"]:
            entry["action"] = "SKIP_NOT_STOPPED_BY_THIS_RUN"
            results[unit] = entry
            continue
        if unit_unsafe(current):
            entry["action"] = "MANUAL_READBACK_REQUIRED"
            entry["status"] = "MANUAL_INTERVENTION_REQUIRED"
            state["manual_intervention_required"] = {"unit": unit, "phase": "restore", "reason": "unsafe or unreadable unit state"}
            failures.append(f"{unit}:unsafe_state={current.get('ActiveState')}")
            results[unit] = entry
            break
        if unit_is_active(current):
            entry["action"] = "ALREADY_ACTIVE"
            entry["readback"] = current
            results[unit] = entry
            safe_update_state(state, state_path, events_path, "unit_already_restored", unit=unit, readback=current)
            continue
        argv = privileged_unit_command(item["scope"], "start", unit)
        entry["action"] = "START_REQUESTED"
        result = run_interactive_command(argv)
        entry["start_result"] = result
        if result.get("returncode") != 0:
            if result.get("manual_intervention_required"):
                state["manual_intervention_required"] = {"unit": unit, "phase": "restore", "result": result}
            failures.append(f"{unit}:start_rc={result.get('returncode')}")
            entry["status"] = "FAIL"
        else:
            readback = unit_state(item["scope"], unit)
            entry["readback"] = readback
            if unit_is_active(readback):
                entry["status"] = "OK"
            else:
                entry["status"] = "FAIL"
                failures.append(f"{unit}:readback={readback.get('ActiveState')}")
        results[unit] = entry
        safe_update_state(state, state_path, events_path, "unit_restore", unit=unit, result=entry)
        if state.get("manual_intervention_required"):
            break
    if not touched:
        status = "RESTORE_NOT_NEEDED"
    elif failures:
        status = "RESTORE_FAILED" if len(failures) == len(touched) else "RESTORE_PARTIAL"
    else:
        status = "RESTORE_OK"
    return {"status": status, "attempted_units": [item["unit"] for item in touched], "results": results, "failures": failures}


def settle_restore_contract(state: Dict[str, Any], post_status: Optional[str] = None) -> Dict[str, Any]:
    contract = state.setdefault("restore_contract", restore_contract_snapshot())
    restore_status = state.get("restore", {}).get("status")
    if restore_status == "RESTORE_NOT_NEEDED":
        state["restore_contract"] = restore_contract_transition(contract, "NOT_NEEDED")
        return state["restore_contract"]
    success = restore_status == "RESTORE_OK" and (post_status is None or post_status == "POST_OK")
    state["restore_contract"] = restore_contract_transition(contract, "VALIDATE" if success else "FAIL", success=success)
    return state["restore_contract"]


def postcheck(pre: Dict[str, Any], touched: List[Dict[str, Any]]) -> Dict[str, Any]:
    discrepancies: List[str] = []
    external_transitions: List[Dict[str, Any]] = []
    states: Dict[str, Any] = {}
    touched_units = {item["unit"] for item in touched}
    for spec in UNIT_SPECS:
        unit = spec["unit"]
        before = pre["units"][unit]
        after = unit_state(spec["scope"], unit)
        states[unit] = after
        if unit_unsafe(after):
            discrepancies.append(f"{unit}: unsafe/invalid POST unit state={after.get('ActiveState')}")
        expected_active = before.get("pre_active")
        actual_active = unit_is_active(after)
        if expected_active != actual_active:
            discrepancy = f"{unit}: PRE active={expected_active} POST active={actual_active}"
            discrepancies.append(discrepancy)
            if unit not in touched_units:
                external_transitions.append(
                    {
                        "unit": unit,
                        "pre_active": expected_active,
                        "post_active": actual_active,
                        "classification": "EXTERNAL_TRANSITION_OR_NATURAL_ONESHOT_COMPLETION",
                        "automator_stop_recorded": False,
                        "causality": "NOT_PROVEN",
                    }
                )
        if before.get("state", {}).get("UnitFileState") != after.get("UnitFileState"):
            discrepancies.append(f"{unit}: UnitFileState changed")
    gpu, gpu_failures = gpu_control_guard(pre["gpu"])
    discrepancies.extend(gpu_failures)
    return {
        "timestamp": now_iso(),
        "status": "POST_OK" if not discrepancies else "POST_CONFLICT",
        "units": states,
        "gpu": gpu,
        "discrepancies": discrepancies,
        "external_transitions": external_transitions,
    }


def validate_observer_preflight(result: Any) -> Optional[str]:
    if not isinstance(result, dict):
        return "observer preflight is not an object"
    if result.get("status") != "PASS":
        return "observer preflight status is not PASS"
    if result.get("returncode") != 0:
        return "observer preflight returncode is not zero"
    if result.get("runtime_path") != str(STATE_ROOT):
        return "observer runtime path mismatch"
    if result.get("runtime_is_directory") is not True or result.get("runtime_writable") is not True or result.get("runtime_executable") is not True:
        return "observer runtime directory permissions are not usable"
    if result.get("runtime_filesystem") != "tmpfs":
        return "observer runtime filesystem is not tmpfs"
    if result.get("observer_jsonl") != str(OBSERVER_JSONL):
        return "observer JSONL path mismatch"
    if result.get("observer_jsonl_parent") != str(STATE_ROOT):
        return "observer JSONL parent mismatch"
    if result.get("observer_jsonl_absent") is not True:
        return "observer JSONL is not absent before C1"
    if result.get("observer_sha256") != EXPECTED_HASHES["c1_observer.py"]:
        return "observer source hash mismatch"
    parsed = result.get("parsed")
    if not isinstance(parsed, dict) or parsed.get("status") != "OK":
        return "observer JSON preflight is not OK"
    if os.path.realpath(str(parsed.get("path"))) != os.path.realpath(str(STATE_ROOT)):
        return "observer reported a different runtime path"
    if parsed.get("filesystem") != "tmpfs":
        return "observer reported a different filesystem"
    for key in ("free_bytes", "total_bytes"):
        value = parsed.get(key)
        if isinstance(value, bool) or not isinstance(value, (int, float)) or value < 0:
            return f"observer reported invalid {key}"
    if result.get("stderr"):
        return "observer preflight wrote stderr"
    return None


def observer_check() -> Dict[str, Any]:
    env = os.environ.copy()
    env["XDG_RUNTIME_DIR"] = str(STATE_ROOT)
    command = ["/usr/bin/python3", str(OBSERVER), "--check-tmpfs"]
    try:
        result = run_read_command(command, timeout=10, env=env)
    except Exception as exc:  # noqa: BLE001 - observer failure is a gate failure
        result = {"returncode": None, "stdout": "", "stderr": f"{type(exc).__name__}: {exc}"}
    parsed: Any = None
    errors: List[str] = []
    try:
        parsed = json.loads(result.get("stdout", ""))
    except Exception as exc:  # noqa: BLE001
        errors.append(f"observer stdout JSON: {type(exc).__name__}: {exc}")
    try:
        observer_hash = sha256_file(OBSERVER)
    except Exception as exc:  # noqa: BLE001
        observer_hash = "NOT_AVAILABLE"
        errors.append(f"observer hash: {type(exc).__name__}: {exc}")
    if result.get("returncode") != 0:
        errors.append(f"observer returncode={result.get('returncode')}")
    if os.path.lexists(OBSERVER_JSONL):
        errors.append("observer JSONL already exists")
    candidate: Dict[str, Any] = {
        "status": "FAIL",
        "command": command,
        "returncode": result.get("returncode"),
        "stdout": result.get("stdout", ""),
        "stderr": result.get("stderr", ""),
        "parsed": parsed,
        "runtime_path": str(STATE_ROOT),
        "runtime_is_directory": os.path.isdir(STATE_ROOT),
        "runtime_writable": os.access(STATE_ROOT, os.W_OK | os.X_OK),
        "runtime_executable": os.access(STATE_ROOT, os.X_OK),
        "runtime_filesystem": parsed.get("filesystem") if isinstance(parsed, dict) else None,
        "observer_jsonl": str(OBSERVER_JSONL),
        "observer_jsonl_parent": str(OBSERVER_JSONL.parent),
        "observer_jsonl_absent": not os.path.lexists(OBSERVER_JSONL),
        "observer_sha256": observer_hash,
        "errors": errors,
    }
    if not errors:
        candidate["status"] = "PASS"
    validation_error = validate_observer_preflight(candidate)
    if validation_error:
        candidate["status"] = "FAIL"
        candidate.setdefault("errors", []).append(validation_error)
    return candidate


def parse_observer_jsonl(path: Path) -> Dict[str, Any]:
    result: Dict[str, Any] = {
        "path": str(path),
        "status": "NOT_AVAILABLE",
        "records": 0,
        "types": [],
        "c1_exit_returncode": None,
        "observer_end_returncode": None,
        "observer_error": None,
        "markers": [],
        "result_line": None,
    }
    if not path.exists():
        return result
    try:
        records: List[Dict[str, Any]] = []
        for line in path.read_text(encoding="utf-8", errors="replace").splitlines():
            if not line.strip():
                continue
            records.append(json.loads(line))
        types = [str(item.get("type")) for item in records]
        markers: List[str] = []
        result_line = None
        for item in records:
            typ = item.get("type")
            if typ == "c1_exit":
                result["c1_exit_returncode"] = item.get("return_code")
            elif typ == "observer_end":
                result["observer_end_returncode"] = item.get("return_code")
            elif typ == "observer_error":
                result["observer_error"] = {"type": item.get("error_type"), "message": item.get("message")}
            elif typ in {"c1_marker", "c1_output"}:
                text = str(item.get("line", ""))
                if text.startswith("marker:"):
                    markers.append(text)
                if "result:" in text:
                    result_line = text
        result.update(
            {
                "status": "OK",
                "records": len(records),
                "types": types,
                "markers": markers,
                "result_line": result_line,
            }
        )
    except Exception as exc:  # noqa: BLE001
        result["error"] = f"{type(exc).__name__}: {exc}"
    return result


def validate_pre_c1_launch(
    state: Dict[str, Any],
    state_path: Path,
    events_path: Path,
    pre: Dict[str, Any],
    provenance_ok: bool,
    provenance_now: Dict[str, Any],
    collision: Dict[str, Any],
    observer_min: Dict[str, Any],
    auth: Dict[str, Any],
    confirmation_ok: bool,
    tty_ok: bool,
) -> None:
    """Final read-only gate immediately before main-graphics may be launched."""
    failures: List[str] = []

    def require(condition: bool, reason: str) -> None:
        if not condition:
            failures.append(reason)

    try:
        state_error = validate_state(state)
        require(state_error is None, f"state schema: {state_error or 'FAIL'}")
        compat_error = validate_active_writer_compat(state)
        require(compat_error is None, f"writer compatibility: {compat_error or 'FAIL'}")
    except Exception as exc:  # noqa: BLE001 - any gate exception blocks C1
        failures.append(f"state validation exception: {type(exc).__name__}: {exc}")

    require(not state.get("state_write_errors"), "state_write_errors is non-empty")
    require(state.get("phase") == "C1", "phase is not C1")
    require(state.get("terminal") is False, "state is terminal before C1")
    require(state.get("post", {}).get("status") == "NOT_RUN", "POST is not NOT_RUN before C1")
    require(state.get("c1", {}).get("status") == "NOT_RUN", "C1 state is not NOT_RUN")
    require(state.get("c1", {}).get("executed") is False, "C1 executed flag is true before launch")
    require(state.get("c1", {}).get("formal_pass") is False, "C1 formal_pass is true before launch")
    for label in ("T_GUARD", "T_PRE"):
        require(state.get("guard", {}).get(label, {}).get("status") == "PASS", f"{label} is not PASS")
    require(state.get("guard", {}).get("T_POST", {}).get("status") == "NOT_RUN", "T_POST is not NOT_RUN before C1")

    require(isinstance(pre, dict) and pre.get("ok") is True, "PRE is not valid")
    if isinstance(pre, dict) and isinstance(pre.get("checks"), dict):
        require(all(item.get("status") == "PASS" for item in pre["checks"].values()), "a PRE check is not PASS")
    execution_gate = pre.get("execution_gate") if isinstance(pre, dict) else None
    require(isinstance(execution_gate, dict) and execution_gate.get("GO_C1") == "AVAILABLE", "execution gate is not AVAILABLE")
    ownership_proof = pre.get("ownership_proof") if isinstance(pre, dict) else None
    require(isinstance(ownership_proof, dict) and ownership_proof.get("status") == OWNERSHIP_FULL and ownership_proof.get("full_proof") is True, "ownership proof is not FULL")
    btrfs_gate = pre.get("btrfs_gate") if isinstance(pre, dict) else None
    require(isinstance(btrfs_gate, dict) and btrfs_gate.get("STATUS") == "MATCHED", "Btrfs identity is not matched")
    system_gates = pre.get("system_gate_contracts") if isinstance(pre, dict) else None
    require(isinstance(system_gates, dict) and bool(system_gates) and all(item.get("STATUS") == "PASS" for item in system_gates.values()), "system gates are not PASS")
    require(provenance_ok is True, "provenance recheck failed")
    require(isinstance(provenance_now, dict) and not provenance_now.get("mismatches"), "provenance mismatches remain")
    require(isinstance(collision, dict) and collision.get("status") == "PASS", "collision check failed")
    observer_state = state.get("observer_minimum_check")
    require(observer_state == observer_min, "durable observer state differs from pre-C1 observer result")
    observer_error = validate_observer_preflight(observer_min)
    require(observer_error is None, f"observer preflight invalid: {observer_error or 'FAIL'}")
    require(isinstance(auth, dict) and auth.get("status") == "OK", "sudo authorization is not OK")
    require(confirmation_ok is True, "RUN-C1 confirmation is not valid")
    require(tty_ok is True, "real TTY is not available")

    try:
        current_path, loaded = load_current_state()
        require(current_path is not None and os.path.realpath(current_path) == os.path.realpath(state_path), "CURRENT does not point to current state")
        require(isinstance(loaded, dict), "current state could not be loaded")
        if isinstance(loaded, dict):
            require(not loaded.get("_load_error"), f"current state load error: {loaded.get('_load_error')}")
            require(not loaded.get("_compatibility_error"), f"current writer mismatch: {loaded.get('_compatibility_error')}")
            require(loaded == state, "durable state differs from in-memory state")
            require(validate_state(loaded) is None, "durable state schema invalid")
            require(validate_active_writer_compat(loaded) is None, "durable state writer incompatible")
    except Exception as exc:  # noqa: BLE001
        failures.append(f"durable state read exception: {type(exc).__name__}: {exc}")

    try:
        require(events_path.is_file() and not events_path.is_symlink(), "events.jsonl is missing or unsafe")
        events = [json.loads(line) for line in read_text(events_path).splitlines() if line.strip()]
        require(state.get("events") == events, "state.events and events.jsonl differ")
    except Exception as exc:  # noqa: BLE001
        failures.append(f"events read exception: {type(exc).__name__}: {exc}")

    if failures:
        raise AutomatorError("PRE_C1_VALIDATION_FAILED: " + "; ".join(failures))


def launch_c1_after_pre_c1_validation(
    run_dir: Path,
    state: Dict[str, Any],
    state_path: Path,
    events_path: Path,
    pre: Dict[str, Any],
    provenance_ok: bool,
    provenance_now: Dict[str, Any],
    collision: Dict[str, Any],
    observer_min: Dict[str, Any],
    auth: Dict[str, Any],
    confirmation_ok: bool,
    tty_ok: bool,
    on_valid: Optional[Callable[[], None]] = None,
) -> Dict[str, Any]:
    validate_pre_c1_launch(
        state,
        state_path,
        events_path,
        pre,
        provenance_ok,
        provenance_now,
        collision,
        observer_min,
        auth,
        confirmation_ok,
        tty_ok,
    )
    if on_valid is not None:
        on_valid()
    return run_c1(run_dir, state, state_path, events_path)


def terminate_c1_child(child: Optional[subprocess.Popen], state: Dict[str, Any]) -> None:
    if child is None or child.poll() is not None:
        survivors = process_scan_for_existing_c1()
        if survivors:
            state["c1"]["remaining_c1_processes"] = survivors
        return
    child.terminate()
    try:
        child.wait(timeout=10)
    except subprocess.TimeoutExpired:
        state["c1"]["termination"] = "OBSERVER_TERMINATE_TIMEOUT_MANUAL_INTERVENTION_REQUIRED"
    except Exception as exc:  # noqa: BLE001
        state["c1"]["termination_error"] = f"{type(exc).__name__}: {exc}"
    survivors = process_scan_for_existing_c1()
    if survivors:
        state["c1"]["remaining_c1_processes"] = survivors


def run_c1(run_dir: Path, state: Dict[str, Any], state_path: Path, events_path: Path) -> Dict[str, Any]:
    stdout_path = run_dir / "c1.stdout"
    stderr_path = run_dir / "c1.stderr"
    env = os.environ.copy()
    env.update(
        {
            "XDG_RUNTIME_DIR": str(STATE_ROOT),
            "TMPDIR": str(run_dir / "tmp"),
            "XDG_CACHE_HOME": str(run_dir / "cache"),
        }
    )
    command = c1_command()
    child: Optional[subprocess.Popen] = None
    update_state(state, state_path, events_path, "c1_start", command=command, env_paths={k: env[k] for k in ("XDG_RUNTIME_DIR", "TMPDIR", "XDG_CACHE_HOME")})
    try:
        with stdout_path.open("wb") as stdout, stderr_path.open("wb") as stderr:
            child = subprocess.Popen(
                command,
                cwd=str(WORKLOAD_DIR),
                env=env,
                stdin=subprocess.DEVNULL,
                stdout=stdout,
                stderr=stderr,
                shell=False,
            )
            state["c1"]["pid"] = child.pid
            try:
                update_state(state, state_path, events_path, "c1_spawn", pid=child.pid)
            except BaseException:
                terminate_c1_child(child, state)
                raise
            started = monotonic()
            while child.poll() is None:
                if INTERRUPTED:
                    terminate_c1_child(child, state)
                    raise InterruptedRun("C1 child interrupted")
                if monotonic() - started > C1_MAX_SECONDS:
                    terminate_c1_child(child, state)
                    raise AutomatorError("C1 exceeded maximum runtime")
                time.sleep(0.2)
            returncode = child.returncode
            survivors = process_scan_for_existing_c1()
            if survivors:
                state["c1"]["remaining_c1_processes"] = survivors
                raise AutomatorError("C1/observer process remains after child exit")
    except BaseException as exc:  # noqa: BLE001 - child cleanup has priority
        if child is not None and child.poll() is None:
            terminate_c1_child(child, state)
        state["c1"]["status"] = "FAILED"
        state["c1"]["error"] = f"{type(exc).__name__}: {exc}"
        required_update_state(state, state_path, events_path, "c1_error", error=state["c1"]["error"])
        raise
    jsonl_path = OBSERVER_JSONL
    parsed = parse_observer_jsonl(jsonl_path)
    formal_checks = {
        "observer_exit_zero": returncode == 0,
        "jsonl_present": parsed.get("status") == "OK",
        "c1_exit_zero": parsed.get("c1_exit_returncode") == 0,
        "observer_end_zero": parsed.get("observer_end_returncode") == 0,
        "no_observer_error": parsed.get("observer_error") is None,
        "measure_start": any("measure_start" in item for item in parsed.get("markers", [])),
        "measure_end": any("measure_end" in item for item in parsed.get("markers", [])),
        "run_end": any("run_end" in item for item in parsed.get("markers", [])),
        "result_valid": "EJECUCIÓN_VÁLIDA" in str(parsed.get("result_line") or ""),
    }
    runtime_validated = all(formal_checks.values())
    state["c1"].update(
        {
            "status": "EXECUTED" if returncode == 0 else "FAILED",
            "executed": True,
            "returncode": returncode,
            "stdout": str(stdout_path),
            "stderr": str(stderr_path),
            "observer_jsonl": str(jsonl_path),
            "observer_parse": parsed,
            "formal_checks": formal_checks,
            "formal_pass": runtime_validated,
            "runtime_validated": False,
            "stdout_sha256": sha256_file(stdout_path) if stdout_path.exists() else None,
            "stderr_sha256": sha256_file(stderr_path) if stderr_path.exists() else None,
            "observer_jsonl_sha256": sha256_file(jsonl_path) if jsonl_path.exists() else None,
            "claims": {
                "A": "RUNTIME_RECORDED_SCIENTIFIC_VALIDITY_DEFERRED" if runtime_validated else "NOT_VALIDATED",
                "B": "PARTIAL_FREQUENCY_EFFECTIVE_NOT_AVAILABLE",
                "C": "PARTIAL_OWNERSHIP_PARTIAL",
                "D": "OBSERVED_PSI_CONTEXT_ONLY",
            },
        }
    )
    required_update_state(state, state_path, events_path, "c1_end", returncode=returncode, formal_pass=runtime_validated, runtime_validated=False, parsed=parsed)
    if returncode != 0:
        raise AutomatorError(f"C1 returned {returncode}")
    return state["c1"]


def finalize_state(state: Dict[str, Any], state_path: Path, events_path: Path, result: str, error: Optional[str] = None) -> None:
    state["terminal"] = True
    state["result"] = result
    state["error"] = error
    state["finished_at"] = now_iso()
    guard_ok = all(
        state.get("guard", {}).get(label, {}).get("status") == "PASS"
        for label in ("T_GUARD", "T_PRE", "T_POST")
    )
    pre = state.get("pre", {})
    execution_gate = pre.get("execution_gate") if isinstance(pre, dict) else None
    ownership_proof = pre.get("ownership_proof") if isinstance(pre, dict) else None
    btrfs_gate = pre.get("btrfs_gate") if isinstance(pre, dict) else None
    system_gates = pre.get("system_gate_contracts") if isinstance(pre, dict) else None
    public_valid = (
        state["c1"].get("executed")
        and state["c1"].get("formal_pass")
        and guard_ok
        and state["restore"].get("status") in {"RESTORE_OK", "RESTORE_NOT_NEEDED"}
        and state.get("post", {}).get("status") == "POST_OK"
        and isinstance(execution_gate, dict)
        and execution_gate.get("GO_C1") == "AVAILABLE"
        and isinstance(ownership_proof, dict)
        and ownership_proof.get("status") == OWNERSHIP_FULL
        and ownership_proof.get("full_proof") is True
        and isinstance(btrfs_gate, dict)
        and btrfs_gate.get("STATUS") == "MATCHED"
        and isinstance(system_gates, dict)
        and bool(system_gates)
        and all(item.get("STATUS") == "PASS" for item in system_gates.values())
        and result == "COMPLETED_RUNTIME_VALIDATED"
    )
    state["c1"]["runtime_validated"] = bool(public_valid)
    state["runtime_contract"] = runtime_contract_snapshot(materialized=True, validated=bool(public_valid))
    state["final_state"] = {
        **state_summary(state),
        "finished_at": state["finished_at"],
    }
    validation_error = validate_state(state)
    if validation_error:
        raise AutomatorError(f"cannot finalize invalid state: {validation_error}")
    compatibility_error = validate_active_writer_compat(state)
    if compatibility_error:
        raise AutomatorError(f"cannot finalize state: {compatibility_error}")
    update_state(state, state_path, events_path, "finalize", result=result, error=error)


def print_plan(pre: Dict[str, Any], plan: Dict[str, Any], precheck: Dict[str, Any]) -> None:
    print("C1_ISOLATION_AUTOMATOR DRY-RUN")
    print("mode=--dry-run")
    print("NO_WRITES=true")
    print("SUDO_INVOKED=false")
    print("SERVICES_MODIFIED=false")
    print("C1_EXECUTED=false")
    print(f"PRE_CURRENT_STATUS={'PASS' if precheck.get('ok') else 'FAIL'}")
    print(f"PRECHECK_ERRORS={json.dumps([k for k, v in precheck.get('checks', {}).items() if v.get('status') != 'PASS'], ensure_ascii=False)}")
    print("DETECTED_UNITS_AND_ACTIONS:")
    for item in plan["unit_actions"]:
        print(f"  {item['unit']}: {item['action']} {command_text(item['argv']) if item['argv'] else ''}")
    print(f"RUNTIME_NAMESPACE={RUNTIME_NAMESPACE}")
    print(f"RUNTIME_SCHEMA_VERSION={RUNTIME_SCHEMA_VERSION}")
    print(f"RUNTIME_NAMESPACE_ACTIVATED_AT={RUNTIME_NAMESPACE_ACTIVATED_AT}")
    print(f"RUNTIME_ROOT={STATE_ROOT}")
    legacy = precheck.get("checks", {}).get("historical_legacy_runtime", {}).get("detail", {})
    print(f"LEGACY_RUNTIME_ROOT={LEGACY_STATE_ROOT}")
    print(f"LEGACY_RUNTIME_STATUS={legacy.get('status', 'NOT_AVAILABLE')}")
    print(f"LEGACY_RUNTIME_CLASSIFICATION={legacy.get('classification', 'NOT_AVAILABLE')}")
    print(f"LEGACY_RUNTIME_SCHEMA_STATUS={legacy.get('legacy_schema_status', 'NOT_AVAILABLE')}")
    print(f"LEGACY_RUNTIME_PRESERVED={legacy.get('preserved', 'NOT_AVAILABLE')}")
    print("RUNTIME_FILES:")
    print("  <STATE_ROOT>/CURRENT")
    print("  <STATE_ROOT>/runs/<run-id>/state.json")
    print("  <STATE_ROOT>/runs/<run-id>/events.jsonl")
    print("  <STATE_ROOT>/runs/<run-id>/t_guard.jsonl")
    print("  <STATE_ROOT>/runs/<run-id>/t_pre.jsonl")
    print("  <STATE_ROOT>/runs/<run-id>/t_post.jsonl")
    print("  <STATE_ROOT>/c1-observer-v1.jsonl (only if --run later passes)")
    print(f"T_GUARD={GUARD_SECONDS}s; T_PRE={T_PRE_SECONDS}s; T_POST={T_POST_SECONDS}s")
    print(f"C1_COMMAND={plan['c1_command_text']}")
    print("RESTORE_PLAN=start only units with PRE active and stop attempted by this execution")
    print("POST_PLAN=compare unit ActiveState/UnitFileState and GPU control readback against PRE")
    print(f"OBSERVER={OBSERVER}")
    print(f"SCRIPT_SHA256={sha256_file(Path(__file__).resolve())}")
    print(f"DOC={DOC}")


def runtime_dependent_preflight_status() -> Dict[str, str]:
    return {
        "status": "DEFERRED_RUNTIME_REQUIRED",
        "observer_preflight": "NOT_RUN",
        "reason": "authorized runtime v2 initialization occurs only in --run",
        "runtime_root": str(STATE_ROOT),
    }


def cmd_dry_run(_args: argparse.Namespace) -> int:
    pre = collect_precheck()
    plan = planned_actions(pre)
    dependent = runtime_dependent_preflight_status()
    print_plan(pre, plan, pre)
    print("PRECHECK_SCOPE=STATIC_DYNAMIC")
    print("OWNERSHIP_STATUS=PARTIAL")
    print("GO_C1=NOT_AVAILABLE")
    print("SYSTEM_GATES=DEFINED_PENDING_EXECUTION")
    print("BTRFS_GATE=CONFLICT")
    print("RUNTIME_MATERIALIZED=NO")
    print("RUNTIME_VALIDATED=NO")
    print("RESTORE_EXECUTED=NO")
    print("RESTORE_VALIDATED=NO")
    print(f"RUNTIME_DEPENDENT_CHECKS={dependent['status']}")
    print(f"OBSERVER_PREFLIGHT={dependent['observer_preflight']}")
    print(f"OBSERVER_PREFLIGHT_REASON={dependent['reason']}")
    return 0


def cmd_prepare(_args: argparse.Namespace) -> int:
    checks: Dict[str, Dict[str, Any]] = {}
    script = Path(__file__).resolve()
    checks["script"] = {"status": "PASS" if script.is_file() else "FAIL", "path": str(script)}
    checks["executable"] = {"status": "PASS" if os.access(script, os.X_OK) else "FAIL"}
    checks["documentation"] = {"status": "PASS" if DOC.is_file() else "FAIL", "path": str(DOC)}
    for command in ("python3", "systemctl", "sudo", "flock", "sha256sum", "readelf", "git"):
        checks[f"command:{command}"] = {"status": "PASS" if shutil.which(command) else "FAIL", "path": shutil.which(command)}
    checks["runtime_tmpfs"] = {"status": "PASS" if fs_type(RUNTIME_DIR) == "tmpfs" else "FAIL", "path": str(RUNTIME_DIR)}
    checks["namespace_invariant"] = {"status": "PASS" if namespace_paths_separate() else "FAIL"}
    legacy = legacy_runtime_inventory()
    checks["historical_legacy_runtime"] = {
        "status": "FAIL" if legacy.get("blocking") else "PASS",
        "detail": legacy,
    }
    ok = all(item["status"] == "PASS" for item in checks.values())
    print("C1_ISOLATION_AUTOMATOR PREPARE")
    print("NO_WRITES=true")
    print("SUDO_INVOKED=false")
    print(f"VERSION={VERSION}")
    print(f"CONTRACT_VERSION={CONTRACT_VERSION}")
    print("IMPLEMENTATION_STATUS=PARTIAL")
    print("OWNERSHIP_STATUS=PARTIAL")
    print("GO_C1=NOT_AVAILABLE")
    print("RUNTIME_MATERIALIZED=NO")
    print("RUNTIME_VALIDATED=NO")
    print("RESTORE_EXECUTED=NO")
    print("RESTORE_VALIDATED=NO")
    print(f"RUNTIME_NAMESPACE={RUNTIME_NAMESPACE}")
    print(f"RUNTIME_SCHEMA_VERSION={RUNTIME_SCHEMA_VERSION}")
    print(f"RUNTIME_NAMESPACE_ACTIVATED_AT={RUNTIME_NAMESPACE_ACTIVATED_AT}")
    print(f"RUNTIME_ROOT={STATE_ROOT}")
    print(f"LEGACY_RUNTIME_ROOT={LEGACY_STATE_ROOT}")
    print(f"LEGACY_RUNTIME_STATUS={legacy.get('status', 'NOT_AVAILABLE')}")
    print(f"LEGACY_RUNTIME_CLASSIFICATION={legacy.get('classification', 'NOT_AVAILABLE')}")
    print(f"LEGACY_RUNTIME_SCHEMA_STATUS={legacy.get('legacy_schema_status', 'NOT_AVAILABLE')}")
    print(f"LEGACY_RUNTIME_PRESERVED={legacy.get('preserved', 'NOT_AVAILABLE')}")
    dependent = runtime_dependent_preflight_status()
    print("PRECHECK_SCOPE=STATIC_ONLY")
    print(f"RUNTIME_DEPENDENT_CHECKS={dependent['status']}")
    print(f"OBSERVER_PREFLIGHT={dependent['observer_preflight']}")
    print(f"OBSERVER_PREFLIGHT_REASON={dependent['reason']}")
    print(f"SCRIPT_SHA256={sha256_file(script)}")
    print(f"DOC_SHA256={sha256_file(DOC) if DOC.exists() else 'NOT_AVAILABLE'}")
    print(json.dumps(checks, ensure_ascii=False, indent=2, sort_keys=True))
    print(f"PREPARE_STATUS={'PASS' if ok else 'FAIL'}")
    return 0 if ok else 1


def cmd_status(_args: argparse.Namespace) -> int:
    legacy = legacy_runtime_inventory()
    print(f"RUNTIME_NAMESPACE={RUNTIME_NAMESPACE}")
    print(f"CONTRACT_VERSION={CONTRACT_VERSION}")
    print(f"RUNTIME_SCHEMA_VERSION={RUNTIME_SCHEMA_VERSION}")
    print(f"RUNTIME_NAMESPACE_ACTIVATED_AT={RUNTIME_NAMESPACE_ACTIVATED_AT}")
    print(f"LEGACY_RUNTIME_ROOT={LEGACY_STATE_ROOT}")
    print(f"LEGACY_RUNTIME_STATUS={legacy.get('status', 'NOT_AVAILABLE')}")
    print(f"LEGACY_RUNTIME_CLASSIFICATION={legacy.get('classification', 'NOT_AVAILABLE')}")
    print(f"LEGACY_RUNTIME_SCHEMA_STATUS={legacy.get('legacy_schema_status', 'NOT_AVAILABLE')}")
    print(f"LEGACY_RUNTIME_PRESERVED={legacy.get('preserved', 'NOT_AVAILABLE')}")
    path, state = load_current_state()
    if path is None:
        print("RUNTIME_STATE=ABSENT")
        print("ACTIVE_RUNTIME_STATE=NONE")
        print("RUNTIME_DESIGNED=YES")
        print("RUNTIME_MATERIALIZED=NO")
        print("RUNTIME_VALIDATED=NO")
        print("RESTORE_PLANNED=DEFINED_FOR_DECLARED_SCOPE")
        print("RESTORE_EXECUTED=NO")
        print("RESTORE_VALIDATED=NO")
        print("C1_STATUS=DEFERRED")
        print("C1_RUNTIME_VALIDATED=NO")
        return 2 if legacy.get("blocking") else 0
    if state is None:
        print(f"RUNTIME_STATE={path}")
        print(f"ACTIVE_RUNTIME_STATE={path}")
        print("ACTIVE_RUNTIME_STATE_STATUS=UNREADABLE_OR_INCOMPLETE")
        return 2
    if state.get("_load_error"):
        print(f"RUNTIME_STATE={path}")
        print(f"ACTIVE_RUNTIME_STATE={path}")
        print(f"ACTIVE_RUNTIME_STATE_STATUS=INVALID: {state['_load_error']}")
        return 2
    if state.get("_compatibility_error"):
        print(f"RUNTIME_STATE={path}")
        print(f"ACTIVE_RUNTIME_STATE={path}")
        print(f"ACTIVE_RUNTIME_STATE_STATUS=WRITER_MISMATCH: {state['_compatibility_error']}")
        print(f"RECORDED_AUTOMATOR_VERSION={state.get('automator_version')}")
        print(f"RECORDED_AUTOMATOR_SHA256={state.get('automator_sha256')}")
        return 2
    incomplete = state_is_incomplete(state)
    print(f"RUNTIME_STATE={path}")
    print(f"ACTIVE_RUNTIME_STATE={path}")
    print(f"ACTIVE_RUNTIME_STATE_STATUS={'INCOMPLETE_RECOVERABLE' if incomplete else 'TERMINAL'}")
    for key in ("run_id", "phase", "result", "terminal", "started_at", "finished_at"):
        print(f"{key.upper()}={state.get(key)}")
    print(f"RESTORE_STATUS={state.get('restore', {}).get('status')}")
    print(f"RESTORE_PLANNED={state.get('restore_contract', {}).get('RESTORE_PLANNED')}")
    print(f"RESTORE_EXECUTED={state.get('restore_contract', {}).get('RESTORE_EXECUTED')}")
    print(f"RESTORE_VALIDATED={state.get('restore_contract', {}).get('RESTORE_VALIDATED')}")
    print(f"RUNTIME_DESIGNED={state.get('runtime_contract', {}).get('RUNTIME_DESIGNED')}")
    print(f"RUNTIME_MATERIALIZED={state.get('runtime_contract', {}).get('RUNTIME_MATERIALIZED')}")
    print(f"RUNTIME_VALIDATED={state.get('runtime_contract', {}).get('RUNTIME_VALIDATED')}")
    print(f"C1_STATUS={state.get('c1', {}).get('status')}")
    print(f"C1_RUNTIME_VALIDATED={public_runtime_validated(state)}")
    if incomplete:
        print("NEXT_ACTION=MANUAL_REVIEW_REQUIRED; --status does not auto-restore")
    return 2 if incomplete or legacy.get("blocking") else 0


def cmd_run(_args: argparse.Namespace) -> int:
    global INTERRUPTED
    INTERRUPTED = False
    set_signal_handlers()
    if not sys.stdin.isatty() or not sys.stdout.isatty():
        print("ABORT: --run requires an interactive TTY for normal sudo authentication", file=sys.stderr)
        return 2
    try:
        confirmation = input("Type RUN-C1 to authorize the minimal runtime workflow: ")
    except EOFError:
        print("ABORT: no interactive confirmation", file=sys.stderr)
        return 2
    if confirmation != "RUN-C1":
        print("ABORT: confirmation mismatch; no changes", file=sys.stderr)
        return 2

    if not namespace_paths_separate():
        print("EXECUTION_DECISION=BLOCKED_NAMESPACE_INVARIANT")
        return 2

    pre = collect_precheck()
    execution_gate = pre.get("execution_gate") if isinstance(pre, dict) else None
    if isinstance(execution_gate, dict) and execution_gate.get("GO_C1") != "AVAILABLE":
        print("EXECUTION_DECISION=NO_GO_PRE")
        print("GO_C1=NOT_AVAILABLE")
        print(f"BLOCKERS={json.dumps(execution_gate.get('BLOCKERS', []), ensure_ascii=False)}")
        return 2

    artifacts = RuntimeArtifacts()
    with RuntimeLock(artifacts) as runtime:
        runtime_initialized = False
        try:
            if any(
                pre["checks"].get(name, {}).get("status") == "FAIL"
                for name in ("no_incomplete_runtime_state", "no_orphan_runtime_runs", "historical_legacy_runtime")
            ):
                cleanup_errors = runtime.cleanup_initialization()
                if cleanup_errors:
                    print(f"RUNTIME_INITIALIZATION_CLEANUP_ERRORS={json.dumps(cleanup_errors, ensure_ascii=False)}", file=sys.stderr)
                print("EXECUTION_DECISION=BLOCKED_INCOMPLETE_STATE")
                print("CURRENT_STATE_PRESERVED=true")
                return 2
            run_context = initialize_authorized_runtime_state(pre, artifacts)
            run_dir = run_context["run_dir"]
            state_path = run_context["state_path"]
            events_path = run_context["events_path"]
            state = run_context["state"]
            runtime_initialized = True
        except BaseException as exc:
            if not runtime_initialized:
                cleanup_errors = runtime.cleanup_initialization()
                if cleanup_errors:
                    print(f"RUNTIME_INITIALIZATION_CLEANUP_ERRORS={json.dumps(cleanup_errors, ensure_ascii=False)}", file=sys.stderr)
            if isinstance(exc, AutomatorError):
                raise
            raise AutomatorError(f"authorized runtime initialization failed: {type(exc).__name__}: {exc}") from exc

        if not pre["ok"]:
            state["phase"] = "ABORTED_PRE"
            state["result"] = "ABORTED_PRE"
            state["restore"] = {
                "status": "RESTORE_ABORTED_NO_CHANGES",
                "attempted_units": [],
                "results": {},
                "failures": [],
            }
            state["restore_contract"] = restore_contract_transition(state.get("restore_contract", restore_contract_snapshot()), "NOT_NEEDED")
            finalize_state(state, state_path, events_path, "ABORTED_PRE", "precheck failed")
            print("EXECUTION_DECISION=BLOCKED_PRE")
            return 2

        observer_min: Optional[Dict[str, Any]] = None
        observer_failure: Optional[BaseException] = None
        try:
            observer_min = observer_check()
            state["observer_minimum_check"] = observer_min
            required_update_state(state, state_path, events_path, "observer_check", result=observer_min)
        except BaseException as exc:  # noqa: BLE001 - observer/persistence failure is fail-closed
            observer_failure = exc
            state["error"] = f"{type(exc).__name__}: {exc}"
        if observer_failure is not None or not isinstance(observer_min, dict) or observer_min.get("status") != "PASS":
            state["restore"] = {
                "status": "RESTORE_ABORTED_NO_CHANGES",
                "attempted_units": [],
                "results": {},
                "failures": [],
            }
            state["restore_contract"] = restore_contract_transition(state.get("restore_contract", restore_contract_snapshot()), "NOT_NEEDED")
            error = state.get("error") or "observer minimum check failed"
            try:
                finalize_state(state, state_path, events_path, "ABORTED_OBSERVER_CHECK", error)
            except BaseException as finalize_exc:  # noqa: BLE001 - no C1 is allowed on any failure
                print(f"OBSERVER_FAILURE_PERSISTENCE_FAILED={type(finalize_exc).__name__}: {finalize_exc}", file=sys.stderr)
            print("EXECUTION_DECISION=ABORTED_OBSERVER_CHECK")
            return 2

        touched: List[Dict[str, Any]] = []
        c1_started = False
        post_done = False
        failure: Optional[BaseException] = None
        run_rc = 1
        run_message = "EXECUTION_DECISION=INCOMPLETE"
        try:
            auth = sudo_authenticate()
            state["sudo"] = auth
            update_state(state, state_path, events_path, "sudo_authentication", result=auth)
            if auth.get("status") != "OK":
                raise AutomatorError("normal interactive sudo authentication failed")

            state["phase"] = "ISOLATING"
            update_state(state, state_path, events_path, "isolation_begin")
            apply_isolation(pre, state, state_path, events_path, touched)
            state["phase"] = "GUARD"
            update_state(state, state_path, events_path, "isolation_complete", units=[item["unit"] for item in touched])
            if not run_guard_window("T_GUARD", GUARD_SECONDS, pre, touched, run_dir, state, state_path, events_path):
                raise AutomatorError("T_GUARD failed")
            if not run_guard_window("T_PRE", T_PRE_SECONDS, pre, touched, run_dir, state, state_path, events_path):
                raise AutomatorError("T_PRE failed")
            provenance_ok, provenance_now = provenance_unchanged(pre)
            state["provenance_recheck_before_c1"] = provenance_now
            required_update_state(state, state_path, events_path, "provenance_recheck", ok=provenance_ok, result=provenance_now)
            if not provenance_ok:
                raise AutomatorError("provenance changed before C1")
            collision = prelaunch_collision_check()
            state["prelaunch_collision_check"] = collision
            required_update_state(state, state_path, events_path, "prelaunch_collision_check", result=collision)
            if collision.get("status") != "PASS":
                raise AutomatorError("C1/observer collision appeared before launch")
            state["phase"] = "C1"
            required_update_state(state, state_path, events_path, "c1_ready", phase=state["phase"])

            def mark_c1_started() -> None:
                nonlocal c1_started
                c1_started = True

            launch_c1_after_pre_c1_validation(
                run_dir,
                state,
                state_path,
                events_path,
                pre,
                provenance_ok,
                provenance_now,
                collision,
                observer_min,
                auth,
                confirmation_ok=confirmation == "RUN-C1",
                tty_ok=sys.stdin.isatty() and sys.stdout.isatty(),
                on_valid=mark_c1_started,
            )
            if not run_guard_window("T_POST", T_POST_SECONDS, pre, touched, run_dir, state, state_path, events_path):
                failure = AutomatorError("T_POST failed")
            post_done = True
        except BaseException as exc:  # noqa: BLE001 - restore is the priority
            failure = exc
            state["error"] = f"{type(exc).__name__}: {exc}"
            update_state(state, state_path, events_path, "execution_failure", error=state["error"], phase=state["phase"])
        finally:
            if c1_started and not post_done:
                try:
                    run_guard_window("T_POST", T_POST_SECONDS, pre, touched, run_dir, state, state_path, events_path)
                except BaseException as post_exc:  # noqa: BLE001
                    state["post_guard_error"] = f"{type(post_exc).__name__}: {post_exc}"
            manual_c1 = bool(state["c1"].get("remaining_c1_processes"))
            termination_manual = "MANUAL_INTERVENTION_REQUIRED" in str(state["c1"].get("termination", ""))
            manual_intervention = manual_c1 or termination_manual or bool(state.get("manual_intervention_required"))
            if manual_intervention:
                state["restore"] = {
                    "status": "MANUAL_INTERVENTION_REQUIRED",
                    "attempted_units": [item["unit"] for item in touched],
                    "results": {},
                    "failures": ["runtime operation may still be in flight; manual readback required"],
                }
                state["post"] = {"status": "MANUAL_INTERVENTION_REQUIRED"}
                state["restore_contract"] = restore_contract_transition(state.get("restore_contract", restore_contract_snapshot()), "FAIL")
                safe_update_state(state, state_path, events_path, "manual_intervention", reason=state.get("manual_intervention_required", "C1 process remains"))
            else:
                if touched:
                    state["phase"] = "RESTORING"
                    safe_update_state(state, state_path, events_path, "restore_begin", units=[item["unit"] for item in touched])
                    restore = restore_units(touched, state, state_path, events_path)
                    state["restore"] = restore
                    safe_update_state(state, state_path, events_path, "restore_end", result=restore)
                else:
                    state["restore"] = {"status": "RESTORE_NOT_NEEDED", "attempted_units": [], "results": {}, "failures": []}
                if state.get("manual_intervention_required"):
                    state["post"] = {"status": "MANUAL_INTERVENTION_REQUIRED"}
                    safe_update_state(state, state_path, events_path, "manual_intervention", reason=state["manual_intervention_required"])
                else:
                    try:
                        post = postcheck(pre, touched)
                        state["post"] = post
                        settle_restore_contract(state, post.get("status"))
                        safe_update_state(state, state_path, events_path, "postcheck", result=post)
                    except BaseException as post_exc:  # noqa: BLE001
                        post = {"status": "POSTCHECK_FAILED", "error": f"{type(post_exc).__name__}: {post_exc}"}
                        state["post"] = post
                        settle_restore_contract(state, post.get("status"))
                        safe_update_state(state, state_path, events_path, "postcheck_failed", error=post["error"])
            if failure is not None:
                state["c1"]["runtime_validated"] = False
                result = "ABORTED_FAILURE_RESTORE_REQUIRED" if state["restore"].get("status") not in {"RESTORE_OK", "RESTORE_NOT_NEEDED"} else "ABORTED_FAILURE_RESTORED"
                finalize_state(state, state_path, events_path, result, f"{type(failure).__name__}: {failure}")
                run_rc = 2
                run_message = f"EXECUTION_DECISION={result}"
            elif (
                state["c1"].get("formal_pass")
                and state["restore"].get("status") in {"RESTORE_OK", "RESTORE_NOT_NEEDED"}
                and post.get("status") == "POST_OK"
            ):
                finalize_state(state, state_path, events_path, "COMPLETED_RUNTIME_VALIDATED", None)
                run_rc = 0
                run_message = "C1_RUNTIME_VALIDATED=YES"
            else:
                finalize_state(state, state_path, events_path, "COMPLETED_PARTIAL_OR_CONFLICT", "formal C1 or POST/restore criteria not all satisfied")
                run_rc = 1
                run_message = "C1_RUNTIME_VALIDATED=NO"
        print(run_message)
        return run_rc


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="Auditable runtime-only C1 isolation workflow")
    group = parser.add_mutually_exclusive_group(required=True)
    group.add_argument("--dry-run", action="store_true", help="read-only plan; no state, sudo, services or C1")
    group.add_argument("--prepare", action="store_true", help="static/read-only preparation checks; no state, sudo or C1")
    group.add_argument("--status", action="store_true", help="read last runtime state; no automatic restore")
    group.add_argument("--run", action="store_true", help="real workflow; requires TTY, confirmation and interactive sudo")
    return parser


def main(argv: Optional[Sequence[str]] = None) -> int:
    args = build_parser().parse_args(argv)
    try:
        if args.dry_run:
            return cmd_dry_run(args)
        if args.prepare:
            return cmd_prepare(args)
        if args.status:
            return cmd_status(args)
        return cmd_run(args)
    except AutomatorError as exc:
        print(f"AUTOMATOR_ERROR: {exc}", file=sys.stderr)
        return 2
    except KeyboardInterrupt:
        print("AUTOMATOR_ERROR: interrupted", file=sys.stderr)
        return 130


if __name__ == "__main__":
    raise SystemExit(main())
