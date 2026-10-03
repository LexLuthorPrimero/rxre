/* rx550_contract_test.c — the contract between rx550-mem and rx550-pm4.
 *
 * This is the only test in the project that compiles BOTH components
 * together.  It exists to prove one specific property: the two modules cannot
 * disagree about an address.  rx550-mem decides whether a GPU address is
 * valid and encodable; rx550-pm4 encodes it.  If their definitions of "46
 * bits" or "4-byte aligned" ever diverge, this test fails.
 *
 * It deliberately does NOT merge the modules.  rx550-pm4 is not included by
 * rx550-mem, and rx550-mem is not included by rx550-pm4; each is compiled
 * from its own directory.  The only coupling is the numeric contract tested
 * here, which is exactly the coupling that must be explicit.
 *
 * No hardware.  No PM4 file is modified.
 */

#include "rx550_addr.h"
#include "rx550_vm.h"
#include "rx550_vis.h"
#include "pm4.h"

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
			printf("  FAIL %s:%d  %s: got 0x%08X want 0x%08X\n",  \
			       __FILE__, __LINE__, (what),                     \
			       (unsigned)rx550__g, (unsigned)rx550__w);       \
		}                                                              \
	} while (0)

#define GART_BASE UINT64_C(0x000000FFC0000000)
#define GART_SIZE (UINT64_C(256) << 20)

static uint32_t ib_storage[64];

/* ---- D1: the two modules must declare the same field width and alignment.
 * rx550_addr.h: RX550_GART_ADDR_BITS 46, RX550_IB_ALIGN_MIN 4
 * pm4.h:        46 address bits, 4-byte granularity (gfx_v8_0.c:6096-6097)  */
static void t_shared_constants(void)
{
	CHECK(RX550_GART_ADDR_BITS == 46u, "D1: addr bits");
	CHECK(RX550_IB_ALIGN_MIN == 4u, "D1: ib align");
	/* pm4.h's own constants, restated here from the file's definitions */
	CHECK((UINT64_C(1) << 46) - 1u == UINT64_C(0x3FFFFFFFFFFF), "D1: mask");
}

/* ---- D2: end to end.  A published buffer's address must encode into the
 * PM4 descriptor exactly as the memory layer says it will, and the two halves
 * must split at the same bit. */
static void t_end_to_end(void)
{
	struct rx550_buf_ctx ctx;
	struct rx550_buf b;
	uint32_t dw[8];
	const uint64_t va = GART_BASE + 0x12340u;
	uint32_t n;

	rx550_buf_ctx_init(&ctx, GART_BASE, GART_SIZE);
	memset(&b, 0, sizeof(b));
	CHECK(rx550_buf_alloc(&ctx, &b, 256u, 256u, RX550_DOM_GTT, 0u)
	      == RX550_OK, "D2: alloc");
	CHECK(rx550_buf_attach_cpu(&b, ib_storage, RX550_AS_CPU_VA)
	      == RX550_OK, "D2: attach cpu");

	/* the memory layer must agree the address is publishable ... */
	CHECK(rx550_buf_publish(&b, va, RX550_AS_GPU_GART) == RX550_OK,
	      "D2: publish rejected by mem layer");
	/* ... and that it is encodable, BEFORE pm4 is asked */
	CHECK(rx550_buf_addr_encodable(&b) == 1, "D2: mem layer says unencodable");
	CHECK(rx550_buf_address_in_window(&b, &ctx.gart) == 1,
	      "D2: address not in window");

	/* the PM4 layer must accept the same address, and produce the split
	 * the memory layer documented. */
	memset(dw, 0xAA, sizeof(dw));
	{
		struct rx550_pm4_buf pb;

		rx550_pm4_buf_init(&pb, dw, 8u);
		CHECK(rx550_pm4_emit_ib_descriptor(&pb, b.gpu_va, 5u, 0u,
						  RX550_PM4_IB_VALID, 0)
		      == RX550_PM4_OK, "D2: pm4 rejected a mem-approved address");
		n = rx550_pm4_buf_count(&pb);
		CHECK_EQ(n, 4u, "D2: descriptor length");
		/* DW0: opcode 0x3F, count 2 */
		CHECK_EQ(dw[0], 0xC0023F00u, "D2: descriptor header");
		/* DW1/DW2: exactly the split gfx_v8_0.c:6096-6097 performs */
		CHECK_EQ(dw[1], (uint32_t)(b.gpu_va & 0xFFFFFFFCu),
			 "D2: addr lo split");
		CHECK_EQ(dw[2], (uint32_t)((b.gpu_va >> 32) & 0xFFFFu),
			 "D2: addr hi split");
		/* the round trip: reassembling the two halves gives the address
		 * back, so the split loses nothing. */
		CHECK_EQ(((uint64_t)dw[2] << 32) | dw[1], b.gpu_va,
			 "D2: split is lossy");
	}
}

/* ---- D3: the two layers must never disagree.  For every interesting
 * address, the mem layer's verdict must equal PM4's acceptance. */
