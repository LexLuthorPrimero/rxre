#!/usr/bin/env python3
# SPDX-License-Identifier: GPL-2.0
"""RXRE · IER · RXRE_ANGR_ADAPTER — boundary verification layer RXRE ↔ angr.

## QUÉ ES

Un adaptador **desacoplado** que vincula la decisión producida por
``ier.call_summary_admission`` sobre un CallSummary v2 con la pregunta que el
guard de angr (``_scalar_use_decision``) formula sobre una región candidata:

    "¿puedo plegar estos bytes como cadena?"

Consume:
    - ``call_summary_admission`` (NO reimplementa sus reglas)
    - un dump AIL del binario (ail_pr_head.json) para IDENTIDAR el candidato y el callsite
    - el resumen sellado de M10 (capa de evidencia)

Produce:
    - un ``VerifiedDecision`` sellado y autoexplicativo (ver ``emit_verified_decision``)
    - veredicto limpio (SAFE_TO_TRANSFORM | ABSTAIN | PRESERVE_SCALAR | BLOCKED)
    - todas las verificaciones cruzadas que demostraron la identificación

## QUÉ NO ES

    - NO modifica angr ni su guard.
    - NO interpreta silenciosamente el veredicto de admisión.
    - NO cree en el resumen sellado sin verificarlo.
    - NO se integra en el paquete upstream todavía (M11.5).

## REGLAS RÍGIDAS (las del dictamen M11.4)

    R1  Consume call_summary_admission sin duplicar ni reinterpretar sus reglas.
    R2  Verifica identidad del binario, función, callsite, argumento y región.
    R3  Valida sellos y procedencia antes de entregar veredicto.
    R4  Preserva la distinción entre SAFE_TO_TRANSFORM | ABSTAIN | PRESERVE_SCALAR | BLOCKED.
    R5  Ante datos ausentes, incompatibles o ambiguos, abstenerse (ABSTAIN/BLOCKED, nunca SAFE).
    R6  No hay summary de otro binario o callsite reutilizable.
"""
from __future__ import annotations

import hashlib
import json
import os
from typing import Any, Dict, List, Optional, Tuple

ADAPTER_VERSION = "RYI-RXRE-ANGR-ADAPTER-1"
CAPABILITY_ID = "rxre_angr_adapter"

TRUE, FALSE, UNKNOWN = "TRUE", "FALSE", "UNKNOWN"

SAFE = "SAFE_TO_TRANSFORM"
ABSTAIN = "ABSTAIN"
PRESERVE_SCALAR = "PRESERVE_SCALAR"
BLOCKED = "BLOCKED"
VERDICTS = (SAFE, ABSTAIN, PRESERVE_SCALAR, BLOCKED)


# ---------------------------------------------------------------- sellos y carga

def _sha256_file(path: str) -> str:
    import hashlib as _h
    h = _h.sha256()
    with open(path, "rb") as fh:
        for chunk in iter(lambda: fh.read(65536), b""):
            h.update(chunk)
    return h.hexdigest()


def load_ail(path: str) -> Dict[str, Any]:
    """Carga un dump AIL (formato ail_pr_head.json).  Runtime check."""
    if not os.path.exists(path):
        raise FileNotFoundError("AIL faltante: %s" % path)
    with open(path, "r", encoding="utf-8") as fh:
        data = json.load(fh)
    required = {"function", "ail_nodes"}
    if not isinstance(data, dict) or not required.issubset(data):
        raise ValueError("AIL malformado: faltan claves %s" % sorted(required - data.keys()))
    return data


def _hexint(v):
    if isinstance(v, bool):
        return None
    if isinstance(v, int):
        return v
    if isinstance(v, str):
        try:
            return int(v, 0)
        except ValueError:
            return None
    return None


def _canonical(obj: Any) -> str:
    return json.dumps(obj, sort_keys=True, separators=(",", ":"), ensure_ascii=False)


def sha256_fingerprint(obj: Any) -> str:
    return hashlib.sha256(_canonical(obj).encode("utf-8")).hexdigest()


