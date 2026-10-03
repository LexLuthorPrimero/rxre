/* SPDX-License-Identifier: GPL-2.0-only */
/*
 * pci_resource.h — interfaz de la capa de propiedad de recursos PCI.
 *
 * Declaraciones compartidas entre pci_resource.c (implementación) y
 * rx550_target.c (único consumidor).  Existe para que ninguna de las dos
 * direcciones declare los prototipos por su cuenta.
 *
 * ALCANCE: sólo propiedad y adquisición.  Ninguna función de esta cabecera
 * mapea memoria, registra IRQ ni reserva buffers DMA.
 */
#ifndef PCI_RESOURCE_H
#define PCI_RESOURCE_H

#include "target_resource.h"

/*
 * target_res_discover — puebla el modelo con las BAR declaradas.
 * No adquiere nada.  No cambia estado del hardware.
 */
void target_res_discover(struct pci_dev *pdev, struct target_resources *res);

/*
 * target_res_claim_regions — adquiere selectivamente la apertura de
 * registros.  Devuelve 0 sólo si la región quedó realmente reclamada.
 */
int target_res_claim_regions(struct pci_dev *pdev,
			     struct target_resources *res);

/*
 * target_res_release — libera únicamente las regiones en estado CLAIMED.
 */
void target_res_release(struct pci_dev *pdev, struct target_resources *res);

#endif /* PCI_RESOURCE_H */
