#!/usr/bin/env python3
"""ORQUESTADOR DE MISIÓN COMPLETA — PREGUNTA -> EVIDENCIA -> HIPOTESIS -> PLAN -> EJECUCION -> VALIDACION -> CONCLUSION.
Integra replay + analyze_dependencies + plan_reinvestigation + verify_reinvestigation.
No simula resultados; no eleva automáticamente a PROVEN."""
import sys, os, json
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))
from pathlib import Path
from rxre.core.replay import analyze_dependencies, plan_reinvestigation, verify_reinvestigation, replay_operacion

class Orchestrator:
    def __init__(self, op_id: str = "op_2939a40bc715d58f", evidence_path: str = None):
        self.op_id = op_id
        self.evidence_path = evidence_path or "audit/evidence/e2e_001.json"
        self.chain = []
        self.conclusion = None
        self.blocked = False
        self.block_reason = None

    def ask(self):
        self.chain.append({"stage": "PREGUNTA", "input": self.op_id, "status": "ok"})

    def evidence(self):
        ev = Path(self.evidence_path)
        if ev.exists():
            meta = json.loads(ev.read_text())
            self.chain.append({"stage": "EVIDENCIA", "path": str(ev), "hash_prefix": meta.get("artefacto_hash_sha256","")[:16], "status": "ok"})
        else:
            self.blocked = True
            self.block_reason = f"evidencia ausente: {self.evidence_path}"
            self.chain.append({"stage": "EVIDENCIA", "path": str(ev), "status": "blocked", "reason": self.block_reason})

    def hypothesis(self):
        if self.blocked:
            self.chain.append({"stage": "HIPOTESIS", "status": "skipped", "reason": self.block_reason})
            return
        dep = analyze_dependencies(self.op_id, self.evidence_path)
        self.chain.append({"stage": "HIPOTESIS", "classification": dep["classification"],
                           "dependencies": dep.get("dependencies", []), "status": "ok"})
        self.dep_result = dep

    def plan(self):
        if self.blocked:
            self.chain.append({"stage": "PLAN", "status": "skipped", "reason": self.block_reason})
            return
        plan = plan_reinvestigation(self.op_id, self.evidence_path)
        self.chain.append({"stage": "PLAN", "action": plan["plan"][0].get("action") if plan.get("plan") else None,
                           "limitacion": plan.get("limitacion"), "status": "ok"})
        self.plan_result = plan

    def execution(self, dry_run: bool = False):
        if self.blocked:
            self.chain.append({"stage": "EJECUCION", "status": "skipped", "reason": self.block_reason})
            return
        action = self.plan_result.get("plan", [{}])[0].get("action") if self.plan_result else None
        if dry_run:
            self.chain.append({"stage": "EJECUCION", "dry_run": True, "action": action, "status": "ok"})
            self.execution_result = {"dry_run": True, "action": action, "op_id": self.op_id}
            return
        # Ejecución real solo si VALID (conservar) o STALE (reevaluar) y no hay bloque
        if action in ("conservar", "reevaluar"):
            replay = replay_operacion(self.op_id)
            self.execution_result = replay
            self.chain.append({"stage": "EJECUCION", "status": replay.get("status"), "reproducible": replay.get("reproducible"), "op_id": self.op_id})
            if replay.get("status") == "replayed" and replay.get("reproducible"):
                pass
            else:
                self.blocked = True
                self.block_reason = f"replay falló: {replay.get('status')}"
        else:
            self.blocked = True
            self.block_reason = "acción no ejecutable: " + str(action)
            self.execution_result = {"status": "blocked", "reason": self.block_reason}
            self.chain.append({"stage": "EJECUCION", "status": "blocked", "reason": self.block_reason})

    def validation(self):
        if self.blocked:
            self.chain.append({"stage": "VALIDACION", "status": "blocked", "reason": self.block_reason})
            self.conclusion = {"verification_status": "UNRESOLVED", "motivo": self.block_reason, "notas": "bloqueo en ejecución"}
            return
        if not hasattr(self, "execution_result"):
            self.execution_result = {}
        ver = verify_reinvestigation(self.plan_result, self.execution_result)
        self.chain.append({"stage": "VALIDACION", "status": ver.get("verification_status"),
                           "motivo": ver.get("motivo"), "reducida_incertidumbre": ver.get("reducida_incertidumbre")})
        self.conclusion = ver

    def finalize(self):
        if self.conclusion is None:
            self.conclusion = {"verification_status": "UNRESOLVED", "motivo": "flujo incompleto", "limitacion": "falta ejecutar validación"}
        self.chain.append({"stage": "CONCLUSION", "status": self.conclusion.get("verification_status"),
                           "motivo": self.conclusion.get("motivo"),
                           "notas": "No se eleva automáticamente a PROVEN; causalidad dinámica NO confirmada"})
        return self.conclusion

    def run(self, dry_run: bool = False):
        self.ask()
        self.evidence()
        self.hypothesis()
        self.plan()
        self.execution(dry_run=dry_run)
        self.validation()
        self.finalize()
        return {
            "mission_id": self.op_id,
            "chain": self.chain,
            "conclusion": self.conclusion,
            "blocked": self.blocked,
            "block_reason": self.block_reason,
            "dry_run": dry_run,
            "nota": "Flujo completo ejecutado sin modificar DB ni evidencia canónica."
        }
