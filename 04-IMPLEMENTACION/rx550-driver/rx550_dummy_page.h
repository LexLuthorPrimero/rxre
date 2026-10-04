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
/*  MEDIDO 2026-10-04:  este codigo es NUEVO.  rx550_dummy_page_pfn() hacia
 *  `dma_pa >> 12` sin comprobar nada, y el resultado truncado es un
 *  PHYSICAL_PAGE_NUMBER PLAUSIBLE Y EQUIVOCADO.  Su gemelo
 *  rx550_pdb0_encode() ya rechazaba en vez de truncar (rx550_pdb0.c:18-21), y
 *  el predicado rx550_pa_representable() ya existia (rx550_spaces.h:88) sin que
 *  este camino lo usara.  Una guarda presente en un lado y ausente en el otro.
 *
 *  En esta maquina el defecto es TEORICO:  la RAM acaba en 34 bits
 *  (0x330000000), luego una PA por encima de 40 no existe.  Se corrige igual,
 *  porque una funcion que acepta en silencio un valor que no puede representar
 *  es un defecto con o sin hardware que lo alcance.
 */
#define RX550_DUMMY_ERR_NO_PA		(-4)	/* la PA no cabe en 40 bits   */

/* ── LA MASCARA DMA, EN NUMEROS ──────────────────────────────────────────────
 *
 * QUE ES
 *   El techo de direcciones de BUS que el device puede recibir por DMA.  En
 *   esta maquina el techo del SILICIO es 1 TiB, pero el device DMA de una
 *   Polaris12 no lo es: el GART es de 40 bits de direccion fisica, y por eso
 *   el techo que se le pide al kernel es de 40 bits y no mas.
 *
 * POR QUE 40 Y NO 64, MEDIDO EN EL CORPUS
 *   gmc_v8_0.c:1133  adev->gmc.mc_mask       = 0xffffffffffULL   -- 40 bit MC
 *   gmc_v8_0.c:1134  adev->gmc.pte_addr_mask = 0x000000FFFFFFF000 -- 40 bit PA
 *   gmc_v8_0.c:1136  dma_set_mask_and_coherent(adev->dev, DMA_BIT_MASK(40));
 *   gmc_v8_0.c:1137-1140  if (r) { pr_warn("No suitable DMA available\n");
 *                                return r; }      <-- Gate DURO: sin mascara no hay device
 *   El registro donde acaba esta pagina es un PHYSICAL_PAGE_NUMBER de 28 bits
 *   (gmc_v8_0.c:890-891 y :920-921), alimentado por un PA de 40.  Una mascara
 *   de 64 noaria mejor nada: solo permitiria PAs que el GART no puede
 *   representar, que es exactamente lo que rx550_dummy_page_pfn() rechaza.
 *
 * LA MASCARA DMA NO ES RX550_PA_MASK, Y CONFUNDIRLAS ES UN ERROR DE LA FAMILIA
 *   rx550_spaces.h:51  RX550_PA_MASK = 0x000000FFFFFFF000
 *   esta aqui              RX550_DMA_MASK = 0x000000FFFFFFFFFF
 *   4 KiB de diferencia.  La mascara DMA se compara con `addr + size - 1`
 *   (include/linux/dma-direct.h:130 y :138), o sea con una direccion de BYTES
 *   que todavia lleva dentro los 12 bits bajos del offset.  Si sederivase una
 *   de la otra, una PA normal de pagina completa como 0x12345000 quedaria
 *   FUERA:  es el mismo error que ya se corrigio en pfn(), donde comparar
 *   `dma_pa & ~RX550_PA_MASK` rechazaba las PAs de todos los dias porque
 *   ~RX550_PA_MASK tambien senala los 12 bits bajos (rx550_dummy_page.c:132-140).
 *
 * MEDIDO 2026-10-04 · POR QUE ESTO HACE FALLAR, Y NO MERAMENTE LIMITAR
 *   El kernel arranca con una mascara de 32 bits para todo PCI:
 *       drivers/pci/probe.c:2047-2051  el kernel asume 32 bits ("Assume 32-bit PCI")
 *                                       dev->dma_mask = 0xffffffff;
 *       drivers/pci/probe.c:2741  dev->dev.dma_mask = &dev->dma_mask;
 *       drivers/pci/probe.c:2743  dev->dev.coherent_dma_mask = 0xffffffffull;
 *   Y una pagina de GFP_KERNEL sale de ZONE_NORMAL, que en esta maquina empieza
 *   en 4 GiB:
 *       MEDIDO /proc/zoneinfo:  zone DMA32 spanned 1044480 pag desde pfn 0x100000,
 *                               zone Normal spanned 2293248 pag  =>  RAM hasta
 *                               pfn 0x330000, o sea 0x330000000, bit 34.
 *   El cruce:
 *       kernel/dma/mapping.c:191-204   dma_map_page_attrs -> dma_map_phys
 *       kernel/dma/mapping.c:120-153   sin IOMMU -> directo
 *       include/linux/dma-direct.h:138 end <= min_not_zero(*dev->dma_mask, bus_dma_limit)
 *                                       con 0xffffffff y end >= 0x100000FFF -> FALSE
 *       kernel/dma/direct.h:112-119     !dma_capable -> si hay swiotlb, bounce; si no, error
 *       kernel/dma/direct.h:130-135     err_overflow -> DMA_MAPPING_ERROR
 *   MEDIDO que NO hay bounce en esta maquina:  is_swiotlb_active() vale
 *   io_tlb_default_mem.nslabs (kernel/dma/swiotlb.c:1649-1654), y el pool solo se
 *   reserva si `addressing_limit` (swiotlb.c:353-363); en x86 eso vale lo que
 *   valga x86_swiotlb_enable (arch/x86/kernel/pci-dma.c:98-109), que aqui es
 *   falso:  sin Xen MEDIDO (/sys/hypervisor/type ausente, /proc/xen ausente) y
 *   sin cifrado de memoria MEDIDO (/sys/kernel/mm/memory_encryption ausente).
 *   O sea:  con la mascara por defecto, el mapa de esta pagina FALLA.  No es
 *   que se quede corto, es que rx550_dummy_page_init() devuelve NO_MAP y no hay
 *   pagina de relleno, y con ella no se completa la secuencia del contexto 0.
 *
 *   DMA_ATTR_SKIP_CPU_SYNC NO cambia nada de esto.  MEDIDO: solo salta el
 *   arch_sync_dma_for_device() (kernel/dma/direct.h:122-127).  La decision de
 *   rebotar o de fallar esta DOS LINEAS ARRIBA (direct.h:112-119), y no mira el
 *   atributo.  "Los bytes nunca se copian" es una consecuencia de tener 40 bits,
 *   no de pedir SKIP_CPU_SYNC.
 *
 * Y ESTO ES UNA AFIRMACION SOBRE LA EJECUCION, NO SOBRE EL TEXTO
 *   MEDIDO que dma_mask_bits == 40 en esta maquina no demuestra que el default
 *   sea 40:  es el VALOR DE bits ENCENDIDOS de la mascara actual, no el ancho
 *   del bus.  drivers/pci/pci-sysfs.c:400-407 lo dice:
 *       return sysfs_emit(buf, "%d\n", fls64(pdev->dma_mask));
 *   MEDIDO que el default es 32 (probe.c:2051) y que el valor actual de 40 lo
 *   puso el driver de referencia, no el hardware:
 *       amdgpu_drv.c:2415   adev->dev = &pdev->dev;   <-- el mismo struct device
 *       gmc_v8_0.c:1136     dma_set_mask_and_coherent(adev->dev, DMA_BIT_MASK(40))
 *   MEDIDO en /sys para 0000:01:00.0:  dma_mask_bits = 40,
 *   consistent_dma_mask_bits = 40, driver = amdgpu.  Los DOS a 40 son la
 *   consecuencia de que ese camino escribe los dos sitios:  probe.c:2741 hace
 *   que *dev->dma_mask sea pdev->dma_mask, y mapping.c:925 / :943 escriben ahi.
 *   Si el day el amdgpu y el default volviera a ser 0xffffffff, fls64 daria 32.
 */
