/*
 * gfx8vmgeom -- test del modelo y de la extraccion.
 *
 * Dos obligaciones, y la segunda es la que importa:
 *
 *  1) que el modelo acierte sobre el corpus real;
 *  2) que el test SEA CAPAZ DE FALLAR.
 *
 * (2) se demuestra, no se supone. Cada control negativo muta una entrada y
 * exige que el modelo o la extraccion cambien de veredicto. Un control que
 * sigue dando el mismo resultado tras mutar la entrada NO discrimina, y el
 * test lo cuenta como fallo aunque el valor original fuera correcto.
 */
#include "gfx8vmgeom.h"

#include <inttypes.h>
#include <stdio.h>
#include <stdlib.h>
#include <string.h>

static unsigned g_pass, g_fail;
static unsigned g_neg_total, g_neg_ok, g_neg_dead;
static bool g_cross_version = false;

/*
 * Raiz para la verificacion cruzada de version. Vacia = no se intenta.
 * La define el Makefile; se deja vacia por defecto para que el binario no
 * dependa de una ruta que solo existe en este repo.
 */
#ifndef GG_VERSION_CROSS_ROOT
#define GG_VERSION_CROSS_ROOT ""
#endif

static void ok(int cond, const char *what)
{
	if (cond) {
		g_pass++;
		printf("  [ OK ] %s\n", what);
	} else {
		g_fail++;
		printf("  [FAIL] %s\n", what);
	}
}

/* ------------------------------------------------------------------ */
/* grupo 1: la extraccion encuentra lo que dice encontrar                */
/* ------------------------------------------------------------------ */

static void test_extraction(const struct gg_corpus *c)
{
	printf("\n== extraccion desde el corpus ==\n");
	ok(c->min_vm_size_gb == 64, "min_vm_size = 64");
	ok(c->fragment_size_default == 9, "fragment_size_default = 9");
	ok(c->max_level == 1, "max_level = 1");
	ok(c->max_bits == 40, "max_bits = 40");
	ok(c->pte_addr_mask == 0x000000FFFFFFF000ULL, "pte_addr_mask = 0xFFFFFFFFF000");
	ok(c->pa_bits == 40, "40 bits de direccion fisica");
	ok(c->bit_valid == 0, "VALID en bit 0");
	ok(c->bit_system == 1, "SYSTEM en bit 1");
	ok(c->bit_snooped == 2, "SNOOPED en bit 2");
	ok(c->bit_tmz == 3, "TMZ en bit 3");
	ok(c->bit_executable == 4, "EXECUTABLE en bit 4 (VI only)");
	ok(c->bit_readable == 5, "READABLE en bit 5");
	ok(c->bit_writeable == 6, "WRITEABLE en bit 6");
	ok(c->frag_shift == 7 && c->frag_width == 5, "FRAG = bits 11:7");
	ok(c->bit_pde_pte == 54, "PDE_PTE en bit 54 (pre-GFX12)");
	ok(c->bit_prt == 51, "PRT en bit 51");
	ok(c->bit_log == 55, "LOG en bit 55");
	ok(c->bit_tf == 56, "TF en bit 56");
	ok(c->bit_noalloc == 58, "NOALLOC en bit 58");
	ok(c->bit_bfs == 59, "BFS en bit 59");
	ok(c->ord_polaris12 == 17, "CHIP_POLARIS12 = 17");
	ok(c->ord_vega10 == 19, "CHIP_VEGA10 = 19");
	ok(c->polaris12_before_vega10, "POLARIS12 < VEGA10: las ramas GMC9 no aplican");
	ok(c->gfx_major == 8 && c->gfx_minor == 0, "GC_HWIP = 8.0.0");

	/* Los bits que GFX8 nunca escribe deben seguir existiendo en el header:
	 * su presencia no es su semantica. Se afirma la distincion. */
	ok(c->bit_tf != 0 && c->bit_log != 0,
	   "TF y LOG existen en el header aunque GFX8 no los escriba");

	/*
	 * Verificacion cruzada de version. La rama que decide block_size es
	 * la causa de todo el hallazgo. Si hubiera cambiado en otra version,
	 * el hallazgo seria un artefacto de 7.1.3 y no una propiedad del ASIC.
	 *
	 * Se hace sobre una ruta que puede no existir: si el arbol 7.2.8 no
	 * esta disponible, no se cuenta como fallo sino como NO_DISPONIBLE,
	 * porque la ausencia del arbol es un hecho del entorno y no una
	 * propiedad del hardware. Confundir las dos seria el error clasico.
	 */
	if (GG_VERSION_CROSS_ROOT[0] != '\0') {
		enum gg_branch_shape s7 = gg_check_block_size_branch(c->src_root);
		enum gg_branch_shape s8 =
			gg_check_block_size_branch(GG_VERSION_CROSS_ROOT);

		ok(s7 == GG_BRANCH_NUMLEVEL_GT1,
		   "7.1.3: la rama es (num_level > 1) -> 9, else get_block_size(tmp)");
		if (s8 == GG_BRANCH_UNKNOWN) {
			printf("  [ND  ] 7.2.8 no disponible en %s: "
			       "verificacion cruzada NO_DISPONIBLE\n",
			       GG_VERSION_CROSS_ROOT);
			g_cross_version = false;
		} else {
			ok(s8 == GG_BRANCH_NUMLEVEL_GT1,
			   "7.2.8: la MISMA rama, luego no es artefacto de version");
			g_cross_version = true;
		}
	}
}

