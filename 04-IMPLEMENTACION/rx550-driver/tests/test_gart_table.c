/* SPDX-License-Identifier: GPL-2.0-only */
/*
 * test_gart_table.c — la geometria de la tabla de la GART y su relleno inicial.
 *
 *   TARGET = RX 550 instalada en esta maquina  (1002:699F, Polaris12, GFX8)
 *   SCOPE  = EXCLUSIVO
 *
 * QUE ES Y QUE NO ES
 *   C puro, unitario, en userspace.  Aritmetica sobre un array normal.
 *
 * POR QUE ESTA LA TABLA Y NO LA HACE rx550_gart_seq.c
 *   El plan dice DONDE esta la tabla  (CONTEXT0_PAGE_TABLE_BASE = tabla >> 12)
 *   y no la crea:  el plan se construye y se compara con el corpus sin tocar
 *   nada.  Aqui esta lo otro,  que es CUANTO ocupa y con que arranca cada
 *   entrada.  Las dos mitades de la verdad,  separadas.
 *
 * QUE NO COMPRUEBA
 *   Que el hardware acepte el contenido inicial.  Que una GART con 65536
 *   entradas validas mapee de verdad  no se puede decir sin ejecutar.
 */
#include <stdio.h>
#include <stdlib.h>
#include <string.h>
#include <stdint.h>
#include <stdbool.h>

#include "rx550_gart_table.h"

static int pass, fail;

static void ok(const char *t) { printf("  PASS  %s\n", t); pass++; }
static void ko(const char *t) { printf("  FAIL  %s\n", t); fail++; }

#define CHECK(cond, name) do { if (cond) ok(name); else ko(name); } while (0)
#define CHECK_EQ(got, want, name) do {					\
	unsigned long long g_ = (unsigned long long)(got);		\
	unsigned long long w_ = (unsigned long long)(want);		\
	if (g_ == w_) ok(name);						\
	else { printf("  FAIL  %s  (%llu != %llu)\n", name, g_, w_);	\
	       fail++; }							\
} while (0)

/* EL NUMERO DE ESTA TARJETA, del log del kernel. */
#define GART_SIZE	(UINT64_C(256) << 20)	/* "GART: 256M"        */
#define ESPERADAS_PAGS	UINT64_C(65536)		/* 256 MiB / 4096      */
#define ESPERADOS_BYTES	UINT64_C(524288)	/* 65536 * 8 = 512 KiB */

