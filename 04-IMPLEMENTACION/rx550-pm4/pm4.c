/* pm4.c — RX550 (Polaris12 / GFX8) PM4 command layer, software only.
 * See pm4.h for scope limits and EVIDENCE.md for the source record. */

#include "pm4.h"

/* ------------------------------------------------------------------ buffer */

void rx550_pm4_buf_init(struct rx550_pm4_buf *b, uint32_t *storage, uint32_t cap_dw)
{
	if (!b)
		return;
	b->dw      = storage;
	b->cap_dw  = cap_dw;
	b->used_dw = 0;
}

void rx550_pm4_buf_reset(struct rx550_pm4_buf *b)
{
	if (!b)
		return;
	/* Determinism: a reset buffer never leaks previous contents. */
	if (b->dw && b->cap_dw)
		for (uint32_t i = 0; i < b->cap_dw; i++)
			b->dw[i] = 0;
	b->used_dw = 0;
}

uint32_t rx550_pm4_buf_count(const struct rx550_pm4_buf *b)
{
	return b ? b->used_dw : 0;
}

uint32_t rx550_pm4_buf_capacity(const struct rx550_pm4_buf *b)
{
	return b ? b->cap_dw : 0;
}

uint32_t rx550_pm4_buf_free(const struct rx550_pm4_buf *b)
{
	if (!b || b->used_dw >= b->cap_dw)
		return 0;
	return b->cap_dw - b->used_dw;
}

int rx550_pm4_buf_append(struct rx550_pm4_buf *b, const uint32_t *src, uint32_t n_dw)
{
	if (!b || !b->dw || !src)
		return RX550_PM4_EINVAL;
	if (n_dw == 0)
		return RX550_PM4_EINVAL;
	if (n_dw > b->cap_dw - b->used_dw)
		return RX550_PM4_ENOSPC;   /* transactional: nothing written */
	for (uint32_t i = 0; i < n_dw; i++)
		b->dw[b->used_dw + i] = src[i];
	b->used_dw += n_dw;
	return RX550_PM4_OK;
}

int rx550_pm4_buf_append_dw(struct rx550_pm4_buf *b, uint32_t v)
{
	return rx550_pm4_buf_append(b, &v, 1);
}

int rx550_pm4_buf_dw(const struct rx550_pm4_buf *b, uint32_t idx, uint32_t *out)
{
	if (!b || !b->dw || !out)
		return RX550_PM4_EINVAL;
	if (idx >= b->used_dw)
		return RX550_PM4_ERANGE;
	*out = b->dw[idx];
	return RX550_PM4_OK;
}

/* ------------------------------------------------------------------ header */

uint32_t rx550_pm4_hdr(uint8_t opcode, uint32_t payload_dw)
{
	/* GFX8 count field == payload_dw - 1; a packet with zero payload DW has
	 * no encoding in this corpus, so it is rejected by the callers below
	 * rather than silently encoded with a wrapped count. */
	uint32_t count = payload_dw - 1u;

	return ((uint32_t)RX550_PM4_HDR_TYPE3 << RX550_PM4_HDR_TYPE_SHIFT)
	     | (((uint32_t)opcode & RX550_PM4_HDR_OPCODE_MASK) << RX550_PM4_HDR_OPCODE_SHIFT)
	     | ((count & RX550_PM4_HDR_COUNT_MASK) << RX550_PM4_HDR_COUNT_SHIFT);
}

uint32_t rx550_pm4_hdr_type(uint32_t hdr)
{
	return (hdr >> RX550_PM4_HDR_TYPE_SHIFT) & 0x3u;
}

uint32_t rx550_pm4_hdr_opcode(uint32_t hdr)
{
	return (hdr >> RX550_PM4_HDR_OPCODE_SHIFT) & RX550_PM4_HDR_OPCODE_MASK;
}

uint32_t rx550_pm4_hdr_count(uint32_t hdr)
{
	return (hdr >> RX550_PM4_HDR_COUNT_SHIFT) & RX550_PM4_HDR_COUNT_MASK;
}

/* ----------------------------------------------------------------- encoders */

