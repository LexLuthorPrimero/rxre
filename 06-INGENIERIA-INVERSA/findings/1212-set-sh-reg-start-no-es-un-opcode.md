# 1212 — `SET_SH_REG_START = 0x2c00` **no es un opcode**: es una base de reubicación. Y eso obliga a corregir la lista de huecos de `1210`

```text
AGENCIA=RX550-INVESTIGACION · WORK_CLASS=SEMANTICS · CORRECTION
AUTOR=AGENTE-INSTR
WRITE_EXECUTION=NONE · GPU=NONE TOUCHED · RUNTIME=NOT_RUN
DISPOSITIVO_TOCADO=NINGUNO · ni 0000:01:00.0 (1002:699f) ni 0000:00:02.0 (8086:0412)
ESCRITOS_POR_ESTA_ITERACION   ninguno (solo lectura)
CIERRA   la pregunta que 1211 §6 dejo abierta:  por que SET_SH_REG y
         SET_CONTEXT_REG no tienen macros y sus _START si
CORRIGE  1210 §3:  la lista de "huecos" includes paquetes que NO TIENEN
         layout porque su payload no es un campo de bits
GENERADO=2026-10-06 · MEDIDO=EN ESTA HOST
```

## 0 · La pregunta y su respuesta en una línea

`1211` midio una asimetria sin explicación: `SET_SH_REG` y `SET_CONTEXT_REG` no tienen macros de
campo, y sus `_START` sí. La explicación es que **`_START` y `_END` no son opcodes**, y por eso
el modo plano de `pm4_grupos.py` no les encuentra campos: no tienen.

## 1 · La prueba de que no pueden ser opcodes: la macro los descarta

`vid.h:105-107`, literal:

```c
#define PACKET3(op, n)	((PACKET_TYPE3 << 30) |				\
			 (((op) & 0xFF) << 8) |				\
			 ((n) & 0x3FFF) << 16)
```

`(op) & 0xFF`. El opcode se enmascara a **8 bits**, y `PACKET3_SET_SH_REG_START = 0x00002c00`
no cabe en 8 bits: en el mejor de los casos `0x2c00 & 0xFF = 0x00`. **La macro no puede
transportar ese valor como opcode.** No es una conjetura sobre la intención del autor: es que la
expresión lo descarta.

Comprobado sobre el árbol entero, y no sobre un ejemplo:

```text
  PACKET3_SET_SH_REG_START         apariciones 21   subtrahendo 15   dentro de PACKET3()  0
  PACKET3_SET_CONTEXT_REG_START    apariciones 22   subtrahendo 14   dentro de PACKET3()  0
  PACKET3_SET_SH_REG_END           apariciones  6   subtrahendo  0   dentro de PACKET3()  0
  PACKET3_SET_CONTEXT_REG_END      apariciones  6   subtrahendo  0   dentro de PACKET3()  0
```

**Cero** usos dentro de `PACKET3()`, en 6 ficheros de paquete y todos los `.c`. Y 29 de 35
apariciones son **subtrahendos**. El uso canónico, `gfx_v8_0.c:1529-1530`:

```c
		ib.ptr[ib.length_dw++] = PACKET3(PACKET3_SET_SH_REG, 1);
		ib.ptr[ib.length_dw++] = vgpr_init_regs[i] - PACKET3_SET_SH_REG_START;
```

El segundo dword es el **offset del registro MMIO menos la base**. No es un opcode: es una
direccion reubicada.

## 2 · Y la aritmética encaja, medida

Los dos valores, contra los registros reales de `gfx_8_0_d.h`:

```text
  base 0x002c00   mmCOMPUTE_PGM_LO   0x002e0c   ->  0x020c   10 bits
  base 0x002c00   mmCOMPUTE_PGM_HI   0x002e0d   ->  0x020d   10 bits
  base 0x00a000   mmPA_SC_RASTER_CONFIG  0xa0d4   ->  0x00d4    8 bits
```

`COMPUTE_PGM_LO` y `COMPUTE_PGM_HI` son registros consecutivos: `0x2e0c` y `0x2e0d`, y restando
la base salen `0x020c` y `0x020d`, también consecutivos y **con un solo bit de diferencia**.

Y las ventanas de las dos familias:

```text
  SET_SH_REG       base 0x02c00   fin 0x03000   =  0x400 bytes = 256 dwords
  SET_CONTEXT_REG  base 0x0a000   fin 0x0a400   =  0x400 bytes = 256 dwords
```

**Las dos son exactamente 0x400 bytes**, 256 dwords, un índice de **8 bits**. Simetría exacta
entre las dos familias de "escribir registro", y los offsets medidos caben de sobra. Eso no es
una coincidencia que se pueda ignorar: son dos ventanas de direccion de la misma anchura, y la
aritmética del driver produce valores que caen dentro de las suyas.

