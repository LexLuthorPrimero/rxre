# 262 · Dos escritores sobre la misma RAM del SMC, y un TAPADA 0 que no puede verlos

WORK_CLASS=READ_ONLY · WRITE_EXECUTION=NONE · MODIFICATIONS 0

> ## Que cambia respecto a lo anterior
>
> Recalcule la cobertura desde cero porque las anclas de linea cambiaron, y el
> recalculo da un resultado que **no** es "nada queda tapado". Da **9 de 13
> escrituras sin rango**, y entre esas hay dos que apuntan de lleno dentro de la
> unica escritura grande. `TAPADA 0` no es un resultado: es la ausencia de
> comparacion.

## Pregunta

`smc_copy_scope` dice `TAPADA 0` sobre las 13 escrituras de
`polaris10_smumgr.c`. Mi criterio de cierre era recalcular la cobertura y ver si
alguna conclusion se caia. Antes de mirar si se cae, hay que saber si ese `0`
puede ver todo lo que hay que ver.

## El problema del recuento

```
smc_copy_scope 1.2.0 · 13 escrituras · 5 offsets · 5 tamanos medidos
  TAPADA          0
  VIVA            4
  NO_RESUELTO     9
```

**Solo 4 tienen rango.** Las otras 9 no pueden entrar en ninguna comparacion de
contencion: sin rango no hay intervalo que comparar. Un `TAPADA 0` sobre 13
escrituras de las que 9 son invisibles al calculo, no es un resultado negativo, es
**`NOT_DETERMINED`**. Y el propio tool lo dice en su pie:

```
RESUMEN (orden TEXTUAL de las sentencias, no de ejecucion)
```

O sea que la herramienta **no modela el orden de ejecucion**, que es justo lo
que decide quien gana cuando dos escrituras apuntan al mismo sitio.

## Medidas que hacen falta, y de donde salen

Vienen de **gcc**, no de calculo a mano, sobre
`pm/powerplay/inc/smu74_discrete.h`, que compila limpia:

| simbolo | valor |
|---|---|
| `sizeof(SMU74_PIDController)` | 36 |
| `offsetof(SMU74_Discrete_DpmTable, SystemFlags)` | 108 |
| `offsetof(SMU74_Discrete_DpmTable, VRConfig)` | dentro del rango, sin medir |
| `offsetof(SMU74_Discrete_DpmTable, GraphicsLevel)` | **236** |
| `offsetof(SMU74_Discrete_DpmTable, MemoryLevel)` | **708** |
| `offsetof(SMU74_Discrete_DpmTable, BootMVdd)` | sin medir |
| `offsetof(SMU74_Discrete_DpmTable, LowSclkInterruptThreshold)` | 1692 |
| `sizeof(SMU74_Discrete_DpmTable)` | 1884 |

## Los dos escritores

**Escritor A**, `polaris10_setup_graphics_level_structure` (`:120`), con datos de
**constantes de compilacion** del propio driver:

```
:80   static const SMU74_Discrete_GraphicsLevel avfs_graphics_level_polaris10[8] = {
:93   static const SMU74_Discrete_MemoryLevel   avfs_memory_level_polaris10 = {
:149  -> dpm_table_start + GraphicsLevel (236),  sizeof(avfs_graphics_level_polaris10)
:157  -> dpm_table_start + MemoryLevel   (708),  sizeof(avfs_memory_level_polaris10)
```

**Escritor B**, `polaris10_init_smc_table` (`:1913`), con datos de la **tabla de
host**, que viene del VBIOS:

```
:2118  smu7_copy_bytes_to_smc(hwmgr,
:2119        dpm_table_start + offsetof(SMU74_Discrete_DpmTable, SystemFlags),
:2121        (uint8_t *)&(table->SystemFlags),
:2122        sizeof(SMU74_Discrete_DpmTable) - 3 * sizeof(SMU74_PIDController), ...)
```

`1884 - 3*36 = 1776`, asi que B escribe el intervalo **108..1883**.

**Y 236 y 708 estan dentro de 108..1883.** A y B escriben el mismo sitio de la
misma RAM del SMC, con fuentes de datos distintas.

Los dos usan la misma base: A la lee de
`SMU7_FIRMWARE_HEADER_LOCATION + offsetof(SMU74_Firmware_Header, DpmTable)` y B
usa `smu_data->smu7_data.dpm_table_start`. Que sean el mismo valor **no lo he
verificado**: es `CORROBORATED`, no `PROVEN`.

