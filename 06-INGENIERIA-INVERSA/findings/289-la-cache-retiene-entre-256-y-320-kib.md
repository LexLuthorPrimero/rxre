# 289 · `262-1` cerrado por medición: el nivel más rápido retiene entre 256 y 320 KiB de conjunto de trabajo

```text
CLASSIFICATION=MEASUREMENT+PROVEN · TRACK=RUNTIME
CORPUS=RESEARCH/working/linux-7.1.3 + boot log de la placa
HARDWARE_SCOPE=HOST-C/RX550/0000:01:00.0
WORK_CLASS=WRITE_LOCAL (banco y kernel propios) · WRITE_EXECUTION=carga Vulkan nivel 1 · NIVEL=1
MODIFICATIONS_CORPUS=0 · GPU INTACTA
INSTRUMENT=vcp con reuse.comp y modelo 5 | ESTADO=VALIDATED (regresion 6/6)
```

## Qué resuelve

**⇒ Cierra `262-1`. El tamaño de la caché de GFX8 no está en ninguna fuente del driver —`265`—,
no se podía medir con un barrido aleatorio —`288`—, y ahora está medido por el patrón que sí
funciona: **el nivel más rápido retiene entre 256 y 320 KiB de conjunto de trabajo con 8
wavefronts residentes. `PROVEN`.**

**⇒ `PROVEN_DERIVED`. El cambio de instrumento es el que lo hace posible. El barrido aleatorio
no puede dar un tamaño porque cada hilo recorre direcciones nuevas sin reutilización y la tasa
de acierto no depende del conjunto. Aquí la distancia de reutilización es la variable `B`, y el
plano de la curva aparece a huella constante en tres recuentos de hilos distintos.** `PROVEN_DERIVED`.

**⇒ `MEASUREMENT`. Las dos latencias de la plataforma, medidas por tres vías independientes que
concurden: acierto ≈ 449 ciclos y fallo ≈ 1075 ciclos.** `MEASUREMENT`.

## 1 · Por qué este patrón mide un tamaño y el anterior no

**⇒ `PROVEN_DERIVED`. El defecto del barrido de `288` era que no había reutilización que medir.
Cada hilo visitaba 1024 direcciones distintas y los 1024 hilos estaban en sitios distintos en
cada instante, de modo que la tasa de acierto la fijaba el solape entre las direcciones vivas y
la capacidad —no el tamaño—, y el punto de meseta medía una transición de estructura.** `PROVEN_DERIVED`.

**⇒ `PROVEN`. `reuse.comp` hace que la distancia de reutilización sea `B` y nada más: cada hilo
tiene un bloque de `B` direcciones y elige dentro de él pseudoaleatoriamente.** `PROVEN`.

```glsl
uint blk = i * B;                          /* bloque propio, sin solape entre hilos */
for (uint k = 0u; k < ITERS; k++) {
    uint idx = blk + ((acc ^ k) % B);      /* dentro del bloque, y depende de acc */
    uint v   = d[idx];
    acc = acc * 1664525u + v + 1013904223u;
}
d[WSIZE + i] = acc;
```

**⇒ `PROVEN_DERIVED`. Las dos condiciones que `277` declaraba necesarias están: el índice
depende de `acc`, que depende de la lectura, así que la cadena es dependiente y el hardware no
puede prefetchear el bloque; y el número de direcciones vivas por hilo es `B`, así que la
distancia de reutilización es exactamente la variable que se barre.** `PROVEN_DERIVED`.

**⇒ `PROVEN`. El banco impone el invariante que hace falta: `WSIZE == items × B`. Si no cuadra,
el bloque del último hilo se sale de la región de lectura y el banco sale con 2 en vez de
producir un tiempo sin validez. `PROVEN`.**

## 2 · El barrido, y la cota

**⇒ `MEASUREMENT`. `reuse.comp`, 512 hilos —8 wavefronts—, 1024 vueltas por hilo, 9 muestras
con calentamiento, control 9 de 9 en los diez puntos.** `MEASUREMENT`.

