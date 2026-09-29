# PROJECT-DOCUMENTATION-STATUS.md — Índice Central del Estado del Ecosistema

> **Archivo:** `00-INDICE/PROJECT-DOCUMENTATION-STATUS.md` (índice de navegación del estado documental, `DRAFT/CONFLICT`)
> **Fase:** FASE R-2 — COMPLETE PROJECT DOCUMENTATION & ECOSYSTEM ARCHITECTURE (R-2.24)
> **Fecha:** 2026-09-24; reconciliación 2026-09-25 — Modo SOLO DOCUMENTAL
> **Clasificación:** [DRAFT/CONFLICT] (índice construido por inspección; requiere
> reconciliación continua y no sustituye las fuentes canónicas).
> **Rol:** índice **por elemento del ecosistema** que responde "¿qué existe / falta / está diseñado /
> ejecutado / validado / planteado / autorizado?" para cada pieza. El mapa documental por archivo está en
> `00-INDICE/R2-GLOBAL-DOCUMENTATION-MAP.md`.

---

> **Nota de alcance (2026-09-23):** las rutas de este índice son localizadores
> canónicos de la estructura reorganizada. Las referencias a `RX550_Iterative_Research/`,
> al backup y a documentos históricos se conservan únicamente cuando forman parte de la
> trazabilidad; no son rutas operativas actuales.

## 0. Convenciones de ESTADO

`EXISTE` = artefacto en repo · `DISEÑADO` = diseño completo sin ejecutar ·
`EJECUTADO` = corrido al menos una vez · `VALIDADO` = solo con gate explícito ·
`INCONCLUSO` = muestra/precondiciones insuficientes · `PARADA_D` = detenida por condición definida ·
`UNKNOWN` = evidencia insuficiente · `DRAFT` = provisional · `CONFLICT` = precedencia pendiente ·
`CONGELADO` = no tocar · `NO AUTORIZADO` = requiere permiso explícito · `IP` = en proceso.
La taxonomía completa está en `00-INDICE/ESTADOS-ES-EN.md`.

## 1. Fases y experimentos

