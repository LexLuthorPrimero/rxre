# DOCUMENTATION-ROUTER — Índice de decisión documental

> **Este fichero es un índice de decisión, no una enciclopedia.** No contiene conocimiento:
> solo dice **qué fichero abrir primero** para cada `TOPIC`, con qué `TEMPORALITY` y
> `HOST_SCOPE`, y cuándo dejar de escalar.
>
> **Regla de uso:** clasifica la consulta → abre el `PRIMARY` → responde. Si el `PRIMARY`
> no alcanza, entonces sí `SECONDARY` → `RAW` → `WEB`. Nunca al revés.
>
> **Vocabulario y justificación:** `01-AUDITORIA/DOCUMENTATION-ROUTER-DESIGN/ROUTING-SCHEMA.md`.
> **Diseño y riesgos:** `../DOCUMENTATION-ROUTER-DESIGN/DOCUMENTATION-ROUTER-DESIGN.md`.
> **Datos completos:** `DOCUMENTATION-INVENTORY-ROUTING.tsv` (1576 filas) y
> `../DOCUMENTATION-CENSUS/DOCUMENTATION-TOPICS.md`.

---

## 0. Las tres identidades de host

**Antes de responder nada, identifica contra qué host pregunta el usuario.**

| `HOST_SCOPE` | SO | kernel | Mesa | RX550 | Cómo se reconoce |
|---|---|---|---|---|---|
| `HOST-A` | Nobara 44 | `7.2.4` / `7.2.6` | 26.2.2 / 26.2.3 | `card1` | La investigación histórica. **1444 filas del inventario** |
| `HOST-B` | Nobara 43 | `6.18.2-…fc43` | 25.3.2 | `card2` | La captura del 2026-09-25T13:58Z. Documentos raíz y `FINAL-VALIDATION` |
| `HOST-C` | Nobara 44 | `7.1.3-…fc44` | 26.2.3 | `card1` | **El host vivo.** Medido el 2026-09-25T22:22Z |
| `UNKNOWN` | — | — | — | — | El documento no declara host. **1406 de 1576 filas** |
| `NOT-APPLICABLE` | — | — | — | — | Diseño, taxonomía o índice. Sin afirmación de hardware |

`HOST_SCOPE_BASIS` distingue `DECLARED` (26 filas: el texto nombra el host) de `INFERRED`
(1550: atribuido por procedencia). **Un `HOST-A INFERRED` es más débil que un `HOST-A DECLARED`.**

### Regla de temporalidad — precondición, no nota al pie

Si la consulta pide **estado actual** y el `PRIMARY` no es `CURRENT_NEW_DISK` con
`HOST_SCOPE=HOST-C`:

```
CURRENT_EVIDENCE=NOT_AVAILABLE
+ indicar qué evidencia HISTÓRICA existe, marcada como tal
+ NO presentar el histórico como actual
```

**Situación real:** solo **2** documentos tienen `HOST_SCOPE=HOST-C`
(`PATCH-SOURCES.md` §3 y `PATCH-REGISTRY-RECOVERED.md`). Los 7 `HOST-B DECLARED`
(`README.md`, `PROBLEM-STATUS-FINAL.md`, `INSTALL.md`, `CHANGELOG.md`,
`RELEASE-CANDIDATE.md`, `01-AUDITORIA/FINAL-VALIDATION/FINAL-VALIDATION-20260925T135831Z.md`, `PATCH-RECOVERY-REPORT.md`) describen
un host que **ya no es el vivo**. `STATUS=STALE` es un terminal de primer nivel.

---

## 1. Resolución en 6 pasos

```
1. QUERY      → 2. QUESTION_TYPE  → 3. TOPIC
             → 4. TEMPORALITY + HOST_SCOPE
             → 5. PRIMARY  → 6. SECONDARY / RAW / WEB  (solo si no alcanza)
```

| Escalón | Regla |
|---|---|
| `PRIMARY` → `SECONDARY` | No leer `SECONDARY` si el `PRIMARY` responde completamente |
| `SECONDARY` → `RAW` | No leer `RAW` si `PRIMARY` + `SECONDARY` bastan |
| `LOCAL` → `WEB` | No consultar web si la documentación local tiene evidencia suficiente |

**`WEB` procede** solo si: (a) la documentación local es insuficiente; (b) hace falta un
hecho externo (upstream, API, manual); (c) el usuario pide información externa actual;
(d) el local marca `UNKNOWN` y existe fuente externa apropiada. **El resultado web se marca
`EXTERNAL` y nunca se presenta como estado de este host.**

### Terminales

| Terminal | Significado | Regla |
|---|---|---|
| `ANSWERED` | Responde el `PRIMARY` | Fin |
| `ESCALATED` | Resuelto con `SECONDARY`/`RAW`/`WEB` | Declarar cuál y por qué |
| `UNKNOWN` | Evidencia insuficiente | **Nunca** → `PASS` |
| `NOT_AVAILABLE` | No existe fuente | **No crear** documentación para rellenarlo |
| `CONFLICT` | Fuentes incompatibles | **Devolver ambas.** No elegir |
| `STALE` | El documento es `CURRENT` pero de `HOST-B` | No sirve como estado actual |
| `REVIEW_REQUIRED` | El contenido contradice lo que el router asume | Escalar a revisión editorial |

---

## 2. Los 6 conflictos

**El router nunca resuelve uno. Devuelve las dos fuentes.**

| `CONFLICT_ID` | Asunto | Fuentes | Precedencia declarada |
|---|---|---|---|
| `C1` | Tests C1: `24/24` vs `37/37` vs `44/44` | `C1-TECHNICAL-RECORD.md` · `DIAGRAMAS/12-MATRIZ-TRAZABILIDAD.md` · sidecar | **Sí** — `01-AUDITORIA/DOCUMENTARY-RECONCILIATION-2026-09-25.md:187-201` → **`CONFLICT_SOURCE`** |
| `C2` | Mesa: `26.2.2` vs `26.2.3` vs `25.3.2` | raíz · host vivo | **Parcial** — `DOCUMENTARY-RECONCILIATION-2026-09-25.md:225-227` → **`CONFLICT_SOURCE`** |
| `C3` | Kernel: `7.2.6` vs `7.2.4` vs `6.18.2` vs `7.1.3` | `P0-…GATE` · `knowledge.md` · `README.md` · `PATCH-SOURCES.md` | «No se funden» — `C1-TECHNICAL-RECORD.md:48` → **`CONFLICT_SOURCE`** |
| `C4` | `cardN`: `card1` vs `card2` | captura · host vivo · scripts históricos | **Sí**, como regla: *no son portables* — `README.md:15-16` → **`CONFLICT_SOURCE`** |
| `C5` | H12-4: implementado vs no ejecutado | `H12-1/README.md` · raíz | No — `DOCUMENTARY-RECONCILIATION-2026-09-25.md` → **`CONFLICT_SOURCE`** |
| `C6` | Btrfs: `CONFLICT`, y el host vivo es ext4 | `AGENTS.md` · `PROBLEM-STATUS-FINAL.md` · host vivo | No — `DOCUMENTARY-RECONCILIATION-2026-09-25.md` → **`CONFLICT_SOURCE`** |

