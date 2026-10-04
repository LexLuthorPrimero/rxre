# 277 · La cadena dependiente sí pagaba su latencia, 443 ciclos: el 7,0 por acceso de esta nota era una unidad equivocada y no debe citarse

> **H1 CORREGIDO EL 2026-10-04.** El titulo anterior decia «La cadena dependiente valida contra su modelo y aun así no mide memoria: 7,0 ciclos por acceso». Ese
> enunciado ya no describe el estado del arbol. El veredicto vigente esta en este
> mismo fichero:
> - `:42` — la latencia real: «La lectura **sí** costaba su latencia: **443 ciclos**»
> - `:47` — el error de unidad: «La latencia que sufre un hilo es `t / iters`»
> - `:53` — prohibido citar: «**Las cifras de esta nota no deben citarse.**»
>
> Este parche toca **solo el H1** y esta marca. El cuerpo no se reescribe: la
> correccion del titulo tiene que quedar rastreable, o el titulo parece haber
> sido asi siempre.

```text
CLASSIFICATION=MEASUREMENT+NEGATIVE_RESULT+INSTRUMENT · TRACK=RUNTIME
CORPUS=RESEARCH/working/linux-7.1.3 + /sys/class/drm/card1/device/hwmon/hwmon1
HARDWARE_SCOPE=HOST-C/RX550/0000:01:00.0
WORK_CLASS=WRITE_LOCAL (banco y kernel propios) · WRITE_EXECUTION=carga Vulkan · NIVEL=1
MODIFICATIONS_CORPUS=0 · GPU INTACTA
INSTRUMENT=vulkan_compute_probe.c tras 276 · VALIDATED (4 controles)
```

## Qué resuelve

**⇒ Ejecuta la medición que `276` dejó preparada —el barrido del conjunto de trabajo con el
kernel de ocupación baja— y el resultado es un `NEGATIVE_RESULT` con un dato colateral
sólido.** `PROVEN`.

**⇒ `PROVEN`. El kernel `occ.comp` cumple las tres condiciones que `271` declaraba necesarias
—pocos hilos, índice pseudoaleatorio, cadena dependiente— valida 256 de 256 contra su modelo
del host, y sin embargo el coste marginal por iteración es de 6,55 ns: 7,0 ciclos a
`sclk` 1063,02 MHz. Una latencia de VRAM en GFX8 son cientos de ciclos.** `PROVEN`.

**⇒ `PROVEN`. Consecuencia directa: la meseta de 16 MiB que produce este barrido NO es el
tamaño de caché. Es un techo de emisión, y por tanto `262-1` sigue sin número.** `PROVEN`.

**⇒ `PROVEN_DERIVED`. El hecho de que el kernel valide contra el modelo descarta la
explicación más obvia —que el shader no ejecutara lo que dice— y deja una sola: la
dependencia no se está costeando en el recurso que debía costarse.** `PROVEN_DERIVED`.

> **`REFUTADA` por `287`.** La conclusión central de esta nota —«el kernel es issue-bound y no
> memory-bound»— **es falsa**. La lectura **sí** costaba su latencia: **443 ciclos** de reloj,
> constante con 64, 256 y 1024 hilos.
>
> El error era aritmético y mío, y está en la unidad: vengo midiendo y reportando
> `t / (items × iters)` como «ns por acceso», que es el **ritmo agregado** con todos los hilos
> en paralelo. La latencia que sufre un hilo es `t / iters`. La diferencia es un factor `items`,
> que ha estado escondido en el denominador durante esta nota y las cuatro siguientes.
>
> Con la magnitud correcta, la curva tiene dos regímenes que esta nota no vio: hasta 1024 hilos
> el límite es de latencia (443 ciclos, el ancho de banda sube linealmente con los hilos); desde
> 4096 es de ancho de banda (se satura en 17,83 GB/s y la latencia se multiplica por cuatro).
> Ver `287` §2 y §3. **Las cifras de esta nota no deben citarse.**

## 1 · La curva, medida con el banco de `276`

**⇒ `MEASUREMENT`. `occ.comp`, 256 hilos —4 workgroups de 64—, 512 iteraciones, `WSIZE`
igual al conjunto de trabajo, 9 muestras con 3 de calentamiento, control activo.** `MEASUREMENT`.

| W (KiB) | t (s) | ns por acceso | `mclk` |
|---|---|---|---|
| 64 | 0,000241 | 1,8387 | 300 |
| 256 | 0,000299 | 2,2812 | 300 |
| 1.024 | 0,000674 | 5,1422 | 300 |
| 4.096 | 0,000990 | 7,5531 | 300 |
| 16.384 | 0,001158 | 8,8348 | 300 |
| 65.536 | 0,001184 | 9,0332 | 300 |
| 262.144 | 0,001252 | 9,5520 | 300 |

