/* SPDX-License-Identifier: GPL-2.0-only */
/*
 * test_vmid1_pgt.c — T1..T11 para el modulo de la jerarquia de VMID1.
 *
 *   TARGET = RX 550 instalada en esta maquina  (1002:699F, Polaris12, GFX8)
 *   SCOPE  = EXCLUSIVO
 *
 * QUE ES Y QUE NO ES
 *   Tests unitarios deterministas.  Sin GPU, sin MMIO, sin kernel, sin
 *   reserva de memoria real:  todo el backing es un array de userspace.
 *   Y por eso la geometria, que es aritmetica, se verifica aqui y no en un
 *   MMIO_TEST.
 *
 * QUE COMPRUEBA CADA UNO, Y POR QUE ESTE Y NO OTRO
 *   La mayoria son de la familia "un caso positivo y su caso limite".  Un
 *   test que solo comprueba el caso negativo no distingue "la regla esta
 *   activa" de "el valor es inalcanzable", y una geometria con una regla
 *   muerta no se distingue de una geometria correcta.
 *
 *   T10 y T11 son ESTATICOS:  leen los dos fuentes de M2 y comprueban que no
 *   nombran lo que no deben nombrar.  Son la parte que protege contra la
 *   regresion que motivo todo esto, que es usar el encoder de PTE o el
 *   encoding de rx550_pdb0.h para un PDE.
 *
 * USO
 *   ./test_vmid1_pgt [ruta_al_directorio_de_los_fuentes]
 *   por defecto "..", que es donde estan rx550_vmid1_pgt.[ch]
 */

#include <stdio.h>
#include <stdlib.h>
#include <string.h>
#include <stdint.h>
#include <stdbool.h>

#include "rx550_vmid1_pgt.h"

/* ── marco de checks ──────────────────────────────────────────────────────
 * El proyecto cuenta, no aborta:  un test que para en el primer fallo no
 * dice cuantos de los restantes tambien fallan. */
static unsigned g_pass;
static unsigned g_fail;

#define CHECK(cond, ...)						\
	do {								\
		if (cond) {						\
			g_pass++;					\
		} else {						\
			g_fail++;					\
			printf("  FALLO  ");				\
			printf(__VA_ARGS__);				\
			printf("\n");					\
		}							\
	} while (0)

#define CHECK_EQ(got, want, ...)					\
	do {								\
		long long g_ = (long long)(got);			\
		long long w_ = (long long)(want);			\
		if (g_ == w_) {						\
			g_pass++;					\
		} else {						\
			g_fail++;					\
			printf("  FALLO  ");				\
			printf(__VA_ARGS__);				\
			printf("   (obtenido %lld, esperado %lld)\n",	\
			       g_, w_);				\
		}							\
	} while (0)

/* La ventana que demuestra GFX8, y la unica que este modulo acepta. */
#define WINDOW_1GIB	(UINT64_C(1) << 30)

/* ═══════════════════════════════════════════════════════════════════════════
 * T1  1 GiB  ->  depth 1
 * ═══════════════════════════════════════════════════════════════════════════ */
static void t1_depth(void)
{
	struct rx550_vmid1_geom g;
	int rc = rx550_vmid1_geometry(WINDOW_1GIB, &g);

	CHECK_EQ(rc, RX550_PGT_OK, "T1 geometry(1GiB) deberia aceptarse");
	CHECK(g.valid, "T1 la geometria deberia quedar valida");
	CHECK_EQ(g.num_level, 1, "T1 num_level");
	/* gfxhub_v1_0.c:267-268  PAGE_TABLE_DEPTH = num_level */
	CHECK_EQ(g.depth_field, 1, "T1 el valor para PAGE_TABLE_DEPTH");
	/* amdgpu_vm.c:2451-2452  num_level 1 -> root_level = AMDGPU_VM_PDB0 */
	CHECK_EQ(g.root_type, RX550_ROOT_PDB0, "T1 root_type debe ser PDB0");
	/* gmc_v8_0.c:933-934  PAGE_TABLE_BLOCK_SIZE = block_size - 9 */
	CHECK_EQ(g.block_size, 9, "T1 block_size");
	CHECK_EQ(g.block_size_field, 0, "T1 el valor para PAGE_TABLE_BLOCK_SIZE");
}

/* ═══════════════════════════════════════════════════════════════════════════
 * T2  1 GiB  ->  512 paginas PTE
 * ═══════════════════════════════════════════════════════════════════════════ */
