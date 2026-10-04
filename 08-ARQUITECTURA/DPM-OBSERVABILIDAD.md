# DPM-OBSERVABILIDAD — Qué se puede ver de la RX 550 con la GPU dormida

**NODE_ID**: `DPM-OBSERVABILIDAD`
**Fecha**: 2026-10-04
**Target**: `0000:01:00.0` = `1002:699f` rev `0xc7`, driver `amdgpu`
**Escrituras al hardware realizadas por este nodo**: **0**

---

## 0. Convenciones de estado (esto es el objeto del trabajo)

| Etiqueta | Significado |
|---|---|
| `MEDIDO_AQUI` | Leí de sysfs/binario en esta máquina, en esta sesión. Con comando y salida literal. |
| `LEIDO_EN_CORPUS` | Leí la línea exacta en `RESEARCH/baseline/linux-7.1.3/`. Con `fichero:línea`. |
| `LEIDO_EN_BINARIO` | Desensamblado/inspeccionado del `amdgpu.ko` instalado. Con offset y bytes. |
| `INFERIDO` | Conclusión razonada. Con la observación que la refutaría. |
| `NOT_DETERMINED` | No se pudo determinar. Con qué falta y dónde está el discriminante. |

**Provenance de `STATE_BEFORE`**: el nodo paralelo `VULKAN-CENSUS` aporta
`08-ARQUITECTURA/CENSUS-CAPACIDADES.md`. **Hash verificado y coincide**:

```
657f6544f45a66740db3bebbfaa897002e333630f758df28f520aad4465d9734  08-ARQUITECTURA/CENSUS-CAPACIDADES.md
```

`STATE_BEFORE` = **TRACED**. No he heredado ningún otro estado sin artefacto.

---

## 1. Qué significa `EBUSY` en esos atributos, con la fuente

### 1.1 Fuente en el corpus — `LEIDO_EN_CORPUS`

El único sitio del driver amdgpu que devuelve `-EBUSY` en la ruta sysfs de Power/Clock/Thermal es
`pm/amdgpu_pm.c`. Cita literal:

```c
/* RESEARCH/baseline/linux-7.1.3/drivers/gpu/drm/amd/pm/amdgpu_pm.c:101-121 */
/**
 * amdgpu_pm_dev_state_check - Check if device can be accessed.
 * @adev: Target device.
 * @runpm: Check runpm status for suspend state checks.
 *
 * Checks the state of the @adev for access. Return 0 if the device is
 * accessible or a negative error code otherwise.
 */
static int amdgpu_pm_dev_state_check(struct amdgpu_device *adev, bool runpm)
{
	bool runpm_check = runpm ? adev->in_runpm : false;
	bool full_init = (adev->init_lvl->level == AMDGPU_INIT_LEVEL_DEFAULT);

	if (amdgpu_in_reset(adev) || !full_init)
		return -EBUSY;

	if (adev->in_suspend && !runpm_check)
		return -EBUSY;

	return 0;
}
```

Y las dos funciones que lo consumen:

```c
/* amdgpu_pm.c:131-140  — modo RESUME: despierta la GPU */
static int amdgpu_pm_get_access(struct amdgpu_device *adev)
{
	int ret;
	ret = amdgpu_pm_dev_state_check(adev, true);
	if (ret)
		return ret;
	return pm_runtime_resume_and_get(adev->dev);
}

/* amdgpu_pm.c:150-168  — modo IF_ACTIVE: NO despierta, sólo comprueba */
static int amdgpu_pm_get_access_if_active(struct amdgpu_device *adev)
{
	int ret;
	/* Ignore runpm status. If device is in suspended state, deny access */
	ret = amdgpu_pm_dev_state_check(adev, false);
	if (ret)
		return ret;
	ret = pm_runtime_get_if_active(adev->dev);
	if (!ret)
		return -EPERM;
	return 0;
}
```

### 1.2 El patrón es total y sin una sola excepción — `LEIDO_EN_CORPUS`

Parseé todos los call-sites de `amdgpu_pm_get_access*` de `amdgpu_pm.c` con sus números de línea.
Resultado: **las 28 funciones `amdgpu_get_*` (lectura) usan `IF_ACTIVE`; las 22 funciones
`amdgpu_set_*` (escritura) usan `RESUME`.** Cero excepciones. Extracto:

| Función | Línea | Modo |
|---|---|---|
| `amdgpu_get_power_dpm_state` | 224 | IF_ACTIVE |
| `amdgpu_get_power_dpm_force_performance_level` | 336 | IF_ACTIVE |
| `amdgpu_get_pp_num_states` | 419 | IF_ACTIVE |
| `amdgpu_get_pp_cur_state` | 449 | IF_ACTIVE |
| `amdgpu_get_pp_table` | 560 | IF_ACTIVE |
| `amdgpu_get_pp_od_clk_voltage` | 863 | IF_ACTIVE |
| `amdgpu_get_pp_features` | 932 | IF_ACTIVE |
| **`amdgpu_get_pp_dpm_clock`** (sclk/mclk/pcie) | **993** | IF_ACTIVE |
| `amdgpu_get_pp_sclk_od` | 1234 | IF_ACTIVE |
| `amdgpu_get_pp_mclk_od` | 1280 | IF_ACTIVE |
| `amdgpu_get_pp_power_profile_mode` | 1350 | IF_ACTIVE |
| **`amdgpu_pm_get_sensor_generic`** (backend de casi todo hwmon) | **1429** | IF_ACTIVE |
| `amdgpu_get_pcie_bw` | 1540 | IF_ACTIVE |
| `amdgpu_get_pm_metrics` | 1725 | IF_ACTIVE |
| `amdgpu_get_gpu_metrics` | 1758 | IF_ACTIVE |
| **`amdgpu_hwmon_show_power_cap_generic`** | **3367** | IF_ACTIVE |
| `amdgpu_hwmon_get_pwm1_enable` / `get_pwm1` / `get_fan1_*` | 2940/3051/3073/3129/3188 | IF_ACTIVE |
| `amdgpu_set_pp_dpm_clock` | 1061 | **RESUME** |
| `amdgpu_set_pp_power_profile_mode` | 1409 | **RESUME** |
| `amdgpu_hwmon_set_power_cap` | 3448 | **RESUME** |

**Consecuencia estructural, y es el punto central del nodo**: *leer nunca despierta la GPU;
escribir sí la despierta.* La telemetría de sysfs es de sólo-rechazo por diseño.

### 1.3 Cadena completa hasta el hardware — `LEIDO_EN_CORPUS`

```
hwmon freq1_input  (amdgpu_pm.c:3639  SENSOR_DEVICE_ATTR)
  -> amdgpu_hwmon_show_sclk            (amdgpu_pm.c:3462)
  -> amdgpu_pm_get_sensor_generic      (amdgpu_pm.c:1423)
  -> amdgpu_pm_get_access_if_active    (amdgpu_pm.c:150)   <-- EBUSY aqui
  -> [si pasa] amdgpu_dpm_read_sensor  (amdgpu_dpm.c:517)
  -> adev->powerplay.pp_funcs->read_sensor
  -> smu7_read_sensor                  (smu7_hwmgr.c:4089)
```

`pp_dpm_sclk` va por `amdgpu_get_pp_dpm_clock` (993) → `amdgpu_dpm_emit_clock_levels`.
`power1_cap_max` va por `amdgpu_hwmon_show_power_cap_generic` (3367) → `amdgpu_dpm_get_power_limit`
(`amdgpu_dpm.c:1564`).

### 1.4 Contraprueba en el BINARIO INSTALADO — `LEIDO_EN_BINARIO`

El `amdgpu.ko` del kernel en marcha **sí está en disco**, y se puede inspeccionar sin tocar la GPU:

```
/lib/modules/7.1.3-200.nobara.fc44.x86_64/kernel/drivers/gpu/drm/amd/amdgpu/amdgpu.ko.zst
  -> amdgpu.ko    sha256 a1a44c2457d33c65149ef4f455173ca446564bfd19bcc9cb215fca10cf24c024
```

`amdgpu_pm_get_sensor_generic` está en `0x412b20` (símbolo local, no exportado). Sus dos
verificadores de puerta fueron *inlined*. Con relocaciones resueltas:

