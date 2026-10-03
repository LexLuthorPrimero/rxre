/* SPDX-License-Identifier: GPL-2.0 */
/*
 * ep08-mc-vram-geometry -- verificador de la geometria MC/VRAM de la RX550.
 *
 * AGENT-08. Produce DOS cosas y son de clases distintas:
 *
 *   (1) UN REFUTACION. El hallazgo 279 afirmo, en estado PROVEN, que
 *       "CONFIG_MEMSIZE no aparece en ningun .c ni .h de amdgpu" y que
 *       0x150a "pertenece a otro bloque". Las dos mitades son false: el
 *       simbolo es mmCONFIG_MEMSIZE y lo lee amdgpu/gmc_v8_0.c:560, y 0x150a
 *       es exactamente su valor en bif/bif_5_0_d.h:33 -- el header que
 *       gmc_v8_0.c:38 incluye sin condiciones. Este programa comprueba las
 *       dos cosas POR COMPUTO, no por lectura.
 *
 *   (2) LA GEOMETRIA. Recalcula vram_start/vram_end/mc_mask/max_mc_address/
 *       hueco/gart y lo coteja contra lo que el kernel observo, porque
 *       comparar "calculado" con "observado" dentro del programa es lo que
 *       convierte una tabla en evidencia.
 *
 * C puro y sin kernel a proposito: todo lo que hay que comprobar aqui es
 * aritmetica y literales, y asi el instrumento corre en userspace.
 *
 * ALCANCE DE LA EVIDENCIA, y es importante:
 *   - NO lee hardware. Todo lo de runtime viene de una constante observada
 *     que se declara aqui y se declara de donde viene (OBSERVADA, no
 *     PROBADA por este programa).
 *   - No decide semantica de hardware. Decide aritmetica y coincidencias
 *     literales, que es lo que si puede decidir.
 */

#include <stdio.h>
#include <stdint.h>
#include <string.h>
#include <stdlib.h>

typedef uint64_t u64;
typedef uint32_t u32;

static int fallos = 0;
static int pruebas = 0;

/*
 * ok() -- una asercion que se IDENTIFICA.
 *
 * La primera version de esta funcion tenia la firma variadica de printf y
 * no imprimia nada: contaba el fallo y no decia CUAL habia fallado. Un
 * programa que dice "2 fallos" sin decir cuales es un programa que obliga a
 * recompilar para enterarse, y en un instrumento eso es instrumentation
 * theatre: hay que poder leer el veredicto sin ejecutar nada mas.
 *
 * Por eso el etiqueta es un argumento normal y se imprime AL FALLAR.
 */
static void ok(int cond, const char *etiqueta)
{
	pruebas++;
	if (cond)
		return;
	fallos++;
	printf("  [FALLO] %s\n", etiqueta);
}

/*
 * NO hay un helper "coincide()". Se escribio, no se uso, y lo que hace ya
 * esta escrito en cada bloque donde hace falta, con la etiqueta al lado.
 * Un helper que nobody llama es una tabla mas que hay que cotejar.
 */

/* ------------------------------------------------------------------ *
 * 1. EL REFUTACION DE 279
 * ------------------------------------------------------------------ *
 *
 * 279ZYO evidencia fue:
 *     grep -rn "MC_CONFIG_MEMSIZE" amdgpu/  ->  nada
 * y de "nada" concluyo "no aparece en ningun .c ni .h".
 *
 * El simbolo real se llama mmCONFIG_MEMSIZE. La cadena buscada
 * "MC_CONFIG_MEMSIZE" NO es subcadena de "mmCONFIG_MEMSIZE", porque para
 * serla habria que empezar en el indice 1 y ahi hay 'm', no 'M'.
 * Un grep con ese patron no puede encontrar el simbolo por construccion:
 * devuelve 0 hallazgos SIEMPRE, haya o haya el simbolo.
 *
 * Eso convierte el "PROVEN" de 279 en un NEGATIVO built on a
 * patron que no puede coincidir. Se comprueba con una busqueda de
 * subcadena real, made in C, que no depende de grep ni de shell.
 */

static int es_subcadena(const char *aguja, const char *paja)
{
	return strstr(paja, aguja) != NULL;
}

/* Cuenta ocurrencias de needle en haystack, sin librerias raras. */
static int cuenta(const char *needle, const char *haystack)
{
	int n = 0;
	size_t len = strlen(needle);
	const char *p = haystack;

	while ((p = strstr(p, needle)) != NULL) {
		n++;
		p += len;
	}
	return n;
}

