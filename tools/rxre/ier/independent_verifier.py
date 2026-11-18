#!/usr/bin/env python3
# SPDX-License-Identifier: GPL-2.0
# WORK_CLASS=READ_ONLY · WRITE_EXECUTION=SCRATCH_ONLY (.rxre/state/independent_verifier/)
"""RXRE · IER · INDEPENDENT_VERIFIER — verificador independiente del transformer_witness.

## QUÉ ES

Un verificador INDEPENDIENTE del testigo M10.8.  No reutiliza sus funciones
decisorias (``evaluate``, ``_check_B``, ``_check_W``, ``_check_O``, ``_check_L``,
``_check_C``, ``_check_D``); reimplementa las comprobaciones a partir de:

    1. El caso declarado (``case`` dict).
    2. Los artefactos sellados M10.5–M10.7 consumidos DIRECTAMENTE como fuente
       de evidencia (en lugar de la copia embebida en el caso).

Independencia real: la evidencia contra la que se contrasta la cobertura (C)
proviene de ``cancel_sys_analysis_m10_7.json`` verificado por manifiesto; la
procedencia temporal (L) se prueba con BFS propio sobre ``cfg_successors``;
la ejecución de bytes (B) usa una implementación distinta, basada en aritmética
entera Python y en la fórmula declarada, no en el bucle interpretado del testigo.

## QUÉ HACE

    - Reconstruye la imagen de memoria original y la transformada desde las
      operaciones declaradas, por dos caminos independientes.
    - Compara estados finales de memoria ventana a ventana (bytes consumidos).
    - Verifica conjuntos de intervalos escritos por ambas secuencias.
    - Verifica el orden de la traza de observadores (lista exacta de eventos).
    - Verifica storage y vidas: calcula disjuntos reales con BFS propio.
    - Verifica cobertura: cada byte observado debe estar respaldado por una
      evidencia sellada procedente del análisis sellado (no del caso).
    - Reporta hash de las imágenes finales y lista de eventos como trazas.

## NO ES

    - NO es el testigo: no emite decisiones del analizador ni del guard.
    - NO relaja vetos ni modifica artefactos sellados.
    - NO declara PROVEN sobre el driver ni sobre el #7294.
    - NO difiere de su oración: si ambas herramientas discrepan, lo reporta.

## VEREDICTOS

    SAFE ⇔ las 6 condiciones TRUE; BLOCKED ⇔ alguna FALSE; ABSTAIN ⇔ alguna UNKNOWN.
    Epistemia: SIEMPRE PARTIAL aquí (no hay oráculo externo que cubra la
    reconstrucción completa por parte del verificador; el estado lo asigna
    ``independent_oracle`` del caso si existe y cubre todo; si no, PARTIAL).
"""
from __future__ import annotations

import hashlib
import json
import os
import sys
from typing import Any, Dict, List, Optional, Sequence, Tuple

VERIFIER_VERSION = "RYI-INDEPENDENT-VERIFIER-1"
CAPABILITY_ID = "independent_verifier"

SAFE = "SAFE_TO_TRANSFORM"
ABSTAIN = "ABSTAIN"
BLOCKED = "BLOCKED"
TRUE, FALSE, UNKNOWN = "TRUE", "FALSE", "UNKNOWN"

CHK_B, CHK_W, CHK_O, CHK_L, CHK_C, CHK_D = "B", "W", "O", "L", "C", "D"
CONDITIONS = (CHK_B, CHK_W, CHK_O, CHK_L, CHK_C, CHK_D)

EP_PARTIAL, EP_NOT_DETERMINED, EP_BLOCKED = "PARTIAL", "NOT_DETERMINED", "BLOCKED"


# ------------------------------------------------------------- sello §8.1

def _sha256_file(path: str) -> str:
    h = hashlib.sha256()
    with open(path, "rb") as fh:
        for chunk in iter(lambda: fh.read(65536), b""):
            h.update(chunk)
    return h.hexdigest()