| Elemento | Tipo | Estado | Documentación | Evidencia | Dependencias | Próximo paso | Autorización |
|---|---|---|---|---|---|---|---|
| **FASE A — discriminación (histórica)** | Experimento | COMPLETADA | `03-EXPERIMENTOS/fase-a-discriminacion-…/` | runs 1–15 + invalidación | — | (cerrada) | n/a |
| **FASE B — cap-probe (histórica)** | Experimento | COMPLETADA | `03-EXPERIMENTOS/fase-b-cap-probe-20260919-122038/` | 25/28/32/35W probe + EP-08 | — | (cerrada) | n/a |
| **FASE B — POLARIS12-MAP (histórica)** | Mapa HW/SW | COMPLETADA | `02-ARQUITECTURA/POLARIS12-MAP/` | mapa A–AJ, candidatos GEO/MEM/FRAG/SHD/ASY/PWR | — | alimenta F/G | n/a |
| **Addenda ASIC/counters/telemetría (2026-09-24)** | Actualización de conocimiento | EXISTE / `PARTIALLY_SUPPORTED` | `02-ARQUITECTURA/COUNTERS-ASIC-TELEMETRY-KNOWLEDGE-ADDENDUM-2026-09-24.md` | correcciones catálogo→API→runtime→validación; ranking A–K | mapa/master | gate P0 de entorno/ownership; counters P3 | sólo documental; no autorización de ejecución |
| **GATE P0 — validez experimental (2026-09-24)** | Auditoría de entorno | **B. `CONTAMINATED_REQUIRES_ISOLATION`** | `01-AUDITORIA/FASE-P0-EXPERIMENTAL-VALIDITY-GATE/P0-EXPERIMENTAL-VALIDITY-GATE-2026-09-24.md` | ownership parcial; clientes RX550; autopilot/kalm con escrituras observadas; CPU/IRQ/PM/storage caracterizados parcialmente | estado vivo del host | revisar diseño de aislamiento antes de A/B; no ejecutar | sólo Gate READ-ONLY; no tuning/optimización |
| **DOCUMENTARY RECONCILIATION (2026-09-25)** | Auditoría/provenance | **COMPLETADA_CON_CONFLICTOS** | `01-AUDITORIA/DOCUMENTARY-RECONCILIATION-2026-09-25.md` | F0/F1/A0/BD=`VOLATILE_EXTERNAL`; C1/H12-4/Mesa/Btrfs reconciliados como conflictos explícitos | P0/C1/R4B | registrar procedencia; no ejecutar runtime | sólo documentación; sin commit |
| **C1 ISOLATION DESIGN (2026-09-25)** | Diseño/protocolo | **PREPARED_FOR_REVIEW** | `04-IMPLEMENTACION/C1-ISOLATION-DESIGN-v1.0.md` + `00-INDICE/DIAGRAMAS/15-C1-ISOLATION-DESIGN.md` | ownership FULL, prechecks, guard, GO/NO-GO/ABORT, restore; `EXECUTION=NONE` | P0/C1-SIDE/R5 | `GAP_REVIEW=COMPLETE`; solicitar autorización separada; no ejecutar | sólo documentación; sin runtime/code/commit |
| **EP-05 / EP-06** | Experimentos | COMPLETADOS | `03-EXPERIMENTOS/ep05-mesa-custom-20260919-212249/` / `03-EXPERIMENTOS/ep06-soak-cap-20260919-205645/` | CUSTOM=STOCK; soak no reproduce E1/E3 | — | (cerrado) | n/a |
| **FASE C (R-14 Superposition)** | Experimento | COMPLETADA | `03-EXPERIMENTOS/R-14-SUPERPOSITION-DISSECTION/` | 22.31 W steady / 24.71 W pico; score 804 | — | (cerrado) | n/a |
| **FASE D etapa 1–2** | Contadores (read-only) | COMPLETADAS | `03-EXPERIMENTOS/FASE-D-COUNTERS-AUDIT/` | auditoría de herramientas/registros + contraste A/B×3 (ratio 1.41); no valida selectors GFX8 | R-0/R-1 | counters P3; no reinicio automático | n/a |
| **FASE D etapa 3** | Contadores (programados) | **DISEÑADA, NO EJECUTADA** | `03-EXPERIMENTOS/FASE-D-COUNTERS-AUDIT/FASE-D-ETAPA-3-*.md` + EVENTOS + AUDITORÍA | PRECHECK, EVENTS, Event-ID audit | R-0.1, R1-1 | ejecutar **solo con autorización** | **NO AUTORIZADO** |
| **M1 (vkmark 35/30W)** | Experimento | **EJECUTADA/COMPLETADA — NO DISCRIMINATIVA** | `03-EXPERIMENTOS/M1-cap-35-30/` | 112/112 checks; cap no liga; no valida la hipótesis M2 | rx550-torneo | — | n/a |
| **Workload sintético** | Infraestructura | EXISTE (CONGELADO) | `03-EXPERIMENTOS/WORKLOAD-SINTETICO/` | E-01/E-02/E-03/ES-01/F2 (VERIFICADO) | — | diseño 8 modos (R-2.9) | modificación NO |
| **FASE E — Real-Game Baseline** | Diseño | **DISEÑADA, BLOQUEADA** | `04-IMPLEMENTACION/FASE-E-REAL-GAME-BASELINE-DESIGN.md` | Bloqueada: sin juego reproducible autorizado | selección/instalación de juego | seleccionar candidato | instalación NO AUTORIZADA |
| **FASE F — Geometry (GEO-01..08)** | Diseño | **DISEÑADA, NO EJECUTADA** | `04-IMPLEMENTACION/FASE-F-GEOMETRY-INVESTIGATION-DESIGN.md` | fichas completas | workload gráfico + Lab K | relación J/implementar launcher | ejecución NO AUTORIZADA |
| **FASE G — Memory/VRAM/GTT** | Diseño | **DISEÑADA, NO EJECUTADA** | `04-IMPLEMENTACION/FASE-G-MEMORY-VRAM-GTT-DESIGN.md` | modelo + G-M1..M5 | workload sintético | G-M1/M5 (read-only) | read-only SÍ; scripts nuevos autorizar |
| **FASE H — RADV/Workarounds** | Diseño | **DISEÑADA, NO EJECUTADA** | `04-IMPLEMENTACION/FASE-H-RADV-WORKAROUNDS-DESIGN.md` | H-1..7 | R0-3 | lectura de código local (M-A) | SÍ (lectura) |
| **FASE I — PowerPlay/DPM** | Diseño | **DISEÑADA, NO EJECUTADA** | `04-IMPLEMENTACION/FASE-I-POWERPLAY-DPM-DESIGN.md` | I-1..5; I-1 read-only; I-2..5 son candidatos, no ejecución de I | L (solo autorización/orden futuro) | I-1 read-only; I-2..5 requieren L | writes solo en marco L |
| **FASE J — Priority Matrix** | Diseño | **DISEÑADA, NO EJECUTADA** | `04-IMPLEMENTACION/EXPERIMENT-PRIORITY-MATRIX.md` | 10 criterios, ALTA/MEDIA/BAJA/BLOQUEADOS | F/G/H/I | priorizar ALTA read-only | n/a |
| **FASE K — Performance Lab (K1..K10)** | Diseño | **DISEÑADA, NO IMPLEMENTADA** | `04-IMPLEMENTACION/FASE-K-PERFORMANCE-LAB-DESIGN.md` | estructura RUN, telemetría, validación, hashing | — | implementar runner (código futuro) | codificación NO AUTORIZADA |
| **FASE L — RX550-Tuner** | Diseño | **DISEÑADA, NO IMPLEMENTADA** | `04-IMPLEMENTACION/FASE-L-RX550-TUNER-DESIGN.md` | state machine + rollback + ownership | K; I solo interfaces/feedback | implementar + autorización writes | writes solo en marco L |
| **FASE M — GFX8 Counter Research** | Diseño | **DISEÑADA (catálogo `SUPPORTED`; runtime `UNKNOWN`)** | `04-IMPLEMENTACION/FASE-M-GFX8-COUNTER-RESEARCH-DESIGN.md` | R-0.1/R1-1 catálogo; rutas M-A..E | R-0/R-1 | congelada P3 salvo decisión que requiera counter | programación NO AUTORIZADA |
| **FASE N — Ecosistema** | Diseño | **DISEÑADA** | `04-IMPLEMENTACION/FASE-N-ECOSYSTEM-ARCHITECTURE.md` | 14 nombres + arquitectura | — | (documental completo) | n/a |
| **FASE O — Control/Orquestación** | Diseño | **DISEÑADA, NO EJECUTADA** | `04-IMPLEMENTACION/FASE-O-GPU-CONTROL-ORCHESTRATION-DESIGN.md` | comparación gestores externos | Orquestador | evaluación futura | instalación NO AUTORIZADA |
| **FASE P — Frame Gen/Upscaling** | Diseño | **DISEÑADA, NO EJECUTADA** | `04-IMPLEMENTACION/FASE-P-FRAME-GENERATION-UPSCALING-DESIGN.md` | separación REAL/PERCIBIDO | E | prueba futura | instalación NO AUTORIZADA |
| **FASE Q — Mesa Optimization** | Diseño | **DISEÑADA, NO EJECUTADA** | `04-IMPLEMENTACION/FASE-Q-MESA-POLARIS12-OPTIMIZATION-DESIGN.md` | inventario por dominio + pipeline validación | M/K | observación código | modificar Mesa NO AUTORIZADO |