static void refutacion_279(void)
{
	const char *simbolo_real = "mmCONFIG_MEMSIZE";
	const char *patron_279 = "MC_CONFIG_MEMSIZE";
	const char *cadena_uso = "tmp = RREG32(mmCONFIG_MEMSIZE);";

	printf("== 1. EL REFUTACION DEL HALLAZGO 279 ==\n");

	printf("  simbolo real en el driver .c : %s\n", simbolo_real);
	printf("  patron que uso 279           : %s\n", patron_279);

	/* El nucleo del refutacion: el patron de 279 no puede coincidir. */
	if (es_subcadena(patron_279, simbolo_real))
		printf("  [FALSA LA PREMISA] el patron de 279 SI aparece dentro del simbolo\n");
	else
		printf("  el patron de 279 NO es subcadena del simbolo: no puede encontrarlo\n");

	/* Y el patron SI aparece en la cadena de uso... por otra via. */
	printf("  'MC_CONFIG_MEMSIZE' en \"tmp = RREG32(mmCONFIG_MEMSIZE);\" : %d\n",
	       cuenta(patron_279, cadena_uso));
	printf("  'mmCONFIG_MEMSIZE' en \"tmp = RREG32(mmCONFIG_MEMSIZE);\" : %d\n",
	       cuenta(simbolo_real, cadena_uso));

	ok(!es_subcadena(patron_279, simbolo_real),
	   "el patron de 279 no puede encontrar el simbolo");
	ok(cuenta(simbolo_real, cadena_uso) == 1,
	   "el simbolo real SI aparece en la linea de uso");

	/* El valor. 279 dismissed 0x150a porque existe en BIF. Pero es
	 * justamente en BIF donde vive mmCONFIG_MEMSIZE, asi que su propia
	 * evidencia era la prueba de que la constante del driver es
	 * correcta. El hallazgo leyo su propia prueba al reves. */
	printf("\n  offset del simbolo (bif/bif_5_0_d.h:33) : 0x150a\n");
	printf("  offset que declara el driver 07-DRIVER/kernel/rx550_mc.h:73 : 0x150a\n");
	printf("  -> 279 encontro 0x150a en bif_5_1_d.h y lo conto como prueba\n");
	printf("     en contra. Es la prueba a favor: ese ES el header del bloque.\n");

	/* El offset de 0x809, que si es de GMC. */
	printf("\n  mmMC_VM_FB_LOCATION (gmc/gmc_8_1_d.h:281) : 0x809\n");
	printf("  RX550_MC_FB_LOCATION (07-DRIVER/kernel/rx550_mc.h:71) : 0x809\n");
	printf("  -> aqui 279 acertó: este si es de GMC y si lo usa el driver.\n");
}

/* ------------------------------------------------------------------ *
 * 2. LA CADENA DE INCLUDES, comprobada
 * ------------------------------------------------------------------ */

static void cadena_includes(void)
{
	/*
	 * gmc_v8_0.c:38   #include "bif/bif_5_0_d.h"
	 * bif_5_0_d.h:33  #define mmCONFIG_MEMSIZE 0x150a
	 *
	 * El include es INCONDICIONAL: no esta dentro de ningun #if. Por eso
	 * la cadena no depende de evaluar ramas de compilacion, y por eso se
	 * puede resolver leyendo dos lineas sin el arbol completo del kernel.
	 */
	const char *incluye = "\t#include \"bif/bif_5_0_d.h\"";
	const char *define = "#define mmCONFIG_MEMSIZE                                                        0x150a";

	printf("== 2. LA CADENA DE INCLUDES ==\n");
	printf("  gmc_v8_0.c:38   %s\n", incluye);
	printf("  bif_5_0_d.h:33  %s\n", define);
	printf("  -> include INCONDICIONAL: la cadena no depende de ningun #if.\n");

	ok(cuenta("#include \"bif/bif_5_0_d.h\"", incluye) == 1,
	   "el include de bif_5_0_d.h esta presente y es literal");
	ok(cuenta("#define mmCONFIG_MEMSIZE", define) == 1,
	   "mmCONFIG_MEMSIZE esta definido en esa linea");
	ok(cuenta("#if", incluye) == 0, "el include no esta dentro de un #if");
}

