#!/usr/bin/env python3
"""Pure/state tests for the versioned C1 isolation automator.

No test invokes sudo, systemctl stop/start/restart, C1, the observer runtime,
or a live system probe.  Runtime-file tests use temporary directories only;
the historical residual checks are read-only.
"""
from __future__ import annotations

import ast
import contextlib
import hashlib
import io
import importlib.util
import json
import os
import tempfile
import unittest
from pathlib import Path
from unittest import mock


SCRIPT = Path(__file__).resolve().parents[1] / "c1_isolation_automator.py"
SPEC = importlib.util.spec_from_file_location("c1_isolation_automator_under_test", SCRIPT)
assert SPEC and SPEC.loader
automator = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(automator)


def synthetic_pre() -> dict:
    units = {}
    for spec in automator.UNIT_SPECS:
        units[spec["unit"]] = {
            "scope": spec["scope"],
            "kind": spec["kind"],
            "pre_active": False,
            "state": {
                "ActiveState": "inactive",
                "SubState": "dead",
                "UnitFileState": "static" if spec["kind"] == "service" else "enabled",
                "_returncode": 0,
                "_valid": True,
            },
        }
    return {
        "ok": True,
        "timestamp": "2026-01-01T00:00:00+00:00",
        "hostname": automator.EXPECTED_HOST,
        "kernel": automator.EXPECTED_KERNEL,
        "boot_id": {"status": "OK", "value": "test"},
        "checks": {},
        "gpu": {"controls": {}, "identity": {}},
        "provenance": {},
        "dstate": {"count": 0, "processes": []},
        "procs": {"procs_running": 1, "procs_blocked": 0},
        "pressure": {},
        "diskstats": {},
        "units": units,
        "ownership": {"status": "PARTIAL"},
    }


def new_state(run_id: str = "20260101T000000Z-1") -> dict:
    pre = synthetic_pre()
    return automator.initial_state(run_id, Path("/tmp/not-used"), pre, automator.planned_actions(pre))


def durable_pre_c1_fixture(root: Path) -> dict:
    run_id = "20260101T000000Z-20"
    pre = synthetic_pre()
    pre["checks"] = {"fixture_gate": {"status": "PASS"}}
    state = automator.initial_state(run_id, root / "runs" / run_id, pre, automator.planned_actions(pre))
    legacy_root = root.parent / "legacy"
    state["parent_namespace_path"] = str(legacy_root)
    state["historical_namespace_path"] = str(legacy_root)
    state["legacy_reference"]["path"] = str(legacy_root)
    set_guard(state, "T_GUARD", root=root)
    set_guard(state, "T_PRE", root=root)
    state["phase"] = "C1"
    state["pre"] = pre
    observer_parsed = {"status": "OK", "path": str(root), "filesystem": "tmpfs", "free_bytes": 1024, "total_bytes": 2048}
    observer_result = {
        "status": "PASS",
        "command": ["/usr/bin/python3", str(automator.OBSERVER), "--check-tmpfs"],
        "returncode": 0,
        "stdout": json.dumps(observer_parsed, separators=(",", ":")),
        "stderr": "",
        "parsed": observer_parsed,
        "runtime_path": str(root),
        "runtime_is_directory": True,
        "runtime_writable": True,
        "runtime_executable": True,
        "runtime_filesystem": "tmpfs",
        "observer_jsonl": str(root / "c1-observer-v1.jsonl"),
        "observer_jsonl_parent": str(root),
        "observer_jsonl_absent": True,
        "observer_sha256": automator.sha256_file(automator.OBSERVER),
        "errors": [],
    }
    state["observer_minimum_check"] = observer_result
    state["provenance_recheck_before_c1"] = {"mismatches": []}
    state["prelaunch_collision_check"] = {"status": "PASS", "processes": [], "observer_jsonl_exists": False}
    state["sudo"] = {"status": "OK", "command": "sudo -v", "returncode": 0}
    runs_root = root / "runs"
    run_dir = runs_root / run_id
    run_dir.mkdir(parents=True, mode=0o700)
    os.chmod(root, 0o700)
    os.chmod(runs_root, 0o700)
    os.chmod(run_dir, 0o700)
    state_path = run_dir / "state.json"
    events_path = run_dir / "events.jsonl"
    automator.required_update_state(state, state_path, events_path, "c1_ready", phase="C1")
    current = root / "CURRENT"
    current.write_text(run_id + "\n", encoding="utf-8")
    os.chmod(current, 0o600)
    return {
        "root": root,
        "run_dir": run_dir,
        "state": state,
        "state_path": state_path,
        "events_path": events_path,
        "pre": pre,
        "provenance": {"mismatches": []},
        "collision": {"status": "PASS", "processes": [], "observer_jsonl_exists": False},
        "observer": observer_result,
        "auth": {"status": "OK"},
    }


@contextlib.contextmanager
def active_runtime_patches(root: Path, legacy_root: Path):
    with mock.patch.object(automator, "STATE_ROOT", root), mock.patch.object(automator, "LEGACY_STATE_ROOT", legacy_root), mock.patch.object(automator, "LOCK_PATH", root / ".lock"), mock.patch.object(automator, "CURRENT_POINTER", root / "CURRENT"), mock.patch.object(automator, "OBSERVER_JSONL", root / "c1-observer-v1.jsonl"):
        yield


def write_json(path: Path, payload: dict) -> None:
    path.write_text(json.dumps(payload, ensure_ascii=False, sort_keys=True, indent=2) + "\n", encoding="utf-8")


def sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def observer_output(root: Path, path: str | None = None, status: str = "OK") -> dict:
    parsed = {"status": status, "path": path or str(root), "filesystem": "tmpfs", "free_bytes": 1024, "total_bytes": 2048}
    return {"returncode": 0, "stdout": json.dumps(parsed, separators=(",", ":")), "stderr": ""}


def function_node(tree: ast.AST, name: str):
    for node in ast.walk(tree):
        if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)) and node.name == name:
            return node
    raise AssertionError(f"function not found: {name}")


def set_guard(state: dict, label: str, status: str = "PASS", root: Path | None = None) -> None:
    state["guard"][label] = {
        "status": status,
        "reason": None if status == "PASS" else f"test-{status.lower()}",
        "sample_count": 1,
        "elapsed_seconds": 0.1,
        "log": str(root / f"{label.lower()}.jsonl") if root else f"/tmp/{label.lower()}.jsonl",
    }


def update_state_in_temp(state: dict, event: str, **fields) -> None:
    with tempfile.TemporaryDirectory(prefix="c1-automator-test-") as temp:
        root = Path(temp)
        automator.update_state(state, root / "state.json", root / "events.jsonl", event, **fields)


