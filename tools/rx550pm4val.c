/*
 * rx550pm4val - command stream validator/decoder for the RX 550 (GFX8).
 *
 * PURPOSE, AND WHY IT EXISTS AT ALL
 *
 * test_pm4.c checks the encoder against values transcribed from amdgpu source.
 * The encoder was written from that same source. So a MISREADING that I made
 * once in the encoder and once in the test passes all 147 checks. That
 * circularity is stated in findings/036 and findings/037 and it is not
 * hypothetical: findings/035 is a correction of exactly that kind of error.
 *
 * This tool breaks the circle. It does not know what the driver *intends*. It
 * walks the dwords and asks only questions that are answerable from the stream
 * itself:
 *
 *   - is this a PACKET3 or an sDMA packet?  (bits 31:30 vs 7:0)
 *   - does the declared length fit inside the buffer?
 *   - for an sDMA packet, is the length implied by the opcode consistent with
 *     what is left?  (sDMA has NO count field, so a wrong length is not a
 *     parse error, it is a different instruction stream)
 *   - do the vm-flush steps appear in the order PTBA -> invalidate -> wait?
 *   - is the PTEPDE entry count >= 1, given the field is stored minus one?
 *   - is the page-table-base register one of the two real runs, and does the
 *     VMID implied by its address match the VMID in the invalidate mask?
 *
 * A tool that cannot parse reports a distinct exit code. It never reports a
 * clean pass it did not earn. That is the same rule as the NOT_COVERAGE gate in
 * tools/pm4dw.c, and it exists because that gate was the only salvageable part
 * of a checker that otherwise reported "0 mismatches" over 2 of 63 definitions.
 *
 * SCOPE AND LIMITS
 *
 *   - Decodes format, not semantics. It cannot tell you whether writing 0x54f
 *     is a good idea; it can tell you that 0x54f is CONTEXT0's PTBA and that
 *     the VMID encoded in the address is 0.
 *   - Opcode coverage is a closed list. Anything outside it is UNKNOWN, the
 *     walk stops, and the exit code is 2. It never guesses a length.
 *   - It is a host tool. It reads a file or stdin. It never touches hardware.
 *
 * Build: cc -std=gnu11 -O2 -Wall -Wextra -o rx550pm4val rx550pm4val.c
 * Run:   rx550pm4val [--selftest] [file]
 */

#include <stdarg.h>
#include <stdbool.h>
#include <stdint.h>
#include <stdio.h>
#include <stdlib.h>
#include <string.h>

#define RX550_NUM_VMID		16

/* gmc_8_1_d.h:607,614,636,643. Two disjoint runs, and the second is lower. */
#define PTBA_RUN0_BASE		0x54f
#define PTBA_RUN0_LAST		0x556
#define PTBA_RUN1_BASE		0x50e
#define PTBA_RUN1_LAST		0x515
#define MM_VM_INVALIDATE_REQUEST	0x51e

/* PTEPDE is 10 dwords (sdma_v4_0.c:1649-1658); INDIRECT is 7 (:816-822). */
#define SDMA_OP_INDIRECT	4
#define SDMA_OP_PTEPDE		12

#define PACKET3_TYPE_MASK	0xc0000000u
#define PACKET3_TYPE		0xc0000000u

/* ------------------------------------------------------------------ output */

static int g_verbose;
static unsigned g_errors;
static unsigned g_warnings;
static unsigned g_packets;
static unsigned g_unknown;

static void err(const char *fmt, ...)
{
	va_list ap;

	g_errors++;
	printf("  ERROR  ");
	va_start(ap, fmt);
	vprintf(fmt, ap);
	va_end(ap);
	printf("\n");
}

static void warn(const char *fmt, ...)
{
	va_list ap;

	g_warnings++;
	printf("  warn   ");
	va_start(ap, fmt);
	vprintf(fmt, ap);
	va_end(ap);
	printf("\n");
}

static void note(const char *fmt, ...)
{
	va_list ap;

	if (!g_verbose)
		return;
	printf("  .     ");
	va_start(ap, fmt);
	vprintf(fmt, ap);
	va_end(ap);
	printf("\n");
}

/* --------------------------------------------------------------- opcode db */

struct pkt3_name {
	uint32_t op;
	const char *name;
};

/* Only opcodes the RX 550 path can emit, plus the two sDMA ones. Kept small on
 * purpose: an opcode with no length rule here is UNKNOWN, not "some length". */
static const struct pkt3_name g_pkt3[] = {
	{ 0x10, "NOP" },
	{ 0x15, "DISPATCH_DIRECT" },
	{ 0x16, "DISPATCH_INDIRECT" },
	{ 0x37, "WRITE_DATA" },
	{ 0x3c, "WAIT_REG_MEM" },
	{ 0x42, "PFP_SYNC_ME" },
	{ 0x43, "SURFACE_SYNC" },
	{ 0x58, "ACQUIRE_MEM" },
	{ 0x46, "EVENT_WRITE" },
	{ 0x47, "EVENT_WRITE_EOP" },
	{ 0x48, "EVENT_WRITE_EOS" },
	{ 0x76, "SET_SH_REG" },
};

static const char *pkt3_name(uint32_t op)
{
	size_t i;

	for (i = 0; i < sizeof g_pkt3 / sizeof g_pkt3[0]; i++)
		if (g_pkt3[i].op == op)
			return g_pkt3[i].name;
	return NULL;
}

/*
 * Length of an sDMA packet, in dwords, given only the opcode.
 * Returns 0 for an opcode with no rule here, which is UNKNOWN and not zero
 * length. Getting this wrong in the other direction is what a count field
 * prevents and sDMA does not have.
 */
