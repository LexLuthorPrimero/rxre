/* SPDX-License-Identifier: GPL-2.0-only */
/*
 * rx550_vmid1_pgt.h — la jerarquia de tabla de VMID1 en GFX8, como OBJETO.
 *
 *   TARGET = RX 550 instalada en esta maquina  (1002:699F, Polaris12, GFX8)
 *   SCOPE  = EXCLUSIVO
 *
 * QUE ES
 *   La representacion software del arbol de dos niveles que el contexto 1
 *   camina:  un PDB0 root de 4 KiB con 512 PDE, y 512 paginas PTE de 4 KiB.
 *   Produce una jerarquia softwaremente valida.  No toca hardware.
 *
 * QUE NO ES, Y NO POR ELECCION DE ESTILO
 *   No programa PAGE_TABLE_BASE_ADDR, ni START/END, ni VM_CONTEXT1_CNTL.
 *   No hace MMIO, no hay ioremap, no hay readl/writel, no hay ring, no invalida.
 *   No reserva memoria: el backing es del nodo siguiente.
 *   No asigna GPU VA.  No hay ventana que gestionar aqui.
 *
 * ─────────────────────────────────────────────────────────────────────────────
 * POR QUE LA GEOMETRIA SE DERIVA Y NO SE DECLARA
 * ─────────────────────────────────────────────────────────────────────────────
 *
 *   Los cinco numeros que definen esta tabla —num_level, root, pte_pages,
 *   pte_entries, coverage— NO SON CONSTANTES DE ESTE FICHERO.  Son la salida
 *   de una funcion de vm_size, y la funcion es la aritmetica del corpus:
 *
 *     amdgpu_vm.c:2433   max_pfn = vm_size << 18
 *     amdgpu_vm.c:2436   tmp = roundup_pow_of_two(max_pfn)
 *     amdgpu_vm.c:2439   tmp = DIV_ROUND_UP(fls64(tmp) - 1, 9) - 1
 *     amdgpu_vm.c:2440   num_level = min(max_level, tmp)
 *     amdgpu_vm.c:2463   block_size = 9   si num_level > 1
 *     amdgpu_vm.c:2466   block_size = amdgpu_vm_get_block_size(tmp)
 *     amdgpu_vm.c:2368   get_block_size:  bits = ilog2(t) + 18
 *     amdgpu_vm.c:2375                             t <= 8  ->  bits - 9
 *     amdgpu_vm.c:2377                             t >  8  ->  (bits+3)/2
 *
 *   Y max_level NO es 4 en general:  para GFX8 es 1.
 *
 *     gmc_v8_0.c:1127   amdgpu_vm_adjust_size(adev, 64, 9, 1, 40);
 *                                                  min_vm_size fragment max_level max_bits
 *
 *   con lo cual num_level queda SIEMPRE en 1 para esta ASIC, y lo que varia
 *   con vm_size es block_size.
 *
 *   SI SE HARDCODEARA (1, 512, 512), EL CODIGO SERIA INCORRECTO EN EL MOMENTO
 *   vm_size | tmp | num_level | block | campo | raiz    | cobertura | cubre vm_size?
 *   --------+-----+-----------+-------+-------+---------+-----------+---------------
 *      1 GiB|   1 |         1 |     9 |     0 |   4 KiB |  1024 MiB | SI, exactamente
 *      2 GiB|   2 |         1 |    10 |     1 |   4 KiB |  2048 MiB | SI, exactamente
 *      4 GiB|   2 |         1 |    10 |     1 |   8 KiB |  4096 MiB | SI, exactamente
 *      8 GiB|   2 |         1 |    10 |     1 |  16 KiB |  8192 MiB | SI, exactamente
 *     64 GiB|   2 |         1 |    10 |     1 | 128 KiB | 65536 MiB | SI, exactamente
 *
 *   MEDIDO 2026-10-04.  ESTA TABLA ESTABA MAL Y EN SUS DOS COLUMNES.
 *
 *   Decia que la cobertura saturaba en 4 GiB y que por eso 8 GiB "NO <- se
 *   rechaza".  Las dos cosas eran falsas:  la cobertura es EXACTAMENTE la
 *   ventana en los cinco casos,  y 8 GiB se acepta.  Con la tabla anterior,
 *   el driver rechazaba su propia ventana de 64 GiB.
 *
 *   LA FORMULA ERRONEA, en las dos copias que habia  —el modulo y
 *   corpus_geometry() en test_block_size.c—:
 *
 *       coverage = 2^block_size * 2^block_size << 12
 *
 *   trata la RAIZ como una tabla mas de 2^block_size entradas.  El corpus no lo
 *   hace.  Con num_level == 1 el root_level es PDB0  (amdgpu_vm.c:2451-2452,
 *   y enum amdgpu_vm_level {PDB3=0, PDB2=1, PDB1=2, PDB0=3, PTB=4}),  y de ahi:
 *
 *       amdgpu_vm_pt.c:58-59    level_shift(PDB0) = 9*(PDB0-PDB0) + block_size
 *                                        = block_size
 *       amdgpu_vm_pt.c:84-85    num_entries(PDB0) = round_up(max_pfn, 1<<shift) >> shift
 *                               y max_pfn = vm_size >> 12,  de modo que el
 *                               numero de entradas DEPENDE de la ventana
 *       amdgpu_vm_pt.c:106-107  entries_mask(PDB0) = 0xffffffff
 *       amdgpu_vm_pt.c:91       num_entries(PTB)  = 1 << block_size
 *       amdgpu_vm_pt.c:191      idx = (pfn >> shift) & mask
 *
 *   Y con eso la cobertura es exactamente max_pfn paginas:  la ventana entera.
 *   El reparto de bits se ve en la linea 191:  la raiz saca los bits 10..33 del
 *   pfn  y la hoja los bits 0..9,  y entre los dos cubren los 24 bits del pfn sin
 *   huecos.
 *
 *   LA COLUMNA "cubre vm_size?" NO PUEDE SER "NO"  con esta aritmetica,  y esa
 *   es la forma que delata la formula:  la cobertura es una identidad de la
 *   ventana,  luego la pregunta no tiene dos respuestas posibles.  Y la tabla
 *   anterior la respondia "NO",  lo cual es logically incompatible con existir en
 *   la misma tabla una cobertura derivada de block_size.
 *
 *   QUIEN REFUTO TODO ESTO:  un adversario independiente leyo amdgpu_vm_pt.c y
 *   amdgpu_vm.h.  Y la evidencia que este componente daba de la cifra falsa eran
 *   TRES IDENTIDADES DE TIEMPO DE COMPILACION  (1<<32 == 4<<30),  que se cumplen
 *   para CUALQUIER estado del driver.  Un control que no puede fallar.
 * POR QUE ROOT Y PTE SON TIPOS DISTINTOS, Y NO UNA CONVENIENCIA
 * ─────────────────────────────────────────────────────────────────────────────
 *
 *   Un PDE y un PTE tienen formatos DISTINTOS en GFX8, y confundirlos no da
 *   un error:  da una traduccion.
 *
 *     gmc_v8_0.c:691-702   PTE   39:12 PA | 11:7 frag | 6 w | 5 r | 4 x | ...
 *                          1 system | 0 valid
 *     gmc_v8_0.c:704-709   PDE   63:59 frag | 58:40 reserved |
 *                          39:1 base address of PTE | 0 valid
 *
 *   El PDE tiene UN campo de direccion, en 39:1, y nada mas.  Si se escriben
 *   alli los flags de PTE —READABLE es el bit 5, WRITEABLE el bit 6— se esta
 *   CORROMPIENDO LA DIRECCION de la pagina de PTE, porque 5 y 6 caen DENTRO
 *   de 39:1.  El sintoma no es un fallo:  es una PTE con permisos cambiados en
 *   una pagina arbitraria.
 *
 *   Por eso aqui no hay una entrada de 64 bits con banderines, sino dos tipos
 *   que no se pueden pasar el uno por el otro, y un encoder que no es el del
 *   PTE.  Este modulo NO incluye rx550_pdb0.h NI rx550_vmid0_gart.h.
 *
 * ─────────────────────────────────────────────────────────────────────────────
 * LO QUE ESTE MODULO NO AFIRMA
 * ─────────────────────────────────────────────────────────────────────────────
 *
 *   Que un PDE bien codificado sea aceptado por el hardware.  Eso exige
 *   programarlo y ejecutarlo, y ninguna de las dos cosas es de aqui.
 *   Que un PTE bien codificado traduzca.  El PTE lo escribe otro modulo.
 *   Que la jerarquia sea alcanzable.  Eso exige el backing y la apertura.
 */

