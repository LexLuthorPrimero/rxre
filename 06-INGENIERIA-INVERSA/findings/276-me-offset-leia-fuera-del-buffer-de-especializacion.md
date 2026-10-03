# 276 · La segunda specialization constant nunca llegó al shader, y el banco reportaba el resultado del optimizador como si fuera el kernel

```text
CLASSIFICATION=INSTRUMENT_BUG+MEASUREMENT+ERROR · TRACK=TOOLING + RUNTIME
CORPUS=RESEARCH/working/linux-7.1.3 + Vulkan 1.1 (especificación de VkSpecializationMapEntry)
HARDWARE_SCOPE=HOST-C/RX550/0000:01:00.0
WORK_CLASS=WRITE_LOCAL (banco y kernels propios) · WRITE_EXECUTION=carga Vulkan · NIVEL=1
MODIFICATIONS_CORPUS=0 · GPU INTACTA
```

## Qué resuelve

**⇒ `PROVEN`. El banco tenía un `VkSpecializationMapEntry` con `offset` = 12 sobre un buffer de
datos de 8 bytes: leía 4 bytes fuera. Consecuencia medida: **la segunda specialization
constant de todo kernel que la declarara no llegaba al shader**, y el valor efectivo era el
default del GLSL.** `PROVEN`.

**⇒ `MEASUREMENT`. El discriminante que lo prueba no es el código, es el tiempo: con el banco
roto, `cache.comp` da el mismo tiempo con `iters=1` que con `iters=256` — su bucle no
cambiaba. Con el banco arreglado escala 5,46×.** `MEASUREMENT`.

**⇒ `PROVEN_DERIVED`. El alcance: todas las cifras de `261`, `270` y `271` salieron de un banco
que no ejecutaba el kernel que su `CONFIG` declaraba. La segunda constant de `cache.comp`
—`STRIDE`— era 16 por defecto, y 16 era justo lo que yo pasaba, así que el defecto quedaba
invisible en la única variable que barría.** `PROVEN_DERIVED`.

**⇒ `PROVEN`. Corregido, `occ.comp` —el kernel de ocupación baja de `271`— valida contra un
modelo del host independiente: 256 de 256, 64 de 64 y 256 de 256 en tres configuraciones.** `PROVEN`.

## 1 · El defecto, literal

```c
uint32_t spec[2] = { iters, g_nacc };          /* 8 bytes */
VkSpecializationMapEntry me[2] = {
    { 0, 0, sizeof(uint32_t) },
    { 1, offsetof(VkSpecializationInfo, pData) + sizeof(uint32_t), sizeof(uint32_t) },
};
```

**⇒ `PROVEN`. `VkSpecializationMapEntry::offset` es el desplazamiento DENTRO de `pData`, no el
offset del campo `pData` dentro de la struct. Con `sizeof(void*) == 8`, el valor era 8 + 4 = 12,
y la entrada pedía los bytes 12..15 de un buffer de 8.** `PROVEN`.

**⇒ `PROVEN_DERIVED. El rango es inválido y la conducta ante un offset inválido no está
especificada: la descarta el driver. Lo medido es que además afecta a la entrada válida, porque
con el offset correcto ambas constantes llegan y con el incorrecto la segunda no.** `PROVEN_DERIVED`.

## 2 · El discriminante: no fue leer el código, fue el tiempo

**⇒ `MEASUREMENT`. El banco roto y el arreglado se compilan del mismo fuente salvo esa línea y
se ejecutan con el mismo comando.** `MEASUREMENT`.

| `iters` | `ident.comp` (1 sc) roto | arreglado | `cache.comp` (2 sc) roto | arreglado |
|---|---|---|---|---|
| 1 | 0,000349 | 0,000358 | 0,000346 | 0,000353 |
| 16 | 0,000340 | 0,000350 | 0,000329 | 0,000360 |
| 256 | 0,000735 | 0,000726 | 0,000831 | **0,004534** |

**⇒ `PROVEN`. `ident.comp` declara una sola specialization constant y los dos bancos coinciden
en las tres filas, 1,03× / 0,99×. `cache.comp` declara dos y divergen 5,46× en `iters=256`.
La diferencia del banco queda por tanto aislada en la segunda constant.** `PROVEN`.

**⇒ `PROVEN_DERIVED. Y el discriminante tiene dos salidas, no una. Si el fallo fuera que
`ITERS` no llegara, `ident.comp` también diferiría, porque su `ITERS` está en
`constant_id = 0`. Difiere en `cache.comp` y no en `ident.comp`, luego lo que se pierde es
`constant_id = 1`.** `PROVEN_DERIVED`.

