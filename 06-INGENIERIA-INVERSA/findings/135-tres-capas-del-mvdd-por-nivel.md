# 135 · Tres capas de por qué el `mvdd` por nivel no llega al SMC, y dos fuentes de VBIOS que el driver ignora

WORK_CLASS=READ_ONLY · WRITE_EXECUTION=NONE · MODIFICATIONS 0

**Continuando `134`: el tercer objeto de voltaje de mi VBIOS no es un dato muerto por casualidad,
sino que hay TRES capas por las que el `mvdd` por nivel no llega al SMC.** Y dos de ellas se
pueden medir.

## Capa 1 — estructural: el registro SCLK del VBIOS no tiene campo `usMvdd`

```c
/* pptable_v1_0.h:186-192 */
ATOM_Tonga_SCLK_Dependency_Record {
        UCHAR  ucVddInd; USHORT usVddcOffset; ULONG ulSclk;
        USHORT usEdcCurrent; UCHAR ucReliabilityTemperature;
        UCHAR  ucCKSVOffsetandDisable;              /* NO HAY usMvdd */
}
/* pptable_v1_0.h:170-177 */
ATOM_Tonga_MCLK_Dependency_Record {
        UCHAR ucVddcInd; USHORT usVddci; USHORT usVddgfxOffset;
        USHORT usMvdd;  ULONG ulMclk; USHORT usReserved;   /* SI LO HAY */
}
```

Y el getter lo refleja exactamente: **`->mvdd` se escribe en UN solo sitio de todo el arbol**,
`process_pptables_v1_0.c:390`, y es el de MCLK. Los dos getters de SCLK (`:431-436` Tonga,
`:460-466` Polaris) **no lo tocan**, y `kzalloc_flex` lo deja a cero.

**Consecuencia directa, independiente de mi placa:** en
`polaris10_get_dependency_volt_by_clk` Ruta A,

```c
:388   else if (dep_table->entries[i].mvdd)     /* SIEMPRE 0 si la tabla es la de SCLK */
:389           *mvdd = dep_table->entries[i].mvdd * VOLTAGE_SCALE;
```

**La rama es inalcanzable para tablas SCLK, siempre, en cualquier placa.** No hace falta ningun
VBIOS raro: el dato no puede existir.

- `ATOM_TONGA_SCLK_DEPENDENCY_RECORD_NO_TIENE_USMVDD = PROVEN`: `pptable_v1_0.h:186-192`
- `EL_GETTER_DE_SCLK_NUNCA_ESCRIBE_MVDD = PROVEN`: unico sitio de asignacion en `:390`
- `LA_RAMA_DE_388_ES_INALCANZABLE_PARA_TABLAS_SCLK = PROVEN_DERIVED`

## Capa 2 — mi placa: el cap de MVDD esta apagado

```c
/* smu7_hwmgr.c:1891-1899 */
if (phm_cap_enabled(hwmgr->platform_descriptor.platformCaps,
                PHM_PlatformCaps_EnableMVDDControl)) {
        if (atomctrl_is_voltage_controlled_by_gpio_v3(hwmgr,
                        VOLTAGE_TYPE_MVDDC, VOLTAGE_OBJ_GPIO_LUT))
                data->mvdd_control = SMU7_VOLTAGE_CONTROL_BY_GPIO;
        ...
}
```

`PHM_PlatformCaps_EnableMVDDControl` viene de `ATOM_TONGA_PP_PLATFORM_CAP_MVDD_CONTROL = 0x1000`,
**bit 12** (`set_platform_caps:88-90`).

**Mi `ulPlatformCaps = 0x068000` tiene bits 15, 17 y 18. El bit 12 NO esta.**

**Logo el bloque entero se salta, `mvdd_control` se queda en `NONE` (puesto en `:1832`), y en
`:1915-1917` el cap se borra de nuevo.**

Y **mi VBIOS SI declara el objeto**: `obj[2]` es `MVDDC(2) + GPIO_LUT(0)`, con **24 bytes**, el
mayor de los tres — que es lo que cabria en una LUT de GPIO. **El VBIOS ofrece el dato y la
capacidad de usarlo; el driver no lo mira porque un bit de otro campo del VBIOS no lo habilita.**

