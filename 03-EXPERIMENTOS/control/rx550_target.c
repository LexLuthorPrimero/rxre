// SPDX-License-Identifier: GPL-2.0-only
/*
 * rx550_target — lifecycle mínimo del driver propio.
 *
 * SEGUNDO COMPONENTE. El primero fue la identidad; este es el esqueleto.
 *
 *     module_init → pci_register_driver → probe() → remove() → unregister → exit
 *
 * ALCANCE
 *   TARGET = RX 550 instalada en esta computadora.  SCOPE = EXCLUSIVO.
 *   Este driver NO es un driver de AMD, ni de GFX8, ni de Polaris12, ni de la
 *   familia RX 550.  La coincidencia es de 5 campos y no tiene comodines.
 *
 *   AMDGPU es EVIDENCIA, no ESPECIFICACIÓN.  No se copia su estructura de
 *   datos, ni su lifecycle, ni sus subsistemas.  No se crean abstracciones
 *   para GPUs futuras.
 *
 * ESTADO DE ALCANCE hardware (deliberadamente vacío)
 *   NO hay BAR, MMIO, DMA, IRQ, doorbell, ring, IB, fence, scheduler, VM,
 *   VRAM, GTT, firmware, power management ni ejecución de GPU.  El lifecycle
 *   no los necesita para demostrarse, y añadirlos ahora sería
 *   anticipación.  Se rigoriza AUDIT_HARDWARE_ACCESS más abajo.
 *
 * FIRMA DE probe()
 *   Verificada contra las cabeceras del kernel en ejecución:
 *     /usr/src/kernels/7.1.3-200.nobara.fc44.x86_64/include/linux/pci.h:1025
 *       int  (*probe)(struct pci_dev *dev, const struct pci_device_id *id);
 *       void (*remove)(struct pci_dev *dev);              (pci.h:1026)
 *       const struct pci_device_id *id_table;             (pci.h:1024)
 *   KERNEL_API_VERSION = VERIFIED
 */

#include <linux/module.h>
#include <linux/pci.h>
#include <linux/slab.h>
#include <linux/init.h>

#include "target_match.h"
#include "pci_resource.h"
#include "rx550_mmio_access.h"

/*
 * Estado software del dispositivo.
 *
 * pdev      ancla de propiedad: OWNER = driver,
 *           LIFETIME = probe() exitoso -> remove().
 * res       modelo de propiedad PCI (componente 4).
 *
 * CAMBIO DE ESTE COMPONENTE, y por que
 *   Se aniade UN campo, `res`, de tipo struct target_resources.
 *     - Conceptualmente pertenece al recurso, no a la identidad del objeto.
 *     - Se embebe en vez de allocarse aparte: una sola asignacion, un solo
 *       free, y por tanto un unico camino de fallo que desenrollar.  Un puntero
 *       anadiria un segundo punto de fallo sin consumidor que lo justifique.
 *     - La logica de recurso vive entera en pci_resource.c; este fichero
 *       queda acoplado solo a tres funciones, no a la maquinaria.
 *   No se ha modificado TARGET_MATCH ni la logica de probe()/remove().
 */
struct target_device {
	struct pci_dev		*pdev;
	struct target_resources	res;
	/*
	 * STATE 3.  `mmio` es el contrato del accessor; `map_base` es el
	 * puntero que DEVOLVIO pci_iomap().  Son dos cosas distintas a
	 * proposito: detach() opera sobre el mapa, y pci_iounmap() solo
	 * puede desmapear exactamente la asignacion que se hizo.  Si se
	 * derivara el puntero del mapa, no habria garantia de que sean el
	 * mismo.
	 */
	struct rx550_mmio_map	mmio;
	void			*map_base;
};

/*
 * id_table: sólo los 4 campos que la API PCI puede expresar.
 *
 *   vendor      0x1002
 *   device      0x699F
 *   subvendor   0x1002
 *   subdevice   0x0B04
 *
 * La REVISIÓN no tiene campo en struct pci_device_id
 * (mod_devicetable.h:44-50) ni participa en pci_match_one_device()
 * (drivers/pci/pci.h:459-469).  Por eso se verifica en probe().
 *
 * class/class_mask se dejan a 0: con class_mask == 0 el término de clase de
 * pci_match_one_device vale siempre 0, así que no imponen ninguna clase.
 * La entrada terminadora { } es obligatoria: el core itera mientras
 * vendor || subvendor || class_mask sea distinto de cero.
 */
static const struct pci_device_id rx550_target_id_table[] = {
	{
		.vendor    = TARGET_VENDOR,
		.device    = TARGET_DEVICE,
		.subvendor = TARGET_SUBSYS_VENDOR,
		.subdevice = TARGET_SUBSYS_DEVICE,
	},
	{ }
};

