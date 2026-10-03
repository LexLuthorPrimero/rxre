/* SPDX-License-Identifier: GPL-2.0 */
/*
 * rx550_pciid — driver exclusivo para la RX 550 instalada en esta maquina.
 *
 *   TARGET = RX 550 INSTALADA EN ESTA COMPUTADORA
 *   SCOPE  = EXCLUSIVO
 *
 * Este driver no es generico. No es un driver para Polaris12, ni para GFX8,
 * ni para Radeon, ni para AMD. La tabla de identificacion acepta una sola
 * tupla, y el alcance declarado es una sola tarjeta. Esa restriccion tiene
 * prioridad sobre cualquier consideracion de reutilizacion o limpieza.
 *
 * COMPONENTE 1 — IDENTIDAD PCI
 *   id_table con exactamente una entrada: vendor 0x1002, device 0x699F.
 *   Tupla demostrada en el corpus, no heredada de un nombre:
 *     amdgpu_drv.c:2041  {0x1002, 0x699F, ..., CHIP_POLARIS12},
 *   El subsystem device (0x0B04) NO se usa como criterio: pci.ids lo declara
 *   como Radeon RX 560, es decir un codigo de modelo reutilizado dentro de la
 *   familia, no un identificador de placa. amdgpu tampoco lo usa.
 *
 * COMPONENTE 2 — LIFECYCLE EXPLICITO
 *   module_init -> pci_register_driver -> probe -> remove
 *   -> pci_unregister_driver -> module_exit
 *
 * COMPONENTE 3 — DEVICE OBJECT Y MODELO DE PROPIEDAD DE RECURSOS
 *   El objeto es un unico campo: el back-pointer a pci_dev. No copia la
 *   identidad, porque la identidad la posee el core y ya es legible por ahi.
 *   No se adquiere ningun recurso fisico. Ver la tabla en la cabecera.
 *
 * LO QUE ESTE ARCHIVO NO HACE, Y NO HARA HASTA QUE HAYA UN COMPONENTE QUE LO
 * JUSTIFIQUE: no habilita el dispositivo, no reserva regiones PCI, no mapea
 * BARs, no hace MMIO, no pide DMA, ni IRQ, ni doorbell, ni ejecuta la GPU.
 * Este driver no accede al hardware.
 *
 * Diseno: 08-ARQUITECTURA/designs/011-driver-baseline-primer-componente.md
 */

#include <linux/errno.h>
#include <linux/init.h>
#include <linux/kernel.h>
#include <linux/module.h>
#include <linux/pci.h>
#include <linux/slab.h>
#include <linux/types.h>

#include "rx550_pciid.h"

#define RX550_PCI_VENDOR_ID	0x1002
#define RX550_PCI_DEVICE_ID	0x699F

/*
 * TARGET_MATCH. Un unico par. Cualquier otro dispositivo no llega a probe.
 *
 * No hay PCI_ANY_ID, no hay otros device IDs, no hay otros vendors. Si en
 * algun momento hiciera falta ampliar esta tabla, eso es un cambio de alcance
 * del proyecto y hay que pararse y reportarlo, no editar la constante.
 */
static const struct pci_device_id rx550_pciid_ids[] = {
	{ PCI_DEVICE(RX550_PCI_VENDOR_ID, RX550_PCI_DEVICE_ID) },
	{ }
};
MODULE_DEVICE_TABLE(pci, rx550_pciid_ids);

/*
 * FIRMAS. Verificadas en los headers del kernel exacto, no de memoria:
 *
 *   /usr/src/kernels/7.1.3-200.nobara.fc44.x86_64/include/linux/pci.h
 *     :1025  int  (*probe)(struct pci_dev *dev,
 *                          const struct pci_device_id *id);
 *     :1026  void (*remove)(struct pci_dev *dev);
 *     :2314  void pci_set_drvdata(struct pci_dev *pdev, void *data)
 *                               -> dev_set_drvdata(&pdev->dev, data)
 *
 * probe() lleva dos argumentos en 7.1.3. La firma clasica de uno solo ya no
 * compila contra este kernel; el Makefile lo rechaza.
 */
