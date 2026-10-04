/* SPDX-License-Identifier: GPL-2.0 */
/*
 * rx550_vm_geom.h — block_size, fragment_size, num_level y max_pfn, PRODUCIDOS.
 *
 * Que es
 *   La aritmetica de amdgpu_vm_adjust_size() (amdgpu_vm.c:2391-2478), que es lo
 *   que decide los tres campos del plan del GART cuyos valores NO son literales
 *   del corpus:
 *
 *     mmVM_CONTEXT1_CNTL.PAGE_TABLE_BLOCK_SIZE  = block_size - 9
 *     mmVM_L2_CNTL3.BANK_SELECT                 = fragment_size
 *     mmVM_L2_CNTL3.L2_CACHE_BIGK_FRAGMENT_SIZE = fragment_size
 *
 *   MEDIDO 2026-10-04: antes de este modulo, NINGUN codigo del componente
 *   rellenaba block_size ni fragment_size desde una lectura.  Estaban
 *   declarados como parametros con un comentario ("10 en esta tarjeta", "9 en
 *   esta tarjeta") y nada los fijaba.  Ese era el unico sitio del componente
 *   donde se podia estar inventando un valor, y no estaba en la tabla de
 *   campos: estaba en el BORDE entre la tabla y el constructor del plan.
 *
 * Que NO es
 *   No lee /proc/meminfo ni sysfs.  No consulta parametros de modulo.  La RAM y
 *   los overrides entran por parametro,  y quien los lee es el llamante.  Es la
 *   misma frontera que rx550_gart_geom.h:  la aritmetica es pura y aqui;  la
 *   lectura del mundo es alla.
 *
 * LO QUE ESTA ESCRITO Y LO QUE ESTA DERIVADO.  Y por que este modulo existe:
 *
 *   - `fragment_size` = 9 sale del LITERAL de la llamada,
 *     amdgpu_gmc: gmc_v8_0.c:1127 `amdgpu_vm_adjust_size(adev, 64, 9, 1, 40)`.
 *     El tercer argumento es 9, y el override por modulo esta en -1.  Es un
 *     hecho del corpus, no una medida.
 *
 *   - `block_size` NO es un literal, y aqui es donde un lector desconfiado
 *     tiene razon en desconfiar:  sale de `si_meminfo()`, o sea de la RAM de la
 *     maquina.  MEDIDO que en esta maquina NO depende de ella,  y no por
 *     casualidad sino con una demostracion de dominio:
 *
 *         la RAM entra por `clamp(phys_ram_gb * 3, 64, 1024)`
 *         ese clamp  produce  vm_size  que produce  tmp = 2
 *         y amdgpu_vm_get_block_size(2) = (ilog2(2)+18) - 9 = 19 - 9 = 10
 *
 *     El barrido de TODO el dominio legal de vm_size, de 64 a 1024 GB, da
 *     block_size = 10 sin excepcion.  O sea que el valor es una funcion pura de
 *     los argumentos de la llamada, y la `si_meminfo()` es un tramo del camino
 *     que no cambia el resultado.  tests/test_vm_geom.c comprueba el barrido,  no
 *     solo el punto.
 *
 *     Si alguien quisiera cambiarlo, el sitio es ESTE fichero y no una
 *     constante en otro:  unico punto de decision,  con el unico oraculo.
 *
 * CUIDADO CON EL `tmp`, que es donde esta elSummary error tipico
 *   amdgpu_vm.c:2436-2440 hace:
 *       tmp = roundup_pow_of_two(max_pfn);
 *       if (amdgpu_vm_block_size != -1) tmp >>= amdgpu_vm_block_size - 9;
 *       tmp = DIV_ROUND_UP(fls64(tmp) - 1, 9) - 1;      <-- REASIGNA tmp
 *   y el `amdgpu_vm_get_block_size(tmp)` de :2466 recibe el VALOR YA REASIGNADO,
 *   que es un numero pequeno (2 en esta ruta),  no el numero de paginas.  Pasar
 *   el max_pfn por ahi da 22,  no 10:  un numero plausible y equivocado,  que es
 *   exactamente la clase de fallo que este componente lleva tres commits
 *   corrigiendo en otros sitios.
 */
#ifndef RX550_VM_GEOM_H
#define RX550_VM_GEOM_H

#include "rx550_spaces.h"

/* El llamador ya ha resuelto los tres overrides de modulo.  Se pasan como
 * banderas explicitas, con -1 = "no hay override", que es el valor por defecto
 * MEDIDO en esta maquina:
 *     /sys/module/amdgpu/parameters/vm_block_size    = -1
 *     /sys/module/amdgpu/parameters/vm_fragment_size = -1
 *     /sys/module/amdgpu/parameters/vm_size          = -1
 * y ninguno aparece en /proc/cmdline.  Se declaran aqui para que el llamante
 * pueda leerlos si algún dia alguien los fija,  y el default este escrito. */
