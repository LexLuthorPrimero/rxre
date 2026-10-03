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
#define RX550_PKT3_WRITE_DATA		0x37	/* sid.h:377 */
#define RX550_PKT3_WAIT_REG_MEM		0x3C	/* sid.h:397 */
#define RX550_PKT3_PFP_SYNC_ME		0x42	/* sid.h:465 */
#define RX550_PKT3_SURFACE_SYNC		0x43	/* vid.h:201 */
#define RX550_PKT3_ACQUIRE_MEM		0x58	/* vid.h:334 */
#define RX550_PKT3_EVENT_WRITE		0x46	/* sid.h:489 */
#define RX550_PKT3_EVENT_WRITE_EOP	0x47	/* sid.h:503 */
#define RX550_PKT3_EVENT_WRITE_EOS	0x48	/* sid.h:515 */
#define RX550_PKT3_SET_SH_REG		0x76	/* sid.h:531 */

/*
 * WRITE_DATA sub-fields. The register number here is ABSOLUTE, unlike SET_SH_REG
 * whose payload is an offset from RX550_PKT3_SET_SH_REG_START. Two different
 * conventions in one ring, and mixing them programs the wrong register without
 * reporting anything.
 */
#define RX550_WRITE_DATA_DST_SEL(x)	((x) << 8)	/* sid.h:378 */
#define RX550_WR_ONE_ADDR		(1u << 16)	/* sid.h:386 */
#define RX550_WR_CONFIRM		(1u << 20)	/* sid.h:387 */
#define RX550_WRITE_DATA_ENGINE_SEL(x)	((x) << 30)	/* sid.h:388 */

/*
 * WAIT_REG_MEM sub-fields. sid.h:398-413.
 *
 * FUNCTION is the comparison operator and 0 is "always", per the enum in the
 * comment at sid.h:399-406. The vm-flush uses FUNCTION(0) with mask 0, which
 * means it does not compare anything: it waits for an event, not for a value.
 * What makes the hardware treat the write to VM_INVALIDATE_REQUEST as the event
 * is NOT_DETERMINED; see findings/029-orden-validacion-fence-no-ring.md.
 */
/*
 * WAIT_REG_MEM sub-fields. From vid.h:169-186 -- NOT sid.h, which has the
 * PACKET3 opcodes but not these. gfx_v8_0.c:33-35 includes vi.h, vi_structs.h and
 * vid.h, so vid.h is the header this ASIC's packets come from.
 */
#define RX550_WAIT_REG_MEM_FUNCTION(x)	((x) << 0)	/* vid.h:169 */
#define RX550_WAIT_REG_MEM_MEM_SPACE(x)	((x) << 4)	/* vid.h:178 */
#define RX550_WAIT_REG_MEM_OPERATION(x)	((x) << 6)	/* vid.h:182 */
#define RX550_WAIT_REG_MEM_ENGINE(x)	((x) << 8)	/* vid.h:186 */

#define RX550_WAIT_REG_MEM_FUNC_ALWAYS	0u		/* vid.h:170-177 */
#define RX550_WAIT_REG_MEM_ENGINE_ME	0u		/* vid.h:187 */
#define RX550_WAIT_REG_MEM_ENGINE_PFP	1u		/* vid.h:188 */
#define RX550_WAIT_REG_MEM_MEM_SPACE_REG 0u		/* vid.h:179 */
#define RX550_WAIT_REG_MEM_MEM_SPACE_MEM 1u		/* vid.h:180 */

/*
 * OPERATION. gfx_v8_0.c uses two values: 0 at :6206 for the vm-flush, commented
 * "wait", and 1 at :6054 for the HDP flush, commented "write, wait, write". Both
 * are on the same register and the same packet type, so the field is real and the
 * vm-flush's zeros are a choice, not an absence of a field.
 */
#define RX550_WAIT_REG_MEM_OP_WAIT	0u		/* gfx_v8_0.c:6206 */
#define RX550_WAIT_REG_MEM_OP_WWW	1u		/* gfx_v8_0.c:6054 */

