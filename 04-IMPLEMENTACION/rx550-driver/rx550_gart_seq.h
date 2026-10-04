/* SPDX-License-Identifier: GPL-2.0 */
/*
 * rx550_gart_seq.h — la secuencia de 34 escrituras que programa el GART de
 * esta tarjeta.
 *
 *   TARGET = RX 550 instalada en esta maquina
 *   SCOPE  = EXCLUSIVO
 *
 * QUE ES
 *   EL PLAN, no la ejecucion.  Toma los parametros que la geometria ya tiene
 *   decididos y devuelve, EN ORDEN, las 34 escrituras a registro que
 *   gmc_v8_0.c:829-947 (gmc_v8_0_gart_enable) hace.
 *
 *   Devuelve un plan.  No toca hardware, no tiene mapa, no depende de nada.
 *   Quien lo ejecuta es rx550_target.c, con rx550_mmio_write32 y
 *   rx550_mmio_update_field.
 *
 * POR QUE UN PLAN Y NO UNA FUNCION QUE ESCRIBA
 *
 *   Porque la secuencia no se puede probar sin hardware si se ejecuta
 *   directamente, y esta es la funcion MAS CRITICA del componente:  una
 *   ejecucion equivocada deja el GART mal puesto y no hay forma de notarlo
 *   hasta que una pagina se mapea mal.  Un plan se compara con el corpus en
 *   userspace, y esa comparacion es la unica forma de que 34 escrituras puedan
 *   tener algo que las vigile.
 *
 *   Y hay una razon mas: las 7 escrituras de control son RMW, y el valor que
 *   queda depende de lo que hubiera.  Un plan tiene que llevar ESE valor
 *   como entrada, porque si no estara assuming el estado de reset.
 *
 * DE DONDE SALE EL ORDEN, Y POR QUE NO ES EL DE LA TABLA
 *
 *   El orden es de gmc_v8_0.c y esta escrito abajo como una lista de nombres de
 *   registro.  NO es el orden de rx550_reg_fields[], que es por indice, ni el
 *   del enum, que tambien es por indice.
 *
 *   Y el orden NO es cosmetico.  La invalidacion va ANTES de programar la base:
 *       L859   mmVM_L2_CNTL2  INVALIDATE_ALL_L1_TLBS, INVALIDATE_L2_CACHE
 *       L886-888  los tres PAGE_TABLE_* del contexto 0
 *   y hay un flush detras de los dos contextos.  Un orden distinto no es "menos
 *   optimo":  es un contexto que puede estar activo mientras se le cambia la
 *   tabla.  Por eso el orden va en el codigo y no en un comentario, igual que
 *   el orden[7] de rx550_vmid0_regs.
 *
 * DE DONDE SALEN LOS VALORES DE CAMPO
 *
 *   De rx550_reg_fields[], que ya tiene mask, shift, width y el valor que la
 *   referencia escribe, con su linea del corpus.  Los RMW se COMPONEN con esa
 *   tabla, no con 41 REG_SET_FIELD copiados:  anadir un campo a la tabla lo
 *   anade a la secuencia, y copiarlo lo desincroniza en silencio.  Ver el
 *   finding 1028.
 *
 * LO QUE NO HACE
 *
 *   No calcula la geometria.  gart_start, gart_end, block_size y fragment_size
 *   entran como parametros, ya decididos por la aritmetica del finding 1027.
 *   Esta funcion no vuelve a decidirlos, y no puede:  decidir la colocacion del
 *   GART es otra pregunta.
 *
 *   No escribe.  No invalida.  No programa el bucle de contextos:  lo DEJA
 *   escrito en el plan como 15 operaciones, para que quien lo ejecute no tenga
 *   que saber que eran 15.
 */
#ifndef RX550_GART_SEQ_H
#define RX550_GART_SEQ_H

#include "rx550_spaces.h"
#include "rx550_mmio.h"

#ifdef __KERNEL__
#include <linux/types.h>
#else
#include <stdint.h>
#include <stdbool.h>
#include <stddef.h>
#endif

/* Los 7 registros que la referencia cambia por RREG32/REG_SET_FIELD.  Para
 * estos hace falta el valor ACTUAL como entrada:  lo que no se nombra se
 * PRESERVA, y la secuencia tiene que preservarlo tambien. */
#define RX550_GART_RMW_NR	7

struct rx550_gart_params {
	/* ── GEOMETRIA, YA DECIDIDA ───────────────────────────────────────── */
	uint64_t	gart_start;	/* bytes, espacio GPU        */
	uint64_t	gart_end;		/* bytes, espacio GPU        */
	uint64_t	table_addr;	/* dir. GPU de la tabla GART */
	uint64_t	dummy_page_addr;	/* PA de SISTEMA             */
	uint64_t	max_pfn;
	unsigned	block_size;	/* 10 en esta tarjeta         */
	unsigned	fragment_size;	/* 9 en esta tarjeta          */

	/* ── EL VALOR ACTUAL DE LOS 7 REGISTROS QUE SON RMW ────────────────
	 *
	 *  indexados por el enum de abajo, NO por el de los registros:  este es
	 *  un grupo pequeno y fijo, y su propio orden evita depender del orden
	 *  de la tabla, que es por indice y cambia cuando se anade un
	 *  registro. */
	uint32_t	cur[RX550_GART_RMW_NR];
};

enum rx550_gart_rmw {
	RX550_GART_RMW_L1_TLB_CNTL = 0,
	RX550_GART_RMW_L2_CNTL,
	RX550_GART_RMW_L2_CNTL2,
	RX550_GART_RMW_L2_CNTL3,
	RX550_GART_RMW_L2_CNTL4,
	RX550_GART_RMW_CTX0_CNTL,
	RX550_GART_RMW_CTX1_CNTL,
};

/* Una escritura del plan.  `reg` es el INDICE del registro, no el offset. */
struct rx550_gart_op {
	uint32_t	reg;
	uint32_t	value;
};

/* 34 escrituras: 19 explicitas y 15 del bucle de contextos 1..15. */
#define RX550_GART_OPS_NR	34

struct rx550_gart_seq {
	struct rx550_gart_op	op[RX550_GART_OPS_NR];
	unsigned			n;
};

#define RX550_GART_SEQ_ERR_INCONSISTENT	(-1)
#define RX550_GART_SEQ_ERR_GEOMETRY	(-2)	/* parametro incoherente   */
#define RX550_GART_SEQ_ERR_TABLE	(-3)	/* la tabla no cubre algo    */

/* Construye el plan.  VALIDA TODO antes de devolver nada:  un plan a medio
 * poblar es peor que un error, porque el llamante no tiene forma de saber
 * cuantas operaciones son validas.
 *
 *  Se rechazan, entre otros:
 *   - gart_start > gart_end
 *   - una direccion de mas de 40 bits (no cabe en PHYSICAL_PAGE_NUMBER tras
 *     el >> 12, y truncar en silencio seria escribir una pagina equivocada)
 *   - block_size o fragment_size fuera del rango del campo de 4 bits
 *   - un max_pfn que no cubre la ventana del GART */
int rx550_gart_seq_build(struct rx550_gart_seq *out,
			 const struct rx550_gart_params *p);

/* El numero de escrituras REALES del plan, que tiene que ser 34.  Existe para
 * que el test lo compruebe sin tener que recorrer el plan entero, y para que un
 * futuro cambio que anada o quita una operacion no pase por un aviso. */
unsigned rx550_gart_seq_len(const struct rx550_gart_seq *s);

#endif /* RX550_GART_SEQ_H */