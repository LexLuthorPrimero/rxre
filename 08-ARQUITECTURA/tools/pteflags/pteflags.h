/*
 * pteflags -- censo de productores de flags de PTE en GFX8/Polaris12.
 *
 * Ver pteflags_scan.c para el metodo. Aqui vive el modelo: que productor
 * escribe que bit, y que significa que un bit no se escriba.
 */
#ifndef PTEFLAGS_H
#define PTEFLAGS_H

#include <ctype.h>
#include <stdbool.h>
#include <stddef.h>
#include <stdio.h>
#include <stdlib.h>
#include <string.h>

#define PF_MAX_PATH 1024
/* 73 -I del build real, cada uno con su ruta completa: el buffer de comando
 * tiene que ser comodo, no ajustado. Un "-I truncado" seria un fallo de
 * preprocesador con el diagnostico equivocado. */
#define PF_MAX_CMD 65536
/* Una TU preprocesada de gmc_v8_0.c ronda los 5 MB; el techo es
 * holgado para no fallar por sorpresa, y existe para que un comando
 * colgado no se coma la memoria del host. */
#define PF_MAX_CAPTURE ((size_t)256 * 1024 * 1024)
#define PF_MAX_NAME 96

/* ------------------------------------------------------------------ */
/* utilidades                                                           */
/* ------------------------------------------------------------------ */

/* Ruta absoluta de `path`, o NULL si no resuelve. Libreable. */
char *pf_abspath(const char *path);

/* Lee un fichero. NULL si no existe. */
char *pf_read(const char *path);

/* Escribe `script` en un temporal, lo ejecuta con cwd=root y captura stdout.
 * Devuelve el codigo de salida, o 90 si el script no se pudo ejecutar.
 * `out` recibe la salida (libreable). */
int pf_run_sh(const char *script, const char *root, char **out,
	      char *why, size_t why_len);

/* ------------------------------------------------------------------ */
/* preprocesador                                                         */
/* ------------------------------------------------------------------ */

/*
 * Preprocesa `src` dentro de `root` con los -I del build real.
 *
 * Devuelve true solo si rc == 0 y la salida no esta vacia. Cualquier otro
 * caso devuelve false con `why` explicado, y `*out` queda NULL.
 *
 * Esto es deliberado: una salida parcial con rc != 0 NO se inspecciona, ni
 * se pasa a grep, ni se reporta como ausencia de nada.
 */
bool pf_preprocess(const char *root, const char *src, char **out,
		   char *why, size_t why_len);

/* Preprocesa y ademas captura la traza de includes (-H). */
bool pf_preprocess_with_includes(const char *root, const char *src,
				 char **tu, char **includes, char *why,
				 size_t why_len);

/* ------------------------------------------------------------------ */
/* consultas sobre la TU                                                */
/* ------------------------------------------------------------------ */

/*
 * Un simbolo esta disponible en la TU si es macro O identificador de
 * enumeracion. Mirar solo macros daria falso negativo para los enums, que es
 * el caso de MTYPE.
 */
bool pf_symbol_in_tu(const char *tu, const char *sym);

/* Cuenta el token como palabra completa. */
unsigned pf_count_token(const char *text, const char *tok);

/* 1 si la cabecera con ese nombre de fichero fue abierta. */
bool pf_header_included(const char *include_trace, const char *leaf);

/* ------------------------------------------------------------------ */
/* el censo                                                              */
/* ------------------------------------------------------------------ */

/*
 * Como se establece que un bit no se escribe en GFX8. La distincion es el
 * resultado central de esta herramienta y no debe colapsarse.
 */
enum pf_absent_reason {
	PF_NOT_ABSENT = 0,

	/* el codigo GFX8 escribe el bit */
	PF_WRITTEN,

	/*
	 * NO se escribe, y la funcion que lo escribiria es la de otra
	 * generacion (gmc_v9_0_get_vm_pte). El simbolo MTYPE ni siquiera esta
	 * definido en la TU de gmc_v8_0.c.
	 */
	PF_OTHER_GEN,

	/*
	 * NO se escribe y el simbolo existe en la TU, pero ninguna rama
	 * alcanzable en GFX8 lo activa. Ejemplo: PRT se limpia
	 * explicitamente, luego no se escribe; pero el simbolo si existe.
	 */
	PF_DEAD_CODE_ON_GFX8,

	/*
	 * NO se escribe y el hardware de GFX8 no tiene el campo. La prueba es
	 * que el campo tampoco existe en los sh_mask de GFX8, no solo que el
	 * driver no lo escriba.
	 */
	PF_NO_HW_FIELD
};

struct pf_bit {
	const char *name;        /* AMDGPU_PTE_VALID ... */
	unsigned bit;            /* posicion, 0..63 */
	const char *producer;    /* quien lo escribe en el camino GFX8 */
	enum pf_absent_reason state;

	/*
	 * Evidencia de POR QUE. Para PF_NO_HW_FIELD: el sh_mask de GFX8 donde
	 * se buscaria el campo, y que no esta. Para PF_OTHER_GEN: la TU en la
	 * que se busco la ausencia.
	 */
	const char *evidence;
};

struct pf_census {
	struct pf_bit bits[24];
	unsigned n_bits;

	/* que simbolos existen en la TU de gmc_v8_0.c */
	bool has_mtype_in_gfx8_tu;
	bool has_mtype_in_gfx9_tu;
	bool gfx8_get_vm_pte_exists;
	bool gfx9_get_vm_pte_exists;

	/* el texto de gmc_v8_0_get_vm_pte, para citarlo */
	char vm_pte_body[1024];
};

/* Ejecuta el censo. Devuelve false con `why` si el corpus no permite afirmar. */
bool pf_census_run(const char *root, struct pf_census *c, char *why,
		   size_t why_len);

/* Imprime el censo. Devuelve el numero de lineas incoherentes. */
int pf_census_report(const struct pf_census *c, FILE *out);

#endif /* PTEFLAGS_H */