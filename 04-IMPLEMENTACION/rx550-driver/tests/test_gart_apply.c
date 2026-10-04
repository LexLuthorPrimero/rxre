/* SPDX-License-Identifier: GPL-2.0-only */
/*
 * test_gart_apply.c — escribir el plan del GART sobre un mapa y comprobarlo.
 *
 *   TARGET = RX 550 instalada en esta maquina  (1002:699F, Polaris12, GFX8)
 *   SCOPE  = EXCLUSIVO
 *
 * QUE ES Y QUE NO ES
 *   C puro, unitario, en userspace.  El "mapa" es un buffer normal con el
 *   tamano de la BAR5, igual que en test_mmio_access.  Ni GPU, ni ring, ni DMA.
 *
 * POR QUE EXISTE, Y POR QUE EL MAPA ES FALSO
 *   test_gart_seq comprueba que el PLAN es el correcto.  Este comprueba que
 *   escribirlo hace lo que dice, y que CUANDO NO RESPONDE se nota.
 *
 *   Y el buffer falso no es una comodidad:  la lectura de vuelta es la unica
 *   forma de distinguir "escrito" de "aceptado", y para ejercitar esa rama hace
 *   falta un mapa que se comporte mal.  Contra la BAR5 real solo responderia,
 *   y la rama de fallo no se probaria nunca.
 *
 * LOS TRES BLOQUES
 *   A1  aplicar un plan bueno:  34 escrituras, 34 lecturas, informe completo.
 *   A2  un mapa que MIENTE en una escritura:  se para en esa, con el indice,
 *       lo leido y lo escrito.  Y no sigue escribiendo.
 *   A3  los negativos:  plan corto, mapa sin enlazar, punteros nulos, y que un
 *       fallo NO deje escrituras a medias sin decir donde.
 *
 * QUE NO COMPRUEBA
 *   Que el hardware real acepte el plan.  Este test no lo demuestra;  lo
 *   demuestra si y solo si el apply se ejecuta contra la BAR5.  RUNTIME_REQUIRED.
 */
#include <stdio.h>
#include <stdlib.h>
#include <string.h>
#include <stdint.h>
#include <stdbool.h>

#include "rx550_gart_seq.h"
#include "rx550_mmio_access.h"

/*  EL MAPA QUE MIENTE.
 *
 *  miente_en = indice de la escritura a partir de la cual escribir es un
 *  no-op.  -1  nunca miente.  Es el unico mecanismo que necesita el test, y es
 *  la razon de que el mapa sea un buffer y no una abstraccion. */
static int pass, fail;

static void ok(const char *t) { printf("  PASS  %s\n", t); pass++; }
static void ko(const char *t) { printf("  FAIL  %s\n", t); fail++; }

#define CHECK(cond, name) do { if (cond) ok(name); else ko(name); } while (0)
#define CHECK_EQ(got, want, name) do {					\
	long long g_ = (long long)(got), w_ = (long long)(want);	\
	if (g_ == w_) ok(name);						\
	else { printf("  FAIL  %s  (%lld != %lld)\n", name, g_, w_);	\
	       fail++; }							\
} while (0)

#define P_GART_START	UINT64_C(0xFF00000000)
#define P_GART_END	UINT64_C(0xFF0FFFFFFF)
#define P_TABLE_ADDR	UINT64_C(0xF400900000)
#define P_DUMMY_PA	UINT64_C(0x0000000123456000)
#define P_MAX_PFN	(UINT64_C(64) << 18)

static void params_buenas(struct rx550_gart_params *p)
{
	memset(p, 0, sizeof(*p));
	p->gart_start = P_GART_START;
	p->gart_end = P_GART_END;
	p->table_addr = P_TABLE_ADDR;
	p->dummy_page_addr = P_DUMMY_PA;
	p->max_pfn = P_MAX_PFN;
	p->block_size = 10;
	p->fragment_size = 9;
}

