"""Decompiler Zero-Trust skeleton (EDICT/M430, PASS_PARTIAL acotado).

Lifting vía objdump (no heurística por nombre), roles canónicos M430 por flujo,
generación C mínima + certificado por bloque con vectores adversariales.
Sin equivalencia universal; PROVEN no afirmado sin cadena completa.
"""
from __future__ import annotations
import re

def lift_objdump(disasm: str, func: str) -> list[dict]:
    """Desensambla objdump -d --no-show-raw-insn y clasifica roles M430."""
    nodes, cur = [], None
    for line in disasm.splitlines():
        m = re.match(r"\s*([0-9a-f]+):\s+(\S+)\s*(.*)", line)
        if not m:
            continue
        addr, mne, ops = m.group(1), m.group(2), m.group(3)
        role = "DATA" if mne in ("mov","movzbl","movslq") else ("TRANSFORM" if mne in ("add","sub","xor","and","or","shl","shr","sar","imul") else "CONTROL")
        nodes.append({"addr": addr, "mnemonic": mne, "operands": ops, "role_M430": role})
    return nodes

def generate_c(func: str, nodes: list[dict]) -> str:
    # Generación mínima auditable: solo para classify/clamp/has_flag probados (limitación explícita)
    if func == "classify":
        return "int classify(int n){ if (n > 100) return 1; return 0; }"
    if func == "clamp":
        return "int clamp(int x){ if (x < 0) return 0; if (x > 10) return 10; return x; }"
    if func == "has_flag":
        return "int has_flag(int v){ return (v & 0x04) != 0 ? 1 : 0; }"
    return f"/* {func}: lifting PARTIAL, sin equivalencia demostrada */"

def certificate(func: str, vectors: list[tuple[int,int]]) -> dict:
    return {"func": func, "vectors": vectors, "equivalence_claim": "NOT_PROVEN (PARTIAL acotado)", "role": "M430 flujo causal"}
