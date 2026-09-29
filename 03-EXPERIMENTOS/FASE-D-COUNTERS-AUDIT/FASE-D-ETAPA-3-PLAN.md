# FASE-D-ETAPA-3-PLAN.md — PLAN (NO EJECUTAR): Contadores programados (clase B) + decisión SPM

**Fecha:** 2026-09-21 (diseño, sin ejecución)
**Documento:** PLAN SOLO LECTURA — no se programó contador, no se escribió ningún registro, no se ejecutó ninguna corrida con este plan.
**Estado de FASE D:** Etapa 1 (auditoría) COMPLETADA · Etapa 2 (contraste A/B×3) COMPLETADA + AUDITADA (v1.4) · **Etapa 3 DISEÑADA — ejecución NO autorizada.**

> REGLA CRÍTICA: Este documento es **planificación**. Describe lo que *se haría* bajo una autorización separada y explícita del operador. La autorización de ejecución NO se deriva de este archivo. Hasta entonces: **no se ejecuta nada** (sin corridas, sin `umr -w`, sin SELECT/CNTL, sin SPM, sin cambios de GPU/sysfs/PowerPlay/Mesa/Kalm/rx550-torneo).

---

## 0. Contexto y corrección a la Etapa 1

### 0.1 Por qué existe Etapa 3

Etapa 2 (auditada) demostró, con 6 corridas intercaladas A B A B A B. La configuración
efectiva de Superposition A fue `1600×900/Medium`; High/1920 fue una petición/args no
coincidente. La tabla es snapshot histórico y no autoriza repetir la corrida.

| Métrica (ventana steady) | A (Superposition `1600×900/Medium`, OpenGL) | B (E-03, Vulkan) |
|---|---|---|
| `W_SMU` steady [W] | **22.256** (22.123/22.301/22.344) | **15.778** (15.822/15.793/15.720) |
| `W_SMU` máximo [W] | 23.62 (23.46/23.68/23.73) | 15.84 (15.91/15.80/15.80) |
| Ratio A/B (por par) | — | **1.398 / 1.412 / 1.421** |
| gpu_busy / mem_busy | ≈100 / ≈25 | ≈100 / ≈36 |
| sclk / mclk (nivel) | 7 (1071) / 2 (1500) en 100 % | 7 / 2 en 100 % |
| RLC_GPU_CLOCK_COUNT rate | ≈24–26 MHz | ≈24–26 MHz |

Señales direccionales (robustas a ambos métodos, 3/3 pares): `vgt/pa/sh` activos en A y 0.0 en B (∞); `sx` A>B (1.51–1.60); `ta/cb/spi/sc/db` ≥ en B (B satura fill). `SPI_CSQ_WF_ACTIVE_COUNT` = 0 en 8408 lecturas (no probatorio read-only; requiere selección GRBM). Hipótesis: H1 **APOYADA** (direccional), H4 **APOYADA** (direccional, sh/sx; WF **NO RESUELTA**), H2/H3/H6 **DEBILITADAS**, H5 **NO RESUELTA**, H7 **NO DISCRIMINADA**, H8 (gating steady) **APOYADA**; gating fino **NO RESUELTO**.

**Lo que Etapa 2 NO pudo hacer (y estos contadores responderían):** contar *eventos reales* por subsistema (primitivas, wavefronts, transacciones L1/L2, ancho de banda DRAM, píxeles escritos) separando la actividad real de la ocupación agregada (`% busy` satura en B sin decir cuánto trabajo es). Los `% busy` miden **ciclo de trabajo** de bits de `GRBM_STATUS`, no trabajo contado.

### 0.2 ERRATUM a la Etapa 1 (FASE-D-COUNTERS-AUDIT.md §5.2/§7/§9)

La Etapa 1 declaró *«TCP/TCC/TA NO tienen registros directos → SPM únicamente»*. **Corrección (fuente: Mesa `src/amd/common/ac_perfcounter.c` / `si_perfcounter.c`, clase VI/GFX8):**

- **SÍ existen registros directos SELECT + LO/HI (MMIO) para TA, TD, TCP, TCC y TCA** en GFX8/Polaris (ver §4.4). La afirmación *«solo vía SPM»* era incorrecta para la *existencia* de los registros.
- Lo que la clasificación `AC_PC_BLOCK_SHADER_WINDOWED` de Mesa sí implica: **TA, TD y TCP** solo cuentan dentro de una **ventana de shader** (requieren `SQ_PERFCOUNTER_CTRL` + eventos `PERFCOUNTER_START/STOP` emitidos vía CP, ruta compleja desde userspace).
- **TCC y TCA NO son shader-windowed** (solo «instance-group»): cuentan **sin** ventana de shader → lectores directos para L2 (H5) **sin** SPM.
- De aquí la decisión de §6: **SPM no es necesario** para las preguntas prioritarias de Etapa 3.

### 0.3 Reglas que gobiernan este plan

1. Estados de hipótesis restringidos: `APOYADA / DEBILITADA / NO RESUELTA / NO DISCRIMINADA`. **Nunca** `VERIFICADA` (sin causalidad asumida).
2. Potencia siempre con las 4 métricas de `METRICS-DEFINITIONS.md`; etiquetar `NOT DIRECTLY COMPARABLE` si se cruzan ventanas.
3. Ningún ID numérico de evento/selector se acepta sin **verificación previa read-only** (Mesa clase VI + catálogo `umr -lr gfx800/gmc810`). TODO lo no verificado se marca `[VERIFICAR]` aquí y es *condición de aborto* si falla (§10).
4. Toda escritura de contador debe ir acompañada de **snapshot previo + restauración verificada byte-a-byte** (§8).
5. Los estados de éxito no declaran causalidad; la Etapa 3 produce evidencia direccional de eventos contados.

