/* pm4.h — RX550 (Polaris12 / GFX8) PM4 command layer.
 *
 * SCOPE: software representation and encoding only.
 *   NO pci_*, NO ioremap, NO readl/writel, NO DMA, NO IRQ, NO doorbell,
 *   NO ring submission, NO GPU access of any kind.
 *
 * WHAT THIS PROVES:  ENCODING = the emitted DW stream has the chosen format.
 * WHAT THIS DOES NOT PROVE: SUBMISSION, FETCH, EXECUTION.  An encoded packet
 * is not a submitted packet and not an executed packet.
 *
 * Every constant below carries a SOURCE line into the project's own kernel
 * corpus (linux-7.1.3).  See EVIDENCE.md for the full record.
 */
#ifndef RX550_PM4_H
#define RX550_PM4_H

#include <stdint.h>

/* ------------------------------------------------------------------ status */
typedef enum {
	RX550_PM4_OK        =  0,
	RX550_PM4_EINVAL    = -1,  /* NULL / out-of-range argument          */
	RX550_PM4_ENOSPC    = -2,  /* capacity would be exceeded            */
	RX550_PM4_ERANGE    = -3   /* value outside the field it must fit in */
} rx550_pm4_status;

/* ---------------------------------------------------------------- opcodes
 * Source: drivers/gpu/drm/amd/amdgpu/vid.h  (the packet header set that
 * gfx_v8_0.c actually compiles against; verified with `gcc -E -dM`).
 *
 * HAZARD, recorded deliberately: amdgpu/sid.h:372 defines
 * PACKET3_INDIRECT_BUFFER_CONST as 0x31, NOT 0x33.  sid.h is not reached from
 * gfx_v8_0.c, so 0x33 is unambiguous for GFX8 — but copying a value out of
 * sid.h instead of vid.h yields a wrong opcode.  Do not "simplify" this.
 */
#define RX550_PM4_OP_INDIRECT_BUFFER       0x3Fu  /* vid.h:190 */
#define RX550_PM4_OP_INDIRECT_BUFFER_CONST 0x33u  /* vid.h:137 */
#define RX550_PM4_OP_DISPATCH_DIRECT       0x15u  /* vid.h:118 */
#define RX550_PM4_OP_SET_SH_REG            0x76u  /* vid.h:347 */
#define RX550_PM4_OP_EVENT_WRITE           0x46u  /* vid.h:226 */

/* SET_SH_REG address base: the shader register index is sent as
 * (reg - PACKET3_SET_SH_REG_START).  Source: vid.h:348; used at
 * gfx_v8_0.c:1530, 1536, 1556, 1562, 1582, 1588. */
#define RX550_PM4_SET_SH_REG_START 0x00002c00u

/* EVENT_WRITE field layout.  Source: vid.h:227-228. */
#define RX550_PM4_EVENT_TYPE(x)  ((uint32_t)(x) << 0)
#define RX550_PM4_EVENT_INDEX(x) ((uint32_t)(x) << 8)

/* INDIRECT_BUFFER control-DW fields.  Source: vid.h:192, 198. */
#define RX550_PM4_IB_VALID     (1u << 23)
#define RX550_PM4_IB_PRE_ENB(x) ((uint32_t)(x) << 21)
/* control = length_dw | (vmid << 24) | flags.  Source: gfx_v8_0.c:6082, 6107 */
#define RX550_PM4_IB_VMID_SHIFT 24

/* The INDIRECT_BUFFER address field is gpu_addr & 0xFFFFFFFC in the low DW
 * and upper_32_bits(gpu_addr) & 0xFFFF in the high DW (gfx_v8_0.c:6096-6097):
 * 46 address bits, 4-byte granularity.  Source: gfx_v8_0.c:6091-6098.
 * An input wider than IB_ADDR_BITS, or not 4-byte aligned, is REJECTED rather
 * than masked: the reference drops those bits silently. */
#define RX550_PM4_IB_ADDR_BITS    46
#define RX550_PM4_IB_ADDR_LO_MASK 0xfffffffcu
#define RX550_PM4_IB_ADDR_HI_MASK 0x0000ffffu

/* COMPUTE_DISPATCH_INITIATOR.COMPUTE_SHADER_EN = mask 0x1, shift 0.
 * Source: gfx_8_0_sh_mask.h:8235-8236.  The reference stream sets exactly
 * this field and nothing else (gfx_v8_0.c:1545-1546). */
#define RX550_PM4_DISPATCH_SHADER_EN 0x1u

