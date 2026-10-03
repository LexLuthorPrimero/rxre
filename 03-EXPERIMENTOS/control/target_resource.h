/* SPDX-License-Identifier: GPL-2.0-only */
/*
 * target_resource.h — modelo de propiedad de recursos PCI.
 *
 * QUÉ ES Y QUÉ NO ES
 *   Modelo de propiedad + capa de adquisición.  NO es MMIO: no hay
 *   traducción a espacio virtual de CPU, ni acceso a registros.
 *
 *   PCI resource acquisition  !=  GPU execution
 *
 * ESCALERA DE ESTADOS (separación estricta exigida)
 *
 *   ABSENT      el hardware no declara esa BAR          (resource_len == 0)
 *   DISCOVERED  declarada y localizada, sin reclamar
 *   CLAIMED     propiedad tomada por este driver
 *   MAPPED      (futuro, componente MMIO) traducción CPU
 *   USED        (futuro) en uso por el driver
 *
 *   Una BAR existente NO es una BAR adquirida.  resource_start() NO es una
 *   dirección virtual.  Una IRQ declarada NO es una IRQ registrada.
 *
 * INVARIANTES
 *   I1  start  es una DIRECCIÓN PCI (espacio del bus), no una VA de CPU.
 *   I2  len    es un TAMAÑO de recurso, no un mapping.
 *   I3  sólo se libera lo que está en estado >= CLAIMED.
 *   I4  nr_claimed cuenta exactamente las ranuras en CLAIMED.
 *
 * ALCANCE
 *   TARGET = RX 550 instalada en esta computadora. SCOPE = EXCLUSIVO.
 *   Sólo se reclama la BAR que el siguiente componente necesitará.  Las demás
 *   quedan DISCOVERED; ninguna se reserva por anticipación.
 *
 * Sin cabeceras del kernel: compila igual en módulo y en test de userspace.
 */
#ifndef TARGET_RESOURCE_H
#define TARGET_RESOURCE_H

#define TARGET_NR_BARS		6

/*
 * La única BAR que este driver reclama hoy.
 *
 * Evidencia del sistema (0000:01:00.0), config space + tamaño de resourceN:
 *   BAR0  0xe000000c  MEM64 prefetch  base 0x0000_0000_E000_0000  256 MiB
 *   BAR1  0x00000000  word alto de BAR0
 *   BAR2  0xf000000c  MEM64 prefetch  base 0x0000_0000_F000_0000  2 MiB
 *   BAR3  0x00000000  word alto de BAR2
 *   BAR4  0x0000e001  I/O            base 0x0000_E000            256 B
 *   BAR5  0xf7d00000  MEM32          base 0x0000_0000_F7D0_0000  256 KiB
 *
 * BAR5 es la apertura de registros.  El mayor offset de registro conocido
 * (mmSCRATCH_REG0 = 0xc040) cabe en 0x40000.  BAR2 es la apertura de
 * doorbell y no se necesita hasta un componente posterior; BAR0 es la
 * apertura de VRAM y BAR4 es decodificación legacy: ninguno se necesita.
 */
#define TARGET_REG_BAR_INDEX	5

enum target_res_state {
	TARGET_RES_ABSENT	= 0,	/* la hardware no la declara          */
	TARGET_RES_DISCOVERED	= 1,	/* localizada, sin reclamar           */
	TARGET_RES_CLAIMED	= 2,	/* propiedad de este driver           */
	TARGET_RES_MAPPED	= 3,	/* futuro: MMIO                       */
	TARGET_RES_USED		= 4,	/* futuro: en uso                     */
};

struct target_res_slot {
	unsigned char		state;		/* enum target_res_state          */
	unsigned char		present;	/* 1 si len > 0                   */
	unsigned long long	start;	/* I1: dirección PCI, no VA       */
	unsigned long long	len;	/* I2: tamaño, no mapping          */
};

struct target_resources {
	struct target_res_slot	bar[TARGET_NR_BARS];
	unsigned int		nr_claimed;	/* I4                            */
	unsigned int		enabled;	/* pci_enable_device()            */
};

/* ¿esta ranura la posee el driver y debe liberarla? (I3) */
static inline int target_res_owned(unsigned char state)
{
	return state >= (unsigned char)TARGET_RES_CLAIMED;
}

/* Inicializa: todo ABSENT, nada reclamado, dispositivo no habilitado. */
static inline void target_res_init(struct target_resources *res)
{
	int i;

	for (i = 0; i < TARGET_NR_BARS; i++) {
		res->bar[i].state   = (unsigned char)TARGET_RES_ABSENT;
		res->bar[i].present = 0;
		res->bar[i].start   = 0;
		res->bar[i].len     = 0;
	}
	res->nr_claimed = 0;
	res->enabled    = 0;
}

/* Registra una BAR localizada.  len == 0 ⇒ no declarada (ABSENT). */
static inline void target_res_set(struct target_resources *res, int bar,
				  unsigned long long start, unsigned long long len)
{
	if (bar < 0 || bar >= TARGET_NR_BARS)
		return;

	res->bar[bar].start   = start;
	res->bar[bar].len     = len;
	res->bar[bar].present = (unsigned char)(len != 0);
	res->bar[bar].state   = (unsigned char)(len != 0 ? TARGET_RES_DISCOVERED
							: TARGET_RES_ABSENT);
}

/* Marca una BAR como reclamada.  Sólo desde DISCOVERED. */
static inline int target_res_mark_claimed(struct target_resources *res, int bar)
{
	if (bar < 0 || bar >= TARGET_NR_BARS)
		return 0;
	if (res->bar[bar].state != (unsigned char)TARGET_RES_DISCOVERED)
		return 0;
	res->bar[bar].state = (unsigned char)TARGET_RES_CLAIMED;
	res->nr_claimed++;
	return 1;
}

/* Vuelve a DISCOVERED.  Sólo desde CLAIMED.  Devuelve lo que se liberó. */
static inline int target_res_mark_released(struct target_resources *res, int bar)
{
	if (bar < 0 || bar >= TARGET_NR_BARS)
		return 0;
	if (res->bar[bar].state != (unsigned char)TARGET_RES_CLAIMED)
		return 0;
	res->bar[bar].state = (unsigned char)TARGET_RES_DISCOVERED;
	if (res->nr_claimed)
		res->nr_claimed--;
	return 1;
}

/* ¿todas las ranurasCLAIMED Released?  usable como aserción de unwind. */
static inline int target_res_all_released(const struct target_resources *res)
{
	int i;

	for (i = 0; i < TARGET_NR_BARS; i++)
		if (res->bar[i].state == (unsigned char)TARGET_RES_CLAIMED)
			return 0;
	return 1;
}

#endif /* TARGET_RESOURCE_H */