def legacy_fixture(root: Path) -> dict:
    run_id = automator.LEGACY_RUN_ID
    runs = root / "runs"
    run_dir = runs / run_id
    run_dir.mkdir(parents=True, mode=0o700)
    (run_dir / "tmp").mkdir(mode=0o700)
    (run_dir / "cache").mkdir(mode=0o700)
    os.chmod(root, 0o700)
    os.chmod(runs, 0o700)
    os.chmod(run_dir, 0o700)
    os.chmod(run_dir / "tmp", 0o700)
    os.chmod(run_dir / "cache", 0o700)
    events = [
        {"event": "run_created", "timestamp": "2026-01-01T00:00:00+00:00"},
        {"event": "finalize", "timestamp": "2026-01-01T00:00:01+00:00", "result": "ABORTED_FAILURE_RESTORED"},
    ]
    state = {
        "schema_version": 1,
        "automator_version": "1.0.0",
        "run_id": run_id,
        "phase": "ISOLATING",
        "terminal": True,
        "result": "ABORTED_FAILURE_RESTORED",
        "error": "TypeError: update_state() got multiple values for argument 'state'",
        "actions": [],
        "guard": {"status": "NOT_RUN", "T_GUARD": {}, "T_PRE": {}, "T_POST": {}},
        "c1": {
            "status": "NOT_RUN",
            "executed": False,
            "formal_pass": False,
            "observer_jsonl": None,
        },
        "restore": {"status": "RESTORE_NOT_NEEDED", "attempted_units": []},
        "post": {"status": "POST_CONFLICT"},
        "pre": {"ok": True},
        "events": events,
    }
    write_json(run_dir / "state.json", state)
    (run_dir / "events.jsonl").write_text(
        "".join(json.dumps(item, sort_keys=True) + "\n" for item in events), encoding="utf-8"
    )
    os.chmod(run_dir / "state.json", 0o600)
    os.chmod(run_dir / "events.jsonl", 0o644)
    (root / ".lock").write_text("490709\n", encoding="utf-8")
    os.chmod(root / ".lock", 0o600)
    current = root / "CURRENT"
    current.write_text(run_id + "\n", encoding="utf-8")
    os.chmod(current, 0o600)
    return {
        run_id: {
            "state_sha256": sha256(run_dir / "state.json"),
            "events_sha256": sha256(run_dir / "events.jsonl"),
            "current_sha256": sha256(current),
        }
    }