### `CONFLICT_SOURCE` — el documento que hay que abrir para *observar* el conflicto

Declarar `CONFLICT` no basta: hay que poder **llegar** al documento que registra la precedencia.
Un `CONFLICT` sin `CONFLICT_SOURCE` routed obliga a recorrer el repositorio para encontrarlo.

**Rol añadido tras `RT-0003`**, donde el conflicto `C1` estaba declarado en `ESCALATION` pero su
observador no era alcanzable desde la fila del topic: el nombre aparecía abreviado y en otro
apartado, de modo que un agente que ya había respondido con el `PRIMARY` no tenía señal para
escalar. En RT-0003 el `PRIMARY` bastó para la pregunta de estado, pero el observador del
conflicto quedó sin leer.

| `CONFLICT_ID` | `CONFLICT_SOURCE` — léelo para ver la declaración de precedencia |
|---|---|
| `C1` | `01-AUDITORIA/DOCUMENTARY-RECONCILIATION-2026-09-25.md` §`C1_TESTS` (líneas 187-201) |
| `C2` | `01-AUDITORIA/DOCUMENTARY-RECONCILIATION-2026-09-25.md` §`MESA_*` (líneas 225-227) |
| `C3` | `01-AUDITORIA/FASE-R5-C1-TECHNICAL-DOCUMENTATION/C1-TECHNICAL-RECORD.md` (línea 48) |
| `C4` | `README.md` §Estado actual (líneas 15-16) |
| `C5` | `01-AUDITORIA/DOCUMENTARY-RECONCILIATION-2026-09-25.md` §`H12-4` |
| `C6` | `01-AUDITORIA/DOCUMENTARY-RECONCILIATION-2026-09-25.md` §`BTRFS` |

Una consulta sobre **recuento de tests, reconciliación o diferencias entre evidencias** de C1
va directamente al `CONFLICT_SOURCE` de `C1`. No necesita recorrer el topic, y no necesita leer
el resto de los documentos de C1.

---

## 3. Tabla de routing — 68 topics

`TEM`: `CUR`=CURRENT_NEW_DISK · `CUR-ST`=CURRENT_NEW_DISK_STALE_HOST · `HA`=HISTORICAL_OLD_DISK ·
`MX`=MIXED · `EXT`=EXTERNAL · `NA`=NOT-APPLICABLE.
`HOST`: `A` `B` `C` `?`(UNKNOWN) `n/a`. Sufijo `d`=DECLARED, `i`=INFERRED.

### D1 · `PROJECT_STATE`

| TOPIC | QTYPE | PRIMARY | TEM | HOST | SECONDARY | RAW | ESCALATION |
|---|---|---|---|---|---|---|---|
| `PROJECT_STATUS` | STATUS | `README.md` | CUR | B d | `PROBLEM-STATUS-FINAL.md` · `RELEASE-CANDIDATE.md` | — | `CONFLICT` si pide valor único |
| `PROBLEM_MATRIX` | STATUS | `PROBLEM-STATUS-FINAL.md` | CUR | B d | `PATCH-REGISTRY-FINAL.md` | — | `UNKNOWN` si el problema no figura |
| `RELEASE` | GITHUB | `RELEASE-CANDIDATE.md` | CUR | B d | `FINAL-RELEASE-REPORT.md` · `RELEASE-EXCLUSIONS.md` | — | `BLOCK` si pide publicar |
| `GITHUB` | GITHUB | `RELEASE-CANDIDATE.md` | CUR | B d | `FINAL-RELEASE-REPORT.md` | — | `NOT_AVAILABLE` (no hay remote) |
| `DECISIONS` | HISTORY | `01-AUDITORIA/DECISIONES-D1-D10.md` | MX | ? | `00-INDICE/decisions.md` | — | `UNKNOWN` |
| `ROADMAP` | STATUS | `00-INDICE/MASTER-PLAN.md` | MX | A d | `04-IMPLEMENTACION/IMPLEMENTATION-ROADMAP.md` | — | Ninguno |
| `DOCUMENTATION_MAP` | DOCUMENTATION | `00-INDICE/README.md` | MX | ? | `00-INDICE/DIAGRAMAS/README.md` | `../DOCUMENTATION-CENSUS/*` | `CONFLICT` (5 mecanismos) |
| `DIAGRAMS` | DOCUMENTATION | `00-INDICE/DIAGRAMAS/README.md` | MX | ? | `00-INDICE/DIAGRAMAS/10-NAVEGACION-DOCUMENTAL.md` | — | `STALE` (16/17 son DRAFT/CONFLICT) |
| `HISTORY` | HISTORY | `01-AUDITORIA/FASE-R2-PROJECT-DOCUMENTATION/R2-HISTORICAL-EXPERIMENT-INVENTORY.md` | HA | A i | `01-AUDITORIA/AUDIT-001/AUDIT-001.md` | backup externo | `HISTORICAL_OTHER_HOST` |
| `CHANGELOG` | DOCUMENTATION | `CHANGELOG.md` | CUR | B d | — | — | Ninguno |
| `PROJECT_OVERVIEW` | DOCUMENTATION | `README.md` | CUR | B d | `04-IMPLEMENTACION/FASE-N-ECOSYSTEM-ARCHITECTURE.md` | — | Ninguno |
| `IDEAS_REGISTRY` | DOCUMENTATION | `RESEARCH/polaris12xl/ideas/README.md` | CUR | B d | `RESEARCH/polaris12xl/ideas/IDEAS-BASE.tsv` | `RESEARCH/polaris12xl/ideas/FUENTE-IDEAS-ORIGINAL.txt` | `RESEARCH/polaris12xl/COMPANION-AUDIT-IDEAS.md` |

### D2 · `PATCH_AND_CORRECTION`

