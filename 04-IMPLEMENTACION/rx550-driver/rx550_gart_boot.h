/* SPDX-License-Identifier: GPL-2.0 */
/*
 * rx550_gart_boot.h — LA SECUENCIA COMPLETA, encadenada.
 *
 * Que es
 *   La unica funcion del componente que encadena los SIETE pasos que este
 *   proyecto se ha comprometido a hacer, EN ORDEN, y que se puede ejecutar
 *   entera sin GPU contra un mapa de userspace.  Antes existian las piezas y
 *   ninguna las encadenaba:  cada una se probaba por separado y el orden entre
 *   ellas no estaba escrito en ninguna parte, con lo que un cambio de orden no
 *   rompia ningun test.
 *
 * LO QUE ESTA SECUENCIA NO CUBRE,  Y POR QUE.  MEDIDO 2026-10-04.
 *
 * El titulo de este fichero decia "LA SECUENCIA COMPLETA"  y no lo era.  En el
 * camino de hardware ANTES de gmc_v8_0_gart_enable()  hay tres cosas mas que el
 * corpus escribe y esta secuencia no:
 *
 *   1. gmc_v8_0_init_golden_registers()   gmc_v8_0.c:1208,  called antes que
 *      gart_enable  (:1228).  Despacha golden_settings_polaris11_a11
 *      (:92-97  via :141-146  para CHIP_POLARIS12)  y escribe 4 registros:
 *      las mmVM_PRT_APERTURE{0..3}_LOW_ADDR  a 0x0fffffff.
 *
 *      POR QUE NO SE HACEN,  y no es "no nos ha dado tiempo":  son un
 *      DESHABILITADOR.  LOGICAL_PAGE_NUMBER es de 28 bits,  y con LOW puesto a
 *      0x0fffffff la ventana [LOW, HIGH) queda VACIA para cualquier HIGH
 *      posible,  porque HIGH > 0x0fffffff es imposible.  Es decir:  garantizar
 *      que PRT no cubre nada.  Y PRT es inalcanzable desde este driver  —exige
 *      el ioctl GEM_VA con AMDGPU_VM_PAGE_PRT,  y este componente no expone
 *      ioctls—,  asi que el estado del reset de esos cuatro registros es
 *      NOT_DETERMINED  y por eso no se afirma ni que estan bien ni que estan mal.
 *      Los 4 registros SI estan declarados en la tabla,  con la columna conf
 *      diciendo que el corpus los escribe.  Finding 1034.
 *
 *   2. gmc_v8_0_mc_program()   la funcion esta en gmc_v8_0.c:433-499  y se
 *      llama en :1210.  MEDIDO:  21 escrituras  WREG32,  3 REG_SET_FIELD  y
 *      4 RREG32  en su cuerpo.  Incluye las tres
 *      mmMC_VM_SYSTEM_APERTURE_*  (:468-473),  que SI estan declaradas en
 *      nuestra tabla  —y con conf PROVEN,  porque el corpus las escribe—.  Esas
 *      tres SI las produce el driver de referencia y este componente NO  por
 *      decision de ambito:  son programacion de la MC,  no del GART.
 *
 *      MEDIDO que mi primera version de este parrafo decia "las tres
 *      mmMC_VM_SYSTEM_APERTURE_*,  que SI estan declaradas en nuestra tabla
 *      (:899-901)".  Las lineas 899-901  son las TRES de
 *      mmVM_L2_CONTEXT1_IDENTITY_APERTURE_*  y del OFFSET,  que son registros
 *      DISTINTOS y que el plan de 34 si incluye.  Las de SYSTEM_APERTURE estan
 *      en 468-473.  Dos familias parecidas,  mismo prefijo de dominio,  y el
 *      numero de linea equivocado en un comentario.  Se comprueba toda cita que
 *      se escriba,  aunque sea en un comentario.
 *
 *   3. gmc_v8_0_polaris_mc_load_microcode()   :1221.  Carga de firmware,  y no
 *      tiene nada que ver con el page table.
 *
 * O sea que el alcance REAL es "la secuencia del GART",  no "el arranque del
 * chip".  Un lector que tomase el titulo al pie de la letra buscaria las 4
 * escrituras golden y las 46 de mc_program,  y no las encontraria.
 * Y este parrafo se puede contrastar:  las seis lineas de la lista son
 * archivo:linea del corpus,  no una resumen.
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
#include "rx550_vm_geom.h"

/* NUMERO DE PASOS.  El informe lo declara, para que un consumidor pueda
 * contar por donde llego sin conocer la lista. */
