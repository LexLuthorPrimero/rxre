# 606 · El acantonado del BAR a 256 MiB, y un flag del banco que llevaba tiempo muerto

```text
CLASSIFICATION=MEASUREMENT+ERROR-CORRECTION · TRACK=RUNTIME
CORPUS=RESEARCH/working/linux-7.1.3 + boot-amdgpu-7.1.3-200.nobara.fc44.x86_64.log (272)
HARDWARE_SCOPE=HOST-C/RX550/0000:01:00.0 · BAR=256M · GTT=5907M
WORK_CLASS=WRITE_LOCAL (banco y kernel propios) · WRITE_EXECUTION=carga Vulkan nivel 1 · NIVEL=1
MODIFICATIONS_CORPUS=0 · GPU INTACTA
INSTRUMENT=vcp con lane.comp, modo CONTIGUO, --mem=0 y --mem=1 | ESTADO=VALIDATED
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

**⇒ `PROVEN`. La VRAM da 44,05 GB/s útiles de media con acceso contiguo, entre 16 y 512 MiB de
huella, verificado en cuatro puntos: 43,7 a 44,5.** `PROVEN`

**⇒ `PROVEN_DERIVED`. Eso es el 91,8% de un techo de 48,0 GB/s, que es 128 bits a `mclk` 1500 MHz.
La corrección del ancho de bus que hizo `602` queda corroborada por una ruta independiente.** `PROVEN_DERIVED`.

**⇒ `PROVEN`. Hay un acantonado exacto en 256 MiB, y coincide con el BAR declarado por el driver.
Una reserva visible por el host de 256 MiB o menos se sirve por la apertura del BAR; una de más cae
a la ruta GTT y cada acceso cruza el PCIe.** `PROVEN`

```text
   huella      VRAM (--mem=0)    RAM del host (--mem=1)
    128 MiB        44,26 GB/s          44,08 GB/s     igual
    256 MiB        44,53 GB/s           1,38 GB/s     ACANTONADO
    320 MiB        43,67 GB/s           1,38 GB/s     ACANTONADO
    512 MiB        43,72 GB/s           1,37 GB/s     ACANTONADO
```

**⇒ `CORROBORATED`. Los 1,37 a 1,38 GB/s de la ruta GTT coinciden con los 1,377 GB/s que midió `286`
con `pciebw`, una herramienta completamente distinta, con una diferencia del 0,22% al 0,51%.** `CORROBORATED`

**⇒ `REFUTED`: la atribución de `602` §4. Los 6,8 ms por despacho NO son coste de descarga.** `REFUTED`

**⇒ `ERROR`: `--mem=vram|host|both` es un flag muerto desde que existe. El banco lo parsea con
`strtoul`, y las palabras dan cero.** `ERROR`

## 1 · Por qué el acantonado decide lo que decide

**⇒ `PROVEN_DERIVED`. Un banco que no distinguiera la ruta de memoria no podría decir si los 44 GB/s
salen de la VRAM o de la RAM del sistema. El acantonado los separa sin ambigüedad: por debajo de
256 MiB los dos modos dan el mismo número, y por encima uno colapsa.** `PROVEN_DERIVED`

**⇒ `PROVEN`. El valor del log que lo fija: `boot-amdgpu-7.1.3-200.nobara.fc44.x86_64.log` línea 34,
`[drm] Detected VRAM RAM=2048M, BAR=256M`, y línea 37, `5907M of GTT memory ready`. El acantonado
medido cae entre 128 MiB y 256 MiB de huella, es decir justo donde el BAR se agota.** `PROVEN`

**⇒ `PROVEN_DERIVED`. Y el modo `--mem=1` por debajo de 256 MiB da 44 GB/s porque la apertura del
BAR mapea la VRAM: el shader sigue leyendo VRAM, sólo que a través de una ventana que el host
también puede tocar. Por encima del BAR no hay apertura y la reserva va a RAM del sistema
accedida por el GTT, y entonces cada carga de carril es un cruce de PCIe.** `PROVEN_DERIVED`

**⇒ `PROVEN_DERIVED`. Consecuencia de diseño, y es de las que cambian un driver: cualquier
reserva visible por el host de más de 256 MiB en esta placa queda limitada por el enlace medido en
`286`, no por la GPU. Con 44 GB/s en VRAM y 1,38 GB/s por PCIe, la diferencia es de 32 veces, y el
error de decidir mal cuesta un 97% del ancho de banda.** `PROVEN_DERIVED`

## 2 · El flag muerto, y lo que invalida

**⇒ `ERROR`: línea 163 del banco hace `g_mem = (int)strtoul(argv[i] + 6, NULL, 10)`. Con
`--mem=vram` el resto de la cadena es `vram`, y `strtoul` de eso es `0`. Con `--mem=host`, `0`.
Con `--mem=both`, `0`. Los tres modos documentados en las líneas 377-379 son exactamente el modo
por defecto.** `ERROR`

```text
  --mem=0      -> tipo[0] flags=0x00000001   DEVICE_LOCAL
  --mem=1      -> tipo[2] flags=0x00000006   HOST_VISIBLE | HOST_COHERENT
  --mem=2      -> tipo[3] flags=0x00000007   HOST_VISIBLE | HOST_COHERENT | DEVICE_LOCAL
  --mem=vram   -> tipo[0] flags=0x00000001   <- caido a 0
  --mem=host   -> tipo[0] flags=0x00000001   <- caido a 0
  --mem=both   -> tipo[0] flags=0x00000001   <- caido a 0