| TOPIC | QTYPE | PRIMARY | TEM | HOST | SECONDARY | RAW | ESCALATION |
|---|---|---|---|---|---|---|---|
| `PATCHES` | PATCH | `PATCH-REGISTRY-FINAL.md` | CUR | ? d | `01-AUDITORIA/PATCH-RECOVERY/PATCH-REGISTRY-RECOVERED.md` | `PATCH-SOURCES.md` | `NOT_AVAILABLE` si no figura |
| `ROLLBACK` | RECOVERY | `ROLLBACK.md` | CUR | ? d | `PATCH-REGISTRY-FINAL.md` | — | `REVIEW_REQUIRED` si pide restaurar backup |
| `INSTALLATION` | CONFIGURATION | `INSTALL.md` | CUR | B d | `TESTING.md` | — | `STALE` (versiones de HOST-B) |

### D3 · `HOST_IDENTITY`

| TOPIC | QTYPE | PRIMARY | TEM | HOST | SECONDARY | RAW | ESCALATION |
|---|---|---|---|---|---|---|---|
| `HOST_IDENTITY` | HOST_IDENTITY | `01-AUDITORIA/PATCH-RECOVERY/PATCH-SOURCES.md` §3 | CUR | **C d** | `01-AUDITORIA/PATCH-RECOVERY/PATCH-REGISTRY-RECOVERED.md` | `01-AUDITORIA/FINAL-VALIDATION/FINAL-VALIDATION-20260925T135831Z.json` → `CUR-ST` B | `STALE` si se cita `FINAL-VALIDATION` |
| `KERNEL` | HARDWARE | `02-ARQUITECTURA/knowledge.md` | MX | A d | `01-AUDITORIA/FASE-P0-EXPERIMENTAL-VALIDITY-GATE/P0-EXPERIMENTAL-VALIDITY-GATE-2026-09-24.md` | — | `CONFLICT` C3 |
| `FIRMWARE` | HARDWARE | `PATCH-REGISTRY-FINAL.md` | CUR | B i | `02-ARQUITECTURA/knowledge.md` | — | `CURRENT_EVIDENCE=NOT_AVAILABLE` |
| `BACKUP` | RECOVERY | `ROLLBACK.md` | CUR | ? d | `00-INDICE/REGISTRO-DE-MOVIMIENTOS.md` | backup externo | `HISTORICAL_OTHER_HOST` |
| `RESET` | RESULT | `PATCH-REGISTRY-FINAL.md` | CUR | B i | `PROBLEM-STATUS-FINAL.md` | `03-EXPERIMENTOS/M1-cap-35-30/runs/*/audit.json` | `NOT_REPRODUCED` |

### D4 · `GPU_ARCHITECTURE`

| TOPIC | QTYPE | PRIMARY | TEM | HOST | SECONDARY | RAW | ESCALATION |
|---|---|---|---|---|---|---|---|
| `RX550` | HARDWARE | `02-ARQUITECTURA/knowledge.md` | MX | A d | `02-ARQUITECTURA/POLARIS12-MAP/POLARIS12-MAP.md` | `PATCH-SOURCES.md` §3 | `CONFLICT` C4 |
| `GPU` | HARDWARE | `02-ARQUITECTURA/knowledge.md` | MX | A d | `02-ARQUITECTURA/POLARIS12-MAP/SOFTWARE-CAPABILITIES.md` | — | `UNKNOWN` |
| `POLARIS12` | HARDWARE | `02-ARQUITECTURA/POLARIS12-MAP/POLARIS12-MAP.md` | MX | A i | `05-FUENTES-EXTERNAS/FASE-R0-EXTERNAL-KNOWLEDGE/R0-4-ARCHITECTURE-LEXA-POLARIS12.md` | — | `WEB` para fact de siliconio |
| `GFX8` | HARDWARE | `03-EXPERIMENTOS/FASE-D-COUNTERS-AUDIT/FASE-D-GFX8-EVENT-ID-AUDIT.md` | HA | ? i | `05-FUENTES-EXTERNAS/FASE-R0-EXTERNAL-KNOWLEDGE/R0-1-GFX8-EVENT-IDS.md` | `FASE-D-COUNTERS-AUDIT/runs/` | `UNKNOWN` (GRBM=2/SQ=4 no validan ASIC) |
| `AMDGPU` | HARDWARE | `02-ARQUITECTURA/knowledge.md` | MX | A d | `02-ARQUITECTURA/POLARIS12-MAP/SOFTWARE-CAPABILITIES.md` | — | `CONFLICT` C3 |
| `DRM` | HARDWARE | `02-ARQUITECTURA/knowledge.md` | MX | A d | `PATCH-REGISTRY-FINAL.md` | — | `UNKNOWN` |
| `PCI` | HARDWARE | `03-EXPERIMENTOS/FASE-R4A-BANDWIDTH-REAL/EXP-F3-A-BANDWIDTH-REAL.md` | HA | ? i | `02-ARQUITECTURA/POLARIS12-MAP/HARDWARE-ROUTES.md` | — | `UNKNOWN` (ancho real) |
| `VRAM` | HARDWARE | `04-IMPLEMENTACION/FASE-G-MEMORY-VRAM-GTT-DESIGN.md` | MX | ? i | `EXP-F3-A-BANDWIDTH-REAL.md` | — | `UNKNOWN` (VRAM real) |
| `SMU` | HARDWARE | `01-AUDITORIA/AUDIT-001/ERRATA.md` §ERRATUM-002 | HA | A i | `01-AUDITORIA/AUDIT-001/METRICS-DEFINITIONS.md` | — | `RESOLVED` (etiquetado `W_SMU`) |

### D5 · `POWER_AND_CLOCKS`

