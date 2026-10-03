/* rx550_sub.h — GFX8 submission contract model.
 *
 * SCOPE: pure data, pure state machine.  It models what a submission IS and
 * what can be claimed about it.  It performs no MMIO write, no doorbell, no
 * DMA, and it never claims that a packet executed.
 *
 * THE CENTRAL RULE.  `EXECUTED` is deliberately absent from the state
 * machine.  The corpus provides no observation that distinguishes "the CP
 * consumed the commands" from "the CP executed them on the shader".  A model
 * that carried an EXECUTED state would manufacture the very inference this
 * project has been forbidden to make.  Consumption is observable; execution
 * is an EXTERNAL boundary, represented here only as an explicit unknown.
 *
 * EVIDENCE (drivers/gpu/drm/amd/, project corpus linux-7.1.3, GFX8 only).
 * Paths in brackets.  Register indices are from
 * include/asic_reg/gca/gfx_8_0_d.h; byte offset = index * 4, which
 * amdgpu_debugfs_process_reg_op performs as RREG32(*pos >> 2).
 */
#ifndef RX550_SUB_H
#define RX550_SUB_H

#include "rx550_addr.h"

/* ------------------------------------------------------------ register table
 * Values below are byte offsets into the GFX aperture, i.e. index * 4.
 * Re-derived independently of the EP08 harness; the two agree exactly. */
#define RX550_REG_CP_RB0_RPTR            0x008700u  /* idx 0x21c0 */
#define RX550_REG_CP_RB0_WPTR            0x00c114u  /* idx 0x3045 */
#define RX550_REG_CP_RB_WPTR_POLL_ADDR_LO 0x00c118u /* idx 0x3046 */
#define RX550_REG_CP_RB_WPTR_POLL_ADDR_HI 0x00c11cu /* idx 0x3047 */
#define RX550_REG_CP_RB_WPTR_POLL_CNTL   0x008708u  /* idx 0x21c2 */
#define RX550_REG_CP_RB_DOORBELL_CONTROL 0x00c164u  /* idx 0x3059 */
#define RX550_REG_GRBM_STATUS            0x008010u  /* idx 0x2004 */
#define RX550_REG_GRBM_STATUS2           0x008008u  /* idx 0x2002 */
#define RX550_REG_CP_BUSY_STAT           0x00867cu  /* idx 0x219f */

/* CP_RB_DOORBELL_CONTROL field layout.
 * include/asic_reg/gca/gfx_8_0_sh_mask.h:1745-1752 */
#define RX550_DB_OFFSET_MASK   0x7ffffcu
#define RX550_DB_OFFSET_SHIFT  2
#define RX550_DB_EN_MASK       0x40000000u
#define RX550_DB_EN_SHIFT      30
#define RX550_DB_HIT_MASK      0x80000000u
#define RX550_DB_HIT_SHIFT     31

/* Value amdgpu installs into POLL_CNTL on the ASICs that program it:
 * gfx_v8_0.c:303,466,567,673.  NOT installed on Polaris 12 — see the
 * POLARIS12 golden-settings check in CONTRACTS/016.  Carried here only so the
 * contrast is explicit and testable; no GFX8 Polaris 12 code may use it. */
#define RX550_POLL_CNTL_TONGA_VALUE 0x00900100u

/* ------------------------------------------------------------------ states
 * A submission only ever moves forward.  See the header comment for why
 * EXECUTED is not here. */
typedef enum {
	RX550_SUB_CREATED = 0,
	RX550_SUB_READY,               /* IB described and validated          */
	RX550_SUB_PUBLISHED,           /* WPTR publication observed          */
	RX550_SUB_CONSUMPTION_OBSERVED,/* RPTR moved                         */
	RX550_SUB_COMPLETED,           /* completion sequence reached         */
	RX550_SUB_RETIRED              /* released                            */
} rx550_sub_state;

/* What we are allowed to say about the work, kept separate from the state.
 * Only CONSUMPTION is an observation this component can ever report. */
