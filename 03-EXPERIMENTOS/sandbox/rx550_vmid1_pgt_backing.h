/* SPDX-License-Identifier: GPL-2.0-only */
/*
 * rx550_vmid1_pgt_backing.h — la propiedad fisica del PGT de VMID1.
 *
 *   TARGET = RX 550 instalada en esta maquina  (1002:699F, Polaris12, GFX8)
 *   SCOPE  = EXCLUSIVO
 *
 * QUE ES
 *   El objeto que POSEE la memoria del PGT y conoce sus direcciones.  Toma la
 *   geometria que ya calculo rx550_vmid1_geometry() y produce, para el nodo
 *   siguiente, exactamente dos cosas:  la direccion DMA del root, y la
 *   direccion DMA de cada pagina PTE.
 *
 * QUE NO ES
 *   No calcula geometria.  No la duplica, no la re-deriva y no la corrige:
 *   la CONSUME, y si no es valida no reserva nada.  Esa es la frontera que
 *   importa, porque duplicar la aritmetica seria el modo de que las dos copias
 *   diverjan sin que nadie lo note.
 *   No programa PAGE_TABLE_BASE_ADDR, ni START/END, ni CNTL, ni la apertura.
 *   No escribe MMIO.  No hay ioremap, ni readl, ni writel, ni ring.
 *   No invalida TLB.  No implementa fences.  No construye un allocator de GPU
 *   VA.  No toca GEM, ni TTM, ni GART.
 *
 * ─────────────────────────────────────────────────────────────────────────────
 * LA SEPARACION DE DIRECCIONES, Y POR QUE NO ES ESTETICA
 * ─────────────────────────────────────────────────────────────────────────────
 *
 *   Hay CUATRO direcciones y este subsistema usa TRES distintas:
 *
 *     kernel virtual   lo que se escribe        el driver, para poblar
 *     dma_addr_t       lo que se programa        el walker: root y hojas
 *     GPU VA           lo que se traduce         la GPU, para el IB
 *
 *   Y la cuarta, la PA de CPU, NO se usa:  con IOMMU no es la direccion que
 *   el dispositivo programa.  Ver BACKING_MECHANISM §H.
 *
 *   De las tres, este modulo conoce las dos primeras.  Y NO HAY NINGUNA
 *   FUNCION QUE CONVIERTA UNA EN OTRA, porque no existe conversion:  el
 *   subsistema DMA del kernel ya dio la direccion correcta en el momento de
 *   reservar, y recalcularla seria reintroducir el error.
 *
 *   Los dos validadores de representabilidad tambien son distintos, y no
 *   intercambiables:
 *
 *     root  28 bits de NUMERO DE PAGINA   PAGE_TABLE_BASE_ADDR
 *     hoja  campo 39:1 de DIRECCION       la entrada de directorio
 *
 *   Aplicar el del root a una hoja rechaza direcciones validas, y el error
 *   realista —una mascara de 28 bits sobre una direccion en bytes— esta
 *   cazado por el test T8 de M2.
 *
 * ─────────────────────────────────────────────────────────────────────────────
 * LA DECISION A / B, Y POR QUE NO ES UNA PREFERENCIA
 * ─────────────────────────────────────────────────────────────────────────────
 *
 *   PARA LAS HOJAS, la contiguidad NO es requisito del hardware.  El hardware
 *   direcciona cada hoja por su PDE, luego cada una lleva su propia direccion
 *   y no hace falta que sean contiguas.  Eso es un hecho del formato del PDE
 *   (gmc_v8_0.c:704-709), no una preferencia.
 *
 *   ASI QUE LA ELECCION ES DE IMPLEMENTACION, y se decide con los cinco
 *   criterios que se pueden comprobar:
 *
 *   1. SEMANTICA DEL HARDWARE      empate.   No exige contiguidad ni la
 *                                   prohibe.  Ningun criterio aqui.
 *   2. LIMITES DE DIRECCION        A pierde.   A exige que el rango ENTERO
 *                                   quepa bajo el bit 39; B no exige nada
 *                                   del conjunto.  Con la geometria maxima
 *                                   aceptada el rango son 8 MiB y cabe, luego
 *                                   hoy no muerde, pero es una restriccion
 *                                   real que B no tiene.
 *   3. FACILIDAD DE ROLLBACK       A gana.    Un solo free.  B necesita un
 *                                   bucle de hasta 1024 frees, y un bucle
 *                                   en el camino de error es donde se
 *                                       cuelgan los drivers.
 *   4. COMPLEJIDAD                A gana.    Una reserva, una liberacion, y
 *                                   el indice es un desplazamiento lineal.
 *   5. REPRODUCIBILIDAD           A gana.    El layout es determinista; con
 *                                   B depende de como reparta el allocator.
 *
 *   DECISION = A, una reserva coherente para todas las hojas.
 *
 *   Y B ESTA IMPLEMENTADO, con el mismo API, porque si A se elige por
 *   comodidad y no por requisito, la comodidad puede cambiar:  una plataforma
 *   que no de un rango contiguo de 8 MiB, o una geometria que lo crezca, y
 *   entonces B es un cambio de un campo y no una reescritura.
 *
 *   LO QUE ESTO NO ES:  contiguidad de hojas como requisito de hardware.  Es
 *   una eleccion de implementacion, registrada como tal, con la alternativa
 *   disponible.  Si alguien la lee como requisito, esta leyendo otra cosa.
 *
 *   Y LA PREGUNTA QUE SI TIENE RESPUESTA:  por que el ROOT si es contiguo y
 *   no se deja configurable?  Porque ahi no hay eleccion.  BASE es UNA base
 *   de 28 bits y el primer nivel se camina linealmente desde ella, luego el
 *   root tiene que ser UN rango.  Con block_size 10 son 2 paginas de 4 KiB, y
 *   tienen que ser adyacentes.  Eso es el registro, no una decision.
 */

