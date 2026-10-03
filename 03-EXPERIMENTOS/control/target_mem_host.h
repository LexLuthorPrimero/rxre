/* SPDX-License-Identifier: GPL-2.0 */
/*
 * target_mem_host.h — el unico punto donde target_mem.h necesita el kernel.
 *
 * target_mem.h incluye <linux/types.h> porque va a formar parte de un modulo.
 * Los tests compilan fuera del arbol, y solo necesitan los tipos. Este header
 * los aporta sin arrastrar el kernel entero, y por lo tanto la unica diferencia
 * entre el target_mem.h del modulo y el de los tests es este include.
 *
 * Si algun dia el contrato necesita algo mas del kernel, este es el fichero que
 * hay que ampliar, y el sitio donde queda escrito por que.
 */
#ifndef TARGET_MEM_HOST_H
#define TARGET_MEM_HOST_H

typedef unsigned char		u8;
typedef unsigned short		u16;
typedef unsigned int		u32;
typedef unsigned long long	u64;

#ifndef __KERNEL__
typedef int			bool;
#ifndef true
#define true	1
#define false	0
#endif
#endif

#endif /* TARGET_MEM_HOST_H */