| TOPIC | QTYPE | PRIMARY | TEM | HOST | SECONDARY | RAW | ESCALATION |
|---|---|---|---|---|---|---|---|
| `POWER_CAP` | POWER | `03-EXPERIMENTOS/M1-cap-35-30/RESULTADOS-M1.md` | HA | ? i | `03-EXPERIMENTOS/fase-b-cap-probe-20260919-122038/RESULTADOS-FASE-B.md` | `03-EXPERIMENTOS/M1-cap-35-30/runs/20260919-235939/` | `NOT_REPRODUCED` (E1/E3/E5) |
| `DPM` | CAUSALITY | `01-AUDITORIA/AUDIT-001/ERRATA.md` | HA | A i | `03-EXPERIMENTOS/fase-a-discriminacion-20260919-114241/RESULTADOS-FASE-A.md` | `03-EXPERIMENTOS/fase-a-discriminacion-20260919-114241/` | `UNRESOLVED` (causalidad) |
| `SCLK` | RESULT | `03-EXPERIMENTOS/fase-a-discriminacion-20260919-114241/RESULTADOS-FASE-A.md` | HA | ? i | `RESULTADOS-FASE-B.md` | `03-EXPERIMENTOS/fase-a-discriminacion-20260919-114241/` | `UNKNOWN` |
| `MCLK` | CAUSALITY | `05-FUENTES-EXTERNAS/FASE-R0-EXTERNAL-KNOWLEDGE/R0-2-POWERPLAY-MCLK-SMU7.md` | EXT | n/a | `03-EXPERIMENTOS/ep06-soak-cap-20260919-205645/RESULTADOS-EP06.md` | `03-EXPERIMENTOS/ep06-soak-cap-20260919-205645/` | `UNKNOWN` (atribución local) |
| `RUNTIME_PM` | STATUS | `01-AUDITORIA/FASE-P0-EXPERIMENTAL-VALIDITY-GATE/P0-EXPERIMENTAL-VALIDITY-GATE-2026-09-24.md` | HA | A d | `04-IMPLEMENTACION/rx550-torneo/README-FASE1.md` | `01-AUDITORIA/FASE-C1-RUNTIME-PREFLIGHT/C1-PREFLIGHT-20260925T061932Z-PRIV.json` | `CURRENT_EVIDENCE=NOT_AVAILABLE` |
| `GOVERNOR` | RESULT | `03-EXPERIMENTOS/FASE-R4B-THERMAL-TEST/TEST-TERMICO-READONLY.md` | HA | ? i | `RESULTADOS-TEST-TERMICO.md` · `RESULTADOS-MINITEST-7.3-B.md` | `03-EXPERIMENTOS/FASE-R4B-THERMAL-TEST/runs/` | `UNKNOWN` |

### D6 · `GRAPHICS_STACK`

| TOPIC | QTYPE | PRIMARY | TEM | HOST | SECONDARY | RAW | ESCALATION |
|---|---|---|---|---|---|---|---|
| `MESA` | STATUS | `PATCH-REGISTRY-FINAL.md` | CUR | B i | `05-FUENTES-EXTERNAS/FASE-R0-EXTERNAL-KNOWLEDGE/R0-3-MESA-WORKAROUNDS-POLARIS12.md` · `PATCH-REGISTRY-RECOVERED.md` `RX550-MP-01` | `PATCH-SOURCES.md` | `CONFLICT` C2 → **`CONFLICT_SOURCE`** `01-AUDITORIA/DOCUMENTARY-RECONCILIATION-2026-09-25.md` |
| `MESA` **estado operativo en HOST-C** *(sub-ruta)* | CONFIGURATION | `01-AUDITORIA/PATCH-RECOVERY/PATCH-SOURCES.md` §3 | CUR | **C d** | `PATCH-REGISTRY-FINAL.md` (estado documental) | — | `DRIVER_ABSENT` — ver §3bis |
| `RADV` | CONFIGURATION | `PATCH-REGISTRY-FINAL.md` | CUR | B i | `02-ARQUITECTURA/knowledge.md` | `01-AUDITORIA/FINAL-VALIDATION/FINAL-VALIDATION-20260925T135831Z.json` | `STALE` (sin `mesa-vulkan-drivers` en C) |
| `VULKAN` | HARDWARE | `01-AUDITORIA/FASE-H12-2-WSI-DOCUMENTATION/H12-2-XDG-SHELL-VULKAN-WSI-EVIDENCE.md` | HA | ? i | `04-IMPLEMENTACION/H12-1/README.md` | — | `NOT_AVAILABLE` si pide extensión |
| `OPENGL` | CONFIGURATION | `PATCH-REGISTRY-FINAL.md` | CUR | B i | `INSTALL.md` | `01-AUDITORIA/FINAL-VALIDATION/FINAL-VALIDATION-20260925T135831Z.json` | `CONFLICT` C4 |
| `WAYLAND` | CONFIGURATION | `PATCH-REGISTRY-FINAL.md` | CUR | B i | `H12-2-XDG-SHELL-VULKAN-WSI-EVIDENCE.md` | — | `UNRESOLVED` |
| `KWIN` | RESULT | `PATCH-REGISTRY-FINAL.md` | CUR | B i | `01-AUDITORIA/FINAL-VALIDATION/FINAL-VALIDATION-20260925T135831Z.md` §renderers | — | `UNRESOLVED` (separación Intel) |
| `XWAYLAND` | CONFIGURATION | `PATCH-REGISTRY-FINAL.md` | CUR | B i | `H12-2-…WSI-EVIDENCE.md` | — | `UNRESOLVED` |
| `INTEL_GPU` | HARDWARE | `02-ARQUITECTURA/knowledge.md` | MX | A d | `PATCH-REGISTRY-FINAL.md` | `PATCH-SOURCES.md` §3 | `CONFLICT` C4 |
| `WSI` | HARDWARE | `01-AUDITORIA/FASE-H12-2-WSI-DOCUMENTATION/H12-2-XDG-SHELL-VULKAN-WSI-EVIDENCE.md` | HA | ? i | `04-IMPLEMENTACION/H12-2/README.md` | — | `CONFLICT` C5 |

### D7 · `MEASUREMENT`

