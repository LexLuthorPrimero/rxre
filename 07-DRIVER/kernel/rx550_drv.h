/* SPDX-License-Identifier: GPL-2.0 */
/*
 * rx550_drv.h -- estado por dispositivo del driver RX 550, etapa 1.
 *
 * Separate de rx550_drv.c para que el futuro ABI con userspace no arrastre la
 * tabla de barras ni la identidad interna.
 *
 * ESTRUCTURA
 *
 * struct drm_device va EMBEBIDO, no en un puntero. Es la forma que el propio
 * core de DRM espera: devm_drm_dev_alloc() recibe el tipo contenedor y el
 * desplazamiento del miembro, y devuelve el struct drm_device ya inicializado
 * dentro. Con un puntero aparte habria dos objetos, dos ciclos de vida y dos
 * caminos de error, sin ninguna ventaja.
 */

#ifndef _RX550_DRV_H_
#define _RX550_DRV_H_

#include <drm/drm_device.h>
#include "rx550_mmio.h"
#include <linux/types.h>

/* PCI_STD_NUM_BARS, en uapi/linux/pci_regs.h:37. Se cita el origen para que
 * cambiar el valor no parezca una decision de diseno. */
#define RX550_NUM_BARS		6

/* Lo que el core de PCI ya normalizo en un resource. */
enum rx550_bar_kind {
	RX550_BAR_ABSENT = 0,	/* no implementado por el hardware */
	RX550_BAR_MEM,		/* memoria */
	RX550_BAR_IO,		/* puerto E/S */
};

struct rx550_bar_info {
	u64	start;		/* fisica, tal como el bus la asigno */
	u64	end;		/* inclusivo */
	u64	len;		/* end - start + 1 */
	u8	bar;		/* indice, 0..5 */
	u8	kind;		/* enum rx550_bar_kind */
	u8	is_64bit;
	u8	is_prefetchable;
};

/*
 * Identidad observada. Solo PCI: no hay ASIC id, no hay revision de silicio,
 * no hay lectura de registro. Lo que no se puede leer sin hardware no se
 * declara como campo.
 */
struct rx550_identity {
	u16	vendor;
	u16	device;
	u16	subsystem_vendor;
	u16	subsystem_device;
	u32	class;		/* pdev->class: 24 bits, ya combinado por el core */
	u8	revision;
};

struct rx550_bdf {
	u16	domain;
	u8	bus;
	u8	dev;
	u8	fn;
};

struct rx550_device {
	struct drm_device	drm;	/* debe ir primero: ver arriba */
	struct pci_dev		*pdev;
	struct rx550_identity	id;
	struct rx550_bdf		bdf;
	struct rx550_bar_info	bars[RX550_NUM_BARS];
	u32			bar_present;	/* numero de BARs implementados */

	/*
	 * La ventana de registros. El mapa va aparte del estado porque el
	 * estado debe poder describirse SIN haber mapeado nada: rx_info lo
	 * imprime, y un lector tiene que poder ver que el mapa no existe y por
	 * que antes de que exista.
	 *
	 * mmio_base es NULL mientras el contrato no se cierre, que es lo que
	 * pasa hoy: ver rx550_mmio.h, NOT_IN_CORPUS en RX550_MMIO_BAR.
	 */
	struct rx550_mmio_info	mmio;
	void			*mmio_base;
	int			mmio_mapped;
};

#endif /* _RX550_DRV_H_ */
