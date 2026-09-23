# MASTER-RESEARCH-STATUS.md — Estado Único del Proyecto

**ESTADO ACTUAL:** 2026-09-23 — **FASE R-4B — EXP-F4-A GOVERNOR READ-ONLY — S1 v2.2 FINALIZADA; PHASE 2 CLASIFICADA `DIAGNOSTIC / THERMALLY CONFOUNDED — NOT FOR VERDICT`; PROPUESTA v2.3 PREPARADA (NO EJECUTADA); MINI-TEST 7.3-B (RAMP CON GOVERNOR) EJECUTADO N=2 (read-only) — RESULTADO: DIST no cabe íntegro desde ≤50 °C (ramp real 0.246–0.252 °C/s; entrada ≤35 °C lo habilitaría según 7.3-A)**: tras PARADA D de la S1 v2.1 (histéresis 58.3 % por throttling térmico 92 °C/SCLK 551), se caracterizó el problema térmico en investigación read-only (`FASE-R4B-THERMAL-TEST`: ramp 0.31 °C/s, recuperación ≤50 °C en 255–270 s, Kalm NO intervino) y se relanzó la S1 bajo **protocolo v2.2** (única variación documentada formalmente ANTES de ejecutar: cooldown pasivo entre passes p1→p2→p3, condición telemétrica `temp ≤50 °C s30s ∧ SCLK nv0 ∧ P<4 W`, tiempos reales 180 s/225 s). Resultado: **15/15 bloques con SCLK 1071 MHz sostenido en los 3 passes** (T_max 86 °C, sin degradación), histéresis **0.26 % → GATEs PASS**, **FREEZE T=9.168 ms, s\*=0.75 (sha256 `6b6d6952…`)**, Phase 2 8/8 trials ejecutados. **Clasificación formal Phase 2: `DIAGNOSTIC / THERMALLY CONFOUNDED — NOT FOR VERDICT`** — auditoría de timestamps: contaminación por **temperatura acumulada** (Phase 2 heredó 84 °C de Fase 1 y 91–92 °C entre trials; causa conocida ≥92 °C de N=2, no duración de trial); R1–R7 NO declarados (ni PASS ni FAIL); Fase 1/FREEZE conservados íntegros. **Propuesta v2.3 lista en `EXP-F4-A-PROTOCOL-v2.3-PROPUESTA.md`** (cooldown telemétrico entre cada trial de Phase 2; FIXED/GOV enteros; DIST con 3 opciones 7.3-A/B/C; sin segmentación). **S2 NO iniciada — pendiente de autorización explícita y elección de opción DIST. Sin veredicto global.** Datos en `experiments/FASE-R4B-GOVERNOR/results/session1-v22/` (S1-v2.1 original intacta en `results/session1/`). Antece: FASE R-4C COMPLETADA (jitter TAA, NIVEL A MAE=0.0px, NIVEL B MAE=3.66×10⁻¹⁰px desde matriz host-visible; 8/8 celdas PASS; ANV sin devices → NO EJECUTADO); FASE R-4A COMPLETADA (enlace Gen2×4 VERIFIED por techo del root port 00:01.0, PCIe teórico 2.0 GB/s/sentido DERIVED, VRAM teórica 96–112 GB/s ESTIMATED, ratio enlace/VRAM corregido ×48–80, real UNKNOWN); FASE R-3.1 COMPLETADA (7 fusiones, 0 PROVEN NOVEL, FUSION-04 READY, FUSION-02/05/06 REJECTED, FUSION-07 BLOCKED); FASE R-3 y R-2 COMPLETADAS; R-1/R-0 COMPLETADAS (GRBM GUI_ACTIVE=2, SQ WAVES=4 VALIDADOS GFX8); programación de contadores y toda escritura SIGUEN NO AUTORIZADAS; MASTER-PLAN NO modificado en R-3..R-4B)  
**Fecha última actualización:** 2026-09-23  
**Versión:** 2.13  
**Punto único de entrada del proyecto** — No reconstruir el estado leyendo otros archivos.

---

## 🟢 QUÉ SABEMOS (VERIFICADO / REPRODUCIBLE)

### Hardware / Sistema
- **RX 550** = Polaris12/GFX8, PCI `1002:699f`, amdgpu, card1. Display en Intel HD 4600 (card0).
- **power1_cap** = 35,000,000 µW (35 W) — valor actual, nunca escrito en sesión actual salvo restore EP-06.
- **DPM** = `auto`. SCLK nivel 7 = 1071 MHz (máximo DPM). MCLK nivel 2 = 1500 MHz (máximo DPM).
- **Mesa** = 26.2.2 (system). CUSTOM `/opt/mesa-26.2.2-rx550-haswell` existe pero NO usado salvo EP-05.
- **Kalm** = `kalmd.py`/`kalm-lite.py` activos (PIDs 4087/4086). `kalm-gpu.service` muerto.

### Experimentos y Resultados
| Experimento | Estado | Hallazgo Clave |
|---|---|---|
| **FASE B — cap-probe (histórica)** | **VERIFICADO** | Cap 25W NO liga SCLK (1071 MHz libre incluso a 71°C) |
| **EP-06 (soak + réplica)** | **VERIFICADO** | Régimen E1/E3 NO reproducible ni frío ni caliente; draw máx 13.6 W |
| **EP-05 (Mesa CUSTOM A/B)** | **VERIFICADO** | CUSTOM = STOCK para 3 escenas; no reproduce E5 |
| **EP-08 (auditoría E1/E3)** | **VERIFICADO** | E1/E3 midieron RX 550 real (amdgpu card1), NO iGPU |
| **M1 (vkmark 35/30W)** | **VERIFICADO** | 12.27 W @35W → NO DISCRIMINATIVO; ΔFPS=0, ΔSCLK=0, IC95% ΔPwr (-0.103, +0.060) |
| **E-03 Corregida (Diseño B)** | **VERIFICADO** | 13.4 W full / 15.75 W steady; MCLK 1500 activo (220/277); 0 faults |
| **ES-01 (Escalado A-D+E)** | **VERIFICADO** | A/B/C/D/E = SIN EFECTO potencia; auto-pacing fetch-bound |
| **F2 (8 fetches)** | **VERIFICADO** | 2× fetches = 2× frametime (112→222 ms), power INVARIANTE (15.76 vs 16.13 W) |
| **R-14 Superposition** | **VERIFICADO** | 22.31 W steady / 24.71 W pico; score 804; OpenGL, geometría real; +6.5 W vs E-03 |
| **FASE D etapa 1 (auditoría counters)** | **VERIFICADO** | UMR+radeontop funcionales (P12); catálogo contadores A/B/C/D; SPM necesario para texture/L2; perf sin HW counters |
| **FASE D etapa 2 (contraste A/B×3)** | **VERIFICADO + AUDITADO (v1.4)** | 6/6 runs válidos; A=22.25 W steady (score 804 replicado) vs B=15.78 W (fps 8.950 replicado); ratio 1.41; vgt/pa/sh ∞ y sx 1.51–1.60 → geometría/vertex+export fuente de la diferencia; mem_busy B>A (36 vs 25); SPI_CSQ=0 en 8408 lecturas (no probatorio read-only); RLC ~25 MHz cte (sin gating en steady). Auditoría `FASE-D-ETAPA-2-AUDIT.md`: 2 errores objetivos en informe (tabla radeontop §4 mezcla métodos; conteo SPI 3306→8408) — conclusiones centrales intactas |

> **Nota de nomenclatura (FASE B):** la letra `FASE B` tiene **dos usos históricos distintos** en este proyecto, ambos conservados literalmente y sin renombrar sus documentos originales:
> 1. **FASE B — cap-probe (histórica)** → `experiments/fase-b-cap-probe-20260919-122038/` (`RESULTADOS-FASE-B.md`): probe de power cap 25/28/32/35 W (19/09).
> 2. **FASE B — POLARIS12-MAP (histórica)** → `experiments/POLARIS12-MAP/` (`POLARIS12-MAP.md`): mapa de subsistemas A–AJ (09/20–21).
> Pertenecen a **líneas históricas distintas**; no constituyen una única secuencia lineal. La nomenclatura posterior (`FASE C` → R-14, `FASE D` → counters) NO debe interpretarse como continuación lineal de ninguna de las dos.