| TOPIC | QTYPE | PRIMARY | TEM | HOST | SECONDARY | RAW | ESCALATION |
|---|---|---|---|---|---|---|---|
| `COUNTERS` | HARDWARE | `03-EXPERIMENTOS/FASE-D-COUNTERS-AUDIT/FASE-D-GFX8-EVENT-ID-AUDIT.md` | HA | ? i | `R0-1-GFX8-EVENT-IDS.md` · `R1-1-GFX8-EVENT-RECONCILIATION.md` | `03-EXPERIMENTOS/FASE-D-COUNTERS-AUDIT/runs/etapa2/` | `UNKNOWN` |
| `TELEMETRY` | RESULT | `02-ARQUITECTURA/COUNTERS-ASIC-TELEMETRY-KNOWLEDGE-ADDENDUM-2026-09-24.md` | HA | A d | `03-EXPERIMENTOS/M1-cap-35-30/TELEMETRY-SCHEMA.md` | `telemetry.csv` por corrida | `UNKNOWN` |
| `FRAME` | RESULT | `03-EXPERIMENTOS/FASE-R4C-JITTER-OBSERVABILITY/EXP-F1-A-RESULTADOS.md` | HA | ? i | `PRECHECK-REPORT.md` · `README.md` (FASE R-4C) | `03-EXPERIMENTOS/FASE-R4C-JITTER-OBSERVABILITY/results/metrics/` | `UNKNOWN` |
| `R4B` | RESULT | `03-EXPERIMENTOS/FASE-R4B-GOVERNOR/EXP-F4-A-RESULTADOS-v2.3.md` | HA | ? i | `00-INDICE/MASTER-RESEARCH-STATUS.md` §Addenda D6 | `03-EXPERIMENTOS/FASE-R4B-GOVERNOR/results/v23/` | `INCONCLUSIVE` (no `SUPPORTED`) |
| `R4C` | VALIDITY | `03-EXPERIMENTOS/FASE-R4C-JITTER-OBSERVABILITY/EXP-F1-A-RESULTADOS.md` | HA | ? i | `03-EXPERIMENTOS/FASE-R4C-JITTER-OBSERVABILITY/README.md` | `03-EXPERIMENTOS/FASE-R4C-JITTER-OBSERVABILITY/results/` | `CURRENT_EVIDENCE=NOT_AVAILABLE` |
| `M1` | RESULT | `03-EXPERIMENTOS/M1-cap-35-30/RESULTADOS-M1.md` | HA | ? i | `04-IMPLEMENTACION/rx550-torneo/README-M1.md` | `03-EXPERIMENTOS/M1-cap-35-30/runs/20260919-235939/` | `NOT_REPRODUCED` |
| `SUPERPOSITION` | RESULT | `03-EXPERIMENTOS/R-14-SUPERPOSITION-DISSECTION/R-14-SUPERPOSITION-DISSECTION.md` | HA | ? i | `03-EXPERIMENTOS/EXPLORATORIO-GravityMark/runs/RESULTADO-Superposition.md` | `05-FUENTES-EXTERNAS/RX550_Benchmarks/` (excluidos) | `UNKNOWN` |
| `BENCHMARKS` | RESULT | `05-FUENTES-EXTERNAS/RX550_Benchmarks/BENCHMARK-INVENTORY.md` | EXT | n/a | `R0-5-BENCHMARKS-EXTERNOS-RX550.md` · `05-FUENTES-EXTERNAS/RX550_Benchmarks/README.md` | — | `EXTERNAL` |
| `GLMARK2` | RESULT | `03-EXPERIMENTOS/fase-a-discriminacion-20260919-114241/RESULTADOS-FASE-A.md` | HA | ? i | `BENCHMARK-INVENTORY.md` | `03-EXPERIMENTOS/fase-a-discriminacion-20260919-114241/` | `UNKNOWN` |
| `EXPERIMENTS` | EXPERIMENT | `00-INDICE/MASTER-RESEARCH-STATUS.md` | MX | A d | `03-EXPERIMENTOS/WORKLOAD-SINTETICO/RESEARCH.md` | por `EXPERIMENT_DIR` | `UNKNOWN` |
| `REPRODUCIBILITY` | REPRODUCIBILITY | `TESTING.md` | CUR | B d | `04-IMPLEMENTACION/IMPLEMENTATION-ROADMAP.md` | — | `CURRENT_EVIDENCE=NOT_AVAILABLE` |

### D8 · `ISOLATION_AND_C1`

| TOPIC | QTYPE | PRIMARY | TEM | HOST | SECONDARY | RAW | ESCALATION |
|---|---|---|---|---|---|---|---|
| `C1` | STATUS | `04-IMPLEMENTACION/C1-ISOLATION-DESIGN-v1.0.md` | MX | ? i | `04-IMPLEMENTACION/C1-ISOLATION-AUTOMATOR.md` | `01-AUDITORIA/FASE-C1-RUNTIME-PREFLIGHT/C1-PREFLIGHT-20260925T061932Z-PRIV.json` | `CONFLICT` C1 → **`CONFLICT_SOURCE`** `01-AUDITORIA/DOCUMENTARY-RECONCILIATION-2026-09-25.md` · `DEFERRED` |
| `C1` **tests/reconciliación** *(sub-ruta)* | RECONCILIATION | `01-AUDITORIA/DOCUMENTARY-RECONCILIATION-2026-09-25.md` §`C1_TESTS` | MX | ? i | `01-AUDITORIA/FASE-R5-C1-TECHNICAL-DOCUMENTATION/C1-TECHNICAL-RECORD.md` (24/24) · `00-INDICE/DIAGRAMAS/12-MATRIZ-TRAZABILIDAD.md` (37/37) | — | `CONFLICT` C1 con precedencia declarada |
| `OWNERSHIP` | STATUS | `01-AUDITORIA/FASE-P0-EXPERIMENTAL-VALIDITY-GATE/P0-EXPERIMENTAL-VALIDITY-GATE-2026-09-24.md` | HA | A d | `C1-PREFLIGHT-20260925T061932Z-PRIV.md` · `AGENTS.md` §Ownership | `01-AUDITORIA/FASE-C1-RUNTIME-PREFLIGHT/C1-PREFLIGHT-20260925T061932Z-PRIV.json` | `PARTIAL`; `CURRENT_EVIDENCE=NOT_AVAILABLE` |
| `GATES` | STATUS | `01-AUDITORIA/FASE-P0-EXPERIMENTAL-VALIDITY-GATE/P0-EXPERIMENTAL-VALIDITY-GATE-2026-09-24.md` | HA | A d | `RELEASE-CANDIDATE.md` · `DOCUMENTARY-RECONCILIATION-2026-09-25.md` | — | `DEFERRED` |
| `RECOVERY` | RECOVERY | `ROLLBACK.md` | CUR | ? d | `C1-RECOVERY-INDEPENDENCE-VALIDATION-20260925T063810Z.md` | `01-AUDITORIA/FASE-C1-RUNTIME-PREFLIGHT/C1-RECOVERY-RUNTIME-TEST-20260925T064051Z-POST.json` | `RESTORE_VALIDATED=NO` |
| `TTY` | RECOVERY | `01-AUDITORIA/FASE-C1-RUNTIME-PREFLIGHT/C1-TTY-GETTY-AUDIT-20260925T074900Z.md` | HA | ? i | `ROLLBACK.md` · `01-AUDITORIA/FASE-C1-RUNTIME-PREFLIGHT/C1-TTY3-RUNTIME-TEST-20260925T075606Z-POST.md` | `01-AUDITORIA/FASE-C1-RUNTIME-PREFLIGHT/C1-TTY-GETTY-AUDIT-20260925T074900Z.json` | `CURRENT_EVIDENCE=NOT_AVAILABLE` |
| `D_STATE` | STATUS | `04-IMPLEMENTACION/C1-ISOLATION-AUTOMATOR.md` | MX | ? i | `C1-ISOLATION-DESIGN-v1.0.md` | — | `CURRENT_EVIDENCE=NOT_AVAILABLE` |

### D9 · `STORAGE`