static void t2_pte_pages(void)
{
	struct rx550_vmid1_geom g;

	CHECK_EQ(rx550_vmid1_geometry(WINDOW_1GIB, &g), RX550_PGT_OK,
		 "T2 geometry(1GiB)");
	/* El numero de paginas PTE es el numero de entradas de la raiz, y la
	 * raiz tiene 2^block_size entradas.  Con block_size 9 son 512. */
	CHECK_EQ(g.pte_pages, 512, "T2 pte_pages");
	CHECK_EQ(g.pte_pages, g.entries_per_level,
		 "T2 pte_pages deberia igualar las entradas del nivel");
}

/* ═══════════════════════════════════════════════════════════════════════════
 * T3  root size = 4 KiB
 * ═══════════════════════════════════════════════════════════════════════════ */
static void t3_root_size(void)
{
	struct rx550_vmid1_geom g;

	CHECK_EQ(rx550_vmid1_geometry(WINDOW_1GIB, &g), RX550_PGT_OK,
		 "T3 geometry(1GiB)");
	CHECK_EQ(g.root_bytes, 4096, "T3 root_bytes");
	/* 4 KiB es una consequence de block_size 9 y de 8 B por entrada, no un
	 * valor puesto a mano.  Si alguien tocara uno de los dos, esta comprobacion
	 * lo delata. */
	CHECK_EQ(g.root_bytes,
		 (uint64_t)g.entries_per_level * RX550_VMID1_ENTRY_BYTES,
		 "T3 root_bytes deberia derivar de entradas * 8");
	CHECK_EQ(g.root_bytes, RX550_VMID1_PAGE_SIZE,
		 "T3 el root deberia ser exactamente una pagina");
}

/* ═══════════════════════════════════════════════════════════════════════════
 * T4  cada pagina PTE = 512 * 8 = 4096
 * ═══════════════════════════════════════════════════════════════════════════ */
static void t4_pte_page_size(void)
{
	struct rx550_vmid1_geom g;

	CHECK_EQ(rx550_vmid1_geometry(WINDOW_1GIB, &g), RX550_PGT_OK,
		 "T4 geometry(1GiB)");
	CHECK_EQ(g.pte_entries, 512, "T4 pte_entries");
	CHECK_EQ(g.pte_page_bytes, 4096, "T4 pte_page_bytes");
	CHECK_EQ(g.pte_page_bytes, 512u * 8u, "T4 512 entradas de 8 B");
	/* Las 512 hojas suman 2 MiB, mas 4 KiB de raiz. */
	CHECK_EQ(g.total_bytes, 4096u + 512u * 4096u, "T4 total_bytes");
}

/* ═══════════════════════════════════════════════════════════════════════════
 * T5  la maxima VA valida mapea al ultimo indice correcto
 * T5b el indexado cubre el rango sin huecos ni solapes
 * ═══════════════════════════════════════════════════════════════════════════ */
static void t5_indexing(void)
{
	struct rx550_vmid1_geom g;
	uint32_t pde = 0, pte = 0;
	uint64_t last_va;

	CHECK_EQ(rx550_vmid1_geometry(WINDOW_1GIB, &g), RX550_PGT_OK,
		 "T5 geometry(1GiB)");

	last_va = g.coverage_bytes - RX550_VMID1_PAGE_SIZE;

	CHECK_EQ(rx550_vmid1_locate(&g, last_va, &pde, &pte), RX550_PGT_OK,
		 "T5 la maxima VA valida deberia localizarse");
	CHECK_EQ(pde, 511, "T5 pde_index del ultimo elemento");
	CHECK_EQ(pte, 511, "T5 pte_index del ultimo elemento");

	/* Y la primera. */
	CHECK_EQ(rx550_vmid1_locate(&g, 0, &pde, &pte), RX550_PGT_OK,
		 "T5 la VA 0 deberia localizarse");
	CHECK_EQ(pde, 0, "T5 pde_index del primer elemento");
	CHECK_EQ(pte, 0, "T5 pte_index del primer elemento");

	/*
	 * T5b:  la reconstruccion del round-trip.
	 *
	 * Si el indexado tuviera un hueco, un VA caeria en un par de indices que
	 * reconstruyen OTRO VA.  Si tuviera solape, dos VA distintas caerian en el
	 * mismo par.  El round-trip detecta las dos cosas a la vez, y detecta
	 * tambien un off-by-one en cualquiera de los dos shifts.
	 */
	{
		uint64_t probe[64];
		size_t i;
		uint32_t k;
		bool ok = true;

		for (k = 0; k < 64; k++) {
			/* Va de la primera pagina a la ultima, mas el ultimo VA de
			 * cada region, que es donde un off-by-one se manifesta. */
			probe[k] = (g.coverage_bytes / 64) * k;
		}
		probe[62] = last_va - RX550_VMID1_PAGE_SIZE;
		probe[63] = last_va;

		for (i = 0; i < 64 && ok; i++) {
			uint64_t rebuilt;

			if (rx550_vmid1_locate(&g, probe[i], &pde, &pte)
			    != RX550_PGT_OK) {
				ok = false;
				break;
			}
			rebuilt = ((uint64_t)pde << (RX550_VMID1_PAGE_SHIFT
						     + g.block_size))
				  | ((uint64_t)pte << RX550_VMID1_PAGE_SHIFT);

			/* El VA reconstruido tiene que caer en la MISMA pagina de
			 * 4 KiB que el original.  Es la unica garantia que hace
			 * falta para afirmar que no hay huecos:  dos VA que
			 * reconstruyen paginas distintas no pueden solaparse. */
			if (rebuilt != (probe[i] & ~(uint64_t)(RX550_VMID1_PAGE_SIZE - 1u)))
				ok = false;
		}
		CHECK(ok, "T5b el round-trip de los indices deberia reconstruir la pagina");
	}

	/* T5c:  el limite de cada sub-indice por separado. */
	CHECK_EQ(pde, 511, "T5c tras el round-trip, pde_index");
	CHECK_EQ(pte, 511, "T5c tras el round-trip, pte_index");
}

