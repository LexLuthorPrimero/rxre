/* SPDX-License-Identifier: GPL-2.0 */
/*
 * pm4decode.c - decodificador de IB de GFX8, para validar el codificador propio.
 *
 * POR QUE EXISTE
 *
 * Hay dos validadores y los dos comprueban lo MISMO: que el dword de cabecera
 * de cada paquete sea igual a una constante calculada a mano.
 *
 *   tools/rx550pm4val.c   1025 lineas, compara cabeceras
 *   07-DRIVER/tests/     835 lineas, compara cabeceras
 *   07-DRIVER/kernel/   1053 lineas, el codificador
 *
 * Ninguno lee la IB de vuelta. Eso deja sin cubrir justo la clase de fallo que
 * un validador de cabeceras no puede ver:
 *
 *   - un paquete que declara count=N y al que se le escriben N+1 dwords;
 *   - una IB que el codificador trunca en silencio por falta de sitio, y el
 *     test sigue verde porque solo mira lo que si se escribio;
 *   - argumentos en orden equivocado, con la cabecera correcta;
 *   - dwords de mas al final, que ningun emisor declara.
 *
 * El decodificador no necesita la especificacion de GFX8, que no esta
 * publicada (findings/033-pm4-spec-gfx8-no-existe-y-el-encuadre.md). Necesita
 * solo el FORMATO DE CABECERA, que esta medido en el binario y es el que
 * findings/038-validador-flujo-y-regla-del-count.md fija como count + 2.
 *
 *     bits 31:30   headerType   3 = PACKET_TYPE3
 *     bits 29:26   count        dwords de payload
 *     bits 15:8    opcode       solo en PACKET_TYPE3
 *     bit  1       compute      forma alterna de PACKET3
 *     total        1 + count + 1 = count + 2
 *
 * COMPROBACIONES, y por que cada una existe
 *
 *   COUNT_IMPOSIBLE    un count mayor que lo que queda es truncamiento, y un
 *                      PACKET2 con count impar no tiene longitud entera.
 *   SIN_PAQUETE        un dword cuyo headerType no es 2 ni 3.
 *   CONSUMO_EXACTO     RED DE SEGURIDAD, INALCANZABLE POR CONSTRUCCION.
 *
 * Sobre CONSUMO_EXACTO: con total = count + 2, todo dword de una IB es
 * cabecera o payload, y no existe el estado "sobran dwords". Un paquete que
 * declara de menos no deja un sobrante: deja que el siguiente dword se
 * interprete como cabecera, y eso sale SIN_PAQUETE o COUNT_IMPOSIBLE. Lo
 * demuestra esta comprobacion lo demuestra el vector [4] de este selftest:
 * "sobran" con 0xDEADBEEF da COUNT_IMPOSIBLE, porque 0xD = 1101 y sus dos bits
 * altos son 11, o sea headerType 3.
 *
 * Se conserva la comprobacion porque es una asercion de una linea y porque
 * si alguna vez fuese alcanzable seria un fallo grave. Pero esta en la
 * documentacion como lo que es -- una red -- y no como una deteccion, porque
 * una lista de comprobaciones que dice mas de las que existen enseña a confiar
 * en comprobaciones que no estan.
 *
 * LO QUE NO HACE
 *
 * No comprueba la SEMANTICA de los argumentos: que un WRITE_DATA lleve el
 * numero absoluto y no el offset, o que un VM_FLUSH tenga el orden correcto.
 * Eso no lo sabe un decodificador de cabeceras, y pretenderlo seria
 * exactamente el "implementar una semantica porque tiene nombre conocido" que
 * AGENTS.md 748-760 prohibe. Para eso estan las marcas EVIDENCIA del codigo.
 *
 * CODIGOS DE SALIDA
 *
 *   0  IB bien formada
 *   1  IB mal formada, con el motivo y la palabra clave de la ofensa
 *   2  uso incorrecto
 */
#include <stdio.h>
#include <stdlib.h>
#include <string.h>
#include <stdint.h>

#include "pm4decode.h"