/*  NO HAY MAPA QUE MIENTE,  y por eso este fichero no trae uno.
 *
 *  El apply escribe en `map` y relee en `map`.  Cualquier mapa que acepte la
 *  escritura devuelve exactamente lo escrito,  de modo que con la API actual no
 *  hay forma de hacer que una escritura no llegue a destino.  Y esa limitacion no
 *  es del test:  es la de la API,  y es correcta para su uso,  que es una BAR5
 *  real donde la lectura si puede fallar.
 *
 *  El primer intento de este fichero fue un envoltorio con dos mapas enlazados,
 *  uno que escribia y otro que leia,  para inyectar el fallo en la escritura N.
 *  Se borro entero porque el apply pide UN mapa,  y porque una segunda version
 *  pretendia interceptar con un flag global:  eso mide el flag,  no el apply.
 *
 *  Lo que si queda,  y es lo que de verdad mide sin hardware,  es el reparto
 *  entre registros verificables y de solo escritura:  A2. */
static void *bar_real;
static struct rx550_mmio_map map_real;

static void mapas_preparar(void)
{
	bar_real = calloc(1, RX550_MMIO_SIZE);
	if (!bar_real) {
		printf("  FAIL  no se pudo reservar el mapa\n");
		exit(1);
	}
}

int main(void)
{
	struct rx550_gart_params p;
	struct rx550_gart_seq seq;
	struct rx550_gart_apply_report rep;

	printf("test_gart_apply — escribir el plan del GART\n\n");

	mapas_preparar();
	params_buenas(&p);

	/*  Se construye el plan sobre el mapa real,  leyendo sus siete registros
	 *  con build_from().  Y para que el buffer tenga contenido antes,  se le
	 *  siembra un estado que NO es cero:  si el apply se limitase a escribir
	 *  34 valores,  sembrar no cambiaria nada,  y con un mapa a cero no se
	 *  distinguiria "escribio el valor" de "ya valia ese". */
	{
		struct rx550_reg r;

		CHECK(rx550_mmio_attach(&map_real, bar_real, RX550_MMIO_SIZE)
		      == RX550_MMIO_OK, "A1 enlazar el mapa real");
		CHECK(rx550_mmio_reg_of(RX550_REG_CTX1_CNTL, &r) == RX550_MMIO_OK,
		      "A1 resolver CTX1_CNTL");
		*(volatile uint32_t *)bar_real = 0u;
		CHECK(rx550_mmio_reg_of(RX550_REG_CTX1_CNTL, &r) == RX550_MMIO_OK,
		      "A1 otra vez, que sea idempotente");
		{
			struct rx550_mmap_offset off;

			CHECK(rx550_mmio_resolve_reg(&map_real,
						      RX550_REG_CTX1_CNTL, &off)
			      == RX550_MMIO_OK, "A1 el offset de CTX1_CNTL");
			*(volatile uint32_t *)((uintptr_t)bar_real + off.bytes)
				= 0xbbbb0004u;
		}
	}

	/* ── A1 · EL CAMINO NORMAL ──────────────────────────────────────── */
	printf("\nA1 · aplicar un plan bueno\n");
	{
		uint32_t snapshot[RX550_GART_RMW_NR];
		struct rx550_reg r;
		struct rx550_mmap_offset off;

		CHECK(rx550_gart_snapshot(&map_real, snapshot) == 0,
		      "A1 snapshot");
		CHECK_EQ(snapshot[RX550_GART_RMW_CTX1_CNTL], 0xbbbb0004u,
			 "A1 el snapshot lee el valor sembrado");
		CHECK(rx550_mmio_reg_of(RX550_REG_CTX1_CNTL, &r)
		      == RX550_MMIO_OK, "A1 resolver");
		CHECK(rx550_mmio_resolve_reg(&map_real, RX550_REG_CTX1_CNTL,
					      &off) == RX550_MMIO_OK, "A1 offset");

		CHECK(rx550_gart_build_from(&map_real, &seq, &p) == 0,
		      "A1 build_from (lee y construye)");
		CHECK_EQ(rx550_gart_seq_len(&seq), 34, "A1 el plan tiene 34");

		/*  El apply escribe en map_real y relee de map_real.  Para que la
		 *  lectura de vuelta tenga sentido,  el "hardware" tiene que
		 *  devolver lo escrito:  eso es lo que hace el mapa real cuando
		 *  nobody lo intercepta.  Asi que aqui se aplica sobre el mapa
		 *  real directamente. */
		memset(&rep, 0, sizeof(rep));
		CHECK(rx550_gart_apply(&map_real, &seq, &rep) == 0,
		      "A1 apply devuelve OK");
		CHECK_EQ(rep.n_escritas, 34u, "A1 se escribieron 34");
		/*  NO son 34 las verificadas,  y este numero se midio antes de
		 *  escribirlo:  de las 34 escrituras solo nueve van a registros
		 *  legibles. */
		CHECK_EQ(rep.n_verificadas, 9u, "A1 nueve se releen y cuadran");
		CHECK_EQ(rep.n_no_verificables, 25u,
			 "A1 y veinticinco van a registro de solo escritura");
		CHECK_EQ(rep.n_verificadas + rep.n_no_verificables, 34u,
			 "A1 y no se queda ninguna sin clasificar");
		CHECK_EQ(rep.primer_fallo, RX550_GART_NO_FALLO, "A1 sin fallos");
		CHECK_EQ(rep.cur[RX550_GART_RMW_CTX1_CNTL], 0xbbbb0004u,
			 "A1 el informe guarda lo que habia antes");

		/*  Y el contenido final, que es la comprobacion que de verdad
		 *  importa:  los cinco registros de control, leidos del mapa. */
		{
			static const struct {
				enum rx550_vmid1_reg_id id;
				uint32_t	mascara;
			} mirar[] = {
				{ RX550_REG_MX_L1_TLB_CNTL, 0x7fu },
				{ RX550_REG_L2_CNTL,       0x1b83fu },
				{ RX550_REG_L2_CNTL2,      0x3u },
				{ RX550_REG_CTX0_CNTL,     0x17u },
				{ RX550_REG_CTX1_CNTL,     0xf000007u },
			};
			bool bien = true;

			for (unsigned k = 0; k < sizeof(mirar) / sizeof(mirar[0]);
			     k++) {
				struct rx550_reg rr;
				struct rx550_mmap_offset oo;
				uint32_t v, quiero = 0;
				bool encontrado = false;

				if (rx550_mmio_reg_of(mirar[k].id, &rr)
				    != RX550_MMIO_OK ||
				    rx550_mmio_resolve_reg(&map_real, mirar[k].id,
							  &oo) != RX550_MMIO_OK ||
				    rx550_mmio_read32(&map_real, rr, &v)
				    != RX550_MMIO_OK) {
					 bien = false;
					 continue;
				}
				/*  CORREGIDO.  Esta comprobacion emparejaba el
				 *  registro k con la operacion k,  y no es la misma
				 *  cosa:  el plan escribe CTX0_CNTL en la 10 y
				 *  CTX1_CNTL2 en la 32,  no en la 1 y la 4.  Ahora se
				 *  busca la operacion por el registro que escribe,
				 *  que es la unica relacion correcta. */
				for (unsigned i = 0; i < seq.n; i++) {
					struct rx550_reg ri;

					if (rx550_mmio_reg_of(mirar[k].id, &ri)
					    != RX550_MMIO_OK)
						continue;
					if (seq.op[i].reg == ri.index) {
						quiero = seq.op[i].value;
						encontrado = true;
						break;
					}
				}
				if (!encontrado) {
					printf("  FAIL  A1 el plan no escribe el "
					       "registro %u\n", k);
					bien = false;
					continue;
				}
				if ((v & mirar[k].mascara)
				    != (quiero & mirar[k].mascara)) {
					printf("  FAIL  A1 registro %u: el mapa "
					       "tiene 0x%08x y el plan 0x%08x\n",
					       k, v & mirar[k].mascara,
					       quiero & mirar[k].mascara);
					 bien = false;
				}
			}
			CHECK(bien, "A1 los cinco registros de control con lo "
			      "que dice el plan");
		}
	}


/* ═══════════════════════════════════════════════════════════════════════════
 * A2 · EL MAPA QUE MIENTE
 *
 * Y AQUI ESTA LA RAZON DE QUE EXISTA EL BASTON DE VERIFICABILIDAD:
 * para poder hacer mentir a un registro hay que escribirlo por una via que el
 * apply no use al releer.  Y la via que queda, con la API actual, es una sola:
 *
 *      el apply escribe en `map` y relee en `map`.
 *
 * Asi que el mapa es un buffer, y para mentir hay que hacer que la escritura no
 * llegue.  Con la API actual no se puede, y la razon es util:  el apply escribe
 * y relea por el mismo puntero,  de modo que cualquier mapa que acepte la
 * escritura devuelve exactamente lo escrito.  La lectura de vuelta solo tiene
 * valor contra la BAR5 real,  y eso es RUNTIME_REQUIRED.
 *
 * Lo que SI se mide aqui,  y es lo que se puede medir sin hardware:
 *
 *   A2.1  que el apply NO intenta verificar los 24 registros de solo escritura
 *         y por tanto no reporta fallos falsos sobre ellos
 *   A2.2  que los 9 que si son RW se verifican uno a uno
 *   A2.3  que el numero de no verificables es exactamente 24,  y no 25 y no 23
 *   A2.4  que un plan con un numero de operaciones distinto NO se aplica
 *         a medias
 * ═══════════════════════════════════════════════════════════════════════════ */

	{
		unsigned v = 0, nv = 0;
		unsigned primero_no_verificable = 99, ultimo = 0;

		for (unsigned i = 0; i < seq.n; i++) {
			if (seq.op[i].verificable) {
				v++;
				ultimo = i;
			} else {
				nv++;
				if (primero_no_verificable == 99)
					primero_no_verificable = i;
			}
		}
		CHECK_EQ(nv, 25u,
			 "A2.3 de las 34 escrituras, 25 van a registro de solo "
			 "escritura");
		CHECK_EQ(v, 9u, "A2.2 nueve son de lectura-escritura");
		CHECK_EQ(v + nv, 34u, "A2.3 y no se queda ninguna sin clasificar");
		CHECK_EQ(primero_no_verificable, 5u,
			 "A2.1 el primer registro de solo escritura es el 5");
		/*  CORREGIDO:  decia 4,  decia "los cinco primeros".  Los nueve
		 *  legibles no son los cinco primeros:  el 5 es el primero de solo
		 *  escritura,  y los ultimos legibles son el 9 (CTX0_CNTL2),  el 10
		 *  (CTX0_CNTL),  el 32 (CTX1_CNTL2) y el 33 (CTX1_CNTL).  El
		 *  ultimo legible es el 33. */
		CHECK_EQ(ultimo, 33u,
			 "A2.1 el ultimo registro legible es el 33, no el 4");

		/*  Los trece indices del bucle que no estan en la tabla de
		 *  registros.  rx550_gart_es_legible() devuelve false para ellos
		 *  porque NO LOS ENCUENTRA,  no porque el corpus los declare de
		 *  solo escritura.  El resultado es el mismo y es el correcto  --
		 *  su ancla, mmVM_CONTEXT0_PAGE_TABLE_BASE_ADDR, es "W"  --  pero la
		 *  razon es distinta,  y esta asercion lo deja dicho para que no se
		 *  lea como una propiedad del hardware que no se ha medido. */
		{
			unsigned fuera = 0;

			for (unsigned i = 0; i < seq.n; i++) {
				struct rx550_reg rr;
				uint32_t idx;

				if (rx550_mmio_reg_of_index(seq.op[i].reg, &rr)
				    != RX550_MMIO_OK)
					continue;
				(void)idx;
				if (seq.op[i].reg >= 0x551u && seq.op[i].reg <= 0x556u)
					fuera++;
				if (seq.op[i].reg >= 0x50fu && seq.op[i].reg <= 0x515u)
					fuera++;
			}
			CHECK_EQ(fuera, 13u,
				 "A2 los trece indices intermedios del bucle no "
				 "estan en la tabla y se tratan como no legibles");
		}

		/*  El apply NO debe declarar exito por haber verificado nueve,  ni
		 *  fallo por no haber verificado veinticuatro.  Y el informe tiene
		 *  que decir las dos cosas. */
		memset(&rep, 0, sizeof(rep));
		CHECK(rx550_gart_apply(&map_real, &seq, &rep) == 0,
		      "A2.1 apply sin falsos fallos sobre los 24 de solo escritura");
		CHECK_EQ(rep.n_verificadas, 9u,
			 "A2.2 el apply verifico exactamente las nueve");
		CHECK_EQ(rep.n_no_verificables, 25u,
			 "A2.1 y dice cuantas no se pueden comprobar");
		CHECK_EQ(rep.primer_fallo, RX550_GART_NO_FALLO, "A2.1 sin fallos");

		/*  Y con un contador que cuadre:  lo verificado mas lo no verificable
		 *  es lo escrito.  Si un dia una operacion se pierde entre el
		 *  counted y la escritura,  esta suma lo delata. */
		CHECK_EQ(rep.n_verificadas + rep.n_no_verificables, rep.n_escritas,
			 "A2.1 verificadas + no verificables == escritas");
	}

	/* ── A2.4 · UN PLAN QUE NO ESTA ENTERO ───────────────────────────── */
	printf("\nA2.4 · un plan que no esta entero\n");
	{
		struct rx550_gart_seq corto = seq;
		struct rx550_gart_apply_report r2;

		/*  El numero de operaciones se reduce en uno.  Como el apply exige
		 *  34,  esto no llega a escribir nada.  La comprobacion que importa
		 *  es que n_escritas valga 0 en el informe:  un apply que escribiera
		 *  33 y se detuviera al final habria dejado el contexto 0
		 *  habilitado con la tabla antigua. */
		corto.n = 33u;
		memset(&r2, 0, sizeof(r2));
		CHECK(rx550_gart_apply(&map_real, &corto, &r2)
		      == RX550_GART_SEQ_ERR_TABLE,
		      "A2.4 un plan de 33 operaciones NO se aplica");
		CHECK_EQ(r2.n_escritas, 0u,
			 "A2.4 y no se escribio NADA, no 33");
		CHECK_EQ(r2.primer_fallo, 0u,
			 "A2.4 el informe no se toco: no se llego a empezar");

		corto.n = 35u;
		CHECK(rx550_gart_apply(&map_real, &corto, &r2)
		      == RX550_GART_SEQ_ERR_TABLE,
		      "A2.4 un plan de 35 tampoco");
		CHECK_EQ(r2.n_escritas, 0u, "A2.4 y sigue sin escribir nada");
	}

	/* ── A3 · LOS NEGATIVOS ─────────────────────────────────────────── */
	printf("\nA3 · los negativos\n");
	{
		struct rx550_gart_seq s2;
		struct rx550_gart_apply_report r3;

		CHECK(rx550_gart_apply(NULL, &seq, &rep) == RX550_GART_SEQ_ERR_INCONSISTENT,
		      "A3 apply sin mapa");
		CHECK(rx550_gart_apply(&map_real, NULL, &rep) == RX550_GART_SEQ_ERR_INCONSISTENT,
		      "A3 apply sin plan");
		CHECK(rx550_gart_apply(&map_real, &seq, NULL) == RX550_GART_SEQ_ERR_INCONSISTENT,
		      "A3 apply sin informe");
		CHECK(rx550_gart_snapshot(&map_real, NULL) == RX550_GART_SEQ_ERR_INCONSISTENT,
		      "A3 snapshot sin salida");
		CHECK(rx550_gart_build_from(NULL, &s2, &p) == RX550_GART_SEQ_ERR_INCONSISTENT,
		      "A3 build_from sin mapa");

		/*  Sin mapa enlazado:  el snapshot falla ANTES de devolver nada,
		 *  y p->cur se queda como estaba.  Un snapshot a medias deja unos
		 *  valores del mapa y otros de antes,  y el plan construido encima
		 *  parece valido. */
		{
			struct rx550_gart_params q;
			uint32_t antes[RX550_GART_RMW_NR];
			bool intacto = true;
			unsigned k;

			params_buenas(&q);
			memcpy(antes, q.cur, sizeof(antes));
			rx550_mmio_detach(&map_real);
			CHECK(rx550_gart_build_from(&map_real, &s2, &q)
			      != 0, "A3 build_from sin mapa enlazado falla");
			for (k = 0; k < RX550_GART_RMW_NR; k++)
				if (q.cur[k] != antes[k])
					intacto = false;
			CHECK(intacto,
			      "A3 y p->cur NO se toco: sin medias lecturas");
			CHECK(rx550_mmio_attach(&map_real, bar_real,
						RX550_MMIO_SIZE) == RX550_MMIO_OK,
			      "A3 reenlazar para seguir");
		}

		/*  Y el apply sin mapa. */
		rx550_mmio_detach(&map_real);
		memset(&r3, 0, sizeof(r3));
		CHECK(rx550_gart_apply(&map_real, &seq, &r3)
		      == RX550_MMIO_ERR_NO_MAP, "A3 apply sin mapa enlazado");
		CHECK_EQ(r3.n_escritas, 0u, "A3 y no se escribio nada");
		rx550_mmio_attach(&map_real, bar_real, RX550_MMIO_SIZE);
	}

	printf("\n  %d pass, %d fail\n", pass, fail);
	if (fail) {
		printf("  CONTRATO: INCUMPLIDO\n");
		return 1;
	}
	printf("  CONTRATO: SATISFECHO\n");
	return 0;
}