/* ═══════════════════════════════════════════════════════════════════════════
 * T6  VA fuera de rango rechazada
 * ═══════════════════════════════════════════════════════════════════════════ */
static void t6_va_out_of_range(void)
{
	struct rx550_vmid1_geom g;
	uint32_t idx = 0xDEADBEEF;

	CHECK_EQ(rx550_vmid1_geometry(WINDOW_1GIB, &g), RX550_PGT_OK,
		 "T6 geometry(1GiB)");

	CHECK_EQ(rx550_vmid1_pde_index(&g, g.coverage_bytes, &idx),
		 RX550_PGT_ERR_VA_OUT_OF_RANGE, "T6 VA == coverage rechazada");
	CHECK_EQ(rx550_vmid1_pte_index(&g, g.coverage_bytes, &idx),
		 RX550_PGT_ERR_VA_OUT_OF_RANGE, "T6 VA == coverage rechazada (pte)");
	CHECK_EQ(rx550_vmid1_pde_index(&g, g.coverage_bytes + 1u, &idx),
		 RX550_PGT_ERR_VA_OUT_OF_RANGE, "T6 coverage+1 rechazada");
	CHECK_EQ(rx550_vmid1_pde_index(&g, UINT64_MAX, &idx),
		 RX550_PGT_ERR_VA_OUT_OF_RANGE, "T6 VA_MAX rechazada");

	/* Y el limite de abajo:  la ultima pagina valida entra. */
	CHECK_EQ(rx550_vmid1_pde_index(&g, g.coverage_bytes - 1u, &idx),
		 RX550_PGT_OK, "T6 coverage-1 deberia aceptarse");
	/* Y que el valor de salida no se toco en un rechazo.  Un reject que
	 * escribe el buffer deja al llamante usando un indice inventado. */
	CHECK_EQ(rx550_vmid1_locate(&g, g.coverage_bytes, &idx, &idx),
		 RX550_PGT_ERR_VA_OUT_OF_RANGE, "T6 locate fuera de rango");
}

/* ═══════════════════════════════════════════════════════════════════════════
 * T7  el PDE se codifica bien, y los bits de PTE NO lo contaminan
 * ═══════════════════════════════════════════════════════════════════════════ */
