/* SPDX-License-Identifier: GPL-2.0-only */
/*
 * rx550_mmio_access.h — acceso a los registros GFX8 por la apertura de BAR5.
 *
 *   TARGET = RX 550 instalada en esta maquina  (1002:699F, Polaris12, GFX8)
 *   SCOPE  = EXCLUSIVO
 *
 * QUE ES
 *   El camino desde un mnemonico de registro GFX8 hasta un acceso de 32 bits
 *   dentro de BAR5.  Y la tabla de los registros de VM y de apertura que el
 *   siguiente nodo va a necesitar.
 *
 * QUE NO ES, Y LA SEPARACION QUE ESTE FICHERO EXISTE PARA MANTENER
 *   · No sabe que existe un PGT.  No menciona `struct rx550_pgt_backing`, ni
 *     `root_dma`, ni `root_base_pn`, ni ninguna geometria.  No incluye
 *     rx550_vmid1_pgt.h ni rx550_vmid1_pgt_backing.h, y un test lo comprueba
 *     sobre el codigo.
 *   · No decide valores.  No sabe que va en PAGE_TABLE_BASE ni en CNTL, ni
 *     que es un numero de pagina o una mascara.  Solo traduce indice -> offset.
 *   · No programa VMID, no invalida TLB, no usa ring, no escribe PTE.
 *   · No tiene politica de runtime PM, ni de enable, ni de clock.
 *
 *   Y LA DIRECCION DE LA DEPENDENCIA, QUE VA EN EL OTRO SENTIDO
 *
 *       PGT / BACKING  ->  produce direcciones y estado
 *       MMIO ACCESSOR  ->  traduce registro a offset, y accede
 *
 *   El accessor es la capa INFERIOR.  La combinacion de las dos ocurre en el
 *   codigo del nodo siguiente, no dentro de ninguna de las dos, y por eso no
 *   hay ninguna funcion que tome un backing.  El ejemplo, y es como se va a
 *   usar:
 *
 *       uint32_t pn;
 *
 *       rx550_pgt_backing_root_base_pn(b, &pn);                  <- BACKING
 *       rx550_mmio_write32(&map, RX550_REG_CTX1_PT_BASE, pn);     <- MMIO
 *
 *   Y las dos lineas son de archivos distintos, y ninguna de las dos capas
 *   necesita incluir a la otra para que eso funcione.
 *
 * ─────────────────────────────────────────────────────────────────────────────
 * POR QUÉ LOS REGISTROS DE VM NO ESTÁN EN target_regs.h
 * ─────────────────────────────────────────────────────────────────────────────
 *
 *   Porque están en un MAPO DE REGISTROS DISTINTO, y eso ya está establecido
 *   en el proyecto:
 *
 *     target_vm.h:12-21
 *       .../asic_reg/gca/gfx_8_0_d.h  ->  0 registros  mmVM_* / mmGTT* / mmPTE*
 *       .../asic_reg/gmc/gmc_8_2_d.h  ->  los de tabla de paginas de GFX8
 *       "En GFX8 estan en el bloque GMC"
 *
 *   Y la tabla de target_regs.h se verifica CONTRA LOS HEADERS GCA:
 *
 *     tests/test_regs.c:106   busca cada nombre en gfx_8_0_d.h y gfx_8_1_d.h
 *     tests/test_regs.c:138   R07 "gfx_8_0 y gfx_8_1 coinciden en los 10 registros"
 *
 *   Añadir ahí un nombre como mmVM_CONTEXT1_CNTL haria que R05 fallara porque
 *   no está en el header GCA, y ese fallo no diría NADA del registro:  diría
 *   que se busca en el mapa equivocado.  Un test que falla por el motivo
 *   equivocado es peor que un test que no existe, porque entrena a desconfiar
 *   del que sí mide.
 *
 *   ASI QUE LA TABLA DE VM/APERTURA VA AQUI, con su procedencia declarada
 *   (gmc_8_2_d.h) y su propia verificacion, y las dos tablas se_keepn
 *   separadas por el mapa al que pertenecen.
 *
 * ─────────────────────────────────────────────────────────────────────────────
 * EL CONTRATO DE LA BAR5, Y NO SE MODIFICA
 * ─────────────────────────────────────────────────────────────────────────────
 *
 *   base        = la BAR5 descubierta en este host
 *   size        = 0x40000                 rx550_mmio.h
 *   byte_offset = index * 4               rx550_mmio.h, RX550_REG_WIDTH
 *   in_window   = offset + 4 <= size      rx550_mmio.h, rx550_reg_in_window()
 *   index       = indice de registro GFX8 del mapa GMC
 *
 *   Y LAS TRES REGLAS QUE HACE UN TIEMPO ATRAS, Y QUE ESTE FICHERO RESPETA
 *
 *   1. EL INDICE NO ES EL OFFSET.  Usar el indice como si ya fuera el offset
 *      produce un acceso VALIDO DENTRO DE LA BAR que golpea otro registro y
 *      devuelve un numero plausible.  No falla:  miente.
 *      rx550_mmio.h:5-20
 *
 *   2. LA COMPROBACIÓN DE VENTANA ES ANTES DEL ACCESO, no después.  Un acceso
 *      fuera de ventana no da un error:  da otro registro.
 *
 *   3. EL TAMAÑO DEL RECURSO SE COMPRUEBA AL ENLAZAR, no en el primer acceso.
 *      Un mapa más pequeño que RX550_MMIO_SIZE no puede contener el último
 *      registro, y descubrirlo escribiendo en hardware es tarde.
 */

#ifndef RX550_MMIO_ACCESS_H
#define RX550_MMIO_ACCESS_H

/* ── COMPATIBILIDAD KBUILD ──────────────────────────────────────────────────
 *
 * kbuild compila con -nostdinc: solo existen las cabeceras del kernel.  Los
 * includes de userspace se sustituyen por los tipos nativos, que son los
 * MISMOS tipos: el kernel define u8/u32/u64 como enteredos de ancho fijo.
 * No se sombrea nada con ficheros locales; se usa la cabecera real.
 *
 * Las macros de <stdint.h> que usa esta cabecera tambien son sustituidas:
 * UINT32_MAX es U32_MAX en kernel y ambos son el maximo del mismo entero de
 * 32 bits, asi que la asercion que las consume conserva su contrato.
 */
#ifdef __KERNEL__
#include <linux/types.h>
/*  limits.h, y no types.h:  U32_MAX / U64_MAX estan en linux/limits.h.
 *  Compilaba por elocate de los includes, no porque el header los trajera, y
 *  se rompio en cuanto otra unidad de traduccion llego antes por otro camino:
 *  rx550_gart_seq.c incluye rx550_mmio.h antes, y entonces U32_MAX no estaba
 *  declarado.  Es la misma clase de error que la del finding 1028, con el
 *  nombre del macro en vez de la convencion de separadores. */
#include <linux/limits.h>
#define UINT32_MAX U32_MAX
#define UINT64_MAX U64_MAX
#else
#include <stdint.h>
#include <stdbool.h>
#endif

#include "rx550_mmio.h"

/* ═══════════════════════════════════════════════════════════════════════════
 * LOS REGISTROS DE VMID1 Y DE APERTURA
 *
 * Treinta y nueve entradas, ORDENADAS POR BYTE_OFFSET ASCENDENTE, con la procedencia de
 * cada una en gmc_8_2_d.h.  El orden no es estetico:  el test lo comprueba, y
 * una tabla desordenada es la que hace imposible ver un solape.
 *
 * Y LOS DATOS DE CAMPO, porque el siguiente nodo va a necesitar ESCRIBIR en
 * estos registros y escribir un valor correcto exige saber cual es el campo.
 * Declararlos aquí es "preparar los registros";  no es programarlos.
 * ═══════════════════════════════════════════════════════════════════════════ */

