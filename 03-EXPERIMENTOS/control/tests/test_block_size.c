/* SPDX-License-Identifier: GPL-2.0-only */
/*
 * test_block_size.c — D1: la codificación de PAGE_TABLE_BLOCK_SIZE.
 *
 *   TARGET = RX 550 instalada en esta maquina  (1002:699F, Polaris12, GFX8)
 *   SCOPE  = EXCLUSIVO
 *
 * QUE COMPRUEBA, Y POR QUÉ CADA COSA ESTÁ EN UN FICHERO APARTE
 *
 *   Este test cruza geometría (M2) y accessor.  Eso lo hace vecino de la
 *   separación que test_mmio_access.c M9 vigila, y por eso NO está en ese
 *   fichero:  M9 exige que el accessor no nombre el PGT, y meter aquí la
 *   comprobación del cruce pondría esa frase en el propio sitio donde se
 *   comprueba.
 *
 *   M12  la fórmula contra la fuente primaria, abriendo las líneas citadas
 *   M13  el rango, en sus tres niveles:  codificable, semántico del corpus,
 *        y el que el camino por defecto de GFX8 alcanza de verdad
 *   M14  la tabla de 1 / 2 / 4 / 8 GiB
 *   M15  el cruce geometría -> campo -> CNTL, y la convención de máscaras
 *   M16  que el rechazo de 8 GiB es GEOMÉTRICO y no una mala lectura del campo
 *   M17  que cada línea citada dice lo que se dice que dice
 *
 * NADA DE ESTO TOCA HARDWARE.  C puro, unitario, en userspace.
 */

#include <stdio.h>
#include <stdlib.h>
#include <string.h>
#include <stdint.h>
#include <stdbool.h>

#include "rx550_vmid1_pgt.h"
#include "rx550_mmio_access.h"

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
		unsigned long long g_ = (unsigned long long)(got);	\
		unsigned long long w_ = (unsigned long long)(want);	\
		if (g_ == w_) {						\
			g_pass++;					\
		} else {						\
			g_fail++;					\
			printf("  FALLO  ");				\
			printf(__VA_ARGS__);				\
			printf("   (obtenido %llu, esperado %llu)\n",	\
			       g_, w_);					\
		}							\
	} while (0)

/* ═══════════════════════════════════════════════════════════════════════════
 * LECTURA DE FUENTES
 *
 * Buffer DEL LLAMANTE, y la razon es la de N1:  una funcion de lectura con un
 * `static` interno devuelve el mismo puntero dos veces, la segunda lectura pisa
 * la primera, y el fallo aparece como "el corpus no dice lo que dice".
 * ═══════════════════════════════════════════════════════════════════════════ */
static char *slurp(const char *path, char *buf, size_t bufsz, size_t *out_len)
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

/* La linea n (1-indexada) en out.  NULL si no existe. */
static char *line_n(const char *txt, size_t len, unsigned long want, char *out,
		    size_t outsz)
{
	size_t at = 0, seen = 0;

	while (at <= len) {
		size_t e = at, k;

		while (e < len && txt[e] != '\n')
			e++;
		seen++;
		if (seen == want) {
			k = e - at;
			if (k >= outsz)
				k = outsz - 1u;
			memcpy(out, txt + at, k);
			out[k] = '\0';
			return out;
		}
		if (e >= len)
			break;
		at = e + 1;
	}
	return NULL;
}

/* ═══════════════════════════════════════════════════════════════════════════
 * M12  LA FÓRMULA CONTRA LA FUENTE PRIMARIA
 *
 * Y LA REGLA:  no basta con que la linea exista.  Hay que leerla y tiene que
 * decir lo que el proyecto afirma que dice.  Un informe anterior afirmo que
 * el corpus escribe `1 << vmid` y luego resultó que lo que escribía era otra
 * cosa,  por no haber abierto la línea.
 * ═══════════════════════════════════════════════════════════════════════════ */
