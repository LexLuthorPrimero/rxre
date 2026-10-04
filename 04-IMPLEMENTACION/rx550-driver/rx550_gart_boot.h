/* SPDX-License-Identifier: GPL-2.0 */
/*
 * rx550_gart_boot.h — LA SECUENCIA COMPLETA, encadenada.
 *
 * Que es
 *   La unica funcion del componente que hace las seis cosas del arranque del
 *   GART EN ORDEN, y que se puede ejecutar entera sin GPU contra un mapa de
 *   userspace.  Antes existian las seis piezas y ninguna las encadenaba:  cada
 *   una se probaba por separado y el orden entre ellas no estaba escrito en
 *   ninguna parte, con lo que un cambio de orden no rompia ningun test.
 *
 * Que NO es
 *   No es un sustituto del takeover.  No pide el bus, no mapea la BAR, no llama
 *   a pci_enable_device.  Toma un mapa YA RESUELTO y una geometria YA LEIDA, y
 *   hace lo que se hace con ellos.
 *
 * EL ORDEN, y de donde sale cada paso
 *   1. reservar la tabla de la GART en VRAM      amdgpu_gart.c:263-278
 *   2. rellenarla con el valor de entrada         amdgpu_gart.c:276
 *   3. calcular la geometria                      amdgpu_gmc.c:294-336
 *   4. construir el plan de escrituras            gmc_v8_0.c:829-946
 *   5. aplicarlo al mapa                          el mismo
 *   6. vaciar la TLB del contexto 0              gmc_v8_0.c:941
 *
 *   El paso 6 va ULTIMO por una razon que no es de estilo:  la invalidacion
 *   tiene que ocurrir DESPUES de programar la tabla, no antes.  Invalidate antes
 *   y luego escribir la tabla deja la TLB con las entradas viejas de la tabla
 *   vieja, que es exactamente el fallo que la invalidacion evita.  El corpus lo
 *   hace en ese orden y con el mismo argumento en gmc_v8_0.c:301-303.
 *
 * EL INFORME, y por que es una estructura y no un int
 *   MEDIDO 2026-10-04: rx550_gart_apply() tiene un informe con 9 verificaciones
 *   y 25 no verificables, y su propia cabecera dice que "un apply que reporta
 *   25 fallos y 9 aciertos sobre un GART bien programado no es util para
 *   diagnosticar nada".  Un int de retorno tiene el mismo problema:  no dice
 *   DONDE se paro.  Este informe dice en que paso, con el codigo de ese paso, y
 *   que pasos se completaron antes.  Un fallo que no dice donde se fallo obliga
 *   a recompilar con printf, que es el ciclo que el proyecto ya paga.
 */
#ifndef RX550_GART_BOOT_H
#define RX550_GART_BOOT_H

#include "rx550_mmio_access.h"
#include "rx550_gart_seq.h"
#include "rx550_gart_table.h"
#include "rx550_gart_geom.h"
#include "rx550_vram.h"
#include "rx550_vram_pool.h"
#include "rx550_dummy_page.h"

/* NUMERO DE PASOS.  El informe lo declara, para que un consumidor pueda
 * contar por donde llego sin conocer la lista. */
enum rx550_gart_boot_step {
	RX550_GART_BOOT_PRESENTE = 0,	/* nada hecho todavia  */
	RX550_GART_BOOT_RESERVA,	/* 1  la tabla tiene sitio  */
	RX550_GART_BOOT_RELLENO,	/* 2  la tabla tiene valor  */
	RX550_GART_BOOT_GEOMETRIA,	/* 3  ventana decideda     */
	RX550_GART_BOOT_PLAN,		/* 4  plan construido      */
	RX550_GART_BOOT_APLICADO,	/* 5  plan escrito         */
	RX550_GART_BOOT_VACIO_TLB,	/* 6  TLB invalidada       */
	RX550_GART_BOOT_LISTO,		/* los seis completos     */
	RX550_GART_BOOT_NR_PASOS
};