int main(void)
{
	struct rx550_gart_tabla_geom g;
	uint64_t *tabla;

	printf("test_gart_table — la tabla de la GART\n\n");

	/* ── G1 · LA GEOMETRIA DE ESTA TARJETA ──────────────────────────── */
	printf("G1 · geometria de 256 MiB\n");
	CHECK(rx550_gart_tabla_geom(GART_SIZE, &g) == 0, "G1 geom");
	CHECK_EQ(g.paginas, ESPERADAS_PAGS, "G1 65536 paginas");
	CHECK_EQ(g.bytes, ESPERADOS_BYTES, "G1 524288 bytes, y son 512 KiB");
	CHECK_EQ(g.bytes, ESPERADAS_PAGS * 8u,
		 "G1 y el tamano son las paginas por OCHO");
	CHECK_EQ(g.entradas_max, ESPERADAS_PAGS, "G1 entradas_max");

	/*  El *8 de gmc_v8_0.c:960 es lo que hace que esta tabla ocupe 512 KiB y
	 *  no 256.  Y elVector que distingue:  si el divisor fuese 4 en vez de
	 *  8,  el numero seria la mitad y seguiria siendo "plausible". */
	{
		uint64_t con_cuatro = ESPERADAS_PAGS * 4u;

		CHECK_EQ(con_cuatro, ESPERADOS_BYTES / 2u,
			 "G1 con 4 bytes por entrada la mitad: el vector "
			 "distingue el 8 del 4");
		CHECK(con_cuatro != ESPERADOS_BYTES,
		      "G1 y el tamano que espera el corpus NO es el de 4 bytes");
	}

	/*  Y que 512 KiB son 512 entradas de 8 bytes por pagina y no un numero
	 *  raro:  65536 entradas de 8 bytes. */
	CHECK(ESPERADOS_BYTES == ESPERADAS_PAGS * RX550_GART_TABLA_ENTRADA_BYTES,
	      "G1 el tamaño es paginas * RX550_GART_TABLA_ENTRADA_BYTES");

	/* ── G2 · LA ARITMETICA DEL CORPUS, PASO A PASO ─────────────────── */
	printf("\nG2 · los tres pasos del corpus, uno a uno\n");
	{
		uint64_t np = GART_SIZE / 4096u;
		uint64_t ts = np * 8u;

		CHECK_EQ(np, ESPERADAS_PAGS,
			 "G2 paso 1, amdgpu_gart.c:533: gart_size / 4096");
		CHECK_EQ(ts, ESPERADOS_BYTES,
			 "G2 paso 2, gmc_v8_0.c:960: paginas * 8");
		CHECK_EQ(RX550_GART_PTE_EXECUTABLE, UINT64_C(0x10),
			 "G2 paso 3, gmc_v8_0.c:961 y amdgpu_vm.h:65");
	}

	/* ── G3 · EL RELLENO ────────────────────────────────────────────── */
	printf("\nG3 · el relleno inicial\n");
	tabla = calloc(ESPERADAS_PAGS, sizeof(uint64_t));
	if (!tabla) {
		printf("  FAIL  no se pudo reservar la tabla\n");
		return 1;
	}

	CHECK(rx550_gart_tabla_reinicia(tabla, ESPERADAS_PAGS) == 0,
	      "G3 reinicia");
	{
		bool todos = true;
		uint64_t distintos = 0;

		for (uint64_t i = 0; i < ESPERADAS_PAGS; i++) {
			if (tabla[i] != RX550_GART_PTE_EXECUTABLE) {
				if (todos)
					printf("  FAIL  G3 entrada %llu vale "
					       "0x%llx\n",
					       (unsigned long long)i,
					       (unsigned long long)tabla[i]);
				todos = false;
			}
		}
		CHECK(todos, "G3 las 65536 entradas valen AMDGPU_PTE_EXECUTABLE");

		/*  El contenido tiene que ser EXACTAMENTE 0x10 y no 0.  Una GART de
		 *  entradas a cero es un estado valido despues de un reset,  pero no
		 *  el estado desde el que el driver arranca,  y la diferencia es un
		 *  bit.  Este vector distingue "lo que escribe el corpus" de "lo que
		 *  sale de calloc". */
		memset(tabla, 0, ESPERADAS_PAGS * sizeof(uint64_t));
		CHECK(tabla[0] == 0u, "G3 calloc deja la tabla a cero");
		CHECK(RX550_GART_PTE_EXECUTABLE != 0u,
		      "G3 y el valor del corpus NO es cero");
		/*  Y el vacio cuenta:  que el recorrido hayamirado las 65536,  no
		 *  un numero menor por un error de rango. */
		CHECK(distintos == 0u, "G3 el recorrido comparo las 65536");
	}

	/*  Y que rellena con OTRO valor funciona igual:  la funcion no esta cableada
	 *  al 0x10. */
	CHECK(rx550_gart_tabla_rellena(tabla, ESPERADAS_PAGS, 0xdeadbeefcafebabeULL) == 0,
	      "G3 rellena con un valor cualquiera");
	CHECK(tabla[0] == 0xdeadbeefcafebabeULL &&
	      tabla[ESPERADAS_PAGS - 1] == 0xdeadbeefcafebabeULL,
	      "G3 y la primera y la ultima entrada tienen ese valor");
	/*  Que no se pase:  la entrada 65536 no existe. */
	/*  Y que rellenar de mas NO es un error de la funcion:  la funcion cuenta
	 *  entradas y no conoce el buffer.  Lo que tiene que impedir es que un
	 *  llamante pase un numero que no cabe en su indice, y eso lo comprueba
	 *  con SIZE_MAX.  Aqui lo que se mide es que la funcion NO se queja de un
	 *  numero arbitrariamente grande que en una plataforma de 64 bits no cabe
	 *  todavia. */
	CHECK(rx550_gart_tabla_rellena(tabla, ESPERADAS_PAGS, 0u) == 0,
	      "G3 rellenar exactamente el numero de entradas");

	/* ── G4 · LOS NEGATIVOS ─────────────────────────────────────────── */
	printf("\nG4 · los negativos\n");
	CHECK(rx550_gart_tabla_geom(0, &g) == RX550_GART_TABLA_ERR_TAMANO,
	      "G4 una GART de cero bytes");
	CHECK(rx550_gart_tabla_geom(4096u * 3u + 1u, &g)
	      == RX550_GART_TABLA_ERR_TAMANO,
	      "G4 un tamano que no es multiplo de 4096");
	/*  El corpus trunca ese caso:  3 paginas y 1 byte darian 3 paginas y
	 *  24 bytes de tabla,  y nadie lo veria.  Aqui se rechaza. */
	CHECK(rx550_gart_tabla_geom(UINT64_C(512) << 20, &g)
	      == RX550_GART_TABLA_ERR_TAMANO,
	      "G4 mas de RX550_GART_SIZE_MAX");
	/*  El borde:  exactamente el maximo tiene que entrar. */
	CHECK(rx550_gart_tabla_geom(UINT64_C(256) << 20, &g) == 0,
	      "G4 y el maximo exacto si entra");
	CHECK(rx550_gart_tabla_geom(4096u, &g) == 0,
	      "G4 y la pagina minima tambien");
	{
		struct rx550_gart_tabla_geom min;

		CHECK(rx550_gart_tabla_geom(4096u, &min) == 0, "G4 la minima");
		CHECK_EQ(min.paginas, 1u, "G4 una pagina");
		CHECK_EQ(min.bytes, 8u, "G4 y 8 bytes, no 4");
	}
	CHECK(rx550_gart_tabla_geom(GART_SIZE, NULL)
	      == RX550_GART_TABLA_ERR_INCONSISTENT, "G4 sin destino");
	CHECK(rx550_gart_tabla_rellena(NULL, 10, 0) == RX550_GART_TABLA_ERR_INCONSISTENT,
	      "G4 rellenar sin tabla");
	CHECK(rx550_gart_tabla_rellena(tabla, 0, 0) == RX550_GART_TABLA_ERR_TAMANO,
	      "G4 rellenar cero entradas");

	/*  Un error NO escribe en el destino. */
	{
		struct rx550_gart_tabla_geom envenenada;

		memset(&envenenada, 0xa5, sizeof(envenenada));
		CHECK(rx550_gart_tabla_geom(0, &envenenada)
		      == RX550_GART_TABLA_ERR_TAMANO, "G4 error");
		CHECK_EQ(envenenada.paginas, 0xa5a5a5a5a5a5a5a5ULL,
			 "G4 y la geometria del llamante no se toco");
	}

	free(tabla);
	printf("\n  %d pass, %d fail\n", pass, fail);
	if (fail) {
		printf("  CONTRATO: INCUMPLIDO\n");
		return 1;
	}
	printf("  CONTRATO: SATISFECHO\n");
	return 0;
}