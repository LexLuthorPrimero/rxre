# FASE D — ETAPA 3 / VERIFICACIÓN DE EVENTOS (offline, read-only)

> **Fecha:** 2026-09-21
> **Metodo:** solo fuentes locales (codigo Mesa en backup local, base de datos UMR, artefactos FASE D). Sin web, sin sudo, sin lecturas en vivo, sin registros.
> **Estado del encargo:** eventos investigados; programación NO autorizada.
>
> **Reconciliación 2026-09-24:** este documento conserva la investigación local
> pre-R-0. La catalogación externa posterior no valida GRBM/SQ para GFX8; ambos siguen
> `NO VERIFICADOS` para el ASIC y la escritura continúa bloqueada.

---

## 0. Alcance y método

Se verifica la tabla de eventos/counter blocks prevista en `FASE-D-ETAPA-3-PLAN.md` (§4.4) y `FASE-D-ETAPA-3-PRECHECK.md`, con el objetivo de asignar a cada slot: evento exacto (ID numérico), campo/bit, unidad, acumulatividad, método de selección/lectura, límites en Polaris12 y **fuente local que lo verifica**.

**Fuentes locales usadas (en orden de prioridad):**

| # | Fuente | Ruta | Contenido |
|---|---|---|---|
| 1 | Mesa source (backup) | `…/mesa/mesa-source/src/amd/common/ac_perfcounter.c|.h`, `…/src/amd/vulkan/radv_perfcounter.{c,h}`, `radv_physical_device.c` | Tablas de bloques VI/cik, flags, selectors_count, instancias, mecanismo CP completo |
| 2 | Header generado Mesa | `…/mesa-26.2.2-build/build-rx550-haswell/src/amd/common/amdgfxregs.h` (23 481 líneas) | R_ macros gfx8, enums CP_PERFMON_CNTL, eventos V_028A90, campos de selectores |
| 3 | UMR db local | `/usr/share/umr/database/ip/gfx_8_0_0.reg`, `gmc_8_1_0.reg` | Nombres/offsets/bitfields de los registros |
| 4 | Kernel amdgpu | `/usr/src/kernels/7.2.4-201.nobara.fc44.x86_64` | **NO DISPONIBLE localmente** (árbol recortado: `amd/amdgpu/` solo Kconfig/Makefile, sin `.c`) |
| 5 | Artefactos FASE D | Etapa 1 `FASE-D-COUNTERS-AUDIT.md`, PRECHECK, correos previos | Catálogos previos; no contienen IDs numéricos de eventos |

**Reglas:** no se rellenan IDs por inferencia. Sin ID numérico con fuente local → **NO VERIFICADO**. Sin manera segura de delimitar/leer → **NO UTILIZABLE** (para la etapa mínima). La exactitud manda sobre completar la tabla.

**Convención de direcciones (conciliación PRECHECK §7):** Mesa `R_03xxxx` = offset BYTE (R_ = addr×4); UMR usa dwords. Ej.: `R_036100` → `0xd840` (dword). «0x0d840» = nombre UMR.

---

## A. Mapeo contadores ↔ hipótesis científicas (FASE D)

| Hipótesis | Necesitamos (evento por bloque) | Slot del plan | IDs disponibles localmente |
|---|---|---|---|
| H1 – Geometría/primitivas | conteo de primitivas/triángulos/frontend (VGT/IA/PA_SU + GRBMSE por SE) | GRBM0/1, GRBMSE0 | Solo GRBM0 (ID 2, ciclos GPU activos — no es conteo de primitivas) |
| H3 – Textura/fetch | textura reach (TA/TCP) y L2 (TCC) | TA, TCP, TCC0 | **NO** (TA/TCP windowed → NO UTILIZABLE; TCC sin ID) |
| H4 – Shader/ALU | ondas/instrucciones ALU (SQ 16 ctrs, SPI 6 ctrs) | SQ, SPI | Solo SQ_WAVES (ID 4, parcial, caveat §C) |
| H5 – L1/L2 eficiencia | REQ vs REQ_MISS (TCC/TCP) | — | **NO** |
| H6 – VRAM/bandwidth | tráfico DRAM (MC_ARB/CITF, gmc810) | MC_ARB0/1 | **NO** (semántica de eventos unidad desconocida localmente); `mem_busy` sysfs VERIFICADO (%, no bytes) |
| Separación geometría-vs-shader | GRBM (front) vs SQ/SPI/SX | GRBM vs SQ/SX | Solo parcial GRBM0 (ciclos) |

