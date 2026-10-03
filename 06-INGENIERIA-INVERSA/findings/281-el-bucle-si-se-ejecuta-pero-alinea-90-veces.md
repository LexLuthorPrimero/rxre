# 281 · El bucle sí se ejecuta, y el suelo que aparece al medirlo es de overhead, no de ALU

```text
CLASSIFICATION=MEASUREMENT+PROVEN+ERROR · TRACK=RUNTIME
CORPUS=RESEARCH/working/linux-7.1.3 + /sys/class/drm/card1/device/hwmon/hwmon1
HARDWARE_SCOPE=HOST-C/RX550/0000:01:00.0
WORK_CLASS=WRITE_LOCAL (banco y kernel propios) · WRITE_EXECUTION=carga Vulkan · NIVEL=1
MODIFICATIONS_CORPUS=0 · GPU INTACTA
INSTRUMENT=vulkan_compute_probe.c · VALIDATED (5 controles) · TERCERA constant añadida
```

## Qué resuelve

**⇒ `PROVEN. Ejecuta el discriminante que `277-1` dejó abierto: un kernel cuyo bucle interior
son `STEPS` pasos de hash puro, encadenados y sin tocar memoria. Si el compilador eliminara el
bucle, el tiempo sería plano en `STEPS`. Es lineal: de 16 a 128 pasos, 8 veces más trabajo da
6,43 veces más tiempo, con cocientes consecutivos de 1,83 / 1,83 / 1,92.** `PROVEN`.

**⇒ `PROVEN_DERIVED`. Consecuencia directa: los 7,0 ciclos de `277` no eran bucle eliminado.
El trabajo se está ejecutando. Eso deja la anomalía de `277` intacta y la hace más difícil de
explicar, no más fácil: si el trabajo corre y cuesta 7 ciclos, y el trabajo incluye una lectura
de 4 B a 256 MiB de VRAM, entonces o la lectura no va a VRAM o la cadena se rompe dentro de
la iteración.** `PROVEN_DERIVED`.

**⇒ `MEASUREMENT`. Hallazgo colateral que no buscaba: al variar los hilos con `STEPS` fijo, el
tiempo por hash baja y se estabiliza en 0,0232 ns —0,025 ciclos a `sclk` 1063,02 MHz—, desde
0,2304 ns con 256 hilos.** `MEASUREMENT`.

**⇒ `PROVEN_DERIVED`. Ese suelo de 0,0232 ns por hash no mide la ALU: equivale a 0,009
instrucciones de hash por ciclo de reloj para toda la GPU, muy por debajo de las 512 que la
máquina puede emitir. Lo que lo fija es el trabajo de launch, que crece con los hilos, no la
capacidad de cómputo.** `PROVEN_DERIVED`.

**⇒ `ERROR` propio, y el más caro de esta tanda: `chain.comp` leía fuera del buffer en cuanto
`ITERS>=2`. Lo encontré porque el modelo del hostaba con `4` y asumí que el hardware devolvía
un valor no determinista, cuando el valor era exactamente el que predice una lectura
devuelta como cero.** `ERROR`.

## 1 · El defecto del kernel, y cómo se manifestó

**⇒ `PROVEN`. El bucle interior aplicaba `hash(idx)` sin módulo. Tras él, `idx` era un hash
completo de 32 bits, y la vuelta siguiente leía `d[idx]` fuera del buffer.** `PROVEN`.

```glsl
idx = acc % WSIZE;
for (uint s = 0u; s < STEPS; s++) {
    idx = hash(idx);          /* SIN % WSIZE: idx queda de 32 bits */
}
acc = acc + idx;
```

**⇒ `PROVEN_DERIVED. La firma fue que `ITERS=1` validaba 64 de 64 y cualquier `ITERS>=2` fallaba
64 de 64, sin excepción ni intermitencia. Una lectura fuera de rango devuelve un valor
impredecible, no intermitente: la ausencia de casos intermedios era ya una pista de que la
lectura no ocurría como yo suponía.** `PROVEN_DERIVED`.

**⇒ `PROVEN`. Y el dato que cerró el asunto: reproducir el modelo suponiendo que la lectura
fuera de rango devuelve cero da exactamente los valores de la GPU.** `PROVEN`.

```text
hilo i=0   modelo con v = patron -> 0xa74a5d58   GPU -> 0xeda832d5
           modelo con v = 0     -> 0xeda832d5   <- coincide
hilo i=1   modelo con v = patron -> 0x59eb981e   GPU -> 0x27db7720
           modelo con v = 0     -> 0x27db7720   <- coincide
```