| TOPIC | QTYPE | PRIMARY | TEM | HOST | SECONDARY | RAW | ESCALATION |
|---|---|---|---|---|---|---|---|
| `STORAGE` | STORAGE | `01-AUDITORIA/FASE-P0-EXPERIMENTAL-VALIDITY-GATE/P0-EXPERIMENTAL-VALIDITY-GATE-2026-09-24.md` | HA | A d | `00-INDICE/AUDITORIA-CONSUMO-SEGUNDO-PLANO.md` | — | `CURRENT_EVIDENCE=NOT_AVAILABLE` |
| `HDD` | STORAGE | `01-AUDITORIA/FASE-P0-EXPERIMENTAL-VALIDITY-GATE/P0-EXPERIMENTAL-VALIDITY-GATE-2026-09-24.md` | HA | A i | `02-ARQUITECTURA/knowledge.md` | — | `HDD_HEALTHY=UNKNOWN`; `CURRENT_EVIDENCE=NOT_AVAILABLE` |
| `BTRFS` | STORAGE | `PROBLEM-STATUS-FINAL.md` (P-012) | MX | ? d | `03-EXPERIMENTOS/WORKLOAD-SINTETICO/RESEARCH.md` §R-11 · `DOCUMENTARY-RECONCILIATION-2026-09-25.md` | `03-EXPERIMENTOS/WORKLOAD-SINTETICO/src/graphics.cpp` | `CONFLICT` C6 |
| `SMART` | STORAGE | `01-AUDITORIA/FASE-P0-EXPERIMENTAL-VALIDITY-GATE/P0-EXPERIMENTAL-VALIDITY-GATE-2026-09-24.md` | HA | A d | `AGENTS.md` §HDD and Btrfs | — | `NOT_RUN`; no autorizado |
| `IO` | STORAGE | `00-INDICE/AUDITORIA-CONSUMO-SEGUNDO-PLANO.md` | HA | ? i | `AUDITORIA-CANDIDATOS-BACKGROUND-v2.md` | — | `CURRENT_EVIDENCE=NOT_AVAILABLE` |
| `PSI` | STORAGE | `01-AUDITORIA/FASE-P0-EXPERIMENTAL-VALIDITY-GATE/P0-EXPERIMENTAL-VALIDITY-GATE-2026-09-24.md` | HA | A d | `C1-ISOLATION-DESIGN-v1.0.md` | — | `CURRENT_EVIDENCE=NOT_AVAILABLE` |

### D10 · `BACKGROUND_AND_SERVICES`

| TOPIC | QTYPE | PRIMARY | TEM | HOST | SECONDARY | RAW | ESCALATION |
|---|---|---|---|---|---|---|---|
| `SYSTEMD` | CONFIGURATION | `00-INDICE/AUDITORIA-CANDIDATOS-BACKGROUND-v2.md` | HA | A i | `PROTOCOLO-AB-LIMPIEZA-BACKGROUND.md` | — | `NOT_AVAILABLE` (0 unidades en HOST-C) |
| `KALM` | CONFIGURATION | `00-INDICE/AUDITORIA-CANDIDATOS-BACKGROUND-v2.md` | HA | A i | `PATCH-REGISTRY-RECOVERED.md` §B | `backup/system/kalm-gpu` | `NOT_AVAILABLE` en HOST-C |
| `KALM` **estado operativo en HOST-C** *(sub-ruta)* | CONFIGURATION | `01-AUDITORIA/PATCH-RECOVERY/PATCH-SOURCES.md` §5 | CUR | **C d** | `PATCH-REGISTRY-RECOVERED.md` §B (parches) | — | `SERVICE_ABSENT` — ver §3bis |
| `AUTOPILOT` | CONFIGURATION | `00-INDICE/AUDITORIA-CANDIDATOS-BACKGROUND-v2.md` | HA | A i | `PROTOCOLO-AB-LIMPIEZA-BACKGROUND.md` | — | `NOT_AVAILABLE` (contenido `RX550-UNK-01`) |
| `BACKGROUND` | STATUS | `00-INDICE/AUDITORIA-CONSUMO-SEGUNDO-PLANO.md` | HA | ? i | `AUDITORIA-CANDIDATOS-BACKGROUND-v2.md` | — | `CURRENT_EVIDENCE=NOT_AVAILABLE` |
| `IRQ` | CONFIGURATION | `00-INDICE/AUDITORIA-CANDIDATOS-BACKGROUND-v2.md` | HA | ? i | `P0-…GATE-2026-09-24.md` | — | `CURRENT_EVIDENCE=NOT_AVAILABLE` |

### D11 · `PASSTHROUGH`

| TOPIC | QTYPE | PRIMARY | TEM | HOST | SECONDARY | RAW | ESCALATION |
|---|---|---|---|---|---|---|---|
| `VFIO` | HARDWARE | `01-AUDITORIA/FASE-VFIO-PASSTHROUGH/VFIO-FEASIBILITY-AUDIT-20260925T132242Z.md` | CUR | B i | `ROLLBACK.md` · `INSTALL.md` | `01-AUDITORIA/FASE-VFIO-PASSTHROUGH/VFIO-FEASIBILITY-AUDIT-20260925T132242Z.json` | `BLOCK` (viabilidad) |
| `IOMMU` | HARDWARE | `01-AUDITORIA/FASE-VFIO-PASSTHROUGH/VFIO-FEASIBILITY-AUDIT-20260925T132242Z.md` | CUR | B i | `INSTALL.md` | — | `WEB` para requisitos de IOMMU |
| `BACO` | HARDWARE | **`NOT_AVAILABLE`** | — | — | — | — | `NOT_AVAILABLE` — sin escalada posible |

### D12 · `GOVERNANCE`

| TOPIC | QTYPE | PRIMARY | TEM | HOST | SECONDARY | RAW | ESCALATION |
|---|---|---|---|---|---|---|---|
| `SECURITY` | SECURITY | `AGENTS.md` | CUR | n/a | `RELEASE-EXCLUSIONS.md` · `README.md` §Reglas | — | `NOT_READY` |
| `SAFETY` | SECURITY | `04-IMPLEMENTACION/IMPLEMENTATION-SAFETY-RULES.md` | MX | n/a | `AGENTS.md` | — | Ninguno |
| `VOCABULARY` | DOCUMENTATION | `AGENTS.md` §Evidence vocabulary | CUR | n/a | `00-INDICE/ESTADOS-ES-EN.md` | — | `REVIEW_REQUIRED` (dos vocabularios) |
| `TEST` | TEST | `TESTING.md` | CUR | B d | `04-IMPLEMENTACION/rx550-torneo/tests/` | — | `CURRENT_EVIDENCE=NOT_AVAILABLE` |
| `OPENCODE` | DOCUMENTATION | `AGENTS.md` §OpenCode discovery | CUR | n/a | — | — | Ninguno |
| `AGENT_RULES` | DOCUMENTATION | `AGENTS.md` | CUR | n/a | — | — | Ninguno |
| `HYPOTHESIS` | STATUS | `00-INDICE/HYPOTHESIS-REGISTER.md` | MX | n/a | `02-ARQUITECTURA/hypotheses.md` · `rejected_ideas.md` | — | `DRAFT` (sin veredictos) |
| `DESIGN` | IMPLEMENTATION | `00-INDICE/MASTER-PLAN.md` | MX | n/a | `04-IMPLEMENTACION/IMPLEMENTATION-ROADMAP.md` | — | Ninguno (no es autorización) |
| `FIREFOX` | CONFIGURATION | **`NOT_AVAILABLE`** | — | — | — | — | `NOT_AVAILABLE` — sin escalada posible |
| `GRUB` | CONFIGURATION | **`NOT_AVAILABLE`** | — | — | — | — | `NOT_AVAILABLE` — solo mención como prohibición |
| `UDEV` | CONFIGURATION | **`NOT_AVAILABLE`** | — | — | — | — | `NOT_AVAILABLE` — solo mención como prohibición |

