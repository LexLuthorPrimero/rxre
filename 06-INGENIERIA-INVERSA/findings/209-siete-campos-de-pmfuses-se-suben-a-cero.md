# 209  Siete campos de configuración real se suben a cero en la tabla de PMFuses, y no es una omisión de Polaris12

WORK_CLASS=READ_ONLY · WRITE_EXECUTION=NONE · MODIFICATIONS 0

## Que copia la funcion, y que hay dentro

`polaris10_populate_pm_fuses` (`:604-662`) rellena `smu_data->power_tune_table` y la
sube en `:654-656`:

```c
if (smu7_copy_bytes_to_smc(hwmgr, pm_fuse_table_offset,
                (uint8_t *)&smu_data->power_tune_table,
                (sizeof(struct SMU74_Discrete_PmFuses) - 92), SMC_RAM_END))
```

`sizeof(SMU74_Discrete_PmFuses) = 176` y `offsetof(VFT_ATE) = 92`, los dos **medidos con
gcc**, no deducidos:

```
sizeof(SMU74_Discrete_PmFuses)   gcc = 176
offsetof(BapmVddCVidHiSidd)     gcc = 0
offsetof(BapmVddCVidLoSidd)     gcc = 8
offsetof(VddCVid)               gcc = 16
offsetof(VFT_ATE)               gcc = 92
```

O sea: copia los offsets **0 a 83**, 84 bytes, y corta exactamente donde empieza `VFT_ATE`.
El truncamiento es correcto y deliberado.

## El reparto de los 84 bytes, campo por campo

Clasificado sobre las 25 entradas que caen en el rango copiado. La distincion que
importa es entre *escrito con un valor real*, *puesto a cero a proposito* y *nunca
tocado*, porque tienen consecuencias distintas:

| offset | bytes | campo | estado |
|---:|---:|---|---|
| 0 | 8 | `BapmVddCVidHiSidd` | **nunca tocado** |
| 8 | 8 | `BapmVddCVidLoSidd` | **nunca tocado** |
| 16 | 8 | `VddCVid` | **nunca tocado** |
| 24 | 1 | `SviLoadLineEn` | valor real |
| 25 | 1 | `SviLoadLineVddC` | valor real |
| 26 | 1 | `SviLoadLineTrimVddC` | 3 (constante) |
| 27 | 1 | `SviLoadLineOffsetVddC` | 0 |
| 28 | 2 | `TDC_VDDC_PkgLimit` | valor real |
| 30 | 1 | `TDC_VDDC_ThrottleReleaseLimitPerc` | valor real |
| 31 | 1 | `TDC_MAWt` | valor real |
| 32 | 1 | `TdcWaterfallCtl` | valor real |
| 33 | 1 | `LPMLTemperatureMin` | valor real |
| 34 | 1 | `LPMLTemperatureMax` | valor real |
| 35 | 1 | `Reserved` | valor real (relleno) |
| 36 | 16 | `LPMLTemperatureScaler` | **cero a proposito**, con comentario |
| 52 | 2 | `FuzzyFan_ErrorSetDelta` | **nunca tocado** |
| 54 | 2 | `FuzzyFan_ErrorRateSetDelta` | **nunca tocado** |
| 56 | 2 | `FuzzyFan_PwmSetDelta` | valor real |
| 58 | 2 | `Reserved6` | nunca tocado (reservado) |
| 60 | 16 | `GnbLPML` | **cero a proposito**, con comentario |
| 76 | 1 | `GnbLPMLMaxVid` | **nunca tocado** |
| 77 | 1 | `GnbLPMLMinVid` | **nunca tocado** |
| 78 | 2 | `Reserved1` | nunca tocado (reservado) |
| 80 | 2 | `BapmVddCBaseLeakageHiSidd` | valor real |
| 82 | 2 | `BapmVddCBaseLeakageLoSidd` | valor real |

**16 con valor real, 2 puestos a cero a proposito, 9 nunca tocados.** De esos 9, dos son
`Reserved6` y `Reserved1`, que no son configuracion. Quedan **7 campos de configuracion
real** que se suben como cero, de forma **incondicional**: no dependen de ningun contador
del VBIOS. Ocurren en el 100 por ciento de las ejecuciones donde la funcion corra.

## Y la distincion que evita un informe equivocado

De esos 7, **ninguno es una omision de Polaris12**:

| campo | polaris10 | tonga | iceland | ci |
|---|---:|---:|---:|---:|
| `BapmVddCVidHiSidd` | 0 | 0 | 1 | 3 |
| `BapmVddCVidLoSidd` | 0 | 0 | 1 | 2 |
| `VddCVid` | 0 | 0 | 1 | 1 |
| `FuzzyFan_ErrorSetDelta` | 0 | 0 | 0 | 0 |
| `FuzzyFan_ErrorRateSetDelta` | 0 | 0 | 0 | 0 |
| `GnbLPMLMaxVid` | 0 | 0 | 0 | 1 |
| `GnbLPMLMinVid` | 0 | 0 | 0 | 0 |

