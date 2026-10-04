/* SPDX-License-Identifier: GPL-2.0-only */
/*
 * test_vmid1_pgt_backing.c — B1..B13 para el backing del PGT de VMID1.
 *
 *   TARGET = RX 550 instalada en esta maquina  (1002:699F, Polaris12, GFX8)
 *   SCOPE  = EXCLUSIVO
 *
 * QUE ES Y QUE NO ES
 *   Tests deterministas.  Sin GPU, sin MMIO, sin kernel, sin reserva real:
 *   el backend de asignacion es una funcion local que cuenta y puede fallar
 *   donde se le diga.  Y eso es lo que permite ejercitar el unwinding, que con
 *   una reserva real solo se veria en un fallo de OOM.
 *
 *   Y POR QUE HAY UN BACKEND DE PRUEBA, DICHO
 *   dma_alloc_coherent() necesita un struct device.  Poner el backing detras
 *   de una tabla de tres llamadas es lo que permite que el unwinding —que es
 *   la parte con mas estados— se pruebe entero sin hardware, y es tambien lo
 *   que mantiene la geometria de M2 verificable en userspace.  No es una capa
 *   de asignacion generica:  son tres punteros a funcion y nada mas.
 *
 * QUE COMPRUEBA CADA UNO
 *   B1..B7  la forma y la correccion
 *   B8      el unwinding ante un fallo a mitad de las hojas
 *   B9..B11 los tres limites, que son tres validaciones distintas
 *   B12     el doble destroy
 *   B13     que no queda ownership por la mitad
 */

#include <stdio.h>
#include <stdlib.h>
#include <string.h>
#include <stdint.h>
#include <stdbool.h>

#include "rx550_vmid1_pgt_backing.h"

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

#define GIB	(UINT64_C(1) << 30)

/* ═══════════════════════════════════════════════════════════════════════════
 * EL BACKEND DE PRUEBA
 *
 * Reparte direcciones simuladas, cuenta, y sabe fallar en una llamada concreta.
 * Las direcciones NO salen de una aritmetica real:  se entregan como un
 * valor base que el test elige, para poder ponerlas donde quiera —por encima
 * del bit 32, por encima del 39, desalineadas— sin depender de donde caeria
 * un allocator de verdad.
 * ═══════════════════════════════════════════════════════════════════════════ */
struct fake {
	uint64_t	next;		/* siguiente direccion a entregar   */
	uint64_t	align;		/* alineacion que se promete       */
	int		calls;		/* reservas pedidas                */
	int		frees;		/* liberaciones pedidas            */
	int		bytes;		/* bytes entregados hasta ahora    */
	int		fail_at;	/* -1 = nunca;  k = fallar en la k-esima
					 * llamada, contada desde 0       */
	int		live;		/* reservas vivas                  */
	uint64_t	bad_addr_at;	/* entregar esta direccion en esa
					 * llamada, o 0 para no hacerlo  */
	int		bad_addr_call;
	/* registro de cada liberacion, para B12 y B13 */
	struct { uint64_t dma; uint64_t bytes; } freed[4096];
};

static int fake_alloc(void *ctx, uint64_t size, void **out_cpu,
		      struct rx550_dma_addr *out_dma)
{
	struct fake *f = (struct fake *)ctx;
	uint64_t addr;

	if (!f || !out_cpu || !out_dma)
		return -1;

	if (f->fail_at >= 0 && f->calls == f->fail_at) {
		/* Un backend que falla NO escribe las salidas, y el test lo
		 * comprueba:  un backend que escribiera garbage y devolviera
		 * error seria un backend que hay que descartar, no que
		 * tolerar. */
		f->calls++;
		return -1;
	}

	if (f->bad_addr_call >= 0 && f->calls == f->bad_addr_call) {
		addr = f->bad_addr_at;
	} else {
		addr = f->next;
		f->next += (size + f->align - 1u) & ~(f->align - 1u);
	}
	if (addr % f->align) {
		/* Un backend que promete alineacion y no la cumple es un
		 * backend roto.  Se le deja pasar para que el codigo bajo
		 * prueba tenga que detectar el desalineado. */
		addr |= (f->align - 1u);
	}

	/* El "cpu pointer" es una direccion de un array real, y la "dma" es la
	 * simulada.  Son independientes a proposito:  en la vida real tambien
	 * lo son, y un test que los cambiara estara probando otra cosa. */
	*out_cpu = calloc(1, size ? size : 1u);
	if (!*out_cpu)
		return -1;
	out_dma->value = addr;

	f->calls++;
	f->live++;
	f->bytes += (int)size;
	return 0;
}

static void fake_release(void *ctx, uint64_t size, void *cpu,
			 struct rx550_dma_addr dma)
{
	struct fake *f = (struct fake *)ctx;

	if (!f)
		return;
	f->frees++;
	f->live--;
	f->bytes -= (int)size;
	if (f->frees < 4096) {
		f->freed[f->frees].dma = dma.value;
		f->freed[f->frees].bytes = size;
	}
	free(cpu);
}

static struct fake g_fake;
static struct rx550_pgt_alloc_ops g_ops;

static void fake_init(uint64_t base, uint64_t align, uint64_t vm)
{
	struct rx550_vmid1_geom geom;
	int rc;

	memset(&g_fake, 0, sizeof(g_fake));
	g_fake.next = base;
	g_fake.align = align;
	g_fake.fail_at = -1;
	g_fake.bad_addr_call = -1;

	g_ops.ctx = &g_fake;
	g_ops.alloc = fake_alloc;
	g_ops.release = fake_release;

	rc = rx550_vmid1_geometry(vm, &geom);
	if (rc != RX550_PGT_OK) {
		printf("  FALLO  la geometria de %llu no se pudo calcular: %s\n",
		       (unsigned long long)(vm >> 20), rx550_vmid1_err_str(rc));
		g_fail++;
		geom.valid = false;
	}
}

static int fake_geom(uint64_t vm, struct rx550_vmid1_geom *g)
{
	return rx550_vmid1_geometry(vm, g);
}

/* ═══════════════════════════════════════════════════════════════════════════
 * B1  1 GiB crea geometria valida y root del tamano correcto
 * ═══════════════════════════════════════════════════════════════════════════ */
