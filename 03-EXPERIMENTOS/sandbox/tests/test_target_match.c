/* SPDX-License-Identifier: GPL-2.0-only */
/*
 * test_target_match.c — T1..T9.
 *
 * Ejecuta la MISMA función que usa el driver (target_match.h), no una copia.
 * Un test que inspecciona texto fuente no puede detectar un defecto de
 * comportamiento; éste invoca la regla real.
 *
 * No carga el módulo. No accede al hardware. No abre /dev, ni sysfs de la GPU.
 */

#include <stdio.h>
#include <string.h>

#include "../target_match.h"

static int pass, fail;

static void check(const char *id, const char *what, int got, int want)
{
	if (got == want) {
		printf("  PASS  %-4s %s\n", id, what);
		pass++;
	} else {
		printf("  FAIL  %-4s %s (got %d, want %d)\n", id, what, got, want);
		fail++;
	}
}

int main(void)
{
	printf("T1-T9 · target_match() · TARGET = RX 550 instalada\n\n");

	/* T1: candidato correcto en los 4 campos de la id_table */
	check("T1", "1002:699F es candidato de la id_table",
	      target_match_core_id(0x1002, 0x699f, 0x1002, 0x0b04), 1);
	check("T1b", "1002:699F con subsys equivocado NO es candidato",
	      target_match_core_id(0x1002, 0x699f, 0x1028, 0x0b04), 0);

	/* T2: subsystem_vendor correcto */
	check("T2", "subsystem_vendor 0x1002 acepta",
	      target_match(0x1002, 0x699f, 0x1002, 0x0b04, 0xc7), 1);
	check("T2b", "subsystem_vendor distinto rechaza",
	      target_match(0x1002, 0x699f, 0x1028, 0x0b04, 0xc7), 0);

	/* T3: subsystem_device correcto */
	check("T3", "subsystem_device 0x0B04 acepta",
	      target_match(0x1002, 0x699f, 0x1002, 0x0b04, 0xc7), 1);
	check("T3b", "subsystem_device distinto rechaza",
	      target_match(0x1002, 0x699f, 0x1002, 0x1720, 0xc7), 0);

	/* T4: revisión C7 */
	check("T4", "revision 0xC7 acepta",
	      target_match(0x1002, 0x699f, 0x1002, 0x0b04, 0xc7), 1);
	check("T4b", "revision 0xC0 rechaza (mismo device, silicio distinto)",
	      target_match(0x1002, 0x699f, 0x1002, 0x0b04, 0xc0), 0);
	check("T4c", "la revisión NO está cubierta por la id_table",
	      target_match_core_id(0x1002, 0x699f, 0x1002, 0x0b04), 1);

	/* T5: cualquier discrepancia rechaza */
	check("T5a", "device equivocado rechaza",
	      target_match(0x1002, 0x1234, 0x1002, 0x0b04, 0xc7), 0);
	check("T5b", "vendor equivocado rechaza",
	      target_match(0x8086, 0x699f, 0x1002, 0x0b04, 0xc7), 0);
	check("T5c", "subsys vendor+device ambos distintos rechazan",
	      target_match(0x1002, 0x699f, 0x1da2, 0xe367, 0xc7), 0);
	check("T5d", "todos los campos distintos rechazan",
	      target_match(0xdead, 0xbeef, 0xcafe, 0xf00d, 0x99), 0);

	/* T6: los cinco correctos aceptan */
	check("T6", "los cinco campos correctos aceptan",
	      target_match(TARGET_VENDOR, TARGET_DEVICE,
			   TARGET_SUBSYS_VENDOR, TARGET_SUBSYS_DEVICE,
			   TARGET_REVISION), 1);

	/* T7: los otros siete device IDs de la misma ASIC rechazan */
	check("T7a", "Polaris12 0x6980 rechaza",
	      target_match(0x1002, OTHER_POLARIS12_DEVICE_0, 0x1002, 0x0b04, 0xc7), 0);
	check("T7b", "Polaris12 0x6981 rechaza",
	      target_match(0x1002, OTHER_POLARIS12_DEVICE_1, 0x1002, 0x0b04, 0xc7), 0);
	check("T7c", "Polaris12 0x6985 rechaza",
	      target_match(0x1002, OTHER_POLARIS12_DEVICE_2, 0x1002, 0x0b04, 0xc7), 0);
	check("T7d", "Polaris12 0x6986 rechaza",
	      target_match(0x1002, OTHER_POLARIS12_DEVICE_3, 0x1002, 0x0b04, 0xc7), 0);
	check("T7e", "Polaris12 0x6987 rechaza",
	      target_match(0x1002, OTHER_POLARIS12_DEVICE_4, 0x1002, 0x0b04, 0xc7), 0);
	check("T7f", "Polaris12 0x6995 rechaza",
	      target_match(0x1002, OTHER_POLARIS12_DEVICE_5, 0x1002, 0x0b04, 0xc7), 0);
	check("T7g", "Polaris12 0x6997 rechaza",
	      target_match(0x1002, OTHER_POLARIS12_DEVICE_6, 0x1002, 0x0b04, 0xc7), 0);

	/* T8: device ID de otra familia */
	check("T8", "1002:67CC rechaza",
	      target_match(0x1002, UNRELATED_DEVICE_ID, 0x1002, 0x0b04, 0xc7), 0);

	/* T9: vendor no-AMD con el resto correcto */
	check("T9a", "vendor no-AMD rechaza",
	      target_match(0x10de, 0x699f, 0x1002, 0x0b04, 0xc7), 0);
	check("T9b", "vendor 0 (comodín) NO acepta: no hay comodines",
	      target_match(0, 0x699f, 0x1002, 0x0b04, 0xc7), 0);

	printf("\nresumen: %d PASS, %d FAIL\n", pass, fail);
	return fail ? 1 : 0;
}