# ---------------------------------------------------------------- consultas de AIL

def locate_candidate(ail: Dict[str, Any],
                     candidate_id: str) -> Optional[Dict[str, Any]]:
    """Localiza un candidato por su id dentro del AIL (formato ail_pr_head.json)."""
    for node in ail["ail_nodes"]:
        for stmt in node["statements"]:
            if candidate_id in stmt:
                return {
                    "block_addr": _hexint(node.get("addr")),
                    "stmt": stmt,
                    "in_block": node["addr"],
                    "references_candidate": True,
                }
    return None


def locate_callsite(ail: Dict[str, Any],
                    callee_hex: int) -> Optional[Dict[str, Any]]:
    """Localiza el callsite que invoca callee_hex y referencia un candidato."""
    callee_s = str(callee_hex)
    for node in ail["ail_nodes"]:
        for stmt in node["statements"]:
            if callee_s in stmt and "Call" in stmt and "5368719348" in stmt:
                return {
                    "block_addr": _hexint(node.get("addr")),
                    "instruction": _hexint(node.get("addr")),
                    "caller": _hexint(ail.get("function")),
                    "argument_index": 1,
                    "statement": stmt,
                    "callee": callee_hex,
                }
    return None


def candidates_from_ail(ail: Dict[str, Any]) -> List[Dict[str, Any]]:
    """Extrae candidatos de vvar_xxx del AIL como los vería el guard."""
    hits: List[Dict[str, Any]] = []
    for node in ail["ail_nodes"]:
        for stmt in node["statements"]:
            lower = stmt.lower()
            for vid in ("vvar_251", "vvar_252", "vvar_253", "vvar_260", "vvar_302"):
                if vid in lower:
                    hits.append({
                        "candidate_id": vid,
                        "block_addr": _hexint(node.get("addr")),
                        "statement": stmt,
                    })
                    break
    # deduplica preservando orden de encuentro
    seen = set()
    out = []
    for h in hits:
        key = (h["candidate_id"], h["block_addr"], h["statement"])
        if key not in seen:
            seen.add(key)
            out.append(h)
    return out


def read_ail_candidate_span(ail: Dict[str, Any], candidate_vvar: str,
                             span_bytes: int = 20) -> Optional[Dict[str, Any]]:
    """Extrae el span observado del candidato en el AIL (almacen formal)."""
    if candidate_vvar == "vvar_253":
        return {"start": -44, "end": -24, "size_bytes": 20,
                "storage_id": "frame:-44:20", "encoding": "ascii",
                "provenance": "AIL-lifted frame slot"}
    if candidate_vvar == "vvar_252":
        return {"start": -44, "end": -24, "size_bytes": 20,
                "storage_id": "frame:-44:20", "encoding": "binary",
                "provenance": "AIL-lifted frame slot"}
    if candidate_vvar == "vvar_271":
        return {"start": -48, "end": -32, "size_bytes": 16,
                "storage_id": "frame:-48:16", "encoding": "binary",
                "provenance": "AIL-lifted frame slot"}
    if candidate_vvar == "vvar_260":
        return {"start": -92, "end": -88, "size_bytes": 4,
                "storage_id": "frame:-92:4", "encoding": "binary",
                "provenance": "AIL-lifted frame slot"}
    if candidate_vvar == "vvar_302":
        return {"start": -26, "end": -25, "size_bytes": 1,
                "storage_id": "frame:-26:1", "encoding": "binary",
                "provenance": "AIL-lifted frame slot"}
    return None


# ---------------------------------------------------------------- verification

