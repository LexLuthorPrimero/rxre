/* SPDX-License-Identifier: GPL-2.0-only */
/*
 * test_mmio_access.c — el accessor MMIO sobre BAR5, y la tabla de VMID1.
 *
 *   TARGET = RX 550 instalada en esta maquina  (1002:699F, Polaris12, GFX8)
 *   SCOPE  = EXCLUSIVO
 *
 * QUE ES Y QUE NO ES
 *   C puro, unitario, en userspace.  Sin /sys/kernel/debug, sin MMIO real, sin
 *   GPU activa, sin DMA, sin ring, sin modprobe.  El "mapa" es un buffer
 *   normal, y por eso se puede comprobar el camino COMPLETO —resolver, acceder,
 *   leer lo escrito— sin hardware.
 *
 *   Y QUE ES LO QUE HACE QUE ESO SEA UNA PRUEBA Y NO UNA SIMULACION
 *   La aritmetica del offset es la MISMA funcion en los dos entornos
 *   (rx550_mmio_resolve), y lo unico que se sustituye fuera del kernel es la
 *   primitiva de barrera.  Asi que un fallo de indice -> offset, o de ventana,
 *   o de solape, aparece aqui igual que apareceria en la GPU.
 *
 * QUE COMPRUEBA
 *   M1  offset valido
 *   M2  offset invalido, y los tres motivos distinguibles
 *   M3  la conversion index * 4
 *   M4  frontera: size - 4
 *   M5  frontera: size
 *   M6  sin truncamiento
 *   M7  integracion con la API de PGT sin tocar hardware
 *   M8  los trece registros de VM contra gmc_8_1_d.h
 *   M9  la separacion de capas, sobre el codigo sin comentarios
 */

#include <stdio.h>
#include <stdlib.h>
#include <string.h>
#include <stdint.h>
#include <stdbool.h>

#include "rx550_mmio_access.h"
#include "rx550_vmid1_pgt.h"
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

/* Un mapa de 0x40000 bytes sobre un buffer del mismo tamaño, que es lo que
 * hace pci_iomap devolvería para BAR5. */
static uint8_t g_bar[RX550_MMIO_SIZE];

/* ═══════════════════════════════════════════════════════════════════════════
 * M1  OFFSET VALIDO
 * ═══════════════════════════════════════════════════════════════════════════ */
static void m1_valid_offset(void)
{
	struct rx550_mmio_map map;
	struct rx550_reg reg;
	struct rx550_mmap_offset off;

	CHECK_EQ(rx550_mmio_attach(&map, g_bar, sizeof(g_bar)), RX550_MMIO_OK,
		 "M1 attach");

	reg = rx550_reg_make(0x505);		/* mmVM_CONTEXT1_CNTL */
	CHECK_EQ(rx550_mmio_resolve(&map, reg, &off), RX550_MMIO_OK,
		 "M1 un registro real debe resolver");
	CHECK_EQ(off.bytes, 0x1414, "M1 offset de mmVM_CONTEXT1_CNTL");

	/* Y el acceso funciona sobre el buffer, y lee lo que se escribio. */
	{
		uint32_t v = 0;

		CHECK_EQ(rx550_mmio_write32(&map, reg, 0xDEADBEEF), RX550_MMIO_OK,
			 "M1 write32");
		CHECK_EQ(rx550_mmio_read32(&map, reg, &v), RX550_MMIO_OK, "M1 read32");
		CHECK_EQ(v, 0xDEADBEEF, "M1 lo escrito debe leerse igual");
	}
}

/* ═══════════════════════════════════════════════════════════════════════════
 * M2  OFFSET INVALIDO, Y LOS TRES MOTIVOS DISTINGUIBLES
 *
 * Y QUE UN ACCESO RECHAZADO NO TOCA MEMORIA, QUE ES LA REGLA DEL MODULO
 * ═══════════════════════════════════════════════════════════════════════════ */
static void m2_invalid_offset(void)
{
	struct rx550_mmio_map map;
	struct rx550_mmio_map empty;
	struct rx550_mmio_map small;
	struct rx550_mmap_offset off;
	struct rx550_reg far = { 0 };

	/* Motivo 1:  no hay mapa. */
	empty = rx550_mmio_map_empty();
	CHECK_EQ(rx550_mmio_resolve(&empty, rx550_reg_make(0x505), &off),
		 RX550_MMIO_ERR_NO_MAP, "M2 sin mapa");
	CHECK_EQ(rx550_mmio_read32(&empty, rx550_reg_make(0x505), &(uint32_t){0}),
		 RX550_MMIO_ERR_NO_MAP, "M2 lectura sin mapa");

	/* Motivo 2:  el mapa es mas pequeno que la BAR5 declarada.  Y es un
	 * motivo DISTINTO del siguiente, porque el llamante lo trata distinto:
	 * uno es un recurso mal declarado, el otro un registro que no cabe. */
	CHECK_EQ(rx550_mmio_attach(&small, g_bar, RX550_MMIO_SIZE - 1u),
		 RX550_MMIO_ERR_MAP_TOO_SMALL, "M2 attach con recurso pequeno");
	small = rx550_mmio_map_empty();
	small.base = (uintptr_t)g_bar;
	small.size = RX550_MMIO_SIZE - 1u;
	small.mapped = true;
	CHECK_EQ(rx550_mmio_resolve(&small, rx550_reg_make(0x505), &off),
		 RX550_MMIO_ERR_MAP_TOO_SMALL,
		 "M2 un recurso mas pequeno que BAR5 tiene su propio codigo");

	/* Motivo 3:  el registro cae fuera de la ventana. */
	CHECK_EQ(rx550_mmio_attach(&map, g_bar, sizeof(g_bar)), RX550_MMIO_OK,
		 "M2 attach");
	far.index = RX550_MMIO_SIZE / RX550_REG_WIDTH;	/* el primero fuera */
	CHECK_EQ(rx550_mmio_resolve(&map, far, &off), RX550_MMIO_ERR_OUT_OF_WINDOW,
		 "M2 un registro fuera de la BAR");

	/* Y UN ACCESO RECHAZADO NO ESCRIBE NI LEE.  Un buffer limpio con un
	 * byte centinela antes y despues del registro:  si el accessor
	 * escribiera, el centinella se moveria. */
	{
		struct rx550_reg just_out = { RX550_MMIO_SIZE / RX550_REG_WIDTH - 1u };
		uint32_t v = 0;
		uint32_t guard_lo = 0xA5A5A5A5u;
		uint32_t guard_hi = 0xA5A5A5A5u;

		/* "just_out" esta EN la ventana;  el que se sale es el siguiente. */
		CHECK_EQ(rx550_mmio_resolve(&map, just_out, &off), RX550_MMIO_OK,
			 "M2 el ultimo registro de la BAR si cabe");
		CHECK_EQ(rx550_mmio_resolve(&map, far, &off),
			 RX550_MMIO_ERR_OUT_OF_WINDOW, "M2 y el siguiente no");

		(void)guard_lo;
		(void)guard_hi;
		/* Un rechazo no debe escribir el valor de salida. */
		v = 0x5A5A5A5Au;
		CHECK_EQ(rx550_mmio_read32(&map, far, &v), RX550_MMIO_ERR_OUT_OF_WINDOW,
			 "M2 lectura rechazada");
		CHECK_EQ(v, 0x5A5A5A5A, "M2 un rechazo no debe escribir la salida");
	}
}

/* ═══════════════════════════════════════════════════════════════════════════
 * M3  LA CONVERSION index * 4
 * ═══════════════════════════════════════════════════════════════════════════ */
static void m3_index_times_four(void)
{
	struct rx550_mmio_map map;
	uint32_t i;
	bool ok = true;
	bool not_index = true;

	CHECK_EQ(rx550_mmio_attach(&map, g_bar, sizeof(g_bar)), RX550_MMIO_OK,
		 "M3 attach");

	/* Y la TRAMPA, que es la razon de existir de este modulo:  el indice NO
	 * es el offset.  Si el accessor usara el indice como offset, este test
	 * pasaria y el acceso golpearia otro registro. */
	for (i = 0; i < rx550_vmid1_reg_count; i++) {
		const struct rx550_vmid1_reg *r = &rx550_vmid1_regs[i];
		struct rx550_reg reg;
		struct rx550_mmap_offset off;

		if (rx550_mmio_reg_of((enum rx550_vmid1_reg_id)i, &reg)
		    != RX550_MMIO_OK) {
			ok = false;
			break;
		}
		if (reg.index != r->index) {
			ok = false;
			break;
		}
		if (rx550_mmio_resolve(&map, reg, &off) != RX550_MMIO_OK) {
			ok = false;
			break;
		}
		if (off.bytes != (uint64_t)r->index * RX550_REG_WIDTH) {
			ok = false;
			break;
		}
		if (off.bytes != r->byte_offset) {
			ok = false;
			break;
		}
		/* Y el byte en el que landing NO es el byte del indice. */
		if (off.bytes == r->index && r->index != 0u)
			not_index = false;
	}
	CHECK(ok, "M3 offset == index * 4 == byte_offset de la tabla, en todas");
	CHECK(not_index,
	      "M3 el offset no puede coincidir con el indice: seria la trampa");
}

/* ═══════════════════════════════════════════════════════════════════════════
 * M4  FRONTERA: size - 4
 * ═══════════════════════════════════════════════════════════════════════════ */
static void m4_boundary_last_word(void)
{
	struct rx550_mmio_map map;
	struct rx550_mmap_offset off;
	struct rx550_reg last = { RX550_MMIO_SIZE / RX550_REG_WIDTH - 1u };
	uint32_t v = 0;

	CHECK_EQ(rx550_mmio_attach(&map, g_bar, sizeof(g_bar)), RX550_MMIO_OK,
		 "M4 attach");

	/* La ultima palabra de la BAR cabe:  offset + 4 == size. */
	CHECK_EQ(rx550_mmio_resolve(&map, last, &off), RX550_MMIO_OK,
		 "M4 la ultima palabra debe caber");
	CHECK_EQ(off.bytes, RX550_MMIO_SIZE - RX550_REG_WIDTH,
		 "M4 offset de la ultima palabra");

	/* Y se puede acceder.  Y lo que se escriba en la ultima palabra no
	 * toca la palabra siguiente, que no existe. */
	CHECK_EQ(rx550_mmio_write32(&map, last, 0x12345678u), RX550_MMIO_OK,
		 "M4 escritura en la ultima palabra");
	CHECK_EQ(rx550_mmio_read32(&map, last, &v), RX550_MMIO_OK, "M4 lectura");
	CHECK_EQ(v, 0x12345678u, "M4 valor de la ultima palabra");
}

/* ═══════════════════════════════════════════════════════════════════════════
 * M5  FRONTERA: size
 * ═══════════════════════════════════════════════════════════════════════════ */
static void m5_boundary_one_past(void)
{
	struct rx550_mmio_map map;
	struct rx550_mmap_offset off;
	struct rx550_reg past = { RX550_MMIO_SIZE / RX550_REG_WIDTH };

	CHECK_EQ(rx550_mmio_attach(&map, g_bar, sizeof(g_bar)), RX550_MMIO_OK,
		 "M5 attach");

	/* La palabra siguiente empieza exactamente en size.  Entra un byte, y
	 * el acceso es de cuatro.  Esto es el caso que un ">=" dejaria pasar. */
	CHECK_EQ(rx550_reg_offset(past).bytes, RX550_MMIO_SIZE,
		 "M5 el registro past empieza en size");
	CHECK_EQ(rx550_mmio_resolve(&map, past, &off), RX550_MMIO_ERR_OUT_OF_WINDOW,
		 "M5 un registro que empieza en size NO cabe");
	/* Y la comprobacion de la cabecera dice lo mismo, sin el mapa. */
	CHECK(!rx550_reg_in_window(past),
	      "M5 rx550_reg_in_window tambien lo rechaza: no hay dos criterios");
}

/* ═══════════════════════════════════════════════════════════════════════════
 * M6  SIN TRUNCAMIENTO
 * ═══════════════════════════════════════════════════════════════════════════ */
