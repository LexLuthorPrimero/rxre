/* pm4_test.c — static/unit tests for the GFX8 PM4 command layer.
 *
 * Every assertion compares concrete DWORD values or return codes.  No test
 * asserts that a symbol, string or file merely exists, except T13 which
 * exists precisely to assert the ABSENCE of hardware API references.
 *
 * No hardware is touched, referenced or required.
 */

#include "pm4.h"

#include <stdio.h>
#include <string.h>

static unsigned g_pass, g_fail;

/* Two macros rather than one variadic: C11 requires at least one argument
 * for "..." and -Wpedantic enforces it, so the no-argument form is separate. */
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

#define CHECK_EQ(got, want, what)                                              \
	CHECKF((uint32_t)(got) == (uint32_t)(want),                             \
	       "%s: got 0x%08X want 0x%08X", (what), (uint32_t)(got),           \
	       (uint32_t)(want))

/* Expected headers, hand-computed from vid.h:105-107 with count=payload-1.
 *   SET_SH_REG       0x76 : 0xC0000000|0x7600|(1<<16) = 0xC0017600
 *   SET_SH_REG (64)  0x76 : 0xC0000000|0x7600|(2<<16) = 0xC0027600
 *   DISPATCH_DIRECT  0x15 : 0xC0000000|0x1500|(3<<16) = 0xC0031500
 *   EVENT_WRITE      0x46 : 0xC0000000|0x4600|(0<<16) = 0xC0004600
 *   INDIRECT_BUFFER  0x3F : 0xC0000000|0x3F00|(2<<16) = 0xC0023F00
 *   INDIRECT_BUF_CONST 0x33: 0xC0000000|0x3300|(2<<16) = 0xC0023300
 */
#define HDR_SET_SH_REG32   0xC0017600u
#define HDR_SET_SH_REG64   0xC0027600u
#define HDR_DISPATCH       0xC0031500u
#define HDR_EVENT_WRITE    0xC0004600u
#define HDR_IB             0xC0023F00u
#define HDR_IB_CONST       0xC0023300u

#define REG_COMPUTE_PGM_LO 0x2e0cu             /* gfx_8_0_d.h:1293 (index) */
#define REG_OFF_PGM_LO     (0x2e0cu - 0x2c00u) /* == 0x20C */

static uint32_t storage_a[64];
static uint32_t storage_b[64];

static struct rx550_pm4_buf fresh(uint32_t *st, uint32_t cap)
{
	struct rx550_pm4_buf b;
	rx550_pm4_buf_init(&b, st, cap);
	return b;
}