#ifndef RX550_VMID1_PGT_H
#define RX550_VMID1_PGT_H

/* COMPATIBILIDAD KBUILD: mismo split que rx550_spaces.h.
 * MEDIDO 2026-10-03: con los tres includes de user, estos .c no compilaban
 * bajo kbuild y por eso no estaban en obj-m.  La rama de userspace no cambia:
 * es la misma que habia antes.
 */
#ifdef __KERNEL__
#include <linux/types.h>
#define UINT64_C(x) U64_C(x)
#define UINT32_C(x) U32_C(x)
/* linux/limits.h:25 define U64_MAX como ((u64)~0ULL).  Es el mismo numero que
 * el UINT64_MAX de <stdint.h>: el guardia contra el desbordamiento de
 * vm_size_bytes, en rx550_vmid1_pgt.c:169, comprueba contra el mismo limite en
 * los dos contextos y por eso no cambia de comportamiento al compilar para el
 * modulo. */
#include <linux/limits.h>
#define UINT64_MAX	U64_MAX
#else
#include <stdint.h>
#include <stdbool.h>
#include <stddef.h>
#endif

/* ── HARDWARE_REQUIREMENT ────────────────────────────────────────────────────
 * Pagina de 4 KiB y entrada de 8 B.  Es el mismo tamano de entrada para el
 * PDE y para el PTE, y ese es el unico rasgo que comparten. */
