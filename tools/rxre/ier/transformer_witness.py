#!/usr/bin/env python3
# SPDX-License-Identifier: GPL-2.0
# WORK_CLASS=READ_ONLY · WRITE_EXECUTION=SCRATCH_ONLY (.rxre/state/transformer_witness/)
"""RXRE · IER · TRANSFORMER_WITNESS — testigo independiente de seguridad de transformación.

## QUÉ ES

Un testigo que evalúa una **transformación propuesta concreta** sobre una región
candidata y produce un veredicto acotado, sin utilizar el guard de angr ni su
decisión como oráculo.  Verifica, como mínimo (M10.8 §3):

    B  Equivalencia de bytes observables
    W  Preservación de escrituras
    O  Preservación del orden de efectos
    L  Linaje y vida de regiones suficientes
    C  Cobertura de las observaciones relevantes
    D  Dominio de evidencia explícito

    SAFE_TO_TRANSFORM  ⇔  B ∧ W ∧ O ∧ L ∧ C ∧ D   (TODAS TRUE; cualquier UNKNOWN ⇒ ABSTAIN)
    BLOCKED            ⇔  alguna condición es FALSE demostrable (transformación rechazada)
    ABSTAIN            ⇔  alguna condición es desconocida/insuficiente

## QUÉ NO ES

    - NO es el guard de angr ni lo sustituye.  NO decide si angr debe aplicar la
      transformación: decide si la transformación CONCRETA preserva los efectos
      dentro del dominio de evidencia declarado.
    - NO valida el comportamiento del driver ni la ejecución del binario.
    - NO relaja ningún veto del analizador.  El veto ABSTAIN de `region_analyzer`
      sigue siendo decisión independiente del veredicto del testigo.
    - NO produce PROVEN: el estatus epistémico máximo es PARTIAL (sin oráculo
      externo independiente adicional).  Con oráculo independiente declarado
      y verificado puede elevarse solo aquello que el oráculo cubre.

## MODELO DE EJECUCIÓN SIMBÓLICA

El testigo ejecuta un **modelo** de la secuencia byte a byte sobre un buffer
simulado (bytes inicializados a 0, como `Insert(0<160>, …)`):

    store_const_bytes   → escribe bytes en offsets
    store_const         → escribe un valor le
    rmw_xor             → in-place XOR byte (o unidad de 16 bits) reversible
    call_summary        → efecto declarado del callee sellado (read/write/none)

Comparaciones: los cinco contratos del caso (secuencia original vs transformada)
se ejecutan sobre el modelo y se contrastan.  El modelo es intencionadamente
pequeño y auditable; su fidelidad al AIL se declara, no se presupone.

## CONSUMO DE ARTEFACTOS SELLADOS (M10.8.1)

`load_sealed_json()` verifica el hash del artefacto contra su manifiesto
SHA256SUMS antes de consumirlo.  Ningún artefacto no verificado entra al testigo.

## ESTADOS

    Operacional: PASS | PARTIAL | BLOCKED | ERROR
    Epistémico:  PROVEN | PARTIAL | NOT_DETERMINED | BLOCKED
    (PROVEN exige oráculo independiente explícito; este módulo nunca lo inventa.)
"""
from __future__ import annotations

import hashlib
import json
import os
import sys
from typing import Any, Dict, List, Optional, Sequence, Tuple

WITNESS_VERSION = "RYI-TRANSFORMER-WITNESS-1"
CAPABILITY_ID = "transformer_witness"

SAFE = "SAFE_TO_TRANSFORM"
ABSTAIN = "ABSTAIN"
BLOCKED = "BLOCKED"

CHK_B, CHK_W, CHK_O, CHK_L, CHK_C, CHK_D = "B", "W", "O", "L", "C", "D"
CONDITIONS = (CHK_B, CHK_W, CHK_O, CHK_L, CHK_C, CHK_D)

TRUE, FALSE, UNKNOWN = "TRUE", "FALSE", "UNKNOWN"

OP_PASS, OP_PARTIAL, OP_BLOCKED, OP_ERROR = "PASS", "PARTIAL", "BLOCKED", "ERROR"
EP_PROVEN, EP_PARTIAL, EP_NOT_DETERMINED, EP_BLOCKED = (
    "PROVEN", "PARTIAL", "NOT_DETERMINED", "BLOCKED")


