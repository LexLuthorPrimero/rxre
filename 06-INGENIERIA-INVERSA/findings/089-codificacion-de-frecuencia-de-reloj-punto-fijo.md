# 089 · Como se codifica una frecuencia de reloj: punto fijo 16.16 sobre el cristal

WORK_CLASS=READ_ONLY · WRITE_EXECUTION=NONE · MODIFICATIONS 0

## Que hay dentro de un nivel de graficos

`GraphicsLevel[8]` son 448 bytes, 56 por nivel. El contenido, medido por gcc:

| offset | bytes | campo |
|---:|---:|---|
| 0 | 4 | `MinVoltage` (`SMU_VoltageLevel`, un `uint32_t`) |
| 4 | 1 | `pcieDpmLevel` |
| 5 | 1 | `DeepSleepDivId` |
| 6 | 2 | `ActivityLevel` |
| 8 | 16 | `CgSpllFuncCntl3`, `CgSpllFuncCntl4`, `CcPwrDynRm`, `CcPwrDynRm1` |
| 24 | 8 | `SclkDid`, `padding`, `EnabledForActivity`, `EnabledForThrottle`, `UpHyst`, `DownHyst`, `VoltageDownHyst`, `PowerThrottle` |
| 32 | 24 | `SclkSetting` |

`sizeof(SMU74_Discrete_GraphicsLevel)` = 56, y `4+1+1+2+16+8+24` = 56. Cuadra.

**No hay ningun campo de frecuencia en MHz.** El reloj se describe con registros del
generador y con la pareja FCW.

## El reloj esta descrito dos veces

`SMU_SclkSetting`, 24 bytes:

```c
struct SMU_SclkSetting {
        uint32_t SclkFrequency;      /* la frecuencia, como numero plano */
        uint16_t Fcw_int;            /* y la misma frecuencia, como ratio FCW */
        uint16_t Fcw_frac;
        uint16_t Pcc_fcw_int;
        uint8_t  PllRange;
        uint8_t  SSc_En;
        uint16_t Sclk_slew_rate;
        uint16_t Pcc_up_slew_rate;
        uint16_t Pcc_down_slew_rate;
        uint16_t Fcw1_int;
        uint16_t Fcw1_frac;
        uint16_t Sclk_ss_slew_rate;
};
```

El host escribe las dos. `polaris10_smumgr.c:902` pone `SclkFrequency = clock`, y las
lineas 930-934 calculan `Fcw_int` y `Fcw_frac` a partir del mismo `clock`. Son una
misma magnitud en dos representaciones, y tienen que ser coherentes.

## La codificacion

`polaris10_smumgr.c:930-934`:

```c
sclk_setting->Fcw_int  = (uint16_t)((clock << table->SclkFcwRangeTable[PllRange].postdiv) / ref_clock);
temp  = clock << table->SclkFcwRangeTable[PllRange].postdiv;
temp <<= 0x10;
do_div(temp, ref_clock);
sclk_setting->Fcw_frac = temp & 0xffff;
```

El ratio es `clock / (ref_clock >> postdiv)`, y se guarda como **punto fijo 16.16**:
la parte entera en `Fcw_int`, los 16 bits bajos de la parte fraccionaria en `Fcw_frac`.

`postdiv` es un **exponente**, no un divisor. `POSTDIV_DIV_BY_16` vale `4`, no `16`
(`smu74_discrete.h:37-41`):

```c
#define POSTDIV_DIV_BY_1  0
#define POSTDIV_DIV_BY_2  1
#define POSTDIV_DIV_BY_4  2
#define POSTDIV_DIV_BY_8  3
#define POSTDIV_DIV_BY_16 4
```

Por eso el codigo hace `<<` y no `/`.

## La tabla de rangos y la formula son la misma operacion al reves

`Range_Table` (`polaris10_smumgr.c:68`) son ocho entradas `{vco, postdiv, fcw_lo,
fcw_hi, fcw_pcc}`. Y la conversion a Hz, en `polaris10_smumgr.c:874`:

```c
range_table[i].trans_lower_frequency = (ref_clk * Range_Table[i].fcw_trans_lower) >> Range_Table[i].postdiv;
range_table[i].trans_upper_frequency = (ref_clk * Range_Table[i].fcw_trans_upper) >> Range_Table[i].postdiv;
```

Una multiplica por el cristal, la otra divide. Comprobado numericamente en las ocho
entradas con `ref_clk = 10000` kHz:

