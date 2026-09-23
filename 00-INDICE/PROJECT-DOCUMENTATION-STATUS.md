# PROJECT-DOCUMENTATION-STATUS.md — Índice Central del Estado del Ecosistema

> **Archivo:** `PROJECT-DOCUMENTATION-STATUS.md` (raíz del repositorio)
> **Fase:** FASE R-2 — COMPLETE PROJECT DOCUMENTATION & ECOSYSTEM ARCHITECTURE (R-2.24)
> **Fecha:** 2026-09-22 — Modo SOLO DOCUMENTAL
> **Clasificación:** [VERIFICADO] (construido por inspección directa del repositorio).
> **Rol:** índice **por elemento del ecosistema** que responde "¿qué existe / falta / está diseñado /
> ejecutado / validado / planteado / autorizado?" para cada pieza. El mapa documental por archivo está en
> `experiments/FASE-R2-PROJECT-DOCUMENTATION/R2-GLOBAL-DOCUMENTATION-MAP.md`.

---

## 0. Convenciones de ESTADO

`EXISTE` = artefacto en repo · `DISEÑADO` = diseño completo ejecutable por otro investigador (sin ejecutar) ·
`EJECUTADO` = corrido al menos una vez · `VALIDADO` = verificado estadísticamente/reproducible ·
`COMPLETADA` = fase cerrada · `PLANIFICADA` = roadmap sin diseño cumplido · `CONGELADO` = no tocar ·
`NO AUTORIZADO` = requiere permiso explícito · `IP` = en proceso.

## 1. Fases y experimentos

