/* SPDX-License-Identifier: GPL-2.0 */
/*
 * rx550_gart_write.h — escritura por lote de PTE GART, sobre un backing ajeno.
 *
 *   TARGET = RX 550 instalada en esta maquina  (1002:699F, Polaris12, GFX8)
 *   SCOPE  = EXCLUSIVO
 *
 * QUE ES
 *   La mitad de escritura del camino de direccionamiento de VMID0.  Recibe
 *   memoria de tabla que alguien mas reservo y escribe en ella exactamente
 *   las entradas que se le piden, ni una mas.
 *
 * QUE NO ES  (y no puede dejar de no ser)
 *   No es un allocator.  No crea gart.bo.  No decide su tamano, su direccion
 *   GPU, ni si vive en VRAM.  No coloca GPUVAs.  No elige gart_start.  No
 *   elige el VMID.  No escribe registros.  No invalida por su cuenta sin que
 *   se lo pidan.
 *
 *   Todo eso llega desde fuera, en una estructura que dice que falta.
 *   Ver rx550_gart_requirements.
 *
 * LAS TRES FASES, SEPARADAS
 *   CONSTRUCTION   vive en rx550_vmid0_gart.c.  Ahi se construyen las PTE.
 *   WRITE_BATCH    es este componente.  Valida, luego escribe.
 *   INVALIDATION   es una interfaz.  Se llama una vez, al final.
 *
 * POR QUE SEPARADAS Y NO UNA SOLA FUNCION
 *   Porque un error en la validacion tiene que ser RECUPERABLE antes de tocar
 *   memoria.  Si construccion, escritura e invalidacion estuvieran juntas, un
 *   PTE mal formado se discoveria con la tabla ya a medias y la TLB
 *   invalidated, que es el estado mas caro de recuperar.  Con las tres
 *   separadas, el fallo ocurre antes del primer store.
 *
 * LO QUE ESTE COMPONENTE NO AFIRMA
 *   Que una escritura aqui sea visible para la GPU.  No hay barrera, no hay
 *   mb(), no hay fence, y no se afirma que haga falta ninguna.  Que la tabla
 *   este actualizada para el hardware es una consecuencia de una invalidacion
 *   y de una ejecucion posterior, y ninguna de las dos esta aqui.
 *
 *   volatile impide que el COMPILADOR se lleve la escritura.  No dice nada
 *   sobre el HARDWARE.  Son dos cosas distintas y esta frase las separa.
 */
#ifndef RX550_GART_WRITE_H
#define RX550_GART_WRITE_H

#include "rx550_vmid0_gart.h"

/* ── el backing: AJENO ──────────────────────────────────────────────────
 * No se reserva, no se libera, no se reubica.  Solo se describe.
 *   base     direccion de la entrada 0
 *   entries  cuantas entradas cubre desde base
 *
 * La tabla real tiene 65536 entradas, pero eso lo fija quien la reserva, no
 * este componente.  Un backing mas pequeno es legitimo y este codigo lo
 * respeta en vez de asumir el maximo.
 */
/* gmc_v8_0.c:665 -- 1 << vmid, y el registro tiene 16 posiciones. */
#define RX550_VMID0_TLB_INVALID_COUNT	16u

struct rx550_gart_backing {
	void		*base;
	uint64_t	entries;
};

/* ── la invalidacion: INTERFAZ, no MMIO ─────────────────────────────────
 * No hay registros, ni WREG32, ni RREG32, ni ring.  La ownership del path
 * de invalidacion no esta cerrada, asi que no se implementa: se declara y
 * se llama.  Quien tenga el MMIO lo provee.
 */
struct rx550_gart_tlb {
	void	(*request)(void *ctx, unsigned vmid);
	void	 *ctx;
};

/* ── lo que este componente NECESITA y no puede obtener ─────────────────
 * Esto es un handoff, no una configuracion.  No se rellena aqui: lo rellena
 * el owner, y si falta algo, este componente no arranca.
 */