#ifndef RX550_VMID1_PGT_BACKING_H
#define RX550_VMID1_PGT_BACKING_H

#include <stdint.h>
#include <stdbool.h>
#include <stddef.h>

#include "rx550_vmid1_pgt.h"

/* ═══════════════════════════════════════════════════════════════════════════
 * LA DIRECCION DMA, COMO TIPO
 *
 * No es un uint64_t.  Es un struct envoltorio, por la misma razon que
 * rx550_spaces.h:5-14 dice:  un entero desnudo no dice de que espacio viene,
 * y el mismo patron de bits significa cosas distintas segun donde se lea.
 *
 * Y NO es el dma_addr_t del kernel, para que este modulo no dependa de el y
 * siga compilandose en userspace.  La conversion esta en el backend del
 * kernel, en un solo sitio, y es una identidad de ancho.
 * ═══════════════════════════════════════════════════════════════════════════ */
struct rx550_dma_addr {
	uint64_t	value;
};

/* La CPU ve un puntero.  El tipo es void* a proposito:  este modulo no
 * escribe en el y no puede comprobar su tipo, y el backend garantiza la
 * coherencia.  Lo que SI se comprueba es que no sea NULL. */

/* ── la politica de hojas:  una decision, con su valor por defecto ──────────
 *
 * Se declara aqui y no se deduce, porque es el unico punto donde el
 * subsistema elige por comodidad en vez de por necesidad, y eso tiene que ser
 * visible en un solo sitio y no repartido por el codigo. */
enum rx550_pgt_leaf_policy {
	/* UN SOLO dma_alloc_coherent de leaf_count * leaf_bytes.
	 * Default.  Un free, indice lineal, layout determinista.
	 * Y la contiguidad NO es un requisito:  ver la politica alternativa. */
	RX550_PGT_LEAF_SINGLE_BLOCK = 0,
	/* UN dma_alloc_coherent por pagina.  1024 reservas y hasta 1024 frees.
	 * No impone ninguna restriccion de rango al conjunto, y existe para que
	 * la decision por defecto no sea una limitacion permanente. */
	RX550_PGT_LEAF_PER_PAGE     = 1,
};