/* ------------------------------------------------- packet3 header (32-bit)
 * PACKET3(op,n) = (3<<30) | ((op & 0xFF) << 8) | ((n & 0x3FFF) << 16)
 * Source: vid.h:105-107.  Decoders: vid.h:92-95 (CP_PACKET_GET_*).
 *
 * COUNT SEMANTICS (FACT, GFX8 corpus, not ISA documentation):
 * across every packet instance in gfx_v8_0.c the count field equals
 * (payload DW count - 1):
 *     SET_SH_REG      1 -> 2 payload   gfx_v8_0.c:1529
 *     SET_SH_REG      2 -> 3 payload   gfx_v8_0.c:1535
 *     DISPATCH_DIRECT 3 -> 4 payload   gfx_v8_0.c:1541
 *     EVENT_WRITE     0 -> 1 payload   gfx_v8_0.c:1549
 *     INDIRECT_BUFFER 2 -> 3 payload   gfx_v8_0.c:6125
 *     WRITE_DATA      3 -> 4 payload   gfx_v8_0.c:891
 * The hardware interpretation of that field is NOT_DETERMINED: no ISA
 * document was available to this component.
 */
#define RX550_PM4_HDR_TYPE3        3u
#define RX550_PM4_HDR_TYPE_SHIFT   30
#define RX550_PM4_HDR_COUNT_SHIFT  16
#define RX550_PM4_HDR_COUNT_MASK   0x3fffu
#define RX550_PM4_HDR_OPCODE_SHIFT 8
#define RX550_PM4_HDR_OPCODE_MASK  0xffu

/* --------------------------------------------------- software IB buffer
 * Caller-owned CPU memory.  No allocation happens in this component.
 */
struct rx550_pm4_buf {
	uint32_t *dw;       /* backing storage, CPU memory, provided by caller */
	uint32_t  cap_dw;   /* capacity in DW                                  */
	uint32_t  used_dw;  /* DW written so far                                */
};

void     rx550_pm4_buf_init(struct rx550_pm4_buf *b, uint32_t *storage, uint32_t cap_dw);
void     rx550_pm4_buf_reset(struct rx550_pm4_buf *b);
uint32_t rx550_pm4_buf_count(const struct rx550_pm4_buf *b);
uint32_t rx550_pm4_buf_capacity(const struct rx550_pm4_buf *b);
uint32_t rx550_pm4_buf_free(const struct rx550_pm4_buf *b);

/* All mutators are transactional: on failure nothing is appended and
 * used_dw is unchanged. */
int rx550_pm4_buf_append_dw(struct rx550_pm4_buf *b, uint32_t v);
int rx550_pm4_buf_append(struct rx550_pm4_buf *b, const uint32_t *src, uint32_t n_dw);
int rx550_pm4_buf_dw(const struct rx550_pm4_buf *b, uint32_t idx, uint32_t *out);

/* ---------------------------------------------------------------- encoder */
uint32_t rx550_pm4_hdr(uint8_t opcode, uint32_t payload_dw);
uint32_t rx550_pm4_hdr_type(uint32_t hdr);
uint32_t rx550_pm4_hdr_opcode(uint32_t hdr);
uint32_t rx550_pm4_hdr_count(uint32_t hdr);

/* SET_SH_REG, one 32-bit value.  3 DW: hdr, reg-START, value. */
int rx550_pm4_emit_sh_set_reg(struct rx550_pm4_buf *b, uint32_t reg, uint32_t value);
/* SET_SH_REG, 64-bit value pair.  4 DW: hdr, reg-START, lo, hi. */
int rx550_pm4_emit_sh_set_reg64(struct rx550_pm4_buf *b, uint32_t reg, uint64_t value);
/* DISPATCH_DIRECT.  5 DW: hdr, x, y, z, initiator. */
int rx550_pm4_emit_dispatch_direct(struct rx550_pm4_buf *b, uint32_t x, uint32_t y,
                                  uint32_t z, uint32_t initiator);
/* EVENT_WRITE.  2 DW: hdr, type|index. */
int rx550_pm4_emit_event_write(struct rx550_pm4_buf *b, uint32_t type, uint32_t index);
/* INDIRECT_BUFFER / INDIRECT_BUFFER_CONST descriptor.  4 DW:
 *   hdr(count 2), addr_lo (gpu_va & 0xFFFFFFFC),
 *   addr_hi (gpu_va>>32 & 0xFFFF), control.
 * `gpu_va` must already be a GPU-visible address supplied by the caller.
 * This component never discovers, allocates or translates one. */
int rx550_pm4_emit_ib_descriptor(struct rx550_pm4_buf *b, uint64_t gpu_va,
                                 uint32_t length_dw, uint32_t vmid,
                                 uint32_t flags, int is_const_ib);

#endif /* RX550_PM4_H */