---

## 1. Preguntas científicas (por incertidumbre)

Cada pregunta: formulación · hipótesis que distingue · medición necesaria · por qué Etapa 2 no la resolvió.

| # | Pregunta | Distingue | Medición necesaria | Por qué Etapa 2 no la resolvió |
|---|---|---|---|---|
| Q1 | ¿El +6.5 W de A proviene de más *geometría/primitivas* o de más *ciclos de shader*? | H1 vs H4 | Conteo de primitivas (VGT/GRBMSE) y de ciclos/eventos de shader (SX, GRBMSE per-SE) por frame; separar en la MISMA corrida | `vgt/pa/sh` son bits busy (ciclo de trabajo); B los tiene a 0 pero el *conteo* no se midió; no hay separación prím-vs-shader contada |
| Q2 | ¿Cuántos wavefronts reales hay en vuelo en A vs B? | H4-WF | Conteo de wavefronts/ocupación SQ/SPI por frame | `SPI_CSQ_WF_ACTIVE_COUNT` = 0 en 8408 lecturas read-only (requiere programar SELECT GRBM MEID/PIPEID/QUEUEID/VMID) |
| Q3 | ¿Cuántos texels/instrucciones de textura (L1/TCP) por frame en A vs B, y cuál es su coste? | H3 | Conteo de transacciones/fetches TCP primario; proxi directo TCC total | `ta` busy A 75–81 vs B 99–100 (B satura *duty* pero desconocemos *eventos*); no hay contador contado |
| Q4 | ¿La brecha es *trabajo de caché L2* (TCC) o *tráfico DRAM* (MC_ARB)? | H5 vs H6 | Contadores TCC (transacciones/hit-miss) + MC_ARB (eventos DRAM/bandwidth) | H5 no instrumentada (prohibido); `mem_busy` es % de período, NO bandwidth; H6 quedó DEBILITADA solo con proxis |
| Q5 | ¿Cuántos píxeles escriben realmente CB/DB en A vs B (fill real)? | H2 | Contadores CB/DB (writes, eventos por primitivo) | `cb`/`db` busy saturan (≈99 en B) sin decir *volumen* de escrituras |
| Q6 | ¿Existe actividad GFX *dentro* de gpu_busy≈100 % que explique la potencia (trabajo real vs ocio)? | H8 | Conteo de eventos globales GRBM vs máscara de uso; correlación con potencia por corrida | gpu_busy≈100 % en ambos no discrimina; RLC solo prueba reloj constante |
| Q7 | ¿El driver (radeonsi vs RADV) explica el reparto de eventos más allá de la diferencia de workload? | H7 | Reparto evento/frame de Q1–Q6 comparado A/B; análisis cualitativo | Los perfiles de pipeline difieren **por construcción** (workload ≠), no aísla driver |

**Fuera de alcance de Etapa 3 (justificado):** mecánica del régimen histórico 17/09 (FASE B–F), comportamiento real DCC/PowerPlay (FASE G–I), BIOS/fuses (FASE J). No se registra como pregunta una de estas.

---

## 2. Inventario priorizado de contadores (A = necesarios / B = útiles secundarios / C = no justifican riesgo)

Vía de acceso (en GFX8): **dir** = directa (sin ventana de shader) · **win** = requiere ventana de shader (SQ_PERFCOUNTER_CTRL + start/stop vía CP) · **SPM** = requiere ring RLC/SPM. Numeración de slots por bloque según Mesa (`num_counters`) — **verificar** en pre-check.

| Contador (bloque) | Vía | Cubre | Prioridad | Justificación |
|---|---|---|---|---|
| `GRBM_PERFCOUNTER0/1` (gfx800) | dir | Q1/Q6 global | **A** | 2 slots globales (eventos de pipeline frontend/back-end); bajo riesgo; ancla de normalización por ciclo |
| `GRBM_SE*_PERFCOUNTER0/1` (GRBMSE, per SE) | dir | Q1 (segmenta geometría vs shader por SE) | **A** | 4 slots/SE; discrimina prím (VGT) vs ciclos de shader (SPI/SQ por SE) **sin** ventana — [VERIFICAR]
| `SX_PERFCOUNTER0/1` (gfx800) | dir | Q1/Q3 (export de shader) | **A** | SX 4 slots; export es la señal direccional más fuerte (1.51–1.60) |
| `TCC_PERFCOUNTER0..N` (gfx800, por slice) | dir | Q4 (transacciones L2, hit/miss) | **A** | **No shader-windowed** → cierra H5 sin SPM; verificar nº de slices (PD12: 4) |
| `TCA_PERFCOUNTER0..N` (gfx800) | dir | Q4 (arbitraje L2) | **B** | Refinamiento de H5; solo si sobran slots/riesgo |
| `CB_PERFCOUNTER0/1` (gfx800) | dir | Q5 (color writes) | **A** | Cierra fill real; H2 está DEBILITADA → confirmar o refutar |
| `DB_PERFCOUNTER0/1` (gfx800) | dir | Q5 (depth) | **A** | Idem CB |
| `MC_ARB_PERFCOUNTER0/1` (gmc810) | dir | Q4/Q6 (eventos DRAM/bandwidth) | **A** | Cuantifica tráfico real VRAM (H6), superando `mem_busy` |
| `PA_SU/PA_SC`, `VGT` dedicado | dir | Q1 (primitivas) | **B** | Si GRBMSE/GRBM no alcanzan granularidad VGT; verificar SELECT dedicado |
| `CPG/CPC/CPF_PERFCOUNTER*` (gfx800) | dir | Q1/Q6 (command processors) | **B** | Utilidad marginal (frontend); bajo prioridad |
| `MC_CITF`, `ATC`, `CHUB_ATC`, `GMCON` (gmc810) | dir | Q4/Q6 (coherencia/GTT) | **B** | Solo si MC_ARB deja ambigüedad (GTT no es probable diferenciador) |
| `SQ_PERFCOUNTER0–15` (gfx800) | **win** | Q1/Q2 (ALU, wavefronts por CU) | **C** | Alto valor pero requiere ventana de shader → Etapa 3-EXT |
| `SPI_PERFCOUNTER*` + `SPI_GFX_WF_ACTIVE*` (gfx800) | **win** | Q2 (wavefronts reales) | **C** | Idem; requiere SELECT GRBM + ventana |
| `TCP_PERFCOUNTER*` (gfx800) | **win** | Q3 (L1/fetch) | **C** | Windowed → Etapa 3-EXT (ver §4.4); proxi directo: TCC |
| `TA_PERFCOUNTER0/1` (gfx800) | **win** | Q3 (texel addresser) | **C** | Windowed → Etapa 3-EXT |
| `TD_PERFCOUNTER*` (gfx800) | **win** | Q3 (texture data) | **C** | Windowed → Etapa 3-EXT |
| `RLC_SPM_*` / ring SPM | **SPM** | Q3/Q4 finas | **C** | Excluido (§6); alta complejidad/riesgo, beneficio marginal dado TCC directo |
| `SRBM`, `SDMA0/1`, `IH`, `DCE` | dir | — | **C** | No aportan a las preguntas (display en iGPU; SDMA copias) |
| GPUPerfAPI (instalación) | — | H7 | **C** | Requiere instalar y cargar perflib kernel; no necesario para vía UMR directa |

