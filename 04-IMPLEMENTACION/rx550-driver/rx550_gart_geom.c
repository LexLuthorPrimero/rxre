/* SPDX-License-Identifier: GPL-2.0 */
/*
 * rx550_gart_geom.c — la aritmetica.  Puro.  Sin MMIO, sin kernel.
 *
 * Corresponde a amdgpu_gmc.c:294-336, amdgpu_gmc_gart_location(), con las
 * nueve expresiones puras de esa funcion en el mismo orden.
 *
 * DOS DIVERGENCIAS DELIBERADAS respecto del corpus, y las dos por escrito.
 * Un puerto que difiere sin decirlo es peor que no portar, porque el que lea
 * el codigo creera que el corpus hace lo que hacemos.
 *
 *   D1 · EL CLAMP.  amdgpu_gmc.c:307-310 encoge gart_size al hueco mayor y
 *       emite un dev_warn; la funcion es `void` y :292 dice que "will never
 *       fails".  Aqui se calcula igual, se marca `clamped`, y se devuelve
 *       RX550_GART_GEOM_ERR_NO_CABE.  Motivo: un GART mas pequeno de lo
 *       pedido es un fallo silencioso salvo que alguien lea el warn, y el
 *       consumidor de este componente ya sabe rechazar geometrias imposibles
 *       (rx550_gart_seq.c:408-421).  No queremos dos politicas distintas de
 *       degradacion en el mismo camino.
 *
 *   D2 · EL ALINEADO DE LA RAMA LOW.  amdgpu_gmc.c:320 usa
 *       ALIGN(mc->fb_end, four_gb) SIN +1, mientras que el calculo de
 *       size_af en :305 usa ALIGN(fb_end + 1, four_gb) CON +1.  La asimetria
 *       solo se nota cuando fb_end es multiplo exacto de 4 GiB: entonces
 *       ALIGN(fb_end, 4GiB) == fb_end y el GART empezaria EN EL ULTIMO BYTE de
 *       la VRAM, solapando un byte.  Aqui se usa ALIGN(fb_end + 1) en las dos.
 *       Con la geometria de esta tarjeta fb_end = 0xF47FFFFFFF, que no es
 *       multiplo de 4 GiB, asi que la divergencia NO se activa: es una
 *       correccion para un caso de borde que en esta placa no se da, escrita
 *       porque el componente no debe heredar un solape de un byte aunque esta
 *       tarjeta no lo alcance.
 *
 * LO QUE NO SE DIVERGE
 *   El clamp se sigue CALCULANDO (lo que importa para saber cuanto habia
 *   disponible), el min() con el hueco se sigue aplicando aunque en esta
 *   tarjeta sea un no-op, y la alineacion final a 4 GiB de :332 se sigue
 *   haciendo por igual para las tres politicas.
 */
#include "rx550_gart_geom.h"

/* (x + a - 1) & ~(a - 1).  Equivalente a ALIGN() del kernel, que en u64 es
 * exactamente esto (uapi/linux/const.h:48-49).  Se reimplementa en vez de
 * depender de la cabecera del kernel para que el .c compile en userspace. */
static uint64_t rx550_align_up(uint64_t x, uint64_t a)
{
	return (x + (a - 1)) & ~(a - 1);
}

int rx550_gart_geometry(const struct rx550_gart_geom_in *in,
			struct rx550_gart_geom *out)
{
	uint64_t max_mc_address;
	uint64_t fb_end;
	uint64_t size_below;
	uint64_t size_above;
	uint64_t gart_size;
	uint64_t gart_start;
	bool     clamped = false;

	if (in == NULL || out == NULL)
		return RX550_GART_GEOM_ERR_NULO;

	/* El registro garantiza que FB_BASE << 24 es multiplo de 16 MiB.  Se
	 * comprueba en vez de asumirlo: si algum dia alguien pasa una
	 * direccion ya desplazada, el algebra de los huecos deja de tener
	 * sentido y el fallo apareceria como "el GART no cabe". */
	if ((in->fb_base & (RX550_FB_BASE_ALIGN - 1)) != 0)
		return RX550_GART_GEOM_ERR_FB_DESALINEADO;
	if (in->vram_bytes == 0)
		return RX550_GART_GEOM_ERR_VRAM_CERO;
	if (in->gart_size == 0)
		return RX550_GART_GEOM_ERR_NO_CABE;