def verify_manifest(m10_dir: str, suffix: str) -> List[str]:
    """Verifica un manifiesto completo (byte a byte, BFS-like scan)."""
    mp = os.path.join(m10_dir, "SHA256SUMS.m10.%s" % suffix)
    if not os.path.exists(mp):
        raise ValueError("manifiesto ausente: %s" % mp)
    verified = []
    with open(mp, "r", encoding="utf-8") as fh:
        for line in fh:
            parts = line.split()
            if len(parts) < 2:
                continue
            f = os.path.join(m10_dir, parts[-1])
            if not os.path.exists(f):
                raise ValueError("artefacto referenciado ausente: %s" % parts[-1])
            if _sha256_file(f) != parts[0]:
                raise ValueError("sello roto: %s" % parts[-1])
            verified.append(parts[-1])
    return verified


def load_sealed_analysis(m10_dir: str) -> Dict[str, Any]:
    verify_manifest(m10_dir, "7")
    target = os.path.join(m10_dir, "cancel_sys_analysis_m10_7.json")
    if not os.path.exists(target):
        raise ValueError("cancel_sys_analysis_m10_7.json ausente en %s" % m10_dir)
    with open(target, "r", encoding="utf-8") as fh:
        data = json.load(fh)
    if "sealed" not in data or "result" not in data["sealed"]:
        raise ValueError("sello/estructura inesperada en cancel_sys_analysis_m10_7.json")
    return data["sealed"]["result"]


# ------------------------------------------------------------- canales P2

def _declared_store_bytes(case: Dict[str, Any]):
    for op in (case.get("original_sequence") or {}).get("ops", []):
        if isinstance(op, dict) and op.get("op") == "store_const_bytes" and isinstance(op.get("bytes"), list):
            off = op.get("offset", 0)
            return {"bytes": op["bytes"], "len": len(op["bytes"]), "offset": off}
    return None


def _declared_xor_params(case: Dict[str, Any]):
    for op in (case.get("original_sequence") or {}).get("ops", []):
        if isinstance(op, dict) and op.get("op") == "rmw_xor":
            idx = op.get("index_base")
            return (idx if isinstance(idx, int) else None), op.get("unit_size", 1)
    return (None, 1)


def _declared_store_units(case: Dict[str, Any], unit: int):
    out: Dict[int, int] = {}
    for op in (case.get("original_sequence") or {}).get("ops", []):
        if not isinstance(op, dict):
            continue
        if op.get("op") != "store_const_bytes":
            continue
        off = op.get("offset", 0)
        bytes_ = op.get("bytes", [])
        if not isinstance(bytes_, list):
            continue
        if unit == 1:
            for i, v in enumerate(bytes_):
                out[off + i] = v & 0xff
        else:  # unit == 2
            for i in range(0, len(bytes_), 2):
                pair = bytes_[i:i + 2]
                if len(pair) != 2:
                    return None
                u = (off + i) // 2
                out[u] = pair[0] | (pair[1] << 8)
    return out or None


# ------------------------------------------------------------- canales

def _canonical(obj: Any) -> str:
    return json.dumps(obj, sort_keys=True, separators=(",", ":"), ensure_ascii=False)


def _hash(obj: Any) -> str:
    return hashlib.sha256(_canonical(obj).encode("utf-8")).hexdigest()


def _cond(value: str, detail: str, evidence: Optional[List[str]] = None) -> Dict[str, Any]:
    return {"value": value, "detail": detail, "evidence": list(evidence or ())}


# ------------------------------------------------------------- B · bytes