### Cuellos de Botella Identificados
- **Todos los workloads sintéticos Vulkan:** **Fetch-latency bound** (auto-pacing). SCLK 1071 fijo, MCLK 1500, mem_busy 36% steady. Más fetches/frame → menos fps → misma potencia.
- **ALU (FMA) y CB (MSAA):** NO son cuellos (B y D no cambian frametime/potencia).
- **Superposition (OpenGL, geometría real):** Rompe el patrón → **22.31 W steady / 24.71 W pico**; **mem_busy 24.6 %** (vs 35.9 % sintéticos); **VRAM 1.55 GB** vs 0.23 GB; **OpenGL/radeonsi** vs Vulkan/RADV. Diferencia = geometría/vertex/post-proceso real vs sintético.
- **FASE D etapa 2 (2026-09-21):** la diferencia **+6.5 W steady (A 22.25 vs B 15.78 W, ratio 1.41)** se correlaciona direccionalmente con el pipeline de geometría/vertex y export de shader: A vgt/pa/sh ≈ 29–39 % y sx 86 % vs vgt/pa/sh = 0 % y sx 57 % en B (fill/raster saturdo en ambos). `mem_busy` NO escala con potencia (B > A con A más potente) → el tráfico DRAM no es el motor principal. Sin clock-gating diferencial en steady (RLC ~25 MHz cte, SCLK/MCLK máximos en A y B). SPI_CSQ_WF_ACTIVE_COUNT = 0 read-only → no informativo sin programación.

### Infraestructura rx550-torneo
- **Fase 1:** 65/65 checks OK (detección, separación Intel/RX550, state_manager, failsafe).
- **Fase 2:** 55/55 checks OK (write-test controlado power/control, rollback verificado).
- **Fase 3:** 56/56 checks OK (perfiles balanced/locked/25W/experimental con `--danger`).
- **M1:** 112/112 checks OK (10 runs pareados, hashes sha256 inmutables).
- **Benchmarks instalados:** GravityMark 1.89, Superposition 1.1, Heaven 4.0, Valley 1.0 en `~/Escritorio/berchmark/instalados/` (hashes SHA-256 verificados).

---

## 🔴 QUÉ FUE INVALIDADO (con ERRATUM en `experiments/AUDIT-001/ERRATA.md`)

| Conclusión Anterior | ERRATUM | Nueva Clasificación |
|---|---|---|
| "Kalm limitó a 25W" | 001 | **INVALIDADO** — Régimen 25W ocurrió SIN kalm (17/09) |
| "Cap 25W liga SCLK" | 001 | **INVALIDADO** — Fase B + EP-06: cap 25W no liga SCLK |
| "25W = techo natural GPU" | 001 | **INVALIDADO** — power1_input era estimador SMU en estado regulatorio |
| "power1_input = potencia real" | 002 | **INVALIDADO** — Es estimador SMU; draw real máx 13.6 W (EP-06), 23.7 W pico (Superposition) |
| "Mesa CUSTOM causó E5" | 003 | **INVALIDADO** — EP-05 A/B: CUSTOM = STOCK; no reproduce E5 |
| "E1/E3 midieron iGPU" | 005 | **REFUTADO** — EP-08: telemetría = RX 550 (mem_info_* solo en amdgpu) |
| "13.40 W ≈ 15.75 W comparables" | 004 | **INVALIDADO** — Definiciones distintas (ventana completa vs régimen estable) |

---

## 🟡 NO REPRODUCIBLE (Histórico, NO es especificación operacional)

- **Régimen E1/E3/E5 completo (17/09/2026):** power1≈25W / SCLK 350-390 / MCLK 1250-1500 / 74-92°C / phong 1285 fps / desktop 443@1080 / jelly 691@35W.
  - Ningún parámetro autorizado (cap, calor, kalm, Mesa stock o CUSTOM) lo reprodujo.
  - Causa raíz = **DESCONOCIDA** sin autorización nueva.

---

## 🟠 HIPÓTESIS (Candidatas sin confirmar)

| Hipótesis | Evidencia Parcial | Estado |
|---|---|---|
| **Auto-pacing GPU / Fetch-latency bound** | ES-01 + F2: frametime ∝ fetches, power/mem_busy invariantes | **SUSTENTADA** por ES-01 + F2 |
| **Clock-gating anula trabajo extra** | Whitepaper Polaris "fine grained clock gating" + ES-01/F2 power invariante | **COHERENTE** |
| **MCLK 1500 requiere presión memoria real** | Superposition (MCLK 300-1500) vs sintético (MCLK 1500 solo con 4× tex 4096²) | **PARCIAL** |
| **Régimen 17/09 = estado térmico previo + MCLK push** | EP-06: soak 71°C + cap 25W no reproduce; draw máx hoy 13.6W | **CANDIDATA** |

---

## ⚫ DESCONOCIDO (Gaps Críticos)

| Gap | Descripción | Prioridad |
|---|---|---|
| **Causa raíz régimen 17/09** | Qué disparó SCLK 350 / MCLK 1250 / 25W en sesión 17/09 | **ALTA** |
| **MCLK sostenido 1250-1500** | Qué lo dispara (hoy solo 625 + picos transitorios) | **ALTA** |
| **Draw real máximo** | Límite térmico/eléctrico real (>13.6 W medidos EP-06; 23.7 W pico Superposition) | **ALTA** |
| **Costo real DRAM / mem_busy** | `mem_busy` ≠ % bandwidth; necesidad contadores HW reales | **ALTA** |
| **Bottleneck GL 640p** | CPU submissions vs present vs VRAM/GTT | **MEDIA** |
| **DCC behavior real** | ¿Superposition usa DCC? ¿Nuestro CB lo deshabilita? | **MEDIA** |
| **PowerPlay internals** | ppfeaturemask, DPM niveles intermedios, voltage behavior | **MEDIA** |
| **Origen "phong 1285 fps"** | ¿Era otra ventana/superficie? | **BAJA** |
| **PCIe x8 vs x4** | Link width/speed negociado real | **BAJA** |
| **BIOS/fuses CUs** | Unidades deshabilitadas: fuse/BIOS/físico | **BAJA** |

---

## 🔵 EXPERIMENTOS AUTORIZADOS (Próximos Pasos)

| Fase | Objetivo | Estado |
|---|---|---|
| **FASE B — POLARIS12-MAP (histórica)** — `experiments/POLARIS12-MAP/` | Mapa completo subsistemas A–AJ (hardware/software/capacidades) | **COMPLETADA** |
| **FASE C** — `R-14-SUPERPOSITION-DISSECTION.md` | Dissección Superposition (22.31 W steady, 24.7 W pico, score 804) | **COMPLETADA** |
| **FASE D** — Performance Counters | Etapa 1 (auditoría read-only) **COMPLETADA**. Etapa 2 (contraste pareado A/B×3) **COMPLETADA** → informe `FASE-D-COUNTERS-AUDIT/FASE-D-ETAPA-2-RESULTADOS.md`; H1 APOYADA, H4 parcial, H8 gating descartado. Etapa 3 (contadores programados + SPM) **DISEÑADA** (`FASE-D-ETAPA-3-PLAN.md`), **PRECHECK completado** (`FASE-D-ETAPA-3-PRECHECK.md`), **etapa 3: eventos investigados** (`FASE-D-ETAPA-3-EVENTS.md`) y **Auditoría de Event IDs GFX8 completada** (`FASE-D-GFX8-EVENT-ID-AUDIT.md`); programación permanece NO autorizada. | **EN CURSO** |
| **FASE E** — Real-Game Baseline | Juego reproducible, offline, ≥30s, RX 550 explícita, misma telemetría | **PENDIENTE** |
| **FASE F** — Geometry Investigation | Documentar candidatos GEO-01..08, seleccionar mayor valor informativo | **PENDIENTE** |
| **FASE G** — Memory/VRAM/GTT | Modelo tráfico memoria + comparación contadores/sysfs | **PENDIENTE** |
| **FASE H** — RADV/Workarounds | Investigar individualmente (shrink_image_store, wait_for_vm_map, etc.) | **PENDIENTE** |
| **FASE I** — PowerPlay/DPM | pp_power_profile_mode, ppfeaturemask (0xfff7bfff), DPM intermedios | **PENDIENTE** |
| **FASE J** — Priority Matrix | `EXPERIMENT-PRIORITY-MATRIX.md` con justificación por evidencia | **PENDIENTE** |
| **FASE K** — POLARIS12 Performance Laboratory | Roadmap post-FASE D (PLANIFICADA): framework reproducible de caracterización/experimentación (estructura común, telemetría unificada, benchmarks A/B reproducibles, clasificación de bottlenecks con niveles de evidencia, experimentos SHD/FRAG/GEO/MEM, analizador K8 solo planificado). Ver `MASTER-PLAN.md` §K | **PLANIFICADA** |
| **FASE L** — RX550-Tuner | Búsqueda experimental (futura, dependiente de FASE K) de configuraciones PowerPlay/perfiles RX 550: perfiles, límites de potencia, clocks, benchmarks, búsqueda controlada, comparación estadística, validación, reversibilidad. Ver `MASTER-PLAN.md` §K | **PLANIFICADA** |
| **FASE M** — GFX8 Counter Research | Recuperar Event IDs GFX8 desde fuentes históricas/primarias (GPUPerfAPI, CodeXL, RGP/VI) sin afirmar su contenido hasta verificar; **GRBM_PERFCOUNTER0_SELECT=0x2 (GUI_ACTIVE) y SQ PERF_SEL=0x4 (WAVES) ahora DOCUMENTADOS/VERIFICADOS para GFX8 por GPUPerfAPI v3.11.1 (FASE R-0, R0-1) y reconciliados con la documentación local (R1-1)**; sin programación de contadores (sigue NO autorizada). Independiente. Ver `MASTER-PLAN.md` §K | **PLANIFICADA** |

