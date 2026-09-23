# FASE-D-GFX8-EVENT-ID-AUDIT.md — Auditoría de Event IDs de Performance Counters GFX8 / Polaris12

> **Fecha:** 2026-09-21
> **Modo:** SOLO READ-ONLY. Sin escrituras, sin UMR -w, sin sudo, sin benchmarks, sin programar contadores, sin modificar GPU/sysfs/PowerPlay/Mesa/Kalm/rx550-torneo.
> **Objetivo:** determinar si existen fuentes locales suficientes para verificar los IDs de eventos (PERF_SEL) de los performance counters de GFX8 / Polaris12 (RX 550, PCI 01:00.0, device 0x699f).
> **Regla principal respetada:** NO inferir event IDs de otra generación.

---

## 1. Texto concluyente (Resultado B)

> **«Los IDs de eventos GFX8 no pueden verificarse mediante las fuentes locales disponibles.»**

Ninguna fuente local (Mesa actual + historial git completo de 222 644 commits, kernel amdgpu, amdgfxregs.h, UMR database, backups, /usr/share/doc, libdrm headers, LLVM instalado, documentación de usuario) contiene la tabla de eventos PERF_SEL para GFX8/Polaris12. Los únicos IDs numéricos encontrados pertenecen a GFX10.3 / GFX11 (RADV) y **no** son evidencia válida para Polaris12.

---

## 2. Fuentes investigadas

| # | Fuente local | Ubicación | Contenido encontrado relevante | Veredicto |
|---|---|---|---|---|
| 1 | **Mesa source (backup)** | `…/RX550_Modo_Torneo_Backup_2026-09-19_0836/mesa/mesa-source/` | `ac_perfcounter.{c,h}`, `ac_perfcounter_gfx{10,103,11,12}.c`, `radv_perfcounter.{c,h}`, `radeonsi/si_perfcounter.c`, `r600/r600_perfcounter.c`, `ac_cmdbuf_cp.c`, `si_gpu_load.c`, `radv_physical_device.c` | Sin tablas de eventos GFX8 |
| 2 | **Historial git Mesa completo** | `.git` en `mesa-source/` (222 644 commits; ramas `main`, `backup-main-before-mesa-2622`, `kimi-rx550-optimization`, `lexluthor/radv-binding-report-cleanup`, remotas `origin/10.0…26.x`) | Búsquedas `-S` sobre `GRBM_PERF_SEL_GUI_ACTIVE`, `SQ_PERF_SEL_WAVES`, `GUI_ACTIVE`, `PERFCOUNTER`, commits de enablement (`f905edb1991`, `acba4c9fd84`) | **Nunca existió** una tabla de eventos VI/GFX8 en Mesa |
| 3 | **amdgfxregs.h** | `…/mesa-26.2.2-build/build-rx550-haswell/src/amd/common/amdgfxregs.h` (23 481 líneas) | `R_` macros gfx7/8/x81/x9; enums `V_028A90` (eventos CP: START=23/STOP=24/SAMPLE=27); `V_036020_CP_PERFMON_STATE_*`; campos de SELECT (S_036100_PERF_SEL, S_036700_SQC_BANK/CLIENT_MASK, SIMD_MASK, S_036780_*_EN, COMPUTE_PERFCOUNT_ENABLE) | Sin `V_` del tipo PERF_SEL (sin valores de evento) |
| 4 | **UMR database** | `/usr/share/umr/database/ip/gfx_8_0_0.reg`, `gmc_8_1_0.reg` | 2633 registros (gfx8): nombres + offsets + bitfields (rango start:end). P.ej. `mmGRBM_PERFCOUNTER0_SELECT 0xd840` con `PERF_SEL 0 5`; `mmGRBM_STATUS 0x2004` con `GUI_ACTIVE 31 31` | **Solo registros y bitfields; CERO enums con valores de evento** (`grep '= 0x'` → vacío) |
| 5 | **Kernel source** | `/usr/src/kernels/7.0.0-200…`, `7.0.1-200…`, `7.2.4-201…` | `drivers/gpu/drm/amd/amdgpu/` contiene **solo `Kconfig` y `Makefile`** (0 archivos `.c`/`.h`) | No usable |
| 6 | **Mesa instalada / custom** | `/opt/mesa-26.2.2-rx550-haswell/` (lib64/include/share), Mesa sistema | Sin fuentes de eventos | No aporta |
| 7 | **Backups no-Mesa** | `…/Backup/…/{audit-history,data,etc,system,manifest,experiments}` y `code/` | Solo logs de benchmarks (`radeonsi, polaris12`, `RADV POLARIS12`, `0x699f`) y scripts | Sin tablas de eventos |
| 8 | **docs/headers del sistema** | `/usr/share/doc/{amdgpu,libdrm,mesa}*`, `/usr/include/drm/amdgpu_drm.h`, `/usr/lib64/llvm*/lib/` | Nada de eventos de contadores | Sin contenido |
| 9 | **Docs en `$HOME`** | `/home/lucas/**` (PDFs, uDocs, whitepapers GCN/Polaris) | **No existen** (búsqueda por nombre vacía) | Fuente primaria ausente |