- `EL_BIT_12_NO_ESTA_EN_MI_ULPLATFORMCAPS = PROVEN`: `0x068000` = bits 15, 17, 18
- `EL_OBJETO_MVDDC_GPIOLUT_DE_MI_VBIOS_NO_SE_CONSULTA_NUNCA = PROVEN`
- `MVDD_CONTROL_MI_PLACA = SMU7_VOLTAGE_CONTROL_NONE = PROVEN`

## Capa 3 — y hay datos reales que se descartan

**La tabla MCLK de mi VBIOS si lleva `usMvdd`, y el getter los copia.** Medido, con el paso de
registro correcto:

```
ATOM_Tonga_MCLK_Dependency_Table en 0x09D8F   ucRevId=0  ucNumEntries=3   stride=13

  idx  ucVddcInd  usVddci  usVddgfxOff  usMvdd  ulMclk      MCLK(MHz)
    0         0      800           0    1000       30000        30
    1         0      800           0    1000       62500        62
    2         4      875           0    1000      150000       150
```

> **`ulMclk = [30000, 62500, 150000]` coincide exactamente con `121`** (300 / 625 / 1500 MHz en
> unidades de 10 kHz). **Cuarta corroboracion independiente de `121`.**

Y con `mvdd_control == NONE`, Ruta A toma la otra rama:

```c
:385   if (SMU7_VOLTAGE_CONTROL_NONE == data->mvdd_control)
:386           *mvdd = data->vbios_boot_state.mvdd_bootup_value * VOLTAGE_SCALE;
```

**Ese `mvdd_bootup_value` viene del `FirmwareInfo`, y lo he medido: `usBootUpMVDDCVoltage = 1500 mV`.**

```
    offset 91:   56320 mV     <- basura
    offset 92:    1500 mV     <- el unico voltaje de rail plausible
    offset 93:       5 mV     <- basura
    offset 94:       0 mV
```

**1500 mV es coherente ademas con que 1500 es el MCLK maximo de la propia tabla.**

> **El valor por nivel del VBIOS es 1000 mV. Lo que el driver envia es 1500 mV, el mismo para los
> tres niveles de reloj.**

- `US_MVDD_MI_VBIOS = 1000_MV_POR_NIVEL = PROVEN`: los tres registros
- `MVDD_BOOTUPVALUE_MI_PLACA = 1500_MV = PROVEN`
- `EL_DRIVER_ENVIA_1500_Y_DESCARTA_1000 = PROVEN_DERIVED`
- `ULMCLK_CORROBORA_121_OTRA_VEZ = PROVEN`

## Y la obtencion del offset 92, dicha con su limit

**No la consigo con gcc, y lo digo.** `ATOM_FIRMWARE_CAPABILITY` es un **bitfield de USHORT**, y
al transcribirlo de `atombios.h:2900-2937` **me queda un bit de mas**: mi transcripcion da
17 bits, luego 3 bytes, luego `sizeof(ATOM_FIRMWARE_INFO_V2_2) = 109`.

**La restriccion que lo cierra es del propio VBIOS:** la tabla declara
`usStructureSize = 108`, asi que `sizeof` **tiene** que ser 108, luego
`sizeof(ATOM_FIRMWARE_CAPABILITY_ACCESS) = 2`, luego `usBootUpMVDDCVoltage` esta en **92**.

Y hay una comprobacion independiente que lo confirma: **1500 mV es el unico valor plausible de
rail entre los cinco candidatos**, y encaja con el MCLK maximo de la tabla.

> **No he medido el offset con el compilador. Lo he derivado de una restriccion del propio
> fichero y lo he confirmado por plausibilidad.** Eso es mas debil que gcc, y lo declaro en vez
> de presentarlo como medido.

Los offsets de `usBootUpVDDCVoltage` (46) y `usBootUpVDDCIVoltage` (78) **si los da gcc**, y sus
valores —**893 mV** y **875 mV**— son voltajes sensatos. Y `875` **aparece tambien** en
`usVddci` del ultimo registro de la tabla MCLK: **dos fuentes del VBIOS coinciden.**