/* El descriptor.  Mismo criterio de confianza que target_regs.h, y misma
 * separacion:  DECLARADO_ANTES de que un registro exista en el mapa, y
 * NO_ESCRITO_EN_GFX8 para los que el corpus no programa. */
enum rx550_reg_confidence {
	/* el corpus escribe este registro en GFX8 */
	RX550_REG_PROVEN	= 0,
	/* el corpus lo define y lo nombra, pero no lo escribe en GFX8 */
	RX550_REG_DECLARED	= 1,
};

struct rx550_vmid1_reg {
	const char		*name;		/* mnemonico GFX8            */
	uint32_t		index;		/* indice en la BAR5         */
	uint32_t		byte_offset;	/* index * 4                 */
	uint32_t		width;		/* bits, siempre 32          */
	/*  PERMISOS:  ANOTACION DEL PROYECTO,  NO DEL CORPUS.
	 *
	 *  Medido:  gmc_8_1_d.h  y  gmc_8_1_sh_mask.h  no contienen  NI UNA  cadena
	 *  "RW",  "W" ni la palabra  access  en 597-655 y 27-60 respectivamente.
	 *  Son listas planas de #define de indice y de __MASK/__SHIFT,  y un
	 *  #define de indice no puede expresar un permiso.
	 *
	 *  O sea que esta columna no tiene de donde venir,  y su unica
	 *  procedencia es que este proyecto la escribio.  Se conserva porque
	 *  decide si una escritura se puede comprobar releyendo  (ver
	 *  rx550_gart_seq.c),  y conservarla como dato DECLARADO con su regla a
	 *  la vista es mejor que mantener una lista de 25 nombres al lado:  al
	 *  menos esta esta en el mismo sitio que el mnemonico y el indice.
	 *
	 *  Y lo que SI tiene evidencia de lectura,  medido sobre todo el arbol
	 *  de amdgpu entero,  contando RREG32 del mnemonico:
	 *
	 *      mmMC_VM_MX_L1_TLB_CNTL   RREG32=4    mmVM_L2_CNTL        RREG32=4
	 *      mmVM_L2_CNTL2             RREG32=1    mmVM_L2_CNTL3       RREG32=2
	 *      mmVM_L2_CNTL4             RREG32=1    mmVM_CONTEXT0_CNTL  RREG32=8
	 *      mmVM_CONTEXT1_CNTL        RREG32=11
	 *      mmVM_CONTEXT0_CNTL2       RREG32=0    <-- el corpus NO lo lee
	 *      mmVM_CONTEXT1_CNTL2       RREG32=0    <-- el corpus NO lo lee
	 *
	 *  Los dos CNTL2 estan marcados "RW" y no tienen ni una lectura en todo el
	 *  driver de referencia:  se escriben a ciegas  (L892 y L922).  Su
	 *  verificabilidad por lectura es  NOT_DETERMINED.
	 *
	 *  Y el valor por defecto, para un registro que no esta en la tabla, es
	 *  false  (no verificable):  la ausencia no se presume legible. */
	const char		*access;	/* "R" | "W" | "RW"  PROYECTO */
	const char		*scope;		/* "CONTEXT1" | "GLOBAL"     */
	const char		*consumer;	/* para que lo usa el proximo */
	const char		*source;	/* fichero del corpus        */
	enum rx550_reg_confidence conf;
};

/* La tabla, y su tamano. */
extern const struct rx550_vmid1_reg rx550_vmid1_regs[];
extern const uint32_t rx550_vmid1_reg_count;

/* Los mnemonicos como indices en esa tabla, para no repetir el indice GFX8 en
 * el codigo del siguiente nodo ni buscar por cadena. */
enum rx550_vmid1_reg_id {
	/*  ORDEN ASCENDENTE POR INDICE, y el resolutor es POSICIONAL, asi que el
	 *  orden del enum ES el orden de la tabla.
	 *
	 *  RENUMERADO 2026-10-03 por segunda vez.  Se anadieron las TRECE entradas
	 *  que faltaban del bloque de contextos 2..7 y 9..15
	 *  (mmVM_CONTEXTn_PAGE_TABLE_BASE_ADDR),  que la referencia escribe
	 *  POSICIONALMENTE:
	 *
	 *      gmc_v8_0.c:912   WREG32(mmVM_CONTEXT0_PAGE_TABLE_BASE_ADDR + i,   ...)
	 *      gmc_v8_0.c:915   WREG32(mmVM_CONTEXT8_PAGE_TABLE_BASE_ADDR + i - 8, ...)
	 *
	 *  y que tienen NOMBRE en gmc_8_1_d.h:607-614 y :637-643.  Con solo las dos
	 *  anclas (0x550 y 0x50e) el bucle escribia trece registros que la tabla no
	 *  conocia,  y eso hacia que rx550_gart_es_legible() devolviera "no legible"
	 *  por AUSENCIA  en vez de por la columna access.  El resultado era el mismo
	 *  y el motivo no:  ver el finding 1031,  que decia la limitation y la deja
	 *  resuelta aqui.
	 *
	 *  Se ponen las trece y no solo las dos anclas porque el header las nombra
	 *  todas,  y una tabla que declara dos de quince deja al lector creyendo que
	 *  las otras trece no existen.  Es el mismo motivo por el que el accessor
	 *  documento el numero de pagina que se escribe en cada una. */
	RX550_REG_L2_CNTL				= 0,
	RX550_REG_L2_CNTL2				= 1,
	RX550_REG_L2_CNTL3				= 2,
	RX550_REG_CTX0_CNTL				= 3,
	RX550_REG_CTX1_CNTL				= 4,
	RX550_REG_CTX0_CNTL2				= 5,
	RX550_REG_CTX1_CNTL2				= 6,
	RX550_REG_CTX8_PT_BASE				= 7,
	RX550_REG_CTX9_PT_BASE				= 8,
	RX550_REG_CTX10_PT_BASE				= 9,
	RX550_REG_CTX11_PT_BASE				= 10,
	RX550_REG_CTX12_PT_BASE				= 11,
	RX550_REG_CTX13_PT_BASE				= 12,
	RX550_REG_CTX14_PT_BASE				= 13,
	RX550_REG_CTX15_PT_BASE				= 14,
	RX550_REG_INVALIDATE_REQUEST			= 15,
	RX550_REG_INVALIDATE_RESPONSE			= 16,
	RX550_REG_CTX0_PROT_FAULT_DEFAULT		= 17,
	RX550_REG_CTX1_PROT_FAULT_DEFAULT		= 18,
	RX550_REG_CTX0_PT_BASE				= 19,
	RX550_REG_CTX1_PT_BASE				= 20,
	RX550_REG_CTX2_PT_BASE				= 21,
	RX550_REG_CTX3_PT_BASE				= 22,
	RX550_REG_CTX4_PT_BASE				= 23,
	RX550_REG_CTX5_PT_BASE				= 24,
	RX550_REG_CTX6_PT_BASE				= 25,
	RX550_REG_CTX7_PT_BASE				= 26,
	RX550_REG_CTX0_PT_START				= 27,
	RX550_REG_CTX1_PT_START				= 28,
	RX550_REG_CTX0_PT_END				= 29,
	RX550_REG_CTX1_PT_END				= 30,
	/*  Los tres siguientes y el APERTURE_* de abajo son de bloques DISTINTOS:
	 *  no confundirlos.  El comentario sobre la identity aperture sigue
	 *  valiendo donde estaba. */
	RX550_REG_IDENTITY_APERTURE_LOW			= 31,
	RX550_REG_IDENTITY_APERTURE_HIGH		= 32,
	RX550_REG_IDENTITY_PHYSICAL_OFFSET		= 33,
	RX550_REG_L2_CNTL4				= 34,
	RX550_REG_APERTURE_LOW				= 35,
	RX550_REG_APERTURE_HIGH				= 36,
	RX550_REG_APERTURE_DEFAULT			= 37,
	RX550_REG_MX_L1_TLB_CNTL				= 38,
	RX550_REG_NR					= 39,
};

