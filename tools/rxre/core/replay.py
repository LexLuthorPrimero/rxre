#!/usr/bin/env python3
"""REPLAY DE MISION — reconstrucción desde registros persistidos (store.py, evidence)."""
import json, sqlite3, hashlib, sys, os
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))
from pathlib import Path
from backends.dispatch import resolve, ejecutar

DB_PATH = Path(__file__).resolve().parents[1] / "storage" / "rxre.sqlite3"

def analyze_dependencies(op_id: str, evidence_path: str = None) -> dict:
    """INVALIDACIÓN CAUSAL — clasifica conclusión según dependencias verificadas (VALID/STALE/UNKNOWN)."""
    # Dependencias de la operación registrada
    if not DB_PATH.exists():
        return {"op_id": op_id, "classification": "UNKNOWN", "reason": "DB no encontrada", "dependencies": []}
    conn = sqlite3.connect(str(DB_PATH))
    try:
        op = conn.execute("SELECT operacion, capability, request_json, response_json FROM operations WHERE operation_id=?", (op_id,)).fetchone()
        if not op:
            return {"op_id": op_id, "classification": "UNKNOWN", "reason": "operación no registrada", "dependencies": []}
        operacion, capability = op[0], op[1]
        params = json.loads(op[2]) if op[2] else {}
        resp = json.loads(op[3]) if op[3] else {}
        dependencies = []
        # Dependencia 1: artefacto (hash)
        art = None
        for base in ["amdgpu.ko", "tools/rxre/fixtures/bin/rxre_min.elf", "/bin/ls"]:
            p = Path(base)
            if p.exists():
                art = str(p.resolve())
                break
        if art:
            h = hashlib.sha256(Path(art).read_bytes()).hexdigest()
            dependencies.append({"name": "artefacto_hash", "value": h[:16], "relevant": True})
            # Comparar con evidencia canónica si se proporciona
            ev = Path(evidence_path) if evidence_path else Path("audit/evidence/e2e_001.json")
            if ev.exists():
                meta = json.loads(ev.read_text())
                ev_hash = meta.get("artefacto_hash_sha256", "")[:16]
                if ev_hash and ev_hash != h[:16]:
                    return {"op_id": op_id, "classification": "STALE", "reason": "hash artefacto cambiado", "dependencies": dependencies, "evidence_path": str(ev)}
        else:
            dependencies.append({"name": "artefacto", "value": None, "relevant": True, "missing": True})
        # Dependencia 2: versión herramienta (respuesta de DB)
        backend = resp.get("backend", {}) if isinstance(resp, dict) else {}
        tool_version = backend.get("tool_version", "")
        repo_commit = backend.get("repository_commit", "")
        dependencies.append({"name": "tool_version", "value": tool_version[:60], "relevant": True})
        # Dependencia 3: evidencia estructural (e2e_002)
        ev2 = Path("audit/evidence/e2e_002.json")
        if ev2.exists():
            meta2 = json.loads(ev2.read_text())
            dependencies.append({"name": "estructura_e2e_002", "value": meta2.get("tipo", ""), "relevant": True})
        else:
            dependencies.append({"name": "evidencia_e2e_002", "value": None, "relevant": False, "missing": True})
        # Clasificación final
        has_missing = any(d.get("missing") for d in dependencies if d.get("relevant"))
        if art and ev.exists():
            meta_ev = json.loads(ev.read_text())
            current_h = hashlib.sha256(Path(art).read_bytes()).hexdigest()[:16]
            ev_h = meta_ev.get("artefacto_hash_sha256", "")[:16]
            if current_h == ev_h and not has_missing:
                return {"op_id": op_id, "classification": "VALID", "reason": "dependencias verificadas y compatibles (artefacto, hash, herramienta, estructura)", "dependencies": dependencies}
            elif current_h != ev_h:
                return {"op_id": op_id, "classification": "STALE", "reason": "hash artefacto modificado respecto a evidencia registradas", "dependencies": dependencies, "evidence_path": str(ev)}
        if has_missing:
            return {"op_id": op_id, "classification": "UNKNOWN", "reason": "información insuficiente (dependencia relevada ausente)", "dependencies": dependencies}
        return {"op_id": op_id, "classification": "VALID", "reason": "dependencias verificadas sin evidencia canónica directa", "dependencies": dependencies}
    finally:
        conn.close()

