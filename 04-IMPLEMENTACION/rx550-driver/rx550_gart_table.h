/* SPDX-License-Identifier: GPL-2.0 */
/*
 * rx550_gart_table.h — la tabla de paginas de la GART: cuanto ocupa y con que se
 * rellena.
 *
 *   TARGET = RX 550 instalada en esta maquina
 *   SCOPE  = EXCLUSIVO
 *
 * QUE ES, Y POR QUE ESTA SEPARADO DE LA SECUENCIA
 *
 *   El plan del GART (rx550_gart_seq.c) programa
 *   mmVM_CONTEXT0_PAGE_TABLE_BASE_ADDR = tabla >> 12.  Es decir:  el plan dice
 *   DONDE esta la tabla y no la crea.  Y no la crea a proposito, porque el plan
 *   se construye y se compara con el corpus sin tocar nada.
 *
 *   Aqui esta lo otro:  CUANTO ocupa esa tabla y con que valor arranca cada
 *   entrada.  Las dos cosas salen de una aritmetica de tres pasos del corpus,
 *   y las tres son medibles sin GPU.
 *
 * LA ARITMETICA, con su cita
 *
 *   amdgpu_gart.c:533   gart.num_gpu_pages = gmc.gart_size / 4096
 *   gmc_v8_0.c:960       gart.table_size    = gart.num_gpu_pages * 8
 *   gmc_v8_0.c:961       gart.gart_pte_flags = AMDGPU_PTE_EXECUTABLE
 *   amdgpu_gart.c:270    la tabla se pide a VRAM con alineacion de 4096
 *   amdgpu_gart.c:276    memset_io(ptr, gart_pte_flags, table_size)
 *
 * PARA ESTA TARJETA
 *
 *   gmc.gart_size = 256 MiB,  del log del kernel  ("GART: 256M 0x000000FF00000000")
 *
 *       num_gpu_pages = 256 MiB / 4096 =  65536
 *       table_size    = 65536 * 8       = 524288  =  512 KiB
 *       valor inicial = AMDGPU_PTE_EXECUTABLE = 1ULL << 4 = 0x10
 *
 *   Y las 512 KiB van EN VRAM, no en memoria del sistema:  el sistema solo es
 *   para los ASIC sin VRAM dedicada  (amdgpu_gart.c:110-118, "for ASICs that
 *   don't have dedicated VRAM").  Esta tarjeta tiene 2 GiB,  asi que le toca
 *   la de VRAM  (amdgpu_gart.c:263-278).
 *
 *   Y ESTA VEZ SI, y es la diferencia con la funcion anterior:  las 512 KiB de
 *   esta tabla se SABEN.  Todo lo demas del GART depende de un reset o de un
 *   firmware.  Esto no:  sale de una division y una multiplicacion sobre un
 *   numero que esta en el log de esta maquina.
 */
#ifndef RX550_GART_TABLE_H
#define RX550_GART_TABLE_H

#include "rx550_spaces.h"

#ifdef __KERNEL__
#include <linux/types.h>
/*  limits.h y no types.h:  U32_MAX esta en linux/limits.h.  Es la misma
 *  trampa que en rx550_mmio_access.h,  y alli la corrected justamente porque
 *  este componente compila las mismas dos cosas en los dos contextos. */
#include <linux/limits.h>
#define UINT32_MAX U32_MAX
#define SIZE_MAX  ULONG_MAX
#else
#include <stdint.h>
#include <stdbool.h>
#include <stddef.h>
#endif

/*  Cada entrada de la tabla de la GART son 8 bytes,  y no 4.  Es el *8 de
 *  gmc_v8_0.c:960,  y es la unica razon por la que la tabla de esta tarjeta
 *  ocupa 512 KiB y no 256.
 *
 *  La entrada de la GART NO es una PTE de 40 bits con los flags dentro:  es una
 *  palabra de 64.  Ver rx550_vmid1_pgt.h,  que explica por que los flags de PTE
 *  (bits 5 y 6) no pueden mezclarse con una direccion. */
#define RX550_GART_TABLA_ENTRADA_BYTES	8u

/*  El valor con el que ARRANCA cada entrada.
 *
 *  No es un valor por defecto:  es lo que escribe el corpus,  medido en
 *  amdgpu_gart.c:276 con memset_io.  Y no es 0:  una GART cuyas 65536 entradas
 *  valen 0 es una GART donde todas las paginas estan invalidas,  que es un
 *  estado valido despues de un reset pero no el estado desde el que el driver
 *  arranca. */
#define RX550_GART_PTE_EXECUTABLE	UINT64_C(0x10)

/* La geometria de la tabla, ya resuelta. */
struct rx550_gart_tabla_geom {
	uint64_t	paginas;	/* num_gpu_pages, 65536 en esta tarjeta */
	uint64_t	bytes;		/* paginas * 8,  524288 aqui           */
	uint32_t	entradas_max;	/* paginas, para acotar el relleno    */
};

