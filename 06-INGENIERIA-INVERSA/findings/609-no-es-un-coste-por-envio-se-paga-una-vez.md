# 609 · No es un coste por envío: se paga una vez, y tres notas lo atribuiron mal

```text
CLASSIFICATION=MEASUREMENT+ERROR-CORRECTION+REFUTED · TRACK=RUNTIME
CORPUS=RESEARCH/working/linux-7.1.3 + boot log de 272
HARDWARE_SCOPE=HOST-C/RX550/0000:01:00.0 · BAR=256M · GTT=5907M
WORK_CLASS=WRITE_LOCAL (banco y kernel propios) · WRITE_EXECUTION=carga Vulkan nivel 1 · NIVEL=1
MODIFICATIONS_CORPUS=0 · GPU INTACTA
INSTRUMENT=vcp con lane.comp y --rep=8 | ESTADO=VALIDATED (9 controles)
```

## Qué resuelve

**⇒ `REFUTED`, por tercera vez y con el mismo número: el coste de 6,8 ms NO es por envío. Se paga
una vez.** `REFUTED`

**⇒ `PROVEN`: ocho envíos seguidos del mismo comando. El primero cuesta 6,4 a 6,7 ms más que los
siguientes, y los siete siguientes coinciden entre sí con una dispersión del 0,36% al 2,85%.** `PROVEN`

**⇒ `PROVEN_DERIVED`: el coste no depende de `ITERS`. Con 512 vueltas es 6,74 ms y con 2.048 es
6,60 ms, y también 6,44 ms con otro separado. Tres medidas, una magnitud.** `PROVEN_DERIVED`

**⇒ `PROVEN_DERIVED`: aparece sólo a partir de una reserva de unos 64 MiB **con** un separado de
unos 16 MiB. Con reserva de 16 MiB y separado de 16 MiB el coste es de −0,06 ms, es decir
nada.** `PROVEN_DERIVED`

**⇒ `NOT_DETERMINED`: qué es. La atribución era falsa tres veces seguidas —submission, descarga de
L2, traducción de páginas— y lo único que queda es que es un pago único, condicionado por las dos
magnitudes, e independiente del trabajo.** `NOT_DETERMINED`

## 1 · La rejilla de dos ejes, que era el paso que había escrito

**⇒ `MEASUREMENT`: `t = a + b*ITERS` con `ITERS` 512, 2.048 y 8.192, `CONTIGUO`, `STRIDE` 262.144,
65.536 hilos, 5 muestras, entropía verificada en cada corrida.** `MEASUREMENT`

| `a` (ms) | sep 4 MiB | sep 16 MiB | sep 64 MiB | sep 128 MiB |
|---|---|---|---|---|
| **res 16 MiB** | 0,254 | 0,231 | inválido | inválido |
| **res 32 MiB** | 0,282 | **1,189** | inválido | inválido |
| **res 64 MiB** | 0,426 | 6,704 | 6,698 | inválido |
| **res 128 MiB** | 0,375 | 6,885 | 6,628 | 8,358 |

**⇒ `PROVEN_DERIVED`: la superficie es de dos dimensiones con dos umbrales. Por debajo de 16 MiB de
separado el coste es 0,25 a 0,43 ms en toda la columna, y en la fila de 64 a 128 MiB de reserva
todo está en 6,6 a 6,9 salvo la primera celda. La conjunción de los dos umbrales es necesaria y
suficiente.** `PROVEN_DERIVED`

**⇒ `PROVEN_DERIVED`: el punto que había dicho que más discrimina, reserva 32 MiB con separado
16 MiB, da 1,19 ms. Con ello queda `REFUTED` que el coste sea el mínimo de los dos: ahí el mínimo
es 16 MiB, igual que en la celda (16, 16), donde el coste es 0,23 ms.** `PROVEN_DERIVED`

## 2 · Y luego, el mismo número con otra atribución

**⇒ `PROVEN`. Cambiando los hilos con las mismas 4.096 páginas tocadas y la misma reserva de 64 MiB,
el interceptor cambia, y por tanto no es un coste fijo por celda sino la forma de una curva.** `PROVEN`

| `items` | KiB por vuelta | páginas por vuelta | `a` (ms) |
|---|---|---|---|
| 1.024 | 4,0 | 1,00 | 0,143 |
| 4.096 | 16,0 | 4,00 | 0,181 |
| 16.384 | 64,0 | 16,00 | 0,367 |
| 65.536 | 256,0 | 64,00 | **0,561** |

