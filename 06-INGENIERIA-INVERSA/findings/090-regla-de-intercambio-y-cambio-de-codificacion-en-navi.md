# 090 · Regla de intercambio de bytes y el cambio de codificacion de reloj en Navi

WORK_CLASS=READ_ONLY · WRITE_EXECUTION=NONE · MODIFICATIONS 0

## Parte 1 · la regla de intercambio, verificada campo a campo

El host convierte 60 campos de la tabla DPM antes de subirla. El reparto parece
arbitrario hasta que se mide: **todo campo de mas de un byte se intercambia, y el
ancho del intercambio es el ancho del campo**.

```
CONVERT_FROM_HOST_TO_SMC_UL(X)   = cpu_to_be32(X)     para uint32_t
CONVERT_FROM_HOST_TO_SMC_US(X)   = cpu_to_be16(X)     para uint16_t
```

Comprobado sobre los 63 campos de los tres structs de nivel de Polaris12
(`SMU74_Discrete_GraphicsLevel`, `SMU74_Discrete_MemoryLevel`,
`SMU74_Discrete_ACPILevel`):

```
63 campos
fuera del invariante: 2
    CgSpllFuncCntl3   4B
    CgSpllFuncCntl4   4B
```

Los bytes de un byte no se tocan. Todo lo demas cumple.

Esto no es cosmetico. `MinVoltage` y `SclkFrequency` son de 32 bits y se intercambian
como **palabras enteras**; `Fcw_int`, `Fcw_frac` y `ActivityLevel` son de 16 y se
intercambian por separado. Confundir los dos anchos no da un valor raro: da un
`MinVoltage` multiplicado por 256, que es un voltaje plausible. Es un fallo
silencioso.

## Parte 2 · dos campos que nadie toca

`CgSpllFuncCntl3` y `CgSpllFuncCntl4` ocupan 8 bytes de cada nivel de 56, y en
`polaris10_smumgr.c` **no aparecen ni una vez**: ni se escriben ni se intercambian.
Verificado en todo el subarbol de `pm/powerplay`:

```
CgSpllFuncCntl3  -> 4 ficheros .c      (los cuatro de la generacion anterior)
CgSpllFuncCntl4  -> 4 ficheros .c
polaris10_smumgr.c  SclkDid 0   CgSpllFcntl 0   Fcw_int 4   -> FCW
```

Lo mismo con `SclkDid`, el tercer campo de la familia.

## Que codifican cada generacion: la tabla completa

Criterio: busqueda literal en los 14 `.c` de `pm/powerplay/smumgr/`, con los totales a
la vista para que sean reproducibles. `SclkDid` = 8 coincidencias, `CgSpllFuncCntl[0-9]`
= 32, `Fcw_int`|`Fcw_frac` = 24, `MpllFuncCntl` = 24. Ninguna truncada.

| fichero | chips que sirve | reloj de graficos | reloj de memoria |
|---|---|---|---|
| `ci_smumgr.c` | CI: Bonaire, Hawaii, Kaveri, Kabini, Mullins (`hwmgr.c:100`) | **registros** `:362-366` | **registros** `:1105-1107` |
| `iceland_smumgr.c` | CHIP_TOPAZ (`hwmgr.c:136`) | **registros** `:864-868` | **registros** `:1156-1158` |
| `tonga_smumgr.c` | CHIP_TONGA (`hwmgr.c:144`) | **registros** `:607-611` | **registros** `:907-909` |
| `fiji_smumgr.c` | CHIP_FIJI (`hwmgr.c:149`) | **registros** `:927-931` | ninguno `:1178-1214` |
| `polaris10_smumgr.c` | **POLARIS10/11/12** (`hwmgr.c:154-157`) | **FCW** `:906-907`, `:930-934` | ninguno `:1178-1204` |
| `vegam_smumgr.c` | CHIP_VEGAM (`hwmgr.c:162`) | **FCW** `:759-765` | **FCW** `:974-975` |
| `smu8_smumgr.c` | CZ: Carrizo, Stoney (`hwmgr.c:127`) | ninguno | ninguno |
| `vega10_smumgr.c` | CHIP_VEGA10 (`hwmgr.c:176`) | ninguno | ninguno |
| `vega12_smumgr.c` | CHIP_VEGA12 (`hwmgr.c:180`) | ninguno | ninguno |
| `vega20_smumgr.c` | CHIP_VEGA20 (`hwmgr.c:186`) | ninguno | ninguno |
| `smu10_smumgr.c` | CHIP_RAVEN (`hwmgr.c:197`) | ninguno | ninguno |
| `smu9_smumgr.c` / `smu7_smumgr.c` / `smumgr.c` | auxiliares y despacho | ninguno | ninguno |

**Ningun fichero usa los dos metodos a la vez.** La interseccion de las busquedas
literales de `SclkDid`+`CgSpllFuncCntl` con las de `Fcw_int`/`Fcw_frac` sobre
`smumgr/*.c` es **vacia**.

