"""rx550-torneo — M1: runner SOSTENIDO de `power1_cap` (35 W vs 30 W).

NO es optimización ni un benchmark automático: es el mecanismo de medición
controlada que mantiene un cap durante UNA corrida y SIEMPRE lo restaura.

Flujo de una corrida:

    preflight (read-only) -> SET cap (1 write) -> readback obligatorio
        -> workload + sampler 10 Hz (SOLO LECTURA) -> RESTORE (1 write) -> readback

Escrituras privilegiadas totales: exactamente 2, siempre sobre `power1_cap`.
El sampler no escribe nada. No hay `sudo` ni privilegios por muestra.

Ejecución real: el runner se lanza UNA vez con root (sudo). El workload se
ejecuta como el usuario de escritorio (SUDO_UID/SUDO_GID), y un guard forkeado
restaura el cap incluso si el proceso muere por SIGKILL.
"""
import csv
import datetime
import json
import os
import re
import signal
import subprocess
import threading
import time

from . import util
from . import write_test as wt

# --- constantes del experimento M1 -----------------------------------------
EXPECTED_ORIGINAL = 35_000_000
DEFAULT_TARGET = 30_000_000
TEMP_ABORT_MC = 90_000
SAMPLE_INTERVAL_S = 0.08
WARMUP_S = 5.0
DEFAULT_DURATION_S = 25.0
WORKLOAD_TIMEOUT_SLACK_S = 30.0

COOLDOWN_TEMP_MC = 45_000
COOLDOWN_STABLE_S = 30.0
COOLDOWN_MAX_WAIT_S = 900.0

TELEMETRY_COLUMNS = [
    "ts", "t_rel", "gpu_busy_pct", "mem_busy_pct", "sclk_hz", "mclk_hz",
    "power1_uw", "power1_cap", "temp_mc", "runtime_status", "event", "cap_target",
]

AUX_NODES = {
    "power_control": ("device", "power/control"),
    "power_dpm_force_performance_level": ("device", "power_dpm_force_performance_level"),
    "pp_dpm_sclk": ("device", "pp_dpm_sclk"),
    "pp_dpm_mclk": ("device", "pp_dpm_mclk"),
    "pp_power_profile_mode": ("device", "pp_power_profile_mode"),
}
STRICT_AUX = ("power_control", "power_dpm_force_performance_level", "pp_power_profile_mode")
NORMALIZED_AUX = ("pp_dpm_sclk", "pp_dpm_mclk")

# Entorno del workload: Mesa STOCK, RX 550 forzada.
WORKLOAD_ENV_OVERRIDES = {
    "MESA_VK_DEVICE_SELECT": "1002:699f",
    "VK_ICD_FILENAMES": "/usr/share/vulkan/icd.d/radeon_icd.x86_64.json",
}
WORKLOAD_ENV_UNSET = ("MESA_CUSTOM", "LD_LIBRARY_PATH", "LIBGL_DRIVERS_PATH")


def default_workload_command(duration_s=DEFAULT_DURATION_S):
    return ["vkmark", "-p", "immediate", "-s", "1920x1080",
            "-b", f"shading:shading=phong:duration={int(duration_s)}"]


def workload_env(base=None):
    env = dict(os.environ if base is None else base)
    for key in WORKLOAD_ENV_UNSET:
        env.pop(key, None)
    env.update(WORKLOAD_ENV_OVERRIDES)
    return env


# --- detección conservadora de reset/hang de GPU (solo-lectura) -------------
# Se consulta `journalctl -k` con una ventana temporal EXACTA alrededor del
# workload (un solo formato: `short-iso`), evitando el diff del ring buffer.
# Solo cuentan firmas inequívocas de reset/hang; los fault benignos (PRT, VM)
# NO se consideran. Si no hay fuente fiable, `checked=false` y NO hay CRITICAL.
KERNEL_LOG_FORMAT = "short-iso"

GPU_RESET_RE = re.compile(
    r"(amdgpu|drm)[^\n]*("
    r"ring [\w.]+ timeout|job timeout|gpu reset|gpu hang|"
    r"reset begin|reset success|asic reset|ring reset|failed to reset|"
    r"gfx (hang|timeout))",
    re.IGNORECASE)