/* ═══════════════════════════════════════════════════════════════════════════
 * EL BACKEND DE ASIGNACION
 *
 * Tres llamadas, inyectadas.  Es lo UNICO que separa este modulo del kernel,
 * y por eso son tres y no mas:  no hay una capa de asignacion generica, no hay
 * un allocator de VA, no hay un pool, no hay cache.
 *
 * Y la razon de que sea una tabla de funciones y no una llamada directa a
 * dma_alloc_coherent:  la geometria de M2 es aritmetica pura y se verifica
 * en userspace.  Un modulo que necesitase el kernel para probar una division
 * por 9 no se podria probar hasta que hubiera hardware, y para entonces la
 * geometria ya estaria en un ring.
 *
 * EL CONTRATO QUE EL BACKEND DEBE CUMPLIR, y que se comprueba al usable
 *
 *   · devuelve 0 y un par cpu/dma no NULOS, o un error y NO escribe nada
 *   · cpu y dma tienen el MISMO size
 *   · cpu es utilizable por el driver:  escribible, y coherente si el
 *     mecanismo lo es
 *   · dma es la direccion que el DISPOSITIVO programa, ya traducida por el
 *     IOMMU si lo hay
 *   · el rango [dma, dma+size) es utilizable por el dispositivo
 *
 * Y LO QUE NO SE ASUME, porque no lo garantiza ninguna de las tres llamadas:
 *   · que dos reservas consecutivas tengan direcciones consecutivas
 *   · que el rango entero quepa bajo el bit 39
 *   · que la memoria sea contigua mas alla de lo que el backend promise
 * ═══════════════════════════════════════════════════════════════════════════ */
struct rx550_pgt_alloc_ops {
	void	*ctx;
	/* size en bytes.  Devuelve 0 y escribe ambos punteros, o != 0 y no escribe nada. */
	int	(*alloc)(void *ctx, uint64_t size,
		       void **out_cpu, struct rx550_dma_addr *out_dma);
	/* size DEBE ser el mismo que se paso a alloc.  No se deduce de otra parte. */
	void	(*release)(void *ctx, uint64_t size,
			  void *cpu, struct rx550_dma_addr dma);
};

/* ═══════════════════════════════════════════════════════════════════════════
 * EL OBJETO DE BACKING
 *
 * Es el dueno de la memoria del PGT.  Y su unica regla de vida es la de §10:
 * no se destruye mientras el objeto exista.
 * ═══════════════════════════════════════════════════════════════════════════ */
struct rx550_pgt_backing {
	/* La geometria es PRESTADA, no poseida.  El objeto guarda un puntero y
	 * no una copia, y por eso hay una invariante dura:
	 *
	 *   la geometria pointed-to tiene que vivir mas que este objeto
	 *
	 * Que es la misma asimetria que rx550_vram.h:14-18 establecio para VRAM:
	 * si el backing guardara una copia mutable, el llamante podria cambiar
	 * la geometria sin que el backing se entere, y el indice y el tamaño
	 * allocado dejarian de corresponder.  Un puntero hace que eso sea un
	 * error de quien lo usa y no un fallo silencioso aqui. */
	const struct rx550_vmid1_geom	*geom;

	/* La tabla de asignacion, POR VALOR.  Copiarla evita que el llamante la
	 * modifique con el backing vivo. */
	struct rx550_pgt_alloc_ops	ops;

	enum rx550_pgt_leaf_policy	policy;

	/* ── ROOT ───────────────────────────────────────────────────────────── */
	struct rx550_vmid1_root		root;
	struct rx550_dma_addr		root_dma;
	bool				root_live;