```asm
412b35: mov  0x5f970(%rdi),%rax        ; adev->init_lvl
412b54: mov  (%rax),%ebp                ; adev->init_lvl->level
412b56: call amdgpu_in_reset            ; R_X86_64_PLT32 amdgpu_in_reset
412b5b: or   %eax,%ebp
412b5d: jne  412bc5                     ; -> EBUSY
412b5f: cmpb $0x0,0x5d261(%rbx)         ; bool de adev+0x5d261
412b66: jne  412bc5                     ; -> EBUSY
412b68: mov  (%rbx),%rdi                ; adev->dev
412b6b: call pm_runtime_get_if_active    ; R_X86_64_PLT32
412b70: test %eax,%eax
412b72: je   412bcc                     ; -> EPERM
412b82: call amdgpu_dpm_read_sensor      ; R_X86_64_PLT32
...
412bc5: mov  $0xfffffff0,%ebp           ; -16  == -EBUSY   <-- EL QUE OBSERVAMOS
412bcc: mov  $0xffffffff,%ebp           ; -1   == -EPERM
```

El valor retornado es literalmente `-16`, que es exactamente `errno 16` = `EBUSY`. **Coincide
con la medición.** El shape de la compilación corresponde 1:1 a
`amdgpu_pm_dev_state_check(adev,false)` + `amdgpu_pm_get_access_if_active()` del corpus.

Los campos los nombré con BTF del módulo **en marcha**
(`/sys/kernel/btf/amdgpu` + base `/sys/kernel/btf/vmlinux`, con `pahole --btf_base`):

```
0x5f970 (+8)  struct amdgpu_init_level *  init_lvl;
0x5d261 (+1)  bool                        in_suspend;
0x5d3d0 (+1)  bool                        in_runpm;
```

Es decir: la condición 1 es literalmente
`adev->reset_domain->in_gpu_reset || (adev->init_lvl->level != 0)` y la condición 2 es
`adev->in_suspend`.

```asm
00000000000065c0 <amdgpu_in_reset>:
  65c9: mov 0x5f030(%rdi),%rax     ; adev->reset_domain   (BTF 0x5f030)
  65d0: mov 0x38(%rax),%eax        ; reset_domain + 0x38  -> atomic_t in_gpu_reset
```
```asm
struct amdgpu_reset_domain {
        struct kref                refcount;      /*  0  4 */
        struct workqueue_struct * wq;            /*  8  8 */
        enum amdgpu_reset_domain_type type;       /* 16  4 */
        struct rw_semaphore        sem;           /* 24 32 */
        atomic_t                   in_gpu_reset;  /* 56  4 */   <-- +0x38
        atomic_t                   reset_res;     /* 60  4 */
};
```

`amdgpu_in_reset()` desreferencia `reset_domain` **sin comprobación de NULL**.

### 1.5 LA CONTRADICCIÓN — hallazgo central de este nodo

En el corpus, `adev->in_suspend` lo escribe **sólo** `amdgpu_device_suspend()`:

```c
/* amdgpu_device.c:4440-4448 */
int amdgpu_device_suspend(struct drm_device *dev, bool notify_clients)
{
	...
	adev->in_suspend = true;
```
```c
/* amdgpu_device.c:4676, dentro de amdgpu_device_resume() */
	adev->in_suspend = false;
```

Verifiqué en el binario dónde están esas escrituras:

```asm
0000000000004320 <amdgpu_device_suspend>   (extensión: 0x4320..0x4640)
  4351: movb $0x1,0x5d251(%rdi)      <-- pone 1
0000000000004650 <amdgpu_device_resume>    (extensión: 0x4650..0x4af0)
  4903: movb $0x0,0x5d251(%r13)      <-- pone 0
```

`in_suspend` está en **`0x5d251`**, no en `0x5d261`. Y barrí el `.text` **completo** del módulo:

```
referencias a 0x5d261 : 88   -> todas LECTURAS (cmpb / movzbl)
escrituras a 0x5d261  :  0
```

Control de tarjetas: el mismo barrido encuentra 61 escrituras `mov*` en el bloque `0x5d2xx`
(`has_hw_reset`@0x5d220 ← `$0x1`, `mp1_state`@0x5d26c, etc.), luego el escaneo funciona.
**No hay ni una.**

Y hay una segunda contradicción, independiente y más fuerte:

```asm
0000000000419250 <amdgpu_get_pp_num_states>
  419270: mov 0x5f960(%rbx),%rax     ; init_lvl   <-- OTRO OFFSET
  4192db: mov (%rax),%ebp
  4192dd: call amdgpu_in_reset
  4192e2: or  %eax,%ebp
  4192e4: jne 4192ef                 ; -> -16
  4192e6: cmpb $0x0,0x5d251(%rbx)    ; bool en 0x5d251  <-- OTRO OFFSET
  4192ed: je  419321
  4192ef: mov $0xfffffffffffffff0,%rax   ; -16 = -EBUSY
```

En el corpus, `amdgpu_get_pp_num_states` (línea 419) y `amdgpu_pm_get_sensor_generic` (línea 1429)
llaman **ambos a `amdgpu_pm_get_access_if_active()`**, luego deben compilar **idéntico**. Pero:

| | `init_lvl` | bool de la 2ª condición |
|---|---|---|
| `amdgpu_pm_get_sensor_generic` | `0x5f970` | `0x5d261` |
| `amdgpu_get_pp_num_states` | `0x5f960` | `0x5d251` |
| diferencia | `+0x10` | `+0x10` |

Dos unidades de traducción del **mismo módulo** discrepan en exactamente `0x10` sobre
`struct amdgpu_device`. En una compilación coherente es imposible. Además
`amdgpu_get_pp_num_states` **no llama** a `pm_runtime_get_if_active`, mientras que el corpus le
exige hacerlo. Concluyo:

> **El `amdgpu.ko` instalado no está compilado de forma internamente consistente respecto a
> `struct amdgpu_device` entre `amdgpu_pm.c` y el resto de amdgpu.** Hay una discrepancia de ABI
> de 16 bytes en la ruta exacta de Power/Clock/Thermal.

Observación que lo refutaría: el fuente Nobara de `amdgpu_pm.c` para `7.1.3-200.fc44`
(kernel-devel / kernel-src rpm), o un `Module.symvers`+configuración que muestres los mismos
offsets en ambas unidades. No está en disco: `/usr/src/kernels/7.1.3-200.nobara.fc44.x86_64`
tiene 148 `.c` **todos bajo `scripts/`**, cero bajo `drivers/`.

### 1.6 Qué significa entonces el `EBUSY` observado

`INFERIDO`, con alto grado de confianza:

1. **No es una avería.** Es un rechazo determinista del driver, código de retorno exacto -16,
   función conocida, dos condiciones identificadas por nombre de campo vía BTF.
2. **No es "la GPU está en runtime suspend".** El caso "sólo runtime-suspend" devuelve
   `-EPERM` (`amdgpu_pm.c:164-165`), no `EBUSY`. `power/runtime_status` dice `suspended`, luego
   si ése fuera el estado operative, el errno sería 1.
3. La condición 2 (`in_suspend`) no puede ser la que dispara: en el código compilado de
   `amdgpu_pm.c` **ese byte no lo escribe nadie** (0 escrituras en todo el módulo), luego está
   a 0 por inicialización de `.bss`.
4. ⇒ Por eliminación, el `EBUSY` viene de la **primera** condición:
   `amdgpu_in_reset(adev) || (adev->init_lvl->level != AMDGPU_INIT_LEVEL_DEFAULT)`.
5. Y como `level` se pone a `AMDGPU_INIT_LEVEL_DEFAULT` (=0, `amdgpu.h:835-839`) en la
   inicialización completa, el disyuncto que dispara es
   **`adev->reset_domain->in_gpu_reset != 0`**.

> **Esto es lo contrario de la hipótesis con la que arrancó este nodo.** La hipótesis
> operativa del enunciado —"`EBUSY` significa que la telemetría está bloqueada por un estado
> de energía conocido y no por una avería" — **queda REFUTADA en su parte causal**: el código
> que devuelve `-EBUSY` en esta máquina es el de *reset en curso / nivel de init no
> completo*, no el de *suspensión de energía*. "No es una avería" sigue siendo cierto; "es un
> estado de energía" no.

`NOT_DETERMINED` (con el discriminante named): distinguir definitivamente
`reset_domain->in_gpu_reset != 0` de `init_lvl->level != 0` exige leer uno de esos dos campos
en runtime. Las dos rutas son `/proc/kcore` y `/sys/kernel/debug/amdgpu/*`, **ambas prohibidas
a este nodo**. **REFUTING OBSERVATION para el punto 5**: que
`/sys/kernel/debug/amdgpu/pm_info` exista y muestre un init level distinto de
`AMDGPU_INIT_LEVEL_DEFAULT` → significaría que dispara el segundo disyuncto, y la conclusión 5
caería.

---

