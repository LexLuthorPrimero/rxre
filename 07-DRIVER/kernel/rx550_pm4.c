// SPDX-License-Identifier: GPL-2.0
/*
 * rx550_pm4.c - PM4 packet encoder for the RX 550 (Polaris 12, GFX8).
 *
 * WHY C AND NOT ASSEMBLY
 *
 * The brief for this file said no assembly scaffolding until the GFX8 PM4
 * formats were established. They now are (IA-1, findings/007-gfx8-pm4-format.md,
 * and re-verified against amdgpu.ko byte-for-byte). But an assembler encodes
 * instructions against registers the hardware has to be told to use, and the
 * register programming sequence for this ASIC is still unknown: the one in
 * gfx_v8_0.c is gfx_v8_0_do_edc_gpr_workarounds(), which returns immediately for
 * anything that is not CHIP_CARRIZO. Writing assembly now would encode packets
 * whose delivery is unknown.
 *
 * What IS knowable is the wire format, and it is pure arithmetic on 32-bit
 * words: no hardware, no state, no side effects. That is what this file is, and
 * because it is a pure function it is testable on a host that refuses to load the
 * module at all. The test does that, and it compares the output against values
 * read out of the real amdgpu.ko rather than against itself.
 *
 * HEADER LAYOUT, from amdgpu/sid.h:335-340:
 *
 *     #define PACKET3(op, n)  ((RADEON_PACKET_TYPE3 << 30) |      \
 *                             (((op) & 0xFF) << 8) |             \
 *                             ((n) & 0x3FFF) << 16)
 *     #define PACKET3_COMPUTE(op, n) (PACKET3(op, n) | 1 << 1)
 *
 * The type is at the top and the opcode in the middle. A previous round of this
 * project used the SDMA_PACKET() layout from cikd.h, which puts the opcode at
 * [31:24]; that is the previous generation's format and produces silently wrong
 * headers, not build errors. This file is written against the macro above.
 *
 * count is 14 bits but occupies only [23:16]. Bits 29:24 are nominally reserved
 * and receive the top 6 bits of a count above 63, which the macro does not
 * reject. The encoder below truncates deliberately and says so; accepting a
 * count that the hardware would read differently is the kind of thing that
 * works on one ASIC and not another.
 */

#include <linux/types.h>

/*
 * `bool` is a kernel builtin, so Kbuild needs no declaration of it. In
 * userspace it comes from <stdbool.h>, which the kernel does not have and which
 * therefore cannot appear in the shared header. This file is compiled by both
 * -- the test links it directly -- so the include goes here, guarded, rather
 * than in rx550_pm4.h where it would break the module build.
 */
#ifndef __KERNEL__
#include <stdbool.h>
#endif

#include "rx550_pm4.h"

/*
 * Build a PACKET3 header.
 *
 * @op: packet opcode, 8 bits
 * @count: payload dwords, 14 bits
 * @compute: set bit 1, which marks the packet as belonging to the compute path
 *
 * The compute bit matters and is not cosmetic. amdgpu.ko contains 0xC0031500 ten
 * times and 0xC0031502 once; gfx_v8_0.c calls the non-compute form. Which one a
 * driver must emit for a compute dispatch is OBSERVED from the macro and the
 * binary, not documented by AMD, so both forms are available and the caller
 * chooses. Encoding the wrong one does not fail loudly.
 */
__u32 rx550_pm4_header(__u32 op, __u32 count, bool compute)
{
	__u32 hdr;

	hdr = (3u << 30);			/* PACKET_TYPE3, value fixed at 0b11 */
	hdr |= (op & 0xFFu) << 8;
	hdr |= (count & 0x3FFFu) << 16;

	if (compute)
		hdr |= 1u << 1;

	return hdr;
}

/*
 * rx550_pm4_set_sh_reg - emit a SET_SH_REG for one 32-bit register.
 *
 * The register number is RELATIVE: gfx_v8_0.c writes
 *
 *     mmCOMPUTE_PGM_LO - PACKET3_SET_SH_REG_START
 *
 * so the payload is an offset from 0x2C00, not an absolute register address. An
 * encoder that writes the absolute number programs a different register and the
 * driver produces no error doing it. rx550_pm4_reg_offset() does the
 * subtraction so the caller cannot forget it.
 */
void rx550_pm4_set_sh_reg(struct rx550_pm4_ib *ib, __u32 reg, __u32 value)
{
	if (!ib || ib->length_dw + 3 > ib->size_dw)
		return;

	ib->buf[ib->length_dw++] =
		rx550_pm4_header(RX550_PKT3_SET_SH_REG, 1, false);
	ib->buf[ib->length_dw++] = rx550_pm4_reg_offset(reg);
	ib->buf[ib->length_dw++] = value;
}

/*
 * rx550_pm4_set_sh_reg2 - emit a SET_SH_REG for a 64-bit register, lo then hi.
 *
 * Same packet, count 2. gfx_v8_0.c uses this for COMPUTE_PGM_LO/HI, which is how
 * a shader address gets into the compute program registers.
 */
