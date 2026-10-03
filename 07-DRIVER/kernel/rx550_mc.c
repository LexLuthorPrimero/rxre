/* SPDX-License-Identifier: GPL-2.0 */
/*
 * rx550_mc.c -- la aritmetica de "donde vive la VRAM" y "cuanta hay".
 *
 * Ver rx550_mc.h para por que esto no esta junto a RREG32. Es C puro a
 * proposito: la parte que puede estar mal es la aritmetica y el rechazo, y esa
 * parte no necesita el kernel para comprobarse. Se comprueba en userspace desde
 * 07-DRIVER/tests/test_mc.c, sin hardware.
 *
 * LA DIVERGENCIA CON EL CODIGO DE REFERENCIA, y donde esta
 *
 * gmc_v8_0.c:560-567 hace esto:
 *
 *     tmp = RREG32(mmCONFIG_MEMSIZE);
 *     if (tmp & 0xffff0000) {
 *         drm_info(... "Probably bad vram size: 0x%08x", tmp);
 *         if (tmp & 0xffff)
 *             tmp &= 0xffff;
 *     }
 *     adev->gmc.mc_vram_size = tmp * 1024ULL * 1024ULL;
 *
 * El comentario de la 561 dice "some boards may have garbage in the upper 16
 * bits", y el codigo de la 564 solo enmascara cuando la mitad BAJA tiene algo.
 * Consecuencia medida, calculada y no supuesta:
 *
 *     CONFIG_MEMSIZE=0xffff0000 -> 4294901760 MiB
 *
 * que es el caso que el comentario describe y no el que corrige: la mitad baja
 * es cero, luego la condicion de la 564 es falsa y no se enmascara nada.
 *
 * Este driver SE NIEGA en ese caso. No es que seImprove el comportamiento: es
 * que un valor que no se sabe interpretar no se multiplica. Un
 * vram_end calculado sobre 4 petabytes no falla donde falla: no falla nunca, y
 * por eso es peor que un fallo.
 */

#include "rx550_mc.h"

/*
 * EL COSTE DE INCLUIR UN .c, y es real.
 *
 * Este fichero se INCLUYE en rx550_drv.c, no se enlaza aparte: la llamada a
 * pci_iomap de MMIO ocupa el .o del modulo, y un miembro con el nombre del
 * modulo no llega a compilarse nunca (07-DRIVER/kernel/Makefile, con el
 * reproductor). La contrapartida es que este .c y rx550_mmio.c caen en la MISMA
 * unidad de traduccion, y por eso lo que aqui es static tiene que llevar el
 * nombre del modulo dentro.
 *
 * No es una preferencia de estilo: la primera version de esta tabla se llamaba
 * `motivos`, igual que la de rx550_mmio.c, y el kernel la compilo con
 *
 *     rx550_mc.c:39:26: error: redefinicion de 'motivos'
 *
 * Un nombre static NO es invisible al linker dentro de un mismo .o. Es la
 * unica clase de colision que el patron de #include introduce, y por eso los
 * dos ficheros llevan el sufijo.
 */


static const char *const motivos_mc[] = {
	[RX550_MC_OK] =
		"CONFIG_MEMSIZE leido y dentro del tope declarado",
	[RX550_MC_MIEMBOS_ALTOS_SIN_SIGNAL] =
		"CONFIG_MEMSIZE tiene los 16 bits altos puestos y la mitad baja a cero: "
		"no se sabe si son basura o si el campo es mas ancho que 16 bits, y "
		"multiplicarlo no se puede corregir",
	[RX550_MC_TAMANO_NULO] =
		"CONFIG_MEMSIZE es cero: no es un tamano de VRAM, y con el vram_end se "
		"desbordaria por debajo",
	[RX550_MC_TAMANO_ABSURDO] =
		"CONFIG_MEMSIZE cuadra pero no cabe en el tope declarado por este driver",
	[RX550_MC_ENMASCARADO] =
		"CONFIG_MEMSIZE tiene bits altos y senal en la mitad baja: se toma la "
		"mitad baja, como hace el codigo de referencia",
};

const char *
rx550_mc_motivo(unsigned motivo)
{
	if (motivo >= sizeof(motivos_mc) / sizeof(motivos_mc[0]))
		return "motivo desconocido: eso es un fallo de la tabla, no del registro";
	if (!motivos_mc[motivo])
		return "motivo sin texto: eso es un hueco en la tabla, no un registro";
	return motivos_mc[motivo];
}

