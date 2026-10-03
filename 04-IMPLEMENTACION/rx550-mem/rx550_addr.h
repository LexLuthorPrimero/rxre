/* rx550_addr.h — address-space vocabulary and minimal buffer object for the
 * RX 550 (Polaris12 / GFX8) driver.
 *
 * SCOPE: pure data.  No hardware, no allocation, no DRM, no PCI, no PM4
 * dependency.  This header does NOT include pm4.h and must not.
 *
 * WHY THIS EXISTS: the PM4 encoder takes a `uint64_t gpu_va` with no notion
 * of which address space it belongs to.  Every value passed to
 * rx550_pm4_emit_ib_descriptor() must come from a producer that has declared
 * the space.  This component is that declaration.
 *
 * RATIONALE FOR EVERY CONSTANT is in ADDRESS-SPACE.md.  Nothing here is
 * inherited from amdgpu's structures; only the hardware-forced numeric limits
 * are carried, each with a source.
 */
#ifndef RX550_ADDR_H
#define RX550_ADDR_H

#include <stdint.h>

/* ------------------------------------------------------------------ spaces
 * "address" is never a bare type in this component.  Every address carries
 * the space it belongs to, so a GPU VA can never be mistaken for a CPU one.
 */
typedef enum {
	RX550_AS_NONE = 0,
	RX550_AS_CPU_VA,     /* process virtual address                    */
	RX550_AS_CPU_PA,     /* physical / bus address, opaque to us        */
	RX550_AS_PCI_BAR,    /* device MMIO window (BAR)                    */
	RX550_AS_GPU_GART,   /* GART virtual address.  This is what the
			     * PACKET3_INDIRECT_BUFFER address field
			     * carries for a system-memory IB.              */
	RX550_AS_GPU_VRAM_PA /* VRAM physical address in the MC space       */
} rx550_addr_space;

/* ------------------------------------------------------------------ domains
 * Where the backing store lives.  A domain is not an address space: a GTT
 * buffer is system memory, and the GPU reaches it through the GART space.
 */
typedef enum {
	RX550_DOM_NONE = 0,
	RX550_DOM_GTT,   /* system RAM, reached through GART    */
	RX550_DOM_VRAM   /* device VRAM                          */
} rx550_domain;

/* ------------------------------------------------------------------ lifetime
 * A buffer moves forward only.  Re-publishing a released buffer, or
 * releasing one that was never published, is an error rather than a silent
 * no-op: a half-valid ownership chain is how a use-after-free survives
 * review.
 */
typedef enum {
	RX550_BUF_EMPTY = 0,
	RX550_BUF_ALLOCATED,   /* backing storage reserved, not GPU-visible  */
	RX550_BUF_PUBLISHED,   /* GPU-visible address attached and valid     */
	RX550_BUF_RELEASED
} rx550_buf_state;

typedef enum {
	RX550_OK = 0,
	RX550_EINVAL,      /* NULL, bad enum, nonsensical geometry        */
	RX550_ESTATE,      /* operation not legal in the current state    */
	RX550_EOWNER,      /* owner mismatch                               */
	RX550_EALIGN,      /* alignment requirement not met                */
	RX550_EBOUNDS      /* address outside the declared window           */
} rx550_status;

/* --------------------------------------------------- GFX8 forced constants
 * Each value is a hardware or pool requirement, not a preference.
 */

/* GART window size when no override is given and the GPU has no 4 GB page
 * support: gmc_v8_0.c:595  -> 256 MiB.  gmc_v8_0.c:601 uses 1024 MiB when
 * 4 GB pages are supported.  The driver must be told which; it does not
 * guess. */
#define RX550_GART_SIZE_DEFAULT_MB   256u
#define RX550_GART_SIZE_4GBPG_MB     1024u

/* Every GPU-visible address in this component is constrained to fit the
 * PACKET3_INDIRECT_BUFFER field: gfx_v8_0.c:6096-6097 encodes
 * `addr & 0xFFFFFFFC` in the low DWORD and `(addr >> 32) & 0xFFFF` in the
 * high one.  That is 46 address bits with 4-byte granularity. */
