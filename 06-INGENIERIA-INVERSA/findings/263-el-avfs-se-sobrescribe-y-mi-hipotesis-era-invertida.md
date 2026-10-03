# 263 · El AVFS se sobrescribe: mi hipotesis de 262 estaba invertida

WORK_CLASS=READ_ONLY · WRITE_EXECUTION=NONE · MODIFICATIONS 0

> ## Cambio de estado, y por que importa
>
> `262` dejo el orden de ejecucion como `NOT_DETERMINED`, con la hipotesis de
> que "A corre despues de B y sobrevive" porque A se ejecuta con la RAM del SMC
> parada. **Eso era una inferencia de diseno, no una medida.** Medido: es al
> reves. **B corre despues de A y lo sobrescribe.**

## La cadena, completa y medida

Todo en `drivers/gpu/drm/amd/amdgpu/amdgpu_device.c`, funcion de init:

```
2399   amdgpu_device_ip_hw_init_phase1(adev);
2403   amdgpu_device_fw_loading(adev);      <- A
2407   amdgpu_device_ip_hw_init_phase2(adev);  <- B
```

**Reparto de fases** (`amdgpu_device.c:2121-2131` y `:2151-2160`): phase1 solo
ejecuta COMMON, PSP-en-VF e IH. phase2 ejecuta el `hw_init` de todo bloque que
sea miembro de *hwini* y no sea uno de esos tres.

**Quien es miembro** (`amdgpu_device.c:190-194`):

```c
return (adev->init_lvl->hwini_ip_block_mask & (1U << block)) != 0;
```

**El mask por defecto** (`:161-164` y `:155`):

```
AMDGPU_IP_BLK_MASK_ALL = GENMASK(AMD_IP_BLOCK_TYPE_NUM - 1, 0)
amdgpu_init_default.hwini_ip_block_mask = AMDGPU_IP_BLK_MASK_ALL
```

Todos los bits. El nivel por defecto es el `default:` de
`amdgpu_set_init_level` (`:206-210`), o sea el de un arranque normal. Luego
**powerplay entra en phase2 sin ambigüedad**.

## A y B, ya resueltos

```
A  amdgpu_device_fw_loading                device.c:2172
   -> amdgpu_pm_load_smu_firmware           amdgpu_dpm.c:670
   -> pp_funcs->load_firmware               amdgpu_dpm.c:680
   -> pp_dpm_load_fw                        amd_powerplay.c:308
   -> smumgr_funcs->start_smu               amd_powerplay.c:315
   -> polaris10_start_smu                   polaris10_smumgr.c:292
      (guardado por if (!smu7_is_smc_ram_running && not_vf))
   -> polaris10_avfs_event_mgr              polaris10_smumgr.c:311
   -> polaris10_setup_graphics_level_structure  :182
      escribe dpm_table_start + GraphicsLevel (236)   :149
      escribe dpm_table_start + MemoryLevel   (708)   :157
      con datos de avfs_graphics_level_polaris10[8] (:80) y avfs_memory_level_polaris10 (:93)

B  amdgpu_device_ip_hw_init_phase2 -> powerplay.hw_init = pp_hw_init   amd_powerplay.c:284
   -> pp_hw_init                     amd_powerplay.c:164
   -> hwmgr_hw_init                  amd_powerplay.c:170
   -> hwmgr.c:273  phm_enable_dynamic_state_management
   -> hardwaremanager.c:91-92        hwmgr_func->dynamic_state_management_enable
   -> smu7_enable_dpm_tasks          smu7_hwmgr.c:1566
   -> smum_init_smc_table            smu7_hwmgr.c:1622
   -> polaris10_init_smc_table       polaris10_smumgr.c:2118
      copia (uint8_t *)&(table->SystemFlags), 1776 B  ->  108..1883
```

`2403 < 2407`. **A escribe 236 y 708, y B los pisa 4 lineas mas tarde en el
mismo init.**

