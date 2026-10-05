# 1139 — Los tres bucles que `1138 §8` dejó como "no hechos": son de una sentencia **sin llaves** y escriben **posicionalmente**. Con ellos, la IB de inicialización de shader de GFX8 queda completa: 294 dwords, y se ve el ISA del compute shader

```text
AGENCIA=RX550-INVESTIGACION · WORK_CLASS=IMPLEMENTATION · VALIDATION
AUTOR=AGENTE-INSTR
WRITE_EXECUTION=NONE · MODIFICATIONS=0 · RUNTIME=NOT_RUN
ESCRITOS_POR_ESTA_ITERACION   tools/ibref.py   (i++, cuerpo sin llaves,
                              escritura posicional, guarda de lectura de registro;
                              57 -> 65 vectores)
                              tools/verif.py   (baseline re-fijada, 46 medidas)
                              08-ARQUITECTURA/artifacts/R13-BRACELOS/{ib.txt,
                              ib.json, mmio.txt}
MODIFICADO_NADA_EXISTENTE    pm4_codec.py, pm4_emit.py, gfx_v8_0.c INTACTOS
CLASSIFICATION=IMPLEMENTATION · VALIDATION
GENERADO=2026-10-04 · MEDIDO=EN ESTA HOST
ESTADO=0 BUCLES SIN RECONOCER EN LA FUNCION · IB COMPLETA
```

## 0 · El resultado, primero

```text
                          1138        AHORA
dwords escritos              186          294
completos                    177          285
bucles desenrollados          3            6
bucles NO reconocidos         3            0
escrituras posicionales       0          108

lo que aparece:  el ISA del compute shader, dword a dword
   0x7E000209  0xBE920108  0xBE940100  0xBE960102  0xBE980104  ...
```

Y el dato que prueba que la guarda de seguridad funciona:

```text
bucle L1628   25 iteraciones   0 escritura(s) al IB capturadas
                                  1 lectura(s) de registro excluidas
```

25 iteraciones desenrolladas, **0 dwords añadidos a la IB**, y el motivo escrito.
`RREG32(...)` es una lectura de registro, no una escritura de anillo, y meterla
habría producido 25 dwords inventados.

## 1 · POR QUÉ NO LOS RECONOCÍA: TRES FORMAS DISTINTAS

`1138 §8` los dejó escritos como *"la extensión más obvious y la no he hecho a
propósito"*. Eran tres razones distintas, no una:

```c
/* gfx_v8_0.c:1517  — i++, SIN llaves, escritura POSICIONAL */
for (i = 0; i < ARRAY_SIZE(vgpr_init_compute_shader); i++)
        ib.ptr[i + (vgpr_offset / 4)] = vgpr_init_compute_shader[i];

/* gfx_v8_0.c:1628  — i++, SIN llaves, y NO es escritura de IB */
for (i = 0; i < ARRAY_SIZE(sec_ded_counter_registers); i++)
        RREG32(sec_ded_counter_registers[i]);
```

| lo que cambia | antes | ahora |
|---|---|---|
| grafía del paso | solo `i += 2` | `i += N` **o** `i++` |
| cuerpo | exigía `{ ... }` | con llaves **o** una sentencia |
| destino | `X.ptr[X.length_dw++]` | además `X.ptr[<cualquier>] = v` |

## 2 · `i++` NO ES OTRA OPERACIÓN

Esto se extiende sin aflojar el contrato, y la distinción importa:

```text
i += 2      paso = entero 2
i++         paso = entero 1        (misma operacion, otra grafia)

lo que el contrato exige es "el paso es un entero CONOCIDO", no una grafía.
Aceptar `i++` no baja el listón: sube el número de formas que se entienden
manteniendo la misma exigencia.
```

Consecuencia: el contrato de rechazo de `1138 §2` sigue íntegro. `i != 4` sigue
sin reconocerse, y con el motivo escrito.

## 3 · EL CUERPO SIN LLAVES, Y POR QUÉ NO ES UN CASO MENOR

