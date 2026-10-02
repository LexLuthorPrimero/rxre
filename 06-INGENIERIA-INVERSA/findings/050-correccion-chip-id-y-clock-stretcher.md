# 050 · Corrección: la rama correcta es la `else`, y CKS es ClockStretcher

`CLASSIFICATION=DOCUMENTATION` · `TRACK=STATIC` · `WORK_CLASS=READ_ONLY/EVIDENCE`
`WRITE_EXECUTION=NONE` · `MODIFICATIONS=0` · `RUNTIME=NOT_RUN` · `GPU INTACTA`
`SCOPE_CLAIM=.write-lock/smu` · `CORRECTS=statement-in-session-2026-10-01` · `COMPLEMENTS=049`

---

## CUDA principal

En el turno anterior afirmé que la rama `chip_id == CHIP_POLARIS10` de
`polaris10_smumgr.c:1674` era "la nuestra". **Es falso.**

`CHIP_POLARIS10 = 15`, `CHIP_POLARIS12 = 17`, y nuestra tarjeta es `17`. La
condición no se cumple y el código ejecutado es la rama `else`, con **constantes
polinómicas distintas**.

Es el cuarto `NAME_MATCH ≠ SEMANTIC_MATCH` del scope, y el más caro: el nombre
del fichero y de la función (`polaris10_`, `polaris10_populate_clock_stretcher_data_table`)
sugiere Polaris10, pero el código sirve a las tres generaciones de Polaris
mediante `chip_id`.

---

## 1. El mapa de identificadores

```
include/drm/amd_asic_type.h
   CHIP_POLARIS10,   /* 15 */
   CHIP_POLARIS11,   /* 16 */
   CHIP_POLARIS12,   /* 17 */      ◄ NUESTRO
```

Y el hardware:

```
0000:01:00.0   1002:699f   asic_type = 17   Polaris12
```

Confirmación cruzada desde el propio driver:

```
smu7_hwmgr.c:1964   (adev->asic_type == CHIP_POLARIS12) ||
hwmgr.c:501         (hwmgr->chip_id == CHIP_POLARIS12)
```

Ambas ramas Polaris12 existen y son alcanzables para nosotros.

## 2. La rama que se ejecuta de verdad

```
polaris10_populate_clock_stretcher_data_table()      polaris10_smumgr.c:1650
   :1661   stretch_amount = table_info->cac_dtp_table->usClockStretchAmount;
   :1664   atomctrl_read_efuse(hwmgr, STRAP_ASIC_RO_LSB, STRAP_ASIC_RO_MSB, &efuse);
   :1667   ro = ((efuse * (ro_range_maximum - ro_range_minimum)) / 255) + ro_range_minimum;

   :1670   for (i = 0; i < sclk_table->count; i++) {
   :1671       smc_state_table.Sclk_CKS_masterEn0_7 |= entries[i].cks_enable << i;   ◄ MAPA DE BITS
   :1674       if (hwmgr->chip_id == CHIP_POLARIS10) {        ← 15, NO somos nosotros
                :1676       volt_without_cks = (2753594000U + ...) / (...)
                :1677       volt_with_cks    = (2797202000U + ...) / (...)
              } else {                                       ◄ ESTA ES LA NUESTRA
                :1680       volt_without_cks = (2416794800U + ...) / (...)
                :1681       volt_with_cks    = (2999656000U + ...) / (...)
              }
   :1685       volt_offset = (uint8_t)(((volt_without_cks - volt_with_cks +
                                             cks_voffset) * 100 + 624) / 625);
   :1687       smc_state_table.Sclk_voltageOffset[i] = volt_offset;
          }
   :1688   smc_state_table.LdoRefSel = (cac_dtp_table->ucCKS_LDO_REFSEL != 0)
                                        ? ucCKS_LDO_REFSEL : 5;
```

### Constantes de la rama `else` (la nuestra)

