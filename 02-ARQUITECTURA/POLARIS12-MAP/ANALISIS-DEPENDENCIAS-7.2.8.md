# ANALISIS-DEPENDENCIAS-7.2.8.md — Dependencias, Display, PCIe, Firmware, Config

**FASE:** dependency analysis. **Código modificado: 0. Experimentos ejecutados: 0.
Clasificaciones semánticas: 0.** Predecesor: `INVENTARIO-ESTRUCTURAL-7.2.8.md`.

## Provenance

`BASELINE-B` = `linux-7.2.8`, `sha256 12e8d5a973d1ad7c5a5c69882e4022b131ed715db7003fdcd760ddf8c3e51941`
(verificado contra `sha256sums.asc`; **firma PGP no verificada** — `NOT_AVAILABLE`).
Análisis en `/home/lucas/rx550-analysis-7.2.8/`. Referencia inmutable
`RX550-INVESTIGACION/rx550-upstream-7.2.8/` **no modificada**.
`BASELINE-A` = kernel en ejecución `7.1.3-200.nobara.fc44`.
Config efectiva leída de `/boot/config-7.1.3-200.nobara.fc44` (12 654 líneas).

---

## 0. Correcciones a afirmaciones previas

| # | afirmación anterior | estado real |
|---|---|---|
| 1 | «PCIe se ajusta con `pcie_gen_performance`, `pcie_gen_power_saving`, `pcie_aspm`, `pcie_link_control`» | **FALSA.** Esos son campos internos `data->pcie_gen_*` de `smu7_hwmgr.c:1944-1951`, **no** parámetros de módulo. Los reales son `pcie_gen2`, `pcie_gen_cap`, `pcie_lane_cap`, `aspm` |
| 2 | «el controlador Haswell limita PCIe» | era `INFERRED`; **ahora OBSERVATION** (§4) |
| 3 | includes de `asic_reg` por fichero | método **insuficiente**: solo includes directos. El cierre transitivo no se calculó (§8) |

---

## 1. Hardware — separaciones cerradas

| capa | valor | clase |
|---|---|---|
| `GPU_CAPABILITY` | `1002:699f` rev `0xc7`; Polaris12/GFX8; VRAM 2 147 483 648 B; visible 268 435 456 B | FACT |
| `PCI_LINK_CAPABILITY` (endpoint) | 8,0 GT/s ×8 | FACT |
| `PCI_LINK_CAPABILITY` (**root port `0000:00:01.0`**) | **5,0 GT/s ×16** | FACT |
| `CURRENT_LINK_STATE` | 5,0 GT/s ×4 (ambos) | OBSERVATION |
| `MOTHERBOARD_CPU_LIMITATION` | **el root port no anuncia más de 5,0 GT/s** | **OBSERVATION** — antes `INFERRED` |
| `DRIVER_CONFIGURATION` | `pcie_gen2=-1` `pcie_gen_cap=0` `pcie_lane_cap=0` `pcie_p2p=Y` `aspm=-1` | FACT |
| `GTT` | 6 194 638 848 B totales | FACT |
| `KERNEL` / `MESA` | 7.1.3-200.nobara.fc44 / 26.2.3 | FACT |

**Consecuencia que cierra una pregunta de H-PCIE:** el objetivo «Gen3» **no es
alcanzable en esta plataforma** — no porque el driver lo limite, sino porque el
root port declara `max_link_speed = 5.0 GT/s`. La Gen3 es una capacidad de la
tarjeta que esta placa no puede ejercer. Lo que queda abierto es solo el
**ancho**: el endpoint tiene 8 lanes y el root port 16, pero se negocia ×4.
Causa (cableado, lanes downgraded, o negociación) = **`UNKNOWN`**.
PCIe sigue siendo `HYPOTHESIS_CANDIDATE`. **No se le llama cuello de botella.**

---

## 2. `boot_vga` — lo que está establecido y lo que no

