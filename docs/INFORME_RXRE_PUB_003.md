# INFORME RXRE-PUB-003 — RESOLUCION DISCREPANCIA Y PLAN
Estado: READY_FOR_PUBLICATION_AUTHORIZATION (candidata verificada) / BLOCKED (publicación real requiere autorización + reconciliación)
Fecha: 2026-10-18. Proyecto: /home/lucas/Escritorio/rxre.

## 1. DISCREPANCIA RESUELTA
- Remote main SHA: c682c4a4cf4e2c5c518a90f41e54107a7ecde6db (git ls-remote confirmado).
- git ls-tree -r --name-only c682c4a: 0 archivos rastreados.
- curl README.md (main): HTTP 200, 1815 B, sha256 abb25aec68a1f9c45067738c3264294993147aa6 (original básico).
- curl LICENSE (main): HTTP 200, 17984 B, sha256 edaef632cbb643e4e7a221717a6c441a4c1a7c918e6e4d56debc3d8739b233f6 (GPL v2, coincide con candidato).
- Candidata README.md: 6686 B, sha256 631956958771a784cc348cae419d32914325ddfd813b872ffd91b1564857a0af (actualizado: READY_NOT_PUBLISHED, contratos, evidencia, F2/C3, instalación PYTHONPATH=tools).
- Resolución: c682c4a es commit vacío (árbol vacío); README/Liz del remoto provienen de trabajo inicial no rastreado en ese SHA. Candidata debe preservar README actualizado + LICENSE + .gitignore actualizado + 27 archivos adicionales (core, tests, evidencia, docs).

## 2. CANDIDATA /tmp/rxre-candidate: 29 archivos verificados
- README.md, LICENSE, .gitignore, audit/evidence/e2e_001..e2e_010, core/replay.py/evidence_integrity.py/orchestrator.py, tests/ (11), docs/ (7: BASELINE_SPE_25, CONTRATO_CAUSAL_INV_ESTRING, CONTRATO_F2_W5_MINIMO, MATRIZ_F2_PRODUCTOR, INFORME_SPE_29, INFORME_PUBLICACION_RXRE, RECONCILIACION_LOCAL_REMOTO, PLAN_RECONCILIACION_SPE_28). Nota: INFORME_RXRE_PUB_001 debe incluirse o documentarse (verificar antes de push).
- Excluidos (verificado): rxre.sqlite3, .rxre/gpu0/*, INFORME_RECUPERACION_RXRE.md, KytyPS5-Source.
- DB intacta; repo histórico intacto; sin modificaciones al repo activo.

## 3. COINCIDENCIA / DIFERENCIA
- Remoto: 0 rastreados; README básico; LICENSE GPL v2.
- Candidata: 29 archivos; README actualizado; LICENSE igual; .gitignore actualizado; core corregido (VALID_EPISTEMIC); evidencia completa; docs completos.
- No hay conflicto de archivo (remoto vacío); solo divergencia de historia (merge-base vacío; MANUAL_RECONCILIATION_REQUIRED; MERGE_PLAN_READY).

## 4. BLOQUEOS Y AUTORIZACIÓN
- MANUAL_RECONCILIATION_REQUIRED (docs/RECONCILIACION_LOCAL_REMOTO.md, docs/PLAN_RECONCILIATION_SPE_28.md): requiere autorización para git merge --allow-unrelated-histories + verificación git ls-tree -r --name-only del merge + confirmación README actualizado aceptable.
- READY_NOT_PUBLISHED (docs/INFORME_PUBLICACION_RXRE.md): no se hizo push; DB intacta; evidencia completa.
- BLOCKED para publicación real: falta autorización explícita; no se ejecuta push.
- F2 (/dev/mem) pendiente autorización (docs/BASELINE_SPE_25.md, CONTRATO_F2_W5_MINIMO.md); C3 (PROVEN_ABSENT) pendiente universo (docs/CONTRATO_CAUSAL_INV_ESTRING.md); PROVEN nunca automático (docs/BASELINE_SPE_25.md, INFORME_SPE_29.md).
- Madness Project Nexus Classic.swf descartado (no referenciado en README actualizado ni contrato; no usado como requisito ni bloqueo).

## 5. SIGUIENTE ACCIÓN (autorización requerida)
Confirmar autorización para reconciliación (MERGE_PLAN_READY) con verificación exacta del árbol resultante y actualización de .gitignore si falta audit/claims.csv / scripts/f2_producer_safe.py. Sin autorización: candidato (/tmp/rxre-candidate/) permanece verificado; proyecto completo; sin nueva cadena funcional iniciada.
