# DOGFOOD-008 — Reconstrucción con RXRE activo: la escritura de `VM_CONTEXT0_CNTL` (GFX8/Polaris12)

**Pregunta:** ¿Cómo se **construye** y **termina consumiendo** la escritura de
`VM_CONTEXT0_CNTL` en el camino GFX8/Polaris12?

**Cadena reconstruida:** `REGISTER → PRODUCER → TRANSFORMATION → REPRESENTATION → CONSUMER → SEMANTIC EFFECT`

**Repo:** `/home/lucas/Escritorio/rxre` (HEAD `9ce74c53`, rama `migration/validated-legacy-work`,
218 mods locales intocables, **sin ops git**). Corpus: `RESEARCH/kernelbuild/linux-7.1.3`
(36706 `.c`; subtree `drivers/gpu/drm/amd`). **Uso de `RX550-INVESTIGACION` como sustituto: PROHIBIDO** (no usado).

**Estado de cierre: `QUESTION_RESOLVED`.**

Entregables: `benchmark/dogfood-008/{trace.log, trajectory.json, metrics.json, evidence-chain.md, rxre-outputs/}`.

---

## 1. Pregunta y estado de cierre

- **Pregunta:** construcción y consumo de la escritura de `VM_CONTEXT0_CNTL` en GFX8/Polaris12.
- **Estado:** `QUESTION_RESOLVED`. La cadena completa se reconstruyó con evidencia de RXRE + fuente.
- **No se ejecutó:** ningún takeover de GPU, ninguna escritura de hardware. La consola es de la Intel
  i915 (`fb0=i915drmfb`); **frontera dura: no tocar 0000:00:02.0**. Todo el análisis es estático/read-only.

## 2. REGISTER — identidad del registro

- **Símbolo:** `mmVM_CONTEXT0_CNTL` (macro `#define`), valor **`0x504`**.
- **Unidad:** **índice de dword** → offset de byte = `0x504 × 4` = **`0x1410`** (BAR0/rmmio).
  Confirmado por `amdgpu_reg_access.c` (`writel(v, adev->rmmio + (reg * 4))`) y por el
  `unit_declaration`/`symbol_class=dword_index_de_mm` de `reg_resolve`.
- **Definición GFX8/Polaris12:** `include/asic_reg/gmc/gmc_8_1_d.h:601` (`#define mmVM_CONTEXT0_CNTL 0x504`);
  idéntico en `gmc_8_2_d.h:603`. El fichero productor `gmc_v8_0.c:35` incluye `gmc_8_1_d.h` (no `gmc_8_2_d.h`).
- **IP block:** **GMC** (Graphics Memory Controller). En GFX8 el controlador de VM está en el GMC;
  MMHUB es un bloque separado solo desde GFX9+ (los `mmhub_*_offset.h` con `0x06c0` son GFX9+).
- **Ambigüedad de generación (registrada):** `reg_resolve --resolve mmVM_CONTEXT0_CNTL` →
  `definition_count=11, chosen=None, candidates=[]`. El resolver **encuentra** las 11 definiciones
  (GMC gmc_6_0/7_0/7_1/8_1/8_2; MMHUB mmhub_1_0/9_1/9_3_0; GC gc_9_0/9_1/9_2_1) pero **no elige**
  la aplicable al ASIC. La identidad del registro es **robusta** porque `0x504` es igual en gmc_8_1 y gmc_8_2.
  → `RXRE_CORRECTNESS_GAP-2` (observado, **no reparado** por regla DOGFOOD-008).

## 3. PRODUCER — todos los productores (no solo el primero)

`mmVM_CONTEXT0_CNTL` se escribe en **tres** puntos de `gmc_v8_0.c` (enumerados, no tomados arbitrariamente):

| # | Productor | Línea | Qué hace |
|---|---|---|---|
| P1 | `gmc_v8_0_gart_enable` | 893-897 | **Constructor principal**: read-modify-write que habilita el contexto VM0 |
| P2 | `gmc_v8_0_gart_disable` | 977 | `WREG32(mmVM_CONTEXT0_CNTL, 0)` — deshabilita (escribe 0) |
| P3 | `gmc_v8_0_vm_fault_interrupt_state` | 1402-1408 | read-modify-write de los 7 bits `*_INTERRUPT` (IRQ de fault) |