#define RX550_VMID1_PAGE_SIZE		4096u
#define RX550_VMID1_PAGE_SHIFT		12u
#define RX550_VMID1_ENTRY_BYTES		8u
#define RX550_VMID1_ENTRY_BITS		64u

/* ── HARDWARE_REQUIREMENT: MAX_LEVEL PARA GFX8 ─────────────────────────────
 * gmc_v8_0.c:1127  amdgpu_vm_adjust_size(adev, 64, 9, 1, 40)
 * El 1 es max_level.  Por eso num_level no puede crecer en esta ASIC. */
#define RX550_VMID1_MAX_LEVEL		1u

/* ── HARDWARE_REQUIREMENT: RANGO CODIFICABLE DE block_size ─────────────────
 * gmc_v8_0.c:933-934   PAGE_TABLE_BLOCK_SIZE = block_size - 9
 * gmc_8_2_sh_mask.h    PAGE_TABLE_BLOCK_SIZE__MASK 0xf000000  __SHIFT 0x18
 * El campo son 4 bits, luego block_size - 9 cabe en [0, 15] y el rango
 * codificable es [9, 24].
 *
 * Y EL ESTADO DE LA EVIDENCIA POR VALOR.  MEDIDO 2026-10-04, CORREGIDO:  esta
 * clasificacion estaba AL REVES,  y era el unico sitio del componente que
 * declaraba un valor de block_size contradictorio.
 *
 * Decia "9 DEMONSTRADO_EN_GFX8" y "10 COMPUTADO_Y_CODIFICABLE, NO_ESCRIBE_EN
 * GFX8".  La primera mitad de la primera frase es cierta:  gmc_v8_0.c:933 ES el
 * sitio de escritura del campo.  Pero el VALOR que llega ahi sale de
 * amdgpu_vm.c:2466,  que con la ventana de 64 GiB de esta maquina produce 10.
 * O sea:  el corpus escribe 10 en gmc_v8_0.c:934,  no 9.  Y "para 2 GiB", que
 * decia la entrada del 10,  era mas estrecho que la verdad:  amdgpu_vm.c:2375-2376
 * produce 10 para 2, 4, 8 y 64 GiB.
 *
 *   9   CODIFICABLE_SIN_ALCANZAR  lo daria el reset de GFX9, no el de GFX8
 *   10  DEMOSTRADO_EN_GFX8         derivado de los literales de
 *                                  gmc_v8_0.c:1127 (64, 9, 1, 40) mas
 *                                  amdgpu_vm.c:2436-2466, y corroborado por el
 *                                  log del arranque: "block size is 10-bit".
 *                                  El barrido de TODO el dominio legal de
 *                                  vm_size lo da constante,  y eso prueba que no
 *                                  depende de la RAM.  Ver rx550_vm_geom.c.
 *   24  EL TOPE DEL CAMPO          codificable, no alcanzado por esta ASIC
 *
 * POR QUE LA CONFUSION ERA FACIL, y por que el 9 no es un valor de GFX8:
 * el reset de GFX9 SI da 9.  mmhub_1_0_default.h lo decodifica a
 * PAGE_TABLE_BLOCK_SIZE = 0,  o sea block_size 9,  y es coherente porque en
 * GFX9 el driver pone block_size = 9 por la rama de num_level > 1
 * (amdgpu_vm.c:2464),  que GFX8 nunca toma porque max_level = 1.  El valor de
 * reset de una generacion no es el valor que escribe otra.
 */
#define RX550_VMID1_BLOCK_SIZE_MIN		9u
#define RX550_VMID1_BLOCK_SIZE_MAX		24u
/* MEDIDO 2026-10-04, D4:  el 9 del CORPUS con el que se resta es un literal
 * suelto en las tres apariciones, y una de ellas —rx550_vmid1_pgt.c:271— lo
 * escribia a mano en vez de nombrarlo.  Se declara una vez aqui. */
#define RX550_VMID1_BLOCK_OFFSET		9u	/* gmc_v8_0.c:933-934 */
/* 10, y no el MINIMO.  El valor que el corpus ESCRIBE en esta ASIC.  Antes
 * apuntaba a 9,  que es el valor del reset de GFX9:  un valor de otra
 * generacion usado como si fuera el de esta. */
