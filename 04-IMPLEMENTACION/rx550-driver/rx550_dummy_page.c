/* SPDX-License-Identifier: GPL-2.0 */
/*
 * rx550_dummy_page.c — la pagina de relleno de la GART.
 *
 *   TARGET = RX 550 instalada en esta maquina
 *   SCOPE  = EXCLUSIVO
 *
 * Sin MMIO, sin ring, sin hardware.  Solo el estado y el contrato de la HAL.
 * Que esa direccion llegue a un registro es asunto de quien la escriba.
 *
 * COMPATIBILIDAD KBUILD:  mismo split que rx550_spaces.h.  La HAL de kernel usa
 * dma_map_page() / dma_unmap_page(), que solo existen en el kernel;  la de
 * userspace la inyecta el test.  Este .c compila de las dos formas.
 */
#include "rx550_dummy_page.h"

/* ── ESTADO ─────────────────────────────────────────────────────────────── */

static void rx550_dummy_reset(struct rx550_dummy_page *p)
{
	p->state = RX550_DUMMY_ABSENT;
	p->dma_pa = 0;
	p->cpu_va = NULL;
}

int rx550_dummy_page_init(struct rx550_dummy_page *p,
			  const struct rx550_dummy_ops *ops,
			  struct rx550_system_pa *out_pa)
{
	void *cpu = NULL;
	uint64_t pa = 0;
	int rc;

	if (p == NULL || ops == NULL || out_pa == NULL)
		return RX550_DUMMY_ERR_INCONSISTENT;
	if (ops->map == NULL || ops->unmap == NULL)
		return RX550_DUMMY_ERR_INCONSISTENT;
	/* Un doble init sin fini no seacepta.  La aceptacion "silenciosa"
	 * devolveria OK y quien llama creeria que tiene una pagina cuando tiene
	 * la de la llamada anterior, con un mapa DMA que no es suyo. */
	if (p->state == RX550_DUMMY_HELD)
		return RX550_DUMMY_ERR_STATE;

	rc = ops->map(ops->ctx, &cpu, &pa);
	if (rc != 0 || cpu == NULL || pa == 0) {
		/* La HAL fallo.  Se deja en ABSENT y SIN ops guardadas:  un init que
		 * falla no puede dejar un mapa a medias que alguien intente
		 * deshacer con una HAL que no es la suya. */
		rx550_dummy_reset(p);
		return RX550_DUMMY_ERR_NO_MAP;
	}

	p->dma_pa = pa;
	p->cpu_va = cpu;
	p->ops = *ops;
	p->state = RX550_DUMMY_HELD;

	out_pa->bytes = pa;
	return 0;
}

int rx550_dummy_page_fini(struct rx550_dummy_page *p)
{
	struct rx550_dummy_ops ops;
	void *cpu;
	uint64_t pa;

	if (p == NULL)
		return RX550_DUMMY_ERR_INCONSISTENT;

	/* Idempotente a proposito:  remove() llama a esto tambien cuando probe()
	 * fallo por el camino de la pagina, y que ese camino produzca un SEGUNDO
	 * fallo es como un unwind se convierte en dos. */
	if (p->state != RX550_DUMMY_HELD)
		return 0;

	ops = p->ops;
	cpu = p->cpu_va;
	pa = p->dma_pa;

	/* El estado pasa a RELEASED ANTES de llamar a unmap:  si unmap falla o
	 * vuelve a entrar, el estado ya dice que no hay nada que deshacer, y una
	 * reentrada no puede liberar dos veces la misma cosa. */
	p->state = RX550_DUMMY_RELEASED;
	p->dma_pa = 0;
	p->cpu_va = NULL;

	if (ops.unmap != NULL)
		ops.unmap(ops.ctx, cpu, pa);
	return 0;
}

int rx550_dummy_page_pa(const struct rx550_dummy_page *p,
			struct rx550_system_pa *out)
{
	if (p == NULL || out == NULL)
		return RX550_DUMMY_ERR_INCONSISTENT;
	if (p->state != RX550_DUMMY_HELD)
		return RX550_DUMMY_ERR_STATE;
	out->bytes = p->dma_pa;
	return 0;
}

