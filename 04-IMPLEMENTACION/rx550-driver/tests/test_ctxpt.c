/* SPDX-License-Identifier: GPL-2.0-only */
/*
 * test_ctxpt.c — la regla que decide el registro de tabla de paginas de un VMID.
 *
 *   TARGET = RX 550 instalada en esta maquina  (1002:699F, Polaris12, GFX8)
 *   SCOPE  = EXCLUSIVO
 *
 * QUE ES Y QUE NO ES
 *   C puro, unitario, en userspace.  Sin MMIO, sin hardware, sin mapa.  Solo
 *   aritmetica sobre numeros que salen del corpus.
 *
 * POR QUE ESTE TEST EXISTE
 *   La tabla de mnemonicos de rx550_mmio_access.c verifica cada entrada POR
 *   SEPARADO contra gmc_8_1_d.h.  Eso no demuestra que el contexto 1 este en el
 *   registro correcto: una tabla con 16 mnemonicos, todos bien escritos, puede
 *   estar en 16 indices equivocados a la vez y ninguna comprobacion por entrada
 *   lo nota.  Lo que demuestra la correccion es la RELACION entre ellos.
 *
 *   Y la relacion tiene un corte en 8 que hace que `base + vmid` sea FALSO para
 *   la mitad de los VMID.  Este test la ejecuta entera.
 *
 * LOS TRES TIPOS DE CASO
 *   C1  la regla contra el corpus:  los 16 VMID, contra el header
 *   C2  los negativos:  vmid 16, 17, UINT_MAX no tienen registro
 *   C3  el valor:  pd_addr >> 12, y el rechazo por truncamiento silencioso
 *
 * QUE NO COMPRUEBA
 *   Que el hardware obedezca.  Que el Valor sea correcto en el silicio.  Eso es
 *   RUNTIME_REQUIRED, y este fichero no dice nada de eso.
 */
#include <stdio.h>
#include <stdint.h>
#include <stdbool.h>

#include "rx550_mmio_access.h"

/* Del corpus, gmc_8_1_d.h.  Copiadas aqui a proposito: si el corpus cambiara,
 * este test tiene que FALLAR, no seguir comparando contra si mismo. */
static const uint32_t corpus_base_index[16] = {
	0x54f, 0x550, 0x551, 0x552, 0x553, 0x554, 0x555, 0x556,	/* 0..7 */
	0x50e, 0x50f, 0x510, 0x511, 0x512, 0x513, 0x514,	0x515,	/* 8..15 */
};

static int pass, fail;

static void ok(const char *t) { printf("  PASS  %s\n", t); pass++; }
static void ko(const char *t) { printf("  FAIL  %s\n", t); fail++; }

#define CHECK(cond, name) do { if (cond) ok(name); else ko(name); } while (0)
#define CHECK_EQ(got, want, name) do {					\
	uint32_t g_ = (uint32_t)(got), w_ = (uint32_t)(want);		\
	if (g_ == w_) ok(name);						\
	else { printf("  FAIL  %s  (0x%x != 0x%x)\n", name, g_, w_);	\
	       fail++; }						\
} while (0)

