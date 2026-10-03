# 270 · El banco medía la copia PCIe, no el kernel: entre el 55% y el 70% del tiempo

```text
CLASSIFICATION=MEASUREMENT+ERROR+INSTRUMENT_BUG · TRACK=RUNTIME
CORPUS=RESEARCH/working/linux-7.1.3 + /sys/class/drm/card1/device/hwmon/hwmon1
HARDWARE_SCOPE=HOST-C/RX550/0000:01:00.0
WORK_CLASS=WRITE_LOCAL (kernel y banco propios) · WRITE_EXECUTION=carga Vulkan · NIVEL=1
MODIFICATIONS_CORPUS=0 · GPU INTACTA
```

## Qué resuelve

**⇒ El banco de pruebas estaba mal construido: la copia del patrón iba en el mismo command
buffer que el despacho, y la región cronometrada reenvía ese buffer. Medido, no supuesto:
3,2577 ns por dword, es decir 1,228 GB/s de copia host→dispositivo dentro del tiempo que yo
publicaba como si fuera el kernel.** `MEASUREMENT`.

**⇒ `PROVEN`. Esa copia era el 54,7% del tiempo en `271` y el 69,6% del número de `261`.** `PROVEN`.

**⇒ `PROVEN`. El defecto se detectó con un control del propio banco —un kernel nulo que no
lee memoria— y no con una discrepancia entre dos números.** `PROVEN`.

**⇒ `PROVEN`. Corregido, el banco reproduce sus dos controles: configuración correcta sale
0 con 256 de 256 palabras verificadas, configuración incorrecta aborta con 4.** `PROVEN`.

**⇒ `PROVEN`. La corrección aritmética que yo mismo hice —restar la copia al tiempo
publicado— es inválida, y la medición directa lo desmiente: 6304,5 GFLOPS contra los
718,4 que yo anuncié.** `REFUTED`.

## 1 · Cómo se encontró: un kernel que no hace nada

**⇒ `PROVEN_DERIVED. La avería no se detectó comparando números, sino construyendo la
pregunta que el banco no se había hecho: ¿cuánto tiempo mide el banco cuando el kernel no
existe? La respuesta es una recta, no un cero, y esa recta es la contaminación.** `PROVEN_DERIVED`.

```glsl
#version 450
layout(local_size_x = 64) in;
layout(constant_id = 0) const uint ITERS = 1u;
layout(constant_id = 1) const uint STRIDE = 16u;
layout(std430, binding = 0) buffer B { uint d[]; };
void main() {
    uint i = gl_GlobalInvocationID.x;
    uint a = 0u;
    for (uint k = 0u; k < ITERS; k++) a += k * 2654435761u;
    d[i] = a;                       /* una sola escritura: 4 B por hilo */
}
```

| W (KiB) | dwords | tiempo (s) | ns por dword |
|---|---|---|---|
| 64 | 16.384 | 0,000103 | 6,287 |
| 1.024 | 262.144 | 0,000956 | 3,647 |
| 4.096 | 1.048.576 | 0,003644 | 3,475 |
| 16.384 | 4.194.304 | 0,013344 | 3,181 |
| 65.536 | 16.777.216 | 0,055029 | 3,280 |

**⇒ `PROVEN`. El ajuste lineal da 3,2577 ns por dword.** `MEASUREMENT`.

**⇒ `PROVEN_DERIVED. Y esa cifra tiene un nombre: 4 B por dword a 1,228 GB/s.** `PROVEN_DERIVED`.

## 2 · Por qué la copia estaba dentro del reloj

**⇒ `PROVEN_DERIVED. El defecto está en una decisión de diseño del banco, escrita en su propio
código: un único command buffer con la copia y el despacho, y la medición reenvía ese mismo
buffer para que la perturbación se acumule.** `PROVEN_DERIVED`.

```c
    VkCommandBufferBeginInfo cbbi = { ... };
    CHECK(vkBeginCommandBuffer(cmd, &cbbi), "vkBeginCommandBuffer");
    VkBufferCopy init = { .srcOffset = 0, .dstOffset = 0, .size = bytes };
    vkCmdCopyBuffer(cmd, sbuf, buf, 1, &init);   /* patron -> dispositivo */
    vkCmdBindPipeline(cmd, VK_PIPELINE_BIND_POINT_COMPUTE, pipe);
    vkCmdDispatch(cmd, items / grp, 1, 1);
