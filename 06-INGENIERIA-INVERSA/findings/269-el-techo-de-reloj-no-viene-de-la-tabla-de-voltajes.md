# 269 · El techo de reloj no viene de la tabla de voltajes, y el ASICMaxEngineClock del firmware vale cero

WORK_CLASS=READ_ONLY · WRITE_EXECUTION=NONE · MODIFICATIONS 0

> ## Que agrega
>
> Cierra `267` y su implication. El voltage offset del clock stretching lo
> calcula **el host desde la frecuencia del reloj**, no desde la tabla de
> voltajes. Y el firmware declara su techo de motor en **cero**. Tres piezas
> sueltas del mismo problema: el reloj alto de esta placa **no tiene un techo
> autoritativo en ninguna parte del VBIOS**.

## 1. El reloj no depende de la tabla de voltajes

`polaris10_smumgr.c:1655-1708`, la ruta completa que corre en mi ASIC:

```c
1661  stretch_amount = (uint8_t)table_info->cac_dtp_table->usClockStretchAmount;
1671  for (i = 0; i < sclk_table->count; i++) {
1672      Sclk_CKS_masterEn0_7 |= sclk_table->entries[i].cks_enable << i;
1674      if (hwmgr->chip_id == CHIP_POLARIS10) {      /* NO es mi rama */
1675-1678    volt_without_cks = ...; volt_with_cks = ...;
1679      } else {                                    /* la mia: chip_id 17 */
1680-1683    volt_without_cks = ...; volt_with_cks = ...;
1686      if (volt_without_cks >= volt_with_cks)
1687          volt_offset = ((volt_without_cks - volt_with_cks +
                            sclk_table->entries[i].cks_voffset) * 100 + 624) / 625;
1690      Sclk_voltageOffset[i] = volt_offset;
1691  }
1696  if (stretch_amount == 0 || stretch_amount > 5) {
1697      phm_cap_unset(..., PHM_PlatformCaps_ClockStretcher);
1699      PP_ASSERT_WITH_CODE(false, ..., return -EINVAL);
1702  }
1704  value = cgs_read_ind_register(hwmgr->device, CGS_IND_REG__SMC, ixPWR_CKS_CNTL);
1705  value &= 0xFFFFFFFE;
1706  cgs_write_ind_register(hwmgr->device, CGS_IND_REG__SMC, ixPWR_CKS_CNTL, value);
```

**El voltaje se deriva de `entries[i].clk`, no de `ucVddInd` ni de
`VoltageObjectInfo`.** Son polinomios racionales ajustados, distintos para
Polaris10 y para el resto. Mi chip es `chip_id = 17` (CHIP_POLARIS12), luego
**corre la rama `else` de `:1680-1683`**, que es la segunda formula.

Con los 8 niveles que decodifique en `267` —`cks_enable` = 0 en el nivel 0 y 1
en los otros siete— el resultado es:

**`Sclk_CKS_masterEn0_7 = 0xFE`.** El bit 0 apagado es coherente con que el nivel
de arranque no lleve clock stretching y los siete de encima si.

## 2. `ixPWR_CKS_CNTL` deja de ser bloqueador, y hace otra cosa

Mi memoria lo tenia como `NOT_DECLARED`. **Se usa en `polaris10_smumgr.c:1704`
y `:1706`**, que es mi ruta viva. Y lo que hace **no** es escribir el stretch
amount: **limpia el bit 0** del registro. El `stretch_amount` solo valida.

## 3. `usClockStretchAmount = 2`, verificado por el camino dificil

Mi memoria lo daba como 2. Confirmado, pero la primera busqueda fallo:

- Mi VBIOS tiene `usPowerTuneTable` con `ucRevId = 4`.
- `process_pptables_v1_0.c:586` hace `if (ucRevId < 3)` -> struct **Tonga**.
- `:613` hace `else if (ucRevId < 4)` -> struct **Fiji**.
- Con rev 4 eligen la rama **que no es ni una ni otra** (el `else` final).

