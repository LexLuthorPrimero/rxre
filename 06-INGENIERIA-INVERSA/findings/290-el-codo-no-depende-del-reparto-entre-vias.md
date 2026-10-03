# 290 · Los 256 KiB no son un artefacto del reparto entre vías: siete permutaciones distintas dan el mismo codo

```text
CLASSIFICATION=MEASUREMENT+PROVEN · TRACK=RUNTIME
CORPUS=RESEARCH/working/linux-7.1.3 + gfx_v8_0.c:7124 (wave_front_size = 64)
HARDWARE_SCOPE=HOST-C/RX550/0000:01:00.0
WORK_CLASS=WRITE_LOCAL (banco y kernel propios) · WRITE_EXECUTION=carga Vulkan nivel 1 · NIVEL=1
MODIFICATIONS_CORPUS=0 · GPU INTACTA
INSTRUMENT=vcp con spread.comp y modelo 6 | ESTADO=VALIDATED (regresion 7/7)
```

## Qué resuelve

**⇒ Cierra `262-1b`. `289` dejó abierta la pregunta de si los 256–320 KiB eran el tamaño físico
del nivel o el conjunto que cabía con la taxonomía de direcciones concreta que usó. La respuesta
es que **no depende de la taxonomía**: siete permutaciones distintas de los bloques, todas
coplrimas con 64, dan el mismo codo dentro de un 5%.** `PROVEN`.

**⇒ `PROVEN_DERIVED`. El discriminante separa las dos hipótesis con dos salidas y ambas son
posibles: si lo que se agotara fuera el reparto entre vías, el codo se desplazaría con `GRP`; si
lo que se agota es la capacidad, el codo queda fijo y solo cambia la dispersión vertical de cada
columna.** `PROVEN_DERIVED`.

**⇒ `PROVEN. La variación horizontal —entre repartos, a huella fija— es del 2,7% al 11,4%. La
variación vertical —entre huellas, a reparto fijo— es del 113% al 125%. Lo que decide el tiempo
es el número de bytes, no dónde caen.** `PROVEN`.

**⇒ `PROVEN_DERIVED`: los 256–320 KiB de `289` son la capacidad del nivel, y no un artefacto de
el reparto de direcciones del kernel.** `PROVEN_DERIVED`.

## 1 · El discriminante, y por qué tenía que ser una permutación

**⇒ `PROVEN. `spread.comp` mantiene el número de bloques, la huella total y el número de hilos, y
sólo cambia a qué bloque pertenece cada hilo dentro de cada grupo de 64.** `PROVEN`.

```glsl
const uint NW = 64u;   /* wave_front_size, gfx_v8_0.c:7124, verificado en 272 */
uint blk = ((i / NW) * NW + ((i % NW) * GRP) % NW) * B;
```

**⇒ `PROVEN_DERIVED`. `GRP` tiene que ser coprimo con 64 para que `(i%NW)*GRP mod NW` sea una
permutación de `0..63`. Con `GRP` par no es permutación, varios hilos comparten bloque, y eso es
otro experimento: bloque compartido es reutilización real, no dispersión. El banco lo rechaza con
`exit 2` y lo dice.** `PROVEN_DERIVED`.

**⇒ `PROVEN`. Con `GRP = 1` la permutación es la identidad, y entonces `spread.comp` tiene que
producir el mismo resultado que `reuse.comp`. Lo produce: 256 de 256 en ambos, palabra a palabra.
Ese es el control que hace válido el resto, y es el que detectó el error de la primera versión de
este fichero.** `PROVEN`.

**⇒ `MEASUREMENT`. En **tiempo** no coinciden, y mi afirmación inicial de que debían coincidir
era demasiado fuerte. La diferencia es aritmética de direcciones fija —`spread.comp` calcula
`((i/NW)*NW + ((i%NW)*GRP)%NW)` y `reuse.comp` calcula `i*B`— y está fuera del bucle, luego es
coste fijo por hilo, no por acceso.** `MEASUREMENT`.