/*
 * Register addresses needed by the vm-flush path. From gmc/gmc_8_1_d.h, the
 * header gmc_v8_0.c:35 actually includes (not gmc_8_2_d.h; see findings/023-pte-productor-sdma-gfx8.md §4).
 *
 * THE PAGE TABLE BASE REGISTERS ARE NOT ONE ARRAY OF SIXTEEN. They are two
 * disjoint contiguous runs of eight, and the second is at a LOWER address than
 * the first:
 *
 *     mmVM_CONTEXT0_PAGE_TABLE_BASE_ADDR   0x54f
 *     mmVM_CONTEXT1_PAGE_TABLE_BASE_ADDR   0x550
 *     ...                                  stride 1
 *     mmVM_CONTEXT7_PAGE_TABLE_BASE_ADDR   0x556
 *     mmVM_CONTEXT8_PAGE_TABLE_BASE_ADDR   0x50e   <- not 0x557
 *     ...                                  stride 1
 *     mmVM_CONTEXT15_PAGE_TABLE_BASE_ADDR  0x515
 *
 * 0x50e - 0x54f = -0x41. The split at VMID 8 is load-bearing, not a naming
 * artifact, and using one stride-1 array of 16 sends VMIDs 8-15 to
 * 0x557..0x55e, which are mmVM_CONTEXT0/1_PAGE_TABLE_START_ADDR and
 * mmVM_CONTEXT0/1_PAGE_TABLE_END_ADDR. That writes a page-directory address into
 * the GART aperture window and silently changes what GPUVA range is translated.
 * Use rx550_vm_ptba_reg(), which refuses a vmid outside 0-15 rather than
 * computing an address that means something else.
 */
#define RX550_MM_VM_CONTEXT0_PTBA		0x54f	/* gmc_8_1_d.h:636 */
#define RX550_MM_VM_CONTEXT8_PTBA		0x50e	/* gmc_8_1_d.h:607 */
#define RX550_MM_VM_INVALIDATE_REQUEST		0x51e	/* gmc_8_1_d.h:615 */

/** RX550_NUM_VMID: contexts 0-15. VMID 0 is the kernel's GART. */
#define RX550_NUM_VMID			16	/* amdgpu_ids.h:34 */

/**
 * RX550_FIRST_KFD_VMID - the first VMID KFD owns on GFX8.
 *
 * gmc_v8_0.c:1162. VMIDs below it are the DRM/graphics half, at the 0x54f run;
 * at and above it are compute, at the 0x50e run. amdgpu_amdkfd.c:766 uses this
 * as the guard before the KFD PTBA write, so `vmid - 8` there can never
 * underflow -- that is the proof the split is intended, not accidental.
 */
#define RX550_FIRST_KFD_VMID		8	/* gmc_v8_0.c:1162 */

/** Ring engine selectors for WRITE_DATA and WAIT_REG_MEM. sid.h:388, 411-412. */
#define RX550_RING_ENGINE_ME		0u
#define RX550_RING_ENGINE_PFP		1u

/**
 * RX550_VM_FLUSH_DW - dwords rx550_vm_flush() writes, PFP_SYNC_ME included.
 * 5 (PTBA) + 5 (invalidate) + 7 (wait) + 2 (sync). gfx_v8_0.c:6197-6221.
 */
#define RX550_VM_FLUSH_DW		19

/** RX550_VM_FLUSH_DW_NO_PFP: the same sequence without the trailing PFP sync. */
#define RX550_VM_FLUSH_DW_NO_PFP	17

/*
 * The first register addressable by SET_SH_REG. The payload of that packet is
 * an offset from this value, not an absolute register number.
 */
#define RX550_PKT3_SET_SH_REG_START	0x00002c00	/* sid.h:532 */

/*
 * SDMA PACKETS -- a DIFFERENT HEADER FORMAT FROM PACKET3.
 *
 * Everything above is a PACKET3: a 3-bit type at the top, an 8-bit opcode at
 * [15:8] and a 14-bit count. sDMA packets have none of that. From
 * vega10_sdma_pkt_open.h:69-72, which is the header sdma_v4_0.c:53 includes:
 *
 *     #define SDMA_PKT_HEADER_op_offset 0
 *     #define SDMA_PKT_HEADER_op_mask   0x000000FF
 *     #define SDMA_PKT_HEADER_op_shift  0
 *     #define SDMA_PKT_HEADER_OP(x) (((x) & 0x000000FF) << 0)
 *
 * The header is ONE BYTE of opcode in bits 7:0. No packet type, no length
 * field, no compute bit. The sDMA engine knows the packet length from the
 * opcode itself, which is why a truncated sDMA packet is not a parse error but
 * a different instruction stream.
 *
 * Note the provenance, because the name is misleading: vega10_sdma_pkt_open.h
 * is what sdma_v4_0.c includes, and sdma_v4_0.c is the IP block for every
 * SDMA0_HWIP 4.0.0 - 4.4.0 (amdgpu_discovery.c:2549-2560), which is GFX8. The
 * definitions Polaris12 executes are named after another chip. See
 * findings/035-correccion-ptepde-es-polaris12.md for the reasoning and findings/023-pte-productor-sdma-gfx8.md for the error this corrects.
 */