`RE_FOR` acababa en `\{`. Los tres bucles de carga de shader **no llevan
llaves**: son de una sentencia. Consecuencia medida: **66 + 42 + 25 = 133
dwords** fuera, y 0 perdidas silenciosas.

Lo que no es menor es lo que cuesta **no** hacerlo, y sale del propio `1138`:

> Si se acepta desenrollar bucles con llaves y se ignoran los que no las
> tienen, entonces el instrumento sabe distinguir "esto es un bucle" de "esto es
> una sentencia suelta" **y no lo dice**. Es exactamente el fallo de `1138 §3`
> por el otro lado: `RE_FOR` no casa, `RE_FOR_CUALQUIER` sí, y el bucle se
> declara no reconocido. Correcto.

La lección es que **el contrato de rechazo y el alcance del reconocimiento son
la misma cosa**. Cada forma que se acepta reduce el alcance de un error
silencioso; cada forma que se rechaza en voz alta es el precio.

## 4 · LA ESCRITURA POSICIONAL, Y EL BUG DE "DESTINO CON VARIABLE PUESTA"

Una escritura secuencial no lleva posición: `ib.ptr[ib.length_dw++] = x` dice
"el siguiente". Una posicional sí: `ib.ptr[i + off] = v` dice **dónde**.

```c
ib.ptr[i + (vgpr_offset / 4)] = vgpr_init_compute_shader[i];
```

La primera versión capturó la fila y dejó el destino **sin ligar**:

```text
L1518   ptr[0 + (vgpr_offset / 4)] = 0x7E000209
```

El `0` sí quedo ligado (el `i`), pero `vgpr_offset / 4` no. Y eso es **peor que
no dar destino**, porque un texto con un simbolo sin ligar parece un destino
legítimo. El vector que lo fija:

```text
desenrollo: el indice de una escritura POSICIONAL queda ligado
       f4[1][4] == "1 + 4"
```

La causa: `_sustituir_elementos` sustituía `tabla[expr]` pero no las variables
sueltas. Ahora sustituye la **expresión entera** al final, y el orden es
deliberado — primero los elementos, porque `t[k]` necesita `k` ligada, y luego
las variables, para que `k + 4` también quede.

Lo que **no** queda ligado es `vgpr_offset`, y es correcto: se calcula en
tiempo de ejecución con `ALIGN(total_size, 256)` y `total_size` acumula tres
contribuciones. Declararlo sin ligar es la respuesta honesta.

## 5 · LA GUARDA: UNA LECTURA DE REGISTRO NO ES UN DWORD

`sec_ded_counter_registers` se recorre con `RREG32(...)`, que **lee** un registro
de hardware. No escribe en el IB.

Si el desenrollado lo hubiera tratado como escritura, la IB habría crecido en 25
dwords inventados: valores de registro leidos por el driver, presentados como
contenido del anillo. Una IB de 319 en vez de 294, con 25 dwords que el hardware
interpretaría como comandos.

Lo que hace:

```text
bucle desenrollado (25 iteraciones): 0 escritura(s) al IB capturadas,
                                     1 lectura(s) de registro excluidas
```

Y el vector:

```text
desenrollo: un bucle de solo RREG32 produce CERO dwords de IB
desenrollo: y lo dice, en vez de producir una IB vacia sin motivo
```

El segundo es el que importa: **una IB a la que le faltan 25 elementos tiene que
decir por qué**, o el que la lee asume que la IB entera está ahí.

## 6 · LA IB COMPLETA, Y LO QUE SE VE AHORA

```text
dwords escritos: 294   completos: 285   incompletos: 9
con posicion: 108
bucles NO reconocidos: []

   L1518   ptr[0 + (vgpr_offset / 4)] = 0x7E000209
   L1521   ptr[4 + (sgpr_offset / 4)] = 0xBE920108
   L1521   ptr[5 + (sgpr_offset / 4)] = 0xBE940100
   L1521   ptr[6 + (sgpr_offset / 4)] = 0xBE960102
   L1521   ptr[7 + (sgpr_offset / 4)] = 0xBE980104
   L1521   ptr[8 + (sgpr_offset / 4)] = 0xBE9A0106
```

