# 134 · La incognita de `133` resuelta: existe un objeto VDDC/SVID2, y produce VddcPhase = 3 sobre una entrada que parece sin rellenar

WORK_CLASS=READ_ONLY · WRITE_EXECUTION=NONE · MODIFICATIONS 0

**Resuelve la unica incognita que `133` dejo declarada, por medicion.** Y el resultado es
mas interesante de lo que esperaba: la tabla de objetos de voltaje de mi VBIOS **esta a cero en
los campos que el driver lee como autoritativos.**

## La tabla, recorrida como lo hace el codigo

`atomctrl_lookup_voltage_type_v3` (`ppatomctrl.c:263-283`) camina la tabla por el `usSize` de
cada entrada, hasta el `usStructureSize` de la cabecera. Con
`ATOM_VOLTAGE_OBJECT_HEADER_V3` de 4 bytes (`atombios.h:5110-5114`: `ucVoltageType`,
`ucVoltageMode`, `usSize`), se reproduce exacto sobre mi VBIOS:

```
ATOM_VOLTAGE_OBJECT_INFO_V3_1 en 0xA7F0   (atomrom lo situa ahi, size=52, rev=3.1)

  usStructureSize = 52   ucTableFormatRevision = 3   ucTableContentRevision = 1

  obj[0]  offset= 4   VDDC (1)  + SVID2 (7)     usSize = 12
  obj[1]  offset=16   VDDCI (4) + SVID2 (7)     usSize = 12
  obj[2]  offset=28   MVDDC (2) + GPIO_LUT (0)  usSize = 24
```

**`4 + 12 + 12 + 24 = 52 = usStructureSize`. Exactamente.**

**Y son tres objetos, que es exactamente el `asVoltageObj[3]` declarado** (`atombios.h:5230`).

> **Eso valida la decodificacion por dentro dos veces**: el total cuadra con la cabecera, y el
> numero de entradas cuadra con el array declarado. Un offset equivocado daria otra cosa.

- `MI_VBIOS_DECLARA_TRES_OBJETOS_DE_VOLTAJE = PROVEN`: `0xA7F4`, `0xA7F8`, `0xA7FC`
- `EL_TOTAL_CUADRA_CON_USSTRUCTURESIZE = PROVEN`: 4+12+12+24 = 52
- `TRES_ENTRADAS_TRES_SLOTS_DECLARADOS = PROVEN`: margen cero en otro eje

## Y hay un VDDC/SVID2, luego la cadena corre entera

```c
/* smu7_hwmgr.c:1876-1878 */
if (atomctrl_is_voltage_controlled_by_gpio_v3(hwmgr, VOLTAGE_TYPE_VDDC, VOLTAGE_OBJ_SVID2))
        data->voltage_control = SMU7_VOLTAGE_CONTROL_BY_SVID2;
```

Como `obj[0]` es VDDC + SVID2, **ese lookup tiene exito** y
`voltage_control = SMU7_VOLTAGE_CONTROL_BY_SVID2`.

**Con eso se cumple la condicion de `:1929`, `atomctrl_get_svi2_info` se ejecuta en `:1930`, y la
cadena de `VddcPhase` corre entera en mi placa.**

## Los bits no son un parametro de hardware: son los enable de las fases SVI2

Aqui esta la parte que cambia la lectura. La cabecera de la struct **documenta el layout**:

```c
/* atombios.h:5178-5190 */
typedef struct  _ATOM_SVID2_VOLTAGE_OBJECT_V3
{
    ATOM_VOLTAGE_OBJECT_HEADER_V3 sHeader;
// 14:7 - PSI0_VID
//    6 - PSI0_EN
//    5 - PSI1
//  4:2 - load line slope trim.
//  1:0 - offset trim,
    USHORT   usLoadLine_PSI;
    UCHAR    ucSVDGpioId;
    UCHAR    ucSVCGpioId;
    ULONG    ulReserved;
```

**Y `smu7_hwmgr.c:1932` extrae exactamente los bits 5 y 6**, que son **`PSI1` y `PSI0_EN`**.

