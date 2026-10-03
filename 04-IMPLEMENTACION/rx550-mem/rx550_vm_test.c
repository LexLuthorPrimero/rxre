/* rx550_vm_test.c — tests for the GFX8 PDB0 / PTE model.
 * Concrete 64-bit values, concrete indices.  No hardware, no MMIO. */

#include "rx550_vm.h"

#include <stdio.h>
#include <string.h>

static unsigned g_pass, g_fail;

#define CHECK(cond, what)                                                      \
	do {                                                                   \
		if (cond) {                                                     \
			g_pass++;                                            \
		} else {                                                        \
			g_fail++;                                            \
			printf("  FAIL %s:%d  %s\n", __FILE__, __LINE__, (what)); \
		}                                                              \
	} while (0)

#define CHECK_EQ(got, want, what)                                              \
	do {                                                                   \
		uint64_t rx550__g = (uint64_t)(got);                           \
		uint64_t rx550__w = (uint64_t)(want);                          \
		if (rx550__g == rx550__w) {                                    \
			g_pass++;                                            \
		} else {                                                        \
			g_fail++;                                            \
			printf("  FAIL %s:%d  %s: got 0x%016llX want 0x%016llX\n", \
			       __FILE__, __LINE__, (what),                     \
			       (unsigned long long)rx550__g,                  \
			       (unsigned long long)rx550__w);                 \
		}                                                              \
	} while (0)

#define CHECK_RC(got, want, what)                                              \
	do {                                                                   \
		int rx550__g = (int)(got);                                    \
		int rx550__w = (int)(want);                                   \
		if (rx550__g == rx550__w) {                                   \
			g_pass++;                                            \
		} else {                                                        \
			g_fail++;                                            \
			printf("  FAIL %s:%d  %s: got %d want %d\n",         \
			       __FILE__, __LINE__, (what), rx550__g, rx550__w); \
		}                                                              \
	} while (0)

#define GART_BASE UINT64_C(0x000000FFC0000000)

/* ---- B1: the PDB0 entry flag word, bit for bit.
 * amdgpu_gmc.c:1147-1151 installs:
 *   base(gmc_v8_0.c:961 = EXECUTABLE)
 *   | VALID | READABLE | WRITEABLE | SNOOPED
 *   | FRAG(0 + 9) = 9<<7 = 0x480
 *   | PDE_PTE_FLAG = AMDGPU_PDE_PTE = bit 54
 */
static void t_pdb0_flags(void)
{
	uint64_t f = rx550_pdb0_entry_flags();

	CHECK_EQ(f, UINT64_C(0x00400000000004F5), "B1: PDB0 entry flags");
	CHECK_EQ(f & RX550_PTE_VALID, RX550_PTE_VALID, "B1: VALID set");
	CHECK_EQ(f & RX550_PTE_READABLE, RX550_PTE_READABLE, "B1: READABLE set");
	CHECK_EQ(f & RX550_PTE_WRITEABLE, RX550_PTE_WRITEABLE, "B1: WRITEABLE set");
	CHECK_EQ(f & RX550_PTE_SNOOPED, RX550_PTE_SNOOPED, "B1: SNOOPED set");
	CHECK_EQ(f & RX550_PDE_PTE, RX550_PDE_PTE, "B1: PDE_PTE set");
	CHECK_EQ(f & RX550_PTE_SYSTEM, 0u, "B1: SYSTEM must not be set");
	CHECK_EQ((f >> RX550_PTE_FRAG_SHIFT) & RX550_PTE_FRAG_MAX, 9u,
		 "B1: FRAG value");
	/* MTYPE does not exist on GFX8; nothing may land in bits 57:59 or 48:54
	 * other than the PDE_PTE bit itself. */
	CHECK_EQ(f & (UINT64_C(0x7f) << 57), 0u, "B1: MTYPE bits set on GFX8");
}

/* ---- B2: entry construction masks the address to 40 bits / 4 KiB. */
static void t_entry(void)
{
	uint64_t flags = rx550_pdb0_entry_flags();

	/* a clean 4 KiB-aligned PA below the 40-bit field is preserved */
	CHECK_EQ(rx550_pdb0_entry(UINT64_C(0x0000000012345000), flags),
		 UINT64_C(0x0000000012345000) | flags, "B2: entry keeps PA");
	/* bits above the 40-bit field are dropped, not carried */
	CHECK_EQ(rx550_pdb0_entry(UINT64_C(0x00FF000012345000), flags),
		 UINT64_C(0x0000000012345000) | flags, "B2: high bits not masked");
	/* sub-4KiB bits are dropped */
	CHECK_EQ(rx550_pdb0_entry(UINT64_C(0x0000000012345123), flags),
		 UINT64_C(0x0000000012345000) | flags, "B2: low bits not masked");
	/* the flags are a strict OR, never overwritten by the address */
	CHECK_EQ(rx550_pdb0_entry(0u, flags), flags, "B2: flags clobbered by PA 0");
}

