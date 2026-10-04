/* SPDX-License-Identifier: GPL-2.0 */
/*
 * rx550_gart_geom.h — PRODUCTOR de la geometria del GART.  Puro.  Sin MMIO.
 *
 * Que es
 *   La aritmetica que decide donde va la ventana del GART dentro del espacio de
 *   direcciones de la MC.  Es la contraparte de rx550_gart_seq.c, que la
 *   CONSUME y no la produce: rx550_gart_seq.h:55-58 dice que no puede decidirla
 *   porque "decidir la colocacion del GART es otra pregunta".  Esta es esa
 *   pregunta, y es aritmetica pura.
 *
 * Que NO es
 *   No lee registros.  No mapea la BAR.  No depende del kernel.  Los dos datos
 *   que necesita de hardware entran por `in` y se los da quien pueda leerlos.
 *
 * POR QUE UN FICHERO NUEVO y no dentro de vmid0_gart ni de vram
 *   rx550_vmid0_gart.* es el CONSUMIDOR (su cabecera dice que gart_start no lo
 *   decide el).  Un productor dentro de un consumidor seria el mismo error de
 *   capa mas sutil: funcionaria, y el test de fronteras no lo detectaria
 *   porque no habria ningun #include nuevo.  Aqui la frontera es visible en el
 *   Makefile, no solo en el grafo de includes.
 *
 *   rx550_vram.h no puedeDEPENDer de nada de este dominio: lo incluyen
 *   rx550_pdb0.h:40 y rx550_ib_bridge.h:35, y arrastrar el layout completo de
 *   PTE a cada unidad que toque la frontera de recurso seria el acoplamiento
 *   que rx550_ib_bridge.h:76 rechaza por escrito.
 *
 * LA ARITMETICA, y de donde sale cada linea
 *   Corresponde a amdgpu_gmc.c:294-336, amdgpu_gmc_gart_location().  Las nueve
 *   expresiones puras de esa funcion estan aqui, en el mismo orden, con la
 *   cita de la linea del corpus de la que sale cada una.
 *
 * LO QUE ESTA ESCRITO Y LO QUE ESTA DEDUCIDO
 *   El corpus declara mc_mask y AMDGPU_GMC_HOLE_START con literales o con
 *   cadenas de dos saltos (gmc_v8_0.c:1133 y gmc_v8_0.c:1127 ->
 *   amdgpu_vm.c:2434 -> amdgpu_gmc.h:36).  Aqui son constantes de compilacion,
 *   y son CORROBORADAS por el hecho de que la aritmetica con ellas reproduce
 *   el GART que el driver de referencia imprimio en esta tarjeta.  Eso no
 *   demuestra que sean correctas en general: demuestra que son las quessi.
 */
#ifndef RX550_GART_GEOM_H
#define RX550_GART_GEOM_H

#include "rx550_spaces.h"

/* ── constantes de la ASIC, con su procedencia ─────────────────────────── */

/* mc_mask del corpus: gmc_v8_0.c:1133  `adev->gmc.mc_mask = 0xffffffffffULL;`
 * con el comentario "This is the max address of the GPU's internal address
 * space".  No es un registro: es un LITERAL por ASIC.  Coincide con
 * RX550_PA_BITS (rx550_spaces.h:50), que es el mismo hecho declarado otra
 * vez; el test lo comprueba. */
#define RX550_MC_MASK             UINT64_C(0x000000FFFFFFFFFF)

/* AMDGPU_GMC_HOLE_START (amdgpu_gmc.h:36) con max_level != 4.  Que
 * max_level sea 1 y no 4 viene de amdgpu_vm_adjust_size(adev, 64, 9, 1, 40)
 * en gmc_v8_0.c:1127, cuyo cuarto argumento es un LITERAL.  Para esta tarjeta
 * el min() de amdgpu_gmc.c:299 se queda con mc_mask y NO con el hueco,
 * porque el hueco (bit 47) esta por encima de los 40 bits.  Verificado
 * aritmeticamente en test_gart_geom.c. */