/*
 * probe — software únicamente.
 *
 * La puerta de 5 campos está AQUÍ, no antes. Que el core PCI haya filtrado
 * por vendor/device NO es motivo suficiente para aceptar: la revisión y los
 * subsistemas no están cubiertos por la id_table.
 */
/* ── MMIO_CAPABILITY ─────────────────────────────────────────────────────
 *
 * Sonda de investigación, NO capacidad funcional.  Default 0: sin este
 * parámetro, probe() no lee ningún registro y su comportamiento es el de
 * siempre.  Con 1, probe() ejecuta tres lecturas de diagnóstico y las
 * registra; no cambia ningún estado del dispositivo.
 *
 * Declarado ANTES de probe(), que es donde se usa.
 */
static int rx550_probe_read;
module_param(rx550_probe_read, int, 0);
MODULE_PARM_DESC(rx550_probe_read,
		 "1 = probe lee 3x mmGRBM_STATUS2 y registra rc/valor (instrumento, no función)");

/* mmGRBM_STATUS2, índice en BAR5.  Offset = índice * RX550_REG_WIDTH. */
#define RX550_PROBE_READ_INDEX	0x2002u

static int rx550_target_probe(struct pci_dev *pdev,
			       const struct pci_device_id *id)
{
	struct target_device *tdev;
	resource_size_t len;
	int rc;

	/* 1-3. contrato de cinco campos; cualquier discrepancia rechaza ANTES
	 *    de reservar nada. Un dispositivo rechazado no crea estado, no
	 *    llama a pci_set_drvdata() y no deja rastro.
	 */
	if (!target_match(pdev->vendor, pdev->device,
			  pdev->subsystem_vendor, pdev->subsystem_device,
			  pdev->revision)) {
		pci_err(pdev,
			"rechazado: identidad %04x:%04x sub %04x:%04x rev %02x no es la tarjeta objetivo\n",
			pdev->vendor, pdev->device,
			pdev->subsystem_vendor, pdev->subsystem_device,
			pdev->revision);
		return -ENODEV;
	}

	/* 4-5. crear e inicializar el estado. */
	tdev = kzalloc(sizeof(*tdev), GFP_KERNEL);
	if (!tdev)
		return -ENOMEM;

	tdev->pdev = pdev;
	target_res_init(&tdev->res);

	/*
	 * ERROR_UNWIND — tabla de estados.  Cada estado se libera SOLO si se
	 * alcanzó, y en orden inverso.  No hay cleanup ficticio.
	 *
	 *   STATE 0  sin recursos                            (inicial)
	 *   STATE 1  pci_enable_device()            DEFERRED  (componente MMIO)
	 *   STATE 2  region PCI reclamada         ACTIVO     (este componente)
	 *   STATE 3  mapeo MMIO                    ACTIVO     (este componente)
	 *   STATE 4  IRQ                             futuro
	 *
	 *   Regla: ONLY_RELEASE_SUCCESSFULLY_ACQUIRED_RESOURCES.
	 */
	target_res_discover(pdev, &tdev->res);

	/*
	 * El error de adquisicion se PROPAGA, no se colapsa.
	 *
	 * drivers/pci/pci.c:3786-3796 (7.1.3) documenta dos hechos que
	 * importan aqui:
	 *   - "Returns 0 on success, or %EBUSY on error."
	 *   - si pci_resource_len(pdev, bar) == 0 devuelve 0 (EXITO), no
	 *     error.  Por eso la guarda de target_res_claim_regions() exige
	 *     DISCOVERED antes de llamar: nunca se pide una BAR ausente.
	 *
	 * -EBUSY significa que otro driver posee la region.  En este host hoy
	 * ese otro driver es amdgpu, enlazado a 0000:01:00.0.  Eso es una
	 * precondicion de integracion, NO un fallo de identidad: reportarlo
	 * como -ENODEV lo hace indistinguible de "esta no es nuestra tarjeta",
	 * y tragarse el codigo es perder la causa.
	 */
	rc = target_res_claim_regions(pdev, &tdev->res);
	if (rc) {
		pci_err(pdev,
			"rechazado: BAR%d no se pudo adquirir: %d%s\n",
			TARGET_REG_BAR_INDEX, rc,
			rc == -EBUSY ? " (ya la posee otro driver)" : "");
		/* STATE 0 -> volver a STATE 0: no se adquirio nada. */
		kfree(tdev);
		return rc;
	}
	/* STATE 2 alcanzado.  Si un paso futuro fallara aqui, remove() ya
	 * es simetrico: liberaria exactamente la region que se reclamo.
	 */

	/* STATE 3.  Mapeo de la apertura de registros.
	 *
	 * La longitud es la DESCUBIERTA del recurso, no TARGET_REG_BAR_SIZE.
	 * La constante es el contrato; el recurso es el hecho.  Mapear la
	 * constante sobre un BAR mayor perderia el resto, y sobre uno menor
	 * pci_iomap() devuelve NULL.  Y length 0 mapearia el BAR entero, que
	 * no es lo que el contrato declara.
	 */
	len = tdev->res.bar[TARGET_REG_BAR_INDEX].len;
	tdev->map_base = pci_iomap(pdev, TARGET_REG_BAR_INDEX, len);
	if (!tdev->map_base) {
		pci_err(pdev,
			"rechazado: BAR%d no se pudo mapear (len %llu)\n",
			TARGET_REG_BAR_INDEX, len);
		/* -ENOMEM y no -ENODEV: la identidad ya se acepto arriba. */
		target_res_release(pdev, &tdev->res);
		kfree(tdev);
		return -ENOMEM;
	}

	/* El tamano lo comprueba attach AL ENLAZAR, no el primer acceso. */
	rc = rx550_mmio_attach(&tdev->mmio, tdev->map_base, len);
	if (rc) {
		pci_err(pdev,
			"rechazado: el mapa de BAR%d no cumple el contrato: %d\n",
			TARGET_REG_BAR_INDEX, rc);
		if (tdev->mmio.mapped)
			rx550_mmio_detach(&tdev->mmio);
		pci_iounmap(pdev, tdev->map_base);
		tdev->map_base = NULL;
		target_res_release(pdev, &tdev->res);
		kfree(tdev);
		return -EINVAL;
	}

	/* 6. asociar. Sólo después de aceptar, adquirir y mapear. */
	pci_set_drvdata(pdev, tdev);

	/* ── MMIO_CAPABILITY: sonda opt-in ───────────────────────────────────
	 *
	 * NO es una capacidad funcional del driver.  Es un instrumento de
	 * investigación: por defecto NO se lee nada, y probe() conserva
	 * exactamente su comportamiento sin este bloque.
	 *
	 * El registro es mmGRBM_STATUS2 (índice 0x2002, offset 0x8008), elegido
	 * porque es el único de BAR5 con lectura real previa demostrada en esta
	 * plataforma.  NO hay oráculo de valor: se registra el rc de cada
	 * llamada y el valor observado, y el veredicto se sostiene solo sobre
	 * los rc y sobre la reproducibilidad de las tres lecturas.
	 *
	 * R3 (bits reservados del registro a 0) queda DEFERRED: es una hipótesis
	 * sobre el valor, no un criterio.
	 */
	if (rx550_probe_read) {
		struct rx550_reg reg = rx550_reg_make(RX550_PROBE_READ_INDEX);
		uint32_t v1 = 0, v2 = 0, v3 = 0;
		int r1, r2, r3;

		r1 = rx550_mmio_read32(&tdev->mmio, reg, &v1);
		r2 = rx550_mmio_read32(&tdev->mmio, reg, &v2);
		r3 = rx550_mmio_read32(&tdev->mmio, reg, &v3);

		/*  R1 = r1==0 && r2==0 && r3==0    acceso ejecutado
		 *  R2 = v1==v2 && v2==v3           lectura repetible
		 *  No se exige ningún valor concreto.                        */
		pci_info(pdev,
			 "MMIO_CAP idx=0x%04x off=0x%08x rc=%d/%d/%d v=0x%08x/0x%08x/0x%08x R1=%d R2=%d\n",
			 RX550_PROBE_READ_INDEX,
			 RX550_PROBE_READ_INDEX * RX550_REG_WIDTH,
			 r1, r2, r3, v1, v2, v3,
			 (r1 == RX550_MMIO_OK && r2 == RX550_MMIO_OK &&
			  r3 == RX550_MMIO_OK),
			 (v1 == v2 && v2 == v3));
	}

	pci_info(pdev,
		"objetivo reconocido; BAR%d mapeada (%llu B) (sin IRQ)\n",
		TARGET_REG_BAR_INDEX, len);
	return 0;
}

