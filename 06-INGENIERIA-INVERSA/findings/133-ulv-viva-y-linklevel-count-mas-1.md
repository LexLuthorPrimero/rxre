# 133 · ULV viva en mi placa, y un `LinkLevel[8]` que se escribe `count + 1` mientras el mismo fichero recorta el mismo campo

WORK_CLASS=READ_ONLY · WRITE_EXECUTION=NONE · MODIFICATIONS 0

> ## RESUELTO POR `134` — si hay un objeto VDDC/SVID2, y produce `VddcPhase = 3`
>
> Este fichero declaro `NOT_DECODED` en vez de publicar una estimacion. **Resuelto por
> medicion**, recorriendo la tabla con el mismo algoritmo que el codigo:
>
> ```
> ATOM_VOLTAGE_OBJECT_INFO_V3_1 en 0xA7F0   usStructureSize = 52
>   obj[0]  VDDC (1)  + SVID2 (7)     usSize = 12
>   obj[1]  VDDCI (4) + SVID2 (7)     usSize = 12
>   obj[2]  MVDDC (2) + GPIO_LUT (0)  usSize = 24
>                                 4+12+12+24 = 52  EXACTO
> ```
>
> **Tres objetos, y son los tres slots de `asVoltageObj[3]`.** Cuadra dos veces: el total con la
> cabecera, y el numero con la declaracion.
>
> ```
> hay VDDC+SVID2  -> voltage_control = SMU7_VOLTAGE_CONTROL_BY_SVID2
>                -> :1930 SE EJECUTA  ->  la cadena de VddcPhase corre entera
>
> usLoadLine_PSI = 0x0012 (18):  bit 6 PSI0_EN = 0   bit 5 PSI1 = 0
> :1932  tmp3 = (18 >> 5) & 0x3   = 0
> :1933  swap de bits              = 0
> :798   VddcPhase = 0 ^ 3        = 3
> ```
>
> **Y los bits 5 y 6 son `PSI1` y `PSI0_EN`** —los enable de las dos fases del regulador SVI2—
> **segun la cabecera de la struct, no segun el codigo**, que lo llama `vddc_phase_shed_control`.
>
> **El hallazgo que sale de ahi:** el driver pone `vddc_phase_shed_control = 1` a proposito
> (`:1923`) y **los bits a cero del VBIOS lo sobrescriben sin ninguna comprobacion**. Mi entrada
> SVI2 tiene `PSI0_VID = 0`, `PSI0_EN = 0`, `PSI1 = 0` y los dos GPIO a 0: **parece sin rellenar**,
> y el driver lo toma como respuesta valida.
>
> **Ademas `obj[1]` es VDDCI+SVID2**, lo que recorre de punta a punta la cadena de `122`:
> bit 15 del PPT -> `ControlVDDCI` -> `:1905` -> `bySVID2` -> **el cap no se borra en `:1919`**.

**Segunda ruta confirmada VIVA en mi ASIC, y con ella quedan los 13 escrituras registro-a-registro
de `polaris10_smumgr.c`.** Ademas: una hipotesis REFUTADA antes de publicar, un par de
contrastes en el mismo fichero, y **una pieza que NO he decodificado y declaro como tal.**

## La ruta ULV: viva, con las dos condiciones medidas

```c
/* polaris10_smumgr.c:1944 */
if (hw_data->ulv_supported && table_info->us_ulv_voltage_offset) {
        result = polaris10_populate_ulv_state(hwmgr, table);
        ...
        cgs_write_ind_register(hwmgr->device, CGS_IND_REG__SMC,
                        ixCG_ULV_PARAMETER, SMU7_CGULVPARAMETER_DFLT);
}
```

| condicion | como se decide | valor en mi placa |
|---|---|---|
| `ulv_supported` | `feature_mask & PP_ULV_MASK` | **`0xfff7bfff & 0x100 = 0x100`** — se cumple |
| `us_ulv_voltage_offset` | PPT, offset **33** | **MEDIDO: 15** — se cumple |

`PP_ULV_MASK = 0x100` (`amd_shared.h:224`) y lo fija `smu7_hwmgr.c:1836`:

```c
data->ulv_supported = hwmgr->feature_mask & PP_ULV_MASK ? true : false;
```

**Ninguno de los tres que `amdgpu_device.c:2023-2027` borra (`0x4`, `0x4000`, `0x8000`) es
`0x100`, igual que con ClockStretcher.**

**Y los valores que van a la tabla del SMC, calculados:**

```
us_ulv_voltage_offset = 15                      (del PPT, offset 33)
VddcOffset    = 15
VddcOffsetVid = (uint8_t)(15 * VOLTAGE_VID_OFFSET_SCALE2 / VOLTAGE_VID_OFFSET_SCALE1)
              = 15 * 100 / 625 = 2               -> sin truncar, el cast a uint8_t no muerde
```

