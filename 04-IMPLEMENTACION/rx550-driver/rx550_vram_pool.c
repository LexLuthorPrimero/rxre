/* SPDX-License-Identifier: GPL-2.0 */
/*
 * rx550_vram_pool.c — first-fit con coalescencia.  Puro: sin kernel, sin MMIO.
 *
 * LAS DOS CLÁUSULAS DEL CONTRATO, y aqui es donde se demuestran:
 *
 *   alloc  No escribe `out` si va a fallar.  Se construye el recurso en una
 *          variable local y solo se copia a `out` en el camino de exito.  La
 *          forma de NO hacerlo es escribir `out` y luego fallar, y eso obliga
 *          al llamante a distinguir "no lo ha tocado" de "lo ha tocado y ha
 *          fallado": un estado del que no se puede salir.
 *
 *   free   Deja `res` en RX550_VRAM_RELEASED y pone `owner` a NULL, como
 *          declara el contrato.  Y como no puede devolver error,  cuenta las
 *          liberaciones rechazadas en `stats`, que es el unico canal.
 */
#include "rx550_vram_pool.h"

/* RX550_POOL_NINGUNO viene de <stdint.h>, que en kernel no es la cabecera que existe.
 * El mismo error que el memset del .h: usar un identificador de libc en un
 * .c que compila de las dos formas.  Se declara aqui. */
#define RX550_POOL_NINGUNO	0xFFFFFFFFu

/* Un resto menor que esto no se parte: se deja pegado al bloque que se
 * entrega.  Sin este minimo, un patron de alloc/libre de tamanos distintos
 * llenaria la lista de huecos diminutos y first-fit se volveria O(n) para
 * siempre. */
#define RX550_VRAM_POOL_MIN_SPLIT	64u

int rx550_vram_pool_set_window(struct rx550_vram_pool *p, uint64_t bytes)
{
	if (p == NULL)
		return RX550_VRAM_ERR_NULO;
	if (bytes == 0)
		return RX550_VRAM_ERR_SIN_MEM;

	/* Re-declarar la ventana con hay gente dentro seria perder sus
	 * reservas sin avisar.  Se rechaza en vez de hacerlo. */
	if (p->bloques != 0)
		return RX550_VRAM_ERR_INVALIDO;

	p->ventana_bytes = bytes;
	p->usados_bytes  = 0;
	p->libre[0].offset = 0;
	p->libre[0].size   = bytes;
	p->libre[0].next   = NULL;
	p->n_libres = 1;
	p->stats.free_blocks = 1;
	p->stats.free_bytes  = bytes;
	return RX550_VRAM_OK;
}

/* Alinea `x` hacia arriba a `a`.  `a` es potencia de dos por contrato, asi que
 * la mascara es exacta;  y aun asi se comprueba arriba,  porque un allocator
 * que alinee con `base & ~(align-1)` sobre un align de 3 produce basura sin
 * avisar y ese error tiene que morir en la frontera. */
static uint64_t align_up(uint64_t x, uint64_t a)
{
	return (x + (a - 1)) & ~(a - 1);
}

int rx550_vram_pool_alloc(void *ctx, uint64_t size, uint64_t alignment,
			   struct rx550_vram_resource *out)
{
	struct rx550_vram_pool *p = (struct rx550_vram_pool *)ctx;
	struct rx550_vram_resource res;
	uint64_t aligned_start, hueco, sobra;
	uint32_t idx;

	/* Las tres validaciones que pueden fallar ANTES de tocar nada.  Un
	 * `out` nulo se puede comprobar;  el contenido de `out` no se toca nunca
	 * hasta el final. */
	if (p == NULL || out == NULL)
		return RX550_VRAM_ERR_NULO;
	if (size == 0)
		return RX550_VRAM_ERR_SIN_MEM;
	if (alignment == 0 || (alignment & (alignment - 1)) != 0)
		return RX550_VRAM_ERR_ALIGN;
	if (p->n_libres == 0) {
		p->stats.allocs_fallidas++;
		return RX550_VRAM_ERR_SIN_MEM;
	}

	/* Una sola pasada, y el criterio es el CORRECTO: un hueco sirve si
	 * cabe lo que se pide DESPUES de alinear su inicio.  El criterio
	 * intuitivo ("el hueco es >= alignment") es el que sobra bytes por
	 * alinear, y aceptaria reservas que luego no caben.
	 *
	 *   necesario = (inicio_alineado - inicio_del_hueco) + size
	 *
	 * Se recorre en orden de offset, que con una ventana declarada desde 0
	 * es first-fit de verdad. */
	{
		uint64_t ini = 0;
		uint32_t i;

		idx = RX550_POOL_NINGUNO;
		for (i = 0; i < p->n_libres; i++) {
			ini = align_up(p->libre[i].offset, alignment);
			if (p->libre[i].size >=
			    ((ini - p->libre[i].offset) + size)) {
				idx = i;
				break;
			}
		}
		if (idx == RX550_POOL_NINGUNO) {
			p->stats.allocs_fallidas++;
			return RX550_VRAM_ERR_SIN_MEM;
		}
		aligned_start = ini;
		hueco = p->libre[idx].size;
	}