	/* amdgpu_gmc.c:299.  Para esta tarjeta el min se queda con mc_mask,
	 * porque el hueco esta por encima de los 40 bits.  Se conserva
	 * igualmente: es el tipo de cosa que no debe "simplificarse" sin
	 * decidirlo, porque si el rango MC creciera empezaria a importar. */
	max_mc_address = RX550_MC_MASK;
	if (RX550_GMC_HOLE_START - 1 < max_mc_address)
		max_mc_address = RX550_GMC_HOLE_START - 1;

	/* amdgpu_gmc.c:232-233 vía amdgpu_gmc.c:222.  fb_end NO viene de un
	 * registro: es fb_base + mc_vram_size - 1.  El campo FB_TOP del mismo
	 * registro no se lee nunca en esta ruta del corpus. */
	fb_end = in->fb_base + in->vram_bytes - 1;

	/* amdgpu_gmc.c:304-305 */
	size_below = in->fb_base;
	size_above = max_mc_address + 1 -
		     rx550_align_up(fb_end + 1, RX550_GART_FOUR_GB);

	/* amdgpu_gmc.c:307-310.  Se calcula igual que el corpus, pero el
	 * resultado NO se acepta en silencio: ver D1 de la cabecera del .c. */
	gart_size = in->gart_size;
	{
		uint64_t mayor = (size_below > size_above) ? size_below : size_above;

		if (gart_size > mayor) {
			gart_size = mayor;
			clamped = true;
		}
	}

	/* amdgpu_gmc.c:312-330.  Dos candidatos, ningun bucle: "BEST_FIT" es
	 * una politica de dos ramas, no un algoritmo de busqueda. */
	switch (in->placement) {
	case RX550_GART_PLACEMENT_LOW:
		/* :317-320, con la D2 del asympto */
		if (size_below >= gart_size)
			gart_start = 0;
		else
			gart_start = rx550_align_up(fb_end + 1,
						    RX550_GART_FOUR_GB);
		break;

	case RX550_GART_PLACEMENT_HIGH:
		/* :314 */
		gart_start = max_mc_address - gart_size + 1;
		break;

	case RX550_GART_PLACEMENT_BEST_FIT:
	default:
		/* :324-325.  Dos disjuntos: cabe abajo Y abajo es el hueco mas
		 * pequeño, o el de arriba no alcanza. */
		if ((size_below >= gart_size && size_below < size_above) ||
		    (size_above < gart_size))
			gart_start = 0;
		else
			gart_start = max_mc_address - gart_size + 1;
		break;
	}

	/* :332, por igual para las tres politicas, y por eso esta FUERA del
	 * switch. */
	gart_start &= ~(RX550_GART_FOUR_GB - 1);

	out->max_mc_address     = max_mc_address;
	out->fb_end             = fb_end;
	out->size_below         = size_below;
	out->size_above         = size_above;
	out->gart_size_effective = gart_size;
	out->clamped            = clamped;
	out->gart_start         = gart_start;

	/* :333 */
	out->gart_end = gart_start + gart_size - 1;

	/* Lo que el corpus no comprueba y este productor si. */
	if (out->gart_start > out->gart_end)
		return RX550_GART_GEOM_ERR_START_MAYOR_END;

	/* PAGE_TABLE_START_ADDR y PAGE_TABLE_END_ADDR llevan un
	 * PHYSICAL_PAGE_NUMBER de 28 bits con shift 12, o sea 40 bits de
	 * direccion (gmc_8_1_sh_mask.h).  Si el GART no cabe ahi, el hardware
	 * no puede direccionarlo y el plan de escrituras produciria un
	 * registro truncado sin avisar. */
	if ((out->gart_start >> RX550_PAGE_SHIFT) > RX550_GART_GEOM_PN_MAX)
		return RX550_GART_GEOM_ERR_FUERA_DE_PT;
	if ((out->gart_end >> RX550_PAGE_SHIFT) > RX550_GART_GEOM_PN_MAX)
		return RX550_GART_GEOM_ERR_FUERA_DE_PT;

	/* D1: el clamp se declara Y se rechaza.  Ver la cabecera del .c. */
	if (clamped)
		return RX550_GART_GEOM_ERR_NO_CABE;

	return RX550_GART_GEOM_OK;
}