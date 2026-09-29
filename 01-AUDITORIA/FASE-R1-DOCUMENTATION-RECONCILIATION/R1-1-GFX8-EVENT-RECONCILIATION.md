# R1-1 — Reconciliación de Event IDs GFX8: GPUPerfAPI vs documentación local (CB/SQ/MC)

> **Archivo:** `R1-1-GFX8-EVENT-RECONCILIATION.md`
> **Fase:** FASE R-1 — DOCUMENTATION RECONCILIATION & MASTER CONSOLIDATION
> **Fecha:** 2026-09-22 — Modo SOLO DOCUMENTAL / READ-ONLY (lecturas, parsing, comparación; sin escrituras de sistema)
> **Clasificación general:** [PARTIALLY_RECONCILED] (evidencia computacional directa sobre
> catálogos; no valida ASIC/runtime)
>
> **RECONCILIACIÓN 2026-09-24:** la fuente `/tmp/opencode/gpa311/` está perdida; la
> comparación inicial no es reproducible independientemente. `v3.11.1` queda como
> extracción histórica y `v3.17` como referencia operativa de catálogo. La intersección
> CB/SQ/MC es un rango de índices, no un rango semánticamente seguro. GRBM=2 y SQ=4 son
> entradas de catálogo, no validación para `1002:699f`. La reconciliación aritmética
> vigente es **19 coincidencias y 4 discrepancias sobre 23 comparaciones**; la formulación
> `20/22` es incorrecta.

---

## 1. Alcance y método

Se reconcilian las discrepancias de **conteo de event IDs / selectors** por bloque reportadas en FASE R-0
(`R0-1-GFX8-EVENT-IDS.md` §2.3) entre:

- **Fuente A — GPUPerfAPI v3.11.1** (`/tmp/opencode/gpa311/gpa_hw_counter_gfx8.cc` — árbol fuente **PERDIDO / NO VERIFICABLE**; recuperación parcial: véase `05-FUENTES-EXTERNAS/FASE-R0-EXTERNAL-KNOWLEDGE/R0-1-GFX8-EVENT-ID-REFERENCE.txt`): arrays internos
  `k<Block>CountersGfx8[]` por instancia; cada entrada = `counter_index_in_group` = `block_event_id` = valor a
  escribir en PERF_SEL. El **rango de índices es continuo 0..N-1** por bloque (verificado por parsing en esta sesión).
- **Fuente B — Mesa local** (`…/mesa-source/src/amd/common/ac_perfcounter.c`): `groups_VI[]`, tabla de
  `selectors`/`instances` por bloque para la clase VI (GFX8). Semántica del campo `selectors`
  (según el propio comentario del código, líneas 542-548): *«…we simply expose the **maximum** number over all
  chips in a class»* → es el **máximo de selectores sobre todos los chips de la clase VI**, NO el rango exacto
  de un ASIC concreto.

**Método de verificación usado aquí:** parsing con Python de `gpa_hw_counter_gfx8.cc` y lectura directa de
`ac_perfcounter.c` (fuentes primarias en disco, read-only). Los arrays GPUPerfAPI se contaron entrada por entrada
y se comprobó que `índice_min=0`, `índice_max=N-1`, `n = N`, todos únicos.

**Resultado de fondo (importante):** **la mayoría de bloques coinciden EXACTAMENTE** entre ambas fuentes
(ver §3). Solo CB, SQ y MC difieren (y se descubre PA_SU con diferencia menor, §4.4). Esto descarta un error
sistemático de una de las fuentes: la estructura general del catálogo es la misma (AMD derivó ambas de la misma
plas de datos), y las diferencias son locales y explicables.

---

## 2. Tabla de reconciliación principal (CB / SQ / MC)