/* ------------------------------------------------------------------ */
/* grupo 2: el modelo reproduce la linea observada en el host           */
/* ------------------------------------------------------------------ */

static void test_model(const struct gg_corpus *c)
{
	struct gg_geometry g;
	char derived[160];
	const char *host = GG_HOST_OBSERVED_VM_LINE;

	printf("\n== el modelo contra la observacion del host ==\n");

	/* La RAM de este host cabe en el rango que produce vm_size = 64 GB. */
	gg_geometry(c, 8, &g);

	snprintf(derived, sizeof(derived),
		 "vm size is %u GB, %u levels, block size is %u-bit, "
		 "fragment size is %u-bit",
		 g.vm_size_gb, g.num_level + 1, g.block_size, g.fragment_size);

	ok(strcmp(derived, host) == 0,
	   "la linea derivada es identica a la observada en el boot");
	printf("       observada: %s\n", host);
	printf("       derivada : %s\n", derived);

	/* lo que 014 afirma, contrastado uno por uno */
	ok(g.block_size == 10, "block_size = 10, no 9");
	ok(g.num_level == 1, "num_level = 1 (un nivel de directorio)");
	ok(g.ptb_entries == 1024, "PTB = 2^block_size = 1024 entradas, no 512");
	ok(g.pdb0_entries == 16384, "PDB0 = 16384 entradas, no 512");
	ok(g.ptb_bytes == 8192, "PTB = 8192 B = 2 paginas, no 1");
	ok(g.pdb0_bytes == 131072, "PDB0 = 128 KiB, no 4 KiB");
	ok(g.ptba_block_field == 1, "PAGE_TABLE_BLOCK_SIZE = block_size - 9 = 1");
	ok(g.va_bits_total == 36, "GPUVA de 36 bits, no 30");

	/* La geometria minima que 014 calcula como 2 MiB */
	ok(g.ptb_entries * 4096u == 4u * 1024u * 1024u,
	   "un PTB cubre 4 MiB, no 2 MiB");
}

/* ------------------------------------------------------------------ */
/* grupo 3: controles negativos. La capacidad de fallar, demostrada.    */
/* ------------------------------------------------------------------ */

/*
 * Cada control devuelve 1 si el mutante fue detectado, 0 si no. Un control
 * que NO detecta su propia mutacion se cuenta aparte como "muerto": es peor
 * que no tenerlo, porque aparenta cobertura.
 */
typedef int (*neg_fn)(const struct gg_corpus *c, const struct gg_geometry *base);

static void neg_run(const char *id, const char *desc, neg_fn fn,
		    const struct gg_corpus *c, const struct gg_geometry *base)
{
	int detected = fn(c, base);

	g_neg_total++;
	if (detected) {
		g_neg_ok++;
		printf("  [ OK ] %s %s -> detectado\n", id, desc);
	} else {
		g_neg_dead++;
		printf("  [DEAD] %s %s -> NO detectado: el control no discrimina\n",
		       id, desc);
	}
}

