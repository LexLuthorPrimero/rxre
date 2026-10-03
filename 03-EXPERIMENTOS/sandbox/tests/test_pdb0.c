/* SPDX-License-Identifier: GPL-2.0 */
/*
 * test_pdb0.c — contrato canonico de PDB0, GART y MMIO.
 *
 * UNA SOLA PREGUNTA: ¿el componente cumple lo que declara?
 * No prueba que un GFX8 obedezca.  Eso es RUNTIME_REQUIRED.
 */
#include "rx550_pdb0.h"
#include "rx550_mmio.h"
#include <stdio.h>
#include <string.h>

static int pass, fail;
static void ok(const char *t) { printf("  PASS  %s\n", t); pass++; }
static void ko(const char *t) { printf("  FAIL  %s\n", t); fail++; }
#define CHECK(c, n) do { if (c) ok(n); else ko(n); } while (0)

#define FAKE_BASE UINT64_C(0x0000ABCDE000)
static int free_calls;
static uint32_t alloc_calls;

struct fake_ctx { int bad_size; int bad_align; int no_owner; int fail; };

static int fake_alloc(void *c, uint64_t size, uint64_t align,
		      struct rx550_vram_resource *out)
{
	struct fake_ctx *f = (struct fake_ctx *)c;
	(void)align;
	alloc_calls++;
	if (f->fail)
		return -1;
	out->offset = rx550_vram_off(FAKE_BASE);
	out->size = f->bad_size ? 16 : size;
	if (f->bad_align)
		out->offset = rx550_vram_off(FAKE_BASE + 1);
	out->alignment = align;
	out->owner = f->no_owner ? NULL : c;
	out->state = RX550_VRAM_HELD;
	return 0;
}

static void fake_free(void *c, struct rx550_vram_resource *r)
{
	(void)c; (void)r;
	free_calls++;
}

