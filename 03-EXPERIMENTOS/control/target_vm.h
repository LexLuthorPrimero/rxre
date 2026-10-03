/* SPDX-License-Identifier: GPL-2.0-only */
/*
 * target_vm.h — modelo mínimo de memoria virtual de GPU para GFX8.
 *
 * QUE ES Y QUE NO ES
 *   Es el modelo de lo que el PRIMER CAMINO necesita, con los limites de
 *   hardware que lo condicionan.  No es una reimplementacion de drm_gpuvm,
 *   ni una copia del gestor de VM de AMDGPU, ni un driver de paginacion.
 *
 * HALLAZGO ESTRUCTURAL QUE CONDICIONA TODO ESTE ARCHIVO
 *
 *   Los registros de tabla de paginas de GFX8 NO estan en el mapa GCA.
 *     .../asic_reg/gca/gfx_8_0_d.h   ->   0 registros  mmVM_* / mmGTT* / mmPTE*
 *     .../asic_reg/gc/gc_9_0_offset.h-> 510 registros  mmVM_* / mmGTT* / mmPTE*
 *
 *   En GFX8 estan en el bloque GMC:
 *     .../asic_reg/gmc/gmc_8_2_d.h:599-618   (gfx_v8_0.c:41 lo incluye)
 *
 *   Consecuencia de arquitectura, no de implementacion: no existe un motor de
 *   recorrido de tabla de paginas en la GPU para GFX8, ni registros GTT con
 *   los que poblarlos desde la GPU.  La tabla se escribe desde la CPU.  Por eso
 *   este modelo es un plano: la CPU escribe, la GPU traduce.
 *
 * LIMITES DE HARDWARE (PROVEN, con registro)
 *   base de tabla de paginas   mmVM_CONTEXT8..15_PAGE_TABLE_BASE_ADDR  0x50e..0x515
 *                              PHYSICAL_PAGE_NUMBER  mask 0xfffffff (28 bits)
 *   profundidad                mmVM_CONTEXT0/1_CNTL.PAGE_TABLE_DEPTH
 *                              mask 0x6 (2 bits, PROGRAMABLE)
 *   tamano de bloque           mmVM_CONTEXT0/1_CNTL.PAGE_TABLE_BLOCK_SIZE
 *                              mask 0xf000000 (4 bits, PROGRAMABLE)
 *   contexto                   ENABLE_CONTEXT  bit 0  de mmVM_CONTEXT0/1_CNTL
 *   invalidacion de TLB        mmVM_INVALIDATE_REQUEST   0x51e  (4 dominios)
 *                              mmVM_INVALIDATE_RESPONSE  0x51f
 *   pagina                     AMDGPU_GPU_PAGE_SIZE 4096  (amdgpu_gart.h:35)
 *
 * LO QUE ESTO CLASIFICA COMO NO NECESARIO PARA EL PRIMER CAMINO
 *   multiplexacion de VMID, multi-proceso, demand paging,Eviction, TTM,
 *   comparticion entre contextos, tabla de paginas jerarquica completa,
 *   drm_gpuvm, GTT como gestor de TTM.
 *   No es que seanWrong: es que ningun consumidor esta demonstrado todavia.
 *
 * LO QUE QUEDA ABIERTO
 *   QUE VALOR de PAGE_TABLE_DEPTH y de BLOCK_SIZE debe usar el primer
 *   contexto.  Los campos son programables, asi que el hardware no impone un
 *   valor; elegirlo sin evidencia seria inventar.  Queda NOT_DETERMINED y
 *   su eleccion pertenece al componente de integracion, con runtime.
 *
 * REGLA QUE NO SE ROMPE
 *   Direccion GPU virtual, direccion fisica y numero de pagina fisica son
 *   tres cosas distintas.  PHYSICAL_PAGE_NUMBER NO es una direccion de bytes.
 */
#ifndef TARGET_VM_H
#define TARGET_VM_H

/* --- limites de hardware, con su procedencia ---------------------------- */
#define TVM_PAGE_SIZE			4096u	/* amdgpu_gart.h:35            */
#define TVM_PAGE_SHIFT			12u	/* amdgpu_gart.h:37            */

/* PHYSICAL_PAGE_NUMBER: 28 bits, gmc_8_2_sh_mask.h */
#define TVM_PT_BASE_PN_MASK		0x0FFFFFFFu
#define TVM_PT_BASE_PN_BITS		28u
/* un numero de pagina fisica de 28 bits cubre esta direccion fisica maxima */
#define TVM_MAX_PHYS_FROM_PN		(((unsigned long long)TVM_PT_BASE_PN_MASK + 1) << TVM_PAGE_SHIFT)