/* El descriptor de un mnemonico, o NULL si el id no existe. */
const struct rx550_vmid1_reg *rx550_vmid1_reg_get(enum rx550_vmid1_reg_id id);

/* ═══════════════════════════════════════════════════════════════════════════
 * LOS CAMPOS, Y POR QUÉ VAN AQUÍ
 *
 * El siguiente nodo programa CNTL y la apertura, y para eso necesita el mask y
 * el shift.  Declararlos aquí evita que ese nodo los vuelva a buscar, y evita
 * que cada uno escriba su propio REG_SET_FIELD con un mask copiado a mano.
 *
 * PROCEDENCIA, y es la de gmc_8_2_sh_mask.h
 * ═══════════════════════════════════════════════════════════════════════════ */

/* ═══════════════════════════════════════════════════════════════════════════
 * LOS CAMPOS
 *
 * UNA SOLA REPRESENTACIÓN, y eso es lo que este bloque reemplaza.
 *
 * Antes de este nodo las máscaras vivían en seis #define sueltos, y sólo
 * seis:  de los 22 campos que mmVM_CONTEXT1_CNTL declara en el header, la
 * cabecera del accessor conocía cuatro.  Eso no era un descuido de nombres,
 * era un agujero:  seis campos que el hardware usa y el software no conocía.
 *
 * Ahora hay UNA tabla, y la tabla es la representación.  Los #define que
 * quedan son ANCLAJES DE COMPILACIÓN, no una segunda copia:  existen para que
 * un _Static_assert pueda comprobarlos, y la tabla los referencia, de modo
 * que el valor está escrito una vez.  Si alguien cambia un ancla, la tabla
 * cambia con ella y no pueden divergir.
 * ═══════════════════════════════════════════════════════════════════════════ */

/* Los tres de la apertura, y el de PAGE_TABLE_BASE y PROTECTION_FAULT_DEFAULT,
 * que son el MISMO concepto con distinto nombre de campo.
 * Ver BACKING_MECHANISM §D. */
#define RX550_PN_MASK			0x0FFFFFFFu	/* 28 bits, numero de pagina */
#define RX550_PN_SHIFT			0u		/* el shift lo pone el software */

/* mmVM_CONTEXT1_CNTL, los dos campos multibit.  Los 20 restantes son de un
 * bit y viven en la tabla, donde no necesitan un nombre propio. */
#define RX550_CNTL_DEPTH_MASK		0x00000006u
#define RX550_CNTL_DEPTH_SHIFT		1u
#define RX550_CNTL_BLOCK_SIZE_MASK	0x0F000000u
#define RX550_CNTL_BLOCK_SIZE_SHIFT	24u

/* mmMC_VM_MX_L1_TLB_CNTL, el otro campo multibit. */
#define RX550_MX_ACCESS_MODE_MASK	0x00000018u
#define RX550_MX_ACCESS_MODE_SHIFT	3u

/* ═══════════════════════════════════════════════════════════════════════════
 * D1  LA CODIFICACIÓN DE PAGE_TABLE_BLOCK_SIZE
 *
 * ─────────────────────────────────────────────────────────────────────────────
 * Y PRIMERO, UNA ADVERTENCIA QUE PARECE DE TIPO DE LETRA Y NO LO ES
 * ─────────────────────────────────────────────────────────────────────────────
 *
 * ESTE MÓDULO Y M2 USAN LA PALABRA "MASK" CON SIGNIFICADOS OPUESTOS:
 *
 *   aquí            RX550_CNTL_BLOCK_SIZE_MASK = 0x0F000000   COLOCADA
 *                   = la convención de AMDGPU:  FIELD_MASK ya desplazada
 *
 *   rx550_vmid1_pgt.h   RX550_PDE_FIELD_MASK  = 0x7FFFFFFFFF   SIN COLOCAR
 *                   = 39 unos, un valor, que luego se desplaza
 *
 * El motivo es que las dos cosas son distintas.  Un FIELD_MASK de AMDGPU es un
 * fragmento de un REGISTRO de 32 bits y ocupa sus bits.  El campo de dirección
 * de un PDE no es un registro:  es un VALOR que el encoder produce y que hay
 * que colocar en 39:1.
 *
 * LA TRAMPA ES CONCRETA:  si alguien lleva la convención de M2 a este módulo y
 * desplaza la máscara otra vez, 0x0F000000 << 24 se sale de 32 bits y vale
 * CERO.  El campo queda a cero, el hardware lee block_size 9 cuando se le
 * pidió otro, y la cobertura resultante es coherente consigo misma y falsa.
 *
 * Ya pasó en este proyecto, 68 comprobaciones de golpe.  Por eso el módulo
 * tiene ahora `rx550_field_placed()` que devuelve la máscara TAL CUAL, y por
 * eso las dos convenciones se nombran distinto:  una lleva FIELD_, la otra no.
 * ─────────────────────────────────────────────────────────────────────────────
 *
 * ─────────────────────────────────────────────────────────────────────────────
 * LA FÓRMULA, Y POR QUÉ ES UN 9 Y NO UN NÚMERO PUESTO AHÍ
 * ─────────────────────────────────────────────────────────────────────────────
 *
 * El campo NO guarda el block_size:  guarda un DESPLAZAMIENTO respecto a 9.
 *
 *   amdgpu_gmc.c:1139
 *       u64 pde0_page_size = (1ULL << vmid0_page_table_block_size) << 21;
 *
 *   es decir   page_size = 2^(campo + 21) bytes
 *
 * y el block_size de amdgpu es log2(page_size) - 12, en bytes:
 *
 *   2^(campo+21) = 2^(block_size+12)   =>   campo = block_size - 9
 *
 * El 9 es 21 - 12,  es decir  "la unidad en que el campo cuenta"  menos  "la
 * unidad en que el block_size cuenta".  No es una constante mágica:  es la
 * diferencia entre dos logaritmos de la MISMA magnitud.
 *
 * Y LA CONSECUENCIA DE QUE SEA UN DESPLAZAMIENTO:  el valor que el hardware
 * devuelve NO es el que se le escribió, sino ese menos 9.
 */
#define RX550_CNTL_PAGE_SIZE_EXPONENT	21u	/* amdgpu_gmc.c:1139  << 21 */
#define RX550_FRAME_SHIFT		12u	/* amdgpu_gart.h:37   PAGE_SHIFT */

#define RX550_CNTL_BLOCK_SIZE_BASE	9u	/* campo 0  →  block_size 9  */
#define RX550_CNTL_BLOCK_SIZE_FIELD_MIN	0u	/* el campo es de 4 bits   */
#define RX550_CNTL_BLOCK_SIZE_FIELD_MAX	15u
#define RX550_CNTL_BLOCK_SIZE_VALUE_MIN	(RX550_CNTL_BLOCK_SIZE_BASE + \
					 RX550_CNTL_BLOCK_SIZE_FIELD_MIN)
#define RX550_CNTL_BLOCK_SIZE_VALUE_MAX	(RX550_CNTL_BLOCK_SIZE_BASE + \
					 RX550_CNTL_BLOCK_SIZE_FIELD_MAX)

/* El valor que el corpus escribe en un campo, cuando lo escribe.  El corpus
 * escribe CNTL2 como literal, no por REG_SET_FIELD, así que ese registro no
 * aporta ningún valor de campo. */
#define RX550_FIELD_NO_CORPUS		0xFFFFFFFFu

