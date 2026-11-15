"""RXRE-LXXIX / M1207 — Clasificación por función (scope).

Capa ADITIVA sobre el clasificador existente. Conserva el `worst-wins` global
intacto: el dict devuelto incluye el veredicto global calculado sobre TODOS los
bloques del dump, exactamente con el mismo criterio que `classify_dump`.

Añade una segunda decisión INDEPENDIENTE:

  - `function_accept`: aceptación individual de una función completa dentro del
    dominio declarado (todos sus bloques/instrucciones == FAITHFUL).
  - `selection`      : la evaluación de la solicitud explícita del caller. Una
    función seleccionada solo se identifica por una tripleta verificable
    (etiqueta, start_addr, end_addr del bloque en el dump) y la solicitud está
    ligada OBLIGATORIAMENTE al hash del artefacto (`artifact_hash`).

Reglas implementadas (Plan LXXIX M1207):

  1. Una función solo se acepta si TODOS sus bloques/instrucciones son FAITHFUL.
  2. Bloques que no pertenecen a ninguna función seleccionada SIGUEN presentes
     en la evaluación global (ninguno desaparece).
  3. La aceptación funcional NO modifica ni sustituye el veredicto global.
  4. PARTIAL/UNSUPPORTED/INVALID conservan su efecto (worst-wins).
  5. El rechazo global por worst-wins permanece.
  6. La selección debe ser declarada explícitamente y ligada al hash del ELF.
  7. Sin comodines ni exclusiones implícitas: una selección solo nombra
     funciones; el resto del artefacto se evalúa SIEMPRE.
  8. Si `selection` es None (ausencia de la clave), el comportamiento es
     compatible con LXXVII: el caller simplemente no añade la evaluación de
     alcance al envelope.

Identidad de función: (label, start_addr, end_addr) del bloque en el dump.
Nunca el nombre aislado.
"""
from __future__ import annotations

import os
import re
import sys
from typing import Any, Dict, List, Optional

_PKG = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
if _PKG not in sys.path:
    sys.path.insert(0, _PKG)

from rxre.decompiler import fidelity as _fid  # noqa: E402

LINE_LABEL = re.compile(r"^([0-9a-f]+)\s+<([^>]+)>:")
LINE = re.compile(r"^\s+([0-9a-f]+):\s+((?:[0-9a-fA-F]{2}\s+)+)\s*(\S+)(?:\s+(.*))?$")
PREC = {"FAITHFUL": 1, "PARTIAL": 2, "UNSUPPORTED": 3, "INVALID": 4}


def _block_start(lines):
    for ln in lines:
        m = LINE.match(ln)
        if m:
            return int(m.group(1), 16)
    return None


def _block_end(lines):
    last = None
    for ln in lines:
        m = LINE.match(ln)
        if m:
            n = len(m.group(2).split())
            last = int(m.group(1), 16) + max(1, n)
    return last


def _ranges_problem(block_records):
    """Detecta rangos duplicados/solapados entre bloques.

    Devuelve dict {idx: set(reasons)}. Dos bloques con el MISMO rango exacto
    pero distinta etiqueta son EXACT_DUPLICATE_RANGE; bytes que se solapan son
    RANGE_OVERLAP.
    """
    rng = [(b["start_addr"], b["end_addr"], i)
           for i, b in enumerate(block_records)
           if b["start_addr"] is not None and b["end_addr"] is not None]
    problems: Dict[int, set] = {}
    for k, (a0, a1, i) in enumerate(rng):
        for b0, b1, j in rng[k + 1:]:
            if a0 == b0 and a1 == b1:
                problems.setdefault(i, set()).add("EXACT_DUPLICATE_RANGE")
                problems.setdefault(j, set()).add("EXACT_DUPLICATE_RANGE")
            elif a0 < b1 and b0 < a1:
                problems.setdefault(i, set()).add("RANGE_OVERLAP")
                problems.setdefault(j, set()).add("RANGE_OVERLAP")
    return problems


def _as_dict(entry):
    if isinstance(entry, str):
        return {"name": entry}
    if isinstance(entry, dict) and isinstance(entry.get("name"), str) and entry["name"].strip():
        out = {"name": entry["name"].strip()}
        if "address" in entry and entry["address"] is not None:
            out["address"] = entry["address"]
        if "artifact_sha256" in entry and entry["artifact_sha256"] is not None:
            out["artifact_sha256"] = entry["artifact_sha256"]
        return out
    return None