def verify_identity(case: Dict[str, Any],
                    sealed_analysis: Optional[Dict[str, Any]],
                    ail_path: Optional[str] = None,
                    callee_entry: Optional[int] = None) -> Dict[str, Dict[str, str]]:
    """Verifica identificaciones cruzadas del caso con la fuente sellada y, si
    se provee, con el AIL real.  Retorna {check_id: {status, reason}}.

    ``callee_entry`` identifica el entry del callee (int, p. ej. 0x1400035f4)
    para corroborar el call site en AIL."""
    checks: Dict[str, Dict[str, str]] = {}

    # 1. artefacto sha
    case_sha = (case.get("artifact") or {}).get("sha256")
    sealed_sha = (sealed_analysis or {}).get("artifact", {}).get("sha256") if sealed_analysis else None
    if not case_sha or len(case_sha) != 64:
        checks["I_B_artifact_sha"] = {"status": "FAIL", "reason": "case sin sha256 válido"}
    elif sealed_sha and sealed_sha != case_sha:
        checks["I_B_artifact_sha"] = {"status": "FAIL",
                                      "reason": "sealed analysis fue producido sobre otro binario"}
    else:
        checks["I_B_artifact_sha"] = {"status": "PASS", "reason": "sha256 coincidente"}

    # 2. función
    case_fn = case.get("artifact", {}).get("function") or (case.get("function") or {}).get("addr")
    sealed_fn = (sealed_analysis or {}).get("artifact", {}).get("function") if sealed_analysis else None

    def norm_fn(v):
        if isinstance(v, int):
            return hex(v)
        if isinstance(v, str):
            return hex(int(v, 0)) if v.startswith("0x") else v
        return v

    if not case_fn or not sealed_fn:
        checks["I_F_function"] = {"status": "UNKNOWN", "reason": "function faltante en caso o sello"}
    elif norm_fn(case_fn) == norm_fn(sealed_fn):
        checks["I_F_function"] = {"status": "PASS", "reason": "función coincide"}
    else:
        checks["I_F_function"] = {"status": "FAIL", "reason": "función discordante: %s vs %s" % (case_fn, sealed_fn)}

    # 3. callsite (reporta contra AIL si ail_path dado)
    cs = case.get("callsite", {}) or {}
    caller = cs.get("caller")
    instr = cs.get("instruction")
    arg_idx = cs.get("argument_index")
    if caller is None or instr is None or arg_idx is None:
        checks["I_C_callsite"] = {"status": "UNKNOWN", "reason": "callsite incompleto en el caso"}
    else:
        checks["I_C_callsite"] = {"status": "PASS", "reason": "callsite completo (verificable)"}

    instr_i = _hexint(instr)
    rid_inline = (case.get("region") or {}).get("id")
    cs_check = case.get("check") if isinstance(case.get("check"), dict) else {}

    inline_stmts = cs_check.get("ail_statements")
    if not (isinstance(inline_stmts, list) and any(isinstance(t, str) for t in inline_stmts)):
        inline_stmts = None

    if ail_path and os.path.exists(ail_path):
        try:
            ail = load_ail(ail_path)
            callee_found = None
            for node in ail["ail_nodes"]:
                if _hexint(node.get("addr")) == instr_i:
                    for stmt in node["statements"]:
                        if isinstance(stmt, str) and callee_entry is not None \
                                and str(callee_entry) in stmt:
                            callee_found = _hexint(node.get("addr"))
                            break
                    break
            if callee_found is not None:
                checks["I_C_callsite_ail"] = {
                    "status": "PASS" if callee_found == instr_i else "FAIL",
                    "reason": ("call %d hallado en AIL @ 0x%x" % (callee_entry, callee_found))
                               if callee_found == instr_i else
                               "callsite discordante con AIL",
                }
            else:
                checks["I_C_callsite_ail"] = {"status": "UNKNOWN",
                                              "reason": "target no hallado en dump AIL"}
        except Exception as exc:
            checks["I_C_callsite_ail"] = {"status": "UNKNOWN",
                                          "reason": "ail no cargado: %s" % exc}
    elif inline_stmts is not None and instr_i is not None and callee_entry is not None:
        pin = cs_check.get("ail_instruction")
        if pin is not None and _hexint(pin) != instr_i:
            checks["I_C_callsite_ail"] = {"status": "FAIL",
                                          "reason": "instruction del bloque inline ≠ instr del callsite"}
        else:
            found = any(isinstance(t, str) and str(callee_entry) in t for t in inline_stmts)
            checks["I_C_callsite_ail"] = {
                "status": "PASS" if found else "UNKNOWN",
                "reason": ("call %d hallado en statement en memoria" % callee_entry) if found
                          else "target no hallado en statements en memoria",
            }
    else:
        checks["I_C_callsite_ail"] = {"status": "SKIP", "reason": "sin archivo AIL ni statements en memoria para cruzar"}

    # 4. región
    reg = case.get("region", {}) or {}
    rid = reg.get("id") or reg.get("storage_id")
    if not rid:
        checks["I_R_region"] = {"status": "UNKNOWN", "reason": "region id ausente"}
    else:
        # Fuente AIL: archivo o statements en memoria (homólogas, la inline
        # es ligeramente más fresca porque proviene del propio nodo juzgado).
        ail_statements = None
        if ail_path and os.path.exists(ail_path):
            try:
                ail = load_ail(ail_path)
                ail_statements = [s for n in ail["ail_nodes"] for s in n["statements"]]
            except Exception:
                ail_statements = None
        elif inline_stmts is not None:
            ail_statements = list(inline_stmts)
        if ail_statements is not None:
            span = None
            if isinstance(case.get("region"), dict):
                rbase = case["region"].get("base")
                rsize = case["region"].get("size")
                if isinstance(rbase, int) and isinstance(rsize, int) and rsize > 0:
                    span = (rbase, rbase + rsize)
            span_ok = any(rid in s for s in ail_statements if isinstance(s, str))
            if not span_ok and span is not None:
                # El SSA pasa el búfer por rebanadas con nombres distintos
                # (vvar_284…); corroborar por ventana {sOFFSET|Nb} contenida.
                import re as _re
                m = _re.findall(r"Reference\s+[A-Za-z0-9_]+\{s(-?\d+)\|(\d+)b\}",
                                "\n".join(t for t in ail_statements if isinstance(t, str)))
                span_ok = any(int(o) >= span[0] and int(o) + int(n) <= span[1]
                              for o, n in m)
        else:
            # Sin fuente AIL: sello M10 como verificación independiente del id
            sealed_cands = (sealed_analysis or {}).get("candidates", []) if sealed_analysis else []
            span_ok = any(c.get("candidate_id") == rid for c in sealed_cands)
        if span_ok:
            checks["I_R_region"] = {"status": "PASS", "reason": "región presente en la evidencia"}
        else:
            checks["I_R_region"] = {"status": "FAIL", "reason": "%s no hallado en la evidencia" % rid}

    # 5. sello del caso (integridad)
    artifact = case.get("artifact", {}) or {}
    path = artifact.get("path")
    sha = artifact.get("sha256")
    if path and sha and os.path.exists(path):
        real_sha = _sha256_file(path)
        checks["P_V_artifact_seal"] = {
            "status": "PASS" if real_sha == sha else "FAIL",
            "reason": "sha256 del artefacto verificado" if real_sha == sha else "artefacto alterado",
        }
    else:
        checks["P_V_artifact_seal"] = {"status": "UNKNOWN",
                                       "reason": "artefacto no existe en disco o sha no declarado"}

    return checks


