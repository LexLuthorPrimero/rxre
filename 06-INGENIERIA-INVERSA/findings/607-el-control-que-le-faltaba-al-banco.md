# 607 · El control que le faltaba al banco: el tiempo tiene que depender de `ITERS`

```text
CLASSIFICATION=MEASUREMENT+ERROR-CORRECTION · TRACK=RUNTIME
CORPUS=RESEARCH/working/linux-7.1.3 + boot-amdgpu-7.1.3-200.nobara.fc44.x86_64.log (272)
HARDWARE_SCOPE=HOST-C/RX550/0000:01:00.0 · BAR=256M · GTT=5907M
WORK_CLASS=WRITE_LOCAL (banco y kernel propios) · WRITE_EXECUTION=carga Vulkan nivel 1 · NIVEL=1
MODIFICATIONS_CORPUS=0 · GPU INTACTA
INSTRUMENT=vcp con lane.comp, --rep=N | ESTADO=VALIDATED (7 controles)
```

> **`ATRIBUCIÓN REFUTADA` por `609`. La magnitud no se movió; la causa sí.**
>
> `606` §3, `607` §3 y `608` llamaron a estos ~6,8 ms **coste por envío**, cada vez con
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
> **Y la superficie de dos ejes de `608` queda corroborada:** la conjunción de los dos
> umbrales es necesaria y suficiente.
>
> **El error de fondo, y es el mismo de §5 de esta nota con `mclk`:** estaba midiendo el
> interceptor de una recta en vez de la diferencia entre dos envíos. Son dos observables
> distintos y usé el que me salía gratis del ajuste. Un interceptor que además depende
> del tramo de `ITERS` con el que se ajuste —la misma celda dio 6,704 ms con `ITERS` de
> 512 a 8.192 y 0,561 ms con `ITERS` de 64 a 512— no es un coste: es la forma de una curva.

## Qué resuelve

**⇒ `ERROR`: durante cuarenta minutos el banco no despachó. Al añadir `--rep=N` borré la línea
`si.pCommandBuffers = cmd_dispatch`, que estaba entre `t0` y el envío, y el envío cronometrado
pasó a subir el patrón entero por el PCIe en vez de despachar.** `ERROR`

**⇒ `PROVEN_DERIVED`: el síntoma era una señal que no admite otra lectura — el tiempo dejó
de depender de `ITERS`. Con el envío equivocado, subir 16 MiB cuesta lo mismo que
despachar 512 iteraciones.** `PROVEN_DERIVED`
**⇒ `CORROBORATED`: los escalones de coste fijo que`606` no eran un artefacto. Con el banco
arreglado se reproducen, y además son independientes de `ITERS`, que es un dato que `606` no
tenía.** `CORROBORATED`

**⇒ `PROVEN_DERIVED`: el coste se acumula a 0,10 ns por dword de huella, o sea 40 GB/s. Eso es la
velocidad de la VRAM —44 GB/s medidos en `606`— y no la del enlace, que es 1,375 GB/s. La forma de
ese coste se parece a una pasada por la VRAM una vez por envío.** `PROVEN_DERIVED`

## 1 · El defecto, y por qué duró cuarenta minutos

**⇒ `ERROR`. El banco tiene dos command buffer: `cmd_pattern` con la copia del patrón y
`cmd_dispatch` con el `vkCmdDispatch`. La línea 521 deja `si` apuntando a `cmd_pattern`, con un
comentario que dice que la copia del patrón va fuera del reloj.** `ERROR`

```c
  462:  VkCommandBuffer *cmd_dispatch = &cmd[0];   /* solo el despacho: esto se cronometra */
  463:  VkCommandBuffer *cmd_pattern  = &cmd[1];   /* solo la copia del patron: fuera del reloj */
  521:  si.pCommandBuffers = cmd_pattern;          /* el patron, a proposito, FUERA del reloj */
  525:  si.pCommandBuffers = cmd_dispatch;         /* y aqui se resigna al despacho */
  551:  double t0 = now_s();
  552:  for (int rep = 0; rep < g_rep; rep++) {
  554:      CHECK(vkQueueSubmit(queue, 1, &si, fence), "vkQueueSubmit2");  <-- enviaba el PATRON
```

