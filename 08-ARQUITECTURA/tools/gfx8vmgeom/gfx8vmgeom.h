/*
 * gfx8vmgeom -- modelo de la geometria GPUVM de GFX8/Polaris12, derivado del corpus.
 *
 * REGLA DE ESTA HERRAMIENTA
 * -------------------------
 * Ninguna constante del modelo esta escrita a mano en el codigo. Todas se
 * EXTRAEN del arbol de referencia con una busqueda anclada, y la extraccion
 * falla ruidosamente si el ancla no aparece. Asi una cita erronea del corpus
 * rompe la herramienta en vez de contaminarla en silencio.
 *
 * Solo existe una excepcion, marcada como tal y comprobada: PAGE_SIZE, que en
 * el kernel es una constante de compilacion del host, no un valor del ASIC.
 *
 * NO hace: no escribe registros, no lee MMIO, no ejecuta nada del driver.
 * Es un calculo sobre texto del corpus.
 */
#ifndef GFX8VMGEOM_H
#define GFX8VMGEOM_H

#include <stdbool.h>
#include <stdint.h>
#include <stdio.h>

#define GG_MAX_PATH 1024
#define GG_MAX_NAME 64

/* --- extraccion ------------------------------------------------------- */

/* Lee un fichero entero. Devuelve false si no existe o no se pudo abrir. */
bool gg_read_file(const char *path, char **out, size_t *out_len);

/*
 * Extrae `count` enteros sin signo que aparecen en `text` a partir del ancla
 * `anchor`, separados tal como los separa `fmt` (scanf-like, p.ej. "%u, %u, %u").
 * Devuelve true solo si la conversion completa tiene exito.
 */
bool gg_extract_after(const char *text, const char *anchor, const char *fmt,
		      unsigned *out, unsigned count);

/* Igual, pero para un unico entero en base 0 (acepta 0x...). */
bool gg_extract_u64_after(const char *text, const char *anchor, uint64_t *out);

/*
 * Extrae el numero de enumeracion de un enumerador dentro de un `enum {`.
 * Devuelve false si el token no esta, o si no esta dentro del rango pedido.
 */
bool gg_enum_ordinal(const char *text, const char *enum_anchor, const char *token,
		     long *out);

/* Extrae el numero que sigue a un "<<" dentro de la definicion de un macro. */
bool gg_macro_shift(const char *text, const char *macro, unsigned *out);

/* Extrae la mascara (p.ej. 0x1fULL) del segundo argumento de un macro. */
bool gg_macro_mask(const char *text, const char *macro, uint64_t *out);

/* --- corpus ----------------------------------------------------------- */

struct gg_corpus {
	char src_root[GG_MAX_PATH]; /* p.ej. RESEARCH/working/linux-7.1.3 */
	char hdr_root[GG_MAX_PATH]; /* p.ej. RESEARCH/kernelbuild/linux-7.1.3 */
	char amdgpu[GG_MAX_PATH];   /* <src_root>/drivers/gpu/drm/amd/amdgpu */
	char asic[GG_MAX_PATH];     /* <hdr_root>/include/drm/amd_asic_type.h */

	/* valores extraidos, con su procedencia para el informe */
	unsigned min_vm_size_gb;
	unsigned fragment_size_default;
	unsigned max_level;
	unsigned max_bits;
	uint64_t pte_addr_mask;
	unsigned pa_bits;

	unsigned bit_valid, bit_system, bit_snooped, bit_tmz;
	unsigned bit_executable, bit_readable, bit_writeable;
	unsigned bit_pde_pte, bit_prt, bit_log, bit_tf, bit_noalloc, bit_bfs;
	unsigned frag_shift, frag_width;

	unsigned gfx_major, gfx_minor, gfx_rev;

	long ord_polaris12, ord_vega10, ord_vega12;
	bool polaris12_before_vega10;   /* gate de many asic_type >= CHIP_VEGA10 */
	bool gfx_before_gfx12;          /* gate de AMDGPU_PDE_PTE_FLAG */
};

