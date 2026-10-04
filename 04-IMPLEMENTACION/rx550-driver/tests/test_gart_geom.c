/* SPDX-License-Identifier: GPL-2.0 */
/*
 * test_gart_geom.c — el PRODUCTOR de la geometria del GART.
 *
 * UNA SOLA PREGUNTA: ¿la aritmetica pura reproduce el GART que el driver de
 * referencia imprimio en ESTA tarjeta?
 *
 * Que NO prueba
 *   Que el hardware obedezca.  Que mmMC_VM_FB_LOCATION valga 0xF400000000 ni
 *   que mmCONFIG_MEMSIZE valga 2048.  Eso es RUNTIME_REQUIRED y no se puede
 *   hacer sin takeover.
 *
 * POR QUE EL VECTOR PRINCIPAL NO ES UNA EXPECTATIVA INVENTADA
 *   El kernel logueo "GART: 256M 0x000000FF00000000 - 0x000000FF0FFFFFFF" en
 *   esta maquina.  Ese numero es una MEDIDA.  Que nueve expresiones puras, con
 *   constantes tomadas de gmc_v8_0.c:1133 y gmc_v8_0.c:595, lo reproduzcan
 *   desde dos entradas de hardware es una corroboracion fuerte de las dos
 *   cosas: de la aritmetica Y de las constantes.  Si las constantes fueran
 *   inventadas, saldria otro numero.
 *
 *   Y es lo que hace que RX550_GART_START = 0 (nuestra DESIGN_CHOICE) NO sea
 *   lo que hace el hardware por defecto: BEST_FIT en esta geometria elige la
 *   rama ALTA.  El test lo comprueba explicitamente para que nadie lo lea al
 *   reves.
 */
#include "rx550_gart_geom.h"
#include <stdio.h>
#include <string.h>

static int pass, fail;
static void ok(const char *t) { printf("  PASS  %s\n", t); pass++; }
static void ko(const char *t) { printf("  FAIL  %s\n", t); fail++; }
#define CHECK(c, n) do { if (c) ok(n); else ko(n); } while (0)

/* El GART que el driver de referencia imprimio en esta tarjeta.  MEDIDO. */
#define MEDIDO_START  UINT64_C(0x000000FF00000000)
#define MEDIDO_END    UINT64_C(0x000000FF0FFFFFFF)
#define MEDIDO_MIB    UINT64_C(256)

/* La entrada de esta tarjeta, tal como la resolverian los dos registros. */
#define ESTA_FB_BASE  RX550_GART_GEOM_ESTA_TARJETA_FB_BASE
#define ESTA_VRAM     RX550_GART_GEOM_ESTA_TARJETA_VRAM

static int calc(uint64_t fb, uint64_t vram, uint64_t gsize,
		enum rx550_gart_placement pl, struct rx550_gart_geom *g)
{
	struct rx550_gart_geom_in in;

	memset(&in, 0, sizeof(in));
	in.fb_base    = fb;
	in.vram_bytes = vram;
	in.gart_size  = gsize;
	in.placement  = pl;
	memset(g, 0, sizeof(*g));
	return rx550_gart_geometry(&in, g);
}

