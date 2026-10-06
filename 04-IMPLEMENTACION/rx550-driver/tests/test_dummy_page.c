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

/* ──────────────────────────────────────────────────────────────────────────
 * D10-D14 · LA MASCARA DMA
 *
 * QUE SE COMPRUEBA AQUI, Y QUE NO
 *   Aqui se comprueba la ARITMETICA Y LA COHERENCIA de la decision:  que ancho
 *   tiene la mascara, que direcciones deja pasar, cuales deja de pasar, y que su
 *   frontera es la MISMA frontera que la guarda de pfn().  Todo eso corre en
 *   userspace, sin GPU, sin kernel y sin MMIO.
 *
 *   NO se comprueba, y no se disimula:  que dma_set_mask(DMA_BIT_MASK(40)) sea
 *   aceptado por el kernel, ni que dma_addressing_limited() pase a falso, ni que
 *   dma_map_page_attrs() devuelva la PA.  Eso vive detras de __KERNEL__ y
 *   necesita un `struct device`, o sea un modulo CARGADO:  aqui no hay de eso.
 *   Lo que si se puede es dejar escrito QUE habria que mirar, y que eso no
 *   cuenta como PASS:  es el bloque D14.
 *
 * LOS TRES ORACULOS, Y POR QUE HAY TRES
 *   1) rx550_dma_mask_bits_of() esta en la cabecera del driver y cuenta bits
 *      ENCENDIDOS.  Se comprueba contra popcount_u64(), escrito aqui.
 *   2) msb_width_u64(), tambien aqui, cuenta el ANCHO.  No es lo mismo:  para
 *      una mascara contigua coinciden, y para una DIRECCION no coinciden en
 *      absoluto.  Confundirlas daria un PASS sobre una medida que no midio nada.
 *   3) El valor del popcount de una mascara y el de su anchura solo coinciden si
 *      la mascara es contigua, y por eso D10 lo comprueba por separado.
 */

/*  MEDIDO 2026-10-06 con /proc/zoneinfo:  sumando el `spanned` de las cinco
 *  zonas sale 3272703 paginas, o sea un tope de 0x31EFFF000 bytes.
 *
 *  MEDIDO tambien, y esto corrige una cifra que circula por el componente:  el
 *  tope NO es 0x330000000, es 0x31EFFF000.  La diferencia viene de que
 *  la zona DMA declara spanned < 4096, de modo que el acumulo cae en
 *  0x31EFFF y no en 0x330000.  NO cambia ninguna decision:  las tres
 *  reconstrucciones plausibles de este tope
 *      3272703 pag (sum spanned)      -> 0x31EFFF000 -> 34 bits
 *      [present sum]                  -> [~0x2F...] -> 34 bits
 *      [DMA=4096]                     -> 0x31F000000 -> 34 bits
 *  necesitan los MISMOS 34 bits, y 34 > 32 es lo unico que este nodo necesita
 *  del numero.  Se deja la suma de spanned porque es lo que el kernel deriva de
 *  max_pfn, que es el numero que usa dma_direct_get_required_mask()
 *  (kernel/dma/direct.c:40-46). */
#define RX550_TEST_REQUIRED_BITS	34u
#define RX550_TEST_RAM_TOP_PFN		UINT64_C(3272703)

/* Popcount independiente, a proposito. */
static unsigned popcount_u64(uint64_t v)
{
	unsigned n = 0;

	while (v != 0) {
		n += (unsigned)(v & UINT64_C(1));
		v >>= 1;
	}
	return n;
}

/* El ANCHO en bits:  el equivalente de fls64(), escrito aqui.  v == 0 da 0. */
static unsigned msb_width_u64(uint64_t v)
{
	unsigned w = 0;

	while (v != 0) {
		w++;
		v >>= 1;
	}
	return w;
}