## 2. Proyectos propios (`04-IMPLEMENTACION/projects/`)

| Proyecto | Estado | Diseño | Dependencias | Implementado | Regla |
|---|---|---|---|---|---|
| **BERRETA** | IDEA/DISEÑO, PROVISIONAL | `04-IMPLEMENTACION/projects/BERRETA/BERRETA-DESIGN.md` | ASY-01, memoria FASE G, Lab K | NO | no implementar sin evidencia |
| **Ghost / Ghost Cache** | IDEA, PROVISIONAL | `04-IMPLEMENTACION/projects/GHOST/GHOST-CACHE-DESIGN.md` | G-M1/G-M5 (modelo memoria) | NO | ascender ciclo IDEA→HIPÓTESIS→OBSERVADO→VALIDADO con evidencia |
| **RX Compression Engine** | IDEA, PROVISIONAL | `04-IMPLEMENTACION/projects/RX-COMPRESSION-ENGINE/…DESIGN.md` | G-M2/G-M4, síntesis (módulo TEXTURE) | NO | evaluar casos ayuda/no-ayuda |
| **Orquestador Final** | DISEÑO, NO IMPLEMENTADO | `04-IMPLEMENTACION/projects/ORCHESTRATOR/FINAL-ORCHESTRATOR-DESIGN.md` | K, L, M, O, P, Q | NO | sin autoridad de HW; SAFETY BOUNDARY |

