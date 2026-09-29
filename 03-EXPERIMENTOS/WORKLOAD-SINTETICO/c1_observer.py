#!/usr/bin/env python3
"""OBS-C1-v1: single user-space collector for the C1 protocol.

The collector owns the only telemetry file.  C1 stdout/stderr are captured through
pipes.  Environmental reads use an explicit, bounded path set; no process/system
inventory or shell scan is performed by this program.
"""
from __future__ import annotations

import argparse
import hashlib
import json
import os
import selectors
import shutil
import subprocess
import sys
import time
from typing import Any, BinaryIO, Callable, Dict, List, Optional

SCHEMA = "c1-observer.v1"
PROJECT_DIR = os.path.realpath(os.path.dirname(os.path.abspath(__file__)))
EXPECTED_BINARY = os.path.realpath(os.path.join(PROJECT_DIR, "main-graphics"))
GPU_ROOT = "/sys/class/drm/card1/device"
HWMON_ROOT = "/sys/class/drm/card1/device/hwmon/hwmon2"
CPU_ROOT = "/sys/devices/system/cpu/cpufreq"
PSI_ROOT = "/proc/pressure"
DISKSTATS = "/proc/diskstats"
PROC_STAT = "/proc/stat"
IRQ_ROOT = "/proc/irq/42"
POLICY_COUNT = 8
GPU_PERIOD_NS = 100_000_000
CPU_PERIOD_NS = 200_000_000
IO_PERIOD_NS = 500_000_000
CLEANUP_TERM_TIMEOUT_S = 2.0
CLEANUP_KILL_TIMEOUT_S = 1.0


class WriterError(RuntimeError):
    """Raised when the JSONL stream cannot remain a valid record stream."""


def mono_ns() -> int:
    return time.clock_gettime_ns(time.CLOCK_MONOTONIC)


def unescape_mount_field(value: str) -> str:
    return (value.replace("\\040", " ")
                 .replace("\\011", "\t")
                 .replace("\\012", "\n")
                 .replace("\\134", "\\"))


def filesystem_type(path: str) -> Optional[str]:
    """Return the longest mountinfo filesystem type for path.

    This reads only /proc/self/mountinfo; it does not invoke external utilities.
    """
    target = os.path.realpath(path)
    best_mount = ""
    best_type: Optional[str] = None
    with open("/proc/self/mountinfo", "r", encoding="utf-8") as stream:
        for line in stream:
            fields = line.rstrip("\n").split()
            try:
                separator = fields.index("-")
                mount_point = unescape_mount_field(fields[4])
                fs_type = fields[separator + 1]
            except (ValueError, IndexError):
                continue
            if target == mount_point or target.startswith(mount_point.rstrip("/") + "/"):
                if len(mount_point) >= len(best_mount):
                    best_mount = mount_point
                    best_type = fs_type
    return best_type


def verify_runtime_dir() -> Dict[str, Any]:
    runtime = os.environ.get("XDG_RUNTIME_DIR")
    if not runtime:
        raise RuntimeError("XDG_RUNTIME_DIR_NOT_AVAILABLE")
    if not os.path.isabs(runtime):
        raise RuntimeError("XDG_RUNTIME_DIR_NOT_ABSOLUTE")
    if not os.path.isdir(runtime):
        raise RuntimeError("XDG_RUNTIME_DIR_NOT_DIRECTORY")
    fs_type = filesystem_type(runtime)
    if fs_type != "tmpfs":
        raise RuntimeError("XDG_RUNTIME_DIR_NOT_TMPFS")
    if not os.access(runtime, os.W_OK | os.X_OK):
        raise RuntimeError("XDG_RUNTIME_DIR_NOT_WRITABLE")
    usage = shutil.disk_usage(runtime)
    return {
        "path": runtime,
        "filesystem": fs_type,
        "free_bytes": usage.free,
        "total_bytes": usage.total,
    }


