"""rx550-torneo — failsafe. Preflight de seguridad y estructura de rollback.

Fase 1: read-only. El rollback NUNCA se aplica; solo se valida que el estado
capturado contiene TODO lo necesario para una futura restauración y se
documenta el requisito de privilegios elevados para esa futura fase.
"""
import os


class NotSupported(Exception):
    """Operación que requeriría escritura y no está disponible en Fase 1."""


class RollbackPlan:
    def __init__(self, state, gpu):
        self.state = state
        self.gpu = gpu
        self.device_dir = gpu["target"]["device"]
        self.blocked_root = []

    def describe_restorations(self):
        """Elementos restaurables y si requieren escritura con privilegios."""
        dev = self.device_dir
        items = []
        for base, rel, name, needs_elevated in state_manager_STATIC_restorable():
            root = self.gpu["hwmon"] if base == "hwmon" else dev
            logical = os.path.join(root, rel)
            items.append({
                "field": name,
                "logical_path": logical,
                "requires_write": True,
                "requires_elevated": needs_elevated,
                "restorable": True,
            })
        return items

    def check_write_permissions(self):
        """Fase 1: ninguna escritura se ejecuta. Reporta el requisito futuro."""
        return [
            f"{name}: restaurar {rel} requiere permiso de escritura "
            f"{'(root)' if elevado else ''} — No ejecutado en Fase 1"
            for base, rel, name, elevado in state_manager_STATIC_restorable()
        ]

    def apply(self, dry_run=True):
        raise NotSupported(
            "aplicar restauración requiere autorización de escritura; "
            "no disponible en Fase 1 (read-only). Sistema sin modificar.")


def _state_manager_module():
    from . import state_manager
    return state_manager


def state_manager_STATIC_restorable():
    return _state_manager_module().RESTORABLE_FIELDS


def preflight_readonly(gpu):
    """Chequeos previos a cualquier operación. No escribe nada."""
    guards = []
    dev = gpu["target"]["device"]
    from .gpu_finder import validate_no_display_on_target
    validate_no_display_on_target(gpu)          # raise si RX 550 tiene display
    for base, rel, _n, _e in state_manager_STATIC_restorable():
        p = os.path.join(dev if base == "device" else gpu["hwmon"], rel)
        if not os.path.exists(p):
            guards.append(f"falta archivo restaurable: {p}")
    if not os.path.isdir(os.path.join(dev, "hwmon")):
        guards.append(f"falta hwmon bajo {dev}")
    return guards