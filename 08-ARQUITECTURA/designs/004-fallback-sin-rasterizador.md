# 004 — Fallback sin rasterizador: especificación del probe F1 y las tres vías alternativas

**Ámbito**: `08-ARQUITECTURA/` — IA-3 (Arquitecto)
**Fecha**: 2026-09-29 · **Ronda**: 6 (especificación) · **Ronda 8** (finalizada con medición)
**Resuelve**: `F1` de `003-fase3-pipeline-grafico.md`, y el plan B si `F1` falla
**Destinatario de la implementación**: `@IA-2` (o quien tenga ámbito de código de prueba)
**Estado de `F1`**: `PASS` — medido, ver `../validations/2026-09-29-f1-format-capability.md`

> **Cambio de estado en esta revisión.** `F1` era `NOT_DETERMINED` cuando se escribió este
> documento. Se midió (`../validations/2026-09-29-f1-format-capability.md`, 2026-09-29T06:23Z):
> `VK_FORMAT_BC3_UNORM_BLOCK` **sí** soporta `SAMPLED_IMAGE` en `1002:699f`. **El camino de
> `003` §3 aplica.** Las tres vías de §5 se conservan porque §5.1 quedó **refutada** y las otras
> dos siguen siendo el plan B ante una regresión de driver, pero su justificación cambió.

---

## 1. Qué decide este documento

`003` diseñó el experimento completo y dejó `F1` como requisito previo:

> ¿`VK_FORMAT_BC3_UNORM_BLOCK` soporta `SAMPLED_IMAGE` en **esta** GPU?

`F1` decide el **método entero**. Medido: **sí**. La sección §3 se conserva íntegra porque el
probe de IA-2 **sigue siendo necesario** — una medición ajena no sustituye a un probe con
autovalidación, y `F4-AD-23` (abortar si no se encuentra el objetivo) sigue sin ejercerse.

## 2. Valores exactos, de fuente primaria

Verificados por mí en `/usr/include/vulkan/vulkan_core.h` (`VK_HEADER_VERSION 341`, línea 69;
paquete `vulkan-headers-1.4.341.0-1.fc44.noarch`):

| Símbolo | Valor | Fuente primaria |
|---|---|---|
| `VK_FORMAT_BC3_UNORM_BLOCK` | `137` | `vulkan_core.h:1945` |
| `VK_FORMAT_BC3_SRGB_BLOCK` | `138` | `vulkan_core.h:1946` — **NO usar**, ver §3.3 |
| `VK_FORMAT_FEATURE_SAMPLED_IMAGE_BIT` | `0x00000001` | `vulkan_core.h:2675` |
| `VK_FORMAT_FEATURE_STORAGE_IMAGE_BIT` | `0x00000002` | `vulkan_core.h:2676` |
| `VK_FORMAT_FEATURE_COLOR_ATTACHMENT_BIT` | `0x00000080` | `vulkan_core.h:2682` |
| `VK_FORMAT_FEATURE_TRANSFER_SRC_BIT` | `0x00004000` | `vulkan_core.h:2688` |
| `VK_FORMAT_FEATURE_TRANSFER_DST_BIT` | `0x00008000` | `vulkan_core.h:2689` |
| `VK_FORMAT_FEATURE_2_SAMPLED_IMAGE_FILTER_MINMAX_BIT` | `0x00010000` | `vulkan_core.h:7224` |
| `VK_FORMAT_FEATURE_2_COPY_IMAGE_INDIRECT_DST_BIT_KHR` | `0x0008000000000000` | `vulkan_core.h:7284` |

Identidad del dispositivo objetivo, la misma que usa el agreement test de la Fase 2:

```
vendorID = 0x1002   deviceID = 0x699f   (RX 550 / Polaris 12, RADV)
```

### 2.1 Corrección: el orden de enumeración de `004` estaba invertido

La versión anterior de este documento (§3.1) listaba:

| Índice | Dispositivo | ❌ real |
|---|---|---|
| 0 | AMD Radeon RX 550 (`1002:699f`) | **Intel HD Graphics 4600** |
| 1 | Intel HD Graphics 4600 (`8086:0412`) | **AMD Radeon RX 550** |
| 2 | llvmpipe (`10005:0000`) | llvmpipe ✓ |

Medido con `vulkaninfo --summary` (2026-09-29T06:23Z):

```
GPU0: 8086:0412  Intel(R) HD Graphics 4600 (HSW GT2)   INTEGRATED_GPU
GPU1: 1002:699f  AMD Radeon RX 550 (RADV POLARIS12)     DISCRETE_GPU
GPU2: 10005:0000 llvmpipe (LLVM 22.1.8, 256 bits)       CPU
```

**El documento acertó al exigir el filtro por PCI y se equivocó en el ejemplo** — y el ejemplo es
lo que se copia. Peor: el índice 0 real es la **iGPU**, así que un probe escrito copiando el
ejemplo habría medido la Intel.

**No son 4 dispositivos**: `dzn_icd.i686.json` está instalado pero el loader lo rechaza
(`Received return code -9 from call to vkCreateInstance in ICD /usr/lib64/libvulkan_dzn.so.
Skipping this driver.`). Son 3.

## 3. Algoritmo del probe, paso a paso

### 3.1 Selección del dispositivo — **el paso que más se va a equivocar**

```
P1  vkCreateInstance(...)                    → VK_SUCCESS, si no: abortar con diagnóstico
P2  vkEnumeratePhysicalDevices(inst, &n, NULL)
P3  vkEnumeratePhysicalDevices(inst, &n, devs)
P4  for i in 0..n-1:
        vkGetPhysicalDeviceProperties(devs[i], &props)
        if props.vendorID == 0x1002 AND props.deviceID == 0x699f:
            target = devs[i]; break
P5  if target == NULL: ABORTAR
```

**Por qué el filtro es obligatorio, y no una comodidad — ahora con medición.** Esta host expone
**tres** dispositivos Vulkan, y **los tres reportan `SAMPLED_IMAGE` para BC3**:

| Índice | Dispositivo | `SAMPLED_IMAGE` BC3 | Consecuencia si se elige mal |
|---|---|---|---|
| 0 | Intel HD 4600 (`8086:0412`) | **sí** | capability de otra GPU |
| 1 | **RX 550 (`1002:699f`)** | **sí** | correcto |
| 2 | llvmpipe (`10005:0000`) | **sí** | **software: implementa BC3 en CPU** |

Elegir por índice habría dado `SAMPLED` **y habría acertado por accidente**, sin ninguna señal de
error. Ese es el peor modo de fallo posible en un probe: no un falso negativo que se ve, sino un
acierto que no prueba nada. `F4-AD-23` queda confirmado empíricamente.

**`P5` es un fallo, no un caso raro.** Si la RX 550 no aparece, el probe **aborta** y reporta qué
dispositivos vio. Dejar el `target` en el primero disponible sería el error completo.

### 3.2 Consulta del formato

```
P6  vkGetPhysicalDeviceFormatProperties(target, VK_FORMAT_BC3_UNORM_BLOCK, &fp)
P7  si (fp.optimalTilingFeatures & VK_FORMAT_FEATURE_SAMPLED_IMAGE_BIT) != 0:
        RESULTADO = SAMPLED
    si no:
        RESULTADO = NO_SAMPLED  →  §5 (fallback)
```

Valor esperado en esta host, ya medido: **`0xd401`** (los cinco bits de Vulkan 1.0:
`0x1 | 0x400 | 0x1000 | 0x4000 | 0x8000`). Si el probe usa
`vkGetPhysicalDeviceFormatProperties2` e incluye `MINMAX`, verá **`0x1d401`**. Ambos son
correctos; lo que importa es que imprima el número y no un «sí/no».

### 3.3 Sobre `BC3_SRGB`

**No usar `VK_FORMAT_BC3_SRGB_BLOCK`** (138). Aplicaría una transformación sRGB al decodificar, y
los valores leídos no serían los del bloque: contaminaría exactamente lo que se quiere medir.

