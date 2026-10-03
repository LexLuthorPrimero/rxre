/* rx550_vis.h — CPU->GPU visibility contract for a GFX8 indirect buffer.
 *
 * WHAT THIS IS.  A model of the ordering the driver must establish before the
 * command processor may fetch an IB that the CPU has just written.  It does
 * NOT perform a barrier, a flush, or an MMIO write.  It is pure data: given a
 * description of what happened, it reports whether the ordering contract is
 * satisfied, and it encodes the coherence packet that carries the ordering
 * in-band.
 *
 * WHY IT IS HERE AND NOT IN rx550-pm4.  rx550-pm4 encodes command packets.
 * This is a MEMORY-VISIBILITY contract: it constrains WHEN a packet may be
 * ordered relative to another packet.  A production packet encoder belongs in
 * rx550-pm4; nothing here calls it.  The two share numbers, not code.
 *
 * EVIDENCE (drivers/gpu/drm/amd/, project corpus linux-7.1.3):
 *   amdgpu_ib.c:80      every amdgpu_ib_get() sets AMDGPU_IB_FLAG_EMIT_MEM_SYNC
 *   amdgpu_ib.c:235     the flag is consumed, calling ring->funcs->emit_mem_sync
 *   amdgpu_ib.c:283     amdgpu_ring_emit_ib() runs AFTER the sync, so the
 *                       coherence packet precedes the INDIRECT_BUFFER
 *                       descriptor IN THE SAME RING
 *   gfx_v8_0.c:6761     gfx_v8_0_emit_mem_sync      -> PACKET3_SURFACE_SYNC
 *   gfx_v8_0.c:6774     gfx_v8_0_emit_mem_sync_compute -> PACKET3_ACQUIRE_MEM
 *   vid.h:201,334       opcodes 0x43 and 0x58
 *   vid.h:215-224       the five *_ACTION_ENA bits
 */
#ifndef RX550_VIS_H
#define RX550_VIS_H

#include "rx550_addr.h"

/* --------------------------------------------------------- packet identity
 * Values are GFX8-specific and are asserted by the test suite so they cannot
 * drift away from the corpus.
 */
#define RX550_OP_SURFACE_SYNC  0x43u  /* vid.h:201 — gfx ring       */
#define RX550_OP_ACQUIRE_MEM   0x58u  /* vid.h:334 — compute ring    */

/* CP_COHER_CNTL: the five actions the reference enables.  gfx_v8_0.c:6764-6768
 * TCL1(22) | TC(23) | SH_KCACHE(27) | SH_ICACHE(29) | TC_WB(18) = 0x28C40000
 * These invalidate texture and L2 caches.  A value of 0xFFFFFFFF for
 * CP_COHER_SIZE with base 0 is the corpus's "whole address range" encoding;
 * its hardware interpretation is NOT_DETERMINED here. */
#define RX550_COHER_CNTL 0x28C40000u
#define RX550_COHER_SIZE 0xFFFFFFFFu
#define RX550_COHER_BASE 0x00000000u
#define RX550_COHER_POLL 0x0000000Au   /* gfx_v8_0.c:6769,6773 */

#define RX550_SURFACE_SYNC_DW  5u   /* header + 4 payload */
#define RX550_ACQUIRE_MEM_DW   7u   /* header + 6 payload */

enum rx550_ring_kind {
	RX550_RING_GFX = 0,      /* gfx_v8_0_emit_mem_sync       */
	RX550_RING_COMPUTE       /* gfx_v8_0_emit_mem_sync_compute */
};

/* ------------------------------------------------------------- the packet
 * Encodes the coherence packet into `out`, which must hold at least
 * RX550_ACQUIRE_MEM_DW entries.  Returns the DW count written, or 0 on a bad
 * argument.  This is an ENCODER OF A KNOWN STREAM, not a barrier: emitting it
 * has no effect until some other component publishes it to a ring.
 */
uint32_t rx550_vis_encode_mem_sync(enum rx550_ring_kind kind, uint32_t *out,
				   uint32_t out_dw);

uint32_t rx550_vis_packet_dw(enum rx550_ring_kind kind);

/* ------------------------------------------------------- the ordering model
 * The invariant the corpus demonstrates: the coherence packet is written to
 * the ring BEFORE the INDIRECT_BUFFER descriptor, so the CP encounters the
 * invalidate first.  A driver that reorders them has changed what the
 * hardware sees, whether or not the CPU-side code "looks right".
 *
 * This models a ring as an ordered sequence of records.  It never touches a
 * ring: the ring is a caller-owned array the model merely indexes.
 */
enum rx550_ring_rec {
	RX550_REC_MEM_SYNC = 0,
	RX550_REC_IB_DESCRIPTOR
};

/* offset in DW within the ring, or RX550_VIS_ABSENT */
#define RX550_VIS_ABSENT 0xffffffffu

int rx550_vis_record(enum rx550_ring_rec rec, uint32_t dw_offset,
		     uint32_t *out_dw_len);

/* True when the ordering the corpus relies on holds.  A descriptor with no
 * preceding coherence packet FAILS this, deliberately: that is the exact
 * inversion the experiment must not perform. */
int rx550_vis_order_ok(uint32_t sync_offset, uint32_t descriptor_offset);

#endif /* RX550_VIS_H */
