#!/usr/bin/env python3
"""ier/cfg.py — Reconstruccion de bloques y aristas desde evidencia ELF. IER-EVOLVE-001 · M9.

## QUE ES

Un reconstructor de control de flujo INDEPENDIENTE del adapter: no consulta
rizin ni radare2 para construir su expectativa. Trabaja solo con
instrucciones decodificadas (GNU objdump) y reubicaciones del ELF.

## REGLAS FIJADAS (contrato RXRE-EVOLVE-001 §3)

    RET            terminador, 0 sucesores intraprocedimentales
    JMP directo    terminador, 1 sucesor intraproc si el destino cae en la
                   seccion; destino externo simbolico si va por reloc
    JMP indirecto  terminador, 0 intraproc + destino externo/no resuelto
    Jcc            terminador, 2 sucesores (taken / fallthrough)
    CALL           NO terminador: la continuacion vive DENTRO del propio
                   bloque. El salto a la funcion llamada es una CALL_EDGE
                   hacia destino externo o simbolico (via reloc).
    CALL noreturn  SOLO con evidencia independiente y regla explicita.
                   Este modulo NUNCA deduce noreturn de un nombre de
                   simbolo. En ET_REL tipico no hay evidencia: jamas se
                   declara CALL_NORET.

Una CALL conserva la continuacion: NUNCA genera un bloque por si sola y
NUNCA termina el bloque. Un CFG que trate `call` como terminador esta
malclasificado por definicion.
"""
from __future__ import annotations

import re
from typing import Any, Dict, List, Optional, Tuple

MODULE_REVISION = "ier-cfg-1"

JCC = {
    "je", "jne", "jz", "jnz", "jg", "jge", "jl", "jle", "ja", "jae",
    "jb", "jbe", "jo", "jno", "js", "jns", "jp", "jnp", "jpe", "jpo",
    "loope", "loopne", "loopnz", "loopz",
}


def _parse_target(operands: str):
    """(target_offset|None, is_indirect)."""
    op = operands.strip()
    if op.startswith("*"):
        return None, True
    m = re.match(r"^([0-9a-fA-F]+)\b", op)
    if m:
        try:
            return int(m.group(1), 16), False
        except ValueError:
            return None, True
    return None, True


def _rel32_symbolic(evidence: Dict[str, Any], section_index: int,
                    ins_off: int, ins_size: int):
    """Relocations cuyo operando es el de ESTA instruccion (rel32/rel8)."""
    for r in evidence.get("relocations", []):
        if r["target_section_index"] != section_index:
            continue
        delta = ins_off + ins_size - 4
        if r["r_offset"] != delta:
            continue
        if r["r_type"] not in (2, 4):  # R_X86_64_PC32, R_X86_64_PLT32
            continue
        name = None
        for t in ("symtab", "dynsym"):
            for s in evidence.get("symbols", []):
                if s["index"] == r["r_sym"] and s.get("symbol_table") == t:
                    name = s["name"]
                    break
            if name is not None:
                break
        return {"symbol": name or "", "r_type": r["r_type"],
                "r_addend": r["r_addend"],
                "via": "rela.%s" % r["source_section_name"].lstrip(".")}
    return None


def _terminal(ins: Dict[str, Any], evidence: Dict[str, Any], section_index: int):
    m = ins["mnemonic"]
    if m in ("ret", "iret", "iretq", "sysret", "sysexit"):
        return ("RET", None)
    if m == "call":
        return ("CALL", None)
    if m == "jmp":
        sym = _rel32_symbolic(evidence, section_index, ins["offset"], ins["size"])
        if sym and not ins["operands"].strip().startswith("*"):
            return ("JMP_SYMBOLIC", sym)
        tgt, ind = _parse_target(ins["operands"])
        if ind or tgt is None:
            return ("JMP_INDIRECT", None)
        return ("JMP_DIRECT", tgt)
    if m in JCC:
        tgt, ind = _parse_target(ins["operands"])
        return ("JCC", None if ind else tgt)
    return ("FALLTHROUGH", None)