#define RX550_SDMA_PKT_OP_MASK		0x000000ff	/* vega10_sdma_pkt_open.h:70 */
#define RX550_SDMA_PKT_OP_SHIFT		0		/* vega10_sdma_pkt_open.h:71 */

/*
 * The page-table producer. This is the ONLY way a GFX8 GPUVM page table is
 * written on this ASIC, because the CPU writer is unreachable by two
 * independent conditions (findings/023-pte-productor-sdma-gfx8.md §2). Value and name from
 * tonga_sdma_pkt_open.h:37 -- the header of THIS ASIC's SDMA generation.
 * findings/142 measures the rule that decides which generation that is.
 */
/*
 * THE OPCODE IS SDMA_OP_GEN_PTEPDE, NOT SDMA_OP_PTEPDE. MEASURED, NOT ARGUED.
 *
 * This name has been got wrong three times in this header: findings/023-pte-productor-sdma-gfx8.md said
 * GEN_PTEPDE, findings/035-correccion-ptepde-es-polaris12.md corrected it to PTEPDE, findings/043-vuelta-atras-035-y-036-leian-el-asic-equivocado.md reversed it
 * back. Three reversals is not a hard question, it is a sign nobody measured
 * which emitters exist and what each one writes. So:
 *
 * Declaradas en formato CITA=/TERMINO=/ROL=, que tools/citeambig.py --sostiene
 * comprueba: el TERMINO= tiene que aparecer LITERALMENTE en el fichero citado.
 * Un comentario sin TERMINO= no lo comprueba nadie, y esta tabla pasó por cuatro
 * revisiones porque nadie podia dirimirla.
 *
 * CITA=tonga_sdma_pkt_open.h | TERMINO=SDMA_OP_GEN_PTEPDE | ROL=nombre del op 12 que corre, :37
 * CITA=vega10_sdma_pkt_open.h | TERMINO=SDMA_OP_PTEPDE | ROL=la otra generacion, :37
 * CITA=sdma_v3_0.c | TERMINO=SDMA_OP_GEN_PTEPDE | ROL=emisor V2, count plano, :987
 * CITA=sdma_v4_0.c | TERMINO=count - 1 | ROL=convencion V3, la que NO corre, :1649
 * CITA=sdma_v5_0.c | TERMINO=count - 1 | ROL=emisor V3 con macro generico, :1217
 * CITA=vi.c | TERMINO=sdma_v3_1_ip_block | ROL=que bloque añade POLARIS12, :2113
 * CITA=amdgpu_device.c | TERMINO=vi_set_ip_blocks | ROL=la rama que se toma, :2145
 * CITA=sdma_v3_0.c | TERMINO=sdma_v3_1_ip_block | ROL=definicion del bloque, :1693
 *
 *   emisor           nombre del op 12     campo count    SDMA
 *   sdma_v2_4.c:714     GEN_PTEPDE         count        V2
 *   sdma_v3_0.c:987     GEN_PTEPDE         count        V2   <-- THIS ASIC
 *   sdma_v4_0.c:1649    PTEPDE             count - 1    V3
 *   sdma_v4_4_2.c:1245  PTEPDE             count - 1    V3
 *   sdma_v5_0.c:1217    PTEPDE             count - 1    V3
 *   sdma_v5_2.c:1116    PTEPDE             count - 1    V3
 *
 * Six emitters, six of six, no exception: the NAME tracks the COUNT convention
 * exactly. GEN_PTEPDE is not PTEPDE spelled differently, it marks the
 * generation whose PTEPDE takes a plain count. Both name the value 12, so the
 * byte emitted is identical either way and the NAME is the only discriminator.
 *
 * Which generation runs here: CHIP_POLARIS12 (vi.c:2107-2123) adds
 * sdma_v3_1_ip_block, defined in sdma_v3_0.c:1693 with .funcs =
 * &sdma_v3_0_ip_funcs. The amdgpu_discovery.c path selecting sdma_v4_0_ip_block
 * for SDMA0_HWIP 4.x is the 'default:' of the switch in amdgpu_device.c:2145,
 * and family VI takes the 'case', so discovery never runs for this chip. That
 * is findings/043-vuelta-atras-035-y-036-leian-el-asic-equivocado.md, verified line by line in findings/115-sd-cuando-hay-invalidate-regla-por-vmid.md.
 *
 * WHY THE PREVIOUS CITATION WAS WORSE THAN COSMETIC. This line used to read,
 * verbatim, with the inline citation naming vega10_sdma_pkt_open.h:37:
 *
 *     #define RX550_SDMA_OP_PTEPDE  12   [cita: vega10_sdma_pkt_open.h:37]
 *
 * (Rewritten here without the literal slash-star that a real comment would
 * carry: quoting a comment opener inside a comment is what -Wcomment reports,
 * and it is not worth two warnings to keep one character of a historical line.)
 * Right value, right number, wrong authority. vega10 is the header of the V3
 * generation -- the one this ASIC does NOT run, and the one whose convention is
 * count-1, the exact convention findings/044-correccion-implementada-y-por-que-make-no-vio-el-cambio.md had to undo in the encoder. A
 * reader who trusted that citation would "fix" this back to count-1 and would
 * be right by the cited authority and wrong for this GPU. A wrong citation is
 * worse than a wrong number: it launders the error.
 *
 * THE TRAP IN vega10_sdma_pkt_open.h, FOR ANYONE BUILDING FROM IT. That header
 * defines three op-12 packet shapes -- SDMA_PKT_PTEPDE_COPY (:1742),
 * _COPY_BACKWARDS (:1815), _RMW (:1899) -- each with a SUB_OP field in bits
 * 15:8 (:1753-1756) selecting GEN / COPY / RMW / COPY_BACKWARDS (:55-58). None of
 * the six emitters uses those macros; all six write the generic
 * SDMA_PKT_HEADER_OP(x), whose op field is bits 7:0 only
 * (tonga_sdma_pkt_open.h:55-56). Those per-packet header macros describe a
 * dispatch surface this corpus never uses, and using them would emit
 * 0x00000Cxx instead of 0x0000000C.
 *
 * The payload of a PTEPDE packet is defined by what the EMITTER writes, not by
 * which header the name was found in.
 */