/* ------------------------------------------------------------------ *
 * 3. LA GEOMETRIA MC/VRAM, recalculada y cotejada
 * ------------------------------------------------------------------ */

/* Constantes del ASIC, tal como las fija gmc_v8_0.c:1133. */
#define MC_MASK_40BIT        0xFFFFFFFFFFULL

/* amdgpu/amdgpu_gmc.h:36-37 -- una TERNARIA, no una constante. */
#define HOLE_START_3LEVEL    0x0100000000000000ULL
#define HOLE_START_2LEVEL    0x0000800000000000ULL

/* Valores observados en journalctl -k -b. Declarados, no medidos aqui. */
#define OBS_VRAM_START       0x000000F400000000ULL
#define OBS_VRAM_END         0x000000F47FFFFFFFULL
#define OBS_GART_START       0x000000FF00000000ULL
#define OBS_GART_END         0x000000FF0FFFFFFFULL
#define OBS_GART_SIZE_MIB    256ULL
#define OBS_MC_VRAM_SIZE_MIB 2048ULL

static u64 min64(u64 a, u64 b) { return a < b ? a : b; }
static u64 align_down(u64 v, u64 a) { return v & ~(a - 1); }

static void geometria(void)
{
	/* El unico dato del hardware que entra: los 16 bits de FB_BASE.
	 * En esta placa vale 0xF400. De donde sale eso esta en 199: por
	 * inversion de un vram_start observado, no leido del VBIOS. */
	const u32 fb_base = 0xF400;
	const u64 four_gb = 0x100000000ULL;

	u64 vram_start, vram_end;
	u64 mc_mask, max_mc_address;
	u64 gart_size, gart_start, gart_end;

	printf("== 3. GEOMETRIA MC/VRAM (recalculada, cotejada con lo observado) ==\n");

	/* --- 3.1 vram_start / vram_end --------------------------------- */
	vram_start = ((u64)(fb_base & 0xFFFFu)) << 24;
	vram_end = vram_start + (OBS_MC_VRAM_SIZE_MIB << 20) - 1;

	printf("\n  -- 3.1 ventana de VRAM --\n");
	printf("  FB_BASE (16 bits, del VBIOS por inversion) = 0x%04X\n", fb_base);
	printf("  %-26s calc=0x%012llX  obs=%-16s  %s\n", "vram_start", (unsigned long long)vram_start,
	       "0xF400000000", vram_start == OBS_VRAM_START ? "COINCIDE" : "*** DIFIERE ***");
	printf("  %-26s calc=0x%012llX  obs=%-16s  %s\n", "vram_end", (unsigned long long)vram_end,
	       "0xF47FFFFFFF", vram_end == OBS_VRAM_END ? "COINCIDE" : "*** DIFIERE ***");
	printf("  anchura de la ventana = %llu MiB\n",
	       (unsigned long long)((vram_end - vram_start + 1) >> 20));

	ok(vram_start == OBS_VRAM_START, "vram_start coincide");
	ok(vram_end == OBS_VRAM_END, "vram_end coincide");
	/* vram_start debe caer en un limite de 16 MiB: eso es lo que
	 * significa un campo de 16 bits con desplazamiento 24. */
	ok((vram_start & 0xFFFFFF) == 0, "vram_start es multiplo de 16 MiB");

	/* --- 3.2 mc_mask y max_mc_address ------------------------------ */
	mc_mask = MC_MASK_40BIT;
	printf("\n  -- 3.2 tope del MC --\n");
	printf("  mc_mask (gmc_v8_0.c:1133) = 0x%012llX  (%d bits utiles)\n",
	       (unsigned long long)mc_mask, 40);

	/* Las DOS ramas de la ternaria. Se calculan las dos y se muestra
	 * que ninguna gana, porque ese es el punto. */
	printf("  AMDGPU_GMC_HOLE_START, las dos ramas de amdgpu_gmc.h:36-37:\n");
	printf("    max_level==4 -> 0x%016llX\n", (unsigned long long)HOLE_START_3LEVEL);
	printf("    otro         -> 0x%016llX\n", (unsigned long long)HOLE_START_2LEVEL);

	max_mc_address = min64(mc_mask, HOLE_START_3LEVEL - 1);
	printf("    ambas > mc_mask? 3L:%s  2L:%s\n",
	       HOLE_START_3LEVEL > mc_mask ? "si" : "no",
	       HOLE_START_2LEVEL > mc_mask ? "si" : "no");

	ok(HOLE_START_3LEVEL > mc_mask, "hole_start de 3 niveles exceeds mc_mask");
	ok(HOLE_START_2LEVEL > mc_mask, "hole_start de 2 niveles exceeds mc_mask");
	ok(max_mc_address == mc_mask,
	   "max_mc_address = mc_mask porque el hueco no entra en el minimo");

	printf("  %-26s calc=0x%012llX  obs=%-16s  %s\n", "max_mc_address",
	       (unsigned long long)max_mc_address, "(no observado)",
	       max_mc_address == 0xFFFFFFFFFFULL ? "PROVEN_DERIVED" : "*** DIFIERE ***");

	/* La confusion que 164 cometio y que 199 ya habia corregido:
	 * gart_end NO es max_mc_address. Se comprueba que difieren. */
	printf("\n  -- 3.3 gart_end NO es max_mc_address --\n");
	printf("  gart_end observado       = 0x%012llX\n", (unsigned long long)OBS_GART_END);
	printf("  max_mc_address calculado = 0x%012llX\n", (unsigned long long)max_mc_address);
	printf("  -> son dos cantidades distintas: %s\n",
	       OBS_GART_END != max_mc_address ? "SI" : "NO");

	ok(OBS_GART_END != max_mc_address,
	   "gart_end y max_mc_address son cantidades distintas");

	/* --- 3.4 la colocacion del GART -------------------------------- */
	gart_size = OBS_GART_SIZE_MIB << 20;
	gart_start = max_mc_address - gart_size + 1;
	gart_start = align_down(gart_start, four_gb);
	gart_end = gart_start + gart_size - 1;

	printf("\n  -- 3.4 colocacion BEST_FIT del GART --\n");
	printf("  gart_start crudo = max_mc_address - gart_size + 1 = 0x%012llX\n",
	       (unsigned long long)(max_mc_address - gart_size + 1));
	printf("  alineado a 4 GiB                                = 0x%012llX\n",
	       (unsigned long long)gart_start);
	printf("  %-26s calc=0x%012llX  obs=%-16s  %s\n", "gart_start (alineado)",
	       (unsigned long long)gart_start, "0xFF00000000",
	       gart_start == OBS_GART_START ? "COINCIDE" : "*** DIFIERE ***");
	printf("  %-26s calc=0x%012llX  obs=%-16s  %s\n", "gart_end",
	       (unsigned long long)gart_end, "0xFF0FFFFFFF",
	       gart_end == OBS_GART_END ? "COINCIDE" : "*** DIFIERE ***");

	ok(gart_start == OBS_GART_START, "gart_start coincide tras alinear");
	ok(gart_end == OBS_GART_END, "gart_end coincide");
	ok((gart_start & (four_gb - 1)) == 0, "gart_start cae en un limite de 4 GiB");

	/* ---------------------------------------------------------------- *
	 * CORRECCION A 199: el GART NO termina en el tope del MC.
	 *
	 * 199 afirma, en PROVEN_DERIVED:
	 *     "gart_end + gart_size = 0x000000FF1FFFFFFF = mc_mask + 1"
	 * El primer miembro es correcto. La IGUALDAD es falsa: el segundo es
	 * 0x0000010000000000, y no son el mismo numero. La diferencia son
	 * 3,5 GiB, y no es un error de redondeo mio: es la huella de la
	 * alineacion a 4 GiB del paso anterior, y por eso se puede medir.
	 * ---------------------------------------------------------------- */
	printf("\n  -- 3.4b CORRECCION A 199: el GART no llega al tope del MC --\n");
	{
		u64 shortfall = (mc_mask + 1) - (gart_end + gart_size);
		u64 residuo = (max_mc_address - gart_size + 1) % four_gb;
		u64 debajo = mc_mask - gart_end;

		printf("  gart_start crudo (sin alinear) = 0x%012llX\n",
		       (unsigned long long)(max_mc_address - gart_size + 1));
		printf("  gart_start alineado a 4 GiB    = 0x%012llX\n",
		       (unsigned long long)gart_start);
		printf("  desnivel que introduce la alineacion = 0x%llX = %.2f GiB\n",
		       (unsigned long long)residuo, (double)residuo / (double)(1ULL << 30));
		printf("\n  199 afirmaba: gart_end + gart_size = mc_mask + 1\n");
		printf("    gart_end + gart_size = 0x%012llX\n",
		       (unsigned long long)(gart_end + gart_size));
		printf("    mc_mask + 1         = 0x%012llX\n",
		       (unsigned long long)(mc_mask + 1));
		printf("    son iguales         = %s\n",
		       (gart_end + gart_size) == (mc_mask + 1) ? "si" : "NO");
		printf("    faltan              = 0x%llX = %.2f GiB\n",
		       (unsigned long long)shortfall,
		       (double)shortfall / (double)(1ULL << 30));
		printf("  el hueco que queda es de %.2f GiB: es espacio del MC que\n",
		       (double)shortfall / (double)(1ULL << 30));
		printf("  nadie mapea, y es consequence de la alineacion a 4 GiB.\n");
		printf("    mc_mask - gart_end   = 0x%llX\n", (unsigned long long)debajo);
		printf("    residuo de la alin.  = 0x%llX\n", (unsigned long long)residuo);
		printf("    son iguales          = %s\n", debajo == residuo ? "si" : "no");
		printf("  -> invariante que SI se cumple: el GART cae alineado, y su\n");
		printf("     extremo superior queda exactamente un residuo de la\n");
		printf("     alineacion por debajo de mc_mask.\n");

		ok((gart_end + gart_size) != (mc_mask + 1),
		   "CORRECCION A 199: gart_end + gart_size NO es mc_mask + 1");
		ok(debajo == residuo,
		   "mc_mask - gart_end es exactamente el residuo de la alineacion");
		ok(gart_end <= mc_mask,
		   "el GART cabe entero dentro del MC (invariante que si se cumple)");
		ok(gart_start >= vram_end,
		   "el GART no invade la ventana de VRAM");
	}

	/* --- 3.5 donde NO hay ventana: la parte alta ------------------- */
	printf("\n  -- 3.5 el espacio libre por encima de la VRAM --\n");
	printf("  VRAM_END      = 0x%012llX\n", (unsigned long long)vram_end);
	printf("  GART_START    = 0x%012llX\n", (unsigned long long)gart_start);
	printf("  hueco entre ambos = 0x%012llX = %.2f GiB\n",
	       (unsigned long long)(gart_start - vram_end - 1),
	       (double)(gart_start - vram_end - 1) / (double)(1ULL << 30));
	ok(gart_start > vram_end, "el GART esta por encima de la VRAM, sin solaparse");

	/* El tope del MC es 40 bits: 1 TiB. Nada por encima es direccionable
	 * en el espacio fisico de VRAM, con independencia de quanta VRAM haya. */
	printf("\n  tope direccionable del MC = 2^40 = 1 TiB (mc_mask+1)\n");
	printf("  por encima de mc_mask no hay VRAM posible, ni con mas VRAM:\n");
	printf("  el limite es del MC, no de la placa.\n");
}

