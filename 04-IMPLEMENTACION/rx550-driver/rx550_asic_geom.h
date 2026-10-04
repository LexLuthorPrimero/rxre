/* SPDX-License-Identifier: GPL-2.0 */
/*
 * rx550_asic_geom.h — la geometria y la capacidad de ESTA RX 550, medidas, cada
 * una con su grado y con su cita.
 *
 *   TARGET = RX 550 instalada en esta maquina  (1002:699F, revision 0xC7)
 *   SCOPE  = EXCLUSIVO
 *
 * DE DONDE SALE
 *   08-ARQUITECTURA/CONSTANTES-GFX8-DRIVER.md   (el informe; §2, §4 y §7)
 *   MEDIDO_EN_LA_PIEZA  = leido de
 *       /sys/class/kfd/kfd/topology/nodes/1/properties
 *       /sys/class/kfd/kfd/topology/nodes/1/caches/N/properties  (N = 0..15)
 *   MEDIDO 2026-10-04 en esta maquina.  OJO: esa ruta NO se puede escribir con un
 *   asterisco dentro de este comentario,  porque "caches/" + "*" + "/properties"
 *   contiene la secuencia de cierre de comentario y trunca el bloque entero.
 *   Por eso va con N.
 *   que es una tabla CRAT de FIRMWARE, no un registro de silicio leido por
 *   ioctl.  AMD admite que la CRAT puede ir errada
 *   (kfd_topology.c:2166-2168).  Por eso el grado maximo de este fichero es
 *   CORROBORADO_2_VIAS y no PROVEN, y por eso lo que hay aqui se puede
 *   DESMENTIR con una relectura de sysfs.
 *
 * ESTE FICHERO NO INCLUYE NADA.  Ni libc, ni cabeceras del kernel, ni otros
 * componentes.  Los _Static_assert de abajo son aritmetica entera y se
 * evaluan sin ningun tipo.
 *
 * ============================================================================
 * §4.3 · LAS DOS CONSTANTES DE CU, Y POR QUE NO HAY UNA TERCERA
 * ============================================================================
 *
 * HAY DOS.  Y no es una manía de estilo:  hay DOS discriminantes medidos, en
 * DIRECCIONES OPUESTAS, sobre el MISMO registro de firmware.
 *
 * Los nueve campos de CU salen de un unico registro, el subtipo CRAT
 * `crat_subtype_computeunit` (kfd_crat.h:104-117), y el kernel los copia todos
 * en nueve lineas seguidas (kfd_crat.c:1036-1044).  El kernel despues reparte
 * ese mismo campo en dos consumidores que lo necesitan en unidades distintas.
 *
 *   RX550_NR_CU_CAPACIDAD = 8     CU QUE HAY.  Reparte por-CU.
 *   RX550_NR_CU_INDICE_MAX = 10   CU QUE HAY QUE CUBRIR AL INDEXAR.
 *
 * ── LADO (A): 8.  DISCRIMINANTE = cwsr_size. ────────────────────────────────
 *
 * MEDIDO: cwsr_size = 2789376, ctl_stack_size = 4096.
 * Se reprodujo con la aritmetica de kfd_queue.c:454-511, con lo que la propia
 * funcion del corpus declara, sobre los valores de CRAT de esta maquina:
 *
 *   cu_num      = simd_count / simd_per_cu = 32 / 4            = 8
 *   WG por CU   = 0x40000 + 0x4000 + 0x10000 + 0x1000         = 348160
 *                (kfd_queue.c:414,403,446,436; ninguna tiene override para
 *                 gfxv == 80003, comprobado leyendo las cuatro)
 *   wave_num    = min(cu_num*40, array_count/simd_arrays_per_engine*512)
 *               = min(8*40, 2/1*512) = min(320, 1024)          = 320
 *   wg_data     = ALIGN(8 * 348160, 4096)                     = 2785280
 *   ctl_stack   = ALIGN(40 + 320*8 + 8, 4096)                  = 4096
 *   cwsr        = ALIGN(ctl_stack + wg_data, 4096)             = 2789376  == MEDIDO
 *
 * Con cu_num = 10 salen ctl_stack = 4096 y cwsr = 3485696.  ctl_stack NO
 * discrimina (sale 4096 en los dos casos porque satura el ALIGN a pagina), asi
 * que el unico discriminante de este lado es cwsr_size.  Y dice 8.
 *
 * LO QUE 10 ROMPE EN ESTE LADO:  +25 % de sobre-reserva de contexto por CU, y
 * el techo de oleadas pasaria a 10*40 = 400 frente a los 320 reales.  El fallo
 * es SILENCIOSO: no hay error, solo memoria reservada de mas.
 *
 * ── LADO (B): 10.  DISCRIMINANTE = las 16 caches publicadas. ───────────────
 *
 * MEDIDO: 16 entradas en nodes/1/caches, todas de nivel 1, linea de 64 B, 12
 * de 16 KiB y 4 de 32 KiB.  NO hay nivel 2.  Los processor_id_low de las 16
 * valen simd_id_base + 1,2,3,4,6,7,8,9 (con repeticiones), y simd_id_base
 * = 2147487744.
 *
 * kfd_crat.c:1173-1189 reparte cada entrada al nodo que le toca asi:
 *
 *     total_num_of_cu = array_count * cu_per_simd_array     ( = 2 * 5 = 10 )
 *     if (id >= simd_id_base && id < simd_id_base + total_num_of_cu)
 *
 * Aplicando ese test a los ids REALES de las 16 entradas:
 *
 *     total_num_of_cu =  8  ->  publica 12 de 16
 *     total_num_of_cu =  9  ->  publica 13 de 16
 *     total_num_of_cu = 10  ->  publica 16 de 16      <== MEDIDO
 *
 * El hecho medido son 16, luego total_num_of_cu >= 10.
 *
 * Que las 16 sean reales y no el relleno: kfd_crat.c:968-1019 define una tabla
 * estatica `dummy_cache_info` de 5 entradas, y una de ellas es un L2 de 2048
 * KiB.  No hay L2 medido, luego las 16 vienen del CRAT de esta maquina.
 *
 * LO QUE 8 ROMPE EN ESTE LADO:  los ids base+8 y base+9 quedan fuera del span
 * y 4 de las 16 entradas de cache no se publican.  Tampoco hay error.
 *
 * ── POR QUE NO SE UNIFICA ─────────────────────────────────────────────────
 *
 * Un solo #define usado en las dos familias de decision esta GARANTIZADO que
 * falla en una de ellas, y el fallo es silencioso en las dos.  Las dos cifras
 * no reconcilian porque NO SON LA MISMA MAGNITUD:  una es un recuento de
 * unidades de compute y la otra es un span de identificadores.  Por eso el
 * nombre de la segunda dice INDICE_MAX y no CU.
 *
 * NO SE AFIRMA que num_cu_per_array signifique "SIMD por array" en vez de "CU
 * por array".  Encaria con el 5 y con el 10 y explicaria por que el conflicto
 * lleva tanto tiempo vivo, pero es una HIPOTESIS sin comprobar y no se usa
 * para nada de lo que hay aqui.
 *
 * REFUTADOR DE ESTA SEccion, el que sea:  una relectura de sysfs con
 * cwsr_size != 2789376 refuta el lado (A);  una relectura con menos de 16
 * entradas en nodes/1/caches refuta el lado (B).  Y refutaria a los dos a la
 * vez una lectura de `max_cu_per_sh` que valiera 4 (2 arrays x 4 CU/array),
 * que es el otro lado de la cuenta de §2.2.
 *
 * ============================================================================
 * LO MEDIDO QUE SOSTIENE A ESAS DOS, Y LO QUE NO ESTA
 * ============================================================================
 */