Solo tiene sentido como **control adicional**: si `SAMPLED` funciona y además `SRGB` funciona,
probar ambos con el mismo corpus confirmaría que el pipeline de muestreo es el esperado. Pero el
resultado de `AD-12` se toma **siempre** de `UNORM`.

### 3.4 Salida mínima del probe

```
PROBE v1 — VK_FORMAT_BC3_UNORM_BLOCK capability
dispositivos enumerados   : 3
  [0] 8086:0412   Intel(R) HD Graphics 4600 (HSW GT2)     <- iGPU
  [1] 1002:699f   AMD Radeon RX 550 (RADV POLARIS12)       <- OBJETIVO por PCI identity
  [2] 10005:0000  llvmpipe (LLVM 22.1.8, 256 bits)         <- software
dispositivo seleccionado   : 1002:699f  (por identity, NO por indice)
optimalTilingFeatures     : 0x0000d401
  SAMPLED_IMAGE            : SI
  BLIT_SRC                 : SI
  SAMPLED_IMAGE_FILTER_LINEAR : SI
  TRANSFER_SRC/DST         : SI
  STORAGE_IMAGE            : NO     <- refuta el fallback A, ver 5.1
  COLOR_ATTACHMENT         : NO     <- BC3 no puede ser attachment en Vulkan, ver 5.5
linearTilingFeatures      : 0x8000000000000000  (COPY_IMAGE_INDIRECT_DST, sin SAMPLED)
VEREDICTO: SAMPLED   ->  el metodo de 003 §3 aplica
```

El valor de `linearTilingFeatures` **no** es decorativo: es lo que obliga a
`VK_IMAGE_TILING_OPTIMAL`, ver §5.6.

## 4. Autovalidación del probe — antes del veredicto

Un probe que devuelve «sí» sin comprobar nada es peor que uno que no existe. Y en este caso el
riesgo es mayor de lo que parecía: como **los tres** dispositivos dicen `SAMPLED`, un probe sin
autovalidación tiene un 2/3 de probabilidad de acertar por casualidad.

| # | Comprobación | Qué evita |
|---|---|---|
| V-A | `props.deviceName` se imprime y **contiene** «RX 550» | que el filtro por PCI falle en silencio |
| V-B | El dispositivo elegido **no** es llvmpipe | el falso positivo por software |
| V-C | `n >= 1` y se imprimió la lista completa | filtro que descarta todo y «funciona» |
| V-D | Se imprime el `apiVersion` del loader | estabilidad de la interpretación de flags |
| **V-E** | Se imprime `linearTilingFeatures` y se comprueba que **no** tiene `SAMPLED_IMAGE` | crear la imagen con tiling linear y no saber por qué falla |
| **V-F** | Se comprueba `apiVersion >= 1.1` si se va a usar `Properties2` | interpretar mal flags de 2.0 |
| **V-G** | `rc != 0` ante fallo de cualquier `P*` | el fallo de `F4-AD-7` §2: un CI verde sobre `[FAIL]` |

**V-B merece atención**: el filtro por PCI ya lo cubre, pero es una segunda barrera con coste
cero. Si alguien cambia el filtro por índice, V-B salta.

**V-G no es opcional** y viene de un fallo ya medido en este proyecto: un test que imprimía
`[FAIL]` por `stderr` devolvía `rc=0`, y un CI reportaba verde (`F4-AD-7`).

## 5. Fallback: medir el sampler sin rasterizador

`F1 = PASS`, así que **ninguna de estas tres vías hace falta hoy**. Se conservan por dos razones:
`§5.1` quedó **refutada por medición** y hay que dejarlo escrito para que nadie la intente, y
las otras dos siguen siendo el plan B si una actualización de Mesa retira `SAMPLED_IMAGE` de BC3.

### 5.1 Opción A — compute shader con `imageLoad` — `NOT_AVAILABLE` por medición

```
VkImage BC3 (STORAGE_IMAGE)  →  compute shader  →  SSBO  →  vkCmdCopyBufferToHost  →  CPU
```