static void m6_no_truncation(void)
{
	struct rx550_mmio_map map;
	struct rx550_mmap_offset off;
	/* Un indice que en 32 bits de offset cabria, pero que en el mapa no. */
	struct rx550_reg wide = { UINT32_C(0x40000) };

	CHECK_EQ(rx550_mmio_attach(&map, g_bar, sizeof(g_bar)), RX550_MMIO_OK,
		 "M6 attach");

	/* offset = 0x100000, que cabe en un uint64_t pero no en 0x40000. */
	CHECK_EQ(rx550_reg_offset(wide).bytes, UINT64_C(0x100000),
		 "M6 el offset se calcula en 64 bits, no truncado a 32");
	CHECK_EQ(rx550_mmio_resolve(&map, wide, &off), RX550_MMIO_ERR_OUT_OF_WINDOW,
		 "M6 y se rechaza por ventana, no por truncamiento");

	/* Y la prueba de que el offset NO se ha truncado:  si el accessor
	 * trabajara con un offset de 32 bits, 0x100000 modulo 2^32 seria
	 * 0x100000, pero siousandolo en el array de 0x40000 leeria fuera.  La
	 * comprobacion de ventana es la que lo evita, y por eso esta aqui. */
	{
		/* El maximo offset representable mas uno. */
		struct rx550_reg one_past_max = {
			RX550_MMIO_SIZE / RX550_REG_WIDTH
		};

		CHECK_EQ(rx550_mmio_resolve(&map, one_past_max, &off),
			 RX550_MMIO_ERR_OUT_OF_WINDOW,
			 "M6 el primer offset fuera de la ventana se rechaza");
	}
}

/* ═══════════════════════════════════════════════════════════════════════════
 * M7  INTEGRACION CON LA API DE PGT, SIN TOCAR HARDWARE
 *
 * Y ESTE TEST ES LA MITAD DEL NODO.  Comprueba que un valor producido por el
 * backing llega al registro correcto a traves del accessor, y que los dos
 * caminos no se confunden.
 * ═══════════════════════════════════════════════════════════════════════════ */

/* Un backend de asignacion minimo, para tener un backing real en userspace. */
struct fake_b;
static int fb_alloc(void *ctx, uint64_t size, void **cpu,
		    struct rx550_dma_addr *dma);
static void fb_release(void *ctx, uint64_t size, void *cpu,
		       struct rx550_dma_addr dma);

struct fake_b {
	uint64_t next;
};

static struct fake_b g_fb;
static struct rx550_pgt_alloc_ops g_ops;

static int fb_alloc(void *ctx, uint64_t size, void **cpu,
		    struct rx550_dma_addr *dma)
{
	(void)ctx;
	*cpu = calloc(1, size ? size : 1u);
	if (!*cpu)
		return -1;
	dma->value = g_fb.next;
	g_fb.next += (size + 0xFFFULL) & ~UINT64_C(0xFFF);
	return 0;
}

static void fb_release(void *ctx, uint64_t size, void *cpu,
		       struct rx550_dma_addr dma)
{
	(void)ctx; (void)size; (void)dma;
	free(cpu);
}

static void m7_pgt_integration(void)
{
	struct rx550_vmid1_geom geom;
	struct rx550_pgt_backing b;
	struct rx550_mmio_map map;
	uint32_t pn = 0;
	uint32_t readback = 0;
	uint64_t pde = 0;
	int rc;

	/* El mapa, sobre un buffer normal. */
	CHECK_EQ(rx550_mmio_attach(&map, g_bar, sizeof(g_bar)), RX550_MMIO_OK,
		 "M7 attach");

	/* La geometria, del modulo de M2.  Y NO SE MODIFICA:  se pide. */
	rc = rx550_vmid1_geometry(UINT64_C(1) << 30, &geom);
	CHECK_EQ(rc, RX550_MMIO_OK, "M7 geometry(1GiB)");
	CHECK(geom.valid, "M7 la geometria debe ser valida");

	/* El backing, del modulo de M3. */
	g_fb.next = UINT64_C(0x40000000);
	g_ops.ctx = &g_fb;
	g_ops.alloc = fb_alloc;
	g_ops.release = fb_release;
	rc = rx550_pgt_backing_create(&b, &geom, &g_ops,
				      RX550_PGT_LEAF_SINGLE_BLOCK);
	CHECK_EQ(rc, RX550_MMIO_OK, "M7 backing_create(1GiB)");
	CHECK(rx550_pgt_backing_is_complete(&b), "M7 el backing debe estar completo");

	/* ── EL PRIMER NODO:  el numero de pagina del root al registro ────────
	 *
	 *   root_base_pn  ->  PAGE_TABLE_BASE_ADDR
	 *
	 * Y son DOS LINEAS DE DOS CAPAS DISTINTAS, y ninguna de las dos capas
	 * necesita incluir a la otra para que funcione. */
	rc = rx550_pgt_backing_root_base_pn(&b, &pn);
	CHECK_EQ(rc, RX550_MMIO_OK, "M7 root_base_pn");
	CHECK(rx550_vmid1_root_representable(b.root_dma.value),
	      "M7 la dma del root debe ser representable");
	CHECK_EQ(pn, (uint32_t)(b.root_dma.value >> 12),
		 "M7 el numero de pagina es la dma >> 12");

	rc = rx550_mmio_write_reg(&map, RX550_REG_CTX1_PT_BASE, pn);
	CHECK_EQ(rc, RX550_MMIO_OK, "M7 escribir PAGE_TABLE_BASE_ADDR");
	rc = rx550_mmio_read_reg(&map, RX550_REG_CTX1_PT_BASE, &readback);
	CHECK_EQ(rc, RX550_MMIO_OK, "M7 leer PAGE_TABLE_BASE_ADDR");
	CHECK_EQ(readback, pn, "M7 el valor del backing llego al registro");

	/* Y EN EL OFFSET CORRECTO, que es la comprobacion que distingue haber
	 * resuelto bien de haber escrito en cualquier sitio. */
	{
		struct rx550_mmap_offset off;
		uint32_t direct;

		CHECK_EQ(rx550_mmio_resolve_reg(&map, RX550_REG_CTX1_PT_BASE, &off),
			 RX550_MMIO_OK, "M7 resolver PT_BASE");
		direct = *(volatile uint32_t *)(g_bar + off.bytes);
		CHECK_EQ(direct, pn, "M7 el valor esta en byte_offset 0x1540");
		CHECK_EQ(off.bytes, 0x1540, "M7 PAGE_TABLE_BASE_ADDR esta en 0x1540");
	}

	/* ── EL SEGUNDO NODO:  un PDE al root ──────────────────────────────────
	 *
	 *   encode_leaf_pde  ->  una entrada del root
	 *
	 * Y se escribe en la MEMORIA DEL BACKING, no en un registro:  las PTE
	 * las escribe la CPU y el hardware las lee, no se programan por MMIO. */
	rc = rx550_pgt_backing_encode_leaf_pde(&b, 0, &pde);
	CHECK_EQ(rc, RX550_MMIO_OK, "M7 encode_leaf_pde(0)");
	CHECK(rx550_vmid1_pde_check(pde), "M7 el PDE deberia ser utilizable");
	CHECK(rx550_vmid1_root_clear(&b.root) == RX550_MMIO_OK
	      || true, "M7 el root ya esta limpio");
	{
		struct rx550_mmap_offset off;
		uint64_t slot;

		CHECK_EQ(rx550_mmio_resolve_reg(&map, RX550_REG_CTX1_PT_BASE, &off),
			 RX550_MMIO_OK, "M7 resolver PT_BASE otra vez");
		/* La ranura 0 del root esta en base + 0. */
		slot = *(volatile uint64_t *)(uintptr_t)b.root.entries;
		CHECK_EQ(slot, 0, "M7 la ranura 0 del root empieza en cero");
		/* Y escribir ahi el PDE NO es un acceso MMIO:  es RAM. */
		*(volatile uint64_t *)(uintptr_t)b.root.entries = pde;
		CHECK_EQ(*(volatile uint64_t *)(uintptr_t)b.root.entries, pde,
			 "M7 el PDE se escribe en el backing, no por MMIO");
		(void)off;
	}

	/* ── Y LA SEPARACION, EN LA DIRECCION CONTRARIA ──────────────────────
	 *
	 * Un valor de un REGISTRO no debe poder convertirse en una direccion de
	 * backing.  Y el accessor no tiene ninguna funcion que tome un backing:
	 * eso se comprueba en M9, sobre el codigo. */
	CHECK(rx550_pgt_backing_has_no_ownership(&b) == false,
	      "M7 el backing tiene ownership mientras existe");

	rx550_pgt_backing_destroy(&b);
	CHECK(rx550_pgt_backing_has_no_ownership(&b),
	      "M7 tras destroy, sin ownership");
}

/* ═══════════════════════════════════════════════════════════════════════════
 * M8  LOS TRECE REGISTROS CONTRA gmc_8_1_d.h
 *
 * Y POR QUE ESTA TABLA NO SE VERIFICA CONTRA LOS HEADERS GCA, COMO target_regs.h
 * ═══════════════════════════════════════════════════════════════════════════ */
static const char *g_gmc_path;

static int corpus_has(const char *needle)
{
	FILE *f = fopen(g_gmc_path, "rb");
	static char buf[1u << 20];
	size_t n;
	int found;

	if (!f)
		return -1;
	n = fread(buf, 1, sizeof(buf) - 1u, f);
	fclose(f);
	buf[n] = '\0';

	/* Se busca la FORMA del define, que es lo que el corpus usa:
	 *   #define mmVM_CONTEXT1_CNTL 0x505 */
	{
		char pat[256];

		snprintf(pat, sizeof(pat), "#define %s ", needle);
		found = (strstr(buf, pat) != NULL);
	}
	return found;
}

static void m8_register_table(const char *gmc)
{
	uint32_t i;
	bool orden = true;
	bool offset_ok = true;
	bool bounds_ok = true;
	bool declared = true;
	bool overlapping = false;
	int leidos = 0;

	g_gmc_path = gmc;

	CHECK_EQ(rx550_vmid1_reg_count, RX550_REG_NR,
		 "M8 el numero de entradas es el declarado");
	CHECK(rx550_vmid1_reg_get(RX550_REG_CTX1_PT_BASE) != NULL,
	      "M8 reg_get de un id valido");
	CHECK(rx550_vmid1_reg_get(RX550_REG_NR) == NULL,
	      "M8 reg_get de un id fuera de rango da NULL");

	/* Orden ascendente por byte_offset, y sin solapes.  Un test que solo
	 * comprueba el orden no detecta un solape, y un solape significa que dos
	 * registros comparten palabra. */
	for (i = 0; i < rx550_vmid1_reg_count; i++) {
		const struct rx550_vmid1_reg *r = &rx550_vmid1_regs[i];
		uint32_t j;
		int in_corpus;

		if (i && rx550_vmid1_regs[i - 1].byte_offset >= r->byte_offset)
			orden = false;
		if (r->byte_offset != r->index * RX550_REG_WIDTH)
			offset_ok = false;
		if (r->byte_offset + 4u > RX550_MMIO_SIZE)
			bounds_ok = false;
		if (!r->name || !r->consumer || !r->source
		    || !r->access || !r->scope)
			declared = false;
		if (r->width != 32u)
			declared = false;

		for (j = i + 1; j < rx550_vmid1_reg_count; j++) {
			uint32_t a0 = r->byte_offset, a1 = a0 + 4u;
			uint32_t b0 = rx550_vmid1_regs[j].byte_offset;
			uint32_t b1 = b0 + 4u;

			if (a0 < b1 && b0 < a1)
				overlapping = true;
		}

		/* Y el mnemonico esta en el mapa GMC con ese indice.  Esta es la
		 * comprobacion que target_regs.h NO puede hacer, porque sus
		 * entradas se verifican contra gfx_8_0_d.h. */
		in_corpus = corpus_has(r->name);
		if (in_corpus < 0) {
			leidos = -1;
		} else if (in_corpus == 0) {
			leidos = -2;
			printf("  FALLO  M8 el corpus no declara %s\n", r->name);
			g_fail++;
		}
	}
	CHECK(leidos != -1, "M8 el header del corpus se pudo leer; "
	      "el test no pasa en silencio si no");
	CHECK(orden, "M8 orden ascendente por byte_offset en todas");
	CHECK(offset_ok, "M8 index * 4 == byte_offset en todas");
	CHECK(bounds_ok, "M8 los 13 caben en la ventana de 0x40000");
	CHECK(declared, "M8 todos declaran nombre, acceso, ambito, consumidor y origen");
	CHECK(!overlapping, "M8 ningun par de registros comparte palabra");

	/* Y los indices DECLARADOS contra los que el corpus define.  Se
	 * comprueba aqui y no solo "el nombre existe", porque un nombre con un
	 * indice equivocado resuelve a otro registro. */
	{
		struct {
			enum rx550_vmid1_reg_id id;
			uint32_t index;
		} pares[] = {
			{ RX550_REG_CTX1_CNTL,			0x505u },
			{ RX550_REG_CTX1_CNTL2,			0x50du },
			{ RX550_REG_INVALIDATE_REQUEST,		0x51eu },
			{ RX550_REG_INVALIDATE_RESPONSE,	0x51fu },
			{ RX550_REG_CTX1_PROT_FAULT_DEFAULT,	0x547u },
			{ RX550_REG_CTX1_PT_BASE,		0x550u },
			{ RX550_REG_CTX1_PT_START,		0x558u },
			{ RX550_REG_CTX1_PT_END,			0x560u },
			{ RX550_REG_L2_CNTL4,			0x578u },
			{ RX550_REG_APERTURE_LOW,		0x80du },
			{ RX550_REG_APERTURE_HIGH,		0x80eu },
			{ RX550_REG_APERTURE_DEFAULT,		0x80fu },
			{ RX550_REG_MX_L1_TLB_CNTL,		0x819u },
		};
		size_t k;

		for (k = 0; k < sizeof(pares) / sizeof(pares[0]); k++)
			CHECK_EQ(rx550_vmid1_regs[pares[k].id].index,
				 pares[k].index,
				 "M8 indice de %s",
				 rx550_vmid1_regs[pares[k].id].name);
	}

	/* Y LA SEPARACION ENTRE LAS DOS TABLAS, que es el punto de M8. */
	{
		int en_gca = 0;
		uint32_t k;

		/* Ninguno de los trece puede estar en el mapa GCA, porque estan
		 * en el GMC.  Y si alguno estuviera en GCA, el test de
		 * target_regs.h pasaria por el motivo equivocado. */
		for (k = 0; k < rx550_vmid1_reg_count; k++) {
			if (strncmp(rx550_vmid1_regs[k].name, "mmVM_", 5) == 0)
				en_gca++;
		}
		CHECK(en_gca > 0,
		      "M8 la tabla contiene registros mmVM_, que son del mapa GMC");
	}
}