### FASE R-0 — EXTERNAL KNOWLEDGE RECOVERY (COMPLETADA 2026-09-22)

Línea documental SOLO READ-ONLY que **resuelve el gap crítico de event IDs GFX8**:

- **R-0.1 RESUELTO [VERIFICADO/ALTA]: la tabla de eventos PERF_SEL de GFX8/Polaris12 existe en
  `GPUOpen-Tools/gpu_performance_api` tag `v3.11.1`** (catálogos autogenerados AMD). Valores
  validados: **GRBM PERF_SEL=2 (GUI_ACTIVE)** y **SQ PERF_SEL=4 (WAVES)** — ambos ahora como
  VERIFICADO PARA GFX8 (refrendan las constantes RADV). 2304 contadores expuestos extraídos a
  `experiments/FASE-R0-EXTERNAL-KNOWLEDGE/R0-1-GFX8-EVENT-ID-REFERENCE.txt`; docs por tema en el
  mismo directorio. GPUPerfAPI v4.0+ ELIMINÓ soporte GCN → usar v3.11.1.
- **R-0.2 [VERIFICADO]:** política DPM MCLK smu7 para bus 128-bit (Polaris12) = `mclk_up_hyst=5,
  `mclk_down_hyst=16`, `mclk_activity=20`, gate `chip_id >= POLARIS10` (kernel `smu7_hwmgr.c`) —
  coincide con R-07 local.
- **R-0.3 [VERIFICADO]:** radeonsi `has_msaa_sample_loc_bug` incluye **POLARIS12**;
  `LINE_FILTER_DISABLE(family<=POLARIS12)`; driconf `clear_db_cache_before_clear`.
- **R-0.4/R-0.5 [VERIFICADO]:** Lexa/Polaris12 512 SP/32 TMU/16 ROP/128-bit/50W/14nm/2.2B
  transistores/101 mm²; RX550 8 CUs; referencia de benchmarks externos.
- **R-0.6 [VERIFICADO]:** catálogo de herramientas históricas — GPUPerfAPI v3.11.1 = única fuente
  abierta con tablas GFX8 hoy; UMR solo registros (sin eventos), confirmado.
- **Resultado B de FASE-D ACTUALIZADO:** «IDs GFX8 no verificables con fuentes locales» →
  «IDs GFX8 VERIFICABLES vía GPUPerfAPI v3.11.1 (no locales); recuperados documentalmente».
- **Blanco intacto:** programación de contadores y toda escritura siguen **NO AUTORIZADAS**;
  congelados intactos (KDE, BIOS/VBIOS); no se instaló ni escribió nada en el sistema.

### FASE R-1 — DOCUMENTATION RECONCILIATION & MASTER CONSOLIDATION (COMPLETADA 2026-09-22)

Fase SOLO DOCUMENTAL (read-only) que reconcilia la documentación acumulada (A–R-0) para dejar el
repositorio internamente coherente antes de M/J/L/E–J. Entregables en
`experiments/FASE-R1-DOCUMENTATION-RECONCILIATION/`:

- **R-1.1** `R1-1-GFX8-EVENT-RECONCILIATION.md` — reconciliación conteos GFX8 GPUPerfAPI v3.11.1 (CB 396/SQ 299/
  MC 33) vs Mesa groups_VI (CB 405/SQ 273/MC 22) → **PARTIALLY_RECONCILED**; coherencia estructural **20/22
  bloques** con coincidencia exacta; semántica/unidad de MC **UNRESOLVED** (no diseñar normalización MC).
- **R-1.2** `FASE-D-GFX8-EVENT-ID-AUDIT.md` §14 — Resultado B cruzado con R-0 (fuente local vs fuente AMD añadida).
- **R-1.3** `FASE-D-ETAPA-2-RESULTADOS.md` §12 — correcciones de la auditoría aplicadas (tabla radeontop método
  declarado, SPI 3306→8408) sin tocar conclusiones.
- **R-1.4** este documento → **v2.5** (historia preservada, contradicciones resueltas vía adenda, no borrado).
- **R-1.5** mapa documental A–R-1 · **R-1.6** modelo de estados de evidencia · **R-1.7** gaps críticos ·
  **R-1.8** capa transversal KERNEL/DRIVER read-only (L.0 Capability Audit ppfeaturemask, pp_od_clk_voltage,
  pp_dpm edge cases) · **R-1.9** readiness E–J · **R-1.10** acciones NO autorizadas;
  **R-1.15** informe final + checklist §14.
- **Constante:** la programación de contadores y toda escritura del sistema SIGUEN **NO AUTORIZADAS**.

### FASE R-2 — COMPLETE PROJECT DOCUMENTATION & ECOSYSTEM ARCHITECTURE (COMPLETADA 2026-09-22, SOLO DOCUMENTAL/DISEÑO)

Fase SOLO DOCUMENTAL Y DE DISEÑO (sin ejecución) que documenta el **trabajo pendiente del ecosistema
completo** (no solo RX550/GFX8), con separación rigurosa de estados (DOCUMENTADO/DISEÑADO/PLANIFICADO/
HIPÓTESIS/UNVERIFIED/BLOCKED/NO AUTORIZADO…) y sin convertir nombres provisionales en tecnologías.
Entregables en `experiments/FASE-R2-PROJECT-DOCUMENTATION/`:

- **R-2.1** `R2-HISTORICAL-EXPERIMENT-INVENTORY.md` — E1/E2/E3/E4/E5/E5b EXISTEN en el backup Torneo
  (sesión 17/09); **E0 = NOT FOUND** como artefacto (solo 2 referencias textuales; datos plausibles sin
  etiquetar en `mesa-resolution-2026…113618|135118`); Familia 2 (E-01/E-02/E-03/ES-01/F2) VERIFICADA
  reproducible. Dos familias "E" distintas, no mezclables.
- **R-2.2** `R2-GLOBAL-DOCUMENTATION-MAP.md` + **R-2.24** `PROJECT-DOCUMENTATION-STATUS.md` (raíz):
  navegación completa del repositorio y estado por elemento del ecosistema.
- **R-2.3..R-2.7 + R-2.10..R-2.13 + R-2.18..R-2.20** — diseños formales `FASE-E…Q…-DESIGN.md`
  (baseline de juego real BLOQUEADA por falta de juego reproducible autorizado; GEO-01..08; modelo de
  memoria G-M1..G-M5; workarounds H-1..H-7; PowerPlay/DPM I-1..I-5; Lab K1..K10; Tuner L; contadores M;
  ecosistema N; gestores O; FG/upscaling P; Mesa Q).
- **R-2.8** `EXPERIMENT-PRIORITY-MATRIX.md` (matriz J, 10 criterios → ALTA/MEDIA/BAJA/BLOQUEADOS).
- **R-2.9** `SYNTHETIC-WORKLOAD-DESIGN.md` (8 modos sobre el prototipo CONGELADO).
- **R-2.14..R-2.17** `projects/BERRETA|GHOST|RX-COMPRESSION-ENGINE|ORCHESTRATOR/*-DESIGN.md`
  (proyectos PROVISIONALES/IDEA, sin implementar; Ghost/RX-Comp dependen de FASE G).
- **R-2.21** `R2-DEPENDENCY-GRAPH.md` (grafo CONFIRMADA/PROBABLE/POTENCIAL).
- **R-2.22** MASTER-PLAN §S · **R-2.23** este documento (v2.6) · **R-2.25** `FASE-R2-FINAL-REPORT.md`.
- **Constante:** programación de contadores y toda escritura SIGUEN **NO AUTORIZADAS**; nada se ejecutó.

### FASE R-3 — ORIGINAL IDEAS, NOVELTY AUDIT & RESEARCH CANDIDATES (COMPLETADA 2026-09-22, SOLO DOCUMENTAL)

Fase SOLO DOCUMENTAL (investigación web; sin ejecución) que generó 10 ideas originales y las auditó contra
prior art. Entregables:

- **I-01..I-10** en `projects/TBDR-IMR|TEMPORAL-TILE-REUSE|JITTER-REPROJECTION|ROP-COMPUTE-OFFLOAD|
  GFX8-FRAME-RECORDER|GHOST-PREDICTIVE-CACHE|ASYNC-OPTICAL-FLOW|CLOSED-LOOP-QUALITY-GOVERNOR|
  L2-RESIDENT-RENDERING|ASYNC-AUX-RENDERER/` (README + prior-art + diseño + riesgos por idea, 40+ docs).
- **`R3-NOVELTY-MATRIX.md`** — clasificación por prior art (escala KNOWN…NOVELTY UNKNOWN); la mitad
  "residencia" de I-01/I-09 **CONTRADICTED BY PRIOR ART** (CB/DB bypass L2 GFX8); premisa "CUs libres"
  **CONTRADICTED**; I-02+I-03 (temporal tile-lock) = slice PARTIALLY NOVEL; único gap de herramienta real =
  I-05 (viewer SQTT GFX8, NOVELTY UNKNOWN). **0 ideas PROVEN NOVEL**.
- **`R3-FEASIBILITY-MATRIX.md`**, **`R3-DEPENDENCIES.md`**, **`R3-MASTER-PLAN-INTEGRATION-PROPOSAL.md`**
  (MASTER-PLAN NO modificado), **`FASE-R3-FINAL-REPORT.md`** (10 preguntas + checklist + recomendaciones).
- **Recomendaciones:** A (integrar): ninguna; B (research candidate): I-05, piezas async de I-04;
  C (hypothesis): I-02, I-03, I-06, I-08, I-10; D (más investigación): I-07 y sub-reclamo de I-09
  (condicionados); E (discard): I-01, I-09 headline, I-04 full-ROP.
- **Constante:** programación de contadores y toda escritura SIGUEN **NO AUTORIZADAS**; nada se ejecutó.

### FASE R-3.1 — FUSION ARCHITECTURE AUDIT (COMPLETADA 2026-09-22, SOLO LECTURA)

Auditoría READ-ONLY de las **7 fusiones** formadas por agrupación de las ideas de R-3. Entregables en
`experiments/FASE-R3-1-FUSION-ARCHITECTURE-AUDIT/`:

- **FUSION-01..07** (`FUSION-01-JITTER-DUAL-CONSUMER.md` … `FUSION-07-MINI-ENGINE.md`) — auditorías por fusión.
- **`ASSUMPTION-AUDIT.md`** — **20 premisas** clasificadas VERIFIED(1)/CONTRADICTED(9)/PARTIALLY VERIFIED(5)/
  PLAUSIBLE(2)/UNKNOWN(5)/REQUIRES EXPERIMENT(2). Claves: ROP saturación REQUIRES EXPERIMENT; 32×32≠unidad HW
  CONTRADICTED; framebuffer-en-L2 CONTRADICTED (bypass CB/DB); jitter≠motion vector CONTRADICTED; compute≠free
  CONTRADICTED como regla; DCC no ahorra PCIe CONTRADICTED; RGP Polaris PARTIALLY (RGP 1.x-era SÍ cubría GCN).
- **Matrices:** `NOVELTY-MATRIX.md`, `FEASIBILITY-MATRIX.md`, `DEPENDENCY-MATRIX.md` (D-3/layer/Mesa/kernel/
  RX-Compression/Ghost/BERRETA/Orquestador), `IMPLEMENTATION-LAYER-MATRIX.md` (ninguna FIRMWARE; kernel solo
  en F3/F4; F1/F4readonly/F6calib = únicas implementables hoy en APPLICATION/LAYER).
- **`EXPERIMENT-ROADMAP.md`** — diseños EXP-F1-A (jitter observable), EXP-F2-A (tile 16/32/64), EXP-F3-A
  (bandwidth real), EXP-F4-A (governor read-only), **EXP-F5-A (mínimo obligatorio de fusión 5)**, EXP-F6-A
  (concurrencia 8 CU). **NINGUNO ejecutado.**
- **`PRIOR-ART-INDEX.md`** — índice consolidado R-3⇄R-3.1 (incluye refutación de fuente LinuxReviews/DCC-PCIe).
- **`R3-1-MASTER-REPORT.md`** — 10 respuestas ejecutivas + checklist de cierre 21/21.
- **Veredictos de prioridad:** FUSION-04 (governor read-only) READY FOR FUTURE EXPERIMENT · FUSION-01/03
  NEEDS PRECONDITION · FUSION-02/05/06 REJECTED/FALSIFIED (versiones fuertes) · FUSION-07 BLOCKED/RESEARCH
  ONLY · FUSION-05 sub-pieza async → BERRETA ASY-01.
- **Constante:** programación de contadores y toda escritura SIGUEN **NO AUTORIZADAS**; MASTER-PLAN NO fue
  modificado durante R-3/R-3.1; R-3.1 solo actualizó este documento (v2.7).

### FASE R-4A — EXP-F3-A BANDWIDTH REAL (COMPLETADA 2026-09-22, READ-ONLY)

Precondición R-3.1 de FUSION-03 resuelta en modo solo-lectura (ni una escritura). Informe:
`experiments/FASE-R4A-BANDWIDTH-REAL/EXP-F3-A-BANDWIDTH-REAL.md`.

- **VERIFIED (sysfs):** enlace PCIe negociado **5.0 GT/s (Gen2) ×4** por techo del **root port 00:01.0**
  (max_link_speed 5.0 GT/s); tarjeta capaz de 8.0 GT/s ×8 pero la plataforma no lo permite. VRAM 2 GiB,
  VIS-VRAM **256 MiB**, GTT **6.2 GB** (=5.77 GiB). Cap 35 W, ~3.7 W ocio. mclk 300/625/1500 MHz, sclk hasta
  1071 MHz.
- **DERIVED:** Gen2×4 teórico = **2.0 GB/s por sentido** (20 GT/s ÷ 10, 8b/10b).
- **ESTIMATED:** payload PCIe efectivo ≈1.4–1.9 GB/s (overhead TLP); VRAM teórica **96–112 GB/s**
  (mclk 1500 × factor GDDR5 ×4 — cross-check R9 290/RX 480; módulo exacto UNKNOWN).
- **Corrección de modelo:** ratio enlace/VRAM pasa de ×24–32 (con 48 GB/s) a **×48–80**. Dirección de las
  conclusiones de FUSION-03 sin cambios; solo magnitud. Adenda escrita en FUSION-03.
- **UNKNOWN / REQUIRES FUTURE EXPERIMENT:** bandwidth REAL medido (amdgpu_benchmark bloqueado por permisos;
  su `.write` correría benchmarks → prohibido aquí); GTT no es constante (depende de DRAM del sistema); módulo
  GDDR5 6 vs 7 Gbps.
- **Constante:** programación de contadores y toda escritura SIGUEN **NO AUTORIZADAS**; no se creó workload,
  no se ejecutó benchmark; MASTER-PLAN intacto.

### FASE R-4C — EXP-F1-A JITTER OBSERVABILITY (COMPLETADA — harness ejecutado bajo autorización, 2026-09-22)

PRECHECK (diseño, verificado read-only) + **EJECUCIÓN COMPLETADA** tras autorización explícita. Todo local en
`experiments/FASE-R4C-JITTER-OBSERVABILITY/` (`harness/`, `results/`); capa vía `VK_LAYER_PATH` local; CERO
modificaciones al sistema; sin benchmarks de rendimiento. Entregables: `README.md`, `EXP-F1-A-JITTER-OBSERVABILITY.md`,
`PRECHECK-REPORT.md`, `PRIOR-ART.md`, y **`EXP-F1-A-RESULTADOS.md`** (resultados observados). Conclusión:

- **NIVEL A (canal directo vía `vkCmdPushConstants`): VERIFICADO por ejecución.** La capa intercepta el llamada
  y lee `pValues` en tiempo de recording → **MAE = 0.0 px (bit-idéntico a la GT)**, 320/320 frames medidos,
  Pearson 1.0, en RADV real (RX 550) y lavapipe.
- **NIVEL B (reconstrucción desde matriz de proyección FSR-consistente `M_jit=translate(jx_ndc,jy_ndc,0)·M_base`
  en UBO host-visible): VERIFICADO por ejecución.** La capa lee los dos slots, computa `T=projJit·inv(projBase)`
  y extrae `jx_px=T[12]·W/2`, `jy_px=−T[13]·H/2` → **MAE total = 3.66×10⁻¹⁰ px, máx error = 3.0×10⁻⁸ px**
  (piso FP32 de la ruta matriz), 320/320, Pearson 1.0.
- **MAE<0.01 px (PROVISIONAL TARGET): PASS con margen ~×10⁷** (0.01 px ÷ 3.66×10⁻¹⁰ px). El piso FP32 observado
  es incluso menor que la cota conservadora ~×50–500 del PRECHECK (matrices exactas, sin acumulación).
- **Matriz ejecutada:** NIVEL A/B × {RADV, lavapipe} × 2 réplicas = **8 corridas exitosas, deterministas**
  (ANV opcional NO EJECUTADO: sin devices físicos con `intel_icd.x86_64.json` — documentado, no como fallo).
- **Incidencias resueltas (documentadas en el informe):** `library_path` relativo→`dlopen` requiere
  `LD_LIBRARY_PATH` local; coexistencia con la implicit layer `VK_LAYER_MESA_device_select` (cadena `pNext`
  distingue link por `function==VK_LAYER_LINK_INFO`); `vkCreateDevice` se resuelve por instance-GPA, no por
  device-GPA con `VK_NULL_HANDLE`; PFN 1.4.341 sin `VkDevice` inicial en device/queue/cmd; gating de nivel con
  comparación a `"1"`.
- **Regla cumplida:** en ningún punto se concluye jitter = motion vector (el MV del harness es fijo e independiente).
- **Constante:** programación de contadores y toda escritura SIGUEN **NO AUTORIZADAS**; MASTER-PLAN intacto.

### FASE R-4B — EXP-F4-A GOVERNOR READ-ONLY (S1 v2.2 COMPLETADA 2026-09-23; Phase 2 clasificada DIAGNOSTIC/THERMALLY CONFOUNDED; PROPUESTA v2.3 lista; MINI-TEST 7.3-B EJECUTADO)

Precondición R-3.1 de FUSION-04 (governor **read-only**, único actuador = render-scale, sin contadores).
Documentación base: `experiments/FASE-R4B-GOVERNOR/` (`EXP-F4-A-PROTOCOL.md` v2.1, `PRE-FLIGHT-CALIBRACION-EXP-F4-A.md`,
`EXP-F4-A-RESULTADOS.md`).

- **S1 v2.1 (parada D, datos intactos en `results/session1/`):** 15/15 bloques open-loop → GATE de
  histéresis **FALLADO (58.3 %)** por throttling térmico (SCLK 1071→551 MHz a ~92 °C en p2/p3). El GATE §14-D
  protegió la corrida (sin FREEZE). Registro completo en `EXP-F4-A-RESULTADOS.md` §1B.
- **Investigación térmica read-only (`FASE-R4B-THERMAL-TEST/`):** caracterización A–J con N=2 réplicas —
  ramp 0.315/0.310 °C/s (±1.6 %), recuperación a ≤50 °C en 255–270 s, power_max 23.5 W < cap 35 W →
  throttling puramente térmico; Kalm audito (VERIFIED: NO interviene — kalmd 4087 solo afinidad IRQ,
  kalm-lite 4086 solo vm.*/proc, kalm-gpu.service muerto desde 18/09). Curvas, análisis y propuesta de
  cooldown en `RESULTADOS-TEST-TERMICO.md` + `analyze_thermal.py`.
