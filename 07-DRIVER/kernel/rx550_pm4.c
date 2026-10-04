// SPDX-License-Identifier: GPL-2.0
/*
 * rx550_pm4.c - PM4 packet encoder for the RX 550 (Polaris 12, GFX8).
 *
 * WHY C AND NOT ASSEMBLY
 *
 * The brief for this file said no assembly scaffolding until the GFX8 PM4
 * formats were established. They now are (IA-1, findings/007-gfx8-pm4-format.md,
 * and re-verified against amdgpu.ko byte-for-byte). But an assembler encodes
 * instructions against registers the hardware has to be told to use, and the
 * register programming sequence for this ASIC is still unknown: the one in
 * gfx_v8_0.c is gfx_v8_0_do_edc_gpr_workarounds(), which returns immediately for
 * anything that is not CHIP_CARRIZO. Writing assembly now would encode packets
 * whose delivery is unknown.
 *
 * What IS knowable is the wire format, and it is pure arithmetic on 32-bit
 * words: no hardware, no state, no side effects. That is what this file is, and
 * because it is a pure function it is testable on a host that refuses to load the
 * module at all. The test does that, and it compares the output against values
 * read out of the real amdgpu.ko rather than against itself.
 *
 * HEADER LAYOUT, from amdgpu/sid.h:335-340:
 *
 *     #define PACKET3(op, n)  ((RADEON_PACKET_TYPE3 << 30) |      \
 *                             (((op) & 0xFF) << 8) |             \
 *                             ((n) & 0x3FFF) << 16)
 *     #define PACKET3_COMPUTE(op, n) (PACKET3(op, n) | 1 << 1)
 *
 * The type is at the top and the opcode in the middle. A previous round of this
 * project used the SDMA_PACKET() layout from cikd.h, which puts the opcode at
 * [31:24]; that is the previous generation's format and produces silently wrong
 * headers, not build errors. This file is written against the macro above.
 *
 * count is 14 bits but occupies only [23:16]. Bits 29:24 are nominally reserved
 * and receive the top 6 bits of a count above 63, which the macro does not
 * reject. The encoder below truncates deliberately and says so; accepting a
 * count that the hardware would read differently is the kind of thing that
 * works on one ASIC and not another.
 */

#include <linux/types.h>

/*
 * `bool` is a kernel builtin, so Kbuild needs no declaration of it. In
 * userspace it comes from <stdbool.h>, which the kernel does not have and which
 * therefore cannot appear in the shared header. This file is compiled by both
 * -- the test links it directly -- so the include goes here, guarded, rather
 * than in rx550_pm4.h where it would break the module build.
 */
#ifndef __KERNEL__
#include <stdbool.h>
#endif

#include "rx550_pm4.h"

/*
 * Build a PACKET3 header.
 *
 * @op: packet opcode, 8 bits
 * @count: payload dwords, 14 bits
 * @compute: set bit 1, which marks the packet as belonging to the compute path
 *
 * The compute bit matters and is not cosmetic. amdgpu.ko contains 0xC0031500 ten
 * times and 0xC0031502 once; gfx_v8_0.c calls the non-compute form. Which one a
 * driver must emit for a compute dispatch is OBSERVED from the macro and the
 * binary, not documented by AMD, so both forms are available and the caller
 * chooses. Encoding the wrong one does not fail loudly.
 */
__u32 rx550_pm4_header(__u32 op, __u32 count, bool compute)
{
	__u32 hdr;

	hdr = (3u << 30);			/* PACKET_TYPE3, value fixed at 0b11 */
	hdr |= (op & 0xFFu) << 8;
	hdr |= (count & 0x3FFFu) << 16;

	if (compute)
		hdr |= 1u << 1;

	return hdr;
}

/*
 * rx550_pm4_set_sh_reg - emit a SET_SH_REG for one 32-bit register.
 *
 * The register number is RELATIVE: gfx_v8_0.c writes
 *
 *     mmCOMPUTE_PGM_LO - PACKET3_SET_SH_REG_START
 *
 * so the payload is an offset from 0x2C00, not an absolute register address. An
 * encoder that writes the absolute number programs a different register and the
 * driver produces no error doing it. rx550_pm4_reg_offset() does the
 * subtraction so the caller cannot forget it.
 */
/*
 * EVIDENCIA  FORMATO = PROVEN  -- findings/007-gfx8-pm4-format.md:125-131.
 * EVIDENCIA  USO EN ESTA PLACA = NOT_APPLICABLE  -- findings/012-edc-gpr-workaround-carrizo.md.
 *   El unico emisor de SET_SH_REG en gfx_v8_0.c es do_edc_gpr_workarounds, y
 *   :1485 hace `if (adev->asic_type != CHIP_CARRIZO) return 0;`. Polaris12 no es
 *   Carrizo: el driver de referencia NO emite este paquete en la RX 550. El
 *   formato es conocido; su emision aqui seria decision propia, no copia. Por
 *   eso se separan las dos marcas en vez de una sola.
 */

void rx550_pm4_set_sh_reg(struct rx550_pm4_ib *ib, __u32 reg, __u32 value)
{
	if (!ib || ib->length_dw + 3 > ib->size_dw)
		return;

	ib->buf[ib->length_dw++] =
		rx550_pm4_header(RX550_PKT3_SET_SH_REG, 1, false);
	ib->buf[ib->length_dw++] = rx550_pm4_reg_offset(reg);
	ib->buf[ib->length_dw++] = value;
}

/*
 * rx550_pm4_set_sh_reg2 - emit a SET_SH_REG for a 64-bit register, lo then hi.
 *
 * Same packet, count 2. gfx_v8_0.c uses this for COMPUTE_PGM_LO/HI, which is how
 * a shader address gets into the compute program registers.
 */
/*
 * EVIDENCIA  FORMATO = PROVEN  -- findings/007-gfx8-pm4-format.md:130 (0xC0027600,
 *   reg-0x2C00, lo32, hi32).
 * EVIDENCIA  USO EN ESTA PLACA = NOT_APPLICABLE  -- findings/012-edc-gpr-workaround-carrizo.md,
 *   mismo gate :1485 que en set_sh_reg.
 */

void rx550_pm4_set_sh_reg2(struct rx550_pm4_ib *ib, __u32 reg, __u64 value)
{
	if (!ib || ib->length_dw + 4 > ib->size_dw)
		return;

	ib->buf[ib->length_dw++] =
		rx550_pm4_header(RX550_PKT3_SET_SH_REG, 2, false);
	ib->buf[ib->length_dw++] = rx550_pm4_reg_offset(reg);
	ib->buf[ib->length_dw++] = (__u32)(value & 0xFFFFFFFFu);
	ib->buf[ib->length_dw++] = (__u32)(value >> 32);
}

/*
 * rx550_pm4_dispatch_direct - emit DISPATCH_DIRECT with immediate dimensions.
 *
 * @x, @y, @z: the three dimension words
 *
 * THE COUNT IS 3 AND FOUR DWORDS FOLLOW. This reproduces gfx_v8_0.c:1541-1546
 * exactly, and it is not a typo here:
 *
 *     ib.ptr[ib.length_dw++] = PACKET3(PACKET3_DISPATCH_DIRECT, 3);
 *     ib.ptr[ib.length_dw++] = 8;                              // x
 *     ib.ptr[ib.length_dw++] = 1;                              // y
 *     ib.ptr[ib.length_dw++] = 1;                              // z
 *     ib.ptr[ib.length_dw++] = REG_SET_FIELD(0, COMPUTE_DISPATCH_INITIATOR,
 *                                            COMPUTE_SHADER_EN, 1);
 *
 * Four words written, count 3. The fourth is the initiator and amdgpu does not
 * count it as payload. WHY is NOT_DETERMINED and is not guessed at here: the
 * parser that would explain it is in hardware, not in this tree. The operational
 * rule is the measured one, and this function encodes the measurement. Changing
 * the count to 4 to "look consistent" would encode something the driver does
 * not do, and nothing would report it.
 *
 * @compute selects the PACKET3_COMPUTE form, which sets bit 1. See the note in
 * rx550_pm4_header().
 */
