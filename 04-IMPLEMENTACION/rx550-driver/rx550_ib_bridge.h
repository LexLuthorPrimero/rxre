/* SPDX-License-Identifier: GPL-2.0 */
/*
 * rx550_ib_bridge.h — GPUVA -> IB -> PM4.  Frontera, no mecanismo.
 *
 *   TARGET = RX 550 instalada en esta maquina
 *   SCOPE  = EXCLUSIVO
 *
 * QUE ES
 *   El contrato minimo que va de un GPUVA ya publicado en la tabla GART a los DWORDs
 *   de PM4 que describen ese indirect buffer.  No asigna, no programa, no
 *   escribe en hardware, no toca el doorbell.
 *
 * QUE NO ES
 *   No es un allocator.  No es una PDB0.  No es un encoder de PM4.
 *   Reutiliza los tres por contrato, no por copia.
 *
 * LA FRONTERA QUE ESTE TIPO ENSEÑA
 *   GPUVA      lo que el shader ve, en el espacio de la GPU
 *   VRAM_OFFSET donde vive la tabla en la ventana de VRAM
 *   SYSTEM_PA  donde vive la RAM del sistema
 *   PM4_ADDR   lo que cabe en el campo de 48 bits del descriptor
 *
 *   Ninguno se convierte en otro sin una funcion explicita.  No hay un
 *   uint64_t que signifique "direccion" a secas.
 *
 * LO QUE ESTE COMPONENTE NO AFIRMA
 *   Que un IB publicado se ejecute.  Que el CP lo consuma.  Que la memoria
 *   cambie.  Eso no lo demuestra ningun estado de esta maquina, y la cadena de
 *   estados de abajo no tiene ninguna transicion que lleve ahi a proposito.
 */
#ifndef RX550_IB_BRIDGE_H
#define RX550_IB_BRIDGE_H

#include "rx550_spaces.h"
#include "rx550_vram.h"

/* ── HARDWARE_REQUIREMENT (rx550-pm4/pm4.h) ────────────────────────────── */
/*   addr_lo = gpu_va & 0xFFFFFFFC
 *   addr_hi = (gpu_va >> 32) & 0xFFFF
 *   => 48 bits de direccion, alineacion de 4 bytes.                     */
#define RX550_IB_ADDR_MASK	UINT64_C(0x0000FFFFFFFFFFFF)
#define RX550_IB_ADDR_ALIGN	4u

/* VMID: 16 bits segun el descriptor, y el rango util lo fija el hardware de
 * contextos, no este componente.  Ver RX550_IB_VMID_MAX. */
/* El campo VMID del descriptor tiene 16 bits y el tipo aqui es uint16_t.
 * Por construccion no puede desbordar, asi que NO hay comprobacion de rango:
 * una comprobacion que nunca puede fallar promete una garantia que no da.
 * Si algun dia el campo se ensancha, este es el sitio donde aparece el
 * rango, y el compilador avisara al anadir la comparacion imposible. */
#define RX550_IB_VMID_MAX	0xffffu

enum rx550_ib_state {
	RX550_IB_ABSENT = 0,
	RX550_IB_CREATED,	/* direccion y longitud declaradas        */
	RX550_IB_READY,		/* validadas, listo para codificar        */
	RX550_IB_PUBLISHED	/* DWORDs emitidos en un buffer de PM4     */
};

/* Los flags son los que el descriptor de PM4 define; este componente solo los
 * transports.  Que un flag concreto signifique algo es semantica de PM4. */
#define RX550_IB_FLAG_NONE	0u

struct rx550_ib_desc {
	struct rx550_gpuva	gpuva;
	uint32_t		length_dw;
	uint16_t		vmid;
	uint32_t		flags;
	bool			const_ib;
	enum rx550_ib_state	state;
	uint32_t		first_dw;	/* donde empieza en el buf  */
};

/* El tipo vive en rx550-pm4.  Se declara aqui, no se incluye: el puente
 * depende del encoder por contrato, y arrastrar su cabecera uniria dos
 * componentes que pueden evolucionar por separado. */
struct rx550_pm4_buf;

/* ── validacion.  Devuelve 0 si el descriptor es codificable. ─────────── */
int rx550_ib_validate(const struct rx550_ib_desc *d);

/* Motivo del rechazo, para diagnostico.  Devuelve 0 si valida. */
enum rx550_ib_reject {
	RX550_IB_OK = 0,
	RX550_IB_REJ_NULL,
	RX550_IB_REJ_STATE,
	RX550_IB_REJ_LEN_ZERO,
	RX550_IB_REJ_LEN_ALIGN,
	RX550_IB_REJ_ADDR_ALIGN,
	RX550_IB_REJ_ADDR_RANGE,
	RX550_IB_REJ_VMID
};
enum rx550_ib_reject rx550_ib_reject_of(const struct rx550_ib_desc *d);

/* ── ciclo de vida ──────────────────────────────────────────────────────── */

/* ABSENT -> CREATED. */
int rx550_ib_create(struct rx550_ib_desc *d, struct rx550_gpuva gpuva,
		    uint32_t length_dw, uint16_t vmid, uint32_t flags,
		    bool const_ib);

/* CREATED -> READY.  Valida.  Si no valida, NO avanza. */
int rx550_ib_make_ready(struct rx550_ib_desc *d);

/* ── FRONTERA CON PM4 ──────────────────────────────────────────────────── */
/* La unica funcion que toca el encoder.  Toma un buffer de PM4 ya existente;
 * no lo crea, no lo inicializa, no decide su tamano. */
int rx550_ib_emit(struct rx550_ib_desc *d, struct rx550_pm4_buf *pm4);

/* La direccion tal y como la tiene que ver el descriptor de PM4.  Se expone
 * para poder compararla con la que el encoder ESCRIBE, sin recalcularla. */
struct rx550_gpuva rx550_ib_pm4_address(const struct rx550_ib_desc *d);

/* ── limite explicito ──────────────────────────────────────────────────── */
/*
 *   PUBLISHED != CONSUMED != EXECUTED != COMPLETED
 *
 * Esta cadena de estados termina en PUBLISHED.  No existe transicion a
 * CONSUMED, ni a EXECUTED, ni a COMPLETED.  No es una omision pendiente: es
 * que ninguno de esos tres esta demostrado, y anadir la transicion seria
 * convertir un UNKNOWN en un hecho.
 */
static inline bool rx550_ib_is_executed(const struct rx550_ib_desc *d)
{
	(void)d;
	return false;	/* por construccion, no por falta de datos */
}

#endif /* RX550_IB_BRIDGE_H */
