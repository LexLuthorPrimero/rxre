#!/usr/bin/env python3
# SPDX-License-Identifier: GPL-2.0
# WORK_CLASS=READ_ONLY · WRITE_EXECUTION=SCRATCH_ONLY (.rxre/state/evidence_contract/)
"""RXRE · IER · EVIDENCE_CONTRACT — contrato de vinculación K = (S, C, T, O).

## QUÉ ES

El contrato que exige la misión M10.10 entre:

    S  fuente de evidencia sellada (verificada por manifiesto antes de consumirse)
    C  caso que consume esa evidencia
    T  transformación propuesta
    O  conjunto de observaciones que deben preservarse

Regla de cierre (M10.10.1):

    SAFE ⇒ Bound(S, C, T, O) ∧ Complete(S, C, T, O)

Un manifiesto íntegro sin vinculación demostrada **no** puede justificar SAFE.

## PRECEDENCIA (resuelve la divergencia M10.9 sobre `evidence_intervals=[]`)

    fuente sellada  →  caso  →  transformación  →  observaciones

    1. La fuente sellada es autoritativa sobre QUÉ evidencia existe.
    2. El caso declara QUÉ observaciones son relevantes (O no puede ser
       implícitamente "todo" ni vacío por descuido).
    3. La transformación determina QUÉ bytes toca (span de writes).
    4. Ningún estado válido de estas cuatro capas por separado basta:
       deben coincidir región, artefacto/sha, función y provenance.

Reglas verificables:

    R1  Bound falla por artefacto/sha/función/región ausentes o discordantes.
    R2  Bound falla si algún intervalo de O sobrepasa los bytes de T.
    R3  Si T toca bytes y O = ∅  →  resultado NOT_DETERMINED (nunca SAFE).
    R4  Si T no toca bytes y O = ∅  →  caso VACUO; SAFE permitido SOLO con
        etiquetado explícito `vacuous: true` en el resultado.
    R5  Complete: cada iv ∈ O debe estar cubierto por (al menos) una evidencia de S
        cuyo intervalo la contenga, con procedencia verificable (subject/objeto/op).
    R6  Evidencia citada por el caso inexistente en S  →  Bound FALSE.
    R7  La validez del manifiesto nunca se infiere de la integridad del caso.

Estados: TRUE/FALSE/UNKNOWN por predicado; los consumidores (testigo y
verificador) DEBEN tratar UNKNOWN como ABSTAIN (fail-closed) y FALSE como BLOCKED.
Los consumidores documentan su uso de este contrato pero mantienen sus propias
aplicaciones; este módulo no es un oráculo.
"""
from __future__ import annotations

import hashlib
import json
import os
from typing import Any, Dict, List, Optional, Sequence, Tuple

CONTRACT_VERSION = "RYI-EVIDENCE-CONTRACT-1"

TRUE, FALSE, UNKNOWN = "TRUE", "FALSE", "UNKNOWN"

# categorías de evidencia que cuentan como observación de contenido o de
# modificación (las NO_OBSERVATION no observan nada).
_CONTENT_CATEGORIES = {
    "SCALAR_READ", "TEXTUAL_READ", "READ_MODIFY_WRITE", "WRITE_ONLY",
    "ADDRESS_ESCAPE", "OPAQUE_CALL",
}


def _canonical(obj: Any) -> str:
    return json.dumps(obj, sort_keys=True, separators=(",", ":"), ensure_ascii=False)


def sha256_text(text: str) -> str:
    return hashlib.sha256(text.encode("utf-8")).hexdigest()


# ---------------------------------------------------------------- utilidades

def _candidate(sealed: Dict[str, Any], region_id: str) -> Optional[Dict[str, Any]]:
    for c in sealed.get("candidates", []):
        if c.get("candidate_id") == region_id:
            return c
    return None


def _case_artifact_sha(case: Dict[str, Any]) -> Optional[str]:
    art = case.get("artifact") or {}
    sha = art.get("sha256")
    return sha if isinstance(sha, str) else None


def _sealed_function(sealed: Dict[str, Any], cand: Optional[Dict[str, Any]]) -> Optional[str]:
    """Función según la fuente sellada (nivel análisis con fallback a evidencias)."""
    art = sealed.get("artifact") or {}
    fn = art.get("function")
    if isinstance(fn, str) and fn:
        return fn
    if cand:
        for e in cand.get("evidence", []):
            prov = e.get("provenance") or {}
            fn = prov.get("function")
            if fn:
                return str(fn)
    return None


def _sealed_sha(sealed: Dict[str, Any], cand: Optional[Dict[str, Any]]) -> Optional[str]:
    """sha256 del artefacto según la fuente sellada (nivel análisis, con fallback a evidencias)."""
    art = sealed.get("artifact") or {}
    sha = art.get("sha256")
    if isinstance(sha, str) and sha:
        return sha
    if cand:
        for e in cand.get("evidence", []):
            prov = e.get("provenance") or {}
            sha = prov.get("artifact_sha256")
            if sha:
                return str(sha)
    return None


def _case_function(case: Dict[str, Any]) -> Optional[str]:
    fn = (case.get("artifact") or {}).get("function")
    if fn:
        return str(fn)
    # fallback: buscar en dominio
    dom = case.get("domain") or {}
    fn = dom.get("function")
    return str(fn) if fn else None


def _intervals_overlap(a: Sequence[int], b: Sequence[int]) -> bool:
    return a[0] < b[1] and b[0] < a[1]


def _covers(iv: Sequence[int], e_iv: Sequence[int]) -> bool:
    return e_iv[0] <= iv[0] and iv[1] <= e_iv[1]


# ---------------------------------------------------------------- contrato K

