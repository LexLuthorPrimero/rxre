"""rx550-torneo — Fase 2: prueba CONTROLADA de escritura única + rollback.

ESTO ES UN TEST DE MECANISMO, NO UNA FUNCIÓN DE OPTIMIZACIÓN.

Autorizado a escribir UNA sola variable:

    <device RX 550>/power/control      (valores válidos: on | auto)

Flujo validado de extremo a extremo:

    CAPTURA -> WRITE ÚNICO -> READBACK -> ROLLBACK -> READBACK FINAL

Nada más se escribe. Todos los demás nodos de control se comparan antes/después
y deben quedar idénticos. La escritura real requiere privilegios (root); las
pruebas inyectan nodos en memoria y nunca tocan sysfs.

Nota de diseño: `util.guard_no_sys_write` sigue vigente para todo el resto del
programa. Esta fase la omite ÚNICAMENTE para el nodo autorizado, y `SysfsNode`
verifica que el path real coincida con el `power/control` del device de la
RX 550 antes de cada escritura.
"""
import datetime
import json
import os
import signal

from . import util

AUTHORIZED_FIELD = "power_control"
AUTHORIZED_REL = os.path.join("power", "control")
VALID_VALUES = ("on", "auto")

# Nodos de control que NUNCA deben cambiar (comparación estricta before/after).
CONTROL_NODES = {
    "power1_cap": ("hwmon", "power1_cap"),
    "power_dpm_force_performance_level": ("device", "power_dpm_force_performance_level"),
    "pp_dpm_sclk": ("device", "pp_dpm_sclk"),
    "pp_dpm_mclk": ("device", "pp_dpm_mclk"),
    "pp_power_profile_mode": ("device", "pp_power_profile_mode"),
}
# Comprobación estricta byte a byte (settings).
STRICT_AUX = ("power1_cap", "power_dpm_force_performance_level", "pp_power_profile_mode")
# Tablas DPM: el marcador '*' de nivel activo es telemetría en vivo y cambia
# solo; se comparan normalizadas (sin '*'), no byte a byte.
NORMALIZED_AUX = ("pp_dpm_sclk", "pp_dpm_mclk")
# runtime_status es consecuencia directa de power/control: solo se registra.

WRITE_REJECT_CODES = ("WRITE_PERMISSION", "WRITE_FAILED")


class WriteTestError(Exception):
    """Error seguro de la prueba de escritura, con código clasificable."""

    def __init__(self, code, message):
        super().__init__(message)
        self.code = code
        self.message = message


class CriticalRollbackError(WriteTestError):
    """El rollback no pudo verificarse. No se intenta nada más."""


class WriteTestInterrupted(WriteTestError):
    """Señal recibida durante la operación; dispara rollback."""

    def __init__(self, signum):
        try:
            name = signal.Signals(signum).name
        except ValueError:
            name = str(signum)
        super().__init__("INTERRUPTED", f"señal {name} durante el test")
        self.signum = signum


def alternate(value):
    """Valor alternativo válido para power/control."""
    if value not in VALID_VALUES:
        raise WriteTestError(
            "UNKNOWN_VALUE",
            f"valor no manejado {value!r}; válidos={VALID_VALUES}; no se escribe")
    return "auto" if value == "on" else "on"


def production_node(gpu):
    """Resuelve el nodo autorizado real a partir de la topología descubierta.

    Devuelve (SysfsNode, logical_path). No asume card1: usa gpu['drm_card'].
    """
    device_real = os.path.realpath(gpu["target"]["device"])
    authorized_real = os.path.join(device_real, "power", "control")
    logical = os.path.join("/sys/class/drm", gpu["drm_card"], "device", "power", "control")
    return SysfsNode(logical, authorized_real), logical


# ------------------------------------------------------------------- nodos

