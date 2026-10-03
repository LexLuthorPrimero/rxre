# 928 — `282-1`: la ruta de texel existe y da el mismo resultado que el buffer, pero no se puede medir fuera de caché

Estado del instrumento: `VALIDADO`, con ventana declarada. Estado de `282-1`: `DEFERRED_BY_MISSING_OBSERVABILITY`.
Alcance: la RX 550 de esta placa, Polaris12/GFX8.1, RADV, Mesa de este equipo.
AUTORIA=AGENTE-SMU
Instrumentos: `vulkan_compute_probe.c` con `--tex`, `texchain.comp`, `texdump.comp`, `texconst.comp`.

## Qué se quería

`282` medió que una lectura encadenada se costea a 3,013 GB/s, 1,51 veces el techo de PCIe, y que
**da el mismo tiempo en VRAM y en RAM**. El discriminante que la propia nota `282` proponía era una
`VkImage` en vez de un `VkBuffer`: una imagen tiene su propia ruta de texel, y si esa ruta difiere,
la diferencia localiza el camino.

La pregunta es de `§H`: si la lectura no distingue dónde están los datos, el coste no está en el
transporte de datos.

## Cómo está construido, y por qué así

La única diferencia entre las dos-armed es **de dónde lee la cadena**. Todo lo demás es idéntico a
propósito:

- mismos `constant_id` que `chain.comp` (0 `ITERS`, 1 `WSIZE`, 2 `STEPS`), así que la
  especialización existente del banco aplica sin cambios;
- mismo `hash`, misma cadena, mismo `acc`;
- **la salida sigue yendo al storage buffer** en `d[WSIZE + i]`. Por eso el modelo del host de la
  cadena sigue siendo válido y el control de contenido significa exactamente lo mismo en las dos
  ramas. Si la salida fuera también por la imagen, el control compararía dos rutas y no probaría
  nada sobre la lectura;
- mismo patrón, Initialization por `vkCmdCopyBufferToImage` fuera del reloj.

Dos decisiones que hubo que justificar en vez de suponer:

**`r32ui`, no `rgba32ui`.** Un uint por texel son 4 B por acceso, los mismos 4 B que `d[idx]`. Con
`rgba32ui` un `texelFetch` traería 16 B de los que se usaría uno, y la razón de bytes por acceso
dejaría de coincidir entre las dos rutas: el experimento mediría dos cosas.

**`usampler2D`, no `uimage2D`.** `usampler2D` es el sampler combinado que corresponde a
`VK_DESCRIPTOR_TYPE_SAMPLED_IMAGE`, que es la ruta que se quiere medir. `uimage2D` obligaría a
`STORAGE_IMAGE`, que es otro camino y otro experimento. Y `usampler2D` no admite calificador de
formato, lo cual es correcto: los 4 B por texel los fija el `VkFormat` de la imagen, en tiempo de
ejecución, no el shader.

## El resultado que sí se ha obtenido

**Las dos rutas dan resultados bit a bit idénticos.** Con el control de contenido activo y el mismo
modelo del host:

```
storage buffer (binding 0)   256 de 256 dwords coinciden con el modelo
imagen r32ui    (binding 1)  256 de 256 dwords coinciden con el modelo
```

Eso es la mitad de `282-1`, y es un hecho sólido: la imagen recibe exactamente el mismo patrón, el
índice `i` del shader llega al texel `i`, y la cadena sobre la imagen produce el mismo resultado que
sobre el buffer. La ruta de texel está characterizeada.

## La ventana, y por qué es el problema

Barrido con el binario sano, con el control de contenido en cada punto:

| imagen | `rowPitch` | volcado | cadena completa |
|---|---|---|---|
| 1 KiB | 1024 | 256/256 | 256/256 |
| 4 KiB | 4096 | 256/256 | 256/256 |
| 16 KiB | 16384 | 256/256 | 256/256 |
| 64 KiB | 65536 | 256/256 | 256/256 |
| 256 KiB | 0 | 0/256 | 0/256 |
| 1 MiB | 0 | 0/256 | 0/256 |
| 4 MiB | 0 | 0/256 | 0/256 |
| 16 MiB | 0 | 0/256 | 0/256 |

La frontera está en 64 KiB, y `rowPitch` pasa a 0 **exactamente** en el mismo punto donde el
contenido deja de cuadrar.

La L3 de esta CPU es de 8 MiB. **64 KiB cabe entero en caché.** El único tamaño en el que la ruta de
texel funciona es un tamaño en el que no se está midiendo la memoria.

Corrijo aquí una conclusión que yo mismo había escrito mal. Al principio tomé `rowPitch == 0` por un
campo que el driver no rellena y cambié el abortar por una observación, convencido de que estaba
confundiendo «no lo sé» con «no está». La correlación exacta entre `rowPitch == 0` y el fallo de
contenido dice otra cosa: **no es un campo vacío, es un síntoma del mismo fallo.** El portón
original, por una vez, decía algo real; lo que no decía era por qué.

## La medición que no se reporta

Dentro de la ventana, apareada, 41 repeticiones, control de contenido activo en las dos ramas:

```
storage buffer (binding 0)   mediana=0,000158 s  sigma=0,000054 s (34,5 %)   1,6591 GB/s
imagen r32ui    (binding 1)  mediana=0,000119 s  sigma=0,000015 s (12,3 %)   2,2029 GB/s
diferencia de medianas = 0,000039 s    sigma maximo = 0,000054 s
razon ruido/ganancia = 1,40
```