---

## 3. IDs encontrados (por generación) — TODOS gated a GFX10.3/GFX11

Unicidad local: `src/amd/vulkan/radv_perfcounter.c`, enums internos `CTR(block, sel)` (S_REG_BLOCK | S_REG_SEL). **Ningún valor desprogramático para GFX8.**

| Símbolo | SEL | Generación real (donde se ejecuta) | Uso en radv |
|---|---|---|---|
| `GRBM_PERF_SEL_GUI_ACTIVE` | **2** | GFX10.3 (y potencial <GFX11 si se habilitara; ver §8) | Op `GPU_CYCLES` «GPU active cycles» (radv_perfcounter.c:164,231-232) |
| `SQ_PERF_SEL_WAVES` | **4** | GFX10.3 (ramas <GFX11) | Op `SHADER_WAVES` «Waves» (línea 194, 260-261) |
| `SQ_PERF_SEL_INSTS_ALL_GFX10` | 0x31 | GFX10.3 | Instructions |
| `SQ_PERF_SEL_INSTS_VALU_GFX10` | 0x40 | GFX10.3 | VALU Instructions |
| `SQ_PERF_SEL_INSTS_SALU_GFX10` | 0x3c | GFX10.3 | SALU Instructions |
| `SQ_PERF_SEL_INST_CYCLES_VALU_GFX10` | 0x75 | GFX10.3 | VALU Busy |
| `SQ_PERF_SEL_INSTS_{GDS,LDS,SMEM,TEX_LOAD,TEX_STORE}_GFX10` | 0x37,0x3b,0x3d,0x45,0x46 | GFX10.3 | instr. por clase |
| `SQ_PERF_SEL_WAVES_GFX11` | **0x14** | GFX11 (¡distinto de 4!) | Waves GFX11 |
| `SQ_PERF_SEL_INSTS_*_GFX11` (bloque `SQ_WGP`) | 0x36..0x67 | GFX11 | idem |
| `GL1C_PERF_SEL_REQ` / `REQ_MISS` | 0xe / 0x12 | GFX10.3 | L1 hit ratio |
| `GL2C_PERF_SEL_REQ` | 0x3 | GFX10.1/10.3 | L2 requests |
| `GL2C_PERF_SEL_MISS_GFX101` / `_GFX103` | 0x23 / 0x2b | GFX10.1 / GFX10.3 | L2 miss |
| `GL2C_PERF_SEL_MC_WRREQ_GFX101` / `_GFX103` | 0x4b / 0x53 | GFX10.1 / GFX10.3 | VRAM write |
| `GL2C_PERF_SEL_EA_{RD,WR}REQ_{32,64,96,128}B_GFX101/103` | 0x4c/0x59-0x5c y 0x55/0x63-0x66 | GFX10.1/GFX10.3 | VRAM read/write bytes |
| `TCP_PERF_SEL_REQ_GFX10` / `REQ_MISS_GFX10` | 0x9 / 0x12 | GFX10.3 | L0 hit ratio |
| `CPF_PERF_SEL_CPF_STAT_BUSY_GFX10` | 0x18 | GFX10/GFX10.3/GFX11 | denominador de Busy% |

Evidencia de la mecánica (compartida por SI/CIK/VI en código, aunque los IDs no): secuencia start/stop/sample/reloj vía `V_028A90_PERFCOUNTER_START=23/STOP=24/SAMPLE=27` y `CP_PERFMON_CNTL` — VERIFICADO (ya en `FASE-D-ETAPA-3-EVENTS.md`), distinto de «valores de PERF_SEL», que es lo que esta auditoría NO pudo verificar para GFX8.

---

## 4. IDs válidos para GFX8 / Polaris12

**Ninguno.** No existió selectores numéricos en ninguna fuente local con gating o aplicación real a GFX8.