# ============================================================ material sellado §8.1

def _sha256_file(path: str) -> str:
    h = hashlib.sha256()
    with open(path, "rb") as fh:
        for chunk in iter(lambda: fh.read(65536), b""):
            h.update(chunk)
    return h.hexdigest()


def _canonical(obj: Any) -> str:
    return json.dumps(obj, sort_keys=True, separators=(",", ":"), ensure_ascii=False)


def load_sealed_json(path: str, manifest_path: Optional[str] = None) -> Dict[str, Any]:
    """Carga un JSON sellado verificando su hash contra su manifiesto.

    Si ``manifest_path`` es None, devuelve el JSON con su hash calculado sin
    verificación (uso de diagnóstico).  Si se proporciona, exige que el nombre
    del archivo aparezca en el manifiesto con hash coincide exacto.
    """
    actual = _sha256_file(path)
    if manifest_path:
        expected = None
        with open(manifest_path, "r", encoding="utf-8") as fh:
            for line in fh:
                line = line.rstrip()
                if not line:
                    continue
                parts = line.split()
                if len(parts) >= 2 and os.path.basename(parts[-1]) == os.path.basename(path):
                    expected = parts[0]
                    break
        if expected is None:
            raise ValueError("artefacto no presente en manifiesto: %s" % os.path.basename(path))
        if expected != actual:
            raise ValueError(
                "sello inválido para %s: manifiesto=%s actual=%s" % (
                    os.path.basename(path), expected, actual))
        return json.load(open(path, "r", encoding="utf-8"))
    return json.load(open(path, "r", encoding="utf-8"))


def load_m10_evidence(m10_dir: str) -> Dict[str, Any]:
    """Consume artefactos sellados M10.5–M10.7 (read-only).

    Verifica SHA256SUMS.m10.5/.m10.6/.m10.7 antes de leer.  Devuelve
    referencias (id, source, interval, confidence, seal) sin mutar nada.
    """
    bundle: Dict[str, Any] = {"manifest_verified": []}
    for suffix in ("7", "6", "5"):
        manifest = os.path.join(m10_dir, "SHA256SUMS.m10.%s" % suffix)
        if os.path.exists(manifest):
            # verificación completa del manifiesto
            with open(manifest, "r", encoding="utf-8") as fh:
                for line in fh:
                    parts = line.split()
                    if len(parts) >= 2:
                        f = parts[-1]
                        if os.path.exists(os.path.join(m10_dir, f)):
                            if _sha256_file(os.path.join(m10_dir, f)) != parts[0]:
                                raise ValueError("sello roto: %s" % f)
            bundle["manifest_verified"].append("SHA256SUMS.m10.%s" % suffix)
    bundle["cancel_sys_analysis"] = load_sealed_json(
        os.path.join(m10_dir, "cancel_sys_analysis_m10_7.json"),
        os.path.join(m10_dir, "SHA256SUMS.m10.7"))
    bundle["callee_summary"] = load_sealed_json(
        os.path.join(m10_dir, "callee_summary_sub_1400035f4.json"),
        os.path.join(m10_dir, "SHA256SUMS.m10.7"))
    bundle["provenance"] = load_sealed_json(
        os.path.join(m10_dir, "provenance_vvar_253_271.json"),
        os.path.join(m10_dir, "SHA256SUMS.m10.7"))
    bundle["analysis_m10_6"] = load_sealed_json(
        os.path.join(m10_dir, "cancel_sys_analysis_m10_6.json"),
        os.path.join(m10_dir, "SHA256SUMS.m10.6"))
    bundle["analysis_m10_5"] = load_sealed_json(
        os.path.join(m10_dir, "cancel_sys_analysis.json"),
        os.path.join(m10_dir, "SHA256SUMS.m10.5"))
    return bundle


# ============================================================ modelo de ejecución

def _region_bytes(region_size: int):
    return bytearray(b"\x00" * region_size)


