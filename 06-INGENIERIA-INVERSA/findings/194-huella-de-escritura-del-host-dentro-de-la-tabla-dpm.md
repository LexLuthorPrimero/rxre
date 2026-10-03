# 194  La huella de escritura del host cabe entera dentro de la tabla DPM

WORK_CLASS=READ_ONLY · WRITE_EXECUTION=NONE · MODIFICATIONS 0

## La pregunta

`084` cerro que el firmware elige donde empieza la tabla DPM y que el host solo
pregunta. Lo que queda por medir es lo contrario: **hasta donde escribe el host**.

No es una curiosidad. Si el host escribiera mas alla del final de la struct, la
comprobacion de rango de `smu7_smumgr.c:59` (`limit > smc_start_address + byte_count`)
la detectaria solo si la copia passing por `smu7_copy_bytes_to_smc`. Una escritura por
otro camino no pasaria por ahi.

## Resultado: 12 usos, los 12 dentro de la struct

`polaris10_smumgr.c` usa `dpm_table_start` en 12 sitios, y **los 12** tienen la forma
`dpm_table_start + offsetof(SMU74_Discrete_DpmTable, <campo>)`. Ninguno suma una
constante suelta ni un offset calculado. No hay una segunda region.

Mapa exacto, offsets por gcc:

| offset | tam | campo | linea |
|---:|---:|---|---|
| 108 | 4 | `SystemFlags` | 2119 |
| 112 | 4 | `VRConfig` | 140 |
| 236 | 448 | `GraphicsLevel` | 147, 1046, 2594 |
| 708 | 96 | `MemoryLevel` | 155, 1215, 2597 |
| 1576 | 1 | `UvdBootLevel` | 2292 |
| 1577 | 1 | `VceBootLevel` | 2328 |
| 1592 | 2 | `BootMVdd` | 164 |
| 1692 | 4 | `LowSclkInterruptThreshold` | 2400 |

`sizeof(SMU74_Discrete_DpmTable)` = 1884. Los ocho campos caen en `[108, 1696)`, dentro.

La extension que el host exige al firmware es exactamente **1884 bytes**, de `0` a
`1884`. No mas, no menos.

## La condicion, cerrada

```
dpm_table_start + 1884 < 0x40000
dpm_table_start        < 260260
```

Con la copia de 1776 bytes desde offset 108: `108 + 1776 = 1884`. Coincide con el
tamano de la struct, que es lo coherente: la copia llena la struct entera desde
`SystemFlags` y los 108 primeros bytes son los tres `PIDController`.

## Lo que el firmware tiene que cumplir

Un unico numero, escrito en la SRAM del SMC:

| que | valor |
|---|---|
| donde | `SMU7_FIRMWARE_HEADER_LOCATION + offsetof(SMU74_Firmware_Header, DpmTable)` = `0x20000 + 52` = **`0x20034`** |
| que | la direccion base de la tabla DPM |
| restriccion | debe ser `< 260260` para que quepan los 1884 bytes antes de `0x40000` |

Ese numero **no esta en el corpus**. Vive en la SRAM que escribe el firmware, y el host
solo lo lee (`polaris10_smumgr.c:2500-2506`). Por eso `SMC_RESERVED_TABLE_SIZE` sigue
siendo `RUNTIME_MISSING`, pero la pregunta ya no es abierta: se sabe que hay un solo
numero, donde esta, y que restriccion cumple.

## Lectura util para un driver propio

Si el driver propio pone la tabla en el sitio, la restriccion es una linea. Si la deja
donde la puso el firmware, la restriccion ya la cumple el firmware y no hay que hacer
nada. Lo que **no** puede hacer un driver propio es suponer que la base es fija: el
protocolo es leerla.

No son cuatro punteros: son **seis**, y todos salen de la cabecera del firmware. La
funcion `polaris10_process_firmware_header` (`polaris10_smumgr.c:2492`) los lee uno a
uno con el mismo patron:

| puntero del driver | campo de la cabecera | offset | direccion absoluta |
|---|---|---:|---:|
| `Version` | `Version` | 20 | 131092 |
| `soft_regs_start` | `SoftRegisters` | 48 | 131120 |
| `dpm_table_start` | `DpmTable` | 52 | 131124 |
| `fan_table_start` | `FanTable` | 56 | 131128 |
| `mc_reg_table_start` | `mcRegisterTable` | 68 | 131140 |
| `arb_table_start` | `mcArbDramTimingTable` | 72 | 131144 |

Offsets por gcc sobre la cabecera real. `sizeof(SMU74_Firmware_Header)` = 180, luego la
cabecera ocupa `[0x20000, 0x200B4)`.

**Ninguno lo elige el host.** La cabecera del firmware es un indice: una tabla de
punteros que el host lee para saber donde esta cada cosa. Un driver propio no puede
suponer ninguna de esas seis direcciones, y tiene que leer las seis.

## Clasificacion

- `SMC_HOST_WRITE_FOOTPRINT = PROVEN`: `[0, 1884)`, los 12 usos dentro de la struct.
- `SMC_DPM_TABLE_ADDRESS_SLOT = PROVEN`: `0x20034`, un solo dword.
- `SMC_DPM_TABLE_BASE_CONSTRAINT = PROVEN`: `< 260260`.
- `SMC_DPM_TABLE_BASE_VALUE = RUNTIME_MISSING`: lo decide el firmware, esta en la SRAM.
- `SMC_FIRMWARE_HEADER_INDEX = PROVEN`: seis punteros, offsets 20/48/52/56/68/72 desde
  `0x20000`. Ninguno lo elige el host.

## Lo que esto NO dice

No dice cual es el valor. Ni que el firmware cumpla. Ni que los offsets sean los que el
firmware espera: que el host escriba en el offset correcto de la struct correcta solo
importa si el firmware lee los mismos offsets, y eso no se deduce del host.

No hay lectura de hardware aqui. Todo esto es estatico y la unica ejecucion es un
compilador sobre una cabecera.