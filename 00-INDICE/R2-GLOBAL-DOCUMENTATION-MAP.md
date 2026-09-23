# R-2.2 — Mapa Documental Global del Repositorio

> **Archivo:** `R2-GLOBAL-DOCUMENTATION-MAP.md`
> **Fase:** FASE R-2 — COMPLETE PROJECT DOCUMENTATION & ECOSYSTEM ARCHITECTURE
> **Fecha:** 2026-09-22 — Modo SOLO DOCUMENTAL (read-only)
> **Clasificación:** [VERIFICADO] — mapa construido por inspección directa del árbol de archivos.

---

## 0. Propósito

Índice completo y navegable de **toda la documentación del proyecto** (repo iterativo activo), en qué
fase se produjo, qué tipo de documento es, y dónde empieza un investigador nuevo. Complementa a
`PROJECT-DOCUMENTATION-STATUS.md` (raíz, estado por elemento del ecosistema) — este mapa documenta lo
**que existe**, el otro lo que **falta/está diseñado/ejecutado**.

Abreviatura de tipos: **REP** = reporte de resultados, **DISEÑO** = documento de diseño (no ejecutado),
**PLAN** = plan de ejecución, **ESTADO** = estado del proyecto, **REF** = referencia/datos,
**AUDIT** = auditoría, **CIERRE** = documento de conocimiento concluido.

---

## 1. Raíz del repositorio (`/home/lucas/Escritorio/RX550_Iterative_Research/`)

| Archivo | Tipo | Contenido / rol |
|---|---|---|
| `README.md` | ÍNDICE | Punto de arranque: qué es el directorio, cómo empezar, archivos de investigación cerrados, datos crudos, estado del sistema |
| `MASTER-PLAN.md` | PLAN/ESTADO | Plan maestro: roadmap FASE K/Q, arquitectura conceptual del ecosistema, Protocolo GPU Ownership, ciclo de vida de tecnologías, principio fundamental, FASE E–J, Capa Transversal (sección final) |
| `MASTER-RESEARCH-STATUS.md` | ESTADO | **Punto único de entrada** (v2.5): qué sabemos/invalidado/no reproducible/hipótesis/desconocido/experimentos autorizados/fases R-0/R-1/CONGELADO/artefactos clave/reglas de seguridad/próxima acción |
| `FINAL-RESEARCH-STATUS.md` | ESTADO | Estado final del cierre 19/09 (histórico) |
| `RX550_BUILD_SPECIFICATION.txt` | SPEC | Especificación de build rx550-torneo (45 secciones, 444 líneas): hardware, arquitectura, Mesa, instrumentación, metodología, perfiles, seguridad |
| `PROJECT-DOCUMENTATION-STATUS.md` | ESTADO | **ÍNDICE CENTRAL R-2** (creado en R-2.24): estado por elemento del ecosistema completo |
| `knowledge.md` | CIERRE | Conocimiento verificado (identidad/sistema, reproducible, Mesa, operacional, histórico) |
| `hypotheses.md` | CIERRE | Hipótesis confirmadas/descartadas/no reproducibles/activas |
| `open_questions.md` | CIERRE | Preguntas abiertas al cierre 19/09 |
| `decisions.md` | CIERRE | Decisiones tomadas al cierre 19/09 |
| `evidence.md` | CIERRE | Episodios, números reproducibles, datos históricos no reproducidos |
| `rejected_ideas.md` | CIERRE | Ideas rechazadas/refutadas |
| `research_log.md` | CIERRE | Bitácora de sesiones (17–20/09) |
| `experiments_proposed.md` | CIERRE | Experimentos propuestos/ejecutados/bloqueados/traspaso a rx550-torneo |

---

## 2. Capa de experimentos (`experiments/`)

### 2.1 FASES A–C y rápidos (históricos 19/09 + disjunción)

