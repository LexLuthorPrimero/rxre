# GEOMETRIA-SEGUNDA-FUENTE — la geometria de la ASIC se lee sin la ROM, y ya esta medida

```text
AGENCIA=RX550-INVESTIGACION · WORK_CLASS=AGENT-MAIN-SISTEMAS · NODO=GEOMETRIA-SEGUNDA-FUENTE
GENERADO=2026-10-04 · MEDIDO=EN ESTA HOST · TARGET=1002:699F rev 0xc7 (CHIP_POLARIS12)
SIN ESCRITURAS AL HARDWARE · SIN ioctl · SIN APERTURA DE /dev/dri NI /dev/kfd · SIN ROOT
ENTRADA PRIMARIA=RESEARCH/baseline/linux-7.1.3/drivers/gpu/drm/amd/amdgpu/amdgpu_atombios.c
             (60399 B, md5 2f86803f613120e0ef6ce65e8a30dcbe, 1951 lineas, leido COMPLETO)
```

## 0. Resumen de lo que este turno cambia

| nº | afirmación | estado antes | estado despues |
|---|---|---|---|
| 1 | `cu_per_simd_array = 5` | `CONFLICTADO` | **`PROVEN_DERIVED`** — es `max_cu_per_sh` y es la **capacidad por ranura**, no el total |
| 2 | «8 CU» | `CONFLICTADO` con el 5 | **`PROVEN_DERIVED`** — son 8 CU **activas**, y no compiten con el 5 |
| 3 | «los 16 cachés published exigen >= 10 CU» | assertion del proyecto | **`REFUTED`** — los 16 cachés cubren 8 `processor_id_low` distintos |
| 4 | «los tres números vienen del MISMO registro CRAT» | premisa del proyecto | **`REFUTED`** — el 5 sale de la tabla maestra `GFX_Info` del ATOMBIOS; el 8 sale de contar registros MMIO |
| 5 | existe una CRAT ACPI | supuesto por el proyecto | **`PROVEN_ABSENT`** — `/sys/firmware/acpi/tables/CRAT` no esta; la CRAT publicada es **VCRAT sintetizada** |
| 6 | `vbios_version` es el campo de versión | supuesto por el hallazgo 1053 | **`REFUTED`** — imprime `ctx->vbios_pn` (nº de parte), no `ctx->vbios_ver_str` |
| 7 | «ATOMBIOS sin campo de versión rellenado» | supuesto por el hallazgo 1053 | **`REFUTED`** — el ATOMBIOS esta presente **y parseado**; lo que se publica es otro campo |
| 8 | tamaños de caché L1 «vienen del firmware» | `NOT_DETERMINED` (MEMORIA-GFX8.md:129) | **`REFUTED`** — salen de la constante `carrizo_cache_info` |
| 9 | inventario consolidado del ASIC | — | **`PROVEN_ABSENT`** — no existe ningun documento asi |

**La geometria de esta ASIC esta completa y medida, sin root y sin la ROM.** Vease §4.

## 1. Alcance de busqueda declarado (obligatorio antes de cualquier ausencia)

Sin este apartado, cualquier `NOT_FOUND` mio seria irresponsable.

```text
CORPUS DE CODIGO
  /home/lucas/Escritorio/RX550-INVESTIGACION/RESEARCH/baseline/linux-7.1.3/
    raices presentes:  Documentation  drivers  include
    ficheros .c        984
    ficheros .h       1721
    ficheros .rs         0
    TOTAL            2705          <-- ver la CORRECCION del hallazgo 1053 en §6.1
  drivers/gpu/drm/amd/amdgpu/   625 ficheros .c/.h
  drivers/gpu/drm/amd/amdkfd/    68 ficheros
  drivers/gpu/drm/amd/include/   atombios.h, atomfirmware.h

CORPUS INCOMPLETO — IMPORTANTE
  amdgpu_pm.c            NO ESTA EN EL CORPUS
  kfd_populate_node_properties   no existe en este arbol
  amdgpu_kms_dev_info            no existe en este arbol
  drivers/gpu/drm/amd/amdgpu/perfctr/  no esta (PERFCTR ausente)

ARBOL DE DISPOSITIVOS MEDIDO
  /sys/bus/pci/devices/0000:01:00.0/         (identico a /sys/class/drm/card1/device/)
  /sys/module/amdgpu/parameters/
  /sys/class/kfd/kfd/topology/nodes/0 y /1
  /sys/class/drm/card1/device/  y sus subdirectorios
  /sys/firmware/acpi/tables/
  /sys/kernel/debug/           (raiz: modo 0700 root)
  /proc/modules
```

Consecuencia directa yobligatoria: **todo lo que yo no encuentre en este corpus se declarara
`NOT_FOUND`, nunca `PROVEN_ABSENT`.** Solo uso `PROVEN_ABSENT` sobre poblaciones que he
enumerado por completo y cuyo resultado he leido.

## 2. Estado de energia: medido antes y despues

```text
ANTES (inicio del turno)
  /sys/bus/pci/devices/0000:01:00.0/power/runtime_status = suspended
  /sys/bus/pci/devices/0000:01:00.0/power/runtime_active_time = 278853

DESPUES (final del turno)
  runtime_status         = suspended
  runtime_active_time    = 278853          <-- IDENTICO
  runtime_suspended_time = 66245912        (antes 65337590; crece con el tiempo, es normal)
  power/control          = auto
  autosuspend_delay_ms   = 5000

VEREDICTO: LA GPU NO SE HA REANUDADO NI UNA SOLA VEZ EN TODO EL TURNO.
runtime_active_time es el contador que el hallazgo 1045 usa como prueba de no-resume,
y no se ha movido. Lectura de sysfs y de /proc solamente.
```

`dmesg` **NO_VERIFICABLE**: `dmesg: read kernel buffer failed: Operacion no permitida`.
Los `pr_err`/`pr_warn` de arranque de amdgpu son, por tanto, inaccesibles en este turno.

## 3. MITA A — la busqueda de la segunda via

### 3.1 `/sys/module/amdgpu/parameters/` — inventario COMPLETO

**96 parametros.** Verificados por dos vias independientes que coinciden:

```text
  ls -1 /sys/module/amdgpu/parameters/            -> 96 entradas
  modinfo amdgpu | grep -c '^parm'               -> 96 entradas
```

Los 96 valores, medidos:

| parametro | valor |lectura para esta ASIC |
|---|---|---|
| `abmlevel` `-1` · `agp` `-1` · `aspm` `-1` · `audio` `-1` · `backlight` `-1` | | sin informacion de ASIC |
| `async_gfx_ring` | `1` | anillo asincrono activo |
| **`bad_page_threshold`** | `-1` | |
| `bapm` `-1` · **`cg_mask`** `18446744073709551615` | | mascara completa |
| `cik_support` `-1` | | |
| **`compute_multipipe`** | `-1` | |
| **`cwsr_enable`** | `1` | CWSR activo |
| `damageclips` `-1` · `dc` `-1` · `dcdebugmask` `0` · `dcfeaturemask` `2` | | |
| `debug_evictions` `N` · `debug_mask` `0` · `deep_color` `0` | | |
| **`disable_cu`** | **`(null)`** | **VEASE §3.5: es la mascara de CU y esta vacia** |
| `discovery` `-1` · `disp_priority` `0` · **`dpm`** `-1` | | |
| `emu_mode` `0` · `enforce_isolation` `-1` · **`exp_hw_support` `0`** | | |
| **`force_asic_type`** | `-1` | autodeteccion, coherente con CHIP_POLARIS12 |
| `forcelongtraining` `0` · `freesync_video` `0` · `fw_load_type` `-1` | | |
| **`gartsize`** | **`Permiso denegado`** | modo `rw-------` root |
| `gpu_recovery` `-1` | | |
| **`gttsize`** | **`Permiso denegado`** | modo `rw-------` root |
| `halt_if_hws_hang` `0` · `hdmi_hpd_debounce_delay_ms` `0` · `hw_i2c` `0` | | |
| `hws_gws_support` `N` · `hws_max_conc_proc` `-1` | | |
| **`ignore_min_pcap`** | **`Permiso denegado`** | modo `rw-------` root |
| **`ip_block_mask`** | **`4294967295`** | **ningun bloque de IP desactivado** |
| `lbpw` `-1` · **`lockup_timeout`** | *(vacio)* | |
| `max_num_of_queues_per_device` `4096` · `mcbp` `-1` · `mes_log_enable` `0` · `modeset` `-1` | | |
| **`moverate`** | **`Permiso denegado`** | modo `rw-------` root |
| `msi` `-1` · `mtype_local` `-1` · `no_queue_eviction_on_vm_fault` `0` · `noretry` `-1` | | |
| `no_system_mem_limit` `N` · `num_kcq` `-1` | | |
| `pcie_gen2` `-1` · `pcie_gen_cap` `0` · `pcie_lane_cap` `0` · **`pcie_p2p` `Y`** | | |
| **`pg_mask`** | **`4294967295`** | |
| **`ppfeaturemask`** | **`0xfff7bfff`** | |
| `queue_preemption_timeout_ms` `9000` · `ras_enable` `-1` · `ras_mask` `4294967295` | | |
| `rebar` `-1` · `reset_method` `-1` · `runpm` `-1` | | |
| **`sched_hw_submission`** | **`2`** | |
| `sched_jobs` `32` · `sched_policy` `0` · `sdma_phase_quantum` `32` · `seamless` `-1` | | |
| `send_sigterm` `0` · `sg_display` `-1` · `si_support` `-1` | | |
| **`smu_memory_pool_size`** | **`0`** | |
| **`smu_pptable_id`** | **`-1`** | autodeteccion |
| **`svm_default_granularity`** | **`9`** | |
| `timeout_fatal_disable` `N` · `timeout_period` `0` · `tmz` `-1` | | |
| `umsch_mm` `0` · `umsch_mm_fwlog` `0` · **`uni_mes` `1`** | | |
| **`user_partt_mode`** | **`4294967294`** | |
| `user_queue` `-1` · `use_xgmi_p2p` `1` · `vcnfw_log` `0` · `virtual_display` `(null)` | | |
| `visualconfirm` `0` · `vis_vramlimit` `0` | | |
| **`vm_block_size`** `-1` · `vm_fault_stop` `0` · `vm_fragment_size` `-1` · `vm_size` `-1` · `vm_update_mode` `-1` | | |
| **`vramlimit`** | **`Permiso denegado`** | modo `rw-------` root |
| `wbrf` `-1` | | |

