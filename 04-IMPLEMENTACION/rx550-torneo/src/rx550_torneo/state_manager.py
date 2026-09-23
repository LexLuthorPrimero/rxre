"""rx550-torneo — state_manager. Snapshot/estado persistente y estructura de rollback de la Fase 1.

Fase 1: SOLO captura/lectura/validación. No aplica ninguna escritura de restauración.
"""
import datetime
import hashlib
import json
import os
import platform
import re
import shutil
import subprocess

from . import util
from .gpu_finder import DEFAULT_TARGET_PCI


RESTORABLE_FIELDS = [
    # (base, rel, nombre lógico, requiere escritura elevada)
    ("device", "power/control", "power_control", True),
    ("hwmon", "power1_cap", "power1_cap", True),
    ("device", "power_dpm_force_performance_level", "power_dpm_force_performance_level", True),
    ("device", "pp_dpm_sclk", "pp_dpm_sclk", True),
    ("device", "pp_dpm_mclk", "pp_dpm_mclk", True),
    ("device", "pp_power_profile_mode", "pp_power_profile_mode", True),
]

REQUIRED_STATE_KEYS = {
    "schema_version", "timestamp", "kernel", "target_pci", "intel_pci",
    "drm_card", "hwmon", "render_node", "driver", "vendor", "device_id",
    "restorable", "capture",
}


def _state_dir_abs(env=None):
    env = env if env is not None else os.environ
    return os.path.join(env.get("XDG_STATE_HOME", os.path.expanduser("~/.local/state")),
                        "rx550-torneo")


def _kalm_status():
    out = {"procs": [], "kalm_gpu_service": None}
    for pat in (r"kalmd\.py", r"kalm-lite\.py", r"kalm-gpu"):
        try:
            r = subprocess.run(["pgrep", "-af", pat], capture_output=True, text=True, timeout=5)
            for ln in (r.stdout or "").splitlines():
                out["procs"].append(ln.strip())
        except (OSError, subprocess.SubprocessError):
            pass
    try:
        r = subprocess.run(["systemctl", "is-active", "kalm-gpu.service"],
                           capture_output=True, text=True, timeout=5)
        out["kalm_gpu_service"] = (r.stdout or r.stderr or "").strip() or "unknown"
    except (OSError, subprocess.SubprocessError):
        out["kalm_gpu_service"] = "unknown"
    return out


def _mesa_status():
    out = {"glxinfo": None, "glxinfo_prime": None, "vulkan_devices": [],
           "custom_mesa_path": "/opt/mesa-26.2.2-rx550-haswell",
           "custom_mesa_exists": None}
    out["custom_mesa_exists"] = os.path.isdir(out["custom_mesa_path"])

    def glxinfo(extra_env=None, libgl_debug=False):
        """Ejecuta glxinfo -B con env SOLO para este proceso.

        Nota (fix Fase 1.1): el env debe aplicarse a glxinfo, no a 'command -v'.
        Antes se hacía `DRI_PRIME=1 command -v glxinfo && glxinfo -B`, con lo que
        DRI_PRIME afectaba a `command -v` y glxinfo corría sin DRI_PRIME.
        """
        if not shutil.which("glxinfo"):
            return None
        env = dict(os.environ)
        env.update(extra_env or {})
        if libgl_debug:
            env["LIBGL_DEBUG"] = "verbose"
        try:
            r = subprocess.run(["glxinfo", "-B"], capture_output=True, text=True,
                               timeout=20, env=env)
        except (OSError, subprocess.SubprocessError):
            return None
        if r.returncode != 0 or not r.stdout:
            return None
        info = {
            "renderer": util_read_pattern(r.stdout, "OpenGL renderer string"),
            "vendor": util_read_pattern(r.stdout, "OpenGL vendor string"),
            "version": util_read_pattern(r.stdout, "OpenGL version string"),
        }
        if libgl_debug:
            m = re.search(r"DRI_PRIME: device \d+\s+-\s+.*?selected \((/dev/dri/renderD[0-9]+)\)",
                          r.stderr or "")
            info["selected_render_node"] = m.group(1) if m else None
        return info

    out["glxinfo"] = glxinfo()
    # Selección GL de la RX 550 por vendor:device (Mesa DRI_PRIME); fallback a índice 1.
    prime = glxinfo({"DRI_PRIME": "1002:699f"}, libgl_debug=True)
    if not prime or (out["glxinfo"] and prime.get("renderer") == out["glxinfo"].get("renderer")):
        alt = glxinfo({"DRI_PRIME": "1"}, libgl_debug=True)
        if alt:
            prime = alt
    out["glxinfo_prime"] = prime

    try:
        r = subprocess.run(["vulkaninfo", "--summary"], capture_output=True, text=True, timeout=20)
        if r.returncode == 0 and r.stdout:
            lines = [ln.strip() for ln in r.stdout.splitlines() if "deviceName" in ln]
            out["vulkan_devices"] = lines
    except (OSError, subprocess.SubprocessError):
        pass
    return out


def util_read_pattern(text, key):
    for ln in text.splitlines():
        s = ln.strip()
        if s.startswith(key):
            return s.split(":", 1)[1].strip()
    return None


def _read_restorable(device_dir, hwmon_dir):
    snapshot = {}
    active = {}
    for base, rel, name, _w in RESTORABLE_FIELDS:
        root = hwmon_dir if base == "hwmon" else device_dir
        path = os.path.join(root, rel)
        txt = util.read_text(path, strip=False, missing_ok=False)
        lines = [ln for ln in txt.splitlines()]
        snapshot[name] = lines
        # marca '*' de estado activo (para poder restaurar nivel activo y contenido)
        active_txt = None
        for ln in lines:
            if "*" in ln:
                active_txt = ln.strip()
                break
        active[name] = active_txt
    return {"files": snapshot, "active": active}