**Conclusión de dominio (VERIFICADO):** los bloques existen y sus registros/offsets son correctos (conciliación Mesa↔UMR, tabla en Anexo). Los **IDs exactos de evento** para casi todos los bloques **no están en las fuentes locales** → mayoría NO VERIFICADO. Revierte directamente sobre la viabilidad de la Etapa 3 mínima (12 slots).

---

## B. Tabla maestra de eventos (por pregunta del encargo)

Columnas: Pregunta → Hipótesis → Bloque → Contador(es) → Registro → Evento → ID exacto → Campo/bit → Unidad → Acumulativo → Método selección → Método lectura → Normalización → Limitación Polaris12 → Fuente → Estado.

| Pregunta del encargo | Hipótesis | Bloque | Contador | Registro (UMR dword / Mesa byte) | Evento | ID exacto | Campo/bit | Unidad | Acumulativo | Selección | Lectura | Normalización | Limitación P12 | Fuente | Estado |
|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|
| ¿Cómo varía la actividad global de la GPU? | GRBM global | GRBM | PERFCOUNTER0 | `GRBM_PERFCOUNTER0_LO/HI` 0xd840 SEL / R_036100 | GPU active (ciclos) | **2** (RADV) | PERF_SEL[0:5] (6 b), USER_DEFINED 0-23 | ciclos | sí (Δ) | SELECT=2 (UMR -w) | disp. MMIO → Δ | /frame, /s | ID de fuente local pero nunca ejecutado en gfx8 (RADV gateado) | `radv_perfcounter.c` + `ac_perfcounter.c` | PARCIAL |
| Ídem segundo slot de contraste | evento frontend alternativo | GRBM | PERFCOUNTER1 | 0xd841 / R_036104 | (sin ID local) | — | PERF_SEL[0:5] | ciclos | sí | — | disp. MMIO | — | sin ID | ningún local | NO VERIFICADO |
| Actividad por shader engine (P12 = 1 SE) | geometría por SE | GRBMSE | SE0_PERFCOUNTER | 0xd045/0xd046/0xd842 SEL | (sin ID local) | — | PERF_SEL[0:5] | ciclos | sí | — | MMIO (GFX_INDEX SE=0) | — | 1 SE real (de 4 regs) | ningún local | NO VERIFICADO |
| Export/bus de shader (geometría→pixel) | SX export | SX | PERFCOUNTER0 | LO/HI 0xd240/1, sel 0xda40 (R_036900) | (sin ID local) | — | PERFCOUNTER_SELECT[0:9], [1]=[10:19] | eventos SX | sí | — | MMIO | — | P12 | ningún local | NO VERIFICADO |
| Eficiencia L2/textura | textura reach | TCC | PERFCOUNTER0 | LO 0xd180…, sel 0xdb80 (16 ctr) | (sin ID local) | — | PERF_SEL[0:7]… | eventos L2 | sí | — | MMIO | — | 1 instancia (Mesa VI) | ningún local | NO VERIFICADO |
| Ídem TCA (arbitración) | copper | TCA | PERFCOUNTER0 | sel 0xdb90 (2 inst) | (sin ID local) | — | PERF_SEL[0:9] | eventos | sí | — | MMIO GFX_INDEX inst | — | instancia 0/1 | ningún local | NO VERIFICADO |
| ROP/carga de salida de color | H2 por CB | CB | PERFCOUNTER0 | 0xd406 LO / sel 0xdc01 | (sin ID local) | — | PERF_SEL[0:8], SEL1[10:18] | eventos CB | sí | — | MMIO | — | P12 | ningún local | NO VERIFICADO |
| Depth/utilización raster | depth | DB | PERFCOUNTER0 | 0xd440 LO / sel 0xdc40 | (sin ID local) | — | PERF_SEL[0:9], SEL1[10:19] | eventos DB | sí | — | MMIO | — | P12 | ningún local | NO VERIFICADO |
| Onda/ocupación de shaders | Shader util | SQ | PERFCOUNTER0–15 | LO 0xd1c0.., sel 0xd9c0/R_036700 | Waves | **4** (%) | PERF_SEL[0:8]; SQC_BANK_MASK[12:15]; SQC_CLIENT_MASK[16:19]; SIMD_MASK[24:27] | ondas | sí (con ventana) | CTRL (R_036780/R_00B82C) + CP | requiere CP_COPY_DATA (radv) | /inst/job | cocina/ventana → **NO UTILIZABLE mínima** (requiere eventos CP PERFCOUNTER_START/STOP cf. §C) | RADV (parcial) | NO UTILIZABLE |
| Ocupación real de wavefronts | SPI | SPI | PERFCOUNTER0 | 0xd181 LO / sel 0xd980 | (sin ID local) | — | PERF_SEL[0:9]… | eventos SPI | sí | — | MMIO | — | P12 | (SPI_CSQ existe como lectura fija) | NO VERIFICADO |
| Textura/L1 (reach/ocupación) | TA | TA | PERFCOUNTER0 alt | LO 0xd2c0, sel 0xdac0 (R_036B00) | windowed | — | PERF_SEL[0:7] | eventos TA | ventana | NO (requiere CP) | — | — | sin ventana segura en UMR puro | Mesa flag SHADER_WINDOWED | NO UTILIZABLE |
| Ídem TCP (L1) | TCP | TCP | PERFCOUNTER0 | LO 0xd340, sel 0xdb40 (R_036D00) | windowed | — | PERF_SEL[0:7] | eventos TCP | ventana | NO | — | — | idem | Mesa flag | NO UTILIZABLE |
| Ídem TD | TD | TD | PERFCOUNTER0 | LO 0xd300, sel 0xdb00 (R_036C00) | windowed | — | PERF_SEL[0:7] | eventos TD | ventana | NO | — | — | idem | Mesa flag | NO UTILIZABLE |
| Bandwidth VRAM | H6 | MC | MC_ARB_P0..P3 | CFG 0x7bc-0x7bf, LO/HI 0x7a6/0x7ae, RSLT_CNTL 0x7d4 | (sin ID local) | — | PERF_SEL[0:7]+PERF_SEL_END[8:15] | indet. | snapshot | CFG + CTRL | MMIO lectura de LO/HI (1 canal a la vez) | — | unidad desconocida | `gmc_8_1_0.reg` (estructura) + amdgfxregs (no en header) | NO VERIFICADO |
| ATC (fallos de página/coherencia) | h6a | GMC | ATC_P0..P3 | CFG 0x7c8.., LO/HI 0x7a0-0x7ad†, RSLT_CNTL 0x7d5 | (sin ID local) | — | PERF_SEL[0:7] | eventos ATC | snapshot | CFG | MMIO | — | fallos no expuestos | (RSLT default 0x04000000 artefacto Etapa 1) | NO VERIFICADO |

