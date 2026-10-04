/* SPDX-License-Identifier: GPL-2.0 */
/*
 * rx550_pdb0.h — PDB0 (page directory block 0), UNA TABLA DE 2 MiB.
 *
 *   TARGET = RX 550 instalada en esta maquina
 *   SCOPE  = EXCLUSIVO
 *
 * ─────────────────────────────────────────────────────────────────────────────
 * D1 · LO QUE ESTE FICHERO DECIA, Y POR QUE ERA FALSO
 * ─────────────────────────────────────────────────────────────────────────────
 *
 * MEDIDO 2026-10-04.  La cabecera se llamaba a si misma "implementacion
 * CANONICA" y declaraba, bajo el epigrafe HARDWARE_REQUIREMENT, 512 entradas
 * con 2 MiB de cobertura.  En el MISMO .ko, compilados los dos por Makefile:30,
 * rx550_vmid1_pgt.c calcula el root de otra manera y sale otro numero.
 *
 *   aqui, con block_size = 9      ->  512 entradas, 2 MiB
 *   rx550_vmid1_pgt.c, ventana de 64 GiB  ->  16384 entradas, 64 GiB
 *
 * Factor 32 en el numero de entradas del root.  Y rx550_vmid1_pgt.h:45 ya lo
 * avisaba con todas las letras: "SI SE HARDCODEARA (1, 512, 512), EL CODIGO
 * SERIA INCORRECTO EN EL MOMENTO".  Alguien lo dejo escrito en dos ficheros
 * contiguos en lugar de quitarlo.
 *
 * QUE SE HIZO, Y POR QUE NO ES CAMBIAR UNA CONSTANTE
 *
 * Las dos cifras no compiten:  describen ventanas distintas.  Con block_size 9
 * la cobertura por tabla es 2 MiB y hacen falta 512 tablas para cubrir 1 GiB
 * (rx550_pdb0_tables_for());  con block_size 10 son 1024 entradas y 4 MiB por
 * tabla.  Ninguna de las dos es "el root":  una es una tabla.
 *
 * Asi que la pregunta "¿cual de las dos es el canonico?" estaba mal planteada,
 * y el trabajo no era cambiar 512 por 16384 —que habria hecho que este
 * componente administrara una ventana de 64 GiB sin decirlo— sino declarar el AMBITO
 * de cada uno.  Y eso es lo que hace el bloque de abajo.
 *
 * EL CRITERIO QUE SE USO, Y POR QUE ESTA DISPONIBLE
 *
 *   1. El hardware no fija un numero de entradas:  fija un CAMPO de 4 bits.
 *      PAGE_TABLE_BLOCK_SIZE = block_size - 9  (gmc_v8_0.c:933-934), luego el
 *      rango codificable es [9, 24] y 512 entradas es el valor del campo en
 *      CERO, no una cuenta permanente.  Este componente lo toma desde
 *      RX550_VMID1_BLOCK_SIZE_MIN, de modo que el 9 no puede cambiar en un
 *      sitio y no en el otro.
 *   2. El unico canonico del root de una VM es la DERIVACION a partir de la
 *      ventana, que es rx550_vmid1_geometry().  No tiene ningun numero
 *      escrito a mano:  todo sale de vm_size_bytes.
 *   3. Este componente no tiene ventana, no tiene vm_size y no tiene consumidor
 *      en el modulo.  No compite por el root.
 *
 * LO QUE NO SE HIZO, Y POR QUE
 *
 *   No se le dio a este componente el numero de entradas del root de una VM.
 *   Habria sido cambiar un ambito por otro sin decidir cual, que es el defecto
 *   con otro nombre.  Ver "LO QUE ESTA SIN DECIDIR", abajo.
 *
 * ─────────────────────────────────────────────────────────────────────────────
 * QUE ES
 *   Un directorio de paginas de 4 KiB con 512 entradas de 8 B, que cubren
 *   2 MiB.  Su contenido son entradas hoja que apuntan a memoria del sistema a
 *   traves de la ventana GART.
 *
 * QUE NO ES
 *   No es el root canonico de una VM:  ese lo deriva rx550_vmid1_pgt.c de la
 *   ventana, y para la ventana de 64 GiB de esta maquina da 16384 entradas.
 *   No es un allocator.  No tiene device.  No toca hardware.  No depende de
 *   ningun header del kernel: se compila y se testea fuera.
 *
 * LO QUE ESTA FIJADO POR HARDWARE
 *   page 4 KiB, entrada de 8 B, marca de hoja en el bit 54, direccion fisica
 *   de 40 bits.  Y el campo de 4 bits del que sale el numero de entradas.
 *
 * LO QUE NO ES UN HECHO DE HARDWARE, Y ESTA SEPARADO POR ESO
 *   512 entradas y 2 MiB.  Salen de tomar block_size = 9, que es el MINIMO
 *   codificable del campo, no el valor que el corpus escribe en esta ASIC
 *   (RX550_VMID1_BLOCK_SIZE_DEMOSTRADO = 10).  El numero de entradas es un
 *   PARAMETRO derivado de un campo, no una constante del silicio.
 *
 * LO QUE ES DECISION NUESTRA
 *   GART_START = 0, y por tanto GART_ADDRESS == SYSTEM_PA.
 *   No es un requisito del hardware.  Ver rx550_spaces.h.
 *
 * LO QUE NO SE MODELA, A PROPOSITO
 *   FRAG   NOT_DETERMINED   su semantica no esta en el corpus
 *   MTYPE  NOT_AVAILABLE    GFX8 no tiene ese campo
 *   TLB    DEFERRED_RUNTIME su comportamiento necesita el dispositivo
 *   ESTAS  NO SE INVENTAN
 *
 * POR QUE LA CREACION NO DEPENDE DE GPUVA
 *   El objeto existe porque hay un hueco VRAM donde escribir una tabla.  Las
 *   GPUVA que luego contenga son contenido, no precondicion de existencia.  Un
 *   nucleo sin shaders sigue necesitando la tabla.
 *
 * LO QUE ESTA SIN DECIDIR, Y NO SE ADIVINA
 *   Que papel tiene esta tabla de 2 MiB dentro del diseno.  No hay consumidor
 *   en el modulo —rx550_pdb0_* no se llama desde ningun .c que este en
 *   Makefile:30, solo desde su propio test— y sin consumidor no hay criterio
 *   para decidir si sobrevive como tabla de un subrange, si se absorbe en
 *   rx550_vmid1_pgt.c, o si se retira.  PROPIETARIO del cierre:  el nodo que
 *   integre el backing.  MIENTRAS TANTO no se le amplia el ambito ni se le
 *   cambia el numero.
 */