- **Variación v2.2 (autorizada, documentada formalmente ANTES de ejecutar en `EXP-F4-A-PROTOCOL-v2.2.md`):**
  único cambio = cooldown pasivo entre passes de Fase 1 (p1→p2→p3), condición de retorno **telemétrica**
  `temp ≤50 °C sostenido ≥30 s ∧ SCLK nivel 0 ∧ P<4 W` (expectativa ~270 s NO asumida como tope; tiempos
  reales registrados). Workload, T, s*, escalas, thresholds, R1–R7, F1–F6, bloques y duraciones **sin
  cambios**.
- **S1 v2.2 ejecutada (`results/session1-v22/`):** **15/15 bloques con SCLK 1071 MHz sostenido en los 3
  passes** (sub-1071 1.2–1.5 % transitorios; T_max p2/p3 = 86 °C, nunca ~92 °C); **GATEs Fase 1 TODOS PASS
  (histéresis 0.26 %)**; **FREEZE T=9.168 ms, s*=0.75, sha256 `6b6d6952…`** (`fase1/manifest.json` +
  `frozen.sha256`); cooldowns reales **180 s** y **225 s**; **Phase 2 completa 8/8 trials** (orden
  `fixed gov fixed gov fixed gov dist dist`); integridad 15/15 + 8/8, DPM/kalm/cap pre↔post idénticos
  (hash `ff9e8280bd…`), journal sin eventos de subsistema → **sin writes**.
