# 004 — Especificación del probe F1 y fallback sin rasterizador

**Ámbito**: `08-ARQUITECTURA/` — IA-3 (Arquitecto)
**Fecha**: 2026-09-29 · **Ronda**: 6
**Resuelve**: `F1` de `003-fase3-pipeline-grafico.md`, y el plan B si `F1` falla
**Destinatario de la implementación**: `@IA-2` (o quien tenga ámbito de código de prueba)

---

## 1. Qué decide este documento

`003` diseñó el experimento completo y dejó `F1` como requisito previo:

> ¿`VK_FORMAT_BC3_UNORM_BLOCK` soporta `SAMPLED_IMAGE` en **esta** GPU?

`F1` decide el **método entero**. Si falla, el camino «VkImage BC3 → sampler → FBO» no aplica y
hay que usar el método de §5.

**Este documento no implementa el probe.** Es la especificación que IA-2 debe cumplir al
escribirlo. Sin ella, el probe puede pasar por la GPU equivocada y dar un falso positivo.

## 2. Valores exactos, de fuente primaria

Verificados en `/usr/include/vulkan/vulkan_core.h` (Vulkan 1.4.341):

```
VK_FORMAT_BC3_UNORM_BLOCK              = 137
VK_FORMAT_BC3_SRGB_BLOCK               = 138      ← NO usar, ver §3.3
VK_FORMAT_FEATURE_SAMPLED_IMAGE_BIT    = 0x00000001
```

Y la identidad del dispositivo objetivo, ya usada por el agreement test de la Fase 2:

```
vendorID = 0x1002   deviceID = 0x699f   (RX 550 / Polaris 12, RADV)
```

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

**Por qué el filtro es obligatorio, y no una comodidad.** Esta host expone **tres** dispositivos
Vulkan:

| Índice | Dispositivo | Consecuencia si se elige mal |
|---|---|---|
| 0 | AMD Radeon RX 550 (`1002:699f`) | correcto |
| 1 | Intel HD Graphics 4600 (`8086:0412`) | capability de otra GPU |
| 2 | llvmpipe (`10005:0000`) | **software: `SAMPLED_IMAGE` casi seguro** |

Elegir por índice de enumeración, o quedarse con el primer dispositivo que devuelva algo, produce
un **falso positivo** que invalida la medición entera: el software rasterizador implementa BC3 en
CPU y **siempre** soporta el formato. El proyecto ya pagó este precio antes, y por eso el
agreement test de la Fase 2 identifica por PCI identity con el mismo criterio.

**`P5` es un fallo, no un caso raro.** Si la RX 550 no aparece, el probe debe **abortar** y reportar
qué dispositivos vio. Dejar el `target` en el primero disponible sería el error completo.

### 3.2 Consulta del formato

```
P6  vkGetPhysicalDeviceFormatProperties(target, VK_FORMAT_BC3_UNORM_BLOCK, &fp)
P7  si (fp.optimalTilingFeatures & VK_FORMAT_FEATURE_SAMPLED_IMAGE_BIT) != 0:
        RESULTADO = SAMPLED
    si no:
        RESULTADO = NO_SAMPLED  →  §5 (fallback)
```

`VK_FORMAT_FEATURE_SAMPLED_IMAGE_BIT` es `0x1` (`vulkan_core.h:2675`). `VK_FORMAT_BC3_UNORM_BLOCK`
es `137` (`vulkan_core.h:1945`).

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
  [0] 1002:699f  AMD Radeon RX 550 (RADV POLARIS12)      <- OBJETIVO por PCI identity
  [1] 8086:0412  Intel(R) HD Graphics 4600
  [2] 10005:0000 llvmpipe
dispositivo seleccionado   : 1002:699f  (por identity, NO por indice)
optimalTilingFeatures     : 0x................
  SAMPLED_IMAGE            : SI
  STORAGE_IMAGE            : NO
  COLOR_ATTACHMENT         : NO
  TRANSFER_SRC/DST         : SI