/*
 * Carga el corpus desde DOS raices, porque el corpus de este repo esta partido:
 *
 *   src_root -> drivers/gpu/drm/amd/amdgpu   (working/baseline: 7.1.3 pristino)
 *   hdr_root -> include/drm/amd_asic_type.h   (solo existe en kernelbuild)
 *
 * Mezclarlos a ciegas seria un fallo: kernelbuild esta instrumentado
 * (RE-02-E1). Se separan por proposito, y `gg_header_sha256_ok()` verifica
 * que el fichero de la cabecera es realmente el del tarball, que es lo que
 * hace legitima la mezcla.
 *
 * `hdr_root` puede ser igual a `src_root` en un arbol completo.
 * Devuelve false con `why` explica si algo no se encontro.
 */
bool gg_corpus_load(struct gg_corpus *c, const char *src_root,
		    const char *hdr_root, char *why, size_t why_len);

/*
 * sha256 del amd_asic_type.h que el tarball 7.1.3 declara.
 * Se compara contra el fichero real para que la cabecera que se usa sea
 * demostrablemente la de 7.1.3 y no una modificada.
 */
extern const char *const GG_ASIC_TYPE_SHA256_7_1_3;

/* Compara el sha256 de <hdr_root>/include/drm/amd_asic_type.h. */
bool gg_header_sha256_ok(const char *hdr_root);

/* sha256 de un fichero, escrito como 64 hex + NUL en `out`. */
bool gg_file_sha256(const char *path, char out[65]);

/*
 * Verificacion cruzada de version.
 *
 * La rama que decide block_size (num_level > 1 -> 9, si no get_block_size(tmp))
 * es la causa de todo el hallazgo. Si esa rama cambiara en otra version, el
 * hallazgo seria un artefacto de 7.1.3 y no una propiedad de Polaris12.
 * Esta funcion lee el arbol indicado y afirma la forma de la rama; el test
 * la ejecuta contra 7.2.8.
 */
enum gg_branch_shape {
	GG_BRANCH_UNKNOWN = 0,   /* no se localizó o la forma no se reconoce */
	GG_BRANCH_NUMLEVEL_GT1, /* if (num_level > 1) block_size = 9; else ... */
	GG_BRANCH_OTHER
};

enum gg_branch_shape gg_check_block_size_branch(const char *src_root);

/* --- modelo ----------------------------------------------------------- */

struct gg_geometry {
	unsigned vm_size_gb;
	uint64_t max_pfn;
	unsigned max_level_unused;   /* reservado: no lo consulta nadie todavia */
	unsigned num_level;          /* niveles de directorio */
	unsigned root_level;         /* PDB3=0 .. PTB=4 */
	unsigned block_size;
	unsigned fragment_size;
	unsigned ptba_depth_field;   /* PAGE_TABLE_DEPTH, el que se escribe para VMID 1..15 */
	unsigned ptba_block_field;   /* PAGE_TABLE_BLOCK_SIZE = block_size - 9 */

	unsigned pdb0_entries, pdb0_bytes;
	unsigned ptb_entries, ptb_bytes;
	unsigned ptb_pages, ptb_kib;
	uint64_t n_ptb;
	uint64_t leaf_table_bytes;     /* suma de todos los PTB */

	unsigned va_bits_pdb0_index;  /* bits que indexan una entrada del root */
	unsigned va_bits_ptb_index;
	unsigned va_bits_offset;
	unsigned va_bits_total;
};

/*
 * Reproduce amdgpu_vm_adjust_size() + amdgpu_vm_pt_num_entries() +
 * amdgpu_vm_pt_level_shift() tal como estan escritos en el corpus.
 *
 * `phys_ram_gb` es la unica entrada que el codigo real lee del host
 * (si_meminfo). Se pasa como parametro para que el modelo sea una funcion
 * pura y comprobable, no una lectura de estado.
 */
void gg_geometry(const struct gg_corpus *c, unsigned phys_ram_gb,
		 struct gg_geometry *g);

/* --- informe ---------------------------------------------------------- */

/* Devuelve la linea que el host observo, tal como quedo registrada. */
extern const char *const GG_HOST_OBSERVED_VM_LINE;

/* Imprime el informe completo. Devuelve el numero de discrepancias. */
int gg_report(const struct gg_corpus *c, const struct gg_geometry *g,
	      unsigned phys_ram_gb, FILE *out);

#endif /* GFX8VMGEOM_H */