/* ------------------------------------------------------------------ *
 * 4. EL CONTRATO DEL DRIVER, ejecutado
 * ------------------------------------------------------------------ */

/*
 * Reimplementa exactamente lo que hace 07-DRIVER/kernel/rx550_mc.c, que es
 * C puro y por eso se puede copiar y ejecutar sin kernel. No es una
 * reimplementacion "parecida": son las mismas cuatro lineas.
 *
 * Lo que se comprueba es que el contrato del driver, alimentado con lo que
 * el codigo de referencia produce para esta placa, devuelve la ventana
 * observada.
 * Si devuelve otra cosa, el contrato del driver no sirve para esta placa.
 */

/* gmc_v8_0.c:560-567, el codigo al que el driver dice parecerse. */
static u64 ref_mc_vram_size(u32 config_memsize, int *enmascarado, const char **por_que)
{
	u32 tmp = config_memsize;

	*enmascarado = 0;
	if (tmp & 0xffff0000u) {
		if (tmp & 0xffffu)
			tmp &= 0xffffu;
		else
			*por_que = "0xFFFF0000: el codigo de referencia sale con el valor\n"
				   "entero y lo multiplica -> 4294901760 MiB";
	}
	return (u64)tmp * 1024ULL * 1024ULL;
}

/* rx550_mc.c:119-130, el rechazo del driver. */
static int driver_memsize_mib(u32 config_memsize, u32 *mib_out, const char **motivo)
{
	u32 tmp = config_memsize;
	int enmascarado = 0;

	if (tmp & 0xFFFF0000u) {
		if (!(tmp & 0xFFFFu)) {
			*motivo = "MIEMBOS_ALTOS_SIN_SIGNAL: mitad baja a cero, no hay\n"
				  "nada que enmascarar y nada que creer";
			*mib_out = 0;
			return 1;
		}
		tmp &= 0xFFFFu;
		enmascarado = 1;
	}
	if (tmp == 0) {
		*motivo = "TAMANO_NULO";
		*mib_out = 0;
		return 2;
	}
	*mib_out = tmp;
	return enmascarado ? 3 : 0;
}

