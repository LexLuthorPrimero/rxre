/* SPDX-License-Identifier: GPL-2.0 */
/*
 * target_mem.h — Q2 MEMORY_OBJECT: el objeto de memoria del driver propio.
 *
 *   TARGET = RX 550 instalada en esta computadora
 *   SCOPE  = EXCLUSIVO
 *
 * QUÉ ES ESTE ARCHIVO
 *   Un contrato de direcciones, no un asignador. No pide memoria, no conoce
 *   TTM, no conoce VRAM. Describe CÓMO se nombra y se traduce una dirección,
 *   que es la parte que el hardware impone, y deja el resto abierto.
 *
 * DE DÓNDE SALE CADA NÚMERO
 *   amdgpu_gart.h:35          AMDGPU_GPU_PAGE_SIZE 4096
 *   amdgpu_gart.h:37          AMDGPU_GPU_PAGE_SHIFT 12
 *   gmc_v8_0.c:1127           amdgpu_vm_adjust_size(adev, 64, 9, 1, 40)
 *                             max_level=1, max_bits=40
 *   gmc_v8_0.c:1134           pte_addr_mask = 0x000000FFFFFFF000
 *   amdgpu_vm.h:76            AMDGPU_PDE_PTE = (1ULL << 54)   (rama pre-GFX12)
 *   amdgpu_vm.h:140-142       AMDGPU_PDE_PTE_FLAG: GFX12 usa el bit 63, GFX8 el 54
 *   amdgpu_vm_pt.c:58         9 * (PDB0 - level) + block_size
 *   amdgpu_vm.h:169-182       regiones de VA reservadas
 *
 *   Nada de esto es herencia. Es la geometría que el hardware impone, leída del
 *   corpus 7.1.3 y contrastada con dos fórmulas independientes (Q1).
 *
 * LO QUE ESTE ARCHIVO NO DECIDE
 *   de dónde sale la memoria física, quién la asigna, ni en qué plano vive.
 *   Eso es DESIGN_CHOICE y se decide en Q2-modelo, no aquí.
 */
#ifndef TARGET_MEM_H
#define TARGET_MEM_H

#ifndef __KERNEL__
#include "target_mem_host.h"
#else
#include <linux/types.h>
#include <linux/stdbool.h>
#endif

/* ── HARDWARE_REQUIREMENT ─────────────────────────────────────────────── */

#define TM_PAGE_SHIFT		12u
#define TM_PAGE_SIZE		(1u << TM_PAGE_SHIFT)

/* 9 bits por nivel: 512 entradas x 8 B = 4096 B = exactamente una pagina. */
#define TM_LEVEL_BITS		9u
#define TM_LEVEL_ENTRIES	(1u << TM_LEVEL_BITS)	/* 512 */
#define TM_ENTRY_SIZE		8u

/* GFX8: max_level = 1, es decir UN nivel de directorio mas la PTB. */
#define TM_NR_DIR_LEVELS	1u
#define TM_PN_BITS		28u			/* (0x0FFFFFFF + 1) << 12 == 2^40 */
#define TM_PA_BITS		40u

/* Mascara del numero de pagina fisica, materializada.
 *
 *   NO es un numero nuevo: es (1 << TM_PN_BITS) - 1, que es exactamente el valor
 *   que test_vm ya verifica contra el corpus, en gmc_8_2_sh_mask.h:
 *     PHYSICAL_PAGE_NUMBER mask == 0xfffffff
 *   Antes el header solo decia "28 bits" y quien quisiera la mascara tenia que
 *   reconstruirla.  Se escribe para que la asercion del contrato tenga contra
 *   que compararse, en vez de comprobarse contra si misma.
 */
#define TM_PN_MASK		((1ull << TM_PN_BITS) - 1ull)

/* GFX8 VA = 9 (PDB0) + 9 (PTB) + 12 (offset) = 30 bits. */
#define TM_VA_BITS		(TM_LEVEL_BITS * (TM_NR_DIR_LEVELS + 1) + TM_PAGE_SHIFT)
#define TM_VA_SIZE		(1ull << TM_VA_BITS)

/* ── PTE / PDE ────────────────────────────────────────────────────────── */

#define TM_PTE_VALID		(1ull << 0)
#define TM_PTE_EXECUTABLE	(1ull << 4)
#define TM_PTE_READABLE		(1ull << 5)
#define TM_PTE_WRITEABLE	(1ull << 6)
#define TM_PTE_PRIV		(1ull << 48)
#define TM_PDE_LEAF		(1ull << 54)		/* GFX8. GFX12 seria el 63. */