## 2. Qué se puede leer SIN despertar la GPU

Barrí el árbol de sysfs de la GPU con `open()` en Python: **253 rutas**, todas lecturas,
sin `grep`, sin abrir `/dev/dri/*`.

```
PRE : runtime_status=suspended  runtime_active_time=278853  runtime_suspended_time=59001183
POST: runtime_status=suspended  runtime_active_time=278853  runtime_suspended_time=59028301
```

`runtime_active_time` **idéntico** antes y después del barrido (0 ms de actividad nueva; sólo
avanzó el reloj monotónico de suspensión 19 ms). **El barrido no despertó la GPU.** Esto
corrobora empíricamente §1.2: las lecturas no toman referencia de runtime PM.

Resultado: **156 OK, 46 EBUSY (= 30 únicos), 12 EACCES, 39 omitidas por política propia.**

Los 46 EBUSY son 30 atributos únicos contados dos veces, porque `hwmon1` existe bajo dos rutas
(`/sys/class/hwmon/hwmon1/` y `/sys/bus/pci/devices/0000:01:00.0/hwmon/hwmon1/`). **30 únicos =
14 en el nodo PCI + 16 en hwmon**, que reproduce exactamente el recuento del nodo `VULKAN-CENSUS`.

### 2.1 Tabla de tres columnas

#### `LEGIBLE_DORMIDA` — dato obtained, GPU en `D3hot`

Ruta exacta bajo `/sys/bus/pci/devices/0000:01:00.0/` salvo indicación. Todas leídas, valor literal.

| Atributo | Valor leído | Interés para DPM |
|---|---|---|
| `max_link_speed` | `8.0 GT/s PCIe` | Techo PCIe de la placa, **estático** |
| `max_link_width` | `8` | Techo de ancho, **estático** |
| `current_link_speed` | `5.0 GT/s PCIe` | ⚠ legible pero **CACHÉ, no actual** (ver §2.4) |
| `current_link_width` | `4` | ⚠ ídem |
| `board_info` | `type : cem` | Tipo de placa |
| `vbios_build` | `565939` | Identidad de VBIOS |
| `vbios_version` | `xxx-xxx-xxx` | Placeholder del driver |
| `fw_version/smc_fw_version` | `0x00221700` | **Versión del SMC**, la que gobierna DPM |
| `fw_version/{pfp,me,ce,rlc,sdma,sdma2,mc,mec,mec2,uvd,vce}_fw_version` | `0xfe / 0xa7 / 0x8c / 0x18 / 0x3a / 0x3a / 0xb4dc50 / 0x2da / 0x2da / 0x1821000 / 0x351a0300` | Todas legible |
| `mem_info_vram_total` | `2147483648` | 2 GiB VRAM |
| `mem_info_vis_vram_total` | `268435456` | 256 MiB visibles |
| `mem_info_gtt_total` | `6194638848` | GTT |
| `mem_info_vram_used` | `5439488` | **Cambia con el uso → observable en vivo** |
| `mem_info_vis_vram_used` | `5439488` | ídem |
| `mem_info_gtt_used` | `14163968` | ídem |
| `thermal_throttling_logging` | `0000:01:00.0: thermal throttling logging enabled, with interval 60 seconds` | **R-NEW-72: el throttling se está logueando** |
| `link/l1_aspm` | `0` | L1 ASPM deshabilitado |
| `pp_force_state` | *(vacío)* | **Ningún P-state forzado** → DPM gobierna |
| `boot_vga` | `1` | |
| `enable` | `1` | |
| `d3cold_allowed` | `1` | |
| `reset_method` | `bus` | |
| `irq` | `37` | |
| `numa_node` | `-1` | |
| `power/control` | `auto` | §3 |
| `power/runtime_status` | `suspended` | |
| `power/runtime_active_time` | `278853` | |
| `power/runtime_suspended_time` | `59001183` | |
| `power/autosuspend_delay_ms` | `5000` | Retardo de autosuspend |
| `power/wakeup` | `disabled` | |
| `device` / `revision` / `vendor` | `0x699f` / `0xc7` / `0x1002` | |
| `subsystem_device` / `subsystem_vendor` | `0x0b04` / `0x1002` | AMD genérico, **no** 1028:0814 |
| `aer_dev_correctable` / `_nonfatal` / `_fatal` | todo ceros | Sin errores PCIe |
| `/sys/class/hwmon/hwmon1/name` | `amdgpu` | |
| **`/sys/class/hwmon/hwmon1/temp1_crit`** | **`97000`** | **Techo térmico = 97.000 °C** (§5) |
| `/sys/class/hwmon/hwmon1/temp1_crit_hyst` | `-273150` | Centinela: histéresis nunca fijada |
| `/sys/class/hwmon/hwmon1/temp1_label` | `edge` | Sensor de borde |
| `/sys/class/hwmon/hwmon1/freq1_label` | `sclk` | **Nombre del reloj, dormida** |
| `/sys/class/hwmon/hwmon1/freq2_label` | `mclk` | **Nombre del reloj, dormida** |
| `/sys/class/hwmon/hwmon1/in0_label` | `vddgfx` | **Rail presente, dormida** |
| `/sys/class/hwmon/hwmon1/power1_label` | `PPT` | **Dominio de potencia, dormida** |
| `/sys/class/hwmon/hwmon1/pwm1_max` | `255` | **Techo de ventilador = 100 %** |
| `/sys/class/hwmon/hwmon1/pwm1_min` | `0` | |

Lo relevante para las ideas del usuario: **la GPU declara el nombre de sus relojes
(`sclk`, `mclk`), el nombre de su rail de tensión (`vddgfx`), el nombre de su dominio de
potencia (`PPT`), su techo térmico (97 °C) y su techo de ventilador (255), todo dormida.**
Lo que no se puede leer dormida son **los valores instantáneos**.

#### `DEVUELVE_EBUSY` — 30 únicos, `errno 16` = `Device or resource busy`

Nodo PCI (14), bajo `/sys/bus/pci/devices/0000:01:00.0/`:

`pp_dpm_sclk` · `pp_dpm_mclk` · `pp_dpm_pcie` · `pp_num_states` · `pp_cur_state` ·
`pp_table` · `pp_sclk_od` · `pp_mclk_od` · `pp_power_profile_mode` ·
`power_dpm_force_performance_level` · `power_dpm_state` · `gpu_busy_percent` ·
`mem_busy_percent` · `pcie_bw`

hwmon (16), bajo `/sys/class/hwmon/hwmon1/`:

`freq1_input` · `freq2_input` · `temp1_input` · `in0_input` · `power1_input` ·
`power1_cap` · `power1_cap_max` · `power1_cap_min` · `power1_cap_default` ·
`pwm1` · `pwm1_enable` · `fan1_input` · `fan1_target` · `fan1_enable` ·
`fan1_min` · `fan1_max`

#### `OTRO`

| Clase | Nº | Contenido |
|---|---|---|
| `EACCES` (errno 13) | 12 | `resource0`, `resource0_wc`, `resource2`, `resource2_wc`, `resource4`, `resource5`, `i2c-{6,7,8}/new_device`, `i2c-{6,7,8}/delete_device`. **No es energía**: son permisos root. `resource0` = 256 MiB de VRAM BAR0 mapeada; leerla exige root, no despierta nada. |
| Omitidas por política propia | 39 | `reset`, `remove`, `rescan`, `uevent`, `driver_override`, `rom`, `autosuspend_delay_ms`, `control`, subárboles `drm/`, `i2c-*/i2c-dev/`, `wakeup/*`, `aer/*`. No las leo: unas son escrituras (`reset`, `remove`, `rescan`), otras no aportan a DPM. **Declarado, no medido.** |
| **Ausentes del todo** | — | `temp2_*`, `temp3_*`, `temp*_emergency`, `in1_input`, `in2_input`, `power2_*`, `fan1_label`, `pp_dpm_force_performance_level_choices`, `power1_average`. Ver §6. |

### 2.2 `power1_average` ausente: CORROBORACIÓN CRUZADA INDEPENDIENTE — `MEDIDO_AQUI` + `LEIDO_EN_CORPUS`

`power1_average` **no existe** en `hwmon1`. El fuente lo explica:

```c
/* smu7_hwmgr.c:4151-4158 */
case AMDGPU_PP_SENSOR_GPU_AVG_POWER:
    if ((adev->asic_type != CHIP_HAWAII) && ... &&
        (adev->asic_type != CHIP_TONGA))
            return -EOPNOTSUPP;      /* <-- Polaris12 cae aqui */
```
```c
/* amdgpu_pm.c:3790-3793, en amdgpu_hwmon_sensor_visible() */
if (attr == &sensor_dev_attr_power1_average.dev_attr.attr &&
    amdgpu_pm_get_sensor_generic(adev, AMDGPU_PP_SENSOR_GPU_AVG_POWER,
                                 (void *)&tmp) == -EOPNOTSUPP)
        return 0;                     /* <-- oculta el atributo */
```

