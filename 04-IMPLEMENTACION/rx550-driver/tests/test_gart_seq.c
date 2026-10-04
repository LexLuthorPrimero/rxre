/* SPDX-License-Identifier: GPL-2.0-only */
/*
 * test_gart_seq.c — el plan de las 34 escrituras que programa el GART.
 *
 *   TARGET = RX 550 instalada en esta maquina  (1002:699F, Polaris12, GFX8)
 *   SCOPE  = EXCLUSIVO
 *
 * QUE ES Y QUE NO ES
 *   C puro, unitario, en userspace.  No hay mapa, no hay hardware, y por eso
 *   esta es LA suite que puede comprobar la funcion mas critica del componente.
 *   Una secuencia que se ejecuta directamente no se puede comparar con el
 *   corpus sin la GPU delante.
 *
 * LOS TRES BLOQUES
 *   S1  el plan contra el corpus:  las 34 operaciones, EN ORDEN, con el valor
 *       que la referencia escribe.  Comparado con gmc_v8_0.c:829-946.
 *   S2  la geometria entra bien:  los valores de ESTA tarjeta, y las
 *       relaciones entre ellos que tienen que cumplirse.
 *   S3  los negativos:  geometria incoherente, direcciones de mas de 40 bits,
 *       block_size fuera de rango, y que un error NO devuelva un plan a medias.
 *
 * QUE NO COMPRUEBA
 *   Que el hardware acepte la secuencia.  Eso es RUNTIME_REQUIRED, y es la
 *   unica cosa que este test no puede decir.
 */
#include <stdio.h>
#include <stdlib.h>
#include <string.h>
#include <stdint.h>
#include <stdbool.h>

#include "rx550_gart_seq.h"
#include "rx550_mmio_access.h"

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

/* ── LOS PARAMETROS DE ESTA TARJETA ──────────────────────────────────────
 *
 *  Todos medidos, ninguno inventado:
 *    gart_start/gart_end   del log del kernel, finding 1027
 *    block_size = 10       "block size is 10-bit", mismo log
 *    fragment_size = 9     "fragment size is 9-bit"
 *    max_pfn               amdgpu_vm_adjust_size(adev, 64, 9, 1, 40) y el
 *                          "vm size is 64 GB" del log:  64 GiB >> 12
 *    table_addr            la tabla del GART, 0xf400900000 del log
 *    dummy_page_addr       cualquiera dentro de 40 bits;  el valor no
 *                          importa para el plan, solo que quepa
 */
#define P_GART_START	UINT64_C(0xFF00000000)
#define P_GART_END	UINT64_C(0xFF0FFFFFFF)
#define P_TABLE_ADDR	UINT64_C(0xF400900000)
#define P_DUMMY_PA	UINT64_C(0x0000000123456000)
#define P_MAX_PFN	(UINT64_C(64) << 18)	/* 64 GiB en paginas */
#define P_BLOCK		10u
#define P_FRAGMENT	9u