/*
 * EVIDENCIA  FORMATO = PROVEN  -- findings/007-gfx8-pm4-format.md:93-104.
 *   Opcode 0x15, count 3, los cuatro dwords x/y/z/initiator, y el header
 *   0xC0031500 / 0xC0031502 con el bit 1 de PACKET3_COMPUTE. El binario lo
 *   corrobora en :106-121. La semantica de los tres payloads la da
 *   findings/010-pgm-rsrc1-decoded.md:99-100.
 * EVIDENCIA  ALCANCE DE HARDWARE = PROVEN_DERIVED, NO PROVEN  -- findings/095-los-5-sin-medir-y-los-2-limite-reconcilian.md:200-203.
 *   La regla count = payload - 1 esta probada sobre el driver de GFX8. Que el
 *   hardware de esta pieza la lea asi sigue sin probar: el driver podria estar
 *   compensando otra lectura. Emitir bien no es lo mismo que ser leido bien.
 * NOT_DETERMINED CORREGIDO: el comentario de esta funcion decia que el
 *   desajuste entre count y los dwords escritos es NOT_DETERMINED.
 *   findings/038-validador-flujo-y-regla-del-count.md:42 lo declara caducado:
 *   es la misma regla de siempre, no una excepcion. Retirado aqui.
 */

void rx550_pm4_dispatch_direct(struct rx550_pm4_ib *ib, __u32 x, __u32 y, __u32 z,
			       bool compute)
{
	if (!ib || ib->length_dw + 5 > ib->size_dw)
		return;

	ib->buf[ib->length_dw++] =
		rx550_pm4_header(RX550_PKT3_DISPATCH_DIRECT, 3, compute);
	ib->buf[ib->length_dw++] = x;
	ib->buf[ib->length_dw++] = y;
	ib->buf[ib->length_dw++] = z;
	/* COMPUTE_DISPATCH_INITIATOR with COMPUTE_SHADER_EN (bit 0) set. */
	ib->buf[ib->length_dw++] = 1u;
}

/*
 * rx550_pm4_event_write - emit EVENT_WRITE with the event token as a dword.
 *
 * @event: an already-built token, e.g. EVENT_TYPE(7) | EVENT_INDEX(4)
 *
 * The token is a SEPARATE dword after the header, not the high 16 bits of the
 * header. gfx_v8_0.c:1549-1550:
 *
 *     ib.ptr[ib.length_dw++] = PACKET3(PACKET3_EVENT_WRITE, 0);
 *     ib.ptr[ib.length_dw++] = EVENT_TYPE(7) | EVENT_INDEX(4);
 *
 * findings/007-gfx8-pm4-format.md section 4 claims the token goes in the high 16
 * bits of the header -- "el campo e del formato SDMA_PACKET, que en PACKET3() es
 * el espacio de count y reservados". The code does not do that, and I implemented
 * it that way first. The test caught it: the header came out as 0xC0004704
 * instead of a bare 0xC0004600 followed by 0x00000407.
 *
 * The two readings differ in a way nothing would ever report. The token 0x407
 * is small, so under the document's reading it lands in bits 8:0, which the
 * sid.h:335 layout calls reserved -- and the second dword would then be dead
 * code. The code writes both dwords. The code is the authority on what the
 * driver emits; the document's reading is a plausible inference that does not
 * survive being typed out and compared against the bytes.
 *
 * EVENT_TYPE(x) is (x) << 0 and EVENT_INDEX(x) is (x) << 8 (sid.h:490-491), so
 * EVENT_TYPE(7) | EVENT_INDEX(4) == 0x407.
 */
/*
 * EVIDENCIA  = PROVEN  -- findings/012-edc-gpr-workaround-carrizo.md:141-146.
 *   Medicion en el binario: el token 0x407 va 23 bytes DESPUES de 0xC0004600
 *   como dword propio, no OR'd dentro del header. Eso REFUTA la lectura de
 *   findings/007-gfx8-pm4-format.md:137-140, que lo ponia en los 16 bits altos
 *   del header, y la de findings/006-lsdma-packets.md:179-181, que repite el
 *   mismo error. El count lo cierra findings/038-validador-flujo-y-regla-del-count.md:29:
 *   count 0 -> 1 dword de payload -> 2 en total.
 *   NO CITAR findings/007-gfx8-pm4-format.md a secas para esta funcion: es el
 *   fichero cuya lectura esta refutada. Es el modo de fallo que findings/114-implgate-cinco-bugs-propios-y-una-afirmacion-falsa.md
 *   describe, y por eso aqui se cita el nombre completo y el por que.
 * HALLAZGO_NONE para la semantica del valor: findings/007-gfx8-pm4-format.md:215-218
 *   dice que EVENT_TYPE y EVENT_INDEX no estan decodificados bit a bit. Que
 *   sea un 'flush parcial de CS' viene solo del NOMBRE del campo, es decir,
 *   de leer un comentario del driver de referencia.
 */

void rx550_pm4_event_write(struct rx550_pm4_ib *ib, __u32 event)
{
	if (!ib || ib->length_dw + 2 > ib->size_dw)
		return;

	ib->buf[ib->length_dw++] =
		rx550_pm4_header(RX550_PKT3_EVENT_WRITE, 0, false);
	ib->buf[ib->length_dw++] = event;
}

/*
 * rx550_sdma_header - build an sDMA packet header.
 *
 * vega10_sdma_pkt_open.h:69-72 puts the opcode in bits 7:0 with no packet
 * type and no count:
 *
 *     #define SDMA_PKT_HEADER_op_offset 0
 *     #define SDMA_PKT_HEADER_op_mask   0x000000FF
 *     #define SDMA_PKT_HEADER_op_shift  0
 *
 * So for PTEPDE the header dword is literally 0x0000000C. Do not read this as a
 * PACKET3: there is no 0xC0000000 type prefix, and there is no count to keep in
 * sync with the payload. A caller that computes a length and puts it in a count
 * field writes garbage into the opcode byte.
 *
 * PROVEN_ABSENT for the count field, not merely unused: the mask is 8 bits at
 * offset 0 and there is no second header field defined in the header this
 * function is transcribed from.
 */
__u32 rx550_sdma_header(__u32 op)
{
	return (op & RX550_SDMA_PKT_OP_MASK) << RX550_SDMA_PKT_OP_SHIFT;
}