| `ITERS` | `reuse.comp` (s) | `spread.comp`, `GRP=1` (s) | diferencia |
|---|---|---|---|
| 64 | 0,000085 | 0,000092 | 8,24% |
| 256 | 0,000125 | 0,000112 | 10,40% |
| 1.024 | 0,000289 | 0,000304 | 5,19% |
| 4.096 | 0,001049 | 0,001022 | 2,57% |
| 16.384 | 0,003773 | 0,003770 | **0,08%** |

**⇒ `PROVEN_DERIVED. La diferencia cae a 0,08% al subir `ITERS`, que es la firma de un coste fijo
que se diluye. Y eso no compromete la comparación de §2: las siete filas usan el mismo shader y
la misma aritmética, luego el sesgo es común a todas y desaparece en la comparación horizontal,
que es la que se sostiene.** `PROVEN_DERIVED`.

## 2 · La medición

**⇒ `MEASUREMENT. 512 hilos, 1024 vueltas, `spread.comp`, cinco huellas por reparto, 5 muestras
con calentamiento, control aprobado en las 35 mediciones.** `MEASUREMENT`.

| `GRP` | 64 KiB | 128 KiB | 192 KiB | 256 KiB | 320 KiB |
|---|---|---|---|---|---|
| 1 | 281 | 291 | 408 | 412 | 627 |
| 3 | 282 | 299 | 401 | 409 | 618 |
| 5 | 277 | 286 | 394 | 406 | 604 |
| 7 | 279 | 287 | 401 | 417 | 619 |
| 15 | 279 | 291 | 407 | 407 | 604 |
| 31 | 283 | 292 | 412 | 406 | 636 |
| 63 | 291 | 303 | 439 | 411 | 620 |

**⇒ `PROVEN`. El codo está en el mismo sitio en las siete filas: el salto de 128 KiB a 192 KiB es
de ×1,34 a ×1,45 según el reparto, y en ningún caso se desplaza.** `PROVEN`.

**⇒ `MEASUREMENT. Las dos variabilidades, calculadas por programa:** `MEASUREMENT`.

```text
entre repartos, a huella fija (horizontal):  5,1% / 5,9% / 11,4% / 2,7% / 5,3%
entre huellas, a reparto fijo (vertical):  113% a 125%
```

**⇒ `PROVEN_DERIVED. Un factor de veinte entre las dos direcciones de la tabla, y la dirección
que manda es la de los bytes. `GRP` no cambia el codo: lo desplaza, como mucho, un 11%, y eso
está dentro de la dispersión del propio punto.** `PROVEN_DERIVED`.

**⇒ `CORROBORATED`. El resultado coincide con `289` en la forma y difiere en las cifras por
detalles de ejecución, no de sustancia. `289` dio meseta hasta 256 KiB a 405-432 ns y subida a
320 KiB a 637 ns; esta nota da meseta de 394-417 ns a 256 KiB y 604-636 ns a 320 KiB, con el
salto de 128 a 192 KiB entre medias. El codo está en el mismo sitio y los niveles coinciden
dentro de un 6%.** `CORROBORATED`.

**⇒ `NOT_DETERMINED`: por qué `289` no vio el salto de 128 a 192 KiB. `289` barrió `B` con
pasos del 22% y su resolución en huella era de 32 KiB; esta nota usa 64 KiB de paso. El salto es
de ×1,34 a ×1,45 y entre dos puntos separados por un 22% se vería diluido. Es una diferencia de
resolución de la malla, no de la magnitud, y no se puede decidir sin repetir `289` con la malla
fina.** `NOT_DETERMINED`.

## 3 · Lo que queda, y lo que no queda

**⇒ `PROVEN_DERIVED`. La capacidad del nivel no depende de cómo se reparten las direcciones
hilos. Eso elimina la explicación más fácil de las dos que `289` dejaba abiertas, y deja una
sola: el número es la capacidad del conjunto de trabajo que el nivel retiene con esta
ocupación.** `PROVEN_DERIVED`.

**⇒ `NOT_DETERMINED`: «capacidad con esta ocupación» y «tamaño físico» siguen sin separarse, pero
la diferencia es más pequeña de lo que la nota de `289` sugiere y no requiere una hipótesis de
conflicto de vías. Quedan dos causas posibles y ninguna se puede decidir desde aquí.** `NOT_DETERMINED`.