/* ---------------------------------------------------------------- T1..T5 */
static void t_buffer_basics(void)
{
	struct rx550_pm4_buf b = fresh(storage_a, 4);
	uint32_t v = 0;

	CHECKF(rx550_pm4_buf_count(&b) == 0, "T1: fresh count != 0 (%u)",
	      rx550_pm4_buf_count(&b));
	CHECK(rx550_pm4_buf_capacity(&b) == 4, "T1: capacity != 4");
	CHECK(rx550_pm4_buf_free(&b) == 4, "T1: free != 4");

	/* T2: single DW append */
	CHECK(rx550_pm4_buf_append_dw(&b, 0xDEADBEEFu) == RX550_PM4_OK,
	      "T2: append_dw rejected");
	CHECK(rx550_pm4_buf_count(&b) == 1, "T2: count != 1");
	CHECK(rx550_pm4_buf_dw(&b, 0, &v) == RX550_PM4_OK, "T2: read back failed");
	CHECK_EQ(v, 0xDEADBEEFu, "T2: dw0");

	/* T3: exact capacity boundary */
	rx550_pm4_buf_reset(&b);
	CHECK(rx550_pm4_buf_append_dw(&b, 1u) == RX550_PM4_OK, "T3: fill 1");
	CHECK(rx550_pm4_buf_append_dw(&b, 2u) == RX550_PM4_OK, "T3: fill 2");
	CHECK(rx550_pm4_buf_append_dw(&b, 3u) == RX550_PM4_OK, "T3: fill 3");
	CHECK(rx550_pm4_buf_append_dw(&b, 4u) == RX550_PM4_OK, "T3: fill 4 = cap");
	CHECK(rx550_pm4_buf_count(&b) == 4, "T3: count != 4");
	CHECK(rx550_pm4_buf_free(&b) == 0, "T3: free != 0 at cap");

	/* T4: overflow rejected, state untouched */
	CHECK(rx550_pm4_buf_append_dw(&b, 5u) == RX550_PM4_ENOSPC,
	      "T4: overflow not rejected");
	CHECK(rx550_pm4_buf_count(&b) == 4, "T4: count changed on overflow");
	CHECK(rx550_pm4_buf_dw(&b, 3, &v) == RX550_PM4_OK, "T4: dw3 unreadable");
	CHECK_EQ(v, 4u, "T4: dw3 clobbered by rejected write");

	CHECK(rx550_pm4_buf_append(&b, storage_b, 1u) == RX550_PM4_ENOSPC,
	      "T4: 1-DW append at cap not rejected");
	CHECK(rx550_pm4_buf_count(&b) == 4, "T4: count changed");

	/* T5: reset.  Every DW of the capacity must be cleared, not just dw0:
	 * a reset that only cleared the first word would still pass a dw0-only
	 * check, so the whole capacity is verified. */
	for (uint32_t i = 0; i < 4; i++)
		storage_a[i] = 0xA5A5A5A5u;
	rx550_pm4_buf_reset(&b);
	CHECK(rx550_pm4_buf_count(&b) == 0, "T5: count != 0 after reset");
	CHECK(rx550_pm4_buf_dw(&b, 0, &v) == RX550_PM4_ERANGE,
	      "T5: dw0 readable after reset");
	for (uint32_t i = 0; i < 4; i++)
		CHECKF(storage_a[i] == 0u, "T5: storage[%u] not zeroed by reset (0x%08X)",
		      i, storage_a[i]);
	CHECK(rx550_pm4_buf_free(&b) == 4, "T5: free != cap after reset");
}

/* ---------------------------------------------------------------- T6..T8 */
static void t_header(void)
{
	struct rx550_pm4_buf b = fresh(storage_a, 16);
	uint32_t h;

	h = rx550_pm4_hdr(RX550_PM4_OP_INDIRECT_BUFFER, 3);
	CHECK_EQ(h, HDR_IB, "T6: hdr(INDIRECT_BUFFER,3)");
	CHECK_EQ(rx550_pm4_hdr_type(h), RX550_PM4_HDR_TYPE3, "T6: type");
	CHECK_EQ(rx550_pm4_hdr_opcode(h), RX550_PM4_OP_INDIRECT_BUFFER, "T6: opcode");
	CHECK_EQ(rx550_pm4_hdr_count(h), 2u, "T6: count");

	/* T7: opcode preservation.  0x3F vs 0x33 is the pair that differs
	 * between vid.h and sid.h; if collapsed, the two descriptors become
	 * indistinguishable. */
	CHECK(rx550_pm4_hdr(RX550_PM4_OP_INDIRECT_BUFFER, 3)
	      != rx550_pm4_hdr(RX550_PM4_OP_INDIRECT_BUFFER_CONST, 3),
	      "T7: 0x3F and 0x33 collapsed");
	CHECK_EQ(rx550_pm4_hdr_opcode(
			 rx550_pm4_hdr(RX550_PM4_OP_INDIRECT_BUFFER_CONST, 3)),
		 RX550_PM4_OP_INDIRECT_BUFFER_CONST, "T7: const opcode");
	CHECK(rx550_pm4_hdr(RX550_PM4_OP_SET_SH_REG, 2)
	      != rx550_pm4_hdr(RX550_PM4_OP_EVENT_WRITE, 2),
	      "T7: SET_SH_REG and EVENT_WRITE collapsed");

	/* T8: count == payload_dw - 1, total stream == 1 + payload */
	CHECK(rx550_pm4_buf_count(&b) == 0, "T8: buffer not empty");
	CHECK(rx550_pm4_emit_sh_set_reg(&b, REG_COMPUTE_PGM_LO, 0x1u) == RX550_PM4_OK,
	      "T8: set_sh_reg failed");
	CHECK(rx550_pm4_buf_count(&b) == 3, "T8: set_sh_reg stream length");
	CHECK_EQ(rx550_pm4_hdr_count(storage_a[0]), 1u, "T8: set_sh_reg count");
}