**Refutada, no arriesgada.** Requiere `VK_FORMAT_FEATURE_STORAGE_IMAGE_BIT`, y en `1002:699f`
para `VK_FORMAT_BC3_UNORM_BLOCK` ese bit **no está** en `optimalTilingFeatures`
(medido: `../validations/2026-09-29-f1-format-capability.md` §3).

La versión anterior de este documento la ponía en «riesgo» por si la decodificación pasaba por
software en vez de por la textura. Ese era el riesgo correcto pero menor: **el driver no ofrece la
vía en absoluto**.

| Estado | Valor |
|---|---|
| `VK_FORMAT_FEATURE_STORAGE_IMAGE_BIT` en BC3/`1002:699f` | `NOT_SET` |
| Opción A | `NOT_AVAILABLE` — no es una elección, es una imposibilidad |
| Refutación | una versión de Mesa que añada `STORAGE_IMAGE` a BC3 la reabre; el commit del driver se detecta comparando el valor impreso |

**Consecuencia colateral**: `P-9` (§6) ya no bloquea a la Opción A, porque la Opción A no existe.
`P-9` sigue bloqueando a la Opción C.

### 5.2 Opción B — copia directa, sin shader

```
VkImage BC3  →  vkCmdCopyImageToBuffer  →  memoria host  →  CPU
```

- `TRANSFER_SRC`/`TRANSFER_DST` **sí** están en BC3 (`0xd401` los incluye).
- **Pero**: que los bits estén no significa que el hardware **transcode** BC3 a RGBA8 al copiar.
  Una copia es byte a byte; si se pide RGBA8 al otro lado, la pregunta es si el driver decodifica.
  La especificación no lo garantiza para formatos comprimidos y **no lo he medido**.
- Si transcodea, es la vía **más limpia**: ni shader, ni sampler, ni rasterizador. El valor leído
  sale del transcoder del hardware.
- **Es la primera que probaría** si `SAMPLED` se pierde: mínima superficie, máximo valor
  diagnóstico.
- Requiere el mismo control `P-9` que la Opción C.

### 5.3 Opción C — solo con GL, no Vulkan

El camino de `test_hardware_bc3.c` (escrito, compila, **nunca ejecutado** según
`004-IMPLEMENTACION` — ver §7 de este documento para la salvedad): DXT5 como color attachment de
un FBO en OpenGL, leído con `glReadPixels`. Es el mismo principio que `003` §3.

- **Es la única vía que puede usar BC3 como attachment**, porque en Vulkan `COLOR_ATTACHMENT` no
  está para BC3 en esta GPU (§5.5) y en OpenGL la extensión `S3TC` tiene su propio camino.
- El bloqueo histórico era el **contexto GLX desde un programa propio**, no el formato. Y ese
  bloqueo puede haberse resuelto: las cabeceras que falaban ya no son el obstáculo (medido:
  `/usr/include/GL` **no existe** y `pkg-config --exists gl` falla, pero el programa declara sus
  propias entradas y las resuelve por `glXGetProcAddressARB`, que es el camino que `glxgears` usa).
- `DRI_PRIME=1` como ruta a `radeonsi`: afirmación de `daf2f29` (commit propio, ronda 5).
  **No la he re-verificado en esta ronda** — `glxgears` es un benchmark y `AGENTS.md` §Safety no
  lo ejecuta sin autorización. Citada, no medida.

### 5.4 Prioridad de fallback — revisada

| Orden | Vía | Por qué en esa posición |
|---|---|---|
| 1 | **C — OpenGL + FBO** | principio idéntico al de `003`; el bloqueo histórico era de contexto, no de formato; y es la única que puede usar BC3 como attachment |
| 2 | **B — copia directa** | sin shader ni sampler; máxima limpieza **si** el hardware transcodifica, que está sin medir |
| 3 | **A — compute `imageLoad`** | **`NOT_AVAILABLE` por medición.** Desciende a última posición por eliminación, no por prudencia |