#define RX550_VMID1_BLOCK_SIZE_DEMOSTRADO	10u

/* ── HARDWARE_REQUIREMENT: EL 18 Y EL 9, QUE EN EL CORPUS SON LITERALES ─────
 *
 * MEDIDO 2026-10-04, D4.  El corpus escribe estos numeros a mano y este modulo
 * los reproducia literales en cuatro sitios.  Se declaran una vez aqui, cada
 * uno con el suyo, y —que es lo importante— SIN FUSIONARLOS, porque no son el
 * mismo hecho:
 *
 *   RX550_VMID1_BITS_POR_GB = 18   amdgpu_vm.c:2359
 *       El segundo factor de "bits = ilog2(vm_size) + 18".  Convierte GiB en
 *       paginas de 4 KiB:  2^30 / 2^12 = 2^18.
 *
 *   RX550_VMID1_NIVEL_MIN_BITS = 9   amdgpu_vm.c:2364 y :2427
 *       El ancho MINIMO de un nivel de tabla, el que hace que un PD quepa en
 *       4 KiB.  Es el 9 de "if (vm_size <= 8) return bits - 9" y el divisor de
 *       "DIV_ROUND_UP(fls64(tmp) - 1, 9)", y en el corpus es el mismo numero
 *       que el 512 de amdgpu_vm_pt.c:88 y que la mascara 0x1ff de :109.
 *
 *   RX550_VMID1_BLOCK_OFFSET = 9     gmc_v8_0.c:933-934
 *       El offset del CAMPO PAGE_TABLE_BLOCK_SIZE = block_size - 9.
 *
 * POR QUE NO SE UNIFICAN LOS DOS 9, aunque valgan lo mismo:  porque un cambio
 * en el campo y un cambio en el ancho de nivel son dos hechos distintos, y un
 * solo nombre obligaria a cambiar los dos a la vez sin que nadie lo decidiera.
 * El Project ya lo dice de esta familia en rx550_vm_geom.h:95-100, y por eso
 * la fusion que D4 propedia para uno de ellos NO se ha hecho. */
#define RX550_VMID1_BITS_POR_GB		18u
#define RX550_VMID1_NIVEL_MIN_BITS	9u

/* ── HARDWARE_REQUIREMENT: LIMITE DEL ROOT ──────────────────────────────────
 * mmVM_CONTEXT1_PAGE_TABLE_BASE_ADDR__PHYSICAL_PAGE_NUMBER  mask 0xfffffff
 * Son 28 bits de NUMERO DE PAGINA, no de direccion.  El tope en bytes sale de
 * aqui:  2^28 * 4 KiB = 2^40. */
#define RX550_PT_BASE_PN_MASK		UINT32_C(0x0FFFFFFF)
#define RX550_PT_BASE_PN_BITS		28u

/* ── HARDWARE_REQUIREMENT: LIMITE DE UNA HOJA ───────────────────────────────
 * gmc_v8_0.c:707  PDE 39:1 physical base address of PTE
 * Es un campo de DIRECCION, de 39 bits, no un numero de pagina.
 *
 * Y AQUI ESTA LA DISTINCION QUE HAY QUE GUARDAR, y que es facil perder:
 *
 *   root  ->  28 bits de NUMERO DE PAGINA  ->  tope 2^28 paginas = 2^40 bytes
 *   hoja  ->  39 bits de DIRECCION en BYTES ->  tope 2^39 bytes, y el hardware
 *             exige ademas los bits 5:1 a cero
 *
 * Los dos topes NO son el mismo numero y no se pueden aplicar uno al otro:
 *
 *   · una hoja en 8 GiB ocupa 33 bits como DIRECCION.  Una comprobacion que
 *     le exigiera 28 bits al valor crudo la rechazaria, y es valida.
 *   · un root en 8 GiB son 2^21 paginas, que SI caben en 28.
 *
 * Es decir: el mismo numero de bits significa cosas distintas segun sea el
 * campo, y por eso hay dos validadores y no uno. */
#define RX550_PDE_ADDR_MASK		UINT64_C(0x000000FFFFFFFFFF)
#define RX550_PDE_ADDR_BITS		39u
#define RX550_PDE_ADDR_SHIFT		1u	/* el campo arranca en el bit 1 */

/* ── HARDWARE_REQUIREMENT: PRECONDICION DE DIRECCION DE UN PDE ──────────────
 * gmc_v8_0.c:715  BUG_ON(*addr & 0xFFFFFF0000000FFFULL)
 *   bits  0..11  ->  la direccion tiene que estar alineada a 4 KiB
 *   bits 40..55  ->  no hay nada por encima del bit 39
 * Y esa alineacion es lo que cumple "bits 5:1 must be 0" (gmc_v8_0.c:708),
 * porque addr[11:0] == 0 implica addr[6:2] == 0. */