	/* ── HOJAS ──────────────────────────────────────────────────────────── */
	uint32_t			leaf_count;	/* de la geometria */
	uint32_t			leaf_live;	/* cuantas estan reservadas */
	struct rx550_vmid1_pte_page	*leaves;	/* leaf_count entradas */
	/*
	 * ownership POR HOJA, y es un campo propio y no `leaves[i].attached`.
	 *
	 * La distincion no es academica, y la primera version de este modulo no
	 * la tenia.  `attached` lo pone rx550_vmid1_pte_page_attach(), y esa
	 * funcion puede FALLAR —o no llamarse— con la memoria ya reservada.  Si
	 * la liberacion mira `attached`, entonces una hoja cuya reserva funciono
	 * pero cuyo attach fallo NO se libera:  y una fuga que no aparece en
	 * ningun flag, sino como `frees != calls` muchisimo mas tarde.
	 *
	 * La regla es una sola:  la PROPIEDAD la establece la RESERVA que
	 * devuelve bien, y se baja en la liberacion.  attach no participa.
	 */
	uint8_t				*leaf_owned;	/* leaf_count entradas, 0 o 1 */
	struct rx550_dma_addr		*leaf_dma;	/* leaf_count entradas */
	/* Solo con RX550_PGT_LEAF_SINGLE_BLOCK:  la reserva unica de la que
	 * salen las leaf_count hojas, y su base. */
	void				*leaf_block_cpu;
	struct rx550_dma_addr		leaf_block_dma;
	uint64_t			leaf_block_bytes;

	/* ── CONTABILIDAD, para que el fallo sea diagnosticable y no opaco ─── */
	uint64_t			live_bytes;	/* lo que hay reservado ahora */
	uint32_t			alloc_calls;	/* quantas reservas se hicieron */
	bool				created;	/* hay algo que liberar */
};

/* ═══════════════════════════════════════════════════════════════════════════
 * ERRORES PROPIOS DE ESTE MODULO
 *
 * Los de M2 se reutilizan tal cual, porque la causa es la misma y duplicar un
 * numero con otro valor seria una segunda fuente de verdad.  Estos seis son de
 * aqui, y estan en la CABECERA y no en el .c porque un llamante tiene que
 * poder distinguirlos:  "el backend fallo" y "el backend devolvio una
 * direccion no representable" son fallos que llevan a sitios distintos.
 * ═══════════════════════════════════════════════════════════════════════════ */
#define RX550_PGTB_ERR_NO_OPS		(-101)	/* backend sin alloc o sin release */
#define RX550_PGTB_ERR_ALLOC		(-102)	/* el backend fallo al reservar    */
#define RX550_PGTB_ERR_BAD_INDEX	(-103)	/* indice de hoja >= leaf_count     */
#define RX550_PGTB_ERR_NOT_READY	(-104)	/* create no termino, o no existe   */
#define RX550_PGTB_ERR_LEAF_RANGE	(-105)	/* el rango entero no cabe en 39:1  */
#define RX550_PGTB_ERR_NOMEM		(-106)	/* sin memoria para los arrays      */

/* ═══════════════════════════════════════════════════════════════════════════
 * API
 *
 * Catorce funciones.  Todo lo que el nodo siguiente necesita, y nada mas.
 * ═══════════════════════════════════════════════════════════════════════════ */

/*
 * rx550_pgt_backing_create — reserva el PGT completo de una geometria dada.
 *
 * SECUENCIA, y el orden importa:
 *   1. comprueba la geometria ANTES de reservar nada
 *   2. reserva el root
 *   3. reserva las hojas
 *   4. valida cada direccion ANTES de engancharla
 *   5. inicializa a cero
 *
 * Y ante un fallo en el paso 3, libera lo del paso 3 anterior y lo del paso 2,
 * y devuelve error con el objeto en un estado que no frees ni liberara dos
 * veces.  Ver §9.
 *
 * Si geom es invalida, o vm_size no es lo que produce geom, NO SE RESERVA
 * NADA y se devuelve el error de la geometria.  Es la condicion que hace que
 * una ventana imposible no llegue a pedir memoria.
 */
int rx550_pgt_backing_create(struct rx550_pgt_backing *b,
			     const struct rx550_vmid1_geom *geom,
			     const struct rx550_pgt_alloc_ops *ops,
			     enum rx550_pgt_leaf_policy policy);