| VCO | postdiv | divisor real | FCW | frecuencia Hz |
|---|---:|---:|---|---|
| 2_4 | 4 | 16 | 75..160 | 46875..100000 kHz |
| 3_6 | 4 | 16 | 112..224 | 70000..140000 kHz |
| 2_4 | 3 | 8 | 75..160 | 93750..200000 kHz |
| 3_6 | 3 | 8 | 112..224 | 140000..280000 kHz |
| 2_4 | 2 | 4 | 75..160 | 187500..400000 kHz |
| 3_6 | 2 | 4 | 112..216 | 280000..540000 kHz |
| 2_4 | 1 | 2 | 75..160 | 375000..800000 kHz |
| 3_6 | 1 | 2 | 112..216 | 560000..1080000 kHz |

Y el FCW reconstruido desde los extremos de frecuencia devuelve **exactamente** los
limites de la tabla, en las ocho entradas:

```
se cumple en las 8 entradas: True
```

Es la identidad que da sentido al conjunto: **el trabajo de la tabla de rangos es
encontrar el `postdiv` que trae el FCW de la frecuencia pedida dentro de la ventana
valida del VCO.** Con dos VCO y cuatro divisores hay ocho combinaciones porque el
generador tiene dos ventanas de operacion y cuatro divisores de post.

## El reloj de referencia es de lectura, no una constante

**CORRECCION. La version anterior de esta seccion estaba mal, en la funcion y en el
motivo.** Decir que Polaris12 podria caer en `soc15_get_xclk` y analisar sus ramas de
`MP1_HWIP` era investigating una funcion que **no es la de este chip**.

La cadena real, verificada:

```
amdgpu_device.c:1980   case CHIP_POLARIS12:
amdgpu_device.c:1989       r = vi_set_ip_blocks(adev);
vi.c:2114                     anade pp_smu_ip_block y vi_common_ip_block
vi.c:2022                     .early_init = vi_common_early_init
vi.c:1472                     adev->asic_funcs = &vi_asic_funcs;
vi.c:1434                     .get_xclk = &vi_get_xclk,
```

**Polaris12 usa `vi_get_xclk`**, no `soc15_get_xclk`. Busqueda literal de
`CHIP_POLARIS12` en `drivers/gpu/drm/amd/`: 74 coincidencias, **cero** en `soc15.c`.
Ademas el mismo chip que en `amdgpu/` es "VI" es, en el subsistema de potencia, "SMU 7.4"
(`hwmgr.c:154-157`), y ahi si usa el metodo FCW. La frontera real no es la generacion de
silicio: es la version del microcodigo.

Las cuatro ramas de `vi_get_xclk` (`vi.c:539-563`):

```c
u32 reference_clock = adev->clock.spll.reference_freq;

if (adev->flags & AMD_IS_APU) {
        switch (adev->asic_type) {
        case CHIP_STONEY:  return 10000;      /* vbios dice 48, real 100 */
        default:           return reference_clock;
        }
}

tmp = RREG32_SMC(ixCG_CLKPIN_CNTL_2);
if (REG_GET_FIELD(tmp, CG_CLKPIN_CNTL_2, MUX_TCLK_TO_XCLK))
        return 1000;

tmp = RREG32_SMC(ixCG_CLKPIN_CNTL);
if (REG_GET_FIELD(tmp, CG_CLKPIN_CNTL, XTALIN_DIVIDE))
        return reference_clock / 4;

return reference_clock;
```

Para una RX 5500, dGPU, queda descartada la rama de APU
(`amdgpu_device.c:1984-1987` separa CZ de VI por `AMD_IS_APU`). Quedan **tres**:

| rama | valor | condicion |
|---|---:|---|
| 1 | `1000` | `MUX_TCLK_TO_XCLK` en `CG_CLKPIN_CNTL_2` |
| 2 | `reference_clock / 4` | `XTALIN_DIVIDE` en `CG_CLKPIN_CNTL` |
| 3 | `reference_clock` | ninguna de las dos |

Las dos decisiones se leen de **registros del SMC**, y `MUX_TCLK_TO_XCLK` **no lo
escribe el driver en ningun sitio**: todas las apariciones de `CG_CLKPIN_CNTL` en
`vi.c` son lecturas (`:554`, `:555`, `:558`, `:559`) o escrituras de otros bits
(`:1202`-`:1210`).

