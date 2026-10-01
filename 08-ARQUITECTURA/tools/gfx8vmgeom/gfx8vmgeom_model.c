/*
 * gfx8vmgeom -- modelo de la geometria GPUVM y su informe.
 *
 * Cada linea del modelo lleva el file:line del corpus de donde sale. Si una
 * de esas lineas cambia, la herramienta deja de compilar la afirmacion, no
 * de seguir dando un numero plausible.
 */
#include "gfx8vmgeom.h"

#include <inttypes.h>
#include <string.h>

/* El valor observado en el host, transcrito de 02-ARQUITECTURA/RESEARCH-LINES.md
 * §16.1 A-8 y §26.11, que lo declaran leido del log del boot. Es la unica
 * observacion de hardware que usa esta herramienta, y entra como CADENA a
 * comparar, no como constante de la que derivar. */
const char *const GG_HOST_OBSERVED_VM_LINE =
	"vm size is 64 GB, 2 levels, block size is 10-bit, fragment size is 9-bit";

/* ------------------------------------------------------------------ */
/* aritmetica del kernel, replicada linea a linea                       */
/* ------------------------------------------------------------------ */

/* amdgpu_vm_get_block_size(), amdgpu_vm.c:2356 */
static unsigned gg_ilog2(uint64_t n)
{
	unsigned r = 0;
	while (n >>= 1)
		r++;
	return r;
}

static unsigned gg_fls64(uint64_t n)
{
	unsigned r = 0;
	while (n) { r++; n >>= 1; }
	return r;
}

static uint64_t gg_roundup_pow2(uint64_t n)
{
	uint64_t r = 1;
	while (r < n)
		r <<= 1;
	return r;
}

static unsigned gg_div_round_up(uint64_t n, uint64_t d)
{
	return (unsigned)(n / d + !!(n % d));
}

static unsigned gg_get_block_size(uint64_t vm_size)
{
	unsigned bits = gg_ilog2(vm_size) + 18;   /* amdgpu_vm.c:2359 */
	if (vm_size <= 8)
		return bits - 9;                       /* :2364 */
	return (bits + 3) / 2;                     /* :2366 */
}

/* amdgpu_vm_pt_level_shift(), amdgpu_vm_pt.c:52 */
static unsigned gg_level_shift(const struct gg_geometry *g, unsigned level)
{
	if (level <= 3)          /* PDB3..PDB0 */
		return 9u * (3u - level) + g->block_size;
	if (level == 4)          /* PTB */
		return 0;
	return ~0u;
}

/* amdgpu_vm_pt_num_entries(), amdgpu_vm_pt.c:75 */
static unsigned gg_num_entries(const struct gg_geometry *g, unsigned level)
{
	unsigned shift = gg_level_shift(g, (unsigned)g->root_level);

	if (level == (unsigned)g->root_level)
		return (unsigned)(((g->max_pfn + (1ULL << shift) - 1) >> shift));
	if (level != 4)
		return 512;
	return 1u << g->block_size;   /* AMDGPU_VM_PTE_COUNT */
}

static unsigned gg_align_up(unsigned v, unsigned a)
{
	return (v + a - 1) & ~(a - 1);
}

/* amdgpu_vm_pt_size(), amdgpu_vm_pt.c:123 */
static unsigned gg_pt_size(const struct gg_geometry *g, unsigned level)
{
	return gg_align_up(gg_num_entries(g, level) * 8u, 4096u);
}

/* ------------------------------------------------------------------ */

void gg_geometry(const struct gg_corpus *c, unsigned phys_ram_gb,
		 struct gg_geometry *g)
{
	unsigned max_size, vm_size, frag;
	uint64_t tmp;
	unsigned max_level = c->max_level;

	memset(g, 0, sizeof(*g));

	/* amdgpu_vm.c:2383  max_size = 1 << (max_bits - 30) */
	max_size = 1u << (c->max_bits - 30);

	/* amdgpu_vm.c:2414-2418  vm_size = roundup_pow_of_two(
	 *                          clamp(phys_ram_gb * 3, min_vm_size, max_size)) */
	{
		unsigned c3 = phys_ram_gb * 3u;
		if (c3 < c->min_vm_size_gb)
			c3 = c->min_vm_size_gb;
		if (c3 > max_size)
			c3 = max_size;
		vm_size = (unsigned)gg_roundup_pow2(c3);
	}
	g->vm_size_gb = vm_size;