static void params_buenas(struct rx550_gart_params *p)
{
	memset(p, 0, sizeof(*p));
	p->gart_start = P_GART_START;
	p->gart_end = P_GART_END;
	p->table_addr = P_TABLE_ADDR;
	p->dummy_page_addr = P_DUMMY_PA;
	p->max_pfn = P_MAX_PFN;
	p->block_size = P_BLOCK;
	p->fragment_size = P_FRAGMENT;
	/* El valor actual de los 7 registros RMW.  Se pone ALGO DISTINTO DE CERO
	 * a proposito:  si el plan solo conservase lo que hay, no se podria
	 * distinguir "conserva" de "pone a cero".  Con estos valores, un plan
	 * que componga mal se ve en el numero final. */
	p->cur[RX550_GART_RMW_L1_TLB_CNTL] = 0xdeadf00du;
	p->cur[RX550_GART_RMW_L2_CNTL] = 0x0badc0deu;
	p->cur[RX550_GART_RMW_L2_CNTL2] = 0xfeed0000u;
	p->cur[RX550_GART_RMW_L2_CNTL3] = 0x00c0ffeeu;
	p->cur[RX550_GART_RMW_L2_CNTL4] = 0xffffffffu;
	/*  Los dos CNTL arrancan con los bits de PAGE_TABLE_DEPTH PUESTOS y en
	 *  un valor que NO es el que va a escribir la referencia.
	 *
	 *  CORREGIDO:  arrancaban los dos a 0x....0000,  y los bits 1 y 2 de PAGE_
	 *  TABLE_DEPTH ya valian 0.  Con esa semilla, "poner PAGE_TABLE_DEPTH=0"
	 *  y "no tocar PAGE_TABLE_DEPTH" dan el MISMO numero,  y una mutacion que
	 *  quitase esa asignacion pasaba verde.  Se vio en el self-test:  al quitar
	 *  el apply_field de ese campo,  0 de 55 comprobaciones fallaron.
	 *
	 *  El contexto 0 lleva 3 (0b11) y el contexto 1 lleva 2 (0b10):  ninguno es
	 *  el valor que la referencia escribe (0 y 1 respectivamente),  asi que los
	 *  dos tienen que MOVerse y un "conservado" se ve. */
	p->cur[RX550_GART_RMW_CTX0_CNTL] = 0xaaaa0006u;
	p->cur[RX550_GART_RMW_CTX1_CNTL] = 0xbbbb0004u;
}

/* El indice que la referencia escribe, por mnemonico. */
static bool idx_de(const char *mnemo, uint32_t *out)
{
	for (uint32_t i = 0; i < rx550_vmid1_reg_count; i++) {
		if (strcmp(rx550_vmid1_regs[i].name, mnemo) == 0) {
			*out = rx550_vmid1_regs[i].index;
			return true;
		}
	}
	return false;
}

static uint32_t idx(const char *m)
{
	uint32_t v = 0;

	if (!idx_de(m, &v)) {
		printf("  FAIL  el plan usa '%s', que no esta en la tabla\n", m);
		fail++;
		return 0;
	}
	return v;
}

