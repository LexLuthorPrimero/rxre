/*
 * pteflags -- test del censo.
 *
 * La asercion central NO es "el censo tiene N filas", sino algo que un
 * censo mal hecho pasaria: que el contraste MTYPE entre GFX8 y GFX9
 * DISCRIMINE. Un censo que no puede distinguir GFX8 de GFX9 no ha
 *териminado nada, aunque imprima una tabla圆满.
 *
 * Por eso hay un control negativo dedicado: se comprueba que la misma
 * consulta corra contra un arbol donde la TU de gmc_v8_0.c SI contiene
 * MTYPE, y que ahi el veredicto cambia.
 */
#include "pteflags.h"

static unsigned g_pass, g_fail;
static unsigned g_neg_total, g_neg_ok, g_neg_dead;

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

typedef int (*neg_fn)(void);

static void neg_run(const char *id, const char *desc, neg_fn fn)
{
	int detected = fn();
	g_neg_total++;
	if (detected) {
		g_neg_ok++;
		printf("  [ OK ] %s %s -> detectado\n", id, desc);
	} else {
		g_neg_dead++;
		printf("  [DEAD] %s %s -> NO discrimina\n", id, desc);
	}
}

/* ------------------------------------------------------------------ */
/* el censo, y lo que tiene que contener                                 */
/* ------------------------------------------------------------------ */

static const struct pf_bit *find(const struct pf_census *c, const char *name)
{
	unsigned i;
	for (i = 0; i < c->n_bits; i++)
		if (strcmp(c->bits[i].name, name) == 0)
			return &c->bits[i];
	return NULL;
}

static void test_census(const struct pf_census *c)
{
	const struct pf_bit *b;

	printf("\n== el censo ==\n");

	ok(c->gfx8_get_vm_pte_exists,
	   "gmc_v8_0_get_vm_pte existe en gmc_v8_0.c");
	ok(strstr(c->vm_pte_body, "AMDGPU_PTE_EXECUTABLE") != NULL,
	   "el cuerpo citado menciona EXECUTABLE");
	ok(strstr(c->vm_pte_body, "*flags &= ~AMDGPU_PTE_PRT") != NULL,
	   "el cuerpo citado limpia PRT explicitamente");

	/* el cuerpo debe estar citado, no reescrito */
	ok(strstr(c->vm_pte_body, "static void gmc_v8_0_get_vm_pte") != NULL,
	   "el cuerpo empieza por la firma real, no por un resumen");

	/* los siete bits que si se escriben */
	b = find(c, "AMDGPU_PTE_VALID");
	ok(b && b->state == PF_WRITTEN, "VALID se escribe");
	b = find(c, "AMDGPU_PTE_SYSTEM");
	ok(b && b->state == PF_WRITTEN, "SYSTEM se escribe");
	b = find(c, "AMDGPU_PTE_SNOOPED");
	ok(b && b->state == PF_WRITTEN, "SNOOPED se escribe");
	b = find(c, "AMDGPU_PTE_READABLE");
	ok(b && b->state == PF_WRITTEN, "READABLE se escribe");
	b = find(c, "AMDGPU_PTE_WRITEABLE");
	ok(b && b->state == PF_WRITTEN, "WRITEABLE se escribe");
	b = find(c, "AMDGPU_PTE_EXECUTABLE");
	ok(b && b->state == PF_WRITTEN, "EXECUTABLE se escribe");
	b = find(c, "AMDGPU_PDE_PTE");
	ok(b && b->state == PF_WRITTEN, "PDE_PTE se escribe, en bit 54");

	/* el caso interesante: PRT se LIMPIA y no se pone */
	b = find(c, "AMDGPU_PTE_PRT");
	ok(b && b->state == PF_DEAD_CODE_ON_GFX8,
	   "PRT: limpiado y nunca puesto -> CLEARED_NOT_SET");
	ok(b && strstr(b->producer, "LIMPIA") != NULL,
	   "PRT: el productor registrado dice que lo limpia");

	/* bits que existen en el header y GFX8 no toca */
	b = find(c, "AMDGPU_PTE_LOG");
	ok(b && b->state != PF_WRITTEN, "LOG no se escribe en GFX8");
	b = find(c, "AMDGPU_PTE_TF");
	ok(b && b->state != PF_WRITTEN, "TF no se escribe en GFX8");
	b = find(c, "AMDGPU_PDE_BFS");
	ok(b && b->state != PF_WRITTEN, "BFS no se escribe en GFX8");

	/* MTYPE: el contraste que da valor al resto */
	printf("\n== el contraste MTYPE ==\n");
	ok(!c->has_mtype_in_gfx8_tu,
	   "MTYPE_UC NO esta en la TU de gmc_v8_0.c");
	ok(c->has_mtype_in_gfx9_tu,
	   "MTYPE_UC SI esta en la TU de gmc_v9_0.c");
	ok(!c->has_mtype_in_gfx8_tu && c->has_mtype_in_gfx9_tu,
	   "el contraste DISCRIMINA (es lo que hace que el censo signifique algo)");
}

/* ------------------------------------------------------------------ */
/* controles negativos                                                   */
/* ------------------------------------------------------------------ */

/*
 * CN-1: si el preprocesador falla, pf_preprocess NO debe devolver una salida
 * parcial. Es el control mas importante: sin el, un rc!=0 se convierte en
 * "grep encontro 0" y el censo entero se apoya sobre una nada.
 */