/* contextos: 2 registros de control (0 y 1) */
#define TVM_NR_CTL_CONTEXTS		2u
/* bases: 8 registros, del 8 al 15 */
#define TVM_FIRST_BASE_CTX		8u
#define TVM_NR_BASE_REGS		8u

/* invalidacion de TLB: 4 dominios en mmVM_INVALIDATE_REQUEST */
#define TVM_NR_TLB_DOMAINS		4u
#define TVM_TLB_REQ_D0			0x1u
#define TVM_TLB_REQ_D1			0x2u
#define TVM_TLB_REQ_D2			0x4u
#define TVM_TLB_REQ_D3			0x8u
#define TVM_TLB_REQ_ALL			0xFu

/* campos programables de mmVM_CONTEXT0/1_CNTL */
#define TVM_DEPTH_FIELD_MASK		0x6u	/* 2 bits, bits 1..2            */
#define TVM_BLOCKSIZE_FIELD_MASK	0xF000000u	/* 4 bits, 24..27      */
#define TVM_ENABLE_CONTEXT		0x1u

/* --- estado de un contexto de VM ---------------------------------------- */
enum target_vm_ctx_state {
	TVM_CTX_ABSENT		= 0,	/* no configurado                  */
	TVM_CTX_CONFIGURED	= 1,	/* base escrita, contexto off      */
	TVM_CTX_ENABLED		= 2,	/* ENABLE_CONTEXT = 1              */
	TVM_CTX_TLB_INVALIDATE	= 3,	/* invalidate pedido               */
	TVM_CTX_TLB_DONE	= 4,	/* respuesta recibida              */
	TVM_CTX_RETIRED		= 5,	/* liberado, no reutilizable        */
};

/* Clasificacion de cada capacidad para el primer camino. */
enum target_vm_need {
	TVM_REQUIRED		= 0,
	TVM_NOT_REQUIRED_YET	= 1,
	TVM_NOT_DETERMINED	= 2,
};

struct target_vm_ctx {
	unsigned char	state;
	unsigned char	ctx_id;		/* 0 o 1: registro CNTL            */
	unsigned char	depth;		/* campo de 2 bits, 0..3          */
	unsigned char	block_size;	/* campo de 4 bits, 0..15         */
	unsigned int	base_pn;		/* PHYSICAL_PAGE_NUMBER, 28 bits  */
	unsigned int	tlb_pending;	/* mascara de dominios pendientes  */
	unsigned char	page_table_valid;/* hay una tabla utilizable         */
};

static inline void tvm_ctx_init(struct target_vm_ctx *c)
{
	c->state = TVM_CTX_ABSENT;
	c->ctx_id = 0;
	c->depth = 0;
	c->block_size = 0;
	c->base_pn = 0;
	c->tlb_pending = 0;
	c->page_table_valid = 0;
}

/* Valida un numero de pagina fisica contra el campo de 28 bits. */
static inline int tvm_pn_valid(unsigned int pn)
{
	return (pn & ~TVM_PT_BASE_PN_MASK) == 0;
}

/* Convierte PHYSICAL_PAGE_NUMBER a direccion fisica en bytes.
 * Son cosas distintas: el registro guarda el numero, no la direccion. */
static inline unsigned long long tvm_pn_to_phys(unsigned int pn)
{
	return ((unsigned long long)pn) << TVM_PAGE_SHIFT;
}

/*
 * tvm_ctx_configure - ABSENT -> CONFIGURED
 *
 * Rechaza un numero de pagina fuera de 28 bits en vez de truncarlo: truncar
 * uniregistro por defectos en vez de reportarlos.
 */
static inline int tvm_ctx_configure(struct target_vm_ctx *c, unsigned int ctx_id,
				    unsigned int base_pn, unsigned int depth,
				    unsigned int block_size)
{
	if (c->state != TVM_CTX_ABSENT)
		return 0;
	if (ctx_id >= TVM_NR_CTL_CONTEXTS)
		return 0;
	if (!tvm_pn_valid(base_pn))
		return 0;
	if (depth > 3u || block_size > 15u)
		return 0;

	c->ctx_id     = (unsigned char)ctx_id;
	c->base_pn    = base_pn;
	c->depth      = (unsigned char)depth;
	c->block_size = (unsigned char)block_size;
	c->state      = TVM_CTX_CONFIGURED;
	return 1;
}

/* CONFIGURED -> ENABLED.  No habilita un contexto sin tabla utilizable. */
static inline int tvm_ctx_enable(struct target_vm_ctx *c)
{
	if (c->state != TVM_CTX_CONFIGURED)
		return 0;
	if (!c->page_table_valid)
		return 0;
	c->state = TVM_CTX_ENABLED;
	return 1;
}

