/* SPDX-License-Identifier: GPL-2.0 */
/*
 * kdeps.c - cierre transitivo de #include locales sobre fuente de kernel.
 *
 * USO:
 *   kdeps [-I dir]... <semilla.c>...
 *
 * PROPOSITO
 *   Resolver que cabeceras alcanza de verdad un fichero .c, transitivamente.
 *   Motivo: contar includes DIRECTOS mide cero y no significa nada
 *   (AGENTS.md 4.2 - una coincidencia es una coordenada, no un significado).
 *
 * RESOLUCION (en este orden, por fichero que incluye):
 *   1. relativo al directorio del fichero que incluye
 *   2. relativo a cada raiz -I, en el orden dado
 *   - Los <...> se cuentan pero NO se siguen: son cabeceras de sistema, no del
 *     arbol que estamos analizando. Contarlos evita el falso "no depende de X".
 *
 * SALIDA
 *   stdout: una ruta de cabecera resuelta por linea, relativa al CWD, unica y
 *           ordenada. Es la UNICA FUENTE DE VERDAD de la herramienta.
 *   stderr: resumen (semillas, filas, profundidad, includes de sistema).
 *
 * SALIDAS
 *   0  ok
 *   1  una semilla no existe o no se pudo leer -> se informa, no se oculta
 *   2  uso incorrecto
 *
 * LIMITACIONES DECLARADAS (no son defectos ocultos, son limites del metodo)
 *   - No parsea la precondicion de #if: una cabecera puede estar en el cierre
 *     y no compilarse para una configuracion dada. El cierre es
 *     SOBRE-estimacion, nunca subestimacion.
 *   - No resuelve macros, ni generacion de cabeceras, ni #include <>
 *     reenviados a un .h local.
 *   - No distingue "alcanzada" de "usada": este tool responde "que se puede
 *     alcanzar", no "que se usa". Usado requiere analisis de simbolos aparte.
 */

#include <stdio.h>
#include <stdlib.h>
#include <stdint.h>
#include <string.h>
#include <errno.h>
#include <sys/stat.h>

#define PATHMAX 1024
#define MAXINC  64

/* ---------- conjunto de rutas, tabla hash abierta ---------- */

struct set {
	char **slot;
	size_t cap;   /* potencia de dos */
	size_t len;
};

static unsigned long fnv1a(const char *s)
{
	unsigned long h = 1469598103934665603UL;
	while (*s) {
		h ^= (unsigned char)*s++;
		h *= 1099511628211UL;
	}
	return h;
}

static int set_grow(struct set *s)
{
	size_t ncap = s->cap ? s->cap * 2 : 1024;
	char **ns = calloc(ncap, sizeof(char *));
	size_t i;

	if (!ns)
		return -1;
	for (i = 0; i < s->cap; i++) {
		if (s->slot[i]) {
			size_t j = fnv1a(s->slot[i]) & (ncap - 1);
			while (ns[j])
				j = (j + 1) & (ncap - 1);
			ns[j] = s->slot[i];
		}
	}
	free(s->slot);
	s->slot = ns;
	s->cap = ncap;
	return 0;
}

/* 0 = insertada ahora, 1 = ya estaba, -1 = error de memoria */
static int set_add(struct set *s, const char *path)
{
	size_t i;

	if (s->len * 2 >= s->cap && set_grow(s) < 0)
		return -1;
	i = fnv1a(path) & (s->cap - 1);
	while (s->slot[i]) {
		if (strcmp(s->slot[i], path) == 0)
			return 1;
		i = (i + 1) & (s->cap - 1);
	}
	s->slot[i] = strdup(path);
	if (!s->slot[i])
		return -1;
	s->len++;
	return 0;
}

static int set_has(struct set *s, const char *path)
{
	size_t i;

	if (!s->cap)
		return 0;
	i = fnv1a(path) & (s->cap - 1);
	while (s->slot[i]) {
		if (strcmp(s->slot[i], path) == 0)
			return 1;
		i = (i + 1) & (s->cap - 1);
	}
	return 0;
}

static int cmpstr(const void *a, const void *b)
{
	return strcmp(*(char *const *)a, *(char *const *)b);
}

/* ---------- resolucion ---------- */

static char incdirs[MAXINC][PATHMAX];
static int  nincdirs;
static struct set seen;      /* cabeceras ya vistas */
static struct set queue;     /* pendientes por procesar */
static int sysincludes;      /* cuenta de <...> */
static int missing;          /* includes no resueltos */

/* registro de includes no resueltos, para diagnostico (stderr) */
#define MAXMISS 4096
static char miss_target[MAXMISS][PATHMAX];
static char miss_from[MAXMISS][PATHMAX];
static int  nmiss;

static int readable(const char *p)
{
	struct stat st;

	return stat(p, &st) == 0 && S_ISREG(st.st_mode);
}

/* Devuelve 1 si 'target' resuelve a 'out' siguiendo las reglas documentadas. */
static int resolve(const char *fromfile, const char *target, char *out)
{
	char dir[PATHMAX];
	char cand[PATHMAX];
	const char *slash;
	int i;

	/* 1. relativo al directorio del includer */
	slash = strrchr(fromfile, '/');
	if (slash) {
		size_t n = (size_t)(slash - fromfile);

		if (n >= sizeof(dir))
			return 0;
		memcpy(dir, fromfile, n);
		dir[n] = '\0';
	} else {
		dir[0] = '.';
		dir[1] = '\0';
	}
	if ((size_t)snprintf(cand, sizeof(cand), "%s/%s", dir, target) < sizeof(cand)
	    && readable(cand)) {
		snprintf(out, PATHMAX, "%s", cand);
		return 1;
	}

	/* 2. raices -I, en orden */
	for (i = 0; i < nincdirs; i++) {
		if ((size_t)snprintf(cand, sizeof(cand), "%s/%s", incdirs[i], target)
		    < sizeof(cand) && readable(cand)) {
			snprintf(out, PATHMAX, "%s", cand);
			return 1;
		}
	}
	return 0;
}