## 3bis. Estado operativo — una versión instalada NO es prueba de funcionamiento

**Añadido tras `RT-0006` y `RT-0007`.** Ambas consultas revelaron el mismo fallo:
el router entregaba la *versión* (`Mesa 26.2.3`, `kalm v3`) y el agente podía responder «Mesa
funciona» o «Kalm está activo» sin haber leído el hecho que lo desmiente.

### Tokenos obligatorios

Cada afirmación sobre el estado del host debe llevar uno de estos. **No se sustituyen entre sí.**

| Token | Significado | Ejemplo verificable |
|---|---|---|
| `VERSION_PRESENT` | Una versión está escrita en un documento | «el doc dice Mesa 26.2.3» |
| `PACKAGE_PRESENT` | El paquete está instalado (`rpm -q`) | `mesa-dri-drivers-26.2.3-1.fc44` |
| `DRIVER_PRESENT` | El módulo/kernel driver está cargado | `amdgpu` presente en sysfs |
| **`DRIVER_OPERATIONAL`** | El driver **funciona**, evidenciado por operación exitosa | `RADV` enumera `0x699f`; `vulkaninfo` responde |
| `SERVICE_PRESENT` | La unidad systemd existe | `systemctl list-unit-files` la lista |
| **`SERVICE_ACTIVE`** | La unidad está **corriendo** | `systemctl is-active` = `active` |
| `SYSTEM_CHANGE_APPLIED` | Un cambio de sistema se aplicó de verdad | `NEW_DISK_APPLIED=YES` verificado |

### Regla de no inferencia

```
VERSION_PRESENT   ≠ PACKAGE_PRESENT   (un doc puede citar una versión no instalada)
PACKAGE_PRESENT   ≠ DRIVER_PRESENT    (instalado no significa cargado)
DRIVER_PRESENT    ≠ DRIVER_OPERATIONAL (cargado no significa que funcione)
SERVICE_PRESENT   ≠ SERVICE_ACTIVE     (existente no significa corriendo)
```

**Nunca** derivar `DRIVER_OPERATIONAL` desde `PACKAGE_PRESENT`, ni `SERVICE_ACTIVE` desde
`SERVICE_PRESENT`. Si no hay evidencia de la operación, el token es `NOT_AVAILABLE`.

### Hechos operativos de HOST-C observados

Del único documento con `HOST_SCOPE=HOST-C` (`PATCH-SOURCES.md` §3, medido 2026-09-25T22:22Z):

| Elemento | Token | Valor observado | Token NO autorizado |
|---|---|---|---|
| `mesa-dri-drivers` | `PACKAGE_PRESENT` | `26.2.3-1.fc44` | `DRIVER_OPERATIONAL` para Vulkan |
| `mesa-vulkan-drivers` | `PACKAGE_ABSENT` | **no instalado** | `VERSION_PRESENT` |
| `amdgpu` en la RX550 | `DRIVER_PRESENT` | PCI `1002:699f`, BDF `0000:01:00.0` | — |
| RADV / Vulkan en HOST-C | `DRIVER_OPERATIONAL` | **`NOT_AVAILABLE`** — no hay `mesa-vulkan-drivers` | asumir operativo desde Mesa 26.2.3 |
| `kalm*.service` | `SERVICE_ABSENT` | **0 unidades** | `SERVICE_ACTIVE` |
| `system-autopilot.*` | `SERVICE_ABSENT` | **0 unidades** | `SERVICE_ACTIVE` |
| `/opt/mesa-26.2.2-rx550-haswell` | `SYSTEM_CHANGE_NOT_APPLIED` | ausente | `SYSTEM_CHANGE_APPLIED` |
| Parches de sistema B (13) | `SYSTEM_CHANGE_NOT_APPLIED` | `NEW_DISK_APPLIED=NO` | `SYSTEM_CHANGE_APPLIED` |

**Consecuencia para `MESA`:** decir «el host tiene Mesa 26.2.3» es `VERSION_PRESENT` +
`PACKAGE_PRESENT` y es cierto. Decir «el host tiene RADV operativo» es **`NOT_AVAILABLE`**: el
paquete Vulkan no está instalado. Decir «Mesa está verificada en el host vivo» es
`NOT_AVAILABLE` para el stack Vulkan.

**Consecuencia para `KALM`:** decir «Kalm v3 con afinidad IRQ topológica» es `HISTORICAL_ONLY`
(HOST-A). Sobre HOST-C, `KALM` es `SERVICE_ABSENT`. Son afirmaciones sobre hosts distintos y no
deben presentarse como la misma realidad.

### Sub-rutas de estado operativo

Añadidas a la tabla de §3 para que estas consultas lleguen a la fuente correcta sin Barrer:

| Sub-ruta | `PRIMARY` | Preguntas que debe capturar |
|---|---|---|
| `MESA` estado operativo HOST-C | `PATCH-SOURCES.md` §3 | «¿Mesa está instalada?», «¿RADV funciona?», «¿hay Mesa verificada aquí?» |
| `KALM` estado operativo HOST-C | `PATCH-SOURCES.md` §5 | «¿Kalm está activo?», «¿cuántas unidades hay?», «¿se aplicó el parche?» |

Cualquier consulta de la columna derecha va **directo** a esa sub-ruta con `nav_depth=1`.

## 4. `EXPERIMENT_DIR` — los 15 buckets

Ruta obligatoria hacia artefactos: `TOPIC → EXPERIMENT_DIR → EXPERIMENT_MD → artefacto`.
**Nunca** abrir un artefacto sin leer antes su `EXPERIMENT_MD`.

