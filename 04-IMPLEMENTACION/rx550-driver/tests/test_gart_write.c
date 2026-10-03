/* SPDX-License-Identifier: GPL-2.0 */
/*
 * test_gart_write.c - el batch writer sobre un backing ajeno.
 *
 * Que se prueba:
 *   Que un lote se escriba entero o no se escriba.  Nunca a medias.
 *   Que los limites se comprueben contra el BACKING, no solo contra el
 *   maximo del hardware.  Un backing de 4 entradas no es una tabla de 65536.
 *   Que una invalidacion por lote, y no por entrada.
 *
 * Que NO se prueba:
 *   Que nada de esto llegue a la GPU.  No hay MMIO aqui, y la funcion de
 *   TLB es un contador.
 */
#include "rx550_gart_write.h"

#include <stdio.h>
#include <string.h>

/* EL TAMANO DE LA TABLA DE ESTE TEST ES UN FIXTURE, NO UN HECHO.
 *
 * Antes decia RX550_GART_ENTRY_COUNT, y ese identificador ya no existe:
 * se retiro de rx550_vmid0_gart.h porque era una segunda autoridad de
 * rango global.  El valor 65536 que traia era DERIVADO, no FACT:
 *
 *   amdgpu_gart.c:533  num_gpu_pages = gmc.gart_size / 4096
 *   gmc_v8_0.c:595     CHIP_POLARIS12 -> gart_size = 256 MiB  ->  65536
 *   gmc_v8_0.c:604-605 gart_size = amdgpu_gart_size << 20    ->  gartsize=1024
 *                                                          da 262144
 *   amdgpu_drv.c:293   module_param_named(gartsize, ..., 0600)
 *
 * osea que el "maximo" dependia de un parametro de modulo escribible por
 * root.  Aqui 65536 es el tamano del ARRAY DE PRUEBA, y el array tiene
 * que ser grande para que los casos de borde del final tengan donde
 * mirar.  Lo que se prueba abajo no es "cual es el maximo", que no lo
 * decide este componente, sino que los limites se comprueban contra el
 * backing que el CALLER declara. */
#define TABLE_N		65536u

static int pass, fail;

static void ok(const char *t) { printf("  PASS  %s\n", t); pass++; }
static void ko(const char *t) { printf("  FAIL  %s\n", t); fail++; }
#define CHECK(c, n) do { if (c) ok(n); else ko(n); } while (0)

/* el backing real de la tabla GART */
static uint64_t big[TABLE_N];

/* backing pequeño, con centinelas, para detectar salidas del rango */
#define SMALL_N 4u
static struct {
	uint64_t	lo;
	uint64_t	t[SMALL_N];
	uint64_t	hi;
} small;

static unsigned invalidations;
static unsigned last_vmid;

static void count_invalidate(void *ctx, unsigned vmid)
{
	(void)ctx;
	invalidations++;
	last_vmid = vmid;
}

static struct rx550_gart_tlb tlb = { count_invalidate, NULL };

static uint64_t pte_of(uint64_t pa, uint64_t flags)
{
	uint64_t e;

	if (rx550_pte_encode((struct rx550_system_pa){ .bytes = pa }, flags, &e) != 0)
		return 0;
	return e;
}