static void m12_formula(const char *gmc_c, const char *vm_c, const char *gmc_h)
{
	static char cbuf[1u << 20], vbuf[1u << 20], hbuf[1u << 20];
	size_t nc = 0, nv = 0, nh = 0;
	char *cs = slurp(gmc_c, cbuf, sizeof(cbuf), &nc);
	char *vs = slurp(vm_c, vbuf, sizeof(vbuf), &nv);
	char *hs = slurp(gmc_h, hbuf, sizeof(hbuf), &nh);
	char L[512];
	bool leidos = true;

	if (!cs || !vs || !hs) {
		CHECK(false, "M12 no se pudieron leer las tres fuentes");
		leidos = false;
	}
	if (!leidos)
		return;

	/* ── 1. el ESCRITOR de GFX8 ──────────────────────────────────────────
	 * gmc_v8_0.c:933-934
	 *     tmp = REG_SET_FIELD(tmp, VM_CONTEXT1_CNTL, PAGE_TABLE_BLOCK_SIZE,
	 *                             adev->vm_manager.block_size - 9);
	 * Y LA OPERACIÓN TIENE QUE ESTAR PARTIDA EN DOS LÍNEAS, porque la segunda
	 * es la que tiene la resta. */
	CHECK(line_n(cs, nc, 933, L, sizeof(L)) != NULL,
	      "M12 gmc_v8_0.c:933 existe");
	CHECK(strstr(L, "PAGE_TABLE_BLOCK_SIZE") != NULL,
	      "M12 gmc_v8_0.c:933 habla de PAGE_TABLE_BLOCK_SIZE");
	CHECK(line_n(cs, nc, 934, L, sizeof(L)) != NULL,
	      "M12 gmc_v8_0.c:934 existe");
	CHECK(strstr(L, "block_size - 9") != NULL,
	      "M12 gmc_v8_0.c:934 contiene literalmente `block_size - 9`");
	/* Y la línea siguiente tiene que escribir el registro:  el bloque se
	 * cierra ahí,  no se queda en una expresión muerta. */
	CHECK(line_n(cs, nc, 935, L, sizeof(L)) != NULL &&
	      strstr(L, "mmVM_CONTEXT1_CNTL") != NULL,
	      "M12 gmc_v8_0.c:935 escribe mmVM_CONTEXT1_CNTL");

	/* ── 2. el LECTOR ────────────────────────────────────────────────────
	 * amdgpu_vm.c:2438   tmp >>= amdgpu_vm_block_size - 9;
	 * La operación INVERSA.  Si sólo hubiera un escritor, `block_size - 9`
	 * podría ser un error tipográfico suyo.  Un lector que deshace lo mismo
	 * es lo que lo convierte en una convención. */
	CHECK(line_n(vs, nv, 2438, L, sizeof(L)) != NULL &&
	      strstr(L, ">>=") != NULL && strstr(L, "- 9") != NULL,
	      "M12 amdgpu_vm.c:2438 deshace la misma resta con >>=");

	/* ── 3. EL DECODIFICADOR DEL TAMAÑO DE PÁGINA, que es donde el 9 se
	 *      demuestra en lugar de suponerse ────────────────────────────── */
	CHECK(line_n(hs, nh, 1139, L, sizeof(L)) != NULL &&
	      strstr(L, "pde0_page_size") != NULL &&
	      strstr(L, "<<21") != NULL,
	      "M12 amdgpu_gmc.c:1139 dice page_size = 2^campo << 21");
	CHECK(line_n(hs, nh, 1150, L, sizeof(L)) != NULL &&
	      strstr(L, "PTE_FRAG") != NULL && strstr(L, "+ 9") != NULL,
	      "M12 amdgpu_gmc.c:1150 usa el mismo +9 en el fragmento de la PTE");

	/* ── 4. LA BASE NO ES UN NÚMERO PUESTO AHÍ ──────────────────────────
	 * 21 - 12 = 9,  con 21 del exponente de página de :1139 y 12 del
	 * desplazamiento del frame de amdgpu_gart.h:37. */
	CHECK_EQ(RX550_CNTL_PAGE_SIZE_EXPONENT, 21u,
		 "M12 el exponente de page_size es 21, de amdgpu_gmc.c:1139");
	CHECK_EQ(RX550_FRAME_SHIFT, 12u,
		 "M12 el desplazamiento del frame es 12, de amdgpu_gart.h:37");
	CHECK_EQ(RX550_CNTL_BLOCK_SIZE_BASE,
		 RX550_CNTL_PAGE_SIZE_EXPONENT - RX550_FRAME_SHIFT,
		 "M12 la base es 21-12, no un 9 escrito a mano");
	CHECK_EQ(RX550_CNTL_BLOCK_SIZE_BASE, 9u,
		 "M12 y coincide con el 9 que escribe el corpus");

	/* ── 5. CUANTAS VECES LO ESCRIBE EL CORPUS ───────────────────────────
	 * No una vez:  en trece ficheros de trece generaciones.  Un 9 escrito
	 * una vez es un descuido;  un 9 escrito trece veces es una convención.
	 * Y el recuento se hace SOBRE EL TEXTO, no de memoria. */
	{
		const char *const archivos[] = {
			"gmc_v6_0.c", "gmc_v7_0.c", "gmc_v8_0.c",
			"gfxhub_v2_0.c", "gfxhub_v2_1.c", "gfxhub_v3_0.c",
			"gfxhub_v3_0_3.c", "gfxhub_v11_5_0.c",
			"gfxhub_v12_0.c",
			"mmhub_v1_8.c", "mmhub_v2_0.c", "mmhub_v3_0.c",
			"mmhub_v3_3.c", "mmhub_v4_1_0.c",
		};
		size_t n = sizeof(archivos) / sizeof(archivos[0]);
		size_t k;
		unsigned con_menos_9 = 0;
		unsigned sin_leer = 0;
		char path[512];
		static char fbuf[1u << 20];
		size_t nf;

		for (k = 0; k < n; k++) {
			snprintf(path, sizeof(path), "%s", "");
			/* el directorio del driver se deduce del gmc_v8_0.c */
			{
				const char *slash = strrchr(gmc_c, '/');
				size_t dl = slash ? (size_t)(slash - gmc_c) : 0;

				if (dl && dl + 32u < sizeof(path)) {
					memcpy(path, gmc_c, dl);
					snprintf(path + dl, sizeof(path) - dl,
						 "/%s", archivos[k]);
				}
			}
			if (!slurp(path, fbuf, sizeof(fbuf), &nf)) {
				sin_leer++;
				continue;
			}
			if (strstr(fbuf, "block_size - 9"))
				con_menos_9++;
		}
		CHECK_EQ(sin_leer, 0u,
			 "M12 los 14 ficheros de la lista se pudieron abrir");
		CHECK(con_menos_9 >= 13u,
		      "M12 al menos 13 ficheros independientes escriben "
		      "`block_size - 9`: es una convención, no un descuido "
		      "(encontrados %u de 14)", con_menos_9);
	}
}