/*
 * rx550_sdma_vm_set_pte_pde - emit the GFX8 page-table producer.
 *
 * sdma_v4_0.c:1643-1659, ten dwords. NOT VERBATIM, and the word used to say so:
 *
 *     ib->ptr[ib->length_dw++] = SDMA_PKT_HEADER_OP(SDMA_OP_PTEPDE);
 *     ib->ptr[ib->length_dw++] = lower_32_bits(pe);      // dst addr
 *     ib->ptr[ib->length_dw++] = upper_32_bits(pe);
 *     ib->ptr[ib->length_dw++] = lower_32_bits(flags);   // mask
 *     ib->ptr[ib->length_dw++] = upper_32_bits(flags);
 *     ib->ptr[ib->length_dw++] = lower_32_bits(addr);    // value
 *     ib->ptr[ib->length_dw++] = upper_32_bits(addr);
 *     ib->ptr[ib->length_dw++] = incr;                    // increment size
 *     ib->ptr[ib->length_dw++] = 0;
 *     ib->ptr[ib->length_dw++] = count - 1;              // number of entries
 *
 * The transcription is of sdma_v4_0.c, which is NOT the file that runs here.
 * Two fields differ from the one below that is running, and they differ
 * together: the op NAME, GEN_PTEPDE against PTEPDE, and the count field,
 * plain `count` against `count - 1`. "Verbatim" was a claim of identity where
 * there is a measured one-field difference in the same direction as the
 * generation -- see findings/188-el-nombre-del-op-12-y-la-cita-equivocada.md:15-29,
 * six emitters, six of six.
 *
 * THE COUNT FIELD IS PLAIN. findings/034-corpus-autoconsistente-layouts-pm4.md said it was minus one, and that was
 * WRONG -- a second reversal of the same field, and the reason matters more
 * than the field.
 *
 * The two emitters in the corpus are:
 *
 *     sdma_v3_0.c:986-996   SDMA_OP_GEN_PTEPDE, writes `count`      <-- RUNS
 *     sdma_v4_0.c:1649-1658 SDMA_OP_PTEPDE,     writes `count - 1`  <-- does not
 *
 * sdma_v3_0.c is what this ASIC runs. The case of CHIP_POLARIS12 adds
 * sdma_v3_1_ip_block (vi.c:2107), which is defined in sdma_v3_0.c:1693 with
 * .funcs = &sdma_v3_0_ip_funcs; and the amdgpu_discovery.c path that selects
 * sdma_v4_0_ip_block for SDMA0_HWIP 4.x is the `default:` of the switch in
 * amdgpu_device.c:2145, which family VI never reaches. findings/043-vuelta-atras-035-y-036-leian-el-asic-equivocado.md.
 *
 * findings/023-pm4-count-convencion-medida.md read sdma_v3_0.c and recorded `count` -- correct. findings/034-corpus-autoconsistente-layouts-pm4.md
 * read sdma_v4_0.c and "corrected" it to `count - 1` -- wrong, and wrong in the
 * dangerous direction, because it justified the change with a cross-check
 * ("the other two producers of this ASIC agree") that was itself reading
 * sdma_v4_0.c. A cross-check performed on one source is not a cross-check, and
 * citing two lines from the same file as if they were two sources is the
 * specific form that fooled me.
 *
 * So this writes `count`. The opcode byte is 12 in both headers, so the header
 * dword is identical either way; only dword 9 differs.
 *
 * WHAT IS STILL NOT_DETERMINED: whether the hardware of this specific part
 * reads that field the way the reference driver writes it. The best available
 * evidence is what the reference driver does, and findings/033-pm4-spec-gfx8-no-existe-y-el-encuadre.md established the
 * GFX8 architecture spec is not published. So the choice is PROVEN_DERIVED from
 * the reference driver, not PROVEN about the hardware, and it is written as
 * `REQUIREMENT` rather than as a fact.
 *
 * ZERO IS STILL REJECTED. That part of findings/034-corpus-autoconsistente-layouts-pm4.md survives: a count of 0 is
 * not a meaningful request, and passing it through produces a packet whose last
 * dword says "zero entries" in one reading and "the maximum" in the other.
 * Which of those the hardware picks is exactly the kind of thing not to find
 * out by trying.
 */
void rx550_sdma_vm_set_pte_pde(struct rx550_pm4_ib *ib, __u64 pe, __u64 addr,
			       __u32 count, __u32 incr, __u64 flags)
{
	if (!ib || count == 0)
		return;

	if (ib->length_dw + RX550_SDMA_PTEPDE_DW > ib->size_dw)
		return;

	ib->buf[ib->length_dw++] = rx550_sdma_header(RX550_SDMA_OP_GEN_PTEPDE);
	ib->buf[ib->length_dw++] = (__u32)(pe & 0xFFFFFFFFu);
	ib->buf[ib->length_dw++] = (__u32)(pe >> 32);
	ib->buf[ib->length_dw++] = (__u32)(flags & 0xFFFFFFFFu);
	ib->buf[ib->length_dw++] = (__u32)(flags >> 32);
	ib->buf[ib->length_dw++] = (__u32)(addr & 0xFFFFFFFFu);
	ib->buf[ib->length_dw++] = (__u32)(addr >> 32);
	ib->buf[ib->length_dw++] = incr;
	ib->buf[ib->length_dw++] = 0;
	ib->buf[ib->length_dw++] = count;
}

/*
 * rx550_vm_ptba_reg - the PAGE_TABLE_BASE_ADDR register for a VMID.
 *
 * gmc_v8_0_emit_flush_gpu_tlb(), gmc_v8_0.c:666-671:
 *
 *     if (vmid < 8)
 *             reg = mmVM_CONTEXT0_PAGE_TABLE_BASE_ADDR + vmid;
 *     else
 *             reg = mmVM_CONTEXT8_PAGE_TABLE_BASE_ADDR + vmid - 8;
 *
 * The branch is not a convenience. The two runs are at 0x54f and 0x50e in
 * gmc_8_1_d.h, and 0x50e < 0x54f, so they are disjoint AND out of VMID order.
 * Treating the sixteen registers as one stride-1 array from context 0 sends
 * VMIDs 8-15 to 0x557..0x55e, and the header says what lives there:
 *
 *     0x557  mmVM_CONTEXT0_PAGE_TABLE_START_ADDR
 *     0x558  mmVM_CONTEXT1_PAGE_TABLE_START_ADDR
 *     ...
 *     0x55d  mmVM_CONTEXT1_PAGE_TABLE_END_ADDR
 *     0x55e  mmVM_CONTEXT0_PAGE_TABLE_END_ADDR
 *
 * Writing a page-directory address into the aperture start/end registers moves
 * the window of GPUVA that gets translated at all. Nothing faults, nothing
 * reports, and every address outside the new window becomes unmapped. This is
 * the failure mode the branch exists to prevent, and it is why a vmid outside
 * 0-15 returns 0 here rather than being clamped: 0x54f is context 0, a valid
 * register, so a clamp would silently program the GART context instead.
 *
 * The split has a second confirmation that it is intended rather than
 * accidental: amdgpu_amdkfd.c:766 refuses a vmid below
 * adev->vm_manager.first_kfd_vmid, which gmc_v8_0.c:1162 sets to 8, before
 * amdgpu_amdkfd_gfx_v8.c:581 evaluates `vmid - 8`. The subtraction cannot
 * underflow because the guard makes vmid >= 8 a precondition.
 */
/*
 * rx550_pm4_surface_sync - the gfx-ring memory sync, five dwords.
 *
 * gfx_v8_0_emit_mem_sync() verbatim, gfx_v8_0.c:
 *
 *     amdgpu_ring_write(ring, PACKET3(PACKET3_SURFACE_SYNC, 3));
 *     amdgpu_ring_write(ring, PACKET3_TCL1_ACTION_ENA |
 *                             PACKET3_TC_ACTION_ENA |
 *                             PACKET3_SH_KCACHE_ACTION_ENA |
 *                             PACKET3_SH_ICACHE_ACTION_ENA |
 *                             PACKET3_TC_WB_ACTION_ENA);  // CP_COHER_CNTL
 *     amdgpu_ring_write(ring, 0xffffffff);  // CP_COHER_SIZE
 *     amdgpu_ring_write(ring, 0);            // CP_COHER_BASE
 *     amdgpu_ring_write(ring, 0x0000000A);   // poll interval
 *
 * count 3, four payload dwords, total 5: count + 2, the uniform rule from
 * findings/038-validador-flujo-y-regla-del-count.md. That rule is checked here for real rather than assumed -- the
 * test_pm4 case for this packet asserts the length from both directions.
 *
 * THE COHER BASE IS 32 BITS HERE. There is no CP_COHER_BASE_HI and no
 * CP_COHER_SIZE_HI in this form; the compute form below has both. SIZE
 * 0xFFFFFFFF with BASE 0 is the whole-4 GiB window, so on this ring the packet
 * cannot name a coher base above 4 GiB. An IB in GTT on a machine with more than
 * 4 GiB of PCI address space is therefore addressed by SIZE rather than by BASE,
 * which is a different mechanism and not one this file asserts anything about.
 * RX550_CP_COHER_CNTL_FULL is the OR of the five ACTION_ENA bits; the driver
 * hard-codes that OR and offers no way to select a subset.
 */
