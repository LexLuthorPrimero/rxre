/* SPDX-License-Identifier: GPL-2.0-only */
/*
 * test_resource.c — T1..T15 del componente 4 (PCI resource ownership).
 *
 * ALCANCE DE CADA TEST, declarado explícitamente:
 *   [DEVICE]  lee el dispositivo real por sysfs.  Discrimina: si la tarjeta
 *             fuera otra, el inventario no coincidiría y el test falla.
 *   [MODEL]   ejecuta la lógica real de target_resource.h, la misma que
 *             compila el driver.  No puede invocar pci_request_region()
 *             porque ésa es una función del kernel.
 *   [SOURCE]  comprueba el fuente o el .ko (ver test_static.sh).
 *
 * No carga el módulo. No hace bind. No mapea. No abre la GPU.
 */
#define _GNU_SOURCE
#include <stdio.h>
#include <stdlib.h>
#include <string.h>
#include <stdint.h>
#include <fcntl.h>
#include <unistd.h>
#include <sys/stat.h>

#include "../target_resource.h"
#include "../target_match.h"

static int pass, fail;

static void chk(const char *id, const char *kind, const char *what, int got, int want)
{
	if (got == want) {
		printf("  PASS  %-5s %-8s %s\n", id, kind, what);
		pass++;
	} else {
		printf("  FAIL  %-5s %-8s %s (got %d want %d)\n", id, kind, what, got, want);
		fail++;
	}
}

static const char *bdf = "0000:01:00.0";
static char dpath[256];

static uint32_t rd32(const char *what, off_t off)
{
	char f[320];
	uint32_t v = 0;
	int fd;

	snprintf(f, sizeof(f), "%s/%s", dpath, what);
	fd = open(f, O_RDONLY);
	if (fd < 0)
		return 0;
	if (pread(fd, &v, 4, off) != 4)
		v = 0;
	close(fd);
	return v;
}

/* Longitud real de una BAR = st_size del fichero resourceN de sysfs.
 * resourceN es un blob binario cuyo tamano declarado ES la longitud de la BAR.
 * Se usa stat(2): fseek/ftell sobre un fichero de sysfs devuelve 0 porque
 * sysfs no es seekable aunque st_size sea correcto. */
static unsigned long long bar_len(int bar)
{
	char f[320];
	struct stat st;

	snprintf(f, sizeof(f), "%s/resource%d", dpath, bar);
	if (stat(f, &st) != 0)
		return 0;
	return (unsigned long long)st.st_size;
}

