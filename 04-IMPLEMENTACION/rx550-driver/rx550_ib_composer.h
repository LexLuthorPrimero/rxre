/* SPDX-License-Identifier: GPL-2.0 */
/*
 * rx550_ib_composer.h — la suma que significa algo, en un solo sitio.
 *
 *   TARGET = RX 550 instalada en esta maquina  (1002:699F, Polaris12, GFX8)
 *   SCOPE  = EXCLUSIVO
 *
 * QUE ES
 *   La unica operacion del driver donde sumar dos numeros tiene sentido:
 *   la direccion GPU del IB mas el desplazamiento del codigo dentro de el.
 *   Vive aqui y en ningun otro sitio.  Si aparece un "+" de ese tipo en
 *   otro fichero, ese fichero esta mal.
 *
 * QUE NO ES
 *   No es un allocator.  No reserva el IB.  No conoce VMID, GPUVA, GART ni
 *   PDB0.  No administra la TLB.  No ejecuta hardware.  No incluye
 *   rx550_ib_bridge.h y no comparte ningun tipo con el.
 *
 * DE DONDE VIENE LA RELACION
 *   FACT  gfx_v8_0.c:1518   ib.ptr[i + (vgpr_offset/4)] = shader[i]
 *          el codigo del shader vive DENTRO del IB, no en otro buffer
 *   FACT  gfx_v8_0.c:1534   gpu_addr = (ib.gpu_addr + (u64)vgpr_offset) >> 8
 *          la direccion de codigo se deriva de la direccion del IB
 *   FACT  gfx_v8_0.c:1541   PACKET3(PACKET3_DISPATCH_DIRECT, 3)
 *   FACT  gfx_v8_0.c:1549   PACKET3_EVENT_WRITE, EVENT_TYPE(7)|EVENT_INDEX(4)
 *   FACT  amdgpu/sid.h:350  PACKET3_DISPATCH_DIRECT = 0x15
 *   FACT  amdgpu/sid.h:489  PACKET3_EVENT_WRITE     = 0x46
 *
 * LA FRONTERA QUE ESTE COMPONENTE MUEVE
 *   Antes:  rx550_program_address_of(code_address, offset_within_code)
 *           -> una sola llamada componia Y codificaba, y rx550_submission
 *              conocia el desplazamiento interno del IB.
 *   Ahora:  la suma vive aqui.  rx550_program_address_of() recibe una
 *           direccion de codigo YA compuesta y solo la codifica.
 *
 *   El motivo no es estetico: mientras el offset fuera parametro de
 *   submission, cualquier otro componente podia hacer esa suma sin que
 *   nadie comprobara la alineacion ni los limites.
 *
 * LO QUE ESTE COMPONENTE NO AFIRMA
 *   Que el IB exista, ni que su direccion sea correcta, ni que el CP lea
 *   lo que se escribe.  No hay ninguna validacion posible aqui sin hardware.
 */
#ifndef RX550_IB_COMPOSER_H
#define RX550_IB_COMPOSER_H

#include "rx550_submission.h"

/* ── los dos operandos que este componente es el unico autorizado a sumar ─
 *
 * rx550_ib_gpu_address   direccion GPU del IB.  Viene de un allocator de
 *                        SA, no de la GART y no de un VMID.  En este camino
 *                        concreto no hay VMID, no hay GPUVA y no hay GART:
 *                        amdgpu_ib_get(adev, NULL, ...)  [gfx_v8_0.c:1509]
 *
 * rx550_code_offset_bytes  desplazamiento del codigo DENTRO del IB, en
 *                        BYTES.  No en unidades de 256: esa conversion la
 *                        hace mas tarde, y por el camino equivocado seria
 *                        256 veces peor.
 *
 * Los dos son de 64 bits y podrian ser el mismo tipo.  No lo son, y esa es
 * la razon de existir del fichero. */
struct rx550_ib_gpu_address {
	uint64_t bytes;
};

struct rx550_code_offset_bytes {
	uint64_t bytes;
};

/* ── packets observados, sin semantica inventada ──────────────────────
 *
 * DISPATCH_COUNT = NOT_VERIFIED.  El corpus emite count=3 y cuatro DWORD de
 * payload.  No se normaliza contra SET_SH_REG, que si usa count=payload.
 * Se reemiten los valores observados y se deja constancia de que la
 * convencion no esta cerrada.
 *
 * EVENT_WRITE   = NOT_INTERPRETED.  Se emiten los dos valores observados y
 * no se afirma que hagan nada.  Es un packet que va donde el corpus lo
 * pone. */