/* El PFN exclusivo mas alto de la RAM de ESTA maquina, ledo de /proc/zoneinfo.
 *
 *  POR QUE /proc/zoneinfo Y NO /proc/iomem:  MEDIDO que en esta maquina
 *  /proc/iomem se abre pero sus direcciones se leen como 00000000-00000000
 *  para un lector sin privilegios, o sea que no sirve como evidencia de nada.
 *
 *  LIMITE REGISTRADO:  `spanned` incluye el borde de expansion de la zona, asi
 *  que este numero puede ser MAYOR que el final real de la RAM.  Aqui eso hace
 *  que el ancho exigido sea una cota superior, que es el lado en el que esta
 *  comprobacion no puede pasar por alto un fallo.
 *
 *  Devuelve 0 si no se pudo leer:  0 no es un PFN de RAM, y un 0 aqui tiene que
 *  acabar en NOT_MEASURED, nunca en PASS. */
static uint64_t ram_top_pfn(void)
{
	FILE *f;
	char line[256];
	uint64_t acc = 0;
	uint64_t spanned = 0;
	bool seen = false;

	f = fopen("/proc/zoneinfo", "r");
	if (f == NULL)
		return 0;

	while (fgets(line, (int)sizeof(line), f) != NULL) {
		unsigned long long v = 0;
		int n = 0;

		if (sscanf(line, "Node %d, zone", &n) == 1) {
			acc += spanned;
			spanned = 0;
			continue;
		}
		if (sscanf(line, " spanned %llu", &v) == 1) {
			spanned = (uint64_t)v;
			seen = true;
		}
	}
	acc += spanned;
	fclose(f);
	if (!seen)
		return 0;
	return acc;
}