**Veredicto sobre este punto.** De los 96 parametros, **ninguno publica geometria de CU**.
Los que llevan prefijo `gfx_*`, `pp_*` o `dpm_*` que se buscaban **no existen como parametros
de modulo**: `pp_*` y `dpm_*` son atributos de sysfs bajo `card1/device/`, no parametros.
`NOT_FOUND` con alcance: los 96 nombres listados arriba, leidos uno a uno.

Lo que si es informativo y es nuevo:

- **`disable_cu = (null)`** — este es el parametro que enmascara CU. Vacio. Por tanto
  **el bitmap de CU activo que se mide mas abajo NO viene de una mascara de software**:
  viene del hardware. Esto es lo que hace que §4 sea una medida y no una copia de una
  configuracion. Verificado por nombre y descripcion: `modinfo amdgpu` ->
  `parm: disable_cu:Disable CUs (se.sh.cu,...) (charp)`.
- **`ip_block_mask = 4294967295`** y **`pg_mask = 4294967295`** — ningun bloque de IP
  descartado, coherente con que la IP discovery de la seccion 4.5 no corra.
- **`gartsize`, `gttsize`, `vramlimit`, `moverate`, `ignore_min_pcap`** son los 5 unicos
  inaccesibles, los 5 con modo `rw-------` root. `NO_VERIFICABLE`, no `PROVEN_ABSENT`.

### 3.2 `/sys/class/drm/card1/device/` — arbol completo

Enumerado el directorio y **todos** sus subdirectorios. Contenido:

```text
ATRIBUTOS PLANOS (nombre -> valor medido)
  vbios_version                     xxx-xxx-xxx          <-- ver §5
  vbios_build                       565939__            (con 2 espacios finales)
  board_info                        type : cem
  boot_vga                          1                    <-- el riesgo del hallazgo 1045
  d3cold_allowed                    1
  reset_method                      bus
  class / revision                  0x030000 / 0xc7
  vendor / device                   0x1002 / 0x699f
  subsystem_vendor / _device        0x1002 / 0x0b04
  ari_enabled                       0
  dma_mask_bits                     40
  consistent_dma_mask_bits          40
  local_cpulist / local_cpus        0-7
  numa_node                         -1
  msi_bus                           1
  current_link_speed / _width       5.0 GT/s PCIe / 4
  max_link_speed / _width           8.0 GT/s PCIe / 8
  mem_info_vram_total               2147483648          (= 2 GiB)
  mem_info_vram_used                5439488
  mem_info_vis_vram_total           268435456           (= 256 MiB, 1/8)
  mem_info_vis_vram_used            5439488
  mem_info_gtt_total                6194638848
  mem_info_gtt_used                 14163968
  mem_info_preempt_used             0
  uevent / modalias / driver -> ../../../../bus/pci/drivers/amdgpu
  driver_override                   (existe, vacio)

BLOQUES DE BAR (leibles por el modo, NO por el contenido)
  resource0    268435456 B   modo rw------- root
  resource2     2097152 B   modo rw------- root
  resource4          256 B  modo rw------- root
  resource5        262144 B  modo rw------- root   (= 256 KiB, el 128 KiB x2 de la ROM)
  rom           131072 B    modo rw------- root   <-- hallazgo 1053

SUBDIRECTORIOS
  aer/        aer_dev_correctable, aer_dev_fatal, aer_dev_nonfatal,
              correctable_ratelimit_{burst,interval_ms}, nonfatal_ratelimit_{burst,interval_ms}
  drm/        card1/  (boot_display=1, card1-DVI-D-1/, card1-HDMI-A-2/, dev, uevent)
              controlD65 -> card1
              renderD129/ (boot_display, dev, uevent)
  fw_version/ ce, mc, mec, mec2, me, pfp, rlc, sdma, sdma2, smc, uvd, vce
  hwmon/hwmon1/ 37 atributos (name=amdgpu, temp1_label=edge, freq1_label=sclk,
                 freq2_label=mclk, in0_label=vddgfx, power1_label=PPT, pwm*, power1_*)
  i2c-6/     name = "AMDGPU i2c bit bus OEM 0x97"
  i2c-7/     name = "AMDGPU DM i2c hw bus 0"
  i2c-8/     name = "AMDGPU DM i2c hw bus 1"
  link/      l1_aspm
  msi_irqs/  37
  power/     autosuspend_delay_ms, control, runtime_active_time, runtime_status,
             runtime_suspended_time, wakeup, wakeup_abort_count, wakeup_active,
             wakeup_active_count, wakeup_count, wakeup_expire_count,
             wakeup_last_time_ms, wakeup_max_time_ms, wakeup_total_time_ms
  wakeup/wakeup14/

ATRIBUTOS QUE RESPONDEN EBUSY  <-- NUEVO
  pp_num_states, pp_power_profile_mode, pp_mclk_od, pp_sclk_od,
  power_dpm_state, power_dpm_force_performance_level, pp_cur_state,
  gpu_busy_percent, mem_busy_percent
  -> todos: "Dispositivo o recurso ocupado"  (errno EBUSY = 16)

ATRIBUTO VACIO
  pp_force_state  -> cadena vacia, NO error
```

**Hallazgo nuevo, el EBUSY.** Nueve atributos de gestion de energia responden **EBUSY**, no
EACCES, con la GPU en `suspended`. La distincion importa: **EACCES** seria un problema de
permisos (irreparable sin root), **EBUSY** es un estado interno del driver. La causa exacta es
`NOT_FOUND` en mi alcance: `amdgpu_pm.c` **no esta en el corpus** (§1) y los nombres
`pp_num_states`, `power_dpm_state` y `gpu_busy_percent` **no aparecen en ninguno de los 625
ficheros de `amdgpu/`**. No afirmo cual es el `return -EBUSY`; afirmo que no lo he encontrado
en el alcance declarado.

**Decision tomada y su porque.** `/sys/class/drm/card1/device/pp_table` existe y NO lo he
leido. Su funcion `show` vive en `amdgpu_pm.c`, que no esta en mi corpus; por tanto **no puedo
demostrar que su lectura no reanude la GPU**. El beneficio de leerlo no compensa con un riesgo
que no puedo acotar, y el hallazgo 1045 ya decidio no reanudar el device de display
(`boot_vga = 1`, medido aqui). Queda `NO_VERIFICABLE` por decision propia, no por permiso.

### 3.3 `/sys/class/kfd/kfd/topology/nodes/1/` — completo

`properties` es un **fichero**, no un directorio. Contenido integro (39 campos):

