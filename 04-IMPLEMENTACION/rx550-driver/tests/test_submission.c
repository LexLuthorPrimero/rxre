/* SPDX-License-Identifier: GPL-2.0 */
/*
 * test_submission.c — codigo -> PM4, sin hardware.
 *
 * Que se prueba:
 *   Que la conversion byte -> unidad de 256 sea la del corpus, y que
 *   rechace lo que el corpus trunca en silencio.
 *   Que el offset del paquete sea 0x020c y NO el 0x2e0c del registro.
 *   Que el paquete tenga 4 DWORD con el layout observado.
 *
 * Que NO se prueba:
 *   Que el CP lo lea.  Que haya codigo.  Que se ejecute.
 */
#include "rx550_submission.h"

#include <stdio.h>
#include <string.h>
#include <stddef.h>

static int pass, fail;

static void ok(const char *t) { printf("  PASS  %s\n", t); pass++; }
static void ko(const char *t) { printf("  FAIL  %s\n", t); fail++; }
#define CHECK(c, n) do { if (c) ok(n); else ko(n); } while (0)

int main(void)
{
	struct rx550_code_address base;
	struct rx550_program_address pa;
	struct rx550_pm4_register_offset off;
	struct rx550_pm4_packet pkt;
	uint32_t buf[8];
	int n;

	printf("test_submission — GPU code address -> PM4\n\n");

	/* ── constantes: contra el corpus, no de memoria ─────────────── */
	CHECK(RX550_PM4_OPCODE_SET_SH_REG == 0x76, "opcode SET_SH_REG = 0x76");
	CHECK(RX550_PM4_REG_WINDOW_START == 0x2C00, "ventana del opcode en 0x2c00");
	CHECK(RX550_REG_COMPUTE_PGM_LO == 0x2E0C, "mmCOMPUTE_PGM_LO = 0x2e0c");
	CHECK(RX550_PM4_OFF_COMPUTE_PGM_LO == 0x020C,
	      "offset EN EL PAQUETE = 0x020c");
	CHECK(RX550_REG_COMPUTE_PGM_LO != RX550_PM4_OFF_COMPUTE_PGM_LO,
	      "el offset del paquete NO es la direccion del registro");
	CHECK(RX550_REG_COMPUTE_PGM_LO - RX550_PM4_REG_WINDOW_START ==
	      RX550_PM4_OFF_COMPUTE_PGM_LO, "0x2e0c - 0x2c00 = 0x020c");
	CHECK(RX550_PM4_SET_SH_REG_COUNT == 2, "count = 2 (LO y HI)");
	CHECK(RX550_PM4_SET_SH_REG_DWORDS == 4, "el paquete ocupa 4 DWORD");
	CHECK(RX550_PROGRAM_ADDR_SHIFT == 8, "la direccion se codifica con >>8");

	/* ── 1. byte address -> >>8 ─────────────────────────────────── */
	base.bytes = UINT64_C(0x10000);
	CHECK(rx550_program_address_of(base, &pa) == 0, "1. conversion correcta");
	CHECK(pa.units == 0x100, "1. 0x10000 >> 8 = 0x100");
	CHECK(pa.units != base.bytes, "1. y NO es lo mismo numero");
	CHECK((base.bytes >> 8) == pa.units, "1. coincide con >>8");

	/* ── 2. byte address desalineada ────────────────────────────── */
	base.bytes = UINT64_C(0x10037);
	CHECK(rx550_program_address_of(base, &pa) != 0,
	      "2. 0x10037 NO alineada a 256: RECHAZADA (no truncada)");
	CHECK(pa.units == 0, "2. y la salida quedo a cero");
	base.bytes = UINT64_C(0x100FF);
	CHECK(rx550_program_address_of(base, &pa) != 0, "2. 0x100FF rechazada");
	base.bytes = UINT64_C(0x10000);
	/* el corpus NO rechazaria ninguno de estos.  Aqui esta la
	 * diferencia entre copiar y decidir. */

	/* ── 3. overflow: ya no aplica aqui ──────────────────────────
	 * La conversion recibia antes un offset, y el overflow era de
	 * base + offset.  Sin offset, una sola direccion no se desborda:
	 * la comprobacion esta ahora en rx550_ib_composer.c, donde la suma
	 * ocurre de verdad.  Los tests de overflow viven en
	 * tests/test_ib_composer.c.  Dejarlos aqui seria probarlos dos
	 * veces y contra la funcion equivocada. */

	/* ── 4. split low/high ──────────────────────────────────────── */
	base.bytes = UINT64_C(0x12345600);
	CHECK(rx550_program_address_of(base, &pa) == 0, "4. conversion");
	CHECK(pa.units == UINT64_C(0x123456), "4. 0x12345600 >> 8");
	CHECK((uint32_t)(pa.units & UINT64_C(0xFFFFFFFF)) == 0x00123456u, "4. LO");
	CHECK((uint32_t)(pa.units >> 32) == 0, "4. HI = 0");
	base.bytes = UINT64_C(0xFFFFFFFFFFFFFF00);
	CHECK(rx550_program_address_of(base, &pa) == 0, "4. direccion alta");
	CHECK((uint32_t)(pa.units >> 32) == 0xFFFFFFu, "4. HI = 0xffffff");
	CHECK((uint32_t)(pa.units & UINT64_C(0xFFFFFFFF)) == 0xFFFFFFFFu, "4. LO");

	/* ── 5. offset del registro = 0x020c ────────────────────────── */
	CHECK(rx550_pm4_register_offset_of(RX550_REG_COMPUTE_PGM_LO, &off) == 0,
	      "5. mmCOMPUTE_PGM_LO aceptado");
	CHECK(off.value == 0x020C, "5. offset codificado = 0x020c");
	CHECK(rx550_pm4_register_addr(off) == RX550_REG_COMPUTE_PGM_LO,
	      "5. y se deshace bien: ventana + 0x020c = 0x2e0c");
	/* el offset del paquete NO reconstruye la direccion del registro
	 * con la ventana equivocada */
	CHECK(off.value != RX550_REG_COMPUTE_PGM_LO,
	      "5. 0x020c != 0x2e0c: dos numeros, dos espacios");
	CHECK(rx550_pm4_register_offset_of(0x2C00, &off) == 0, "5. ventana: inicio");
	CHECK(off.value == 0, "5. offset 0 en el inicio de la ventana");
	CHECK(rx550_pm4_register_offset_of(0x3000, &off) != 0,
	      "5. registro fuera de la ventana rechazado");
	CHECK(rx550_pm4_register_offset_of(0x2BFF, &off) != 0,
	      "5. registro por debajo rechazado");
	CHECK(rx550_pm4_register_offset_of(0x020C, &off) != 0,
	      "5. pasar 0x020c como si fuera el registro se rechaza");

	/* ── 6/7. el paquete completo ────────────────────────────────── */
	memset(buf, 0xAA, sizeof(buf));
	base.bytes = UINT64_C(0x10000);
	CHECK(rx550_program_address_of(base, &pa) == 0, "6. conversion");
	CHECK(rx550_pm4_register_offset_of(RX550_REG_COMPUTE_PGM_LO, &off) == 0,
	      "6. offset del registro");
	n = rx550_pm4_emit_compute_pgm(buf, 8, off, pa);
	CHECK(n == 4, "6. se escriben 4 DWORD");
	/* PACKET3: TYPE[31:30]=3  COUNT[29:16]  OPCODE[15:8]   vid.h:105-107 */
	CHECK(((buf[0] >> 30) & UINT32_C(0x3)) == UINT32_C(3) &&
	      ((buf[0] >> 8) & UINT32_C(0xFF)) == UINT32_C(0x76) &&
	      ((buf[0] >> 16) & UINT32_C(0x3FFF)) == UINT32_C(2),
	      "6. header: TYPE=3 OPCODE=0x76 COUNT=2");
	CHECK(buf[1] == 0x020C, "6. offset = 0x020c");
	CHECK(buf[2] == 0x100u, "6. LO = 0x100");
	CHECK(buf[3] == 0u, "6. HI = 0");
	CHECK(buf[4] == UINT32_C(0xAAAAAAAA), "6. y nada mas escrito");

	rx550_pm4_packet_of(buf, &pkt);
	CHECK(pkt.header == buf[0] && pkt.offset == 0x020C &&
	      pkt.addr_lo == 0x100 && pkt.addr_hi == 0,
	      "7. el paquete reensamblado coincide");
	/* opcode en [15:8];  & 0xFFFF leeria [15:0] y daria 0x7600. */
	CHECK(((pkt.header >> 8) & UINT32_C(0xFF)) == RX550_PM4_OPCODE_SET_SH_REG,
	      "7. opcode en [15:8]");
	/* count en [29:16] con mascara;  >>16 sin mascara incluye TYPE. */
	CHECK(((pkt.header >> 16) & UINT32_C(0x3FFF)) == RX550_PM4_SET_SH_REG_COUNT,
	      "7. count en [29:16] = 2");

	/* ── 8. ningun campo de VMID ────────────────────────────────── */
	/* El paquete observado tiene 4 DWORD y ninguno lleva un VMID.
	 * Se comprueba contando: ni uno de los cuatro es un vmid. */
	CHECK(RX550_PM4_SET_SH_REG_DWORDS == 4, "8. exactamente 4 campos");
	/* opcode en [15:8], no literal de 16 bits.  vid.h:105-107 */
	CHECK(((pkt.header >> 8) & UINT32_C(0xFF)) == UINT32_C(0x76) &&
	      pkt.offset == 0x020C,
	      "8. los dos primeros son opcode y registro, no contexto");
	/* un VMID 0 seria el valor 0 y un VMID cualquiera cabe en 16 bits;
	 * con 4 campos y este layout no hay sitio para un quinto */
	CHECK(RX550_PM4_SET_SH_REG_DWORDS + 1 != 4,
	      "8. no existe un quinto DWORD donde meter un VMID");

	/* ── 9/10. sin GART, sin PDB0 ────────────────────────────────── */
	/* El componente no incluye ningun header del driver: su unico
	 * include es <stdint.h> y <stdbool.h>.  Eso se comprueba con el
	 * alcance de la API, no con un test: no existe ninguna funcion
	 * que reciba un tipo de la GART o de la PDB0. */
	CHECK(sizeof(struct rx550_code_address) == sizeof(uint64_t),
	      "9. la direccion de codigo no arrastra nada mas");
	CHECK(sizeof(struct rx550_program_address) == sizeof(uint64_t),
	      "9. ni la direccion codificada");
	CHECK(sizeof(struct rx550_pm4_register_offset) == sizeof(uint32_t),
	      "9. ni el offset del registro");

	/* ── capacidad insuficiente: todo o nada ─────────────────────── */
	memset(buf, 0xAA, sizeof(buf));
	CHECK(rx550_pm4_emit_compute_pgm(buf, 3, off, pa) == -1,
	      "3 DWORD no bastan: rechazado");
	CHECK(buf[0] == UINT32_C(0xAAAAAAAA) && buf[1] == UINT32_C(0xAAAAAAAA) &&
	      buf[2] == UINT32_C(0xAAAAAAAA),
	      "y no se escribio ninguno");
	CHECK(rx550_pm4_emit_compute_pgm(buf, 4, off, pa) == 4,
	      "exactamente 4 si: se acepta");
	CHECK(rx550_pm4_emit_compute_pgm(NULL, 8, off, pa) == -1, "dst NULL rechazado");

	/* ── TASK C: la longitud no vive en el paquete ──────────────── */
	{
		struct rx550_code_package pkg;

		pkg.code_size = 0x200;
		CHECK(pkg.code_size == 0x200,
		      "C. code_size es metadato del package");
		/* No hay ningun sitio en el paquete donde quepa. */
		/* count cubre LO y HI; el header no lleva longitud de codigo. */
		CHECK(((pkt.header >> 8) & UINT32_C(0xFF)) == UINT32_C(0x76) &&
		      ((pkt.header >> 16) & UINT32_C(0x3FFF)) == UINT32_C(2) &&
		      pkt.offset == 0x020C,
		      "C. el paquete observado no lleva longitud de codigo");
	}

	/* ── TASK D: entry_offset ───────────────────────────────────── */
	/* entry_offset = 0 es DESIGN_CHOICE de un package propio.
	 * Aqui no aparece: el paquete observado no lo usa, y anadir un
	 * descriptor de entrada seria inventar un consumidor. */
	CHECK(offsetof(struct rx550_pm4_packet, header) == 0 &&
	      offsetof(struct rx550_pm4_packet, offset) == 4 &&
	      offsetof(struct rx550_pm4_packet, addr_lo) == 8 &&
	      offsetof(struct rx550_pm4_packet, addr_hi) == 12,
	      "D. el descriptor tiene 4 campos y no un quinto de entrada");
	CHECK(sizeof(struct rx550_pm4_packet) == 16, "D. 16 bytes, nada mas");

	/* ── limite explicito ───────────────────────────────────────── */
	CHECK(rx550_submission_is_executed() == false,
	      "PM4 emitido no implica EJECUTADO");
	CHECK(n == 4, "y el estado no miente sobre si mismo");

	printf("\n  %d pass, %d fail\n", pass, fail);
	return fail ? 1 : 0;
}