**Caller upstream del productor principal (P1):**
```
amdgpu_device_init (amdgpu_device.c)
  → ip_blocks[i].version->funcs->hw_init(&adev->ip_blocks[i])   [amdgpu_device.c:2132/2159/2199/...]
    → gmc_v8_0_ip_funcs.hw_init   [fn-ptr, gmc_v8_0.c:1718]
      → gmc_v8_0_hw_init(ip_block)   [gmc_v8_0.c:1203]
        → [if adev->asic_type == CHIP_POLARIS12] gmc_v8_0_polaris_mc_load_microcode   [gmc_v8_0.c:1220-1222]
        → gmc_v8_0_gart_enable(adev)   [gmc_v8_0.c:1228]  ← PRODUCTOR
```
La rama `CHIP_POLARIS12` en L1220-1222 ancla la cadena al target.

## 4. TRANSFORMATION — cómo se construye el valor

`gmc_v8_0.c:892-897` — **read-modify-write** con `REG_SET_FIELD` (no constante directa):
```c
WREG32(mmVM_CONTEXT0_CNTL2, 0);                          /* L892 */
tmp = RREG32(mmVM_CONTEXT0_CNTL);                         /* L893: lee actual */
tmp = REG_SET_FIELD(tmp, VM_CONTEXT0_CNTL, ENABLE_CONTEXT, 1);                       /* L894: bit 0  */
tmp = REG_SET_FIELD(tmp, VM_CONTEXT0_CNTL, PAGE_TABLE_DEPTH, 0);                      /* L895: bits 1-2 */
tmp = REG_SET_FIELD(tmp, VM_CONTEXT0_CNTL, RANGE_PROTECTION_FAULT_ENABLE_DEFAULT, 1); /* L896: bit 4  */
WREG32(mmVM_CONTEXT0_CNTL, tmp);                          /* L897 */
```
- Bits tocados: `0x1 | 0x10` = `0x11`, con `PAGE_TABLE_DEPTH` (mask `0x6`) explícitamente a 0; resto preservado.
- **Contexto previo (L886-891):** programa la page table del contexto VM0 (start/end/base/fault-addr, todo `>> 12` = a páginas de 4 KiB).
- **Semántica de campos** (`gmc_8_1_sh_mask.h:6581-6620`, idéntico en `gmc_8_2_sh_mask.h`):
  `ENABLE_CONTEXT` bit0 (mask `0x1`), `PAGE_TABLE_DEPTH` bits1-2 (mask `0x6`),
  `RANGE_PROTECTION_FAULT_ENABLE_DEFAULT` **bit4** (mask `0x10`).
  **Corrección registrada:** RANGE_PROTECTION_FAULT_ENABLE_DEFAULT es **bit 4**, no bit 10 (bit 10 = PDE0).

## 5. REPRESENTATION — mecanismo concreto de escritura

```
WREG32(reg, v)                                    amdgpu.h:1295
  → amdgpu_device_wreg(adev, reg, v, 0)           amdgpu_reg_access.c
      if (reg*4 < adev->rmmio_size):
          if SR-IOV VF:  amdgpu_kiq_wreg(adev, reg, v, 0)   [PM4 vía KIQ]
          else (bare metal): writel(v, adev->rmmio + reg*4)  [MMIO BAR0]  ← ESTA PC
      else: amdgpu_reg_pcie_wr32(adev, reg*4, v)
  + tracepoint trace_amdgpu_device_wreg(pdev->device, reg, v)
```
- **Esta PC (RX550 física, bare metal):** `writel(tmp, adev->rmmio + 0x1410)` — escritura MMIO a **BAR0**, offset byte **0x1410**.
- Observabilidad: tracepoint `trace_amdgpu_device_wreg`.

## 6. CONSUMER — quién consume la escritura

| Consumidor | Tipo | Evidencia |
|---|---|---|
| **Unidad VM/MMU del GMC** (contexto 0) | hardware | usa VM_CONTEXT0_CNTL para habilitar el contexto y traducir direcciones GPU-virtuales contra la GART page table. **No observable por RXRE** (solo software); inferido de la semántica de campos + función del IP block → `DERIVATION` |
| `gmc_v8_0_vm_fault_interrupt_state` (L1385) | software (2º productor/lector) | lee y reescribe `mmVM_CONTEXT0_CNTL`: `bits` = OR de 7 masks `*_INTERRUPT` (bits 3,6,9,12,15,18,21 → `0x249248`); `DISABLE: tmp &= ~bits`; `ENABLE: tmp |= bits` |
| `gmc_v8_0_gart_disable` (L977) | software | `WREG32(mmVM_CONTEXT0_CNTL, 0)` — invierte el efecto del productor |

**Relación producer↔consumer:** el consumidor (P3) **preserva** los bits que el productor (P1) fijó
(ENABLE_CONTEXT, PAGE_TABLE_DEPTH, RANGE_PROTECTION_FAULT_ENABLE_DEFAULT) y solo altera los 7 bits
`*_INTERRUPT`. Hay una **dependencia de datos real** productor→consumidor.