**OBSERVATION:** `card1: boot_vga=1`; `card0: boot_vga` vacío. Panel activo en
`card0-HDMI-A-1`; `card1-DVI-D-1` y `card1-HDMI-A-2` ambos `disconnected`.

**DERIVATION (de `amdgpu_drv.c:2377`, cuerpo de `amdgpu_pci_probe`):**

```c
if ((pdev->class >> 8) == PCI_CLASS_DISPLAY_VGA ||
    (pdev->class >> 8) == PCI_CLASS_DISPLAY_OTHER) {
        if (drm_firmware_drivers_only() && amdgpu_modeset == -1)
                return -EINVAL;
}
...
adev = devm_drm_dev_alloc(&pdev->dev, &amdgpu_kms_driver, typeof(*adev), ddev);
```

1. La clase PCI de la RX550 **es** `DISPLAY_VGA` (`0x030000` confirmado), así
   que ese gate se evalúa.
2. `amdgpu_modeset` vale `-1` (efectivo, §5), luego la condición de rechazo
   queda reducida a `drm_firmware_drivers_only()`.
3. **El probe registra siempre `amdgpu_kms_driver`.** No existe ruta de registro
   sin KMS en la implementación actual.

**UNKNOWN:** qué establece `boot_vga` en el kernel y qué etapas del boot
dependen de él. No se leyó `drivers/pci/pci.c` ni el camino de fbcon.
**El fichero exacto a leer está identificado**, no se lee aquí por alcance.

**Conclusión parcial:** `boot_vga=1` **no** implica que la RX550 necesite KMS
para acelerar. Implica que el kernel la señala como dispositivo VGA de arranque,
y que el probe de amdgpu entra por el gate de display. Son dos hechos
distintos. No se resuelve la cadena de boot aquí.

---

## 3. §1 — La frontera de display: resultado

**Este es el resultado más útil de la iteración.**

| nivel de acoplamiento | resultado |
|---|---|
| **includes de fuente** | **0 de 631** ficheros del core incluyen `../display/` |
| **llamadas al gestor de display** | **6 símbolos distintos, 8 call sites**: `amdgpu_dm_backlight_caps` (2), `amdgpu_dm_abm_level` (2), `amdgpu_dm_set_pixel`, `amdgpu_dm_plane_get_scanout_buffer`, `amdgpu_dm_irq`, `amdgpu_dm_debugfs` |
| **símbolos de display que usa el core** | `drm_connector_*` (29+27+14), `drm_encoder_init` (21), `drm_dp_dpcd_writeb` (9)… → acoplado al **subsistema DRM**, no a `amd/display/` |
| **enlazado** | `amd/amdgpu/Makefile:332` `include $(FULL_AMD_DISPLAY_PATH)/Makefile`, `:334` `amdgpu-y += $(AMD_DISPLAY_FILES)` — **incondicional** |
| **punto de entrada** | `amdgpu_pci_probe` → `devm_drm_dev_alloc(..., &amdgpu_kms_driver, ...)` — **siempre el driver KMS** |

**Lectura:** el acoplamiento de `amd/display/` (1 166 ficheros, 592 729 líneas)
con el core **no está en el código**: está en **tres** puntos concretos —

1. `Makefile:332,334` (enlazado),
2. 8 llamadas `amdgpu_dm_*`,
3. el registro en `amdgpu_kms_driver` dentro del probe.

**Eso hace la pregunta del brief reformulable y más barata:** no «¿podemos
borrar 1 166 archivos?», sino «¿qué Rompe si `amdgpu_y` deja de incluir
`AMD_DISPLAY_FILES`, se sustituyen esas 8 llamadas, y el registro deja de usar
el driver KMS?». Los 1 166 archivos siguen siendo necesarias para el camino
de display, pero **su acoplamiento con el resto del driver es de 8 llamadas**.

`P = CANDIDATE_FOR_REMOVAL`. **No `REMOVE_CONFIRMED`.** No se ha eliminado nada
y no se ha medido qué se pierde.

---

## 4. §9 — Configuración efectiva del driver en ejecución

De `/boot/config-7.1.3-200.nobara.fc44`:

| símbolo | valor | consecuencia |
|---|---|---|
| `CONFIG_DRM_AMDGPU` | **`m`** | el driver es módulo |
| `CONFIG_DRM_AMDGPU_SI` | **`y`** | **15 objetos de generaciones previas SÍ se compilan** |
| `CONFIG_DRM_AMDGPU_CIK` | **`y`** | ídem |
| `CONFIG_DRM_AMDGPU_USERPTR` | `y` | userptr write |
| `CONFIG_DRM_TTM` / `_HELPER` | `m` / `m` | TTM presente |
| `CONFIG_DRM_SCHED` | `m` | planificador presente |
| `CONFIG_DRM_KMS_HELPER` | `y` | helpers KMS |
| `CONFIG_DRM_BUDDY` | `m` | DRM buddy allocator |
| `CONFIG_DRM_EXEC` / `DRM_SUBALLOC_HELPER` | `m` / `m` | |
| `CONFIG_VGA_SWITCHEROO` | `y` | APTX — y el quirk de `0x699f` es de otro subsystem (§`AMDGPU-POLARIS12-DECISION-POINTS.md`) |
| `CONFIG_ACPI_VIDEO` | `m` | |
| `CONFIG_HMM_MIRROR` | `y` | **habilita `amdgpu_hmm.o`** |
| `CONFIG_AMD_IOMMU` | `y` | IOMMU activo |
| `CONFIG_FW_LOADER` | `y` | carga de firmware |

**Convierte un hecho estructural en un hecho de ejecución:** los 15 objetos
`CIK` + `SI` que el inventario marcó como inalcanzables para Polaris12
**están dentro del módulo que está cargado ahora mismo**. No se eliminan por
configuración en el kernel actual; se eliminarían deshabilitando dos flags
**al compilar**. `SYSTEM_CHANGE`: no ejecutado.

---

## 5. §7 — GTT: qué se puede observar y qué no

| observable | disponibilidad |
|---|---|
| `mem_info_vram_total/used` | **disponible** |
| `mem_info_vis_vram_total/used` | **disponible** |
| `mem_info_gtt_total/used` | **disponible** |
| `mem_info_preempt_used` | disponible |
| `debug_evictions` | **`N` — registro de evictions DESACTIVADO** |
| `vm_fault_stop` | `0` |
| `no_queue_eviction_on_vm_fault` | `0` |
| `vm_size` / `vm_block_size` / `vm_fragment_size` / `vm_update_mode` | `-1` (auto) |
| `gttsize` / `vramlimit` | nombre presente en `parameters/`, **valor no legible** |
| `/sys/kernel/debug/dri/*` | **`NOT_AVAILABLE_BY_PERMISSION`** — verificado 2026-09-28: `debugfs` **sí está montado** (`rw,nosuid,nodev,noexec,relatime`), pero `/sys/kernel/debug` tiene modo `drwx------` duenio `root` y `ls` devuelve `Permiso denegado`. **No** es `ABSENT`, **no** es `EMPTY`, **no** es `NOT_SUPPORTED`. No se sortea el bloqueo de `sudo` |
| `vm_bad_pages` / contadores de page fault | **no presentes en sysfs** |

**`GTT_PRESSURE = UNKNOWN`.** No hay lectura de presión: `debug_evictions=N` y
los contadores de fault no son accesibles por esta vía. El valor 5,9 GiB es un
tamaño configurado, no una presión observada. **No se modifica GTT.**

Para cerrarlo harían falta los contadores de `debugfs` de amdgpu
(`amdgpu_fence_info`, `amdgpu_gem_*`, `amdgpu_vm_*`), que exigen privileges que
no se han pedido.

---

## 6. §8 — Firmware: `PRESENT` ≠ `LOADED` ≠ `USED` ≠ `REQUIRED`

**PRESENT** — `/lib/firmware/amdgpu/`: 677 entradas, 26 MB, 39 familias de ASIC.

