// SPDX-License-Identifier: GPL-2.0
/*
 * nhwa — intervención mínima para el discriminante DOORBELL / WPTR-POLLING.
 *
 * Qué hace, y sólo esto:
 *
 *   kprobe(amdgpu_mm_wdoorbell)
 *       pre_handler
 *           adev = regs->di            (1er argumento, ABI SysV x86-64)
 *           validar asic_type == CHIP_POLARIS12
 *           *(u8 *)(adev + off) = val
 *           return 0                   (NO toca el instruction pointer)
 *
 * Por qué NO se salta el cuerpo de la función:
 * el objetivo es que la guarda que el propio driver ya escribió se encargue
 * de suprimir el write físico, no que el instrumento lo sustituya.
 *
 *     amdgpu_doorbell_mgr.c:61   if (amdgpu_device_skip_hw_access(adev))
 *     amdgpu_doorbell_mgr.c:62           return;
 *     amdgpu_doorbell_mgr.c:65   writel(v, adev->doorbell.cpu_addr + index);
 *
 * y amdgpu_device.c:822-847 muestra que amdgpu_device_skip_hw_access() es
 * exactamente `adev->no_hw_access` (el resto es solo aserciones LOCKDEP).
 *
 * En gfx_v8_0_ring_set_wptr_gfx() la publicación del WPTR (:6028) ocurre
 * ANTES del doorbell (:6029), así que la publicación queda intacta.
 *
 * FAIL-CLOSED:
 *   - si el argumento no pasa la validación de identidad PCI, no se escribe
 *     nada; cualquier otro dispositivo AMD es rechazado
 *   - si off != el valor verificado, el módulo no carga
 *   - si val no es 0 ni 1, el módulo no carga
 *   - cargar el módulo sin val=1 NO arma la intervención
 *
 * OFFSETS: NO se recalculan aquí. Vienen verificados contra el BTF del módulo
 * REALMENTE CARGADO (/sys/kernel/btf/amdgpu), no contra cabeceras ni contra el
 * árbol upstream del proyecto. El guard externo (P8) es el que aborta si el
 * valor real cambia.
 *
 * Autoría/propósito: instrumento de laboratorio para un experimento controlado.
 * No tiene usuarios fuera de este experimento, no se carga en producción y no
 * se debe instalar como parte del sistema.
 */

#include <linux/module.h>
#include <linux/kernel.h>
#include <linux/kprobes.h>
#include <linux/ptrace.h>
#include <linux/init.h>

#if !defined(CONFIG_X86_64)
#error "nhwa: verificado sólo para x86-64 (SysV, 1er argumento en RDI)"
#endif

/*
 * Identidad del dispositivo: coincidencia EXACTA con la tarjeta objetivo.
 *
 *   objetivo : 0000:01:00.0
 *              vendor           0x1002
 *              device           0x699f
 *              subsystem_vendor 0x1002
 *              subsystem_device 0x0b04
 *              revision         0xc7
 *              modalias  pci:v00001002d0000699Fsv00001002sd00000B04bc03sc00i00
 *
 * POR QUÉ LOS CINCO CAMPOS Y NO SÓLO vendor:device:
 *   el catálogo local /usr/share/hwdata/pci.ids lista bajo el ÚNICO device ID
 *   0x699f al menos cinco tableros distintos:
 *       1028:1720  Radeon RX 550X            (Dell)
 *       1458:22f3  Radeon RX 550 2GB         (Gigabyte)
 *       148c:2380  Lexa XL [Radeon RX 550]
 *       17aa:5069  Thinkpad E480/E580         (Lenovo)
 *       1da2:e367  Lexa PRO [Radeon RX 550]
 *   => device por sí solo NO identifica la tarjeta. La exclusividad es de
 *     Architecture, no una optimización: este instrumento no debe poder
 *      actuar sobre ninguna otra.
 *
 *   La revisión se incluye porque NO es derivable del device ID: el driver
 *   condiciona firmware con ASICID_IS_P23(did, rid) y el valor 0xc7 aparece
 *   ahí bajo did=0x6987, un device ID distinto.
 *
 *   asic_type NO es criterio de matching: ocho device IDs distintos mapean a
 *   CHIP_POLARIS12 en la tabla de amdgpu. Se usa sólo como corroboración
 *   interna, nunca como condición suficiente.
 *
 * OFFSETS, todos verificados contra el BTF del kernel EN EJECUCION:
 *
 *   struct amdgpu_device  (de /sys/kernel/btf/amdgpu, el modulo CARGADO)
 *       pdev         offset        8   struct pci_dev *
 *       asic_type    offset     1640   enum amd_asic_type, 4 bytes
 *       no_hw_access offset  381969   bool, 1 byte        = 0x5D411
 *
 *   struct pci_dev       (de /sys/kernel/btf/vmlinux)
 *       vendor           offset       60   u16
 *       device           offset       62   u16
 *       subsystem_vendor offset       64   u16
 *       subsystem_device offset       66   u16
 *       revision         offset       72   u8
 *
 *   enum amd_asic_type, del árbol del kernel EN EJECUCION:
 *       /usr/src/kernels/$(uname -r)/include/drm/amd_asic_type.h:49
 *       CHIP_POLARIS12 = 17
 *
 * El preflight (P8) vuelve a leer estos offsets y aborta si alguno cambió.
 * El módulo NO los recalcula ni los adapta.
 */
#define NHWA_TARGET_SYMBOL	"amdgpu_mm_wdoorbell"