| Artefacto | Tipo | Contenido |
|---|---|---|
| `fase-a-discriminacion-20260919-114241/RESULTADOS-FASE-A.md` + `INVALIDACION-corridas-04-09.md` | REP/AUDIT | FASE A (histórica): discriminación de cargas; invalidación de corridas 04-09 |
| `fase-b-cap-probe-20260919-122038/RESULTADOS-FASE-B.md` | REP | FASE B cap-probe (histórica): cap 25/28/32/35 W → 25W NO liga SCLK |
| `fase-b-cap-probe-20260919-122038/EP08-auditoria-telemetria-E1E3.md` | AUDIT | EP-08: telemetría E1/E3 midió RX 550 real (REFUTA la hipótesis iGPU) |
| `ep05-mesa-custom-20260919-212249/RESULTADOS-EP05.md` | REP | EP-05: Mesa CUSTOM A/B → CUSTOM=STOCK en 3 escenas |
| `ep06-soak-cap-20260919-205645/RESULTADOS-EP06.md` | REP | EP-06: soak 71°C + cap 25W no reproduce régimen E1/E3; draw máx 13.6 W |
| `EXPLORATORIO-GravityMark/runs/RESULTADO.md` + `RESULTADO-Superposition.md` | REP | Exploratorio GravityMark y Superposition (puente hacia FASE C) |
| `R-14-SUPERPOSITION-DISSECTION/R-14-SUPERPOSITION-DISSECTION.md` | REP | **FASE C**: disección Superposition: 22.31 W steady / 24.71 W pico, score 804, OpenGL, +6.5 W vs E-03 |
| `M1-cap-35-30/RESULTADOS-M1.md` + `TELEMETRY-SCHEMA.md` | REP/REF | **M1**: vkmark 35/30W pareado: 12.27 W @35W → NO DISCRIMINATIVO; 10 runs, hashes sha256 |
| `AUDIT-001/AUDIT-001.md`, `ERRATA.md`, `METRICS-DEFINITIONS.md`, `EVIDENCE-MATRIX.md` | AUDIT | Auditoría completa del cierre: erratas 001–005, definiciones de métricas |

### 2.2 POLARIS12-MAP (FASE B histórica, geografía del hardware/software)

| Artefacto | Tipo | Contenido |
|---|---|---|
| `POLARIS12-MAP/POLARIS12-MAP.md` | MAPA | Tabla maestra de subsistemas A–AJ |
| `POLARIS12-MAP/HARDWARE-ROUTES.md` | MAPA | Rutas de hardware |
| `POLARIS12-MAP/SOFTWARE-CAPABILITIES.md` | MAPA | Capacidades de software/telemetría |
| `POLARIS12-MAP/EXPERIMENT-CANDIDATES.md` | CANDIDATOS | **Candidatos GEO-01..08 (FASE F)** + checklist Regla 19 |
| `POLARIS12-MAP/UNVERIFIED-CLAIMS.md` | AUDIT | Afirmaciones no verificadas |

### 2.3 FASE D — Performance Counters (audio, diseño y ajustes)

| Artefacto | Tipo | Contenido |
|---|---|---|
| `FASE-D-COUNTERS-AUDIT/FASE-D-COUNTERS-AUDIT.md` | REP | Etapa 1: auditoría read-only de contadores (UMR+radeontop funcionales, catálogo A/B/C/D) |
| `FASE-D-COUNTERS-AUDIT/FASE-D-ETAPA-2-PLAN.md` | PLAN | Etapa 2: contraste pareado A/B |
| `FASE-D-COUNTERS-AUDIT/FASE-D-ETAPA-2-RESULTADOS.md` (+ §12 corregido R-1.3) | REP | Etapa 2: A 22.25 W steady vs B 15.78 W, ratio 1.41; geometría/vertex+export |
| `FASE-D-COUNTERS-AUDIT/FASE-D-ETAPA-2-AUDIT.md` | AUDIT | Auditoría etapa 2: 2 errores objetivos de documentación, conclusiones intactas |
| `FASE-D-COUNTERS-AUDIT/FASE-D-ETAPA-3-PLAN.md` / `-PRECHECK.md` / `-EVENTS.md` | PLAN/DISEÑO | Etapa 3 DISEÑADA (contadores programados + SPM), NO ejecutada |
| `FASE-D-COUNTERS-AUDIT/FASE-D-GFX8-EVENT-ID-AUDIT.md` | AUDIT | Auditoría de Event IDs GFX8 (Conclusión B + adenda §14 R-1.2) |
| `FASE-D-COUNTERS-AUDIT/runs/` | REF | Corridas etapa 2 (A1..B3, journal/metadata/stdout) + muestras radeontop/UMR |

### 2.4 FASE R-0 — External Knowledge Recovery (COMPLETADA 22/09)