enum rx550_gart_boot_err {
	RX550_GART_BOOT_OK = 0,
	RX550_GART_BOOT_ERR_NULO,		/* falta un argumento   */
	RX550_GART_BOOT_ERR_VRAM,	/* el pool no dio sitio  */
	RX550_GART_BOOT_ERR_RELLENO,	/* no se pudo rellenar   */
	RX550_GART_BOOT_ERR_GEOMETRIA,	/* geometria no valida   */
	RX550_GART_BOOT_ERR_PLAN,	/* el plan no se construye*/
	RX550_GART_BOOT_ERR_APLICAR,	/* fallo dentro de apply */
	RX550_GART_BOOT_ERR_VACIO_TLB	/* fallo en el flush     */
};

/* Lo que hay que brings.  Todo por valor explicito:  esta funcion no lee
 * registros, no consulta parametros de modulo y no tiene estado global. */
struct rx550_gart_boot_req {
	const struct rx550_mmio_map	*map;

	/* El allocator y la base de CPU de la ventana VRAM.  El pool da
	 * OFFSETS;  la base es lo que los convierte en punteros. */
	struct rx550_vram_pool		*pool;
	uint64_t			 vram_base_cpu;	/* VA de la ventana */

	/* La pagina de relleno.  La secuencia la escribe en dos registros
	 * PROTECTION_FAULT_DEFAULT_ADDR como PA de SISTEMA, y lo que va al
	 * campo PHYSICAL_PAGE_NUMBER es su >> 12, que es lo que produce
	 * rx550_dummy_page_pfn().  Aqui entra la PA entera, que es lo que el
	 * resto del componente ya usa. */
	uint64_t			 dummy_page_addr;

	/* Geometria de la ventana del GART.  La PRODUCE
	 * rx550_gart_geometry(), que es puro;  aqui entra ya decidida porque
	 * esta funcion es el consumidor, no el productor. */
	uint64_t			 gart_start;
	uint64_t			 gart_end;

	/* Los dos parametros sin PRODUCTOR todavia.  MEDIDO: ningun codigo del
	 * componente los rellena desde una medicion,  y son de los que salen
	 * PAGE_TABLE_BLOCK_SIZE, BANK_SELECT y L2_CACHE_BIGK_FRAGMENT_SIZE.
	 * Van declarados MODELO y no MEDIDO,  no como dato. */
	uint32_t			 block_size;		/* MODELO */
	uint32_t			 fragment_size;		/* MODELO */
	uint32_t			 max_pfn;		/* MODELO */

	/* La direccion GPU de la tabla.  La calcula el pool, no el llamante:
	 * tabla_gpu_offset = vram_base_gpu + res.offset.  Aqui solo hace
	 * falta la parte de GPU,  que es lo que va a PAGE_TABLE_BASE. */
	uint64_t			 vram_base_gpu;

	unsigned			 vmid;		/* el del flush */
};

/* Lo que paso.  Escribirse entero ANTES de empezar,  para que un informe de
 * un fallo tenga tambien lo que si funciono. */
struct rx550_gart_boot_report {
	enum rx550_gart_boot_step	ultimo_paso;
	enum rx550_gart_boot_err	err;

	/* El codigo del paso que fallo,  tal cual lo devolvio el.  Un informe
	 * que colapsa los motivos es el defecto que este commit dice evitar. */
	int				rc_del_paso;

	struct rx550_vram_resource	res;
	uint64_t			 tabla_gpu_offset;
	struct rx550_gart_tabla_geom	tabla_geom;
	struct rx550_gart_geom		geom;
	struct rx550_gart_seq		seq;
	struct rx550_gart_apply_report	apply;
	uint32_t			 plan_len;
};

/* La secuencia entera.  Devuelve RX550_GART_BOOT_OK solo si los SEIS pasos
 * completos.  Ante cualquier fallo, `out` conserva en que paso se paro y con
 * que codigo, y NO se deshace lo que ya se habia hecho:  las reservas y las
 * escrituras previas se quedan, y `out` lo dice con `ultimo_paso`.  Deshacer
 * seria un séptimo paso que el corpus tampoco hace. */
int rx550_gart_boot(const struct rx550_gart_boot_req *req,
		    struct rx550_gart_boot_report *out);

#endif /* RX550_GART_BOOT_H */