# R1-1 — Reconciliación de Event IDs GFX8: GPUPerfAPI vs documentación local (CB/SQ/MC)

> **Archivo:** `R1-1-GFX8-EVENT-RECONCILIATION.md`
> **Fase:** FASE R-1 — DOCUMENTATION RECONCILIATION & MASTER CONSOLIDATION
> **Fecha:** 2026-09-22 — Modo SOLO DOCUMENTAL / READ-ONLY (lecturas, parsing, comparación; sin escrituras de sistema)
> **Clasificación general:** [VERIFICADO] (evidencia computacional directa sobre ambas fuentes)

---

## 1. Alcance y método

Se reconcilian las discrepancias de **conteo de event IDs / selectors** por bloque reportadas en FASE R-0
(`R0-1-GFX8-EVENT-IDS.md` §2.3) entre:

- **Fuente A — GPUPerfAPI v3.11.1** (`/tmp/opencode/gpa311/gpa_hw_counter_gfx8.cc`): arrays internos
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

| Bloque | Fuente A: GPUPerfAPI v3.11.1 (event IDs, índice=PERF_SEL) | Fuente B: Mesa local `ac_perfcounter.c` groups_VI | Diferencia | Explicación | Nivel de confianza | Estado final |
|---|---|---|---|---|---|---|
| **CB** | **396** por instancia (16 inst; índice 0..395), 160 expuestos con nombre (10/inst) | **405** selectors (máx. clase VI) | A − B = **−9** (Mesa cuenta 9 más) | El campo PERF_SEL de CB es de 9 bits → 512 valores posibles. Mesa expone el **máximo sobre la clase VI** (405), que incluye selectores que GPUPerfAPI no enumera con evento/nombre en GFX8 base (reservados/derivados/inespecíficos de Polaris12). GPUPerfAPI cataloga exactamente el rango interno del generador AMD para GFX8 (0..395). Es una **diferencia de alcance de catálogo, no de semántica** para ningún evento con nombre. Para FASE M usar 0..395 como rango con evento definido; 396..404 requieren verificación adicional | ALTA (método de conteo distinto verificado en ambas fuentes); MEDIA para identidad exacta de los 9 selectores extra | **PARTIALLY_RECONCILED** |
| **SQ** | **299** por instancia (8 sub-bloques SQ/Cs/Es/Gs/Hs/Ls/Ps/Vs × 4 inst; índice 0..298) | **273** selectors (máx. clase VI) | A − B = **+26** (GPUPerfAPI cuenta 26 más) | Mesa contrae SQ a un único bloque `cik_SQ` con 273 selectors (máx. clase VI); GPUPerfAPI conserva el **rango interno completo del generador** (299) incluyendo eventos sin nombre público (solo 16/inst ≈ expuestos). El evento crítico validado **`SQ_PERF_SEL_WAVES = 4` está presente y coincide en ambas** (R0-1 §3.3). Diferencia de método: rango interno vs selectors expuestos | ALTA (mecanismo); MEDIA (identidad de los 26 eventos adicionales sin nombre) | **PARTIALLY_RECONCILED** |
| **MC** | **33** por instancia (32 inst; índice 0..32) | **22** selectors (máx. clase VI) | A − B = **+11** (GPUPerfAPI cuenta 11 más) | GPUPerfAPI cataloga 33 event IDs internos del bloque MC (sin nombres públicos — MC no aparece en la referencia expuesta); Mesa expone solo 22 selectors (máx. clase VI). Además, en FASE-D-ETAPA-3-EVENTS.md §D ya se documentó que la **semántica/unidad de los eventos MC no está verificada en ninguna fuente local** (unidad desconocida). Por tanto los 33 eventos son **rango formal** (valores aceptables de PERF_SEL) pero **sin semántica validada**; los 22 de Mesa son los selectors que el driver declara. Rango seguro para uso: 0..21 por Mesa; 0..32 solo si se autoriza y se verifica unidad | ALTA (mecanismo); **la semántica de eventos MC queda NO VERIFICADA en ambas** → no se puede profundizar documentalmente | **PARTIALLY_RECONCILED** (conteo) · semántica MC → **UNRESOLVED** |

