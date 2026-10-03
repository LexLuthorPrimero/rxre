// SPDX-License-Identifier: GPL-2.0
/*
 * rx550pm4_emit.c - dump real encoder output for rx550pm4val to validate.
 *
 * WHY THIS EXISTS
 *
 * test_pm4.c checks the encoder against values transcribed from amdgpu source,
 * and the encoder was written from that same source. A misreading made once in
 * each place passes every check. That is findings/035-correccion-ptepde-es-polaris12.md (retractada por 043,
 * como el error mismo: el fichero equivocado, no la conclusion) in concrete form: the
 * opcode name and the count-1 field were both wrong in findings/023-pte-productor-sdma-gfx8.md because the
 * wrong ASIC's file was read, and only a different KIND of evidence caught it.
 *
 * This program is the different kind of evidence. It links the SAME
 * ../kernel/rx550_pm4.c the module links, calls the SAME emitters, and writes
 * the dwords out. Nothing here is transcribed: if the encoder emits a wrong
 * count, the wrong opcode name's value, or the wrong dword order, the bytes
 * here carry that error and rx550pm4val sees it.
 *
 * What the validator can and cannot do with them:
 *
 *   CAN: parse the stream, check that declared lengths fit, check that the
 *        PTBA and the invalidate name the same VMID, check the PTEPDE entry
 *        count is not an underflow, check the vm-flush step order. All of that
 *        is answerable from the bytes plus the format rules, without consulting
 *        the corpus.
 *   CANNOT: tell you the right value is the right value. If both the encoder
 *        and the driver's intent are wrong in the same direction, the stream is
 *        internally consistent and will pass. That limitation is why this is a
 *        cross-check and not a proof.
 *
 * Output is raw little-endian dwords on stdout, so:
 *
 *     ./test_pm4_emit gfx 3 0x900000 > /tmp/stream.bin
 *     rx550pm4val /tmp/stream.bin
 *
 * The "ring-*" modes prepend the delivery path -- the coherence packet and the
 * INDIRECT that names the IB -- so the validator sees the two address spaces
 * meet. The IB those name is a fictitious 0x12345000 with a fixed length; the
 * point being validated is the ring-side packet sequence, not that address.
 */

#include <stdbool.h>
#include <stdint.h>
#include <stdio.h>
#include <stdlib.h>
#include <string.h>

#include "../kernel/rx550_pm4.h"

#define MAX_DW	256

static void usage(const char *me)
{
	fprintf(stderr,
		"usage: %s <mode> <vmid> <pd_addr_hex> [count] [incr] [flags_hex]\n"
		"  mode    gfx | compute | pteonly | ring-gfx | ring-compute\n"
		"  vmid    0-15\n"
		"  pd_addr page directory address, GPU bytes, hex\n"
		"  count   PTEPDE entries, default 1\n"
		"  incr    bytes added per entry, default 8\n"
		"  flags   64-bit PTE flags, default 0x7\n", me);
}

int main(int argc, char **argv)
{
	struct rx550_pm4_ib ib;
	uint32_t buf[MAX_DW];
	bool gfx;
	const char *mode;
	uint32_t vmid, count = 1, incr = 8;
	uint64_t pd;
	uint64_t flags = 0x7;
	size_t i;

	if (argc < 4) {
		usage(argv[0]);
		return 2;
	}

	mode = argv[1];
	if (strcmp(mode, "gfx") == 0)
		gfx = true;
	else if (strcmp(mode, "compute") == 0)
		gfx = false;
	else if (strcmp(mode, "pteonly") == 0 ||
		 strcmp(mode, "ring-gfx") == 0 ||
		 strcmp(mode, "ring-compute") == 0)
		gfx = false;
	else {
		usage(argv[0]);
		return 2;
	}

	vmid = (uint32_t)strtoul(argv[2], NULL, 0);
	pd = strtoull(argv[3], NULL, 0);
	if (argc > 4)
		count = (uint32_t)strtoul(argv[4], NULL, 0);
	if (argc > 5)
		incr = (uint32_t)strtoul(argv[5], NULL, 0);
	if (argc > 6)
		flags = strtoull(argv[6], NULL, 0);

	memset(buf, 0, sizeof buf);
	ib.buf = buf;
	ib.size_dw = MAX_DW;
	ib.length_dw = 0;

	/* The page-table write, into the same IB. This is the point: the SDMA
	 * packet and the WRITE_DATA packets share one buffer, which is how it
	 * works on the hardware. */
	rx550_sdma_vm_set_pte_pde(&ib, 0x800000ull, 0x2000ull, count, incr, flags);

	if (strcmp(mode, "pteonly") != 0) {
		if (!rx550_vm_flush(&ib, vmid, pd, gfx)) {
			fprintf(stderr,
				"rx550pm4_emit: rx550_vm_flush refused (vmid %u)\n",
				vmid);
			return 1;
		}
	}

	/* The "ring-*" modes emit the delivery path into a SECOND buffer: the
	 * coherence packet and the INDIRECT go in ring memory, while the PTEPDE
	 * and the vm-flush went into the IB in GTT. Concatenating them into one
	 * buffer would be a lie about the memory layout, and the validator's
	 * ordering checks exist precisely because the two are separate. */
	if (strncmp(mode, "ring-", 5) == 0) {
		struct rx550_pm4_ib ring;
		uint32_t rbuf[MAX_DW];

		gfx = (strcmp(mode, "ring-gfx") == 0);
		memset(rbuf, 0, sizeof rbuf);
		ring.buf = rbuf;
		ring.size_dw = MAX_DW;
		ring.length_dw = 0;
		if (!rx550_ring_submit(&ring, 0x12345000ull, ib.length_dw, vmid, gfx)) {
			fprintf(stderr,
				"rx550pm4_emit: rx550_ring_submit refused\n");
			return 1;
		}
		for (i = 0; i < ring.length_dw; i++) {
			unsigned char b[4];

			b[0] = (unsigned char)(rbuf[i] & 0xffu);
			b[1] = (unsigned char)((rbuf[i] >> 8) & 0xffu);
			b[2] = (unsigned char)((rbuf[i] >> 16) & 0xffu);
			b[3] = (unsigned char)((rbuf[i] >> 24) & 0xffu);
			if (fwrite(b, 1, 4, stdout) != 4)
				return 1;
		}
		return 0;
	}

	for (i = 0; i < ib.length_dw; i++) {
		unsigned char b[4];

		b[0] = (unsigned char)(buf[i] & 0xffu);
		b[1] = (unsigned char)((buf[i] >> 8) & 0xffu);
		b[2] = (unsigned char)((buf[i] >> 16) & 0xffu);
		b[3] = (unsigned char)((buf[i] >> 24) & 0xffu);
		if (fwrite(b, 1, 4, stdout) != 4)
			return 1;
	}

	return 0;
}
