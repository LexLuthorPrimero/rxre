# 132 · ClockStretcher: cuatro condiciones, tres medidas, y la ruta está VIVA en mi placa con margen cero en dos sitios

WORK_CLASS=READ_ONLY · WRITE_EXECUTION=NONE · MODIFICATIONS 0

**La primera ruta de código que confirmo que se ejecuta en mi ASIC en toda la tanda, y con
margen cero en dos arrays.** Cierra los 13 escrituras registro-a-registro que llevaba pendientes
desde el principio de la sesion, y contiene una correccion mia de la clase "offset estimado en
vez de calculado".

## Las cuatro condiciones, y su estado

```c
/* smu7_hwmgr.c:1939-1942 */
if ((hwmgr->pp_table_version != PP_TABLE_V0) && (hwmgr->feature_mask & PP_CLOCK_STRETCH_MASK)
        && (table_info->cac_dtp_table->usClockStretchAmount != 0))
        phm_cap_set(hwmgr->platform_descriptor.platformCaps, PHM_PlatformCaps_ClockStretcher);
```

| condicion | como se decide | valor en mi placa |
|---|---|---|
| 1 · `pp_table_version != PP_TABLE_V0` | `hwmgr->pp_table_version` | **V1**, se cumple |
| 2 · `feature_mask & PP_CLOCK_STRETCH_MASK` | `0x400` contra `amdgpu_pp_feature_mask` | **`0xfff7bfff & 0x400 = 0x400`**, se cumple |
| 3 · `usClockStretchAmount != 0` | tabla PowerTune del VBIOS | **MEDIDO: 2** |
| 4 · no lo borra `atomctrl_is_asic_internal_ss_supported` | tabla `ASIC_InternalSS_Info` de ATOM | **MEDIDO: presente en 0xa824** |

### La 2, en detalle

```c
/* amdgpu_drv.c:202 */
uint amdgpu_pp_feature_mask = 0xfff7bfff;
/* amdgpu_device.c:2021-2027 */
adev->pm.pp_feature = amdgpu_pp_feature_mask;
adev->pm.pp_feature &= ~PP_GFXOFF_MASK;       /* 0x8000 */
adev->pm.pp_feature &= ~PP_OVERDRIVE_MASK;    /* 0x4000 */
adev->pm.pp_feature &= ~PP_PCIE_DPM_MASK;     /* 0x0004 */
```

`PP_CLOCK_STRETCH_MASK = 0x400` (`amd_shared.h:226`), y **ninguno de los tres que se borran es
0x400**, luego el bit sobrevive. `PP_CLOCK_STRETCH_MASK` **solo se lee en todo el arbol**, nunca
se escribe: es un modulo, y `amdgpu_drv.c:499` lo expone como `ppfeaturemask`.

### La 4, y por que «presente» basta

`atomctrl_is_asic_internal_ss_supported` (`ppatomctrl.c:824`) solo pregunta si la tabla sale no
NULL. Y el parser **no valida la revision**:

```c
/* atom.c:1642-1660 */
bool amdgpu_atom_parse_data_header(struct atom_context *ctx, int index, ...)
{
        int idx = CU16(ctx->data_table + index * 2 + 4);
        if (!mdt[index])
                return false;                 /* <-- lo UNICO que comprueba */
        ...
        return true;
}
```

Localizando la tabla con la herramienta del otro agente —**ejecutada, no modificada**—:

```
MASTER DATA TABLE en 0x97f2
   5   FirmwareInfo                  0x9974   size=108    rev=2.2
  16   PowerPlayInfo                 0x9c0a   size=778    rev=7.1
  27   ASIC_InternalSS_Info          0xa824   size=40     rev=3.1
  presentes: 21 | offset 0 (ausentes): 14
```

**`ASIC_InternalSS_Info` esta presente en 0xa824**, luego la condicion 4 se cumple.

**Y de paso: `PowerPlayInfo @ 0x9c0a`, que es mi ancla de la sesion, queda confirmada por una via
independiente.**