#define PM4_TYPE0	0u
#define PM4_TYPE1	1u
#define PM4_TYPE2	2u
#define PM4_TYPE3	3u

#define PM4_HDR_TYPE(d)		(((uint32_t)(d)) >> 30)
#define PM4_HDR_COUNT(d)	((((uint32_t)(d)) >> 16) & 0x3Fu)
#define PM4_HDR_OPCODE(d)	((((uint32_t)(d)) >> 8) & 0xFFu)
#define PM4_HDR_COMPUTE(d)	((((uint32_t)(d)) >> 1) & 1u)

/* longitud total de un paquete: cabecera + count + 1 (el +1 es el propio
 * campo de longitud, que va dentro de count).
 * 038-validador-flujo-y-regla-del-count.md:34 lo fija. */
#define PM4_DWORDS(count)	((unsigned)(count) + 2u)

/* enum pm4_defecto, struct pm4_pkt y struct pm4_resultado viven en
 * pm4decode.h desde que las pruebas del driver los necesitan. Declararlos
 * tambien aqui era una redeclaracion que hacia fallar el build entero,
 * y un build que falla no lo detecta ningun test: se limita a no
 * ejecutarse y el binario viejo sigue en su sitio. */



/*
 * Decodifica buf[0..n_dw) en out[0..max_pkt).
 *
 * Devuelve 0 si la IB es bien formada, 1 si no. Rellena res siempre, y en el
 * caso de defecto res->motivo dice cual y res->offset donde.
 */
