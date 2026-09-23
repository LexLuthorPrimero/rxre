"""rx550-torneo — Fase 3 (preparación): experimento CONTROLADO sobre power1_cap.

TEST DE MECANISMO, NO optimización y SIN benchmarks. Escribe UNA sola variable:

    <hwmon RX 550>/power1_cap        (µW)

con readback obligatorio y restauración EXACTA del valor original. NO toca
`power/control`, DPM, SCLK/MCLK, power profile, voltajes ni clocks.

El hwmon se resuelve dinámicamente desde la GPU PCI `1002:699f` (nunca asume
`hwmon2`). Este módulo solo prepara el mecanismo; la prueba real requiere
autorización explícita y se ejecuta con `cap-write-test --confirm`.
"""
import os

from . import util
from . import write_test as wt

# Escalón moderado para el valor temporal por defecto (NO es un sweep).
DEFAULT_DELTA_UW = 5_000_000  # 5 W

# Nodos que deben permanecer intactos en Fase 3 (incluye power/control).
CONTROL_NODES3 = {
    "power_control": ("device", "power/control"),
    "power_dpm_force_performance_level": ("device", "power_dpm_force_performance_level"),
    "pp_dpm_sclk": ("device", "pp_dpm_sclk"),
    "pp_dpm_mclk": ("device", "pp_dpm_mclk"),
    "pp_power_profile_mode": ("device", "pp_power_profile_mode"),
}
STRICT_AUX3 = ("power_control", "power_dpm_force_performance_level", "pp_power_profile_mode")
NORMALIZED_AUX3 = ("pp_dpm_sclk", "pp_dpm_mclk")


def production_cap_node(gpu):
    """Nodo autorizado power1_cap del hwmon dinámico de la RX 550."""
    hwmon_real = os.path.realpath(gpu["hwmon"])
    authorized_real = os.path.join(hwmon_real, "power1_cap")
    logical = os.path.join(gpu["hwmon"], "power1_cap")
    return wt.SysfsNode(logical, authorized_real), logical


def read_limits(gpu):
    """Límites reales expuestos por sysfs para power1_cap (µW)."""
    hw = gpu["hwmon"]

    def ri(name, missing_ok=False):
        try:
            return util.read_int(os.path.join(hw, name), missing_ok=missing_ok)
        except util.SafeIOError as exc:
            raise wt.WriteTestError("LIMITS_UNREADABLE", f"{name}: {exc}")

    return {"min": ri("power1_cap_min"), "max": ri("power1_cap_max"),
            "default": ri("power1_cap_default", missing_ok=True)}


def read_aux3(gpu):
    """Lectura read-only de los nodos que NO deben cambiar en Fase 3."""
    dev = gpu["target"]["device"]
    hw = gpu["hwmon"]
    out = {}
    for name, (base, rel) in CONTROL_NODES3.items():
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


def validate_value(value, limits, original):
    """Rechazo ANTES de escribir: rango real y distinto del original."""
    if not isinstance(value, int):
        raise wt.WriteTestError("BAD_VALUE", f"valor no entero: {value!r}")
    lo, hi = limits["min"], limits["max"]
    if value < lo or value > hi:
        raise wt.WriteTestError("OUT_OF_RANGE", f"{value} µW fuera de [{lo}, {hi}]")
    if value == original:
        raise wt.WriteTestError("SAME_VALUE", f"{value} µW == original; no es un cambio")
    return value


def default_temporary(original, limits):
    """Valor temporal por defecto: baja un escalón si se puede; si no, sube."""
    lo, hi = limits["min"], limits["max"]
    if original > lo:
        cand = max(lo, original - DEFAULT_DELTA_UW)
    elif original < hi:
        cand = min(hi, original + DEFAULT_DELTA_UW)
    else:
        raise wt.WriteTestError("NO_ROOM", "sin rango para un valor distinto")
    if cand == original:
        raise wt.WriteTestError("NO_ROOM", "no se pudo proponer un valor distinto")
    return cand


