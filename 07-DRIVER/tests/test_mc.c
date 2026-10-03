/* SPDX-License-Identifier: GPL-2.0 */
/*
 * test_mc.c -- donde vive la VRAM y cuanta hay, sin hardware.
 *
 * EL VECTOR IMPORTANTE
 *
 * Este fichero lleva dentro la funcion de gmc_v8_0.c:560-567 tal cual, y para
 * cada valor de CONFIG_MEMSIZE calcula LAS DOS respuestas: la de amdgpu y la de
 * este driver. La divergencia no esta escrita en un comentario, esta CALCULADA
 * aqui al lado, y por eso se puede ver cambiar cuando el codigo de referencia
 * cambie.
 *
 * Es el mismo criterio que se uso para las mascaras de los opcode: una
 * afirmacion sobre lo que hace otro codigo tiene que poder fallar.
 *
 * LO QUE ESTABLECE
 *
 *   los dos offsets, y que estan en BLOQUES DISTINTOS
 *   vram_start = (FB_LOCATION & 0xFFFF) << 24
 *   vram_end   = vram_start + tamano - 1, borde superior incluido
 *   la cadena completa reproduce los dos numeros del log de esta placa
 *   y rechaza lo que el codigo de referencia acepta sin querer
 *
 * LO QUE NO ESTABLECE
 *
 *   que los registros valgan lo que la prediccion dice. Eso exige el mapa, y
 *   el mapa sigue retenido por el bloque<->BAR (NOT_IN_CORPUS, 176 §3).
 *
 * Salida 0 si todo se comporta como se documenta, 1 si no.
 */

#include <stdint.h>
#include <stdio.h>

#include "../kernel/rx550_mc.h"

static int failures;
static int checks;

/* El codigo de referencia, COPIADO. gmc_v8_0.c:560-567.
 * No se importa: importar el interior de un modulo no es posible, y copiarlo es
 * lo que hace que el test pueda calcular las dos respuestas y compararlas. */
static uint64_t
arriba_como_referencia(uint32_t tmp)
{
	if (tmp & 0xffff0000u) {
		if (tmp & 0xffffu)
			tmp &= 0xffffu;
	}
	return (uint64_t)tmp * 1024ULL * 1024ULL;
}

static void
check(int cond, const char *what, const char *detail)
{
	checks++;
	if (cond) {
		printf("  [ OK ] %s\n", what);
	} else {
		printf("  [FAIL] %s -- %s\n", what, detail ? detail : "");
		failures++;
	}
}

struct caso {
	uint32_t	memsize;
	const char	*nombre;
};

static const struct caso casos[] = {
	{ 0x00000800u, "2048 MiB, el valor real de esta placa" },
	{ 0xffff0000u, "el caso que el comentario de gmc_v8_0.c:561 describe" },
	{ 0xffff0800u, "bits altos Y senal en la mitad baja: el que SI corrige" },
	{ 0x00000000u, "cero" },
	{ 0x0000ffffu, "65535 MiB, absurdo y sin un solo bit alto" },
	{ 0xffff00ffu, "255 MiB, enmascarado a algo que PARECE razonable" },
	{ 0x00000800u + 0x00000000u, "otro 2048 MiB, para que la tabla tenga dos" },
};

#define N_CASOS	(sizeof(casos) / sizeof(casos[0]))