def evaluate_scope(dump_text: str, domain_file: Optional[str],
                   selection: Optional[List[Any]] = None,
                   artifact_hash: Optional[str] = None) -> Dict[str, Any]:
    """Evalúa el alcance (per-función) sin tocar el veredicto global.

    `selection` es una lista explícita. Cada elemento puede ser una cadena
    (nombre de función) o un dict {"name", "address"?, "artifact_sha256"?}.

    Requisitos de seguridad de la solicitud (Plan LXXIX M1207/M1208):

      - `artifact_hash` (sha256 del artefacto analizado) es OBLIGATORIO para
        cualquier selección no vacía; si falta -> selección rechazada.
      - un `artifact_sha256` por entrada que no coincide con `artifact_hash`
        -> entrada rechazada (la selección está ligada al ELF, no al nombre).
      - un `address` por entrada que no coincide con el inicio del bloque
        encontrado -> entrada rechazada.
      - nombre inexistente -> FUNCTION_NOT_FOUND; nombre ambiguo -> AMBIGUOUS.
      - rango duplicado/solapado en el bloque seleccionado -> rechazada.
    """
    contract = _fid.load_contract(domain_file)
    blocks = list(_fid.split_blocks(dump_text))
    block_records: List[Dict[str, Any]] = []
    for name, lines in blocks:
        verdict_obj = _fid.classify_block(lines, contract)
        insns = verdict_obj.get("instructions", [])
        # Igual que `classify_dump`: el preámbulo de objdump (name=None, sin
        # instrucciones) no es un bloque de código.
        if name is None and not insns:
            continue
        start, end = _block_start(lines), _block_end(lines)
        block_records.append({
            "label": name,
            "start_addr": start,
            "end_addr": end,
            "nbytes": sum(i["nbytes"] for i in insns),
            "insns_count": len(insns),
            "verdict": verdict_obj["verdict"],
            "reasons": list(verdict_obj.get("reasons", [])),
        })

    # --- reglas de pertenencia/integridad de rangos -------------------------
    problems = _ranges_problem(block_records)
    for idx, reasons in problems.items():
        block_records[idx]["reasons"].extend(sorted(reasons))

    # --- decisión por función y veredicto global (worst-wins) ----------------
    function_accept = {}
    for idx, b in enumerate(block_records):
        label = b["label"] if b["label"] else "<addr:%#x>" % (b["start_addr"] or 0)
        function_accept[label] = (b["verdict"] == "FAITHFUL")
    global_verdict = "FAITHFUL"
    for b in block_records:
        if PREC[b["verdict"]] > PREC[global_verdict]:
            global_verdict = b["verdict"]

    # --- evaluación de la solicitud explícita --------------------------------
    sel_result: Dict[str, Any] = {
        "requested": selection if selection is not None else [],
        "identified": [],
        "rejected": [],
        "reasons": [],
        "artifact_hash": artifact_hash,
        "requested_count": len(selection) if isinstance(selection, list) else None,
    }

    if selection is not None:
        if not isinstance(selection, list):
            sel_result["reasons"].append("SELECTION_NOT_A_LIST")
            sel_result["rejected"].append({"name": None, "reason": "SELECTION_NOT_A_LIST"})
        elif len(selection) == 0:
            sel_result["reasons"].append("SELECTION_EMPTY")
            sel_result["rejected"].append({"name": None, "reason": "SELECTION_EMPTY"})
        elif not artifact_hash:
            sel_result["reasons"].append("SELECTION_REQUIRES_ARTIFACT_HASH")
            sel_result["rejected"].append({"name": None, "reason": "SELECTION_REQUIRES_ARTIFACT_HASH"})
        else:
            seen_names: Dict[str, int] = {}
            for entry in selection:
                norm = _as_dict(entry)
                if norm is None:
                    sel_result["rejected"].append({"name": None, "reason": "SELECTION_ENTRY_INVALID"})
                    continue
                name = norm["name"]
                seen_names[name] = seen_names.get(name, 0) + 1
                if seen_names[name] > 1:
                    sel_result["rejected"].append({"name": name, "reason": "DUPLICATE_SELECTION_ENTRY"})
                    continue
                if norm.get("artifact_sha256") and norm["artifact_sha256"] != artifact_hash:
                    sel_result["rejected"].append({"name": name, "reason": "ARTIFACT_SHA256_MISMATCH"})
                    continue
                matches = [b for b in block_records if b["label"] == name]
                if norm.get("address") is not None:
                    try:
                        addr_req = int(norm["address"], 16) if isinstance(norm["address"], str) else int(norm["address"])
                    except (ValueError, TypeError):
                        sel_result["rejected"].append({"name": name, "reason": "SELECTION_ADDRESS_UNPARSEABLE"})
                        continue
                    addr_matches = [b for b in block_records if b["start_addr"] == addr_req]
                    if matches:
                        matches = [b for b in matches if b["start_addr"] == addr_req]
                    else:
                        matches = addr_matches
                    if not matches:
                        sel_result["rejected"].append({"name": name, "reason": "ADDRESS_NOT_FOUND"})
                        continue
                if not matches:
                    sel_result["rejected"].append({"name": name, "reason": "FUNCTION_NOT_FOUND"})
                    continue
                if len(matches) > 1:
                    sel_result["rejected"].append({"name": name, "reason": "AMBIGUOUS_FUNCTION"})
                    continue
                m = matches[0]
                idx = block_records.index(m)
                row_problems = problems.get(idx, set())
                if row_problems:
                    sel_result["rejected"].append({
                        "name": name,
                        "reason": "RANGE_INTEGRITY: %s" % ",".join(sorted(row_problems)),
                    })
                    continue
                sel_result["identified"].append({
                    "name": m["label"],
                    "address": "%#x" % m["start_addr"] if m["start_addr"] is not None else None,
                    "end_addr": "%#x" % m["end_addr"] if m["end_addr"] is not None else None,
                    "size": m["nbytes"],
                    "insns_count": m["insns_count"],
                    "verdict": m["verdict"],
                    "function_accept": m["verdict"] == "FAITHFUL",
                })

    scope_functions = [
        {
            "label": b["label"],
            "start_addr": "%#x" % b["start_addr"] if b["start_addr"] is not None else None,
            "end_addr": "%#x" % b["end_addr"] if b["end_addr"] is not None else None,
            "nbytes": b["nbytes"],
            "insns_count": b["insns_count"],
            "verdict": b["verdict"],
            "reasons": b["reasons"],
        }
        for b in block_records
    ]

    return {
        "verdict": global_verdict,
        "functions": scope_functions,
        "function_accept": function_accept,
        "selection": sel_result,
        "reasons": sorted({r for b in block_records for r in b["reasons"]}),
        "artifact_hash": artifact_hash,
    }