```text
cpu_cores_count 0            mem_banks_count 1          caches_count 16
io_links_count 1             p2p_links_count 0           cpu_core_id_base 0
simd_id_base 2147487744      max_waves_per_simd 10       lds_size_in_kb 64
gds_size_in_kb 0             num_gws 0                   wave_front_size 64
array_count 2                simd_arrays_per_engine 1    cu_per_simd_array 5
simd_per_cu 4                max_slots_scratch_cu 32     gfx_target_version 80003
vendor_id 4098               device_id 27039             location_id 256
domain 0                     drm_render_minor 129        hive_id 0
num_sdma_engines 2           num_sdma_xgmi_engines 0     num_sdma_queues_per_engine 2
num_cp_queues 24             cwsr_size 2789376           ctl_stack_size 4096
max_engine_clk_fcompute 1071 local_mem_size 0            fw_version 730
capability 4736              capability2 0               debug_prop 0
sdma_fw_version 58           unique_id 0                 num_xcc 1
max_engine_clk_ccompute 4000
gpu_id 12578                 name polaris12
```

`node name = polaris12` es la medicion que fija `adev->asic_type == CHIP_POLARIS12` en el
arbol de este nodo, y por tanto la rama `CHIP_POLARIS12` de `gfx_v8_0_gpu_early_init`.

`mem_banks/0` = 2147483648 B, coherente con `mem_info_vram_total` = 2147483648.

**Cotejo con el enunciado del encargo.** El encargo decia «lo que NO hay ahi es el numero de CU
ni CU-por-SE. Confirma o refuta». **REFUTADO, en las dos partes:**

- **CU-por-SE: SI esta.** `cu_per_simd_array = 5` es literalmente `max_cu_per_sh` (§4.2).
- **Numero de CU: SI esta, dos veces y por dos vias independientes.** `simd_count / simd_per_cu
  = 32 / 4 = 8` (`kfd_queue.c:492`), y la aritmetica de `cwsr_size` (§4.3). Ninguna de las dos
  necesita la ROM.

### 3.4 Los 16 cachés: el dato que cierra la contradiccion

Las 16 entradas, medidas campo a campo. **Ocho `processor_id_low` distintos, no diez ni
dieciseis**, y el identificador **…749 falta**:

| cache | `processor_id_low` | `level` | `size` KiB | `cache_line_size` | `type` | `sibling_map[0..3]` |
|---|---|---|---|---|---|---|
| 0 | 2147487745 | 1 | 16 | 64 | 9 | 1,0,0,0 |
| 1 | 2147487746 | 1 | 16 | 64 | 9 | 1,0,0,0 |
| 2 | 2147487747 | 1 | 16 | 64 | 9 | 1,0,0,0 |
| 3 | 2147487748 | 1 | 16 | 64 | 9 | 1,0,0,0 |
| 4 | 2147487750 | 1 | 16 | 64 | 9 | 1,0,0,0 |
| 5 | 2147487751 | 1 | 16 | 64 | 9 | 1,0,0,0 |
| 6 | 2147487752 | 1 | 16 | 64 | 9 | 1,0,0,0 |
| 7 | 2147487753 | 1 | 16 | 64 | 9 | 1,0,0,0 |
| 8 | 2147487745 | 1 | 32 | 64 | **10** | **1,1,1,0** |
| 9 | 2147487748 | 1 | 32 | 64 | **10** | 1,0,0,0 |
| 10 | 2147487750 | 1 | 32 | 64 | **10** | **1,1,1,0** |
| 11 | 2147487753 | 1 | 32 | 64 | **10** | 1,0,0,0 |
| 12 | 2147487745 | 1 | 16 | 64 | 9 | **1,1,1,0** |
| 13 | 2147487748 | 1 | 16 | 64 | 9 | 1,0,0,0 |
| 14 | 2147487750 | 1 | 16 | 64 | 9 | **1,1,1,0** |
| 15 | 2147487753 | 1 | 16 | 64 | 9 | 1,0,0,0 |

Recuento: **12 de `size 16 / type 9`**, **4 de `size 32 / `type 10`**, **cero de nivel 2**.
`cache_line_size = 64` en las dieciseis, como ya era sabido.

`type` se decodifica con `kfd_crat.c:1208-1214` sobre `include/linux/hsa.h`: `type 9 =
DATA|HSACU`, `type 10 = INSTRUCTION|HSACU`. O sea **12 L1 de datos de 16 KiB y 4 L1 de
instruccion de 32 KiB**.

**REFUTACION DIRECTA de «16 cachés published exigen >= 10 CU».** Los 16 registros de cache se
reparten sobre **8** identificadores de CU. Si el total de CU fuesen 10, algunos identificadores no
tendrian ninguna entrada de cache, y el conjunto de identificadores publicados no habria sido
contiguo con un hueco solo. Lo que hay es un hueco unico y limpio. El umbral de 10 no se
sostiene ni como cota ni como aproxímacion. **Refutador que lo volvería a abrir:** encontrar una
entrada de cache adicional con `processor_id_low` fuera de {…745..748, …750..753}. No existe
en las 16 medidas.

### 3.5 `/sys/kernel/debug/dri/1/` — el PermissionError, y su nivel real

Confirmado, **pero el nivel de la denegacion no es el que se suponia**:

```text
/sys/kernel/debug                          modo=700 owner=root(0) grupo=root(0)   <-- ACCESIBLE al stat
/sys/kernel/debug/dri                      stat: Permission denied
/sys/kernel/debug/dri/1                    stat: Permission denied
/sys/kernel/debug/dri/1/amdgpu_gca_config  stat: Permission denied
```

Con `open()` real: las cuatro rutas dan `PermissionError [Errno 13]`.

Contexto del proceso: `uid=1000(lucas) gid=1000(lucas) grupos=1000,10(wheel),100(users)`,
`CapEff: 0000000000000000` (sin ninguna capability), `CapBnd: 000001ffffffffff`.
`/proc/mounts`: `debugfs /sys/kernel/debug debugfs rw,nosuid,nodev,noexec,relatime`.

**Lo que esto significa, y es una correccion importante.** La denegacion esta **en la raiz de
debugfs, que es modo 0700 root**, no en `dri/1` ni en `amdgpu_gca_config`. Por tanto:

- `amdgpu_gca_config` **no tiene nada de particular**: es tan inaccessible como
  `/sys/kernel/debug/dri`, que no tiene nada que ver con amdgpu.
- **NO_VERIFICABLE**: el modo y el owner de **cada nodo** dentro de `dri/1/`. El encargo pedia
  anotarlos y **no es posible**: el directorio padre no es transitable, asi que ningun `stat`
  sobre un hijo puede completarse. No lo he intentado por otra via, conforme a la instruccion
  de no eludirlo.
- Consecuencia sobre el hallazgo 1053 y sobre `MICROARCH-GFX8.md:411`: la mencion de
  `amdgpu_gca_config` como «la via de una lectura» sigue siendo la via correcta, pero el
  obstacle no es el nodo, es el arbol entero. Afecta igual a `amdgpu_gca_config`,
  `amdgpu_kms_info`, `amdgpu_firmware_info` y a todo lo demas.

## 4. La CONTRADICCION 5-contra-8: resuelta, y no era una contradiccion

### 4.1 De donde sale el 5, exactamente

Cadena completa, con fichero y linea, sin saltos:

```text
ROM (no legible por uid 1000, modo 0600 root)
  tabla maestra ATOMBIOS  ->  GFX_Info
  offset del campo: asHeader(4) + GfxIpMinVer(1) + GfxIpMajVer(1)
                     + max_shader_engines(1) + max_tile_pipes(1) = byte 8
  (estructura: drivers/gpu/drm/amd/include/atombios.h:5647-5658,
   ATOM_GFX_INFO_V2_1, el comentario del cabecera dice "GFX_InfoTable for Polaris10/Polaris11")
        |
        |  amdgpu_atombios.c:731-755  amdgpu_atombios_get_gfx_info()
        |    :746  adev->gfx.config.max_cu_per_sh = gfx_info->info.max_cu_per_sh;
        |  llamado desde gfx_v8_0.c:1683, rama `case CHIP_POLARIS12:` (:1681-1695)
        v
adev->gfx.config.max_cu_per_sh = 5
        |
        |  kfd_crat.c:2292  cu->num_cu_per_array = gfx_info->max_cu_per_sh;
        |    (dentro de `static int kfd_create_vcrat_image_gpu(void *pcrat_image,`,
        |     kfd_crat.c:2234 — lafabrica de CRAT VIRTUAL, no un parser de ACPI)
        |  kfd_crat.c:1042  dev->node_props.cu_per_simd_array = cu->num_cu_per_array;
        v