**Configuración MÍNIMA propuesta (12 slots, todos `dir`, una sola corrida ×6):** GRBM ×2 · GRBMSE (SE0) ×2 · SX ×1 · TCC ×2 (2 slices, evento idéntico) · TCA ×1 (opcional) · CB ×1 · DB ×1 · MC_ARB ×2. Se evita multiplicar sets de corridas (ver §7.2).

---

## 3. Atención especial por subsistema (actividad real vs utilización agregada)

Regla transversal: un bit `busy` al 99 % indica *que la unidad se mantuvo ocupada el periodo*, NO *cuánto trabajo hizo*. Un contador evento indica *cuántos eventos*; la normalización por frame/ciclo convierte eso en *trabajo real*. En ambas escrutan; las advertencias indican cómo leer cada par.

| Subsistema | Pregunta | Contador(es) | Advertencia (real vs utilización) |
|---|---|---|---|
| **L1 / L2 / TCC / TCP / TA** | Q3/Q4 (H3/H5) | TCC dir; TCP/TA/TD win (EXT) | B satura el bit `ta` a ~99 %; ¿son eventos por frame comparables a A? TCC solo dir da hit/miss; TCP/L1 queda en EXT. La «diferencia de textura» solo es contada si TCC/EXT la revelan |
| **Wavefront / Workgroup** | Q2 (H4-WF) | SQG/SQ/SPI win; proxi GRBMSE+SX | `SPI_CSQ=0` en 8408 lecturas NO prueba 0 wavefronts (registro de cola no seleccionada). Solo los win (EXT) cierran esto; los directos solo dan proxis |
| **Shader / ALU / export** | Q1/Q3 (H4) | SX dir; GRBMSE per-SE dir; SQ win (EXT) | `sh` busy A≈39 vs B=0 pero `sx` A≈93 vs B≈57: el export no es proxi de ALU. Contadores dir separan export (SX) de emit (GRBMSE SPI) |
| **Geometría / vertex / primitive** | Q1 (H1) | GRBMSE/GRBM prím; VGT/PA_SC dir (B) | `vgt/pa=0` en B = bit busy nunca activo en la ventana; el *conteo* de primitivas dirá si B genera alguna. Si prím A>>B con shader A>B → H1+H4 co-motor |
| **Raster / ROP / fill** | Q5 (H2) | CB, DB dir | fill satura en B (sc/db/cb≈99) GASTANDO MENOS potencia: los contadores CB/DB deciden si B escribe MÁS píxeles (entonces el fill NO es el diferenciador) o MENOS (entonces el duty era engañoso) |
| **VRAM / MC / DRAM** | Q4/Q6 (H6) | MC_ARB dir | `mem_busy` B(36)>A(25) con A más potente: el % NO es bandwidth. MC_ARB contará eventos DRAM reales; si B≥A → H6 definitivamente DEBILITADA |
| **Frontend / CP** | Q6 | CPG/CPC/CPF (B) | No discrimina las preguntas; mide el liderazgo de la lista de comandos |

---

## 4. Semántica por contador (registro, campo/bit, unidad, snapshot/acumulativo, selección, bloque, incremento, normalización, aliasing/overflow, límites Polaris12)

**Fuentes:** Mesa `src/amd/common/ac_perfcounter.c` + `src/gallium/drivers/radeonsi/si_perfcounter.c` (clase VI), catálogo real `umr -lr gfx800` / `umr -lr gmc810` de la máquina (Etapa 1). Offsets base indicados en notación de registros R_0xxxxx (dwords). **Todo evento marcado `[VERIFICAR]` debe confirmarse (read-only, §8-PRE) antes de cualquier escritura; si falla → abortar ese slot (§10.1).**

### 4.1 Convenciones comunes (todas aplican a cada fila)

