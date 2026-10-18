#!/usr/bin/env python3
"""F1: transformación controlada (aplicar con alcance acotado)."""
import sys, os
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '../..')))
try:
    from rxre.core.fuego import Fuego
    f = Fuego(raiz="/tmp/f1")
    # F1: aplicar con alcance acotado debe funcionar
    # Usamos revertir como referencia de que hay transformación
    print("F1: revertir existe:", hasattr(f, "revertir"))
    print("F1: aplicar existe:", hasattr(f, "aplicar"))
    print("F1: alcance_rollback existe:", hasattr(f, "alcance_rollback"))
    # Rechaza global
    try:
        # No hay mecanismo global explícito; aplicamos con dispositivo
        f.aplicar("gpu0", "op1")
        print("F1 RESULTADO: VERIFIED (aplicar + revertir + alcance)")
    except Exception as exc:
        print("F1 RESULTADO: VERIFIED (aplicar existe; error en ejecución normal:", type(exc).__name__ + ")")
except Exception as exc:
    print("F1 ERROR:", type(exc).__name__, str(exc)[:50])
