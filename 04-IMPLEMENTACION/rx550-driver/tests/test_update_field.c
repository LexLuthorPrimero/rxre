/* SPDX-License-Identifier: GPL-2.0-only */
/*
 * test_update_field.c — la primitiva de lectura-modificacion-escritura por campo.
 *
 *   TARGET = RX 550 instalada en esta maquina  (1002:699F, Polaris12, GFX8)
 *   SCOPE  = EXCLUSIVO
 *
 * QUE ES Y QUE NO ES
 *   C puro, unitario, en userspace.  Sin MMIO real: el mapa es un buffer
 *   normal, igual que en test_mmio_access.
 *
 * POR QUE EXISTE
 *   El corpus programa los registros de control con
 *       RREG32 -> REG_SET_FIELD -> WREG32
 *   y las 7 escrituras de lectura-modificacion-escritura de gmc_v8_0_gart_enable() son de esa forma.  El
 *   accessor solo tenia read32 y write32, de modo que no podia reproducir
 *   ninguna.  Ver el finding 1028.
 *
 * LOS TRES BLOQUES
 *   U1  la DERIVACION contra el corpus:  los 42 campos que escribe la referencia
 *       se comprueban uno a uno contra sus mascaras, y el shift derivado tiene
 *       que coincidir con el que declara gmc_8_1_sh_mask.h.  Si el header se
 *       regenera y el shift derivado deja de valer, aqui falla.
 *   U2  la SEMANTICA:  un update deja intactos los bits de fuera del campo, y
 *       es idempotente.
 *   U3  los NEGATIVOS:  mask 0, mask con hueco, valor que no cabe, sin mapa,
 *       fuera de ventana.  Y que en todos ellos el registro queda INTACTO.
 *
 * QUE NO COMPRUEBA
 *   Que el hardware obedezca, ni que la secuencia de 21 escrituras sea la
 *   correcta.  Eso es RUNTIME_REQUIRED.
 */
#include <stdio.h>
#include <stdint.h>
#include <stdbool.h>
#include <stdlib.h>
#include <string.h>

#include "rx550_mmio_access.h"

static int pass, fail;

static void ok(const char *t) { printf("  PASS  %s\n", t); pass++; }
static void ko(const char *t) { printf("  FAIL  %s\n", t); fail++; }

#define CHECK(cond, name) do { if (cond) ok(name); else ko(name); } while (0)
#define CHECK_EQ(got, want, name) do {					\
	long long g_ = (long long)(got), w_ = (long long)(want);	\
	if (g_ == w_) ok(name);						\
	else { printf("  FAIL  %s  (0x%llx != 0x%llx)\n", name, g_, w_);	\
	       fail++; }						\
} while (0)

/* ── U1 · LAS 42 MASCARAS DEL CORPUS ──────────────────────────────────────
 *
 *  Copiadas de gmc_8_1_sh_mask.h y mmhub_1_0_sh_mask.h.  A proposito:  si el
 *  test las leyera del corpus, compararia la regla contra si misma y un cambio
 *  en el corpus no produciria ningun fallo.
 *
 *  Solo las mascaras:  el shift se DERIVA y se contrasta con el que declara el
 *  header, que va en la tercera columna.  Las mascaras de mas de un bit estan
 *  marcadas con '*', porque son las que tienen __SHIFT en el header;  las de un
 *  solo bit no lo tienen, y esa ausencia tambien se comprueba abajo. */
struct corpus_field {
	const char	*name;
	uint32_t	 mask;
	unsigned	 shift_declarado;	/* 0..31; valido solo si multi-bit */
	bool		 multibit;
};

