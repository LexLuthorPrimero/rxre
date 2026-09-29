# R1-5 — MAPA DOCUMENTAL (estado de la documentación A → R-1)

> **Tarea R-1.5** — FASE R-1 DOCUMENTATION RECONCILIATION & MASTER CONSOLIDATION — 2026-09-22 — SOLO DOCUMENTAL
> Estado de cada documento, versión, estado, dependencias, contradicciones conocidas y resoluciones.
>
> **Reconciliación 2026-09-24:** este mapa conserva el estado histórico; los claims GFX8
> actuales son `PARTIALLY_RECONCILED / CATALOG ONLY`, no verificaciones runtime.

---

## 1. Documentos maestros

| Documento | Versión | Estado | Depende de | Contradicciones conocidas (resueltas en R-1) |
|---|---|---|---|---|
| `MASTER-PLAN.md` | reconciliación 2026-09-24 | DOCUMENTAL | nada | FASE M: claims GFX8 `CATALOG ONLY`; no runtime |
| `MASTER-RESEARCH-STATUS.md` | reconciliación 2026-09-24 | RECONCILIADO (D6) | MASTER-PLAN | snapshots pre-D6 conservados; claims GFX8 source-level |
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
| `UNVERIFIED-CLAIMS.md` | ? | **PARTIALLY_RECONCILED** | Claim de soporte GFX8: catálogo externo documentado, runtime/ASIC `UNKNOWN` |

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
| `FASE-D-ETAPA-3-PLAN.md` (v1.5) | v1.5 | DISEÑADA, NO EJECUTADA | 12 slots requieren mapa eventos VI | catálogo source-level no habilita ejecución; NO AUTORIZADA |
| `FASE-D-ETAPA-3-PRECHECK.md` | ? | COMPLETADA | — | — |
| `FASE-D-ETAPA-3-EVENTS.md` | ? | COMPLETADA | GRBM=2/SQ=4 `CATALOG ONLY`; primera escritura bloqueada | ejecución NO AUTORIZADA |
| `FASE-D-GFX8-EVENT-ID-AUDIT.md` | ? | COMPLETADA + §14 adenda (R-1.2) | Resultado B «no verificable con locales» | adenda §14 Resultado B — Revisión post R-0 |

## 6. FASE R-0 — EXTERNAL KNOWLEDGE (`FASE-R0-EXTERNAL-KNOWLEDGE/`)

| Documento | Versión | Estado |
|---|---|---|
| `R0-1-GFX8-EVENT-IDS.md` + reference | ? | **PARTIALLY_RECONCILED**; 2304 filas de catálogo, no eventos validados |
| `R0-2-POWERPLAY-MCLK-SMU7.md` | ? | COMPLETADA |
| `R0-3-MESA-WORKAROUNDS-POLARIS12.md` | ? | COMPLETADA |
| `R0-4-ARCHITECTURE-LEXA-POLARIS12.md` | ? | COMPLETADA |
| `R0-5-BENCHMARKS-EXTERNOS-RX550.md` | ? | COMPLETADA |
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
