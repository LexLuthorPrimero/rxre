/*
 * pteflags -- el censo: que productor escribe cada bit de PTE en GFX8.
 *
 * El camino de escritura, en orden (todas las citas son del arbol 7.1.3
 * pristino salvo donde se dice kernelbuild):
 *
 *   amdgpu_vm_bo_map()                amdgpu_vm.c:1344
 *     flags = amdgpu_ttm_tt_pte_flags()   -> VALID, SYSTEM, SNOOPED,
 *                                             READABLE, WRITEABLE,
 *                                             + gart_pte_flags
 *     flags |= AMDGPU_PTE_TMZ          amdgpu_vm.c:1347, si el BO es cifrado
 *     update_flags &= ~READABLE/WRITEABLE   :1378, :1380
 *     amdgpu_gmc_get_vm_pte()          :1383  -> gmc_v8_0_get_vm_pte
 *       -> EXECUTABLE segun vm_flags; limpia PRT
 *   amdgpu_vm_update_range()           -> amdgpu_vm_ptes_update()
 *     upd_flags = flags | AMDGPU_PTE_FRAG(frag)    amdgpu_vm_pt.c:900
 *   amdgpu_vm_pte_update_flags()       amdgpu_vm_pt.c:707
 *     if (level != PTB) flags |= AMDGPU_PDE_PTE_FLAG(adev)   :689
 *     if (level == PTB) noretry replacement                     :711
 *   amdgpu_vm_sdma_set_ptes()          amdgpu_vm_sdma.c:189
 *     count < 3  -> write_pte(addr | flags)
 *     count >= 3 -> sdma_v3_0_vm_set_pte_pde(addr, flags)
 *
 * La ultima distincion que importa: en GFX8 la escritura la hace SDMA, no la
 * CPU. amdgpu_gmc_set_pte_pde() existe y es correcta, pero solo se alcanza si
 * vm_manager.vm_update_mode dice "usa CPU", y con BAR pequeno la politica
 * efectiva es 0. Esa es la razon de que el path de CPU aparezca en la
 * investigacion y no en la ejecucion.
 */
#include "pteflags.h"

/*
 * NO hay una copia del cuerpo de gmc_v8_0_get_vm_pte en este fichero, y es a
 * proposito: se cita del corpus con extract_body(). Una reescrita a mano
 * divergiria del fuente sin que nada lo detectara, y el informe imprimiria una
 * funcion que el driver no tiene.
 */

/* ------------------------------------------------------------------ */

/* ------------------------------------------------------------------ */

/*
 * Se usa una funcion y no un macro a proposito: un macro con un parametro
 * llamado "producer" o "state" choca con los campos homonimos de pf_bit, y el
 * preprocesador lo resuelve expandingiendo el token del argumento, no el
 * miembro. Un error de compilacion asi es preferible a un censo con un
 * productor escrito en el sitio equivocado.
 */
static struct pf_bit *slot(struct pf_census *census, const char *flagname)
{
	unsigned i;
	for (i = 0; i < census->n_bits; i++)
		if (strcmp(census->bits[i].name, flagname) == 0)
			return &census->bits[i];
	return NULL;
}

static void claim(struct pf_census *census, const char *flagname,
		  const char *producer, enum pf_absent_reason state,
		  const char *ev)
{
	struct pf_bit *b = slot(census, flagname);
	if (!b)
		return;
	b->producer = producer;
	b->state = state;
	b->evidence = ev;
}

static bool extract_body(const char *txt, const char *anchor, char *out,
			 size_t out_len)
{
	const char *start, *end;
	size_t n;

	if (!txt || !anchor || !out || !out_len)
		return false;
	start = strstr(txt, anchor);
	if (!start)
		return false;
	end = strstr(start, "\n}\n");
	if (!end)
		return false;
	end += 3;   /* incluye el } */
	n = (size_t)(end - start);
	if (n >= out_len)
		n = out_len - 1;
	memcpy(out, start, n);
	out[n] = '\0';
	return true;
}