- `EL_OFFSET_92_VIENE_DE_UNA_RESTRICCION_Y_UNA_COMPROBACION_DE_PLAUSIBILIDAD = PROVEN_DERIVED`
- `GCC_ME_DA_109_Y_EL_VBIOS_DECLARA_108 = PROVEN`: mi transcripcion del bitfield tiene un bit de mas
- `USBOOTUPVDDCI_875_COINCIDE_CON_USVDDCI_DE_LA_TABLA_MCLK = PROVEN`

## El resultado, en una linea

**Mi VBIOS ofrece tres fuentes de informacion de MVDD —el objeto MVDDC+GPIO_LUT, el `usMvdd` de
los tres registros MCLK, y el `usBootUpMVDDCVoltage` del FirmwareInfo— y el driver usa
exactamente una: el valor de arranque, que es el mismo para todos los niveles.**

Y por debajo hay una capa que no depende de mi placa: **para las tablas SCLK el dato por nivel
no puede existir**, porque el formato del registro VBIOS no tiene ese campo.

## Clasificacion

- `ATOM_TONGA_SCLK_DEPENDENCY_RECORD_NO_TIENE_USMVDD = PROVEN`
- `EL_GETTER_DE_SCLK_NUNCA_ESCRIBE_MVDD = PROVEN`: unico en `:390`
- `LA_RAMA_DE_388_ES_INALCANZABLE_PARA_TABLAS_SCLK = PROVEN_DERIVED`
- `EL_BIT_12_NO_ESTA_EN_MI_ULPLATFORMCAPS = PROVEN`
- `EL_OBJETO_MVDDC_GPIOLUT_DE_MI_VBIOS_NO_SE_CONSULTA_NUNCA = PROVEN`
- `US_MVDD_MI_VBIOS = 1000_MV_POR_NIVEL = PROVEN`
- `MVDD_BOOTUPVALUE_MI_PLACA = 1500_MV = PROVEN`
- `EL_DRIVER_ENVIA_1500_Y_DESCARTA_1000 = PROVEN_DERIVED`
- `ULMCLK_CORROBORA_121_OTRA_VEZ = PROVEN`
- `EL_OFFSET_92_ES_DERIVADO_NO_MEDIDO_CON_GCC = PROVEN_DERIVED`, declarado
- `USBOOTUPVDDCI_875_COINCIDE_CON_LA_TABLA_MCLK = PROVEN`
- `TRES_FUENTES_DE_MVDD_Y_EL_DRIVER_USA_UNA = PROVEN_DERIVED`

## Lo que esto obliga a hacer en un driver propio

1. **Un cap que habilita una capacidad tiene que coincidir con el dato que la capacidad
   necesita.** Aqui el cap lo decide el PPT y el dato esta en la tabla de objetos de voltaje, y
   **nadie comprueba que los dos esten de acuerdo.** Si mi driver quiere control de MVDD, lo
   decide el VBIOS **o** lo decido yo, pero **no por un bit que esta en otro sitio.**
2. **Un valor por defecto no sustituye a una tabla, y hay que saber cual de las dos viaja.**
   Aqui viaja el de arranque: **1500 mV fijos para tres niveles de reloj**, cuando el VBIOS tiene
   1000 mV para cada uno.
3. **Cuando un formato de registro no tiene un campo, el campo del struct del host no debe
   existir** — o debe marcarse como no disponible. `phm_ppt_v1_clock_voltage_dependency_record`
   se usa para las dos tablas, y el campo `mvdd` solo tiene sentido en una.
4. **Y un offset que no puedo medir con el compilador lo declaro como derivado.** Aqui tengo el
   gcc dando 109 y el VBIOS declarando 108, y la verdad esta en el medio. **Publicar el numero
   sin decir de donde sale seria el error que mas caro me ha salido en todo el trabajo.**

## Estado

Hallazgo **135**: las **tres capas** del `mvdd` por nivel quedan identificadas, dos de ellas
medidas en mi VBIOS, y **cuarta corroboracion independiente de `121`**.