/sys/class/kfd/kfd/topology/nodes/1/properties : cu_per_simd_array 5      <-- MEDIDO
```

**El 5 es un valor de ASIC**, no una lectura mal interpretada: es el byte 8 de `GFX_Info`, un
campo de geometria nominal. Y para Polaris12 **no existe ninguna constante en el driver** que
pueda sobreescribirlo: `gfx_v8_0_gpu_early_init` (`gfx_v8_0.c:1638-1779`) tiene ramas
hardcodeadas para Topaz (`:1650`, 6 CU), Fiji (`:1667`, 16), Tonga (`:1714`, 8), Carrizo
(`:1733`, 8), Stoney (`:1750`, 3) y un `default` (`:1765`, 2); **Polaris12 esta en `:1681-1695`
y no asigna ninguno de los seis campos**, solo llama a `amdgpu_atombios_get_gfx_info()`.

> **Aviso de trampa para el resto del proyecto:** los `= 8` de `gfx_v8_0.c:1714` y `:1733`
> pertenecen a **Tonga y Carrizo**. Un grep de `max_cu_per_sh = 8` sobre `gfx_v8_0.c` sale un
> 8 que no es de esta placa. Esta es, con alta probabilidad, laprocedencia del «8» con el que
> se planteo la contradiccion.

### 4.2 Y el 5 no es el total de CU: es CU por ranura

`kfd_crat.c:2288-2292`:

```c
cu->array_count     = gfx_info->max_sh_per_se * gfx_info->max_shader_engines;
total_num_of_cu     = (cu->array_count * gfx_info->max_cu_per_sh);
cu->num_cu_per_array = gfx_info->max_cu_per_sh;
```

`array_count` y `cu_per_simd_array` se publican **multiplicados y sin combinar**:
`sysfs` los emite por separado (`kfd_topology.c:461-467`), y `array_count` se emite ya
multiplicado por `NUM_XCC` (`:462-463`). Measured: `array_count = 2`, `cu_per_simd_array = 5`,
producto **10 ranuras de CU**. El hardware no tiene por que poblar las diez.

### 4.3 De donde sale el 8, y por que es una magnitud distinta

El 8 **no viene del mismo sitio que el 5**. Viene de contar CU **activos** leyendo
**registros MMIO**:

```text
gfx_v8_0.c:7060-7070  gfx_v8_0_get_cu_active_bitmap()
    data  = RREG32(mmCC_GC_SHADER_ARRAY_CONFIG) | RREG32(mmGC_USER_SHADER_ARRAY_CONFIG)
    mask  = amdgpu_gfx_create_bitmask(adev->gfx.config.max_cu_per_sh)
    return ~REG_GET_FIELD(data, CC_GC_SHADER_ARRAY_CONFIG, INACTIVE_CUS) & mask

gfx_v8_0.c:7072-7126  gfx_v8_0_get_cu_info()
    memset(cu_info, 0, sizeof(*cu_info));                      (:7080)
    for i < max_shader_engines / j < max_sh_per_se / k < max_cu_per_sh:
        bitmap = gfx_v8_0_get_cu_active_bitmap(adev);         (:7099)
        ... cuenta los bits activos ...
        active_cu_number += counter;                           (:7110)
    cu_info->number = active_cu_number;                        (:7119)
    cu_info->simd_per_cu              = NUM_SIMD_PER_CU;      (:7121)
    cu_info->max_waves_per_simd       = 10;                   (:7122)  <-- CONSTANTE
    cu_info->max_scratch_slots_per_cu = 32;                   (:7123)  <-- CONSTANTE
    cu_info->wave_front_size          = 64;                   (:7124)  <-- CONSTANTE
    cu_info->lds_size                 = 64;                   (:7125)  <-- CONSTANTE
```

El divisor que faltaba en el proyecto, resuelto:

```text
kfd_crat.c:2284   cu->num_simd_cores = cu_info->simd_per_cu * (cu_info->number / kdev->kfd->num_nodes);

kfd_device.c:747  kfd->num_nodes = amdgpu_xcp_get_num_xcp(kfd->adev->xcp_mgr);
```

**`num_nodes` es el numero de particiones XCP, NO el numero de nodos de la topologia KFD.**
Por eso `/sys/class/kfd/kfd/topology/nodes/` tiene 2 entradas (0 = CPU, 1 = GPU) y, sin
embargo, el divisor es **1**. Corroborado por `num_xcc = 1` publicado. De aqui:

```text
simd_count medido = 32 = simd_per_cu(4) * cu_info->number / num_nodes(1)
                        =>  cu_info->number = 8        CU ACTIVAS, PROVEN_DERIVED
```

Y el segundo esquema independiente, la aritmetica de `cwsr_size`, cuyo productor he localizado
(`kfd_queue.c:480-519`, `kfd_queue_ctx_save_restore_size()` — no lo habia citado ningun
documento del proyecto):

```text
kfd_queue.c:492   cu_num = props->simd_count / props->simd_per_cu / NUM_XCC(xcc_mask)  = 32/4/1 = 8
kfd_queue.c:454-469 get_num_waves()  wave_num = min(cu_num*40, array_count/simd_arrays_per_engine*512)
                                    para cu_num=8  -> min(320, 2/1*512=1024) = 320
kfd_queue.c:401-452 por CU, para gfxv = gfx_target_version = 80003:
    kfd_get_vgpr_size_per_cu = 0x40000 = 262144     (:414)
    kfd_get_sgpr_size_per_cu = 0x4000  =  16384     (:403)
    kfd_get_lds_size_per_cu  = 0x10000 =  65536     (:446)
    kfd_get_hwreg_size_per_cu= 0x1000  =   4096     (:436)
    WG_CONTEXT_DATA_SIZE_PER_CU                = 348160   (:471-473)
kfd_queue.c:495  wg_data_size  = ALIGN(8 * 348160, 4096)          = 2785280
kfd_queue.c:497-499 ctl_stack  = 320*8 + 8 = 2568; ALIGN(40+2568, 4096) = 4096
kfd_queue.c:511  cwsr_size    = ALIGN(4096 + 2785280, 4096)        = 2789376
```

```text
MEDIDO                       ctl_stack_size = 4096      cwsr_size = 2789376   <- IDENTICOS
CONTRASTE con cu_num = 10    ctl_stack_size = 4096      cwsr_size = 3485696   <- NO coincide
```

`ctl_stack_size` **no discrimina** (sale 4096 en ambos casos, porque el `ALIGN` a pagina se
traga la diferencia). `cwsr_size` **si discrimina, y de forma unica**. Nota: el criterio de
refutacion que el propio proyecto escribio en `CONSTANTES-GFX8-DRIVER.md:836` («o `cwsr_size !=
2789376`») queda **disparado como no-refutador**: la aritmetica produce exactamente 2789376
con `cu_num = 8`.

### 4.4 La premisa del proyecto que es incorrecta

> «los tres vienen del MISMO registro de firmware CRAT»

**REFUTADO.** Los tres numeros vienen de **tres producers distintos**:

| numero | producer | origen fisico | necesita ROM |
|---|---|---|---|
| `cu_per_simd_array = 5` | `kfd_crat.c:2292` <- `amdgpu_atombios.c:746` | tabla maestra `GFX_Info` del ATOMBIOS | **si** |
| `cu_info->number = 8` | `gfx_v8_0.c:7119` <- `RREG32` de `mmCC_GC_SHADER_ARRAY_CONFIG` | **registros MMIO de la GPU** | **no** |
| `cwsr_size = 2789376` | `kfd_queue.c:511`, derivado del anterior | derivado, sin lectura propia | **no** |

Y hay un cuarto hecho que reencuadra todo: **`PROVEN_ABSENT` la CRAT de ACPI.**

```text
/sys/firmware/acpi/tables/     contiene APIC DBGP DMAR DSDT FACP FACS FIDT FPDT HPET
                               MCFG SSDT1..SSDT5
/sys/firmware/acpi/tables/CRAT NO EXISTE   (ls: no se puede acceder: No existe el fichero)
```

Por tanto la CRAT que KFD publica en `nodes/1/` **no viene de ACPI**: la fabrica
`kfd_create_vcrat_image_gpu()` (`kfd_crat.c:2234`) la sintetiza en memoria a partir de
`adev->gfx.cu_info` y `adev->gfx.config`. Eso explica por que `cu_per_simd_array` sale
literalmente de `max_cu_per_sh`: **no es una transcripcion de firmware, es una copia del
mismo campo en memoria que el debugger de amdgpu**, y por eso es la tercera via que
`CONSTANTES-GFX8-DRIVER.md:482-483` daba por pendiente. Ya no hay que esperar a
`amdgpu_gca_config` para confirmar `max_cu_per_sh = 5`: esta medido.

### 4.5 La geometria completa, reconstruida y verificada campo a campo

`kfd_crat.c:1613-1616` selecciona, para `CHIP_POLARIS12`, la tabla `polaris12_cache_info`, que
en `kfd_crat.c:130` es un alias: `#define polaris12_cache_info carrizo_cache_info`. La tabla
`carrizo_cache_info` (`kfd_crat.c:90-123`) tiene **tres** entradas y ningun campo de firmware:

| # | `cache_size` KiB | `cache_level` | `cache_line_size` | banderas | `num_cu_shared` |
|---|---|---|---|---|---|
| 0 | 16 | 1 | 64 | `DATA \| HSACU` | **1** |
| 1 | 32 | 1 | 64 | `INST \| HSACU` | **4** |
| 2 | 16 | 1 | 64 | `DATA \| HSACU` | **4** |

y el comentario literal en `kfd_crat.c:122` es `/* TODO: Add L2 Cache information */`. De ahi
el **cero de caches de nivel 2** medido: no es un misterio del silicio, es que la tabla de
referencia no tiene entrada de L2.

Simulando `kfd_topology.c:1818-1863` con estos numeros y con las 16 entradas medidas, el
**barrido exhaustivo del espacio de hipotesis** (`array_count = SE*SH = 2`, medido) da:

```text
TODAS las hipotesis que reproducen EXACTAMENTE las 16 entradas medidas:

  SE  SH  max_cu_per_sh  bitmap por (SE,SH)   CU activas totales
   2   1         5            0b11110                 8
   1   2         5            0b11110                 8
  (ninguna otra combinacion de SE, SH, max_cu_per_sh y bitmap de 0 a 5 CU por ranura)
```

Lo que queda **unicamente determinado por esta via**, y lo que **no**:

```text
UNICO Y MEDIDO
  max_cu_per_sh            = 5
  bitmap de CU por (SE,SH) = 0b11110   -> ranura 0 INACTIVA, ranuras 1,2,3,4 ACTIVAS
  CU activas totales       = 8
  ranuras de CU totales    = array_count * max_cu_per_sh = 10   (2 vacias)

PRODUCTO, NO FACTORIZACION
  max_shader_engines * max_sh_per_se = 2
  (SE=2,SH=1) y (SE=1,SH=2) son INDISTINGUIBLES con este dato: el bucle de
  kfd_topology.c:1824-1848 recorre (i,j) en el mismo orden y acumula cu_processor_id
  igual en ambos casos. NO AFIRMO cual de los dos es. -> NOT_DETERMINED por esta via.
```

### 4.6 La IP discovery NO corre en Polaris12 (por que el 5 no lo pisa nadie)

`amdgpu_discovery.c:493-521`, `amdgpu_discovery_get_fw_name()`: el `switch (adev->asic_type)`
cubre `CHIP_VEGA10`, `CHIP_VEGA12`, `CHIP_RAVEN`, `CHIP_VEGA20`, `CHIP_ARCTURUS`,
`CHIP_ALDEBARAN`, y **`default: return NULL;`**. `CHIP_POLARIS12` no esta. Por tanto
`amdgpu_discovery_init()` no carga blob, y **las lineas `amdgpu_discovery.c:1745` y `:1790` —
que asignan `max_cu_per_sh` desde `GC_INFO` — no se ejecutan para esta ASIC**.

Corroboracion independiente del estado de la placa:

```text
/usr/lib/firmware/amdgpu/  contiene 677 ficheros
  *_ip_discovery.bin.xz presentes: aldebaran, arcturus, picasso, raven, vega10, vega12, ...
  polaris*_ip_discovery.bin     : NINGUNO
```

De aqui se sigue, con dossupportes independientes (el `switch` y el directorio de firmware):

- `adev->gfx.config.max_cu_per_sh` viene **exclusivamente** de `amdgpu_atombios_get_gfx_info()`,
  es decir **solo de la ROM**, para Polaris12.
- Los campos `gc_tcp_l1_size`, `gc_l1_instruction_cache_size_per_sqc`,
  `gc_l1_data_cache_size_per_sqc`, `gc_gl1c_per_sa`, `gc_gl2c_per_gpu` **siguen valiendo 0**
  en esta ASIC, porque solo los rellena la IP discovery. Por eso
  `kfd_fill_gpu_cache_info_from_gfx_config()` no contributes nada y manda la tabla constante
  `carrizo_cache_info`.
- **`MEMORIA-GFX8.md:111` queda INVALIDADO en su premisa**: cita
  `amdgpu_discovery.c:1767-1786` como la fuente de firmware de estos campos en runtime. Ese
  camino **no se ejecuta en Polaris12**.

### 4.7 Que numero de los tres se puede medir sin la ROM — respuesta directa

```text
SE PUEDE MEDIR SIN LA ROM, sin root, y ya esta medido:

  CU activas = 8
      via 1:  simd_count(32) / simd_per_cu(4) / num_xCC(1)          [kfd_queue.c:492]
      via 2:  aritmetica exacta de cwsr_size = 2789376             [kfd_queue.c:511]
      via 3:  8 processor_id_low distintos entre las 16 caches      [medido]
      via 4:  simulacion de los 16 registros de cache campo a campo [kfd_crat.c:90-123]

  CU por ranura (max_cu_per_sh) = 5
      via unica:  cu_per_simd_array = 5                             [kfd_crat.c:2292]
      Y ESTA MEDIDO. Es el unico de los tres que en realidad no necesita
      la ROM para CONOCERSE, porque KFD lo republica.

  ranuras de CU totales = 10
      producto de los dos anteriores, ambos medidos.

LO QUE NO SE PUEDE MEDIR SIN LA ROM (NO_VERIFICABLE, no NOT_DETERMINED):

  max_tile_pipes, max_backends_per_se, max_texture_channel_caches,
  y el resto de los seis campos de ATOM_GFX_INFO_V2_1
      -> Ninguno se republica en sysfs, ni en debugfs de forma accesible,
         ni en KFD. La unica via es la ROM, o amdgpu_gca_config (root).
  cwsr_size por separado de cu_num: no es una entrada independiente, es una
      FUNCION de cu_num, asi que no aporta un cuarto numero.
```

**En sintesis: de los tres numeros, los que se pueden medir aqui son el 5 y el 8, y ambos
estan medidos. El 8 es el que responds a la pregunta util («cuantas CU tiene esta placa que
ejecutan»), y se lee desde sysfs sin ningun privilegio especial.**

## 5. El origen de `xxx-xxx-xxx`, y las tres ramas que el proyecto no distinguia

### 5.1 El mecanismo exacto: el atributo no imprime lo que su nombre dice

```text
amdgpu_atombios.c:1807-1816
    static ssize_t amdgpu_atombios_get_vbios_version(...)
    {
        ...
        struct atom_context *ctx = adev->mode_info.atom_context;
        return sysfs_emit(buf, "%s\n", ctx->vbios_pn);        <-- :1815
    }

amdgpu_atombios.c:1829-1831   DEVICE_ATTR(vbios_version, 0444, ..._get_vbios_version, NULL)
                               DEVICE_ATTR(vbios_build,   0444, ..._get_vbios_build,   NULL)

amdgpu_atombios.c:1837-1850   amdgpu_vbios_version_attrs_is_visible()
        if (attr == &dev_attr_vbios_build.attr && !strlen(ctx->build_num))
                return 0;                                     <-- :1846-1847
        return attr->mode;

amdgpu_atombios.c:1857-1864   amdgpu_atombios_sysfs_init()
        if (adev->mode_info.atom_context)                     <-- :1859
                return devm_device_add_group(..., &amdgpu_vbios_version_attr_group);
        return 0;
```

**`vbios_version` imprime `ctx->vbios_pn`, que es el numero de parte. El campo de version
autentico es `ctx->vbios_ver_str`, y `vbios_version` NO lo imprime.** Recuento completo de
las dos variables en todo el corpus:

```text
ctx->vbios_pn       (atom.h:151, uint8_t[STRLEN_LONG]=64)   UNICO escritor: atom.c:1459
    amdgpu_atombios.c:1815   sysfs  "vbios_version"    <-- LO QUE ESTAMOS VIENDO
    amdgpu_kms.c:1123        memcpy a vbios_info
    amdgpu_kms.c:1983        DRM debugfs, rotulado "VBIOS version: %s"   <-- mismo error
    atom.c:1526-1528         atom_print_vbios_info
    amdgpu_dev_coredump.c:201   "vbios pn"
    amdgpu_ras.c:4046-4049 / amdgpu_ras_eeprom.c:204-223 / amdgpu_fru_eeprom.c:67-99
                               COINCIDENCIAS por subcadena: "D161","D163","D603","D603GLXE",
                               "D673","D707","D16406","D36002"

ctx->vbios_ver_str  (atom.h:153, uint8_t[STRLEN_NORMAL]=32)  UNICO escritor: atom.c:1493
    atom.c:1493/1495          escritura
    atom.c:1533-1536          atom_print_vbios_info (solo a dmesg)
    amdgpu_kms.c:1126-1127    memcpy a vbios_info
    amdgpu_dev_coredump.c:203  "vbios ver_str"
    ***NINGUNA APARICION EN NINGUN ATRIBUTO DE SYSFS***
```