| Artefacto | Tipo | Contenido |
|---|---|---|
| `FASE-R0-EXTERNAL-KNOWLEDGE/FASE-R0-EXTERNAL-KNOWLEDGE-FINAL-REPORT.md` | REP | Informe final R-0 |
| `R0-1-GFX8-EVENT-IDS.md` + `R0-1-GFX8-EVENT-ID-REFERENCE.txt` | REF | Event IDs GFX8 desde GPUPerfAPI v3.11.1 (2304 eventos; GRBM=2 GUI_ACTIVE, SQ=4 WAVES VALIDADOS) |
| `R0-2-POWERPLAY-MCLK-SMU7.md` | REF | Política MCLK smu7 para bus 128-bit (mclk_up 5 / down 16 / activity 20) |
| `R0-3-MESA-WORKAROUNDS-POLARIS12.md` | REF | Workarounds Mesa que aplican a Polaris12 (msaa_sample_loc, LINE_FILTER_DISABLE, driconf) |
| `R0-4-ARCHITECTURE-LEXA-POLARIS12.md` | REF | Lexa/Polaris12: 512 SP/32 TMU/16 ROP/128-bit/50W/14nm/2.2B transistores |
| `R0-5-BENCHMARKS-EXTERNOS-RX550.md` | REF | Benchmarks externos RX550 (contexto, no adoptados) |
| `R0-6-HERRAMIENTAS-HISTORICAS-GFX8.md` | REF | GPUPerfAPI v3.11.1 = única fuente abierta con tablas GFX8; CodeXL EOL; RGP sin GFX8; UMR sin eventos |

### 2.5 FASE R-1 — Documentation Reconciliation (COMPLETADA 22/09)

| Artefacto | Tipo | Contenido |
|---|---|---|
| `FASE-R1-DOCUMENTATION-RECONCILIATION/R1-1-GFX8-EVENT-RECONCILIATION.md` | AUDIT | Reconcil. conteos GFX8: CB 396 vs 405, SQ 299 vs 273, MC 33 vs 22 → PARTIALLY_RECONCILED; 20/22 bloques; MC UNRESOLVED |
| `R1-5-DOCUMENTATION-STATUS.md` | ESTADO | Mapa documental A–R-1 |
| `R1-6-EVIDENCE-STATE-MODEL.md` | AUDIT | Modelo de estados de evidencia |
| `R1-7-CRITICAL-GAPS.md` | AUDIT | Gaps críticos |
| `R1-8-CROSS-CUTTING-AUDIT.md` | AUDIT | Capa transversal KERNEL/DRIVER (read-only ops) |
| `R1-9-E-J-READINESS.md` | AUDIT | Readiness E–J |
| `R1-10-NON-AUTHORIZED-ACTIONS.md` | AUDIT | Acciones NO autorizadas |
| `FASE-R1-FINAL-REPORT.md` | REP | Informe final R-1 + checklist |

### 2.6 WORKLOAD-SINTETICO (repositorio de workload Vulkan)

| Artefacto | Tipo | Contenido |
|---|---|---|
| `WORKLOAD-SINTETICO/README.md` | ÍNDICE/DISEÑO | Prototipo mínimo Vulkan COMPUTE; selección estricta 1002:699f; parámetros; estado PENDIENTE de validación per se |
| `WORKLOAD-SINTETICO/DESIGN-GRAPHICS.md` | DISEÑO | Diseño de workload GRÁFICO (2ª fase, no implementado): objetivo draw ≥27 W @35W discriminativo; 2 metas operativas; criterios de clasificación |
| `WORKLOAD-SINTETICO/RESEARCH.md` | REF/PLAN | RESEARCH R-01: specs Polaris12; planes de búsqueda |
| `WORKLOAD-SINTETICO/ESCALADO-E03.md` | REP | Escalado de E-03 (registro) |
| `WORKLOAD-SINTETICO/runs/exploratorio-{01,02,03,03-corrected}/` | REF | Corridas E-01/E-02/E-03 (00: preliminares, 03-corrected = VERIFICADO) |
| `WORKLOAD-SINTETICO/runs/escalado-01/` | REF | ES-01: ejes A0/D2 (overdraw, fma, tex, msaa), E1 (combo), F2 (fetch) |
| `WORKLOAD-SINTETICO/main`, `main-graphics`, `Makefile`, `src/` | CÓDIGO | Código del workload (CONGELADO) |

### 2.7 FASE R-2 (este directorio — COMPLETE PROJECT DOCUMENTATION & ECOSYSTEM)