def _carry_ops(mem: bytearray, region_base: int, size: int,
               ops: Sequence[Dict[str, Any]]) -> None:
    for op in ops:
        kind = op.get("op")
        if kind == "store_const_bytes":
            offset = op["offset"]
            data = bytes(op["bytes"])
            mem[offset:offset + len(data)] = data
        elif kind == "store_const":
            mem[op["offset"]] = op["value"] & 0xff
        elif kind == "rmw_xor":
            unit = op.get("unit_size", 1)
            index_base = op.get("index_base")
            if not isinstance(index_base, int):
                raise ValueError("rmw_xor sin index_base demostrable")
            start, span = op["offset"], op["size"]
            if unit == 1:
                for i in range(start, start + span):
                    mem[i] ^= (i + index_base) & 0xff
            elif unit == 2:
                for i in range(start, start + span, 2):
                    u = (i - start) // 2
                    cur = mem[i] | (mem[i + 1] << 8)
                    dec = cur ^ ((u + index_base) & 0xffff)
                    mem[i] = dec & 0xff
                    mem[i + 1] = (dec >> 8) & 0xff
            else:
                raise ValueError("unit_size no soportado: %r" % (unit,))
        elif kind == "call_summary":
            summary = op.get("summary") or {}
            if summary.get("writes_through_args"):
                # escritura mediante puntero: el callee puede sobre escribir bytes
                # del candidato; el testigo NO puede ignorarla → falla B a menos
                # que el registro lo contemple explícitamente
                raise ValueError("escritura indirecta en callee no modelada por el caso")
            # reads/text_consuming/none: el candidato no cambia en la fase del fold
        else:
            raise ValueError("operación desconocida: %r" % (kind,))


def _execute(original_ops: Sequence[Dict[str, Any]],
             region_base: int, region_size: int) -> bytes:
    mem = _region_bytes(region_size)
    _carry_ops(mem, region_base, region_size, original_ops)
    return bytes(mem)


# ============================================================ las seis condiciones

def _cond(value: str, detail: str, evidence: Optional[List[str]] = None) -> Dict[str, Any]:
    return {"value": value, "detail": detail, "evidence": list(evidence or ())}


def _bytes_consumed(case: Dict[str, Any]) -> List[List[int]]:
    ivs = case["observations"].get("consumed_intervals")
    if not isinstance(ivs, list):
        return []
    out = []
    for iv in ivs:
        try:
            lo, hi = int(iv[0]), int(iv[1])
        except (TypeError, ValueError, IndexError):
            return []
        if lo < hi:
            out.append([lo, hi])
    return out


def _check_B(case: Dict[str, Any]) -> Dict[str, Any]:
    if "original_sequence" not in case or "proposed_transform" not in case:
        return _cond(UNKNOWN, "falta original_sequence o proposed_transform")
    region = case["region"]
    size = int(region["size"])
    base = int(region["base"])
    original_ops = case["original_sequence"]["ops"]
    try:
        mem_orig = _execute(original_ops, base, size)
    except ValueError as exc:
        return _cond(UNKNOWN, "secuencia original no modelable: %s" % exc)
    # la transformación propuesta escribe bytes concretos; verificarla como paso
    t_ops = case["proposed_transform"].get("ops", [])
    try:
        mem_folded = _execute(t_ops, base, size)
    except ValueError as exc:
        return _cond(UNKNOWN, "transformación propuesta no modelable: %s" % exc)
    consumed = _bytes_consumed(case)
    if not consumed:
        return _cond(UNKNOWN, "sin intervalos consumidos declarados; no se puede verificar equivalencia observable")
    mismatches = []
    for iv in consumed:
        lo, hi = max(0, iv[0] - base), min(size, iv[1] - base)
        if mem_orig[lo:hi] != mem_folded[lo:hi]:
            mismatches.append([iv[0], iv[1]])
    if mismatches:
        return _cond(FALSE, "bytes observables difieren en %s" % mismatches,
                     ["evidence.mismatch"])
    return _cond(TRUE, "bytes observables idénticos en %d intervalo(s)" % len(consumed),
                 ["model.original", "model.folded"])


