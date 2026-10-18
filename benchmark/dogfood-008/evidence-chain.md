# DOGFOOD-008 — Cadena de evidencia: escritura de VM_CONTEXT0_CNTL (GFX8/Polaris12)

Pregunta: ¿Cómo se **construye** y **termina consumiendo** la escritura de `VM_CONTEXT0_CNTL`
en el camino GFX8/Polaris12?

Cadena reconstruida:
```
REGISTER -> PRODUCER -> TRANSFORMATION -> REPRESENTATION -> CONSUMER -> SEMANTIC EFFECT
```

Metodología: RXRE activo (`tools/reg_resolve.py`, `tools/evidence_search.py`,
`tools/trace_path.py`, `tools/relations.py`, `tools/claims.py`) sobre el corpus
`RESEARCH/kernelbuild/linux-7.1.3`. Shell manual solo para leer/interpretar fuente
(clasificado `AUXILIARY_SHELL`) o para recuperar capacidades RXRE fallidas
(`RXRE_CAPABILITY_GAP`). Ver `trace.log` y `metrics.json`.

Estado de cierre: **QUESTION_RESOLVED**.

---

## 0. TARGET (verificado)

| Campo | Valor | Evidencia |
|---|---|---|
| ASIC | Polaris12 (RX 550) | `include/drm/amd_asic_type.h:49` `CHIP_POLARIS12 = 17` |
| Generación GFX | GFX8 (gfx 8_0_2) | IP block GMC v8_0 (`gmc_v8_0.c`) |
| IP block del registro | **GMC** (Graphics Memory Controller) | `gmc_v8_0.c` incluye `gmc_8_1_d.h` |
| NOTA | En GFX8 el controlador de VM está en el GMC; MMHUB es un bloque separado solo desde GFX9+ | `mmhub_*_offset.h` son GFX9+ |

---

## 1. REGISTER (identidad del registro)

**CLAIM R1:** `VM_CONTEXT0_CNTL` es la macro `mmVM_CONTEXT0_CNTL`, un **índice dword** = `0x504`.
- Evidencia: `include/asic_reg/gmc/gmc_8_1_d.h:601` `#define mmVM_CONTEXT0_CNTL  0x504`.
- Evidencia: `include/asic_reg/gmc/gmc_8_2_d.h:603` `#define mmVM_CONTEXT0_CNTL  0x504` (idéntico).
- RXRE: `reg_resolve.py --resolve mmVM_CONTEXT0_CNTL` → `symbol_class=dword_index_de_mm`, `definition_count=11`.
- **Unidad:** el valor `0x504` es un **índice de dword**; el offset de byte = `reg * 4` = `0x504 * 4` = `0x1410`.
  Confirmado por `amdgpu_reg_access.c` (`writel(v, adev->rmmio + (reg * 4))`) y por el `unit_declaration` de `reg_resolve`.

**CLAIM R2:** El registro está definido en **11 lugares** (múltiples generaciones/IP-blocks), y el resolver **no elige** cuál aplica a GFX8.
- Evidencia (RXRE `reg_resolve --resolve mmVM_CONTEXT0_CNTL`): `definition_count=11, chosen=None, candidates=[]`.
- Las 11 definiciones (RXRE `evidence_search --query mmVM_CONTEXT0_CNTL`, 42 hits / 17 ficheros):
  - GMC (GFX6/7/8): `gmc_6_0_d.h:1217`=0x504, `gmc_7_0_d.h:545`=0x504, `gmc_7_1_d.h:578`=0x504, `gmc_8_1_d.h:601`=0x504, `gmc_8_2_d.h:603`=0x504
  - MMHUB (GFX9+): `mmhub_1_0_offset.h:1347`=0x06c0, `mmhub_9_1_offset.h`, `mmhub_9_3_0_offset.h`
  - GC (GFX9+): `gc_9_0_offset.h`, `gc_9_1_offset.h`, `gc_9_2_1_offset.h`
- **Decisión (estática, §49):** para GFX8/Polaris12 la definición aplicable es **`gmc_8_1_d.h:601`** (la que está en alcance para `gmc_v8_0.c`, el fichero productor — ver §2). `gmc_8_2_d.h` tiene el mismo valor `0x504`, así que la identidad del registro es **robusta** frente a la ambigüedad de generación.
- **GAP (observado, no reparado):** `reg_resolve` no selecciona la generación (`chosen=None`). Clasificado `RXRE_CORRECTNESS_GAP-2`.

