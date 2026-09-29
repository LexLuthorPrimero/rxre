# 006 — P-9: cómo separar decodificación BC3 por hardware de decodificación por software

**Ámbito**: `08-ARQUITECTURA/` — IA-3 (Arquitecto)
**Fecha**: 2026-09-29 · **Ronda**: 9
**Resuelve**: `P-9` de `004-fallback-sin-rasterizador.md` §6
**Estado**: `RESUELTO` por lectura de código fuente + aritmética verificada. El experimento
  de Fase 3 sigue siendo necesario; lo que cambia es qué se espera de él y qué control necesita.
**Clasificación de trabajo**: `READ_ONLY/EVIDENCE` (grep sobre árbol Mesa local + Python).
  **No** he ejecutado nada en la GPU, ni benchmarks, ni shaders.

---

## 0. El reframe

`004` §6 formulaba P-9 como «**¿cómo se verifica** que la decodificación la hizo el hardware?».
Esa formulación es incorrecta, y su incorrección es la razón por la que P-9 parecía irresoluble.

`AGENTS.md` §Falsificación no pide *demostrar* una hipótesis rival: pide **nombrar la observación
que la refutaría**. La pregunta operativa no es «¿cómo pruebo que es hardware?» sino:

> **¿Qué resultado del experimento sería incompatible con que la decodificación la hiciera el
> driver por software?**

Sin esa formulación no hay criterio de éxito, porque «no veo señales de software» no es una
medida. Con ella, P-9 tiene respuesta y la respuesta es barata: **no hace falta ningún contador,
ni `vkGetBufferDeviceAddress`, ni timeline semaphores, ni medir latencia.**

## 1. Respuesta corta

**La lectura del código fuente de Mesa descarta la hipótesis rival por construcción.**

En Mesa 26.2, `radeonsi` y `RADV` **no contienen ningún descompresor BC3 en CPU**. Verificado:

```
$ grep -rn "dxt5_rgba\|dxt5_srgba\|u_format_s3tc" src/gallium/drivers/radeonsi/   → sin resultados
$ grep -rn "dxt5_rgba\|dxt5_srgba\|u_format_s3tc" src/amd/vulkan/                → sin resultados
```

Es decir: el único decodificador BC3 por software de Mesa está en el camino de **llvmpipe**
(`src/gallium/auxiliary/gallivm/lp_bld_format_s3tc.c`), y llvmpipe es **otro driver**, no una
ruta alternativa dentro de radeonsi. Un contexto radeonsi **no tiene** a dónde caer si su
hardware no sabe decodificar: la textura se manda a la texture unit o el muestreo falla.

Árbol usado: `/home/lucas/mesa`, `git describe` = `26.1-branchpoint-1415-gc5e413533f4`,
`VERSION` = `26.2.0-devel`. **No** es el árbol del binario instalado
(`mesa-dri-drivers-26.2.3-1.fc44.x86_64`) — ver §5, es la principal salvedad de este documento.

## 2. La trampa de nombres que casi me hace responder mal

`radeonsi` tiene una función llamada `gfx6_decompress_textures` (`gfx/si_blit.c:811`) y
`si_decompress_color_texture` (`gfx/si_blit.c:563`). El nombre dice «decompress». **No tiene nada
que ver con BC3.**

Es *fast-clear*: la textura tiene un buffer CMask o un FMASK de MSAA, o DCC, y "decomprimir"
significa materializar ese valor de fast-clear en la superficie real. La guarda lo dice
(`si_blit.c:568-571`):

```c
/* CMASK or DCC can be discarded and we can still end up here. */
if (!tex->cmask_buffer && !tex->surface.fmask_size &&
    !vi_dcc_enabled(tex, first_level))
   return;
```

Y `assert(sctx->gfx_level < GFX11)` en `:567` más el `if (sctx->gfx_level == GFX10_3)` en `:848`
confirman que el descompresor es de la era pre-GFX11, cuando CMask/DCC existían. El prefijo
`gfx6_`/`gfx11_` son variantes del mismo mecanismo de fast-clear por generación.

**Un grep ingenuo de "decompress" en radeonsi produce una advertencia falsa.** Si hubiera
respondido con eso, habría dicho «el driver puede descomprimir BC3 en software» — que es falso, y
que habría bloqueado el proyecto sin motivo.

## 3. Por qué la hipótesis rival no es «llvmpipe se cuela dentro de radeonsi»

Es una hipótesis distinta, y la recepción la formuló bien. Vale la pena fijarla:

- **Riesgo real, distinto:** que el *contexto* creado no sea el que creemos. `DRI_PRIME=1` elige
  un dispositivo, pero si la selección falla, el contexto puede caer a otro driver sin error
  visible. Ese es exactamente el fallo de `F4-AD-23`, y lo cubre `V-A`/`V-B` leyendo
  `GL_RENDERER`, que para radeonsi incluye el nombre de la GPU.