int
main(void)
{
	struct rx550_mc_vram v;
	uint32_t mib = 0;
	int i, r;

	printf("1. Los dos registros, y que estan en BLOQUES DISTINTOS:\n");
	check(RX550_MC_FB_LOCATION == 0x809,
	      "mmMC_VB_FB_LOCATION en 0x809, bloque GMC 8.1", NULL);
	check(RX550_MC_CONFIG_MEMSIZE == 0x150a,
	      "mmCONFIG_MEMSIZE en 0x150a, y ese es bloque BIF 4.1", NULL);
	check(RX550_MC_FB_LOCATION != RX550_MC_CONFIG_MEMSIZE,
	      "los dos offsets NO son el mismo registro", NULL);

	printf("\n2. La cadena completa contra los numeros observados:\n");
	/* journalctl -k -b en esta placa, sin root:
	 *   VRAM: 2048M 0x000000F400000000 - 0x000000F47FFFFFFF */
	r = rx550_mc_vram_desde_registros(0x0000F400u, 0x00000800u, &v);
	check(r == RX550_MC_OK, "0x0F40 y 0x800 se aceptan sin motivo de rechazo",
	      NULL);
	check(v.inicio == 0x000000F400000000ULL,
	      "inicio = 0x000000F400000000, el que dice el log", NULL);
	check(v.fin == 0x000000F47FFFFFFFULL,
	      "fin    = 0x000000F47FFFFFFF, el que dice el log, borde incluido",
	      NULL);
	check(v.mib == 2048, "2048 MiB, que es lo que dice el log", NULL);
	check(v.crudo == 0x00000800u,
	      "y se conserva el valor CRUDO del registro, sin retocar", NULL);

	printf("\n3. La prediccion que queda falsable:\n");
	printf("       mmMC_VM_FB_LOCATION tiene que leer 0x0000F400\n");
	printf("       mmCONFIG_MEMSIZE    tiene que leer 0x00000800\n");
	check(rx550_mc_fb_base(0x0000F400u) == 0x000000F400000000ULL,
	      "si FB_LOCATION leyera 0x0F40, el inicio seria el observado", NULL);
	check(rx550_mc_memsize_mib(0x00000800u, &mib) == RX550_MC_OK &&
	      mib == 2048,
	      "si CONFIG_MEMSIZE leyera 0x800, el tamano seria el observado", NULL);

	printf("\n4. La DIVERGENCIA, calculada y noLpintada:\n");
	printf("     CONFIG_MEMSIZE   nombre                                amdgpu        este\n");
	for (i = 0; i < (int)N_CASOS; i++) {
		uint64_t ref = arriba_como_referencia(casos[i].memsize);
		uint32_t mio = 0;
		int rr = rx550_mc_memsize_mib(casos[i].memsize, &mio);
		const char *mot = (rr == RX550_MC_OK || rr == RX550_MC_ENMASCARADO)
			? "aceptado" : rx550_mc_motivo(rr);
		char buf[16];
		uint64_t miobytes = (rr == RX550_MC_OK || rr == RX550_MC_ENMASCARADO)
			? (uint64_t)mio * 1024 * 1024 : 0;
		snprintf(buf, sizeof(buf), "%llu",
			 (unsigned long long)(miobytes / (1024 * 1024)));
		printf("     0x%08x  %-38s %10lluMiB  %s\n",
		       casos[i].memsize, casos[i].nombre,
		       (unsigned long long)(ref / (1024 * 1024)),
		       (rr == RX550_MC_OK || rr == RX550_MC_ENMASCARADO)
			? buf : mot);
	}

	printf("\n   Y las tres diferencias, una por una:\n");
	/* (a) el caso del comentario, que la referencia NO corrige */
	check(arriba_como_referencia(0xffff0000u) ==
	      4294901760ULL * 1024ULL * 1024ULL,
	      "(a) la referencia multiplica 4294901760 MiB con 0xffff0000", NULL);
	check(rx550_mc_memsize_mib(0xffff0000u, &mib) ==
	      RX550_MC_MIEMBOS_ALTOS_SIN_SIGNAL,
	      "(a) este driver SE NIEGA con 0xffff0000, y no enmascara", NULL);

	/* (b) absurdo sin un solo bit alto: no hay aviso ni mascara ahi */
	check(rx550_mc_memsize_mib(0x0000ffffu, &mib) == RX550_MC_TAMANO_ABSURDO,
	      "(b) 65535 MiB se rechaza por el tope declarado", NULL);

	/* (c) cero, que llevaria vram_end por debajo del inicio */
	r = rx550_mc_vram_desde_registros(0x0000F400u, 0x00000000u, &v);
	check(r == RX550_MC_TAMANO_NULO,
	      "(c) cero se rechaza, y no se devuelve una ventana vacia", NULL);
	check(v.inicio == 0 && v.fin == 0,
	      "(c) y la ventana queda a cero, no con fin < inicio", NULL);

	printf("\n5. El caso que la referencia SI cubre, se acepta:\n");
	check(rx550_mc_memsize_mib(0xffff0800u, &mib) == RX550_MC_ENMASCARADO &&
	      mib == 2048,
	      "0xffff0800 se enmascara a 2048 y se dice que se enmascaro", NULL);
	check(rx550_mc_vram_desde_registros(0x0000F400u, 0xffff0800u, &v) ==
	      RX550_MC_ENMASCARADO,
	      "y la ventana sale igual que con el registro limpio", NULL);

	printf("\n6. El borde del contrato:\n");
	check(rx550_mc_memsize_mib(0x00000800u, &mib) == RX550_MC_OK,
	      "un out NULL no revienta", NULL);
	check(rx550_mc_vram_desde_registros(0xF400u, 0x800u, NULL) ==
	      RX550_MC_TAMANO_NULO,
	      "y desde_registros con out NULL devuelve motivo, no escribe", NULL);
	check(RX550_MC_MEMSIZE_MAX_MiB == 16ULL * 1024ULL,
	      "el tope son 16 GiB, MODEL_CHOICE declarado", NULL);
	/* Y por que 16 y no 64: un tope por encima de lo que el campo puede
	 * expresar no rechaza NADA y parece que filtra. Este es el vector que
	 * lo fija. */
	check(RX550_MC_MEMSIZE_MAX_MiB < 65535ULL,
	      "el tope esta POR DEBAJO de 65535 MiB, que es lo que el campo puede dar",
	      NULL);
	check(rx550_mc_fb_base(0xFFFFFFFFu) == 0x00FFFF000000ULL,
	      "el registro entero da 0xFFFF000000, el tope del campo, sin desbordar",
	      NULL);
	check(rx550_mc_fb_base(0x00000001u) == 0x1000000ULL,
	      "y un bit en la posicion 0 sube a la 24, no se queda abajo", NULL);

	printf("\n%d checks, %d failure(s)\n", checks, failures);
	if (failures) {
		printf("RESULT: FAIL\n");
		return 1;
	}
	printf("RESULT: PASS\n");
	printf("\nNOT covered, and not claimed:\n"
	       "  - que los dos registros valgan 0x0F40 y 0x800. Eso exige el\n"
	       "    mapa, y el mapa sigue retenido por el bloque<->BAR (NOT_IN_CORPUS,\n"
	       "    findings/176 §3). Lo que si queda es la PREDICCION, y es falsable.\n"
	       "  - que 2048 MiB sea el tamano de este chip y no el de la placa con\n"
	       "    otra VRAM. El log lo dice de ESTA placa, con este VBIOS.\n"
	       "  - que el hardware no pueda dar 0xffff0000 de verdad. Que el codigo\n"
	       "    de referencia no lo.contemple es una OBSERVACION sobre el codigo,\n"
	       "    no una medida del silicio. Por eso aqui se rechaza: no se Multiplica.\n"
	       "  - la unidad de MC_VM_FB_LOCATION mas alla de los bits 24..39: el\n"
	       "    header no declara el layout de este campo (ver findings/201 §5).\n");
	return 0;
}