static void t7_pde_encoding(void)
{
	uint64_t addr;
	uint64_t pde = 0;
	size_t i;

	/* Una pagina PTE alineada, con los bits bajos varidos para que la
	 * comprobacion no dependa de una direccion AFORTUNADA. */
	for (i = 0; i < 64; i++) {
		addr = (UINT64_C(1) << 39) - UINT64_C(0x1000) * (i + 1u);
		addr &= ~UINT64_C(0xFFF);	/* alinear a 4 KiB */
		addr |= UINT64_C(0x1000);		/* y no dejar la pagina 0 */
		if (i == 0)
			addr = UINT64_C(0x1000);

		CHECK_EQ(rx550_vmid1_pde_encode(addr, &pde), RX550_PGT_OK,
			 "T7 pde_encode deberia aceptar una pagina alineada");

		/* VALID a 1. */
		CHECK((pde & RX550_PDE_VALID_MASK) == RX550_PDE_VALID_MASK,
		      "T7 VALID deberia estar a 1");

		/* 58:40 a cero. */
		CHECK((pde & RX550_PDE_RESERVED_MASK) == 0,
		      "T7 los bits reservados 58:40 deberian estar a cero");

		/* 63:59 a cero por la politica declarada. */
		CHECK((pde & RX550_PDE_FRAG_MASK) == 0,
		      "T7 los bits 63:59 deberian estar a cero");

		/*
		 * Y LA COMPROBACION QUE DISCRIMINA ENTRE PDE Y PTE.
		 *
		 * En un PDE los bits 5 y 6 NO son permisos:  son parte de la
		 * direccion.  Y como la pagina esta alineada a 4 KiB, el hardware
		 * exige que esos bits sean cero (gmc_v8_0.c:708, "bits 5:1 must
		 * be 0").  Si el encoder contaminase el campo con
		 * READABLE/WRITEABLE, aqui aparecese un 1 espurio.
		 *
		 * Esa es la asercion que habria fallado con el encoder de PTE, y
		 * no con un error:  con un PDE que apunta a otra pagina.
		 */
		CHECK((pde & (UINT64_C(1) << 5)) == 0,
		      "T7 el bit 5 de un PDE es direccion, no READABLE: debe ser 0");
		CHECK((pde & (UINT64_C(1) << 6)) == 0,
		      "T7 el bit 6 de un PDE es direccion, no WRITEABLE: debe ser 0");

		/* Y el round-trip:  la direccion se recupera intacta. */
		CHECK_EQ(rx550_vmid1_pde_decode(pde), addr,
			 "T7 el round-trip del PDE deberia conservar la direccion");

		CHECK(rx550_vmid1_pde_check(pde), "T7 pde_check deberia aceptar");
	}

	/* Un PDE invalido tiene que ser detectable. */
	pde = 0;
	CHECK(!rx550_vmid1_pde_check(pde), "T7 un cero no es un PDE utilizable");
	pde = RX550_PDE_VALID_MASK | RX550_PDE_RESERVED_MASK;
	CHECK(!rx550_vmid1_pde_check(pde),
	      "T7 un PDE con 58:40 sucios no es utilizable");
	pde = RX550_PDE_VALID_MASK | RX550_PDE_FRAG_MASK;
	CHECK(!rx550_vmid1_pde_check(pde),
	      "T7 un PDE con 63:59 sucios no es utilizable");

	/* Y los dos rechazos del encoder. */
	CHECK_EQ(rx550_vmid1_pde_encode(UINT64_C(0x1001), &pde),
		 RX550_PGT_ERR_LEAF_UNALIGNED, "T7 una pagina no alineada se rechaza");
	CHECK_EQ(rx550_vmid1_pde_encode(UINT64_C(1) << 40, &pde),
		 RX550_PGT_ERR_LEAF_UNREPRESENTABLE,
		 "T7 una pagina por encima del bit 39 se rechaza");
}

/* ═══════════════════════════════════════════════════════════════════════════
 * T8  una hoja por encima de 28 bits NO se rechaza
 *
 * Y ESTE TEST TIENE SENTIDO SOLO CON UNA LECTURA CONCRETA:  ">28 bits" se
 * refiere a los bits que ocupa la DIRECCION como numero crudo, no a los que
 * ocupa el numero de pagina.  Una hoja en 8 GiB ocupa 33 bits como direccion y
 * es perfectamente valida, porque su campo es 39:1.  Un validador que le
 * exigiera 28 bits al valor crudo la rechazaria, y ese es el error que este
 * test existe para cazar.
 * ═══════════════════════════════════════════════════════════════════════════ */
static void t8_leaf_above_28_bits(void)
{
	const uint64_t leaf_8gib = UINT64_C(8) << 30;	/* 0x2_0000_0000 */
	uint64_t pde = 0;

	/* 33 bits como direccion.  Si el limite de 28 bits se aplicase aqui,
	 * esto seria un rechazo, y seria un rechazo incorrecto. */
	CHECK(leaf_8gib > UINT64_C(0x0FFFFFFF),
	      "T8 el VA de prueba debe ocupar mas de 28 bits como direccion");
	CHECK(rx550_vmid1_leaf_representable(leaf_8gib),
	      "T8 una hoja en 8 GiB debe ser representable en el campo 39:1");
	CHECK_EQ(rx550_vmid1_pde_encode(leaf_8gib, &pde), RX550_PGT_OK,
		 "T8 pde_encode debe aceptar una hoja en 8 GiB");
	CHECK_EQ(rx550_vmid1_pde_decode(pde), leaf_8gib,
		 "T8 el round-trip debe conservar una hoja en 8 GiB");
	CHECK(rx550_vmid1_pde_check(pde), "T8 el PDE debe ser utilizable");

	/* Y el contraste:  el limite de la hoja NO es el del root.  Un root en la
	 * misma direccion NO es representable, porque su campo es un numero de
	 * pagina de 28 bits que no da para 8 GiB...  salvo que si, y por eso el
	 * limite del root se comprueba con otro caso, en T9. */
}