- `radeonsi` (conductor OpenGL que **sí** soporta GFX8 y `AMD_performance_monitor`): `si_perfcounter.c` solo **reenvía el selector que el usuario pide** (`group->selectors[..] = sub_index` → `selectors[idx] | regs->select_or`). Meso nunca definió la semántica de los eventos VI; la lista vive del lado de la app (CodeXL/GPUPerfAPI).
- `r600_perfcounter.c` (GFX6): mismo patrón de passthrough; sus tablas con eventos viven en cada chip del driver r600 y son **GFX6**, no GFX8.
- El driver que sí usa contadores HW en GFX8 con nombres es solo el mecanismo, no los eventos (§2).

---

## 5. IDs no válidos / no demostrados para GFX8

| Supuesto | Estado |
|---|---|
| `GRBM PERF_SEL = 2` ⇒ «GPU active / GUI active» | **NO VERIFICADO para GFX8** (ver §8) |
| `SQ PERF_SEL = 4` ⇒ «Waves» | **NO VERIFICADO para GFX8** (ver §9) |
| Resto de eventos RADV (GL1C/GL2C/TCP/SQ*_GFX10/GFX11, CPF busy) | **NO VERIFICADO para GFX8** — definidos/atribuidos a GFX10/10.3/11 (nombres `_GFX10`, `_GFX101`, `_GFX103`, `_GFX11` explícitos) |
| GRBMSE/SX/CB/DB/SPI/TCC/TCA/TA/TD/MC_EN (eventos vía selectores) | NO VERIFICADO (sin listado local alguno) |

---

## 6. Diferencias entre generaciones (evidenciadas localmente)

- **SQ WAVES:** GFX10.3 = **0x4** (bloque `SQ`) vs GFX11 = **0x14** (bloque `SQ_WGP`). Mismo evento comercial, distinto valor → jamás asumir portabilidad.
- **GL2C MISS:** GFX10.1 = 0x23 vs GFX10.3 = 0x2b; **EA_*REQ**: distintos por familia (0x4c/0x59-0x5c vs 0x55/0x63-0x66).
- **SQ instrucciones:** GFX10.1 usa sufijos `_GFX10` (-0x31..0x75), GFX11 usa `_GFX11` (0x36..0x67) y bloques `SQ_WGP`; valores no compartidos.
- **CPF_STAT_BUSY:** la constante `_GFX10` (0x18) se reutiliza en GFX11 ("_GFX10" en el nombre), otra señal de que los numerales se mueven entre generaciones.
- **Eventos CP (V_028A90):** START/STOP/SAMPLE = 23/24/27 son estables gfx7→gfx10 (VERIFICADO en amdgfxregs, idénticos para `<= gfx9` y `>= gfx10`); NO son PERF_SEL, y no validan eventos de contador.
- **registros vs eventos:** la pieza de registro (SELECT/CTRL/CP_PERFMON_CNTL/GFX_INDEX) es idéntica en estructura gfx7/gfx8/x81/x9 (amdgfxregs); la pieza «qué valor escribir en PERF_SEL» es la que cambia por chip y NO está localmente.

---

## 7. Bloqueos

- **BLOQUEADO — Primera escritura `GRBM_PERFCOUNTER0_SELECT = 0x2`:** no se puede demostrar que el evento nº2 de GRBM en GFX8 signifique «GPU active». BLOQUEADO científicamente (no solo por autorización).
- **BLOQUEADO — Etapa 3 mínima de 12 slots** del plan: depende de IDs de evento que ninguna fuente local verifica.
- **BLOQUEADO ambiental — lectura MMR en vivo** (root) y cualquier prueba de contadores.

---

## 8. GRBM = 2 (análisis específico)

- ¿Existe fuente local que confirme 2 = GPU active **en GFX8**? **No.**
- Corroboración parcial solo del **concepto**: `mmGRBM_STATUS` (0x2004) tiene el bit `GUI_ACTIVE 31` (UMR db gfx8) y `si_gpu_load.c`/`r600_gpu_load.c` computan la carga de la GPU con ese **bit de estado** (no un contador). El nombre «GUI_ACTIVE/GPU active» existe en GFX8 como semántica de estado, pero **ninguna fuente local** lo vincula al valor del campo PERF_SEL del registro SELECT.
- El valor `2` de radv (`GRBM_PERF_SEL_GUI_ACTIVE = CTR(GRBM, 2)`) es una constante genérica introducida en 2022-06-04 (`439e4b5c88b`) junto con constantes GFX10; el gate de la extensión (`radv_perf_query_supported`, `radv_physical_device.c:55-61`) solo deja ejecutarla en **GFX10_3** o **GFX11..11.5**; el comentario del commit de enablement es *«the code has only been tested on GFX10.3»* (`f905edb1991`). En GFX8 **nunca se ejecutó ni validó**.
- Conclusión: **NO marcar como VERIFICADO** aunque aparezca en Mesa moderna. Como máximo «PARCIALMENTE VERIFICADO» (solo constancia de la semántica GUI_ACTIVE de estado en GFX8, sin vínculo al selector). Para el diseño experimental se trata como **NO DEMOSTRADO / BLOQUEADO**.

