# AMDGPU-POLARIS12-DECISION-POINTS.md — Los 76 puntos de decisión del driver para la RX 550

**PROPÓSITO:** inventario completo de los puntos donde `amdgpu` ramifica
específicamente para `CHIP_POLARIS12` / `0x699F`. Es el mapa que hay que tener
antes de modificar el driver: cada fila es una decisión que el driver toma por
tu tarjeta y no por la familia.

**NO es** un mapa de capacidades del siliconio. Para eso está
`POLARIS12-MAP.md`, que es complementario y no solapado (verificado: 0
coincidencias de `CHIP_POLARIS12` / `smu7` / `polaris10_smumgr` en
`POLARIS12-MAP.md`).

## Provenance

| Campo | Valor |
|---|---|
| `SOURCE` | `RESEARCH/baseline/linux-7.1.3/drivers/gpu/drm/amd/` |
| `VERSION` | kernel 7.1.3 · manifest `RESEARCH/baseline/MANIFEST.sha256` · `EXIT=0` · 2 787/2 787 |
| `CONTRASTE` | `/home/lucas/rx550-upstream-7.2.8/linux-7.2.8/drivers/gpu/drm/amd/` |
| `CONTRASTE_VERSION` | upstream 7.2.8 · `sha256 12e8d5a9…e51941` (coincide con el publicado por upstream) |
| `FECHA` | 2026-09-28 |
| `HOST` | `HOST-C` · Nobara 44 · kernel `7.1.3-200.nobara.fc44.x86_64` |
| `SCOPE` | solo `drivers/gpu/drm/amd/`. **No** cubre `drivers/base/power/`, `include/`, `Documentation/` |
| `WORK_CLASS` | `READ_ONLY/EVIDENCE` + `DOCUMENTATION`. 0 escrituras al driver |

**Query reproducible:**

```bash
cd RESEARCH/baseline/linux-7.1.3/drivers/gpu/drm/amd
LC_ALL=C grep -rn 'CHIP_POLARIS12\|0x699[Ff]' .
```

`LC_ALL=C` es obligatorio: con locale español `diff` y `grep` cambian sus
cadenas de salida y los conteos salen a cero. Ya ha causado dos errores en esta
investigación.

## 1. Cifras

Unidad: **ocurrencia de la cadena** en el árbol `amd/`. Un mismo fichero puede
tener varias.

| Área | Ficheros | Puntos |
|---|---:|---:|
| Gestión de energía — `pm/powerplay/` | 7 | **18** |
| Núcleo — `amdgpu/` | 14 | **49** |
| Compute — `amdkfd/` | 6 | **6** |
| Display — `display/amdgpu_dm/` | 1 | **3** |
| **TOTAL** | **28** | **76** |

Corrección de un conteo previo mío: en una respuesta anterior cité «17» para
`pm/` y «42» para `amdgpu/`. Los valores verificados son **18** y **49**. El
total de 76 sí era correcto.

## 2. Gestión de energía — 18 puntos, 7 ficheros

Tu tarjeta **usa la pila PowerPlay `smu7`**, no swsmu. Evidencia:
`pm/swsmu/smu7/` **no existe** en 7.1.3 ni en 7.2.8.

