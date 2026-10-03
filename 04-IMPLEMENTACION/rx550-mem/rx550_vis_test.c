/* rx550_vis_test.c — tests for the GFX8 CPU->GPU visibility contract.
 * Concrete DW values, concrete ordering results.  No hardware. */

#include "rx550_vis.h"

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
		uint32_t rx550__g = (uint32_t)(got);                           \
		uint32_t rx550__w = (uint32_t)(want);                          \
		if (rx550__g == rx550__w) {                                    \
			g_pass++;                                            \
		} else {                                                        \
			g_fail++;                                            \
			printf("  FAIL %s:%d  %s: got 0x%08X want 0x%08X\n",  \
			       __FILE__, __LINE__, (what), rx550__g, rx550__w);  \
		}                                                              \
	} while (0)

/* ---- A1: the gfx coherence packet, byte for byte.
 * gfx_v8_0.c:6761-6771:
 *   PACKET3(PACKET3_SURFACE_SYNC, 3) = 0xC0000000|0x4300|0x30000
 *   CP_COHER_CNTL  = TCL1|TC|SH_KCACHE|SH_ICACHE|TC_WB = 0x28C40000
 *   CP_COHER_SIZE  = 0xFFFFFFFF ; CP_COHER_BASE = 0 ; poll = 0x0A
 */
static void t_surface_sync(void)
{
	uint32_t p[RX550_ACQUIRE_MEM_DW];
	uint32_t n;

	memset(p, 0xAA, sizeof(p));
	n = rx550_vis_encode_mem_sync(RX550_RING_GFX, p, RX550_ACQUIRE_MEM_DW);
	CHECK_EQ(n, 5u, "A1: gfx packet length");
	CHECK_EQ(p[0], 0xC0034300u, "A1: SURFACE_SYNC header");
	CHECK_EQ(p[1], 0x28C40000u, "A1: CP_COHER_CNTL");
	CHECK_EQ(p[2], 0xFFFFFFFFu, "A1: CP_COHER_SIZE");
	CHECK_EQ(p[3], 0x00000000u, "A1: CP_COHER_BASE");
	CHECK_EQ(p[4], 0x0000000Au, "A1: poll interval");
	/* nothing past the packet may be touched */
	CHECK_EQ(p[5], 0xAAAAAAAAu, "A1: wrote past gfx packet");
	CHECK_EQ(p[6], 0xAAAAAAAAu, "A1: wrote past gfx packet (2)");
}

/* ---- A2: the compute coherence packet, byte for byte.
 * gfx_v8_0.c:6774-6783: PACKET3(PACKET3_ACQUIRE_MEM, 5) */
static void t_acquire_mem(void)
{
	uint32_t p[RX550_ACQUIRE_MEM_DW];
	uint32_t n;

	memset(p, 0xAA, sizeof(p));
	n = rx550_vis_encode_mem_sync(RX550_RING_COMPUTE, p, RX550_ACQUIRE_MEM_DW);
	CHECK_EQ(n, 7u, "A2: compute packet length");
	CHECK_EQ(p[0], 0xC0055800u, "A2: ACQUIRE_MEM header");
	CHECK_EQ(p[1], 0x28C40000u, "A2: CP_COHER_CNTL");
	CHECK_EQ(p[2], 0xFFFFFFFFu, "A2: CP_COHER_SIZE");
	CHECK_EQ(p[3], 0x000000FFu, "A2: CP_COHER_SIZE_HI");
	CHECK_EQ(p[4], 0x00000000u, "A2: CP_COHER_BASE");
	CHECK_EQ(p[5], 0x00000000u, "A2: CP_COHER_BASE_HI");
	CHECK_EQ(p[6], 0x0000000Au, "A2: poll interval");
}

/* ---- A3: opcodes and the coherence mask must not drift. */
static void t_constants(void)
{
	CHECK(RX550_OP_SURFACE_SYNC == 0x43u, "A3: SURFACE_SYNC drifted");
	CHECK(RX550_OP_ACQUIRE_MEM == 0x58u, "A3: ACQUIRE_MEM drifted");
	CHECK(RX550_COHER_CNTL == 0x28C40000u, "A3: COHER_CNTL drifted");
	CHECK(RX550_COHER_POLL == 0x0Au, "A3: poll drifted");
}