## 7. BIDIRECTIONAL_RELATION

**`BIDIRECTIONAL_RELATION = PARTIAL`.**
- **productor → consumidor (flujo de datos): PASS.** El consumidor lee `mmVM_CONTEXT0_CNTL` y preserva los bits del productor.
- **consumidor → productor (flujo de datos): FAIL.** El productor lee el registro a `t=init` (valor de reset, L893) **antes** de que el consumidor ejecute; ningún dato fluye en sentido inverso.
- **productor ↔ consumidor (grafo de llamadas): FAIL en ambos sentidos.** No hay arista de llamada entre `gmc_v8_0_gart_enable` y `gmc_v8_0_vm_fault_interrupt_state`; son invocados desde fases distintas del init (device-init vs IRQ-setup). La relación es **solo a través del registro compartido**.
- **Verdicto:** bidireccional sobre el **registro compartido** (ambos lo acceden), unidireccional en **flujo de datos** (productor→consumidor), ausente en el **grafo de llamadas**.
- Nota: `relations.py`/`claims.py` operan sobre la DB de findings numerados, no sobre símbolos de fuente; no hay finding previo sobre `VM_CONTEXT0_CNTL` (grep `findings/` vacío), así que la bidireccionalidad se prueba sobre la cadena de fuente reconstruida.

## 8. Contexto GFX8/Polaris12

- ASIC: **Polaris12** = `CHIP_POLARIS12 = 17` (`include/drm/amd_asic_type.h:49`), GFX8 (gfx 8_0_2).
- IP block del registro: **GMC v8_0** (`gmc_v8_0.c`), no MMHUB (MMHUB es GFX9+).
- Rama específica del target: `gmc_v8_0.c:1220-1222` (`asic_type == CHIP_POLARIS12` → `gmc_v8_0_polaris_mc_load_microcode`).
- La definición del registro (`0x504`) y los bitfields son **estables** entre gmc_8_1 (Polaris11) y gmc_8_2 (Polaris12).

## 9. Evidencia por claim (claim · fuente · línea · operación RXRE · provenance · estado)

| Claim | Fuente:línea | Operación RXRE | Provenance | Estado |
|---|---|---|---|---|
| R1: `mmVM_CONTEXT0_CNTL`=0x504, índice dword | gmc_8_1_d.h:601 | reg_resolve (dword_index_de_mm) + evidence_search | corpus linux-7.1.3 | **FACT** |
| R2: 11 definiciones, resolver no elige | reg_resolve output | reg_resolve --resolve mmVM_CONTEXT0_CNTL | rxre-outputs/reg_resolve-mmVM_CONTEXT0_CNTL.json | **FACT** (gap) |
| R3: gmc_v8_0.c incluye gmc_8_1_d.h | gmc_v8_0.c:35 | evidence_search (agrupación) + shell S7 | corpus | **FACT** |
| P1: productor = gmc_v8_0_gart_enable | gmc_v8_0.c:829,893-897 | trace_path --from + shell S2/S3 | rxre-outputs/trace_path-from-gmc_v8_0_gart_enable.json | **FACT** |
| P2/P3: otros dos escritores | gmc_v8_0.c:977,1402-1408 | evidence_search + shell S2/S13 | corpus | **FACT** |
| P3-caller: cadena upstream | gmc_v8_0.c:1228,1718; amdgpu_device.c | shell S9/S10/S11 (recupera timeout trace_path) | corpus | **FACT** |
| T1: construcción por REG_SET_FIELD RMW | gmc_v8_0.c:892-897 | shell S2/S3 | corpus | **FACT** |
| T2: semántica de campos | gmc_8_1_sh_mask.h:6581-6620 | shell S14/S16 | corpus | **FACT** |
| W1/W2: WREG32→amdgpu_device_wreg→writel(rmmio+reg*4) | amdgpu.h:1295; amdgpu_reg_access.c | shell S4/S5/S6 | corpus | **FACT** |
| C1: consumidor HW = unidad VM/MMU | (semántica de campos) | derivación de T2 + función IP block | — | **DERIVATION** |
| C2: consumidor SW = vm_fault_interrupt_state | gmc_v8_0.c:1385-1420 | shell S13 | corpus | **FACT** |
| E1: efecto (contexto habilitado, tabla 1 nivel, fault rango) | (semántica de campos) | derivación de T2 | — | **DERIVATION** |
| B1: BIDIRECTIONAL_RELATION=PARTIAL | cadena reconstruida | análisis de la cadena | evidence-chain.md §7 | **DERIVATION** |

## 10. Uso de RXRE (capacidades e invocaciones)

- **Capacidades usadas (5):** register (`reg_resolve.py`), search (`evidence_search.py`),
  trace (`trace_path.py`), relations (`relations.py`), claims (`claims.py`).
