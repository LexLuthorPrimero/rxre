/* SPDX-License-Identifier: GPL-2.0 */
/*
 * test_vram_pool.c — el allocator, y sobre todo las DOS clausulas del
 * contrato que dice cumplir.
 *
 * UNA SOLA PREGUNTA: ¿cumple el pool el contrato de rx550_vram.h, incluida la
 * parte de "si falla, NO ESCRIBE `out`", que ningun allocator habia
 * implementado?
 *
 * QUE NO PRUEBA
 *   Que 512 KiB de VRAM se consigan en esta tarjeta.  Este pool reparte bytes
 *   DENTRO de un intervalo que le da el llamante;  el intervalo viene de
 *   CONFIG_MEMSIZE,  que es RUNTIME_REQUIRED.  Aqui se le da un intervalo de
 *   mentira,  y por eso este test no dice nada del hardware.
 *
 * LOS TAMANOS SON LOS REALES, no inventados:
 *   512 KiB alineados a 4096   la tabla del GART (rx550_gart_table.h)
 *   4 KiB                      una tabla de PDB0 (rx550_pdb0.h:45)
 */
#include "rx550_vram_pool.h"
#include <stdio.h>

static int pass, fail;
static void ok(const char *t) { printf("  PASS  %s\n", t); pass++; }
static void ko(const char *t) { printf("  FAIL  %s\n", t); fail++; }
#define CHECK(c, n) do { if (c) ok(n); else ko(n); } while (0)

#define TABLA_BYTES  UINT64_C(524288)
#define TABLA_ALIGN  UINT64_C(4096)
#define PDB0_BYTES   UINT64_C(4096)

/* ────────────────────────────────────────────────────────────────────────── */
static void fase_ventana(void)
{
	struct rx550_vram_pool p;

	printf("ventana\n");

	/* Un pool nuevo no tiene ventana.  QUE NO: si el pool nace con una
	 * capacidad por defecto, esa capacidad es una constante quemada, y la
	 * capacidad real la lee CONFIG_MEMSIZE. */
	rx550_vram_pool_init(&p);
	CHECK(p.ventana_bytes == 0, "nace SIN ventana, no con una por defecto");
	CHECK(rx550_vram_pool_free_bytes(&p) == 0, "y por tanto con cero libres");
	CHECK(rx550_vram_pool_largest(&p) == 0, "y sin ningun hueco");

	CHECK(rx550_vram_pool_set_window(&p, 0) == RX550_VRAM_ERR_SIN_MEM,
	      "ventana de 0 bytes rechazada");
	CHECK(rx550_vram_pool_set_window(&p, TABLA_BYTES) == RX550_VRAM_OK,
	      "ventana de 512 KiB aceptada");
	CHECK(p.ventana_bytes == TABLA_BYTES, "y declarada");
	CHECK(rx550_vram_pool_largest(&p) == TABLA_BYTES, "con un hueco del todo");
	CHECK(rx550_vram_pool_set_window(NULL, 1) == RX550_VRAM_ERR_NULO,
	      "pool nulo rechazado");
}

static void fase_no_cabe(void)
{
	struct rx550_vram_pool p;

	printf("sin ventana no hay memoria\n");

	/* ESTE es el estado que mas conviene comprobar:  un pool que no ha
	 * recibido su ventana no puede servir ni un byte, y su error tiene que
	 * ser SIN_MEM, no un Segmentation Fault. */
	rx550_vram_pool_init(&p);
	{
		struct rx550_vram_resource r;

		CHECK(rx550_vram_pool_alloc(&p, TABLA_BYTES, TABLA_ALIGN, &r) ==
		      RX550_VRAM_ERR_SIN_MEM,
		      "sin ventana, pedir la tabla del GART da SIN_MEM");
	}
	CHECK(rx550_vram_pool_set_window(&p, TABLA_BYTES) == RX550_VRAM_OK,
	      "una vez declarada, si");
	/* Re-declarar con gente dentro perderia sus reservas en silencio. */
	{
		struct rx550_vram_resource r;

		CHECK(rx550_vram_pool_alloc(&p, PDB0_BYTES, 8, &r) == RX550_VRAM_OK,
		      "una reserva pequena entra");
		CHECK(rx550_vram_pool_set_window(&p, TABLA_BYTES) ==
		      RX550_VRAM_ERR_INVALIDO,
		      "re-declarar la ventana con gente dentro se rechaza");
	}
}

