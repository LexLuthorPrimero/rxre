# 1588 — Secuencia completa de TLB flush en GFX8: `gmc_v8_0_emit_flush_gpu_tlb` + `WAIT_REG_MEM` + `PFP_SYNC_ME`

## 0 · RESUMEN

El "muro de fuente" del hallazgo **1421** (GFX8 no publica registros de VM) **se rompe para la secuencia de flush**: el formato PTE/PDE está documentado en `gmc_v8_0.c:692-710`, los registros `mmVM_INVALIDATE_REQUEST` y `mmVM_CONTEXT0_PAGE_TABLE_BASE_ADDR` existen en `gmc_8_1_d.h`/`gmc_8_2_d.h`, y la secuencia completa de 3 pasos es visible en `gfx_v8_0_ring_emit_vm_flush` + `gmc_v8_0_emit_flush_gpu_tlb`. Conecta hallazgos **1580** (`WAIT_REG_MEM`), **1581** (`PFP_SYNC_ME`), y cierra la semántica de entrada a GPUVM.

---

## 1 · LA SECUENCIA COMPLETA (fuente verificada)

```c
// gmc_v8_0_emit_flush_gpu_tlb [gmc_v8_0.c:668-683]
static uint64_t gmc_v8_0_emit_flush_gpu_tlb(struct amdgpu_ring *ring,
                                            unsigned int vmid, uint64_t pd_addr)
{
    uint32_t reg;
    if (vmid < 8)
        reg = mmVM_CONTEXT0_PAGE_TABLE_BASE_ADDR + vmid;   // 0x54F + vmid
    else
        reg = mmVM_CONTEXT8_PAGE_TABLE_BASE_ADDR + vmid - 8; // 0x557 + (vmid-8)
    amdgpu_ring_emit_wreg(ring, reg, pd_addr >> 12);       // Write PD base

    // Trigger invalidation for this VMID
    amdgpu_ring_emit_wreg(ring, mmVM_INVALIDATE_REQUEST, 1 << vmid); // 0x51E
    return pd_addr;
}

// gfx_v8_0_ring_emit_vm_flush [gfx_v8_0.c:6191-6215]
static void gfx_v8_0_ring_emit_vm_flush(struct amdgpu_ring *ring,
                                        unsigned vmid, uint64_t pd_addr)
{
    int usepfp = (ring->funcs->type == AMDGPU_RING_TYPE_GFX);

    amdgpu_gmc_emit_flush_gpu_tlb(ring, vmid, pd_addr);    // ← Step 1-2 above

    // Wait for invalidation to complete
    amdgpu_ring_write(ring, PACKET3(PACKET3_WAIT_REG_MEM, 5));  // ← Step 3
    amdgpu_ring_write(ring, WAIT_REG_MEM_OPERATION(0) |       // wait
                    WAIT_REG_MEM_FUNCTION(0) |                // always
                    WAIT_REG_MEM_ENGINE(0));                  // me
    amdgpu_ring_write(ring, mmVM_INVALIDATE_REQUEST);         // register to poll
    amdgpu_ring_write(ring, 0);                               // high dword
    amdgpu_ring_write(ring, 0);                               // ref
    amdgpu_ring_write(ring, 0);                               // mask
    amdgpu_ring_write(ring, 0x20);                            // poll interval

    // Compute doesn't have PFP
    if (usepfp) {
        // Sync PFP to ME, otherwise we might get invalid PFP reads
        amdgpu_ring_write(ring, PACKET3(PACKET3_PFP_SYNC_ME, 0)); // ← Step 4
        amdgpu_ring_write(ring, 0x0);
    }
}
```

---

## 2 · REGISTROS Y OFFSETS CONCRETOS (GFX8 / GMC 8.1)

| Registro | Macro | `gmc_8_1_d.h` dword offset | Byte offset (MMIO) | Uso |
|----------|-------|---------------------------|-------------------|-----|
| `mmVM_INVALIDATE_REQUEST` | `mmVM_INVALIDATE_REQUEST` | **0x51E** | **0x1478** | Escrito (1<<VMID), luego polleado por WAIT_REG_MEM |
| `mmVM_CONTEXT0_PAGE_TABLE_BASE_ADDR` | `mmVM_CONTEXT0_PAGE_TABLE_BASE_ADDR` | **0x54F** | **0x153C** | Base PD para VMID 0-7 |
| `mmVM_CONTEXT8_PAGE_TABLE_BASE_ADDR` | `mmVM_CONTEXT8_PAGE_TABLE_BASE_ADDR` | **0x557** | **0x155C** | Base PD para VMID 8-15 |

