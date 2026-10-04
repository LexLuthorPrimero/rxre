# CENSUS DE CAPACIDADES — RX550 / POLARIS12 / GFX8 — NODO `VULKAN-CENSUS`

```text
NODE_ID       : VULKAN-CENSUS
ORIGEN        : idea de usuario N-INT-89 «matriz de capacidades de colas Vulkan»
FECHA         : 2026-10-04T11:13:59Z (UTC) .. 2026-10-04 (lecturas subsiguientes)
HOST          : Intel Core i7-4790 (family 6, model 60, stepping 3), 4C/8T, 1 nodo NUMA
KERNEL        : 7.1.3-200.nobara.fc44.x86_64   (Nobara Linux 44, ID_LIKE rhel/centum/fedora)
SALIDA        : ESTE UNICO FICHERO. No se ha editado nada mas del arbol.
NIVEL DE AUTORIZACION : 4 (investiga, no interviene)
```

## 0. CLASIFICACION DE EVIDENCIA USADA EN TODO EL DOCUMENTO

| Marca | Significado |
|---|---|
| `[LE]` | `LEÍDO_EN_EJECUCIÓN` — valor obtenido por lectura en esta sesión |
| `[FUENTE]` | `LEÍDO_EN_FUENTE` — valor obtenido leyendo contenido de fichero/binario, sin ejecutar el driver |
| `[DER]` | `DERIVADO` — aritmética sobre valores `[LE]` citados, con la operación escrita |
| `[SUPUESTO]` | cálculo que depende de un modelo declarado explícitamente |
| `[ND]` | `NOT_DETERMINED` — no determinado, y se dice por qué |
| `[BLOQ]` | bloqueado; se dice qué falta |

Regla aplicada sin excepción (§9 del prompt): **un binario instalado es evidencia sobre una implementación, no sobre el hardware.** Ninguna cadena de texto encontrada dentro de `libvulkan_radeon.so` se cuenta como soporte de una capacidad Vulkan. Se cuenta, en el mejor caso, como `EXISTE_CODIGO_QUE_SABE_ENCENDER_UN_FLAG`, y así se etiqueta.

## 1. VEREDICTO EN UNA FRASE

**La GPU está en `D3hot` con runtime-PM `suspended`, `/dev/dri/renderD129` es `0666` (cualquier usuario la abre), y por tanto *toda* capacidad Vulkan de cola es `REQUIERE_ABRIR_DEVICE` → `BLOQUEADA`.** Lo que sí se ha cerrado sin tocar la GPU: identidad completa de la pila, mapa de BARs, topología PCIe y un techo de ancho de banda **medido** que invalida la vía PCIe de R-NEW-37..40 sin necesidad de escribir nada.

---

# PARTE 1 — IDENTIDAD DE LA PILA GRÁFICA INSTALADA

## 1.1 Versiones, con fichero fuente y hash

| Componente | Versión | Evidencia |
|---|---|---|
| Kernel en ejecución | `7.1.3-200.nobara.fc44.x86_64` | `[LE]` `uname -r` |
| Módulo `amdgpu` (en ejecución) | `srcversion D68004925455E20A24C2B87`, `vermagic 7.1.3-200.nobara.fc44.x86_64 SMP preempt mod_unload` | `[LE]` `/sys/module/amdgpu/srcversion`, `/sys/module/amdgpu/taint` = `''` |
| Módulo `amdgpu` (en disco) | `srcversion D68004925455E20A24C2B87` — **idéntico al en ejecución** | `[FUENTE]` `modinfo amdgpu` |
| `amdgpu.ko.zst` | 5 954 300 B | `[LE]` `os.stat` |
| sha256 `amdgpu.ko.zst` | `6ec8f7e7a258c520c9c8b9f4269f73d2052bcd1bdb8d178c640b9c25aa06a663` | `[LE]` |
| **`/sys/module/amdgpu/version`** | **NO EXISTE** (`FileNotFoundError`) | `[LE]` |
| Mesa | `26.2.3` | `[FUENTE]` cadena `Mesa version: 26.2.3\n` dentro de `libvulkan_radeon.so`; `[LE]` `rpm -qa` → `mesa-vulkan-drivers-freeworld-26.2.3-1.fc44.x86_64` |
| Paquete que trae el ICD AMD | `mesa-vulkan-drivers-freeworld-26.2.3-1.fc44.x86_64` | `[LE]` `rpm -qf /usr/lib64/libvulkan_radeon.so` |
| Versión in-binary, autoritativa | `.note.package` = `{"type":"rpm","name":"mesa-vulkan-drivers-freeworld","version":"26.2.3-1.fc44","architecture":"x86_64","osCpe":"cpe:/o:fedoraproject:fedora:44"}` | `[FUENTE]` `readelf -n /usr/lib64/libvulkan_radeon.so` |
| **RADV** | no tiene versión propia: es parte de Mesa ⇒ `26.2.3`. Confirmado por presencia de cadenas exclusivas de RADV | `[FUENTE]` cadenas `Mesa releases. Please use RADV_...`, `RADV_PERFTEST`, `RADV_QUEUE_DISABLE` |
| Vulkan ICD de AMD | `radeon_icd.x86_64.json` → `/usr/lib64/libvulkan_radeon.so`, `api_version "1.4.354"`, `file_format_version "1.0.1"` | `[LE]` ver §1.2 |
| **AMDVLK / AMD ICD** | **NO INSTALADO** — no existe `amd_icd.*.json` en `/usr/share/vulkan/icd.d/` | `[LE]` listado completo del directorio, 30 ficheros |
| Vulkan loader | `1.4.341.0-1.fc44.x86_64`; `SONAME=libvulkan.so.1`; fichero `libvulkan.so.1.4.341` | `[LE]` `rpm -q vulkan-loader`, `[FUENTE]` `readelf -d` |
| sha256 loader | `a09dab583a4b8e50bba61d1284b46b9d6256300713aa1db6f20f06b2dbbe0696` | `[LE]` |
| sha256 ICD json AMD | `d1c36db1d658755b0cb325f991e337544f7a607a6f5c277e62b1de7d81d7a4c7` (179 B) | `[LE]` |
| sha256 `libvulkan_radeon.so` | `953078a3840a1db21740c40af3e5cdc9dc02912966a5b737c682e047c18bfbe3` (19 378 152 B) | `[LE]` |
| build-id `libvulkan_radeon.so` | `eddd1842f07c5c1dd4ddc4000a6172cc420a4f4f` | `[FUENTE]` `readelf -n` |
| LLVM usado por RADV | `libLLVM.so.22.1` (DT_NEEDED); `llvm-22.1.8-4.fc44.x86_64` | `[FUENTE]` `readelf -d`, `[LE]` `rpm -q llvm` |
| SPIR-V | `libSPIRV-Tools.so` (DT_NEEDED); `spirv-tools-2026.1-2.fc43`; `spirv-llvm-translator-22.1.2-1.fc44` | `[LE]` `rpm -qa` |
| libdrm | `2.4.134-1.fc44`; `SONAME=libdrm.so.2` | `[LE]`, `[FUENTE]` |
| Vulkan headers instalados | `vulkan-headers-1.4.341.0-1.fc44.noarch`; `/usr/include/vulkan/vulkan_core.h` = 1 265 235 B | `[LE]` |
| `vulkaninfo` | `/usr/bin/vulkaninfo` de `vulkan-tools-1.4.341.0-1.fc44.x86_64` | `[LE]` `rpm -ql vulkan-tools` |
| **Validation layers** | **`vulkan-validationlayers` NO INSTALADO** | `[LE]` `rpm -q` |

### 1.2 Contenido literal del ICD de AMD

`/usr/share/vulkan/icd.d/radeon_icd.x86_64.json`, 8 líneas, 179 bytes, íntegro:

```json
{
    "ICD": {
        "api_version": "1.4.354",
        "library_arch": "64",
        "library_path": "/usr/lib64/libvulkan_radeon.so"
    },
    "file_format_version": "1.0.1"
}
```

Nota de lectura: `"api_version": "1.4.354"` es **la versión de interfaz del ICD**, no la versión de API que la tarjeta expondrá. No es evidencia de nada del device.

### 1.3 Inventario de ICDs y layers (R-NEW-83..88)

`[LE]` `/usr/share/vulkan/icd.d/` contiene **30 ficheros** = 15 drivers × {i686, x86_64}:
`asahi, broadcom, dzn, freedreno, intel_hasvk, intel, lvp, nouveau, panfrost, powervr_mesa, radeon, virtio` (+ `radv` no aparece: el ICD de RADV se llama `radeon`).

`[LE]` `/etc/vulkan/icd.d/` — existe, **0 entradas**. `/usr/local/share/vulkan/icd.d/` — **AUSENTE**. ⇒ no hay override de ICD en `/etc`.

`[LE]` `/usr/share/vulkan/explicit_layer.d/` — existe, **0 entradas**. ⇒ **no hay ninguna explicit layer instalada.**
`[LE]` `/etc/vulkan/explicit_layer.d/` — existe, 0 entradas.

`[LE]` `/usr/share/vulkan/implicit_layer.d/` — **7 ficheros**:

| Layer | enable_environment | activo por defecto |
|---|---|---|
| `VK_LAYER_MANGOHUD_overlay_x86_64` | `MANGOHUD=1` | no `[FUENTE]` |
| `VK_LAYER_VKBASALT_post_processing` | `ENABLE_VKBASALT=1` | no `[FUENTE]` |
| `VK_LAYER_FROG_gamescope_wsi_x86_64` | `ENABLE_GAMESCOPE_WSI=1` | no `[FUENTE]` |
| `VK_LAYER_MESA_device_select` | **sólo `disable_environment: NODEVICE_SELECT=1`** | **sí, por reglas del loader** `[FUENTE]` |
| `VK_LAYER_MESA_anti_lag` | `ENABLE_LAYER_MESA_ANTI_LAG=1`; expone `VK_AMD_anti_lag` | no `[FUENTE]` |
| (+ las dos variantes i686 de MangoHud y gamescope) | | |

`[LE]` Entorno del proceso de census: 92 variables, **0** empiezan por `VK_`, `MESA_`, `DRI_`, `AMD`, `RADV`, y **0** son `MANGOHUD`/`ENABLE_VKBASALT`/`NODEVICE_SELECT`. ⇒ no hay redirección forzada de ICD ni de layer en esta sesión.

**Consecuencia para el diseño de cualquier experimento Vulkan futuro (no es una mejora, es un control de validez):** la única capa que se interpondrá por defecto es `VK_LAYER_MESA_device_select`, que introduce una capa de selección de device y expone `VK_EXT_layer_settings`. Cualquier medición futura debe declararla, o fijar `NODEVICE_SELECT=1`.

### 1.4 RadV: 24 variables de entorno embebidas en el binario

`[FUENTE]` regex `RADV_[A-Z0-9_]{2,40}` sobre `libvulkan_radeon.so` → 24:

```text
RADV_BVH_STATS_FILE            RADV_PROFILE_PSTATE
RADV_CACHE_COUNTERS_BUFFER_SIZE RADV_QUEUE_DISABLE
RADV_DEBUG                     RADV_RRA_TRACE_COPY_AFTER_BUILD
RADV_EXPERIMENTAL              RADV_RRA_TRACE_HISTORY_SIZE
RADV_FORCE_VRS                 RADV_RRA_TRACE_RESOLUTION_SCALE
RADV_FORCE_VRS_CONFIG_FILE     RADV_RRA_TRACE_VALIDATE
RADV_GPU_TRACEPOINT            RADV_SPM_COUNTERS_CONFIG
RADV_PERFTEST                  RADV_TEX_ANISO
RADV_PRINTF_BUFFER_SIZE        RADV_THREAD_TRACE_BUFFER_SIZE
RADV_THREAD_TRACE_CACHE_COUNTERS
RADV_THREAD_TRACE_INSTRUCTION_TIMING
RADV_THREAD_TRACE_INSTRUCTION_TIMING_SE_MASK
RADV_THREAD_TRACE_QUEUE_EVENTS
RADV_TRAP_HANDLER              RADV_TRAP_HANDLER_EXCP
```

Etiqueta estricta: esto prueba **qué variables acepta el binario instalado**, no que el hardware soporte el subsistema correspondiente, y no prueba que la variable tenga efecto en una sesión suspendida.

---

# PARTE 2 — LO QUE SYSFS DECLARA DE ESTA TARJETA, SIN TOCAR LA GPU

## 2.1 Identidad PCI — `TARGET MATCH` con salvedad

`[LE]` `/sys/bus/pci/devices/0000:01:00.0/`:

```text
vendor            = '0x1002'
device            = '0x699f'
subsystem_vendor  = '0x1002'
subsystem_device  = '0x0b04'
revision          = '0xc7'
class             = '0x030000'
modalias          = 'pci:v00001002d0000699Fsv00001002sd00000B04bc03sc00i00'
driver            -> ../../../../bus/pci/drivers/amdgpu
driver_override   = '(null)'
boot_vga          = '1'
enable            = '1'
```

`[LE]` espacio de configuración binario, `/sys/bus/pci/devices/0000:01:00.0/config` (modo `0644`, 64 bytes leídos):

```text
config:0x00 vendor        = 0x1002
config:0x02 device        = 0x699f
config:0x04 command       = 0x0407
config:0x06 status        = 0x0010
config:0x08 revision      = 0xc7
config:0x0b base_class    = 0x03
config:0x0e header_type   = 0x80
config:0x2c BAR6          = 0x0b041002
```

Dos rutas independientes (sysfs de atributos y espacio de configuración crudo) coinciden en `vendor/device/revision`. `1002:699F` rev `0xC7` es el identificador de RX 550 / Polaris12. ⇒ **NO hay `_TARGET_MISMATCH_` en identidad PCI.** El documento no queda condicionado por la comprobación del nodo 4.

Salvedades honestas que **no** puedo cerrar:
- `[ND]` «Polaris12» y «GFX8» **no están escritos en ningún fichero leído**. La evidencia de ASIC es: (a) el device ID `0x699F`; (b) el juego de firmware ya cargado, §2.6. No he consultado ninguna tabla PCI-ID externa — no hay descarga a internet.
- `[ND]` `subsystem_device = 0x0b04` no lo he contrastado con ninguna base de datos de subsistemas. Lo dejo como valor bruto.
- `[ND]` **`vbios_version = 'xxx-xxx-xxx'`**. No sé si es un literalplaceholder en el VBIOS de esta placa o una lectura anómala. No lo ajusto: lo reporto. Es el primer sitio donde mirar si aparece una contradicción sobre la identidad de la placa.
- `[ND]` `header_type = 0x80` (bit multifunción). No he determinado qué función secundaria expone (BAR6 con base `0x0b041000` y bits de tipo `0x2` = «below-1M», obsoleto). No concluyo nada.

## 2.2 Mapa `/dev/dri/*` ↔ PCI — cerrado por dos rutas

`[LE]` symlink `device`:

```text
card0     -> ../../../0000:00:02.0   (i915,  class 0x038000)
renderD128-> ../../../0000:00:02.0
card1     -> ../../../0000:01:00.0   (amdgpu, class 0x030000)
renderD129-> ../../../0000:01:00.0
```

`[LE]` `/dev/dri/by-path/`:

```text
pci-0000:01:00.0-card    -> ../card1
pci-0000:01:00.0-render  -> ../renderD129
pci-0000:00:02.0-card    -> ../card0
pci-0000:00:02.0-render  -> ../renderD128
```

`[LE]` `realpath('/sys/class/drm/card1/device')` == `realpath('/sys/bus/pci/devices/0000:01:00.0')` == `/sys/devices/pci0000:00/0000:00:01.0/0000:01:00.0` ⇒ `IGUALES = True`.

`[LE]` drivers ligados: `0000:00:02.0 → i915`, `0000:01:00.0 → amdgpu`. Sólo dos dispositivos con clase `0x03xxxx`.

**Conclusión de identidad de nodo:** `renderD129` y `card1` son la RX 550. `renderD128`/`card0` son la Intel HD Graphics 4600. **No hay ambigüedad de nodo.**

`[LE]` permisos yLTE:

```text
/dev/dri/card0      mode=0660 uid=0 gid=39(video)    major=226 minor=0
/dev/dri/card1      mode=0660 uid=0 gid=39(video)    major=226 minor=1
/dev/dri/renderD128 mode=0666 uid=0 gid=105(render)  major=226 minor=128
/dev/dri/renderD129 mode=0666 uid=0 gid=105(render)  major=226 minor=129
/dev/kfd            EXISTE
```

`[LE]` `id` del proceso de census: `uid=1000(lucas) gid=1000(lucas) grupos=1000(lucas),10(wheel),100(users)`.

> **HECHO DE SEGURIDAD DECISIVO.** El usuario de este proceso **no** está en `video`(39) **ni** en `render`(105). Por tanto **no puede** abrir `card0`/`card1` (`0660`) — pero **sí puede** abrir `renderD128`/`renderD129` porque son `0666`. El modelo de permisos **no protege** la GPU de una escritura indirecta vía render node. La única defensa es la disciplina. §4.2 explica por qué eso convierte `vulkaninfo` en inviable.

## 2.3 BARs — decodificados desde el fichero `resource` y contrastados con config space

`[LE]` `/sys/bus/pci/devices/0000:01:00.0/resource`, 13 líneas (una por BAR 0..6, ROM, 7..12), 741 B. Constantes de decodificación leídas de
`/usr/src/kernels/7.1.3-200.nobara.fc44.x86_64/include/linux/ioport.h:37..72` (`IORESOURCE_*`) y
`/usr/include/linux/pci_regs.h:96..111` (`PCI_BASE_ADDRESS_*`).

| # | `resource:N` | start | end | flags crudos | tamaño `[DER]` | tipo `[DER]` |
|---|---|---|---|---|---|---|
| 0 | `resource:1` | `0xe0000000` | `0xefffffff` | `0x14220c` | 16 MiB | `MEM` + `MEM_64` + `PREFETCH` + `SIZEALIGN` + `WINDOW`; bits de bus `0x0c` = 64-bit prefetchable |
| 1 | `resource:2` | 0 | 0 | `0x0` | — | no implementado (lee 0) |
| 2 | `resource:3` | `0xf0000000` | `0xf01fffff` | `0x14220c` | 2 MiB | igual que BAR0 |
| 3 | `resource:4` | 0 | 0 | `0x0` | — | no implementado |
| 4 | `resource:5` | `0x0000e000` | `0x0000e0ff` | `0x40101` | 256 B | `IO` + `SIZEALIGN`; `type:4=1` (ROM) ⇒ puertos VGA |
| 5 | `resource:6` | `0xf7d00000` | `0xf7d3ffff` | `0x40200` | 256 KiB | `MEM` + `SIZEALIGN`; bits de bus `0x0` ⇒ **32-bit NO prefetchable** ⇒ apertura ROM/VBIOS |
| 6 | `resource:7` | `0x000c0000` | `0x000dffff` | `0x212` | 128 KiB | `MEM`; `type:4=2` (reserved); bits de bus `0x12` ⇒ SMBIOS |
| ROM | `resource:8` | 0 | 0 | `0x0` | — | descodificación ROM **deshabilitada** |
| 7..12 | `resource:9..13` | 0 | 0 | `0x0` | — | no implementados |

Contraste independiente `[LE]` config space: `BAR0=0xe000000c`, `BAR2=0xf000000c`, `BAR4=0x0000e001`, `BAR5=0xf7d00000`, `BAR6=0x0b041002`, `ROM=0x00000000`. Los niblos bajos coinciden con el decode. **El `resource` y el config space no se contradicen.**

**Lo que esto significa, con sus límites:**
- BAR2 = 2 MiB es la **ventana MMIO de la GART** bajo el dominio de usuario. Es el techo del espacio de direcciones de VRAM mapeable por el driver: `[LE]` `mem_info_vis_vram_total = 268435456` (256 MiB) dice lo mismo por otra vía ⇒ coherencia cruzada.
- `[DER]` El límite duro de VRAM direccionable por proceso es **2 MiB**, no 256 MiB. Consecuencia directa y medible: cualquier carga de N-INT-90/91/92 que supere 2 MiB de superficie mapeada **no es representativa de la tarjeta**, porque obliga a `moverate`-driven eviction/reimport. Esto es un hecho de diseño experimental, no una mejora.
- `[ND]` **NO he podido leer `resource0_wc` ni `resource2_wc`.** Existen (`os.listdir` los muestra) pero son `mode=0600 uid=0 gid=0` y la lectura devuelve `PermissionError`. El encargo las pedía. **No las he sustituido por invención.** Lo que sí puedo afirmar es el atributo de prefetch desde config space: BAR0 y BAR2 tienen bit `PCI_BASE_ADDRESS_MEM_PREFETCH` (`0x08`) activo ⇒ el hardware los declara prefetchable. Si el kernel los sirve como write-combining o no, es `[ND]`.

## 2.4 PCIe — hallazgo mayor, y acerca las ideas R-NEW-37..40

`[LE]` `/sys/bus/pci/devices/0000:01:00.0/`:

```text
max_link_speed     = '8.0 GT/s PCIe'
max_link_width     = '8'
current_link_speed = '5.0 GT/s PCIe'
current_link_width = '4'
```

`[LE]` puente aguas arriba = `0000:00:01.0` (`realpath` del padre; `vendor=0x8086`, `device=0x0c01`, `class=0x060400` = puente PCI-a-PCI):

```text
max_link_speed     = '5.0 GT/s PCIe'
max_link_width     = '16'
current_link_speed = '5.0 GT/s PCIe'
current_link_width = '4'
```

`[LE]` `/sys/module/amdgpu/parameters/pcie_gen_cap = '0'` y `pcie_lane_cap = '0'` ⇒ **autodetección** (0 = autodetect según el `modinfo`). El driver no está capando nada por parámetro.

Cadena causal reconstruida:

```text
PCIe: la tarjeta declara capacidad Gen3 x8                  [LE] max_link_*
  ↓  el techo lo pone el puente, no la tarjeta
el puente 8086:0c01 declara máximo Gen2                       [LE] puente max_link_speed = 5.0 GT/s
  ↓
el enlace negociado queda en Gen2                             [LE] current_link_speed (ambos) = 5.0 GT/s
  ↓
y en x4, tanto en la tarjeta como en el puente                 [LE] current_link_width = 4 / 4
  ↓
ningún parámetro de amdgpu lo explica                          [LE] pcie_gen_cap=0, pcie_lane_cap=0
```

`[DER]` Con `[SUPUESTO]` codificación 8b/10b (obligatoria en Gen1/Gen2, no en Gen3):

```text
enlace efectivo  : 5.0 GT/s × 4 = 20 Gbit/s crudos × 8/10 = 16 Gbit/s = 2.00 GB/s (por dirección)
capacidad tarjeta: 8.0 GT/s × 8 = 64 Gbit/s crudos × 8/10 = 51.2 Gbit/s = 6.40 GB/s (por dirección)
razón            : 2.00 / 6.40 = 0.3125  (se está usando ~1/3 de la capacidad de la tarjeta)
```

