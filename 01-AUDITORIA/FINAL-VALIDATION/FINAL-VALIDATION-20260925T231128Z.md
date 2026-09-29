# FINAL-VALIDATION — 20260925T231128Z

> Evidencia generada por `tools/validate_rx550_final.py` (read-only, sin privilegios).
> No sobrescribe capturas anteriores. Vista legible del `.json` contiguo.

## Identidad del host — `HOST_SCOPE=HOST-C`, `HOST_SCOPE_BASIS=DECLARED`

El kernel en ejecucion, `os_release` y las versiones de paquetes coinciden con lo
registrado como HOST-C en `01-AUDITORIA/PATCH-RECOVERY/PATCH-SOURCES.md` §3.
La identidad se demuestra directamente; no se infiere.

| Campo | Valor |
|---|---|
| `generated_at` | `2026-09-25T23:11:28+00:00` |
| Modo | `READ_ONLY/EVIDENCE` |
| `writes_to_system` | `False` |
| `benchmarks_executed` | `False` |
| SO | Nobara Linux 44 (KDE Plasma Desktop Edition), `VERSION_ID=44` |
| Kernel en ejecucion | `7.1.3-200.nobara.fc44.x86_64` |
| Sesion | `wayland` / `KDE` |
| `validation_status` | `OBSERVED` |

## GPU — RX550 por identidad dinamica

| Campo | Valor |
|---|---|
| `pci_id` | `1002:699f` |
| `bdf` | `0000:01:00.0` |
| `driver` | `amdgpu` |
| `drm_card` | `card1` |
| `render_node` | `/dev/dri/renderD129` |
| `hwmon` | `hwmon1` |
| `sysfs_device` | `/sys/bus/pci/devices/0000:01:00.0` |
| `status` | `OBSERVED` |

**`cardN` no es identidad.** La captura resuelve por `pci_id` + `bdf`.

## Renderers

- **GL por defecto:** `Mesa Intel(R) HD Graphics 4600 (HSW GT2)` (vendor `Intel`) — `OBSERVED`
- **GL con `DRI_PRIME=1002:699f`:** `AMD Radeon RX 550 / 550 Series (radeonsi, polaris12, ACO, DRM 3.64, 7.1.3-200.nobara.fc44.x86_64)` (vendor `AMD`) — `OBSERVED`
- **Vulkan RADV, ICD AMD aislada:** `device_ids=['0x699f']`, `device_names=['AMD Radeon RX 550 / 550 Series (RADV POLARIS12)']`, icd `radeon_icd.x86_64.json` — `OBSERVED`

## PM / DPM — lectura, sin escritura

| Campo | Valor |
|---|---|
| `power_control` | `auto` |
| `runtime_status` | `active` |
| `dpm_level` | `auto` |
| `power1_cap_uw` | `35000000` |
| `power1_cap_default_uw` | `35000000` |
| `power1_cap_max_uw` | `35000000` |
| `power1_input_uw` | `5138000` |
| `temp1_input_mc` | `27000` |

`power1_input_uw` es **`W_SMU`** (estimador del sensor), no un vatimetro.

## Servicios — `is-active` / `is-enabled`

| Unidad | active | enabled |
|---|---|---|
| `irqbalance.service` | `active` | `enabled` |
| `kalm-gpu.service` | `inactive` | `not-found` |
| `kalm.service` | `inactive` | `not-found` |
| `sys-tuned.service` | `inactive` | `not-found` |
| `system-autopilot.timer` | `inactive` | `not-found` |

## Journal del boot actual

| Senal | Cuenta |
|---|---|
| `amdgpu_error_like` | 1 |
| `gpu_reset` | 0 |
| `prt_notice` | 1 |
| `ra24` | 0 |
| `ring_timeout` | 0 |
| `vm_fault_non_prt` | 0 |

- `kwin_permission_denied_count`: **0**
- `journal_query_errors`: `['', '']`

Nota sobre las senales: `amdgpu_error_like=1` y `prt_notice=1` son **la misma linea**
`amdgpu 0000:01:00.0: Disabling VM faults because of PRT request!` de la secuencia de
arranque (journalctl -b -k, linea 1095). No es un ring timeout, ni un reset, ni un VM fault.
`gpu_reset=0`, `ring_timeout=0`, `ra24=0`, `vm_fault_non_prt=0`.

## Almacenamiento

- root: `/dev/sdb3 ext4 rw,relatime`
- home: `(no separado)`
- `smart_checked`: `False`

## Git

- branch `main`, commit `c6146788e0d4fb12d9b0ec1209fa2840692de0c5`
- remote: `(ninguno)`
- worktree entries: 378

## Limitaciones declaradas por la propia herramienta

- No benchmark, A/B, power-cap write, service change, GPU reset, SMART, or Btrfs write was executed.
- A missing tool or inaccessible field remains NOT_AVAILABLE; it is not treated as success.
- The presence of a renderer does not prove the cause of a historical performance regime.

## CONFLICT observado en esta captura

**`CONFLICT-4` — kernel en ejecucion vs paquete `kernel-core`:**

| Fuente | Valor |
|---|---|
| `uname -r` (lectura directa) | `7.1.3-200.nobara.fc44.x86_64` |
| `rpm -q kernel-core` (campo de la captura) | `6.18.2-200.nobara.fc43.x86_64` |

Resolucion verificada por lectura de solo lectura: **ambos kernels estan instalados**
(`6.18.2-200.nobara.fc43` y `7.1.3-200.nobara.fc44`). `rpm -q` devuelve el
primer coincidente en orden alfabetico, no el que esta en ejecucion. El campo
`packages['kernel-core']` de la captura es por tanto enganoso: no describe el host en ejecucion.
La identidad del host se establece por `uname -r` + `os_release`, no por ese campo.
El script no se modifico: el defecto se registra, no se parchea.

## Lo que esta captura NO demuestra

- **No demuestra `OWNERSHIP=FULL`.** El esquema no incluye clientes DRM, FDs,
  escritores, ni namespaces de root. `OWNERSHIP` sigue `NOT_AVAILABLE` para HOST-C.
  La ausencia de servicios Kalm **no** implica ownership completo.
- **No cierra `G1`.** Cubre identidad, PM/DPM leido, journal del boot, servicios
  y renderers. No cubre clientes, causalidad, ni re-ejecucion de las suites 64/64, 110/110, 54+1.
- `mesa-vulkan-drivers` figura `None` en el bloque de paquetes, pero
  `vulkan_radv_icd` reporta `OBSERVED` con `0x699f`. El ICD RADV resuelve;
  el paquete queried no esta instalado. Se conserva el hecho; no se reconcilia aqui.
- La presencia de un renderer **no prueba** la causa de un regimen historico.