- `LA_RUTA_ULV_SE_EJECUTA_EN_MI_PLACA = PROVEN_DERIVED`
- `VDDCOFFSETVID_2_SIN_TRUNCAR = PROVEN`: las escalas son `625` y `100` (`hwmgr.h:39-40`)

## `VddcPhase` pasa por tres transformaciones, y la tercera no esta escrita

Para `CHIP_POLARIS12`, `VddcPhase` se determina asi, **en dos ficheros**:

```
smu7_hwmgr.c:1923   vddc_phase_shed_control = 1;                      (por defecto)
smu7_hwmgr.c:1924   if (chip is POLARIS12 | P20 | P21 | P30 | P31) {
smu7_hwmgr.c:1929       if (voltage_control == SMU7_VOLTAGE_CONTROL_BY_SVID2) {
smu7_hwmgr.c:1930           atomctrl_get_svi2_info(hwmgr, VOLTAGE_TYPE_VDDC, &tmp1, &tmp2, &tmp3);
smu7_hwmgr.c:1932           tmp3 = (tmp3 >> 5) & 0x3;                   (extrae los bits 5 y 6)
smu7_hwmgr.c:1933           vddc_phase_shed_control = ((tmp3 << 1) | (tmp3 >> 1)) & 0x3;   (INTERCAMBIA)

polaris10_smumgr.c:798   state->VddcPhase = data->vddc_phase_shed_control ^ 0x3;    (INVIERTE)
polaris10_smumgr.c:800   state->VddcPhase = (data->vddc_phase_shed_control) ? 0 : 1;  (otros chips)
```

**Extraer dos bits, intercambiarlos, e invertirlos.** Y **la tercera transformacion usa `^ 0x3`
solo para mi familia, mientras los demas chips usan un ternario invertido** — que con valor 1
daria `0`, y el `^ 0x3` daria `2`.

**No hay ningun comentario que explique por que Polaris12 invierte con `^ 0x3` y no con `^ 1`, ni
por que el valor se intercambia antes de invertirse.** Los dos numeros son de 2 bits, asi que
`^ 0x3` es un NOT de 2 bits y `^ 1` daria un resultado distinto para 2 y 3.

- `VDDCPHASE_PASA_POR_TRES_TRANSFORMACIONES = PROVEN`: extraer, intercambiar, invertir
- `LA_TERCERA_ES_PROPIA_DE_MI_FAMILIA_Y_NO_ESTA_ESCRITA = PROVEN`: `:798` frente a `:800`
- `LOS_DEMAS_CHIPS_USAN_UN_TERNARIO_Y_NO_UN_XOR = PROVEN`

## Hipotesis REFUTADA: el NULL desreferenciado no es alcanzable

Vi esto y pense «desreferencia nula»:

```c
/* ppatomctrl.c:1090-1093, atomctrl_get_svi2_info */
voltage_object = atomctrl_lookup_voltage_type_v3(voltage_info, voltage_type, VOLTAGE_OBJ_SVID2);
*svd_gpio_id = voltage_object->asSVID2Obj.ucSVDGpioId;      /* sin comprobar NULL */
```

Y `atomctrl_lookup_voltage_type_v3` **devuelve `NULL` en `:282`** si no encuentra el objeto.

**Refutado: `atomctrl_get_svi2_info` tiene UN solo llamador, y su puerta es el MISMO lookup.**

```c
/* smu7_hwmgr.c:1876-1878 */
if (atomctrl_is_voltage_controlled_by_gpio_v3(hwmgr, VOLTAGE_TYPE_VDDC, VOLTAGE_OBJ_SVID2))
        data->voltage_control = SMU7_VOLTAGE_CONTROL_BY_SVID2;
/* smu7_hwmgr.c:1929 */
if (data->voltage_control == SMU7_VOLTAGE_CONTROL_BY_SVID2) {
        atomctrl_get_svi2_info(hwmgr, VOLTAGE_TYPE_VDDC, &tmp1, &tmp2, &tmp3);
```

`atomctrl_is_voltage_controlled_by_gpio_v3:566-567` hace `... != NULL` sobre **el mismo lookup con
los mismos argumentos**. O sea: **si se llega a `:1930`, el lookup ya tuvo exito**, y la tabla del
VBIOS no ha cambiado entre las dos llamadas.

**No es un fallo. Pero es la forma mas fragil de seguridad que he encontrado en el arbol:**

```
:566-567   ret = atomctrl_lookup_voltage_type_v3(...) != NULL;          COMPRUEBA
:589-590   if (voltage_object == NULL) return -1;                        COMPRUEBA
:1090-1093 voltage_object = atomctrl_lookup_voltage_type_v3(...);        NO COMPRUEBA
```