static int rx550_pciid_probe(struct pci_dev *pdev,
			     const struct pci_device_id *id)
{
	struct rx550_target *target;

	/*
	 * El id_table ya filtro antes de llegar aqui. Se comprueba de nuevo
	 * porque TARGET_MATCH es el contrato del driver, no una consecuencia
	 * del filtrado: si esta condicion se cumple sola, el codigo de ahi
	 * esta mal y el fallo tiene que verse aqui y no tres capas mas abajo.
	 */
	if (id->vendor != RX550_PCI_VENDOR_ID ||
	    id->device != RX550_PCI_DEVICE_ID)
		return -ENODEV;

	/*
	 * Unico punto de fallo antes de que exista propiedad. Un unico
	 * recurso — el propio objeto — y un unico error. Si un componente
	 * posterior anade recursos, este es el sitio donde nace su unwind:
	 * liberar solo lo que se haya adquirido con exito, en orden inverso.
	 */
	target = kmalloc(sizeof(*target), GFP_KERNEL);
	if (!target)
		return -ENOMEM;

	/* Inicializacion total antes de publicar. Sin campos sin valor. */
	target->pdev = pdev;

	/* Publicacion. A partir de aqui el driver es dueno del objeto. */
	pci_set_drvdata(pdev, target);

	/*
	 * La identidad se lee del core, no del objeto: no esta copiada en
	 * ningun sitio. Este log es la ultima vez que el driver la consulta.
	 */
	pci_info(pdev,
		 "bound: %04x:%04x subsys %04x:%04x rev %02x\n",
		 pdev->vendor, pdev->device, pdev->subsystem_vendor,
		 pdev->subsystem_device, pdev->revision);

	return 0;
}

/*
 * Simetrico con probe(), en orden inverso al de adquisicion.
 *
 * El kernel solo llama a remove() si probe() devolvio 0, pero no se asume:
 * un remove() que no encuentre estado no hace nada y no libera de mas.
 */
static void rx550_pciid_remove(struct pci_dev *pdev)
{
	struct rx550_target *target = rx550_target_of(pdev);

	if (!target)
		return;

	/*
	 * Invariante del objeto: el back-pointer tiene que ser este mismo
	 * dispositivo. Si no lo fuera, el objeto publication no es el que
	 * remove cree, y liberarlo seria liberar el estado de otro.
	 */
	if (target->pdev != pdev) {
		pci_err(pdev, "drvdata does not belong to this device\n");
		return;
	}

	pci_info(pdev, "unbound: %04x:%04x\n", pdev->vendor, pdev->device);

	/* Despublicar antes de destruir: el estado deja de ser alcanzable. */
	pci_set_drvdata(pdev, NULL);

	/* Destruir y liberar. Unica propiedad, liberada una sola vez. */
	kfree(target);
}

/*
 * Un unico struct pci_driver, correspondiente al target. Sin tabla de ASICs,
 * sin dispatch por familia, sin ops de segundo nivel.
 */
static struct pci_driver rx550_pciid_driver = {
	.name		= "rx550_pciid",
	.id_table	= rx550_pciid_ids,
	.probe		= rx550_pciid_probe,
	.remove		= rx550_pciid_remove,
};

static int __init rx550_pciid_init(void)
{
	int r;

	r = pci_register_driver(&rx550_pciid_driver);
	if (r) {
		pr_err("rx550_pciid: pci_register_driver failed (%d)\n", r);
		return r;
	}

	pr_info("rx550_pciid: registered for %04x:%04x\n",
		RX550_PCI_VENDOR_ID, RX550_PCI_DEVICE_ID);
	return 0;
}

static void __exit rx550_pciid_exit(void)
{
	/* El core llama a remove() por cada dispositivo enlazado antes de
	 * volver de aqui. Unload no necesita reproducir esa parte. */
	pci_unregister_driver(&rx550_pciid_driver);
	pr_info("rx550_pciid: unregistered\n");
}

/* Explicitos, no module_pci_driver(): el ciclo de vida es el objeto del
 * componente 2 y tiene que poder leerse, no deducirse de una macro. */
module_init(rx550_pciid_init);
module_exit(rx550_pciid_exit);

MODULE_AUTHOR("RX550-INVESTIGACION");
MODULE_DESCRIPTION("RX550 target board, 0x1002:0x699F — identity + lifecycle + object");
MODULE_LICENSE("GPL");
MODULE_VERSION("0.3");
