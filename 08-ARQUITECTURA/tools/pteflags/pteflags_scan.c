/*
 * pteflags -- censo de los productores de flags de PTE alcanzables en GFX8.
 *
 * QUE HACE
 * --------
 * Recorre el camino de escritura de una PTE en Polaris12 y determina, para
 * cada bit, QUIEN lo pone. La pregunta que responde es la de AGENTS.md:506:
 *
 *   "Localizar todos los producers de PTE flags para GFX8, resolver sus
 *    transformaciones hasta amdgpu_gmc_set_pte_pde, identificar cada bit
 *    escrito, y clasificar cada bit como PROVEN/NOT_DETERMINED."
 *
 * POR QUE NO BASTA CON LEER
 * -------------------------
 * Porque la ausencia de un flag en el camino GFX8 tiene dos explicaciones
 * muy distintas, y confundirlas es el error clasico de este tipo de trabajo:
 *
 *   (a) el flag no se escribe en GFX8 porque el hardware de GFX8 no lo tiene;
 *   (b) el flag no se escribe porque la funcion que lo pone es la de GFX9.
 *
 * Las dos se ven igual leyendo el fuente. Se distinguen con el
 * preprocesador: si el simbolo ni siquiera esta definido en la unidad de
 * traduccion, es (b), y el codigo ni siquiera podria compilar usandolo.
 *
 * METODO, Y POR QUE NO ES LO OBVIO
 * ---------------------------------
 * El preprocesador se ejecuta con los MISMOS -I que el build real registro
 * en el .cmd del arbol, mas los -DCC_USING_* que el Makefile del kernel
 * calcula. Sin eso el preprocesador falla con
 *
 *     #error Compiler does not support fentry?
 *
 * y produce una salida PARCIAL que parece correcta. Un "grep encontro 0"
 * sobre esa salida parcial no prueba una ausencia: es el fallo que
 * PRE-EXECUTION CONTRACT CHECK prohibe explicitamente, y que este repo ya
 * registro dos veces. Por eso rc se comprueba SIEMPRE y un rc != 0 aborta.
 */
#include "pteflags.h"

#include <stdlib.h>
#include <string.h>
#include <unistd.h>

/*
 * La construccion y ejecucion del preprocesador viven en pteflags_util.c, y
 * en un solo sitio a proposito. Estaban en dos ficheros con dos bucles de -I
 * distintos, y divergieron sin que nada lo notara: una se olvido de los
 * -include y ambas fallaban por motivos distintos. Ver pf_build_pp().
 */

/* ------------------------------------------------------------------ */
/* consultas sobre la TU preprocesada                                    */
/* ------------------------------------------------------------------ */

/*
 * Un simbolo esta DISPONIBLE en la TU si aparece como macro (#define) o como
 * identificador de enumeracion. Solo mirar macros daria un falso "no existe"
 * para todo lo que sea enum, que es justo el caso de MTYPE.
 */
/*
 * Un simbolo esta DISPONIBLE en la TU si aparece como macro (#define) o como
 * identificador de enumeracion. Mirar solo macros daria un falso NEGATIVO
 * para todo lo que sea enum, que es justo el caso de MTYPE.
 *
 * Y hay un segundo fallo que esta funcion cometio al principio: buscar el
 * simbolo como subcadena sin exigir limites de palabra hace que
 * "MTYPE_UC" aparezca dentro de "X86_MEMTYPE_UC", con lo que la consulta
 * decia SI para una TU donde el simbolo no existe. Un falso positivo aqui
 * es PEOR que un falso negativo: hace que una ausencia parezca una presencia
 * y el censo entero se apoya sobre el error.
 *
 * Se corrige exigiendo que el caracter anterior y el siguiente no formen
 * parte de un identificador.
 */
static bool word_boundary_before(const char *tu, const char *p)
{
	if (p == tu)
		return true;
	return !(isalnum((unsigned char)p[-1]) || p[-1] == '_');
}

static bool word_boundary_after(const char *p, size_t symlen)
{
	char after = p[symlen];
	return !(isalnum((unsigned char)after) || after == '_');
}

bool pf_symbol_in_tu(const char *tu, const char *sym)
{
	char pat[PF_MAX_NAME + 32];
	size_t sl;
	const char *p;

	if (!tu || !sym || !*sym)
		return false;
	sl = strlen(sym);
	if (sl + 12 >= sizeof(pat))
		return false;

	/* forma 1: macro con un espacio */
	snprintf(pat, sizeof(pat), "\n#define %s ", sym);
	if (strstr(tu, pat))
		return true;

	/* forma 2: macro con parentesis */
	snprintf(pat, sizeof(pat), "\n#define %s(", sym);
	if (strstr(tu, pat))
		return true;

	/* forma 3: identificador de enumeracion o variable, con limites de
	 * palabra a ambos lados. Se recorren todas las apariciones porque el
	 * patron anterior puede existir para otra cosa. */
	p = tu;
	while ((p = strstr(p, sym)) != NULL) {
		if (word_boundary_before(tu, p) && word_boundary_after(p, sl))
			return true;
		p += sl;
	}
	return false;
}

/* Cuenta apariciones de un token como palabra completa. */
unsigned pf_count_token(const char *text, const char *tok)
{
	unsigned n = 0;
	size_t tl = strlen(tok);
	const char *p = text;

	if (!text || !tok || !tl)
		return 0;

	while ((p = strstr(p, tok)) != NULL) {
		bool left_ok = (p == text) ||
			       (p[-1] != '_' && !isalnum((unsigned char)p[-1]));
		char after = p[tl];
		bool right_ok = (after == '\0') ||
				(after != '_' && !isalnum((unsigned char)after));
		if (left_ok && right_ok)
			n++;
		p += tl;
	}
	return n;
}

/* Devuelve 1 si la cabecera fue abierta en la TU. */
bool pf_header_included(const char *include_trace, const char *leaf)
{
	const char *p;
	size_t ll = strlen(leaf);

	if (!include_trace || !leaf)
		return false;
	p = include_trace;
	while ((p = strstr(p, leaf)) != NULL) {
		char before = (p == include_trace) ? '/' : p[-1];
		if (before == '/')
			return true;
		p += ll;
	}
	return false;
}