**`vbios_ver_str` no se publica por sysfs en ningun caso, ni siquiera cuando esta relleno.**
Consecuencia directa: **la afirmacion del hallazgo 1053 de que el atributo se llama
`vbios_version` y por tanto muestra la version es incorrecta**, aunque su conclusion de que la
cadena procede de la ROM siga siendo correcta. Y `amdgpu_kms.c:1983` arrastra el mismo error de
rotulo en el debugfs de DRM, de modo que leerlo no arregla nada.

### 5.2 De donde sale `xxx-xxx-xxx` literalmente

```text
atom.c:1427-1465   atom_get_vbios_pn()
    off_to_vbios_str = 0
    p_rom = ctx->bios
    if (*(p_rom + 0x2f) != 0)                                  /* NUMBER_OF_STRINGS */
            off_to_vbios_str = *(u16 *)(p_rom + 0x6e);          /* STRING_START        */
            vbios_str = p_rom + off_to_vbios_str;
    else
            vbios_str = p_rom + 0x80;                          /* VBIOS_PART_NUMBER   */
    if (*vbios_str == 0)
            vbios_str = atom_find_str_in_rom(ctx, "ATOMBIOS", 3, 1024, 64);   /* :1447 */
    ...
    while (count < 64 && vbios_str[count] >= ' ' && vbios_str[count] <= 'z')  /* :1457 */
            ctx->vbios_pn[count++] = vbios_str[count];                         /* :1459 */
    ctx->vbios_pn[count] = 0;
```

`ctx->vbios_pn` se inicializa a cero por `kzalloc` y **solo se escribe aqui**, leyendo
`ctx->bios`. Por tanto los bytes ASCII `xxx-xxx-xxx` **estan en el buffer de ROM que el driver
tiene en memoria** (`adev->bios`). Eso queda `PROVEN` por el recuento de escritores: no hay
otra ruta de escritura en los 2705 ficheros del corpus.

Cual de las dos ramas se tomo (`0x2f != 0` leyendo el offset de `0x6e`, o el fijo `0x80`, o
la busqueda de `"ATOMBIOS"` entre 3 y 1024) es **`NO_VERIFICABLE`** sin la ROM. No lo afirmo.

### 5.3 Las tres ramas, discriminadas una por una

El encargo pedia separar tres hechos distintos que el proyecto tiene apuntando al mismo sitio.
Se pueden separar, y con el codigo disponible:

```text
RAMO A — EL ATOMBIOS ESTA AUSENTE
  ESTADO: REFUTADO
  POR QUE: amdgpu_atombios_sysfs_init() (amdgpu_atombios.c:1859) solo anade el grupo de
  atributos SI adev->mode_info.atom_context != NULL. Y adev->mode_info.atom_context se asigna
  en amdgpu_atombios.c:1914 con el resultado de amdgpu_atom_parse(); si fuese NULL, la linea
  :1916 llama amdgpu_atombios_fini() y devuelve -ENOMEM, y el grupo NUNCA se crearia.
  MEDIDO: /sys/class/drm/card1/device/ CONTIENE vbios_version y vbios_build.
          Su existencia prueba adev->mode_info.atom_context != NULL.
  ademas: node name = polaris12 (kfd nodes/1) prueba que asic_type = CHIP_POLARIS12, cuya
  rama de gfx_v8_0_gpu_early_init (:1681) LLAMA a amdgpu_atombios_get_gfx_info(); si el
  ATOMBIOS estuviese ausente, :1684-1685 abortaria el arranque de la GPU y no tendriamos GPU.

RAMO B — EL ATOMBIOS ESTA SIN PARSEAR
  ESTADO: REFUTADO
  POR QUE: (1) el mismo argumento de arriba — atom_context != NULL solo si el parseo devolvio
  contexto. (2) amdgpu_atom_parse llama, en su camino de exito (atom.c:1601-1605),
  atom_get_vbios_pn, _date, _version y _build; si no se hubieran ejecutado, no habria ni
  vbios_pn ni build_num.
  MEDIDO ADEMAS: vbios_build = "565939  " (CON ESPACIOS FINALES, no vacio). El atributo
  vbios_build esta OCULTO cuando build_num esta vacio (amdgpu_atombios.c:1846-1847). Que
  exista en el arbol prueba que build_num es NO VACIO. Y atom_get_vbios_build (atom.c:1499-1519)
  solo produce un string no vacio tras recorrer, con comprobacion de limites
  `str < atom_rom_hdr` en :1510 y :1513, la cadena de configuracion y luego la de change-list
  a partir de ATOM_ROM_TABLE_PTR -> ATOM_ROM_CFG_PTR. Eso es un recorrido CORRECTO de la
  cabecera del ROM. Un ROM no parseable no llega aqui.
  "565939" es la tercera cadena del bloque (la de change-list), leida con limites correctos.

RAMO C — PRESENTE CON EL CAMPO DE VERSION SIN RELLENAR
  ESTADO: REFUTADO **COMO ESTADO DE LA RAMA**, y REEMPLAZADO por el hecho correcto:
          la rama C no es un estado distinguible, porque el campo que se publica NO es
          el campo de version.
  HECHOS: (a) el ATOMBIOS esta PRESENTE y PARSADO (ramo A y ramo B). (b) Lo que se
  publica es ctx->vbios_pn, el numero de parte, cuyo valor en esta placa es la cadena
  literal "xxx-xxx-xxx". (c) El valor de ctx->vbios_ver_str — el campo de version de verdad,
  que se extrae buscando "ATOMBIOSBK-AMD" (atom.c:1488-1496) y se deja a '' si no se
  encuentra — es NO_VERIFICABLE: no se publica por sysfs en ningun caso (§5.1), y el
  unico sitio de runtime donde se imprime es atom_print_vbios_info() (atom.c:1521-1540),
  que escribe a dmesg, y dmesg es NO_VERIFICABLE para uid 1000 en esta host.
```

**Redaccion correcta del hecho, en una linea:** el ATOMBIOS de esta tarjeta esta presente y
ha sido parseado por el driver —prueba: los dos atributos de sus cadenas existen y
`vbios_build` esta relleno— y el identificador de numero de parte que publica
`/sys/class/drm/card1/device/vbios_version` contiene la cadena literal `xxx-xxx-xxx`; el
campo de version autentico del ATOMBIOS no se publica por sysfs y su valor no es observable
sin dmesg.

### 5.4 Consecuencia colateral medible del valor `xxx-xxx-xxx`

Las nueve rutas de `vbios_pn` del corpus hacen **coincidencia por subcadena** contra
identificadores de placa de AMD: `D161`, `D163`, `D603`, `D603GLXE`, `D673`, `D707`, `D16406`,
`D36002` (`amdgpu_ras.c:4046-4049`, `amdgpu_ras_eeprom.c:204-223`,
`amdgpu_fru_eeprom.c:67-99`). Una cadena `"xxx-xxx-xxx"` **no puede coincidir con ninguna**.
Por tanto, en esta placa, esas nueve ramas caen todas por la via negativa.

Esto **no** es una hipotesis: es una consecuencia de la comparacion de cadenas, y es
`PROVEN_DERIVED` dado el valor medido. No se ha ejecutado ningun codigo de esas ramas ni se ha
observado su comportamiento en runtime, asi que **no afirmo** que el RAS se degrade; afirmo que
la condicion de entrada no puede cumplirse. `board_info` si devuelve `type : cem`, pero eso
viene del EEPROM FRU, no de `vbios_pn`.

## 6. MITA B — inventario y documentos desactualizados

### 6.1 Correccion al hallazgo 1053 (el alcance de su busqueda)

1053 afirma: *«medido sobre los **304 ficheros `.c`/`.h`/`.rs`** de `linux-7.1.3`: **0
ocurrencias de `xxx-xxx-xxx`**»*.

```text
MEDIDO POR MI, en el mismo arbol:
  .c    984
  .h   1721
  .rs     0        <-- NO HAY NI UN SOLO .rs EN linux-7.1.3
  TOTAL 2705       <-- no 304
```

**La poblacion declarada en 1053 (304) no corresponde a este arbol (2705).** La CONCLUSION
(0 ocurrencias) la he **reproducido yo sobre los 2705 ficheros, sin excepcion**: sigue siendo
0. Pero la poblacion medida era incorrecta, y por el principio del AGENTS.md §16 (`READ SCOPE
GATE`) un `NOT_FOUND` declarado sobre 304 ficheros cuando hay 2705 es un `NOT_FOUND` con alcance
insuficiente. Este turno lo cierra con el alcance correcto.

