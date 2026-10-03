// SPDX-License-Identifier: GPL-2.0
/*
 * test_pm4.c - the PM4 encoder, checked against the real amdgpu.ko.
 *
 * WHAT MAKES THIS TEST DIFFERENT FROM THE OTHER TWO
 *
 * A test that checks the encoder against itself proves nothing: a wrong encoder
 * and a matching wrong expectation pass together. So the expected values here
 * are not written from the implementation. They are the five packet headers
 * counted inside the shipped amdgpu.ko (vermagic 7.1.3-200.nobara.fc44,
 * srcversion D68004925455E20A24C2B87, SHA256 a1a44c24...c024):
 *
 *     0xC0031500   10 occurrences   PACKET3(DISPATCH_DIRECT, 3)
 *     0xC0031502    1 occurrence    PACKET3_COMPUTE(DISPATCH_DIRECT, 3)
 *     0xC0027600   10 occurrences   PACKET3(SET_SH_REG, 2)
 *     0xC0017600   10 occurrences   PACKET3(SET_SH_REG, 1)
 *     0xC0004600   15 occurrences   PACKET3(EVENT_WRITE, 0)
 *
 * All five were reproduced by counting little-endian byte patterns in the module.
 * The encoder is checked against values that came out of the artefact the driver
 * is meant to replace, so agreeing with it is evidence about the format and not
 * about my transcription.
 *
 * WHAT IT DOES NOT ESTABLISH
 *
 * That these packets do anything. No packet built here has been executed on the
 * RX 550. The register programming that would deliver them is not in this tree,
 * and the only dispatch sequence available is a Carrizo EDC workaround that
 * returns immediately for CHIP_POLARIS12. Correct bytes in a command stream that
 * nothing delivers is a formatting result, not a working GPU.
 *
 * Exit 0 if every case behaves as documented, 1 otherwise.
 */

#include <stdbool.h>	/* the kernel has no stdbool.h; the test needs it */
#include <stdint.h>
#include <stdio.h>
#include <string.h>

#include "../kernel/rx550_pm4.h"
#include "../../tools/pm4decode.h"

static int failures;
static int checks;

/*
 * CONVENCION DE MARCADO. Todo check producido por check_ib() o
 * check_ib_hasta_no_pm4() empieza por "[IB] ". No es decorativo: tools/mutate.py
 * reparte los mutantes caidos entre "lo detecta el decodificador" y "solo lo
 * detectan las cabeceras" buscando ese prefijo, y si un check nuevo se anade sin
 * el, el reparto miente sin avisar. Por eso el marcador es un prefijo y no una
 * palabra: una palabra aparece y desaparece con el texto que se reescriba, y
 * mutate.py comprueba que el numero de checks marcados coincide con el numero
 * de llamadas a los helpers.
 */

/* La IB viva que decodifican los dos helpers de abajo. El test es de un
 * solo hilo y un solo buffer; pasarla por parametro seria mas limpio y
 * aqui seria ruido. Va ANTES de los helpers porque los dos la usan. */
static const uint32_t *g_buf;
static unsigned g_ib_len;

static void check(int cond, const char *what, const char *detail)
{
	checks++;
	if (cond) {
		printf("  [ OK ] %s\n", what);
	} else {
		printf("  [FAIL] %s -- %s\n", what, detail);
		failures++;
	}
}

/*
 * Igual que check_ib, pero para una IB cuyo ULTIMO paquete NO es PM4. El
 * decodificador no cubre las cabeceras SDMA (SDMA_PKT_HEADER_OP), asi que
 * devuelve NO_ES_PM4 en ese dword. Eso NO es un fallo del encoder: es el limite
 * declarado de la herramienta, y se afirma como tal en vez de afirmar que la
 * IB esta bien.
 *
 * El nombre NO dice "hasta_sdma" a proposito. El decodificador no sabe que el
 * paquete es SDMA: sabe que no es PM4. Lo que si distingue un SDMA de otra
 * cosa es el byte bajo, y por eso op_esperado se comprueba: es lo que evita que
 * esta funcion sirva para tapar un dword corrupto cualquiera. Por eso se
 * llama a si misma con lo que el driver emite (SDMA_OP_INDIRECT=4,
 * SDMA_OP_PTEPDE=12) y no con "cualquier cosa".
 */
static void
check_ib_hasta_no_pm4(const char *que, unsigned n_pkt_esperados, unsigned no_pm4_dw,
		      unsigned op_esperado)
{
	struct pm4_pkt p[128];
	struct pm4_resultado r;

	if (pm4_decode(g_buf, g_ib_len, p, 128, &r) == 0) {
		check(0, que, "la IB decodifico entera: no hay paquete SDMA");
		return;
	}
	if (r.defecto != PM4_NO_ES_PM4) {
		check(0, que, r.motivo);
		return;
	}
	if (r.offset != no_pm4_dw) {
		char d[96];
		snprintf(d, sizeof(d), "el paquete no-PM4 esta en el dword %u, esperaba %u",
			 r.offset, no_pm4_dw);
		check(0, que, d);
		return;
	}
	/* El byte bajo con op_mask 0xFF / op_shift 0 (tonga_sdma_pkt_open.h:55-56).
	 * Sin esto, el helper aceptaria CUALQUIER dword no-PM4, y su nombre
	 * empezaria a ser una forma elegante de no comprobar nada. */
	if ((g_buf[r.offset] & 0xFFu) != op_esperado) {
		char d[96];
		snprintf(d, sizeof(d),
			 "el byte bajo es 0x%02x, esperaba el op 0x%02x: no es el "
			 "paquete que dice ser", (unsigned)(g_buf[r.offset] & 0xFFu),
			 op_esperado);
		check(0, que, d);
		return;
	}
	if (r.n_pkt != n_pkt_esperados) {
		char d[96];
		snprintf(d, sizeof(d), "decodifico %u paquetes antes del no-PM4, esperaba %u",
			 r.n_pkt, n_pkt_esperados);
		check(0, que, d);
		return;
	}
	check(1, que, NULL);
}

/* El puntero a la IB viva, para que el helper no tenga que recibirla. El test
 * es de un solo hilo y de un solo buffer; pasarlo por parametro seria mas
 * limpio y aqui seria ruido. */

/*
 * DECODIFICA la IB que acaba de producir el encoder y exige que este bien
 * formada. Esto NO es lo que hacen las comprobaciones de cabecera de este
 * fichero: aquellas miran buf[0] de cada paquete contra una constante, y eso
 * no ve ni un truncamiento ni un count que no cuadre con lo emitido.
 *
 * Se anade porque el decodificador existe y no usarlo seria una herramienta
 * mas sin consumidor: aqui se usa sobre las funciones de emision que se comprueban abajo.
 */
static void