**CLAIM R3:** El fichero productor `gmc_v8_0.c` incluye `gmc_8_1_d.h` (no `gmc_8_2_d.h`).
- Evidencia: `gmc_v8_0.c:35` `#include "gmc/gmc_8_1_d.h"`.
- Contraste: `gfx_v8_0.c:41` y `mxgpu_vi.c:36` incluyen `gmc_8_2_d.h`.
- RXRE: `evidence_search` (agrupación por fichero, S1) + lectura de `#include` (S7).

---

## 2. PRODUCER (quién construye la escritura)

**CLAIM P1:** El productor principal es **`gmc_v8_0_gart_enable(struct amdgpu_device *adev)`**, `gmc_v8_0.c:829`.
- Evidencia: `gmc_v8_0.c:893-897` (el RREG32/WREG32 de `mmVM_CONTEXT0_CNTL`).
- RXRE: `trace_path.py --from gmc_v8_0_gart_enable --chip CHIP_POLARIS12` → raíz `gmc_v8_0.c:829`, verdict `NO_CONDICIONAL`.
- Identificación de la función contenedora: S3 (awk sobre `gmc_v8_0.c`).

**CLAIM P2:** Hay **tres** puntos de escritura de `mmVM_CONTEXT0_CNTL` en `gmc_v8_0.c` (tres productores), no uno:
1. `gmc_v8_0_gart_enable` (L893-897): read-modify-write que **habilita** el contexto VM0 (el constructor principal).
2. `gmc_v8_0_gart_disable` (L977): `WREG32(mmVM_CONTEXT0_CNTL, 0)` — **deshabilita** (escribe 0).
3. `gmc_v8_0_vm_fault_interrupt_state` (L1402-1408): read-modify-write de los bits de **IRQ de fault** (ver §5).
- Evidencia: RXRE `evidence_search --query mmVM_CONTEXT0_CNTL` (hits en `gmc_v8_0.c` L893, L897, L977, L1402) + S2/S3/S13.

**CLAIM P3 (caller upstream del productor):**
```
amdgpu_device_init (amdgpu_device.c)
  → ip_blocks[i].version->funcs->hw_init(&adev->ip_blocks[i])   [amdgpu_device.c:2132/2159/2199/2329/2349/3188/3228]
    → gmc_v8_0_ip_funcs.hw_init   [fn-ptr, gmc_v8_0.c:1718]
      → gmc_v8_0_hw_init(ip_block)   [gmc_v8_0.c:1203]
        → [if adev->asic_type == CHIP_POLARIS12] gmc_v8_0_polaris_mc_load_microcode(adev)   [gmc_v8_0.c:1220-1222]
        → gmc_v8_0_gart_enable(adev)   [gmc_v8_0.c:1228]  ← PRODUCTOR
```
- Evidencia: `gmc_v8_0.c:1228` `r = gmc_v8_0_gart_enable(adev);` (S9, recuperación por timeout de `trace_path --callers-of`); `gmc_v8_0.c:1718` `.hw_init = gmc_v8_0_hw_init`; `gmc_v8_0.c:1765/1773/1781` `.funcs = &gmc_v8_0_ip_funcs`; `amdgpu_device.c` caller genérico (S11).
- **Rama Polaris12 confirmada:** `gmc_v8_0.c:1220-1222` tiene `adev->asic_type == CHIP_POLARIS12` → `gmc_v8_0_polaris_mc_load_microcode`. Esto ancla la cadena al target (Polaris12).

---

## 3. TRANSFORMATION (cómo se construye el valor)

**CLAIM T1:** El valor se construye por **read-modify-write** con `REG_SET_FIELD`, no por escritura directa de una constante.
```c
/* gmc_v8_0.c:892-897 */
WREG32(mmVM_CONTEXT0_CNTL2, 0);                          /* L892: limpia CNTL2 */
tmp = RREG32(mmVM_CONTEXT0_CNTL);                         /* L893: lee valor actual */
tmp = REG_SET_FIELD(tmp, VM_CONTEXT0_CNTL, ENABLE_CONTEXT, 1);                       /* L894 */
tmp = REG_SET_FIELD(tmp, VM_CONTEXT0_CNTL, PAGE_TABLE_DEPTH, 0);                      /* L895 */
tmp = REG_SET_FIELD(tmp, VM_CONTEXT0_CNTL, RANGE_PROTECTION_FAULT_ENABLE_DEFAULT, 1); /* L896 */
WREG32(mmVM_CONTEXT0_CNTL, tmp);                          /* L897: escribe */
```
- Evidencia: `gmc_v8_0.c:892-897` (S2/S3).