---

## 9. SQ = 4 (análisis específico)

- ¿Fuente local que confirme 4 = Waves **en GFX8**? **No.**
- El único lugar con `4` es el enum `SQ_PERF_SEL_WAVES = CTR(SQ, 0x4)` (radv, GFX10-era) — mismo caveat de gate y de «solo probado en GFX10.3».
- Contra-evidencia de portabilidad dentro de la única fuente que define estos números: **GFX11 usa 0x14** y bloque `SQ_WGP`. No hay por qué suponer que GFX8 comparta con GFX10.3.
- Conclusión: **NO VERIFICADO para GFX8** (ni siquiera parcialmente; sin corolario de estado para SQ).

---

## 10. Decisión sobre la primera escritura

- `GRBM_PERFCOUNTER0_SELECT = 0x2` **NO es** científicamente válido para nuestra RX 550 con el conocimiento local actual → **BLOQUEADA**. No ejecutar.
- Equivalentemente, la propuesta §H de `FASE-D-ETAPA-3-EVENTS.md` se anula en su paso 2 hasta disponer de un mapa de eventos GFX8 verificado.

---

## 11. Fuente primaria faltante

La tabla de eventos PERF_SEL **del bloque VGT/GRBM/GRBMSE/SX/SQ/SPI/CB/DB/TCC/TCA/TA/TD/TCP/MC para VI/GFX8** (Polaris12 = gfx803). Vive en material de AMD no presente localmente:

1. **GPUPerfAPI** (`perfgeneration.h`, enums `GPA_HW_EXPORTED_COUNTER_*` por chip/generation; paquete offline, licencia AMD, no instalado).
2. **CodeXL / RGP — "Hardware Performance Counters"** para Polaris (listados `CONSOLE_EVENT_*`).
3. Documentación oficial **"Radeon Performance Counters / Polaris"** (PDF whitepaper GCN + suplemento por ASIC).
4. (Sí existen en el kernel upstream moderno tablas por uArch para *otras* familias, p.ej. `drivers/gpu/drm/amd/amdgpu/nm_...` de GFX10/11; **VI no las tiene** y el árbol local ni siquiera trae el código).

Cualquiera de estas, aportada como fuente local o autorizada y citada por generación (GFX8/gfx803), permitiría rehacer la tabla del plan. También serviría cross-check: ejecutar un cacho de tests con `AMD_performance_monitor` (radeonsi escribe el selector que la app pide) *disponible en la GFX8*, pero requiere app+autorización+lectura de resultados — no realizados aquí.

---

## 12. Entregable y estado

- Crear/actualizar: `FASE-D-GFX8-EVENT-ID-AUDIT.md` (este documento).
- `MASTER-RESEARCH-STATUS.md`: sin numerical addenda salvo la frase «Auditoría de Event IDs GFX8 completada; programación permanece NO autorizada.»
- `FASE-D-ETAPA-3-EVENTS.md`: §H marcada como **BLOQUEADA** (ver nota en archivo).

**Estricto read-only. Sin escrituras, sin benchmarks, sin programar, sin solicitar contraseña, sin modificar el sistema. Detener aquí.**

---

## 13. Búsqueda explícita de los tokens solicitados (item 1)

Regex `GFX80[0-5]`, `polaris1[12]`, `gfx800`, `gfx803`, `PERF_SEL` en `mesa-source/src/**` (c/cpp/h) y en UMR db:

| Token | Meso src (hits) | Significado de los hits | UMR gfx_8_0_0.reg |
|---|---|---|---|
| `GFX801` | 2 | `ac_rgp.c:861,875` → `EF_AMDGPU_MACH_AMDGCN_GFX801` (machine-type GCN ELF para marcadores RGP; **no** es event ID) | 0 |
| `GFX802` … `GFX805` | 0 | — | 0 |
| `gfx800` / `gfx803` | 0 | — (el archivo gfx8 de registros se llama `gfx_8_0_0` por convención de IP) | 0 |
| `polaris11` | 19 | `ac_gpu_info.c`, `amd_family.{c,h}`, `si_state_draw.cpp`, `si_state_msaa.c`, `amdgpu_devices.c`, addrlib (`siaddrlib.h`), `aco_print_asm.cpp` → solo **identificación de familia/ASIC** (family `CHIP_POLARIS11/12`, feature flags, nombres), ninguna tabla de eventos | 0 |
| `polaris12` | 23 | idem (identificación de familia, `CHIP_POLARIS12`) | 0 |
| `PERF_SEL` | — | presente como **campo de registro** (S_036100_PERF_SEL, etc.), nunca como tabla de valores | 158 (bitfield de SELECTs; sin valores) |