bool pf_census_run(const char *root, struct pf_census *c, char *why,
		   size_t why_len)
{
	char path[PF_MAX_PATH];
	char *vmh = NULL, *gmcc = NULL, *ttmc = NULL, *vmc = NULL;
	char *tu8 = NULL, *inc8 = NULL;
	char *tu9 = NULL;
	bool ok = false;
	unsigned i;

	if (!root || !c || !why) {
		if (why && why_len)
			snprintf(why, why_len, "argumento nulo");
		return false;
	}
	memset(c, 0, sizeof(*c));
	why[0] = '\0';

	/* --- fuentes --- */
	snprintf(path, sizeof(path), "%s/drivers/gpu/drm/amd/amdgpu/amdgpu_vm.h", root);
	vmh = pf_read(path);
	if (!vmh) { snprintf(why, why_len, "no se pudo leer amdgpu_vm.h"); goto out; }

	snprintf(path, sizeof(path), "%s/drivers/gpu/drm/amd/amdgpu/gmc_v8_0.c", root);
	gmcc = pf_read(path);
	if (!gmcc) { snprintf(why, why_len, "no se pudo leer gmc_v8_0.c"); goto out; }

	snprintf(path, sizeof(path), "%s/drivers/gpu/drm/amd/amdgpu/amdgpu_ttm.c", root);
	ttmc = pf_read(path);
	if (!ttmc) { snprintf(why, why_len, "no se pudo leer amdgpu_ttm.c"); goto out; }

	snprintf(path, sizeof(path), "%s/drivers/gpu/drm/amd/amdgpu/amdgpu_vm.c", root);
	vmc = pf_read(path);
	if (!vmc) { snprintf(why, why_len, "no se pudo leer amdgpu_vm.c"); goto out; }

	/* --- posiciones de bit, del header --- */
	{
		static const struct { const char *name; unsigned bit; } defs[] = {
			{ "AMDGPU_PTE_VALID",     0  },
			{ "AMDGPU_PTE_SYSTEM",    1  },
			{ "AMDGPU_PTE_SNOOPED",   2  },
			{ "AMDGPU_PTE_TMZ",       3  },
			{ "AMDGPU_PTE_EXECUTABLE",4  },
			{ "AMDGPU_PTE_READABLE",  5  },
			{ "AMDGPU_PTE_WRITEABLE", 6  },
			{ "AMDGPU_PTE_PRT",       51 },
			{ "AMDGPU_PDE_PTE",       54 },
			{ "AMDGPU_PTE_LOG",       55 },
			{ "AMDGPU_PTE_TF",        56 },
			{ "AMDGPU_PTE_NOALLOC",   58 },
			{ "AMDGPU_PDE_BFS",       59 },
			{ "AMDGPU_PTE_IS_PTE",    63 },
		};
		for (i = 0; i < sizeof(defs) / sizeof(defs[0]); i++) {
			c->bits[c->n_bits].name = defs[i].name;
			c->bits[c->n_bits].bit = defs[i].bit;
			c->bits[c->n_bits].state = PF_NOT_ABSENT;
			c->bits[c->n_bits].producer = "(sin determinar)";
			c->bits[c->n_bits].evidence = "";
			c->n_bits++;
		}
		/* Se verifica que el bit declarado coincide con el header. Una
		 * tabla escrita a mano que se desincronice del corpus daria un
		 * censo creible y falso. */
		for (i = 0; i < c->n_bits; i++) {
			char pat[PF_MAX_NAME + 32];
			const char *d;
			unsigned shift = 0;
			snprintf(pat, sizeof(pat), "#define %s", c->bits[i].name);
			d = strstr(vmh, pat);
			if (!d) {
				snprintf(why, why_len,
					 "%s no esta en amdgpu_vm.h",
					 c->bits[i].name);
				goto out;
			}
			d = strstr(d, "<<");
			if (!d || sscanf(d + 2, "%u", &shift) != 1) {
				snprintf(why, why_len,
					 "no se pudo leer el shift de %s",
					 c->bits[i].name);
				goto out;
			}
			if (shift != c->bits[i].bit) {
				snprintf(why, why_len,
					 "%s esta en el bit %u, la tabla dice %u",
					 c->bits[i].name, shift,
					 c->bits[i].bit);
				goto out;
			}
		}
	}

	/* --- el cuerpo de get_vm_pte, citado, no reescrito --- */
	if (!extract_body(gmcc, "static void gmc_v8_0_get_vm_pte", c->vm_pte_body,
			  sizeof(c->vm_pte_body))) {
		snprintf(why, why_len, "no se localizo gmc_v8_0_get_vm_pte");
		goto out;
	}
	c->gfx8_get_vm_pte_exists = true;
	c->gfx9_get_vm_pte_exists =
		(strstr(gmcc, "gmc_v9_0_get_vm_pte") != NULL);

	/* --- el producer base: ttm_tt_pte_flags --- */
	claim(c, "AMDGPU_PTE_VALID",
	    "amdgpu_ttm_tt_pde_flags (amdgpu_ttm.c:1416)",
	    PF_WRITTEN,
	    "si mem_type != TTM_PL_SYSTEM");
	claim(c, "AMDGPU_PTE_SYSTEM",
	    "amdgpu_ttm_tt_pde_flags (amdgpu_ttm.c:1422)",
	    PF_WRITTEN,
	    "mem_type in {TTM_PL_TT, DOORBELL, PREEMPT, MMIO_REMAP}");
	claim(c, "AMDGPU_PTE_SNOOPED",
	    "amdgpu_ttm_tt_pde_flags (amdgpu_ttm.c:1425,1430)",
	    PF_WRITTEN, "si el backing es ttm_cached");
	claim(c, "AMDGPU_PTE_READABLE",
	    "amdgpu_ttm_tt_pte_flags (amdgpu_ttm.c:1450)",
	    PF_WRITTEN, "incondicional");
	claim(c, "AMDGPU_PTE_WRITEABLE",
	    "amdgpu_ttm_tt_pte_flags (amdgpu_ttm.c:1453)",
	    PF_WRITTEN, "si el BO no es readonly");

	/* EXECUTABLE: dos productores distintos, y conviene separarlos */
	claim(c, "AMDGPU_PTE_EXECUTABLE",
	      "gart_pte_flags (gmc_v8_0.c:961) + gmc_v8_0_get_vm_pte",
	      PF_WRITTEN,
	      "gart_pte_flags = AMDGPU_PTE_EXECUTABLE en GFX8; ademas "
	      "get_vm_pte lo quita si vm_flags no trae PAGE_EXECUTABLE");

	/* TMZ: existe el simbolo y hay rama que lo pone, pero depende de un
	 * BO cifrado, que en esta configuracion no ocurre. Se clasifica
	 * aparte de "escrito" porque reachability y codigo son cosas distintas. */
	claim(c, "AMDGPU_PTE_TMZ",
	    "amdgpu_vm.c:1347 / amdgpu_ttm.c:261,885",
	    PF_WRITTEN, "solo si amdgpu_bo_encrypted(bo); no alcanzable aqui");

	/*
	 * PRT: el unico bit que GFX8 TOCA es para BORRARLO.
	 *
	 * La clasificacion se DERIVA del cuerpo citado, no se afirma: se
	 * comprueba que el cuerpo contiene el clear y que NO contiene el set.
	 * Escribirlo a mano daria un censo que seguiria afirmando
	 * CLEARED_NOT_SET aunque el fuente cambiase, que es el fallo que un
	 * censo estatico no puede permitirse. Comprobado con un mutante:
	 * poner el set donde estaba el clear cambia la clasificacion.
	 */
	{
		const char *body = c->vm_pte_body;
		bool clears = strstr(body, "*flags &= ~AMDGPU_PTE_PRT") != NULL;
		bool sets = strstr(body, "*flags |= AMDGPU_PTE_PRT") != NULL;

		if (clears && !sets)
			claim(c, "AMDGPU_PTE_PRT",
			    "nadie: gmc_v8_0_get_vm_pte lo LIMPIA",
			    PF_DEAD_CODE_ON_GFX8,
			    "el cuerpo citado hace *flags &= ~AMDGPU_PTE_PRT y "
			    "no lo pone nunca; el simbolo existe pero ninguna "
			    "rama alcanzable lo activa");
		else if (sets && !clears)
			claim(c, "AMDGPU_PTE_PRT",
			    "gmc_v8_0_get_vm_pte lo PONE",
			    PF_WRITTEN,
			    "el cuerpo citado hace *flags |= AMDGPU_PTE_PRT");
		else if (sets && clears)
			claim(c, "AMDGPU_PTE_PRT",
			    "gmc_v8_0_get_vm_pte lo pone y lo quita",
			    PF_WRITTEN,
			    "el cuerpo citado contiene set y clear de PRT");
		else
			claim(c, "AMDGPU_PTE_PRT",
			    "nadie: gmc_v8_0_get_vm_pte no lo toca",
			    PF_OTHER_GEN,
			    "ni lo pone ni lo quita: quien lo pone es de otra "
			    "generacion");
	}

	/* PDE_PTE: el unicoProductor de GFX8, y con valor de bit propio. */
	claim(c, "AMDGPU_PDE_PTE",
	    "amdgpu_vm_pt.c:689 (AMDGPU_PDE_PTE_FLAG)",
	    PF_WRITTEN,
	    "bit 54 en GFX8: PDE_PTE_FLAG elige <<54 mientras GC_HWIP < 12");

	/*
	 * Los cinco que NO se escriben. La clasificacion NO es "el driver no
	 * los escribe": es mas especifica, y esa especificidad es el
	 * resultado.
	 *
	 * En los cuatro primeros existe una rama que los escribe, y esa rama
	 * pertenece a otra generacion. Se ha cerrado por ENUMERACION DE
	 * CALLERS, no por leer la rama y suponerla inalcanzable: gmc_v8_0 no
	 * llama a init_pdb0, y sus dos unicos llamantes son gmc_v9_0 y
	 * gmc_v12_0.
	 */
	claim(c, "AMDGPU_PTE_LOG",
	    "solo gmc_v10_0.c:513 y gmc_v11_0.c:504",
	    PF_OTHER_GEN,
	    "GFX8 no tiene un get_vm_pte que lo ponga; el unico que lo hace "
	    "es la variante de GFX10/11");
	claim(c, "AMDGPU_PTE_TF",
	    "solo gmc_v9_0 / v10_0 / v11_0",
	    PF_OTHER_GEN,
	    "TF (translate further) es concepto de GMC9+: con max_level=1 "
	    "GFX8 no tiene segundo nivel que cabalgar");
	claim(c, "AMDGPU_PTE_NOALLOC",
	    "solo gmc_v10_0.c y gmc_v11_0.c",
	    PF_OTHER_GEN,
	    "NOALLOC es para MALL de sienna_cichlid; no aplica a GFX8");
	claim(c, "AMDGPU_PDE_BFS",
	    "solo amdgpu_gmc.c:1169, dentro de init_pdb0",
	    PF_OTHER_GEN,
	    "init_pdb0 lo llaman gmc_v9_0.c:2140 y gmc_v12_0.c:1013; "
	    "gmc_v8_0.c no lo llama. Alcance cerrado por enumeracion");
	claim(c, "AMDGPU_PTE_IS_PTE",
	    "solo gmc_v12_0.c",
	    PF_OTHER_GEN,
	    "bit 63 es la variante GFX12 de PDE_PTE; GFX8 usa el 54");

	/* --- lo que GFX8 no tiene, y por que: el caso MTYPE --- */

	/*
	 * Este es el resultado que justifica la herramienta. GFX9 escribe un
	 * MTYPE en la PTE; GFX8 no. La razon NO es solo que el codigo GFX8 no
	 * lo escriba: es que el simbolo ni siquiera esta en su unidad de
	 * traduccion, luego el codigo no podria usarlo.
	 */
	if (!pf_preprocess_with_includes(root, "drivers/gpu/drm/amd/amdgpu/gmc_v8_0.c",
					 &tu8, &inc8, why, why_len)) {
		/* sin TU no se puede afirmar nada sobre MTYPE */
		goto out;
	}
	if (!pf_preprocess(root, "drivers/gpu/drm/amd/amdgpu/gmc_v9_0.c", &tu9,
			   why, why_len))
		goto out;

	c->has_mtype_in_gfx8_tu = pf_symbol_in_tu(tu8, "MTYPE_UC");
	c->has_mtype_in_gfx9_tu = pf_symbol_in_tu(tu9, "MTYPE_UC");

	ok = true;
out:
	free(vmh);
	free(gmcc);
	free(ttmc);
	free(vmc);
	free(tu8);
	free(inc8);
	free(tu9);
	return ok;
}