`[ND]` **Por qué x4 y no x8/x16:** no determinable con lo que se ha leído. Candidatos no separados por esta evidencia: señal insuficiente, lanes enmascarados, limitación de placa, o lectura de un ancho de enlace no negotiationado por software de plataforma. **Separarlos exigiría inspección de BIOS o un analizador PCIe, no sysfs.**

`[LE]` `link/l1_aspm = '0'` (ASPM L1 deshabilitado).

**Efecto sobre las ideas del usuario, sin exagerar nada:** la mitad de R-NEW-37..40 («sube el PCIe», «aprovecha más ancho de banda») no es ejecutable por software de driver, porque el techo lo pone un puente de chipset en Gen2. Eso es un hecho, no una mejora ni un fracaso: cierra la pregunta de si esa vía existe. Queda `NOT_DETERMINED` si un ajuste de BIOS elevaría el Gen2→Gen3 del puente, y eso ya no es un experimento de driver.

## 2.5 Estado de energía — el hecho que cierra el resto del documento

`[LE]` `/sys/bus/pci/devices/0000:01:00.0/`:

```text
power_state             = 'D3hot'
power/runtime_status    = 'suspended'
power/control           = 'auto'
power/autosuspend_delay_ms = '5000'
power/runtime_active_time     = '278853'
power/runtime_suspended_time = '57875987'
power/wakeup            = 'disabled'
/sys/module/amdgpu/holders = []          (vacío: ningún cliente DRM mantiene referencia)
```

`[DER]`: `runtime_suspended_time / (runtime_active_time + runtime_suspended_time)` = 57 875 987 / 58 154 840 = **0.99521** ⇒ el 99.52 % del tiempo desde el arranque ha estado suspendido. `runtime_active_time` ≈ 278.9 s de actividad total.

**Los 30 atributos que exigen el device despierto devolvieron `EBUSY` (`OSError: [Errno 16]`), no datos:**

```text
/sys/bus/pci/devices/0000:01:00.0/  (14)
  gpu_busy_percent  mem_busy_percent
  pp_num_states     pp_cur_state     pp_power_profile_mode
  pp_dpm_sclk       pp_dpm_mclk      pp_dpm_pcie
  pp_mclk_od        pp_sclk_od
  power_dpm_state   power_dpm_force_performance_level
  pcie_bw           pp_table

/sys/bus/pci/devices/0000:01:00.0/hwmon/hwmon1/  (16)
  freq1_input  freq2_input  temp1_input  in0_input  power1_input
  fan1_input  fan1_min  fan1_max  fan1_target  fan1_enable
  pwm1  pwm1_enable  power1_cap  power1_cap_min  power1_cap_max  power1_cap_default
```

`[LE]` Lo que en hwmon **sí** se pudo leer son sólo constantes estáticas: `temp1_crit = 97000` (m°C ⇒ 97 °C), `pwm1_min='0'`, `pwm1_max='255'`, `freq1_label='sclk'`, `freq2_label='mclk'`, `power1_label='PPT'`, `in0_label='vddgfx'`, `temp1_label='edge'`.

`[LE]` `thermal_throttling_logging = '0000:01:00.0: thermal throttling logging enabled, with interval 60 seconds'`.

### 2.5.1 Autorreporte de riesgo — reads que ejecuté y su justificación

Ejecuté `read()` sobre los 30 atributos `EBUSY` de arriba y sobre `resource0`, `resource0_wc`, `resource2`, `resource2_wc`, `resource4`, `resource5`, `rom`, `reset`, y los parámetros `gartsize`, `gttsize`, `ignore_min_pcap`, `moverate`, `vramlimit`. Todos son `open()`+`read()`, ninguno un `write()`.

Lo que **puedo** afirmar con evidencia de esta misma ejecución: **no se observó ningún despertar.** `power_state` se leyó **después** del bloque `pp_*` y seguía en `D3hot`; `power/runtime_status` seguía `suspended`; `holders` seguía vacío. Si un `read()` hubiera hecho `pm_runtime_get`, algún valor habría cambiado.

Lo que **no** puedo afirmar: que tal lectura *no pueda* tener efectos secundarios en general, porque **no dispongo del código fuente de amdgpu** (§1 tabla: 148 ficheros `.c` en todo el árbol del kernel, los 148 bajo `scripts/`, **cero** bajo `drivers/`). Por tanto:

> **Este nodo no debe repetirse sin verificar antes en fuente si `amdgpu` llama a `pm_runtime_get` en el `show` de esos atributos.** Consta como riesgo asumido y delimitado, no como hecho resuelto.

## 2.6 Firmware cargado — evidencia independiente de que esto es GFX8/Polaris

`[LE]` `/sys/bus/pci/devices/0000:01:00.0/fw_version/` (12 entradas):

```text
ce_fw_version  = '0x0000008c'      mec_fw_version   = '0x000002da'
mc_fw_version  = '0x00b4dc50'      mec2_fw_version  = '0x000002da'
me_fw_version  = '0x000000a7'      pfp_fw_version   = '0x000000fe'
rlc_fw_version = '0x00000018'      smc_fw_version   = '0x00221700'
sdma_fw_version = '0x0000003a'     sdma2_fw_version = '0x0000003a'
uvd_fw_version = '0x01821000'      vce_fw_version   = '0x351a0300'
```

Dos hechos que sí se pueden cerrar:

1. `[LE]` El juego es `{ce, mec, mec2, me, pfp, rlc, sdma, sdma2, smc, uvd, vce, mc}` — 12 entradas. `[LE]` `modinfo amdgpu` declara 694 blobs de firmware, entre ellos `amdgpu/polaris12_{mec,rlc,ce,me,pfp,sdma,smc,vce,uvd,mec2}.bin`. La presencia de **`uvd` + `vce`** y la ausencia de **`vcn`** sitúa la generación en la anterior a VCN. Eso es coherente con Polaris12/GFX8 y **contradice** una lectura Vega10/Vega20 o Navi.
2. `[ND]` `uvd_fw_version = 0x01821000` y `vce_fw_version = 0x351a0300`: **no he contrastado estos valores con ninguna fuente primaria.** No los interpreto.

## 2.7 Memoria y VRAM

`[LE]`:

```text
mem_info_vram_total        = 2147483648      (2.00 GiB)
mem_info_vram_used         =    5439488
mem_info_vis_vram_total    =  268435456      (256 MiB)
mem_info_vis_vram_used     =    5439488
mem_info_gtt_total         = 6194638848      (~5.77 GiB)
mem_info_gtt_used          =   14163968
mem_info_preempt_used      =          0
```

`[DER]` `vis_vram_total` (256 MiB) = `0x10000000` = el tamaño de BAR0 declarado en §2.3. Dos interfaces distintas dan el mismo número.

`[LE]` `consistent_dma_mask_bits = '40'`, `dma_mask_bits = '40'` ⇒ máscara DMA de 40 bits, coherente con el límite de 64-bit.

`[ND]` `vram_total = 2 GiB` coincide con el «~2 GiB» del contrato de target. **No he medido la velocidad ni el tipo de VRAM** (`pp_dpm_mclk` devuelve `EBUSY`).

## 2.8 NUMA y entorno (contribuye a R-NEW-19/20)

`[LE]`: `numa_node = '-1'`, `local_cpus = 'ff'`, `local_cpulist = '0-7'`. `[LE]` `lscpu`: 1 nodo NUMA, `NUMA node0 CPU(s): 0-7`, L3 = 8 MiB, `Address sizes: 39 bits physical, 48 bits virtual`.