/*
 * EVIDENCIA  = PROVEN  -- findings/039-coherencia-ib-si-existe.md:42-61.
 *   Transcribe gfx_v8_0_emit_mem_sync: SURFACE_SYNC opcode 0x43, count 3, 5 dwords.
 *   AVISO DE CITA: el numero 039 esta duplicado en el arbol; este bloque cita el
 *   nombre completo porque el numero solo no identifica.
 */

void rx550_pm4_surface_sync(struct rx550_pm4_ib *ib)
{
	if (!ib || ib->length_dw + RX550_SURFACE_SYNC_DW > ib->size_dw)
		return;

	ib->buf[ib->length_dw++] =
		rx550_pm4_header(RX550_PKT3_SURFACE_SYNC, 3, false);
	ib->buf[ib->length_dw++] = RX550_CP_COHER_CNTL_FULL;
	ib->buf[ib->length_dw++] = 0xffffffffu;	/* CP_COHER_SIZE */
	ib->buf[ib->length_dw++] = 0u;		/* CP_COHER_BASE */
	ib->buf[ib->length_dw++] = RX550_MEM_SYNC_POLL;
}

/*
 * rx550_pm4_acquire_mem - the compute-ring memory sync, seven dwords.
 *
 * gfx_v8_0_emit_mem_sync_compute(), gfx_v8_0.c:
 *
 *     amdgpu_ring_write(ring, PACKET3(PACKET3_ACQUIRE_MEM, 5));
 *     amdgpu_ring_write(ring, ...same five ACTION_ENA bits...);
 *     amdgpu_ring_write(ring, 0xffffffff);  // CP_COHER_SIZE
 *     amdgpu_ring_write(ring, 0xff);        // CP_COHER_SIZE_HI
 *     amdgpu_ring_write(ring, 0);           // CP_COHER_BASE
 *     amdgpu_ring_write(ring, 0);           // CP_COHER_BASE_HI
 *     amdgpu_ring_write(ring, 0x0000000A);  // poll interval
 *
 * count 5, six payload dwords, total 7: count + 2 again. And the address IS 64
 * bits, so this form can name a coher base anywhere in PCI space, which the gfx
 * form cannot. That is the whole reason the reference driver has two functions
 * and selects between them by ring type rather than by address.
 *
 * Same CP_COHER_CNTL in both, and the same poll interval. So the difference is
 * the packet opcode and the address width, nothing else that is visible here.
 */
/*
 * EVIDENCIA  = PROVEN  -- findings/039-coherencia-ib-si-existe.md:56-61.
 *   ACQUIRE_MEM opcode 0x58, count 5, mas SIZE_HI/BASE_HI: 7 dwords, transcrito de
 *   gfx_v8_0_emit_mem_sync_compute.
 *   NOT_DETERMINED subordinado: que caches cubre CP_COHER_CNTL (mismo hallazgo :174).
 *   El PROVEN es del paquete emitido; el alcance de coherencia sigue abierto.
 */

void rx550_pm4_acquire_mem(struct rx550_pm4_ib *ib)
{
	if (!ib || ib->length_dw + RX550_ACQUIRE_MEM_DW > ib->size_dw)
		return;

	ib->buf[ib->length_dw++] =
		rx550_pm4_header(RX550_PKT3_ACQUIRE_MEM, 5, false);
	ib->buf[ib->length_dw++] = RX550_CP_COHER_CNTL_FULL;
	ib->buf[ib->length_dw++] = 0xffffffffu;	/* CP_COHER_SIZE */
	ib->buf[ib->length_dw++] = 0xffu;	/* CP_COHER_SIZE_HI */
	ib->buf[ib->length_dw++] = 0u;		/* CP_COHER_BASE */
	ib->buf[ib->length_dw++] = 0u;		/* CP_COHER_BASE_HI */
	ib->buf[ib->length_dw++] = RX550_MEM_SYNC_POLL;
}

/*
 * EVIDENCIA  = PROVEN  -- findings/039-coherencia-ib-si-existe.md:12-13.
 *   gfx_v8_0.c:6916 y :6950 asignan dos emit_mem_sync DISTINTOS en las tablas de
 *   ring; luego el despacho por tipo de ring es lo que hace el driver de referencia.
 */

void rx550_pm4_mem_sync(struct rx550_pm4_ib *ib, bool gfx_ring)
{
	if (gfx_ring)
		rx550_pm4_surface_sync(ib);
	else
		rx550_pm4_acquire_mem(ib);
}

/*
 * rx550_pm4_indirect - reference an IB from the ring, six dwords.
 *
 * sdma_v4_0_ring_emit_ib(), sdma_v4_0.c:
 *
 *     sdma_v4_0_ring_insert_nop(ring, (2 - lower_32_bits(ring->wptr)) & 7);
 *     amdgpu_ring_write(ring, SDMA_PKT_HEADER_OP(SDMA_OP_INDIRECT) |
 *                       SDMA_PKT_INDIRECT_HEADER_VMID(vmid & 0xf));
 *     amdgpu_ring_write(ring, lower_32_bits(ib->gpu_addr) & 0xffffffe0);
 *     amdgpu_ring_write(ring, upper_32_bits(ib->gpu_addr));
 *     amdgpu_ring_write(ring, ib->length_dw);
 *     amdgpu_ring_write(ring, 0);
 *     amdgpu_ring_write(ring, 0);
 *
 * FIVE points that each cost something to get right.
 *
 * ONE. The header is an sDMA packet with the VMID in bits 19:16, not a PACKET3.
 * The sub-opcode is OR'd into the same byte.
 *
 * AND THIS IS NOT THE ONLY SUCH PACKET ON GFX8. There are three ways to name an
 * IB on this ASIC and the other two are PACKET3, not sDMA:
 *
 *     gfx_v8_0_ring_emit_ib_gfx      (:6075)  PACKET3(PACKET3_INDIRECT_BUFFER, 2), 4 dwords
 *     gfx_v8_0_ring_emit_ib_compute  (:6107)  same opcode, 4 dwords
 *     gfx_v8_0_ring_emit_ib_kiq      (:6969)  the compute one, shared
 *
 * and the differences from this one are not cosmetic:
 *
 *   - ADDRESS MASK. This producer masks with 0xffffffe0, 32 bytes. The PACKET3
 *     ones mask with 0xFFFFFFFC, 4 bytes. Same field, same ASIC, two alignments.
 *   - VMID POSITION. Here it is bits 19:16. There it is bits 31:24, packed with
 *     the length in `control = length_dw | (vmid << 24)`.
 *   - VALID BIT. The compute producer ORs INDIRECT_BUFFER_VALID (1 << 23) into
 *     control. The gfx producer does not. Why is NOT_DETERMINED.
 *
 * findings/039-coherencia-ib-si-existe.md implemented this one and described it as "the" reference packet,
 * which was a generalisation I had not checked. The encoder here is correct for
 * the sDMA/page path and says nothing about the gfx or compute paths.
 *
 * TWO. The low half of the address is MASKED, not checked: "& 0xffffffe0". A
 * misaligned IB address is silently rounded down and the GPU fetches from
 * somewhere else. This function refuses instead, which is the only reason the
 * caller finds out. Note that the mask makes the driver's own output always
 * aligned whether or not the input was, so the reference driver cannot express
 * this bug -- but a driver that omits the mask can, and that is the difference
 * being closed.
 *
 * THREE. length_dw is ABSOLUTE. Not minus one. This is the opposite convention
 * from PTEPDE's entry count and from PACKET3's count, and getting it wrong makes
 * the GPU execute a prefix of the IB with no error.
 *
 * FOUR. The trailing two zeros are not counted anywhere. Six dwords total from
 * an opcode that carries no length, so the length lives in the driver's head.
 *
 * FIVE. The driver emits an alignment NOP FIRST:
 *
 *     sdma_v4_0_ring_insert_nop(ring, (2 - lower_32_bits(ring->wptr)) & 7);
 *
 * commented "IB packet must end on a 8 DW boundary". This packet is SIX dwords,
 * so with w = wptr & 7 it ends at w + 6, 8-aligned exactly when w == 2, and the
 * pad is (2 - w) & 7. The literal 2 is 8 minus the packet length. I first wrote
 * that it was the size of the INDIRECT header, which is a different number and a
 * more plausible-sounding explanation; see RX550_SDMA_INDIRECT_NOP_PAD_FOR in the
 * header for the derivation.
 *
 * It depends on ring->wptr, which this encoder does not model, so it is NOT
 * emitted here and NOT claimed to be correct. It is one of the two things a
 * caller must supply itself, and it is the reason the encoder takes an IB rather
 * than a ring position: a ring has a wptr, a malloc does not.
 *
 * This function refuses a misaligned address by writing nothing, so the caller
 * can check the return. It cannot refuse the missing NOP, because it cannot know
 * the position.
 *
 * SCOPE, stated because findings/039-coherencia-ib-si-existe.md did not state it: this is the SDMA/page
 * path only. The gfx and compute rings of this ASIC name an IB with
 * PACKET3_INDIRECT_BUFFER instead, with a different address mask, a different
 * VMID position, and a VALID bit that the gfx path omits. See the block comment
 * above and findings/040-wptr-doorbell-y-tres-productores-de-ib.md.
 */