enum rx550_gart_boot_step {
	RX550_GART_BOOT_PRESENTE = 0,	/* nada hecho todavia  */
	RX550_GART_BOOT_VM_GEOM,	/* 1  ventana de VM decidida */
	RX550_GART_BOOT_RESERVA,	/* 2  la tabla tiene sitio  */
	RX550_GART_BOOT_RELLENO,	/* 3  la tabla tiene valor  */
	RX550_GART_BOOT_GEOMETRIA,	/* 4  ventana del GART      */
	RX550_GART_BOOT_PLAN,		/* 5  plan construido      */
	RX550_GART_BOOT_APLICADO,	/* 6  plan escrito         */
	RX550_GART_BOOT_VACIO_TLB,	/* 7  TLB invalidada       */
	RX550_GART_BOOT_LISTO,		/* los siete completos    */
	RX550_GART_BOOT_NR_PASOS
};

/* MEDIDO 2026-10-04.  ESTE ENUM NO ES EL ORDEN DE EJECUCION, y el comentario de
 * arriba  ("ORDEN ASCENDENTE")  se refiere al indice, no a la secuencia.
 *
 * El orden real, medido por las asignaciones de ultimo_paso en el .c:
 *
 *     VM_GEOM = 1     <- se ejecuta el 1
 *     RESERVA = 2     <- se ejecuta el 3
 *     RELLENO = 3     <- se ejecuta el 4
 *     GEOMETRIA = 4   <- se ejecuta el 2
 *     PLAN = 5, APLICADO = 6, VACIO_TLB = 7
 *
 * O sea que ultimo_paso recorre 1 -> 4 -> 2 -> 3 -> 5 -> 6 -> 7, que NO es
 * monótono.  La geometria va antes que la reserva porque  gart_end - gart_start + 1
 * se usa para dimensionar la tabla  (rx550_gart_table.c)  y una ventana al reves
 * daria un numero gigante:  eso fue un BUG DE ORDEN mio, corregido, y el
 * comentario esta en el .c.
 *
 * POR QUE EL ENUM NO SIGUE AL ORDEN.  Porque el ORDEN cambia con las
 * dependencias  —que es exactamente lo que/passó aqui—  y reenumerar el enum
 * rompe todo consumidor que guarde el numero.  El enum nombra pasos  (que son
 * estables)  y el .c los ordena.  Duplicarlos seria una lista mas que
 * desincronizar.
 *
 * CONSECUENCIA, Y ES LA QUE IMPORTA:  ultimo_paso es una ETIQUETA de donde se
 * paro,  NO un contador de progreso.  Un consumidor que quiera "cuantos pasos
 * he hecho" tiene que contar Los pasos ella,  comparando con el ultimo_paso
 * conocido y no restando. */

enum rx550_gart_boot_err {
	RX550_GART_BOOT_OK = 0,
	RX550_GART_BOOT_ERR_NULO,		/* falta un argumento   */
	RX550_GART_BOOT_ERR_VM_GEOM,	/* la ventana de VM no sale */
	RX550_GART_BOOT_ERR_VRAM,	/* el pool no dio sitio  */
	RX550_GART_BOOT_ERR_RELLENO,	/* no se pudo rellenar   */
	RX550_GART_BOOT_ERR_GEOMETRIA,	/* geometria no valida   */
	RX550_GART_BOOT_ERR_PLAN,	/* el plan no se construye*/
	RX550_GART_BOOT_ERR_APLICAR,	/* fallo dentro de apply */
	RX550_GART_BOOT_ERR_VACIO_TLB	/* fallo en el flush     */
};

