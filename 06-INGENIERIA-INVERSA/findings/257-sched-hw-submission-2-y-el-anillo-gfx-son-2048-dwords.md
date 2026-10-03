# 257 · `sched_hw_submission=2` está medido, el anillo GFX son 2048 dwords, y el comentario del driver que no cuadra con sus propias cifras no importa por qué

```text
CLASSIFICATION=MEASUREMENT+DERIVATION · TRACK=RUNTIME + STATIC
CORPUS=RESEARCH/working/linux-7.1.3 + /sys/module/amdgpu/parameters/
HARDWARE_SCOPE=HOST-C/RX550/0000:01:00.0
WORK_CLASS=READ_ONLY/EVIDENCE · WRITE_LOCAL=PROPIOS · MODIFICATIONS_CORPUS=0 · WRITE_EXECUTION=NONE
RUNTIME=SYSFS SOLO LECTURA · GPU INTACTA
```

> **Convención de rutas.** `amdgpu/x.c` = `drivers/gpu/drm/amd/amdgpu/x.c`. Las 13 citas de
> código resuelven con base `drivers/gpu/drm/amd/`.

## Qué resuelve

**Cierra el `PENDIENTE=255-1` y abre el lado de performance de §H.** `PROVEN`.

**⇒ `PROVEN`. `/sys/module/amdgpu/parameters/vm_size`, `vm_block_size` y `vm_fragment_size`
valen los tres `-1`. La rama que calculó `255` —la de los defaults— es la que se ejecuta, así que
los cinco valores de la geometría de GFX8 suben de `PROVEN_DERIVED` a `PROVEN` sobre runtime.** `PROVEN`.

**⇒ `PROVEN`. `sched_hw_submission = 2`, medido. Es el default declarado en
`amdgpu/amdgpu_drv.c:178` y no un valor forzado por módulo, y `amdgpu/amdgpu_device.c:1577` lo
confirma como el mínimo que el driver acepta.** `PROVEN`.

**⇒ `PROVEN_DERIVED`. Con esos dos valores, el anillo GFX de GFX8 mide 2048 dwords = 8 KiB. Y el
resultado es robusto: cualquier presupuesto de frame entre 129 y 256 dwords da ese mismo anillo,
así que el valor exacto del presupuesto no importa.** `PROVEN_DERIVED`.

## 1 · Los tres parámetros que cierran `255`

**⇒ `PROVEN`. Lectura directa de sysfs, que es la ruta que `255` declaró como
`ALCANZABLE_SIN_ROOT=NO_MEDIDO` y que existe:** `PROVEN`.

```text
/sys/module/amdgpu/parameters/vm_size           = -1
/sys/module/amdgpu/parameters/vm_block_size     = -1
/sys/module/amdgpu/parameters/vm_fragment_size  = -1
```

**⇒ `PROVEN_DERIVED`. Cada uno cierra una rama distinta del cálculo de `255`:** `PROVEN_DERIVED`.

| parámetro | guarda en el driver | valor medido | rama que se ejecuta |
|---|---|---|---|
| `vm_size` | `amdgpu_vm.c:2388` | `-1` | el `else`, con `si_meminfo` |
| `vm_block_size` | `amdgpu_vm.c:2425` | `-1` | no se aplica el `>>=` |
| `vm_fragment_size` | `amdgpu_vm.c:2456` | `-1` | `= fragment_size_default = 9` |

**⇒ `PROVEN_DERIVED. La diferencia entre esta nota y `255` es de grado de evidencia, no de
contenido: `255` calculó la rama correcta y dijo que lo estaba; aquí se ha comprobado que es la
rama que corre.** `PROVEN_DERIVED`.

## 2 · `sched_hw_submission`: el default es también el suelo

**⇒ `PROVEN`. Tres piezas y las tres verificadas:** `PROVEN`.

```c
amdgpu_drv.c:178     int amdgpu_sched_hw_submission = 2;      /* el default */
amdgpu_drv.c:490     MODULE_PARM_DESC(sched_hw_submission, "the max number of HW submissions (default 2)");
amdgpu_drv.c:491     module_param_named(sched_hw_submission, amdgpu_sched_hw_submission, int, 0444);
```

**⇒ `PROVEN_DERIVED`. Y el valor no puede ser 1: `amdgpu/amdgpu_device.c:1577` es
`if (amdgpu_sched_hw_submission < 2)` y `amdgpu_device.c:1580` lo sobrescribe a 2 con un
`dev_warn`. `amdgpu_device.c:1581` además exige que sea potencia de dos y `amdgpu_device.c:1584`
lo redondea. El conjunto de valores aceptables es {2, 4, 8, 16, 32, 64, 128, 256}, y el mínimo
es 2.** `PROVEN_DERIVED`.

**⇒ `PROVEN`. Y el valor por tipo de anillo, `amdgpu/amdgpu_ring.c:232-248`, porque el 2 no se
aplica igual a todos:** `PROVEN`.

| anillo | `sched_hw_submission` | línea |
|---|---|---|
| GFX, COMPUTE, SDMA | **2** (el del módulo) | `amdgpu_ring.c:232` |
| KIQ | `max(2, 256)` = **256** | `amdgpu_ring.c:244` |
| MES | **8** (fijo) | `amdgpu_ring.c:246` |
| page ring de SDMA0 | **256** (fijo) | `amdgpu_ring.c:248` |

**⇒ `PROVEN_DERIVED. El comentario de `amdgpu_ring.c:237-241` explica el caso de KIQ: lo usan
KFD y KGD, que pueden tener fences pendientes y no usan el scheduler de la GPU, así que sus
tareas seiterse directamente al anillo. El 256 no es un límite, es una reserva de trabajo
pendiente.** `PROVEN_DERIVED`.