/*
 * EVIDENCIA  = PROVEN  -- NO PROVEN_DERIVED, y el cambio es de fondo.
 *   La transcripcion initial venia de sdma_v4_0.c:816-822, que findings/043-vuelta-atras-035-y-036-leian-el-asic-equivocado.md:27-37
 *   y findings/046-la-version-de-ip-que-nunca-se-consulta.md:69-75licerian NO corre en esta GPU.
 *   Eso obligaba a marcarlo PROVEN_DERIVED. YA NO:
 *     vi.c:2106-2113            case CHIP_POLARIS12 -> &sdma_v3_1_ip_block
 *     sdma_v3_0.c:1693-1699     sdma_v3_1_ip_block -> &sdma_v3_0_ip_funcs
 *     sdma_v3_0.c:422-441       sdma_v3_0_ring_emit_ib, el emisor de ESTA placa
 *   Y el cuerpo de sdma_v3_0_ring_emit_ib es IDENTICO byte a byte al de
 *   sdma_v4_0_ring_emit_ib, salvo el nombre del helper NOP. Mismo
 *   AMDGPU_JOB_GET_VMID, mismo (2 - wptr) & 7, mismo & 0xffffffe0, mismo
 *   length_dw absoluto, mismos dos ceros, 6 dwords. Los valores del header
 *   tambien coinciden: tonga_sdma_pkt_open.h:29 y vega10_sdma_pkt_open.h:29
 *   definen ambos SDMA_OP_INDIRECT 4, y tonga:1649-1650 da vmid_mask 0xF con
 *   shift 16, o sea VMID en 19:16, que es lo que escribe esta funcion.
 *   El derivado es real pero innecesario: el fichero correcto estaba a una
 *   tabla de distancia. Registro en
 * findings/119-el-fichero-que-si-corre-esta-a-una-tabla.md.
 * AVISO DE PROCEDENCIA: el comentario cita vega10_sdma_pkt_open.h y el SDMA de
 *   esta placa incluye tonga_sdma_pkt_open.h. Mismo valor, distinta procedencia:
 *   es la clase que findings/041-herramientas-de-procedencia-y-auditoria.md:12 ya nombra.
 * NOT_DETERMINED subordinados: si el NOP de alineacion a 8 dwords hace falta o
 *   es cosmetico (039-coherencia-ib-si-existe.md:176,
 *   040-wptr-doorbell-y-tres-productores-de-ib.md:185); por que el
 *   productor gfx omite INDIRECT_BUFFER_VALID (040-wptr-doorbell-y-tres-productores-de-ib.md:183), que es la razon de que
 *   esta funcion sea solo-sDMA; y si el camino sDMA/page se ejerce en runtime
 *   en este ASIC. Alineacion: PARTIAL, 4 B en gfx/compute y 32 B en sDMA
 *   (040-wptr-doorbell-y-tres-productores-de-ib.md:186), asi que el rechazo de gpu_addr & 0x1f es correcto SOLO para
 *   el camino sDMA.
 */

void rx550_pm4_indirect(struct rx550_pm4_ib *ib, __u64 gpu_addr, __u32 length_dw,
			__u32 vmid)
{
	if (!ib || ib->length_dw + RX550_SDMA_INDIRECT_DW > ib->size_dw)
		return;

	if (gpu_addr & 0x1f)
		return;		/* see point TWO; refuses rather than masks */

	if (vmid >= RX550_NUM_VMID)
		return;

	if (length_dw == 0)
		return;		/* an IB of no dwords is a null submission */

	/* opcode in bits 7:0, vmid in bits 19:16 -- see rx550_pm4.h for why this
	 * is not (vmid & 0xf). */
	ib->buf[ib->length_dw++] = rx550_sdma_header(RX550_SDMA_OP_INDIRECT) |
				    ((vmid & RX550_SDMA_INDIRECT_VMID_MASK)
				     << RX550_SDMA_INDIRECT_VMID_SHIFT);
	ib->buf[ib->length_dw++] = (__u32)(gpu_addr & 0xffffffffu);
	ib->buf[ib->length_dw++] = (__u32)(gpu_addr >> 32);
	ib->buf[ib->length_dw++] = length_dw;
	ib->buf[ib->length_dw++] = 0;
	ib->buf[ib->length_dw++] = 0;
}

/*
 * rx550_ring_submit - the delivery path.
 *
 * The two packets that go in RING memory before the hardware is told to fetch
 * anything. Before this, rx550_vm_flush() and rx550_sdma_vm_set_pte_pde() emitted
 * correct bytes into a caller-owned buffer and there was no function that named
 * that buffer to the hardware; findings/037-ptba-dos-tramos-y-vm-flush.md named it as the missing piece.
 *
 * Note what is NOT here: the IB's own dwords. The coherence packet, the INDIRECT
 * and the alignment NOP live in ring memory; the PTEPDE and the vm-flush live in
 * the IB. Two different address spaces, which is the structural fact that makes
 * this more than concatenation, and which is why the caller must pass both.
 *
 * All-or-nothing, so that a submission cannot end up with an invalidate
 * scheduled and no reference to the buffer holding it.
 */