| # | `file:line` | Función | Qué decide |
|---:|---|---|---|
| 1 | `pm/powerplay/hwmgr/hwmgr.c:156` | `hwmgr_early_init` | **Selecciona el gestor de SMU**: `hwmgr->smumgr_funcs = &polaris10_smu_funcs`. Es el primer fork que decide tu tarjeta |
| 2 | `pm/powerplay/hwmgr/hwmgr.c:501` | `polaris_set_asic_special_caps` | Activa `PHM_PlatformCaps_SPLLShutdownSupport` |
| 3 | `pm/powerplay/hwmgr/smu7_hwmgr.c:1230` | `smu7_enable_sclk_mclk_dpm` | Tu tarjeta entra en el grupo que habilita DPM de SCLK y MCLK |
| 4 | `pm/powerplay/hwmgr/smu7_hwmgr.c:1924` | `smu7_init_dpm_defaults` | Rama de control de fase VDDC (`vddc_phase_shed_control`) vía SVI2 |
| 5 | `pm/powerplay/hwmgr/smu7_hwmgr.c:1964` | `smu7_init_dpm_defaults` | `disable_edc_leakage_controller = false` — **EDC leakage controller activo** por defecto en Polaris12 |
| 6 | **`pm/powerplay/hwmgr/smu7_hwmgr.c:1975`** | `smu7_init_dpm_defaults` | **Guard por device+revision. Ver §3** |
| 7 | `pm/powerplay/hwmgr/smu7_hwmgr.c:2061` | `smu7_get_evv_voltages` | Calcula el rango de voltaje con `smu7_calculate_ro_range()` |
| 8 | `pm/powerplay/hwmgr/smu7_hwmgr.c:3384` | `smu7_vblank_too_short` | `switch_limit_us = is_memory_gddr5 ? 450 : 150` µs. **Si el vblank es más corto, no se permite cambiar de reloj** |
| 9 | `pm/powerplay/hwmgr/smu7_hwmgr.c:3385` | `smu7_vblank_too_short` | Para Polaris12 se toma siempre el límite alto (450/150), sin la vía `is_kicker` de Polaris10/11 |
| 10 | `pm/powerplay/hwmgr/smu7_hwmgr.c:4871` | `smu7_check_mc_firmware` | Envía `PPSMC_MSG_EnableFFC` al SMC |
| 11 | `pm/powerplay/hwmgr/smu7_hwmgr.c:4878` | `smu7_check_mc_firmware` | Envía `PPSMC_MSG_DisableFFC` al SMC |
| 12 | `pm/powerplay/hwmgr/ppatomctrl.c:1199` | `atomctrl_get_voltage_range` | `*max_vddc` desde `ATOM_ASIC_PROFILING_INFO_V3_6.ulMaxVddc / 100` — **el límite de voltaje viene del firmware ATOM, no del driver** |
| 13 | `pm/powerplay/hwmgr/smu7_powertune.c:998` | `smu7_enable_didt_config` | Programa la configuración DIDT con `GCCACConfig_Polaris11` (**reutiliza la de Polaris11**) |
| 14 | `pm/powerplay/hwmgr/smu7_thermal.c:179` | `smu7_fan_ctrl_start_smc_fan_control` | Entre en el grupo que delega el control de ventilador al SMC, si `ucEnableZeroRPM` |
| 15 | `pm/powerplay/hwmgr/smu7_baco.c:79` | `smu7_baco_set_state` | Tu tarjeta admite BACO (modo de reset por fuel) |
| 16 | `pm/powerplay/smumgr/polaris10_smumgr.c:793` | `polaris10_populate_ulv_level` | Rellena el nivel ULV (undervolt) |
| 17 | `pm/powerplay/smumgr/polaris10_smumgr.c:1801` | `polaris10_populate_avfs_parameters` | Aplica parámetros AVFS, con la condición `!ASICID_IS_P23(revision)` |
| 18 | `pm/powerplay/smumgr/polaris10_smumgr.c:1819` | `polaris10_populate_avfs_parameters` | Para Polaris12 y no-P23 fija `ulGB_VDROOP_TABLE_CKSOFF_a0 = 0xF6B024DD` a mano |

## 3. El hallazgo: existe un guard por device+revision y tu tarjeta NO lo cumple

`pm/powerplay/hwmgr/smu7_hwmgr.c:1975-1984`, dentro de
`smu7_init_dpm_defaults()`:

```c
if ((adev->pdev->device == 0x699F) &&
    (adev->pdev->revision == 0xCF)) {
        phm_cap_unset(..., PHM_PlatformCaps_PowerContainment);
        data->enable_tdc_limit_feature = false;
        data->enable_pkg_pwr_tracking_feature = false;
        data->disable_edc_leakage_controller = true;
        phm_cap_unset(..., PHM_PlatformCaps_ClockStretcher);
}
```

Es el **único punto de los 76 que discrimina tu ID exacto de tarjeta** en vez
de la familia. Es el segundo, por orden de aparición, dentro de la misma
función que en la línea 1964 había puesto
`disable_edc_leakage_controller = false` para Polaris12: el guard lo vuelve a
poner a `true`.

**Tu tarjeta tiene revisión `0xC7`, no `0xCF`.** Verificado con dos instrumentos
independientes:

| Instrumento | `device` | `revision` |
|---|---|---|
| `lspci -nn -v -s 01:00.0` | `1002:699f` | **`rev c7`** |
| `/sys/bus/pci/devices/0000:01:00.0/{device,revision}` | `0x699f` | **`0xc7`** |

