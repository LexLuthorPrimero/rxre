# Validación final del host RX 550 — 2026-09-25

**Modo:** `READ_ONLY/EVIDENCE`
**Fuente primaria:** `FINAL-VALIDATION-20260925T135831Z.json`
**Hash JSON:** `0fea12f9da09a30456e1ab06c6b8fa40a27af94fcc64e2ae8b8fe9ac22e7e1cb`
**Herramienta:** `tools/validate_rx550_final.py` (Python 3, sólo lectura)
**Host observado:** Nobara Linux 43, kernel `6.18.2-200.nobara.fc43.x86_64`
**Sesión observada:** Wayland/KDE

Este documento registra una fotografía de la instalación actual. No es una
re-ejecución de los experimentos históricos y no convierte una salida de
diagnóstico en una causalidad.

## 1. Identidad de la GPU

| Dato | Valor observado |
|---|---|
| PCI objetivo | `1002:699f` |
| BDF | `0000:01:00.0` |
| Driver | `amdgpu` |
| DRM actual | `card2` |
| Render node | `/dev/dri/renderD129` |
| hwmon actual | `hwmon1` |
| GPU Intel | `8086:0412`, BDF `0000:00:02.0`, `i915`, `card1` |

`card1`/`card2` son valores de esta instalación, no identificadores portables.
La regla portable es resolver por BDF y `vendor:device`; no se debe volver a
usar `DRI_PRIME=1` como si significara “AMD”.

## 2. Mesa, Vulkan y sesión gráfica

- Mesa de distribución: `25.3.2-2.fc43.x86_64`.
- LLVM: `21.1.7`; libdrm: `2.4.128`; firmware: `20251125`.
- `glxinfo -B` y `DRI_PRIME=1002:699f glxinfo -B` muestran RX 550/Polaris12.
- RADV aislado con
  `VK_ICD_FILENAMES=/usr/share/vulkan/icd.d/radeon_icd.x86_64.json`
  muestra `AMD Radeon RX 550 / 550 Series (RADV POLARIS12)`, `deviceID=0x699f`.
- La sesión Wayland negotiated `wl_drm` con la RX 550 como dispositivo
  principal. La salida física conectada está en el Intel `card1`; por tanto,
  la RX 550 participa en el render/compositor aunque no sea la salida física.
- `qdbus org.kde.KWin /KWin supportInformation` devolvió KWin 6.5.4, backend
  DRM y renderer AMD/RX 550.
- `DISPLAY=:0 glxinfo -B` devuelve AMD; `DRI_PRIME=1` devuelve Intel. Es una
  diferencia real de selección y no un resolvedor.
- El journal contiene 14 mensajes de permiso denegado asociados a KWin al
  abrir/testear `card1`. El impacto sobre la salida no queda determinado por
  esta lectura y no se corrigió.

### Extensión Vulkan solicitada

Con el ICD RADV aislado, `VK_EXT_image_drm_format_modifier` no aparece en la
lista de extensiones del dispositivo GFX8. Esto se registra como
`NOT_AVAILABLE`; no se crea un parche para simular una extensión que el
dispositivo no expone.

## 3. PM, DPM, firmware y logs

La lectura instantánea, sin escrituras, encontró:

- `power/control=auto`, `runtime_status=active`, DPM `auto`.
- `power1_cap=35 W`, default y máximo `35 W`.
- `W_SMU` leído de `power1_input`: aproximadamente `5.1 W` en la muestra de
  esta validación; no es vatímetro independiente.
- `pp_dpm_sclk` tenía `1046 MHz` activo; `pp_dpm_mclk` tenía `300 MHz` activo;
  el perfil era `3D_FULL_SCREEN`.
- La validación no ejecutó workloads, benchmarks ni escrituras de DPM/PM; sólo leyó los estados mostrados.
- El paquete de firmware y el ROM bar estaban presentes; no se modificó VBIOS,
  firmware, power cap, DPM, clocks ni PM.

Señales del journal del boot:

- `gpu_reset=0`, `ring_timeout=0`, `RA24=0`, `VM fault` no-PRT `=0`.
- Una línea `Disabling VM faults because of PRT request!` fue clasificada como
  aviso benigno, no como fallo.
- Dos líneas genéricas de `amdgpu` fueron: fallo de vendor infoframe en el
  conector AMD desconectado y el aviso PRT anterior. No se extrapoló una causa
  de rendimiento a partir de ellas.

## 4. Servicios y almacenamiento

- `kalm-gpu.service`, `kalm.service` y `system-autopilot.timer`: `inactive` y
  `not-found` en la instalación actual.
- `irqbalance.service`: `active`/`enabled`; no se cambió.
- No se encontraron configuración persistente específica de RX 550 en
  `/etc/modprobe.d`, `/etc/dracut.conf.d`, `/etc/udev/rules.d` o
  `/etc/default/grub`.
- `/` está en `/dev/sdb3` con `ext4`; el Btrfs histórico de `sda2` no está
  montado como raíz en esta instalación.
- No se ejecutó SMART, scrub, reparación Btrfs ni escritura de almacenamiento.
  Por tanto, la salud del disco y cualquier causalidad histórica siguen
  `UNKNOWN`.

## 5. Pruebas estáticas ejecutadas

| Prueba | Resultado |
|---|---|
| `python3 -m unittest discover -s 04-IMPLEMENTACION/tests -p 'test_*.py'` | `54` tests, `OK`, `1` skip |
| `PYTHONDONTWRITEBYTECODE=1 python3 04-IMPLEMENTACION/rx550-torneo/tests/run_tests.py` | `64/64` checks |
| `PYTHONDONTWRITEBYTECODE=1 python3 04-IMPLEMENTACION/rx550-torneo/tests/run_tests_m1.py` | `110/110` checks; `strace` `NOT_AVAILABLE`, no se cuenta como PASS |
| `python3 -m py_compile` de los módulos modificados | OK |
| `git diff --check` de los cambios de esta consolidación | OK |
| `tools/validate_rx550_final.py` | `OBSERVED`, sin escrituras al sistema |

Los tests de M1 usan un nodo temporal y estados sintéticos; no escribieron
`/sys`. La validación depm/DPM anterior sigue siendo un contrato de lectura,
no autorización para el runner de escritura.

## 6. Límites y veredicto de esta fase

- No se declararon reparados el reset/hang, la estabilidad bajo carga, la
  separación Intel/RX 550, DPM/SCLK/MCLK, BACO, VFIO ni la recuperación C1.
- La corrección de upload de R-11 está conservada en el workload histórico;
  no se volvió a ejecutar en esta instalación.
- La instalación actual no tiene Mesa CUSTOM en `/opt`, ni Kalm GPU, ni una
  configuración de arranque RX 550. Esto no prueba que los problemas
  históricos sean inexistentes.
- El árbol Git tenía cambios no confirmados y no tenía remoto en el momento
  de esta captura.

**Estado de la validación:** `PARTIALLY_RESOLVED` para la identificación y
los procedimientos de selección; `UNRESOLVED` para la estabilidad causal, la
separación del compositor y la validación runtime de correcciones históricas.
