# 902 · Reserva y separación son dos ejes, y el coste depende de los dos a la vez

```text
CLASSIFICATION=MEASUREMENT · TRACK=RUNTIME
CORPUS=RESEARCH/working/linux-7.1.3 + boot log de 272
HARDWARE_SCOPE=HOST-C/RX550/0000:01:00.0 · BAR=256M · GTT=5907M
WORK_CLASS=WRITE_LOCAL (banco y kernel propios) · WRITE_EXECUTION=carga Vulkan nivel 1 · NIVEL=1 · AUTORIA=AGENTE-SMU
MODIFICATIONS_CORPUS=0 · GPU INTACTA
INSTRUMENT=vcp con lane.comp, constant_id 4 STRIDE y 5 SUBRANGE | ESTADO=VALIDATED (8 controles)
```

> **`ATRIBUCIÓN REFUTADA` por `609`. La magnitud no se movió; la causa sí.**
>
> `606` §3, `607` §3 y `902` llamaron a estos ~6,8 ms **coste por envío**, cada vez con
> una causa distinta y cada vez sin un discriminante que la separara de las alternativas.
> `609` lo mide con ocho envíos seguidos del mismo comando:
>
> ```text
>   reserva 64 MiB, separado 16 MiB, ITERS=2048
>     envio 1      18,944 ms
>     envios 2..8  12,29 a 12,42 ms   dispersion 1,07%
>     diferencia   +6,599 ms
> ```
>
> **Se paga una vez, no por envío.** Los siete siguientes coinciden entre sí al 1%.
>
> **Lo que sí sobrevive de estas tres notas:** la magnitud —6,4 a 6,7 ms—, que es
> independiente de `ITERS` (6,74 ms a 512 vueltas y 6,60 ms a 2.048), independiente del
> separado una vez pasado el umbral (6,60 a 16 MiB y 6,44 a 64 MiB), y **ausente** con
> reserva de 16 MiB y separado de 16 MiB, donde da −0,06 ms.
>
> **Y la superficie de dos ejes de `902` queda corroborada:** la conjunción de los dos
> umbrales es necesaria y suficiente.
>
> **El error de fondo, y es el mismo de §5 de esta nota con `mclk`:** estaba midiendo el
> interceptor de una recta en vez de la diferencia entre dos envíos. Son dos observables
> distintos y usé el que me salía gratis del ajuste. Un interceptor que además depende
> del tramo de `ITERS` con el que se ajuste —la misma celda dio 6,704 ms con `ITERS` de
> 512 a 8.192 y 0,561 ms con `ITERS` de 64 a 512— no es un coste: es la forma de una curva.

## Qué resuelve

**⇒ `REFUTED`: que el coste de `606` §3 y `607` sea el tamaño reservado. Con la reserva fijada en
64 MiB y el separado bajando a 4 MiB, el coste cae de 6,99 a 1,22 ms.** `REFUTED`

**⇒ `REFUTED`: que sea el separado. Con la reserva en 16 MiB y el separado en 16 MiB, el coste es
0,24 ms; con la reserva en 64 MiB y el mismo separado en 16 MiB, es 7,06 ms.** `REFUTED`

**⇒ `PROVEN_DERIVED`: es una interacción de los dos ejes, con umbral en los dos.** `PROVEN_DERIVED`

```text
  reserva   separado    a (ms)
    16 MiB   16 MiB      0,24
    32 MiB   32 MiB     ~0,0
    64 MiB    4 MiB      1,22
    64 MiB   16 MiB      7,06
    64 MiB   32 MiB      6,99
    64 MiB   64 MiB      6,99
   128 MiB  128 MiB      7,11
   256 MiB  256 MiB      6,79
   512 MiB  512 MiB      6,76
```

**⇒ `PROVEN_DERIVED`: usar MENOS de un búfer más grande cuesta 29 veces más que usar todo de uno
más pequeño.** `PROVEN_DERIVED`

## 1 · Por qué hacía falta separar los dos ejes

**⇒ `PROVEN_DERIVED`. Hasta aquí «huella» significaba dos cosas a la vez: el tamaño del búfer, que
fija la traducción de direcciones que el driver prepara, y hasta dónde llegaba el kernel. Con el
banco anterior esos dos valores eran el mismo número, porque el shader reducía sus índices módulo
`WSIZE` y `WSIZE` era también el tamaño de la reserva. Cualquier explicación del coste tenía que
explicar las dos cosas a la vez, y por eso no avanzaba.** `PROVEN_DERIVED`

