/* SPDX-License-Identifier: GPL-2.0-only */
/*
 * test_dummy_page.c — la pagina de relleno de la GART.
 *
 *   TARGET = RX 550 instalada en esta maquina  (1002:699F, Polaris12, GFX8)
 *   SCOPE  = EXCLUSIVO
 *
 * QUE ES Y QUE NO ES
 *   C puro, unitario, en userspace.  La HAL es una pareja de punteros a
 *   funcion inyectada, y aqui son contadores.  Ni GPU, ni DMA, ni kernel.
 *
 * POR QUE LA HAL ESTA INYECTADA
 *   Para que este test exista.  La version real usa dma_map_page_attrs(), que
 *   no se puede ejecutar fuera del kernel, y un contrato que solo se puede
 *   probar con la GPU delante no llega a probarse nunca.  Con la HAL inyectada
 *   se puede comprobar lo que de verdad importa, que es el ESTADO:  que no se
 *   mapea dos veces, que un fallo no deja un mapa a medias, y que un fini sin
 *   init no invoca a unmap.
 *
 *   El numero de llamadas a map y unmap es el oraculo.  Un test que solo
 *   comprueba el valor de salida no detectaria un mapa que se repite.
 *
 * QUE NO COMPRUEBA
 *   Que dma_map_page_attrs funcione.  Que el PA que devuelva la HAL sea el de
 *   esta pagina.  Que el hardware lo acepte.  Todo eso es RUNTIME_REQUIRED.
 */
#include <stdio.h>
#include <stdlib.h>
#include <string.h>
#include <stdint.h>
#include <stdbool.h>

#include "rx550_dummy_page.h"

static int pass, fail;

static void ok(const char *t) { printf("  PASS  %s\n", t); pass++; }
static void ko(const char *t) { printf("  FAIL  %s\n", t); fail++; }

#define CHECK(cond, name) do { if (cond) ok(name); else ko(name); } while (0)
#define CHECK_EQ(got, want, name) do {					\
	long long g_ = (long long)(got), w_ = (long long)(want);	\
	if (g_ == w_) ok(name);						\
	else { printf("  FAIL  %s  (%lld != %lld)\n", name, g_, w_);	\
	       fail++; }						\
} while (0)

/* ── LA HAL DE PRUEBA ────────────────────────────────────────────────────
 *
 *  Contadores, y un PA que se puede envenenar para simular los dos fallos
 *  que importan:  que la HAL falle, y que devuelva una direccion cero. */
struct fake_hal {
	int		map_calls;
	int		unmap_calls;
	int		map_rc;		/* != 0 hace fallar el map      */
	bool		return_zero_pa;	/* devuelve pa = 0             */
	bool		return_null_va;	/* devuelve va = NULL          */
	uint64_t	next_pa;
};

static int fk_map(void *ctx, void **out_va, uint64_t *out_pa)
{
	struct fake_hal *h = (struct fake_hal *)ctx;

	h->map_calls++;
	if (h->map_rc != 0)
		return h->map_rc;
	if (h->return_null_va)
		*out_va = NULL;
	else
		*out_va = (void *)0x1000;
	*out_pa = h->return_zero_pa ? 0 : h->next_pa;
	return 0;
}

static void fk_unmap(void *ctx, void *va, uint64_t pa)
{
	struct fake_hal *h = (struct fake_hal *)ctx;

	(void)va;
	(void)pa;
	h->unmap_calls++;
}

static struct rx550_dummy_ops ops_de(struct fake_hal *h)
{
	struct rx550_dummy_ops o;

	o.map = fk_map;
	o.unmap = fk_unmap;
	o.ctx = h;
	return o;
}

