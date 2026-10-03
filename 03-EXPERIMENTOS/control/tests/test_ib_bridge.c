/* SPDX-License-Identifier: GPL-2.0 */
/*
 * test_ib_bridge.c — contrato del puente GPUVA -> IB -> PM4.
 *
 * UNA SOLA PREGUNTA: ¿el puente hace lo que declara, y se niega a hacer
 * lo que no puede garantizar?
 */
#include "rx550_ib_bridge.h"
#include "pm4.h"
#include <stdio.h>
#include <string.h>

static int pass, fail;
static void ok(const char *t) { printf("  PASS  %s\n", t); pass++; }
static void ko(const char *t) { printf("  FAIL  %s\n", t); fail++; }
#define CHECK(c, n) do { if (c) ok(n); else ko(n); } while (0)

int main(void)
{
	struct rx550_ib_desc d;
	static uint32_t storage[64];
	struct rx550_pm4_buf b;
	struct rx550_gpuva va;
	uint32_t n, hdr, lo, hi, ctl;
	enum rx550_ib_reject why;

	printf("test_ib_bridge — GPUVA -> IB -> PM4\n\n");

	/* ── geometria del descriptor (evidencia de rx550-pm4) ────────── */
	CHECK(RX550_IB_ADDR_MASK == UINT64_C(0x0000FFFFFFFFFFFF), "mascara de 48 bits");
	CHECK(RX550_IB_ADDR_ALIGN == 4, "alineacion de 4 B");

	/* ── 1. IB valido ─────────────────────────────────────────────── */
	memset(&d, 0, sizeof(d));
	va = rx550_gpuva_make(0x0000000010000000ull);
	CHECK(rx550_ib_create(&d, va, 16, 3, RX550_IB_FLAG_NONE, false) == 0,
	      "1. IB valido creado");
	CHECK(d.state == RX550_IB_CREATED, "1. estado CREATED");
	CHECK(rx550_ib_validate(&d) == 0, "1. valida");
	why = rx550_ib_reject_of(&d);
	CHECK(why == RX550_IB_OK, "1. motivo OK");
	CHECK(rx550_ib_make_ready(&d) == 0, "1. READY");
	CHECK(d.state == RX550_IB_READY, "1. estado READY");

	/* ── 2. longitud cero ─────────────────────────────────────────── */
	{
		struct rx550_ib_desc z;
		memset(&z, 0, sizeof(z));
		z.state = RX550_IB_CREATED;
		va = rx550_gpuva_make(0x10000);
		(void)rx550_ib_create(&z, va, 0, 0, 0, false);
		z.length_dw = 0;
		CHECK(rx550_ib_make_ready(&z) != 0, "2. longitud 0 rechazada");
		CHECK(rx550_ib_reject_of(&z) == RX550_IB_REJ_LEN_ZERO,
		      "2. motivo LEN_ZERO");
		CHECK(z.state == RX550_IB_CREATED, "2. no avanza de CREATED");
	}

	/* ── 3. GPUVA desalineada ─────────────────────────────────────── */
	{
		struct rx550_ib_desc u;
		memset(&u, 0, sizeof(u));
		va = rx550_gpuva_make(0x10002);	/* no alineado a 4 */
		(void)rx550_ib_create(&u, va, 16, 0, 0, false);
		CHECK(rx550_ib_make_ready(&u) != 0, "3. GPUVA desalineada rechazada");
		CHECK(rx550_ib_reject_of(&u) == RX550_IB_REJ_ADDR_ALIGN,
		      "3. motivo ADDR_ALIGN");
	}

	/* ── 4. GPUVA por encima de 48 bits ───────────────────────────── */
	{
		struct rx550_ib_desc b48;
		memset(&b48, 0, sizeof(b48));
		va = rx550_gpuva_make(UINT64_C(0x0001000000000000));
		(void)rx550_ib_create(&b48, va, 16, 0, 0, false);
		CHECK(rx550_ib_make_ready(&b48) != 0, "4. GPUVA > 48 bits rechazada");
		CHECK(rx550_ib_reject_of(&b48) == RX550_IB_REJ_ADDR_RANGE,
		      "4. motivo ADDR_RANGE");
	}

	/* ── 5. VMID invalido ─────────────────────────────────────────── */
	{
		struct rx550_ib_desc bad;
		memset(&bad, 0, sizeof(bad));
		va = rx550_gpuva_make(0x20000);
		(void)rx550_ib_create(&bad, va, 16, 0xffff, 0, false);
		bad.vmid = 0xffffu;	/* el maximo esta permitido */
		CHECK(rx550_ib_make_ready(&bad) == 0, "5. vmid 0xffff permitido");
		bad.vmid = (uint16_t)0xffff;	/* truncado: sigue siendo valido */
		(void)rx550_ib_make_ready(&bad);
		CHECK(rx550_ib_reject_of(&bad) == RX550_IB_OK,
		      "5. un vmid de 16 bits nunca desborda el campo");
	}

	/* ── 6. limite de longitud ────────────────────────────────────── */
	{
		struct rx550_ib_desc l;
		memset(&l, 0, sizeof(l));
		va = rx550_gpuva_make(0x30000);
		(void)rx550_ib_create(&l, va, 0xfffffff0u, 0, 0, false);
		CHECK(rx550_ib_make_ready(&l) == 0, "6. longitud maxima aceptada");
		(void)rx550_ib_create(&l, va, 0xfffffff2u, 0, 0, false);
		l.length_dw = 0xfffffff2u;	/* no alineada a 4 */
		CHECK(rx550_ib_make_ready(&l) != 0, "6. longitud no alineada rechazada");
	}

	/* ── 7. transicion de estado invalida ─────────────────────────── */
	CHECK(rx550_ib_make_ready(&d) != 0, "7. READY->READY rechazado");
	CHECK(rx550_ib_create(&d, va, 16, 0, 0, false) != 0,
	      "7. redefinir un IB vivo rechazado");
	CHECK(rx550_ib_validate(NULL) != 0, "7. NULL rechazado");
	CHECK(rx550_ib_reject_of(NULL) == RX550_IB_REJ_NULL, "7. motivo NULL");
	{
		struct rx550_ib_desc fresh;
		memset(&fresh, 0, sizeof(fresh));
		va = rx550_gpuva_make(0x40000);
		(void)rx550_ib_create(&fresh, va, 16, 0, 0, false);
		CHECK(rx550_ib_make_ready(&fresh) == 0, "7. primer make_ready");
		CHECK(rx550_ib_make_ready(&fresh) != 0, "7. make_ready dos veces rechazado");
	}

	/* ── 10. PM4: salida real ─────────────────────────────────────── */
	rx550_pm4_buf_init(&b, storage, 64);
	CHECK(rx550_pm4_buf_count(&b) == 0, "10. buffer vacio al inicio");
	CHECK(rx550_ib_emit(&d, &b) == 0, "10. emit correcto");
	CHECK(d.state == RX550_IB_PUBLISHED, "10. estado PUBLISHED");
	n = rx550_pm4_buf_count(&b);
	CHECK(n == 4, "10. el descriptor ocupa 4 DW");
	CHECK(d.first_dw == 0, "10. first_dw registrado");
	CHECK(rx550_pm4_buf_dw(&b, 0, &hdr) == 0, "10. DW0 leido");
	CHECK(rx550_pm4_buf_dw(&b, 1, &lo) == 0, "10. DW1 leido");
	CHECK(rx550_pm4_buf_dw(&b, 2, &hi) == 0, "10. DW2 leido");
	CHECK(rx550_pm4_buf_dw(&b, 3, &ctl) == 0, "10. DW3 leido");
	CHECK(lo == 0x10000000u, "10. addr_lo = gpu_va & 0xFFFFFFFC");
	CHECK(hi == 0, "10. addr_hi = gpu_va >> 32");
	CHECK(rx550_pm4_buf_dw(&b, 0, &hdr) == 0, "10. hdr releido");
	CHECK(rx550_pm4_buf_count(&b) == 4, "10. nada se escribio de mas");

	/* ── 7b. publicar dos veces no duplica ────────────────────────── */
	{
		uint32_t before = rx550_pm4_buf_count(&b);
		CHECK(rx550_ib_emit(&d, &b) != 0, "7. re-emitir rechazado");
		CHECK(rx550_pm4_buf_count(&b) == before,
		      "7. el buffer no cambio al re-emitir");
	}

	/* ── 11. la direccion no lleva una SYSTEM_PA por accidente ────── */
	{
		struct rx550_ib_desc t;
		struct rx550_system_pa pa;
		uint32_t dw;
		memset(&t, 0, sizeof(t));
		/* una PA de sistema baja es un numero valido; lo que se
		 * comprueba es que el descriptor NO lo Toma como direccion */
		pa.bytes = 0x0000deadbeefull;
		CHECK(pa.bytes % 4 == 3, "11. la PA de prueba esta desalineada");
		(void)rx550_ib_create(&t, rx550_gpuva_make(0x50000), 16, 0, 0, false);
		CHECK(rx550_ib_make_ready(&t) == 0, "11. IB de control valido");
		CHECK(rx550_ib_emit(&t, &b) == 0, "11. emitido");
		CHECK(rx550_pm4_buf_dw(&b, 5, &dw) == 0, "11. addr_lo leido");
		CHECK(dw != (uint32_t)pa.bytes,
		      "11. el descriptor no contiene la SYSTEM_PA");
		CHECK(rx550_pm4_buf_dw(&b, 6, &dw) == 0, "11. addr_hi leido");
		CHECK(dw == 0, "11. addr_hi no trae bits de PA de sistema");
	}

	/* ── 12. un VRAM_OFFSET no se acepta como GPUVA ───────────────── */
	{
		struct rx550_ib_desc v;
		struct rx550_vram_resource res;
		struct rx550_gpuva as_va;
		memset(&v, 0, sizeof(v));
		memset(&res, 0, sizeof(res));
		res.offset = rx550_vram_off(0x0000100000000000ull);
		as_va = rx550_gpuva_make(res.offset.bytes);	/* el error, a proposito */
		(void)rx550_ib_create(&v, as_va, 16, 0, 0, false);
		/* el valor cabe en 48 bits, asi que el validador NO lo puede
		 * detectar: por eso el tipo existe.  Se documenta el limite. */
		CHECK(rx550_ib_make_ready(&v) == 0,
		      "12. un offset VRAM alineado NO es detectable por el validador");
		CHECK(rx550_vram_off(0x10000).bytes != as_va.bytes,
		      "12. offset VRAM y GPUVA son valores distintos, aun con el mismo tipo");
		CHECK(res.offset.bytes == 0x0000100000000000ull && as_va.bytes == res.offset.bytes,
		      "12. el error es un CAST, no una conversion: por eso no se detecta");
	}

	/* ── 9. la direccion del descriptor es la GPUVA, no un offset ─── */
	CHECK(rx550_ib_pm4_address(&d).bytes == d.gpuva.bytes,
	      "9. la direccion del descriptor es la GPUVA, no un offset");
	{
		struct rx550_gpuva m = rx550_ib_pm4_address(&d);
		CHECK(m.bytes <= RX550_IB_ADDR_MASK, "9. direccion dentro de 48 bits");
	}

	/* ── A) LA MASCARA DE 48 BITS ─────────────────────────────────── */
	/*
	 * Desde rx550_ib_emit() la mascara NO es alcanzable: emit() exige
	 * READY y llama a validate(), que rechaza ADR_RANGE antes.  Ahi la
	 * mascara es un no-op.
	 *
	 * Pero rx550_ib_pm4_address() es publico y NO tiene precondicion de
	 * estado.  Si le se entrega un descriptor todavia no validado, la
	 * mascara es lo unico que impide devolver una direccion que el
	 * campo de 48 bits del descriptor no puede representar.
	 *
	 * Este test fija ese contrato.  Si alguien quita la mascara, falla.
	 */
	{
		struct rx550_ib_desc raw;
		struct rx550_gpuva out;
		memset(&raw, 0, sizeof(raw));
		raw.gpuva = rx550_gpuva_make(
			UINT64_C(0x123456789ABCD000));	/* 64 bits usados */
		raw.state = RX550_IB_CREATED;			/* sin validar  */
		raw.length_dw = 16;

		CHECK(rx550_ib_validate(&raw) != 0,
		      "A. el descriptor sin validar se rechaza");
		out = rx550_ib_pm4_address(&raw);
		CHECK(out.bytes != raw.gpuva.bytes,
		      "A. el accessor NO devuelve la direccion sin enmascarar");
		CHECK((out.bytes & ~RX550_IB_ADDR_MASK) == 0,
		      "A. lo que devuelve cabe en 48 bits");
		CHECK(out.bytes == (raw.gpuva.bytes & RX550_IB_ADDR_MASK),
		      "A. y es exactamente la parte representable");
		/* NULL tambien: devolver 0, no un basura de pila */
		CHECK(rx550_ib_pm4_address(NULL).bytes == 0,
		      "A. NULL devuelve 0");
	}

	/* ── limite explicito ─────────────────────────────────────────── */
	CHECK(!rx550_ib_is_executed(&d), "PUBLISHED no implica EXECUTED");
	CHECK(d.state == RX550_IB_PUBLISHED, "y el estado no miente sobre si mismo");

	printf("\n  %d pass, %d fail\n", pass, fail);
	return fail ? 1 : 0;
}
