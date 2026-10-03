/* rx550_addr_test.c — static/unit tests for the GFX8 address & buffer model.
 * No hardware, no allocation, no DRM.  Assertions compare concrete values
 * and return codes, not symbol presence — except the two audits at the end,
 * whose entire purpose is to assert ABSENCE. */

#include "rx550_addr.h"

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

#define CHECKF(cond, fmt, ...)                                                 \
	do {                                                                   \
		if (cond) {                                                     \
			g_pass++;                                            \
		} else {                                                        \
			g_fail++;                                            \
			printf("  FAIL %s:%d  " fmt "\n", __FILE__, __LINE__, \
			       __VA_ARGS__);                                   \
		}                                                              \
	} while (0)

/* Evaluates `got` exactly ONCE.  A macro that expands its argument into both
 * the comparison and the message re-evaluates side-effecting calls, which
 * silently corrupts any state machine under test. */
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

/* A GART window placed at the top of a 1 TiB MC space, as
 * amdgpu_gmc.c:314 does: gart_start = max_mc_address - gart_size + 1. */
#define GART_BASE UINT64_C(0x000000FFC0000000)   /* 1 TiB - 256 MiB      */
#define GART_SIZE (UINT64_C(256) << 20)

/* ------------------------------------------------------------- window */
static void t_window(void)
{
	struct rx550_gart_window w = { GART_BASE, GART_SIZE };

	CHECK(rx550_gart_window_valid(&w) == 1, "T1: valid window rejected");
	CHECK(rx550_gart_window_valid(0) == 0, "T1: NULL window accepted");

	w.size = 0u;
	CHECK(rx550_gart_window_valid(&w) == 0, "T1: zero-size window accepted");

	/* base beyond the 46-bit field: a window that could only ever hold
	 * unencodable addresses must be refused at construction. */
	w.base = RX550_GART_ADDR_MASK + 1u;
	w.size = 4096u;
	CHECK(rx550_gart_window_valid(&w) == 0, "T1: out-of-field base accepted");

	/* base + size - 1 must not wrap past the field */
	w.base = RX550_GART_ADDR_MASK - 4095u;
	w.size = 8192u;
	CHECK(rx550_gart_window_valid(&w) == 0, "T1: wrapping window accepted");

	w.base = GART_BASE;
	w.size = GART_SIZE;
	CHECK(rx550_gart_window_valid(&w) == 1, "T1: restored window rejected");
}

/* ------------------------------------------------------------ alloc */
static void t_alloc(void)
{
	struct rx550_buf_ctx ctx;
	struct rx550_buf b;
	struct rx550_buf other;

	rx550_buf_ctx_init(&ctx, GART_BASE, GART_SIZE);
	memset(&b, 0, sizeof(b));

	CHECK_RC(rx550_buf_alloc(&ctx, &b, 256u, 4u, RX550_DOM_GTT, 0u),
		 RX550_OK, "T2: alloc GTT");
	CHECK(b.state == RX550_BUF_ALLOCATED, "T2: state after alloc");
	CHECK(b.domain == RX550_DOM_GTT, "T2: domain not recorded");
	CHECK(b.gpu_space == RX550_AS_NONE, "T2: gpu_space set before publish");
	CHECK(b.cpu_space == RX550_AS_NONE, "T2: cpu_space set before attach");
	CHECK(b.owner != 0u, "T2: owner id not allocated");
	CHECK(rx550_buf_size(&b) == 256, "T2: size query");
	CHECK(rx550_buf_usable_dw(&b) == 64, "T2: usable_dw (256/4)");

	/* owner ids are monotonic and distinct */
	CHECK(rx550_buf_alloc(&ctx, &other, 256u, 4u, RX550_DOM_GTT, 0u)
	      == RX550_OK, "T2: second alloc");
	CHECK(other.owner != b.owner, "T2: owner id reused");

	/* rejections */
	{
		struct rx550_buf z;

		memset(&z, 0, sizeof(z));
		CHECK_RC(rx550_buf_alloc(0, &z, 256u, 4u, RX550_DOM_GTT, 0u),
			 RX550_EINVAL, "T3: NULL ctx");
		CHECK_RC(rx550_buf_alloc(&ctx, 0, 256u, 4u, RX550_DOM_GTT, 0u),
			 RX550_EINVAL, "T3: NULL buf");
		CHECK_RC(rx550_buf_alloc(&ctx, &z, 0u, 4u, RX550_DOM_GTT, 0u),
			 RX550_EINVAL, "T3: zero size");

		memset(&z, 0, sizeof(z));
		CHECK_RC(rx550_buf_alloc(&ctx, &z, 256u, 3u, RX550_DOM_GTT, 0u),
			 RX550_EINVAL, "T3: non-pow2 alignment");
		CHECK_RC(rx550_buf_alloc(&ctx, &z, 256u, 0u, RX550_DOM_GTT, 0u),
			 RX550_EINVAL, "T3: zero alignment");

		/* GTT must meet the descriptor granularity; VRAM is not bound
		 * by the descriptor field. */
		memset(&z, 0, sizeof(z));
		CHECK_RC(rx550_buf_alloc(&ctx, &z, 256u, 2u, RX550_DOM_GTT, 0u),
			 RX550_EALIGN, "T3: GTT below 4-byte alignment");
		memset(&z, 0, sizeof(z));
		CHECK_RC(rx550_buf_alloc(&ctx, &z, 256u, 2u, RX550_DOM_VRAM, 0u),
			 RX550_OK, "T3: VRAM wrongly bound by descriptor rule");

		memset(&z, 0, sizeof(z));
		CHECK_RC(rx550_buf_alloc(&ctx, &z, 256u, 4u, RX550_DOM_NONE, 0u),
			 RX550_EINVAL, "T3: untyped domain");
	}
}