- **Acumulativo, no snapshot:** LO+HI forman un contador que se incrementa con cada evento; se lee por DIFERENCIA entre dos lecturas (Δ) sobre la ventana steady. Lectura no atómica → margen en el conteo.
- **Unidad:** eventos (no ciclos, salvo los «_CYCLES» indicados). Normalizar como `Δ_eventos / Δ_tiempo` y `/ frame` (frames de la ventana: Superposition desde `-log_txt`; E-03 fijo 8.95 fps, 179 frames/measure).
- **Overflow/aliasing:** LO (32-bit, a veces LO/HI = 48/64-bit). Δ con wraparound módulo del ancho del contador; si solo hay LO (32-bit) a 1071 MHz un contador «por ciclo» desborda en ~4 s → **mayorar el tiempo entre muestras** o usar eventos de menor frecuencia; **verificar ancho** en PRE (base `_HI` presente o no).
- **Selección:** cada bloque expone SELECT (y a veces SELECT1/SELECT2). El valor de SELECT elige el evento; SELECT1/2 eligen condiciones auxiliares (ej. máscaras de instancia/SE). No asignado = 0 → sin conteo (de ahí los ceros de Etapa 2).
- **Limites Polaris12/GFX8:** nº de contadores simultáneos por bloque = nº de registros LO disponibles (GRBM 2, GRBMSE 4, SX 4, TCC según slices, CB 4, DB 4, MC_ARB 4 — **verificar**). Múltiples eventos pueden requerir multipara el SELECT en lecturas sucesivas (no simultáneo). 1 SH (Pol-E-ramos?), 1 SE en Polaris12 (verificar).

### 4.2 Bloques DIRECTOS seleccionados (config MÍNIMA)

| Contador (registro; offset base) | Campo/bit | Unidad / semántica | Snap/Cumul | Selección | Bloque medido | Incremento significa | Normalización | Aliasing/Overflow | Límites P12 |
|---|---|---|---|---|---|---|---|---|---|
| `GRBM_PERFCOUNTER0_LO/HI` (R_034100/104; SELECT R_036100) | LO+HI 32-bit c/u; SELECT campo evento | Evento global del pipeline GFX (ej. primitivas totales / ciclos de front-end) `[VERIFICAR evento]` | Acum. | SELECT→evento global; [VERIFICAR máscara] | GRBM agregado (toda la GPU) | Un evento de pipeline global ocurrió | Δ/Δt; Δ/frame; ratio A/B | 32/48-bit; wraparound | 2 contadores globales |
| `GRBM_PERFCOUNTER1_LO/HI` (R_03410C/110; SELECT R_036104) | idem | Segundo evento global (ideal: backbone de ciclos o fetch) `[VERIFICAR]` | Acum. | SELECT→evento | GRBM | idem | idem | idem | 2 |
| `GRBM_SE0_PERFCOUNTER0/1` (LO R_034114…; SELECT R_036108/10C) | LO/HI; SELECT evento por SE | Evento **por SE**: miembro GRBMSE con events VGT/SPI/SC/PC `[VERIFICAR lista]` | Acum. | SELECT→evento SE0; acceder vía `--bank <SE> <SH>` | Shader Engine 0 | Un evento del subsistema elegido en SE0 | Δ/Δt por SE; Δ/frame | wraparound | 4 por SE; 1 SE típico en P12 (verificar) |
| `SX_PERFCOUNTER0_LO/HI` (R_034900/904; SELECT R_036900 `[VERIFICAR]`) | LO/HI; SELECT evento | Eventos de **shader export** (instrucciones export/valores por anillo) `[VERIFICAR]` | Acum. | SELECT→evento export | SX (export/backpipe) | Se exportó 1 dato/instrucción de shader | Δ/frame; Δ/Δt | 32-bit si solo LO | 4 contadores |
| `TCC_PERFCOUNTER0_LO/HI` por slice (LO R_034E00+…; SELECT R_036E00) | LO/HI; SELECT evento L2 | Transacciones L2 (lectura/escritura/hit-miss) `[VERIFICAR eventos: ej. L2 read xfer, write xfer, miss, hit]` | Acum. | SELECT→evento L2; por slice (instancia) | L2 (TCC, por slice) | Una transacción L2 del tipo elegido | Δ/frame; ratio; suma de slices | wraparound; nº slices [VERIFICAR: 4] | 4 slices × regs |
| `TCA_PERFCOUNTER0…` (gfx800) | LO/HI; SELECT | Arbitraje de L2 (sectores/colas) `[VERIFICAR]` | Acum. | SELECT→evento TCA | TCA (controladora L2) | Un evento de arbitraje L2 | Δ/frame | wraparound | verificar |
| `CB_PERFCOUNTER0_LO/HI` (gfx800) | LO/HI; SELECT | Eventos de **color buffer** (píxeles escritos, regiones, cache miss CB) `[VERIFICAR]` | Acum. | SELECT→evento CB | CB (color ROP) | Un píxel/operación de color completado | Δ/frame; Δ/píxel (1920×1080×layers) | wraparound; margen con MSAA (B msaa=1 en diseño B) | 4 contadores |
| `DB_PERFCOUNTER0_LO/HI` (gfx800) | LO/HI; SELECT | Eventos **depth** (z-read/z-write/passthrough, miss depth cache) `[VERIFICAR]` | Acum. | SELECT→evento DB | DB (depth ROP) | Una operación z/fragmento procesada | Δ/frame | wraparound | 4 contadores |
| `MC_ARB_PERFCOUNTER0/1` (gmc810) | LO/HI; SELECT/CNTL | Eventos del **arbiter de memoria** (ej. nº de bursts, activaciones activas) `[VERIFICAR eventos: ej. burst rd/wr]` | Acum. | SELECT→evento MC + SELECT1 máscara | MC (arbiter/DRAM) | Un acceso DRAM del tipo elegido | Δ/frame; estimador de bandwidth (events×granularity [VERIFICAR]) | wraparound | 4 contadores |

