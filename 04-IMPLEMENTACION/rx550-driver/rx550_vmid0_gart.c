/* SPDX-License-Identifier: GPL-2.0 */
/*
 * rx550_vmid0_gart.c — construccion, no ejecucion.
 *
 * Sin MMIO, sin ring, sin allocator, sin kernel API.  Este fichero no hace
 * nada que el hardware pueda observar: calcula numeros.  Que esos numeros
 * produzcan efecto es asunto de quien los escriba.
 */
#include "rx550_vmid0_gart.h"

/* COMPATIBILIDAD KBUILD.  El kernel no tiene <string.h>: tiene
 * <linux/string.h>.  Mismo split que rx550_spaces.h y rx550_mmio_access.h, y
 * por el mismo motivo: este .c se compila de las dos formas, en el modulo y en
 * los tests de host.  MEDIDO 2026-10-03: sin esto, cuatro .c de este
 * componente no compilaban bajo kbuild y por eso no estaban en obj-m.
 *
 * Este fichero no usa nada mas de libc: sin allocator, sin MMIO, sin ring.
 */
#ifdef __KERNEL__
#include <linux/string.h>
#else
#include <string.h>
#endif

/* Posiciones de campo.  FACT: asic_reg/gmc/gmc_8_2_sh_mask.h, que es el header
 * que incluye gfx_v8_0.c:42 para esta ASIC (POLARIS12 = GFX8.2).  No se cita
 * gmc_8_1_sh_mask.h: los valores coinciden hoy, pero el registro al que
 * pertenecen es el de la revision que esta placa usa, y la equivalencia
 * numerica no es lo que hace valida una referencia.
 *
 * MASK y SHIFT son ambos OBSERVED: el corpus declara los __SHIFT explicitamente
 * junto a cada __MASK.  Una version anterior de este comentario afirmaba que no
 * existian y los derivaba de la mascara; era una ausencia falsa, obtenida
 * buscando en la revision equivocada. */
#define RX550_CNTL_ENABLE_MASK		UINT32_C(0x00000001)	/* 6457 */
#define RX550_CNTL_DEPTH_MASK		UINT32_C(0x00000006)	/* 6459 */
#define RX550_CNTL_RANGE_PF_MASK	UINT32_C(0x00000010)	/* 6463 */
#define RX550_CNTL_BLOCK_SIZE_MASK	UINT32_C(0x0F000000)	/* 6499 */

#define RX550_CNTL_ENABLE_SHIFT		0u	/* OBSERVED: 6458 */
#define RX550_CNTL_DEPTH_SHIFT		1u	/* OBSERVED: 6460 */
#define RX550_CNTL_RANGE_PF_SHIFT	4u	/* OBSERVED: 6464 */

int rx550_gart_aperture_init(struct rx550_gart_aperture *ap,
			     uint64_t start, uint64_t size)
{
	if (ap == NULL)
		return -1;
	if (size == 0 || size > RX550_GART_SIZE_MAX)
		return -1;
	/* Una apertura que no es un numero entero de paginas deja una
	 * entrada parcial al final.  Se rechaza aqui para que entries sea
	 * exacto y el indexador no tenga que reimplementar el redondeo. */
	if ((size % RX550_GART_PAGE_SIZE) != 0)
		return -1;
	/* El registro START no tiene bits para esto y el driver de
	 * referencia alinea a 4 GiB (amdgpu_gmc.c:332).  No es nuestro
	 * requisito: es el del hardware, y por eso se comprueba. */
	if ((start & (RX550_GART_APERTURE_ALIGN - 1)) != 0)
		return -1;

	ap->start = start;
	ap->size = size;
	ap->entries = size / RX550_GART_PAGE_SIZE;
	ap->end = start + size - 1;
	return 0;
}

int rx550_gart_offset_of(const struct rx550_gpuva gpuva,
			 const struct rx550_gart_aperture *ap,
			 struct rx550_gart_offset_bytes *out)
{
	uint64_t off;

	if (out == NULL || ap == NULL)
		return -1;
	out->bytes = 0;

	/* gpuva por debajo del inicio: no se resta y se espera.  Restarlo
	 * en uint64_t daria un numero enorme que pasaria el rango, y eso
	 * seria un indice de tabla valido apuntando a otra entrada. */
	if (gpuva.bytes < ap->start)
		return -1;

