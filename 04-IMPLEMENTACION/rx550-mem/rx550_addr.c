/* rx550_addr.c — address-space vocabulary and minimal buffer object.
 * Pure data.  See rx550_addr.h for scope and ADDRESS-SPACE.md for sources. */

#include "rx550_addr.h"

static int is_pow2(uint32_t v)
{
	return v != 0u && (v & (v - 1u)) == 0u;
}

int rx550_gart_window_valid(const struct rx550_gart_window *w)
{
	if (!w)
		return 0;
	if (w->size == 0u)
		return 0;
	/* base + size - 1 must not wrap and must stay inside the field the
	 * PM4 descriptor can carry, otherwise a published address could be
	 * valid in the window and unencodable in the packet. */
	if (w->base > RX550_GART_ADDR_MASK)
		return 0;
	if (w->size - 1u > RX550_GART_ADDR_MASK - w->base)
		return 0;
	return 1;
}

void rx550_buf_ctx_init(struct rx550_buf_ctx *ctx, uint64_t gart_base,
			uint64_t gart_size)
{
	if (!ctx)
		return;
	ctx->gart.base = gart_base;
	ctx->gart.size = gart_size;
	ctx->next_owner_id = 1u;
}

int rx550_buf_alloc(struct rx550_buf_ctx *ctx, struct rx550_buf *b,
		    uint32_t size_bytes, uint32_t align_bytes,
		    rx550_domain domain, uint32_t owner)
{
	if (!ctx || !b)
		return RX550_EINVAL;
	if (size_bytes == 0u)
		return RX550_EINVAL;
	if (!is_pow2(align_bytes))
		return RX550_EINVAL;
	/* A GART-visible buffer must at least meet the granularity the
	 * descriptor field can represent.  VRAM is not bound by that field. */
	if (domain == RX550_DOM_GTT && align_bytes < RX550_IB_ALIGN_MIN)
		return RX550_EALIGN;
	if (domain != RX550_DOM_GTT && domain != RX550_DOM_VRAM)
		return RX550_EINVAL;

	if (b->state != RX550_BUF_EMPTY)
		return RX550_ESTATE;

	b->cpu_ptr   = 0;
	b->cpu_space = RX550_AS_NONE;
	b->gpu_va    = 0u;
	b->gpu_space = RX550_AS_NONE;
	b->domain    = domain;
	b->size_bytes = size_bytes;
	b->align_bytes = align_bytes;
	b->owner     = owner ? owner : ctx->next_owner_id++;
	if (b->owner == 0u)
		b->owner = ctx->next_owner_id++;
	b->state     = RX550_BUF_ALLOCATED;
	return RX550_OK;
}

int rx550_buf_attach_cpu(struct rx550_buf *b, void *cpu_ptr,
			 rx550_addr_space space)
{
	if (!b || !cpu_ptr)
		return RX550_EINVAL;
	if (b->state != RX550_BUF_ALLOCATED)
		return RX550_ESTATE;
	if (space != RX550_AS_CPU_VA && space != RX550_AS_CPU_PA)
		return RX550_EINVAL;

	b->cpu_ptr   = cpu_ptr;
	b->cpu_space = space;
	return RX550_OK;
}

int rx550_buf_publish(struct rx550_buf *b, uint64_t gpu_va,
		      rx550_addr_space space)
{
	if (!b)
		return RX550_EINVAL;
	if (b->state != RX550_BUF_ALLOCATED)
		return RX550_ESTATE;
	if (space != RX550_AS_GPU_GART && space != RX550_AS_GPU_VRAM_PA)
		return RX550_EINVAL;

	/* The reference masks the low two bits away (gfx_v8_0.c:6096). Silently
	 * dropping address bits is how an address quietly stops being the one
	 * the caller asked for, so the encoder rejects it instead. */
	if (gpu_va & 0x3u)
		return RX550_EALIGN;
	/* The field is 46 address bits (lo DW bits 31:2, hi DW bits 47:32, of
	 * which only 45:32 are address).  A wider value would have its high
	 * bits truncated by the & 0xFFFF at gfx_v8_0.c:6097; reject it. */
	if (gpu_va >> RX550_GART_ADDR_BITS)
		return RX550_EBOUNDS;

	b->gpu_va    = gpu_va;
	b->gpu_space = space;
	b->state     = RX550_BUF_PUBLISHED;
	return RX550_OK;
}

int rx550_buf_release(struct rx550_buf *b, uint32_t owner)
{
	if (!b)
		return RX550_EINVAL;
	if (b->state == RX550_BUF_EMPTY || b->state == RX550_BUF_RELEASED)
		return RX550_ESTATE;
	if (owner == 0u || owner != b->owner)
		return RX550_EOWNER;

	b->state = RX550_BUF_RELEASED;
	b->cpu_ptr = 0;
	b->cpu_space = RX550_AS_NONE;
	/* gpu_va and gpu_space are deliberately left intact: a released
	 * buffer keeps the address it had, so a stale use is visible in a
	 * dump rather than silently reading 0. */
	return RX550_OK;
}

int rx550_buf_size(const struct rx550_buf *b)
{
	if (!b)
		return RX550_EINVAL;
	return (int)b->size_bytes;
}

int rx550_buf_usable_dw(const struct rx550_buf *b)
{
	if (!b)
		return RX550_EINVAL;
	return (int)(b->size_bytes / 4u);
}

int rx550_buf_is_published(const struct rx550_buf *b)
{
	return b && b->state == RX550_BUF_PUBLISHED;
}

int rx550_buf_address_in_window(const struct rx550_buf *b,
				const struct rx550_gart_window *w)
{
	if (!b || !w)
		return 0;
	if (b->state != RX550_BUF_PUBLISHED)
		return 0;
	if (b->gpu_space != RX550_AS_GPU_GART)
		return 0;
	if (!rx550_gart_window_valid(w))
		return 0;
	if (b->gpu_va < w->base)
		return 0;
	return (b->gpu_va - w->base) < w->size;
}

int rx550_buf_addr_encodable(const struct rx550_buf *b)
{
	if (!b)
		return 0;
	if (b->state != RX550_BUF_PUBLISHED)
		return 0;
	if (b->gpu_space != RX550_AS_GPU_GART)
		return 0;
	if (b->gpu_va > RX550_GART_ADDR_MASK)
		return 0;
	return (b->gpu_va & (RX550_IB_ALIGN_MIN - 1u)) == 0u;
}
