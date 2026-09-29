# Medición F1 — capacidad de `VK_FORMAT_BC3_UNORM_BLOCK` en `1002:699f`

**Ámbito**: `08-ARQUITECTURA/` — IA-3 (Arquitecto)
**Fecha**: 2026-09-29T06:23Z
**Clasificación de trabajo**: `READ_ONLY/EVIDENCE` (enumeración y consulta de formato; no escribe
en la GPU, no dibuja, no mide rendimiento)
**Resuelve**: `F1` de `003-fase3-pipeline-grafico.md` §7
**Estado**: `F1 = PASS` (`SAMPLED`), con dos restricciones que **no** estaban en el diseño

---

## 1. Qué se midió y con qué

Comando, reproducible:

```
$ vulkaninfo --summary 2>/dev/null | sed -n '/^Devices:/,$p' | grep -E "^GPU|vendorID|deviceID|deviceName|driverName"
$ vulkaninfo --show-formats 2>/dev/null > vk-fmt.txt
```

`vulkaninfo` **Instance Version: 1.4.341**. Artefacto preservado:
`/tmp/opencode/vk-fmt.txt`, 8234 líneas,
sha256 `5ff5762b10386655e9eb34b54d72319451e89c8e67161bf0c5169ace2d03fffd`.

Paquetes (`rpm -qa | grep mesa-vulkan`, `rpm -qf` sobre cada ICD):

| Objeto | Token | Valor medido |
|---|---|---|
| `libvulkan_radeon.so` (RADV) | `DRIVER_PRESENT` | `mesa-vulkan-drivers-freeworld-26.2.3-1.fc44.x86_64` |
| `libvulkan_lvp.so` (llvmpipe) | `DRIVER_PRESENT` | `mesa-vulkan-drivers-freeworld-26.2.3-1.fc44.x86_64` |
| `vulkaninfo`, `vkcube` | `PACKAGE_PRESENT` | presentes, `/usr/bin/` |
| `vulkan-headers` | `PACKAGE_PRESENT` | `vulkan-headers-1.4.341.0-1.fc44.noarch` |
| `mesa-vulkan-drivers` | `PACKAGE_ABSENT` | **no instalado** — pero esto **no** implica que no haya Vulkan |

## 2. Dispositivos enumerados — y una corrección a `004` §3.1

```
GPU0: vendorID 0x8086  deviceID 0x0412  Intel(R) HD Graphics 4600 (HSW GT2)   INTEGRATED_GPU
GPU1: vendorID 0x1002  deviceID 0x699f  AMD Radeon RX 550 (RADV POLARIS12)     DISCRETE_GPU
GPU2: vendorID 0x10005 deviceID 0x0000  llvmpipe (LLVM 22.1.8, 256 bits)       CPU
```

**`004-fallback-sin-rasterizador.md` §3.1 tenía el orden invertido**: ponía `[0]` = RX 550,
`[1]` = Intel, `[2]` = llvmpipe. El orden real es Intel → AMD → llvmpipe. El documento ✅ acertó
en exigir el filtro por PCI identity, ❌ se equivocó en el ejemplo, y el ejemplo es exactamente lo
que alguien copiaría. Corregido en `004` §2.1.

También medido: `dzn_icd` está presente pero el loader lo rechaza
(`terminator_CreateInstance: Received return code -9 from call to vkCreateInstance in ICD
/usr/lib64/libvulkan_dzn.so. Skipping this driver.`), así que **son 3 dispositivos, no 4**.

## 3. El resultado de F1

`1002:699f` (RADV), grupo de formatos comprimidos que contiene `FORMAT_BC3_UNORM_BLOCK`
(vk-fmt.txt:5442-5449):