**⇒ `ERROR`: la celda (64, 16) dio 6,704 ms en la rejilla, con `ITERS` de 512 a 8.192, y 0,561 ms
aquí, con `ITERS` de 64 a 512. La misma celda, la misma máquina, y el interceptor depende del
tramo de `ITERS` con el que se ajuste.** `ERROR`

**⇒ `PROVEN_DERIVED`: un interceptor que depende del tramo de ajuste no es un coste. Es la
descripción de una curva que es empinada por debajo de unas 512 vueltas y plana por encima. Y esa
es exactamente la forma de un calentamiento.** `PROVEN_DERIVED`

## 3 · El discriminante que lo cierra

**⇒ `PROVEN`: `--rep=8` repite el envío cronometrado dentro de la misma región. Si el coste fuera por
envío, los ocho costarían lo mismo. Si fuera un pago único, el primero se diferenciaría.** `PROVEN`

| reserva | separado | `ITERS` | envío 1 | envíos 2 a 8 | envío 1 − media | dispersión 2–8 |
|---|---|---|---|---|---|---|
| 64 MiB | 16 MiB | 512 | 9,924 ms | 3,16–3,25 ms | **+6,735** | 2,85% |
| 64 MiB | 16 MiB | 2.048 | 18,944 ms | 12,29–12,42 ms | **+6,599** | 1,07% |
| 64 MiB | 64 MiB | 2.048 | 18,883 ms | 12,38–12,47 ms | **+6,437** | 0,71% |
| 16 MiB | 16 MiB | 2.048 | 12,297 ms | 12,32–12,37 ms | **−0,059** | 0,36% |

**⇒ `PROVEN_DERIVED`: se paga una vez y no por envío, y no depende de `ITERS`. Lo único que
depende de `ITERS` es el trabajo, que es la parte lineal.** `PROVEN_DERIVED`

**⇒ `PROVEN_DERIVED`: y no aparece con reserva de 16 MiB. Los cuatro puntos anteriores están
medidos con la misma máquina, el mismo banco, el mismo kernel y el mismo número de envíos.** `PROVEN_DERIVED`

## 4 · Corrección de las tres notas anteriores

**⇒ `ERROR`, y es el patrón de §68 con la magnitud estable y la interpretación inestable: el número
6,8 ms no se movió desde `606`, y la causa que le puse cambió tres veces.** `ERROR`

```text
  606  lo atribuí a coste de descarga, y lo llamé coste POR ENVIO
  607  lo acoté a "por envío, proporcional a la huella, independiente de ITERS"
  902  lo separé en dos ejes y lo llamé interacción de reserva y separado, por envío
  609  no es por envío: es un pago ÚNICO de 6,4 a 6,7 ms
```

**⇒ `PROVEN_DERIVED`: en los tres casos la magnitud estaba bien y la causa era inventada, y en los
tres casos la causa la escribí sin un discriminante que la separara de las alternativas. Es la
misma forma del error que `606` §5 ya señalaba en `mclk`: una magnitud medida con una causa
elegida.** `PROVEN_DERIVED`

**⇒ `PROVEN_DERIVED`: lo que faltaba era un discriminante de una sola línea y ya existía en el
banco. `--rep` separa «por envío» de «una vez» sin ningún código nuevo: es la misma medición, otra
vez, con el tiempo por unidad de envío.** `PROVEN_DERIVED`

**⇒ `PROVEN_DERIVED`: el error de fondo es que estaba midiendo el interceptor de una recta en vez
de la diferencia entre dos envíos, que es lo que responde a la pregunta. Son dos observables
distintos y usé el que me salía gratis del ajuste.** `PROVEN_DERIVED`

## 5 · Lo que queda, con la cota nueva

**⇒ `NOT_DETERMINED`: el mecanismo. Lo que queda acotado es esto.** `NOT_DETERMINED`

```text
PAGADO UNA VEZ, no por envío
INDEPENDIENTE de ITERS: 6,74 a 512 vueltas y 6,60 a 2.048
INDEPENDIENTE del separado una vez pasado el umbral: 6,60 a 16 MiB y 6,44 a 64 MiB
CONDICIONADO por los dos umbrales: reserva >= ~64 MiB Y separado >= ~16 MiB
AUSENTE con reserva 16 MiB y separado 16 MiB: -0,06 ms
```