VEREDICTO: SAMPLED   ->  el metodo de 003 §3 aplica
```

**`0x` en minúsculas y el valor completo**, no un «sí/no» suelto: permite comparar entre corridas
y detectar cambios de driver.

## 4. Autovalidación del probe — antes del veredicto

Un probe que devuelve «sí» sin comprobar nada es peor que uno que no existe.

| # | Comprobación | Qué evita |
|---|---|---|
| V-A | `props.deviceName` se imprime y **contiene** «RX 550» | que el filtro por PCI falle en silencio |
| V-B | El dispositivo elegido **no** es llvmpipe | el falso positivo por software |
| V-C | `n >= 1` y se imprimió la lista completa | filtro que descarta todo y «funciona» |
| V-D | Se imprime el `apiVersion` del loader | estabilidad de la interpretación de flags |

**V-B merece atención**: el filtro por PCI ya lo cubre, pero es una segunda barrera con coste
cero. Si alguien cambia el filtro por índice, V-B salta.

## 5. Fallback: medir el sampler sin rasterizador

Si `F1` devuelve `NO_SAMPLED`, el camino de `003` §3 no aplica. **Esto no significa que no se pueda
medir el sampler** — significa que hay que llegar a la decodificación BC3 por otra puerta.

### 5.1 Opción A — compute shader con `imageLoad`

```
VkImage BC3 (STORAGE_IMAGE)  →  compute shader  →  SSBO  →  vkCmdCopyBufferToHost  →  CPU
```

- Requiere `VK_FORMAT_FEATURE_STORAGE_IMAGE_BIT` en lugar de `SAMPLED_IMAGE_BIT`.
- El shader sí escribe (`imageStore`), pero escribe **lo que lee**: no hay aritmética.
- **Riesgo**: en algunos drivers el `imageLoad` de un formato bloqueado **no pasa por el
  sampler de hardware** y se decodifica por software. Eso invalidaría la medición tanto como
  llvmpipe.
- **Por eso**: si se usa esta vía, hay que **verificar que la decodificación es de hardware**, no
  de software. Cómo se verifica está en `NOT_DETERMINED` (`P-9`, ver §6).

### 5.2 Opción B — copia directa, sin shader

```
VkImage BC3  →  vkCmdCopyImageToBuffer  →  memoria host  →  CPU
```

- Solo sirve si el hardware transcodea BC3 al copiar. **No está garantizado**; muchos drivers
  solo permiten copias entre formatos iguales.
- Si funciona, es la vía **más limpia**: ni shader, ni sampler, ni rasterizador. El valor leído
  sale del transcoder del hardware.
- Es la primera que probaría: mínima superficie, máximo valor diagnóstico.

### 5.3 Opción C — solo con GL, no Vulkan

El camino de `test_hardware_bc3.c` (escrito, compila, nunca ejecutado): DXT5 como color
attachment de un FBO en OpenGL, leído con `glReadPixels`. Es exactamente el mismo principio que
`003` §3, y `DRI_PRIME=1` ya está verificado como ruta a `radeonsi`.

**Es la opción con menos incógnitas**, porque el punto de bloqueo histórico fue el **contexto
GLX desde un programa propio**, no el formato. Y ese bloqueo puede haberse resuelto con las
cabeceras que ya están instaladas.

### 5.4 Prioridad de fallback

| Orden | Vía | Por qué primero |
|---|---|---|
| 1 | **C — OpenGL + FBO** | principio idéntico al de `003`, y el bloqueo histórico era de contexto, no de formato |
| 2 | **B — copia directa** | sin shader ni sampler; máxima limpieza si el hardware transcodifica |
| 3 | **A — compute `imageLoad`** | **solo** si se demuestra que la decodificación es por hardware |

**A va última a propósito.** Es la que parece más directa y es la que más fácilmente produce un
resultado que parece hardware y no lo es.

## 6. Pregunta que queda abierta en el fallback

**P-9**: ¿cómo se verifica empíricamente que una decodificación BC3 la hizo el **hardware de
textura** y no el driver por software?

Esto no es teórico. Es la diferencia entre `AD-12` resuelto y `AD-12` resuelto **con una mentira**.
Sin `P-9`, la opción A no es utilizable, y la opción C necesita el mismo control.

Pistas a explorar, ninguna cerrada:

- El hardware tiene un contador de **operaciones de textura**; si el bloque se decodifica por
  software, el contador no se mueve. `F4` ya confirma que hay problemas de acceso a `GFX8`
  counters, así que esta vía puede no estar disponible.
- La **latencia** de la muestra cambia según el tamaño del recurso. No es concluyente por sí sola.
- La comparación con `llvmpipe`: si el resultado de la iGPU y el de llvmpipe son **idénticos**
  hasta el bit, eso es sospechoso. No es prueba de software, pero es una señal.

## 7. Criterios de éxito de esta especificación

| # | Criterio |
|---|---|
| Q1 | El probe identifica el dispositivo por PCI identity, y **aborta** si no lo encuentra |
| Q2 | `V-A`..`V-D` pasan antes de emitir veredicto |
| Q3 | Imprime el valor **completo** de `optimalTilingFeatures` |
| Q4 | Si `NO_SAMPLED`, dice **explícitamente** cuál de los tres fallbacks toca, y por qué ese |
| Q5 | `VK_FORMAT_BC3_UNORM_BLOCK` (137), nunca `SRGB` (138) |

## 8. Lo que este documento no establece

- **No** dice si `SAMPLED_IMAGE` está presente. Eso es lo que `F1` va a medir.
- **No** garantiza que el fallback funcione. Cada vía tiene su propia incógnita, y la Opción A
  tiene una_condition que `P-9` debe resolver.
- **No** decide a qué vía se recurre. La decisión depende de `F1`, y el orden de §5.4 es una
  recomendación, no una decisión tomada.
