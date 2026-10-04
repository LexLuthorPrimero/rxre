/* SPDX-License-Identifier: GPL-2.0 */
/*
 * rx550_vm_geom.c — la aritmetica.  Puro: sin kernel, sin lectura, sin MMIO.
 *
 * Transcripcion de amdgpu_vm_adjust_size() (amdgpu_vm.c:2391-2478) y de
 * amdgpu_vm_get_block_size() (amdgpu_vm.c:2368-2379), con la linea del corpus de
 * la que sale cada expresion.  El objetivo es que la duda "¿este numero es de la
 * tarjeta o es mio?" tenga una respuesta que no dependa de leer un comentario.
 */
#include "rx550_vm_geom.h"

/* Las primitivas del kernel, reimplementadas.  En u32/u64 son exactamente
 * estas, y reimplementarlas evita depender de cabeceras que no existen de las dos
 * formas.  El orden es el de uso:  roundup llama a fls. */

/* arch/x86/include/asm/bitops.h:396-412:  1-INDEXADO,  y 0 si x == 0.  O sea
 * fls64(v) == bit_length(v) para v != 0. */
static uint32_t rx550_fls64(uint64_t v)
{
	uint32_t n = 0;

	if (v == 0)
		return 0;
	while (v > 1) {
		v >>= 1;
		n++;
	}
	return n + 1;
}

/* include/linux/log2.h:156-164:  ilog2(v) == fls64(v) - 1 */
static uint32_t rx550_ilog2(uint64_t v)
{
	return rx550_fls64(v) - 1;
}

/* include/linux/log2.h:55-58, LEIDO en el kernel que corre:
 *
 *     unsigned long __roundup_pow_of_two(unsigned long n)
 *     { return 1UL << fls_long(n - 1); }
 *
 * Y la rama de constante, log2.h:177-178:
 *     ((n) == 1) ? 1 : (1UL << (ilog2((n) - 1) + 1))
 *
 * MEDIDO que mi primera version restaba uno de mas:
 * `1 << (fls64(v-1) - 1)`, que da roundup(64) = 32 en vez de 64.  El `-1` que
 * sobra es el que hace que fls sea 1-indexado;  restarlo dos veces es el error
 * clasico con esta primitiva.  Las dos formas del kernel concuerdan,  y las dos
 * dan 64 para 64.
 *
 * El `v <= 1` protege el n de 0, que la cabecera declara indefinido
 * (log2.h:171).  El kernel usa el 0 solo en el `(n)==1` de la rama de
 * constante,  y en runtime cae en __roundup_pow_of_two,  donde n-1 = 0 y
 * fls_long(0) = 0 dan 1. */
static uint64_t rx550_roundup_pow2(uint64_t v)
{
	if (v <= 1)
		return 1;
	return UINT64_C(1) << rx550_fls64(v - 1);
}

/* DIV_ROUND_UP de include/linux/math.h:  -(-a/b) en enteros.  Con a positivo es
 * (a + b - 1) / b,  que es lo que dice la macro del kernel. */
static uint32_t rx550_div_round_up(uint32_t a, uint32_t b)
{
	return (a + b - 1) / b;
}

/* amdgpu_vm.c:2368-2379.  El parametro se llama `vm_size` en el corpus pero
 * recibe `tmp`,  que a esta altura vale un numero pequeno;  eso es lo que hace
 * que devuelva 10 y no 22. */
static uint32_t rx550_vm_get_block_size(uint64_t v)
{
	uint32_t bits = rx550_ilog2(v) + RX550_VM_PFN_SHIFT;

	/* :2375  if (vm_size <= 8) */
	if (v <= 8)
		return bits - RX550_VM_BLOQUE_OFFSET;
	/* :2378  return ((bits + 3) / 2); */
	return (bits + 3) / 2;
}

int rx550_vm_geometry(const struct rx550_vm_geom_in *in,
		      struct rx550_vm_geom *out)
{
	uint32_t max_size, vm_size, tmp, num_level;

	if (in == NULL || out == NULL)
		return RX550_VM_GEOM_ERR_NULO;

	/* amdgpu_vm.c:2395  max_size = 1 << (max_bits - 30)  */
	max_size = 1u << (RX550_VM_MAX_BITS - 30);

