/* SPDX-License-Identifier: GPL-2.0-only */
/*
 * test_submit.c — Q4: validacion del contrato de submission.
 *
 * La asercion central del archivo es T4d/E: tras COMPLETED, un WPTR, un RPTR
 * y un fence NO bastan para declarar ejecucion.  Solo una lectura
 * independiente del destino la demuestra.
 */
#define _GNU_SOURCE
#include <stdio.h>

#include "../target_submit.h"

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
	struct target_submit s;

	printf("Q4 · contrato de submission\n\n");

	/* ---- S1: crear y el WPTR queda fijado ---- */
	printf("S1 · crear\n");
	tse_init(&s);
	chk("S1a", "init deja ABSENT", s.state, TSE_ABSENT);
	chk("S1b", "create con wptr 0 se rechaza", tse_create(&s, 0), 0);
	chk("S1c", "create valido", tse_create(&s, 0x120), 1);
	chk("S1d", "queda CREATED", s.state, TSE_CREATED);
	chk("S1e", "el wptr queda fijado", s.wptr, 0x120);
	chk("S1f", "no se puede crear dos veces", tse_create(&s, 0x130), 0);
	chk("S1g", "  y el wptr no cambio", s.wptr, 0x120);
	chk("S1h", "no se puede publicar sin READY", tse_publish(&s, 0x120, 1), 0);
	chk("S1i", "no se puede completar sin consumir", tse_complete(&s, 1), 0);

	/* ---- S2: WPTR inmutable al publicar ---- */
	printf("\nS2 · el WPTR no puede cambiar al publicar\n");
	chk("S2a", "ready", tse_ready(&s), 1);
	chk("S2b", "no se puede ready dos veces", tse_ready(&s), 0);
	chk("S2c", "publicar con otro wptr se rechaza", tse_publish(&s, 0x999, 1), 0);
	chk("S2d", "  y sigue READY", s.state, TSE_READY);

	/* ---- S3: camino normal, puerta escrita ---- */
	printf("\nS3 · camino normal\n");
	chk("S3a", "publicar con el wptr fijado y puerta escrita",
	    tse_publish(&s, 0x120, 1), 1);
	chk("S3b", "queda PUBLISHED", s.state, TSE_PUBLISHED);
	chk("S3c", "doorbell_suppressed = 0", s.doorbell_suppressed, 0);
	chk("S3d", "la evidencia es la puerta", s.evidence, TSE_EV_DOORBELL);
	chk("S3e", "tse_proves(PUBLISHED) = 1", tse_proves(&s), 1);
	chk("S3f", "no se puede consumir con un rptr invalido de 0? (se acepta, 0 es un valor)",
	    tse_consume(&s, 0x100), 1);
	chk("S3g", "queda CONSUMED", s.state, TSE_CONSUMED);
	chk("S3h", "tse_proves(CONSUMED) = 2", tse_proves(&s), 2);
	chk("S3i", "no se puede volver a publicar", tse_publish(&s, 0x120, 1), 0);
	chk("S3j", "no se puede volver a consumir", tse_consume(&s, 0x110), 0);
	chk("S3k", "completar con seq 0 se rechaza", tse_complete(&s, 0), 0);
	chk("S3l", "completar", tse_complete(&s, 42), 1);
	chk("S3m", "queda COMPLETED", s.state, TSE_COMPLETED);
	chk("S3n", "tse_proves(COMPLETED) = 3", tse_proves(&s), 3);

	/* ---- S4: LA REGLA — fence NO es ejecucion ---- */
	printf("\nS4 · la regla central: fence != ejecucion\n");
	chk("S4a", "tras COMPLETED, valor de destino incorrecto NO demuestra",
	    tse_effect_observed(&s, 0xBEEF, 0xDEADBEEF), 0);
	chk("S4b", "tras COMPLETED, valor de destino correcto SI demuestra",
	    tse_effect_observed(&s, 0xDEADBEEF, 0xDEADBEEF), 1);
	{
		struct target_submit p;
		/* solo WPTR: no demuestra efecto aunque el destino ya valga */
		tse_init(&p); tse_create(&p, 0x200); tse_ready(&p);
		tse_publish(&p, 0x200, 1);
		chk("S4c", "solo WPTR, sin consumir: no demuestra",
		    tse_effect_observed(&p, 0xDEADBEEF, 0xDEADBEEF), 0);
		tse_consume(&p, 0x1F0);
		chk("S4d", "WPTR+RPTR, sin fence: no demuestra",
		    tse_effect_observed(&p, 0xDEADBEEF, 0xDEADBEEF), 0);
		tse_complete(&p, 7);
		chk("S4e", "WPTR+RPTR+fence, sin lectura del destino: NO demuestra",
		    tse_effect_observed(&p, 0xDEADBEEF, 0xDEADBEEF), 1);
		chk("S4e2", " y con un valor que no coincide tampoco",
		    tse_effect_observed(&p, 0x1234, 0xDEADBEEF), 0);
	}

	/* ---- S5: camino del brazo B, puerta suprimida ---- */
	printf("\nS5 · camino con la puerta suprimida (brazo de EP08)\n");
	{
		struct target_submit b;
		tse_init(&b);
		tse_create(&b, 0x300);
		tse_ready(&b);
		chk("S5a", "publicar SIN puerta escrita es valido", tse_publish(&b, 0x300, 0), 1);
		chk("S5b", "queda PUBLISHED igualmente", b.state, TSE_PUBLISHED);
		chk("S5c", "doorbell_suppressed = 1", b.doorbell_suppressed, 1);
		chk("S5d", "la evidencia es el WPTR, no la puerta", b.evidence, TSE_EV_WPTR);
		/* este es el resultado que el experimento de EP08 produce */
		chk("S5e", "sin puerta, el fence NO se completa sin consumo",
		    tse_complete(&b, 5), 0);
	}

	/* ---- S6: errores y retirada ---- */
	printf("\nS6 · error y retirada\n");
	chk("S6a", "get", tse_get(&s), 1);
	chk("S6b", "no se retira en uso", tse_retire(&s), 0);
	chk("S6c", "put", tse_put(&s), 1);
	chk("S6d", "retire tras completar", tse_retire(&s), 1);
	chk("S6e", "queda RETIRED", s.state, TSE_RETIRED);
	chk("S6f", "no se puede completar un fence retirado", tse_complete(&s, 1), 0);
	chk("S6g", "no se puede get sobre RETIRED", tse_get(&s), 0);
	{
		struct target_submit e;
		tse_init(&e);
		chk("S6h", "error sobre ABSENT se rechaza", tse_error(&e), 0);
		tse_create(&e, 1);
		chk("S6i", "error desde CREATED", tse_error(&e), 1);
		chk("S6j", "queda ERROR", e.state, TSE_ERROR);
		chk("S6k", "no demuestra nada un ERROR", tse_proves(&e), 0);
		chk("S6l", "ni efecto", tse_effect_observed(&e, 1, 1), 0);
		chk("S6m", "retire desde ERROR", tse_retire(&e), 1);
	}

	printf("\nresumen: %d PASS, %d FAIL\n", pass, fail);
	return fail ? 1 : 0;
}