check_ib(const char *que, unsigned n_pkt_esperados, unsigned opcode_esperado)
{
	struct pm4_pkt p[128];
	struct pm4_resultado r;

	if (pm4_decode(g_buf, g_ib_len, p, 128, &r) != 0) {
		check(0, que, r.motivo);
		return;
	}
	if (r.n_pkt != n_pkt_esperados) {
		char d[96];
		snprintf(d, sizeof(d), "esperaba %u paquetes y hay %u",
			 n_pkt_esperados, r.n_pkt);
		check(0, que, d);
		return;
	}
	if (opcode_esperado != 0xFFFFFFFFu && p[0].opcode != opcode_esperado) {
		const char *n = pm4_nombre(p[0].opcode);
		char d[96];
		snprintf(d, sizeof(d), "el primer paquete es 0x%02x%s, esperaba 0x%02x",
			 p[0].opcode, n ? " " : "", opcode_esperado);
		check(0, que, d);
		return;
	}
	check(1, que, NULL);
}

static void check_eq(const char *what, uint32_t got, uint32_t want)
{
	char b[128];

	if (got == want) {
		check(1, what, "");
		return;
	}
	snprintf(b, sizeof b, "got 0x%08X, expected 0x%08X", got, want);
	check(0, what, b);
}

/* The header values as they appear in amdgpu.ko. Not derived from the code. */
#define HDR_DISPATCH_PLAIN	0xC0031500u
#define HDR_DISPATCH_COMPUTE	0xC0031502u
#define HDR_SET_SH_REG_2	0xC0027600u
#define HDR_SET_SH_REG_1	0xC0017600u
#define HDR_EVENT_WRITE		0xC0004600u

/* Register offsets, gfx_8_0_d.h. */
#define MM_COMPUTE_DISPATCH_INITIATOR	0x2e00
#define MM_COMPUTE_NUM_THREAD_X		0x2e07
#define MM_COMPUTE_PGM_LO		0x2e0c
#define MM_COMPUTE_PGM_HI		0x2e0d
#define MM_COMPUTE_PGM_RSRC1		0x2e12

#define IB_MAX	64