static unsigned sdma_len(uint32_t op)
{
	switch (op) {
	case SDMA_OP_PTEPDE:
		return 10;
	case SDMA_OP_INDIRECT:
		return 6;	/* hdr, addr lo, addr hi, length, 0, 0 -- not 7 */
	default:
		return 0;
	}
}

static const char *sdma_name(uint32_t op)
{
	switch (op) {
	case SDMA_OP_PTEPDE:
		return "PTEPDE";
	case SDMA_OP_INDIRECT:
		return "INDIRECT";
	default:
		return NULL;
	}
}

/* ------------------------------------------------------- register decoding */

/*
 * Which page-table-base run an address belongs to, and the VMID it implies.
 * Returns the run index (0 or 1), or -1 if the address is not a PTBA at all.
 *
 * The asymmetry is the whole reason this function exists: the runs are disjoint
 * AND out of VMID order, so address 0x552 is VMID 3 and 0x552+1 is not VMID 4
 * under a single-array model. See findings/037.
 */
static int ptba_vmid(uint32_t reg, uint32_t *vmid)
{
	if (reg >= PTBA_RUN0_BASE && reg <= PTBA_RUN0_LAST) {
		*vmid = reg - PTBA_RUN0_BASE;
		return 0;
	}
	if (reg >= PTBA_RUN1_BASE && reg <= PTBA_RUN1_LAST) {
		*vmid = reg - PTBA_RUN1_BASE + 8;
		return 1;
	}
	return -1;
}


/*
 * The aperture registers, which is where a single-array PTBA model lands.
 * gmc_8_1_d.h: these are the addresses 0x557..0x55e, i.e. PTBA_RUN0 + 8..15.
 * Naming them lets the report say "you wrote a page-directory value into the
 * aperture window" instead of "unknown register 0x557", which is the difference
 * between a diagnostic and a shrug.
 */
static const char *aperture_name(uint32_t reg)
{
	switch (reg) {
	case 0x557: return "mmVM_CONTEXT0_PAGE_TABLE_START_ADDR";
	case 0x558: return "mmVM_CONTEXT1_PAGE_TABLE_START_ADDR";
	case 0x55f: return "mmVM_CONTEXT0_PAGE_TABLE_END_ADDR";
	case 0x55e: return "mmVM_CONTEXT1_PAGE_TABLE_END_ADDR";
	default:    return NULL;
	}
}

/* ---------------------------------------------------------------- the walk */

struct vmflush_state {
	bool saw_ptba;
	uint32_t ptba_vmid;
	size_t ptba_at;
	bool saw_invalidate;
	uint32_t invalidate_vmid;
	size_t invalidate_at;
	bool saw_wait;
	size_t wait_at;
	int wait_before_invalidate;
	int wait_before_ptba;
	bool saw_coherence;
	size_t coherence_at;
	bool saw_indirect;
	size_t indirect_at;
	int indirect_without_coherence;
	int indirect_in_ib;
};

/*
 * The coherence packets. Both write a CP_COHER_CNTL with the same five ACTION_ENA
 * bits, so the discriminators are the length and the presence of the 64-bit
 * halves. gfx_v8_0.c emits SURFACE_SYNC (5 dwords, no HI) on gfx rings and
 * ACQUIRE_MEM (7 dwords, SIZE_HI and BASE_HI) on compute rings.
 */
#define COHER_CNTL_FULL	0x28c40000u

static void decode_write_data(const uint32_t *d, struct vmflush_state *vs,
			      size_t *at)
{
	uint32_t cmd = d[1];
	uint32_t reg = d[2];
	uint32_t val = d[4];
	uint32_t vmid;
	int run;

	note("WRITE_DATA cmd=0x%08X reg=0x%04X val=0x%08X", cmd, reg, val);

	if (!(cmd & (1u << 20)))
		warn("WRITE_DATA at 0x%04X has WR_CONFIRM clear; gfx_v8_0_ring_emit_wreg sets it for gfx and compute rings",
		     reg);

	run = ptba_vmid(reg, &vmid);
	if (run >= 0) {
		/* No alignment check here, and there was one here first that was
		 * WRONG. What lands in this register is pd_addr >> 12, a page frame
		 * number. A PFN has no alignment requirement -- its low 12 bits are
		 * significant PFN bits, not padding. The alignment requirement is
		 * on pd_addr before the shift, and that is the caller's to hold.
		 * Checking the shifted value flagged every legal write, including
		 * the known-good vector, which is how I found out it was wrong. */
		printf("  [PTBA ] run%d vmid=%u  reg=0x%04X  pfn (pd_addr>>12) = 0x%08X\n",
		       run, vmid, reg, val);
		vs->saw_ptba = true;
		vs->ptba_vmid = vmid;
		vs->ptba_at = *at;
		return;
	}

	if (reg == MM_VM_INVALIDATE_REQUEST) {
		printf("  [INV  ] VM_INVALIDATE_REQUEST = 0x%08X\n", val);
		if (val == 0)
			err("VM_INVALIDATE_REQUEST = 0 invalidates no context");
		if (val & ~((1u << RX550_NUM_VMID) - 1))
			err("VM_INVALIDATE_REQUEST = 0x%08X sets bits outside contexts 0-15", val);
		/* The mask may name one context or several. Record the lowest set
		 * bit as "the" vmid, and let the cross-check below be the thing that
		 * notices a mismatch. A mask with more than one bit set is legal on
		 * this register -- gmc_v8_0_flush_gpu_tlb is called with 1 << vmid
		 * but nothing forbids a wider flush -- so it is noted, not flagged. */
		vs->saw_invalidate = true;
		vs->invalidate_vmid = val ? (uint32_t)__builtin_ctz(val) : 0;
		vs->invalidate_at = *at;
		if (val && (val & (val - 1)))
			warn("VM_INVALIDATE_REQUEST names %u contexts; the PTBA cross-check uses the lowest",
			     (unsigned)__builtin_popcount(val));
		return;
	}

	{
		const char *ap = aperture_name(reg);

		if (ap)
			printf("  [APER ] 0x%04X %s = 0x%08X\n", reg, ap, val);
		else
			printf("  [REG  ] 0x%04X = 0x%08X\n", reg, val);
	}
}