**Las cuatro se cumplen ⟹ `polaris10_populate_clock_stretcher_data_table` se ejecuta en mi
placa.** Y `usClockStretchAmount = 2` pasa el rango valido (`!= 0 && <= 5`).

## Margen cero en dos sitios, dentro de la ruta viva

```c
/* polaris10_smumgr.c:1671-1691 */
for (i = 0; i < sclk_table->count; i++) {
        smu_data->smc_state_table.Sclk_CKS_masterEn0_7 |=
                        sclk_table->entries[i].cks_enable << i;      /* :1672 */
        ...
        smu_data->smc_state_table.Sclk_voltageOffset[i] = volt_offset;   /* :1690 */
}
```

`sclk_table->count` es el `ucNumEntries` del VBIOS. Y:

```c
/* smu74_discrete.h:358 y :362 */
uint8_t  Sclk_CKS_masterEn0_7;      <-- un BYTE, y se desplaza << i
uint8_t  Sclk_voltageOffset[8];     <-- ocho, y se indexa con i
```

**Dos consecuencias distintas, y las dos con margen cero en mi placa:**

1. **`Sclk_voltageOffset[i]` para `i` hasta `count - 1`.** Con `count = 8` —lo que declara mi
   VBIOS (`121`)— el bucle escribe exactamente los 8. **Un noveno reloj de dependencia
   escribiria 8 bytes pasto el array**, y lo que hay detras es `LdoRefSel` y el resto de
   `SMU74_SoftRegisters`, que van al SMC.
2. **`cks_enable << i` sobre un `uint8_t`.** El **nombre del campo dice 0 a 7**, y el bucle no
   comprueba nada. Con `i >= 8` los bits se pierden; con `i >= 32` el desplazamiento es
   indefinido segun C.

**Ninguno de los dos mira la capacidad.** Es `224` (antes `120`) y `229` (antes `128`) por tercera vez, ahora en el registro
de datos del ClockStretcher, y en una ruta **que si corre en mi placa**.

- `SCLK_VOLTAGE_OFFSET_8_Y_MI_VBIOS_DECLARA_8 = PROVEN`: margen cero, `smu74_discrete.h:362` y `121`
- `SCLK_CKS_MASTEREN0_7_ES_UN_BYTE_Y_SE_DESPLAZA_HASTA_COUNT_MENOS_1 = PROVEN`: `smu74_discrete.h:358`
- `EL_NOMBRE_DEL_CAMPO_DICE_0_A_7_Y_NADA_LO_COMPRUEBA = PROVEN`

## Y el `stretch_amount` se valida y se tira

`usClockStretchAmount = 2` lo aporta el VBIOS. En el codigo aparece **tres veces**:

```
:1659   uint8_t i, stretch_amount, volt_offset = 0;                  <-- declarado
:1661   stretch_amount = (uint8_t)table_info->cac_dtp_table->usClockStretchAmount;
:1696   if (stretch_amount == 0 || stretch_amount > 5) { ... }
```

**Y a partir de ahi, nada.** Lo unico que se escribe en un registro es:

```c
/* polaris10_smumgr.c:1704-1706 */
value = cgs_read_ind_register(hwmgr->device, CGS_IND_REG__SMC, ixPWR_CKS_CNTL);
value &= 0xFFFFFFFE;                       /* borra el bit 0 */
cgs_write_ind_register(hwmgr->device, CGS_IND_REG__SMC, ixPWR_CKS_CNTL, value);
```

**Un read-modify-write que borra un bit. El importe de estiramiento no llega a ningun
registro.**

**Lo que no puedo determinar, y no voy a afirmar:** si el SMC deduce la cantidad desde
`Sclk_CKS_masterEn0_7`, o si el bit 0 de `ixPWR_CKS_CNTL` es un habilitador y el importe viaja
por el registro de mensaje. **Es comportamiento del firmware, y `DPM-BASE-EN-SMC` sigue
`NOT_AVAILABLE`.** Lo que si es demostrable es que **el host no lo escribe**, y que
`ixPWR_CKS_CNTL` **no esta declarado en ninguna cabecera de mi corpus** — solo se usa en los
`.c` de smu7 y fiji.