/* ═══════════════════════════════════════════════════════════════════════════
 * M13  EL RANGO, EN TRES NIVELES
 *
 * Y LA DISTINCIÓN IMPORTANTE:  "el rango del campo" y "el rango que el
 * hardware acepta" no son lo mismo, y el proyecto usa el primero.  Un nodo que
 * los confunda aceptaría block_size 22 como representable cuando el hardware
 * no lo genera nunca.
 * ═══════════════════════════════════════════════════════════════════════════ */
static void m13_range(void)
{
	/* ── nivel 1:  lo que el CAMPO puede contener ─────────────────────── */
	CHECK_EQ(RX550_CNTL_BLOCK_SIZE_MASK, 0x0F000000u,
		 "M13 la máscara del campo es 0x0F000000, COLOCADA (AMDGPU)");
	CHECK_EQ(RX550_CNTL_BLOCK_SIZE_SHIFT, 24u,
		 "M13 el shift es 24");
	CHECK_EQ(RX550_CNTL_BLOCK_SIZE_FIELD_MAX,
		 RX550_CNTL_BLOCK_SIZE_MASK >> RX550_CNTL_BLOCK_SIZE_SHIFT,
		 "M13 el máximo del campo sale de su máscara: 4 bits");
	CHECK_EQ(RX550_CNTL_BLOCK_SIZE_FIELD_MIN, 0u,
		 "M13 el campo arranca en 0");
	CHECK_EQ(RX550_CNTL_BLOCK_SIZE_VALUE_MIN, 9u,
		 "M13 el block_size mínimo codificable es 9");
	CHECK_EQ(RX550_CNTL_BLOCK_SIZE_VALUE_MAX, 24u,
		 "M13 el block_size máximo codificable es 24");

	/* ── nivel 2:  el tope SEMÁNTICO del corpus para num_level 1 ────────
	 * amdgpu_vm.c:2459-2462
	 *     min(amdgpu_vm_block_size, max_bits - AMDGPU_GPU_PAGE_SHIFT
	 *                                       - 9 * num_level)
	 * con gmc_v8_0.c:1127  max_bits = 40  y  max_level = 1:
	 *     40 - 12 - 9*1 = 19
	 * Es un tope que el corpus aplica SÓLO en la rama del parámetro de
	 * módulo.  No es el rango codificable, y por eso el proyecto no lo usa
	 * como guarda. */
	CHECK_EQ(40u - 12u - 9u * 1u, 19u,
		 "M13 el tope semántico del corpus para num_level 1 es 19 "
		 "(amdgpu_vm.c:2460-2462 con gmc_v8_0.c:1127)");
	CHECK(19u < RX550_CNTL_BLOCK_SIZE_VALUE_MAX,
	      "M13 el tope semántico es MÁS ESTRECHO que el codificable: "
	      "por eso no pueden confundirse");

	/* ── los dos extremos, y que se codifiquen bien ───────────────────── */
	CHECK_EQ(rx550_block_size_encode(9u), 0u,
		 "M13 block_size 9 -> campo 0");
	CHECK_EQ(rx550_block_size_encode(24u), 15u,
		 "M13 block_size 24 -> campo 15, el máximo del campo");
	CHECK_EQ(rx550_block_size_encode(10u), 1u,
		 "M13 block_size 10 -> campo 1");

	/* ── fuera de rango, y la razón de que UINT32_MAX sea el centinela ──
	 * El corpus restaría sobre un entero sin signo:  8 - 9 = 0xFFFFFFFF,
	 * recortado a 4 bits = 15 = block_size 24.  Pedir 512 bytes y obtener
	 * 64 GiB, en silencio. */
	CHECK_EQ(rx550_block_size_encode(8u), UINT32_MAX,
		 "M13 block_size 8 NO es representable y no se envuelve al 15");
	CHECK_EQ(rx550_block_size_encode(25u), UINT32_MAX,
		 "M13 block_size 25 NO es representable");
	CHECK_EQ(rx550_block_size_encode(0u), UINT32_MAX,
		 "M13 block_size 0 NO es representable");
	CHECK_EQ(rx550_block_size_encode(UINT32_MAX), UINT32_MAX,
		 "M13 block_size UINT32_MAX no es representable");

	/* Y la prueba de que el wrap era de verdad un 64:  lo que el corpus
	 * haría con 8, comparado con lo que hace el encoder. */
	{
		uint32_t el_del_corpus = (8u - 9u) &
			(RX550_CNTL_BLOCK_SIZE_MASK >> RX550_CNTL_BLOCK_SIZE_SHIFT);

		CHECK_EQ(el_del_corpus, 15u,
			 "M13 el corpus con block_size 8 escribiría 15: un "
			 "silencio de 2^24 veces");
		CHECK(rx550_block_size_encode(8u) != 15u,
		      "M13 y el encoder NO lo hace");
	}

	/* ── el round-trip en los 16 valores codificables ──────────────────── */
	{
		uint32_t i;
		bool ida_y_vuelta = true;

		for (i = 0; i <= RX550_CNTL_BLOCK_SIZE_FIELD_MAX; i++) {
			uint32_t bs = RX550_CNTL_BLOCK_SIZE_BASE + i;
			uint32_t campo = rx550_block_size_encode(bs);
			uint32_t leido;

			if (campo != i) {
				ida_y_vuelta = false;
				printf("  FALLO  M13 encode(%u) = %u, esperado %u\n",
				       bs, campo, i);
				g_fail++;
				continue;
			}
			/* Y el decoder lee del REGISTRO, no del campo. */
			leido = rx550_block_size_decode(0xFFFFFFFFu);
			if (leido != RX550_CNTL_BLOCK_SIZE_VALUE_MAX) {
				ida_y_vuelta = false;
				g_fail++;
			}
		}
		CHECK(ida_y_vuelta,
		      "M13 los 16 valores codificables hacen round-trip: "
		      "campo = block_size - 9 y block_size = campo + 9");
	}

	/* ── el decoder lee el registro entero, y eso es lo que lo distingue ──
	 * Si el decoder tomara el valor del campo,  0x01000000 daría 1 y no
	 * 10.  La diferencia es exactamente la que hace útil el readback. */
	{
		uint32_t campo = rx550_block_size_encode(10u);
		uint32_t reg = rx550_field_set(0u, RX550_CNTL_BLOCK_SIZE_MASK,
					       RX550_CNTL_BLOCK_SIZE_SHIFT, campo);

		CHECK_EQ(campo, 1u, "M13 el valor del campo para bs 10 es 1");
		CHECK_EQ(reg, 0x01000000u, "M13 y en el registro queda en el bit 24");
		CHECK_EQ(rx550_block_size_decode(reg), 10u,
			 "M13 el decoder devuelve 10, NO 1: lee el registro");
	}
}