```
optimalTilingFeatures: count = 7
    FORMAT_FEATURE_2_SAMPLED_IMAGE_BIT                 0x0000000000000001
    FORMAT_FEATURE_2_BLIT_SRC_BIT                      0x0000000000000400
    FORMAT_FEATURE_2_SAMPLED_IMAGE_FILTER_LINEAR_BIT   0x0000000000001000
    FORMAT_FEATURE_2_TRANSFER_SRC_BIT                  0x0000000000004000
    FORMAT_FEATURE_2_TRANSFER_DST_BIT                  0x0000000000008000
    FORMAT_FEATURE_2_SAMPLED_IMAGE_FILTER_MINMAX_BIT   0x0000000000010000
    FORMAT_FEATURE_2_COPY_IMAGE_INDIRECT_DST_BIT_KHR   0x0008000000000000

linearTilingFeatures: count = 1
    FORMAT_FEATURE_2_COPY_IMAGE_INDIRECT_DST_BIT_KHR   0x0008000000000000
bufferFeatures:      None
```

Valores de los bits verificados en `/usr/include/vulkan/vulkan_core.h:7209-7284`
(`VK_HEADER_VERSION 341`, línea 69). `VK_FORMAT_BC3_UNORM_BLOCK = 137` en
`vulkan_core.h:1945`.

**`F1 = PASS`. `SAMPLED_IMAGE` está presente. El método de `003` §3 aplica.**

Palabra `optimalTilingFeatures` de Vulkan 1.0 correspondiente a los 5 bits de 1.0:
`0x1 | 0x400 | 0x1000 | 0x4000 | 0x8000 = ` **`0xd401`**. El probe debe imprimir ese valor si
consulta `vkGetPhysicalDeviceFormatProperties` (API 1.0); verá `0x1d401` si usa
`vkGetPhysicalDeviceFormatProperties2` e incluye `MINMAX`.

## 4. Tres restricciones que el diseño NO contemplaba

### 4.1 `VK_IMAGE_TILING_LINEAR` **no** sirve → la imagen debe ser `OPTIMAL`

`linearTilingFeatures` de BC3 en `1002:699f` contiene **un solo** bit, y no es `SAMPLED_IMAGE`.
`003` §3 no decía qué tiling usar; el código de ejemplo aurait podido usar linear y fallar.

**Requisito añadido**: `VkImage` BC3 con `imageTiling = VK_IMAGE_TILING_OPTIMAL`.

### 4.2 `STORAGE_IMAGE` **no** está → el fallback A queda **refutado**, no "riesgoso"

`004` §5.1 decía de la Opción A «requiere `STORAGE_IMAGE`» y la ponía en riesgo por si la
decodificación pasaba por software. La pregunta era si el driver lo soportaría.

**No lo soporta.** `FORMAT_FEATURE_2_STORAGE_IMAGE_BIT` (`0x2`) no está en la lista. La Opción A
**no es una opción** para BC3 en este dispositivo. Deja de ser "usar con cuidado" y pasa a
`NOT_AVAILABLE`, por medición, no por especulación.

### 4.3 `COLOR_ATTACHMENT` **no** está → el camino DXT5-como-attachment es exclusivo de GL

`FORMAT_FEATURE_2_COLOR_ATTACHMENT_BIT` (`0x80`) no está. En Vulkan, BC3 **no** puede ser color
attachment de un render pass en esta GPU. El enfoque de `test_hardware_bc3.c` (DXT5 como
`GL_COLOR_ATTACHMENT0`) es exclusivo de la extensión de OpenGL y no tiene equivalente en Vulkan
aquí.

**Esto no invalida el diseño de `003`**, que usa BC3 como `SAMPLED` y RGBA8 como attachment — la
dirección correcta. Pero cierra una puerta que `003` §4.1 dejaba abierta como «replantear» y que
en realidad no tiene a dónde replantear.

## 5. Dispositivos no objetivo — por qué el filtro por PCI no es opcional

Los mismos bits BC3 en los otros dos dispositivos:

| Dispositivo | `SAMPLED_IMAGE` | Otros bits `optimalTiling` |
|---|---|---|
| `8086:0412` Intel HD 4600 | **sí** | `BLIT_SRC`, `FILTER_LINEAR`, `TRANSFER_SRC/DST` |
| `1002:699f` RX 550 | **sí** | los 7 de §3 |
| `10005:0000` llvmpipe | **sí** | los 7 de §3 + `HOST_IMAGE_TRANSFER` |

**Los tres reportan `SAMPLED_IMAGE`.** Un probe que eligiera por índice, o que se quedara con el
primer dispositivo que devuelve algo, habría dado `SAMPLED` y **habría acertado por accidente**.
`F4-AD-23` queda confirmado empíricamente, no solo por argumento.