#define RX550_SDMA_OP_GEN_PTEPDE	12		/* tonga_sdma_pkt_open.h:37 */

/** RX550_SDMA_PTEPDE_DW: dwords in a PTEPDE packet, header included. */
/* La cita es la del emisor que CORRE en esta pieza, y no es un detalle. Ese mismo
 * 10 aparece en sdma_v4_0.c:1649-1658, que es el otro ASIC, asi que el VALOR no
 * distingue nada: lo que se puede equivocar sin que el numero se queje es la fuente.
 * Y esa fuente equivocada es la que arrastro el dword 9 a `count - 1` dos veces. tools/
 * emisor.py comprueba esta cita, ademas del valor, precisamente por eso.
 */
#define RX550_SDMA_PTEPDE_DW		10		/* sdma_v3_0.c:986-996 */

/*
 * SDMA_OP_INDIRECT: the packet that tells the SDMA where to fetch a command
 * buffer from. 7 dwords, length implied by the opcode, because sDMA packets
 * have no count field.
 *
 * THE OPCODE IS 4, NOT 17, AND THE VMID GOES IN BITS 19:16, NOT 3:0.
 *
 * Both were wrong in the first draft of this comment block and neither was
 * caught by a compiler, because both were constants I supplied rather than read.
 * The VMID one is the instructive mistake: the mask IS 0xF
 * (vega10_sdma_pkt_open.h:2082), so reading the mask as a bit position looks
 * reasonable and gives a field at bits 3:0, where the opcode already lives. The
 * shift is 16 (vega10_sdma_pkt_open.h:2083), so the field is 19:16.
 *
 * Writing 4 | vmid instead of 4 | (vmid << 16) would place the VMID on top of
 * the opcode in bits 7:4 of the same byte and produce opcode 4|vmid, which is a
 * different sDMA packet. No build error, no warning, no test failure unless a
 * test knows the right value independently. This is the class of error
 * findings/035-block-size-tres-claims-y-un-log.md was about, arriving by a different route: a plausible number
 * supplied instead of a measured one.
 */