/* Lo que hay que brings.  Todo por valor explicito:  esta funcion no lee
 * registros, no consulta parametros de modulo y no tiene estado global.
 *
 * Ni siquiera la RAM:  eso entra como un numero en `req->vm.ram_gb`,  y quien
 * lo lee de /proc/meminfo es el llamante.  La frontera es la misma que en
 * rx550_gart_geom.h:  la aritmetica es pura y aqui;  la lectura del mundo es
 * alla.  Una secuencia que leyera /proc/meminfo no seria testeable en
 * userspace,  y esta si lo es. */
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

	/* MEDIDO 2026-10-04, CORREGIDO.  Este struct llevaba block_size,
	 * fragment_size y max_pfn marcados MODELO,  y no habia NINGUN codigo de
	 * produccion que los rellenara:  estaban escritos a mano en tres fixtures
	 * de test.  Era el unico sitio del componente donde se podia estar
	 * inventando un valor,  y no estaba en la tabla de campos:  estaba en el
	 * BORDE entre la tabla y el constructor del plan.
	 *
	 * Ahora NO SE PUEDEN PASAR.  Entra lo que rx550_vm_geom_in necesita —la
	 * RAM y los tres overrides—  y la secuencia llama a rx550_vm_geometry(),
	 * que es puro,  igual que hace con rx550_gart_geometry().  Un numero sin
	 * productor deja de ser representable en la frontera,  y eso es mas fuerte
	 * que escribir en el comentario que no hay que inventarlo:  una comentario
	 * se puede saltarse sin que nada se entere.
	 *
	 * El porque de que block_size = 10 no dependa de esta maquina,  y del
	 * barrido que lo demuestra,  esta en rx550_vm_geom.c.  Aqui no se repite. */
	struct rx550_vm_geom_in		 vm;

	/* La direccion GPU de la tabla.  La calcula el pool, no el llamante:
	 * tabla_gpu_offset = vram_base_gpu + res.offset.  Aqui solo hace
	 * falta la parte de GPU,  que es lo que va a PAGE_TABLE_BASE. */
	uint64_t			 vram_base_gpu;

	unsigned			 vmid;		/* el del flush */
};

/* Lo que paso.  Escribirse entero ANTES de empezar,  para que un informe de
 * un fallo tenga tambien lo que si funciono. */
/* Los bits de `geom_campos`.  UN BIT POR CAMPO,  y el nombre lleva el MISMO
 * nombre que el campo  —para que un hueco en la mascara se vea mirando el
 * campo,  y no leyendo un numero—. */
#define RX550_BOOT_GEOM_GART_START	(1u << 0)
#define RX550_BOOT_GEOM_GART_END	(1u << 1)
#define RX550_BOOT_GEOM_TAMANO		(1u << 2)
#define RX550_BOOT_GEOM_CLAMPED		(1u << 3)
/* Los cuatro que esta secuencia NO rellena.  Se declaran para poder escribir su
 * nombre en el informe,  de modo que la lista de lo que falta sea legible y no
 * un 7. */
#define RX550_BOOT_GEOM_MAX_MC_ADDRESS	(1u << 4)
#define RX550_BOOT_GEOM_FB_END		(1u << 5)
#define RX550_BOOT_GEOM_SIZE_BELOW	(1u << 6)
#define RX550_BOOT_GEOM_SIZE_ABOVE	(1u << 7)
/* Los TRES que esta secuencia produce.  MEDIDO:  el bit de CLAMPED NO va aqui,
 * porque clamped lo decide rx550_gart_geometry()  —el PRODUCTOR—  y esta
 * funcion es su CONSUMIDORA:  recibe la ventana ya decidida.  O sea que la
 * secuencia produce tres  y recibe uno,  y el nombre de la mascara lo dice. */
#define RX550_BOOT_GEOM_PRODUCIDOS	(RX550_BOOT_GEOM_GART_START | \
					 RX550_BOOT_GEOM_GART_END | \
					 RX550_BOOT_GEOM_TAMANO)