> Regla de lectura en diseño: **cada contador se lee en pares** (t1, t2) cada ~0.5 s dentro de la ventana steady, timestamped (epoch-ns) para alinear con telemetría/radeontop. El Δ se acota a la intersección de la ventana con el intervalo de muestreo.

### 4.3 Bloques windowed — catalogados pero EXCLUIDOS de la Etapa 3 mínima

| Contador (offset base) | Vía | Por qué se excluye | Qué respondería |
|---|---|---|---|
| `SQ_PERFCOUNTER0–15` (gfx800) | win | Requiere `SQ_PERFCOUNTER_CTRL` + eventos START/STOP vía CP/IB; usuariospace UMR no lo emite de forma segura | ciclos ALU por CU, wavefronts por primitivo |
| `SPI_PERFCOUNTER*`, `SPI_GFX_WF_ACTIVE_*` | win | idem (y SELECT GRBM MEID/PIPE/QUEUE para WF reales) | wavefronts reales (Q2) |
| `TCP_PERFCOUNTER*` (LO R_034D00; SELECT R_036D00) | win | Shader-windowed (`AC_PC_BLOCK_SHADER_WINDOWED`) | fetch/texels L1 (Q3) |
| `TA_PERFCOUNTER0/1` (LO R_034B00; SELECT R_036B00/R_036B08; SELECT1 R_036B04) | win | idem | texel address (Q3) |
| `TD_PERFCOUNTER*` (LO R_034C00; SELECT R_036C00) | win | idem | texture data (Q3) |

La vía documentada para usarlos (EXT, sin autorización) requeriría: configurar `SQ_PERFCOUNTER_CTRL`, iniciar/detener la ventana con `PKT3`/IB con `WRITE_DATA` (como hace radeonsi/RADV), entregado por un mecanismo de range/driver — fuera del alcance plano aquí.

### 4.4 Nota de registro (ERRA etapa 1 — ver §0.2)

Taquigrafía de offsets directos verificados en el análisis de Mesa (clase VI): `TA` LO R_034B00 / SELECT R_036B00(+R_036B04 SELECT1, R_036B08 SELECT contador1) · `TD` LO R_034C00 / SELECT R_036C00 · `TCP` LO R_034D00 / SELECT R_036D00 · `TCC` LO R_034E00 / SELECT R_036E00 · `SX` LO R_034900 / SELECT R_036900 · `GRBM` LO R_034100/R_03410C / SELECT R_036100/R_036104 · `GRBMSE` LO R_034114… / SELECT R_036108…114. **Antes de escribir, confirmar nombres/offsets exactos en `umr -lr gfx800`/`gmc810` (PRE, read-only).**

---

## 5. Mecanismo de programación (conceptual, para la configuración MÍNIMA)

> Escrituras de registros MMIO → **autorización explícita separada**. Nunca se ejecutan desde este plan. La secuencia conceptual es:

1. **Pre-verificación read-only (obligatoria, ver §8-PRE):** para cada slot, resolver `[VERIFICAR]`: nombre UMR canónico (`gfx800.mm<REG>`) y offset con `umr -lr gfx800|gmc810`; ID numérico del evento y máscara desde `ac_perfcounter.c` (enum de eventos VI) + `si_perfcounter.c` (secuencia enable/read/disable del driver). Si algún slot no se confirma → se elimina (no sustituir por inventiva).
2. **Snapshot (PRE):** `umr -r` de TODOS los registros a tocar (cada LO/HI/SELECT/SELECT1/CNTL + `SQ_PERFCOUNTER_CTRL`, `GRBM_GFX_INDEX` si aplica, y los SELECT existentes) → `pre_state_<run>.txt` (hex, inmutcript, con hash).
3. **Programar (por corrida, ANTES de la ventana steady):**
   - Escribir SELECT por cada slot: `umr -i {idx} -w "gfx800.mmGRBM_PERFCOUNTER0_SELECT" {evento}` etc. Para instancias por SE/slice usar `umr --bank <se> <sh>` (equivale a `amdgpu_gfx_select_se_sh`), o escribir los SELECT por-slice de TCC.
   - Poner LO/HI a 0 (reseteo) si el HW lo permite (verificar «clear on write»); alternativamente registrar el primer valor y restar (Δ).
   - **No** se emite `SQ_PERFCOUNTER_CTRL` (bloques win excluidos).
4. **Lectura en vivo (DURANTE):** bucle `umr -r` de LO/HI por slot a ~2 Hz con timestamp epoch-ns; Δ por par de lecturas dentro de la ventana steady; alineación offline con telemetría/radeontop (mismos criterios de §7).
5. **Restauración (POST):** re-escribir cada registro con el valor del snapshot (SELECT=valor pre, LO/HI=valor pre); verificar **byte a byte** (`pre_state` vs `post_state`); relectura tras 60 s idle → todos en estado idle (0x0 o valor pre) y `GRBM_PERFCOUNTER*_LO=0` sin carga.
6. **Auditoría de escritura:** tabla por-corrida de cada registro tocado (registro, valor_pre, valor_programado, valor_leído_max, valor_restaurado, match pre/post) como artefacto.

**Riesgos del mecanismo (diseñados en §11/matriz):** escritura directa MMIO fuera de la sincronización del driver (el driver podría reprogramar SELECT durante la corrida → desvincular el contexto del kernel solo para la ventana; LPM/DPM transición puede tocar contadores); lectura no atómica LO/HI (margen documentado); si el contador requiere enable-global no contemplado (p.ej. bit de habilitación en un registro de control GRBM) → se detecta en sanity idle (no avanza bajo carga → slot abortado, §10.2).