	off = gpuva.bytes - ap->start;
	if (off >= ap->size)
		return -1;

	out->bytes = off;
	return 0;
}

int rx550_gart_index_of(const struct rx550_gart_aperture *ap,
			const struct rx550_gart_offset_bytes off,
			struct rx550_gart_pte_index *out)
{
	if (out == NULL || ap == NULL)
		return -1;
	out->index = 0;

	/* La autoridad es la apertura que el caller tiene delante.  Un
	 * maximo global aqui permitiria devolver un indice valido para una
	 * entrada que esta apertura no tiene. */
	if (off.bytes >= ap->size)
		return -1;

	out->index = off.bytes >> RX550_GART_PAGE_SHIFT;
	if (out->index >= ap->entries)
		return -1;
	return 0;
}

int rx550_gart_entry_offset_of(const struct rx550_gart_aperture *ap,
			       const struct rx550_gart_pte_index idx,
			       struct rx550_gart_offset_bytes *out)
{
	if (out == NULL || ap == NULL)
		return -1;
	out->bytes = 0;

	if (idx.index >= ap->entries)
		return -1;

	out->bytes = idx.index * RX550_GART_PTE_SIZE;
	return 0;
}

int rx550_pte_encode(struct rx550_system_pa pa, uint64_t flags, uint64_t *out)
{
	if (out == NULL)
		return -1;
	*out = 0;

	/* PA_POLICY = REJECT_UNALIGNED.  El corpus enmascara
	 * (amdgpu_gmc.c:173); copiarlo haria que una PA con los bits
	 * bajos puestos se tradujera a OTRA pagina, sin error visible. */
	if ((pa.bytes & (RX550_GART_PAGE_SIZE - 1)) != 0)
		return -1;
	if ((pa.bytes & ~RX550_GART_PA_MASK) != 0)
		return -1;

	/* Un flag que el layout de la GART de GFX8 no define no se
	 * escribe.  amdgpu_vm.h define TMZ(3), PRT(51), LOG(55), TF(56)
	 * y NOALLOC(58), pero gmc_v8_0.c:691-702 los marca RESERVADOS
	 * para una PTE de GART, y gmc_v8_0.c:728 limpia PRT. */
	if ((flags & ~RX550_PTE_FLAG_MASK) != 0)
		return -1;

	*out = (pa.bytes & RX550_GART_PA_MASK) | flags;
	return 0;
}

struct rx550_system_pa rx550_pte_decode(uint64_t entry)
{
	struct rx550_system_pa pa;

	pa.bytes = entry & RX550_GART_PA_MASK;
	return pa;
}

bool rx550_pte_valid(uint64_t entry)
{
	return (entry & RX550_PTE_VALID) != 0;
}

int rx550_vmid0_config_build(struct rx550_vmid0_config *cfg)
{
	if (cfg == NULL)
		return -1;

	/* PAGE_TABLE_DEPTH=1 belongs to VMID1+.  En el contexto 0
	 * programaria un segundo nivel contra una tabla que no lo tiene.
	 * Lo rechaza el constructor, no el hardware: la decision de que
	 * este componente solo modela profundidad 0 es nuestra. */
	if (RX550_VMID0_DEPTH != RX550_VMID0_DEPTH_MAX)
		return -1;

	cfg->enable_context = RX550_VMID0_ENABLE_CONTEXT;
	cfg->page_table_depth = RX550_VMID0_DEPTH;
	cfg->range_pf_default = RX550_VMID0_RANGE_PF_DEFAULT;

	/* PAGE_TABLE_BLOCK_SIZE no tiene campo en esta configuracion.  No
	 * se acepta el parametro, no se acepta el flag, no se deja en
	 * cero a escondidas: sencillamente no existe aqui. */
	return 0;
}

int rx550_vmid0_base_from_vram(struct rx550_vram_offset off,
			       struct rx550_gart_gpu_pfn *out)
{
	if (out == NULL)
		return -1;
	out->value = 0;

	/* El registro BASE es de 32 bits.  Un offset de VRAM que no quepa
	 * tras el >>12 no se trunca. */
	if (off.bytes > UINT64_C(0xFFFFFFFF) * RX550_GART_PAGE_SIZE)
		return -1;

	out->value = off.bytes >> RX550_GART_PAGE_SHIFT;
	return 0;
}