	/* amdgpu_vm.c:2421  max_pfn = vm_size << 18 */
	g->max_pfn = (uint64_t)vm_size << 18;
	g->max_level_unused = 0;
	g->ptba_depth_field = 0;               /* se rellena abajo */

	/* amdgpu_vm.c:2425-2429 */
	tmp = gg_roundup_pow2(g->max_pfn);
	/* amdgpu_vm_block_size == -1 en esta ruta, luego no hay ">>=" */
	tmp = gg_div_round_up(gg_fls64(tmp) - 1, 9) - 1;
	g->num_level = (max_level < (unsigned)tmp) ? max_level : (unsigned)tmp;

	/* amdgpu_vm.c:2431-2445 */
	switch (g->num_level) {
	case 4: g->root_level = 0; break;   /* PDB3 */
	case 3: g->root_level = 1; break;   /* PDB2 */
	case 2: g->root_level = 2; break;   /* PDB1 */
	case 1: g->root_level = 3; break;   /* PDB0 */
	default:
		g->root_level = 0;
		break;                        /* amdgpu_vm.c:2444 dev_err */
	}

	/* amdgpu_vm.c:2446-2454
	 * OJO: en la rama num_level == 1 el driver pasa `tmp` a
	 * amdgpu_vm_get_block_size(), no `vm_size`. Es la razon de que
	 * block_size sea 10 y no 13 con 64 GB de VM. */
	if (g->num_level > 1)
		g->block_size = 9;
	else
		g->block_size = gg_get_block_size(tmp);

	/* amdgpu_vm.c:2456-2459 */
	frag = c->fragment_size_default;
	g->fragment_size = frag;

	/* gmc_v8_0.c:894 PAGE_TABLE_DEPTH, 0 para context0
	 * gmc_v8_0.c:931 PAGE_TABLE_BLOCK_SIZE, solo para context1-15 */
	g->ptba_depth_field = 1u;           /* el que se escribe para VMID 1..15 */
	g->ptba_block_field = g->block_size - 9u;

	/* geometria de tablas */
	g->pdb0_entries = gg_num_entries(g, (unsigned)g->root_level);
	g->pdb0_bytes   = gg_pt_size(g, (unsigned)g->root_level);
	g->ptb_entries  = gg_num_entries(g, 4);
	g->ptb_bytes    = gg_pt_size(g, 4);
	g->ptb_pages    = g->ptb_entries;
	g->ptb_kib      = g->ptb_entries * 4u;         /* 4 KiB por pagina */
	g->n_ptb        = (g->max_pfn + g->ptb_entries - 1) / g->ptb_entries;
	g->leaf_table_bytes = g->n_ptb * g->ptb_bytes;

	/* ancho de GPUVA
	 * el indice del root ocupa (log2(max_pfn) - block_size) bits
	 * el indice de la hoja ocupa block_size bits
	 * el offset ocupa 12 bits */
	g->va_bits_pdb0_index = gg_ilog2(g->max_pfn) - g->block_size;
	g->va_bits_ptb_index  = g->block_size;
	g->va_bits_offset     = 12;
	g->va_bits_total      = g->va_bits_pdb0_index + g->va_bits_ptb_index
	                      + g->va_bits_offset;
}

/* ------------------------------------------------------------------ */
/* informe                                                              */
/* ------------------------------------------------------------------ */