**⇒ `PROVEN_DERIVED. Lo que hace el banco roto con `cache.comp` es ejecutar el bucle sin leer
memoria en él. `ident.comp` lee `d[i]` una vez y multiplica 256 veces en registro; `cache.comp`
lee `d[idx]` dentro del bucle. Con `iters=1` ambos leen una vez y coinciden; a partir de ahí el
banco roto se comporta como `ident`. Eso es un bucle cuya lectura se hoistea cuando el patrón
de acceso pasa a ser analizable, y el banco lo reportaba como si fuera el kernel.** `PROVEN_DERIVED`.

## 3 · Por qué `271` no lo vio, y por qué eso importa más que el bug

**⇒ `PROVEN_DERIVED. `cache.comp` declara `STRIDE = 16u` como default. Yo pasaba 16 en
`argv[4]`. El valor que yo creía estar midiendo y el valor que el shader usaba eran el mismo
número por casualidad, y los dos ambos no se distinguían.** `PROVEN_DERIVED`.

```glsl
layout(constant_id = 0) const uint ITERS  = 1u;
layout(constant_id = 1) const uint STRIDE = 16u;   /* el default ES 16 */
```

**⇒ `PROVEN_DERIVED. El banco sí reportaba la configuración en su `CONFIG`, con `nacc=16`, y
esa línea era verdad. El defecto no está en lo que el banco dice, está en lo que el driver
hace con lo que le dan. Un banco que imprime su configuración no ha verificado que la GPU la
ejecute: esa es exactamente la separación que `261` economizar al construir laVkSpecializationInfo
y que su propio comentario afirma haber hecho bien.** `PROVEN_DERIVED`.

**⇒ `PROVEN_DERIVED. Y hay un segundo efecto, más fuerte que la constant perdida: con la
constant perdida, el bucle se optimiza. Es decir, el defecto no solo mide menos trabajo del
que se cree, sino que cambia la nature del trabajo ejecutado.** `PROVEN_DERIVED`.

## 4 · El alcance sobre las notas anteriores

**⇒ `PROVEN. Re-medido con el banco arreglado, `cache.comp` en `W = 32768 KiB` da 0,06799 ns
por acceso. `271` publicó 0,01060.** `PROVEN`.

```text
271 publico        0,01046 ns/acceso  (banco con copia contaminada y me[1] roto)
270 tras corregir          0,01060 ns/acceso  (banco sin copia, me[1] roto)
276                0,06799 ns/acceso  (banco sin copia, me[1] arreglado)
```

**⇒ `REFUTED`. La meseta de `271` no era una propiedad del hardware. Era el kernel midiendo
una fracción del trabajo que el banco declaraba.** `REFUTED`.

**⇒ `PROVEN_DERIVED. Y el hallazgo de `271` —que el kernel era issue-bound y no memory-bound—
no sobrevive. Con el bucle real ejecutándose, 0,0680 ns por acceso son 58,9 GB/s, que es el
orden de magnitud de la VRAM, no tres veces su techo. `271` llegó a la respuesta
equivocada por un motivo equivocado.** `PROVEN_DERIVED`.

**⇒ `PROVEN`. La conclusión de `270` —que el kernel ALU da 6304,5 GFLOPS y es imposible— sí
sobrevive: no dependía de `constant_id = 1`, `alu.comp` no declara una segunda constant, y un
número 2,9× el techo con 16 CUs no sale de un defecto de instrumentación sino de un kernel que
el driver optimiza. Se anota que ahora hay un segundo mecanismo conocido para producing
números imposibles, y que `270` lo atribuyó a la latencia cuando era la eliminación del
bucle.** `PROVEN_DERIVED`.

## 5 · El kernel que sí mide, construido y validado