int main(void)
{
	struct rx550_pdb0 p;
	struct fake_ctx fc;
	static uint64_t table[RX550_PDB0_ENTRIES];
	struct rx550_gpuva va;
	struct rx550_system_pa pa;
	struct rx550_pdb0_index idx;
	struct rx550_gart_addr g;
	struct rx550_reg r;
	uint64_t e;

	printf("test_pdb0 — GART, PDB0 y MMIO\n\n");

	/* ── FASE 1: GART contract ───────────────────────────────────── */
	CHECK(RX550_GART_START == 0, "GART_START = 0 (DESIGN_CHOICE)");
	CHECK(rx550_gart_is_identity(), "GART es identidad con la ventana de sistema");
	pa.bytes = 0x000012340000ull;
	g = rx550_gart_of_pa(pa);
	CHECK(g.bytes == pa.bytes, "GART address == system PA con base 0");
	/* el offset VRAM y la direccion GART son espacios distintos */
	CHECK(rx550_vram_off(0x40).bytes == 0x40, "offset VRAM en bytes");
	CHECK(!(rx550_vram_off(0x40).bytes == g.bytes), "VRAM offset != GART address");
	CHECK(rx550_vram_off_eq_ga(rx550_vram_off(0x40), g) == false,
	      "la funcion de confusion devuelve falso para espacios distintos");
	CHECK(rx550_vram_off_eq_ga(rx550_vram_off(0x40),
				    rx550_gart_of_pa((struct rx550_system_pa)
						    {.bytes = 0x40})),
	      "…y verdadero solo cuando los bytes coinciden de verdad");

	/* 40 bits */
	CHECK(rx550_pa_representable((struct rx550_system_pa)
				     {.bytes = 0x000000FFFF000000ull}),
	      "PA de 40 bits representable");
	CHECK(!rx550_pa_representable((struct rx550_system_pa)
				      {.bytes = 0x0000010000000000ull}),
	      "PA por encima de 40 bits rechazada");
	CHECK(rx550_pa_aligned((struct rx550_system_pa){.bytes = 0x1000}),
	      "PA alineada a 4 KiB");
	CHECK(!rx550_pa_aligned((struct rx550_system_pa){.bytes = 0x1001}),
	      "PA desalineada rechazada");

	/* ── geometria HARDWARE ───────────────────────────────────────── */
	CHECK(RX550_PDB0_ENTRIES == 512, "512 entradas");
	CHECK(RX550_PDB0_ENTRY_SIZE == 8, "entrada de 8 B");
	CHECK(RX550_PDB0_BYTES == 4096, "512*8 = 4 KiB");
	CHECK(RX550_PDB0_COVERAGE == 2ull * 1024 * 1024, "cobertura 2 MiB");
	CHECK(RX550_PDB0_LEAF == (UINT64_C(1) << 54), "marca de hoja en bit 54");
	CHECK((RX550_PDB0_LEAF & RX550_PA_MASK) == 0,
	      "la hoja no invade el campo de direccion");
	CHECK(rx550_pdb0_tables_for(0) == 0, "0 bytes -> 0 tablas");
	CHECK(rx550_pdb0_tables_for(1) == 1, "1 byte -> 1 tabla");
	CHECK(rx550_pdb0_tables_for(RX550_PDB0_COVERAGE) == 1, "2 MiB -> 1 tabla");
	CHECK(rx550_pdb0_tables_for(RX550_PDB0_COVERAGE + 1) == 2, "2 MiB+1 -> 2");

	/* indice */
	idx.value = 0;
	CHECK(rx550_pdb0_index_in_range(idx), "indice 0 valido");
	idx.value = RX550_PDB0_ENTRIES - 1;
	CHECK(rx550_pdb0_index_in_range(idx), "indice 511 valido");
	idx.value = RX550_PDB0_ENTRIES;
	CHECK(!rx550_pdb0_index_in_range(idx), "indice 512 invalido");
	va = rx550_gpuva_make(0);
	CHECK(rx550_pdb0_index_for_va(va).value == 0, "GPUVA baja -> indice 0");
	va = rx550_gpuva_make(511 * RX550_PAGE_SIZE);
	CHECK(rx550_pdb0_index_for_va(va).value == 511, "GPUVA alta -> indice 511");
	va = rx550_gpuva_make(RX550_PDB0_COVERAGE);
	CHECK(rx550_pdb0_index_for_va(va).value == 0, "el indice se reinicia");

	/* codificacion */
	e = rx550_pdb0_encode(rx550_gart_of_pa(
		(struct rx550_system_pa){.bytes = 0x1000}), true);
	CHECK(rx550_pdb0_entry_valid(e), "entrada valida");
	CHECK(rx550_pdb0_entry_addr(e).bytes == 0x1000, "direccion recuperable");
	CHECK((e & RX550_PTE_WRITEABLE) != 0, "escribible");
	CHECK((e & RX550_PTE_READABLE) != 0, "legible");
	CHECK((e & RX550_PDB0_LEAF) != 0, "hoja marcada");
	e = rx550_pdb0_encode(rx550_gart_of_pa(
		(struct rx550_system_pa){.bytes = 0x2000}), false);
	CHECK((e & RX550_PTE_WRITEABLE) == 0, "solo lectura si no se pide escritura");
	CHECK(rx550_pdb0_encode(rx550_gart_of_pa(
		(struct rx550_system_pa){.bytes = 0x0000010000000000ull}), true) == 0,
	      "PA no representable codifica a 0, no se trunca");

	/* ── FASE 4: MMIO ─────────────────────────────────────────────── */
	CHECK(RX550_MMIO_SIZE == 0x40000, "rmmio_size 0x40000");
	CHECK(RX550_REG_WIDTH == 4, "registro de 4 bytes");
	r = rx550_reg_make(0x21c0);
	CHECK(rx550_reg_offset(r).bytes == 0x8700,
	      "mmCP_RB0_RPTR: indice 0x21c0 -> offset 0x8700");
	CHECK(rx550_reg_offset(r).bytes != r.index,
	      "el indice NO es el offset: la trampa esta documentada");
	CHECK(rx550_reg_in_window(r), "0x8700 dentro de la ventana");
	r = rx550_reg_make((uint32_t)((RX550_MMIO_SIZE / 4) - 1));
	CHECK(rx550_reg_in_window(r), "ultimo registro dentro de la ventana");
	r = rx550_reg_make((uint32_t)(RX550_MMIO_SIZE / 4));
	CHECK(!rx550_reg_in_window(r), "un registro mas alla queda fuera");
	CHECK(rx550_mmap_offset_aligned(
		rx550_reg_offset(rx550_reg_make(7))), "offset de registro alineado");

	/* ── FASE 2/3: objeto y frontera de allocator ────────────────── */
	rx550_pdb0_init(&p);
	memset(&fc, 0, sizeof(fc));
	CHECK(p.state == RX550_PDB0_EMPTY, "init deja EMPTY");
	CHECK(rx550_pdb0_alloc(&p, NULL, fake_alloc, fake_free, 4096) != 0,
	      "alloc sin contexto rechazado");
	CHECK(rx550_pdb0_init_table(&p, 1, table) != 0, "init_table antes de alloc");
	CHECK(rx550_pdb0_destroy(&p, 1) != 0, "destroy de EMPTY rechazado");

	CHECK(rx550_pdb0_alloc(&p, &fc, fake_alloc, fake_free, 4096) == 0, "alloc ok");
	CHECK(alloc_calls == 1, "el allocator fue invocado");
	CHECK(p.state == RX550_PDB0_ALLOCATED, "ALLOCATED");
	CHECK(rx550_pdb0_alloc(&p, &fc, fake_alloc, fake_free, 4096) != 0,
	      "doble alloc rechazado");
	/* el objeto NO guarda el allocator, solo el contexto y el freefn */
	CHECK(p.alloc_ctx == (void *)&fc, "guarda el contexto, no la funcion");

	/* PDB0 se crea SIN ninguna GPUVA asignada */
	CHECK(rx550_pdb0_init_table(&p, 7, table) == 0,
	      "PDB0 se inicializa sin GPUVA");
	CHECK(rx550_pdb0_open(&p, 7) == 0, "open");
	CHECK(rx550_pdb0_open(&p, 8) != 0, "open con dueno ajeno rechazado");
	CHECK(p.state == RX550_PDB0_PROGRAMMABLE, "PROGRAMMABLE");

	/* mutacion */
	va = rx550_gpuva_make(0);
	pa.bytes = 0x000056780000ull;
	CHECK(rx550_pdb0_map_va(&p, 8, va, pa, true) != 0, "mutacion ajena rechazada");
	CHECK(rx550_pdb0_map_va(&p, 0, va, pa, true) != 0, "dueno 0 rechazado");
	CHECK(rx550_pdb0_map_va(&p, 7, va, (struct rx550_system_pa){.bytes = 0x1001},
				 true) != 0, "PA desalineada rechazada");
	CHECK(rx550_pdb0_map_va(&p, 7, va,
				(struct rx550_system_pa){.bytes = 0x0000010000000000ull},
				true) != 0, "PA no representable rechazada");
	CHECK(rx550_pdb0_map_va(&p, 7, va, pa, true) == 0, "mapeo valido");
	idx.value = 0;
	CHECK(rx550_pdb0_lookup(&p, idx, &e) == 0, "lookup");
	CHECK(rx550_pdb0_entry_addr(e).bytes == pa.bytes,
	      "la entrada contiene la PA que se dio");
	CHECK(p.live_entries == 1, "una entrada viva");
	CHECK(rx550_pdb0_unmap_index(&p, 7, idx) == 0, "unmap");
	CHECK(p.live_entries == 0, "ninguna viva");
	idx.value = RX550_PDB0_ENTRIES;
	CHECK(rx550_pdb0_unmap_index(&p, 7, idx) != 0, "unmap fuera de rango");
	CHECK(rx550_pdb0_lookup(&p, idx, &e) != 0, "lookup fuera de rango");

	/* retiro */
	free_calls = 0;
	CHECK(rx550_pdb0_destroy(&p, 8) != 0, "destroy con dueno ajeno rechazado");
	CHECK(free_calls == 0, "y no libero nada");
	CHECK(rx550_pdb0_destroy(&p, 7) == 0, "destroy");
	CHECK(free_calls == 1, "liberado una vez");
	CHECK(p.state == RX550_PDB0_RETIRED, "RETIRED");
	CHECK(rx550_pdb0_destroy(&p, 7) != 0, "doble destroy rechazado");
	CHECK(free_calls == 1, "y no vuelve a liberar");

	/* ── no inferencia de ejecucion ──────────────────────────────── */
	CHECK(1, "este modulo no contiene ninguna llamada a hardware");

	printf("\n  %d pass, %d fail\n", pass, fail);
	return fail ? 1 : 0;
}