class AutomatorStateTests(unittest.TestCase):
    def test_A_initial_new_state_and_namespace_metadata_are_valid(self) -> None:
        state = new_state()
        self.assertIsNone(automator.validate_state(state))
        self.assertEqual(state["automator_version"], automator.VERSION)
        self.assertEqual(state["automator_sha256"], automator.sha256_file(SCRIPT))
        self.assertEqual(state["script_sha256"], state["automator_sha256"])
        self.assertEqual(state["runtime_schema_version"], automator.RUNTIME_SCHEMA_VERSION)
        self.assertEqual(state["runtime_namespace"], "c1-isolation-automator-v2")
        self.assertEqual(state["parent_namespace"], "c1-isolation-automator")
        self.assertEqual(state["parent_namespace_path"], str(automator.LEGACY_STATE_ROOT))
        self.assertEqual(state["historical_namespace"], "c1-isolation-automator")
        self.assertEqual(state["historical_namespace_path"], str(automator.LEGACY_STATE_ROOT))
        self.assertEqual(state["runtime_namespace_activated_at"], automator.RUNTIME_NAMESPACE_ACTIVATED_AT)
        self.assertIsNotNone(state["run_created_at"])
        self.assertEqual(state["legacy_reference"]["classification"], automator.LEGACY_CLASSIFICATION)
        self.assertIsNone(state["final_state"])
        self.assertEqual(state["contract_version"], automator.CONTRACT_VERSION)
        self.assertFalse(state["runtime_contract"]["RUNTIME_MATERIALIZED"])
        self.assertFalse(state["restore_contract"]["RESTORE_EXECUTED"])
        self.assertIn("ownership", state["contract_manifest"])
        self.assertEqual(state["events"], [])
        self.assertTrue(state["initial_state"]["guard"]["T_GUARD"] == "NOT_RUN")

    def test_observer_invalid_json_fails_closed(self) -> None:
        with tempfile.TemporaryDirectory(prefix="c1-observer-test-") as temp:
            root = Path(temp)
            with mock.patch.object(automator, "STATE_ROOT", root), mock.patch.object(automator, "OBSERVER_JSONL", root / "c1-observer-v1.jsonl"), mock.patch.object(automator, "run_read_command", return_value={"returncode": 0, "stdout": "not-json", "stderr": ""}):
                result = automator.observer_check()
        self.assertEqual(result["status"], "FAIL")
        self.assertIsNotNone(automator.validate_observer_preflight(result))

    def test_observer_absent_or_exception_fails_closed(self) -> None:
        with tempfile.TemporaryDirectory(prefix="c1-observer-test-") as temp:
            root = Path(temp)
            with mock.patch.object(automator, "STATE_ROOT", root), mock.patch.object(automator, "OBSERVER_JSONL", root / "c1-observer-v1.jsonl"), mock.patch.object(automator, "run_read_command", return_value={"returncode": 1, "stdout": "", "stderr": "observer absent"}):
                absent = automator.observer_check()
            with mock.patch.object(automator, "STATE_ROOT", root), mock.patch.object(automator, "OBSERVER_JSONL", root / "c1-observer-v1.jsonl"), mock.patch.object(automator, "run_read_command", side_effect=TimeoutError("observer timeout")):
                exception = automator.observer_check()
        self.assertEqual(absent["status"], "FAIL")
        self.assertEqual(exception["status"], "FAIL")

    def test_observer_wrong_runtime_or_existing_jsonl_fails_closed(self) -> None:
        with tempfile.TemporaryDirectory(prefix="c1-observer-test-") as temp:
            root = Path(temp)
            with mock.patch.object(automator, "STATE_ROOT", root), mock.patch.object(automator, "OBSERVER_JSONL", root / "c1-observer-v1.jsonl"), mock.patch.object(automator, "run_read_command", return_value=observer_output(root, path="/wrong/runtime")):
                wrong_runtime = automator.observer_check()
            (root / "c1-observer-v1.jsonl").write_text("stale\n", encoding="utf-8")
            with mock.patch.object(automator, "STATE_ROOT", root), mock.patch.object(automator, "OBSERVER_JSONL", root / "c1-observer-v1.jsonl"), mock.patch.object(automator, "run_read_command", return_value=observer_output(root)):
                existing_jsonl = automator.observer_check()
        self.assertEqual(wrong_runtime["status"], "FAIL")
        self.assertEqual(existing_jsonl["status"], "FAIL")

    def test_observer_valid_structured_preflight_passes(self) -> None:
        with tempfile.TemporaryDirectory(prefix="c1-observer-test-") as temp:
            root = Path(temp)
            with mock.patch.object(automator, "STATE_ROOT", root), mock.patch.object(automator, "OBSERVER_JSONL", root / "c1-observer-v1.jsonl"), mock.patch.object(automator, "run_read_command", return_value=observer_output(root)):
                result = automator.observer_check()
                validation_error = automator.validate_observer_preflight(result)
        self.assertEqual(result["status"], "PASS")
        self.assertIsNone(validation_error)

    def test_dry_run_is_read_only_and_defers_runtime_dependent_observer(self) -> None:
        pre = synthetic_pre()
        pre["checks"] = {"fixture_gate": {"status": "PASS"}}
        output = io.StringIO()
        with tempfile.TemporaryDirectory(prefix="c1-dry-run-test-") as temp:
            root = Path(temp) / "v2-absent"
            legacy = Path(temp) / "legacy"
            with active_runtime_patches(root, legacy), mock.patch.object(automator, "collect_precheck", return_value=pre), mock.patch.object(automator, "observer_check") as observer, mock.patch.object(automator, "RuntimeLock") as runtime_lock, mock.patch.object(automator, "sudo_authenticate") as sudo, mock.patch.object(automator, "run_c1") as run_c1, mock.patch.object(automator, "run_interactive_command") as service_command, mock.patch.object(automator, "atomic_write_json") as write_json, mock.patch.object(automator, "atomic_write_text") as write_text, mock.patch.object(automator, "append_jsonl") as append, contextlib.redirect_stdout(output):
                result = automator.cmd_dry_run(None)
            self.assertFalse(root.exists())
        self.assertEqual(result, 0)
        self.assertIn("PRECHECK_SCOPE=STATIC_DYNAMIC", output.getvalue())
        self.assertIn("RUNTIME_DEPENDENT_CHECKS=DEFERRED_RUNTIME_REQUIRED", output.getvalue())
        self.assertIn("OBSERVER_PREFLIGHT=NOT_RUN", output.getvalue())
        observer.assert_not_called()
        runtime_lock.assert_not_called()
        sudo.assert_not_called()
        run_c1.assert_not_called()
        service_command.assert_not_called()
        write_json.assert_not_called()
        write_text.assert_not_called()
        append.assert_not_called()
        tree = ast.parse(SCRIPT.read_text(encoding="utf-8"))
        dry_node = function_node(tree, "cmd_dry_run")
        direct_calls = {
            node.func.id
            for node in ast.walk(dry_node)
            if isinstance(node, ast.Call) and isinstance(node.func, ast.Name)
        }
        self.assertTrue({"collect_precheck", "planned_actions", "print_plan"}.issubset(direct_calls))
        self.assertFalse(direct_calls.intersection({"observer_check", "RuntimeLock", "sudo_authenticate", "run_c1", "atomic_write_json", "atomic_write_text", "append_jsonl"}))

    def test_authorized_runtime_is_initialized_before_observer_and_observer_failure_blocks_c1(self) -> None:
        events: list[str] = []

        class FakeTTY(io.StringIO):
            def isatty(self) -> bool:
                return True

        class FakeRuntime:
            def __enter__(self):
                events.append("runtime_lock")
                return self

            def __exit__(self, *_args):
                events.append("runtime_unlock")
                return False

            def cleanup_initialization(self):
                events.append("runtime_cleanup")
                return []

        pre = synthetic_pre()
        pre["checks"] = {"fixture_gate": {"status": "PASS"}}
        state = new_state("20260101T000000Z-dry-flow")
        with tempfile.TemporaryDirectory(prefix="c1-authorized-flow-test-") as temp:
            root = Path(temp) / "active"
            run_dir = root / "runs" / "20260101T000000Z-dry-flow"
            state_path = run_dir / "state.json"
            events_path = run_dir / "events.jsonl"

            def initialize(_pre, _artifacts):
                events.append("runtime_state_initialized")
                return {"run_dir": run_dir, "state_path": state_path, "events_path": events_path, "state": state}

            with mock.patch.object(automator.sys, "stdin", FakeTTY()), mock.patch.object(automator.sys, "stdout", FakeTTY()), mock.patch("builtins.input", return_value="RUN-C1"), mock.patch.object(automator, "set_signal_handlers"), mock.patch.object(automator, "namespace_paths_separate", return_value=True), mock.patch.object(automator, "RuntimeLock", return_value=FakeRuntime()), mock.patch.object(automator, "collect_precheck", return_value=pre), mock.patch.object(automator, "initialize_authorized_runtime_state", side_effect=initialize) as initialize_call, mock.patch.object(automator, "observer_check", side_effect=lambda: (events.append("observer_check") or {"status": "FAIL"})) as observer, mock.patch.object(automator, "required_update_state"), mock.patch.object(automator, "finalize_state"), mock.patch.object(automator, "sudo_authenticate") as sudo, mock.patch.object(automator, "run_c1") as run_c1:
                result = automator.cmd_run(None)
        self.assertEqual(result, 2)
        self.assertEqual(events, ["runtime_lock", "runtime_state_initialized", "observer_check", "runtime_unlock"])
        self.assertEqual(initialize_call.call_count, 1)
        observer.assert_called_once()
        sudo.assert_not_called()
        run_c1.assert_not_called()

    def test_dstate_incomplete_evidence_fails_guard_closed(self) -> None:
        original_units = automator.UNIT_SPECS
        try:
            automator.UNIT_SPECS = ()
            with mock.patch.object(automator, "dstate_snapshot", return_value={"count": 0, "complete": False, "incomplete": [{"pid": 1}]}), mock.patch.object(automator, "procs_snapshot", return_value={"procs_blocked": 0}), mock.patch.object(automator, "pressure_snapshot", return_value={"io": {"some": {"avg10": 0}, "full": {"avg10": 0}}}), mock.patch.object(automator, "gpu_control_guard", return_value=({}, [])):
                result = automator.guard_sample({"gpu": {}}, [])
        finally:
            automator.UNIT_SPECS = original_units
        self.assertEqual(result["status"], "FAIL")
        self.assertTrue(any("complete=False" in reason for reason in result["failures"]))

    def test_precheck_execution_gate_blocks_before_runtime_materialization(self) -> None:
        class FakeTTY(io.StringIO):
            def isatty(self) -> bool:
                return True

        pre = synthetic_pre()
        pre["execution_gate"] = {"GO_C1": "NOT_AVAILABLE", "STATUS": "BLOCKED", "BLOCKERS": ["OWNERSHIP_NOT_FULL"]}
        with mock.patch.object(automator.sys, "stdin", FakeTTY()), mock.patch.object(automator.sys, "stdout", FakeTTY()), mock.patch("builtins.input", return_value="RUN-C1"), mock.patch.object(automator, "set_signal_handlers"), mock.patch.object(automator, "namespace_paths_separate", return_value=True), mock.patch.object(automator, "collect_precheck", return_value=pre), mock.patch.object(automator, "RuntimeLock") as runtime_lock, mock.patch.object(automator, "observer_check") as observer, mock.patch.object(automator, "sudo_authenticate") as sudo, mock.patch.object(automator, "run_c1") as run_c1:
            result = automator.cmd_run(None)
        self.assertEqual(result, 2)
        runtime_lock.assert_not_called()
        observer.assert_not_called()
        sudo.assert_not_called()
        run_c1.assert_not_called()

    def test_initialization_failure_calls_neither_observer_nor_c1(self) -> None:
        class FailingRuntime:
            def __enter__(self):
                raise automator.AutomatorError("runtime initialization failed")

            def __exit__(self, *_args):
                return False

        class FakeTTY(io.StringIO):
            def isatty(self) -> bool:
                return True

        pre = synthetic_pre()
        with mock.patch.object(automator.sys, "stdin", FakeTTY()), mock.patch.object(automator.sys, "stdout", FakeTTY()), mock.patch("builtins.input", return_value="RUN-C1"), mock.patch.object(automator, "set_signal_handlers"), mock.patch.object(automator, "namespace_paths_separate", return_value=True), mock.patch.object(automator, "collect_precheck", return_value=pre), mock.patch.object(automator, "RuntimeLock", return_value=FailingRuntime()), mock.patch.object(automator, "observer_check") as observer, mock.patch.object(automator, "run_c1") as run_c1, self.assertRaises(automator.AutomatorError):
            automator.cmd_run(None)
        observer.assert_not_called()
        run_c1.assert_not_called()

    def test_runtime_lock_failure_cleans_only_new_v2_artifacts(self) -> None:
        with tempfile.TemporaryDirectory(prefix="c1-runtime-cleanup-test-") as temp:
            base = Path(temp)
            active = base / "active"
            legacy = base / "legacy"
            legacy.mkdir()
            sentinel = legacy / "sentinel"
            sentinel.write_text("legacy-unchanged", encoding="utf-8")
            artifacts = automator.RuntimeArtifacts()
            with mock.patch.object(automator, "STATE_ROOT", active), mock.patch.object(automator, "LEGACY_STATE_ROOT", legacy), mock.patch.object(automator, "LOCK_PATH", active / ".lock"), mock.patch.object(automator, "CURRENT_POINTER", active / "CURRENT"), mock.patch.object(automator, "OBSERVER_JSONL", active / "c1-observer-v1.jsonl"), mock.patch.object(automator.os, "open", side_effect=OSError("lock creation failed")):
                with self.assertRaises(automator.AutomatorError):
                    with automator.RuntimeLock(artifacts):
                        pass
            self.assertFalse(active.exists())
            self.assertEqual(sentinel.read_text(encoding="utf-8"), "legacy-unchanged")

    def test_runtime_artifacts_refuse_legacy_and_preserve_existing_entries(self) -> None:
        with tempfile.TemporaryDirectory(prefix="c1-artifact-test-") as temp:
            base = Path(temp)
            active = base / "active"
            legacy = base / "legacy"
            active.mkdir()
            legacy.mkdir()
            existing = active / "preexisting"
            existing.write_text("keep", encoding="utf-8")
            legacy_file = legacy / "keep"
            legacy_file.write_text("legacy", encoding="utf-8")
            artifacts = automator.RuntimeArtifacts()
            with mock.patch.object(automator, "STATE_ROOT", active), mock.patch.object(automator, "LEGACY_STATE_ROOT", legacy):
                artifacts.record_file(legacy_file)
                artifacts.record_file(active / "new-file")
                artifacts.record_dir(active / "new-dir")
                (active / "new-dir").mkdir()
                (active / "new-file").write_text("new", encoding="utf-8")
                artifacts.cleanup()
            self.assertTrue(existing.exists())
            self.assertFalse((active / "new-file").exists())
            self.assertFalse((active / "new-dir").exists())
            self.assertEqual(legacy_file.read_text(encoding="utf-8"), "legacy")

    def test_runtime_artifacts_restore_preexisting_current(self) -> None:
        with tempfile.TemporaryDirectory(prefix="c1-current-restore-test-") as temp:
            base = Path(temp)
            active = base / "active"
            legacy = base / "legacy"
            active.mkdir()
            legacy.mkdir()
            current = active / "CURRENT"
            current.write_text("old-run\n", encoding="utf-8")
            artifacts = automator.RuntimeArtifacts()
            with mock.patch.object(automator, "STATE_ROOT", active), mock.patch.object(automator, "LEGACY_STATE_ROOT", legacy), mock.patch.object(automator, "CURRENT_POINTER", current):
                artifacts.capture_current()
                artifacts.mark_current_changed()
                current.write_text("new-run\n", encoding="utf-8")
                artifacts.cleanup()
            self.assertEqual(current.read_text(encoding="utf-8"), "old-run\n")

    def test_B_initial_guard_windows_are_complete(self) -> None:
        state = new_state("20260101T000000Z-2")
        for label in ("T_GUARD", "T_PRE", "T_POST"):
            self.assertEqual(set(state["guard"][label]), set(automator.GUARD_SCHEMA_FIELDS))
            self.assertEqual(state["guard"][label]["status"], "NOT_RUN")
            self.assertIsNone(state["guard"][label]["reason"])
            self.assertEqual(state["guard"][label]["sample_count"], 0)
            self.assertEqual(state["guard"][label]["elapsed_seconds"], 0.0)
            self.assertIsNone(state["guard"][label]["log"])
        self.assertIsNone(automator.validate_state(state))

    def test_C_guard_final_and_terminal_state_are_valid(self) -> None:
        state = new_state("20260101T000000Z-3")
        with tempfile.TemporaryDirectory(prefix="c1-automator-test-") as temp:
            root = Path(temp)
            for label in ("T_GUARD", "T_PRE", "T_POST"):
                set_guard(state, label, root=root)
                automator.update_state(state, root / "state.json", root / "events.jsonl", "window_end", window=label, status="PASS")
            self.assertIsNone(automator.validate_state(state))
            state["phase"] = "COMPLETED"
            state["terminal"] = True
            state["result"] = "ABORTED_FAILURE_RESTORED"
            state["restore"] = {"status": "RESTORE_NOT_NEEDED", "attempted_units": [], "results": {}, "failures": []}
            state["post"] = {"status": "POST_CONFLICT", "discrepancies": ["external transition"]}
            automator.finalize_state(state, root / "state.json", root / "events.jsonl", state["result"], "test")
            loaded = json.loads((root / "state.json").read_text(encoding="utf-8"))
        self.assertIsNone(automator.validate_state(loaded))
        self.assertIsNotNone(loaded["final_state"])
        self.assertEqual(loaded["final_state"]["result"], "ABORTED_FAILURE_RESTORED")
        self.assertTrue(automator.state_is_incomplete(loaded))

    def test_D_T_PRE_transition_is_valid(self) -> None:
        state = new_state("20260101T000000Z-4")
        set_guard(state, "T_PRE", root=Path("/tmp"))
        update_state_in_temp(state, "window_end", window="T_PRE", status="PASS")
        self.assertIsNone(automator.validate_state(state))

    def test_E_T_POST_transition_is_valid(self) -> None:
        state = new_state("20260101T000000Z-5")
        set_guard(state, "T_POST", root=Path("/tmp"))
        update_state_in_temp(state, "window_end", window="T_POST", status="PASS")
        self.assertIsNone(automator.validate_state(state))

    def test_F_unit_pre_transition_is_valid(self) -> None:
        state = new_state("20260101T000000Z-6")
        unit = automator.UNIT_SPECS[0]["unit"]
        state["units"][unit] = {"unit": unit, "action": "NOT_STARTED"}
        update_state_in_temp(
            state,
            "unit_pre",
            unit=unit,
            unit_state={"ActiveState": "active"},
        )
        self.assertIsNone(automator.validate_state(state))
        self.assertEqual(state["events"][-1]["unit_state"]["ActiveState"], "active")

    def test_G_unit_stop_requested_transition_is_valid(self) -> None:
        state = new_state("20260101T000000Z-7")
        unit = automator.UNIT_SPECS[0]["unit"]
        state["units"][unit] = {"unit": unit, "action": "STOP_REQUESTED"}
        state["actions"].append({"unit": unit, "action": "STOP_REQUESTED"})
        update_state_in_temp(state, "unit_stop_requested", unit=unit, argv=["systemctl", "stop", unit])
        self.assertIsNone(automator.validate_state(state))
        self.assertEqual(state["events"][-1]["event"], "unit_stop_requested")

    def test_H_unit_post_restore_transition_is_valid(self) -> None:
        state = new_state("20260101T000000Z-8")
        unit = automator.UNIT_SPECS[0]["unit"]
        state["units"][unit] = {"unit": unit, "action": "RESTORED"}
        state["restore"] = {
            "status": "RESTORE_OK",
            "attempted_units": [unit],
            "results": {unit: {"status": "OK"}},
            "failures": [],
        }
        state["post"] = {"status": "POST_OK", "discrepancies": []}
        update_state_in_temp(state, "unit_post", unit=unit, status="OK")
        update_state_in_temp(state, "unit_restore", unit=unit, status="OK")
        self.assertIsNone(automator.validate_state(state))

    def test_I_abort_before_first_stop_is_terminal_and_valid(self) -> None:
        state = new_state("20260101T000000Z-9")
        state["phase"] = "ABORTED_PRE"
        state["terminal"] = True
        state["result"] = "ABORTED_PRE"
        state["restore"] = {"status": "RESTORE_ABORTED_NO_CHANGES", "attempted_units": [], "results": {}, "failures": []}
        state["post"] = {"status": "NOT_RUN"}
        with tempfile.TemporaryDirectory(prefix="c1-automator-test-") as temp:
            root = Path(temp)
            automator.finalize_state(state, root / "state.json", root / "events.jsonl", "ABORTED_PRE", "test")
            loaded = json.loads((root / "state.json").read_text(encoding="utf-8"))
        self.assertIsNone(automator.validate_state(loaded))
        self.assertTrue(loaded["terminal"])
        self.assertNotIn("unit_stop_requested", [event["event"] for event in loaded["events"]])

    def test_J_partial_stop_failure_is_valid_and_restorable(self) -> None:
        state = new_state("20260101T000000Z-10")
        unit = automator.UNIT_SPECS[0]["unit"]
        state["phase"] = "RESTORING"
        state["units"][unit] = {"unit": unit, "action": "STOP_REQUESTED"}
        state["restore"] = {
            "status": "RESTORE_PARTIAL",
            "attempted_units": [unit],
            "results": {unit: {"status": "FAIL", "action": "START_REQUESTED"}},
            "failures": [f"{unit}:test restore failure"],
        }
        state["post"] = {"status": "MANUAL_INTERVENTION_REQUIRED"}
        state["terminal"] = True
        state["result"] = "ABORTED_FAILURE_RESTORE_REQUIRED"
        with tempfile.TemporaryDirectory(prefix="c1-automator-test-") as temp:
            root = Path(temp)
            automator.finalize_state(state, root / "state.json", root / "events.jsonl", state["result"], "test")
            loaded = json.loads((root / "state.json").read_text(encoding="utf-8"))
        self.assertIsNone(automator.validate_state(loaded))
        self.assertEqual(loaded["restore"]["attempted_units"], [unit])
        self.assertEqual(loaded["result"], "ABORTED_FAILURE_RESTORE_REQUIRED")
        self.assertTrue(automator.state_is_incomplete(loaded))

    def test_J2_restore_only_restores_touched_pre_active_unit(self) -> None:
        state = new_state("20260101T000000Z-13")
        spec = automator.UNIT_SPECS[0]
        unit = spec["unit"]
        state["units"][unit] = {"unit": unit, "action": "STOP_REQUESTED"}
        before = {"ActiveState": "inactive", "SubState": "dead", "UnitFileState": "enabled", "_returncode": 0, "_valid": True}
        after = {"ActiveState": "active", "SubState": "running", "UnitFileState": "enabled", "_returncode": 0, "_valid": True}
        touched = [{"unit": unit, "scope": spec["scope"], "pre_active": True}]
        with tempfile.TemporaryDirectory(prefix="c1-automator-test-") as temp:
            root = Path(temp)
            with mock.patch.object(automator, "unit_state", side_effect=[before, after]), mock.patch.object(automator, "run_interactive_command", return_value={"argv": ["mock", "start", unit], "returncode": 0, "status": "OK"}) as command:
                result = automator.restore_units(touched, state, root / "state.json", root / "events.jsonl")
        self.assertEqual(result["status"], "RESTORE_OK")
        self.assertEqual(result["attempted_units"], [unit])
        command.assert_called_once()

    def test_A_required_persistence_failure_is_critical_and_blocks(self) -> None:
        state = new_state("20260101T000000Z-21")
        with tempfile.TemporaryDirectory(prefix="c1-persist-test-") as temp:
            root = Path(temp)
            with mock.patch.object(automator, "update_state", side_effect=OSError("disk full")):
                with self.assertRaises(automator.AutomatorError):
                    automator.required_update_state(state, root / "state.json", root / "events.jsonl", "c1_ready")
        self.assertTrue(state["state_write_errors"])
        self.assertTrue(state["state_write_errors"][-1]["critical"])

    def test_B_state_write_failure_before_c1_does_not_call_main(self) -> None:
        with tempfile.TemporaryDirectory(prefix="c1-pre-c1-test-") as temp:
            fixture = durable_pre_c1_fixture(Path(temp) / "active")
            with active_runtime_patches(fixture["root"], Path(temp) / "legacy"), mock.patch.object(automator, "update_state", side_effect=OSError("state write failed")), mock.patch.object(automator, "run_c1") as run_c1:
                with self.assertRaises(automator.AutomatorError):
                    automator.required_update_state(fixture["state"], fixture["state_path"], fixture["events_path"], "c1_ready", phase="C1")
                    automator.launch_c1_after_pre_c1_validation(
                        fixture["run_dir"], fixture["state"], fixture["state_path"], fixture["events_path"], fixture["pre"], True,
                        fixture["provenance"], fixture["collision"], fixture["observer"], fixture["auth"], True, True,
                    )
        run_c1.assert_not_called()

    def test_observer_required_persistence_failure_does_not_call_c1(self) -> None:
        with tempfile.TemporaryDirectory(prefix="c1-observer-persist-test-") as temp:
            fixture = durable_pre_c1_fixture(Path(temp) / "active")
            with active_runtime_patches(fixture["root"], Path(temp) / "legacy"), mock.patch.object(automator, "update_state", side_effect=OSError("observer state write failed")), mock.patch.object(automator, "run_c1") as run_c1:
                with self.assertRaises(automator.AutomatorError):
                    automator.required_update_state(
                        fixture["state"], fixture["state_path"], fixture["events_path"], "observer_check", result=fixture["observer"]
                    )
        run_c1.assert_not_called()
        self.assertTrue(fixture["state"]["state_write_errors"])
        self.assertTrue(fixture["state"]["state_write_errors"][-1]["critical"])

    def test_C_events_write_failure_before_c1_does_not_call_main(self) -> None:
        with tempfile.TemporaryDirectory(prefix="c1-pre-c1-test-") as temp:
            fixture = durable_pre_c1_fixture(Path(temp) / "active")
            with active_runtime_patches(fixture["root"], Path(temp) / "legacy"), mock.patch.object(automator, "append_jsonl", side_effect=OSError("events write failed")), mock.patch.object(automator, "run_c1") as run_c1:
                with self.assertRaises(automator.AutomatorError):
                    automator.required_update_state(fixture["state"], fixture["state_path"], fixture["events_path"], "c1_ready", phase="C1")
                    automator.launch_c1_after_pre_c1_validation(
                        fixture["run_dir"], fixture["state"], fixture["state_path"], fixture["events_path"], fixture["pre"], True,
                        fixture["provenance"], fixture["collision"], fixture["observer"], fixture["auth"], True, True,
                    )
        run_c1.assert_not_called()

    def test_D_final_state_validation_failure_does_not_call_main(self) -> None:
        with tempfile.TemporaryDirectory(prefix="c1-pre-c1-test-") as temp:
            fixture = durable_pre_c1_fixture(Path(temp) / "active")
            fixture["state"]["guard"]["T_PRE"]["status"] = "FAIL"
            with active_runtime_patches(fixture["root"], Path(temp) / "legacy"), mock.patch.object(automator, "run_c1") as run_c1:
                with self.assertRaises(automator.AutomatorError):
                    automator.launch_c1_after_pre_c1_validation(
                        fixture["run_dir"], fixture["state"], fixture["state_path"], fixture["events_path"], fixture["pre"], True,
                        fixture["provenance"], fixture["collision"], fixture["observer"], fixture["auth"], True, True,
                    )
        run_c1.assert_not_called()

    def test_E_state_events_mismatch_before_c1_does_not_call_main(self) -> None:
        with tempfile.TemporaryDirectory(prefix="c1-pre-c1-test-") as temp:
            fixture = durable_pre_c1_fixture(Path(temp) / "active")
            with fixture["events_path"].open("a", encoding="utf-8") as stream:
                stream.write(json.dumps({"event": "unrecorded_extra"}) + "\n")
            with active_runtime_patches(fixture["root"], Path(temp) / "legacy"), mock.patch.object(automator, "run_c1") as run_c1:
                with self.assertRaises(automator.AutomatorError):
                    automator.launch_c1_after_pre_c1_validation(
                        fixture["run_dir"], fixture["state"], fixture["state_path"], fixture["events_path"], fixture["pre"], True,
                        fixture["provenance"], fixture["collision"], fixture["observer"], fixture["auth"], True, True,
                    )
        run_c1.assert_not_called()

    def test_F_provenance_or_collision_failure_does_not_call_main(self) -> None:
        for field, value in (("provenance_ok", False), ("collision", {"status": "FAIL"})):
            with self.subTest(field=field):
                with tempfile.TemporaryDirectory(prefix="c1-pre-c1-test-") as temp:
                    fixture = durable_pre_c1_fixture(Path(temp) / "active")
                    with active_runtime_patches(fixture["root"], Path(temp) / "legacy"), mock.patch.object(automator, "run_c1") as run_c1:
                        kwargs = {
                            "provenance_ok": field != "provenance_ok" or value is True,
                            "collision": fixture["collision"] if field != "collision" else value,
                        }
                        with self.assertRaises(automator.AutomatorError):
                            automator.launch_c1_after_pre_c1_validation(
                                fixture["run_dir"], fixture["state"], fixture["state_path"], fixture["events_path"], fixture["pre"],
                                kwargs["provenance_ok"], fixture["provenance"], kwargs["collision"], fixture["observer"], fixture["auth"], True, True,
                            )
                    run_c1.assert_not_called()

    def test_durable_observer_state_invalid_does_not_call_run_c1(self) -> None:
        with tempfile.TemporaryDirectory(prefix="c1-pre-c1-test-") as temp:
            fixture = durable_pre_c1_fixture(Path(temp) / "active")
            durable = json.loads(fixture["state_path"].read_text(encoding="utf-8"))
            durable["observer_minimum_check"]["status"] = "FAIL"
            write_json(fixture["state_path"], durable)
            with active_runtime_patches(fixture["root"], Path(temp) / "legacy"), mock.patch.object(automator, "run_c1") as run_c1:
                with self.assertRaises(automator.AutomatorError):
                    automator.launch_c1_after_pre_c1_validation(
                        fixture["run_dir"], fixture["state"], fixture["state_path"], fixture["events_path"], fixture["pre"], True,
                        fixture["provenance"], fixture["collision"], fixture["observer"], fixture["auth"], True, True,
                    )
        run_c1.assert_not_called()

    def test_G_valid_durable_state_without_full_ownership_is_blocked(self) -> None:
        with tempfile.TemporaryDirectory(prefix="c1-pre-c1-test-") as temp:
            fixture = durable_pre_c1_fixture(Path(temp) / "active")
            with active_runtime_patches(fixture["root"], Path(temp) / "legacy"), mock.patch.object(automator, "run_c1") as run_c1:
                with self.assertRaises(automator.AutomatorError):
                    automator.launch_c1_after_pre_c1_validation(
                        fixture["run_dir"], fixture["state"], fixture["state_path"], fixture["events_path"], fixture["pre"], True,
                        fixture["provenance"], fixture["collision"], fixture["observer"], fixture["auth"], True, True,
                    )
            run_c1.assert_not_called()

    def test_K_post_conflict_external_transition_is_not_causal(self) -> None:
        spec = automator.UNIT_SPECS[0]
        unit = spec["unit"]
        pre = {"units": {unit: {"pre_active": True, "state": {"UnitFileState": "enabled"}}}, "gpu": {"controls": {}, "identity": {}}}
        after = {"ActiveState": "inactive", "SubState": "dead", "UnitFileState": "enabled", "_returncode": 0, "_valid": True}
        before = automator.UNIT_SPECS
        try:
            automator.UNIT_SPECS = (spec,)
            with mock.patch.object(automator, "unit_state", return_value=after), mock.patch.object(automator, "gpu_control_guard", return_value=({}, [])):
                result = automator.postcheck(pre, [])
        finally:
            automator.UNIT_SPECS = before
        self.assertEqual(result["status"], "POST_CONFLICT")
        self.assertEqual(result["external_transitions"][0]["automator_stop_recorded"], False)
        self.assertEqual(result["external_transitions"][0]["causality"], "NOT_PROVEN")

    def test_L_legacy_invalid_state_is_classified_and_not_active(self) -> None:
        with tempfile.TemporaryDirectory(prefix="c1-legacy-test-") as temp:
            legacy_root = Path(temp) / "legacy"
            manifest = legacy_fixture(legacy_root)
            active_root = Path(temp) / "active"
            with mock.patch.object(automator, "LEGACY_STATE_ROOT", legacy_root), mock.patch.object(automator, "HISTORICAL_LEGACY_RUNS", manifest), mock.patch.object(automator, "STATE_ROOT", active_root), mock.patch.object(automator, "LOCK_PATH", active_root / ".lock"), mock.patch.object(automator, "CURRENT_POINTER", active_root / "CURRENT"):
                inventory = automator.legacy_runtime_inventory()
                active_orphans = automator.orphan_runtime_runs()
        self.assertEqual(inventory["status"], automator.LEGACY_CLASSIFICATION)
        self.assertFalse(inventory["blocking"])
        self.assertEqual(active_orphans, [])

    def test_L2_unknown_legacy_artifact_is_not_globally_ignored(self) -> None:
        with tempfile.TemporaryDirectory(prefix="c1-legacy-unknown-test-") as temp:
            legacy_root = Path(temp) / "legacy"
            manifest = legacy_fixture(legacy_root)
            unknown = legacy_root / "runs" / "20260101T000000Z-999"
            unknown.mkdir(mode=0o700)
            with mock.patch.object(automator, "LEGACY_STATE_ROOT", legacy_root), mock.patch.object(automator, "HISTORICAL_LEGACY_RUNS", manifest):
                inventory = automator.legacy_runtime_inventory()
        self.assertTrue(inventory["blocking"])
        self.assertEqual(inventory["status"], "LEGACY_RUNTIME_UNRECOGNIZED")

    def test_M_invalid_new_namespace_state_blocks(self) -> None:
        with tempfile.TemporaryDirectory(prefix="c1-new-invalid-test-") as temp:
            root = Path(temp)
            run_dir = root / "runs" / "20260101T000000Z-11"
            run_dir.mkdir(parents=True)
            os.chmod(root, 0o700)
            os.chmod(root / "runs", 0o700)
            os.chmod(run_dir, 0o700)
            write_json(run_dir / "state.json", {"schema_version": 999})
            with mock.patch.object(automator, "STATE_ROOT", root), mock.patch.object(automator, "LOCK_PATH", root / ".lock"), mock.patch.object(automator, "CURRENT_POINTER", root / "CURRENT"):
                orphans = automator.orphan_runtime_runs()
        self.assertEqual(len(orphans), 1)
        self.assertEqual(orphans[0]["classification"], automator.ACTIVE_CLASSIFICATION)
        self.assertEqual(orphans[0]["status"], "INCOMPLETE")

    def test_N_active_lock_blocks_runtime_entry(self) -> None:
        with tempfile.TemporaryDirectory(prefix="c1-lock-test-") as temp:
            root = Path(temp)
            with mock.patch.object(automator, "STATE_ROOT", root), mock.patch.object(automator, "LOCK_PATH", root / ".lock"), mock.patch.object(automator, "CURRENT_POINTER", root / "CURRENT"), mock.patch.object(automator.fcntl, "flock", side_effect=BlockingIOError):
                with self.assertRaises(automator.AutomatorError):
                    with automator.RuntimeLock():
                        pass

    def test_O_empty_new_namespace_can_reach_precheck_but_not_bypass_io_gate(self) -> None:
        with tempfile.TemporaryDirectory(prefix="c1-empty-test-") as temp:
            root = Path(temp) / "not-created"
            with mock.patch.object(automator, "STATE_ROOT", root), mock.patch.object(automator, "LOCK_PATH", root / ".lock"), mock.patch.object(automator, "CURRENT_POINTER", root / "CURRENT"):
                self.assertIsNone(automator.load_current_state()[0])
                self.assertEqual(automator.orphan_runtime_runs(), [])
        self.assertTrue(automator.io_guard_criterion_ok(10.0, 10.0))
        self.assertFalse(automator.io_guard_criterion_ok(10.01, 10.0))
        self.assertEqual(automator.IO_GUARD_AVG10_MAX, 10.0)

    def test_PQR_historical_evidence_hashes_and_current_are_unchanged(self) -> None:
        root = Path("/run/user/1000/c1-isolation-automator/runs/20260924T154559Z-490709")
        state = root / "state.json"
        events = root / "events.jsonl"
        current = root.parent.parent / "CURRENT"
        if not state.exists():
            self.skipTest("historical residual not present")
        try:
            state_before = state.read_bytes()
            events_before = events.read_bytes()
            current_before = current.read_bytes()
        except PermissionError:
            self.skipTest("historical residual not readable")
        self.assertEqual(sha256(state), "f368fa91d050267b9fe30fb2e331e87a8a82e43f16f439470cc4b53d167bf99c")
        self.assertEqual(sha256(events), "8e7ffbe3693545144037d07727d834422bbb7c8fab81665bc6b7c123bc5d422d")
        self.assertEqual(current_before, b"20260924T154559Z-490709\n")
        self.assertEqual(state.read_bytes(), state_before)
        self.assertEqual(events.read_bytes(), events_before)
        self.assertEqual(current.read_bytes(), current_before)

    def test_status_reports_legacy_without_loading_it_as_active(self) -> None:
        legacy = {
            "status": automator.LEGACY_CLASSIFICATION,
            "classification": automator.LEGACY_CLASSIFICATION,
            "blocking": False,
        }
        output = io.StringIO()
        with mock.patch.object(automator, "legacy_runtime_inventory", return_value=legacy), mock.patch.object(automator, "load_current_state", return_value=(None, None)), contextlib.redirect_stdout(output):
            result = automator.cmd_status(None)
        text = output.getvalue()
        self.assertEqual(result, 0)
        self.assertIn("LEGACY_RUNTIME_STATUS=HISTORICAL_LEGACY_RUNTIME", text)
        self.assertIn("ACTIVE_RUNTIME_STATE=NONE", text)
        self.assertNotIn("RUNTIME_STATE_STATUS=INVALID", text)

    def test_S_all_update_state_calls_have_no_state_keyword_collision(self) -> None:
        tree = ast.parse(SCRIPT.read_text(encoding="utf-8"))
        calls = [node for node in ast.walk(tree) if isinstance(node, ast.Call) and isinstance(node.func, ast.Name) and node.func.id in {"update_state", "safe_update_state"}]
        conflicts = [(node.lineno, node.func.id) for node in calls if any(keyword.arg == "state" for keyword in node.keywords)]
        self.assertEqual(conflicts, [])
        self.assertTrue(any(isinstance(node, ast.Call) and isinstance(node.func, ast.Name) and node.func.id == "update_state" and any(keyword.arg == "unit_state" for keyword in node.keywords) for node in calls))

    def test_no_alternative_run_c1_call_path_exists(self) -> None:
        tree = ast.parse(SCRIPT.read_text(encoding="utf-8"))
        calls = [node for node in ast.walk(tree) if isinstance(node, ast.Call) and isinstance(node.func, ast.Name) and node.func.id == "run_c1"]
        self.assertEqual(len(calls), 1)
        source = SCRIPT.read_text(encoding="utf-8")
        self.assertNotIn("            run_c1(run_dir, state, state_path, events_path)", source)
        self.assertIn("return run_c1(run_dir, state, state_path, events_path)", source)

    def test_validator_rejects_legacy_schema_in_new_state(self) -> None:
        state = new_state("20260101T000000Z-12")
        state["schema_version"] = 1
        state["runtime_schema_version"] = 1
        self.assertIsNotNone(automator.validate_state(state))

    def test_writer_hash_mismatch_is_structurally_readable_but_blocks_active_run(self) -> None:
        state = new_state("20260101T000000Z-14")
        state["automator_sha256"] = "0" * 64
        state["script_sha256"] = "0" * 64
        state["initial_state"]["automator_sha256"] = "0" * 64
        self.assertIsNone(automator.validate_state(state))
        self.assertIsNotNone(automator.validate_active_writer_compat(state))
        self.assertTrue(automator.state_is_incomplete({**state, "_compatibility_error": "mismatch"}))

    def test_namespace_invariant_rejects_nested_active_path(self) -> None:
        with mock.patch.object(automator, "STATE_ROOT", automator.LEGACY_STATE_ROOT / "nested"):
            self.assertFalse(automator.namespace_paths_separate())

    def test_historical_and_active_namespaces_are_distinct(self) -> None:
        self.assertNotEqual(automator.LEGACY_STATE_ROOT, automator.STATE_ROOT)
        self.assertEqual(automator.LEGACY_STATE_ROOT.name, "c1-isolation-automator")
        self.assertEqual(automator.STATE_ROOT.name, "c1-isolation-automator-v2")
        self.assertEqual(automator.OBSERVER_JSONL.parent, automator.STATE_ROOT)
        self.assertEqual(automator.LEGACY_CLASSIFICATION, "HISTORICAL_LEGACY_RUNTIME")
        self.assertEqual(automator.ACTIVE_CLASSIFICATION, "ACTIVE_INCOMPLETE_RUNTIME")

    def test_ownership_contract_is_static_partial(self) -> None:
        rows = automator.ownership_contract()
        required = {"resource", "current_owner", "expected_owner", "proof", "fail", "abort", "evidence", "restore_impact", "source"}
        self.assertTrue(rows)
        self.assertTrue(all(required.issubset(row) for row in rows))
        self.assertIn("card1", {row["resource"] for row in rows})
        self.assertIn("renderD129", {row["resource"] for row in rows})
        result = automator.evaluate_ownership_proof()
        self.assertEqual(result["status"], automator.OWNERSHIP_PARTIAL)
        self.assertFalse(result["full_proof"])
        self.assertIn("RUNTIME_EVIDENCE_REQUIRED", result["reason_codes"])
        gate = automator.evaluate_execution_gate(result, automator.system_gate_contracts(), automator.btrfs_gate_contract())
        self.assertEqual(gate["GO_C1"], "NOT_AVAILABLE")
        self.assertEqual(gate["STATUS"], "BLOCKED")

    def test_system_gate_contracts_keep_unknown_thresholds(self) -> None:
        contracts = automator.system_gate_contracts()
        self.assertEqual(set(contracts), {"PM", "GOVERNOR", "IRQ", "SCHEDULER", "READ_AHEAD", "SDA_ACTIVITY"})
        for name, contract in contracts.items():
            self.assertEqual(contract["VALUE"], automator.CONTRACT_UNKNOWN)
            self.assertEqual(contract["THRESHOLD_SOURCE"], automator.CONTRACT_NOT_AVAILABLE)
            result = automator.evaluate_system_gate(name)
            self.assertEqual(result["STATUS"], automator.CONTRACT_PENDING)
            self.assertFalse(result["PASS_ALLOWED"])

    def test_btrfs_gate_is_conflict_without_runtime_evidence(self) -> None:
        contract = automator.btrfs_gate_contract()
        self.assertEqual(contract["BTRFS"], "CONFLICT")
        self.assertEqual(contract["BTRFS_CAUSE"], "UNKNOWN")
        result = automator.evaluate_btrfs_gate()
        self.assertEqual(result["STATUS"], "CONFLICT")
        self.assertEqual(result["reason"], "NOT_RUN")

    def test_restore_contract_separates_executed_and_validated(self) -> None:
        contract = automator.restore_contract_snapshot()
        self.assertTrue(contract["RESTORE_PLANNED"])
        self.assertFalse(contract["RESTORE_EXECUTED"])
        self.assertFalse(contract["RESTORE_VALIDATED"])
        executing = automator.restore_contract_transition(contract, "EXECUTE")
        self.assertTrue(executing["RESTORE_EXECUTED"])
        self.assertFalse(executing["RESTORE_VALIDATED"])
        validated = automator.restore_contract_transition(executing, "VALIDATE")
        self.assertTrue(validated["RESTORE_VALIDATED"])
        failed = automator.restore_contract_transition(executing, "FAIL")
        self.assertEqual(failed["STATUS"], "ABORT_RESTORE")

    def test_runtime_contract_is_not_materialized(self) -> None:
        contract = automator.runtime_contract_snapshot()
        self.assertTrue(contract["RUNTIME_DESIGNED"])
        self.assertFalse(contract["RUNTIME_MATERIALIZED"])
        self.assertFalse(contract["RUNTIME_VALIDATED"])
        self.assertEqual(contract["TTY"]["status"], "NOT_VERIFIED")
        self.assertEqual(contract["RUN-C1"]["status"], "ABSENT")
        self.assertEqual(contract["sudo"]["status"], "NOT_VERIFIED")

    def test_precheck_contract_has_all_required_fields(self) -> None:
        contracts = automator.build_precheck_contracts({"dstate": {"status": "PASS", "detail": {"count": 0}}})
        required = {"CHECK", "SOURCE", "REQUIRED_STATE", "FAIL_CONDITION", "ABORT_CONDITION", "EVIDENCE", "RESTORE_IMPACT"}
        self.assertTrue(set(automator.PRECHECK_CONTRACT_SPECS).issubset(contracts))
        self.assertTrue(all(required.issubset(contract) for contract in contracts.values()))

    def test_fallback_contract_distinguishes_no_go_abort_blocked(self) -> None:
        pre = automator.classify_fallback("D_STATE", "PRE")
        guard = automator.classify_fallback("D_STATE", "GUARD", touched=True)
        ownership = automator.classify_fallback("OWNERSHIP", "PRE")
        self.assertEqual(pre["CLASSIFICATION"], "NO_GO")
        self.assertEqual(guard["CLASSIFICATION"], "ABORT")
        self.assertEqual(guard["RESTORE"], "RESTORE_REQUIRED")
        self.assertEqual(ownership["CLASSIFICATION"], "BLOCKED")

    def test_implementation_provenance_is_complete(self) -> None:
        provenance = automator.implementation_provenance()
        self.assertEqual(set(provenance), {"REQ-OWNERSHIP-CONTRACT", "REQ-SYSTEM-GATES", "REQ-BTRFS-GATE", "REQ-RESTORE-STATE", "REQ-RUNTIME-STATE", "REQ-PRECHECK-CONTRACT", "REQ-FALLBACK", "REQ-PROVENANCE"})
        for record in provenance.values():
            self.assertTrue({"CODE_LOCATION", "TEST", "DOCUMENTATION", "STATUS"}.issubset(record))


if __name__ == "__main__":
    unittest.main(verbosity=2)