- **Lo que verifiqué y no verifiqué:**
  - `MESA_VK_DEVICE_SELECT` / `VK_LOADER_DEVICES_SELECT` no se usaron. La selección fue por
    PCI identity en el propio programa (`004` §3.1), no por variable de entorno. La
    correspondencia sesión↔`1002:699f` la establece el `deviceID`, no el entorno.
  - La ruta GL de `test_hardware_bc3.c` **sí** depende de que `DRI_PRIME=1` seleccione bien. Esa
    ruta tiene un riesgo que la de Vulkan no tiene, y es un argumento más a favor de Vulkan.
  - `GL_RENDERER` no es consultable antes de tener contexto; no hay forma de comprobar la
    selección antes de crear el contexto. Se comprueba **después**, y si falla se aborta (V-A).

## 4. La aritmética del rival: llvmpipe NO es ni truncamiento ni redondeo

Aquí está el resultado que da valor al experimento, y que no esperaba.

Si alguien ejecutara el test de rampa sobre **llvmpipe** creyendo que mide el mismo hardware,
obtendría una tercera respuesta, distinta de las dos hipótesis de `AD-11`. Reproduje la
aritmética exacta de `lp_build_lerpdxta` (`lp_bld_format_s3tc.c:817-877`) en Python y la comparé
con las dos predicciones sobre **los 136 686 pares (a0,a1,i) donde spec y trunc difieren**:

| llvmpipe coincide con… | Pares |
|---|---|
| spec Microsoft `+3`/`+2` | 42 170 (30.8 %) |
| truncamiento (bcdec) | 93 867 (68.6 %) |
| **ninguna de las dos** | **649 (0.47 %)** |

Detalle de la aritmética de llvmpipe: no interpola con la fórmula de la especificación. Usa
pesos fijos de 16 bits, `weight = 255*64/5` o `255*64/7`, hace `w = (weight*(code-1))>>6` y luego
`a0 + ((a1-a0)*w)>>8`. Es una aproximación con error propio, sesgada hacia truncamiento pero no
igual a él.

**Esto convierte el control de `004` §6 en un discriminante fuerte.** La idea original era
débil —«si la iGPU y llvmpipe dan lo mismo, es sospechoso»—. Ahora es concreta: llvmpipe es un
**tercero conocido**, y se puede predecir su salida sin ejecutarlo. Si el experimento sobre la
RX 550 produce un resultado que coincide con llvmpipe en los 649 casos donde llvmpipe no coincide
con nadie, eso sí sería una señal fuerte de software. Y si produce spec o trunc de forma
uniforme, no hay contaminación de llvmpipe.

**Consecuencia de diseño para el test de Fase 3:** añadir llvmpipe como **tercer predictor
explícito** y reportar el breakdown de cuatro categorías, no de tres. Con el corpus actual
(64 bloques, 5 en la rama `a0<=a1`) el poder de discriminación es bajo. El corpus de `003` §2
cubre las dos ramas pero 64 bloques no alcanzan para 649 casos excepcionales. Ver §6.

## 5. Salvedades — lo que este documento NO establece

- **El árbol de Mesa no es el binario instalado — y la vía para verificarlo por binario está
  CERRADA.** `/home/lucas/mesa` es `26.1-branchpoint-1415-gc5e413533f4` / `VERSION
  26.2.0-devel`; el driver que corre es `mesa-dri-drivers-26.2.3-1.fc44`. Misma serie menor,
  **commit no verificado igual**. Que `radeonsi` no tenga descompresor BC3 en CPU en este árbol
  **no lo establece** para el binario instalado. `PLAUSIBLE`, no `OBSERVED` para el host.

  **`Q-3` se intentó y es `FAIL` por método**, no por resultado. Ver §5.1. **No reintentar con
  `nm -D`, `strings` ni búsqueda de constantes**: se midió que no discriminan.
- **`llvmpipe` y `radeonsi` son el mismo paquete.** Que llvmpipe tenga el decodificador y
  radeonsi no, dentro del mismo `.so` de distro, es consistente con la lectura del código, pero
  la separación real es entre **ICD de Vulkan** (`libvulkan_radeon.so` vs `libvulkan_lvp.so`,
  paquetes distintos que *sí* verifiqué: `mesa-vulkan-drivers-freeworld`). Para GL
  (`radeonsi_dri.so` vs `swrast`) la atribución es por convención de nombre de driver.
- **No he ejecutado el test de rampa.** No sé qué responderá la RX 550. `AD-12` sigue
  `NOT_DETERMINED`.