> Ambos headers (`gmc_8_1_d.h` y `gmc_8_2_d.h`) tienen valores idénticos. GFX8 usa GMC 8.1.

---

## 3 · FORMATO PTE / PDE (documentado en `gmc_v8_0.c:692-710`)

### PTE (4 KB page)
```
Bit 63:40  RESERVED
Bit 39:12  Physical page base address (4 KB aligned)
Bit 11:7   Fragment (5 bits)
Bit 6      Write permission
Bit 5      Read permission
Bit 4      Execute permission
Bit 3      Reserved
Bit 2      Snooped
Bit 1      System
Bit 0      Valid
```

### PDE (Page Directory Entry)
```
Bit 63:59  Block fragment size (5 bits)
Bit 58:40  Reserved
Bit 39:1   Physical base address of PTE table
Bit 5:1    Must be 0
Bit 0      Valid
```

> **Nota**: `gmc_v8_0_get_vm_pde` (`:712-716`) asume `*addr & 0xFFFFFF0000000FFFULL == 0` — la base del PDE debe estar alineada a 256 KB (bits 12:39 para dirección, bits 0:11 MBZ).

---

## 4 · CONEXIÓN CON HALLAZGOS PREVIOS

| Hallazgo | Qué aporta | Cómo encaja aquí |
|----------|------------|------------------|
| **1580** | `PACKET3_WAIT_REG_MEM` opcode `0x3C`, 4 campos, 3 emisiones en GFX8 | **Una de las 3 emisiones ES ESTA** (línea 6199-6207): pollea `mmVM_INVALIDATE_REQUEST` en engine ME |
| **1581** | `PACKET3_PFP_SYNC_ME` opcode `0x42`, count=0, 1 uso en GFX8 | **ES ESTE** (línea 6212): sincroniza PFP→ME tras invalidación TLB |
| **1584** | Cobertura RXRE 22% sobre 11.866 registros | Estos registros están en `gmc_8_1_d.h` (cabecera nativa GFX8) → **descubiertos por RXRE** |
| **1421** | "GFX8 no publica ningún registro de VM" | **REFUTADO PARCIALMENTE**: el *flush path* SÍ está publicado (gmc_8_1_d.h + gmc_v8_0.c). Lo que falta son `VM_CONTEXT{2..15}_CNTL` y la decodificación completa de `EVENT_WRITE_EOP` |

---

## 5 · LA ENTRADA A GPUVM (hallazgo 1580 § "vía de entrada a GPUVM")

El hallazgo 1580 identificó que una de las 3 emisiones de `WAIT_REG_MEM` en GFX8 es "la vía de entrada a GPUVM". **Esta es esa vía**:

```
Page Directory update (host writes PD base)
         │
         ▼
Write VM_CONTEXT{0,8}_PAGE_TABLE_BASE_ADDR  [gmc_v8_0_emit_flush_gpu_tlb]
         │
         ▼
Write VM_INVALIDATE_REQUEST = (1 << VMID)   [gmc_v8_0_emit_flush_gpu_tlb]
         │
         ▼
GPU starts TLB invalidation for that VMID
         │
         ▼
WAIT_REG_MEM polls VM_INVALIDATE_REQUEST == 0  [gfx_v8_0_ring_emit_vm_flush]
         │         (engine=ME, function=always, operation=wait)
         ▼
PFP_SYNC_ME (if GFX ring)                     [gfx_v8_0_ring_emit_vm_flush]
         │
         ▼
TLB flush complete → safe to use new page tables
```

---

## 6 · IMPLICACIONES PARA DRIVER PROPIO

### Emisión PM4 directa (sin helper del kernel)