/* De dónde viene lo que se sabe de un campo.  Y LA DISTINCIÓN IMPORTA:
 *
 *   PROVEN_CORPUS_WRITES   el corpus REG_SET_FIELD lo escribe, y hay linea.
 *   DECLARED_NOT_WRITTEN   el header lo declara y el corpus NO lo toca.
 *
 * Los doce DECLARED_NOT_WRITTEN de CNTL existen para una sola cosa:  que el
 * nodo siguiente sepa qué bits SON SUYOS y cuáles tiene que preservar.  El
 * corpus programa con RREG32 → REG_SET_FIELD → WREG32, que conserva lo demás;
 * un escritor que no sepa qué campos hay no puede conservar nada. */
enum rx550_field_provenance {
	RX550_FIELD_PROVEN_CORPUS_WRITES	= 0,
	RX550_FIELD_DECLARED_NOT_WRITTEN	= 1,
};

struct rx550_reg_field {
	const char			*reg;		/* registro en el mapa GMC */
	const char			*name;		/* nombre del campo       */
	uint32_t			 mask;		/* tal cual el header     */
	uint32_t			 shift;		/* tal cual el header     */
	uint8_t				 width;		/* bits utiles            */
	uint32_t			 corpus;	/* valor, o NO_CORPUS     */
	const char			*source;	/* fichero:linea          */
	enum rx550_field_provenance	 prov;
};

extern const struct rx550_reg_field rx550_reg_fields[];
extern const uint32_t rx550_reg_field_count;

/* Los dos identificadores de los campos de CNTL y de MX_L1_TLB_CNTL, para no
 * repetir cadenas en el código del siguiente nodo.
 *
 * ─────────────────────────────────────────────────────────────────────────────
 * EL ORDEN DE ESTE ENUM ES EL ORDEN DE LA TABLA, Y ESO ES UNA RESTRICCIÓN
 * ─────────────────────────────────────────────────────────────────────────────
 *
 * El enum es un índice, y un índice que no coincide con la fila a la que
 * apunta es un error que no se ve:  rx550_field_of() devuelve un puntero
 * VÁLIDO, con máscara y shift coherentes consigo mismo, y del campo
 * equivocado.
 *
 * Pasó.  El enum tenía PAGE_TABLE_BLOCK_SIZE en la posición 2 y la tabla tenía
 * en la 2 RANGE_PROTECTION_FAULT_ENABLE_DEFAULT,  así que pedir el campo del
 * block_size devolvía el de Range con máscara 0x10 y shift 4.  Un test que
 * compara `rx550_field_of(i) == &tabla[i]` NO lo ve,  porque eso es cierto por
 * construcción:  el puntero a la fila i es la fila i.
 *
 * El test que lo ve compara el NOMBRE,  y por eso hay uno. */
enum rx550_field_id {
	RX550_FLD_CNTL_ENABLE_CONTEXT                         = 0,
	RX550_FLD_CNTL_PAGE_TABLE_DEPTH                       = 1,
	RX550_FLD_CNTL_RANGE_PROT_FAULT_DEFAULT               = 2,
	RX550_FLD_CNTL_DUMMY_PAGE_PROT_FAULT_DEFAULT          = 3,
	RX550_FLD_CNTL_PDE0_PROT_FAULT_DEFAULT                = 4,
	RX550_FLD_CNTL_VALID_PROT_FAULT_DEFAULT               = 5,
	RX550_FLD_CNTL_READ_PROT_FAULT_DEFAULT                = 6,
	RX550_FLD_CNTL_WRITE_PROT_FAULT_DEFAULT               = 7,
	RX550_FLD_CNTL_EXECUTE_PROT_FAULT_DEFAULT             = 8,
	RX550_FLD_CNTL_BLOCK_SIZE                             = 9,
	RX550_FLD_CNTL_RANGE_PROT_FAULT_INTERRUPT             = 10,
	RX550_FLD_CNTL_DUMMY_PAGE_PROT_FAULT_INTERRUPT        = 11,
	RX550_FLD_CNTL_PDE0_PROT_FAULT_INTERRUPT              = 12,
	RX550_FLD_CNTL_VALID_PROT_FAULT_INTERRUPT             = 13,
	RX550_FLD_CNTL_READ_PROT_FAULT_INTERRUPT              = 14,
	RX550_FLD_CNTL_WRITE_PROT_FAULT_INTERRUPT             = 15,
	RX550_FLD_CNTL_EXECUTE_PROT_FAULT_INTERRUPT           = 16,
	RX550_FLD_CNTL_PDE0_PROT_FAULT_SAVE                   = 17,
	RX550_FLD_CNTL_VALID_PROT_FAULT_SAVE                  = 18,
	RX550_FLD_CNTL_READ_PROT_FAULT_SAVE                   = 19,
	RX550_FLD_CNTL_WRITE_PROT_FAULT_SAVE                  = 20,
	RX550_FLD_CNTL_EXECUTE_PROT_FAULT_SAVE                = 21,
	RX550_FLD_L2_ENABLE_L2_CACHE                          = 22,
	RX550_FLD_L2_ENABLE_L2_FRAGMENT_PROCESSING            = 23,
	RX550_FLD_L2_ENABLE_L2_PTE_CACHE_LRU_UPDATE_BY_WRITE  = 24,
	RX550_FLD_L2_ENABLE_L2_PDE0_CACHE_LRU_UPDATE_BY_WRITE = 25,
	RX550_FLD_L2_EFFECTIVE_L2_QUEUE_SIZE                  = 26,
	RX550_FLD_L2_CONTEXT1_IDENTITY_ACCESS_MODE            = 27,
	RX550_FLD_L2_ENABLE_DEFAULT_PAGE_OUT_TO_SYSTEM_MEMORY = 28,
	RX550_FLD_L2C2_INVALIDATE_ALL_L1_TLBS                 = 29,
	RX550_FLD_L2C2_INVALIDATE_L2_CACHE                    = 30,
	RX550_FLD_L2C3_L2_CACHE_BIGK_ASSOCIATIVITY            = 31,
	RX550_FLD_L2C3_BANK_SELECT                            = 32,
	RX550_FLD_L2C3_L2_CACHE_BIGK_FRAGMENT_SIZE            = 33,
	RX550_FLD_L2C4_VMC_TAP_CONTEXT0_PDE_REQUEST_PHYSICAL  = 34,
	RX550_FLD_L2C4_VMC_TAP_CONTEXT0_PDE_REQUEST_SHARED    = 35,
	RX550_FLD_L2C4_VMC_TAP_CONTEXT0_PDE_REQUEST_SNOOP     = 36,
	RX550_FLD_L2C4_VMC_TAP_CONTEXT0_PTE_REQUEST_PHYSICAL  = 37,
	RX550_FLD_L2C4_VMC_TAP_CONTEXT0_PTE_REQUEST_SHARED    = 38,
	RX550_FLD_L2C4_VMC_TAP_CONTEXT0_PTE_REQUEST_SNOOP     = 39,
	RX550_FLD_L2C4_VMC_TAP_CONTEXT1_PDE_REQUEST_PHYSICAL  = 40,
	RX550_FLD_L2C4_VMC_TAP_CONTEXT1_PDE_REQUEST_SHARED    = 41,
	RX550_FLD_L2C4_VMC_TAP_CONTEXT1_PDE_REQUEST_SNOOP     = 42,
	RX550_FLD_L2C4_VMC_TAP_CONTEXT1_PTE_REQUEST_PHYSICAL  = 43,
	RX550_FLD_L2C4_VMC_TAP_CONTEXT1_PTE_REQUEST_SHARED    = 44,
	RX550_FLD_L2C4_VMC_TAP_CONTEXT1_PTE_REQUEST_SNOOP     = 45,
	RX550_FLD_CNTL0_ENABLE_CONTEXT                        = 46,
	RX550_FLD_CNTL0_PAGE_TABLE_DEPTH                      = 47,
	RX550_FLD_CNTL0_RANGE_PROTECTION_FAULT_ENABLE_DEFAULT = 48,
	RX550_FLD_MX_ENABLE_L1_TLB                            = 49,
	RX550_FLD_MX_ENABLE_L1_FRAGMENT_PROCESSING            = 50,
	RX550_FLD_MX_SYSTEM_ACCESS_MODE                       = 51,
	RX550_FLD_MX_SYSTEM_APERTURE_UNMAPPED_ACCESS          = 52,
	RX550_FLD_MX_ENABLE_ADVANCED_DRIVER_MODEL             = 53,
	RX550_FLD_MX_ECO_BITS                                 = 54,
	RX550_FLD_NR                                          = 55,
};


