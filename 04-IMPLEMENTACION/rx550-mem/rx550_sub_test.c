/* rx550_sub_test.c — tests for the GFX8 submission contract model.
 * Every assertion checks a concrete value or a concrete return code.
 * The execution-inference tests are the point of this file. */

#include "rx550_sub.h"

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
#define GART_SIZE (UINT64_C(256) << 20)

static uint32_t storage[16];

/* A published buffer, built through the memory layer so the address space
 * travels with it. */
static int published_buffer(struct rx550_buf_ctx *ctx, struct rx550_buf *b,
			    uint64_t va, uint32_t size)
{
	memset(b, 0, sizeof(*b));
	if (rx550_buf_alloc(ctx, b, size, 256u, RX550_DOM_GTT, 0u) != RX550_OK)
		return 0;
	if (rx550_buf_attach_cpu(b, storage, RX550_AS_CPU_VA) != RX550_OK)
		return 0;
	return rx550_buf_publish(b, va, RX550_AS_GPU_GART) == RX550_OK;
}

/* ---- 1: register offsets must match index*4 exactly. */
static void t_registers(void)
{
	/* Re-derived from gfx_8_0_d.h; the EP08 harness states the same nine
	 * values independently.  Agreement between two derivations is the
	 * check; the literals below are that agreement. */
	CHECK_EQ(RX550_REG_CP_RB0_RPTR,            0x8700u, "1: RPTR");
	CHECK_EQ(RX550_REG_CP_RB0_WPTR,            0xc114u, "1: WPTR");
	CHECK_EQ(RX550_REG_CP_RB_WPTR_POLL_ADDR_LO, 0xc118u, "1: POLL ADDR_LO");
	CHECK_EQ(RX550_REG_CP_RB_WPTR_POLL_ADDR_HI, 0xc11cu, "1: POLL ADDR_HI");
	CHECK_EQ(RX550_REG_CP_RB_WPTR_POLL_CNTL,   0x8708u, "1: POLL CNTL");
	CHECK_EQ(RX550_REG_CP_RB_DOORBELL_CONTROL, 0xc164u, "1: DOORBELL CONTROL");
	CHECK_EQ(RX550_REG_GRBM_STATUS,            0x8010u, "1: GRBM_STATUS");
	CHECK_EQ(RX550_REG_GRBM_STATUS2,           0x8008u, "1: GRBM_STATUS2");
	CHECK_EQ(RX550_REG_CP_BUSY_STAT,           0x867cu, "1: CP_BUSY_STAT");

	/* index*4 must be reconstructible: 0x21c0*4 = 0x8700, 0x3045*4 = 0xc114 */
	CHECK_EQ(0x21c0u * 4u, RX550_REG_CP_RB0_RPTR, "1: RPTR index*4");
	CHECK_EQ(0x3045u * 4u, RX550_REG_CP_RB0_WPTR, "1: WPTR index*4");
	CHECK_EQ(0x3059u * 4u, RX550_REG_CP_RB_DOORBELL_CONTROL,
		 "1: DOORBELL index*4");

	CHECK_EQ(RX550_DB_OFFSET_MASK, 0x7ffffcu, "1: DOORBELL_OFFSET mask");
	CHECK_EQ(RX550_DB_OFFSET_SHIFT, 2u, "1: DOORBELL_OFFSET shift");
	CHECK_EQ(RX550_DB_EN_MASK, 0x40000000u, "1: DOORBELL_EN mask");
	CHECK_EQ(RX550_DB_EN_SHIFT, 30u, "1: DOORBELL_EN shift");
	CHECK_EQ(RX550_DB_HIT_MASK, 0x80000000u, "1: DOORBELL_HIT mask");
	CHECK_EQ(RX550_DB_HIT_SHIFT, 31u, "1: DOORBELL_HIT shift");
}