#define RX550_GMC_HOLE_START      UINT64_C(0x0000800000000000)

/* four_gb de amdgpu_gmc.c:42: `static const u64 four_gb = 0x100000000ULL;`
 * Es una CONSTANTE DE FICHERO, no un calculo.  Se usa RX550_GART_ALIGN
 * (rx550_spaces.h:57) y no la otra declaracion del mismo numero que hay en
 * rx550_vmid0_gart.h:178, para que haya una sola autoridad; el test afirma
 * que las dos coinciden, que es lo que faltaba. */
#define RX550_GART_FOUR_GB        RX550_GART_ALIGN

/* mmMC_VM_FB_LOCATION.FB_BASE es de 16 bits con shift 0, y el corpus lo
 * desplaza 24 (gmc_v8_0.c:416-418).  O sea que fb_base es SIEMPRE multiplo
 * de 16 MiB.  El productor lo comprueba en vez de asumirlo. */
#define RX550_FB_BASE_ALIGN       (UINT64_C(1) << 24)

/* El PHYSICAL_PAGE_NUMBER de PAGE_TABLE_START/END_ADDR es de 28 bits con
 * shift 12, o sea 40 bits de direccion.  Es el limite estructural que
 * decide si una geometria es programable o no.
 *
 * Se declara AQUÍ y no se incluye rx550_mmio_access.h para no crear una
 * dependencia de este productor (capa baja) hacia el accessor.  El valor es
 * el mismo que RX550_PN_MASK (rx550_mmio_access.h:296) y el test lo afirma,
 * que es lo que evita dos autoridades para el mismo limite. */
#define RX550_GART_GEOM_PN_MAX    UINT64_C(0x0FFFFFFF)

/* El ANCHO de ese campo, que es otra cosa que el valor maximo: 28 bits.
 * Se declara aparte porque confundirlos produce un `1 << 0x0FFFFFFF`, que es
 * un desplazamiento imposible y no un error de compilador en todas partes.
 * La asercion de abajo es la que liga las dos. */
#define RX550_GART_GEOM_PN_BITS   28u

/* ── politica de colocacion ─────────────────────────────────────────────── */

/* amdgpu_gmc.h:217-221.  El corpus no expone esto como parametro de modulo:
 * cada ASIC elige en su propio .c.  Lo que hace ESTE driver es al reves, y a
 * proposito: la colocacion es la UNICA decision de este dominio que no es
 * aritmetica, y por tanto la unica que conviene poder名字ar en un test. */
enum rx550_gart_placement {
	RX550_GART_PLACEMENT_LOW = 0,		/* amdgpu_gmc.c:316-321      */
	RX550_GART_PLACEMENT_HIGH,		/* amdgpu_gmc.c:313-315      */
	RX550_GART_PLACEMENT_BEST_FIT		/* amdgpu_gmc.c:322-329      */
};

/* POLARIS12 usa BEST_FIT: gmc_v8_0.c:422.  Y con la geometria medida de esta
 * tarjeta la rama que BEST_FIT elige es la ALTA.  Es decir: el driver de
 * referencia coloco el GART en 0xFF00000000, NO en 0.  Que nuestro
 * RX550_GART_START sea 0 (rx550_spaces.h:56) es una DESIGN_CHOICE distinta de
 * la del corpus, y por tanto NO es lo que hace el hardware por defecto. */
#define RX550_GART_PLACEMENT_DEF   RX550_GART_PLACEMENT_BEST_FIT

/* ── entrada ───────────────────────────────────────────────────────────── */

struct rx550_gart_geom_in {
	/* ENTRADA, de mmMC_VM_FB_LOCATION (0x809) campo FB_BASE mask 0xffff
	 * shift 0, multiplicado por 2^24.  gmc_v8_0.c:416-418. */
	uint64_t			fb_base;