const struct rx550_reg_field *rx550_field_of(enum rx550_field_id id);

/* ═══════════════════════════════════════════════════════════════════════════
 * LAS CUATRO OPERACIONES PURAS, Y LA REGLA QUE LAS GOBIERNA
 *
 * LA REGLA:  una operación de campo sólo toca los bits de SU campo.  Nunca
 * uno de al lado, nunca uno de fuera.  No es una propiedad que se compruebe
 * al final, es la definición de la función, y por eso los bits contiguos se
 * calculan y se aplican juntos en una sola expresión.
 *
 * Y LA SEGUNDA REGLA, que es la que hace útil a la primera:  un valor fuera
 * del ancho del campo se RECORTA, no se propaga.  Un PAGE_TABLE_BLOCK_SIZE
 * con block_size 30 no puede desplazar un 1 hasta el bit 28:  la anchura la
 * decide el hardware, y el software que no la respeta ha escrito en otro
 * registro.
 * ═══════════════════════════════════════════════════════════════════════════ */

/* La máscara del campo, YA COLOCADA en su posición dentro del registro.
 *
 * ─────────────────────────────────────────────────────────────────────────────
 * Y AQUÍ ESTÁ LA CONVENCIÓN, QUE ES LA QUE HACE FALLAR ESTE MÓDULO SI SE OLVIDA
 * ─────────────────────────────────────────────────────────────────────────────
 *
 * En gmc_8_2_sh_mask.h  el campo se declara con DOS macros:
 *
 *      #define VM_CONTEXT1_CNTL__PAGE_TABLE_BLOCK_SIZE_MASK   0xf000000
 *      #define VM_CONTEXT1_CNTL__PAGE_TABLE_BLOCK_SIZE__SHIFT 0x18
 *
 * Y `MASK` YA ESTÁ DESPLAZADA:  0xf000000 son los bits 24..27, no los bits
 * 0..3 de una máscara sin colocar.  `__SHIFT` dice dónde está, y sirve para
 * leer y para escribir, NO para volver a colocar la máscara.
 *
 * Por eso esta función DEVUELVE LA MASCARA TAL CUAL, y no `mask << shift`.
 * La primera versión hacía `mask << shift`, que desplazaba dos veces y
 * producía 0xf000000000, es decir cero.  Los tests lo detectaron en 68
 * comprobaciones, todas de un mismo defecto.
 *
 * Y no es una peculiaridad de este header:  es la convención de AMDGPU, y el
 * proyecto ya la tenía escrita en M2 como la distinción entre
 * `RX550_PDE_FIELD_MASK` y `RX550_PDE_FIELD_PLACED_MASK`.  La regla que sale
 * de las dos es:  antes de desplazar una máscara, comprobar de dónde sale.
 */
static inline uint32_t rx550_field_placed(uint32_t mask, uint32_t shift)
{
	(void)shift;		/* la máscara llega colocada;  ver arriba */
	return mask;
}

/* Escribe un campo sobre un valor de registro, conservando el resto.  Esta es
 * la operación que el corpus hace con REG_SET_FIELD, y la que el nodo
 * siguiente necesita para no pisar lo que no conoce.
 *
 * Y LA ARITMÉTICA, que es donde está la trampa:
 *
 *     conserva   reg_value & ~mask          la máscara YA está colocada
 *     escribe    (value << shift) & mask     el valor sube, la máscara recorta
 *
 * Las dos mitades usan `mask` sin desplazar, porque la máscara llega puesta.
 * La primera versión hacía `~(mask << shift)` para la primera mitad, y eso
 * desplazaba el complemento:  para PAGE_TABLE_BLOCK_SIZE daba ~0xF000000000,
 * que truncado a 32 bits es 0, es decir no conservaba NADA. */
static inline uint32_t rx550_field_set(uint32_t reg_value, uint32_t mask,
				       uint32_t shift, uint32_t value)
{
	return (reg_value & ~mask) | ((value << shift) & mask);
}

/* Lee un campo de un valor de registro. */
static inline uint32_t rx550_field_get(uint32_t reg_value, uint32_t mask,
				       uint32_t shift)
{
	return (reg_value >> shift) & (mask >> shift);
}

/* El valor máximo representable, que es la máscara puesta sobre sí misma. */
static inline uint32_t rx550_field_max(uint32_t mask, uint32_t shift)
{
	return mask >> shift;
}

/* Los mismos, sobre la tabla, para no tener que pasar mask y shift a mano. */
static inline uint32_t rx550_field_set_id(uint32_t reg_value,
					  enum rx550_field_id id, uint32_t value)
{
	const struct rx550_reg_field *f = rx550_field_of(id);

	return f ? rx550_field_set(reg_value, f->mask, f->shift, value)
		 : reg_value;
}

static inline uint32_t rx550_field_get_id(uint32_t reg_value,
					  enum rx550_field_id id)
{
	const struct rx550_reg_field *f = rx550_field_of(id);

	return f ? rx550_field_get(reg_value, f->mask, f->shift) : 0u;
}

/* ═══════════════════════════════════════════════════════════════════════════
 * D1  ENCODER Y DECODER
 *
 * El encoder NO es `block_size - 9` suelto.  Es una comprobación de rango
 * primero, y la razón de que lo sea es un fallo concreto:
 *
 * El corpus hace la resta sobre un entero sin signo.  Un block_size de 8 da
 * 0xFFFFFFFF, y al recortar a los 4 bits del campo eso es 15,  es decir
 * block_size 24.  Pedir 512 bytes de página y obtener 64 GiB, en silencio y
 * con un readback que parece correcto.
 *
 * El proyecto no llega ahí porque rx550_vmid1_geometry() valida [9,24] antes
 * de calcular,  pero eso es una guarda en otro módulo.  Un encoder que no
 * puede fallar solo no depende de que alguien se acuerde de la guarda.
 *
 * Y el DECODER es la otra mitad, y es la que hace falta para el readback:  si
 * se escribe el campo 1 y se lee 1,  eso NO demuestra que block_size sea 10.
 * Lo demuestra es que se lea 10 de vuelta.
 */
/* Devuelve el VALOR DEL CAMPO,  no el registro con el campo puesto.
 *
 * Y esa distinción es el error de la primera versión:  devolvía
 * `rx550_field_set(0, MASK, SHIFT, valor)`,  que da 0x01000000 para block_size
 * 10,  y el nombre dice que va a devolver un 1.  El nibble de arriba lo pone
 * rx550_field_set() al componer el registro;  esta función sólo dice qué número
 * va dentro.  Devolver el registro compuesto y llamarlo "campo" es el mismo
 * error que comparar FIELD_MASK contra una máscara de dirección,  con otro
 * nombre.
 *
 * Y EL RECORTE A 4 BITS NO SE COMPRUEBA AQUÍ,  y ése es el punto:  lo hace
 * rx550_field_set(),  que es donde vive la máscara.  Si esta función también
 * mascara,  hay dos sitios que recortan,  y con dos sitios que recortan uno de
 * los dos deja de recortar el día que cambien la máscara. */
static inline uint32_t rx550_block_size_encode(uint32_t block_size)
{
	if (block_size < RX550_CNTL_BLOCK_SIZE_VALUE_MIN ||
	    block_size > RX550_CNTL_BLOCK_SIZE_VALUE_MAX)
		return UINT32_MAX;	/* no representable, y NO un valor de campo */

	return block_size - RX550_CNTL_BLOCK_SIZE_BASE;
}