Archivos **`polaris12_*`**: **20**. Incluyen variantes de stepping:
`polaris12_me.bin.xz` **y** `polaris12_me_2.bin.xz`; igual `ce`, `mec`, `mec2`,
`pfp`. **Tu tarjeta es rev `0xc7`** — qué variante se carga depende de la
revisión, y esa regla vive en el código, no en el nombre del fichero.

### Cadena de seleccion — hay DOS mecanismos distintos

**Mecanismo 1 · microcodigo de grafica (GFX8): `MODULE_FIRMWARE`, no
`amdgpu_ucode_request`.** En `amd/amdgpu/gfx_v8_0.c:158-169` hay **11 nombres
distintos** de firmware `polaris12` declarados con `MODULE_FIRMWARE`: `ce`, `ce_2`,
`pfp`, `pfp_2`, `me`, `me_2`, `mec`, `mec_2`, `mec2`, `mec2_2`, `rlc`. La cadena
`polaris12` aparece 12 veces en el fichero, pero eso son **ocurrencias**, no
declaraciones. *Correccion 2026-09-28: antes se decia "12 declaraciones".* **No existe `polaris12_rlc_2`**: RLC solo tiene
una variante.

**Mecanismo 2 · SDMA: nombre derivado de la version de IP.**
`amdgpu_sdma_init_microcode()` (`amdgpu_sdma.c:204`):

```c
amdgpu_ucode_ip_version_decode(adev, SDMA0_HWIP, ucode_prefix, sizeof(ucode_prefix));
if (instance == 0)
        amdgpu_ucode_request(adev, ..., "amdgpu/%s.bin",   ucode_prefix);
else
        amdgpu_ucode_request(adev, ..., "amdgpu/%s%d.bin", ucode_prefix, instance);
```

Produce `amdgpu/polaris12_sdma.bin` (instancia 0) y `amdgpu/polaris12_sdma1.bin`.
**El nombre depende de la version de IP, no de la revision del ASIC.**

`amdgpu_ucode_request()` (`amdgpu_ucode.c:1504`) recibe el nombre como
`fmt` + varargs y llama a `request_firmware` en `:1520`. Callers: `amdgpu_cgs.c:356`,
`amdgpu_device.c:1956` (`gpu_info`), `amdgpu_isp.c:82`, `amdgpu_mes.c:727/731`,
`amdgpu_psp.c:3933/3958/3961/4132/4135/4413/4416/4452/4581`,
`amdgpu_sdma.c:216/220`, `amdgpu_umsch_mm.c:135`, `amdgpu_uvd.c:264`,
`amdgpu_vce.c:176`, `amdgpu_vcn.c:112/119`, `amdgpu_vpe.c:240`.

### Selector `_2` — `CLOSED` (2026-09-28)

**Correccion**: una version anterior de este documento decia que el selector `_2`
"no esta localizado". **Es falso: esta localizado y no depende de la revision.**

Localizado en `amd/amdgpu/gfx_v8_0.c`, funcion `gfx_v8_0_init_microcode()`:

```c
if (adev->asic_type >= CHIP_POLARIS10 && adev->asic_type <= CHIP_POLARIS12) {
        err = amdgpu_ucode_request(adev, &adev->gfx.pfp_fw,
                                   AMDGPU_UCODE_OPTIONAL,
                                   "amdgpu/%s_pfp_2.bin", chip_name);
        if (err == -ENODEV)
                err = amdgpu_ucode_request(adev, &adev->gfx.pfp_fw,
                                           AMDGPU_UCODE_REQUIRED,
                                           "amdgpu/%s_pfp.bin", chip_name);
} else { /* solo la variante sin _2, REQUIRED */ }
```

Patron identico para `pfp` (`:983-997`), `me`, `ce`, `mec` y `mec2`.
**`rlc` solo pide `"amdgpu/%s_rlc.bin"`** — no existe rama `_2`, que explica por
que no hay `polaris12_rlc_2`.

#### Cadena demostrada