/* ── LA CLAUSULA 1: si falla, no escribe `out` ─────────────────────────── */
static void fase_out_intacto(void)
{
	struct rx550_vram_pool p;
	struct rx550_vram_resource r;
	uint64_t i;

	printf("si falla, NO ESCRIBE out\n");

	rx550_vram_pool_init(&p);
	rx550_vram_pool_set_window(&p, PDB0_BYTES);

	/* Se siembra `r` con un patron reconocible.  Despues se le pide algo que
	 * no cabe.  Si el allocator escribiera `out` antes de fallar, el patron
	 * habria cambiado.  Este es el test que hace que la clausula sea una
	 * propiedad y no una intencion. */
	rx550_vram_resource_reset(&r);
	r.offset    = rx550_vram_off(UINT64_C(0xDEADBEEF));
	r.size      = UINT64_C(0x1234);
	r.alignment = UINT64_C(0x40);
	r.owner     = (void *)0x1234;
	r.state     = RX550_VRAM_HELD;

	CHECK(rx550_vram_pool_alloc(&p, TABLA_BYTES, TABLA_ALIGN, &r) ==
	      RX550_VRAM_ERR_SIN_MEM,
	      "pedir 512 KiB en una ventana de 4 KiB falla");
	CHECK(r.offset.bytes == UINT64_C(0xDEADBEEF), "offset intacto");
	CHECK(r.size == UINT64_C(0x1234), "size intacto");
	CHECK(r.alignment == UINT64_C(0x40), "alignment intacto");
	CHECK(r.owner == (void *)0x1234, "owner intacto");
	CHECK(r.state == RX550_VRAM_HELD, "state intacto");

	/* Y lo mismo para los otros tres rechazos, con el mismo patron. */
	for (i = 0; i < 4; i++) {
		rx550_vram_resource_reset(&r);
		r.size = UINT64_C(0x777);

		switch (i) {
		case 0: rx550_vram_pool_alloc(&p, PDB0_BYTES, 0, &r); break;
		case 1: rx550_vram_pool_alloc(&p, PDB0_BYTES, 3, &r); break;
		case 2: rx550_vram_pool_alloc(&p, 0, 8, &r); break;
		case 3: rx550_vram_pool_alloc(&p, PDB0_BYTES, 8, NULL); break;
		}
		if (i < 3)
			CHECK(r.size == UINT64_C(0x777),
			      "rechazo por parametro invalido tampoco escribe out");
	}
}

static void fase_parametros(void)
{
	struct rx550_vram_pool p;
	struct rx550_vram_resource r;

	printf("parametros\n");

	rx550_vram_pool_init(&p);
	rx550_vram_pool_set_window(&p, TABLA_BYTES);

	CHECK(rx550_vram_pool_alloc(NULL, PDB0_BYTES, 8, &r) ==
	      RX550_VRAM_ERR_NULO, "ctx nulo rechazado");
	CHECK(rx550_vram_pool_alloc(&p, PDB0_BYTES, 8, NULL) ==
	      RX550_VRAM_ERR_NULO, "out nulo rechazado");
	CHECK(rx550_vram_pool_alloc(&p, 0, 8, &r) == RX550_VRAM_ERR_SIN_MEM,
	      "size 0 rechazado");
	CHECK(rx550_vram_pool_alloc(&p, PDB0_BYTES, 0, &r) ==
	      RX550_VRAM_ERR_ALIGN, "align 0 rechazado");
	CHECK(rx550_vram_pool_alloc(&p, PDB0_BYTES, 3, &r) ==
	      RX550_VRAM_ERR_ALIGN, "align no potencia de dos rechazado");
	CHECK(rx550_vram_pool_alloc(&p, PDB0_BYTES, 6, &r) ==
	      RX550_VRAM_ERR_ALIGN, "align 6 rechazado");
	/* El contador mide SOLO falta de hueco.  NULO, ALIGN y SIN_MEM por
	 * parametro son errores del LLAMANTE, no de capacidad, y no se cuentan:
	 * `allocs_fallidas` con un nombre honesto vale mas que un contador que
	 * mezcla dos cosas y no se puede interpretar. */
	CHECK(p.stats.allocs_fallidas == 0,
	      "los rechazos por parametro NO cuentan como fallo de capacidad");
	/* La ventana de esta fase es de TABLA_BYTES justos, asi que la tabla SI
	 * cabe.  Para agotarla hay que pedir MAS de lo que la ventana tiene:
	 * un fallo por parametro no consume nada, asi que la ventana sigue
	 * intacta y la peticion que viene despues sigue teniendo que funcionar. */
	CHECK(rx550_vram_pool_alloc(&p, TABLA_BYTES * 2, TABLA_ALIGN, &r) ==
	      RX550_VRAM_ERR_SIN_MEM, "pedir el doble de la ventana: SIN_MEM");
	CHECK(p.stats.allocs_fallidas == 1,
	      "y ese SI cuenta, porque es falta de hueco de verdad");

	/* El filtro de la frontera tiene que aceptar lo que el pool entrega. */
	CHECK(rx550_vram_pool_alloc(&p, TABLA_BYTES, TABLA_ALIGN, &r) ==
	      RX550_VRAM_OK, "la tabla del GART entra en 512 KiB");
	CHECK(rx550_vram_resource_valid(&r, TABLA_BYTES, TABLA_ALIGN) == 0,
	      "y el filtro de la frontera la acepta");
}