struct rx550_gart_requirements {
	const struct rx550_gart_backing	*backing;	/* TABLE_BACKING   */
	unsigned			 vmid;		/* VMID            */
	const struct rx550_gart_tlb	*tlb;		/* TLB_INVALIDATOR */
};

/* TABLE_GPU_BASE y TABLE_SIZE NO aparecen aqui a proposito: son entrada del
 * componente de programacion de VMID0 (rx550_vmid0_gart.c), no de este.
 * Que un unico sitio los necesite no significa que los dos los demiandan. */

/* ── validacion de una PTE YA CONSTRUIDA ──────────────────────────────
 *
 * El lote entra construido, no en PA + flags.  Asi que hay que comprobar
 * que lo que llega cumple el layout de GFX8 y no simplemente que se pueda
 * construir.  Sin esto, un lote con un bit reservado pasaria intacto.
 *
 * Comprueba (gmc_v8_0.c:691-702):
 *   · bits 40..63 a cero    (reserved)
 *   · bit 3 a cero          (reserved)
 *   · PA representable en 40 bits y alineada a 4 KiB
 *   · no hay nada mas: los bits 0..2 y 4..6 son flags declarados y validos
 */
int rx550_pte_check(uint64_t entry);

/* Bits que una PTE de GART de GFX8 puede tener.  Si algo se sale, no es una
 * PTE de este hardware. */
#define RX550_PTE_GFX8_ALLOWED	(RX550_PTE_FLAG_MASK | RX550_GART_PA_MASK)

/* ── validacion del backing ──────────────────────────────────────────── */
int rx550_gart_backing_check(const struct rx550_gart_backing *b);

/* ── WRITE_BATCH ───────────────────────────────────────────────────────
 *
 * Politica de escrituras (todas Demonstratebles, ninguna asumida):
 *   · valida el lote COMPLETO antes del primer store
 *   · si algo falla, cero escrituras, y el backing queda intacto
 *   · si todo pasa, escribe exactamente n entradas, ni una mas
 *   · nunca escribe parcialmente
 *   · nunca toca una entrada fuera de [first, first+n)
 *
 * count == 0 -> RECHAZADO.  Es DESIGN_CHOICE, no un hecho: un lote vacio
 * no tiene lectura, y un lote vacio seguido de una invalidacion es trabajo
 * que no compra nada.  Si algun dia hace falta, se anade un caso explicito.
 *
 * Devuelve n, o -1.  No hay mas valores de retorno: no existe el caso
 * "escribi parte", y esa es la garantia que hay que poder comprobar. */
int rx550_gart_write(const struct rx550_gart_backing *b,
		     struct rx550_gart_pte_index first,
		     const uint64_t *entries, uint32_t n);

/* ── WRITE_BATCH -> INVALIDATE ─────────────────────────────────────────
 *
 * El orden es el del corpus: amdgpu_gart.c:331-336 escribe todas las
 * entradas y despues invalida UNA vez.  El numero de invalidaciones no
 * depende de n.  No hay forma de invalidar por entrada en esta API, y su
 * ausencia es el contrato, no un hueco.
 *
 * No hay mb() entre las dos fases.  No hay evidencia de que GFX8 lo exija.
 * Si aparece, se anade como campo de esta funcion y se documenta de donde
 * salio, no como una barrera de estilo.
 */
int rx550_gart_write_invalidate(const struct rx550_gart_backing *b,
				struct rx550_gart_pte_index first,
				const uint64_t *entries, uint32_t n,
				const struct rx550_gart_tlb *tlb, unsigned vmid);

/* ── limite explicito ──────────────────────────────────────────────────
 *
 *   WRITE_BATCH_COMPLETED != VISIBLE_TO_GPU != EXECUTED != COMPLETED
 *
 * La funcion de arriba devuelve el numero de entradas escritas.  Eso es
 * todo lo que afirma.  Los tres estados de la derecha no tienen ninguna
 * transicion aqui, y anadirlas seria rellenar un UNKNOWN con un hecho.
 */
static inline bool rx550_gart_write_is_executed(uint32_t entries_written)
{
	(void)entries_written;
	return false;	/* por construccion, no por falta de datos */
}

#endif /* RX550_GART_WRITE_H */