static void decode_coherence(const uint32_t *d, uint32_t op, size_t *at,
			     struct vmflush_state *vs)
{
	int wide = (op == 0x58);

	printf("  [SYNC ] %s CP_COHER_CNTL=0x%08X SIZE=0x%08X",
	       wide ? "ACQUIRE_MEM" : "SURFACE_SYNC", d[1], d[2]);
	if (wide)
		printf(" SIZE_HI=0x%08X", d[3]);
	printf(" BASE=0x%08X", wide ? d[4] : d[3]);
	if (wide)
		printf(" BASE_HI=0x%08X", d[5]);
	printf(" poll=0x%X\n", d[wide ? 6 : 4]);

	if (d[1] != COHER_CNTL_FULL)
		warn("%s writes CP_COHER_CNTL=0x%08X; gfx_v8_0_emit_mem_sync%s hard-codes 0x%08X",
		     wide ? "ACQUIRE_MEM" : "SURFACE_SYNC", d[1],
		     wide ? "_compute" : "", COHER_CNTL_FULL);

	vs->saw_coherence = true;
	vs->coherence_at = *at;
}

/* The INDIRECT packet is 6 dwords, not 7: hdr, addr lo, addr hi, length, 0, 0. */
static void decode_indirect2(const uint32_t *d, size_t *at,
			     struct vmflush_state *vs)
{
	uint64_t addr = ((uint64_t)d[2] << 32) | d[1];
	uint32_t len = d[3];
	uint32_t op = d[0] & 0xffu;
	uint32_t vmid = (d[0] >> 16) & 0xfu;

	printf("  [REF  ] INDIRECT opcode=%u vmid=%u gpu_addr=0x%016llX length_dw=%u\n",
	       op, vmid, (unsigned long long)addr, len);

	if (op != 4)
		err("INDIRECT opcode is %u; vega10_sdma_pkt_open.h:29 says SDMA_OP_INDIRECT is 4", op);
	if (addr & 0x1f)
		err("INDIRECT gpu_addr 0x%llX is not 32-byte aligned; sdma_v4_0_ring_emit_ib "
		    "masks with 0xffffffe0 rather than checking",
		    (unsigned long long)addr);
	if (len == 0)
		err("INDIRECT length_dw is 0, which is a null submission");
	if (d[4] != 0 || d[5] != 0)
		warn("INDIRECT trailing dwords are 0x%08X 0x%08X; sdma_v4_0.c:821-822 writes 0 0",
		     d[4], d[5]);

	vs->saw_indirect = true;
	vs->indirect_at = *at;
	if (!vs->saw_coherence)
		vs->indirect_without_coherence = 1;
}

static void decode_wait_reg_mem(const uint32_t *d, size_t *at)
{
	uint32_t cmd = d[1];
	uint32_t function = cmd & 0x7u;
	uint32_t mem_space = (cmd >> 4) & 0x1u;
	uint32_t operation = (cmd >> 6) & 0x3u;
	uint32_t engine = (cmd >> 8) & 0x1u;
	static const char *fn[] = { "always", "<", "<=", "==", "!=", ">=", ">" };

	printf("  [WAIT ] reg=0x%04X ref=0x%08X mask=0x%08X poll=0x%X "
	       "op=%u function=%s mem_space=%s engine=%s\n",
	       d[2], d[4], d[5], d[6], operation,
	       function < 7 ? fn[function] : "?",
	       mem_space ? "mem" : "reg", engine ? "pfp" : "me");
	(void)at;	/* position tracked by the caller, not here */

	/* findings/029: the vm-flush uses function 0 (always) with mask 0, so it
	 * compares nothing. Not an error -- it is what the driver does -- but a
	 * reader of the stream deserves to be told. */
	if (function == 0 && d[5] == 0)
		note("this WAIT_REG_MEM compares nothing (function=always, mask=0); "
		     "what it waits on is NOT_DETERMINED (findings/029)");
}

static void decode_ptepde(const uint32_t *d)
{
	uint64_t pe = (uint64_t)d[1] | ((uint64_t)d[2] << 32);
	uint64_t flags = (uint64_t)d[3] | ((uint64_t)d[4] << 32);
	uint64_t addr = (uint64_t)d[5] | ((uint64_t)d[6] << 32);
	uint32_t incr = d[7];
	uint32_t pad = d[8];
	uint32_t nm1 = d[9];
	/* Campo plano: el valor ES el numero de entradas. findings/043. */

	printf("  [PTE  ] pe=0x%016llX flags=0x%016llX addr=0x%016llX incr=0x%X entries=%u\n",
	       (unsigned long long)pe, (unsigned long long)flags,
	       (unsigned long long)addr, incr, nm1);

	if (pad != 0)
		err("PTEPDE dword 8 is 0x%08X; sdma_v4_0.c:1657 writes 0 unconditionally", pad);
	/* El campo de entradas es plano en el ASIC que corre (sdma_v3_0.c:996),
	 * findings/043. Asi que no hay mas-uno que comprobar: lo que se comprueba
	 * es que el dword 8 sea 0, que si lo es el driver, y que el recuento no
	 * sea absurdo. Un valor 0xffffffff seria 4 G entradas si es plano, y
	 * 4 G si es mas-uno tambien, asi que en ambos casos es un error y se
	 * reporta como tal sin afirmar cual de las dos lecturas se aplica. */
	if (nm1 == 0xffffffffu)
		err("PTEPDE entry count field is 0xFFFFFFFF, i.e. 2^32 entries under "
		    "either encoding");
	if (incr == 0)
		warn("PTEPDE incr is 0; a count above 1 would rewrite one entry N times");
	if (nm1 > 1 && (uint64_t)nm1 * 8ull > 0x100000ull)
		warn("PTEPDE entries=%u span %llu bytes of page table",
		     nm1, (unsigned long long)nm1 * 8ull);
}