#ifndef RX550_ASIC_GEOM_H
#define RX550_ASIC_GEOM_H

/* ── §4.3 · LAS DOS.  NOMBRES FIJADOS POR EL INFORME ──────────────────────── */
#define RX550_NR_CU_CAPACIDAD	8u	/* CU que hay: CWSR, stack, oleadas, ocupacion */
#define RX550_NR_CU_INDICE_MAX	10u	/* span de ids que hay que cubrir al indexar   */

/* ── MEDIDO_EN_LA_PIEZA · la entrada de las dos cuentas ───────────────────── */
#define RX550_ASIC_SIMD_COUNT			32u
#define RX550_ASIC_SIMD_PER_CU			4u
#define RX550_ASIC_ARRAY_COUNT			2u
#define RX550_ASIC_SIMD_ARRAYS_PER_ENGINE	1u
/* CONFLICTADO: 2 * 5 = 10 no reconcilia con 32 / 4 = 8.  Ver §4.3.  No es un
 * error tipografico descartable: las dos cifras son load-bearing. */
#define RX550_ASIC_CU_PER_SIMD_ARRAY		5u
#define RX550_ASIC_SIMD_ID_BASE			2147487744u

/* ── MEDIDO_EN_LA_PIEZA · el otro lado del discriminante (A) ─────────────── */
#define RX550_ASIC_CTL_STACK_MEDIDO		4096u	/* B    */
#define RX550_ASIC_CWSR_MEDIDO			2789376u	/* B    */