```
POLARIS12, revision 0xc7
  |
  +-- [OBSERVATION] pci->revision = 0xC7        sysfs, dos instrumentos
  +-- [OBSERVATION] adev->asic_type = CHIP_POLARIS12
  |        amdgpu_drv.c:2041  {0x1002, 0x699F, ..., CHIP_POLARIS12}
  |
  +-- [TRANSFORMACION] switch (adev->asic_type) -> chip_name = "polaris12"
  |        gfx_v8_0.c:971-972
  |
  +-- [CONDICION] asic_type >= CHIP_POLARIS10 && asic_type <= CHIP_POLARIS12
  |        gfx_v8_0.c:983     *** NO LEE adev->rev ***
  |
  +-- TRUE  -> request "amdgpu/polaris12_pfp_2.bin"   [OPTIONAL]
  |              |
  |              +-- -ENODEV -> "amdgpu/polaris12_pfp.bin"  [REQUIRED]
  |
  +-- FALSE -> no aplica a Polaris12
```

**`revision 0xc7` NO PARTICIPA EN EL SELECTOR `_2`.** Intervienen solo dos cosas:
estar en el rango de `asic_type` Polaris10-12, y que el fichero `_2` resuelva en
el cargador de firmware. Es un **orden de preferencia por disponibilidad**, no una
variante elegida por stepping.

| bloque | ¿depende de la revision? | estado |
|---|---|---|
| grafica (`{ce,pfp,me,mec,mec2}[_2].bin`, `rlc`) | **NO** — `asic_type` + disponibilidad | `CLOSED` |
| SDMA (`polaris12_sdma.bin`, `polaris12_sdma1.bin`) | **NO** — version de IP | `SELECTABLE` |

### Nivel alcanzado y las separaciones que NO se cruzan

`PRESENT` -> **`REFERENCED_BY_CODE`** -> **`SELECTABLE`** -> **`REQUESTED`: NO
alcanzado**.

| nivel | significado | firmado aqui |
|---|---|---|
| `PRESENT` | el fichero existe en `/lib/firmware/amdgpu/` | SI (20 `polaris12_*`) |
| `REFERENCED_BY_CODE` | el codigo lo nombra | SI (ambos mecanismos) |
| `SELECTABLE` | el selector que lo elige esta identificado | SI (`CLOSED`) |
| `REQUESTED` | el cargador lo pidio en runtime | **NO** |
| `LOADED` | se copio a memoria y valido | **NO** |
| `USED` | un bloque funcional lo consume | **NO** |

**`PRESENT` no es `REQUESTED`.** Las variantes `_2` estan presentes y el codigo
las prefiere, pero que el cargador las resuelva no se ha observado.

**`REQUESTED` no es `LOADED`.** Habria que leer el `dmesg` de la carga de ucode.

**`LOADED` no es `USED`.** Que un microcodo se cargue no prueba que un bloque
funcional lo este usando despues.

Esta iteracion se ejecuto **exclusivamente por lectura de codigo**; los tres
ultimos niveles exigen observacion de runtime, no autorizada.

**REQUIRED** — `UNKNOWN`. La interfaz de firmware es contractual; que bloques IP
la necesitan para Polaris12, no esta trazado.

---

## 7. §3 — J / K / L / O

| relación | símbolos | ficheros | estado |
|---|---|---|---|
| **J · GEM** | `amdgpu_gem_object_create`, `ttm_bo_init` | `amdgpu_gem.c`, `amdgpu_object.c`, `amdgpu_ttm.c`, `amdgpu_dma_buf.c`, `amdgpu_cs.c` | **PARCIAL.** Localizado el punto de integración TTM (`amdgpu_object.c`). **CLOSURE TRANSITIVO NO CALCULADO** |
| **K · GPUVM** | `amdgpu_vm_init`, `amdgpu_vm_map` | `amdgpu_vm.c`, `amdgpu_vm_cpu.c`, `amdgpu_vm_sdma.c`, `amdgpu_csa.c`, `amdgpu_kms.c` | **PARCIAL** — mismos 4 ficheros + 2 más |
| **L · scheduler** | `drm_sched_init`, `drm_sched_job_add` | `amdgpu_device.c`, `amdgpu_fence.c`, `amdgpu_cs.c`, `amdgpu_sync.c`, `amdgpu_ttm.c` | **PARCIAL** |
| **O · firmware** | `request_firmware` | `amdgpu_ucode.c:1520` | **PARCIAL** — ver §6 |