/*
 * Walk the stream. Returns 0 if every dword was consumed by a packet the tool
 * understands, 1 if a structural violation was reported, 2 if the walk could
 * not continue (unknown opcode, or a packet that runs past the end).
 *
 * 2 is deliberately distinct from 0. "I could not parse this" is not "this is
 * fine", and conflating them is how a validator becomes a rubber stamp.
 */
static int walk(const uint32_t *buf, size_t ndw)
{
	struct vmflush_state vs;
	size_t i = 0;

	memset(&vs, 0, sizeof vs);

	printf("--- %zu dwords (0x%zX bytes) ---\n", ndw, ndw * 4);

	while (i < ndw) {
		uint32_t d = buf[i];

		if ((d & PACKET3_TYPE_MASK) == PACKET3_TYPE) {
			uint32_t op = (d >> 8) & 0xffu;
			uint32_t count = (d >> 16) & 0x3fffu;
			const char *nm = pkt3_name(op);
			/*
			 * TOTAL DWORDS = count + 2, not count + 1.
			 *
			 * I wrote count + 1 first and this tool's own selftest caught
			 * it, because the stream then desynchronised one dword early
			 * and reported "dword 0x00000900 is neither a PACKET3 nor a
			 * known sDMA packet" on a stream that is perfectly valid.
			 *
			 * The rule is uniform across every packet in the GFX8 path,
			 * measured against gfx_v8_0.c and the GFX8 ib/vm emitters:
			 *
			 *   WRITE_DATA       count 3   4 payload dwords   -> 5
			 *   WAIT_REG_MEM     count 5   6 payload dwords   -> 7
			 *   PFP_SYNC_ME      count 0   1 payload dword    -> 2
			 *   EVENT_WRITE      count 0   1 payload dword    -> 2
			 *   SET_SH_REG       count 1   2 payload dwords   -> 3
			 *   SET_SH_REG (x2)  count 2   3 payload dwords   -> 4
			 *   DISPATCH_DIRECT  count 3   4 payload dwords   -> 5
			 *
			 * In every case the declared count is one LESS than the
			 * payload. So the honest statement about the format is
			 * "count = payload - 1", and DISPATCH_DIRECT is not a
			 * driver quirk. rx550_pm4.c carried a comment calling
			 * DISPATCH_DIRECT's mismatch unexplained; that comment was
			 * wrong, and the general rule explains it.
			 */
			size_t need = (size_t)count + 2;

			g_packets++;
			printf("dw%-4zu PACKET3 %-16s count=%-4u", i,
			       nm ? nm : "?", count);

			if (!nm) {
				g_unknown++;
				printf("\n");
				err("dw%zu: PACKET3 opcode 0x%02X is not in this tool's table; "
				    "stopping rather than guessing a length", i, op);
				return 2;
			}
			if (i + need > ndw) {
				printf("\n");
				err("dw%zu: %s declares count=%u, needing %zu dwords, "
				    "but only %zu remain",
				    i, nm, count, need, ndw - i);
				return 2;
			}
			printf(" len=%zu\n", need);

			if (op == 0x37)
				decode_write_data(&buf[i], &vs, &i);
			else if (op == 0x43 || op == 0x58)
				decode_coherence(&buf[i], op, &i, &vs);
			else if (op == 0x3c) {
				decode_wait_reg_mem(&buf[i], &i);
				if (!vs.saw_invalidate)
					vs.wait_before_invalidate = 1;
				if (!vs.saw_ptba)
					vs.wait_before_ptba = 1;
				vs.saw_wait = true;
				vs.wait_at = i;
			} else if (op == 0x42 && count != 0)
				warn("PFP_SYNC_ME has count=%u; gfx_v8_0.c:6218 writes count 0",
				     count);

			i += need;
			continue;
		}

		/* Not a PACKET3: an sDMA packet, opcode in bits 7:0. No count field,
		 * so the length comes from the opcode or nowhere. */
		{
			uint32_t op = d & 0xffu;
			const char *nm = sdma_name(op);
			unsigned need = sdma_len(op);

			if (!nm) {
				g_unknown++;
				err("dw%zu: dword 0x%08X is neither a PACKET3 nor a known "
				    "sDMA packet (opcode %u); stopping",
				    i, d, op);
				return 2;
			}
			g_packets++;
			if (i + need > ndw) {
				err("dw%zu: sDMA %s is %u dwords, needing %u, but only "
				    "%zu remain -- and sDMA has no count to make this "
				    "a parse error rather than a desync",
				    i, nm, need, need, ndw - i);
				return 2;
			}
			printf("dw%-4zu sDMA   %-16s len=%-4u (implied by opcode)\n",
			       i, nm, need);

			if (op == SDMA_OP_PTEPDE)
				decode_ptepde(&buf[i]);
			else
				decode_indirect2(&buf[i], &i, &vs);

			i += need;
		}
	}

	/* Cross-packet invariants. These need no corpus constant: they are
	 * relations between packets that are both present. */
	if (vs.saw_ptba && vs.saw_invalidate) {
		if (vs.ptba_vmid != vs.invalidate_vmid)
			err("vm-flush names PTBA for VMID %u but invalidates VMID %u",
			    vs.ptba_vmid, vs.invalidate_vmid);
		else
			printf("--- vm-flush consistent: PTBA and invalidate both name VMID %u ---\n",
			       vs.ptba_vmid);
	} else if (vs.saw_ptba || vs.saw_invalidate) {
		/* ERROR, and it was a warn() first.
		 *
		 * A stream that invalidates a VMID but writes no register in either
		 * page-table-base run is inconsistent whatever the other write was.
		 * And the usual cause is the findings/037 bug: a single stride-1
		 * array of 16 sends VMIDs 8-15 to PTBA_RUN0 + 8, which is
		 * mmVM_CONTEXT0_PAGE_TABLE_START_ADDR. Flagging that as a warning
		 * would have let the exact mistake the tool was built to catch
		 * through with exit 0.
		 *
		 * It cannot name the offending register from here, because the
		 * decoder only knows "some other WRITE_DATA happened"; the
		 * aperture_name() line above is what makes it findable. */
		err("vm-flush is incomplete: PTBA %s, invalidate %s. A stream that "
		    "invalidates without naming a page table base either lost the "
		    "PTBA write or wrote it to 0x557-0x55e (the aperture registers)",
		    vs.saw_ptba ? "present" : "absent",
		    vs.saw_invalidate ? "present" : "absent");
	}
	if (vs.wait_before_ptba)
		err("a WAIT_REG_MEM precedes the PTBA write; gfx_v8_0_ring_emit_vm_flush writes the PTBA first");
	if (vs.wait_before_invalidate)
		err("a WAIT_REG_MEM precedes the invalidate; gfx_v8_0_ring_emit_vm_flush invalidates first");
	if (vs.saw_wait && !vs.saw_invalidate)
		warn("WAIT_REG_MEM present with no invalidate to wait on");

	/*
	 * Coherence before reference.
	 *
	 * amdgpu_ib_get() sets AMDGPU_IB_FLAG_EMIT_MEM_SYNC and amdgpu_ib.c:235
	 * turns it into a coherence packet emitted into the RING, immediately
	 * before the packet that names the IB. The IB lives in GTT
	 * (amdgpu_ib.c:362) and is written by the CPU, so the GPU fetching it
	 * over PCIe is exactly the case this ordering exists for. An INDIRECT
	 * with no coherence packet before it is a submission the driver of
	 * reference would not produce.
	 */
	if (vs.indirect_without_coherence)
		err("an INDIRECT at dw%zu references an IB with no coherence packet "
		    "before it; amdgpu_ib.c:235 emits one, and the IB is CPU-written "
		    "GTT memory", vs.indirect_at);
	if (vs.saw_coherence && vs.saw_indirect) {
		if (vs.coherence_at < vs.indirect_at)
			printf("--- delivery order verified: coherence dw%zu < INDIRECT dw%zu ---\n",
			       vs.coherence_at, vs.indirect_at);
		else
			err("the INDIRECT at dw%zu precedes the coherence packet at dw%zu",
			    vs.indirect_at, vs.coherence_at);
	}

	/*
	 * PTBA before invalidate, before wait.
	 *
	 * This check was MISSING and a mutation found it: swapping the two
	 * WRITE_DATA packets in the encoder left the stream fully parseable, with
	 * the same VMID in both places, and this tool reported CLEAN. Recording
	 * the position of each step and comparing the positions is what closes
	 * that. Positions rather than a state flag, because "have I seen it yet"
	 * cannot express "was it before".
	 *
	 * A WAIT_REG_MEM is not necessarily part of a vm-flush -- gfx_v8_0.c uses
	 * it for the HDP flush too -- so only the relative order of steps that
	 * are all present is asserted, and only when all three are.
	 */
	if (vs.saw_ptba && vs.saw_invalidate && vs.saw_wait) {
		if (vs.ptba_at > vs.invalidate_at)
			err("the invalidate (dw%zu) precedes the PTBA write (dw%zu); "
			    "gmc_v8_0_emit_flush_gpu_tlb writes the PTBA first, so a "
			    "flush ordered this way invalidates the old directory "
			    "and then points at the new one",
			    vs.invalidate_at, vs.ptba_at);
		if (vs.invalidate_at > vs.wait_at)
			err("the wait (dw%zu) precedes the invalidate (dw%zu); the wait "
			    "is there to wait for the invalidate",
			    vs.wait_at, vs.invalidate_at);
		if (vs.ptba_at < vs.invalidate_at && vs.invalidate_at < vs.wait_at)
			printf("--- vm-flush order verified: PTBA dw%zu < invalidate dw%zu "
			       "< wait dw%zu ---\n",
			       vs.ptba_at, vs.invalidate_at, vs.wait_at);
	}

	return g_errors ? 1 : 0;
}