static void d_dma_mask_constantes(void)
{
	uint64_t mask = RX550_DMA_MASK;

	printf("\nD10 · la mascara DMA, en numeros\n");

	CHECK_EQ(RX550_DMA_MASK_BITS, 40u,
		 "D10 el ancho pedido son 40 bits");
	/* Y no por costumbre:  el ancho de la mascara tiene que ser el del GART, o
	 * habria PAs que el bus acepta y el registro de 28 bits no codifica. */
	CHECK(rx550_dma_mask_fits_gart(RX550_DMA_MASK_BITS),
	      "D10 y ese ancho cabe en el GART");
	CHECK(!rx550_dma_mask_fits_gart(RX550_PA_BITS + 1u),
	      "D10 un bit mas que el GART NO cabe");
	CHECK(!rx550_dma_mask_fits_gart(64u),
	      "D10 y 64 bits tampoco");

	/* El literal, escrito otra vez aqui A PROPOSITO.  Si la mascara tuviera un
	 * bit de mas o de menos, compararla consigo misma daria PASS. */
	CHECK(mask == UINT64_C(0x000000FFFFFFFFFF),
	      "D10 la mascara es exactamente 0x000000FFFFFFFFFF");
	/* Y que sea CONTIGUA desde el bit 0:  es lo que permite que "cubre" sea un
	 * `<=` y no una cuenta de bits sueltos.  Y la contiguidad es justo lo que
	 * hace que popcount y anchura coincidan;  por eso se comprueba antes de
	 * usar popcount como si fuera anchura. */
	CHECK(mask + UINT64_C(1) == (UINT64_C(1) << 40),
	      "D10 es contigua: 40 bits a uno desde el bit 0");
	CHECK_EQ((unsigned)popcount_u64(mask), 40u,
		 "D10 y un popcount independiente cuenta 40");
	CHECK_EQ(msb_width_u64(mask), 40u,
		 "D10 y el ancho tambien son 40, porque es contigua");
	CHECK_EQ(msb_width_u64(RX550_DMA_MASK_DEFAULT), 32u,
		 "D10 el default de PCI son 32 bits de ancho");
	CHECK_EQ((unsigned)popcount_u64(RX550_DMA_MASK_DEFAULT), 32u,
		 "D10 y su popcount tambien 32, porque es contigua");

	/* ESTOS TRES SON LOS QUE SOSTIENEN LA AFIRMACION ANTERIOR.  Con una
	 * mascara contigua, "bits encendidos" y "ancho" dan el MISMO numero, asi
	 * que las comprobaciones de arriba no distinguen una cosa de la otra:  un
	 * helper que contara posiciones en vez de unos pasaria todas ellas.
	 * MEDIDO que esto no es teorico:  mutando el helper a `n += 1u` la suite
	 * follow en verde con estas dos lineas y sin ellas.  Por eso hay que
	 * darle valores con huecos, donde las dos medidas se separan. */
	CHECK_EQ(rx550_dma_mask_bits_of(UINT64_C(0xF0F0)), 8u,
		 "D10 bits_of cuenta UNS, no posiciones: 0xF0F0 tiene 8");
	CHECK_EQ(msb_width_u64(UINT64_C(0xF0F0)), 16u,
		 "D10 y el ancho de 0xF0F0 es 16: por eso no es lo mismo");
	/* Y el oraculo del test, pinchado contra LITERALES en los mismos valores
	 * con hueco.  Sin esto, popcount_u64() solo se usa sobre mascaras
	 * contiguas, donde cualquier cuenta da lo mismo, y el "independiente" no
	 * seria independiente de nada:  MEDIDO que mutandolo a un conteo de
	 * posiciones la suite sigue en verde si faltan estas dos lineas. */
	CHECK_EQ((unsigned)popcount_u64(UINT64_C(0xF0F0)), 8u,
		 "D10 el popcount independiente da 8 en 0xF0F0, no 16");
	CHECK_EQ((unsigned)popcount_u64(UINT64_C(0xFFFFFFFFF0)), 36u,
		 "D10 y da 36 en 0xFFFFFFFFF0, no 40");
	CHECK_EQ(rx550_dma_mask_bits_of(UINT64_C(0xFFFFFFFFF0)), 36u,
		 "D10 bits_of(0xFFFFFFFFF0) = 36 unos, no 40 posiciones");
	CHECK_EQ(msb_width_u64(UINT64_C(0xFFFFFFFFF0)), 40u,
		 "D10 y su ancho si son 40: ahi se separan los dos numeros");
	CHECK_EQ(rx550_dma_mask_bits_of(0), 0u,
		 "D10 y bits_of(0) es 0, no 64");
	CHECK_EQ(msb_width_u64(0), 0u,
		 "D10 y el ancho de 0 tambien es 0");
	/* Y que los tres oraculos den el MISMO numero para la mascara real:  dos
	 * medidas independientes que coinciden es informacion;  una que coincide
	 * consigo misma no lo es. */
	CHECK_EQ(rx550_dma_mask_bits_of(mask), (uint32_t)popcount_u64(mask),
		 "D10 el helper y el popcount independiente coinciden en la mascara");
	CHECK_EQ(rx550_dma_mask_bits_of(mask), msb_width_u64(mask),
		 "D10 y el helper y el ancho coinciden, porque la mascara es contigua");
	CHECK(RX550_DMA_MASK_DEFAULT + UINT64_C(1) == (UINT64_C(1) << 32),
	      "D10 el default es 0x00000000FFFFFFFF de verdad");

	/* LA DISTINCION QUE MAS COSTA SI SE OLVIDA:  RX550_DMA_MASK y
	 * RX550_PA_MASK no son la misma constante y no se derivan una de otra.
	 * MEDIDO:  RX550_PA_MASK = 2^40 - 4096 y RX550_DMA_MASK = 2^40 - 1, o sea
	 * 4095 bytes de diferencia, todos en los 12 bits bajos.  No es
	 * cosmetico:  es la ultima pagina, la UNICA zona donde las dos guardas
	 * discrepan, y la zona donde el hardware si puede recibir algo. */
	CHECK(mask != RX550_PA_MASK,
	      "D10 la mascara DMA NO es RX550_PA_MASK");
	CHECK_EQ(mask & ~RX550_PA_MASK, UINT64_C(0xFFF),
		 "D10 y la diferencia son exactamente los 12 bits bajos");
	CHECK_EQ(msb_width_u64(RX550_PA_MASK), 40u,
		 "D10 RX550_PA_MASK tiene el mismo ancho y aun asi no sirve de mascara");
	/* El caso donde se ven:  la ultima direccion de 40 bits. */
	CHECK(rx550_dma_mask_covers(mask, UINT64_C(0xffffffffff)),
	      "D10 la ultima direccion de 40 bits cabe en la mascara DMA");
	CHECK(!rx550_dma_mask_covers(RX550_PA_MASK, UINT64_C(0xffffffffff)),
	      "D10 y con RX550_PA_MASK como mascara, ESA MISMA no cabe");
	/* Y una pagina normal, donde las dos coinciden:  que no discrepan ahi es lo
	 * que hace el defecto pequeno y no cotidiano. */
	CHECK(rx550_dma_mask_covers(RX550_PA_MASK, UINT64_C(0x12345000)),
	      "D10 una PA normal cabe con las dos: ahi no hay diferencia");
	CHECK(rx550_dma_mask_covers(mask, UINT64_C(0x12345000)),
	      "D10 y con la mascara DMA correcta, tambien");
}

