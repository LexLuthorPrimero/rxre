# 003 — Fase 3: medir el sampler de hardware (AD-12)

**Ámbito**: `08-ARQUITECTURA/` — IA-3 (Arquitecto)
**Fecha**: 2026-09-29 · **Ronda**: 5
**Estado**: diseño completo, ejecución **no** bloqueada por `unbind`
**Resuelve**: `AD-12`, hoy `NOT_DETERMINED`

---

## 0. Corrección al enunciado de la tarea

La tarea parte de que «la ejecución en hardware real sigue bloqueada por F4-AD-15 (requiere
`unbind`)». **Eso es incorrecto, y lo verifiqué antes de aceptar la premisa.**

```
vkcube --gpu_number 1     →  Selected GPU 1: AMD Radeon RX 550 (RADV POLARIS12), rc=0
DRI_PRIME=1 glxgears      →  GL_RENDERER = AMD Radeon RX 550 (radeonsi, polaris12)
```

**Fase 3 no necesita `unbind`.** La medición del sampler la ejecuta el driver **que ya está
cargado** (RADV / radeon si). `F4-AD-15` aplica al **driver propio de Fase 4**, que es otra cosa:
reclamar el dispositivo en exclusiva. Son dos questions distintas y se confundieron.

**Consecuencia**: `AD-12` **no está bloqueada**. Es ejecutable hoy, con el host como está.

**Lo que sí bloquea** a Fase 3, y es real:

| Bloqueo | Estado |
|---|---|
| GLX desde un programa propio (cliente/servidor) | sin resolver — medido en ronda anterior |
| `VkImage` con `VK_FORMAT_BC3_UNORM_BLOCK` como attachment | **sin verificar** |
| `glReadPixels` de un FBO en un contexto propio | **sin verificar** |

Los tres son del **entorno de prueba**, no del diseño. Y los tres se resuelven escribiendo código y
midiendo, no autorizando `unbind`.

---

## 1. Qué se quiere demostrar

`AD-12`: **¿el sampler de textura del Polaris 12 decodifica la rampa alfa de BC3 con truncamiento
o con redondeo `+3`/`+2`?**

Esto no es una curiosidad de documentación. Este proyecto entrega un **encoder**, y el consumidor
del encoder es el hardware. Si el sampler trunca:

- `rx550_compress.c` emite bloques que la RX 550 decodifica distinto de `rx550_decompress_block()`
- el error **viaja dentro del payload del bloque**, no en un informe
- un round-trip contra el decodificador propio **lo oculta por construcción**

Lo que el agreement test de la Fase 2 establece es que **shader y C concuerdan**. Lo que **no**
establece es qué regla sigue el **sampler**: el shader GLSL no es el sampler.

## 2. Principio de método: el shader no participa

Esta es la decisión de diseño que más importa, y es la que hace fiable la medición.

**El valor que se lee del hardware debe salir del sampler, no de una operación aritmética del
shader.** Si el fragment shader calcula algo, una aritmética defectuosa se confunde con un sampler
defectuoso.

Por eso el shader **no calcula nada**: hace `texture(sampler, uv)` y devuelve el valor.

```
VkImage BC3  →  VkSampler  →  fragment shader (solo texture())  →  FBO RGBA8  →  readback
                                                                 ↑
                                              el 100 % de la aritmética es del hardware
```

Un `texture()` es opaco: no hay forma de que el shader altere el resultado. Y en la GPU moderna el
descompresor BC3 es **hardware dedicado** (el texture unit), no instrucciones.

**Consecuencia sobre el corpus**: se reutiliza el de la Fase 1, que cubre **las dos ramas**:

| Rama | Bloques | Qué distingue |
|---|---|---|
| `a0 > a1` | 59 de 64 | rampa de 6 valores, divisor 7, `+3` |
| `a0 <= a1` | 5 de 64 | rampa de 4 valores, divisor 5, `+2`, más `a[6]=0`, `a[7]=255` |

La cobertura de `a0 > a1` es alta, que es justo donde la divergencia truncar/redondear es más
frecuente (ítems 2, 4 y 6 de la rampa de 8).

## 3. Flujo de datos