	/* :2400-2431.  Tres caminos, y el orden importa:  el override gana,  y si
	 * no, la RAM manda con un factor de 3 y un suelo. */
	if (in->vm_size_gb != RX550_VM_GEOM_SIN_OVERRIDE) {
		if (in->vm_size_gb <= 0) {
			/* :2402-2406  avisa y recorta al maximo.  Aqui no hay
			 * donde avisar,  asi que el recorte se hace igual y el
			 * valor recortado es el que sale.  Es la decision
			 * silenciosa de un modulo sin via de aviso. */
			vm_size = max_size;
		} else {
			vm_size = (uint32_t)in->vm_size_gb;
			if (vm_size > max_size)
				vm_size = max_size;
		}
	} else {
		/* :2429-2430  roundup_pow_of_two(clamp(ram*3, min, max)) */
		if (in->ram_gb == 0)
			return RX550_VM_GEOM_ERR_RAM_CERO;
		{
			uint32_t tripled = in->ram_gb * 3u;
			uint32_t clamped = tripled;

			if (clamped < RX550_VM_MIN_SIZE_GB)
				clamped = RX550_VM_MIN_SIZE_GB;
			if (clamped > max_size)
				clamped = max_size;
			vm_size = rx550_roundup_pow2(clamped);
		}
	}

	/* :2433  max_pfn = (uint64_t)vm_size << 18.  OJO:  son PAGINAS de 2 KiB
	 * y por eso el 18,  no el 12 de la pagina. */
	out->vm_size_gb = vm_size;
	out->max_pfn    = (uint64_t)vm_size << RX550_VM_PFN_SHIFT;

	/* :2436-2440.  AQUI ESTA EL REASSIGN que hace que block_size valga 10:
	 *
	 *   tmp = roundup_pow_of_two(max_pfn)      -> 2^24 con vm_size = 64
	 *   tmp = DIV_ROUND_UP(fls64(tmp) - 1, 9) - 1   -> 2
	 *
	 * El segundo `tmp` REEMPLAZA al primero.  Y el valor con el que se
	 * llama a get_block_size es este,  no el max_pfn. */
	tmp = rx550_roundup_pow2(out->max_pfn);
	if (in->block_size != RX550_VM_GEOM_SIN_OVERRIDE) {
		/* :2437-2438  el override desplaza ANTES del round */
		if (in->block_size < 9) {
			tmp = 0;
		} else {
			tmp >>= (uint32_t)(in->block_size - 9);
			tmp = rx550_roundup_pow2(tmp);
		}
	}
	tmp = rx550_div_round_up(rx550_fls64(tmp) - 1u, RX550_VM_BLOQUE_OFFSET) - 1u;

	/* :2440  num_level = min(max_level, tmp) */
	num_level = (tmp < RX550_VM_MAX_LEVEL) ? tmp : RX550_VM_MAX_LEVEL;
	/* :2441-2456  el switch solo elige root_level,  y su `default` (:2454-2455)
	 * hace dev_err y CONTINUA.  Se reproduce esa continuacion —los numeros
	 * tienen que ser los del corpus— y se marca con `degenerado`, que es lo
	 * que el corpus no dice.  Con max_level = 1 el unico caso posible es 1,
	 * y solo se llega a 0 con un override de block_size muy grande. */
	out->degenerado = (num_level == 0);
	if (num_level > 4)
		return RX550_VM_GEOM_ERR_NIVELES;
	out->num_level = num_level;

	/* :2457-2466.  Tres ramas, y con max_level = 1 la segunda es
	 * inalcanzable:  num_level > 1 no puede darse. */
	if (in->block_size != RX550_VM_GEOM_SIN_OVERRIDE) {
		/* :2459-2462  min(override, bits - PAGE_SHIFT - 9*levels) */
		uint32_t techo = RX550_VM_MAX_BITS - RX550_PAGE_SHIFT -
				 RX550_VM_BLOQUE_OFFSET * num_level;

		out->block_size = ((uint32_t)in->block_size < techo)
			? (uint32_t)in->block_size : techo;
	} else if (num_level > 1) {
		out->block_size = RX550_VM_BLOQUE_OFFSET;	/* :2464 */
	} else {
		out->block_size = rx550_vm_get_block_size(tmp);	/* :2466 */
	}

	/* :2468-2471  el override gana;  si no, el literal de la llamada. */
	if (in->fragment_size != RX550_VM_GEOM_SIN_OVERRIDE) {
		if (in->fragment_size <= 0)
			return RX550_VM_GEOM_ERR_OVERRIDE;
		out->fragment_size = (uint32_t)in->fragment_size;
	} else {
		out->fragment_size = RX550_VM_FRAGMENT_DEFAULT;
	}

	/* El campo del plan.  Se calcula aqui,  no en el llamante,  para que la
	 * conversion exista en un solo sitio. */
	return RX550_VM_GEOM_OK;
}