/* ------------------------------------------------------------ publish */
static uint32_t storage[64];

static void t_publish(void)
{
	struct rx550_buf_ctx ctx;
	struct rx550_buf b, fresh;
	int dummy = 0;

	rx550_buf_ctx_init(&ctx, GART_BASE, GART_SIZE);

	/* A buffer that was never allocated is EMPTY: publishing and attaching
	 * to it are state errors, not success. */
	memset(&fresh, 0, sizeof(fresh));
	CHECK(fresh.state == RX550_BUF_EMPTY, "T4: zeroed buffer is not EMPTY");
	CHECK_RC(rx550_buf_publish(&fresh, GART_BASE, RX550_AS_GPU_GART),
		 RX550_ESTATE, "T4: publish of EMPTY state");
	CHECK_RC(rx550_buf_attach_cpu(&fresh, storage, RX550_AS_CPU_VA),
		 RX550_ESTATE, "T4: attach of EMPTY state");
	CHECK_RC(rx550_buf_release(&fresh, 1u), RX550_ESTATE,
		 "T4: release of EMPTY state");

	memset(&b, 0, sizeof(b));
	CHECK(rx550_buf_alloc(&ctx, &b, 256u, 256u, RX550_DOM_GTT, 0u)
	      == RX550_OK, "T4: alloc");
	CHECK(b.state == RX550_BUF_ALLOCATED, "T4: state after alloc");

	CHECK_RC(rx550_buf_attach_cpu(&b, storage, RX550_AS_CPU_VA),
		 RX550_OK, "T4: attach CPU");
	CHECK(b.cpu_space == RX550_AS_CPU_VA, "T4: cpu_space recorded");
	CHECK_RC(rx550_buf_attach_cpu(&b, storage, RX550_AS_PCI_BAR),
		 RX550_EINVAL, "T4: BAR accepted as CPU space");
	CHECK_RC(rx550_buf_attach_cpu(&b, 0, RX550_AS_CPU_VA),
		 RX550_EINVAL, "T4: NULL cpu_ptr");
	CHECK(b.cpu_space == RX550_AS_CPU_VA, "T4: cpu_space clobbered by rejects");

	/* address below the window is encodable but not inside it */
	memset(&b, 0, sizeof(b));
	CHECK(rx550_buf_alloc(&ctx, &b, 256u, 256u, RX550_DOM_GTT, 0u)
	      == RX550_OK, "T5: alloc");
	CHECK_RC(rx550_buf_publish(&b, GART_BASE - 4096u, RX550_AS_GPU_GART),
		 RX550_OK, "T5: publish below window base");
	CHECK(rx550_buf_address_in_window(&b, &ctx.gart) == 0,
	      "T5: address below window reported as inside");
	CHECK(rx550_buf_addr_encodable(&b) == 1,
	      "T5: below-window address wrongly reported unencodable");

	/* a BAR address is not a GPU address the descriptor can carry */
	memset(&b, 0, sizeof(b));
	CHECK(rx550_buf_alloc(&ctx, &b, 256u, 256u, RX550_DOM_GTT, 0u)
	      == RX550_OK, "T5: alloc");
	CHECK_RC(rx550_buf_publish(&b, GART_BASE, RX550_AS_PCI_BAR),
		 RX550_EINVAL, "T5: BAR accepted as GPU space");
	CHECK(b.state == RX550_BUF_ALLOCATED,
	      "T5: rejected publish changed state");

	/* misaligned GART address */
	memset(&b, 0, sizeof(b));
	CHECK(rx550_buf_alloc(&ctx, &b, 256u, 256u, RX550_DOM_GTT, 0u)
	      == RX550_OK, "T5: alloc");
	CHECK_RC(rx550_buf_publish(&b, GART_BASE + 2u, RX550_AS_GPU_GART),
		 RX550_EALIGN, "T5: misaligned GART address accepted");

	/* the real publish */
	memset(&b, 0, sizeof(b));
	CHECK(rx550_buf_alloc(&ctx, &b, 256u, 256u, RX550_DOM_GTT, 0u)
	      == RX550_OK, "T6: alloc");
	CHECK_RC(rx550_buf_publish(&b, GART_BASE + 256u, RX550_AS_GPU_GART),
		 RX550_OK, "T6: publish");
	CHECK(rx550_buf_is_published(&b) == 1, "T6: not published");
	CHECK(b.gpu_va == GART_BASE + 256u, "T6: gpu_va recorded");
	CHECK(b.gpu_space == RX550_AS_GPU_GART, "T6: gpu_space recorded");
	CHECK(rx550_buf_address_in_window(&b, &ctx.gart) == 1,
	      "T6: published address not in window");
	CHECK(rx550_buf_addr_encodable(&b) == 1, "T6: published not encodable");

	/* re-publishing an already published buffer is a state error */
	CHECK_RC(rx550_buf_publish(&b, GART_BASE + 512u, RX550_AS_GPU_GART),
		 RX550_ESTATE, "T6: re-publish of PUBLISHED state");
	CHECK(b.gpu_va == GART_BASE + 256u, "T6: gpu_va changed by failed re-publish");

	/* past the window end */
	memset(&b, 0, sizeof(b));
	CHECK(rx550_buf_alloc(&ctx, &b, 256u, 256u, RX550_DOM_GTT, 0u)
	      == RX550_OK, "T7: alloc");
	CHECK_RC(rx550_buf_publish(&b, GART_BASE + GART_SIZE, RX550_AS_GPU_GART),
		 RX550_OK, "T7: one-past-end address accepted by publish");
	CHECK(rx550_buf_address_in_window(&b, &ctx.gart) == 0,
	      "T7: one-past-end reported as inside");

	/* beyond the 46-bit field.  MASK+1 == 2^46, which is both 4-aligned and
	 * out of range, so it isolates the bounds check. */
	memset(&b, 0, sizeof(b));
	CHECK(rx550_buf_alloc(&ctx, &b, 256u, 256u, RX550_DOM_GTT, 0u)
	      == RX550_OK, "T7: alloc");
	CHECK_RC(rx550_buf_publish(&b, RX550_GART_ADDR_MASK + 1u,
				   RX550_AS_GPU_GART),
		 RX550_EBOUNDS, "T7: address beyond 46-bit field accepted");

	/* An address that is BOTH misaligned and out of range: the encoder
	 * checks alignment first, and that precedence is part of the
	 * contract, so it is asserted rather than left to chance. */
	memset(&b, 0, sizeof(b));
	CHECK(rx550_buf_alloc(&ctx, &b, 256u, 256u, RX550_DOM_GTT, 0u)
	      == RX550_OK, "T7: alloc");
	CHECK_RC(rx550_buf_publish(&b, RX550_GART_ADDR_MASK + 4u,
				   RX550_AS_GPU_GART),
		 RX550_EALIGN, "T7: precedence of alignment over bounds");

	/* a VRAM physical address is not encodable by the descriptor */
	memset(&b, 0, sizeof(b));
	CHECK(rx550_buf_alloc(&ctx, &b, 256u, 256u, RX550_DOM_VRAM, 0u)
	      == RX550_OK, "T8: VRAM alloc");
	CHECK_RC(rx550_buf_publish(&b, 0x1000u, RX550_AS_GPU_VRAM_PA),
		 RX550_OK, "T8: VRAM publish");
	CHECK(rx550_buf_addr_encodable(&b) == 0,
	      "T8: VRAM address reported as descriptor-encodable");
	CHECK(rx550_buf_address_in_window(&b, &ctx.gart) == 0,
	      "T8: VRAM address reported as GART");
	(void)dummy;
}