**CLAIM T2 (semántica de los campos, GFX8):** layout de bits desde `gmc_8_1_sh_mask.h:6581-6620` (idéntico en `gmc_8_2_sh_mask.h`):
| Campo | Mask | Shift | Bit | Valor que fija T1 |
|---|---|---|---|---|
| `ENABLE_CONTEXT` | 0x1 | 0x0 | 0 | **1** (habilita el contexto VM0) |
| `PAGE_TABLE_DEPTH` | 0x6 | 0x1 | 1-2 | **0** (profundidad de tabla = 0) |
| `RANGE_PROTECTION_FAULT_ENABLE_DEFAULT` | 0x10 | 0x4 | 4 | **1** (fault de rango por defecto) |
- Bits tocados por T1: `0x1 | 0x10` = `0x11`, con `PAGE_TABLE_DEPTH` (0x6) explícitamente a 0. El resto de bits se preservan del `RREG32`.
- **CORRECCIÓN registrada:** `RANGE_PROTECTION_FAULT_ENABLE_DEFAULT` es **bit 4** (mask 0x10), NO bit 10. Bit 10 (mask 0x400) es `PDE0_PROTECTION_FAULT_ENABLE_DEFAULT`. (S16)

**CLAIM T3 (contexto de la transformación):** antes de T1, `gmc_v8_0_gart_enable` programa las **page tables** del contexto VM0 (S2):
```c
WREG32(mmVM_CONTEXT0_PAGE_TABLE_START_ADDR, adev->gmc.gart_start >> 12);   /* >> 12 = a páginas */
WREG32(mmVM_CONTEXT0_PAGE_TABLE_END_ADDR,   adev->gmc.gart_end >> 12);
WREG32(mmVM_CONTEXT0_PAGE_TABLE_BASE_ADDR,  table_addr >> 12);
WREG32(mmVM_CONTEXT0_PROTECTION_FAULT_DEFAULT_ADDR, (u32)(adev->dummy_page_addr >> 12));
```
- La transformación `>> 12` convierte direcciones de byte a índices de página (4 KiB).

---

## 4. REPRESENTATION (mecanismo concreto de escritura)

**CLAIM W1:** `WREG32(reg, v)` se expande a `amdgpu_device_wreg(adev, reg, v, 0)`.
- Evidencia: `amdgpu/amdgpu.h:1295` `#define WREG32(reg, v) amdgpu_device_wreg(adev, (reg), (v), 0)` (S4).

**CLAIM W2:** `amdgpu_device_wreg` escribe por **MMIO directo a BAR0** en bare metal, o por **PM4 vía KIQ** bajo SR-IOV.
```c
/* amdgpu/amdgpu_reg_access.c */
void amdgpu_device_wreg(struct amdgpu_device *adev, uint32_t reg, uint32_t v, uint32_t acc_flags)
{
    if (amdgpu_device_skip_hw_access(adev)) return;
    if ((reg * 4) < adev->rmmio_size) {
        if (!(acc_flags & AMDGPU_REGS_NO_KIQ) && amdgpu_sriov_runtime(adev) &&
            down_read_trylock(&adev->reset_domain->sem)) {
            amdgpu_kiq_wreg(adev, reg, v, 0);          /* SR-IOV VF: PM4 vía KIQ */
            up_read(&adev->reset_domain->sem);
        } else {
            writel(v, ((void __iomem *)adev->rmmio) + (reg * 4));   /* bare metal: MMIO BAR0 */
        }
    } else {
        amdgpu_reg_pcie_wr32(adev, reg * 4, v);        /* fuera de rmmio: acceso PCIe */
    }
    trace_amdgpu_device_wreg(adev->pdev->device, reg, v);
}
```
- Evidencia: `amdgpu/amdgpu_reg_access.c` (S6).
- **Para esta PC (RX550 física, bare metal):** `writel(v, adev->rmmio + 0x504*4)` = escritura MMIO a **BAR0**, offset de byte **0x1410**.
- **Confirmación de la unidad:** `reg * 4` — el mm* es un índice dword (coherente con `reg_resolve` `dword_index_de_mm` y el `unit_declaration`).
- Observabilidad: tracepoint `trace_amdgpu_device_wreg(pdev->device, reg, v)`.

---

## 5. CONSUMER (quién consume la escritura)

