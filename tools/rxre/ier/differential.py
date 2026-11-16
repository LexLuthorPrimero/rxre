#!/usr/bin/env python3
"""ier/differential.py — Comparacion oraculo vs adapter y discriminacion. IER-EVOLVE-001 · M9.

## QUE ES

Compara dos representaciones INDEPENDIENTES del mismo artefacto:

    oraculo   = binexpr.identify_evidence + cfg.build_cfg (evidencia propia)
    adaptador = salida NORMALIZADA del backend bajo prueba (rizin via
                backends/adapters/rz_functions.py, sin tocar el adapter)

El oraculo NUNCA consulta al adapter para construir su expectativa.
Una divergencia detectada correctamente es un EXITO OPERATIVO del
comparador, no un error: DIVERGENCE no implica ERROR.

## ESTADOS (tres ejes independientes, contrato §4)

    operational_status:  PASS | BLOCKED | ERROR
    comparison_status:   MATCH | DIVERGENCE | INCONCLUSIVE
    epistemic_status:    PROVEN | PARTIAL | NOT_DETERMINED | BLOCKED

    - adapter con fallo tecnico -> INCONCLUSIVE (no se inventa concordancia)
    - adapter devolvio cero observaciones sobre funcion que el oraculo
      afirma -> DIVERGENCE (property missing_observation): el defecto se
      demuestra por ausencia, no por cifra
    - divergencia real -> operational PASS (el predictor sigue vivo),
      epistemic NOT_DETERMINED hasta anclar evidencia adicional
    - concordancia por si sola no eleva epistemic: PROVEN exige dominio
      declarado y mas evidencia

## PREREGISTRO §6.3 (fijacion de hipotesis, control de ejecucion)

PREREGISTRATION_6948 fija H1/H3, los brazos a-d, predicciones por brazo y
respecto de cada rival, y la regla de refutacion ANTES de cualquier
ejecucion. `check_separation()` verifica estaticamente que hay al menos
un brazo donde los rivales discrepan; los brazos donde todos los rivales
predicen igual estan marcados separates=false y NO cuentan como evidencia
discriminatoria.
"""
from __future__ import annotations

from typing import Any, Dict, List, Optional

MODULE_REVISION = "ier-differential-1"

OP_PASS, OP_BLOCKED, OP_ERROR = "PASS", "BLOCKED", "ERROR"
CMP_MATCH, CMP_DIVERGENCE, CMP_INCONCLUSIVE = "MATCH", "DIVERGENCE", "INCONCLUSIVE"
EP_PROVEN, EP_PARTIAL, EP_NOT_DETERMINED, EP_BLOCKED = (
    "PROVEN", "PARTIAL", "NOT_DETERMINED", "BLOCKED")

# --- Preregistro del experimento discriminante (§6.3 / arm d) ---------------
# FECHADO EN EL CODIGO: cualquier brazo que todos los rivales predicen igual
# esta marcado separates=false y no cuenta. El brazo d SI separa H1 y H3.
PREREGISTRATION_6948: Dict[str, Any] = {
    "question": "¿El truncamiento de CALL retpoline en #6948 depende del TIPO de relocation o del reconocimiento thunk+flag?",
    "domain": "ET_REL x86-64, analysis.jmp.retpoline=true",
    "hypotheses": {
        "H1": {
            "claim": "toda CALL hacia un simbolo *__x86_indirect_thunk_* se analiza como RJMP (truncamiento), INDEPENDIENTEMENTE del tipo de relocation",
            "predicts": {"a": "truncamiento", "b": "sin truncamiento", "c": "igual en ambas codificaciones", "d": "truncamiento"},
        },
        "H3": {
            "claim": "el defecto exige la combinacion { analysis.jmp.retpoline=true, nombre thunk, relocation R_X86_64_PLT32 }",
            "predicts": {"a": "truncamiento", "b": "sin truncamiento", "c": "igual en ambas codificaciones", "d": "sin truncamiento"},
        },
    },
    "arms": [
        {"arm": "a", "fixture": "PLT32 -> __x86_indirect_thunk_rax (control positivo)",
         "role": "confirmatory", "separates": False},
        {"arm": "b", "fixture": "PLT32 -> simbolo NO-thunk (funcion ordinaria)",
         "role": "control_negative", "separates": False},
        {"arm": "c", "fixture": "jcc rel8 vs jcc rel32 (robustez de codificacion)",
         "role": "robustness", "separates": False},
        {"arm": "d", "fixture": "PC32 -> __x86_indirect_thunk_rax (MISMA instruccion, otra relocation)",
         "role": "discriminant", "separates": True},
    ],
    "refutation": {
        "arm_d_observado": {
            "truncamiento": "refuta H3; H1 permanece candidata en su dominio",
            "sin_truncamiento": "refuta H1; H3 permanece candidata en su dominio",
            "error_tecnico": "ningun rival refutado: resultado INCONCLUSIVE",
        },
    },
    "separation_rule": ("un brazo cuenta como discriminante solo si al menos "
                        "dos rivales predicen resultados distintos en el; los "
                        "brazos que no separan NO aportan evidencia contra "
                        "ningun rival aunque fallen"),
    "preserved_conditions": (
        "bytes de la CALL, nombre/ubicacion del thunk, seccion/posicion de la "
        "instruccion, contexto de control de flujo, version/opciones de rizin: "
        "constantes entre A (fixture a) y B (fixture d)"),
}


