/* SPDX-License-Identifier: GPL-2.0 */
/*
 * rx550_mc.h -- donde vive la VRAM, y cuanto hay, leido de dos bloques distintos.
 *
 * POR QUE ESTE FICHERO NO ES UN PAR DE CONSTANTES
 *
 * Porque "leer un registro" no es el contrato. El contrato es: qué se hace con
 * lo que viene, qué se RECHAZA y con qué motivo. Y en este caso el valor de
 * partida se rechaza a veces, porque hay un hueco medido en el codigo que hace
 * de referencia.
 *
 * EL HECHO DE PARTIDA
 *
 * La ventana de registros es BAR5 de 256 KiB (202), y en ella hay DOS registros
 * que contestan a la misma pregunta y estan en bloques de IP DISTINTOS:
 *
 *     mmMC_VM_FB_LOCATION   0x809    GMC 8.1   donde EMPIEZA la VRAM
 *                                               include/asic_reg/gmc/gmc_8_1_d.h:281
 *     mmCONFIG_MEMSIZE      0x150a   BIF 4.1   CUANTA hay
 *                                               include/asic_reg/bif/bif_4_1_d.h:33
 *
 * Que uno este en GMC y el otro en BIF es lo que hace que el mapa
 * bloque<->BAR siga siendo NOT_IN_CORPUS (176 §3) pese a saber ya cual es la
 * ventana: puede que hacer falta mas de una.
 *
 * REPRESENTACION, no opinion
 *
 * El codigo que hace de referencia (gmc_v8_0.c:411-422, rama "no soy VF", que
 * es la de esta GPU) hace:
 *
 *     base = RREG32(mmMC_VM_FB_LOCATION) & 0xFFFF;
 *     base <<= 24;
 *
 * y el consumidor (amdgpu_gmc.c:220-221):
 *
 *     mc->vram_start = base;
 *     mc->vram_end   = mc->vram_start + mc->mc_vram_size - 1;
 *
 * De ahi se sigue, sin suponer nada, que el registro NO guarda una direccion:
 * guarda los bits 24..39 de una direccion de 40 bits, y los de 0 a 23 son cero.
 * Eso explica por separado lo que el estado del proyecto anotaba como
 * vram_base_offset = 0: no es una constante de compilacion, es la FORMA que
 * tiene la representacion.
 *
 * LO QUE ESTA MEDIDO Y LO QUE NO
 *
 *   PROVEN        los dos offsets y el codigo que los lee y los consume
 *   DERIVATION    vram_start = (reg & 0xFFFF) << 24, y vram_end = start + size - 1
 *   OBSERVED      en esta placa vale 0x000000F400000000 - 0x000000F47FFFFFFF
 *                 (journalctl -k -b, sin root), y la aritmetica del consumidor
 *                 reproduce el segundo numero EXACTO
 *   PREDICCION    falsable, y es lo que comprobara este driver en cuanto exista
 *                 el mapa:  mmMC_VM_FB_LOCATION  tiene que leer 0x00000F40
 *                           mmCONFIG_MEMSIZE     tiene que leer 0x00000800
 *
 *   NO MEDIDO     los valores reales de los registros. Requieren el mapa.
 *
 * Y el segundo punto de la prediccion tiene un moreover: si CONFIG_MEMSIZE no
 * leyera 0x800, la cadena de 201 estaria refutada, y eso es una prueba que no
 * se puede hacer de otra manera.
 */

#ifndef _RX550_MC_H_
#define _RX550_MC_H_

/* __u32/__u64 y no u32/u64: los nombres cortos son typedef exclusive del kernel.
 * La regla esta escrita en rx550_pm4.h:18-20 y se incumplio una vez aqui. */
#include <linux/types.h>

/* findings/201: include/asic_reg/gmc/gmc_8_1_d.h:281 */
#define RX550_MC_FB_LOCATION		0x809
/* findings/202: include/asic_reg/bif/bif_4_1_d.h:33  (BIF 4.1, no GMC) */
#define RX550_MC_CONFIG_MEMSIZE		0x150a

/* El campo de FB_LOCATION son 16 bits que ocupan las posiciones 24..39.
 * El 24 sale de gmc_v8_0.c:418 y el 0xFFFF de gmc_v8_0.c:417. */
#define RX550_MC_FB_LOCATION_MASK	0xFFFFu
#define RX550_MC_FB_LOCATION_SHIFT	24u

/* CONFIG_MEMSIZE esta documentado en MIB, no en bytes. El *1024*1024 de
 * gmc_v8_0.c:567 con el comentario "size in MB on si" en la 559. */
