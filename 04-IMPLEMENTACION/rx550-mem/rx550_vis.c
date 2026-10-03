/* rx550_vis.c — CPU->GPU visibility contract for a GFX8 indirect buffer.
 * Pure data.  See rx550_vis.h for the evidence record. */

#include "rx550_vis.h"

uint32_t rx550_vis_packet_dw(enum rx550_ring_kind kind)
{
	return kind == RX550_RING_COMPUTE ? RX550_ACQUIRE_MEM_DW
					  : RX550_SURFACE_SYNC_DW;
}

uint32_t rx550_vis_encode_mem_sync(enum rx550_ring_kind kind, uint32_t *out,
				   uint32_t out_dw)
{
	uint32_t need;

	if (!out)
		return 0u;
	need = rx550_vis_packet_dw(kind);
	if (out_dw < need)
		return 0u;

	if (kind == RX550_RING_COMPUTE) {
		/* gfx_v8_0.c:6774-6783: PACKET3(ACQUIRE_MEM, 5) then
		 * cntl, size, size_hi, base, base_hi, poll. */
		out[0] = (3u << 30) | (RX550_OP_ACQUIRE_MEM << 8) | (5u << 16);
		out[1] = RX550_COHER_CNTL;
		out[2] = RX550_COHER_SIZE;
		out[3] = 0x000000ffu;   /* CP_COHER_SIZE_HI */
		out[4] = RX550_COHER_BASE;
		out[5] = 0x00000000u;   /* CP_COHER_BASE_HI */
		out[6] = RX550_COHER_POLL;
	} else {
		/* gfx_v8_0.c:6761-6771: PACKET3(SURFACE_SYNC, 3) then
		 * cntl, size, base, poll. */
		out[0] = (3u << 30) | (RX550_OP_SURFACE_SYNC << 8) | (3u << 16);
		out[1] = RX550_COHER_CNTL;
		out[2] = RX550_COHER_SIZE;
		out[3] = RX550_COHER_BASE;
		out[4] = RX550_COHER_POLL;
	}
	return need;
}

int rx550_vis_record(enum rx550_ring_rec rec, uint32_t dw_offset,
		     uint32_t *out_dw_len)
{
	uint32_t len;

	switch (rec) {
	case RX550_REC_MEM_SYNC:
		len = RX550_SURFACE_SYNC_DW;   /* gfx ring is the minimum */
		break;
	case RX550_REC_IB_DESCRIPTOR:
		len = 4u;   /* header + addr_lo + addr_hi + control */
		break;
	default:
		return RX550_EINVAL;
	}
	if (out_dw_len)
		*out_dw_len = len;
	return (int)dw_offset;
}

int rx550_vis_order_ok(uint32_t sync_offset, uint32_t descriptor_offset)
{
	if (sync_offset == RX550_VIS_ABSENT)
		return 0;   /* no coherence packet at all: contract not met */
	if (descriptor_offset == RX550_VIS_ABSENT)
		return 0;
	/* The coherence packet must START strictly before the descriptor.
	 * Equal offsets would mean both records claim the same slot, which is
	 * an overlap, not an ordering. */
	return sync_offset < descriptor_offset;
}