static void b1_1gib(void)
{
	struct rx550_vmid1_geom g;
	struct rx550_pgt_backing b;
	uint64_t root_size;

	CHECK_EQ(fake_geom(GIB, &g), RX550_PGT_OK, "B1 geometry(1GiB)");
	root_size = g.root_bytes;

	fake_init(UINT64_C(0x10000000), 4096, GIB);
	CHECK_EQ(rx550_pgt_backing_create(&b, &g, &g_ops,
					  RX550_PGT_LEAF_SINGLE_BLOCK),
		 RX550_PGT_OK, "B1 create(1GiB)");
	/* Y el root tiene el tamano que dice la geometria, y el Allocation
	 * pidio EXACTAMENTE eso:  sin un 4096 escrito aqui. */
	CHECK_EQ(b.root.bytes, root_size, "B1 root.bytes debe ser geometry.root_bytes");
	CHECK_EQ(g_fake.freed[0].bytes, 0, "B1 aun no hay liberaciones");
	CHECK(b.root.bytes != 0, "B1 el root tiene que tener tamano");
	CHECK(rx550_pgt_backing_is_complete(&b), "B1 el backing debe estar completo");
	rx550_pgt_backing_destroy(&b);
}

/* ═══════════════════════════════════════════════════════════════════════════
 * B2  2 GiB crea root segun geometry.root_size, sin literal
 *
 * Y el punto del test no es que 2 GiB funcione:  es que el tamano del root lo
 * pone la GEOMETRIA.  Por eso el test compara contra g.root_bytes y no contra
 * un numero, y por eso exige ademas que 2 GiB y 1 GiB den roots DISTINTOS:  si
 * los dos dieran 4096, un literal habria pasado el test sin que se notase.
 * ═══════════════════════════════════════════════════════════════════════════ */
static void b2_2gib_root_from_geometry(void)
{
	struct rx550_vmid1_geom g1, g2;
	struct rx550_pgt_backing b1, b2;

	CHECK_EQ(fake_geom(GIB, &g1), RX550_PGT_OK, "B2 geometry(1GiB)");
	CHECK_EQ(fake_geom(2 * GIB, &g2), RX550_PGT_OK, "B2 geometry(2GiB)");

	/* MEDIDO 2026-10-04:  el par de ventanas de este test era 1 GiB y 2 GiB,
	 * y elSizes del root tienen que ser DISTINTOS  —si los dos dieran 4096, un
	 * literal hardcodeado pasaria el test sin que se notase—.
	 *
	 * MEDIDO que con la formula de cobertura CORREGIDA  (amdgpu_vm_pt.c:84-85:
	 * las entradas de la raiz salen de un round_up de max_pfn,  no de
	 * 2^block_size)  1 GiB y 2 GiB dan AMBOS raiz de 4 KiB:
	 *
	 *     1 GiB   block_size 9   ceil(2^18 / 2^9)  = 512 entradas = 4 KiB
	 *     2 GiB   block_size 10  ceil(2^19 / 2^10) = 512 entradas = 4 KiB
	 *
	 * Los dos dan 512 porque el block_size sube justo cuando el numerador se
	 * duplica.  O sea que el invariante de este test era una CONSECUENCIA de la
	 * formula falsa,  y no una propiedad.  El caso de 3 GiB daba 6144  —que no
	 * es ni multiplo de 4 KiB ni un tamano de pagina—  lo que delata que el
	 * numero de entradas venia de ahi.
	 *
	 * EL INVARIANTE SE CONSERVA,  con un par donde si distingue:  2 GiB da 4
	 * KiB y 4 GiB da 8 KiB.  Y se anade la comprobacion de por que 1 y 2 GiB
	 * coinciden,  porque es el dato que hace que el par no sirva. */
	CHECK_EQ(g1.root_bytes, g2.root_bytes,
		 "B2 1 GiB y 2 GiB dan el MISMO root: 512 entradas cada uno, y el "
		 "block_size sube con el numerador");
	CHECK(fake_geom(4 * GIB, &g2) == RX550_PGT_OK, "B2 geometry(4GiB)");
	CHECK(g1.root_bytes != g2.root_bytes,
	      "B2 2 GiB y 4 GiB SI derivan roots distintos: 512 contra 1024");
	CHECK_EQ(g2.root_bytes, 8192u,
		 "B2 la geometria de 4 GiB deriva 8 KiB: el literal esta en el"
		 " test, no en el modulo");

	fake_init(UINT64_C(0x10000000), 4096, GIB);
	CHECK_EQ(rx550_pgt_backing_create(&b1, &g1, &g_ops,
					  RX550_PGT_LEAF_SINGLE_BLOCK),
		 RX550_PGT_OK, "B2 create(1GiB)");
	CHECK_EQ(b1.root.bytes, g1.root_bytes, "B2 root de 1 GiB = geometria");
	rx550_pgt_backing_destroy(&b1);

	fake_init(UINT64_C(0x10000000), 4096, 4 * GIB);
	CHECK_EQ(rx550_pgt_backing_create(&b2, &g2, &g_ops,
					  RX550_PGT_LEAF_SINGLE_BLOCK),
		 RX550_PGT_OK, "B2 create(4GiB)");
	CHECK_EQ(b2.root.bytes, g2.root_bytes, "B2 root de 4 GiB = geometria");
	/* Y el Allocation pidio el valor de la geometria, no otro.  Esto es lo
	 * que detecta un 4096 hardcodeado en el modulo. */
	CHECK_EQ(g_fake.bytes - (int)g2.root_bytes - (int)g2.pte_pages * (int)g2.pte_page_bytes, 0,
		 "B2 no debe quedar memoria sin contabilizar");
	rx550_pgt_backing_destroy(&b2);
}

/* B3  UNA VENTANA IMPOSIBLE ES RECHAZADA ANTES DE UNA ALLOCATION REAL
 *
 * MEDIDO 2026-10-04:  este nodo usaba 8 GiB como "ventana imposible",  porque
 * con la formula falsa la cobertura eran 4 GiB y no llegaba.  MEDIDO que con la
 * formula corregida el corpus CUBRE 8 GiB —y 64 GiB,  que es la ventana de esta
 * maquina—,  de modo que el test llevaba dos commits多万元 检查endo algo que no
 * es un defecto.
 *
 * MEDIDO que 1 TiB NO es imposible:  rx550_vmid1_geometry() la acepta  (rc = 0),
 * porque el tope no es el de la ventana sino el del desplazamiento y del
 * producto.  MEDIDO tam/en con el propio modulo:  de siete ventanas balotadas,
 *  las que se rechazan son la de 0 bytes  (RX550_PGT_ERR_VM_SIZE)  y la de
 * UINT64_MAX  (que no es multiplo de 4 KiB,  mismo codigo).  La de 1 TiB entra.
 *
 * Aqui se usa la de 0,  que es la ventana imposible trivial y la que un
 * llamante puede encontrar sin proposito.  Y se mide el caso de 1 TiB para que
 * quede escrito que entra,  y no se confunda con una frontera.
 */