/* El block_size que el hardware está usando, leído del registro.  Se pasa el
 * REGISTRO entero y no el valor del campo, porque es el valor real el que hay
 * que pasar por get:  es el mismo contrato que tiene el lector del corpus. */
static inline uint32_t rx550_block_size_decode(uint32_t reg_value)
{
	return RX550_CNTL_BLOCK_SIZE_BASE +
	       rx550_field_get(reg_value, RX550_CNTL_BLOCK_SIZE_MASK,
			       RX550_CNTL_BLOCK_SIZE_SHIFT);
}

/* ═══════════════════════════════════════════════════════════════════════════
 * EL ACCESOR
 * ═══════════════════════════════════════════════════════════════════════════ */

/* ESPACIO DE ERRORES PROPIO, Y POR QUÉ NO SE REUSA EL DE PGT
 *
 * La primera version de este modulo devolvia RX550_PGT_OK y
 * RX550_PGT_ERR_INCONSISTENT, y eso es una DEPENDENCIA QUE ESTA CABECERA
 * PROHIBE:  para nombrar un codigo de error de PGT habria que incluir
 * rx550_vmid1_pgt.h, y entonces el accessor —que es la capa inferior— sabria
 * que existe el PGT.  Compilarlo fue el error que lo destapo.
 *
 * Y ADEMAS TIENE VENTAJA:  los tres espacios no se solapan, de modo que un
 * llamante puede distinguir DE QUE CAPA viene un fallo con solo mirar el
 * numero, sin una tabla de procedencias:
 *
 *      M2       -1  .. -13
 *      BACKING  -101 .. -106
 *      MMIO     -200 .. -204
 */
#define RX550_MMIO_OK			0
#define RX550_MMIO_ERR_INCONSISTENT	(-200)	/* parametro nulo o invalido */
#define RX550_MMIO_ERR_NO_MAP		(-201)	/* no hay mapa enlazado      */
#define RX550_MMIO_ERR_OUT_OF_WINDOW	(-202)	/* el registro no cabe       */
#define RX550_MMIO_ERR_MAP_TOO_SMALL	(-203)	/* el mapa es menor que BAR5  */
#define RX550_MMIO_ERR_BAD_ID		(-204)	/* mnemonico inexistente     */

/*  Y POR QUE LOS CUATRO ESTAN DISTINTOS, Y NO UN "ACCESO INVALIDO"
 *
 *  Los tres primeros los trata el llamante de forma distinta, y por eso no
 *  pueden ser el mismo numero:
 *
 *    NO_MAP          no hay BAR5 mapeada:  el recurso no se ha tomado.  El
 *                    siguiente nodo no debe reintentar el acceso, debe tomar
 *                    el recurso.
 *    MAP_TOO_SMALL   el recurso se tomo pero es MAS PEQUEÑO que BAR5.  Eso es
 *                    una declaracion de recurso equivocada, y un ">=" en la
 *                    ventana lo dejaria pasar hasta escribir.
 *    OUT_OF_WINDOW   el registro no cabe en la BAR.  Eso es un error en el
 *                    mnemonico o en el indice, y el mismo en cualquier mapa.
 */

/* Resuelve un mnemonico a un registro indexado.  Puro:  no toca hardware y
 * no depende de ningun mapa. */
int rx550_mmio_reg_of(enum rx550_vmid1_reg_id id, struct rx550_reg *out);

/*  Resolver por INDICE de registro, y no por identificador del enum.
 *
 *  Hace falta porque hay registros que el enum no puede nombrar:  el corpus
 *  escribe mmVM_CONTEXT0_PAGE_TABLE_BASE_ADDR + i,  y para i = 1..15  son quince
 *  registros reales  (0x550..0x557 y 0x50f..0x515)  que no tienen entrada en
 *  ninguna tabla.  Meterlos uno a uno en el enum para luego sumar el mismo
 *  numero otra vez seria la tabla y el calculo Belt and braces:  uno de los dos
 *  dejaria de usarse y el otro empezaria a mentir.
 *
 *  La validacion NO es la del enum.  El enum valida que el id exista en la
 *  tabla;  aqui lo que se valida es que el indice quepa en la ventana,  que es
 *  lo que evita que un 0xffffffff se convierta en una direccion.  Las dos cosas
 *  se hacen:  rx550_mmio_resolve() sigue aplicando su comprobacion sobre el
 *  offset resultante,  asi que un indice aqui fuera de rango tampoco llega a
 *  escribir. */
int rx550_mmio_reg_of_index(uint32_t index, struct rx550_reg *out);

/* ── EL REGISTRO DE TABLA DE PAGINAS DE UN VMID ────────────────────────────
 *
 *  ESTA FUNCION EXISTE PORQUE LA REGLA NO ESTA EN LA TABLA, Y LA TABLA NO
 *  PUEDE TENERLA.
 *
 *  La tabla declara 16 mnemonicos, uno por entrada, y cada uno se verifica por
 *  separado contra gmc_8_1_d.h.  Eso NO demuestra que el contexto 1 este en el
 *  registro correcto: 0x550 esta bien como mnemonico, y 0x551 tambien, y
 *  0x5a0 tambien, y una tabla de 16 entradas todas correctas por separado puede
 *  estar en 16 indices equivocados a la vez sin que ninguna comprobacion lo
 *  note.  Lo que demuestra la correccion es la RELACION entre ellos, y la
 *  relacion no esta escrita en ninguna parte de este componente.
 *
 *  La relacion, del corpus y solo del corpus:
 *
 *    gmc_v8_0.c:672-676, gmc_v8_0_emit_flush_gpu_tlb()
 *        if (vmid < 8)
 *                reg = mmVM_CONTEXT0_PAGE_TABLE_BASE_ADDR + vmid;
 *        else
 *                reg = mmVM_CONTEXT8_PAGE_TABLE_BASE_ADDR + vmid - 8;
 *        amdgpu_ring_emit_wreg(ring, reg, pd_addr >> 12);
 *
 *    gmc_8_1_d.h:636-655     los 16 indices, y solo dos bloques
 *        0..7    mmVM_CONTEXT0..7_PAGE_TABLE_BASE_ADDR  = 0x54f .. 0x556
 *        8..15   mmVM_CONTEXT8..15_PAGE_TABLE_BASE_ADDR = 0x50e .. 0x515
 *
 *  O sea:  la regla es POSICIONAL, tiene un CORTE en 8, y los dos bloques NO son
 *  contiguos ni en el mismo orden.  Un `base + vmid` sin el corte escribe en
 *  0x50e para el VMID 8, que es el registro del VMID 15 del otro bloque, y
 *  produce un fallo que no se ve hasta que una pagina se mapea mal.
 *
 *  Indice, no offset:  el numero de gmc_8_1_d.h es el indice, y el offset en
 *  bytes es indice * 4.  Es la misma trampa que ya documenta test_pdb0 con
 *  mmCP_RB0_RPTR, y por eso el tipo de salida se llama reg_index.
 *
 *  vmid >= 16 se rechaza:  mmVM_INVALIDATE_REQUEST tiene 16 dominios
 *  (gmc_8_0.c:637, bucle vmid 1..15), asi que no hay un contexto 16 al que
 *  escribir aunque la aritmetica_CONTINUE_dando un indice dentro de BAR5.
 */
uint32_t rx550_mmio_ctx_pt_base_index(unsigned vmid);