int
pm4_decode(const uint32_t *buf, unsigned n_dw, struct pm4_pkt *out,
	   unsigned max_pkt, struct pm4_resultado *res)
{
	unsigned i = 0, k = 0;

	memset(res, 0, sizeof(*res));
	res->defecto = PM4_OK;

	if (out == NULL || max_pkt == 0 || (buf == NULL && n_dw)) {
		snprintf(res->motivo, sizeof(res->motivo),
			 "argumentos invalidos: buf=%p out=%p max=%u",
			 (const void *)buf, (void *)out, max_pkt);
		res->defecto = PM4_SIN_PAQUETE;
		return 1;
	}

	while (i < n_dw) {
		uint32_t hdr = buf[i];
		unsigned tipo = PM4_HDR_TYPE(hdr);
		unsigned count = PM4_HDR_COUNT(hdr);
		unsigned total;

		if (k >= max_pkt) {
			snprintf(res->motivo, sizeof(res->motivo),
				 "se agotaron los %u huecos de salida en el dword %u",
				 max_pkt, i);
			res->defecto = PM4_SIN_PAQUETE;
			res->offset = i;
			res->n_pkt = k;
			return 1;
		}

		/*
		 * Un PACKET2 cuenta en bytes, no en dwords. El driver propio no
		 * emite ninguno, y si apareciera con un numero impar la longitud
		 * en dwords no seria entera: eso se marca en vez de redondear.
		 */
		if (tipo == PM4_TYPE2) {
			if (count & 1u) {
				snprintf(res->motivo, sizeof(res->motivo),
					 "PACKET2 con count impar (%u) en el dword %u: "
					 "la longitud en bytes no es multiplo de 4",
					 count, i);
				res->defecto = PM4_COUNT_IMPOSIBLE;
				res->offset = i;
				res->n_pkt = k;
				return 1;
			}
			total = count + 2u;
		} else {
			total = PM4_DWORDS(count);
		}

		/*
		 * PRIMERO la validez del tipo, y despues el truncamiento. En el
		 * orden contrario, un dword que no es cabecera ninguna se
		 * diagnostica como "declara 2 dwords y solo queda 1", que es
		 * verdad pero no ayuda: la pregunta util es por que ese dword
		 * no es una cabecera. El selftest lo detecto con el vector [5].
		 */
		if (tipo != PM4_TYPE2 && tipo != PM4_TYPE3) {
			/*
			 * No es PACKET2 ni PACKET3. La causa legitima es que
			 * sea un paquete SDMA, que lleva cabecera propia
			 * (SDMA_PKT_HEADER_OP) y que rx550_ring_submit()
			 * emite. Decir "ningun emisor escribe esto" seria
			 * una acusacion falsa: el emisor existe y lo hace a
			 * proposito, solo que con otro formato de cabecera.
			 *
			 * Por eso NO se intenta adivinar cual es: se dice que
			 * aqui termina lo que esta herramienta sabe, y quien
			 * siga tiene que decidir si lo cubre.
			 */
			/*
			 * El byte bajo SI se puede leer con certeza: en la cabecera
			 * SDMA generica el campo op es op_mask 0x000000FF con
			 * op_shift 0 (tonga_sdma_pkt_open.h:55-56), el mismo para
			 * todos los tipos de paquete SDMA. Eso no es interpretar
			 * el paquete, es leer un campo que la cabecera declara
			 * uniforme, y convierte "headerType=0" en algo accionable.
			 */
			snprintf(res->motivo, sizeof(res->motivo),
				 "dword %u: headerType=%u, no es PACKET2 ni PACKET3. "
				 "Lo legitimo aqui es un paquete SDMA (cabecera "
				 "SDMA_PKT_HEADER_OP), que este decodificador NO "
				 "cubre. op=0x%02x (%u), leido del byte bajo con "
				 "op_mask 0x000000FF / op_shift 0",
				 i, tipo, (unsigned)(buf[i] & 0xFFu),
				 (unsigned)(buf[i] & 0xFFu));
			res->defecto = PM4_NO_ES_PM4;
			res->offset = i;
			res->n_pkt = k;	/* lo que SI se decodifico antes */
			return 1;
		}

		/* TRUNCAMIENTO: el paquete dice mas de lo que queda. */
		if (total > n_dw - i) {
			snprintf(res->motivo, sizeof(res->motivo),
				 "paquete en el dword %u declara %u dwords y solo "
				 "quedan %u", i, total, n_dw - i);
			res->defecto = PM4_COUNT_IMPOSIBLE;
			res->offset = i;
			return 1;
		}

		out[k].offset	= i;
		out[k].n_dw	= total;
		out[k].tipo	= tipo;
		out[k].count	= count;
		out[k].compute	= PM4_HDR_COMPUTE(hdr);
		out[k].opcode	= (tipo == PM4_TYPE3) ?
					PM4_HDR_OPCODE(hdr) : 0u;
		{
			unsigned c = total < 8u ? total : 8u;
			unsigned j;
			for (j = 0; j < c; j++)
				out[k].dw[j] = buf[i + j];
		}

		k++;
		i += total;
	}

	res->n_pkt = k;

	/* lo decodificado tiene que acabar donde acaba la IB */
	if (i != n_dw) {
		snprintf(res->motivo, sizeof(res->motivo),
			 "la decodificacion se paro en %u y la IB tiene %u: "
			 "sobran dwords sin paquete que los cubra",
			 i, n_dw);
		res->defecto = PM4_CONSUMO_EXACTO;
		res->offset = i;
		return 1;
	}

	return 0;
}

/* ------------------------------------------------------------------ */
/* Nombre del opcode, para que el fallo sea legible. No es una tabla de */
/* semantica: son los opcodes que el driver propio emite, leidos de su */
/* propia tabla, y lo que no esta se imprime en hexadecimal.           */
/* ------------------------------------------------------------------ */
/*
 * Nombre del opcode. TABLA TRANSCRITA DE drivers/gpu/drm/amd/amdgpu/sid.h, no
 * escrita de memoria.
 *
 * La primera version de esta tabla estaba hecha de memoria y tenía SIETE
 * entradas equivocadas. Lo encontró el test, no la lectura:
 *
 *     puesto por mi   real (sid.h)
 *     0x1d PREAMBLE_CNTL              0x1d PACKET3_ATOMIC_GDS
 *     0x28 PREAMBLE_BEGIN_CLEAR_STATE 0x28 PACKET3_CONTEXT_CONTROL
 *     0x2a PREAMBLE_END_CLEAR_STATE   0x2a PACKET3_INDEX_TYPE
 *     0x3c WRITE_DATA                 0x3c PACKET3_WAIT_REG_MEM
 *     0x44 MEM_SET_CNTL               0x44 PACKET3_ME_INITIALIZE
 *     -- (0x37 no estaba)            0x37 PACKET3_WRITE_DATA
 *     -- (WAIT_REG_MEM no estaba)     0x3c
 *
 * Un nombre equivocado en un diagnostico es peor que un numero: hace que el
 * mensaje diga algo con autoridad y este equivocado.
 */