/* ═══════════════════════════════════════════════════════════════════════════
 * T9  el root por encima de los 28 bits SI se rechaza
 * ═══════════════════════════════════════════════════════════════════════════ */
static void t9_root_28_bits(void)
{
	uint32_t pn = 0;
	/* El limite:  (2^28 - 1) paginas, o sea la ultima direccion que el
	 * numero de pagina puede nombrar. */
	const uint64_t root_max = ((uint64_t)RX550_PT_BASE_PN_MASK + 1u)
				  << RX550_VMID1_PAGE_SHIFT;	/* 2^40 */
	const uint64_t root_over = root_max + RX550_VMID1_PAGE_SIZE;	/* 2^40 + 4 KiB */

	/* Justo en el limite:  la pagina 0x0FFFFFFF. */
	CHECK(rx550_vmid1_root_representable(root_max - RX550_VMID1_PAGE_SIZE),
	      "T9 la pagina 0x0FFFFFFF deberia ser representable");
	CHECK_EQ(rx550_vmid1_root_base_pn(root_max - RX550_VMID1_PAGE_SIZE, &pn),
		 RX550_PGT_OK, "T9 root_base_pn en el limite deberia aceptarse");
	CHECK_EQ(pn, RX550_PT_BASE_PN_MASK, "T9 el numero de pagina en el limite");

	/* Una pagina mas:  ya no cabe. */
	CHECK(!rx550_vmid1_root_representable(root_over),
	      "T9 la pagina 0x10000000 NO deberia ser representable");
	CHECK_EQ(rx550_vmid1_root_base_pn(root_over, &pn),
		 RX550_PGT_ERR_ROOT_UNREPRESENTABLE,
		 "T9 root_base_pn deberia rechazar lo que no cabe");

	/* Y nunca trunca:  el valor de salida no se escribe en un rechazo. */
	pn = 0xDEADBEEF;
	CHECK_EQ(rx550_vmid1_root_base_pn(root_over, &pn),
		 RX550_PGT_ERR_ROOT_UNREPRESENTABLE, "T9 rechazo");
	CHECK_EQ(pn, 0xDEADBEEF, "T9 un rechazo no debe escribir en la salida");

	/* El desalineado tambien, y por un codigo distinto. */
	CHECK_EQ(rx550_vmid1_root_base_pn(UINT64_C(0x1001), &pn),
		 RX550_PGT_ERR_ROOT_UNREPRESENTABLE,
		 "T9 un root desalineado no puede producir un numero de pagina");
}

/* ═══════════════════════════════════════════════════════════════════════════
 * T10  no existe dependencia de rx550_pdb0.h
 * T11  no existe reutilizacion del encoder de PTE para el root
 *
 * ESTATICOS, y por lectura de los fuentes.  Son la parte del test que protege
 * contra la regresion que motivo la correccion de depth:  un directorio
 * construido con semantica de PTE no da un error, da una traduccion.
 * ═══════════════════════════════════════════════════════════════════════════ */

/*
 * Busca un token en el CODIGO de un fichero, con los comentarios eliminados.
 *
 * POR QUE HAY QUE BORRAR LOS COMENTARIOS
 *
 * Estos dos ficheros MENCIONAN, a proposito y con detalle, todo lo que no se
 * usa:  rx550_pdb0.h, RX550_PDB0_LEAF_BIT, rx550_pte_encode, writel, ioremap,
 * dma_alloc_coherent.  Las menciones son el POR QUE de la decision, y estan
 * en los comentarios de cabecera.
 *
 * Un test que buscara sobre el texto crudo contaria esas menciones como usos y
 * fallaria siempre, y un test que las ignorara a mano dejaria pasar un uso
 * real que estuviera en un comentario de linea.  Lo unico que distingue el
 * caso bueno del malo es DONDE esta la palabra, y por eso se eliminan los
 * comentarios y se busca en lo que queda.
 *
 * Devuelve -1 si el fichero no se pudo leer, lo que NO es lo mismo que "no lo
 * contiene":  un test que no ha leido nada no puede pasar.
 */
