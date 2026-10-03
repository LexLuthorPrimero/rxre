/* rx550_vm.h — GFX8 VMID-0 page table model: PTE layout and PDB0 geometry.
 *
 * SCOPE: pure data and pure arithmetic.  It computes what the page table for
 * VMID 0 must contain for a given GPU virtual address and a given system
 * physical address.  It performs NO writeq, NO MMIO, NO DMA.
 *
 * EVIDENCE (drivers/gpu/drm/amd/, project corpus linux-7.1.3, GFX8 only):
 *   gmc_v8_0.c:1134       pte_addr_mask = 0x000000FFFFFFF000  (40-bit PA)
 *   amdgpu_vm.h:57-68     VALID bit0, SYSTEM bit1, SNOOPED bit2, EXECUTABLE
 *                         bit4 (VI only), READABLE bit5, WRITEABLE bit6
 *   amdgpu_vm.h:70        FRAG(x) = (x & 0x1f) << 7
 *   amdgpu_vm.h:141-142   AMDGPU_PDE_PTE_FLAG(adev) == AMDGPU_PDE_PTE (bit 54)
 *                         for any gfx below v12 — that includes GFX8
 *   gmc_v8_0.c:961        gfx8 gart_pte_flags = AMDGPU_PTE_EXECUTABLE (no MTYPE;
 *                         MTYPE fields exist only for v9+/NV10/GFX12)
 *   amdgpu_gmc.c:1136-1139 each PDE0 (used as PTE) covers
 *                         2^block_size * 2 MiB, block_size = 0 for GFX8
 *   amdgpu_gmc.c:1145-1150 PDB0 is VRAM, PAGE_SIZE aligned, contiguous, CPU
 *                         accessible
 *   amdgpu_gmc.c:163-175  entry value = (addr & pte_addr_mask) | flags
 *
 * NOT_DETERMINED, deliberately not modelled: the hardware meaning of FRAG,
 * cache/maintenance semantics of SNOOPED, and whether EXECUTABLE is required.
 * No ISA document was available to this component.
 */
#ifndef RX550_VM_H
#define RX550_VM_H

#include "rx550_addr.h"

/* ---------------------------------------------------------- PTE bit layout */
#define RX550_PTE_VALID      (UINT64_C(1) << 0)   /* amdgpu_vm.h:57  */
#define RX550_PTE_SYSTEM     (UINT64_C(1) << 1)   /* amdgpu_vm.h:58  */
#define RX550_PTE_SNOOPED    (UINT64_C(1) << 2)   /* amdgpu_vm.h:59  */
#define RX550_PTE_EXECUTABLE (UINT64_C(1) << 4)   /* amdgpu_vm.h:66  */
#define RX550_PTE_READABLE   (UINT64_C(1) << 5)   /* amdgpu_vm.h:67  */
#define RX550_PTE_WRITEABLE  (UINT64_C(1) << 6)   /* amdgpu_vm.h:68  */

/* FRAG occupies bits 11:7 and holds 5 bits.  amdgpu_vm.h:70 */
#define RX550_PTE_FRAG_SHIFT 7
#define RX550_PTE_FRAG_MAX   0x1fu

/* A PDE interpreted as a PTE: bit 54 on gfx < v12.  amdgpu_vm.h:141 */
#define RX550_PDE_PTE        (UINT64_C(1) << 54)

/* The physical address field: 40 bits, 4 KiB granularity.
 * gmc_v8_0.c:1134 — the source comments it "40 bit PA". */
#define RX550_PTE_ADDR_MASK  UINT64_C(0x000000FFFFFFF000)
#define RX550_PTE_ADDR_BITS  40

/* Default flags the reference installs before adding VALID/READ/WRITE/SNOOPED:
 * gmc_v8_0.c:961.  Kept separate so a caller can tell "what the hardware field
 * positions are" from "what the reference chose to set". */
#define RX550_GART_PTE_FLAGS_GFX8 RX550_PTE_EXECUTABLE

/* PDB0 entry granularity for GFX8: 2^block_size * 2 MiB with block_size = 0.
 * amdgpu_gmc.c:1136-1139.  This is the unit the hardware translates by. */
#define RX550_PDB0_BLOCK_SIZE_SHIFT 21
#define RX550_PDB0_ENTRY_BYTES  (UINT64_C(1) << RX550_PDB0_BLOCK_SIZE_SHIFT)

/* Block size register value for GFX8: never assigned, so zero.  Derived from
 * the absence of any assignment in gmc_v8_0.c. */
#define RX550_PDB0_BLOCK_SIZE 0u

/* Page table depth for GFX8 VMID 0: zero means a FLAT table, one level.
 * See gfxhub_v1_0.c:218-230 which programs PAGE_TABLE_DEPTH from it. */
#define RX550_PT_DEPTH_GFX8 0u

/* The flags the reference installs for a PDB0 entry:
 * amdgpu_gmc.c:1147-1151
 *   VALID | READABLE | WRITEABLE | SNOOPED
 *   | FRAG(block_size + 9)
 *   | PDE_PTE_FLAG
 * plus the gfx8 gart_pte_flags base.  With block_size = 0 that is FRAG(9). */
uint64_t rx550_pdb0_entry_flags(void);

/* Builds one PDB0 entry: (system_physical & ADDR_MASK) | flags.
 * Mirrors amdgpu_gmc.c:173-175. */
uint64_t rx550_pdb0_entry(uint64_t system_pa, uint64_t flags);

/* Index of the PDB0 entry that must cover `gpu_va`, given the GART window
 * base.  Returns RX550_VM_NO_INDEX if the address is outside the window or
 * the mapping would not fit in the 46-bit descriptor field. */
#define RX550_VM_NO_INDEX 0xffffffffu
uint32_t rx550_pdb0_index(uint64_t gpu_va, uint64_t gart_base);

/* How many PDB0 entries a buffer of `size_bytes` starting at `gpu_va`
 * occupies, given 2 MiB granularity.  A buffer smaller than 2 MiB still
 * consumes one whole entry: the hardware translates at entry granularity, not
 * at buffer granularity.  This is why a 20-byte IB costs a 2 MiB mapping. */
uint32_t rx550_pdb0_entries_for(uint64_t gpu_va, uint32_t size_bytes,
				uint64_t gart_base);

/* The system physical address a buffer must start at to be reachable through
 * PDB0 entry `index`: entries are 2 MiB granular and the address is masked to
 * 4 KiB, so the caller must supply an already-2MiB-aligned PA. */
int rx550_pdb0_phys_for_index(uint32_t index, uint64_t gart_base,
			      uint64_t *out_pa);

#endif /* RX550_VM_H */