`[DER]` `numa_node = -1` ⇒ el driver **no** ha realizado NUMA binding; y como la máquina tiene un solo nodo, la topología no penaliza. **No hay problema de placement NUMA que atacar en esta máquina.** Eso reduce el valor esperado de cualquier experimento de NUMA-placement sobre este target, y es un hecho de entorno, no una opinion.

## 2.9 Errores AER y salud del enlace

`[LE]`: los tres contadores AER están **todos a 0**: `aer_dev_correctable` (9 líneas, `TOTAL_ERR_COR 0`), `aer_dev_nonfatal` (24 líneas, `TOTAL_ERR_NONFATAL 0`), `aer_dev_fatal` (24 líneas, `TOTAL_ERR_FATAL 0`). `broken_parity_status = '0'`. `config:0x06 status = 0x0010` ⇒ sólo `CAPABILITY_LIST`; sin bits de error pendientes.

`[LE]` `board_info = 'type : cem'`. `[ND]` No he determinado qué más campos tiene la string de board_info ni su formato completo.

## 2.10 Display — por qué la GPU puede estar dormida

`[LE]` conectores:

```text
card0-HDMI-A-1   status=connected     enabled=enabled   dpms=On    39 modos
card0-VGA-1      status=disconnected  enabled=disabled  dpms=Off    0 modos
card1-DVI-D-1    status=disconnected  enabled=disabled  dpms=Off    0 modos
card1-HDMI-A-2   status=disconnected  enabled=disabled  dpms=Off    0 modos
```

`[DER]` La sesión gráfica corre sobre la **Intel HD Graphics 4600** (`0000:00:02.0`, `i915`, `HDMI-A-1` conectado). Ningún conector de la RX550 está activo, pese a `boot_vga = '1'`. Esto **explica** (§14 CONFOUNDERS) por qué el runtime-PM puede suspenderla: no hay scanout que mantener.

**Consecuencia experimental, y es real:** cualquier futuro experimento Vulkan sobre esta máquina Cold-renderiza mientras la Intel pilota el display. No es un defecto de la GPU; es una propiedad del entorno que **debe declararse** en el contrato de benchmark, porque afecta a Firmware de la iGPU, composición del compositor y paths de presentación.

## 2.11 `reset` — ni leído ni escrito, y por diseño

`[LE]` `os.stat('/sys/bus/pci/devices/0000:01:00.0/reset')` ⇒ **`mode=0200`, `uid=0`, `gid=0`**. Es *write-only* y *root-only*. El intento de lectura devolvió `PermissionError`.

`[LE]` `reset_method = 'bus'`. `[LE]` `/sys/module/amdgpu/parameters/reset_method = '-1'` (auto).

**No he escrito `reset`. No lo escribiré desde este proyecto sin autorización explícita de nivel 4.** El modo `0200 root` significa que el propio modelo de permisos del kernel lo deja fuera del alcance de este proceso en ambos sentidos: ni puedo leerlo ni, sin `sudo`, escribirlo. Consta como seguridad positiva del sistema, no como límite que sortear.

Otros atributos con bit de escritura en este nodo, **no tocados** (sólo `stat`): `remove` (`0220`), `rescan` (`0200`), `driver_override` (`0644`), `enable` (`0644`), `power/control` (`0644`), `power/autosuspend_delay_ms` (`0644`), `power/wakeup` (`0644`), `pp_force_state` (`0644`), `power_dpm_force_performance_level` (EBUSY al leer), `link/l1_aspm` (`0644`), `local_cpus` (`0444`).

## 2.12 Qué NO se ha podido leer de este nodo, con motivo exacto

| Atributo | Modo | Resultado |
|---|---|---|
| `resource0` | `0600 root` | `PermissionError` |
| `resource0_wc` | `0600 root` | `PermissionError` |
| `resource2` | `0600 root` | `PermissionError` |
| `resource2_wc` | `0600 root` | `PermissionError` — **el que el encargo pedía** |
| `resource4` | `0600 root` | `PermissionError` |
| `resource5` | `0600 root` | `PermissionError` |
| `rom` | `0600 root` | `PermissionError` |
| `reset` | `0200 root` | `PermissionError` (write-only) |
| `msi_irqs` | directorio | `IsADirectoryError` — contiene `37`; `irq = '37'` se leyó por otra vía |
| `fw_version` | directorio | `IsADirectoryError` — se leyó vía §2.6 |
| `hwmon/hwmon1/{device,power,subsystem}` | directorios | `IsADirectoryError` |
| `/proc/driver/amdgpu` | — | **no existe** |

Anomalía registrada sin ajustar: `[LE]` `os.stat` da `st_size` de `resource0 = 268435456` (256 MiB), `resource2 = 2097152` (2 MiB), `resource4 = 256`, `resource5 = 262144`. Los tres últimos coinciden con los tamaños decodificados de `resource`. **`resource0` NO coincide**: `resource:1` dice 16 MiB, `stat` dice 256 MiB. Como el contenido de `resource0` es ilegible, `[ND]`: no sé si `st_size` es el tamaño del BAR reservado o el tamaño del fichero. Contradicción menor registrada, **no explicada**.

---

# PARTE 3 — LA MATRIZ DE CAPACIDADES

## 3.1 Por qué `vulkaninfo --summary` NO se ha ejecutado

No es una decisión de criterio: es una cadena de tres hechos verificados.

1. `[LE]` `vulkaninfo --help` (única forma documentada de no abrir el device) **no ofrece tal forma**. Su `--summary` dice literalmente: *"Show a summary of the instance and GPU's on a system."* Enumerar GPUs requiere `VkInstance` + `VkPhysicalDevice`, luego el ICD debe abrir el render node.
2. `[FUENTE]` `/usr/lib64/libvulkan_radeon.so` contiene el símbolo `drmGetDevices2` (1 ocurrencia). `/usr/lib64/libdrm.so.2` contiene los formatos `renderD%d` y `/dev/dri/%s` — es decir, libdrm **construye y abre** `/dev/dri/renderD129`.
3. `[LE]` `/dev/dri/renderD129` es `mode=0666` y `lucas` no está en `render` ⇒ **el open tendría éxito**.

Por tanto `vulkaninfo --summary` abriría el device, `drm_open` de amdgpu haría `pm_runtime_get`, y la GPU saldría de `D3hot`. Eso es una transición de estado del hardware. **PROHIBIDO en nivel de autorización < 4. No se ejecutó.** Ni `vulkaninfo`, ni `vkcube`, ni `vkcubepp`, ni `wayland-info`, ni `glxinfo`, ni `xrandr --verbose`.

Observación que refuta la clasificación «`--summary` es inofensivo»: si lo fuera, el permiso `0666` no importaría. Importa.

## 3.2 Matriz

Tres estados posibles, según lo que se haya podido hacer **sin escribir**:
`DECLARADO_EN_SYSFS` · `REQUIERE_ABRIR_DEVICE` · `NO_SABIDO`.

`DECLARADO_EN_SYSFS` sólo se usa cuando el valor está **en un fichero que he leído**, con la ruta y la línea citadas. Ninguna fila de §3.3 es `DECLARADO_EN_SYSFS`. **La matriz no se ha podido construir.** Eso es el resultado.

### 3.3 Familias de cola (`VkQueueFamilyProperties`, `/usr/include/vulkan/vulkan_core.h:3656..3661`)

```c
3656: typedef struct VkQueueFamilyProperties {
3657:     VkQueueFlags    queueFlags;
3658:     uint32_t        queueCount;
3659:     uint32_t        timestampValidBits;
3660:     VkExtent3D      minImageTransferGranularity;
3661: } VkQueueFamilyProperties;
```

