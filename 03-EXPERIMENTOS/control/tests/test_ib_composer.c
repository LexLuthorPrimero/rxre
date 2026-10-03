/* SPDX-License-Identifier: GPL-2.0 */
/*
 * test_ib_composer.c — la suma que significa algo.
 *
 * Que se prueba:
 *   Que IB_GPU_ADDRESS + CODE_OFFSET_BYTES se componga, y solo si ambos
 *   operandos son validos por separado.
 *   Que la alineacion se compruebe en los OPERANDOS y no en la suma.
 *   Que los tipos no se mezclen.
 *
 * Que NO se prueba:
 *   Que el IB exista.  Que el CP lea nada.  Que un shader se ejecute.
 */
#include "rx550_ib_composer.h"

#include <stdio.h>
#include <string.h>

static int pass, fail;

static void ok(const char *t) { printf("  PASS  %s\n", t); pass++; }
static void ko(const char *t) { printf("  FAIL  %s\n", t); fail++; }
#define CHECK(c, n) do { if (c) ok(n); else ko(n); } while (0)

#define IB_LEN	UINT64_C(0x10000)

int main(void)
{
	struct rx550_ib_gpu_address base;
	struct rx550_code_offset_bytes off;
	struct rx550_code_address code;
	uint32_t buf[32];
	uint32_t n;

	printf("test_ib_composer — IB_GPU_ADDRESS + CODE_OFFSET_BYTES\n\n");

	/* ── 8/9. IDENTIDAD DE TIPO, dentro del binario ──────────────────
	 * _Generic es una comprobacion de COMPILACION que se puede
	 * observar en un test que corre.  Si estas dos aserciones estan
	 * dentro, el binario no compilo si los tipos se hubieran
	 * mezclado.  No es decoracion: es la garantia real. */
	CHECK(_Generic(base, struct rx550_ib_gpu_address: 1, default: 0),
	      "8. el operando izquierdo es IB_GPU_ADDRESS");
	CHECK(_Generic(off, struct rx550_code_offset_bytes: 1, default: 0),
	      "9. el operando derecho es CODE_OFFSET_BYTES");
	CHECK(_Generic(code, struct rx550_code_address: 1, default: 0),
	      "9. el resultado es CODE_ADDRESS, no un uint64_t");
	CHECK(sizeof(base) == sizeof(uint64_t) &&
	      sizeof(off) == sizeof(uint64_t) &&
	      sizeof(code) == sizeof(uint64_t),
	      "9. los tres ocupan lo mismo y siguen siendo tipos distintos");

	/* ── constructores: la unica puerta de entrada ───────────────── */
	CHECK(rx550_ib_gpu_address_make(0x10000, &base) == 0, "base 0x10000 valida");
	CHECK(rx550_ib_gpu_address_make(0x10001, &base) != 0, "base desalineada rechazada");
	CHECK(base.bytes == 0, "y la salida quedo a cero");
	CHECK(rx550_code_offset_make(0x200, &off) == 0, "offset 0x200 valido");
	CHECK(rx550_code_offset_make(0x201, &off) != 0, "offset desalineado rechazado");
	(void)rx550_ib_gpu_address_make(0x10000, &base);

	/* ── 1. base + offset validos ────────────────────────────────── */
	off.bytes = 0x200;
	CHECK(rx550_ib_code_address_of(base, off, IB_LEN, &code) == 0,
	      "1. composicion valida");
	CHECK(code.bytes == 0x10200, "1. 0x10000 + 0x200 = 0x10200");
	off.bytes = 0;
	CHECK(rx550_ib_code_address_of(base, off, IB_LEN, &code) == 0,
	      "1. offset 0 aceptado");
	CHECK(code.bytes == 0x10000, "1. y da la base");

	/* ── 2. offset fuera del IB ──────────────────────────────────── */
	off.bytes = IB_LEN;
	CHECK(rx550_ib_code_address_of(base, off, IB_LEN, &code) != 0,
	      "2. offset == IB_LENGTH rechazado");
	CHECK(code.bytes == 0, "2. y la salida quedo a cero");
	off.bytes = IB_LEN + 0x100;
	CHECK(rx550_ib_code_address_of(base, off, IB_LEN, &code) != 0,
	      "2. offset mas alla del IB rechazado");
	off.bytes = IB_LEN - 0x100;
	CHECK(rx550_ib_code_address_of(base, off, IB_LEN, &code) == 0,
	      "2. el ultimo offset dentro del IB es valido");
	CHECK(rx550_ib_code_address_of(base, off, 0, &code) != 0,
	      "2. IB de longitud 0 rechazado");
	/* Un IB mas pequeno acota MAS, no menos. */
	off.bytes = 0x800;
	CHECK(rx550_ib_code_address_of(base, off, 0x800, &code) != 0,
	      "2. offset 0x800 en un IB de 0x800: en el limite, rechazado");
	CHECK(rx550_ib_code_address_of(base, off, 0xA00, &code) == 0,
	      "2. y con IB de 0xA00 si cabe");

	/* ── 3. overflow ──────────────────────────────────────────────── */
	/* base + offset por encima de UINT64_MAX. */
	{
		struct rx550_ib_gpu_address huge;

		huge.bytes = UINT64_MAX - 0xFF;	/* + 0x100 desborda */
		off.bytes = 0x100;
		CHECK(rx550_ib_code_address_of(huge, off, UINT64_MAX, &code) != 0,
		      "3. suma que desborda uint64: rechazada");
		CHECK(code.bytes == 0, "3. y NO se envuelve a un valor bajo");
		/* UINT64_MAX exacto NO esta alineado a 256, asi que se
		 * rechaza por alineacion, no por overflow.  El codigo hace
		 * bien: mi primer test daba por aceptable un valor que no
		 * lo es.  El maximo realmente aceptable es el ultimo
		 * multiple de 256 por debajo de 2^64. */
		huge.bytes = UINT64_MAX - 0xFF;
		off.bytes = 0xFF;	/* + 0xFF = UINT64_MAX exacto */
		CHECK(rx550_ib_code_address_of(huge, off, UINT64_MAX, &code) != 0,
		      "3. UINT64_MAX exacto rechazado: no esta alineado");
		huge.bytes = UINT64_MAX - 0xFF;
		off.bytes = 0x100;	/* + 0x100 = 2^64, desborda */
		CHECK(rx550_ib_code_address_of(huge, off, UINT64_MAX, &code) != 0,
		      "3. suma que llega exactamente a 2^64: rechazada");
		CHECK(code.bytes == 0, "3. y no envuelve a 0");
		{
			struct rx550_ib_gpu_address last;

			/* El mayor valor alineado cuya suma con 0x100
			 * quepa: 2^64-0x200.  El inmediatamente
			 * anterior, 2^64-0x100, ya desborda, y lo
			 * comprueba el primer CHECK de este bloque. */
			last.bytes = UINT64_MAX - UINT64_C(0x1FF);
			off.bytes = 0x100;
			CHECK(rx550_ib_code_address_of(last, off, UINT64_MAX,
						       &code) == 0,
			      "3. el mayor alineado que aun cabe se acepta");
			CHECK(code.bytes == (UINT64_MAX - UINT64_C(0x1FF)) + 0x100,
			      "3. y compone sin desbordar");
			last.bytes = UINT64_MAX - UINT64_C(0xFF);
			CHECK(rx550_ib_code_address_of(last, off, UINT64_MAX,
						       &code) != 0,
			      "3. 2^64-0x100 con offset 0x100: suma = 2^64, rechazada");
		}
	}

	/* ── 4. base desalineada ──────────────────────────────────────── */
	/* Se mete a proposito por el constructor de offset, para que el
	 * rechazo venga de la composicion y no del constructor. */
	off.bytes = 0x200;
	base.bytes = 0x10001;
	CHECK(rx550_ib_code_address_of(base, off, IB_LEN, &code) != 0,
	      "4. base desalineada rechazada");
	/* 0x10100 esta ALINEADA: su byte bajo es 0x00.  Eso no lo es. */
	base.bytes = 0x10100;
	CHECK(rx550_ib_code_address_of(base, off, IB_LEN, &code) == 0,
	      "4. 0x10100 SI esta alineada (byte bajo 0x00): se acepta");
	base.bytes = 0x10080;
	CHECK(rx550_ib_code_address_of(base, off, IB_LEN, &code) != 0,
	      "4. base 0x10080 (byte bajo 0x80): rechazada");
	base.bytes = 0x180;
	CHECK(rx550_ib_code_address_of(base, off, IB_LEN, &code) != 0,
	      "4. base 0x180: rechazada");

	/* ── 5. offset desalineado ────────────────────────────────────── */
	base.bytes = 0x10000;
	off.bytes = 0x201;
	CHECK(rx550_ib_code_address_of(base, off, IB_LEN, &code) != 0,
	      "5. offset desalineado rechazado");

	/* ── 5-bis. LA SUMA ALINEADA NO IMPLICA OPERANDOS ALINEADOS ─────
	 *
	 * 0x80 + 0x80 = 0x100, que SI esta alineada a 256.  Un
	 * compositor que comprobara solo el resultado lo aceptaria.  Esta
	 * es la razon de las dos guardas de alineacion, y por que una
	 * sola sobre la suma seria la sexta guarda muerta del proyecto. */
	base.bytes = 0x80;
	off.bytes = 0x80;
	CHECK((base.bytes + off.bytes) % RX550_PROGRAM_ADDR_UNIT == 0,
	      "5b. la SUMA 0x80+0x80=0x100 esta alineada...");
	CHECK((base.bytes % RX550_PROGRAM_ADDR_UNIT) != 0 &&
	      (off.bytes % RX550_PROGRAM_ADDR_UNIT) != 0,
	      "5b. ...pero 0x80 NO esta alineado en ninguno de los dos");
	CHECK(rx550_ib_code_address_of(base, off, IB_LEN, &code) != 0,
	      "5b. y el compositor la RECHAZA:_operandos, no suma");
	CHECK(code.bytes == 0, "5b. sin producir resultado");

	/* ── 10. offset en la ultima posicion valida ──────────────────── */
	base.bytes = 0x10000;
	off.bytes = IB_LEN - 0x100;
	CHECK(rx550_ib_code_address_of(base, off, IB_LEN, &code) == 0,
	      "10. ultimo offset valido aceptado");
	CHECK(code.bytes == 0x10000 + IB_LEN - 0x100, "10. y compuesto bien");
	off.bytes = IB_LEN;
	CHECK(rx550_ib_code_address_of(base, off, IB_LEN, &code) != 0,
	      "10. uno mas: rechazado");

	/* ── la codificacion va DESPUES, en el otro componente ─────────── */
	{
		struct rx550_program_address prog;

		base.bytes = 0x10000;
		off.bytes = 0x200;
		CHECK(rx550_ib_code_address_of(base, off, IB_LEN, &code) == 0,
		      "codificacion: composicion");
		CHECK(rx550_program_address_of(code, &prog) == 0,
		      "codificacion: program address");
		/* (0x10000 + 0x200) >> 8 = 0x102.  El orden importa: si se
		 * codificara antes, (0x10000>>8) + 0x200 = 0x100 + 0x200
		 * = 0x300, que es 3 veces mas. */
		CHECK(prog.units == 0x102, "codificacion: (base+off)>>8 = 0x102");
		CHECK(prog.units != (UINT64_C(0x100) + 0x200),
		      "codificacion: codificar antes NO daria lo mismo");
	}

	/* ── el paquete de programa ───────────────────────────────────── */
	memset(buf, 0xAA, sizeof(buf));
	base.bytes = 0x10000;
	off.bytes = 0x200;
	CHECK(rx550_composer_emit_program(buf, 32, base, off, IB_LEN, &n) == 0,
	      "SET_SH_REG emitido");
	CHECK(n == 4, "4 DWORD");
	/* PACKET3: TYPE[31:30]=3  COUNT[29:16]  OPCODE[15:8]   vid.h:105-107 */
	CHECK(((buf[0] >> 30) & UINT32_C(0x3)) == UINT32_C(3) &&
	      ((buf[0] >> 8) & UINT32_C(0xFF)) == UINT32_C(0x76) &&
	      ((buf[0] >> 16) & UINT32_C(0x3FFF)) == UINT32_C(2),
	      "TYPE=3 OPCODE=0x76 COUNT=2");
	CHECK(buf[1] == 0x020C, "offset 0x020c");
	CHECK(buf[2] == 0x102u && buf[3] == 0u, "LO=0x102 HI=0");
	memset(buf, 0xAA, sizeof(buf));
	CHECK(rx550_composer_emit_program(buf, 32, base, off, 0x100, &n) != 0,
	      "offset fuera del IB: no emite");
	CHECK(buf[0] == UINT32_C(0xAAAAAAAA), "y no escribio nada");
	CHECK(rx550_composer_emit_program(buf, 3, base, off, IB_LEN, &n) != 0,
	      "capacidad insuficiente: no emite");
	CHECK(buf[0] == UINT32_C(0xAAAAAAAA), "y sigue sin escribir");

	/* ── DISPATCH_DIRECT: count NOT_VERIFIED, se reemite tal cual ─── */
	memset(buf, 0xAA, sizeof(buf));
	{
		struct rx550_dispatch_spec d = { 8, 1, 1, true };

		CHECK(rx550_composer_emit_dispatch(buf, 32, d, &n) == 0,
		      "DISPATCH_DIRECT emitido");
		CHECK(n == 5, "5 DWORD: 1 header + 4 payload");
		CHECK(((buf[0] >> 30) & UINT32_C(0x3)) == UINT32_C(3) &&
		      ((buf[0] >> 8) & UINT32_C(0xFF)) == UINT32_C(0x15) &&
		      ((buf[0] >> 16) & UINT32_C(0x3FFF)) == UINT32_C(3),
		      "TYPE=3 OPCODE=0x15 COUNT=3 (NOT_VERIFIED, se reemite)");
		CHECK(buf[1] == 8 && buf[2] == 1 && buf[3] == 1, "x=8 y=1 z=1");
		CHECK(buf[4] == 1, "COMPUTE_SHADER_EN=1");
		CHECK(buf[5] == UINT32_C(0xAAAAAAAA), "y nada mas");
		d.shader_en = false;
		CHECK(rx550_composer_emit_dispatch(buf, 32, d, &n) == 0,
		      "con shader_en=0");
		CHECK(buf[4] == 0, "COMPUTE_SHADER_EN=0");
	}
	CHECK(rx550_composer_emit_dispatch(buf, 4, (struct rx550_dispatch_spec){ 0, 0, 0, false }, &n) != 0,
	      "4 DWORD no bastan para DISPATCH_DIRECT");

	/* ── EVENT_WRITE: se emite, no se interpreta ──────────────────── */
	memset(buf, 0xAA, sizeof(buf));
	CHECK(rx550_composer_emit_event_write(buf, 32, &n) == 0, "EVENT_WRITE emitido");
	CHECK(n == 3, "3 DWORD");
	/* COUNT=0 no discrimina un extractor erroneo: se afirma TYPE+OPCODE. */
	CHECK(((buf[0] >> 30) & UINT32_C(0x3)) == UINT32_C(3) &&
	      ((buf[0] >> 8) & UINT32_C(0xFF)) == UINT32_C(0x46),
	      "TYPE=3 OPCODE=0x46 (COUNT=0 no discriminante)");
	CHECK(buf[1] == ((7u << 8) | 4u), "EVENT_TYPE(7)|EVENT_INDEX(4), sin semantica");

	/* ── la secuencia observada, en orden ─────────────────────────── */
	{
		uint32_t used = 0;
		struct rx550_dispatch_spec d = { 8, 1, 1, true };
		uint32_t seq[32];

		memset(seq, 0, sizeof(seq));
		base.bytes = 0x10000;
		off.bytes = 0;
		CHECK(rx550_composer_emit_program(&seq[used], 32 - used, base, off,
						  IB_LEN, &n) == 0, "secuencia: programa");
		used += n;
		CHECK(rx550_composer_emit_dispatch(&seq[used], 32 - used, d, &n) == 0,
		      "secuencia: dispatch");
		used += n;
		CHECK(rx550_composer_emit_event_write(&seq[used], 32 - used, &n) == 0,
		      "secuencia: event write");
		used += n;
		CHECK(used == 4 + 5 + 3, "secuencia: 4+5+3 = 12 DWORD");
		/* Indices 0/4/9 dependen de SET_SH_REG_DWORDS=4 y DISPATCH_DWORDS=5,
		 * NO de EVENT_WRITE_DWORDS.   vid.h:105-107 */
		CHECK(((seq[0] >> 30) & UINT32_C(0x3)) == UINT32_C(3) &&
		      ((seq[0] >> 8) & UINT32_C(0xFF)) == UINT32_C(0x76) &&
		      ((seq[0] >> 16) & UINT32_C(0x3FFF)) == UINT32_C(2),
		      "secuencia[0]: TYPE=3 OPCODE=0x76 COUNT=2");
		CHECK(((seq[4] >> 30) & UINT32_C(0x3)) == UINT32_C(3) &&
		      ((seq[4] >> 8) & UINT32_C(0xFF)) == UINT32_C(0x15) &&
		      ((seq[4] >> 16) & UINT32_C(0x3FFF)) == UINT32_C(3),
		      "secuencia[4]: TYPE=3 OPCODE=0x15 COUNT=3");
		CHECK(((seq[9] >> 30) & UINT32_C(0x3)) == UINT32_C(3) &&
		      ((seq[9] >> 8) & UINT32_C(0xFF)) == UINT32_C(0x46),
		      "secuencia[9]: TYPE=3 OPCODE=0x46 (COUNT=0 no discriminante)");
	}

	/* ── limite explicito ─────────────────────────────────────────── */
	CHECK(rx550_composer_is_executed() == false,
	      "COMPOSED != EMITTED != EXECUTED");

	printf("\n  %d pass, %d fail\n", pass, fail);
	return fail ? 1 : 0;
}
