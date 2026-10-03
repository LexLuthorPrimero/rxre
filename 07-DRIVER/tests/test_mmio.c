/* SPDX-License-Identifier: GPL-2.0 */
/*
 * test_mmio.c -- el contrato de la ventana de registros, sin hardware.
 *
 * QUE ESTABLECE Y QUE NO
 *
 * Que los ocho offsets de registro del driver CABEN en la ventana que el
 * hardware muestra medir. Eso es una propiedad de dos numeros medidos, y se
 * puede comprobar entera en userspace.
 *
 * NO establece que la ventana este donde este driver cree que esta. Eso es
 * findings/176 §3: NOT_IN_CORPUS, y por eso rx550_mmio_valida() devuelve
 * RX550_MMIO_NO_VERIFICADA incluso cuando la geometria es correcta. Un test
 * que pasara en ese caso estaria declarando algo que la evidencia no declara.
 *
 * Los numeros vienen de dos sitios, y por eso el test los repite en vez de
 * importarlos del modulo: si el cambio viene con el cambio, el test deja de
 * comprobarlo.
 *
 *     RX550_MMIO_LEN      findings/176, stat() sobre resource2
 *     los 3 RX550_MM_*    findings/180, contra gmc_8_1_d.h
 *     los 5 MM_COMPUTE_*  findings/180, contra gfx_8_0_d.h
 *
 * Salida 0 si todo se comporta como se documenta, 1 si no.
 */

#include <stdbool.h>
#include <stdint.h>
#include <stdio.h>

#include "../kernel/rx550_mmio.h"

static int failures;
static int checks;

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

/* Los ocho offsets que el driver propio va a escribir. Los nombres se replican
 * aqui para que el fallo diga CUAL esta fuera, no solo cuantos. */
struct off_nombre {
	const char	*nombre;
	uint32_t	offset;
};

static const struct off_nombre offsets[] = {
	{ "RX550_MM_VM_CONTEXT0_PTBA",		RX550_MM_VM_CTX0_PTBA },
	{ "RX550_MM_VM_CONTEXT8_PTBA",		RX550_MM_VM_CTX8_PTBA },
	{ "RX550_MM_VM_INVALIDATE_REQUEST",	RX550_MM_VM_INVALIDATE_REQ },
	{ "MM_COMPUTE_DISPATCH_INITIATOR",	0x2e00 },
	{ "MM_COMPUTE_NUM_THREAD_X",		0x2e07 },
	{ "MM_COMPUTE_PGM_LO",			0x2e0c },
	{ "MM_COMPUTE_PGM_HI",			0x2e0d },
	{ "MM_COMPUTE_PGM_RSRC1",		0x2e12 },
};

#define N_OFFSETS	(sizeof(offsets) / sizeof(offsets[0]))

