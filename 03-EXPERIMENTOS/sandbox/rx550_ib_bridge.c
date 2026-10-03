/* SPDX-License-Identifier: GPL-2.0 */
/*
 * rx550_ib_bridge.c — implementacion.  CPU puro.  Sin kernel, sin device.
 */
#include "rx550_ib_bridge.h"
#include "pm4.h"

enum rx550_ib_reject rx550_ib_reject_of(const struct rx550_ib_desc *d)
{
	if (d == NULL)
		return RX550_IB_REJ_NULL;
	if (d->state != RX550_IB_CREATED && d->state != RX550_IB_READY)
		return RX550_IB_REJ_STATE;
	if (d->length_dw == 0)
		return RX550_IB_REJ_LEN_ZERO;
	if ((d->length_dw % RX550_IB_ADDR_ALIGN) != 0)
		return RX550_IB_REJ_LEN_ALIGN;
	/* El descriptor codifica la direccion con & 0xFFFFFFFC: una GPUVA
	 * desalineada perderia los dos ultimos bits en silencio. */
	if ((d->gpuva.bytes % RX550_IB_ADDR_ALIGN) != 0)
		return RX550_IB_REJ_ADDR_ALIGN;
	if ((d->gpuva.bytes & ~RX550_IB_ADDR_MASK) != 0)
		return RX550_IB_REJ_ADDR_RANGE;
	return RX550_IB_OK;
}

int rx550_ib_validate(const struct rx550_ib_desc *d)
{
	return rx550_ib_reject_of(d) == RX550_IB_OK ? 0 : -1;
}

int rx550_ib_create(struct rx550_ib_desc *d, struct rx550_gpuva gpuva,
		    uint32_t length_dw, uint16_t vmid, uint32_t flags,
		    bool const_ib)
{
	if (d == NULL)
		return -1;
	if (d->state != RX550_IB_ABSENT)
		return -1;		/* no se redefine un IB vivo */

	d->gpuva = gpuva;
	d->length_dw = length_dw;
	d->vmid = vmid;
	d->flags = flags;
	d->const_ib = const_ib;
	d->first_dw = 0;
	d->state = RX550_IB_CREATED;
	return 0;
}

int rx550_ib_make_ready(struct rx550_ib_desc *d)
{
	if (d == NULL)
		return -1;
	if (d->state != RX550_IB_CREATED)
		return -1;
	if (rx550_ib_validate(d) != 0)
		return -1;		/* no avanza si no valida */

	d->state = RX550_IB_READY;
	return 0;
}

struct rx550_gpuva rx550_ib_pm4_address(const struct rx550_ib_desc *d)
{
	struct rx550_gpuva a;
	a.bytes = 0;
	if (d != NULL)
		a.bytes = d->gpuva.bytes & RX550_IB_ADDR_MASK;
	return a;
}

int rx550_ib_emit(struct rx550_ib_desc *d, struct rx550_pm4_buf *pm4)
{
	uint32_t before;
	int r;

	if (d == NULL || pm4 == NULL)
		return -1;
	/* Solo se emite desde READY.  Publicar no es idempotente a proposito:
	 * emitir dos veces duplicaria el descriptor en el ring. */
	if (d->state != RX550_IB_READY)
		return -1;
	if (rx550_ib_validate(d) != 0)
		return -1;

	before = rx550_pm4_buf_count(pm4);
	d->first_dw = before;

	r = rx550_pm4_emit_ib_descriptor(pm4, d->gpuva.bytes, d->length_dw,
					d->vmid, d->flags,
					d->const_ib ? 1 : 0);
	if (r != 0)
		return -1;

	d->state = RX550_IB_PUBLISHED;
	return 0;
}