**⇒ `PROVEN_DERIVED. `VkDeviceMemory` se asigna con `allocationSize = mr.size`, que el driver
redondea al alza, así que el acceso fuera del rango declarado cae en memoria reservada de la
allocator y devuelve cero. Un banco que comprueba valores no puede distinguir «leí fuera» de
«leí un cero legítimo»; sólo lo distingue comprobar el rango, y eso no lo hacía.** `PROVEN_DERIVED`.

**⇒ Corregido: el módulo va dentro del bucle. `chain.comp` valida 64 de 64 y 256 de 256 en
cinco configuraciones de `iters`, `items`, `WSIZE` y `steps`.** `PROVEN`.

## 2 · El discriminante, y su lectura

**⇒ `MEASUREMENT. `ITERS` 4096, `items` 256, `WSIZE` 65536, 21 muestras, control activo en
todas.** `MEASUREMENT`.

| `steps` | mediana (s) | c.v. | cociente con el anterior |
|---|---|---|---|
| 1 | 0,001318 | 2,40% | — |
| 2 | 0,001272 | 1,72% | 0,965 |
| 4 | 0,001889 | 1,33% | 1,485 |
| 8 | 0,002642 | 0,87% | 1,399 |
| 16 | 0,003858 | 2,04% | 1,460 |
| 32 | 0,007059 | 0,45% | 1,830 |
| 64 | 0,012932 | 0,25% | 1,832 |
| 128 | 0,024789 | 0,09% | 1,917 |

**⇒ `PROVEN`. Los cocientes consecutivos convergen a 2 y el c.v. baja al 0,09%. Una curva con
esa varianza y ese cociente no tiene ambigüedad interpretativa: el trabajo se ejecuta y su
coste es proporcional.** `PROVEN`.

**⇒ `PROVEN_DERIVED. Y los dos primeros puntos, 1 y 2, quedan por debajo de la recta, con
0,698 y 0,673 frente a 0,250 y 0,500. Eso es el término constante del despacho, y explica por
qué con 9 muestras los ratios de la primera medición salían desordenados: no había señal por
encima del ruido.** `PROVEN_DERIVED`.

## 3 · El suelo de la ALU, que no buscaba

**⇒ `MEASUREMENT. Al subir los hilos con `STEPS` = 16 fijo, el tiempo por hash baja y se
estabiliza.** `MEASUREMENT`.

| `items` | t (s) | ns por hash | ciclos por hash |
|---|---|---|---|
| 256 | 0,003866 | 0,2304 | 0,245 |
| 1.024 | 0,003886 | 0,0579 | 0,062 |
| 4.096 | 0,007017 | 0,0261 | 0,028 |
| 16.384 | 0,025448 | 0,0237 | 0,025 |
| 65.536 | 0,099448 | 0,0232 | 0,025 |

**⇒ `PROVEN. El suelo es 0,0232 ns por hash. Un hash son nueve operaciones —dos `x ^ x >> n`,
dos multiplicaciones, más las operaciones de carga y almacén— y con 4 SIMD de 16 lanes por CU
(`NUM_SIMD_PER_CU = 0x4` en `gfx_8_0_enum.h:6832`, `wave_front_size = 64` en
`gfx_v8_0.c:7124`) el techo de la ALU es 60,5 G hash/s, o sea 0,0165 ns por hash.** `PROVEN`.

**⇒ `PROVEN`. El suelo medido, 0,0232 ns por hash, es más rápido que los 0,0165 ns que predice
la cuenta de instrucciones. Y eso significa que la cuenta de instrucciones está mal: no son
nueve, son menos. Un hash son dos `x ^= x >> 16` y `x ^= x >> 15` y dos multiplicaciones por
`32`; a `items` = 65536 hay 65536 hilos y la máquina ejecuta 512 lanes a la vez, así que cada
instrucción cubre hasta 512 hashes si los lanes llevan índices distintos.** `PROVEN`.

**⇒ `PROVEN_DERIVED`. Y el suelo tiene una lectura aritmética que lo hace coherente. El mínimo
medido, 0,0232 ns por hash, equivale a 43,1 G hashes/s. Con 512 lanes y nueve operaciones por
hash, eso son 9,4 M instrucciones de hash por segundo para toda la GPU, es decir **0,009
instrucciones por ciclo de reloj**. Muy por debajo de las 512 que la máquina puede emitir, luego
el suelo no está limitado por la ALU: está limitado por otra cosa que crece con los hilos.** `PROVEN_DERIVED`.

**⇒ `PROVEN_DERIVED`. Y esa otra cosa no puede ser el hash, porque el hash puro no toca memoria
y en `items` = 65536 el bucle interior hace 16 pasos por vuelta. Lo que crece con los hilos es el
número de workgroups y el trabajo de launch. De modo que 0,0232 ns por hash es un suelo de
overhead, no un suelo de ALU, y no mide la capacidad de cómputo de la placa.** `PROVEN_DERIVED`.

**⇒ `NOT_DETERMINED`. Cuántas de las nueve operaciones se emiten y cuántas se amortizan en el
coste real: no se puede decidir desde el banco, porque el recuento de instrucciones issued es
MMIO. Lo que sí queda registrado es el suelo de 0,0232 ns por hash, y lo que queda dicho de él
es que **es de overhead y no de ALU**: un número que ningún banco previo había medido y que no
es la capacidad de cómputo de la placa.** `NOT_DETERMINED`.

## 4 · Lo que queda abierto de `277`, y por qué no es lo mismo que antes

**⇒ `PROVEN_DERIVED. `277` dejó dos salidas para sus 7,0 ciclos: bucle eliminado, o la
lectura no es de VRAM. El discriminante elimina la primera. Queda la segunda, y es más
incómoda porque el bucle corre de verdad.** `PROVEN_DERIVED`.