**⇒ `PROVEN`. La curva tiene la forma que se busca: sube y se aplana. El aplanamiento empieza
en 16384 KiB, y de 65536 a 262144 KiB —un factor 4— la variación es del 5,7%.** `PROVEN`.

**⇒ `PROVEN_DERIVED. Y ese 5,7% es exactamente el tipo de número que en `271` se interpretó como
«la memoria no importa». Pero aquí el aplanamiento no prueba que la memoria no importe: prueba
que el kernel no está pidiendo memoria. Falta decidir cuál de las dos cosas es, y para eso hace
falta un número que no dependa de la interpretación de la curva.** `PROVEN_DERIVED`.

## 2 · El número que no admite dos lecturas

**⇒ `PROVEN`. Separando el overhead fijo del coste marginal con un ajuste lineal sobre siete
puntos de `ITERS` de 64 a 4096, a conjunto de trabajo de 256 MiB:** `MEASUREMENT`.

```text
t = A + B * ITERS
A (coste fijo)              = 0,000439603 s
B (por iteracion)           = 0,000001677 s
B / items, con items = 256  = 6,5508 ns por iteracion por hilo
6,5508 ns a sclk 1063,02 MHz = 7,0 ciclos
```

**⇒ `PROVEN`. Siete ciclos. Ése es el dato, y no admite interpretación benévola: una cadena
dependiente de 256 hilos sobre un conjunto de 256 MiB que no cabe en ninguna caché de esta
placa tendría que costar la latencia de la VRAM, que es de cientos de ciclos.** `PROVEN`.

**⇒ `PROVEN_DERIVED. Y hay una comprobación que separa «cadena rota» de «cadena que nunca llega
a ser una»: subir `ITERS` con el conjunto fijo. Si la cadena se costase en memoria, el tiempo
por iteración sería constante; si el trabajo se amortizara, mejoraría al subir `ITERS`.
Medido: 38,51 ns a 64 iteraciones, 12,02 a 256, 8,53 a 1024, 6,87 a 4096. Mejora de forma
monótona, luego hay coste fijo de despacho que domina a `ITERS` bajos, y por encima de 1024 el
marginal se estabiliza en 7 ciclos.** `PROVEN_DERIVED`.

## 3 · La comprobación que más restringe, y su lectura

**⇒ `PROVEN. La prueba decisiva no es la curva de caché sino la de ocupación: con la cadena
intacta y el conjunto fijo en 256 MiB, subir el número de hilos debe paralelizar las cadenas
y bajar el tiempo por acceso.** `PROVEN`.

| `items` | t (s) | ns por acceso | cadenas/s |
|---|---|---|---|
| 256 | 0,002173 | 8,2893 | 0,12 G |
| 1.024 | 0,006839 | 6,5222 | 0,15 G |
| 4.096 | 0,016024 | 3,8204 | 0,26 G |
| 16.384 | 0,048072 | 2,8653 | 0,35 G |
| 65.536 | 0,175353 | 2,6130 | 0,38 G |

**⇒ `PROVEN_DERIVED. El tiempo por acceso baja de 8,29 a 2,61 ns al multiplicar los hilos por
256. Eso es paralelismo real y es la firma de una cadena que sí se costorea: el hardware está
tapando la latencia con más trabajo concurrente.** `PROVEN_DERIVED`.

**⇒ `PROVEN_DERIVED. Y al mismo tiempo, el mejor caso sigue siendo 2,61 ns por acceso, es
decir unos 2,8 ciclos. Una cadena dependiente real no puede resuelverse en 2,8 ciclos contra
256 MiB de VRAM. Las dos observaciones juntas son la contradicción: el paralelismo es real, y
la latencia que se está midiendo no es la de la memoria.** `PROVEN_DERIVED`.

**⇒ `PROVEN_DERIVED. La lectura que queda y que no obliga a descartar el kernel: la
dependencia se rompe dentro de la propia iteración. `acc` se realimenta con una multiplicación
y una suma antes de que se calcule el índice siguiente, así que el índice de la vuelta `k+1`
depende de la vuelta `k` —pero el hardware puede haber emitido la carga de `k+1` antes de
resolver `k` si el compilador las reordena, porque el índice es una función de `acc` y
`acc` se conoce en la vuelta `k` antes de la carga de esa vuelta.** `PROVEN_DERIVED`.

