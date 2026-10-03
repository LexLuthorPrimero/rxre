/* SPDX-License-Identifier: GPL-2.0-only */
/*
 * test_fence.c — Q3: validacion del modelo de fence.
 *
 * Ejecuta la logica real de target_fence.h. No carga el modulo, no observa
 * la GPU, no espera ningun timeout de verdad: los timeouts del modelo son
 * transiciones puras, no esperas.
 */
#define _GNU_SOURCE
#include <stdio.h>

#include "../target_fence.h"

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

int main(void)
{
	struct target_fence f;

	printf("Q3 · modelo de fence\n\n");

	/* ---- F1: crear exige camino y timeout ---- */
	printf("F1 · creacion: el camino de senal es obligatorio\n");
	tfm_init(&f);
	chk("F1a", "init deja ABSENT", f.state, TFM_FENCE_ABSENT);
	chk("F1b", "crear sin camino se rechaza", tfm_create(&f, TFM_PATH_NONE, 1000), 0);
	chk("F1c", "crear con timeout 0 se rechaza", tfm_create(&f, TFM_PATH_RELEASE_MEM, 0), 0);
	chk("F1d", "crear con camino invalido se rechaza", tfm_create(&f, (enum target_fence_path)99, 1000), 0);
	chk("F1e", "  y sigue ABSENT tras los rechazos", f.state, TFM_FENCE_ABSENT);
	chk("F1f", "crear con RELEASE_MEM", tfm_create(&f, TFM_PATH_RELEASE_MEM, 1000), 1);
	chk("F1g", "queda CREATED", f.state, TFM_FENCE_CREATED);
	chk("F1h", "el camino queda registrado", f.path, TFM_PATH_RELEASE_MEM);
	chk("F1i", "no se puede crear dos veces", tfm_create(&f, TFM_PATH_EVENT_WRITE_EOP, 5), 0);
	chk("F1j", "  y el camino original no cambio", f.path, TFM_PATH_RELEASE_MEM);

	/* ---- F2: publicar y observar ---- */
	printf("\nF2 · publicar y observar\n");
	chk("F2a", "no se puede observar sin publicar", tfm_observe(&f, 1), 0);
	chk("F2b", "publicar", tfm_publish(&f, 7), 1);
	chk("F2c", "la secuencia queda fijada", f.seq, 7);
	chk("F2d", "no se puede publicar dos veces", tfm_publish(&f, 8), 0);
	chk("F2e", "  y la secuencia no cambio", f.seq, 7);
	chk("F2f", "observar una secuencia distinta se rechaza", tfm_observe(&f, 8), 0);
	chk("F2g", "  y sigue PUBLISHED", f.state, TFM_FENCE_PUBLISHED);
	chk("F2h", "observar la secuencia correcta", tfm_observe(&f, 7), 1);
	chk("F2i", "queda SIGNALLED", f.state, TFM_FENCE_SIGNALLED);
	chk("F2j", "es settled", tfm_settled(&f), 1);
	/* duplicar senalizacion: el rechazo lo da el estado, no una funcion aparte */
	chk("F2k", "doble senalizacion se rechaza", tfm_observe(&f, 7), 0);
	chk("F2l", "  el estado no se altera", f.state, TFM_FENCE_SIGNALLED);
	chk("F2m", "  y la secuencia observada sigue siendo la misma", f.observed, 7);

	/* ---- F3: timeout ---- */
	printf("\nF3 · timeout\n");
	tfm_init(&f);
	tfm_create(&f, TFM_PATH_EVENT_WRITE_EOP, 250);
	chk("F3a", "timeout antes de publicar se rechaza", tfm_timeout(&f), 0);
	tfm_publish(&f, 3);
	chk("F3b", "timeout tras publicar", tfm_timeout(&f), 1);
	chk("F3c", "queda TIMED_OUT", f.state, TFM_FENCE_TIMED_OUT);
	chk("F3d", "es settled", tfm_settled(&f), 1);
	chk("F3e", "no se puede observar despues del timeout", tfm_observe(&f, 3), 0);
	chk("F3f", "no se puede volver a caducar", tfm_timeout(&f), 0);

	/* ---- F4: transiciones invalidas ---- */
	printf("\nF4 · transiciones invalidas\n");
	tfm_init(&f);
	chk("F4a", "error sobre ABSENT se rechaza", tfm_error(&f), 0);
	chk("F4b", "get sobre ABSENT se rechaza", tfm_get(&f), 0);
	chk("F4c", "retire sobre ABSENT se rechaza", tfm_retire(&f), 0);
	tfm_create(&f, TFM_PATH_RELEASE_MEM, 10);
	chk("F4d", "retire sin crear secuencia se rechaza", tfm_retire(&f), 0);
	chk("F4e", "get sobre CREATED", tfm_get(&f), 1);
	chk("F4f", "retire en uso se rechaza", tfm_retire(&f), 0);
	chk("F4g", "put", tfm_put(&f), 1);
	chk("F4h", "put de mas se rechaza", tfm_put(&f), 0);

	/* ---- F5: monotonicidad de la secuencia ---- */
	printf("\nF5 · comparacion de secuencias (no es <)\n");
	chk("F5a", "8 va despues de 7", tfm_seq_after(8, 7), 1);
	chk("F5b", "7 NO va despues de 8", tfm_seq_after(7, 8), 0);
	chk("F5c", "iguales no van despues", tfm_seq_after(7, 7), 0);
	/* wraparound: 0 va despues de 0xFFFFFFFF en aritmetica modular */
	chk("F5d", "tras el wrap, 0 va despues de 0xFFFFFFFF",
	    tfm_seq_after(0, 0xFFFFFFFFu), 1);
	chk("F5e", "y 0xFFFFFFFF NO va despues de 0",
	    tfm_seq_after(0xFFFFFFFFu, 0), 0);
	/* el caso limite: diferencia exactamente media */
	chk("F5f", "diferencia de 2^31 no cuenta como despues",
	    tfm_seq_after(0x80000000u, 0), 0);
	chk("F5g", "diferencia de 2^31-1 si cuenta",
	    tfm_seq_after(0x7FFFFFFFu, 0), 1);

	/* ---- F6: retirada ---- */
	printf("\nF6 · retirada\n");
	tfm_init(&f);
	tfm_create(&f, TFM_PATH_RELEASE_MEM, 10);
	tfm_publish(&f, 11);
	tfm_observe(&f, 11);
	chk("F6a", "retire tras senalizar", tfm_retire(&f), 1);
	chk("F6b", "queda RETIRED", f.state, TFM_FENCE_RETIRED);
	chk("F6c", "no se puede senalizar un fence retirado", tfm_observe(&f, 11), 0);
	chk("F6d", "no se puede get sobre RETIRED", tfm_get(&f), 0);
	chk("F6e", "retire de nuevo se rechaza", tfm_retire(&f), 0);

	printf("\nresumen: %d PASS, %d FAIL\n", pass, fail);
	return fail ? 1 : 0;
}
