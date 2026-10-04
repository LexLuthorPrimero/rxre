/* SPDX-License-Identifier: GPL-2.0 */
/*
 * rx550_dummy_page.h — la pagina que el driver rellena cuando un hueco de la
 * GART se queda vacio.
 *
 *   TARGET = RX 550 instalada en esta maquina
 *   SCOPE  = EXCLUSIVO
 *
 * QUE ES
 *   Una sola pagina de RAM del sistema, mapeada por DMA en las DOS direcciones.
 *   Su direccion fisica va a mmVM_CONTEXT{0,1}_PROTECTION_FAULT_DEFAULT_ADDR
 *   >> 12, y es lo que el hardware escribe cuando una tabla de paginas
 *   invalida una entrada.
 *
 * POR QUE EXISTE Y POR QUE NO ES UN PARAMETRO QUE SE PASA
 *
 *   gmc_v8_0_gart_enable() la usa en dos sitios, L889 y L921:
 *       WREG32(mmVM_CONTEXT0_PROTECTION_FAULT_DEFAULT_ADDR,
 *              (u32)(adev->dummy_page_addr >> 12));
 *       WREG32(mmVM_CONTEXT1_PROTECTION_FAULT_DEFAULT_ADDR,
 *              (u32)(adev->dummy_page_addr >> 12));
 *   y rx550_vmid0_regs_build() la recibe como PARAMETRO, que es correcto:  una
 *   funcion que construye numeros no deberia pedir memoria.
 *
 *   Lo que falta en el driver propio es el PRODUCTOR de ese parametro.  No hay
 *   nada en el componente que lo produzca, y sin el no hay forma de completar la
 *   secuencia del contexto 0.
 *
 * POR QUE NO SE USA TTM, Y POR QUE ESO ESTA BIEN
 *
 *   La referencia usa la pagina global de TTM:
 *       amdgpu_gart.c:76   struct page *dummy_page = ttm_glob.dummy_read_page;
 *       amdgpu_gart.c:81   adev->dummy_page_addr = dma_map_page_attrs(
 *                               &adev->pdev->dev, dummy_page, 0, PAGE_SIZE,
 *                               DMA_BIDIRECTIONAL, DMA_ATTR_SKIP_CPU_SYNC);
 *
 *   O sea:  TTM aporta el marco, y el mapa DMA lo hace amdgpu igual.  Para
 *   OUR driver, arrastrar TTM por una sola pagina seria dejar una dependencia
 *   entera —con su DRM, su asignador y su”— a cambio de un `alloc_page`.  Se
 *   hace el alloc_page, y el mapa DMA es el mismo que usa la referencia.
 *
 *   La pagina es de SOLO LECTURA para la GPU en el sentido de que no se escribe
 *   nunca, pero el mapa es BIDIRECCIONAL porque el hardware hace memcpy de
 *   origen y destino indistintos y con solo lectura fallaria.  No es una
 *   distincion academica:  la referencia pide DMA_BIDIRECTIONAL y pedir menos es
 *   cambiar el contrato.
 *
 * LA FORMA:  HAL INYECTADO, COMO EL RESTO
 *
 *   map/unmap entran por punteros a funcion, igual que rx550_vram_alloc_fn.  No
 *   para hacer la cabecera portable:  para que el contrato se pueda PROBAR en
 *   userspace sin GPU, que es la unica forma de que un test de esto signifique
 *   algo.  Un init que solo se puede probar con la GPU delante no se prueba.
 */
#ifndef RX550_DUMMY_PAGE_H
#define RX550_DUMMY_PAGE_H

#include "rx550_spaces.h"

#ifdef __KERNEL__
#include <linux/types.h>
#else
#include <stdint.h>
#include <stdbool.h>
#include <stddef.h>
#endif

/* ── HAL ────────────────────────────────────────────────────────────────────
 *
 *  Las dos operaciones que hacen falta, y nada mas.  `alloc_page` se llama una
 *  vez y devuelve un puntero opaco;  el que lo libera es el mapa, porque una
 *  pagina DMA mapeada se LIBERA con dma_free, no con __free_page.  Por eso no
 *  hay un unmap de pagina suelta:  unmap Deshace el mapeo, y un free aparte
 *  deshace la pagina, y confundirlos es como se fuga memoria con barrera. */
typedef int  (*rx550_dummy_map_fn)(void *ctx, void **out_cpu_va,
				   uint64_t *out_dma_pa);