/*
 * EVIDENCIA  = PROVEN  -- findings/039-coherencia-ib-si-existe.md:145.
 *   La funcion nombra el contrato: coherencia en el RING antes del
 *   SDMA_OP_INDIRECT, y todo-o-nada. El orden lo dan :78-89 y :105-115; :173
 *   lo clasifica PROVEN por posicion; :164-165 lo valida en el validador con
 *   M6/M7/M8 detectadas.
 * LO QUE ESTA FUNCION NO HACE, aunque su comentario la llame 'delivery path':
 *   NO programa wptr NI el doorbell. findings/039-coherencia-ib-si-existe.md:192-195
 *   lo dice literal: sin doorbell no hay entrega, escribir el ring no hace que
 *   la GPU lo ejecute. El doorbell es escritura a BAR2 con index * 4, y
 *   findings/040-wptr-doorbell-y-tres-productores-de-ib.md:98-133 deja esa
 *   escritura en NOT_RUN por politica. Sin esa pieza esto codifica pero no
 *   entrega; decirlo aqui evita que el nombre de la funcion sugiera lo
 *   contrario.
 * NOT_DETERMINED subordinado: findings/039-coherencia-ib-si-existe.md:174, que
 *   caches cubre CP_COHER_CNTL = 0x28C40000 en GFX8. La emision esta probada;
 *   el alcance no. Y si el NOP de alineacion a 8 dwords hace falta o es
 *   cosmetico (039-coherencia-ib-si-existe.md:176,
 *   040-wptr-doorbell-y-tres-productores-de-ib.md:185) esta funcion no lo
 *   modela: no ve wptr.
 * AVISO DE CITA: 039 esta duplicado en el arbol y el otro 039 no menciona esta
 *   funcion. Por eso el nombre completo.
 */

__u32 rx550_ring_submit(struct rx550_pm4_ib *ring, __u64 ib_gpu_addr,
			__u32 ib_length_dw, __u32 vmid, bool gfx_ring)
{
	__u32 need = gfx_ring ? (RX550_SURFACE_SYNC_DW + RX550_SDMA_INDIRECT_DW) :
				(RX550_ACQUIRE_MEM_DW + RX550_SDMA_INDIRECT_DW);

	if (!ring)
		return 0;
	if (ring->length_dw + need > ring->size_dw)
		return 0;
	/* Same refusals rx550_pm4_indirect() makes, checked before writing the
	 * coherence packet so a refused submission leaves the ring untouched. */
	if ((ib_gpu_addr & 0x1f) || !ib_length_dw || vmid >= RX550_NUM_VMID)
		return 0;

	rx550_pm4_mem_sync(ring, gfx_ring);
	rx550_pm4_indirect(ring, ib_gpu_addr, ib_length_dw, vmid);

	return 1;
}

/*
 * EVIDENCIA  = PROVEN_DERIVED  -- findings/037-ptba-dos-tramos-y-vm-flush.md:13-24,59-61.
 *   La geometria de dos tramos (CONTEXT0+vmid para 0-7, CONTEXT8+vmid-8 para 8-15)
 *   y el rechazo del 0 salen de ahi. Es PROVEN_DERIVED, no PROVEN: deriva de lo que
 *   hace el driver de referencia, no de una lectura del hardware.
 *   NOTA DE POSICION: el comentario que documenta esta funcion estaba 260 lineas
 *   mas arriba, describing un bloque de codigo distinto. Esta marca va aqui para que
 *   la funcion tenga su propia evidencia a la vista.
 */

__u32 rx550_vm_ptba_reg(__u32 vmid)
{
	if (vmid >= RX550_NUM_VMID)
		return 0;

	if (vmid < RX550_FIRST_KFD_VMID)
		return RX550_MM_VM_CONTEXT0_PTBA + vmid;

	return RX550_MM_VM_CONTEXT8_PTBA + (vmid - RX550_FIRST_KFD_VMID);
}

/*
 * rx550_vm_invalidate_mask - the VM_INVALIDATE_REQUEST bit for a VMID.
 *
 * gmc_v8_0_flush_gpu_tlb(), gmc_v8_0.c:658, and gmc_v8_0_emit_flush_gpu_tlb()
 * at :674, both write `1 << vmid` with the comment "bits 0-15 are the VM
 * contexts0-15". Sixteen contexts and sixteen bits, so vmid < 16 is exact and
 * the shift cannot lose a bit. A vmid of 16 would shift a 1 out of the word
 * entirely, which is why this returns 0 rather than shifting.
 */
/*
 * EVIDENCIA  = PROVEN  -- findings/106-funcion-no-existe-y-el-trigger-es-software.md:57-73,146.
 *   El valor `1 << vmid` sobre 16 contextos esta escrito literalmente en gmc_v8_0.c:665,680,
 *   y los 16 bits con mascara identica los confirma :146. FUNCTION no existe en el registro
 *   de bloque, asi que el trigger es enteramente software.
 */

__u32 rx550_vm_invalidate_mask(__u32 vmid)
{
	if (vmid >= RX550_NUM_VMID)
		return 0;

	return 1u << vmid;
}

/*
 * rx550_pm4_write_data - emit WRITE_DATA.
 *
 * gfx_v8_0_ring_emit_wreg() verbatim in shape, five dwords:
 *
 *     amdgpu_ring_write(ring, PACKET3(PACKET3_WRITE_DATA, 3));
 *     amdgpu_ring_write(ring, cmd);
 *     amdgpu_ring_write(ring, reg);
 *     amdgpu_ring_write(ring, 0);
 *     amdgpu_ring_write(ring, val);
 *
 * and the command word is chosen by ring type:
 *
 *     AMDGPU_RING_TYPE_GFX:   WRITE_DATA_ENGINE_SEL(1) | WR_CONFIRM
 *     AMDGPU_RING_TYPE_KIQ:   1 << 16            [no inc addr]
 *     default:                WR_CONFIRM
 *
 * So the three command words are 0x40100000, 0x00010000 and 0x00100000. This
 * takes the engine as a parameter and reproduces the first and third; the KIQ
 * form is a different thing (no confirm, no inc addr) and is exposed as
 * RX550_WR_ONE_ADDR for a caller that wants it, not selected by this function.
 *
 * THE REGISTER IS ABSOLUTE. This is the trap worth stating: SET_SH_REG takes an
 * offset from 0x2C00 and WRITE_DATA takes the register number itself. Both are
 * register writes in the same ring. An encoder that shares one helper between
 * them writes either a nonsense offset or a register 0x2C00 registers away,
 * and neither is reported.
 */
/*
 * EVIDENCIA  = PROVEN_DERIVED  -- findings/037-ptba-dos-tramos-y-vm-flush.md:92-112.
 *   La asimetria que importa: WRITE_DATA lleva el NUMERO ABSOLUTO del registro,
 *   no el offset relativo que lleva SET_SH_REG (:99, y mutacion M2 en :147).
 */

void rx550_pm4_write_data(struct rx550_pm4_ib *ib, __u32 reg, __u32 val,
			  __u32 engine)
{
	__u32 cmd;

	if (!ib || ib->length_dw + 5 > ib->size_dw)
		return;

	cmd = RX550_WR_CONFIRM;
	if (engine == RX550_RING_ENGINE_PFP)
		cmd |= RX550_WRITE_DATA_ENGINE_SEL(RX550_RING_ENGINE_PFP);

	ib->buf[ib->length_dw++] =
		rx550_pm4_header(RX550_PKT3_WRITE_DATA, 3, false);
	ib->buf[ib->length_dw++] = cmd;
	ib->buf[ib->length_dw++] = reg;
	ib->buf[ib->length_dw++] = 0;
	ib->buf[ib->length_dw++] = val;
}