/* ------------------------------------------------------------ ownership */
static void t_ownership(void)
{
	struct rx550_buf_ctx ctx;
	struct rx550_buf b;

	rx550_buf_ctx_init(&ctx, GART_BASE, GART_SIZE);
	memset(&b, 0, sizeof(b));
	CHECK(rx550_buf_alloc(&ctx, &b, 256u, 256u, RX550_DOM_GTT, 0u)
	      == RX550_OK, "T9: alloc");

	/* re-allocating a live buffer would silently discard the existing
	 * owner and address, so it must be refused while the buffer is live. */
	CHECK_RC(rx550_buf_alloc(&ctx, &b, 512u, 256u, RX550_DOM_GTT, 0u),
		 RX550_ESTATE, "T9: re-alloc of ALLOCATED buffer");
	CHECK(rx550_buf_size(&b) == 256, "T9: size changed by refused re-alloc");

	/* attach a real CPU pointer so the release-time clear is observable */
	CHECK_RC(rx550_buf_attach_cpu(&b, storage, RX550_AS_CPU_VA),
		 RX550_OK, "T9: attach CPU");
	CHECK(b.cpu_ptr == storage, "T9: cpu_ptr not recorded");

	CHECK_RC(rx550_buf_release(&b, 0u), RX550_EOWNER,
		 "T9: release by unowned id accepted");
	CHECK_RC(rx550_buf_release(&b, b.owner + 1u), RX550_EOWNER,
		 "T9: release by wrong owner accepted");
	CHECK(b.state == RX550_BUF_ALLOCATED, "T9: state changed by failed release");

	CHECK_RC(rx550_buf_release(&b, b.owner), RX550_OK, "T9: release by owner");
	CHECK(b.state == RX550_BUF_RELEASED, "T9: state after release");
	CHECK(b.cpu_ptr == 0, "T9: cpu_ptr not cleared on release");
	CHECK(rx550_buf_is_published(&b) == 0, "T9: released reported published");

	/* double release and post-release use must be errors */
	CHECK_RC(rx550_buf_release(&b, b.owner), RX550_ESTATE, "T9: double release");
	CHECK_RC(rx550_buf_publish(&b, GART_BASE, RX550_AS_GPU_GART),
		 RX550_ESTATE, "T9: publish after release");
	CHECK_RC(rx550_buf_attach_cpu(&b, storage, RX550_AS_CPU_VA),
		 RX550_ESTATE, "T9: attach after release");

	/* explicit external owner is honoured */
	memset(&b, 0, sizeof(b));
	CHECK(rx550_buf_alloc(&ctx, &b, 256u, 256u, RX550_DOM_GTT, 77u)
	      == RX550_OK, "T9: alloc with explicit owner");
	CHECK(b.owner == 77u, "T9: explicit owner not honoured");
	CHECK_RC(rx550_buf_release(&b, 78u), RX550_EOWNER,
		 "T9: wrong owner on explicit-owner buffer");
	CHECK_RC(rx550_buf_release(&b, 77u), RX550_OK, "T9: explicit owner release");
}