const char *
pm4_nombre(unsigned opcode)
{
	switch (opcode) {
	/* sid.h: PACKET3_<NOMBRE> */
	case 0x15: return "DISPATCH_DIRECT";
	case 0x1d: return "ATOMIC_GDS";
	case 0x28: return "CONTEXT_CONTROL";
	case 0x2a: return "INDEX_TYPE";
	case 0x37: return "WRITE_DATA";
	case 0x3c: return "WAIT_REG_MEM";
	case 0x3f: return "INDIRECT_BUFFER";
	case 0x42: return "PFP_SYNC_ME";
	case 0x43: return "SURFACE_SYNC";
	case 0x44: return "ME_INITIALIZE";
	case 0x46: return "EVENT_WRITE";
	case 0x47: return "EVENT_WRITE_EOP";
	case 0x48: return "EVENT_WRITE_EOS";
	case 0x76: return "SET_SH_REG";
	/* vid.h: no están en sid.h */
	case 0x40: return "PREAMBLE_BEGIN";
	case 0x41: return "PREAMBLE_END";
	case 0x58: return "ACQUIRE_MEM";
	case 0x59: return "RELEASE_MEM";
	case 0xc0: return "CONTROL_SWITCH";
	default:   return NULL;
	}
}

#ifndef PM4DECODE_NO_MAIN
/* pm4_volcar la usa solo el main() de linea de comandos. Sin esta guarda
 * enlazarlo en test_pm4 da -Wunused-function: un aviso real, no cosmetico,
 * porque significa que el enlazado ha dejado fuera una parte de la
 * herramienta sin que nadie lo decida explicitamente. */
static void
pm4_volcar(FILE *f, const uint32_t *buf, unsigned n_dw)
{
	unsigned i;
	for (i = 0; i < n_dw; i++) {
		const char *n = pm4_nombre(PM4_HDR_OPCODE(buf[i]));

		fprintf(f, "    [%3u] 0x%08x", i, buf[i]);
		if (PM4_HDR_TYPE(buf[i]) == PM4_TYPE3 && n)
			fprintf(f, "  %s%s count=%u", n,
				PM4_HDR_COMPUTE(buf[i]) ? " (compute)" : "",
				PM4_HDR_COUNT(buf[i]));
		fputc('\n', f);
	}
}
#endif /* PM4DECODE_NO_MAIN */

#ifdef PM4DECODE_SELFTEST
static int fallos;

static void
check(int cond, const char *que)
{
	if (cond) {
		printf("  OK   %s\n", que);
	} else {
		printf("  FAIL %s\n", que);
		fallos++;
	}
}