/*
 * rx550_pm4_wait_reg_mem - emit WAIT_REG_MEM, seven dwords.
 *
 * gfx_v8_0.c:6205-6213 for the vm-flush's own use:
 *
 *     amdgpu_ring_write(ring, PACKET3(PACKET3_WAIT_REG_MEM, 5));
 *     amdgpu_ring_write(ring, (WAIT_REG_MEM_OPERATION(0) | [wait] |
 *                                  WAIT_REG_MEM_FUNCTION(0) |  [always] |
 *                                  WAIT_REG_MEM_ENGINE(0))); [me]
 *     amdgpu_ring_write(ring, mmVM_INVALIDATE_REQUEST);
 *     amdgpu_ring_write(ring, 0);
 *     amdgpu_ring_write(ring, 0); [ref]
 *     amdgpu_ring_write(ring, 0); [mask]
 *     amdgpu_ring_write(ring, 0x20); [poll interval]
 *
 * SEVEN dwords with a count of 5, so SIX payload dwords follow a count of 5.
 *
 * CORRECTION. This comment used to say "the header declares five payload words
 * and the code writes them, so the count and the payload agree". That was false:
 * it writes six, not five. tools/rx550pm4val.c measured the same property across
 * every packet in the GFX8 path and it is uniform:
 *
 *     WRITE_DATA       count 3   4 payload   total 5
 *     WAIT_REG_MEM     count 5   6 payload   total 7
 *     PFP_SYNC_ME      count 0   1 payload   total 2
 *     EVENT_WRITE      count 0   1 payload   total 2
 *     SET_SH_REG       count 1   2 payload   total 3
 *     SET_SH_REG (x2)  count 2   3 payload   total 4
 *     DISPATCH_DIRECT  count 3   4 payload   total 5
 *
 * Seven of seven: TOTAL DWORDS = count + 2, equivalently count = payload - 1.
 * So a decoder of this ASIC must not use count + 1 as a length, and the
 * DISPATCH_DIRECT comment above calling its own mismatch unexplained is wrong
 * for the same reason. See findings/038-validador-flujo-y-regla-del-count.md.
 *
 * CORRECTION, because I got this wrong first: I wrote above that
 * WAIT_REG_MEM_OPERATION does not exist, having grepped sid.h:398-413 and found
 * only FUNCTION, MEM_SPACE and ENGINE there. It exists, at vid.h:182, as
 * (x) << 6. The grep missed it because sid.h is not the header these fields come
 * from -- gfx_v8_0.c:33-35 includes vi.h, vi_structs.h and vid.h, and the
 * WAIT_REG_MEM_* macros live in vid.h:169-186. That is the same tab-indented
 * #define and wrong-file mistake that hid RX550_PKT3_* from an earlier grep in
 * this project; the fix is the same, grep the file the code includes.
 *
 * The consequence for this function is that OPERATION is a parameter rather than
 * omitted, because it is a real field with two values used on this same ASIC:
 * 0 ("wait") for the vm-flush at :6206 and 1 ("write, wait, write") for the HDP
 * flush at :6054. Both encode to 0x40 in the command word.
 *
 * Combined with FUNCTION(0) = "always" (vid.h:170-177) and mask 0, the vm-flush
 * instance of this packet compares nothing. What the hardware waits on is
 * NOT_DETERMINED; findings/029-orden-validacion-fence-no-ring.md states the same and this encoder does not guess.
 */
/*
   * EVIDENCIA  FORMATO = PROVEN, y con la dimension de la prueba corregida.
   *   Los cuatro campos de control que esta funcion empaqueta y el valor
   *   0='always'. CORRECCION 1.1.0: esta marca decia antes que los cuatro estan
   *   PROVEN "por DOS familias de headers independientes: vid.h escrito a mano
   *   (:180-187) y soc15d.h generado del XML (:214-220)". Medido, es 3 de 4:
   *
   *     campo        vid.h                  soc15d.h                       2 fuentes
   *     FUNCTION   :169 ((x) << 0)     :199 (((unsigned)(x)) & 0x7) << 0    SI
   *     MEM_SPACE  :178 ((x) << 4)     :200 (((unsigned)(x)) & 0x3) << 4    SI
   *     OPERATION  :182 ((x) << 6)     :201 (((unsigned)(x)) & 0x3) << 6    SI
   *     ENGINE     :186 ((x) << 8)     NO EXISTE                        -- NO --
   *
   *   ENGINE << 8 tiene UNA sola fuente en todo el arbol: vid.h:186, y cero
   *   coincidencias en soc15d.h y en vi.h. Una corroboracion declarada sobre
   *   cuatro campos y medida sobre tres es el mismo defecto que tumbo a
   *   findings/034-corpus-autoconsistente-layouts-pm4.md: un contraste hecho
   *   sobre una fuente no es un contraste.
   *
   *   Y las dos familias no se parecen en la codificacion: soc15d.h APLICA
   *   MASCARA a cada campo (& 0x7, & 0x3) y vid.h no. Que coincidan en el
   *   desplazamiento y no en el ancho no es coincidir: el dato de que ENGINE es
   *   de 1 bit, o de que FUNCTION son 3, sale de UN solo fichero.
   *
   *   "generado del XML" no consta en el fichero: ni vid.h ni soc15d.h llevan
   *   marca de generado. Que haya dos familias no es lo mismo que sean
   *   independientes: ambas acabaron en la misma base de datos de ASIC de AMD,
   *   asi que son dos CODIFICACIONES de una especificacion, no dos
   *   observaciones independientes de ella.
   *
   *   El fichero del que sale la instancia que el comentario transcribe,
   *   gfx_v8_0.c, SI corre en Polaris12 --
   *   findings/043-vuelta-atras-035-y-036-leian-el-asic-equivocado.md:70.
   *   Encadre y medidas: findings/122-para-que-el-encuadre-de-dos-fuentes-resulte-honesto.md
 *   MASK=0 vacia la comparacion (110-funcion-es-de-wait-reg-mem-no-del-invalidate.md:187), que es lo que hace que un
 *   FUNCTION=0 con mask=0 sea una espera y no una comprobacion.
 * NOT_DETERMINED subordinados, y son distintos entre si:
 *   - Que hace el hardware con FUNCTION=0, OPERATION=0, mask=0, poll=0x20
 *     sigue abierto (110-funcion-es-de-wait-reg-mem-no-del-invalidate.md:194,
 *     068-orden-emision-ptba-invalidate-wait-pfp.md:111,
 *     107-sc-function-always-2-de-7-y-el-ring-usa-1.md:151).
 *     findings/108-sd-pfp-escribe-me-espera-punto-de-visibilidad.md:144
 *     lo eleva a HYPOTHESIS (barrier de visibilidad, no comparacion) y
 *     findings/109-sd-un-anillo-dos-motores-tres-esperas.md:50-62 demuestra que el
 *     driver SI sabe escribir una espera real cuando quiere. El caso vacio es
 *     una eleccion, no una averia, y eso es lo que hace que duela no saberlo.
 *   - Por que count = payload - 1: la regla esta medida (7/7,
 *     038-validador-flujo-y-regla-del-count.md:34) pero
 *     038-validador-flujo-y-regla-del-count.md:49-52 la declara observacion sobre el camino GFX8, no ley de arquitectura.
 *   - El parametro engine NO es universal: ME en el vm-flush
 *     (108-sd-pfp-escribe-me-espera-punto-de-visibilidad.md:137), PFP en el
 *     hdp_flush del ring GFX (109-sd-un-anillo-dos-motores-tres-esperas.md:36-37).
 *     La emision lo resuelve; el alcance lo
 *     decide el llamante, y esta funcion no lo puede ver.
 */

void rx550_pm4_wait_reg_mem(struct rx550_pm4_ib *ib, __u32 reg, __u32 ref,
			    __u32 mask, __u32 poll, __u32 function,
			    __u32 operation, __u32 mem_space, __u32 engine)
{
	__u32 cmd;

	if (!ib || ib->length_dw + 7 > ib->size_dw)
		return;

	cmd = RX550_WAIT_REG_MEM_FUNCTION(function & 0x7u);
	cmd |= RX550_WAIT_REG_MEM_MEM_SPACE(mem_space & 0x1u);
	cmd |= RX550_WAIT_REG_MEM_OPERATION(operation & 0x3u);
	cmd |= RX550_WAIT_REG_MEM_ENGINE(engine & 0x1u);

	ib->buf[ib->length_dw++] =
		rx550_pm4_header(RX550_PKT3_WAIT_REG_MEM, 5, false);
	ib->buf[ib->length_dw++] = cmd;
	ib->buf[ib->length_dw++] = reg;
	ib->buf[ib->length_dw++] = 0;
	ib->buf[ib->length_dw++] = ref;
	ib->buf[ib->length_dw++] = mask;
	ib->buf[ib->length_dw++] = poll;
}