Bits de familia definidos en `vulkan_core.h:2828..2832`: `GRAPHICS=0x1`, `COMPUTE=0x2`, `TRANSFER=0x4`, `SPARSE_BINDING=0x8`, `PROTECTED=0x10`.

| Propiedad | Valor | Estado | Por qué |
|---|---|---|---|
| `queueFamilyCount` | — | `REQUIERE_ABRIR_DEVICE` | sólo existe vía `vkGetPhysicalDeviceQueueFamilyProperties`. No hay sysfs equivalente |
| `queueFlags` por familia | — | `REQUIERE_ABRIR_DEVICE` | ídem |
| `queueCount` por familia | — | `REQUIERE_ABRIR_DEVICE` | ídem |
| `timestampValidBits` | — | `REQUIERE_ABRIR_DEVICE` | ídem |
| `minImageTransferGranularity` | — | `REQUIERE_ABRIR_DEVICE` | ídem |
| Cota superior de colas de HW del driver | `sched_hw_submission = '2'` | `DECLARADO_EN_SYSFS` | `/sys/module/amdgpu/parameters/sched_hw_submission:1`. Es **parámetro del driver**, no cola Vulkan. Distinto objeto |
| Jobs en cola de SW | `sched_jobs = '32'` | `DECLARADO_EN_SYSFS` | ídem, misma advertencia de objeto |
| `max_num_of_queues_per_device` | `'4096'` | `DECLARADO_EN_SYSFS` | es de ROCm/KFD, no de Vulkan |
| `num_kcq` | `'-1'` (auto) | `DECLARADO_EN_SYSFS` | `num_kcq` es de KFD. No aplica a Vulkan |

### 3.4 Timestamps y clock (necesario para N-INT-90 coste de sincronización)

Campos en `vulkan_core.h:3612..3613`: `timestampComputeAndGraphics`, `timestampPeriod`.

| Propiedad | Valor | Estado |
|---|---|---|
| `timestampPeriod` | — | `REQUIERE_ABRIR_DEVICE` |
| `timestampComputeAndGraphics` | — | `REQUIERE_ABRIR_DEVICE` |
| Reloj SCLK actual | — | `BLOQ` — `pp_dpm_sclk` y `freq1_input` dan `EBUSY` |
| Reloj MCLK actual | — | `BLOQ` — ídem |
| `RADV_PROFILE_PSTATE` existe | sí, string en el binario | `[FUENTE] EXISTE_CODIGO_QUE_SABE_LEER_UNA_VARIABLE`. **No** prueba que haya pstates que forzar ni que el experimento sea válido |

### 3.5 Compute y async compute (N-INT-45/46/47)

| Propiedad | Valor | Estado |
|---|---|---|
| `VK_QUEUE_COMPUTE_BIT` presente en alguna familia | — | `REQUIERE_ABRIR_DEVICE` |
| `VK_KHR_timeline_semaphore` soportado | — | `REQUIERE_ABRIR_DEVICE` |
| `VkPhysicalDeviceVulkan12Features::timelineSemaphore` (`vulkan_core.h:6438`) | — | `REQUIERE_ABRIR_DEVICE` |
| `VK_KHR_buffer_device_address` / `::bufferDeviceAddress` (`vulkan_core.h:6439`) | — | `REQUIERE_ABRIR_DEVICE` |
| `VK_EXT_host_query_reset` / `::hostQueryReset` (`vulkan_core.h:6437`) | — | `REQUIERE_ABRIR_DEVICE` |
| `compute_multipipe` (parámetro) | `'-1'` auto | `DECLARADO_EN_SYSFS` — objeto: driver, no Vulkan |
| `user_queue` (parámetro) | `'-1'` auto | `DECLARADO_EN_SYSFS` — objeto: ROCm, no Vulkan |
| `maxComputeWorkGroupCount[3]` (`vulkan_core.h:3573`) | — | `REQUIERE_ABRIR_DEVICE` |
| `maxComputeWorkGroupInvocations` (`:3574`) | — | `REQUIERE_ABRIR_DEVICE` |
| `maxComputeWorkGroupSize[3]` (`:3575`) | — | `REQUIERE_ABRIR_DEVICE` |
| `maxComputeSharedMemorySize` (`:3572`) | — | `REQUIERE_ABRIR_DEVICE` |

`[FUENTE]` La cadena `VK_KHR_timeline_semaphore` aparece **1 vez** en `libvulkan_radeon.so`; igual `VK_KHR_buffer_device_address`, `VK_EXT_host_query_reset`, `VK_AMD_shader_ballot`, `VK_EXT_shader_realtime_clock` → **0**, `VK_AMD_gpu_shader_float64` → **0**, `VK_AMD_shader_atomic_float` → **0**, `VK_AMD_device_query` → **0**. **Los ceros no se convierten en "no soportado"**: una extensión puede no necesitar nombre (p. ej. `VK_EXT_shader_realtime_clock` está reemplazado por `VK_KHR_shader_clock`, que sí aparece). Ausencia de cadena ⇒ `NO_SABIDO`, nunca `REFUTED`.

### 3.6 Presión de descriptor / resource-binding (N-INT-92)

Campos en `vulkan_core.h:3529..3547`:

| Propiedad | Estado |
|---|---|
| `maxBoundDescriptorSets` (`:3534`) | `REQUIERE_ABRIR_DEVICE` |
| `maxPerStageDescriptorSamplers` (`:3535`) | `REQUIERE_ABRIR_DEVICE` |
| `maxPerStageDescriptorUniformBuffers` (`:3536`) | `REQUIERE_ABRIR_DEVICE` |
| `maxPerStageDescriptorStorageBuffers` (`:3537`) | `REQUIERE_ABRIR_DEVICE` |
| `maxPerStageDescriptorSampledImages` (`:3538`) | `REQUIERE_ABRIR_DEVICE` |
| `maxPerStageDescriptorStorageImages` (`:3539`) | `REQUIERE_ABRIR_DEVICE` |
| `maxPerStageResources` (`:3541`) | `REQUIERE_ABRIR_DEVICE` |
| `maxDescriptorSetSamplers` (`:3542`) | `REQUIERE_ABRIR_DEVICE` |
| `maxDescriptorSetUniformBuffers` (`:3543`) | `REQUIERE_ABRIR_DEVICE` |
| `maxDescriptorSetStorageBuffers` (`:3545`) | `REQUIERE_ABRIR_DEVICE` |
| `maxPushConstantsSize` (`:3529`) | `REQUIERE_ABRIR_DEVICE` |
| `minUniformBufferOffsetAlignment` (`:3589`) | `REQUIERE_ABRIR_DEVICE` |
| `minStorageBufferOffsetAlignment` (`:3590`) | `REQUIERE_ABRIR_DEVICE` |
| `minMemoryMapAlignment` (`:3587`) | `REQUIERE_ABRIR_DEVICE` |
| `maxMemoryAllocationCount` (`:3530`) | `REQUIERE_ABRIR_DEVICE` |
| `VK_EXT_memory_budget` | `REQUIERE_ABRIR_DEVICE` (y adicionalmente `REQUIERE_ABRIR_DEVICE` para leer el presupuesto) |

**Pero** sí hay un hecho de sistema que **acota** estas capacidades sin abrirlas:

`[LE]` `mem_info_vis_vram_total = 268435456` (256 MiB), `mem_info_gtt_total = 6194638848`, `moverate = PermissionError` (`0600 root`). `[DER]` Con una ventana de BAR2 de 2 MiB (§2.3), los límites de descriptor/buffer de Vulkan se ejercitan bajo una restricción de superficie de 2 MiB. Cualquier valor de `maxPerStageDescriptor*` que se obtenga estará por debajo de ese techo. **Esto es una advertencia de validez experimental, no una propiedad de la matriz.**