/* ---- 2: creation takes a BUFFER, so the address space cannot be lost. */
static void t_create(void)
{
	struct rx550_buf_ctx ctx;
	struct rx550_buf b;
	struct rx550_submission s;

	rx550_buf_ctx_init(&ctx, GART_BASE, GART_SIZE);
	CHECK(published_buffer(&ctx, &b, GART_BASE + 0x400u, 20u), "2: setup");

	CHECK_RC(rx550_sub_create(&s, 7u, &b), RX550_OK, "2: create");
	CHECK(s.ib_gpu_va == GART_BASE + 0x400u, "2: ib_gpu_va");
	/* 20 bytes -> 5 DW, which is exactly gfx_v8_0.c:896 */
	CHECK_EQ(s.ib_length_dw, 5u, "2: ib_length_dw");
	CHECK(s.owner == 7u, "2: owner");
	CHECK(rx550_sub_state_get(&s) == RX550_SUB_CREATED, "2: initial state");

	/* an unpublished buffer cannot become a submission */
	{
		struct rx550_buf raw;

		memset(&raw, 0, sizeof(raw));
		CHECK(rx550_buf_alloc(&ctx, &raw, 20u, 256u, RX550_DOM_GTT, 0u)
		      == RX550_OK, "2: alloc");
		CHECK_RC(rx550_sub_create(&s, 7u, &raw), RX550_ESTATE,
			 "2: unpublished buffer accepted");
	}
	/* a VRAM buffer is published but not descriptor-encodable */
	{
		struct rx550_buf vram;

		memset(&vram, 0, sizeof(vram));
		CHECK(rx550_buf_alloc(&ctx, &vram, 20u, 256u, RX550_DOM_VRAM, 0u)
		      == RX550_OK, "2: vram alloc");
		CHECK(rx550_buf_publish(&vram, 0x1000u, RX550_AS_GPU_VRAM_PA)
		      == RX550_OK, "2: vram publish");
		CHECK_RC(rx550_sub_create(&s, 7u, &vram), RX550_EBOUNDS,
			 "2: VRAM address accepted for an IB descriptor");
	}
}

/* ---- 3: the full happy path, and monotonic WPTR. */
static void t_path(void)
{
	struct rx550_buf_ctx ctx;
	struct rx550_buf b;
	struct rx550_submission s;

	rx550_buf_ctx_init(&ctx, GART_BASE, GART_SIZE);
	CHECK(published_buffer(&ctx, &b, GART_BASE + 0x400u, 20u), "3: setup");
	CHECK_RC(rx550_sub_create(&s, 7u, &b), RX550_OK, "3: create");
	CHECK_RC(rx550_sub_mark_ready(&s), RX550_OK, "3: ready");
	CHECK(s.state == RX550_SUB_READY, "3: state READY");

	s.wptr_before = 0x100u;
	s.doorbell_configured = 1u;
	s.doorbell_published = 1u;
	CHECK_RC(rx550_sub_mark_published(&s, 0x120u), RX550_OK, "3: publish");
	CHECK(s.wptr_after == 0x120u, "3: wptr_after");
	CHECK(s.state == RX550_SUB_PUBLISHED, "3: state PUBLISHED");

	CHECK_RC(rx550_sub_mark_consumption(&s, 0x118u, 1), RX550_OK,
		 "3: consumption");
	CHECK(rx550_sub_claim_get(&s) == RX550_CLAIM_CONSUMPTION,
	      "3: claim must be CONSUMPTION");
	CHECK(rx550_sub_rptr_advanced(&s) == 1, "3: rptr_advanced");

	CHECK_RC(rx550_sub_mark_completed(&s, 1), RX550_OK, "3: completed");
	CHECK(s.state == RX550_SUB_COMPLETED, "3: state COMPLETED");
	CHECK_RC(rx550_sub_retire(&s, 7u), RX550_OK, "3: retire");
	CHECK(s.state == RX550_SUB_RETIRED, "3: state RETIRED");
}

/* ---- 4: RPTR that does not advance yields NO consumption claim. */
static void t_rptr_classification(void)
{
	struct rx550_buf_ctx ctx;
	struct rx550_buf b;
	struct rx550_submission s;

	rx550_buf_ctx_init(&ctx, GART_BASE, GART_SIZE);

	/* equal to wptr_before: no progress */
	CHECK(published_buffer(&ctx, &b, GART_BASE + 0x400u, 20u), "4: setup");
	CHECK_RC(rx550_sub_create(&s, 7u, &b), RX550_OK, "4: create");
	CHECK_RC(rx550_sub_mark_ready(&s), RX550_OK, "4: ready");
	s.wptr_before = 0x100u;
	CHECK_RC(rx550_sub_mark_published(&s, 0x120u), RX550_OK, "4: publish");
	CHECK_RC(rx550_sub_mark_consumption(&s, 0x100u, 1), RX550_OK,
		 "4: consumption step");
	CHECK(rx550_sub_claim_get(&s) == RX550_CLAIM_NONE,
	      "4: equal RPTR must yield NO claim");
	CHECK(rx550_sub_rptr_advanced(&s) == 0, "4: equal RPTR reported advanced");

	/* below wptr_before: the window says the CP went backwards */
	CHECK(published_buffer(&ctx, &b, GART_BASE + 0x400u, 20u), "4: setup 2");
	CHECK_RC(rx550_sub_create(&s, 7u, &b), RX550_OK, "4: create 2");
	CHECK_RC(rx550_sub_mark_ready(&s), RX550_OK, "4: ready 2");
	s.wptr_before = 0x100u;
	CHECK_RC(rx550_sub_mark_published(&s, 0x120u), RX550_OK, "4: publish 2");
	CHECK_RC(rx550_sub_mark_consumption(&s, 0x0F0u, 1), RX550_OK,
		 "4: consumption 2");
	CHECK(rx550_sub_claim_get(&s) == RX550_CLAIM_NONE,
	      "4: regressed RPTR must yield NO claim");
}