**Por qué `PARCIAL` y no `CERRADO`:** no se generó índice de símbolos.
`cscope`/`ctags` no se ejecutaron. Localizar un símbolo por `grep` da
**coordenadas, no significado** (§4.2 del `AGENTS.md`): un caller de
`amdgpu_vm_init` no demuestra que el camino sea obligatorio para esta GPU.
`CALLERS`/`CALLEES` completos siguen **`UNKNOWN`**.

---

## 8. §4 — `amd/include`: universo medido

| | |
|---|---:|
| headers en `amd/include` | 564 |
| de los cuales `asic_reg/` | **488** |
| líneas de `asic_reg/` | **4 977 963** = **97,3 %** de `amd/include` |
| líneas de `amd/include` no-`asic_reg` | 138 431 |
| subdirectorios IP en `asic_reg/` | **39** |

Los 39 bloques: `athub bif clk dce dcn df dpcs gc gca gmc hdp lsdma mmhub mp
nbif nbio oss pcie pwr rsmu sdma sdma0…sdma7 smu smuio thm umc uvd vce vcn vpe
wafl xgmi`.

**Cierre transitivo: `CLOSED` (2026-09-28).** Resuelto con `tools/kdeps.c`.

Herramienta: written en C, no descargada. Fuentes `6e0961a15…` (pre-arity) →
`78b9de4f2c…` tras corregir el defecto de comentarios. Binario en `/tmp`.

**Procedencia de las rutas `-I`** — extraídas de 8 Makefiles, no elegidas a mano:

| origen | nº | clave |
|---|---:|---|
| `amdgpu/Makefile:34-45` (`ccflags-y`) | 12 | `FULL_AMD_PATH=$(src)/..`, `DISPLAY_FOLDER_NAME=display` |
| `pm/Makefile:23-34+` | 12+ | `FULL_AMD_PATH` |
| `display/Makefile:29-40+` | 21 | `FULL_AMD_DISPLAY_PATH` |
| `ras/Makefile:26-27` | 2 | `AMD_GPU_RAS_FULL_PATH`, `AMD_GPU_RAS_MGR=ras_mgr` |
| `pm/powerplay/Makefile`, `display/amdgpu_dm/Makefile`, `amdkfd/Makefile`, `acp/Makefile` | 3 | incluidos transitivamente |
| Kbuild estándar | 4 | `-I. -Iinclude -Iarch/x86/include -Iinclude/uapi` |
| **total distintos** | **50** | |

**`amdgpu/Makefile` es solo la primera capa**: de ahí salen 12 rutas; `pm/` y
`display/` añaden ~38. Include clave que faltaba en el primer intento:
`-I.../include/asic_reg`, que es la razón de que los headers de registros se
incluyan **sin** el prefijo `asic_reg/`.

**El `-I` que faltaba era real, pero el último pendiente era un falso positivo de
la herramienta**: `kdeps` parseaba `#include` dentro de comentarios de bloque y
reportaba `"include/amdgpu_dal_power_if.h"`, cuyo fichero **no existe en
ninguna parte del árbol** (`display/amdgpu_dm/amdgpu_dm.h:68`, dentro de
`/* … */`). Corregida la herramienta, se repitieron los controles.

**Resultado final** (`exit 0`, 28 semillas = los `.c` con decisiones Polaris12):

| | |
|---|---|
| cabeceras únicas alcanzadas | **391** |
| includes de sistema contados | 386 |
| `no_resueltos` | **0** |
| `asic_reg` alcanzados | **8 de 39**: `bif dce gca gmc oss smu uvd vce` |
| `asic_reg` **NO alcanzados** | **31** (ahora sí demostrado) |
| líneas `asic_reg` alcanzadas | **544 226 de 4 977 966 = 10,9 %** |
| líneas `asic_reg` no alcanzadas | **4 433 740** |

