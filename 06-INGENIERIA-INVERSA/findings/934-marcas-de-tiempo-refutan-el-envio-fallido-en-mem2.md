# 934 — Marcas de tiempo de la GPU: `--mem=2` no es un envío fallido, es memoria invisible
> ## CORRECCION por `938` — leer esto antes que nada de esta nota
>
> **Lo que queda ANULADO:** la sección «Cierre del pendiente» afirmaba que en tiempo de GPU las dos
> ramas de `textura` estaban a 0,9% y en tiempo de host a 26%, y que eso sugería que la magnitud de
> GPU separa mejor. **Ese 0,9% no significa nada.** La línea `GPU` que el banco imprimía se leía
> **una sola vez, tras la calibración**, y `bench.py` la emparejaba con la mediana de host de las
> repeticiones: dos números que no describen el mismo trabajo. Corregido en `938`, donde la marca
> va en la línea de su propia medición.
>
> **Lo que sigue en pie, y es la parte que justifica este instrumento:** el `REFUTED` del envío
> fallido en `--mem=2`. Ese resultado no dependía de la escala de la magnitud, sino de que la marca
> hubiera voltado o no, y `--mem=2` dio 27,4 µs de trabajo frente a los 34,6 µs de `--mem=0`, con la sonda
> constante coincidio en 4,32 µs en los dos modos. Sigue en pie.
>
> **Lo que hay que rehacer:** la elección de magnitud para `§H`, con el emparejamiento ya correcto.
> No está hecha.


Estado: un `REFUTED` y un `PROVEN` nuevo. Cierra el punto que `933` dejó abierto sobre `--mem=2`.
Alcance: la RX 550 de esta placa, Polaris12/GFX8.1, RADV, Mesa de este equipo.
AUTORIA=AGENTE-SMU
Instrumentos: `vulkan_compute_probe.c` con `--tex` y con marcas de tiempo; `bench.py` 15 de 15.

## Qué se quería

`933` dejo tres candidatos para por qué `--mem=2` devuelve el buffer intacto, y uno de ellos era
**que el envío fallara de forma silenciosa**. Ese candidato era el más barato de cerrar y el más
grave, porque si fuera cierto, todo lo demás que el banco ha medido con esa misma ruta estaría
sospechoso.

La forma de cerrarlo no es mirar el buffer: es preguntar a la GPU **cuánto tiempo estuvo
ejecutando**. Un command buffer descartado no escribe marcas.

## Lo que se añadió

Un pool de consultas de tipo `VK_QUERY_TYPE_TIMESTAMP` con dos marcas: una al principio del command
buffer del despacho y otra al final. Más la lectura de vuelta con `vkGetQueryPoolResults`.

La capacidad se **consulta y se declara**, no se asume:

```
COLA      familias=3 elegida=0 flags=0x0000000f
TIMESTAMP timestampValidBits=64 timestampPeriod=40.000 ns  utilizable
GPU      intervalo_marcas=0.036480 ms  pool=presente  qrc=0  qv=[32342852459,32342853371]
```

En esta placa hay marcas y son utilizables. Si `timestampValidBits` fuera 0, el banco lo dice y
sigue funcionando: una capacidad ausente no puede ser un `ABORTO` en un banco que ya tiene trabajo.

## El resultado que refuta un candidato

```
--mem=0   34,56 us de GPU
--mem=1   35,04 us de GPU
--mem=2   27,36 us de GPU      <-- el despacho SE EJECUTA
```

Y con una sonda que escribe una constante y no depende de la memoria:

```
--mem=0    4,32 us de GPU
--mem=2    4,32 us de GPU      <-- identico
```

**El envío no falla. La GPU ejecuta el kernel sobre el BAR.** El candidato queda `REFUTADO` por
medición directa, y con él cae la sospecha sobre todo lo demás que el banco midió por esa ruta.

Lo que queda, reformulado: **el BAR es direccionable y ejecutable por la GPU, pero su contenido no es
visible en ninguna de las dos direcciones.** Ni la copia de host a dispositivo entra, ni lo que la
GPU escribe sale. El `0xdeadbeef` de `933` es el estado inicial de esa memoria y se queda ahí.

Los candidatos que quedan son coherentes entre sí y todos apuntan a lo mismo: **falta coherencia de
caché entre el host y la apertura del BAR**. La copia escribe por una vía que la GPU no lee, y la GPU
escribe por una vía que el host no lee. Eso es lo que se espera de una apertura que no pasa por el
mismo dominio de coherencia que la memoria del sistema.

Eso es `NOT_DETERMINED`, y la via para cerrarlo no es otro flag de Vulkan: es comprobar si la
escritura del host es visible para la GPU por un camino que no sea una copia. Con `--mem=2` eso no
ocurre, y por eso el contenido que la GPU produce no se ve al releer.

**Consecuencia para el proyecto, y es una consecuencia dura: un driver propio no puede contar con el
BAR como espacio de trabajo en esta placa con este driver.** No es lento, no es degradado: es un
espacio donde se puede ejecutar y del que no se puede leer nada.

## Un número que sale de paso y que es de `§H`

El caso conocido, `--mem=0` con la cadena:

```
tiempo de host   72 us
tiempo de GPU    36,48 us
```