† La marca «†» señala offsets no verificados numéricamente aquí; la fila **no** es lista para programar y **no** se completan offsets por inferencia.

**Lectura de la tabla:** Los únicos IDs numéricos visibles en el source local son **GRBM GUI_ACTIVE (PERF_SEL=2)** y **SQ WAVES (PERF_SEL=4)**; su semántica y aplicabilidad al ASIC GFX8 local no están validadas. La catalogación externa posterior los mantiene como entradas de catálogo, no como selectores runtime. Todo lo demás queda NO VERIFICADO o NO UTILIZABLE para la etapa mínima.

---

## C. SQ/SPI: mecanismo y partes CP vs MMIO (VERIFICADO, radv_perfcounter.c + amdgfxregs.h)

**Secuencia tal como la implementa RADV (`radv_begin_query`→`radv_perfcounter_emit_*`):**

1. **Selección (MMIO uconfig, vía PKT3_WRITE_DATA):** `ac_cmdbuf_set_ucfg_perfctr_reg(R_0361xx_GRBM/SQ/SX/…_PERFCOUNTERn_SELECT)` → en UMR puro sería escritura directa a 0xd840 (GRBM) / 0xd9c0 (SQ) / 0xda40 (SX)… .
2. **Control:** `R_036780_SQ_PERFCOUNTER_CTRL` escribido dos veces como `CTRL seq` si SQ (pre-GFX11): dword0 = `S_036780_PS_EN(1)|VS_EN(1)|GS_EN(1)|ES_EN(1)|HS_EN(1)|LS_EN(1)|CS_EN(1)` (0x7f) y dword1 = **SQ_PERFCOUNTER_MASK 0xffffffff** (CTRL2). En gfx10+ solo shaders&0x7f. Campos verificados en amdgfxregs: PS_EN=bit0…CS_EN=bit6, CNTR_RATE[8:12], DISABLE_FLUSH=bit13.
3. **Ventana (eventos CP, NO MMIO):** `V_028A90_PERFCOUNTER_START=23`, `V_028A90_PERFCOUNTER_SAMPLE=27`, `V_028A90_PERFCOUNTER_STOP=24` (VERIFICADO). Se escriben en `R_028A90_VGT_EVENT_INITIATOR` **vía IB** → **no emitible con UMR puro**.
4. **Habilitación SH:** `R_00B82C_COMPUTE_PERFCOUNT_ENABLE = S_00B82C_PERFCOUNT_ENABLE(1)` (bit0). En UMR db gfx8: `mmCOMPUTE_PERFCOUNT_ENABLE 0x2e0b` (VERIFICADO nombre/offset).
5. **Arranque/detención del conteo (MMIO):** `R_036020_CP_PERFMON_CNTL = S_036020_PERFMON_STATE(…START_COUNTING=1)` y al terminar `STOP_COUNTING=2` (+ SAMPLE_ENABLE). Valores VERIFICADOS en amdgfxregs: DISABLE_AND_RESET=0, START_COUNTING=1, STOP_COUNTING=2, DISABLE_AND_RESET_PHANTOM=4, COUNT_AND_DUMP_PHANTOM=5; campo PERFMON_STATE. Campo también presente en UMR db.
6. **Lectura:** `ac_cmdbuf_read_perfcounters` → **CP_COPY_DATA (PKT3)**, no lectura directa; UMR no puede reproducirlo.
7. **Reset post-query:** BACK_PERFMON/… rompe ventana; se restaura SELECT=0, CTRL=0, CP_PERFMON_CNTL=0 (DISABLE_AND_RESET).