static void t_sh_and_event(void)
{
	struct rx550_pm4_buf b = fresh(storage_a, 32);

	CHECK(rx550_pm4_emit_sh_set_reg(&b, REG_COMPUTE_PGM_LO, 0x89ABCDEFu)
	      == RX550_PM4_OK, "sh_set_reg");
	CHECK_EQ(storage_a[0], HDR_SET_SH_REG32, "sh_set_reg hdr");
	CHECK_EQ(storage_a[1], REG_OFF_PGM_LO, "sh_set_reg reg offset");
	CHECK_EQ(storage_a[2], 0x89ABCDEFu, "sh_set_reg value");

	rx550_pm4_buf_reset(&b);
	CHECK(rx550_pm4_emit_sh_set_reg64(&b, REG_COMPUTE_PGM_LO,
					  0x1122334455667788ull) == RX550_PM4_OK,
	      "sh_set_reg64");
	CHECK_EQ(storage_a[0], HDR_SET_SH_REG64, "sh_set_reg64 hdr");
	CHECK_EQ(storage_a[1], REG_OFF_PGM_LO, "sh_set_reg64 reg offset");
	CHECK_EQ(storage_a[2], 0x55667788u, "sh_set_reg64 lo");
	CHECK_EQ(storage_a[3], 0x11223344u, "sh_set_reg64 hi");

	rx550_pm4_buf_reset(&b);
	CHECK(rx550_pm4_emit_event_write(&b, 7u, 4u) == RX550_PM4_OK, "event_write");
	CHECK_EQ(storage_a[0], HDR_EVENT_WRITE, "event_write hdr");
	/* gfx_v8_0.c:1550 -> EVENT_TYPE(7) | EVENT_INDEX(4) */
	CHECK_EQ(storage_a[1], 0x00000407u, "event_write payload");
}

/* ------------------------------------------------------------------- T9 */
static void t_ib_descriptor(void)
{
	struct rx550_pm4_buf b = fresh(storage_a, 32);
	/* 46-bit address with BOTH halves non-trivial, so a change to either
	 * the hi field or the lo mask is observable. */
	const uint64_t va = 0x00003fffabcde000ull;

	CHECK(rx550_pm4_emit_ib_descriptor(&b, va, 3u, 5u, RX550_PM4_IB_VALID, 0)
	      == RX550_PM4_OK, "T9: ib_descriptor");
	CHECK(rx550_pm4_buf_count(&b) == 4, "T9: stream length");
	CHECK_EQ(storage_a[0], HDR_IB, "T9: hdr");
	CHECK_EQ(storage_a[1], 0xabcde000u, "T9: addr lo (va & 0xFFFFFFFC)");
	CHECK_EQ(storage_a[2], 0x00003fffu, "T9: addr hi (va>>32 & 0xFFFF)");
	/* control = flags | length_dw | (vmid << 24) */
	CHECK_EQ(storage_a[3], 0x05800003u, "T9: control");

	rx550_pm4_buf_reset(&b);
	CHECK(rx550_pm4_emit_ib_descriptor(&b, va, 3u, 5u, 0u, 1) == RX550_PM4_OK,
	      "T9: const descriptor");
	CHECK_EQ(storage_a[0], HDR_IB_CONST, "T9: const hdr");
	CHECK_EQ(storage_a[3], 0x05000003u, "T9: const control (no VALID)");

	/* Address-field boundaries.  The field is 46 bits; the reference masks
	 * anything wider, so the encoder must reject it instead.
	 * 2^46 - 4 = 0x3ffffffffffc is the largest aligned value that fits. */
	rx550_pm4_buf_reset(&b);
	CHECK(rx550_pm4_emit_ib_descriptor(&b, 0x00003ffffffffffcull, 1u, 0u, 0u, 0)
	      == RX550_PM4_OK, "T9: max 46-bit address rejected");
	CHECK_EQ(storage_a[1], 0xfffffffcu, "T9: max address lo field");
	/* 46 address bits: lo carries 31:2, hi carries 45:32 (14 bits). */
	CHECK_EQ(storage_a[2], 0x00003fffu, "T9: max address hi field");
	rx550_pm4_buf_reset(&b);
	CHECK(rx550_pm4_emit_ib_descriptor(&b, 0x0000400000000000ull, 1u, 0u, 0u, 0)
	      == RX550_PM4_ERANGE, "T9: 2^46 accepted");
	rx550_pm4_buf_reset(&b);
	CHECK(rx550_pm4_emit_ib_descriptor(&b, 0x0000800000000000ull, 1u, 0u, 0u, 0)
	      == RX550_PM4_ERANGE, "T9: 2^47 accepted");
	rx550_pm4_buf_reset(&b);
	CHECK(rx550_pm4_emit_ib_descriptor(&b, 0x0000123456789abcull, 1u, 0u, 0u, 0)
	      == RX550_PM4_OK, "T9: valid 45-bit address wrongly rejected");
	CHECK(rx550_pm4_buf_count(&b) == 4, "T9: 45-bit address stream length");
	CHECK_EQ(storage_a[1], 0x56789abcu, "T9: 45-bit address lo field");
	CHECK_EQ(storage_a[2], 0x00001234u, "T9: 45-bit address hi field");
}