**⇒ `PROVEN`. Dos constantes nuevas lo separan, y las dos son specialization constants para que el
compilador pueda plegarlas y no introduzcan trabajo extra.** `PROVEN`

```glsl
layout(constant_id = 4) const uint STRIDE    = 262144u;  /* dwords que avanza por vuelta */
layout(constant_id = 5) const uint SUBRANGE  = 0u;       /* 0 = igual que WSIZE */
```

**⇒ `PROVEN`: los índices se reducen primero módulo `SUBRANGE` y sólo después módulo `WSIZE`. Con
`SUBRANGE < WSIZE` el kernel recorre una subregión y deja el resto del búfer sin tocar: la reserva
sigue siendo de 64 MiB y el número de cargas, de hilos y de trabajo de ALU es idéntico.** `PROVEN`

**⇒ `PROVEN`: `SUBRANGE = 0` reproduce exactamente el patrón anterior.** `PROVEN`

```text
  SUBRANGE=0        : 256 coinciden, 0 NO, 0 sin modificar
  SUBRANGE=4194304  : 256 coinciden, 0 NO, 0 sin modificar     (WSIZE)
  SUBRANGE=1048576  : 256 coinciden, 0 NO, 0 sin modificar     (subregion)
  tiempos: 0,000367 s contra 0,000376 s, diferencia 2,45%
```

## 2 · Las mediciones

**⇒ `MEASUREMENT. `CONTIGUO`, `STRIDE` 262.144, 65.536 hilos, `t = a + b*ITERS` con `ITERS` 512,
2.048 y 8.192, 7 muestras, control de entropía en cada corrida.** `MEASUREMENT`

**⇒ `MEASUREMENT`: reserva fijada en 64 MiB, sólo cambia el separado.** `MEASUREMENT`

| separado | `t(512)` | `t(2048)` | `t(8192)` | `a` (ms) | GB/s marginal |
|---|---|---|---|---|---|
| 4 MiB | 2,477 | 3,486 | 13,054 | **1,219** | 183,5 |
| 16 MiB | 10,060 | 19,108 | 55,186 | **7,063** | 44,6 |
| 32 MiB | 9,961 | 19,163 | 55,395 | 6,990 | 44,4 |
| 64 MiB | 10,087 | 19,136 | 55,802 | 6,992 | 44,0 |

**⇒ `PROVEN_DERIVED`: de 4 a 64 MiB de separado el coste va de 1,22 a 6,99 ms y se satura a los
16 MiB. La banda marginal se mantiene en 44 GB/s en los tres casos por encima del umbral, y el
separado de 4 MiB da 183,5 GB/s, que es caché por construcción y no dice nada de la VRAM.** `PROVEN_DERIVED`

**⇒ `PROVEN_DERIVED`: y el barrido de reserva, con el separado igual a la reserva, da el otro
extremo.** `PROVEN_DERIVED`

```text
  16 MiB -> 0,24 ms      32 MiB -> ~0,0 ms      64 MiB -> 6,80 ms
  128 MiB -> 7,11 ms     256 MiB -> 6,79 ms     512 MiB -> 6,76 ms
```

**⇒ `PROVEN_DERIVED`: a 32 MiB el coste es prácticamente cero y a 64 MiB es 6,8 ms. Hay un umbral
entre 32 y 64 MiB de reserva. Y en la tabla del separado, con reserva de 64 MiB, el umbral está
entre 4 y 16 MiB de separado.** `PROVEN_DERIVED`

**⇒ `PROVEN_DERIVED`: el resultado que más informativo separa las dos cosas. Con el mismo separado
de 16 MiB, la reserva decide entre 0,24 y 7,06 ms. Con la misma reserva de 64 MiB, el separado
decide entre 1,22 y 7,06 ms.** `PROVEN_DERIVED`

## 3 · Lo que queda, y por qué los candidatos de `607` se estrechan

**⇒ `NOT_DETERMINED`: el mecanismo. La cota es ahora que depende de la reserva y del separado a
la vez, con un umbral en cada eje.** `NOT_DETERMINED`

```text
1. descarga o invalidacion de L2 que cubre la reserva y se activa cuando el conjunto de
   trabajo se acerca al tamano reservado  -> explicaria el eje de la reserva
2. coste de traduccion por pagina, con un banco de TLB que se llena segun el separado y un
   page-table que se recorre segun la reserva  -> explicaria los dos ejes juntos
3. lectura del biffer entero por envio, que solo se nota cuando el kernel llega a las
   paginas que quedan lejos  -> tambien explicaria los dos ejes