int rx550_dummy_page_pfn(const struct rx550_dummy_page *p, uint32_t *out)
{
	if (p == NULL || out == NULL)
		return RX550_DUMMY_ERR_INCONSISTENT;
	if (p->state != RX550_DUMMY_HELD)
		return RX550_DUMMY_ERR_STATE;

	/* El registro lleva un PHYSICAL_PAGE_NUMBER de 28 bits, no una direccion.
	 * Si esto devolviera la direccion, quien lo use escribiria un numero
	 * plausible en un registro de paginas.
	 *
	 * Y MEDIDO 2026-10-04: el comentario decia el peligro y el codigo NO lo
	 * comprobaba.  Este `>> 12` trunca en silencio cualquier PA con bits por
	 * encima de 40, y el numero truncado es un PHYSICAL_PAGE_NUMBER valido:
	 *  plausible, y equivocado.  Es exactamente lo contrario de lo que hace
	 * rx550_pdb0_encode() (rx550_pdb0.c:18-21), que rechaza en vez de
	 * truncar, y de lo que hace rx550_pdb0_map_va() con
	 * rx550_pa_representable() (rx550_pdb0.c:161).  El predicado EXISTIA y
	 * este camino no lo usaba:  una guarda presente en un lado y ausente en
	 * su gemelo.
	 *
	 * Que se note cuando:  solo si la mascara DMA del device se queda en el
	 * techo por defecto de 32 bits, que es lo que pasa mientras el driver no
	 * llame a dma_set_mask_and_coherent(40).  MEDIDO en esta maquina:  la
	 * RAM acaba en 34 bits,  luego una PA por encima de 40 NO existe y el
	 * truncamiento es teorico aqui.  Es teorico, no inexistente:  el defecto
	 * es que la funcion aceptaria en silencio una PA que no puede representar.
	 *
	 * LA COMPROBACION ES SOBRE EL NUMERO DE PAGINA, no sobre la mascara de
	 * la PA.  MEDIDO:  la primera version usaba `(dma_pa & ~RX550_PA_MASK)`,
	 * y eso rechazaba las PAs NORMALES, porque ~RX550_PA_MASK tambien señala
	 * los 12 bits bajos, que son el offset DENTRO de la pagina y se
	 * descartan con el >> 12.  Una PA como 0x123456789, que es de 37 bits y
	 * perfectamente valida, tiene los bits bajos a 0x789 y quedaba
	 * rechazada:  el guard era mas estricto que el hardware y rompia el caso
	 * de todos los dias.  Lo que hay que comparar es el numero de pagina
	 * contra su ancho, que es lo que va al registro. */
	{
		uint64_t pag = p->dma_pa >> RX550_PAGE_SHIFT;
		uint64_t max_pag = (UINT64_C(1) <<
				   (RX550_PA_BITS - RX550_PAGE_SHIFT)) - 1;

		if (pag > max_pag)
			return RX550_DUMMY_ERR_NO_PA;
		*out = (uint32_t)pag;
	}
	return 0;
}

int rx550_dummy_page_fault_reg(const struct rx550_dummy_page *p,
			       uint32_t *out)
{
	return rx550_dummy_page_pfn(p, out);
}

/* ── LA HAL DE KERNEL ──────────────────────────────────────────────────── */

#ifdef __KERNEL__
#include <linux/mm.h>

int rx550_dummy_kernel_map(void *ctx, void **out_cpu_va, uint64_t *out_dma_pa)
{
	struct device *dev = (struct device *)ctx;
	struct page *page;
	dma_addr_t dma;

	if (dev == NULL || out_cpu_va == NULL || out_dma_pa == NULL)
		return -EINVAL;

	/* MEDIDO 2026-10-04 · PRECONDICION, Y POR QUE FALLA ANTES DE RESERVAR:
	 * esta HAL hace alloc_page(GFP_KERNEL), y GFP_KERNEL sale de ZONE_NORMAL,
	 * que en esta maquina empieza en 4 GiB (/proc/zoneinfo:  DMA32 acaba en el
	 * pfn 0x100000, Normal cubre 2293248 paginas desde ahi).  Con la mascara
	 * de 32 bits del default PCI (probe.c:2051) esa pagina cae FUERA del
	 * techo de bus, y el mapa falla:
	 *   dma_map_page_attrs()  mapping.c:191-204 -> dma_map_phys
	 *   sin IOMMU              mapping.c:120-153 -> directo
	 *   dma_capable()          dma-direct.h:138  end <= *dev->dma_mask  -> FALSE
	 *   sin rebote posible     direct.h:112-119  is_swiotlb_active()==false aqui
	 *   DMA_MAPPING_ERROR      direct.h:130-135
	 * El mapa se deshace solo al final de la funcion, o sea que sin esta
	 * guarda el fallo se cobraria una pagina del allocator para nada.  Con la
	 * guarda el codigo de error DICE la causa:  -ERANGE es "la mascara no da",
	 * -ENOMEM es "no hay memoria".  Antes las dos cosas salian igual de
	 * -ENOMEM y no habia forma de distinguirlas desde remove().
	 *
	 * dma_addressing_limited() es el predicado del kernel para esta pregunta
	 * exacta --"la mascara es demasiado pequena para toda la memoria del
	 * sistema"-- (mapping.c:961-976), no una reimplementacion de el. */
	if (dma_addressing_limited(dev))
		return -ERANGE;

	/* __GFP_ZERO, igual que la pagina global de TTM que usa la referencia:  si
	 * el hardware llega a memcpy hacia ella, el destino tiene que existir. */
	page = alloc_page(GFP_KERNEL | __GFP_ZERO);
	if (page == NULL)
		return -ENOMEM;

	/* DMA_BIDIRECTIONAL, y no DMA_TO_DEVICE:  la referencia lo pide
	 * bidireccional (amdgpu_gart.c:83) y esta pagina es origen Y destino. */
	dma = dma_map_page_attrs(dev, page, 0, PAGE_SIZE,
				 DMA_BIDIRECTIONAL, DMA_ATTR_SKIP_CPU_SYNC);
	if (dma_mapping_error(dev, dma)) {
		__free_page(page);
		return -ENOMEM;
	}

	*out_cpu_va = page_address(page);
	*out_dma_pa = (uint64_t)dma;
	return 0;
}