int rx550_vmid0_fault_from_pa(struct rx550_system_pa pa, struct rx550_pfn *out)
{
	if (out == NULL)
		return -1;
	out->value = 0;

	if (pa.bytes > UINT64_C(0xFFFFFFFF) * RX550_GART_PAGE_SIZE)
		return -1;

	out->value = pa.bytes >> RX550_GART_PAGE_SHIFT;
	return 0;
}

int rx550_vmid0_regs_build(struct rx550_vmid0_regs *regs,
			   const struct rx550_vmid0_config *cfg,
			   struct rx550_gart_gpu_pfn base,
			   uint64_t gart_start, uint64_t gart_end,
			   struct rx550_system_pa dummy_page_addr)
{
	uint32_t start_pfn;
	uint32_t end_pfn;
	uint32_t fault_pfn;
	uint32_t cntl;

	if (regs == NULL || cfg == NULL)
		return RX550_VMID0_ERR_INCONSISTENT;
	memset(regs, 0, sizeof(*regs));

	/* Se valida TODO antes de devolver nada.  Un caller que recibe
	 * error no tiene un struct a medio poblar.
	 *
	 * MEDIDO 2026-10-04:  los nueve guards de a continuacion devolvian
	 * `-1`,  los nueve.  Este es el cambio:  cada uno devuelve su codigo de
	 * enum rx550_vmid0_regs_err  y ninguno comparte numero con otro.  El
	 * criterio y la justificacion estan en rx550_vmid0_gart.h,  junto al
	 * enum,  que es donde el gemelo rx550_gart_seq.h:196 lo escribio tambien.
	 * MEDIDO tambien que el cambio no rompe a nadie:  sobre los 78
	 * .c/.h/.sh del arbol no hay un solo llamante que compare contra el
	 * literal -1. */
	if (cfg->enable_context != RX550_VMID0_ENABLE_CONTEXT)
		return RX550_VMID0_ERR_ENABLE_CONTEXT;
	if (cfg->page_table_depth != RX550_VMID0_DEPTH)
		return RX550_VMID0_ERR_DEPTH;
	if (cfg->range_pf_default != RX550_VMID0_RANGE_PF_DEFAULT)
		return RX550_VMID0_ERR_RANGE_PF;
	if (base.value > UINT64_C(0xFFFFFFFF))
		return RX550_VMID0_ERR_BASE_TOO_WIDE;
	if (gart_start > UINT64_C(0xFFFFFFFF) * RX550_GART_PAGE_SIZE)
		return RX550_VMID0_ERR_START_TOO_WIDE;
	if (gart_end > UINT64_C(0xFFFFFFFF) * RX550_GART_PAGE_SIZE)
		return RX550_VMID0_ERR_END_TOO_WIDE;
	if (dummy_page_addr.bytes > UINT64_C(0xFFFFFFFF) * RX550_GART_PAGE_SIZE)
		return RX550_VMID0_ERR_PA_TOO_WIDE;
	/* MEDIDO 2026-10-04.  ESTE ES EL GEMELO EXACTO de la guarda que le faltaba
	 * a rx550_gart_seq.c,  y que un nodo anterior cerro alli.  Aqui solo se
	 * acotaba el TECHO  —fault_pfn = dummy_page_addr.bytes >> 12  con 0 da 0—  y
	 * el suelo se pasaba.
	 *
	 * POR QUE 0 NO ES UNA DIRECCION VALIDA,  con la evidencia:
	 *   · 0 es el CENTINELA DE AUSENTE en el corpus:  amdgpu_gart.c:79, :84-88
	 *     (= 0; return -ENOMEM), :101, :106, :520.
	 *   · NO es el centinela de dma_map:  include/linux/dma-mapping.h:116 es
	 *     ~(dma_addr_t)0,  de modo que un mapa que devolviera 0 PASARIA el
	 *     control de :152.  El argumento "dma_map falla luego no hay pagina" no
	 *     sostiene la guarda.
	 *   · MEDIDO que las 76 ocurrencias de dummy_page_addr en el amdgpu del
	 *     corpus  se usan como >> 8 / >> 12 / >> 44  sin comprobar el cero.
	 *
	 * Y CON 0,  lo que sale es fault_pfn = 0  en PROTECTION_FAULT_DEFAULT_ADDR:
	 * todo fault de proteccion del contexto 0 traduce a PA 0.
	 *
	 * LA LIMITACION QUE ESTA GUARDA NO CERRABA,  Y QUE ESTE COMMIT CIERRA:
	 * hasta a0bedd7  esta funcion DEVOLVIA -1 PARA TODO.  El -1 de esta guarda
	 * era INDISTINGUIBLE del techo de la linea de arriba  -y de las otras seis
	 * comprobaciones-,  de modo que un llamante no podia saber si lo que fallo
	 * fue el techo,  la profundidad o que no hay pagina.
	 *
	 * RESUELTO AQUI,  con el codigo que faltaba:
	 *   esta guarda devuelve RX550_VMID0_ERR_NO_DUMMY_PAGE (-9)
	 *   y la de una linea mas arriba devuelve RX550_VMID0_ERR_PA_TOO_WIDE (-8)
	 *
	 * Y NO SE CONFUNDEN POR CASUALIDAD:  los DOS son limites del MISMO
	 * parametro,  dummy_page_addr,  y los DOS arreglos son distintos.
	 *   PA_TOO_WIDE    (> 2^40-1)  el arreglo es la mascara DMA,
	 *                                dma_set_mask_and_coherent(40)
	 *   NO_DUMMY_PAGE  (== 0)       el arreglo es que corra
	 *                                rx550_dummy_page_init()
	 * Un codigo generico aqui hace que el llamante pruebe dma_set_mask:  lo
	 * correcto para el techo,  y absolutamente inútil para el suelo.  El gemelo
	 * rx550_gart_seq.c:484-487  ya devolvia DOS codigos distintos sobre el MISMO
	 * parametro  (== 0 -> ERR_NO_DUMMY_PAGE -4,  > MAX -> ERR_GEOMETRY -2),  y
	 * por el mismo motivo.  La justificacion entera esta en
	 * rx550_vmid0_gart.h,  junto al enum,  que es donde el gemelo escribio la
	 * suya tambien.
	 *
	 * AMBITO,  que conviene no ver mas grande de lo que es:  este espacio de
	 * errores es de ESTA funcion.  Las otras ocho de este .c devuelven -1 sin
	 * nombre y siguen asi;  abrirlas es otro trabajo y no se ha hecho de paso.
	 */
	if (dummy_page_addr.bytes == 0)
		return RX550_VMID0_ERR_NO_DUMMY_PAGE;