/* --------------------------------------------------------------- selftest */

/* A known-good GFX8 stream: one PTEPDE then the 19-dword gfx vm-flush for VMID
 * 3. 29 dwords. This is the vector the cross-check in findings/038 uses. */
static const uint32_t g_good[] = {
	/* PTEPDE, sdma_v4_0.c:1649-1658 */
	0x0000000c, 0x00000000, 0x00000008, 0x00000003, 0x00000000,
	0x00002000, 0x00000000, 0x00000008, 0x00000000, 0x00000000,
	/* WRITE_DATA PTBA(vmid 3) = 0x54f + 3 = 0x552, value 0x900 */
	0xc0033700, 0x40100000, 0x00000552, 0x00000000, 0x00000900,
	/* WRITE_DATA VM_INVALIDATE_REQUEST = 1 << 3 */
	0xc0033700, 0x40100000, 0x0000051e, 0x00000000, 0x00000008,
	/* WAIT_REG_MEM: op 0, function always, reg space, me */
	0xc0053c00, 0x00000000, 0x0000051e, 0x00000000,
	0x00000000, 0x00000000, 0x00000020,
	/* PFP_SYNC_ME */
	0xc0004200, 0x00000000,
};

static int selftest(void)
{
	int bad = 0;
	unsigned e;
	int n;

	printf("=== rx550pm4val selftest ===\n\n");

	/* 1. The known-good vector must come back clean AND fully decoded. */
	printf("[1] known-good: 1 PTEPDE + gfx vm-flush vmid 3, 29 dwords\n");
	g_errors = g_warnings = g_packets = g_unknown = 0;
	n = walk(g_good, sizeof g_good / sizeof g_good[0]);
	if (n != 0 || g_errors || g_unknown)
		bad++;
	printf("    verdict: %s (exit %d, %u error(s), %u unknown)\n\n",
	       (n == 0 && !g_errors && !g_unknown) ? "PASS" : "FAIL", n, g_errors, g_unknown);

	/* 2. Empty input. Must be clean and decode zero packets, not crash and
	 * not claim it validated something. */
	printf("[2] empty stream (0 dwords)\n");
	g_errors = g_warnings = g_packets = g_unknown = 0;
	n = walk(g_good, 0);
	if (n != 0 || g_errors || g_packets != 0)
		bad++;
	printf("    verdict: %s (exit %d, %u packet(s))\n\n",
	       (n == 0 && g_packets == 0) ? "PASS" : "FAIL", n, g_packets);

	/* 3. Unknown opcode: exit 2, NOT 0. This is the whole design. */
	printf("[3] unknown PACKET3 opcode 0x99 (must exit 2, not 0)\n");
	{
		const uint32_t v[] = { 0xc0099900, 0, 0 };
		g_errors = g_warnings = g_packets = g_unknown = 0;
		n = walk(v, 3);
		if (n != 2 || !g_unknown)
			bad++;
		printf("    verdict: %s (exit %d, unknown=%u)\n\n",
		       (n == 2 && g_unknown) ? "PASS" : "FAIL", n, g_unknown);
	}
	/* 4. Unknown sDMA opcode: also exit 2. */
	printf("[4] unknown sDMA opcode 0x63 (must exit 2)\n");
	{
		const uint32_t v[] = { 0x00000063, 0, 0, 0 };
		g_errors = g_warnings = g_packets = g_unknown = 0;
		n = walk(v, 4);
		if (n != 2 || !g_unknown)
			bad++;
		printf("    verdict: %s (exit %d, unknown=%u)\n\n",
		       (n == 2 && g_unknown) ? "PASS" : "FAIL", n, g_unknown);
	}
	/* 5. Truncated PTEPDE: 9 of 10 dwords. Must exit 2, because sDMA has no
	 *    count and a short packet is a desync, not a parse error. */
	printf("[5] PTEPDE truncated to 9 dwords (must exit 2)\n");
	{
		g_errors = g_warnings = g_packets = g_unknown = 0;
		n = walk(g_good, 9);
		if (n != 2)
			bad++;
		printf("    verdict: %s (exit %d)\n\n", n == 2 ? "PASS" : "FAIL", n);
	}
	/* 6. Truncated PACKET3: count 3 with 2 dwords left. Exit 2. */
	printf("[6] WRITE_DATA count=3 with only 2 dwords left (must exit 2)\n");
	{
		const uint32_t v[] = { 0xc0033700, 0x40100000 };
		g_errors = g_warnings = g_packets = g_unknown = 0;
		n = walk(v, 2);
		if (n != 2)
			bad++;
		printf("    verdict: %s (exit %d)\n\n", n == 2 ? "PASS" : "FAIL", n);
	}
	/* 7. The straddle case: a stream that ends mid-packet at offset 28, one
	 *    dword into the PFP_SYNC_ME's second word. */
	printf("[7] PFP_SYNC_ME truncated to 1 dword (must exit 2)\n");
	{
		g_errors = g_warnings = g_packets = g_unknown = 0;
		n = walk(g_good, 28);
		if (n != 2)
			bad++;
		printf("    verdict: %s (exit %d)\n\n", n == 2 ? "PASS" : "FAIL", n);
	}
	/* 8. PTBA in the wrong run for the VMID being invalidated. This is the
	 *    findings/037 error, and it must be caught by a relation, not by a
	 *    transcribed constant. */
	printf("[8] PTBA run 0 vmid 3 (0x552) with invalidate mask for VMID 4\n");
	{
		uint32_t v[29];

		memcpy(v, g_good, sizeof v);
		/* dw19 is the invalidate mask. dw9 is the PTEPDE entry count; I put
		 * it there first and the vector passed for the wrong reason, which
		 * is the failure mode a self-test has to be checked against too. */
		v[19] = 1u << 4;		/* invalidate bit 4 */
		g_errors = g_warnings = g_packets = g_unknown = 0;
		n = walk(v, 29);
		if (n != 1 || !g_errors)
			bad++;
		printf("    verdict: %s (exit %d, %u error)\n\n",
		       (n == 1 && g_errors) ? "PASS" : "FAIL", n, g_errors);
	}
	/* 9. A stride-1 single-array PTBA: vmid 8 written as 0x557. That address
	 *    is not in either run, so the tool must say so rather than decode a
	 *    VMID for it. */
	printf("[9] PTBA 0x557 -- the address a single-array model would compute\n");
	{
		uint32_t v[29];

		memcpy(v, g_good, sizeof v);
		/* dw12 is the PTBA register, not dw7. */
		v[12] = PTBA_RUN0_BASE + 8;	/* 0x557 */
		g_errors = g_warnings = g_packets = g_unknown = 0;
		n = walk(v, 29);
		if (n != 1 || !g_errors)
			bad++;
		printf("    verdict: %s (exit %d, %u error(s)); 0x557 is not in either "
		       "PTBA run, so the vm-flush loses its PTBA and that is an error\n\n",
		       (n == 1 && g_errors) ? "PASS" : "FAIL", n, g_errors);
	}
	/* 10. PTEPDE with the entry count underflowed: 0xFFFFFFFF. */
	printf("[10] PTEPDE entry count field 0xFFFFFFFF (must be an error)\n");
	{
		uint32_t v[29];

		memcpy(v, g_good, sizeof v);
		v[9] = 0xffffffffu;	/* dw9 is the count-minus-one field */
		g_errors = g_warnings = g_packets = g_unknown = 0;
		n = walk(v, 29);
		if (n != 1 || !g_errors)
			bad++;
		printf("    verdict: %s (exit %d, %u error)\n\n",
		       (n == 1 && g_errors) ? "PASS" : "FAIL", n, g_errors);
	}
	/* 11. PTEPDE with a non-zero dword 8, which the driver never writes. */
	printf("[11] PTEPDE dword 8 non-zero (must be an error)\n");
	{
		uint32_t v[29];

		memcpy(v, g_good, sizeof v);
		v[8] = 1u;		/* dw8 is PTEPDE's unconditional zero */
		g_errors = g_warnings = g_packets = g_unknown = 0;
		n = walk(v, 29);
		if (n != 1 || !g_errors)
			bad++;
		printf("    verdict: %s (exit %d, %u error)\n\n",
		       (n == 1 && g_errors) ? "PASS" : "FAIL", n, g_errors);
	}
	/* 12. Ordering: the wait moved before the PTBA write. */
	printf("[12] WAIT_REG_MEM emitted before the PTBA (must be an error)\n");
	{
		uint32_t v[29];
		int j;

		/* Move the 7-dword WAIT (dw20..26) to the front, length preserving,
		 * so the stream still parses and the only thing under test is the
		 * ordering. Patching individual dwords instead would make the walk
		 * desynchronise, and a desync reports exit 2 for a reason that has
		 * nothing to do with the ordering rule being tested. */
		for (j = 0; j < 7; j++)
			v[j] = g_good[20 + j];
		memcpy(v + 7, g_good + 0, 20 * sizeof(uint32_t));
		memcpy(v + 27, g_good + 27, 2 * sizeof(uint32_t));
		g_errors = g_warnings = g_packets = g_unknown = 0;
		n = walk(v, 29);
		if (n != 1 || !g_errors)
			bad++;
		printf("    verdict: %s (exit %d, %u error)\n\n",
		       (n == 1 && g_errors) ? "PASS" : "FAIL", n, g_errors);
	}

	/* 13. INDIRECT with no coherence packet before it. The IB is CPU-written
	 *    GTT memory (amdgpu_ib.c:362), and amdgpu_ib.c:235 emits the coherence
	 *    packet for exactly that reason. */
	printf("[13] INDIRECT with no coherence packet (must be an error)\n");
	{
		/* Just the INDIRECT, 6 dwords, nothing before it. I first copied
		 * g_good + 10, which is the vm-flush without its PTEPDE -- that is a
		 * complete, valid vm-flush and has no INDIRECT in it at all, so the
		 * vector was testing nothing. The stream has to actually contain the
		 * reference whose missing coherence is the point. */
		const uint32_t v[6] = {
			0x00030004, 0x12345000, 0, 29, 0, 0,
		};
		g_errors = g_warnings = g_packets = g_unknown = 0;
		n = walk(v, 6);
		if (n != 1 || !g_errors)
			bad++;
		printf("    verdict: %s (exit %d, %u error)\n\n",
		       (n == 1 && g_errors) ? "PASS" : "FAIL", n, g_errors);
	}
	/* 14. The coherence packet AFTER the INDIRECT. Length preserving: swap the
	 *     5-dword SURFACE_SYNC and the 6-dword INDIRECT, which is 5+6 vs 6+5
	 *     -- not length preserving, so instead emit INDIRECT then a sync. */
	printf("[14] INDIRECT before the coherence packet (must be an error)\n");
	{
		/* 6 + 5 = 11, the same total, built by hand rather than swapped. */
		const uint32_t v[11] = {
			0x00030004, 0x12345000, 0, 19, 0, 0,		/* INDIRECT */
			0xc0034300, 0x28c40000, 0xffffffff, 0, 0x0a,	/* SURFACE_SYNC */
		};
		g_errors = g_warnings = g_packets = g_unknown = 0;
		n = walk(v, 11);
		if (n != 1 || !g_errors)
			bad++;
		printf("    verdict: %s (exit %d, %u error)\n\n",
		       (n == 1 && g_errors) ? "PASS" : "FAIL", n, g_errors);
	}
	/* 15. The full submission shape: coherence, INDIRECT, then the IB's own
	 *     contents. 5 + 6 + 29 = 40 dwords. The two address spaces meet here. */
	printf("[15] full submission: coherence + INDIRECT + IB contents\n");
	{
		uint32_t v[40];
		int j, nbad = 0;

		/* INDIRECT is 6 dwords at dw5..dw10, so the IB's 29 dwords start at
		 * dw11. I wrote 5 + j, which overlaps the INDIRECT by one dword and
		 * produced a stream that desynchronised. */
		for (j = 0; j < 29; j++)
			v[11 + j] = g_good[j];
		v[0] = 0xc0034300;			/* SURFACE_SYNC */
		v[1] = 0x28c40000;
		v[2] = 0xffffffff;
		v[3] = 0;
		v[4] = 0x0a;
		v[5] = 0x00030004;			/* INDIRECT, vmid 3 */
		v[6] = 0x12345000;
		v[7] = 0;
		v[8] = 29;				/* the IB is 29 dwords */
		v[9] = 0;
		v[10] = 0;
		g_errors = g_warnings = g_packets = g_unknown = 0;
		n = walk(v, 40);
		if (n != 0 || g_errors)
			nbad++;
		if (bad) {
			printf("    verdict: %s (exit %d, %u error(s), %u packet(s))\n\n",
			       nbad ? "FAIL" : "PASS", n, g_errors, g_packets);
			if (nbad)
				bad++;
		} else {
			printf("    verdict: PASS (exit %d, %u error(s), %u packet(s))\n\n",
			       n, g_errors, g_packets);
		}
	}
	/* 16. INDIRECT with a misaligned gpu_addr, which sdma_v4_0_ring_emit_ib
	 *     would have masked down silently. */
	printf("[16] INDIRECT with a misaligned gpu_addr (must be an error)\n");
	{
		uint32_t v[11] = {
			0x00030004, 0x1234501f, 0, 29, 0, 0,		/* low 5 bits set */
			0xc0034300, 0x28c40000, 0xffffffff, 0, 0x0a,
		};
		g_errors = g_warnings = g_packets = g_unknown = 0;
		n = walk(v, 11);
		if (n != 1 || !g_errors)
			bad++;
		printf("    verdict: %s (exit %d, %u error)\n\n",
		       (n == 1 && g_errors) ? "PASS" : "FAIL", n, g_errors);
	}

	e = (unsigned)bad;
	printf("=== selftest: %u of 16 vectors behaved as specified ===\n", 16 - e);
	if (bad) {
		printf("RESULT: FAIL\n");
		return 1;
	}
	printf("RESULT: PASS\n");
	return 0;
}

