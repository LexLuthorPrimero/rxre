/* SPDX-License-Identifier: GPL-2.0-only */
/*
 * target_regs.h — base de datos semantica de registros para el primer camino.
 *
 * ALCANCE
 *   Registros necesarios para el camino end-to-end primero, y nada mas.
 *   No es un dump del mapa GFX8: son los registros que una lectura o escritura
 *   nossa puede Selective usar, con su consumidor y su confianza declarados.
 *
 * INVARIANTE CENTRAL — NO CONFUNDIR
 *
 *      register_index  x  4  =  byte_offset
 *
 *   El indice es una palabra de 32 bits dentro de la apertura.  El byte offset
 *   es donde cae dentro de esa palabra en la apertura.  Ejemplos reales:
 *      mmCP_RB0_RPTR            index 0x21c0 -> byte 0x8700
 *      mmCP_RB_WPTR_POLL_CNTL   index 0x21c2 -> byte 0x8708
 *      mmSCRATCH_REG0           index 0xc040 -> byte 0x30100
 *   Confundir ambos produce un acceso 4x desplazado y silenciosamente erroneo.
 *
 * SEPARACION QUE ESTA TABLA HACE EXPLICITA
 *      PCI bus address   direccion en el bus PCI      (resource_start)
 *      host mapping      VA de CPU del hueco mapeado  (component MMIO)
 *      __iomem pointer   base ioremap()                (component MMIO)
 *      register index    palabra dentro de la BAR     (esta tabla)
 *      byte offset       byte dentro de la palabra    (esta tabla)
 *
 * ESTA TABLA NO ES MMIO.  Declara indices y offsets; no mapea ni accede.
 *
 * PROCEDENCIA
 *   Los indices se.toml de las cabeceras del corpus, NO de memoria:
 *     .../include/asic_reg/gca/gfx_8_0_d.h
 *     .../include/asic_reg/gca/gfx_8_1_d.h
 *   Los diez coinciden en ambas, de modo que la tabla vale para GFX8.0 y
 *   GFX8.1 y la ambiguedad "cual de los dos" queda cerrada.
 *   tests/test_regs.c vuelve a leer esas cabeceras y falla si divergen.
 */
#ifndef TARGET_REGS_H
#define TARGET_REGS_H

/* Apertura de registros: BAR5, MEM32, 256 KiB.  Ver target_resource.h. */
#define TARGET_REG_BAR_SIZE	0x40000ULL

/* Confianza de cada entrada.  No es decorativa: decide si puede ser
 * consumidor de una decisión. */
enum target_reg_confidence {
	TARGET_REG_PROVEN	= 0,	/* observado en el corpus 7.1.3        */
	TARGET_REG_SUPPORTED	= 1,	/* derivado, con la regla declarada   */
	TARGET_REG_UNKNOWN	= 2,	/* no establecido                      */
};

struct target_reg_desc {
	const char	*name;		/* mnemonico GFX8                     */
	unsigned int	index;		/* palabra dentro de la BAR           */
	unsigned int	byte_offset;	/* index * 4                          */
	unsigned int	width;		/* bits: 32                           */
	const char	*access;	/* "R" | "W" | "RW"                   */
	const char	*writer;	/* quien lo escribe                    */
	const char	*reader;	/* quien lo lee                       */
	const char	*consumer;	/* para que lo usa NUESTRO driver     */
	const char	*purpose;	/* que demuestra                      */
	enum target_reg_confidence	conf;
};

/*
 * ORDEN POR byte_offset ASCENDENTE.  tests/test_regs.c lo comprueba, junto con
 * la no solapacion: una entrada mal ordenada o duplicada es un defecto real,
 * no una cuestion de estilo.
 */