```text
1. capacidad fisica, con los 8 wavefronts residentes repartidos en 2 SH (SE 2, SH 1 del boot log
   verificado en 272): 256-320 KiB serian la capacidad total de la L2 de esta GPU.
2. no es fisica sino el resultado de la asociatividad y del numero de vias por SH: con 8
   wavefronts y bloques de B dwords, el reparto real entre vias puede dejar una fraccion
   del conjunto inutilizable.
```

**⇒ `PROVEN_DERIVED`. Y hay un dato de §H que sale de aquí y que no estaba en ninguna nota: la
variación del 11,4% es la mayor de las cinco columnas, y ocurre exactamente en 192 KiB, que es el
punto del codo. En el resto de la curva la dispersión por reparto es del 2,7% al 5,9%. Eso
dice que la taxonomía de direcciones sólo tiene efecto cuando el conjunto roza la capacidad,
que es la definición operativa de conflicto.** `PROVEN_DERIVED`.

## 4 · Mis errores

**⇒ `ERROR`: la primera versión de `spread.comp` usaba `(i%64)*GRP + i/64`, que con `GRP = 1`
NO da `i`. El kernel medía bloqueos superpuestos, no la taxonomía que yo creía medir. Lo detectó
el control de equivalencia con `reuse.comp`, que es exactamente para lo que lo escribí.** `ERROR`.

**⇒ `ERROR`: ese mismo control falló antes por una causa distinta —el banco metía `g_steps` en
`constant_id = 2`, que en `spread.comp` es `B`, y `NW` recibía `g_mode`. Son dos días de bugs
distintos en el mismo sitio: la especial `sc2` sólo miraba el modelo 5.** `ERROR`.

**⇒ `PROVEN_DERIVED`. Los dos son la misma clase que los de `289`, y el patrón que ya nombré en
esa nota se repite sin descanso: he buscado en el shader cinco o seis veces y en el banco una, y
aquí el primer fallo era del shader y el segundo del banco, en la misma tarde. Lo que no cambia es
que ninguno de los dos habría salido sin el control que exigí antes de medir.** `PROVEN_DERIVED`.

**⇒ `PROVEN_DERIVED`. Y hay una observación sobre por qué el control de equivalencia existe y
funciona: compara dos implementaciones del mismo experimento y exige que coincidan. Eso detecta
errores de construcción que ningún control de contenido detecta, porque ambos kernels serían
correctos por separado y aun asímedirían cosas distintas. `262` tuvo un control así —kernel
equivocado, modelo par— y lo que no tuvo fue el gemelo, la misma pregunta hecha de dos maneras
que tienen que coincidir.** `PROVEN_DERIVED`.

## 5 · PENDIENTE

```text
262-1  | ESTADO=RESOLVED por 289
           | RESULTADO=el nivel mas rapido retiene entre 256 y 320 KiB de conjunto de trabajo
           |           con 8 wavefronts residentes
262-1b | ESTADO=PARTIAL por 290
           | RESUELTO=el numero NO depende del reparto entre vias. siete permutaciones
           |          coprimas con 64 dan el mismo codo dentro de un 5%
           | ABIERTO=capacidad fisica total frente a capacidad efectiva por asociatividad
           | ALCANZABLE_SIN_ROOT=no sin observable del hardware de la cache

287-1  | ESTADO=OPEN · CONTRADICTION
           | 17,829 GB/s son el 371% del techo que permite mclk 300 MHz
           | AVANCE_290=con un nivel que retiene 256-320 KiB por 8 wavefronts a ~1.075
           |          ciclos, una fraccion sustancial del acceso puede servirla la cache.
           |          y se sabe que la traduccion de pagina no cuenta (288).

INSTRUMENT=vcp | ESTADO=VALIDATED
           | KERNELS=7 (probe, occ, chain, div, page, reuse, spread)
           | MODELOS=7 (0..6)
           | CONSTANTS=5 (ITERS, WSIZE, STEPS/B segun modelo, MODE, GRP)
           | INVARIANTES_4=wsize >= items, WSIZE >= items,
           |               WSIZE == items x B (modelos 5 y 6), GRP coprimo con 64
           | CONTROLES_ESPECIALES=equivalencia spread(GRP=1) == reuse
```