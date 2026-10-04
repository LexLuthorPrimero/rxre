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
#include "rx550_mmio_access.h"

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
	/*  VERIFICABLE:  se puede comprobar releyendo el registro.  Y para
	 *
	 *  24 de las 34 escrituras van a registros que la propia tabla del driver
	 *  declara "W",  o sea de solo escritura:
	 *
	 *      los 15 PAGE_TABLE_BASE del bucle de contextos
	 *      PAGE_TABLE_START y _END de los dos contextos
	 *      PROTECTION_FAULT_DEFAULT de los dos contextos
	 *      los tres de la identity aperture
	 *      y CNTL2 del contexto 1  ("W" segun la tabla)
	 *
	 *  Releerlos NO prueba que la escritura haya tenido efecto:  lo unico que
	 *  devolveria es lo que hubiera,  que es lo mismo que devolveria si no se
	 *  hubiera escrito nada.  Y peor:  si el apply exigiera la igualdad,  de las
	 *  34 escrituras solo PODRIAN verificarse 9,  y las otras 25 darian fallo
	 *  con toda la razon.  Un apply que reporta 25 fallos y 9 acertos sobre un
	 *  GART bien programado no es util para diagnosticar nada.
	 *
	 *  El flag sale de la columna `access` de rx550_vmid1_regs[],  que ya
	 *  existe y ya dice "W" para esos 24.  No se reimplementa aqui:  se lee. */
	bool		verificable;
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

/* -- LA PARTE QUE TOCA EL MAPA ------------------------------------------------
 *
 *  Todo lo de arriba es puro.  Lo de abajo escribe, y son tres funciones
 *  separadas a proposito, porque el ORDEN en que se llaman no es un detalle:
 *
 *      1.  rx550_gart_snapshot()   LEE  los 7 registros que la secuencia
 *                                    cambia por RMW
 *      2.  rx550_gart_build_from()  usa esa lectura y produce el plan
 *      3.  rx550_gart_apply()       ESCRIBE  las 34 y las relee
 *
 *  El paso 1 tiene que ir antes del 2 porque los siete RMW se componen sobre lo
 *  que hubiera, y lo que hubiera hay que leerlo del hardware.  Quien se salte el
 *  snapshot y pase unos cur inventados esta escribiendo un plan coherente sobre
 *  un registro cuyo resto de campos no ha mirado nadie, y no se va a enterar
 *  hasta que una pagina se mapee mal.
 *
 *  build_from() existe para que ese orden no sea una instruccion en un
 *  comentario:  hace los dos pasos juntos y no hay forma de hacer el segundo sin
 *  el primero.
 */

/* Los SIETE registros, en el orden de enum rx550_gart_rmw. */
int rx550_gart_snapshot(const struct rx550_mmio_map *map, uint32_t *cur_out);

/* Snapshot + build.  Equivale a:
 *      rx550_gart_snapshot(map, p->cur);  rx550_gart_seq_build(seq, p);
 *  y no se puede usar al reves. */
int rx550_gart_build_from(const struct rx550_mmio_map *map,
			 struct rx550_gart_seq *seq,
			 const struct rx550_gart_params *p);

/* Que se ha escrito, que numero de operacion, y que se ha leido de vuelta.  Los
 * tres, porque la lectura de vuelta es la UNICA forma de saber que el hardware
 * ha usado el plan.  Sin ella, 34 escrituras a un mapa correcto son indistingu-
 * bles de 34 escrituras a un mapa que no responde. */
struct rx550_gart_apply_report {
	uint32_t	cur[RX550_GART_RMW_NR];	/* lo que se leyo antes   */
	unsigned	n_escritas;		/* las que se hicieron       */
	unsigned	n_verificadas;		/* las releidas que cuadraron */
	unsigned	n_no_verificables;	/* las de registro "W":  ni
						 * se pueden comprobar ni se
						 * deben declarar fallo */
	unsigned	primer_fallo;		/* indice, o UINT32_MAX si
						 * ninguna fallo  */
	uint32_t	leido;		/* lo que devolvio el registro */
	uint32_t	escrito;		/* lo que se pretendia       */
};

#define RX550_GART_NO_FALLO	UINT32_MAX

/* Aplica el plan y VERIFICA cada escritura releyendo el registro.  Si una
 * lectura no devuelve lo escrito,  se para ahi y lo dice con el indice:  seguir
 * escribiendo encima de un mapa que ya no responde no arregla nada y esconde el
 * primer sintoma,  que es el unico que vale.
 *
 * Un mapa de lectura y escritura es una precondicion, no un resultado:  aqui se
 * escribe,  y el llamador tiene que haberlo reservado por su cuenta. */
int rx550_gart_apply(const struct rx550_mmio_map *map,
		     const struct rx550_gart_seq *seq,
		     struct rx550_gart_apply_report *out);

#endif /* RX550_GART_SEQ_H */