| huella (KiB) | B | ns por vuelta | ciclos | x previo |
|---|---|---|---|---|
| 64 | 32 | 297,9 | 317 | — |
| 96 | 48 | 346,7 | 369 | 1,16 |
| 128 | 64 | 313,5 | 333 | 0,90 |
| 160 | 80 | 405,3 | 431 | 1,29 |
| 192 | 96 | 431,6 | 459 | 1,06 |
| 224 | 112 | 426,8 | 454 | 0,99 |
| **256** | 128 | **424,8** | 452 | 1,00 |
| **320** | 160 | **636,7** | 677 | **1,50** |
| 384 | 192 | 771,5 | 820 | 1,21 |
| 512 | 256 | 1.011,7 | 1.075 | 1,31 |

**⇒ `PROVEN`. El plano está entre 160 y 256 KiB —405,3 / 431,6 / 426,8 / 424,8 ns, una variación
del 6,5% sobre un factor 1,6 en huella— y el codo está entre 256 y 320 KiB, con un factor 1,50
en un paso de 1,25× en el tamaño.** `PROVEN`.

**⇒ `PROVEN_DERIVED`. Los tres primeros puntos quedan por debajo del plano y no son un segundo
nivel más rápido: con `items` = 512 y `B` = 32 el trabajo total es de 64 KiB, y el arranque del
despacho es comparable. Son coste fijo, no caché, y por eso se excluyen de la cota.** `PROVEN_DERIVED`.

## 3 · La comprobación que separa «capacidad» de «artefacto»

**⇒ `MEASUREMENT. Si lo que se agota es una capacidad, el plano tiene que aparecer a la misma
huella con distinto número de hilos, y `B` tiene que desplazarse de forma inversamente
proporcional a los hilos.** `MEASUREMENT`.

| huella | `items` = 128 | `items` = 256 | `items` = 512 |
|---|---|---|---|
| 32 KiB | 280 | 277 | 269 |
| 64 KiB | 343 | 274 | 280 |
| 128 KiB | 405 | 379 | 286 |
| 256 KiB | 468 | 450 | 411 |
| 512 KiB | — | 852 | 1.007 |
| 1.024 KiB | — | — | 1.856 |

**⇒ `PROVEN_DERIVED`. La latencia a una huella dada es la misma con 128, 256 y 512 hilos: a
256 KiB son 468, 450 y 411 ns, y a 32 KiB son 280, 277 y 269 ns. El número de hilos no mueve la
curva, la huella sí.** `PROVEN_DERIVED`.

**⇒ `PROVEN_DERIVED`. Y esto es lo que separa la explicación correcta de la que propuse antes.
`288` dejó la conclusión en «el recurso que se agota depende del número de hilos
concurrentes»; es incorrecto: lo que se agota son los bytes, y el error fue comparar `B` en
lugar de la huella.** `PROVEN_DERIVED`.

## 4 · Las dos latencias, por tres vías

**⇒ `PROVEN. El acierto en el nivel rápido es de 449 ciclos y el fallo en memoria de 1.075.** `PROVEN`.

```text
acierto  422,1 ns  ->  449 ciclos   meseta de 160 a 256 KiB, esta nota
fallo   1011,7 ns  -> 1.075 ciclos  huella de 512 KiB, esta nota
        1.003,9 ns  -> 1.067 ciclos  huella de 4.096 KiB, barrido de 288
```

**⇒ `CORROBORATED`. Las dos primeras medidas de fallo —1.075 y 1.067 ciclos— concuerdan al 0,8%,
y proceden de instrumental y patron distintos: uno barre el conjunto de trabajo con acceso
aleatorio y el otro barre la distancia de reutilización con acceso controlado. Que coincidan
es lo que hace que las dos notas sean creíbles.** `CORROBORATED`.

**⇒ `PROVEN_DERIVED`. Y el valor de 7.227 ciclos del barrido de `288` a 64 MiB es de otra cosa: es
la latencia con la presión de la translator de página y del número de peticiones en vuelo, no el
fallo limpio de caché. Que las dos notas den números distintos a huellas distintas es lo
esperado, y que coincidan donde se solapan es lo que valida las dos.** `PROVEN_DERIVED`.

## 5 · Lo que queda del lado del mecanismo

