/* SPDX-License-Identifier: GPL-2.0 */
/*
 * rx550_spaces.h — espacios de direcciones, tipados y separados.
 *
 *   TARGET = RX 550 instalada en esta maquina
 *   SCOPE  = EXCLUSIVO
 *
 * POR QUE EXISTE
 *   Un uint64_t desnudo no dice de que espacio viene.  El mismo patron de bits
 *   significa cinco cosas distintas en este driver, y confundirlas produce un
 *   acceso a la memoria equivocada que devuelve un numero plausible.
 *
 *   Cada tipo de aqui es un struct envolvente, no un typedef.  Un typedef no
 *   impediria pasar uno por donde se espera otro.
 *
 * DECISION DE DISENO, NO HECHO
 *   GART_START = 0.
 *
 *   El driver de referencia puede elegirlo (amdgpu_gmc.c:312-332, tres ramas,
 *   siempre alineado a 4 GiB).  Nuestro driver elige 0.  Eso hace que
 *   GART_ADDRESS == SYSTEM_PA, que elimina una ambiguedad para el primer
 *   diseno.
 *
 *   ESTO NO ES UN REQUISITO DE HARDWARE.  No se ha demostrado que el silicio
 *   acepte la configuracion; eso se comprueba en runtime.  Lo que se ha hecho
 *   es dejar de depender el diseno propio de una configuracion historica.
 */
#ifndef RX550_SPACES_H
#define RX550_SPACES_H

/* COMPATIBILIDAD KBUILD: ver la nota equivalente en rx550_mmio_access.h.
 * u8/u32/u64 son los mismos tipos de ancho fijo; UINT64_C pasa a U64_C.
 *
 * UINT32_C se mapea igual porque rx550_vmid0_gart.h:305 lo usa y este es el
 * header del que lo hereda.  MEDIDO 2026-10-03: sin esta linea, ese .c no
 * compilaba bajo kbuild con "declaracion implicita de la funcion UINT32_C",
 * mientras en userspace pasaba sin decir nada porque <stdint.h> si lo trae.
 */
#ifdef __KERNEL__
#include <linux/types.h>
#define UINT64_C(x) U64_C(x)
#define UINT32_C(x) U32_C(x)
#else
#include <stdint.h>
#include <stdbool.h>
#include <stddef.h>
#endif

/* ── HARDWARE_REQUIREMENT ──────────────────────────────────────────────── */
#define RX550_PA_BITS		40u
#define RX550_PA_MASK		UINT64_C(0x000000FFFFFFF000)
#define RX550_PAGE_SIZE		4096u
#define RX550_PAGE_SHIFT	12u

/* ── DESIGN_CHOICE ──────────────────────────────────────────────────────── */
#define RX550_GART_START	UINT64_C(0)
#define RX550_GART_ALIGN	(UINT64_C(1) << 32)	/* 4 GiB, como el de referencia */

/* ── VRAM offset: byte dentro de la ventana de VRAM ─────────────────────── */
struct rx550_vram_offset {
	uint64_t bytes;
};

/* ── SYSTEM_PA: direccion fisica de RAM del sistema ────────────────────── */
struct rx550_system_pa {
	uint64_t bytes;
};

/* ── GART_ADDRESS: direccion en la ventana que la GPU puede usar ────────── */
/* Con GART_START == 0 coincide con SYSTEM_PA.  Se mantiene el tipo aparte por
 * si la decision se revisa: cambiar la politica no debe cambiar las firmas. */
struct rx550_gart_addr {
	uint64_t bytes;
};

/* ── GPUVA: direccion virtual del espacio de la GPU ────────────────────── */
struct rx550_gpuva {
	uint64_t bytes;
};

/* ── PDB0_INDEX: indice de entrada, no una direccion ────────────────────── */
struct rx550_pdb0_index {
	uint32_t value;
};

/* ── conversiones, cada una con precondicion explicita ──────────────────── */

static inline bool rx550_pa_representable(struct rx550_system_pa pa)
{
	/* Truncar en silencio seria peor que rechazar: produciria un mapping a
	 * la memoria equivocada y nadie lo notaria. */
	return (pa.bytes & ~RX550_PA_MASK) == 0;
}

static inline struct rx550_gart_addr rx550_gart_of_pa(struct rx550_system_pa pa)
{
	struct rx550_gart_addr g;
	g.bytes = pa.bytes + RX550_GART_START;
	return g;
}

static inline struct rx550_gpuva rx550_gpuva_make(uint64_t bytes)
{
	struct rx550_gpuva v;
	v.bytes = bytes;
	return v;
}

static inline struct rx550_vram_offset rx550_vram_off(uint64_t bytes)
{
	struct rx550_vram_offset o;
	o.bytes = bytes;
	return o;
}

/* La identidad GART<->PA SOLO es cierta con nuestra eleccion de GART_START. */
static inline bool rx550_gart_is_identity(void)
{
	return RX550_GART_START == 0;
}

static inline bool rx550_pa_aligned(struct rx550_system_pa pa)
{
	return (pa.bytes % RX550_PAGE_SIZE) == 0;
}

static inline bool rx550_vram_aligned(struct rx550_vram_offset o, uint64_t align)
{
	return align != 0 && (o.bytes % align) == 0;
}

/* Dos espacios que jamas deben compararse.  Se expone para que el test
 * documente la confusion en vez de dejarla implícita. */
static inline bool rx550_vram_off_eq_ga(struct rx550_vram_offset o,
					struct rx550_gart_addr g)
{
	return o.bytes == g.bytes;
}

#endif /* RX550_SPACES_H */
