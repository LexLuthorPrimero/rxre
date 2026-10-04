/* SPDX-License-Identifier: GPL-2.0 */
/*
 * rx550_vram.h — frontera de recurso VRAM.  NO es un allocator.
 *
 * Que es
 *   El contrato que un allocator de VRAM debe satisfacer, y el tipo de recurso
 *   que devuelve.  Nada mas.
 *
 * Que NO es
 *   No es drm_buddy.  No es ttm.  No es amdgpu_vram_mgr.  Esos existen en el
 *   driver de referencia y son evidencia de QUE hace falta un allocator, no de
 *   COMO tiene que ser el nuestro.
 *
 * POR QUE el recurso se presta y no se posee
 *   PDB0 -> recurso VRAM, y recurso VRAM -> allocator.  Si PDB0 tuviera un
 *   puntero de vuelta al allocator, el grafo tendria ciclo.  El objeto guarda
 *   el recurso y la funcion de liberacion, nunca el allocator.  Esa asimetria
 *   es lo que mantiene el grafo aciclico, y hay un test que lo comprueba.
 */
#ifndef RX550_VRAM_H
#define RX550_VRAM_H

#include "rx550_spaces.h"

/* ── estados del recurso ────────────────────────────────────────────────── */
enum rx550_vram_state {
	RX550_VRAM_ABSENT = 0,
	RX550_VRAM_HELD,
	RX550_VRAM_RELEASED
};

struct rx550_vram_resource {
	struct rx550_vram_offset	offset;	/* byte dentro de la ventana VRAM */
	uint64_t			size;		/* bytes                          */
	uint64_t			alignment;	/* bytes, potencia de dos         */
	void			       *owner;	/* opaco: quien lo reservo        */
	enum rx550_vram_state		state;
};

/* ── espacio de errores ───────────────────────────────────────────────────
 *
 * MEDIDO 2026-10-04: la firma devolvia `int` SIN espacio de valores.  No habia
 * RX550_VRAM_OK, ni ERR_*, ni nada que permitiera distinguir "no cabe" de "el
 * backend fallo" de "el backend devolvio basura".  El unico consumidor
 * (rx550_pdb0.c:92,96) colapsaba cualquier motivo a -1, de modo que la
 * informacion se perdia en el punto de entrada y no se podia propagar.
 *
 * Se declara por lo mismo que los otros cuatro modulos del componente tienen el
 * suyo: rx550_mmio_access.h, rx550_vmid1_pgt_backing.h, rx550_dummy_page.h y
 * rx550_gart_table.h.  Cuatro de cinco ya lo tenian y esta frontera era la
 * unica que no.
 *
 * RANGO: -100..-90, para no colisionar con los otros cuatro.
 */
#define RX550_VRAM_OK			0
#define RX550_VRAM_ERR_NULO		(-90)	/* puntero nulo                   */
#define RX550_VRAM_ERR_ALIGN		(-91)	/* align 0 o no potencia de dos   */
#define RX550_VRAM_ERR_SIN_MEM		(-92)	/* la peticion no cabe            */
#define RX550_VRAM_ERR_BACKEND		(-93)	/* el backend fallo               */
#define RX550_VRAM_ERR_INVALIDO		(-94)	/* devolvio algo no conforme     */
#define RX550_VRAM_ERR_DOBLE		(-95)	/* doble liberacion               */

/* La firma que un allocator debe cumplir.  Deliberadamente minima: el PDB0
 * no necesita saber nada mas.
 *
 * CONTRATO DE LAS DOS, y el "o no escribe" es la parte que suele faltar:
 *
 *   alloc  Si devuelve RX550_VRAM_OK, escribe TODO `out` y lo deja en
 *          RX550_VRAM_HELD.  Si devuelve cualquier otro valor, NO ESCRIBE
 *          `out` en absoluto: lo deja intacto.  Un alloc que falla dejando
 *          `out` a medias obliga a cada llamante a distinguir "no lo ha tocado"
 *          de "lo ha tocado y ha fallado", y ese es un estado del que no se
 *          puede salir.  rx550_vmid1_pgt_backing.h:173 escribe esa misma regla
 *          para su backend, y es el precedente.
 *
 *   free   No devuelve nada, y por tanto no puede fallar: si necesita
 *          informar, es que el contrato estaba mal.  Deja `res` en
 *          RX550_VRAM_RELEASED, y es su deber no volver a usarlo.
 */
typedef int (*rx550_vram_alloc_fn)(void *ctx, uint64_t size, uint64_t alignment,
				   struct rx550_vram_resource *out);
typedef void (*rx550_vram_free_fn)(void *ctx, struct rx550_vram_resource *res);

static inline void rx550_vram_resource_reset(struct rx550_vram_resource *r)
{
	r->offset = rx550_vram_off(0);
	r->size = 0;
	r->alignment = 0;
	r->owner = NULL;
	r->state = RX550_VRAM_ABSENT;
}

/* Valida lo que el allocator devolvió.  Devuelve 0 si sirve, -1 si no.
 * Un allocator que devuelve basura se rechaza aqui, no mas abajo.
 *
 * MEDIDO 2026-10-04: esta funcion comprobaba tres cosas y el contrato declara
 * cinco.  Las tres que faltaban eran SILENCIOSAS: un allocator que mintiese en
 * el campo `alignment` o devolviese `state = ABSENT` pasaba el filtro entero, y
 * el fallo no aparecia como "el allocator mintio" sino mas tarde como "la GPU
 * no mapea bien", que es el sintoma mas caro de buscar en todo el componente
 * (las mismas palabras en rx550_mmio_access.h:819-822).  Se cierran aqui y cada
 * una tiene su asercion en tests/test_vram.c.
 *
 * El orden importa: align == 0 se comprueba PRIMERO porque aparece como modulo
 * en el ultimo return, y dividir por cero en userspace es una SIGFIPE que
 * mata el test en vez de fallar la asercion.
 *
 * Sobre `alignment >= align` y no `== align`: un allocator que entrega MAS
 * alineacion de la pedida cumple el contrato, y el chequeo del offset lo
 * confirma.  Rechazar el exceso seria incorrecto.  Lo que no se acepta es
 * prometer menos de lo pedido, o no rellenar el campo.
 */
static inline int rx550_vram_resource_valid(const struct rx550_vram_resource *r,
					    uint64_t min_size, uint64_t align)
{
	if (align == 0)
		return -1;

	/* potencia de dos.  El allocator tipico alinea con `base & ~(align-1)`,
	 * que para align = 3 produce basura sin avisar.  El comentario del
	 * campo lo prometia y ninguna capa lo exigia. */
	if ((align & (align - 1)) != 0)
		return -1;

	/* El campo `alignment` tiene que existir y no prometer menos de lo
	 * pedido.  Sin esto, un offset bien alineado con el campo puesto a 0
	 * pasaba. */
	if (r->alignment < align)
		return -1;

	if (r->owner == NULL)
		return -1;

	/* ABSENT con owner no nulo, o RELEASED, significan que no hay memoria
	 * despite a que el allocator haya rellenado el resto.  El filtro no
	 * miraba `state`. */
	if (r->state != RX550_VRAM_HELD)
		return -1;

	if (r->size < min_size)
		return -1;
	if ((r->offset.bytes % align) != 0)
		return -1;
	return 0;
}

#endif /* RX550_VRAM_H */