/*
 * remove — simétrico a probe().
 *
 * Orden de salida = inverso al de entrada.  Hoy sólo hay un estado de
 * recurso, así que la simetría es de una regla, no de cuatro:
 *
 *     region PCI liberada        <- lo último adquirido, lo primero liberado
 *     (irq release)              <- futuro
 *     (mmio unmap)                <- futuro
 *     pci_disable_device()        <- futuro, DEFERRED
 *     asociación retirada
 *     estado liberado
 *
 * No se accede al hardware.  Si probe() no llegó a asociar estado, remove()
 * no debe asumir que existe: se comprueba antes de liberar.
 */
static void rx550_target_remove(struct pci_dev *pdev)
{
	struct target_device *tdev = pci_get_drvdata(pdev);

	if (!tdev)
		return;

	/* retirar la asociación antes de liberar */
	pci_set_drvdata(pdev, NULL);

	/* STATE 3 se desmonta ANTES que STATE 2, en orden inverso al de
	 * adquisición.  detach() sobre el mapa, y pci_iounmap() sobre el
	 * puntero que devolvió pci_iomap(), que es el único que garantiza
	 * desmapear exactamente lo que se mapeó.
	 */
	if (tdev->mmio.mapped)
		rx550_mmio_detach(&tdev->mmio);
	if (tdev->map_base) {
		pci_iounmap(pdev, tdev->map_base);
		tdev->map_base = NULL;
	}

	/* liberar SÓLO lo adquirido.  target_res_release recorre únicamente
	 * las ranuras CLAIMED (invariante I3).
	 */
	target_res_release(pdev, &tdev->res);

	kfree(tdev);

	pci_info(pdev, "lifecycle retirado\n");
}