/* identidad exacta de la tarjeta objetivo — constantes, no parámetros */
#define NHWA_PCI_VEN_ID		0x1002u
#define NHWA_PCI_DEV_ID		0x699fu
#define NHWA_PCI_SUB_VEN_ID	0x1002u
#define NHWA_PCI_SUB_DEV_ID	0x0b04u
#define NHWA_PCI_REVISION	0xc7u

#define NHWA_OFF_PDEV		8u		/* amdgpu_device.pdev          */
#define NHWA_OFF_PCI_VENDOR	60u		/* pci_dev.vendor              */
#define NHWA_OFF_PCI_DEVICE	62u		/* pci_dev.device              */
#define NHWA_OFF_PCI_SUB_VEN	64u		/* pci_dev.subsystem_vendor    */
#define NHWA_OFF_PCI_SUB_DEV	66u		/* pci_dev.subsystem_device    */
#define NHWA_OFF_PCI_REVISION	72u		/* pci_dev.revision            */
#define NHWA_OFF_ASIC_TYPE	1640u		/* amdgpu_device.asic_type     */
#define NHWA_ASIC_POLARIS12	17u

#define NHWA_OFF_NO_HW_ACCESS	0x5D411u

static struct kprobe nhwa_kp;

static unsigned int off = NHWA_OFF_NO_HW_ACCESS;
module_param(off, uint, 0444);
MODULE_PARM_DESC(off, "byte offset de no_hw_access dentro de struct amdgpu_device");

static int val;
module_param(val, int, 0444);
MODULE_PARM_DESC(val, "valor a escribir: 0 (desarma) o 1 (arma)");

/*
 * Hot path. Sin logging: un printk por doorbell ahogaría el anillo y
 * contaminaría la medición.
 *
 * El orden importa: se VALIDA antes de ESCRIBIR. Un `adev` que no sea el
 * dispositivo objetivo produce 0 escrituras, ni siquiera de 0.
 */
static int nhwa_pre(struct kprobe *p, struct pt_regs *regs)
{
	u64 adev = (u64)regs->di;
	u64 pdev;
	u16 vendor, device, sub_ven, sub_dev;
	u8 revision;
	u32 asic;

	if (!adev)
		return 0;

	pdev = *(u64 *)(adev + NHWA_OFF_PDEV);
	if (!pdev)
		return 0;

	/* TARGET_MATCH: coincidencia exacta, cinco campos */
	vendor = *(u16 *)(pdev + NHWA_OFF_PCI_VENDOR);
	device = *(u16 *)(pdev + NHWA_OFF_PCI_DEVICE);
	sub_ven = *(u16 *)(pdev + NHWA_OFF_PCI_SUB_VEN);
	sub_dev = *(u16 *)(pdev + NHWA_OFF_PCI_SUB_DEV);
	revision = *(u8 *)(pdev + NHWA_OFF_PCI_REVISION);

	if (vendor    != NHWA_PCI_VEN_ID     ||	/* 0x1002 */
	    device    != NHWA_PCI_DEV_ID     ||	/* 0x699f */
	    sub_ven   != NHWA_PCI_SUB_VEN_ID ||	/* 0x1002 */
	    sub_dev   != NHWA_PCI_SUB_DEV_ID ||	/* 0x0b04 */
	    revision  != NHWA_PCI_REVISION)	/* 0xc7  */
		return 0;

	/* corroboración interna; NO sustituye al match exacto */
	asic = *(u32 *)(adev + NHWA_OFF_ASIC_TYPE);
	if (asic != NHWA_ASIC_POLARIS12)
		return 0;

	*(u8 *)(adev + off) = (u8)val;
	return 0;
}

static int __init nhwa_init(void)
{
	int r;

	/* fail-closed en la carga: fuera de estos valores, no se registra nada */
	if (val != 0 && val != 1) {
		pr_err("nhwa: val debe ser 0 o 1 (recibido %d); no se carga\n",
		       val);
		return -EINVAL;
	}

	if (off != NHWA_OFF_NO_HW_ACCESS) {
		pr_err("nhwa: off debe ser 0x%X (recibido 0x%X); no se carga\n",
		       NHWA_OFF_NO_HW_ACCESS, off);
		return -EINVAL;
	}

	nhwa_kp.symbol_name = NHWA_TARGET_SYMBOL;
	nhwa_kp.pre_handler = nhwa_pre;

	r = register_kprobe(&nhwa_kp);
	if (r) {
		pr_err("nhwa: register_kprobe(%s) falló: %d\n",
		       NHWA_TARGET_SYMBOL, r);
		return r;
	}

	pr_info("nhwa: probe activo sobre %s, off=0x%X, val=%d\n",
		NHWA_TARGET_SYMBOL, off, val);
	return 0;
}

static void __exit nhwa_exit(void)
{
	/*
	 * NO se restaura no_hw_access aquí, a propósito.
	 *
	 * El byte pertenece a struct amdgpu_device, no al estado del módulo:
	 * rmmod NO garantiza no_hw_access == 0. El rollback es un ciclo
	 * controlado y explícito, documentado en preruntime.sh, y su
	 * verificación es COMPORTAMENTAL (amdgpu_test_ib vuelve a pasar).
	 */
	unregister_kprobe(&nhwa_kp);
	pr_info("nhwa: probe retirado. no_hw_access conserva el último valor escrito.\n");
}

module_init(nhwa_init);
module_exit(nhwa_exit);

MODULE_LICENSE("GPL");
MODULE_DESCRIPTION("nhwa: intervene no_hw_access via kprobe on amdgpu_mm_wdoorbell (lab instrument)");
MODULE_VERSION("0.1");