## 6. CONFLICT con el router — `mesa-vulkan-drivers` ausente no implica «sin Vulkan»

`01-AUDITORIA/DOCUMENTATION-ROUTER/DOCUMENTATION-ROUTER.md` §3bis (commit `ad4d08b`) afirma:

> `mesa-vulkan-drivers` · `PACKAGE_ABSENT` · **no instalado** · Token NO autorizado:
> `DRIVER_OPERATIONAL` → «RADV / Vulkan en HOST-C · `NOT_AVAILABLE` — no hay `mesa-vulkan-drivers`»

**La conclusión es falsa y la medición la refuta.** El paquete que provide los ICD no se llama
`mesa-vulkan-drivers`:

```
$ rpm -qf /usr/lib64/libvulkan_radeon.so
mesa-vulkan-drivers-freeworld-26.2.3-1.fc44.x86_64
$ rpm -qf /usr/lib64/libvulkan_lvp.so
mesa-vulkan-drivers-freeworld-26.2.3-1.fc44.x86_64
$ rpm -q mesa-vulkan-drivers
el paquete mesa-vulkan-drivers no está instalado
```

Es el tercer caso del patrón que `AGENTS.md` §Falsificación ya documenta dos veces
(`vulkan.h` vs `vulkan-devel`; `spirv-tools` vs `vulkan-devel`): **se comprueba un vecino del
objeto, no el objeto**. La cadena de paquetes correcta es
`mesa-vulkan-drivers-freeworld` `PACKAGE_PRESENT` → ICD presente → **RADV `DRIVER_OPERATIONAL`**:
enumera `1002:699f`, reporta `apiVersion 1.4.354`, `driverName radv`, `driverInfo Mesa 26.2.3`, y
responde consultas de formato.

| Token | Valor correcto |
|---|---|
| `mesa-vulkan-drivers` | `PACKAGE_ABSENT` — cierto, y no prueba nada |
| `mesa-vulkan-drivers-freeworld` | `PACKAGE_PRESENT` `26.2.3-1.fc44` |
| RADV sobre `1002:699f` | `DRIVER_OPERATIONAL` (operación exitosa evidenciada) |
| RADV VkImage BC3 → sampler → FBO | `NOT_DETERMINED` — `F1` no lo establece, solo la capacidad |

**No reparo el router**: está fuera de mi ámbito. Lo reporto. La corrección la escribe quien
mantenga `01-AUDITORIA/`.

`TESTING.md` / `PROYECTO_STATUS.md` heredan la misma afirmación; quedan marcados `CONFLICT`
hasta que se corrija la fuente.

## 7. Lo que esta medición NO establece

- **No** mide la interpolación de la rampa alfa. `AD-12` sigue `NOT_DETERMINED`. Que el formato
  sea `SAMPLED` no dice qué regla aplica el texture unit.
- **No** mide rendimiento. `vkGetPhysicalDeviceFormatProperties` no ejecuta la GPU.
- **No** establece que la decodificación pase por la texture unit y no por el driver
  (`P-9` en `004` §6, sigue abierto).
- **No** sustituye al probe. Esta medición es una consulta de lectura; el probe de IA-2 sigue
  siendo necesario para el aborto por identidad (`F4-AD-23`) y para los valores por API 1.0.
- **No** verifiqué `DRI_PRIME=1 glxgears` ni `vkcube`. Son benchmarks / carga de GPU; no
  reejecutados en esta ronda. La afirmación «Fase 3 no requiere `unbind`» sigue citando a
  `daf2f29`, commit propio de la ronda 5, **no** medida por mí hoy.

## 8. Reproducción

```
vulkaninfo --summary 2>/dev/null | sed -n '/^Devices:/,$p'
vulkaninfo --show-formats 2>/dev/null | sed -n '/^GPU1:/,/^GPU2:/p' \
  | grep -A20 'FORMAT_BC3_UNORM_BLOCK'
rpm -qf /usr/lib64/libvulkan_radeon.so
```

Sin escrituras a disco fuera de `/tmp/opencode/`. Sin `sudo`. Sin cambios de sistema.