**⇒ `NOT_DETERMINED`: si ese reordenamiento ocurre, o si la L2 está --------------------------------------------------------------
atendiendo más de lo que su tamaño permite, no se puede decidir desde esta plataforma sin un
observable de MMIO.** `NOT_DETERMINED`.

## 4 · Lo que sí queda, y lo que no

**⇒ `PROVEN. Cuatro afirmaciones que el banco sostiene y que no dependen de ninguna
interpretación de la curva:** `PROVEN`.

```text
1. occ.comp se ejecuta y produce lo que su shader dice: 256 de 256 coinciden con el modelo
   del host, en tres configuraciones distintas de iters, items y WSIZE.
2. el coste marginal de una iteracion es 6,55 ns por hilo, 7,0 ciclos a sclk 1063,02 MHz,
   con un conjunto de trabajo de 256 MiB que no cabe en ninguna cache de esta placa.
3. ese coste es el mismo con 256 MiB que con 64 MiB de conjunto, dentro del 5,7%.
4. con 65536 hilos el tiempo por acceso baja a 2,61 ns: hay paralelismo real.
```

**⇒ `NOT_DETERMINED`. Y lo que ninguna de las cuatro sostiene: que ese número sea una latencia
de memoria. No lo es según la física de la placa, y un banco que lo presentara como tal
estaría repitiendo el error de `271` con un número nuevo.** `NOT_DETERMINED`.

**⇒ `PROVEN_DERIVED. Consecuencia para `262-1`: la meseta de 16 MiB no es el tamaño de caché.
El tamaño de caché sigue sin número, y por un motivo distinto al de `265`: no es que no esté
en ninguna fuente, es que el único instrumento que podría medirlo no llega a la memoria.** `PROVEN_DERIVED`.

**⇒ `PROVEN_DERIVED. Y el valor del instrumento se ve en `4`: 0,38 G cadenas/s con 65536 hilos
es un dato utilizable sobre el paralelismo de esta GPU, aunque no diga nada sobre la
latencia. Un resultado negativo que deja un número bueno es un resultado mejor que un
resultado positivo que no se sostiene.** `PROVEN_DERIVED`.

## 5 · La regla que este caso añade

**⇒ `PROVEN_DERIVED. El readback contra el modelo del host valida que el kernel calcula lo
que su fuente declara. No valida que el hardware lo costree donde la fuente dice que lo
custee. Son dos preguntas distintas, y `276` demonstrated que la primera puede pasar mientras
la segunda es falsa: con la constant perdida, el resultado era coherente, el modelo acertaba, y
el trabajo ejecutado era una fracción.** `PROVEN_DERIVED`.

**⇒ `PROVEN_DERIVED. El control que faltaba en el banco era un tercero: comprobar que el
tiempo escala con el parámetro que se dice estar variando. `occ.comp` declara `ITERS` en
`constant_id = 0` y el banco lo pasa por `VkSpecializationInfo`; que `t` escale con `ITERS` es
una comprobación independiente del readback, y si falla señala a la instrumentación antes que
al hardware. No estaba, y por eso el defecto de `276` pudo vivir durante tres notas.** `PROVEN_DERIVED`.

**⇒ `PROVEN_DERIVED. Y la forma del error es la misma que en `246`, `254`, `262`, `267`, `270` y
`276`, con una diferencia instructive: en todos los anteriores el número era imposible y lo
detecté tarde por eso. Aquí el número es físicamente plausible —6,55 ns, 7 ciclos, una latencia
de caché corriente— y no hay ninguna prueba aritmética que lo delate. Ha hecho falta un
argumento físico, no un número imposible.** `PROVEN_DERIVED`.

## 6 · PENDIENTE

```text
PENDIENTE=262-1 | HALLAZGO=277-*.md | ESTADO=NOT_IMPLEMENTED
           | NECESITA=CORPUS  (observable de MMIO de la L2, o un kernel cuya latencia
           |                   no se pueda reordenar: p.ej. inhibition por barrera)
           | ALCANZABLE_SIN_ROOT=no   <- la razon del cambio devia a la nota 276

PENDIENTE=277-1 | ESTADO=OPEN
           | PREGUNTA=¿por que 7 ciclos con 256 MiB de conjunto de trabajo?
           | DISCriminante=un kernel con barrier() entre la lectura y el uso del dato:
           |              si entonces el coste sube a cientos de ciclos, la cadena si se
           |              estaba rompiendo y el compilador es el responsable.
           | ALCANZABLE_SIN_ROOT=si

INSTRUMENT=vulkan_compute_probe.c | ESTADO=VALIDATED pero con un control menos
           | FALTA=verificar que t escala con la specialization constant que se varia
```