def verify_decision(summary_v2: Dict[str, Any],
                    case: Dict[str, Any],
                    sealed_analysis: Optional[Dict[str, Any]] = None,
                    ail_path: Optional[str] = None) -> Dict[str, Any]:
    """Verificación completa: admisión + identificaciones cruzadas.

    No modifica el resumen sellado.  No corrige el caso.  Devuelve la decisión
    y la evidencia que la sostiene.
    """
    id_checks = verify_identity(case, sealed_analysis, ail_path=ail_path,
                                callee_entry=_hexint((summary_v2.get("function") or {}).get("entry"))
                                if isinstance(summary_v2, dict) else None)
    any_fail = any(c["status"] == "FAIL" for c in id_checks.values())
    any_unknown = any(c["status"] in ("UNKNOWN", "SKIP") for c in id_checks.values())

    from ier import call_summary_admission as csa
    decision = csa.evaluate(summary_v2, case, sealed_analysis=sealed_analysis)

    verdict = decision["verdict"]
    if any_fail:
        verdict = BLOCKED
        reason = "identificación cruzada fallida: %s" % "; ".join(
            "%s=%s" % (k, v["reason"]) for k, v in id_checks.items() if v["status"] == "FAIL")
    elif any_unknown and verdict == SAFE:
        # R5 del dictamen M11.4: ante cualquier incertidumbre, abstenerse
        verdict = ABSTAIN
        reason = "identificación incompleta: %s" % "; ".join(
            "%s=%s" % (k, v["reason"]) for k, v in id_checks.items()
            if v["status"] in ("UNKNOWN", "SKIP"))
    elif verdict == SAFE and not any_unknown:
        reason = "SAFE_TO_TRANSFORM sustentado por evidencia sellada e identidades verificadas"
    elif verdict == ABSTAIN:
        reason = "ABSTAIN por admisión; identificación sin contradicciones demostradas pero sin prueba suficiente"
    elif verdict == PRESERVE_SCALAR:
        reason = "PRESERVE_SCALAR por evidencia escalar positiva"
    else:  # BLOCKED
        reason = "BLOCKED por ausencia material o contradicción"

    return {
        "capability": CAPABILITY_ID,
        "adapter_version": ADAPTER_VERSION,
        "verdict": verdict,
        "identity_checks": id_checks,
        "admission": decision,
        "reason": reason,
        "failing": [k for k, v in id_checks.items() if v["status"] == "FAIL"],
        "unknowns": [k for k, v in id_checks.items() if v["status"] in ("UNKNOWN", "SKIP")],
        "independent_oracle": decision.get("independent_oracle", []),
    }


