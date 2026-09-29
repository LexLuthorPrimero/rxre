# rx550-torneo — Fase 1 (READ-ONLY)

Implementación del núcleo de la Fase 1 de acuerdo a `../../02-ARQUITECTURA/RX550_BUILD_SPECIFICATION.txt`
(§17-20, §29, §34-35). **No escribe nada en sysfs.** No ejecuta benchmarks,
no instala paquetes ni usa privilegios.

> **Fase 1.1 (read-only):** corregido el probe GL (`_mesa_status`), documentada
> la selección display/GL/Vulkan y confirmada la procedencia de `power/control`.
> Ver secciones al final. Sin cambios funcionales más allá de la lectura.

## Alcance implementado

- Detección determinística de la RX 550 por PCI `1002:699f` (nunca asume
  `cardN`/`hwmonX`), verificación de driver `amdgpu`, resolución de `hwmon`,
  render node (`/dev/dri/by-path/...-render`) y BDF real.
- Separación estricta de la Intel HD 4600 `8086:0412` (GPU de display, i915).
  Aborta si la RX 550 aparece como display o si la Intel no tiene conector
  `connected`.
- State Manager: captura, persistencia atómica, hash SHA-256, validación de
  esquema y carga para rollback (sin aplicar).
- CLI: `status`, `state-save`, `state-show`, `state-load`, `verify`.
- Estructura de rollback (`failsafe.py`) con los 6 campos restaurables y el
  requisito de escritura elevada documentado (no ejecutado).

## Estructura

```
rx550-torneo
├── rx550-torneo              # entrypoint (bash → python3 -m rx550_torneo.cli)
├── src/rx550_torneo/
│   ├── util.py               # lecturas read-only, BDF, guards
│   ├── gpu_finder.py         # detección/validación de topología
│   ├── state_manager.py      # captura, estado persistente, rollback (load)
│   ├── failsafe.py           # preflight y plan de rollback (NO aplica)
│   └── cli.py                # subcomandos
└── tests/run_tests.py        # tests obligatorios A–J
```

## Estado persistente

- Directorio: `$XDG_STATE_HOME/rx550-torneo/` (default `~/.local/state/rx550-torneo/`).
  Override de prueba: `RX550_TORNEO_STATE_DIR`.
- `state.json` (canónico, ordenado) + `state.json.sha256`.
- Escritura atómica (`tmp` + `fsync` + `rename`) y lock exclusivo `flock`.
- `state-save` **se niega** a sobrescribir un estado válido existente salvo `--force`.

## Uso

```bash
./rx550-torneo status                # detección + lecturas vivas
./rx550-torneo --json status         # (--json también vale tras el subcomando)
./rx550-torneo state-save            # falla si ya existe estado
./rx550-torneo state-save --force
./rx550-torneo state-show            # verificación de hash + resumen
./rx550-torneo state-load            # valida que sea restaurable (sin aplicar)
./rx550-torneo verify                # validaciones integrales (rc=1 si falla)
```

Overrides solo para pruebas (no afectan operación normal):
`RX550_TORNEO_TARGET_PCI`, `RX550_TORNEO_INTEL_PCI`, `RX550_TORNEO_DRM_DIR`,
`RX550_TORNEO_RENDER_OVERRIDE`, `RX550_TORNEO_HWMON_OVERRIDE`.

## Garantías read-only

- El código no abre ningún path bajo `/sys` en modo escritura
  (`util.guard_no_sys_write` bloquea por diseño).
- `tests/run_tests.py` test J:
  - auditoría interna (`RX550_TORNEO_AUDIT_WRITES=1`): `status`/`state-show`/`verify`
    no registran escrituras; `state-save` solo escribe `state.json` (nunca `/sys`);
  - `strace -e openat,open`: sin aperturas de escritura a `/sys`;
  - `power1_cap` y `power/control` intactos antes/después.

## Campos capturados (state.json)

- Identidad/topología: `target_pci`, `intel_pci`, `drm_card`, `bdf`, `vendor`,
  `device_id`, `driver`, `hwmon`, `render_node`, `intel_card`, `intel_bdf`.
- `restorable.files` (6): `power_control`, `power1_cap`,
  `power_dpm_force_performance_level`, `pp_dpm_sclk`, `pp_dpm_mclk`,
  `pp_power_profile_mode`; más `restorable.active` (nivel marcado con `*`).
- `capture.live`: `power1_cap`/`_default`/`_max`, `power1_input`, `temp1_input`,
  `freq1_input`, `gpu_busy_percent`, `mem_busy_percent`, `mem_info_vram_used`,
  `mem_info_gtt_used`, `runtime_status`.
- `kalm`: procesos `kalmd.py` / `kalm-lite.py` / `kalm-gpu` y estado de
  `kalm-gpu.service`.