/*
 * rx550_mc_fb_base -- la direccion de inicio, en bytes.
 *
 * No puede fallar, y por eso devuelve el valor y no un estado. Los 16 bits que
 * quedan por debajo del 24 son cero POR REPRESENTACION, no por recorte: el
 * registro contiene los bits 24..39 de una direccion de 40, y la parte baja la
 * pone el hardware a cero. Por eso esta funcion no necesita un maximo, y por
 * eso rx550_mc_offset_ok() de la ventana no dice nada de esto.
 */
__u64
rx550_mc_fb_base(__u32 fb_location)
{
	return ((__u64)(fb_location & RX550_MC_FB_LOCATION_MASK))
		<< RX550_MC_FB_LOCATION_SHIFT;
}

/*
 * rx550_mc_memsize_mib -- el tamano en MiB, o un motivo por el que no se dice.
 *
 * La divergencia esta en MIEMBOS_ALTOS_SIN_SIGNAL y en NULO. ENMASCARADO
 * reproduce lo que hace el codigo de referencia porque ese caso SI esta
 * cubierto ahi, y no conviene divergir de un caso que funciona: la diferencia
 * entre aceptar y rechazar tiene que ser una decision, y esta es "aceptamos lo
 * que el otro acepta y rechazamos lo que el otro no sabe".
 */
int
rx550_mc_memsize_mib(__u32 config_memsize, __u32 *mib_out)
{
	__u32 tmp = config_memsize;
	__u64 mib;
	int enmascarado = 0;

	if (tmp & 0xFFFF0000u) {
		if (!(tmp & 0xFFFFu)) {
			/* La mitad baja a cero: no hay nada que enmascarar y nada
			 * que creer. El codigo de referencia sale de aqui con el
			 * valor entero y lo multiplica. */
			if (mib_out)
				*mib_out = 0;
			return RX550_MC_MIEMBOS_ALTOS_SIN_SIGNAL;
		}
		tmp &= 0xFFFFu;
		enmascarado = 1;
	}
	mib = tmp;

	if (mib == 0) {
		if (mib_out)
			*mib_out = 0;
		return RX550_MC_TAMANO_NULO;
	}

	if (mib > RX550_MC_MEMSIZE_MAX_MiB) {
		if (mib_out)
			*mib_out = (__u32)mib;
		return RX550_MC_TAMANO_ABSURDO;
	}

	if (mib_out)
		*mib_out = (__u32)mib;
	return enmascarado ? RX550_MC_ENMASCARADO : RX550_MC_OK;
}

/*
 * rx550_mc_vram_desde_registros -- el contrato entero.
 *
 * El borde SUPERIOR va incluido, porque el codigo de referencia lo incluye
 * (amdgpu_gmc.c:221 resta uno) y un borde que no coincide con el suyo no sirve
 * para comparar nada con lo que se ha observado.
 */
int
rx550_mc_vram_desde_registros(__u32 fb_location, __u32 config_memsize,
			      struct rx550_mc_vram *out)
{
	__u32 mib = 0;
	int r;

	if (!out)
		return RX550_MC_TAMANO_NULO;

	out->inicio = 0;
	out->fin = 0;
	out->crudo = config_memsize;
	out->mib = 0;
	out->motivo = RX550_MC_TAMANO_NULO;
	out->porque = rx550_mc_motivo(RX550_MC_TAMANO_NULO);

	r = rx550_mc_memsize_mib(config_memsize, &mib);
	if (r != RX550_MC_OK && r != RX550_MC_ENMASCARADO) {
		out->motivo = (__u32)r;
		out->porque = rx550_mc_motivo(r);
		return r;
	}

	out->mib = mib;
	out->inicio = rx550_mc_fb_base(fb_location);
	out->fin = out->inicio + ((__u64)mib * RX550_MC_MEMSIZE_MiB) - 1;

	/* Red de seguridad del contrato: si alguna vez se combinan un inicio y
	 * un final que no cuadran, es mejor devolver un motivo que una ventana
	 * con el final por debajo del inicio. */
	if (out->fin < out->inicio) {
		out->inicio = 0;
		out->fin = 0;
		out->motivo = RX550_MC_TAMANO_ABSURDO;
		out->porque = rx550_mc_motivo(RX550_MC_TAMANO_ABSURDO);
		return RX550_MC_TAMANO_ABSURDO;
	}

	out->motivo = (__u32)r;
	out->porque = rx550_mc_motivo(r);
	return r;
}