/* ------------------------------------------------------------------ T10 */
static void t_dispatch_direct(void)
{
	struct rx550_pm4_buf b = fresh(storage_a, 32);

	CHECK(rx550_pm4_emit_dispatch_direct(&b, 8u, 1u, 1u,
					    RX550_PM4_DISPATCH_SHADER_EN)
	      == RX550_PM4_OK, "T10: dispatch_direct");
	CHECK(rx550_pm4_buf_count(&b) == 5, "T10: stream length");
	CHECK_EQ(storage_a[0], HDR_DISPATCH, "T10: hdr");
	/* gfx_v8_0.c:1542-1544 writes 8, 1, 1 */
	CHECK_EQ(storage_a[1], 8u, "T10: x");
	CHECK_EQ(storage_a[2], 1u, "T10: y");
	CHECK_EQ(storage_a[3], 1u, "T10: z");
	/* gfx_v8_0.c:1545-1546 -> COMPUTE_DISPATCH_INITIATOR.COMPUTE_SHADER_EN = 1 */
	CHECK_EQ(storage_a[4], 0x00000001u, "T10: initiator");

	/* The corpus stream uses y=1, z=1 and initiator=1, so field order
	 * among those three is NOT observable from it.  A second call with four
	 * distinct values makes every position distinguishable. */
	rx550_pm4_buf_reset(&b);
	CHECK(rx550_pm4_emit_dispatch_direct(&b, 0x11111111u, 0x22222222u,
					    0x33333333u, 0x44444444u)
	      == RX550_PM4_OK, "T10: distinct dispatch");
	CHECK_EQ(storage_a[1], 0x11111111u, "T10: distinct x");
	CHECK_EQ(storage_a[2], 0x22222222u, "T10: distinct y");
	CHECK_EQ(storage_a[3], 0x33333333u, "T10: distinct z");
	CHECK_EQ(storage_a[4], 0x44444444u, "T10: distinct initiator");
}