typedef enum {
	RX550_CLAIM_NONE = 0,
	RX550_CLAIM_CONSUMPTION,   /* RPTR advanced over the measured window */
	RX550_CLAIM_EXECUTION      /* NEVER set by this component           */
} rx550_claim;

/* --------------------------------------------------------- the submission
 * Mirrors the shape required by the contract, with every field typed. */
struct rx550_submission {
	uint64_t ib_gpu_va;      /* RX550_AS_GPU_GART, 46 bits, 4-aligned     */
	uint32_t ib_length_dw;   /* PM4 payload DWORDs, not bytes            */

	uint32_t wptr_before;    /* ring WPTR before publication             */
	uint32_t wptr_after;     /* ring WPTR after publication              */
	uint32_t rptr_observed;  /* a single RPTR reading, with its context   */
	uint32_t rptr_window_valid; /* 0 = the rptr_observed reading is not
	                              comparable to wptr_before/after        */

	rx550_sub_state state;
	rx550_claim     claim;

	uint32_t doorbell_configured; /* CP_RB_DOORBELL_CONTROL was programmed */
	uint32_t doorbell_published;  /* a doorbell aperture write occurred   */
	uint32_t poll_configured;     /* ADDR_LO/HI programmed; see note      */
	uint32_t owner;
};

void rx550_sub_init(struct rx550_submission *s, uint32_t owner);

/* Builds a submission from a buffer that the memory layer has already
 * validated.  Takes the BUFFER, not a bare address, so the address space
 * cannot be lost between layers. */
int rx550_sub_create(struct rx550_submission *s, uint32_t owner,
		     const struct rx550_buf *b);

/* READY: the descriptor is well formed. */
int rx550_sub_mark_ready(struct rx550_submission *s);

/* PUBLISHED: the WPTR moved.  Monotonicity is enforced: WPTR is a ring
 * cursor, so it may only advance, and a value that goes backwards is a
 * contract violation, not a wrap. */
int rx550_sub_mark_published(struct rx550_submission *s, uint32_t wptr_after);

/* CONSUMPTION_OBSERVED: an RPTR reading that is comparable to the
 * publication window advanced past wptr_before.  The caller must declare
 * whether the reading is comparable; an incomparable reading is refused
 * rather than compared. */
int rx550_sub_mark_consumption(struct rx550_submission *s, uint32_t rptr,
			       int comparable);

/* COMPLETED: the completion sequence reached.  `seq_ok` is the caller's
 * statement that the completion write was observed; this component cannot
 * observe memory and therefore cannot assert it. */
int rx550_sub_mark_completed(struct rx550_submission *s, int seq_ok);

int rx550_sub_retire(struct rx550_submission *s, uint32_t owner);

rx550_sub_state rx550_sub_state_get(const struct rx550_submission *s);
rx550_claim     rx550_sub_claim_get(const struct rx550_submission *s);

/* The only inference this component will make.  It reports whether the
 * observed RPTR is consistent with the CP having consumed the published
 * work — and explicitly does NOT report execution. */
int rx550_sub_rptr_advanced(const struct rx550_submission *s);

/* True when a doorbell was actually published.  WPTR publication through
 * memory-mapped WB is NOT a doorbell; the two are separate mechanisms and
 * this function must not conflate them. */
int rx550_sub_doorbell_published(const struct rx550_submission *s);

/* WPTR_POLL_CNTL as it would be programmed.  Returns 0 for the Polaris 12
 * path, which does not program it: gfx_v8_0.c writes POLL_CNTL only inside
 * the *_mgcg_cgcg_init[] tables, and the CHIP_POLARIS12 case programs
 * golden_settings_polaris11_a11 and polaris11_golden_common_all, neither of
 * which contains it.  A zero return is an ABSENCE of programming and says
 * nothing about whether polling is enabled, sufficient or irrelevant. */
uint32_t rx550_sub_poll_cntl_value(int is_polaris12_path);

#endif /* RX550_SUB_H */