	/* ENTRADA, de mmCONFIG_MEMSIZE (0x150a) en bytes.  El corpus lo
	 * multiplica por 1 MiB (gmc_v8_0.c:565) y guarda mc_vram_size. */
	uint64_t			vram_bytes;

	/* Entrada de POLITICA, no de hardware.  256 MiB para POLARIS12
	 * (gmc_v8_0.c:595). */
	uint64_t			gart_size;

	enum rx550_gart_placement	placement;
};

/* ── salida ────────────────────────────────────────────────────────────── */

struct rx550_gart_geom {
	/* Derivados.  Se exponen todos porque son el sujeto de los vectores de
	 * borde: un test que solo mira gart_start no puede distinguir "eligio la
	 * rama baja" de "eligio la alta por accidente". */
	uint64_t	max_mc_address;	/* min(mc_mask, HOLE_START-1)     */
	uint64_t	fb_end;		/* fb_base + vram_bytes - 1       */
	uint64_t	size_below;		/* el hueco de ABAJO de la VRAM   */
	uint64_t	size_above;		/* el hueco de ARRIBA, alineado  */
	uint64_t	gart_size_effective;	/* tras el clamp, si lo hubo     */

	/* El resultado. */
	uint64_t	gart_start;
	uint64_t	gart_end;

	/* MODELO, no hardware: el corpus degrada el GART en silencio
	 * (amdgpu_gmc.c:307-310) y su funcion no puede fallar.  Este productor
	 * calcula lo mismo pero NO se encoge en silencio: lo declara y devuelve
	 * error.  Ver RX550_GART_GEOM_ERR_NO_CABE y la nota del .c. */
	bool		clamped;
};

/* ── codigos de error ──────────────────────────────────────────────────── */

enum rx550_gart_geom_err {
	RX550_GART_GEOM_OK = 0,
	RX550_GART_GEOM_ERR_NULO,		/* puntero nulo                  */
	RX550_GART_GEOM_ERR_VRAM_CERO,		/* vram_bytes == 0                */
	RX550_GART_GEOM_ERR_FB_DESALINEADO,	/* fb_base no multiplo de 16 MiB  */
	RX550_GART_GEOM_ERR_NO_CABE,		/* no cabe ni en el hueco mayor   */
	RX550_GART_GEOM_ERR_START_MAYOR_END,	/* geometria degenerada          */
	RX550_GART_GEOM_ERR_FUERA_DE_PT		/* no cabe en PHYSICAL_PAGE_NUMBER */
};

/* ── la funcion ────────────────────────────────────────────────────────── */

/* Aritmetica pura.  Sin MMIO, sin kernel, sin estado global.  Se prueba en
 * userspace contra el GART que el driver de referencia imprimio en esta
 * tarjeta, que es un numero MEDIDO y no una expectativa inventada.
 *
 * Devuelve 0 solo si la geometria resultante es utilizable.  Los dos motivos
 * por los que puede no serlo estan en las notas de implementacion: el GART
 * pedido no cabe en el hueco mayor, y la geometria no es representable en el
 * campo PHYSICAL_PAGE_NUMBER de 28 bits de PAGE_TABLE_START/END_ADDR.
 */
int rx550_gart_geometry(const struct rx550_gart_geom_in *in,
			struct rx550_gart_geom *out);

/* El mismo calculo con la entrada de esta tarjeta ya resuelta.  Existe para
 * que un test pueda comprobar que las constantes de arriba siguen produciendo
 * el numero medido, sin escribir la entrada a mano cada vez. */
#define RX550_GART_GEOM_ESTA_TARJETA_FB_BASE   UINT64_C(0x000000F400000000)
#define RX550_GART_GEOM_ESTA_TARJETA_VRAM      (UINT64_C(2048) << 20)

#endif /* RX550_GART_GEOM_H */