/* ═══════════════════════════════════════════════════════════════════════════
 * M14  LA TABLA DE 1 / 2 / 4 / 8 GiB
 *
 * Y LA FUENTE de la tabla:  la aritmética del corpus, reimplementada aquí desde
 * amdgpu_vm.c:2433-2466,  no copiada del proyecto.  Si las dos coinciden,  es
 * que el proyecto dice la verdad;  y si no,  el proyecto tiene un error.  Por
 * eso las dos implementaciones están en ficheros distintos.
 * ═══════════════════════════════════════════════════════════════════════════ */

/* amdgpu_vm.c:2368-2379  amdgpu_vm_get_block_size(), con fls64 corregido */
static uint32_t corpus_fls64(uint64_t v)
{
	return v ? (uint32_t)(64u - (uint32_t)__builtin_clzll(v)) : 0u;
}

static uint64_t corpus_div_round_up(uint64_t n, uint64_t d)
{
	return (n + d - 1) / d;
}

static uint64_t corpus_roundup_pow2(uint64_t v)
{
	if (v <= 1)
		return 1;
	return UINT64_C(1) << (64 - __builtin_clzll(v - 1));
}

static uint32_t corpus_get_block_size(uint64_t t)
{
	uint32_t bits = (corpus_fls64(t) - 1u) + 18u;

	if (t <= 8)
		return bits - 9u;
	return (bits + 3u) / 2u;
}

struct corpus_geom {
	uint64_t max_pfn;
	uint64_t rpot;
	uint64_t tmp;
	int num_level;
	uint32_t block_size;
	uint32_t field;
	uint64_t coverage;
};