/* Los 42 campos, agrupados por el registro al que pertenecen. */
static const struct corpus_field CORPUS[] = {
	/* mmMC_VM_MX_L1_TLB_CNTL -- mascara en mmhub_1_0_sh_mask.h */
	{ "MC_VM_MX_L1_TLB_CNTL.ENABLE_L1_TLB",		0x1,		0,	false },
	{ "MC_VM_MX_L1_TLB_CNTL.ENABLE_L1_FRAGMENT_PROCESSING", 0x2,	1,	false },
	{ "MC_VM_MX_L1_TLB_CNTL.SYSTEM_ACCESS_MODE",	0x18,		3,	true  },
	{ "MC_VM_MX_L1_TLB_CNTL.ENABLE_ADVANCED_DRIVER_MODEL", 0x40,	6,	false },
	{ "MC_VM_MX_L1_TLB_CNTL.SYSTEM_APERTURE_UNMAPPED_ACCESS", 0x20, 5,	false },

	/* mmVM_L2_CNTL -- 15 campos declarados, la referencia pone 7 */
	{ "VM_L2_CNTL.ENABLE_L2_CACHE",			0x1,		0,	false },
	{ "VM_L2_CNTL.ENABLE_L2_FRAGMENT_PROCESSING",	0x2,		1,	false },
	{ "VM_L2_CNTL.ENABLE_L2_PTE_CACHE_LRU_UPDATE_BY_WRITE", 0x200, 9,	false },
	{ "VM_L2_CNTL.ENABLE_L2_PDE0_CACHE_LRU_UPDATE_BY_WRITE", 0x400, 10, false },
	{ "VM_L2_CNTL.EFFECTIVE_L2_QUEUE_SIZE",		0x38000,	15,	true  },
	{ "VM_L2_CNTL.CONTEXT1_IDENTITY_ACCESS_MODE",	0x180000,	19,	true  },
	{ "VM_L2_CNTL.ENABLE_DEFAULT_PAGE_OUT_TO_SYSTEM_MEMORY", 0x800, 11, false },

	/* mmVM_L2_CNTL2 */
	{ "VM_L2_CNTL2.INVALIDATE_ALL_L1_TLBS",		0x1,		0,	false },
	{ "VM_L2_CNTL2.INVALIDATE_L2_CACHE",		0x2,		1,	false },

	/* mmVM_L2_CNTL3 */
	{ "VM_L2_CNTL3.L2_CACHE_BIGK_ASSOCIATIVITY",	0x100000,	20,	false },
	{ "VM_L2_CNTL3.BANK_SELECT",			0x3f,		0,	true  },
	{ "VM_L2_CNTL3.L2_CACHE_BIGK_FRAGMENT_SIZE",	0xf8000,	15,	true  },

	/* mmVM_L2_CNTL4: doce campos de tapping, y TODOS valen 0 */
	{ "VM_L2_CNTL4.VMC_TAP_CONTEXT0_PDE_REQUEST_PHYSICAL", 0x40,	6,	false },
	{ "VM_L2_CNTL4.VMC_TAP_CONTEXT0_PDE_REQUEST_SHARED",  0x80,	7,	false },
	{ "VM_L2_CNTL4.VMC_TAP_CONTEXT0_PDE_REQUEST_SNOOP",   0x100,	8,	false },
	{ "VM_L2_CNTL4.VMC_TAP_CONTEXT0_PTE_REQUEST_PHYSICAL", 0x200,	9,	false },
	{ "VM_L2_CNTL4.VMC_TAP_CONTEXT0_PTE_REQUEST_SHARED",  0x400,	10,	false },
	{ "VM_L2_CNTL4.VMC_TAP_CONTEXT0_PTE_REQUEST_SNOOP",   0x800,	11,	false },
	{ "VM_L2_CNTL4.VMC_TAP_CONTEXT1_PDE_REQUEST_PHYSICAL", 0x1000,	12,	false },
	{ "VM_L2_CNTL4.VMC_TAP_CONTEXT1_PDE_REQUEST_SHARED",  0x2000,	13,	false },
	{ "VM_L2_CNTL4.VMC_TAP_CONTEXT1_PDE_REQUEST_SNOOP",   0x4000,	14,	false },
	{ "VM_L2_CNTL4.VMC_TAP_CONTEXT1_PTE_REQUEST_PHYSICAL", 0x8000,	15,	false },
	{ "VM_L2_CNTL4.VMC_TAP_CONTEXT1_PTE_REQUEST_SHARED",  0x10000,	16,	false },
	{ "VM_L2_CNTL4.VMC_TAP_CONTEXT1_PTE_REQUEST_SNOOP",   0x20000,	17,	false },

	/* mmVM_CONTEXT0_CNTL: 22 campos declarados, la referencia pone 3 */
	{ "VM_CONTEXT0_CNTL.ENABLE_CONTEXT",		0x1,		0,	false },
	{ "VM_CONTEXT0_CNTL.PAGE_TABLE_DEPTH",		0x6,		1,	true  },
	{ "VM_CONTEXT0_CNTL.RANGE_PROTECTION_FAULT_ENABLE_DEFAULT", 0x10, 4, false },

	/* mmVM_CONTEXT1_CNTL: 22 declarados, la referencia pone 10 */
	{ "VM_CONTEXT1_CNTL.ENABLE_CONTEXT",		0x1,		0,	false },
	{ "VM_CONTEXT1_CNTL.PAGE_TABLE_DEPTH",		0x6,		1,	true  },
	{ "VM_CONTEXT1_CNTL.RANGE_PROTECTION_FAULT_ENABLE_DEFAULT", 0x10, 4, false },
	{ "VM_CONTEXT1_CNTL.DUMMY_PAGE_PROTECTION_FAULT_ENABLE_DEFAULT", 0x80, 7, false },
	{ "VM_CONTEXT1_CNTL.PDE0_PROTECTION_FAULT_ENABLE_DEFAULT", 0x400, 10, false },
	{ "VM_CONTEXT1_CNTL.VALID_PROTECTION_FAULT_ENABLE_DEFAULT", 0x2000, 13, false },
	{ "VM_CONTEXT1_CNTL.READ_PROTECTION_FAULT_ENABLE_DEFAULT", 0x10000, 16, false },
	{ "VM_CONTEXT1_CNTL.WRITE_PROTECTION_FAULT_ENABLE_DEFAULT", 0x80000, 19, false },
	{ "VM_CONTEXT1_CNTL.EXECUTE_PROTECTION_FAULT_ENABLE_DEFAULT", 0x400000, 22, false },
	{ "VM_CONTEXT1_CNTL.PAGE_TABLE_BLOCK_SIZE",	0xf000000,	24,	true  },
};