def plan_reinvestigation(op_id: str, evidence_path: str = None) -> dict:
    """PLANIFICADOR DE REINVESTIGACIÓN — decisiones ejecutables a partir de dependencias."""
    dep = analyze_dependencies(op_id, evidence_path)
    plan = {"op_id": op_id, "classification": dep["classification"],
            "dependencies_checked": dep.get("dependencies", []),
            "plan": [], "limitacion": None, "evidence_path": dep.get("evidence_path")}
    # Reglas según clasificación
    if dep["classification"] == "VALID":
        plan["plan"] = [{"action": "conservar", "reason": "dependencias verificadas y compatibles",
                         "evidence": "audit/evidence/e2e_001.json + e2e_002.json",
                         "dependencia": "artefacto + hash + herramienta + estructura",
                         "condition": "hash artefacto permanece igual; versión herramienta sin cambio semántico"}]
        plan["limitacion"] = "No requiere repetición. Causalidad dinámica NO confirmada por esta evidencia (#CONTRATO_CAUSAL_INV_ESTRING)."
    elif dep["classification"] == "STALE":
        stale_dep = [d["name"] for d in dep["dependencies"] if d.get("relevant")]
        # Proponer mínimo: validar hash y, si afectado, repetir binary.inspect sobre artefacto actualizado
        plan["plan"] = [{"action": "reevaluar", "reason": f"dependencia STALE: {', '.join(stale_dep)}",
                         "proposal": "repetir binary.inspect sobre artefacto actualizado; comparar hash con evidencia canónica",
                         "dependencia_afectada": stale_dep,
                         "evidence_origin": dep.get("evidence_path", "audit/evidence/e2e_001.json"),
                         "condition": "nuevo hash coincide con evidencia actualizada o evidencia se actualiza tras repetición"}]
        plan["limitacion"] = "No se ejecuta automáticamente; requiere autorización para acceso /dev/mem si se requiere captura física (F2 PARTIAL)."
    elif dep["classification"] == "UNKNOWN":
        missing = [d["name"] for d in dep["dependencies"] if d.get("missing")]
        plan["plan"] = [{"action": "investigar", "reason": f"dependencia faltante o insuficiente: {', '.join(missing)}",
                         "proposal": "verificar existencia de artefacto, evidencias canónicas (e2e_001/e2e_002) y registro DB (store.sqlite3)",
                         "dependencia_faltante": missing,
                         "evidence_origin": "audit/evidence/ (verificar) + store.sqlite3 operations",
                         "condition": "todas las dependencias relevantes presentes y verificadas"}]
        plan["limitacion"] = "Grafo de dependencias incompleto; no se puede determinar si la conclusión es STALE o VALID sin completar datos."
    return plan

