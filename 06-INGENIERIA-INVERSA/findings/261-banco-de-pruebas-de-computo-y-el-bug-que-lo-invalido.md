# 261 · La capacidad que faltaba para §H: un banco de pruebas de cómputo, con su control negativo y el bug que casi lo invalida

```text
CLASSIFICATION=IMPLEMENTATION+VALIDATION+MEASUREMENT · TRACK=TOOLING + RUNTIME
CORPUS=RESEARCH/working/linux-7.1.3 + /sys/class/drm/card1/device/hwmon/hwmon1
HARDWARE_SCOPE=HOST-C/RX550/0000:01:00.0
WORK_CLASS=WRITE_LOCAL (herramienta propia) + NIVEL 1 (carga de GPU)
MODIFICATIONS_CORPUS=0 · WRITE_EXECUTION=carga de cómputo Vulkan, sin escrituras de hardware
GPU INTACTA · NIVEL DE PERMISOS=1
```

> **`CORREGIDA` por `270`.** El banco con el que se midió esta nota metía la copia del patrón
> dentro de la región cronometrada. La configuración de esta nota se resuelve exactamente —
> 137,44 GFLOP son `items = 2²⁷ = 134.217.728`, `iters = 64`, `nacc = 8` — y la copia eran
> **0,43724 s de los 0,62855 s publicados: el 69,6%**. Los 218,7 GFLOPS no son el rendimiento de
> este kernel ni casi.
>
> El `INVALID_RESULT` de esta nota **se mantiene**, pero la causa que aquí se enuncia no es la
> buena: no es que el kernel mida latencia, es que **el bucle está siendo eliminado**. Re-medido
> con el banco corregido, el mismo kernel da 6304,5 GFLOPS, que es 2,9 veces el techo que tendría
> esta GPU incluso con 16 CUs a `sclk` de 1063,02 MHz medido en `hwmon1`. Ver `270` §4.2.

## Qué resuelve

**Cierra `PENDIENTE=258-2`: sí se puede cargar esta GPU, y `mclk` sí responde.** `PROVEN`.

**⇒ `PROVEN`. Bajo carga de cómputo sostenida, `mclk` sube de 300 MHz a 625 MHz —no a 1500—,
mientras `sclk` queda clavado en 1071 MHz con varianza cero.** `OBSERVED`.

**⇒ `PROVEN`. Y el contrato de medición tiene una desviación del 0,01% sobre 30 pasadas, lo que
lo hace capaz de resolver variaciones superiores al 0,03%.** `MEASUREMENT`.

**⇒ `ERROR`: el banco de pruebas reportaba una configuración que no ejecutaba. El argumento
`iters` de la línea de comandos llegaba al `printf` y a ningún otro sitio; el bucle estaba
horneado en el SPIR-V. Todas las primeras mediciones fueron de 64 iteraciones mientras el
programa declaraba 4096.** `ERROR`.

## 1 · La herramienta y por qué hacía falta

**⇒ `PROVEN_ABSENT`: no había ninguna forma de ejecutar trabajo en el ASIC objetivo. La
precondición que `258` declaró —«una carga que eleve mclk y sclk»— no era ejecutable con nada
de lo que había en el sistema.** `PROVEN_ABSENT`.

**⇒ Lo que sí había, medido: `vkcube` y `vkcubepp` instalados, `/usr/include/vulkan/vulkan.h`
presente, `glslangValidator`, `spirv-dis`, `spirv-val`, `spirv-opt`, gcc 16.2.1 y
`/dev/dri/renderD129` abierto en `O_RDWR`. Faltaba la pieza: un programa de cómputo.** `PROVEN`.