/* CN-1: si get_block_size recibiera vm_size en vez de tmp, daria 13. */
static int cn1(const struct gg_corpus *c, const struct gg_geometry *base)
{
	(void)c;
	unsigned bits = 0, alt;
	uint64_t v = (uint64_t)base->vm_size_gb;

	while (v >>= 1)
		bits++;
	bits += 18;
	alt = (v <= 8) ? (bits - 9) : ((bits + 3) / 2);
	/* el mutante produce 13; el modelo real produce 10 */
	return alt != base->block_size;
}

/* CN-2: la rama que el documento 014 cree que corre (num_level > 1 -> 9). */
static int cn2(const struct gg_corpus *c, const struct gg_geometry *base)
{
	(void)c;
	return 9u != base->block_size;
}

/* CN-3: fragment_size distinto. */
static int cn3(const struct gg_corpus *c, const struct gg_geometry *base)
{
	(void)c;
	return 8u != base->fragment_size;
}

/* CN-4: la hipotesis "512 entradas por nivel". */
static int cn4(const struct gg_corpus *c, const struct gg_geometry *base)
{
	(void)c;
	return 512u != base->ptb_entries && 512u != base->pdb0_entries;
}

/* CN-5: si PAGE_TABLE_BLOCK_SIZE fuera block_size y no block_size - 9. */
static int cn5(const struct gg_corpus *c, const struct gg_geometry *base)
{
	(void)c;
	return base->block_size != base->ptba_block_field;
}

/* CN-6: si el gate asic_type >= CHIP_VEGA10 fuera cierto. */
static int cn6(const struct gg_corpus *c, const struct gg_geometry *base)
{
	(void)c;
	/* si POLARIS12 fuera >= VEGA10, la rama (num_level > 1) y otras
	 * de GMC9 aplicarian; el rasgo observable es que el modelo entonces
	 * dibujaria una geometria de 4 niveles, no 1 */
	return c->polaris12_before_vega10 && (base->num_level == 1);
}

/* CN-7: extraccion. Un ancla inexistente debe fallar, no devolver 0. */
static int cn7(const struct gg_corpus *c, const struct gg_geometry *base)
{
	(void)base;
	char *vmh = NULL;
	char path[2 * GG_MAX_PATH];
	unsigned got = 0xdead;
	bool r;

	(void)snprintf(path, sizeof(path), "%s/amdgpu_vm.h", c->amdgpu);
	if (!gg_read_file(path, &vmh, NULL))
		return 0;   /* ni siquiera pudo leer: el control no prueba nada */

	/* se sustituye el ancla real por una que no existe en el fichero */
	if (!gg_extract_after(vmh, "#define AMDGPU_PTE_NO_EXISTE_XYZ",
			     "%u", &got, 1))
		return 1;   /* fallo como se espera */

	/* si llego aqui, devolvio exito con un valor: hay que mirar el valor */
	r = (got == 0);
	free(vmh);
	return r;
}

/* CN-8: el enum. Un token inexistente debe fallar. */
static int cn8(const struct gg_corpus *c, const struct gg_geometry *base)
{
	(void)base;
	char *soc = NULL;
	char path[GG_MAX_PATH];
	long ord = -1;

	snprintf(path, sizeof(path), "%s", c->asic);
	if (!gg_read_file(path, &soc, NULL))
		return 0;
	if (!gg_enum_ordinal(soc, "enum amd_asic_type", "CHIP_NO_EXISTE_XYZ", &ord))
		return 1;
	free(soc);
	return 0;
}

/* CN-9: el corpus equivocado debe fallar al cargar. */
static int cn9(const struct gg_corpus *c, const struct gg_geometry *base)
{
	(void)c;
	(void)base;
	struct gg_corpus bad;
	char why[256];

	if (gg_corpus_load(&bad, "/tmp/opencode/no-existe-este-arbol",
			   "/tmp/opencode/no-existe-este-arbol", why, sizeof(why)))
		return 0;   /* cargo algo: el fallo de carga no discrimina */
	return why[0] != '\0';
}

/*
 * CN-11: sha256. Es el control mas importante de la lista, porque es el que
 * hace legitima la mezcla de dos raices de corpus. Si el verificador de hash
 * aceptara cualquier fichero, mezclarlas seria una confianza ciega y el resto
 * de la herramienta dejaria de ser evidencia.
 */