### 3.7 Variación de pipeline-state (N-INT-93)

| Propiedad | Estado |
|---|---|
| `maxViewports` (`:3583`) | `REQUIERE_ABRIR_DEVICE` |
| `maxViewportDimensions[2]` (`:3584`) | `REQUIERE_ABRIR_DEVICE` |
| `viewportBoundsRange[2]` (`:3585`) | `REQUIERE_ABRIR_DEVICE` |
| `viewportSubPixelBits` (`:3586`) | `REQUIERE_ABRIR_DEVICE` |
| `maxColorAttachments` (`:3605`) | `REQUIERE_ABRIR_DEVICE` |
| `maxDrawIndirectCount` (`:3580`) | `REQUIERE_ABRIR_DEVICE` |
| `maxComputeWorkGroupSize[3]` (`:3575`) | `REQUIERE_ABRIR_DEVICE` |
| `VK_EXT_extended_dynamic_state` | `[FUENTE]` 3 ocurrencias en el binario ⇒ `EXISTE_CODIGO`. Estado de soporte: `NO_SABIDO` |
| `pp_dpm_*` (tabla de p-states) | `BLOQ` — `EBUSY` |
| `pp_num_states` | `BLOQ` — `EBUSY` |

### 3.8 Lo que hay que hacer para desbloquear la matriz

Se dice exactamente qué, no «más análisis»:

```text
1. Una autorización de nivel 4 que cubra, explícitamente:
     · abrir  /dev/dri/renderD129  en modo render (NO /dev/dri/card1)
     · aceptar  runtime-PM resume  de  D3hot -> activo   como efecto previsto
     · NO aceptar reset, NO aceptar modprobe/rmmod, NO aceptar escritura a /sys/class/drm/*
2. Con esa autorización, la matriz se llena con UNA llamada:
     vkEnumeratePhysicalDevices + vkGetPhysicalDeviceQueueFamilyProperties
     + vkGetPhysicalDeviceProperties2 con pNext de VkPhysicalDeviceTimestampProperties
   Más un volcado de VkPhysicalDeviceLimits y VkPhysicalDeviceVulkan12Features.
   Eso NO es un experimento: es una única enumeración. Coste ≈ segundos.
3. Alternativa sin abrir el device, y es la que este documento deja como
   NOT_DETERMINED: derivar las capacidades de RADV desde su CÓDIGO FUENTE.
   Hoy eso es imposible en esta máquina (ver §4.3).
```

Sin (1) o sin (3), la matriz **no existe**, y los experimentos N-INT-90/91/92/93 y N-INT-45/46/47 **no se pueden diseñar**, sólo adivinar.

---

# PARTE 4 — CONTRADICCIONES Y BLOQUEOS QUE HAY QUE RESOLVER ANTES DE EDIFICAR

## 4.1 ¿Hay más de un ICD capable de tomar esta tarjeta? — RESUELTO, y no

- `[LE]` `/usr/share/vulkan/icd.d/` tiene 15 drivers × 2 arquitecturas, pero **sólo uno** puede tomar un ASIC AMD: `radeon_icd.*.json` → RADV. **No hay `amd_icd.*.json`** ⇒ no hay AMDVLK. No hay conflicto RADV↔AMDVLK.
- `[LE]` No hay `nouveau_icd`.toml de toma sobre hardware AMD: `nouveau_icd.*.json` apunta a `libvulkan_nouveau.so`, que sólo sirve GPUs NVIDIA. **Sin conflicto real.**
- `[LE]` `/etc/vulkan/icd.d/` tiene 0 entradas ⇒ **ningún ICD está deshabilitado por el sistema** a propósito.
- `[LE]` `0000:01:00.0 → driver = amdgpu`; `[LE]` `/proc/modules` no contiene `nouveau`.

**Veredicto: un solo ICD elegible para el ASIC AMD. Sin contradicción aquí.**

## 4.2 La contradicción que sí importa: el permiso no protege

```text
Dato A [LE]: GPU en D3hot, runtime_status = suspended, holders vacío.
Dato B [LE]: renderD129 mode 0666; el usuario NO está en el grupo render.
Dato C [FUENTE]: RADV -> drmGetDevices2 (libvulkan_radeon.so)
                 libdrm -> "renderD%d", "/dev/dri/%s"  (construye y ABRE)
Dato D [LE]: vulkaninfo --help no ofrece ninguna forma de no enumerar GPUs.
```

`[DER]` A∧B∧C∧D ⇒ **cualquier cliente Vulkan ejecutado como `lucas` despertará la GPU.** El modelo de permisos del kernel, que en `card1` sí bloquea (0660 root:video), **no** bloquea en el render node. El riesgo no es teórico, es el camino por defecto de cualquier herramienta Vulkan.

**Ésta es la contradicción que había que mirar, y es la que condiciona todo lo demás.** No la he «resuelto»: la he registrado y la he respetado no abriendo nada.

## 4.3 Corpus: no hay ni Mesa ni fuentes de amdgpu

- `[LE]` (heredado del nodo principal, no repetido) `RESEARCH/` no contiene Mesa, RADV, radeonsi ni LLVM.
- `[LE]` **Confirmado y ampliado por este nodo**: `/usr/src/kernels/7.1.3-200.nobara.fc44.x86_64/` tiene 22 938 ficheros, de los cuales **148 son `.c`, y los 148 están bajo `scripts/`** (utilidades de build). `drivers/pci/` contiene 9 entradas y **ninguna** es `.c` (sólo `Kconfig`, `Makefile` y 7 directorios). `drivers/gpu/` idem. **Cero fuentes de drivers de kernel instaladas.**

Consecuencia dura: la vía «derivar la matriz desde el código de RADV» y la vía «verificar en fuente si un `read()` de sysfs puede hacer `pm_runtime_get`» están **ambas** cerradas en esta máquina. No con "cuesta más", sino con: **el objeto no existe en disco.**

## 4.4 Contradicciones menores registradas sin ajustar

| # | Contradicción | Estado |
|---|---|---|
| C1 | `resource:1` dice BAR0 = 16 MiB; `stat(resource0).st_size` = 256 MiB | `NOT_DETERMINED`. Contenido de `resource0` ilegible |
| C2 | `vbios_version = 'xxx-xxx-xxx'` | `NOT_DETERMINED`. Reportado, no interpretado |
| C3 | `boot_vga = 1` pero ningún conector de `card1` activo | **Resuelta**: la sesión corre en la Intel HD 4600, §2.10 |
| C4 | `modinfo` de disco dice `srcversion D68004925455E20A24C2B87`; `/sys/module/amdgpu/srcversion` dice lo mismo | **Resuelta**: coinciden. El módulo cargado es el del árbol de la distribución para este kernel |
| C5 | `/sys/module/amdgpu/version` no existe | **Resuelta como hecho**: este build no exporta `version`. No se busca más |

---

# PARTE 5 — QUÉ IDEA DEL USUARIO QUEDA EJECUTABLE, Y CUÁL NO

Severidad aplicada sin excepción, como pidió el encargo. Ninguna idea se mejora aquí.

## 5.1 Ejecutable AHORA, con este documento