```

**⇒ `PROVEN_DERIVED. Y hay un agravante: la copia escala con `items`, y `items` es exactamente
la variable que se barre para medir. La contaminación no es un ruido de fondo con el que se
pueda convivir: tiene la misma dependencia funcional que el tamaño de la carga, de modo que
produce exactamente la forma de curva que uno busca.** `PROVEN_DERIVED`.

## 3 · La corrección y su verificación

**⇒ `PROVEN`. Dos command buffers en lugar de uno: la copia sola en el suyo, el despacho solo
en el suyo, y la copia enviada antes de arrancar el reloj y fuera de él.** `PROVEN`.

**⇒ `MEASUREMENT`. Verificación con el mismo kernel nulo: la pendiente pasa de 3,2577 a
0,3432 ns por dword, una reducción de 9,5 veces.** `MEASUREMENT`.

| W (KiB) | dwords | antes (s) | ahora (s) | ns por dword ahora |
|---|---|---|---|---|
| 64 | 16.384 | 0,000097 | 0,000044 | 2,686 |
| 1.024 | 262.144 | 0,000954 | 0,000193 | 0,736 |
| 16.384 | 4.194.304 | 0,013422 | 0,001114 | 0,266 |
| 65.536 | 16.777.216 | 0,054935 | 0,006155 | 0,367 |

**⇒ `PROVEN_DERIVED. El residuo de 0,3432 ns por dword no es contaminación: escala con `items` y
el kernel nulo escribe 4 B por hilo, así que es tráfico real del kernel. Se distingue de la
contaminación en que ésa estaba en el reloj y éste se cronometra.** `PROVEN_DERIVED`.

**⇒ `MEASUREMENT`. Los dos controles siguen distinguiendo, que es lo único que hace válido un
banco: `probe.spv` sale 0 con 256 de 256 verificadas; `alu.spv` con la misma configuración
aborta con 4 y muestra las tres primeras discrepancias.** `MEASUREMENT`.

## 4 · Lo que obliga a corregir

### En `271`

**⇒ `PROVEN`. El 54,7% del tiempo medido en W = 1024 KiB y el 57,9% en W = 32768 KiB eran la
copia.** `PROVEN`.

**⇒ `PROVEN_DERIVED. Y esto invalida la prueba central de `271` tal como está escrita. La
planitud que interpreté como «la latencia está oculta por la ocupación» se calculó sobre una
magnitud contaminada, y la copia produce aplanamiento por la misma razón que produce el
kernel: ambas escalan linealmente con `items`.** `PROVEN_DERIVED`.

**⇒ `PROVEN_DERIVED. La conclusión de `271` sobrevive, pero rehecha y con otro argumento. Con
el banco correcto la curva baja hasta W = 8192 KiB y a partir de ahí se aplana: 0,01046 ns por
acceso en 8192 KiB contra 0,01060 en 32768 KiB, una variación del 1,3% sobre un factor 4 en el
conjunto de trabajo.** `PROVEN_DERIVED`.

**⇒ `PROVEN_DERIVED. Y el aplanamiento ahora tiene una explicación que la medición sostiene: por
debajo de 8 MiB el tiempo por acceso BAJA al crecer el conjunto de trabajo, que es la firma de
amortizar el coste fijo del lanzamiento; por encima ya no baja ni sube. No es un codo de caché:
un codo de caché subiría.** `PROVEN_DERIVED`.

**⇒ `ERROR`: los números publicados en `271` —0,0233 y 0,0220 ns por acceso, 5,6% de variación,
172 GB/s— quedan sustituidos por 0,01243, 0,01046 y 0,01060 con 1,3% de variación en la meseta.
La tabla de `271` está desactualizada y no debe citarse.** `ERROR`.

### En `261`

**⇒ `PROVEN`. Su configuración se resuelve exactamente: 137,44 GFLOP son `items = 2²⁷ = 134.217.728`
con `iters = 64` y `nacc = 8`, porque 134.217.728 × 64 × 8 × 2 = 137.438.953.472.** `PROVEN`.