static const struct target_reg_desc target_regs[] = {
{
	"mmGRBM_STATUS2",	0x2002, 0x8008, 32, "R",
	"hardware",
	"gfx_v8_0_is_idle() gfx_v8_0.c:4803",
	"precondicion de aislamiento antes de A y B",
	"idle autoritativo del driver: el registro debe valer exactamente 0x8, "
	"que significa todos los ME pipes y el RLC sin peticion pendiente",
	TARGET_REG_PROVEN
},
{
	"mmGRBM_STATUS",	0x2004, 0x8010, 32, "R",
	"hardware",
	"gfx_v8_0_is_idle() gfx_v8_0.c:4802",
	"precondicion de aislamiento antes de A y B",
	"GUI_ACTIVE (bit 31) debe ser 0. El driver NO comprueba los otros 25 bits "
	"de actividad; leerlos es una extension nuestra, no del driver",
	TARGET_REG_PROVEN
},
{
	"mmCP_BUSY_STAT",	0x219f, 0x867c, 32, "R",
	"hardware",
	"NINGUNO: el driver GFX8 no lo lee",
	"observacion adicional, NO sustituto del criterio del driver",
	"vector de actividad de 16 bits. SEM_CMDFIFO_NOT_EMPTY (0x1000) indica "
	"trabajo encolado; CE_PARSING_PACKETS (0x400000) es el Command Engine, "
	"o sea compute. Semantica por nombre de campo, no autoritativa del driver",
	TARGET_REG_SUPPORTED
},
{
	"mmCP_RB0_RPTR",	0x21c0, 0x8700, 32, "R",
	"command processor (hardware)",
	"NINGUNO: el driver no lo lee en ningun sitio",
	"observacion de CONSUMO, nunca de ejecucion",
	"puntero de lectura del ring 0, lo actualiza el hardware al hacer fetch. "
	"Es el ring 0 por definicion del nombre de registro; los compute rings "
	"necesitarian seleccion SRBM. NO convertible en indicador de ejecucion",
	TARGET_REG_PROVEN
},
{
	"mmCP_RB_WPTR_POLL_CNTL", 0x21c2, 0x8708, 32, "W?",
	"NUNCA: el driver no lo escribe para Polaris12",
	"NINGUNO",
	"configuracion de sondeo, solo lectura para el primer camino",
	"solo dos campos: POLL_FREQUENCY (0xffff, shift 0) e IDLE_POLL_COUNT "
	"(0xffff0000, shift 16). SIN bit de enable. El driver deja el valor por "
	"defecto del hardware; no se ha observado quien lo inicializa",
	TARGET_REG_PROVEN
},
{
	"mmCP_RB0_WPTR",	0x3045, 0xc114, 32, "W",
	"gfx_v8_0.c:4255 en init del ring",
	"NINGUNO: el driver no lo lee",
	"vista del hardware del WPTR del ring 0",
	"para el ring 0 esta direccion ES el doorbell: WDOORBELL32 escribe aqui. "
	"Por eso es a la vez el destino del doorbell y el estado del WPTR",
	TARGET_REG_PROVEN
},
{
	"mmCP_RB_WPTR_POLL_ADDR_LO", 0x3046, 0xc118, 32, "W",
	"gfx_v8_0.c:4263 en init del ring",
	"NINGUNO",
	"configuracion estatica: direccion sondeada",
	"low 32 bits de ring->wptr_gpu_addr. Programado una vez, nunca reescrito",
	TARGET_REG_PROVEN
},
{
	"mmCP_RB_WPTR_POLL_ADDR_HI", 0x3047, 0xc11c, 32, "W",
	"gfx_v8_0.c:4264 en init del ring",
	"NINGUNO",
	"configuracion estatica: direccion sondeada",
	"high 32 bits, enmascarado a 0xFF. Programado una vez, nunca reescrito",
	TARGET_REG_PROVEN
},
{
	"mmCP_RB_DOORBELL_CONTROL", 0x3059, 0xc164, 32, "RW",
	"gfx_v8_0_set_cpg_door_bell() gfx_v8_0.c:4213",
	"NINGUNO: el driver no lo lee",
	"precondicion observable de la intervencion del componente EP08",
	"configuracion, NO via de escritura: DOORBELL_EN (1 si ring->use_doorbell), "
	"DOORBELL_OFFSET = ring->doorbell_index, y CP_RB_DOORBELL_RANGE_LOWER "
	"(0x305a). El unico write fisico del doorbell es amdgpu_doorbell_mgr.c:65",
	TARGET_REG_PROVEN
},
{
	"mmSCRATCH_REG0",	0xc040, 0x30100, 32, "RW",
	"gfx_v8_0_ring_test_ring() gfx_v8_0.c:845,852",
	"gfx_v8_0_ring_test_ring() gfx_v8_0.c:856",
	"FUERA del camino del componente EP08",
	"registro de efecto del ring test. NO es observable de amdgpu_test_ib: "
	"ese test escribe en un slot del WB del driver, no aqui. 0xc040 cabe en "
	"0x40000, la apertura de registros",
	TARGET_REG_PROVEN
},
};

#define TARGET_NR_REGS	(sizeof(target_regs) / sizeof(target_regs[0]))

#endif /* TARGET_REGS_H */