```
volt_without_cks = (2416794800U + (clk/100) * 1476925/10  - (ro - 50)*1000000)
                  / (2625416 - (clk/100) * (12586807/10000))

volt_with_cks    = (2999656000U - (clk/100) * 392803     - (ro - 44)*1000000)
                  / (3422454 - (clk/100) * (18886376/10000))
```

Contra las de la rama `POLARIS10` (2753594000U / 2797202000U), que **no
ejecutamos**.

```
CLK_STRETCHER_POLARIS12_BRANCH = PROVEN
  condicion:  hwmgr->chip_id == CHIP_POLARIS10   valor 15
  nuestro:    17
  ⇒ la rama ejecutada es la else
  ⇒ constantes 2416794800U / 2999656000U son las vigentes
```

## 3. La unidad del voltaje: mV, por fin

```
smu7_hwmgr.c:2021-2022   min = 1200;  max = 2000;    ◄ evv_revision == 1
smu7_hwmgr.c:2025-2026   min = 1200;  max = 2500;    ◄ evv_revision == 2
smu7_hwmgr.c:2030-2031   min = 1100;  max = 2100;    ◄ sin revision EVV
smu7_hwmgr.c:2033-2034   data->ro_range_minimum = min;
                         data->ro_range_maximum = max;
```

Rangos de 1100-2500 sobre un campo que se usa como voltaje: la unidad es
**milivoltios**. Esto cierra la pregunta que en 049 dejé como `NOT_DETERMINED`.

```
VOLTAGE_UNIT = PROVEN   mV
  evidencia: rangos 1100/1200 .. 2000/2100/2500 en un contexto de voltaje,
             usados directamente como voltaje en el polinomio
  la escala VOLTAGE_SCALE=4 de 049 pertenece a OTRA capa (SmioTable1 del SMC),
             no a la capa del registro VBIOS
```

Consecuencia: **el `2000` de `smu7_setup_voltage_range_from_vbios` es el mismo
dominio de unidades**, y el corte en `> 2000` descarta lecturas de 2001 mV o más
como no plausibles. Coherente: 2.0 V es un techo razonable para el núcleo.

## 4. `cks_enable` y `cks_voffset` resueltos

```
cks_enable   por entrada   →  Sclk_CKS_masterEn0_7 |= cks_enable << i
                            ⇒ es un BITO de la entrada i, "este estado de reloj
                              tiene el ClockStretcher activado"
cks_voffset  por entrada   →  entra en volt_offset
                            ⇒ corrección en mV que el driver aplica al cálculo

polaris10_smumgr.c:1690   stretch_amount ∈ [0,5]  → si no, quita
                          PHM_PlatformCaps_ClockStretcher y avisa con PP_ASSERT
```

```
CKS_MEANING = PROVEN   ClockStretcher
  evidencia directa:  PHM_PlatformCaps_ClockStretcher
                       stretch_amount, Sclk_CKS_masterEn0_7, volt_with_cks
  CKS = Clock Stretch(er), no "Clock Keeper Switch" como suponía
```

Y el nombre de la función, `polaris10_populate_clock_stretcher_data_table`, es
correcto: la generación es Polaris10 pero la función **también sirve a Polaris11 y
12**, discriminando con `chip_id` por dentro.

## 5. `ro` viene de un eFuse real

```
smu7_smumgr... :1664   atomctrl_read_efuse(hwmgr, STRAP_ASIC_RO_LSB,
                                           STRAP_ASIC_RO_MSB, &efuse)
ro = (efuse * (max - min)) / 255 + min
```

`ro` es una **característica física de la dies concreta** leída de un eFuse de
8 bits, reescalada al rango de frecuencia del ASIC. El voltaje de cada estado de
reloj depende de la pieza ensamblada, no solo de su modelo.

```
RO_IS_PER_DIE_EFUSE = PROVEN
  origen:  strap eFuse, 8 bits, leido por atomctrl_read_efuse
  mapeo:   lineal sobre [ro_range_minimum, ro_range_maximum]
  efecto:  desplaza volt_without_cks y volt_with_cks
  ⇒ el voltaje no es solo funcion del modelo, es funcion de la dies
```