- **No he medido contadores, latencia, ni `vkGetBufferDeviceAddress`.** Ver §7, por qué no hacen
  falta.
- **No he verificado** que el árbol `/home/lucas/mesa` sea el que se usó para compilar cualquier

### 5.1 `Q-3` — `FAIL` por método: la verificación por binario **no puede** hacerse aquí

`Q-3` pedía comprobar, sobre el binario instalado, que `radeonsi` no contiene descompresor BC3
en CPU. `nm -D` y `strings` eran el método propuesto. **Medido, no supuesto** (2026-09-29T07:0xZ,
solo lectura):

```
/usr/lib64/dri/radeon_dri.so           NO EXISTE
/usr/lib64/dri/radeonsi_dri.so          symlink 14 B -> libdril_dri.so  (stub, 93 592 B)
/usr/lib64/libgallium-26.2.3.so        55 347 624 B   <-- el driver real esta aqui
  .symtab                              AUSENTE (binario stripped)
  simbolos s3tc|dxt|lerp (.symtab)     0
  simbolos s3tc|dxt|lerp (.dynsym)     0
  cadenas lp_bld_format_s3tc           0
  cadenas util_format_s3tc             0
```

**Por qué el método no puede discriminar.** El paquete `mesa-dri-drivers` de Fedora separa el
driver en una librería compartida sin tabla de símbolos. No hay nombres de función que buscar.
Cero símbolos **no** es evidencia de ausencia de código: en un binario stripped el código está y
el nombre no. Usar `nm -D` aquí razonaría desde la ausencia de evidencia, que es el primer caso
de la tabla de `AGENTS.md` §Falsificación.

**Por qué buscar constantes tampoco.** Es la parte que cierra la vía, y es la razón de
`FAIL` por método y no solo por inutilidad de `nm`:

| Constante | Apariciones (le16) | Percentil vs ruido |
|---|---|---|
| `3264` (`weight5 = 255*64/5`) | 1 111 | 278 |
| **`2331`** (`weight7 = 255*64/7`, valor real) | **159** | **40** |
| `2330` (`weight7`, valor de IA-1) | 196 | 49 |
| **baseline**: 400 valores de 16 bits aleatorios | media **443**, max 29 485, min 22 | — |

En un binario de 55 MB, un valor de 16 bits aparece **~443 veces por azar**. `2331` aparece
**159** veces, **por debajo** del ruido, y el valor **incorrecto** `2330` aparece *más*. Esa
ordenación es la firma del azar, no de un programa. La búsqueda de constantes no discrimina
nada: convertiría ruido en evidencia si alguien la presentara como confirmación.

**Clasificación: `FAIL`.** No es que el driver tenga un descompresor; es que **este método no
puede distinguirlo**. La hipótesis de `F4-AD-27` sigue `PLAUSIBLE` — sostenida por la lectura
del árbol, con la salvedad adicional de que la vía de verificación por binario está cerrada.

**Lo que sí cerraría `Q-3`**: reconstruir el árbol que produjo el binario, o compilar `radeonsi`
desde fuente y comparar. Es trabajo de `@IA-1` y excede mi ámbito (`06-INGENIERIA-INVERSA/`).

**Aviso contra reintentos**: no repetir `nm -D`, `strings` ni búsqueda de constantes esperando
distinto resultado. La measurement está en §5.1 y es reproducible.


  build del proyecto. `mesa-26.2.2-build` existe en `/home/lucas` y podría ser otro árbol.

## 6. Requisito nuevo para el test de Fase 3

Con P-9 resuelto por lectura, el test de `003` §3 necesita un cambio: **el predictor software
llvmpipe pasa a ser una cuarta categoría de comparación, calculada offline** (el algoritmo está
en `lp_bld_format_s3tc.c:817-877`, es determinista y no necesita GPU).

| # | Cambio | Motivo |
|---|---|---|
| R-1 | Predictor `llvmpipe` como cuarta categoría, escrito **independiente** de los otros dos | si compartiera fórmula con otro, no discriminate (mismo principio que `N4`) |
| R-2 | Reportar las **cuatro** categorías con conteos | «mixto» deja de ser una etiqueta ambigua |
| R-3 | El corpus debe cubrir los 649 pares donde llvmpipe no coincide con nadie | si no, el control no tiene potencia |
| R-4 | Un resultado llvmpipe puro se reporta como **`CONTAMINATED_LLVMPIPE`**, no como un hallazgo | sería un fallo del entorno, no una propiedad del hardware |

## 7. Las tres preguntas de la recepción, respondidas