/* La direccion fisica va en bits [51:12]. */
#define TM_ADDR_MASK		0x000000FFFFFFF000ull
#define TM_ADDR_SHIFT		TM_PAGE_SHIFT

/* ── regiones de VA reservadas por el hardware ────────────────────────── */
/* amdgpu_vm.h:169-182. Se restan del rango asignable. */
#define TM_RESERVED_CSA_SIZE	(2ull << 20)
#define TM_RESERVED_SEQ64_SIZE	(2ull << 20)
#define TM_RESERVED_TRAP_SIZE	(1ull << 16)
#define TM_RESERVED_BOTTOM	(1ull << 16)
#define TM_RESERVED_TOTAL	(TM_RESERVED_CSA_SIZE + TM_RESERVED_SEQ64_SIZE + \
				 TM_RESERVED_TRAP_SIZE + TM_RESERVED_BOTTOM)

#define TM_VA_USER_START	TM_RESERVED_BOTTOM
#define TM_VA_USER_END		(TM_VA_SIZE - TM_RESERVED_CSA_SIZE - \
				 TM_RESERVED_SEQ64_SIZE - TM_RESERVED_TRAP_SIZE)

/* ── traduccion ──────────────────────────────────────────────────────── */

/* page number de una GPUVA */
static inline u64 tm_va_to_pn(u64 va)
{
	return va >> TM_ADDR_SHIFT;
}

/* indice de entrada de nivel 'level' (0 = PTB, 1 = PDB0) */
static inline u32 tm_level_index(u64 va, u32 level)
{
	return (u32)((va >> (TM_PAGE_SHIFT + TM_LEVEL_BITS * level)) &
		     (TM_LEVEL_ENTRIES - 1));
}

/* bits de la GPUVA que seleccionan la entrada de PTB */
static inline u32 tm_ptb_index(u64 va)
{
	return (u32)((va >> TM_PAGE_SHIFT) & (TM_LEVEL_ENTRIES - 1));
}

/* ── construccion de entradas ─────────────────────────────────────────── */

/* PDE: apunta a la siguiente tabla. Sin marca de hoja. */
static inline u64 tm_pde_make(u64 next_table_pa)
{
	return (next_table_pa & TM_ADDR_MASK) | TM_PTE_VALID;
}

/* PTE: hoja. Un bit por permiso, hoja marcada, direccion fisica arriba. */
static inline u64 tm_pte_make(u64 pa, bool readable, bool writeable, bool exec)
{
	u64 e = (pa & TM_ADDR_MASK) | TM_PDE_LEAF | TM_PTE_VALID;

	if (readable)
		e |= TM_PTE_READABLE;
	if (writeable)
		e |= TM_PTE_WRITEABLE;
	if (exec)
		e |= TM_PTE_EXECUTABLE;
	return e;
}

/* ── lectura de entradas ──────────────────────────────────────────────── */

/* Cada escritor tiene su lector. tm_pde_make() marca TM_PTE_VALID igual que
 * tm_pte_make(), porque en GFX8 el bit 0 de una PDE significa lo mismo que en
 * una PTE: la entrada existe.  La funcion existia solo para PTE, y el test del
 * contrato no podia leer un PDE sin mentir.  No es semantica nueva: es el mismo
 * bit, con el nombre del tipo de entrada que se esta leyendo.
 *
 * amdgpu_vm_pt.c escribe _PAGE_ENTRY_VALID en las dos, no solo en las PTE.
 */
static inline bool tm_pde_is_valid(u64 e)   { return (e & TM_PTE_VALID) != 0; }

static inline bool tm_pte_is_valid(u64 e)   { return (e & TM_PTE_VALID) != 0; }
static inline bool tm_pte_is_leaf(u64 e)    { return (e & TM_PDE_LEAF) != 0; }
static inline bool tm_pde_is_leaf(u64 e)    { return (e & TM_PDE_LEAF) != 0; }
static inline bool tm_pte_is_readable(u64 e)  { return (e & TM_PTE_READABLE) != 0; }
static inline bool tm_pte_is_writeable(u64 e) { return (e & TM_PTE_WRITEABLE) != 0; }
static inline bool tm_pte_is_exec(u64 e)      { return (e & TM_PTE_EXECUTABLE) != 0; }

/* direccion fisica que apunta una entrada (hoja o no) */
static inline u64 tm_entry_pa(u64 e)
{
	return e & TM_ADDR_MASK;
}

#endif /* TARGET_MEM_H */