#ifndef RX550_PDB0_H
#define RX550_PDB0_H

#include "rx550_spaces.h"
#include "rx550_vmid1_pgt.h"	/* SOLO por RX550_VMID1_BLOCK_SIZE_MIN */
#include "rx550_vram.h"

/* Que esta cabecera depends de rx550_vmid1_pgt.h NO crea una dependencia
 * circular:  el include va en un punto ya protegido por su propio #ifndef, y
 * rx550_vmid1_pgt.h no incluye esta.  Y el simbolo que se toma es UNO, el
 * minimo codificable del campo, que es un hecho de hardware.  La dependencia
 * es de hardware, no de ambito:  los dos componentes siguen sin solaparse de
 * ambito, que es lo que el bloque de cabecera deja escrito. */

/* ── HARDWARE_REQUIREMENT ──────────────────────────────────────────────────
 * La pagina, la entrada, y el campo del que sale el numero de entradas.
 *
 * El numero de entradas NO es un HARDWARE_REQUIREMENT y por eso no esta aqui.
 * El hardware da un campo de 4 bits (gmc_v8_0.c:933-934,
 * PAGE_TABLE_BLOCK_SIZE = block_size - 9) y el numero de entradas es
 * 1 << block_size.  Ver el bloque MODEL_CHOICE de abajo. */
#define RX550_PDB0_ENTRY_SIZE	8u
#define RX550_PDB0_LEAF_BIT	54u
#define RX550_PDB0_LEAF		(UINT64_C(1) << RX550_PDB0_LEAF_BIT)

/* ── MODEL_CHOICE: EL block_size DE ESTA TABLA ─────────────────────────────
 *
 * MEDIDO 2026-10-04.  Este es el numero que replaces a un 512 escrito a mano,
 * y la razon por la que el 9 no vive aqui como un literal suelto.
 *
 * ESTE COMPONENTE USA EL MINIMO CODIFICABLE, 9.  No es el valor que el corpus
 * escribe en esta ASIC, que es 10 (RX550_VMID1_BLOCK_SIZE_DEMOSTRADO, derivado
 * de gmc_v8_0.c:1127 mas amdgpu_vm.c:2436-2466).  Se toma del MINIMO y no del
 * demostrado a proposito, y por dos razones que se pueden discutir por separado:
 *
 *   · Es el unico valor que NO depende de la ventana.  El 10 sale de una
 *     ventana de 64 GiB;  este componente no tiene ventana, asi que atarlo al
 *     10 seria atarlo a una ventana que no ha pedido.
 *   · Es el unico valor cuya consecuencia esta escrita y comprobada: 512
 *     entradas de 8 B son exactamente 4 KiB, o sea UNA pagina.  Con 10 serian
 *     1024 entradas y 8 KiB, o sea DOS paginas, y esta tabla pasaria a
 *     necesitar un bloque contiguo de 8 KiB en VRAM, que es una precondicion
 *     que rx550_pdb0_alloc() no sabe expresar con su `alignment`.
 *
 * ASI QUE EL 512 ES UNA DECISION DE MODELO CON SU CONSECUENCIA ESCRITA, no un
 * hecho del hardware con el nombre de hecho.  Y si algun dia esta tabla tiene
 * que cubrir mas, el numero se cambia aqui y en un test mas, no en dos sitios
 * que no se ven entre si.
 *
 * LO QUE ESTA LEYENDO:  el minimo codificable del campo, no una cuenta. */