def _check_W(case: Dict[str, Any]) -> Dict[str, Any]:
    orig_w = case.get("intervals_written_original")
    t_w = case.get("intervals_written_transform")
    if not isinstance(orig_w, list) or not isinstance(t_w, list):
        return _cond(UNKNOWN, "falta intervals_written_original o intervals_written_transform")
    consumed = [iv for iv in _bytes_consumed(case)]
    if not consumed:
        return _cond(UNKNOWN, "sin intervalos consumidos")
    # a) cada byte consumido debe estar escrito por ambas secuencias
    def _covers(intervals, iv):
        return any(a <= iv[0] and iv[1] <= b for a, b in
                   ((i[0], i[1]) for i in intervals))
    for iv in consumed:
        if not _covers(orig_w, iv):
            return _cond(FALSE, "la secuencia original no escribe bytes consumidos %s" % iv)
        if not _covers(t_w, iv):
            return _cond(FALSE, "la transformación no escribe bytes consumidos %s" % iv)
    # b) la transformación no puede escribir fuera del span declarado
    extra = [i for i in t_w if not any(a <= i[0] and i[1] <= b for a, b in orig_w)]
    if extra:
        return _cond(FALSE,
                     "la transformación escribe fuera del span original: %s" % extra)
    return _cond(TRUE, "escrituras preservadas: consumidos⊆escritos y sin escritura extra",
                 ["writes.orig", "writes.transform"])


def _check_O(case: Dict[str, Any]) -> Dict[str, Any]:
    order = case.get("order_check")
    if not isinstance(order, dict):
        return _cond(UNKNOWN, "sin order_check")
    orig = order.get("original")
    folded = order.get("transform")
    if not isinstance(orig, list) or not isinstance(folded, list):
        return _cond(UNKNOWN, "order_check incompleto")
    # los observadores deben aparecer en el MISMO orden con las mismas claves
    def _keys(seq):
        return [tuple(item) for item in seq]
    if _keys(orig) != _keys(folded):
        return _cond(FALSE, "el orden de observadores difiere entre original y transformada",
                     ["order.original", "order.transform"])
    return _cond(TRUE, "orden de observadores preservado (%d eventos)" % len(orig),
                 ["order.original", "order.transform"])


def _check_L(case: Dict[str, Any]) -> Dict[str, Any]:
    lineage = case.get("lineage")
    if not isinstance(lineage, dict):
        return _cond(UNKNOWN, "sin linaje en el caso")
    allowed = lineage.get("allowed_storage_writes")
    if not isinstance(allowed, list):
        return _cond(UNKNOWN, "lineage.allowed_storage_writes ausente")
    transformed_stores = case.get("proposed_transform", {}).get("storage_writes", [])
    if not isinstance(transformed_stores, list):
        return _cond(UNKNOWN, "proposed_transform.storage_writes no declarado")
    ok = set(transformed_stores) <= set(allowed)
    if not ok:
        return _cond(FALSE, "transformación escribe storages no permitidos: %s ⊄ %s" % (
            sorted(set(transformed_stores)), sorted(set(allowed))))
    must_absent = lineage.get("must_not_overlap", [])
    new_ivs = case.get("proposed_transform", {}).get("overlap_intervals", [])
    for other in must_absent:
        o_iv = other.get("interval")
        if not isinstance(o_iv, list) or len(o_iv) != 2:
            return _cond(UNKNOWN, "must_not_overlap malformado: %r" % (other,))
        # solo las regiones VIVAS durante la transformación restringen el solape
        if not other.get("live_during_transform", False):
            continue
        if other.get("id") is None:
            return _cond(UNKNOWN, "must_not_overlap sin id")
        for iv in new_ivs:
            if iv[0] < o_iv[1] and o_iv[0] < iv[1]:
                return _cond(FALSE,
                             "transformación extiende writes sobre región viva %s (%s) "
                             "enmascarando su vida" % (other.get("id"), o_iv))
    return _cond(TRUE, "linaje respetado: writes dentro de storages permitidos, sin solape con vidas ajenas",
                 ["lineage.allowed", "lineage.must_not_overlap"])


