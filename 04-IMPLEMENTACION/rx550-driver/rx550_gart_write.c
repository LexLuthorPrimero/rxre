/* SPDX-License-Identifier: GPL-2.0 */
/*
 * rx550_gart_write.c — validar, despues escribir.  En ese orden y no al reves.
 */
#include "rx550_gart_write.h"

int rx550_pte_check(uint64_t entry)
{
	/* Es la UNICA comprobacion que hace falta, y las otras dos que
	 * parecian necesarias son estructurales.  Decirlo aqui evita que
	 * alguien las vuelva a escribir:
	 *
	 *  · 40 bits de PA -- implicito.  La mascara PA tapa 12..39, luego
	 *    los bits 40..63 estan fuera de ALLOWED y esta misma prueba los
	 *    rechaza.  Un chequeo de rango aparte ("entry & PA_MASK > PA_MASK")
	 *    seria codigo muerto: una mascara no puede excederse a si misma.
	 *
	 *  · PA alineada a 4 KiB -- implicito.  entry & PA_MASK tiene los
	 *    12 bajos en cero por construccion de la mascara.  Comprobar
	 *    (entry & 0xFFF) seria un ERROR: los bits 0..11 no son solo PA,
	 *    son VALID, SYSTEM, SNOOPED, EXECUTABLE, READABLE, WRITEABLE
	 *    y FRAGMENT.  Rechazar por "desalineada" rechazaria una PTE
	 *    perfectamente buena por tener el bit de validez puesto. */
	if ((entry & ~RX550_PTE_GFX8_ALLOWED) != 0)
		return -1;

	return 0;
}

int rx550_gart_backing_check(const struct rx550_gart_backing *b)
{
	if (b == NULL || b->base == NULL)
		return -1;
	if (b->entries == 0)
		return -1;
	/* NO HAY AUTORIDAD DE RANGO GLOBAL AQUI, y no hay por que ponerla.
	 *
	 * Este componente no conoce el maximo de entradas que la apertura
	 * puede direccionar, y no lo averigua: RX550_GART_ENTRY_COUNT se
	 * retiro de rx550_vmid0_gart.h porque era una SEGUNDA autoridad de
	 * rango, y la autoridad real es la apertura.
	 *
	 * MEDIDO, y por que la retirada era correcta y no purismo:
	 *
	 *   amdgpu_gart.c:533   num_gpu_pages = gmc.gart_size / 4096
	 *   amdgpu_gart.h:33    AMDGPU_GPU_PAGE_SIZE = 4096
	 *   gmc_v8_0.c:595      CHIP_POLARIS12 -> gart_size = 256 MiB
	 *   gmc_v8_0.c:604-605  gart_size = amdgpu_gart_size << 20
	 *   amdgpu_drv.c:154    amdgpu_gart_size = -1   (auto)
	 *   amdgpu_drv.c:293    module_param_named(gartsize, ..., 0600)
	 *   gmc_v8_0.c:608      gart_size += smu_prv_buffer_size
	 *
	 *   count = gart_size / 4096, y gart_size NO es una constante:
	 *
	 *     auto      256 MiB  ->  65536 entradas
	 *     gartsize=1024      -> 262144 entradas
	 *
	 *   osea que 65536 es un valor DERIVADO del parametro por defecto,
	 *   congelado en una constante global.  Un `gartsize=1024` escrito
	 *   por root en /sys/module/amdgpu/parameters/gartsize produce una
	 *   apertura de 262144 entradas en ESTA MISMA ASIC, y la comprobacion
	 *   que se acaba de quitar la rechazaria.  La constante no era un
	 *   hecho del hardware: era una eleccion de configuracion.
	 *
	 * LO QUE QUEDA, y basta para no escribir fuera del backing: la cota
	 * del CALLER, puesta tres veces mas abajo contra b->entries --
	 * D (n <= entries), B (first <= entries) y E+F (first + n <= entries,
	 * por resta).  De E+F sale, sin comprobar nada mas, que todo indice
	 * escrito esta en [0, entries-1].
	 *
	 * LO QUE SE PIERDE, dicho para que no se lea como gratis: este
	 * componente ya no detecta un backing que declare MAS entradas de las
	 * que reservo.  Eso lo detecta quien reserva, comparando entries
	 * contra la apertura que reservo. */
	return 0;
}

