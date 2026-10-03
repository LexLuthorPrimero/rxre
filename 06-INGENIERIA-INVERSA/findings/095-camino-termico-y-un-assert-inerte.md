# 095 · El camino termico: grados que entran, Q8.8 que sale, y un assert que avisa y no hace nada

WORK_CLASS=READ_ONLY · WRITE_EXECUTION=NONE · MODIFICATIONS 0

## La cadena de los limites termicos

`polaris10_smumgr.c:2019-2024`, dentro de `polaris10_init_smc_table`:

```c
table->TemperatureLimitHigh =
        table_info->cac_dtp_table->usTargetOperatingTemp *
        SMU7_Q88_FORMAT_CONVERSION_UNIT;
table->TemperatureLimitLow  =
        (table_info->cac_dtp_table->usTargetOperatingTemp - 1) *
        SMU7_Q88_FORMAT_CONVERSION_UNIT;
```

`SMU7_Q88_FORMAT_CONVERSION_UNIT = 256` (`smu7_hwmgr.h:355`). La entrada esta en
**grados Celsius enteros**, de la sub-tabla `cac_dtp_table` del PPT, y la salida es
**punto fijo Q8.8**: los 8 bits bajos son la parte fraccionaria.

El limite bajo es **un grado menos** que el alto. Es una ventana de un grado, no dos
umbrales independientes.

Los dos campos son `uint16_t` (`smu74_discrete.h:310` y `:312`). Con multiplicador 256,
un valor de grados hasta 255 cabe justo; a partir de ahi no cabe.

## El assert que detecta el desbordamiento y no hace nada

Tres lineas antes, `polaris10_smumgr.c:445-447`:

```c
PP_ASSERT_WITH_CODE(cac_dtp_table->usTargetOperatingTemp <= 255,
                        "Target Operating Temp is out of Range!",
                        );
```

El tercer argumento esta **vacio**. El macro, `inc/pp_debug.h:37-43`:

```c
#define PP_ASSERT_WITH_CODE(cond, msg, code)	\
	do {					\
		if (!(cond)) {			\
			pr_warn_ratelimited("%s\n", msg);	\
			code;			\
		}				\
	} while (0)
```

Con `code` vacio, la expansion es `if (!(cond)) { pr_warn_ratelimited(...); }`: avisa y
**sigue adelante**. Comparar con `polaris10_smumgr.c:1699-1701`, donde el mismo macro si
lleva `return -EINVAL` y por tanto detiene.

O sea: **la comprobacion existe, es correcta, detecta exactamente la condicion que
corrompe el valor, y su unico efecto es un aviso en el log.**

## Que pasa cuando se dispara

Aritmetica verificada, no estimada:

```
usTargetOperatingTemp -> campo uint16_t -> grados leidos de vuelta
       0 -> High=     0 ( 0.00 C)   Low= 65280 (255.00 C)
       1 -> High=   256 ( 1.00 C)   Low=     0 ( 0.00 C)
     100 -> High= 25600 (100.00 C)  Low= 25344 ( 99.00 C)
     255 -> High= 65280 (255.00 C)  Low= 65024 (254.00 C)
     256 -> High=     0 ( 0.00 C)   Low= 65280 (255.00 C)  <-- TRUNCADO
     300 -> High= 11264 (44.00 C)   Low= 11008 ( 43.00 C)  <-- TRUNCADO
```

Dos casos, ambos SilentZero y los dos plausibles:

**Por encima de 255.** El producto se trunca al `uint16_t` de destino. Con 300 grados, el
firmware recibe 44. Un limite termico de 44 °C en una GPU que se estrangula por
temperatura es un valor **muy plausible**: esta por debajo del trabajo normal, asi que no
dispara nada raro. Y con 256, `High` vale exactamente 0.

**Con valor 0.** `usTargetOperatingTemp - 1` da `-1` en `int`, `* 256` da `-256`, y al
truncar a `uint16_t` queda **65280 = 255 °C**. El par sale **invertido**: limite alto 0,
limite bajo 255. Un firmware que espere `Low < High` recibe lo contrario.

Ninguno de los dos casos da un error: dan numeros que significan otra cosa.

### No es alcanzable por el usuario

Comprobado, porque el comentario de `process_pptables_v1_0.c:672` dice
*"Set the initial temp to the same as default"* y eso sugiere que el valor puede cambiar:

`usTargetOperatingTemp` solo se escribe en cuatro sitios, los tres en el parser del PPT
(`process_pptables_v1_0.c:605`, `:627`, `:671`) y el cuarto al inicializar
(`smu7_hwmgr.c:2614`, copiando a la tabla dinamica). **Ninguno fuera de
`pm/powerplay`.**

