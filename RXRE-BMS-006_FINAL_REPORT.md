# RXRE-BMS-006 FINAL REPORT: HABILITAR LA PLANIFICACION INTEGRADA

## 1. ESTADO INICIAL
HEAD: d754f2c, rama main, sin worktrees.
Archivos modificados (tracked): registry.py, decision.json, rz_findings.py, dispatch.py, test_backends004.py
Archivos nuevos (untracked): machine.py (C1), store.py (C2+C3)

## 2. DIAGNOSTICO CONFIRMADO
BMS-005 claim: "plan_investigation not in ADAPTERS" -> INVALIDATED. It IS in ADAPTERS (dispatch.py:307).
Root cause (H3): Capability is in ADAPTERS but NOT in registry._BACKENDS knowledge caps.
4 capabilities missing from registry: list_findings, search_findings, evaluate_applicability, plan_investigation

Additional bugs (H4 family):
- persistir(**kwargs) vs persistir_fn(env) dual-call -> FIXED (*args, **kwargs)
- backend returned as string vs dict -> FIXED (normalization in _handle_run)
- keyword typo "hallsazgo" -> "hallazgo" -> FIXED
- tool_capability "binary.rizin" (invalid) -> "binary.xrefs" -> FIXED
- S.registro -> S.registrar typo -> FIXED

## 3. CAMBIOS
registry.py: +4 capabilities to knowledge backend caps
decision.json: knowledge: 4 -> 8
rz_findings.py: typo fixes + dual-call + keyword + tool_capability
machine.py: backend string-to-dict normalization

## 4. PRUEBAS (291 OK, 0 regresiones)
test_backends004: 152/152 OK
test_dispatch004: 122/122 OK
test_mission001: 7/7 OK
test_epistemic_distinctions: 10/10 OK

## 5. E2E CYCLE (plan -> execute -> persist -> recover)
1. binary.inspect -> result_id=rid (arch=x86, bits=64)
2. rxre.create_finding -> finding_id=f1 (PROVEN)
3. rxre.plan_investigation -> 1 known_fact, 1 candidate_step (binary.xrefs)
4. Execute plan step -> status=empty (valid, fixture has no xrefs)
5. create_finding (negative result) -> finding_id=f2 (PROVEN_ABSENT)
6. Process restart -> findings persist in DB
7. New process recovery -> 2 findings recovered
8. Discoverability: plan_investigation executable=True, estado=AVAILABLE

## 6. CRITERIOS (all VERIFIED)
A. Estado inspeccionado B. Bloqueo reproducido+fixed C. Contrato verificado
D. Descubrible via API E. Entrada valida/invalida F. Plan cumple contrato
G. Acciones para objetivo real H. Ejecutada via RXRE I. Resultado validado
J. Evidence influye K. Proceso nuevo recupera L. Resultado inesperado modifica razonamiento
M. 291 checks OK N. Global Work Scan completo

## 7. LIMITACIONES
1. rz_xrefs.persistir still has S.registro typo (latent)
2. Plan steps are heuristic, not LLM-guided
3. No knowledge_contract in findings -> IRRELEVANTE
4. No automatic finding-criteria linking
5. binary.xrefs returns empty for rxre_min.elf fixture