| Elemento | Tipo | Estado | Documentación | Evidencia | Dependencias | Próximo paso | Autorización |
|---|---|---|---|---|---|---|---|
| **FASE A — discriminación (histórica)** | Experimento | COMPLETADA | `experiments/fase-a-discriminacion-…/` | runs 1–15 + invalidación | — | (cerrada) | n/a |
| **FASE B — cap-probe (histórica)** | Experimento | COMPLETADA | `fase-b-cap-probe-…/` | 25/28/32/35W probe + EP-08 | — | (cerrada) | n/a |
| **FASE B — POLARIS12-MAP (histórica)** | Mapa HW/SW | COMPLETADA | `experiments/POLARIS12-MAP/` | mapa A–AJ, candidatos GEO/MEM/FRAG/SHD/ASY/PWR | — | alimenta F/G | n/a |
| **EP-05 / EP-06** | Experimentos | COMPLETADOS | `ep05…` / `ep06…` | CUSTOM=STOCK; soak no reproduce E1/E3 | — | (cerrado) | n/a |
| **FASE C (R-14 Superposition)** | Experimento | COMPLETADA | `R-14-SUPERPOSITION-DISSECTION/` | 22.31 W steady / 24.71 W pico; score 804 | — | (cerrado) | n/a |
| **FASE D etapa 1–2** | Contadores (read-only) | COMPLETADAS | `FASE-D-COUNTERS-AUDIT/` | auditoría + contraste A/B×3 (ratio 1.41) | R-0/R-1 | — | n/a |
| **FASE D etapa 3** | Contadores (programados) | **DISEÑADA, NO EJECUTADA** | `FASE-D-ETAPA-3-*.md` + EVENTOS + AUDITORÍA | PRECHECK, EVENTS, Event-ID audit | R-0.1, R1-1 | ejecutar **solo con autorización** | **NO AUTORIZADO** |
| **M1 (vkmark 35/30W)** | Experimento | COMPLETADA/VALIDADO | `M1-cap-35-30/` | 112/112 checks; NO DISCRIMINATIVO | rx550-torneo | — | n/a |
| **Workload sintético** | Infraestructura | EXISTE (CONGELADO) | `WORKLOAD-SINTETICO/` | E-01/E-02/E-03/ES-01/F2 (VERIFICADO) | — | diseño 8 modos (R-2.9) | modificación NO |
| **FASE E — Real-Game Baseline** | Diseño | **DISEÑADA, BLOQUEADA** | `FASE-R2…/FASE-E-…DESIGN.md` | Bloqueada: sin juego reproducible autorizado | selección/instalación de juego | seleccionar candidato | instalación NO AUTORIZADA |
| **FASE F — Geometry (GEO-01..08)** | Diseño | **DISEÑADA, NO EJECUTADA** | `FASE-F-…DESIGN.md` | fichas completas | workload gráfico + Lab K | relación J/implementar launcher | ejecución NO AUTORIZADA |
| **FASE G — Memory/VRAM/GTT** | Diseño | **DISEÑADA, NO EJECUTADA** | `FASE-G-…DESIGN.md` | modelo + G-M1..M5 | workload sintético | G-M1/M5 (read-only) | read-only SÍ; scripts nuevos autorizar |
| **FASE H — RADV/Workarounds** | Diseño | **DISEÑADA, NO EJECUTADA** | `FASE-H-…DESIGN.md` | H-1..7 | R0-3 | lectura de código local (M-A) | SÍ (lectura) |
| **FASE I — PowerPlay/DPM** | Diseño | **DISEÑADA, NO EJECUTADA** | `FASE-I-…DESIGN.md` | I-1..5 | L | I-1 read-only; I-2..5 con L | writes solo en corrida L |
| **FASE J — Priority Matrix** | Diseño | **DISEÑADA, NO EJECUTADA** | `EXPERIMENT-PRIORITY-MATRIX.md` | 10 criterios, ALTA/MEDIA/BAJA/BLOQUEADOS | F/G/H/I | priorizar ALTA read-only | n/a |
| **FASE K — Performance Lab (K1..K10)** | Diseño | **DISEÑADA, NO IMPLEMENTADA** | `FASE-K-…DESIGN.md` | estructura RUN, telemetría, validación, hashing | — | implementar runner (código futuro) | codificación NO AUTORIZADA |
| **FASE L — RX550-Tuner** | Diseño | **DISEÑADA, NO IMPLEMENTADA** | `FASE-L-…DESIGN.md` | state machine + rollback + ownership | K, I | implementar + autorización writes | writes solo en marco L |
| **FASE M — GFX8 Counter Research** | Diseño | **DISEÑADA (catálogo DOCUMENTADO)** | `FASE-M-…DESIGN.md` | R-0.1/R1-1 catálogo; rutas M-A..E | R-0/R-1 | M-A lecturas | programación NO AUTORIZADA |
| **FASE N — Ecosistema** | Diseño | **DISEÑADA** | `FASE-N-…DESIGN.md` | 14 nombres + arquitectura | — | (documental completo) | n/a |
| **FASE O — Control/Orquestación** | Diseño | **DISEÑADA, NO EJECUTADA** | `FASE-O-…DESIGN.md` | comparación gestores externos | Orquestador | evaluación futura | instalación NO AUTORIZADA |
| **FASE P — Frame Gen/Upscaling** | Diseño | **DISEÑADA, NO EJECUTADA** | `FASE-P-…DESIGN.md` | separación REAL/PERCIBIDO | E | prueba futura | instalación NO AUTORIZADA |
| **FASE Q — Mesa Optimization** | Diseño | **DISEÑADA, NO EJECUTADA** | `FASE-Q-…DESIGN.md` | inventario por dominio + pipeline validación | M/K | observación código | modificar Mesa NO AUTORIZADO |

## 2. Proyectos propios (`projects/`)