Los tres `FuzzyFan` de error **no los escribe ninguna de las cuatro rutas**. Los tres VID
solo los escribe la familia CI, que es GCN1/2. Y `GnbLPMLMaxVid`/`MinVid` solo la CI.

Una version anterior de este documento decia que "Tonga e Iceland calculan los VID".
**Es falso: Tonga tiene cero apariciones.** Verificado por busqueda exacta en las cuatro
rutas.

Eso cambia la conclusion de forma importante: **no es un defecto de implementacion, es un
contrato de generacion**. Los campos que SMU 7.4 no rellena son los que el firmware de
SMU 7.4 no espera, porque la familia CI los necesita y SMU 7.x no. Un campo que nadie
escribe durante cuatro generaciones de ruta no es un olvido: es que no aplica.

## Lo que si es un hecho, y como hay que formularlo

**`PROVEN`**: siete campos de configuracion del `SMU74_Discrete_PmFuses` se suben a la
SRAM del SMC con valor cero en la ruta de Polaris12, de forma incondicional.

**`NOT_DETERMINED`**: que hace el firmware con ellos. Que no se rellenen en cuatro rutas
distintas es un indicio fuerte de que no los usa, pero un indicio no es una prueba. Lo
correcto para un driver propio es **reproducir el contrato** (no rellenar lo que upstream
no rellena) y dejarlo escrito como decision, no como olvido.

**`SEMANTIC_MISSING`**: si el firmware de esta placa concreta, que es un microcodigo
concreto con sus propios fuses, lee o no esos campos.

## Y un metodo que me fallo, y que hay que registrar

Mi primer barrido dio "11 campos sin escribir", y luego "9". Los dos numeros estaban
mal por un fallo mio en el clasificador: la expresion regular buscaba `campo =` y **no
cascaba con la asignacion dentro de un bucle con indice**, o sea
`power_tune_table.GnbLPML[i] = 0;`.

Ese `= 0` es justo el caso que mas importa distinguir, porque es "puesto a cero a
proposito" y no "nunca tocado". Lo que lo resolucue fue ir al codigo y leer las dos
funciones:

```c
static int polaris10_populate_temperature_scaler(struct pp_hwmgr *hwmgr)
{
        /* Currently not used. Set all to zero. */
        for (i = 0; i < 16; i++)
                smu_data->power_tune_table.LPMLTemperatureScaler[i] = 0;
```

Idem `polaris10_populate_gnb_lpml`. **El comentario lo dice explicitamente.** Es una
decision declarada y documentada, no un descuido.

Leccion: **una herramienta que clasifica "escrito" frente a "no escrito" tiene que
distinguir tambien "escrito con cero a proposito"**, y un barrido automatico que no lo
hace produce exactamente el informe equivocado: acusa de omision lo que es una decision.

## Clasificacion

- `PMFUSES_COPY_IS_84_BYTES = PROVEN_DERIVED`: `176 - 92`, con ambos numeros de gcc, y
  `offsetof(VFT_ATE) = 92` confirma que el corte es deliberado.
- `PMFUSES_TWENTY_FIVE_FIELDS_IN_RANGE = PROVEN_DERIVED`: offsets 0-83, contados desde el
  layout con gcc como referencia.
- `PMFUSES_SEVEN_CONFIG_FIELDS_UNWRITTEN = PROVEN`: los tres VID, dos `FuzzyFan` de error
  y `GnbLPMLMaxVid`/`MinVid`. Incondicional, sin dependencia de contadores.
- `PMFUSES_TWO_FIELDS_ZERO_ON_PURPOSE = PROVEN`: `LPMLTemperatureScaler` y `GnbLPML`, con
  el comentario `Currently not used. Set all to zero.`
- `PMFUSES_NOT_A_POLARIS10_OMISSION = PROVEN`: Tonga e Iceland tampoco escriben los VID
  (0 apariciones); los tres `FuzzyFan` de error no los escribe ninguna de las cuatro rutas.
  **Refuta** la afirmacion de que Tonga e Iceland los calculan.
- `PMFUSES_FIRMWARE_USE_UNKNOWN = NOT_DETERMINED`: la ausencia en cuatro rutas es un
  indicio de que no aplican, no una prueba. `SEMANTIC_MISSING` para el firmware concreto.

## La guarda que envuelve todo esto

Toda la funcion esta bajo `if (phm_cap_enabled(...,
PHM_PlatformCaps_PowerContainment))` (`:609-610`). Si esa capability no esta activa,
**la copia no ocurre en absoluto** y la tabla que dejo el firmware queda intacta.

Ese es el camino seguro. Y hace que el hallazgo tenga una condicion de alcance que hay que
decir: los 84 bytes a cero solo se suben si PowerContainment esta activo. Si el PPT de
esta placa no lo activa, la tabla que hay en la SRAM es la que puso el firmware, no una
tabla de ceros.

El valor efectivo de esa capability es `RUNTIME_MISSING`: viene de
`powerplay_table->ulPlatformCaps` del VBIOS.