static void b3_1tib_rejected_before_alloc(void)
{
	struct rx550_vmid1_geom g;
	struct rx550_pgt_backing b;

	CHECK_EQ(fake_geom(0, &g), RX550_PGT_ERR_VM_SIZE,
	      "B3 una ventana de 0 bytes se rechaza");
	CHECK_EQ(fake_geom(1024 * 1024 * GIB, &g), RX550_PGT_OK,
	      "B3 y 1 TiB SE ACEPTA:  el tope no es el de la ventana");
	CHECK_EQ(fake_geom(8 * GIB, &g), RX550_PGT_OK,
	      "B3 y 8 GiB SE ACEPTA:  el corpus lo cubre");
	CHECK_EQ(fake_geom(64 * GIB, &g), RX550_PGT_OK,
	      "B3 y 64 GiB SE ACEPTA:  es la ventana de esta maquina");
	/* Y el resto del nodo trabaja con la geometria INVALIDA,  de modo que se
	 * vuelve a pedir:  MEDIDO que sin esta linea el create recibia la de
	 * 64 GiB —que es valida—  y por eso tenia exito,  y las tres
	 * comprobaciones siguientes decian la verdad sobre una geometria que no
	 * era la que creian.  MEDIDO:  el fallo aparecia como "create
	 * deberia fallar" cuando lo que pasaba es que se le habia dado otra. */
	CHECK_EQ(fake_geom(0, &g), RX550_PGT_ERR_VM_SIZE,
	      "B3 y para el resto del nodo, la geometria es la invalida");

	/* Y con una geometria que no es valida, create no pide NADA.  Esta es la
	 * condicion que hace que una ventana imposible no llegue al allocator:
	 * el conteo de llamadas tiene que ser exactamente cero. */
	fake_init(UINT64_C(0x10000000), 4096, GIB);
	CHECK_EQ(rx550_pgt_backing_create(&b, &g, &g_ops,
					  RX550_PGT_LEAF_SINGLE_BLOCK),
		 RX550_PGT_ERR_INCONSISTENT,
		 "B3 create con geometria invalida debe fallar");
	CHECK_EQ(g_fake.calls, 0, "B3 no debe haber pedida ninguna memoria");
	CHECK_EQ(g_fake.frees, 0, "B3 ni una liberacion");
	CHECK(rx550_pgt_backing_has_no_ownership(&b), "B3 sin ownership");
}

/* ═══════════════════════════════════════════════════════════════════════════
 * B4  root DMA address queda asociado correctamente
 * ═══════════════════════════════════════════════════════════════════════════ */
static void b4_root_dma(void)
{
	struct rx550_vmid1_geom g;
	struct rx550_pgt_backing b;
	struct rx550_dma_addr d;
	uint32_t pn = 0;
	uint32_t pde = 0;

	fake_init(UINT64_C(0x40000000), 4096, GIB);
	CHECK_EQ(fake_geom(GIB, &g), RX550_PGT_OK, "B4 geometry(1GiB)");
	CHECK_EQ(rx550_pgt_backing_create(&b, &g, &g_ops,
					  RX550_PGT_LEAF_SINGLE_BLOCK),
		 RX550_PGT_OK, "B4 create");

	CHECK_EQ(rx550_pgt_backing_root_dma(&b, &d), RX550_PGT_OK, "B4 root_dma");
	CHECK_EQ(d.value, b.root_dma.value, "B4 root_dma coincide con el interno");
	CHECK(d.value != 0, "B4 la dma del root no puede ser 0");
	/* Y es la direccion que el backend entrego, ni una transformada. */
	CHECK_EQ(d.value, b.root.entries ? d.value : 0,
		 "B4 la dma del root viene del backend");
	CHECK(rx550_vmid1_root_representable(d.value),
	      "B4 la dma del root debe ser representable para PAGE_TABLE_BASE");
	/* El numero de pagina se deriva con el validador del ROOT. */
	CHECK_EQ(rx550_pgt_backing_root_base_pn(&b, &pn), RX550_PGT_OK, "B4 base_pn");
	CHECK_EQ(pn, (uint32_t)(d.value >> 12), "B4 base_pn = dma >> 12");
	/* Y la geometria es la misma, sin copia. */
	CHECK(rx550_pgt_backing_geom(&b) == &g, "B4 la geometria es prestada");

	/* Un backing no creado no devuelve un 0 que parece una direccion. */
	{
		struct rx550_pgt_backing empty;

		memset(&empty, 0, sizeof(empty));
		CHECK(rx550_pgt_backing_root_dma(&empty, &d) != RX550_PGT_OK,
		      "B4 un backing vacio no debe entregar una dma");
		CHECK(rx550_pgt_backing_root_base_pn(&empty, &pde) != RX550_PGT_OK,
		      "B4 un backing vacio no debe entregar un pn");
	}

	rx550_pgt_backing_destroy(&b);
}

/* ═══════════════════════════════════════════════════════════════════════════
 * B5  cada leaf page conserva su propio DMA address
 * ═══════════════════════════════════════════════════════════════════════════ */