#define RX550_PM4_OPCODE_DISPATCH_DIRECT	UINT32_C(0x15)
#define RX550_PM4_DISPATCH_COUNT		UINT32_C(3)	/* NOT_VERIFIED */
#define RX550_PM4_OPCODE_EVENT_WRITE		UINT32_C(0x46)
#define RX550_PM4_EVENT_COUNT			UINT32_C(0)
#define RX550_PM4_EVENT_TYPE			UINT32_C(7)
#define RX550_PM4_EVENT_INDEX			UINT32_C(4)

#define RX550_PM4_DISPATCH_DWORDS		5u	/* 1 header + 4 payload */
#define RX550_PM4_EVENT_WRITE_DWORDS		3u	/* 1 header + 2 payload */

struct rx550_dispatch_spec {
	uint32_t	x;
	uint32_t	y;
	uint32_t	z;
	bool		shader_en;	/* COMPUTE_DISPATCH_INITIATOR bit 0 */
};

/* ── la composicion ────────────────────────────────────────────────────
 *
 * Precondiciones, todas comprobadas y ninguna inferida:
 *   · ib_length_bytes > 0
 *   · offset < ib_length_bytes          <- el offset no puede salirse
 *   · base + offset no desborda uint64
 *   · base alineada a 256 B
 *   · offset alineado a 256 B
 *
 * LAS DOS ALINEACIONES SE COMPRUEBAN POR SEPARADO, y no la suma.
 * Comprobar (base + offset) % 256 seria la sexta guarda muerta del
 * proyecto: 0x100 + 0x100 = 0x200 esta alineado con los dos operandos
 * mal.  El resultado alineado no implica operandos alineados, y el
 * diagnostico tambien se pierde: base mal alineada es un fallo del
 * allocator del IB, offset mal alineado es un fallo del package, y con
 * una sola comprobacion los dos se reportan igual.
 *
 * OVERFLOW = REJECT.  Envolver a un valor bajo produciria una direccion de
 * codigo que CAE dentro del IB y apunta a otro sitio: peor que un error. */
int rx550_ib_code_address_of(struct rx550_ib_gpu_address base,
			     struct rx550_code_offset_bytes off,
			     uint64_t ib_length_bytes,
			     struct rx550_code_address *out);

/* Constructores.  No hay conversion implicita: para obtener uno de estos
 * tipos hay que pasar por aqui, y aqui se puede rechazar. */
int rx550_ib_gpu_address_make(uint64_t bytes, struct rx550_ib_gpu_address *out);
int rx550_code_offset_make(uint64_t bytes, struct rx550_code_offset_bytes *out);

/* ── la secuencia de packets ───────────────────────────────────────────
 *
 * El compositor ORDENA.  No interpreta el contenido de un SET_SH_REG, que
 * es cosa de rx550_submission, ni de un DISPATCH_DIRECT, que no tiene
 * consumidor en ningun sitio todavia.  Solo coloca.
 *
 * Secuencia observada (gfx_v8_0.c:1535-1550), por cada shader:
 *     SET_SH_REG  (programa)  ->  DISPATCH_DIRECT  ->  EVENT_WRITE
 *
 * El compositor expone las tres por separado, no una funcion que las tres.
 * La secuencia completa la decide quien compone, que es quien sabe si
 * emite uno o tres shaders. */
int rx550_composer_emit_program(uint32_t *dst, uint32_t cap_dw,
				struct rx550_ib_gpu_address base,
				struct rx550_code_offset_bytes off,
				uint64_t ib_length_bytes,
				uint32_t *written);

int rx550_composer_emit_dispatch(uint32_t *dst, uint32_t cap_dw,
				 struct rx550_dispatch_spec spec,
				 uint32_t *written);

int rx550_composer_emit_event_write(uint32_t *dst, uint32_t cap_dw,
				    uint32_t *written);

/* ── IB_LENGTH frente a CODE_LENGTH ─────────────────────────────────────
 *
 *   IB_LENGTH_BYTES  protege el offset.  Es un limite de seguridad de este
 *                    compositor.  No es un campo de ningun paquete.
 *
 *   CODE_LENGTH      es metadato del package.  Este compositor no lo
 *                    conoce y no lo necesita.  Confundirlos seria el
 *                    error: uno protege una direccion, el otro describe
 *                    un contenido.
 *
 *   PACKET_STREAM    no lleva ninguno de los dos.  DISPATCH_DIRECT lleva
 *                    dimensiones, no longitudes. */

/* ── limite explicito ──────────────────────────────────────────────────
 *
 *   COMPOSED != EMITTED != CONSUMED != EXECUTED != COMPLETED
 *
 * Este componente produce el primero y el segundo.  No hay transicion a
 * CONSUMED, ni a EXECUTED, ni a COMPLETED, y no la habra mientras la
 * unica forma de observarlas sea un hardware que no tenemos. */
static inline bool rx550_composer_is_executed(void)
{
	return false;	/* por construccion, no por falta de datos */
}

#endif /* RX550_IB_COMPOSER_H */