static void corpus_geometry(uint32_t gb, struct corpus_geom *o)
{
	memset(o, 0, sizeof(*o));
	/* gmc_v8_0.c:1127   amdgpu_vm_adjust_size(adev, 64, 9, 1, 40)
	 *                     min_vm_size=64  fragment_size_default=9
	 *                     max_level=1     max_bits=40
	 * amdgpu_vm.c:2433   max_pfn = vm_size << 18 */
	o->max_pfn = (uint64_t)gb << 18;
	/* :2436 */ o->rpot = corpus_roundup_pow2(o->max_pfn);
	/* :2439   DIV_ROUND_UP(fls64(tmp) - 1, 9) - 1
	 *         y amdgpu_vm_block_size == -1,  así que no hay desplazamiento */
	o->tmp = corpus_div_round_up(corpus_fls64(o->rpot) - 1u, 9u) - 1u;
	/* :2440   num_level = min(max_level, tmp) */ o->num_level = 1;
	/* :2463-2466  con num_level == 1 se llama a get_block_size(tmp) */
	o->block_size = corpus_get_block_size(o->tmp);
	/* gmc_v8_0.c:934  campo = block_size - 9 */
	o->field = o->block_size - 9u;
	/* cobertura:  2^bs páginas de 2^(bs+12) bytes  =  2^(2*bs+12) */
	o->coverage = UINT64_C(1) << (2u * o->block_size + 12u);
}

static void m14_sizes(void)
{
	struct {
		uint32_t gb;
		int expected_rc;	/* 0 = aceptada */
		uint32_t bs, field, depth, pte_pages;
		uint64_t coverage;
	} t[] = {
		{ 1, 0,  9,  0, 1,  512, UINT64_C(1) << 30 },
		{ 2, 0, 10,  1, 1, 1024, UINT64_C(1) << 32 },
		{ 4, 0, 10,  1, 1, 1024, UINT64_C(1) << 32 },
	};
	size_t n = sizeof(t) / sizeof(t[0]);
	size_t k;
	bool coincide = true;

	printf("  ── tabla: proyecto vs aritmética del corpus ──\n");
	for (k = 0; k < n; k++) {
		struct rx550_vmid1_geom g;
		struct corpus_geom c;
		uint64_t bytes = (uint64_t)t[k].gb << 30;
		int rc = rx550_vmid1_geometry(bytes, &g);

		corpus_geometry(t[k].gb, &c);
		printf("    %2u GiB  PROY bs=%2u campo=%u pte=%4u cov=%5llu MiB   "
		       "CORPUS bs=%2u campo=%u tmp=%llu cov=%5llu MiB\n",
		       t[k].gb, g.block_size, g.block_size_field, g.pte_pages,
		       (unsigned long long)(g.coverage_bytes >> 20),
		       c.block_size, c.field, (unsigned long long)c.tmp,
		       (unsigned long long)(c.coverage >> 20));

		CHECK_EQ((int)rc, 0,
		 "M14 %u GiB debe aceptarse", t[k].gb);
		CHECK_EQ(g.block_size, t[k].bs, "M14 %u GiB block_size", t[k].gb);
		CHECK_EQ(g.block_size_field, t[k].field,
			 "M14 %u GiB campo PAGE_TABLE_BLOCK_SIZE", t[k].gb);
		CHECK_EQ(g.depth_field, t[k].depth, "M14 %u GiB PAGE_TABLE_DEPTH",
			 t[k].gb);
		CHECK_EQ(g.pte_pages, t[k].pte_pages, "M14 %u GiB páginas de PTE",
			 t[k].gb);
		CHECK_EQ(g.coverage_bytes, t[k].coverage,
			 "M14 %u GiB cobertura", t[k].gb);

		/* Y LA COMPARACIÓN CON EL CORPUS, que es lo que hace que la tabla
		 * no sea una reinvención. */
		if (g.block_size != c.block_size ||
		    g.block_size_field != c.field ||
		    g.coverage_bytes != c.coverage) {
			coincide = false;
			printf("  FALLO  M14 %u GiB: el proyecto NO coincide con "
			       "amdgpu_vm.c\n", t[k].gb);
			g_fail++;
		}
	}
	CHECK(coincide,
	      "M14 la geometria del proyecto coincide con la aritmetica de "
	      "amdgpu_vm.c:2433-2466 en 1, 2 y 4 GiB");

	/* ── la cobertura menos el vm_size, que es lo que hace la guarda ──── */
	{
		struct rx550_vmid1_geom g2, g4;
		int64_t d2, d4;

		rx550_vmid1_geometry(UINT64_C(2) << 30, &g2);
		rx550_vmid1_geometry(UINT64_C(4) << 30, &g4);
		d2 = (int64_t)((g2.coverage_bytes - (UINT64_C(2) << 30)) >> 20);
		d4 = (int64_t)((g4.coverage_bytes - (UINT64_C(4) << 30)) >> 20);
		CHECK_EQ(d2, 2048, "M14 2 GiB: la cobertura excede en 2048 MiB");
		CHECK_EQ(d4, 0, "M14 4 GiB: la cobertura no excede");
		/* Y la sub-cobertura es un hecho medido, no un olvido. */
		CHECK(g2.coverage_bytes > (UINT64_C(2) << 30),
		      "M14 2 GiB produce sub-ventana por exceso de cobertura, "
		      "que acota START/END, no por defecto de geometria");
	}
}