**⇒ `PROVEN`. La copia eran 0,43724 s de los 0,62855 s publicados: el 69,6%.** `PROVEN`.

**⇒ `MEASUREMENT`. Re-medido con el banco correcto, ese mismo kernel da 0,02180 s, o sea
6304,5 GFLOPS.** `MEASUREMENT`.

**⇒ `PROVEN`. 6304,5 GFLOPS es imposible aunque no se sepa el número de CUs, que sigue
`NOT_DETERMINED` por la contradicción de `cg_mask` de `261`. A `sclk` de 1063,02 MHz medido en
`hwmon1`, incluso con 16 CUs —más de los que lleva un chip de este encapsulado— el techo sería
2177 GFLOPS, y 6304,5 es 2,9 veces ese techo.** `PROVEN`.

**⇒ `PROVEN_DERIVED. Así que la conclusión de `261` —`INVALID_RESULT`, las 218,7 GFLOPS no son
una medida de rendimiento— sobrevive, pero la causa quexiety enunciada no es la buena. No es que
mida latencia: es que el bucle está siendo eliminado. Un kernel cuyo resultado no depende del
número de iteraciones no es un kernel de cómputo.** `PROVEN_DERIVED`.

## 5 · Dato colateral que sí es un hallazgo

**⇒ `PROVEN. La copia host→dispositivo mide 1,228 GB/s, que es el 61% del techo de 2,000 GB/s
de PCIe Gen2 x4 derivado en `258`.** `PROVEN`.

**⇒ `PROVEN_DERIVED. Es una confirmación independiente de la frontera de `258` por una vía
completamente distinta: no se leyó de `/sys`, no se usó `sclk` ni `mclk`, se dedujo del tiempo
de una copia de staging. Y sale por debajo del techo, que es lo que corresponde a una copia
host→dispositivo real con buffer deunión por escritura.** `PROVEN_DERIVED`.

## 6 · Mis errores de esta tanda

**⇒ `ERROR`: publiqué `271` con una prueba construida sobre la magnitud contaminada. El
razonamiento era válido en forma —«si fuera memory-bound, el tiempo escalaría»— pero el número
que lo alimentaba no era el que decía ser.** `ERROR`.

**⇒ `ERROR`: anuncié 718,4 GFLOPS como resultado plausible de restar la copia al tiempo de
`261`. Fue un número obtenido mentalmente por diferencia, no medido, y la medición directa dio
6304,5.** `ERROR`.

**⇒ `PROVEN_DERIVED. El error de fondo es el mismo que en `246`, `254`, `262` y `271`, y esta
vez con una forma nueva: restar dos tiempos medidos en contextos distintos no produce una
medición, produce una resta. Que un número salga razonable no lo valida; sólo lo valida volver a
medirlo.** `PROVEN_DERIVED`.

**⇒ `PROVEN_DERIVED. Y hay una diferencia con los errores anteriores que conviene registrar:
aquí el defecto no estaba en el razonamiento sino en el instrumento, y ningún razonamiento lo
habría detectado. Un argumento correcto sobre una magnitud mal medida no es un dato, y la
diferencia entre las dos cosas no se ve en la prosa sino en el banco.** `PROVEN_DERIVED`.

## 7 · Lo que queda abierto

```text
PENDIENTE=262-1 | HALLAZGO=270-*.md | ESTADO=NOT_IMPLEMENTED
           | NECESITA=CORPUS  (kernel de ocupacion baja + accesos aleatorios)
           | ALCANZABLE_SIN_ROOT=si
```

**⇒ `NOT_IMPLEMENTED`. El kernel de `262` sigue sin construirse, y ahora tiene una razón más
para construirse: la plataforma de medición está recién arreglada, y medir sobre el banco
contaminado habría producido otro número sin valor.** `NOT_IMPLEMENTED`.

**⇒ `PROVEN_DERIVED. Y hay una consecuencia de alcance que no es un pendiente sino un
requirement: `261` y `271` son las dos notas que sostenían resultados de rendimiento, y las dos
tenían el mismo defecto. Cualquier cifra de rendimiento publicada antes de esta nota que venga
de este banco debe leerse como cota superior, no como medida.** `PROVEN_DERIVED`.