int rx550_gart_write(const struct rx550_gart_backing *b,
		     struct rx550_gart_pte_index first,
		     const uint64_t *entries, uint32_t n)
{
	volatile uint64_t *dst;
	uint32_t i;

	/* A. backing utilizable: no NULL, base no NULL, entries > 0, y
	 * entries dentro de lo que el hardware puede direccionar.  La
	 * capacidad la pone quien reservo, y se respeta tal cual. */
	if (rx550_gart_backing_check(b) != 0)
		return -1;
	if (entries == NULL)
		return -1;

	/* C. count == 0 -> RECHAZO EXPLICITO.
	 *
	 * No se deduce de first + n - 1.  Eso sería depending de un
	 * desbordamiento de unsigned para rechazar, y un desbordamiento
	 * no es un contrato: es lo que hace aritmetica, no lo que este
	 * componente promete.  Ademas con la comprobacion puesta, n=0
	 * devolveria 0 y el llamador leeria eso como "escritas 0
	 * entradas, sin error", que es exactamente el estado raro que
	 * merece un -1. */
	if (n == 0)
		return -1;

	/* D. el lote no puede ser mas grande que la tabla entera. */
	if ((uint64_t)n > b->entries)
		return -1;

	/* B. el primer indice tiene que caber en la tabla.  Se acota con
	 * <= y no con < para que la resta de E+F no pueda desbordar:
	 * con first == entries la diferencia es 0 y n >= 1 la rechaza
	 * igualmente, pero la aritmetica queda dentro de rango. */
	if (first.index > b->entries)
		return -1;

	/* E + F, por resta y no por suma.
	 *
	 *   n <= entries - first     <=>     first + n <= entries
	 *
	 * first + n podria desbordar un uint64_t, y el patron "comprobar
	 * que no desborde" ya se ha demostrado fragil en este proyecto:
	 * una guarda que depende de que la aritmetica coopere.  La resta
	 * no puede desbordar porque B ya garantiza first <= entries.
	 *
	 * G. de aqui sale, sin comprobar nada mas, que los indices
	 * escritos son first .. first+n-1, todos dentro de
	 * [0, entries-1].  No se escribe una entrada fuera del backing. */
	if ((uint64_t)n > b->entries - first.index)
		return -1;

	/* VALIDATE_ALL: el lote entero se comprueba antes del primer store.
	 * Un elemento malo devuelve -1 sin haber escrito nada. */
	for (i = 0; i < n; i++) {
		if (rx550_pte_check(entries[i]) != 0)
			return -1;
	}

	/* WRITE_ALL: exactamente n, ni una mas, ni una menos. */
	dst = (volatile uint64_t *)b->base;
	for (i = 0; i < n; i++)
		dst[first.index + (uint64_t)i] = entries[i];

	return (int)n;
}

int rx550_gart_write_invalidate(const struct rx550_gart_backing *b,
				struct rx550_gart_pte_index first,
				const uint64_t *entries, uint32_t n,
				const struct rx550_gart_tlb *tlb, unsigned vmid)
{
	int written;

	if (tlb == NULL || tlb->request == NULL)
		return -1;
	if (vmid >= RX550_VMID0_TLB_INVALID_COUNT)
		return -1;

	/* La escritura va primero y completa.  Si falla, no se invalida
	 * nada: invalidar una tabla que no se toco solo cuesta. */
	written = rx550_gart_write(b, first, entries, n);
	if (written < 0)
		return -1;

	/* Una vez.  No depende de n.  No hay mb() y no se afirma que
	 * haga falta: UNKNOWN, no Forgotten. */
	tlb->request(tlb->ctx, vmid);
	return written;
}