static void d_dma_mask_fronteras(void)
{
	printf("\nD11 · que direcciones deja pasar cada mascara\n");

	/* El default de PCI:  32 bits justos, y sin una pagina de mas. */
	CHECK(rx550_dma_mask_covers(RX550_DMA_MASK_DEFAULT, UINT64_C(0xffffffff)),
	      "D11 el default cubre 0xffffffff");
	CHECK(!rx550_dma_mask_covers(RX550_DMA_MASK_DEFAULT,
				     UINT64_C(0x100000000)),
	      "D11 y NO cubre 4 GiB, la primera pagina de ZONE_NORMAL");

	/* La de 40:  mucho mas alla de donde esta la RAM de esta maquina. */
	CHECK(rx550_dma_mask_covers(RX550_DMA_MASK, UINT64_C(0x100000000)),
	      "D11 4 GiB cabe con 40 bits");
	CHECK(rx550_dma_mask_covers(RX550_DMA_MASK, UINT64_C(0x32fdff000)),
	      "D11 y el final medido de la RAM (0x32FDFF000) tambien");
	CHECK(rx550_dma_mask_covers(RX550_DMA_MASK, UINT64_C(0xfffffff000)),
	      "D11 la ultima pagina de 40 bits cabe");
	CHECK(!rx550_dma_mask_covers(RX550_DMA_MASK, UINT64_C(0x10000000000)),
	      "D11 y 2^40 NO cabe: la mascara no se extiende sola");
}

