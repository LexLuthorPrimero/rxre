# 1536 — los campos de geometría son offsets, no exponentes, y las filas salen de una rama que esta placa toca de lleno

```text
AGENCIA=RX550-INVESTIGACION · PARTE=1/MC-MEMORIA+ROM · FASE=2 (geometria)
CLASSIFICATION=SEMANTICA-DE-REGISTRO+ALCANCE-DEGENERACIONAL+ERROR-CORRECTION-PROPIA
TRACK=STATIC · CERO HARDWARE · Intel no tocada
GENERADO=2026-10-05
CIERRA=el "nº de filas" que el 1528 dejo NOT_DETERMINED, y corrige la semantica de los campos
ESTADO=PROBADO · NOOFBANK/NOOFCOLS/NOOFROWS son offsets, NO exponentes: +2, +8, +10
       · hay DOS decodes distintos del mismo campo NOOFROWS en el arbol, y no coinciden
       · con NOOFROWS=4 la segunda dice 16384 filas, y 4 cae EXACTAMENTE en el umbral
       · 16384 filas x 4 KB = 64 MB, y la placa es de 2048 MB: falta un factor de 32
       · el codigo que lo dice es de DMP legado de SI, y NO corre en Polaris12
       · y me equivocaré otra vez si digo que NOOFROWS no lo lee nadie
```

## 1. Me iba a equivocar otra vez, y el `grep` lo impidió

Iba a escribir que `NOOFROWS` no lo lee nadie en el driver, basing-me en un `grep` sobre
`amdgpu/*.c`. Es falso. Está en `pm/legacy-dpm/si_dpm.c`, dos veces, y **la segunda trae la
semántica completa**:

```c
  si_dpm.c:3737   row    = ((tmp & MC_ARB_RAMCFG__NOOFROWS_MASK) >> ...SHIFT) + 10;
  si_dpm.c:3738   column = ((tmp & MC_ARB_RAMCFG__NOOFCOLS_MASK) >> ...SHIFT) + 8;
  si_dpm.c:3739   bank   = ((tmp & MC_ARB_RAMCFG__NOOFBANK_MASK) >> ...SHIFT) + 2;
  si_dpm.c:3741   density = (1 << (row + column - 20 + bank)) * width;

  si_dpm.c:4795   if (tmp >= 4)  dram_rows = 16384;
  si_dpm.c:4798   else            dram_rows = 1 << (tmp + 10);
```

**Los tres campos son offsets, no exponentes.** `+2`, `+8`, `+10`. Eso confirma por tercera vez, y
con la fuente mas fuerte, que mi tentativa del principio —"todos son exponentes del mismo encoding"—
era falsa. El `1528` ya lo habia refutado por la falta de shift en el driver; esto lo refuta con la
formula del productor.

Con los valores de esta placa:

```text
  row    = 4 + 10 = 14
  column = 2 + 8  = 10
  bank   = 2 + 2  = 4
  density = (1 << (14 + 10 - 20 + 4)) * width = 256 * width
        width=16 ->  4096 bits =  512 B
        width=32 ->  8192 bits = 1024 B
        width=64 -> 16384 bits = 2048 B
```

## 2. El numero de filas, y por que el 4 es demasiado bonito

La segunda lectura da una rama distinta para el mismo campo:

```text
  NOOFROWS >= 4  ->  dram_rows = 16384        (constante, no exponente)
  NOOFROWS <  4  ->  dram_rows = 1 << (NOOFROWS + 10)   = 1024, 2048, 4096, 8192
```

**Nuestro `NOOFROWS` es exactamente 4**, o sea **justo en el umbral** donde se deja el exponente y
entra la constante. Si fuera 3, darian 8192 filas; si fuera 5, tambien 16384. Que caiga en el borde
es casualidad de una placa, pero significa que la lectura es inequivoca: **o este valor da 16384
filas, o la codificacion no es la que creo.**

## 3. Y aqui se cae: 16384 filas por 4 KB dan 64 MB, no 2048

```text
  16384 filas x 4 KB por fila = 67.108.864 bytes = 64 MB
  la placa declara                                    2048 MB
  factor que falta                                            32
```

Un factor de **exactamente 32**, limpio. Caben los sospechosos de siempre —4 bancos por 8
dispositivos, o 2 canales por 16 bancos, o una combinacion— y **ninguno esta confirmado**.

Lo que si queda, y es la parte que importa:

- la **fila de 4 KB** es de `gfx_v8_0.c:1819`, que **si es gfx8 y si corre en esta placa**
- las **16384 filas** son de `pm/legacy-dpm/si_dpm.c`, que es **DMP legado de Southern Islands**
- los **bancos y columnas** son del mismo fichero legado

## 4. El alcance, que es lo que no quiero perder de vista

`pm/legacy-dpm/` es el camino de DMP viejo, para SI y CIK. **Polaris12 no lo usa**: gfx8 va por
SMIU/SMU7, que es un controlador completamente distinto. Estas formulas:

- **no se ejecutan en esta tarjeta**
- no son evidencia del comportamiento de esta tarjeta
- **si** son evidencia de como se codificaba `MC_ARB_RAMCFG` en una generacion anterior, y el
  registro y sus campos son los mismos

O sea: **esto es `DERIVED` de una fuente generacionalmente distinta, y no `PROVEN` para Polaris12.**
Lo digo asi porque seria facilísimo presentarlo como el cierre del item 2 y seria falso.

Y hay una tension interna que no resuelvo: **las dos lecturas de `NOOFROWS` en el mismo fichero dan
resultados incompatibles** para el mismo valor de entrada. Con `NOOFROWS = 4`, la linea 3737 da
`row = 14` y la 4793 da `16384`. No son la misma magnitud: una parece filas por canal y la otra
filas totales, o una es antes de unajuste y la otra despues. **No lo reconcilio porque no tengo la
semantica de la diferencia, y specular aqui seria inventar.**

## 5. Dónde queda el item 2

```text
  fila                    4 KB          PROBADO   (gfx_v8_0.c:1819, corre en gfx8)
  encoding de los campos  +2 / +8 / +10 PROBADO   (si_dpm.c, generacion anterior)
  nº de filas             16384         DERIVED   (si_dpm.c:4793, NO corre en Polaris12)
  bancos                  4             DERIVED   (si_dpm.c:3739, misma salvedad)
  columnas                10            DERIVED   (si_dpm.c:3738, misma salvedad)
  16384 x 4 KB = 64 MB contra 2048 MB declarados    CONTRADICCION ABIERTA, falta un factor 32
  densidad por dispositivo  1 KB con width=32        DERIVED, y no cuadra con un chip real
  nº de filas, version gfx8                          NOT_DETERMINED
```

**El item 2 no se cierra, y no por falta de datos del ROM: sino porque las dos unicas fuentes que
explican los offsets de estos campos son de una generacion que no corre en esta placa.** Eso es un
descubrimiento sobre el proyecto, no un fallo de la lectura: **para el formato de la geometria de
gfx8 no hay fuente en el corpus.**

## 6. Decision log (§103)

```text
DECISION    usar las formulas de si_dpm como DERIVED con alcance generacional, y no como PROVEN
WHY         §86: separacion entre evidencia historica y observacion actual.  El codigo no corre
            en Polaris12, y publicarlo como medida de la tarjeta seria exactamente el error que
            el 1494/1496/1498 ya corrigieron tres veces.
ALTERNATIVA  publicar "la geometria es 16384 filas x 4 KB" y cerrar el item 2.  Descartada: no
            cuadra con los 2048 MB (factor 32), y ademas el codigo no corre aqui.
ALTERNATIVA  descartar si_dpm por ser de otra generacion.  Descartada: es la unica fuente que
            declara el encoding, y descartarla tira informacion que si vale.
DISCriminante  un registro de esta placa con NOOFROWS observado.  Amdgpu_gc_info no lo expone; el
            registro MC_ARB_RAMCFG si, y es hardware, y ahora esta prohibido.
            ASTA es la dependencia, y es la unica que queda en el item 2 que no es de ROM.
CONSECUENCIA  el item 2 queda con su parte de ROM AGOTADA.  Lo que falta es o hardware, o una
            fuente de gfx8 que el proyecto no tiene.
REVERSIBLE  si el alcance generacional fuera invalido, este hallazgo cae entero.  Por eso lo
            marco DERIVED y no PROVEN, y por eso escribo el alcance en el titulo del ESTADO.
```

## 7. La parte de ROM del item 2 se ha agotado, y eso es un resultado

Tres hallazgos seguidos (1532, 1535, este) han salido todos del mismo fichero de 58 880 bytes, y cada
uno ha quitado un `NOT_DETERMINED` y puesto dos nuevos con nombre. **Ese es el momento de parar con
el ROM en este item**, no porque se haya acabado —quedan tablas— sino porque **las que quedan ya no
tocan la geometria**.

Lo que queda del item 2, reduzido a lo que de verdad falta:

```text
  1. el encoding de los campos en gfx8        no hay fuente en el corpus.  DEPENDENCIA EXTERNA
  2. el valor de MC_ARB_RAMCFG en el siliconio   requiere leer un registro.  HARDWARE
  3. el factor 32 entre 64 MB y 2048 MB       requiere saber cuantos dispositivos hay.  NO_DETERMINED
  4. amdgpu_gc_info, el unico artefacto que traeria la fila ya decodificada   requiere debugfs
```

Cuatro huecos, **ninguno resoluble sin salir del ROM**, y tres de los cuatro por una dependencia
externa nombrada. Eso es un item en `DEFERRED` con la lista escrita, que es mas util que un item
abierto e indefinido.