- `mesa`: `glxinfo` (display/Intel), `glxinfo_prime` (DRI_PRIME, renderer de la
  RX 550 y `selected_render_node`), dispositivos Vulkan, presencia de
  `/opt/mesa-26.2.2-rx550-haswell`.
- `kernel`, `timestamp`, `schema_version`.

## Tests

```
python3 tests/run_tests.py
```

Resultado: **65/65 checks OK** (A–K), incluida detección, separación de Intel,
paths, captura, round-trip, protección anti-sobrescritura, errores seguros con
GPU ausente/PCI incorrecto/ruta inesperada y cero escrituras.

Test **K** (regresión de Fase 1.1, read-only): verifica que `DRI_PRIME` selecciona
el renderer GL de la RX 550 sin asumir `card1`/`renderD129` (descubre la
topología). Comprueba: (1) renderer `AMD`/`radeonsi`; (2) modelo RX 550;
(3) `selected_render_node` == render node dinámico de la RX 550; (4) ese render
node resuelve vía `/sys/class/drm/<node>` + `/sys/bus/pci/devices/<bdf>` a PCI
`1002:699f`; (5) la selección difiere del renderer por defecto. Si la RX 550 no
está disponible o GL no puede seleccionarla, falla de forma segura y explica la
causa (p. ej. `GPUError[NO_CARDS]`), sin tocar display, DRM/KMS, sysfs ni power.

## Requisitos futuros (NO implementados en Fase 1)

Restaurar `power/control`, `power1_cap`, `power_dpm_force_performance_level`,
`pp_dpm_sclk`, `pp_dpm_mclk`, `pp_power_profile_mode` requiere **permiso de
escritura** (algunos con privilegios elevados). `failsafe.RollbackPlan.apply()`
lanza `NotSupported` a propósito. Pendiente de autorización explícita.

## Selección de GPU: display vs GL vs Vulkan (Fase 1.1)

Configuración: sesión **Wayland (KDE/kwin_wayland)**, `DISPLAY=:0` vía Xwayland.
Tres planos distintos:

| Plano | Quién decide | GPU | Evidencia |
|---|---|---|---|
| Display / compositor | kwin_wayland + Xwayland | **Intel HD 4600** `8086:0412` (card0) | `glxinfo -B` sin env = Intel; conectores Intel `connected` |
| Renderer OpenGL (por app) | Mesa `DRI_PRIME` (GLX/DRI3) | **Intel por defecto**, **RX 550** con `DRI_PRIME` | `DRI_PRIME=1002:699f glxinfo -B` = `AMD Radeon RX 550 ... radeonsi` |
| Vulkan (por app) | loader + `DRI_PRIME` / `MESA_VK_DEVICE_SELECT` / `VK_ICD_FILENAMES` | Intel, RX 550 y llvmpipe enumerados | `vulkaninfo --summary` |

### Por qué `DRI_PRIME=1 glxinfo -B` mostró Intel en la captura inicial

No era una limitación de Mesa: era un **bug del probe de Fase 1**. En
`state_manager._mesa_status` el comando era:

```bash
DRI_PRIME=1 command -v glxinfo >/dev/null 2>&1 && glxinfo -B
```

La asignación `DRI_PRIME=1` aplica **solo a `command -v`**; `glxinfo -B` corría
sin `DRI_PRIME`. Repro:

```bash
bash -c 'DRI_PRIME=1 command -v glxinfo >/dev/null 2>&1 && glxinfo -B'  # -> Intel  (bug)
bash -c 'command -v glxinfo >/dev/null 2>&1 && DRI_PRIME=1 glxinfo -B'  # -> RX 550 (correcto)
```

### Método reproducible para verificar la RX 550 como renderer GL

No cambia la GPU de display (Intel sigue conduciendo el compositor); solo el
contexto GL del proceso:

```bash
# 1) Renderer de la RX 550 (sintaxis recomendada, vendor:device)
DRI_PRIME=1002:699f glxinfo -B | grep 'OpenGL renderer string'
# -> AMD Radeon RX 550 / 550 Series (radeonsi, polaris12, ACO, DRM 3.64, ...)

# 2) Equivalente por índice o por bus PCI (formato Mesa: guiones bajos)
DRI_PRIME=1 glxinfo -B | grep 'OpenGL renderer string'
DRI_PRIME=pci-0000_01_00_0 glxinfo -B | grep 'OpenGL renderer string'

# 3) Verificar el render node elegido (stderr)
DRI_PRIME=1002:699f DRI_PRIME_DEBUG=1 glxinfo -B 2>&1 | grep DRI_PRIME
# -> DRI_PRIME: 2 devices
# -> DRI_PRIME: device 0  - vid:did match -> selected (/dev/dri/renderD129)
```