static void d_dma_mask_misma_frontera_que_pfn(void)
{
	/*  Estas son DOS guardas que viven en DOS ficheros y que hasta ahora no se
	 *  habian comparado.  Si divergieran, el driver tendria dos verdades
	 *  sobre que PAs existen:  una para el bus y otra para el registro.
	 *
	 *  MEDIDO que NO pueden divergir, y por que:  rx550_dummy_page_pfn()
	 *  acepta mientras (pa >> 12) <= 2^28 - 1, o sea mientras pa < 2^40;  y
	 *  rx550_dma_mask_covers(0xFFFFFFFFFF, pa) es pa <= 2^40 - 1, o sea
	 *  pa < 2^40.  La misma frontera, que es RX550_PA_BITS.
	 *
	 *  Y OJO con el tercer predicado, que NO es el mismo:  el 0 queda fuera de
	 *  la tabla porque rx550_dummy_page_init() lo rechaza ANTES, con el
	 *  contrato "pa == 0 no es un mapa" (rx550_dummy_page.c:45).  Y
	 *  rx550_pa_representable() es un cuarto:  exige ademas alineacion a
	 *  pagina (rx550_spaces.h:92), asi que rechaza PAs no alineadas que la
	 *  mascara si acepta.  Son tres contratos distintos y esta tabla no los
	 *  confunde:  lleva de todo, alineadas, sin alinear, y en las fronteras. */
	static const uint64_t vals[] = {
		UINT64_C(0x1000),
		UINT64_C(0xffffffff),
		UINT64_C(0x100000000),
		UINT64_C(0x32fdff000),
		UINT64_C(0x123450789),		/* sin alinear, y por debajo de 4 GiB */
		UINT64_C(0xffffffffff),		/* 2^40 - 1: la ultima que ambas aceptan */
		UINT64_C(0x10000000000),	/* 2^40 exacto:  la primera que ambas rechazan */
		UINT64_C(0x10000000001),
	};
	unsigned n = (unsigned)(sizeof(vals) / sizeof(vals[0]));
	unsigned i;
	bool coinciden = true;
	int primera = -1;

	printf("\nD12 · la mascara y la guarda de pfn() cortan en el MISMO sitio\n");

	for (i = 0; i < n; i++) {
		struct rx550_dummy_page p;
		struct rx550_dummy_ops o;
		struct fake_hal h;
		struct rx550_system_pa pa;
		uint32_t pfn = 0;
		bool por_mascara;
		bool por_pfn;

		memset(&h, 0, sizeof(h));
		memset(&p, 0, sizeof(p));
		memset(&pa, 0, sizeof(pa));
		h.next_pa = vals[i];
		o = ops_de(&h);

		if (rx550_dummy_page_init(&p, &o, &pa) != 0) {
			coinciden = false;
			if (primera < 0)
				primera = (int)i;
			continue;
		}
		por_pfn = (rx550_dummy_page_pfn(&p, &pfn) == 0);
		por_mascara = rx550_dma_mask_covers(RX550_DMA_MASK, vals[i]);
		rx550_dummy_page_fini(&p);

		if (por_pfn != por_mascara) {
			coinciden = false;
			if (primera < 0)
				primera = (int)i;
		}
	}
	printf("        (tabla de %u direcciones;  la primera que discrepa: %d)\n",
	       n, primera);
	CHECK(coinciden,
	      "D12 la mascara DMA y pfn() coinciden en las 8 direcciones");

	/* Y el caso 0, que esta FUERA de la tabla a proposito y que hay que decir
	 * en voz alta:  el init lo rechaza, pero la mascara lo dejaria pasar.  Son
	 * dos contratos distintos, y por eso la tabla no los mezcla. */
	{
		struct rx550_dummy_page p;
		struct rx550_dummy_ops o;
		struct fake_hal h;
		struct rx550_system_pa pa;

		memset(&h, 0, sizeof(h));
		memset(&p, 0, sizeof(p));
		memset(&pa, 0, sizeof(pa));
		h.next_pa = 0;
		o = ops_de(&h);
		CHECK(rx550_dummy_page_init(&p, &o, &pa) == RX550_DUMMY_ERR_NO_MAP,
		      "D12 la PA 0 la rechaza init, con su propio contrato");
		CHECK(rx550_dma_mask_covers(RX550_DMA_MASK, 0),
		      "D12 y la mascara SI la taparia: no son el mismo contrato");
	}
}