### 6.2 Existe un inventario consolidado del ASIC? — `PROVEN_ABSENT`

```text
BUSQUEDA: 08-ARQUITECTURA/*.md y subdirectorios, y los .md de la raiz del proyecto.
  "INVENTARIO" / "inventario del ASIC" / "RESUMEN DEL ASIC" / "TABLA DE GEOMETR"
    -> 0 coincidencias.
  26 documentos de 08-ARQUITECTURA/ mencionan 699f / POLARIS12 / polaris12.
  NO hay ninguna tabla que reuna "todo lo que se sabe de esta ASIC" en un sitio.
```

**El proyecto no tiene la lista que el encargo da por hecha.** La geometria esta repartida y
en parte contradicha entre `KFD-TOPOLOGIA.md` (que la tiene y laaclara) y
`CONSTANTES-GFX8-DRIVER.md` (que la declara `CONFLICTADO` y no reconciliada). Esa
desincronizacion interna **es** el problema, y es lo que este turno mide.

### 6.3 Lo que ya estaba hecho — declaracion de no-novedad

**Debo decirlo con claridad: `KFD-TOPOLOGIA.md` ya habia resuelto la contradiccion 5-contra-8
antes de este turno.** Su §2 titula literalmente «CONTRADICCIÓN (2) — `cu_per_simd_array = 5`
contra `32/4 = 8`», su §2.3 dice *«Y `array_count = 2` no contradice nada. `LEIDO_EN_CORPUS`»*,
su §5 es *«Verificación independiente: la simulación reproduce los 16 cachés»*, y su linea 784
registra como **`PROVEN`** que *«`cu_per_simd_array`=5 es `max_cu_per_sh` (capacidad); 8 es
`cu_info->number` (CU activas)»*. Este turno **no** descubre eso. Lo que anade es:

1. **`num_nodes` resuelto.** `KFD-TOPOLOGIA.md:311` deja el divisor simbolico
   (`number/num_nodes = 8`). `kfd_device.c:747` demuestra que `num_nodes` es
   `amdgpu_xcp_get_num_xcp()` = 1, luego **`cu_info->number = 8` directamente**, no el cociente.
2. **`cwsr_size` con productor y aritmetica completa.** `KFD-TOPOLOGIA.md:739` registra el
   valor medido pero ningun documento cita `kfd_queue.c:480-519`. Este turno lo localiza y
   comprueba que `cwsr_size` **discrimina** 8 frente a 10 de forma unica.
3. **El bitmap de CU al nivel del bit.** `KFD-TOPOLOGIA.md:789` dice «4 activas por SH x 2 SH =
   8 CU», `CORROBORATED`. Este turno lo convierte en `0b11110` exacto (ranura 0 inactiva,
   ranuras 1-4 activas) y verifica el multiconjunto completo de las 16 entradas por
   `processor_id_low`, `size` y `sibling_map`.
4. **`PROVEN_ABSENT` la CRAT de ACPI**, y por tanto el caracter **VCRAT sintetizada** del
   reparto. `KFD-TOPOLOGIA.md` cita `kfd_crat.c:2288` pero no establece que no hay CRAT de ACPI,
   que es lo que convierte esa linea en una copia y no en una transcripcion de firmware.
5. **`PROVEN_ABSENT` la IP discovery en Polaris12**, y por tanto que `max_cu_per_sh` no lo pisa
   nadie mas que la ROM, y que los campos `gc_*` de cache siguen a cero.

### 6.4 Documentos que quedan DESACTUALIZADOS, con fichero:linea

No los he editado, conforme a la instruccion. Solo los nombro con la linea exacta.

**A. `08-ARQUITECTURA/CONSTANTES-GFX8-DRIVER.md` — el mas desactualizado, contradice al tree**

| linea | contenido actual | por que queda desactualizado |
|---|---|---|
| `:128` | `cu_per_simd_array` = 5 marcado **`CONFLICTADO`** | es `PROVEN_DERIVED` (medido y con productor, §4.1) |
| `:385` | `B) CU = array_count * cu_per_simd_array = 2 * 5 = 10` | 10 son **ranuras**, no CU. Hay **8 CU activas** |
| `:422` | comentario `dev->node_props.cu_per_simd_array);  /* = 10 */` | idem |
| `:482-483` | *«Refutador de este §4: una lectura de `amdgpu_gca_config` … que diga `max_cu_per_sh = 5`»* | **ese refutador ya se ha disparado sin root**, via `cu_per_simd_array` (`kfd_crat.c:2292`) |
| `:783` | *«CONFLICTADO `cu_per_simd_array = 5` frente a `simd_count/simd_per_cu = 8`. **NO reconcilian**»* | **SI reconcilian**: capacidad por ranura frente a CU activas (§4) |
| `:836` | criterio de refutacion de «8 CU»: *«o `cwsr_size != 2789376`»* | comprobado: la aritmetica da 2789376 con `cu_num = 8`. **No refutado** |

**B. `08-ARQUITECTURA/MICROARCH-GFX8.md`**

| linea | contenido actual | por que queda desactualizado |
|---|---|---|
| `:257` | *«nº de CU de esta placa — `NOT_FOUND`»* | **8 CU activas, medidas por 3 vias** (§4.3-4.5) |
| `:258` | *«CU por SH / SH por SE / nº de SE — `NOT_FOUND` (idem)»* | **CU por ranura = 5, medido**; `SE*SH = 2` medido; la factorizacion queda `NOT_DETERMINED` |
| `:349` | *«Nº de CU, CU/SH, SH/SE, nº de SE. Vienen del VBIOS, no del driver»* | a medias: CU/SH viene del VBIOS **y se mide por KFD**; el nº de CU **no** viene del VBIOS, sale de registros MMIO (`gfx_v8_0.c:7119`) |
| `:497` | *«NOT_FOUND nº de CU / CU-por-SH / SH-por-SE / nº de SE (vienen del VBIOS, `amdgpu_atombios.c:744-750`)»* | idem `:257`/`:258` |
| `:521` | *«nº de CU de esta placa \| VBIOS, o `amdgpu_gca_config` \| una lectura»* | **ya esta medido sin ninguna de las dos**; la accion proposed esta cumplida |
| `:411` | `amdgpu_gca_config` como «la via de una lectura» | el nodo es correcto pero el obstaculo es **la raiz de debugfs en modo 0700**, no el nodo (§3.5) |

Lo que **NO** cambia en este documento: `:259` (*«tamaño de un slot de scratch —
`NOT_FOUND`»*). `max_scratch_slots_per_cu = 32` sigue siendo un recuento
(`gfx_v8_0.c:7123`) y mi medicion no aporta el tamano en bytes. Sigue `NOT_FOUND`, y con el
alcance que el documento ya declara.

**C. `08-ARQUITECTURA/CU-OCCUPANCY-WIRING.md`**

| linea | contenido actual | por que queda desactualizado |
|---|---|---|
| `:31` | *«geometría 4x8» → `NOT_FOUND` / `NOT_TRACED`* | la geometria 4x8 es ahora **`PROVEN_DERIVED` y verificada campo a campo** |
| `:421` | *«¿cuántos motores de micro-engine (ME), SH y CU hay realmente? \| Del VBIOS … `NOT_FOUND` en el corpus»* | CU: 8 activas / 10 ranuras, medidas. **ME: sigue `NOT_FOUND`**, no lo toco |
| `:484` | *«geometría 4×8» `NOT_FOUND` / `NOT_TRAZADA`: sale del VBIOS* | igual que `:31`; y **no sale del VBIOS**: sale de registros MMIO |
| `:528` | *«Geometría de la placa: `NOT_FOUND` en el corpus. Relleno desde VBIOS.»* | desactualizado; y «relleno desde VBIOS» es innecesario para CU |

**D. `08-ARQUITECTURA/MEMORIA-GFX8.md`**

| linea | contenido actual | por que queda desactualizado |
|---|---|---|
| `:111` | *«**firmware**, leída en `amdgpu/amdgpu_discovery.c:1767-1786`»* | **esa ruta no se ejecuta en Polaris12** (§4.6): no hay IP discovery |
| `:129` | *«POLARIS12: `NOT_DETERMINED`. No se pueden derivar del código fuente; vienen del blob de firmware»* | para las **tres caches que sí se publican**, sus parametros **son** constantes de compilacion (`carrizo_cache_info`, `kfd_crat.c:90-123`, `:130`). Internamente inconsistente con `:144-158` del mismo documento, que ya lo dice bien. **La inconsistencia es dentro del propio fichero** |
| `:169` | *«`DEPENDENCY_UNSATISFIED` cuya unica fuente es el firmware en runtime»* (sobre L2) | **parcialmente**: sigue faltando el tamano real de L2/TCC, pero la ausencia de L2 publicada ya tiene explicacion (`/* TODO: Add L2 Cache information */`, `kfd_crat.c:122`), no «fuente que falta» |