class SysfsNode:
    """Nodo sysfs autorizado (producción). Guard estricto de path."""

    def __init__(self, path, authorized_real):
        self.path = path
        self.authorized_real = os.path.realpath(authorized_real)

    def verify_authorized(self):
        real = os.path.realpath(self.path)
        if real != self.authorized_real:
            raise WriteTestError(
                "PATH_INVALID",
                f"{self.path} -> {real} != autorizado {self.authorized_real}")
        if not real.startswith("/sys/"):
            raise WriteTestError("PATH_INVALID", f"no es sysfs: {real}")
        return True

    def read(self):
        return util.read_text(self.path, strip=True, missing_ok=False)

    def write(self, value):
        self.verify_authorized()
        try:
            with open(self.path, "w", encoding="utf-8") as fh:
                fh.write(value)
        except PermissionError:
            raise WriteTestError("WRITE_PERMISSION", f"sin permiso de escritura: {self.path}")
        except OSError as exc:
            raise WriteTestError("WRITE_FAILED", f"error de escritura {self.path}: {exc}")


class FileNode:
    """Archivo plano. SOLO tests: se niega a apuntar a /sys."""

    def __init__(self, path):
        self.path = path

    def verify_authorized(self):
        if os.path.realpath(self.path).startswith("/sys/"):
            raise WriteTestError("PATH_INVALID", "FileNode no puede apuntar a /sys")
        return True

    def read(self):
        return util.read_text(self.path, strip=True, missing_ok=False)

    def write(self, value):
        self.verify_authorized()
        try:
            with open(self.path, "w", encoding="utf-8") as fh:
                fh.write(value)
        except OSError as exc:
            raise WriteTestError("WRITE_FAILED", f"error de escritura {self.path}: {exc}")


class FakeNode:
    """Nodo en memoria para tests unitarios. Nunca toca sysfs.

    - bad_readback: valor erróneo devuelto en el primer readback tras el write.
    - fail_read / fail_read_after_write: simulan pérdida de acceso al nodo.
    """

    def __init__(self, value="on", authorized=True, fail_read=False, fail_write=False,
                 fail_write_always=False, bad_readback=None, fail_read_after_write=False):
        self.value = value
        self.authorized = authorized
        self.fail_read = fail_read
        self.fail_write = fail_write
        self.fail_write_always = fail_write_always
        self.bad_readback = bad_readback
        self.fail_read_after_write = fail_read_after_write
        self.writes = []
        self._post_write = False
        self._pending_bad = None

    def verify_authorized(self):
        if not self.authorized:
            raise WriteTestError("PATH_INVALID", "ruta simulada no autorizada")
        return True

    def read(self):
        if self.fail_read:
            raise util.SafeIOError("lectura simulada fallida")
        if self._post_write and self.fail_read_after_write:
            raise util.SafeIOError("lectura simulada fallida tras el write")
        if self._pending_bad is not None:
            val = self._pending_bad
            self._pending_bad = None
            return val
        return self.value

    def write(self, value):
        self.verify_authorized()
        if self.fail_write_always or self.fail_write:
            raise WriteTestError("WRITE_FAILED", "escritura simulada rechazada")
        self.value = value
        self.writes.append(value)
        if not self._post_write:
            self._post_write = True
            if self.bad_readback is not None:
                self._pending_bad = self.bad_readback


# --------------------------------------------------------------- auxiliares

def read_aux(gpu):
    """Lectura read-only de los nodos de control + runtime_status."""
    dev = gpu["target"]["device"]
    hw = gpu["hwmon"]
    out = {}
    for name, (base, rel) in CONTROL_NODES.items():
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


def _now():
    return datetime.datetime.now().astimezone()


def normalize_dpm(text):
    """Quita el marcador '*' de nivel activo de una tabla pp_dpm_* (telemetría)."""
    if text is None:
        return None
    return "\n".join(ln.replace(" *", "").rstrip() for ln in text.splitlines()).strip()


# ------------------------------------------------------------------ sesión