#define RX550_PDE_ADDR_PRECOND_MASK	UINT64_C(0xFFFFFF0000000FFF)

/* ── HARDWARE_REQUIREMENT: LAYOUT DEL PDE ───────────────────────────────────
 * gmc_v8_0.c:704-709 */
#define RX550_PDE_VALID_BIT		0u
#define RX550_PDE_VALID_MASK		(UINT64_C(1) << RX550_PDE_VALID_BIT)

/* El campo de direccion, en DOS formas, y la distincion no es cosmetica.
 *
 *   FIELD_MASK        el valor del campo tal cual lo calcula el encoder: 39 unos
 *   PLACED_MASK       ese mismo valor ya colocada en su sitio dentro de la
 *                     entrada de 64 bits, o sea ocupando los bits 39:1
 *
 * Comparar FIELD_MASK contra una mascara de direccion es un error de uno:  el
 * campo arranca en el bit 1, no en el bit 0.  Los _Static_assert de abajo
 * existen para que ese error no pueda volver a colarse. */
#define RX550_PDE_FIELD_MASK		UINT64_C(0x7FFFFFFFFF)		/* valor: 39 unos, bits 0..38 */
#define RX550_PDE_FIELD_PLACED_MASK	UINT64_C(0x000000FFFFFFFFFE)	/* colocado: bits 39:1 */
#define RX550_PDE_RESERVED_MASK		UINT64_C(0x00FFFF0000000000)	/* 58:40 */
#define RX550_PDE_FRAG_SHIFT		59u			/* 63:59 */
#define RX550_PDE_FRAG_BITS		5u
#define RX550_PDE_FRAG_MASK		(UINT64_C(0x1F) << RX550_PDE_FRAG_SHIFT)

/* ── DISENO: bits 63:59 ─────────────────────────────────────────────────────
 * "block fragment size".  El corpus lo NOMBRA y no lo ESCRIBE nunca en GFX8,
 * porque la unica funcion que construye flags de PDE esta vacia:
 *
 *   gmc_v8_0.c:712-716  gmc_v8_0_get_vm_pde()  { BUG_ON(...); }   <- sin flags
 *   gmc_v8_0.c:718-729  gmc_v8_0_get_vm_pte()  { ... EXECUTABLE ... }
 *
 * Se escribe CERO, y no porque se suponga que sea el valor correcto, sino
 * porque con block_size 9 no hay fragmento que describir:  una ventana de
 * 1 GiB repartida en 512 paginas PTE son 2 MiB por pagina, y 2 MiB es
 * exactamente una pagina.  El valor 0 describe la geometria derivada.
 *
 * NO ES UNA AFIRMACION DE QUE EL HARDWARE ESPERE 0.  Si esperase otra cosa, el
 * sintoma seria "la tabla se lee mal", y eso lo mide un MMIO_TEST del nodo de
 * integracion, no este. */
#define RX550_PDE_FRAG_POLICY		RX550_PDE_FRAG_ZERO
#define RX550_PDE_FRAG_ZERO		UINT64_C(0)

/* ═══════════════════════════════════════════════════════════════════════════
 * ERRORES
 *
 * Todos distintos, ninguno ambiguo, ninguno compartido entre causas que el
 * llamante tenga que tratar de forma distinta.
 * ═══════════════════════════════════════════════════════════════════════════ */
enum rx550_vmid1_err {
	RX550_PGT_OK				=   0,
	RX550_PGT_ERR_VM_SIZE			=  -1,	/* 0, no multiplo de 4 KiB */
	RX550_PGT_ERR_OVERFLOW			=  -2,	/* la aritmetica se desborda */
	RX550_PGT_ERR_UNSUPPORTED_LEVEL		=  -3,	/* num_level != 1 */
	/* MEDIDO 2026-10-04, D2.  Este comentario decia "block_size != 9" y era
	 * FALSO:  la guarda de rx550_vmid1_pgt.c:256-258 acepta el RANGO
	 * [RX550_VMID1_BLOCK_SIZE_MIN, RX550_VMID1_BLOCK_SIZE_MAX], o sea [9, 24].
	 * Un comentario de un enum es exactamente el tipo de cadena que un humano
	 * cita como autoridad, asi que se escribe la condicion que el codigo
	 * comprueba de verdad.  El unico sitio donde el 9 sigue siendo el valor es
	 * el minimo del campo, y ese esta nombrado arriba. */
	RX550_PGT_ERR_UNSUPPORTED_BLOCK_SIZE	=  -4,	/* block_size fuera de [9, 24] */
	RX550_PGT_ERR_VM_SIZE_INCOHERENT	=  -5,	/* coverage != vm_size */
	RX550_PGT_ERR_NO_BACKING		=  -6,	/* entries == NULL */
	RX550_PGT_ERR_ROOT_UNALIGNED		=  -7,
	RX550_PGT_ERR_ROOT_UNREPRESENTABLE	=  -8,	/* no cabe en 28 bits de pagina */
	RX550_PGT_ERR_LEAF_UNALIGNED		=  -9,
	RX550_PGT_ERR_LEAF_UNREPRESENTABLE	= -10,	/* no cabe en 39:1 */
	RX550_PGT_ERR_INDEX_RANGE		= -11,	/* indice >= entradas */
	RX550_PGT_ERR_VA_OUT_OF_RANGE		= -12,	/* va >= coverage */
	RX550_PGT_ERR_INCONSISTENT		= -13,	/* objetos de escalas distintas */
};