/* ──────────────────────────────────────────────────────────────────────────
 * D-NUEVO · LA GUARDA QUE FALTABA:  una PA por encima de 40 bits
 *
 * MEDIDO 2026-10-04: rx550_dummy_page_pfn() hacia `dma_pa >> 12` sin comprobar
 * nada, y el resultado truncado es un PHYSICAL_PAGE_NUMBER PLAUSIBLE Y
 * EQUIVOCADO:  no da error, no avisa, y quien lo escriba en un registro de
 * paginas no tiene forma de saber que el numero no es el que cree.  Su gemelo
 * rx550_pdb0_encode() ya rechazaba en vez de truncar (rx550_pdb0.c:18-21), y
 * el predicado rx550_pa_representable() ya existia (rx550_spaces.h:88) sin que
 * este camino lo usara.  Una guarda presente en un lado y ausente en su gemelo.
 *
 * En esta maquina el defecto es TEORICO:  la RAM acaba en 34 bits
 * (0x330000000), luego una PA por encima de 40 no existe.  Se corrige igual,
 * porque una funcion que acepta en silencio un valor que no puede representar
 * es un defecto con o sin hardware que lo alcance.
 */
static void d_pa_no_representable(void)
{
	struct rx550_dummy_page p;
	struct rx550_dummy_ops o;
	struct fake_hal h;
	struct rx550_system_pa pa;
	uint32_t pfn = UINT32_C(0xDEADBEEF);

	printf("\nD9 · PA por encima de 40 bits: se rechaza, no se trunca\n");
	memset(&p, 0, sizeof(p));
	memset(&h, 0, sizeof(h));
	o = ops_de(&h);

	/* 41 bits:  no representable. */
	h.next_pa = (UINT64_C(1) << 40) + UINT64_C(0x1000);
	memset(&pa, 0, sizeof(pa));
	CHECK(rx550_dummy_page_init(&p, &o, &pa) == 0, "D9 init con PA de 41 bits");
	CHECK(rx550_dummy_page_pfn(&p, &pfn) == RX550_DUMMY_ERR_NO_PA,
	      "D9 una PA por encima de 40 bits se RECHAZA");
	CHECK(pfn == UINT32_C(0xDEADBEEF),
	      "D9 y el destino queda intacto: no se escribe un numero plausible");
	CHECK(rx550_dummy_page_fault_reg(&p, &pfn) == RX550_DUMMY_ERR_NO_PA,
	      "D9 y fault_reg, que la envuelve, rechaza igual");

	/* El BORDE:  exactamente 2^40 NO cabe en 40 bits.  Una guarda que
	 * aceptase ese valor Would dejar fuera el final del espacio. */
	rx550_dummy_page_fini(&p);
	h.next_pa = UINT64_C(1) << 40;
	memset(&p, 0, sizeof(p));
	memset(&pa, 0, sizeof(pa));
	CHECK(rx550_dummy_page_init(&p, &o, &pa) == 0, "D9 init con PA = 2^40");
	CHECK(rx550_dummy_page_pfn(&p, &pfn) == RX550_DUMMY_ERR_NO_PA,
	      "D9 2^40 exacto TAMPOCO cabe en 40 bits");

	/* Y el ultimo valor que SI cabe, que es el que no hay que romper. */
	rx550_dummy_page_fini(&p);
	h.next_pa = (UINT64_C(1) << 40) - UINT64_C(1);
	memset(&p, 0, sizeof(p));
	memset(&pa, 0, sizeof(pa));
	CHECK(rx550_dummy_page_init(&p, &o, &pa) == 0, "D9 init con PA = 2^40-1");
	CHECK(rx550_dummy_page_pfn(&p, &pfn) == 0,
	      "D9 el ultimo valor representable SI vale");
	/*  (2^40 - 1) >> 12 == 2^28 - 1:  el numero de pagina es de 28 bits,
	 *  que es el ancho del PHYSICAL_PAGE_NUMBER.  Mi primera expectativa
	 *  decia 20, y por eso fallaba. */
	CHECK(pfn == ((UINT32_C(1) << 28) - 1),
	      "D9 y su pfn es exactamente >> 12");

	/* El caso normal, que es el de todos los dias. */
	rx550_dummy_page_fini(&p);
	h.next_pa = UINT64_C(0x12340000);
	memset(&p, 0, sizeof(p));
	memset(&pa, 0, sizeof(pa));
	CHECK(rx550_dummy_page_init(&p, &o, &pa) == 0, "D9 init con PA normal");
	CHECK(rx550_dummy_page_pfn(&p, &pfn) == 0, "D9 una PA normal vale");
	CHECK(pfn == UINT32_C(0x12340), "D9 y su pfn es >> 12");

	/* El codigo nuevo es DISTINTO de los otros tres.  Un espacio de errores
	 * donde dos codigos valen lo mismo no es un espacio de errores. */
	CHECK(RX550_DUMMY_ERR_NO_PA != RX550_DUMMY_ERR_NO_MAP, "D9 NO_PA != NO_MAP");
	CHECK(RX550_DUMMY_ERR_NO_PA != RX550_DUMMY_ERR_STATE, "D9 NO_PA != STATE");
	CHECK(RX550_DUMMY_ERR_NO_PA != RX550_DUMMY_ERR_INCONSISTENT,
	      "D9 NO_PA != INCONSISTENT");
	rx550_dummy_page_fini(&p);
}

