# R0-1 — Catálogo de Performance Counters GFX8 (Polaris12): GPUPerfAPI v3.17 / v3.11.1 histórico

> **Archivo:** `R0-1-GFX8-EVENT-IDS.md` (referencia completa: `R0-1-GFX8-EVENT-ID-REFERENCE.txt`)
> **Fase:** FASE R-0 — EXTERNAL KNOWLEDGE RECOVERY / RESOLUCIÓN DE GAP R-0.1 (crítico FASE M)
> **Fecha:** 2026-09-22 — Modo SOLO DOCUMENTAL (read-only; descarga en /tmp, sin instalación)
> **Clasificación:** [PARTIALLY_RECONCILED / CATALOG ONLY] — filas y nombres genéricos
> extraídos de fuente primaria; no prueban evento, semántica ni seguridad en `1002:699f`.
>
> **RECONCILIACIÓN DE FUENTES (2026-09-24):** `v3.11.1` queda como extracción
> histórica; la referencia operativa de tablas GFX8 es `v3.17` (la rama v4 eliminó
> GFX8/GFX9). `2304` significa filas expuestas por el catálogo, no eventos únicos ni
> validados para `1002:699f`. Las tablas son genéricas GFX8; la aplicabilidad al ASIC
> Polaris12 y la equivalencia nominal `gfx803/gfx804` no están resueltas. Un rango
> `0..N-1` es un índice de catálogo, no una garantía semántica de seguridad.
> Fuentes upstream:
> - https://github.com/GPUOpen-Tools/gpu_performance_api/tree/v3.17
> - https://github.com/GPUOpen-Tools/gpu_performance_api/tree/v3.11.1
> - https://github.com/GPUOpen-Tools/gpu_performance_api/releases/tag/v4.0.0

---

## 1. Conclusión operativa reconciliada

**El gap R-0.1 queda parcialmente acotado, no resuelto para el ASIC:** la fuente
`GPUOpen-Tools/gpu_performance_api` en `v3.17` contiene tablas GFX8 genéricas y
`v3.11.1` conserva la extracción histórica. La presencia de una fila o un nombre no
acredita que el evento exista, tenga semántica conocida o sea programable en la RX550
`1002:699f`. El ASIC se documenta de forma neutral como `Polaris12/GFX8`; no se
promueven equivalencias `gfx803/gfx804`.

- En `gpa_hw_counter_gfx8.cc` (7,83 MB) los arrays usan **índices contiguos por bloque**
  (0..N-1) como `counter_index_in_group`/PERF_SEL a nivel source-level; esto no valida
  la existencia o seguridad de cada evento en el ASIC.
- En `gpa_hw_exposed_counters_gfx8.cc` y `public_counter_names_vk_gfx8*.txt` residen los **nombres
  canónicos** (ej: `GRBM_PERF_SEL_GUI_ACTIVE`).
- `public_counter_names_vk_gfx8_baffin.txt` e `_ellesmere.txt` son idénticos (diff vacío):
  los nombres expuestos son **genéricos GFX8**, no ASIC-specific; la aplicabilidad a
  Polaris12 queda `UNKNOWN`.
- **GPUPerfAPI v4.0+ eliminó el soporte GCN (GFX8 y GFX9)**. Para una referencia actual
  de tablas GFX8 usar `v3.17`; `v3.11.1` queda como historial de extracción y no como
  prueba de runtime.

### 1.1 Estructura del evento (confirmada por código)

- `struct GpaHardwareCounterDesc` (gpa_counter.h) → primer campo:
  `counter_index_in_group` (= `block_event_id` = valor de PERF_SEL).
- `gpa_counter_generator_base.cc` (líneas ~347-458): parses tokens `block, instance, event id,
  alternate_name`; resolución `GetIndex(gpa_hardware_block, block_instance, block_event_id, …)`.
- Un bloque+instancia+event_id identifica una entrada de catálogo; no basta para
  programar ni para probar que exista en `1002:699f`. El nombre expuesto es evidencia
  de catálogo, no de runtime.

---

## 2. Catálogos internos GFX8 — identidades por bloque (índice = event ID)

### 2.1 Conteos de eventos expuestos (documentados) — 2304 filas extraídas

