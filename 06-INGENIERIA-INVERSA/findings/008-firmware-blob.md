# 008 — `polaris12_smc.bin`: extracción, integridad y estructura del header

**Clasificación**: `READ_ONLY/EVIDENCE`
**Fecha**: 2026-09-29
**Ámbito**: IA-1, `06-INGENIERIA-INVERSA/`
**Autorización**: lectura de `/usr/lib/firmware`, escritura en `firmware/` propio. Sin sysfs, sin
carga de firmware en la GPU, sin `SYSTEM_CHANGE`.

---

## 1. El nombre del brief no es el del fichero

El brief pide extraer `polaris12_smc.bin`. En este host **no existe ningún fichero con ese
nombre exacto**:

```
$ find / -name 'polaris12_smc.bin' -not -path '/proc/*'
(sin resultados)
```

Lo que hay son **19 blobs de firmware de Polaris 12**, todos con sufijo `.bin.xz`:

```
/usr/lib/firmware/amdgpu/polaris12_smc.bin.xz      ← el pedido, comprimido
/lib/firmware/amdgpu/polaris12_smc.bin.xz           ← el mismo, vía enlace
```

Son **copias del mismo fichero**: `/lib/firmware` es un enlace a `/usr/lib/firmware` en esta
distribución. Se verificó que ambos resuelven al mismo contenido por `xz` y que el SHA256 del
`.xz` es igual.

**Descompresión necesaria.** `xz -dc` produce el blob plano.

## 2. Identidad del artefacto extraído

| Campo | Valor |
|---|---|
| Ruta origen | `/usr/lib/firmware/amdgpu/polaris12_smc.bin.xz` |
| Ruta extraída | `06-INGENIERIA-INVERSA/firmware/polaris12_smc.bin` |
| Tamaño descomprimido | **130 388 B** (32 597 dwords) |
| SHA256 (descomprimido) | `4b8eb326a7fbd391554fe50bc43cf04a917b01a806884ea324f5c3fe88a6ec77` |
| `file` | `data` — sin magic recognized |

El blob está commiteado. **Debe estarlo**: es la referencia contra la que se compara cualquier
firmware que un driver propio tenga que entender, y son 130 KB.

> El SHA256 del `.xz` comprimido es un dato distinto del del blob. Citar el del `.bin`
> descomprimido.

## 3. Estructura del header: decodificada y verificada

La definición está en `RESEARCH/working/linux-7.1.3/drivers/gpu/drm/amd/amdgpu/amdgpu_ucode.h:30-41`:

```c
struct common_firmware_header {
    uint32_t size_bytes;              /* tamaño total header + imagen(es) */
    uint32_t header_size_bytes;       /* tamaño del header solo */
    uint16_t header_version_major;
    uint16_t header_version_minor;
    uint16_t ip_version_major;        /* versión de IP */
    uint16_t ip_version_minor;
    uint32_t ucode_version;
    uint32_t ucode_size_bytes;        /* tamaño del ucode */
    uint32_t ucode_array_offset_bytes;/* offset del payload desde el header */
    uint32_t crc32;                   /* CRC32 del payload */
};
```

32 B empaquetados. Decodificación del blob real, little-endian como hace el driver
(`le32_to_cpu` en x86):

| Offset | Campo | Valor bruto | Valor |
|---|---|---|---|
| `0x00` | `size_bytes` | `0x0001FD54` | **130 388** |
| `0x04` | `header_size_bytes` | `0x00000024` | **36** |
| `0x08` | `header_version_major` | | 1 |
| `0x0A` | `header_version_minor` | | 0 |
| `0x0C` | `ip_version_major` | | **7** |
| `0x0E` | `ip_version_minor` | | **2** |
| `0x10` | `ucode_version` | `0x00221700` | `0x00221700` |
| `0x14` | `ucode_size_bytes` | `0x0001FC54` | **130 132** |
| `0x18` | `ucode_array_offset_bytes` | `0x00000100` | **256** |
| `0x1C` | `crc32` | `0xAE2B3B78` | `0xAE2B3B78` |

**Coherencia verificada aritméticamente:**

- `size_bytes = 130 388` **coincide exactamente con el tamaño del fichero.** Es la prueba de que
  el offset 0 es el campo que dice ser: si fuera otra cosa, la coincidencia sería casual.
- El payload empieza en el offset **256**, no en `header_size_bytes = 36`. Hay **220 B** entre
  el final del header y el payload. **No se ha establecido qué contienen**; no se rellena por
  suposición. Probablemente metadatos de carga, pero eso es `PLAUSIBLE` sin verificar.
- `ucode_size_bytes = 130 132` y `256 + 130 132 = 130 388` = tamaño total. **La aritmética
  cierra exactamente.** Es la segunda comprobación independiente de que el header está bien
  interpretado.

## 4. `ip_version = 7.2` — y lo que NO permite concluir

El header declara **`ip_version_major = 7`, `ip_version_minor = 2`**.