static void
t(void)
{
	struct pm4_pkt p[16];
	struct pm4_resultado r;
	/* EVENT_WRITE count=0 -> 2 dwords; SET_SH_REG count=2 -> 4 dwords */
	uint32_t ib[] = {
		0xC0004600u, 0x00000407u,		/* EVENT_WRITE, 2 dw */
		0xC0027600u, 0x00002C10u, 0x00000000u, 0x00000000u,	/* SET_SH_REG, 4 dw */
	};
	uint32_t truncada[] = { 0xC0027600u, 0x00002C10u };
	uint32_t sobran[]   = { 0xC0004600u, 0x00000407u, 0xDEADBEEFu };
	uint32_t noheader[] = { 0x12345678u };
	uint32_t par2impar[] = { 0x80010000u, 0u, 0u };
	/* count=7 -> total=9, asi que la IB tiene 9 dwords. Con 18 sobraban
	 * nueve sin cubrir y el decodificador tenia razon en marcarlo: el
	 * vector estaba mal, no el codigo. */
	uint32_t largo[]   = { 0xC0071500u, 1, 2, 3, 4, 5, 6, 7, 8 };

	printf("=== pm4decode selftest ===\n\n");

	printf("[1] una IB bien formada se decodifica y CUADRA\n");
	check(pm4_decode(ib, 6, p, 16, &r) == 0, "sin defecto");
	check(r.n_pkt == 2, "dos paquetes");
	check(p[0].opcode == 0x46 && p[0].count == 0 && p[0].n_dw == 2,
	      "el primero es EVENT_WRITE count=0 total=2");
	check(p[1].opcode == 0x76 && p[1].count == 2 && p[1].n_dw == 4,
	      "el segundo es SET_SH_REG count=2 total=4");
	check(p[1].offset == 2, "el segundo empieza en el dword 2");
	check(p[0].compute == 0, "EVENT_WRITE no es la forma compute");

	printf("\n[2] la forma compute se lee en el bit 1\n");
	{
		uint32_t cc[] = { 0xC0031502u, 0, 0, 0, 0 };
		check(pm4_decode(cc, 5, p, 16, &r) == 0, "sin defecto");
		check(p[0].compute == 1, "bit 1 -> forma compute");
		check(p[0].opcode == 0x15 && p[0].count == 3, "DISPATCH count=3");
		check(p[0].n_dw == 5, "total = count + 2 = 5");
	}

	printf("\n[3] TRUNCAMIENTO: count mayor que lo que queda\n");
	check(pm4_decode(truncada, 2, p, 16, &r) == 1, "falla");
	check(r.defecto == PM4_COUNT_IMPOSIBLE, "defecto COUNT_IMPOSIBLE");
	check(r.offset == 0, "el fallo esta en el dword 0");

	printf("\n[4] SOBRA: no existe el estado, y el vector lo demuestra\n");
	check(pm4_decode(sobran, 3, p, 16, &r) == 1, "falla");
	/* 0xDEADBEEF tiene headerType 3 (0xD = 1101), asi que NO es un sobrante
	 * sino una cabecera con un count enorme: da COUNT_IMPOSIBLE. Por eso
	 * CONSUMO_EXACTO es inalcanzable y la comprobacion queda como red. */
	check(r.defecto == PM4_COUNT_IMPOSIBLE,
	      "0xDEADBEEF se lee como cabecera, no como sobrante");

	printf("\n[5] una cabecera SDMA no es PACKET2/3, y no es basura\n");
	check(pm4_decode(noheader, 1, p, 16, &r) == 1, "falla");
	check(r.defecto == PM4_NO_ES_PM4, "defecto NO_ES_PM4");
	check(strstr(r.motivo, "SDMA") != NULL,
	      "el motivo menciona SDMA, que es la causa legitima");
	check(strstr(r.motivo, "Ningun emisor") == NULL,
	      "el motivo NO acusa al driver: es lo que fallaba antes");
	/* El buffer motivo se quedo en 160 con este mensaje puesto, y lo que se
	 * perdia era justo la cola: el op leido del byte bajo. Un mensaje
	 * truncado dice media verdad, asi que se comprueba la cola. */
	check(strstr(r.motivo, "op_shift 0") != NULL,
	      "la cola del motivo NO se trunca (buffer suficiente)");
	check(strstr(r.motivo, "op=0x") != NULL,
	      "el motivo informa del op del byte bajo");

	printf("\n[6] PACKET2 con count impar no tiene longitud entera\n");
	check(pm4_decode(par2impar, 3, p, 16, &r) == 1, "falla");
	check(r.defecto == PM4_COUNT_IMPOSIBLE, "defecto COUNT_IMPOSIBLE");

	printf("\n[7] un paquete LARGO se guarda truncado, sin desbordar\n");
	check(pm4_decode(largo, 9, p, 16, &r) == 0, "sin defecto");
	check(r.n_pkt == 1 && p[0].n_dw == 9, "un paquete de 9 dwords");
	check(p[0].count == 7, "count = 7");

	printf("\n[8] una IB vacia es valida, no un defecto\n");
	check(pm4_decode(NULL, 0, p, 16, &r) == 0, "sin defecto");
	check(r.n_pkt == 0, "cero paquetes");

	printf("\n[9] huecos de salida agotados: se dice, no se pisa memoria\n");
	{
		uint32_t dos[] = { 0xC0004600u, 0x00000407u, 0xC0004600u, 0x00000407u };
		check(pm4_decode(dos, 4, p, 1, &r) == 1, "falla");
		check(r.defecto == PM4_SIN_PAQUETE, "defecto SIN_PAQUETE");
		check(strstr(r.motivo, "agotaron") != NULL, "el motivo lo dice");
	}

	printf("\n[10] el motivo de un defecto NOMBRA el dword\n");
	(void)pm4_decode(truncada, 2, p, 16, &r);
	check(strstr(r.motivo, "dword 0") != NULL, "el motivo cita el dword");

	/* "=" * 72 es Python, no C. En C se imprime la cadena:
	 * el separador no informa de nada. */
	puts("========================================================================");
	if (fallos) {
		printf("RESULT: FAIL (%d)\n", fallos);
		return;
	}
	printf("RESULT: PASS (25 vectores)\n");
}
#endif /* PM4DECODE_SELFTEST */