def check_separation(reg: Dict[str, Any]) -> Dict[str, Any]:
    """Verifica estaticamente que hay al menos un brazo separante.

    Devuelve un dict con `ok`, `separating_arms` y `notes`. No ejecuta
    nada: es una comprobacion del preregistro, no del resultado.
    """
    separating = [a for a in reg.get("arms", []) if a.get("separates")]
    hypotheses = reg.get("hypotheses", {})
    notes = []
    ok_arms = []
    for arm in separating:
        preds = {h: hdef["predicts"].get(arm["arm"])
                 for h, hdef in hypotheses.items()}
        distinct = len(set(preds.values())) > 1
        if distinct:
            ok_arms.append(arm["arm"])
        else:
            notes.append("brazo %s marcado separante pero sus predicciones "
                         "coinciden: no discrimina" % arm["arm"])
    return {"ok": len(ok_arms) >= 1,
            "separating_arms": ok_arms,
            "not_discriminating_notes": notes}


def adapter_observation_from_functions(adapter_result: Dict[str, Any]) -> Dict[str, Any]:
    """Normaliza un envelope `rz_functions.functions` a observacion minima.

    No es un adapter ni duplica el registro: es la frontera de lectura
    entre la salida del backend y este comparador.
    """
    status = adapter_result.get("status") or "error"
    out = {"status": status, "tool": (adapter_result.get("backend") or {}).get("backend_id", "unknown"),
           "observations": []}
    if status != "ok":
        return out
    for res in adapter_result.get("results") or []:
        value = res.get("value") or {}
        for f in value.get("funciones") or []:
            name = f.get("name") or ""
            out["observations"].append({
                "name": name,
                "stem": name.split(".")[-1] if "." in name else name,
                "offset": f.get("offset"),
                "size": f.get("size"),
                "realsz": f.get("realsz"),
                "nbbs": f.get("nbbs"),
            })
    return out


def _stFunc(evidence: Dict[str, Any]) -> List[Dict[str, Any]]:
    return [s for s in evidence.get("symbols", [])
            if s.get("type") == "STT_FUNC" and s.get("st_shndx") not in (0,)]


def _oracle_function_facts(evidence: Dict[str, Any], cfg: Dict[str, Any]) -> List[Dict[str, Any]]:
    facts = []
    covs = {}
    for r in evidence.get("instruction_coverage", {}).get("declared_code_ranges", []):
        covs[r["section"]] = (r["start"], r["end"])
    for s in _stFunc(evidence):
        if s.get("st_size", 0) > 0:
            expected_size = s["st_size"]
        else:
            expected_size = covs.get(s["st_shndx"], (0, 0))[1] - covs.get(s["st_shndx"], (0, 0))[0]
        facts.append({"name": s["name"], "offset": s["st_value"],
                      "expected_size": expected_size,
                      "expected_realsz": expected_size,
                      "section": s["st_shndx"]})
    # bloques dentro del rango de cada funcion
    blocks = cfg.get("blocks", [])
    for fact in facts:
        start, end = fact["offset"], fact["offset"] + fact["expected_size"]
        fact["expected_nbbs"] = sum(
            1 for b in blocks
            if b["section"] == fact["section"]
            and b["bytes_range"][0] >= start and b["bytes_range"][1] <= end)
    return facts


