# 282 · El shader no distingue VRAM de RAM: la lectura se costea a 3,01 GB/s, 1,51 veces el techo de PCIe de `258`

```text
CLASSIFICATION=MEASUREMENT+PROVEN+INSTRUMENT · TRACK=RUNTIME
CORPUS=RESEARCH/working/linux-7.1.3 + Vulkan 1.1 + /sys/class/drm/card1/device/hwmon/hwmon1
HARDWARE_SCOPE=HOST-C/RX550/0000:01:00.0
WORK_CLASS=WRITE_LOCAL (banco y kernel propios) · WRITE_EXECUTION=carga Vulkan · NIVEL=1
MODIFICATIONS_CORPUS=0 · GPU INTACTA
INSTRUMENT=vulkan_compute_probe.c · 4 modos de memoria · muestra los tipos y heaps reales
```

> **`AFECTADA` por `606`: el discriminante de esta nota no llegó a ejecutarse.**
>
> La separación VRAM / RAM del sistema se hizo con `--mem=host`. El banco parsea ese flag
> en la línea 163 con `strtoul(argv[i] + 6, NULL, 10)`, y `strtoul("host")` es **cero**:
>
> ```text
>   --mem=vram |host |both  ->  g_mem = 0  =  DEVICE_LOCAL
>   --mem=0                  ->  tipo[0] flags=0x00000001  DEVICE_LOCAL
>   --mem=1                  ->  tipo[2] flags=0x00000006  HOST_VISIBLE
>   --mem=2                  ->  tipo[3] flags=0x00000007  HOST_VISIBLE|DEVICE_LOCAL
> ```
>
> Es decir, las dos corridas de la comparación eran la misma. La salida del banco **imprime**
> el tipo de memoria que eligió, `kernel=tipo[N] flags=0x...`, y eso estaba en el registro y
> no se leyó.
>
> **Estado:** la conclusión de esta nota puede ser correcta y estar mal argumentada. No se
> ha refutado; se ha privada de la evidencia que la sostenía. Repetir con `--mem=1` es
> `606-2`, y hay un separador mejor que `--mem`: el acantonado del **BAR a 256 MiB**
>
> ```text
>   huella      --mem=0 (VRAM)    --mem=1 (RAM del host)
>    128 MiB        44,26 GB/s          44,08 GB/s
>    256 MiB        44,53 GB/s           1,38 GB/s   <- el BAR se agota
>    512 MiB        43,72 GB/s           1,37 GB/s
> ```

## Qué resuelve

**⇒ Ejecuta el discriminante que `281` propuso —variar el tipo de memoria del buffer para
separar «la lectura va a VRAM» de «la lectura no va a VRAM»— y el resultado es categórico: el
tiempo es idéntico.** `PROVEN`.

**⇒ `PROVEN`. Con `STEPS` = 16 y control pasando 9 de 9 en cada modo: VRAM 0,003871 s, RAM
0,003866 s, razón 1,0013. Con `STEPS` = 64: VRAM 0,012955 s, RAM 0,012965 s, razón 0,9992.** `PROVEN`.