> **Lo que el driver llama `vddc_phase_shed_control` no es un parametro misterioso: son los dos
> bits de habilitacion de fase del regulador SVI2.** El nombre no lo dice, y la unica
> documentacion esta en la cabecera del VBIOS, no en el codigo.

## El valor, calculado con numeros de mi VBIOS

```
usLoadLine_PSI = 0x0012  (18)

    bits 14:7   PSI0_VID      = 0x00
    bit  6      PSI0_EN       = 0
    bit  5      PSI1          = 0
    bits 4:2    slope trim    = 4
    bits 1:0    offset trim   = 2

    ucSVDGpioId = 0        ucSVCGpioId = 0

smu7_hwmgr.c:1932          tmp3 = (18 >> 5) & 0x3   = 0
smu7_hwmgr.c:1933          swap de bits               = 0
polaris10_smumgr.c:798     VddcPhase = 0 ^ 3         = 3
```

**`VddcPhase = 3` en mi placa.**

- `US_LOAD_LINE_PSI_MI_VBIOS = 0x0012 = PROVEN`
- `BIT_5_Y_6_SON_PSI1_Y_PSI0_EN = PROVEN`: lo dice la cabecera, `atombios.h:5182-5183`
- `VDDCPHASE_MI_PLACA = 3 = PROVEN`: `tmp3` es `uint16_t` (`smu7_hwmgr.c:1810`), que coincide con
  `uint16_t *load_line`

## Y aqui esta el hallazgo de verdad: el VBIOS pone a cero lo que el driver usa como autoritativo

El driver **tiene un valor por defecto sensato**:

```c
/* smu7_hwmgr.c:1923 */
data->vddc_phase_shed_control = 1;              /* por defecto: control de fase activo */
```

Y despues, si hay un objeto SVID2, **lo sustituye por los bits del VBIOS** — sin comprobar nada:

```
:1923   vddc_phase_shed_control = 1
:1924   if (chip is POLARIS12 | P20 | P21 | P30 | P31) {
:1929       if (voltage_control == BY_SVID2) {
:1930           atomctrl_get_svi2_info(..., &tmp3);
:1932           tmp3 = (tmp3 >> 5) & 0x3;
:1933           vddc_phase_shed_control = ((tmp3 << 1) | (tmp3 >> 1)) & 0x3;
```

**En mi placa los bits son 0, luego el valor por defecto `1` se convierte en `0`, y `VddcPhase`
sale `3`.**

**Y la entrada parece sin rellenar:** `PSI0_VID = 0`, `PSI0_EN = 0`, `PSI1 = 0`, y
`ucSVDGpioId = ucSVCGpioId = 0` — dos senales distintas en el mismo GPIO 0. El comentario dice
«0~31, 0 means GPIO0», asi que cero es un valor legal, pero **los tres campos a cero juntos
parecen un marcador de posicion, no un dato.**

**El driver no distingue «el VBIOS no relleno esto» de «el VBIOS dice que las dos fases estan
deshabilitadas».** Toma los ceros como respuesta valida y **sobrescribe su propio valor por
defecto con ellos**.

- `EL_DEFECTO_1_LO_SOBRESCRIBE_EL_VBIOS_SIN_COMPROBAR = PROVEN`: `:1923` frente a `:1932-1933`
- `NO_HAY_NINGUNA_COMPROBACION_DE_QUE_LA_ENTRADA_SEA_VALIDA = PROVEN`
- `LA_ENTRADA_MI_VBIOS_PARECE_SIN_RELLENAR = PROVEN_DERIVED`: tres campos a cero y dos GPIO iguales

**Lo que NO puedo determinar, y no afirmo:** si `VddcPhase = 3` es el valor correcto para el SMC.
Eso es comportamiento de firmware, y `DPM-BASE-EN-SMC` sigue `NOT_AVAILABLE`. **Lo demostrable es
que el host envia 3, y que lo deduce de una entrada con los bits a cero.**

## Corroboracion de `122` de punta a punta

`obj[1]` es **VDDCI(4) + SVID2(7)**. Eso recorre la cadena entera de `122`:

```
ATOM_TONGA_PP_PLATFORM_CAP_VDDCI_CONTROL = 0x8000, bit 15 de ulPlatformCaps = 0x068000  -> SET
   -> set_platform_caps:94-96      phm_cap_set(PHM_PlatformCaps_ControlVDDCI)
   -> smu7_hwmgr.c:1905            phm_cap_enabled(ControlVDDCI)         -> cierto
   -> :1910-1912                   atomctrl_is_voltage_controlled_by_gpio_v3(VDDCI, SVID2)
   -> obj[1] es VDDCI+SVID2        -> CIERTO
   -> :1912                        data->vddci_control = BY_SVID2
   -> :1919-1921                   NO se hace phm_cap_unset(ControlVDDCI)
```

**`122` queda confirmado de punta a punta, y con una via que no habia usado**: no solo el bit del
PPT, sino que **la tabla de objetos de voltaje contiene el objeto que el bit anuncia.**

- `EL_CAP_CONTROLVDDCI_LO_CONFIRMA_UN_SEGUNDO_VBIOS_INDEPENDIENTE = PROVEN`

## Clasificacion

- `LA_INCOGNITA_DE_133_QUEDA_RESUELTA = PROVEN`: hay un VDDC/SVID2
- `MI_VBIOS_TIENE_TRES_OBJETOS_DE_VOLTAJE = PROVEN`: VDDC/SVID2, VDDCI/SVID2, MVDDC/GPIO_LUT
- `EL_TOTAL_Y_EL_NUMERO_CUADRAN_CON_LA_CABECERA_Y_CON_LA_DECLARACION = PROVEN`: 52 y 3
- `VOLTAGE_CONTROL_MI_PLACA = SMU7_VOLTAGE_CONTROL_BY_SVID2 = PROVEN`
- `LA_CADENA_DE_VDDCPHASE_CORRE_EN_MI_PLACA = PROVEN_DERIVED`
- `LOS_BITS_5_Y_6_SON_PSI1_Y_PSI0_EN = PROVEN`: la cabecera lo dice, `atombios.h:5182-5183`
- `VDDCPHASE_MI_PLACA = 3 = PROVEN`: `0x0012` -> 0 -> 0 -> `0 ^ 3`
- `LO_QUE_EL_DRIVER_LLAMA_PHASE_SHED_SON_LOS_ENABLE_DE_FASE_SVI2 = PROVEN`
- `EL_VBIOS_SOBRESCRIBE_EL_DEFECTO_DEL_DRIVER_CON_CEROS = PROVEN`: `:1923` frente a `:1932`
- `LA_ENTRADA_PARECE_SIN_RELLENAR = PROVEN_DERIVED`
- `EL_CAP_CONTROLVDDCI_CORROBORADO_POR_UN_SEGUNDO_VBIOS = PROVEN`
- `SI_VDDCPHASE_3_ES_CORRECTO_PARA_EL_SMC = NOT_AVAILABLE`

## Lo que esto obliga a hacer en un driver propio

1. **Un valor por defecto no sobrevive a una lectura de dato sin validar.** Aqui el driver pone
   `1` —«control de fase activo»— y una entrada de VBIOS a cero lo cambia a `3`. **Si el dato
   puede faltar, hay que distinguir «falta» de «vale cero».** Un dato que llega todo a cero
   desde una tabla que se declara por version **es un dato que falta**, y hay que tratarlo como tal.
2. **El nombre de un campo tiene que decir lo que es.** `vddc_phase_shed_control` **son los dos
   bits de habilitacion de fase del SVI2**, y eso solo se lee en la cabecera del VBIOS, a 900
   lineas del codigo que lo usa. **Si el VBIOS renombra el campo, el driver sigue compilando y
   manda basura.**
3. **Mi tabla de objetos la dimensiono y la recorro con los DOS limites**, como el `133` pedia:
   el del array declarado y el del VBIOS. Aqui coinciden por casualidad de que mi VBIOS trae
   justo tres.
4. **Y cuando un valor pasa por extraer, intercambiar e invertir, un valor por defecto tiene que
   volver a estar disponible.** Si el VBIOS no dice nada, el default se aplica.

## Estado

Hallazgo **134**: **la incognita de `133` queda resuelta por medicion**, la cadena completa de
`VddcPhase` esta medida hasta su ultimo numero, y `122` queda corroborado por una segunda tabla
del VBIOS.