| Bloque | Fuente A: GPUPerfAPI v3.17/v3.11.1 (catálogo, índice=PERF_SEL) | Fuente B: Mesa local `ac_perfcounter.c` groups_VI | Diferencia | Explicación | Nivel de confianza | Estado final |
|---|---|---|---|---|---|---|
| **CB** | **396** por instancia (16 inst; índice 0..395), 160 expuestos con nombre (10/inst) | **405** selectors (máx. clase VI) | A − B = **−9** (Mesa cuenta 9 más) | GPUPerfAPI cataloga un rango interno GFX8; Mesa expone una clase VI más amplia. Es una **diferencia de alcance de catálogo**, no una garantía semántica. `0..395` es un índice de catálogo; cualquier evento requiere tupla y verificación ASIC. | ALTA (método de conteo); MEDIA para identidad extra | **PARTIALLY_RECONCILED** |
| **SQ** | **299** por instancia (8 sub-bloques SQ/Cs/Es/Gs/Hs/Ls/Ps/Vs × 4 inst; índice 0..298) | **273** selectors (máx. clase VI) | A − B = **+26** (GPUPerfAPI cuenta 26 más) | Mesa contrae SQ a un bloque `cik_SQ`; GPUPerfAPI conserva un rango interno con entradas sin nombre público. `SQ_PERF_SEL_WAVES=4` queda como entrada de catálogo, no como validación ASIC. | ALTA (mecanismo); MEDIA para extras | **PARTIALLY_RECONCILED** |
| **MC** | **33** por instancia (32 inst; índice 0..32) | **22** selectors (máx. clase VI) | A − B = **+11** (GPUPerfAPI cuenta 11 más) | GPUPerfAPI cataloga 33 índices internos sin nombres públicos suficientes; Mesa expone 22 selectores. Semántica/unidad MC no está verificada. **No existe rango seguro de uso**; 0..21 y 0..32 son solo conteos/índices de catálogo. | ALTA (conteo); semántica `UNKNOWN` | **PARTIALLY_RECONCILED** · semántica MC **UNRESOLVED** |

> **Regla reconciliada:** los rangos `0..N-1` y sus intersecciones describen índices de
> catálogo, no eventos semánticamente seguros. Cada selector requiere una tupla
> (bloque, instancia, nombre canónico, backend/API, ASIC/family, generación) y una
> verificación de aplicabilidad. No se programa ningún selector por inferencia de rango.

---

## 3. Bloques que coinciden exactamente como entradas de catálogo

Verificación por parsing de `gpa_hw_counter_gfx8.cc` vs `ac_perfcounter.c` groups_VI:

| Bloque | GPUPerfAPI (índices) | Mesa groups_VI (selectors) | ¿Coincide? |
|---|---|---|---|
| GRBM | 34 (0..33) | 34 | **SÍ** |
| GRBMSE | 15 (0..14) | 15 | **SÍ** |
| DB | 257 (0..256) | 257 | **SÍ** |
| SPI | 197 (0..196) | 197 | **SÍ** |
| SX | 34 (0..33) | 34 | **SÍ** |
| VGT | 147 (0..146) | 147 | **SÍ** |
| IA | 24 (0..23) | 24 | **SÍ** |
| WD | 37 (0..36) | 37 | **SÍ** |
| CPG | 48 (0..47) | 48 | **SÍ** |
| CPC | 24 (0..23) | 24 | **SÍ** |
| CPF | 19 (0..18) | 19 | **SÍ** |
| SRBM | 27 (0..26) | 27 | **SÍ** |
| GDS | 121 (0..120) | 121 | **SÍ** |
| TCC | 192 (0..191) | 192 | **SÍ** |
| TCA | 35 (0..34), 2 inst | 35, 2 inst | **SÍ** |
| TA | 119 (0..118) | 119 | **SÍ** |
| TD | 55 (0..54) | 55 | **SÍ** |
| TCP | 180 (0..179) | 180 | **SÍ** |
| PA_SC | 397 (0..396) | 397 | **SÍ** |
| PA_SU | **153** (0..152) | **154** | **NO** (diferencia menor, §4.4) |

**Lectura:** 19 de 23 comparaciones coinciden exactamente; 4 discrepancias (CB, SQ, MC, PA_SU).
La formulación `20/22` queda corregida. GRBM=2 y SQ=4 son entradas de catálogo; no prueban
aplicabilidad al ASIC ni seguridad de programación.

---

## 4. Análisis por bloque discrepante

### 4.1 CB — 396 vs 405
Mesa declara `{&cik_CB, 405}` en `groups_VI`. El campo PERF_SEL de CB es 9 bits (`PERF_SEL[0:8]`), que admite
hasta 512 valores; por tanto 405 es un subconjunto del rango binario y 396 también. La diferencia de +9 en Mesa
se explica por el máximo-sobre-clase-VI (comentario del código) y porque GPUPerfAPI genera el rango interno del
bloque con eventos definidos. **No hay contradicción funcional:** ningún evento con nombre existente en GPUPerfAPI
es negado por Mesa. R0-1 §2.3 ya lo señaló como «métodos de conteo distintos»; aquí se confirma con las fuentes.