# Mensajes benignos que NUNCA deben contar como reset/hang.
BENIGN_RESET_RE = re.compile(r"Disabling VM faults because of PRT request", re.IGNORECASE)


def is_reset_line(line):
    """True solo para evidencia inequívoca de reset/hang (excluye benignos)."""
    if not line or BENIGN_RESET_RE.search(line):
        return False
    return bool(GPU_RESET_RE.search(line))


def read_kernel_window(since_epoch, until_epoch):
    """Ventana read-only de `journalctl -k`. Devuelve (lineas, error, formato)."""
    argv = ["journalctl", "-k", "--no-pager", f"--output={KERNEL_LOG_FORMAT}",
            f"--since=@{float(since_epoch):.6f}", f"--until=@{float(until_epoch):.6f}"]
    try:
        p = subprocess.run(argv, capture_output=True, text=True, timeout=20)
    except (OSError, subprocess.SubprocessError) as exc:
        return None, f"{type(exc).__name__}: {exc}", None
    if p.returncode != 0:
        return None, (p.stderr or f"journalctl rc={p.returncode}").strip(), None
    return p.stdout.splitlines(), None, KERNEL_LOG_FORMAT


class CapRunError(wt.WriteTestError):
    pass


class AbortError(CapRunError):
    """Abort solicitado en caliente (temperatura, timeout). Dispara restore."""


# ------------------------------------------------------------- lectura read-only
def read_aux_m1(gpu):
    dev = gpu["target"]["device"]
    hw = gpu["hwmon"]
    out = {}
    for name, (base, rel) in AUX_NODES.items():
        root = hw if base == "hwmon" else dev
        try:
            out[name] = util.read_text(os.path.join(root, rel), strip=True, missing_ok=True)
        except util.SafeIOError as exc:
            out[name] = f"<error:{exc}>"
    try:
        out["runtime_status"] = util.read_text(
            os.path.join(dev, "power", "runtime_status"), strip=True, missing_ok=True)
    except util.SafeIOError as exc:
        out["runtime_status"] = f"<error:{exc}>"
    return out


def read_limits(gpu):
    hw = gpu["hwmon"]

    def ri(name, missing_ok=False):
        try:
            return util.read_int(os.path.join(hw, name), missing_ok=missing_ok)
        except util.SafeIOError as exc:
            raise CapRunError("LIMITS_UNREADABLE", f"{name}: {exc}")

    return {"min": ri("power1_cap_min"), "max": ri("power1_cap_max")}


def read_telemetry(gpu):
    """Una muestra read-only. Nunca escribe."""
    d = gpu["target"]["device"]
    h = gpu["hwmon"]

    def ri(path):
        try:
            return util.read_int(path, missing_ok=True)
        except util.SafeIOError:
            return None

    row = {
        "gpu_busy_pct": ri(os.path.join(d, "gpu_busy_percent")),
        "mem_busy_pct": ri(os.path.join(d, "mem_busy_percent")),
        "sclk_hz": ri(os.path.join(h, "freq1_input")),
        "mclk_hz": ri(os.path.join(h, "freq2_input")),
        "power1_uw": ri(os.path.join(h, "power1_input")),
        "power1_cap": ri(os.path.join(h, "power1_cap")),
        "temp_mc": ri(os.path.join(h, "temp1_input")),
        "runtime_status": util.read_text(
            os.path.join(d, "power", "runtime_status"), strip=True, missing_ok=True),
    }
    return row


def _active_markers(text):
    if not text:
        return 0
    return sum(1 for ln in text.splitlines() if " *" in ln)