---

## 6. Decisión SPM

**Decisión: EXCLUIR SPM de la Etapa 3 mínima.** No se configura el ring RLC/SPM ni `RLC_SPM_*`.

Justificación:
1. **H5 (caché L2) se cubre con TCC directo** (no shader-windowed, §0.2 y §4.2) → el beneficio neto de SPM para las preguntas A es marginal.
2. El ring SPM en Polaris12 implica configurar el ring del RLC + ruta de *sample* con el microcódigo; el kernel moderno expone SPM vía `amdgpu_spm_funcs`/KIQ (interfaz rec resource), orientada a IP más moderna, con riesgo de *hang* y restauración compleja — desproporcionado para esta fase.
3. Las preguntas prioritarias (Q1, Q4, Q5, Q6) son respondibles con contadores directos; Q2/Q3 (windowed WS/SQ/SPI/TCP/TA) requieren mecanismo de **ventana de shader**, no SPM.
4. **Cambio de estado** solo si los resultados de TCC directo muestran ambigüedad irresoluble L2-vs-L1 → se solicita **ETAPA 3-EXT (SPM)** con autorización específica, diseño de ring y validación de restauración, como fase separada.

---

## 7. Diseño experimental (MÍNIMO)

### 7.1 Reglas idénticas a Etapa 2 (no negociables)

- **6 corridas intercaladas A B A B A B** (3 réplicas c/u), pausas idle 30 s (misma workload) / 60 s (cambio de workload).
- **Ventana steady:** definición exacta de `METRICS-DEFINITIONS.md` §1.4 (gpu_busy≥95, sclk≥1071, mclk≥1500, descartar ~5 s iniciales, ≥100 muestras).
- **Métricas de potencia:** las 4 métricas por corrida (`power_avg_full/steady`, `power_max_full/steady`, `steady_window_samples/duration_s`) — idéntico pipeline de Etapa 2 (`telemetria.sh` 10 Hz).
- **Instrumentación paralela:** radeontop 1 Hz (dump) + telemetría 10 Hz + UMR contadores 2 Hz, todo timestamped (epoch-ns); frames desde logs (Superposition `-log_txt`; E-03 measure 179 frames @ 8.95 fps).
- **Sin cambios:** workload (Inmutado), Mesa, kernel, sysfs, PowerPlay, Kalm, rx550-torneo. Pre/post_flight idénticos (DPM auto, piso 214/300, power1_cap 35W).

### 7.2 Multiplexación y límite de slots

- Config MÍNIMA = 12 slots directos (GRBM×2, GRBMSE×2, SX×1, TCC×2, TCA×1, CB×1, DB×1, MC_ARB×2) en UN set de 6 corridas. La configuración se mantiene fija durante las 6 corridas (mismos SELECT en las mismas réplicas) para permitir comparación directa A vs B y réplica a réplica.
- Si tras el análisis se quieren MÁS eventos de los slots disponibles → **multiplex en sets adicionales**: cada set = +6 corridas con exactamente la misma estructura; NO se cambia la configuración a mitad de corrida. La recomendación inicial es **NO** necesitar set adicional (los eventos elegidos cubren Q1/Q4/Q5/Q6; Q2/Q3 quedan a EXT).
- Análisis: por slot, `Δ_{ventana}` por réplica; media/min–máx por A y B; `ratio_A/B` con rangos; correlación por-frame con potencia de la misma ventana. Nunca comparar valores brutos entre workloads de distinta duración (solo Δ normalizados o ratios por frame).

### 7.3 Determinismo esperado (reproducibilidad de Etapa 2, para detectar anomalías)

- A: score 804, `power_avg_steady` 22.123–22.344 W; B: fps 8.950, 15.720–15.822 W. Si una réplica se desvía de estos rangos → réplica inválida (repetir, sin abortar el experimento). Si TODAS se desvían → actividad de contadores alteró el estado → perlección/Abort (§10).

---

## 8. Protocolo de seguridad PRE / DURANTE / POST

### 8.1 PRE (antes de cualquier escritura)

1. **Checklist read-only completo:** verbos `umr -lr gfx800`, `umr -lr gmc810`, tablas Mesa VI (eventos SELECT/SELECT1/CNTL), `si_perfcounter.c` secuencia enable/read/disable → resolver TODOS los `[VERIFICAR]`. **Gate: si no se resuelve → abortar ese slot (§10.1).**
2. **Sanity idle (requiere la autorización de escritura):** en GPU idle, programar la config completa, leer 2× con 5 s de separación (Δ≈0 esperado) y **restaurar de inmediato**; si Δ≠0 sin carga → investigar/en-mendenda; si no se aclara → abortar.
3. **Snapshot:** todos los registros a tocar → `pre_state_<run>.txt` + hash SHA-256; además `GRBM_PERFCOUNTER*_LO=0` para probar no-programación previa.
4. **Estado del sistema:** power1_cap 35W, `performance_level=auto`, kalm PIDs vivos, sin otros clientes de `renderD129`, 0 faults en ventana previa.
5. **Documento de config aprobada:** tabla `slot → registro → SELECT(evento) → máscara → comportamiento ventana` aprobada; fuera de esto, no se toca nada.

### 8.2 DURANTE