/* Lee un fichero y encola sus #include "locales".
 *
 * Estado de comentario de bloque sostenido entre lineas: un #include dentro de
 * un comentario NO es un include. Sin esto, kdeps reportaba como pendiente un
 * include comentado cuyo fichero no existe en ninguna parte del arbol, lo que
 * hacia parecer el universo de inputs incompleto cuando no lo estaba.
 */
static int in_block_comment;

static void scan(const char *path)
{
	FILE *f = fopen(path, "r");
	char line[PATHMAX * 2];

	if (!f) {
		fprintf(stderr, "kdeps: no se pudo leer %s: %s\n", path,
			strerror(errno));
		return;
	}
	while (fgets(line, sizeof(line), f)) {
		char target[PATHMAX];
		char resolved[PATHMAX];
		const char *p = line;
		int quoted;
		char *scan = line;

		/* seguir el estado de comentario de bloque dentro de la linea */
		while (*scan) {
			if (in_block_comment) {
				char *e = strstr(scan, "*/");

				if (!e)
					break;
				in_block_comment = 0;
				scan = e + 2;
			} else {
				char *o = strstr(scan, "/*");

				if (!o)
					break;
				in_block_comment = 1;
				scan = o + 2;
			}
		}
		if (in_block_comment)
			continue;

		while (*p == ' ' || *p == '\t')
			p++;
		if (strncmp(p, "#include", 8) != 0)
			continue;
		p += 8;
		while (*p == ' ' || *p == '\t')
			p++;
		if (*p == '<') {
			sysincludes++;
			continue;
		}
		if (*p != '"')
			continue;
		p++;
		quoted = 0;
		{
			size_t n = 0;

			while (*p && n < sizeof(target) - 1) {
				if (*p == '"') {
					quoted = 1;
					break;
				}
				target[n++] = *p++;
			}
			target[n] = '\0';
		}
		if (!quoted || target[0] == '\0')
			continue;
		if (resolve(path, target, resolved)) {
			if (set_add(&seen, resolved) == 0)
				set_add(&queue, resolved);
		} else {
			missing++;
			if (nmiss < MAXMISS) {
				snprintf(miss_target[nmiss], PATHMAX, "%s", target);
				snprintf(miss_from[nmiss], PATHMAX, "%s", path);
				nmiss++;
			}
		}
	}
	fclose(f);
}

int main(int argc, char **argv)
{
	int i, first = 1, rc = 0;
	size_t k;
	char **list;
	size_t n = 0;

	while (first < argc && argv[first][0] == '-' && argv[first][1] == 'I') {
		const char *v = argv[first][2] ? argv[first] + 2 : NULL;

		if (!v && first + 1 < argc)
			v = argv[++first];
		if (!v || nincdirs >= MAXINC) {
			fprintf(stderr, "kdeps: -I invalido o demasiados\n");
			return 2;
		}
		snprintf(incdirs[nincdirs], PATHMAX, "%s", v);
		nincdirs++;
		first++;
	}
	if (first >= argc) {
		fprintf(stderr, "uso: %s [-I dir]... <semilla.c>...\n", argv[0]);
		return 2;
	}

	/* control negativo: una semilla inexistente debe fallar, no callar */
	for (i = first; i < argc; i++) {
		if (!readable(argv[i])) {
			fprintf(stderr, "kdeps: semilla no existe o no es regular: %s\n",
				argv[i]);
			rc = 1;
		} else {
			set_add(&seen, argv[i]);
			set_add(&queue, argv[i]);
		}
	}

	while (queue.len) {
		char cur[PATHMAX];
		size_t j, best = SIZE_MAX;
		const char *bp = NULL;

		/* extraer una Any (orden de recorrido estable: no afecta al conjunto) */
		for (j = 0; j < queue.cap; j++) {
			if (queue.slot[j] && strcmp(queue.slot[j], "") != 0) {
				best = j;
				bp = queue.slot[j];
				break;
			}
		}
		if (!bp)
			break;
		snprintf(cur, sizeof(cur), "%s", bp);
		free(queue.slot[best]);
		queue.slot[best] = NULL;
		queue.len--;
		scan(cur);
	}

	list = calloc(seen.len ? seen.len : 1, sizeof(char *));
	if (!list)
		return 1;
	for (i = 0; (size_t)i < seen.cap; i++)
		if (seen.slot[i] && set_has(&seen, seen.slot[i]))
			list[n++] = seen.slot[i];
	qsort(list, n, sizeof(char *), cmpstr);
	for (k = 0; k < n; k++)
		puts(list[k]);

	fprintf(stderr,
		"kdeps: semillas=%d cabeceras_unicas=%zu includes_sistema=%d no_resueltos=%d\n",
		argc - first, n, sysincludes, missing);
	if (nmiss) {
		int u;

		fprintf(stderr, "kdeps: DETALLE de includes no resueltos:\n");
		for (u = 0; u < nmiss; u++)
			fprintf(stderr, "  \"%s\"  <-  %s\n", miss_target[u],
				miss_from[u]);
	}
	return rc;
}