**Ésta es una prueba independiente, hecha desde el árbol sysfs real, de que esta tarjeta corre
PowerPlay legado `smu7_hwmgr` y no swsmu.** No la.saqué del código: la deduje de la ausencia de
un fichero. Corrobora §4.

### 2.3 `pp_dpm_sclk`/`pp_dpm_mclk`/`pp_dpm_pcie` NO son lecturas puras — `LEIDO_EN_CORPUS`

Riesgo asumido, no hecho seguro:

```c
/* smu7_hwmgr.c:5056-5104 */
static int smu7_emit_clock_levels(struct pp_hwmgr *hwmgr, ..., int *offset)
{
	struct smu7_single_dpm_table *sclk_table = &(data->dpm_table.sclk_table);
	...
	case PP_SCLK:
		ret = smum_send_msg_to_smc(hwmgr, PPSMC_MSG_API_GetSclkFrequency, &clock);
		...
		for (i = 0; i < sclk_table->count; i++)
			size += sysfs_emit_at(buf, size, "%d: %uMhz %s\n", i,
					      sclk_table->dpm_levels[i].value / 100,
					      (i == now) ? "*" : "");
```

La **tabla** viene de RAM del driver (`data->dpm_table`, cargada del PowerPlay table al boot);
la **marca `*` de nivel actual** requiere un *mailbox message* a la SMC
(`PPSMC_MSG_API_GetSclkFrequency = 0x200`, `smu7_ppsmc.h:334`;
`API_GetMclkFrequency = 0x201`, línea 335). Es decir: **leer `pp_dpm_sclk` escribe un registro
MMIO** (`mmSMU_MP1_SRBM2P_MSG_0`, `ARG_0`, `RESP_0` — §4.1). Igual `pp_dpm_pcie`, que llama a
`smu7_get_current_pcie_speed` (línea 5106).

### 2.4 `power1_input` es la peor de las 30 — `LEIDO_EN_CORPUS`

```c
/* smu7_hwmgr.c:4044-4087 */
static int smu7_get_gpu_power(struct pp_hwmgr *hwmgr, u32 *query)
{
	...
	if ((adev->asic_type != CHIP_HAWAII) && ... ) {
		smum_send_msg_to_smc_with_parameter(hwmgr, PPSMC_MSG_GetCurrPkgPwr, 0, &tmp);
		*query = tmp;
		if (tmp != 0)
			return 0;
	}
	/* ---- RAMPA DE RESPALDO ---- */
	smum_send_msg_to_smc(hwmgr, PPSMC_MSG_PmStatusLogStart, NULL);
	cgs_write_ind_register(hwmgr->device, CGS_IND_REG__SMC, ixSMU_PM_STATUS_95, 0);
	for (i = 0; i < 10; i++) {
		msleep(500);                                   /* 500 ms */
		smum_send_msg_to_smc(hwmgr, PPSMC_MSG_PmStatusLogSample, NULL);
		tmp = cgs_read_ind_register(hwmgr->device, CGS_IND_REG__SMC, ixSMU_PM_STATUS_95);
		if (tmp != 0)
			break;
	}
```

Consecuencias medibles, ambas `LEIDO_EN_CORPUS`:

1. Si `GetCurrPkgPwr` devuelve 0, **leer `power1_input` bloquea hasta 10 × 500 ms = 5 s**.
   Relevante directo para **N-INT-48** ("necesita sampling suficiente"): el periodo de muestreo
   efectivo de un observador de potencia no puede bajar de 5 s mientras esta rampa esté activa.
2. La rampa **escribe** `ixSMU_PM_STATUS_95` (`cgs_write_ind_register`) e invoca
   `PmStatusLogStart`/`PmStatusLogSample`. **Un "read" de `power1_input` puede escribir en el
   hardware.** Lo declaro como **riesgo asumido**: no he podido verificar en fuente que la
   escritura sea destructiva, y no he ejecutado nada que la dispare.

### 2.5 `current_link_speed` legible ≠ actual — `INFERIDO`

`current_link_speed` y `current_link_width` devuelven `5.0 GT/s` y `4` con la GPU dormida. El
PCIe link no puede estar negotiating a 5 GT/s en D3hot. Son valores **cacheados en RAM del
driver**, actualizados en resume. **Legible no significa actual.** Consecuencia para
**N-INT-51** (mapa de independencia SCLK/MCLK): cualquier "estado actual" leído por sysfs en
este target puede estar obsoleto, y hay que distinguir lectura-de-RAM de lectura-de-hardware
para cada atributo. La tabla §2.1 marca cuáles son de qué tipo.

---

## 3. `power/control` y `power_state`, LEÍDOS

### 3.1 Lo que dice ahora — `MEDIDO_AQUI`

```
$ cat /sys/bus/pci/devices/0000:01:00.0/power/control
auto
$ cat /sys/bus/pci/devices/0000:01:00.0/power_state
D3hot
$ cat /sys/bus/pci/devices/0000:01:00.0/power/runtime_status
suspended
$ cat /sys/bus/pci/devices/0000:01:00.0/power/autosuspend_delay_ms
5000
$ stat -c '%n %A %U:%G' /sys/bus/pci/devices/0000:01:00.0/power/control
/sys/bus/pci/devices/0000:01:00.0/power/control -rw-r--r-- root:root
```

Ciclo de servicio medido:
`278853 / (278853 + 59001183) = 0.4704 %` activo, **99.5296 % suspendido**. Reproduce el
99.52 % de `VULKAN-CENSUS`.

Parámetros del módulo, leídos: `runpm = -1` (auto), `dpm = -1` (auto), `gpu_recovery = -1`,
`msi = -1`, `ppfeaturemask = 0xfff7bfff`, `sched_hw_submission = 2`, `umsch_mm = 0`.
**Runtime PM está habilitado**, luego `power/control=auto` es la política vigente.

### 3.2 Qué implicaría cada valor — `LEIDO_EN_CORPUS`

| Valor | Efecto | ¿Despierta la GPU? |
|---|---|---|
| `auto` (actual) | Autosuspend tras `autosuspend_delay_ms` de inactividad | No por sí solo |
| `on` | Runtime PM queda *forzado a activo*; ya no hay autosuspend | **Sí, y se queda despierto** |

Es semántica del core PM (`drivers/base/power/sysfs.c`), no de amdgpu. Del lado amdgpu, el que
se opone al runtime suspend es:

```c
/* amdgpu_drv.c:2800-2810, amdgpu_pmops_runtime_suspend() */
static int amdgpu_pmops_runtime_suspend(struct device *dev)
{
	...
	if (adev->pm.rpm_mode == AMDGPU_RUNPM_NONE) {
		pm_runtime_forbid(dev);
		return -EBUSY;
	}
```

Es decir: si `rpm_mode == AMDGPU_RUNPM_NONE`, el driver se **auto-prohíbe** (`pm_runtime_forbid`)
y nunca se suspende. `runpm = -1` significa "el driver decide", y está decidiendo suspender.

### 3.3 LA CONCLUSIÓN FUERTE que pedía el nodo

> **En el nivel de sysfs, observar SCLK/MCLK/potencia/temperatura obliga a escribir.**
> No existe ruta de sólo-lectura que llegue a los 30 atributos.

Evidencia: §1.2 (toda lectura usa `IF_ACTIVE`, que devuelve `-EBUSY` sin despertar) + §3.1
(`power/control = auto`) + §2.1 (`power/runtime_status = suspended`, corroborado por
`runtime_active_time` invariante durante el barrido).

Matiz importante, y creo que es lo más accionable del nodo: **el bloqueo no es uniforme en
coste.** De los 30 atributos, al menos 11 los sirve el driver **desde RAM, sin tocar hardware**:

- `pp_dpm_sclk` / `pp_dpm_mclk` / `pp_dpm_pcie` → tabla en `data->dpm_table` (§2.3; sólo el
  asterisco de "actual" va a la SMC)
- `power1_cap`, `power1_cap_max`, `power1_cap_min`, `power1_cap_default` → `pp_get_power_limit`
  lee `hwmgr->default_power_limit`, RAM pura (§5.2)
- `pp_num_states`, `pp_cur_state` → tablas de estado en RAM