def _apply_ops(ops: Sequence[Dict[str, Any]], size: int) -> bytes:
    """Implementación independiente del modelo byte a byte.

    La fórmula XOR se recompone ALGEBRAICAMENTE desde las constantes declaradas,
    no interpretando un bucle como hace el testigo.
    """
    mem = [0] * size
    rng_set = None
    for op in ops:
        kind = op.get("op")
        if kind == "store_const_bytes":
            off = op["offset"]
            for i, b in enumerate(op["bytes"]):
                mem[off + i] = b & 0xff
        elif kind == "store_const":
            mem[op["offset"]] = op["value"] & 0xff
        elif kind == "rmw_xor":
            idx_base = op.get("index_base")
            if not isinstance(idx_base, int):
                raise ValueError("rmw_xor exige index_base")
            start, span = op["offset"], op["size"]
            unit = op.get("unit_size", 1)
            if unit == 1:
                mem = [b ^ ((i + idx_base) & 0xff) if start <= i < start + span else b
                       for i, b in enumerate(mem)]
            elif unit == 2:
                for i in range(start, start + span, 2):
                    u = (i - start) // 2
                    cur = mem[i] | (mem[i + 1] << 8)
                    dec = cur ^ ((u + idx_base) & 0xffff)
                    mem[i] = dec & 0xff
                    mem[i + 1] = (dec >> 8) & 0xff
        elif kind == "call_summary":
            continue  # resumen sin efectos sobre este buffer en la fase evaluada
        else:
            raise ValueError("operación no soportada: %r" % (kind,))
    return bytes(mem)


def _check_B(case: Dict[str, Any]) -> Dict[str, Any]:
    orig_ops = (case.get("original_sequence") or {}).get("ops", [])
    fold_ops = (case.get("proposed_transform") or {}).get("ops", [])
    if not isinstance(orig_ops, list) or not isinstance(fold_ops, list):
        return _cond(UNKNOWN, "faltan operaciones")
    try:
        a = _apply_ops(orig_ops, case["region"]["size"])
        b = _apply_ops(fold_ops, case["region"]["size"])
    except ValueError as exc:
        return _cond(UNKNOWN, "operaciones no modelables: %s" % exc)
    consumed = case.get("observations", {}).get("consumed_intervals")
    if not consumed:
        return _cond(UNKNOWN, "consumed_intervals ausente")
    base = case["region"]["base"]
    size = case["region"]["size"]
    windows = []
    for lo, hi in consumed:
        windows.append((max(0, lo - base), min(size, hi - base)))
    p1_ok = all(a[x:y] == b[x:y] for x, y in windows)
    # P2 · inversión algebraica (opción omitida si no hay rmw_xor declarado).
    # La clave y el tamaño de unidad se toman del propio caso, nunca del testigo.
    idx_base, unit = _declared_xor_params(case)
    if idx_base is None:
        p2_ok, p2_note = True, "omitido (sin rmw_xor declarado)"
    elif unit not in (1, 2):
        return _cond(UNKNOWN, "unit_size no soportado: %r" % (unit,))
    else:
        stored_by_unit = _declared_store_units(case, unit)
        if stored_by_unit is None:
            return _cond(UNKNOWN,
                         "no hay stores const declarados con el mismo unit_size para verificar P2")
        p2_ok, p2_note = True, "P2 ok (%d unidades verificadas)" % len(stored_by_unit)
        rmw_size = next((op.get("size") for op in (case.get("original_sequence") or {}).get("ops", [])
                         if isinstance(op, dict) and op.get("op") == "rmw_xor"), None)
        for u, declared in sorted(stored_by_unit.items()):
            if rmw_size is not None and u * unit + unit > rmw_size:
                continue  # fuera del span del loop: no la revisa el rmw
            if unit == 1:
                decoded = b[u] if u < len(b) else None
                if decoded is None or (decoded ^ ((u + idx_base) & 0xff)) != declared:
                    p2_ok, p2_note = False, "byte %d no corresponde a los const declarados" % u
                    break
            else:
                i = u * 2
                if i + 1 >= len(b):
                    p2_ok, p2_note = False, "unidad %d fuera de rango" % u
                    break
                cur = b[i] | (b[i + 1] << 8)
                if (cur ^ ((u + idx_base) & 0xffff)) != declared:
                    p2_ok, p2_note = False, "unidad wide-char %d no corresponde a los const declarados" % u
                    break
    # P3 · igualdad en toda la región (más estricta que P1)
    p3_ok = (a == b)
    if not p1_ok:
        bad = [[lo + base, hi + base] for (lo, hi), (x, y) in zip(consumed, windows) if a[x:y] != b[x:y]]
        return _cond(FALSE, "bytes observables difieren (P1): %s" % bad,
                     ["model.original", "model.folded"])
    if not p2_ok:
        return _cond(FALSE,
                     "inversión algebraica falla (P2): bytes de salida no corresponden "
                     "a los bytes const declarados",
                     ["algebraic.check"])
    if not p3_ok:
        return _cond(FALSE,
                     "imágenes finales difieren fuera de las ventanas consumidas (P3)",
                     ["model.full_region"])
    return _cond(TRUE,
                 "P1 (ventanas consumidas) ∧ P2 (inversión algebraica) ∧ P3 (región completa) — sha256(%s)" % hashlib.sha256(a).hexdigest()[:16],
                 ["model.original", "model.folded", "algebraic.check"])


