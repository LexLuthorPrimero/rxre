/* rx550_vm.c — GFX8 VMID-0 page table model.  Pure arithmetic. */

#include "rx550_vm.h"

uint64_t rx550_pdb0_entry_flags(void)
{
	uint32_t frag = RX550_PDB0_BLOCK_SIZE + 9u;

	return RX550_GART_PTE_FLAGS_GFX8
	     | RX550_PTE_VALID
	     | RX550_PTE_READABLE
	     | RX550_PTE_WRITEABLE
	     | RX550_PTE_SNOOPED
	     | RX550_PDE_PTE
	     | (((uint64_t)frag & RX550_PTE_FRAG_MAX) << RX550_PTE_FRAG_SHIFT);
}

uint64_t rx550_pdb0_entry(uint64_t system_pa, uint64_t flags)
{
	/* amdgpu_gmc.c:173-175 — the address is masked, so bits above the
	 * 40-bit field are dropped rather than rejected.  This component
	 * exposes that behaviour explicitly instead of hiding it, and the
	 * caller is expected to have validated the address already. */
	return (system_pa & RX550_PTE_ADDR_MASK) | flags;
}

uint32_t rx550_pdb0_index(uint64_t gpu_va, uint64_t gart_base)
{
	uint64_t off;

	if (gpu_va > RX550_GART_ADDR_MASK)
		return RX550_VM_NO_INDEX;
	if (gpu_va < gart_base)
		return RX550_VM_NO_INDEX;
	off = gpu_va - gart_base;
	/* The index must itself be representable: the flat table is indexed by
	 * the offset from the window base, and the field is bounded. */
	off >>= RX550_PDB0_BLOCK_SIZE_SHIFT;
	if (off > 0xffffffffu)
		return RX550_VM_NO_INDEX;
	return (uint32_t)off;
}

uint32_t rx550_pdb0_entries_for(uint64_t gpu_va, uint32_t size_bytes,
				uint64_t gart_base)
{
	uint64_t first, last, n;

	if (rx550_pdb0_index(gpu_va, gart_base) == RX550_VM_NO_INDEX)
		return RX550_VM_NO_INDEX;
	if (size_bytes == 0u)
		return RX550_VM_NO_INDEX;

	first = (gpu_va - gart_base) >> RX550_PDB0_BLOCK_SIZE_SHIFT;
	last = (gpu_va - gart_base + size_bytes - 1u)
	       >> RX550_PDB0_BLOCK_SIZE_SHIFT;
	n = last - first + 1u;
	if (n > 0xffffffffu)
		return RX550_VM_NO_INDEX;
	return (uint32_t)n;
}

int rx550_pdb0_phys_for_index(uint32_t index, uint64_t gart_base,
			      uint64_t *out_pa)
{
	uint64_t va, pa;

	if (!out_pa)
		return RX550_EINVAL;
	va = gart_base + ((uint64_t)index << RX550_PDB0_BLOCK_SIZE_SHIFT);
	if (va > RX550_GART_ADDR_MASK)
		return RX550_EBOUNDS;
	/* An identity-mapped VA is the only physical address this model can
	 * justify: the GART window is placed at the top of the MC range
	 * (amdgpu_gmc.c:314) and the system-memory block that follows it is
	 * populated by a component this model does not own.  Reporting the
	 * identity is honest; inventing a translation would not be. */
	pa = va & RX550_PTE_ADDR_MASK;
	*out_pa = pa;
	return RX550_OK;
}
