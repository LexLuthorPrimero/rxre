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
#endif /* __KERNEL__ */