#define RX550_SDMA_OP_INDIRECT		4	/* vega10_sdma_pkt_open.h:29 */
#define RX550_SDMA_INDIRECT_VMID_MASK	0xf	/* vega10_sdma_pkt_open.h:2082 */
#define RX550_SDMA_INDIRECT_VMID_SHIFT	16	/* vega10_sdma_pkt_open.h:2083 */

/*
 * SIX dwords, not seven. I wrote 7 and the test caught it: 7 compiles, emits a
 * valid-looking stream with one dword of padding at the end, and makes every
 * offset after it wrong by one. Counted from sdma_v4_0.c:816-822 -- header,
 * addr low, addr high, length_dw, 0, 0.
 */
#define RX550_SDMA_INDIRECT_DW		6	/* sdma_v4_0.c:816-822 */

/*
 * The alignment NOP that precedes it, and why the driver's constant is 2.
 *
 *     sdma_v4_0_ring_insert_nop(ring, (2 - lower_32_bits(ring->wptr)) & 7);
 *     // "IB packet must end on a 8 DW boundary"
 *
 * The packet is 6 dwords, so with w = wptr & 7 it ends at w + 6, which is
 * 8-aligned exactly when w == 2. Padding (2 - w) & 7 achieves that. So the
 * literal 2 is 8 minus the packet length, NOT the size of the packet header --
 * I wrote that in the .c first and it was wrong, and the wrong version was the
 * kind that sounds like an explanation.
 *
 * It depends on ring->wptr, which this encoder does not model, so it is NOT
 * emitted. It is one of the two things a caller must supply.
 */
#define RX550_SDMA_INDIRECT_NOP_PAD_FOR(len_dw)	(((8 - ((len_dw) & 7)) & 7))

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

/**
 * rx550_vm_ptba_reg - the PAGE_TABLE_BASE_ADDR register for a VMID.
 *
 * @vmid: 0-15. VMID 0 is the kernel's GART; 1-7 are graphics; 8-15 are compute.
 *
 * Returns 0 for a vmid outside 0-15, which is not a valid register. Callers must
 * treat 0 as a refusal, not an address: the arithmetic that looks like a
 * natural single stride-1 array sends VMIDs 8-15 to the aperture range registers
 * instead. See the register block in this header for the offsets.
 */
__u32 rx550_vm_ptba_reg(__u32 vmid);

/** rx550_vm_invalidate_mask - the VM_INVALIDATE_REQUEST bit for a VMID. */
__u32 rx550_vm_invalidate_mask(__u32 vmid);

/**
 * rx550_pm4_write_data - emit WRITE_DATA, a register write from the ring.
 *
 * @reg: ABSOLUTE register number. Not an offset -- see this header.
 * @engine: RX550_RING_ENGINE_ME / _PFP. The gfx ring selects the PFP.
 *
 * Five dwords: header with count 3, then a command word, the register, a zero,
 * and the value. gfx_v8_0_ring_emit_wreg().
 */
void rx550_pm4_write_data(struct rx550_pm4_ib *ib, __u32 reg, __u32 val,
			  __u32 engine);

/** rx550_pm4_wait_reg_mem - emit WAIT_REG_MEM, seven dwords. */
void rx550_pm4_wait_reg_mem(struct rx550_pm4_ib *ib, __u32 reg, __u32 ref,
			    __u32 mask, __u32 poll, __u32 function,
			    __u32 operation, __u32 mem_space, __u32 engine);

/** rx550_pm4_pfp_sync_me - emit PFP_SYNC_ME, two dwords. GFX rings only. */
void rx550_pm4_pfp_sync_me(struct rx550_pm4_ib *ib);

