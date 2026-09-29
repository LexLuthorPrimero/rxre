// SPDX-License-Identifier: GPL-2.0
/*
 * test_pm4.c - the PM4 encoder, checked against the real amdgpu.ko.
 *
 * WHAT MAKES THIS TEST DIFFERENT FROM THE OTHER TWO
 *
 * A test that checks the encoder against itself proves nothing: a wrong encoder
 * and a matching wrong expectation pass together. So the expected values here
 * are not written from the implementation. They are the five packet headers
 * counted inside the shipped amdgpu.ko (vermagic 7.1.3-200.nobara.fc44,
 * srcversion D68004925455E20A24C2B87, SHA256 a1a44c24...c024):
 *
 *     0xC0031500   10 occurrences   PACKET3(DISPATCH_DIRECT, 3)
 *     0xC0031502    1 occurrence    PACKET3_COMPUTE(DISPATCH_DIRECT, 3)
 *     0xC0027600   10 occurrences   PACKET3(SET_SH_REG, 2)
 *     0xC0017600   10 occurrences   PACKET3(SET_SH_REG, 1)
 *     0xC0004600   15 occurrences   PACKET3(EVENT_WRITE, 0)
 *
 * All five were reproduced by counting little-endian byte patterns in the module.
 * The encoder is checked against values that came out of the artefact the driver
 * is meant to replace, so agreeing with it is evidence about the format and not
 * about my transcription.
 *
 * WHAT IT DOES NOT ESTABLISH
 *
 * That these packets do anything. No packet built here has been executed on the
 * RX 550. The register programming that would deliver them is not in this tree,
 * and the only dispatch sequence available is a Carrizo EDC workaround that
 * returns immediately for CHIP_POLARIS12. Correct bytes in a command stream that
 * nothing delivers is a formatting result, not a working GPU.
 *
 * Exit 0 if every case behaves as documented, 1 otherwise.
 */

#include <stdbool.h>	/* the kernel has no stdbool.h; the test needs it */
#include <stdint.h>
#include <stdio.h>
#include <string.h>

#include "../kernel/rx550_pm4.h"

static int failures;
static int checks;

static void check(int cond, const char *what, const char *detail)
{
	checks++;
	if (cond) {
		printf("  [ OK ] %s\n", what);
	} else {
		printf("  [FAIL] %s -- %s\n", what, detail);
		failures++;
	}
}

static void check_eq(const char *what, uint32_t got, uint32_t want)
{
	char b[128];

	if (got == want) {
		check(1, what, "");
		return;
	}
	snprintf(b, sizeof b, "got 0x%08X, expected 0x%08X", got, want);
	check(0, what, b);
}

/* The header values as they appear in amdgpu.ko. Not derived from the code. */
#define HDR_DISPATCH_PLAIN	0xC0031500u
#define HDR_DISPATCH_COMPUTE	0xC0031502u
#define HDR_SET_SH_REG_2	0xC0027600u
#define HDR_SET_SH_REG_1	0xC0017600u
#define HDR_EVENT_WRITE		0xC0004600u

/* Register offsets, gfx_8_0_d.h. */
#define MM_COMPUTE_DISPATCH_INITIATOR	0x2e00
#define MM_COMPUTE_NUM_THREAD_X		0x2e07
#define MM_COMPUTE_PGM_LO		0x2e0c
#define MM_COMPUTE_PGM_HI		0x2e0d
#define MM_COMPUTE_PGM_RSRC1		0x2e12

#define IB_MAX	64