**⇒ `PROVEN_DERIVED. Y la vía correcta es cómputo y no gráficos, por una razón concreta:
`vkcube` exige una superficie WSI y esta AMD no tiene display conectado —`233` registró cero
CRTC— mientras que el cómputo Vulkan no necesita superficie y funciona por el render node.** `PROVEN_DERIVED`.

**⇒ Artefactos creados, todos propios y en el directorio de herramientas del proyecto:**

```text
08-ARQUITECTURA/tools/vulkan_compute_probe.c   el banco de pruebas
08-ARQUITECTURA/tools/probe.comp              el shader GLSL
08-ARQUITECTURA/tools/probe.spv               su compilación SPIR-V
08-ARQUITECTURA/tools/vcp                     el binario
```

## 2 · La regla que el programa impone, y su control negativo

**⇒ `PROVEN`. El banco aborta si no encuentra exactamente `1002:699f`, y también aborta si el
dispositivo seleccionado es de tipo CPU. No hay ruta de reserva.** `PROVEN`.

**⇒ Y la razón está medida, no supuesta: `vulkaninfo` lista tres dispositivos, y el tercero es
`llvmpipe (LLVM 22.1.8, 256 bits)` de tipo `PHYSICAL_DEVICE_TYPE_CPU`. Una herramienta de
banco de pruebas que degrade ahí mide el procesador de la máquina, que es un `i7-4790`, y
devuelve un número plausible.** `PROVEN`.

**⇒ `PROVEN`. El control negativo se ejecutó invirtiendo el objetivo a `10005:0000`, que es
llvmpipe, y el programa abortó con código de salida 3 y el mensaje «ABORTO: el dispositivo
seleccionado es de TIPO CPU». El objetivo real da código de salida 0.** `PROVEN`.

**⇒ `ERROR`: mi primera versión del control usó `$?` después de un pipe con `tail` y `sed`, que
mide el código de salida del último elemento de la tubería, no el del programa. El control
pareció fallar cuando en realidad abortaba bien. Repetido sin tubería, `exit code real = 3`.** `ERROR`.

**⇒ Ése es exactamente el fallo de §26 —«nunca asumir que el código de salida del consumidor es
el del productor»— y es la segunda vez en esta sesión que me ocurre: la primera con `head` en la
verificación de citas, ahora con `tail` en un control de validación.** `ERROR`.

## 3 · El bug que invalidaba las mediciones

**⇒ `ERROR`. El banco imprimía `CONFIG items=... iters=4096` y ejecutaba 64 iteraciones.** `ERROR`.

```c
61   uint32_t iters = (argc > 1) ? strtoul(argv[1],...) : 64;   /* llega al printf */
211  printf("CONFIG    items=%u iters=%u ...", items, iters, ...);
```

**⇒ `PROVEN`. El bucle estaba en el GLSL, compilado al SPIR-V con la constante horneada. El
SPIR-V de 64 iteraciones mide 1244 bytes y el de 4096 mide 1260: la diferencia es
exactamente la codificación del valor.** `PROVEN`.

**⇒ `PROVEN_DERIVED. La consecuencia medida era un ritmo imposible. Con los valores que el
programa declaraba, 137,44 GFLOP en 0,62855 s dan 218,7 GFLOPS, pero el cálculo que hice al
principio usó las 4096 iteraciones declaradas y produjo 40 TFLOP/s, que es unas 36 veces el techo
físico de esta GPU. Un número 36 veces imposible es la señal de que el modelo de la carga, no el
hardware.** `PROVEN_DERIVED`.

**⇒ La corrección es la que corresponde a la regla de «el artefacto esperado es el que se
consume»: `VkSpecializationMapEntry` con `constant_id = 0` en el GLSL y
`cpci.stage.pSpecializationInfo` en el C, para que el `ITERS` declarado llegue al shader.** `PROVEN`.

**⇒ Y la prueba de que la corrección funciona no es que compile: es que el tiempo escale con el
argumento.** `PROVEN`.

| `ITERS` | mediana (s) | razón frente a 64 | razón de iteraciones |
|---|---|---|---|
| 64 | 0,002176 | 1,00 | 1 |
| 256 | 0,010024 | 4,61 | 4 |
| 1024 | 0,039491 | 18,14 | 16 |
| 4096 | 0,157360 | 72,30 | 64 |
| 16384 | 0,628544 | 288,79 | 256 |

