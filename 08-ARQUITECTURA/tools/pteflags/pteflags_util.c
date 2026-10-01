/*
 * pteflags -- utilidades de fichero y ejecucion.
 */
#include "pteflags.h"

#include <errno.h>
#include <sys/wait.h>
#include <limits.h>
#include <unistd.h>

/*
 * El root se absolutiza ANTES de construir nada. Sin esto, un root relativo
 * combinado con el cwd del proceso produce rutas como
 * "./../../../RESEARCH/..." que no resuelven, y el fallo aparece como un
 * error del preprocesador sobre kconfig.h, que no dice nada del root.
 */
char *pf_abspath(const char *path)
{
	char buf[PF_MAX_CMD];

	if (!path)
		return NULL;
	if (realpath(path, buf) == NULL)
		return NULL;
	return strdup(buf);
}

char *pf_read(const char *path)
{
	FILE *f;
	long sz;
	char *buf;
	size_t got;

	if (!path)
		return NULL;
	f = fopen(path, "rb");
	if (!f)
		return NULL;
	if (fseek(f, 0, SEEK_END) != 0) {
		fclose(f);
		return NULL;
	}
	sz = ftell(f);
	if (sz < 0) {
		fclose(f);
		return NULL;
	}
	rewind(f);
	buf = malloc((size_t)sz + 1);
	if (!buf) {
		fclose(f);
		return NULL;
	}
	got = fread(buf, 1, (size_t)sz, f);
	fclose(f);
	buf[got] = '\0';
	return buf;
}