**Consecuencia para Etapa 3 mínima (NO UTILIZABLE):**
- SQ/SPI que cuenten por ventana limpia necesitan pasos 3 y 6 (eventos + COPY_DATA) → **NO UTILIZABLE con UMR puro**.
- Sin la ventana, el contador SQ también avanzaría con solo `CP_PERFMON_CNTL=START` (hipótesis no confirmada por fuente local → no se puede afirmar; queda **NO VERIFICADO** y por seguridad se trata como NO UTILIZABLE).
- `SPI_CSQ_WF_ACTIVE_COUNT_0..7` (uso Etapa 1/2) sí son lectura directa (A/B), pero no son de evento ni configurables (estado).

---

## D. Memoria (gmc810): CFG / LO / HI / RSLT_CNTL (estructura VERIFICADA, eventos NO)

**Registros (UMR db `gmc_8_1_0.reg`, dwords):** `MC_ARB_PERFCOUNTER0..3_CFG` 0x7bc..0x7bf; `MC_ARB_PERFCOUNTER_LO` 0x7a6 y `_HI` 0x7ae (registro único de readback); `MC_ARB_PERFCOUNTER0..3_RSLT_CNTL` 0x7d4 (único compartido).

| Registro | Campo (bitfield, db) |
|---|---|
| `…_CFG` | PERF_SEL[0:7], PERF_SEL_END[8:15], PERF_MODE[24:27] |
| `…_RSLT_CNTL` | PERF_COUNTER_SELECT[0:3], START_TRIGGER[8:15], STOP_TRIGGER[16:23], ENABLE_ANY=24, CLEAR_ALL=25, STOP_ALL_ON_SATURATE=26 |