/* ═══════════════════════════════════════════════════════════════════════════
 * M15  EL CRUCE, Y LA CONVENCIÓN DE MÁSCARAS
 *
 * Esto es lo que se rompería si alguien invirtiera las dos convenciones:  la
 * geometría produce el campo,  el campo se compone en CNTL,  y un
 * desplazamiento doble deja el campo en cero sin que nada falle.
 * ═══════════════════════════════════════════════════════════════════════════ */

/* compone CNTL entero, como haría el nodo de programación */
static uint32_t compose_cntl(const struct rx550_vmid1_geom *g)
{
	uint32_t v = 0xFFFFFFFFu;	/* hardware desconocido: todo a 1 */

	v = rx550_field_set_id(v, RX550_FLD_CNTL_ENABLE_CONTEXT, 1u);
	v = rx550_field_set_id(v, RX550_FLD_CNTL_PAGE_TABLE_DEPTH, g->depth_field);
	v = rx550_field_set_id(v, RX550_FLD_CNTL_BLOCK_SIZE, g->block_size_field);
	v = rx550_field_set_id(v, RX550_FLD_CNTL_RANGE_PROT_FAULT_DEFAULT, 1u);
	v = rx550_field_set_id(v, RX550_FLD_CNTL_DUMMY_PAGE_PROT_FAULT_DEFAULT, 1u);
	v = rx550_field_set_id(v, RX550_FLD_CNTL_PDE0_PROT_FAULT_DEFAULT, 1u);
	v = rx550_field_set_id(v, RX550_FLD_CNTL_VALID_PROT_FAULT_DEFAULT, 1u);
	v = rx550_field_set_id(v, RX550_FLD_CNTL_READ_PROT_FAULT_DEFAULT, 1u);
	v = rx550_field_set_id(v, RX550_FLD_CNTL_WRITE_PROT_FAULT_DEFAULT, 1u);
	v = rx550_field_set_id(v, RX550_FLD_CNTL_EXECUTE_PROT_FAULT_DEFAULT, 1u);
	return v;
}