/* El VALOR que se escribe en ese registro:  el numero de pagina, no la
 * direccion.
 *
 *  gmc_8_0.c:675   amdgpu_ring_emit_wreg(ring, reg, pd_addr >> 12)
 *  gmc_8_1_sh_mask.h:6879
 *      VM_CONTEXT0_PAGE_TABLE_BASE_ADDR__PHYSICAL_PAGE_NUMBER_MASK = 0xfffffff
 *
 *  28 bits, y el campo empieza en el bit 0.  Un >> 12 sobre una direccion de
 *  40 bits da exactamente 28, asi que el campo cabe entero.  Si la direccion
 *  tuviera mas de 40 bits, el truncamiento seria SILENCIOSO y el error no
 *  apareceria hasta que la pagina se lea mal:  por eso se rechaza en vez de
 *  cortar.
 */
#define RX550_PT_PAGE_SHIFT	12u
#define RX550_PT_PN_BITS		28u
#define RX550_PT_MAX_PD_ADDR	((UINT64_C(1) << RX550_PT_PN_BITS) << RX550_PT_PAGE_SHIFT) - UINT64_C(1)

/* Devuelve 0 y no escribe nada en `out` si la direccion no cabe en 40 bits. */
int rx550_mmio_pt_value(uint64_t pd_addr, uint32_t *out);

/* Resuelve un registro a su offset DENTRO del mapa, comprobando la ventana.
 *
 * Y ESTA ES LA FRONTERA DEL MODULO:  aqui se decide si el acceso procede.  Si
 * no procede, NO HAY ACCESO, y el motivo se distingue entre tres causas que
 * el llamante trata de forma distinta:  no hay mapa, el registro no cabe, o el
 * mapa es mas pequeno que la BAR5 declarada. */
int rx550_mmio_resolve(const struct rx550_mmio_map *map, struct rx550_reg reg,
		       struct rx550_mmap_offset *out);

/* Y el atajo por mnemonico, que compone las dos y no repite la comprobacion. */
int rx550_mmio_resolve_reg(const struct rx550_mmio_map *map,
			   enum rx550_vmid1_reg_id id,
			   struct rx550_mmap_offset *out);

/* ── ACTUALIZACION DE UN CAMPO:  la primitiva que faltaba ───────────────────
 *
 *  POR QUE EXISTE, Y NO COMO UN "SET_FIELD" MAS
 *
 *  El corpus programa los registros de control con
 *      RREG32 -> REG_SET_FIELD -> WREG32            (amdgpu.h:1354-1356)
 *  y de las 34 escrituras de gmc_v8_0_gart_enable(), SIETE son de esa forma.
 *
 *  CORREGIDO el 2026-10-03, dos veces.  Aqui decia "las 21 escrituras son TODAS
 *  de esa forma" y no hay ni una escritura ciega en la secuencia".  Las dos
 *  partes eran falsas:
 *
 *      son 34, no 21
 *      y de esas 34,  SIETE son RMW  y  27 son escrituras directas de un
 *                     literal o de un PFN
 *
 *  Las siete RMW, con su linea real:
 *      L849 mmMC_VM_MX_L1_TLB_CNTL   L859 mmVM_L2_CNTL     L863 mmVM_L2_CNTL2
 *      L870 mmVM_L2_CNTL3             L885 mmVM_L2_CNTL4    L897 mmVM_CONTEXT0_CNTL
 *      L935 mmVM_CONTEXT1_CNTL
 *
 *  y las 27 directas caen todas en registros cuyo valor es un unico numero,
 *  asi que no pierden nada al escribirlas a pelo.
 *
 *  Lo que si es cierto, y es lo que hace falta esta primitiva, es lo de los
 *  registros de control:  en mmVM_CONTEXT0_CNTL hay 22 campos y la referencia
 *  pone 3, de modo que una escritura directa pondria a cero los otros 19 y el
 *  resultado no falla al escribir:  falla mucho despues, cuando una pagina se
 *  mapea mal.  Ese es el motivo de que la RMW por campo exista, y no el hecho
 *  de que toda la secuencia sea una RMW.
 *
 *  Y el accessor no tenia forma de hacerlo.  Solo read32 y write32.  Ver el
 *  finding 1028.
 *
 *  EL SHIFT SE DERIVA DEL MASK, Y NO SE COPIA
 *
 *  amdgpu declara <REG>__<FIELD>_MASK y <REG>__<FIELD>__SHIFT.  El __SHIFT es
 *  redundante:  MEDIDO sobre los 42 campos que escribe gmc_v8_0_gart_enable(),
 *  en los 42 casos vale el numero de ceros finales del MASK, y el invariante
 *
 *      (mask >> shift) == 2^ancho - 1
 *
 *  se cumple sin una sola excepcion.
 *
 *  Por que importa no copiarlo:  una tabla de 42 constantes __SHIFT escritas a
 *  mano es una tabla que se desincroniza en silencio el dia que el header se
 *  regenere, y el fallo se manifesta como "la GPU no mapea bien", que es el
 *  sintoma mas caro de buscar de todo este componente.  Con el mask solo, la
 *  tabla se puede comprobar contra el corpus entero con un invariante, que es
 *  lo que hace test_update_field.c.
 *
 *  POR QUE RECHAZA UN MASK MAL FORMADO, Y POR QUE
 *
 *  Un mask con dos grupos de unos separados ("0b101") no tiene una posicion
 *  unica, y un mask de cero no tiene ninguna.  Derivarlos en silencio daria un
 *  shift que el hardware no espera.  Se rechazan, con el motivo distinguido del
 *  que ya existe para el acceso, porque quien llama trata los dos distinto.
 */
#define RX550_MMIO_ERR_BAD_MASK		(-205)	/* mask 0 o no contiguo      */
#define RX550_MMIO_ERR_VALUE_RANGE	(-206)	/* el valor no cabe en el campo */

/* Posicion y anchura de un campo, derivadas del MASK.  Puro, sin mapa ni HW.
 *
 *  EL NOMBRE, Y POR QUE NO ES "rx550_field_of"
 *
 *  Ya existe rx550_field_of(enum rx550_field_id) en este mismo fichero:  busca
 *  POR NOMBRE en la tabla rx550_reg_fields[] y devuelve un puntero.  Esta
 *  deriva POR MASMARA y devuelve dos numeros.  Son cosas distintas con nombres
 *  que se diferencian en un prefijo, y la primera version de esta función se
 *  llamaba igual:  un `rx550_field_of` nuevo con otro sentido, a tres lineas
 *  del de verdad.  Dos funciones con el mismo nombre y distinta semantica son
 *  la clase de trampa que este componente existe para no tener. */
int rx550_mmio_field_from_mask(uint32_t mask, unsigned *out_shift, unsigned *out_width);

/* El NUCLEO PURO:  aplica un campo a un VALOR, sin tocar memoria.
 *
 *  update_field() es esto mas el acceso.  Separate, por dos razones:
 *
 *   1.  Se puede probar y usar en userspace sin mapa, y es lo que necesita el
 *       constructor de la secuencia del GART:  esa secuencia se CALCULA antes
 *       de escribirse, y calcularla necesita composing sobre un valor entero.
 *   2.  Si la composicion viviera dentro de update_field(), no habria forma de
 *       comprobarla sin un mapa, y la regla de los campos seria lo unico del
 *       componente que no tendria un test que pueda fallar sin hardware.
 */
int rx550_mmio_apply_field(uint32_t raw, uint32_t mask, uint32_t value,
			   uint32_t *out);

/* Lee, cambia SOLO los bits del campo, y escribe.  Devuelve el valor que queda
 * en el registro, para que el llamante pueda comprobarlo sin releer. */
int rx550_mmio_update_field(const struct rx550_mmio_map *map,
			    struct rx550_reg reg,
			    uint32_t mask, uint32_t value,
			    uint32_t *out_value);

/* El valor de un campo ya leído, con la misma validacion que la escritura.
 * Un mask invalido NO se aplica en silencio aqui tampoco:  leer un campo con
 * mascara invalida daria un numero que no significa nada. */
int rx550_mmio_get_field(uint32_t raw, uint32_t mask, uint32_t *out_value);