/* ---- 5: NO FALSE EXECUTION INFERENCE.  This is the load-bearing test.
 * A completed submission, with consumption observed, must still never
 * report execution — and no sequence of states may reach an EXECUTED claim. */
static void t_no_execution_inference(void)
{
	struct rx550_buf_ctx ctx;
	struct rx550_buf b;
	struct rx550_submission s;

	rx550_buf_ctx_init(&ctx, GART_BASE, GART_SIZE);
	CHECK(published_buffer(&ctx, &b, GART_BASE + 0x400u, 20u), "5: setup");
	CHECK_RC(rx550_sub_create(&s, 7u, &b), RX550_OK, "5: create");
	CHECK_RC(rx550_sub_mark_ready(&s), RX550_OK, "5: ready");
	s.wptr_before = 0u;
	CHECK_RC(rx550_sub_mark_published(&s, 0x120u), RX550_OK, "5: publish");
	CHECK_RC(rx550_sub_mark_consumption(&s, 0x120u, 1), RX550_OK,
		 "5: consumption");
	CHECK_RC(rx550_sub_mark_completed(&s, 1), RX550_OK, "5: completed");

	/* WPTR == RPTR == the end of the submission.  The corpus gives no
	 * observation that separates "consumed" from "executed", so the claim
	 * must be the weakest defensible one. */
	CHECK(s.wptr_after == 0x120u, "5: wptr");
	CHECK(s.rptr_observed == 0x120u, "5: rptr");
	CHECK_EQ(s.wptr_after, s.rptr_observed, "5: WPTR == RPTR");
	CHECK(rx550_sub_claim_get(&s) == RX550_CLAIM_CONSUMPTION,
	      "5: claim must stay CONSUMPTION");
	CHECK(rx550_sub_claim_get(&s) != RX550_CLAIM_EXECUTION,
	      "5: EXECUTION must be unreachable");
	CHECK(s.state != RX550_SUB_COMPLETED || rx550_sub_claim_get(&s)
	      != RX550_CLAIM_EXECUTION,
	      "5: completion must not imply execution");

	/* and there is no state, and no API, that could set it */
	CHECK_EQ(RX550_SUB_RETIRED, 5u, "5: RETIRED is the last state");
}

