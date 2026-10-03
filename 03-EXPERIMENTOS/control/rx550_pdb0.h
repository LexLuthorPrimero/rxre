/* SPDX-License-Identifier: GPL-2.0 */
/*
 * rx550_pdb0.h — PDB0 (page directory block 0), implementacion CANONICA.
 *
 *   TARGET = RX 550 instalada en esta maquina
 *   SCOPE  = EXCLUSIVO
 *
 * QUE ES
 *   Un directorio de paginas de 4 KiB con 512 entradas de 8 B, que cubren
 *   2 MiB.  Su contenido son entradas hoja que apuntan a memoria del sistema a
 *   traves de la ventana GART.
 *
 * QUE NO ES
 *   No es un allocator.  No tiene device.  No toca hardware.  No depende de
 *   ningun header del kernel: se compila y se testea fuera.
 *
 * LO QUE ESTA FIJADO POR HARDWARE
 *   page 4 KiB, 9 bits por nivel, 512 entradas, 8 B por entrada,
 *   marca de hoja en el bit 54, direccion fisica de 40 bits, cobertura 2 MiB.
 *
 * LO QUE ES DECISION NUESTRA
 *   GART_START = 0, y por tanto GART_ADDRESS == SYSTEM_PA.
 *   No es un requisito del hardware.  Ver rx550_spaces.h.
 *
 * LO QUE NO SE MODELA, A PROPOSITO
 *   FRAG   NOT_DETERMINED   su semantica no esta en el corpus
 *   MTYPE  NOT_AVAILABLE    GFX8 no tiene ese campo
 *   TLB    DEFERRED_RUNTIME su comportamiento necesita el dispositivo
 *   ESTAS  NO SE INVENTAN
 *
 * POR QUE LA CREACION NO DEPENDE DE GPUVA
 *   El objeto existe porque hay un hueco VRAM donde escribir una tabla.  Las
 *   GPUVA que luego contenga son contenido, no precondicion de existencia.  Un
 *   nucleo sin shaders sigue necesitando la tabla.
 */
#ifndef RX550_PDB0_H
#define RX550_PDB0_H

#include "rx550_spaces.h"
#include "rx550_vram.h"

/* ── HARDWARE_REQUIREMENT ──────────────────────────────────────────────── */
#define RX550_PDB0_ENTRIES	512u
#define RX550_PDB0_ENTRY_SIZE	8u
#define RX550_PDB0_BYTES		(RX550_PDB0_ENTRIES * RX550_PDB0_ENTRY_SIZE)
#define RX550_PDB0_COVERAGE	((uint64_t)RX550_PDB0_ENTRIES * RX550_PAGE_SIZE)
#define RX550_PDB0_LEAF_BIT	54u
#define RX550_PDB0_LEAF		(UINT64_C(1) << RX550_PDB0_LEAF_BIT)

/* ── flags activos ─────────────────────────────────────────────────────── */
/* Posiciones: HARDWARE_REQUIREMENT (amdgrtiene PTE_READABLE/WRITEABLE/VALID). */
/* Cual se pone: DESIGN_CHOICE.  Solo se activa lo que se puede justificar. */
#define RX550_PTE_VALID		(UINT64_C(1) << 0)
#define RX550_PTE_READABLE	(UINT64_C(1) << 5)
#define RX550_PTE_WRITEABLE	(UINT64_C(1) << 6)
/* FRAG, bits 7-11: NOT_DETERMINED.  No se tocan. */
/* MTYPE: NO EXISTE en GFX8.  No se inventa. */

enum rx550_pdb0_state {
	RX550_PDB0_EMPTY = 0,
	RX550_PDB0_ALLOCATED,
	RX550_PDB0_INITIALIZED,
	RX550_PDB0_PROGRAMMABLE,
	RX550_PDB0_RETIRED
};

struct rx550_pdb0 {
	enum rx550_pdb0_state		state;
	struct rx550_vram_resource	res;	/* PRESTADO, no poseido   */
	void			       *alloc_ctx;	/* contexto del allocator  */
	rx550_vram_free_fn		freefn;		/* para devolverlo        */
	uint64_t		       *entries;	/* area de staging del caller */
	uint32_t			owner;		/* quien puede mutar      */
	uint32_t			live_entries;
};

/* ── API ────────────────────────────────────────────────────────────────── */

void rx550_pdb0_init(struct rx550_pdb0 *p);

/* EMPTY -> ALLOCATED.  Toma un recurso PRESTADO por el allocator. */
int rx550_pdb0_alloc(struct rx550_pdb0 *p, void *alloc_ctx,
		     rx550_vram_alloc_fn allocfn, rx550_vram_free_fn freefn,
		     uint64_t alignment);

/* ALLOCATED -> INITIALIZED.  `entries` es memoria DEL CALLER: este objeto
 * no asigna, porque la politica de asignacion no es parte de su contrato. */
int rx550_pdb0_init_table(struct rx550_pdb0 *p, uint32_t owner,
			  uint64_t *entries);

int rx550_pdb0_open(struct rx550_pdb0 *p, uint32_t owner);

/* address = SYSTEM_PA.  La conversion a GART ocurre dentro, con GART_START. */
int rx550_pdb0_map_va(struct rx550_pdb0 *p, uint32_t owner,
		      struct rx550_gpuva va, struct rx550_system_pa pa,
		      bool writable);

int rx550_pdb0_unmap_index(struct rx550_pdb0 *p, uint32_t owner,
			   struct rx550_pdb0_index idx);

int rx550_pdb0_lookup(const struct rx550_pdb0 *p, struct rx550_pdb0_index idx,
		      uint64_t *out_entry);

int rx550_pdb0_destroy(struct rx550_pdb0 *p, uint32_t owner);

/* ── funciones puras, sin objeto ────────────────────────────────────────── */

uint64_t rx550_pdb0_encode(struct rx550_gart_addr gart, bool writable);
bool     rx550_pdb0_entry_valid(uint64_t e);
struct rx550_gart_addr rx550_pdb0_entry_addr(uint64_t e);
bool     rx550_pdb0_index_in_range(struct rx550_pdb0_index idx);
struct rx550_pdb0_index rx550_pdb0_index_for_va(struct rx550_gpuva va);
uint64_t rx550_pdb0_tables_for(uint64_t size_bytes);

#endif /* RX550_PDB0_H */