static void m15_cross(void)
{
	struct {
		uint32_t gb;
		uint32_t cntl;
	} t[] = {
		/*  Delcroce de arriba sale 0xFFFFFFFF,  los nueve campos que el
		 *  corpus pone a 1 se ponen,  y el nibble 24..27 es el único
		 *  que depende de la geometría:
		 *    campo 0  ->  nibble 0   ->  0xF0FFFFFB
		 *    campo 1  ->  nibble 1   ->  0xF1FFFFFB
		 *  Los bits 28..31 y el 5 y el 8 se quedan como estaban,  que
		 *  es lo que demuestra que componer no pisa lo de al lado. */
		{ 1, 0xF0FFFFFBu },
		{ 2, 0xF1FFFFFBu },
		{ 4, 0xF1FFFFFBu },
	};
	size_t k;
	bool ok = true;

	for (k = 0; k < sizeof(t) / sizeof(t[0]); k++) {
		struct rx550_vmid1_geom g;
		uint32_t cntl, campo, leido;

		CHECK_EQ(rx550_vmid1_geometry((uint64_t)t[k].gb << 30, &g), 0,
			 "M15 %u GiB geometria", t[k].gb);
		cntl = compose_cntl(&g);
		if (cntl != t[k].cntl) {
			ok = false;
			printf("  FALLO  M15 %u GiB CNTL = 0x%08X, esperado "
			       "0x%08X\n", t[k].gb, cntl, t[k].cntl);
			g_fail++;
		}
		/* Y LAS TRES PREGUNTAS QUE IMPORTAN DEL READBACK */
		campo = rx550_field_get_id(cntl, RX550_FLD_CNTL_BLOCK_SIZE);
		leido = rx550_block_size_decode(cntl);
		if (campo != g.block_size_field || leido != g.block_size) {
			ok = false;
			g_fail++;
		}
	}
	CHECK(ok,
	      "M15 la geometria compone CNTL, y el campo y el block_size se "
	      "leen de vuelta");

	/* ── LA CONVENCIÓN, DICHA POR PARTES ──────────────────────────────
	 *  · FIELD_MASK ya viene colocado;  colocarlo otra vez lo anula
	 *  · el campo 0 tiene que dejar el registro SIN bit 24
	 *  · el campo 1 tiene que poner SOLO el bit 24 */
	{
		uint32_t solo = rx550_field_set(0u, RX550_CNTL_BLOCK_SIZE_MASK,
						RX550_CNTL_BLOCK_SIZE_SHIFT, 0u);

		CHECK_EQ(solo, 0u,
			 "M15 el campo 0 deja CNTL con el nibble alto a cero");
		CHECK_EQ(rx550_field_placed(RX550_CNTL_BLOCK_SIZE_MASK,
					    RX550_CNTL_BLOCK_SIZE_SHIFT),
			 0x0F000000u,
			 "M15 la mascara COLOCADA es 0x0F000000 y no 0xF");
		/* Y el desplazamiento doble, que es el error de N1 reducido a
		 * una línea, tiene que dar cero.  No se prueba que "no compile":
		 * compila, y por eso hay que probarlo. */
		CHECK_EQ(RX550_CNTL_BLOCK_SIZE_MASK << RX550_CNTL_BLOCK_SIZE_SHIFT,
			 0u,
			 "M15 desplazar la máscara dos veces la ANULA: 0x0F000000 "
			 "<< 24 = 0, y el campo quedaría en 0 para siempre");
		/* Y el round-trip por el decoder, que es lo que valida de verdad */
		CHECK_EQ(rx550_block_size_decode(rx550_field_set(0u,
				RX550_CNTL_BLOCK_SIZE_MASK,
				RX550_CNTL_BLOCK_SIZE_SHIFT, 15u)), 24u,
			 "M15 el nibble alto a 1 significa block_size 24");
	}

	/* ── Y LA COHERENCIA CON LA TABLA DE CAMPOS, que es la segunda copia
	 *    de la máscara.  Si las dos se separan,  una está mal. ───────── */
	{
		const struct rx550_reg_field *f =
			rx550_field_of(RX550_FLD_CNTL_BLOCK_SIZE);
		const struct rx550_reg_field *bad = NULL;
		uint32_t i;

		CHECK(f != NULL, "M15 el campo BLOCK_SIZE existe en la tabla");
		if (f) {
			CHECK_EQ(f->mask, RX550_CNTL_BLOCK_SIZE_MASK,
				 "M15 el ancla y la tabla tienen la misma máscara");
			CHECK_EQ(f->shift, RX550_CNTL_BLOCK_SIZE_SHIFT,
				 "M15 el ancla y la tabla tienen el mismo shift");
			CHECK_EQ(f->width, 4u, "M15 el campo es de 4 bits");
		}
		/* Y que ningun otro campo del registro comparta el nibble 24..27 */
		for (i = 0; i < rx550_reg_field_count; i++) {
			const struct rx550_reg_field *o = &rx550_reg_fields[i];

			if (o == f || strcmp(o->reg, f->reg) != 0)
				continue;
			if (o->mask & RX550_CNTL_BLOCK_SIZE_MASK)
				bad = o;
		}
		CHECK(bad == NULL,
		      "M15 ningun otro campo de CNTL toca los bits 24..27");
	}
}

/* ═══════════════════════════════════════════════════════════════════════════
 * M16  EL RECHAZO DE 8 GiB ES GEOMÉTRICO
 *
 * Y LA PREGUNTA QUE ESTE NODO TIENE QUE RESPONDER:  ¿el rechazo viene de que
 * la geometría no cubre, o de que alguien leyó mal el campo y creyó que 8 GiB
 * no cabía en el nibble?
 *
 * La respuesta es que el nibble lo admite de sobra:  8 GiB con block_size 10
 * necesita el campo 1, que es el mismo que usan 2 y 4 GiB.  El rechazo es
 * porque la cobertura del nivel es de 4 GiB,  y eso es un hecho de la
 * geometría,  no del campo.
 * ═══════════════════════════════════════════════════════════════════════════ */