int
main(void)
{
	struct rx550_mmio_info info;
	unsigned fuera, i;

	printf("1. La ventana, contra lo medido y lo observado en 202:\n");
	/* Los numeros vienen de dos sitios distintos y por eso el test los
	 * comprueba contra dos cosas: resource5 por stat(), y el "register mmio
	 * size" que el kernel imprime al arrancar. Si los dos dijeran cosas
	 * distintas, este test no podria elegir. */
	check(RX550_MMIO_LEN == 256u * 1024u,
	      "RX550_MMIO_LEN son 256 KiB, la longitud medida de resource5", NULL);
	/* Aqui estaba `check(RX550_MMIO_BAR == 5)`, y era la forma mas debil de
	 * comprobar la ventana de registros: comparaba el numero con el mismo
	 * numero. Se cambio el 2026-10-03, y no por estilo.
	 *
	 * Lo que sustituye NO es mas flojo: es el mismo 5, pero derivado de la
	 * geometria, que es una propiedad del hardware medida por el nucleo, y no
	 * de una constante escrita al lado del test que la usa. El 5 sigue siendo el
	 * numero correcto; lo que cambio es de donde sale y, sobre todo, que ahora
	 * este test puede FALLAR si la geometria no lo selecciona. */
	{
		struct rx550_bar_desc medidos[] = {
			/* findings/176 §1 y findings/305, por stat() sin root y por el
			 * rango del fichero `resource` agregado. Los dos coinciden. */
			{ 0, 268435456u, 1 },	/* BAR0  256 MiB  memoria */
			{ 1,         0u, 0 },	/* BAR1  no implementado */
			{ 2,  2097152u, 1 },	/* BAR2    2 MiB  memoria */
			{ 3,         0u, 0 },	/* BAR3  no implementado */
			{ 4,      256u, 0 },	/* BAR4  256 BYTES de E/S */
			{ 5,   262144u, 1 },	/* BAR5  256 KiB  memoria */
		};
		struct rx550_mmio_info d;

		check(rx550_mmio_deriva(medidos, 6, &d) == RX550_MMIO_OK,
		      "la geometria real deriva un BAR", NULL);
		check(d.bar == 5,
		      "y el que deriva es el 5, sin que nadie lo escribiera", NULL);
		check(d.len == RX550_MMIO_LEN,
		      "y su longitud es exactamente la de la ventana", NULL);
		check(d.es_valido == 1, "y la geometria queda marcada valida", NULL);
	}

	/* Y el negative que hace este contrato comprobable: la ventana que se
	 * TOMABA antes, 2 MiB, es la de resource2 y no es la de registros. Un
	 * test que solo comprobara el numero correcto no detectaria haber
	 * vuelto al equivocado. */
	check(RX550_MMIO_LEN != 2u * 1024u * 1024u,
	      "la ventana NO es la de 2 MiB: esa es resource2", NULL);

	printf("\n2. Los offsets caben en la ventana de 256 KiB:\n");
	fuera = rx550_mmio_offsetes_fuera(NULL, 0, RX550_MMIO_LEN);
	check(fuera == 0, "sin lista de offsets no se afirma nada, no que caben", NULL);

	for (i = 0; i < N_OFFSETS; i++) {
		char buf[112];
		snprintf(buf, sizeof(buf), "%s = 0x%04x cabe en %u bytes",
			 offsets[i].nombre, offsets[i].offset, RX550_MMIO_LEN);
		check(rx550_mmio_offset_ok(offsets[i].offset, RX550_MMIO_LEN),
		      buf, NULL);
	}

	/* Y la forma agregada, que es la que usa el gate. */
	{
		uint32_t lista[N_OFFSETS];
		for (i = 0; i < N_OFFSETS; i++)
			lista[i] = offsets[i].offset;
		check(rx550_mmio_offsetes_fuera(lista, N_OFFSETS,
						RX550_MMIO_LEN) == 0,
		      "ninguno de los ocho offsets se sale de la ventana", NULL);
	}

	/* El extremo: el ultimo byte dentro, el siguiente fuera. */
	check(rx550_mmio_offset_ok(RX550_MMIO_LEN - 1, RX550_MMIO_LEN),
	      "el ultimo byte de la ventana esta DENTRO", NULL);
	check(!rx550_mmio_offset_ok(RX550_MMIO_LEN, RX550_MMIO_LEN),
	      "un byte mas alla ya esta FUERA", NULL);
	check(!rx550_mmio_offset_ok(0x80000000u, RX550_MMIO_LEN),
	      "un offset con el bit 31 puesto no pasa por estar en negativo", NULL);

	printf("\n3. La geometria decide, y con un motivo legible:\n");
	/* ESTOS TRES CAMBIARON DE SENTIDO el 2026-10-03, y es lo unico que se
	 * invirtio. Antes los tres afirmaban que una geometria correcta NO
	 * alcanzaba, y el ultimo comprobaba `valida(0, RX550_MMIO_LEN)` -> AUSENTE
	 * con el texto "otro BAR con el tamano correcto NO se acepta: el indice esta
	 * declarado".
	 *
	 * Ese ultimo control custodiaba un enclavamiento que era correcto ENTONCES:
	 * mientras el indice estuviera declarado, rechazar cualquier otro era lo
	 * unico que impedia heredar el NOT_IN_CORPUS. Con el indice derivado, ese
	 * control se ha vuelto falso: rechazaria geometrias validas y, peor, no
	 * distinguiria un indice mal derivado de uno bien derivado.
	 *
	 * NO SE BORRA NADA: los tres casos siguen aquí, con la razon cambiada. Un
	 * control que se quita porque dejo de ser verdad es una decision; uno que se
	 * quita sin dejar escrito por que es un agujero. */
	check(rx550_mmio_valida(5, RX550_MMIO_LEN, &info) == RX550_MMIO_OK,
	      "geometria correcta ALCANZA para mapear: el indice ya esta derivado",
	      NULL);
	check(info.es_valido == 1,
	      "y la geometria se reconoce como valida", NULL);
	check(info.motivo == RX550_MMIO_OK && info.porque != NULL &&
	      info.porque[0] != '\0',
	      "y el motivo dice por que, en castellano", NULL);

	check(rx550_mmio_valida(5, RX550_MMIO_LEN / 2, &info) ==
	      RX550_MMIO_TAMANO_OTRO,
	      "una ventana de la mitad del tamano NO se acepta", NULL);
	check(info.es_valido == 0,
	      "y con ella la geometria queda marcada como no valida", NULL);

	check(rx550_mmio_valida(5, 0, &info) ==
	      RX550_MMIO_BAR_AUSENTE,
	      "una longitud cero es un BAR ausente, no un tamano raro", NULL);

	/* El que guardaba el "indice declarado". Invertido, y por el motivo que se
	 * dice arriba: ahora el indice viene de deriva(), y por eso lo que hay que
	 * comprobar es que la longitud, no el indice. */
	check(rx550_mmio_valida(0, RX550_MMIO_LEN, &info) == RX550_MMIO_OK,
	      "cualquier indice con la longitud correcta pasa: el indice se deriva, "
	      "no se compara con una constante", NULL);

	check(rx550_mmio_valida(5, RX550_MMIO_LEN, NULL) ==
	      RX550_MMIO_BAR_AUSENTE,
	      "un out NULL no revienta", NULL);

	printf("\n3b. La derivacion, y sus controles negativos:\n");
	/* Un criterio que dice "el BAR que mide RX550_MMIO_LEN" sin exigir unicidad
	 * devolveria el primero de la tabla, y eso es elegir por el orden del array.
	 * Estos casos son los que hacen falsable el criterio, y son los que
	 * fallarian si alguien aflojara la unicidad. */
	{
		struct rx550_mmio_info d;
		struct rx550_bar_desc solo_io[]      = { { 4, RX550_MMIO_LEN, 0 } };
		struct rx550_bar_desc solo_io_otro[] = { { 4, 256u, 0 } };
		struct rx550_bar_desc solo_2mib[]    = { { 2, 2097152u, 1 } };
		struct rx550_bar_desc dos_iguales[]  = { { 5, RX550_MMIO_LEN, 1 },
							{ 3, RX550_MMIO_LEN, 1 } };
		struct rx550_bar_desc vacia[]       = { { 1, 0u, 0 }, { 3, 0u, 0 } };
		struct rx550_bar_desc io_y_mem[]     = { { 4, RX550_MMIO_LEN, 0 },
							{ 5, RX550_MMIO_LEN, 1 } };

		check(rx550_mmio_deriva(solo_io, 1, &d) == RX550_MMIO_BAR_NO_MEMORIA,
		      "un BAR de E/S de la longitud EXACTA NO es la ventana, y el motivo "
		      "dice que es tipo, no tamano", NULL);
		/* Este caso salio mal dos veces y las dos por la misma razon: la
		 * expectativa la escribi desde la intuicion y no desde el criterio.
		 * La primera vez puse 256 BYTES donde decia "longitud exacta", asi que
		 * no probaba lo que su nombre decia. La segunda fois espere
		 * BAR_AUSENTE, que dice "no implementado por el hardware", y es falso:
		 * BAR4 SI esta implementado. Lo que lo descarta es el TIPO, y por eso
		 * el motivo es NO_MEMORIA tanto si la longitud coincide como si no.
		 *
		 * Esa es la decision, y conviene que este escrita: cuando hay un BAR de
		 * E/S implementado, el motivo es "no es memoria", no "no existe". El
		 * tamaño secundario no cambia la razon por la que no puede ser la
		 * ventana. */
		check(rx550_mmio_deriva(solo_io_otro, 1, &d) == RX550_MMIO_BAR_NO_MEMORIA,
		      "un BAR de E/S de OTRO tamano tampoco es la ventana, y el motivo "
		      "sigue siendo el tipo, no la longitud", NULL);
		check(rx550_mmio_deriva(solo_2mib, 1, &d) == RX550_MMIO_TAMANO_OTRO,
		      "un BAR de memoria de 2 MiB NO es la ventana, aunque sea memoria", NULL);
		check(rx550_mmio_deriva(dos_iguales, 2, &d) == RX550_MMIO_BAR_AMBIGUO,
		      "DOS BAR de memoria de la longitud exacta: ambiguo, y no se elige", NULL);
		check(rx550_mmio_deriva(dos_iguales, 2, &d) != RX550_MMIO_OK &&
		      d.es_valido == 0,
		      "y en el ambiguo la geometria queda NO valida", NULL);
		check(rx550_mmio_deriva(vacia, 2, &d) == RX550_MMIO_BAR_AUSENTE,
		      "ningun BAR implementado es BAR ausente, no un tamano raro", NULL);
		check(rx550_mmio_deriva(io_y_mem, 2, &d) == RX550_MMIO_OK && d.bar == 5,
		      "con un E/S de la misma longitud delante, la unicidad RESUELVE sola", NULL);
		check(rx550_mmio_deriva(NULL, 0, &d) == RX550_MMIO_BAR_AUSENTE,
		      "una tabla nula no revienta", NULL);
		check(rx550_mmio_deriva(vacia, 2, NULL) == RX550_MMIO_BAR_AUSENTE,
		      "un out NULL no revienta", NULL);
	}
	check(rx550_mmio_motivo(RX550_MMIO_BAR_AMBIGUO) !=
	      rx550_mmio_motivo(RX550_MMIO_BAR_AUSENTE),
	      "el motivo de ambiguo NO es el de ausente: son fallos distintos", NULL);

	printf("\n4. El motivo es un enum cerrado:\n");
	check(rx550_mmio_motivo(RX550_MMIO_OK)[0] != '\0',
	      "RX550_MMIO_OK tiene texto", NULL);
	check(rx550_mmio_motivo(9999)[0] != '\0',
	      "un motivo fuera de rango tambien tiene texto, no una lectura nula", NULL);
	check(rx550_mmio_motivo(RX550_MMIO_NO_VERIFICADA) !=
	      rx550_mmio_motivo(RX550_MMIO_OK),
	      "el motivo de 'no verificada' NO es el de 'conforme'", NULL);

	printf("\n%d checks, %d failure(s)\n", checks, failures);
	if (failures) {
		printf("RESULT: FAIL\n");
		return 1;
	}
	printf("RESULT: PASS\n");
	printf("\nNOT covered, and not claimed:\n"
	       "  - que un offset apunte al registro que dice. Lo verifican las ocho\n"
	       "    lineas de findings/180 contra el ASIC, una por una.\n"
	       "  - que escribir en la ventana tenga efecto. No hay hardware aqui.\n"
	       "  - que la geometria de la tabla que se pasa sea la de esta placa. La\n"
	       "    tabla del test son las longitudes MEDIDAS (176 §1, 305), escritas a\n"
	       "    mano en el test; que el nucleo las lea en ejecucion es cosa del\n"
	       "    modulo, y eso no se comprueba aqui.\n"
	       "  - SIGUE NOT_IN_CORPUS el mapa bloque-de-amdgpu -> BAR. No es lo que\n"
	       "    se derivo: se derivo que BAR es la apertura de registros de ESTE\n"
	       "    dispositivo, que es otra pregunta y tiene fuentes.\n"
	       "");
	return 0;
}