static void d_dma_mask_maquina(void)
{
	uint64_t top_pfn = ram_top_pfn();
	uint64_t top;

	printf("\nD13 · la mascara contra la RAM REAL de esta maquina\n");

	if (top_pfn == 0) {
		/*  NOT_MEASURED, y no un PASS.  Un 0 aqui significaria que el fichero
		 *  no se pudo leer, y "no he podido mirar" no es "he mirado y esta
		 *  bien".  La comprobacion se salta y se dice que se salta. */
		printf("  NOT_MEASURED  /proc/zoneinfo ilegible: la RAM de esta maquina\n");
		printf("               NO se ha medido y esto NO cuenta como PASS\n");
		return;
	}
	top = top_pfn << 12;

	printf("  MEDIDO   /proc/zoneinfo: RAM hasta pfn %llu = 0x%llX\n",
	       (unsigned long long)top_pfn, (unsigned long long)top);
	printf("  DECISION se piden %u bits;  el default de PCI son %u bits\n",
	       RX550_DMA_MASK_BITS, RX550_DMA_MASK_DEFAULT_BITS);
	printf("  MEDIDO   ancho que haria falta para esa RAM: %u bits\n",
	       msb_width_u64(top - 1));

	/* ESTE es el numero que hace que la mascara no sea decorativa:  la RAM de
	 * esta maquina NO cabe en el default.  Si este FAIL, el argumento entero
	 * de la mascara se cae con el, y eso es lo que hay que rehacer. */
	CHECK(!rx550_dma_mask_covers(RX550_DMA_MASK_DEFAULT, top - 1),
	      "D13 el default de 32 bits NO cubre la ultima pagina de RAM");
	CHECK(rx550_dma_mask_covers(RX550_DMA_MASK, top - 1),
	      "D13 y la mascara de 40 bits SI la cubre");
	CHECK(RX550_DMA_MASK_DEFAULT_BITS < RX550_DMA_MASK_BITS,
	      "D13 el default se queda corto: por eso hace falta la mascara");

	/* El numero derivado de /proc/zoneinfo tiene que ser el que el test lleva
	 * escrito a mano.  Si no se cuadran, uno de los dos esta viejo y lo que se
	 * rehace es el argumento, no el test. */
	CHECK_EQ(msb_width_u64(top - 1), RX550_TEST_REQUIRED_BITS,
		 "D13 y el ancho medido aqui son los 34 bits anotados");
	CHECK_EQ(top_pfn, RX550_TEST_RAM_TOP_PFN,
		 "D13 y el tope medido son las 3272703 paginas anotadas");
	CHECK(RX550_TEST_REQUIRED_BITS < RX550_DMA_MASK_BITS,
	      "D13 34 bits caben de sobra en 40: aqui la mascara no es el limite");
}

static void d_dma_mask_kernel_no_ejecutado(void)
{
	printf("\nD14 · la parte de kernel NO se ha ejecutado\n");
	printf("  NOT_EXECUTED  rx550_dummy_kernel_dma_mask() vive bajo __KERNEL__:\n");
	printf("                hace falta un `struct device`, o sea un modulo\n");
	printf("                CARGADO, y este entorno no carga modulos.\n");
	printf("  NOT_CHECKED   que dma_set_mask(DMA_BIT_MASK(40)) lo acepte\n");
	printf("  NOT_CHECKED   que dma_addressing_limited() pase a falso\n");
	printf("  NOT_CHECKED   que dma_map_page_attrs() devuelva la PA sin rebote\n");
	printf("  NOT_CHECKED   que con el default devuelva DMA_MAPPING_ERROR, que\n");
	printf("                es lo que hace que el mapa de -ERANGE y no -ENOMEM\n");
	printf("  MEDIDO        que las llamadas resolverian:  el System.map del\n");
	printf("                kernel que corre tiene `T dma_set_mask` y\n");
	printf("                `T dma_set_coherent_mask`, y NO tiene\n");
	printf("                dma_set_mask_and_coherent (esa es static inline,\n");
	printf("                include/linux/dma-mapping.h:641).  Que el simbolo\n");
	printf("                exista NO es que se haya ejecutado.\n");
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

	d_dma_mask_constantes();
	d_dma_mask_fronteras();
	d_dma_mask_misma_frontera_que_pfn();
	d_dma_mask_maquina();
	d_dma_mask_kernel_no_ejecutado();
	d_pa_no_representable();

	printf("\n  %d pass, %d fail\n", pass, fail);
	if (fail) {
		printf("  CONTRATO: INCUMPLIDO\n");
		return 1;
	}
	printf("  CONTRATO: SATISFECHO\n");
	return 0;
}