## 3 · La fórmula y la cuantización, que es el hallazgo

**⇒ `PROVEN`. `amdgpu/amdgpu_ring.c:339` y `amdgpu_ring.c:342`:** `PROVEN`.

```c
339      ring->ring_size = roundup_pow_of_two(max_dw * 4 * sched_hw_submission);
341      ring->ring_size = roundup_pow_of_two(max_dw * 4);
342      ring->count_dw = (ring->ring_size - 4) >> 2;
```

**⇒ `PROVEN_DERIVED`. El `ring_size` es una potencia de dos, luego está cuantizado. Eso convierte
cualquier error en el presupuesto de `max_dw` en holgura en vez de en corrupción. El rango de
`max_dw` que produce 2048 dwords con `sched_hw_submission = 2` es [129, 256], medido por
programa: `128 < max_dw·8 ≤ 2048`.** `PROVEN_DERIVED`.

**⇒ Y aquí está el dato: el comentario de `amdgpu/gfx_v8_0.c:6878` dice «maximum 215dw if count
16 IBs in», y la suma de las constantes que el propio driver escribe en las 18 líneas siguientes
da un número distinto.** `PROVEN`.

**⇒ `PROVEN_DERIVED. Los cuatro candidatos —215 del comentario, 172 y 177 de las constantes según
si el `* 5` de `VI_FLUSH_GPU_TLB_NUM_WREG` se cuenta una vez o dos, y 241 sumando las 16 IBs por
`emit_ib_size = 4` de `gfx_v8_0.c:6897`— caen todos dentro de [129, 256]. Por lo tanto la
discrepancia no cambia el anillo y el comentario obsoleto no ha producido ningún bug
observable.** `PROVEN_DERIVED`.

**⇒ `PROVEN_DERIVED. La consecuencia para el driver propio es la que importa: un presupuesto de
frame demasiado corto no es un fallo de corrección sino una pérdida de espacio, y uno demasiado
largo tampoco, mientras que no cruce el límite de la potencia de dos. La clase de error que hay
que temer no es la del presupuesto, es la del cruce de potencia.** `PROVEN_DERIVED`.

**⇒ Y los niveles de llenado, por programa, que es donde se ve la holgura:**

| `max_dw` | usado | anillo | lleno | holgura |
|---|---|---|---|---|
| 172 | 1376 dw | 2048 dw | 67,2% | 32,8% |
| 215 | 1720 dw | 2048 dw | 84,0% | 16,0% |
| 241 | 1928 dw | 2048 dw | 94,1% | 5,9% |

**⇒ `PROVEN_DERIVED. Con el valor del comentario el anillo GFX queda al 16% de holgura, que es
un margen razonable. Con el valor más alto de mis sumas queda al 5,9%, que roza el límite en el
que un frame con más IBs de los 16 podría desbordar. El comentario, aunque no cuadre con sus
propias cifras, es el número conservador y ése es el que conviene replicar.** `PROVEN_DERIVED`.

## 4 · Un resultado de lectura que no era un valor

**⇒ `PROVEN`. Cuatro parámetros de los 86 se leen como cadena vacía: `gttsize`, `gartsize`,
`vramlimit` y `moverate`. La causa es de permisos, no de valor: están en modo `0600` frente a
`0444` de los otros 81.** `PROVEN`.

**⇒ `PROVEN_DERIVED`. El `0600` viene del cuarto argumento de `module_param_named`, que es la
máscara de permisos del fichero en sysfs. `amdgpu/amdgpu_drv.c:293` es
`module_param_named(gartsize, amdgpu_gart_size, uint, 0600)` y `amdgpu_drv.c:302` es
`module_param_named(gttsize, amdgpu_gtt_size, int, 0600)`, contra `amdgpu_drv.c:491` que usa
`0444` para `sched_hw_submission`.** `PROVEN_DERIVED`.

**⇒ `ERROR`. Mi primera lectura los imprimió como vacíos sin que yo notara la diferencia, porque
usaba `$(cat …)` y el `2>&1` del error no se veía. Un parámetro ilegible y un parámetro vacío
son la misma cosa en la salida y cosas distintas en la realidad, y esa es exactamente la
distinción que §25 del prompt maestro obliga a mantener: artefacto vacío ≠ resultado válido.** `ERROR`.

**⇒ `PROVEN_DERIVED. Consecuencia sobre `243`: `amdgpu_drv.c:155` declara
`int amdgpu_gtt_size = -1; /* auto */` y eso es un hecho del código, pero el valor efectivo en
runtime sigue sin estar observado, porque el parámetro que lo publica no es legible sin `root`.
La conclusión de `243` sigue siendo válida porque el default del código no depende de haber
leído sysfs, pero el valor en vivo queda `NOT_OBSERVED` y no `PROVEN`.** `PROVEN_DERIVED`.