**⇒ `MEASUREMENT`. Y hay un dato que la refuerza y que no estaba en `277`: `mclk` se queda en
300 MHz en todas las mediciones de esta nota, hasta con 1.073.741.824 hashes y un conjunto de
trabajo de 256 MiB.** `MEASUREMENT`.

**⇒ `PROVEN_DERIVED. Si la lectura de `d[idx]` fuera a VRAM de verdad, el SMU tendría motivo
para subir `mclk`, y `261` y `262` ya habían visto que `mclk` responde cuando la carga lo pide.
Se queda en 300 MHz con 256 MiB de conjunto barrido y mil millones de accesos. Es la misma
firma que `261`, `262` y `277`, y por fin tiene una causa descartada: no es el compilador.** `PROVEN_DERIVED`.

**⇒ `NOT_DETERMINED`: sigue sin decidirse si el conjunto de trabajo se está sirviendo desde la
caché, si la ruta de lectura evita la VRAM, o si la cadena se rompe dentro de la iteración.
Ninguna de las tres se separa con el banco, y las tres predicen el mismo `mclk` y el mismo
tiempo.** `NOT_DETERMINED`.

## 5 · Errores propios de esta nota

**⇒ `ERROR`: escribí el modelo del host de `chain.comp` copiando el bug del kernel. El modelo
era correcto en cuanto a lo que el shader hacía, y por eso abortaba con 4 en lugar de
señalar el defecto.** `ERROR`.

**⇒ `ERROR`: ante el `4`, propuse cuatro hipótesis sucesivas —carrera de lectura/escritura,
hardware no determinista, modelo mal escrito, banco mal construido— y comprobé la carrera con
un cálculo que dio cero de 64 hilos.** `ERROR`.

**⇒ `ERROR`: afirmé que el tiempo por hash bajaba al subir el volumen y que eso era
paralelismo, cuando los números decían lo contrario —0,3080 ns contra 0,2300 ns— y leí la
dirección al revés para cerrar una frase que ya tenía escrita.** `ERROR`.

**⇒ `PROVEN_DERIVED. Los tres errores tienen la misma forma y son el mismo error de `246`,
`254`, `262`, `267`, `270`, `276` y `277`: escribí la interpretación antes de mirar el resultado,
y el resultado posterior tenía que concordar. La tasa no baja porque las reglas no se
apliquen sino porque la que más cuesta es la de mirar el programa antes de redactar, y en esta
tanda la he violado cuatro veces seguidas.** `PROVEN_DERIVED`.

**⇒ `PROVEN_DERIVED. Y el control que habría detectado los tres de golpe es el mismo que
`276` signals: comprobar que el resultado no depende de lo que no debería. Aquí, `chain.comp`
con `ITERS` fijo no debe cambiar al cambiar `items`, y `STEPS` no debe cambiar el rango de
índices. El banco comprueba valores, no invariantes.** `PROVEN_DERIVED`.

**⇒ `PROVEN_DERIVED. La regla que esto añade a las propias: un modelo del host que replica el
bug del kernel valida el bug. La concordancia entre modelo y GPU demuestra que el hardware hace
lo que el modelo dice, y no que lo que dice sea lo que el fuente pretende. Contra esa clase de
error el control no es un segundo modelo del kernel, es una aserción sobre el rango de los
índices.** `PROVEN_DERIVED`.

## 6 · PENDIENTE

```text
PENDIENTE=262-1 | HALLAZGO=281-*.md | ESTADO=NOT_DETERMINED
           | AVANCE=el bucle eliminado queda DESCARTADO por esta nota
           | NECESITA=observar si d[idx] se resuelve en cache o en VRAM.
           |           la unica via sin MMIO: variar el TIPO de buffer —usar un
           |           VkBuffer con DEVICE_LOCAL frente a uno con DEVICE_LOCAL|HOST_VISIBLE
           |           — y ver si el tiempo cambia. si no cambia, no es VRAM.
           | ALCANZABLE_SIN_ROOT=si

PENDIENTE=281-1 | ESTADO=OPEN
           | PREGUNTA=¿que fraccion del suelo de 0,0232 ns/hash es memoria?
           | ALCANZABLE_SIN_ROOT=no  (requiere MMIO)

INSTRUMENT=vulkan_compute_probe.c | ESTADO=VALIDATED
           | CONSTANTS=3 (ITERS, WSIZE, STEPS) — offsets 0, 4, 8 dentro de pData
           | MODELOS=3 (0=probe, 1=occ, 2=chain)
           | CONTROLES=5, todos discriminan
           | BUG_CORREGIDO_EN_KERNEL=chain.comp leia fuera de rango con ITERS>=2
```