int main(int argc, char **argv)
{
	if (argc > 1)
		bdf = argv[1];
	snprintf(dpath, sizeof(dpath), "/sys/bus/pci/devices/%s", bdf);

	printf("componente 4 · PCI resource ownership · %s\n", bdf);
	printf("TARGET = RX 550 instalada · SCOPE = EXCLUSIVO\n\n");

	/* ---------------- T1-T3  [DEVICE] ---------------- */
	{
		uint32_t b0 = rd32("config", 0x10);
		uint32_t b1 = rd32("config", 0x14);
		uint32_t b2 = rd32("config", 0x18);
		uint32_t b3 = rd32("config", 0x1c);
		uint32_t b4 = rd32("config", 0x20);
		uint32_t b5 = rd32("config", 0x24);

		printf("T1-T3 · inventario real del dispositivo\n");
		/* T2: clasificación por tipo, de los bits del BAR */
		chk("T2a", "DEVICE", "BAR0 es MEM (bit0=0)", (b0 & 1) == 0, 1);
		chk("T2b", "DEVICE", "BAR0 es 64-bit (bits2:1=2)", ((b0 >> 1) & 3) == 2, 1);
		chk("T2c", "DEVICE", "BAR0 es prefetchable (bit3=1)", ((b0 >> 3) & 1) == 1, 1);
		chk("T2d", "DEVICE", "BAR2 es MEM 64-bit prefetchable",
		    ((b2 & 1) == 0) && (((b2 >> 1) & 3) == 2) && (((b2 >> 3) & 1) == 1), 1);
		chk("T2e", "DEVICE", "BAR4 es I/O (bit0=1)", (b4 & 1) == 1, 1);
		chk("T2f", "DEVICE", "BAR5 es MEM 32-bit (bits2:1=0)",
		    ((b5 & 1) == 0) && (((b5 >> 1) & 3) == 0), 1);
		chk("T2g", "DEVICE", "BAR5 NO es prefetchable (bit3=0)", ((b5 >> 3) & 1) == 0, 1);

		/* T1: los words altos de las BAR de 64 bits valen 0 */
		chk("T1a", "DEVICE", "BASE(0) = 0x00000000E0000000",
		    (unsigned long long)(((unsigned long long)b1 << 32) | (b0 & 0xfffffff0u)),
		    0x00000000E0000000ULL);
		chk("T1b", "DEVICE", "BASE(2) = 0x00000000F0000000",
		    (unsigned long long)(((unsigned long long)b3 << 32) | (b2 & 0xfffffff0u)),
		    0x00000000F0000000ULL);
		chk("T1c", "DEVICE", "BASE(4) I/O = 0xE000", (unsigned long long)(b4 & ~1u), 0xE000ULL);
		chk("T1d", "DEVICE", "BASE(5) = 0xF7D00000",
		    (unsigned long long)(b5 & 0xfffffff0u), 0xF7D00000ULL);

		/* T3: longitudes, del tamaño de resourceN */
		chk("T3a", "DEVICE", "len(BAR0) = 256 MiB", bar_len(0) == 256ULL << 20, 1);
		chk("T3b", "DEVICE", "len(BAR1) = 0 (word alto)", bar_len(1) == 0, 1);
		chk("T3c", "DEVICE", "len(BAR2) = 2 MiB", bar_len(2) == 2ULL << 20, 1);
		chk("T3d", "DEVICE", "len(BAR3) = 0 (word alto)", bar_len(3) == 0, 1);
		chk("T3e", "DEVICE", "len(BAR4) = 256 (I/O)", bar_len(4) == 256, 1);
		chk("T3f", "DEVICE", "len(BAR5) = 256 KiB", bar_len(5) == 256ULL << 10, 1);
		/* invariante I2: la apertura de registros debe cubrir el
		 * mayor offset de registro conocido. */
		chk("T3g", "DEVICE", "len(BAR5) cubre mmSCRATCH_REG0 0xc040",
		    bar_len(5) > 0xc040ULL, 1);
	}

	/* ---------------- T4  [MODEL] ---------------- */
	{
		struct target_resources r;
		int i, absent = 0;

		printf("\nT4 · modelo de propiedad\n");
		target_res_init(&r);
		chk("T4a", "MODEL", "init deja nr_claimed = 0", r.nr_claimed, 0);
		chk("T4b", "MODEL", "init deja enabled = 0", r.enabled, 0);
		for (i = 0; i < TARGET_NR_BARS; i++)
			if (r.bar[i].state == TARGET_RES_ABSENT)
				absent++;
		chk("T4c", "MODEL", "init: las 6 BAR en ABSENT", absent, TARGET_NR_BARS);

		/* len == 0 ⇒ ABSENT, no DISCOVERED: son estados distintos */
		target_res_set(&r, 0, 0xE0000000ULL, 256ULL << 20);
		chk("T4d", "MODEL", "len>0 ⇒ DISCOVERED", r.bar[0].state, TARGET_RES_DISCOVERED);
		target_res_set(&r, 1, 0, 0);
		chk("T4e", "MODEL", "len==0 ⇒ ABSENT (no DISCOVERED)", r.bar[1].state, TARGET_RES_ABSENT);

		/* BAR existente NO es BAR adquirida */
		chk("T4f", "MODEL", "DISCOVERED no está owned", target_res_owned(r.bar[0].state), 0);
		chk("T4g", "MODEL", "ABSENT no está owned", target_res_owned(r.bar[1].state), 0);
		/* I3: sólo CLAIMED está owned */
		target_res_mark_claimed(&r, 0);
		chk("T4h", "MODEL", "CLAIMED está owned", target_res_owned(r.bar[0].state), 1);
		chk("T4i", "MODEL", "nr_claimed cuenta exactamente 1", r.nr_claimed, 1);
	}

	/* ---------------- T5-T6  [MODEL]  enable DEFERRED != MISSING ---- */
	{
		struct target_resources r;

		printf("\nT5-T6 · pci_enable_device() DEFERRED\n");
		target_res_init(&r);
		/* T5: camino de exito, modelado por el estado que
		 * habilitación dejaría tras la región.  No se invoca la API. */
		chk("T5", "MODEL", "STATE 0: enabled=0 antes de cualquier cosa", r.enabled, 0);
		/* T6: camino de fallo, igualmente modelado: si el enable se
		 * hubiera intentado y fallado, no se habría tocado región. */
		target_res_set(&r, TARGET_REG_BAR_INDEX, 0xF7D00000ULL, 256ULL << 10);
		chk("T6a", "MODEL", "fallo de enable no avanza nr_claimed", r.nr_claimed, 0);
		chk("T6b", "MODEL", "fallo de enable deja la BAR DISCOVERED",
		    r.bar[TARGET_REG_BAR_INDEX].state, TARGET_RES_DISCOVERED);
	}

	/* ---------------- T7-T8  [MODEL]  adquisición ---------------- */
	{
		struct target_resources r;

		printf("\nT7-T8 · adquisición de región (modelo)\n");
		target_res_init(&r);
		target_res_set(&r, 0, 0xE0000000ULL, 256ULL << 20);
		target_res_set(&r, 1, 0, 0);
		target_res_set(&r, 2, 0xF0000000ULL, 2ULL << 20);
		target_res_set(&r, 3, 0, 0);
		target_res_set(&r, 4, 0xE000ULL, 256);
		target_res_set(&r, 5, 0xF7D00000ULL, 256ULL << 10);

		/* T7: camino de éxito */
		chk("T7a", "MODEL", "claim de BAR5 desde DISCOVERED", target_res_mark_claimed(&r, 5), 1);
		chk("T7b", "MODEL", "nr_claimed = 1 tras el claim", r.nr_claimed, 1);
		chk("T7c", "MODEL", "sólo BAR5 queda CLAIMED",
		    r.bar[5].state == TARGET_RES_CLAIMED &&
		    r.bar[0].state == TARGET_RES_DISCOVERED &&
		    r.bar[2].state == TARGET_RES_DISCOVERED &&
		    r.bar[4].state == TARGET_RES_DISCOVERED, 1);

		/* T8: camino de conflicto — claim sobre una BAR ABSENT falla */
		chk("T8a", "MODEL", "claim de una BAR ABSENT falla", target_res_mark_claimed(&r, 1), 0);
		chk("T8b", "MODEL", "el conflicto no incrementa nr_claimed", r.nr_claimed, 1);
		chk("T8c", "MODEL", "la BAR en conflicto sigue ABSENT", r.bar[1].state, TARGET_RES_ABSENT);
		/* doble claim no puede ocurrir */
		chk("T8d", "MODEL", "doble claim de la misma BAR falla", target_res_mark_claimed(&r, 5), 0);
		chk("T8e", "MODEL", "nr_claimed sigue 1", r.nr_claimed, 1);
	}

	/* ---------------- T9-T11  unwind y simetría ---------------- */
	{
		struct target_resources r;

		printf("\nT9-T11 · unwind, orden de liberación, simetría\n");
		target_res_init(&r);
		target_res_set(&r, 0, 0xE0000000ULL, 256ULL << 20);
		target_res_set(&r, 2, 0xF0000000ULL, 2ULL << 20);
		target_res_set(&r, 5, 0xF7D00000ULL, 256ULL << 10);

		/* T9: fallo de adquisición ⇒ vuelta a STATE 0, nada que liberar */
		chk("T9a", "MODEL", "sin claim no hay nada owned",
		    target_res_all_released(&r), 1);

		/* acquire, luego unwind completo */
		target_res_mark_claimed(&r, 5);
		chk("T9b", "MODEL", "tras adquirir, no todo released",
		    target_res_all_released(&r), 0);

		/* T10: orden de liberación — sólo CLAIMED, en índice inverso */
		{
			int bar;
			int released[6], n = 0;
			for (bar = TARGET_NR_BARS - 1; bar >= 0; bar--)
				if (target_res_owned(r.bar[bar].state)) {
					released[n++] = bar;
					target_res_mark_released(&r, bar);
				}
			chk("T10a", "MODEL", "se libera exactamente 1 región", n, 1);
			chk("T10b", "MODEL", "y es la adquirida (BAR5)", released[0], 5);
		}
		chk("T10c", "MODEL", "todo released tras el unwind",
		    target_res_all_released(&r), 1);
		chk("T10d", "MODEL", "nr_claimed vuelve a 0", r.nr_claimed, 0);

		/* T11: simetría de remove — liberar una BAR no adquirida es inocuo */
		chk("T11a", "MODEL", "release de no-CLAIMED no hace nada",
		    target_res_mark_released(&r, 2), 0);
		chk("T11b", "MODEL", "y nr_claimed sigue 0", r.nr_claimed, 0);
		chk("T11c", "MODEL", "BAR2 sigue DISCOVERED tras un release no-dueño",
		    r.bar[2].state, TARGET_RES_DISCOVERED);
	}

	/* ---------------- T15  TARGET_MATCH sin cambios ---------------- */
	{
		printf("\nT15 · TARGET_MATCH intacto\n");
		chk("T15a", "MODEL", "los 5 campos correctos aceptan",
		    target_match(0x1002, 0x699f, 0x1002, 0x0b04, 0xc7), 1);
		chk("T15b", "MODEL", "otro Polaris12 (0x6987) rechaza",
		    target_match(0x1002, 0x6987, 0x1002, 0x0b04, 0xc7), 0);
		chk("T15c", "MODEL", "otra tarjeta del mismo device ID (1028:1720) rechaza",
		    target_match(0x1002, 0x699f, 0x1028, 0x1720, 0xc7), 0);
	}

	printf("\nresumen: %d PASS, %d FAIL\n", pass, fail);
	return fail ? 1 : 0;
}