**⇒ `PROVEN`. `occ.comp` lleva las tres condiciones que `271` §4 declaraba necesarias: pocos
hilos, accesos pseudoaleatorios y cadena dependiente.** `PROVEN`.

```glsl
uint idx = hash(i + 0x9e3779b9u) % WSIZE;
for (uint k = 0u; k < ITERS; k++) {
    uint v   = d[idx];
    acc      = acc * 1664525u + v + 1013904223u;   /* consume v: no reordenable */
    idx      = hash(acc ^ (k * 0x85ebca6bu)) % WSIZE;  /* depende de v: cadena */
}
d[i] = acc;
```

**⇒ `PROVEN. Y tiene su propio modelo del host, con el mismo hash escrito al lado, y tres
configuraciones validan palabra a palabra.** `PROVEN`.

| `iters` | `items` | WSIZE | resultado |
|---|---|---|---|
| 256 | 256 | 1024 | 256 de 256 coinciden |
| 4 | 64 | 65536 | 64 de 64 coinciden |
| 16 | 1024 | 4096 | 256 de 256 coinciden |

**⇒ `PROVEN. El banco tiene ahora cuatro controles que discriminan: modelo correcto → 0, modelo
del kernel equivocado → 4, `wsize < items` → 2, y par kernel/modelo → 4.** `PROVEN`.

**⇒ `PROVEN_DERIVED. Para desacoplar conjunto de trabajo y despacho hizo falta un argumento
nuevo, `argv[5]`. Con `items` como ambas magnitudes los requisitos son incompatibles por
construcción: pocos hilos y conjunto grande no caben en un solo número.** `PROVEN_DERIVED`.

## 6 · Mis errores, y el patrón que ya es forma fija

**⇒ `ERROR`. Construí `occ.comp`, escribí su modelo del host, y cuando no coincidieron
concluí cuatro veces seguidas sobre el kernel —carrera de lectura/escritura, prefetch, caché
ausente— sin comprobar una sola vez que la specialization constant hubiera llegado.** `ERROR`.

**⇒ `ERROR`: el banco roto y el arreglado dan 5,46× de diferencia y ambos «validan» sus
controles. El control que yo tenía —readback contra modelo— no distingue un kernel mal escrito
de una constante que no llega, porque en ambos casos el resultado es coherente y distinto del
esperado. Para detectarlo hacía falta un control de la CONFIGURACIÓN, comparando dos bancos
que difieren en un solo carácter.** `ERROR`.

**⇒ `PROVEN_DERIVED. El patrón que se repite es el de `246`, `254`, `262`, `267` y `270`: el
número delata el error tarde. Aquí hay dos y la diferencia entre ellos es instructiva. En
aquellos el número era imposible. Aquí 0,0105 ns por acceso es un número perfectamente
plausible —la L2 de una GPU puede dar más— y aun así era falso. Un número puede ser físicamente
posible y estar describiendo un kernel que no es el que se cree.** `PROVEN_DERIVED`.

**⇒ `PROVEN_DERIVED. Y la regla que este caso añade a las propias: un banco de pruebas que
imprime su configuración no ha verificado que la configuración se ejecute. `CONFIG items=…
iters=… nacc=…` era exactamente igual de cierto antes y después del arreglo. La verificación
que faltaba no era leer el printf sino un discriminante que separe «la constante llegó» de
«la constante no llegó», y ese discriminante resultó ser comparar el mismo kernel contra dos
bancos que difieren en una línea.** `PROVEN_DERIVED`.

## 7 · PENDIENTE

```text
PENDIENTE=262-1 | HALLAZGO=276-*.md | ESTADO=INSTRUMENT_READY
           | NECESITA=medir con occ.comp (banco validado, 4 controles)
           | ALCANZABLE_SIN_ROOT=si

PENDIENTE=271-1 | ESTADO=REOPENED
           | MOTIVO=la meseta de 271 era artefacto; rehacer el barrido de tamaño
           |         de conjunto de trabajo con occ.comp y no con cache.comp

INSTRUMENT=vulkan_compute_probe.c | ESTADO=VALIDATED
           | CONTROLES=4 (0 correcto / 4 modelo equivocado / 2 wsize<items / 4 par)
           | BUG_CORREGIDO=me[1].offset: offsetof(pData)+4 -> sizeof(uint32_t)
```