**⇒ `PROVEN. El cociente constante es 1,13 sobre las cinco filas: el trabajo escala linealmente
y hay un coste fijo por pasada del 13%. Antes de la corrección el tiempo era idéntico para 64 y
para 4096, lo que es lo que delató el fallo.** `PROVEN`.

## 4 · La medición, con su contrato

**⇒ `MEASUREMENT`. 30 pasadas de 4.194.304 items con `ITERS` 16384, tras 5 de calentamiento, con
muestreo concurrente de hwmon a 20 Hz:** `MEASUREMENT`.

```text
tiempo por pasada   min=0,62847   mediana=0,62855   max=0,62866 s
desviación típica   0,00006 s = 0,01% de la mediana
integridad          30 de 30 pasadas devolvieron tiempo
```

```text
muestreo concurrente, 773 muestras
  mclk  min=300   mediana=300   max=625   MHz
  sclk  min=1071  mediana=1071  max=1071  MHz
  ppt   min=13,12 mediana=17,03 max=17,04  W
  temp  min=56,0  mediana=60,0  max=63,0  C
```

**⇒ `PROVEN`. Tres cosas que sólo se ven con la carga sostenida:** `OBSERVED`.

**⇒ Una: `sclk` está clavado en 1071 MHz con varianza cero en las 773 muestras. 1071 MHz es el
nivel 7 de `pp_dpm_sclk`, el más alto de los ocho.** `PROVEN_DERIVED`.

**⇒ Dos: `mclk` con mediana de 300 MHz y máximo de 625, y nunca 1500. El nivel de memoria sube
algo pero no a su máximo.** `PROVEN_DERIVED`.

**⇒ Y la tercera es la que explica las dos anteriores: este kernel es una cadena dependiente.**
`PROVEN_DERIVED`.

```glsl
for (uint k = 0u; k < ITERS; k++)
    a = a * 1664525u + 1013904223u;
```

**⇒ La iteración k+1 no puede empezar hasta que termine la k, así que el límite no es el ancho de
la ALU sino la latencia de una multiplicación. Con 16384 iteraciones y unos 4 ciclos de latencia
por multiplicación, cada item ocupa unos 65.536 ciclos, unos 61 µs a 1,071 GHz.** `PROVEN_DERIVED`.

**⇒ `PROVEN_DERIVED. Y de ahí sale la firma completa: un kernel dependiente consume la ALU con
independencia nula y no genera tráfico de memoria, así que el controlador de memoria no tiene
nada que hacer y el SMU deja la memoria en su nivel bajo mientras sube el reloj de shader. Un
reloj de shader al máximo con memoria al mínimo no es una contradicción, es la firma de una
carga que no toca la memoria.** `PROVEN_DERIVED`.

**⇒ Consecuencia: las 218,7 GFLOPS de esta nota NO son una medida de rendimiento de cómputo. Es
una medida de latencia entera con un techo de ocupación. Para medir rendimiento hace falta un
kernel con varias cadenas independientes, y ese kernel todavía no existe.** `PROVEN_DERIVED`.

**⇒ `PROVEN_DERIVED. Y hay un dato térmico que no era esperable: la temperatura sube de 47-48 °C
en reposo a 60 °C de mediana y 63 °C de máximo, con sólo 17,03 W, que es el 48,7% del tope de
35 W. El calor de esta máquina no viene de la potencia consumida.** `PROVEN_DERIVED`.

**⇒ `PROVEN_DERIVED. Y eso deja en evidencia el dato de `258`: `222` derivó
`usOperatingTempMaxLimit = 43` y `258` ya midió 46-47 °C en reposo. Con carga, la tarjeta está 20
grados por encima de ese límite.** `PROVEN_DERIVED`.

## 5 · Contradicción que esta nota abre — **RESUELTA en `272`**

> **`RESUELTA` por `272`.** No era una contradicción de valor sino de categoría semántica.
> `cg_mask` es una máscara de banderas de **clock gating** (`u64`, `AMD_CG_SUPPORT_*`,
> consumida en `amdgpu_device.c:2111` como `adev->cg_flags &= amdgpu_cg_mask`); el `0x1e` es
> el **bitmap de CUs activos** del GFX (`u32`, producido en `gfx_v8_0.c:7069` como
> `~INACTIVE_CUS & create_bitmask(max_cu_per_sh)`). Tipo, productor, consumidor y fase de init
> distintos. El techo de cómputo queda en **1088,5 GFLOPS** con los 8 CUs activos a `sclk`
> 1063,02 MHz. Ver `272` §1 y §4.