- `STRETCH_AMOUNT_SE_VALIDA_Y_NO_LLEGA_A_NINGUN_REGISTRO = PROVEN`: tres apariciones, ninguna
  de escritura
- `IXPWR_CKS_CNTL_NO_ESTA_DECLARADO_EN_MI_CORPUS = PROVEN_DERIVED`
- `SI_EL_SMC_LO_DEDUCE_ES_COMPORTAMIENTO_DE_FIRMWARE = NOT_AVAILABLE`

## El contraste con `228` (antes `126`), que es lo que quiero copiar

`228` (antes `126`) encontro `polaris10_smumgr.c:1729`:

```c
} else {
        PP_ASSERT_WITH_CODE(false, "VDDC should be on SVI2 control in merged mode!", );
}
```

**Condicion literal `false` y tercer argumento VACIO: se dispara siempre y no hace nada.**

Y aqui, en `:1699`, a treinta lineas de distancia, **el mismo idiom**:

```c
PP_ASSERT_WITH_CODE(false,
                "Stretch Amount in PPTable not supported",
                return -EINVAL);
```

**El tercero es `return -EINVAL`, y ese si aborta.**

> **El mismo `false` literal, con accion y sin accion. Lo que decide no es la condicion, es el
> tercer argumento** — que es exactamente lo que `228` (antes `126`) demostro con los 1093 asserts, y aqui se
> ve en dos lineas del mismo fichero.

- `EL_FALSE_LITERAL_ES_INERTE_SIN_ACCION_Y_ABORTA_CON_ACCION = PROVEN`: `:1699` frente a `:1729`

## Mi correccion: un offset ESTIMADO en vez de CALCULADO

Leyendo la tabla PowerTune calcule el destino en `PPT + 34`, **porque afirmé que era el
siguiente campo a `usUlvVoltageOffset`.** No lo es. Salio `0x4D00 = 19712`, que apunta a
`0xE90A`, **mas alla del fin del VBIOS (58880 bytes = 0xE5C0).**

**Un destino fuera del fichero es la senal de que el offset estaba mal, y lo use como tal.**

Leida la lista de campos completa, `usPowerTuneTableOffset` esta en el offset **57**:

```
 off  campo                            valor    destino       contraste
  35  usStateArrayOffset               0x004D   0x09C57       (131, coherente)
  43  usMclkDependencyTableOffset      0x0185   0x09D8F       121 dice 0x9D8F  COINCIDE
  45  usSclkDependencyTableOffset      0x010B   0x09D15       121 dice 0x9D15  COINCIDE
  47  usVddcLookupTableOffset          0x0077   0x09C81
  49  usVddgfxLookupTableOffset        0x00C9   0x09CD3       123 dice 0x9CD3  COINCIDE
  51  usMMDependencyTableOffset        0x01AE   0x09DB8       121 dice 0x9DB8  COINCIDE
  57  usPowerTuneTableOffset           0x02A1   0x09EAB       PowerTune @ 0x9EAB  COINCIDE
```

**Cinco destinos coinciden con mediciones previas mias, independientes.** Eso valida la cadena
entera de offsets, y por tanto el 57.

> **Un offset solo es real si se calcula. Estimar "el siguiente campo" produce un numero
> plausible que puede apuntar fuera del fichero.** Y aqui el fallo fue visible: una direccion
> mas alla del final.

- `MI_OFFSET_34_ERA_UN_ESTIMACION_Y_APUNtaba_FUERA_DEL_VBIOS = CORRECTED`
- `LA_CADENA_DE_OFFSETS_QUEDA_VALIDADA_POR_5_MEDICIONES_PREVIAS = PROVEN`

## La medicion que lo cierra

```
usPowerTuneTableOffset = 0x02A1  ->  ATOM_Fiji_PowerTune_Table en 0x9EAB
ucRevId = 4          ->  la RAMA >= 4, no la de Fiji ni la de Tonga
usClockStretchAmount = 2         ->  != 0     *** LA CONDICION QUE FALTA ***
usTjMax = 93                     ->  coincide con 118
usEDCLimit = 0
```