/* ------------------------------------------------------------------ T11 */
static void t_invalid_arguments(void)
{
	struct rx550_pm4_buf b = fresh(storage_a, 2);
	uint32_t v;

	CHECK(rx550_pm4_buf_append_dw(NULL, 1u) == RX550_PM4_EINVAL, "T11: NULL buf");
	CHECK(rx550_pm4_buf_append_dw(&b, 1u) == RX550_PM4_OK, "T11: precondition");
	CHECK(rx550_pm4_buf_append(&b, NULL, 1u) == RX550_PM4_EINVAL, "T11: NULL src");
	CHECK(rx550_pm4_buf_append(&b, storage_b, 0u) == RX550_PM4_EINVAL, "T11: n=0");
	CHECK(rx550_pm4_buf_dw(&b, 99u, &v) == RX550_PM4_ERANGE, "T11: idx OOR");

	/* a multi-DW packet must not partially land in a 2-DW buffer */
	rx550_pm4_buf_reset(&b);
	CHECK(rx550_pm4_emit_dispatch_direct(&b, 1u, 1u, 1u, 0u) == RX550_PM4_ENOSPC,
	      "T11: 5-DW packet into 2-DW buffer not rejected");
	CHECK(rx550_pm4_buf_count(&b) == 0, "T11: partial write on rejected packet");
	CHECK_EQ(storage_a[0], 0u, "T11: storage touched by rejected packet");

	/* register below the SET_SH_REG base has no encoding here */
	rx550_pm4_buf_reset(&b);
	CHECK(rx550_pm4_emit_sh_set_reg(&b, 0x100u, 0u) == RX550_PM4_ERANGE,
	      "T11: reg below SET_SH_REG_START accepted");

	/* address not 4-byte aligned: the reference masks, we reject */
	rx550_pm4_buf_reset(&b);
	CHECK(rx550_pm4_emit_ib_descriptor(&b, 0x1002ull, 1u, 0u, 0u, 0)
	      == RX550_PM4_ERANGE, "T11: unaligned IB address accepted");
	CHECK(rx550_pm4_emit_ib_descriptor(&b, 0x1000ull, 1u, 0x100u, 0u, 0)
	      == RX550_PM4_ERANGE, "T11: vmid > 255 accepted");
	CHECK(rx550_pm4_buf_count(&b) == 0,
	      "T11: rejected descriptor wrote something");
}

/* ------------------------------------------------------------------ T12 */
static int build_sample(struct rx550_pm4_buf *b)
{
	int r;

	rx550_pm4_buf_reset(b);
	r = rx550_pm4_emit_sh_set_reg(b, REG_COMPUTE_PGM_LO, 0xCAFEBABEu);
	if (r)
		return r;
	r = rx550_pm4_emit_sh_set_reg64(b, REG_COMPUTE_PGM_LO, 0x0123456789abcdefull);
	if (r)
		return r;
	r = rx550_pm4_emit_dispatch_direct(b, 8u, 1u, 1u, RX550_PM4_DISPATCH_SHADER_EN);
	if (r)
		return r;
	r = rx550_pm4_emit_event_write(b, 7u, 4u);
	if (r)
		return r;
	return rx550_pm4_emit_ib_descriptor(b, 0x00003fffabcde000ull, 11u, 3u,
					   RX550_PM4_IB_VALID, 0);
}

static void t_determinism(void)
{
	struct rx550_pm4_buf a = fresh(storage_a, 64);
	struct rx550_pm4_buf b = fresh(storage_b, 64);

	/* 3 set_reg + 4 set_reg64 + 5 dispatch + 2 event + 4 ib = 18 DW */
	CHECK(build_sample(&a) == RX550_PM4_OK, "T12: first build failed");
	CHECK(build_sample(&b) == RX550_PM4_OK, "T12: second build failed");
	CHECK(rx550_pm4_buf_count(&a) == 18, "T12: sample stream length");
	CHECK(memcmp(storage_a, storage_b, 18 * sizeof(uint32_t)) == 0,
	      "T12: two builds of the same input differ");

	/* rebuild into the same buffer after reset: byte-identical */
	CHECK(build_sample(&a) == RX550_PM4_OK, "T12: rebuild failed");
	CHECK(memcmp(storage_a, storage_b, 18 * sizeof(uint32_t)) == 0,
	      "T12: rebuild after reset differs");
}

/* ------------------------------------------------------------------ T13
 * Asserts the ABSENCE of hardware API references in the component sources.
 */