/* ---- B3: geometry.  2 MiB per entry for GFX8. */
static void t_geometry(void)
{
	CHECK_EQ(RX550_PDB0_ENTRY_BYTES, UINT64_C(0x200000), "B3: entry size");
	CHECK_EQ(RX550_PDB0_BLOCK_SIZE, 0u, "B3: block size");
	CHECK_EQ(RX550_PT_DEPTH_GFX8, 0u, "B3: depth is flat");
	CHECK_EQ(RX550_PTE_ADDR_MASK, UINT64_C(0x000000FFFFFFF000), "B3: addr mask");
}

/* ---- B4: index arithmetic, and the fact that a 20-byte IB costs a whole
 * 2 MiB mapping entry.  This is the design consequence of depth 0. */
static void t_index(void)
{
	uint64_t va = GART_BASE;

	CHECK_EQ(rx550_pdb0_index(va, GART_BASE), 0u, "B4: index at window base");
	CHECK_EQ(rx550_pdb0_index(va + 0x1FFFFF, GART_BASE), 0u,
		 "B4: last byte of first entry");
	CHECK_EQ(rx550_pdb0_index(va + 0x200000, GART_BASE), 1u,
		 "B4: first byte of second entry");
	CHECK_EQ(rx550_pdb0_index(va + 0x200000 + 0x1234, GART_BASE), 1u,
		 "B4: inside second entry");

	/* below the window, and beyond the 46-bit field */
	CHECK_EQ(rx550_pdb0_index(GART_BASE - 1u, GART_BASE),
		 RX550_VM_NO_INDEX, "B4: below window accepted");
	CHECK_EQ(rx550_pdb0_index(RX550_GART_ADDR_MASK + 1u, GART_BASE),
		 RX550_VM_NO_INDEX, "B4: beyond field accepted");

	/* the small-IB fact: 20 bytes still consumes one whole 2 MiB entry,
	 * which is what gfx_v8_0.c:887-896 submits. */
	CHECK_EQ(rx550_pdb0_entries_for(va, 20u, GART_BASE), 1u,
		 "B4: 20-byte IB entry count");
	CHECK_EQ(rx550_pdb0_entries_for(va, 0x1FFFFF, GART_BASE), 1u,
		 "B4: just-under-2MiB entry count");
	CHECK_EQ(rx550_pdb0_entries_for(va, 0x200000, GART_BASE), 1u,
		 "B4: exactly 2MiB entry count");
	CHECK_EQ(rx550_pdb0_entries_for(va, 0x200001, GART_BASE), 2u,
		 "B4: 2MiB+1 entry count");
	CHECK_EQ(rx550_pdb0_entries_for(va + 0x1FFF000, 0x200000, GART_BASE), 2u,
		 "B4: unaligned span entry count");
	CHECK_EQ(rx550_pdb0_entries_for(GART_BASE - 1u, 20u, GART_BASE),
		 RX550_VM_NO_INDEX, "B4: below window accepted (entries)");
	CHECK_EQ(rx550_pdb0_entries_for(va, 0u, GART_BASE),
		 RX550_VM_NO_INDEX, "B4: zero size accepted");
}

/* ---- C1: identity mapping, bounded by the 40-bit PA field. */
static void t_phys(void)
{
	uint64_t pa = 0;

	CHECK_RC(rx550_pdb0_phys_for_index(0, GART_BASE, &pa), RX550_OK,
		 "C1: index 0");
	CHECK_EQ(pa, GART_BASE & RX550_PTE_ADDR_MASK, "C1: index 0 PA");
	CHECK_RC(rx550_pdb0_phys_for_index(1, GART_BASE, &pa), RX550_OK,
		 "C1: index 1");
	CHECK_EQ(pa, (GART_BASE + 0x200000u) & RX550_PTE_ADDR_MASK, "C1: index 1 PA");
	CHECK(rx550_pdb0_phys_for_index(0, GART_BASE, 0) == RX550_EINVAL,
	      "C1: NULL out accepted");
	/* an index that would push the VA past the 46-bit field */
	CHECK(rx550_pdb0_phys_for_index(0xffffffffu, GART_BASE, &pa)
	      == RX550_EBOUNDS, "C1: out-of-field index accepted");
}

int main(void)
{
	printf("rx550-vm GFX8 PDB0/PTE model (software only, no MMIO)\n");

	t_pdb0_flags();
	t_entry();
	t_geometry();
	t_index();
	t_phys();

	printf("passed=%u failed=%u\n", g_pass, g_fail);
	return g_fail ? 1 : 0;
}