class CapTestSession(wt.WriteTestSession):
    """Ciclo cap: preflight+rangos -> write -> readback -> rollback -> readback.

    Reutiliza el manejo de señales/errores y el guard de path de Fase 2.
    """

    def __init__(self, gpu, node, value=None, limits_reader=None,
                 aux_reader=None, hooks=None, capture_fn=None):
        super().__init__(gpu, node, aux_reader=aux_reader or read_aux3,
                         hooks=hooks, capture_fn=capture_fn)
        self.value = value
        self.limits_reader = limits_reader or read_limits
        self.limits = None
        self.original_int = None
        self.temporary_int = None
        self.delta = None

    def preflight(self):
        t = self.gpu["target"]
        if (t.get("vendor"), t.get("device_id")) != (0x1002, 0x699f):
            raise wt.WriteTestError("WRONG_GPU", f"GPU objetivo no es 1002:699f: {t.get('pci')}")
        if t.get("driver") != "amdgpu":
            raise wt.WriteTestError("WRONG_GPU", f"driver no amdgpu: {t.get('driver')}")
        if self.gpu["intel"]["vendor"] != 0x8086:
            raise wt.WriteTestError("WRONG_GPU", f"Intel no 0x8086: {self.gpu['intel'].get('pci')}")
        if self.gpu["intel"]["card"] == self.gpu["drm_card"]:
            raise wt.WriteTestError("WRONG_GPU", "objetivo == Intel; imposible")
        if not self.gpu.get("display_cards"):
            raise wt.WriteTestError("NO_DISPLAY",
                                    "no hay conector Intel 'connected'; display no confirmado")
        if not util.path_belongs_to_prefix(self.gpu["hwmon"], t["device"]):
            raise wt.WriteTestError(
                "BAD_HWMON", f"hwmon {self.gpu['hwmon']} no pertenece al device {t['device']}")
        self.node.verify_authorized()
        try:
            self.original = self.node.read()
            self.original_int = int(self.original)
        except util.SafeIOError as exc:
            raise wt.WriteTestError("NODE_UNREADABLE", f"no se pudo leer power1_cap: {exc}")
        except ValueError:
            raise wt.WriteTestError("UNKNOWN_VALUE", f"power1_cap no entero: {self.original!r}")
        self.limits = self.limits_reader(self.gpu)
        if not (self.limits["min"] <= self.original_int <= self.limits["max"]):
            raise wt.WriteTestError(
                "INCONSISTENT",
                f"original {self.original_int} µW fuera de límites {self.limits}")
        temp = self.value if self.value is not None else default_temporary(self.original_int,
                                                                          self.limits)
        validate_value(temp, self.limits, self.original_int)
        self.temporary_int = temp
        self.delta = temp - self.original_int
        self.aux_before = self.aux_reader(self.gpu)
        if self.capture_fn:
            try:
                self.full_capture = self.capture_fn()
            except Exception as exc:  # noqa: BLE001
                self._event("capture_error", error=f"{type(exc).__name__}: {exc}")
        self._event("preflight_ok", original=self.original, temporary=str(temp),
                    limits=self.limits, path=getattr(self.node, "path", None))
        return self.original

    def _calculate_temporary(self):
        return str(self.temporary_int)

    def _check_aux(self):
        self.aux_after = self.aux_reader(self.gpu)
        for key in STRICT_AUX3:
            before = self.aux_before.get(key)
            after = self.aux_after.get(key)
            if before != after:
                self.aux_diff.append((key, before, after))
        for key in NORMALIZED_AUX3:
            before = wt.normalize_dpm(self.aux_before.get(key))
            after = wt.normalize_dpm(self.aux_after.get(key))
            if before != after:
                self.aux_diff.append((key, before, after))
        if self.aux_diff:
            self.result = "AUX_CHANGED"
            raise wt.WriteTestError(
                "AUX_CHANGED",
                "nodos NO autorizados cambiaron: " + "; ".join(
                    f"{k}: {a!r} -> {b!r}" for k, a, b in self.aux_diff))

    def audit(self):
        a = super().audit()
        a["field"] = "power1_cap"
        a["limits"] = self.limits
        a["original_int"] = self.original_int
        a["temporary_int"] = self.temporary_int
        a["delta_int"] = self.delta
        return a