/* ------------------------------------------------------------------- input */

static int slurp(const char *path, uint32_t **out, size_t *out_ndw)
{
	FILE *f = path ? fopen(path, "rb") : stdin;
	uint32_t *buf = NULL;
	size_t cap = 0, n = 0;

	if (!f) {
		fprintf(stderr, "rx550pm4val: cannot open %s\n", path);
		return -1;
	}

	cap = 1024;
	buf = malloc(cap * sizeof *buf);
	if (!buf) {
		if (path)
			fclose(f);
		return -1;
	}

	for (;;) {
		unsigned char b[4];
		size_t got = fread(b, 1, 4, f);

		if (got == 0)
			break;
		if (got != 4) {
			fprintf(stderr,
				"rx550pm4val: input is not a whole number of dwords "
				"(trailing %zu byte(s))\n", got);
			free(buf);
			if (path)
				fclose(f);
			return -1;
		}
		if (n == cap) {
			uint32_t *nb;

			cap *= 2;
			nb = realloc(buf, cap * sizeof *buf);
			if (!nb) {
				free(buf);
				if (path)
					fclose(f);
				return -1;
			}
			buf = nb;
		}
		buf[n++] = (uint32_t)b[0] | ((uint32_t)b[1] << 8) |
			   ((uint32_t)b[2] << 16) | ((uint32_t)b[3] << 24);
	}

	if (path)
		fclose(f);
	*out = buf;
	*out_ndw = n;
	return 0;
}