/* Libera todo lo que quede vivo.  Es idempotente por construccion:  la segunda
 * llamada no tiene nada que liberar y no toca el backend.  Ver B12. */
void rx550_pgt_backing_destroy(struct rx550_pgt_backing *b);

/* La direccion DMA del root, ya validada para PAGE_TABLE_BASE_ADDR. */
int rx550_pgt_backing_root_dma(const struct rx550_pgt_backing *b,
			       struct rx550_dma_addr *out);

/* El numero de pagina que se escribiria en PAGE_TABLE_BASE_ADDR.  Es el unico
 * punto donde la direccion del root se convierte en un valor de registro, y
 * usa el validador del ROOT, no el de la hoja. */
int rx550_pgt_backing_root_base_pn(const struct rx550_pgt_backing *b,
				   uint32_t *out_pn);

/* La direccion DMA de la hoja i, ya validada contra el campo 39:1. */
int rx550_pgt_backing_leaf_dma(const struct rx550_pgt_backing *b, uint32_t index,
			       struct rx550_dma_addr *out);

/* Codifica el PDE que apunta a la hoja i.  Une backing y encoder de M2 en el
 * punto donde se usan juntos, para que nadie tenga que compositionar a mano una
 * dma_addr con un pde_encode. */
int rx550_pgt_backing_encode_leaf_pde(const struct rx550_pgt_backing *b,
				      uint32_t index, uint64_t *out_pde);

/* La geometria que se uso, sin copia y sin conversion. */
const struct rx550_vmid1_geom *rx550_pgt_backing_geom(
	const struct rx550_pgt_backing *b);

/* Comprobaciones de invariante, para depurar y para testear.  No son
 * aserciones:  devuelven bool y el llamante decide. */
bool rx550_pgt_backing_is_complete(const struct rx550_pgt_backing *b);
bool rx550_pgt_backing_has_no_ownership(const struct rx550_pgt_backing *b);

/* ── el unwinding, expuesto para poder testearlo sin una reserva real ───────
 *
 * El test B8 necesita comprobar que un fallo a mitad de las hojas libera
 * todo.  Con SINGLE_BLOCK no hay fallo a mitad, porque hay una sola reserva;
 * asi que B8 se ejerce con PER_PAGE, y para eso hace falta poder pedirle al
 * objeto que libere lo que tiene.  Es la misma funcion que usa destroy, no
 * una segunda. */
void rx550_pgt_backing_release_all(struct rx550_pgt_backing *b);

/* Texto del error, incluidos los propios del backing.  No para logica. */
const char *rx550_pgt_backing_err_str(int rc);

/* ═══════════════════════════════════════════════════════════════════════════
 * INVARIANTES ESTATICAS
 *
 * Solo de REPRESENTACION.  Deliberadamente ninguna sobre cuantas hojas hay ni
 * sobre el tamano del root:  esos son DERIVADOS de la geometria, y ponerlos
 * aqui seria volver a hardcodear lo que M2 calcula.
 * ═══════════════════════════════════════════════════════════════════════════ */
_Static_assert(sizeof(struct rx550_dma_addr) == sizeof(uint64_t),
		"la direccion DMA no cabe en el tipo que la representa");
_Static_assert(offsetof(struct rx550_pgt_backing, root_dma)
	       > offsetof(struct rx550_pgt_backing, root),
		"la dma del root tiene que ir despues de su estructura");
_Static_assert(offsetof(struct rx550_pgt_backing, leaf_dma)
	       > offsetof(struct rx550_pgt_backing, leaves),
		"las dma de las hojas tienen que ir despues de las hojas");
_Static_assert(RX550_VMID1_BLOCK_SIZE_MIN
	       == RX550_VMID1_BLOCK_SIZE_DEMOSTRADO,
		"el minimo codificable deberia coincidir con el demostrado");

#endif /* RX550_VMID1_PGT_BACKING_H */