def _check_C(case: Dict[str, Any]) -> Dict[str, Any]:
    """Cobertura bajo el contrato K=(S,C,T,O).

    Dos modos:
      - producción: el caso lleva ``sealed_analysis`` (fuente verificada) → el
        contrato completo (Bound ∧ Complete) es exigido; violación ⇒ BLOCKED,
        cobertura incompleta ⇒ ABSTAIN.
      - diagnóstico: sin fuente sellada; la cobertura se limita a la evidencia
        declarada por el caso y queda etiquetada ``binding: NOT_EVALUATED``;
        estos casos nunca son aptos para afirmaciones de producción.
    """
    try:
        from ier.evidence_contract import check_binding
    except ImportError:
        try:
            from .evidence_contract import check_binding  # type: ignore
        except ImportError:
            check_binding = None

    obs = case.get("observations", {})
    sealed = case.get("sealed_analysis")
    consumed_raw = obs.get("consumed_intervals")

    if isinstance(sealed, dict):
        if check_binding is None:
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
                         "Bound∧Complete verificados (ids: %s)" % res["coverage"],
                         res["coverage"])
        return _cond(UNKNOWN,
                     "cobertura no cerrada por contrato: bound=%s complete=%s violations=%s" % (
                         res["bound"], res["complete"], res["violations"]),
                     res.get("coverage", []))

    # ---- modo diagnóstico (sin fuente sellada)
    intervals = obs.get("evidence_intervals")
    consumed = _bytes_consumed(case)
    if not isinstance(intervals, list):
        return _cond(UNKNOWN,
                     "sin fuente sellada ni evidence_intervals; binding NOT_EVALUATED")
    if intervals is not None and not consumed:
        # T no toca bytes declarados u O=∅ sin T: posible vacuo no verificable
        return _cond(UNKNOWN,
                     "caso vacuo no verificable sin fuente sellada; binding NOT_EVALUATED")
    if "unobserved_bytes" not in obs:
        return _cond(UNKNOWN, "sin declaración de unobserved_bytes; cobertura no demostrable")
    unobserved = obs.get("unobserved_bytes")
    if unobserved is None or not isinstance(unobserved, list):
        return _cond(UNKNOWN, "unobserved_bytes malformado")
    for iv in consumed:
        for u in unobserved:
            if u[0] < iv[1] and iv[0] < u[1]:
                return _cond(UNKNOWN,
                             "byte no observado %s solapa consumido %s" % (u, iv))
    for iv in consumed:
        found = False
        for ev in intervals:
            if not isinstance(ev, dict):
                return _cond(UNKNOWN, "evidence_intervals malformado")
            eiv = ev.get("interval")
            if isinstance(eiv, list) and eiv[0] <= iv[0] and iv[1] <= eiv[1]:
                found = True
                break
        if not found:
            return _cond(UNKNOWN, "observación consumida %s sin evidencia que la cubra" % iv)
    return _cond(TRUE,
                 "diagnóstico: consumidos⊆evidencia declarada; binding NOT_EVALUATED (sin fuente sellada)",
                 ["evidence.intervals", "diagnostic.limited_coverage"])


def _check_D(case: Dict[str, Any]) -> Dict[str, Any]:
    domain = case.get("domain")
    if not isinstance(domain, dict):
        return _cond(UNKNOWN, "sin dominio declarado")
    required = ("artifact_sha256", "function", "scope", "limits")
    missing = [k for k in required if not domain.get(k)]
    if missing:
        return _cond(UNKNOWN, "dominio incompleto: faltan %s" % missing)
    return _cond(TRUE,
                 "dominio explícito: %s @ %s, scope=%s, límites=%d" % (
                     domain["function"], domain["artifact_sha256"][:12],
                     domain["scope"], len(domain["limits"])),
                 ["domain.artifact", "domain.scope", "domain.limits"])


_CHECKS = {CHK_B: _check_B, CHK_W: _check_W, CHK_O: _check_O,
           CHK_L: _check_L, CHK_C: _check_C, CHK_D: _check_D}