**⇒ `CONTRADICTION` **[REFUTADA en `272`]**. `/sys/module/amdgpu/parameters/cg_mask` lee
`18446744073709551615`, o sea `0xFFFFFFFFFFFFFFFF`, con todos los bits activos. El estado del
proyecto declara para esta placa «8 CUs; CU masks 0x1e», y `0x1e` tiene cinco bits, no
dieciséis.** `CONTRADICTION`.

**⇒ `NOT_DETERMINED` **[RESUELTO en `272`]**: cuál de las dos cifras es la correcta, o si
describen cosas distintas. No lo he resuelto y no lo voy a resolver por coherencia narrativa.
`cg_mask` puede ser una máscara de habilitación con la lectura «todos habilitados» por defecto,
o puede ser de un dominio de unidades distinto al de la máscara de CU del GFX.** `NOT_DETERMINED`.

**⇒ Y esa cifra importa: el techo de cómputo de la GPU se calcula a partir del número de CU y
del ancho de la ALU, así que sin resolverla no se puede dar ningún techo en FLOPS.** `NOT_DETERMINED`.

## 6 · Lo que esta nota deja establecido y lo que no

**⇒ `PROVEN`, con 30 muestras y 0,01% de desviación:** la GPU acepta carga de cómputo real
por la vía Vulkan con RADV; `sclk` se fija en su nivel máximo; `mclk` sube a 625 MHz pero no a
1500; el consumo llega a 17 W de 35; la temperatura llega a 63 °C.

**⇒ `INVALID_RESULT`: cualquier afirmación de rendimiento.** La carga es una cadena dependiente
y mide latencia, no anchura de cómputo. El número de 218,7 GFLOPS no es una cifra de throughput
y no debe usarse como tal.

**⇒ `NOT_DETERMINED`: la clasificación de cuello de botella de §52.** Falta un kernel de
ancho de cómputo y uno de ancho de memoria para separar las dos cosas. La herramienta ya está
construida y validada; sólo faltan los dos shaders.

```text
PENDIENTE=261-1 | HALLAZGO=261-*.md | ESTADO=NOT_DETERMINED
           | NECESITA=CORPUS  (kernel de cadenas independientes, sin revision pendiente)
           | ALCANZABLE_SIN_ROOT=si
```

**⇒ `NOT_DETERMINED`: el número de CU, y por tanto todo techo en FLOPS.** `NOT_DETERMINED`.

**⇒ `PROVEN_DERIVED. Y la herramienta cumple el requisito de §38 de ser un activo reutilizable:
cambiar el shader cambia lo que se mide sin tocar el programa, y el programa valida que el
dispositivo es el correcto en cada ejecución. El siguiente kernel es un fichero GLSL, no un
programa nuevo.** `PROVEN_DERIVED`.

## 7 · Errores propios registrados en esta nota

**⇒ `ERROR` ×4, y todos son los mismos que ya vienen de `243`, `246`, `253` y `257`:**

1. Escribí el banco de pruebas sin verificar que el `iters` de la línea de comandos llegara al
   shader. El programa era plausible, compilaba, y el control negativo pasaba. Sólo fallaba en
   el mundo, y lo delató un cálculo imposible, no una revisión.
2. Usé `$?` después de una tubería para comprobar el código de salida del abort.
3. Calculé 40 TFLOP/s, 36 veces el techo físico, a partir de una configuración que el programa
   declaraba y no ejecutaba.
4. Antes de compilar escribí `VkPhysicalDeviceProps`, que no existe; el compilador lo cazó.

**⇒ `PROVEN_DERIVED. El cuarto fue el más barato de todos: el compilador lo dijo en un segundo.
Los otros tres no los dijo nadie. El control que faltaba no era sobre el dispositivo, era sobre
el propio programa: ¿coincide lo que declara con lo que ejecuta? Ese control no lo escribí y
tuve que construirlo después, cuando el daño estaba hecho.** `ERROR`.

**⇒ Y el orden importa para la siguiente: el control negativo del dispositivo lo hice bien y a
propósito; el control de la configuración propia lo hice tarde y por accidente, prompted por
un número imposible. Un banco de pruebas necesita dos controles, y el segundo es el que se
olvida.** `ERROR`.