/*
 * CP_COHER_CNTL for the whole-coherency case, which is the only case the
 * reference driver emits. gfx_v8_0_emit_mem_sync() and
 * gfx_v8_0_emit_mem_sync_compute() both write exactly this OR:
 *
 *     PACKET3_TCL1_ACTION_ENA        (1 << 22)
 *   | PACKET3_TC_ACTION_ENA          (1 << 23)  [L2]
 *   | PACKET3_SH_KCACHE_ACTION_ENA   (1 << 27)
 *   | PACKET3_SH_ICACHE_ACTION_ENA   (1 << 29)
 *   | PACKET3_TC_WB_ACTION_ENA       (1 << 18)  [L2]
 *                          == 0x28C40000
 *
 * The four ACTION_ENA bits without WB are the invalidate side and TC_WB is the
 * writeback side. Both are set, so the packet is invalidate-and-writeback, not
 * either alone. Which caches that covers on GFX8 is NOT_DETERMINED; the field
 * names are the only evidence and five of them overlap.
 */
#define RX550_CP_COHER_CNTL_FULL	0x28c40000u

/** RX550_MEM_SYNC_POLL: the poll interval both sync packets use. gfx_v8_0.c. */
#define RX550_MEM_SYNC_POLL		0x0au

/** RX550_SURFACE_SYNC_DW: 5. count 3, four payload dwords. gfx_v8_0.c. */
#define RX550_SURFACE_SYNC_DW		5
/** RX550_ACQUIRE_MEM_DW: 7. count 5, six payload dwords. gfx_v8_0.c. */
#define RX550_ACQUIRE_MEM_DW		7

/**
 * rx550_pm4_mem_sync - make CPU-written memory visible to the GPU.
 *
 * @gfx_ring: SURFACE_SYNC (32-bit coher base) for gfx, ACQUIRE_MEM (64-bit) for
 *            compute. NOT interchangeable, see the note on rx550_pm4_surface_sync.
 *
 * FIVE or SEVEN dwords. This is the packet that makes an IB written by the CPU in
 * GTT readable by the GPU over PCIe: amdgpu_ib.c:79-80 sets
 * AMDGPU_IB_FLAG_EMIT_MEM_SYNC with the comment "flush the cache before commit the
 * IB", and amdgpu_ib.c:235-236 turns that flag into this packet. It goes in the
 * RING, immediately before the SDMA_OP_INDIRECT that references the IB, not inside
 * the IB.
 *
 * WHY THIS IS NOT OPTIONAL ON GFX8. I claimed for part of one session that GFX8
 * had no emit_mem_sync and that the flag was inert. That was wrong: gfx_v8_0.c:6916
 * and :6950 both set it, and the function is in the same file. findings/039-cierre-de-includes-resolucion-real.md records
 * the correction. The coherent thing to take from it is not the claim but the
 * method error behind it, which happened twice in that session: a grep piped to head
 * and the visible part read as the complete answer.
 */
void rx550_pm4_mem_sync(struct rx550_pm4_ib *ib, bool gfx_ring);

/** rx550_pm4_surface_sync - the 32-bit-base form, gfx_v8_0.c. Five dwords. */
void rx550_pm4_surface_sync(struct rx550_pm4_ib *ib);

/** rx550_pm4_acquire_mem - the 64-bit-base form, gfx_v8_0.c. Seven dwords. */
void rx550_pm4_acquire_mem(struct rx550_pm4_ib *ib);

/**
 * rx550_pm4_indirect - reference an IB from the ring, six dwords.
 *
 * @gpu_addr: the IB's GPU address. MUST be 32-byte aligned: the reference driver
 *             masks with 0xffffffe0 rather than checking, so a misaligned address
 *             silently fetches from somewhere else. This function refuses one.
 * @length_dw: the IB's length in dwords. Absolute, not minus one.
 * @vmid: the VMID the IB executes in, 0-15.
 */
void rx550_pm4_indirect(struct rx550_pm4_ib *ib, __u64 gpu_addr, __u32 length_dw,
			__u32 vmid);

/**
 * rx550_ring_submit - the delivery path: mem_sync, then reference the IB.
 *
 * @ib: the indirect buffer already filled by the PTEPDE and vm-flush emitters
 * @ib_gpu_addr: where that buffer lives
 * @ib_length_dw: how many dwords of it are meaningful
 * @vmid: VMID to execute it in
 * @gfx_ring: selects SURFACE_SYNC over ACQUIRE_MEM, and PFP_SYNC_ME inside
 *            rx550_vm_flush()
 *
 * Emits the two packets the reference driver emits in ring memory before the
 * hardware is told to fetch anything: the coherence packet, then
 * SDMA_OP_INDIRECT pointing at the IB. Eleven dwords on a gfx ring, thirteen on
 * compute. The IB's own contents are NOT included -- those live in GTT, not in the
 * ring -- which is the whole reason this function exists: findings/037-ptba-dos-tramos-y-vm-flush.md emitted
 * correct bytes into a malloc and had no way to name them to the hardware.
 *
 * All-or-nothing, for the same reason as rx550_vm_flush().
 */