static const char *const forbidden[] = {
	"pci_enable_device", "pci_request_regions", "pci_iomap", "pci_set_master",
	"ioremap", "iounmap", "readl", "writel", "__iomem", "dma_alloc_coherent",
	"dma_map_single", "request_irq", "irqhandler", "MMIO", "mmio",
	"doorbell", "DOORBELL", "wptr", "WPTR", "submit", "kick", "schedule",
	"amdgpu_", "AMDGPU", "vmalloc", "kmalloc", "GFP_", "copy_to_user",
	"copy_from_user", "no_hw_access", "kprobe",
	"ring_kick", "write_wptr", "amdgpu_ring", "amdgpu_ib", "amdgpu_job",
};

/* Strips C comments in place.  The audit must look at CODE: a comment saying
 * "NO doorbell" documents an absence, it is not a doorbell.  Scanning raw
 * text produced false positives against this file's own header comment. */
static void strip_comments(char *s)
{
	char *r = s, *w = s;
	int in_block = 0, in_line = 0, in_str = 0, in_chr = 0;

	while (*r) {
		if (in_block) {
			if (r[0] == '*' && r[1] == '/') { in_block = 0; r += 2; }
			else r++;
			continue;
		}
		if (in_line) {
			if (*r == '\n') { in_line = 0; *w++ = *r; }
			r++;
			continue;
		}
		if (!in_str && !in_chr && r[0] == '/' && r[1] == '*') {
			in_block = 1; r += 2; continue;
		}
		if (!in_str && !in_chr && r[0] == '/' && r[1] == '/') {
			in_line = 1; r += 2; continue;
		}
		if (*r == '"' && !in_chr) in_str = !in_str;
		else if (*r == '\'' && !in_str) in_chr = !in_chr;
		*w++ = *r;
		r++;
	}
	*w = '\0';
}

static int scan_source(const char *path, const char *what)
{
	static char buf[65536];
	size_t n;
	FILE *f = fopen(path, "rb");
	int bad = 0;

	if (!f) {
		printf("  FAIL T13: cannot open %s\n", path);
		g_fail++;
		return 1;
	}
	n = fread(buf, 1, sizeof(buf) - 1, f);
	buf[n] = '\0';
	fclose(f);
	strip_comments(buf);

	for (size_t i = 0; i < sizeof(forbidden) / sizeof(forbidden[0]); i++) {
		if (strstr(buf, forbidden[i])) {
			printf("  FAIL T13: %s code references forbidden token '%s'\n",
			       what, forbidden[i]);
			bad = 1;
		}
	}
	return bad;
}

static void t_no_hardware_api(void)
{
	int bad = 0;

	bad |= scan_source("pm4.h", "pm4.h");
	bad |= scan_source("pm4.c", "pm4.c");
	CHECK(!bad, "T13: hardware API token present in component sources");
}

/* ------------------------------------------------------------------ T14 */
static void t_build_contract(void)
{
	CHECK(RX550_PM4_OP_INDIRECT_BUFFER == 0x3Fu, "T14: opcode 0x3F drifted");
	CHECK(RX550_PM4_OP_INDIRECT_BUFFER_CONST == 0x33u, "T14: opcode 0x33 drifted");
	CHECK(RX550_PM4_OP_DISPATCH_DIRECT == 0x15u, "T14: opcode 0x15 drifted");
	CHECK(RX550_PM4_OP_SET_SH_REG == 0x76u, "T14: opcode 0x76 drifted");
	CHECK(RX550_PM4_OP_EVENT_WRITE == 0x46u, "T14: opcode 0x46 drifted");
	CHECK(RX550_PM4_SET_SH_REG_START == 0x00002c00u, "T14: SET_SH_REG_START drifted");
}

int main(void)
{
	printf("rx550-pm4 GFX8 command layer tests (software only, no hardware)\n");

	t_buffer_basics();     /* T1 T2 T3 T4 T5 */
	t_header();            /* T6 T7 T8 */
	t_sh_and_event();
	t_ib_descriptor();     /* T9 */
	t_dispatch_direct();   /* T10 */
	t_invalid_arguments(); /* T11 */
	t_determinism();       /* T12 */
	t_no_hardware_api();   /* T13 */
	t_build_contract();    /* T14 */

	printf("passed=%u failed=%u\n", g_pass, g_fail);
	return g_fail ? 1 : 0;
}
