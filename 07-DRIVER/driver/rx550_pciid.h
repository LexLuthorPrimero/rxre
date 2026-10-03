/* SPDX-License-Identifier: GPL-2.0 */
/*
 * rx550_pciid — driver exclusivo para la RX 550 instalada en esta maquina.
 *
 *   TARGET = RX 550 INSTALADA EN ESTA COMPUTADORA
 *   SCOPE  = EXCLUSIVO
 *
 * Estado del componente:  1) identidad PCI  2) lifecycle  3) device object
 *
 * Ver 08-ARQUITECTURA/designs/011-driver-baseline-primer-componente.md
 */
#ifndef _RX550_PCIID_H
#define _RX550_PCIID_H

#include <linux/types.h>
#include <linux/pci.h>

/*
 * ============================================================================
 * EL OBJETO
 * ============================================================================
 *
 * Estado de software propiedad del driver para UNA instancia del target.
 *
 * CAMBIO RESPECTO AL COMPONENTE 2: el objeto ya no guarda una copia de la
 * identidad. Antes tenia `struct rx550_pciid id`. Se quito.
 *
 * Por que se puede quitar, con evidencia y no por gusto:
 *
 *   - Los valores de identidad (vendor, device, subsys_vendor, subsys_device,
 *     revision) son properties de struct pci_dev, que el core de PCI relleno al
 *     enumerar. Son legibles en cualquier momento a traves de `pdev`.
 *   - El core es dueno de `pdev` y lo mantiene vivo mientras el driver este
 *     enlazado. Copiarlos al objeto no los protege de nada: creates una
 *     segunda fuente de verdad que puede divergir de la primera.
 *   - En esta fase el driver no los consulta despues de probe(). La unica
 *     lectura es la linea de log de probe, que puede leerlos de `pdev`
 *     directamente en ese momento.
 *
 * Es decir: TARGET IDENTITY no es DEVICE RUNTIME STATE. La identidad la posee
 * el core; el objeto solo guarda la relacion con el core.
 *
 * ============================================================================
 * CONTRATO POR CAMPO
 * ============================================================================
 *
 * FIELD   pdev
 * PURPOSE ancla el estado del driver a la instancia del core, y da un punto
 *         unico desde el que alcanzar todo lo que en el futuro se anade
 *         (regiones PCI, IRQ, DMA, MMIO). Sin el, cada recurso futuro
 *         necesitaria un puntero propio, redundante.
 * OWNER   el driver, mientras el objeto existe. NO es del driver el `pdev`:
 *         es del core de PCI, y solo se toma una referencia logica.
 * INITIALIZED_WHERE
 *         probe(), inmediatamente despues de la asignacion y antes de publicar.
 * VALID_FROM
 *         el return 0 de probe().
 * INVALIDATED_WHERE
 *         remove(), con pci_set_drvdata(pdev, NULL), antes de destruir.
 * FREED_WHERE
 *         remove(), con kfree(). Nunca antes.
 *
 * ============================================================================
 * MODELO DE PROPIEDAD DE RECURSOS
 * ============================================================================
 *
 * RESOURCE_MODEL != RESOURCE_ACQUISITION
 *
 * Esta tabla esta DECLARADA y vacia. Su proposito es que ningun componente
 * posterior acquire un recurso sin decidir antes quien lo posee y quien lo
 * libera, en orden inverso. Hoy no se adquiere ninguno.
 *
 *   RECURSO         MODELADO   ADQUIRIDO_HOY   LIBERADO_HOY   DUEÑO FUTURO
 *   PCI DEVICE      SI         NO             NO             core de PCI
 *   PCI REGIONS     SI         NO             NO             el driver
 *   MMIO            SI         NO             NO             el driver
 *   IRQ             SI         NO             NO             el driver
 *   DMA             SI         NO             NO             el driver
 *
 * Ninguna de estas llamadas aparece en el codigo, y su ausencia es comprobada
 * por el test estatico. No se anaden "para cuando hagan falta".
 *
 * ============================================================================
 * INVARIANTES DE VIDA
 * ============================================================================
 *
 *   ANTES DE PROBE     no hay objeto. El driver no publica nada.
 *   PROBE EXITOSO      objeto asignado, inicializado, publicado. El driver es
 *                      dueno desde este instante.
 *   TRAS PROBE         solo se lee drvdata en remove().
 *   REMOVE             se recupera, se despublica, se destruye, se libera.
 *   TRAS REMOVE        no hay objeto.
 *
 * El driver NO depende de que el core deje drvdata a NULL antes de probe().
 * Esa semantica no es verificable en este arbol — las fuentes del driver core
 * no estan en el arbol de headers — y no se necesita: la correccion viene de
 * que solo se publica tras una asignacion exitosa, y de que solo se lee en
 * remove(), para el que el core solo invoca tras un probe que devolvio 0.
 */
struct rx550_target {
	struct pci_dev		*pdev;	/* del core, no del driver */
};

/* Recuperacion. Unico camino de lectura de drvdata en todo el driver. */
static inline struct rx550_target *rx550_target_of(struct pci_dev *pdev)
{
	return pci_get_drvdata(pdev);
}

#endif /* _RX550_PCIID_H */