Para ésos, el `EBUSY` **no protege hardware**: es una puerta de política aplicada uniformemente.
Y no es uniforme por descuido — §2.2 demuestra que el driver **sí** sabe degradar atributos
(\`power1_average\` no existe), y sin embargo no degrada los de RAM.

**Refutación de "observar obliga a escribir"**: si existiera un `pp_dpm_sclk` legible, no
haría falta escribir. REFUTING OBSERVATION: un `cat` exitoso a cualquiera de esos 11 con
`runtime_status=suspended`. No lo obtuve; los 30 dan `EBUSY`.

`NOT_DETERMINED`: **no existe en este target ningún canal de sólo-lectura a la telemetría.**
Los candidatos serían `debugfs` (`/sys/kernel/debug/amdgpu/pm_info`, prohibido aquí y exige
root), `ftrace`/`kprobe` sobre `amdgpu_pm_get_sensor_generic` (haría falta `bpftrace` y
`CAP_BPF`/root), `/proc/kcore` (prohibido), o un `power/control` distinto (escritura).
Ninguno es de sólo-lectura *y* no-privilegiado a la vez.

---

## 4. La máquina de estados de DPM desde las cabeceras

### 4.0 Qué IP blocks usa esta tarjeta — `LEIDO_EN_CORPUS`

```
amdgpu_drv.c:2041   {0x1002, 0x699F, PCI_ANY_ID, PCI_ANY_ID, 0, 0, CHIP_POLARIS12}
amdgpu_device.c:1980-1989   CHIP_POLARIS12 -> vi_set_ip_blocks(adev)
vi.c:2105-2123      vi_common, gmc_v8_1, tonga_ih, gfx_v8_0, sdma_v3_1,
                    pp_smu, dm, uvd_v6_3, vce_v3_4
amd_powerplay.c:294-301    pp_smu_ip_block { .type = AMD_IP_BLOCK_TYPE_SMC, 1.0.0,
                                            .funcs = &pp_ip_funcs }
hwmgr.c:154-160,169 CHIP_POLARIS12 -> hwmgr->smumgr_funcs = &polaris10_smu_funcs
                                ; smu7_init_function_pointers(hwmgr)
smumgr.c:49-50     MODULE_FIRMWARE("amdgpu/polaris12_smc.bin"),
                   MODULE_FIRMWARE("amdgpu/polaris12_k_smc.bin")
```

**Polaris12 corre PowerPlay legado (`smu7_hwmgr` + `polaris10_smu_funcs` + firmware SMU8), NO
swsmu.** Corroborado por ausencia de `pm/swsmu/smu8/` (sólo `smu11 smu12 smu13 smu14 smu15`) y
por la corroboración cruzada independiente de §2.2.

Dato lateral útil: el quirk de ATPX de `0x699f` (`amdgpu_atpx_handler.c:571`) está condicionado
a subsistema `1028:0814`. Nuestra tarjeta es `1002:0b04` → **el quirk no aplica**.
También `ASICID_IS_P23` (`amdgpu.h:769-778`) sólo cubre `0x6987` y `0x6981`; nuestra
`0x699f` rev `0xc7` **no** es P23.

### 4.1 HALLAZGO: en SMU 8.0 la máquina de estados DPM NO es un mapa de registros

Conté los defines DPM/PSTATE/PWR de las cabeceras SMU:

| Cabecera | Líneas | Defines `ix\w*(DPM|PSTATE|PWR_)\w*` |
|---|---|---|
| `asic_reg/smu/smu_7_0_0_d.h` | 742 | **243** (incluye `ixDPM_TABLE_1..N` @`0x3f000`+) |
| `asic_reg/smu/smu_7_1_0_d.h` | 1345 | **506** |
| **`asic_reg/smu/smu_8_0_d.h`** (la de esta tarjeta) | 672 | **9** |

En `smu_8_0_d.h` sólo quedan 9, y ninguno es una tabla DPM programable desde el host:

```c
460: #define ixCURRENT_PSTATE_NB              0xd0211008
480: #define ixSPR_FUSE_PSTATEPWR1            0xd0211058
481: #define ixSPR_FUSE_PSTATEPWR2            0xd021105c
482: #define ixSPR_FUSE_PSTATEPWR3            0xd0211060
495: #define ixUNBPM_EXIT_TO_PSTATE           0xd0211098
```

> **En Polaris12/SMU8 el DPM no se programa con registros: vive en la SMC y se consulta por
> mailbox.** No existe un "registro de estado DPM" que el host pueda pollar.

Corrijo un error metodológico que cometí y dejo constancia: mi primer barrido de
`dpcs/`, `smuio/`, `athub/` devolvió "0 registros" porque busqué el prefijo `ix`. Esos
headers usan prefijo **`mm`**. El recuento correcto:

| Cabecera | Registros (mm*) | DPM-relevantes |
|---|---|---|
| `dpcs/dpcs_2_0_0_offset.h` | 273 | 25: `mmDPCSTX{0..5}_DPCSTX_TX_CLOCK_CNTL` (`0x2928`+`0xD8·n`), `mmRDPCSTX*_RDPCSTX_CLOCK_CNTL`, `mmRDPCSTX*_RDPCSTX_MEM_POWER_CTRL` (`0x2937`+…) y `_MEM_POWER_CTRL2` |
| `smuio/smuio_9_0_offset.h` | 75 | 0 (sólo `ROM_CNTL`/`ROM_INDEX`/`ROM_DATA`, `CGTT_ROM_CLK_CTRL0`) |
| `athub/athub_1_0_offset.h` | 208 | 1: `mmATHUB_MEM_POWER_LS` (`0x003a`) |
| `smu/smu_8_0_d.h` | 643 | 45, §4.2 |

DPCS 2.0.0 trae la estructura de **6 transmisores PCIe** (DPCSTX0..5) cada uno con su
`_TX_CLOCK_CNTL` y su `RDPCSTX*_MEM_POWER_CTRL`/`_2`. Eso **sí** es estructura de DPM
observable por registro, y es el sitio natural para **N-INT-47** (observador de transiciones)
y **N-INT-48** (latencia de transición). No verificado en hw: no he tocado la GPU.

### 4.2 Estructura, no semántica — lo que se puede inferir de los nombres

Distingo `NOMBRE DE REGISTRO` de `SEMANTICA`. Lo que sigue son **nombres y offsets medidos en
las cabeceras**; lo que *significan* es `NOT_DETERMINED` salvo donde el código del driver lo
usa explícitamente.

**(a) Mailbox host↔SMC** — `smu_8_0_d.h:250-297`, 16 ranuras cada uno:

```c
250: #define mmSMU_MP1_SRBM2P_MSG_0   0x1c0   ... MSG_15   0x1cf
266: #define mmSMU_MP1_SRBM2P_RESP_0  0x1d0   ... RESP_15  0x1df
282: #define mmSMU_MP1_SRBM2P_ARG_0   0x1e0   ... ARG_15   0x1ef
```
Uso real, `smu8_smumgr.c:66-102`: escribe `ARG_0`←parámetro, `RESP_0`←0, `MSG_0`←id, y hace
poll de `RESP_0` con `PHM_WAIT_FIELD_UNEQUAL(..., CONTENT, 0)`. Respuesta en
`mmSMU_MP1_SRBM2P_ARG_0` (`smu8_get_argument`, línea 56-63).

**(b) SRAM privada de la SMC, acceso indirecto por índice** — `smu_8_0_d.h:193-200`, 16 pares:

```c
193: #define mmMP0PUB_IND_INDEX_0  0x180   ... INDEX_15  0x19e
194: #define mmMP0PUB_IND_DATA_0   0x181   ... DATA_15   0x19f
```
Uso real, `smu8_smumgr.c:109-144`:
```c
cgs_write_register(hwmgr->device, mmMP0PUB_IND_INDEX_0, SMN_MP1_SRAM_START_ADDR + smc_address);
cgs_write_register(hwmgr->device, mmMP0PUB_IND_DATA_0,  value);
```
con las comprobaciones `3 & smc_address` (alineación 4 B) y `limit <= smc_address+3`.
**Éste es el canal por el que se lee/escribe la tabla DPM en runtime.** Es una vista de 32 bits
con índice de 32 bits (`PWRHW_SMC_IND_INDEX__SMC_IND_ADDR_MASK 0xffffffff`,
`smu_8_0_sh_mask.h:1337`), no un mapa plano. Ésta es la variable que un observador de DPM
necesitaría, y es la que no existe expuesta por sysfs.

**(c) FSM de gestión de potencia "UNBPM"** — `smu_8_0_d.h:458-510`, con campos nombrados en
`smu_8_0_sh_mask.h:1369-1442`:

| Registro | Offset | Campos con máscara |
|---|---|---|
| `ixUNBPM_PWRMGT_ACK` | `0xd0211000` | `REQUESTOR_CODE` (5b), `REQUEST_ACK` (b8), `REQUEST_NACK` (b16), `ERROR_CODE` (8b, b24) |
| `ixUNBPM_NBPWRMGT_CMD` | `0xd0211010` | `TARGET_BLOCK` (2b), `TARGET_CMD` (b8), `DCT_SR_MAP` (8b,b16), `RETURN_NB_ACK` (b24), `OVERRIDE_PARAMS` (b25), **`SET_NB_LOW_POWER`** (b26), **`SET_NB_STUTTER_MODE`** (b27) |
| `ixUNBPM_NBPWRMGT_FSM_CFG` | `0xd0211014` | `DIS_AUTO_PWRGATE_ON_EXIT` (b1) |
| `ixUNBPM_FUSES_VAL_PWROK` | `0xd0211028` | (fuse de power-ok) |
| `ixMISC_SMU_PWRMGT_CFG0` / `_DATA` | `0xd0211030` / `0xd0211048` | `TARGET_ADDR` (32b), `TIMER_EN`, `TIMER_INTERVAL` (17b) |
| `ixMISC_GNB_PWRMGT_CFG0/1/DATA` | `0xd0211094`/`0xd0211034`/`0xd021103c` | idem |
| `ixUNBPM_PWRCTRL_MISC` | `0xd02110bc` | |
| `ixUNBPM_PWRMGT_REQ_DBG_STATUS` | `0xd02110d4` | |
| `ixUNBPM_EXIT_TO_PSTATE` | `0xd0211098` | |
| `ixPOWERON_CPU_0/1`, `ixPOWERREADY_CPU_0/1` | `0xd0220000/04`, `0xd0230000/04` | |
| `ixCOREPM_PWRCTRL_MISC_0` | `0xd022002c` | |

**Lo que se puede inferir de los nombres** (`INFERIDO`): existe una FSM de gestión de potencia
con comando/ack de estilo handshake, direccionable por bloques, con modo de baja potencia y
modo *stutter*, y con fuses de *power-ok*. Es decir, la existencia de una **máquina de estados
de encendido/apagado** está命名 por el hardware. Lo que **no** se puede inferir de los nombres
es la polaridad de cada bit, el orden real de las transiciones, ni qué campos corresponden a
MCLK. **Refutación**: que un `UNBPM_NBPWRMGT_CMD` observado no responden al modelo de 2 bloques
con ack.

**(d) Mensajes SMC del dominio DPM** — `pm/powerplay/inc/cz_ppsmc.h` (101 defines). Los
relevantes:

```c
 62: #define PPSMC_MSG_GetFeatureStatus             0x2
 77: #define PPSMC_MSG_SetMinDeepSleepSclk          0x11
102: #define PPSMC_MSG_SetPstateSoftMin             0x2A
103: #define PPSMC_MSG_SetPstateSoftMax             0x2B
104: #define PPSMC_MSG_SetPstateHardMin             0x2C
105: #define PPSMC_MSG_SetPstateHardMax             0x2D
106: #define PPSMC_MSG_DisableLowMemoryPstate       0x2E
107: #define PPSMC_MSG_EnableLowMemoryPstate        0x2F
117: #define PPSMC_MSG_PowerStateNotify             0x39
119: #define PPSMC_MSG_GetMaxSclkLevel              0x3B
125: #define PPSMC_MSG_GetMaxPstate                 0x41
135: #define PPSMC_MSG_GetConservativePowerLimit    0x4B
140: #define PPSMC_MSG_NBDPM_Enable                 0x140
141: #define PPSMC_MSG_NBDPM_Disable                0x141
143: #define PPSMC_MSG_DPM_FPS_Mode                 0x15d
144: #define PPSMC_MSG_DPM_Activity_Mode            0x15e
170: #define PPSMC_MSG_DPM_ForceState               0x104
```
```c
/* smu7_ppsmc.h */
334: #define PPSMC_MSG_API_GetSclkFrequency   0x200
335: #define PPSMC_MSG_API_GetMclkFrequency   0x201
393: #define PPSMC_MSG_GetCurrPkgPwr          0x282
```
`cz_ppsmc.h:38-42` define además `enum DPM_ARRAY { HARD_MAX, HARD_MIN, SOFT_MAX, SOFT_MIN }`,
y `173-179` las máscaras `SCLK_DPM_MASK 0x00080000`, `UVD_DPM_MASK 0x00010000`,
`VCE_DPM_MASK 0x00400000`, `NB_DPM_MASK 0x00000800`.

`PPSMC_MSG_PowerStateNotify` (0x39) y `PPSMC_MSG_GetFeatureStatus` (0x2) son, por nombre, la
**notificación de cambio de estado de potencia** y la **consulta de features de DPM**. Son los
dos candidatos naturales para un observador **por evento** en vez de por sondeo — mucho más
barato que N-INT-48 con polling. `NOT_DETERMINED` si están habilitado en esta SMC.

**Negativo relevante**: `PPSMC_MSG_GetConservativePowerLimit` (0x4B) está **definido y nunca
referenciado** en todo el árbol. No es un camino vivo.

### 4.3 La estructura DPM sí está en RAM del driver, y es por parejas

Ésta es la estructura que de verdad implementa las ideas N-INT-51/57:

```c
/* smu7_hwmgr.h:77-86 */
struct smu7_power_state {
	uint32_t                  magic;
	struct smu7_uvd_clocks    uvd_clks;
	struct smu7_vce_clocks    vce_clks;
	uint32_t                  sam_clk;
	uint16_t                  performance_level_count;
	bool                      dc_compatible;
	uint32_t                  sclk_threshold;
	struct smu7_performance_level performance_levels[SMU7_MAX_HARDWARE_POWERLEVELS];
};

/* hardwaremanager.h:270-277 */
struct PHM_PerformanceLevel {
	uint32_t coreClock;              uint32_t vddc;
	uint32_t memory_clock;           uint32_t vddci;
	uint32_t nonLocalMemoryFreq;     uint32_t nonLocalMemoryWidth;
};
```
```c
/* smu7_hwmgr.h:88-110 */
struct smu7_dpm_level { bool enabled; uint32_t value; uint32_t param1; };
#define MAX_REGULAR_DPM_NUMBER 8
struct smu7_single_dpm_table { uint32_t count; struct smu7_dpm_level dpm_levels[MAX_REGULAR_DPM_NUMBER]; };
struct smu7_dpm_table {
	struct smu7_single_dpm_table sclk_table, mclk_table, pcie_speed_table,
	                            vddc_table, vddci_table, mvdd_table;
};
```
```c
/* smu7_hwmgr.h:112-126: registros de reloj que el driver conocer */
struct smu7_clock_registers {
	uint32_t vCG_SPLL_FUNC_CNTL, vCG_SPLL_FUNC_CNTL_2/3/4,
	         vCG_SPLL_SPREAD_SPECTRUM, vCG_SPLL_SPREAD_SPECTRUM_2,
	         vDLL_CNTL, vMCLK_PWRMGT_CNTL,          /* <-- MCLK power mgmt */
	         vMPLL_AD_FUNC_CNTL, vMPLL_DQ_FUNC_CNTL,
	         vMPLL_FUNC_CNTL, vMPLL_FUNC_CNTL_1/2, vMPLL_SS1, ...
};
```

**Consecuencia directa para N-INT-51** (`INFERIDO`): **SCLK y MCLK se mueven en una tabla
*compartida*, con `sclk_table` y `mclk_table` como dos tablas sisters dentro de
`struct smu7_dpm_table`, y cada nivel de performance lleva un par `(coreClock, memory_clock)`.
La independencia SCLK/MCLK no es libre por nivel: la granularidad la fija `MAX_REGULAR_DPM_NUMBER
= 8` y la Tabla de PowerPlay. Refutación: que un nivel del par SCLK/MCLK vara de forma
independiente de la tabla, con más de 8 niveles.

**Para N-INT-60** (histéresis): `sclk_threshold` (offset 40 del power state) y
`hwmgr->sclk_cec_leakage`/`sclk_dpm_ce_threshold` son estructura de histéresis explícita en el
propio driver. Y `hwmgr.c:500-503` marca `PHM_PlatformCaps_SPLLShutdownSupport` **para
POLARIS12**, y `hwmgr.c:505-512` marca `DBRamping`/`TDRamping`/`TCPRamping` para POLARIS12
(`!= CHIP_POLARIS11`). Eso es estructura de transición de voltaje, que es donde vive la
histéresis de R-NEW-72.

---

## 5. El techo de energía de ESTA tarjeta

### 5.1 Techo térmico: SÍ, medido y legible dormida — `MEDIDO_AQUI`

```
/sys/class/hwmon/hwmon1/temp1_crit        = 97000       -> 97.000 °C
/sys/class/hwmon/hwmon1/temp1_label       = edge
/sys/class/hwmon/hwmon1/temp1_crit_hyst   = -273150     -> centinela, histéresis nunca fijada
/sys/class/hwmon/hwmon1/pwm1_max          = 255         -> 100 % ventilador
/sys/class/bus/pci/.../thermal_throttling_logging =
    "0000:01:00.0: thermal throttling logging enabled, with interval 60 seconds"
```

**97.000 °C en el sensor `edge`, y el log de throttling térmico está ACTIVO con intervalo de
60 s.** Éste es el techo térmico duro y ya es un hecho, sin necesidad de despertar nada.

### 5.2 Techo de potencia eléctrica: `NOT_DETERMINED`, y la razón es interesante — `LEIDO_EN_CORPUS`

`power1_cap_max`, `power1_cap_min`, `power1_cap_default` y `power1_cap` dan `EBUSY`.
**No se puede determinar el valor, y no se estima.**

Lo importante es *por qué* es interesante. Su backend **no toca hardware**:

```c
/* amd_powerplay.c:973-1009 */
static int pp_get_power_limit(void *handle, uint32_t *limit,
			      enum pp_power_limit_level pp_limit_level,
			      enum pp_power_type power_type)
{
	struct pp_hwmgr *hwmgr = handle;
	if (!hwmgr || !hwmgr->pm_en || !limit)      return -EINVAL;
	if (power_type != PP_PWR_TYPE_SUSTAINED)    return -EOPNOTSUPP;
	switch (pp_limit_level) {
	case PP_PWR_LIMIT_CURRENT:  *limit = hwmgr->power_limit;             break;
	case PP_PWR_LIMIT_DEFAULT:  *limit = hwmgr->default_power_limit;     break;
	case PP_PWR_LIMIT_MAX:
		*limit = hwmgr->default_power_limit;
		if (hwmgr->od_enabled)
			*limit *= (100 + hwmgr->platform_descriptor.TDPODLimit);
			*limit /= 100;
		break;
	case PP_PWR_LIMIT_MIN:      *limit = 0;                             break;
	default: ret = -EOPNOTSUPP;                                          break;
	}
	return ret;
}
```
(`PP_PWR_LIMIT_MIN` es literalmente **0**, hardcodeado.) Se registra como
`.get_power_limit = pp_get_power_limit` en la línea 1586, y `amdgpu_dpm.c:1564-1578` lo despacha.

De dónde sale ese número:
```c
/* smu7_powertune.c:1181-1182, dentro de smu7_enable_power_containment() */
hwmgr->default_power_limit = hwmgr->power_limit =
		cac_table->usMaximumPowerDeliveryLimit;
```
```c
/* struct phm_cac_tdp_table (USHORT = uint16) */
uint16_t usTDC, usBatteryPowerLimit, usSmallPowerLimit, usLowCACLeakage,
         usHighCACLeakage, usMaximumPowerDeliveryLimit, usEDCLimit, ...
```

> **El techo de potencia es un campo `uint16` de la PowerPlay Table v1** (`cac_dtp_table`),
> cargado al boot en RAM del driver. No es un registro, no se consulta a la SMC, y no cambia en
> runtime (salvo que se escriba `power1_cap`). **Existe y es un valor fijo; es que el fichero
> que lo expone está detrás de la puerta `EBUSY`.**

Si `power1_cap_max` fuese 0 al despertar la GPU, significaría que power containment está
desactivado (§5.3). Esa es la predicción falsable.

### 5.3 Si el valor es значимый o 0 — `INFERIDO`

`default_power_limit` sólo se rellena si `PP_CAP(PHM_PlatformCaps_PowerContainment)` **y**
`data->enable_pkg_pwr_tracking_feature` (`smu7_powertune.c:1162,1174,1181`).
`PowerContainment` viene de `PP_POWER_CONTAINMENT_MASK` (`hwmgr.c:465-467`).

Y aquí hay una coincidencia que hay que registrar con precisión, porque es fácil equivocarse:

```c
/* smu7_hwmgr.c:1975-1984 */
if ((adev->pdev->device == 0x699F) &&
    (adev->pdev->revision == 0xCF)) {
	phm_cap_unset(hwmgr->platform_descriptor.platformCaps,
			PHM_PlatformCaps_PowerContainment);
	data->enable_tdc_limit_feature = false;
	data->enable_pkg_pwr_tracking_feature = false;
	data->disable_edc_leakage_controller = true;
	phm_cap_unset(..., PHM_PlatformCaps_ClockStretcher);
}
```

El corpus **sí** tiene un caso especial para `0x699F`, y desactiva el power containment
justo para el `0x699F` rev **`0xCF`**. **Nuestra tarjeta es `0x699F` rev `0xc7` — NO es
`0xCF`.** El `unset` **no se aplica**. Predicción: `power1_cap_max` debería dar un valor
distinto de 0. `C7` ≠ `CF`: un dígito. No lo aproximo.

`NOT_DETERMINED` el valor. **Refutación**: leer `power1_cap_max` con la GPU despierta y ver 0 →
refutaría que PowerContainment esté activo en esta tabla concreta, y con ello toda la cadena.

---

## 6. Qué queda bloqueado, y por qué

### 6.1 `BLOQUEADO_POR_ESTADO_DE_ENERGIA`

Sólo se resuelve **durmiendo la GPU el tiempo suficiente y leyendo**, que es una **escritura**
(`power/control`) y por tanto una **decisión de autorización**, no una acción de este nodo.

| Bloqueado | Por qué |
|---|---|
| `freq1_input` (SCLK), `freq2_input` (MCLK) | `amdgpu_pm_get_sensor_generic`→`IF_ACTIVE`; y el valor viene de mailbox a la SMC (§4.1) |
| `temp1_input` | ídem; sensor leído vía SMC |
| `power1_input` | ídem; y su rampa de respaldo **escribe** `ixSMU_PM_STATUS_95` y puede tardar 5 s (§2.4) |
| `in0_input` (vddgfx) | ídem; lee `PWR_SVI2_STATUS` indirecto de la SMC |
| `gpu_busy_percent`, `mem_busy_percent` | ídem; leen soft-registers de SMC (`AverageGraphicsActivity`/`AverageMemoryActivity`) |
| `power1_cap*` | **No lo bloquea la energía**: es RAM (§5.2). Bloqueo por política. |

### 6.2 `BLOQUEADO_POR_AUTORIZACION`

| Bloqueado | Por qué |
|---|---|
| `/sys/kernel/debug/amdgpu/pm_info` y amigos | `debugfs` prohibido por el encargo; además root |
| `/proc/kcore` | prohibido por el encargo |
| `power/control` → `on` | Escritura. Prohibida. |
| `bpftrace`/kprobe sobre `amdgpu_pm_get_sensor_generic` | Requiere `CAP_BPF`/root; y adjuntar un kprobe es escribir en el kernel |
| `vulkaninfo`/`glxinfo`/`radeontop`/`amdgpu_top` | Prohibidos por el encargo |
| `dmesg`/`journalctl` | Prohibidos por el encargo — y probablemente **es donde estaría la prueba de §1.6** |
| `resource0`..`resource5` (BARs) | Requiere root (`EACCES`), no energía |
| `gartsize`, `gttsize`, `vramlimit`, `moverate`, `ignore_min_pcap` | `EACCES` en `/sys/module/amdgpu/parameters/` |

### 6.3 `NO_EXISTE_EN_ESTE_TARGET`

Verificado por listado real de `hwmon1`, y confirmado por el código que los ocultaría:

| Ausente | Causa | Cita |
|---|---|---|
| `power1_average` | `GPU_AVG_POWER` → `-EOPNOTSUPP` en Polaris12 | `smu7_hwmgr.c:4151-4158`, `amdgpu_pm.c:3790-3793` |
| `temp2_*`, `temp3_*` | Sin sensores junction ni VRAM-mem en esta placa | `amdgpu_pm.c:3601-3608` (sólo se crean si el sensor existe) |
| `temp*_emergency` | Capacidad no presente | `amdgpu_pm.c:3600,3604,3608` |
| `in1_input`, `in2_input` | Sólo hay un rail: `vddgfx`. Sin `vddnb`/`vddboard` | `amdgpu_pm.c:3623,3625` |
| `power2_*` | Un solo dominio de potencia (`PPT`) | `amdgpu_pm.c:3634-3638` |
| `fan1_label` | No implementado para este driver | `amdgpu_pm.c:3612-3616` |
| `*_choices` (`power_dpm_force_performance_level_choices` etc.) | El driver no las crea en esta versión | ausente del listado |
| **Los 30 atributos con `EBUSY`** | **No es una ausencia**: existen y responden. Bloqueados por política. | §1, §3.3 |

Y una ausencia conceptual, la más importante de esta sección:

| Ausente | Por qué importa |
|---|---|
| **Cualquier registro DPM consultable** | En SMU8 el DPM no es un mapa de registros (§4.1). Vive en la SMC. **No hay polling possible sin un cliente SMC**, y un cliente SMC es un driver, no una herramienta. |

---

## 7. Qué significa esto para las ideas del usuario

No son planes: son restricciones medidas que las ideas tienen que respetar.

| Idea | Efecto de este nodo |
|---|---|
| **N-INT-47** observador de transiciones MCLK | **MÁS SEGURO de lo que se suponía, y menos útil.** El DPM no está en registros (`smu_8_0_d.h`: 9 defines DPM). No hay registro que delatar una transición. Lo que sí existe: `mmRDPCSTX*_MEM_POWER_CTRL` (DPCS 2.0.0) y `vMCLK_PWRMGT_CNTL` (`smu7_clock_registers`) — estructura, semántica `NOT_DETERMINED`. |
| **N-INT-48** latencia de transición MCLK | **Restricción dura y medible:** leer `power1_input` puede tardar 5 s (§2.4). Un muestreo por debajo de 5 s no es posible por polling de sysfs. Y todo polling devuelve `EBUSY`. |
| **N-INT-50** clasificador de workload para MCLK | El discriminante existe en hardware: `AverageGraphicsActivity` y `AverageMemoryActivity` son **soft-registers separados** de la SMC (`smu7_hwmgr.c:4117-4128`) → carga de GPU y de VRAM son variables distintas. Ambos dan `EBUSY` ahora. |
| **N-INT-51** mapa de independencia SCLK/MCLK | **Respuesta estructural:** `sclk_table` y `mclk_table` son tablas sisters en `struct smu7_dpm_table`, ≤ `MAX_REGULAR_DPM_NUMBER`=8 niveles, y cada nivel lleva el par `(coreClock, memory_clock)`. La independencia está acotada por la Tabla de PowerPlay. |
| **N-INT-56** curva respuesta frecuencia→rendimiento/potencia/energía/temperatura | Requiere las 4 variables simultáneas. 3 de 4 dan `EBUSY`. El techo térmico (97 °C) sí es legible. |
| **N-INT-57** sensibilidad por clase de workload | Necesita la separación GPU-load / VRAM-load, que existe (§N-INT-50). |
| **N-INT-58** energía por frame (**no FPS/W**) | **El más afectado.** `power1_input` es la única fuente de energía instantánea y es la peor: `EBUSY` + posible escritura a `ixSMU_PM_STATUS_95` + hasta 5 s de latencia. |
| **N-INT-59** energy-delay product | Ídem N-INT-58. |
| **N-INT-60** histéresis transición potencia vs workload | La estructura de histéresis existe: `sclk_threshold` en el power state; `PHM_PlatformCaps_SPLLShutdownSupport`, `DBRamping`, `TDRamping`, `TCPRamping` activas para POLARIS12 (`hwmgr.c:500-512`); `PPSMC_MSG_PowerStateNotify` (0x39) como evento, no sondeo. |
| **R-NEW-72** máximo rendimiento práctico sostenido | **Con lo medido: 97.000 °C es un hecho.** El techo eléctrico es `NOT_DETERMINED` (§5.2). El techo de PCIe es legible: 8.0 GT/s x8 máximo, 5.0 GT/s x4 en uso — pero **es caché, no actual** (§2.5). |

---

## 8. Reproducibilidad

- Corpus: `RESEARCH/baseline/linux-7.1.3/`, sin modificar.
- Binario: `amdgpu.ko` descomprimido de
  `/lib/modules/7.1.3-200.nobara.fc44.x86_64/kernel/drivers/gpu/drm/amd/amdgpu/amdgpu.ko.zst`
  → `sha256 a1a44c2457d33c65149ef4f455173ca446564bfd19bcc9cb215fca10cf24c024`.
  Descompresión y extracción en `/tmp/opencode/amdgpu_probe/` (**fuera del árbol del proyecto**).
- BTF: `/sys/kernel/btf/amdgpu` + base `/sys/kernel/btf/vmlinux`, leídos con
  `pahole --btf_base`.
- Barrido sysfs: `open()` + `os.walk`, 253 rutas, resultado en `/tmp/opencode/sweep.json`.
  Sin `grep`. Sin abrir `/dev/dri/*`.
- Cero escrituras al hardware. Cero `modprobe`/`rmmod`. Cero `dmesg`/`journalctl`.

### Limitación de provenance que declaro

`objdump` se ejecutó sobre el `.ko` **de disco**; los offsets BTF salen del módulo **en
marcha**. Que ambos coincidan en `0x5d261` y `0x5f970` sugiere que son el mismo build, pero **no
lo he probado**. Si el módulo en marcha fuera un build distinto, §1.4 se mantendría (es
estructura del `.ko` de disco) pero §1.5 se debilitaría. **Refutación**: comparar
`/sys/kernel/btf/amdgpu` contra el BTF del `.ko` de disco con `--btf_base`.

---

## 9. Resumen de estados

| # | Afirmación | Estado |
|---|---|---|
| 1 | Los 30 atributos dan `EBUSY`; 30 únicos = 14 PCI + 16 hwmon | `MEDIDO_AQUI` (corrobora `VULKAN-CENSUS`) |
| 2 | El código del `EBUSY` es `amdgpu_pm.c:109-121` / `150-168` | `LEIDO_EN_CORPUS` |
| 3 | El binario retorna literalmente `-16` | `LEIDO_EN_BINARIO` |
| 4 | Las 28 lecturas usan `IF_ACTIVE`; las 22 escrituras usan `RESUME` | `LEIDO_EN_CORPUS` |
| 5 | `in_suspend`/`init_lvl` en `0x5d261`/`0x5f970` | `LEIDO_EN_BINARIO` (BTF) |
| 6 | El módulo instalado tiene **0 escrituras** a `0x5d261` | `LEIDO_EN_BINARIO` |
| 7 | Dos unidades de traducción discrepan `0x10` sobre `struct amdgpu_device` | `LEIDO_EN_BINARIO` |
| 8 | `EBUSY` viene de la 1ª puerta, no del estado de energía | `INFERIDO` (§1.6) |
| 9 | Cuál disyuncto dispara (`in_gpu_reset` vs `init_lvl->level`) | **`NOT_DETERMINED`** (§1.6) |
| 10 | Observar SCLK/MCLK/potencia/temp obliga a escribir | `INFERIDO` (§3.3), refutación nombrada |
| 11 | 11 de los 30 atributos los sirve el driver desde RAM | `LEIDO_EN_CORPUS` |
| 12 | En SMU8 el DPM no es un mapa de registros (9 vs 243/506 defines) | `LEIDO_EN_CORPUS` |
| 13 | SCLK/MCLK son tablas sisters, ≤8 niveles, par `(coreClock, memory_clock)` | `LEIDO_EN_CORPUS` |
| 14 | La tarjeta corre PowerPlay legado, no swsmu | `LEIDO_EN_CORPUS` + corroboración `MEDIDO_AQUI` (§2.2) |
| 15 | Techo térmico = **97.000 °C** (edge), legible dormida | `MEDIDO_AQUI` |
| 16 | Techo de potencia = `uint16` de la PowerPlay Table en RAM; **valor `NOT_DETERMINED`** | `LEIDO_EN_CORPUS` + `NOT_DETERMINED` |
| 17 | `0x699F` rev **`0xC7`** ≠ el caso rev `0xCF` que desactiva PowerContainment | `LEIDO_EN_CORPUS` + `MEDIDO_AQUI` |
| 18 | Leer `power1_input` puede escribir `ixSMU_PM_STATUS_95` y tardar 5 s | `LEIDO_EN_CORPUS` (riesgo asumido, no ejecutado) |
| 19 | `current_link_speed` es caché, no actual | `INFERIDO` |
| 20 | No hay registro DPM consultable; hace falta cliente SMC | `LEIDO_EN_CORPUS` |