/* ---- 6: impossible transitions are refused. */
static void t_impossible(void)
{
	struct rx550_buf_ctx ctx;
	struct rx550_buf b;
	struct rx550_submission s;

	rx550_buf_ctx_init(&ctx, GART_BASE, GART_SIZE);
	CHECK(published_buffer(&ctx, &b, GART_BASE + 0x400u, 20u), "6: setup");
	CHECK_RC(rx550_sub_create(&s, 7u, &b), RX550_OK, "6: create");

	/* publish before ready */
	CHECK_RC(rx550_sub_mark_published(&s, 0x10u), RX550_ESTATE,
		 "6: publish before ready");
	/* consumption before publication */
	CHECK_RC(rx550_sub_mark_consumption(&s, 0x10u, 1), RX550_ESTATE,
		 "6: consumption before publication");
	/* completion before consumption */
	CHECK_RC(rx550_sub_mark_completed(&s, 1), RX550_ESTATE,
		 "6: completion before consumption");
	/* retire before anything */
	CHECK_RC(rx550_sub_retire(&s, 7u), RX550_ESTATE, "6: retire from CREATED");
	/* ready twice */
	CHECK_RC(rx550_sub_mark_ready(&s), RX550_OK, "6: ready");
	CHECK_RC(rx550_sub_mark_ready(&s), RX550_ESTATE, "6: ready twice");

	/* WPTR must strictly advance */
	s.wptr_before = 0x100u;
	CHECK_RC(rx550_sub_mark_published(&s, 0x100u), RX550_EALIGN,
		 "6: WPTR did not advance");
	CHECK_RC(rx550_sub_mark_published(&s, 0x0F0u), RX550_EALIGN,
		 "6: WPTR went backwards");
	CHECK_RC(rx550_sub_mark_published(&s, 0x101u), RX550_OK, "6: WPTR +1");

	/* an incomparable RPTR reading must be refused, not compared */
	CHECK_RC(rx550_sub_mark_consumption(&s, 0x999u, 0), RX550_ESTATE,
		 "6: incomparable reading accepted");
	CHECK(s.rptr_window_valid == 0, "6: rptr recorded from bad window");
	/* but the submission is still in PUBLISHED, so it can be retried */
	CHECK(s.state == RX550_SUB_PUBLISHED, "6: state damaged by refused read");
	CHECK_RC(rx550_sub_mark_consumption(&s, 0x101u, 1), RX550_OK,
		 "6: retry with comparable reading");

	/* completion requires a positive observation from the caller */
	CHECK_RC(rx550_sub_mark_completed(&s, 0), RX550_ESTATE,
		 "6: completion without observation");
	/* wrong owner */
	CHECK_RC(rx550_sub_retire(&s, 8u), RX550_EOWNER, "6: wrong owner retire");
	CHECK_RC(rx550_sub_retire(&s, 0u), RX550_EOWNER, "6: unowned retire");
	CHECK_RC(rx550_sub_retire(&s, 7u), RX550_OK, "6: owner retire");
	CHECK_RC(rx550_sub_retire(&s, 7u), RX550_ESTATE, "6: double retire");
}

/* ---- 7: WB publication is NOT a doorbell. */
static void t_doorbell_distinction(void)
{
	struct rx550_buf_ctx ctx;
	struct rx550_buf b;
	struct rx550_submission s;

	rx550_buf_ctx_init(&ctx, GART_BASE, GART_SIZE);
	CHECK(published_buffer(&ctx, &b, GART_BASE + 0x400u, 20u), "7: setup");
	CHECK_RC(rx550_sub_create(&s, 7u, &b), RX550_OK, "7: create");
	CHECK_RC(rx550_sub_mark_ready(&s), RX550_OK, "7: ready");
	s.wptr_before = 0u;
	/* CP_RB_DOORBELL_CONTROL was programmed at init ... */
	s.doorbell_configured = 1u;
	/* ... but no doorbell aperture write has happened yet. */
	CHECK_RC(rx550_sub_mark_published(&s, 0x10u), RX550_OK, "7: publish");
	CHECK(rx550_sub_doorbell_published(&s) == 0,
	      "7: WPTR publication reported as a doorbell");
	/* configuring the register does not publish anything */
	CHECK(s.doorbell_configured == 1, "7: config lost");
	CHECK(rx550_sub_doorbell_published(&s) == 0,
	      "7: config alone reported as a doorbell");

	s.doorbell_published = 1u;
	CHECK(rx550_sub_doorbell_published(&s) == 1, "7: doorbell not reported");
}

/* ---- 8: POLL_CNTL absence on the Polaris 12 path. */
static void t_poll(void)
{
	/* NOT an inference about polling semantics. Only whether the driver
	 * programs the register. */
	CHECK_EQ(rx550_sub_poll_cntl_value(1), 0u,
		 "8: POLARIS12 path must not program POLL_CNTL");
	CHECK_EQ(rx550_sub_poll_cntl_value(0), 0x00900100u,
		 "8: other GFX8 path value");
	CHECK(RX550_POLL_CNTL_TONGA_VALUE == 0x00900100u,
	      "8: Tonga POLL_CNTL value drifted");
}

int main(void)
{
	printf("rx550-sub GFX8 submission contract model (software only)\n");

	t_registers();
	t_create();
	t_path();
	t_rptr_classification();
	t_no_execution_inference();
	t_impossible();
	t_doorbell_distinction();
	t_poll();

	printf("passed=%u failed=%u\n", g_pass, g_fail);
	return g_fail ? 1 : 0;
}