/*
 * El main() de linea de comandos se puede excluir al enlazar este fichero en
 * un binario que ya tiene otro. Sin esta guarda, test_pm4 falla con
 * "definiciones multiples de main", y pm4decode.h lo advertia en un
 * comentario mientras el Makefile hacia justo lo contrario.
 */
#ifndef PM4DECODE_NO_MAIN

int
main(int argc, char **argv)
{
	struct pm4_pkt p[256];
	struct pm4_resultado r;
	unsigned n_dw;
	int rv;

	if (argc > 1 && !strcmp(argv[1], "--selftest")) {
#ifdef PM4DECODE_SELFTEST
		t();
		return 0;
#else
		fprintf(stderr, "compilado sin PM4DECODE_SELFTEST\n");
		return 2;
#endif
	}

	if (argc != 2) {
		fprintf(stderr,
			"uso: %s <fichero de dwords en hexadecimal, uno por linea>\n"
			"     %s --selftest\n", argv[0], argv[0]);
		return 2;
	}

	{
		FILE *f = fopen(argv[1], "r");
		char ln[128];
		unsigned cap = 1024, n = 0;
		uint32_t *buf;

		if (!f) {
			fprintf(stderr, "no se abre %s\n", argv[1]);
			return 2;
		}
		buf = malloc(cap * sizeof(*buf));
		if (!buf) {
			fclose(f);
			return 2;
		}
		while (fgets(ln, sizeof(ln), f)) {
			char *e;
			unsigned long v;

			if (ln[0] != '0' && ln[0] != '1' && ln[0] != '2')
				continue;
			v = strtoul(ln, &e, 16);
			if (e == ln)
				continue;
			if (n == cap) {
				cap *= 2;
				buf = realloc(buf, cap * sizeof(*buf));
				if (!buf) {
					fclose(f);
					return 2;
				}
			}
			buf[n++] = (uint32_t)v;
		}
		fclose(f);
		n_dw = n;
		printf("IB de %u dwords\n\n", n_dw);
		pm4_volcar(stdout, buf, n_dw);

		rv = pm4_decode(buf, n_dw, p, 256, &r);
		printf("\n");
		if (rv == 0) {
			printf("BIEN FORMADA: %u paquetes\n", r.n_pkt);
		} else {
			printf("MAL FORMADA (%s) en el dword %u:\n  %s\n",
			       r.defecto == PM4_CONSUMO_EXACTO ? "CONSUMO_EXACTO" :
			       r.defecto == PM4_COUNT_IMPOSIBLE ? "COUNT_IMPOSIBLE" :
			       "SIN_PAQUETE", r.offset, r.motivo);
		}
		free(buf);
	}

	return rv;
}
#endif /* PM4DECODE_NO_MAIN */