- **Diagnóstico formal de Phase 2 — clasificación `DIAGNOSTIC / THERMALLY CONFOUNDED — NOT FOR
  VERDICT`:** auditoría de timestamps (telemetría 10 Hz + governor_trace) demuestra que la causa es
  **temperatura acumulada**, no duración de trial: Phase 2 heredó 84 °C de Fase 1 (sin cooldown
  FREEZE→fixed1) y cada trial heredó 91–92 °C del anterior (sin cooldown entre trials) → SCLK
  551 MHz desde ~v0. Solo fixed1 conserva v0–v1 limpias; 0 de 8 trials íntegros. R1–R7 **NO**
  declarados con estos datos (ni PASS ni FAIL); Fase 1/FREEZE conservados íntegros. Detalle:
  `EXP-F4-A-RESULTADOS.md` §1C.5.
- **Propuesta v2.3 preparada (`EXP-F4-A-PROTOCOL-v2.3-PROPUESTA.md`), NO EJECUTADA:** cooldown
  telemétrico entre CADA trial de Phase 2 (condición DN-07 ≤50 °C s30s ∧ SCLK nv0 ∧ P<4 W);
  FIXED (60 s→≈69 °C) y GOV (120 s→≈87 °C) enteros desde ≤50 °C (margen bajo 90 °C verificado);
  DIST (200 s) con 3 opciones (entrada ≤40 °C / mini-test read-only de ramp con governor activo /
  marcación por ventana); regla por ventana `THERMALLY CONFOUNDED` (T>90 °C o SCLK<1071 → ventana
  excluida); segmentación RECHAZADA (invalida ventanas ancladas a t0 y steps internos +60/+120);
  auditoría de invariantes (T/s*/escalas/banda/R1–R7/F1–F6/workload/réplicas/governor/harness/
  analyze) sin cambios; duración estimada ~65–72 min/sesión. Respuestas A–I y evaluación de los 5
  esquemas de cooldown dentro.