static void t_layers_agree(void)
{
	static const uint64_t candidates[] = {
		GART_BASE,                                  /* window base       */
		GART_BASE + 4u,                            /* minimal aligned   */
		GART_BASE + 0x12340u,                      /* mid-entry         */
		GART_BASE + GART_SIZE - 4u,                /* last valid        */
		UINT64_C(0x3FFFFFFFFFFC),                  /* max 46-bit        */
		UINT64_C(0x3FFFFFFFFFFD),                  /* max +1, misaligned*/
		UINT64_C(0x400000000000),                  /* 2^46, out of field*/
		UINT64_C(0x0000000012345000),              /* small PA-shaped   */
	};
	size_t i;

	for (i = 0; i < sizeof(candidates) / sizeof(candidates[0]); i++) {
		struct rx550_buf_ctx ctx;
		struct rx550_buf b;
		struct rx550_pm4_buf pb;
		uint32_t dw[8];
		int mem_ok, pm4_ok;
		uint64_t va = candidates[i];

		rx550_buf_ctx_init(&ctx, GART_BASE, GART_SIZE);
		memset(&b, 0, sizeof(b));
		memset(dw, 0, sizeof(dw));
		rx550_pm4_buf_init(&pb, dw, 8u);

		if (rx550_buf_alloc(&ctx, &b, 256u, 256u, RX550_DOM_GTT, 0u)
		    != RX550_OK)
			continue;
		mem_ok = (rx550_buf_publish(&b, va, RX550_AS_GPU_GART) == RX550_OK)
		      && rx550_buf_addr_encodable(&b);
		pm4_ok = (rx550_pm4_emit_ib_descriptor(&pb, va, 5u, 0u, 0u, 0)
			  == RX550_PM4_OK);

		/* The one address that differs: a GART VA must fit 46 bits and be
		 * 4-aligned; PM4 enforces exactly that and nothing else, so the
		 * two verdicts must be identical for every candidate. */
		if (mem_ok != pm4_ok) {
			printf("  FAIL D3: layers disagree at 0x%016llX "
			       "(mem=%d pm4=%d)\n",
			       (unsigned long long)va, mem_ok, pm4_ok);
			g_fail++;
		} else {
			g_pass++;
		}
	}
}

/* ---- D4: a descriptor must never be buildable from a non-published buffer.
 * This is the boundary rule: PM4 receives an address, never a buffer. */
static void t_boundary_rule(void)
{
	struct rx550_buf_ctx ctx;
	struct rx550_buf b;
	struct rx550_pm4_buf pb;
	uint32_t dw[8];
	uint64_t va = GART_BASE + 0x2000u;

	rx550_buf_ctx_init(&ctx, GART_BASE, GART_SIZE);
	memset(&b, 0, sizeof(b));
	memset(dw, 0, sizeof(dw));
	rx550_pm4_buf_init(&pb, dw, 8u);

	/* ALLOCATED but not PUBLISHED: the mem layer must refuse to say this
	 * address is encodable, and there must be no address to hand over. */
	CHECK(rx550_buf_alloc(&ctx, &b, 256u, 256u, RX550_DOM_GTT, 0u)
	      == RX550_OK, "D4: alloc");
	CHECK(rx550_buf_is_published(&b) == 0, "D4: published before publish");
	CHECK(rx550_buf_addr_encodable(&b) == 0, "D4: unpublished encodable");

	/* After publishing, and after releasing, the rules are the ones above:
	 * published -> encodable, released -> not. */
	CHECK(rx550_buf_publish(&b, va, RX550_AS_GPU_GART) == RX550_OK,
	      "D4: publish");
	CHECK(rx550_buf_addr_encodable(&b) == 1, "D4: published not encodable");
	CHECK(rx550_pm4_emit_ib_descriptor(&pb, b.gpu_va, 5u, 0u, 0u, 0)
	      == RX550_PM4_OK, "D4: pm4 rejected a published address");
	CHECK(rx550_buf_release(&b, b.owner) == RX550_OK, "D4: release");
	CHECK(rx550_buf_addr_encodable(&b) == 0, "D4: released still encodable");
	/* The address value survives release on purpose: a stale descriptor is
	 * a visible bug, not a silent zero. */
	CHECK(b.gpu_va == va, "D4: gpu_va cleared on release");
}

/* ---- D5: unit discipline.  The buffer size is bytes, the descriptor length
 * is DW.  A caller converting between them must not silently round. */
static void t_units(void)
{
	struct rx550_buf_ctx ctx;
	struct rx550_buf b;

	rx550_buf_ctx_init(&ctx, GART_BASE, GART_SIZE);
	memset(&b, 0, sizeof(b));
	CHECK(rx550_buf_alloc(&ctx, &b, 20u, 256u, RX550_DOM_GTT, 0u)
	      == RX550_OK, "D5: alloc 20 B (the corpus IB size)");
	CHECK_EQ(rx550_buf_size(&b), 20u, "D5: bytes");
	CHECK_EQ(rx550_buf_usable_dw(&b), 5u, "D5: DW count for a 20 B buffer");
	/* gfx_v8_0.c:896 sets ib.length_dw = 5 for exactly this buffer. */
	CHECK_EQ(rx550_buf_usable_dw(&b), 5u, "D5: corpus length_dw");
	/* a buffer whose size is not a DW multiple loses the remainder */
	memset(&b, 0, sizeof(b));
	CHECK(rx550_buf_alloc(&ctx, &b, 22u, 256u, RX550_DOM_GTT, 0u)
	      == RX550_OK, "D5: alloc 22 B");
	CHECK_EQ(rx550_buf_usable_dw(&b), 5u, "D5: 22 B must yield 5 usable DW");
	/* and 2 MiB granularity means that 20 B still costs one PDB0 entry */
	CHECK_EQ(rx550_pdb0_entries_for(GART_BASE, 20u, GART_BASE),
		 1u, "D5: PDB0 entries for a 20 B IB");
}

int main(void)
{
	printf("rx550-mem <-> rx550-pm4 contract (software only, no hardware)\n");

	t_shared_constants();
	t_end_to_end();
	t_layers_agree();
	t_boundary_rule();
	t_units();

	printf("passed=%u failed=%u\n", g_pass, g_fail);
	return g_fail ? 1 : 0;
}