**⇒ Y hay dos lecturas que sí son legibles y merecen registrarse por lo que son:
`disable_cu` y `virtual_display` devuelven `(null)`, que es un parámetro de tipo `charp` con
puntero nulo, no un entero mal leído. Es la clase de artefacto que hace que un parser numérico
produzca basura sin avisar.** `PROVEN`.

## 5 · Lo que queda abierto

**⇒ `NOT_OBSERVED`: los valores efectivos de `gttsize`, `gartsize`, `vramlimit` y `moverate` en
esta máquina. La ruta existe pero necesita privilegios.** `NOT_OBSERVED`.

**⇒ `NOT_DETERMINED`: si el tamaño real del anillo GFX en runtime es 2048 dwords. La fórmula lo
predice y las tres ramas dan el mismo valor, pero no hay lectura del `ring_size` ya
construido.** `NOT_DETERMINED`.

```text
PENDIENTE=257-1 | HALLAZGO=257-*.md | ESTADO=NOT_DETERMINED
           | NECESITA=/sys/kernel/debug/dri/1/amdgpu_ring_gfx  (card1 es la AMD, ver HARDWARE-FINGERPRINT.md)
           | ALCANZABLE_SIN_ROOT=NO_MEDIDO
```

**⇒ `PROVEN_DERIVED. Y ese `card1` es exactamente la trampa que `HARDWARE-FINGERPRINT.md`
registró: los índices de `cardN` no coinciden con los del bus PCI, y `card0` es la Intel. Un
error de índice en una ruta de debugfs da lectura vacía y se interpreta como «no hay dato», que
es un falso `NOT_OBSERVED` sobre la iGPU.** `PROVEN_DERIVED`.

**⇒ `NOT_DETERMINED`: por qué el comentario de `gfx_v8_0.c:6878` dice 215 y sus propias constantes
dicen otra cosa. Ninguna de las cuatro(sumadas, con y sin el doble conteo del `* 5`, y con y
sin las 16 IBs) da 215, y con 16 IBs ningún número entero de IBs produce exactamente 215 desde
las constantes actuales. Lo más probable es que el comentario sea anterior a un cambio en las
partidas, pero eso es hipótesis, no medida.** `NOT_DETERMINED`.

**⇒ `PROVEN_DERIVED. Con esto §H tiene por primera vez una medición de runtime de la
configuración de submission, que es la variable que §52 nombra `SUBMISSION-bound` y la primera
que un driver propio puede cambiar con un solo parámetro.** `PROVEN_DERIVED`.

## 6 · Errores propios registrados en esta nota

**⇒ `ERROR`. Sumé a mano las 18 partidas de `emit_frame_size` y obtuve 87; el programa da 109,
luego 177 y luego 172 según cómo se trate `VI_FLUSH_GPU_TLB_NUM_WREG * 5`. Cuatro cifras
distintas para la misma suma. Es la sexta vez que un número calculado mentalmente discrepa del
programa, y ya no es casualidad: es que la operación es de 18 sumandos y mi fiabilidad en eso es
nula.** `ERROR`.

**⇒ `ERROR`. Mi primer parser de `emit_frame_size` usó `.*` sobre los comentarios
multilínea de `gfx_v8_0.c:6884-6886`, que van a tres líneas, y por eso extrajo los números de
la línea siguiente como si fueran partidas del presupuesto. Un comentario que ocupa tres líneas
no es un comentario, es un caso especial del parser.** `ERROR`.

**⇒ `ERROR`. Conté el `5` de `VI_FLUSH_GPU_TLB_NUM_WREG * 5` dos veces: una como resultado de la
multiplicación y otra como operando suelto, porque sustituí el nombre de la macro por `15` y
dejé el `* 5` intacto. El arreglo fue sustituir la expresión entera, no el operando.** `ERROR`.

**⇒ Y el patrón de los tres es el mismo de siempre: la conclusión se escribe antes de que el
programa termine, y aquí además la conclusión correcta es la que menos importa, porque la
cuantización del anillo hace que ninguno de los cuatro valores cambie el resultado.** `ERROR`.