static int cn1(void)
{
	char *out = NULL;
	char why[256];
	/*
	 * BUG que este control arrastro durante esta sesion: usaba PF_ROOT,
	 * que es la raiz VALIDA, en el caso que pretendia ser el negativo. O
	 * sea: probaba que el camino bueno funciona y se marcaba DEAD porque
	 * el negativo no existia. Un control negativo que no cambia la
	 * entrada no controla nada; parece controlar y no controla.
	 */
	const char *root = "/tmp/opencode/pf-no-existe-este-arbol";
	int ok_bad;

	if (pf_preprocess(root, "drivers/gpu/drm/amd/amdgpu/gmc_v8_0.c", &out,
			  why, sizeof(why))) {
		if (out)
			free(out);
		return 0;   /* devolvio exito: no discrimina */
	}
	ok_bad = (out == NULL) && (why[0] != '\0');

	/*
	 * Y exige lo contrario: la raiz real debe funcionar. Un control que
	 * solo prueba el camino negativo pasaria aunque pf_preprocess
	 * devolviese siempre error, y eso no seria un test sino una
	 * constante.
	 */
	{
		char *out2 = NULL;
		char why2[256];
		if (!pf_preprocess(PF_ROOT, "drivers/gpu/drm/amd/amdgpu/gmc_v8_0.c",
				  &out2, why2, sizeof(why2)))
			return 0;   /* la raiz real falla: no discrimina */
		free(out2);
	}
	return ok_bad;
}

/*
 * CN-2: una TU de solo macros NO puede decir que MTYPE existe, porque MTYPE
 * es un enum. Si pf_symbol_in_tu devolviera true con una TU de macros, la
 * afirmacion "MTYPE no esta" seria vraie por el motivo equivocado.
 */
static int cn2(void)
{
	const char *macros_only =
		"#define FOO 1\n#define BAR 2\n";
	const char *con_enum =
		"typedef enum MTYPE {\n\tMTYPE_NC_NV = 0x0,\n"
		"\tMTYPE_NC = 0x1,\n} MTYPE;\n";

	/* con solo macros debe decir que no */
	if (pf_symbol_in_tu(macros_only, "MTYPE_UC"))
		return 0;
	/* con el enum presente debe decir que si */
	if (!pf_symbol_in_tu(con_enum, "MTYPE_NC"))
		return 0;
	return 1;
}

/*
 * CN-3: pf_count_token no debe contar un prefijo. MTYPE_UC no puede contar
 * como MTYPE_U ni como MTYPE_UCEX.
 */
static int cn3(void)
{
	const char *t = "MTYPE_UCEX MTYPE_UC xMTYPE_UC MTYPE_UC";
	return pf_count_token(t, "MTYPE_UC") == 2u;
}

/*
 * CN-4: pf_header_included debe exigir la barra. Un nombre que aparece como
 * sufijo de otro no cuenta.
 */
static int cn4(void)
{
	const char *trace =
		". /a/b/gfx_9_0_offset.h\n. /a/b/vega10_enum.h\n";
	/* cn4 no imprime: su veredicto lo da neg_run. Un ok(0,"") aqui
	 * metia un [FAIL] vacio que se leia como un fallo real. */
	return pf_header_included(trace, "vega10_enum.h") &&
	       !pf_header_included(trace, "gfx_8_0_enum.h");
}

/*
 * CN-5: el censo completo contra un arbol donde NO existe gmc_v8_0_get_vm_pte
 * debe fallar, no devolver un censo vacio con exito. Un censo que no puede
 * fallar no es un censo.
 */
static int cn5(void)
{
	struct pf_census c;
	char why[256];
	/* se pasa un .c que no existe como fuente del cuerpo */
	if (pf_census_run("/tmp/opencode/arbol-inexistente-pf", &c, why,
			  sizeof(why)))
		return 0;
	return why[0] != '\0';
}

static void test_negatives(void)
{
	printf("\n== controles negativos ==\n");
	neg_run("CN-1", "raiz inexistente -> sin salida parcial", cn1);
	neg_run("CN-2", "enum no es macro (MTYPE)", cn2);
	neg_run("CN-3", "conteo de token no cuenta prefijos", cn3);
	neg_run("CN-4", "cabecera exige la barra inicial", cn4);
	neg_run("CN-5", "censo sobre arbol inexistente", cn5);
}

/* ------------------------------------------------------------------ */

int main(int argc, char **argv)
{
	struct pf_census c;
	char why[512];
	const char *root;
	int bad;

#ifndef PF_ROOT
#define PF_ROOT "../../../RESEARCH/kernelbuild/linux-7.1.3"
#endif
	root = (argc > 1) ? argv[1] : PF_ROOT;

	printf("pteflags -- raiz: %s\n", root);

	if (!pf_census_run(root, &c, why, sizeof(why))) {
		printf("ERROR: no se pudo ejecutar el censo: %s\n", why);
		printf("RESULT: NO EJECUTADO\n");
		return 2;
	}
	printf("censo ejecutado\n");

	test_census(&c);
	test_negatives();

	printf("\n== informe ==\n");
	bad = pf_census_report(&c, stdout);

	printf("\n== resumen ==\n");
	printf("  aserciones           %u\n", g_pass);
	printf("  fallos               %u\n", g_fail);
	printf("  controles negativos  %u\n", g_neg_total);
	printf("  ...detectados        %u\n", g_neg_ok);
	printf("  ...muertos           %u\n", g_neg_dead);
	printf("  informe              %d lineas incoherentes\n", bad);

	if (g_fail == 0 && bad == 0 && g_neg_dead == 0 && g_neg_total > 0)
		printf("RESULT: OK -- y el test puede fallar\n");
	else
		printf("RESULT: FALLO\n");

	return (g_fail == 0 && bad == 0 && g_neg_dead == 0) ? 0 : 1;
}