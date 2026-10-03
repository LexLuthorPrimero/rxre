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
/* `bool` es palabra clave desde C23, y `typedef int bool` pasa a ser un error.
 * MEDIDO 2026-10-03 con gcc 16.2 de este equipo: `-std=c23` es el estandar por
 * defecto, asi que este typedef ya no compila.  Antes de C23 el lenguaje no
 * traia el tipo, y por eso hacia falta aportarlo.
 *
 * La condicion es la version del estandar, no un #ifdef del compilador: asi el
 * mismo fuente sirve para las dos ramas sin depender de como se llame gcc. */
#  if !defined(__STDC_VERSION__) || __STDC_VERSION__ < 202311L
typedef int			bool;
#  endif
#ifndef true
#define true	1
#define false	0
#endif
#endif

#endif /* TARGET_MEM_HOST_H */