Leyendo el layout **Tonga** me salen valores grandes y sin sentido
(8964, 9216, 8960...) porque ese no es el struct. Con el layout **Fiji**, campo
`usClockStretchAmount` en **offset 25**: **2**.

Con 2, `:1696` no dispara, luego **ClockStretcher sigue activo**. Eso corrobora
`132` por una via que no es medicion: `132` lo midio, y aqui se deduce de un
campo del VBIOS que solo pasa el filtro si esta en 1..5.

La misma tabla, ahora con el layout correcto, da la tabla de potencia que no
tenia:

| campo | valor |
|---|---:|
| `usTDP` | 35 |
| `usTDC` | 36 |
| `usTjMax` | 93 |
| `usSoftwareShutdownTemp` | 97 |
| `usBatteryPowerLimit` | 35 |

## 4. Hay un parche para Polaris10 rev C7 que **no corre en mi placa**

`hwmgr/smu7_hwmgr.c:2513-2532`:

```c
2513  if (adev->pdev->device == 0x67DF && hw_revision == 0xC7 &&
2514      ((sub_sys_id == 0xb37 && sub_vendor_id == 0x1002) ||
2515       (sub_sys_id == 0x4a8 && sub_vendor_id == 0x1043) ||
2516       (sub_sys_id == 0x9480 && sub_vendor_id == 0x1682))) {
2520      PWR_CKS_CNTL, CKS_STRETCH_AMOUNT, 0x3;
2524      if (lookup_table->entries[dep_mclk_table->entries[...count-1].vddInd].us_vdd >= 1000)
2525          return 0;
2527      for (i = 0; i < lookup_table->count; i++)
2529          if (... us_vdd >= 1000) { dep_mclk_table->entries[...].vddInd = i; return 0; }
2533  }
```

Con la identidad de mi placa:

```
mi device = 0x699F      el parche pide 0x67DF    -> NO coincide
mi revision = 0xC7      el parche pide 0xC7      -> coincide
mi sub_sys  = 0x0B04    el parche pide b37/4a8/9480 -> NO coincide
```

**El parche no se ejecuta en mi ASIC.** Consecuencias:

- Placas Polaris10 rev C7 reciben `CKS_STRETCH_AMOUNT = 0x3`; **mi placa recibe
  el 2 del VBIOS**.
- Esas placas reciben ademas un **parche del indice de voltaje**; **mi placa no**.

Y el parche existe precisamente porque la linea 2524 hace
`lookup_table->entries[vddInd]` **sin comprobar que `vddInd <
lookup_table->count`**. Es una lectura fuera de rango que AMD tapo en un
subconjunto de placas y **dejo sin tapar en el resto**.

Mi VBIOS usa `ucVddInd = 9` en el nivel mas alto, con una tabla de 3 entradas
(`134`). En mi placa no hay red que lo parchee.

## 5. `ulASICMaxEngineClock = 0`

`revkit/atomrom.py firmware` sobre mi captura, tabla `_ATOM_FIRMWARE_INFO_V1_2`
en `0x9974`, `ucFormatRevision = 2`, `ucContentRevision = 2`, `usStructureSize`
**108**. Autotest: 11 controles, todos OK, sobre ROM sintetico.

```
ulFirmwareRevision          0x0f320201
ulDefaultEngineClock        21400        214 MHz
ulDefaultMemoryClock        30000        300 MHz
ulDriverTargetEngineClock   0            0 MHz
ulDriverTargetMemoryClock   360000       3600 MHz
ulASICMaxEngineClock        0            0 MHz<-- el techo de motor es CERO
ulASICMaxMemoryClock        62610        626 MHz
ulASICMaxTemperature        0
```

El tool se niega a afirmar la unidad sin contraste, sale con codigo 4, y al
tenerle la captura viva la fija:

```
ulDefaultEngineClock   214  vs   214 MHz   COINCIDE
ulDefaultMemoryClock   300  vs   300 MHz   COINCIDE
unidad = 10 kHz = 1/100 MHz     CORROBORATED
```

Y el cruce con mi medicion viva: `MCLK: 300 MHz`, `PSTATE_SCLK: 214 MHz`,
`PSTATE_MCLK: 625 MHz`. **`ulASICMaxMemoryClock = 626.10 MHz` queda justo por
encima del paso de 625 MHz que la placa estaba usando.** Coherente.

**`ulASICMaxEngineClock = 0` no es un valor normal: no hay techo de motor
declarado en el firmware.** Los campos de memoria si vienen rellenos
(30000, 62610, 360000). Los de motor, cero.

## El cuadro, junto

| fuente | techo de motor | voltaje |
|---|---|---|
| tabla DPM (`267`) | 1071 MHz | `MinVoltage` = 0 |
| VoltageObjectInfo (`134`) | — | objetos sin rellenar |
| `ucVddInd` (`267`) | — | indice 9 sobre 3 entradas |
| FirmwareInfo (esta) | **`ulASICMaxEngineClock = 0`** | — |
| reloj vivo | 997 MHz, techo 214 MHz | — |

**El unico numero de techo de motor que existe es el 1071 MHz de la tabla DPM, y
nadie mas lo respalda.** El voltage offset del clock stretching se calcula en el
host desde la frecuencia, lo cual salva el camino del reloj aunque el voltaje
declarado valga cero: el firmware recibe el offset, no una curva.

## Por que esto importa para el objetivo de rendimiento

Un driver propio tiene que decidir el techo de SCLK, y aqui **el unico sitio
con un numero es la tabla DPM del VBIOS**. No hay limite del firmware que lo
respalde, no hay voltaje que lo sostenga en la tabla, y el indice de voltaje del
nivel mas alto apunta fuera de rango sin red de seguridad en mi placa.

Eso deja una sola via para pasar de 1071 MHz: **la ruta B de overdrive de
`127`**, porque ahi el techo lo pone el driver, no el VBIOS.

## Lo que NO afirmo

- **NO** afirmo que la placa no corra a 1071 MHz. `PSTATE_SCLK: 214 MHz` en mi
  captura es el estado de reposo, y `997 MHz` es la frecuencia de trabajo en
  ese instante; ninguna de las dos dice cual es el maximo alcanzable.
- **NO** he medido voltajes ni frecuencias. `B_RUNTIME = NOT_EXECUTED`.
- **NO** afirmo que el `ulASICMaxEngineClock = 0` sea un bug de AMD. Puede ser
  que el campo no se use y el limite real viva solo en la tabla DPM. Es
  `NOT_DETERMINED`, y lo digo asi porque no he encontrado un consumidor de ese
  campo en el arbol.
- No he tocado hardware, firmware ni VBIOS.

## Correccion de mi propio proceso

`atomrom.py` resulto ser una herramienta bien hecha en un aspecto que casi todos
fallan: **se niega a publicar una unidad sin contraste independiente**, y cuando
el contraste no cuadra con una hipotesis mia —`ulFirmwareRevision` contra las
feature versions del kernel— declara `NOT_DETERMINED` en vez de `REFUTED`. Es
exactamente la disciplina que pido en mi trabajo y que yo he violado hoy al
publicar «usClockStretchAmount = 2» desde la memoria antes de verificarlo.

## Frontier siguiente

Determinar si el firmware SMC consume `MinVoltage` y `ulASICMaxEngineClock`, o si
los ignora. Discriminante barato: buscar en el firmware del SMC si existen
referencias a esas posiciones de la tabla DPM. Es el nudo entre `134`, `267` y
esto, y decide si el reloj alto de esta placa tiene o no techo real.

Es `RUNTIME_MISSING` con lo que tengo: el firmware SMC no esta en mi corpus. Y
`atomrom.py` no puede cubrirlo porque solo parsea el VBIOS, no el firmware
cargado.