| Proyecto | Estado | Diseño | Dependencias | Implementado | Regla |
|---|---|---|---|---|---|
| **BERRETA** | IDEA/DISEÑO, PROVISIONAL | `projects/BERRETA/BERRETA-DESIGN.md` | ASY-01, memoria FASE G, Lab K | NO | no implementar sin evidencia |
| **Ghost / Ghost Cache** | IDEA, PROVISIONAL | `projects/GHOST/GHOST-CACHE-DESIGN.md` | G-M1/G-M5 (modelo memoria) | NO | ascender ciclo IDEA→HIPÓTESIS→OBSERVADO→VALIDADO con evidencia |
| **RX Compression Engine** | IDEA, PROVISIONAL | `projects/RX-COMPRESSION-ENGINE/…DESIGN.md` | G-M2/G-M4, síntesis (módulo TEXTURE) | NO | evaluar casos ayuda/no-ayuda |
| **Orquestador Final** | DISEÑO, NO IMPLEMENTADO | `projects/ORCHESTRATOR/FINAL-ORCHESTRATOR-DESIGN.md` | K, L, M, O, P, Q | NO | sin autoridad de HW; SAFETY BOUNDARY |

## 3. Infraestructura y herramientas

| Elemento | Estado | Doc | Nota |
|---|---|---|---|
| **rx550-torneo** | IMPLEMENTADO + VALIDADO (65/55/56/112 checks) | `rx550-torneo/README-*.md` | herramienta operativa; no lo reemplaza FASE L |
| **Benchmarks instalados** | EXISTE | `~/Escritorio/berchmark/instalados/` | GravityMark, Superposition, Heaven, Valley (hashes verificados) |
| **RADV/radeonsi (Mesa system y /opt custom)** | CONGELADO | BUILD_SPEC §5/§30/§31 | no modificar; EP-05 ya verificó CUSTOM=STOCK |
| **Kalm** | Activo (detectar en vivo) | knowledge.md | no asumir estado; protocolo ownership |
| **GPUPerfAPI v3.11.1 (referencia)** | Descargado/verificado documentalmente | `FASE-R0…/R0-1-…REFERENCE.txt` | única fuente abierta con tablas GFX8 |

## 4. Resumen por categoría (contestar a las 7 preguntas)

| Pregunta | Respuesta abreviada |
|---|---|
| ¿Qué **EXISTE**? | Toda la capa FASE A–D/R-0/R-1 (docs+datos), WORKLOAD-SINTETICO (código+runs), rx550-torneo, benchmarks, backup histórico E-series |
| ¿Qué **FALTA**? | Código del Lab K, launcher del sintético (8 modos), implementación de L/M/O/P/Q, GHOST/BERRETA/RX-Comp/Orquestador (solo diseños), juego real (FASE E) |
| ¿Qué está **DISEÑADO** (sin ejecutar)? | E (bloqueada), F, G, H, I, J, K, L, M, N, O, P, Q + 4 proyectos (diseño) |
| ¿Qué está **EJECUTADO**? | Fases A/B/C/D(1-2)/M1, EP-05/06, E-01..03/ES-01/F2, R-14, M1 |
| ¿Qué está **VALIDADO**? | A–B probados, D-1/2 auditado, M1 (112/112), E-03/ES-01/F2 (VERIFICADO), rx550-torneo checks, GPUPerfAPI catálogo (documental), R-0.1/R-0.2/R-0.3 |
| ¿Qué está **PLANTEADO** (roadmap sin diseño)? | ejecución de cada fase tras Lab K; instalaciones de herramientas externas (O/P/M-B); adopción de tecnologías (se decide con gobernanza) |
| ¿Qué está **NO AUTORIZADO / CONGELADO**? | programar contadores (D-3/M), toda escritura sysfs/PowerPlay/VBIOS/BIOS/Mesa/kernel fuera de marco L, modificar WORKLOAD-SINTETICO, instalar/ejecutar benchmarks sin permiso, Kalm/GRUB/kernel |

## 5. Conclusión
El ecosistema completo queda **inventariado, diseñado y trazable** en un único índice. La ejecución de las
fases E–J/K–Q y de los proyectos propios permanece sujeta a: (1) implementación autorizada del Lab K/
launcher, (2) autorización explícita para writes/contadores/instalaciones, y (3) evidencia de las fases
read-only (G-M1/M5, F/G) antes de ascender proyectos PROVISIONAL.