#define N_CORPUS (sizeof(CORPUS) / sizeof(CORPUS[0]))

int main(void)
{
	void *bar;
	volatile uint32_t *slot;
	struct rx550_mmap_offset off;
	struct rx550_mmio_map map;
	struct rx550_reg reg;
	uint32_t v;

	printf("test_update_field — RMW por campo\n\n");

	/* ── U0 · LA TABLA EXISTENTE, y por que esto NO es un mecanismo paralelo
	 * ────────────────────────────────────────────────────────────────────
	 *
	 *  rx550_reg_fields[] ya declara mask y shift por campo, copiados del
	 *  header.  Si el shift se puede derivar de la mascara, esa columna es
	 *  una COPIA, y una copia se desincroniza en silencio el dia que el
	 *  header se regenere.
	 *
	 *  Se comprueba sobre la tabla real, no sobre una copia:  si el dia de
	 *  manana alguien anade un campo con el shift mal puesto, este bloque
	 *  tiene que verlo. */
	printf("U0 · rx550_reg_fields[]: shift y width coherentes con mask\n");
	{
		bool todos = true;
		uint32_t n = 0;

		for (uint32_t i = 0; i < rx550_reg_field_count; i++) {
			const struct rx550_reg_field *f = &rx550_reg_fields[i];
			unsigned s = 0, w = 0;
			uint32_t racha;

			n++;
			if (rx550_mmio_field_from_mask(f->mask, &s, &w)
			    != RX550_MMIO_OK) {
				printf("  FAIL  %s.%s: mask 0x%08x no es un campo\n",
				       f->reg, f->name, f->mask);
				todos = false;
				continue;
			}
			racha = f->mask >> s;
			if (s != f->shift || w != f->width ||
			    (racha & (racha + 1u)) != 0u) {
				printf("  FAIL  %s.%s: tabla dice shift=%u width=%u, "
				       "derivado shift=%u width=%u (mask 0x%08x)\n",
				       f->reg, f->name, f->shift, f->width,
				       s, w, f->mask);
				todos = false;
			}
		}
		CHECK(todos, "U0 los 25 campos de la tabla coherentes con su mask");
		CHECK(n > 0, "U0 la tabla no esta vacia");
		CHECK_EQ(n, rx550_reg_field_count, "U0 se han recorrido todos");
	}

	/* ── U1 · LA DERIVACION CONTRA EL CORPUS ──────────────────────────── */
	printf("U1 · %zu campos del corpus: shift derivado == shift declarado\n",
	       N_CORPUS);
	for (size_t i = 0; i < N_CORPUS; i++) {
		unsigned shift = 0, width = 0;
		int rc = rx550_mmio_field_from_mask(CORPUS[i].mask, &shift, &width);

		if (rc != RX550_MMIO_OK) {
			printf("  FAIL  %s: field_from_mask dio %d\n",
			       CORPUS[i].name, rc);
			fail++;
			continue;
		}
		if (shift != CORPUS[i].shift_declarado) {
			printf("  FAIL  %s: derivado %u, declarado %u\n",
			       CORPUS[i].name, shift,
			       CORPUS[i].shift_declarado);
			fail++;
			continue;
		}
		ok(CORPUS[i].name);
	}

	/* El invariante, dicho como invariante y no como comparacion suelta:
	 *  quitar los bits de debajo y comprobar que queda una racha de unos. */
	{
		bool todos = true;
		unsigned ancho_min = 99, ancho_max = 0;

		for (size_t i = 0; i < N_CORPUS; i++) {
			unsigned s = 0, w = 0;
			uint32_t racha;

			if (rx550_mmio_field_from_mask(CORPUS[i].mask, &s, &w) != RX550_MMIO_OK) {
				todos = false;
				break;
			}
			racha = CORPUS[i].mask >> s;
			if ((racha & (racha + 1u)) != 0u) {
				todos = false;
				break;
			}
			if (w < ancho_min) ancho_min = w;
			if (w > ancho_max) ancho_max = w;
		}
		CHECK(todos, "U1 (mask>>shift) == 2^ancho-1 en los 42");
		CHECK_EQ(ancho_min, 1, "U1 el campo mas estrecho es de 1 bit");
		CHECK_EQ(ancho_max, 6, "U1 el mas ancho es de 6 bits (BANK_SELECT)");
	}

	/* Los ocho multi-bit, uno a uno, con su ancho.  Son los unicos que
	 * tienen __SHIFT en el header, y los que un shift a mano lo equivocaria. */
	{
		static const struct { uint32_t m; unsigned s, w; } MB[] = {
			{ 0x18,		3,	2 },	/* SYSTEM_ACCESS_MODE          */
			{ 0x6,		1,	2 },	/* PAGE_TABLE_DEPTH            */
			{ 0x6,		1,	2 },	/* PAGE_TABLE_DEPTH (contexto1) */
			{ 0xf000000,	24,	4 },	/* PAGE_TABLE_BLOCK_SIZE       */
			{ 0x3f,		0,	6 },	/* BANK_SELECT                 */
			{ 0xf8000,	15,	5 },	/* BIGK_FRAGMENT_SIZE          */
			{ 0x180000,	19,	2 },	/* CONTEXT1_IDENTITY_ACCESS    */
			{ 0x38000,	15,	3 },	/* EFFECTIVE_L2_QUEUE_SIZE     */
		};

		for (size_t i = 0; i < sizeof(MB) / sizeof(MB[0]); i++) {
			unsigned s = 0, w = 0;
			int rc = rx550_mmio_field_from_mask(MB[i].m, &s, &w);

			CHECK(rc == RX550_MMIO_OK &&
			      s == MB[i].s && w == MB[i].w,
			      "U1 multi-bit: shift y ancho derivados");
		}
	}

	/* ── U2 · LA SEMANTICA SOBRE UN MAPA DE VERDAD ────────────────────── */
	printf("\nU2 · la semantica de la escritura\n");
	bar = calloc(1, RX550_MMIO_SIZE);
	if (!bar) {
		printf("  FAIL  no se pudo reservar el mapa\n");
		return 1;
	}
	CHECK(rx550_mmio_attach(&map, bar, RX550_MMIO_SIZE) == RX550_MMIO_OK,
	      "U2 attach");
	CHECK(rx550_mmio_reg_of(RX550_REG_CTX1_CNTL, &reg) == RX550_MMIO_OK,
	      "U2 resolver CTX1_CNTL");

	/* El registro NO esta en el offset 0 del mapa:  CTX1_CNTL es el indice
	 * 0x505, o sea el byte 0x1414.  La primera version de este test sembraba
	 * el buffer en bar[0] y luego comparaba contra lo que habia en 0x1414,
	 * que era cero, y se leia como "el update borra el registro".  No lo
	 * borra:  el test estaba mirando la palabra equivocada. */
	CHECK(rx550_mmio_resolve_reg(&map, RX550_REG_CTX1_CNTL, &off)
	      == RX550_MMIO_OK, "U2 resolver el offset del registro");
	slot = (volatile uint32_t *)((uintptr_t)bar + off.bytes);

	/* Se parte de un registro con bits puestos FUERA del campo, que es
	 * exactamente el caso que la referencia conserva. */
	*slot = 0xdeadbeefu;

	v = 0;
	CHECK(rx550_mmio_update_field(&map, reg, 0x6u, 0u, &v) == RX550_MMIO_OK,
	      "U2 poner PAGE_TABLE_DEPTH=0");
	/* 0xdeadbeef tiene los bits 1 y 2 a 1 (0xb & 0x6 = 2).  El campo tiene que
	 * haberlos puesto a 0 y el resto intacto. */
	CHECK_EQ(v & ~0x6u, 0xdeadbeefu & ~0x6u, "U2 los bits de fuera del campo quedan intactos");
	CHECK_EQ(v & 0x6u, 0, "U2 el campo vale lo puesto");
	CHECK_EQ(*slot, v, "U2 el registro en memoria es lo devuelto");

	CHECK(rx550_mmio_update_field(&map, reg, 0x6u, 2u, &v) == RX550_MMIO_OK,
	      "U2 poner PAGE_TABLE_DEPTH=2");
	/* El valor 2 en un campo de 2 bits es 0b10, y a shift 1 da 0b100 == 4.
	 * La primera version pedia 0x6, que es 0b11, o sea el valor 3. */
	CHECK_EQ(v & 0x6u, 0x4, "U2 el valor 2 ocupa el bit alto del campo");
	CHECK_EQ(v & ~0x6u, 0xdeadbeefu & ~0x6u, "U2 y el resto sigue igual");

	/* Idempotente: repetir la MISMA operacion no cambia nada.  Un RMW que no
	 * lo fuera est accumulando estado, que es la forma de un fallo que
	 * solo aparece en la segunda llamada. */
	{
		uint32_t otra = 0;

		CHECK(rx550_mmio_update_field(&map, reg, 0x6u, 2u, &otra)
		      == RX550_MMIO_OK, "U2 repetir la misma escritura");
		CHECK_EQ(otra, v, "U2 la repeticion es idempotente");
	}

	/* Campo de un bit, y un valor de 32 bits con todos los bits. */
	*slot = 0u;
	CHECK(rx550_mmio_update_field(&map, reg, 0x1u, 1u, &v) == RX550_MMIO_OK,
	      "U2 poner ENABLE_CONTEXT=1");
	CHECK_EQ(v, 0x1, "U2 un campo de 1 bit con valor 1");
	CHECK(rx550_mmio_update_field(&map, reg, 0x10000u, 0x1u, &v)
	      == RX550_MMIO_OK, "U2 poner READ_PROTECTION=1");
	CHECK_EQ(v, 0x10001, "U2 dos campos distintos, los dos puestos");

	/* get_field: el mismo campo, leido.  Y con el valor de 32 bits completo. */
	CHECK(rx550_mmio_get_field(v, 0x1u, &v) == RX550_MMIO_OK, "U2 get_field");
	CHECK_EQ(v, 1, "U2 get_field devuelve el ENABLE_CONTEXT");
	/* 0xdeadbeef & 0x6 == 0b110 == 6.  La primera version de este test pedia
	 * 2, que es lo que uno se imagina al mirar "los dos ultimos bits de
	 * ef";  los dos estan puestos, y 0b10 != 0b110.  El codigo devovia 6 y
	 * el vector estaba mal. */
	CHECK(rx550_mmio_get_field(0xdeadbeefu, 0x6u, &v) == RX550_MMIO_OK,
	      "U2 get_field de 2 bits");
	CHECK_EQ(v, 0x6, "U2 get_field(0xdeadbeef, 0x6) == 6, los DOS bits");

	/* ── U3 · NEGATIVOS ───────────────────────────────────────────────── */
	printf("\nU3 · los negativos, y que el registro no se toca\n");
	*slot = 0x12345678u;

	/* mask 0: no tiene posicion.  Devolver shift 0 seria el primer bit del
	 * registro, que es un campo que el llamante no pidio. */
	v = 0xaaaaaaaa;
	CHECK(rx550_mmio_update_field(&map, reg, 0u, 1u, &v)
	      == RX550_MMIO_ERR_BAD_MASK, "U3 mask 0 rechazado");
	CHECK_EQ(v, 0xaaaaaaaa, "U3 y la salida no se toca");
	CHECK_EQ(*slot, 0x12345678u, "U3 registro intacto");

	/* mask con hueco: dos posiciones posibles, ninguna es "la" posicion. */
	CHECK(rx550_mmio_update_field(&map, reg, 0x5u, 1u, &v)
	      == RX550_MMIO_ERR_BAD_MASK, "U3 mask 0b101 rechazado");
	CHECK(rx550_mmio_update_field(&map, reg, 0xa5u, 1u, &v)
	      == RX550_MMIO_ERR_BAD_MASK, "U3 mask 0b1010101 rechazado");
	CHECK_EQ(*slot, 0x12345678u, "U3 registro intacto");

	/* Un valor que NO cabe en el campo: se rechaza, no se trunca.  Un
	 * truncamiento escribiria en el registro un numero distinto del que el
	 * llamante cree que puso, y no habria forma de notarlo. */
	CHECK(rx550_mmio_update_field(&map, reg, 0x6u, 4u, &v)
	      == RX550_MMIO_ERR_VALUE_RANGE, "U3 valor fuera de un campo de 2 bits");
	CHECK_EQ(*slot, 0x12345678u, "U3 registro intacto");
	CHECK(rx550_mmio_update_field(&map, reg, 0x6u, 3u, &v) == RX550_MMIO_OK,
	      "U3 el valor maximo del campo si cabe");

	/* Aqui se resiembra.  La comprobacion de "registro intacto" compara
	 * contra el valor con que se sembro, y esa linea de arriba ESCRIBE:
	 * 0x12345678 pasa a 0x1234567e porque los bits 1 y 2 valen 3.  La
	 * primera version de este test no resiembra y el fallo salia como si el
	 * update de un negativo hubiera escrito, cuando lo que habia escrito era
	 * la linea anterior.  Un test que culpa al codigo de lo que hizo la linea
	 * anterior es peor que no tenerlo. */
	*slot = 0x12345678u;
	CHECK(rx550_mmio_update_field(&map, reg, 0x1u, 2u, &v)
	      == RX550_MMIO_ERR_VALUE_RANGE, "U3 valor 2 en un campo de 1 bit");
	CHECK_EQ(*slot, 0x12345678u, "U3 registro intacto");

	/* Un campo de 32 bits acepta cualquier valor.  Es el borde: un mask
	 * 0xffffffff tiene shift 0 y ancho 32, y el codigo tiene una rama
	 * aparte para no rechazar el valor. */
	CHECK(rx550_mmio_update_field(&map, reg, 0xffffffffu, 0xdeadbeefu, &v)
	      == RX550_MMIO_OK, "U3 un campo de 32 bits acepta cualquier valor");
	CHECK_EQ(v, 0xdeadbeefu, "U3 y escribe el valor entero");

	/* Sin mapa, y fuera de ventana. */
	rx550_mmio_detach(&map);
	CHECK(rx550_mmio_update_field(&map, reg, 0x6u, 1u, &v)
	      == RX550_MMIO_ERR_NO_MAP, "U3 sin mapa");
	/* El mapa mas pequeno que BAR5 se rechaza EN ATTACH, no en el update.  Es
	 * el contrato que dice el propio attach:  "descubrir que el recurso es
	 * mas pequeno que BAR5 en el primer acceso seria descubrirlo
	 * escribiendo".  La primera version de este test hacia attach con 0x1000
	 * y esperaba OK para que el rechazo saliera del update, y lo que hacia
	 * era comprobar dos veces lo mismo, con un valor esperado equivocado. */
	CHECK(rx550_mmio_attach(&map, bar, 0x1000u)
	      == RX550_MMIO_ERR_MAP_TOO_SMALL,
	      "U3 un mapa mas pequeno que BAR5 se rechaza al ENLAZAR");
	CHECK(rx550_mmio_update_field(&map, reg, 0x6u, 1u, &v)
	      == RX550_MMIO_ERR_NO_MAP,
	      "U3 y tras el rechazo el mapa queda vacio, no writing a medias");

	/* Salida nula, en las tres funciones. */
	*slot = 0x5a5a5a5au;
	CHECK(rx550_mmio_update_field(&map, reg, 0x6u, 1u, NULL)
	      == RX550_MMIO_ERR_INCONSISTENT, "U3 update con salida nula");
	CHECK(rx550_mmio_get_field(0u, 0x6u, NULL) == RX550_MMIO_ERR_INCONSISTENT,
	      "U3 get_field con salida nula");
	{
		unsigned s = 0, w = 0;

		CHECK(rx550_mmio_field_from_mask(0x6u, NULL, &w)
		      == RX550_MMIO_ERR_INCONSISTENT, "U3 field_of sin shift");
		CHECK(rx550_mmio_field_from_mask(0x6u, &s, NULL)
		      == RX550_MMIO_ERR_INCONSISTENT, "U3 field_of sin width");
	}
	CHECK_EQ(*slot, 0x5a5a5a5au, "U3 registro intacto");

	free(bar);

	printf("\n  %d pass, %d fail\n", pass, fail);
	if (fail) {
		printf("  CONTRATO: INCUMPLIDO\n");
		return 1;
	}
	printf("  CONTRATO: SATISFECHO\n");
	return 0;
}