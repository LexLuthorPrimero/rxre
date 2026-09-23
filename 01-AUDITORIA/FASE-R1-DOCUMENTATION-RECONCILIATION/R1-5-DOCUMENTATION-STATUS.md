# R1-5 — MAPA DOCUMENTAL (estado de la documentación A → R-1)

> **Tarea R-1.5** — FASE R-1 DOCUMENTATION RECONCILIATION & MASTER CONSOLIDATION — 2026-09-22 — SOLO DOCUMENTAL
> Estado de cada documento, versión, estado, dependencias, contradicciones conocidas y resoluciones.

---

## 1. Documentos maestros

| Documento | Versión | Estado | Depende de | Contradicciones conocidas (resueltas en R-1) |
|---|---|---|---|---|
| `MASTER-PLAN.md` | v? (§A-§Q + Capa Transversal) | ACTUALIZADO (recibe §FASE R-1 en R-1.13) | nada | §FASE M «GRBM=2 BLOQUEADO» → anulado por R-0.1/R-1.1 (pendiente de reflejar en R-1.13) |
| `MASTER-RESEARCH-STATUS.md` | v2.5 | RECONCILIADO (R-1.4) | MASTER-PLAN | Conclusión B antigua de FASE D → adenda en PRÓXIMA ACCIÓN INMEDIATA; nota ‹GRBM BLOQUEADO› → VERIFICADO doc. |
| `experiments_proposed.md` | ? | ? | ? | revisado |

## 2. FASE A — Discriminación (`fase-a-discriminacion-*`)

| Documento | Versión | Estado | Notas |
|---|---|---|---|
| `RESULTADOS-FASE-A.md`, `INVALIDACION-corridas-04-09.md` | ? | COMPLETADA | régimen 17/09 **[NO REPRODUCIBLE]** → no especificación |

## 3. FASE B — Cap-probe (`fase-b-cap-probe-*`) y POLARIS12-MAP

| Documento | Versión | Estado | Notas |
|---|---|---|---|
| `RESULTADOS-FASE-B.md`, `EP08-*` | ? | COMPLETADA | cap 25 W no liga SCLK; 1071 MHz libre |
| `POLARIS12-MAP/*` | ? | COMPLETADA | subsistemas A–AJ |
| `UNVERIFIED-CLAIMS.md` | ? | COMPLETADA | «GPUPerfAPI soporta GFX8» NO VERIFICADO → **RESUELTO[VERIFICADO] por R-0.1** (GPUPerfAPI v3.11.1 SÍ soporta GFX8) |

## 4. EP-05 / EP-06 / M1 / AUDIT-001 / SUPERPOSITION-DISSECTION

| Documento | Versión | Estado |
|---|---|---|
| `ep05-mesa-custom-20260919-212249/` | ? | COMPLETADA |
| `ep06-soak-cap-20260919-205645/` | ? | COMPLETADA |
| `M1-cap-35-30/` | ? | COMPLETADA |
| `AUDIT-001/` | ? | COMPLETADA |
| `R-14-SUPERPOSITION-DISSECTION/` | ? | COMPLETADA |
| `EXPLORATORIO-GravityMark/` | ? | COMPLETADA |
| `WORKLOAD-SINTETICO/` (E-03 corregida, ES-01) | ? | COMPLETADA/CONGELADO |

## 5. FASE D — Performance Counters (`FASE-D-COUNTERS-AUDIT/`)

| Documento | Versión | Estado | Contradicción | Resolución R-1 |
|---|---|---|---|---|
| `FASE-D-COUNTERS-AUDIT.md` (Etapa 1) | ? | COMPLETADA | — | — |
| `FASE-D-ETAPA-2-PLAN.md` | ? | COMPLETADA | — | — |
| `FASE-D-ETAPA-2-RESULTADOS.md` | v? | CORREGIDO (R-1.3) | tabla radeontop §4 mezcla métodos; SPI «3306» ≠ 8408 | §12 Correcciones post-auditoría |
| `FASE-D-ETAPA-2-AUDIT.md` | ? | COMPLETADA | errores objetivos detectados | aplicado en R-1.3 |
| `FASE-D-ETAPA-3-PLAN.md` (v1.5) | v1.5 | DISEÑADA, NO EJECUTADA | 12 slots requieren mapa eventos VI | mapa obtenido en R-0; ejecución sigue NO AUTORIZADA |
| `FASE-D-ETAPA-3-PRECHECK.md` | ? | COMPLETADA | — | — |
| `FASE-D-ETAPA-3-EVENTS.md` | ? | COMPLETADA | §H primera escritura GRBM=2 BLOQUEADA; mayoría IDs NO VERIFICADO | §H pasa a «mapa verificado, ejecución NO autorizada» (R-1.2/R1-1) |
| `FASE-D-GFX8-EVENT-ID-AUDIT.md` | ? | COMPLETADA + §14 adenda (R-1.2) | Resultado B «no verificable con locales» | adenda §14 Resultado B — Revisión post R-0 |

## 6. FASE R-0 — EXTERNAL KNOWLEDGE (`FASE-R0-EXTERNAL-KNOWLEDGE/`)

| Documento | Versión | Estado |
|---|---|---|
| `R0-1-GFX8-EVENT-IDS.md` + `R0-1-GFX8-EVENT-ID-REFERENCE.txt` | ? | COMPLETADA (2304 contadores) |
| `R0-2-MCLK-POLARIS-MEMORY.md` | ? | COMPLETADA |
| `R0-3-MESA-GFX8-WORKAROUNDS.md` | ? | COMPLETADA |
| `R0-4-LEXA-POLARIS12-SPECS.md` | ? | COMPLETADA |
| `R0-5-RX550-EXTERNAL-BENCHMARKS.md` | ? | COMPLETADA |
| `R0-6-HERRAMIENTAS-HISTORICAS-GFX8.md` | ? | COMPLETADA |
| `FASE-R0-EXTERNAL-KNOWLEDGE-FINAL-REPORT.md` | ? | COMPLETADA |

## 7. FASE R-1 (`FASE-R1-DOCUMENTATION-RECONCILIATION/`)

| Documento | Estado |
|---|---|
| `R1-1-GFX8-EVENT-RECONCILIATION.md` | COMPLETADA |
| `R1-5-DOCUMENTATION-STATUS.md` (este) | COMPLETADA |
| `R1-6-EVIDENCE-STATE-MODEL.md` | COMPLETADA |
| `R1-7-CRITICAL-GAPS.md` | COMPLETADA |
| `R1-8-CROSS-CUTTING-AUDIT.md` | COMPLETADA |
| `R1-9-E-J-READINESS.md` | COMPLETADA |
| `R1-10-NON-AUTHORIZED-ACTIONS.md` | COMPLETADA |
| `FASE-R1-FINAL-REPORT.md` | COMPLETADA |

## 8. Roadmap futuro (PLANIFICADO, NO ejecutable)

FASE E–J (pendientes), K/Q (L,M,N,O,P,Q) planificadas en MASTER-PLAN §K; Capa Transversal KERNEL/DRIVER
documentada (read-only de investigación).

## 9. Glosario de estados de documento

IDENTICAL/IMPASSE → ver R1-6 (state model). Un documento en estado **CONTRADICTED** queda prohibido como fuente
de diseño experimental hasta reconciliación.

---

**Confirmación read-only:** mapa construido por lectura de la documentación; sin escrituras de sistema.