typedef void (*rx550_dummy_unmap_fn)(void *ctx, void *cpu_va, uint64_t dma_pa);

struct rx550_dummy_ops {
	rx550_dummy_map_fn	map;
	rx550_dummy_unmap_fn	unmap;
	void			*ctx;
};

/* ── ESTADO ─────────────────────────────────────────────────────────────── */
enum rx550_dummy_state {
	RX550_DUMMY_ABSENT = 0,
	RX550_DUMMY_HELD,
	RX550_DUMMY_RELEASED
};

struct rx550_dummy_page {
	enum rx550_dummy_state	state;
	uint64_t		dma_pa;	/* PA del sistema, la que va al registro */
	void		       *cpu_va;	/* puntero del kernel, para deshacer */
	struct rx550_dummy_ops	ops;	/* la HAL con la que se/mapearon */
	bool			have_ops;
};

#define RX550_DUMMY_ERR_INCONSISTENT	(-1)
#define RX550_DUMMY_ERR_NO_MAP		(-2)	/* la HAL fallo               */
#define RX550_DUMMY_ERR_STATE		(-3)	/* transicion ilegal          */

/* ABSENT -> HELD.  Devuelve el PA por `out_pa` para que el llamante no tenga
 * que leer el struct y poder comprobar el estado sin acoplar al struct. */
int rx550_dummy_page_init(struct rx550_dummy_page *p,
			  const struct rx550_dummy_ops *ops,
			  struct rx550_system_pa *out_pa);

/* HELD -> RELEASED.  Idempotente sobre ABSENT y RELEASED, porque remove() va a
 * llamar a esto en un camino de error y no puede que eso sea un segundo fallo. */
int rx550_dummy_page_fini(struct rx550_dummy_page *p);

/* El PA, en el tipo del sistema.  No un uint64_t desnudo:  la misma direccion
 * con otro nombre significa otra cosa, y esa es la trampa que todo el
 * componente esta hecho para cerrar. */
int rx550_dummy_page_pa(const struct rx550_dummy_page *p,
			struct rx550_system_pa *out);

/* El numero de pagina, que es lo que va al registro:  PA >> 12.
 *
 * Y AQUI ESTA LA TRAMPA DE ESTA DIRECCION:  el registro no lleva una
 * direccion, lleva un PHYSICAL_PAGE_NUMBER de 28 bits.  El corpus lo dice en
 * gmc_8_0.c:889, `(u32)(adev->dummy_page_addr >> 12)`, y el ancho del campo en
 * gmc_8_1_sh_mask.h.  Una funcion que devolviera la direccion entera y que el
 * llamador tiene que desplazarlo seria el error mas caro de esta lista:
 * escribiria un numero plausible en un registro de paginas. */
int rx550_dummy_page_pfn(const struct rx550_dummy_page *p, uint32_t *out);

/* El valor exacto que va a mmVM_CONTEXT{0,1}_PROTECTION_FAULT_DEFAULT_ADDR. */
int rx550_dummy_page_fault_reg(const struct rx550_dummy_page *p,
			       uint32_t *out);

/* ── LA HAL DE KERNEL, si se quiere la de verdad ──────────────────────────
 *
 *  expuesta aparte y no usada por las funciones de arriba:  quien quiera la de
 *  kernel la pide explicitamente, y asi el test de userspace no puede acabarse
 *  enlazando la de kernel por accidente. */
#ifdef __KERNEL__
#include <linux/dma-mapping.h>
#include <linux/device.h>

/*  El ctx es un `struct device *`, NO un `struct pci_dev *`.
 *
 *  La API de DMA del kernel toma device, y la referencia pasa exactamente lo
 *  mismo:  amdgpu_gart.c:81, `dma_map_page_attrs(&adev->pdev->dev, ...)`.
 *  La primera version de esto tomaba pci_dev y el kernel no lo compila:  tres
 *  -Wincompatible-pointer-types y un -Wint-conversion, que son elavor que
 *  kbuild pone cuando la firma esta mal.  La firma la dicta la API, no la
 *  conveniencia de quien escribe. */
int rx550_dummy_kernel_map(void *ctx, void **out_cpu_va, uint64_t *out_dma_pa);
void rx550_dummy_kernel_unmap(void *ctx, void *cpu_va, uint64_t dma_pa);
#endif

#endif /* RX550_DUMMY_PAGE_H */