```

**⇒ `PROVEN_DERIVED`: el candidato 2 es el único que explica por qué los dos ejes hacen falta a la
vez. Si fuera una descarga de L2 sobre la reserva, el separado no cambiaría nada; si fuera sólo
traducción por el separado, la reserva no cambiaría nada. Y los dos cambian.** `PROVEN_DERIVED`

**⇒ `NOT_DETERMINED`, y esto es lo que queda como frontera viva: la superficie. Falta la rejilla de
dos ejes —reserva por separado— para saber si es un producto, un mínimo de los dos, o una función
con dos mesetas.** `NOT_DETERMINED`

```text
  la rejilla que falta: reserva {16, 32, 64, 128} x separado {4, 16, 64, 128}
  doce puntos, caben en una corrida
  y el punto que mas discrimina: reserva 32 MiB con separado 16 MiB
     si ahi el coste es alto, el minimo de los dos no explica nada y hace falta un producto
     si es cero, la reserva manda y el separado solo importa cuando la reserva es grande
```

## 4 · Errores

**⇒ `ERROR`: propuse un control falso antes de medir. Dije que «`STRIDE` no puede cambiar el
resultado con `ADDR=1` porque sólo cambia a qué direcciones se llega». Es falso: con `ADDR=1` el
shader escribe justo la dirección, así que el resultado tiene que cambiar. El control real es que
ambos modos validan contra el modelo del host, y lo hacen.** `ERROR`

**⇒ `ERROR`: el invariante que escribí para `STRIDE` —que el paso por 64 carriles tiene que caber
en `WSIZE`— es falso. El paso es por hilo, no por grupo, y todas las direcciones se reducen módulo
`WSIZE`. Lo sustituí por la condición que sí importa: que el paso sea múltiplo de 64 para que los
bloques de vueltas sucesivas no se entrelacen.** `ERROR`

**⇒ `ERROR`: el módulo de `SUBRANGE` en el modelo del host lo apliqué a cuatro de los cinco sitios
y el quinto no casó por la sangría. Compilaba, y el control de equivalencia con `SUBRANGE=0` pasaba
igualmente porque los dos casos reducían módulo `WSIZE`. Un control que sólo ejercita el caso en el
que no ha cambiado nada no es un control.** `ERROR`

**⇒ `PROVEN_DERIVED`: la suma del día. Once errores, y cuatro de los últimos cinco eran una línea
de parche mal aplicada, no una idea equivocada. El patrón no es la arrogancia ni el descuido: es
que **reemplazar un bloque para insertar una estructura dentro de él borra lo que no se está
mirando**, y que un control que sólo prueba el caso por defecto no prueba nada.** `PROVEN_DERIVED`

## 5 · PENDIENTE

```text
606-1 | ESTADO=SATURATED por 905
           | ACOTADO=el deficit sigue a las PAGINAS distintas que el kernel toca, no al
           |         rango: 4096 paginas con rango de 16 y de 64 MiB dan 1,905 y 1,905 ms
           |         y el mismo numero de paginas con rango de 64 y de 256 MiB da 4,630 y
           |         5,018 ms. Sublineal: 4x mas paginas da 2,43x mas coste.
           | REFUTADO=rango de direcciones, pago por envio (609), solo la reserva (608)
           | BLOQUEO=MMIO: hace falta un registro del TLB o del page walker en marcha
           | REFUTADO=que sea solo la reserva, o solo el separado
           | SIGUIENTE=la rejilla de dos ejes, doce puntos
           |         el punto que mas discrimina es reserva 32 MiB con separado 16 MiB

607-1 | ESTADO=OPEN, con mejor cota
           | PIDE=candidate 2 (traduccion) es el unico que explica los dos ejes a la vez
           | ALCANZABLE_SIN_ROOT=si

BANCO  | ESTADO=VALIDATED, 8 controles
           | NUEVO=constant_id 4 STRIDE, 5 SUBRANGE en lane.comp, con invariantes de rango
           | NUEVO=el modelo del host replica el doble modulo; si no, el control de contenido
           |         compara dos cuentas distintas y pasa por casualidad
           | CONTROLES_8=contenido, estructura por modo, entropia por modo, invariantes,
           |              especializacion alcanzable, equivalencia spread(GRP=1)==reuse,
           |              trabajo ADDR=0==ADDR=1, tiempo crece con ITERS,
           |              SUBRANGE=0 == SUBRANGE==WSIZE
           | KERNELS=8 · MODELOS=8 · CONSTANTS=6
```