- **Mini-test 7.3-B EJECUTADO (N=2 read-only, autorizado por el usuario 2026-09-23; NO forma
  parte de S2; datos en `FASE-R4B-THERMAL-TEST/runs/minitest-ramp-gov/rep{1,2}/`; plan
  `EXP-F4-A-MINITEST-RAMP-GOV-PLAN.md`, resultados `RESULTADOS-MINITEST-7.3-B.md`):** ramp con
  governor activo (governor.py sin tocar, T=9.168 ms) partiendo de DN-07 (≤50 °C). Respuestas
  A–I: governor responde correctamente a 1071 (LOWER/RAISE alineadas, latencias dentro de
  especificación, p99 trace == p99 frames en todas las ventanas → semántica temporal íntegra);
  **ramp efectiva 0.252 vs 0.246 °C/s (Δ=2.1 %, reproducible)**; **T_max=92 °C en ambas
  réplicas ANTES de completar los 200 s** (REP1 v9 degradada T≥90 a t≈172 s; REP2 v7–v9 T≥90 a
  t≈135 s, entrada 45 °C); SCLK 1071 sostenido solo en las ventanas limpias (REP1 v0–v7,
  REP2 v0–v5); 0 aborts, ±0 writes verificado (DPM/kalm/cap idénticos `ff9e8280bd`). **Conclusión
  per criterio: DIST NO puede ejecutarse íntegro desde ≤50 °C (opción 1 NO demostrada); con
  entrada ≤35 °C sería viable (7.3-A, t_90≈221 s>200 s); ≤40 °C queda en el filo (t_90≈201 s);
  7.3-C (marcación por ventana) como red de seguridad → R7 pasaría a DIAGNOSTIC NOT FOR VERDICT.
  NO se preparó v2.3-final; la elección 7.3-A/C y la autorización de S2 quedan PENDIENTES del
  usuario.**
- **Constante:** sesión 2 **NO iniciada** (detención solicitada tras S1 + tras mini-test;
  pendiente de autorización explícita y elección de opción DIST 7.3-A/C); **sin veredicto
  global**; programación de
  contadores y toda escritura SIGUEN **NO AUTORIZADAS**; MASTER-PLAN intacto.

| **FASE N** — Technology Naming & Architecture | Línea DOCUMENTAL (PLANIFICADA): inventario y nomenclatura oficial del ecosistema; clasificar proyectos/tecnologías/frameworks/herramientas/motores/perfiles/experimentos/investigaciones/benchmarks/documentación; tabla `Nombre oficial|tipo|objetivo|estado|dependencia|alias`; no implementar tecnologías. Ver `MASTER-PLAN.md` §K | **PLANIFICADA (DOCUMENTAL)** — diseño completo en FASE R-2.13 (`FASE-N-ECOSYSTEM-ARCHITECTURE.md`) |
| **FASE O** — GPU Control & Orchestration Research | Línea de INVESTIGACIÓN (PLANIFICADA): evaluar LACT, CoreCtrl, amdgpu-clocks, interfaces sysfs/amdgpu, PowerPlay, DPM, runtime-PM, perfiles, restauración y ownership; no reemplazar rx550-torneo sin comparar capacidades; Protocolo GPU Ownership (detectar→verificar→adquirir→experimentar→restaurar→liberar→verificar) y aplicarlo a gestores como Kalm solo si realmente están activos. Herramientas externas = objetos de evaluación, no soluciones adoptadas. Ver `MASTER-PLAN.md` §K | **PLANIFICADA** |
| **FASE P** — Frame Generation & Upscaling Research | Línea de INVESTIGACIÓN (PLANIFICADA): lsfg-vk, FSR, upscaling, frame generation, Vulkan layers, inyección/interposición, coste/latencia/calidad, compatibilidad Polaris12; separar estrictamente RENDIMIENTO REAL vs PERCIBIDO; nunca mezclar en los benchmarks del Lab K. No asumir mejora sin experimentos. Ver `MASTER-PLAN.md` §K | **PLANIFICADA** |
| **FASE Q** — Mesa Polaris12 Optimization Research | Línea de INVESTIGACIÓN (PLANIFICADA): oportunidades en Mesa/radeonsi/RADV específicas de Polaris12 sin asumir beneficio; pipeline OBSERVACIÓN→HIPÓTESIS→CAMBIO AISLADO→A/B→RÉPLICAS→MEDICIÓN→VALIDACIÓN→ACEPTAR/RECHAZAR; cambios aislados para causalidad; modificación solo en etapa experimental futura con rollback definido. Ver `MASTER-PLAN.md` §K | **PLANIFICADA** |

*Nota: las FASE K/Q (K, L, M, N, O, P, Q) son roadmap **PLANIFICADO/FUTURO** — no autorizadas para ejecución; ninguna hipótesis presentada como resultado experimental; N/O/P/Q son líneas de investigación documental; GRBM_PERFCOUNTER0_SELECT=0x2 (GUI_ACTIVE) y SQ PERF_SEL=0x4 (WAVES) **VERIFICADOS para GFX8 documentalmente en FASE R-0 (R0-1) y reconciliados en FASE R-1 (R1-1)** — la ejecución/escritura sigue NO autorizada (no se afirma que UMR sea la única vía). No se asume que Kalm está activo: su estado debe verificarse en el momento de cada experimento. LACT/CoreCtrl/amdgpu-clocks = objetos de evaluación, no soluciones adoptadas. BIOS/VBIOS = solo investigación futura de alto riesgo. Las FASE E–J existentes permanecen intactas. Inventario del ecosistema, arquitectura conceptual, Protocolo GPU Ownership, ciclo de vida de tecnologías, principio fundamental y FASE L/M ampliadas en `MASTER-PLAN.md` §K. Añadida la **Capa Transversal — KERNEL / DRIVER COMPATIBILITY & EDGE-CASE LAYER** (sección final de `MASTER-PLAN.md`, no es una FASE): telemetría (clasificación A/B/C/D), LACT vs rx550-torneo, amdgpu-clocks (identificación por PCI), L.0 ppfeaturemask, pp_od_clk_voltage, pp_dpm edge cases (WRITE SUCCESS ≠ STATE CHANGE VERIFIED), pp_table, VBIOS high-risk, Observability Perturbation, Hardware Identity, Capability Matrix, Experimental Safety Gate y clasificación de afirmaciones externas.*

---

## 🔒 CONGELADO (NO TOCAR sin autorización explícita nueva)

- **WORKLOAD-SINTETICO:** código, shaders, Makefile, configuración Mesa, drirc, Kalm, kernel, GRUB
- **BIOS / VBIOS / SPPT / pp_table**
- **ppfeaturemask** (valor actual `0xfff7bfff` — no escribir)
- **Kalm writes** (kalmd.py, kalm-lite.py, kalm-gpu.service, config `/etc/kalm/`)
- **Mesa del sistema** (`/usr/lib64/`, `/usr/share/vulkan/icd.d/`)
- **GRUB / kernel / DRM / KMS / amdgpu config**
- **Cambios permanentes de sysfs** (power1_cap, DPM, pp_dpm_sclk/mclk, pp_power_profile_mode)
- **Configuraciones permanentes del sistema**

---

## 📁 ARTEFACTOS CLAVE (Rutas)