int main(void)
{
	struct rx550_gart_seq s;
	struct rx550_gart_params p;

	printf("test_gart_seq — el plan del GART\n\n");

	params_buenas(&p);
	memset(&s, 0xff, sizeof(s));
	CHECK(rx550_gart_seq_build(&s, &p) == 0, "S1 build");
	CHECK_EQ(rx550_gart_seq_len(&s), 34, "S1 son 34 escrituras");
	CHECK_EQ(s.n, RX550_GART_OPS_NR, "S1 y el plan cabe en su array");

	/*  Todo lo que sigue INDEXA el plan,  y lo hace suponiendo que hay 34.
	 *  Si el constructor devolviera un plan corto,  esas comprobaciones
	 *  leerian basura:  el `memset` de 0xff de arriba deja el array entero en
	 *  0xffffffff,  asi que los indices sueltos darian "fail" por casualidad.
	 *
	 *  Y en una mutacion del self-test eso no fue un fallo sino un SEGV:  el
	 *  plan se emitio con 19 operaciones y el recorrido del bucle llego a un
	 *  indice que no existia.  Un test que aborta con SIGSEGV en vez de
	 *  fallar con un mensaje es peor que no tener el test:  no dice que se ha
	 *  roto,  y se lleva por delante el resto de la suite. */
	if (s.n != RX550_GART_OPS_NR) {
		printf("  FAIL  S1 el plan tiene %u operaciones y todo lo de abajo "
		       "las indexa:  se para aqui para no leer fuera\n", s.n);
		fail++;
		goto resumen;
	}

	/* ── S1 · LA SECUENCIA, UNA A UNA Y EN ORDEN ──────────────────────── */
	printf("\nS1 · la secuencia contra gmc_v8_0.c:829-946\n");
	{
		static const struct { const char *reg; unsigned op; } ESPERADO[] = {
			{ "mmMC_VM_MX_L1_TLB_CNTL",                   0  }, /* L849 */
			{ "mmVM_L2_CNTL",                             1  }, /* L859 */
			{ "mmVM_L2_CNTL2",                            2  }, /* L863 */
			{ "mmVM_L2_CNTL3",                            3  }, /* L870 */
			{ "mmVM_L2_CNTL4",                            4  }, /* L885 */
			{ "mmVM_CONTEXT0_PAGE_TABLE_START_ADDR",      5  }, /* L887 */
			{ "mmVM_CONTEXT0_PAGE_TABLE_END_ADDR",        6  }, /* L888 */
			{ "mmVM_CONTEXT0_PAGE_TABLE_BASE_ADDR",       7  }, /* L889 */
			{ "mmVM_CONTEXT0_PROTECTION_FAULT_DEFAULT_ADDR", 8  }, /* L890 */
			{ "mmVM_CONTEXT0_CNTL2",                      9  }, /* L892 */
			{ "mmVM_CONTEXT0_CNTL",                       10  }, /* L897 */
			{ "mmVM_L2_CONTEXT1_IDENTITY_APERTURE_LOW_ADDR", 11  }, /* L899 */
			{ "mmVM_L2_CONTEXT1_IDENTITY_APERTURE_HIGH_ADDR", 12  }, /* L900 */
			{ "mmVM_L2_CONTEXT_IDENTITY_PHYSICAL_OFFSET", 13  }, /* L901 */
			{ "mmVM_CONTEXT1_PAGE_TABLE_START_ADDR",      14  }, /* L908 */
			{ "mmVM_CONTEXT1_PAGE_TABLE_END_ADDR",        15  }, /* L909 */
			/* L910: los 15 del bucle, del 16 al 30 */
			{ "mmVM_CONTEXT1_PROTECTION_FAULT_DEFAULT_ADDR", 31  }, /* L920 */
			{ "mmVM_CONTEXT1_CNTL2",                      32  }, /* L922 */
			{ "mmVM_CONTEXT1_CNTL",                       33  }, /* L935 */
		};
		bool bien = true;

		for (size_t i = 0; i < sizeof(ESPERADO) / sizeof(ESPERADO[0]); i++) {
			if (s.op[ESPERADO[i].op].reg != idx(ESPERADO[i].reg)) {
				printf("  FAIL  op %u: esperado %s (0x%03x), "
				       "obtenido 0x%03x\n",
				       ESPERADO[i].op, ESPERADO[i].reg,
				       idx(ESPERADO[i].reg), s.op[ESPERADO[i].op].reg);
				bien = false;
			}
		}
		CHECK(bien, "S1 las 19 escrituras explicitas, en su registro y su orden");
	}

	/* Los 15 del bucle, y aqui es donde el corte en 8 se nota. */
	{
		bool bien = true;

		for (unsigned vmid = 1; vmid < 16; vmid++) {
			uint32_t e = rx550_mmio_ctx_pt_base_index(vmid);
			uint32_t g = s.op[15 + vmid].reg;

			if (g != e) {
				printf("  FAIL  bucle vmid %u: esperado 0x%03x, "
				       "obtenido 0x%03x\n", vmid, e, g);
				bien = false;
			}
		}
		CHECK(bien, "S1 los 15 del bucle salen de la regla, con corte en 8");
		/* Y los dos bloques, explicito:  el segundo esta POR DEBAJO. */
		/*  CORREGIDO.  Este vector pedia 0x54f, que es el ancla del
		 *  CONTEXTO 0, no la del contexto 1.  La regla es
		 *      gmc_v8_0.c:913  mmVM_CONTEXT0_PAGE_TABLE_BASE_ADDR + i
		 *  y ese ancla es 0x54f,  o sea que el contexto 1 esta en 0x550.
		 *  La comprobacion de arriba contra rx550_mmio_ctx_pt_base_index()
		 *  ya lo decia bien;  este vector de mas era el que estaba mal, y
		 *  los dos juntos se contradecen. */
		CHECK(s.op[16].reg == 0x550, "S1 bucle vmid 1 -> 0x550 (CTX0_BASE+1)");
		CHECK(s.op[23].reg == 0x50e, "S1 bucle vmid 8 -> 0x50e, POR DEBAJO");
		CHECK(s.op[23].reg < s.op[22].reg,
		      "S1 el bloque 8..15 esta por debajo del 0..7");
		CHECK(s.op[30].reg == 0x515, "S1 bucle vmid 15 -> 0x515");
	}

	/* ── LOS VALORES ──────────────────────────────────────────────────── */
	printf("\nS1 · los valores\n");
	{
		uint32_t table_pfn = (uint32_t)(P_TABLE_ADDR >> 12);
		uint32_t dummy_pfn = (uint32_t)(P_DUMMY_PA >> 12);

		CHECK_EQ(s.op[5].value, (uint32_t)(P_GART_START >> 12),
			 "S1 CTX0_PT_START = gart_start >> 12");
		CHECK_EQ(s.op[6].value, (uint32_t)(P_GART_END >> 12),
			 "S1 CTX0_PT_END   = gart_end >> 12");
		CHECK_EQ(s.op[7].value, table_pfn,
			 "S1 CTX0_PT_BASE  = table_addr >> 12");
		CHECK_EQ(s.op[8].value, dummy_pfn,
			 "S1 CTX0_PROT_FAULT = dummy >> 12");
		CHECK_EQ(s.op[9].value, 0, "S1 CTX0_CNTL2 = literal 0");
		/*  Y el del contexto 1 es un CUATRO,  no un cero:  gmc_v8_0.c:923.
		 *  Este vector no existia,  y un 0 ahi habria pasado inadvertido
		 *  porque al lado hay un 0 legitimo en CTX0_CNTL2. */
		CHECK_EQ(s.op[32].value, 4, "S1 CTX1_CNTL2 = literal 4, NO un 0");
		CHECK_EQ(s.op[11].value, 0, "S1 identity aperture LOW = 0");
		CHECK_EQ(s.op[12].value, 0, "S1 identity aperture HIGH = 0");
		CHECK_EQ(s.op[13].value, 0, "S1 IDENTITY_PHYSICAL_OFFSET = 0");
		CHECK_EQ(s.op[14].value, 0, "S1 CTX1_PT_START = 0");
		CHECK_EQ(s.op[15].value, (uint32_t)(P_MAX_PFN - 1),
			 "S1 CTX1_PT_END = max_pfn - 1");

		/* Y los quince del bucle llevan la MISMA tabla que el contexto 0. */
		bool bien = true;

		for (unsigned vmid = 1; vmid < 16; vmid++)
			if (s.op[15 + vmid].value != table_pfn)
				 bien = false;
		CHECK(bien, "S1 los 15 del bucle llevan table_addr >> 12");
		CHECK_EQ(s.op[31].value, dummy_pfn,
			 "S1 CTX1_PROT_FAULT = dummy >> 12, el MISMO que el ctx0");
	}

	/* ── LOS RMW:  conserva lo que no nombra ───────────────────────────── */
	printf("\nS1 · los RMW conservan lo que no nombran\n");
	{
		/* mmVM_CONTEXT0_CNTL: 22 campos, la referencia pone 3.  Los otros 19
		 * tienen que seguir como estaban. */
		uint32_t Depth = 0x6u, Enable = 0x1u, RangePF = 0x10u;
		uint32_t otros = ~(Depth | Enable | RangePF);

		CHECK_EQ(s.op[10].value & otros, p.cur[RX550_GART_RMW_CTX0_CNTL] & otros,
			 "S1 CTX0_CNTL conserva los 19 campos que no toca");
		CHECK_EQ(s.op[10].value & Enable, Enable, "S1 CTX0_CNTL ENABLE_CONTEXT=1");
		CHECK_EQ(s.op[10].value & Depth, 0, "S1 CTX0_CNTL PAGE_TABLE_DEPTH=0");
		CHECK_EQ(s.op[10].value & RangePF, RangePF,
			 "S1 CTX0_CNTL RANGE_PROT_FAULT_ENABLE_DEFAULT=1");

		/* mmVM_CONTEXT1_CNTL: 22 declarados, 10 escritos.  PAGE_TABLE_BLOCK_SIZE
		 * va a block_size - 9, y ahi es 10 - 9 = 1. */
		uint32_t Bs = 0xf000000u;

		CHECK_EQ((s.op[33].value & Bs) >> 24, P_BLOCK - 9,
			 "S1 CTX1_CNTL PAGE_TABLE_BLOCK_SIZE = block_size - 9");
		/*  CORREGIDO.  Pedia 0x6, que es el VALOR 3 (0b11).  El corpus
		 *  pone 1,  y el valor 1 en un campo de dos bits es 0b01, que
		 *  desplazado al bit 1 ocupa 0b100 == 0x4...  no:  el campo esta en
		 *  los bits 1 y 2,  y el valor 1 pone el bit 1 a 1 y el 2 a 0:
		 *  0b010 == 0x2.  Es el mismo desplazamiento queacia mal en el
		 *  test_update_field,  con el otro valor. */
		CHECK_EQ(s.op[33].value & Depth, 0x2, "S1 CTX1_CNTL PAGE_TABLE_DEPTH=1");

		/*  Y el bloque entero de L2_CNTL4.  CORREGIDO:  este vector pedia
		 *  el registro entero a cero, y no es eso.  La referencia pone sus
		 *  DOCE VMC_TAP a cero y PRESERVA todo lo demas del registro, que
		 *  es justo lo que hace el RREG32.  El valor de partida era
		 *  0xffffffff precisamente para poder distinguir "conserva" de
		 *  "pone a cero", y el vector hacia exactamente eso mal. */
		{
			uint32_t taps = 0;

			for (unsigned b = 6; b <= 17; b++)
				taps |= 1u << b;
			CHECK_EQ(s.op[4].value & taps, 0u,
				 "S1 L2_CNTL4: los doce VMC_TAP a cero");
			CHECK_EQ(s.op[4].value & ~taps,
				 p.cur[RX550_GART_RMW_L2_CNTL4] & ~taps,
				 "S1 L2_CNTL4: los bits de fuera de los taps, intactos");
			CHECK_EQ(taps, 0x3FFC0u,
				 "S1 la mascara de los doce taps, calculada aparte");
		}

		/* Y uno que la referencia escribe entero:  L2_CNTL3 toma el
		 * fragment_size en BANK_SELECT y en BIGK_FRAGMENT_SIZE. */
		CHECK_EQ(s.op[3].value & 0x3fu, P_FRAGMENT,
			 "S1 L2_CNTL3 BANK_SELECT = fragment_size");
		CHECK_EQ((s.op[3].value & 0xf8000u) >> 15, P_FRAGMENT,
			 "S1 L2_CNTL3 BIGK_FRAGMENT_SIZE = fragment_size");
	}

	/* ── S2 · QUE EL PLAN CAMBIA CON LA GEOMETRIA ─────────────────────── */
	printf("\nS2 · el plan responde a la geometria\n");
	{
		struct rx550_gart_seq s2;
		struct rx550_gart_params q = p;

		/*  CORREGIDO.  Desplazaba solo gart_start,  con lo que la ventana
		 *  se invertia y el build devolvia error de geometria:  el fallo se
		 *  leia como "el plan no responde a la geometria" cuando lo que
		 *  habia era un vector mal hecho.  La ventana se mueve entera. */
		/*  +1 GiB, y no +8.  CORREGIDO:  la ventana real del GART esta en
		 *  0xFF00000000,  que esta a unos 4 GiB del tope de los 40 bits del
		 *  PHYSICAL_PAGE_NUMBER,  y +8 GiB la saca de rango:
		 *      0xFF00000000 + 0x200000000 = 0x10100000000  >  2^40
		 *  El constructor lo rechazaba con error de geometria,  y el fallo se
		 *  leia como "el plan no responde a la geometria".  Lo que de verdad
		 *  demuestra este vector es una restriccion que no estaba escrita:
		 *  la ventana del GART NO se puede mover arriba de 0xFFC0000000. */
		q.gart_start += 0x40000000ull;	/* +1 GiB */
		q.gart_end   += 0x40000000ull;
		CHECK(rx550_gart_seq_build(&s2, &q) == 0, "S2 build con otra ventana");
		CHECK_EQ(s2.op[5].value, (uint32_t)((p.gart_start + 0x40000000ull) >> 12),
			 "S2 START sigue a gart_start");
		/*  CORREGIDO:  decia "END no se mueve".  Se escribio para el
		 *  vector que desplazaba solo el inicio,  que era el vector erroneo:
		 *  si solo se mueve el inicio,  lo que hay que comprobar es que el
		 *  final se queda,  y con la ventana entera moviendose lo que tiene
		 *  que comprobar es que el final LA SIGUE.  Con el vector viejo,  esta
		 *  comprobacion pasaba por el motivo equivocado. */
		CHECK_EQ(s2.op[6].value, (uint32_t)((p.gart_end + 0x40000000ull) >> 12),
			 "S2 END sigue a la ventana entera");
		CHECK_EQ(s2.n, s.n, "S2 y el numero de operaciones no cambia");

		q = p;
		q.block_size = 9;			/* la referencia haria 9 - 9 = 0 */
		CHECK(rx550_gart_seq_build(&s2, &q) == 0, "S2 build con block_size 9");
		CHECK_EQ((s2.op[33].value & 0xf000000u) >> 24, 0,
			 "S2 BLOCK_SIZE = block_size - 9, y 9 - 9 = 0");

		q = p;
		q.fragment_size = 11;
		CHECK(rx550_gart_seq_build(&s2, &q) == 0, "S2 build con fragment 11");
		CHECK_EQ(s2.op[3].value & 0x3fu, 11, "S2 BANK_SELECT sigue al fragment");
	}

	/* ── S3 · LOS NEGATIVOS, Y QUE NO DEVUELVAN UN PLAN A MEDIAS ───────── */
	printf("\nS3 · los negativos\n");
	{
		struct rx550_gart_seq mala;
		struct rx550_gart_params q;

		/* Un plan ENVENENADO: si un error lo devolviera tal cual, el test de
		 * "no hay plan a medias" no valdria nada, porque el plan seria
		 * indistinguible de uno bueno. */
		memset(&mala, 0xa5, sizeof(mala));

		CHECK(rx550_gart_seq_build(NULL, &p) == RX550_GART_SEQ_ERR_INCONSISTENT,
		      "S3 sin destino");
		CHECK(rx550_gart_seq_build(&mala, NULL) == RX550_GART_SEQ_ERR_INCONSISTENT,
		      "S3 sin parametros");
		CHECK_EQ(mala.n, 0xa5a5a5a5u & 0xffffffffu,
			 "S3 y el plan del llamante NO se toco");

		q = p;
		q.gart_start = q.gart_end + 1;
		CHECK(rx550_gart_seq_build(&mala, &q) == RX550_GART_SEQ_ERR_GEOMETRY,
		      "S3 gart_start > gart_end");
		/*  CORREGIDO.  Decia !=,  y lo que hay que comprobar es que el
		 *  destino sigue ENVENENADO:  si el error escribiera algo, el test
		 *  de "no hay plan a medias" no distinguiria nada.  Al reves, el
		 *  test pasaba por el motivo equivocado. */
		CHECK_EQ(mala.n, 0xa5a5a5a5u, "S3 y el destino sigue sin tocar");

		q = p;
		q.table_addr = UINT64_C(1) << 41;		/* mas de 40 bits */
		CHECK(rx550_gart_seq_build(&mala, &q) == RX550_GART_SEQ_ERR_GEOMETRY,
		      "S3 table_addr de mas de 40 bits");
		q = p;
		q.dummy_page_addr = UINT64_C(1) << 41;
		CHECK(rx550_gart_seq_build(&mala, &q) == RX550_GART_SEQ_ERR_GEOMETRY,
		      "S3 dummy_page_addr de mas de 40 bits");

		/* 2^40 exacto:  el >> 12 da 2^28, y el campo es de 28 bits, asi que
		 * el desplazamiento NO lo delata.  Solo lo delata comprobar antes. */
		q = p;
		q.table_addr = UINT64_C(1) << 40;
		CHECK(rx550_gart_seq_build(&mala, &q) == RX550_GART_SEQ_ERR_GEOMETRY,
		      "S3 table_addr exactamente 2^40, que el >>12 no delata");

		q = p;
		q.block_size = 16;				/* el campo es de 4 bits */
		CHECK(rx550_gart_seq_build(&mala, &q) == RX550_GART_SEQ_ERR_GEOMETRY,
		      "S3 block_size 16, y el campo es de 4");
		q = p;
		q.fragment_size = 16;
		CHECK(rx550_gart_seq_build(&mala, &q) == RX550_GART_SEQ_ERR_GEOMETRY,
		      "S3 fragment_size 16");

		/*  CORREGIDO.  Este bloque comprobaba que "la ventana del GART no
		 *  cabe en max_pfn",  que era una comprobacion INVENTADA:  no
		 *  existe en el corpus y no puede existir,  porque las ventanas
		 *  del contexto 0 y del contexto 1 son independientes y en esta
		 *  tarjeta no se anidan.
		 *      ventana del GART >> 12  =  267452415
		 *      ventana del VM          =   16777216
		 *  Es decir que la condicion que se comprobaba era CIERTA con la
		 *  geometria real,  y el constructor rechazaba la tarjeta.
		 *  Lo que se comprueba ahora es lo unico medido:  que el campo de
		 *  28 bits del PAGE_TABLE_END del contexto 1 quepa. */
		q = p;
		q.max_pfn = 0;
		CHECK(rx550_gart_seq_build(&mala, &q) == RX550_GART_SEQ_ERR_GEOMETRY,
		      "S3 max_pfn cero:  max_pfn - 1 no existe");
		q = p;
		q.max_pfn = 0x10000001ull;			/* 2^28 + 1: END = 2^28 */
		CHECK(rx550_gart_seq_build(&mala, &q) == RX550_GART_SEQ_ERR_GEOMETRY,
		      "S3 max_pfn cuyo END no cabe en 28 bits");
		q = p;
		q.max_pfn = 0x10000000ull;			/* END = 2^28 - 1, justo */
		CHECK(rx550_gart_seq_build(&mala, &q) == 0,
		      "S3 y con max_pfn justo SI cabe en los 28 bits");
	}

	/* Y rx550_gart_seq_len de un plan que no existe. */
	CHECK_EQ(rx550_gart_seq_len(NULL), 0, "S3 len de NULL");

resumen:
	printf("\n  %d pass, %d fail\n", pass, fail);
	if (fail) {
		printf("  CONTRATO: INCUMPLIDO\n");
		return 1;
	}
	printf("  CONTRATO: SATISFECHO\n");
	return 0;
}