```c
// 1. Write PD base (byte offset = dword_offset * 4)
ring_emit_wreg(ring, 0x153C + (vmid < 8 ? vmid*4 : (vmid-8)*4 + 0x20), pd_addr >> 12);

// 2. Trigger invalidation
ring_emit_wreg(ring, 0x1478, 1u << vmid);

// 3. WAIT_REG_MEM (PACKET3_WAIT_REG_MEM = 0x3C, count=5)
ring_write(ring, 0x3C000005);                    // PACKET3 header
ring_write(ring, 0x00000000);                    // op=wait, fn=always, engine=ME
ring_write(ring, 0x00001478);                    // mmVM_INVALIDATE_REQUEST (byte offset)
ring_write(ring, 0x00000000);                    // high dword
ring_write(ring, 0x00000000);                    // ref
ring_write(ring, 0x00000000);                    // mask
ring_write(ring, 0x00000020);                    // poll interval = 32

// 4. PFP_SYNC_ME (PACKET3_PFP_SYNC_ME = 0x42, count=0) - solo GFX ring
ring_write(ring, 0x42000000);
ring_write(ring, 0x00000000);
```

### PTE/PDE construction

```c
// PTE: 64 bits
uint64_t pte = (phys_addr & 0xFFFFFFFFFFFFF000ULL) |  // bits 39:12
               ((fragment & 0x1F) << 7) |              // bits 11:7
               (write ? (1<<6) : 0) |
               (read  ? (1<<5) : 0) |
               (exec  ? (1<<4) : 0) |
               (snooped ? (1<<2) : 0) |
               (system  ? (1<<1) : 0) |
               (valid   ? (1<<0) : 0);

// PDE: 64 bits
uint64_t pde = (pte_table_base & 0xFFFFFFFFFFE00ULL) | // bits 39:1 (256KB aligned)
               ((frag_size & 0x1F) << 59) |             // bits 63:59
               (valid ? 1 : 0);                         // bit 0
```

---

## 7 · ESTADO EPISTÉMICO

| Magnitud | Estado | Justificación |
|----------|--------|---------------|
| Secuencia flush (4 pasos) | **PROVEN_DERIVED** | Código fuente completo en 7.1.3, 2 funciones |
| Registros VM_INVALIDATE_REQUEST / CONTEXT_PAGE_TABLE_BASE | **PROVEN** | En `gmc_8_1_d.h` / `gmc_8_2_d.h` (cabeceras nativas GFX8) |
| Formato PTE/PDE | **PROVEN_DERIVED** | Comentarios en `gmc_v8_0.c:692-710` (documentación kernel) |
| `WAIT_REG_MEM` pollea `VM_INVALIDATE_REQUEST` | **PROVEN_DERIVED** | Código explícito en `gfx_v8_0_ring_emit_vm_flush` |
| `PFP_SYNC_ME` tras flush | **PROVEN_DERIVED** | Código explícito, condicionado a `ring_type == GFX` |
| Decodificación `EVENT_WRITE_EOP` (si.h) | **NOT_PUBLISHED** | Hallazgo 1421 — sigue abierto, no afecta al flush |
| `VM_CONTEXT{2..15}_CNTL` | **NOT_PUBLISHED** | Hallazgo 1421 — contexto multi-VM no necesario para flush básico |

**LIMITACIÓN**: árbol 7.1.3 vs kernel 7.2.9 corriendo; la secuencia de flush es estable desde VI.

---

## 8 · ARTEFACTOS

- Código fuente: `gmc_v8_0.c:661-683`, `gfx_v8_0.c:6191-6215`
- Registros: `gmc_8_1_d.h:617,638` / `gmc_8_2_d.h:617,638`
- PTE/PDE: `gmc_v8_0.c:692-710`

---

## 9 · PRÓXIMA ACCIÓN (Global Work Scan §58)

- [15] **IMPLEMENTATION**: emitir secuencia completa en driver C/ASM con offsets concretos
- [04] **DEPENDENCIES**: `VM_INVALIDATE_REQUEST` @ 0x1478, `CONTEXT_PAGE_TABLE_BASE` @ 0x153C → listos para PM4
- [19] **VALIDATION**: si MMIO autorizado, verificar `mmVM_INVALIDATE_REQUEST` bit behavior en flush real
- [03] **CLAIMS**: formato PTE/PDE → claim crítico para GPUVM; ahora tiene fuente (kernel comments)