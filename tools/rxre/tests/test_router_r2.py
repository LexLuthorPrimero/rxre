#!/usr/bin/env python3
"""R2: 4 capacidades en ADAPTERS."""
import sys, os
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '../..')))
try:
    from rxre.dispatch import ADAPTERS
    req = {"binary.functions", "source.semantic_search",
           "runtime.trace", "formal.check"}
    caps = set(ADAPTERS.keys())
    faltan = req - caps
    presentes = caps & req
    print("R2 PRESENTES:", presentes)
    print("R2 FALTANTES:", faltan)
    # R2 VERIFIED solo si las 4 existen
    assert not faltan, f"R2 PARTIAL: faltan {faltan}"
except Exception as exc:
    print("R2 EXCEPTION:", type(exc).__name__, str(exc)[:60])