| Bloque | Eventos expuestos | Valor observado clave (event_id = PERF_SEL) |
|---|---|---|
| **CB** (16 inst) | 10/inst → 160 | `CB0_PERF_SEL_DRAWN_QUAD_FRAGMENT=7`, `CM_MC_WRITE_REQUEST=116`, `FC_MC_WRITE_REQUEST=117`, `CC_MC_WRITE_REQUEST=118`, `CM_MC_READ_REQUEST=126`, `FC_MC_READ_REQUEST=127`, `CC_MC_READ_REQUEST=128`, `EXPORT_32_ABGR_QUAD_FRAGMENT=162`, `FC_MC_DCC_WRITE_REQUEST=257`, `FC_MC_DCC_READ_REQUEST=259` |
| **DB** (16 inst) | 15/inst → 240 | rango visto 4–188 (P0/P1/P2/P3_HIZ_QUAD_COUNT etc.) |
| **GPUTime** | 6 | — |
| **GRBM** | **2** | **`GRBM_PERF_SEL_COUNT=0`, `GRBM_PERF_SEL_GUI_ACTIVE=2`** |
| **PA_SC** (4) | 9/inst → 36 | `PA_SC0_QZ0_QUAD_COUNT=163`, `_P0_HIZ_QUAD_COUNT=239`, `_EARLYZ_QUAD_COUNT=263` |
| **PA_SU** (4) | 13/inst → 52 | `PA_SU0_PERF_PAPC_PA_INPUT_PRIM=8`, `PA_SU0_PERF_PAPC_CLPR_CULL_PRIM=14` |
| **SPI** (4) | 18/inst → 72 | `SPI0_PERF_VS_BUSY=1`, `_VS_WAVE=10`, `_CSG_BUSY=58`, `_CSG_NUM_THREADGROUPS=59`, `_CSG_WAVE=62`, `_CSN_BUSY=64`, `_CSN_NUM_THREADGROUPS=65`, `_CSN_WAVE=68`, `_PS_CTL_BUSY=70`, `_PS_CTL_WAVE=75` |
| **SQ** (base + CS/ES/GS/HS/LS/PS/VS, 4 c/u) | 16/inst → 8 bloques × 64 = 512 | **`SQ*_PERF_SEL_WAVES=4`**, `_ITEMS=14`, `_INSTS_VALU=26`, `_INSTS_VMEM_WR=27`, `_INSTS_VMEM_RD=28`, `_INSTS_SALU=30`, `_INSTS_SMEM=31`, `_INSTS_FLAT=32`, `_INSTS_FLAT_LDS_ONLY=33`, `_INSTS_LDS=34`, `_INSTS_GDS=35`, `_WAIT_INST_LDS=61`, `_INST_CYCLES_VALU=81`, `_INST_CYCLES_SALU=86`, `_THREAD_CYCLES_VALU=89`, `_LDS_BANK_CONFLICT=97` |
| **SX** (4) | 8/inst → 32 | — |
| **TA** (64) | 16/inst → 1024 | — |
| **TCC** (16) | 5/inst → 80 | — |
| **TCP** (64) | 1/inst → 64 | `TCP0_PERF_SEL_TCP_TA_DATA_STALL_CYCLES=3` |
| **VGT** (4) | 6/inst → 24 | — |

**Total de filas expuestas: 2304** → `R0-1-GFX8-EVENT-ID-REFERENCE.txt` (tabla evento/nombre/grupo).
No equivale a 2304 eventos únicos ni a 2304 eventos validados para Polaris12.

### 2.2 Catálogos internos por bloque (índice contiguo = event IDs disponibles)

Del array interno `k<Block>CountersGfx8[]` de `gpa_hw_counter_gfx8.cc` (índices 0..N-1 por
bloque/instancia) — memoria de los archivos consultados:

| Bloque | Instancias | Events (índices) | Nota vs doc local Mesa |
|---|---|---|---|
| Cb | 16 | 396 | 405 en si_perfcounter/uM no comparable (nombres distintos) |
| Cpc | 1 | 24 | — |
| Cpf | 1 | 19 | — |
| Cpg | 1 | 48 | — |
| Db | 16 | 257 | — |
| Gds | 1 | 121 | — |
| Gpin | 1 | 5 | — |
| GpuTime | 1 | 6 | — |
| GpuTimestamp | 1 | 1 | — |
| Grbm | 1 | 34 | — |
| Grbmse | 4 | 15 | — |
| Ia | 2 | 24 | — |
| Mc | 32 | 33 | MC=22 en doc local (discrepancia a notar) |
| PaSc | 4 | 397 | — |
| PaSu | 4 | 153 | — |
| Rlc | 1 | 7 | — |
| Sdma | 2 | 62 | — |
| Spi | 4 | 197 | — |
| Sq | 4 (+ SqCs/SqEs/SqGs/SqHs/SqLs/SqPs/SqVs 4 c/u) | 299 | SQ=273 en doc local (discrepancia a notar) |
| Srbm | 1 | 27 | — |
| Sx | 4 | 34 | — |
| Ta | 64 | 119 | — |
| Tca | 2 | 35 | — |
| Tcc | 16 | 192 | — |
| Tcp | 64 | 180 | — |
| Td | 64 | 55 | — |
| Vgt | 4 | 147 | — |
| Wd | 1 | 37 | — |