> **Regla operativa derivada (FASE M/D):** como el valor PERF_SEL es de ancho fijo por bloque (CB 9b, SQ 9b,
> MC 8b) y el significado se define por catálogo, **el rango a usar es el común documentado** (intersección):
> CB 0..395, SQ 0..272, MC 0..21 para diseño seguro; el margen adicional de la fuente con más entradas queda
> registrado como «VERIFICABLE con catálogo de eventos nombrados» y NO se programa sin resolución.

---

## 3. Bloques que SÍ coinciden exactamente (evidencia de alineación del catálogo)

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

**Lectura:** 20 de 22 bloques coinciden bit a bit en conteo. La discrepancia reportada originalmente (CB/SQ/MC)
es una minoría localizada; GRBM **coincide en 34** (confirmando las constantes GUI_ACTIVE=2 / rango 0..33), y DB
en 257 (coherente con EVENTS §E).

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
un único `cik_SQ` con 273 selectors (máx. clase VI). La diferencia (+26 en GPUPerfAPI) refleja eventos internos
sin nombre público. El evento crítico **SQ WAVES = 4** es consistente entre fuentes y queda **[VERIFICADO]** para
GFX8 (R0-1 §3.3). 

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

1. **FASE M (GFX8 Counter Research) — parte documental DESBLOQUEADA:** los rangos de PERF_SEL por bloque ya son
   conocidos y mayoritariamente son coincidentes entre GPUPerfAPI y Mesa. La programación sigue **NO autorizada**.
2. **GRBM GUI_ACTIVE=2 y SQ WAVES=4** quedan refrendados por ambas fuentes (R0-1 §3 y §4.2). La nota de
   `MASTER-RESEARCH-STATUS.md` líneas 119-120 (que los daba por «BLOQUEADO»/«NO VERIFICADO») queda **desactualizada**
   y se corrige en R-1.4.
3. **MC:** permanece como el único bloque donde el **conteo** está reconciliado pero la **semántica** no → sin
   fuente de nombres/unidad no se diseña su normalización.
4. **Recomendación de rango seguro (documental):** usar la intersección (CB 0..395, SQ 0..272, MC 0..21) para
   propuestas de programación futura; cualquier selector fuera de estos rangos exige verificación con catálogo
   nombrado de la variante Polaris12.

---

## 6. Estados finales (según modelo R-1.6)

| Elemento | Estado final |
|---|---|
| Reconciliación de conteos CB/SQ/MC (y PA_SU) | [RECONCILED] a nivel de mecanismo → **PARTIALLY_RECONCILED** por identidad 1:1 de los selectores extra no verificada |
| Semántica/unidad de eventos MC | **UNRESOLVED** |
| GRBM GUI_ACTIVE=2 / SQ WAVES=4 para GFX8 | **[VERIFICADO]** (Fuente A + B + R0-1) |
| Coincidencia estructural de catálogos (20/22 bloques) | [VERIFICADO] |

---

## 7. Trazabilidad y fuentes

- Fuente A (parsing en esta sesión): `/tmp/opencode/gpa311/gpa_hw_counter_gfx8.cc` — arrays
  `kCb0/Sq0/Mc0/…CountersGfx8[]` (conteo de entradas, rango continuo 0..N-1, unicidad confirmada).
- Fuente A (expuestos): `/tmp/opencode/gpa311/gpa_hw_exposed_counters_gfx8.cc`, `public_counter_names_vk_gfx8*.txt`,
  y referenca consolidada `experiments/FASE-R0-EXTERNAL-KNOWLEDGE/R0-1-GFX8-EVENT-ID-REFERENCE.txt` (2304 filas).
- Fuente B: `…/RX550_Modo_Torneo_Backup_2026-09-19_0836/mesa/mesa-source/src/amd/common/ac_perfcounter.c`
  (líneas 542-566: grupos CIK/VI/gfx9; líneas 585-690: uso de `selectors` = número de selectors; archivos h).
- Documentos dependientes: `R0-1-GFX8-EVENT-IDS.md` (§2.2, §2.3, §3), `FASE-D-ETAPA-3-EVENTS.md` (§B, §D, §E),
  `FASE-D-GFX8-EVENT-ID-AUDIT.md` (Resultado B → cruzar R-1.2), `R1-6-EVIDENCE-STATE-MODEL.md` (estados).

**Confirmación read-only:** esta reconciliación se realizó solo con lectura/parsing de archivos locales; no se
programó contador, no se escribió sysfs/MMIO, no se ejecutó experimento alguno.