## Lo que queda en la RAM del SMC

Lo que queda en `GraphicsLevel` y `MemoryLevel` es **el contenido de la tabla de
host** (`&hw_data->dpm_table`), que viene del **VBIOS**, y **no** las constantes
`avfs_*` que el driver compila a mano.

O sea: **`avfs_graphics_level_polaris10[8]` no llega al SMC por este camino.**

## Consecuencia para el proyecto

Esos ocho niveles AVFS son **los maximos de SCLK que el driver declara**, y son
la clase de constante que un driver especializado querria fijar. Si se escriben
y se sobrescriben en la misma secuencia de init, entonces el techo de reloj en
esta placa lo determinan el VBIOS y el firmware, no el host.

`262` ya habia medido que la tabla del VBIOS da **1071 MHz** como maximo de SCLK.
Con este orden, ese 1071 MHz es el numero que manda, y la ruta B de overdrive de
`127` sigue siendo la unica via para pasar de ahi.

**Esto no es todavia una perdida de rendimiento**: si la tabla de host trae
niveles equivalentes o mejores, sobrescribir es inocuo, y el VBIOS de esta placa
ya viene con una tabla de 8 estados SCLK reconstruida en `121`. Lo que queda
`NOT_DETERMINED` es si el contenido de host y el AVFS coinciden, y si el
firmware despues vuelve a escribir esos niveles por su cuenta.

## En el resume

A **no** corre en resume: `hwmgr_resume` (`hwmgr.c:331`) llama a
`phm_enable_dynamic_state_management` en `:345` y ya esta. O sea que B si corre en
resume, y A no. El SMC conserva su RAM entre suspend, pero B vuelve a escribir
`108..1883` equally. **En los dos caminos B sobrescribe.**

## Por que la hipotesis anterior era plausible y falsa

Mi razonamiento fue: "A corre con `!smu7_is_smc_ram_running`, o sea antes de
arrancar el firmware; el diseno de PP es llenar la RAM antes de arrancar; luego A
despues de B". El error es que **`start_smu` no arranca el firmware SMC**: es un
callback `amd_pm_funcs.load_firmware` que amdgpu invoca en
`amdgpu_device_fw_loading`, en un punto **anterior** a phase2, precisamente
porque el firmware tiene que estar ahi antes de que powerplay inicialice el DPM.
Ese "antes" es el que no vi.

Es el mismo patron de fallo que ya tengo registrado: **leer el proposito de un
guard y tratarlo como prueba de orden.** El guardia prueba una condicion de
entrada, no una posicion en la secuencia.

## Lo que NO afirmo

- **NO** afirmo que esto sea un fallo. Requiere saber si la tabla de host
  difiere de la AVFS, y eso no lo he comparado byte a byte.
- **NO** he medido ningun reloj. Todo esto es lectura de codigo: `B_RUNTIME =
  NOT_EXECUTED`.
- **NO** he tocado hardware ni he ejecutado nada en la GPU.
- Los offsets (236, 708, 108, 1884) vienen de gcc sobre la cabecera IP del
  corpus; el orden viene de leer las funciones enteras.

## La conclusion que mas me gusta de este cierre

`262` dejo el punto como `NOT_DETERMINED` con el discriminante nombrado, en vez
de darlo por bueno. Ese campo vacio es exactamente lo que impidio que publicase
la hipotesis invertida. **Un `NOT_DETERMINED` bien puesto renta; una
explicacion plausible tirada a la basura cuesta doble.**

## Frontier siguiente

Comparar `hw_data->dpm_table` frente a `avfs_graphics_level_polaris10` y
`avfs_memory_level_polaris10`: si difieren, el techo efectivo lo decide el VBIOS;
si coinciden, la ruta AVFS es redundante en vez de destructiva. Es una
comparacion de estructuras que ya tengo medidas con gcc, y ademas de lo que mas
interesa al rendimiento.