/* ------------------------------------------- contract with the PM4 encoder
 * The PM4 component enforces: 46-bit field, 4-byte granularity, and that
 * the buffer is published.  This model must agree with it exactly. */
static void t_pm4_contract(void)
{
	struct rx550_buf_ctx ctx;
	struct rx550_buf b;

	rx550_buf_ctx_init(&ctx, GART_BASE, GART_SIZE);

	/* a) allocated but never published: not encodable */
	memset(&b, 0, sizeof(b));
	CHECK(rx550_buf_alloc(&ctx, &b, 256u, 256u, RX550_DOM_GTT, 0u)
	      == RX550_OK, "T10: alloc");
	CHECK(rx550_buf_addr_encodable(&b) == 0, "T10: unpublished encodable");

	/* b) largest GART address the field can carry, 4-aligned */
	memset(&b, 0, sizeof(b));
	CHECK(rx550_buf_alloc(&ctx, &b, 256u, 256u, RX550_DOM_GTT, 0u)
	      == RX550_OK, "T10: alloc");
	CHECK_RC(rx550_buf_publish(&b, RX550_GART_ADDR_MASK - 3u,
				   RX550_AS_GPU_GART),
		 RX550_OK, "T10: max encodable address");
	CHECK(rx550_buf_addr_encodable(&b) == 1, "T10: max address not encodable");

	/* c) the same value minus 1 is misaligned AND unencodable */
	memset(&b, 0, sizeof(b));
	CHECK(rx550_buf_alloc(&ctx, &b, 256u, 256u, RX550_DOM_GTT, 0u)
	      == RX550_OK, "T10: alloc");
	CHECK_RC(rx550_buf_publish(&b, RX550_GART_ADDR_MASK - 1u,
				   RX550_AS_GPU_GART),
		 RX550_EALIGN, "T10: misaligned max accepted");
	CHECK(rx550_buf_addr_encodable(&b) == 0, "T10: unaligned reported encodable");

	/* d) the whole window lies inside the 46-bit field, so every address
	 *    the window can yield is descriptor-encodable.  If this ever
	 *    becomes false, encodability stops being implied by window
	 *    membership and the two checks must be consulted separately. */
	CHECK(GART_BASE + GART_SIZE <= RX550_GART_ADDR_MASK,
	      "T10: window no longer inside the 46-bit field");
	CHECK(rx550_gart_window_valid(&ctx.gart) == 1,
	      "T10: window under test is not valid");
}

