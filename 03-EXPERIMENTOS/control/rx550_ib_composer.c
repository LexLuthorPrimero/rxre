/* SPDX-License-Identifier: GPL-2.0 */
/*
 * rx550_ib_composer.c — la suma, una vez.
 */
#include "rx550_ib_composer.h"

int rx550_ib_gpu_address_make(uint64_t bytes, struct rx550_ib_gpu_address *out)
{
	if (out == NULL)
		return -1;
	out->bytes = 0;

	/* La alineacion se comprueba aqui, en el constructor, y no en la
	 * composicion.  Es el mismo hecho en los dos sitios, pero el
	 * error aparece donde se puede atribuir: una base desalineada es
	 * un fallo del allocator del IB, no del codigo que compone. */
	if ((bytes % RX550_PROGRAM_ADDR_UNIT) != 0)
		return -1;

	out->bytes = bytes;
	return 0;
}

int rx550_code_offset_make(uint64_t bytes, struct rx550_code_offset_bytes *out)
{
	if (out == NULL)
		return -1;
	out->bytes = 0;

	if ((bytes % RX550_PROGRAM_ADDR_UNIT) != 0)
		return -1;

	out->bytes = bytes;
	return 0;
}

int rx550_ib_code_address_of(struct rx550_ib_gpu_address base,
			     struct rx550_code_offset_bytes off,
			     uint64_t ib_length_bytes,
			     struct rx550_code_address *out)
{
	if (out == NULL)
		return -1;
	out->bytes = 0;

	if (ib_length_bytes == 0)
		return -1;

	/* OFFSET_BOUNDS.  El codigo vive dentro del IB, asi que su
	 * desplazamiento no puede salirse.  Esto NO lo comprueba el
	 * corpus: ahi las tablas son estaticas y estan alineadas por
	 * construccion.  Aqui el offset viene de un package, y un package
	 * puede decir cualquier numero. */
	if (off.bytes >= ib_length_bytes)
		return -1;

	/* OVERFLOW.  Con specifically: envolver aqui no da "una direccion
	 * alta", da una direccion BAJA que cabe dentro del IB y apunta a
	 * un sitio distinto. */
	if (base.bytes > UINT64_MAX - off.bytes)
		return -1;

	/* Las DOS alineaciones, por separado.  Ver la nota del header:
	 * comprobar la suma seria una guarda mas, y con mala diagnostica. */
	if ((base.bytes % RX550_PROGRAM_ADDR_UNIT) != 0)
		return -1;
	if ((off.bytes % RX550_PROGRAM_ADDR_UNIT) != 0)
		return -1;

	/* La unica suma con sentido del driver. */
	out->bytes = base.bytes + off.bytes;
	return 0;
}

int rx550_composer_emit_program(uint32_t *dst, uint32_t cap_dw,
				struct rx550_ib_gpu_address base,
				struct rx550_code_offset_bytes off,
				uint64_t ib_length_bytes,
				uint32_t *written)
{
	struct rx550_code_address code;
	struct rx550_program_address prog;
	struct rx550_pm4_register_offset reg;
	int n;

	if (written == NULL)
		return -1;
	*written = 0;

	/* La composicion ANTES de codificar.  Al reves, el resultado seria
	 * (base>>8) + offset, que no es una direccion de codigo sino una
	 * suma de una unidad y otra. */
	if (rx550_ib_code_address_of(base, off, ib_length_bytes, &code) != 0)
		return -1;
	if (rx550_program_address_of(code, &prog) != 0)
		return -1;

	if (rx550_pm4_register_offset_of(RX550_REG_COMPUTE_PGM_LO, &reg) != 0)
		return -1;
	n = rx550_pm4_emit_compute_pgm(dst, cap_dw, reg, prog);
	if (n < 0)
		return -1;

	*written = (uint32_t)n;
	return 0;
}

int rx550_composer_emit_dispatch(uint32_t *dst, uint32_t cap_dw,
				 struct rx550_dispatch_spec spec,
				 uint32_t *written)
{
	if (written == NULL)
		return -1;
	*written = 0;
	if (dst == NULL || cap_dw < RX550_PM4_DISPATCH_DWORDS)
		return -1;

	dst[0] = (RX550_PM4_PACKET_TYPE3 << 30) |
		  ((RX550_PM4_OPCODE_DISPATCH_DIRECT & UINT32_C(0xFF)) << 8) |
		  ((RX550_PM4_DISPATCH_COUNT & UINT32_C(0x3FFF)) << 16);
	dst[1] = spec.x;
	dst[2] = spec.y;
	dst[3] = spec.z;
	/* gfx_v8_0.c:1546  REG_SET_FIELD(0, COMPUTE_DISPATCH_INITIATOR,
	 *                               COMPUTE_SHADER_EN, 1)
	 * El registro entero vale 0 con ese bit puesto.  No se emiten mas
	 * campos: este es el unico que el corpus escribe aqui. */
	dst[4] = spec.shader_en ? UINT32_C(1) : UINT32_C(0);

	*written = RX550_PM4_DISPATCH_DWORDS;
	return 0;
}

int rx550_composer_emit_event_write(uint32_t *dst, uint32_t cap_dw,
				    uint32_t *written)
{
	if (written == NULL)
		return -1;
	*written = 0;
	if (dst == NULL || cap_dw < RX550_PM4_EVENT_WRITE_DWORDS)
		return -1;

	dst[0] = (RX550_PM4_PACKET_TYPE3 << 30) |
		  ((RX550_PM4_OPCODE_EVENT_WRITE & UINT32_C(0xFF)) << 8) |
		  ((RX550_PM4_EVENT_COUNT & UINT32_C(0x3FFF)) << 16);
	dst[1] = (RX550_PM4_EVENT_TYPE << 8) | RX550_PM4_EVENT_INDEX;

	*written = RX550_PM4_EVENT_WRITE_DWORDS;
	return 0;
}