int main(void)
{
	struct rx550_dummy_page p;
	struct rx550_dummy_ops o;
	struct fake_hal h;
	struct rx550_system_pa pa;
	uint32_t v;

	printf("test_dummy_page — la pagina de relleno de la GART\n\n");

	/* ── D1 · EL CAMINO NORMAL ──────────────────────────────────────── */
	printf("D1 · init, PA, PFN, el valor de registro, y fini\n");
	memset(&h, 0, sizeof(h));
	memset(&p, 0, sizeof(p));
	h.next_pa = UINT64_C(0x123456789);
	o = ops_de(&h);

	memset(&pa, 0xff, sizeof(pa));
	CHECK(rx550_dummy_page_init(&p, &o, &pa) == 0, "D1 init");
	CHECK_EQ(h.map_calls, 1, "D1 map llamado UNA vez");
	CHECK_EQ(h.unmap_calls, 0, "D1 y unmap todavia no");
	CHECK_EQ(p.state, RX550_DUMMY_HELD, "D1 estado HELD");
	CHECK(pa.bytes == 0x123456789, "D1 la PA devuelta es la que dio la HAL");
	CHECK_EQ(p.dma_pa, 0x123456789, "D1 y queda guardada en el objeto");

	CHECK(rx550_dummy_page_pa(&p, &pa) == 0, "D1 page_pa");
	CHECK(pa.bytes == 0x123456789, "D1 page_pa devuelve lo mismo");

	/* El registro lleva un PFN de 28 bits, NO una direccion.  Esta es la
	 * trampa de esta pieza, y la razon de que exista pfn() aparte de pa(). */
	CHECK(rx550_dummy_page_pfn(&p, &v) == 0, "D1 page_pfn");
	CHECK_EQ(v, (uint32_t)(0x123456789ULL >> 12), "D1 PFN == PA >> 12");
	CHECK(rx550_dummy_page_fault_reg(&p, &v) == 0, "D1 fault_reg");
	CHECK_EQ(v, (uint32_t)(0x123456789ULL >> 12),
		 "D1 el valor del registro es el PFN, no la direccion");
	/* Y el desplazamiento tiene que ser de 12, no de otro:  un PA >> 16
	 * tambien "cabe" en 28 bits y tambien parece plausible. */
	CHECK((uint32_t)(0x123456789ULL >> 12) != (uint32_t)(0x123456789ULL >> 16),
	      "D1 >>12 y >>16 NO dan el mismo numero: el vector distingue");

	CHECK(rx550_dummy_page_fini(&p) == 0, "D1 fini");
	CHECK_EQ(h.unmap_calls, 1, "D1 unmap llamado UNA vez");
	CHECK_EQ(p.state, RX550_DUMMY_RELEASED, "D1 estado RELEASED");
	CHECK_EQ(p.dma_pa, 0, "D1 y la PA se ha borrado");
	CHECK(p.cpu_va == NULL, "D1 y el puntero se ha borrado");

	/* ── D2 · EL DOBLE INIT ─────────────────────────────────────────── */
	printf("\nD2 · init dos veces sin fini\n");
	memset(&h, 0, sizeof(h));
	memset(&p, 0, sizeof(p));
	h.next_pa = 0x2000000;
	o = ops_de(&h);

	CHECK(rx550_dummy_page_init(&p, &o, &pa) == 0, "D2 primer init");
	CHECK_EQ(h.map_calls, 1, "D2 map una vez");
	CHECK(rx550_dummy_page_init(&p, &o, &pa) == RX550_DUMMY_ERR_STATE,
	      "D2 segundo init RECHAZADO");
	CHECK_EQ(h.map_calls, 1, "D2 y NO se ha mapeado otra vez");
	CHECK_EQ(h.unmap_calls, 0, "D2 y no se ha liberado nada");
	/* Y el primer mapa sigue vivo:  el rechazo no lo toco. */
	CHECK_EQ(p.state, RX550_DUMMY_HELD, "D2 el primer mapa sigue HELD");
	CHECK_EQ(p.dma_pa, 0x2000000, "D2 y con la misma PA");
	CHECK(rx550_dummy_page_fini(&p) == 0, "D2 fini del primero");
	CHECK_EQ(h.unmap_calls, 1, "D2 unmap exactamente una vez");

	/* ── D3 · LA HAL FALLA ──────────────────────────────────────────── */
	printf("\nD3 · la HAL falla\n");
	memset(&h, 0, sizeof(h));
	memset(&p, 0, sizeof(p));
	h.next_pa = 0x3000000;
	h.map_rc = -12;				/* -ENOMEM */
	o = ops_de(&h);
	CHECK(rx550_dummy_page_init(&p, &o, &pa) == RX550_DUMMY_ERR_NO_MAP,
	      "D3 init devuelve NO_MAP");
	CHECK_EQ(p.state, RX550_DUMMY_ABSENT, "D3 el estado sigue ABSENT");
	CHECK_EQ(p.dma_pa, 0, "D3 y no hay PA guardada");
	/* Lo que protege el mapa ahi es el ESTADO, no un segundo indicador:  si
	 * state != HELD, fini no llama a unmap.  Y eso se comprueba abajo, con el
	 * contador de unmap, que es el oraculo de verdad. */
	CHECK(rx550_dummy_page_fini(&p) == 0, "D3 un fini de mas no hace daño");
	CHECK_EQ(h.unmap_calls, 0, "D3 y no invoca a unmap: lo protege el estado");
	CHECK_EQ(h.unmap_calls, 0, "D3 y unmap no se invoco: no hay nada");

	/* Y con la HAL devolviendo PA cero o VA nulo, que son las dos formas en
	 * que un map "devuelve exito" sin tener nada. */
	memset(&h, 0, sizeof(h));
	memset(&p, 0, sizeof(p));
	h.next_pa = 0x4000000;
	h.return_zero_pa = true;
	o = ops_de(&h);
	CHECK(rx550_dummy_page_init(&p, &o, &pa) == RX550_DUMMY_ERR_NO_MAP,
	      "D3 una PA de cero no es un mapa");
	CHECK_EQ(p.state, RX550_DUMMY_ABSENT, "D3 estado ABSENT");

	memset(&h, 0, sizeof(h));
	memset(&p, 0, sizeof(p));
	h.next_pa = 0x4000000;
	h.return_null_va = true;
	o = ops_de(&h);
	CHECK(rx550_dummy_page_init(&p, &o, &pa) == RX550_DUMMY_ERR_NO_MAP,
	      "D3 un VA nulo no es un mapa");
	CHECK_EQ(p.state, RX550_DUMMY_ABSENT, "D3 estado ABSENT");

	/* ── D4 · EL FINI, Y SU IDEMPOTENCIA ────────────────────────────── */
	printf("\nD4 · fini, y fini sin nada\n");
	memset(&h, 0, sizeof(h));
	memset(&p, 0, sizeof(p));
	h.next_pa = 0x5000000;
	o = ops_de(&h);

	/* fini sobre ABSENT no invoca unmap.  remove() llama a esto tambien
	 * cuando probe() fallo antes de la pagina, y que ahi produzca un
	 * segundo fallo es como un unwind se convierte en dos. */
	CHECK(rx550_dummy_page_fini(&p) == 0, "D4 fini sobre ABSENT no falla");
	CHECK_EQ(h.unmap_calls, 0, "D4 y NO llama a unmap");
	CHECK_EQ(h.map_calls, 0, "D4 y no llama a map");

	CHECK(rx550_dummy_page_init(&p, &o, &pa) == 0, "D4 init");
	CHECK(rx550_dummy_page_fini(&p) == 0, "D4 fini");
	CHECK(rx550_dummy_page_fini(&p) == 0, "D4 fini otra vez");
	CHECK_EQ(h.unmap_calls, 1, "D4 unmap SIGUE siendo una vez");

	/* Y reusar el objeto tras un fini completo. */
	CHECK(rx550_dummy_page_init(&p, &o, &pa) == 0,
	      "D4 se puede reusar el objeto tras un fini completo");
	CHECK_EQ(h.map_calls, 2, "D4 map la segunda vez");
	CHECK_EQ(p.state, RX550_DUMMY_HELD, "D4 y vuelve a HELD");
	CHECK(rx550_dummy_page_fini(&p) == 0, "D4 fini final");
	CHECK_EQ(h.unmap_calls, 2, "D4 unmap dos veces en total, una por init");

	/* ── D5 · LOS PARAMETROS NULOS Y LAS HAL INCOMPLETAS ────────────── */
	printf("\nD5 · nulos y medias HAL\n");
	memset(&h, 0, sizeof(h));
	o = ops_de(&h);
	CHECK(rx550_dummy_page_init(NULL, &o, &pa) == RX550_DUMMY_ERR_INCONSISTENT,
	      "D5 init sin objeto");
	CHECK(rx550_dummy_page_init(&p, NULL, &pa) == RX550_DUMMY_ERR_INCONSISTENT,
	      "D5 init sin ops");
	CHECK(rx550_dummy_page_init(&p, &o, NULL) == RX550_DUMMY_ERR_INCONSISTENT,
	      "D5 init sin salida");
	CHECK_EQ(h.map_calls, 0, "D5 y no se ha llamado a map en ningun caso");

	{
		struct rx550_dummy_ops mala = o;

		mala.map = NULL;
		CHECK(rx550_dummy_page_init(&p, &mala, &pa)
		      == RX550_DUMMY_ERR_INCONSISTENT, "D5 HAL sin map");
		mala = o;
		mala.unmap = NULL;
		CHECK(rx550_dummy_page_init(&p, &mala, &pa)
		      == RX550_DUMMY_ERR_INCONSISTENT, "D5 HAL sin unmap");
	}

	CHECK_EQ(h.map_calls, 0, "D5 ninguna de esas intento mapear");

	/* Y los lectores sobre un objeto sin pagina. */
	memset(&p, 0, sizeof(p));
	CHECK(rx550_dummy_page_pa(&p, &pa) == RX550_DUMMY_ERR_STATE,
	      "D5 page_pa sin pagina");
	CHECK(rx550_dummy_page_pfn(&p, &v) == RX550_DUMMY_ERR_STATE,
	      "D5 page_pfn sin pagina");
	CHECK(rx550_dummy_page_fault_reg(&p, &v) == RX550_DUMMY_ERR_STATE,
	      "D5 fault_reg sin pagina");
	CHECK(rx550_dummy_page_pfn(&p, NULL) == RX550_DUMMY_ERR_INCONSISTENT,
	      "D5 page_pfn sin salida");
	/* Y con la salida intacta, para que el que ignore el codigo no lea un
	 * numero de la reserva. */
	v = 0xdeadbeef;
	CHECK(rx550_dummy_page_pfn(&p, &v) == RX550_DUMMY_ERR_STATE,
	      "D5 page_pfn sin pagina otra vez");
	CHECK_EQ(v, 0xdeadbeef, "D5 y la salida no se toca");

	d_pa_no_representable();

	printf("\n  %d pass, %d fail\n", pass, fail);
	if (fail) {
		printf("  CONTRATO: INCUMPLIDO\n");
		return 1;
	}
	printf("  CONTRATO: SATISFECHO\n");
	return 0;
}