# --------------------------------------------------------------------- sampler
class Sampler(threading.Thread):
    """Hilo de muestreo 10 Hz. SOLO lee y escribe CSV en el directorio de salida."""

    def __init__(self, reader, out_csv, interval, cap_target, warmup_s=0.0):
        super().__init__(daemon=True, name="m1-sampler")
        self.reader = reader
        self.out_csv = out_csv
        self.interval = interval
        self.cap_target = cap_target
        self.warmup_s = warmup_s
        self.stop_event = threading.Event()
        self.abort_reason = None
        self.rows = 0
        self.error = None
        self._t0 = time.monotonic()

    def run(self):
        try:
            with open(self.out_csv, "w", newline="", encoding="utf-8") as fh:
                writer = csv.writer(fh)
                writer.writerow(TELEMETRY_COLUMNS)
                while not self.stop_event.is_set():
                    row = self.reader()
                    row = dict(row)
                    row["ts"] = time.time()
                    row["t_rel"] = round(time.monotonic() - self._t0, 4)
                    row["cap_target"] = self.cap_target
                    temp = row.get("temp_mc")
                    event = ""
                    if isinstance(temp, int) and temp >= TEMP_ABORT_MC:
                        event = f"EVENT_T>={TEMP_ABORT_MC // 1000}C"
                        if self.abort_reason is None:
                            self.abort_reason = f"temp {temp} mC >= {TEMP_ABORT_MC} mC"
                    row["event"] = event
                    writer.writerow([row.get(c) for c in TELEMETRY_COLUMNS])
                    fh.flush()
                    self.rows += 1
                    self.stop_event.wait(self.interval)
        except Exception as exc:  # noqa: BLE001
            self.error = f"{type(exc).__name__}: {exc}"

    def stop(self):
        self.stop_event.set()