**Mecanismo (estructura):** los 4 selectores son config; un solo registro `LO/HI` muestra el contador indicado por `PERF_COUNTER_SELECT`; `START/STOP_TRIGGER`+`CLEAR_ALL` controlan el snapshot/borrado. Sin embargo:
- La **semántica de PERF_SEL de MC no está en ninguna fuente local** (amdgfxregs.h no contiene registros MC; kernel amdgpu no disponible) → **NO VERIFICADO**.
- Unidad (transacciones vs bytes vs ciclos) **NO VERIFICADA** → sin normalización en bytes.
- `ATC_PERFCOUNTER_RSLT_CNTL` visto en estado 0x04000000 (estado RESET) en artefacto Etapa 1 (idle) — consistente con lecturas 0x0 sin programar.
- **Alternativa ya VERIFICADA en Etapa 2:** `mem_busy_percent` (sysfs) mide % de periodo de tráfico, no volumen → solo como % complementario, no bytes/instrucción.

**Conclusión:** H6 solo puede apoyarse en `mem_busy` (%) — suficiente para «¿cuánto % de la carga es memoria?», insuficiente para «¿cuántos bytes por frame?» → la banda de memoria queda **NO VERIFICADA**.

---

## E. Instancias/agrupación (VERIFICADO, ac_perfcounter.c VI)

- GFX8 usa la tabla **`groups_VI`** (`case GFX8`, ac_perfcounter.c:713).
- **Instancias por bloque (VI):** solo `cik_TCA {n=35, instances=2}` → TCA se lee por 2 instancias (0/1); **TCC, TCP, TA, TD, SQ, SX, CB, DB, GRBMSE, SPI, MC}: instancia = 1** → **no sumar ni duplicar lecturas por SE/CU** en el modelo Mesa.
- Flags VI: CB/DB = `AC_PC_BLOCK_SE|AC_PC_BLOCK_INSTANCE_GROUPS`; GRBM/GRBMSE = sin flags; SQ = `AC_PC_BLOCK_SE|AC_PC_BLOCK_SHADER` (select_or = `SQC_BANK_MASK(15)|SQC_CLIENT_MASK(15)|SIMD_MASK(15)`); TA/TD/TCP = `SHADER_WINDOWED`.
- P12 tiene **1 sola SE**: los registros GRBM_SE1..SE3 existen pero no corresponden a HW activo → contadores SE0 (0xd045-0xd04c son SE0..SE3) solo se usan SE0.
- **selectors_count por bloque (VI, límite del campo PERF_SEL):** GRBM 34 (campo 6 b), GRBMSE 15 (6b), SX 34 (10b), TCC 192 (8b), TCA 35 (10b), CB 405 (9b), DB 257 (10b), SQ 273 (9b), SPI 197 (10b), TA 119 (8b), TD 55 (8b), TCP 180 (8b), MC 22 (8b), VGT 147, IA 24, WD 37, CPG 48, CPC 24, CPF 19, SRBM 27, GDS 121, PA_SC 397, PA_SU 154.

---

## F. TA / TD / TCP (windowed → NO UTILIZABLE para la etapa mínima)