/* ───────────────────────────────────────────────────────────���───────────── */
static void fase_constantes(void)
{
	struct rx550_gart_geom g;

	printf("constantes\n");

	/* mc_mask de gmc_v8_0.c:1133 con el comentario "40 bit MC". */
	CHECK(RX550_MC_MASK == UINT64_C(0x000000FFFFFFFFFF),
	      "mc_mask = 0xFFFFFFFFFF (gmc_v8_0.c:1133)");
	CHECK(RX550_MC_MASK == ((UINT64_C(1) << RX550_PA_BITS) - 1),
	      "mc_mask coincide con RX550_PA_BITS: una sola autoridad para los 40 bits");

	/* four_gb de amdgpu_gmc.c:42. */
	CHECK(RX550_GART_FOUR_GB == UINT64_C(0x100000000),
	      "four_gb = 4 GiB (amdgpu_gmc.c:42)");
	CHECK(RX550_GART_FOUR_GB == RX550_GART_ALIGN,
	      "el productor usa RX550_GART_ALIGN, la otra declaracion esta libre");

	/* gart_size de POLARIS12, gmc_v8_0.c:595. */
	CHECK(ESTA_VRAM == (UINT64_C(2048) << 20), "VRAM de la tarjeta = 2048 MiB");
	CHECK(MEDIDO_MIB == (UINT64_C(256) << 20) >> 20,
	      "GART de la tarjeta = 256 MiB (gmc_v8_0.c:595)");

	/* El limite de PHYSICAL_PAGE_NUMBER.  El productor lo declara por su
	 * cuenta para no depender del accessor; estas dos aserciones son las
	 * que ligan las dos declaraciones del mismo limite. */
	CHECK(RX550_GART_GEOM_PN_MAX == UINT64_C(0x0FFFFFFF),
	      "PHYSICAL_PAGE_NUMBER = 28 bits");
	CHECK(((MEDIDO_END >> RX550_PAGE_SHIFT) & ~RX550_GART_GEOM_PN_MAX) == 0,
	      "el GART MEDIDO cabe entero en PHYSICAL_PAGE_NUMBER");

	/* El min() de amdgpu_gmc.c:299 se queda con mc_mask en esta tarjeta. */
	CHECK(RX550_GMC_HOLE_START - 1 > RX550_MC_MASK,
	      "el hueco esta por encima de 40 bits: el min se queda con mc_mask");
	CHECK(calc(ESTA_FB_BASE, ESTA_VRAM, MEDIDO_MIB << 20,
		   RX550_GART_PLACEMENT_BEST_FIT, &g) == 0,
	      "la geometria de la tarjeta se calcula sin error");
	CHECK(g.max_mc_address == RX550_MC_MASK,
	      "y max_mc_address sale como mc_mask, no como el hueco");
}