```
┌─ ENTRADA ─────────────────────────────────────────────────────────┐
│ corpus_compressed.bin    1024 B = 64 bloques BC3, 16 B cada uno  │
│ corpus_cpu_reference.bin 4096 B = 64 × 64 B RGBA (Fase 1)         │
└────────────────────────────────┬──────────────────────────────────┘
                                 │
┌─ SUBIDA ────────────────────────▼──────────────────────────────────┐
│ VkImage  VK_FORMAT_BC3_UNORM_BLOCK                                 │
│   64 bloques = 8×8 bloques = 32×32 texels                           │
│   VK_IMAGE_USAGE_SAMPLED_BIT | VK_IMAGE_USAGE_TRANSFER_DST_BIT     │
│ VkDeviceMemory HOST_VISIBLE (mapeada) ← vkCmdCopyBufferToImage      │
└────────────────────────────────┬──────────────────────────────────┘
                                 │
┌─ MUESTREO ──────────────────────▼──────────────────────────────────┐
│ DescriptorSet: VkSampler (LINEAR, CLAMP_TO_EDGE) + VkImageView      │
│ Fragment shader: layout(location=0) out vec4 c;                      │
│                  void main(){ c = texture(sampler, uv); }            │
│   ← SIN aritmética. Solo texture().                                 │
│ Vertex: fullscreen triangle, sin atributos                          │
└────────────────────────────────┬──────────────────────────────────┘
                                 │
┌─ LECTURA ──────────────────────▼──────────────────────────────────┐
│ VkImage RGBA8_UNORM 32×32 (VkImageUsage COLOR_ATTACHMENT)           │
│ RenderPass: LOAD=CLEAR, STORE=STORE                                 │
│ Framebuffer + Subpass                                              │
│ vkCmdDraw(3, 1, 0, 0)                                              │
│ vkQueueWaitIdle                                                    │
│ vkCmdCopyImageToBuffer → memoria mapeada → CPU                     │
└────────────────────────────────┬──────────────────────────────────┘
                                 │
┌─ COMPARACIÓN ───────────────────▼──────────────────────────────────┐
│ por bloque, por texel, canal alfa:                                  │
│   hw == trunc(x)   → hardware USA TRUNCAMIENTO                      │
│   hw == round(x)   → hardware USA REDONDEO                          │
│   ninguna          → clasificación mixta, REPORTAR, no adivinar     │
└─────────────────────────────────────────────────────────────────────┘
```

**Por qué textura y FBO, y no solo texture → buffer**: un `storage buffer` con
`imageSample`+`imageStore` es posible en GLSL, pero `imageStore` **sí** es una escritura del shader.
Con FBO el único escritor es el rasterizador, que es exactamente el sampler. Menos superficie de
duda.

## 4. Configuración mínima de Vulkan

Elementos, sin valores inventados:

| Objeto | Para qué | Riesgo |
|---|---|---|
| `VkImage` BC3 + `VkImageView` | fuente de la muestra | **ALTO**: ¿el driver acepta BC3 como `SAMPLED`? |
| `VkSampler` | `LINEAR` + `CLAMP_TO_EDGE` | bajo |
| `VkRenderPass` + `VkFramebuffer` | destino RGBA8 | bajo |
| `VkPipelineLayout` + `VkPipeline` | gráfico, VS+FS triviales | medio |
| `VkDescriptorSetLayout` + pool | sampler + image view | bajo |
| `VkCommandPool` + `VkCommandBuffer` | grabación | bajo |
| `VkFence` | espera | bajo |
| `vkCmdCopyBufferToImage` | subida | bajo |
| `vkCmdCopyImageToBuffer` | lectura | bajo |

**SPIR-V del fragment shader**: se compila con `glslangValidator`, **no** con `clang -target
amdgcn`. Es un shader de Vulkan, no el artefacto de Fase 4. Confundir ambos sería el error
`F4-AD-9` repetido.

### 4.1 Requisito previo que decide el método

**`VK_FORMAT_BC3_UNORM_BLOCK` tiene que soportar `VK_IMAGE_USAGE_SAMPLED_BIT`.** Si el driver lo
rechaza, hay que cambiar de estrategia a `vkGetPhysicalDeviceFormatProperties` + copia
`BUFFER→IMAGE→BUFFER` con `vkCmdCopyImageToBuffer` (transcoder hardware, sin rasterizador).

**Este es el primer paso del experimento y su primer resultado.** Se consulta
`vkGetPhysicalDeviceFormatProperties(VK_FORMAT_BC3_UNORM_BLOCK)` y se registra
`optimalTilingFeatures`. Si no incluye `SAMPLED_IMAGE`, el resto del diseño no aplica y hay que
replantear.

## 5. Autovalidación: obligatoria, y con qué objetivo

Sin esto, el fallo es el de la Fase 2 en otra forma: salida vacía leída como resultado.

| # | Comprobación | Qué evita |
|---|---|---|
| S1 | `formatProperties` incluye `SAMPLED_IMAGE` | descubrir al final que el método no aplica |
| S2 | El framebuffer reporta `VK_FRAMEBUFFER_COMPLETE` | attachment inválido |
| S3 | El shader module se crea | GLSL inválido |
| S4 | El corpus subido **coincide byte a byte** con el fichero | staging corrupto |
| S5 | Los **canales RGB de referencia son 0** en todo el corpus | si el sampler devuelve color, el corpus no es el esperado |
| S6 | Los **índices 0 y 1 decodifican a `a0` y `a1` exactos** | caminho de medición roto |
| S7 | El FBO **no** está todo a cero | el shader no ejecutó |