**⇒ `PROVEN_DERIVED. Y hay un argumento aritmético que no depende de nada que no esté
determinado: la lectura se costea a 3,013 GB/s, y el techo de PCIe Gen2 x4 derivado en `258` es
2,000 GB/s. Leer de la RAM del sistema exige cruzar PCIe, luego 1,51 veces su techo es
imposible. Y tampoco puede estar yendo a VRAM, porque entonces sería más rápida que la RAM y
mide lo mismo.** `PROVEN_DERIVED`.

**⇒ `PROVEN_DERIVED`. Combinado con `281`, que probó que la cadena ALU sí se ejecuta y escala
linealmente, la conclusión es una sola y es la más dura de esta tanda: **la parte del trabajo que
toca memoria no se está costeando, y la parte que es ALU sí.** No es que el bucle se optimice;
es que el acceso no entra en el tiempo.** `PROVEN_DERIVED`.

> **`ALCANCE ACOTADO` por `284`.** El argumento de §3 —«3,013 GB/s es imposible en esta placa»—
> es correcto **dado el estado actual del enlace**, y no dado el hardware. Verificado contra
> `sysfs`: `current_link_speed` = 5,0 GT/s y `current_link_width` = 4, luego 2,000 GB/s, lo que
> confirma el techo que esta nota usó. Pero `max_link_speed` = 8,0 GT/s y `max_link_width` = 8,
> luego la tarjeta admite **7,877 GB/s**.
>
> ```text
> lectura medida              2,970 GB/s
> techo del enlace ACTUAL     2,000 GB/s  ->  1,49x   IMPOSIBLE AHORA
> techo del enlace MAXIMO     7,877 GB/s  ->  0,38x   cabria de sobra
> ```
>
> Si el enlace llegara a negociarse en Gen3 ×8, esta medición dejaría de ser imposible por el
> argumento del enlace. La razón de que esté en Gen2 ×4 es `NOT_DETERMINED` (`284`, `258-4`).

> **`REFUTADO` el §3 por `287`; §1 y §2 se sostienen.** La afirmación de §3 —«3,013 GB/s es
> imposible en esta placa»— falla por dos motivos independientes, ambos míos.
>
> El primero es la unidad, como en `277`: el 3,013 GB/s viene de `t / (items × iters)`, que es
> el ritmo agregado. El segundo es el encuadre: **el buffer del kernel es `DEVICE_LOCAL`, o sea
> VRAM, y su techo es 24,0 GB/s, no los 2,000 GB/s del enlace.** Contra el techo correcto,
> 2,970 GB/s son un 12,4% — perfectamente plausible para una cadena de baja ocupación. El 1,49×
> era una coincidencia aritmética entre un número mal formado y un techo que no era el recurso
> implicado.
>
> **El «no se distingue VRAM de RAM» de §1 sí se sostiene**, con el matiz de `287`: si lo que se
> mide es latencia, las latencias de la VRAM y de la RAM pueden ser del mismo orden y no tienen
> por qué distinguirse. Ver `287` §5.

## 1 · El confound, cerrado antes de comparar

**⇒ `PROVEN_DERIVED. Un discriminante que compara dos modos de memoria es vacío si ambos modos
acaban en el mismo heap. El banco ahora imprime el tipo y el heap reales de las dos
asignaciones, antes de medir.** `PROVEN_DERIVED`.

```text
--mem=0  kernel=tipo[0] flags=0x00000001 heap=0   staging=tipo[2] flags=0x00000006 heap=1
--mem=1  kernel=tipo[2] flags=0x00000006 heap=1   staging=tipo[2] flags=0x00000006 heap=1
```

**⇒ `PROVEN`. Los dos modos usan memoria distinta de verdad: `heap=0` con
`DEVICE_LOCAL` para VRAM, `heap=1` con `HOST_VISIBLE` para RAM. `memoryTypeCount` es 7.** `PROVEN`.

**⇒ `NOT_APPLICABLE`: el tercer modo, `HOST_VISIBLE | DEVICE_LOCAL`, existe como tipo pero
produce ceros en las 256 palabras y el control aborta con 4. No es utilizable como storage
buffer por el driver de esta placa, así que ese brazo del discriminante no existe.** `NOT_APPLICABLE`.

## 2 · El resultado

**⇒ `MEASUREMENT. `chain.comp`, `ITERS` 4096, `items` 256, `WSIZE` 65536, 9 muestras, y sólo se
acepta una muestra si su control pasa.** `MEASUREMENT`.

| `steps` | memoria | t (s) | ns por acceso | control |
|---|---|---|---|---|
| 16 | VRAM | 0,003871 | 3,6917 | 9/9 |
| 16 | RAM | 0,003866 | 3,6869 | 9/9 |
| 64 | VRAM | 0,012955 | 12,3549 | 9/9 |
| 64 | RAM | 0,012965 | 12,3644 | 9/9 |

**⇒ `PROVEN`. Razón 1,0013 con 16 pasos y 0,9992 con 64. Dos razones que son 1 dentro del ruido,
con el control pasando en todas las muestras y con las dos memorias verificadas como
distintas.** `PROVEN`.

**⇒ `MEASUREMENT. Y con `STEPS` = 0, donde la iteración es sólo la lectura y no hay ALU que la
diluya: 1,3275 ns por acceso en VRAM y 1,3351 ns en RAM, razón 0,9943.** `MEASUREMENT`.