Difieren en el último nibble: `7` frente a `F`.

**Consecuencia:** upstream decidió que en un `0x699F` rev `0xCF` esas cuatro
características de potencia deben estar **desactivadas**. Tu rev `0xC7` **no
recibe ese tratamiento** y corre con los valores por defecto de Polaris12:
PowerContainment activo, TDC limit activo, package power tracking activo,
EDC leakage controller **activo**, ClockStretcher activo.

**Clasificación honesta:** esto es un hecho de código
(`FACT_FOR_upstream_7.1.3`), verificado en fuente y en el host. **No** es un
diagnóstico. No afirma que ninguna de esas cuatro características cause el
problema que te trae aquí; afirma que tu tarjeta está fuera de un guard que
upstream escribió para un hermano de revisión de la misma familia. Eso es un
`QUESTION`, no una `CONCLUSION`.

**Lo que lo cerraría:** el commit upstream que añadió ese guard, para saber qué
fallo lo motivó. `NOT_DONE` — es el siguiente paso natural y no requiere tocar
nada.

## 4. Núcleo `amdgpu/` — 49 puntos, 14 ficheros

### 4.1 Identificación y arranque

| `file:line` | Función / contexto | Qué decide |
|---|---|---|
| `amdgpu/amdgpu_drv.c:2034-2041` | tabla `amdgpu_pci_table` | **8 IDs → `CHIP_POLARIS12`**: `0x6980` `0x6981` `0x6985` `0x6986` `0x6987` `0x6995` `0x6997` **`0x699F`** ← la tuya |
| `amdgpu/amdgpu_device.c:1980` | `amdgpu_device_ip_early_init` | Orden de early-init de los IP blocks |
| `amdgpu/amdgpu_ucode.c:582` | `amdgpu_ucode_get_load_type` | Tipo de microcode a cargar |
| `amdgpu/amdgpu_cgs.c:325` | `amdgpu_cgs_get_firmware_info` | Qué firmware CGS ("soft" vs "hard") |
| `amdgpu/amdgpu_i2c.c:227` | `amdgpu_i2c_init` | Inicialización de I²C (SMBus) |

### 4.2 Pipeline gráfico — `gfx_v8_0.c`, 15 puntos

| `file:line` | Función | Qué decide |
|---|---|---|
| `784` | `gfx_v8_0_init_golden_registers` | Registros golden de la ISA GFX8 |
| `973`, `983`, `1003`, `1024`, `1104`, `1126` | `gfx_v8_0_init_microcode` | 6 ramas del rango `POLARIS10..POLARIS12` al cargar el microcode |
| `1682` | `gfx_v8_0_gpu_early_init` | Early init de la GPU |
| `1899` | `gfx_v8_0_sw_init` | Inicialización por software de la IP GFX |
| `2632` | `gfx_v8_0_tiling_mode_table_init` | Tabla de modos de tiling |
| `3458` | `gfx_v8_0_raster_config` | Configuración de raster |
| `4031` | `gfx_v8_0_init_pg` | Ruta de power-gating: llama a `gfx_v8_0_init_power_gating(adev)` |
| `5315` | `gfx_v8_0_enable_gfx_static_mg_power_gating` | **Delega el power-gating del bloque GFX al SMU**: `amdgpu_dpm_set_powergating_by_smu(adev, AMD_IP_BLOCK_TYPE_GFX, enable, 0)` |
| `5407` | `gfx_v8_0_set_powergating_state` | Activa power-gating estático de management block según `pg_flags & AMD_PG_SUPPORT_GFX_SMG` |
| `5996` | `gfx_v8_0_set_clockgating_state` | `gfx_v8_0_polaris_update_gfx_clock_gating(adev, state)` |

### 4.3 Memoria — `gmc_v8_0.c`, 4 puntos

| `file:line` | Función | Qué decide |
|---|---|---|
| `141` | `gmc_v8_0_init_golden_registers` | Registros golden de GMC |
| `241` | `gmc_v8_0_init_microcode` | Microcode del controlador de memoria |
| `592` | `gmc_v8_0_mc_init` | **GART de 256 MB** — Polaris12 en el cubo «all engines support GPUVM», igual que Polaris10/11 y VegaM |
| `1220` | `gmc_v8_0_hw_init` | Rama de hw_init específica |
| `amdgpu/amdgpu_gmc.c:1077` | `amdgpu_gmc_init_vga_resv_regions` | Regiones VGA reservadas |

