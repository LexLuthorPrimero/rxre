/* SPDX-License-Identifier: GPL-2.0 */
/*
 * rx550_pdb0.c — implementacion.  CPU puro.  Sin kernel, sin device.
 */
#include "rx550_pdb0.h"

/* ── funciones puras ───────────────────────────────────────────────────── */

bool rx550_pdb0_entry_valid(uint64_t e)
{
	return (e & RX550_PTE_VALID) != 0;
}

uint64_t rx550_pdb0_encode(struct rx550_gart_addr gart, bool writable)
{
	uint64_t e;

	/* Una PA por encima de 40 bits no es representable.  Devolver 0, que
	 * ademas es una entrada no valida, es mejor que truncar. */
	if ((gart.bytes & ~RX550_PA_MASK) != 0)
		return 0;

	e = (gart.bytes & RX550_PA_MASK) | RX550_PDB0_LEAF | RX550_PTE_VALID |
	    RX550_PTE_READABLE;

	if (writable)
		e |= RX550_PTE_WRITEABLE;

	return e;
}

struct rx550_gart_addr rx550_pdb0_entry_addr(uint64_t e)
{
	struct rx550_gart_addr g;
	g.bytes = e & RX550_PA_MASK;
	return g;
}

bool rx550_pdb0_index_in_range(struct rx550_pdb0_index idx)
{
	return idx.value < RX550_PDB0_ENTRIES;
}

struct rx550_pdb0_index rx550_pdb0_index_for_va(struct rx550_gpuva va)
{
	struct rx550_pdb0_index i;
	i.value = (uint32_t)((va.bytes >> RX550_PAGE_SHIFT) &
			     (RX550_PDB0_ENTRIES - 1u));
	return i;
}

uint64_t rx550_pdb0_tables_for(uint64_t size_bytes)
{
	uint64_t pages;

	if (size_bytes == 0)
		return 0;

	pages = (size_bytes + (RX550_PAGE_SIZE - 1)) / RX550_PAGE_SIZE;
	return (pages + (RX550_PDB0_ENTRIES - 1)) / RX550_PDB0_ENTRIES;
}

/* ── objeto ─────────────────────────────────────────────────────────────── */

void rx550_pdb0_init(struct rx550_pdb0 *p)
{
	p->state = RX550_PDB0_EMPTY;
	rx550_vram_resource_reset(&p->res);
	p->alloc_ctx = NULL;
	p->freefn = NULL;
	p->entries = NULL;
	p->owner = 0;
	p->live_entries = 0;
}

int rx550_pdb0_alloc(struct rx550_pdb0 *p, void *alloc_ctx,
		     rx550_vram_alloc_fn allocfn, rx550_vram_free_fn freefn,
		     uint64_t alignment)
{
	struct rx550_vram_resource out;
	int rc;

	if (p->state != RX550_PDB0_EMPTY)
		return -1;
	if (alloc_ctx == NULL || allocfn == NULL)
		return -1;
	if (alignment == 0)
		return RX550_VRAM_ERR_ALIGN;

	rx550_vram_resource_reset(&out);

	/* El motivo se PROPAGA.  Antes todo se colapsaba a -1, que hacia
	 * imposible distinguir "no cabe" de "el backend fallo" de "el backend
	 * devolvio basura" en el punto de entrada.  Los tres siguen siendo
	 * fallo, asi que las comprobaciones de los callers (que comparan != 0)
	 * siguen valiendo; lo que cambia es que ahora se puede decidir. */
	rc = allocfn(alloc_ctx, RX550_PDB0_BYTES, alignment, &out);
	if (rc != RX550_VRAM_OK)
		return rc;

	/* El allocator puede devolver algo inservible.  Se rechaza aqui, y se
	 * dice cual de las tres cosas fallo. */
	if (rx550_vram_resource_valid(&out, RX550_PDB0_BYTES, alignment) != 0)
		return RX550_VRAM_ERR_INVALIDO;

	p->res = out;
	p->alloc_ctx = alloc_ctx;
	p->freefn = freefn;
	p->state = RX550_PDB0_ALLOCATED;
	return 0;
}

