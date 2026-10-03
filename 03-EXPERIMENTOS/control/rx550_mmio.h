/* SPDX-License-Identifier: GPL-2.0 */
/*
 * rx550_mmio.h — contrato de acceso al registro MMIO.  NO accede al hardware.
 *
 * LA TRAMPA DE UNIDADES
 *   Un offset de registro no es un offset en bytes.  En el driver de
 *   referencia el indice se multiplica por 4 antes de indexar el mapping:
 *
 *     amdgpu_reg_access.c:371   if ((reg * 4) < adev->rmmio_size)
 *     amdgpu_reg_access.c:378       readl(base + (reg * 4))
 *
 *   Usar el indice como si ya fuera el offset produce un ACCESO VALIDO DENTRO
 *   DE LA BAR que golpea otro registro, y devuelve un numero plausible.  No
 *   falla: miente.
 *
 *   Concretamente, con rmmio_size = 0x40000:
 *     mmCP_RB0_RPTR  indice 0x21c0  ->  offset real 0x8700
 *     usado como offset             ->  0x21c0, otro registro
 *
 *   De ahi que este modulo exponga siempre el indice y deje la conversion
 *   explicita, en un solo sitio.
 *
 * EVIDENCIA DEL LIMITE
 *   rmmio_size = 0x40000, por identidad de expresion entre
 *   pci-sysfs.c:1248 (res_attr->size) y amdgpu_device.c:3814
 *   (adev->rmmio_size = pci_resource_len(pdev, 5)).
 */
#ifndef RX550_MMIO_H
#define RX550_MMIO_H

#include "rx550_spaces.h"

/* ── HARDWARE_REQUIREMENT ──────────────────────────────────────────────── */
#define RX550_BAR_INDEX		5u
#define RX550_MMIO_SIZE		UINT64_C(0x40000)
#define RX550_REG_WIDTH		4u			/* bytes por registro */

/* registro: indice, no offset */
struct rx550_reg {
	uint32_t index;
};

/* offset: bytes dentro de la BAR */
struct rx550_mmap_offset {
	uint64_t bytes;
};

static inline struct rx550_reg rx550_reg_make(uint32_t index)
{
	struct rx550_reg r;
	r.index = index;
	return r;
}

static inline struct rx550_mmap_offset rx550_reg_offset(struct rx550_reg r)
{
	struct rx550_mmap_offset o;
	o.bytes = (uint64_t)r.index * RX550_REG_WIDTH;
	return o;
}

/* ¿el registro cae dentro de la ventana mapeada?  Si no, el acceso va por la
 * via indirecta y este modulo no la cubre. */
static inline bool rx550_reg_in_window(struct rx550_reg r)
{
	return rx550_reg_offset(r).bytes + RX550_REG_WIDTH <= RX550_MMIO_SIZE;
}

static inline bool rx550_mmap_offset_aligned(struct rx550_mmap_offset o)
{
	return (o.bytes % RX550_REG_WIDTH) == 0;
}

/* El limite superior del registro indexable. */
#define RX550_LAST_REG_INDEX	((uint32_t)((RX550_MMIO_SIZE / RX550_REG_WIDTH) - 1))

/* ─────────────────────────────────────────────────────────────────────────────
 * EL MAPA DE LA BAR
 *
 * Añadido por GPUVM.MMIO_ACCESSOR_INTEGRATION.  Lo que hay antes de esta linea
 * es la CONTRACTA, y estaba completa y verificada:  el indice, la conversion
 * a offset, y la comprobacion de ventana.  Lo que faltaba era el objeto sobre
 * el que se aplica esa conversion, y eso es lo de aqui.
 *
 * Y NO HAY UNA SEGUNDA POLITICA DE DIRECCIONAMIENTO.  La conversion indice ->
 * offset sigue siendo rx550_reg_offset(), y la comprobacion de ventana sigue
 * siendo rx550_reg_in_window(), que son las dos de arriba y no se tocan.  Este
 * fichero no las reescribe, no las envuelve y no las duplica:  anade un
 * receptor y nada mas.
 *
 * POR QUE `base` ES uintptr_t Y NO void*
 *
 * Porque el tipo de la base depende de donde se compila —__iomem en el kernel,
 * un puntero normal en userspace para poder probar el camino de acceso sin
 * hardware— y un struct que lo guarde tiene que compilar en los dos.  Lo que
 * el mapa NO hace es leer ni escribir:  eso lo hace el accessor, que es donde
 * viven readl y writel.
 * ───────────────────────────────────────────────────────────────────────────── */
struct rx550_mmio_map {
	uintptr_t	base;		/* base de la BAR5 ya asignada */
	uint64_t	size;		/* bytes mapeados, RX550_MMIO_SIZE */
	bool		mapped;		/* hay algo mapeado detras de base */
};

/* Un mapa vacio.  Sin `mapped` a true, ningun acceso procede. */
static inline struct rx550_mmio_map rx550_mmio_map_empty(void)
{
	struct rx550_mmio_map m;

	m.base = 0;
	m.size = 0;
	m.mapped = false;
	return m;
}

/* Y uno con base.  El TAMANO NO SE INVENTA:  tiene que ser el que el
 * dispositivo declara para BAR5, y rx550_mmio_size_ok() lo comprueba. */
static inline struct rx550_mmio_map rx550_mmio_map_make(uintptr_t base,
							uint64_t size)
{
	struct rx550_mmio_map m;

	m.base = base;
	m.size = size;
	m.mapped = (base != 0u);
	return m;
}

/* ¿El tamaño mapeado sirve para el contrato de la BAR?
 *
 * RX550_MMIO_SIZE es el tamaño declarado de BAR5.  Un mapa mas pequeño no
 * puede contener el ultimo registro, y uno mas grande significaria que el
 * tamaño real del recurso no es el que se cree.  Las dos cosas son un fallo de
 * la integracion, y se rechazan aqui y no en el primer acceso, que ya habria
 * escrito en hardware. */
static inline bool rx550_mmio_size_ok(uint64_t size)
{
	return size >= RX550_MMIO_SIZE;
}

/* El offset de un registro DENTRO del mapa, o la razon por la que no.
 *
 * Y LA COMPROBACION DE VENTANA SE APLICA AL OFFSET, NO AL INDICE.  Es lo mismo,
 * porque rx550_reg_in_window() ya trabaja sobre el offset, pero decirlo aqui
 * evita la lectura de que hay dos comprobaciones:  no las hay.
 */
static inline bool rx550_mmio_map_in_window(const struct rx550_mmio_map *m,
					    struct rx550_reg r)
{
	if (!m || !m->mapped)
		return false;
	if (!rx550_reg_in_window(r))
		return false;
	return rx550_reg_offset(r).bytes + RX550_REG_WIDTH <= m->size;
}

#endif /* RX550_MMIO_H */