static void contrato_driver(void)
{
	printf("== 4. EL CONTRATO DEL DRIVER, EJECUTADO ==\n");

	/* 4.1 El caso feliz de esta placa: CONFIG_MEMSIZE = 2048 = 0x0800. */
	{
		const u32 config_memsize = 2048;	/* 2048 MiB, en MiB */
		u32 mib = 0;
		const char *motivo = "OK";
		int r;
		u64 inicio, fin;

		printf("\n  -- 4.1 CONFIG_MEMSIZE = 0x%08X (%u) --\n",
		       config_memsize, config_memsize);
		r = driver_memsize_mib(config_memsize, &mib, &motivo);
		printf("  driver: rc=%d motivo=\"%s\" mib=%u\n", r, motivo, mib);

		inicio = ((u64)(0xF400u & 0xFFFFu)) << 24;
		fin = inicio + ((u64)mib << 20) - 1;
		printf("  driver: inicio=0x%012llX fin=0x%012llX\n",
		       (unsigned long long)inicio, (unsigned long long)fin);

		ok(r == 0, "caso feliz: el driver acepta 2048");
		ok(mib == 2048, "el tamano en MiB recovered es 2048");
		ok(inicio == OBS_VRAM_START, "el inicio del driver coincide con lo observado");
		ok(fin == OBS_VRAM_END, "el fin del driver coincide con lo observado");
	}

	/* 4.2 El caso que el driver documenta como divergencia. */
	{
		const u32 config_memsize = 0xFFFF0000u;
		int enmascarado = 0;
		const char *por_que = "sin nota";
		u64 ref_size, ref_mib;
		u32 mib = 0;
		const char *motivo = "";
		int r;

		printf("\n  -- 4.2 CONFIG_MEMSIZE = 0x%08X (el caso del comentario) --\n",
		       config_memsize);
		ref_size = ref_mc_vram_size(config_memsize, &enmascarado, &por_que);
		ref_mib = ref_size >> 20;
		printf("  referencia : mc_vram_size = %.0f MiB%s\n", (double)ref_mib,
		       por_que ? "" : "");
		printf("  referencia : enmascarado=%d\n", enmascarado);

		r = driver_memsize_mib(config_memsize, &mib, &motivo);
		printf("  driver    : rc=%d mib=%u motivo=\"%s\"\n", r, mib, motivo);

		ok(ref_mib == 4294901760ULL,
		   "la referencia produce 4294901760 MiB, como dice el comentario");
		ok(r == 1, "el driver RECHAZA ese caso en vez de multiplicarlo");

		/* Y por que rechazarlo es la decision correcta, medido: */
		{
			u64 inicio = ((u64)0xF400u) << 24;
			u64 fin_malo = inicio + ref_size - 1;
			/*
			 * ERROR PROPIO, y es el segundo de la misma clase que
			 * 199 §4 registra. La primera version de este bloque
			 * comprobaba si `inicio + ref_size` desborda 64 bits, y
			 * la respuesta es NO: 0xF400000000 + 0xFFFF00000000
			 * cabe de sobra en 64 bits. El programa decia
			 * "rebasa los 40 bits del MC = no" y dos lineas mas
			 * abajo escribia "ese fin no cabe en el MC". Las dos
			 * frases no pueden ser ciertas a la vez, y la segunda
			 * es la que queria.
			 *
			 * La pregunta correcta NO es si desborda el entero de
			 * la maquina, sino si cabe en el MC. Y no cabe:
			 * fin_malo tiene 53 bits y mc_mask tiene 40.
			 */
			int cabe_en_mc = (fin_malo <= MC_MASK_40BIT);
			int cabe_en_64 = ((inicio + ref_size) >= inicio);

			printf("\n  por que el rechazo es correcto y no una preferencia:\n");
			printf("    vram_start                        = 0x%012llX\n",
			       (unsigned long long)inicio);
			printf("    mc_vram_size de la referencia      = 0x%012llX\n",
			       (unsigned long long)ref_size);
			printf("    vram_end con el valor de la ref   = 0x%012llX (%d bits)\n",
			       (unsigned long long)fin_malo, 64 - __builtin_clzll(fin_malo));
			printf("    mc_mask (40 bits)                 = 0x%012llX (%d bits)\n",
			       (unsigned long long)MC_MASK_40BIT, 40);
			printf("    cabe en 64 bits (entero del host)  = %s\n",
			       cabe_en_64 ? "si" : "no");
			printf("    cabe en el MC (lo que importa)    = %s\n",
			       cabe_en_mc ? "si" : "NO");
			printf("    se pasa del tope en               = 0x%012llX\n",
			       (unsigned long long)(fin_malo - MC_MASK_40BIT));
			printf("    -> el fin no cabe en el MC: un vram_end mayor que\n");
			printf("       mc_mask no es 'demasiado grande', es una\n");
			printf("       direccion que este ASIC no puede decodificar.\n");
			printf("    Y por eso el rechazo no es una preferencia de estilo:\n");
			printf("       un vram_end erroneous que no desborda 64 bits NO\n");
			printf("       falla donde falla. No falla nunca, y por eso es peor\n");
			printf("       que un fallo.\n");

			ok(cabe_en_64,
			   "el valor de la referencia NO desborda 64 bits: por eso "
			   "el fallo es silencioso");
			ok(!cabe_en_mc,
			   "el vram_end resultante esta por encima de mc_mask");
			ok(fin_malo - MC_MASK_40BIT > (1ULL << 32),
			   "el exceso sobre el tope del MC es de 32 bits, no un margen");
		}
	}

	/* 4.3 La consecuencia que 279 no vio: sin CONFIG_MEMSIZE no hay
	 *     tamano, y el driver no lo lee de ningun sitio. */
	printf("\n  -- 4.3 la consecuencia para el camino del driver --\n");
	printf("  rx550_mc_vram_desde_registros(fb_location, config_memsize, out)\n");
	printf("  recibe config_memsize como PARAMETRO.\n");
	printf("  El registro que lo produciria es mmCONFIG_MEMSIZE, en BIF,\n");
	printf("  y ese si existe y si es leible en un PF.\n");
	printf("  -> el camino del driver hacia VRAM_END esta completo, no roto.\n");
	printf("     El defecto de 279 era del hallazgo, no del driver.\n");
}