**A va última porque no va**: la versión anterior la ponía última «a propósito», por la
posibilidad de una decodificación por software. Esa razón sigue siendo válida **para cuando se
reabra**, y es la razón por la que A sigue en la lista en vez de borrarse. Un cambio de driver
que añada `STORAGE_IMAGE` la reactiva, y entonces vuelve a ser la más traicionera de las tres.

### 5.5 BC3 no puede ser color attachment en Vulkan — cierra una vía de replanteo

Medido: `VK_FORMAT_FEATURE_COLOR_ATTACHMENT_BIT` (`0x80`) **no** está en BC3/`1002:699f`.

`003` §4.1 decía «si el driver rechaza BC3, cambiar de estrategia a copia
`BUFFER→IMAGE→BUFFER`». Correcto en el fondo, pero el texto sugería implícitamente que
BC3-como-attachment era una alternativa. **En Vulkan no lo es, en esta GPU.** El diseño de `003` §3
no lo usaba (BC3 `SAMPLED` → RGBA8 attachment), así que **el diseño principal es válido**; lo que
se cierra es una puerta que nadie tenía intención de cruzar.

### 5.6 `VK_IMAGE_TILING_LINEAR` no sirve — requisito añadido

Medido: `linearTilingFeatures` de BC3 en `1002:699f` contiene **un solo** bit,
`COPY_IMAGE_INDIRECT_DST_BIT_KHR` (`0x0008000000000000`). **No** `SAMPLED_IMAGE`.

`003` §3 no especificaba el tiling. Un `VkImage` BC3 creado con `VK_IMAGE_TILING_LINEAR` no sería
muestreable, y el fallo aparecería como un error de creación o como una imagen vacía — no como un
`INVALID_FORMAT`.

**Requisito**: `imageTiling = VK_IMAGE_TILING_OPTIMAL`. Comprobación `V-E`.

## 6. Pregunta que queda abierta en el fallback

**P-9**: ¿cómo se verifica empíricamente que una decodificación BC3 la hizo el **hardware de
textura** y no el driver por software?

**Cambio de estado**: con la Opción A refutada (§5.1), `P-9` ya **no** bloquea a la Opción A.
**Sigue bloqueando a la Opción C**, que es la primera del orden. Sin `P-9`, la Opción C puede
producir un número que parece hardware y no lo es — y ese número decidiría `AD-12`.

Esto no es teórico. Es la diferencia entre `AD-12` resuelto y `AD-12` resuelto **con una mentira**.

Pistas, ninguna cerrada:

- El hardware tiene un contador de **operaciones de textura**; si el bloque se decodifica por
  software, el contador no se mueve. `F4` ya confirma que hay problemas de acceso a contadores
  `GFX8`, así que esta vía puede no estar disponible. `NOT_DETERMINED`.
- La **latencia** de la muestra cambia según el tamaño del recurso. No es concluyente por sí sola.
- La comparación con `llvmpipe`: si el resultado de la iGPU y el de llvmpipe son **idénticos**
  hasta el bit, eso es sospechoso. No es prueba de software, pero es una señal. **Ahora hay un
  dato nuevo que la hace más fuerte**: los tres dispositivos reportan el mismo conjunto de
  capabilities BC3 salvo por dos bits, lo que confirma que son rutas de código distintas — pero
  **no** dice nada sobre si la decodificación de la RX 550 es de hardware.
- **Especulación, no evidencia, y la dejo marcada como tal**: un `imageLoad` de un formato
  bloqueado podría resolverse por software en algunos drivers. No lo he medido y no hay forma de
  medirlo aquí sin el contador de §1. `NOT_DETERMINED`.

## 7. Criterios de éxito de esta especificación

| # | Criterio | Estado |
|---|---|---|
| Q1 | El probe identifica el dispositivo por PCI identity, y **aborta** si no lo encuentra | spec §3.1, sin implementar |
| Q2 | `V-A`..`V-G` pasan antes de emitir veredicto | spec §4, sin implementar |
| Q3 | Imprime el valor **completo** de `optimalTilingFeatures` y de `linearTilingFeatures` | spec §3.4 |
| Q4 | Si `NO_SAMPLED`, dice **explícitamente** cuál de las tres vías toca, y por qué ese | spec §5.4 |
| Q5 | `VK_FORMAT_BC3_UNORM_BLOCK` (137), nunca `SRGB` (138) | spec §3.3 |
| **Q6** | `VkImage` BC3 creada con `VK_IMAGE_TILING_OPTIMAL` | **añadido** por medición §5.6 |
| **Q7** | El probe devuelve `rc != 0` ante cualquier fallo | **añadido** por `F4-AD-7` §2 |