def capture(gpu, target_pci=DEFAULT_TARGET_PCI):
    t = gpu["target"]
    dev = t["device"]
    hw = gpu["hwmon"]

    def dev_opt(rel, fun=util.read_text):
        try:
            return fun(os.path.join(dev, rel))
        except util.SafeIOError:
            return None

    def hw_opt(rel, fun=util.read_text):
        try:
            return fun(os.path.join(hw, rel))
        except util.SafeIOError:
            return None

    restorable = _read_restorable(dev, hw)

    cap_default = hw_opt("power1_cap_default")
    try:
        cap_max = hw_opt("power1_cap_max")
    except Exception:
        cap_max = None

    capture = {
        "live": {
            "power1_cap": hw_opt("power1_cap"),
            "power1_cap_default": cap_default,
            "power1_cap_max": cap_max,
            "power1_input": hw_opt("power1_input"),
            "temp1_input": hw_opt("temp1_input"),
            "freq1_input": hw_opt("freq1_input"),
            "gpu_busy_percent": dev_opt("gpu_busy_percent"),
            "mem_busy_percent": dev_opt("mem_busy_percent"),
            "mem_info_vram_used": dev_opt("mem_info_vram_used"),
            "mem_info_gtt_used": dev_opt("mem_info_gtt_used"),
            "runtime_status": dev_opt("power/runtime_status"),
        },
        "restorable": restorable,
    }

    state = {
        "schema_version": 1,
        "timestamp": datetime.datetime.now().astimezone().isoformat(timespec="seconds"),
        "kernel": platform.release(),
        "target_pci": target_pci,
        "intel_pci": gpu["intel_pci"],
        "drm_card": gpu["drm_card"],
        "hwmon": gpu["hwmon"],
        "render_node": gpu["render_node"],
        "driver": t["driver"],
        "vendor": t["vendor"],
        "device_id": t["device_id"],
        "bdf": t["bdf"],
        "intel_card": gpu["intel"]["card"],
        "intel_bdf": gpu["intel"]["bdf"],
        "intel_connectors": _connectors(gpu, "intel"),
        "target_connectors": _connectors(gpu, "target"),
        "kalm": _kalm_status(),
        "mesa": _mesa_status(),
        "restorable": restorable,
        "capture": capture,
    }
    return state


def _connectors(gpu, which):
    from .gpu_finder import _connector_status
    return _connector_status(gpu[which]["card"], gpu["drm_dir"])


# ---------------------------------------------------------------- JSON IO

def _canonical(state):
    return json.dumps(state, ensure_ascii=False, sort_keys=True, separators=(",", ":"))


def _sha(text):
    return hashlib.sha256(text.encode("utf-8")).hexdigest()


def _atomic_write_text(path, text):
    tmp = path + ".tmp"
    digest = _sha(text.strip())
    with open(tmp, "w", encoding="utf-8") as fh:
        fh.write(text)
        fh.flush()
        os.fsync(fh.fileno())
    os.replace(tmp, path)
    with open(path + ".sha256", "w", encoding="utf-8") as fh:
        fh.write(digest + "\n")


class StateFileExists(Exception):
    def __init__(self, path):
        super().__init__(f"ya existe un estado en {path}; usar --force para sobrescribir")


def state_paths(state_dir=None):
    state_dir = state_dir or _state_dir_abs()
    return state_dir, os.path.join(state_dir, "state.json")


def save(state, state_dir=None, force=False, audit_hook=None):
    state_dir, sp = state_paths(state_dir)
    canonical = _canonical(state)
    dig = _sha(canonical)

    if not os.path.isdir(state_dir):
        os.makedirs(state_dir, mode=0o700)

    if os.path.exists(sp) and not force:
        existing = read_if_valid(sp)
        if existing is not None:
            raise StateFileExists(sp)

    _atomic_write_text(sp, canonical + "\n")
    if audit_hook:
        audit_hook(sp)
    return {"path": sp, "sha256": dig, "bytes": len(canonical)}


def read_if_valid(sp):
    """Devuelve el dict si el JSON es válido y el hash coincide; None si no existe; lanza si corrupto."""
    if not os.path.exists(sp):
        return None
    body = open(sp, "r", encoding="utf-8").read().strip()
    try:
        data = json.loads(body)
    except json.JSONDecodeError as exc:
        raise util.SafeIOError(f"estado corrupto (JSON inválido) en {sp}: {exc}")
    sha_path = sp + ".sha256"
    if os.path.exists(sha_path):
        want = open(sha_path, "r").read().strip()
        if _sha(body) != want:
            raise util.SafeIOError(f"estado corrupto (hash no coincide) en {sp}")
    return data


def load(state_dir=None):
    state_dir, sp = state_paths(state_dir)
    return sp, read_if_valid(sp)


def validate_schema(state):
    if not isinstance(state, dict):
        return ["no es un objeto"]
    errs = []
    for k in REQUIRED_STATE_KEYS:
        if k not in state:
            errs.append(f"falta clave {k}")
    return errs


def load_for_rollback(state_dir=None):
    """Carga el estado y Reporta si tiene TODO lo necesario para restaurar (sin aplicar)."""
    sp, st = load(state_dir)
    if st is None:
        raise util.SafeIOError(f"no hay estado que cargar en {sp}")
    errs = validate_schema(st)
    if errs:
        raise util.SafeIOError("estado inválido: " + "; ".join(errs))
    missing = [name for _b, _r, name, _w in RESTORABLE_FIELDS
               if st["restorable"]["files"].get(name) is None]
    return {"path": sp, "state": st, "missing_restorable": missing}