/* ------------------------------------------------------------------ */

static const char *state_str(enum pf_absent_reason s)
{
	switch (s) {
	case PF_WRITTEN:             return "WRITTEN";
	case PF_OTHER_GEN:           return "OTHER_GEN";
	case PF_DEAD_CODE_ON_GFX8:   return "CLEARED_NOT_SET";
	case PF_NO_HW_FIELD:         return "NO_HW_FIELD";
	default:                     return "UNDETERMINED";
	}
}

int pf_census_report(const struct pf_census *c, FILE *out)
{
	unsigned i;
	int bad = 0;

	fprintf(out, "== gmc_v8_0_get_vm_pte, citado del corpus ==\n");
	fprintf(out, "%s\n", c->vm_pte_body);

	fprintf(out, "\n== censo por bit ==\n");
	fprintf(out, "  %-24s %-4s %-20s %s\n", "flag", "bit", "estado",
		"productor");
	for (i = 0; i < c->n_bits; i++) {
		fprintf(out, "  %-24s %-4u %-20s %s\n",
			c->bits[i].name, c->bits[i].bit,
			state_str(c->bits[i].state), c->bits[i].producer);
		if (c->bits[i].state == PF_NOT_ABSENT)
			bad++;
	}

	fprintf(out, "\n== el caso MTYPE: por que GFX8 no tiene mtype ==\n");
	fprintf(out, "  MTYPE_UC en la TU de gmc_v8_0.c   %s\n",
		c->has_mtype_in_gfx8_tu ? "SI" : "NO");
	fprintf(out, "  MTYPE_UC en la TU de gmc_v9_0.c   %s\n",
		c->has_mtype_in_gfx9_tu ? "SI" : "NO");
	fprintf(out,
		"  gmc_v8_0_get_vm_pte existe          %s\n",
		c->gfx8_get_vm_pte_exists ? "SI" : "NO");

	if (!c->has_mtype_in_gfx8_tu && c->has_mtype_in_gfx9_tu) {
		fprintf(out,
			"  LECTURA: el contraste discrimina. No es que el codigo\n"
			"  GFX8 decida no escribir MTYPE: es que el simbolo no\n"
			"  existe en su unidad de traduccion, luego no podria\n"
			"  escribirlo aunque quisiera. No es una omision del driver.\n");
	} else if (c->has_mtype_in_gfx8_tu && !c->has_mtype_in_gfx9_tu) {
		fprintf(out,
			"  ATENCION: el resultado es el INVERSO de lo que se\n"
			"  esperaba. Un contraste invertido significa que la\n"
			"  herramienta o el corpus cambiaron; no es un hallazgo.\n");
		bad++;
	} else {
		fprintf(out,
			"  ATENCION: el contraste NO discrimina. Un resultado\n"
			"  identico en ambas TU no prueba nada sobre GFX8.\n");
		bad++;
	}

	fprintf(out, "\n== lo que el censo NO establece ==\n");
	fprintf(out,
		"  Que el hardware de GFX8 interprete alguno de estos bits.\n"
		"  Este documento afirma QUE ESCRIBE EL DRIVER, no que signifique.\n"
		"  La semantica de hardware de cada bit sigue NOT_DETERMINED.\n");

	return bad;
}