| Pregunta | Respuesta | Base |
|---|---|---|
| ¿Qué observación sería incompatible con decodificación por software? | Un resultado que coincida con el predictor llvmpipe en los 649 pares donde llvmpipe es único frente a spec y trunc. Y, estructuralmente: que radeonsi no tenga descompresor BC3 en CPU | §1, §4 |
| ¿Hay registros, timing o comportamiento que solo el hardware pueda producir? | **No lo usaría, y no hace falta.** `gpu_busy_percent` da `EBUSY` en este host; `/sys/kernel/debug/dri/` da `EPERM`; el nodo KFD `polaris12` tiene `perf/` **vacío**. El timing no es concluyente por sí solo —`004` §6 ya lo decía— y aquí no hay ni contadores ni relojes utilizables | medición propia, §8 |
| ¿`vkGetBufferDeviceAddress` o timeline semaphores para medir latencia? | **No.** `vkGetBufferDeviceAddress` responde a "¿la dirección es de dispositivo?", no "¿quién decodificó?". Los timeline semaphores miden orden y sincronización de submits, no el origen aritmético de un texel. Ninguno de los dos observa la decodificación. Serían complejidad sin poder de discernimiento | razonamiento |
| ¿`DRI_PRIME=1` garantiza la GPU discreta, o puede caer a CPU? | **No lo garantiza por sí solo**, pero el riesgo es de *contexto equivocado*, no de decodificación por software: si cae, cae a **radeonsi en la iGPU** o a **llvmpipe**, y en ambos casos `GL_RENDERER` lo delata. La ruta Vulkan no depende de `DRI_PRIME` en absoluto —el propio programa elige por PCI identity— y por eso no tiene esa debilidad | `004` §3.1, `V-A`/`V-B` |

## 8. Lo que medí para responder §7 fila 2

Comandos, todos de solo lectura, 2026-09-29T06:4xZ:

```
cat /sys/bus/pci/devices/0000:01:00.0/gpu_busy_percent   → EBUSY
ls /sys/kernel/debug/dri/                                → EPERM
ls /sys/class/kfd/kfd/topology/nodes/1/perf/             → vacío
cat /sys/class/kfd/kfd/topology/nodes/1/name             → polaris12
```

Nodo KFD: `node0` sin nombre, `node1` = `polaris12` → la RX550 es el nodo 1, coherente con
`1002:699f`. `renderD129` es legible por el usuario (grupo `render`), `card1` no (grupo `video`).

`pcie_bw` existe pero devuelve `560 0 128`, valores de ancho de enlace, no un contador de
actividad. `pp_dpm_sclk` sí es legible y muestra 8 estados (214–1071 MHz) — pero medir si el
reloj sube al decodificar BC3 sería un benchmark, y `AGENTS.md` §Safety lo prohíbe sin
autorización. **No lo hago, y no hace falta para P-9.**

## 9. Estado de P-9

| Elemento | Antes | Ahora |
|---|---|---|
| Hipótesis rival | «el driver puede decodificar en software» | «el contexto creado no es el que creemos» |
| Separación | `NOT_DETERMINED` | lectura de código + aritmética verificada (§1, §4) |
| Bloquea Opción A (compute) | sí | **no** — la A ya está `NOT_AVAILABLE` por `STORAGE_IMAGE` |
| Bloquea Opción C (GL) | sí | **no del todo**: el contexto se verifica por `GL_RENDERER` (V-A), y el contaminante conocido es llvmpipe, detectable por el predictor de §4 |
| Bloquea camino principal (Vulkan) | sí | **no**: la selección es por PCI identity en el propio programa, no por variable de entorno |
| Contadores GFX8 requeridos | sí | **no** — y además no son accesibles aquí (§8) |
| `AD-12` | `NOT_DETERMINED` | **`NOT_DETERMINED`** — P-9 resuelto no cierra AD-12 |

**Lo que P-9 resuelve es si el experimento es interpretable. No es el experimento.** `AD-12` sigue
necesitando la medición de la rampa en la RX 550, y eso es Fase 3, no este documento.

## 10. Lo que pido a otras IAS

| # | Para | Petición | Bloquea |
|---|---|---|---|
| `Q-1` | `@IA-2` | En el probe, añadir el predictor llvmpipe como cuarta categoría (R-1, R-2) | la interpretabilidad de Fase 3 |
| `Q-2` | `@IA-2` | Ampliar el corpus para cubrir los 649 pares donde llvmpipe difiere de ambos (R-3) | igual |
| `Q-3` | `@IA-1` | **RETIRADA — `FAIL` por método** (§5.1). Sustituto: reconstruir el árbol del binario, o compilar `radeonsi` desde fuente y comparar | convertiría `PLAUSIBLE` en `OBSERVED` |
| `Q-4` | `@IA-1` | Solo informativo: si el árbol de `/home/lucas/mesa` es el mismo del build del proyecto, o si `mesa-26.2.2-build` es otro árbol | salen en §5 |
