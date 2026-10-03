// SPDX-License-Identifier: GPL-2.0-only
/*
 * pci_resource.c — capa de adquisición de recursos PCI.
 *
 * QUE HACE
 *   Descubre las BAR del dispositivo objetivo, y reclama selectivamente SOLO
 *   la que el siguiente componente necesitara: la apertura de registros.
 *
 * QUE NO HACE, y es deliberado
 *   No mapea.   No usa pci_iomap, ioremap, readl/writel/readq/writeq.
 *   No pide IRQ. No usa request_irq ni pci_alloc_irq_vectors.
 *   No usa DMA.  No hay buffers.
 *   No toca doorbells, rings, IB, fences, scheduler, VM, VRAM ni firmware.
 *
 *   PCI resource acquisition  !=  GPU execution
 *
 * APIs, verificadas en las cabeceras del kernel EN EJECUCION
 *   /usr/src/kernels/7.1.3-200.nobara.fc44.x86_64/include/linux/pci.h
 *     :1416  int  __must_check pci_enable_device(struct pci_dev *dev);
 *     :1441  void             pci_disable_device(struct pci_dev *dev);
 *     :1567  int  __must_check pci_request_regions(struct pci_dev *, const char *);
 *     :1569  void             pci_release_regions(struct pci_dev *);
 *     :1570  int  __must_check pci_request_region(struct pci_dev *, int, const char *);
 *     :1571  void             pci_release_region(struct pci_dev *, int);
 *     :2283  pci_resource_start(dev, bar)    :2284 pci_resource_end(dev, bar)
 *     :2285  pci_resource_flags(dev, bar)    :2286 pci_resource_len(dev, bar)
 *
 *   Las cuatro ultimas son macros sobre pci_resource_n() (pci.h:2282), que
 *   indexan pdev->resource[bar].  Verificado por compilacion con kbuild real
 *   contra este kernel: 0 errores.
 *
 * POR QUE pci_request_region() Y NO pci_request_regions()
 *   La primera reclama UNA BAR por indice.  La segunda reclama TODAS, que es
 *   exactamente la reserva por anticipacion que este componente prohibe.
 *
 * PCI_ENABLEMENT = DEFERRED
 *   pci_enable_device() habilita decodificacion de memoria y bus mastering, y
 *   hace un reset del dispositivo.  Es estado real de hardware.  En este
 *   componente NO hay consumidor: no se mapea nada todavia, y
 *   pci_request_region() es pura contabilidad de propiedad (toma el recurso
 *   I/O y registra un conflicto) sin tocar el dispositivo.  Habilitar ahora
 *   seria una transicion de hardware sin necesidad demostrable.
 *   Lo requiere el componente MMIO, inmediatamente antes del primer
 *   pci_iomap.  Ver la tabla de unwind en target_resource.h y en probe().
 */

#include <linux/module.h>
#include <linux/pci.h>

#include "pci_resource.h"

/*
 * target_res_discover — localiza las BAR declaradas.
 *
 * No es adquisicion: solo puebla el modelo.  Una BAR con len == 0 queda
 * ABSENT, que es un estado distinto de DISCOVERED.
 */
void target_res_discover(struct pci_dev *pdev, struct target_resources *res)
{
	int bar;

	for (bar = 0; bar < TARGET_NR_BARS; bar++) {
		unsigned long long len;
		unsigned long long start;

		/* Una BAR de 64 bits consume el indice siguiente.  Para ese slot
		 * alto pci_resource_len() devuelve 0, y eso lo marca
		 * correctamente como ABSENT en vez de DISCOVERED.
		 */
		len   = (unsigned long long)pci_resource_len(pdev, bar);
		start = (unsigned long long)pci_resource_start(pdev, bar);

		target_res_set(res, bar, start, len);
	}
}

/*
 * target_res_claim_regions — adquiere la apertura de registros.
 *
 * Devuelve 0 solo si la region quedo realmente reclamada.  Si la BAR no
 * estaba DISCOVERED, o si pci_request_region() falla, no se marca nada: la
 * invariante I3 (no liberar lo que no se adapto) se mantiene por construccion,
 * porque target_res_mark_claimed() solo transiciona desde DISCOVERED.
 */
int target_res_claim_regions(struct pci_dev *pdev, struct target_resources *res)
{
	int rc;

	if (res->bar[TARGET_REG_BAR_INDEX].state != TARGET_RES_DISCOVERED)
		return -ENODEV;

	rc = pci_request_region(pdev, TARGET_REG_BAR_INDEX,
				KBUILD_MODNAME " reg-aperture");
	if (rc)
		return rc;

	if (!target_res_mark_claimed(res, TARGET_REG_BAR_INDEX)) {
		/* Inconsistencia del modelo: deshaz la adquisicion real. */
		pci_release_region(pdev, TARGET_REG_BAR_INDEX);
		return -EFAULT;
	}
	return 0;
}

/*
 * target_res_release — simetrico de claim.
 *
 * I3: recorre UNICAMENTE las ranuras en estado CLAIMED.  Ningun cleanup
 * ficticio: una ranura DISCOVERED o ABSENT no se toca, y disable del
 * dispositivo no se invoca porque no se habilito (PCI_ENABLEMENT DEFERRED).
 */
void target_res_release(struct pci_dev *pdev, struct target_resources *res)
{
	int bar;

	for (bar = 0; bar < TARGET_NR_BARS; bar++) {
		if (!target_res_owned(res->bar[bar].state))
			continue;
		pci_release_region(pdev, bar);
		target_res_mark_released(res, bar);
	}
}