La unica temperatura objetivo escribible por el usuario es
`fan_target_temperature_store` (`amdgpu_pm.c:4240`), que va por
`amdgpu_distribute_custom_od_settings` y controla el **ventilador**, no el limite de la
tabla DPM.

O sea: el truncamiento **no lo puede provocar un usuario**. Depende solo de lo que diga
la PowerPlay Table de la placa. Eso baja la gravedad respecto a "vulnerable", pero no
cambia que el assert que lo detectaria sea inerte.

## Dos campos que valen cero literal

```c
table->VoltageResponseTime = 0;      /* 2027 */
table->PhaseResponseTime   = 0;      /* 2028 */
```

Sin condicion, sin fuente, sin justificacion. Se suben a cero al SMC. Si el firmware los
usa como constantes de un lazo de control, el lazo corre con tiempo de respuesta cero.

Que sea un problema o no es `SEMANTIC_MISSING`: el firmware no esta en el corpus.

## BootPhases: nadie lo escribe

`BootPhases` es un campo de la tabla (`smu74_discrete.h:270`). Busqueda por nombre exacto
en todo `drivers/gpu/drm/amd`: tres coincidencias, **las tres declaraciones**, ninguna
escritura.

Queda a cero por la creacion con `kzalloc_obj` del backend
(`polaris10_smumgr.c:339`). El firmware recibe `BootPhases = 0`.

Esto encaja con `207`: los bits 30-31 de `MinVoltage` son precisamente las fases, y
`polaris10_get_dependency_volt_by_clk` pone `*voltage |= 1 << PHASES_SHIFT`, o sea **1**.
La tabla dice una fase y `BootPhases` dice cero. Si el firmware usa ambos, no coinciden.
Que lo use: `NOT_DETERMINED`.

## Dos escalas para el mismo TDP

| sitio | escala | destino |
|---|---:|---|
| `polaris10_smumgr.c:442-443` | `usTDP * 128` | `DefaultTdp` y `TargetTdp` de la tabla |
| `smu7_powertune.c:1258` | `(100+ajuste) * usTDP * 256 / 100` | `PPSMC_MSG_OverDriveSetTargetTdp` |

El mismo `usTDP` de la misma sub-tabla, con **multiplicadores distintos**: 128 en la tabla
y 256 en el mensaje. Las dos lineas son correctas en lo que escriben; lo que no se puede
determinar desde el host es si es una discrepancia o dos convenciones distintas para
dos destinos distintos. `SEMANTIC_MISSING`.

## Los limites de alerta NO van por mensaje SMC

Preguntado de la forma que uno se preguntaria: hay un mensaje tipo
`PPSMC_MSG_SetTemperatureLimit`? **No existe en este kernel.** Busqueda por nombre exacto
en `pm/powerplay/`: cero coincidencias.

Los umbrales de alerta van por **registros indirectos** del controlador termico,
`smu7_thermal.c:335-343`:

```c
CG_THERMAL_INT.DIG_THERM_INTH   = high / PP_TEMPERATURE_UNITS_PER_CENTIGRADES
CG_THERMAL_INT.DIG_THERM_INTL   = low  / PP_TEMPERATURE_UNITS_PER_CENTIGRADES
CG_THERMAL_CTRL.DIG_THERM_DPM   = high / PP_TEMPERATURE_UNITS_PER_CENTIGRADES
```

`PP_TEMPERATURE_UNITS_PER_CENTIGRADES = 1000` (`inc/power_state.h:119`): la API habla en
mili-grados y el hardware recibe **grados enteros por division entera**. Es decir: **se
pierde la parte fraccionaria antes de llegar al hardware.**

El maximo viene del PPT (`smu7_hwmgr.c:5558-5560`,
`usSoftwareShutdownTemp * 1000`). El valor por defecto `104000` de
`thermal_temp_setting` **es inalcanzable en esta ruta**: su unico consumidor esta en la
rama `pp_table_version == PP_TABLE_V0` (`smu7_hwmgr.c:5561-5562`), y para Polaris12 la
version es V1.

## Dos caminos muertos en Polaris12

Comprobado por identificador, no por lectura.

**`smu7_patch_voltage_workaround`** (`smu7_hwmgr.c:2493-2535`) exige
`adev->pdev->device == 0x67DF` (`smu7_hwmgr.c:2513`). `0x67DF` esta asignado a
`CHIP_POLARIS10` en `amdgpu_drv.c:2026`. Los identificadores de `CHIP_POLARIS12` son
`0x6980, 0x6981, 0x6985, 0x6986, 0x6987, 0x6995, 0x6997, 0x699F`
(`amdgpu_drv.c:2034-2041`), y `hwmgr->chip_id` sale de esa misma tabla
(`amdgpu_device.c:3694`). Los dos son excluyentes: **la condicion es falsa por
construccion**, no "podria cumplirse". Y no toca ningun limite termico.