**CLAIM C1 (consumidor hardware):** el consumidor último es la **unidad de VM/MMU del GMC** (VM context 0), que usa `VM_CONTEXT0_CNTL` para habilitar el contexto y traducir direcciones GPU-virtuales usando la page table configurada por T3. Este consumo es **hardware** (no es trazable por RXRE, que solo ve software); se infiere de la semántica de los campos (T2) y de la función del bloque GMC.
- Estado: `DERIVATION` (semántica de campos + función del IP block), no observación de hardware.

**CLAIM C2 (consumidor software, segundo productor/lector):** `gmc_v8_0_vm_fault_interrupt_state` (gmc_v8_0.c:1385) **lee y reescribe** `mmVM_CONTEXT0_CNTL` para habilitar/deshabilitar las IRQs de fault:
```c
/* gmc_v8_0.c:1386-1414 */
u32 bits = (VM_CONTEXT1_CNTL__RANGE_PROTECTION_FAULT_ENABLE_INTERRUPT_MASK |      /* 0x8   bit 3  */
            VM_CONTEXT1_CNTL__DUMMY_PAGE_PROTECTION_FAULT_ENABLE_INTERRUPT_MASK | /* 0x40  bit 6  */
            VM_CONTEXT1_CNTL__PDE0_PROTECTION_FAULT_ENABLE_INTERRUPT_MASK |       /* 0x200 bit 9  */
            VM_CONTEXT1_CNTL__VALID_PROTECTION_FAULT_ENABLE_INTERRUPT_MASK |      /* 0x1000 bit 12 */
            VM_CONTEXT1_CNTL__READ_PROTECTION_FAULT_ENABLE_INTERRUPT_MASK |       /* 0x8000 bit 15 */
            VM_CONTEXT1_CNTL__WRITE_PROTECTION_FAULT_ENABLE_INTERRUPT_MASK |      /* 0x40000 bit 18 */
            VM_CONTEXT1_CNTL__EXECUTE_PROTECTION_FAULT_ENABLE_INTERRUPT_MASK);    /* 0x200000 bit 21 */
/* bits = 0x249248 */
case AMDGPU_IRQ_STATE_DISABLE:  tmp = RREG32(mmVM_CONTEXT0_CNTL); tmp &= ~bits; WREG32(mmVM_CONTEXT0_CNTL, tmp); /* ... */
case AMDGPU_IRQ_STATE_ENABLE:   tmp = RREG32(mmVM_CONTEXT0_CNTL); tmp |=  bits; WREG32(mmVM_CONTEXT0_CNTL, tmp); /* ... */
```
- Evidencia: `gmc_v8_0.c:1385-1420` (S13). Los `_MASK` de `VM_CONTEXT1_CNTL` se reutilizan para VM_CONTEXT0 porque el layout de bits es idéntico (verificado en `gmc_8_1_sh_mask.h`).
- **Relación producer↔consumer:** el consumidor **preserva** los bits que el productor fijó (ENABLE_CONTEXT, PAGE_TABLE_DEPTH, RANGE_PROTECTION_FAULT_ENABLE_DEFAULT) y solo altera los 7 bits `*_INTERRUPT` (bits 3,6,9,12,15,18,21). Es una dependencia de datos: el consumidor lee lo que el productor escribió.

**CLAIM C3 (deshabilitación):** `gmc_v8_0_gart_disable` (gmc_v8_0.c:977) consume el registro escribiendo 0 (deshabilita el contexto), invirtiendo el efecto del productor.
- Evidencia: `gmc_v8_0.c:977` `WREG32(mmVM_CONTEXT0_CNTL, 0);` (S2/S3).

---

## 6. SEMANTIC EFFECT (efecto final)

**CLAIM E1:** el efecto de la escritura de `VM_CONTEXT0_CNTL` (T1, vía W2) es:
- bit 0 `ENABLE_CONTEXT=1` → **habilita** el contexto de VM 0 (el MMU empieza a traducir direcciones usando la page table de T3).
- bits 1-2 `PAGE_TABLE_DEPTH=0` → tabla de páginas de **1 nivel** (profundidad 0).
- bit 4 `RANGE_PROTECTION_FAULT_ENABLE_DEFAULT=1` → se genera **fault por defecto** en violaciones de rango.
- Efecto conjunto: el GMC queda configurado para traducir direcciones GPU-virtuales del contexto 0 contra la GART page table, con protección de rango activa.
- Estado: `DERIVATION` (de la semántica de campos T2 + la función del bloque GMC). No es observación de hardware directa.

---

## 7. BIDIRECCIONALIDAD (producer ↔ consumer)