def _ct_obj(kind: str, payload: Any) -> Dict[str, Any]:
    if kind == "JCC":
        return {"type": "JCC", "direction": "conditional", "target": payload}
    if kind == "JMP_DIRECT":
        return {"type": "JMP_DIRECT", "direction": "direct", "target": payload}
    if kind == "JMP_SYMBOLIC":
        return {"type": "JMP_SYMBOLIC", "direction": "direct",
                "target_symbol": payload.get("symbol")}
    if kind == "JMP_INDIRECT":
        return {"type": "JMP_INDIRECT", "direction": "indirect", "target": None}
    if kind == "RET":
        return {"type": "RET", "direction": "return", "target": None}
    return {"type": "FALLTHROUGH", "direction": "fallthrough", "target": None}


def build_cfg(evidence: Dict[str, Any]) -> Dict[str, Any]:
    if evidence.get("operational_status") != "PASS":
        return {"operational_status": evidence.get("operational_status", "BLOCKED"),
                "blocks": [], "edges": [],
                "limitations": ["CFG no construido: identificacion no PASS"],
                "stats": {"n_blocks": 0, "n_edges": 0, "n_call_edges": 0}}

    insns = evidence.get("instructions", [])
    if not insns:
        return {"operational_status": "ERROR", "blocks": [], "edges": [],
                "limitations": ["sin instrucciones decodificadas"],
                "stats": {"n_blocks": 0, "n_edges": 0, "n_call_edges": 0}}

    blocks: List[Dict[str, Any]] = []
    edges: List[Dict[str, Any]] = []
    limitations = [
        "noreturn NUNCA se deduce de un nombre de simbolo; en ET_REL no hay evidencia",
        "destinos externos (thunks) = CALL_EDGE/edge con destination simbolica, NO sucesor de bloque",
    ]

    by_sec: Dict[int, List[int]] = {}
    for i, ins in enumerate(insns):
        by_sec.setdefault(ins["section"], []).append(i)

    for sec_index, idxs in sorted(by_sec.items()):
        idxs.sort(key=lambda i: insns[i]["offset"])
        lst = [insns[i] for i in idxs]

        leaders = {0}
        for ins in lst:
            kind, payload = _terminal(ins, evidence, sec_index)
            fall = ins["offset"] + ins["size"]
            if kind == "FALLTHROUGH" or kind == "CALL":
                continue
            if kind == "RET":
                leaders.add(fall)  # cierra alcanzabilidad desde aqui
                continue
            if kind == "JCC":
                if isinstance(payload, int):
                    leaders.add(payload)
                leaders.add(fall)
                continue
            if kind == "JMP_DIRECT":
                if isinstance(payload, int):
                    leaders.add(payload)
                leaders.add(fall)
                continue
            if kind == "JMP_INDIRECT":
                leaders.add(fall)
                continue
            if kind == "JMP_SYMBOLIC":
                leaders.add(fall)
                continue

        # partir en bloques
        ranges: List[Tuple[int, int]] = []
        start = None
        for i, ins in enumerate(lst):
            off = ins["offset"]
            if i == 0 or off == 0 or off in leaders:
                if start is not None:
                    ranges.append((start, i))
                start = i
        if start is not None:
            ranges.append((start, len(lst)))

        sec_blocks: List[Dict[str, Any]] = []
        for b0, b1 in ranges:
            chunk = lst[b0:b1]
            ct_kind, ct_payload = _terminal(chunk[-1], evidence, sec_index)
            sec_blocks.append({
                "section": sec_index,
                "bytes_range": [chunk[0]["offset"], chunk[-1]["offset"] + chunk[-1]["size"]],
                "instruction_indices": idxs[b0:b1],
                "control_transfer": _ct_obj(ct_kind, ct_payload),
                "successors": [],
            })

        base = len(blocks)
        for b, sb in enumerate(sec_blocks):
            sb["id"] = base + b
        blocks.extend(sec_blocks)

        off2id = {(sb["section"], sb["bytes_range"][0]): sb["id"] for sb in sec_blocks}

        for sb in sec_blocks:
            ct = sb["control_transfer"]
            fall = sb["bytes_range"][1]
            if ct["type"] == "RET":
                edges.append({"source": sb["id"], "destination": None,
                              "kind": "return",
                              "evidence": ["terminator@%#x" % (sb["bytes_range"][1] - 1)]})
            elif ct["type"] == "JMP_DIRECT":
                tgt = ct["target"]
                dest = off2id.get((sb["section"], tgt))
                if dest is not None:
                    sb["successors"] = [dest]
                    edges.append({"source": sb["id"], "destination": dest,
                                  "kind": "direct",
                                  "evidence": ["jmp -> %#x" % tgt]})
                else:
                    edges.append({"source": sb["id"], "destination": None,
                                  "kind": "unresolved",
                                  "evidence": ["jmp -> %#x (externo/no resuelto)" % tgt]})
            elif ct["type"] == "JMP_SYMBOLIC":
                edges.append({"source": sb["id"],
                              "destination": ct["target_symbol"] or "symbolic_target",
                              "kind": "direct",
                              "evidence": ["jmp --symbolic--> %s" % ct["target_symbol"]]})
            elif ct["type"] == "JMP_INDIRECT":
                edges.append({"source": sb["id"], "destination": None,
                              "kind": "unresolved",
                              "evidence": ["jmp indirecto"]})
            elif ct["type"] == "JCC":
                tgt = ct["target"]
                succ = []
                taken = off2id.get((sb["section"], tgt)) if isinstance(tgt, int) else None
                fall_id = off2id.get((sb["section"], fall))
                if taken is not None:
                    succ.append(taken)
                    edges.append({"source": sb["id"], "destination": taken,
                                  "kind": "conditional_taken",
                                  "evidence": ["jcc taken -> %#x" % tgt]})
                if fall_id is not None:
                    succ.append(fall_id)
                    edges.append({"source": sb["id"], "destination": fall_id,
                                  "kind": "conditional_fall",
                                  "evidence": ["jcc fallthrough -> %#x" % fall]})
                sb["successors"] = succ
            else:  # FALLTHROUGH
                dest = off2id.get((sb["section"], fall))
                if dest is not None:
                    sb["successors"] = [dest]
                    edges.append({"source": sb["id"], "destination": dest,
                                  "kind": "fallthrough",
                                  "evidence": ["secuencial -> %#x" % fall]})
            # CALL_EDGE de TODAS las llamadas del bloque
            for ii in sb["instruction_indices"]:
                ins = insns[ii]
                if ins["mnemonic"] != "call":
                    continue
                sym = _rel32_symbolic(evidence, sec_index, ins["offset"], ins["size"])
                tgt, ind = _parse_target(ins["operands"])
                if sym:
                    dest = sym["symbol"] or "symbolic_target"
                    ev_l = ["call@%#x --reloc(%d) via %s--> %s"
                            % (ins["offset"], sym["r_type"], sym["via"], dest)]
                elif tgt is not None:
                    dest = "internal@%#x" % tgt
                    ev_l = ["call directo @%#x -> %#x" % (ins["offset"], tgt)]
                else:
                    dest = "unresolved_call_target"
                    ev_l = ["call indirecto @%#x" % ins["offset"]]
                edges.append({"source": sb["id"], "destination": dest,
                              "kind": "call", "evidence": ev_l})

    stats = {"n_blocks": len(blocks), "n_edges": len(edges),
             "n_call_edges": sum(1 for e in edges if e["kind"] == "call")}
    return {"operational_status": "PASS",
            "blocks": blocks, "edges": edges,
            "limitations": limitations,
            "stats": stats,
            "revision": MODULE_REVISION}