## El discriminante, y por que no lo cierro

El orden de ejecucion es lo unico que decide, y las dos rutas entran por
punteros de tablas distintas:

```
A: pp_dpm_funcs.load_firmware        = pp_dpm_load_fw        (amd_powerplay.c:1554)
      -> pp_dpm_load_fw (:308) -> smumgr_funcs->start_smu (:315)
      -> polaris10_start_smu (:292), guardado por if (!smu7_is_smc_ram_running && not_vf)
      -> polaris10_avfs_event_mgr (:311) -> polaris10_setup_graphics_level_structure (:182)

B: hwmgr_func->dynamic_state_management_enable = smu7_enable_dpm_tasks  (smu7_hwmgr.c:5861)
      -> hardwaremanager.c:91-92 -> smu7_enable_dpm_tasks (:1566)
      -> smum_init_smc_table (:1622) -> polaris10_init_smc_table
```

Lo que **si** se puede decir sin suponer: A corre bajo `!smu7_is_smc_ram_running`,
o sea **con la RAM del SMC todavia parada**. B escribe precisamente en esa RAM.
El diseno entero de PP es llenar la RAM del SMC con el host **antes** de
arrancar el firmware, asi que el orden esperable es **A despues de B**, y entonces
A sobrevive.

**Pero "el orden esperable" no es una medida.** No he tracedado el orden real en
la capa amdgpu: mi busqueda del llamante de `hardwaremanager.c:91` salio vacia
en dos intentos, asi que ese enlace es `NOT_DETERMINED` y **no ausente**. Una
de esas dos busquedas caduco por timeout, que es peor: un cero por tiempo
agotado no es informacion.

Estado del cierre: **`NOT_DETERMINED`**, con el discriminante nombrado y medible
en cuanto se lea la secuencia de init y resume de amdgpu.

## Por que esto importa mas que un recuento

Si el orden real fuera B despues de A, entonces la copia de 1776 B **machaca**
los niveles AVFS que el driver habia puesto, y los sustituye por los del VBIOS.
No es una hipotesis exotica: son dos fuentes de verdad para el mismo intervalo,
y una gana por orden de llamadas, no por diseno explicito.

Para un driver especializado esto no es academico: `avfs_graphics_level_polaris10[8]`
son los **maximos AVFS que compila el driver**, escritos a mano, y son
justamente el techo alcanzable de SCLK. Si B los sobreescribe, el techo efectivo
pasa a ser el del VBIOS, que es **1071 MHz** segun la reconstruccion de la tabla
DPM. Es justo el limite que mi hallazgo de ULV daba por alcanzable con
overdrive.

No afirmo que se sobreescriba. Afirmo que **la pregunta esta abierta y es
decisiva**, y que hoy nadie en el proyecto la tiene anotada.

## Correccion de alcance sobre mi propia conclusion previa

`213` y `214` concluyen `SMC_FAN_AND_ARB_WRITES_UNTOUCHED = PROVEN` y
`SMC_OVERDRIVE_WRITE_UNTOUCHED = PROVEN_DERIVED`. Esas dos **no las toco aqui**:
las escrituras de fan y arb estan en tablas distintas de la DPM (offsets 0..35 y
0..383 de `fan_table_start` y `arb_table_start`), asi que la contencion no puede
darse y `PROVEN` aguanta. Lo que **no** cubrian esas dos claims es el par A/B de
este documento, que es DPM contra DPM dentro de la misma tabla. Es un hueco
distinto y no estaba registrado.

## Tool y reproduccion

Sin herramienta nueva. gcc como verdad de terreno para el layout, y lectura de
funciones completas para las dos rutas. El unico hueco de capacidad es el
orden de ejecucion, que `smc_copy_scope` **no modela por diseno** y dice que no
modela.

## Frontier siguiente, con el discriminante puesto

Leer la secuencia de init y de resume en la capa amdgpu hasta
`amd_pm_funcs.load_firmware` y `phm_enable_dpm_for_runtime_resume`, y afirmar el
orden. Es una lectura de codigo, coste bajo, y cierra el unico punto que queda
`NOT_DETERMINED` de este hallazgo.

Si se confirma A despues de B, la consecuencia es que el techo de SCLK en esta
placa lo fija el **VBIOS** y no el AVFS del driver, y eso cambia el objetivo de
rendimiento.