/* Y el bit que recibe del productor,  declarado para que un consumidor pueda
 * decir "clamped lo puso el de al lado"  y no suponerlo. */
#define RX550_BOOT_GEOM_DEL_PRODUCTOR	RX550_BOOT_GEOM_CLAMPED

struct rx550_gart_boot_report {
	enum rx550_gart_boot_step	ultimo_paso;
	enum rx550_gart_boot_err	err;

	/* El codigo del paso que fallo,  tal cual lo devolvio el.  Un informe
	 * que colapsa los motivos es el defecto que este commit dice evitar. */
	int				rc_del_paso;

	struct rx550_vram_resource	res;
	uint64_t			 tabla_gpu_offset;
	struct rx550_vm_geom		vm_geom;
	struct rx550_gart_tabla_geom	tabla_geom;
	struct rx550_gart_geom		geom;

	/* QUE CAMPOS DE `geom` ESTAN REALMENTE RELLENOS.
	 *
	 * MEDIDO 2026-10-04.  Esta secuencia rellena TRES de los ocho campos de
	 * rx550_gart_geom  —gart_start, gart_end y gart_size_effective,  mas
	 * clamped—  y deja a CERO los cuatro derivados:
	 *
	 *     max_mc_address   fb_end   size_below   size_above
	 *
	 * Y no habia ninguna bandera que lo dijera.  Un consumidor que lea
	 * out->geom.size_below  ve un 0,  y no puede distinguir
	 *
	 *     "el hueco de ABAJO de la VRAM es de 0 bytes"      —imposible,  y por
	 *                                                          tanto un dato
	 *     "este campo no lo relleno esta secuencia"            corrupto
	 *
	 * Y en el corpus los cuatro son MEDICIONES REALES,  no ceros:
	 *     gmc_v8_0.c:1133  mc_mask       0xffffffffff
	 *     amdgpu_gmc.c      fb_end        fb_base + vram_bytes - 1
	 *     amdgpu_gmc.c      size_below    el hueco bajo la VRAM
	 *     amdgpu_gmc.c      size_above    el hueco alto,  alineado
	 *
	 * Los cuatro salen de rx550_gart_geometry(),  que es el PRODUCTOR y es
	 * puro.  Esta funcion es su CONSUMIDORA  —la ventana entra ya decidida,  que
	 * es el contrato de rx550_gart_boot.h—  y no puede rellenar lo que no ha
	 * calculado.
	 *
	 * QUE HAY QUE HACER CON ESTA MASCARA:  un consumidor que necesite los cuatro
	 * tiene que llamar al productor y usar SU salida.  Esta estructura no es el
	 * sitio.  Y la mascara lo dice,  en vez de dejar que un 0 parezca un dato.
	 */
	uint32_t			geom_campos;
	struct rx550_gart_seq		seq;
	struct rx550_gart_apply_report	apply;
	uint32_t			 plan_len;

	/* Un aviso, no un fallo.  MEDIDO: rx550_vm_geometry() puede devolver
	 * `degenerado` con el corpus avisando y continuando
	 * (amdgpu_vm.c:2454-2455).  Los numeros los deja tal cual para que no
	 * difieran de lo que veria el hardware,  y esto dice que el estado es
	 * raro.  Un informe que no lo dijera estaria callando un dato. */
	unsigned			 aviso;
};

/* La secuencia entera.  Devuelve RX550_GART_BOOT_OK solo si los SEIS pasos
 * completos.  Ante cualquier fallo, `out` conserva en que paso se paro y con
 * que codigo, y NO se deshace lo que ya se habia hecho:  las reservas y las
 * escrituras previas se quedan, y `out` lo dice con `ultimo_paso`.  Deshacer
 * seria un séptimo paso que el corpus tampoco hace. */
int rx550_gart_boot(const struct rx550_gart_boot_req *req,
		    struct rx550_gart_boot_report *out);

#endif /* RX550_GART_BOOT_H */