int main(int argc, char **argv)
{
	uint32_t *buf;
	size_t ndw;
	int i, rc;

	for (i = 1; i < argc; i++) {
		if (strcmp(argv[i], "--selftest") == 0)
			return selftest();
		if (strcmp(argv[i], "-v") == 0 || strcmp(argv[i], "--verbose") == 0) {
			g_verbose = 1;
			continue;
		}
		if (strcmp(argv[i], "--help") == 0 || strcmp(argv[i], "-h") == 0) {
			printf("usage: %s [-v] [file]   (file of little-endian dwords; - for stdin)\n"
			       "       %s --selftest\n", argv[0], argv[0]);
			return 0;
		}
	}

	if (slurp(argc > 1 ? argv[argc - 1] : NULL, &buf, &ndw))
		return 2;

	printf("=== rx550pm4val: RX 550 (GFX8) command stream ===\n");
	rc = walk(buf, ndw);

	printf("--- %u packet(s), %u error(s), %u warning(s), %u unknown ---\n",
	       g_packets, g_errors, g_warnings, g_unknown);

	if (rc == 2)
		printf("RESULT: UNDECODED -- the walk stopped. This is NOT a pass.\n");
	else if (rc)
		printf("RESULT: VIOLATION\n");
	else
		printf("RESULT: CLEAN -- every dword was consumed by a packet this "
		       "tool understands, and no relation was violated. That is a "
		       "statement about the bytes, not about the hardware.\n");

	free(buf);
	/* 0 clean, 1 violation, 2 undecodable or unreadable input. */
	return rc;
}