## 3 · El argumento que no depende de ninguna incógnita

**⇒ `PROVEN_DERIVED. Esta placa es discreta, con BAR de 256 MiB (`243`), luego no hay UMA: leer
de la RAM del sistema exige cruzar el enlace PCIe.** `PROVEN_DERIVED`.

```text
lectura de 4 B, coste medido        1,3275 ns  ->  3,013 GB/s
techo de PCIe Gen2 x4, derivado    2,000 GB/s  (258)
minimo teorico para 4 B por PCIe    2,000 ns
medido                              1,3275 ns  =  1,51 veces el techo del enlace
```

**⇒ `PROVEN`. 3,013 GB/s sobre RAM es imposible en esta placa por una razón que no depende del
número de CUs, ni del tamaño de caché, ni de ninguna de las incógnitas que quedan abiertas: el
enlace no puede dar más de 2,000 GB/s y esto pide 3,013.** `PROVEN`.

**⇒ `PROVEN_DERIVED. Y la otra rama queda cerrada por simetría. Si la lectura fuera a VRAM, sería
más rápida que la RAM —la VRAM tiene 12 veces más de ancho de banda según `258`— y mediríamos
tiempos distintos. Medimos los mismos.** `PROVEN_DERIVED`.

**⇒ `PROVEN_DERIVED. Las dos salidas de `277` y `281` quedan así: el bucle eliminado está
descartado por `281`, y la lectura a VRAM está descartada por esta nota. Lo que queda no es una
de las dos hipótesis que tenía, sino una tercera que no había considerado: que el acceso se
resuelva en un nivel de caché del que el conjunto de 256 MiB no debería caber, o que la ruta de
carga del shader no pase por el sistema de memoria que estoy suponiendo.** `PROVEN_DERIVED`.

## 4 · La carrera, cuantificada, y por qué sólo se reportan dos filas

**⇒ `PROVEN`. `chain.comp` escribe `d[i]` al final de `main`, para `i < items`, y lee `d[idx]` en
el bucle. Si `idx` cae en `[0, items)`, el hilo lee una palabra que otro hilo puede haber
escrito. No es una hipótesis: contando por programa, 1 hilo de 256 termina su última lectura
dentro de la zona escrita.** `PROVEN`.

**⇒ `MEASUREMENT. La tasa de fallo del control depende de `ITERS`, y por eso el barrido anterior
no es todo válido.** `MEASUREMENT`.

| `steps` | `iters` | control VRAM | control RAM |
|---|---|---|---|
| 16 | 64 | 40/40 | 40/40 |
| 0 | 64 | 36/40 | 34/40 |
| 1 | 64 | 0/40 | 0/40 |

**⇒ `PROVEN_DERIVED. Con `STEPS` = 1 y `ITERS` = 64 el control falla siempre; con `ITERS` = 1
pasa siempre, y con `ITERS` = 8 falla una palabra de 256. La ventana de carrera es la última
lectura de cada hilo, y su probabilidad crece con el número de vueltas. Eso explica la
aparición del fallo y su desaparición, y no es un defecto del kernel sino un defecto del
diseño: el kernel lee y escribe el mismo buffer.** `PROVEN_DERIVED`.

**⇒ `PROVEN_DERIVED. Por eso las únicas filas que esta nota reporta son `STEPS` = 16 y 64, donde
el control pasa 9 de 9 en cada muestra aceptada. Las filas con `STEPS` = 0 y 1 quedan con la
tasa de control al lado y no se usan para concluir nada.** `PROVEN_DERIVED`.

## 5 · El estado de `262-1`, que es lo que esta nota tenía que cerrar

**⇒ `NOT_DETERMINED`, y con un motivo que ha cambiado tres veces.** `NOT_DETERMINED`.

```text
265  no esta en ninguna fuente del driver
277  el barrido mide emision, no memoria
281  el bucle NO se elimina; el coste es de overhead, no de ALU
282  y ahora: el acceso no se costea a 3,013 GB/s, 1,51x el techo de PCIe, y el shader
     no distingue VRAM de RAM
```