void rx550_pm4_set_sh_reg2(struct rx550_pm4_ib *ib, __u32 reg, __u64 value)
{
	if (!ib || ib->length_dw + 4 > ib->size_dw)
		return;

	ib->buf[ib->length_dw++] =
		rx550_pm4_header(RX550_PKT3_SET_SH_REG, 2, false);
	ib->buf[ib->length_dw++] = rx550_pm4_reg_offset(reg);
	ib->buf[ib->length_dw++] = (__u32)(value & 0xFFFFFFFFu);
	ib->buf[ib->length_dw++] = (__u32)(value >> 32);
}

/*
 * rx550_pm4_dispatch_direct - emit DISPATCH_DIRECT with immediate dimensions.
 *
 * @x, @y, @z: the three dimension words
 *
 * THE COUNT IS 3 AND FOUR DWORDS FOLLOW. This reproduces gfx_v8_0.c:1541-1546
 * exactly, and it is not a typo here:
 *
 *     ib.ptr[ib.length_dw++] = PACKET3(PACKET3_DISPATCH_DIRECT, 3);
 *     ib.ptr[ib.length_dw++] = 8;                              // x
 *     ib.ptr[ib.length_dw++] = 1;                              // y
 *     ib.ptr[ib.length_dw++] = 1;                              // z
 *     ib.ptr[ib.length_dw++] = REG_SET_FIELD(0, COMPUTE_DISPATCH_INITIATOR,
 *                                            COMPUTE_SHADER_EN, 1);
 *
 * Four words written, count 3. The fourth is the initiator and amdgpu does not
 * count it as payload. WHY is NOT_DETERMINED and is not guessed at here: the
 * parser that would explain it is in hardware, not in this tree. The operational
 * rule is the measured one, and this function encodes the measurement. Changing
 * the count to 4 to "look consistent" would encode something the driver does
 * not do, and nothing would report it.
 *
 * @compute selects the PACKET3_COMPUTE form, which sets bit 1. See the note in
 * rx550_pm4_header().
 */
void rx550_pm4_dispatch_direct(struct rx550_pm4_ib *ib, __u32 x, __u32 y, __u32 z,
			       bool compute)
{
	if (!ib || ib->length_dw + 5 > ib->size_dw)
		return;

	ib->buf[ib->length_dw++] =
		rx550_pm4_header(RX550_PKT3_DISPATCH_DIRECT, 3, compute);
	ib->buf[ib->length_dw++] = x;
	ib->buf[ib->length_dw++] = y;
	ib->buf[ib->length_dw++] = z;
	/* COMPUTE_DISPATCH_INITIATOR with COMPUTE_SHADER_EN (bit 0) set. */
	ib->buf[ib->length_dw++] = 1u;
}

/*
 * rx550_pm4_event_write - emit EVENT_WRITE with the event token as a dword.
 *
 * @event: an already-built token, e.g. EVENT_TYPE(7) | EVENT_INDEX(4)
 *
 * The token is a SEPARATE dword after the header, not the high 16 bits of the
 * header. gfx_v8_0.c:1549-1550:
 *
 *     ib.ptr[ib.length_dw++] = PACKET3(PACKET3_EVENT_WRITE, 0);
 *     ib.ptr[ib.length_dw++] = EVENT_TYPE(7) | EVENT_INDEX(4);
 *
 * findings/007-gfx8-pm4-format.md section 4 claims the token goes in the high 16
 * bits of the header -- "el campo e del formato SDMA_PACKET, que en PACKET3() es
 * el espacio de count y reservados". The code does not do that, and I implemented
 * it that way first. The test caught it: the header came out as 0xC0004704
 * instead of a bare 0xC0004600 followed by 0x00000407.
 *
 * The two readings differ in a way nothing would ever report. The token 0x407
 * is small, so under the document's reading it lands in bits 8:0, which the
 * sid.h:335 layout calls reserved -- and the second dword would then be dead
 * code. The code writes both dwords. The code is the authority on what the
 * driver emits; the document's reading is a plausible inference that does not
 * survive being typed out and compared against the bytes.
 *
 * EVENT_TYPE(x) is (x) << 0 and EVENT_INDEX(x) is (x) << 8 (sid.h:490-491), so
 * EVENT_TYPE(7) | EVENT_INDEX(4) == 0x407.
 */
void rx550_pm4_event_write(struct rx550_pm4_ib *ib, __u32 event)
{
	if (!ib || ib->length_dw + 2 > ib->size_dw)
		return;

	ib->buf[ib->length_dw++] =
		rx550_pm4_header(RX550_PKT3_EVENT_WRITE, 0, false);
	ib->buf[ib->length_dw++] = event;
}

__u32 rx550_pm4_reg_offset(__u32 reg)
{
	if (reg < RX550_PKT3_SET_SH_REG_START) {
		/*
		 * A register below the base cannot be expressed as an offset, and
		 * subtracting anyway would wrap into a valid-looking index for a
		 * different register. Saturate instead: a caller passing 0 gets a
		 * value the hardware will reject, not one that programs elsewhere.
		 */
		return 0;
	}
	return reg - RX550_PKT3_SET_SH_REG_START;
}