- Mesa marca TA/TD/TCP como `SHADER_WINDOWED` (VI): su ventana de conteo se define **solo** con eventos PERFCOUNTER_START/STOP vía CP IB (§C) — imposible con UMR puro y sin garantía de delimitación segura.
- SPM (`RLC_SPM_*`) existe para TCP/TCC/TA pero es config avanzada y queda **excluido del plan** (PRECHECK).
- RADV (que sí sabe hacer las ventanas) **deshabilita** la query de rendimiento para gfx8 (`radv_perf_query_supported` → solo GFX10_3/GFX11) → no hay ni siquiera runtime local que las haga en P12.
- → Para textura/L1 la Etapa 3 mínima **no tiene ruta segura**: se marca **NO UTILIZABLE** (no bloqueamos el progreso; simplemente se descarta esta hipótesis para la etapa mínima).

---

## G. Priorización (VERIFICADO / NO VERIFICADO)

**Prioridad 1 (ninguna programación verificable en P12 hoy — ver auditoría `FASE-D-GFX8-EVENT-ID-AUDIT.md`):**
1. `GRBM_PERFCOUNTER0_SELECT=2` → **BLOQUEADA** (no se demuestra en GFX8 que el evento 2 sea «GPU active»). Solo queda infraestructura de lectura Δ y snapshot/restore (idempotente, reversible, sin programar).
2. Toma de estado de restauración (snapshot de SELECT/CTRL/CP_PERFMON_CNTL/GFX_INDEX) + métodos de lectura POST.

**Prioridad 2 (bloqueados por falta de ID local — solo programables si se autoriza el mapa de eventos desde fuente externa autorizada):**
- GRBM1 (segundo evento), GRBMSE0 SE0 (evento VGT/PA escala), SX/CB/DB, TCC/TCA requests, MC/ATC con CFG+RSLT (normalización al obtener unidad).

**Descartados para la etapa mínima (NO UTILIZABLE):**
- TA/TD/TCP (windowed CP); SQ/SPI por ventana (CP + COPY_DATA); conteo de bytes de banda MC (unidad NO VERIFICADA). Alternativa leer: `mem_busy` / `gpu_busy` / contadores de estado.

**Nota de corrección al catálogo Etapa 1 (`FASE-D-COUNTERS-AUDIT.md` §3):** el rango «GRBM_SE0..SE3 0x0d050-0x0d06f» debe ser `0x0d045 (SE0_LO) … 0x0d04c (SE3_HI)`; SPI tiene 6 contadores (0..5), no 2-3; SQ tiene 16 (0..15). Estas cifras quedan superadas por este documento.

---

## H. Diseño de la primera escritura hipotética (NO EJECUTAR — BLOQUEADA)

**NOTA (auditoría `FASE-D-GFX8-EVENT-ID-AUDIT.md`, 2026-09-21): esta primera escritura queda BLOQUEADA** — no existe fuente local que demuestre que el evento PERF_SEL=2 del GRBM en GFX8/Polaris12 signifique «GPU active». La constante es genérica de RADV, solo probada en GFX10.3. El paso 2 no es ejecutable.

Guarda histórica (cómo habría sido validar read/write si estuviera autorizada y verificada):

1. **Snapshot previo** (lecturas en vivo autorizadas): `GRBM_PERFCOUNTER0_SELECT`, `GRBM_PERFCOUNTER0_LO/HI`, `GRBM_SE0_…`, `SQ_PERFCOUNTER_CTRL`, `SQ_PERFCOUNTER0_SELECT`, `CP_PERFMON_CNTL`, `GRBM_GFX_INDEX`, `CPC_PERFCOUNTER0_SELECT` (default 0x000fffff), `ATC_PERFCOUNTER_RSLT_CNTL` (default 0x04000000).
2. **Escritura única:** `gfx800.mmGRBM_PERFCOUNTER0_SELECT = 0x2` — **BLOQUEADA** por la auditoría (sin verificación GFX8). No tocar LO/HI, ni CP_PERFMON_CNTL, ni SMU.
3. **Lectura post-exp:** mismas direcciones; verificado que `SELECT` se puede leer y que el valor persistió (opcional: LO no cambió sin trabajo; sin esperar cambio, es HW monitor).
4. **Restauración:** reescribir el valor snapshot (SELECT→0) y verificar; si no se puede leer para restaurar → **cold reboot** (por diseño, sin daño persistente).
5. **Criterios de aborto (objetivos):** cualquier divergencia del snapshot; aparición de VM fault/reset (baseline: 26 líneas de burst 06:40-06:41 sin resets en el journal); lectura de SELECT devolviendo distinto de 0x2; LO mutando sin trabajo correspondiente.
6. **Métrica de éxito:** valores finales idénticos al snapshot; ninguna fault nueva; SELECT permanece 0x2 tras ciclo completo.