**Esto es la versión de IP del propio SMC, no la del GFX.** Son IP blocks distintos. Es tentador
leer "7.2" y concluir algo sobre `GFX_HWIP`; sería el salto que `AGENTS.md` prohíbe.

**`GFX_HWIP` sigue `NOT_DETERMINED`.** Su valor viene del ASIC ID leído por UMR, no de un
header de firmware. Lo que sí se establece es que el SMC de esta GPU **es de IP 7.2**, lo cual
es un dato nuevo y utilizable para validar que un driver propio habla con la versión de SMC
correcta.

## 5. El CRC32 no se pudo verificar

El header declara `crc32 = 0xAE2B3B78`. El CRC32 estándar de los 130 132 B del payload da:

```
zlib.crc32(payload) = 0x9D6AEF38     ≠     0xAE2B3B78
```

**No coinciden, y no se ha establecido por qué.** Dos posibilidades, ninguna comprobada:

1. El driver usa un CRC32 con polinomio o inicialización distintos del estándar.
2. El CRC se calcula sobre un rango distinto del que se ha supuesto (por ejemplo incluyendo los
   220 B entre header y payload).

**No se decide entre las dos porque el árbol de referencia es parcial**: `amdgpu_ucode.c`
imprime el campo con `DRM_DEBUG` pero **no lo verifica** — la verificación no está en ese
fichero, y `amdgpu_smc.c` **no existe** en `RESEARCH/working/linux-7.1.3` (632 ficheros de
`amdgpu/`, sin el parser de SMC). La función de CRC que lo computa no está disponible aquí.

`NOT_DETERMINED`. Para el objetivo de Fase 4 es un bloqueo menor: un driver propio que quiera
**producir** firmware necesita la función de CRC, y esa hay que conseguirla de otra fuente
(árbol completo del kernel, o lectura del blob de la PSP en la GPU).

## 6. Los otros 18 blobs de Polaris 12

Disponibles en `/usr/lib/firmware/amdgpu/`, todos `.xz`:

| Grupo | Ficheros | Para qué |
|---|---|---|
| **Shader ISA** | `polaris12_pfp.bin.xz`, `polaris12_pfp_2.bin.xz`, `polaris12_me.bin.xz`, `polaris12_me_2.bin.xz`, `polaris12_mec.bin.xz`, `polaris12_mec_2.bin.xz`, `polaris12_mec2.bin.xz`, `polaris12_mec2_2.bin.xz` | microcode de GFX8 |
| **Command processor** | `polaris12_smc.bin.xz`, `polaris12_k_smc.bin.xz` | microcode del command processor |
| **Memory controller** | `polaris12_mc.bin.xz`, `polaris12_32_mc.bin.xz`, `polaris12_k_mc.bin.xz` | control de VRAM |
| **DMA** | `polaris12_sdma.bin.xz`, `polaris12_sdma1.bin.xz` | **LSDMA — el subsistema de PM4** |
| **RLC** | `polaris12_rlc.bin.xz` | reloadable logic control |
| **Video** | `polaris12_vce.bin.xz`, `polaris12_uvd.bin.xz` | codificación |
| **CE** | `polaris12_ce.bin.xz`, `polaris12_ce_2.bin.xz` | command engine |

**`polaris12_sdma.bin.xz` es el relevante para el submit de compute**, dado el hallazgo de la
Ronda 1 de que el envío PM4 de esta generación es LSDMA. Está entre los 19 pero **no se ha
extraído ni medido**: `DEFERRED`, la tarea de esta ronda era el SMC.

Todos los nombres llevan el sufijo `_2` en varios casos, lo que indica variantes de versión del
mismo microcode. No se ha determinado cuál usa esta GPU: eso lo decide el hardware, no el
directorio. `NOT_DETERMINED`.

## 7. Límites

- El blob está **decodificado, no descompilado**. Conocer el header y que el CRC cuadra
  aritméticamente no dice qué contiene el microcode.
- Los **220 B** entre `header_size_bytes` y `ucode_array_offset` no se han inspeccionado.
- La **función de CRC** no se ha identificado (§5).
- **No se ha cargado nada en la GPU.** `RUNTIME_EXECUTION` no autorizado en este ámbito.
- El árbol de referencia es **parcial**: sin `include/uapi` y sin `amdgpu_smc.c`. Las
  definiciones de header sí estaban, en `amdgpu_ucode.h`.
- No se ha establecido cuál de los 19 blobs carga esta GPU ni en qué orden.

## Procedencia

SHA256 y tamaño por `sha256sum`/`stat` sobre el fichero extraído con
`xz -dc /usr/lib/firmware/amdgpu/polaris12_smc.bin.xz` el 2026-09-29. Decodificación del header
contra `amdgpu_ucode.h:30-41` con las comprobaciones aritméticas de §3. El cálculo del CRC
estándar con `zlib.crc32` y su comparación con el campo del header.