**`PPM_PkgPwrLimit` y `PPM_TemperatureLimit`**: solo aparecen en `ci_smumgr.c:735-736` e
`iceland_smumgr.c:1879-1880`. En la ruta de Polaris12 quedan a cero.

> **CORRECCION.** Una version anterior de este parrafo decia que `ci_smumgr.c` era
> Carrizo. **Es falso.** `ci_smu_funcs` se asigna en `hwmgr.c:100`, bajo
> `case AMDGPU_FAMILY_CI`, y esa familia es GCN1/2: Bonaire, Hawaii, Kaveri, Kabini y
> Mullins (`hwmgr.c:98-100`). Carrizo es GCN3 fusionado, familia CZ, y va a
> `smu8_smu_funcs` (`hwmgr.c:127`), otro fichero. `iceland_smu_funcs` si es Topaz, en
> `hwmgr.c:136` bajo `case CHIP_TOPAZ`. La conclusion (codigo muerto para Polaris12)
> no cambia; los nombres de chip si.

## La correccion para un driver propio

1. Comprobar el rango **antes** de calcular, y no con un assert de tercer argumento
   vacio: `if (t == 0 || t > 255) ...`.
2. Tratar `usTargetOperatingTemp == 0` como caso propio, no restar 1 sin comprobar.
3. No asumir que un limite termico que "parece normal" no esta truncado: con 300 grados
   el firmware recibe 44, que es plausible.
4. Decidir `VoltageResponseTime` y `PhaseResponseTime` en vez de heredar el cero.
5. Escribir `BootPhases`, o documentar que se deja a cero a proposito.
6. Para los umbrales de alerta, escribir los registros indirectos; no hay mensaje.

## Clasificacion

- `SMC_THERMAL_UNIT_IN = PROVEN`: grados Celsius enteros, del PPT.
- `SMC_THERMAL_UNIT_OUT = PROVEN`: Q8.8, `SMU7_Q88_FORMAT_CONVERSION_UNIT` = 256.
- `SMC_THERMAL_LIMIT_LOW_IS_MINUS_ONE = PROVEN`: el limite bajo es el alto menos un
  grado.
- `SMC_THERMAL_RANGE_ASSERT_INERT = PROVEN`: `PP_ASSERT_WITH_CODE` con el tercer
  argumento vacio avisa y continua. Detecta el desbordamiento y no lo detiene.
- `SMC_THERMAL_TRUNCATION = PROVEN`: por encima de 255 grados el valor se trunca al
  `uint16_t`; con 300 quedan 44 grados. Con 0 el par sale invertido (alto 0, bajo 255).
- `SMC_RESPONSE_TIMES_HARDCODED_ZERO = PROVEN`: los dos valen 0 literal.
- `SMC_BOOT_PHASES_UNWRITTEN = PROVEN`: ninguna escritura en todo `drivers/gpu/drm/amd`.
- `SMC_TDP_TWO_SCALES = PROVEN` las dos lineas, `SEMANTIC_MISSING` si es discrepancia.
- `SMC_SET_TEMPERATURE_LIMIT_MESSAGE = PROVEN_ABSENT`: buscado por nombre exacto, cero
  coincidencias. Los umbrales van por registros indirectos.
- `SMC_THERMAL_INT_DIVISION = PROVEN`: mili-grados a grados por division entera.
- `SMC_PATCH_VOLTAGE_WORKAROUND_UNREACHABLE = PROVEN`: `0x67DF` es POLARIS10 y
  `chip_id` sale de la tabla de PCI.
- `SMC_PPM_LIMITS_DEAD = PROVEN`: Carrizo y Topaz unicamente.
- `SMC_CAC_DTP_TABLE_NO_NULL_CHECK = PROVEN` el defecto, `RUNTIME_MISSING` si se alcanza.

## Lo que esto NO dice

No dice que la PowerPlay Table de esta placa tenga un valor fuera de rango. No he leido
el PPT ni el VBIOS: es analisis estatico de la ruta de codigo.

No dice que el firmware trunque, interprete o rechace. `TemperatureLimitHigh` en Q8.8 es
una afirmacion sobre el nombre del campo y el multiplicador; lo que el firmware haga con
los bits es `SEMANTIC_MISSING`.

No hay lectura de hardware aqui, no hay escritura, no hay `/sys`, no hay modulos.