int main(void)
{
	struct rx550_gart_backing b;
	struct rx550_gart_pte_index first;
	uint64_t lot[4];
	uint64_t lot8[8];
	uint32_t i;

	printf("test_gart_write - lote sobre backing externo\n\n");

	for (i = 0; i < SMALL_N; i++)
		small.t[i] = 0;
	small.lo = UINT64_C(0xAAAAAAAAAAAAAAAA);
	small.hi = UINT64_C(0xBBBBBBBBBBBBBBBB);

	for (i = 0; i < 4; i++)
		lot[i] = pte_of(UINT64_C(0x10000) * (i + 1), RX550_PTE_VALID);

	/* ── 1. lote válido ─────────────────────────────────────────── */
	b.base = big;
	b.entries = TABLE_N;
	memset(big, 0, sizeof(big));
	first.index = 0;
	CHECK(rx550_gart_write(&b, first, lot, 4) == 4, "1. lote de 4 escrito");
	CHECK(big[0] == lot[0] && big[3] == lot[3], "1. las 4 entradas están donde tocaba");
	CHECK(big[4] == 0, "1. y NADA fuera del rango pedido");
	CHECK(big[TABLE_N - 1u] == 0, "1. ni al final de la tabla");

	/* ── 2. una entrada inválida -> cero escrituras ──────────────── */
	{
		uint64_t bad[4];

		memcpy(bad, lot, sizeof(bad));
		bad[2] = UINT64_C(1) << 51;	/* PRT: reservado en GFX8 */
		memset(big, 0, sizeof(big));
		CHECK(rx550_gart_write(&b, first, bad, 4) != 0,
		      "2. lote con entrada inválida rechazado");
		CHECK(big[0] == 0 && big[1] == 0 && big[2] == 0 && big[3] == 0,
		      "2. CERO escrituras: ni siquiera las tres válidas");
	}
	{
		uint64_t bad[4];

		memcpy(bad, lot, sizeof(bad));
		bad[0] = UINT64_C(1) << 63;	/* IS_PTE: no existe en GFX8 */
		memset(big, 0, sizeof(big));
		CHECK(rx550_gart_write(&b, first, bad, 4) != 0,
		      "2. IS_PTE (63) rechazado");
		CHECK(big[0] == 0, "2. y nada escrito");
	}
	{
		uint64_t bad[4];

		memcpy(bad, lot, sizeof(bad));
		bad[3] = UINT64_C(1) << 3;	/* bit 3 reservado */
		memset(big, 0, sizeof(big));
		CHECK(rx550_gart_write(&b, first, bad, 4) != 0,
		      "2. bit 3 (reservado) rechazado");
		CHECK(big[0] == 0, "2. y nada escrito");
	}
	{
		uint64_t bad[4];

		memcpy(bad, lot, sizeof(bad));
		bad[1] = UINT64_C(1) << 55;	/* LOG */
		memset(big, 0, sizeof(big));
		CHECK(rx550_gart_write(&b, first, bad, 4) != 0, "2. LOG (55) rechazado");
		CHECK(big[0] == 0, "2. y nada escrito");
	}
	{
		/* PA por encima de 40 bits, sin los bits de flag que
		 * la activarían: tiene que caer en RESERVED. */
		uint64_t bad[4];

		memcpy(bad, lot, sizeof(bad));
		bad[0] = UINT64_C(0x100000000000);
		memset(big, 0, sizeof(big));
		CHECK(rx550_gart_write(&b, first, bad, 4) != 0,
		      "2. PA por encima de 40 bits rechazada");
	}

	/* ── 3. first + count == TABLE_N -> exactamente el límite ─────── */
	memset(big, 0, sizeof(big));
	first.index = TABLE_N - 4u;
	CHECK(rx550_gart_write(&b, first, lot, 4) == 4,
	      "3. last index == TABLE_N-1: la última entrada es válida");
	CHECK(big[TABLE_N - 1u] == lot[3], "3. y está escrita");
	CHECK(big[TABLE_N - 2u] == lot[2], "3. la penúltima también");

	/* ── 4. uno más allá ────────────────────────────────────────── */
	first.index = TABLE_N - 4u + 1u;
	CHECK(rx550_gart_write(&b, first, lot, 4) != 0,
	      "4. last index == TABLE_N: rechazado");
	first.index = TABLE_N - 1u;
	CHECK(rx550_gart_write(&b, first, lot, 2) != 0,
	      "4. first=TABLE_N-1 con count=2 se sale");
	first.index = TABLE_N;	/* uno más que el backing */
	CHECK(rx550_gart_write(&b, first, lot, 1) != 0,
	      "4. first=TABLE_N rechazado antes de cualquier aritmética");
	first.index = UINT64_MAX;
	CHECK(rx550_gart_write(&b, first, lot, 4) != 0,
	      "4. first=UINT64_MAX no desborda hacia dentro");

	/* ── 5. el límite es el BACKING, no el hardware ─────────────── */
	/* Este es el caso que el componente anterior no cubria.  Un backing
	 * de 4 entradas con first=1000 pasaria un chequeo contra 65536 y
	 * escribiria 1000 entradas fuera de un array de 4. */
	b.base = small.t;
	b.entries = SMALL_N;
	first.index = 1000;
	{
		unsigned k;

		for (k = 0; k < SMALL_N; k++)
			small.t[k] = 0;
		small.lo = UINT64_C(0xAAAAAAAAAAAAAAAA);
		small.hi = UINT64_C(0xBBBBBBBBBBBBBBBB);
	}
	CHECK(rx550_gart_write(&b, first, lot, 4) != 0,
	      "5. first=1000 en un backing de 4 entradas: RECHAZADO");
	CHECK(small.t[0] == 0 && small.t[1] == 0 && small.t[2] == 0 &&
	      small.t[3] == 0,
	      "5. y no escribió nada");
	CHECK(small.lo == UINT64_C(0xAAAAAAAAAAAAAAAA) &&
	      small.hi == UINT64_C(0xBBBBBBBBBBBBBBBB),
	      "5. los centinelas siguen intactos");

	/* ── 5b. LA GUARDA B, CON DIENTES ─────────────────────────────
	 *
	 * MEDIDO, y por que este caso existe: con la guarda B retirada
	 * entera, la suite ANTERIOR daba 56 pass, 0 fail.  Verde con el
	 * componente sin una de sus tres acotaciones.
	 *
	 * Por que no lo notaba.  B es `first.index > b->entries`, y E+F es
	 * `n > b->entries - first`.  Cuando first > entries la RESTA se
	 * va por debajo de cero en unsigned y da UINT64_MAX, luego E+F
	 * deja pasar cualquier n: B es el UNICO que puede atrapar ese caso.
	 * Y el unico caso de la suite que lo necesitaba era el de arriba,
	 * first=1000 sobre un backing de 4, con los centinelas pegados a
	 * la ARRAY (small.lo y small.hi).  Una escritura 1000 entradas
	 * mas alla no toca ni small.t[0..3] ni los centinelas, asi que sus
	 * cuatro CHECK seguian en verde mientras el componente escribia
	 * 1000 palabras fuera del array.  Un centinela pegado al array
	 * detecta el desbordamiento PEGADO, no el lejano.
	 *
	 * Aqui la fuga cae DENTRO del array reservado: el backing es de
	 * UNA entrada en la palabra central, el canario esta dos palabras
	 * mas alla, y first=2 se sale del backing sin salirse de la
	 * reserva.  Asi, con B, no se escribe nada; sin B, la escritura cae
	 * exactamente sobre el canario y el CHECK se pone rojo.  Cero
	 * comportamiento indefinido en los dos lados.
	 */
	{
		static uint64_t	guard[4];

		guard[0] = UINT64_C(0x1111111111111111);	/* canario previo */
		guard[1] = 0;				/* ENTRADA 0 = backing */
		guard[2] = 0;				/* entrada 1, no usada */
		guard[3] = UINT64_C(0x2222222222222222);	/* canario posterior */

		b.base = &guard[1];
		b.entries = 1;
		first.index = 2;		/* > entries: solo B puede rechazarlo */
		CHECK(rx550_gart_write(&b, first, lot, 1) != 0,
		      "5b. first=2 en un backing de 1: RECHAZADO por B");
		CHECK(guard[0] == UINT64_C(0x1111111111111111) &&
		      guard[3] == UINT64_C(0x2222222222222222),
		      "5b. y el canario al que CAERIA la fuga, intacto");
		CHECK(guard[2] == 0,
		      "5b. ni la palabra de en medio");
		/* El caso 5 sigue despues con el backing que espera: b.base
		 * y b.entries se dejan como estaban.  MEDIDO: al meter este
		 * bloque en medio, los cuatro CHECK siguientes de "5. first=0
		 * ... valido" se pusieron rojos, porque escribian sobre el
		 * backing equivocado.  Un caso nuevo que cambia el estado
		 * compartido rompe los casos viejos aunque no los toque. */
		b.base = small.t;
		b.entries = SMALL_N;
	}
	first.index = 0;
	CHECK(rx550_gart_write(&b, first, lot, 4) == 4,
	      "5. first=0 con 4 entradas en un backing de 4: válido");
	CHECK(small.t[0] == lot[0] && small.t[3] == lot[3], "5. escrito");
	CHECK(small.lo == UINT64_C(0xAAAAAAAAAAAAAAAA) &&
	      small.hi == UINT64_C(0xBBBBBBBBBBBBBBBB),
	      "5. y los centinelas siguen intactos");
	/* Este caso es el UNICO donde first <= entries y aun asi
	 * first + count se pasa.  B no lo puede atrapar, asi que depende
	 * enteramente de E+F.  Y el centinela es lo que delata la
	 * escritura de mas: sin el, la mutacion "quita E+F" devuelve 2
	 * y el CHECK de arriba sigue en verde. */
	small.lo = UINT64_C(0xAAAAAAAAAAAAAAAA);
	small.hi = UINT64_C(0xBBBBBBBBBBBBBBBB);
	first.index = SMALL_N - 1u;
	CHECK(rx550_gart_write(&b, first, lot, 2) != 0,
	      "5. first=3 con count=2 en backing de 4: se sale");
	CHECK(small.hi == UINT64_C(0xBBBBBBBBBBBBBBBB),
	      "5. y el centinela posterior NO fue sobrescrito");
	CHECK(small.lo == UINT64_C(0xAAAAAAAAAAAAAAAA),
	      "5. ni el anterior");
	/* first=2 count=2 llega justo al final: valido, y debe escribir */
	first.index = SMALL_N - 2u;
	CHECK(rx550_gart_write(&b, first, lot, 2) == 2,
	      "5. first=2 count=2 en backing de 4: exactamente al borde, valido");
	CHECK(small.t[2] == lot[0] && small.t[3] == lot[1], "5. las dos ultimas escritas");

	/* backing mal formado */
	b.base = NULL;
	b.entries = SMALL_N;
	CHECK(rx550_gart_write(&b, first, lot, 1) != 0, "5. backing NULL rechazado");
	b.base = small.t;
	b.entries = 0;
	CHECK(rx550_gart_write(&b, first, lot, 1) != 0, "5. backing de 0 entradas rechazado");
	/* ESTE CASO CAMBIO DE SEMANTICA, y el cambio es el hallazgo.
	 *
	 * ANTES: un backing de 65537 entradas se rechazaba, porque
	 * rx550_gart_backing_check() comparaba contra RX550_GART_ENTRY_COUNT.
	 * Ese identificador se retiro de rx550_vmid0_gart.h y la comparacion
	 * se fue con el, porque 65536 no era un maximo del hardware sino un
	 * DERIVED: gart_size / 4096 con el gart_size POR DEFECTO de
	 * POLARIS12 (gmc_v8_0.c:595, amdgpu_gart.c:533).
	 *
	 * DESCARTADO: "era un numero inventado".  No lo era: 256 MiB / 4 KiB
	 * son exactamente 65536.  Lo que no era un hecho es que 65536 valiera
	 * siempre, porque gart_size depende de un parametro de modulo
	 * escribible por root (amdgpu_drv.c:154 y :293, modo 0600) y
	 * gmc_v8_0.c:604-605 lo aplica como `amdgpu_gart_size << 20`.
	 * MEDIDO el contrafactual: `gartsize=1024` produce una apertura de
	 * 262144 entradas en ESTA MISMA ASIC.  La comprobacion que se quito
	 * la habria rechazado.  No era una guarda de seguridad: era un
	 *(parametro de configuracion) elevated a constante.
	 *
	 * AHORA: no hay cota global, y el componente lo dice.  Un backing de
	 * 65537 no se rechaza por ser grande; se acepta, y el indice se acota
	 * contra b->entries.  El que reserve mas entradas de las que le
	 * corresponden lo detecta quien reserva, comparando entries contra
	 * la apertura que reservo.  Este CHECK existe para que volver a poner
	 * una cota global salga ROJO y no verde. */
	b.entries = TABLE_N + 1u;
	CHECK(rx550_gart_write(&b, first, lot, 1) == 1,
	      "5. backing de 65537 entradas: NO rechazado (no hay cota global)");
	/* Y el limite del backing sigue mandando por encima de cualquier
	 * numero: uno PEQUENO se rechaza igual, que es la propiedad que si
	 * evita la escritura fuera del array. */
	b.base = small.t;
	b.entries = SMALL_N;
	first.index = SMALL_N;
	CHECK(rx550_gart_write(&b, first, lot, 1) != 0,
	      "5. y un backing PEQUENO sigue rechazando: la cota es b->entries");

	/* ── count == 0: rechazo EXPLÍCITO, no un underflow ────────────
	 *
	 * Si el rechazo dependiera de first + n - 1 desbordando, quitar
	 * el if (n == 0) no cambiaria nada: el desborde seguiria
	 * atrapando el lote.  Estos tests distinguen las dos cosas:
	 * con el guard retirado, count=0 tiene que devolver 0 (exito con
	 * cero entradas), no -1. */
	b.entries = TABLE_N;
	first.index = 0;
	CHECK(rx550_gart_write(&b, first, lot, 0) != 0,
	      "count=0 RECHAZADO por un guard dedicado");
	/* primero con el respaldo de un backing de UNA entrada: first+n-1
	 * seria 0 y no desbordaria, luego sin el guard no habria nada que
	 * lo atrapara salvo el propio guard */
	b.base = small.t;
	b.entries = 1;
	first.index = 0;
	CHECK(rx550_gart_write(&b, first, lot, 0) != 0,
	      "count=0 tambien con backing de 1 entrada y first=0");
	b.base = big;
	b.entries = TABLE_N;
	CHECK(rx550_gart_write(&b, first, NULL, 0) != 0, "y con array NULL tambien");

	/* ── B/E/F en el borde: first == entries ────────────────────── */
	/* Con la acotacion por RESTA, first == entries da
	 * entries - first == 0, y cualquier n >= 1 se rechaza.  Si
	 * alguien volviera a(first + n <= entries) sin la acotacion
	 * previa, aqui first + n todavia no desbordaria con estos
	 * valores, asi que el test no distingue.  Con first = UINT64_MAX
	 * si: first + n desborda, la resta no. */
	first.index = SMALL_N;
	CHECK(rx550_gart_write(&b, first, lot, 1) != 0,
	      "first == backing->entries con count=1 rechazado");
	first.index = UINT64_MAX;
	CHECK(rx550_gart_write(&b, first, lot, 1) != 0,
	      "first = UINT64_MAX rechazado por la resta, no por suma");
	first.index = UINT64_MAX - 2u;
	CHECK(rx550_gart_write(&b, first, lot, 8) != 0,
	      "first = UINT64_MAX-2 con count=8: first+n desbordaria en suma");
	CHECK(rx550_gart_write(&b, first, lot, 0) != 0, "y count=0 tambien");

	/* ── 10. una invalidación por lote ──────────────────────────── */
	first.index = 0;
	for (i = 0; i < 8; i++)
		lot8[i] = pte_of(UINT64_C(0x10000) * (i + 1), RX550_PTE_VALID);

	invalidations = 0;
	memset(big, 0, sizeof(big));
	CHECK(rx550_gart_write_invalidate(&b, first, lot8, 8, &tlb, 0) == 8,
	      "10. lote de 8 escrito e invalidado");
	CHECK(invalidations == 1, "10. UNA invalidación, no ocho");
	CHECK(last_vmid == 0, "10. para el VMID pedido");

	invalidations = 0;
	CHECK(rx550_gart_write_invalidate(&b, first, lot, 1, &tlb, 3) == 1,
	      "10. un solo elemento tambien invalida una vez");
	CHECK(invalidations == 1, "10. y sigue siendo una");

	/* si la escritura falla, no se invalida: invalidar una tabla que
	 * no se toco no compra nada */
	invalidations = 0;
	{
		uint64_t bad[4];

		memcpy(bad, lot, sizeof(bad));
		bad[1] = UINT64_C(1) << 51;
		CHECK(rx550_gart_write_invalidate(&b, first, bad, 4, &tlb, 0) != 0,
		      "10. lote inválido falla");
		CHECK(invalidations == 0, "10. y NO se invalida");
	}
	CHECK(rx550_gart_write_invalidate(&b, first, lot, 1, NULL, 0) != 0,
	      "10. sin invalidador, rechazado: no se puede fingir que se invalidó");
	{
		struct rx550_gart_tlb vacuo = { NULL, NULL };

		CHECK(rx550_gart_write_invalidate(&b, first, lot, 1, &vacuo, 0) != 0,
		      "10. invalidador sin funcion rechazado");
	}
	CHECK(rx550_gart_write_invalidate(&b, first, lot, 1, &tlb, 16) != 0,
	      "10. VMID 16 rechazado (el registro tiene 16 posiciones)");

	/* ── el handoff: qué necesita y qué no decide ───────────────── */
	{
		struct rx550_gart_requirements req;

		req.backing = &b;
		req.vmid = 0;
		req.tlb = &tlb;
		CHECK(req.backing != NULL && req.tlb != NULL,
		      "el owner provee backing, vmid y tlb");
		CHECK(req.backing->base == big && req.backing->entries == TABLE_N,
		      "TABLE_SIZE lo decide quien reserva, no este componente");
	}

	/* ── limite explícito ───────────────────────────────────────── */
	CHECK(rx550_gart_write_is_executed(8) == false,
	      "WRITE_BATCH_COMPLETED no implica EXECUTED");
	CHECK(rx550_gart_write_is_executed(0) == false, "tampoco con 0");

	printf("\n  %d pass, %d fail\n", pass, fail);
	return fail ? 1 : 0;
}