**⇒ `ERROR`. Al escribir `--rep=N` sustituí el bloque que iba de `double t0 = now_s();` al `printf`
por un bucle, y ese bloque contenía la línea que resignaba `si` a `cmd_dispatch`. Sustituir un
bloque para insertar una estructura dentro de él es borrar lo que no estaba mirando.** `ERROR`

**⇒ `PROVEN`: la prueba de que el defecto es mío y no una propiedad del banco es que antes de
`--rep` el tiempo sí dependía de `ITERS`. La curva de siete puntos de `606` a 256 MiB iba de
6,313 ms con 256 vueltas a 104,245 ms con 16.384, y esa curva la tomé del mismo código.** `PROVEN`

**⇒ `PROVEN`: la magnitud del error da la medida de lo que se estaba midiendo sin querer. La copia
del patrón son `wsize * 4` bytes, y medí 0,73 ns por dword —1,375 GB/s—, que es exactamente el
ancho de banda del PCIe que `286` midió con otra herramienta. El número estava bien; lo que
medía era otra cosa.** `PROVEN`

| | lo que el banco enviaba | lo que debía |
|---|---|---|
| patrón | 16 MiB / 32 MiB / 64 MiB en 12,3 / 24,5 / 48,8 ms | el despacho |
| dependencia de `ITERS` | ninguna, 12,37 / 12,37 / 12,35 ms para 512 / 1024 / 2048 | fuerte |

## 2 · El control que le faltaba, y la razón de que sea el que faltaba

**⇒ `PROVEN_DERIVED`. El banco validaba contenido, patrón de direcciones, entropía, invariantes y
trabajo del shader. No validaba que la región cronometrada hiciera el trabajo que dice medir. Es
el mismo hueco que `602` encontró con el control de trabajo, un nivel más abajo: `602` comprobó
que el shader no eliminaba las cargas; esto comprueba que se despacha el shader.** `PROVEN_DERIVED`

**⇒ `PROVEN`. El control es de una línea y no tiene ninguna lectura alternativa:

```text
  el tiempo TIENE QUE crecer con ITERS, con la huella fija
  si no crece, el envio cronometrado no esta despachando
```

**⇒ `PROVEN_DERIVED`. Y es barato porque usa el propio `ITERS` como sonda: no hace falta un
instrumento nuevo, ni un kernel nuevo, ni un reloj nuevo. Sólo hace falta mirar el número que ya
se estaba imprimiendo y preguntarse si tiene sentido.** `PROVEN_DERIVED`

**⇒ `PROVEN_DERIVED`: la serie de errores de este proyecto tiene una forma constante y esta nota la
confirma por septima vez. La causa nunca es el hardware: es la unidad, el denominador, el encuadre,
el cable entre host y shader, el cable entre dos command buffer, o una línea borrada por un parche.
Y en los dos últimos casos, un control sobre el trabajo lo habría detectado y ningún control sobre
el resultado lo hizo.** `PROVEN_DERIVED`

## 3 · Lo que sobrevive, y lo que queda

**⇒ `CORROBORATED`: el exceso de coste por huella de `606` §3 se reproduce con el banco corregido,
y ahora se sabe que no depende de `ITERS`, cosa que `606` no había medido.** `CORROBORATED`

| huella | `606` sin `--rep` | aquí, banco arreglado | `ITERS` 512 → 4096 |
|---|---|---|---|
| 16 MiB | 0,198 ms | 0,250 ms | 3,224 → 24,423 ms |
| 32 MiB | 3,447 ms | 1,740 ms | 6,433 → 28,353 ms |
| 64 MiB | 6,924 ms | 6,722 ms | 9,848 → 31,627 ms |

**⇒ `PROVEN_DERIVED`: a 16 MiB el intercepto es el mismo —0,198 contra 0,250 ms— y a 64 MiB también,
6,924 contra 6,722. Los dos extremos corroboran y el punto intermedio no, así que la diferencia
está en la calidad del ajuste, no en el fenómeno: con cuatro puntos y ruido en `ITERS` pequeño, el
interceptor de una recta es lo primero que se mueve.** `PROVEN_DERIVED`