int rx550_pm4_emit_sh_set_reg(struct rx550_pm4_buf *b, uint32_t reg, uint32_t value)
{
	uint32_t p[3];

	if (!b || !b->dw)
		return RX550_PM4_EINVAL;
	/* The encoder sends (reg - START); a register below START has no
	 * encoding in this corpus. Rejected instead of wrapping. */
	if (reg < RX550_PM4_SET_SH_REG_START)
		return RX550_PM4_ERANGE;

	p[0] = rx550_pm4_hdr(RX550_PM4_OP_SET_SH_REG, 2);
	p[1] = reg - RX550_PM4_SET_SH_REG_START;
	p[2] = value;
	return rx550_pm4_buf_append(b, p, 3);
}

int rx550_pm4_emit_sh_set_reg64(struct rx550_pm4_buf *b, uint32_t reg, uint64_t value)
{
	uint32_t p[4];

	if (!b || !b->dw)
		return RX550_PM4_EINVAL;
	if (reg < RX550_PM4_SET_SH_REG_START)
		return RX550_PM4_ERANGE;

	p[0] = rx550_pm4_hdr(RX550_PM4_OP_SET_SH_REG, 3);
	p[1] = reg - RX550_PM4_SET_SH_REG_START;
	p[2] = (uint32_t)(value & 0xffffffffu);
	p[3] = (uint32_t)(value >> 32);
	return rx550_pm4_buf_append(b, p, 4);
}

int rx550_pm4_emit_dispatch_direct(struct rx550_pm4_buf *b, uint32_t x, uint32_t y,
                                   uint32_t z, uint32_t initiator)
{
	uint32_t p[5];

	if (!b || !b->dw)
		return RX550_PM4_EINVAL;

	p[0] = rx550_pm4_hdr(RX550_PM4_OP_DISPATCH_DIRECT, 4);
	p[1] = x;
	p[2] = y;
	p[3] = z;
	p[4] = initiator;
	return rx550_pm4_buf_append(b, p, 5);
}

int rx550_pm4_emit_event_write(struct rx550_pm4_buf *b, uint32_t type, uint32_t index)
{
	uint32_t p[2];

	if (!b || !b->dw)
		return RX550_PM4_EINVAL;
	if (type > 0xffu || index > 0xffffffu)
		return RX550_PM4_ERANGE;

	p[0] = rx550_pm4_hdr(RX550_PM4_OP_EVENT_WRITE, 1);
	p[1] = RX550_PM4_EVENT_TYPE(type) | RX550_PM4_EVENT_INDEX(index);
	return rx550_pm4_buf_append(b, p, 2);
}

int rx550_pm4_emit_ib_descriptor(struct rx550_pm4_buf *b, uint64_t gpu_va,
                                 uint32_t length_dw, uint32_t vmid,
                                 uint32_t flags, int is_const_ib)
{
	uint32_t p[4];
	uint8_t  op;

	if (!b || !b->dw)
		return RX550_PM4_EINVAL;
	/* The reference masks the low two bits away (gfx_v8_0.c:6096). Silently
	 * dropping address bits is how an address quietly stops being the one
	 * the caller asked for, so the encoder rejects it instead. */
	if (gpu_va & 0x3u)
		return RX550_PM4_ERANGE;
	/* The field is 46 address bits (lo DW bits 31:2, hi DW bits 47:32, of
	 * which only 45:32 are address).  A wider value would have its high
	 * bits truncated by the & 0xFFFF at gfx_v8_0.c:6097; reject it. */
	if (gpu_va >> RX550_PM4_IB_ADDR_BITS)
		return RX550_PM4_ERANGE;
	if (length_dw > 0xffffffu)
		return RX550_PM4_ERANGE;
	if (vmid > 0xffu)
		return RX550_PM4_ERANGE;

	op = is_const_ib ? RX550_PM4_OP_INDIRECT_BUFFER_CONST
	                 : RX550_PM4_OP_INDIRECT_BUFFER;

	p[0] = rx550_pm4_hdr(op, 3);
	p[1] = (uint32_t)(gpu_va & RX550_PM4_IB_ADDR_LO_MASK);
	p[2] = (uint32_t)((gpu_va >> 32) & RX550_PM4_IB_ADDR_HI_MASK);
	p[3] = flags | length_dw | (vmid << RX550_PM4_IB_VMID_SHIFT);
	return rx550_pm4_buf_append(b, p, 4);
}