# ---------------------------------------------------------------------- sesión
class CapRunSession:
    """Una corrida: SET -> readback -> workload+sampler -> RESTORE -> readback.

    Inyectable para tests: `node`, `aux_reader`, `limits_reader`, `reader`
    (telemetría), `cooldown_fn`, `hooks` ({'before_workload': fn}).
    """

    def __init__(self, gpu, node, target, workload_cmd=None, out_dir=None,
                 aux_reader=None, limits_reader=None, reader=None,
                 duration_s=DEFAULT_DURATION_S, warmup_s=WARMUP_S,
                 interval_s=SAMPLE_INTERVAL_S, hooks=None, enable_guard=True,
                 workload_user=None, workload_group=None, workload_env=None,
                 sleep=time.sleep, monotonic=time.monotonic, popen=None,
                 log_reader=None):
        self.gpu = gpu
        self.node = node
        self.target = int(target)
        self.workload_cmd = list(workload_cmd or default_workload_command(duration_s))
        self.out_dir = out_dir
        self.aux_reader = aux_reader or read_aux_m1
        self.limits_reader = limits_reader or read_limits
        self.reader = reader or (lambda: read_telemetry(gpu))
        self.duration_s = duration_s
        self.warmup_s = warmup_s
        self.interval_s = interval_s
        self.hooks = hooks or {}
        self.enable_guard = enable_guard
        self.workload_user = workload_user
        self.workload_group = workload_group
        self.workload_env = workload_env
        self.sleep = sleep
        self.monotonic = monotonic
        self.popen = popen or subprocess.Popen
        self.log_reader = log_reader or read_kernel_window
        self.expected_log_format = KERNEL_LOG_FORMAT

        self.original = None
        self.set_readback = None
        self.restored = None
        self.readback_final = None
        self.workload_rc = None
        self.workload_timeout = duration_s + WORKLOAD_TIMEOUT_SLACK_S
        self.aux_before = {}
        self.aux_after = {}
        self.aux_diff = []
        self.gpu_reset_check = {}
        self.result = "NOT_STARTED"
        self.fatal = None
        self.events = []
        self.rollback_attempts = 0
        self.cap_written = False
        self._restore_attempted = False
        self._restore_done = False
        self.sampler = None
        self._proc = None
        self._old_handlers = {}
        self._guard_pid = None
        self._guard_w = None

    # -- auditoría -----------------------------------------------------------
    def _event(self, name, **kw):
        ev = {"t": datetime.datetime.now().astimezone().isoformat(timespec="milliseconds"),
              "event": name}
        ev.update(kw)
        self.events.append(ev)

    def audit(self):
        t = self.gpu["target"]
        return {
            "schema_version": "m1-1",
            "timestamp": datetime.datetime.now().astimezone().isoformat(timespec="seconds"),
            "pci_id": f"{t.get('vendor', 0):04x}:{t.get('device_id', 0):04x}",
            "drm_card": self.gpu.get("drm_card"),
            "bdf": t.get("bdf"),
            "path": getattr(self.node, "path", None),
            "field": "power1_cap",
            "expected_original": EXPECTED_ORIGINAL,
            "original": self.original,
            "target": self.target,
            "set_readback": self.set_readback,
            "restored": self.restored,
            "readback_final": self.readback_final,
            "workload_rc": self.workload_rc,
            "result": self.result,
            "rollback_attempts": self.rollback_attempts,
            "aux_before": self.aux_before,
            "aux_after": self.aux_after,
            "aux_diff": self.aux_diff,
            "aux_unchanged": not self.aux_diff,
            "gpu_reset_check": self.gpu_reset_check,
            "events": self.events,
            "fatal": self.fatal,
        }

    # -- señales -------------------------------------------------------------
    def _install_handlers(self):
        def handler(signum, _frame):
            raise wt.WriteTestInterrupted(signum)
        for sig in (signal.SIGINT, signal.SIGTERM, signal.SIGHUP):
            try:
                self._old_handlers[sig] = signal.getsignal(sig)
                signal.signal(sig, handler)
            except (ValueError, OSError):
                pass

    def _restore_handlers(self):
        for sig, prev in list(self._old_handlers.items()):
            try:
                signal.signal(sig, prev)
            except (ValueError, OSError):
                pass
        self._old_handlers = {}

    # -- guard de crash (SIGKILL) -------------------------------------------
    def _spawn_guard(self):
        if not self.enable_guard or not hasattr(os, "fork"):
            return
        try:
            r, w = os.pipe()
        except OSError:
            return
        pid = os.fork()
        if pid == 0:  # hijo: hereda privilegios y el valor original
            os.close(w)
            code = 0
            try:
                if os.read(r, 1) != b"A":
                    os._exit(0)  # el padre murió antes de armar: nada que restaurar
                data = os.read(r, 1)
                if data in (b"K", b"F"):
                    os._exit(0)
                try:
                    self._guard_restore()
                except Exception:  # noqa: BLE001
                    code = 2
            finally:
                os._exit(code)
        os.close(r)
        self._guard_pid = pid
        self._guard_w = w
        try:
            os.write(w, b"A")  # armar: a partir de aquí el guard restaura ante EOF
        except OSError:
            pass

    def _guard_restore(self):
        status = "unknown"
        try:
            self.node.write(str(EXPECTED_ORIGINAL))
            rb = self.node.read()
            status = "restored" if int(rb) == EXPECTED_ORIGINAL else f"MISMATCH:{rb}"
        except Exception as exc:  # noqa: BLE001
            status = f"FAILED:{type(exc).__name__}:{exc}"
        if self.out_dir:
            try:
                with open(os.path.join(self.out_dir, "guard.log"), "a", encoding="utf-8") as fh:
                    fh.write(f"{datetime.datetime.now().astimezone().isoformat()} "
                             f"guard_restore {status}\n")
            except OSError:
                pass

    def _finish_guard(self):
        if self._guard_w is None:
            return
        try:
            os.write(self._guard_w, b"K" if self._restore_done else b"F")
            os.close(self._guard_w)
        except OSError:
            pass
        try:
            os.waitpid(self._guard_pid, 0)
        except OSError:
            pass
        self._guard_w = None

    # -- preflight -----------------------------------------------------------
    def preflight(self):
        t = self.gpu["target"]
        if (t.get("vendor"), t.get("device_id")) != (0x1002, 0x699f):
            raise CapRunError("WRONG_GPU", f"GPU objetivo no es 1002:699f: {t.get('pci')}")
        if t.get("driver") != "amdgpu":
            raise CapRunError("WRONG_GPU", f"driver no amdgpu: {t.get('driver')}")
        if self.gpu["intel"]["vendor"] != 0x8086:
            raise CapRunError("WRONG_GPU", f"Intel no 0x8086: {self.gpu['intel'].get('pci')}")
        if self.gpu["intel"]["card"] == self.gpu["drm_card"]:
            raise CapRunError("WRONG_GPU", "objetivo == Intel; imposible")
        if not self.gpu.get("display_cards"):
            raise CapRunError("NO_DISPLAY", "display Intel no confirmado")
        self.node.verify_authorized()
        try:
            original_text = self.node.read()
        except util.SafeIOError as exc:
            raise CapRunError("NODE_UNREADABLE", f"no se pudo leer power1_cap: {exc}")
        try:
            original = int(original_text)
        except (TypeError, ValueError):
            raise CapRunError("UNKNOWN_VALUE", f"power1_cap no entero: {original_text!r}")
        if original != EXPECTED_ORIGINAL:
            raise CapRunError(
                "ORIGINAL_MISMATCH",
                f"power1_cap={original} != esperado {EXPECTED_ORIGINAL}; no se escribe nada")

        self.aux_before = self.aux_reader(self.gpu)
        if self.aux_before.get("power_control") != "on":
            raise CapRunError("PRECONDITION",
                              f"power/control={self.aux_before.get('power_control')!r} != 'on'")
        dpm = self.aux_before.get("power_dpm_force_performance_level")
        if dpm != "auto":
            raise CapRunError("PRECONDITION", f"DPM={dpm!r} != 'auto'")
        for key in NORMALIZED_AUX:
            n = _active_markers(self.aux_before.get(key))
            if n != 1:
                raise CapRunError(
                    "FORCING_DETECTED",
                    f"{key} tiene {n} niveles activos (esperado 1): posible forcing SCLK/MCLK")

        limits = self.limits_reader(self.gpu)
        self.limits = limits
        if not (limits["min"] <= original <= limits["max"]):
            raise CapRunError("INCONSISTENT", f"original {original} fuera de {limits}")
        if not (limits["min"] <= self.target <= limits["max"]):
            raise CapRunError("OUT_OF_RANGE", f"target {self.target} fuera de {limits}")
        self.original = original
        self._event("preflight_ok", original=original, target=self.target,
                    path=getattr(self.node, "path", None))
        return original

    # -- escrituras ----------------------------------------------------------
    def _set_cap(self):
        self._event("set_begin", value=self.target)
        # C: si el write se aplica y luego lanza, igual debemos intentar restore.
        self.cap_written = True
        self.node.write(str(self.target))
        self.set_readback = self.node.read()
        self._event("set_readback", value=self.set_readback)
        if self.set_readback is None or int(self.set_readback) != self.target:
            raise CapRunError(
                "SET_READBACK", f"readback {self.set_readback!r} != target {self.target}")

    def _restore(self, reason):
        if self._restore_attempted:
            return
        self._restore_attempted = True
        self.rollback_attempts += 1
        self._event("restore_begin", value=EXPECTED_ORIGINAL, reason=reason)
        self.node.write(str(EXPECTED_ORIGINAL))
        self.restored = str(EXPECTED_ORIGINAL)
        self.readback_final = self.node.read()
        self._event("restore_readback", value=self.readback_final)
        if self.readback_final is None or int(self.readback_final) != EXPECTED_ORIGINAL:
            self.result = "CRITICAL"
            raise wt.CriticalRollbackError(
                "ROLLBACK_MISMATCH",
                f"CRÍTICO: restore no verificado: {self.readback_final!r} != {EXPECTED_ORIGINAL}")
        self._restore_done = True
        self._event("restore_ok", value=self.readback_final)

    def _safe_restore(self, reason):
        if not self.cap_written or self._restore_attempted:
            return
        try:
            self._restore(reason)
        except Exception as exc:  # noqa: BLE001
            self.result = "CRITICAL"
            self._event("restore_failed", reason=reason, error=f"{type(exc).__name__}: {exc}")

    # -- workload ------------------------------------------------------------
    def _run_workload(self):
        os.makedirs(self.out_dir, exist_ok=True)
        telemetry = os.path.join(self.out_dir, "telemetry.csv")
        self.sampler = Sampler(self.reader, telemetry, self.interval_s,
                               cap_target=self.target, warmup_s=self.warmup_s)
        full_cmd = self.workload_cmd
        self._event("workload_begin", cmd=full_cmd)
        hook = self.hooks.get("before_workload")
        if hook:
            hook(self)
        stdout_path = os.path.join(self.out_dir, "stdout.txt")
        stderr_path = os.path.join(self.out_dir, "stderr.txt")
        kwargs = {}
        if self.workload_user is not None:
            kwargs["user"] = self.workload_user
        if self.workload_group is not None:
            kwargs["group"] = self.workload_group
        workload_start = time.time()
        with open(stdout_path, "wb") as fo, open(stderr_path, "wb") as fe:
            proc = self.popen(full_cmd, stdout=fo, stderr=fe,
                              env=self.workload_env or workload_env(), **kwargs)
            self._proc = proc
            self.sampler.start()
            deadline = self.monotonic() + self.workload_timeout
            try:
                while proc.poll() is None:
                    if self.sampler.abort_reason:
                        self._terminate(proc)
                        raise AbortError("TEMP_ABORT", self.sampler.abort_reason)
                    if self.monotonic() > deadline:
                        self._terminate(proc)
                        raise AbortError("WORKLOAD_TIMEOUT",
                                         f"workload excedió {self.workload_timeout}s")
                    self.sleep(0.1)
                self.workload_rc = proc.returncode
                workload_end = time.time()
            finally:
                self.sampler.stop()
                self.sampler.join(timeout=5.0)
        self._event("workload_end", rc=self.workload_rc,
                    rows=self.sampler.rows if self.sampler else None,
                    sampler_error=self.sampler.error if self.sampler else None)
        if self.sampler and self.sampler.error:
            raise CapRunError("SAMPLER_ERROR", self.sampler.error)
        if self._check_gpu_reset(workload_start, workload_end):
            self.result = "CRITICAL"
            raise CapRunError(
                "GPU_RESET_OR_HANG",
                "evidencia de reset/hang de GPU en la ventana: "
                + "; ".join(self.gpu_reset_check["matches"][:3]))
        if self.workload_rc != 0:
            raise CapRunError(
                "WORKLOAD_FAILED",
                f"workload terminó con rc={self.workload_rc}; stdout/stderr en {self.out_dir}")

    def _check_gpu_reset(self, since, until):
        """Ventana `journalctl` de un solo formato; True solo con evidencia clara."""
        try:
            lines, err, fmt = self.log_reader(since, until)
        except Exception as exc:  # noqa: BLE001
            lines, err, fmt = None, f"{type(exc).__name__}: {exc}", None
        available = (err is None and fmt == self.expected_log_format
                     and lines is not None)
        matched = [ln for ln in lines if is_reset_line(ln)] if available else []
        self.gpu_reset_check = {
            "checked": available,
            "error": err,
            "format": fmt,
            "expected_format": self.expected_log_format,
            "since": since,
            "until": until,
            "matches": matched,
        }
        self._event("gpu_reset_check", checked=available, matches=len(matched))
        return bool(matched)

    def _terminate(self, proc):
        try:
            proc.terminate()
            try:
                proc.wait(timeout=5)
            except subprocess.TimeoutExpired:
                proc.kill()
                proc.wait(timeout=5)
        except Exception:  # noqa: BLE001
            pass

    # -- auxiliares ----------------------------------------------------------
    def _check_aux(self):
        self.aux_after = self.aux_reader(self.gpu)
        for key in STRICT_AUX:
            b, a = self.aux_before.get(key), self.aux_after.get(key)
            if b != a:
                self.aux_diff.append((key, b, a))
        for key in NORMALIZED_AUX:
            b = wt.normalize_dpm(self.aux_before.get(key))
            a = wt.normalize_dpm(self.aux_after.get(key))
            if b != a:
                self.aux_diff.append((key, b, a))
        if self.aux_diff:
            self.result = "AUX_CHANGED"
            raise CapRunError(
                "AUX_CHANGED",
                "nodos NO autorizados cambiaron: " + "; ".join(
                    f"{k}: {x!r} -> {y!r}" for k, x, y in self.aux_diff))

    # -- ejecución -----------------------------------------------------------
    def run(self):
        if self.out_dir:
            os.makedirs(self.out_dir, exist_ok=True)
        try:
            self.preflight()
            self._install_handlers()
            self._spawn_guard()
            self._set_cap()
            self._run_workload()
            self._restore("normal")
            self._check_aux()
            self.result = "OK"
        except BaseException as exc:  # noqa: BLE001
            code = getattr(exc, "code", "UNEXPECTED")
            if code != "INTERRUPTED":
                self._safe_restore(reason=code)
            else:
                self._safe_restore(reason="INTERRUPTED")
            if self.result not in ("CRITICAL", "AUX_CHANGED"):
                if code == "INTERRUPTED":
                    self.result = "INTERRUPTED"
                elif isinstance(exc, AbortError):
                    self.result = "ABORTED"
                else:
                    self.result = "ERROR"
            self.fatal = {"code": code, "message": str(exc)}
            self._event("fatal", code=code, message=str(exc))
        finally:
            self._restore_handlers()
            self._finish_guard()
        return self.audit()

    def save(self):
        os.makedirs(self.out_dir, exist_ok=True)
        path = os.path.join(self.out_dir, "audit.json")
        text = json.dumps(self.audit(), ensure_ascii=False, sort_keys=True, indent=2)
        tmp = path + ".tmp"
        with open(tmp, "w", encoding="utf-8") as fh:
            fh.write(text)
            fh.flush()
            os.fsync(fh.fileno())
        os.replace(tmp, path)
        return path