Conclusión: los tokens buscados no aportan event IDs para GFX8/Polaris12; todo lo coincidente es identificación de maqueta o campos de registro, no el mapa de eventos.

---

## 14. Resultado B — Revisión posterior a FASE R-0 (2026-09-22)

> **Adenda de FASE R-1 (reconciliación documental).** La conclusión histórica del **Resultado B** (§1) —
> «los IDs de eventos GFX8 no pueden verificarse mediante las fuentes locales disponibles» — **sigue siendo
> correcta para las fuentes LOCALES** y **no se elimina ni se reescribe**. Lo que añade esta revisión es que
> R-0 encontró la **fuente externa oficial verificable** que la §11 («Fuente primaria faltante», punto 1:
> GPUPerfAPI) anticipaba como candidata.

**Novedades aportadas por FASE R-0 (ver `experiments/FASE-R0-EXTERNAL-KNOWLEDGE/`):**

1. **GPUPerfAPI `v3.11.1` SÍ contiene tablas completas de event IDs GFX8** (documento `R0-1-GFX8-EVENT-IDS.md`
   [VERIFICADO]): catálogos autogenerados `gpa_hw_counter_gfx8.cc/.h`, `gpa_hw_exposed_counters_gfx8.cc`,
   `public_counter_names_vk_gfx8{,_baffin,_ellesmere}.txt`. Referencia consolidada de 2304 contadores expuestos
   en `R0-1-GFX8-EVENT-ID-REFERENCE.txt`.
2. **GRBM GUI_ACTIVE = 2 VALIDADO para GFX8** (`GRBM_PERF_SEL_GUI_ACTIVE = 2` en catálogo AMD). La constante RADV
   «2» deja de ser «no probada en GFX8»: queda refrendada por la tabla AMD GFX8. Revierte el bloqueo científico de
   §§7/8/10 sobre la primera escritura `GRBM_PERFCOUNTER0_SELECT=0x2`.
3. **SQ WAVES = 4 VALIDADO para GFX8** («`SQ*_PERF_SEL_WAVES = 4`» en los 8 sub-bloques SQ). Contra-evidencia GFX11
   (0x14) sigue siendo válida como aviso de no-portabilidad entre generaciones, pero ya no bloquea GFX8.
4. **GPUPerfAPI v4.0+ eliminó GCN (GFX8/GFX9)** → cualquier recuperación futura debe usar el tag `v3.11.1`.

**Discrepancias de conteo detectadas y estado de reconciliación** (análisis detallado en
`experiments/FASE-R1-DOCUMENTATION-RECONCILIATION/R1-1-GFX8-EVENT-RECONCILIATION.md`):

| Bloque | Local (§5/§E EVENTS) | GPUPerfAPI | Estado |
|---|---|---|---|
| CB | 405 selectors (máx. clase VI) | 396 event IDs (0..395) | **PARTIALLY_RECONCILED** (misma base de datos, conteo de alcance distinto) |
| SQ | 273 selectors (máx. clase VI) | 299 event IDs (0..298) | **PARTIALLY_RECONCILED** (idem; SQ WAVES=4 coherente en ambas) |
| MC | 22 selectors (máx. clase VI) | 33 event IDs (0..32) | **PARTIALLY_RECONCILED** en conteo · semántica/unidad MC **UNRESOLVED** |

**Efecto sobre las conclusiones previas de este documento (NO las borra, las contextualiza):**
- §7 bloqueo de la primera escritura: cambia de «sin verificación posible» a «**verificado documentalmente**;
  la ejecución sigue NO autorizada» (la autorización es condición separada).
- §8 (§8 GRBM=2) y §9 (§9 SQ=4): «NO VERIFICADO para GFX8» → **[VERIFICADO] documentalmente para GFX8**.
- §§1/2/3/4/5/6: permanecen tal cual (validez del método de auditoría local y de «ninguna fuente local»).
- **La programación de contadores sigue NO autorizada**; nada de esta adenda habilita escritura.

**Traceabilidad:** sección creada por FASE R-1 (tarea R-1.2) sin modificar el historial anterior; cruza
`R0-1-GFX8-EVENT-IDS.md`, `R0-6-HERRAMIENTAS-HISTORICAS-GFX8.md`, `R1-1-GFX8-EVENT-RECONCILIATION.md` y
`MASTER-RESEARCH-STATUS.md` (v2.5).