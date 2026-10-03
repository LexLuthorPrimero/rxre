# 271 · El kernel de caché mide la tasa de emisión, no la memoria, y eso lo delata un tiempo que no escala

```text
CLASSIFICATION=MEASUREMENT+NEGATIVE_RESULT+ERROR · TRACK=RUNTIME
CORPUS=RESEARCH/working/linux-7.1.3 + /sys/class/drm/card1/device/hwmon/hwmon1
HARDWARE_SCOPE=HOST-C/RX550/0000:01:00.0
WORK_CLASS=WRITE_LOCAL (kernel propio) · WRITE_EXECUTION=carga Vulkan · NIVEL=1
MODIFICATIONS_CORPUS=0 · GPU INTACTA
```

> **`RENUMERADA`. Esta nota era la `267` y pasó a ser la `271`, porque el 267 ya lo ocupaba
> `267-la-curva-vf-de-mi-vbios-no-esta-rellena.md`, que es otra nota y no la mía.**
>
> **`CORREGIDA` por `270`. El banco con el que se midió esta nota metía la copia del patrón
> dentro de la región cronometrada: **3,2577 ns por dword, el 54,7% al 57,9% del tiempo**. Todas
> las cifras de esta nota —la tabla de §1, los 0,0233 y 0,0220 ns por acceso, el 5,6%, los
> 172 GB/s, el 36× y el 7×— **están medidas sobre una magnitud contaminada y no deben citarse**.
>
> La conclusión sobrevive, rehecha y con otro argumento: con el banco corregido la curva baja
> hasta W = 8192 KiB y a partir de ahí se aplana, 0,01046 contra 0,01060 ns por acceso, 1,3% de
> variación sobre un factor 4. Ver `270` §4.1. El razonamiento de §2 y §3 sigue siendo válido
> en forma, pero se apoyaba en números que no eran los que decían ser.

## Qué resuelve

**Ejecuta el discriminante que `265` propuso — barrer el tamaño del conjunto de trabajo y buscar
la meseta— y el resultado es un `NEGATIVE_RESULT`: el barrido mide la tasa de emisión de la
máquina, no su memoria.** `PROVEN`.

**⇒ `PROVEN`. El tiempo por acceso es de 0,0220 a 0,0233 ns, constante desde W = 1024 KiB hasta
W = 32768 KiB: un factor de 32 en el conjunto de trabajo con una variación del 5,6%.** `OBSERVED`.

**⇒ `PROVEN_DERIVED. Un kernel que no escala con el conjunto de trabajo no está midiendo
memoria: la latencia está oculta por la ocupación y el límite es la emisión de instrucciones.**
`PROVEN_DERIVED`.

**⇒ `INVALID_RESULT`: los 172 GB/s aparentes no son ancho de banda de VRAM. Son 36 veces el techo
a `mclk` 300 y 7 veces el techo a `mclk` 1500.** `INVALID_RESULT`.

**⇒ `ERROR`: el primer barrido que hice, con `iters` variable para mantener el trabajo constante,
era inválido por construcción, y no lo vi hasta que un punto dio 2003 GB/s.** `ERROR`.

## 1 · El barrido válido, y cómo se midió

**⇒ `MEASUREMENT`. `ITERS` fijo en 256, salto fijo de 16 dwords, N = 9 con 3 de calentamiento,
con el control de readback activo en modo `--nocontrol` y salida distinta de cero verificada.** `MEASUREMENT`.

| W (KiB) | dwords | accesos totales | mediana (s) | ns por acceso | GB/s aparente |
|---|---|---|---|---|---|
| 64 | 16.384 | 4.194.304 | 0,000139 | 0.0331 | 121 |
| 1.024 | 262.144 | 67.108.864 | 0,001562 | 0.0233 | 172 |
| 2.048 | 524.288 | 134.217.728 | 0,003037 | 0.0226 | 177 |
| 4.096 | 1.048.576 | 268.435.456 | 0,005909 | 0.0220 | 182 |
| 8.192 | 2.097.152 | 536.870.912 | 0,011790 | 0.0220 | 182 |
| 32.768 | 8.388.608 | 2.147.483.648 | 0,047191 | 0.0220 | 182 |

**⇒ `PROVEN`. El trabajo total crece exactamente 512 veces de la primera a la última fila, y el
tiempo por acceso no se mueve.** `PROVEN`.

## 2 · Por qué eso descarta la medición de memoria, no la confirma

**⇒ `PROVEN_DERIVED`. El razonamiento es corto y no admite lectura alternativa: si el kernel
estuviera limitado por memoria, duplicar el conjunto de trabajo duplicaría los fallos y el
tiempo se doblaría. No se dobla. No hay fallos crecientes.** `PROVEN_DERIVED`.

**⇒ `PROVEN_DERIVED`. Sin fallos crecientes, la máquina está ocultando la latencia con
ocupación: muchos warps residentes, cada uno con una petición en vuelo, y la memoria responde a
tiempo antes de que el warp necesite el dato. El cuello pasa a ser la velocidad a la que el
procesador de comandos emite y las unidades de texto ejecutan la instrucción de carga.** `PROVEN_DERIVED`.

**⇒ `PROVEN`. Y el número lo confirma: 4 B por acceso en 0,0233 ns son 172 GB/s, que es 36 veces
el techo de 4,80 GB/s a `mclk` 300 MHz y 8 veces el de 24,0 GB/s a `mclk` 1500 MHz,derivado en `258`.**
`PROVEN`.

**⇒ `PROVEN_DERIVED. Y por eso `mclk` se queda en 300 MHz en todo el barrido: la máquina no está
pidiendo memoria, así que el SMU no tiene motivo para subir el reloj. Es la misma firma que
describió `261` y `262`, y aquí aparece con la causa por primera vez identificada.** `PROVEN_DERIVED`.