1. Secuencia por corrida: pre_flight → samplers → workload → ventana (≈260 s A; ≈40 s B) → post_flight, réplica a réplica (A1 B1 A2 B2 A3 B3).
2. **Solo** los slots aprobados se escriben; **no** se reescribe registro durante la corrida.
3. Ventana steady y Δ de contadores alineados por epoch-ns; se exige la ventana completa ≥100 muestras (si una réplica falla → inválida, repetir como §7.3).
4. **Watchdog en vivo:** `journalctl` streaming por GPU fault/VM fault/ring; si un fault/hang requiere reboot → ir a ABORT (no reintentar sin autorización nueva).

### 8.3 POST

1. **Restauración de TODOS** los registros desde snapshot (SELECT, SELECT1, CNTL, LO/HI), en orden inverso al programado.
2. **Verificación de paridad:** `post_state_<run>.txt` vs `pre_state_<run>.txt` byte a byte (diff) + relectura tras 60 s idle → `GRBM_PERFCOUNTER*_LO=0` (o valor pre) y sin conteo residual.
3. **Verificaciones de sistema:** DPM auto, sclk piso 214, mclk piso 300, power1_cap 35000000, temp idle ≈ pre, 0 faults.
4. Solo si todo coincide → corrida válida; si no → NO válida, registrar y restaurar hasta concluir.

---

## 9. Criterios de éxito por hipótesis

Los estados siguen las reglas §0.3. Señal estándar: `ratio_{A/B}` por evento **por frame** con rangos de réplicas no solapados, o patrón sistemático claro. Nada se declara causal; evidencia direccional de **eventos contados**.

### 9.1 H1 (geom/vertex) y geometría-vs-shader
- Primitivas/eventos VGT (GRBMSE/GRBM) por frame: **A / B ≥ 1.5** y rangos no solapados → H1 **APOYADA** (contada).
- Si además SX/export por frame A/B ≥ 1.5 → geometría **y** shader-export suben juntas → el +41 % es *trabajo de ambos tramos*, no solo uno.
- Si primitivas A/B ≈ 1 pero shader-export A/B ≥ 1.5 → el motor es **shader/export** (H4), H1 re-dirigida.

### 9.2 H4 / H4-WF (wavefronts)
- Los contadores win (SQ/SPI, EXT) son los únicos que cierran WF reales → en Etapa 3 mínima H4-WF queda documentado con el proxi directo: SX export por frame y GRBMSE SPI/emit por SE. **ÉXITO mínimo = declarar H4-WF NO RESUELTA en mínima y, si los proxis escalan con A, recomendar la ventana EXT.**

### 9.3 H3 (texturas/fetch)
- Vía directa: TCC transacciones L2 por frame y `ta` (radi valori). Escenarios: si TCC y ta por frame **A ≈ B** (B no hace más trabajo de textura) → H3 **DEBILITADA** como motor (coherente con Etapa 2); si A > B ≥ 1.5 con TCC → H3 **APOYADA**.
- La resolución fina L1 (TCP) y texel address (TA/TD) queda a EXT (windowed); si los resultados directos son ambiguos → H3 **NO RESUELTA** (sin forzar).

### 9.4 H5 (caché L2) y caché-vs-VRAM
- TCC hit/miss y transacciones por frame: comparada contra MC_ARB (DRAM). **caché-vs-VRAM se distingue así:** si el tráfico L2 (TCC) goza y el tráfico DRAM (MC_ARB) es proporcional → la presión real es de caches más DRAM escalada; si TCC alto con MC bajo → A con más trabajo de caché reutilizado (L2 residente); si TCC≈A≈B → H5 **NO APOYADA** como diferenciador.
- ÉXITO = tabla `TCC(xA/B) · MC_ARB(xA/B) · mem_busy` que permite una de las tres lecturas anteriores de forma no ambigüa (rangos no solapados o patrón claro).

### 9.5 H2 (fill) — CB/DB por frame
- Si CB/DB por frame **A ≥ B** sin solape → H2 re-evaluada (pero Etapa 2 apunta a lo contrario); si **B ≥ A** (B escriba más) → H2 **DEBILITADA** (coherente): el duty del fill en B no era trabajo por-frame mayor.

### 9.6 H6 (VRAM/MC) y Q6 (trabajo oculto vs gpu_busy)
- MC_ARB eventos/frame: si **B ≥ A** → H6 **DEBILITADA definitivamente** (el más ocupado de RAM gasta menos). GRBM global events vs gpu_busy≈100 %: si los eventos globales A >> B dentro de un gpu_busy≈100 → describe *trabajo real* (Q6).

### 9.7 Regla de cierre general
Cada hipótesis reporta: contador + config + n réplicas + ratio(media, min–máx) + lectura `APOYADA/DEBILITADA/NO RESUELTA/NO DISCRIMINADA`. Si ninguna señal supera el umbral → documento de **NO DISCRIMINADO** y se recomienda cuánto de Q2/Q3 requiere la ventana EXT.

---

## 10. Criterios de aborto (objetivos)

| # | Criterio | Acción |
|---|---|---|
| 10.1 | Un `[VERIFICAR]` (nombre/offset/evento/máscara) NO confirmable en PRE read-only | Eliminar ese slot (no sustituir por inventiva); si es crítico para Q priori → replanificar |
| 10.2 | Sanity idle: contador avanza sin carga, o no avanza bajo carga conocida | Abortar ese slot/config; investigar antes de seguir |
| 10.3 | Restauración post NO byte-idéntica (diff pre/post) o `GRBM*_LO≠0` tras idle | Abortar la corrida y TODO el set; no reintentar sin autorización nueva |
| 10.4 | GPU fault/VM fault/hang/necesidad de reboot durante la corrida | Abortar, restaurar desde snapshot, detener samplers; NO reintentar sin autorización |
| 10.5 | Se descubre que un evento requiere ventana de shader (SQ_PERFCOUNTER_CTRL/IB) no planificada | Reclasificar el slot a EXT; NO improvisar la ventana en vivo |
| 10.6 | Ventana steady no alcanza ≥100 muestras o mclk/sclk fuera de 7/2 en una réplica | Réplica inválida → repetir (regla §7.3); si ocurre en varias → evaluación de estado |
| 10.7 | La escritura del kernel re-programa SELECT durante la corrida (detectado por delta incoherente entre réplicas) | Registrar; si sistemático → abortar config y usar vía de range/driver (EXT) |
| 10.8 | Resultado NO discrimina (ratios dentro del ruido, rangos solapados) | Mantener `NO RESUELTA`/`NO DISCRIMINADA`; NO forzar interpretación; recomendar EXT |
| 10.9 | Cualquier escritura NO aprobada (fuera de la tabla de config) | Detener de inmediato, restaurar, registrar desviación |