**⇒ `NOT_DETERMINED`: el tamaño de caché de GFX8 sigue sin número, y la vía sin MMIO que
`281` proponía queda cerrada. Un banco de Vulkan no puede distinguir «la caché de la GPU» de
«la caché de la CPU», porque para el shader ambas son cachés con el mismo tiempo.** `NOT_DETERMINED`.

**⇒ `PROVEN_DERIVED. Y hay un dato que sí es un hallazgo y que no buscaba: la lectura de 4 B por
acceso encadenado se costea a 3,013 GB/s en esta placa con este driver, contra 2,000 GB/s de
techo de enlace y 24,0 GB/s de techo de VRAM. Ese número es el límite efectivo que cualquier
driver propio tiene que respetar, y no viene de la especificación del hardware sino de lo que el
camino de lectura hace de la instrucción.** `PROVEN_DERIVED`.

## 6 · Errores propios

**⇒ `ERROR`: al imprimir el tipo de memoria indexé `memoryTypes[ti]` sin acotar `ti` contra
`memoryTypeCount`. Dio `SIGBUS`. Un diagnóstico que rompe el banco es peor que no tenerlo, y
tuve que reconstruir el binario anterior para seguir midiendo.** `ERROR`.

**⇒ `ERROR`: la primera versión de la tabla de tiempos no llevaba la tasa de control al lado, y
con `STEPS` = 1 el control falla 0 de 40. Publicar una cifra cuyo control nunca pasa es
exactamente el error que `277` me reprochó, y lo cometí en la nota inmediatamente posterior.**
`ERROR`.

**⇒ `ERROR`: afirmé que 0,0232 ns por hash era «más rápido que el techo de la ALU». Al hacer la
división, 0,0165 ns es el techo y 0,0232 ns el medido: el medido es más LENTO. Leí la dirección
al revés y construí sobre ella una interpretación entera sobre la ALU que no sostiene.** `ERROR`.

**⇒ `PROVEN_DERIVED. Los tres son el mismo error de siempre —redactar antes de mirar— y el
tercero es el más instructivo porque lo detecté con una división, después de haber escrito tres
párrafos sobrecapacidad de cómputo. La regla de la que me olvidé es la más simple de todas:
ningún número que decide una conclusión se calcula mentalmente. Yo calculé 0,0232 frente a
0,0165 mirando la tabla, no corriendo el programa.** `PROVEN_DERIVED`.

**⇒ `PROVEN_DERIVED. Y hay una regla específica de esta tanda que sale de aquí: una cifra cuyo
control pasa 9 de 10 y otra que pasa 40 de 40 no se pueden comparar, aunque el banco las haya
producido con el mismo comando. El control no es una nota al pie, es parte del dato.** `PROVEN_DERIVED`.

## 7 · PENDIENTE

```text
PENDIENTE=262-1 | HALLAZGO=282-*.md | ESTADO=NOT_DETERMINED
           | AVANCE=descartadas las dos salidas anteriores; el barrido de conjunto de
           |         trabajo via Vulkan no puede cerrar el tamaño de cache
           | RAZON=para el shader, la cache de la GPU y la de la CPU son lo mismo
           | ALCANZABLE_SIN_ROOT=no

PENDIENTE=282-1 | ESTADO=OPEN
           | PREGUNTA=¿por que una lectura encadenada se costea a 3,013 GB/s, 1,51x el
           |          techo de PCIe, e igual en VRAM y en RAM?
           | DISCAMINANTE_CANDIDATO=un VkImage en vez de un VkBuffer: una imagen tiene
           |          su propia ruta de texel, y si esa ruta difiere, la diferencia
           |          localizaria el camino. sin MMIO.
           | ALCANZABLE_SIN_ROOT=si

PENDIENTE=282-2 | ESTADO=OPEN
           | PREGUNTA=¿el kernel puede leerse y escribirse sin carrera?
           | NECESITA=dos buffers, o escribir en d[WSIZE + i] con el bufferampliado a WSIZE+items
           | ALCANZABLE_SIN_ROOT=si
```