Los 31 no alcanzados: `athub clk dcn df dpcs gc hdp lsdma mmhub mp nbif nbio
pcie pwr rsmu sdma sdma0…sdma7 smuio thm umc vcn vpe wafl xgmi`.

**Corrección de un error previo**: se afirmó que en GFX8 los registros de SDMA
están en `asic_reg/sdma/`. **Falso**: vienen de `asic_reg/gca/gfx_8_0_{d,enum,
sh_mask}.h` — en GFX8 SDMA está dentro del bloque GCA. `asic_reg/sdma/` existe
para ASICs posteriores. La predicción salió del nombre del directorio, no del
código.

**Alcance de la afirmación, y su límite.** "No alcanzable" significa *no
alcanzable desde estas 28 semillas, con el conjunto de `-I` efectivos del build*.
**NO significa innecesario para la RX550**: una cabecera puede ser alcanzable solo
por un camino conditioned por configuración, o ser necesaria de forma
indirecta. No se infiere que puedan eliminarse del futuro driver.

Las 5 116 394 líneas están **medidas**. Cuáles son alcanzables desde el camino
de ejecución: **`UNKNOWN`**, con el método pendiente identificado (resolver
includes transitivamente sobre los 28 ficheros del mapa de decisión).

**No se elimina nada.** `amd/include` es el mayor bloque de generalidad y el
de peor relación esfuerzo/beneficio para demostrar.

---

## 9. §10 — Cadena de probe (derivada, no supuesta)

`amd/amdgpu/amdgpu_drv.c:2377` `amdgpu_pci_probe`, en orden:

| # | etapa | línea / condición |
|---:|---|---|
| 1 | gate de clase display + `drm_firmware_drivers_only()` | antes de todo; `amdgpu_modeset == -1` |
| 2 | lista de PCI IDs no soportados (`amdgpu_unsupported_pciidlist`) | |
| 3 | `supports_atomic` = display virtual **o** `amdgpu_device_asic_has_dc_support()` | |
| 4 | gate `AMD_EXP_HW_SUPPORT` | tu ASIC no lo requiere |
| 5 | `amdgpu_fix_asic_type(pdev, flags)` | |
| 6 | incompatibilidad SME/RAVEN | no aplica |
| 7 | `amdgpu_support_enabled()` | |
| 8 | **`devm_drm_dev_alloc(..., &amdgpu_kms_driver, ...)`** | **punto de acoplamiento con display** |

Salida: `amdgpu_pci_remove` (:2538). PM ops: `prepare` (:2590), `suspend`
(:2620), `suspend_noirq` (:2650), `resume` (:2666), `freeze` (:2687).

**Separación display vs aceleración:** el **único** punto de entrada del
camino de aceleración que toca display es el paso 8 (el tipo de `drm_driver`
registrado). Todo lo demás —energía, VRAM, rings, submit— cuelga de
`adev`, no de KMS. Esto **sugiere** que el camino mínimo sin display existe y
es acotable, pero **no se ha trazado**: `UNLOCKED` el camino desde
`devm_drm_dev_alloc` hasta rings/PM4.

---

## 10. §5 — Categorías A / B / C (preliminar, sin clasificación semántica)

| cat | contenido | estado |
|---|---|---|
| **A · obligatorio por contrato** | UAPI DRM/KMS, `pci_driver`, ABI del kernel, interfaz de firmware (ATOM/SMU), `drm_ioctl` que Mesa/KWin usan | **identificado en principio; el conjunto exacto `UNKNOWN`** |
| **B · necesario para Polaris12** | `pm/powerplay/hwmgr/smu7_*`, `smumgr/polaris10_smumgr.c`, `gfx_v8_0.c`, `gmc_v8_0.c`, `vi.c`, `sdma_v3_0.c` — los 28 ficheros del mapa de decisión | **localizado; justificación por fichero `UNKNOWN`** |
| **C · generalidad no necesaria (candidatos)** | 15 objetos `CIK`+`SI` (ya confirmados en compilación); `amd/display` (1 166 ficheros, acoplamiento de 8 llamadas); `amd/include` no-`asic_reg` de otras familias; firmware de 37 familias no-`polaris12` | **candidatos, ninguno confirmado** |