**Y un dato que no buscaba: `ucRevId = 4`**, o sea que mi placa entra en la tercera rama de
`get_cac_tdp_table` (`:586` `< 3`, `:613` `< 4`, y el resto). **No es la de "Fiji and newer" que
sugeria el comentario.** Mi VBIOS es revisin 4 de la tabla PowerTune.

## Clasificacion

- `LAS_CUATRO_CONDICIONES_SE_CUMPLEN = PROVEN`: dos del codigo, **dos medidas**
- `FEATURE_MASK_TIENE_EL_BIT_0X400_Y_NADIE_LO_BORRA = PROVEN`: `0xfff7bfff`, y los tres que se
  borran son 0x4, 0x4000 y 0x8000
- `EL_PARSER_NO_VALIDA_LA_REVISION_SOLO_EL_OFFSET = PROVEN`: `atom.c:1650`
- `ASIC_INTERNAL_SS_INFO_PRESENTE_EN_MI_VBIOS = PROVEN`: `0xa824`, rev 3.1
- `LA_RUTA_CLOCKSTRETCHER_SE_EJECUTA_EN_MI_PLACA = PROVEN_DERIVED`
- `SCLK_VOLTAGE_OFFSET_8_CON_8_RELOJES = PROVEN`: margen cero, ruta viva
- `SCLK_CKS_MASTEREN0_7_UN_BYTE_DESPLAZADO_HASTA_COUNT_MENOS_1 = PROVEN`: margen cero, ruta viva
- `STRETCH_AMOUNT_SE_VALIDA_Y_NO_LLEGA_A_NINGUN_REGISTRO = PROVEN`
- `EL_FALSE_LITERAL_ABORTA_SI_TERCEER_ARGUMENTO_TIENE_ACCION = PROVEN`: `:1699` frente a `:1729`
- `MI_OFFSET_ESTIMADO_APUNTOBA_FUERA_DEL_VBIOS = CORRECTED`
- `CADENA_DE_OFFSETS_VALIDADA_POR_5_MEDICIONES_PREVIAS = PROVEN`
- `POWERPLAYINFO_CONFIRMADO_POR_VIA_INDEPENDIENTE = PROVEN`: master table en 0x97f2
- `MI_POWER_TUNE_UCREVID_ES_4_NO_FIJI = PROVEN`: la rama real no es la que dice el comentario

## Lo que esto obliga a hacer en un driver propio

1. **El margen cero se comprueba al escribir, no al declarar.** `Sclk_voltageOffset[8]` con 8
   relojes funciona hoy y falla con el noveno. **Mi array lo dimensiono por el maximo que
   acepto, no por el que hoy viene.**
2. **Cuando el nombre de un campo declara su rango, ese rango es el que hay que comprobar.**
   `Sclk_CKS_masterEn0_7` dice 0 a 7 en su nombre. **Es documentacion ejecutable, y aqui no la
   lee nadie.**
3. **Un dato del VBIOS que se valida y luego se tira es una decision, no un olvido — pero hay
   que decidirla.** Si el importe de estiramiento no lo aplica el host, entonces el campo del
   VBIOS **no hace nada**, y eso deberia estar escrito. **No lo esta en ninguna parte.**
4. **Un `assert` con accion y el mismo sin accion, en el mismo fichero, es el mapa de lo que hay
   que revisar.** Dos lineas, treinta lineas de distancia, y la diferencia es un tercer
   argumento.
5. **Y no estimo offsets.** Cinco mediciones previas independientes validan mi cadena; un destino
   fuera del fichero habría invalidado las cinco si no lo hubiera comprobado.

## Estado

Hallazgo **132**: la ruta de **ClockStretcher queda confirmada VIVA en mi placa**, con margen cero
en dos arrays, y los 13 registros pendientes quedan reducidos a dos con contenido real
(`ixPWR_CKS_CNTL` y `ixCG_ULV_PARAMETER`).