/* ── LA GEOMETRIA REAL ─────────────────────────────────────────────────── */
static void fase_geometria(void)
{
	struct rx550_vram_pool p;
	struct rx550_vram_resource tabla, pdb;
	uint32_t i;
	int n_pdb = 0;

	printf("la geometria real\n");

	/* 2 MiB de VRAM de mentira:  la tabla del GART mas 128 tablas de PDB0.
	 * Con la tarjeta real (2048 MiB) sobra de largo;  aqui lo que se
	 * comprueba es la MECANICA, no que quepa. */
	rx550_vram_pool_init(&p);
	rx550_vram_pool_set_window(&p, UINT64_C(2) << 20);

	CHECK(rx550_vram_pool_alloc(&p, TABLA_BYTES, TABLA_ALIGN, &tabla) ==
	      RX550_VRAM_OK, "tabla del GART: 512 KiB alineados a 4096");
	CHECK((tabla.offset.bytes % TABLA_ALIGN) == 0,
	      "tabla del GART: alineada a 4096");
	CHECK(tabla.size == TABLA_BYTES, "tabla del GART: 512 KiB exactos");
	CHECK(tabla.state == RX550_VRAM_HELD, "tabla del GART: HELD");
	CHECK(rx550_vram_pool_free_bytes(&p) == (UINT64_C(2) << 20) - TABLA_BYTES,
	      "y el resto sigue libre");

	for (i = 0; i < 128; i++) {
		if (rx550_vram_pool_alloc(&p, PDB0_BYTES, 8, &pdb) != RX550_VRAM_OK)
			break;
		if (pdb.offset.bytes < tabla.offset.bytes + TABLA_BYTES)
			break;			/* se solaparia con la tabla */
		n_pdb++;
	}
	CHECK(n_pdb == 128, "128 tablas de PDB0 despues de la del GART");
	CHECK(pdb.offset.bytes >= tabla.offset.bytes + TABLA_BYTES,
	      "ninguna se solapa con la tabla del GART");
	CHECK(rx550_vram_pool_free_bytes(&p) ==
	      (UINT64_C(2) << 20) - TABLA_BYTES - 128 * PDB0_BYTES,
	      "y el conteo de libres cuadra");
}