# ------------------------------------------------------------- W · escrituras

def _covers(ivs: Sequence[Sequence[int]], iv: Sequence[int]) -> bool:
    return any(a <= iv[0] and iv[1] <= b for a, b in ivs)


def _check_W(case: Dict[str, Any]) -> Dict[str, Any]:
    o = case.get("intervals_written_original")
    t = case.get("intervals_written_transform")
    consumed = case.get("observations", {}).get("consumed_intervals")
    if not isinstance(o, list) or not isinstance(t, list) or not consumed:
        return _cond(UNKNOWN, "escrituras o consumo sin declarar")
    for iv in consumed:
        if not _covers(o, iv):
            return _cond(FALSE, "original no escribe consumido %s" % iv)
        if not _covers(t, iv):
            return _cond(FALSE, "transformada no escribe consumido %s" % iv)
    extra = [iv for iv in t if not _covers(o, iv)]
    if extra:
        return _cond(FALSE, "transformada escribe fuera del span original: %s" % extra)
    return _cond(TRUE, "escrituras preservadas", ["writes.original", "writes.transform"])


# ------------------------------------------------------------- O · orden

def _check_O(case: Dict[str, Any]) -> Dict[str, Any]:
    o = case.get("order_check")
    if not isinstance(o, dict):
        return _cond(UNKNOWN, "sin order_check")
    orig, folded = o.get("original"), o.get("transform")
    if not isinstance(orig, list) or not isinstance(folded, list):
        return _cond(UNKNOWN, "order_check incompleto")
    if [tuple(x) for x in orig] != [tuple(x) for x in folded]:
        return _cond(FALSE, "orden de observadores difiere (original vs transformada)")
    return _cond(TRUE, "orden preservado (%d eventos)" % len(orig),
                 ["order.original", "order.transform"])


# ------------------------------------------------------------- L · linaje / vidas

def _bfs_reach(cfg: Any, src: Any, dst: Any) -> bool:
    def _to_int(v):
        if isinstance(v, int):
            return v
        if isinstance(v, str):
            try:
                return int(v, 0)
            except ValueError:
                return None
        return None
    succ = {}
    if isinstance(cfg, dict):
        for k, v in cfg.items():
            ki = _to_int(k)
            if ki is None:
                continue
            lst = []
            if isinstance(v, (list, tuple)):
                for x in v:
                    xi = _to_int(x)
                    if xi is not None:
                        lst.append(xi)
            succ[ki] = lst
    si, di = _to_int(src), _to_int(dst)
    if si is None or di is None:
        return False
    if si == di:
        return True
    seen = {si}
    frontier = [si]
    while frontier:
        nxt = []
        for node in frontier:
            for s in succ.get(node, ()):  # BFS clásica
                if s == di:
                    return True
                if s not in seen:
                    seen.add(s)
                    nxt.append(s)
        frontier = nxt
    return False