#define RX550_VM_GEOM_SIN_OVERRIDE	(-1)

/* Los argumentos de la llamada de POLARIS12, con su procedencia:
 *   gmc_v8_0.c:1127   amdgpu_vm_adjust_size(adev, 64, 9, 1, 40);
 *                      min=64  fragment=9  level=1  bits=40
 * Los cuatro son LITERALES del corpus y por eso son constantes aqui.  No son
 * parametros:  el corpus no ofrece knob para ninguno de los cuatro. */
#define RX550_VM_MIN_SIZE_GB	64u
#define RX550_VM_FRAGMENT_DEFAULT	9u
#define RX550_VM_MAX_LEVEL	1u
#define RX550_VM_MAX_BITS	40u

/* El margen contra el que salta una pagina:  es el segundo factor de
 * max_pfn << este, y el 18 es de amdgpu_gmc.h.  No es 12:  max_pfn cuenta PAGINAS
 * de 2 KiB,  no bytes.  Este es el error mas caro de esta aritmetica, porque un
 * 18 por 12 da 64 GB de espacio en vez de 128 TiB,  y el numero sigue siendo
 * plausible. */
#define RX550_VM_PFN_SHIFT	18u

/* El 9 delPAGE_TABLE_BLOCK_SIZE = block_size - 9, y el 9 de
 * amdgpu_vm_get_block_size(),  son COSAS DISTINTAS que valen lo mismo.  El
 * primero es el offset del campo,  el segundo el ancho minimo de una tabla de
 * paginas.  Se declara una vez con su nombre y se usa con ese nombre,  para que
 * un cambio en uno no se lleve por delante el otro en silencio. */
#define RX550_VM_BLOQUE_OFFSET	9u

/* Si se fija amdgpu.vm_size,  manda ese.  Si no,  la RAM manda. */
struct rx550_vm_geom_in {
	/* RAM de la maquina en GiB,  REDONDEADA como la hace el corpus:
	 *   phys_ram_gb = (totalram * mem_unit + (1<<30)-1) >> 30
	 * MEDIDO en esta maquina: 12098908 kB  ->  12 GiB.
	 * Ignorado si `vm_size_gb` no es SIN_OVERRIDE. */
	uint32_t	ram_gb;

	/* Overrides de modulo,  o SIN_OVERRIDE.  Los tres son -1 medidos. */
	int32_t		vm_size_gb;
	int32_t		block_size;
	int32_t		fragment_size;
};

struct rx550_vm_geom {
	/* Lo que sale, y lo que el plan del GART necesita. */
	uint32_t	vm_size_gb;		/* tras clamp y roundup    */
	uint64_t	max_pfn;		/* vm_size_gb << 18        */
	uint32_t	num_level;		/* niveles de tabla, 1..4 */
	uint32_t	block_size;		/* 10 en esta ruta         */
	uint32_t	fragment_size;		/* 9                       */

	/* MEDIDO: la llamada del corpus puede dejar num_level en 0,  y el corpus
	 * NO se detiene:  amdgpu_vm.c:2454-2455 cae en el `default` del switch y
	 * hace `dev_err("VMPT only supports 2~4+1 levels")`,  y LUEGO calcula
	 * block_size con un num_level de 0,  o sea con el tope semantico
	 * 40 - 12 - 0 = 28 en vez de 19.  O sea:  avisa y entra en un estado que
	 * el propio mensaje dice que no vale.
	 *
	 * Aqui los numeros son los del corpus —para que no difieran de lo que
	 * veria el hardware— y esta bandera dice que el estado es degenerado, que
	 * es lo que el corpus no dice.  rejecting en vez de avisar seria una
	 * divergencia MAS grande:  el driver de referencia acepta la
	 * configuracion y nosotros la rechazariamos. */
	bool		degenerado;		/* num_level quedo en 0    */
};

enum rx550_vm_geom_err {
	RX550_VM_GEOM_OK = 0,
	RX550_VM_GEOM_ERR_NULO,
	RX550_VM_GEOM_ERR_RAM_CERO,	/* sin override y ram_gb = 0 */
	RX550_VM_GEOM_ERR_OVERRIDE,	/* un override fuera de rango */
	RX550_VM_GEOM_ERR_NIVELES	/* num_level > 4: inasequible */
};

/* La aritmetica.  Pura:  sin lectura, sin kernel, sin estado global. */
int rx550_vm_geometry(const struct rx550_vm_geom_in *in,
		      struct rx550_vm_geom *out);

/* El campo tal como lo escribe el plan,  para que la conversion
 * block_size -> PAGE_TABLE_BLOCK_SIZE no se escriba a mano en otro sitio. */
static inline uint32_t rx550_vm_geom_block_field(uint32_t block_size)
{
	return block_size - RX550_VM_BLOQUE_OFFSET;
}

#endif /* RX550_VM_GEOM_H */