Ningún elemento de C pasa a `REMOVE_CONFIRMED` en esta fase.

---

## 11. Contradicciones detectadas

| # | contradicción | estado |
|---|---|---|
| 1 | El router (`DOCUMENTATION-ROUTER.md` §3bis) dice que Vulkan/RADV es `NOT_AVAILABLE` porque `mesa-vulkan-drivers` no está instalado. El paquete real es `mesa-vulkan-drivers-freeworld` y **RADV responde con `deviceID 0x699f`** | **ABIERTA**, no tocada aquí |
| 2 | `README.md` y documentos raíz describen `HOST-B`; el host vivo es `HOST-C` | ABIERTA, conocida |
| 3 | Este documento cita «el root port limita a 5 GT/s» como `OBSERVATION`, mientras el informe previo lo tenía como `INFERRED` | **CERRADA** en §1 |
| 4 | Mi afirmación previa sobre los nombres de parámetros PCIe | **CERRADA** en §0 |
| 5 | `amd/display` tiene 592 729 líneas pero solo **8** call sites desde el core | **no es contradicción**: documenta que el coste es de enlace, no de acoplamiento |

---

## 12. Experimentos futuros (ninguno autorizado, ninguno ejecutado)

| id | qué mide | discriminante | estado |
|---|---|---|---|
| `EXP-PCIE-BANDWIDTH-REAL` | ancho de banda PCIe efectivo | Gen2 ×4 actual vs Gen2 ×8 si el cableado lo permite. **Gen3 es imposible: el root port declara 5 GT/s** | `NOT_RUN` — no autorizado |
| `EXP-GTT-PRESSURE` | evictions, migraciones, page faults | `debug_evictions` está en `N`; requiere contadores de debugfs | `NOT_RUN` — requiere privileges |
| `EXP-FW-LOADED` | qué firmware carga para `0x699f` rev `0xc7` | traza de `amdgpu_ucode.c:1520` + nombre construido | `NOT_RUN` — es lectura de código, no ejecución |
| `EXP-ISOLATION` | attribution de mediciones | el gate P0 sigue en `CONTAMINATED_REQUIRES_ISOLATION` | `NOT_RUN` — requiere autorización runtime |

**Ningún resultado de rendimiento existe todavía.** Por tanto **no estamos
autorizados a concluir qué modificación maximiza rendimiento**, y este
documento no lo intenta.

---

## 13. Estado de readiness

**`INVESTIGATION_REQUIRED`** · componente de **`METHODOLOGY_REQUIRED`**
· 1 decisión de requisito **resuelta por el usuario** (`P`).

** Cerrado en esta iteración:**
`PCI_LINK_CAPABILITY` del root port · `MOTHERBOARD_CPU_LIMITATION` ·
`DRIVER_CONFIGURATION` efectiva · configuración efectiva completa · frente real
de `amd/display` (§3) · cadena de probe hasta el registro DRM · universo
medido de `amd/include` · `PRESENT` de firmware · contractualmente qué
SELECT/depende-on obligan al driver.

** Abierto, con su método pendiente:** cierre transitivo de includes (J, K y
§8) · `CALLERS`/`CALLEES` (requiere índice de símbolos) · camino de aceleración
desde el registro hasta rings/PM4 · `boot_vga` en el kernel · `LOADED`/`USED`
de firmware · causa del ×4 negociado · observabilidad de GTT.

**Decisión de requisito que ya diste:** la RX550 no necesita pilotar monitor.
Convertido en el §3: el acoplamiento medido son 3 puntos, no 1 166 archivos.
**Sigue sin estar autorizado a eliminar nada.**