**La mitad del tiempo medido por el host no es trabajo de la GPU.** Eso no es una precisión del
cronómetro: es envío. Y es exactamente el discriminante que `§H` necesita para separar
envío-limitado de GPU-limitado, y que hasta ahora no tenía: `bench.py` mide tiempo de host y lo
reportaba como si fuera tiempo de GPU.

La línea `GPU` es la que hay que mirar para el trabajo real de §H, y la que hay que mirar para saber
si un descenso de 5 µs es trabajo o es cola.

## Dos defectos del banco que aparecieron al hacerlo

**Las propiedades de la familia de cola nunca se leían.** La llamada era

```c
uint32_t qf = 0; vkGetPhysicalDeviceQueueFamilyProperties(gpu, &qf, NULL);
```

que pasa el **puntero donde la función espera el contador**, y `NULL` donde espera el puntero a
propiedades. Escribía en `qf` el número de familias y no leía ninguna. El banco usaba la familia 0 a
ciegas y le salía bien porque este dispositivo tiene una familia que sirve. En cuanto había que
*preguntarle* algo a la familia, había que leerla de verdad. Ahora se lee, se busca una familia con
`GRAPHICS` y `COMPUTE`, y se eligen explícitamente. Resultado: **3 familias**, no 1.

**Mi reserva de la línea `GPU` era un bug, no una ausencia.** Escribí
`gpu_ms >= 0.0 ? "%.6f" : "no disponible"` como argumento de un `%s`. Cuando el valor faltaba, la
línea imprimía literalmente `%.6f`, y cuando estaba bien, imprimía el número. Es decir: **el fallo se
presentaba con el aspecto del éxito.** La primera vez que lo vi pensé que las marcas no volvían, y
si no hubiera seguido mirando, habría registrado «las marcas no funcionan en esta placa» como hecho.

La leccion es la misma de siempre y conviene no adornarla: un instrumento que en su modo de fallo
imprime algo con forma de dato es peor que uno que falla en silencio, porque el silencio se nota.

## Cierre del pendiente: `bench.py` ya reporta los dos tiempos

`correr()` acepta ahora un dict de salida que se rellena con la marca de GPU, y hay un
`medir_con_gpu()` que devuelve ambas series, descartando por igual las muestras que no pasan el
control de contenido. Se eligió un parámetro de salida y no ampliar la tupla devuelta porque las
cuatro suites ya validadas desempaquetan cuatro elementos, y **el camino de medición de todo lo demás
no se toca por añadir una observación.**

La primera corrida de la suite `textura` con las dos magnitudes:

| | host (mediana) | sigma host | GPU (mediana) | GPU/host |
|---|---|---|---|---|
| storage buffer | 129 µs | 21 µs | 92,32 µs | 71,6 % |
| imagen r32ui | 162 µs | 20 µs | 93,12 µs | 57,5 % |

**El veredicto no cambió y no tenía que cambiar:** sigue siendo `separación insuficiente`, porque la
decisión se sigue tomando sobre el tiempo de host, que es lo que se decidió antes. Cambiar la
magnitud sobre la que se decide en la misma iteración en que se introduce la magnitud haría imposible
saber cuál de las dos dio el resultado. Esa magnitud se decide despues, con datos.

Pero los números dejan una observación que no estaba prevista, y es la razón por la que vale la pena
haberlo hecho: **en tiempo de GPU las dos ramas están a 0,9 % (92,32 contra 93,12 µs), y en tiempo de
host están a 26 %.** La diferencia de host es casi toda envío.

Eso no es un resultado sobre la ruta de texel, y no se reporta como tal. Es una pista sobre **cuál
magnitud es la buena para `§H`**: la de GPU separa workloads mejor que la de host, porque el host
arrastra una varianza de envío que no es trabajo. Confirmarlo exige repetir el par con las dos
magnitudes y suficientes muestras para que la comparación sea significativa, y eso es una iteración
propia.

## Instrumentos

- `vulkan_compute_probe.c`: `--tex`, marcas de tiempo, lectura de la familia de cola con selección
  explícita. Con la bandera y las marcas apagadas, el comportamiento es el de antes.
- `bench.py` 15 de 15, puerta de frescura del binario activa.
- La línea `GPU` es nueva en la salida del banco, y `bench.py` ya la consume. El runner sigue
  decidiendo con el tiempo de host, a proposito.

## Lo que queda abierto

- **Que `bench.py` reporte el tiempo de GPU junto al de host**, y que el contrato de medición diga
  cuál de los dos se está comparando. Es lo que separa envío-limitado de GPU-limitado, y ahora hay
  instrumento para ello.
- **`--mem=2`**: por qué la memoria del BAR no es visible en ninguna dirección. Candidatos:
  coherencia de caché, o el driver asignando una apertura que no es la que cree. No hay más
  discriminantes baratos desde Vulkan; el siguiente sería comprobar la coherencia con una escritura
  del host leída por la GPU sin copia, que es el mismo kernel con `--mem=2` y sin `vkCmdCopyBuffer`.
- ~~**`282-2`**~~ **RANCIOSO**: cerrado en `283` (dos regiones disjuntas, 0/40 → 40/40).
- **El chequeo «no nulos»** sigue aceptando `0xdeadbeef`, que es como se descubrió lo de `--mem=2`.
  Con las marcas de tiempo hay una forma mejor de comprobarlo: si hay intervalo de GPU y el buffer no
  cambió, no es un kernel que calcula mal.