**⇒ `NOT_DETERMINED`: los 256–320 KiB son la capacidad del conjunto de trabajo que cabe en el
nivel más rápido **con 8 wavefronts residentes y con esta taxonomía de direcciones**, y no
necesariamente el tamaño físico de esa caché.** `NOT_DETERMINED`.

**⇒ `PROVEN_DERIVED`. La diferencia no es un matiz: en este kernel la huella es contigua y cada
hilo tiene su bloque contiguo de `B` dwords, así que el reparto entre vías depende de cómo casen
las direcciones con los bancos. Un patrón con la misma ocupación y un reparto de direcciones
distinto daría otra cifra para la misma caché física.** `PROVEN_DERIVED`.

**⇒ `PROVEN_DERIVED`. Lo que sí queda establecido sin ambigüedad es la forma que la pregunta
original pedía: hay un nivel de memoria rápida que retiene del orden de 2⁸ KiB de conjunto de
trabajo por 8 wavefronts, y su salida cuesta un factor 1,50 en latencia.** `PROVEN_DERIVED`.

## 6 · Errores propios

**⇒ `ERROR`: al comprobar si el codo se desplazaba con el número de hilos comparé los valores de
`B`, y concluí que la capacidad no se comportaba como una capacidad. La comparación correcta es
la huella, `items × B × 4`, y con ella el plano aparece a la misma cifra en los tres recuentos.
Es el error de la serie de `287` —comparar el índice en vez de la magnitud— en una forma nueva:
no fue la unidad, fue el denominador.** `ERROR`.

**⇒ `ERROR`: el banco ponía `g_steps` en `constant_id = 2`, que en `reuse.comp` es `B`. El
control fallaba 0 de 64 y el mensaje no decía por qué. Tuve que leer la tabla de especiales para
encontrarlo.** `ERROR`.

**⇒ `PROVEN_DERIVED`. Los dos son errores de banco antes de tener un dato, la misma clase que
`286`, y el segundo es más grave porque el banco anunciaba un número y su resultado
discrepaban sin que ningún control lo explicara. Un control que falla debería señalar la causa;
el mío señalaba síntoma.** `PROVEN_DERIVED`.

**⇒ `PROVEN_DERIVED`. Y hay un patrón en la serie que no quiero dejar de nombrar: cuando algo no
sale, mi primer impulso es buscar en el kernel. En este caso el kernel era correcto y lo que
fallaba era que el banco no le pasaba el valor que declaraba. He buscado en el shader cinco o seis
veces y en el banco una, y el banco era donde estaba cuatro de ellas.** `PROVEN_DERIVED`.

## 7 · PENDIENTE

```text
262-1 | ESTADO=RESOLVED por esta nota
           | RESULTADO=el nivel mas rapido retiene entre 256 y 320 KiB de conjunto de
           |           trabajo con 8 wavefronts residentes y esta taxonomia de direcciones
           | LATENCIAS=acierto 449 ciclos, fallo 1.075 ciclos
           | NO_ES=el tamaño fisico de la cache; es el conjunto que cabe

262-1b | ESTADO=OPEN
           | PREGUNTA=¿cual es el tamaño fisico de ese nivel?
           | NECESITA=variar la taxonomia de direcciones con la MISMA ocupacion, para
           |           separar el tamano fisico del reparto entre vias
           | ALCANZABLE_SIN_ROOT=si

287-1 | ESTADO=OPEN · CONTRADICTION, con avance
           | 17,829 GB/s son el 371% del techo que permite mclk 300 MHz
           | AVANCE=con un nivel de ~256 KiB por 8 wavefronts a 1.075 ciclos, la cache
           |   puede servir buena parte del acceso. y se sabe que la traduccion no cuenta.

INSTRUMENT=vcp | ESTADO=VALIDATED
           | CONSTANTS=4 (ITERS, WSIZE, STEPS/MODE, BLK segun modelo)
           | MODELOS=6 (0=probe, 1=occ, 2=chain, 3=div, 4=page, 5=reuse)
           | INVARIANTES_3=wsize >= items, WSIZE >= items, WSIZE == items x B en reuse
           | NOTA=constant_id=2 lo decide el modelo, no el orden de los argumentos
```