**CLAIM B1:** `BIDIRECTIONAL_RELATION = PARTIAL`.
- **productor → consumidor (flujo de datos): PASS.** El consumidor (C2) lee `mmVM_CONTEXT0_CNTL` y preserva los bits que el productor (T1) estableció. Hay una dependencia de datos real.
- **consumidor → productor (flujo de datos): FAIL.** El productor lee el registro a `t=init` (valor de reset, L893) **antes** de que el consumidor ejecute; ningún dato fluye del consumidor al productor.
- **productor ↔ consumidor (grafo de llamadas): FAIL en ambos sentidos.** No hay arista de llamada entre `gmc_v8_0_gart_enable` y `gmc_v8_0_vm_fault_interrupt_state`; son invocados desde fases distintas del init (device-init vs IRQ-setup). La relación es **solo a través del registro compartido**.
- **Verdicto:** la relación es **bidireccional sobre el registro compartido** (ambos lo acceden), pero **unidireccional en flujo de datos** (productor→consumidor) y **ausente en el grafo de llamadas**.
- Nota metodológica: `relations.py`/`claims.py` operan sobre la DB de findings numerados, no sobre símbolos de fuente; no hay finding previo sobre `VM_CONTEXT0_CNTL` (S15), así que la bidireccionalidad se prueba sobre la cadena de fuente reconstruida.

---

## 8. CADENA CAUSAL COMPLETA

```
REGISTER   mmVM_CONTEXT0_CNTL = 0x504 (dword index)          gmc_8_1_d.h:601
   │       byte offset = 0x504 * 4 = 0x1410 (BAR0/rmmio)
   ▼
PRODUCER   gmc_v8_0_gart_enable(adev)                         gmc_v8_0.c:829
   │       llamado por gmc_v8_0_hw_init (L1228) ← gmc_v8_0_ip_funcs.hw_init (L1718)
   │       ← amdgpu_device_init → ip_blocks[].version->funcs->hw_init()
   ▼
TRANSFORM  tmp=RREG32; REG_SET_FIELD(ENABLE_CONTEXT,1);       gmc_v8_0.c:893-897
           REG_SET_FIELD(PAGE_TABLE_DEPTH,0);
           REG_SET_FIELD(RANGE_PROTECTION_FAULT_ENABLE_DEFAULT,1)
   │       (+ page-table start/end/base/fault-addr, >>12)      gmc_v8_0.c:886-891
   ▼
REPR       WREG32(mmVM_CONTEXT0_CNTL, tmp)                    amdgpu.h:1295
   │       → amdgpu_device_wreg(adev, 0x504, tmp, 0)          amdgpu_reg_access.c
   │       → writel(tmp, adev->rmmio + 0x1410)  [bare metal]  ← ESTA PC
   │       → amdgpu_kiq_wreg(...)              [SR-IOV VF]
   │       + tracepoint trace_amdgpu_device_wreg
   ▼
CONSUMER   HW: unidad VM/MMU del GMC (contexto 0)             (hardware, no observable por RXRE)
           SW: gmc_v8_0_vm_fault_interrupt_state (L1385)      gmc_v8_0.c:1402-1408
               (read-modify-write de los 7 bits *_INTERRUPT=0x249248)
           SW: gmc_v8_0_gart_disable (L977) → WREG32(...,0)   gmc_v8_0.c:977
   ▼
EFFECT     contexto VM0 habilitado; tabla de 1 nivel;          (DERIVATION)
           protección de rango activa; MMU traduce contra GART
```

---

## 9. LIMITACIONES Y ESTADOS

- `reg_resolve` no resuelve sin prefijo `mm` (`RXRE_CORRECTNESS_GAP-1`) ni elige generación (`RXRE_CORRECTNESS_GAP-2`). **Observado, no reparado** (regla DOGFOOD-008).
- `trace_path --callers-of` hace timeout sobre el corpus (`RXRE_CAPABILITY_GAP-3`); recuperado por grep (S9).
- `trace_path --from` resuelve símbolos genéricos por coincidencia textual (`RXRE_LIMITATION-4`); su selftest advierte "veredicto por rama declarada, NO prueba ejecución real".
- El consumidor hardware (C1) y el efecto final (E1) son `DERIVATION` (semántica de campos + función del IP block), **no** observación de hardware. No se hizo takeover de la GPU (verde: la consola es de la Intel i915; prohibido tocarla).
- No se reutilizaron conclusiones de DOGFOOD-001/002 como autoridad; la cadena se reconstruyó con evidencia de esta sesión.