/* ── el vector que decide ───────────────────────────────────────────────── */
static void fase_medido(void)
{
	struct rx550_gart_geom g;
	int rc;

	printf("el numero medido\n");

	rc = calc(ESTA_FB_BASE, ESTA_VRAM, MEDIDO_MIB << 20,
		  RX550_GART_PLACEMENT_BEST_FIT, &g);

	CHECK(rc == RX550_GART_GEOM_OK, "BEST_FIT sobre la geometria de la tarjeta: OK");
	CHECK(g.gart_start == MEDIDO_START,
	      "gart_start reproduce el 0xFF00000000 MEDIDO en el log del kernel");
	CHECK(g.gart_end == MEDIDO_END,
	      "gart_end reproduce el 0xFF0FFFFFFF MEDIDO en el log del kernel");
	CHECK(g.gart_size_effective == (MEDIDO_MIB << 20), "tamano efectivo = 256 MiB");
	CHECK(!g.clamped, "no hubo clamp: el GART pedido cabia");

	/* Los derivados, que son el sujeto de los vectores de borde. */
	CHECK(g.fb_end == UINT64_C(0xF47FFFFFFF), "fb_end = fb_base + vram - 1");
	CHECK(g.size_below == UINT64_C(0xF400000000), "hueco de ABAJO = fb_base");
	CHECK(g.size_above == UINT64_C(0x0B00000000), "hueco de ARRIBA = 44 GiB");

	/* El dato que hace el GART arriba y no abajo: BEST_FIT elige la rama
	 * ALTA porque el hueco de abajo es el MAS GRANDE, no el mas pequeno.
	 * Si alguien "simplifica" el criterio, esta asercion cae. */
	CHECK(g.size_below > g.size_above,
	      "el hueco de abajo es mayor: BEST_FIT no puede elegirlo por mejor ajuste");

	/* LA DIVERGENCIA QUE NOS AFECTA.  Nuestra DESIGN_CHOICE pone el GART en
	 * 0; el hardware por defecto lo pone en 0xFF00000000.  Ninguno de los
	 * dos numeros es el del otro, y el componente tiene que saber cual usa. */
	{
		struct rx550_gart_geom lo;

		CHECK(calc(ESTA_FB_BASE, ESTA_VRAM, MEDIDO_MIB << 20,
			   RX550_GART_PLACEMENT_LOW, &lo) == 0,
		      "LOW sobre la misma geometria: OK");
		CHECK(lo.gart_start == 0,
		      "LOW da gart_start = 0, que es nuestra DESIGN_CHOICE");
		CHECK(RX550_GART_START == 0, "y coincide con RX550_GART_START");
		CHECK(lo.gart_start != g.gart_start,
		      "…pero NO es lo que hace el hardware por defecto");
	}

	/* LA DIVERGENCIA D2, y por que es estructuralmente inalcanzable.
	 *
	 * El corpus usa ALIGN(fb_end) sin +1 en la rama LOW, y eso solaparia UN
	 * BYTE con la VRAM cuando fb_end fuese multiplo exacto de 4 GiB, porque
	 * ALIGN de un multiplo devuelve el multiplo y el GART empezaria en el
	 * ultimo byte de la VRAM.
	 *
	 * Con las ENTRADAS que este productor acepta, eso no puede pasar:
	 *   fb_base es multiplo de 16 MiB   (comprobado: RX550_FB_BASE_ALIGN)
	 *   vram_bytes es multiplo de 1 MiB (viene de mmCONFIG_MEMSIZE << 20)
	 * luego  fb_end + 1 = fb_base + vram  es multiplo de 1 MiB, y por tanto
	 *       fb_end  ≡  -1  (mod 1 MiB)
	 * luego  fb_end  ≡  4 GiB - 1  (mod 4 GiB),  que NUNCA es 0.
	 *
	 * Y ALIGN(fb_end) == ALIGN(fb_end+1) para todo ese conjunto, porque
	 * ninguno de los dos cruza un multiple de 4 GiB.
	 *
	 * ESTO ES LO QUE SE COMPRUEBA.  Un test que no puede discriminar entre
	 * las dos versiones no es un test debil: es la prueba de que el
	 * defecto del corpus no tiene acceso desde aqui. */
	CHECK(RX550_FB_BASE_ALIGN == (UINT64_C(16) << 20),
	      "fb_base es multiplo de 16 MiB por construccion del registro");
	{
		struct rx550_gart_geom d;
		uint64_t fb, vram;
		unsigned k;
		int difieren = 0;

		/* El caso de borde exacto: fb_end = 4 GiB*k - 1, que es lo mas
		 * cerca del multiple que la validacion permite. */
		for (k = 1; k <= 64; k <<= 1) {
			uint64_t tope = (uint64_t)k << 32;

			fb = UINT64_C(0x10000000);			/* 256 MiB */
			vram = tope - fb - UINT64_C(0);		/* fb_end = tope-1 */
			if (fb % RX550_FB_BASE_ALIGN != 0)
				continue;
			if (calc(fb, vram, UINT64_C(8) << 30,
				 RX550_GART_PLACEMENT_LOW, &d) != 0)
				continue;
			if (d.gart_start != ((uint64_t)k << 32))
				difieren++;
			CHECK((d.fb_end % RX550_GART_FOUR_GB) ==
			      (RX550_GART_FOUR_GB - 1),
			      "fb_end cae SIEMPRE en 4 GiB-1, nunca en un multiple");
		}
		CHECK(difieren == 0,
		      "y con ese borde, ALIGN(fb_end) y ALIGN(fb_end+1) coinciden");
		/* El residuo, escrito: el unico caso en que divergirian es
		 * fb_end multiplo de 4 GiB, y la entrada lo prohibe. */
		CHECK(1, "D2 es inalcanzable con las entradas validadas: no hace "
		      "falta test que lo dispare porque no puede dispararse");
	}
}