#define RX550_GART_ADDR_BITS   46
#define RX550_GART_ADDR_MASK   ((UINT64_C(1) << RX550_GART_ADDR_BITS) - UINT64_C(1))

/* Minimum granularity a GTT IB must satisfy.  gfx_v8_0.c:6096 masks the low
 * two bits, so a 4-byte-aligned address is the only one that survives
 * encoding unchanged. */
#define RX550_IB_ALIGN_MIN 4u

/* Alignment the amdgpu IB pools are cut with: amdgpu_ib.c:361 passes 256.
 * This is a pool policy, not a hardware requirement, and is recorded as
 * such: a first driver may use any alignment >= RX550_IB_ALIGN_MIN. */
#define RX550_IB_POOL_ALIGN 256u

/* Size of one amdgpu IB pool, for reference only: amdgpu_ring.h:71
 * (1024*1024).  NOT a constraint on a single IB. */
#define RX550_IB_POOL_SIZE_BYTES (1024u * 1024u)

/* ------------------------------------------------------------------ window
 * The MC address window the GART occupies.  amdgpu_gmc.c:264 derives
 * gart_end = gart_start + gart_size - 1, and :314 places the window at the
 * top of the MC address range.  A driver must be given the window; this
 * component never guesses a base address.
 */
struct rx550_gart_window {
	uint64_t base;   /* first usable GPU address        */
	uint64_t size;   /* in bytes, page-multiple         */
};

int rx550_gart_window_valid(const struct rx550_gart_window *w);

/* ------------------------------------------------------------------ buffer */
struct rx550_buf {
	void      *cpu_ptr;          /* NULL when there is no CPU mapping */
	rx550_addr_space cpu_space;  /* space cpu_ptr belongs to          */

	uint64_t   gpu_va;
	rx550_addr_space gpu_space;  /* space gpu_va belongs to           */
	rx550_domain domain;

	uint32_t    size_bytes;
	uint32_t    align_bytes;

	uint32_t    owner;           /* opaque; 0 means unowned           */
	rx550_buf_state state;
};

/* The GART window the buffer is validated against.  Kept in the buffer so a
 * published address can always be re-checked without external state. */
struct rx550_buf_ctx {
	struct rx550_gart_window gart;
	uint32_t next_owner_id;      /* monotonic; 0 reserved as unowned  */
};

void rx550_buf_ctx_init(struct rx550_buf_ctx *ctx, uint64_t gart_base,
			uint64_t gart_size);

/* owner == 0 allocates a fresh id; any non-zero value is honoured as-is so
 * a caller can model an externally owned buffer. */
int rx550_buf_alloc(struct rx550_buf_ctx *ctx, struct rx550_buf *b,
		    uint32_t size_bytes, uint32_t align_bytes,
		    rx550_domain domain, uint32_t owner);
int rx550_buf_attach_cpu(struct rx550_buf *b, void *cpu_ptr,
			 rx550_addr_space space);
int rx550_buf_publish(struct rx550_buf *b, uint64_t gpu_va,
		      rx550_addr_space space);
int rx550_buf_release(struct rx550_buf *b, uint32_t owner);

int rx550_buf_size(const struct rx550_buf *b);
int rx550_buf_usable_dw(const struct rx550_buf *b);
int rx550_buf_is_published(const struct rx550_buf *b);
int rx550_buf_address_in_window(const struct rx550_buf *b,
				const struct rx550_gart_window *w);

/* True when a PM4 IB descriptor could carry this buffer's address, i.e. the
 * address fits the 46-bit field and the 4-byte granularity.  This is the
 * contract the PM4 encoder's own validation will re-check; the two must not
 * disagree. */
int rx550_buf_addr_encodable(const struct rx550_buf *b);

#endif /* RX550_ADDR_H */