Sintaxis documentada por Mesa (`DRI_PRIME=vendor_id:device_id`, `DRI_PRIME=N` o
`DRI_PRIME=pci-0000_XX_YY_Z` con **guiones bajos**). Ojo: `DRI_PRIME=pci-0000:01:00.0`
(con dos puntos) **no** funciona — verificado: devuelve Intel. La ausencia de
PRIME providers en `xrandr --listproviders` (0 bajo Xwayland) **no** impide
`DRI_PRIME`, que usa DRI3 del loader de Mesa, no RandR.

### Condición / límites

- Requiere `glxinfo` (presente) y sesión X11/Xwayland con DRI3 (presente).
- `DRI_PRIME` selecciona el **renderer**, no la GPU de display: la imagen se
  presenta a través de Xwayland/Intel. No altera kwin ni KMS.
- Vulkan: para forzar inequívocamente la RX 550 usar
  `VK_ICD_FILENAMES=/usr/share/vulkan/icd.d/radeon_icd.x86_64.json vulkaninfo --summary`.
  `MESA_VK_DEVICE_SELECT=1002:699f` **no es una garantía**: la observación del
  09-19 lo dejó en primera posición, pero otros entornos seleccionaron Intel. La
  verificación del device `0x699f` en `vulkaninfo` es obligatoria.

## Procedencia de `power/control` (Fase 1.1)

**CONFIRMADO: `power/control=on` NO lo puso la Fase 1.** Fue establecido
**manualmente** por el usuario (`sudo tee`), antes de la Fase 1; el programa
nunca escribió ese valor (test J + `strace`). Ya estaba presente mucho antes.

Evidencia (journal del boot actual, `boot_id c9334edf...`, boot 2026-09-18 08:09):

```
sep 19 10:25:52 sudo[448950]: lucas : ... COMMAND=/usr/sbin/tee /sys/class/drm/card1/device/power/control
sep 19 10:25:52 kernel: amdgpu 0000:01:00.0: [drm] PCIE GART of 256M enabled ...
sep 19 10:25:53 kernel: amdgpu 0000:01:00.0: [drm] UVD and UVD ENC initialized successfully.
sep 19 10:25:53 sudo[449518]: lucas : ... tee /sys/class/drm/card1/device/hwmon/hwmon2/power1_cap
sep 19 10:25:53 sudo[449525]: lucas : ... tee /sys/class/drm/card1/device/power_dpm_force_performance_level
```

- ÚLTIMA escritura a `power/control` en todo el boot: **09-19 10:25:52**, por
  `sudo tee` invocado por `lucas` (escritura manual). Antes hubo muchas
  (09-18 15:19–16:15) durante pruebas de runtime PM.
- `stat` de sysfs confirma que `mtime` = última escritura: `power/control`
  mtime `10:25:52` y `power1_cap` mtime `21:19:46` (= restore de EP-06).
- Todos los `state_initial.txt`/`state_final.txt` de las Fases A/B y EP-06
  (09-19 11:42, 12:20, 20:56) ya registran `device/power/control: on`.
- La Fase 1 corrió ~22:00 (11.5 h después) y nunca escribe sysfs (test J +
  `strace`). El `sudo tee` activó el resume de la GPU (GART/UVD/VCE), no la
  suspendió.

Incógnitas de esta procedencia: el journal no imprime el payload de `tee`; el
valor `on` se infiere de (a) valor actual, (b) `mtime` sin cambios posteriores,
(c) trayectoria de resume. Actor/hora = **confirmados**; valor = **confirmado
por estado+mtime**, payload no logueado.

Nota: `power/control` de dos objetos distintos:
- `/sys/class/drm/card1/device/power/control` (dispositivo PCI) = **`on`** ← el que captura el programa.
- `/sys/class/drm/card1/power/control` (DRM card) = `auto`, `runtime_status=unsupported`.

## Cambio de código en Fase 1.1

Único cambio, estrictamente para corregir una lectura read-only:
`state_manager._mesa_status` en `src/rx550_torneo/state_manager.py`. Ahora
ejecuta `glxinfo` con un `env` de proceso (aplicado al binario, no a
`command -v`), usa `DRI_PRIME=1002:699f` con fallback a `DRI_PRIME=1`, y captura
`selected_render_node` vía `LIBGL_DEBUG=verbose`. Sin escrituras; tests 60/60.

## Incertidumbres restantes

- La lectura de algunos nodos puede depender de permisos según el archivo; se
  registra como `None`/NA, nunca se escala a root.
- `pp_power_profile_mode` no lleva marca `*` de estado activo en el formato
  actual; `active` queda `None` para ese campo.
- `mtime` de sysfs como "última escritura": consistente en los casos
  observados (`power/control`, `power1_cap`, dpm), no documentado por el kernel
  como garantía formal.