def sha256_file(path: str) -> str:
    digest = hashlib.sha256()
    with open(path, "rb") as stream:
        for chunk in iter(lambda: stream.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def read_git_head() -> Dict[str, Any]:
    git_dir = os.path.join(PROJECT_DIR, ".git")
    head_path = os.path.join(git_dir, "HEAD")
    try:
        with open(head_path, "r", encoding="utf-8") as stream:
            head = stream.read().strip()
    except (OSError, UnicodeError) as exc:
        return {"status": "NOT_AVAILABLE", "error": type(exc).__name__}
    if not head.startswith("ref: "):
        return {"status": "OK", "value": head}
    ref = head[5:].strip()
    ref_path = os.path.join(git_dir, ref)
    try:
        with open(ref_path, "r", encoding="utf-8") as stream:
            return {"status": "OK", "value": stream.read().strip(), "ref": ref}
    except (OSError, UnicodeError):
        pass
    packed_path = os.path.join(git_dir, "packed-refs")
    try:
        with open(packed_path, "r", encoding="utf-8") as stream:
            for line in stream:
                fields = line.strip().split()
                if len(fields) == 2 and fields[1] == ref:
                    return {"status": "OK", "value": fields[0], "ref": ref, "packed": True}
    except (OSError, UnicodeError):
        pass
    return {"status": "NOT_AVAILABLE", "ref": ref}


def provenance_manifest(binary_path: str, command: List[str], args: argparse.Namespace) -> Dict[str, Any]:
    source_paths = {
        "graphics.cpp": os.path.join(PROJECT_DIR, "src", "graphics.cpp"),
        "vertex.vert": os.path.join(PROJECT_DIR, "src", "vertex.vert"),
        "fragment.frag": os.path.join(PROJECT_DIR, "src", "fragment.frag"),
        "fragment2.frag": os.path.join(PROJECT_DIR, "src", "fragment2.frag"),
        "Makefile": os.path.join(PROJECT_DIR, "Makefile"),
        "c1_observer.py": os.path.join(PROJECT_DIR, "c1_observer.py"),
    }
    source_hashes: Dict[str, Any] = {}
    for name, path in source_paths.items():
        try:
            source_hashes[name] = {"status": "OK", "sha256": sha256_file(path), "path": path}
        except OSError as exc:
            source_hashes[name] = {"status": "NOT_AVAILABLE", "path": path, "error": type(exc).__name__}
    return {
        "status": "AVAILABLE_PARTIAL",
        "binary_path": binary_path,
        "binary_sha256": sha256_file(binary_path),
        "source_hashes": source_hashes,
        "git_head": read_git_head(),
        "build_id": args.build_id or {"status": "NOT_AVAILABLE", "reason": "not supplied to collector"},
        "compiler": args.compiler or {"status": "NOT_AVAILABLE", "reason": "not supplied to collector"},
        "flags": args.cxxflags or {"status": "NOT_AVAILABLE", "reason": "not supplied to collector"},
        "observer_argv": list(sys.argv),
        "c1_argv": list(command),
        "cwd": args.cwd or os.getcwd(),
    }


def read_optional(path: str, parser: Callable[[str], Any]) -> Dict[str, Any]:
    try:
        with open(path, "r", encoding="utf-8") as stream:
            raw = stream.read().strip()
    except (OSError, UnicodeError) as exc:
        return {"status": "NOT_AVAILABLE", "path": path, "error": type(exc).__name__}
    if not raw:
        return {"status": "NOT_AVAILABLE", "path": path}
    try:
        return {"status": "OK", "path": path, "value": parser(raw)}
    except (TypeError, ValueError) as exc:
        return {"status": "INVALID", "path": path, "error": type(exc).__name__}


def parse_int(raw: str) -> int:
    return int(raw.strip(), 0)


def parse_dpm_hz(raw: str) -> int:
    for line in raw.splitlines():
        if "*" not in line:
            continue
        try:
            _, label_text = line.split(":", 1)
            label = label_text.replace("*", "").strip().lower()
            if label.endswith("ghz"):
                return int(float(label[:-3].strip()) * 1_000_000_000)
            if label.endswith("mhz"):
                return int(float(label[:-3].strip()) * 1_000_000)
            if label.endswith("khz"):
                return int(float(label[:-3].strip()) * 1_000)
        except (ValueError, IndexError):
            continue
    raise ValueError("no starred DPM frequency")


def parse_psi(raw: str) -> Dict[str, Any]:
    result: Dict[str, Any] = {}
    for line in raw.splitlines():
        parts = line.split()
        if not parts:
            continue
        resource = parts[0]
        values: Dict[str, int] = {}
        for item in parts[1:]:
            if "=" not in item:
                continue
            key, value = item.split("=", 1)
            try:
                values[key] = int(value)
            except ValueError:
                continue
        result[resource] = values
    return result


def parse_diskstats(raw: str) -> Dict[str, Any]:
    for line in raw.splitlines():
        fields = line.split()
        if len(fields) < 14 or fields[0:2] != ["8", "0"]:
            continue
        return {
            "device": fields[0] + ":" + fields[1],
            "reads_completed": int(fields[2]),
            "reads_merged": int(fields[3]),
            "sectors_read": int(fields[4]),
            "read_time_ms": int(fields[5]),
            "writes_completed": int(fields[6]),
            "writes_merged": int(fields[7]),
            "sectors_written": int(fields[8]),
            "write_time_ms": int(fields[9]),
            "io_in_progress": int(fields[10]),
            "io_time_ms": int(fields[11]),
            "weighted_io_time_ms": int(fields[12]),
            "discards_completed": int(fields[13]) if len(fields) > 13 else None,
        }
    raise ValueError("sda diskstats row not found")


def parse_procs_blocked(raw: str) -> int:
    for line in raw.splitlines():
        if line.startswith("procs_blocked "):
            return int(line.split()[1])
    raise ValueError("procs_blocked not found")


def parse_process_stat(raw: str) -> Dict[str, Any]:
    close = raw.rfind(")")
    if close < 0:
        raise ValueError("process stat malformed")
    fields = raw[close + 2:].split()
    if len(fields) < 15:
        raise ValueError("process stat short")
    ticks = [int(fields[index]) for index in (11, 12, 13, 14)]
    return {
        "state": fields[0],
        "utime_ticks": ticks[0],
        "stime_ticks": ticks[1],
        "cutime_ticks": ticks[2],
        "cstime_ticks": ticks[3],
    }


def parse_context_switches(raw: str) -> Dict[str, int]:
    result: Dict[str, int] = {}
    for line in raw.splitlines():
        if line.startswith("voluntary_ctxt_switches:") or line.startswith("nonvoluntary_ctxt_switches:"):
            key, value = line.split(":", 1)
            result[key] = int(value.strip())
    return result


class JsonlWriter:
    def __init__(self, path: str):
        self.path = path
        self.sequence = 0
        self.state = "OPEN"
        self.valid = True
        self.last_error: Optional[Dict[str, str]] = None
        self.fd = os.open(path, os.O_WRONLY | os.O_CREAT | os.O_EXCL, 0o600)
        self.stream = os.fdopen(self.fd, "w", encoding="utf-8", buffering=1)

    def _invalidate(self, stage: str, exc: BaseException) -> None:
        self.state = "INVALID"
        self.valid = False
        self.last_error = {"stage": stage, "type": type(exc).__name__, "message": str(exc)}
        raise WriterError(f"JSONL writer {stage} failure: {type(exc).__name__}: {exc}") from exc

    def emit(self, record_type: str, **fields: Any) -> None:
        if not self.valid:
            raise WriterError("JSONL writer is already invalid")
        record: Dict[str, Any] = {
            "schema": SCHEMA,
            "seq": self.sequence,
            "t_mono_ns": mono_ns(),
            "type": record_type,
        }
        record.update(fields)
        try:
            payload = json.dumps(record, separators=(",", ":"), ensure_ascii=False) + "\n"
        except (TypeError, ValueError) as exc:
            self._invalidate("serialize", exc)
        self.state = "WRITING"
        try:
            written = self.stream.write(payload)
            if written != len(payload):
                raise OSError(f"short write: {written}/{len(payload)}")
        except (OSError, UnicodeError, ValueError) as exc:
            self._invalidate("write", exc)
        self.state = "FLUSHING"
        try:
            self.stream.flush()
        except (OSError, UnicodeError, ValueError) as exc:
            self._invalidate("flush", exc)
        self.sequence += 1
        self.state = "OPEN"

    def close(self) -> None:
        if self.stream.closed:
            return
        try:
            self.stream.flush()
        except (OSError, UnicodeError, ValueError) as exc:
            self._invalidate("close_flush", exc)
        try:
            self.stream.close()
        except (OSError, UnicodeError, ValueError) as exc:
            self._invalidate("close", exc)
        if self.valid:
            self.state = "CLOSED"

    def status(self) -> Dict[str, Any]:
        return {
            "path": self.path,
            "state": self.state,
            "valid": self.valid,
            "sequence": self.sequence,
            "last_error": self.last_error,
        }


class C1StreamReader:
    def __init__(self, stream: BinaryIO, name: str, writer: JsonlWriter):
        self.stream = stream
        self.name = name
        self.writer = writer
        self.buffer = b""
        self.eof = False

    def read_available(self, file_descriptor: int) -> None:
        chunk = os.read(file_descriptor, 65536)
        if not chunk:
            self.eof = True
            if self.buffer:
                text = self.buffer.decode("utf-8", errors="replace").rstrip("\r")
                record_type = "c1_marker" if text.startswith("marker:") or text.startswith("frame_marker:") else "c1_output"
                self.writer.emit(record_type, stream=self.name, line=text)
                self.buffer = b""
            return
        self.buffer += chunk
        while b"\n" in self.buffer:
            line, self.buffer = self.buffer.split(b"\n", 1)
            text = line.decode("utf-8", errors="replace").rstrip("\r")
            record_type = "c1_marker" if text.startswith("marker:") or text.startswith("frame_marker:") else "c1_output"
            self.writer.emit(record_type, stream=self.name, line=text)


def gpu_sample(gpu_root: str, hwmon_root: str) -> Dict[str, Any]:
    return {
        "gpu_busy_percent": read_optional(gpu_root + "/gpu_busy_percent", parse_int),
        "mem_busy_percent": read_optional(gpu_root + "/mem_busy_percent", parse_int),
        "sclk_hz": read_optional(gpu_root + "/pp_dpm_sclk", parse_dpm_hz),
        "mclk_hz": read_optional(gpu_root + "/pp_dpm_mclk", parse_dpm_hz),
        "power1_input": read_optional(hwmon_root + "/power1_input", parse_int),
        "temp1_input": read_optional(hwmon_root + "/temp1_input", parse_int),
        "vram_used": read_optional(gpu_root + "/mem_info_vram_used", parse_int),
        "gtt_used": read_optional(gpu_root + "/mem_info_gtt_used", parse_int),
        "runtime_status": read_optional(gpu_root + "/power/runtime_status", lambda value: value),
    }


def cpu_sample(cpu_root: str, pid: int) -> Dict[str, Any]:
    policies: List[Dict[str, Any]] = []
    for index in range(POLICY_COUNT):
        base = f"{cpu_root}/policy{index}"
        policies.append({
            "policy": index,
            "governor_nominal": read_optional(base + "/scaling_governor", lambda value: value),
            "frequency_observed": read_optional(base + "/scaling_cur_freq", parse_int),
        })
    process_stat = read_optional(f"/proc/{pid}/stat", parse_process_stat)
    process_status = read_optional(f"/proc/{pid}/status", parse_context_switches)
    process_cpu_ticks: Dict[str, Any] = {"status": "NOT_AVAILABLE"}
    if process_stat.get("status") == "OK":
        ticks = (process_stat["value"]["utime_ticks"] +
                 process_stat["value"]["stime_ticks"] +
                 process_stat["value"]["cutime_ticks"] +
                 process_stat["value"]["cstime_ticks"])
        try:
            hz = os.sysconf("SC_CLK_TCK")
            process_cpu_ticks = {"status": "OK", "value": ticks / hz, "ticks": ticks, "hz": hz}
        except (ValueError, OSError):
            process_cpu_ticks = {"status": "INVALID", "ticks": ticks}
    return {
        "policies": policies,
        "process_cpu_time": process_cpu_ticks,
        "context_switches": process_status,
        "frequency_effective_estimate": {
            "status": "NOT_AVAILABLE",
            "reason": "no APERF/MPERF effective-frequency path in this collector",
        },
    }


def io_sample() -> Dict[str, Any]:
    return {
        "psi_cpu": read_optional(PSI_ROOT + "/cpu", parse_psi),
        "psi_io": read_optional(PSI_ROOT + "/io", parse_psi),
        "psi_memory": read_optional(PSI_ROOT + "/memory", parse_psi),
        "diskstats_sda": read_optional(DISKSTATS, parse_diskstats),
        "procs_blocked": read_optional(PROC_STAT, parse_procs_blocked),
        "agent_events": {
            "status": "NOT_AVAILABLE",
            "reason": "collector does not poll service or process state",
        },
    }


def irq_sample() -> Dict[str, Any]:
    return {
        "irq42_smp_affinity_list": read_optional(IRQ_ROOT + "/smp_affinity_list", lambda value: value),
        "irq42_effective_affinity": read_optional(IRQ_ROOT + "/effective_affinity", lambda value: value),
    }


def pm_sample(gpu_root: str) -> Dict[str, Any]:
    return {
        "power_control": read_optional(gpu_root + "/power/control", lambda value: value),
        "runtime_status": read_optional(gpu_root + "/power/runtime_status", lambda value: value),
        "autosuspend_delay_ms": read_optional(gpu_root + "/power/autosuspend_delay_ms", parse_int),
    }


def parse_args(argv: Optional[List[str]] = None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="C1 observer v1")
    parser.add_argument("--check-tmpfs", action="store_true",
                        help="verify XDG_RUNTIME_DIR tmpfs and exit")
    parser.add_argument("--cwd", default=None,
                        help="working directory for the supplied C1 command")
    parser.add_argument("--binary-sha256", default=None,
                        help="optional expected SHA-256 for the fixed main-graphics binary")
    parser.add_argument("--build-id", default=None,
                        help="optional build ID to record in provenance")
    parser.add_argument("--compiler", default=None,
                        help="optional compiler string to record in provenance")
    parser.add_argument("--cxxflags", default=None,
                        help="optional compiler flags to record in provenance")
    parser.add_argument("--gpu-root", default=GPU_ROOT)
    parser.add_argument("--hwmon-root", default=HWMON_ROOT)
    parser.add_argument("--cpu-root", default=CPU_ROOT)
    parser.add_argument("command", nargs=argparse.REMAINDER)
    args = parser.parse_args(argv)
    if args.command and args.command[0] == "--":
        args.command = args.command[1:]
    return args


def check_tmpfs_and_print() -> int:
    try:
        result = verify_runtime_dir()
    except RuntimeError as exc:
        print(json.dumps({"status": "ERROR", "error": str(exc)}, separators=(",", ":")))
        return 1
    print(json.dumps({"status": "OK", **result}, separators=(",", ":")))
    return 0


def close_reader(selector: selectors.BaseSelector, reader: Optional[C1StreamReader]) -> None:
    if reader is None:
        return
    try:
        selector.unregister(reader.stream)
    except (KeyError, OSError, ValueError):
        pass
    try:
        reader.stream.close()
    except (OSError, ValueError):
        pass


def cleanup_child(child: Optional[subprocess.Popen[bytes]],
                  selector: selectors.BaseSelector,
                  stdout_reader: Optional[C1StreamReader],
                  stderr_reader: Optional[C1StreamReader],
                  writer: JsonlWriter) -> Dict[str, Any]:
    status: Dict[str, Any] = {
        "child_started": child is not None,
        "terminated": False,
        "killed": False,
        "waited": False,
        "writer": writer.status(),
    }
    if child is not None and child.poll() is None:
        try:
            child.terminate()
            status["terminated"] = True
        except OSError as exc:
            status["terminate_error"] = type(exc).__name__
        try:
            child.wait(timeout=CLEANUP_TERM_TIMEOUT_S)
            status["waited"] = True
        except subprocess.TimeoutExpired:
            try:
                child.kill()
                status["killed"] = True
            except OSError as exc:
                status["kill_error"] = type(exc).__name__
            try:
                child.wait(timeout=CLEANUP_KILL_TIMEOUT_S)
                status["waited"] = True
            except subprocess.TimeoutExpired as exc:
                status["wait_error"] = type(exc).__name__
    elif child is not None:
        status["waited"] = True
    close_reader(selector, stdout_reader)
    close_reader(selector, stderr_reader)
    try:
        selector.close()
    except OSError as exc:
        status["selector_error"] = type(exc).__name__
    try:
        writer.close()
    except WriterError as exc:
        status["writer_close_error"] = str(exc)
    status["writer"] = writer.status()
    return status


def run_observer(args: argparse.Namespace) -> int:
    runtime = verify_runtime_dir()
    if not args.command:
        raise RuntimeError("C1_COMMAND_NOT_AVAILABLE")
    if args.cwd is not None and not os.path.isdir(args.cwd):
        raise RuntimeError("CWD_NOT_DIRECTORY")

    command = list(args.command)
    if not os.path.isabs(command[0]):
        raise RuntimeError("C1_BINARY_PATH_NOT_ABSOLUTE")
    if not os.path.isfile(EXPECTED_BINARY) or not os.access(EXPECTED_BINARY, os.X_OK):
        raise RuntimeError("EXPECTED_MAIN_GRAPHICS_NOT_EXECUTABLE")
    if os.path.realpath(command[0]) != EXPECTED_BINARY:
        raise RuntimeError("C1_BINARY_OUTSIDE_ALLOWLIST")
    if os.path.commonpath([EXPECTED_BINARY, PROJECT_DIR]) != PROJECT_DIR:
        raise RuntimeError("C1_BINARY_OUTSIDE_PROJECT_TREE")
    command[0] = EXPECTED_BINARY
    observed_binary_sha256 = sha256_file(EXPECTED_BINARY)
    if args.binary_sha256 is not None:
        expected = args.binary_sha256.strip().lower()
        if len(expected) != 64 or expected != observed_binary_sha256:
            raise RuntimeError("C1_BINARY_SHA256_MISMATCH")

    provenance = provenance_manifest(EXPECTED_BINARY, command, args)
    output_path = os.path.join(runtime["path"], "c1-observer-v1.jsonl")
    writer = JsonlWriter(output_path)
    child: Optional[subprocess.Popen[bytes]] = None
    selector = selectors.DefaultSelector()
    stdout_reader: Optional[C1StreamReader] = None
    stderr_reader: Optional[C1StreamReader] = None
    last_runtime_status: Optional[str] = None
    last_irq_affinity: Optional[str] = None
    result: Optional[int] = None
    try:
        writer.emit(
            "observer_start",
            runtime=runtime,
            output=output_path,
            command=command,
            provenance=provenance,
            binary_sha256=observed_binary_sha256,
            gpu_root=args.gpu_root,
            hwmon_root=args.hwmon_root,
            cpu_root=args.cpu_root,
            sample_missing={
                "status": "NOT_AVAILABLE",
                "reason": "no imputation; scheduled_lag_ns is the loss/delay indicator",
            },
        )
        child = subprocess.Popen(
            command,
            cwd=args.cwd,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            bufsize=0,
            close_fds=True,
            shell=False,
        )
        assert child.stdout is not None and child.stderr is not None
        stdout_reader = C1StreamReader(child.stdout, "stdout", writer)
        stderr_reader = C1StreamReader(child.stderr, "stderr", writer)
        selector.register(child.stdout, selectors.EVENT_READ, stdout_reader)
        selector.register(child.stderr, selectors.EVENT_READ, stderr_reader)
        writer.emit("c1_spawn", pid=child.pid)

        next_gpu = mono_ns() + GPU_PERIOD_NS
        next_cpu = mono_ns() + CPU_PERIOD_NS
        next_io = mono_ns() + IO_PERIOD_NS
        while True:
            now = mono_ns()
            deadlines = [next_gpu, next_cpu, next_io]
            timeout = max(0.0, (min(deadlines) - now) / 1_000_000_000.0)
            events = selector.select(timeout)
            for key, _ in events:
                reader = key.data
                assert isinstance(reader, C1StreamReader)
                reader.read_available(key.fd)
                if reader.eof:
                    selector.unregister(key.fd)

            now = mono_ns()
            if now >= next_gpu:
                sample = gpu_sample(args.gpu_root, args.hwmon_root)
                status = sample["runtime_status"]
                if status.get("status") == "OK":
                    value = status["value"]
                    if last_runtime_status is not None and value != last_runtime_status:
                        writer.emit("event", event_type="pm_transition",
                                    field="runtime_status", previous=last_runtime_status,
                                    current=value)
                    last_runtime_status = value
                writer.emit("sample", stream="gpu", fields=sample,
                            scheduled_lag_ns=max(0, now - next_gpu))
                next_gpu = now + GPU_PERIOD_NS
            if now >= next_cpu:
                writer.emit("sample", stream="cpu", fields=cpu_sample(args.cpu_root, child.pid),
                            scheduled_lag_ns=max(0, now - next_cpu))
                next_cpu = now + CPU_PERIOD_NS
            if now >= next_io:
                io_fields = io_sample()
                irq_fields = irq_sample()
                pm_fields = pm_sample(args.gpu_root)
                writer.emit("sample", stream="io", fields=io_fields,
                            scheduled_lag_ns=max(0, now - next_io))
                writer.emit("sample", stream="irq", fields=irq_fields)
                writer.emit("sample", stream="pm", fields=pm_fields)
                irq_value = irq_fields["irq42_smp_affinity_list"]
                if irq_value.get("status") == "OK":
                    value = irq_value["value"]
                    if last_irq_affinity is not None and value != last_irq_affinity:
                        writer.emit("event", event_type="irq_transition", irq=42,
                                    previous=last_irq_affinity, current=value)
                    last_irq_affinity = value
                next_io = now + IO_PERIOD_NS

            if child.poll() is not None and stdout_reader.eof and stderr_reader.eof:
                break
        return_code = child.wait()
        writer.emit("c1_exit", return_code=return_code)
        writer.emit("observer_end", return_code=return_code)
        result = 0 if return_code == 0 else 1
    except Exception as exc:
        if writer.valid:
            try:
                writer.emit("observer_error", error_type=type(exc).__name__, message=str(exc))
            except WriterError:
                pass
        raise
    finally:
        cleanup_status = cleanup_child(child, selector, stdout_reader, stderr_reader, writer)
        if not writer.valid:
            print(f"c1-observer: INVALID_JSONL {writer.status()}", file=sys.stderr)
            result = 2
        elif cleanup_status.get("wait_error"):
            print(f"c1-observer: CHILD_WAIT_FAILURE {cleanup_status}", file=sys.stderr)
            result = 2
    if result is None:
        result = 1
    return result


def main(argv: Optional[List[str]] = None) -> int:
    args = parse_args(argv)
    if args.check_tmpfs:
        return check_tmpfs_and_print()
    try:
        return run_observer(args)
    except WriterError as exc:
        print(f"c1-observer: INVALID_WRITER: {exc}", file=sys.stderr)
        return 2
    except (OSError, RuntimeError, ValueError) as exc:
        print(f"c1-observer: {type(exc).__name__}: {exc}", file=sys.stderr)
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