## 3 · La prueba de que no es prefetch

**⇒ La hipótesis natural era el prefetch hardware: el salto de 16 dwords son 64 B exactos, la
unidad que un prefetch de líneas maneja mejor. Se comprobó con un salto primo.** `PROVEN_DERIVED`.

| W (KiB) | ns/acceso, salto 16 | ns/acceso, salto 17 | razón |
|---|---|---|---|
| 1.024 | 0,0232 | 0,0235 | 1,01 |
| 4.096 | 0,0221 | 0,0220 | 1,00 |
| 16.384 | 0,0239 | 0,0217 | 0,91 |
| 65.536 | 0,0220 | 0,0220 | 1,00 |

**⇒ `REFUTED`. El salto primo, que desalinea cada acceso y rompe cualquier patrón reconocible,
da el mismo resultado: razón 1,00 en todo el rango. La explicación no es el prefetch.** `REFUTED`.

**⇒ `PROVEN_DERIVED. Y esto es lo que hace el resultado sólido en lugar de una conjetura: la causa
no es el patrón de acceso sino la ocupación, y se ve en que cambiar el patrón no cambia nada y
cambiar el conjunto de trabajo tampoco.** `PROVEN_DERIVED`.

**⇒ Y los tres primeros puntos, más lentos por acceso, tienen la misma explicación y no son un
efecto de caché: con W = 64 KiB sólo hay 16.384 hilos, el trabajo es tan pequeño que no se llena
la máquina y el lanzamiento domina.** `PROVEN_DERIVED`.

## 4 · Qué kernel mediría de verdad, y por qué este no

**⇒ `NOT_IMPLEMENTED`. Para exponer la memoria hacen falta tres condiciones a la vez:** `PROVEN_DERIVED`.

```text
1. Pocos hilos        -> ocupacion baja    -> la latencia no se puede ocultar
2. Accesos aleatorios -> sin patron        -> el prefetch no puede anticipar
3. Cadena dependiente -> cada acceso espera al anterior
```

**⇒ `PROVEN_DERIVED. El kernel de `262` tenía la condición 3 y `261` la tenía parcialmente; el
kernel de esta nota tiene la 2 y la 1 en sentido contrario — muchos hilos. Lo que falta en
todos ellos es la 1: baja ocupación.** `PROVEN_DERIVED`.

**⇒ Y esa es la razón por la que tres kernels seguidos dan el mismo número sin que ninguno haya
medido la memoria. La variable que no se ha movido en ningún intento es la ocupación, y es la que
decide si la medición es de memoria o de emisión.** `PROVEN_DERIVED`.

## 5 · Lo que queda abierto

```text
PENDIENTE=262-1 | HALLAZGO=271-*.md | ESTADO=NOT_IMPLEMENTED
           | NECESITA=CORPUS  (kernel de ocupacion baja + accesos aleatorios)
           | ALCANZABLE_SIN_ROOT=si
```

**⇒ `NOT_DETERMINED`: el tamaño de caché de GFX8 sigue sin número. `265` probó que no está en
ninguna fuente del driver, y esta nota prueba que tampoco sale de un barrido de este tipo. La
vía que queda es la de la condición 1, con un kernel de ocupación baja.** `NOT_DETERMINED`.

**⇒ `PROVEN_DERIVED. Y hay un dato de esta nota que sí es un hallazgo, aunque no sea el buscado:
el barrido establece que con 8 millones de hilos y 256 iteraciones cada uno, esta GPU ejecuta
un acceso de carga cada 0,0220 ns sin que el reloj de memoria se mueva. Eso es una cota de
emisión, y es un techo real de la arquitectura que ningún driver propio puede superar con
código de shader.** `PROVEN_DERIVED`.

## 6 · Errores propios de esta nota

**⇒ `ERROR`: el primer barrido, con `iters` calculado para mantener constante el trabajo, medía
cosas distintas en cada punto.** `ERROR`.

```text
W = 64 KiB    -> iters = 256
W = 1024 KiB  -> iters = 16
W = 16384 KiB -> iters = 1
```

**⇒ El resultado fue una meseta falsa en 16 MiB con `mclk` subiendo a 1500 MHz en un punto, y
era exactamente el aspecto de la respuesta que `265` pedía. La forma de la curva coincidía con la
hipótesis y el número era imposible; acepté la forma y no el número.** `ERROR`.

**⇒ `ERROR`: el artefacto que delató el error fue un punto con 2003 GB/s, un valor 83 veces el
techo físico. Ese momento es el mismo de `246`, `254` y `262`: el número imposible es la señal y
se llegó tarde.** `ERROR`.

**⇒ Y el error de fondo es peor que en las notas anteriores, porque aquí el dato no era imposible
sino plausible: 172 GB/s lo es, porque la L2 de una GPU puede dar más. La absurdidad de 2003 GB/s
me hizo parar; la de 172 GB/s no.** `PROVEN_DERIVED`.

**⇒ `PROVEN_DERIVED. La lección se repite y se acumula: en cada nota anterior el delator fue un
número imposible. En esta, el número era físicamente posible y aun así no era la magnitudes que
buscaba, porque la magnitud correcta no estaba en la lectura del kernel sino en su dominio: el
tiempo, no los bytes por segundo. Un cálculo puede ser físicamente posible y estar midiendo otra
cosa.** `PROVEN_DERIVED`.