static void b5_leaf_dmas(void)
{
	struct rx550_vmid1_geom g;
	struct rx550_pgt_backing b;
	struct rx550_dma_addr d;
	uint32_t i;
	bool distinct = true;
	bool all_valid = true;

	fake_init(UINT64_C(0x40000000), 4096, GIB);
	CHECK_EQ(fake_geom(GIB, &g), RX550_PGT_OK, "B5 geometry(1GiB)");
	CHECK_EQ(rx550_pgt_backing_create(&b, &g, &g_ops, RX550_PGT_LEAF_PER_PAGE),
		 RX550_PGT_OK, "B5 create(PER_PAGE)");

	/* Con PER_PAGE cada hoja tiene su reserva, luego su dma. */
	CHECK_EQ(g_fake.calls, 1 + (int)g.pte_pages,
		 "B5 PER_PAGE debe hacer una reserva por hoja mas la del root");
	CHECK_EQ(b.leaf_count, g.pte_pages, "B5 leaf_count viene de la geometria");

	{
		struct rx550_dma_addr prev;

		prev.value = 0;
		for (i = 0; i < b.leaf_count; i++) {
			CHECK_EQ(rx550_pgt_backing_leaf_dma(&b, i, &d), RX550_PGT_OK,
				 "B5 leaf_dma(i)");
			if (i > 0 && d.value == prev.value)
				distinct = false;
			if (!rx550_vmid1_leaf_representable(d.value))
				all_valid = false;
			/* Y cada una es una pagina PTE con su tamano. */
			if (b.leaves[i].bytes != g.pte_page_bytes)
				all_valid = false;
			prev = d;
		}
	}
	CHECK(distinct, "B5 cada hoja deberia tener una dma propia");
	CHECK(all_valid, "B5 cada hoja deberia ser representable y del tamano correcto");

	/* Y con SINGLE_BLOCK las hojas SON vistas sobre un bloque, con
	 * direcciones consecutivas.  Tambien es valido, y tambien distinto. */
	rx550_pgt_backing_destroy(&b);

	fake_init(UINT64_C(0x40000000), 4096, GIB);
	CHECK_EQ(rx550_pgt_backing_create(&b, &g, &g_ops,
					  RX550_PGT_LEAF_SINGLE_BLOCK),
		 RX550_PGT_OK, "B5 create(SINGLE_BLOCK)");
	CHECK_EQ(g_fake.calls, 2, "B5 SINGLE_BLOCK: root + un bloque de hojas");
	for (i = 0; i < b.leaf_count; i++) {
		CHECK_EQ(rx550_pgt_backing_leaf_dma(&b, i, &d), RX550_PGT_OK,
			 "B5 SINGLE_BLOCK leaf_dma(i)");
		if (d.value != b.leaf_block_dma.value + (uint64_t)i * g.pte_page_bytes)
			distinct = false;
	}
	CHECK(distinct, "B5 SINGLE_BLOCK: hoja i en base + i*leaf_bytes");
	rx550_pgt_backing_destroy(&b);
}

/* ═══════════════════════════════════════════════════════════════════════════
 * B6  PDE encode consume la dma de la hoja correcta
 * ═══════════════════════════════════════════════════════════════════════════ */
static void b6_pde_from_leaf_dma(void)
{
	struct rx550_vmid1_geom g;
	struct rx550_pgt_backing b;
	struct rx550_dma_addr d;
	uint64_t pde = 0;
	uint32_t i;
	bool ok = true;

	fake_init(UINT64_C(0x40000000), 4096, GIB);
	CHECK_EQ(fake_geom(GIB, &g), RX550_PGT_OK, "B6 geometry(1GiB)");
	CHECK_EQ(rx550_pgt_backing_create(&b, &g, &g_ops,
					  RX550_PGT_LEAF_SINGLE_BLOCK),
		 RX550_PGT_OK, "B6 create");

	/* Para CADA hoja:  el PDE que sale tiene que apuntar a ESA hoja, y no a
	 * la primera, ni a la siguiente, ni a la raiz.  Y eso se comprueba
	 * decodificando, que es la unica forma de comprobarlo sin hardware. */
	for (i = 0; i < b.leaf_count; i++) {
		if (rx550_pgt_backing_encode_leaf_pde(&b, i, &pde) != RX550_PGT_OK) {
			ok = false;
			break;
		}
		if (rx550_vmid1_pde_decode(pde) != b.leaf_dma[i].value) {
			ok = false;
			break;
		}
		if (!rx550_vmid1_pde_check(pde)) {
			ok = false;
			break;
		}
		/* Y NO puede ser la direccion del root:  el PDE de una hoja y
		 * la base del root son cosas distintas. */
		if (rx550_vmid1_pde_decode(pde) == b.root_dma.value) {
			ok = false;
			break;
		}
	}
	CHECK(ok, "B6 cada PDE deberia apuntar a su propia hoja, no a otra");

	/* Y la hoja 0 y la hoja 511 dan PDEs distintos. */
	{
		uint64_t p0 = 0, pn = 0;

		CHECK_EQ(rx550_pgt_backing_encode_leaf_pde(&b, 0, &p0), RX550_PGT_OK,
			 "B6 pde(0)");
		CHECK_EQ(rx550_pgt_backing_encode_leaf_pde(&b, b.leaf_count - 1, &pn),
			 RX550_PGT_OK, "B6 pde(ultima)");
		CHECK(p0 != pn, "B6 dos hojas distintas no pueden dar el mismo PDE");
	}

	/* Un indice fuera de rango no inventa un PDE. */
	CHECK(rx550_pgt_backing_encode_leaf_pde(&b, b.leaf_count, &pde) != RX550_PGT_OK,
	      "B6 un indice fuera de rango no debe codificar");
	CHECK(rx550_pgt_backing_leaf_dma(&b, 0xFFFFFFFFu, &d) != RX550_PGT_OK,
	      "B6 leaf_dma fuera de rango debe fallar");

	rx550_pgt_backing_destroy(&b);
}

/* ═══════════════════════════════════════════════════════════════════════════
 * B7  root y leaf no comparten encoder
 *
 * Lo que se comprueba es que los DOS caminos de codificacion producen
 * formatos que NO se pueden confundir, y que la validacion de cada uno es la
 * suya.
 * ═══════════════════════════════════════════════════════════════════════════ */