int pf_run_sh(const char *script, const char *root, char **out, char *why,
	      size_t why_len)
{
	char path[] = "/tmp/opencode/pf-XXXXXX";
	int fd, pipefd[2];
	pid_t pid;
	int status = 0;
	FILE *rf;
	size_t cap = 1 << 16, len = 0;
	char *buf;

	/*
	 * Traza del comando exacto que se va a ejecutar. Sin esto, un rc != 0
	 * aqui es un "no se pudo ejecutar" sin informacion: se probo durante
	 * esta sesion y fue exactamente lo que hizo falta para poder
	 * diagnosticar cuatro fallos distintos del preprocesador.
	 */
	{
		FILE *tr = fopen("/tmp/opencode/pf_cmd.sh", "w");
		if (tr) {
			fputs(script, tr);
			fclose(tr);
		}
	}

	*out = NULL;

	if (!script || !root) {
		snprintf(why, why_len, "argumento nulo");
		return 90;
	}

	/* Directorio de trabajo: si no existe, no se invoca nada. Un mkdir -p
	 * callido aqui daria un fallo de permisos con un diagnostico que
	 * parece un problema del corpus. */
	if (access(root, R_OK | X_OK) != 0) {
		snprintf(why, why_len, "raiz inaccesible: %s", root);
		return 91;
	}

	fd = mkstemp(path);
	if (fd < 0) {
		snprintf(why, why_len, "no se pudo crear el temporal: %s",
			 strerror(errno));
		return 92;
	}
	{
		ssize_t w = write(fd, script, strlen(script));
		if (w < 0 || (size_t)w != strlen(script)) {
			close(fd);
			unlink(path);
			snprintf(why, why_len, "escritura parcial del script");
			return 93;
		}
	}
	close(fd);

	if (pipe(pipefd) != 0) {
		unlink(path);
		snprintf(why, why_len, "pipe: %s", strerror(errno));
		return 94;
	}

	pid = fork();
	if (pid < 0) {
		close(pipefd[0]);
		close(pipefd[1]);
		unlink(path);
		snprintf(why, why_len, "fork: %s", strerror(errno));
		return 95;
	}

	if (pid == 0) {
		close(pipefd[0]);
		dup2(pipefd[1], STDOUT_FILENO);
		dup2(pipefd[1], STDERR_FILENO);
		close(pipefd[1]);
		if (chdir(root) != 0)
			_exit(97);
		execl("/bin/sh", "sh", path, (char *)NULL);
		_exit(98);
	}

	close(pipefd[1]);
	buf = malloc(cap);
	if (!buf) {
		close(pipefd[0]);
		waitpid(pid, &status, 0);
		unlink(path);
		snprintf(why, why_len, "sin memoria para la salida");
		return 96;
	}

	rf = fdopen(pipefd[0], "r");
	if (!rf) {
		free(buf);
		close(pipefd[0]);
		waitpid(pid, &status, 0);
		unlink(path);
		snprintf(why, why_len, "fdopen: %s", strerror(errno));
		return 99;
	}

	/*
	 * Bucle de lectura.
	 *
	 * BUG que se corrigio aqui, y que se registro porque es facil de
	 * repetir: la condicion "espacio libre > 0" mas "fread devuelve 0"
	 * parece el final del stream, pero NO lo es. Con el buffer lleno,
	 * fread(0 bytes disponibles) devuelve 0 y el bucle sale cortando la
	 * salida. El hijo sigue escribiendo, recibe SIGPIPE, y el estado
	 * sale con codigo 1: un fallo que no tiene nada que ver con la causa.
	 *
	 * Se distingue el final real con ferror(), y se crece el buffer con
	 * realloc. El sintoma era: la salida se truncaba a 65535 bytes y el
	 * preprocesador "fallaba" sin error visible.
	 */
	for (;;) {
		size_t room, got;

		if (len + 1 >= cap) {
			char *nb;
			if (cap >= PF_MAX_CAPTURE) {   /* cota dura */
				free(buf);
				fclose(rf);
				close(pipefd[0]);
				waitpid(pid, &status, 0);
				unlink(path);
				snprintf(why, why_len,
					 "salida descomun (%u bytes): el comando no "
					 "termina o genera demasiado",
					 (unsigned)cap);
				return 89;
			}
			cap *= 2;
			nb = realloc(buf, cap);
			if (!nb) {
				free(buf);
				fclose(rf);
				close(pipefd[0]);
				waitpid(pid, &status, 0);
				unlink(path);
				snprintf(why, why_len, "realloc");
				return 96;
			}
			buf = nb;
		}

		room = cap - len - 1;
		got = fread(buf + len, 1, room, rf);
		len += got;

		if (got < room)
			break;          /* lectura corta = fin del stream */
		/* got == room: el buffer se lleno entero, hay que crecer */
	}

	if (ferror(rf)) {
		free(buf);
		fclose(rf);
		close(pipefd[0]);
		waitpid(pid, &status, 0);
		unlink(path);
		snprintf(why, why_len, "error de lectura: %s", strerror(errno));
		return 90;
	}

	buf[len] = '\0';

	fclose(rf);
	/*
	 * status se inicializa a -1 y se COMPRUEBA el retorno de waitpid.
	 * Sin eso, un waitpid fallido deja status con el valor anterior y
	 * WIFEXITED/WIFSIGNALED dan basura: el codigo de salida reported no
	 * tiene nada que ver con el del proceso.
	 */
	status = -1;
	if (waitpid(pid, &status, 0) < 0) {
		free(buf);
		unlink(path);
		snprintf(why, why_len, "waitpid fallo: %s", strerror(errno));
		return 90;
	}
	unlink(path);

	if (WIFEXITED(status))
		*out = buf;
	else {
		free(buf);
		*out = NULL;
	}

	if (WIFEXITED(status))
		return WEXITSTATUS(status);
	if (WIFSIGNALED(status)) {
		snprintf(why, why_len, "el proceso murio por senal %d",
			 WTERMSIG(status));
		return 128 + WTERMSIG(status);
	}
	return 90;
}


/*
 * Se construye UNA sola vez el comando del preprocesador, con la opcion de
 * traza de includes. Antes havia dos funciones con dos bucles de -I
 * distintos, y divergieron: una se olvido de los -include, y las dos
 * fallaban por motivos distintos sin que se notara. Una sola construccion
 * hace imposible esa clase de divergencia.
 *
 * Devuelve true solo si el comando es coherente. NO invoca nada.
 */
