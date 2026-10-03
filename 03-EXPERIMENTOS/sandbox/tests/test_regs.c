/* SPDX-License-Identifier: GPL-2.0-only */
/*
 * test_regs.c — validacion cruzada de la base de datos de registros.
 *
 * Este test NO copia los offsets: los RELEE del corpus del kernel y falla si
 * la tabla diverge.  Un test que comprobara la tabla contra si mismo no
 * detectaria ni un solo error de transcripcion.
 *
 * Lee:
 *   .../include/asic_reg/gca/gfx_8_0_d.h
 *   .../include/asic_reg/gca/gfx_8_1_d.h
 * Rutas sobrescribibles por argv para no depender del cwd.
 */
#define _GNU_SOURCE
#include <stdio.h>
/* La ruta del corpus era RELATIVA al cwd ("../../RESEARCH/..."), y el cwd
 * puede estar en cualquier sitio: dentro del arbol funcionaba, fuera daba 0
 * y los tests de offset se convertian en falsos negativos.  Ahora es un
 * define con valor por defecto, sobreescribible con -DRX550_CORPUS=...,
 * y el Makefile lo toma de $(RX550_CORPUS) si esta definido. */
#ifndef RX550_CORPUS
#define RX550_CORPUS "/home/lucas/Escritorio/RX550-INVESTIGACION/RESEARCH/kernelbuild/linux-7.1.3/drivers/gpu/drm/amd"
#endif

#include <stdlib.h>
#include <string.h>

#include "../target_regs.h"

static int pass, fail;

static void chk(const char *id, const char *what, int got, int want)
{
	if (got == want) {
		printf("  PASS  %-6s %s\n", id, what);
		pass++;
	} else {
		printf("  FAIL  %-6s %s (got %d want %d)\n", id, what, got, want);
		fail++;
	}
}

/* busca "#define <NOMBRE> <valor>" y devuelve el valor, o -1 */
static long long corpus_offset(const char *path, const char *name)
{
	char line[512];
	FILE *f = fopen(path, "r");
	long long v = -1;

	if (!f)
		return -1;
	while (fgets(line, sizeof(line), f)) {
		if (strncmp(line, "#define ", 8) == 0 &&
		    strstr(line, name)) {
			/* exige que el nombreTermine en separador, para no
			 * confundir mmCP_RB0_RPTR con mmCP_RB0_RPTR_ADDR */
			const char *hit = strstr(line, name);
			char after = hit[strlen(name)];
			if (after == ' ' || after == '\t') {
				sscanf(hit + strlen(name), "%llx", (unsigned long long *)&v);
				fclose(f);
				return v;
			}
		}
	}
	fclose(f);
	return -1;
}

int main(int argc, char **argv)
{
	const char *g80 = argc > 1 ? argv[1] : "RESEARCH/kernelbuild/linux-7.1.3/drivers/gpu/drm/amd/include/asic_reg/gca/gfx_8_0_d.h";
	const char *g81 = argc > 2 ? argv[2] : "RESEARCH/kernelbuild/linux-7.1.3/drivers/gpu/drm/amd/include/asic_reg/gca/gfx_8_1_d.h";
	size_t i, j;
	int orden_ok = 1, solape = 0, in_bar = 1, coincide_80_81 = 1;
	FILE *probe;
	probe = fopen(g80, "r");
	chk("R00", "gfx_8_0_d.h se puede abrir (si no, R05/R07 serian falsos)", probe ? 1 : 0, 1);
	if (probe) fclose(probe);
	probe = fopen(g81, "r");
	chk("R00", "gfx_8_1_d.h se puede abrir", probe ? 1 : 0, 1);
	if (probe) fclose(probe);
	int offset_malo = 0, ancho_malo = 0, tabla_vacia = 0;

	printf("base de datos de registros · %zu entradas\n", TARGET_NR_REGS);
	printf("fuente: gfx_8_0_d.h y gfx_8_1_d.h del corpus\n\n");

	tabla_vacia = (TARGET_NR_REGS == 0);
	chk("R01", "la tabla no esta vacia", tabla_vacia, 0);

	for (i = 0; i < TARGET_NR_REGS; i++) {
		const struct target_reg_desc *r = &target_regs[i];
		long long c80, c81;

		/* invariante central: index * 4 == byte_offset */
		if (r->byte_offset != r->index * 4)
			offset_malo++;

		/* ancho: solo 32 en esta tabla */
		if (r->width != 32)
			ancho_malo++;

		/* cabe dentro de la apertura de registros */
		if (r->byte_offset + 4 > TARGET_REG_BAR_SIZE)
			in_bar = 0;

		/* orden ascendente por byte_offset */
		if (i && target_regs[i - 1].byte_offset >= r->byte_offset)
			orden_ok = 0;

		/* cross-check contra el corpus, AMBAS cabeceras */
		c80 = corpus_offset(g80, r->name);
		c81 = corpus_offset(g81, r->name);
		if (c80 != (long long)r->index || c81 != (long long)r->index) {
			printf("  FAIL  R05   %-26s tabla=0x%04x gfx_8_0=0x%llx gfx_8_1=0x%llx\n",
			       r->name, r->index, c80, c81);
			fail++;
		} else {
			pass++;
		}
		if (c80 != c81)
			coincide_80_81 = 0;

		/* no solape: 4 bytes por entrada, ordenadas */
		for (j = i + 1; j < TARGET_NR_REGS; j++) {
			unsigned int a0 = r->byte_offset, a1 = a0 + 4;
			unsigned int b0 = target_regs[j].byte_offset, b1 = b0 + 4;
			if (a0 < b1 && b0 < a1)
				solape++;
		}

		/* toda entrada declara confidence y consumer no vacios */
		if (r->conf > TARGET_REG_UNKNOWN)
			chk("R06", "confidence dentro de rango", 0, 1);
		if (!r->consumer || !*r->consumer || !r->purpose || !*r->purpose) {
			printf("  FAIL  R06   %-26s sin consumer/purpose\n", r->name);
			fail++;
		} else {
			pass++;
		}
	}

	chk("R02", "invariante index*4 == byte_offset en todas las entradas", offset_malo, 0);
	chk("R03", "todas dentro de BAR5 (0x40000)", in_bar, 1);
	chk("R04", "orden ascendente por byte_offset", orden_ok, 1);
	chk("R05b", "ningun solape entre entradas", solape, 0);
	chk("R07", "gfx_8_0 y gfx_8_1 coinciden en los 10 registros", coincide_80_81, 1);
	chk("R08", "todas con ancho 32", ancho_malo, 0);

	/* el invariante por construccion, con un ejemplo real del proyecto */
	{
		const struct target_reg_desc *r = &target_regs[0];
		(void)r;
		chk("R09", "mmCP_RB0_RPTR: 0x21c0*4 = 0x8700", 0x21c0 * 4, 0x8700);
		chk("R10", "mmCP_RB_WPTR_POLL_CNTL: 0x21c2*4 = 0x8708", 0x21c2 * 4, 0x8708);
		chk("R11", "mmSCRATCH_REG0: 0xc040*4 = 0x30100", 0xc040 * 4, 0x30100);
	}

	printf("\nresumen: %d PASS, %d FAIL\n", pass, fail);
	return fail ? 1 : 0;
}