**Tres llamadas al mismo lookup en el mismo fichero; dos comprueban y una no.** La que no
comprueba es la que se apoya en que su unico llamador haga la comprobacion por ella, **en otro
fichero y 500 lineas mas alla**.

- `EL_NULL_DESREFERENCIADO_NO_ES_ALCANZABLE = REFUTADO`: el invariante se cumple por construccion
- `LA_SEGURIDAD_DEPENDE_DE_UN_INVARIANTE_EN_OTRO_FICHERO = PROVEN`: `ppatomctrl.c` frente a `smu7_hwmgr.c`
- `TRES_CALLS_AL_MISMO_LOOKUP_DOS_COMPRUEBAN_Y_UNA_NO = PROVEN`: `:566`, `:589`, `:1090`

## `LinkLevel[8]` se escribe `count + 1`, y el mismo fichero recorta el mismo campo

```c
/* polaris10_smumgr.c:823-825, con el comentario que explica el porque */
        /* Index (dpm_table->pcie_speed_table.count) is reserved for PCIE boot level. */
for (i = 0; i <= dpm_table->pcie_speed_table.count; i++) {       /* <=, no < */
        table->LinkLevel[i].PcieGenSpeed = ...
```

Y **`pcie_count` puede llegar a `sclk_count + 1`**:

```c
/* process_pptables_v1_0.c:502-508 */
pcie_count = (pp_table_information->vdd_dep_on_sclk->count) + 1;
if ((uint32_t)atom_pcie_table->ucNumEntries <= pcie_count)
        pcie_count = (uint32_t)atom_pcie_table->ucNumEntries;
```

O sea `pcie_count` hasta **9**, y el bucle escribe **10** entradas en
`LinkLevel[SMU74_MAX_LEVELS_LINK]` = `LinkLevel[SMU__NUM_PCIE_DPM_LEVELS]` = **`LinkLevel[8]`**.

**Y en el MISMO fichero, otra funcion recorta ese mismo campo contra ese mismo valor:**

```c
/* polaris10_smumgr.c:2355-2359, polaris10_update_bif_smc_table */
max_entry = (SMU74_MAX_LEVELS_LINK < pcie_table->count) ?
                        SMU74_MAX_LEVELS_LINK :
                        pcie_table->count;
for (i = 0; i < max_entry; i++)
        smu_data->bif_sclk_table[i] = pcie_table->entries[i].pcie_sclk;
```

**Dos funciones, el mismo array de capacidad 8, el mismo `pcie_table->count`: una recorta y la
otra escribe uno mas.** Y el recorte de `:2355` es correcto **aunque el caso valido sea
`count == 8`**, porque `min(8, 8) = 8` y entra justo. **El que falta es el que hace `+1`.**

- `LINKLEVEL8_Y_EL_BUCLE_ESCRIBE_COUNT_MAS_1 = PROVEN`: `:825` con `<=`
- `EL_MISMO_FICHERO_OTRO_SITIO_SI_RECORTA = PROVEN`: `:2355-2357`
- `ESCRIBIR_COUNT_MAS_1_ES_LO_UNICO_QUE_FALTA = PROVEN`

### Y en mi placa, no desborda

```
usPCIETableOffset @61 = 0x02F0 -> ATOM_Tonga_PCIE_Table en 0x09EFA
    ucRevId = 1   ucNumEntries = 3

pcie_count = min(ucNumEntries, sclk_count + 1) = min(3, 9) = 3
el bucle escribe i = 0..3  ->  4 entradas     en LinkLevel[8]
```

**Margen 4. No desborda en mi placa.** Desbordaria con un VBIOS que declarase **8 o mas**
entradas PCIe.

**Ademas hay un detalle de contrato:** `:836-837` pone
`LinkLevelCount = (uint8_t)count` (= 3) mientras se escriben **4** registros. El indice `count`
—el reservado para el boot— **se escribe pero no se cuenta**. Es deliberado y esta comentado, pero
el SMC recibe un numero y hay uno mas escrito: **el SMC no lo sabra.**

- `MARGEN_4_EN_MI_PLACA = PROVEN`: medido
- `EL_DESBORDA_NECESITA_8_ENTRADAS_PCIE = PROVEN_DERIVED`
- `LINKLEVELCOUNT_NO_CUENTA_EL_REGISTRO_RESERVADO = PROVEN`: `:836-837` frente a `:825`

## Y una pieza que NO he decodificado

El lookup de objetos de voltaje camina la tabla **por el `usSize` de cada entrada, hasta el
`usStructureSize` de la cabecera** — no por el limite del array declarado:

```c
/* ppatomctrl.c:267-280 */
unsigned int size = le16_to_cpu(voltage_object_info_table->sHeader.usStructureSize);
while (offset < size) {
        ...
        offset += le16_to_cpu(voltage_object->asGpioVoltageObj.sHeader.usSize);
}
return NULL;
```

Y el array declarado es **`ATOM_VOLTAGE_OBJECT_V3 asVoltageObj[3]`** (`atombios.h:5230`), o sea
**fijo en 3, con un recorrido que no mira ese 3.**

Es **la misma forma que `224` (antes `120`), `229` (antes `128`) y `132`**: una longitud que declara el VBIOS gobernando un
recorrido sobre un array de tamano fijo.

`atomrom` da `VoltageObjectInfo size=52`, y `ATOM_COMMON_TABLE_HEADER` son 4 bytes, luego el
recorrido cubre 48 bytes. **`4 + 3*16 = 52` encaja exacto si cada objeto mide 16 bytes.**

**Lo que NO he hecho: decodificar los bytes para confirmar que hay un objeto `VOLTAGE_TYPE_VDDC`
(1) con `VOLTAGE_OBJ_SVID2` (7), que es lo que decidiria `voltage_control` y por tanto
`VddcPhase`.** Me pare ahi porque `ATOM_VOLTAGE_OBJECT_V3` es una **union** y su tamano no lo fija
el array sino el miembro mayor, y sin el `usSize` de cada entrada no puedo recorrerla con
seguridad. **Declaro la incognita en vez de publicarla resuelta.**

- `EL_LOOKUP_CAMINA_POR_USSTRUCTURESIZE_Y_NO_POR_LOS_3_DECLARADOS = PROVEN`: `:267-280` frente a `atombios.h:5230`
- `52 = 4 + 3*16_ES_COHERENTE_PERO_NO_CONFIRMADO = NOT_DECODED`
- `EXISTE_UN_OBJETO_VDDC_SVID2_EN_MI_VBIOS = NOT_DECODED`: decide `voltage_control` y `VddcPhase`

## Clasificacion

- `LA_RUTA_ULV_SE_EJECUTA_EN_MI_PLACA = PROVEN_DERIVED`: **medidas las dos condiciones**
- `VDDCOFFSETVID_2_SIN_TRUNCAR = PROVEN`
- `VDDCPHASE_TRES_TRANSFORMACIONES_EN_DOS_FICHEROS = PROVEN`
- `LA_TERCERA_ES_PROPIA_DE_MI_FAMILIA_Y_SIN_EXPLICAR = PROVEN`
- `EL_NULL_DESREFERENCIADO_NO_ES_ALCANZABLE = REFUTADO`
- `TRES_CALLS_AL_MISMO_LOOKUP_DOS_COMPRUEBAN_Y_UNA_NO = PROVEN`
- `LA_SEGURIDAD_QUE_FALTA_DEPENDE_DE_UN_INVARIANTE_EN_OTRO_FICHERO = PROVEN`
- `LINKLEVEL8_ESCRITO_COUNT_MAS_1 = PROVEN`
- `EL_MISMO_FICHERO_RECORTA_EL_CAMPO_QUE_EL_OTRO_SOBRESCRIBE = PROVEN`
- `MARGEN_4_EN_MI_PLACA = PROVEN`: medido, no desborda
- `EL_LOOKUP_DE_VOLTAJE_IGNORA_EL_LIMITE_DEL_ARRAY = PROVEN`
- `EXISTE_UN_OBJETO_VDDC_SVID2 = NOT_DECODED`: declarado, no inventado

## Lo que esto obliga a hacer en un driver propio

1. **Una funcion de biblioteca con contrato propio.** `atomctrl_get_svi2_info` desreferencia sin
   comprobar y depende de que su unico llamador haya comprobado por ella. **Mi helper comprueba
   el lookup, siempre, y no espera que quien llama lo haga.**
2. **Un recorrido por VBIOS tiene que tener dos limites: el declarado y el del array.** Aqui hay
   un 3 declarado y un `usStructureSize` del VBIOS, y el codigo solo mira el segundo.
3. **Cuando el mismo campo se usa en dos sitios del mismo fichero, uno lo recorta y el otro no,
   hay que copies el recorte al que falta.** El de `:2355` es correcto y esta a 1500 lineas del
   que no lo es.
4. **Y un parametro de hardware de dos bits no pasa por tres transformaciones sin un comentario.**
   Extraer, intercambiar e invertir es una decision de hardware, y no esta escrita en ninguna
   parte.

## Estado

Hallazgo **133**: **ULV es la segunda ruta confirmada viva en mi placa**, los 13 registros
pendientes quedan **cerrados**, y queda **una incognita declarada** en vez de resuelta por
estimacion.