#define ROW(label, fmt, ...)                                                 \
	do {                                                                  \
		fprintf(out, "  %-34s " fmt "\n", label, ##__VA_ARGS__);      \
	} while (0)

int gg_report(const struct gg_corpus *c, const struct gg_geometry *g,
	      unsigned phys_ram_gb, FILE *out)
{
	int bad = 0;
	char derived[160];

	snprintf(derived, sizeof(derived),
		 "vm size is %u GB, %u levels, block size is %u-bit, "
		 "fragment size is %u-bit",
		 g->vm_size_gb, g->num_level + 1, g->block_size,
		 g->fragment_size);

	fprintf(out, "== corpus ==\n");
	fprintf(out, "  %-34s %s\n", "fuentes", c->src_root);
	fprintf(out, "  %-34s %s\n", "cabecera", c->hdr_root);
	ROW("amdgpu_vm_adjust_size(min,frag,maxlvl,b)", "%u, %u, %u, %u",
	    c->min_vm_size_gb, c->fragment_size_default, c->max_level,
	    c->max_bits);
	ROW("pte_addr_mask", "0x%012" PRIx64 "  -> %u bits de PA",
	    c->pte_addr_mask, c->pa_bits);
	ROW("CHIP_POLARIS12 < CHIP_VEGA10", "%ld < %ld  -> %s",
	    c->ord_polaris12, c->ord_vega10,
	    c->polaris12_before_vega10 ? "las ramas GMC9 NO aplican" : "SI aplican");
	ROW("GC_HWIP", "%u.%u.%u  -> PDE_PTE en bit %u",
	    c->gfx_major, c->gfx_minor, c->gfx_rev, c->bit_pde_pte);

	fprintf(out, "\n== bits de la PTE (de amdgpu_vm.h) ==\n");
	ROW("VALID/SYSTEM/SNOOPED/TMZ", "%u / %u / %u / %u",
	    c->bit_valid, c->bit_system, c->bit_snooped, c->bit_tmz);
	ROW("EXECUTABLE/READABLE/WRITEABLE", "%u / %u / %u",
	    c->bit_executable, c->bit_readable, c->bit_writeable);
	ROW("FRAG", "shift %u, ancho %u bits", c->frag_shift, c->frag_width);
	ROW("PDE_PTE / PRT / LOG / TF", "%u / %u / %u / %u",
	    c->bit_pde_pte, c->bit_prt, c->bit_log, c->bit_tf);
	ROW("NOALLOC / BFS", "%u / %u", c->bit_noalloc, c->bit_bfs);

	fprintf(out, "\n== modelo (phys_ram_gb = %u) ==\n", phys_ram_gb);
	ROW("vm_size", "%u GB", g->vm_size_gb);
	ROW("max_pfn", "%" PRIu64 " paginas", g->max_pfn);
	ROW("num_level (directorios)", "%u", g->num_level);
	ROW("root_level", "%u (PDB0)", g->root_level);
	ROW("block_size", "%u bits", g->block_size);
	ROW("fragment_size", "%u", g->fragment_size);
	ROW("PAGE_TABLE_DEPTH escrito", "%u", g->ptba_depth_field);
	ROW("PAGE_TABLE_BLOCK_SIZE escrito", "%u", g->ptba_block_field);
	ROW("PDB0 entradas / bytes", "%u / %u", g->pdb0_entries, g->pdb0_bytes);
	ROW("PTB entradas / bytes", "%u / %u", g->ptb_entries, g->ptb_bytes);
	ROW("PTB cubre", "%u paginas = %u KiB = %u MiB",
	    g->ptb_pages, g->ptb_kib, g->ptb_kib / 1024);
	ROW("nº PTB para max_pfn", "%" PRIu64, g->n_ptb);
	ROW("suma de tablas hoja", "%" PRIu64 " B = %" PRIu64 " MiB",
	    g->leaf_table_bytes, g->leaf_table_bytes / (1024 * 1024));
	ROW("GPUVA", "[%u] root | [%u] hoja | [%u] offset = %u bits",
	    g->va_bits_pdb0_index, g->va_bits_ptb_index, g->va_bits_offset,
	    g->va_bits_total);

	fprintf(out, "\n== contraste con el host ==\n");
	fprintf(out, "  observado : %s\n", GG_HOST_OBSERVED_VM_LINE);
	fprintf(out, "  derivado  : %s\n", derived);
	if (strcmp(derived, GG_HOST_OBSERVED_VM_LINE) == 0) {
		fprintf(out, "  RESULT    : COINCIDE (block_size=%u, no 9)\n",
			g->block_size);
	} else {
		fprintf(out, "  RESULT    : DIFIERE\n");
		bad++;
	}

	/* la hipotesis que 014-documento afirma
	 * (block_size = 9, 512 entradas por nivel) */
	if (g->block_size == 9) {
		fprintf(out, "  CONTRASTE 014: el modelo NO distingue, revisar\n");
		bad++;
	} else {
		fprintf(out,
			"  CONTRASTE 014: block_size=%u != 9  -> la rama\n"
			"    (num_level > 1) de amdgpu_vm.c:2452 NO es la que\n"
			"    corre; corre la de :2454, que pasa tmp y no vm_size\n",
			g->block_size);
	}

	return bad;
}

#undef ROW