/* ------------------------------------------------------------- audits */
static void strip_comments(char *s)
{
	char *r = s, *w = s;
	int blk = 0, line = 0, str = 0;

	while (*r) {
		if (blk) {
			if (r[0] == '*' && r[1] == '/') { blk = 0; r += 2; }
			else r++;
			continue;
		}
		if (line) {
			if (*r == '\n') { line = 0; *w++ = *r; }
			r++;
			continue;
		}
		if (!str && r[0] == '/' && r[1] == '*') { blk = 1; r += 2; continue; }
		if (!str && r[0] == '/' && r[1] == '/') { line = 1; r += 2; continue; }
		if (*r == '"') str = !str;
		*w++ = *r;
		r++;
	}
	*w = '\0';
}

/* This component must not reach into the PM4 encoder, and must not name any
 * hardware API.  Both are ABSENCE assertions; a comment is not a reference. */
static const char *const forbidden[] = {
	"ioremap", "iounmap", "readl", "writel", "__iomem", "pci_", "dma_",
	"mmio", "MMIO", "doorbell", "DOORBELL", "wptr", "WPTR", "kmalloc",
	"vmalloc", "GFP_", "request_irq", "kprobe", "no_hw_access",
	"pm4.h", "rx550_pm4_", "drm_", "amdgpu_", "ttm",
};

static int scan(const char *path)
{
	static char buf[65536];
	size_t n;
	FILE *f = fopen(path, "rb");
	int bad = 0;

	if (!f) {
		printf("  FAIL audit: cannot open %s\n", path);
		g_fail++;
		return 1;
	}
	n = fread(buf, 1, sizeof(buf) - 1, f);
	buf[n] = '\0';
	fclose(f);
	strip_comments(buf);

	for (size_t i = 0; i < sizeof(forbidden) / sizeof(forbidden[0]); i++) {
		if (strstr(buf, forbidden[i])) {
			printf("  FAIL audit: %s code references '%s'\n", path,
			       forbidden[i]);
			bad = 1;
		}
	}
	return bad;
}

static void t_audits(void)
{
	int bad = 0;

	bad |= scan("rx550_addr.h");
	bad |= scan("rx550_addr.c");
	CHECK(!bad, "T11: forbidden reference in component source");

	/* Numeric contract: these must not drift away from the PM4 encoder. */
	CHECK(RX550_GART_ADDR_BITS == 46u, "T12: GART addr bits drifted");
	CHECK(RX550_IB_ALIGN_MIN == 4u, "T12: IB align drifted");
	CHECK(RX550_IB_POOL_ALIGN == 256u, "T12: pool align drifted");
	CHECK(RX550_GART_SIZE_DEFAULT_MB == 256u, "T12: default gart size drifted");
	CHECK(RX550_GART_SIZE_4GBPG_MB == 1024u, "T12: 4GBpg gart size drifted");
}

int main(void)
{
	printf("rx550-mem GFX8 address/buffer model (software only, no hardware)\n");

	t_window();      /* T1 */
	t_alloc();       /* T2 T3 */
	t_publish();     /* T4 T5 T6 T7 T8 */
	t_ownership();   /* T9 */
	t_pm4_contract();/* T10 */
	t_audits();      /* T11 T12 */

	printf("passed=%u failed=%u\n", g_pass, g_fail);
	return g_fail ? 1 : 0;
}