void rx550_dummy_kernel_unmap(void *ctx, void *cpu_va, uint64_t dma_pa)
{
	struct device *dev = (struct device *)ctx;
	struct page *page;

	if (dev == NULL || cpu_va == NULL)
		return;
	/* SIN el struct page:  en ESTE kernel (7.1.3) dma_unmap_page_attrs()
	 * lleva 5 argumentos y no lleva la pagina, solo la direccion.
	 * dma-mapping.h:164
	 *     void dma_unmap_page_attrs(struct device *dev, dma_addr_t addr,
	 *                                size_t size, enum dma_data_direction,
	 *                                unsigned long attrs);
	 * La referencia llama igual, amdgpu_gart.c:103, con la misma aridad.
	 * Ponerla con la pagina era de un kernel anterior y no compila. */
	dma_unmap_page_attrs(dev, (dma_addr_t)dma_pa, PAGE_SIZE,
			     DMA_BIDIRECTIONAL, DMA_ATTR_SKIP_CPU_SYNC);
	/* La pagina se suelta DESPUES de deshacer el mapa, y no antes:  en este
	 * kernel el unmap no necesita la pagina, pero si en otro si, liberarla
	 * antes seria usar memoria ya devuelta. */
	page = virt_to_page(cpu_va);
	__free_page(page);
}