def verify_binding(case: Dict[str, Any],
                   sealed_analysis: Dict[str, Any]) -> Dict[str, Any]:
    """Verifica Bound(S, C, T, O) y Complete(S, C, T, O).

    Devuelve un dict con:
      bound: TRUE|FALSE|UNKNOWN
      complete: TRUE|FALSE|UNKNOWN
      vacuous: bool (True solo si T no toca bytes y O==∅)
      coverage: ids de evidencias que cubren cada iv de O
      violations: lista de motivos ([] si todo bien)
    """
    violations: List[str] = []   # fatales: invalidan Bound
    advisories: List[str] = []   # no fatales: registro obligatorio, no invalidan
    coverage: List[str] = []

    if not isinstance(sealed_analysis, dict):
        return {"bound": UNKNOWN, "complete": UNKNOWN, "vacuous": False,
                "coverage": [], "violations": ["fuente sellada ausente o malformada"],
                "advisories": []}
    cand = _candidate(sealed_analysis, str(case.get("region", {}).get("id")))
    if cand is None:
        return {"bound": FALSE, "complete": FALSE, "vacuous": False,
                "coverage": [],
                "violations": ["candidato %r ausente en la fuente sellada" %
                               case.get("region", {}).get("id")],
                "advisories": advisories}
    # registro de procedencia débil: evidencias sin sha256 propio (advisory)
    weak = sum(1 for e in cand.get("evidence", [])
               if not (e.get("provenance") or {}).get("artifact_sha256"))
    if weak:
        advisories.append(
            "procedencia débil: %d evidencias sin artifact_sha256 propio "
            "(vinculación por sello de análisis completa a nivel contenedor)" % weak)

    # R7: manifiesto — ya verificado por el cargador; aquí sólo se registra.
    case_sha = _case_artifact_sha(case)
    seal_sha = _sealed_sha(sealed_analysis, cand)
    if case_sha and seal_sha and case_sha != seal_sha:
        violations.append("fuente sellada pertenece a OTRO artefacto (%s… vs %s…)" %
                          (seal_sha[:12], case_sha[:12]))
    elif not seal_sha:
        # sin sha en ningún nivel: no hay identificación demostrable del artefacto
        violations.append("fuente sellada sin artifact_sha256 en ningún nivel (sin procedencia vinculante)")

    case_fn = _case_function(case)
    seal_fn = _sealed_function(sealed_analysis, cand)
    if case_fn and seal_fn and str(case_fn) != str(seal_fn):
        violations.append("función discordante: caso %s vs fuente %s" % (case_fn, seal_fn))

    # R2: todo intervalo de O debe solapar con al menos un intervalo del span de T.
    consumed = (case.get("observations") or {}).get("consumed_intervals") or []
    t_span = (case.get("proposed_transform") or {}).get("overlap_intervals") or []
    if t_span:
        for iv in consumed:
            if not any(_intervals_overlap(iv, span) for span in t_span):
                violations.append("observación %s fuera del span de la transformación" % (iv,))

    # R6: toda evidencia citada por el caso debe existir en S.
    declared = (case.get("observations") or {}).get("evidence_intervals")
    if isinstance(declared, list):
        known = {e.get("id") for e in cand.get("evidence", [])}
        missing = [e.get("id") for e in declared if e.get("id") not in known]
        if missing:
            violations.append("caso cita evidencias inexistentes en la fuente: %s" % missing)

    bound = FALSE if violations else TRUE

    # R3/R4: O vacío vs T que toca bytes.
    if not consumed:
        if t_span:
            return {"bound": bound if bound == FALSE else UNKNOWN,
                    "complete": UNKNOWN,
                    "vacuous": False,
                    "coverage": [],
                    "violations": violations +
                    ["T toca bytes pero el caso no declara observaciones (O=∅): fallback fail-closed"],
                    "advisories": advisories}
        return {"bound": bound if bound == FALSE else TRUE,
                "complete": TRUE if bound != FALSE else FALSE,
                "vacuous": True,
                "coverage": [],
                "violations": violations,
                "advisories": advisories}

    # Complete: cada iv debe estar cubierto por evidencia de contenido de S.
    for iv in consumed:
        found = None
        for e in cand.get("evidence", []):
            eiv = e.get("interval")
            if isinstance(eiv, list) and _covers(iv, eiv):
                # debe tener categoría de observación, no NO_OBSERVATION
                if e.get("category") in _CONTENT_CATEGORIES:
                    found = e
                    break
        if not found:
            violations.append("consumido %s sin evidencia de S que lo cubra" % (iv,))
        else:
            coverage.append(found["id"])

    complete = TRUE if (bound != FALSE and not any(
        v.startswith("consumido") for v in violations)) else FALSE
    if any(v.startswith("consumido") for v in violations):
        complete = UNKNOWN
    return {"bound": bound, "complete": complete, "vacuous": False,
            "coverage": sorted(set(coverage)),
            "violations": violations,
            "advisories": advisories}


def check_binding(case: Dict[str, Any],
                  sealed_analysis: Dict[str, Any]) -> Dict[str, Any]:
    """Interfaz pública: {bound, complete, vacuous, verdict_hint, coverage, violations}."""
    r = verify_binding(case, sealed_analysis)
    bound, complete = r["bound"], r["complete"]
    if r["vacuous"] and bound != FALSE:
        hint = "VACUOUS"   # SAFE permitido SOLO con etiquetado explícito
    elif bound == FALSE:
        hint = "BLOCKED"
    elif complete == TRUE:
        hint = "SAFE_ALLOWED"
    else:
        hint = "ABSTAIN"
    r["verdict_hint"] = hint
    return r