| Idea | Qué queda ejecutado | Qué es y qué no es |
|---|---|---|
| **N-INT-89** «matriz de capacidades de colas Vulkan» | **Ejecutada y BLOQUEADA.** He producido: identidad completa de la pila con hashes; mapa de BARs decodificado y contrastado; topología PCIe y techo de ancho de banda medido; estado de energía; **la definición exacta de la matriz** (`vulkan_core.h:3656..3661` + `:3529..3616` + `:6437..6439`) con cada celda clasificada | Sigue siendo **capability audit, no mejora**. Y además: **incompleto**, porque el 100 % de las celdas es `REQUIERE_ABRIR_DEVICE`. No ha producido ninguna capacidad. Lo que ha producido es **el conjunto de hechos sin los cuales cualquier experimento Vulkan posterior no se puede diseñar**, que es exactamente el valor que la revisión le atribuyó |
| **R-NEW-37..40** (PCIe) | **Respondidas negatively y sin tocar nada.** El enlace está en Gen2 x4 porque el puente `8086:0c01` declara máximo Gen2; `amdgpu` no lo capta (`pcie_gen_cap=0`, `pcie_lane_cap=0`). Techo medido ≈ 2.00 GB/s/dir vs 6.40 GB/s/dir de capacidad de la tarjeta | **Respondidas**, no resueltas. La vía «subir el PCIe desde el driver» queda `PROVEN_ABSENT` como palanca de driver. Si un ajuste de BIOS elevara el puente, eso es un experimento de BIOS, no de driver, y sigue `[ND]` |
| **R-NEW-19/20** (entorno) | **Cerradas como marco.** Host = i7-4790, 1 nodo NUMA, `numa_node = -1`, 8 MiB L3, máscara DMA 40 bits, desktop en la Intel HD 4600, GPU sin scanout y auto-suspendiendo a 5 s | Cerradas como **declaración de validez**, no como mejora. No hay problema de NUMA-placement que atacar en esta máquina: es un hecho que **rebaja** el valor esperado de esa línea |
| **R-NEW-83..88** (comparación Mesa por workload / versiones / workarounds) | **BLOQUEADAS, y ahora por una razón más fuerte.** No hay Mesa en el corpus (heredado), no hay fuentes de kernel (`§4.3`), y la comparación por workload exigiría ejecutar workloads ⇒ abrir el device | El audit de versiones de *este* sistema **sí** está hecho (§1): Mesa 26.2.3, RADV 26.2.3, loader 1.4.341, LLVM 22.1.8, kernel 7.1.3-200.nobara.fc44. Eso es un hecho cerrado. La comparación *entre* versiones sigue cerrada |

## 5.2 NO ejecutable, y no por falta de esfuerzo

| Idea | Por qué no |
|---|---|
| **N-INT-90** coste de sincronización | Necesita `timestampPeriod`, `timestampValidBits` y un reloj functioning ⇒ todos `REQUIERE_ABRIR_DEVICE`. `freq1_input` da `EBUSY`. **No se puede ni medir** |
| **N-INT-91** granularidad de command buffers | Necesita `VkQueueFamilyProperties.queueCount` y `timestampValidBits` ⇒ `REQUIERE_ABRIR_DEVICE` |
| **N-INT-92** presión de descriptor / resource-binding | Necesita toda la familia `maxPerStageDescriptor*` / `maxDescriptorSet*` ⇒ `REQUIERE_ABRIR_DEVICE`. Se ha establecido un techo de sistema independiente (2 MiB de ventana), pero no los valores |
| **N-INT-93** variación de pipeline-state | Igual. `pp_dpm_*` y `pp_num_states` dan `EBUSY` |
| **N-INT-45/46/47** async compute | `timelineSemaphore`, `bufferDeviceAddress`, `hostQueryReset` — las tres en `REQUIERE_ABRIR_DEVICE`. Lo único cerrado es que el ICD las implementa |
| **R-NEW-99** | Confirmado como estaba: **NO ES EXPERIMENTO. Infraestructura.** Este documento es exactamente eso. No se le ha cambiado el estatus |

## 5.3 Lo que este documento NO es

No es una mejora. No es un benchmark. No es una capability matrix (es el **esqueleto** de una, con las celdas vacías y la razón de cada vacío). No ha movido un solo bit de estado del hardware. No ha abierto `/dev/dri/renderD129`. No ha ejecutado `vulkaninfo`. No ha escrito en `/sys/class/drm/*`, ni en `/sys/kernel/debug/dri/*`, ni en `reset`, ni en `remove`, ni en `rescan`.

Lo que sí ha producido, y es real: **hechos verificados con cita que antes no estaban registrados**, y **tres bloqueos correctamente caracterizados** (D3hot, permisos que no protegen, ausencia de fuentes) que impiden seguir construyendo encima sin autorización.

---

# PARTE 6 — BITÁCORA DE LA EJECUCIÓN

Todo lo ejecutado fue `python3` con `open()`/`os.walk`, `rpm -q`/`-qf`/`-ql`, `readelf`, `modinfo`, `lscpu`, `nproc`, `uname`, `os.stat`, `os.readlink`, `os.listdir`, `id`, y `sha256` por streaming. Ninguna escritura. Ningún `open(..., 'w')`. Ningún `write()` a sysfs. Ningún `modprobe`/`rmmod`/`insmod`. Ningún `dmesg`/`journalctl`/`strace`.

Comandos de terceros ejecutados, con su justificación de no-escritura:

| Binario | Por qué se considera sólo-lectura |
|---|---|
| `vulkaninfo --help` | Termina por `argv` antes de crear instancia. **Único uso que hago de `vulkaninfo`.** No se ejecutó ningún otro modo |
| `readelf -n` / `-d` | Lee secciones ELF del fichero |
| `modinfo amdgpu` | Lee la sección `.modinfo` del `.ko` en disco. No interactúa con el módulo cargado |
| `rpm -q/-qf/-ql` | Consulta la base de datos RPM en local |
| `lscpu` | Lee `/proc/cpuinfo` y `/sys/devices/system/cpu` |
| `id` | Lee la base de credenciales del proceso |

## 6.1 Estado de la GPU al terminar el nodo

`[LE]` relectura final, idéntica a la inicial:

```text
power_state              = 'D3hot'
power/runtime_status     = 'suspended'
enable                   = '1'
current_link_speed       = '5.0 GT/s PCIe'
current_link_width       = '4'
/sys/module/amdgpu/holders = []
```

**Estado antes = estado después.** El nodo no cambió el estado del hardware. Este es el criterio de éxito de este encargo.

## 6.2 Limitaciones declaradas de este documento

1. Las ~30 celdas `REQUIERE_ABRIR_DEVICE` **no** se han medido. No hay ni un solo valor Vulkan en este fichero, y eso es deliberado.
2. `resource0_wc` y `resource2_wc` — que el encargo pedía explícitamente — **no** se han podido leer (`0600 root`). Se dice en §2.12 y §2.3 en lugar de inventar.
3. No se ha descargado nada de internet. No se ha contrastado ningún device ID, subsistema ni versión de firmware contra una base de datos externa. Todo device-ID y familia de chip cited viene del sysfs/config-space/local.
4. No he determinado la causa del x4 (§2.4), ni el significado de `vbios_version = 'xxx-xxx-xxx'` (§2.1), ni la discrepancia de tamaño de `resource0` (§4.4 C1).
5. La conclusión «un `read()` de sysfs no despertó la GPU» es una observación de esta ejecución, no una garantía estructural: no hay fuente de amdgpu para verificarlo (§2.5.1, §4.3).
6. No se ha modificado ningún otro fichero del árbol. `CENSUS-CAPACIDADES.md` no existía antes de este nodo (`os.listdir` previo: sin esa entrada).

## 6.3 Una frase para el nodo principal

> La RX550 está **identificada sin ambigüedad** (`1002:699F` rev `0xC7`, `amdgpu`, `renderD129`), pero está **dormida en D3hot** y **cualquier cliente Vulkan la despertaría** porque `/dev/dri/renderD129` es `0666`. La capability matrix de N-INT-89 **no se puede construir en nivel de autorización < 4**; queda delivering su esqueleto exacto, el mapa de BARs, y un techo PCIe medido de ≈2.00 GB/s/dir impuesto por el puente de chipset en Gen2 que **cierra la vía PCIe de R-NEW-37..40 sin necesidad de escribir nada**.