/* ── bordes ─────────────────────────────────────────────────────────────── */
static void fase_bordes(void)
{
	struct rx550_gart_geom g;

	printf("bordes\n");

	CHECK(calc(ESTA_FB_BASE, ESTA_VRAM, 0, RX550_GART_PLACEMENT_BEST_FIT,
		   &g) == RX550_GART_GEOM_ERR_NO_CABE, "gart_size = 0 rechazado");
	CHECK(calc(ESTA_FB_BASE, 0, MEDIDO_MIB << 20, RX550_GART_PLACEMENT_BEST_FIT,
		   &g) == RX550_GART_GEOM_ERR_VRAM_CERO, "vram_bytes = 0 rechazado");

	/* fb_base tiene que ser multiplo de 16 MiB porque el registro lo
	 * garantiza: FB_BASE es de 16 bits y el corpus lo desplaza 24. */
	CHECK(calc(ESTA_FB_BASE + 1, ESTA_VRAM, MEDIDO_MIB << 20,
		   RX550_GART_PLACEMENT_BEST_FIT, &g) == RX550_GART_GEOM_ERR_FB_DESALINEADO,
	      "fb_base desalineado a 16 MiB rechazado");
	CHECK(calc(ESTA_FB_BASE + (UINT64_C(1) << 24), ESTA_VRAM, MEDIDO_MIB << 20,
		   RX550_GART_PLACEMENT_BEST_FIT, &g) == RX550_GART_GEOM_OK,
	      "fb_base exactamente un paso de 16 MiB mas vale");

	/* EL CLAMP.  Con la geometria MEDIDA y un GART de 2 TiB no cabe en
	 * ninguno de los dos huecos: el de abajo es de 976 GiB.  El corpus lo
	 * encoge a 976 GiB y avisa por dev_warn; este productor lo calcula, lo
	 * MARCA y devuelve error.
	 *
	 * El primer vector uso fb_base = 0 y NO disparaba el clamp: con la VRAM
	 * en 0 el hueco de ABAJO es 0 pero el de ARRIBA son 4080 GiB, y 512 MiB
	 * caben de sobra.  Un vector que no dispara la rama que dice probar no
	 * prueba esa rama. */
	CHECK(calc(ESTA_FB_BASE, ESTA_VRAM, UINT64_C(2) << 40,
		   RX550_GART_PLACEMENT_BEST_FIT, &g) == RX550_GART_GEOM_ERR_NO_CABE,
	      "GART de 2 TiB con la geometria medida: no cabe en ningun hueco");
	CHECK(g.clamped, "y el clamp queda MARCADO, no aceptado en silencio");
	CHECK(g.gart_size_effective == g.size_below,
	      "el tamano encogido es el hueco mayor, como hace el corpus");
	CHECK(g.gart_size_effective == UINT64_C(0xF400000000),
	      "que aqui son 976 GiB, el hueco de ABAJO");

	/* RX550_GART_GEOM_ERR_FUERA_DE_PT no se puede disparar, y eso es mejor
	 * que un vector que lo dispare: es una guarda probada innecesaria.
	 *
	 *   - Si size_below > size_above, el clamp toma size_below como maximo,
	 *     luego gart_size <= size_below, y la rama LOW-else (que exige
	 *     size_below < gart_size) es inalcanzable.
	 *   - Si size_below <= size_above, sin clamp gart_size <= size_above =
	 *     max_mc + 1 - ALIGN(fb_end+1), luego
	 *       gart_end = ALIGN(fb_end+1) + gart_size - 1 <= max_mc_address.
	 *   - El caso LOW con size_below >= gart_size da gart_start = 0, que
	 *     tambien cabe.
	 * Luego gart_end <= max_mc_address SIEMPRE, y max_mc_address son 40
	 * bits, que es exactamente lo que cabe en PHYSICAL_PAGE_NUMBER.
	 *
	 * Y el invariante se comprueba ademas por ejecucion, sobre las tres
	 * politicas y ocho tamanos. */
	CHECK(RX550_GART_GEOM_PN_BITS == 28u, "el ancho del campo es de 28 bits");
	CHECK((((UINT64_C(1) << RX550_GART_GEOM_PN_BITS) << RX550_PAGE_SHIFT) - 1)
	      == RX550_MC_MASK,
	      "max_mc_address coincide EXACTAMENTE con el limite de pagina: "
	      "por eso FUERA_DE_PT no puede dispararse");
	{
		struct rx550_gart_geom q;
		uint64_t t;
		uint64_t max_visto = 0;
		int fuera = 0;

		for (t = 1; t <= (UINT64_C(1) << 30); t <<= 1) {
			if (calc(ESTA_FB_BASE, ESTA_VRAM, t,
				 RX550_GART_PLACEMENT_LOW, &q) ==
			    RX550_GART_GEOM_ERR_FUERA_DE_PT)
				fuera++;
			if (calc(ESTA_FB_BASE, ESTA_VRAM, t,
				 RX550_GART_PLACEMENT_HIGH, &q) ==
			    RX550_GART_GEOM_ERR_FUERA_DE_PT)
				fuera++;
			if (calc(ESTA_FB_BASE, ESTA_VRAM, t,
				 RX550_GART_PLACEMENT_BEST_FIT, &q) ==
			    RX550_GART_GEOM_ERR_FUERA_DE_PT)
				fuera++;
			if (q.gart_end > max_visto)
				max_visto = q.gart_end;
		}
		CHECK(fuera == 0,
		      "24 combinaciones de politica y tamano: FUERA_DE_PT, ninguna");
		CHECK(max_visto <= RX550_MC_MASK,
		      "y ningun gart_end rebasa los 40 bits de la MC");
	}

	/* Puntero nulo: se comprueba antes de leer nada. */
	{
		struct rx550_gart_geom_in in;

		memset(&in, 0, sizeof(in));
		CHECK(rx550_gart_geometry(NULL, &g) == RX550_GART_GEOM_ERR_NULO,
		      "entrada nula rechazada");
		CHECK(rx550_gart_geometry(&in, NULL) == RX550_GART_GEOM_ERR_NULO,
		      "salida nula rechazada");
	}
}

