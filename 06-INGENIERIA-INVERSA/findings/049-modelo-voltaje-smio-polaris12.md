# 049 · El modelo de voltaje real de Polaris12: SMIO, 4 niveles y una macro que no hace lo que su nombre dice

`CLASSIFICATION=DOCUMENTATION` · `TRACK=STATIC` · `WORK_CLASS=READ_ONLY/EVIDENCE`
`WRITE_EXECUTION=NONE` · `MODIFICATIONS=0` · `RUNTIME=NOT_RUN` · `GPU INTACTA`
`SCOPE_CLAIM=.write-lock/smu` · `COMPLEMENTS=047,048`

---

## CUDA principal

El voltaje del núcleo en Polaris12 **no se escribe en ningún registro de voltaje**.
El driver rellena una tabla con **índices SMIO** y voltajes escalados, y el
firmware SMU ejecuta el cambio. El límite duro es de **4 niveles**.

---

## 1. La tabla de núcleo

```
polaris10_populate_smc_vddc_table(hwmgr, table)      polaris10_smumgr.c:691
{
   data  = hwmgr->backend;                      → struct smu7_hwmgr
   count = data->vddc_voltage_table.count;
   if (SMU7_VOLTAGE_CONTROL_BY_GPIO == data->voltage_control) {
       if (count > SMU_MAX_SMIO_LEVELS)
           count = SMU_MAX_SMIO_LEVELS;                        ◄ TOPE
       for (level = 0; level < count; ++level) {
           table->SmioTable1.Pattern[level].Voltage =
               PP_HOST_TO_SMC_US(entries[level].value * VOLTAGE_SCALE);
           table->SmioTable1.Pattern[level].Smio = (uint8_t) level;
           table->Smio[level] |= entries[level].smio_low;
       }
       table->SmioMask1 = data->vddc_voltage_table.mask_low;
   }
   return 0;
}
```

Tres dominios con la misma estructura:

```
polaris10_smumgr.c:664   polaris10_populate_smc_mvdd_table()    memoria
polaris10_smumgr.c:691   polaris10_populate_smc_vddc_table()    nucleo
polaris10_smumgr.c:716   polaris10_populate_smc_vddci_table()   E/S
```

## 2. El límite: 4 niveles

```
smu72.h:103   #define SMU_MAX_SMIO_LEVELS  4
smu73.h:103   #define SMU_MAX_SMIO_LEVELS  4
smu74.h:132   #define SMU_MAX_SMIO_LEVELS  4     ◄ smu74 = Polaris
smu75.h:53    #define SMU_MAX_SMIO_LEVELS  4
```

Usado `smu74.h` ⇒ **SMU 7.4**, consistente con `polaris10_smu_funcs`.

```
POLARIS_VOLTAGE_LEVELS = PROVEN   4, clippado en el populate
  si la tabla tiene más de 4 entradas, el resto se descarta silenciosamente
  no hay error ni aviso: es un truncamiento
```

El mismo valor en las cuatro generaciones smu7/smu8/smu9/smu10 sugiere que es
un tope del **generador de reloj**, no del ASIC.

```
SMIO_LEVEL_LIMIT_IS_GENERATOR_WIDE = CORROBORATED
  idéntico en smu72..smu75 ⇒ límite de laBlocks de SMIO, no del chip
```

## 3. La macro que no hace lo que su nombre dice

```
pp_endian.h:30   #define PP_HOST_TO_SMC_US(X)   cpu_to_be16(X)
```

El nombre `US` sugiere una **conversión de unidades**. Lo que hace es un
**intercambio de bytes a 16 bits big-endian**, y nada más.

```
PP_HOST_TO_SMC_US_IS_NOT_A_UNIT_CONVERSION = PROVEN
  lo que hace :  truncar a 16 bits + byte-swap a big-endian
  lo que sugiere: cambio de unidades
  el nombre empieza por PP_ = PowerPlay, y US no es microsegundos aquí
```

Consecuencia directa: **la escala de voltaje no la pone la macro, la pone el
producto anterior.**

```
VOLTAGE_SCALE = PROVEN   hwmgr.h:38   VOLTAGE_SCALE = 4

cadena real del valor:
  value (host)
     × VOLTAGE_SCALE (4)                  hwmgr.h:38
     → PP_HOST_TO_SMC_US  = cpu_to_be16   pp_endian.h:30
     → 16 bits, big-endian, en SmioTable1.Pattern[level].Voltage
```