**Importante:** los arrays internos definen un rango de índices (`0..N-1`) por bloque.
Ese rango no prueba que cada índice tenga semántica conocida, que exista en el ASIC
concreto o que sea seguro programarlo. La aplicabilidad individual requiere nombre
canónico, backend/API, ASIC/family y generación; la programación sigue congelada.

### 2.3 Discrepancias vs documentación local (a registrar en matriz)

| Bloque | GPUPerfAPI gfx8 | Doc local (si_perfcounter/EVENTS) | Nota |
|---|---|---|---|
| CB | 396 | 405 (P12) | El doc local contaba selectores distintos (puesta de "selectors_count") — ver FASE-D-ETAPA-3 |
| SQ | 299 | 273 | Ídem; rango interno mayor en GPUPerfAPI |
| MC | 33 | 22 | Discrepancia a documentar: fuente de eventos MC distinta |

Estas diferencias corresponden a contar *métodos distintos*: GPUPerfAPI expone el rango completo
por unidad; si_perfcounter listaba solo selectores usables del driver. No invalida ninguna; se
reseñan por transparencia.

---

## 3. Validación cruzada con investigación local

1. **FASE-D (Resultado B)** decía "no hay tabla local de eventos GFX8" → confirmado para las
   fuentes locales auditadas. La fuente externa permite documentar entradas de catálogo,
   pero no valida el ASIC concreto ni el runtime.
2. **GRBM GUI_ACTIVE = 2** y **SQ WAVES = 4** quedan como *entradas nombradas en catálogos
   GFX8*, no como eventos validados para `1002:699f`. La ejecución/programación sigue
   `NO AUTORIZADA`.
3. **SPI_CSQ / SPI busy** y PA_SC/PA_SU son referencias de catálogo; la aplicabilidad al
   ASIC, la semántica y la seguridad de programación son `UNKNOWN`.

---

## 4. Restricciones de uso

- **SOLO REFERENCIA DOCUMENTAL.** Sigue **prohibido** programar contadores, escribir MMIO/sysfs o
  ejecutar experimentos que escriban en la GPU.
- La lectura del catálogo es evidencia de fuente, no de runtime. La extracción local
  `/tmp/opencode/gpa311/` está `PERDIDA / NO VERIFICABLE`; solo sobrevive el extracto
  `R0-1-GFX8-EVENT-ID-REFERENCE.txt`. La referencia upstream actual es `v3.17`; `v3.11.1`
  queda como historial.
- **No asumir que Polaris12 tiene presente todas las instancias catalogadas** (p.ej. TA 64
  instancias, TCC 16, Mc 32): la tabla es a nivel de familia GFX8; la unidad concreta expone las
  que tenga habilitadas por fuses (asunto de FASE polígono A→AJ del mapa P12). El **event ID es
  idéntico** lo use o no; la **instancia máxima** dependerá del ASIC.

---

## 5. Archivos de trabajo (en `/tmp/opencode/gpa311/`, referencia, NO instalados — **PERDIDO / NO VERIFICABLE**; recuperación parcial: `R0-1-GFX8-EVENT-ID-REFERENCE.txt`)

`gpa_hw_counter_gfx8.cc/.h`, `gpa_hw_counter_gfx8_baffin.cc/.h`, `gpa_hw_counter_gfx8_ellesmere.cc/.h`,
`gpa_hw_exposed_counters_gfx8.cc/.h`, `public_counter_names_vk_gfx8.txt`,
`public_counter_names_vk_gfx8_baffin.txt`, `public_counter_names_vk_gfx8_ellesmere.txt`,
`public_counter_definitions_gfx8.txt`, `public_counter_definitions_compute_gfx8.txt`,
`graphics_counter_tables_gfx8.rst`, `compute_counter_tables_gfx8.rst`, `gpa_counter.h`,
`gpa_counter_generator_base.cc`, `gpa_counter_generator_vk_base.cc`.

Fuente: https://github.com/GPUOpen-Tools/gpu_performance_api (tags v3.17 y v3.11.1). Licencia MIT.

---

## 6. Confianza

- **Alta (VERIFICADO):** presencia y contenido del catálogo AMD GFX8 en los tags upstream
  revisados; la presencia de una fila no implica validación para Polaris12.
- **Media-Alta:** equivalencia `counter_index_in_group = block_event_id = PERF_SEL` (deducida del
  código `gpa_counter_generator_base.cc` + estructura `GpaHardwareCounterDesc`; no es una
  declaración literal "event_id" en el JSON, pero es la única lectura coherente).
- No se manipula hardware; solo documenta los valores que *se escribirían* si la programación se
  autorizara en el futuro.