/* ---- A4: argument rejection, and no partial write. */
static void t_reject(void)
{
	uint32_t p[RX550_ACQUIRE_MEM_DW];

	CHECK_EQ(rx550_vis_encode_mem_sync(RX550_RING_GFX, 0, 8u), 0u,
		 "A4: NULL out accepted");
	/* a too-small destination must write nothing at all */
	memset(p, 0xAA, sizeof(p));
	CHECK_EQ(rx550_vis_encode_mem_sync(RX550_RING_COMPUTE, p, 4u), 0u,
		 "A4: undersized destination accepted");
	CHECK_EQ(p[0], 0xAAAAAAAAu, "A4: partial write on undersized destination");
	CHECK_EQ(rx550_vis_encode_mem_sync(RX550_RING_GFX, p, 4u), 0u,
		 "A4: gfx packet fits in 4 DW?");
	CHECK_EQ(p[0], 0xAAAAAAAAu, "A4: wrote despite rejecting");
}

/* ---- A5: the ordering invariant the corpus depends on.
 * amdgpu_ib.c:235 emits the sync, :283 emits the descriptor, so the sync
 * record starts strictly earlier.  Every inversion must be rejected. */
static void t_ordering(void)
{
	/* the corpus-shaped layout: sync at 0, descriptor at 5 */
	CHECK(rx550_vis_order_ok(0u, 5u) == 1, "A5: sync-then-descriptor rejected");
	/* sync at 0, descriptor at 5 is the only shape the reference produces
	 * for a 5-DW gfx packet, but any strict ordering is accepted */
	CHECK(rx550_vis_order_ok(3u, 8u) == 1, "A5: later sync rejected");
	CHECK(rx550_vis_order_ok(7u, 8u) == 1, "A5: adjacent sync rejected");

	/* descriptor before sync: the inversion this must catch */
	CHECK(rx550_vis_order_ok(5u, 0u) == 0, "A5: descriptor-before-sync accepted");
	CHECK(rx550_vis_order_ok(8u, 3u) == 0, "A5: inverted ordering accepted");
	/* equal: overlap, not ordering */
	CHECK(rx550_vis_order_ok(4u, 4u) == 0, "A5: overlapping records accepted");
	/* missing sync entirely */
	CHECK(rx550_vis_order_ok(RX550_VIS_ABSENT, 5u) == 0, "A5: absent sync accepted");
	/* missing descriptor */
	CHECK(rx550_vis_order_ok(0u, RX550_VIS_ABSENT) == 0,
	      "A5: absent descriptor accepted");
	CHECK(rx550_vis_order_ok(RX550_VIS_ABSENT, RX550_VIS_ABSENT) == 0,
	      "A5: both absent accepted");

	/* record lengths */
	{
		uint32_t len = 0;

		CHECK(rx550_vis_record(RX550_REC_MEM_SYNC, 0u, &len) == 0,
		      "A5: record offset not returned");
		CHECK_EQ(len, 5u, "A5: mem_sync record length");
		CHECK(rx550_vis_record(RX550_REC_IB_DESCRIPTOR, 5u, &len) == 5,
		      "A5: descriptor offset not returned");
		CHECK_EQ(len, 4u, "A5: ib descriptor record length");
		CHECK(rx550_vis_record(RX550_REC_IB_DESCRIPTOR, 5u, 0) == 5,
		      "A5: NULL out_dw_len accepted");
		CHECK(rx550_vis_record((enum rx550_ring_rec)99, 0u, &len)
		      == RX550_EINVAL, "A5: invalid record accepted");
	}
}

int main(void)
{
	printf("rx550-vis GFX8 CPU->GPU visibility contract (software only)\n");

	t_surface_sync();
	t_acquire_mem();
	t_constants();
	t_reject();
	t_ordering();

	printf("passed=%u failed=%u\n", g_pass, g_fail);
	return g_fail ? 1 : 0;
}