**Medido y no depende del probe**: `F1 = PASS` (`SAMPLED`, `0xd401`) —
`../validations/2026-09-29-f1-format-capability.md`.

## 8. Lo que este documento no establece

- **No** dice qué regla de interpolación aplica el sampler. `AD-12` sigue `NOT_DETERMINED`. Que el
  formato sea `SAMPLED` no dice nada de la rampa alfa.
- **No** dice si la Opción B transcodifica. `TRANSFER_SRC/DST` están medidos; el transcode, no.
- **No** dice si la Opción C funciona. El bloqueo histórico de contexto GLX sigue sin resolver
  desde mi última ronda, y la afirmación de que `DRI_PRIME=1` lo resuelve viene de `daf2f29`,
  **citada, no re-verificada**.
- **No** dice si la decodificación es de hardware. `P-9` sigue abierto.
- **No** sustituye al probe. Una medición de formato ajena no ejercita el aborto de `F4-AD-23`.
- **No** afirma nada sobre el rendimiento. Ninguna de estas vías es un benchmark.

## 9. Procedencia de los datos de este documento

Según `F4-AD-24` y `../designs/005-regla-citacion.md`:

| Dato | Grado | Fuente |
|---|---|---|
| `VK_FORMAT_BC3_UNORM_BLOCK = 137` | **medido por mí** | `grep -n` sobre `/usr/include/vulkan/vulkan_core.h:1945`, 2026-09-29T06:2xZ |
| Los 9 valores de bits de §2 | **medido por mí** | `grep -n` sobre `vulkan_core.h`, mismo momento |
| `VK_HEADER_VERSION 341`, `vulkan-headers-1.4.341.0-1.fc44` | **medido por mí** | `grep`, `rpm -q` |
| Orden y contenido de los 3 dispositivos | **medido por mí** | `vulkaninfo --summary`, 2026-09-29T06:23Z |
| `optimalTilingFeatures = 0xd401`, `linearTilingFeatures`, ausencia de `STORAGE_IMAGE` y `COLOR_ATTACHMENT` | **medido por mí** | `vulkaninfo --show-formats`, sha256 `5ff5762b…fffd` |
| `dzn` rechazado por el loader | **medido por mí** | stderr de `vulkaninfo`, mismo momento |
| `mesa-vulkan-drivers-freeworld-26.2.3-1.fc44` provee `libvulkan_radeon.so` y `libvulkan_lvp.so` | **medido por mí** | `rpm -qf` |
| `mesa-vulkan-drivers` no instalado | **medido por mí** | `rpm -q mesa-vulkan-drivers` |
| `/usr/include/GL` no existe, `pkg-config gl` falla | **medido por mí** | `ls`, `pkg-config --exists gl` |
| `test_hardware_bc3.c` nunca ejecutado | **citado** | `004-IMPLEMENTACION`, afirmación de ronda previa; **no verificada por mí** |
| `DRI_PRIME=1` da contexto `radeonsi` | **citado** | `daf2f29` (commit propio, ronda 5); **no re-verificada** |
| `GFX8` counters con problemas de acceso | **citado** | ronda previa vía `F4`; **no verificada por mí** |
| Los tres dispositivos dicen `SAMPLED_IMAGE` para BC3 | **medido por mí** | `vulkaninfo --show-formats`, sección de cada GPU |

**Lo que NO he medido y por tanto no afirmo**: si la GPU ejecuta un shader, si el FBO es completo,
si la rampa alfa del hardware trunca o redondea, si la Opción B transcodifica, si la Opción C
funciona, o si la decodificación es de hardware.