class WriteTestSession:
    """Ejecuta el ciclo captura -> write -> readback -> rollback -> readback.

    Inyectable para tests: `node` (obligatorio), `aux_reader`, `hooks`
    (p.ej. {'after_write': fn}) y `capture_fn`. En producción no se usan hooks.
    """

    def __init__(self, gpu, node, aux_reader=None, hooks=None, capture_fn=None):
        self.gpu = gpu
        self.node = node
        self.aux_reader = aux_reader or read_aux
        self.hooks = hooks or {}
        self.capture_fn = capture_fn
        self.original = None
        self.temporary = None
        self.readback = None
        self.restored = None
        self.readback_final = None
        self.result = "NOT_STARTED"
        self.events = []
        self.rollback_attempts = 0
        self.aux_before = {}
        self.aux_after = {}
        self.aux_diff = []
        self.full_capture = None
        self._old_handlers = {}
        self._write_started = False
        self._wrote = False

    # -- auditoría ------------------------------------------------------
    def _event(self, name, **kw):
        ev = {"t": _now().isoformat(timespec="milliseconds"), "event": name}
        ev.update(kw)
        self.events.append(ev)

    def audit(self):
        t = self.gpu["target"]
        cap_summary = None
        if isinstance(self.full_capture, dict):
            cap_summary = {
                "timestamp": self.full_capture.get("timestamp"),
                "capture": self.full_capture.get("capture"),
            }
        return {
            "schema_version": 1,
            "timestamp": _now().isoformat(timespec="seconds"),
            "pci_id": f"{t.get('vendor', 0):04x}:{t.get('device_id', 0):04x}",
            "drm_card": self.gpu.get("drm_card"),
            "bdf": t.get("bdf"),
            "path": getattr(self.node, "path", None),
            "original": self.original,
            "temporary": self.temporary,
            "readback": self.readback,
            "restored": self.restored,
            "readback_final": self.readback_final,
            "result": self.result,
            "rollback_attempts": self.rollback_attempts,
            "aux_before": self.aux_before,
            "aux_after": self.aux_after,
            "aux_diff": self.aux_diff,
            "aux_unchanged": not self.aux_diff,
            "events": self.events,
            "capture_before": cap_summary,
        }

    # -- señales --------------------------------------------------------
    def _install_handlers(self):
        def handler(signum, _frame):
            raise WriteTestInterrupted(signum)
        for sig in (signal.SIGINT, signal.SIGTERM):
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

    # -- preflight ------------------------------------------------------
    def preflight(self):
        t = self.gpu["target"]
        if (t.get("vendor"), t.get("device_id")) != (0x1002, 0x699f):
            raise WriteTestError("WRONG_GPU", f"GPU objetivo no es 1002:699f: {t.get('pci')}")
        if t.get("driver") != "amdgpu":
            raise WriteTestError("WRONG_GPU", f"driver del objetivo no es amdgpu: {t.get('driver')}")
        if self.gpu["intel"]["vendor"] != 0x8086:
            raise WriteTestError("WRONG_GPU", f"Intel no 0x8086: {self.gpu['intel'].get('pci')}")
        if self.gpu["intel"]["card"] == self.gpu["drm_card"]:
            raise WriteTestError("WRONG_GPU", "objetivo == Intel; imposible")
        if not self.gpu.get("display_cards"):
            raise WriteTestError("NO_DISPLAY",
                                 "no hay conector Intel 'connected'; display no confirmado")
        self.node.verify_authorized()
        try:
            self.original = self.node.read()
        except util.SafeIOError as exc:
            raise WriteTestError("NODE_UNREADABLE", f"no se pudo leer el nodo: {exc}")
        if self.original not in VALID_VALUES:
            raise WriteTestError(
                "UNKNOWN_VALUE",
                f"valor original inesperado {self.original!r}; no se escribe nada")
        self.aux_before = self.aux_reader(self.gpu)
        if self.capture_fn:
            try:
                self.full_capture = self.capture_fn()
            except Exception as exc:  # noqa: BLE001
                self._event("capture_error", error=f"{type(exc).__name__}: {exc}")
        self._event("preflight_ok", original=self.original, path=getattr(self.node, "path", None))
        return self.original

    # -- rollback -------------------------------------------------------
    def _rollback(self):
        if self.original is None:
            raise CriticalRollbackError("NO_ORIGINAL", "sin valor original para restaurar")
        self.rollback_attempts += 1
        self._event("rollback_begin", value=self.original)
        self.node.write(self.original)
        self.restored = self.original
        self.readback_final = self.node.read()
        self._event("rollback_readback", value=self.readback_final)
        if self.readback_final != self.original:
            self.result = "CRITICAL"
            raise CriticalRollbackError(
                "ROLLBACK_MISMATCH",
                f"CRÍTICO: rollback no verificado: {self.readback_final!r} != {self.original!r}")
        self.result = "ROLLED_BACK"
        return True

    def _safe_rollback(self, reason):
        """Intentar restaurar UNA sola vez. Si falla: CRITICAL y no continuar."""
        if not self._write_started or self.rollback_attempts >= 1:
            return
        try:
            self._rollback()
            self._event("rollback_ok", reason=reason)
        except Exception as exc:  # noqa: BLE001
            self.result = "CRITICAL"
            self._event("rollback_failed", reason=reason, error=f"{type(exc).__name__}: {exc}")

    def _check_aux(self):
        self.aux_after = self.aux_reader(self.gpu)
        for key in STRICT_AUX:
            before = self.aux_before.get(key)
            after = self.aux_after.get(key)
            if before != after:
                self.aux_diff.append((key, before, after))
        for key in NORMALIZED_AUX:
            before = normalize_dpm(self.aux_before.get(key))
            after = normalize_dpm(self.aux_after.get(key))
            if before != after:
                self.aux_diff.append((key, before, after))
        if self.aux_diff:
            self.result = "AUX_CHANGED"
            raise WriteTestError(
                "AUX_CHANGED",
                "nodos NO autorizados cambiaron: " + "; ".join(
                    f"{k}: {a!r} -> {b!r}" for k, a, b in self.aux_diff))

    # -- ejecución ------------------------------------------------------
    def _calculate_temporary(self):
        """Valor temporal. Fase 2: alterna on/auto. Subclases (p.ej. cap) lo sobrescriben."""
        return alternate(self.original)

    def run(self):
        self.preflight()
        try:
            self._install_handlers()
            self.temporary = self._calculate_temporary()
            self._write_started = True
            self._event("write_begin", value=self.temporary, path=getattr(self.node, "path", None))
            self.node.write(self.temporary)
            self._wrote = True
            self._event("write_ok", value=self.temporary)
            hook = self.hooks.get("after_write")
            if hook:
                hook(self)
            self.readback = self.node.read()
            self._event("readback", value=self.readback)
            if self.readback != self.temporary:
                raise WriteTestError(
                    "READBACK_MISMATCH",
                    f"readback {self.readback!r} != temporal {self.temporary!r}")
            self._rollback()
            self._check_aux()
            self.result = "OK"
        except WriteTestError as exc:
            if exc.code in WRITE_REJECT_CODES and not self._wrote:
                self.result = "ERROR"
                self._event("write_rejected", code=exc.code, message=exc.message)
            else:
                self._safe_rollback(reason=exc.code)
                if exc.code == "INTERRUPTED":
                    self.result = "INTERRUPTED"
                elif self.result not in ("CRITICAL", "AUX_CHANGED"):
                    self.result = "ERROR"
                self._event("error", code=exc.code, message=exc.message)
            raise
        except BaseException as exc:  # noqa: BLE001
            self._safe_rollback(reason="UNEXPECTED")
            if self.result not in ("CRITICAL", "AUX_CHANGED"):
                self.result = "ERROR"
            self._event("unexpected", error=f"{type(exc).__name__}: {exc}")
            raise
        finally:
            self._restore_handlers()
        return self.audit()


# ------------------------------------------------------------- persistencia

def save_audit(audit, state_dir):
    """Persistencia atómica del registro de auditoría (nunca en /sys)."""
    os.makedirs(state_dir, mode=0o700, exist_ok=True)
    stamp = datetime.datetime.now().strftime("%Y%m%d-%H%M%S")
    path = os.path.join(state_dir, f"write-test-{stamp}.json")
    text = json.dumps(audit, ensure_ascii=False, sort_keys=True, indent=2)
    tmp = path + ".tmp"
    with open(tmp, "w", encoding="utf-8") as fh:
        fh.write(text)
        fh.flush()
        os.fsync(fh.fileno())
    os.replace(tmp, path)
    return path