## La frontera, corregida

**No es en Navi. La version anterior de este documento decia que si, y era falso por dos
motivos independientes.**

**Motivo 1: el salto ocurre en Polaris, que es anterior a Navi.** Polaris10/11/12 son
SMU 7.4 y ya usan FCW (`polaris10_smumgr.c:930-934`). Los que usan el metodo de
registros son SMU 7.0 (CI), 7.1 (Topaz), 7.2 (Tonga) y 7.3 (Fiji). La frontera real es
**SMU 7.3 -> SMU 7.4**.

**Motivo 2: Navi y posteriores no usan ninguno de los dos metodos.** No estan en
`smumgr/`: Arcturus, Aldebaran, Sienna, Van Gogh, Navi, Renoir y Dimgrey viven en
`pm/swsmu/` y en `amdgpu/*_reg_init.c`. Busqueda literal de `Fcw`/`fcw` en
`pm/swsmu/**/*.c`: **una sola coincidencia en todo el arbol**, y es una macro de
depuracion sin usar (`smu14_driver_if_v14_0.h:164`). El contrato pasa a ser frecuencia
objetivo y lo resuelve el firmware.

**El error de Carrizo.** Este era un error de hecho, no de matiz. `ci_smumgr.c` es la
familia **CI** (`hwmgr.c:98-100`: Bonaire, Hawaii, Kaveri, Kabini, Mullins), que es
**GCN1/2**. Carrizo y Stoney son GCN3 fusionados, familia **CZ**, y van a
`smu8_smu_funcs` (`hwmgr.c:124-127`), que **no codifica reloj de ninguna manera**. El
reparto por `AMD_IS_APU` esta en `amdgpu_device.c:1984-1987`. Carrizo no esta en el
grupo de registros: esta en el grupo que no codifica nada.

**La prueba estructural de que la frontera es del firmware, no del driver:** la struct
de Polaris12 contiene **las dos cosas a la vez**. `SMU74_Discrete_DpmTable` conserva los
campos legacy `CgSpllFuncCntl3`/`CgSpllFuncCntl4` (`smu74_discrete.h:88-89`) y `SclkDid`
(`:92`), *y* el sub-bloque `SclkSetting` con `Fcw_int`/`Fcw_frac` (`smu74_discrete.h:100`,
`:67-80`). El driver simplemente deja los legacy a cero. En cambio la struct de Tonga
(`smu72_discrete.h:47-70`) **no tiene** `SclkSetting`. O sea: la frontera es exactamente
"que version del contrato entiende el firmware", y la define el **numero de version de
microcodigo**, no la generacion de la tarjeta.

**Dos hipotesis alternativas, refutadas:**

- *"solo las de escritorio con reloj programable"* -> **REFUTADA**. Carrizo y Stoney
  (portatiles) son grupo C, sin codificacion. Y un CI portatil y una RX 5500 tienen
  ambos reloj programable, luego el criterio no discrimina.
- *"solo las que tienen VoltageLevel embebido"* -> **REFUTADA**. `SMU_VoltageLevel
  MinVoltage` aparece en la struct que usa registros (`smu72_discrete.h:48`) y en la que
  usa FCW (`smu74_discrete.h:84`). No discrimina en absoluto.

**Hay una subfrontera adicional, distinta, en reloj de memoria.** El contrato de memoria
pierde los registros MPLF ya en Fiji (SMU 7.3): CI, Tonga e Iceland escriben
`MpllFuncCntl*`; Fiji y Polaris12 no escriben nada. El retorno del FCW en memoria ocurre
solo en VegaM (`vegam_smumgr.c:974-975`), y la struct que lo aloja
(`smu75_discrete.h:158-160`: `Fcw_int`, `Fcw_frac`, `Postdiv`) **no existe** en la de
Polaris12 (`smu74_discrete.h:133-152`).

En el metodo viejo, `ci_smumgr.c:362-366`:

```c
sclk->CgSpllFuncCntl3 = spll_func_cntl_3;
sclk->CgSpllFuncCntl4 = spll_func_cntl_4;
sclk->SclkDid         = (uint8_t)dividers.pll_post_divider;
```

En el nuevo, `polaris10_smumgr.c:930-934`:

```c
sclk_setting->Fcw_int  = (uint16_t)((clock << postdiv) / ref_clock);
temp  = clock << postdiv;  temp <<= 0x10;  do_div(temp, ref_clock);
sclk_setting->Fcw_frac = temp & 0xffff;
```

`CgSpllFuncCntl3/4` y `SclkDid` no son un descuido: son el **resto del metodo
anterior**, que sigue en la struct porque la struct la comparten todas las
generaciones.

Cuanto ocupan, contado sobre la tabla real:

| donde | campo | bytes | veces | subtotal |
|---|---|---:|---:|---:|
| `GraphicsLevel[8]` | `CgSpllFuncCntl3` | 4 | 8 | 32 |
| `GraphicsLevel[8]` | `CgSpllFuncCntl4` | 4 | 8 | 32 |
| `GraphicsLevel[8]` | `SclkDid` | 1 | 8 | 8 |
| `ACPILevel` | `SclkDid` | 1 | 1 | 1 |
| | | | **total** | **73** |

**73 bytes de los 1884 de la tabla** que el host deja como los encuentre. Una version
anterior de este documento decia 72: se habia contado solo `GraphicsLevel` y se habia
olvidado `ACPILevel.SclkDid`. Los dos numeros estan contados, no estimados.

## Que significa eso para un driver propio

Tres cosas, todas accionables:

1. **El metodo del reloj depende de la generacion.** Copiar el codigo de Tonga en
   Polaris12 no funciona: no es que este equivocado, es que escribe campos que ya no
   se llenan. Y copiar el de Polaris10 en Tonga tampoco.

2. **Los tres campos muertos hay que reservarlos.** Por el mismo argumento que los
   `PIDController` de `087`: si el driver propio hace la struct sin ellos, todos los
   offsets posteriores se desplazan 9 bytes por nivel y el firmware lee campos
   equivocados sin avisar. Se ignoran como contenido y se respetan como espacio.

3. **La regla de intercambio no admite excepciones ni conjeturas.** Se aplica campo a
   campo, con el ancho del campo. Los 60 campos convertidos de la tabla DPM de
   Polaris10 cumplen los 60.

## El detalle de los 60

La conversion no es solo del nivel de graficos. La tabla entera:

| zona | campos convertidos |
|---|---|
| `SclkFcwRangeTable[8]` | `fcw_pcc`, `fcw_trans_upper`, `fcw_trans_lower` (los tres, en las dos ramas) |
| `SystemFlags`, `VRConfig`, `SmioMask1/2`, `SclkStepSize`, `CurrSclkPllRange` | `UL` |
| `TemperatureLimitHigh/Low`, `VoltageResponseTime`, `PhaseResponseTime` | `US` |
| `BootVddc`, `BootVddci`, `BootMVdd` | `US` |
| `SclkSetting` completo | `SclkFrequency` en `UL`, los nueve campos de 16 en `US` |
| `VceLevel`/`SamuLevel`/`UvdLevel` | `Frequency`, `MinVoltage`, `VclkFrequency`, `DclkFrequency` en `UL` |
| `BapmVddcVidHi/LoSidd`, `tdc_limit`, `VddcOffset` | `US` |
| `LowSclkInterruptThreshold` | `UL` |

Los 60 cumplen el invariante, sin una excepcion.

## Clasificacion

- `SMC_BYTE_SWAP_RULE = PROVEN`: todo campo >1 byte se intercambia con su propio
  ancho. 63 campos de nivel comprobados, 2 excepciones.
- `SMC_BYTE_SWAP_EXCEPTIONS = PROVEN`: `CgSpllFuncCntl3` y `CgSpllFuncCntl4`, nunca
  escritas ni convertidas en la ruta Polaris10.
- `SCLK_ENCODING_GENERATION_SPLIT = PROVEN`: registros en SMU 7.0-7.3 (CI, Topaz, Tonga,
  Fiji); FCW en SMU 7.4-7.5 (Polaris10/11/12, VegaM); nada en 8.x, 9.x, 10.x y
  swsmu. **El corte es SMU 7.3 -> 7.4, no Navi.** La version anterior de este documento
  decia Navi y era falso.
- `SCLK_ENCODING_CARRIZO = REFUTED`: la version anterior atribuia Carrizo a
  `ci_smumgr.c`. Carrizo es familia CZ y usa `smu8_smu_funcs` (`hwmgr.c:127`), que no
  codifica reloj. `ci_smumgr.c` es GCN1/2.
- `SCLK_ENCODING_SPLIT_IS_FIRMWARE_VERSION = PROVEN`: la struct de Polaris12 contiene los
  campos legacy y los FCW a la vez; la de Tonga solo tiene los legacy.
- `SMC_DPM_TABLE_CONVERSIONS = PROVEN`: 60 conversiones, las 60 conformes.

## Lo que esto NO dice

No dice si el firmware lee `CgSpllFuncCntl3/4` o `SclkDid` aunque el host no los
escriba. Que no los escriba el host no significa que no los lea el firmware: puede
usarlos como salida. Es `NOT_IN_CORPUS`.

No dice por que el firmware de SMU 7.4 cambio a FCW. Que las dos codificaciones
coexistan en la struct de Polaris12 es un hecho; el motivo es arquitectura del
generador de reloj y esta en el firmware, que no esta en el corpus.

No dice nada de Arcturus, Aldebaran, Sienna, Van Gogh, Navi, Renoir ni Dimgrey mas alla
de que **no usan ninguno de los dos metodos**. Su contrato de reloj no se ha
investigado: son `swsmu`, fuera del ambito de este documento.

No hay lectura de hardware aqui.