int rx550_pdb0_init_table(struct rx550_pdb0 *p, uint32_t owner, uint64_t *entries)
{
	if (p->state != RX550_PDB0_ALLOCATED)
		return -1;
	if (owner == 0)
		return -1;

	/* La tabla tiene que estar alineada a 4 bytes: es un array de u64. */
	if ((entries != NULL) &&
	    ((uintptr_t)entries % sizeof(uint64_t)) != 0)
		return -1;

	p->entries = entries;
	p->owner = owner;
	p->live_entries = 0;
	p->state = RX550_PDB0_INITIALIZED;
	return 0;
}

int rx550_pdb0_open(struct rx550_pdb0 *p, uint32_t owner)
{
	if (p->state != RX550_PDB0_INITIALIZED)
		return -1;
	if (owner == 0 || owner != p->owner)
		return -1;

	p->state = RX550_PDB0_PROGRAMMABLE;
	return 0;
}

int rx550_pdb0_map_va(struct rx550_pdb0 *p, uint32_t owner,
		      struct rx550_gpuva va, struct rx550_system_pa pa,
		      bool writable)
{
	struct rx550_pdb0_index idx;
	struct rx550_gart_addr gart;
	uint64_t e;

	if (p->state != RX550_PDB0_PROGRAMMABLE)
		return -1;
	if (owner == 0 || owner != p->owner)
		return -1;
	if (p->entries == NULL)
		return -1;

	/* La PA tiene que estar alineada a pagina y ser representable. */
	if (!rx550_pa_aligned(pa))
		return -1;
	if (!rx550_pa_representable(pa))
		return -1;

	/* La GPUVA debe caer en la cobertura de ESTA tabla. */
	idx = rx550_pdb0_index_for_va(va);
	if (!rx550_pdb0_index_in_range(idx))
		return -1;

	gart = rx550_gart_of_pa(pa);
	e = rx550_pdb0_encode(gart, writable);
	if (e == 0)
		return -1;

	if (!rx550_pdb0_entry_valid(p->entries[idx.value]))
		p->live_entries++;

	p->entries[idx.value] = e;
	return 0;
}

int rx550_pdb0_unmap_index(struct rx550_pdb0 *p, uint32_t owner,
			   struct rx550_pdb0_index idx)
{
	if (p->state != RX550_PDB0_PROGRAMMABLE)
		return -1;
	if (owner == 0 || owner != p->owner)
		return -1;
	if (p->entries == NULL)
		return -1;
	if (!rx550_pdb0_index_in_range(idx))
		return -1;

	if (rx550_pdb0_entry_valid(p->entries[idx.value])) {
		p->entries[idx.value] = 0;
		p->live_entries--;
	}
	return 0;
}

int rx550_pdb0_lookup(const struct rx550_pdb0 *p, struct rx550_pdb0_index idx,
		      uint64_t *out_entry)
{
	if (p->state != RX550_PDB0_PROGRAMMABLE)
		return -1;
	if (!rx550_pdb0_index_in_range(idx))
		return -1;
	if (out_entry == NULL || p->entries == NULL)
		return -1;

	*out_entry = p->entries[idx.value];
	return 0;
}

int rx550_pdb0_destroy(struct rx550_pdb0 *p, uint32_t owner)
{
	if (p->state == RX550_PDB0_EMPTY)
		return -1;
	if (p->state == RX550_PDB0_RETIRED)
		return -1;			/* doble retiro rechazado */
	if (owner == 0 || owner != p->owner)
		return -1;

	if (p->freefn != NULL && p->alloc_ctx != NULL)
		p->freefn(p->alloc_ctx, &p->res);

	rx550_vram_resource_reset(&p->res);
	p->alloc_ctx = NULL;
	p->freefn = NULL;
	p->entries = NULL;
	p->live_entries = 0;
	p->state = RX550_PDB0_RETIRED;
	return 0;
}