/* ═══════════════════════════════════════════════════════════════════════════
 * GEOMETRIA
 *
 * Un solo tipo, y TODOS sus campos derivados.  No hay ningun campo que se
 * pueda escribir a mano sin pasar por rx550_vmid1_geometry().
 * ═══════════════════════════════════════════════════════════════════════════ */

/* El tipo de raiz que sale de la aritmetica.
 * amdgpu_vm.c:2441-2456  num_level 1 -> root_level = AMDGPU_VM_PDB0
 *                        num_level 0 -> dev_err, RECHAZADO
 * Los demas niveles existen en el corpus para ASICs que no son este. */
enum rx550_vmid1_root_type {
	RX550_ROOT_UNSET	= 0,
	RX550_ROOT_PDB0		= 1,	/* el unico demostrado para GFX8 */
};

struct rx550_vmid1_geom {
	uint64_t		vm_size_bytes;	/* ENTRADA, la que pidio el caller */
	uint32_t		num_level;	/* derivado */
	enum rx550_vmid1_root_type root_type;	/* derivado */
	uint32_t		block_size;	/* derivado, en bits */
	uint32_t		depth_field;	/* derivado: valor para PAGE_TABLE_DEPTH */
	uint32_t		block_size_field;/* derivado: valor para PAGE_TABLE_BLOCK_SIZE */
	uint32_t		entries_per_level;/* derivado: 2^block_size */
	uint64_t		level_bytes;	/* derivado: entries * 8 */
	uint32_t		pte_pages;	/* derivado: 2^block_size */
	uint32_t		pte_entries;	/* derivado: 2^block_size */
	uint64_t		root_bytes;	/* derivado: level_bytes */
	uint64_t		pte_page_bytes;	/* derivado: level_bytes */
	uint64_t		coverage_bytes;	/* derivado: 2^block_size * 2^block_size * 2^12 */
	uint32_t		start_pn;	/* derivado: 0 */
	uint32_t		end_pn;		/* derivado: (coverage>>12) - 1 */
	uint64_t		total_bytes;	/* derivado: root + pte_pages * pte_page */
	bool			valid;		/* solo true si todo lo anterior es coherente */
};

/* ═══════════════════════════════════════════════════════════════════════════
 * ROOT PDB0
 *
 * Tipo DISTINTO del de una pagina PTE.  No hay conversion entre ellos, y no
 * hay ninguna funcion que acepte uno donde espera el otro.
 *
 * El backing es PRESTADO:  el array lo pone el caller, y este modulo no reserva,
 * no libera y no sabe de donde vino.  Ver §PTE_PAGE_MEMORY más abajo.
 * ═══════════════════════════════════════════════════════════════════════════ */
struct rx550_vmid1_root {
	uint64_t		       *entries;	/* entries_per_level, en memoria ajena */
	uint64_t			bytes;		/* root_bytes de la geometria */
	uint64_t			bus;		/* direccion de BUS, 4 KiB alineada */
	uint32_t			count;		/* entries_per_level */
	bool				attached;
	bool				cleared;
};

/* ═══════════════════════════════════════════════════════════════════════════
 * PAGINA PTE
 *
 * Otro tipo.  Contiene PTE reales, no PDE.  Y su backing tambien es ajeno.
 * ═══════════════════════════════════════════════════════════════════════════ */
struct rx550_vmid1_pte_page {
	uint64_t		       *entries;	/* pte_entries, en memoria ajena */
	uint64_t			bytes;		/* pte_page_bytes de la geometria */
	uint64_t			bus;		/* direccion de BUS, 4 KiB alineada */
	uint32_t			count;		/* pte_entries */
	bool				attached;
	bool				cleared;
};