**S6 es la fuerte.** Los índices 0 y 1 no interpolan: son los endpoints literales. Si el sampler no
devuelve exactamente `a0`/`a1`, el problema está en el camino, no en la rampa. **Es el mismo
principio que sostiene la Fase 2.**

**S5** es un control gratuito: el corpus de la Fase 1 fuerza el color a negro, así que RGB debe
salir 0. Cualquier valor distinto significa que el corpus no es el que creemos.

## 6. Control negativo: antes del primer resultado

Sin esto, el test no prueba nada.

| # | Mutante | Detección esperada |
|---|---|---|
| N4 | `round()` replaced por `trunc()` **en el predictor** | cambia la clasificación de **todos** los pares |
| N5 | `.spv` del fragment shader sustituido por uno vacío | S7 falla, o `S3` |
| N6 | omitir `vkCmdWaitFences` | lectura antes de que el hardware escriba → salida a cero |

**N4 es el control decisivo.** Si el predictor y la implementación comparten el mismo
`(k*a0 + m*a1 + r)/d`, el test **no puede** distinguir truncamiento de redondeo. **El predictor debe
estar escrito dos veces, de forma independiente**, o el experimento no vale.

## 7. Criterios de éxito

| # | Criterio | Verificación |
|---|---|---|
| F1 | `VK_FORMAT_BC3_UNORM_BLOCK` soporta `SAMPLED_IMAGE` | `formatProperties` |
| F2 | S1..S7 pasan | salida del validador |
| F3 | N4, N5, N6 se rechazan | control negativo |
| F4 | **Clasificación inequívoca**: trunc **o** redondeo, sin residuo | conteo de las tres categorías |
| F5 | La clasificación es **coherente en las dos ramas** (`a0>a1` y `a0<=a1`) | breakdown por rama |

**F4 con residuo no nulo no es un éxito parcial: es un `NOT_DETERMINED`**, y se reporta como tal.
Sería el caso de que el sampler use una regla que no es ni truncamiento ni redondeo — y eso sería
un hallazgo, no un fallo.

## 8. Resultados posibles y qué implica cada uno

| Resultado | Lectura | Consecuencia |
|---|---|---|
| **Truncamiento** | `bcdec v0.985` coincide con el hardware | **AD-11 refutado en hardware.** El encoder con redondeo emite bloques mal decodificados |
| **Redondeo** | la especificación D3D9 coincide con el hardware | AD-11 confirmado; `bcdec` es el que diverge |
| **Mixto** | regla distinta | `NOT_DETERMINED`. Reportar. **No forzar un veredicto** |
| **No reproducible** | S* falla | corregir el entorno antes de interpretar |

## 9. Relación con Fase 4

**Conexión que sí existe**: los **mismos bloques BC3**.

```
encoder Fase 1 ──▶ corpus_compressed.bin ──┬──▶ Fase 3: VkImage BC3 → sampler de hardware
                                           └──▶ Fase 4: objeto ELF OpenCL C → shader propio
```

Si el sampler **trunca** y mantenemos el redondeo (`F4-AD-12`), entonces el encoder de la Fase 1 y
el sampler de la Fase 4 **no coinciden en la rampa**, y el agreement test de 4B no puede dar 0/4096
por esa causa. **Fase 3 es un prerrequisito logical de Fase 4B**, no un experimento paralelo.

**Conexión que NO existe**: la ejecución de Fase 3 **no** requiere el driver propio. Usa el que ya
está cargado. Por eso no necesita `unbind`.

**Y una advertencia sobre el GPU**: la Fase 3 ejecuta trabajo en la RX 550. `AGENTS.md` prohíbe
benchmarks y cargas no autorizadas sin permiso explícito. Este experimento es una medida puntual
reproducible, no un benchmark, y la autorización de este turno lo cubre. **No se repetirá sin
motivo.**

## 10. Dependencias de Fase 4 — `PENDIENTE-IA-2`

En `reviews/2026-09-29-arch-fase3-requirements.md`. La relevante:

**Si Fase 4 quiere que su driver lea bloques BC3 con la misma semántica, necesita la respuesta de
Fase 3.** No al revés: Fase 3 no necesita nada de Fase 4 para ejecutarse.

## 11. Lo que este documento no establece

- **No** dice si el sampler trunca o redondea. Eso es lo que se va a medir.
- **No** asume que BC3 sea `SAMPLED`-capable. Es `F1`, y si falla, el método cambia.
- **No** promete ejecución. Este documento diseña; el primer resultado será `F1`.