| Artefacto | Tipo | Contenido |
|---|---|---|
| `R2-HISTORICAL-EXPERIMENT-INVENTORY.md` (R-2.1) | AUDIT | Inventario E0–E5 (dos familias) |
| `R2-GLOBAL-DOCUMENTATION-MAP.md` (R-2.2) | MAPA | Este documento |
| FASE-E…Q de diseño (R-2.3..R-2.13, R-2.18..R-2.20) | DISEÑO | Ver `FASE-R2-FINAL-REPORT.md` para índice |
| `EXPERIMENT-PRIORITY-MATRIX.md` (R-2.8) | DISEÑO/PLAN | Matriz de prioridad de experimentos |
| `SYNTHETIC-WORKLOAD-DESIGN.md` (R-2.9) | DISEÑO | Diseño del lab de workloads sintéticos |
| `R2-DEPENDENCY-GRAPH.md` (R-2.21) | MAPA | Grafo de dependencias del ecosistema |
| `FASE-R2-FINAL-REPORT.md` | REP | Informe final R-2 (apartados A–O) |
| `projects/{BERRETA,GHOST,RX-COMPRESSION-ENGINE,ORCHESTRATOR}/` | DISEÑO | Proyectos propios (diseño, NO implementado) |

---

## 3. `rx550-torneo/` — único proyecto implementado

| Artefacto | Tipo | Contenido |
|---|---|---|
| `rx550-torneo/README-FASE1.md` | ÍNDICE | Fase 1: 65/65 checks (detección, separación Intel/RX550, state_manager, failsafe) |
| `rx550-torneo/README-FASE2.md` | ÍNDICE | Fase 2: 55/55 checks (write-test power/control, rollback verificado) |
| `rx550-torneo/README-FASE3.md` | ÍNDICE | Fase 3: 56/56 checks (perfiles balanced/locked/25W/experimental `--danger`) |
| `rx550-torneo/README-M1.md` | ÍNDICE | M1: 112/112 checks (10 runs pareados, hashes inmutables) |
| `rx550-torneo/rx550-torneo` | CÓDIGO | Ejecutable bash read-only de Fase 1 |
| `rx550-torneo/src/rx550_torneo` | CÓDIGO | Código fuente |
| `rx550-torneo/tests/` | CÓDIGO | Tests |

---

## 4. Backup histórico (`RX550_Modo_Torneo_Backup_2026-09-19_0836/`)

No forma parte del repo activo; contiene la sesión 17/09 (Familia "E") y barridos del 18/09. Ver
`R2-HISTORICAL-EXPERIMENT-INVENTORY.md` §2/§4 para el inventario detallando:
`mesa-e1-…170430`, `mesa-e2-…175132|175301`, `mesa-e3-…213646` (con `e4/`, `e5/`, `e5b/`, `m1/raw/`),
`mesa-resolution-…113618|135118`, `mesa-ab-results-…101506|103427`, `mesa-p1/p2-…`,
`rx550-power-sweep-…132309|140527`.

---

## 5. Rutas de navegación recomendadas para un investigador nuevo

1. `README.md` (raíz) → 2. `MASTER-RESEARCH-STATUS.md` (v2.5, punto único de entrada) → 3.
   `PROJECT-DOCUMENTATION-STATUS.md` (índice R-2) → 4. Por tema:
   - **Contadores/GFX8:** `FASE-D-COUNTERS-AUDIT/` + `FASE-R0…R0-1` + `R1-1` + `FASE-M…-DESIGN`
   - **Workloads/potencia:** `WORKLOAD-SINTETICO/` + `R-14-SUPERPOSITION-DISSECTION` + `M1-cap-35-30`
   - **Historial E:** `R2-HISTORICAL-EXPERIMENT-INVENTORY.md`
   - **Roadmap/ecosistema:** `MASTER-PLAN.md` §K + `FASE-N-ECOSYSTEM-ARCHITECTURE.md`
   - **Proyectos propios:** `projects/` (BERRETA, GHOST, RX-COMPRESSION-ENGINE, ORCHESTRATOR)

---

## 6. Conclusión del mapa

- La documentación está distribuida en 4 capas: raíz (cierre 19/09 + estado), `experiments/`
  (fases A–D, R-0, R-1, WORKLOAD-SINTETICO), `rx550-torneo/` (implementación), y backup (histórico 17-18/09).
- Con la FASE R-2 se añade: capa `experiments/FASE-R2-PROJECT-DOCUMENTATION/` (diseños E–Q + informes)
  y capa `projects/` (diseños de proyectos propios), cerrando el inventario documental completo del
  ecosistema.