/*
 * ERROR_UNWIND
 *   La ruta de error es proporcional al código real, que hoy es una sola
 *   asignación:
 *     - matching falla      → return -ENODEV, no se reservó nada
 *     - kzalloc falla       → return -ENOMEM, no se reservó nada
 *     - aceptación         → pci_set_drvdata, y remove() lo libera
 *   No hay fase parcial que deshacer; no se fabrica arquitectura de cleanup
 *   para un caso inexistente.  Si se añade una fase parcial, aquí se
 *   documenta y se deshace en orden inverso.
 */
/*
 * No se declara el sub-struct .driver embebido: pci_register_driver() ya
 * asigna  drv->driver.name = drv->name  y  drv->driver.bus = &pci_bus_type
 * (drivers/pci/pci-driver.c:1475-1476 en 7.1.3). Declararlo aquí exigiría
 * referenciar pci_bus, que no es visible desde <linux/pci.h>.
 *
 * module_pci_driver(x) == module_driver(x, pci_register_driver,
 *                                       pci_unregister_driver)
 * (include/linux/pci.h:1693-1694): aporta module_init/module_exit.
 */
static struct pci_driver rx550_target_pci_driver = {
	.name     = "rx550_target",
	.probe    = rx550_target_probe,
	.remove   = rx550_target_remove,
	.id_table = rx550_target_id_table,
};

module_pci_driver(rx550_target_pci_driver);

/*
 * AUDIT_HARDWARE_ACCESS
 *   Componente 4.  Se PERMITEN, y son esperadas, las APIs de propiedad:
 *     pci_request_region / pci_release_region / pci_resource_len / start
 *
 *   CAMBIO EN STATE 3, y se reporta aquí porque el propio bloque lo exige.
 *   pci_iomap y pci_iounmap han pasado de PROHIBIDAS a PERMITIDAS.  Razón:
 *   STATE 3 mapea la apertura de registros; sin ellas no hay mapa, y el
 *   contrato del accessor exige un mapa ya asignado.  Los tests que las
 *   listan como prohibidas fallan a proposito y hay que actualizarlos, no
 *   debilitar la comprobacion.
 *
 *   Se PROHIBEN, y se auditan sobre el fuente y sobre el .ko:
 *     ioremap, pci_enable_device, pci_request_regions,
 *     readl/writel/readq/writeq, dma_*, request_irq, doorbell, amdgpu.
 *   HARDWARE_RESOURCE_ACQUISITION = YES  (region BAR5)
 *   MMIO_MAPPING = YES (STATE 3: pci_iomap sobre BAR5, reversible con
 *   pci_iounmap y deshecho en el rollback de probe() y en remove())
 *   MMIO_ACCESS = NONE   IRQ = NONE   DMA = NONE   GPU_EXECUTION = NONE
 *   Mapear no es acceder: nada desreferencia el mapa todavia.  MMIO_ACCESS
 *   pasara a YES solo cuando exista una lectura o escritura real.
 *   Si alguna vez aparece una API prohibida, no se elimina sin reportar por qué.
 */
MODULE_LICENSE("GPL");
MODULE_DESCRIPTION("Lifecycle mínimo para la tarjeta objetivo RX 550 instalada (exclusivo)");
MODULE_AUTHOR("RX550-INVESTIGACION");
MODULE_VERSION("0.1");