static bool pf_build_pp(const char *root, const char *src, bool trace,
			char *cmd, size_t cmd_len, char *why, size_t why_len)
{
	char cmdfile[2 * PF_MAX_PATH];
	char autoconf[2 * PF_MAX_PATH];
	char *incs, *tok, *save;
	size_t n;
	bool pending_i = false;

	snprintf(cmdfile, sizeof(cmdfile),
		 "%s/drivers/gpu/drm/amd/amdgpu/.amdgpu_vm_pt.o.cmd", root);
	incs = pf_read(cmdfile);
	if (!incs) {
		snprintf(why, why_len, "no se pudo leer el .cmd del build: %s",
			 cmdfile);
		return false;
	}

	/*
	 * El .cmd de amdgpu NO lleva -I./include/generated, y sin el
	 * include/linux/kconfig.h aborta con
	 *     fatal error: generated/autoconf.h: No existe
	 * porque Makefile:589 anade -I$(objtree)/include y el .cmd lo hereda
	 * de ahi. Se anade con su fundamento, y se COMPRUEBA que el fichero
	 * exista: anadirla a ciegas seria mover el fallo de sitio en lugar de
	 * resolverlo.
	 */
	snprintf(autoconf, sizeof(autoconf), "%s/include/generated/autoconf.h",
		 root);
	if (access(autoconf, R_OK) != 0) {
		free(incs);
		snprintf(why, why_len, "falta %s", autoconf);
		return false;
	}

	/*
	 * -E y NO -dM.
	 *
	 * -dM solo emite MACROS. Los identificadores de enumeracion, que es
	 * donde vive MTYPE, no aparecen nunca, y una consulta que solo mira
	 * macros daria un falso NEGATIVO: "MTYPE no existe" cuando en
	 * realidad existe como enum. Ese falso negativo habria producido la
	 * conclusion opuesta a la correcta, y con apariencia de rigor.
	 *
	 * -E emite la unidad de traduccion entera, enums incluidos, y es lo
	 * que hace falta para preguntar por un simbolo.
	 */
	n = (size_t)snprintf(cmd, cmd_len, "#!/bin/sh\nexec gcc -E%s \\\n",
			     trace ? " -H" : "");
	if (n >= cmd_len) {
		free(incs);
		snprintf(why, why_len, "comando desbordado");
		return false;
	}

	/*
	 * El .cmd escribe "-I./ruta" SIN espacio. Se aceptan las dos formas
	 * porque un "-I ./ruta" daria "-I" suelto y "tok + 2" se comeria el
	 * primer caracter de la ruta.
	 */
	for (tok = strtok_r(incs, " \t\n", &save); tok;
	     tok = strtok_r(NULL, " \t\n", &save)) {
		const char *path = NULL;

		if (pending_i) {
			path = tok;
			pending_i = false;
		} else if (strcmp(tok, "-I") == 0) {
			pending_i = true;
			continue;
		} else if (strncmp(tok, "-I", 2) == 0) {
			path = tok + 2;
		} else {
			continue;
		}
		if (!path || !*path)
			continue;
		if (n + strlen(path) + 8 >= cmd_len) {
			free(incs);
			snprintf(why, why_len, "comando desbordado en -I");
			return false;
		}
		/*
		 * El -I es OBLIGATORIO. Emitir solo la ruta entrecomillada
		 * produce un gcc que acepta los argumentos como ficheros
		 * fuente en vez de como rutas de busqueda, y el fallo aparece
		 * mucho despues como "linux/firmware.h no existe". Se perdio
		 * una hora de diagnostico por esto; queda comentado para que
		 * no se repita.
		 */
		n += (size_t)snprintf(cmd + n, cmd_len - n, "  -I '%s' \\\n",
				      path);
	}
	if (pending_i) {
		free(incs);
		snprintf(why, why_len, "el .cmd acaba en un -I sin ruta");
		return false;
	}

	n += (size_t)snprintf(cmd + n, cmd_len - n,
		"  -I '%s/include/generated' \\\n"
		"  -include '%s/include/linux/compiler-version.h' \\\n"
		"  -include '%s/include/linux/kconfig.h' \\\n"
		"  -include '%s/include/linux/compiler_types.h' \\\n"
		"  -mfentry -pg -DCC_USING_FENTRY -DCC_USING_NOP_MCOUNT \\\n"
		"  -D__KERNEL__ \\\n  '%s'%s\n",
		root, root, root, root, src, trace ? " 2>&1" : "");
	free(incs);

	if (n >= cmd_len) {
		snprintf(why, why_len, "comando desbordado al final");
		return false;
	}
	return true;
}

/*
 * Diagnostico del fallo. pf_run_sh mezcla stdout y stderr, asi que se corta por
 * la primera "#define": lo que hay antes es el error del compilador.
 *
 * El texto se COPIA antes de usarse: "src" puede apuntar a "why", y snprintf
 * con destino y origen solapados es indefinido. El compilador lo avisa con
 * -Wrestrict, y aqui se le hace caso.
 */
static void pp_diagnose(char *out, char *why, size_t why_len, int rc,
			const char *tag)
{
	/* el error del compilador va por stderr y se mezcla con la TU; se
	 * toman los primeros 300 caracteres, que es donde esta el mensaje */
	const char *src = out ? out : "(sin stderr)";
	char diag[320];
	size_t dlen = strlen(src);

	if (dlen > sizeof(diag) - 1)
		dlen = sizeof(diag) - 1;
	memcpy(diag, src, dlen);
	diag[dlen] = '\0';
	snprintf(why, why_len, "preprocesador%s rc=%d. Diagnostico: %s", tag,
		 rc, diag);
}