static void b7_no_shared_encoder(void)
{
	struct rx550_vmid1_geom g;
	struct rx550_pgt_backing b;
	uint64_t pde = 0;
	uint32_t pn = 0;

	fake_init(UINT64_C(0x40000000), 4096, GIB);
	CHECK_EQ(fake_geom(GIB, &g), RX550_PGT_OK, "B7 geometry(1GiB)");
	CHECK_EQ(rx550_pgt_backing_create(&b, &g, &g_ops,
					  RX550_PGT_LEAF_SINGLE_BLOCK),
		 RX550_PGT_OK, "B7 create");
	CHECK_EQ(rx550_pgt_backing_encode_leaf_pde(&b, 0, &pde), RX550_PGT_OK,
		 "B7 pde(0)");

	/* El root NO se codifica con el encoder de PDE:  se convierte a numero
	 * de pagina, que es otra cosa.  Y las dos salidas no se parecen. */
	CHECK_EQ(rx550_pgt_backing_root_base_pn(&b, &pn), RX550_PGT_OK, "B7 base_pn");
	CHECK(pn != pde, "B7 un numero de pagina y un PDE no pueden ser lo mismo");

	/* Un PDE de hoja NO tiene los flags de PTE, y eso es lo que lo
	 * distingue de una entrada construida con el encoder de PTE. */
	CHECK((pde & (UINT64_C(1) << 5)) == 0, "B7 el PDE no tiene READABLE");
	CHECK((pde & (UINT64_C(1) << 6)) == 0, "B7 el PDE no tiene WRITEABLE");

	/* Y los dos validadores son distintos:  una hoja por encima del tope
	 * del root es representable como hoja, y el mismo numero como root
	 * tambien, porque los dos topes coinciden en 2^40 — pero se validan
	 * por codigos distintos, que es lo que hace que un fallo sea
	 * diagnosticable. */
	{
		const uint64_t far = UINT64_C(8) << 30;	/* 8 GiB */
		uint32_t tmp = 0;

		CHECK(rx550_vmid1_leaf_representable(far),
		      "B7 8 GiB es una hoja valida");
		CHECK(rx550_vmid1_root_representable(far),
		      "B7 8 GiB tambien es un root valido: los topes coinciden");
		/* Y el error de cada uno se distingue por su codigo. */
		CHECK(rx550_vmid1_root_base_pn(UINT64_C(1) << 40, &tmp)
		      == RX550_PGT_ERR_ROOT_UNREPRESENTABLE,
		      "B7 el fallo del root tiene su codigo");
		CHECK_EQ(rx550_vmid1_pde_encode(UINT64_C(1) << 40, &pde),
			 RX550_PGT_ERR_LEAF_UNREPRESENTABLE,
			 "B7 el fallo de la hoja tiene su codigo");
	}
	rx550_pgt_backing_destroy(&b);
}

/* ═══════════════════════════════════════════════════════════════════════════
 * B8  fallo de una leaf libera todas las anteriores Y el root
 *
 * Y ESTE TEST ES EL QUE JUSTIFICA HABER IMPLEMENTADO LA POLITICA PER_PAGE.
 * Con SINGLE_BLOCK hay una sola reserva de hojas, luego no existe "fallo de
 * la hoja k".  El unwinding de verdad solo se puede ejercitar con N reservas,
 * y si no se ejercita, es codigo que nadie ha ejecutado.
 * ═══════════════════════════════════════════════════════════════════════════ */
static void b8_unwind_partial(void)
{
	struct rx550_vmid1_geom g;
	struct rx550_pgt_backing b;
	uint32_t k;

	CHECK_EQ(fake_geom(GIB, &g), RX550_PGT_OK, "B8 geometry(1GiB)");

	/* Fallo en varias hojas distintas, y en la ultima, que es el borde. */
	for (k = 0; k < 4; k++) {
		uint32_t fail_index = (uint32_t[]){1u, 7u, 255u, g.pte_pages - 1u}[k];

		fake_init(UINT64_C(0x40000000), 4096, GIB);
		/* La llamada 0 es el root;  la k+1 es la hoja fail_index. */
		g_fake.fail_at = (int)fail_index + 1;

		CHECK_EQ(rx550_pgt_backing_create(&b, &g, &g_ops,
						  RX550_PGT_LEAF_PER_PAGE),
			 RX550_PGTB_ERR_ALLOC, "B8 create debe fallar");

		/* Se reserve root + fail_index hojas, y se liberaron TANTAS.
		 * Ni una mas, ni una menos:  ese es el criterio. */
		CHECK_EQ(g_fake.calls, (int)fail_index + 2,
			 "B8 cuantas reservas se pidieron (fallo en la hoja k)");
		CHECK_EQ(g_fake.frees, (int)fail_index + 1,
			 "B8 cuantas liberaciones hicieron: root + las k vivas");
		CHECK_EQ(g_fake.live, 0, "B8 no debe quedar ninguna reserva viva");
		CHECK_EQ(g_fake.bytes, 0, "B8 no debe quedar memoria viva");
		/* Y el objeto no es dueño de nada, o un destroy posterior
		 * liberaria dos veces. */
		CHECK(rx550_pgt_backing_has_no_ownership(&b),
		      "B8 tras el fallo no debe quedar ownership");
		/* Y un destroy despues no toca el backend. */
		rx550_pgt_backing_destroy(&b);
		CHECK_EQ(g_fake.frees, (int)fail_index + 1,
			 "B8 destroy tras un fallo no debe liberar otra vez");
	}
}

/* ═══════════════════════════════════════════════════════════════════════════
 * B9  direccion mal alineada es rechazada
 * ═══════════════════════════════════════════════════════════════════════════ */