/* ── DERIVADO · los cuatro sumandos de kfd_queue.c:454-511, con su cita ──── */
#define RX550_ASIC_OLAADAS_POR_CU		40u	/* kfd_queue.c:459            */
#define RX550_ASIC_OLAADAS_POR_ARRAY		512u	/* kfd_queue.c:460            */
#define RX550_ASIC_BYTES_CTX_POR_CU		348160u	/* 0x55000; :414,:403,:446,:436 */
#define RX550_ASIC_BYTES_PILA_POR_OLAADA	8u	/* kfd_queue.c:476, gfxv < 100100 */
#define RX550_ASIC_BYTES_CABECERA_CWSR		40u	/* kfd_queue.c:478            */
#define RX550_ASIC_WAVE_TECHO			320u	/* min(8*40, 2/1*512)         */

/* ── MEDIDO_EN_LA_PIEZA · el otro lado del discriminante (B) ─────────────── */
#define RX550_ASIC_NR_CACHE			16u
#define RX550_ASIC_CACHE_LINE_SIZE		64u	/* B */
#define RX550_ASIC_CACHE_NIVEL_MAX		1u	/* la AUSENCIA de L2 esta medida */
#define RX550_ASIC_CACHE_ID_MIN_OFFSET		1u	/* processor_id_low - simd_id_base */
#define RX550_ASIC_CACHE_ID_MAX_OFFSET		9u

/* ============================================================================
 * MEDIDO SIN CONSUMIDOR TODAVIA
 *
 * Estas cuatro estan medidas y citadas, y aun no las usa nadie:  el driver
 * todavia no ha llegado al shader ni al planificador de colas.  Se escriben
 * con lo que NO autorizan al lado, que es la parte util de escribirlas pronto.
 *
 * NO SE ESCRIBEN, Y POR QUE:
 *
 *   max_hw_contexts = 8   (gfx_v8_0.c:1688)   NO_DETERMINED_QUE_OBJETO
 *       Choca con dos constantes del driver que ninguna esta corroborada:
 *       TVM_NR_CTL_CONTEXTS 2 (target_vm.h:66) y RX550_GMC_NR_VMIDS 16
 *       (rx550_mmio_access.c:762).  Sin saber si "max_hw_contexts" (tope de
 *       contextos de hardware simultaneos) es el MISMO objeto que "NR_CTL_
 *       CONTEXTS" (cuenta de contextos de control del driver), escribir 8
 *       crearia una cuarta autoridad sin resolver las otras dos.  FALTA EL
 *       CRITERIO:  la definicion de TVM_NR_CTL_CONTEXTS en su propio .c.
 *       PROPIETARIO del cierre:  ahi.
 *
 *   mem_clk_max = 1500    NO_DETERMINED_LA_UNIDAD
 *       El valor esta medido (nodes/1/mem_banks/0/properties).  Que sea MHz NO
 *       esta verificado:  no hay en el corpus ningun sitio donde se declare la
 *       unidad.  Multiplicarlo por el ancho de linea daria un ancho de banda
 *       con una unidad inventada.  NO SE ESCRIBE hasta que la unidad exista.
 *       PROPIETARIO del cierre:  la documentacion HSA/KFD.
 *
 *   bytes de un slot de scratch   NO_DETERMINED
 *       Ni el kernel, ni sysfs, ni ningun registro del corpus lo expone.  Sin
 *       el no se puede dimensionar la pagina de scratch.  PROPIETARIO:  el
 *       firmware del SQ/RLC.
 *
 *   descomposicion de las 24 colas de CP   NO_DETERMINED
 *       24 / 2 MEC = 12 es una division, no una geometria.  La verdad esta en
 *       cp_queue_bitmap, que se arma en kfd_device_queue_manager.c:97-101 y
 *       no es una constante.
 * ============================================================================
 */
#define RX550_ASIC_NUM_CP_QUEUES		24u
#define RX550_ASIC_NUM_SDMA_ENGINES		2u
#define RX550_ASIC_NUM_SDMA_QUEUES_POR_ENGINE	2u
#define RX550_ASIC_NUM_SDMA_QUEUES		(RX550_ASIC_NUM_SDMA_ENGINES * \
						 RX550_ASIC_NUM_SDMA_QUEUES_POR_ENGINE)
#define RX550_ASIC_CLK_FCOMPUTE_MAX_MHZ		1071u