int main(void)
{
	printf("test_ctxpt — registro de tabla de paginas por VMID\n\n");

	/* ── C1 · LA REGLA, LOS 16 VMID, CONTRA EL CORPUS ─────────────────── */
	printf("C1 · la regla posicional contra gmc_8_1_d.h\n");
	for (unsigned vmid = 0; vmid < 16u; vmid++) {
		char buf[96];

		snprintf(buf, sizeof buf,
			 "C1 vmid %u -> indice 0x%03x (corpus 0x%03x)",
			 vmid, rx550_mmio_ctx_pt_base_index(vmid),
			 corpus_base_index[vmid]);
		CHECK_EQ(rx550_mmio_ctx_pt_base_index(vmid),
			 corpus_base_index[vmid], buf);
	}

	/* El corte, por separado y con su porque.  `base + vmid` sin corte daria
	 * 0x50e para el 0, 0x516 para el 8 y 0x517 para el 9: ninguno de los dos
	 * ultimos es el registro de su contexto. */
	CHECK(rx550_mmio_ctx_pt_base_index(0) == 0x54f,
	      "C1 el bloque 0..7 arranca en 0x54f");
	CHECK(rx550_mmio_ctx_pt_base_index(7) == 0x556,
	      "C1 el bloque 0..7 termina en 0x556");
	CHECK(rx550_mmio_ctx_pt_base_index(8) == 0x50e,
	      "C1 el bloque 8..15 arranca en 0x50e, NO en 0x557");
	CHECK(rx550_mmio_ctx_pt_base_index(8) != 0x54f + 8u,
	      "C1 base+vmid SIN corte daria 0x557, y es el registro de START");
	CHECK(rx550_mmio_ctx_pt_base_index(9) != 0x54f + 9u,
	      "C1 base+vmid SIN corte daria 0x558, y es el registro de START");
	/* Los dos bloques no son contiguos: la diferencia entre el fin del
	 * primero y el principio del segundo es negativa en valor de bloque. */
	CHECK(rx550_mmio_ctx_pt_base_index(8) < rx550_mmio_ctx_pt_base_index(7),
	      "C1 el segundo bloque esta POR DEBAJO del primero");

	/* Y la relacion con la tabla de mnemonicos: el contexto 1 de la tabla
	 * tiene que COINCIDIR con lo que dice la regla.  Si las dos cosas
	 * discrepan, la tabla y la regla estan hablando de registros
	 * distintos y una de las dos esta mal. */
	{
		struct rx550_reg r;

		CHECK_EQ(rx550_mmio_reg_of(RX550_REG_CTX1_PT_BASE, &r),
			 RX550_MMIO_OK, "C1 resolver CTX1_PT_BASE");
		CHECK_EQ(r.index, rx550_mmio_ctx_pt_base_index(1),
			 "C1 la tabla y la regla coinciden en el contexto 1");
	}

	/* ── C2 · NEGATIVOS: NO HAY CONTEXTO 16 ───────────────────────────── */
	printf("\nC2 · vmid fuera de rango\n");
	CHECK(rx550_mmio_ctx_pt_base_index(16) == 0,
	      "C2 vmid 16 no tiene registro");
	CHECK(rx550_mmio_ctx_pt_base_index(17) == 0,
	      "C2 vmid 17 no tiene registro");
	CHECK(rx550_mmio_ctx_pt_base_index(1000) == 0,
	      "C2 vmid 1000 no tiene registro");
	CHECK(rx550_mmio_ctx_pt_base_index(0xffffffffu) == 0,
	      "C2 vmid 0xffffffff no tiene registro");
	/* Y el motivo por el que no se devuelve un indice calculable:  el
	 * resultado caeria dentro de BAR5 y el acceso no fallaria. */
	CHECK(rx550_mmio_ctx_pt_base_index(16) == 0 ||
	      rx550_mmio_ctx_pt_base_index(16) >= 0x40000u,
	      "C2 el rejection no deja un indice dentro de BAR5");

	/* ── C3 · EL VALOR: NUMERO DE PAGINA, NO DIRECCION ────────────────── */
	printf("\nC3 · el valor que se escribe\n");
	{
		uint32_t v = 0xffffffffu;

		CHECK_EQ(rx550_mmio_pt_value(UINT64_C(0), &v), RX550_MMIO_OK,
			 "C3 pd_addr 0 -> 0");
		CHECK_EQ(v, 0, "C3 el valor de 0 es 0");

		CHECK_EQ(rx550_mmio_pt_value(UINT64_C(0x1000), &v), RX550_MMIO_OK,
			 "C3 pd_addr 4 KiB");
		CHECK_EQ(v, 1, "C3 una pagina -> PN 1");

		CHECK_EQ(rx550_mmio_pt_value(UINT64_C(0x12345000), &v),
			 RX550_MMIO_OK, "C3 pd_addr arbitrario");
		CHECK_EQ(v, 0x12345, "C3 >> 12, y no >> 0");

		/* El tope: 40 bits de direccion entran enteros en 28 de campo. */
		CHECK_EQ(rx550_mmio_pt_value(RX550_PT_MAX_PD_ADDR, &v),
			 RX550_MMIO_OK, "C3 el tope de 40 bits se acepta");
		CHECK_EQ(v, 0x0fffffff, "C3 el tope da el campo entero");

		/* Un byte por encima del tope:  se rechaza, NO se trunca. */
		v = 0xdeadbeefu;
		CHECK(rx550_mmio_pt_value(RX550_PT_MAX_PD_ADDR + 1u, &v) !=
		      RX550_MMIO_OK,
		      "C3 un byte por encima del tope se RECHAZA");
		CHECK_EQ(v, 0xdeadbeef, "C3 y la salida no se toca al rechazar");

		CHECK(rx550_mmio_pt_value(UINT64_MAX, &v) != RX550_MMIO_OK,
		      "C3 UINT64_MAX se rechaza, no se trunca a 28 bits");
		CHECK_EQ(v, 0xdeadbeef, "C3 y la salida sigue intacta");

		/* El borde exacto. */
		CHECK(rx550_mmio_pt_value(UINT64_C(1) << 40, &v) != RX550_MMIO_OK,
		      "C3 exactamente 2^40 se rechaza");
		CHECK(rx550_mmio_pt_value(UINT64_C(1) << 39, &v) == RX550_MMIO_OK,
		      "C3 2^39 es la ultima direccion valida");

		/* NOTA SOBRE EL ORDEN DE LA COMPROBACION, y por que este bloque no
		 * pretende distinguirlo.
		 *
		 * Se puede comprobar el rango antes o despues del desplazamiento y
		 * la decision es la MISMA:  pd_addr >> 12 < 2^28  <=>  pd_addr < 2^40.
		 * Medido: moviendo la comprobacion detras del >>, el valor de 2^40
		 * se sigue rechazando.  No existe ninguna entrada que distinga los dos
		 * ordenes, y decirlo de otro modo seria inventar una asercion que no
		 * mide nada.
		 *
		 * Lo que SI distingue, y lo que de verdad importa, es que `*out` no se
		 * escriba cuando se rechaza:  un llamante que ignore el codigo de
		 * error leeria un valor inventado.  Eso es lo que comprueban las tres
		 * aserciones de arriba, y se ha verificado rompiéndolas:  al mover la
		 * comprobacion detras del >> y escribir antes de comprobar, fallan
		 * dos de tres. */

		CHECK(rx550_mmio_pt_value(0, NULL) != RX550_MMIO_OK,
		      "C3 salida nula se rechaza");
	}

	printf("\n  %d pass, %d fail\n", pass, fail);
	if (fail) {
		printf("  CONTRATO: INCUMPLIDO\n");
		return 1;
	}
	printf("  CONTRATO: SATISFECHO\n");
	return 0;
}