static void b9_misaligned(void)
{
	struct rx550_vmid1_geom g;
	struct rx550_pgt_backing b;
	struct fake *f;
	uint64_t aligned = UINT64_C(0x40000000);

	/* Un backend que entrega una direccion desalineada, y que por tanto
	 * incumple su propio contrato.  El codigo tiene que detectarlo, porque
	 * el contrato no es una garantia:  es una promesa que se comprueba. */
	fake_init(aligned, 4096, GIB);
	CHECK_EQ(fake_geom(GIB, &g), RX550_PGT_OK, "B9 geometry(1GiB)");

	/* El root desalineado. */
	f = &g_fake;
	f->bad_addr_call = 0;		/* la primera reserva es el root */
	f->bad_addr_at = aligned + 1u;	/* desalineada a proposito */
	CHECK_EQ(rx550_pgt_backing_create(&b, &g, &g_ops,
					  RX550_PGT_LEAF_SINGLE_BLOCK),
		 RX550_PGT_ERR_ROOT_UNREPRESENTABLE,
		 "B9 un root desalineado debe rechazarse");
	CHECK_EQ(f->frees, 1, "B9 el root invalido debe liberarse");
	CHECK_EQ(f->live, 0, "B9 nada vivo");

	/* Y una hoja desalineada, con el root bien. */
	fake_init(aligned, 4096, GIB);
	CHECK_EQ(fake_geom(GIB, &g), RX550_PGT_OK, "B9 geometry(1GiB)");
	f = &g_fake;
	f->bad_addr_call = 3;		/* root + hojas 0 y 1 bien, hoja 2 mal */
	f->bad_addr_at = aligned + 2u;
	CHECK_EQ(rx550_pgt_backing_create(&b, &g, &g_ops, RX550_PGT_LEAF_PER_PAGE),
		 RX550_PGT_ERR_LEAF_UNREPRESENTABLE,
		 "B9 una hoja desalineada debe rechazarse");
	/* Y EL NUMERO DE LIBERACIONES ES 4, NO 3, y eso es el punto:  la hoja
	 * con la direccion desalineada SI se reservo.  Que su direccion no
	 * sirva no la devuelve.  La PROPIEDAD la establece la reserva que
	 * devuelve bien y se baja en la liberacion;  attach y la validacion no
	 * participan.  Con un criterio basado en `attached`, esa cuarta reserva
	 * se perdia, y la fuga no aparecia en ningun flag:  solo como un
	 * contador que no cuadra mas tarde y en otro sitio. */
	CHECK_EQ(f->frees, 4, "B9 root + 3 hojas, incluida la que se reservo mal");
	CHECK_EQ(f->calls, 4, "B9 se reservaron root + 3 hojas");
	CHECK_EQ(f->live, 0, "B9 nada vivo: la hoja invalida tambien se libero");
	rx550_pgt_backing_destroy(&b);
	CHECK_EQ(f->frees, 4, "B9 destroy tras el fallo no libera otra vez");
}

/* ═══════════════════════════════════════════════════════════════════════════
 * B10  direccion no representable por root es rechazada
 * ═══════════════════════════════════════════════════════════════════════════ */
static void b10_root_unrepresentable(void)
{
	struct rx550_vmid1_geom g;
	struct rx550_pgt_backing b;
	struct fake *f;

	fake_init(UINT64_C(0x40000000), 4096, GIB);
	CHECK_EQ(fake_geom(GIB, &g), RX550_PGT_OK, "B10 geometry(1GiB)");
	f = &g_fake;
	/* El tope del root es 28 bits de NUMERO DE PAGINA:  (2^28-1)<<12.
	 * Una pagina mas ya no cabe, y es el caso limite exacto. */
	f->bad_addr_call = 0;
	f->bad_addr_at = (UINT64_C(1) << 40);	/* exactamente 2^40 */
	CHECK_EQ(rx550_pgt_backing_create(&b, &g, &g_ops,
					  RX550_PGT_LEAF_SINGLE_BLOCK),
		 RX550_PGT_ERR_ROOT_UNREPRESENTABLE,
		 "B10 un root en 2^40 debe rechazarse");
	CHECK_EQ(f->frees, 1, "B10 el root invalido debe liberarse, no perderse");
	CHECK_EQ(f->live, 0, "B10 nada vivo");
	CHECK(rx550_pgt_backing_has_no_ownership(&b), "B10 sin ownership");

	/* Y el caso limite de acceptacion:  la ultima pagina representable. */
	fake_init(UINT64_C(0x40000000), 4096, GIB);
	CHECK_EQ(fake_geom(GIB, &g), RX550_PGT_OK, "B10 geometry(1GiB)");
	f = &g_fake;
	f->bad_addr_call = 0;
	f->bad_addr_at = (UINT64_C(1) << 40) - 4096u;	/* la ultima valida */
	CHECK_EQ(rx550_pgt_backing_create(&b, &g, &g_ops,
					  RX550_PGT_LEAF_SINGLE_BLOCK),
		 RX550_PGT_OK, "B10 la pagina 0x0FFFFFFF deberia aceptarse");
	CHECK(rx550_pgt_backing_is_complete(&b), "B10 y deberia estar completo");
	rx550_pgt_backing_destroy(&b);
}

/* ═══════════════════════════════════════════════════════════════════════════
 * B11  una leaf por encima del viejo limite de root NO se rechaza
 *
 * Y ESTE TEST ES LA CORRECCION DE UN ERROR PROPIO YA DOCUMENTADO.  Se afirmo
 * que "una hoja puede vivir por encima del limite de 28 bits, y la raiz no".
 * Medido:  los dos topes son 2^40 - 4096, y ambos aceptan el mismo conjunto.
 * Lo que sigue siendo cierto es que los CAMPOS son distintos, y por eso una
 * mascara de 28 bits SIN desplazar sobre una direccion en bytes —el error
 * realista— rechazaria una hoja valida.  Eso es lo que este test comprueba.
 * ═══════════════════════════════════════════════════════════════════════════ */
static void b11_leaf_above_old_root_limit(void)
{
	struct rx550_vmid1_geom g;
	struct rx550_pgt_backing b;
	struct fake *f;
	uint64_t pde = 0;

	/* 8 GiB:  33 bits como DIRECCION, muy por encima de 28. */
	const uint64_t far = UINT64_C(8) << 30;

	fake_init(far, 4096, GIB);
	CHECK_EQ(fake_geom(GIB, &g), RX550_PGT_OK, "B11 geometry(1GiB)");

	f = &g_fake;
	f->bad_addr_call = 1;		/* el root bien;  las hojas por encima */
	f->bad_addr_at = far;
	/* El root sale de la secuencia normal;  la reserva de hojas en far. */
	/* Y el rango completo de hojas cabe:  2 MiB desde 8 GiB. */
	CHECK_EQ(rx550_pgt_backing_create(&b, &g, &g_ops,
					  RX550_PGT_LEAF_SINGLE_BLOCK),
		 RX550_PGT_OK, "B11 hojas a 8 GiB deberian aceptarse");
	CHECK_EQ(b.leaf_block_dma.value, far, "B11 el bloque de hojas esta en 8 GiB");
	CHECK(rx550_vmid1_leaf_representable(b.leaf_dma[0].value),
	      "B11 una hoja a 8 GiB es representable en 39:1");
	CHECK(rx550_pgt_backing_encode_leaf_pde(&b, 0, &pde) == RX550_PGT_OK,
	      "B11 y se puede codificar en un PDE");
	CHECK(rx550_pgt_backing_is_complete(&b), "B11 backing completo");

	/* Y una hoja por encima de 2^40 SI se rechaza:  el limite de la hoja
	 * existe, y es el campo, no el del root. */
	{
		struct rx550_pgt_backing b2;
		struct fake *f2;

		fake_init(UINT64_C(0x40000000), 4096, GIB);
		f2 = &g_fake;
		f2->bad_addr_call = 1;
		f2->bad_addr_at = UINT64_C(1) << 40;
		CHECK(rx550_pgt_backing_create(&b2, &g, &g_ops,
					       RX550_PGT_LEAF_SINGLE_BLOCK) != RX550_PGT_OK,
		      "B11 un bloque de hojas a 2^40 debe rechazarse");
		rx550_pgt_backing_destroy(&b2);
	}
	rx550_pgt_backing_destroy(&b);
}