Cual de las tres se aplica es `RUNTIME_MISSING`, y ahora **por el motivo correcto**: el
estado de dos registros del SMC que el host solo lee. La unidad de
`reference_freq` es 10 kHz (`atombios.h:3125`, `usCoreReferenceClock //In 10Khz unit`),
asi que con un cristal de 100 MHz los tres valores serian 10000, 2500 y 1000.

**Lo que si es solido para un driver propio: el reloj de referencia se LEE de un registro
del SMC, no es constante.** Con eso, todos los numeros de la tabla se calculan en
runtime y no se pueden cocer. Y si el reloj esta dividido por 4, **todos** los
`Fcw_int` que calcule el host cambian en un factor 4.

## Un detalle que no hay que replicar

El bucle que busca el rango **no tiene `else`** (`polaris10_smumgr.c:922-928`):

```c
for (i = 0; i < NUM_SCLK_RANGE; i++) {
        if (clock > smu_data->range_table[i].trans_lower_frequency
        && clock <= smu_data->range_table[i].trans_upper_frequency) {
                sclk_setting->PllRange = i;
                break;
        }
}
```

Si la frecuencia queda fuera de las ocho ventanas, `PllRange` conserva lo que tuviera.
La tabla se crea con `kzalloc_obj` (`smu7_hwmgr.c:3030`) y luego se le aplica
`smu7_init_dpm_defaults`, asi que no es basura indeterminada: es un valor por defecto,
probablemente 0, que significa la entrada ÷16 / VCO 2.4. **Una frecuencia impos queda
codificada con una ventana que no le corresponde, sin error ni aviso.**

Un driver propio deberia rechazar la frecuencia o clamar. Este caso es el mismo
"produce algo plausible en vez de un error" del resto del trabajo, aqui en el driver
y no en la herramienta.

Ademas hay dos constantes cocidas en el calculo: el PCC al 10% y el spread spectrum al
2% (`polaris10_smumgr.c:936` y `:940`), con un comentario que lo dice
(`Hardcode 10% for now`). Un driver propio tiene que decidir esos dos valores en vez
de heredarlos.

## Lectura practica

Para fijar una frecuencia hay que:

1. Leer `ref_clock` de `adev->clock.spll.reference_freq`.
2. Buscar el indice de rango donde caiga la frecuencia.
3. `Fcw_int = (freq << postdiv) / ref_clock`, `Fcw_frac` con los 16 bits altos.
4. Poner las dos copias: `SclkFrequency` y la pareja FCW.
5. Elegir `postdiv` de forma que el FCW caiga en la ventana del VCO.

No basta con escribir una frecuencia. Y el paso 3 es donde un error de una unidad
produce un reloj estable pero equivocado, que es el fallo mas dificil de detectar sin
osciloscopio.

## Clasificacion

- `SCLK_ENCODING = PROVEN`: punto fijo 16.16, `(freq << postdiv) / ref_clock`.
- `POSTDIV_IS_EXPONENT = PROVEN`: `POSTDIV_DIV_BY_16` = 4, y el codigo usa `<<`.
- `SCLK_RANGE_TABLE_IDENTITY = PROVEN`: las dos tablas son inversas, verificado en las
  ocho entradas.
- `SCLK_REFERENCE_CLOCK_IS_RUNTIME = PROVEN`: sale de `adev->clock.spll.reference_freq`.
- `SCLK_XCLK_FUNCTION_FOR_POLARIS12 = PROVEN`: `vi_get_xclk` (`vi.c:539`), reached por
  `vi.c:1472` <- `vi.c:2022` <- `vi.c:2114` <- `amdgpu_device.c:1989`. **No es
  `soc15_get_xclk`**; la version anterior de este documento lo afirmaba y era falso.
- `SCLK_XCLK_BRANCH_FOR_POLARIS12 = RUNTIME_MISSING`: tres ramas reales
  (`1000`, `reference_clock/4`, `reference_clock`), decididas por dos registros del SMC
  que el host solo lee. `MUX_TCLK_TO_XCLK` no lo escribe el driver.
- `SCLK_RANGE_LOOKUP_NO_ELSE = PROVEN`: una frecuencia fuera de rango deja `PllRange`
  con su valor anterior.
- `SCLK_PCC_SS_HARDCODED = PROVEN`: 10% y 2% constantes en el codigo.

## Lo que esto NO dice

No dice si el firmware usa `SclkFrequency` o la pareja FCW cuando discrepan. Esa
pregunta necesita el firmware, y no esta en el corpus.

No dice si las ocho ventanas son las correctas para esta placa concreta. Son las que
el driver declara para la generacion.

No hay lectura de hardware aqui.