- **Invocaciones RXRE: 17** (13 exploración + 4 re-captura de artefactos).
  - register=3, search=2, trace=4, relations=2, claims=2.
- **Artefactos crudos** en `benchmark/dogfood-008/rxre-outputs/`:
  `reg_resolve-VM_CONTEXT0_CNTL.json`, `reg_resolve-mmVM_CONTEXT0_CNTL.json`,
  `evidence_search-VM_CONTEXT0_CNTL.json`, `evidence_search-mmVM_CONTEXT0_CNTL.json`,
  `trace_path-from-gmc_v8_0_gart_enable.json`.

## 11. Gaps y limitaciones de RXRE (observados, NO reparados)

| ID | Herramienta | Síntoma | Clasificación |
|---|---|---|---|
| RXRE_CORRECTNESS_GAP-1 | reg_resolve | `--resolve VM_CONTEXT0_CNTL` (sin `mm`) → 0 defs, `constant_maybe` | corrección: no prueba prefijo `mm` |
| RXRE_CORRECTNESS_GAP-2 | reg_resolve | `--resolve mmVM_CONTEXT0_CNTL` → 11 defs, `chosen=None` | corrección: no elige generación/ASIC |
| RXRE_CAPABILITY_GAP-3 | trace_path | `--callers-of` → timeout 120000ms | capacidad: consulta inversa no termina |
| RXRE_LIMITATION-4 | trace_path | `--from` resuelve símbolos genéricos (`dev_err`,`memset`) a ubicaciones arbitrarias | limitación: coincidencia textual, sin desambiguar macro/fn-ptr (selftest: "veredicto por rama declarada, NO prueba ejecución real") |

## 12. Clasificación del shell manual

- **Shell manual total: 18** llamadas.
- **AUXILIARY_SHELL: 16** — leer/parsear fuente (RXRE localiza símbolos; la IA interpreta la
  transformación/semántica, que no forma parte del contrato de RXRE). Ej: cuerpos de funciones,
  bitfields, `#include`, macros `WREG32`.
- **RXRE_CAPABILITY_GAP: 1** — S9 (grep de callers), porque `trace_path --callers-of` (la capacidad
  RXRE correspondiente) hizo timeout. Recuperación de una capacidad que RXRE debería proporcionar.
- **Captura (C4):** 1 cp de un artefacto ya generado.

## 13. GLOBAL WORK SCAN (registrar, NO ejecutar)

Categorías con trabajo técnico elegible **identificado** (no ejecutado, por regla DOGFOOD-008):

1. **[03] CLAIMS críticos abiertos:** `C1` (consumidor HW = unidad VM/MMU) y `E1` (efecto final) son
   `DERIVATION`, no observación de hardware. Para cerrarlos como `FACT` haría falta **observación de
   hardware** (readback de `VM_CONTEXT0_CNTL` tras la escritura, o traza `trace_amdgpu_device_wreg`).
   **Bloqueado** por la frontera dura (no tocar la Intel/consola; takeover de RX550 no autorizado en esta tarea).
2. **[09] TOOL gaps:** `reg_resolve` (sin prefijo `mm`; sin elección de generación) y `trace_path`
   (`--callers-of` timeout; resolución textual imprecisa). **No reparados** (regla DOGFOOD-008);
   registrados para el propietario.
3. **[12] REPRODUCIBILITY gaps:** la cadena es reproducible desde el corpus + RXRE (artefactos en
   `rxre-outputs/`), pero la elección de generación (gmc_8_1 vs gmc_8_2) es una decisión manual
   (S7/S8) que `reg_resolve` no automatiza.
4. **[18] OPTIMIZACIONES:** ninguna (regla DOGFOOD-008: no optimizar, no reparar).
5. **[20] USER IDEAS:** ninguna nueva en esta sesión.

**Cierre:** `QUESTION_RESOLVED`. La cadena REGISTER→PRODUCER→TRANSFORMATION→REPRESENTATION→CONSUMER→
SEMANTIC EFFECT quedó reconstruida con evidencia; los dos puntos `DERIVATION` (consumidor HW y efecto)
quedan registrados como abiertos, bloqueados por la frontera de hardware (no takeover en esta tarea).

---

### Métricas (resumen)

```
RXRE_INVOCATIONS=17  FAILED_RXRE_CALLS=3  RECOVERY_CALLS=2  REPEATED_CALLS=4  MANUAL_SHELL_CALLS=18
SEARCH=2  REGISTER=3  RELATION=2  CLAIM=2  TRACE=4
BIDIRECTIONAL_RELATION=PARTIAL   Estado=QUESTION_RESOLVED
```