## 3. Infraestructura y herramientas

| Elemento | Estado | Doc | Nota |
|---|---|---|---|
| **rx550-torneo** | IMPLEMENTADO + VALIDADO (65/55/56/112 checks) | `04-IMPLEMENTACION/rx550-torneo/README-*.md` | herramienta operativa; no lo reemplaza FASE L |
| **Benchmarks externos** | OBSERVADOS, NO CERTIFICADOS POR EL REPO | `~/Escritorio/berchmark/instalados/` | el inventario separa instalación externa, descarga, ejecución histórica y elegibilidad |
| **RADV/radeonsi (Mesa system y /opt custom)** | CONGELADO | `02-ARQUITECTURA/RX550_BUILD_SPECIFICATION.txt` §5/§30/§31 | no modificar; EP-05 ya verificó CUSTOM=STOCK |
| **Kalm** | Activo (detectar en vivo) | `02-ARQUITECTURA/knowledge.md` | no asumir estado; protocolo ownership |
| **GPUPerfAPI v3.17 (referencia; v3.11.1 histórico)** | CATÁLOGO DOCUMENTAL | `05-FUENTES-EXTERNAS/FASE-R0-EXTERNAL-KNOWLEDGE/R0-1-GFX8-EVENT-ID-REFERENCE.txt` | 2304 filas no equivalen a eventos validados; programación NO AUTORIZADA |

## 4. Resumen por categoría (contestar a las 7 preguntas)

| Pregunta | Respuesta abreviada |
|---|---|
| ¿Qué **EXISTE**? | Toda la capa FASE A–D/R-0/R-1 (docs+datos), WORKLOAD-SINTETICO (código+runs), rx550-torneo, benchmarks, backup histórico E-series |
| ¿Qué **FALTA**? | Código del Lab K, launcher del sintético (8 modos), implementación de L/M/O/P/Q, GHOST/BERRETA/RX-Comp/Orquestador (solo diseños), juego real (FASE E) |
| ¿Qué está **DISEÑADO** (sin ejecutar)? | E (bloqueada), F, G, H, I, J, K, L, M, N, O, P, Q + 4 proyectos (diseño) |
| ¿Qué está **EJECUTADO**? | Fases A/B/C/D(1-2)/M1, EP-05/06, E-01..03/ES-01/F2, R-14, M1 |
| ¿Qué está **VALIDADO**? | A–B probados, D-1/2 auditado, E-03/ES-01/F2 (observados), rx550-torneo checks; M1 solo tiene **integridad 112/112** y es `NO DISCRIMINATIVO`, no validación de hipótesis; el catálogo GPUPerfAPI queda `PARTIALLY_RECONCILED` y R-4B `INCONCLUSIVE` |
| ¿Qué está **PLANTEADO** (roadmap sin diseño)? | ejecución de cada fase tras Lab K; instalaciones de herramientas externas (O/P/M-B); adopción de tecnologías (se decide con gobernanza) |
| ¿Qué está **NO AUTORIZADO / CONGELADO**? | programar contadores (D-3/M), toda escritura sysfs/PowerPlay/VBIOS/BIOS/Mesa/kernel fuera de marco L, modificar WORKLOAD-SINTETICO, instalar/ejecutar benchmarks sin permiso, Kalm/GRUB/kernel |

## 5. Conclusión
El ecosistema completo queda **inventariado, diseñado y trazable** en un único índice. La ejecución de las
fases E–J/K–Q y de los proyectos propios permanece sujeta a: (1) implementación autorizada del Lab K/
launcher, (2) autorización explícita para writes/contadores/instalaciones, y (3) evidencia de las fases
read-only (G-M1/M5, F/G) antes de ascender proyectos PROVISIONAL.