Lo que **NO** cambia: la afirmacion de que **el tamano de la L2 de esta tarjeta no se puede
derivar** sigue siendo correcta. `gc_gl2c_per_gpu` requiere IP discovery (§4.6), asi que
continua `NOT_DETERMINED`. Este turno no la mejora.

**E. `08-ARQUITECTURA/KFD-TOPOLOGIA.md`** — el unico que esta mayoritariamente al dia.
Anadir, no corregir: `num_nodes = 1` por `kfd_device.c:747`; productor y aritmetica de
`cwsr_size`; `PROVEN_ABSENT` de la CRAT de ACPI; bitmap `0b11110`; y una advertencia que el
documento necesita: **`kfd_create_vcrat_image_gpu` no es un parser de ACPI**, es una fabrica,
y por eso `cu_per_simd_array` sale identico a `max_cu_per_sh` por copia, no por transcripcion.

## 7. Clasificacion final de cada afirmacion de este turno

| afirmacion | estado | refutador que la echaria abajo |
|---|---|---|
| `max_cu_per_sh = 5` | **`PROVEN_DERIVED`** | un `cu_per_simd_array` distinto del 5, o un `max_cu_per_sh`≠5 en `amdgpu_gca_config` |
| CU activas = 8 | **`PROVEN_DERIVED`** | `cwsr_size`≠2789376, o `simd_count`≠32, o un `processor_id_low` fuera de {745-748,750-753} |
| bitmap por ranura = `0b11110` | **`PROVEN_DERIVED`** | un `sibling_map` distinto de `{1,0,0,0}` / `{1,1,1,0}` en las 16 entradas |
| `max_shader_engines * max_sh_per_se = 2` | **`PROVEN_DERIVED`** | un `array_count`≠2 |
| factorizacion (SE,SH) | **`NOT_DETERMINED`** | un campo de topologia que separe SH de SE; ninguna entrada de cache lo hace |
| `cu_info->number` se cuenta en registros MMIO | **`PROVEN`** (estatico, `gfx_v8_0.c:7119`) | que `gfx_v8_0_get_cu_info` no se llame para CHIP_POLARIS12; solo se llama desde la misma tabla ip que asigna los 4 campos hardcodeados, asi que un `lds_size`=64 distinto lo refutaria |
| `max_cu_per_sh` viene **solo** de la ROM en Polaris12 | **`PROVEN`** (dos soportes: `amdgpu_discovery.c:501-521` y ausencia de `polaris*_ip_discovery.bin`) | un `max_cu_per_sh`≠5 en `amdgpu_gca_config` |
| no hay CRAT de ACPI | **`PROVEN_ABSENT`** (poblacion enumerada: las 13 tablas de `/sys/firmware/acpi/tables/`) | que aparezca `CRAT` en ese directorio |
| la CRAT publicada es VCRAT sintetizada | **`PROVEN_DERIVED`** | una CRAT de ACPI presente, que es justo el refutador anterior |
| `vbios_version` imprime `vbios_pn` | **`PROVEN`** (`amdgpu_atombios.c:1815`, unico escritor en `atom.c:1459`) | que `sysfs_emit` imprimiese `vbios_ver_str`; el codigo dice lo contrario |
| el ATOMBIOS esta presente y parseado | **`PROVEN_DERIVED`** | que `vbios_build` estuviese ausente del arbol (`is_visible`, `:1846-1847`), o que `vbios_build` saliese vacio |
| `xxx-xxx-xxx` procede de bytes de la ROM | **`PROVEN`** (unico escritor de `vbios_pn`) | un segundo escritor de `ctx->vbios_pn`; el recuento sobre 2705 ficheros da uno |
| `ctx->vbios_ver_str` no se publica por sysfs | **`PROVEN_ABSENT`** en los sysfs de este arbol | un atributo de sysfs que lo imprima; el recuento de sus 5 apariciones no da ninguno |
| valor de `ctx->vbios_ver_str` | **`NO_VERIFICABLE`** | acceso a `dmesg`, que uid 1000 no tiene |
| nueve coincidencias de `vbios_pn` no pueden dispararse | **`PROVEN_DERIVED`** | una de las subcadenasBUSCAR apareciendo dentro de `xxx-xxx-xxx` |
| causa del `EBUSY` de los 9 atributos `pp_*` | **`NOT_FOUND`** | `amdgpu_pm.c` ausente del corpus (§1). **NO** afirmo que no exista en el kernel |
| modo y owner de cada nodo de `dri/1/` | **`NO_VERIFICABLE`** | no hay via sin eludir: el padre es 0700 root |
| `gartsize`, `gttsize`, `vramlimit`, `moverate`, `ignore_min_pcap` | **`NO_VERIFICABLE`** | modo `rw-------` root |
| `pp_table` | **`NO_VERIFICABLE` por decision propia** | `amdgpu_pm.c` ausente ⇒ no puedo probar que su lectura no reanude la GPU |

## 8. Lo que este turno NO ha hecho

```text
NO ha leido la ROM.           PermissionError medido en el turno 1053, no repetido aqui.
NO ha abierto /dev/dri/*, /dev/kfd, ni ha hecho ioctl.
NO ha escrito en el hardware. Ni un solo registro, ni un solo fichero de sysfs escribible.
NO ha reanudado la GPU.       runtime_active_time = 278853 antes y despues.
NO ha hechecho commit.
NO ha editado ningun documento existente, ni 04-IMPLEMENTACION/rx550-driver/, ni tools/,
   ni revkit/, ni docs/, ni findings/.
NO ha modificado power/control ni nada escribible.
NO ha usado sudo ni root.     CapEff = 0.
NO ha eludido debugfs.        El intento fue un `stat`/`open` de solo lectura, con excepcion
                              registrada, y se abandono ahi.
```

**Observacion concurrente, registrada por honestidad, no es parte de mi trabajo.** Durante
este turno, `git status` muestra modificados artefactos de compilacion de
`04-IMPLEMENTACION/rx550-driver/` (`rx550_drv.ko`, `Module.symvers`, varios `.o` y `.o.cmd`).
**Yo no he ejecutado ningun compilador, ni `make`, ni `gcc`**; las unicas herramientas que he
ejecutado han sido `grep`, `sed -n`, `cat`, `ls`, `stat`, `find`, `md5sum`, `wc`, `python3`
(puramente aritmetico, sin escritura) y las herramientas de escritura sobre **este unico
fichero**. Esos artefactos los produce otro proceso. Lo dejo anotado porque
`AGENTS.md` §88 fija `PROJECT_ACTIVE_AGENT <= 1` para el nodo tecnico principal, y porque un
cambio en el arbol del driver durante mi turno es exactamente el tipo de cosa que un informe
debe declarar en vez de tragarse. **No lo he tocado ni lo he investigated: no es mi
alcance.**

## 9. Fichero creado

```text
08-ARQUITECTURA/GEOMETRIA-SEGUNDA-FUENTE.md      (este fichero, unico creado)
```

## 10. Consecuencia para la peticion de root del hallazgo 1053

1053 colocaba `cat .../rom` como «la peticion de autorizacion mas barata». Este turno **no
cambia esa peticion** —la ROM sigue siendo la unica via para `max_tile_pipes`,
`max_backends_per_se` y `max_texture_channel_caches`— pero **le quita la mayor parte del
motivo**:

```text
LO QUE YA NO NECESITA LA ROM  (medido en este turno, sin root)
  nº de CU de la placa .................. 8 activas de 10 ranuras
  CU por ranura (max_cu_per_sh) .......... 5
  bitmap de CU por ranura ................ 0b11110
  SH por SE x SE ......................... producto = 2 (factorizacion no determinada)
  siz de caches L1 publicadas ........... 16 KiB (x12) y 32 KiB (x4), linea 64
  ausencia de L2 publicada ............... explicada por el TODO del kernel, no por un hueco
  cwsr_size, ctl_stack_size ............. deducidos, no medidos
  max_waves_per_simd, lds, wave_front,
  max_slots_scratch_cu .................. constantes de gfx_v8_0.c:7122-7125

LO QUE SIGUE NECESITANDO LA ROM  (NO_VERIFICABLE por cualquier via sin privilegios)
  max_tile_pipes
  max_backends_per_se
  max_texture_channel_caches
  los demas campos de ATOM_GFX_INFO_V2_1
  ctx->vbios_ver_str (el campo de version de verdad)
```

Es decir: **la geometria de CU queda cerrada sin la ROM. La geometria de memoria de
textura, no.** La peticion de root sigue justificada, pero por tres campos y no por «la
geometria».