/* ─────────────────────────────────────────────────────────────────────────────
 * PTE_PAGE_MEMORY = EXTERNAL_BACKING
 *
 * Este modulo NO tiene dma_alloc_coherent, ni __get_free_pages, ni ningun
 * allocator.  Coupling el constructor puro al dispositivo haria que la
 * geometria, que es aritmetica, dejara de poderse testear sin hardware.
 *
 * El contrato es:  el caller aporta un array de pte_entries uint64_t, ya
 * alineado a 4 KiB y con su direccion de bus.  Este modulo lo escribe, lo
 * valida y lo limpia.  La propiedad fisica —de donde sale ese array, quien
 * lo libera, y si su direccion de bus es la que el puente entiende— es del
 * nodo PGT_BACKING_INTEGRATION, y aqui solo se exige que la direccion sea
 * representable en el campo del PDE.
 * ───────────────────────────────────────────────────────────────────────────── */

/* ═══════════════════════════════════════════════════════════════════════════
 * API
 * ═══════════════════════════════════════════════════════════════════════════ */

/* Geometria.  Deriva TODO desde vm_size_bytes.  vm_size_bytes == 0 es error.
 * No escribe memoria. */
int rx550_vmid1_geometry(uint64_t vm_size_bytes, struct rx550_vmid1_geom *out);

/* Engancha un root a un array externo.  Valida la alineacion y la
 * representabilidad de root_bus ANTES de aceptar nada. */
int rx550_vmid1_root_attach(struct rx550_vmid1_root *root,
			    const struct rx550_vmid1_geom *g,
			    uint64_t *entries, uint64_t root_bus);

/* Pone todas las entradas del root a cero, que es "no valida" porque el bit 0
 * es VALID en el PDE (gmc_v8_0.c:709).  Devuelve error si no esta enganchado. */
int rx550_vmid1_root_clear(struct rx550_vmid1_root *root);

/* Engancha una pagina PTE a un array externo, con la misma disciplina. */
int rx550_vmid1_pte_page_attach(struct rx550_vmid1_pte_page *page,
				const struct rx550_vmid1_geom *g,
				uint64_t *entries, uint64_t page_bus);

/* Pone todas las entradas de la pagina a cero, que es "no valida" porque el
 * bit 0 es VALID en el PTE (gmc_v8_0.c:702). */
int rx550_vmid1_pte_page_clear(struct rx550_vmid1_pte_page *page);

/* ── EL ENCODER DEL PDE ────────────────────────────────────────────────────
 *
 * NO es rx550_pte_encode().  No es el de rx550_pdb0.h.  No toca 5 ni 6, que
 * en un PDE estan dentro del campo de direccion.
 *
 *   pde = ((pte_page_bus >> 1) & 0x7FFFFFFFFF) << 1) | VALID
 * con 63:59 a cero segun RX550_PDE_FRAG_POLICY.
 *
 * Rechaza:  no alineado a 4 KiB, y por encima del bit 39.  Las dos cosas son
 * el BUG_ON de gmc_v8_0.c:715. */
int rx550_vmid1_pde_encode(uint64_t pte_page_bus, uint64_t *out_pde);

/* Lee la direccion de la pagina PTE de un PDE codificado. */
uint64_t rx550_vmid1_pde_decode(uint64_t pde);

/* Un PDE es representable si y solo si no tiene residuo:  valid a 1, el campo
 * de direccion con bits 5:1 a cero, 58:40 a cero, y 63:59 a cero. */
bool rx550_vmid1_pde_check(uint64_t pde);

/* ── EL ENCODER DEL PTE NO ESTA AQUI, Y ES DELIBERADO ─────────────────────
 * Poblar un PTE es trabajo de otro modulo, que ya existe:  el camino de
 * escritura de lote sobre un backing ajeno, con la regla de que se valida
 * todo antes de escribir el primer store.  Este modulo NO lo incluye, y por
 * eso rx550_vmid1_pgt.c no menciona ni rx550_pte_encode ni RX550_PTE_. */

/* ── INDEXADO ───────────────────────────────────────────────────────────────
 * Funciones PURAS:  misma entrada, misma salida, sin estado.
 * Devuelven error en vez de recortar. */
int rx550_vmid1_pde_index(const struct rx550_vmid1_geom *g, uint64_t va,
			  uint32_t *out_index);
int rx550_vmid1_pte_index(const struct rx550_vmid1_geom *g, uint64_t va,
			  uint32_t *out_index);

/* Los dos indices juntos, y la pagina que contiene la entrada. */
int rx550_vmid1_locate(const struct rx550_vmid1_geom *g, uint64_t va,
		       uint32_t *out_pde_index, uint32_t *out_pte_index);

/* ── VALIDADORES DE DIRECCION, SEPARADOS A PROPOSITO ───────────────────────
 *
 * Dos funciones, no una.  Aplicar el limite del root a una hoja rejecta
 * direcciones validas; aplicar el de la hoja a un root es mas laxo de lo que
 * el registro permite. */