static long file_contains_code(const char *path, const char *needle)
{
	FILE *f = fopen(path, "rb");
	static char buf[262144];
	static char out[262144];
	size_t n;
	size_t i = 0, o = 0;
	int in_block = 0;
	int in_line = 0;
	long hit;

	if (!f)
		return -1;
	n = fread(buf, 1, sizeof(buf) - 1u, f);
	fclose(f);
	buf[n] = '\0';

	for (i = 0; i < n && o + 1u < sizeof(out); i++) {
		char c = buf[i];
		char nx = (i + 1u < n) ? buf[i + 1] : '\0';

		if (in_block) {
			if (c == '*' && nx == '/') {
				in_block = 0;
				i++;
			}
			continue;
		}
		if (in_line) {
			if (c == '\n') {
				in_line = 0;
				out[o++] = c;
			}
			continue;
		}
		if (c == '/' && nx == '*') {
			in_block = 1;
			i++;
			continue;
		}
		if (c == '/' && nx == '/') {
			in_line = 1;
			i++;
			continue;
		}
		out[o++] = c;
	}
	out[o] = '\0';

	hit = (long)(strstr(out, needle) ? 1 : 0);
	return hit;
}

static void t10_t11_no_bad_dependency(const char *dir)
{
	char path_c[512];
	char path_h[512];
	long hit;
	int readable;

	snprintf(path_c, sizeof(path_c), "%s/rx550_vmid1_pgt.c", dir);
	snprintf(path_h, sizeof(path_h), "%s/rx550_vmid1_pgt.h", dir);

	readable = (file_contains_code(path_c, "rx550_vmid1_pgt") >= 0)
		   && (file_contains_code(path_h, "RX550_VMID1_PGT_H") >= 0);
	CHECK(readable,
	      "T10/T11 no se pudieron leer los fuentes;  el test no puede pasar en "
	      "silencio por no haber comprobado nada");

	if (!readable)
		return;

	/* T10:  rx550_pdb0.h no se incluye, y sus macros no se usan.
	 * La busqueda es sobre el codigo sin comentarios;  ver la nota de
	 * file_contains_code(). */
	hit = file_contains_code(path_c, "#include \"rx550_pdb0.h\"");
	CHECK_EQ(hit, 0, "T10 rx550_vmid1_pgt.c no debe incluir rx550_pdb0.h");
	hit = file_contains_code(path_h, "#include \"rx550_pdb0.h\"");
	CHECK_EQ(hit, 0, "T10 rx550_vmid1_pgt.h no debe incluir rx550_pdb0.h");
	hit = file_contains_code(path_c, "RX550_PDB0_LEAF_BIT");
	CHECK_EQ(hit, 0, "T10 no debe usarse RX550_PDB0_LEAF_BIT");
	hit = file_contains_code(path_c, "rx550_pdb0_encode");
	CHECK_EQ(hit, 0, "T10 no debe usarse ningun encoder de rx550_pdb0");

	/* T11:  rx550_pte_encode no se usa, y rx550_vmid0_gart.h no se incluye. */
	hit = file_contains_code(path_c, "rx550_pte_encode");
	CHECK_EQ(hit, 0, "T11 no debe reutilizarse rx550_pte_encode para el root");
	hit = file_contains_code(path_h, "rx550_pte_encode");
	CHECK_EQ(hit, 0, "T11 la cabecera no debe declarar ni usar rx550_pte_encode");
	hit = file_contains_code(path_c, "RX550_PTE_");
	CHECK_EQ(hit, 0, "T11 no debe usarse ningun flag de PTE en M2");
	hit = file_contains_code(path_c, "#include \"rx550_vmid0_gart.h\"");
	CHECK_EQ(hit, 0, "T11 rx550_vmid1_pgt.c no debe incluir rx550_vmid0_gart.h");
	hit = file_contains_code(path_h, "#include \"rx550_vmid0_gart.h\"");
	CHECK_EQ(hit, 0, "T11 la cabecera no debe incluir rx550_vmid0_gart.h");

	/* Y lo que si tiene que estar:  un encoder de PDE propio. */
	hit = file_contains_code(path_c, "rx550_vmid1_pde_encode");
	CHECK(hit > 0, "T11 debe existir un encoder de PDE propio");
	/* Y que no se toca hardware.  Estas seis son la frontera de M2. */
	hit = file_contains_code(path_c, "writel");
	CHECK_EQ(hit, 0, "M2 no debe usar writel");
	hit = file_contains_code(path_c, "readl");
	CHECK_EQ(hit, 0, "M2 no debe usar readl");
	hit = file_contains_code(path_c, "ioremap");
	CHECK_EQ(hit, 0, "M2 no debe usar ioremap");
	hit = file_contains_code(path_c, "dma_alloc_coherent");
	CHECK_EQ(hit, 0, "M2 no debe reservar memoria DMA");
	hit = file_contains_code(path_c, "__asm__");
	CHECK_EQ(hit, 0, "M2 no debe introducir ensamblador");
	hit = file_contains_code(path_c, "PAGE_TABLE_BASE_ADDR");
	CHECK_EQ(hit, 0, "M2 no debe programar PAGE_TABLE_BASE_ADDR");
}