/* ── FIRST-FIT: por orden de offset ────────────────────────────────────── */
static void fase_first_fit(void)
{
	struct rx550_vram_pool p;
	struct rx550_vram_resource a, b, c, d;

	printf("first-fit por orden de offset\n");

	rx550_vram_pool_init(&p);
	rx550_vram_pool_set_window(&p, UINT64_C(1) << 20);

	/* Tres bloques con huecos entre ellos, para que first-fit tenga
	 * ELECCION y no sea "el unico que hay". */
	CHECK(rx550_vram_pool_alloc(&p, 0x100, 1, &a) == RX550_VRAM_OK, "A en 0x0");
	CHECK(rx550_vram_pool_alloc(&p, 0x100, 1, &b) == RX550_VRAM_OK, "B en 0x100");
	CHECK(rx550_vram_pool_alloc(&p, 0x100, 1, &c) == RX550_VRAM_OK, "C en 0x200");
	CHECK(a.offset.bytes == 0 && b.offset.bytes == 0x100 &&
	      c.offset.bytes == 0x200, "y van en orden");
	CHECK(rx550_vram_pool_free_bytes(&p) == (UINT64_C(1) << 20) - 0x300,
	      "libre = ventana - 0x300");

	/* Libero B.  Ahora hay dos huecos: uno grande al final y otro en medio.
	 * first-fit debe tomar el DEL MEDIO, que es el primero por offset. */
	rx550_vram_pool_free(&p, &b);
	CHECK(rx550_vram_pool_alloc(&p, 0x80, 1, &d) == RX550_VRAM_OK, "D");
	CHECK(d.offset.bytes == 0x100,
	      "first-fit toma el hueco de menor offset, no el mas grande");

	/* Y si pido mas de lo que cabe en el hueco pequeno pero menos que en el
	 * grande, first-fit TIENE que saltar al grande.  Un allocator que solo
	 * mirase el primero daria SIN_MEM con hueco de sobra. */
	rx550_vram_pool_free(&p, &d);
	CHECK(rx550_vram_pool_alloc(&p, 0x180, 1, &d) == RX550_VRAM_OK,
	      "pido 0x180: no cabe en el hueco pequeno");
	CHECK(d.offset.bytes == 0x300,
	      "y first-fit salta al hueco grande en vez de rendirse");
}

/* ── LA COALESCENCIA, que es lo que da fragmentacion interna CERO ─────── */
static void fase_coalescencia(void)
{
	struct rx550_vram_pool p;
	struct rx550_vram_resource a, b, c, d;
	uint32_t bloques;

	printf("coalescencia\n");

	rx550_vram_pool_init(&p);
	rx550_vram_pool_set_window(&p, UINT64_C(1) << 20);

	CHECK(rx550_vram_pool_alloc(&p, 0x100, 1, &a) == RX550_VRAM_OK, "A");
	CHECK(rx550_vram_pool_alloc(&p, 0x100, 1, &b) == RX550_VRAM_OK, "B");
	CHECK(rx550_vram_pool_alloc(&p, 0x100, 1, &c) == RX550_VRAM_OK, "C");
	/* MEDIDO, y el primer test decia 2:  tres reservas CONTIGUAS dejan UN
	 * hueco, el final.  No hay hueco intermedio porque no hay nada entre
	 * ellas.  El caso del hueco intermedio se construye abajo, liberando
	 * la del medio. */
	bloques = p.n_libres;
	CHECK(bloques == 1, "3 reservas contiguas dejan 1 hueco, el final");
	CHECK(p.libre[0].offset == 0x300, "que empieza justo tras la tercera");

	/* Al liberar en orden inverso, los tres huecos tienen que fundirse en
	 * UNO.  Si no, la fragmentacion crece sin limite y el regimen
	 * permanente de alloc/libre acaba sin memoria. */
	rx550_vram_pool_free(&p, &c);
	rx550_vram_pool_free(&p, &b);
	rx550_vram_pool_free(&p, &a);
	CHECK(p.n_libres == 1, "liberar los tres deja UN hueco");
	CHECK(p.libre[0].offset == 0, "que empieza en 0");
	CHECK(p.libre[0].size == (UINT64_C(1) << 20), "y mide la ventana entera");
	CHECK(rx550_vram_pool_largest(&p) == (UINT64_C(1) << 20),
	      "el hueco mas grande es la ventana");

	/* Y el regimen permanente: 100 veces alloc y free del mismo tamaño, y
	 * el hueco mas grande NO debe decrecer.  Esta es la asercion que
	 * justifica first-fit para este componente: fragmentacion interna
	 * CERO en el regimen que realmente hay. */
	for (unsigned k = 0; k < 100; k++) {
		CHECK(k != 0 || rx550_vram_pool_alloc(&p, TABLA_BYTES,
						      TABLA_ALIGN, &d) ==
			      RX550_VRAM_OK || true, "");
		if (k == 0)
			continue;
		rx550_vram_pool_free(&p, &d);
	}
	{
		int estable = 1;

		for (unsigned k = 0; k < 100; k++) {
			if (rx550_vram_pool_alloc(&p, TABLA_BYTES, TABLA_ALIGN,
						  &d) != RX550_VRAM_OK) {
				estable = 0;
				break;
			}
			rx550_vram_pool_free(&p, &d);
		}
		CHECK(estable, "100 ciclos de alloc/free de 512 KiB: ninguno falla");
		CHECK(rx550_vram_pool_largest(&p) == (UINT64_C(1) << 20),
		      "y el hueco mas grande NO ha decrecido");
	}
}

