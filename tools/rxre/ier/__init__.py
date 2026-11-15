"""RXRE · IER — Ingenieria Inversa Evolutiva y Reparativa.

Paquete nuevo: trabajo aparte del nucleo heredado (core/, backends/).
Nada de aqui promociona capacidades ni publica nada por si mismo;
toda promocion a PROMOTED es dictado del propietario.
"""
from . import mission, capability  # noqa: F401
__all__ = ["mission", "capability"]
__version__ = "IER-0.1.0"