```

**⇒ `PROVEN_DERIVED`: la primera vez que lo ejecuté creí que el acantonado de 32 y 64 MiB era de
la ruta de VRAM, porque los escalones aparecían idénticos con las dos palabras. No aparecían
idénticos porque eran las dos la misma ejecución.** `PROVEN_DERIVED`

**⇒ `REFUTED`: el discriminante de `282`. Esa nota usó `--mem=host` para separar VRAM de RAM, y con
el flag en ese estado midió DEVICE_LOCAL las dos veces. Lo que `282` afirmó no separó no está
separado.** `REFUTED`

**⇒ `NOT_DETERMINED`: qué habría dado `282` con el flag vivo. Ahora se puede repetir en una
corrida, y el resultado es el que acabo de medir: para el acceso contiguo la ruta no cambia nada
por debajo del BAR. La conclusión de `282` de que el shader no distingue VRAM de RAM puede ser
correcta y estar mal argumentada, porque el experimento no varió lo que creía variar.** `NOT_DETERMINED`

**⇒ `PROVEN_DERIVED`: el patrón es el de siempre y ya no es un accidente. Once líneas de programa,
un comentario que anuncia una interfaz con tres palabras, y un `strtoul` que acepta un número. El
comentario describía el instrumento que yo creía tener, no el que tenía. La lectura de la
interfaz de un instrumento propio no es un detalle: es una aserción que hay que verificar como
cualquier otra, y aquí verifiqué el resultado de la corrida y no el camino que took.** `PROVEN_DERIVED`

## 3 · `602` §4 era un número correcto con un inventado

**⇒ `ERROR`: `602` §4-publicó «5,4 a 6,8 ms por despacho» y lo atribuyó a coste de descarga. El
número sale; la causa la puse yo sin discriminarla.** `ERROR`

**⇒ `PROVEN`: la región temporizada del banco, líneas 529-534, es exactamente `vkResetFences`,
`vkQueueSubmit` y `vkWaitForFences`. La creación del búfer y la subida del patrón ocurren antes,
en las líneas 372 a 527. Así que el intercepto es de envío y fence, y sin embargo depende de la
huella, cosa que un envío no puede hacer: `vkQueueSubmit` no sabe quantos MiB tiene el búfer.** `PROVEN`

**⇒ `MEASUREMENT`: el intercepto frente a la huella, con dos puntos por ajuste y el régimen lineal
verificado antes, `CONTIGUO`, 65.536 hilos, control de entropía en cada corrida.** `MEASUREMENT`

| huella | `a` (ms) | salto |
|---|---|---|
| 16 MiB | 0,198 | |
| 32 MiB | 3,447 | **+3,25 ms** |
| 64 MiB | 6,924 | **+3,48 ms** |
| 128 MiB | 7,117 | +0,19 ms, plano |

**⇒ `PROVEN_DERIVED`: dos escalones de ~3,3 ms al cruzar 32 y 64 MiB, y plano de 64 a 512 MiB. La
huella se multiplica por ocho entre 16 y 128 MiB y el coste sólo por 35,9: no es proporcional, y
un coste de envío tampoco lo sería.** `PROVEN_DERIVED`

**⇒ `PROVEN`: los escalones aparecen igual en la ruta de VRAM y en la de RAM del host, con la
misma magnitud. No son de la apertura del BAR, porque el acantonado del BAR está en 256 MiB y
estos están en 32 y 64.** `PROVEN`

**⇒ `NOT_DETERMINED`: el mecanismo de los dos escalones de 3,3 ms. No es un coste de envío, no es
la apertura del BAR, no es proporcional a la huella y no aparece por debajo de 32 MiB. Quedan
candidatos que se distinguen con observables distintos, y ninguno está eliminado todavía.** `NOT_DETERMINED`

```text
1. coste de traduccion de paginas: 32 MiB son 8192 paginas de 4 KiB y 64 MiB son
   16384. El banco de TLB de esta GPU tiene un numero finito de entradas y cada
   pagina nueva cuesta una traduccion.