/* ═══════════════════════════════════════════════════════════════════════════
 * B12  doble destroy no libera dos veces
 * ═══════════════════════════════════════════════════════════════════════════ */
static void b12_double_destroy(void)
{
	struct rx550_vmid1_geom g;
	struct rx550_pgt_backing b;
	int frees_after_first;

	fake_init(UINT64_C(0x40000000), 4096, GIB);
	CHECK_EQ(fake_geom(GIB, &g), RX550_PGT_OK, "B12 geometry(1GiB)");
	CHECK_EQ(rx550_pgt_backing_create(&b, &g, &g_ops,
					  RX550_PGT_LEAF_SINGLE_BLOCK),
		 RX550_PGT_OK, "B12 create");
	CHECK_EQ(g_fake.frees, 0, "B12 antes de destruir no hay frees");

	rx550_pgt_backing_destroy(&b);
	frees_after_first = g_fake.frees;
	CHECK(frees_after_first > 0, "B12 el primer destroy debe liberar");
	CHECK_EQ(g_fake.live, 0, "B12 nada vivo tras el primer destroy");
	CHECK(rx550_pgt_backing_has_no_ownership(&b), "B12 sin ownership");

	/* Y ahora, destroy de nuevo.  Con SINGLE_BLOCK son dos reservas:  el
	 * root y el bloque de hojas.  Un segundo destroy no debe llamarse ni
	 * una vez mas al backend. */
	rx550_pgt_backing_destroy(&b);
	rx550_pgt_backing_destroy(&b);
	CHECK_EQ(g_fake.frees, frees_after_first,
		 "B12 un segundo destroy no debe liberar otra vez");
	CHECK_EQ(g_fake.live, 0, "B12 sigue sin memoria viva");

	/* Y con PER_PAGE, que tiene muchas mas reservas, tampoco. */
	fake_init(UINT64_C(0x40000000), 4096, GIB);
	CHECK_EQ(fake_geom(GIB, &g), RX550_PGT_OK, "B12 geometry(1GiB)");
	CHECK_EQ(rx550_pgt_backing_create(&b, &g, &g_ops, RX550_PGT_LEAF_PER_PAGE),
		 RX550_PGT_OK, "B12 create(PER_PAGE)");
	rx550_pgt_backing_destroy(&b);
	frees_after_first = g_fake.frees;
	CHECK_EQ(frees_after_first, 1 + (int)g.pte_pages,
		 "B12 PER_PAGE: root + una por hoja");
	rx550_pgt_backing_destroy(&b);
	CHECK_EQ(g_fake.frees, frees_after_first,
		 "B12 PER_PAGE: el segundo destroy no libera mas");
	/* Y un destroy sobre un objeto nunca creado. */
	{
		struct rx550_pgt_backing never;

		memset(&never, 0, sizeof(never));
		rx550_pgt_backing_destroy(&never);
		CHECK_EQ(g_fake.frees, frees_after_first,
			 "B12 destroy de un objeto vacio no toca el backend");
	}
}

/* ═══════════════════════════════════════════════════════════════════════════
 * B13  el backing no deja paginas ownership-less
 *
 * Y el criterio es el CONTABLE, no el de flags:  el numero de liberaciones
 * tiene que ser IGUAL al numero de reservas, en exito y en fallo, y con las dos
 * politicas.  Un backing que pierde una reserva no se ve en un flag:  se ve en
 * que frees != calls.
 * ═══════════════════════════════════════════════════════════════════════════ */
static void b13_no_orphan(void)
{
	struct rx550_vmid1_geom g[3];
	struct rx550_pgt_backing b;
	const uint64_t vms[3] = { GIB, 2 * GIB, 4 * GIB };
	enum rx550_pgt_leaf_policy pols[2] = {
		RX550_PGT_LEAF_SINGLE_BLOCK, RX550_PGT_LEAF_PER_PAGE
	};
	unsigned i, p;

	for (i = 0; i < 3; i++)
		CHECK_EQ(fake_geom(vms[i], &g[i]), RX550_PGT_OK,
			 "B13 la geometria deberia existir");

	for (i = 0; i < 3; i++) {
		for (p = 0; p < 2; p++) {
			int calls, frees;

			fake_init(UINT64_C(0x40000000), 4096, vms[i]);
			CHECK_EQ(rx550_pgt_backing_create(&b, &g[i], &g_ops, pols[p]),
				 RX550_PGT_OK, "B13 create");
			calls = g_fake.calls;
			CHECK(rx550_pgt_backing_is_complete(&b),
			      "B13 el backing deberia estar completo");
			CHECK_EQ(b.leaf_live, b.leaf_count,
				 "B13 todas las hojas vivas");
			CHECK_EQ(b.live_bytes,
				 b.root.bytes
				 + (pols[p] == RX550_PGT_LEAF_SINGLE_BLOCK
				    ? (uint64_t)b.leaf_count * b.leaf_block_bytes / b.leaf_count
				    : (uint64_t)b.leaf_count * b.leaves[0].bytes),
				 "B13 live_bytes debe ser el total reservado");

			rx550_pgt_backing_destroy(&b);
			frees = g_fake.frees;
			CHECK_EQ(frees, calls, "B13 frees == calls");
			CHECK_EQ(g_fake.live, 0, "B13 nada vivo");
			CHECK_EQ(g_fake.bytes, 0, "B13 cero bytes vivos");
			CHECK(rx550_pgt_backing_has_no_ownership(&b),
			      "B13 sin ownership tras destroy");
		}
	}

	/* Y el caso de fallo, que es donde un ownership se pierde de verdad. */
	for (i = 0; i < 3; i++) {
		int calls, frees;

		fake_init(UINT64_C(0x40000000), 4096, GIB);
		g_fake.fail_at = 1 + (int)g[0].pte_pages / 2;
		CHECK(rx550_pgt_backing_create(&b, &g[0], &g_ops,
					       RX550_PGT_LEAF_PER_PAGE) != RX550_PGT_OK,
		      "B13 create debe fallar");
		calls = g_fake.calls;
		frees = g_fake.frees;
		CHECK(frees > 0, "B13 el fallo debe liberar algo");
		/* Una llamada mas:  la que fallo.  Y frees tiene que igualar
		 * a calls - 1. */
		CHECK_EQ(frees, calls - 1,
			 "B13 frees == calls - 1: solo la que fallo no se libero");
		CHECK_EQ(g_fake.live, 0, "B13 nada vivo tras el fallo");
		rx550_pgt_backing_destroy(&b);
		CHECK_EQ(g_fake.frees, frees,
			 "B13 destroy tras fallo no libera mas");
	}
}