Este diseño NO se ejecuta en esta fase (programación NO autorizada **y paso 2 BLOQUEADO por falta de verificación GFX8**, ver `FASE-D-GFX8-EVENT-ID-AUDIT.md`). Solo documenta cómo sería la primera programación si se autoriza y se verifica el evento.

---

## I. Conclusiones y entregables

1. **Mecanismo CP/eventos:** VERIFICADO en local (valores de CP_PERFMON_CNTL, eventos V_028A90, campos SQ_CTRL, COMPUTE_PERFCOUNT_ENABLE). La etapa mínima puede, **sin autorización**, solo:
   - saber el mapa completo de registros (VERIFICADO),
   - calibrar la unidad de lectura/restauración (VERIFICADO),
   - y NO programar (ninguna escritura realizada).
2. **IDs de eventos:** solo `GRBM PERF_SEL=2` y `SQ PERF_SEL=4` aparecen como constantes (radv), **pero con la auditoría `FASE-D-GFX8-EVENT-ID-AUDIT.md` quedan NO VERIFICADOS para GFX8** (solo probados en GFX10.3; GFX11 usa SQ WAVES=0x14). Sin mapa de eventos VI autorizado no hay manera de completar los 12 slots del plan.
3. **Acción siguiente del operador:** aportar el mapa de eventos GFX8 (GPUPerfAPI/CodeXL o documentación oficial Polaris por ASIC) como fuente local/autorizada; mientras tanto, Etapa 3 se reduce a observación read-only (`gpu_busy`, `mem_busy`, SPI_CSQ) — **sin programar nada**. La primera escritura §H queda BLOQUEADA.

---

## Anexo — conciliación de offsets Mesa↔UMR (VERIFICADO, no exhaustivo)

| Registro | Mesa byte | = dword UMR |
|---|---|---|
| `GRBM_PERFCOUNTER0_SELECT` | 0x036100 | 0x0d840 |
| `GRBM_SE0_PERFCOUNTER_SELECT` | 0x036108 | 0x0d842 |
| `GRBM_SE0_PERFCOUNTER_LO` | 0x034114 | 0x0d045 |
| `SQ_PERFCOUNTER0_SELECT` | 0x036700 | 0x0d9c0 |
| `SQ_PERFCOUNTER0_LO` | 0x034700 | 0x0d1c0 |
| `SQ_PERFCOUNTER_CTRL` | 0x036780 | 0x0d9e0 |
| `CP_PERFMON_CNTL` | 0x036020 | 0x0d808 |
| `GRBM_GFX_INDEX` | 0x030800 | 0x0c200 |
| `COMPUTE_PERFCOUNT_ENABLE` | 0x00B82C | 0x02e0b |

*`SQ_PERFCOUNTER0_SELECT` (0xd9c0) no debe confundirse con `SQ_PERFCOUNTER0_LO` (0xd1c0). Ambos verificados en UMR db.*

> **Estado final del encargo:** Etapa 3 investigada en profundidad a nivel de código/registros; **programación NO autorizada**. El plan de 12 slots mínima NO es realizable hoy sin el mapa de eventos VI. La primera escritura de §H queda **BLOQUEADA** por la auditoría `FASE-D-GFX8-EVENT-ID-AUDIT.md` (GRBM=2 no verificado para GFX8).
