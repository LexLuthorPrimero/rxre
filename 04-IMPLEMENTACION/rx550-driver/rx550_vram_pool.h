/* SPDX-License-Identifier: GPL-2.0 */
/*
 * rx550_vram_pool.h — un allocator de VRAM, y el primero que existe.
 *
 * Que es
 *   Un pool de rango contiguo con lista de bloques libres y ajuste primero,
 *   sobre un intervalo de bytes que le DA EL LLAMANTE.  Cumple el contrato de
 *   rx550_vram.h, incluidas las dos clausulas que ese contrato declara y que
 *   ningun allocator habia implementado todavia: el "o no escribe `out`" del
 *   alloc, y el "deja `res` en RELEASED" del free.
 *
 * Que NO es
 *   No es un allocator de VRAM de verdad.  Allocar bytes en un intervalo es la
 *   parte facil; lo que hace falta para VRAM real es/mapear esas paginas en el
 *   espacio de direcciones de la GPU, y eso es otro modulo y otro dia.
 *
 *   No es drm_buddy, ni ttm, ni amdgpu_vram_mgr.  Esos existen en el driver de
 *   referencia y son evidencia de QUE hace falta un allocator, no de COMO tiene
 *   que ser el nuestro.
 *
 * POR QUE FIRST-FIT Y NO BEST-FIT NI BUDDY
 *   MEDIDO 2026-10-04: en este componente hay DOS peticiones previsibles y
 *   known:  la tabla del GART, 65536 x 8 B = 512 KiB alineados a 4096
 *   (rx550_gart_table.h),  y las tablas de PDB0, 4096 B cada una
 *   (rx550_pdb0.h:45).  Con dos tamanos fijos, first-fit con coalescencia da
 *   fragmentation interna CERO en el regimen permanente: los bloques se liberan
 *   y vuelven a fundirse.  Best-fit seria marginally mejor en un patron
 *  Variable,  y aqui no hay patron variable.  Buddy seria mas rapido de
 *   fragmentar en teoria y mas codigo sin measured need.  First-fit es la que
 *   se puede PROBAR exhaustivamente sin GPU,  que es el criterio del proyecto.
 *
 * LO QUE NO SE AFIRMA
 *   Que.first-fit sea el allocator correcto para la carga real.  Eso no se ha
 *   medido,  y no hay carga real todavia: probe() no ejecuta el GART.  Es la
 *   opcion mas simple que se puede probar,  no la optima,  y el criterio del
 *   proyecto para specialise es medida, no elegancia.
 */
#ifndef RX550_VRAM_POOL_H
#define RX550_VRAM_POOL_H

#include "rx550_vram.h"

/* Bloque libre.  La lista es simplemente enlazada por `next`,  y `prev_count`
 * NO existe: el pool no indexa por recurso,  busca por offset al liberar.  Es
 * O(n) en el peor caso y O(1) en el regimen de dos tamanos. */
struct rx550_vram_block {
	uint64_t			offset;	/* byte dentro de la ventana */
	uint64_t			size;	/* bytes                       */
	struct rx550_vram_block		*next;
};

/* Conteo de bloques libres y de huecos contiguos, para que un test pueda
 * observar la fragmentacion SIN que el allocator tenga que devolver un estado.
 * `free` es `void` por contrato: si necesita informar es que el contrato estaba
 * mal.  Estas dos cuentas son el unico canal que tiene. */
struct rx550_vram_pool_stats {
	uint32_t	free_blocks;	/* bloques en la lista        */
	uint64_t	free_bytes;	/* bytes en la lista          */
	uint32_t	allocs_ok;
	uint32_t	frees_ok;
	uint32_t	frees_rechazadas;	/* liberacion invalida o doble */
	uint32_t	allocs_fallidas;
};

#define RX550_VRAM_POOL_NR_BLOCKS	16	/* bloques libres maximos */

struct rx550_vram_pool {
	uint64_t			ventana_bytes;	/* capacidad declarada */
	uint64_t			usados_bytes;
	uint32_t			bloques;	/* bloques ocupados     */
	struct rx550_vram_block		libre[RX550_VRAM_POOL_NR_BLOCKS];
	uint32_t			n_libres;
	struct rx550_vram_pool_stats	stats;
};

/* Un pool empieza VACIO: sin ventana, y por tanto con cero capacidad.  Que no
 * haya un "pool vacio que reserva 64 KiB por defecto" es deliberado: la
 * capacidad de la VRAM la lee CONFIG_MEMSIZE, y meterla aqui seria quemarla
 * como constante, que es el defecto que este componente lleva tres
 * correcciones deshaciendo.
 *
 * El reset se escribe CAMPO A CAMPO y no con memset: esta cabecera la incluye
 * codigo de kernel, y el equivalente de memset ahi es linux/string.h, no
 * <string.h>.  Meter la cabecera de libc en una linea que compila de las dos
 * formas es el mismo error que ya se registro con target_mem_host.h haciendo
 * `typedef int bool`. */
static inline void rx550_vram_pool_init(struct rx550_vram_pool *p)
{
	uint32_t i;

	p->ventana_bytes = 0;
	p->usados_bytes  = 0;
	p->bloques       = 0;
	p->n_libres      = 0;
	for (i = 0; i < RX550_VRAM_POOL_NR_BLOCKS; i++) {
		p->libre[i].offset = 0;
		p->libre[i].size   = 0;
		p->libre[i].next   = NULL;
	}
	p->stats.free_blocks       = 0;
	p->stats.free_bytes        = 0;
	p->stats.allocs_ok         = 0;
	p->stats.frees_ok          = 0;
	p->stats.frees_rechazadas  = 0;
	p->stats.allocs_fallidas   = 0;
}

/* Declara la ventana.  Devuelve RX550_VRAM_OK o RX550_VRAM_ERR_SIN_MEM si
 * `bytes` es 0.  DECLARACION, no descubrimiento: quien llama ya leyo la
 * capacidad de la someplace y la pasa. */
int rx550_vram_pool_set_window(struct rx550_vram_pool *p, uint64_t bytes);

/* Las dos funciones del contrato.  Se implementan aqui porque el pool ES un
 * allocator,  no un allocator inyectado: no hay backend detras que inyectar. */
int  rx550_vram_pool_alloc(void *ctx, uint64_t size, uint64_t alignment,
			   struct rx550_vram_resource *out);
void rx550_vram_pool_free(void *ctx, struct rx550_vram_resource *res);

/* Bytes libres totiros,  y bytes libres en el hueco MAS GRANDE.  La segunda
 * es la que responde "¿cabe la tabla del GART ahora mismo?",  que es la
 * pregunta que se va a hacer el cliente y para la que first-fit con
 * fragmentacion interna cero tiene la respuesta trivial. */
uint64_t rx550_vram_pool_free_bytes(const struct rx550_vram_pool *p);
uint64_t rx550_vram_pool_largest(const struct rx550_vram_pool *p);

#endif /* RX550_VRAM_POOL_H */