# R0-1 — Event IDs de Performance Counters GFX8 (Polaris12): GPUPerfAPI v3.11.1

> **Archivo:** `R0-1-GFX8-EVENT-IDS.md` (referencia completa: `R0-1-GFX8-EVENT-ID-REFERENCE.txt`)
> **Fase:** FASE R-0 — EXTERNAL KNOWLEDGE RECOVERY / RESOLUCIÓN DE GAP R-0.1 (crítico FASE M)
> **Fecha:** 2026-09-22 — Modo SOLO DOCUMENTAL (read-only; descarga en /tmp, sin instalación)
> **Clasificación:** [VERIFICADO] — evento → valor PERF_SEL confirmado por fuente primaria AMD
> (catalogo autogenerado del repo oficial de eventos).

---

## 1. Conclusión operativa

**El gap R-0.1 queda RESUELTO:** la fuente `GPUOpen-Tools/gpu_performance_api` en su **tag
`v3.11.1`** contiene las tablas completas de contadores HW de GFX8 (compatible con GCN 4.º /
`gfx803` → Polaris12 / RX 550 `1002:699f`), con **nombres de evento reales y valores numéricos
exactos** que se escriben en los registros `*_PERFCOUNTERn_SELECT` (campo PERF_SEL).

- En `gpa_hw_counter_gfx8.cc` (7,83 MB) los **índices contiguos por bloque son los event IDs
  completos** (0..N-1) — el índice = valor PERF_SEL.
- En `gpa_hw_exposed_counters_gfx8.cc` y `public_counter_names_vk_gfx8*.txt` residen los **nombres
  canónicos** (ej: `GRBM_PERF_SEL_GUI_ACTIVE`).
- `public_counter_names_vk_gfx8_baffin.txt` e `_ellesmere.txt` son idénticos (diff vacío):
  los nombres de evento expuestos son **genéricos GFX8**, no ASIC-specific (no hay tabla
  específica "polaris12" separada; gfx803 queda cubierto por la tabla GFX8 base).
- **GPUPerfAPI v4.0+ eliminó el soporte GCN (GFX8 y GFX9)** → FASE M: usar exclusivamente tag
  v3.11.1; la rama main/master NO aporta.

### 1.1 Estructura del evento (confirmada por código)

- `struct GpaHardwareCounterDesc` (gpa_counter.h) → primer campo:
  `counter_index_in_group` (= `block_event_id` = valor de PERF_SEL).
- `gpa_counter_generator_base.cc` (líneas ~347-458): parses tokens `block, instance, event id,
  alternate_name`; resolución `GetIndex(gpa_hardware_block, block_instance, block_event_id, …)`.
- Un bloque+instancia+event_id identifica de forma inequívoca qué contador programar. El parent
  expuesto mapea a los nombres reales en la referencia.

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

**Total extraído: 2304 filas** → `R0-1-GFX8-EVENT-ID-REFERENCE.txt` (tabla evento/nombre/grupo).

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

**Importante:** los catálogos internos definen el **rango de event IDs válidos** (0..N-1) por
bloque, con o sin nombre expuesto. Estos rangos son la referencia para validar cualquier selector
que se quiera programar (p.ej. `GRBM PERF_SEL < 34` siempre válido; `SQ PERF_SEL < 299`).

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

1. **FASE-D (Resultado B)** decía "no hay tabla local de eventos GFX8" → **confirmado**: ninguna
   fuente local la tiene. Pero **existe fuente externa verificable sin need de escribir
   hardware**, y ahora está disponible de forma read-only. **Resultado B se actualiza**: los IDs
   GFX8 ya NO dependen de inferencia; pueden citarse desde GPUPerfAPI v3.11.1.
2. **GRBM GUI_ACTIVE = 2 →⁠ VALIDADO para GFX8** (línea 152 `FASE-D-ETAPA-3-EVENTS.md` y FASE M:
   `GRBM_PERFCOUNTER0_SELECT=0x2`). La constante RADV "2" queda ahora refrendada por el catálogo
   AMD GFX8 explícito (`GRBM_PERF_SEL_GUI_ACTIVE = 2`).
3. **SQ WAVES = 4 → VALIDADO para GFX8** (`SQ*_PERF_SEL_WAVES = 4` en los 8 bloques SQ). Ya no se
   trata como "no probado en GFX8".
4. **SPI_CSQ / SPI busy**: SPI `CSG_BUSY=58`, `CSN_BUSY=64` — ofrece alternativa de lectura de
   ocupación de shader por SPI (existe el registro fixed `SPI_CSQ_WF_ACTIVE_COUNT` leído en la
   Etapa 2, pero como evento programable hay ID válido).
5. **PA_SC / PA_SU**: disponibles los IDs reales para contadores de culling/primitives.

---

## 4. Restricciones de uso

- **SOLO REFERENCIA DOCUMENTAL.** Sigue **prohibido** programar contadores, escribir MMIO/sysfs o
  ejecutar experimentos que escriban en la GPU.
- La lectura del catálogo es válida (descarga a `/tmp/opencode/gpa311/`, artifact en
  `FASE-R0-EXTERNAL-KNOWLEDGE/R0-1-GFX8-EVENT-ID-REFERENCE.txt`).
- **No asumir que Polaris12 tiene presente todas las instancias catalogadas** (p.ej. TA 64
  instancias, TCC 16, Mc 32): la tabla es a nivel de familia GFX8; la unidad concreta expone las
  que tenga habilitadas por fuses (asunto de FASE polígono A→AJ del mapa P12). El **event ID es
  idéntico** lo use o no; la **instancia máxima** dependerá del ASIC.

---

## 5. Archivos de trabajo (en `/tmp/opencode/gpa311/`, referencia, NO instalados)

`gpa_hw_counter_gfx8.cc/.h`, `gpa_hw_counter_gfx8_baffin.cc/.h`, `gpa_hw_counter_gfx8_ellesmere.cc/.h`,
`gpa_hw_exposed_counters_gfx8.cc/.h`, `public_counter_names_vk_gfx8.txt`,
`public_counter_names_vk_gfx8_baffin.txt`, `public_counter_names_vk_gfx8_ellesmere.txt`,
`public_counter_definitions_gfx8.txt`, `public_counter_definitions_compute_gfx8.txt`,
`graphics_counter_tables_gfx8.rst`, `compute_counter_tables_gfx8.rst`, `gpa_counter.h`,
`gpa_counter_generator_base.cc`, `gpa_counter_generator_vk_base.cc`.

Fuente: https://github.com/GPUOpen-Tools/gpu_performance_api (tag v3.11.1). Licencia MIT.

---

## 6. Confianza

- **Alta (VERIFICADO):** presencia y contenido del catálogo AMD GFX8 (repositorio oficial del
  fabricante, tag fijo). Confirmación extra vía `gpa_tree.json` (verificado por API del árbol git
  que estos archivos existen en v3.11.1 y NO en v4.x/master).
- **Media-Alta:** equivalencia `counter_index_in_group = block_event_id = PERF_SEL` (deducida del
  código `gpa_counter_generator_base.cc` + estructura `GpaHardwareCounterDesc`; no es una
  declaración literal "event_id" en el JSON, pero es la única lectura coherente).
- No se manipula hardware; solo documenta los valores que *se escribirían* si la programación se
  autorizara en el futuro.