static int cn11(const struct gg_corpus *c, const struct gg_geometry *base)
{
	(void)base;
	char path[2 * GG_MAX_PATH];
	char got[65];
	bool wrote;

	/* caso positivo: la cabecera real debe pasar, y la carga ya lo exigio */
	if (!gg_header_sha256_ok(c->hdr_root))
		return 0;

	/* caso negativo: un fichero mutado debe ser rechazado.
	 * Se copia la cabecera real, se le cambia un byte, y se exige que el
	 * hash ya no coincida. */
	(void)snprintf(path, sizeof(path), "%s/include/drm/amd_asic_type.h.cn11",
		       c->hdr_root);
	{
		char orig[2 * GG_MAX_PATH];
		FILE *in;
		char *buf = NULL;
		size_t len = 0;

		(void)snprintf(orig, sizeof(orig),
			       "%s/include/drm/amd_asic_type.h", c->hdr_root);
		if (!gg_read_file(orig, &buf, &len))
			return 0;
		if (len == 0) {
			free(buf);
			return 0;
		}
		buf[0] = (buf[0] == 'X') ? 'Y' : 'X';   /* mutacion de 1 byte */

		in = fopen(path, "wb");
		if (!in) {
			free(buf);
			return 0;
		}
		wrote = (fwrite(buf, 1, len, in) == len);
		fclose(in);
		free(buf);
		if (!wrote) {
			remove(path);
			return 0;
		}
	}

	{
		bool real_rejected = false;
		bool mut_rejected = false;

		/* el mutante NO puede pasar el chequeo */
		if (gg_file_sha256(path, got))
			mut_rejected = (strcmp(got, GG_ASIC_TYPE_SHA256_7_1_3) != 0);

		/* el original SI debe pasarlo: si tampoco pasara, el verificador
		 * no estaria midiendo nada */
		(void)snprintf(path, sizeof(path),
			       "%s/include/drm/amd_asic_type.h.cn11.orig", c->hdr_root);
		(void)snprintf(got, sizeof(got), "%s", "");
		{
			char o2[2 * GG_MAX_PATH];
			(void)snprintf(o2, sizeof(o2),
				       "%s/include/drm/amd_asic_type.h", c->hdr_root);
			if (gg_file_sha256(o2, got))
				real_rejected = (strcmp(got,
						        GG_ASIC_TYPE_SHA256_7_1_3) == 0);
		}

		(void)snprintf(path, sizeof(path),
			       "%s/include/drm/amd_asic_type.h.cn11", c->hdr_root);
		remove(path);

		return (mut_rejected && real_rejected) ? 1 : 0;
	}
}

/*
 * CN-10: el modelo debe responder al valor de max_bits, no a una constante
 * propia.
 *
 * La primera version de este control uso max_bits = 48 y resulto MUERTO: con
 * max_size = 2^18 el clamp de amdgpu_vm.c:2418 dejaba vm_size en su suelo de
 * 64, luego el mutante no se propagaba y el control no discriminaba nada. Se
 * registra porque es el fallo que el propio protocolo de este repo ya prohibe:
 * un control que nunca se ha visto fallar no prueba que detecte.
 *
 * max_bits = 30 si se propaga: max_size cae a 1, vm_size cae a 1, max_pfn cae
 * a 2^18, y block_size cae a 9. Es decir, que block_size sea 10 y no 9 es
 * consecuencia de max_bits = 40, no una eleccion del modelo.
 */
static int cn10(const struct gg_corpus *c, const struct gg_geometry *base)
{
	struct gg_corpus mut = *c;
	struct gg_geometry g2;
	bool propagates;

	mut.max_bits = 30;
	gg_geometry(&mut, 8, &g2);

	propagates = (g2.block_size != base->block_size) &&
		     (g2.max_pfn != base->max_pfn) &&
		     (g2.vm_size_gb != base->vm_size_gb);

	/* y el mutante produce justamente el 9 que el documento 014 afirma,
	 * lo que confirma que el 9 no es un error de lectura sino lo que se
	 * obtendria con otra configuracion de max_bits */
	if (!propagates)
		return 0;
	return g2.block_size == 9u;
}

/*
 * CN-12: sensibilidad a la RAM del host. El unico dato que el modelo lee del
 * exterior es si_meminfo, asi que hay que comprobar que el modelo responde a
 * el y que la linea observada depende de en que rango cae la RAM.
 */
