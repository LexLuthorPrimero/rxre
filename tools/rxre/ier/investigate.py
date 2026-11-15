#!/usr/bin/env python3
# SPDX-License-Identifier: GPL-2.0
# WORK_CLASS=READ_ONLY
"""RXRE · IER · INVESTIGATE — hipotesis rivales y experimentos discriminantes.

La regla del juego: no acumules pruebas; elige el experimento que FALLE a
H1 o H2 (mejor: que solo una sobreviva). Cuando no existe un discriminante
honestamente disponible, la respuesta es abstenerse, no promocionar.
"""
from __future__ import annotations
import json
import os
from typing import Any, Dict, List, Optional


def _repo_root() -> str:
    return os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "..", ".."))


def _sha256_text(text: str) -> str:
    import hashlib
    return hashlib.sha256(text.encode("utf-8")).hexdigest()


def formular(statement: str, kind: str = "claim") -> Dict[str, Any]:
    hid = "hyp_" + _sha256_text(statement)[:16]
    return {"hypothesis_id": hid, "statement": statement, "kind": kind,
            "status": "pending"}


def discriminanes() -> List[str]:
    """Catalogo acotado de discriminantes disponibles hoy en RXRE."""
    return ["exit_code_delta", "output_hash_delta", "set_identity",
            "gdb_backtrace_delta", "decode_table_diff",
            "ir_lower_exception_quality"]


def elegir(misiones_razonamientos: Dict[str, List[str]]) -> Optional[str]:
    """Elige el primer discriminante aplicable; None si ninguno sirve."""
    disponibles = set(discriminanes())
    for disc in ("exit_code_delta", "output_hash_delta", "set_identity"):
        if disc in disponibles:
            return disc
    # gdb/harness solo si ambos ya citan esos observables
    for cand in ("gdb_backtrace_delta", "decode_table_diff",
                 "ir_lower_exception_quality"):
        for h in misiones_razonamientos.values():
            if cand in h and cand in disponibles:
                return cand
    return None


def contrastar(observacion: Dict[str, Any]) -> Dict[str, Any]:
    """Abastecedor determinista: dado X observado, decide si H gana/pierde.

    Demostracion minima; en produccion la captura la hacen los adapters.
    """
    disc = observacion.get("discriminant")
    h1, h2 = observacion.get("h1_result"), observacion.get("h2_result")
    if h1 is None or h2 is None:
        return {"decision": "NOT_DETERMINED",
                "reason": "faltan observaciones para ambas hipotesis"}
    if h1 == h2:
        return {"decision": "NOT_DETERMINED",
                "reason": "ambas hipotesis predicen el mismo observable"}
    if observacion.get("expected_h1") is not None:
        mine = observacion["expected_h1"]
        return {"decision": "H1" if h1 == mine else "H2",
                "expected": mine,
                "h1_result": h1, "h2_result": h2,
                "discriminant": disc}
    return {"decision": "NOT_DETERMINED",
            "reason": "sin prediccion de H1 verificable",
            "discriminant": disc}


def evaluar_falsabilidad(statement: str) -> Dict[str, Any]:
    """Un enunciado es semi-cuantitativo si lleva un ancla medible u observable
    concreto, o un límite físico propio (bytes, números, tamaños, hex, ABI)."""
    import re
    import hashlib
    s = statement.lower()
    numeros = bool(re.search(r"0[xX][0-9a-f]+|\d+", s))
    unidades = bool(re.search(r"\b(bytes?|kb|mb|bits?|tokens?|ms|µs|ns|hex|ascii|elf|aarch64|x86_64|i386)\b", s))
    cuantitativa = numeros or unidades
    return {"statement": statement,
            "semi_cuantitativa": cuantitativa,
            "numeros": numeros,
            "unidades": unidades,
            "falsador_sugerido": ("refinar: define qué observable invalida H, "
                                  "p. ej. bytes concretos comparados con H"),
            "statement_hash": _sha256_text(statement)}


def rechaza_inaceptable(statement: str) -> bool:
    s = statement.lower()
    marcas = ("siempre", "nunca", "todo", "nada", "si o no")
    return sum(1 for m in marcas if m in s) >= 2
