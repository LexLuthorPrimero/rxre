/* SPDX-License-Identifier: GPL-2.0-only */
/*
 * target_match.h — contrato de identidad del dispositivo objetivo.
 *
 * PROPOSITO
 *   Regla de coincidencia EXCLUSIVA de la tarjeta objetivo, aislada del kernel
 *   para poder ejecutarse en tests sin hardware.
 *
 *   TARGET = RX 550 instalada en esta computadora
 *   SCOPE  = EXCLUSIVO
 *   OTHER GPUs = NO SOPORTADAS
 *
 *   La exclusividad es de Arquitectura, no una optimización futura. Este
 *   archivo no debe ganar parámetros, rangos ni comodines.
 *
 * ALCANCE DE LA API PCI (verificado, 7.1.3)
 *   drivers/pci/pci.h:459-469  pci_match_one_device()
 *       id_table expresa: vendor, device, subvendor, subdevice
 *       class_mask == 0  =>  no impone clase
 *       revision         =>  NO participa en el match del core
 *   mod_devicetable.h:44-50  struct pci_device_id no tiene campo de revisión.
 *   Por eso la revisión se verifica aquí y en probe(), no en la id_table.
 *
 * POR QUÉ CINCO CAMPOS Y NO UNO
 *   /usr/share/hwdata/pci.ids lista bajo el único device ID 0x699F al menos
 *   cinco tableros distintos (1028:1720, 1458:22f3, 148c:2380, 17aa:5069,
 *   1da2:e367). El device ID NO identifica la tarjeta.
 *
 * LO QUE ESTO NO AFIRMA
 *   Que la tupla de 5 campos sea única en el mundo. Eso es
 *   TARGET_MATCH_COMPLETENESS = NOT_DETERMINED: no hay evidencia local que lo
 *   refute ni que lo demuestre. Un segundo tablero con la misma tupla sería
 *   aceptado. Afinar exigiría identidad de placa (VBIOS), que es lectura de
 *   runtime no autorizada.
 */
#ifndef TARGET_MATCH_H
#define TARGET_MATCH_H

/* Identidad observada de la tarjeta objetivo, leída del sistema. */
#define TARGET_VENDOR			0x1002u
#define TARGET_DEVICE			0x699Fu
#define TARGET_SUBSYS_VENDOR		0x1002u
#define TARGET_SUBSYS_DEVICE		0x0B04u
#define TARGET_REVISION			0xC7u

/* Los 8 device IDs que el driver de referencia mapea a la misma ASIC
 * (CHIP_POLARIS12). Los ocho deben ser rechazados por este driver: la ASIC no
 * identifica la tarjeta. Se listan aquí sólo para el test de alcance. */
#define OTHER_POLARIS12_DEVICE_0	0x6980u
#define OTHER_POLARIS12_DEVICE_1	0x6981u
#define OTHER_POLARIS12_DEVICE_2	0x6985u
#define OTHER_POLARIS12_DEVICE_3	0x6986u
#define OTHER_POLARIS12_DEVICE_4	0x6987u
#define OTHER_POLARIS12_DEVICE_5	0x6995u
#define OTHER_POLARIS12_DEVICE_6	0x6997u
/* el octavo es TARGET_DEVICE (0x699f) */

/* Un device ID de otra familia presente en la tabla de referencia. */
#define UNRELATED_DEVICE_ID		0x67CCu

typedef unsigned int	t_u32;
typedef unsigned char	t_u8;

/*
 * target_match — ¿es ESTE dispositivo la tarjeta objetivo?
 *
 * Los cinco campos deben coincidir. Cualquier discrepancia rechaza.
 * No hay comodines, rangos, ni atajos por familia/ASIC.
 *
 * Usa tipos planos (t_u32/t_u8) para poder compilarse igual en kernel y en
 * el test de userspace sin includes condicionales.
 */
static inline int target_match(t_u32 vendor, t_u32 device,
			      t_u32 subsys_vendor, t_u32 subsys_device,
			      t_u8 revision)
{
	return vendor == TARGET_VENDOR			&&
	       device == TARGET_DEVICE			&&
	       subsys_vendor == TARGET_SUBSYS_VENDOR	&&
	       subsys_device == TARGET_SUBSYS_DEVICE	&&
	       (t_u32)revision == (t_u32)TARGET_REVISION;
}

/*
 * target_match_core_id — ¿coincide con lo que la id_table puede expresar?
 *
 * Es la parte que hace el PCI core antes de llamar a probe(). Sirve sólo
 * para poder afirmar en los tests que la puerta de probe() NO es la única
 * barrera, y para dejar explícito que la revisión no está cubierta aquí.
 */
static inline int target_match_core_id(t_u32 vendor, t_u32 device,
				       t_u32 subsys_vendor, t_u32 subsys_device)
{
	return vendor == TARGET_VENDOR		&&
	       device == TARGET_DEVICE		&&
	       subsys_vendor == TARGET_SUBSYS_VENDOR &&
	       subsys_device == TARGET_SUBSYS_DEVICE;
}

#endif /* TARGET_MATCH_H */
