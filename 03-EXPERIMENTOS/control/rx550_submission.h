/* SPDX-License-Identifier: GPL-2.0 */
/*
 * rx550_submission.h — direccion de codigo -> PM4.  Construccion, no ejecucion.
 *
 *   TARGET = RX 550 instalada en esta maquina  (1002:699F, Polaris12, GFX8)
 *   SCOPE  = EXCLUSIVO
 *
 * QUE ES
 *   El camino que va de "donde esta el codigo" a "los DWORDs de PM4 que le
 *   dicen al CP donde lo esta".  Convierte una direccion en BYTES a la
 *   unidad que el registro de shader espera, y emite el paquete.
 *
 * QUE NO ES
 *   No es un IB descriptor.  No es un allocator.  No conoce la GART.  No
 *   conoce el VMID.  No toca hardware.  No espera a nada.
 *
 * DE DONDE VIENE CADA COSA
 *   FACT  amdgpu/sid.h:531          PACKET3_SET_SH_REG = 0x76
 *   FACT  amdgpu/sid.h:532          PACKET3_SET_SH_REG_START = 0x2c00
 *   FACT  asic_reg/gca/gfx_8_0_d.h:1293   mmCOMPUTE_PGM_LO = 0x2e0c
 *   FACT  gfx_v8_0.c:1534           gpu_addr = (ib.gpu_addr + off) >> 8;
 *   FACT  gfx_v8_0.c:1535           PACKET3(PACKET3_SET_SH_REG, 2)
 *   FACT  gfx_v8_0.c:1536           mmCOMPUTE_PGM_LO - PACKET3_SET_SH_REG_START
 *   FACT  gfx_v8_0.c:1537-1538      lower_32_bits(gpu_addr), upper_32_bits
 *
 * UN TRAMPIO QUE ESTE COMPONENTE EXISTE PARA EVITAR
 *   0x020c NO es el offset del registro.  mmCOMPUTE_PGM_LO es 0x2e0c.
 *   0x020c es lo que va EN EL PAQUETE: 0x2e0c - 0x2c00 = 0x020c.
 *   Son dos numeros que se parecen y significan cosas distintas.  Por eso
 *   hay dos tipos y no un solo uint32_t.
 *
 * LO QUE ESTE COMPONENTE NO AFIRMA
 *   Que el CP vaya a leer esa direccion.  Que exista un shader ahi.  Que
 *   el paquete se ejecute.  Que s_endpgm signifique nada.
 *   gfx803 == Polaris12 es NOT_DETERMINED y este fichero no lo presume.
 */
#ifndef RX550_SUBMISSION_H
#define RX550_SUBMISSION_H

#include <stdint.h>
#include <stdbool.h>
#include <stddef.h>

/* ── los dos numeros que no son el mismo numero ─────────────────────── */
#define RX550_PM4_PACKET_TYPE3		UINT32_C(3)		/* PACKET_TYPE3, vid.h:90 */
#define RX550_PM4_OPCODE_SET_SH_REG	UINT32_C(0x76)
#define RX550_PM4_REG_WINDOW_START	UINT32_C(0x2C00)
#define RX550_PM4_REG_WINDOW_END	UINT32_C(0x3000)

/* FACT: asic_reg/gca/gfx_8_0_d.h:1293 */
#define RX550_REG_COMPUTE_PGM_LO	UINT32_C(0x2E0C)

/* El valor que va EN EL PAQUETE, no en el registro.  Derivado:
 * 0x2E0C - 0x2C00 = 0x020C.  Mismo numero, otro espacio. */
#define RX550_PM4_OFF_COMPUTE_PGM_LO	UINT32_C(0x020C)

/* gfx_v8_0.c:1535 -- PACKET3(opcode, 2): dos DWORDs de valor. */
#define RX550_PM4_SET_SH_REG_COUNT	UINT32_C(2)

/* gfx_v8_0.c:1534 -- la direccion se codifica en unidades de 256 bytes. */
#define RX550_PROGRAM_ADDR_SHIFT	8u
#define RX550_PROGRAM_ADDR_UNIT		UINT64_C(256)

/* El paquete entero ocupa 4 DWORD: opcode|count, offset, LO, HI. */
#define RX550_PM4_SET_SH_REG_DWORDS	4u

/* ── tipos ──────────────────────────────────────────────────────────────
 * Tres espacios y tres unidades distintas.  La direccion del codigo esta
 * en BYTES.  El registro esta en el espacio de registros de la ASIC.  El
 * offset del paquete es un indice RELATIVO a la ventana del opcode.  Un
 * uint32_t unico no distinguiria los tres. */
struct rx550_code_address {
	uint64_t bytes;		/* direccion de codigo en la GPU, en BYTES */
};

struct rx550_program_address {
	uint64_t units;		/* la misma direccion, en unidades de 256 B */
};