/*
 * tvm_ctx_invalidate_tlb - pide invalidacion de un dominio.
 *
 * El hardware tiene 4 dominios (mmVM_INVALIDATE_REQUEST bits 0..3).  Pedir un
 * dominio que no existe no es un no-op: seria una peticion mal formada que
 * podria quedar colgada esperando respuesta.
 */
static inline int tvm_ctx_invalidate_tlb(struct target_vm_ctx *c, unsigned int domain_mask)
{
	if (c->state != TVM_CTX_ENABLED)
		return 0;
	if (domain_mask == 0 || (domain_mask & ~TVM_TLB_REQ_ALL) != 0)
		return 0;
	c->tlb_pending |= domain_mask;
	c->state = TVM_CTX_TLB_INVALIDATE;
	return 1;
}

/* La respuesta del hardware llega por mmVM_INVALIDATE_RESPONSE. */
static inline int tvm_ctx_invalidate_done(struct target_vm_ctx *c,
					  unsigned int domain_mask)
{
	if (c->state != TVM_CTX_TLB_INVALIDATE)
		return 0;
	if ((domain_mask & c->tlb_pending) != domain_mask)
		return 0;
	c->tlb_pending &= ~domain_mask;
	if (c->tlb_pending == 0)
		c->state = TVM_CTX_ENABLED;
	return 1;
}

/* Habilita el contexto tras una invalidacion completa. */
static inline int tvm_ctx_resume(struct target_vm_ctx *c)
{
	if (c->state != TVM_CTX_ENABLED)
		return 0;
	c->state = TVM_CTX_ENABLED;
	return 1;
}

/* El unico camino a RETIRED es pasar por un contexto habilitado o no. */
static inline int tvm_ctx_retire(struct target_vm_ctx *c)
{
	if (c->state != TVM_CTX_ENABLED && c->state != TVM_CTX_CONFIGURED &&
	    c->state != TVM_CTX_ABSENT)
		return 0;
	c->tlb_pending = 0;
	c->page_table_valid = 0;
	c->state = TVM_CTX_RETIRED;
	return 1;
}

static inline int tvm_ctx_usable(const struct target_vm_ctx *c)
{
	return c->state == TVM_CTX_ENABLED;
}

/* --- tabla de requisitos del primer camino -------------------------------- */
struct target_vm_req {
	const char	*capability;
	int		need;		/* enum target_vm_need */
	const char	*basis;
};

/*
 * BASE DE REQUISITOS MINIMA.  Cada fila dice POR QUE, no solo QUE.
 * TVM_NOT_DETERMINED marca una decision que la evidencia no cierra.
 */
static const struct target_vm_req target_vm_requirements[] = {
{ "un unico espacio de direcciones",	TVM_REQUIRED,
  "el primer camino tiene un solo anillo y un solo IB" },
{ "un unico contexto de VM",		TVM_REQUIRED,
  "no hay multi-proceso ni multi-contexto que demostrar" },
{ "tabla de paginas propia",		TVM_REQUIRED,
  "la CPU debe escribir la tabla: GFX8 no tiene motor de recorrido" },
{ "tabla de paginas jerarquica completa", TVM_NOT_REQUIRED_YET,
  "ningun consumidor de una jerarquia profunda; el rango primero es pequeno" },
{ "multiplexacion de VMID",		TVM_NOT_REQUIRED_YET,
  "un solo contexto basta para el primer camino" },
{ "resolucion de faults",		TVM_NOT_REQUIRED_YET,
  "sin demand paging no hay fault que resolver" },
{ "invalidation de TLB",		TVM_REQUIRED,
  "tras escribir la tabla hay que invalidar, o la GPU puede usar la vieja" },
{ "valor de PAGE_TABLE_DEPTH",		TVM_NOT_DETERMINED,
  "el campo es programable (2 bits): el hardware no impone un valor" },
{ "valor de PAGE_TABLE_BLOCK_SIZE",	TVM_NOT_DETERMINED,
  "el campo es programable (4 bits): el hardware no impone un valor" },
{ "drm_gpuvm",				TVM_NOT_REQUIRED_YET,
  "gestor de VA de Linux; adoptarlo ahora seria copiar arquitectura" },
{ "TTM / GTT como gestor de TTM",	TVM_NOT_REQUIRED_YET,
  "no hay VRAM swappable en el primer camino" },
};

#define TVM_NR_REQS (sizeof(target_vm_requirements) / sizeof(target_vm_requirements[0]))

#endif /* TARGET_VM_H */