**`INCONCLUYENTE`.** El ruido es 1,40 veces la diferencia. El banco lo dice, el runner no lo
publica, y no hay número que reportar aquí. Anotarlo sería exactamente el error que `282` ya
cometió una vez y que corrigió.

Además, aunque separara, no respondería a `282`: 64 KiB es caché, y `282` habla de 3 GB/s contra un
techo de PCIe.

## Instrumentos

- `vulkan_compute_probe.c`: bandera `--tex`. Con la bandera apagada no cambia nada, y se comprobó que
  el caso conocido de `chain.spv` sigue dando 256/256. El layout de descriptor, el pool y la
  escritura de descriptors pasan a ser de dos bindings, y el binding 0 se escribe **siempre**.
- `texchain.comp`: la cadena leyendo por `texelFetch`. Compila; el SPIR-V muestra
  `OpImageFetch ... Lod %int_0`, sin filtrado.
- `texdump.comp`: control de la configuración del propio banco. Lee el texel `i` y lo escribe en el
  SSBO, para que se compare con el patrón. Sin él, un banco que mide la ruta de texel no distingue
  «la ruta de texel es más lenta» de «la imagen no tiene lo que debería».
- `texconst.comp`: sonda que escribe una constante sin leer la imagen. Sirve para dividir el espacio
  de hipótesis en dos: si una constante tampoco llega, el fallo no es de la lectura.
- `bench.py --selftest`: 12 de 12, `exit=0`. El parche no rompió el banco.

## Errores propios de esta iteración

Seis, y todos de la misma familia: **un instrumento que parece funcionar y no está midiendo lo que
dice medir.** Ninguno dio error de API; todos dieron un número o un cero.

1. **La bandera quedó después de un `continue`.** El bucle de banderas tiene
   `if (strncmp(argv[i], "--rep=", 6)) continue;`, así que `--tex` colocado justo debajo era código
   muerto. Sin línea `IMAGEN`, sin imagen, y el banco funcionando con normalidad. Es el mismo
   defecto que se llevó por delante la línea del despacho en `607`.

2. **Moví la escritura de `binding 0` dentro del `else` de `--tex`.** Con la bandera encendida el
   storage buffer se quedaba sin descriptor: `vkAllocateDescriptorSets` devolvía éxito, el
   despacho no producía nada, y el readback daba ceros. El control informaba «el resultado no es el
   esperado», que es el síntoma, y no «el binding 0 no está escrito», que es la causa.

3. **Al sustituir el portón borré la creación de la `imageView`.** Estaba entre el portón y el
   `printf`. Con `iv == VK_NULL_HANDLE` el descriptor apunta a una vista nula y el despacho no
   produce nada. Sin `IMAGEN` en la salida, que era la única señal.

4. **Metí la creación de la imagen después de la escritura del descriptor**, que necesita la vista.
   Los tres errores de compilacion no eran de la API: eran de nombres mal escritos.

5. **`VkImageSubresourceLayout` no existe.** Se llama `VkSubresourceLayout`. Lo inventé sin buscarlo
   en la cabecera instalada. `VK_IMAGE_LAYOUT_DESCRIPTOR` tampoco existe; para un sampled image es
   `VK_IMAGE_LAYOUT_SHADER_READ_ONLY_OPTIMAL`.

6. **El barrido de la ventana estaba mal por partida doble.** Primero pasé `items=1024` con
   `wsize=256`, que viola el invariante `wsize >= items` y que el banco rechazaba correctamente; yo
   lei ese rechazo como un fallo de la ruta de texel. Despues un script con `subprocess` no
   produjo salida, y declaro «el porton pasa» donde la corrida directa abortaba.
     banco discrepante: cuando un script y una corrida directa no coinciden, la corrida directa gana.**

Un patrón que se repite y que conviene mirar de frente: en los cuatro primeros errores **ninguna
llamada de Vulkan falló**. El conjunto se asignó bien, la vista se creó bien, la imagen se enlazó
bien. Lo que faltaba era una cosa presente en el camino, y su ausencia se manifestó como un
resultado medible pero equivocado. Un banco que solo comprueba que las llamadas devuelvan éxito no
comprueba nada sobre lo que midió.


## Lo que queda abierto

- **Cablear `texdump.spv` como prefacio obligatorio de toda corrida con `--tex` en `bench.py`.** Es
  la acción siguiente y es barata. Con el patrón actual, el runner no puede distinguir una ruta de
  texel válida de una imagen vacía.
- **`282-1` sigue abierta.** No por falta de instrumento: existe, y valida. Por falta de
  observabilidad a escala: la ruta de texel no funciona por encima de 64 KiB en esta placa con
  Vulkan, y 64 KiB es caché. Quedan dos vías y ninguna es barata: una imagen teselada
  (`VK_IMAGE_TILING_OPTIMAL`) con una copia de host a teselas, cuyo coste hay que medir aparte para
  no contaminar la comparación; o un banco en Metal/RADV fuera de Vulkan.
- ~~**`282-2`**: si el kernel puede leerse y escribirse sin carrera. Sin tocar.~~
  **RANCIOSO: cerrado en `283`, que partió el buffer en dos regiones disjuntas y pasó de
  0/40 a 40/40. Lo arrastré aquí cinco notas después del cierre.**