#define RX550_GART_TABLA_ERR_INCONSISTENT	(-1)
#define RX550_GART_TABLA_ERR_TAMANO		(-2)	/* gart_size incoherente */
#define RX550_GART_TABLA_ERR_DESBORDA		(-3)	/* no cabe en size_t     */

/*  Resuelve la geometria desde el tamano de la GART.  RECHAZA, entre otros:
 *
 *   - un gart_size que no sea multiplo de 4096.  El corpus trunca  (la division
 *     entera de amdgpu_gart.c:533)  y un tamano raro se trunca en silencio;  y un
 *     multiplo de 4096 con resto 0 aqui es una condicion que se puede exigir.
 *   - un gart_size de 0:  una tabla de 0 entradas no cubre nada,  y una GART de
 *     0 bytes no existe.
 *   - un gart_size por encima de RX550_GART_SIZE_MAX,  que es la politica del
 *     propio driver  (rx550_vmid0_gart.h:72).
 */
int rx550_gart_tabla_geom(uint64_t gart_size, struct rx550_gart_tabla_geom *out);

/*  Rellena las `entradas` primeras con `valor`.  Devuelve cuantas ha escrito,  o
 *  error.  No devuelve el numero de bytes:  el que llama sabe el tamaño de su
 *  buffer  y el error que importa es el de no caber.
 *
 *  Y el puntero se avanza, que es lo que hace un bucle de relleno y lo que
 *  espera quien lo llama.  Por eso la funcion NO acepta un numero de bytes y
 *  un valor:  acepta un numero de ENTRADAS y un valor, y convierte una vez. */
int rx550_gart_tabla_rellena(uint64_t *tabla, uint64_t entradas, uint64_t valor);

/*  Lo mismo, con el valor por PALABRA de 64 bits.  Existe para que el 0x10 no
 *  se escriba a mano en el llamante.
 *
 *  MEDIDO 2026-10-04.  ESTO NO ES EL VALOR DEL CORPUS, y la frase anterior si
 *  lo decia.  La cadena real es:
 *
 *    - AMDGPU_PTE_EXECUTABLE = (1ULL << 4) = 0x10   (amdgpu_vm.h:65)
 *    - ese valor se asigna a gart_pte_flags         (gmc_v8_0.c:961)
 *    - y se pasa a memset_io(ptr, gart_pte_flags, table_size)
 *                                                  (amdgpu_gart.c:276)
 *    - memset_io toma un INT DE BYTE, no una palabra:
 *      `void memset_io(volatile void __iomem *, int, size_t)`
 *      (arch/x86/include/asm/io.h:205), y su implementacion en
 *      arch/x86/lib/iomem.c:114-125 acaba en memset((void *)a, b, c).
 *
 *  Luego el corpus NO escribe 0x10 por entrada:  escribe 0x10 en CADA BYTE, y
 *  cada entrada de 64 bits queda 0x1010101010101010.  Eso tiene tres
 *  consecuencias, y las tres estan medidas:
 *
 *    1. NUESTRO VALOR PASARIA NUESTRO VALIDADOR Y EL SUYO NO.
 *       rx550_pte_check() (rx550_gart_write.c:24) rechaza lo que hay fuera de
 *       RX550_PTE_GFX8_ALLOWED, y 0x1010101010101010 viola los bits 44, 52 y
 *       60.  Si adoptamos el valor byte-replicado, el relleno de este modulo
 *       no podria alimentarse de rx550_gart_write(), que valida cada entrada
 *       antes del primer store.
 *
 *    2. LA DIFERENCIA ES INOBSERVABLE PARA ESTA TARJETA.  Bit a bit:
 *         bit 0  VALID   0 en ambos
 *         bit 4  EXEC    1 en ambos
 *         bits 12,20,28,36 (PA)   0 aqui, basura ahi
 *         bits 44,52,60 (reservado alto)  0 aqui, basura ahi
 *       Con VALID = 0 la entrada es invalida y su campo de direccion no se
 *       consulta: el acceso falla y PROTECTION_FAULT_DEFAULT manda a la pagina
 *       de relleno.  El unico caso en que la diferencia seria observable es
 *       que el bit 0 del valor estuviera a 1, y no lo esta.
 *
 *    3. ES UN DEFECTO LATENTE DE amdgpu, no una decision.  gart_pte_flags es
 *       una mascara de bits en todas partes (amdgpu_gmc.c:1135 hace
 *       `flags |= VALID|READABLE|...` sobre ella), y pasarla como argumento de
 *       byte es un desajuste de tipo.  En esta ASIC no se ve por el motivo 2.
 *
 *  ASI QUE ESTE MODULO ESCRIBE 0x10 POR PALABRA, y la afirmacion correcta es:
 *  "un valor cuyos bits funcionales son los del corpus", no "el valor del
 *  corpus".  La diferencia esta registrada, no resuelta, porque resolverla
 *  exigiria saber que hace el silicio con una entrada invalida. */
int rx550_gart_tabla_reinicia(uint64_t *tabla, uint64_t entradas);

#endif /* RX550_GART_TABLE_H */