#define RX550_PDB0_BLOCK_SIZE	RX550_VMID1_BLOCK_SIZE_MIN	/* 9 */

/* MODEL_CHOICE · derivado.  Los tres son consecuencia del anterior, y por eso
 * no se pueden cambiar por un lado y dejar el otro escrito a mano. */
#define RX550_PDB0_ENTRIES	(1u << RX550_PDB0_BLOCK_SIZE)		/* 512 */
#define RX550_PDB0_BYTES		(RX550_PDB0_ENTRIES * RX550_PDB0_ENTRY_SIZE)
#define RX550_PDB0_COVERAGE	((uint64_t)RX550_PDB0_ENTRIES * RX550_PAGE_SIZE)

/* ── flags activos ─────────────────────────────────────────────────────── */
/* Posiciones: HARDWARE_REQUIREMENT (amdgrtiene PTE_READABLE/WRITEABLE/VALID). */
/* Cual se pone: DESIGN_CHOICE.  Solo se activa lo que se puede justificar. */
#define RX550_PTE_VALID		(UINT64_C(1) << 0)
#define RX550_PTE_READABLE	(UINT64_C(1) << 5)
#define RX550_PTE_WRITEABLE	(UINT64_C(1) << 6)
/* FRAG, bits 7-11: NOT_DETERMINED.  No se tocan. */
/* MTYPE: NO EXISTE en GFX8.  No se inventa. */

enum rx550_pdb0_state {
	RX550_PDB0_EMPTY = 0,
	RX550_PDB0_ALLOCATED,
	RX550_PDB0_INITIALIZED,
	RX550_PDB0_PROGRAMMABLE,
	RX550_PDB0_RETIRED
};

struct rx550_pdb0 {
	enum rx550_pdb0_state		state;
	struct rx550_vram_resource	res;	/* PRESTADO, no poseido   */
	void			       *alloc_ctx;	/* contexto del allocator  */
	rx550_vram_free_fn		freefn;		/* para devolverlo        */
	uint64_t		       *entries;	/* area de staging del caller */
	uint32_t			owner;		/* quien puede mutar      */
	uint32_t			live_entries;
};

/* ── API ────────────────────────────────────────────────────────────────── */

void rx550_pdb0_init(struct rx550_pdb0 *p);

/* EMPTY -> ALLOCATED.  Toma un recurso PRESTADO por el allocator. */
int rx550_pdb0_alloc(struct rx550_pdb0 *p, void *alloc_ctx,
		     rx550_vram_alloc_fn allocfn, rx550_vram_free_fn freefn,
		     uint64_t alignment);

/* ALLOCATED -> INITIALIZED.  `entries` es memoria DEL CALLER: este objeto
 * no asigna, porque la politica de asignacion no es parte de su contrato. */
int rx550_pdb0_init_table(struct rx550_pdb0 *p, uint32_t owner,
			  uint64_t *entries);

int rx550_pdb0_open(struct rx550_pdb0 *p, uint32_t owner);

/* address = SYSTEM_PA.  La conversion a GART ocurre dentro, con GART_START. */
int rx550_pdb0_map_va(struct rx550_pdb0 *p, uint32_t owner,
		      struct rx550_gpuva va, struct rx550_system_pa pa,
		      bool writable);

int rx550_pdb0_unmap_index(struct rx550_pdb0 *p, uint32_t owner,
			   struct rx550_pdb0_index idx);

int rx550_pdb0_lookup(const struct rx550_pdb0 *p, struct rx550_pdb0_index idx,
		      uint64_t *out_entry);

int rx550_pdb0_destroy(struct rx550_pdb0 *p, uint32_t owner);

/* ── funciones puras, sin objeto ────────────────────────────────────────── */

uint64_t rx550_pdb0_encode(struct rx550_gart_addr gart, bool writable);
bool     rx550_pdb0_entry_valid(uint64_t e);
struct rx550_gart_addr rx550_pdb0_entry_addr(uint64_t e);
bool     rx550_pdb0_index_in_range(struct rx550_pdb0_index idx);
struct rx550_pdb0_index rx550_pdb0_index_for_va(struct rx550_gpuva va);
uint64_t rx550_pdb0_tables_for(uint64_t size_bytes);

#endif /* RX550_PDB0_H */