	sobra = hueco - ((aligned_start - p->libre[idx].offset) + size);

	/* Parte, o se entrega entero si el resto es demasiado pequeno para
	 * merecer su propia entrada en la lista. */
	if (sobra >= RX550_VRAM_POOL_MIN_SPLIT) {
		p->libre[idx].offset = aligned_start + size;
		p->libre[idx].size   = sobra;
	} else {
		/* El hueco entero se consume.  Se quita de la lista. */
		if (idx + 1 < p->n_libres) {
			uint32_t k;

			for (k = idx; k + 1 < p->n_libres; k++)
				p->libre[k] = p->libre[k + 1];
		}
		p->n_libres--;
	}

	/* Aqui, y solo aqui, se toca `out`. */
	res.offset    = rx550_vram_off(aligned_start);
	res.size      = size;
	res.alignment = alignment;
	res.owner     = p;
	res.state     = RX550_VRAM_HELD;
	*out = res;

	p->usados_bytes += size;
	p->bloques++;
	p->stats.allocs_ok++;
	p->stats.free_bytes  -= size;
	p->stats.free_blocks = p->n_libres;
	return RX550_VRAM_OK;
}

void rx550_vram_pool_free(void *ctx, struct rx550_vram_resource *res)
{
	struct rx550_vram_pool *p = (struct rx550_vram_pool *)ctx;
	uint64_t off, size;
	uint32_t i, k;

	if (p == NULL || res == NULL) {
		if (p != NULL)
			p->stats.frees_rechazadas++;
		return;
	}

	off  = res->offset.bytes;
	size = res->size;

	/* Una liberacion tiene que ser de una reserva NUESTRA, y tiene que
	 * estar en uso.  Todo lo contrario se cuenta y se sale: `free` no
	 * devuelve nada por contrato,  asi que el error no se propaga,  se
	 * cuenta. */
	if (res->owner != p || res->state != RX550_VRAM_HELD ||
	    size == 0 || off + size > p->ventana_bytes) {
		p->stats.frees_rechazadas++;
		return;
	}
	if (p->n_libres >= RX550_VRAM_POOL_NR_BLOCKS) {
		p->stats.frees_rechazadas++;
		return;
	}

	/* Insercion ordenada por offset, que es lo que hace posible la
	 * coalescencia con una sola pasada. */
	for (i = 0; i < p->n_libres && p->libre[i].offset < off; i++)
		;
	if (i < p->n_libres)
		for (k = p->n_libres; k > i; k--)
			p->libre[k] = p->libre[k - 1];
	p->libre[i].offset = off;
	p->libre[i].size   = size;
	p->n_libres++;

	/* Fusiona con el vecino de la izquierda y con el de la derecha. */
	if (i > 0 && p->libre[i - 1].offset + p->libre[i - 1].size == p->libre[i].offset) {
		p->libre[i - 1].size += p->libre[i].size;
		for (k = i; k + 1 < p->n_libres; k++)
			p->libre[k] = p->libre[k + 1];
		p->n_libres--;
		i--;
	}
	if (i + 1 < p->n_libres &&
	    p->libre[i].offset + p->libre[i].size == p->libre[i + 1].offset) {
		p->libre[i].size += p->libre[i + 1].size;
		for (k = i + 1; k + 1 < p->n_libres; k++)
			p->libre[k] = p->libre[k + 1];
		p->n_libres--;
	}

	/* El contrato: free deja el recurso en RELEASED. */
	res->owner = NULL;
	res->state = RX550_VRAM_RELEASED;

	p->usados_bytes -= size;
	p->bloques--;
	p->stats.frees_ok++;
	p->stats.free_bytes  += size;
	p->stats.free_blocks = p->n_libres;
}

uint64_t rx550_vram_pool_free_bytes(const struct rx550_vram_pool *p)
{
	if (p == NULL)
		return 0;
	return p->ventana_bytes - p->usados_bytes;
}

uint64_t rx550_vram_pool_largest(const struct rx550_vram_pool *p)
{
	uint64_t best = 0;
	uint32_t i;

	if (p == NULL)
		return 0;
	for (i = 0; i < p->n_libres; i++)
		if (p->libre[i].size > best)
			best = p->libre[i].size;
	return best;
}