### 4.4 Reset, ASPM y BACO — `vi.c`, 10 puntos

Estos son los que más importan para el topic `RESET` del proyecto.

| `file:line` | Función | Qué decide |
|---|---|---|
| `vi.c:906` | `vi_asic_supports_baco` | Polaris12 → `amdgpu_dpm_is_baco_supported(adev)`. **BACO no está hardcodeado: lo decide la pila PM** |
| `vi.c:932` | `vi_asic_reset_method` | **El método de reset de tu tarjeta lo decide PowerPlay**, no una constante. Con `amdgpu_reset_method` a `-1` (auto) consulta `amdgpu_dpm_is_baco_supported()` |
| `vi.c:1268` | `vi_program_aspm` | Programación de ASPM |
| `vi.c:1344` | `vi_need_full_reset` | Cuándo hace falta un reset completo |
| `vi.c:274` | `vi_query_video_codecs` | Codecs de vídeo soportados |
| `vi.c:523` | `vi_init_golden_registers` | Registros golden de VI |
| `vi.c:1566` | `vi_common_early_init` | Early init común |
| `vi.c:1975` | `vi_common_set_clockgating_state` | Clock gating de VI |
| `vi.c:2107` | `vi_set_ip_blocks` | Qué bloques IP se encienden |
| `vi.c:105` | macro de preprocessador | `asic_type <= CHIP_POLARIS12` en una condición de macro, **fuera de toda función** |

### 4.5 Multimedios

| `file:line` | Función | Qué decide |
|---|---|---|
| `amdgpu/amdgpu_uvd.c:244` | `amdgpu_uvd_sw_init` | Init de UVD |
| `amdgpu/amdgpu_vce.c:138` | `amdgpu_vce_firmware_name` | Nombre del firmware de VCE |
| `amdgpu/vce_v3_0.c:391` | `vce_v3_0_get_harvest_config` | Configuración de harvest (chips recortados de fábrica) |
| `amdgpu/sdma_v3_0.c:217`, `:289` | `sdma_v3_0_init_golden_registers`, `…_init_microcode` | SDMA (copia de datos) |

### 4.6 Quirk de subsistema

| `file:line` | Contexto | Qué decide |
|---|---|---|
| `amdgpu/amdgpu_atpx_handler.c:571` | tabla de quirks APTX | `{0x1002, 0x699f, 0x1028, 0x0814, AMDGPU_PX_QUIRK_FORCE_ATPX}` — para el **subsistema `0x1028:0x0814`**. Tu subsistema es `0x1002:0x0b04`, **así que este quirk NO te aplica** |

## 5. Compute — `amdkfd/`, 6 puntos

Un punto por fichero, todos de inicialización. Solo afectan si usas ROCm/compute.

| `file:line` | Función |
|---|---|
| `kfd_device.c:294` | `kgd2kfd_probe` |
| `kfd_topology.c:2144` | `kfd_topology_add_device` |
| `kfd_crat.c:1613` | `kfd_get_gpu_cache_info` |
| `kfd_device_queue_manager.c:3025` | `device_queue_manager_init` |
| `kfd_flat_memory.c:423` | `kfd_init_apertures` |
| `kfd_packet_manager.c:290` | `pm_init` |

## 6. Display — 3 puntos

| `file:line` | Función | Qué decide |
|---|---|---|
| `display/amdgpu_dm/amdgpu_dm.c:2366` | `load_dmcu_fw` | Qué firmware DMCU carga |
| `display/amdgpu_dm/amdgpu_dm.c:5786` | `amdgpu_dm_initialize_drm_device` | Inicialización del DRM device |
| `display/amdgpu_dm/amdgpu_dm.c:6044` | `dm_early_init` | **`adev->mode_info.num_crtc = 5; num_hpd = 5`** — tu tarjeta declara 5 CRTC y 5 conectores |

## 7. Estado 7.1.3 → 7.2.8 para estos 28 ficheros

| | Ficheros |
|---|---:|
| **Byte-idénticos** | **9** |
| Cambiados, sin tocar ninguna línea Polaris12 | 17 |
| Cambiados **con** contenido Polaris12 | 2 |

Los dos con contenido: `amdgpu/gmc_v8_0.c` (refactor puro — `gart_size` extraído
a `amdgpu_gmc_set_gart_size(adev, SZ_1G)`, tu tarjeta sigue en el cubo de
256 MB) y `pm/powerplay/hwmgr/smu7_hwmgr.c`.