#define RX550_MC_MEMSIZE_MiB		(1024ULL * 1024ULL)

/*
 * Tope de tamano. MODEL_CHOICE, no un hecho del ASIC: es el limite que este
 * driver se pone para poder decir "esto no es un tamano de VRAM" y negarse a
 * seguir. Sin el, un valor absurdo se multiplica en silencio y el error aparece
 * tres eslabones mas abajo, cuando ya no se parece a nada.
 *
 * 16 GiB, y el numero sale de una cuenta que el primer valor no hacia.
 *
 * La version anterior de esta constante era 64 GiB = 65536 MiB. El campo que
 * llega aqui tiene 16 bits y viene enmascarado, asi que lo UNICO que puede
 * expresar son 0..65535 MiB. Un tope de 65536 MiB no puede rechazar NADA que el
 * campo sea capaz de representar: es decorativo, y lo que worse, un rejected
 * check da la sensacion de que hay un filtro donde no lo hay.
 *
 * Por eso el tope tiene que estar ESTRICTAMENTE por debajo del maximo del
 * campo, y 16 GiB cumple las dos cosas a la vez:
 *
 *     por debajo de 65535 MiB   -> rechaza 65535, que es absurdo
 *     por encima de la VRAM real mas grande de esta generacion
 *                                 Polaris11 llega a 8 GB, y aqui el tope es el
 *                                 doble: 32 veces el 2048 MiB que dice el log
 *
 * Y es un MODEL_CHOICE, no un hecho del ASIC: si algun dia un chip de este
 * proyecto lo superara, lo que se mueve es ESTA constante y no la comprobacion.
 */
#define RX550_MC_MEMSIZE_MAX_MiB	(16ULL * 1024ULL)

/*
 * Motivos de rechazo. Se numeran para poder contarlos, y para que un rechazo
 * sin motivo no se confunda con un fallo de bus: un -ENODEV sin frase no
 * dice si el registro no estaba, si no cuadraba o si nadie lo leyo.
 */
enum rx550_mc_motivo {
	RX550_MC_OK = 0,
	/*
	 * Los 16 bits altos tienen algo Y la mitad baja es cero. Es el caso que
	 * describe el comentario del codigo de referencia y que NO corrige. Se
	 * detalla en rx550_mc_memsize_mib(), que es donde esta la divergencia.
	 */
	RX550_MC_MIEMBOS_ALTOS_SIN_SIGNAL,
	/* Ni un bit alto ni un bit bajo: 0 no es un tamano de VRAM. */
	RX550_MC_TAMANO_NULO,
	/* Cuadra, pero no cabe en el tope declarado. */
	RX550_MC_TAMANO_ABSURDO,
	/* Bits altos con senal en la mitad baja: se enmascara, como hace el
	 * codigo de referencia. Es el caso que SI corrige, y aqui se acepta
	 * por compatibility, pero se dice cual de los dos es. */
	RX550_MC_ENMASCARADO,
};

struct rx550_mc_vram {
	__u64	inicio;		/* bytes, borde inferior incluido */
	__u64	fin;		/* bytes, borde SUPERIOR incluido */
	__u32	crudo;		/* lo que decia CONFIG_MEMSIZE, sin tocar */
	__u32	mib;		/* MiB Validados */
	__u32	motivo;		/* enum rx550_mc_motivo */
	const char	*porque;	/* frase legible del motivo */
};

/*
 * El contrato entero en una llamada.
 *
 * Devuelve RX550_MC_OK y rellena `out` con la ventana de VRAM, o devuelve el
 * motivo del rechazo y deja `out` con inicio y fin a cero. NUNCA devuelve una
 * ventana a medias: un `fin` menor que `inicio` no es un estado, es un bug.
 */
int rx550_mc_vram_desde_registros(__u32 fb_location, __u32 config_memsize,
				  struct rx550_mc_vram *out);

const char *rx550_mc_motivo(unsigned motivo);

/*
 * Las dos mitades del contrato, por separado, porque se pueden probar sueltas.
 *
 * rx550_mc_fb_base()   solo la direccion: no puede fallar, y por eso devuelve
 *                      el valor en vez de un estado. Es aritmetica pura.
 * rx550_mc_memsize_mib()  solo el tamano: SI puede rechazarse.
 */
__u64 rx550_mc_fb_base(__u32 fb_location);
int rx550_mc_memsize_mib(__u32 config_memsize, __u32 *mib_out);

#endif /* _RX550_MC_H_ */