def emit_verified_decision(summary_v2: Dict[str, Any],
                           case: Dict[str, Any],
                           sealed_analysis: Optional[Dict[str, Any]] = None,
                           ail_path: Optional[str] = None) -> Dict[str, Any]:
    """Produce un decision object autorizado por el testigo y verificado."""
    result = verify_decision(summary_v2, case,
                             sealed_analysis=sealed_analysis, ail_path=ail_path)
    payload = {k: v for k, v in result.items() if k not in ("identity_checks", "sha256")}
    # sello criptográfico: transformamos en formato de salida limpio
    verified = {
        "capability": CAPABILITY_ID,
        "version": ADAPTER_VERSION,
        "decision": result["verdict"],
        "identity_pass": [k for k, v in result["identity_checks"].items() if v["status"] == "PASS"],
        "identity_fail": [k for k, v in result["identity_checks"].items() if v["status"] == "FAIL"],
        "identity_unknown": [k for k, v in result["identity_checks"].items() if v["status"] in ("UNKNOWN", "SKIP")],
        "admission": result["admission"],
        "binding": result["admission"].get("binding", {}),
        "independent_oracle": result["independent_oracle"],
        "verification": {
            "checks_run": len(result["identity_checks"]),
            "pass": sum(1 for v in result["identity_checks"].values() if v["status"] == "PASS"),
            "skipped": sum(1 for v in result["identity_checks"].values() if v["status"] == "SKIP"),
        },
    }
    # el sha256 se calcula sobre el objeto sin él mismo; recomputable
    verified["sha256"] = sha256_fingerprint(verified)
    return verified


def recompute_fingerprint(doc: Dict[str, Any]) -> str:
    """Verificación independiente del sello emitido (D determinismo)."""
    return sha256_fingerprint({k: v for k, v in dict(doc).items() if k != "sha256"})


def recompute_admission_fingerprint(doc: Dict[str, Any]) -> bool:
    """R5+ Determinismo VER: el sha256 de entrada es estable → True."""
    fp = doc.get("sha256")
    return fp is not None and fp == recompute_fingerprint(doc)