Abortar ≠ fallar el experimento: cada aborto produce un artefacto de diagnóstico (qué slot, qué registros, qué heat-up) reutilizable.

---

## 11. Matriz final de decisión y recomendación de alcance

### 11.1 Matriz «Pregunta | Contador | Riesgo | Información esperada | ¿Justifica Etapa 3?»

| Pregunta | Contador (vía) | Riesgo de la medición | Información esperada | ¿Justifica Etapa 3? |
|---|---|---|---|---|
| Q1 geometría vs shader | GRBM/GRBMSE prím + SX (dir) | Bajo-medio (SELECT directo) | Ratio prím y export A/B por frame, separando tramos | **SÍ** |
| Q2 wavefronts reales | SQ/SPI (win) | Alto (ventana shader no implementada) | WF por CU/frame | **NO en mínima** → EXT |
| Q3 texels/fetch L1 | TCP/TA/TD (win) + proxi TCC | Alto (win) / bajo (TCC) | transacciones L2 vs fetch L1 | **PARCIAL** (TCC sí; TCP/TA solo EXT) |
| Q4 caché L2 vs DRAM | TCC + MC_ARB (dir) | Bajo-medio | Tráfico L2 y DRAM por frame → decide H5 vs H6 | **SÍ** |
| Q5 fill/Rops | CB/DB (dir) | Bajo | Píxeles/z-writes por frame A vs B | **SÍ** |
| Q6 tráfico VRAM real | MC_ARB (dir) | Bajo-medio | eventos DRAM/frame; sustituye `mem_busy` | **SÍ** |
| Q7 trabajo real vs gpu_busy | GRBM global (dir) | Bajo | eventos globales/frame en gpu_busy≈100 % | **SÍ** |
| Q8 driver H7 | reparto Q1–Q6 | — | interpretativo; no aísla driver | **NO** |

### 11.2 Recomendación de alcance

- **ETAPA 3 MÍNIMA (recomendada, autorizable):** la Config MÍNIMA de 12 slots **directos** (GRBM×2, GRBMSE×2, SX×1, TCC×2, TCA×1, CB×1, DB×1, MC_ARB×2) sobre 6 corridas intercaladas A/B×3 idénticas a Etapa 2, con snapshot + restauración verificada byte a byte. Respondería Q1/Q4/Q5/Q6 y la parte directa de Q7, cerrando H5 y poniendo H1/H2/H3/H6 en términos de **eventos contados por frame**. Riesgo principal: disciplina de escritura/restauración (mitigada por §8 y abortos §10).
- **ETAPA 3-EXT (NO autorizable hoy):** ventana de shader para SQ/SPI (Q2), TCP/TA/TD (Q3) y SPM (Q4 fina). Requiere investigación previa de mecanismo (emisión del start/stop vía CP/ring con los mismos derechos que radeonsi/RADV) y **nueva autorización específica**. Solo si los directos dejan ambigüedad irresoluble.
- **NO justifica Etapa 3:** Q8 (driver), más sets de corridas repercutivos (añadir sets solo si un evento adicional gana a los 12 slots), instalación de GPUPerfAPI.
- **La ejecución de la Etapa 3 MÍNIMA queda condicionada a:** (a) aprobación del operador de este plan; (b) superación del PRE read-only (§8.1.1) para todos los slots; (c) sanity idle OK (§8.1.2). Fallar (a)/(b)/(c) → NO ejecutar.

---

## A. Artefactos y trazabilidad

- `FASE-D-ETAPA-2-AUDIT.md` (v1.4): reconstrucción, errores objetivos del informe, matriz de hipótesis — base de Q1–Q8.
- `FASE-D-ETAPA-2-RESULTADOS.md`: informe §4/§6/§7 (correcciones de AUDIT §9 pendientes de aplicar en próxima edición).
- `FASE-D-COUNTERS-AUDIT.md` (§0.2 corrige su aserción «SPM únicamente»).
- `runs/etapa2/{A1..B3}/`: artefactos de referencia (pre/post_flight, telemetria.csv, radeontop.csv, umr_samples.csv, metadata).
- `METRICS-DEFINITIONS.md`: 4 métricas y ventana steady obligatorias.
- Mesa `src/amd/common/ac_perfcounter.c` y `src/gallium/drivers/radeonsi/si_perfcounter.c`: tablas VI (bloques, `num_counters`, SELECT/SELECT1, flags `SHADER_WINDOWED`).
- Catálogos UMR de la máquina: `umr -lr gfx800`, `umr -lr gmc810` (read-only; parte de PRE).

## B. Estado del documento

**Etapa 3 diseñada — ejecución NO autorizada.** Este archivo es el entregable autorizado de diseño; no ejecuta corridas ni escribe registros. Para ejecutar se requiere: autorización explícita del operador + PRE read-only superado + sanity idle OK.