### 7.1 Corrección: sí hay un cambio de comportamiento que te puede alcanzar

En una respuesta anterior afirmé que **no existía ningún cambio de
comportamiento** entre 7.1.3 y 7.2.8 en la ruta de tu RX550, y que el hook
nuevo `smu7_notify_ac_dc` era «inerte». **La primera afirmación era demasiado
fuerte.** Verificado ahora:

7.2.8 añade en `smu7_hwmgr.c`:

```c
static void smu7_notify_ac_dc(struct pp_hwmgr *hwmgr)
{
    if (adev->pm.ac_power &&
        phm_cap_enabled(..., PHM_PlatformCaps_AutomaticDCTransition))
        smum_send_msg_to_smc(hwmgr, PPSMC_MSG_RunningOnAC, NULL);
    pp_funcs->pm_compute_clocks(adev->powerplay.pp_handle);
}
```

La condición que yo había dado por no cumplida **sí se cumple** para
Polaris12: `hwmgr.c:497` activa `PHM_PlatformCaps_AutomaticDCTransition` de
forma incondicional, y `hwmgr.c:501-504` activa además
`PHM_PlatformCaps_SPLLShutdownSupport` para Polaris12. Por tanto la única
condición que queda es `adev->pm.ac_power`, que es un campo interno del driver
**no expuesto en sysfs**: su valor en este host es `NOT_DETERMINED` desde
userspace.

Los otros dos cambios de 7.2.8 en ese fichero sí son-PSM-free y no cambian
decisión: (a) comprobaciones de límites `>= lookup_table->count` con
`pr_err` + `-EINVAL` sobre `vddgfx`/`vddc`, y (b) aplicación de
`PP_PWR_Q24_8_TO_MW()` donde faltaba la conversión de unidades.

**Clasificación:** hay **un** cambio upstream con contenido Polaris12 capaz de
alcanzar tu tarjeta, y es de notificación AC/DC, no de clocks ni DPM levels.

## 8. Lo que este documento NO establece

- **No es un diagnóstico.** Ninguna de las 76 filas dice qué te está causando un
  problema concreto.
- **No cubre `drivers/base/power/`.** La baseline también lo contiene
  (`clock_ops.c`, `common.c`, `generic_ops.c`, `main.c`) y no está comparado con
  7.2.8. `NOT_DONE`.
- **`is_memory_gddr5` es `NOT_DETERMINED`.** Decidido por el punto 8 desde la
  tabla ATOM, no expuesto en sysfs. Cambia el límite de 450 µs a 150 µs.
- **Sin commit de origen.** Los `git log` de estos puntos no se han
  consultado; no hay `COMMIT` asociado a ninguno de los 76.
- **Estabilidad temporal:** el host se midió en una sesión. Sin `TEMPORALITY`
  declarado más allá de `startup`/`steady-state`.
- **Nitidez de la revisión:** `0xC7` frente a `0xCF` es un hecho de
  enumeración del bus PCI, no una revisión de silicio. Que upstream guarde por
  `0xCF` sugiere que laczа concerne a la stepping, pero eso es
  `INFERRED`, no establecido.

## 9. Siguientes pasos que no tocan el driver

| # | Acción | Por qué |
|---:|---|---|
| 1 | `git log -S` sobre el guard de `0x699F` en `smu7_hwmgr.c` para encontrar el commit que lo añadió | decir **qué fallo** motivó el guard; es lo que convierte §3 de `QUESTION` en hipótesis con mecanismo |
| 2 | Diff de `drivers/base/power/` contra 7.2.8 | hueco declarado en §8 |
| 3 | Resolver si el panel va por la RX550 o por la Intel | solo lectura; delimita el riesgo de cualquier cambio futuro |
| 4 | Leer `amdgpu_reset_method` y `amdgpu_dpm_is_baco_supported()` en el árbol vivo | el método de reset de tu tarjeta lo decide el PM, y el topic `RESET` está `NOT_REPRODUCED` |

---

**Verificación de este documento:** 76 puntos, 28 ficheros, 4 áreas. Las cifras
se derivaron con `grep -rn` sobre el árbol sellado y se recomputaron por área
después de escribirse. Las filas con `Qué decide` en `PENDING_READ` no
existen: o se han leído, o no se han incluído.