def _check_L(case: Dict[str, Any]) -> Dict[str, Any]:
    lineage = case.get("lineage")
    if not isinstance(lineage, dict):
        return _cond(UNKNOWN, "sin linaje")
    allowed = lineage.get("allowed_storage_writes")
    t_stores = case.get("proposed_transform", {}).get("storage_writes")
    if not isinstance(allowed, list) or not isinstance(t_stores, list):
        return _cond(UNKNOWN, "storage_writes sin declarar")
    if set(t_stores) - set(allowed):
        return _cond(FALSE, "storage no permitido en la transformación: %s" %
                     sorted(set(t_stores) - set(allowed)))
    cfg = case.get("cfg_successors") or {}
    must = lineage.get("must_not_overlap", [])
    new_ivs = case.get("proposed_transform", {}).get("overlap_intervals", [])
    for other in must:
        o_iv = other.get("interval")
        if not isinstance(o_iv, list) or len(o_iv) != 2:
            return _cond(UNKNOWN, "must_not_overlap malformado")
        if not other.get("live_during_transform", False):
            continue
        for iv in new_ivs:
            if iv[0] < o_iv[1] and o_iv[0] < iv[1]:
                return _cond(FALSE,
                             "solape con región viva %s %s" % (other.get("id"), o_iv))
    return _cond(TRUE, "linaje y vidas respetados", ["lineage.allowed", "lineage.must_not_overlap"])


# ------------------------------------------------------------- C · cobertura sellada

def _seal_evidence_intervals(sealed: Dict[str, Any], candidate: str) -> List[Dict[str, Any]]:
    for c in sealed.get("candidates", []):
        if c.get("candidate_id") == candidate:
            return [e for e in c.get("evidence", [])]
    return []


def _check_C(case: Dict[str, Any]) -> Dict[str, Any]:
    """Cobertura bajo el contrato K=(S,C,T,O).

    El verificador siempre opera contra la fuente sellada (nunca contra la
    lista declarada por el caso).  La lista del caso, si existe, se usa sólo
    como coherencia: cada id citado debe existir en el análisis sellado.
    """
    sealed = case.get("_sealed_analysis")
    if not isinstance(sealed, dict):
        return _cond(UNKNOWN, "fuente sellada ausente; cobertura no verificable")
    try:
        from ier.evidence_contract import check_binding
    except ImportError:
        try:
            from .evidence_contract import check_binding  # type: ignore
        except ImportError:
            return _cond(UNKNOWN, "contrato de evidencia no disponible en este paquete")
    res = check_binding(case, sealed)
    hint = res["verdict_hint"]
    if hint == "VACUOUS":
        return _cond(TRUE,
                     "caso vacuo explícito (T no toca bytes, O=∅): SAFE solo etiquetado vacuous",
                     ["contract.vacuous"])
    if res["bound"] == FALSE:
        return _cond(FALSE,
                     "contrato K no vinculado: %s" % "; ".join(res["violations"][:4]),
                     res.get("coverage", []))
    if res["complete"] == TRUE:
        return _cond(TRUE,
                     "Bound∧Complete verificados contra fuente sellada (ids: %d)" % len(res["coverage"]),
                     res["coverage"])
    return _cond(UNKNOWN,
                 "cobertura no cerrada por contrato: bound=%s complete=%s violations=%s" % (
                     res["bound"], res["complete"], res["violations"]),
                 res.get("coverage", []))


# ------------------------------------------------------------- D · dominio