2. una pasada de invalidacion de L2 que el driver hace cuando el buffer
   supera cierto tamano.
3. una accion de firmware o de DPM que se dispara por tamano de biffer.
4. el page-table del GPUVM, que cambia de nivel al pasar de cierto tamano.
```

**⇒ `NOT_DETERMINED`, y es la frontera mas util que sale de esta nota: el umbral esta entre 16 y
32 MiB, se puede localizar al MiB, y comparar ese número contra los candidatos de arriba es un
discriminante directo. Queda abierto, no cerrado.** `NOT_DETERMINED`

## 4 · La banda, corroborada por una segunda ruta

**⇒ `CORROBORATED`: `602` dio 43,2 GB/s marginales por un ajuste de dos puntos. Con cinco puntos y
mínimos cuadrados, y después con la curva completa de siete puntos a 256 MiB, sale 44,0 a 44,5.
La cifra de `602` era correcta; lo que no lo era era su explicación.** `CORROBORATED`

| | GB/s | % de 48,0 |
|---|---|---|
| 16 MiB, 5 puntos | 44,30 | 92,3% |
| 128 MiB | 44,29 | 92,3% |
| 256 MiB | 44,53 | 92,8% |
| 320 MiB | 43,67 | 91,0% |
| 512 MiB | 43,72 | 91,1% |

**⇒ `PROVEN_DERIVED`: 91,8% de media de un techo de 48,0 GB/s, sobre un rango de huella de 16 a
512 MiB, con la entropía verificada y el reparto de direcciones verificado. La corrección del
ancho de bus de `602` no dependía de una medición dudosa: depende de esta, que tiene control de
entropía y acantonado de BAR.** `PROVEN_DERIVED`

## 5 · Errores

| # | error | cómo salió |
|---|---|---|
| 1 | atribuí 6,8 ms a la descarga sin discriminarla | la huella de la que depende lo desmiente |
| 2 | `--mem=host` no cambiaba nada y lo leí como si cambiara | el `MEMTIPOS` de la corrida, que ignored |
| 3 | creí que los escalones eran propios de la VRAM | eran la misma ejecución dos veces |

**⇒ `PROVEN_DERIVED`: el segundo es el más instructive de los tres. La corrida imprimía el tipo
de memoria que eligió, `tipo[0]`, y estaba ahí, en la salida, y no lo miré. Un instrumento que
imprime su propia configuración sólo sirve si alguien lee esa línea.** `PROVEN_DERIVED`

## 6 · PENDIENTE

```text
602-4 | ESTADO=RESUELTA por 606
           | REFUTADA la atribucion: no es coste de descarga
           | RESUELTO=los 6,8 ms son un coste quantized en la huella, con escalones de 3,3 ms
           |          al cruzar 32 y 64 MiB, plano de 64 a 512 MiB

606-1 | ESTADO=OPEN, NUEVO
           | PREGUNTA=que son los escalones de 3,3 ms en 32 y 64 MiB
           | DISC_RIMINANTE=localizar el umbral al MiB entre 16 y 32, y comparar contra
           |          8192 paginas de 4 KiB, contra el numero de lineas de 128 B, y contra
           |          los niveles del page table de GPUVM
           | ALCANZABLE_SIN_ROOT=si

606-2 | ESTADO=OPEN, NUEVO
           | PREGUNTA=repetir el discriminante de 282 con --mem=1 vivo
           | POR_QUE=282 uso --mem=host, que caia a 0, luego no separo nada
           | NOTA=el acantonado del BAR da ahora el separador correcto, y es 256 MiB

282   | ESTADO=AFECTADA por 606
           | SU_DISC_RIMINANTE_NO_SE_EJECUTO=--mem=host devolvia 0 = DEVICE_LOCAL
           | PENDIENTE=repetir con --mem=1

286   | ESTADO=CORROBORADA por 606
           | su 1,377 GB/s de PCIe h->d aparece como 1,37-1,38 GB/s en la ruta GTT,
           | con una herramienta distinta y una diferencia del 0,22% al 0,51%

BANCO  | ESTADO=VALIDATED, con un defecto conocido y una leccion
           | DEFECTO=--mem=vram|host|both caido a 0 por strtoul; solo funcionan 0, 1 y 2
           | ACCION=aceptar las palabras, no solo numeros, y que el valor no pedido sea error
           | KERNELS=8 · MODELOS=8 · CONSTANTS=6 · INVARIANTES=5 · CONTROLES=6
```