def _divergence(prop: str, expected: Any, observed: Any, refs: List[str],
                scope: str) -> Dict[str, Any]:
    return {"property": prop, "expected": expected, "observed": observed,
            "evidence_refs": list(refs), "scope": scope}


def compare(evidence: Dict[str, Any], cfg: Dict[str, Any],
            adapter_observation: Dict[str, Any],
            scope: str = "") -> Dict[str, Any]:
    limitations: List[str] = []

    def make(operational: str, comparison: str, epistemic: str,
             divergences: List[Dict[str, Any]]) -> Dict[str, Any]:
        return {
            "operational_status": operational,
            "comparison_status": comparison,
            "epistemic_status": epistemic,
            "divergences": divergences,
            "adapter": {"tool": adapter_observation.get("tool"),
                        "status": adapter_observation.get("status"),
                        "n_observations": len(adapter_observation.get("observations", []))},
            "limitations": limitations,
            "revision": MODULE_REVISION,
        }

    if evidence.get("operational_status") != OP_PASS:
        ep = EP_BLOCKED if evidence.get("operational_status") == OP_BLOCKED else EP_NOT_DETERMINED
        return make(evidence.get("operational_status"), CMP_INCONCLUSIVE, ep, [])

    if cfg.get("operational_status") != OP_PASS:
        return make(OP_ERROR, CMP_INCONCLUSIVE, EP_NOT_DETERMINED, [])

    astatus = adapter_observation.get("status")
    if astatus not in ("ok", "empty"):
        limitations.append("adapter termino con status=%s: sin observacion comparable" % astatus)
        return make(OP_PASS, CMP_INCONCLUSIVE, EP_NOT_DETERMINED, [])

    obs_by_stem = {o.get("stem"): o for o in adapter_observation.get("observations", [])}
    facts = _oracle_function_facts(evidence, cfg)
    scope = scope or ("ET_REL x86-64; %s" % evidence.get("artifact_sha256", "?")[:16])

    divergences: List[Dict[str, Any]] = []
    refs = ["elf:.text", "symbols:STT_FUNC", "decoded-by:GNU objdump",
            "artifacts:%s" % evidence.get("artifact_sha256", "?")[:16]]
    missing = 0
    for fact in facts:
        obs = obs_by_stem.get(fact["name"])
        if obs is None:
            missing += 1
            divergences.append(_divergence(
                "missing_observation",
                {"function": fact["name"], "expected_size": fact["expected_size"]},
                None, refs, scope))
            continue
        if obs.get("size") is not None and obs["size"] != fact["expected_size"]:
            divergences.append(_divergence(
                "analyzed_size", fact["expected_size"], obs["size"],
                refs + ["adapter:%s" % adapter_observation.get("tool")], scope))
        if obs.get("realsz") is not None and obs["realsz"] != fact["expected_realsz"]:
            divergences.append(_divergence(
                "analyzed_realsz", fact["expected_realsz"], obs["realsz"],
                refs + ["adapter:%s" % adapter_observation.get("tool")], scope))
        if obs.get("nbbs") is not None and fact["expected_nbbs"] > 0 \
                and obs["nbbs"] != fact["expected_nbbs"]:
            divergences.append(_divergence(
                "basic_block_count", fact["expected_nbbs"], obs["nbbs"],
                refs + ["cfg:ier/cfg", "adapter:%s" % adapter_observation.get("tool")],
                scope))

    if missing == len(facts) and facts:
        # el adapter no observa nada de lo que el oraculo afirma: defecto por
        # ausencia, con todas las propiedades esperadas como evidencia
        limitations.append("el adapter no produjo observaciones para NINGUNA funcion declarada")
        return make(OP_PASS, CMP_DIVERGENCE, EP_NOT_DETERMINED, divergences)

    if divergences:
        return make(OP_PASS, CMP_DIVERGENCE, EP_NOT_DETERMINED, divergences)

    limitations.append("concordancia observada; no equivale a PROVEN (dominio no declarado ampliamente)")
    return make(OP_PASS, CMP_MATCH, EP_PARTIAL, [])