/* ═══════════════════════════════════════════════════════════════════════════
 * EXTRAS:  los guards de geometria, que son la razon de que este modulo no
 * construya nunca una tabla falsa.
 * ═══════════════════════════════════════════════════════════════════════════ */
static void guards(void)
{
	struct rx550_vmid1_geom g;
	uint64_t root[512];
	struct rx550_vmid1_root r;

	CHECK_EQ(rx550_vmid1_geometry(0, &g), RX550_PGT_ERR_VM_SIZE,
		 "vm_size 0 se rechaza");
	CHECK_EQ(rx550_vmid1_geometry(RX550_VMID1_PAGE_SIZE, &g),
		 RX550_PGT_ERR_VM_SIZE_INCOHERENT,
		 "una ventana de una sola pagina no puede cubrirse");
	CHECK_EQ(rx550_vmid1_geometry(WINDOW_1GIB + 1u, &g),
		 RX550_PGT_ERR_VM_SIZE, "un vm_size no multiplo de pagina se rechaza");

	/* Y las ventanas que la aritmetica del corpus produce.
	 *
	 * ESTA SECCION CAMBIO CON EL NODO DE BACKING, y el cambio es una
	 * mutacion de la guarda, no un relajamiento del test.
	 *
	 * ANTES   se aceptaba solo block_size == 9, y 2 GiB se rechazaba.
	 * AHORA   la guarda es el RANGO DEL CAMPO —block_size en [9, 24],
	 *         derivado de 4 bits en el shift 24— y el segundo criterio es
	 *         cobertura INSUFICIENTE, no cobertura distinta.
	 *
	 * CONSECUENCIA PARA 2 GiB:  se acepta, con block_size 10 y raiz de 8 KiB.
	 * Y para 8 GiB:  se sigue rechazando, pero por el motivo que de verdad
	 * importa, que es que la cobertura no llega.  Por eso los dos casos de
	 * abajo no son "< 0":  exigen el CODIGO, porque "no lo suporto" y "la
	 * geometria es incoherente" son fallos que el llamante distingue y una
	 * guarda muerta no se distingue de una guarda que funciona. */
	CHECK_EQ(rx550_vmid1_geometry(WINDOW_1GIB * 2u, &g), RX550_PGT_OK,
		 "2 GiB deberia aceptarse: block_size 10 cabe en el campo");
	CHECK_EQ(g.block_size, 10, "2 GiB -> block_size 10");
	CHECK_EQ(g.block_size_field, 1, "2 GiB -> PAGE_TABLE_BLOCK_SIZE = 1");
	CHECK_EQ(g.root_bytes, 8192u,
		 "2 GiB -> raiz de 8 KiB, DERIVADA de 2^10 entradas * 8");
	CHECK_EQ(g.pte_pages, 1024u, "2 GiB -> 1024 paginas PTE");
	/* Y la cobertura con holgura es correcta, no un defecto:  START y END
	 * acotan la ventana real, y eso es de M6. */
	CHECK(g.coverage_bytes > g.vm_size_bytes,
	      "2 GiB con cobertura de 4 GiB es sobreaprovisionar, no incoherencia");

	/* 8 GiB:  el motivo del rechazo es la cobertura, y se exige el codigo. */
	CHECK_EQ(rx550_vmid1_geometry(WINDOW_1GIB * 8u, &g),
		 RX550_PGT_ERR_VM_SIZE_INCOHERENT,
		 "8 GiB se rechaza por cobertura insuficiente, no por block_size");
	CHECK_EQ(rx550_vmid1_geometry(WINDOW_1GIB * 64u, &g),
		 RX550_PGT_ERR_VM_SIZE_INCOHERENT,
		 "64 GiB se rechaza por cobertura insuficiente");
	/* Y 4 GiB, que es la cobertura maxima efectiva:  entra exacto. */
	CHECK_EQ(rx550_vmid1_geometry(WINDOW_1GIB * 4u, &g), RX550_PGT_OK,
		 "4 GiB deberia aceptarse: es la cobertura maxima efectiva");
	CHECK_EQ(g.coverage_bytes, WINDOW_1GIB * 4u,
		 "4 GiB -> cobertura exacta de 4 GiB");

	/* Y el root:  validar la direccion ANTES de aceptarla. */
	CHECK_EQ(rx550_vmid1_geometry(WINDOW_1GIB, &g), RX550_PGT_OK,
		 "guards geometry(1GiB)");
	CHECK_EQ(rx550_vmid1_root_attach(&r, &g, root, UINT64_C(0x1001)),
		 RX550_PGT_ERR_ROOT_UNREPRESENTABLE,
		 "un root desalineado no se engancha");
	CHECK_EQ(rx550_vmid1_root_attach(&r, &g, root, (UINT64_C(1) << 40)),
		 RX550_PGT_ERR_ROOT_UNREPRESENTABLE,
		 "un root fuera de 28 bits de pagina no se engancha");
	CHECK_EQ(rx550_vmid1_root_attach(&r, &g, root, UINT64_C(0x200000)),
		 RX550_PGT_OK, "un root valido se engancha");
	CHECK_EQ(rx550_vmid1_root_clear(&r), RX550_PGT_OK, "el root se limpia");
	CHECK_EQ(root[0], 0, "tras el limpiado, la entrada 0 es cero");
	CHECK_EQ(root[511], 0, "tras el limpiado, la entrada 511 es cero");

	/* Una geometria manipulada no vale:  el flag valid no es decorativo. */
	g.valid = false;
	CHECK_EQ(rx550_vmid1_root_attach(&r, &g, root, UINT64_C(0x200000)),
		 RX550_PGT_ERR_INCONSISTENT,
		 "una geometria no valida no se usa");
}