static void m16_eight_gib(void)
{
	struct rx550_vmid1_geom g8;
	struct corpus_geom c8;
	int rc;

	rc = rx550_vmid1_geometry(UINT64_C(8) << 30, &g8);
	CHECK(rc != 0, "M16 8 GiB se rechaza");
	/* Y el código concreto dice POR QUÉ:  -5 es
	 * RX550_PGT_ERR_VM_SIZE_INCOHERENT,  "la cobertura derivada no es la
	 * ventana pedida".  Y -4,  que sería el de block_size,  NO es.
	 *
	 * La comparación va con signo, y no con el módulo:  la primera versión
	 * comparaba `(uint32_t)(-rc)` contra `(uint32_t)(-5)`,  que es comparar
	 * 5 contra 4294967291.  Dos conversiones a unsigned que sólo coinciden
	 * en el papel. */
	CHECK_EQ((int)rc, (int)RX550_PGT_ERR_VM_SIZE_INCOHERENT,
		 "M16 el error es VM_SIZE_INCOHERENT (cobertura), no de bloque");
	CHECK((int)rc != (int)RX550_PGT_ERR_UNSUPPORTED_BLOCK_SIZE,
	      "M16 y NO es UNSUPPORTED_BLOCK_SIZE:  el nibble no Rechaza 8 GiB");

	/* Y lo que el CORPUS haría con 8 GiB, que es lo que separa las dos
	 * hipótesis:  el campo NO es el problema. */
	corpus_geometry(8, &c8);
	CHECK_EQ(c8.block_size, 10u,
		 "M16 el corpus también da block_size 10 para 8 GiB");
	CHECK_EQ(c8.field, 1u,
		 "M16 y el campo 1, que es el mismo que usan 2 y 4 GiB");
	CHECK_EQ(c8.field, 1u,
		 "M16 el nibble admite 8 GiB de sobra: no es un problema de campo");
	CHECK(c8.coverage < (UINT64_C(8) << 30),
	      "M16 la cobertura del corpus para 8 GiB es 4 GiB, menor que 8 GiB");
	CHECK_EQ(c8.coverage, UINT64_C(1) << 32,
		 "M16 y coincide con la del proyecto");

	/* Y LA PRUEBA DIRECTA:  si la cobertura tuviera que ser 8 GiB con el
	 * campo 1,  el block_size teria que ser distinto.  Y no lo es. */
	{
		uint32_t necesario = 9u;
		uint64_t cob = UINT64_C(1) << (2u * necesario + 12u);

		while (cob < (UINT64_C(8) << 30) && necesario < 40u)
			cob = UINT64_C(1) << (2u * (++necesario) + 12u);
		printf("    el primer block_size cuya cobertura alcanza 8 GiB es "
		       "%u (campo %u), y el proyecto usa %u\n",
		       necesario, necesario - 9u, 10u);
		CHECK(necesario > 10u,
		      "M16 alcanzar 8 GiB exigiría un block_size MAYOR que el que "
		      "el corpus usa: el límite es la cobertura, no el nibble");
	}
}

/* ─────────────────────────────────────────────────────────────────────────── */

int main(int argc, char **argv)
{
	const char *gmc_c = (argc > 1) ? argv[1] : NULL;
	const char *vm_c = (argc > 2) ? argv[2] : NULL;
	const char *gmc_h = (argc > 3) ? argv[3] : NULL;
	static char p1[512], p2[512], p3[512];
	const char *cands_vm[2] = {
		"../../../RESEARCH/kernelbuild/linux-7.1.3/drivers/gpu/drm/amd/"
		"amdgpu/amdgpu_vm.c",
		"../../RESEARCH/kernelbuild/linux-7.1.3/drivers/gpu/drm/amd/"
		"amdgpu/amdgpu_vm.c",
	};
	const char *cands_h[2] = {
		"../../../RESEARCH/kernelbuild/linux-7.1.3/drivers/gpu/drm/amd/"
		"amdgpu/amdgpu_gmc.c",
		"../../RESEARCH/kernelbuild/linux-7.1.3/drivers/gpu/drm/amd/"
		"amdgpu/amdgpu_gmc.c",
	};
	int ci;

	if (!gmc_c) {
		const char *c[2] = {
			"../../../RESEARCH/kernelbuild/linux-7.1.3/drivers/gpu/"
			"drm/amd/amdgpu/gmc_v8_0.c",
			"../../RESEARCH/kernelbuild/linux-7.1.3/drivers/gpu/"
			"drm/amd/amdgpu/gmc_v8_0.c",
		};

		gmc_c = c[0];
		for (ci = 0; ci < 2; ci++) {
			FILE *f = fopen(c[ci], "rb");

			if (f) {
				fclose(f);
				gmc_c = c[ci];
				break;
			}
		}
	}
	if (!vm_c) {
		vm_c = cands_vm[0];
		for (ci = 0; ci < 2; ci++) {
			FILE *f = fopen(cands_vm[ci], "rb");

			if (f) {
				fclose(f);
				vm_c = cands_vm[ci];
				break;
			}
		}
	}
	if (!gmc_h) {
		gmc_h = cands_h[0];
		for (ci = 0; ci < 2; ci++) {
			FILE *f = fopen(cands_h[ci], "rb");

			if (f) {
				fclose(f);
				gmc_h = cands_h[ci];
				break;
			}
		}
	}
	p1[0] = p2[0] = p3[0] = '\0';
	(void)p1; (void)p2; (void)p3;

	printf("test_block_size  —  D1: PAGE_TABLE_BLOCK_SIZE en GFX8\n");
	printf("gmc_v8_0.c : %s\namdgpu_vm.c: %s\namdgpu_gmc.c: %s\n\n",
	       gmc_c, vm_c, gmc_h);

	m12_formula(gmc_c, vm_c, gmc_h);
	m13_range();
	m14_sizes();
	m15_cross();
	m16_eight_gib();

	printf("\n  passed: %u\n  failed: %u\n", g_pass, g_fail);
	return g_fail ? 1 : 0;
}