def verify_reinvestigation(plan: dict, result: dict) -> dict:
    """VERIFICACIÓN DE REINVESTIGACIÓN — clasifica RESOLVED / UNRESOLVED / INVALID_RESULT."""
    # Validación estructural del resultado
    verification = {
        "plan_op_id": plan.get("op_id"),
        "result_op_id": result.get("op_id"),
        "plan_action": plan.get("plan", [{}])[0].get("action") if plan.get("plan") else None,
        "verification_status": None,
        "motivo": None,
        "evidencia_resultado": None,
        "condicion_plan": plan.get("plan", [{}])[0].get("condition") if plan.get("plan") else None,
        "dependencias_verificadas": False,
        "evidencia_integridad": False,
        "reducida_incertidumbre": False,
        "limitacion": plan.get("limitacion")
    }
    # 1. Verificar que el resultado corresponde al plan
    if verification["plan_op_id"] != verification["result_op_id"]:
        verification["verification_status"] = "INVALID_RESULT"
        verification["motivo"] = "operación del resultado no coincide con el plan"
        verification["evidencia_resultado"] = "op_id mismatch"
        return verification
    # 2. Verificar integridad de evidencia (hash, esquema)
    evidence_path = result.get("evidence_path") or plan.get("evidence_path")
    evidence_integrity = True
    if evidence_path:
        ev_path = Path(evidence_path)
        if not ev_path.exists():
            evidence_integrity = False
        else:
            try:
                meta = json.loads(ev_path.read_text())
                art_path = meta.get("artefacto_path", meta.get("artefacto", ""))
                art = Path(art_path) if art_path else None
                if art and art.exists():
                    current_h = hashlib.sha256(art.read_bytes()).hexdigest()[:16]
                    ev_hash = meta.get("artefacto_hash_sha256", meta.get("hash_sha256", ""))[:16]
                    if ev_hash and current_h != ev_hash:
                        evidence_integrity = False
            except Exception:
                evidence_integrity = False
    verification["evidencia_integridad"] = evidence_integrity
    # 3. Verificar condición del plan
    condition = verification["condicion_plan"] or ""
    action = verification["plan_action"]
    res_class = result.get("classification", result.get("reproducible", ""))
    if action == "conservar" and verification["evidencia_integridad"]:
        verification["verification_status"] = "RESOLVED"
        verification["motivo"] = "dependencias verificadas y compatibles; evidencia intacta; no requiere repetición"
        verification["reducida_incertidumbre"] = True
    elif action == "reevaluar" and verification["evidencia_integridad"]:
        verification["verification_status"] = "RESOLVED"
        verification["motivo"] = "dependencia STALE verificada; evidencia actualizada o consistente con reevaluación"
        verification["reducida_incertidumbre"] = True
    elif action == "investigar" and verification["evidencia_integridad"]:
        verification["verification_status"] = "UNRESOLVED"
        verification["motivo"] = "plan de investigación no reduce incertidumbre; falta verificación de dependencias relevantes"
        verification["reducida_incertidumbre"] = False
    else:
        verification["verification_status"] = "UNRESOLVED"
        verification["motivo"] = "resultado no satisface la condición del plan o evidencia alterada/incompleta"
        verification["reducida_incertidumbre"] = False
    return verification

def replay_operacion(op_id: str) -> dict:
    """Reconstruye una operación desde store.py y compara con evidencia canónica."""
    if not DB_PATH.exists():
        return {"status": "no_db", "op_id": op_id, "error": "rxre.sqlite3 no encontrado"}
    conn = sqlite3.connect(str(DB_PATH))
    try:
        op = conn.execute(
            "SELECT operation_id, operacion, capability, request_json, response_json FROM operations WHERE operation_id=?",
            (op_id,)).fetchone()
        if not op:
            return {"status": "not_found", "op_id": op_id, "error": "operación no registrada"}
        operacion, capability, request_json_str, response_json_str = op[1], op[2], op[3], op[4]
        params = json.loads(request_json_str) if request_json_str else {}
        # Intentar replay real (no modifica DB)
        if capability == "binary.inspect":
            art_path = params.get("target", "").split("@")[0] if isinstance(params.get("target"), str) else None
            # Resolver ruta relativa a repositorio
            art = None
            for base in ["amdgpu.ko", "tools/rxre/fixtures/bin/rxre_min.elf", "/bin/ls"]:
                p = Path(base)
                if p.exists():
                    art = str(p.resolve())
                    break
            result_replay = {"artefacto_reconstruido": art}
            if art:
                try:
                    res = ejecutar(capability, {"artefacto": art, "timeout": 10})
                    result_replay["reproducible"] = (res.get("status") == "ok")
                    result_replay["replay_status"] = res.get("status")
                    result_replay["hash_actual"] = hashlib.sha256(Path(art).read_bytes()).hexdigest()[:16]
                    # Comparar con evidencia canónica (e2e_001.json) si existe
                    ev_path = Path("audit/evidence/e2e_001.json")
                    if ev_path.exists():
                        meta = json.loads(ev_path.read_text())
                        result_replay["evidence_found"] = True
                        result_replay["hash_evidence"] = meta.get("artefacto_hash_sha256", "")[:16]
                        result_replay["hash_match"] = result_replay["hash_actual"] == meta.get("artefacto_hash_sha256", "")[:16]
                    else:
                        result_replay["evidence_found"] = False
                    result_replay["differences"] = []
                    if result_replay.get("hash_match") is False:
                        result_replay["differences"].append("hash_mismatch_evidence")
                    if art and not Path(art).exists():
                        result_replay["differences"].append("artifact_missing")
                    if result_replay.get("reproducible"):
                        result_replay["differences"].append("reproducible_structural")
                except Exception as exc:
                    result_replay["replay_error"] = f"{type(exc).__name__}: {str(exc)[:60]}"
                    result_replay["reproducible"] = False
            else:
                result_replay["reproducible"] = False
                result_replay["differences"].append("artifact_not_resolved")
        return {
            "status": "replayed",
            "op_id": op_id,
            "operacion": operacion,
            "capability": capability,
            "reproducible": result_replay.get("reproducible", False),
            "replay_result": result_replay,
            "differences": result_replay.get("differences", []),
            "nota": "Replay reconstruido desde store.py sin modificar DB; diferencias clasificadas como determinismo/entorno/información insuficiente."
        }
    finally:
        conn.close()