/* ============================================================================
 * LOS DISCRIMINANTES, EN TIEMPO DE COMPILACION
 *
 * No son identidades que se cumplan para cualquier estado del driver:  cada
 * uno se CAE si alguien cambia el numero de CU por el otro lado, y por eso son
 * la puerta de §4.3 y no una decoracion.
 * ============================================================================
 */

/* (A) El recuento funcional de CU es la cuenta que el corpus usa. */
_Static_assert(RX550_NR_CU_CAPACIDAD * RX550_ASIC_SIMD_PER_CU
		       == RX550_ASIC_SIMD_COUNT,
		"el lado (A): 8 CU es lo que sale de simd_count / simd_per_cu");

/* (A) cwsr_size medido cierra con 8 y NO cierra con 10.  kfd_queue.c:495-511,
 * y las dos ramas estan calculadas aqui, no affirmadas. */
_Static_assert(RX550_NR_CU_CAPACIDAD * RX550_ASIC_BYTES_CTX_POR_CU
		       + RX550_ASIC_CTL_STACK_MEDIDO
		       == RX550_ASIC_CWSR_MEDIDO,
		"el lado (A): cwsr_size medido = ctl_stack + 8 CU * contexto");
_Static_assert(RX550_NR_CU_INDICE_MAX * RX550_ASIC_BYTES_CTX_POR_CU
		       + RX550_ASIC_CTL_STACK_MEDIDO
		       != RX550_ASIC_CWSR_MEDIDO,
		"el lado (A): con 10 CU el cwsr_size medido no cerraria (+25 %)");

/* (A) El techo de oleadas, y el mismo discriminante por el otro multiplicador.
 * Los DOS terminos se escriben:  si el segundo pasara a ser el que corta, el
 * techo de 320 dejaria de ser el minimo y este assert se caeria. */
_Static_assert(RX550_ASIC_WAVE_TECHO
		       == RX550_NR_CU_CAPACIDAD * RX550_ASIC_OLAADAS_POR_CU,
		"el techo de oleadas es el primer termino de kfd_queue.c:459");
_Static_assert(RX550_ASIC_WAVE_TECHO
		       <= ((RX550_ASIC_ARRAY_COUNT /
			    RX550_ASIC_SIMD_ARRAYS_PER_ENGINE)
			   * RX550_ASIC_OLAADAS_POR_ARRAY),
		"el segundo termino de kfd_queue.c:460 no es el que corta");
_Static_assert(RX550_NR_CU_INDICE_MAX * RX550_ASIC_OLAADAS_POR_CU
		       != RX550_ASIC_WAVE_TECHO,
		"el lado (A): con 10 CU el techo de oleadas serian 400, no 320");

/* (B) El span tiene que cubrir el id de cache mas alto que existe, porque si
 * no, kfd_crat.c:1187-1189 deja de publicar entradas.  Este es EL assert que
 * convierte "10" en una consecuencia y no en un numero. */
_Static_assert(RX550_NR_CU_INDICE_MAX
		       == RX550_ASIC_ARRAY_COUNT * RX550_ASIC_CU_PER_SIMD_ARRAY,
		"el lado (B): el span es array_count * cu_per_simd_array");
_Static_assert(RX550_NR_CU_INDICE_MAX > RX550_ASIC_CACHE_ID_MAX_OFFSET,
		"el lado (B): el span tiene que alcanzar el id de cache mas alto "
		"que existe, o kfd_crat.c:1187-1189 deja de publicar 4 de las 16");
_Static_assert(RX550_NR_CU_CAPACIDAD <= RX550_ASIC_CACHE_ID_MAX_OFFSET,
		"el lado (B): CAPACIDAD no llega al id de cache mas alto que existe, "
		"y por eso con 8 se publicarian 12 de las 16 y no 16");

/* Las dos cifras no son la misma magnitud, y por eso no se reconcilian. */
_Static_assert(RX550_NR_CU_CAPACIDAD < RX550_NR_CU_INDICE_MAX,
		"CAPACIDAD e INDICE_MAX son dos magnitudes distintas, no dos medidas "
		"de la misma: si coincidieran, el conflicto de §4.3 seria un error "
		"de tecleo y no una contradiccion del registro de firmware");

/* Las 16 entradas de cache: la ausencia de L2 esta medida (las 16 se leyeron y
 * ninguna es de nivel 2), luego esto es un hecho y no una suposicion. */
_Static_assert(RX550_ASIC_CACHE_NIVEL_MAX == 1u,
		"no hay L2 en esta placa: se leyeron las 16 entradas y ninguna es "
		"de nivel 2, y dummy_cache_info SI tiene un L2 de 2048 KiB");

#endif /* RX550_ASIC_GEOM_H */