/* Separa la TU (desde la primera #define) de la traza de includes. */
static bool pp_split(char *all, char **tu, char **includes, char *why,
		     size_t why_len)
{
	size_t tlen;

	/*
	 * Con -E la salida empieza por comentarios de licencia, no por
	 * "#define". Se separa la traza de includes (lineas que empiezan por
	 * un punto y puntos suspensivos) del resto, que es la TU.
	 */
	if (!all || !*all) {
		snprintf(why, why_len, "el preprocesador no produjo salida");
		return false;
	}
	/*
	 * La traza de -H empieza con UN punto y sigue con espacios:
	 *
	 *     . ./include/linux/firmware.h
	 *     .. ./include/linux/types.h
	 *
	 * Un test que exija ".." como prefijo no encuentra la linea y se
	 * queda con tlen = 0, con lo que la TU entera se toma por traza.
	 * Se admite CUALQUIER cantidad de puntos iniciales, que es lo que el
	 * formato significa: profundidad de anidamiento.
	 */
	tlen = 0;
	{
		const char *p = all;
		while (*p) {
			const char *eol = strchr(p, '\n');
			size_t linelen = eol ? (size_t)(eol - p) : strlen(p);
			const char *q = p;
			size_t dots = 0;

			while (q < p + linelen && *q == '.') {
				dots++;
				q++;
			}
			if (dots == 0) {
				tlen = (size_t)(p - all);
				break;
			}
			if (!eol)
				break;
			p = eol + 1;
		}
	}

	*tu = strdup(all + tlen);
	if (!*tu) {
		snprintf(why, why_len, "sin memoria");
		return false;
	}
	if (includes) {
		char *trace = malloc(tlen + 1);
		if (!trace) {
			free(*tu);
			*tu = NULL;
			snprintf(why, why_len, "sin memoria");
			return false;
		}
		memcpy(trace, all, tlen);
		trace[tlen] = '\0';
		*includes = trace;
	}
	return true;
}

bool pf_preprocess(const char *root, const char *src, char **out, char *why,
		   size_t why_len)
{
	char *abs = NULL, *all = NULL;
	char cmd[PF_MAX_CMD];
	int rc;
	bool r;

	*out = NULL;
	if (!root || !src || !out || !why) {
		snprintf(why, why_len, "argumento nulo");
		return false;
	}
	why[0] = '\0';

	abs = pf_abspath(root);
	if (!abs) {
		snprintf(why, why_len, "la raiz no resuelve: %s", root);
		return false;
	}
	if (!pf_build_pp(abs, src, false, cmd, sizeof(cmd), why, why_len)) {
		free(abs);
		return false;
	}

	rc = pf_run_sh(cmd, abs, &all, why, why_len);
	free(abs);

	if (rc != 0) {
		pp_diagnose(all, why, why_len, rc, "");
		free(all);
		return false;
	}

	r = pp_split(all, out, NULL, why, why_len);
	if (!r && why[0] == '\0')
		snprintf(why, why_len, "pp_split fallo sin diagnóstico");
	free(all);
	if (!r)
		return false;
	if (**out == '\0') {
		free(*out);
		*out = NULL;
		snprintf(why, why_len, "TU vacia");
		return false;
	}
	return true;
}

bool pf_preprocess_with_includes(const char *root, const char *src, char **tu,
				 char **includes, char *why, size_t why_len)
{
	char *abs = NULL, *all = NULL;
	char cmd[PF_MAX_CMD];
	int rc;
	bool r;

	*tu = NULL;
	if (includes)
		*includes = NULL;
	if (!root || !src || !tu || !why) {
		snprintf(why, why_len, "argumento nulo");
		return false;
	}
	why[0] = '\0';

	abs = pf_abspath(root);
	if (!abs) {
		snprintf(why, why_len, "la raiz no resuelve: %s", root);
		return false;
	}
	if (!pf_build_pp(abs, src, true, cmd, sizeof(cmd), why, why_len)) {
		free(abs);
		return false;
	}
	rc = pf_run_sh(cmd, abs, &all, why, why_len);
	free(abs);

	if (rc != 0) {
		pp_diagnose(all, why, why_len, rc, " (-H)");
		free(all);
		return false;
	}
	r = pp_split(all, tu, includes, why, why_len);
	if (!r && why[0] == '\0')
		snprintf(why, why_len, "pp_split fallo sin diagnóstico");
	free(all);
	return r;
}