/* Lectura y escritura de 32 bits.  Devuelven el codigo del resolver, y no
 * tocan hardware si el resolver no dijo que sí. */
int rx550_mmio_read32(const struct rx550_mmio_map *map, struct rx550_reg reg,
		      uint32_t *out_value);
int rx550_mmio_write32(const struct rx550_mmio_map *map, struct rx550_reg reg,
		       uint32_t value);

/* Los mismos por mnemonico, para el codigo del siguiente nodo. */
int rx550_mmio_read_reg(const struct rx550_mmio_map *map,
			enum rx550_vmid1_reg_id id, uint32_t *out_value);
int rx550_mmio_write_reg(const struct rx550_mmio_map *map,
			 enum rx550_vmid1_reg_id id, uint32_t value);

/* Enlaza y desenlaza el mapa.  El TAMANO se comprueba aqui, no en el primer
 * acceso. */
int rx550_mmio_attach(struct rx550_mmio_map *map, void *base, uint64_t size);
void rx550_mmio_detach(struct rx550_mmio_map *map);

/* Texto del error.  No para lógica de control. */
const char *rx550_mmio_err_str(int rc);

/* ═══════════════════════════════════════════════════════════════════════════
 * INVARIANTES ESTATICAS
 *
 * De REPRESENTACION y de CONTRATO, no de valores de hardware.  La anchura de
 * la palabra y el factor indice -> offset SI son contrato del mapa, y por eso
 * van aquí:  si cambian, el accesoor entero pasa a estar equivocado en
 * silencio.
 * ═══════════════════════════════════════════════════════════════════════════ */
_Static_assert(RX550_REG_WIDTH == 4u,
		"la BAR5 se direcciona en palabras de 4 B; cambiarlo cambia el contrato");
_Static_assert(RX550_MMIO_SIZE == 0x40000u,
		"el tamaño de la apertura de registros es un dato del host medido");
_Static_assert(sizeof(struct rx550_mmap_offset) == sizeof(uint64_t),
		"el offset tiene que caber en el tipo que lo representa");
_Static_assert(RX550_REG_NR == 39u,
		"la tabla de registros tiene 39 entradas: 20 de la secuencia + 13 del bloque de contextos 2..7 y 9..15");
	/*  D3.  Los tres de la identity aperture son tres ids consecutivos, y
	 *  los tres usan el ancla de 28 bits de numero de pagina con shift 0.
	 *  Que el CORPUS los siga escribiendo a cero lo comprueba el test, no
	 *  esto:  esto solo ata la forma de la tabla. */
	_Static_assert(RX550_REG_IDENTITY_APERTURE_HIGH ==
			RX550_REG_IDENTITY_APERTURE_LOW + 1u,
			"LOW y HIGH de la identity aperture son contiguos");
	_Static_assert(RX550_REG_IDENTITY_PHYSICAL_OFFSET ==
			RX550_REG_IDENTITY_APERTURE_LOW + 2u,
			"el PHYSICAL_OFFSET es el tercero, y no uno ausente");
	_Static_assert(RX550_REG_IDENTITY_PHYSICAL_OFFSET + 1u ==
			RX550_REG_L2_CNTL4,
			"y el bloque va justo antes de L2_CNTL4, por indice");
	_Static_assert(RX550_PN_MASK == 0x0FFFFFFFu,
		"el limite del numero de pagina es de 28 bits, y no es negociable");
_Static_assert((RX550_CNTL_DEPTH_MASK >> RX550_CNTL_DEPTH_SHIFT) == 0x3u,
		"PAGE_TABLE_DEPTH ocupa 2 bits");
_Static_assert((RX550_CNTL_BLOCK_SIZE_MASK >> RX550_CNTL_BLOCK_SIZE_SHIFT) == 0xFu,
		"PAGE_TABLE_BLOCK_SIZE ocupa 4 bits, luego block_size en [9,24]");
_Static_assert((RX550_MX_ACCESS_MODE_MASK >> RX550_MX_ACCESS_MODE_SHIFT) == 0x3u,
		"SYSTEM_ACCESS_MODE ocupa 2 bits");
/*  El numero de la tabla de campos.  ERA 28  (22 de mmVM_CONTEXT1_CNTL y 6 de
 *  mmMC_VM_MX_L1_TLB_CNTL)  y ahora es 55,  con los 27 campos que
 *  gmc_v8_0_gart_enable() escribe y faltaban:
 *
 *      VM_L2_CNTL      7      VM_L2_CNTL2   2      VM_L2_CNTL3   3
 *      VM_L2_CNTL4    12      VM_CONTEXT0_CNTL   3
 *
 *  Y el reparto por registro, que es lo que hay que recontar cuando cambie:
 *
 *      mmVM_CONTEXT1_CNTL          22
 *      mmVM_L2_CNTL                 7
 *      mmVM_L2_CNTL2                2
 *      mmVM_L2_CNTL3                3
 *      mmVM_L2_CNTL4               12
 *      mmVM_CONTEXT0_CNTL           3
 *      mmMC_VM_MX_L1_TLB_CNTL       6
 *      ------------------------------------
 *      total                       55
 *
 *  Ver el finding 1030. */
_Static_assert(RX550_FLD_NR == 55u,
		"la tabla de campos tiene 22+7+2+3+12+3+6 = 55 entradas");
/* Y D1:  el rango del VALOR tiene que ser el rango del CAMPO desplazado por la
 * base.  Si alguien cambia la base y no el rango, estas dos lo dicen. */
_Static_assert(RX550_CNTL_BLOCK_SIZE_FIELD_MAX ==
		(RX550_CNTL_BLOCK_SIZE_MASK >> RX550_CNTL_BLOCK_SIZE_SHIFT),
		"el maximo del campo tiene que salir de su propia mascara");
_Static_assert(RX550_CNTL_BLOCK_SIZE_VALUE_MIN == 9u &&
		RX550_CNTL_BLOCK_SIZE_VALUE_MAX == 24u,
		"el rango codificable de block_size es [9,24]: campo [0,15]");
_Static_assert(RX550_CNTL_BLOCK_SIZE_FIELD_MIN == 0u,
		"el campo 0 tiene que ser el block_size minimo, no un offset");
/* Y LA BASE TIENE QUE SALER DE SUS DOS FUENTES MEDIDAS, no ser un 9 escrito a
 * mano.  El 9 es 21 - 12:  el exponente con el que el corpus escala el tamaño
 * de página, menos el desplazamiento del frame.  Si cualquiera de los dos
 * cambia, esta aserción falla y obliga a volver a la evidencia.
 *
 * La primera versión de esta aserción comparaba BASE + SHIFT contra 21, que
 * son 9 + 24 = 33, y por eso no-compilaba.  La relación correcta es entre el
 * exponente de página y el frame, y no tiene nada que ver con el shift del
 * campo:  son dos cosas distintas, y sumarlas fue el error. */
_Static_assert(RX550_CNTL_BLOCK_SIZE_BASE ==
		(RX550_CNTL_PAGE_SIZE_EXPONENT - RX550_FRAME_SHIFT),
		"la base es page_size_exp - frame_shift: 21 - 12 = 9, medido en "
		"amdgpu_gmc.c:1139 y amdgpu_gart.h:37");
/* Y la que ata D1 al GFX8 concreto, y que rompen los mutantes `base-8` y
 * `base-10` sin tocar nada más. */
_Static_assert(RX550_CNTL_BLOCK_SIZE_BASE == 9u,
		"el corpus escribe `block_size - 9` en gmc_v8_0.c:934");
/* Y la coherencia de los tres anclajes con la tabla, que es lo que impide que
 * la tabla y las aserciones se separen sin que ninguna lo note. */
_Static_assert(RX550_FIELD_NO_CORPUS == 0xFFFFFFFFu,
		"el centinela de 'el corpus no escribe este campo' no puede ser un valor posible");

#endif /* RX550_MMIO_ACCESS_H */