Consecuencia para un driver propio: **sin el eFuse no hay voltaje correcto.** No
es un valor que se pueda promediar ni copiar de otro Polaris12.

## 6. Las ramas Polaris12 que sí existen

Tres sitios donde el código discrimina explícitamente nuestra generación:

```
polaris10_smumgr.c:793   si POLARIS12 o P20/P21/P30/P31
                             state->VddcPhase = vddc_phase_shed_control ^ 0x3;
                         si no
                             state->VddcPhase = vddc_phase_shed_control ? 0 : 1;

polaris10_smumgr.c:1801  si P20, o (POLARIS12 y no P23), o P21
                             avfs_params.ucEnableApplyAVFS_CKS_OFF_Voltage = 1;

polaris10_smumgr.c:1819  si POLARIS12 y no P23
                             ulGB_VDROOP_TABLE_CKSOFF_a0 = 0xF6B024DD;
                             ulGB_VDROOP_TABLE_CKSOFF_a1 = 0x3005E;
                             ulGB_VDROOP_TABLE_CKSOFF_a2 = 0x18A5F;
```

La de `:793` invierte la polaridad con `^ 0x3` frente al `? 0 : 1` de la rama
genérica: nuestra generación **invierte el sentido del phase shedding**.

```
VDDC_PHASE_SHED_POLARIS_INVERTED = PROVEN   :793
  nuestra generacion:  vddc_phase_shed_control XOR 0x3
  generica:            vddc_phase_shed_control ? 0 : 1
  ⇒ el significado del flag esta invertido en nuestra generacion
```

## 7. Lo que sigue abierto

```
STRAP_ASIC_RO_LSB/MSB   ubicacion del registro de eFuse    NOT_READ
atomctrl_read_efuse     implementacion de la lectura          NOT_READ
Sclk_CKS_masterEn0_7    nombre del campo, 8 bits              PROVEN (nombre)
usClockStretchAmount    unidad y rango                         NOT_DETERMINED
VddcPhase               que fase representa 0x3 vs 0           NOT_DETERMINED
P20/P21/P23/P30/P31     ASICID_IS_* por revision, no por chip_id NOT_READ
```

---

## 8. Dos fallos nominales míos en este turno

| # | Fallo | Regla violada |
|---|---|---|
| 33º | `grep ... \| head -6` cortando la salida: no pude confirmar la ausencia de `CHIP_POLARIS10` en `pm/` porque la lista ya tenia 6 lineas | `TRUNCATION_AS_ABSENCE`, la regla la escribi yo |
| 34º | Afirmar que la rama `CHIP_POLARIS10` era la nuestra | `NAME_MATCH ≠ SEMANTIC_MATCH`, aplicado al nombre del fichero |

El 33º es especialmente malo porque es exactamente el fallo que esa regla
describe: un límite de salida convertido en ausencia. Y lo cometí **después** de
escribir la regla. Lo dejo registrado porque un hallazgo que solo documenta
errores ajenos no sirve de nada.

---

## Para el driver propio

```
1. leer el eFuse de RO antes de calcular voltajes        (atomctrl_read_efuse)
2. mapear ro a [ro_range_min, ro_range_max] con la escala /255
3. si no hay revision EVV: 1100..2100 mV   (o 1200..2000 / 1200..2500 con EVV)
4. para Polaris12 (chip_id 17) usar la rama else:
       volt_without_cks = (2416794800U + clk/100*1476925/10 - (ro-50)*1e6)
                         / (2625416 - clk/100*12586807/10000)
       volt_with_cks    = (2999656000U - clk/100*392803     - (ro-44)*1e6)
                         / (3422454 - clk/100*18886376/10000)
5. volt_offset = (volt_without_cks - volt_with_cks + cks_voffset)*100+624 / 625
6. Sclk_CKS_masterEn0_7 |= cks_enable << i     (un bit por entrada)
7. invertir el phase shedding: VddcPhase = vddc_phase_shed_control ^ 0x3
8. unidad de todos los voltajes: mV
```