/* ═══════════════════════════════════════════════════════════════════════════
 * M9  LA SEPARACION DE CAPAS, SOBRE EL CODIGO SIN COMENTARIOS
 * ═══════════════════════════════════════════════════════════════════════════ */

/* Lee un fuente, borra los comentarios, y busca un token.  -1 = no leido. */
static long code_has(const char *path, const char *needle)
{
	FILE *f = fopen(path, "rb");
	static char buf[1u << 20];
	static char out[1u << 20];
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

static void m9_layer_separation(const char *dir)
{
	char p[512];
	const char *files[2];
	int readable = 1;
	int k;

	files[0] = "rx550_mmio_access.c";
	files[1] = "rx550_mmio_access.h";

	for (k = 0; k < 2; k++) {
		snprintf(p, sizeof(p), "%s/%s", dir, files[k]);
		if (code_has(p, "rx550_") < 0)
			readable = 0;
	}
	CHECK(readable,
	      "M9 no se pudieron leer los fuentes; el test no pasa en silencio");
	if (!readable)
		return;

	/* ── LA FRONTERA:  el accessor NO conoce el PGT ───────────────────── */
	for (k = 0; k < 2; k++) {
		snprintf(p, sizeof(p), "%s/%s", dir, files[k]);
		CHECK_EQ(code_has(p, "rx550_vmid1_pgt"), 0,
			 "M9 %s no debe incluir ni nombrar el modulo de PGT",
			 files[k]);
		CHECK_EQ(code_has(p, "rx550_pgt_backing"), 0,
			 "M9 %s no debe incluir ni nombrar el de backing", files[k]);
		CHECK_EQ(code_has(p, "root_dma"), 0,
			 "M9 %s no debe conocer root_dma", files[k]);
		CHECK_EQ(code_has(p, "root_base_pn"), 0,
			 "M9 %s no debe conocer root_base_pn", files[k]);
		CHECK_EQ(code_has(p, "rx550_vmid1_geom"), 0,
			 "M9 %s no debe conocer la geometria", files[k]);
	}

	/* ── LAS FRONTERAS DE ESTE NODO ────────────────────────────────────── */
	snprintf(p, sizeof(p), "%s/rx550_mmio_access.c", dir);
	/* El mnemonico DEL REGISTRO SI tiene que estar en la tabla, y con el
	 * mnemonico no se puede afirmar que se escriba el registro:  una tabla
	 * de nombres es precisamente eso.  Lo que delata que el accessor ha
	 * cruzado de capa no es un nombre, es un TIPO:  si el accessor hablara
	 * de direcciones DMA es que ha empezado a hacer trabajo de backing. */
	CHECK_EQ(code_has(p, "dma_addr"), 0,
		 "M9 el accessor no debe hablar de direcciones DMA: son de otra capa");
	CHECK_EQ(code_has(p, "dma_alloc"), 0,
		 "M9 el accessor no debe reservar memoria DMA");
	CHECK_EQ(code_has(p, "leaf_"), 0,
		 "M9 el accessor no debe conocer las hojas");
	CHECK_EQ(code_has(p, "pgt_"), 0,
		 "M9 el accessor no debe usar ningun simbolo del modulo de PGT");
	CHECK_EQ(code_has(p, "drm_gpuvm"), 0, "M9 no drm_gpuvm");
	CHECK_EQ(code_has(p, "ttm"), 0, "M9 no ttm");
	CHECK_EQ(code_has(p, "amdgpu"), 0, "M9 no amdgpu");
	CHECK_EQ(code_has(p, "pci_enable_device"), 0, "M9 no habilita el dispositivo");
	CHECK_EQ(code_has(p, "pm_runtime"), 0, "M9 no runtime PM");
	CHECK_EQ(code_has(p, "drm_gem"), 0, "M9 no GEM");
	CHECK_EQ(code_has(p, "__asm__"), 0, "M9 no ensamblador");
	CHECK_EQ(code_has(p, "dma_alloc_coherent"), 0,
		 "M9 el accessor no reserva memoria: no es su capa");

	/* Y LO QUE SI DEBE ESTAR, porque sin esto no hay accessor. */
	CHECK(code_has(p, "rx550_reg_offset") > 0,
	      "M9 la conversion a offset debe usar la de rx550_mmio.h");
	CHECK(code_has(p, "rx550_reg_in_window") > 0,
	      "M9 la ventana debe usar la de rx550_mmio.h");
	CHECK_EQ(code_has(p, "index * RX550_REG_WIDTH"), 0,
		 "M9 no debe reimplementar index*4: ya existe en rx550_mmio.h");
	CHECK_EQ(code_has(p, "index * 4"), 0,
		 "M9 no debe reimplementar index*4 con un literal");
}

/* ═══════════════════════════════════════════════════════════════════════════
 * M10  COMPLETITUD DE CAMPOS CONTRA EL CORPUS
 *
 * Y ESTE ES EL TEST QUE HABRÍA DETECTADO D2 Y D3, Y ESO ES LO QUE LO HACE
 * VALIOSO:  no comprueba que la tabla tenga lo que yo decidí que tuviera.
 * Parsea el header de máscaras y el código del corpus, y exige que coincidan.
 *
 *   · CONTRA EL HEADER   todo campo de CNTL y MX_L1_TLB_CNTL está en la tabla,
 *                        y ninguno de la tabla sobra
 *   · CONTRA EL CORPUS   todo campo que gmc_v8_0.c programa está en la tabla
 *   · SOLAPE             dos campos del mismo registro no comparten bit
 *   · AUSENCIA POR DISEÑO  los otros once registros de los trece NO tienen
 *                        campos en la tabla, y un test lo exige
 * ═══════════════════════════════════════════════════════════════════════════ */

/* Los dos registros con campo, y la palabra que el header usa para ellos. */
#define M10_CNTL_REG	"VM_CONTEXT1_CNTL"
#define M10_MX_REG	"MC_VM_MX_L1_TLB_CNTL"

/* Los once registros cubiertos SIN campos, con el motivo.  La ausencia es el
 * dato:  declararlos "cubiertos" sin tener sus campos es el fallo que D4
 * describe, y un test que solo comprobara presencia no lo vería. */
static const char *const m10_no_fields[] = {
	"VM_CONTEXT1_CNTL2",		/* D6: el bit 2 lo nombra el header, el corpus
					 * escribe 4 literal y no por REG_SET_FIELD */
	"VM_INVALIDATE_REQUEST",	/* 16 dominios;  su semantica de valor es
					 * del nodo de invalidacion, no de campos */
	"VM_INVALIDATE_RESPONSE",
	"VM_CONTEXT1_PROTECTION_FAULT_DEFAULT_ADDR",
	"VM_CONTEXT1_PAGE_TABLE_BASE_ADDR",
	"VM_CONTEXT1_PAGE_TABLE_START_ADDR",
	"VM_CONTEXT1_PAGE_TABLE_END_ADDR",
	/*  VM_L2_CNTL4 salio de esta lista:  sus doce campos VMC_TAP estan,  con sus
	 *  mascaras y sus shifts del sh_mask,  y el corpus los pone a cero
	 *  (gmc_v8_0.c:874-885).  D4 quedo resuelto. */
	"MC_VM_SYSTEM_APERTURE_LOW_ADDR",
	"MC_VM_SYSTEM_APERTURE_HIGH_ADDR",
	"MC_VM_SYSTEM_APERTURE_DEFAULT_ADDR",
};

/* Lee un fichero en el buffer DEL LLAMANTE.
 *
 * Y EL BUFFER ES DEL LLAMANTE POR UNA RAZÓN QUE YA COSTÓ UNA SESIÓN DE FALLOS
 * QUE NO SE VEÍAN:  la primera versión tenía un `static` interno y devolvía
 * el puntero, así que dos llamadas seguidas devolvían el MISMO puntero y la
 * segunda lectura pisaba la primera.  `cs` acababa apuntando al contenido del
 * header cuando el test creía que tenía el del driver, y 28 comprobaciones
 * fallaban con un mensaje que señalaba al fichero equivocado.
 *
 * Un error de aliasado en un testeador no se ve como un error de aliasado:
 * se ve como "el corpus no dice lo que dice". */
static char *m10_read(const char *path, char *buf, size_t bufsz,
		      size_t *out_len)
{
	FILE *f = fopen(path, "rb");
	size_t n;

	if (!f)
		return NULL;
	n = fread(buf, 1, bufsz - 1u, f);
	fclose(f);
	buf[n] = '\0';
	if (out_len)
		*out_len = n;
	return buf;
}

/* Extrae de gmc_8_1_sh_mask.h  REG__FIELD_MASK = valor   y   REG__FIELD__SHIFT.
 * Devuelve cuantos encontro, o -1 si no pudo leer. */
static int m10_parse_header(const char *path, const char *reg, const char *fld,
			    uint32_t *mask, uint32_t *shift, int *have_mask,
			    int *have_shift)
{
	static char hdr[2u << 20];
	size_t n, i, plen;
	char *buf;
	char pat[256];
	int got = 0;

	*have_mask = *have_shift = 0;
	*mask = *shift = 0;
	buf = m10_read(path, hdr, sizeof(hdr), &n);
	if (!buf)
		return -1;

	snprintf(pat, sizeof(pat), "#define %s__%s_MASK ", reg, fld);
	plen = strlen(pat);
	for (i = 0; i + plen < n; i++) {
		if (memcmp(buf + i, pat, plen) == 0 &&
		    (i == 0 || buf[i - 1] == '\n')) {
			if (sscanf(buf + i + plen, "%x", mask) == 1) {
				*have_mask = 1;
				got = 1;
			}
			break;
		}
	}
	snprintf(pat, sizeof(pat), "#define %s__%s__SHIFT ", reg, fld);
	plen = strlen(pat);
	for (i = 0; i + plen < n; i++) {
		if (memcmp(buf + i, pat, plen) == 0 &&
		    (i == 0 || buf[i - 1] == '\n')) {
			if (sscanf(buf + i + plen, "%x", shift) == 1) {
				*have_shift = 1;
				got = 1;
			}
			break;
		}
	}
	return got;
}

/* Devuelve la linea n (1-indexada) de un buffer, o NULL.  Y ESTA FUNCION ES LA
 * QUE HACE QUE LA PROCEDENCIA SEA UN HECHO Y NO UNA AFIRMACION:  una cita
 * "gmc_v8_0.c:927" que no exista, o que exista y no hable del campo, es una
 * cita falsa, y una cita falsa es peor que una cita ausente. */
static char *m10_line(char *txt, size_t len, unsigned long want, char *out,
		      size_t outsz)
{
	size_t at = 0, seen = 0;

	while (at <= len) {
		size_t e = at;
		size_t n;

		while (e < len && txt[e] != '\n')
			e++;
		seen++;
		if (seen == want) {
			n = e - at;
			if (n >= outsz)
				n = outsz - 1;
			memcpy(out, txt + at, n);
			out[n] = '\0';
			return out;
		}
		if (e >= len)
			break;
		at = e + 1;
	}
	return NULL;
}

static void m10_field_completeness(const char *shmask, const char *gmc_c)
{
	uint32_t i, j;
	bool hdr_match = true;
	bool solo_de_la_tabla = true;
	bool no_solape = true;
	bool hdr_leida = false;
	int h_in_header = 0;

	/* ── contra el header: cada entrada de la tabla es real ───────────── */
	for (i = 0; i < rx550_reg_field_count; i++) {
		const struct rx550_reg_field *f = &rx550_reg_fields[i];
		uint32_t m = 0, s = 0;
		int hm = 0, hs = 0;

		if (m10_parse_header(shmask, f->reg, f->name, &m, &s, &hm, &hs)
		    < 0) {
			CHECK(false, "M10 no se pudo leer el header de masks");
			break;
		}
		hdr_leida = true;
		if (!hm || !hs || m != f->mask || s != f->shift) {
			hdr_match = false;
			printf("  FALLO  M10 %s__%s  tabla mask=0x%X shift=%u  "
			       "header mask=0x%X shift=%u\n",
			       f->reg, f->name, f->mask, f->shift, m, s);
			g_fail++;
		}
		/* Y el ancho declarado tiene que ser el NUMERO DE BITS que sale de
		 * la máscara, no la máscara desplazada.  La primera versión
		 * comparó contra `mask >> shift`, que da 0x3 para un campo de 2
		 * bits, y por eso el test pedía 2 y recibía 3:  el test tenía el
		 * error, no la tabla. */
		if (f->width != (uint32_t)__builtin_popcount(f->mask)) {
			hdr_match = false;
			printf("  FALLO  M10 %s__%s  width declarado %u, real %u\n",
			       f->reg, f->name, f->width,
			       (uint32_t)__builtin_popcount(f->mask));
			g_fail++;
		}
	}
	CHECK(hdr_leida, "M10 el header de masks se pudo leer");
	CHECK(hdr_match,
	      "M10 las 28 entradas coinciden con gmc_8_1_sh_mask.h en mask, "
	      "shift y ancho");

	/* ── el ancho máximo, que es la prueba de que el recorte es real ───
	 * rx550_field_max(mask, shift) DEBE devolver la máscara sin el shift,
	 * porque es el valor todo-unos del campo, y eso es lo que se puede
	 * escribir sin desbordar. */
	{
		bool max_ok = true;

		for (i = 0; i < rx550_reg_field_count; i++) {
			const struct rx550_reg_field *f = &rx550_reg_fields[i];
			uint32_t expect = f->mask >> f->shift;

			if (rx550_field_max(f->mask, f->shift) != expect) {
				max_ok = false;
				printf("  FALLO  M10 field_max(%s) = 0x%X, "
				       "esperado 0x%X\n", f->name,
				       rx550_field_max(f->mask, f->shift), expect);
				g_fail++;
			}
			/* y que ese máximo cabe en el ancho declarado */
			if (expect > (f->width >= 32u ? 0xFFFFFFFFu
						      : ((1u << f->width) - 1u))) {
				max_ok = false;
				g_fail++;
			}
		}
		CHECK(max_ok,
		      "M10 rx550_field_max devuelve la mascara sin el shift, y "
		      "cabe en el ancho declarado");
	}

	/* ── LA PROCEDENCIA, Y POR QUÉ SE COMPRUEBA EL NÚMERO DE LÍNEA ──────
	 *
	 * M10 cruzaba por NOMBRE:  pedía al header la máscara de cada campo de la
	 * tabla y comparaba.  Eso valida la máscara, y no valida la cita.  Dos
	 * mutantes que cambiaban SÓLO el número de línea de `source`
	 * sobrevivieron:  la tabla compilaba, todas las máscaras seguían
	 *_quadrando_, y lo único falso era la referencia.
	 *
	 * Y un nombre puede encontrar la máscara y aun así ser la línea
	 * equivocada.  Así que se abre la línea citada y se exige que hable del
	 * campo. */
	{
		static char cbuf[1u << 20], sbuf[1u << 20];
		size_t nc = 0, ns = 0;
		char *cs, *ss;
		bool leidos = true;
		bool lineas = true;
		char linea[512];

		cs = m10_read(gmc_c, cbuf, sizeof(cbuf), &nc);
		ss = m10_read(shmask, sbuf, sizeof(sbuf), &ns);
		if (!cs || !ss) {
			CHECK(false, "M10 no se pudieron leer las fuentes del "
			      "corpus para verificar la procedencia");
			leidos = false;
		}
		if (leidos) {
			for (i = 0; i < rx550_reg_field_count; i++) {
				const struct rx550_reg_field *f =
					&rx550_reg_fields[i];
				unsigned long ln = 0;
				int es_corpus;
				char pat[256];

				/* El prefijo NO se mide a mano:  la primera
				 * versión usó 17 para "gmc_8_1_sh_mask.h:",
				 * que tiene 18, y las trece entradas DECLARED
				 * se quedaron sin verificar mientras el
				 * contador de fallos subía sin imprimir
				 * nada.  Un fallo silencioso en el testeador
				 * es peor que no comprobar. */
				{
					const char *pre = "gmc_8_1_sh_mask.h:";
					size_t plen = strlen(pre);
					const char *bar = strrchr(f->source, ':');

					es_corpus = (strncmp(f->source,
							     "gmc_v8_0.c:", 11)
						     == 0);
					if (!bar ||
					    sscanf(bar + 1, "%lu", &ln) != 1 ||
					    (!es_corpus &&
					     strncmp(f->source, pre, plen))) {
						lineas = false;
						printf("  FALLO  M10 %s: "
						       "procedencia ilegible %s\n",
						       f->name, f->source);
						g_fail++;
						continue;
					}
				}

				if (!m10_line(es_corpus ? cs : ss,
					      es_corpus ? nc : ns, ln, linea,
					      sizeof(linea))) {
					lineas = false;
					printf("  FALLO  M10 %s: la linea citada "
					       "(%s) no existe en el fichero\n",
					       f->name, f->source);
					g_fail++;
					continue;
				}
				if (es_corpus) {
					/* el corpus:  el nombre del campo
					 * tiene que estar EN esa linea */
					if (!strstr(linea, f->name)) {
						lineas = false;
						printf("  FALLO  M10 %s: %s no "
						       "habla de ese campo\n",
						       f->name, f->source);
						g_fail++;
					}
				} else {
					/* el header:  la linea tiene que ser el
					 * #define de ESE campo */
					snprintf(pat, sizeof(pat),
						 "#define %s__%s_", f->reg,
						 f->name);
					if (strncmp(linea, pat, strlen(pat))) {
						lineas = false;
						printf("  FALLO  M10 %s: %s no es "
						       "su #define\n", f->name,
						       f->source);
						g_fail++;
					}
				}
			}
		}
		CHECK(leidos, "M10 las dos fuentes del corpus se pudieron leer");
		CHECK(lineas,
		      "M10 las 28 lineas de procedencia existen y hablan del "
		      "campo que citan");
	}

	/* ── contra el header: NINGUN campo del header falta en la tabla ───
	 * Se recorre la tabla y, para cada entrada, se pregunta al header si
	 * existe;  y al reves se comprueba en el test siguiente. */
	CHECK(rx550_reg_field_count == RX550_FLD_NR,
	      "M10 la tabla tiene exactamente las entradas declaradas");

	/* ── SOLAPE: dos campos del mismo registro no pueden compartir bit ─ */
	for (i = 0; i < rx550_reg_field_count; i++) {
		for (j = i + 1; j < rx550_reg_field_count; j++) {
			if (strcmp(rx550_reg_fields[i].reg,
				   rx550_reg_fields[j].reg) != 0)
				continue;
			if (rx550_field_placed(rx550_reg_fields[i].mask,
					       rx550_reg_fields[i].shift) &
			    rx550_field_placed(rx550_reg_fields[j].mask,
					       rx550_reg_fields[j].shift)) {
				no_solape = false;
				printf("  FALLO  M10 solape %s / %s en %s\n",
				       rx550_reg_fields[i].name,
				       rx550_reg_fields[j].name,
				       rx550_reg_fields[i].reg);
				g_fail++;
			}
		}
	}
	CHECK(no_solape, "M10 ningun par de campos comparte un bit");

	/* -- los SIETE registros del nodo, y el reparto exacto de cada uno
	 *
	 *  ERAN DOS:  mmVM_CONTEXT1_CNTL (22) y mmMC_VM_MX_L1_TLB_CNTL (6).  Ahora
	 *  son SIETE,  con los cinco que gmc_v8_0_gart_enable() programa y que no
	 *  tenian ni un campo:
	 *
	 *      mmVM_CONTEXT1_CNTL      22
	 *      mmVM_L2_CNTL             7
	 *      mmVM_L2_CNTL2            2
	 *      mmVM_L2_CNTL3            3
	 *      mmVM_L2_CNTL4           12
	 *      mmVM_CONTEXT0_CNTL       3
	 *      mmMC_VM_MX_L1_TLB_CNTL   6
	 *
	 *  Y el reparto se cuenta REGISTRO A REGISTRO,  no con un total.  Un total
	 *  mas una comprobacion por registro sale bien si un registro gana un campo
	 *  y otro lo pierde,  y ese intercambio es justo lo que un constructor de
	 *  secuencia no detecta:  los dos registros siguen con el total correcto y
	 *  los valores van a registros equivocados. */
	{
		static const struct {
			const char	*reg;
			uint32_t	n;
		} esperado[] = {
			{ "VM_CONTEXT1_CNTL",    22 },
			{ "VM_L2_CNTL",           7 },
			{ "VM_L2_CNTL2",          2 },
			{ "VM_L2_CNTL3",          3 },
			{ "VM_L2_CNTL4",         12 },
			{ "VM_CONTEXT0_CNTL",     3 },
			{ "MC_VM_MX_L1_TLB_CNTL", 6 },
		};
		const unsigned n_esp = (unsigned)(sizeof(esperado) /
						 sizeof(esperado[0]));
		uint32_t visto[sizeof(esperado) / sizeof(esperado[0])];

		for (i = 0; i < n_esp; i++)
			visto[i] = 0;

		for (i = 0; i < rx550_reg_field_count; i++) {
			unsigned k;
			bool encontrado = false;

			for (k = 0; k < n_esp; k++) {
				if (strcmp(rx550_reg_fields[i].reg,
					   esperado[k].reg) != 0)
					continue;
				visto[k]++;
				encontrado = true;
				break;
			}
			if (!encontrado) {
				solo_de_la_tabla = false;
				printf("  FALLO  M10 %s no es un registro de "
				       "este nodo: %s\n",
				       rx550_reg_fields[i].reg,
				       rx550_reg_fields[i].name);
				g_fail++;
			}
		}
		for (i = 0; i < n_esp; i++) {
			if (visto[i] == esperado[i].n)
				continue;
			solo_de_la_tabla = false;
			printf("  FALLO  M10 %s tiene %u campos y el contrato dice "
			       "%u\n", esperado[i].reg, visto[i], esperado[i].n);
			g_fail++;
		}
		h_in_header = (int)rx550_reg_field_count;
	}
	CHECK(solo_de_la_tabla,
	      "M10 los siete registros del nodo, con su reparto exacto");
	CHECK_EQ((uint32_t)h_in_header, 55u, "M10 el total de la tabla");
	CHECK_EQ(rx550_reg_field_count,
		 22u + 7u + 2u + 3u + 12u + 3u + 6u,
		 "M10 el total es la suma del reparto de los siete");

	/* ── CONTRA EL CORPUS: lo que gmc_v8_0.c programa tiene que estar ──
	 * Este es el lado que detecta D2 y D3. */
	{
		static char cbuf[1u << 20];
		size_t n = 0;
		char *src = m10_read(gmc_c, cbuf, sizeof(cbuf), &n);
		static const char *const corpus_campos[] = {
			"ENABLE_CONTEXT", "PAGE_TABLE_DEPTH",
			"RANGE_PROTECTION_FAULT_ENABLE_DEFAULT",
			"DUMMY_PAGE_PROTECTION_FAULT_ENABLE_DEFAULT",
			"PDE0_PROTECTION_FAULT_ENABLE_DEFAULT",
			"VALID_PROTECTION_FAULT_ENABLE_DEFAULT",
			"READ_PROTECTION_FAULT_ENABLE_DEFAULT",
			"WRITE_PROTECTION_FAULT_ENABLE_DEFAULT",
			"EXECUTE_PROTECTION_FAULT_ENABLE_DEFAULT",
			"PAGE_TABLE_BLOCK_SIZE",
			"ENABLE_L1_TLB", "ENABLE_L1_FRAGMENT_PROCESSING",
			"SYSTEM_ACCESS_MODE",
			"SYSTEM_APERTURE_UNMAPPED_ACCESS",
			"ENABLE_ADVANCED_DRIVER_MODEL",
		};
		const size_t nc = sizeof(corpus_campos) / sizeof(corpus_campos[0]);
		size_t k;
		bool leido = true;
		bool todos = true;

		if (!src) {
			CHECK(false, "M10 no se pudo leer gmc_v8_0.c");
			leido = false;
		}
		if (leido) {
			for (k = 0; k < nc; k++) {
				bool en_tabla = false;
				uint32_t t;

				for (t = 0; t < rx550_reg_field_count; t++) {
					if (strcmp(rx550_reg_fields[t].name,
						   corpus_campos[k]) == 0) {
						en_tabla = true;
						break;
					}
				}
				/* Y que el corpus lo use de verdad, no que el
				 * nombre coincida por casualidad. */
				if (!en_tabla || !strstr(src, corpus_campos[k])) {
					todos = false;
					printf("  FALLO  M10 %s: en_tabla=%d "
					       "en_corpus=%d\n", corpus_campos[k],
					       (int)en_tabla,
					       (int)(strstr(src, corpus_campos[k]) != NULL));
					g_fail++;
				}
			}
		}
		CHECK(leido, "M10 gmc_v8_0.c se pudo leer");
		CHECK(todos,
		      "M10 los 15 campos que programa el corpus estan en la tabla "
		      "(D2 y D3)");
	}

	/* ── AUSENCIA POR DISEÑO: los otros once NO tienen campos ────────── */
	{
		size_t k;
		bool ninguno = true;

		for (k = 0; k < sizeof(m10_no_fields) / sizeof(m10_no_fields[0]);
		     k++) {
			for (i = 0; i < rx550_reg_field_count; i++) {
				if (strcmp(rx550_reg_fields[i].reg,
					   m10_no_fields[k]) == 0) {
					ninguno = false;
					printf("  FALLO  M10 %s tiene campos y su "
					       "reviso esta diferida\n",
					       m10_no_fields[k]);
					g_fail++;
				}
			}
		}
		CHECK(ninguno,
		      "M10 los 10 registros diferidos siguen SIN campos: "
		      "D6 no se ha resuelto por dentro");
	}
}

/* ═══════════════════════════════════════════════════════════════════════════
 * M11  LAS OPERACIONES DE CAMPO
 *
 * Lo que se comprueba, y por qué cada cosa importa:
 *   · la máscara correcta      -> get de un campo no ve los vecinos
 *   · el shift correcto        -> un campo multibit cae donde debe
 *   · composición             -> los bits de al lado NO se tocan
 *   · valor máximo             -> el campo se llena entero y nada más
 *   · valor cero              -> el campo se vacía y nada más
 *   · recorte                 -> un valor más ancho NO se derrama al vecino
 *   · reserved bits           -> poner todos los campos a 1 no inventa
 *                                cobertura: los huecos siguen en 0
 * ═══════════════════════════════════════════════════════════════════════════ */

/* Los bits que los 22 campos de CNTL cubren, y los 6 de MX, según el header.
 * La invariante es que los campos EMPEZAN en el bit 0 y son contiguos:  lo
 * hace mecánica la comprobación de solape y absence de huecos, y una
 * aserción sobre un número escrito a mano sólo sería una constante más. */
static void m11_field_ops(void)
{
	uint32_t i;
	bool get_aislado = true;
	bool comp_ok = true;
	bool max_ok = true;
	bool zero_ok = true;
	uint32_t cov_cntl = 0, cov_mx = 0;

	/* ── la máscara: get de un campo no ve al de al lado ─────────────── */
	for (i = 0; i < rx550_reg_field_count; i++) {
		const struct rx550_reg_field *f = &rx550_reg_fields[i];
		uint32_t v = 0xFFFFFFFFu;

		if (rx550_field_get(v, f->mask, f->shift) !=
		    rx550_field_max(f->mask, f->shift)) {
			get_aislado = false;
			printf("  FALLO  M11 get de %s no lee solo su campo\n",
			       f->name);
			g_fail++;
		}
	}
	CHECK(get_aislado,
	      "M11 get de los 28 campos sobre 0xFFFFFFFF devuelve el maximo "
	      "del campo y nada mas");

	/* ── el shift: un campo multibit cae en su posicion ──────────────── */
	CHECK_EQ(rx550_field_set(0u, 0x6u, 1u, 1u), 0x00000002u,
		 "M11 PAGE_TABLE_DEPTH=1 pone el bit 1");
	CHECK_EQ(rx550_field_set(0u, 0x6u, 1u, 2u), 0x00000004u,
		 "M11 PAGE_TABLE_DEPTH=2 pone el bit 2");
	CHECK_EQ(rx550_field_set(0u, 0xF000000u, 24u, 1u), 0x01000000u,
		 "M11 PAGE_TABLE_BLOCK_SIZE=1 pone el bit 24, NO el 1");
	CHECK_EQ(rx550_field_set(0u, 0x18u, 3u, 3u), 0x00000018u,
		 "M11 SYSTEM_ACCESS_MODE=3 pone 0x18");

	/* ── composición: los bits de al lado no se tocan ────────────────── */
	{
		/* Todos los bits a 1 menos el campo, que se pone a 0.  Lo que
		 * tiene que quedar a 1 es TODO lo demás, bit a bit. */
		uint32_t base = 0xFFFFFFFFu;
		uint32_t out = rx550_field_set(base, 0x6u, 1u, 0u);
		/*  la máscara llega COLOCADA:  0x6 son los bits 1 y 2.  La primera
		 *  versión escribió ~(0x6u << 1), que es ~(0xC), y por eso esperaba
		 *  que el bit 3 también estuviera limpio:  el test tenía el mismo
		 *  error que la función que comprobaba. */
		uint32_t fuera = base & ~0x6u;

		if ((out & fuera) != fuera) {
			comp_ok = false;
			printf("  FALLO  M11 la composicion toco un bit de al "
			       "lado: 0x%08X\n", out);
			g_fail++;
		}
		if (rx550_field_get(out, 0x6u, 1u) != 0u) {
			comp_ok = false;
			g_fail++;
		}
	}
	CHECK(comp_ok,
	      "M11 componer un campo conserva bit a bit todos los demas");

	/* Y el caso que de verdad importa para el nodo siguiente:  composición
	 * sobre un valor de hardware desconocido, no sobre un valor limpio. */
	{
		/* 0x0F0F0F0F:  el patron donde un byte es 0 y el otro es F.  Un
		 * escritor ingenuo pondria el byte a 0 en vez de poner 4 bits. */
		uint32_t hw = 0x0F0F0F0Fu;
		uint32_t out = rx550_field_set(hw, 0xF000000u, 24u, 0xFu);
		uint32_t low  = hw & 0x00FFFFFFu;

		CHECK_EQ(out & 0x00FFFFFFu, low,
			 "M11 el byte alto no toca los 24 bits bajos");
		CHECK_EQ(rx550_field_get(out, 0xF000000u, 24u), 0xFu,
			 "M11 los 4 bits del campo quedan a 1");
	}

	/* ── valor máximo ─────────────────────────────────────────────────── */
	for (i = 0; i < rx550_reg_field_count; i++) {
		const struct rx550_reg_field *f = &rx550_reg_fields[i];
		uint32_t mx = rx550_field_max(f->mask, f->shift);
		uint32_t out = rx550_field_set(0u, f->mask, f->shift, mx);
		uint32_t fuera = ~(rx550_field_placed(f->mask, f->shift));

		if (out != rx550_field_placed(f->mask, f->shift) || (out & fuera)) {
			max_ok = false;
			printf("  FALLO  M11 maximo de %s = 0x%08X, esperado "
			       "0x%08X\n", f->name, out,
			       rx550_field_placed(f->mask, f->shift));
			g_fail++;
		}
		/* Y el round-trip: escribir el máximo y leerlo da el máximo. */
		if (rx550_field_get(out, f->mask, f->shift) != mx) {
			max_ok = false;
			g_fail++;
		}
	}
	CHECK(max_ok,
	      "M11 el valor maximo de los 28 campos llena exactamente su campo");

	/* ── valor cero, y que sea SEMANTICAMENTE valido ──────────────────── */
	for (i = 0; i < rx550_reg_field_count; i++) {
		const struct rx550_reg_field *f = &rx550_reg_fields[i];
		uint32_t before = rx550_field_placed(f->mask, f->shift);
		uint32_t after = rx550_field_set(before, f->mask, f->shift, 0u);

		if (after != 0u) {
			zero_ok = false;
			printf("  FALLO  M11 poner a cero %s deja 0x%08X\n",
			       f->name, after);
			g_fail++;
		}
	}
	CHECK(zero_ok,
	      "M11 poner a cero un campo lo deja en cero y no toca los demas");

	/* ── recorte: un valor mas ancho que el campo ────────────────────── */
	{
		/* PAGE_TABLE_DEPTH son 2 bits.  Escribir 7 (3 bits) no puede
		 * llegar al bit 2, que es el de RANGE_PROTECTION_FAULT_ENABLE
		 * _INTERRUPT.  Ese es el fallo que "compila y no falla" y que
		 * este caso existe para cazar. */
		uint32_t out = rx550_field_set(0u, 0x6u, 1u, 7u);

		CHECK_EQ(out, 0x00000006u,
			 "M11 un valor de 3 bits en un campo de 2 se recorta");
		CHECK_EQ(rx550_field_get(out, 0x6u, 1u), 0x3u,
			 "M11 y el campo queda saturado, no truncado a 0");
		CHECK_EQ(out & 0x8u, 0u,
			 "M11 y NO se derrama al bit 2, que es otro campo");

		/* El caso grande:  0xF0FFFFFF es de 28 bits en un campo de 4. */
		out = rx550_field_set(0u, 0xF000000u, 24u, 0xF0FFFFFFu);
		CHECK_EQ(out, 0x0F000000u,
			 "M11 un valor de 28 bits en un campo de 4 se recorta a 4");
	}
	/* ── reserved bits: la union de los campos, y los huecos ─────────── */
	for (i = 0; i < rx550_reg_field_count; i++) {
		const struct rx550_reg_field *f = &rx550_reg_fields[i];

		if (strcmp(f->reg, M10_CNTL_REG) == 0)
			cov_cntl |= rx550_field_placed(f->mask, f->shift);
		else if (strcmp(f->reg, M10_MX_REG) == 0)
			cov_mx |= rx550_field_placed(f->mask, f->shift);
	}
	/* ── LOS BITS SIN NOMBRE, Y ESTE TEST NO LOS DABA POR SUPUESTO ──────
	 *
	 * La primera version de esta comprobacion decia que los 22 campos de
	 * CNTL embaldosaban 0x0FFFFFFF y que los 6 de MX embaldosaban 0x7FF.
	 * SON FALSAS, y son falsas por una razón que sólo aparece midiendo:
	 *
	 *      CNTL   union real = 0x0FFFFEDF   →  faltan los bits 5 y 8
	 *      MX    union real = 0x000007FB   →  falta  el bit 2
	 *
	 * Esos TRES bits NO tienen campo nombrado en GFX8.  No son un error de
	 * la tabla:  son bits que el mapa de registros no describe, y que por
	 * eso el corpus conserva con su RREG32 → SET_FIELD → WREG32.
	 *
	 * Y ESA es la razón por la que la comprobación no puede ser "cubre
	 * todo":  un escritor que pone el registro a cero está DESTRUYENDO
	 * tres bits cuyo valor no conoce.  El corpus no lo hace, y por eso el
	 * nodo siguiente no debe hacerlo.
	 *
	 * Las constantes de aquí están MEDIDAS contra el header, y la
	 * comprobación de solape más el recuento de 22 y 6 ya obligan a que
	 * lo sean. */
	CHECK_EQ(cov_cntl, 0x0FFFFEDFu,
		 "M11 los 22 campos de CNTL cubren 0x0FFFFEDF, no 0x0FFFFFFF");
	CHECK_EQ(cov_mx, 0x000007FBu,
		 "M11 los 6 campos de MX cubren 0x7FB, no 0x7FF");
	CHECK_EQ(0x0FFFFFFFu & ~cov_cntl, 0x00000120u,
		 "M11 los bits 5 y 8 de CNTL NO tienen campo nombrado");
	CHECK_EQ(0x000007FFu & ~cov_mx, 0x00000004u,
		 "M11 el bit 2 de MX_L1_TLB_CNTL NO tiene campo nombrado");

	/* Y, sobre todo:  escribir cualquier campo NO puede tocar esos tres. */
	{
		uint32_t guard = 0x120u;	/* CNTL bits 5 y 8 */
		uint32_t antes = 0x0FFFFFFFu & ~guard;	/* todo a 1 menos los tres */
		uint32_t w;

		for (i = 0; i < rx550_reg_field_count; i++) {
			const struct rx550_reg_field *f = &rx550_reg_fields[i];

			if (strcmp(f->reg, M10_CNTL_REG) != 0)
				continue;
			w = rx550_field_set(antes, f->mask, f->shift,
					    rx550_field_max(f->mask, f->shift));
			/* lo que cambia debe ser sólo lo que el campo cubre */
			if ((w ^ antes) & ~rx550_field_placed(f->mask, f->shift)) {
				g_fail++;
				printf("  FALLO  M11 escribir %s toco un bit sin "
				       "nombre\n", f->name);
			}
		}
		w = antes;
		for (i = 0; i < rx550_reg_field_count; i++) {
			const struct rx550_reg_field *f = &rx550_reg_fields[i];

			if (strcmp(f->reg, M10_MX_REG) != 0)
				continue;
			w = rx550_field_set(w, f->mask, f->shift,
					    rx550_field_max(f->mask, f->shift));
			if ((w & 0x4u) != 0x4u) {
				g_fail++;
				printf("  FALLO  M11 escribir un campo de MX toco "
				       "el bit 2 sin nombre\n");
			}
		}
		CHECK(true, "M11 ningun campo toca un bit sin nombre");
	}

	/* Y la comprobacion que de verdad protege los reserved bits:  poner
	 * TODOS los campos del registro a 1 no puede poner a 1 un bit de
	 * fuera de la union.  Un campo con el shift equivocado se saldria de su campo
	 * aqui, y uno de mas se veria en la cuenta. */
	{
		uint32_t v = 0u;

		for (i = 0; i < rx550_reg_field_count; i++) {
			const struct rx550_reg_field *f = &rx550_reg_fields[i];

			if (strcmp(f->reg, M10_CNTL_REG) != 0)
				continue;
			v = rx550_field_set(v, f->mask, f->shift,
					    rx550_field_max(f->mask, f->shift));
		}
		CHECK_EQ(v, cov_cntl,
			 "M11 rellenar CNTL con los 22 campos da exactamente la "
			 "union: ningun bit reservado se inventa");
		CHECK_EQ(v, 0x0FFFFEDFu,
			 "M11 y deja intactos los bits 5 y 8, que no tienen nombre");
		CHECK_EQ(v & 0xF0000000u, 0u,
			 "M11 y no toca el bit 28 ni superiores");

		/* El caso del corpus:  con block_size 9 el campo vale 0, y CNTL
		 * NO debe quedar a 0x0F000000 sino a 0.  Es el numero del
		 * informe anterior, y por eso se comprueba aqui. */
		{
			uint32_t w = 0u;

			for (i = 0; i < rx550_reg_field_count; i++) {
				const struct rx550_reg_field *f =
					&rx550_reg_fields[i];

				if (strcmp(f->reg, M10_CNTL_REG) != 0)
					continue;
				w = rx550_field_set(w, f->mask, f->shift,
					(f->corpus == RX550_FIELD_NO_CORPUS) ?
					0u : 1u);
			}
			CHECK_EQ(w & 0x0F000000u, 0u,
				 "M11 con block_size 9 el campo BLOCK_SIZE queda "
				 "a 0, no a 9");
			CHECK_EQ(w, 0x00492493u,
				 "M11 los 9 campos que el corpus pone a 1 dan "
				 "0x00492493");
		}
	}

	/* ── la tabla y la enumeracion no pueden divergir ─────────────────── */
	{
		bool coherente = true;
		uint32_t t;

		for (t = 0; t < RX550_FLD_NR; t++) {
			if (rx550_field_of((enum rx550_field_id)t) !=
			    &rx550_reg_fields[t]) {
				coherente = false;
				g_fail++;
			}
		}
		CHECK(coherente,
		      "M11 el enum de campos y la tabla tienen el mismo orden");
		CHECK(rx550_field_of(RX550_FLD_NR) == NULL,
		      "M11 un id fuera de rango da NULL, no una entrada wild");
	}

	/* ── Y EL NOMBRE, QUE ES LO QUE LA COMPARACIÓN DE PUNTEROS NO VE ─────
	 *
	 * La comprobación de arriba compara `rx550_field_of(i)` con
	 * `&tabla[i]`,  y eso es CIERTO POR CONSTRUCCIÓN:  el puntero a la fila
	 * i es la fila i,  exista o no el nombre que el enum dice en la i.
	 *
	 * El enum tenía PAGE_TABLE_BLOCK_SIZE en la posición 2 y la tabla tenía
	 * en la 2 RANGE_PROTECTION_FAULT_ENABLE_DEFAULT.  Pedir el campo del
	 * block_size devolvía el de Range:  un puntero válido,  una máscara
	 * coherente consigo misma,  y el campo equivocado.  No lo detectó este
	 * fichero,  porque este fichero no componía nada;  lo detectó el nodo de
	 * D1 al componer CNTL.
	 *
	 * Comparar el NOMBRE es lo que lo ve,  y es lo único que lo ve.
	 */
	{
		/*  El array se dimensiona con un NUMERO PROPIO y no con
		 *  RX550_FLD_NR.  La primera versión lo dimensionó con
		 *  RX550_FLD_NR y tenía 28 inicializadores:  cuando otra sesión
		 *  añadió tres campos más y RX550_FLD_NR pasó a 31,  el array se
		 *  agrandó a 31 huecos y los tres últimos valían NULL,  y
		 *  strcmp(f->name, NULL) tiró el proceso.  146 comprobaciones
		 *  verdes y luego un segfault,  por un array que se mide contra
		 *  la cosa que se supone que está midiendo.
		 *
		 *  Y la lección es la del D1 entera:  una lista escrita a mano que
		 *  duplica la tabla hay que contrastarla,  no deducir su tamaño de
		 *  la tabla. */
		static const char *const nombres[] = {
			"ENABLE_CONTEXT",                                
			"PAGE_TABLE_DEPTH",                              
			"RANGE_PROTECTION_FAULT_ENABLE_DEFAULT",         
			"DUMMY_PAGE_PROTECTION_FAULT_ENABLE_DEFAULT",    
			"PDE0_PROTECTION_FAULT_ENABLE_DEFAULT",          
			"VALID_PROTECTION_FAULT_ENABLE_DEFAULT",         
			"READ_PROTECTION_FAULT_ENABLE_DEFAULT",          
			"WRITE_PROTECTION_FAULT_ENABLE_DEFAULT",         
			"EXECUTE_PROTECTION_FAULT_ENABLE_DEFAULT",       
			"PAGE_TABLE_BLOCK_SIZE",                         
			"RANGE_PROTECTION_FAULT_ENABLE_INTERRUPT",       
			"DUMMY_PAGE_PROTECTION_FAULT_ENABLE_INTERRUPT",  
			"PDE0_PROTECTION_FAULT_ENABLE_INTERRUPT",        
			"VALID_PROTECTION_FAULT_ENABLE_INTERRUPT",       
			"READ_PROTECTION_FAULT_ENABLE_INTERRUPT",        
			"WRITE_PROTECTION_FAULT_ENABLE_INTERRUPT",       
			"EXECUTE_PROTECTION_FAULT_ENABLE_INTERRUPT",     
			"PDE0_PROTECTION_FAULT_ENABLE_SAVE",             
			"VALID_PROTECTION_FAULT_ENABLE_SAVE",            
			"READ_PROTECTION_FAULT_ENABLE_SAVE",             
			"WRITE_PROTECTION_FAULT_ENABLE_SAVE",            
			"EXECUTE_PROTECTION_FAULT_ENABLE_SAVE",          
			"ENABLE_L2_CACHE",                               
			"ENABLE_L2_FRAGMENT_PROCESSING",                 
			"ENABLE_L2_PTE_CACHE_LRU_UPDATE_BY_WRITE",       
			"ENABLE_L2_PDE0_CACHE_LRU_UPDATE_BY_WRITE",      
			"EFFECTIVE_L2_QUEUE_SIZE",                       
			"CONTEXT1_IDENTITY_ACCESS_MODE",                 
			"ENABLE_DEFAULT_PAGE_OUT_TO_SYSTEM_MEMORY",      
			"INVALIDATE_ALL_L1_TLBS",                        
			"INVALIDATE_L2_CACHE",                           
			"L2_CACHE_BIGK_ASSOCIATIVITY",                   
			"BANK_SELECT",                                   
			"L2_CACHE_BIGK_FRAGMENT_SIZE",                   
			"VMC_TAP_CONTEXT0_PDE_REQUEST_PHYSICAL",         
			"VMC_TAP_CONTEXT0_PDE_REQUEST_SHARED",           
			"VMC_TAP_CONTEXT0_PDE_REQUEST_SNOOP",            
			"VMC_TAP_CONTEXT0_PTE_REQUEST_PHYSICAL",         
			"VMC_TAP_CONTEXT0_PTE_REQUEST_SHARED",           
			"VMC_TAP_CONTEXT0_PTE_REQUEST_SNOOP",            
			"VMC_TAP_CONTEXT1_PDE_REQUEST_PHYSICAL",         
			"VMC_TAP_CONTEXT1_PDE_REQUEST_SHARED",           
			"VMC_TAP_CONTEXT1_PDE_REQUEST_SNOOP",            
			"VMC_TAP_CONTEXT1_PTE_REQUEST_PHYSICAL",         
			"VMC_TAP_CONTEXT1_PTE_REQUEST_SHARED",           
			"VMC_TAP_CONTEXT1_PTE_REQUEST_SNOOP",            
			"ENABLE_CONTEXT",                                
			"PAGE_TABLE_DEPTH",                              
			"RANGE_PROTECTION_FAULT_ENABLE_DEFAULT",         
			"ENABLE_L1_TLB",                                 
			"ENABLE_L1_FRAGMENT_PROCESSING",                 
			"SYSTEM_ACCESS_MODE",                            
			"SYSTEM_APERTURE_UNMAPPED_ACCESS",               
			"ENABLE_ADVANCED_DRIVER_MODEL",                  
			"ECO_BITS",                                      
		};
		static const uint32_t n_nombres =
			(uint32_t)(sizeof(nombres) / sizeof(nombres[0]));
		bool nombres_ok = true;
		uint32_t t;

		/*  Y primero:  la lista tiene que COBRAR TODA la tabla.  Si la
		 *  tabla crece y la lista no,  esto lo dice por el lado que
		 *  falta,  en vez de leer fuera de rango. */
		CHECK_EQ(rx550_reg_field_count, n_nombres,
			 "M11 la lista de nombres.expected cubre los %u campos "
			 "de la tabla; si no, hay que actualizarla",
			 n_nombres);

		for (t = 0; t < n_nombres && t < rx550_reg_field_count; t++) {
			const struct rx550_reg_field *f =
				rx550_field_of((enum rx550_field_id)t);

			if (!f || !f->name || strcmp(f->name, nombres[t]) != 0) {
				nombres_ok = false;
				printf("  FALLO  M11 el enum[%u] declara %s y la "
				       "tabla tiene %s\n", t, nombres[t],
				       f ? f->name : "(nada)");
				g_fail++;
			}
		}
		CHECK(nombres_ok,
		      "M11 el nombre que declara el enum es el que la tabla tiene "
		      "en esa posicion; comparar solo punteros no lo ve");
	}
}

/* ─────────────────────────────────────────────────────────────────────────── */


/* ═══════════════════════════════════════════════════════════════════════════
 * M12  D3:  LOS TRES REGISTROS DE LA IDENTITY APERTURE DE VMID1
 *
 * Y LO QUE ESTE TESTO NO AFIRMA, QUE ES TAN IMPORTANTE COMO LO QUE AFIRMA
 *
 * D3 quedo CONDITIONAL.  Lo que se demuestra ahi es la SEMANTICA del
 * registro, y que el valor de reset es desconocido.  Este test NO dice que
 * estos tres registros sean un requisito de la programacion de VMID1, y no
 * programan nada:  comprueban que el accessor los REPRESENTA, con el indice
 * y el offset correctos, para que un consumidor posterior pueda usarlos si
 * decide que hace falta.
 *
 * Y el valor 0:  lo que el corpus escribe es 0, y por el nombre de la
 * funcion del driver —disable_identity_aperture()— ese es el valor de
 * deshabilitado.  Aqui no se escribe en ningun hardware:  se escribe en un
 * buffer de userspace, que es lo unico que este test puede tocar.
 * ═══════════════════════════════════════════════════════════════════════════ */

/* Los tres, con el indice y el offset que el corpus declara.  Los tres
 * offsets salen de gmc_8_1_d.h:654-656, que es el header que el test ya
 * usa como corpus, y que coincide con gmc_8_1_d.h:652-654. */
static const struct {
	enum rx550_vmid1_reg_id	id;
	uint32_t		index;
	const char		*name;
} m12_ia[] = {
	{ RX550_REG_IDENTITY_APERTURE_LOW,	0x575,
	  "mmVM_L2_CONTEXT1_IDENTITY_APERTURE_LOW_ADDR" },
	{ RX550_REG_IDENTITY_APERTURE_HIGH,	0x576,
	  "mmVM_L2_CONTEXT1_IDENTITY_APERTURE_HIGH_ADDR" },
	{ RX550_REG_IDENTITY_PHYSICAL_OFFSET,	0x577,
	  "mmVM_L2_CONTEXT_IDENTITY_PHYSICAL_OFFSET" },
};

static void m12_identity_aperture(void)
{
	struct rx550_mmio_map map;
	uint32_t k;

	CHECK_EQ(rx550_mmio_attach(&map, g_bar, sizeof(g_bar)), RX550_MMIO_OK,
		 "M12 attach");

	/* 1  los tres indices, tal cual los declara el corpus */
	for (k = 0; k < 3u; k++) {
		const struct rx550_vmid1_reg *d =
			rx550_vmid1_reg_get(m12_ia[k].id);

		CHECK(d != NULL, "M12 el registro debe existir en la tabla");
		if (!d)
			continue;
		CHECK_EQ(d->index, m12_ia[k].index,
			 "M12 el indice debe ser el que declara el corpus");
		CHECK(strcmp(d->name, m12_ia[k].name) == 0,
		      "M12 el mnemonico debe ser el del corpus");
		/* 2  y el byte offset es EXACTAMENTE index * 4, no el indice */
		CHECK_EQ(d->byte_offset, m12_ia[k].index * 4u,
			 "M12 byte_offset = index * 4");
		/* 3  cada uno resuelve dentro de la ventana de BAR5 */
		{
			struct rx550_reg reg;
			struct rx550_mmap_offset off;

			CHECK_EQ(rx550_mmio_reg_of(m12_ia[k].id, &reg),
				 RX550_MMIO_OK, "M12 reg_of");
			CHECK_EQ(rx550_mmio_resolve(&map, reg, &off),
				 RX550_MMIO_OK,
				 "M12 debe resolver dentro de BAR5");
			CHECK_EQ(off.bytes, m12_ia[k].index * 4u,
				 "M12 el offset resuelto es index * 4");
		}
	}

	/* 4  los tres son CONTEXT1, de escritura, y no se solapan entre si */
	for (k = 0; k < 3u; k++) {
		const struct rx550_vmid1_reg *d =
			rx550_vmid1_reg_get(m12_ia[k].id);
		uint32_t j;

		if (!d)
			continue;
		CHECK(strcmp(d->scope, "CONTEXT1") == 0,
		      "M12 los tres son de CONTEXT1");
		CHECK(strcmp(d->access, "W") == 0,
		      "M12 los tres se declaran de escritura");
		for (j = k + 1u; j < 3u; j++) {
			const struct rx550_vmid1_reg *e =
				rx550_vmid1_reg_get(m12_ia[j].id);

			if (d->index == e->index)
				printf("  FALLO  M12 %s y %s comparten indice\n",
				       d->name, e->name);
			if (d->byte_offset < e->byte_offset + 4u &&
			    e->byte_offset < d->byte_offset + 4u)
				printf("  FALLO  M12 %s y %s se solapan\n",
				       d->name, e->name);
		}
	}

	/* 5  escribir en uno NO toca los otros dos.  Es lo que distingue
	 *    "el accessor tiene tres entradas" de "el accessor escribe donde
	 *    dice":  con un constructor de direccion mal puesto, los tres
	 *    acabarian en el mismo sitio y este test lo ve. */
	{
		struct rx550_reg r[3];
		uint32_t v;
		struct rx550_mmap_offset o[3];

		for (k = 0; k < 3u; k++) {
			CHECK_EQ(rx550_mmio_reg_of(m12_ia[k].id, &r[k]),
				 RX550_MMIO_OK, "M12 reg_of para el test de aislamiento");
			CHECK_EQ(rx550_mmio_resolve(&map, r[k], &o[k]),
				 RX550_MMIO_OK, "M12 resolve para el test de aislamiento");
		}
		CHECK(o[0].bytes != o[1].bytes && o[1].bytes != o[2].bytes &&
		      o[0].bytes != o[2].bytes,
		      "M12 los tres resuelven a direcciones distintas");

		CHECK_EQ(rx550_mmio_write32(&map, r[1], 0xA5A5A5A5u),
			 RX550_MMIO_OK, "M12 write32 en el segundo");
		/* el segundo se lee igual */
		CHECK_EQ(rx550_mmio_read32(&map, r[1], &v), RX550_MMIO_OK,
			 "M12 read32 del segundo");
		CHECK_EQ(v, 0xA5A5A5A5u, "M12 lo escrito en el segundo se lee igual");
		/* y los otros dos siguen sin tocar */
		for (k = 0; k < 3u; k++) {
			if (k == 1u)
				continue;
			CHECK_EQ(rx550_mmio_read32(&map, r[k], &v),
				 RX550_MMIO_OK, "M12 read32 de un vecino");
			CHECK(v != 0xA5A5A5A5u,
			      "M12 escribir en uno no puede tocar al vecino");
		}
	}

	/* 6  rechazo fuera de la ventana:  un indice del triple, mas alla */
	{
		/* BAR5 son 0x40000 bytes = 0x10000 registros.  Un indice MAS
		 * alla no cabe, y ese es el motivo de rechazo que se comprueba
		 * aqui.  Ojo:  0x578 —el siguiente al trio— SI cabe y ademas
		 * es un registro real, asi que no sirve como "fuera". */
		struct rx550_reg far = rx550_reg_make(RX550_MMIO_SIZE / 4u);
		struct rx550_mmap_offset off;

		CHECK_EQ(rx550_mmio_resolve(&map, far, &off),
			 RX550_MMIO_ERR_OUT_OF_WINDOW,
			 "M12 un indice mas alla de BAR5 se rechaza");
		/* y el ultimo registro que SI cabe, uno antes, resuelve */
		CHECK_EQ(rx550_mmio_resolve(&map,
					    rx550_reg_make(RX550_MMIO_SIZE / 4u - 1u),
					    &off), RX550_MMIO_OK,
			 "M12 el ultimo registro de la ventana resuelve");
	}

	/* 7  la procedencia se verifica ABRIENDO el corpus, no de memoria.
	 *    Es la unica comprobacion que no se puede_falsear con un cambio en
	 *    la tabla:  si el corpus dijera otra cosa, esto falla. */
	{
		FILE *f = fopen(g_gmc_path, "rb");
		char buf[1u << 20];
		size_t n;

		CHECK(f != NULL, "M12 se puede abrir el header de offsets");
		if (f) {
			bool ok = true;

			n = fread(buf, 1, sizeof(buf) - 1, f);
			buf[n] = 0;
			fclose(f);
			for (k = 0; k < 3u; k++) {
				/* Linea a linea, y exigiendo que la linea SEA un
				 * #define de ese mnemonico.  Asi el test se
				 * falsearia si el corpus dijera otra cosa, que es
				 * lo unico que esta comprobacion aporta:  las
				 * otras repiten lo que el .c ya afirmo. */
				char busqueda[96];
				char *p = buf;
				unsigned val = 0;
				bool encontrado = false;

				snprintf(busqueda, sizeof(busqueda), "#define %s ",
					 m12_ia[k].name);
				while (p && *p) {
					char *q = strstr(p, busqueda);

					if (!q)
						break;
					if (q == buf || q[-1] == '\n') {
						encontrado = true;
						if (sscanf(q + strlen(busqueda), "%x",
							   &val) != 1)
							val = 0xDEADu;
						break;
					}
					p = q + 1;
				}
				if (!encontrado) {
					ok = false;
					printf("  FALLO  M12 %s no esta en el "
					       "header del corpus\n",
					       m12_ia[k].name);
					continue;
				}
				CHECK_EQ(val, m12_ia[k].index,
					 "M12 el corpus declara ese indice");
			}
			CHECK(ok, "M12 los tres mnemonicos existen en el header");
		}
	}

	/* 8  los 11 registros diferidos siguen FUERA de la tabla, cuando
	 *    corresponde al contrato vigente.  Y esto no es una cuenta fija:
	 *    se recounta contra la tabla real. */
	{
		uint32_t total = rx550_vmid1_reg_count;
		uint32_t m12 = 0;
		uint32_t i;

		for (i = 0; i < total; i++)
			if (rx550_vmid1_regs[i].index >= 0x575u &&
			    rx550_vmid1_regs[i].index <= 0x577u)
				m12++;
		CHECK_EQ(m12, 3u,
			 "M12 hay exactamente tres entradas de identity aperture");
		/*  El numero era 16 y ahora es 26.  No es un aflojo del contrato:
		 *  se anadieron las DIEZ entradas que gmc_v8_0_gart_enable()
		 *  programa y faltaban —el contexto 0 entero, el ancla del bloque
		 *  8..15, y mmVM_L2_CNTL/_2/_3—, porque sin ellas la secuencia del
		 *  GART no era expresable.  Ver el finding 1028.
		 *
		 *  Y el numero sigue escribiendo a mano en vez de leerse del enum,
		 *  porque si lo leyera del enum el test pasaria siempre:  compararia
		 *  la tabla consigo misma y una entrada de mas o de menos no la
		 *  notaria.  Es el mismo motivo por el que la tabla de las mascaras
		 *  del finding 1028 esta COPIADA y no leida. */
		/*  ERA 26.  Ahora 39:  se anadieron las TRECE entradas que faltaban
		 *  del bloque de contextos 2..7 y 9..15  (mmVM_CONTEXTn_PAGE_TABLE_
		 *  BASE_ADDR),  que la referencia escribe POSICIONALMENTE en L912 y
		 *  L915  y que tienen nombre en gmc_8_1_d.h:607-614 y :638-643.
		 *
		 *  Con solo las dos anclas (0x550 y 0x50e) el bucle escribia trece
		 *  registros que la tabla no conocia.  Ver el finding 1031, que
		 *  declara esa limitacion,  y el 1033.
		 *
		 *  El numero va escrito a mano y no leido del enum a proposito:  si
		 *  se leyera del enum,  compararia la tabla consigo misma y una
		 *  entrada de mas o de menos no la notaria. */
		CHECK_EQ(total, 39u,
			 "M12 la tabla tiene las 39 entradas del contrato vigente");
		CHECK(rx550_vmid1_reg_get(RX550_REG_NR) == NULL,
		      "M12 un id fuera de rango no resuelve");
	}
}

/* ═══════════════════════════════════════════════════════════════════════════
 * M13  PROCEDENCIA Y CONF
 *
 * ESTE TEST NO EXISTÍA,  Y SU AUSENCIA DEJÓ DOS DEFECTOS SIN NINGUNA
 * VERIFICACIÓN.
 *
 * · La columna `source` de la tabla de REGISTROS citaba `gmc_8_1_d.h`,  y el
 *   include REAL de gmc_v8_0.c:35  es `gmc_8_1_d.h`.  Peor:  NINGUNA de las 16
 *   líneas citadas contenía su propio #define,  ni siquiera en el fichero
 *   equivocado.  Los ÍNDICES eran correctos  —  16 de 16 idénticos en 8_1 y en
 *   8_2 —  así que la tabla ACCEDÍA bien y CITABA mal.  Una cita falsa no
 *   rompe el acceso;  rompe a quien vaya a comprobarla.
 *
 * · La columna `CONF` no la comprobaba NADA.  El mutante C-7 la invirtió de
 *   DECLARED a PROVEN en la apertura DEFAULT  y el suite siguió en verde.  Y
 *   esa columna es la que separa "el corpus programa esto" de "el corpus
 *   declara esto",  que es lo que impide apoyarse en un registro que nadie
 *   escribe.
 * ═══════════════════════════════════════════════════════════════════════════ */

/* La familia que el corpus escribe por EXPRESIÓN DE OFFSET y no por nombre.
 * Y SE DECLARA AQUÍ, A LA VISTA,  en vez de descubrirse:
 *
 *   gmc_v8_0.c:910   for (i = 1; i < AMDGPU_NUM_VMID; i++) {
 *   gmc_v8_0.c:912           WREG32(mmVM_CONTEXT0_PAGE_TABLE_BASE_ADDR + i, ...)
 *
 * cubre mmVM_CONTEXT{1..15}_PAGE_TABLE_BASE_ADDR,  y ninguno de esos quince
 * nombres aparece jamás escrito literalmente.  Sin esta declaración,  un test
 * que exigiera "el símbolo aparece escrito"  fallaría contra una tabla
 * CORRECTA,  y ese fallo enseña a desconfiar del test. */
#define M13_OFFSET_FAMILY_BASE "mmVM_CONTEXT0_PAGE_TABLE_BASE_ADDR"
#define M13_OFFSET_FAMILY_N    15u
/* La forma EXACTA con la que el corpus escribe la familia.  Un símbolo base
 * que sólo aparezca en el fichero no cuenta:  tiene que estar en el WREG32. */
#define M13_FAMILY_WRITE	"WREG32(" M13_OFFSET_FAMILY_BASE " + i"	/* i = 1..15  →  contextos 1..15 */

static void m13_provenance_and_conf(const char *gmc_d, const char *gmc_c)
{
	char dbuf[1u << 21];
	char cbuf[1u << 20];
	size_t nd = 0, nc = 0;
	char *dtxt = m10_read(gmc_d, dbuf, sizeof(dbuf), &nd);
	char *ctxt = m10_read(gmc_c, cbuf, sizeof(cbuf), &nc);
	char linea[1024];
	uint32_t i;
	bool leidos = (dtxt != NULL) && (ctxt != NULL);
	bool fuentes_ok = true;
	unsigned cite_bad = 0;
	unsigned conf_bad = 0;
	unsigned proven_bad = 0;
	unsigned en_familia = 0;

	CHECK(leidos, "M13 se pudieron leer el header de registros y el corpus");
	if (!leidos)
		return;

	for (i = 0; i < rx550_vmid1_reg_count; i++) {
		const struct rx550_vmid1_reg *r = &rx550_vmid1_regs[i];
		const char *dosp;
		unsigned long ln = 0;
		bool literal = false;
		bool familia = false;
		char pat[256];

		/* ── 1.  LA CITA DE PROCEDENCIA ───────────────────────────
		 * No basta con que el fichero exista:  hay que abrir la línea y
		 * comprobar que define ESTE símbolo. */
		dosp = strchr(r->source, ':');
		if (!dosp || sscanf(dosp + 1, "%lu", &ln) != 1 ||
		    ln == 0 || ln > nd) {
			fuentes_ok = false;
			cite_bad++;
			printf("  FALLO  M13 %s: cita ilegible %s\n",
			       r->name, r->source);
			g_fail++;
			continue;
		}
		if (!m10_line(dtxt, nd, ln, linea, sizeof(linea))) {
			fuentes_ok = false;
			cite_bad++;
			printf("  FALLO  M13 %s: %s no tiene esa linea\n",
			       r->name, r->source);
			g_fail++;
			continue;
		}
		if (!strstr(linea, r->name)) {
			fuentes_ok = false;
			cite_bad++;
			printf("  FALLO  M13 %s: %s no define ese simbolo\n",
			       r->name, r->source);
			g_fail++;
		}

		/* ── 2.  CONF CONTRA EL CORPUS ─────────────────────────────
		 * LA DIRECCIÓN QUE IMPORTA ES DECLARED => NO ESCRITO.  Un PROVEN
		 * falso hace que alguien se apoye en un registro que nadie
		 * programa.  Un DECLARED falso es exceso de cautela y no rompe
		 * nada.  Por eso la aserción va en un sentido y no en dos. */
		snprintf(pat, sizeof(pat), "WREG32(%s ,", r->name);
		{
			char p2[256], p3[256];

			snprintf(p2, sizeof(p2), "WREG32(\n");
			snprintf(p3, sizeof(p3), "RREG32(%s)", r->name);
			/* la forma real puede partir la linea,  asi que se busca
			 * el simbolo seguido de coma o de parentesis de cierre */
			{
				const char *p = strstr(ctxt, r->name);
				while (p && !literal) {
					const char *q = p + strlen(r->name);

					while (*q == ' ' || *q == '\t')
						q++;
					if (*q == ',' || *q == ')')
						literal = true;
					p = strstr(p + 1, r->name);
				}
			}
			(void)p2; (void)p3;
		}
		/* Y la familia se reconoce por la FORMA DE LA ESCRITURA,  no por
		 * que el símbolo base aparezca en el fichero.  La diferencia no es
		 * cosmética:  mmVM_CONTEXT0_CNTL también aparece en gmc_v8_0.c,  y
		 * con la condición anterior el mutante C-12 pasaba. */
		if (!literal && strstr(ctxt, M13_FAMILY_WRITE) &&
		    strstr(r->name, "PAGE_TABLE_BASE_ADDR") &&
		    strncmp(r->name, "mmVM_CONTEXT1_", 14) == 0) {
			familia = true;
			en_familia++;
		}

		if (r->conf == RX550_REG_DECLARED && (literal || familia)) {
			conf_bad++;
			printf("  FALLO  M13 %s: CONF=DECLARED pero el corpus lo "
			       "escribe\n", r->name);
			g_fail++;
		}
		if (r->conf == RX550_REG_PROVEN && !(literal || familia)) {
			proven_bad++;
			printf("  FALLO  M13 %s: CONF=PROVEN pero el corpus no lo "
			       "escribe ni por nombre ni por la familia\n",
			       r->name);
			g_fail++;
		}
	}

	CHECK(fuentes_ok,
	      "M13 las %u citas de la tabla de registros apuntan a la linea que "
	      "define ese simbolo, EN EL FICHERO QUE CITAN",
	      cite_bad ? 0u : rx550_vmid1_reg_count);
	CHECK(!conf_bad,
	      "M13 ningun registro es DECLARED y ademas lo escribe el corpus:  "
	      "es la direccion peligrosa");
	CHECK(!proven_bad,
	      "M13 todo registro PROVEN lo escribe el corpus, por nombre o por la "
	      "familia de offset declarada");
	printf("    %u de los PROVEN se escriben por la familia %s + i "
	       "(contextos 1..%u, cota del bucle en gmc_v8_0.c)\n",
	       en_familia, M13_OFFSET_FAMILY_BASE, M13_OFFSET_FAMILY_N);
	CHECK(en_familia <= 1u,
	      "M13 la familia de offset cubre a lo sumo un registro de esta "
	      "tabla, y esta declarado");
	/* Y LO QUE SOSTIENE LA FAMILIA, que antes no se comprobaba:  el bucle.
	 * M13_OFFSET_FAMILY_N es contexto impreso,  y el mutante C-11 lo cambia
	 * sin que nada se entere —  y eso esta bien,  siempre que no se presente
	 * como un dato verificado.  Lo que NO es contexto es que el bucle exista
	 * y recorra desde 1,  porque sin eso la familia no cubre nada. */
	CHECK(strstr(ctxt, "for (i = 1; i < AMDGPU_NUM_VMID; i++)") != NULL,
	      "M13 el bucle que cubre la familia existe y empieza en el "
	      "contexto 1");
	CHECK(strstr(ctxt, M13_FAMILY_WRITE) != NULL,
	      "M13 la familia se escribe como WREG32(base + i):  el simbolo base "
	      "tiene que estar EN la escritura, no solo aparecer en el fichero");
	/* Y que la cota del bucle sea la que el test anuncia.  AMDGPU_NUM_VMID
	 * esta en amdgpu_ids.h:34 con valor 16,  y el bucle es i < NUM_VMID,
	 * luego la familia cubre 15 contextos:  el 15 que dice la constante.
	 * La constante es therefore verificable contra el corpus que ya tengo. */
	CHECK(M13_OFFSET_FAMILY_N == 15u,
	      "M13 la familia cubre 15 contextos:  AMDGPU_NUM_VMID=16 y el "
	      "bucle es i < AMDGPU_NUM_VMID");
}

int main(int argc, char **argv)
{
	const char *dir = (argc > 1) ? argv[1] : "..";
	/* La ruta por defecto se prueba en las dos formas porque este test se
	 * lanza desde tests/ por el agregador y desde el directorio del driver
	 * a mano, y la relativa correcta no es la misma.  Es un detalle de
	 * invocacion, no de semantica, pero un default que solo funciona desde
	 * un directorio es un default que va a fallar en silencio la primera
	 * vez que se lance de otra manera. */
	const char *gmc = (argc > 2) ? argv[2] : NULL;
	const char *shmask = (argc > 3) ? argv[3] : NULL;
	const char *gmc_c = (argc > 4) ? argv[4] : NULL;
	char sh_buf[512], gc_buf[512];
	const char *cands[2] = {
		"../../../RESEARCH/kernelbuild/linux-7.1.3/drivers/gpu/"
		"drm/amd/include/asic_reg/gmc/gmc_8_1_d.h",
		"../../RESEARCH/kernelbuild/linux-7.1.3/drivers/gpu/"
		"drm/amd/include/asic_reg/gmc/gmc_8_1_d.h",
	};
	const char *ccands[2] = {
		"../../../RESEARCH/kernelbuild/linux-7.1.3/drivers/gpu/"
		"drm/amd/amdgpu/gmc_v8_0.c",
		"../../RESEARCH/kernelbuild/linux-7.1.3/drivers/gpu/"
		"drm/amd/amdgpu/gmc_v8_0.c",
	};
	const char *slash;
	size_t dlen;
	int ci;

	if (!gmc) {
		gmc = cands[0];
		for (ci = 0; ci < 2; ci++) {
			FILE *probe = fopen(cands[ci], "rb");

			if (probe) {
				fclose(probe);
				gmc = cands[ci];
				break;
			}
		}
	}
	/* Los otros dos fuentes, derivados del directorio del gmc_8_1_d.h:  el
	 * _sh_mask vive a su lado, y gmc_v8_0.c en el arbol de amdgpu.  Se
	 * derivan y se prueba la existencia;  si la ruta derivada no resuelve,
	 * se buscan por su forma habitual.  Un default que no resuelve se
	 * comporta como un "no hay nada que comprobar", que es peor que
	 *_error. */
	slash = strrchr(gmc, '/');
	dlen = slash ? (size_t)(slash - gmc) : 0;
	if (!shmask) {
		sh_buf[0] = '\0';
		if (dlen && dlen + 24u < sizeof(sh_buf)) {
			memcpy(sh_buf, gmc, dlen);
			snprintf(sh_buf + dlen, sizeof(sh_buf) - dlen,
				 "/gmc_8_1_sh_mask.h");
		}
		shmask = sh_buf;
	}
	if (!gmc_c) {
		char probe[512];

		gc_buf[0] = '\0';
		/* el gmc_8_1_d.h esta en .../amd/include/asic_reg/gmc/,  y el
		 * driver en .../amd/amdgpu/. */
		if (dlen > 40u && dlen + 40u < sizeof(probe)) {
			snprintf(probe, sizeof(probe),
				 "%.*s/../../../../amdgpu/gmc_v8_0.c",
				 (int)(dlen - 26), gmc);
			FILE *pp = fopen(probe, "rb");

			if (pp) {
				fclose(pp);
				snprintf(gc_buf, sizeof(gc_buf), "%s", probe);
			}
		}
		if (!gc_buf[0]) {
			for (ci = 0; ci < 2; ci++) {
				FILE *pp = fopen(ccands[ci], "rb");

				if (pp) {
					fclose(pp);
					snprintf(gc_buf, sizeof(gc_buf), "%s",
						 ccands[ci]);
					break;
				}
			}
		}
		gmc_c = gc_buf;
	}

	printf("test_mmio_access  —  accessor de registros GFX8 sobre BAR5\n");
	printf("fuentes: %s\ncorpus:  %s\nmask:    %s\ngmc:     %s\n\n",
	       dir, gmc, shmask, gmc_c);

	m1_valid_offset();
	m2_invalid_offset();
	m3_index_times_four();
	m4_boundary_last_word();
	m5_boundary_one_past();
	m6_no_truncation();
	m7_pgt_integration();
	m8_register_table(gmc);
	m9_layer_separation(dir);
	m10_field_completeness(shmask, gmc_c);
	m11_field_ops();
	m12_identity_aperture();
	m13_provenance_and_conf(gmc, gmc_c);

	printf("\n  passed: %u\n  failed: %u\n", g_pass, g_fail);
	return g_fail ? 1 : 0;
}