#define RX550_DMA_MASK_BITS		RX550_PA_BITS	/* 40: el GART */
#define RX550_DMA_MASK			UINT64_C(0x000000FFFFFFFFFF)

/* El default de PCI, MEDIDO en probe.c:2051 y :2743.  Se escribe aqui para que
 * el test pueda comprobar en userspace lo que el kernel haria con el. */
#define RX550_DMA_MASK_DEFAULT_BITS	32u
#define RX550_DMA_MASK_DEFAULT		UINT64_C(0x00000000FFFFFFFF)

/* Cuantos bits tiene una mascara.  Sin libfls:  esta cabecera compila bajo
 * kernel y bajo userspace, y fls()/fls64() no existen en los dos sitios. */
static inline uint32_t rx550_dma_mask_bits_of(uint64_t mask)
{
	uint32_t n = 0;

	while (mask != 0) {
		n += (uint32_t)(mask & UINT64_C(1));
		mask >>= 1;
	}
	return n;
}

/* La mascara cubre ESTA direccion de bytes.  Mismo comparador que el kernel,
 * solo que aqui no hay size:  la mascara es de direccion, el size lo mete el
 * que llama (include/linux/dma-direct.h:130). */
static inline bool rx550_dma_mask_covers(uint64_t mask, uint64_t pa)
{
	return pa <= mask;
}

/* Una mascara mas ancha que el GART no compra nada y si deja pasar PAs que el
 * registro no puede representar.  Este es el invariante que ata la mascara DMA
 * con rx550_dummy_page_pfn(). */
