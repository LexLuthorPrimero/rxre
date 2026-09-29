# IMPLEMENTATION-READINESS-AUDIT.md — Auditoría de madurez de implementación (RX 550)

**Fecha:** 2026-09-23 · **Modo:** SOLO LECTURA (ningún archivo, sysfs, registro ni resultado modificado)
**Estado del proyecto:** EXP-F4-A v2.3 queda **INCONCLUSO** según su informe (`FASE-R4B-GOVERNOR/EXP-F4-A-RESULTADOS-v2.3.md`). S2-v2.3 fue **INICIADA y PARADA D** antes de Phase 2; la correlación con carga externa es una causa probable no verificada, no una causa raíz. No se reintenta S2-v2.3.
**Condición de parada:** esta auditoría NO implementa nada, NO toca la GPU, NO modifica el sistema y NO ejecuta el roadmap. Termina con el reporte A–G (§16).

> **Notación:** en las tablas y gates resumidos, `P` significa `W_SMU` leído de
> `power1_input`; no es vatímetro independiente.

---

## 1. Objetivo y alcance

Determinar, con toda la evidencia disponible hasta EXP-F4-A v2.3, qué conocimientos pueden convertirse en
optimizaciones **reales, reversibles y medibles** para la RX 550, cuáles necesitan un **A/B adicional** y cuáles
**todavía requieren investigación**.

Reglas permanentes aplicadas (del encargo):
- No se modifica el sistema (Mesa, kernel, firmware/VBIOS, PowerPlay, sysfs, DPM, config persistente).
- No se ejecutan benchmarks nuevos; solo se lee evidencia ya registrada.
- No se repite S2-v2.3, no se rescata EXP-F4-A, no se alteran resultados existentes.
- Resultados n=1..3 jamás se tratan como evidencia de población.
- Hipótesis no se convierten en hechos; no se inventa causalidad.
- Si algo no está determinado: 1) documentación del proyecto, 2) fuentes primarias de Internet, 3) UNKNOWN.

## 2. Método y reglas de evidencia

Se auditaron los documentos del repositorio por fase (ver §4). Cada candidato se clasifica en **exactamente una**
categoría A–E (§3). La clasificación se deriva de la evidencia (números y rutas), no de intuición. Se usan los
estados de evidencia del proyecto: `[VERIFICADO]`, `[REPRODUCIBLE]`, `[OBSERVADO]`, `[HIPÓTESIS]`,
`[DOCUMENTADO]`, `[PARTIALLY_RECONCILED]`, `[UNRESOLVED]`, `[CONTRADICTED]`, `[NO REPRODUCIBLE]`
(`FASE-R1-DOCUMENTATION-RECONCILIATION/R1-6-EVIDENCE-STATE-MODEL.md`).

**Corrección documental detectada (no modifica nada):** el par de escalas "1.00/0.93/0.86/0.75/0.60" con p99
"11.46/9.35/7.02/4.9/2.85 ms" **no existe en el repositorio**. Las escalas reales congeladas de FASE-R4B son
**{1.00, 0.87, 0.75, 0.62, 0.50}** con curva de Fase 1 (v2.3, n=1): **11.441 / 9.337 / 7.037 / 4.897 / 2.848 ms**
(`FASE-R4B-GOVERNOR/results/v23/session1/fase1/manifest.json`). Los valores del encargo coinciden casi
exactamente con esa curva; las etiquetas 0.93/0.86/0.60 provienen del diseño no ejecutado
`projects/CLOSED-LOOP-QUALITY-GOVERNOR/EXPERIMENT-DESIGN.md` (sweep futuro 1.00→0.60). **Se usan las escalas
verificadas {1.00, 0.87, 0.75, 0.62, 0.50}.**

## 3. Clasificación obligatoria y niveles de riesgo

| Categoría | Definición |
|---|---|
| **A — IMPLEMENTABLE AHORA** | Evidencia suficiente para implementar una modificación reversible y medirla. |
| **B — IMPLEMENTABLE CON A/B** | Hipótesis suficientemente sólida para diseñar un A/B controlado antes de hacerla permanente. |
| **C — REQUIERE MÁS INVESTIGACIÓN** | La evidencia actual no permite diseñar responsablemente una implementación. |
| **D — DESCARTADO / REFUTADO** | La evidencia contradice la hipótesis o muestra que no produce el efecto esperado. |
| **E — INCONCLUSO** | Evidencia insuficiente o confusa; no debe utilizarse todavía. |

Tres niveles de riesgo (no equivalentes), priorizando software/config primero:

1. **SOFTWARE** — Mesa/RADV/radeonsi, Vulkan/OpenGL, configuración de aplicaciones (env por proceso, render-scale, driconf). Riesgo bajo-media; reversible por proceso.
2. **DRIVER/SISTEMA** — DPM, runtime PM, power cap, clocks, perfiles, políticas de energía (sysfs: `power1_cap`, `pp_dpm_*`, `pp_power_profile_mode`, `ppfeaturemask`, `power/control`). Requiere protocolo snapshot→write→readback→restore→readback y, fuera de `power/control`/`power1_cap` autorizados, **autorización explícita**.
3. **HARDWARE/FIRMWARE** — VBIOS, registers MMIO (contadores PERF_SEL), PowerPlay tables, BIOS. Alto riesgo; **congelado** salvo autorización extrema.

## 4. Fuentes auditadas (mapa)

| Área | Directorio | Hallazgo principal |
|---|---|---|
| FASE A | `fase-a-discriminacion-…/` | Cap 25 W no liga hoy; selector VK numérico roto; GL 640p no SCLK-bound |
| FASE B (cap-probe) | `fase-b-cap-probe-…/` | Curva de cap PLANA 25→35 W; EP-08 confirma RX 550 real en E1/E3 |
| EP-05 / EP-06 | `ep05-mesa-custom…/`, `ep06-soak…/` | Mesa CUSTOM==STOCK; régimen E1/E3 no reproducible ni caliente |
| M1 | `M1-cap-35-30/` | Cap 35/30 W NO DISCRIMINATIVO (W_SMU 12.27 W < 27 W) |
| WORKLOAD-SINTETICO | `WORKLOAD-SINTETICO/` | E-03 15.75 W steady + MCLK 1500; escalado y F2 sin efecto en potencia; techo ~16 W |
| FASE C | `R-14-SUPERPOSITION-DISSECTION/` | Superposition 22.31 W steady / 24.71 W pico (`W_SMU`); correlación direccional, no causalidad geométrica |
| GravityMark | `EXPLORATORIO-GravityMark/` | GravityMark 200k NO DISCRIMINATIVO (12.4 W); 4m = OOM |
| FASE D | `FASE-D-COUNTERS-AUDIT/` | Catálogo contadores GFX8; etapa 2 A/B (22.25 vs 15.78 W); etapa 3 NO AUTORIZADA |
| POLARIS12-MAP | `POLARIS12-MAP/` | Mapa A–AJ; GEO/SHD/MEM/FRAAG/PWR solo PLANEADOS |
| R-0 | `FASE-R0-EXTERNAL-KNOWLEDGE/` | GPUPerfAPI v3.17 catálogo GFX8; v3.11.1 histórico; 2304 filas no eventos validados; política MCLK 5/16/20 source-level |
| R-1 | `FASE-R1-DOCUMENTATION-RECONCILIATION/` | Reconciliación de catálogos: 19/23; rangos no semánticamente seguros; MC `UNRESOLVED` |
| R-2 / R-3 / R-3.1 | `FASE-R2-…/`, `FASE-R3-…/`, `FASE-R3-1-…/` | Fases E–Q diseñadas, ninguna ejecutada; FUSION-04 READY; 0 PROVEN NOVEL |
| R-4A | `FASE-R4A-BANDWIDTH-REAL/` | PCIe Gen2×4 por techo HW; 2.0 GB/s por sentido; GTT 6.2 GB; VIS 256 MiB |
| R-4B | `FASE-R4B-GOVERNOR/` + `FASE-R4B-THERMAL-TEST/` | S1-v2.3 EJECUTADA/COMPLETADA; S2-v2.3 PARADA_D; observación diagnóstica R1/R3 3/3; R1–R6 no evaluables formalmente; t90 depende de condición/experimento |
| R-4C | `FASE-R4C-JITTER-OBSERVABILITY/` | Jitter observable (MAE 3.66×10⁻¹⁰ px) — herramienta, no optimización |
| Torneo | `rx550-torneo/` | Fases 1–3 + M1 (65/55/56/112 checks); whitelist 2 nodos; rollback verificado |

## 5. Hallazgos por fase (resumen de evidencia)

### 5.1 FASE A/B (régimen de potencia y cap)
- Con los workloads disponibles la potencia estimada por sensor SMU (`W_SMU`) es **9.4–13.6 W** y el cap (25–35 W) **no liga**: el SMU no baja SCLK
  por un cap no alcanzado (Fase B: 25→35 W plano, SCLK 1071, P 10.7–11.6 W; M1: ΔFPS=ΔSCLK=0, ΔP IC95%
  (−0.103, +0.060) W).
- EP-06: a 70–71 °C con cap 25 W sigue SCLK 1071 y `W_SMU` 9.6–11.5 W → el régimen E1/E3 (25 W clavado / SCLK 350–390)
  **no se reproduce** ni frío ni caliente. `W_SMU` máximo observado: **13.6 W** (EP-06) y **23.7 W pico** (Superposition).
- `MESA_VK_DEVICE_SELECT=1002:699f` selecciona hoy la **iGPU 0x412** (3/3); seleccionar por **ICD**
  (`VK_ICD_FILENAMES=…/radeon_icd.x86_64.json`) o por **nombre** da 0x699F de forma determinística.

### 5.2 FASE C y WORKLOAD-SINTETICO (potencia y bottleneck)
- Superposition (OpenGL/radeonsi, geometría): **22.31 W steady `W_SMU` (N=1987), 24.71 W pico, `mem_busy` 24.6 %,
  VRAM 1554 MB, score 804** — rompe el patrón de los sintéticos (15.75–16.18 W) con **mem_busy menor**; la explicación causal sigue abierta.
- Sintéticos Vulkan: **fetch-latency bound**; escalar overdraw/FMA/texturas/MSAA/fetches NO sube potencia
  (ES-01 plano 15.75–16.18 W, deriva ±0.33 W; F2: frametime 2× con potencia invariante 15.76 vs 16.13 W).
- E-03 corregida: MCLK 1500 observado (220/277 muestras) con `mem_busy` 36–49 %; la
  política upstream 5/16/20 no prueba que `mem_busy` sea el trigger local. R-4A mostró
  readout local 3/16/20; el mapping de campo/perfil queda `UNRESOLVED`. `W_SMU`
  steady ≈15.75 W; “más memoria” no equivale causalmente a “más potencia”.

### 5.3 FASE D / Polaris12-MAP (contadores y rutas)
- Programación de contadores: **NO AUTORIZADA** (invariante R-0/R-1/R-2/R-4B). Mapa preparado:
  12 slots (GRBM×2, GRBMSE×2, SX×1, TCC×2, TCA×1, CB×1, DB×1, MC_ARB×2).
  GRBM=2 y SQ=4 son entradas de catálogo, no validación para `1002:699f`; los rangos
  son índices de catálogo, no rangos semánticamente seguros; semántica MC `UNRESOLVED`.
