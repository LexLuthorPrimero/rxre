/* SPDX-License-Identifier: GPL-2.0 */
/*
 * rx550_pm4.h - PM4 packet encoder interface.
 *
 * Shared between the kernel module and the userspace test. The test compiles
 * the same .c file the module does, so a packet the test validates is the packet
 * the module emits, not a transcription of it.
 *
 * NOT INSTABLE ABI. These are internal, not ioctl payloads. Nothing crosses the
 * user/kernel boundary through this header, and it may change without a version
 * bump. Confusing the two is how a driver ends up with an ABI version that has
 * nothing to do with the structs userspace actually passes.
 */
#ifndef _RX550_PM4_H
#define _RX550_PM4_H

/*
 * __u32/__u64, not u32/u64. The short names are kernel-only typedefs; in
 * userspace linux/types.h provides __u32 and nothing else, so a header written
 * with u32 compiles in the module and fails in the test with "unknown type name"
 * on every line. The __u forms are the ones both sides accept.
 *
 * NO stdbool.h HERE, and no size_t. Two things the kernel does not have:
 *
 *   - The kernel has no <stbool.h>; `bool` is a builtin. Including it fails the
 *     Kbuild with "stbool.h: No existe el fichero o el directorio". A header
 *     shared by both sides cannot include it, so callers that need it include it
 *     themselves before this header: the userspace test does, the kernel does not.
 *   - size_t is not in scope from linux/types.h in userspace, and
 *     <linux/stddef.h> resolves to the UAPI copy, which does not define it.
 *     The dword counts are therefore __u32. An indirect buffer is bounded by a
 *     few thousand dwords; 32 bits is not a real limit and it removes a type
 *     that cannot be spelled for both compilers.
 */
#include <linux/types.h>

/*
 * Opcodes, from amdgpu/sid.h. Each verified at the cited line.
 *
 * These are GFX8 values. gfx_v12_1_pkt.h carries its own, which is the reminder
 * that the format changes between generations and this table is not portable.
 */
#define RX550_PKT3_NOP			0x10	/* sid.h:343 */
#define RX550_PKT3_DISPATCH_DIRECT	0x15	/* sid.h:350 */
#define RX550_PKT3_DISPATCH_INDIRECT	0x16	/* sid.h:351 */
#define RX550_PKT3_EVENT_WRITE		0x46	/* sid.h:489 */
#define RX550_PKT3_EVENT_WRITE_EOP	0x47	/* sid.h:503 */
#define RX550_PKT3_EVENT_WRITE_EOS	0x48	/* sid.h:515 */
#define RX550_PKT3_SET_SH_REG		0x76	/* sid.h:531 */

/*
 * The first register addressable by SET_SH_REG. The payload of that packet is
 * an offset from this value, not an absolute register number.
 */
#define RX550_PKT3_SET_SH_REG_START	0x00002c00	/* sid.h:532 */

/*
 * An indirect buffer: a growable array of dwords with a hard capacity.
 *
 * Every emit function takes one and silently does nothing if it would overflow.
 * Silent is deliberate and is also the risk: a truncated command stream on a GPU
 * is not a crash, it is a partial job. The length is what a caller must check
 * before submitting, which is why length_dw is public rather than hidden.
 */
struct rx550_pm4_ib {
	__u32	*buf;		/**< destination, at least size_dw dwords */
	__u32	 size_dw;	/**< capacity in dwords */
	__u32	 length_dw;	/**< dwords written so far */
};

/** rx550_pm4_header - build a PACKET3 header. @compute sets bit 1. */
__u32 rx550_pm4_header(__u32 op, __u32 count, bool compute);

/** rx550_pm4_reg_offset - absolute register to SET_SH_REG payload offset. */
__u32 rx550_pm4_reg_offset(__u32 reg);

/** rx550_pm4_set_sh_reg - SET_SH_REG, one dword. */
void rx550_pm4_set_sh_reg(struct rx550_pm4_ib *ib, __u32 reg, __u32 value);

/** rx550_pm4_set_sh_reg2 - SET_SH_REG, two dwords (lo, hi) for a 64-bit register. */
void rx550_pm4_set_sh_reg2(struct rx550_pm4_ib *ib, __u32 reg, __u64 value);

/**
 * rx550_pm4_dispatch_direct - DISPATCH_DIRECT with immediate x, y, z.
 *
 * Writes five dwords, of which the header declares a count of 3. That matches
 * gfx_v8_0.c and the reason is not established; see the note in the .c file
 * before changing it.
 */
void rx550_pm4_dispatch_direct(struct rx550_pm4_ib *ib, __u32 x, __u32 y, __u32 z,
			       bool compute);

/**
 * rx550_pm4_event_write - EVENT_WRITE.
 *
 * @event: an already-built token, e.g. EVENT_TYPE(7) | EVENT_INDEX(4) == 0x407
 *
 * Writes two dwords: the header with count 0, then the token. The token is not
 * the header's high 16 bits, which is what findings/007 says and what this was
 * first written to do; the test caught the difference. See the .c file.
 */
void rx550_pm4_event_write(struct rx550_pm4_ib *ib, __u32 event);

#endif /* _RX550_PM4_H */