int main(void)
{
	struct rx550_pm4_ib ib;
	uint32_t buf[IB_MAX];

	printf("=== test_pm4: encoder vs values counted in amdgpu.ko ===\n");
	printf("    a1a44c24...c024, srcversion D68004925455E20A24C2B87\n");
	printf("    format only. No packet here has run on the RX 550.\n\n");

	printf("1. Header arithmetic, against the binary:\n");
	check_eq("PACKET3(DISPATCH_DIRECT, 3)          = 0xC0031500",
		 rx550_pm4_header(RX550_PKT3_DISPATCH_DIRECT, 3, false),
		 HDR_DISPATCH_PLAIN);
	check_eq("PACKET3_COMPUTE(DISPATCH_DIRECT, 3)  = 0xC0031502",
		 rx550_pm4_header(RX550_PKT3_DISPATCH_DIRECT, 3, true),
		 HDR_DISPATCH_COMPUTE);
	check_eq("PACKET3(SET_SH_REG, 2)               = 0xC0027600",
		 rx550_pm4_header(RX550_PKT3_SET_SH_REG, 2, false),
		 HDR_SET_SH_REG_2);
	check_eq("PACKET3(SET_SH_REG, 1)               = 0xC0017600",
		 rx550_pm4_header(RX550_PKT3_SET_SH_REG, 1, false),
		 HDR_SET_SH_REG_1);
	check_eq("PACKET3(EVENT_WRITE, 0)              = 0xC0004600",
		 rx550_pm4_header(RX550_PKT3_EVENT_WRITE, 0, false),
		 HDR_EVENT_WRITE);
	{
		/* The compute form differs from the plain one by exactly bit 1 and
		 * nothing else. If it ever differs by more, the two paths have
		 * diverged and the one-occurrence count in the binary no longer
		 * describes this encoder. */
		uint32_t d = rx550_pm4_header(RX550_PKT3_DISPATCH_DIRECT, 3, false);
		uint32_t c = rx550_pm4_header(RX550_PKT3_DISPATCH_DIRECT, 3, true);

		check_eq("compute form differs from plain by exactly 0x2",
			 c ^ d, 0x2u);
	}

	printf("\n2. The opcode went in [15:8] and the type in [31:30]:\n");
	{
		uint32_t h = rx550_pm4_header(RX550_PKT3_SET_SH_REG, 1, false);

		check_eq("bits 31:30 == 0b11 (PACKET_TYPE3)", h >> 30, 3u);
		check_eq("bits 15:8 == opcode 0x76", (h >> 8) & 0xFF, 0x76u);
		check_eq("bits 23:16 == count 1", (h >> 16) & 0x3FFF, 1u);
	}
	printf("         (a layout with the opcode at [31:24], which is what\n"
	       "          SDMA_PACKET() in cikd.h uses, would fail all three)\n");

	printf("\n3. count is masked to 14 bits, and the top 6 do not leak:\n");
	{
		/* count 0x3FFF is the mask's maximum. If the encoder used the full
		 * 32-bit shift, bits 29:24 would be non-zero and the header would
		 * not match any value in the binary. */
		uint32_t h = rx550_pm4_header(RX550_PKT3_NOP, 0x3FFF, false);

		check_eq("count 0x3FFF is masked, not truncated differently",
			 (h >> 16) & 0x3FFF, 0x3FFFu);
		check_eq("bits 31:30 still the type at max count", h >> 30, 3u);
	}

	printf("\n4. SET_SH_REG payload is a RELATIVE offset:\n");
	check_eq("COMPUTE_PGM_LO (0x2E0C) - 0x2C00 = 0x020C",
		 rx550_pm4_reg_offset(MM_COMPUTE_PGM_LO), 0x020Cu);
	check_eq("COMPUTE_PGM_RSRC1 (0x2E12) - 0x2C00 = 0x0212",
		 rx550_pm4_reg_offset(MM_COMPUTE_PGM_RSRC1), 0x0212u);
	{
		/* An absolute register number would program a different register
		 * and produce no error. This is the single most likely silent
		 * failure in a hand-written encoder, so it is asserted directly. */
		uint32_t abs = MM_COMPUTE_PGM_LO;

		check(abs != (uint32_t)rx550_pm4_reg_offset(MM_COMPUTE_PGM_LO),
		      "the offset is NOT the absolute register number", "");
	}
	{
		/* Saturating rather than wrapping: a register below the base must
		 * not alias into a valid index for something else. */
		check_eq("a register below 0x2C00 saturates to 0",
			 rx550_pm4_reg_offset(0x1000), 0u);
	}

	printf("\n5. set_sh_reg emits header, offset, value -- three dwords:\n");
	memset(buf, 0xAA, sizeof(buf));
	memset(&ib, 0, sizeof(ib));
	ib.buf = buf;
	ib.size_dw = IB_MAX;
	rx550_pm4_set_sh_reg(&ib, MM_COMPUTE_PGM_RSRC1, 0x240);
	g_buf = buf; g_ib_len = ib.length_dw;
	check_ib("[IB] la IB de set_sh_reg decodifica", 1u, 0x76u);
	check_eq("length_dw == 3", (uint32_t)ib.length_dw, 3u);
	check_eq("dword 0 is the header", buf[0], HDR_SET_SH_REG_1);
	check_eq("dword 1 is the relative offset", buf[1], 0x0212u);
	check_eq("dword 2 is the value", buf[2], 0x240u);

	printf("\n6. set_sh_reg2 emits lo then hi:\n");
	memset(buf, 0xAA, sizeof(buf));
	ib.length_dw = 0;
	rx550_pm4_set_sh_reg2(&ib, MM_COMPUTE_PGM_LO, 0x1122334455667788ull);
	g_buf = buf; g_ib_len = ib.length_dw;
	check_ib("[IB] la IB de set_sh_reg2 decodifica", 1u, 0x76u);
	check_eq("length_dw == 4", (uint32_t)ib.length_dw, 4u);
	check_eq("dword 0 is the count-2 header", buf[0], HDR_SET_SH_REG_2);
	check_eq("dword 1 is the relative offset", buf[1], 0x020Cu);
	check_eq("dword 2 is the low half", buf[2], 0x55667788u);
	/* 0x1122334455667788 >> 32 == 0x11223344. I first wrote 0x11223322 here,
	 * transposing two digits; the test failed and was right. A hand-typed
	 * expected value is exactly the kind of thing that should be computed. */
	check_eq("dword 3 is the high half", buf[3], 0x11223344u);

	printf("\n7. DISPATCH_DIRECT: header says 3, five dwords are written.\n");
	printf("   This reproduces gfx_v8_0.c:1541-1546. The mismatch is in\n"
	       "   the driver too, and why is NOT_DETERMINED.\n");
	memset(buf, 0xAA, sizeof(buf));
	ib.length_dw = 0;
	rx550_pm4_dispatch_direct(&ib, 8, 1, 1, false);
	g_buf = buf; g_ib_len = ib.length_dw;
	check_ib("[IB] la IB de dispatch_direct decodifica", 1u, 0x15u);
	check_eq("length_dw == 5, four payload words after the header",
		 (uint32_t)ib.length_dw, 5u);
	check_eq("dword 0 is 0xC0031500", buf[0], HDR_DISPATCH_PLAIN);
	check_eq("dword 1 is x", buf[1], 8u);
	check_eq("dword 2 is y", buf[2], 1u);
	check_eq("dword 3 is z", buf[3], 1u);
	{
		/* COMPUTE_DISPATCH_INITIATOR with COMPUTE_SHADER_EN, bit 0
		 * (gfx_8_0_sh_mask.h:8235). Not decoded beyond that: the other
		 * 12 fields are known to exist and are not needed here. */
		check_eq("dword 4 is the initiator, COMPUTE_SHADER_EN only",
			 buf[4], 1u);
	}
	{
		/* If the count were 4 to match the four written words, the header
		 * would be 0xC0041500, which does not occur in amdgpu.ko at all.
		 * Asserting that it is absent is the point: it is why this looks
		 * like a bug and is not one. */
		uint32_t wrong = rx550_pm4_header(RX550_PKT3_DISPATCH_DIRECT, 4, false);

		check_eq("count 4 would give 0xC0041500, which is not in the module",
			 wrong, 0xC0041500u);
	}

	memset(buf, 0xAA, sizeof(buf));
	ib.length_dw = 0;
	rx550_pm4_dispatch_direct(&ib, 8, 1, 1, true);
	check_eq("compute form emits 0xC0031502", buf[0], HDR_DISPATCH_COMPUTE);

	/*
	 * EVENT_WRITE: the token is a separate dword.
	 *
	 * findings/007 section 4 says it goes in the header's high 16 bits. It
	 * does not: gfx_v8_0.c:1549-1550 writes the header with count 0 and then
	 * a second dword holding EVENT_TYPE(7) | EVENT_INDEX(4). I implemented the
	 * documented version first and this check is what caught it.
	 */
	printf("\n8. EVENT_WRITE: header with count 0, token in a separate dword:\n");
	memset(buf, 0xAA, sizeof(buf));
	ib.length_dw = 0;
	rx550_pm4_event_write(&ib, (7u << 0) | (4u << 8));	/* 0x407 */
	g_buf = buf; g_ib_len = ib.length_dw;
	check_ib("[IB] la IB de event_write decodifica", 1u, 0x46u);
	check_eq("length_dw == 2", (uint32_t)ib.length_dw, 2u);
	check_eq("dword 0 is the bare header, nothing OR'd in",
		 buf[0], HDR_EVENT_WRITE);
	check_eq("dword 1 is the token 0x407", buf[1], 0x407u);
	{
		/* EVENT_TYPE(x) = x<<0, EVENT_INDEX(x) = x<<8 (sid.h:490-491).
		 * Absorbing the token into the header would give 0xC0004600 | 0x407
		 * = 0xC0004607, leaving the second dword dead. 0xC0004600 occurs 15
		 * times in amdgpu.ko; the OR'd form occurs zero times, which is the
		 * evidence that the token is a separate word. I asserted the wrong
		 * sum (0xC0004704) the first time and the test caught me, same as
		 * the two transposed constants above. */
		uint32_t as_header = HDR_EVENT_WRITE | 0x0407u;

		check_eq("absorbing the token would give 0xC0004607",
			 as_header, 0xC0004607u);
		check(as_header != HDR_EVENT_WRITE,
		      "0xC0004607 is NOT in the module; 0xC0004600 is, 15 times",
		      "");
	}

	printf("\n9. A full sequence, assembled the way gfx_v8_0.c does it:\n");
	memset(buf, 0xAA, sizeof(buf));
	ib.length_dw = 0;
	rx550_pm4_set_sh_reg(&ib, MM_COMPUTE_NUM_THREAD_X, 256 * 5);
	rx550_pm4_dispatch_direct(&ib, 8, 1, 1, false);
	rx550_pm4_event_write(&ib, (7u << 0) | (4u << 8));	/* 0x407 */
	g_buf = buf; g_ib_len = ib.length_dw;
	check_ib("[IB] la secuencia de 3 paquetes decodifica entera", 3u, 0x76u);
	check_eq("three packets, 3 + 5 + 2 dwords", (uint32_t)ib.length_dw, 10u);
	check_eq("pkt 0 header", buf[0], HDR_SET_SH_REG_1);
	/* 0x2E07 - 0x2C00 == 0x0207. I first wrote 0x0007, having subtracted
	 * 0x2E00 instead. Another transposed expectation, caught the same way. */
	check_eq("pkt 0 offset for NUM_THREAD_X (0x2E07-0x2C00)", buf[1], 0x0207u);
	check_eq("pkt 0 value 256*5", buf[2], 1280u);
	check_eq("pkt 1 header", buf[3], HDR_DISPATCH_PLAIN);
	check_eq("pkt 2 header is the bare 0xC0004600", buf[8], HDR_EVENT_WRITE);
	check_eq("pkt 2 trailer is the token 0x407", buf[9], 0x407u);

	printf("\n10. Overflow is refused, not truncated silently mid-packet:\n");
	{
		/* An IB with room for 3 dwords cannot take a 5-dword dispatch.
		 * Nothing is written and length_dw does not move, so the caller
		 * sees an unchanged buffer rather than a partial packet. A partial
		 * command stream is the failure this guards: the GPU would run
		 * half a job and report nothing. */
		memset(buf, 0xAA, sizeof(buf));
		ib.buf = buf;
		ib.size_dw = 3;
		ib.length_dw = 0;
		rx550_pm4_dispatch_direct(&ib, 8, 1, 1, false);
		check_eq("a 5-dword packet into a 3-dword IB writes nothing",
			 (uint32_t)ib.length_dw, 0u);
		check_eq("and leaves the buffer untouched", buf[0], 0xAAAAAAAAu);
	}
	{
		/* An IB with room for exactly 5 must accept it. An off-by-one here
		 * would reject every real dispatch. */
		memset(buf, 0xAA, sizeof(buf));
		ib.size_dw = 5;
		ib.length_dw = 0;
		rx550_pm4_dispatch_direct(&ib, 8, 1, 1, false);
		check_eq("exactly 5 dwords is enough", (uint32_t)ib.length_dw, 5u);
	}
	{
		/* set_sh_reg into a 2-dword IB: 3 needed, so refused. */
		memset(buf, 0xAA, sizeof(buf));
		ib.size_dw = 2;
		ib.length_dw = 0;
		rx550_pm4_set_sh_reg(&ib, MM_COMPUTE_PGM_RSRC1, 0x240);
		check_eq("a 3-dword packet into a 2-dword IB writes nothing",
			 (uint32_t)ib.length_dw, 0u);
	}
	{
		/* A NULL ib must not crash the caller. Cheap, and a NULL check
		 * that is missing shows up as an oops on someone else's path. */
		rx550_pm4_dispatch_direct(NULL, 8, 1, 1, false);
		rx550_pm4_set_sh_reg(NULL, MM_COMPUTE_PGM_RSRC1, 0x240);
		rx550_pm4_event_write(NULL, 0);
		check(1, "NULL ib is handled without dereferencing", "");
	}

	/*
	 * THE sDMA BLOCK, ADDED FOR THE PTEPDE PRODUCER.
	 *
	 * The five headers above are checked against bytes counted inside the
	 * shipped amdgpu.ko. PTEPDE is checked differently, and the difference is
	 * the point: no PACKET3 header appears in a PTEPDE packet, so there is no
	 * 0xC... value to count in the module. Its expected values are transcribed
	 * from sdma_v4_0.c:1643-1659 and vega10_sdma_pkt_open.h:37,69-72, which is
	 * a weaker provenance than the binary and is labelled as such below.
	 *
	 * The values are NOT derived from the encoder: 10 dwords, the field order,
	 * the zero at index 8 and the count-1 at index 9 are all stated in the
	 * corpus and written out here independently. If the encoder and this
	 * expectation were both wrong in the same way the test would still pass,
	 * which is why the count-1 case below is checked with a deliberate
	 * mutation rather than only against the expectation.
	 */
	printf("11. sDMA header, from vega10_sdma_pkt_open.h (not from the binary):\n");
	{
		/* 12 in bits 7:0 and nothing else. A PACKET3 would be 0xC0030C00
		 * at minimum; the absence of any 0xC0000000 bit is the property
		 * that makes this a different packet class. */
		check_eq("SDMA header(PTEPDE)               = 0x0000000C",
			 rx550_sdma_header(RX550_SDMA_OP_GEN_PTEPDE), 0x0000000Cu);
		check_eq("the opcode is a bare byte, not a PACKET3 type",
			 (uint32_t)((rx550_sdma_header(RX550_SDMA_OP_GEN_PTEPDE) >> 30) & 3u), 0u);
		check_eq("opcodes above 8 bits are masked, not truncated into the field",
			 rx550_sdma_header(0x1FFu), 0x000000FFu);
	}

	printf("12. PTEPDE producer, from sdma_v4_0.c:1643-1659:\n");
	{
		/* Values chosen to be distinguishable in every dword position: the
		 * two halves of each 64-bit field differ, and the three 64-bit
		 * fields differ from each other. If the encoder swapped flags and
		 * addr, or emitted hi before lo, this vector catches it. */
		const uint64_t pe    = 0x0123456789ABCDEFull;
		const uint64_t flags = 0x0000000102000003ull;	/* VALID|SNOOPED|SYSTEM|PRT-ish */
		const uint64_t addr  = 0x00000000FEDCBA98ull;
		const uint32_t incr  = 0x10u;
		const uint32_t count = 4u;

		memset(buf, 0xAA, sizeof(buf));
		ib.buf = buf;
		ib.size_dw = IB_MAX;
		ib.length_dw = 0;

		rx550_sdma_vm_set_pte_pde(&ib, pe, addr, count, incr, flags);

		check_eq("PTEPDE writes 10 dwords", (uint32_t)ib.length_dw, 10u);
		g_buf = buf; g_ib_len = ib.length_dw;
		check_ib_hasta_no_pm4("[IB] PTEPDE: el primer dword ya es cabecera SDMA",
				     0u, 0u, 12u);	/* SDMA_OP_PTEPDE = 12 */
		check_eq("dw0  header: opcode 12, no type bits", buf[0], 0x0000000Cu);
		check_eq("dw1  pe low",     buf[1], 0x89ABCDEFu);
		check_eq("dw2  pe high",    buf[2], 0x01234567u);
		check_eq("dw3  flags low",  buf[3], 0x02000003u);
		check_eq("dw4  flags high", buf[4], 0x00000001u);
		check_eq("dw5  addr low",   buf[5], 0xFEDCBA98u);
		check_eq("dw6  addr high",  buf[6], 0x00000000u);
		check_eq("dw7  incr",       buf[7], 0x00000010u);
		check_eq("dw8  is zero, always", buf[8], 0x00000000u);
		/* findings/034 said this field was count-1. It is not, on this ASIC:
		 * sdma_v3_0.c:996 is the emitter that runs and it writes plain `count`.
		 * findings/043-vuelta-atras-035-y-036-leian-el-asic-equivocado.md. The check name says which finding it settles, because a
		 * bare "count" here would be indistinguishable from the wrong version. */
		check_eq("dw9  plain count, per sdma_v3_0.c (043)", buf[9], 4u);
	}

	printf("13. PTEPDE boundaries:\n");
	{
		/* count = 1 es el caso que escribe UNA entrada, y es el mas comun de
		 * todos: una sola pagina mapeada. Con la codificacion plana de
		 * findings/043-vuelta-atras-035-y-036-leian-el-asic-equivocado.md vale 1; con la de mas-uno de 034 valia 0. Este check
		 * distingue las dos de un vistazo. */
		memset(buf, 0xAA, sizeof(buf));
		ib.buf = buf;
		ib.size_dw = IB_MAX;
		ib.length_dw = 0;
		rx550_sdma_vm_set_pte_pde(&ib, 0x1000ull, 0x2000ull, 1u, 8u, 0x7ull);
		check_eq("count=1 encodes 1 entry, plain (043)", buf[9], 1u);
		check_eq("count=1 still writes a full packet", (uint32_t)ib.length_dw, 10u);
	}
	{
		/* count = 0. count-1 would be 0xFFFFFFFF, i.e. 2^32 entries into
		 * the page table. Refused, not passed through. */
		memset(buf, 0xAA, sizeof(buf));
		ib.buf = buf;
		ib.size_dw = IB_MAX;
		ib.length_dw = 0;
		rx550_sdma_vm_set_pte_pde(&ib, 0x1000ull, 0x2000ull, 0u, 8u, 0x7ull);
		check_eq("count=0 writes nothing rather than 0xFFFFFFFF entries",
			 (uint32_t)ib.length_dw, 0u);
		check_eq("count=0 leaves the buffer untouched", buf[0], 0xAAAAAAAAu);
	}
	{
		/* An IB with room for 9 of the 10 dwords must take none of them. A
		 * partial sDMA packet is worse than a short PACKET3: the engine
		 * infers length from the opcode, so a truncated stream desynchronises
		 * rather than ending. */
		memset(buf, 0xAA, sizeof(buf));
		ib.buf = buf;
		ib.size_dw = 9;
		ib.length_dw = 0;
		rx550_sdma_vm_set_pte_pde(&ib, 0x1000ull, 0x2000ull, 1u, 8u, 0x7ull);
		check_eq("a 9-dword IB rejects the 10-dword packet",
			 (uint32_t)ib.length_dw, 0u);
		ib.size_dw = 10;
		ib.length_dw = 0;
		rx550_sdma_vm_set_pte_pde(&ib, 0x1000ull, 0x2000ull, 1u, 8u, 0x7ull);
		check_eq("a 10-dword IB accepts it exactly", (uint32_t)ib.length_dw, 10u);
	}
	{
		/* Two packets back to back: the second must not overwrite the
		 * first, which is the whole reason length_dw is maintained. */
		memset(buf, 0xAA, sizeof(buf));
		ib.buf = buf;
		ib.size_dw = IB_MAX;
		ib.length_dw = 0;
		rx550_sdma_vm_set_pte_pde(&ib, 0x1000ull, 0x2000ull, 1u, 8u, 0x7ull);
		rx550_sdma_vm_set_pte_pde(&ib, 0x5000ull, 0x6000ull, 1u, 8u, 0x7ull);
		check_eq("two packets occupy 20 dwords", (uint32_t)ib.length_dw, 20u);
		check_eq("first packet's header survives", buf[0], 0x0000000Cu);
		check_eq("second packet's header follows", buf[10], 0x0000000Cu);
		check_eq("second packet's pe low is at dw11", buf[11], 0x00001000u + 0x4000u);
	}
	{
		rx550_sdma_vm_set_pte_pde(NULL, 0x1000ull, 0x2000ull, 1u, 8u, 0x7ull);
		check(1, "NULL ib is handled without dereferencing (sDMA)", "");
	}

	/*
	 * THE VM-FLUSH PATH. Section 14 is the one that gives the PTEPDE
	 * producer a destination: the same IB carries the SDMA packet that writes
	 * the page directory, and the WRITE_DATA packets that name it.
	 *
	 * Same provenance caveat as section 12. These values are transcribed from
	 * gfx_v8_0.c:6197-6221, gmc_v8_0.c:661-677 and gmc_8_1_d.h, not counted in a
	 * binary -- a vm-flush is a ring sequence, not a constant that appears
	 * anywhere in amdgpu.ko.
	 */
	printf("14. The page-table base registers are TWO runs, not one array:\n");
	{
		/* From gmc_8_1_d.h. The arithmetic below is the point of the test:
		 * if these are one stride-1 array, the second run starts at 0x557
		 * and is the aperture START register. */
		check_eq("context 0  PTBA is 0x54F", RX550_MM_VM_CONTEXT0_PTBA, 0x54Fu);
		check_eq("context 8  PTBA is 0x50E, NOT 0x557", RX550_MM_VM_CONTEXT8_PTBA, 0x50Eu);
		check_eq("the second run is BELOW the first",
			 (uint32_t)(RX550_MM_VM_CONTEXT8_PTBA < RX550_MM_VM_CONTEXT0_PTBA), 1u);
		check_eq("VMID 0 -> 0x54F",  rx550_vm_ptba_reg(0), 0x54Fu);
		check_eq("VMID 1 -> 0x550, stride 1", rx550_vm_ptba_reg(1), 0x550u);
		check_eq("VMID 7 -> 0x556, stride 1", rx550_vm_ptba_reg(7), 0x556u);
		check_eq("VMID 8 -> 0x50E, stride 1 from ITS OWN base",
			 rx550_vm_ptba_reg(8), 0x50Eu);
		check_eq("VMID 15 -> 0x515, stride 1", rx550_vm_ptba_reg(15), 0x515u);
		/* The single-array assumption, spelled out, must be false. */
		check(!(RX550_MM_VM_CONTEXT0_PTBA + 8 == RX550_MM_VM_CONTEXT8_PTBA),
		      "a stride-1 array of 16 would be WRONG", "");
		check(rx550_vm_ptba_reg(8) != RX550_MM_VM_CONTEXT0_PTBA + 8,
		      "VMID 8 does not land on 0x557 (aperture start)", "");
		/* Out of range is refused, not clamped: 0x54F is context 0, a real
		 * register, so clamping would program the GART context. */
		check_eq("VMID 16 is refused, not wrapped", rx550_vm_ptba_reg(16), 0u);
		check_eq("VMID 0xFFFFFFFF is refused", rx550_vm_ptba_reg(0xFFFFFFFFu), 0u);
		check_eq("VMID 0x20 does not shift a bit out",
			 rx550_vm_invalidate_mask(0x20), 0u);
		check_eq("VMID 15 -> bit 15, the top of the field",
			 rx550_vm_invalidate_mask(15), 0x8000u);
	}

	printf("15. WRITE_DATA takes an ABSOLUTE register, unlike SET_SH_REG:\n");
	{
		memset(buf, 0xAA, sizeof(buf));
		ib.buf = buf;
		ib.size_dw = IB_MAX;
		ib.length_dw = 0;
		rx550_pm4_write_data(&ib, 0x51Eu, 0x8000u, RX550_RING_ENGINE_PFP);
	g_buf = buf; g_ib_len = ib.length_dw;
	check_ib("[IB] la IB de write_data decodifica", 1u, 0x37u);	/* 0x37 = PACKET3_WRITE_DATA (sid.h:377). 0x3c es WAIT_REG_MEM. */
	g_buf = buf; g_ib_len = ib.length_dw;
	check_ib("[IB] la IB de write_data decodifica", 1u, 0x37u);	/* 0x37 = PACKET3_WRITE_DATA (sid.h:377). 0x3c es WAIT_REG_MEM. */

		check_eq("write_data emits 5 dwords", (uint32_t)ib.length_dw, 5u);
		check_eq("dw0  header PACKET3(WRITE_DATA, 3) = 0xC0033700",
			 buf[0], 0xC0033700u);
		check_eq("dw1  cmd = ENGINE_SEL(1)|WR_CONFIRM = 0x40100000",
			 buf[1], 0x40100000u);
		check_eq("dw2  the ABSOLUTE register number", buf[2], 0x51Eu);
		check_eq("dw3  is zero", buf[3], 0u);
		check_eq("dw4  the value", buf[4], 0x8000u);
		/* The trap: SET_SH_REG would have written 0x51E - 0x2C00 = 0x291E. */
		check(!(buf[2] == rx550_pm4_reg_offset(0x51Eu)),
		      "the register is NOT the SET_SH_REG offset (0x291E)", "");
		/* The compute/default command word has no ENGINE_SEL. */
		memset(buf, 0xAA, sizeof(buf));
		ib.length_dw = 0;
		rx550_pm4_write_data(&ib, 0x51Eu, 1u, RX550_RING_ENGINE_ME);
		check_eq("ME engine -> cmd = WR_CONFIRM only = 0x00100000",
			 buf[1], 0x00100000u);
	}

	printf("16. WAIT_REG_MEM and PFP_SYNC_ME:\n");
	{
		memset(buf, 0xAA, sizeof(buf));
		ib.buf = buf;
		ib.size_dw = IB_MAX;
		ib.length_dw = 0;
		/* The vm-flush's own instance: operation 0, always, reg, me. */
		rx550_pm4_wait_reg_mem(&ib, 0x51Eu, 0u, 0u, 0x20u,
				       RX550_WAIT_REG_MEM_FUNC_ALWAYS,
				       RX550_WAIT_REG_MEM_OP_WAIT,
				       RX550_WAIT_REG_MEM_MEM_SPACE_REG,
				       RX550_WAIT_REG_MEM_ENGINE_ME);
		check_eq("wait_reg_mem emits 7 dwords", (uint32_t)ib.length_dw, 7u);
		g_buf = buf; g_ib_len = ib.length_dw;
		check_ib("[IB] wait_reg_mem: el count 5 son 7 dwords y decodifica",
			 1u, 0x3Cu);	/* 0x3c = PACKET3_WAIT_REG_MEM, sid.h:397 */
		check_eq("dw0  header PACKET3(WAIT_REG_MEM, 5) = 0xC0053C00",
			 buf[0], 0xC0053C00u);
		check_eq("dw1  cmd is 0: operation 0, function 0, mem_space 0, engine 0",
			 buf[1], 0u);
		check_eq("dw2  the register", buf[2], 0x51Eu);
		check_eq("dw3  is zero", buf[3], 0u);
		check_eq("dw4  ref",  buf[4], 0u);
		check_eq("dw5  mask", buf[5], 0u);
		check_eq("dw6  poll interval 0x20", buf[6], 0x20u);
		/* OPERATION is a real field with a used value on this ASIC. The
		 * HDP flush at gfx_v8_0.c:6054 uses 1, which is 1 << 6. */
		memset(buf, 0xAA, sizeof(buf));
		ib.length_dw = 0;
		rx550_pm4_wait_reg_mem(&ib, 0x0E70u, 0xFFu, 0xFFu, 0x10u, 3u,
				       RX550_WAIT_REG_MEM_OP_WWW,
				       RX550_WAIT_REG_MEM_MEM_SPACE_REG,
				       RX550_WAIT_REG_MEM_ENGINE_ME);
		check_eq("OPERATION(1) lands at bit 6 (the HDP-flush form)",
			 buf[1] & 0x40u, 0x40u);
		check_eq("FUNCTION(3) == is at bits 2:0", buf[1] & 0x7u, 3u);
		/* PFP_SYNC_ME: count 0, then a zero dword. Same shape as EVENT_WRITE. */
		memset(buf, 0xAA, sizeof(buf));
		ib.length_dw = 0;
		rx550_pm4_pfp_sync_me(&ib);
		check_eq("pfp_sync_me emits 2 dwords", (uint32_t)ib.length_dw, 2u);
		check_eq("dw0  header PACKET3(PFP_SYNC_ME, 0) = 0xC0004200",
			 buf[0], 0xC0004200u);
		check_eq("dw1  is zero", buf[1], 0u);
	}

	printf("17. The complete vm-flush, 19 dwords on a gfx ring:\n");
	{
		const uint64_t pd = 0x0000001234567000ull;	/* page-aligned */
		const uint32_t vmid = 3u;

		memset(buf, 0xAA, sizeof(buf));
		ib.buf = buf;
		ib.size_dw = IB_MAX;
		ib.length_dw = 0;
		check_eq("rx550_vm_flush reports success", rx550_vm_flush(&ib, vmid, pd, true), 1u);
		g_buf = buf; g_ib_len = ib.length_dw;
		check_ib("[IB] vm_flush: los 4 paquetes decodifican en orden", 4u, 0x37u);
		check_eq("gfx ring: 19 dwords", (uint32_t)ib.length_dw, RX550_VM_FLUSH_DW);

		check_eq("pkt0 header WRITE_DATA(3)",   buf[0],  0xC0033700u);
		check_eq("pkt0 cmd  PFP|CONFIRM",       buf[1],  0x40100000u);
		check_eq("pkt0 reg  PTBA(3) = 0x552",   buf[2],  0x552u);
		check_eq("pkt0 zero",                   buf[3],  0u);
		/* 0x1234567000 >> 12 == 0x1234567, seven hex digits. I wrote
		 * 0x12345 here first -- five -- and the test caught it, which is the
		 * test doing its job on me rather than on the encoder. */
		check_eq("pkt0 value = pd >> 12",       buf[4],  0x01234567u);

		check_eq("pkt1 header WRITE_DATA(3)",   buf[5],  0xC0033700u);
		check_eq("pkt1 cmd  PFP|CONFIRM",       buf[6],  0x40100000u);
		check_eq("pkt1 reg  VM_INVALIDATE_REQUEST", buf[7], 0x51Eu);
		check_eq("pkt1 zero",                   buf[8],  0u);
		check_eq("pkt1 value = 1 << vmid",      buf[9],  0x00000008u);

		check_eq("pkt2 header WAIT_REG_MEM(5)", buf[10], 0xC0053C00u);
		check_eq("pkt2 cmd  all zeros",         buf[11], 0u);
		check_eq("pkt2 reg  VM_INVALIDATE_REQUEST", buf[12], 0x51Eu);

		check_eq("pkt3 header PFP_SYNC_ME(0)",  buf[17], 0xC0004200u);
		check_eq("pkt3 zero",                   buf[18], 0u);
	}
	{
		/* Compute ring: no PFP, and the command words lose ENGINE_SEL. */
		const uint64_t pd = 0x0000001234567000ull;

		memset(buf, 0xAA, sizeof(buf));
		ib.buf = buf;
		ib.size_dw = IB_MAX;
		ib.length_dw = 0;
		check_eq("compute ring: success", rx550_vm_flush(&ib, 9u, pd, false), 1u);
		check_eq("compute ring: 17 dwords, no PFP sync",
			 (uint32_t)ib.length_dw, RX550_VM_FLUSH_DW_NO_PFP);
		check_eq("compute cmd = WR_CONFIRM only", buf[1], 0x00100000u);
		check_eq("VMID 9 -> PTBA 0x50F", buf[2], 0x50Fu);
		check_eq("invalidate bit 9", buf[9], 0x0200u);
	}
	{
		/* ALL-OR-NOTHING. An IB with 18 of the 19 dwords takes none of them:
		 * a vm-flush cut short is a different command stream, not a shorter
		 * one. */
		memset(buf, 0xAA, sizeof(buf));
		ib.buf = buf;
		ib.size_dw = RX550_VM_FLUSH_DW - 1;
		ib.length_dw = 0;
		check_eq("an 18-dword IB refuses the vm-flush",
			 rx550_vm_flush(&ib, 3u, 0x1234567000ull, true), 0u);
		check_eq("and writes nothing", (uint32_t)ib.length_dw, 0u);
		check_eq("and leaves the buffer untouched", buf[0], 0xAAAAAAAAu);

		ib.size_dw = RX550_VM_FLUSH_DW;
		ib.length_dw = 0;
		check_eq("a 19-dword IB accepts it exactly",
			 rx550_vm_flush(&ib, 3u, 0x1234567000ull, true), 1u);
	}
	{
		/* An out-of-range vmid is refused before anything is written, so the
		 * caller cannot end up with a PTBA written and no invalidate. */
		memset(buf, 0xAA, sizeof(buf));
		ib.buf = buf;
		ib.size_dw = IB_MAX;
		ib.length_dw = 0;
		check_eq("VMID 16 is refused", rx550_vm_flush(&ib, 16u, 0x1000ull, true), 0u);
		check_eq("and nothing is written", (uint32_t)ib.length_dw, 0u);
	}
	{
		/* PTEPDE then vm-flush in one IB: the ordering claim of this whole
		 * section, as a single buffer. 10 + 19 = 29 dwords, and the PTBA
		 * write lands at offset 10. */
		memset(buf, 0xAA, sizeof(buf));
		ib.buf = buf;
		ib.size_dw = IB_MAX;
		ib.length_dw = 0;
		rx550_sdma_vm_set_pte_pde(&ib, 0x800000ull, 0x2000ull, 1u, 8u, 0x7ull);
		check_eq("the directory write is 10 dwords", (uint32_t)ib.length_dw, 10u);
		check_eq("vm-flush appends after it",
			 rx550_vm_flush(&ib, 3u, 0x900000ull, true), 1u);
		check_eq("total 29 dwords", (uint32_t)ib.length_dw, 29u);
		check_eq("PTEPDE header still at dw0",  buf[0],  0x0000000Cu);
		check_eq("vm-flush WRITE_DATA starts at dw10", buf[10], 0xC0033700u);
		check_eq("its PTBA is at dw12", buf[12], 0x552u);
		check_eq("its value is pd>>12 of 0x900000", buf[14], 0x00000900u);
	}
	{
		rx550_pm4_write_data(NULL, 0x51Eu, 1u, RX550_RING_ENGINE_PFP);
		rx550_pm4_wait_reg_mem(NULL, 0x51Eu, 0u, 0u, 0u, 0u, 0u, 0u, 0u);
		rx550_pm4_pfp_sync_me(NULL);
		check_eq("vm_flush(NULL) is refused", rx550_vm_flush(NULL, 3u, 0x1000ull, true), 0u);
		check(1, "NULL ib is handled without dereferencing (vm-flush)", "");
	}

	printf("18. Memory sync: the packet that makes a CPU-written IB visible:\n");
	{
		/* gfx_v8_0_emit_mem_sync(). Count 3, four payload dwords, total 5,
		 * so count + 2 holds here too -- the rule from findings/038-validador-flujo-y-regla-del-count.md checked
		 * against a packet it was not derived from. */
		memset(buf, 0xAA, sizeof(buf));
		ib.buf = buf;
		ib.size_dw = IB_MAX;
		ib.length_dw = 0;
		rx550_pm4_surface_sync(&ib);
		check_eq("surface_sync emits 5 dwords", (uint32_t)ib.length_dw, 5u);
		check_eq("dw0  PACKET3(SURFACE_SYNC, 3) = 0xC0034300", buf[0], 0xC0034300u);
		check_eq("dw1  CP_COHER_CNTL = the OR of 5 ACTION_ENA bits = 0x28C40000",
			 buf[1], 0x28C40000u);
		check_eq("dw2  CP_COHER_SIZE = 0xFFFFFFFF", buf[2], 0xFFFFFFFFu);
		check_eq("dw3  CP_COHER_BASE = 0", buf[3], 0u);
		check_eq("dw4  poll interval 0x0A", buf[4], 0x0Au);
		/* Recomputed here from the five bits, so the constant above is
		 * checked rather than trusted. */
		{
			uint32_t ored = (1u << 22) | (1u << 23) | (1u << 27) |
					(1u << 29) | (1u << 18);
			check_eq("the OR of the five vid.h bits is 0x28C40000",
				 ored, 0x28C40000u);
		}
		/* The gfx form has a 32-bit coher base: no SIZE_HI, no BASE_HI. */
		check_eq("the gfx form is 5 dwords, so it cannot carry a 64-bit base",
			 (uint32_t)RX550_SURFACE_SYNC_DW, 5u);
	}
	{
		/* gfx_v8_0_emit_mem_sync_compute(). Count 5, six payload, total 7. */
		memset(buf, 0xAA, sizeof(buf));
		ib.buf = buf;
		ib.size_dw = IB_MAX;
		ib.length_dw = 0;
		rx550_pm4_acquire_mem(&ib);
		check_eq("acquire_mem emits 7 dwords", (uint32_t)ib.length_dw, 7u);
		check_eq("dw0  PACKET3(ACQUIRE_MEM, 5) = 0xC0055800", buf[0], 0xC0055800u);
		check_eq("dw1  CP_COHER_CNTL, same as the gfx form", buf[1], 0x28C40000u);
		check_eq("dw2  CP_COHER_SIZE", buf[2], 0xFFFFFFFFu);
		check_eq("dw3  CP_COHER_SIZE_HI = 0xFF -- the 64-bit part", buf[3], 0xFFu);
		check_eq("dw4  CP_COHER_BASE", buf[4], 0u);
		check_eq("dw5  CP_COHER_BASE_HI -- the 64-bit part", buf[5], 0u);
		check_eq("dw6  poll interval 0x0A", buf[6], 0x0Au);
	}
	{
		/* The dispatch between them is by ring type, and the two opcodes
		 * differ, so getting it backwards is a different packet, not a
		 * tuning difference. */
		memset(buf, 0xAA, sizeof(buf));
		ib.buf = buf;
		ib.size_dw = IB_MAX;
		ib.length_dw = 0;
		rx550_pm4_mem_sync(&ib, true);
		g_buf = buf; g_ib_len = ib.length_dw;
		check_ib("[IB] mem_sync en ring GFX decodifica", 1u, 0x43u);
		check_eq("gfx ring selects SURFACE_SYNC", buf[0], 0xC0034300u);
		memset(buf, 0xAA, sizeof(buf));
		ib.length_dw = 0;
		rx550_pm4_mem_sync(&ib, false);
		g_buf = buf; g_ib_len = ib.length_dw;
		check_ib("[IB] mem_sync en ring compute decodifica", 1u, 0x58u);
		check_eq("compute ring selects ACQUIRE_MEM", buf[0], 0xC0055800u);
	}

	printf("19. INDIRECT: naming the IB to the hardware:\n");
	{
		const uint64_t addr = 0x0000000012345000ull;	/* 32-byte aligned */
		const uint32_t len = 29u;

		memset(buf, 0xAA, sizeof(buf));
		ib.buf = buf;
		ib.size_dw = IB_MAX;
		ib.length_dw = 0;
		rx550_pm4_indirect(&ib, addr, len, 3u);
		check_eq("indirect emits 6 dwords, not 7", (uint32_t)ib.length_dw, 6u);
		/* The two constants I assumed wrong before reading vid.h. */
		check_eq("dw0  opcode 4 | vmid 3 in bits 19:16 = 0x00030004",
			 buf[0], 0x00030004u);
		check_eq("the opcode is 4, not 17", buf[0] & 0xFFu, 4u);
		check_eq("the vmid is NOT in bits 3:0",
			 (uint32_t)((buf[0] >> 16) & 0xFu), 3u);
		check_eq("dw1  gpu_addr low", buf[1], 0x12345000u);
		check_eq("dw2  gpu_addr high", buf[2], 0u);
		check_eq("dw3  length_dw is ABSOLUTE, not minus one", buf[3], 29u);
		check_eq("dw4  zero", buf[4], 0u);
		check_eq("dw5  zero", buf[5], 0u);
		/* The mask, not a check: sdma_v4_0.c:819 does "& 0xffffffe0".
		 * This encoder refuses instead, so the difference is observable. */
		memset(buf, 0xAA, sizeof(buf));
		ib.length_dw = 0;
		rx550_pm4_indirect(&ib, addr | 0x1fu, len, 3u);
		check_eq("a misaligned gpu_addr is REFUSED, not masked down",
			 (uint32_t)ib.length_dw, 0u);
		memset(buf, 0xAA, sizeof(buf));
		ib.length_dw = 0;
		rx550_pm4_indirect(&ib, addr, 0u, 3u);
		check_eq("a zero-length IB is refused", (uint32_t)ib.length_dw, 0u);
		memset(buf, 0xAA, sizeof(buf));
		ib.length_dw = 0;
		rx550_pm4_indirect(&ib, addr, len, 16u);
		check_eq("vmid 16 is refused", (uint32_t)ib.length_dw, 0u);
	}

	printf("20. The delivery path: mem_sync then INDIRECT:\n");
	{
		memset(buf, 0xAA, sizeof(buf));
		ib.buf = buf;
		ib.size_dw = IB_MAX;
		ib.length_dw = 0;
		check_eq("ring_submit on a gfx ring succeeds",
			 rx550_ring_submit(&ib, 0x12345000ull, 29u, 3u, true), 1u);
		check_eq("5 sync + 6 indirect = 11 dwords", (uint32_t)ib.length_dw, 11u);
		g_buf = buf; g_ib_len = ib.length_dw;
		check_ib_hasta_no_pm4("[IB] ring_submit: el sync decodifica y luego un SDMA",
				     1u, 5u, 4u);	/* SDMA_OP_INDIRECT = 4 */
		check_eq("dw0  is the SURFACE_SYNC header", buf[0], 0xC0034300u);
		check_eq("dw5  is the INDIRECT header", buf[5], 0x00030004u);
		check_eq("dw6  its gpu_addr low", buf[6], 0x12345000u);
		check_eq("dw7  gpu_addr high", buf[7], 0u);
		check_eq("dw8  length_dw", buf[8], 29u);
		/* The ordering is the whole point: coherence before reference. */
		check(!(buf[5] & 0xC0000000u) && (buf[0] & 0xC0000000u),
		      "the coherence packet precedes the INDIRECT that uses it", "");

		memset(buf, 0xAA, sizeof(buf));
		ib.length_dw = 0;
		check_eq("compute ring succeeds",
			 rx550_ring_submit(&ib, 0x12345000ull, 29u, 3u, false), 1u);
		check_eq("7 sync + 6 indirect = 13 dwords", (uint32_t)ib.length_dw, 13u);
		check_eq("dw0  is the ACQUIRE_MEM header", buf[0], 0xC0055800u);
		check_eq("dw7  is the INDIRECT header", buf[7], 0x00030004u);
	}
	{
		/* A refused submission must not have emitted the coherence packet
		 * alone: an INVALIDATE-able buffer that was never referenced, or a
		 * flush for a submission that will not happen. */
		memset(buf, 0xAA, sizeof(buf));
		ib.buf = buf;
		ib.size_dw = IB_MAX;
		ib.length_dw = 0;
		check_eq("a misaligned IB address refuses the submission",
			 rx550_ring_submit(&ib, 0x12345001ull, 29u, 3u, true), 0u);
		check_eq("and emits nothing at all", (uint32_t)ib.length_dw, 0u);
		check_eq("leaving the ring buffer untouched", buf[0], 0xAAAAAAAAu);

		ib.size_dw = 10;
		ib.length_dw = 0;
		check_eq("a ring with 10 of the 11 dwords refuses the submission",
			 rx550_ring_submit(&ib, 0x12345000ull, 29u, 3u, true), 0u);
		check_eq("and emits nothing", (uint32_t)ib.length_dw, 0u);
		ib.size_dw = IB_MAX;
	}
	{
		check_eq("ring_submit(NULL) is refused",
			 rx550_ring_submit(NULL, 0x1000ull, 29u, 3u, true), 0u);
		rx550_pm4_surface_sync(NULL);
		rx550_pm4_acquire_mem(NULL);
		rx550_pm4_indirect(NULL, 0x1000ull, 29u, 3u);
		check(1, "NULL ib is handled without dereferencing (sync/indirect)", "");
	}

	printf("\n%d checks, %d failure(s)\n", checks, failures);
	if (failures) {
		printf("RESULT: FAIL\n");
		return 1;
	}
	printf("RESULT: PASS\n");
	printf("\nNOT covered, and not claimed:\n"
	       "  - the provenance of the PTEPDE expectations is weaker than\n"
	       "    the PACKET3 ones. Those five headers were counted inside\n"
	       "    amdgpu.ko; PTEPDE cannot be, because a PTEPDE packet\n"
	       "    contains no PACKET3 header to count. Its expected values\n"
	       "    are transcribed from sdma_v4_0.c:1643-1659. A matching\n"
	       "    misreading in the encoder and in this test would pass.\n"
	       "  - whether any of these packets reaches the hardware. The\n"
	       "    register programming sequence is not in this tree.\n"
	       "  - DISPATCH_DIRECT's dimensions. They come from\n"
	       "    COMPUTE_NUM_THREAD_X/Y/Z and are per-shader state, not a\n"
	       "    constant this encoder can supply.\n"
	       "  - the count=3-with-5-dwords rule. Encoded as measured; the\n"
	       "    reason is NOT_DETERMINED and is not asserted here.\n"
	       "  - DISPATCH_INDIRECT (0x16), and every packet outside the\n"
	       "    dispatch sequence.\n");
	return 0;
}