/*
 * rx550_pm4_pfp_sync_me - emit PFP_SYNC_ME, two dwords.
 *
 * gfx_v8_0.c:6218-6219:
 *
 *     amdgpu_ring_write(ring, PACKET3(PACKET3_PFP_SYNC_ME, 0));
 *     amdgpu_ring_write(ring, 0x0);
 *
 * A count of 0 and a second dword of zero, which is the same shape as
 * EVENT_WRITE: a packet whose trailing dword is not payload.
 * findings/020-vmflush-dword-budget-gfx8.md:55 settled that a KIQ ring does not emit
 * this, and gfx_v8_0.c:6216 guards it with
 * `if (usepfp)`, so this function's caller decides, not the function.
 */
/*
 * EVIDENCIA  = PROVEN_DERIVED  -- findings/068-orden-emision-ptba-invalidate-wait-pfp.md:107
 *   (condicion de emision solo-ring-GFX, PROVEN) y :23-49 (secuencia).
 *   El opcode 0x42 es identico en 9 generaciones. El count 0 -> 1 dword de payload,
 *   2 en total, es la regla de findings/038-validador-flujo-y-regla-del-count.md:28.
 *   NOT_DETERMINED subordinado: que hace exactamente PFP_SYNC_ME en el hardware
 *   sigue abierto (findings/095-se-pfp-me-ce-tres-motores-tres-icache.md).
 */

void rx550_pm4_pfp_sync_me(struct rx550_pm4_ib *ib)
{
	if (!ib || ib->length_dw + 2 > ib->size_dw)
		return;

	ib->buf[ib->length_dw++] =
		rx550_pm4_header(RX550_PKT3_PFP_SYNC_ME, 0, false);
	ib->buf[ib->length_dw++] = 0;
}

/*
 * rx550_vm_flush - program a page table base and invalidate that VMID's TLB.
 *
 * This is the function findings/036-correccion-023-implementada-ptepde.md said was missing: the one that gives the
 * PTEPDE producer somewhere to point. It is the composition of
 * gfx_v8_0_ring_emit_vm_flush() (gfx_v8_0.c:6197-6221) and
 * gmc_v8_0_emit_flush_gpu_tlb() (gmc_v8_0.c:661-677), and those two are the only
 * places in the GFX8 tree that write a per-VMID PTBA outside of gart
 * initialisation.
 *
 * ALL-OR-NOTHING, and the reason is specific rather than stylistic: a vm-flush
 * cut in half is either a PTBA written with no invalidate -- the hardware keeps
 * translating from the old directory -- or an invalidate with no wait. Neither
 * is a shorter command stream, both are a different command stream. So this
 * checks capacity once, for the whole sequence, rather than letting the three
 * constituent emitters each check their own.
 *
 * The order below is the whole guarantee that exists at the software level:
 *
 *   1. PTEPDE  (emitted earlier, into the same IB, by the caller)
 *   2. PTBA    this function, first packet
 *   3. invalidate
 *   4. wait for the invalidate
 *   5. PFP sync, if this is a gfx ring
 *
 * Steps 2 and 3 are in the same ring as step 1, which is the connection worth
 * stating: on GFX8 the page directory is written by SDMA into memory and the base
 * that names it is written by the command processor out of the same IB. Neither
 * one alone is a translation. The hardware-execution order of the three is
 * still NOT_DETERMINED -- findings/018-execution-order-invalidacion-gfx8.md:188
 * lo declara NOT_PROVEN -- and is not asserted here.
 *
 * Se cita por nombre completo a proposito: el numero 029 esta duplicado en el
 * arbol (dos ficheros 029-) y a secas no dice cual. Es el modo de fallo que
 * findings/114-implgate-cinco-bugs-propios-y-una-afirmacion-falsa.md documenta, y el mismo que se corrigio en el .h de este driver.
 *
 * Returns 1 if the sequence was written, 0 if it was refused. A caller that
 * ignores this gets a silently un-flushed VMID, which is the exact failure
 * findings/029-orden-validacion-fence-no-ring.md was written about.
 */
/*
 * EVIDENCIA  ORDEN DE EMISION = PROVEN_DERIVED  -- findings/068-orden-emision-ptba-invalidate-wait-pfp.md:22-49.
 *   Secuencia transcrita con valores exactos: PTBA -> INVALIDATE -> WAIT -> PFP_SYNC_ME,
 *   19 y 17 dwords segun el caso.
 *   NO SUBIR A PROVEN: findings/018-execution-order-invalidacion-gfx8.md deja el ORDEN
 *   DE EJECUCION en hardware como NOT_DETERMINED. Emision es una cosa y ejecucion otra.
 */

__u32 rx550_vm_flush(struct rx550_pm4_ib *ib, __u32 vmid, __u64 pd_addr,
		     bool gfx_ring)
{
	__u32 need = gfx_ring ? RX550_VM_FLUSH_DW : RX550_VM_FLUSH_DW_NO_PFP;
	__u32 reg;

	if (!ib)
		return 0;

	/* Refuse before writing anything. See the header for what reg == 0 means. */
	reg = rx550_vm_ptba_reg(vmid);
	if (reg == 0)
		return 0;

	if (ib->length_dw + need > ib->size_dw)
		return 0;

	rx550_pm4_write_data(ib, reg, (__u32)(pd_addr >> 12),
			     gfx_ring ? RX550_RING_ENGINE_PFP :
					RX550_RING_ENGINE_ME);

	rx550_pm4_write_data(ib, RX550_MM_VM_INVALIDATE_REQUEST,
			     rx550_vm_invalidate_mask(vmid),
			     gfx_ring ? RX550_RING_ENGINE_PFP :
					RX550_RING_ENGINE_ME);

	/* OPERATION "wait", FUNCTION "always", MEM_SPACE register, ENGINE me:
	 * four zeros, which is why the command word is 0. */
	rx550_pm4_wait_reg_mem(ib, RX550_MM_VM_INVALIDATE_REQUEST, 0, 0, 0x20,
			       RX550_WAIT_REG_MEM_FUNC_ALWAYS,
			       RX550_WAIT_REG_MEM_OP_WAIT,
			       RX550_WAIT_REG_MEM_MEM_SPACE_REG,
			       RX550_WAIT_REG_MEM_ENGINE_ME);

	if (gfx_ring)
		rx550_pm4_pfp_sync_me(ib);

	return 1;
}

/*
 * EVIDENCIA  = PROVEN  -- findings/007-gfx8-pm4-format.md:125-135.
 *   SET_SH_REG_START = 0x2c00 y el payload es el offset RELATIVO a esa base.
 *   MODEL_CHOICE PROPIO, sin hallazgo: la rama de saturacion de esta funcion
 *   (reg por debajo de la base -> 0) no la cubre ningun documento del corpus. Se deja
 *   marcada como decision propia para que no se lea como evidencia.
 */

__u32 rx550_pm4_reg_offset(__u32 reg)
{
	if (reg < RX550_PKT3_SET_SH_REG_START) {
		/*
		 * A register below the base cannot be expressed as an offset, and
		 * subtracting anyway would wrap into a valid-looking index for a
		 * different register. Saturate instead: a caller passing 0 gets a
		 * value the hardware will reject, not one that programs elsewhere.
		 */
		return 0;
	}
	return reg - RX550_PKT3_SET_SH_REG_START;
}