/* ── LA MASCARA DMA ──────────────────────────────────────────────────────────
 *
 * POR QUE DOS LLAMADAS Y NO dma_set_mask_and_coherent()
 *   MEDIDO en el kernel EN EJECUCION, de tres maneras independientes que se
 *   dicen lo mismo:
 *
 *   1) TEXTO.  include/linux/dma-mapping.h, byte a byte identico entre
 *      /usr/src/kernels/7.1.3-200.nobara.fc44.x86_64 y el corpus
 *      (sha256 4263b862df9eb2e77481520850996a14a2f5eaafe611544f32ada8dfde32e5ba):
 *          :197  int  dma_set_mask(struct device *dev, u64 mask);
 *          :198  int  dma_set_coherent_mask(struct device *dev, u64 mask);
 *          :641  static inline int dma_set_mask_and_coherent(struct device *dev, u64 mask)
 *
 *   2) OBJETO.  Compilando contra esas cabeceras una sonda minima que llama a
 *      las tres y leyendo `nm -u` del objeto (fichero de la sonda aparte, no
 *      es codigo del driver):
 *              U dma_set_mask
 *              U dma_set_coherent_mask
 *              U dma_map_page_attrs
 *              U dma_addressing_limited
 *              U dma_get_required_mask
 *          dma_set_mask_and_coherent  NO APARECE:  se ha expandido dentro.
 *
 *   3) BINARIO.  System.map del kernel que corre:
 *              ffffffff814cafa0 T dma_set_mask
 *              ffffffff814cddb0 T dma_set_coherent_mask
 *              dma_set_mask_and_coherent   NO ESTA
 *
 *   O sea:  la version de dos en una es INLINE, y las otras dos son simbolos
 *   reales y exportados.  Eso NO es un capricho de estilo y no lo decide la
 *   puerta estatica:  MEDIDO que ni `dma_set_mask` ni `dma_set_coherent_mask`
 *   estan en la lista de simbolos prohibidos de tests/test_static.sh (la lista
 *   es UNDEF_PROHIBIDOS, test_static.sh:538-542, y no menciona ningun dma_set_*).
 *
 *   La razon de fondo es que la version de dos en una DESCARTA el codigo de
 *   error de la mascara coherente:
 *          dma-mapping.h:635-647
 *              static inline int dma_set_mask_and_coherent(struct device *dev, u64 mask)
 *              {
 *                      int rc = dma_set_mask(dev, mask);
 *                      if (rc == 0)
 *                              dma_set_coherent_mask(dev, mask);   <-- rc perdido
 *                      return rc;
 *              }
 *   Es correcto ignorarlo (el comentario de :636-640 explica que la API
 *   garantiza que la coherente puede ser igual o menor que la de streaming), y
 *   aun asi asi no se puede COMPROBAR.  Llamando por separado el segundo rc
 *   existe, y un kernel futuro que rompa esa garantia sale como un numero
 *   distinto en lugar de tragarsela.
 *
 * POR QUE 40 Y NO EL ANCHO QUE HAGA FALTA
 *   MEDIDO 2026-10-04 que dma_set_mask(40) es ACEPTABLE aqui:  el driver de
 *   referencia, que esta cargada y es el driver ENLAZADO a 0000:01:00.0
 *   (MEDIDO:  /sys/bus/pci/devices/0000:01:00.0/driver -> .../amdgpu), lo hizo
 *   sin volverse atrás:  gmc_v8_0.c:1136 y :1137-1140 cortan el probe si falla.
 *   MEDIDO en la maquina:  dma_mask_bits = 40 y consistent_dma_mask_bits = 40.
 *   Y la garantia la da el kernel, no la suerte:
 *       kernel/dma/direct.c:564-565   if (mask >= DMA_BIT_MASK(32)) return 1;
 *   o sea que con mapping directo (MEDIDO:  /sys/kernel/iommu_groups tiene 0
 *   grupos y /proc/cmdline no lleva iommu=, intel_iommu= ni amd_iommu=) 40 bits
 *   siempre se pueden pedir.  Por que 40 y no mas, no es una cuestion de lo
 *   que acepte el kernel:  es que mas alla de 40 el GART no puede representar
 *   el PA, y una mascara mas ancha solo deja pasar entradas que el registro
 *   de 28 bits no puede codificar (gmc_v8_0.c:1133-1134, :890-891, :920-921).
 */
int rx550_dummy_kernel_dma_mask(void *ctx, struct rx550_dma_mask_report *out)
{
	struct device *dev = (struct device *)ctx;
	struct rx550_dma_mask_report r;
	int rc;

	if (dev == NULL)
		return -EINVAL;
	if (out == NULL) {
		/* Un informe que se pide explicitamente y no se puede escribir no
		 * puede seguir siendo opcional en silencio:  se avisa con el codigo
		 * de un argumento malo, que es lo que es. */
		return -EINVAL;
	}

	r.mask_before = dma_get_mask(dev);
	r.required = dma_get_required_mask(dev);
	r.limited_before = dma_addressing_limited(dev) ? 1 : 0;

	rc = dma_set_mask(dev, RX550_DMA_MASK);
	r.streaming_rc = rc;
	r.coherent_rc = -EIO;
	if (rc == 0) {
		/* Solo si la de streaming fue aceptada:  poner la coherente con una
		 * mascara mas ancha que la de streaming seria pedir algo que el
		 * contrato no permite, y el kernel lo negaria sin decir por que. */
		r.coherent_rc = dma_set_coherent_mask(dev, RX550_DMA_MASK);
	}

	r.mask_after = dma_get_mask(dev);
	r.coherent_after = dev->coherent_dma_mask;
	r.mask_bits = rx550_dma_mask_bits_of(r.mask_after);
	r.required_bits = rx550_dma_mask_bits_of(r.required);
	r.limited_after = dma_addressing_limited(dev) ? 1 : 0;

	*out = r;

	/* Un informe con la mascara puesta a medias y rc == 0 seria un informe
	 * que dice que no paso nada mientras pasa algo. */
	if (rc != 0)
		return rc;
	if (r.mask_after != RX550_DMA_MASK)
		return -EIO;
	return 0;
}
#endif /* __KERNEL__ */