/* SPDX-License-Identifier: GPL-2.0 */
/*
 * rx550_submission.c — una conversion y cuatro escrituras.  Nada mas.
 */
#include "rx550_submission.h"

int rx550_program_address_of(struct rx550_code_address base,
			     struct rx550_program_address *out)
{
	if (out == NULL)
		return -1;
	out->units = 0;

	/* Ya no se suma nada: la direccion de codigo llega TERMINADA.  Esta
	 * funcion paso de hacer composicion Y codificacion a hacer solo
	 * codificacion, y por eso ya no tiene un parametro de offset.  La
	 * suma vive en rx550_ib_composer.c, que es el unico sitio donde
	 * sumar la direccion del IB con el offset del codigo significa algo.
	 *
	 * Por eso aqui ya no hay overflow que comprobar: una sola direccion
	 * no se desborda.  La comprobacion esta donde la suma ocurre. */

	/* DESIGN_CHOICE = REJECT_UNALIGNED.  El corpus trunca estos ocho
	 * bits en silencio (gfx_v8_0.c:1534).  No se copia: una direccion
	 * truncada produce una ejecucion de otro codigo sin senal de error. */
	if ((base.bytes % RX550_PROGRAM_ADDR_UNIT) != 0)
		return -1;

	out->units = base.bytes >> RX550_PROGRAM_ADDR_SHIFT;
	return 0;
}

int rx550_pm4_register_offset_of(uint32_t reg,
				 struct rx550_pm4_register_offset *out)
{
	if (out == NULL)
		return -1;
	out->value = 0;

	/* Fuera de la ventana, la resta daria un numero que el hardware
	 * no leeria como registro.  No se escribe ese numero: se
	 * rechaza el registro. */
	if (reg < RX550_PM4_REG_WINDOW_START || reg >= RX550_PM4_REG_WINDOW_END)
		return -1;

	out->value = reg - RX550_PM4_REG_WINDOW_START;
	return 0;
}

int rx550_pm4_emit_compute_pgm(uint32_t *dst, uint32_t cap_dw,
			      struct rx550_pm4_register_offset reg,
			      struct rx550_program_address addr)
{
	if (dst == NULL)
		return -1;
	/* Todo o nada.  Si no caben cuatro, no se escribe ninguno: un
	 * paquete a medias en un ring es peor que no escribirlo. */
	if (cap_dw < RX550_PM4_SET_SH_REG_DWORDS)
		return -1;

	/* PACKET3(op, n) == (PACKET_TYPE3 << 30) | ((op & 0xFF) << 8)
	 *                   | ((n & 0x3FFF) << 16)      vid.h:105-107
	 * type en [31:30], count en [29:16], opcode en [15:8], byte bajo 0. */
	dst[0] = (RX550_PM4_PACKET_TYPE3 << 30) |
		  ((RX550_PM4_OPCODE_SET_SH_REG & UINT32_C(0xFF)) << 8) |
		  ((RX550_PM4_SET_SH_REG_COUNT & UINT32_C(0x3FFF)) << 16);
	dst[1] = reg.value;
	dst[2] = (uint32_t)(addr.units & UINT64_C(0xFFFFFFFF));
	dst[3] = (uint32_t)(addr.units >> 32);
	return (int)RX550_PM4_SET_SH_REG_DWORDS;
}

void rx550_pm4_packet_of(const uint32_t *src, struct rx550_pm4_packet *out)
{
	if (out == NULL)
		return;

	out->header = 0;
	out->offset = 0;
	out->addr_lo = 0;
	out->addr_hi = 0;

	if (src == NULL)
		return;

	out->header = src[0];
	out->offset = src[1];
	out->addr_lo = src[2];
	out->addr_hi = src[3];
}
