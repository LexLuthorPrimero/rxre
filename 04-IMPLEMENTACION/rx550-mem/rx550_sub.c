/* rx550_sub.c — GFX8 submission contract model.  Pure state machine. */

#include "rx550_sub.h"

void rx550_sub_init(struct rx550_submission *s, uint32_t owner)
{
	if (!s)
		return;
	s->ib_gpu_va = 0u;
	s->ib_length_dw = 0u;
	s->wptr_before = 0u;
	s->wptr_after = 0u;
	s->rptr_observed = 0u;
	s->rptr_window_valid = 0u;
	s->state = RX550_SUB_CREATED;
	s->claim = RX550_CLAIM_NONE;
	s->doorbell_configured = 0u;
	s->doorbell_published = 0u;
	s->poll_configured = 0u;
	s->owner = owner;
}

int rx550_sub_create(struct rx550_submission *s, uint32_t owner,
		     const struct rx550_buf *b)
{
	if (!s || !b)
		return RX550_EINVAL;
	if (b->state != RX550_BUF_PUBLISHED)
		return RX550_ESTATE;
	/* The address must be one the descriptor can actually carry, and the
	 * memory layer is the single place that knows the space. */
	if (!rx550_buf_addr_encodable(b))
		return RX550_EBOUNDS;

	rx550_sub_init(s, owner);
	s->ib_gpu_va    = b->gpu_va;
	s->ib_length_dw = (uint32_t)(b->size_bytes / 4u);
	if (s->ib_length_dw == 0u)
		return RX550_EINVAL;
	return RX550_OK;
}

int rx550_sub_mark_ready(struct rx550_submission *s)
{
	if (!s)
		return RX550_EINVAL;
	if (s->state != RX550_SUB_CREATED)
		return RX550_ESTATE;
	if (s->ib_gpu_va == 0u || s->ib_length_dw == 0u)
		return RX550_EINVAL;
	s->state = RX550_SUB_READY;
	return RX550_OK;
}

int rx550_sub_mark_published(struct rx550_submission *s, uint32_t wptr_after)
{
	if (!s)
		return RX550_EINVAL;
	if (s->state != RX550_SUB_READY)
		return RX550_ESTATE;
	/* WPTR is a ring cursor.  A value below the starting point is a
	 * contract violation; this model does not implement wraparound
	 * because nothing in the closed path needs it, and guessing the
	 * ring size would be inventing a constraint. */
	if (wptr_after < s->wptr_before)
		return RX550_EALIGN;
	if (wptr_after == s->wptr_before)
		return RX550_EALIGN;   /* publication must advance the cursor */

	s->wptr_after = wptr_after;
	s->state = RX550_SUB_PUBLISHED;
	return RX550_OK;
}

int rx550_sub_mark_consumption(struct rx550_submission *s, uint32_t rptr,
			       int comparable)
{
	if (!s)
		return RX550_EINVAL;
	if (s->state != RX550_SUB_PUBLISHED)
		return RX550_ESTATE;
	/* A reading that cannot be placed in the same window as wptr_before
	 * must not be compared against it.  Refusing is the honest answer. */
	if (!comparable)
		return RX550_ESTATE;

	s->rptr_observed = rptr;
	s->rptr_window_valid = 1u;
	/* Consumption is the ONLY claim this component can make, and it makes
	 * it only when the reading actually advanced past the pre-publication
	 * cursor. */
	if (rptr > s->wptr_before)
		s->claim = RX550_CLAIM_CONSUMPTION;
	s->state = RX550_SUB_CONSUMPTION_OBSERVED;
	return RX550_OK;
}

int rx550_sub_mark_completed(struct rx550_submission *s, int seq_ok)
{
	if (!s)
		return RX550_EINVAL;
	if (s->state != RX550_SUB_CONSUMPTION_OBSERVED)
		return RX550_ESTATE;
	/* The caller asserts the completion write was seen.  This component
	 * cannot check it, and it never upgrades the claim: completion is not
	 * execution. */
	if (!seq_ok)
		return RX550_ESTATE;
	s->state = RX550_SUB_COMPLETED;
	return RX550_OK;
}

int rx550_sub_retire(struct rx550_submission *s, uint32_t owner)
{
	if (!s)
		return RX550_EINVAL;
	if (s->state == RX550_SUB_CREATED || s->state == RX550_SUB_RETIRED)
		return RX550_ESTATE;
	if (owner == 0u || owner != s->owner)
		return RX550_EOWNER;
	s->state = RX550_SUB_RETIRED;
	return RX550_OK;
}

rx550_sub_state rx550_sub_state_get(const struct rx550_submission *s)
{
	return s ? s->state : RX550_SUB_CREATED;
}

rx550_claim rx550_sub_claim_get(const struct rx550_submission *s)
{
	return s ? s->claim : RX550_CLAIM_NONE;
}

int rx550_sub_rptr_advanced(const struct rx550_submission *s)
{
	if (!s)
		return 0;
	if (!s->rptr_window_valid)
		return 0;
	return s->rptr_observed > s->wptr_before;
}

int rx550_sub_doorbell_published(const struct rx550_submission *s)
{
	return s ? (int)s->doorbell_published : 0;
}

uint32_t rx550_sub_poll_cntl_value(int is_polaris12_path)
{
	/* NOT a claim about polling semantics.  It reports only whether the
	 * driver programs the register on this path, and for Polaris 12 the
	 * answer is no. */
	return is_polaris12_path ? 0u : RX550_POLL_CNTL_TONGA_VALUE;
}