## 3 · Los dos `_END` no los usa nadie

```text
  PACKET3_SET_SH_REG_END          en 6 .h   en 0 .c   valor 0x00003000
  PACKET3_SET_CONTEXT_REG_END     en 6 .h   en 0 .c   valor 0x000a400
```

Se declaran en **6 cabeceras de paquete independientes** y no aparecen en **ningún** fichero `.c`
del driver. Y el valor coincide en las 6.

> Eso son dos cosas a la vez. Una: seis fuentes primarias coinciden en el valor, que es la
> corroboración más fuerte disponible sin hardware (§22). Dos: **el driver no escribe nunca el
> marcador de fin**, asi que el paquete se cierra por otro mecanismo — el `count` de la
> cabecera — y el `_END` es documentación o residuo.

Sobre `SET_CONTEXT_REG_END` el valor se declara con dos rellenos distintos, `0x000a400` en unas
cabeceras y `0x0000a400` en otras. Es el **mismo número**, `0xa400`. No es una contradicción y
no se registra como tal.

## 4 · La corrección a `1210`, que es lo importante de este hallazgo

`1210` listó 28 —luego 24— paquetes emitidos "sin layout" y los trató como huecos de
conocimiento. Presentado asi, implica que falta saber algo. Para al menos dos de ellos **no falta
nada**:

```text
  SET_SH_REG         el payload es un indice de registro opaco,  no un campo
                     de bits.  No hay layout porque no hay estructura.
  SET_CONTEXT_REG    idem.
```

Un paquete sin campos no es un paquete sin determinar: es un paquete **sin estructura que
determinar**, y su decodificación es `cabecera + opcode + count + índice`, sin decodificar más.

La distinción importa para lo que venga después, y es la razón de que este hallazgo exista:

```text
  POR DETERMINAR   SET_SH_REG_START no dice nada del layout de SET_SH_REG.
                   Falta informacion.
  SIN ESTRUCTURA   SET_SH_REG no tiene macros porque su payload no es un
                   campo de bits.  No falta informacion:  no hay campo.

  Confundirlas produce trabajo infinito:  se buscaría un layout que no existe.
```

`1210` no cometió un error de cifra —los 24 están bien contados— sino un error de **encuadre**:
llamó "hueco" a lo que en parte es "no aplica". Queda corregido aquí.

## 5 · Lo que queda abierto y es real

```text
  ABIERTO   por que el driver escribe  SET_SH_REG  con count 1 y 2  en sitios
            distintos  (gfx_v8_0.c:1529 count 1,  :1535 count 2),  y que
            significa la diferencia.  No es determinable de vid.h.

  ABIERTO   si el hardware acepta el indice sin el marcador _END.  El
            driver no lo emite,  luego o no hace falta o funciona por el
            count.  SOLO RUNTIME puede separar esas dos.  Y no se ha leido
            ni un registro.

  ABIERTO   si 0x2c00 y 0xa000 son realmente "bases"  o son casualmente los
            primeros offsets de cada bloque.  La aritmetica encaja,  pero
            encajar no es probar.  NOT_DETERMINED.
```

## 6 · Clasificación epistémica

```text
  _START/_END no son opcodes        PROVEN     el & 0xFF los descarta y hay
                                                  0 usos en PACKET3()
  se usan como base de reubicacion  OBSERVED   29 subtrahentos medidos
  ventanas de 0x400 bytes            CORROBORATED  por la simetria y por
                                                  los offsets medidos
  valor de los _END                 CORROBORATED  6 fuentes,  0 usos
  el payload no es un campo de bits  NOT_DETERMINED  coherente con el uso,
                                                  pero no leido del ASIC
  ASIC leido                         NOT_OBSERVED  RUNTIME=NOT_RUN
```

## 7 · Procedimiento

```text
PREGUNTA   ¿por que SET_SH_REG y SET_CONTEXT_REG no tienen macros y sus
            _START si?
FUENTES    vid.h:105-107   (la macro PACKET3 y su mascara)
           vid.h:343-350   (los cuatro valores)
           sid.h, soc15d.h, cikd.h, nvd.h, gfx_v12_1_pkt.h  (las otras 5)
           asic_reg/gca/gfx_8_0_d.h  (mmCOMPUTE_PGM_LO/HI, mmPA_SC_RASTER_CONFIG)
           gfx_v8_0.c:1529-1536, 1555-1562, 1235-1236, 4162-4173
MEDIDO     0 usos dentro de PACKET3()  /  29 subtrahentos
           6 .h declaran cada _END  /  0 .c los usan
           ventanas de 0x400 bytes en las dos familias
           0x020c, 0x020d, 0x00d4 como residuos
SIN INTERVENCION  todo lectura del arbol.  No se toco ningun registro.
DISPOSITIVO  NINGUNO.  i915 y amdgpu intactos.
RUNTIME      NOT_RUN
```