| Artefacto | Ruta |
|---|---|
| Auditoría completa | `experiments/AUDIT-001/` (AUDIT-001.md, ERRATA.md, METRICS-DEFINITIONS.md, EVIDENCE-MATRIX.md) |
| FASE A — discriminación (histórica) | `experiments/fase-a-discriminacion-20260919-114241/` (RESULTADOS-FASE-A.md, INVALIDACION-corridas-04-09.md) |
| FASE B — cap-probe (histórica) | `experiments/fase-b-cap-probe-20260919-122038/` (RESULTADOS-FASE-B.md, EP08-auditoria-telemetria-E1E3.md) |
| FASE B — POLARIS12-MAP (histórica) | `experiments/POLARIS12-MAP/` (POLARIS12-MAP.md, HARDWARE-ROUTES.md, SOFTWARE-CAPABILITIES.md, EXPERIMENT-CANDIDATES.md, UNVERIFIED-CLAIMS.md) |
| EP-05 (Mesa CUSTOM A/B) | `experiments/ep05-mesa-custom-20260919-212249/RESULTADOS-EP05.md` |
| EP-06 (soak + réplica) | `experiments/ep06-soak-cap-20260919-205645/RESULTADOS-EP06.md` |
| rx550-torneo | `rx550-torneo/` (Fases 1–3 + M1, 65/55/56/112 checks OK) |
| M1 (vkmark 35/30W) | `experiments/M1-cap-35-30/` (RESULTADOS-M1.md, TELEMETRY-SCHEMA.md, runs/20260919-235939/) |
| E-03 corregida | `experiments/WORKLOAD-SINTETICO/runs/exploratorio-03-corrected/` |
| ES-01 (Escalado) | `experiments/WORKLOAD-SINTETICO/runs/escalado-01/` |
| F2 (8 fetches) | `experiments/WORKLOAD-SINTETICO/runs/escalado-01/F2-*/` |
| GravityMark | `experiments/EXPLORATORIO-GravityMark/runs/` |
| Superposition (exploratorio) | `experiments/EXPLORATORIO-GravityMark/runs/Superposition/` |
| **FASE C — R-14 Superposition Dissection** | `experiments/R-14-SUPERPOSITION-DISSECTION/` (R-14-SUPERPOSITION-DISSECTION.md, runs/superposition_dissection_1/) |
| **FASE D — Performance Counters** | `experiments/FASE-D-COUNTERS-AUDIT/` — Etapa 1: `FASE-D-COUNTERS-AUDIT.md` · Etapa 2: `FASE-D-ETAPA-2-PLAN.md`, `FASE-D-ETAPA-2-RESULTADOS.md` (+§12 correcciones R-1.3), `FASE-D-ETAPA-2-AUDIT.md` + `runs/etapa2/A{1,2,3}/B{1,2,3}/` · Etapa 3 (DISEÑADA, NO EJECUTADA): `FASE-D-ETAPA-3-PLAN.md`, `FASE-D-ETAPA-3-PRECHECK.md`, `FASE-D-ETAPA-3-EVENTS.md` · **Auditoría IDs**: `FASE-D-GFX8-EVENT-ID-AUDIT.md` (COMPLETADA, Conclusión B + adenda §14 R-1.2) |
| **FASE R-0 — External Knowledge Recovery** | `experiments/FASE-R0-EXTERNAL-KNOWLEDGE/` (R0-1..R0-6 + REFERENCE.txt + informe final) — COMPLETADA |
| **FASE R-1 — Documentation Reconciliation** | `experiments/FASE-R1-DOCUMENTATION-RECONCILIATION/` (R1-1..R1-15) — COMPLETADA |
| **FASE R-2 — Project Documentation** | `experiments/FASE-R2-PROJECT-DOCUMENTATION/` (R-2.1..R-2.25, FASE-R2-FINAL-REPORT.md) + raíz `PROJECT-DOCUMENTATION-STATUS.md` — COMPLETADA |
| **FASE R-3 — Original Ideas / Novelty Audit** | `experiments/FASE-R3-NOVELTY-AUDIT/` (R3-NOVELTY-MATRIX, R3-FEASIBILITY-MATRIX, R3-DEPENDENCIES, R3-MASTER-PLAN-INTEGRATION-PROPOSAL, FASE-R3-FINAL-REPORT) + `projects/` I-01..I-10 (40+ docs) — COMPLETADA |
| **FASE R-3.1 — Fusion Architecture Audit** | `experiments/FASE-R3-1-FUSION-ARCHITECTURE-AUDIT/` (FUSION-01..07, ASSUMPTION-AUDIT, NOVELTY/FEASIBILITY/DEPENDENCY/IMPLEMENTATION-LAYER matrices, EXPERIMENT-ROADMAP, PRIOR-ART-INDEX, README, R3-1-MASTER-REPORT) — COMPLETADA (READ-ONLY) |
| **FASE R-4A — EXP-F3-A Bandwidth Real** | `experiments/FASE-R4A-BANDWIDTH-REAL/EXP-F3-A-BANDWIDTH-REAL.md` — COMPLETADA (READ-ONLY): enlace Gen2×4 (techo bridge), PCIe teórico 2.0 GB/s/sentido DERIVED, VRAM 96–112 GB/s ESTIMATED, GTT 6.2 GB VERIFIED; real UNKNOWN; adenda en FUSION-03 |
| **FASE R-4C — EXP-F1-A Jitter Observability** | `experiments/FASE-R4C-JITTER-OBSERVABILITY/` (README.md, EXP-F1-A-JITTER-OBSERVABILITY.md, PRECHECK-REPORT.md, PRIOR-ART.md, EXP-F1-A-RESULTADOS.md, harness/, results/) — **COMPLETADA**: NIVEL A MAE=0.0px y NIVEL B MAE=3.66×10⁻¹⁰px/máx 3×10⁻⁸px reconstruyendo desde matriz host-visible; 8/8 corridas PASS deterministas (RADV RX550 real + lavapipe ×2 réplicas ×2 niveles); MAE<0.01px PROVISIONAL TARGET superado ~×10⁷; ANV NO EJECUTADO (sin devices); jitter≠MV |
| **FASE R-4B — EXP-F4-A Governor Read-Only** | `experiments/FASE-R4B-GOVERNOR/` (EXP-F4-A-PROTOCOL.md v2.1, EXP-F4-A-PROTOCOL-v2.2.md, **EXP-F4-A-PROTOCOL-v2.3-PROPUESTA.md**, PRE-FLIGHT-CALIBRACION-EXP-F4-A.md, EXP-F4-A-RESULTADOS.md, harness/, controller/, telemetry/, results/session1) + `experiments/FASE-R4B-THERMAL-TEST/` (investigación térmica A–J, N=2, **mini-test 7.3-B ramp con governor N=2**) — **S1 v2.2 COMPLETADA 2026-09-23**: GATEs TOTALES PASS (histéresis 0.26 % tras cooldown entre passes), FREEZE T=9.168 ms/s\*=0.75/sha256 `6b6d6952…`, Phase 2 8/8 ejecutados y **clasificada `DIAGNOSTIC / THERMALLY CONFOUNDED — NOT FOR VERDICT`** (R1–R7 sin declarar, causa = temperatura acumulada, N=2); sin writes; S1 v2.1 = parada D (registro §1B); **propuesta v2.3 preparada (cooldown entre trials de Phase 2; DIST opciones 7.3-A/B/C)**; **mini-test 7.3-B ejecutado (N=2): DIST 200 s NO cabe desde ≤50 °C (ramp 0.252/0.246 °C/s, T_max 92 °C pre-final) → entrada ≤35 °C (7.3-A) o 7.3-C como opciones; S2 NO iniciada, sin veredicto global** |
| Benchmarks instalados | `~/Escritorio/berchmark/instalados/` (hashes SHA-256 verificados) |
| Ecosistema / inventario (FASE N–Q) + Capa Transversal | `MASTER-PLAN.md` §K (FASE K/Q, arquitectura conceptual, inventario del ecosistema, Protocolo GPU Ownership, RX Compression Engine provisional, FASE L/M ampliadas, ciclo de vida y principio fundamental) + sección final **Capa Transversal — KERNEL / DRIVER COMPATIBILITY & EDGE-CASE LAYER** (telemetría y clasificación A/B/C/D, LACT/amdgpu-clocks, ppfeaturemask L.0, pp_od_clk_voltage, pp_dpm edge cases, pp_table, VBIOS high-risk, Observability Perturbation, Hardware Identity, Capability Matrix, Experimental Safety Gate, clasificación de afirmaciones externas) |

---

## 🚫 NO HACER (Reglas de Seguridad)

1. No escribir `power1_cap`, DPM, SCLK, MCLK, ppfeaturemask fuera de corrida autorizada con snapshot+readback+restore.
2. No instalar/ejecutar benchmarks/instaladores sin autorización y revisión de licencia.
3. No modificar rx550-torneo, artefactos M1, Mesa system, `/opt/mesa-...`, kalm, GRUB/kernel/DRM.
4. No diseñar/implementar BERRETA, Ghost Cache, GEO, memoria, RADV, PowerPlay — falta caracterizar cuello de botella y documento de diseño.
5. No adoptar régimen histórico 17/09 como especificación de rendimiento ([NO REPRODUCIBLE]).
5. No comparar métricas de potencia sin etiquetar `NOT DIRECTLY COMPARABLE` (ver `METRICS-DEFINITIONS.md`).

---

## 📋 PRÓXIMA ACCIÓN INMEDIATA