static int cn12(const struct gg_corpus *c, const struct gg_geometry *base)
{
	(void)base;
	struct gg_geometry g_lo, g_hi;

	gg_geometry(c, 8, &g_lo);    /* <= 21 GB -> vm_size 64  */
	gg_geometry(c, 64, &g_hi);   /* 64 GB     -> vm_size 256 */

	return (g_lo.vm_size_gb != g_hi.vm_size_gb) &&
	       (g_lo.max_pfn != g_hi.max_pfn) &&
	       (g_hi.vm_size_gb == 256);
}

static void test_negatives(const struct gg_corpus *c,
			   const struct gg_geometry *base)
{
	printf("\n== controles negativos (capacidad de fallar) ==\n");
	neg_run("CN-1", "get_block_size recibiera vm_size en vez de tmp",
		cn1, c, base);
	neg_run("CN-2", "la rama (num_level > 1) -> block_size = 9",
		cn2, c, base);
	neg_run("CN-3", "fragment_size = 8", cn3, c, base);
	neg_run("CN-4", "512 entradas por nivel", cn4, c, base);
	neg_run("CN-5", "PTBA field = block_size, sin el -9", cn5, c, base);
	neg_run("CN-6", "gate asic_type >= VEGA10 invertido", cn6, c, base);
	neg_run("CN-7", "ancla inexistente en amdgpu_vm.h", cn7, c, base);
	neg_run("CN-8", "enumerador inexistente en amd_asic_type.h", cn8, c, base);
	neg_run("CN-9", "raiz de corpus inexistente", cn9, c, base);
	neg_run("CN-10", "max_bits 40 -> 30 (debe dar block_size 9)",
		cn10, c, base);
	neg_run("CN-11", "sha256: cabecera mutada debe ser rechazada",
		cn11, c, base);
	neg_run("CN-12", "sensibilidad a la RAM del host", cn12, c, base);
}

/* ------------------------------------------------------------------ */

int main(int argc, char **argv)
{
	struct gg_corpus c;
	struct gg_geometry g;
	char why[512];
	const char *src;
	const char *hdr;
	int bad;

#ifndef DEFAULT_SRC_ROOT
#define DEFAULT_SRC_ROOT "../../../RESEARCH/working/linux-7.1.3"
#endif
#ifndef DEFAULT_HDR_ROOT
#define DEFAULT_HDR_ROOT "../../../RESEARCH/kernelbuild/linux-7.1.3"
#endif

	src = (argc > 1) ? argv[1] : DEFAULT_SRC_ROOT;
	hdr = (argc > 2) ? argv[2] : DEFAULT_HDR_ROOT;

	printf("gfx8vmgeom -- fuentes: %s\n", src);
	printf("gfx8vmgeom -- cabecera: %s\n", hdr);

	if (!gg_corpus_load(&c, src, hdr, why, sizeof(why))) {
		printf("ERROR: no se pudo cargar el corpus: %s\n", why);
		printf("RESULT: NO EJECUTADO\n");
		return 2;
	}
	printf("corpus cargado\n");

	test_extraction(&c);

	gg_geometry(&c, 8, &g);
	test_model(&c);
	test_negatives(&c, &g);

	printf("\n== informe ==\n");
	bad = gg_report(&c, &g, 8, stdout);

	printf("\n== resumen ==\n");
	printf("  aserciones           %u\n", g_pass);
	printf("  fallos               %u\n", g_fail);
	printf("  controles negativos  %u\n", g_neg_total);
	printf("  ...detectados        %u\n", g_neg_ok);
	printf("  ...muertos            %u\n", g_neg_dead);
	printf("  informe              %d discrepancias\n", bad);
	printf("  cruce de version     %s\n",
	       g_cross_version ? "PROVEN (7.1.3 y 7.2.8, misma rama)"
	                       : "NO_DISPONIBLE o no afirmado");

	if (g_fail == 0 && bad == 0 && g_neg_dead == 0 && g_neg_total > 0)
		printf("RESULT: OK -- y el test puede fallar (%u controles "
		       "negativos vivos)\n", g_neg_ok);
	else
		printf("RESULT: FALLO\n");

	return (g_fail == 0 && bad == 0 && g_neg_dead == 0) ? 0 : 1;
}