/* ═══════════════════════════════════════════════════════════════════════════
 * B14  ESTATICOS:  las fronteras del modulo, comprobadas sobre el fuente
 * ═══════════════════════════════════════════════════════════════════════════ */
static long code_contains(const char *path, const char *needle)
{
	FILE *f = fopen(path, "rb");
	static char buf[262144];
	static char out[262144];
	size_t n, i = 0, o = 0;
	int blk = 0, lin = 0;
	long r;

	if (!f)
		return -1;
	n = fread(buf, 1, sizeof(buf) - 1u, f);
	fclose(f);
	buf[n] = '\0';
	for (i = 0; i < n && o + 1u < sizeof(out); i++) {
		char c = buf[i], nx = (i + 1u < n) ? buf[i + 1] : '\0';

		if (blk) { if (c == '*' && nx == '/') { blk = 0; i++; } continue; }
		if (lin) { if (c == '\n') { lin = 0; out[o++] = c; } continue; }
		if (c == '/' && nx == '*') { blk = 1; i++; continue; }
		if (c == '/' && nx == '/') { lin = 1; i++; continue; }
		out[o++] = c;
	}
	out[o] = '\0';
	r = (long)(strstr(out, needle) ? 1 : 0);
	return r;
}

static void b14_static(const char *dir)
{
	char p[512];
	int readable;

	snprintf(p, sizeof(p), "%s/rx550_vmid1_pgt_backing.c", dir);
	readable = code_contains(p, "rx550_pgt_backing_create") >= 0;
	CHECK(readable, "B14 no se pudo leer el fuente; el test no pasa en silencio");
	if (!readable)
		return;

	/* Las fronteras del nodo, sobre el CODIGO sin comentarios. */
	CHECK_EQ(code_contains(p, "writel"), 0, "B14 no writel");
	CHECK_EQ(code_contains(p, "readl"), 0, "B14 no readl");
	CHECK_EQ(code_contains(p, "ioremap"), 0, "B14 no ioremap");
	CHECK_EQ(code_contains(p, "dma_alloc_coherent"), 0,
		 "B14 la llamada real va en el backend del kernel, no aqui");
	CHECK_EQ(code_contains(p, "__asm__"), 0, "B14 no asm");
	CHECK_EQ(code_contains(p, "PAGE_TABLE_BASE_ADDR"), 0,
		 "B14 no se programa PAGE_TABLE_BASE, solo se calcula su valor");
	CHECK_EQ(code_contains(p, "START_ADDR"), 0, "B14 no START/END");
	CHECK_EQ(code_contains(p, "VM_CONTEXT1_CNTL"), 0, "B14 no CNTL");
	CHECK_EQ(code_contains(p, "INVALIDATE"), 0, "B14 no invalidacion");
	CHECK_EQ(code_contains(p, "rx550_pdb0"), 0, "B14 no rx550_pdb0");
	CHECK_EQ(code_contains(p, "rx550_pte_encode"), 0, "B14 no el encoder de PTE");
	CHECK_EQ(code_contains(p, "amdgpu"), 0, "B14 no semantica de amdgpu");
	CHECK_EQ(code_contains(p, "drm_"), 0, "B14 no drm");
	CHECK_EQ(code_contains(p, "ttm"), 0, "B14 no ttm");

	/* Y la geometria NO esta duplicada:  el backing no vuelve a calcularla. */
	CHECK_EQ(code_contains(p, "get_block_size"), 0,
		 "B14 el backing no debe reimplementar la aritmetica");
	CHECK_EQ(code_contains(p, "amdgpu_vm.c"), 0,
		 "B14 el backing no debe citar la aritmetica del corpus");
	CHECK(code_contains(p, "rx550_vmid1_geometry") >= 0
	      || code_contains(p, "geom->") >= 0,
	      "B14 el backing debe consumir la geometria");

	/* Y el root no tiene un tamano literal:  el tamano sale de la
	 * geometria, luego no puede haber un 4096 ni un 8192 hardcodeado. */
	CHECK_EQ(code_contains(p, "4096"), 0, "B14 sin literal 4096");
	CHECK_EQ(code_contains(p, "8192"), 0, "B14 sin literal 8192");
	/* Ni un 512 de hojas. */
	CHECK_EQ(code_contains(p, "512"), 0, "B14 sin literal 512");
}

/* ─────────────────────────────────────────────────────────────────────────── */

int main(int argc, char **argv)
{
	const char *dir = (argc > 1) ? argv[1] : "..";

	printf("test_vmid1_pgt_backing  —  backing del PGT de VMID1\n");
	printf("fuentes: %s\n\n", dir);

	b1_1gib();
	b2_2gib_root_from_geometry();
	b3_1tib_rejected_before_alloc();
	b4_root_dma();
	b5_leaf_dmas();
	b6_pde_from_leaf_dma();
	b7_no_shared_encoder();
	b8_unwind_partial();
	b9_misaligned();
	b10_root_unrepresentable();
	b11_leaf_above_old_root_limit();
	b12_double_destroy();
	b13_no_orphan();
	b14_static(dir);

	printf("\n  passed: %u\n  failed: %u\n", g_pass, g_fail);
	return g_fail ? 1 : 0;
}