Esos valores son la carga del **compute shader** que el driver programa en el
anillo. Antes no estaban: el instrumento no miraba dentro de esos bucles.

`vgpr_init_compute_shader` tiene 66 dwords, `sgpr_init_compute_shader` 42, y las
escrituras son `ptr[0..65]` y `ptr[4..45]` — **con un hueco de 4 entre
ambos**, que es `sgpr_offset - vgpr_offset` y que en ejecución sale de
`ALIGN(total_size, 256)`. El hueco es visible porque las escrituras llevan su
posición, no porque se suponga que son contiguas.

## 7 · MEDIDO, NO DECLARADO

```text
bucles               6   (3 de += 2, 3 de ++)
iteraciones         17, 17, 17, 66, 42, 25
desenrollados      ['i:17','i:17','i:17','i:25','i:42','i:66']
NO reconocidos     []
duplicados         []

puerta  46 medidas, SIN DERIVA
        ibref.desenrollados y ibref.bucles_no_desenrollados perturbadas
        una por una: rc=1   restaurada: rc=0
```

El cambio de baseline es exactamente lo esperado y solo eso:

```text
APARECEN   i:25, i:42, i:66
DESAPARECEN   L1517, L1520, L1628
```

Las tres que desaparecen son exactamente las tres que `1138 §3` reportaba como
no reconocidas, y las tres que aparecen son las tres que ahora se desenrollan.
**No hay una cuarta.**

## 8 · MIS ERRORES

```text
1. `_sentencia` no se inserto (buscaba `def _a_enter`, que ya no existia tras
   la reescritura de 1138)  ->  NameError en tiempo de ejecucion

2. el selftest PASABA con la ruta sin llaves sin ejercitarla
   57 vectores, rc=0, y el codigo de las llaves sin llaves no existia
   Solo se vio porque al ejecutarlo contra la funcion REAL salio
   "NO desenrollados: [1517, 1520, 1628]" con la lista vacia de bucles

3. filas de 3 o 4 elementos segun el camino, y `ib_de_funcion` leia `f[4]`
   ->  IndexError. Normalizadas a 5

4. vector que esperaba `cc` para `t[k]` con k=2: el array son PARES
   (a,1,b,2,cc,3), asi que t[2] es `b`. Contaba por pares un array que
   se indexa por elemento
```

El **#2** es el que más me importa, y es una clase que ya había pagado: **una
prueba que pasa sin ejercitar el código**. Los 57 vectores daban verde con una
ruta entera sin cobertura. Lo vi porque ejecuté la herramienta de verdad y el
resultado no cuadraba con lo que los vectores decían.

Un selftest que no falla no es una prueba de que el código funciona: es una
prueba de que los vectores que existen funcionan. La diferencia aparece cuando
alguien lee el número y cree que todo está cubierto.

## 9 · LO QUE SIGUE SIN ESTAR HECHO

**`vgpr_offset` y `sgpr_offset` quedan sin ligar.** Se calculan con `ALIGN` sobre
`total_size`, que suma tres contribuciones y luego alinea. Resolverlo requiere
sintetizar la aritmética de tamaño, que es otra capacidad, y da como resultado
el **hueco de 4 dwords** entre las dos cargas. El hueco es visible; su
explicación no.

**Los 9 `INCOMPLETO` restantes** son `gpu_addr` (4, en `lower_32_bits` /
`upper_32_bits`) y `COMPUTE_DISPATCH_INITIATOR`. Ligables con `--set`.

**`RREG32` no se sintetiza en absoluto.** Se cuenta y se excluye, que es lo
seguro, pero su lectura sería observable en una traza de MMIO y no lo es.

**No he desenrollado bucles anidados.** No hay ninguno en esta función, y no
puedo afirmar que no haya en `gfx_v8_0.c` sin medirlo. Es un
`NOT_DETERMINED` declarado, no un `PROVEN_ABSENT`.

**Y nada de esto es evidencia de hardware.** `RUNTIME=NOT_RUN`. Los 0x7E, 0xBE
que salen son lo que el driver **escribe**; que el hardware los interprete como
instrucciones de shader es lo que no he verificado.