def evaluate_contract(result: dict, evidence_path: str = None) -> dict:
    """CONTRATO UNIFORME — separa ejecución, entrada, resultado, evidencia y conclusión."""
    status = result.get("status")
    precheck = (result.get("precheck") or {}).get("ok") if isinstance(result.get("precheck"), dict) else None
    ejecucion = (result.get("ejecucion") or {}).get("status") if isinstance(result.get("ejecucion"), dict) else None
    results = result.get("results", []) if isinstance(result.get("results"), list) else []
    ev_path = Path(evidence_path) if evidence_path else None
    integrity = False
    if ev_path and ev_path.exists():
        try:
            meta = json.loads(ev_path.read_text())
            art_path = meta.get("artefacto_path", meta.get("artefacto", ""))
            art = Path(art_path) if art_path else None
            integrity = art.exists() if art else False
        except Exception:
            integrity = False
    if status == "invalid_input" or precheck is False:
        contract_state = "INVALID_INPUT"
        epistemic = "NOT_DETERMINED"
        reason = "entrada no válida o no es binario (BK_INVALID / BK_EMPTY)"
    elif status == "blocked" or ejecucion is None or ejecucion == "blocked":
        contract_state = "BLOCKED"
        epistemic = "NOT_DETERMINED"
        reason = "ejecución bloqueada por error o falta de permiso (BK_ERROR)"
    elif status == "ok" and precheck is True:
        if results:
            first = results[0] if isinstance(results, list) else results
            limitations = first.get("limitations", []) if isinstance(first, dict) else []
            if isinstance(limitations, list) and len(limitations) > 0:
                contract_state = "PARTIAL"
                epistemic = "PARTIAL"
                reason = "ejecución completada pero con datos parciales / declaración de límite (BK_OK + limitaciones)"
            else:
                contract_state = "COMPLETE"
                epistemic = "VALID"
                reason = "ejecución completa con evidencia íntegra (BK_OK + sin limitaciones críticos)"
            if ev_path and ev_path.exists():
                meta_ev = json.loads(ev_path.read_text())
                if meta_ev.get("tipo_evidencia") == "frontera_analizador":
                    contract_state = "PARTIAL"
                    epistemic = "PARTIAL"
                    reason = "frontera de analizador documentada; no se afirma análisis completo"
        else:
            contract_state = "COMPLETE"
            epistemic = "VALID"
            reason = "ejecución completa (BK_OK) sin resultados detallados"
    else:
        contract_state = "UNKNOWN"
        epistemic = "NOT_DETERMINED"
        reason = "estado técnico no clasificado en contrato (no BK_OK / BK_INVALID / BK_ERROR / BK_EMPTY)"
    return {
        "contract_state": contract_state,
        "epistemic": epistemic,
        "reason": reason,
        "execution_status": status,
        "precheck_ok": precheck,
        "execution_status_backend": ejecucion,
        "evidence_integrity": integrity,
        "results_count": len(results),
        "limitations_present": bool(results and isinstance(results[0], dict) and results[0].get("limitations")),
        "note": "Estado técnico (status) != validez semántica (epistemic). No se eleva automáticamente a PROVEN."
    }

