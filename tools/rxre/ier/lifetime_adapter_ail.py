#!/usr/bin/env python3
"""RXRE · IER · LIFETIME_ADAPTER_AIL — extracción genérica desde angr AIL.

Convierte el grafo AIL decompilado en un documento de evidencia temporal
(`ryi-lifetime-evidence/2`) consumible por `ier.lifetime_contract.evaluate`.

Todo el conocimiento *específico del fixture* viaja como datos (`lives_spec`
o el documento ya construido); este módulo es genérico:

  esteroyecto AIL → CFG (refs de pila) → documento + vidas (parámetro)

Ningún offset, vvar ni dirección está hard-coded aquí.
"""
from __future__ import annotations

import json
import re
from typing import Any, Dict, List, Optional, Tuple

SCHEMA = "ryi-lifetime-evidence/2"
CAPABILITY_ID = "lifetime_adapter_ail"

_VVAR_RE = re.compile(r"Reference\s*\(\s*(vvar_\d+)\{s(-?\d+)\|(\d+)b\}")
_VVAR_BARE_RE = re.compile(r"(vvar_\d+)\{s(-?\d+)\|(\d+)b\}")
_SP_RE = re.compile(r"sp-(\d+)(?!\d)")


def _stmt_refs(stmt_str: str) -> List[Dict[str, Any]]:
    """Extrae referencias de pila de un enunciado AIL (str(x))."""
    refs: List[Dict[str, Any]] = []
    seen: set = set()

    def add(rid, base, size, kind):
        if rid in seen:
            return
        seen.add(rid)
        refs.append({"id": rid, "base": base, "size": size, "end": base + size, "kind": kind})

    for m in _VVAR_RE.finditer(stmt_str):
        add(m.group(1), int(m.group(2)), int(m.group(3)), "vvar")
    for m in _VVAR_BARE_RE.finditer(stmt_str):
        add(m.group(1), int(m.group(2)), int(m.group(3)), "vvar")
    for m in _SP_RE.finditer(stmt_str):
        rid = "sp-%s" % m.group(1)
        if rid in seen:
            continue
        seen.add(rid)
        base = -int(m.group(1))
        refs.append({"id": rid, "base": base, "size": 8, "end": base + 8, "kind": "stack_offset"})
    return refs


def _stmt_complete(stmt_str: str) -> bool:
    """True si el enunciado no contiene pila sin ligar."""
    if "sp-" not in stmt_str and "{s-" not in stmt_str:
        return True
    return bool(_VVAR_RE.search(stmt_str) or _VVAR_BARE_RE.search(stmt_str)
                or _SP_RE.search(stmt_str))


def collect_cfg_from_decompiler(d) -> Dict[str, Any]:
    """Extrae CFG + statements + refs desde un Decompiler ya ejecutado.

    Devuelve {"entry", "coverage", "nodes"}; los nodos AIL con la misma
    dirección se fusionan en el primero visto y los successors se re-atan a
    ese id (el grafo AIL contiene duplicados equivalentes)."""
    graph = d.ail_graph
    first_of_addr: Dict[int, str] = {}
    entries: List[Tuple[str, object, int]] = []
    occurrence: Dict[int, int] = {}

    for n in graph.nodes():
        addr = getattr(n, "addr", None)
        if addr is None:
            continue
        occ = occurrence.get(addr, 0)
        occurrence[addr] = occ + 1
        nid = "0x%x#0" % addr
        first_of_addr.setdefault(addr, nid)
        if addr in first_of_addr and first_of_addr[addr] == nid:
            entries.append((nid, n, addr))

    nodes: Dict[str, Dict[str, Any]] = {}
    for nid, n, addr in entries:
        stmts = getattr(n, "statements")
        slist = []
        for i, s in enumerate(stmts):
            sstr = str(s)
            slist.append({
                "id": "%s#%d" % (nid, i),
                "raw": sstr,
                "stack_refs": _stmt_refs(sstr),
                "references_complete": _stmt_complete(sstr),
            })
        succs = []
        for t in graph.successors(n):
            taddr = getattr(t, "addr", None)
            if taddr is None:
                continue
            tid = first_of_addr.get(taddr)
            if tid is not None and tid not in succs:
                succs.append(tid)
        nodes[nid] = {"addr": int(addr), "statements": slist, "successors": succs}

    entry = min(nodes, key=lambda k: nodes[k]["addr"])
    return {"entry": entry, "coverage": "complete", "nodes": nodes}


def build_document(*, artifact_sha256: str, artifact_path: str, architecture: str,
                   function_entry: int, cfg: Dict[str, Any],
                   lives: List[Dict[str, Any]], candidate: Dict[str, Any],
                   seal_sha256: Optional[str] = None) -> Dict[str, Any]:
    doc = {
        "version": SCHEMA,
        "artifact": {"path": artifact_path, "sha256": artifact_sha256,
                     "architecture": architecture},
        "function": {"entry": hex(function_entry)},
        "cfg": cfg,
        "lives": lives,
        "candidate": candidate,
        "producer": {"tool": CAPABILITY_ID, "schema": SCHEMA},
    }
    if seal_sha256:
        doc["seal_sha256"] = seal_sha256
    return doc


def seal_document(doc: Dict[str, Any]) -> Dict[str, Any]:
    from ier.lifetime_contract import _canonical_seal
    doc = dict(doc)
    doc.pop("seal_sha256", None)
    doc["seal_sha256"] = _canonical_seal(doc)
    return doc
