# 1224 — Los 9 divergentes que no son offsets, uno a uno: **2 son falsos positivos míos, 3 son correctos por generación, y queda 1 vivo**

```text
AGENCIA=RX550-INVESTIGACION · WORK_CLASS=CLOSE-OUT · HEADER-CENSUS
AUTOR=AGENTE-INSTR
WRITE_EXECUTION=NONE · GPU=NONE TOUCHED · RUNTIME=NOT_RUN
DISPOSITIVO_TOCADO=NINGUNO · ni 0000:01:00.0 (1002:699f) ni 0000:00:02.0 (8086:0412)
ESCRITOS_POR_ESTA_ITERACION   ninguno (solo lectura)
CIERRA   1223 §"los 8 simbolos divergentes que no son offsets, en tres
         grupos sin mapear".  Los mapeo uno a uno,  y el recuento era 9 no 8
GENERADO=2026-10-06 · MEDIDO=EN ESTA HOST
```

## 0 · El censo bien hecho, y lo que salió

```text
  simbolos con el MISMO nombre en mas de un header      321
  de los cuales, con VALOR DISTINTO                     28
    offsets *_REGISTER_OFFSET                           19   -> 1223
    OTROS                                                9   -> este hallazgo
```

Y de esos 9: **2 son un error mío de comparación**, 3 son constantes que *deben* diferir, 3
divergen con cero emisiones, y 1 diverge y se usa.

## 1 · Dos que NO divergen: relleno de ceros

```text
  PACKET3_SET_CONTEXT_REG_START   sid.h 0x000a000   vid.h 0x0000a000
  PACKET3_SET_CONTEXT_REG_END     sid.h 0x000a400   vid.h 0x0000a400
```

`0x000a000` y `0x0000a000` son el mismo número, `0xa000`. **El mismo número con distinto relleno
de ceros.** Mi comparador era de texto, así que los contó como distintos.

**Eso baja la cifra real de 9 a 7, y son dos errores de detector míos.** Es la sexta vez en esta
tanda que un número sale verosímil y equivocado, y la segunda vez hoy por comparar texto donde
tocaba comparar valor.

## 2 · Tres que DEBEN diferir: son constantes por generación

```text
  MMSCH_VERSION         mmsch_v1_0.h  0x1
                        mmsch_v2_0..v5_0.h  (MAJOR << 16 | MINOR)
  MMSCH_VERSION_MAJOR   v2_0 2   v3_0 3   v4_0 4   v5_0 5
  SDMA_OP_DUMMY_TRAP    navi10 32  sdma_v6_0_0 32  sdma_v7_1_0 32  vega10 16
```

`MMSCH_VERSION_MAJOR` es 2, 3, 4, 5 según la generación: **su valor ES la generación**, y la
comparación entre headers no tiene sentido. Lo mismo con `SDMA_OP_DUMMY_TRAP`, que vale 32 en
Navi10 y 16 en Vega10.

**No son divergencias. Son el comportamiento correcto de un header por ASIC.** Contarlos como
divergencia fue un error de modelo por mi parte, no del censo.

## 3 · Tres que divergen y no las emite nadie

El trío `LOAD_*_REG`, opcode que asigna cada header:

```text
  header              LOAD_SH_REG  LOAD_CONFIG_REG  LOAD_CONTEXT_REG
    vid.h                   0x5F             0x60                0x61
    cikd.h                  0x5F             0x60                0x61
    soc15d.h                0x5F             0x60                0x61
    nvd.h                   0x5F             0x60                0x61
    gfx_v12_1_pkt.h         0x5F             0x60                0x61
    sid.h                   0x61             0x5F                0x60     <- PERMUTADO
```

Cinco headers van en el orden `SH, CONFIG, CONTEXT`. **`sid.h` va al revés**: le da `0x5F` a
CONFIG y `0x61` a SH. No es un desplazamiento parcial, es el trío entero permutado.

Y la razón por la que no importa hoy:

```text
  PACKET3_LOAD_SH_REG         emisiones en .c:  0    apariciones en .h:  6
  PACKET3_LOAD_CONFIG_REG     emisiones en .c:  0    apariciones en .h:  6
  PACKET3_LOAD_CONTEXT_REG    emisiones en .c:  0    apariciones en .h:  6
```

**Ningún `.c` del driver los emite.** Están declarados en seis headers y no se usan. Así que la
divergencia es **latente**: no produce ningún fallo observable, y solo mordería a quien escriba un
decodificador o emita esos paquetes a mano usando `sid.h` en vez de `vid.h`.

Que `sid.h` sea el equivocado o los otros cinco, no se puede decidir por uso, porque no hay uso.
Queda como `NOT_DETERMINED`, con la posición de los dos lados escrita.

## 4 · Uno que diverge y se usa: `INDIRECT_BUFFER_CONST`

```text
  vid.h 0x33      cikd.h 0x33      soc15d.h 0x33      sid.h 0x31
  emisiones en .c:  4
```

`sid.h` es el único con `0x31`; los otros tres con `0x33`. Y **se emite cuatro veces**, así que
aquí la divergencia es viva, no latente. Para GFX8 el valor es `0x33`, porque `gfx_v8_0.c` incluye
`vid.h` (línea 35) y no `sid.h`.

## 5 · El recuento final, y la corrección a `1223`

```text
  1223 §"LO QUE SIGUE"  decia   los 8 simbolos divergentes que no son offsets,
                                en tres grupos sin mapear

  CORRECTO
     eran 9,  no 8
     2 de los 9 son falsos positivos mios  (relleno de ceros)
     3 de los 9 son constantes por generacion  (correctas, no son divergencia)
     4 son divergencias reales:   3 LATENTES  (LOAD_*_REG,  0 emisiones)
                                   1 VIVA      (INDIRECT_BUFFER_CONST,  4 emisiones)

  y el reparto de las 28 divergencias del conjunto completo:
     19  offsets de registro,  dos linajes de ASIC        -> 1223
      4  anomalias de opcode,  las 4 en sid.h             -> aqui
      5  constantes por generacion,  no son anomalias
```

**Las cuatro anomalías de opcode están todas en `sid.h`.** Ni una en `vid.h`.

## 6 · Procedimiento

```text
PREGUNTA   ¿ cuales son los simbolos divergentes que no son offsets?
FUENTES    censo de los headers de amdgpu/  (contar nombres,  comparar valor)
           los tres LOAD_*_REG en los seis headers de paquete
           conteo de emisiones en los .c del driver
MEDIDO     321 simbolos compartidos   28 divergentes   19 offsets   9 otros
     2 falsos positivos (0x000a000 == 0x0000a000)
     3 por generacion (MMSCH_VERSION,  MMSCH_VERSION_MAJOR,  SDMA_OP_DUMMY_TRAP)
     3 latentes  (LOAD_SH_REG, LOAD_CONFIG_REG, LOAD_CONTEXT_REG:  0 emisiones)
     1 viva      (INDIRECT_BUFFER_CONST:  4 emisiones,  sid.h 0x31 contra 0x33)
AUTOCORR.  la primera version del detector comparaba  (texto, numero de linea)  como
           valor,  de modo que los 321 parecian divergir.  Volvio a salir un
           recuento verosimil y equivocado:  la sexta vez en esta tanda  y la
           segunda hoy por comparar texto donde iba valor.
DISPOSITIVO  NINGUNO.  i915 y amdgpu intactos.
RUNTIME      NOT_RUN
LO QUE SIGUE
  - cual de los dos lados del trio LOAD_*_REG es el bueno:  no se puede por uso
    porque no hay uso.  Habria que comparar con la especificacion de AMD,  que
    033 ya declaro que no publica.
  - la ventana de codigos libres entre 0x33 y 0x3F en vid.h,  para saber si
    0x31 estalla o esta libre en esta generacion
```