No hay conversión a microvoltios en el código. Si el host almacena el voltaje en
mV, ×4 lo deja en una escala de 1/4 de mV, es decir **0.25 mV por unidad** — pero
eso es una inferencia del factor, no una afirmación del corpus.

```
VOLTAGE_UNIT = NOT_DETERMINED
  el corpus da el factor 4 y el truncado a 16 bits
  la unidad nominal del campo Voltage NO está documentada
  → marcar como NOT_DETERMINED, no deducir 0.25 mV
```

## 4. La ruta de aplicación

```
data->vddc_voltage_table  ──►  table->SmioTable1.Pattern[level].Voltage
                           ──►  table->SmioTable1.Pattern[level].Smio
                           ──►  table->Smio[level]       (más smio_low)
                           ──►  table->SmioMask1
                                    │
                                    ▼
                    smum_populate_all_graphic_levels()   smumgr.c
                                    │
                                    ▼
                    copia a la SRAM del SMC
                                    │
                                    ▼
                    mensaje PPSMC_* → firmware
                                    │
                                    ▼
                    el firmware ACCIONA los SMIO → cambia el voltaje
```

```
VOLTAGE_APPLIED_BY_FIRMWARE = PROVEN_DERIVED
  el driver no escribe voltaje: entrega índices SMIO
  y el firmware los ejecuta
  ⇒ el voltaje del núcleo es OTRO dominio delegado al firmware,
     igual que el reloj lo era en la ruta SI (041-045)
```

`smu7_hwmgr.h:33   SMU7_VOLTAGE_CONTROL_BY_GPIO = 0x1`

Es un **flag de modo**: si no es GPIO, la rama entera no se ejecuta y la tabla
queda vacía. Hay al menos dos mecanismos de control de voltaje y Polaris usa el de
SMIO.

## 5. Corrección a 041-042

```
MODELO_ENERGIA_POLARIS != CURVA_AT
  041/042: banda de histéresis A-T con r600_calculate_at, CG_AT__CG_R/L
  049:     tabla de (nivel, voltaje, smio) con tope de 4

  no son dos versiones de lo mismo: son modelos distintos
  la curva A-T pertenece a la ruta SI (no compilada para Polaris12)
  el modelo Polaris es por dominio de voltaje vía SMIO
```

## 6. Estado

```
VOLTAGE_CONTROL_MECHANISM     PROVEN    SMIO/GPIO, flag 0x1
VOLTAGE_DOMAINS               PROVEN    mvdd / vddc / vddci
VOLTAGE_LEVEL_LIMIT           PROVEN    4
VOLTAGE_SCALE                 PROVEN    ×4
VOLTAGE_ENDIANNESS            PROVEN    16 bits big-endian
VOLTAGE_UNIT_NOMINAL          NOT_DETERMINED
SMIO_EXECUTION                NOT_IN_CORPUS   lo hace el firmware
vddc_voltage_table  origen    NOT_READ    quién la rellena
voltage_control  lectura      NOT_READ    dónde se decide GPIO vs otro
```

## 7. Fallos nominales

| # | Busqué | Realidad |
|---|---|---|
| 31º | `PP_HOST_TO_SMC_US` como conversión de unidades | es `cpu_to_be16` |
| 32º | `SMU_MAX_SMIO_LEVELS` en `powerplay/inc/*.h` solo | hay 4 copias, una por generación |

El 31º es el quarto caso del patrón `NAME_MATCH ≠ SEMANTIC_MATCH` en este scope.
Los nombres en este subsistema describen la **intención** (units, per-smu) y
rara vez la **operación**.

---

## Para el driver propio

```
1. construir la tabla de 4 niveles como máximo, por dominio
2. voltage_host × 4 → truncar a 16 bits → byte-swap a big-endian
3. el índice SMIO va en Pattern[].Smio y los bits en table->Smio[]
4. SmioMask1 = máscara de bits válidos
5. subir la tabla a la SRAM del SMC y mandar el mensaje
6. NO escribir voltaje directamente: lo ejecuta el firmware

Pendiente de medir antes de implementar:
  · la unidad nominal del campo Voltage   (NOT_DETERMINED)
  · quién rellena vddc_voltage_table y de dónde salen los voltajes
  · qué significa exactamente voltage_control != BY_GPIO
```