# --------------------------------------------------------------------- schedule
def cooldown(gpu, reader=None, target_mc=COOLDOWN_TEMP_MC, stable_s=COOLDOWN_STABLE_S,
             max_wait_s=COOLDOWN_MAX_WAIT_S, sleep=time.sleep, monotonic=time.monotonic):
    """Espera a que la temperatura esté <= target_mc de forma estable."""
    reader = reader or (lambda: read_telemetry(gpu))
    start = monotonic()
    stable_from = None
    while True:
        temp = reader().get("temp_mc")
        now = monotonic()
        if now - start > max_wait_s:
            raise AbortError("COOLDOWN_TIMEOUT", f"cooldown excedió {max_wait_s}s (temp={temp})")
        if isinstance(temp, int) and temp <= target_mc:
            if stable_from is None:
                stable_from = now
            elif now - stable_from >= stable_s:
                return temp
        else:
            stable_from = None
        sleep(1.0)


def run_schedule(gpu, node, workload_cmd=None, out_dir=None, blocks=5,
                 arms=(EXPECTED_ORIGINAL, DEFAULT_TARGET), duration_s=DEFAULT_DURATION_S,
                 session_kwargs=None, cooldown_fn=None, schedule_name="m1"):
    """5 bloques pareados con orden alternado; aborta ante cualquier fallo."""
    session_kwargs = dict(session_kwargs or {})
    if workload_cmd is not None:
        session_kwargs.setdefault("workload_cmd", workload_cmd)
    cooldown_fn = cooldown_fn if cooldown_fn is not None else (lambda: cooldown(gpu))
    os.makedirs(out_dir, exist_ok=True)
    audits = []
    for block in range(1, blocks + 1):
        order = list(arms) if block % 2 == 1 else list(reversed(arms))
        for arm_i, target in enumerate(order, start=1):
            cooldown_fn()
            run_dir = os.path.join(out_dir, f"block{block:02d}-arm{arm_i}-{target}")
            sess = CapRunSession(gpu, node, target, out_dir=run_dir,
                                 duration_s=duration_s, **session_kwargs)
            audit = sess.run()
            sess.save()
            audit["run_dir"] = run_dir
            audit["block"] = block
            audit["arm_index"] = arm_i
            audits.append(audit)
            if audit["result"] != "OK":
                _write_schedule(out_dir, schedule_name, audits, stopped_early=True)
                return audits
    _write_schedule(out_dir, schedule_name, audits, stopped_early=False)
    return audits


def _write_schedule(out_dir, name, audits, stopped_early):
    summary = {
        "schema_version": "m1-schedule-1",
        "name": name,
        "timestamp": datetime.datetime.now().astimezone().isoformat(timespec="seconds"),
        "stopped_early": stopped_early,
        "n_runs": len(audits),
        "results": [a["result"] for a in audits],
        "runs": audits,
    }
    path = os.path.join(out_dir, f"{name}-schedule.json")
    tmp = path + ".tmp"
    with open(tmp, "w", encoding="utf-8") as fh:
        fh.write(json.dumps(summary, ensure_ascii=False, sort_keys=True, indent=2))
        fh.flush()
        os.fsync(fh.fileno())
    os.replace(tmp, path)
    return path