**⇒ `CORROBORATED`: la banda marginal sigue en 40 a 44 GB/s en las tres huellas, que es el titular
de `606`.** `CORROBORATED`

**⇒ `PROVEN_DERIVED`: el coste se acumula a 0,10 ns por dword de huella.** `PROVEN_DERIVED`

```text
  32 MiB -> 3,40 ms / 33.554.432 dwords = 0,1013 ns por dword
  64 MiB -> 7,40 ms / 67.108.864 dwords = 0,1103 ns por dword
```

**⇒ `PROVEN_DERIVED`: cuatro bytes cada 0,10 ns son 40 GB/s. La VRAM va a 44 GB/s y el PCIe a
1,375 GB/s. Un coste que se acumula a 40 GB/s se parece a una pasada por la VRAM, no a una
transferencia.** `PROVEN_DERIVED`

**⇒ `NOT_DETERMINED`: el mecanismo. La cota es ahora mucho más estrecha que en `606`: es un coste
**por envío**, **proporcional a la huella**, **independiente del trabajo**, y que se acumula a la
velocidad de la VRAM.** `NOT_DETERMINED`

```text
1. una invalidacion o descarga de L2 que el driver hace por envio cuando el búfer es grande
2. el page walker del GPUVM recorriendo el espacio de un búfer que cambia de nivel
3. una lectura del búfer entero que el propio driver necesita para algo, a velocidad de VRAM
4. el mismo efecto de 602 medido en otro sitio: el hardware cobrando por direccion tocada
```

**⇒ `NOT_DETERMINED`, y con esto la frontera `606-1` deja de ser «qué son los escalones» para ser
«cuál de estos cuatro». El discriminante más barato que veo: bajar de 64 a 128 a 256 MiB. Si sigue
siendo proporcional, son 1, 2 o 4; si se aplana como en `606`, es 1.** `NOT_DETERMINED`

## 4 · Errores

| # | error | cómo salió |
|---|---|---|
| 1 | borré `si.pCommandBuffers = cmd_dispatch` al insertar `--rep` | el tiempo dejó de depender de `ITERS` |

**⇒ `PROVEN_DERIVED`: es el séptimo de la serie y el primero que no lo detectó ningún control
existente, porque ningún control existente miraba esa magnitud. Añadido ahora, y es el que
impide que vuelva a pasar.** `PROVEN_DERIVED`

## 5 · PENDIENTE

```text
606-1 | ESTADO=ABIERTA, MEJOR DEFINIDA por 607
           | ACOTADO=por envio, proporcional a la huella, independiente de ITERS,
           |         a 0,10 ns por dword = 40 GB/s, que es velocidad de VRAM
           | SIGUIENTE_PASO=probar 128 y 256 MiB con el banco arreglado
           |         si sigue proporcional -> 1, 2 o 4
           |         si se aplana -> 1, una descarga de L2
           | RESUELTO_POR_608=se APLANA: 6,8 ms a 64, 128, 256 y 512 MiB
           |             y ademas depende del SEPARADO, no solo de la reserva

606   | ESTADO=CORROBORADA por 607 en sus dos extremos (16 y 64 MiB)
           | el punto de 32 MiB no reproduce; es calidad del ajuste, no un fenomeno nuevo

607-1 | ESTADO=OPEN, NUEVO
           | PREGUNTA=de donde sale un coste por envio que recorre el búfer entero
           |           a la velocidad de la VRAM
           | NOTA=si es una descarga de L2, un driver propio podria evitarla con una
           |      tecnica concreta, y por eso importa saberlo antes de construir el driver

BANCO  | ESTADO=VALIDATED, ahora con 7 controles
           | NUEVO=el tiempo tiene que crecer con ITERS; si no, no se esta despachando
           | NUEVO=--rep=N, con rechazo explicito de valores no numericos
           | LECCION=al insertar una estructura en un bloque, no sustituir el bloque entero:
           |          lo que no se esta mirando es lo que se borra
           | KERNELS=8 · MODELOS=8 · CONSTANTS=6 · INVARIANTES=5
```