struct rx550_pm4_register_offset {
	uint32_t value;		/* relativo a RX550_PM4_REG_WINDOW_START */
};

/* ── TASK A: la conversion ──────────────────────────────────────────────
 *
 * ESTA FIRMA CAMBIO.  Antes recibia (code_address, offset_within_code) y
 * hacia dos cosas: componer la direccion y codificarla.  La composicion
 * se movio a rx550_ib_composer.c, que es el unico sitio donde sumar la
 * direccion del IB con el offset del codigo significa algo.
 *
 * Aqui ya no hay offset, y por eso ya no hay overflow que comprobar: una
 * sola direccion no se desborda.  La comprobacion de overflow vive ahora
 * en el compositor, donde la suma ocurre de verdad.
 *
 * Lo que queda es una conversion de unidades, que es lo unico que este
 * componente sabe hacer.  No conoce el IB, no conoce el offset interno del
 * IB, y no podria aceptarlos aunque se los dieran: no son parametros.
 *
 * ALINEACION: DESIGN_CHOICE = REJECT.
 * El corpus no comprueba nada y trunca los 8 bits bajos en silencio.  Una
 * direccion truncada 37 bytes a la izquierda no es un error visible: el CP
 * leeria codigo de otra parte y no habria forma de saber por que.  Es la
 * misma politica que PA_POLICY = REJECT_UNALIGNED en la capa GART, y por
 * el mismo motivo.  No es un hecho del hardware: es una decision nuestra. */
int rx550_program_address_of(struct rx550_code_address base,
			     struct rx550_program_address *out);

/* ── TASK B: el offset del registro ─────────────────────────────────────
 * El corpus escribe la RESTA: mmCOMPUTE_PGM_LO - PACKET3_SET_SH_REG_START.
 * Se comprueba que el registro caiga dentro de la ventana, porque un
 * registro fuera de [0x2c00,0x3000) restado daría un numero que el
 * hardware no interpretaria como registro. */
int rx550_pm4_register_offset_of(uint32_t reg, struct rx550_pm4_register_offset *out);

static inline uint32_t rx550_pm4_register_addr(const struct rx550_pm4_register_offset o)
{
	return o.value + RX550_PM4_REG_WINDOW_START;
}

/* ── TASK C: la longitud ────────────────────────────────────────────────
 * El paquete observado lleva CUENTA de registros, no longitud de codigo.
 *   gfx_v8_0.c:1535   PACKET3(PACKET3_SET_SH_REG, 2)
 * Ese 2 es el numero de DWORDs de valor (LO y HI).  No es el tamano del
 * shader.  Por eso este componente no lleva CODE_SIZE: no hay ningun
 * paquete aqui que lo consuma, y meterlo seria inventar un campo. */
struct rx550_code_package {
	uint64_t code_size;	/* metadato del package, no del paquete PM4 */
};

/* ── TASK E: la emision ─────────────────────────────────────────────────
 *
 * Escribe 4 DWORD en dst, y solo si caben.  Devuelve el numero de DWORDs
 * escritos, o -1.  No hay emision parcial: si no caben 4, no se escribe
 * ninguno.  El mismo criterio del batch writer, por el mismo motivo.
 *
 * No depende de rx550-pm4.  Un ring buffer de emision es una estructura
 * con semantica propia y un ciclo de vida que aqui no se usa: la
 * unificacion costaria mas de lo que aporta, y este componente no necesita esa semantica: necesita un
 * sitio donde escribir cuatro numeros. */
int rx550_pm4_emit_compute_pgm(uint32_t *dst, uint32_t cap_dw,
			      struct rx550_pm4_register_offset reg,
			      struct rx550_program_address addr);

/* ── el paquete, para poder auditarlo sin hardware ───────────────────── */
struct rx550_pm4_packet {
	uint32_t	header;		/* PACKET3: type[31:30] count[29:16] opcode[15:8] */
	uint32_t	offset;		/* registro relativo a la ventana */
	uint32_t	addr_lo;
	uint32_t	addr_hi;
};

/* Reensambla un paquete ya escrito, para poder compararlo con lo esperado.
 * No es una conveniencia: es lo que permite que un test verifique el
 * contenido sin reinterpretar el buffer. */
void rx550_pm4_packet_of(const uint32_t *src, struct rx550_pm4_packet *out);

/* ── limite explicito ─────────────────────────────────────────────────
 *
 *   PM4_EMITTED != CONSUMED != EXECUTED != COMPLETED
 *
 * El estado de este componente termina en "los cuatro DWORDs estan en el
 * buffer".  No existe transicion a CONSUMED.  No hay ninguna forma de
 * observar las otras tres desde aqui, y anadirla seria rellenar un
 * UNKNOWN con un hecho. */
static inline bool rx550_submission_is_executed(void)
{
	return false;	/* por construccion, no por falta de datos */
}

#endif /* RX550_SUBMISSION_H */
