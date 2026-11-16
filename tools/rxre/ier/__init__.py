"""RXRE · IER — Ingenieria Inversa Evolutiva y Reparativa.

Paquete nuevo: trabajo aparte del nucleo heredado (core/, backends/).
Nada de aqui promociona capacidades ni publica nada por si mismo;
toda promocion a PROMOTED es dictado del propietario.
"""
from . import mission, capability, investigate_f02, cleanup_guard, territory, defect  # noqa: F401
from . import binexpr, cfg, differential  # noqa: F401
__all__ = ["mission", "capability", "investigate_f02", "cleanup_guard", "territory", "defect",
           "binexpr", "cfg", "differential"]
__version__ = "IER-0.6.0"