**FASE R-4B (EXP-F4-A) — PHASE 2 CLASIFICADA + PROPUESTA v2.3 EN REVISIÓN + MINI-TEST 7.3-B EJECUTADO (2026-09-23).**
`experiments/FASE-R4B-GOVERNOR/EXP-F4-A-RESULTADOS.md` §1C + `EXP-F4-A-PROTOCOL-v2.2.md` +
`EXP-F4-A-PROTOCOL-v2.3-PROPUESTA.md` + `FASE-R4B-THERMAL-TEST/RESULTADOS-MINITEST-7.3-B.md`:
GATEs Fase 1 **TODOS PASS** (histéresis 0.26 % tras cooldown v2.2 entre passes), **FREEZE
T=9.168 ms, s*=0.75** (sha256 `6b6d6952…`), Phase 2 8/8 trials ejecutada y **clasificada
`DIAGNOSTIC / THERMALLY CONFOUNDED — NOT FOR VERDICT`** (auditoría de timestamps: contaminación por
**temperatura acumulada** — Phase 2 heredó 84 °C de Fase 1 y 91–92 °C entre trials; 0 de 8 trials
íntegros; R1–R7 NO declarados). Verificaciones integridad/read-only OK. **Mini-test 7.3-B
EJECUTADO (N=2 read-only, autorizado por el usuario, NO parte de S2):** governor responde
correctamente a 1071 y semántica íntegra, pero **DIST de 200 s NO cabe desde ≤50 °C**
(ramp real 0.246–0.252 °C/s, T_max 92 °C antes del final en ambas réplicas; REP1 v9 degradada,
REP2 v7–v9). **Decisión pendiente del usuario:** (a) opción DIST — **7.3-A con entrada ≤35 °C**
(recomendada por la ramp medida; ≤40 °C queda sin margen) o **7.3-C** marcación por ventana
(R7 → DIAGNOSTIC NOT FOR VERDICT); (b) autorización explícita para
ejecutar S2 bajo v2.3 (reproducible extendiendo `run_all_v22.sh`). Constante: programación de
contadores y toda escritura SIGUEN NO AUTORIZADAS; S1-v2.1 original intacta como diagnóstico.
Tras R-4B siguen candidatos NO INICIADOS: EXP-F5-A (fusión 5 mínimo obligatorio), EXP-F6-A
(concurrencia 8 CU). Recordatorio permanente de FASE D:
**PROGRAMACIÓN PERMANECE NO AUTORIZADA.** Etapa 3: eventos investigados (`experiments/FASE-D-COUNTERS-AUDIT/FASE-D-ETAPA-3-EVENTS.md`, offline/read-only): mecanismo CP/eventos VERIFICADO en código Mesa local (CP_PERFMON_CNTL 0/1/2; eventos V_028A90 START=23/STOP=24/SAMPLE=27; campos SQ_CTRL; COMPUTE_PERFCOUNT_ENABLE); CONCORDANCIA Mesa↔UMR de offsets (dword = byte/4). **Auditoría de Event IDs GFX8 completada** (`experiments/FASE-D-COUNTERS-AUDIT/FASE-D-GFX8-EVENT-ID-AUDIT.md`): se investigaron Mesa local (+ historial git completo 222 644 commits), kernel amdgpu (recortado: solo Kconfig/Makefile), amdgfxregs.h (sin enums PERF_SEL), UMR db (2633 regs, CERO enums de evento), /opt, backups, /usr/share/doc y $HOME. **Conclusión B: «Los IDs de eventos GFX8 no pueden verificarse mediante las fuentes locales disponibles.»** radeonsi (sí soporta GFX8 y AMD_performance_monitor) reenvía el selector del usuario sin definir eventos; los únicos IDs numéricos (GRBM=2 «GPU active», SQ WAVES=4, GL1C/GL2C/TCP/SQ_*, CPF=0x18) son de RADV y **solo se ejecutan/probaron en GFX10.3 (o GFX11, con valores distintos p.ej. SQ WAVES=0x14)** — el comentario del commit de enablement (f905edb1991) dice literalmente «the code has only been tested on GFX10.3»; GFX8 nunca se habilitó. **GRBM PERF_SEL=2 y SQ PERF_SEL=4 → NO VERIFICADO para GFX8** (GUI_ACTIVE solo existe como bit 31 de GRBM_STATUS, no como selector). **La primera escritura `GRBM_PERFCOUNTER0_SELECT=0x2` (propuesta §H del EVENTS) queda BLOQUEADA** — científicamente no válida sin el mapa de eventos VI. Fuente primaria faltante: tabla PERF_SEL de VI/gfx803 de material AMD (GPUPerfAPI/CodeXL/RGP o documentación oficial Polaris). **No ejecutar hasta nueva autorización explícita + mapa de eventos GFX8 verificado + PRE read-only superado + sanity idle OK.** El plan `experiments/FASE-D-COUNTERS-AUDIT/FASE-D-ETAPA-3-PLAN.md` (v1.5, 2026-09-21) define 11 secciones: preguntas Q1–Q8, inventario priorizado A/B/C, semántica por contador (GRBM/GRBMSE/SX/TCC/TCA/CB/DB/MC_ARB directos; SQ/SPI/TCP/TA/TD windowed; SPM EXCLUIDO), mecanismo conceptual de programación+restauración, diseño mínimo (6 corridas intercaladas A/B×3 idénticas a Etapa 2), protocolo PRE/DURANTE/POST, criterios de éxito (H1, H3, H5, geometría-vs-shader, caché-vs-VRAM), criterios de aborto y matriz final. **No ejecutar hasta nueva autorización explícita + PRE read-only superado + sanity idle OK.** Para cuantificar trabajo real de unidades (SQ/CB/DB/MC_ARB/MC_CITF/ATC/CHUB_ATC/GMCON/CP) y caches L1/L2 (TCC directo; TCP/TA/TD solo vía ventana de shader) se requiere programación de contadores (escrituras MMIO) → requiere nueva autorización y política de restauración.

> **↳ RECONCILIACIÓN FASE R-1 (2026-09-22) — adenda que NO borra el historial de FASE D.** La Conclusión B
> era válida para la vía elegida en su momento: **«fuentes locales no verifican IDs GFX8»**. Posteriormente FASE
> R-0 completó la **Fuente primaria faltante** que esta misma línea denunciaba (GPUPerfAPI):
> - **GRBM PERF_SEL=2 = GUI_ACTIVE [VERIFICADO para GFX8]** en `GPUOpen gpu_performance_api v3.11.1`
>   (constante `GRBM_PERF_SEL_GUI_ACTIVE = 2` de catálogo AMD GFX8) — refrenda la constante RADV=2. La nota de
>   «GUI_ACTIVE solo existe como bit 31 de GRBM_STATUS» quedaba así **invalidada como causa de bloqueo**.
> - **SQ PERF_SEL=4 = WAVES [VERIFICADO para GFX8]** (`SQ*_PERF_SEL_WAVES = 4`, presente en los 8 sub-bloques
>   Sq/Cs/Es/Gs/Hs/Ls/Ps/Vs). Los valores GFX11/Sienna-Cichlid (p.ej. 0x14) corresponden a otra generación y
>   siguen sirviendo como aviso de no-portabilidad.
> - La escritura `GRBM_PERFCOUNTER0_SELECT=0x2` de §H del EVENTS pasa de «científicamente NO válida por falta
>   de mapa» a «mapa obtenido y verificado ✓; **ejecución sigue NO AUTORIZADA**» (autorización supervisión aparte).
> - Reconciliación de conteos 396 vs 405 (CB), 299 vs 273 (SQ), 33 vs 22 (MC) en
>   `experiments/FASE-R1-DOCUMENTATION-RECONCILIATION/R1-1-GFX8-EVENT-RECONCILIATION.md` (PARTIALLY_RECONCILED;
>   coherencia estructural 20/22 bloques; semántica/unidad MC sigue UNRESOLVED → no diseñar normalización MC).
> - Análoga: adenda «## 14. Resultado B — Revisión posterior a FASE R-0» en `FASE-D-GFX8-EVENT-ID-AUDIT.md`.

Investigar subsistemas A–AJ (ver `experiments/POLARIS12-MAP/POLARIS12-MAP.md` — tabla maestra de subsistemas) usando fuentes primarias: whitepaper Polaris, GCN whitepaper, GPUOpen, Mesa upstream, kernel amdgpu, Chip and Cheese, RasterGrid, Phoronix, Igor'sLab.

**WORKLOAD-SINTETICO permanece CONGELADO durante toda la auditoría y mapeo.**