| `EXPERIMENT_DIR` | `EXPERIMENT_MD` (entrada) |
|---|---|
| `03-EXPERIMENTOS/FASE-R4B-GOVERNOR` | `EXP-F4-A-RESULTADOS-v2.3.md` |
| `03-EXPERIMENTOS/FASE-R4C-JITTER-OBSERVABILITY` | `EXP-F1-A-RESULTADOS.md` |
| `03-EXPERIMENTOS/FASE-R4B-THERMAL-TEST` | `TEST-TERMICO-READONLY.md` |
| `03-EXPERIMENTOS/FASE-D-COUNTERS-AUDIT` | `FASE-D-GFX8-EVENT-ID-AUDIT.md` |
| `03-EXPERIMENTOS/M1-cap-35-30` | `RESULTADOS-M1.md` |
| `03-EXPERIMENTOS/fase-a-discriminacion-20260919-114241` | `RESULTADOS-FASE-A.md` |
| `03-EXPERIMENTOS/fase-b-cap-probe-20260919-122038` | `RESULTADOS-FASE-B.md` |
| `03-EXPERIMENTOS/WORKLOAD-SINTETICO` | `RESEARCH.md` |
| `03-EXPERIMENTOS/ep05-mesa-custom-20260919-212249` | `RESULTADOS-EP05.md` |
| `03-EXPERIMENTOS/ep06-soak-cap-20260919-205645` | `RESULTADOS-EP06.md` |
| `03-EXPERIMENTOS/FASE-R4A-BANDWIDTH-REAL` | `EXP-F3-A-BANDWIDTH-REAL.md` |
| `03-EXPERIMENTOS/R-14-SUPERPOSITION-DISSECTION` | `R-14-SUPERPOSITION-DISSECTION.md` |
| `03-EXPERIMENTOS/EXPLORATORIO-GravityMark` | *(sin `.md` en raíz)* |
| `03-EXPERIMENTOS/rx550-power-sweep-20260918-132309` | `…-132309/ESTADO-HISTORICO-NO-UTILIZABLE.md` |
| `03-EXPERIMENTOS/rx550-power-sweep-20260918-140527` | `…-140527/ESTADO-HISTORICO-NO-UTILIZABLE.md` |
| `03-EXPERIMENTOS/results` | `results/ESTADO.md` |

**Los 2 power-sweep están marcados `ESTADO-HISTORICO-NO-UTILIZABLE`: leer ese `.md` ANTES de
cualquier dato de esas carpetas.**

---

## 5. Parches — `PATCH_CLASS`

**El router no aplica parches, no hace cherry-pick y no modifica nada.**

| `PATCH_CLASS` | Dónde | `APPLIED_ON_HOST_C` |
|---|---|---|
| `STATIC_PROJECT_PATCH` | `PATCH-REGISTRY-RECOVERED.md` §A (`RX550-PP-01..07`, `TP-01`, `C1-01/02`, `DP-01/02`) | `PARTIAL` — en el árbol; `PP-05` y `PP-07` requieren rebuild; `C1-01/02` nunca ejecutados |
| `SYSTEM_PATCH` | `PATCH-REGISTRY-RECOVERED.md` §B (`RX550-SD-01..04`, `PM-01/02`, `UD-01/02`, `SCP-01/02/03`, `MP-01`) | **`NO`** — verificado 2026-09-25T22:22Z: 0 unidades `kalm*`, 0 `system-autopilot*`, sin `/opt/kalm`, sin `/opt/mesa-26.2.2-rx550-haswell` |
| `EVIDENCE` | `01-AUDITORIA/PATCH-RECOVERY/PATCH-SOURCES.md` (procedencia y hashes) | `N-A` |
| `HYPOTHESIS` | `RX550-UNK-01` (`system-autopilot`), `RX550-KP-01`/`AG-01`/`GR-01` | `NOT_AVAILABLE` — sin fuente |

**Regla dura:** ningún `SYSTEM_PATCH` se presenta como aplicado al host vivo. El único dato
verificable es el negativo (`NEW_DISK_APPLIED=NO`).
`RX550-MP-01` (Mesa, commit `583c5d2f44152ed70d6f9aff58fbca5abcf7376d`): `ORIGINAL_APPLIED=UNKNOWN`,
`NEW_DISK_APPLIED=NO`, `SYSTEM_CHANGE_REQUIRED=SI`. Es un cambio de **logging**, no funcional.

---

## 6. Referencias rotas — `REFERENCE_STATUS`

**No se reparan.** Se reportan con su causa.

| `REASON` | N | Significado |
|---|---:|---|
| `REORG-2026-09-23` | ~70 | Ruta anterior a la reorganización. La reparación está documentada en `00-INDICE/POST-REORGANIZATION-SET-I-REPAIR-RESULT.md` pero **no se reaplicó** |
| `OLD-DISK-FILE` | ~30 | Cita un fichero del HOST-A que no está en el repo (`kalmd.py`, `kalm-lite.py`, `/usr/local/bin/system-autopilot.sh`). **No es un error** |
| `RUNTIME-UNVERSIONED` | ~25 | Lo crea el runner al ejecutarse (`state.json`, `stdout.txt`, `m1-schedule.json`). **No es un error** |
| `AMBIGUOUS-PATH` | ~15 | Nombre sin ruta; requiere contexto |

Catálogo completo: `../DOCUMENTATION-CENSUS/DOCUMENTATION-RELATIONSHIPS.md` §5.

---

## 7. Los 4 topics sin fuente primaria

`BACO` · `FIREFOX` · `GRUB` · `UDEV` → `PRIMARY_SOURCE=NOT_AVAILABLE`.

El router **no crea documentación** para rellenarlos. Devuelve el terminal con la lista de
menciones como contexto, marcada como mención y no como evidencia. Para `GRUB` y `UDEV`, la
respuesta es doble: *no hay fuente* **y** *están prohibidos*
(`AGENTS.md` §Safety, `README.md` §Reglas de seguridad).

---

## 8.cuando el router no sabe

| Situación | Terminal |
|---|---|
| El topic no está en la tabla de §3 | `ESCALATED` al censo: `../DOCUMENTATION-CENSUS/DOCUMENTATION-TOPICS.md` §15 |
| El `PRIMARY` marca `UNKNOWN` y hay fuente upstream | `ESCALATED` a `WEB`, resultado marcado `EXTERNAL` |
| El `PRIMARY` marca `CONFLICT` | `CONFLICT` con las 2 fuentes de §2 |
| La pregunta pide un valor y hay 3 hosts | `STALE` + `CURRENT_EVIDENCE=NOT_AVAILABLE` |
| Nada de lo anterior | `UNKNOWN` — **nunca** `PASS` |

**Si el router y un documento discrepan, `REVIEW_REQUIRED`.** El router no corrige documentos.