bool rx550_vmid1_root_representable(uint64_t root_bus);
bool rx550_vmid1_leaf_representable(uint64_t leaf_bus);

/* El numero de pagina que se escribiria en PAGE_TABLE_BASE_ADDR.  Rechaza lo
 * que no quepa en los 28 bits, y NO trunca. */
int rx550_vmid1_root_base_pn(uint64_t root_bus, uint32_t *out_pn);

/* Texto del error, para diagnostico.  No para lógica de control. */
const char *rx550_vmid1_err_str(int rc);

/* ═══════════════════════════════════════════════════════════════════════════
 * INVARIANTES ESTATICAS
 *
 * Solo lo que es una PROPIEDAD DE REPRESENTACION y que un fallo romperia en
 * silencio.  Deliberadamente NO hay aqui ninguna asercion sobre num_level, ni
 * sobre block_size, ni sobre coverage:  esos son DERIVADOS de vm_size y se
 * validan en tiempo de ejecucion, porque hardcodearlos aqui seria
 * exactamente el error que este modulo existe para no cometer.
 * ═══════════════════════════════════════════════════════════════════════════ */
_Static_assert(RX550_VMID1_NIVEL_MIN_BITS == 9u,
		"el ancho minimo de nivel deducido del 512 de amdgpu_vm_pt.c:88 no es 9");
_Static_assert((1u << RX550_VMID1_NIVEL_MIN_BITS) == 512u,
		"9 bits de nivel son 512 entradas, o una pagina de 4 KiB con 8 B por entrada");
_Static_assert(RX550_VMID1_BLOCK_OFFSET == RX550_VMID1_BLOCK_SIZE_MIN,
		"el offset del campo y el minimo codificable son el mismo 9: el campo vale 0");
_Static_assert(RX550_VMID1_BITS_POR_GB == 18u,
		"el factor GiB -> pagina deducido de 2^30/2^12 no es 18");
_Static_assert(RX550_VMID1_ENTRY_BYTES == sizeof(uint64_t),
		"una entrada de tabla de VM no es un uint64_t");
_Static_assert(RX550_VMID1_ENTRY_BITS == 64u,
		"el ancho de entrada deducido de 8 B no es 64 bits");
_Static_assert(RX550_VMID1_PAGE_SHIFT == 12u,
		"el shift de pagina deducido de 4 KiB no es 12");
_Static_assert(RX550_PDE_VALID_BIT == 0u,
		"VALID esta en el bit 0 tanto en el PDE como en el PTE");
_Static_assert((RX550_PDE_FIELD_MASK << RX550_PDE_ADDR_SHIFT)
		== RX550_PDE_FIELD_PLACED_MASK,
		"el campo colocado 39:1 no es FIELD_MASK desplazado");
_Static_assert(RX550_PDE_FIELD_PLACED_MASK == (RX550_PDE_ADDR_MASK & ~UINT64_C(1)),
		"el campo 39:1 no cubre exactamente los bits 39:1 de la direccion");
_Static_assert((RX550_PDE_FIELD_PLACED_MASK & RX550_PDE_RESERVED_MASK) == 0,
		"el campo de direccion invade los bits reservados 58:40");
_Static_assert((RX550_PDE_RESERVED_MASK & RX550_PDE_VALID_MASK) == 0,
		"VALID invade los bits reservados 58:40");
_Static_assert((RX550_PDE_FRAG_MASK & RX550_PDE_RESERVED_MASK) == 0,
		"los bits de fragmento no se solapan con los reservados");
_Static_assert((RX550_PDE_FIELD_PLACED_MASK & RX550_PDE_VALID_MASK) == 0,
		"el campo de direccion colocado no contiene el bit VALID");
_Static_assert((RX550_PDE_FIELD_PLACED_MASK & RX550_PDE_FRAG_MASK) == 0,
		"el campo de direccion colocado no toca los bits de fragmento");
_Static_assert(RX550_PDE_VALID_BIT == 0u,
		"VALID del PDE esta en el bit 0");
_Static_assert((RX550_PDE_ADDR_PRECOND_MASK & RX550_PDE_ADDR_MASK)
		== UINT64_C(0xFFF),
		"la parte baja del BUG_ON de gmc_v8_0.c:715 es la alineacion a 4 KiB");
_Static_assert((RX550_PDE_ADDR_PRECOND_MASK & ~RX550_PDE_ADDR_MASK)
		== UINT64_C(0xFFFFFF0000000000),
		"la parte alta del BUG_ON queda fuera del limite de 39 bits");
_Static_assert(RX550_PDE_ADDR_BITS == 39u,
		"el ancho del campo de direccion deducido de la mascara no es 39");
_Static_assert(RX550_PDE_FRAG_BITS == 5u,
		"el numero de bits de fragmento deducido no es 5");

#endif /* RX550_VMID1_PGT_H */