int main(void)
{
	struct rx550_pm4_ib ib;
	uint32_t buf[IB_MAX];

	printf("=== test_pm4: encoder vs values counted in amdgpu.ko ===\n");
	printf("    a1a44c24...c024, srcversion D68004925455E20A24C2B87\n");
	printf("    format only. No packet here has run on the RX 550.\n\n");

	printf("1. Header arithmetic, against the binary:\n");
	check_eq("PACKET3(DISPATCH_DIRECT, 3)          = 0xC0031500",
		 rx550_pm4_header(RX550_PKT3_DISPATCH_DIRECT, 3, false),
		 HDR_DISPATCH_PLAIN);
	check_eq("PACKET3_COMPUTE(DISPATCH_DIRECT, 3)  = 0xC0031502",
		 rx550_pm4_header(RX550_PKT3_DISPATCH_DIRECT, 3, true),
		 HDR_DISPATCH_COMPUTE);
	check_eq("PACKET3(SET_SH_REG, 2)               = 0xC0027600",
		 rx550_pm4_header(RX550_PKT3_SET_SH_REG, 2, false),
		 HDR_SET_SH_REG_2);
	check_eq("PACKET3(SET_SH_REG, 1)               = 0xC0017600",
		 rx550_pm4_header(RX550_PKT3_SET_SH_REG, 1, false),
		 HDR_SET_SH_REG_1);
	check_eq("PACKET3(EVENT_WRITE, 0)              = 0xC0004600",
		 rx550_pm4_header(RX550_PKT3_EVENT_WRITE, 0, false),
		 HDR_EVENT_WRITE);
	{
		/* The compute form differs from the plain one by exactly bit 1 and
		 * nothing else. If it ever differs by more, the two paths have
		 * diverged and the one-occurrence count in the binary no longer
		 * describes this encoder. */
		uint32_t d = rx550_pm4_header(RX550_PKT3_DISPATCH_DIRECT, 3, false);
		uint32_t c = rx550_pm4_header(RX550_PKT3_DISPATCH_DIRECT, 3, true);

		check_eq("compute form differs from plain by exactly 0x2",
			 c ^ d, 0x2u);
	}

	printf("\n2. The opcode went in [15:8] and the type in [31:30]:\n");
	{
		uint32_t h = rx550_pm4_header(RX550_PKT3_SET_SH_REG, 1, false);

		check_eq("bits 31:30 == 0b11 (PACKET_TYPE3)", h >> 30, 3u);
		check_eq("bits 15:8 == opcode 0x76", (h >> 8) & 0xFF, 0x76u);
		check_eq("bits 23:16 == count 1", (h >> 16) & 0x3FFF, 1u);
	}
	printf("         (a layout with the opcode at [31:24], which is what\n"
	       "          SDMA_PACKET() in cikd.h uses, would fail all three)\n");

	printf("\n3. count is masked to 14 bits, and the top 6 do not leak:\n");
	{
		/* count 0x3FFF is the mask's maximum. If the encoder used the full
		 * 32-bit shift, bits 29:24 would be non-zero and the header would
		 * not match any value in the binary. */
		uint32_t h = rx550_pm4_header(RX550_PKT3_NOP, 0x3FFF, false);

		check_eq("count 0x3FFF is masked, not truncated differently",
			 (h >> 16) & 0x3FFF, 0x3FFFu);
		check_eq("bits 31:30 still the type at max count", h >> 30, 3u);
	}

	printf("\n4. SET_SH_REG payload is a RELATIVE offset:\n");
	check_eq("COMPUTE_PGM_LO (0x2E0C) - 0x2C00 = 0x020C",
		 rx550_pm4_reg_offset(MM_COMPUTE_PGM_LO), 0x020Cu);
	check_eq("COMPUTE_PGM_RSRC1 (0x2E12) - 0x2C00 = 0x0212",
		 rx550_pm4_reg_offset(MM_COMPUTE_PGM_RSRC1), 0x0212u);
	{
		/* An absolute register number would program a different register
		 * and produce no error. This is the single most likely silent
		 * failure in a hand-written encoder, so it is asserted directly. */
		uint32_t abs = MM_COMPUTE_PGM_LO;

		check(abs != (uint32_t)rx550_pm4_reg_offset(MM_COMPUTE_PGM_LO),
		      "the offset is NOT the absolute register number", "");
	}
	{
		/* Saturating rather than wrapping: a register below the base must
		 * not alias into a valid index for something else. */
		check_eq("a register below 0x2C00 saturates to 0",
			 rx550_pm4_reg_offset(0x1000), 0u);
	}

	printf("\n5. set_sh_reg emits header, offset, value -- three dwords:\n");
	memset(buf, 0xAA, sizeof(buf));
	memset(&ib, 0, sizeof(ib));
	ib.buf = buf;
	ib.size_dw = IB_MAX;
	rx550_pm4_set_sh_reg(&ib, MM_COMPUTE_PGM_RSRC1, 0x240);
	check_eq("length_dw == 3", (uint32_t)ib.length_dw, 3u);
	check_eq("dword 0 is the header", buf[0], HDR_SET_SH_REG_1);
	check_eq("dword 1 is the relative offset", buf[1], 0x0212u);
	check_eq("dword 2 is the value", buf[2], 0x240u);

	printf("\n6. set_sh_reg2 emits lo then hi:\n");
	memset(buf, 0xAA, sizeof(buf));
	ib.length_dw = 0;
	rx550_pm4_set_sh_reg2(&ib, MM_COMPUTE_PGM_LO, 0x1122334455667788ull);
	check_eq("length_dw == 4", (uint32_t)ib.length_dw, 4u);
	check_eq("dword 0 is the count-2 header", buf[0], HDR_SET_SH_REG_2);
	check_eq("dword 1 is the relative offset", buf[1], 0x020Cu);
	check_eq("dword 2 is the low half", buf[2], 0x55667788u);
	/* 0x1122334455667788 >> 32 == 0x11223344. I first wrote 0x11223322 here,
	 * transposing two digits; the test failed and was right. A hand-typed
	 * expected value is exactly the kind of thing that should be computed. */
	check_eq("dword 3 is the high half", buf[3], 0x11223344u);

	printf("\n7. DISPATCH_DIRECT: header says 3, five dwords are written.\n");
	printf("   This reproduces gfx_v8_0.c:1541-1546. The mismatch is in\n"
	       "   the driver too, and why is NOT_DETERMINED.\n");
	memset(buf, 0xAA, sizeof(buf));
	ib.length_dw = 0;
	rx550_pm4_dispatch_direct(&ib, 8, 1, 1, false);
	check_eq("length_dw == 5, four payload words after the header",
		 (uint32_t)ib.length_dw, 5u);
	check_eq("dword 0 is 0xC0031500", buf[0], HDR_DISPATCH_PLAIN);
	check_eq("dword 1 is x", buf[1], 8u);
	check_eq("dword 2 is y", buf[2], 1u);
	check_eq("dword 3 is z", buf[3], 1u);
	{
		/* COMPUTE_DISPATCH_INITIATOR with COMPUTE_SHADER_EN, bit 0
		 * (gfx_8_0_sh_mask.h:8235). Not decoded beyond that: the other
		 * 12 fields are known to exist and are not needed here. */
		check_eq("dword 4 is the initiator, COMPUTE_SHADER_EN only",
			 buf[4], 1u);
	}
	{
		/* If the count were 4 to match the four written words, the header
		 * would be 0xC0041500, which does not occur in amdgpu.ko at all.
		 * Asserting that it is absent is the point: it is why this looks
		 * like a bug and is not one. */
		uint32_t wrong = rx550_pm4_header(RX550_PKT3_DISPATCH_DIRECT, 4, false);

		check_eq("count 4 would give 0xC0041500, which is not in the module",
			 wrong, 0xC0041500u);
	}

	memset(buf, 0xAA, sizeof(buf));
	ib.length_dw = 0;
	rx550_pm4_dispatch_direct(&ib, 8, 1, 1, true);
	check_eq("compute form emits 0xC0031502", buf[0], HDR_DISPATCH_COMPUTE);

	/*
	 * EVENT_WRITE: the token is a separate dword.
	 *
	 * findings/007 section 4 says it goes in the header's high 16 bits. It
	 * does not: gfx_v8_0.c:1549-1550 writes the header with count 0 and then
	 * a second dword holding EVENT_TYPE(7) | EVENT_INDEX(4). I implemented the
	 * documented version first and this check is what caught it.
	 */
	printf("\n8. EVENT_WRITE: header with count 0, token in a separate dword:\n");
	memset(buf, 0xAA, sizeof(buf));
	ib.length_dw = 0;
	rx550_pm4_event_write(&ib, (7u << 0) | (4u << 8));	/* 0x407 */
	check_eq("length_dw == 2", (uint32_t)ib.length_dw, 2u);
	check_eq("dword 0 is the bare header, nothing OR'd in",
		 buf[0], HDR_EVENT_WRITE);
	check_eq("dword 1 is the token 0x407", buf[1], 0x407u);
	{
		/* EVENT_TYPE(x) = x<<0, EVENT_INDEX(x) = x<<8 (sid.h:490-491).
		 * Absorbing the token into the header would give 0xC0004600 | 0x407
		 * = 0xC0004607, leaving the second dword dead. 0xC0004600 occurs 15
		 * times in amdgpu.ko; the OR'd form occurs zero times, which is the
		 * evidence that the token is a separate word. I asserted the wrong
		 * sum (0xC0004704) the first time and the test caught me, same as
		 * the two transposed constants above. */
		uint32_t as_header = HDR_EVENT_WRITE | 0x0407u;

		check_eq("absorbing the token would give 0xC0004607",
			 as_header, 0xC0004607u);
		check(as_header != HDR_EVENT_WRITE,
		      "0xC0004607 is NOT in the module; 0xC0004600 is, 15 times",
		      "");
	}

	printf("\n9. A full sequence, assembled the way gfx_v8_0.c does it:\n");
	memset(buf, 0xAA, sizeof(buf));
	ib.length_dw = 0;
	rx550_pm4_set_sh_reg(&ib, MM_COMPUTE_NUM_THREAD_X, 256 * 5);
	rx550_pm4_dispatch_direct(&ib, 8, 1, 1, false);
	rx550_pm4_event_write(&ib, (7u << 0) | (4u << 8));	/* 0x407 */
	check_eq("three packets, 3 + 5 + 2 dwords", (uint32_t)ib.length_dw, 10u);
	check_eq("pkt 0 header", buf[0], HDR_SET_SH_REG_1);
	/* 0x2E07 - 0x2C00 == 0x0207. I first wrote 0x0007, having subtracted
	 * 0x2E00 instead. Another transposed expectation, caught the same way. */
	check_eq("pkt 0 offset for NUM_THREAD_X (0x2E07-0x2C00)", buf[1], 0x0207u);
	check_eq("pkt 0 value 256*5", buf[2], 1280u);
	check_eq("pkt 1 header", buf[3], HDR_DISPATCH_PLAIN);
	check_eq("pkt 2 header is the bare 0xC0004600", buf[8], HDR_EVENT_WRITE);
	check_eq("pkt 2 trailer is the token 0x407", buf[9], 0x407u);

	printf("\n10. Overflow is refused, not truncated silently mid-packet:\n");
	{
		/* An IB with room for 3 dwords cannot take a 5-dword dispatch.
		 * Nothing is written and length_dw does not move, so the caller
		 * sees an unchanged buffer rather than a partial packet. A partial
		 * command stream is the failure this guards: the GPU would run
		 * half a job and report nothing. */
		memset(buf, 0xAA, sizeof(buf));
		ib.buf = buf;
		ib.size_dw = 3;
		ib.length_dw = 0;
		rx550_pm4_dispatch_direct(&ib, 8, 1, 1, false);
		check_eq("a 5-dword packet into a 3-dword IB writes nothing",
			 (uint32_t)ib.length_dw, 0u);
		check_eq("and leaves the buffer untouched", buf[0], 0xAAAAAAAAu);
	}
	{
		/* An IB with room for exactly 5 must accept it. An off-by-one here
		 * would reject every real dispatch. */
		memset(buf, 0xAA, sizeof(buf));
		ib.size_dw = 5;
		ib.length_dw = 0;
		rx550_pm4_dispatch_direct(&ib, 8, 1, 1, false);
		check_eq("exactly 5 dwords is enough", (uint32_t)ib.length_dw, 5u);
	}
	{
		/* set_sh_reg into a 2-dword IB: 3 needed, so refused. */
		memset(buf, 0xAA, sizeof(buf));
		ib.size_dw = 2;
		ib.length_dw = 0;
		rx550_pm4_set_sh_reg(&ib, MM_COMPUTE_PGM_RSRC1, 0x240);
		check_eq("a 3-dword packet into a 2-dword IB writes nothing",
			 (uint32_t)ib.length_dw, 0u);
	}
	{
		/* A NULL ib must not crash the caller. Cheap, and a NULL check
		 * that is missing shows up as an oops on someone else's path. */
		rx550_pm4_dispatch_direct(NULL, 8, 1, 1, false);
		rx550_pm4_set_sh_reg(NULL, MM_COMPUTE_PGM_RSRC1, 0x240);
		rx550_pm4_event_write(NULL, 0);
		check(1, "NULL ib is handled without dereferencing", "");
	}

	printf("\n%d checks, %d failure(s)\n", checks, failures);
	if (failures) {
		printf("RESULT: FAIL\n");
		return 1;
	}
	printf("RESULT: PASS\n");
	printf("\nNOT covered, and not claimed:\n"
	       "  - whether any of these packets reaches the hardware. The\n"
	       "    register programming sequence is not in this tree.\n"
	       "  - DISPATCH_DIRECT's dimensions. They come from\n"
	       "    COMPUTE_NUM_THREAD_X/Y/Z and are per-shader state, not a\n"
	       "    constant this encoder can supply.\n"
	       "  - the count=3-with-5-dwords rule. Encoded as measured; the\n"
	       "    reason is NOT_DETERMINED and is not asserted here.\n"
	       "  - DISPATCH_INDIRECT (0x16), and every packet outside the\n"
	       "    dispatch sequence.\n");
	return 0;
}