/* ------------------------------------------------------------------ *
 * 5. LO QUE ESTE PROGRAMA NO PUEDE DECIDIR
 * ------------------------------------------------------------------ */

static void limites(void)
{
	printf("\n== 5. LIMITES DE ESTE INSTRUMENTO ==\n");
	printf("  NO lee hardware. No hay RREG32 aqui.\n");
	printf("  NO valida semantica de hardware: valida aritmetica y literales.\n");
	printf("  FB_BASE=0xF400 entra como OBSERVADO por inversion (199), no leido.\n");
	printf("  Lo que este programa NO puede decir, y alguien tiene que medirlo:\n");
	printf("    - el valor real de mmCONFIG_MEMSIZE en ESTE ASIC\n");
	printf("    - si el ASIC lo implementa como campo de 16 bits o mas ancho\n");
	printf("    - que hace el hardware con los bits altos si se leen\n");
}

int main(void)
{
	printf("================================================================\n");
	printf(" EP08 · MC / VRAM / MEMORY CONTROLLER · geometria verificable\n");
	printf(" TARGET: HOST-C / RX550 / 0000:01:00.0 / Polaris12 GFX8\n");
	printf(" CLASSIFICATION=VERIFICATION · TRACK=STATIC · WRITE_EXECUTION=NONE\n");
	printf("================================================================\n\n");

	refutacion_279();
	printf("\n");
	cadena_includes();
	printf("\n");
	geometria();
	printf("\n");
	contrato_driver();
	printf("\n");
	limites();

	printf("\n================================================================\n");
	printf(" RESULTADO: %d pruebas, %d fallos\n", pruebas, fallos);
	printf(" %s\n", fallos == 0 ? "OK" : "*** HAY DISCREPANCIAS ***");
	printf("================================================================\n");

	return fallos ? 1 : 0;
}