/* ── las tres politicas producen tres cosas distintas ───────────────────── */
static void fase_politicas(void)
{
	struct rx550_gart_geom low, high, best;
	uint64_t tam = MEDIDO_MIB << 20;

	printf("las tres politicas\n");

	CHECK(calc(ESTA_FB_BASE, ESTA_VRAM, tam, RX550_GART_PLACEMENT_LOW,
		   &low) == 0, "LOW: OK");
	CHECK(calc(ESTA_FB_BASE, ESTA_VRAM, tam, RX550_GART_PLACEMENT_HIGH,
		   &high) == 0, "HIGH: OK");
	CHECK(calc(ESTA_FB_BASE, ESTA_VRAM, tam, RX550_GART_PLACEMENT_BEST_FIT,
		   &best) == 0, "BEST_FIT: OK");

	CHECK(low.gart_start != high.gart_start, "LOW y HIGH danSitios distintos");
	CHECK(high.gart_start == best.gart_start,
	      "BEST_FIT coincide con HIGH en esta geometria");

	/* Las tres tienen el MISMO tamano y estan alineadas a 4 GiB. */
	CHECK(low.gart_end - low.gart_start == tam - 1, "LOW: mismo tamano");
	CHECK(high.gart_end - high.gart_start == tam - 1, "HIGH: mismo tamano");
	CHECK(best.gart_end - best.gart_start == tam - 1, "BEST_FIT: mismo tamano");
	CHECK((low.gart_start & (RX550_GART_FOUR_GB - 1)) == 0, "LOW alineada a 4 GiB");
	CHECK((high.gart_start & (RX550_GART_FOUR_GB - 1)) == 0, "HIGH alineada a 4 GiB");
	CHECK((best.gart_start & (RX550_GART_FOUR_GB - 1)) == 0,
	      "BEST_FIT alineada a 4 GiB: la alineacion es comun a las tres");

	/* HIGH no puede sobrepasar el tope de la MC. */
	CHECK(high.gart_end <= high.max_mc_address,
	      "HIGH no rebasa max_mc_address");
}

/* ── lo que la funcion NO decide ────────────────────────────────────────── */
static void fase_no_decidido(void)
{
	printf("lo que no decide\n");

	CHECK(1, "no lee ningun registro: eso es RUNTIME_REQUIRED");
	CHECK(1, "no compueba que fb_base valga lo que dice el registro");
	CHECK(1, "no dice nada sobre si el hardware obedece la geometria");
	CHECK(1, "el clamp se calcula con la aritmetica del corpus pero SE RECHAZA");
	CHECK(1, "la rama LOW usa ALIGN(fb_end+1), el corpus usa ALIGN(fb_end)");
}

int main(void)
{
	printf("test_gart_geom — productor de la geometria del GART\n\n");

	fase_constantes();
	fase_medido();
	fase_bordes();
	fase_politicas();
	fase_no_decidido();

	printf("\n  %d pass, %d fail\n", pass, fail);
	return fail ? 1 : 0;
}