### 4.2 SQ — 299 vs 273
GPUPerfAPI tiene 8 arrays SQ (Sq + Cs/Es/Gs/Hs/Ls/Ps/Vs), cada uno con 299 índices (0..298). Mesa agrupa SQ en
un único `cik_SQ` con 273 selectors (máx. clase VI). La diferencia (+26 en GPUPerfAPI) refleja
entradas internas sin nombre público. `SQ WAVES = 4` queda como entrada de catálogo
coincidente, no como validación para `1002:699f`.

### 4.3 MC — 33 vs 22
GPUPerfAPI `Mc0` = 33 índices (0..32) con **32 instancias**. Mesa `cik_MC` = 22 selectors. La ligazón es débil en
ambas: sin nombres públicos MC (no aparece en la referencia expuesta de 2304 filas) y con la semántica/unidad
documentada como **NO VERIFICADA** en `FASE-D-ETAPA-3-EVENTS.md` §D. Mensaje para FASE M: **no diseñar
normalización de MC (bytes/bandwidth) hasta obtener una fuente con nombres y unidad de eventos MC.**

### 4.4 PA_SU — 153 vs 154 (hallazgo adicional, menor)
`groups_VI` declara `{&cik_PA_SU, 154}` mientras GPUPerfAPI `PaSu0` = 153 (0..152). Difiere en **1** selector.
Mismo mecanismo que CB (máx. clase VI vs rango interno). Estado: **PARTIALLY_RECONCILED** (diferencia menor,
sin impacto en los eventos usados: `PA_SU0_PERF_PAPC_PA_INPUT_PRIM=8`, `_CLPR_CULL_PRIM=14` están dentro del rango
común).

---

## 5. Implicaciones para FASE M y FASE D

1. **FASE M (GFX8 Counter Research) — reconciliación estructural parcial:** los conteos de catálogo
   pueden documentarse, pero la fuente temporal principal está perdida y la aplicabilidad al ASIC
   no está demostrada. La programación sigue **NO autorizada**.
2. **GRBM GUI_ACTIVE=2 y SQ WAVES=4** quedan como entradas de catálogo coincidentes, no como
   eventos validados para `1002:699f`.
3. **MC:** el conteo no resuelve semántica/unidad; no se diseña normalización de bandwidth.
4. **No existe rango semánticamente seguro:** no se usan intersecciones como autorización de
   programación. Cada selector requiere nombre, backend/API, ASIC/family y generación.

---

## 6. Estados finales (según modelo R-1.6)

| Elemento | Estado final |
|---|---|
| Reconciliación de conteos CB/SQ/MC (y PA_SU) | **PARTIALLY_RECONCILED**; identidad 1:1 de selectores extra no verificada |
| Semántica/unidad de eventos MC | **UNRESOLVED** |
| GRBM GUI_ACTIVE=2 / SQ WAVES=4 para GFX8 | **PARTIALLY_RECONCILED / CATALOG ONLY**; no validado para `1002:699f` |
| Coincidencia estructural de catálogos (19/23 comparaciones) | **PARTIALLY_RECONCILED** |

---

## 7. Trazabilidad y fuentes

- Fuente A (parsing en esta sesión): `/tmp/opencode/gpa311/gpa_hw_counter_gfx8.cc` (**PERDIDO / NO VERIFICABLE**) — arrays
  `kCb0/Sq0/Mc0/…CountersGfx8[]` (conteo de entradas, rango continuo 0..N-1, unicidad confirmada).
- Fuente A (expuestos): `/tmp/opencode/gpa311/gpa_hw_exposed_counters_gfx8.cc` (**PERDIDO / NO VERIFICABLE**), `public_counter_names_vk_gfx8*.txt`,
  y referenca consolidada `05-FUENTES-EXTERNAS/FASE-R0-EXTERNAL-KNOWLEDGE/R0-1-GFX8-EVENT-ID-REFERENCE.txt` (2304 filas).
- Fuente B: `…/RX550_Modo_Torneo_Backup_2026-09-19_0836/mesa/mesa-source/src/amd/common/ac_perfcounter.c`
  (líneas 542-566: grupos CIK/VI/gfx9; líneas 585-690: uso de `selectors` = número de selectors; archivos h).
- Documentos dependientes: `R0-1-GFX8-EVENT-IDS.md` (§2.2, §2.3, §3), `FASE-D-ETAPA-3-EVENTS.md` (§B, §D, §E),
  `FASE-D-GFX8-EVENT-ID-AUDIT.md` (Resultado B → cruzar R-1.2), `R1-6-EVIDENCE-STATE-MODEL.md` (estados).

**Confirmación read-only:** esta reconciliación se realizó solo con lectura/parsing de archivos locales; no se
programó contador, no se escribió sysfs/MMIO, no se ejecutó experimento alguno.