	start_pfn = (uint32_t)(gart_start >> RX550_GART_PAGE_SHIFT);
	end_pfn = (uint32_t)(gart_end >> RX550_GART_PAGE_SHIFT);
	fault_pfn = (uint32_t)(dummy_page_addr.bytes >> RX550_GART_PAGE_SHIFT);

	cntl = 0;
	cntl |= (cfg->enable_context << RX550_CNTL_ENABLE_SHIFT) &
		RX550_CNTL_ENABLE_MASK;
	cntl |= (cfg->page_table_depth << RX550_CNTL_DEPTH_SHIFT) &
		RX550_CNTL_DEPTH_MASK;
	cntl |= (cfg->range_pf_default << RX550_CNTL_RANGE_PF_SHIFT) &
		RX550_CNTL_RANGE_PF_MASK;
	/* PAGE_TABLE_BLOCK_SIZE se queda a cero porque no se escribe.
	 * No es un default: es la ausencia del campo en esta
	 * configuracion.  Si alguien lo quisiera, el constructor tendria
	 * que ofrecerlo, y no lo ofrece. */

	regs->page_table_base = (uint32_t)base.value;
	regs->page_table_start = start_pfn;
	regs->page_table_end = end_pfn;
	regs->protection_fault_default = fault_pfn;
	regs->cntl2 = 0;
	regs->cntl = cntl;

	/* gmc_v8_0.c:886-897 y :941 */
	regs->order[0] = 0;	/* PAGE_TABLE_BASE_ADDR           */
	regs->order[1] = 1;	/* PAGE_TABLE_START_ADDR          */
	regs->order[2] = 2;	/* PAGE_TABLE_END_ADDR            */
	regs->order[3] = 3;	/* PROTECTION_FAULT_DEFAULT_ADDR  */
	regs->order[4] = 4;	/* CNTL2                          */
	regs->order[5] = 5;	/* CNTL                           */
	regs->order[6] = 6;	/* INVALIDATE                     */
	return 0;
}