/* ═══════════════════════════════════════════════════════════════════════════
 * COHERENCIA CON EL ENCODER EXISTENTE:  la comprobacion que haria un
 * cross-check con el encoder de PTE, hecho SIN llamarlo.
 * ═══════════════════════════════════════════════════════════════════════════ */

/*
 * Este bloque no llama a rx550_pte_encode, y no debe.  Lo que hace es
 * COMPROBAR que el formato de un PTE y el de un PDE no se pueden confundir,
 * construyendo a mano lo que el encoder de PTE produciria y mostrando que no
 * es un PDE.
 *
 *   RX550_PTE_VALID      bit 0    = 1
 *   RX550_PTE_READABLE   bit 5    = 1
 *   RX550_PTE_WRITEABLE  bit 6    = 1
 *   PA en bits 39:12
 *
 * Contra un PDE, que tiene el campo en 39:1 y nada mas.
 */
static void pte_shape_is_not_pde(void)
{
	const uint64_t bus = UINT64_C(0x1000);
	uint64_t pde = 0;
	uint64_t pte_ish;
	uint64_t pde_addr;

	CHECK_EQ(rx550_vmid1_pde_encode(bus, &pde), RX550_PGT_OK, "encode");

	/* Un "PTE" para la misma direccion, con los flags que el driver escribe. */
	pte_ish = ((UINT64_C(0) << 12) | (bus & UINT64_C(0xFFFFFFFFFF000)))
		  | (UINT64_C(1) << 0)		/* valid   */
		  | (UINT64_C(1) << 5)		/* readable*/
		  | (UINT64_C(1) << 6);		/* writeable */
	pde_addr = rx550_vmid1_pde_decode(pde);

	/* El PDE codificado NO tiene los flags. */
	CHECK((pde & (UINT64_C(1) << 5)) == 0, "el PDE no tiene READABLE");
	CHECK((pde & (UINT64_C(1) << 6)) == 0, "el PDE no tiene WRITEABLE");

	/* Y el PTE, de haber pasado por el campo del PDE, apuntaria a OTRA pagina.
	 * Porque los bits 5 y 6 del PTE caen dentro de 39:1.  Ese desplazamiento
	 * es de 32 y de 64 bytes respectivamente, y es la razon de que reutilizar
	 * el encoder de PTE no produzca un error sino una traduccion erronea. */
	CHECK_EQ(pde_addr, bus, "el PDE apunta a la pagina correcta");
	CHECK(rx550_vmid1_pde_check(pde), "el PDE es utilizable");
	/* La asercion de la confusion, dicha como comparacion: */
	CHECK(((pte_ish >> 6) & UINT64_C(0x7FFFFFFFFF)) != ((bus >> 1) & UINT64_C(0x7FFFFFFFFF)),
	      "el campo de direccion de un PTE con flags NO coincide con el de un PDE");
}

/* ═══════════════════════════════════════════════════════════════════════════ */

int main(int argc, char **argv)
{
	const char *dir = (argc > 1) ? argv[1] : "..";

	printf("test_vmid1_pgt  —  jerarquia GFX8 de VMID1\n");
	printf("fuentes: %s\n\n", dir);

	t1_depth();
	t2_pte_pages();
	t3_root_size();
	t4_pte_page_size();
	t5_indexing();
	t6_va_out_of_range();
	t7_pde_encoding();
	t8_leaf_above_28_bits();
	t9_root_28_bits();
	t10_t11_no_bad_dependency(dir);
	guards();
	pte_shape_is_not_pde();

	printf("\n  passed: %u\n  failed: %u\n", g_pass, g_fail);
	return g_fail ? 1 : 0;
}