__u32 rx550_ring_submit(struct rx550_pm4_ib *ring, __u64 ib_gpu_addr,
			__u32 ib_length_dw, __u32 vmid, bool gfx_ring);

/**
 * rx550_vm_flush - program a page table base and invalidate that VMID's TLB.
 *
 * @vmid:  0-15
 * @pd_addr: page directory address, in GPU bytes. Shifts down by 12 itself.
 * @gfx_ring: emit the trailing PFP_SYNC_ME. A compute ring has no PFP.
 *
 * The complete GFX8 vm-flush, in emission order, from
 * gfx_v8_0_ring_emit_vm_flush() (gfx_v8_0.c:6197-6221) and
 * gmc_v8_0_emit_flush_gpu_tlb() (gmc_v8_0.c:661-677):
 *
 *     WREG  PTBA(vmid)                 = pd_addr >> 12
 *     WREG  VM_INVALIDATE_REQUEST     = 1 << vmid
 *     WAIT_REG_MEM on VM_INVALIDATE_REQUEST, ref 0, mask 0, poll 0x20
 *     PFP_SYNC_ME                       (gfx rings only)
 *
 * Nineteen dwords with the sync, seventeen without.
 *
 * The order is PROVEN at the software-emission level and is the whole of the
 * guarantee available: PTEPDE writes the directory in memory, PTBA points the
 * hardware at it, and the invalidate drops stale TLB entries. Whether the
 * hardware retires them in that order, and what the wait actually waits on given
 * that mask is 0, is NOT_DETERMINED -- see findings/029-orden-validacion-fence-no-ring.md and this file's note on
 * WAIT_REG_MEM.
 *
 * Writes nothing and returns 0 if the IB cannot hold the whole sequence. A
 * partial vm-flush would program a page table base without invalidating, or
 * invalidate without waiting, and either one is the failure this exists to
 * prevent.
 */
__u32 rx550_vm_flush(struct rx550_pm4_ib *ib, __u32 vmid, __u64 pd_addr,
		     bool gfx_ring);

/** rx550_sdma_header - build an sDMA packet header. One opcode byte, no count. */
__u32 rx550_sdma_header(__u32 op);

/**
 * rx550_sdma_vm_set_pte_pde - emit the packet that writes GFX8 page-table entries.
 *
 * @pe:    address of the page-entry array to write
 * @addr:  the value to OR into each entry (the physical address)
 * @count: how many entries. MUST be >= 1.
 * @incr:  bytes added to @addr per entry
 * @flags: 64-bit access flags, the AMDGPU_PTE_* set
 *
 * THIS IS NOT A PACKET3 and rx550_pm4_header() cannot encode it. See the sDMA
 * block in this header.
 *
 * Writes exactly RX550_SDMA_PTEPDE_DW dwords. A count of 0 is rejected and
 * writes nothing.
 *
 * CORRECCION 1.0.0: este comentario decia antes "because the encoding is
 * count - 1 and 0 - 1 would be 0xFFFFFFFF, i.e. 4 G entries". Eso era
 * findings/034, y findings/034 esta RETRACTADO. Leia sdma_v4_0.c y
 * "corrigio" a count - 1 el count que findings/023-pm4-count-convencion-medida.md habia leido bien en
 * sdma_v3_0.c. Este ASIC corre el primero, asi que aqui se escribe `count`.
 * La justificacion del .c en rx550_pm4.c (misma funcion, ~20 lineas antes de
 * esta) lo cuenta entero. La regla de rechazo de 0 NO cambia por el error:
 * un 0 no es una peticion con significado. Lo que cambia es el motivo, y el
 * motivo anterior era falso.
 */
void rx550_sdma_vm_set_pte_pde(struct rx550_pm4_ib *ib, __u64 pe, __u64 addr,
			       __u32 count, __u32 incr, __u64 flags);

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