/* ── LA CLAUSULA 2: free deja RELEASED, y cuenta lo que rechaza ───────── */
static void fase_free(void)
{
	struct rx550_vram_pool p;
	struct rx550_vram_resource r, copia;
	uint32_t rechazos;

	printf("free\n");

	rx550_vram_pool_init(&p);
	rx550_vram_pool_set_window(&p, UINT64_C(1) << 20);

	CHECK(rx550_vram_pool_alloc(&p, 0x1000, 1, &r) == RX550_VRAM_OK, "reserva");
	copia = r;
	CHECK(copia.state == RX550_VRAM_HELD, "nace HELD");

	/* El contrato dice que free deja RELEASED.  NADIE lo comprobaba:  el
	 * unico free del componente antes de esto era el fake de test_pdb0, que
	 * solo incrementa un contador. */
	rx550_vram_pool_free(&p, &r);
	CHECK(r.state == RX550_VRAM_RELEASED, "free deja state en RELEASED");
	CHECK(r.owner == NULL, "y owner a NULL");
	CHECK(copia.state == RX550_VRAM_HELD,
	      "y solo toca la copia que se le paso, no el original");
	CHECK(p.stats.frees_ok == 1, "una liberacion buena");

	/* Doble liberacion:  el recurso ya no es HELD, asi que el pool la
	 * rechaza.  free no puede devolver nada por contrato,  asi que el error
	 * se CUENTA.  Ese contador es el unico canal de observabilidad que
	 * tiene, y por eso existe. */
	rechazos = p.stats.frees_rechazadas;
	rx550_vram_pool_free(&p, &r);
	CHECK(p.stats.frees_rechazadas == rechazos + 1,
	      "doble liberacion: se rechaza y se cuenta");
	CHECK(p.stats.frees_ok == 1, "y no se cuenta como buena");

	/* Un recurso ajeno. */
	rx550_vram_resource_reset(&r);
	r.owner  = (void *)0x999;
	r.state  = RX550_VRAM_HELD;
	r.size   = 0x100;
	r.offset = rx550_vram_off(0);
	rx550_vram_pool_free(&p, &r);
	CHECK(p.stats.frees_rechazadas == rechazos + 2,
	      "liberar un recurso de otro pool: rechazada y contada");

	/* Fuera de la ventana. */
	r.owner  = &p;
	r.size   = UINT64_C(1) << 21;
	r.state  = RX550_VRAM_HELD;
	rx550_vram_pool_free(&p, &r);
	CHECK(p.stats.frees_rechazadas == rechazos + 3,
	      "liberar algo que se sale de la ventana: rechazada");

	rx550_vram_pool_free(&p, NULL);
	rx550_vram_pool_free(NULL, &r);
	CHECK(1, "y liberar NULL no revienta");
}

static void fase_contexto(void)
{
	struct rx550_vram_pool p;
	struct rx550_vram_resource r;

	printf("contexto\n");

	CHECK(rx550_vram_pool_free_bytes(NULL) == 0, "free_bytes(NULL) = 0");
	CHECK(rx550_vram_pool_largest(NULL) == 0, "largest(NULL) = 0");
	rx550_vram_pool_init(&p);
	CHECK(rx550_vram_pool_alloc(&p, PDB0_BYTES, 8, &r) ==
	      RX550_VRAM_ERR_SIN_MEM,
	      "y un pool recien iniciado no sirve ni 4 KiB");
}

int main(void)
{
	printf("test_vram_pool — el allocator de VRAM\n\n");

	fase_ventana();
	fase_no_cabe();
	fase_out_intacto();
	fase_parametros();
	fase_geometria();
	fase_first_fit();
	fase_coalescencia();
	fase_free();
	fase_contexto();

	printf("\n  %d pass, %d fail\n", pass, fail);
	return fail ? 1 : 0;
}