static inline bool rx550_dma_mask_fits_gart(uint32_t mask_bits)
{
	return mask_bits <= RX550_PA_BITS;
}

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
 * gmc_v8_0.c:890-891,
 *     WREG32(mmVM_CONTEXT0_PROTECTION_FAULT_DEFAULT_ADDR,
 *             (u32)(adev->dummy_page_addr >> 12));
 * y otra vez en :920-921 para el contexto 1;  el ancho del campo esta en
 * gmc_8_1_sh_mask.h.  Una funcion que devolviera la direccion entera y que el
 * llamador tiene que desplazarlo seria el error mas caro de esta lista:
 * escribiria un numero plausible en un registro de paginas.
 *
 * MEDIDO 2026-10-04:  (QUOTED-DEFECT) esta cita decia `gmc_8_0.c:889`, y eran las dos cosas
 * mal a la vez.  El fichero se llama gmc_v8_0.c (con V), y la linea 889 es la
 * de PAGE_TABLE_BASE_ADDR:  la escritura de PROTECTION_FAULT_DEFAULT_ADDR
 * empieza en la 890 y su `>> 12` esta en la 891.  Una cita que no abre es una
 * afirmacion que no se puede comprobar, y una que abre en la linea de al lado
 * es peor:  parece comprobada y no lo esta. */
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

/* ── EL INFORME DE LA MASCARA ───────────────────────────────────────────────
 *
 *  Por que un struct y no solo un int:  la pregunta de este nodo no era "puedo
 *  fijar la mascara", sino "que cambia para el resto del driver si la fijo".
 *  Sin el antes y el despues, la respuesta a eso es una frase y no una medida.
 *  Todo lo de aqui son VALORES LEIDOS del device, nunca supuestos.
 *
 *  required        dma_get_required_mask()  -> el ancho minimo para direccionar
 *                  toda la RAM.  En esta maquina, 34 bits (MEDIDO: ver la nota
 *                  de la mascara, la zona Normal acaba en el bit 34).
 *  limited_*       dma_addressing_limited() -> la respuesta del kernel a "¿la
 *                  mascara da para toda la memoria del sistema?".  Es el
 *                  discriminante que de verdad importa, y lo define el kernel:
 *                  kernel/dma/mapping.c:961-976.
 */
struct rx550_dma_mask_report {
	uint64_t	mask_before;		/* dma_get_mask() ANTES        */
	uint64_t	mask_after;		/* dma_get_mask() DESPUES      */
	uint64_t	coherent_after;		/* dev->coherent_dma_mask      */
	uint64_t	required;		/* dma_get_required_mask()     */
	uint32_t	mask_bits;		/* bits de mask_after         */
	uint32_t	required_bits;		/* bits de required            */
	int		streaming_rc;		/* lo que devolvio dma_set_mask */
	int		coherent_rc;		/* ... y dma_set_coherent_mask  */
	int		limited_before;
	int		limited_after;
};

/* Fija RX550_DMA_MASK en las dos mascaras del device.  Idempotente:  repetirla
 * con el mismo valor reescribe lo mismo (mapping.c:925 y :943) y no cambia el
 * estado.  QUE ESTO CAMBIA PARA EL RESTO DEL DRIVER, MEDIDO:
 *
 *   ANTES   mask = 0x00000000FFFFFFFF (32 bits, probe.c:2051)
 *           dma_addressing_limited() == true
 *           dma_map_page_attrs() de una pagina de GFP_KERNEL devuelve
 *           DMA_MAPPING_ERROR  ->  rx550_dummy_page_init() == RX550_DUMMY_ERR_NO_MAP
 *           y no hay pagina de relleno:  el contexto 0 se queda sin
 *           mmVM_CONTEXT0_PROTECTION_FAULT_DEFAULT_ADDR.
 *
 *   DESPUES mask = 0x000000FFFFFFFFFF (40 bits)
 *           dma_addressing_limited() == false
 *           dma_map_page_attrs() devuelve la PA tal cual, sin rebote y sin
 *           copia, y rx550_dummy_page_pfn() puede representarla.
 *
 * Devuelve 0 solo si mask_after == RX550_DMA_MASK.  Si el kernel no puede dar
 * 40 bits devuelve su propio codigo (-EIO, mapping.c:922), sin inventar otro:
 * un numero que no viene del kernel no se puede comparar con el de amdgpu.
 *
 * `out` es OBLIGATORIO, y a proposito:  un informe que se pide explicitamente y
 * no se puede escribir no puede seguir siendo opcional en silencio, porque
 * entonces la funcion puede devolver 0 sin que nadie sepa lo que habia antes.  Con
 * `out == NULL` devuelve -EINVAL, que es lo que es:  un argumento malo.  Si lo
 * que se quiere es solo fijar la mascara y no mirar el antes, la funcion tiene
 * que un informe igual:  no hay atajo, y el que no lo quiera puede mirar el
 * informe.
 */
int rx550_dummy_kernel_dma_mask(void *ctx, struct rx550_dma_mask_report *out);

#endif

#endif /* RX550_DUMMY_PAGE_H */