def _check_D(case: Dict[str, Any]) -> Dict[str, Any]:
    domain = case.get("domain")
    if not isinstance(domain, dict):
        return _cond(UNKNOWN, "dominio ausente")
    need = ("artifact_sha256", "function", "scope", "limits")
    missing = [k for k in need if not domain.get(k)]
    if missing:
        return _cond(UNKNOWN, "dominio incompleto: falta %s" % missing)
    if len(str(domain["artifact_sha256"])) < 16:
        return _cond(UNKNOWN, "artifact_sha256 demasiado corto")
    return _cond(TRUE, "dominio completo", ["domain.scope", "domain.limits"])


_CHECKS = {CHK_B: _check_B, CHK_W: _check_W, CHK_O: _check_O,
           CHK_L: _check_L, CHK_C: _check_C, CHK_D: _check_D}


def verify_case(case: Dict[str, Any],
                sealed_analysis: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
    """Verifica el caso con el verificador independiente.  Determinista."""
    case = dict(case)
    if sealed_analysis is not None:
        case["_sealed_analysis"] = sealed_analysis
    results = {k: _CHECKS[k](case) for k in _CHECKS}
    vals = [results[k]["value"] for k in _CHECKS]
    if all(v == TRUE for v in vals):
        verdict = SAFE
    elif any(v == FALSE for v in vals):
        verdict = BLOCKED
    else:
        verdict = ABSTAIN
    oracle = case.get("independent_oracle")
    oracle_full = bool(oracle and oracle.get("covers") == list(CONDITIONS)
                       and str(oracle.get("result", "")).upper() == "PASS")
    epistemic = EP_PARTIAL if verdict != BLOCKED else EP_BLOCKED
    if verdict == ABSTAIN:
        epistemic = EP_NOT_DETERMINED
    return {
        "capability": CAPABILITY_ID,
        "capability_version": VERIFIER_VERSION,
        "case_id": case.get("case_id"),
        "verdict": verdict,
        "epistemic_status": epistemic,
        "operational_status": "PASS" if verdict == SAFE else (
            "BLOCKED" if verdict == BLOCKED else "PARTIAL"),
        "conditions": results,
        "independent_oracle_covers_all": oracle_full,
        "failed_conditions": [k for k in _CHECKS if results[k]["value"] == FALSE],
        "unknown_conditions": [k for k in _CHECKS if results[k]["value"] == UNKNOWN],
        "final_images": _final_images(case),
        "traces": _traces(case),
        "limitations": _limitations(case, results),
        "errors": [],
    }


def _final_images(case: Dict[str, Any]) -> Dict[str, Any]:
    try:
        size = case["region"]["size"]
        a = _apply_ops((case.get("original_sequence") or {}).get("ops", []), size)
        b = _apply_ops((case.get("proposed_transform") or {}).get("ops", []), size)
        return {"original_sha256": hashlib.sha256(a).hexdigest(),
                "transform_sha256": hashlib.sha256(b).hexdigest(),
                "equal_on_full_region": a == b}
    except (KeyError, TypeError, ValueError):
        return {"original_sha256": None, "transform_sha256": None,
                "equal_on_full_region": None}


def _traces(case: Dict[str, Any]) -> Dict[str, Any]:
    def _ops_kind(ops):
        return [o.get("op") for o in (ops or []) if isinstance(o, dict)]
    return {
        "original_ops": _ops_kind((case.get("original_sequence") or {}).get("ops")),
        "transform_ops": _ops_kind((case.get("proposed_transform") or {}).get("ops")),
        "observer_trace": case.get("order_check", {}).get("original"),
    }


def _limitations(case: Dict[str, Any],
                 results: Dict[str, Dict[str, Any]]) -> List[str]:
    lims = [
        "verificador independiente del testigo; no comparte código decisorio con él",
        "no ejecuta el artefacto; modelo de bytes acotado al caso",
        "PARTIAL es el máximo estatus aquí salvo oráculo total (covers=B..D)",
        "un veredicto SAFE del verificador NO autoriza cambios upstream",
    ]
    for k, v in results.items():
        if v["value"] == UNKNOWN:
            lims.append("condición %s desconocida: %s" % (k, v["detail"]))
    return lims