**⇒ `PROVEN_DERIVED`: que sea independiente de `ITERS` lo deja fuera de casi todo lo que se
ejecuta por vuelta. Quedan tres cosas que ocurren una vez y dependen del búfer: la traducción de
la dirección base del shader, la construcción del page table de GPUVM para la reserva entera, y
una acción de firmware o de DPM que se dispare por tamaño.** `PROVEN_DERIVED`

**⇒ `PROVEN_DERIVED`: que necesite los dos umbrales a la vez es lo que más acota. Una construcción
de page table depende sólo de la reserva. Una traducción de la dirección base depende sólo de la
reserva. Ninguna de las dos necesita un separado de 16 MiB.** `PROVEN_DERIVED`

**⇒ `NOT_DETERMINED`, y es la frontera viva: la tercera, la que depende de las dos. Un pago único
que exige que la reserva sea grande **y** que el kernel se espalce por una fracción grande de ella
se parece a una invalidación cuyo alcance lo fija el búfer y cuyo coste lo fija lo que se toca. O
se parece a que el driver constructiona la traducción sólo para la parte que el kernel va a
mirar, y paga por adelantado.** `NOT_DETERMINED`

**⇒ `NOT_DETERMINED`: el discriminante siguiente. Los dos umbrales están en números que son
potencias de dos en páginas —32 MiB son 8.192 páginas, 16 MiB son 4.096— y eso vale para ocho
hipótesis a la vez. Lo que los separaría de verdad es mover un umbral sin tocar el otro:
con reserva de 64 MiB, ¿baja el coste si el separado baja de 16 a 15 MiB, o el umbral es de
reserva?** `NOT_DETERMINED`

## 6 · Errores

| # | error | cómo salió |
|---|---|---|
| 1 | la rejilla dio 6,704 ms en (64,16) y 0,561 ms en la misma celda | el interceptor depende del tramo de ajuste |
| 2 | propuesta: que la rejilla `>= 3` era un fallo del instrumento | era el invariante de `SUBRANGE > WSIZE`, correcto |
| 3 | propuesta: que `a` no crece con `items` porque el mecanismo es de páginas | crece, luego no es sólo de páginas |

**⇒ `PROVEN_DERIVED`: el primero es otra vez el mismo error de siempre, y esta vez mío solo: leí
un número de un ajuste y lo tomé por una propiedad del hardware.** `PROVEN_DERIVED`

## 7 · PENDIENTE

```text
606-1 | ESTADO=SATURATED por 905
           | REFUTADO por 905=que el pago siga al RANGO de direcciones. Dos
           |   configuraciones con las mismas 4096 paginas, la misma reserva de 64 MiB
           |   y rangos de 16 y 64 MiB dan 1,905 y 1,905 ms.
           | VIVO=el deficit sigue a las PAGINAS distintas que el kernel toca,
           |   sublineal: 4096 paginas 1,905 ms y 16.384 paginas 4,630 ms
           |   contra 15,6 ms que daria un coste lineal por pagina
           | BLOQUEO=MMIO

606-1-b | ESTADO=RESUELTA por 609 en la atribución
           | REFUTADO=que sea coste por envío. Se paga una vez.
           | MEDIDA=6,4 a 6,7 ms, independiente de ITERS y del separado pasado el umbral
           | CONDICIONADA=reserva >= ~64 MiB Y separado >= ~16 MiB
           | MECANISMO=NOT_DETERMINED

607-1 | ESTADO=OPEN, con la cota de 609
           | PIDE=algo que ocurra una vez y necesite los dos umbrales a la vez
           | SIGUIENTE=mover un umbral sin tocar el otro

902   | ESTADO=CORROBORADA por 609 en la rejilla; su atribución de "por envío" queda
           |          REFUTADA por 609
           | SU_REJILLA_SIRVE=la conjunción de los dos umbrales es necesaria y suficiente

BANCO  | ESTADO=VALIDATED, 9 controles
           | NUEVO=el discriminante de "por envío" contra "una vez": --rep, y comparar el
           |         primer envío con la media de los siguientes
           | LECCION=un interceptor de un ajuste no es un coste. Es la diferencia entre dos
           |         unidades de la magnitud la que responde a las preguntas de atribución.
           | KERNELS=8 · MODELOS=8 · CONSTANTS=6
```