- Registros por bloque: GRBM 2, SX/TCC/TCA/CB/DB/TCP/MC_ARB 4, SQ 16, SPI 6, TA/TD 2. Sin PMU amdgpu para
  `perf`; UMR (2633 regs) sin enums de evento; radeontop solo heurísticas (gpu_busy/mem_busy).
- Etapa 2: A=22.25 W `W_SMU` vs B=15.78 W (ratio 1.41); vgt/pa/sh y sx (1.51–1.60)
  correlacionan. Esto orienta la hipótesis hacia geometría/vertex/export, pero no
  demuestra causalidad ni excluye ROP/DRAM (`mem_busy` es proxy).
- GEO/SHD/FRAG/MEM/PWR: **PLANEADOS (sin ejecución)**.

### 5.4 R-0/R-1 (conocimiento externo)
- Política DPM MCLK smu7 128-bit: upstream `mclk_up_hyst=5`, `down_hyst=16`,
  `activity=20` (`smu7_hwmgr.c`, gate `chip_id ≥ POLARIS10`) — **VERIFICADO
  source-level**; R-4A registró local `3/16/20`, mapping `UNRESOLVED`; no prueba
  el trigger local ni la equivalencia con `mem_busy_percent`.
- Workarounds radeonsi activos por familia: `has_msaa_sample_loc_bug` (POLARIS10..12), `LINE_FILTER_DISABLE
  (family ≤ POLARIS12)`, driconf `radeonsi_clear_db_cache_before_clear` (bug #96908, fix d938b8c) — [VERIFICADO];
  **efecto real sin medir** (GAP-11).
- Overdrive: `ppfeaturemask` actual `0xfff7bfff` no contiene 0x4000 → OD no disponible; `pp_od_clk_voltage` no
  autorizado.
- GPUPerfAPI `v3.17` es la referencia operativa recomendada para tablas GFX8; `v3.11.1`
  queda como extracción histórica. v4.0+ eliminó GCN. La presencia de catálogo no prueba
  runtime, ASIC ni seguridad de programación.

### 5.5 R-4A (bandwidth)
- Enlace negociado **Gen2×4 = 2.0 GB/s por sentido (DERIVED)**; techo real = root port 00:01.0 (5.0 GT/s);
  el endpoint es capaz de Gen3×8 pero la plataforma no. Payload 1.4–1.9 GB/s (ESTIMATED). VRAM 96–112 GB/s
  (ESTIMATED). GTT 6.2 GB, VIS-VRAM 256 MiB (VERIFIED). Ratio enlace/VRAM **×48–80** (corrección oficial vs ×24–32).
- Bandwidth REAL medido: **UNKNOWN** (amdgpu_benchmark denegado por permisos; su `.write` ejecutaría benchmarks).
- Compresión para “competir con VRAM”: **CONTRADICTED** (DCC no ahorra PCIe); “render pequeño → VIS 256 MiB”:
  viable (sub-producto útil).

### 5.6 R-4B (governor, T, s*, térmico) — reconciliación D6
- Protocolo: escalas {1.00, 0.87, 0.75, 0.62, 0.50}; T de referencia v2.2 = 9.168 ms;
  el manifest de la corrida v2.3 contiene `T_run=9.153 ms` (Δ 0.16 %, aceptado); s*=0.75;
  banda [0.90, 1.10]·T; fixed 60 s, gov 120 s, dist 200 s; cooldown DN-07
  `≤50 °C s30 ∧ SCLK nv0 ∧ P<4 W`; anti-deadlock 3600 s; abort ≥96 °C.
- **S1-v2.3:** `EXECUTED/COMPLETADA` (15/15 bloques; 8/8 trials). La Fase 2 de S1 es
  evidencia diagnóstica: R1 y R3 muestran 3/3 observaciones, pero R1–R6 **no son
  evaluables formalmente** porque falta la unión 6+6; los valores de R2/R4/R6 son
  observaciones que no cumplen sus literales, no PASS/FAIL global. R7 es
  `INCONCLUSIVE / NOT FOR VERDICT` por diseño y confound térmico.
- **S2-v2.3:** `INICIADA / PARADA_D` (rc=9) durante cooldown p2→p3; 10/15 bloques de
  Fase 1 y 0 trials de Phase 2. La no convergencia (`T=49 °C`, SCLK nivel 7,
  `W_SMU=6.395 W`) es compatible con carga externa; la identidad del cliente y la causa
  raíz no están verificadas. El logger externo está `PERDIDO / NO VERIFICABLE`.
- **Térmico:** no existe un `t90` universal. Test térmico N=2: 90 °C a 169/136 s
  desde sus condiciones iniciales; mini-test 7.3-B N=2: 171.9/134.8 s alineados a
  `m0`; S1-v2.3: aproximadamente `t0+100–120 s` en DIST, con ventanas posterior
  confounded. `t90≈221 s` desde ≤35 °C es extrapolación lineal histórica, no
  evidencia operacional; ≤35 °C queda opción no verificada.
- **Veredicto global:** `INCONCLUSO / INCONCLUSIVE`; nunca `SUPPORTED`; no reintentar S2-v2.3.
- La ausencia de convergencia del cooldown no demuestra por sí sola carga externa,
  fallo HW ni causalidad de un proceso concreto.

### 5.7 rx550-torneo (estado de infraestructura)
- Verificación GPU dual (0x1002:699f objetivo / 0x8086:0412 Intel NO-display); 6 nodos RESTORABLE_FIELDS
  (`power/control`, `power1_cap`, `power_dpm_force_performance_level`, `pp_dpm_sclk`, `pp_dpm_mclk`,
  `pp_power_profile_mode`); máx 2 escrituras por nodo + readback + rollback 1 intento; `guard_no_sys_write`
  whitelist; 90 °C es confound y 96 °C es el abort configurado (M1 histórico usaba
  90 °C como regla de corrida); detector de reset vía journalctl; 65/55/56/112 checks OK.
- Gaps: no hay función governor; el presupuesto térmico no está modelado; bandwidth/contadores bloqueados.

---

## 6. Tabla maestra de candidatos (45)

*Leyenda nivel: S=software/config · D=driver/sistema · F=firmware/registros · I=instrumento/regla/documental
(sin efecto sobre el sistema).*

| ID | Candidato | Nivel | Cat. | Evidencia clave |
|---|---|---|---|---|
| A-01 | SEL-01 — selección VK determinística de la RX 550 | I | **A** | `1002:699f`→0x412 roto; ICD/nombre→0x699F 3/3 |
| A-02 | TOR-OBS — telemetría read-only del governor en rx550-torneo | I | **A** | harness v2.3 ya read-only; física térmica N=2 reproducible |
| A-03 | THERM-OBS — T_max/SCLK_min por ventana + presupuesto t90 | I | **A** | confound §6.3 post-hoc; t90 se reporta por condición (134.8–171.9 s en mini-test), sin valor universal |
| A-04 | ENV-01 — precondición de exclusividad GPU + diagnóstico de cooldown | I | **A** | S2-v2.3 PARADA D documentada (sclk=7, P=6.395 W) |
| A-05 | TOR-CD — cooldown alineado a DN-07 (≤50 °C ∧ nv0 ∧ P<4 W) | D | **A** | condición verificada operativamente (8/8 S1, 345 s S2) |
| A-06 | MES-AB — regla de control del sample-loc-bug/MSAA en A/B | I | **A** | R0-3 [VERIFICADO]; GAP-11 mide efecto |
| A-07 | GPU-ID — verificación dual + RESTORABLE_FIELDS como baseline | I | **A** | gpu_finder + spec §29; 6 nodos; 112 checks M1 |
| A-08 | R0-POL — reconciliación de catálogo GPUPerfAPI v3.17 + índice histórico v3.11.1 | I | **A** | R0-1/R1-1 [PARTIALLY_RECONCILED / CATALOG ONLY]; no programación |
| A-09 | R4A-CON — constraint PCIe Gen2×4 en planificación | I | **A** | root port 5.0 GT/s; 2.0 GB/s por sentido DERIVED |
| A-10 | DOC-REC — reconciliar documentos heredados (Gen3×8, 501 GB/s, ×24–32) | I | **A** | cifras 501/Gen3×8 y ratios antiguos quedan **REJECTED**; R-4A/UNKNOWN y 96–112 estimado |
| B-01 | GOV-01 — detención en primer escalón en banda (0.87) / escalón 0.93 | S | **B** | R1/R3 3/3 como observaciones diagnósticas; R1–R6 no evaluables formalmente; n=3 |
| B-02 | GOV-02 — ventana de decisión 30–60 s o EMA | S | **B** | R4 no cumple literal en S1 (ventana 5); diagnóstico, no veredicto formal |
| B-03 | GOV-03 — grilla de escalas intermedias (0.93/0.86/0.80) | S | **B** | R2 overshoot 65–70 % en S1; observado, no PASS/FAIL formal |
| B-04 | T-01 — DIST acotado por presupuesto térmico (≤120 s activos o cap) | D | **B** | t90 por condición: 134.8–171.9 s en mini-test; no valor universal; 200 s no demostrada desde ≤50 °C |
| B-05 | R4A-02 — política de alojamiento GTT vs VRAM (hot set) | S | **B** | versión débil PARTIALLY VERIFIED; requiere A/B |
| B-06 | R4A-04 — buffer VIS-VRAM 256 MiB (render pequeño→VIS) | S | **B** | VIS 256 MiB VERIFIED; sub-producto viable |
| B-07 | MCLK-AB — encarrilamiento MCLK 1500 (pp_dpm_mclk) | D | **B** | política 5/16/20 **source-level**; MCLK 1500 reactivo no prueba causalidad; requiere FASE I/L |
| C-01 | CNT-12 — instrumentación de contadores GFX8 (12 slots) | F | **C** | catálogo GFX8 `PARTIALLY_RECONCILED`; GRBM/SQ no validados para ASIC; ejecución NO autorizada |
| C-02 | R4A-01 — medición de bandwidth real | I | **C** | amdgpu_benchmark denegado; real UNKNOWN |
| C-03 | R4A-03 — compresión delta en aplicación | S | **C** | fuerte CONTRADICTED; débil sin medir coste descompresión |
| C-04 | R4A-06 — identificación de módulo GDDR5 (6 vs 7 Gbps) | I | **C** | 96 vs 112 GB/s sin resolver |
| C-05 | WL-GFX-01 — workload sintético ≥20 W | S | **C** | techo ~16 W observado; WORKLOAD-SINTETICO CONGELADO |
| C-06 | DCC-01 — derrota de DCC / entropía de CB | S | **C** | H-CB-DRAM [HIPÓTESIS]; micro-bench no hecho |
| C-07 | GEO-01 — vertex throughput | S | **C** | FASE F diseñada; requiere contadores + autorización |
| C-08 | GEO-02 — primitive throughput | S | **C** | FASE F diseñada; culling pre-raster sin verificar |
| C-09 | FRAG-01 — sample shading MSAA 8× | S | **C** | explica 3.13× (E5); necesita control H-1; GAP-11 |
| C-10 | SHD-01 — Wave32 vs Wave64 | S | **C** | soporte GFX8 sin documentar; FASE Q |
| C-11 | PWR-01 — power profile modes | D | **C** | efecto SMU7/Polaris12 desconocido; write requiere L |
| C-12 | MEM-01/MEM-03 — VRAM pressure / sparse | S | **C** | MEM-01 riesgo OOM (Matriz J BAJA); MEM-03 sin diseño |
| C-13 | DIST35 — DIST con entrada ≤35 °C (opción histórica 7.3-A) | D | **C** | `t90≈221 s` es extrapolación lineal; no se midió un trial completo a 35 °C; no se declara viable |
| C-14 | ASY-01/BERRETA — async compute overlaps | S | **C** | ACE/HWS family-level documentado; nº ACEs, overlap y runtime local `UNKNOWN` |
| C-15 | I-05 — GFX8 frame recorder (herramienta) | I | **C** | PARTIALLY NOVEL; gap SQTT-GFX8 NO VERIFICADO |
| C-16 | SP-PRESET-01 — preset/resolución superior de Superposition | I | **C** | requiere licencia/XML; opción sin autorizar |
| C-17 | OVD-01 — Overdrive (ppfeaturemask 0x4000) | D | **C** | mask no contiene 0x4000; OD no disponible |
| D-01 | CAP-01 — power1_cap 25–35 W como palanca | D | **D** | curva plana (Fase B); M1 NO DISCRIMINATIVO |
| D-02 | MES-01 — Mesa CUSTOM como optimización | S | **D** | CUSTOM==STOCK (EP-05) |
| D-03 | SOAK-01 — soak térmico para reproducir E1/E3 | D | **D** | EP-06: no reproducible ni caliente |
| D-04 | KALM-01 — kalm como palanca | D | **D** | kalm descartado; dirección opuesta (EP-06) |
| D-05 | WL-SCALE-01 — escalar overdraw/FMA/tex/MSAA/combo | S | **D** | ES-01 plano 15.75–16.18 W |
| D-06 | WL-FRAG-01 — 8 fetchs de fragment | S | **D** | F2: potencia invariante (−0.4 W) |
| D-07 | WL-COMPUTE-01 — compute ALU puro | S | **D** | E-01/E-02: 13.23→12.38 W |
| D-08 | GM-01 — GravityMark 200k como workload M2 | S | **D** | 12.4 W media; 4m = OOM |
| D-09 | DIST-200 — DIST 200 s desde ≤50 °C | D | **D** | mini-test N=2: T_max 92 °C pre-final |
| E-01 | GOV-TORNEO — governor como función permanente de torneo | S | **E** | EXP-F4-A INCONCLUSO; n=3; R2/R4/R6 no cumplen |
| E-02 | REG17 — régimen 17/09 + “phong 1285 fps” | I | **E** | NO REPRODUCIBLE; linaje no fiable (O3) |
| E-03 | R2R4R6 — literales R2/R4/R6 + F1–F6 | I | **E** | R1–R6 no evaluables formalmente por muestra incompleta; F1–F6 no computados |

**Conteo:** A=10 · B=7 · C=17 · D=9 · E=3 · **Total = 46** (45 candidatos + E-03 como enunciado; se reportan
como **45 candidatos auditados**, con E-03 incluido). *Nota de conteo: E-03 es el mismo enunciado de los
candidatos GOV; se mantiene como candidato propio "literales no alcanzados" para no perder la clasificación
de los criterios de veredicto.*

---

## 7. Candidatos A — IMPLEMENTABLE AHORA

### A-02 · TOR-OBS — Telemetría read-only del governor en rx550-torneo

| Campo | Valor |
|---|---|
| **Optimización propuesta** | Nuevo comando `r4b-observe`: registro por ventana de 20 s de p99/SCLK/T/P + escala `s*`, sin escribir nada (instrumentación pasiva del harness v2.3 ya read-only). |
| **Mecanismo técnico** | Sampler 10 Hz (temp/SCLK/P/busy) + marcación de ventanas anclada a t0; lógica en el runner, ningún actuador. |
| **Evidencia local** | Harness R4B read-only ejecutado 8/8 en S1 (hashes `1aa8aa85…`, `922c429b…` intactos); física térmica N=2 reproducible (±1.6 % rampa); `marcar_ventanas.py` validado en S1. `FASE-R4B-GOVERNOR/EXP-F4-A-RESULTADOS-v2.3.md` §C–D. |
| **Evidencia externa** | — (ninguna requerida). |
| **Variable que modifica** | Ninguna (solo logs/CSV del harness). |
| **Componente que toca** | Runner/telemetría de rx550-torneo. |
| **Riesgo** | Nulo (read-only). |
| **Reversibilidad** | N/A (no toca estado). |
| **Cómo medirla** | Correlación entre `mark=CONFOUNDED` y (T_max, SCLK_min) en datos ya guardados. |
| **Baseline requerido** | DPM auto, cap 35 W, idle nv0/P<4 W, GPU sin clientes. |
| **Métrica primaria** | `T_max` y `SCLK_min` por ventana (hoy solo post-hoc). |
| **Métricas secundarias** | p99, power_avg_steady, count bajo-1071. |
| **Criterio PASS** | Marcado automático reproduce §6.3 (dist1 v5–v9, dist2 v6–v9) sobre datos S1. |
| **Criterio FAIL** | El marcado difiere del manual en ≥1 ventana. |
| **Categoría** | **A** |
| **UNKNOWNs restantes** | Umbral “sostenido ≥15 s” del §6.3 sin validación estadística. |
| **Dependencias** | Ninguna. |
| **¿rx550-torneo?** | Sí: sampler M1 (`logger-driver.out`, 10 Hz) ya es compatible. |

### A-03 · THERM-OBS — Presupuesto térmico como aviso (t90 estimado)

| Campo | Valor |
|---|---|
| **Optimización propuesta** | Extender el runner con modelo `t90 ≈ (90 − T_entrada) / rampa` y emitir alerta antes de cruzar 90/92 °C; registrar T_max/SCLK_min por ventana en `metrics.json`. |
| **Mecanismo técnico** | Rampa medida (0.31 °C/s sin governor; 0.246–0.252 °C/s con governor); margen 49→90 °C = ~100–172 s para la carga DIST. |
| **Evidencia local** | `FASE-R4B-THERMAL-TEST/RESULTADOS-TEST-TERMICO.md` (N=2: 90 °C a 169/136 s, recuperación 255–270 s); `RESULTADOS-MINITEST-7.3-B.md` (t90 alineado a m0: 171.9/134.8 s; no hay resultado completo desde 35 °C); S1-v2.3: t0+100–120 s en ventanas DIST confounded. |
| **Variable que modifica** | Ninguna (alerta/salida del runner). |
| **Componente que toca** | Sampler M1 (read-only). |
| **Riesgo** | Nulo. |
| **Reversibilidad** | N/A. |
| **Cómo medirla** | Comparar predicción t90 vs cruce real en trials ya guardados. |
| **Baseline requerido** | Entrada térmica registrada (≤50 °C). |
| **Métrica primaria** | T_max por ventana vs 90 °C (y 96 °C abort). |
| **Métricas secundarias** | SCLK_min/under_pct, `W_SMU` steady. |
| **Criterio PASS** | Predice cruce ±15 s en datos S1 (dist1 v5, dist2 v6). |
| **Criterio FAIL** | Error >30 s o falso negativo (cruce sin aviso). |
| **Categoría** | **A** (como aviso; NO como garantía) |
| **UNKNOWNs restantes** | Rampa con cap reducido (25–28 W) en este chasis (1 punto mini-test). |
| **Dependencias** | Ninguna. |
| **¿rx550-torneo?** | Sí, C2: “presupuesto térmico como aviso” (evidencia SÍ como aviso, NO como garantía). |

### A-04 · ENV-01 — Precondición de exclusividad GPU y diagnóstico de cooldown

| Campo | Valor |
|---|---|
| **Optimización propuesta** | En preflight y en cada cooldown: inventariar clientes de `renderD129`/`card1` (lsof/fuser) y abortar con diagnóstico explícito si `SCLK nv0 ∧ P<4 W` no converge en plazo corto, en vez de esperar 3600 s a ciegas. |
| **Mecanismo técnico** | La no convergencia con `T≤50 °C` es compatible con carga externa; no demuestra por sí sola carga externa ni fallo HW. La causa raíz permanece `UNKNOWN`. |
| **Evidencia local** | `results/logs/session2-v23.log` (T=49 °C, sclk=7, P=6.395 W, timeout 3600 s → rc=9); patrón externo 100 %/1071/~6.4 W desde ~03:45 (logger micro12); pre_flight S2 con P=3.281 W y T=65 °C. |
| **Variable que modifica** | Gates de arranque/cooldown del runner (sin tocar GPU). |
| **Componente que toca** | `run_all_v23.sh`/preflight de experimentos; preflight de torneo. |
| **Riesgo** | Bajo (solo gates). |
| **Reversibilidad** | Completa (se revierte quitando el gate). |
| **Cómo medirla** | Tiempo de cooldown (esperado 150–345 s) y estado P/SCLK en reposo pre-fase. |
| **Baseline requerido** | Idle firma: busy 0 %, SCLK nv0, T≈44–49 °C, P<4 W. |
| **Métrica primaria** | `cooldown_dur_s`, `ret_sclk_nivel`, `ret_power_uW`. |
| **Métricas secundarias** | nº clientes abiertos en node render. |
| **Criterio PASS** | Cooldown converge y, si no, se diagnostica cliente en ≤60 s. |
| **Criterio FAIL** | Timeout silencioso o inicio de trial con GPU no idle. |
| **Categoría** | **A** |
| **UNKNOWNs restantes** | Identidad del cliente en el instante del evento (PIDs no re-verificables en artefactos guardados; solo el patrón mecánico está registrado). |
| **Dependencias** | Ninguna. |
| **¿rx550-torneo?** | Sí: `gpu_finder` ya separa Intel/RX 550; añadir `verify` de exclusividad al preflight FASE2/3/M1. |

### A-05 · TOR-CD — Cooldown alineado a DN-07 en rx550-torneo

| Campo | Valor |
|---|---|
| **Optimización propuesta** | Alinear constantes de cooldown de M1 con la condición R4B verificada: fin = `temp≤50 °C s30 ∧ SCLK nv0 ∧ P<4 W` (hoy 45 °C/30 s, compatible pero sin SCLK/P). |
| **Mecanismo técnico** | Refinamiento del criterio de fin de cooldown (registro de SCLK nv0 y P<4 W además de T). |
| **Evidencia local** | S1-v2.3: 8/8 cooldowns 150–341 s con entrada 49 °C/nv0/3.36 W; S2 cooldown1 345 s OK con retorno análogo. `RESULTADOS-TEST-TERMICO.md` (255–270 s desde ~74 °C). |
| **Variable que modifica** | Constantes del runner (`cap_run.py`). |
| **Componente que toca** | Capa de control de corrida (software). |
| **Riesgo** | Bajo; el 45 °C actual ya cumple la condición R4B (45 < 50). |
| **Reversibilidad** | Parámetro configurable. |
| **Cómo medirla** | cooldown_dur_s vs curva medida. |
| **Baseline requerido** | Idle térmico (≤50 °C, nv0, P<4 W). |
| **Métrica primaria** | tiempo para condición DN-07 completa. |
| **Métricas secundarias** | T, SCLK, P en el instante de fin. |
| **Criterio PASS** | El runner no inicia trial con SCLK>0 o P≥4 W. |
| **Criterio FAIL** | Trial iniciado con GPU activa. |
| **Categoría** | **A** |
| **UNKNOWNs restantes** | Ninguna relevante (condición operativamente verificada). |
| **Dependencias** | Ninguna. |
| **¿rx550-torneo?** | Sí (C4): alinear `COOLDOWN_TEMP_MC`/escensitica de M1. |

### A-06 · MES-AB — Regla de control del sample-loc-bug/MSAA en A/B

| Campo | Valor |
|---|---|
| **Optimización propuesta** | Regla de método: todo A/B con MSAA/small-prim-filter debe controlar el filtro de sample locations y el line-filter (levers de Mesa/radeonsi), para no atribuir a “MSAA” lo que causan erratas verificadas. |
| **Mecanismo técnico** | `has_msaa_sample_loc_bug` (POLARIS10..12) alterna `SMALL_PRIM_FILTER_ENABLE`; `LINE_FILTER_DISABLE(family≤POLARIS12)`; bug #96908 (fix d938b8c) — radeonsi ya los aplica; es regla de interpretación. |
| **Evidencia local** | R0-3 [VERIFICADO]; R1-8 §9 “MSAA sample loc bug en POLARIS12 = VERIFICADO presente”; Matriz J (H-1) le da la mayor potencia explicativa sobre el 3.13× de E5. |
| **Evidencia externa** | Postas mesa-dev 2017-03, bug #96908, Fossies `si_state_msaa.c` (fuentes en R0-3). |
| **Variable que modifica** | Ninguna hoy (regla de método); driconf/env en un A/B futuro. |
| **Componente que toca** | Protocolo de experimentos (documental). |
| **Riesgo** | Nulo. |
| **Reversibilidad** | N/A. |
| **Cómo medirla** | Checklist de control de filtro en fichas GEO/FRAG. |
| **Baseline requerido** | — |
| **Métrica primaria** | Presencia del control en el diseño A/B. |
| **Métricas secundarias** | — |
| **Criterio PASS** | A/B MSAA declara filtro controlado. |
| **Criterio FAIL** | A/B MSAA sin control de filtro (invalida). |
| **Categoría** | **A** |
| **UNKNOWNs restantes** | Estado exacto del código local Mesa 26.2.2 (no leído); GAP-11 (efecto real sin medir → candidato C-09). |
| **Dependencias** | Ninguna. |
| **¿rx550-torneo?** | Indirecto (regla para FASE F/Q futuras). |

### A-01 · SEL-01 — Selección VK determinística de la RX 550

| Campo | Valor |
|---|---|
| **Optimización propuesta** | Estandarizar la selección de la RX 550 en Vulkan por **ICD** (`VK_ICD_FILENAMES=…/radeon_icd.x86_64.json`) o **nombre**, prohibiendo `MESA_VK_DEVICE_SELECT=1002:699f` (roto). |
| **Mecanismo técnico** | Loader Vulkan: por nombre/default selecciona AMD 0x699F 3/3; por ID numérico selecciona Intel 0x412 3/3 (bug de capas/Mesa 26.2.2, UNKNOWN). |
| **Evidencia local** | `INVALIDACION-corridas-04-09.md` (FPS iGPU 2876–3395, card1 idle); EP-05 (ambos brazos forzados a radeon por ICD). |
| **Variable que modifica** | Env por proceso (cero sysfs). |
| **Componente que toca** | Configuración de ejecución del workload. |
| **Riesgo** | Nulo (reversible quitando env). |
| **Reversibilidad** | 100 %. |
| **Cómo medirla** | Verificación runtime device 0x699F + telemetría card1 no-idle. |
| **Baseline requerido** | — |
| **Métrica primaria** | device físico 0x699F en runtime. |
| **Métricas secundarias** | FPS del workload (coherencia con histórico). |
| **Criterio PASS** | 3/3 runs con 0x699F. |
| **Criterio FAIL** | Cualquier run en 0x412. |
| **Categoría** | **A** (corrección de configuración, no palanca de rendimiento) |
| **UNKNOWNs restantes** | Por qué el ID numérico seleccionaba AMD el 17/09 y hoy Intel. |
| **Dependencias** | Ninguna. |
| **¿rx550-torneo?** | Sí: ya usa ICD + verificación; estandarizar en runner. |

### A-07 · GPU-ID — Verificación dual + baseline de estado (runtime PM y cap)

| Campo | Valor |
|---|---|
| **Optimización propuesta** | Adoptar como requisito de baseline de TODO experimento: verificación dual (0x1002:699f objetivo, 0x8086:0412 Intel NO-display) + captura de los 6 nodos RESTORABLE_FIELDS + `runtime_status` + `power1_cap` antes/después. |
| **Mecanismo técnico** | `gpu_finder.py` (TARGET_IS_DISPLAY/INTEL_NOT_DISPLAY) + `state_manager` (snapshot SHA-256, escritura atómica, flock); spec §29; whitelist `guard_no_sys_write`. |
| **Evidencia local** | Torneo Fase 1–3 + M1: 65/55/56/112 checks OK; M1 `readback_final=35000000` 10/10; ausencia de writes en todos los runs read-only. |
| **Variable que modifica** | Ninguna (relé integral de seguridad). |
| **Componente que toca** | Infraestructura del runner (software). |
| **Riesgo** | Nulo; previene tocar Intel y estado permanente incorrecto. |
| **Reversibilidad** | N/A (es el mecanismo de reversión). |
| **Cómo medirla** | Checks del suite + hashes pre/post. |
| **Baseline requerido** | state.json previo + hash. |
| **Métrica primaria** | `readback_final == original` por nodo. |
| **Métricas secundarias** | nº writes por nodo (≤2). |
| **Criterio PASS** | Rollback verificado post-run. |
| **Criterio FAIL** | Readback mismatch sin rollback. |
| **Categoría** | **A** (ya implementado; se adopta como regla) |
| **UNKNOWNs restantes** | Ninguno. |
| **Dependencias** | Ninguna. |
| **¿rx550-torneo?** | Sí — ya existe (C8/C9). |

### A-08 · R0-POL — Política de catálogo de event IDs (sin rango semántico seguro)

| Campo | Valor |
|---|---|
| **Optimización propuesta** | Regla del proyecto: citar GPUPerfAPI v3.17 como catálogo de referencia y v3.11.1 como historial; no usar rangos como garantía semántica; no programar contadores. |
| **Mecanismo técnico** | 2304 filas de catálogo no equivalen a eventos validados; v4.0+ eliminó GCN; UMR/radeontop no son fuente de eventos. |
| **Evidencia local** | `R0-1-GFX8-EVENT-ID-REFERENCE.txt` (2304 filas); R1-1 (19/23); semántica/aplicabilidad `UNKNOWN`. |
| **Evidencia externa** | README/RELEASE_NOTES GPUPerfAPI (fuente citada en R0-6). |
| **Variable que modifica** | Flujo de trabajo documental. |
| **Componente que toca** | Documentación/diseño (sin sistema). |
| **Riesgo** | Nulo. |
| **Reversibilidad** | N/A. |
| **Cómo medirla** | No aplica (política). |
| **Categoría** | **A** |
| **UNKNOWNs restantes** | Semántica/unidad MC (UNRESOLVED) — prohibe normalizar banda MC. |
| **Dependencias** | Ninguna. |
| **¿rx550-torneo?** | No (herramientas de investigación). |

### A-09 · R4A-CON — Constraint PCIe Gen2×4 en planificación

| Campo | Valor |
|---|---|
| **Optimización propuesta** | Planificar todo diseño de transferencias host↔GPU bajo techo 2.0 GB/s por sentido; descartar “mejoras de enlace por software”. |
| **Mecanismo técnico** | Techo HW del root port 00:01.0 (5.0 GT/s Gen2); el endpoint es Gen3×8 pero la plataforma no negocia más. |
| **Evidencia local** | `EXP-F3-A-BANDWIDTH-REAL.md` (VERIFIED: Gen2×4; max root port 5.0 GT/s); corroborado en `FASE-D-ETAPA-3-PRECHECK.md`. |
| **Variable que modifica** | Modelo/planificación. |
| **Riesgo** | Nulo. |
| **Reversibilidad** | N/A. |
| **Categoría** | **A** (constraint verificado) |
| **UNKNOWNs restantes** | ¿×8 Gen2 en otro slot? (UNKNOWN, irrelevante: ≪ VRAM). |
| **Dependencias** | Ninguna. |
| **¿rx550-torneo?** | Indirección (decisiones de alojamiento de memoria, B-05/B-06). |

### A-10 · DOC-REC — Reconciliar documentación heredada

| Campo | Valor |
|---|---|
| **Optimización propuesta** | Corregir en el repo las cifras pre-R-4A contradictorias (“PCIe Gen3×8 negociado” en POLARIS12-MAP; “501 GB/s” en FASE-G; “×24–32” en ASSUMPTION-AUDIT/R3-1). |
| **Mecanismo técnico** | Actualización documental únicamente (con aval del usuario; no se ejecuta en esta auditoría). |
| **Evidencia local** | EXP-F3-A sysfs vs POLARIS12-MAP.md:183/230, FASE-G-MEMORY-VRAM-GTT-DESIGN.md:42, ASSUMPTION-AUDIT §7. |
| **Categoría** | **A** (documental; requiere decisión del usuario) |
| **¿rx550-torneo?** | No. |

---

## 8. Candidatos B — IMPLEMENTABLE CON A/B

### B-01 · GOV-01 — Detención en el primer escalón en banda (0.87) / escalón intermedio 0.93

| Campo | Valor |
|---|---|
| **Optimización propuesta** | Cambiar la regla de selección de `s* = max{s : P99(s) ≤ T}` por “primer escalón descendente dentro de banda” (0.87) o añadir escalón 0.93. Expectativa: p99 ≈ 9.33 ms ≤ T=9.153 ms, recuperando ~2.3 ms de latencia sacrificada a 0.75. |
| **Mecanismo técnico** | El governor tocaría menos el rendimiento manteniendo p99 dentro de banda; el paso 1.00→0.87 ya asienta en 1.02·T. |
| **Evidencia local** | S1-v2.3 gov1–3, v4–v6: p99 settle 9326–9339 µs, r≈1.0194–1.0197 (3/3 en banda [8.251, 10.085]); R6 FAIL (settle 0.87 vs s\*=0.75); curva congelada 11.441/9.337/7.037 ms. **(n=3, NO población)** |
| **Variable que modifica** | Regla de `s*` en el governor (render-scale de la app — nivel SOFTWARE, reversible por frame). |
| **Componente que toca** | Harness R4B / futuro runner governor. |
| **Riesgo** | Bajo (paramétrico, sin sysfs nuevo). |
| **Reversibilidad** | Total (config). |
| **Cómo medirla** | R1–R4 (r en banda, overshoot, reversiones, convergencia) con muestra completa n=6. |
| **Baseline requerido** | No se reintenta S2-v2.3. Una futura A/B requiere un protocolo nuevo, T_run explícita y autorización nueva. |
| **Métrica primaria** | r = p99_settle / T ∈ [0.90, 1.10]. |
| **Métricas secundarias** | Δ% vs FIXED; overshoot %; nº reversiones; convergencia. |
| **Criterio PASS** | R1 ≥5/6 + R3 ≥5/6 + converge ≤4 ventanas + Δ vs fixed ≤ −10 %. |
| **Criterio FAIL** | r fuera de banda >1 ventana o reversiones sostenidas. |
| **Categoría** | **B** |
| **UNKNOWNs restantes** | Comportamiento de 0.93 nunca medido en este repo; estabilidad del settle con paso menor. |
| **Dependencias** | No se reintenta S2-v2.3. Futura réplica: protocolo/autorización nuevos, ENV-01 y telemetría A-02/A-03. |
| **¿rx550-torneo?** | Alta: loop de governor por ventana = subcomando `governor` reutilizando `gpu_finder`/`state_manager`/`failsafe`; cualquier escritura requiere autorización separada. |

### B-02 · GOV-02 — Ventana de decisión 30–60 s o EMA multi-ventana

| Campo | Valor |
|---|---|
| **Optimización propuesta** | Sustituir decisión por ventana única de 20 s por ventanas de 30–60 s o EMA del p99. |
| **Mecanismo técnico** | La ventana de 20 s contiene la cola de frames del cambio de escala (lays 4→8); mayor ventana separa transitorio de estado estacionario. |
| **Evidencia local** | R4 no cumple literal en S1 (convergencia en ventana 5); diagnóstico n=3, no PASS/FAIL formal. |
| **Variable que modifica** | `WINDOW_S` en harness/analyze/gov loop (software). |
| **Riesgo** | Bajo (paramétrico; aumenta latencia de reacción y acerca a t90). |
| **Reversibilidad** | Total. |
| **Cómo medirla** | Recomputar R1–R4 y overshoot sobre telemetría/run_frames YA guardados (read-only). |
| **Baseline requerido** | Datos S1 v2.3 (guardados). |
| **Métrica primaria** | convergencia ≤4 ventanas con nueva W. |
| **Métricas secundarias** | overshoot %, reversiones. |
| **Criterio PASS** | settle estable en ≤4 ventanas sin revertir. |
| **Criterio FAIL** | Empeora overshoot o desconverge. |
| **Categoría** | **B** |
| **UNKNOWNs restantes** | Estacionariedad de vkmark >20 s; interacción con presupuesto térmico. |
| **Dependencias** | B-01, B-04 (ventanas largas solo en fixed/gov, no dist). |
| **¿rx550-torneo?** | Alta: lógica de control dentro del runner M1. |

### B-03 · GOV-03 — Grilla de escalas intermedias (0.93/0.86/0.80)

| Campo | Valor |
|---|---|
| **Optimización propuesta** | Refinar la grilla {1.00, 0.87, 0.75, 0.62, 0.50} con pasos de ~0.06–0.07 para reducir el overshoot por paso. |
| **Mecanismo técnico** | R2 (overshoot 65–70 %) es consecuencia del paso brusco 1.00→0.87; pasos pequeños mantienen la caída por paso bajo control. La curva 0.87→0.75 es casi lineal (9.337→7.037 ms) → interpolable (no medida). |
| **Evidencia local** | R2 FAIL overshoot 65.7–70.38 % en el paso ejecutado; curva manifest. (n=3 + interpolación, no medida en 0.93/0.86.) |
| **Variable que modifica** | Grilla de escalas en protocolo/harness (software). |
| **Riesgo** | Medio-bajo (más bloques por sesión → más riesgo térmico). |
| **Reversibilidad** | Total (config). |
| **Cómo medirla** | Fase-1 de 7–8 escalas con gates v2.3; luego overshoot por paso en R2. |
| **Baseline requerido** | Misma app/T/s\*. |
| **Métrica primaria** | overshoot % del literal R2 (≤1 % por ventana en el límite del diseño). |
| **Métricas secundarias** | p99 por escala; tiempo total de sesión; T_max. |
| **Criterio PASS** | R2 alcanza literal con la nueva grilla (>5/6). |
| **Criterio FAIL** | Más bloques exceden el presupuesto térmico de la sesión. |
| **Categoría** | **B** |
| **UNKNOWNs restantes** | p99 de 0.93/0.86 nunca medido (solo interpolado). |
| **Dependencias** | B-04 (presupuesto térmico). |
| **¿rx550-torneo?** | Alta: grilla configurable en el runner. |

### B-04 · T-01 — DIST acotado por presupuesto térmico

| Campo | Valor |
|---|---|
| **Optimización propuesta** | (a) Acortar `dist` a ≤120 s, o (b) mantener un cap declarado ~25–28 W,
  o (c) diseñar pausas; todas son alternativas de diseño y requieren protocolo/autorización. |
| **Mecanismo técnico** | No existe `t90(35 W)` universal. Las réplicas alineadas a `m0` mostraron 171.9 s (T(m0)=44 °C) y 134.8 s (T(m0)=55 °C); con entrada ≤50 °C el DIST de 200 s no se demostró íntegro. La opción ≤35 °C es histórica y no verificada. |
| **Evidencia local** | dist1 CONFOUNDED v5–v9, dist2 v6–v9 (S1); `RESULTADOS-TEST-TERMICO.md` (N=2); mini-test 7.3-B (N=2: 92 °C pre-final). R7 NOT FOR VERDICT. |
| **Variable que modifica** | `RUN_DURATION_DIST` y/o `power1_cap` por trial (D — sysfs con protocolo M1/FASE3 ya validado). |
| **Componente que toca** | Harness/runner; cap por trial. |
| **Riesgo** | Bajo solo con el patrón SET→workload→RESTORE; 90 °C es confound y 96 °C
  es el abort configurado; no se ejecuta aquí. |
| **Reversibilidad** | Total (parámetros + restore readback). |
| **Cómo medirla** | T_max y SCLK_min por ventana con la nueva configuración; reclasificar con §6.3. |
| **Baseline requerido** | Entrada ≤50 °C; GPU sin clientes. |
| **Métrica primaria** | Nº ventanas CONFOUNDED = 0 en `dist`. |
| **Métricas secundarias** | T_max, SCLK_min, p99 por ventana. |
| **Criterio PASS** | DIST medible íntegro (0 ventanas confounded) y R7 computable. |
| **Criterio FAIL** | Cualquier ventana vuelve a cruzar 90 °C. |
| **Categoría** | **B** |
| **UNKNOWNs restantes** | Rampa real con cap 25–28 W (1 punto mini-test); efecto de pausas en cola de frames. |
| **Dependencias** | A-03 (telemetría por ventana), B-02. |
| **¿rx550-torneo?** | Alta: M1 (`cap_run.py`) ya implementa SET/RESTORE con abort y guard. |

### B-05 · R4A-02 — Política de alojamiento GTT vs VRAM (hot set)

| Campo | Valor |
|---|---|
| **Optimización propuesta** | DEVICE_LOCAL para datos re-leídos; GTT solo si se re-leen N veces y L2 amortiza; evaluar con A/B frametime/power. |
| **Mecanismo técnico** | Asignación de memoria por API (VK_MEMORY_PROPERTY_*), política TTM/amdgpu; sin tocar kernel. |
| **Evidencia local** | R4A: ratio ×48–80; GTT 6.2 GB no constante; VIS 256 MiB; moverate 8 MB/s. FUSION-03: versión débil PARTIALLY VERIFIED y defendible. |
| **Evidencia externa** | GPUOpen (DCC no ahorra PCIe); TTM moverate (PRIOR-ART-INDEX). |
| **Variable que modifica** | Dominio de memoria de la app (software). |
| **Riesgo** | Medio (VRAM 2 GiB limitada; eviction lenta a 8 MB/s). |
| **Reversibilidad** | Total (solo asignación). |
| **Cómo medirla** | A/B frametime/power con data GTT vs VRAM (FUSION-03 §6 falsable). |
| **Baseline requerido** | Bandwidth real (C-02) idealmente; de lo contrario techo teórico 2.0 GB/s. |
| **Métrica primaria** | Δ frametime p99 VRAM vs GTT. |
| **Métricas secundarias** | power_avg_steady; mem_info_*_used. |
| **Criterio PASS** | GTT con re-lectura ≥ N mejora/mantiene frametime y baja PCIe. |
| **Criterio FAIL** | Empeora frametime > umbral del CV intra-brazo. |
| **Categoría** | **B** |
| **UNKNOWNs restantes** | GTT real ≈ 2 GB/s?; modelo “L2 amortiza re-lecturas” no validado en esta GPU. |
| **Dependencias** | C-02 (bandwidth real) como precondición recomendada. |
| **¿rx550-torneo?** | Posible (política de asignación en el workload del harness). |

### B-06 · R4A-04 — Buffer VIS-VRAM 256 MiB (render pequeño→VIS)

| Campo | Valor |
|---|---|
| **Optimización propuesta** | Alojar superficies host-visible dentro del BAR (VIS-VRAM 256 MiB) y evitar spill a GTT (que cruza PCIe al máximo). |
| **Mecanismo técnico** | Asignaciones HOST_VISIBLE acotadas a 256 MiB vía Vulkan/amdgpu. |
| **Evidencia local** | VIS-VRAM 268435456 B VERIFIED (EXP-F3-A); ratio enlace/VRAM ×48. FUSION-03: “la lógica ‘render pequeño→VIS’ es viable y es el sub-producto útil”. |
| **Variable que modifica** | Dominio de memoria de superficies (software). |
| **Riesgo** | Bajo (cap duro 256 MiB; exceso = GTT). |
| **Reversibilidad** | Total. |
| **Cómo medirla** | log `mem_info_vis_vram_used` vs `gtt_used`; A/B frametime/power vs baseline GTT. |
| **Métrica primaria** | % de superficies host-visible en VIS; Δ frametime. |
| **Categoría** | **B** |
| **UNKNOWNs restantes** | Bandwidth VIS real (no medido); DCC-on-GTT si se spill. |
| **Dependencias** | C-02 recomendada. |
| **¿rx550-torneo?** | Posible (asignación en runner/harness). |

### B-07 · MCLK-AB — Encarrilamiento de MCLK a 1500 MHz (A/B controlado)

| Campo | Valor |
|---|---|
| **Optimización propuesta** | A/B controlado de forzar MCLK al nivel 2 (`pp_dpm_mclk`) bajo protocolo FASE I/L (snapshot→write→readback→restore→readback) para medir impacto real en frametime/potencia de cargas de memoria. |
| **Mecanismo técnico** | La política smu7 128-bit 5/16/20 es **source-level**; `EnabledForActivity=1` aparece en la fuente, pero el trigger local y el mapeo de `mem_busy` son `UNKNOWN`. Forzar sería una acción de escritura separada, no una eliminación demostrada de un umbral local. |
| **Evidencia local** | E-03: MCLK 1500 con `mem_busy` 36–49 %; E-01/E-02: 300 con 3–7 %. Son observaciones correlacionales; R-07 + R0-2 documentan la política, no validan el ASIC. |
| **Evidencia externa** | `smu7_hwmgr.c` (commits 8d89b96…, 7d892ca…) vía R0-2. |
| **Variable que modifica** | `pp_dpm_mclk` (sysfs — D, NO AUTORIZADO hoy). |
| **Componente que toca** | PowerPlay/SMU7. |
| **Riesgo** | Medio (write; “WRITE SUCCESS ≠ STATE CHANGE VERIFIED”; puede elicitar estados inesperados). |
| **Reversibilidad** | Con protocolo obligatorio + restore readback (R1-10 §D.4). |
| **Cómo medirla** | A/B MCLK 625 vs 1500 en carga de memoria; telemetría 10 Hz. |
| **Baseline requerido** | DPM auto, cap 35 W, idle nv0. |
| **Métrica primaria** | Δ frametime p99; Δ power_avg_steady. |
| **Métricas secundarias** | mem_busy, T_max. |
| **Criterio PASS** | Δ medible y estable > CV intra-brazo, sin aborts. |
| **Criterio FAIL** | Δ ausente o inestable. |
| **Categoría** | **B** (hipótesis sólida; requiere A/B y autorización) |
| **UNKNOWNs restantes** | Comportamiento SMU real de la unidad (VBIOS/pptable); efecto en latencia/estabilidad no medido; GAP-10 (DPM intermedios). |
| **Dependencias** | Autorización; FASE I/L; ENV-01. |
| **¿rx550-torneo?** | Posible en FASE 3 vía `pp_dpm_mclk` con `verify_authorized` (extiende whitelist). |

---

## 9. Candidatos C — REQUIERE MÁS INVESTIGACIÓN

### C-01 · CNT-12 — Instrumentación de contadores GFX8 (etapa 3, 12 slots)

| Campo | Valor |
|---|---|
| **Optimización propuesta** | Atribuir potencia/bottleneck con contadores HW (12 slots: GRBM×2, GRBMSE×2, SX×1, TCC×2, TCA×1, CB×1, DB×1, MC_ARB×2); solo diseño, no autorización. |
| **Mecanismo técnico** | Escritura de `*_PERFCOUNTERn_SELECT` requeriría una tupla evento/ASIC/instancia verificada; no se asumen rangos ni semántica; ventana CP y restauración quedarían subjects a protocolo separado. |
| **Evidencia local** | Mapa de registros (FASE-D-ETAPA-3-EVENTS/PRECHECK); GRBM=2/SQ=4 `CATALOG ONLY`; 19/23; MC/aplicabilidad `UNKNOWN`. |
| **Evidencia externa** | GPUPerfAPI v3.17 catálogo; v3.11.1 histórico; 2304 filas no eventos validados. |
| **Variable que modifica** | Registros MMIO PERF_SEL (F — NO AUTORIZADO). |
| **Riesgo** | Medio-alto (perturbación de la carga K8; requiere root); bloqueado por autorización. |
| **Reversibilidad** | Protocolo snapshot→write→readback→restore. |
| **Cómo medirla** | A/B idéntico a etapa 2 (`W_SMU` 22.25 vs 15.78 W) con contadores; no causalidad automática. |
| **Categoría** | **C** |
| **UNKNOWNs restantes** | Instancias por fuses (GAP-08); semántica MC (GAP-09); equivalencia `index=PERF_SEL` Media-Alta (deducida). |
| **Dependencias** | Autorización explícita + PRE read-only + sanity idle (R1-10 §A). |
| **¿rx550-torneo?** | No hasta autorización (PolarisLens = provisional). |

### C-02 · R4A-01 — Medición de bandwidth real

| Campo | Valor |
|---|---|
| **Optimización propuesta** | Cerrar el UNKNOWN estructural de R-4A midiendo GB/s reales por dominio (GTT/VIS/VRAM/DMA). |
| **Mecanismo técnico** | Lectura de `amdgpu_benchmark` (`.read` = usage, inocua) bajo sudo autorizado, o gpu-pcie-bench-style; sin tocar moverate/VM. |
| **Evidencia local** | EXP-F3-A §4: “No hay interfaz de lectura sin ejecutar pruebas… cerrar con corrida autorizada”. |
| **Variable que modifica** | Ninguna (medición). |
| **Riesgo** | Bajo (read); `.write` prohibido (corre benchmarks). |
| **Categoría** | **C** |
| **Dependencias** | Autorización sudo read + Lab K. |
| **¿rx550-torneo?** | Precondición de B-05/B-06. |

### C-03 · R4A-03 — Compresión delta en aplicación

| Campo | Valor |
|---|---|
| **Optimización propuesta** | Comprimir el hot set en CPU antes del cruce PCIe (byte-over-wire), descomprimir en GPU. |
| **Mecanismo técnico** | Delta-compresión en app + descompresión en 8 CUs; integración con RX-Compression-Engine (no construido). |
| **Evidencia local** | Techo 2.0 GB/s por sentido; FUSION-03: fuerte CONTRADICTED, débil defendible. |
| **Riesgo** | Coste de descompresión no medido (1.2 TFLOPS). |
| **Categoría** | **C** |
| **UNKNOWNs restantes** | Fracción de payload real; ratio de re-lectura del tile GTT-residente. |
| **Dependencias** | C-02; señal de FASE G. |
| **¿rx550-torneo?** | No (proyecto RX-Compression-Engine bloqueado por falta de señal). |

### C-04 · R4A-06 — Identificación de módulo GDDR5 (6 vs 7 Gbps)

| Campo | Valor |
|---|---|
| **Optimización propuesta** | Fijar 96 vs 112 GB/s leyendo memtype/VBIOS espejo (sudo read-only). |
| **Evidencia local** | EXP-F3-A §3 (cross-check R9 290/RX 480). |
| **Riesgo** | Bajo. |
| **Categoría** | **C** |
| **Dependencias** | Autorización de lectura VBIOS. |

### C-05 · WL-GFX-01 — Workload sintético ≥20 W

| Campo | Valor |
|---|---|
| **Optimización propuesta** | Llegar a `W_SMU` ≥20 W (camino hacia discriminar 35 vs 30 W): E-03 logró 15.75 W steady + MCLK 1500. |
| **Mecanismo técnico** | CB con entropía, texturas 4×4096² > L2, política 5/16/20 **source-level**; techo observado ~16 W con DPM auto. |
| **Evidencia local** | E-03 (`W_SMU` 13.4/15.75 W); ES-01 y F2 planos; Superposition (22.31 W) es una asociación que no prueba que la geometría sea la causa. |
| **Variable que modifica** | Carga (software); WORKLOAD-SINTETICO CONGELADO. |
| **Riesgo** | Bajo (0 faults tras fix R-11); VM faults si storage images. |
| **Categoría** | **C** |
| **UNKNOWNs restantes** | CB bypass-L2 (H-CB-DRAM) [HIPÓTESIS]; política mclk_activity activa sin confirmar al 100 %. |
| **Dependencias** | Descongelar WORKLOAD-SINTETICO (autorización). |
| **¿rx550-torneo?** | No (rama separada hasta evidencia). |

### C-06 · DCC-01 — Derrota de DCC / entropía de CB

| Campo | Valor |
|---|---|
| **Optimización propuesta** | Cuantificar cuánta entropía de CB hace que DCC deje de comprimir; levers `radv_disable_dcc=1`/usage flags. |
| **Evidencia local** | R-06 (DCC 8:1, deps); `RADV_DEBUG=nodcc` no eliminó VM faults (R-11); H-CB-DRAM [HIPÓTESIS] solo documentada en Tahiti GCN1. |
| **Riesgo** | Bajo (env). |
| **Categoría** | **C** |
| **UNKNOWNs restantes** | Micro-bench de entropía (§9 DESIGN-GRAPHICS) NO hecho. |

### C-07 · GEO-01 — Vertex throughput

| Campo | Valor |
|---|---|
| **Optimización propuesta** | Determinar si VS/IA es el cuello real (complejidad VS × instanceCount, `vkCmdDrawIndexedIndirect`). |
| **Evidencia local** | FASE D etapa 2: vgt/pa/sh ∞ A-vs-B; FASE F diseñada (ficha completa); Matriz J ALTA 26/30. |
| **Riesgo** | Bajo (carga); requiere contadores para confirmar. |
| **Categoría** | **C** (diseñado; necesita FASE F autorizada + eventualmente C-01) |
| **¿rx550-torneo?** | No hoy. |

### C-08 · GEO-02 — Primitive throughput

| Campo | Valor |
|---|---|
| **Optimización propuesta** | Micro-triángulos 1–16 px para separar IA/PA del raster (confounders: culling PAPC pre-raster). |
| **Evidencia local** | FASE F (PA_SU PAPC 8/14, PA_SC QZ0 163 — documentales); contadores NO programables sin autorización. |
| **Categoría** | **C** |

### C-09 · FRAG-01 — Sample shading MSAA 8×

| Campo | Valor |
|---|---|
| **Optimización propuesta** | Explicar el 3.13× de E5 (MSAA 4×: −18…−70 %) con sample shading controlado. |
| **Evidencia local** | R2-HISTORICAL-EXPERIMENT-INVENTORY (E5/E3); H-1 (R0-3: sample-loc-bug presente) control obligatorio; GAP-11 sin medir. |
| **Categoría** | **C** |

### C-10 · SHD-01 — Wave32 vs Wave64

| Campo | Valor |
|---|---|
| **Optimización propuesta** | A/B de tamaño de wave para compute (ACO/LLVM, FASE Q). |
| **Evidencia local** | ALU descartada como eje (E5b 1.04–1.14); soporte wave32/64 GFX8 sin documentar. |
| **Categoría** | **C** |
| **¿rx550-torneo?** | No (dominio compilador). |

### C-11 · PWR-01 — Power profile modes

| Campo | Valor |
|---|---|
| **Optimización propuesta** | A/B de perfiles `pp_power_profile_mode` (POWER_SAVING/VIDEO/COMPUTE). |
| **Evidencia local** | DPM caracterizado (E4/E5b); perfil legible; R0-2 (política smu7 coherente: no atribuir a bug lo que es política); efecto real en SMU7/Polaris12 **desconocido**. |
| **Riesgo** | Medio (write); reversibilidad SOLO con snapshot+readback (FASE L). |
| **Categoría** | **C** (B condicional si FASE L habilita writes) |
| **Dependencias** | FASE L; autorización. |

### C-12 · MEM-01 / MEM-03 — VRAM pressure y sparse

| Campo | Valor |
|---|---|
| **Optimización propuesta** | MEM-01: pressure VRAM 50–150 % de 2 GiB (eviction); MEM-03: residencia sparse VK. |
| **Evidencia local** | MEM-01: riesgo OOM ALTO (Matriz J BAJA 20/30); MEM-03: sin ficha de diseño (gap documental). |
| **Riesgo** | Alto (OOM/device lost) → ventana de reinicio obligatoria. |
| **Categoría** | **C** |

### C-13 · DIST35 — DIST con entrada ≤35 °C (opción 7.3-A)

| Campo | Valor |
|---|---|
| **Optimización propuesta** | Diseño histórico de DIST desde ≤35 °C (t90 modelo ≈ 221 s); **no ejecutar ni reintentar** bajo el estado D6. |
| **Evidencia local** | Mini-test 7.3-B: desde ≤50 °C no cabe (92 °C pre-final); modelo 7.3-A (t90 221 s) NO medido aún. |
| **Riesgo** | Alto: entrada ≤35 °C no garantizada; 90 °C es confound y 96 °C abort de un protocolo autorizado. |
| **Categoría** | **C** (requiere prueba autorizada; si falla → D) |
| **¿rx550-torneo?** | No hoy. |

### C-14 · ASY-01 / BERRETA — async compute overlaps

| Campo | Valor |
|---|---|
| **Optimización propuesta** | Aprovechar ACE/HWS con compute async (Overlap de present/filtros). |
| **Evidencia local** | ACE/HWS family-level documentado (whitepaper + fuentes de scheduling); nº ACEs Lexa, overlap y runtime local **UNKNOWN**; BERRETA sin señal experimental. |
| **Categoría** | **C** (bloqueado por falta de señal F/G/H/I) |

### C-15 · I-05 — GFX8 frame recorder (herramienta)

| Campo | Valor |
|---|---|
| **Optimización propuesta** | Evaluar un viewer SQTT GFX8; la existencia del gap/runtime es `UNKNOWN` y requiere capability audit, no build asumido. |
| **Evidencia local** | R3-NOVELTY-MATRIX: PARTIALLY NOVEL; gap SQTT-GFX8 vs RGP NO VERIFICADO. |
| **Categoría** | **C** |

### C-16 · SP-PRESET-01 — Preset/resolución superior de Superposition

| Campo | Valor |
|---|---|
| **Optimización propuesta** | La configuración histórica efectiva `1600×900/Medium` queda cerrada; cualquier preset `1080p/High` sería otro workload y requiere autorización nueva. |
| **Evidencia local** | Config efectiva 1600x900/Medium (fase activa 18.8 W media/23.7 W máx); VRAM 1.63 GiB “sin presión”. |
| **Riesgo** | Bajo; ejecución NO autorizada (R1-10 §B). |
| **Categoría** | **C** |

### C-17 · OVD-01 — Overdrive (ppfeaturemask 0x4000)

| Campo | Valor |
|---|---|
| **Optimización propuesta** | Habilitar Overdrive para undervolt/underclock bajo cap 35 W (estudio FASE L). |
| **Evidencia local** | `ppfeaturemask` 0xfff7bfff sin 0x4000 → OD no disponible; `pp_od_clk_voltage` no verificada para RX 550; campo congelado. |
| **Riesgo** | Alto (política eléctrica); requiere FASE L.0 tras Capability Audit. |
| **Categoría** | **C** |

---

## 10. Candidatos D — DESCARTADO / REFUTADO

| ID | Candidato | Evidencia refutatoria (con número) |
|---|---|---|
| D-01 | **CAP-01** — power1_cap 25–35 W como palanca | Fase B: curva plana 25→35 W (SCLK 1071, `W_SMU` 10.7–11.6 W); M1: ΔFPS=ΔSCLK=0, ΔP IC95% (−0.103, +0.060) W, `W_SMU` 12.27 W < 27 W. Aclaración M1: NO significa “30 W = 35 W para cualquier workload” — descartado probado para los workloads disponibles. |
| D-02 | **MES-01** — Mesa CUSTOM como optimización | EP-05: CUSTOM==STOCK (ΔFPS ≤1 %, ΔP ≤0.3 W, mismo SCLK/MCLK); nunca 25–31 W ni 88–92 °C. |
| D-03 | **SOAK-01** — soak térmico para reproducir E1/E3 | EP-06: 70–71 °C cap 25 W → SCLK 1071, 9.6–11.5 W; no reproduce ni frío ni caliente. |
| D-04 | **KALM-01** — kalm como palanca | EP-06: con kalm activo régimen libre; sin kalm (17/09) régimen regulatorio → dirección opuesta; kalm descartado como causa. |
| D-05 | **WL-SCALE-01** — escalado overdraw/FMA/tex/MSAA/combo | ES-01: todas variantes 15.75–16.18 W (deriva ±0.33 W); MSAA 8× sin efecto en frametime (~112.5 vs 112.1 ms). |
| D-06 | **WL-FRAG-01** — 8 fetchs de fragment | F2: frametime 2× (112→222 ms) pero `W_SMU` 15.76 vs 16.13 W (−0.4 W) y `mem_busy` 36 % idéntica → H-F2 RECHAZADA. |
| D-07 | **WL-COMPUTE-01** — compute ALU puro | E-01 `W_SMU` 13.23 W → E-02 12.38 W (−0.85 W); MCLK 300; `mem_busy` 3–7 %; gate 27 W NO superado. |
| D-08 | **GM-01** — GravityMark 200k como workload M2 | `W_SMU` 12.4 W media / 14.8 W máx; VRAM 2.10/2.00 GB (98 %); `-asteroids 4m` = device lost/OOM (2.86 GB > 2 GB). |
| D-09 | **DIST-200** — DIST 200 s desde ≤50 °C como diseño de trial | Mini-test 7.3-B (N=2): T_max=92 °C antes de completar 200 s; S1: dist1/2 CONFOUNDED. Descarte para entrada ≤50 °C; la opción ≤35 °C queda histórica/no verificada (C-13), no se reintenta. |

---

## 11. Candidatos E — INCONCLUSO (no utilizar todavía)

| ID | Candidato | Motivo |
|---|---|---|
| E-01 | **GOV-TORNEO** — governor como función permanente de rx550-torneo | EXP-F4-A global INCONCLUSO (n=3; S2 sin datos); R2/R4/R6 no cumplen literal en S1; `final()` inaplicable. NO convertir en configuración permanente. Los datos de S1 son diagnóstico, no veredicto. |
| E-02 | **REG17** — régimen E1/E3/E5 + “phong 1285 fps” | [NO REPRODUCIBLE]; linaje de E1 no fiable (O3: 1285 fps @365 MHz “imposible físicamente”); no usar como especificación. |
| E-03 | **R2R4R6** — literales de convergencia del governor (R2/R4/R6 + R5) | Evidencia parcial (n=3): overshoot 65–70 %, convergencia ventana 5, asentamiento 0.87≠0.75; R5 y F1–F6 no computables. Queda inconcluso hasta muestra completa. |

---

## 12. rx550-torneo — qué se puede integrar y cómo

**Regla de integración (spec §17-18, §24, §34-35):** solo se tocan en producción `power/control` (FASE 2) y
`power1_cap` (FASE 3/M1); máx 2 escrituras por nodo; readback obligatorio; rollback 1 intento; sin estado
permanente provocado.

| Candidato | Evidencia suficiente | Controles necesarios | Estado a guardar | Rollback | Verificar GPU (RX550) | Evitar Intel HD4600 | Runtime PM | Temperatura | Evita estado permanente incorrecto |
|---|---|---|---|---|---|---|---|---|---|
| A-02 TOR-OBS (telemetría governor) | SÍ (read-only) | Ninguno nuevo | CSV/audit + state.json | N/A | `gpu_finder` 0x699F | `TARGET_IS_DISPLAY`/`INTEL_NOT_DISPLAY` | lee `power/control` (FASE2) | registro T_max/SCLK_min por ventana | Sin writes: imposible |
| A-03 THERM-OBS (presupuesto t90) | SÍ como aviso; NO como garantía | Modelo t90 + alerta | CSV | N/A | idem | idem | idem | Alerta antes de 90/96 °C | Sin writes |
| A-04 ENV-01 (exclusividad) | SÍ (S2 documentado) | lsof/fuser de renderD129/card1 en preflight | audit.json | N/A | idem | idem | idem | Cooldown hasta ≤50 °C + nv0 + `W_SMU` <4 W | Sin inicio con GPU activa |
| A-05 TOR-CD (cooldown alineado) | SÍ (8/8 S1; 345 s S2) | Criterio `≤50 °C s30 ∧ nv0 ∧ W_SMU<4 W` | cooldown tsv | Restore M1 | idem | idem | idem | Alinear a DN-07 | Criterio más estricto que 45 °C actual |
| B-01 GOV-01 (escala de render) | NO (veredicto INCONCLUSO; n=3) — no se reintenta S2 | Governor por ventana, T_run explícita, sin clientes | state + control_scale | clears por frame (software) | idem | idem | sin cambio | Presupuesto t90 documentado por condición | Reversible por config; solo SOFTWARE |
| B-04 T-01 (DIST y cap) | PARCIAL (térmica N=2) | cap por trial SET/RESTORE (patrón M1) | audit + telemetría | RESTORE + readback (cap_run) | idem | idem | sin cambio | 90 °C confound; 96 °C abort; cooldown 45 °C/30 s | Guard SIGKILL + restore_needed |
| B-07 MCLK-AB (pp_dpm_mclk) | PARCIAL (política VERIFICADA; efecto sin medir) | snapshot→write→readback→restore→readback; FASE I/L | 6 nodos RESTORABLE_FIELDS | 1 intento + readback | idem | idem | sin cambio | Presupuesto t90 | Extiende whitelist SOLO con autorización |

**Punto crítico:** ninguna integración de governor como *función de render* es autorizable hoy porque el
EXP-F4-A es INCONCLUSO. B-01 queda como candidato future A/B, no como S2 autorizado; cualquier réplica
requiere un protocolo y autorización nuevos. Los prerrequisitos read-only (A-02…A-05) quedan documentados; no se integran ni ejecutan
en esta fase.

---

## 13. Firma de GPU no idle durante S2 — clasificación documental

**Hechos registrados (evidencia):**
- `results/logs/session2-v23.log`: cooldown p2→p3 con T=49 °C (≤50 OK) pero **sclk nivel 7 (1071 MHz) y
  P=6.395 W** → condición `nv0 ∧ P<4 W` nunca anidada → timeout 3600 s → PARADA D (rc=9).
- `results/v23/session2/fase1/cooldown1.tsv`: el cooldown p1→p2 SÍ convergió en 345 s (retorno 49.0 °C, nivel 0,
  3.367 W).
- Logger independiente read-only (`/tmp/opencode/micro12/vkmark30-telemetry.csv`, activo desde 18/09; **PERDIDO / NO VERIFICABLE, no reconstruido**; líneas
  ~25732+): patrón sostenido `gpu_busy=100 % · SCLK 1071 · mclk 300 · mem_busy 0 · ~11.5 W` (y ≈6.4 W registrado
  en el contexto), desde las ~03:45 hasta el final.
- Clientes amdgpu de `0000:01:00.0` identificados en monitoreo en vivo: Xwayland (pid 2721, `/dev/dri/card1`) y
  gpu-process de ChatGPT (pid 3722793, `/dev/dri/renderD129`). **Advertencia de trazabilidad:** estos PIDs provienen
  del contexto de ejecución/monitoreo; no se pudieron re-verificar en artefactos archivados (ningún archivo del repo
  o /tmp/opencode los contiene). El **patrón mecánico** (SCLK 1071 + P≥4 W sostenidos en cooldown) SÍ está 100 %
  documentado en los logs guardados.

**Clasificación:**
| Estado | ¿Se puede afirmar? | Justificación |
|---|---|---|
| **Observado** | SÍ | Se observó una firma de GPU no idle (busy 100 %, SCLK 1071, P≈6.4–11.5 W, mem_busy 0) durante el cooldown p2→p3 y posteriores; el protocolo read-only cumplió su anti-deadlock. |
| **Correlacionado** | SÍ | Hay coincidencia temporal (~03:45 en adelante) entre la carga persistente y el fallo del cooldown; también pre_flight de S2 ya mostraba GPU no-idle (P=3.281 W, T=65 °C). |
| **Causalidad demostrada** | NO | No hay evidencia que demuestre cuál de los clientes (Xwayland, ChatGPT gpu-process, u otro) generó la carga. “gpu_busy=100 % con mem_busy=0 y ~6.4 W” es compatible con presentación/2D, pero no identifica al actor. |
| **Causalidad desconocida** | SÍ (parcial) | Por qué el estado se mantuvo horas (redraw loop de Xwayland vs canvas de ChatGPT vs otro) es UNKNOWN; tampoco se verificó si Xwayland sostiene card1 por ser el nodo de presentación aun sin conector activo. |

**Protocolo de control futuro (NO ejecutado aquí; solo diseño):**
1. Firma de idle obligatoria antes de cada fase: busy 0 %, SCLK nv0, T≤50 °C, P<4 W, **0 fds** de procesos no
   esenciales en `renderD129`/`card1` (lsof/fuser).
2. Inventario de exclusividad en preflight (A-04): registrar todos los clientes del render node y exigir
   “solo el workload”.
3. Diagnóstico de cooldown acotado: si en ≤120 s no converge con T≤50 °C, muestrear P/SCLK por cliente e
   informar, en lugar de un timeout ciego de 3600 s.
4. Para repositorios sensibles (S2-v2.3): sesión sin clientes de la dGPU (parar Xwayland sobre card1 / usar
   sesión de prueba) y validar con el propio protocolo GPU Ownership de FASE O.
5. No asumir causalidad por nombre de cliente: la atribución requiere un experimento de aislamiento (por
   ejemplo, kill de un cliente y verificación de la firma de idle).

---

## 14. Resultado final (secciones exigidas 1–5)

### 1) IMPLEMENTABLE AHORA (10)
- **A-01 SEL-01** — selección VK determinística (ICD/nombre). Evidencia: `1002:699f`→0x412 roto; ICD→0x699F 3/3.
- **A-02 TOR-OBS** — telemetría read-only del governor. Evidencia: harness v2.3 read-only 8/8; `marcar_ventanas.py` validado.
- **A-03 THERM-OBS** — presupuesto térmico como aviso + T_max/SCLK_min por ventana. Evidencia: rampa 0.31/0.246–0.252 °C/s (N=2); t90 ~136–172 s.
- **A-04 ENV-01** — precondición de exclusividad y diagnóstico de cooldown. Evidencia: PARADA D rc=9 (sclk=7, P=6.395 W).
- **A-05 TOR-CD** — cooldown alineado a DN-07. Evidencia: 8/8 cooldowns 150–341 s; S2 cooldown1 345 s.
- **A-06 MES-AB** — regla de control del sample-loc-bug/MSAA en A/B. Evidencia: R0-3 [VERIFICADO].
- **A-07 GPU-ID** — verificación dual + RESTORABLE_FIELDS como baseline. Evidencia: 65/55/56/112 checks; rollback 10/10.
- **A-08 R0-POL** — reconciliación de catálogo GPUPerfAPI v3.17 / v3.11.1 histórico;
  no hay rango semánticamente seguro ni autorización de programación. Evidencia: R0-1/R1-1.
- **A-09 R4A-CON** — constraint PCIe Gen2×4. Evidencia: root port 5.0 GT/s (VERIFIED).
- **A-10 DOC-REC** — reconciliar documentación heredada (requiere decisión del usuario).

*Matiz obligatorio:* ninguno de los A es una palanca de rendimiento bruto; son correcciones de configuración
(SEL-01) e instrumentos/reglas (A-02…A-10). No existe hoy ningún knob de rendimiento con evidencia suficiente
para clasificarse A.

### 2) REQUIERE A/B (7)
B-01 GOV-01 (detención en 0.87/escalón 0.93) · B-02 GOV-02 (ventana/EMA) · B-03 GOV-03 (grilla intermedia) ·
B-04 T-01 (DIST por presupuesto térmico) · B-05 R4A-02 (alojamiento GTT/VRAM) · B-06 R4A-04 (buffer VIS 256 MiB) ·
B-07 MCLK-AB (encarrilamiento MCLK 1500).

### 3) REQUIERE MÁS INVESTIGACIÓN (17)
C-01 contadores (12 slots) · C-02 bandwidth real · C-03 compresión delta · C-04 módulo GDDR5 · C-05 workload
≥20 W · C-06 DCC · C-07 GEO-01 · C-08 GEO-02 · C-09 FRAG-01 · C-10 SHD-01 · C-11 power profiles · C-12 MEM-01/03 ·
C-13 DIST ≤35 °C · C-14 async/BERRETA · C-15 frame recorder · C-16 preset Superposition · C-17 Overdrive.

### 4) DESCARTADO (9)
D-01 CAP-01 · D-02 MES-01 · D-03 SOAK-01 · D-04 KALM-01 · D-05 WL-SCALE-01 · D-06 WL-FRAG-01 ·
D-07 WL-COMPUTE-01 · D-08 GM-01 · D-09 DIST-200 (entrada ≤50 °C).

### 5) INCONCLUSO (3)
E-01 GOV-TORNEO (governor permanente) · E-02 REG17 (régimen 17/09 + phong 1285) · E-03 R2R4R6 (literales R2/R4/R6, R5, F1–F6).

---

## 15. UNKNOWNs más importantes (de toda la evidencia)

1. **Bandwidth REAL medido (PCIe/GTT/VIS/VRAM/DMA)** — sin interfaz de lectura sin ejecutar pruebas; UNKNOWN
   estructural de R-4A (bloquea B-05/B-06 en rigor).
2. **Semántica/unidad de los eventos MC** (UNRESOLVED) + **instancias por fuses** (GAP-08) — impiden diseñar
   normalización de banda y seleccionar contadores con seguridad (C-01).
3. **Causa raíz del régimen 17/09** (25 W / SCLK 350–390 / MCLK 1250–1500 / 74–92 °C) — [NO REPRODUCIBLE];
   incluye el “phong 1285 fps” (O3) con linaje no fiable.
4. **`mem_busy` como proxy de actividad DRAM** (GAP-04, ALTA) — su semántica real se desconoce; pequeñas
   variaciones (24.6 vs 36 %) no explican la potencia (Superposition vs sintéticos).
5. **Comportamiento SMU real de la unidad** (VBIOS/pptable/térmica) para MCLK/SCLK y perfiles — la política
   del driver está VERIFICADA (R0-2), el resultado eléctrico de la placa no.
6. **Efecto real del sample-loc-bug y de los workarounds radeonsi** en el código local (GAP-11; Mesa 26.2.2 no
   leído).
7. **Atribución del cliente de la dGPU durante S2** (Xwayland vs ChatGPT) — correlación, no causalidad (ver §13).

## 16. Condición de parada — reporte final (A–G)

**A. Candidatos auditados:** **45** (sin contar los ítems de regla puramente documental que se desdoblaron;
ver tabla maestra §6 ≥45 filas con A-01..C-17, D-01..D-09, E-01..E-03).

**B. Distribución:** A=10 · B=7 · C=17 · D=9 · E=3. (Total 46 filas; E-03 comparte enunciado con GOV, se cuenta
una vez en 45 y se reporta la fila E-03 como criterio de veredicto.)

**C. Candidatos A — IMPLEMENTABLE AHORA:** A-01 (SEL-01), A-02 (TOR-OBS), A-03 (THERM-OBS), A-04 (ENV-01),
A-05 (TOR-CD), A-06 (MES-AB), A-07 (GPU-ID), A-08 (R0-POL), A-09 (R4A-CON), A-10 (DOC-REC — con decisión del
usuario).

**D. Candidatos B — REQUIERE A/B:** B-01 (GOV-01), B-02 (GOV-02), B-03 (GOV-03), B-04 (T-01), B-05 (R4A-02),
B-06 (R4A-04), B-07 (MCLK-AB).

**E. UNKNOWNs 3–5 más importantes:** (1) bandwidth real medido; (2) semántica MC + instancias por fuses;
(3) causa raíz régimen 17/09 (incl. phong 1285); (4) `mem_busy` como proxy real de DRAM; (5) comportamiento SMU
real de la unidad (VBIOS/pptable) y atribución del cliente dGPU en S2 (empate de prioridad; se listan 5, con la
nota de que (5) tiene dos componentes).

**F. Candidato future de implementación reversible (NO EJECUTAR AHORA):** **GOV-A/B: “detención del governor
en el primer escalón dentro de banda + ventana de decisión + escalón intermedio” (B-01+B-02+B-03)**. No se
reintenta S2-v2.3; cualquier réplica debe ser un protocolo nuevo con autorización nueva. La integración
read-only de A-02/A-03/A-04/A-05 puede precederla. Las piezas R1 3/3, Δ rel −18.5 % y curva
congelada son evidencia diagnóstica direccional de n=3, no un veredicto de implementación.

**G. Evidencia concreta que lo justifica:**
1. `FASE-R4B-GOVERNOR/results/v23/session1/fase2/metrics.json` + `EXP-F4-A-RESULTADOS-v2.3.md` §A: gov settle
   p99 ≈ 9.33 ms, r=1.0194–1.0197 (3/3 en banda [8.251, 10.085] ms), 0 reversiones y convergencia
   en ventana 5; son observaciones diagnósticas de S1, no gates formales. Comparación pareada
   gov 9.33 vs fixed 11.45 ms → Δ ≈ −18.5 % (3 pares).
2. Curva de Fase 1 congelada (v2.3 manifest): 11.441 / 9.337 / 7.037 / 4.897 / 2.848 ms (monótona, gates PASS y
   histéresis ≤0.41 %).
3. Presupuesto térmico: no hay un `t90` universal; las réplicas alineadas a `m0` muestran
   171.9/134.8 s y el DIST de 200 s no se demostró íntegro desde ≤50 °C. El cooldown DN-07
   fue observado 8/8 en S1; no equivale a exclusive environment proof.
4. El mismo candidato NO es clasificable A porque el veredicto global es INCONCLUSO y S2
   quedó PARADA_D; queda B solo para un A/B future, no como configuración permanente.

---

*Fin de la auditoría. No se implementó nada: no se modificó la GPU, no se modificó el sistema, no se ejecutó el
roadmap. Documentos auxiliares canónicos: `04-IMPLEMENTACION/IMPLEMENTATION-ROADMAP.md` y `04-IMPLEMENTACION/IMPLEMENTATION-SAFETY-RULES.md` (no se duplican en esta carpeta).*