def evaluate(case: Dict[str, Any]) -> Dict[str, Any]:
    """Evalúa un caso y devuelve el veredicto del testigo.  Determinista."""
    errors: List[str] = []
    if not isinstance(case, dict):
        return _blocked("caso debe ser objeto")
    region = case.get("region")
    if not isinstance(region, dict) or "base" not in region or "size" not in region:
        return _blocked("caso sin región válida")
    try:
        size = int(region["size"])
        int(region["base"])
        if size < 0 or size > 2**31:
            raise ValueError("size fuera de dominio")
    except (TypeError, ValueError):
        return _blocked("tamaño o base de región inválida")

    results = {k: _CHECKS[k](case) for k in _CHECKS}
    values = [results[k]["value"] for k in _CHECKS]
    if all(v == TRUE for v in values):
        verdict = SAFE
    elif any(v == FALSE for v in values):
        verdict = BLOCKED
    else:
        verdict = ABSTAIN
    failed = [k for k in _CHECKS if results[k]["value"] == FALSE]
    unknown = [k for k in _CHECKS if results[k]["value"] == UNKNOWN]

    oracle = case.get("independent_oracle")
    oracle_ok = bool(oracle and str(oracle.get("result", "")).upper() == "PASS"
                     and oracle.get("tool")
                     and oracle.get("covers") == list(CONDITIONS))
    epistemic = EP_PROVEN if (verdict == SAFE and oracle_ok) else EP_PARTIAL
    if verdict == ABSTAIN:
        epistemic = EP_NOT_DETERMINED
    elif verdict == BLOCKED:
        epistemic = EP_BLOCKED

    return {
        "capability": CAPABILITY_ID,
        "capability_version": WITNESS_VERSION,
        "case_id": case.get("case_id"),
        "verdict": verdict,
        "epistemic_status": epistemic,
        "operational_status": OP_PASS if verdict == SAFE else (
            OP_BLOCKED if verdict == BLOCKED else OP_PARTIAL),
        "conditions": results,
        "verdict_basis": list(_CHECKS),
        "failed_conditions": failed,
        "unknown_conditions": unknown,
        "domain": case.get("domain"),
        "independent_oracle": oracle,
        "limitations": _limitations(case, results),
        "errors": errors,
        "manifest_verified": case.get("manifest_verified", []),
    }


def _limitations(case: Dict[str, Any],
                 results: Dict[str, Dict[str, Any]]) -> List[str]:
    lims = [
        "el testigo valida una transformación CONCRETA; no autoriza otras",
        "no ejecuta el artefacto; el modelo byte a byte cubre solo el dominio declarado",
        "el veredicto del testigo es independiente del veto del analizador; no revoca ABSTAIN previo",
        "PROVEN exige oráculo independiente que cubra TODAS las condiciones (B..D); con oráculo parcial el estatus máximo es PARTIAL",
    ]
    for k, v in results.items():
        if v["value"] == UNKNOWN:
            lims.append("condición %s desconocida: %s" % (k, v["detail"]))
    domain = case.get("domain") or {}
    for name in domain.get("limits", []):
        if name not in lims:
            lims.append(name)
    return lims


def _blocked(reason: str) -> Dict[str, Any]:
    return {
        "capability": CAPABILITY_ID,
        "capability_version": WITNESS_VERSION,
        "case_id": None,
        "verdict": BLOCKED,
        "epistemic_status": EP_BLOCKED,
        "operational_status": OP_BLOCKED,
        "conditions": {k: _cond(UNKNOWN, "no evaluado: %s" % reason) for k in _CHECKS},
        "verdict_basis": list(_CHECKS),
        "failed_conditions": list(_CHECKS),
        "unknown_conditions": [],
        "domain": None,
        "independent_oracle": None,
        "limitations": [reason],
        "errors": [reason],
        "manifest_verified": [],
    }


# ============================================================ IER glue

def as_capability_stub() -> Dict[str, Any]:
    """Semilla para ier.capability.declarar(); NO declara ni promociona nada."""
    return {
        "name": "transformer_witness",
        "purpose": "testigo independiente de seguridad de transformación sobre evidencia sellada",
        "domain": "re/decompiler-simplifiers",
        "version": WITNESS_VERSION,
        "limitations": [
            "requiere caso explícito con dominio declarado",
            "no ejecuta el artefacto",
            "SAFE exige B ∧ W ∧ O ∧ L ∧ C ∧ D",
        ],
    }


def select_capability() -> Dict[str, Any]:
    return {"id": CAPABILITY_ID, "version": WITNESS_VERSION,
            "available": True,
            "conditions": list(CONDITIONS),
            "verdicts": [SAFE, ABSTAIN, BLOCKED]}
