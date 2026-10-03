# 221  El firmware que analicé en 115 es el de esta placa, confirmado por dos vías independientes que no comparten nada

WORK_CLASS=READ_ONLY · WRITE_EXECUTION=NONE · MODIFICATIONS 0

CORROBORA Y CIERRA LA PROCEDENCIA DE `115` Y `116` · USA OBSERVACIONES DE `revkit/capturas/`
(ficheros de otro agente, **no modificados**)

## El resultado, en una linea

El campo que lei a mano del blob en `115` es **el mismo campo, en el mismo offset, con el
mismo valor** que el driver leyo del hardware en caliente:

```
polaris12_smc.bin  +16  ->  0x00221700      (yo, a mano, sobre el fichero)
revkit/capturas/amdgpu_firmware_info.txt  ->  0x00221700  (34.23.0)
```

**Y el segundo blob del proyecto tambien cuadra**, por una via que no comparte nada con la
anterior:

```
07-DRIVER/tests/data/polaris12_sdma.bin  size_bytes = 12692 = tamaño del fichero
                                          ucode_version = 0x0000003A
captura:  SDMA0 firmware version 0x0000003a                              -> COINCIDE
```

## Por que esto no es una comprobacion tautologica

Porque **los dos numeros vienen de sitios distintos y por mecanismos distintos**:

| | como lo obtengo | quien lo obtiene en el hardware |
|---|---|---|
| blob SMC | leyendo un fichero del repo | PSP lo descarga, lo copia a VRAM, y el driver lo vuelve a leer |
| blob SDMA | leyendo otro fichero del repo | idem, por su propia via de carga |

Y el **valor del VBIOS** tampoco: `revkit/capturas/amdgpu_vbios.txt` son 58880 B con
`ATOMBIOS BK-AMD VER015.050.002.001.000000` y la cadena `D09001 Lexa XL A0 GDDR5 128bit 2GB`.
Eso es el ROM que **la placa ejecuta**, no un fichero de referencia.

**Mi corpus de analisis esta Measure-anchored a esta placa**, y no lo era antes de hoy.

## La cadena completa, eslabon por eslabon

Para que el numero coincida, tienen que ser verdad **simultaneamente** cinco cosas. Cada
una es una afirmacion por separado, y cada una es comprobable por separado:

1. **El blob del repo es el que carga el PSP.** No un firmware de otra placa.
2. **`polaris12_smc.bin` tiene el layout de cabecera correcto.** Si no, el offset 16 seria
   otra cosa.
3. **La struct esta empaquetada.** Si no, `ucode_version` caeria en otro offset.
4. **El driver lee ese mismo offset.** Rastreado en el codigo, no supuesto.
5. **El valor sobrevive intacto hasta lo que se imprime.** Sin casts que lo trunquen.

Las cinco se cumplen. La 5 es la que casi se rompe: en la rama **no-SMC** el codigo hace

```c
info->version = (uint16_t)le32_to_cpu(header->header.ucode_version);
```

**Un cast a `uint16_t`**, que de `0x00221700` dejaria `0x1700`. Si el SMC pasara por ahi, la
captura imprimiria `0x00001700 (23.0.0)`. Imprime `0x00221700 (34.23.0)`.

La rama del SMC es **otra**, y ahi:

```c
/* amdgpu_cgs.c, rama SMC_UCODE */
hdr    = (const struct smc_firmware_header_v1_0 *)adev->pm.fw->data;
adev->pm.fw_version = le32_to_cpu(hdr->header.ucode_version);   /* sin cast */
info->version       = adev->pm.fw_version;                     /* sin cast */
```

**Sin truncamiento.** Y la cuenta sale exacta:

```
0x00221700 ->  major (>>16)&0xff = 0x22 = 34
               minor (>>8)&0xff  = 0x17 = 23
               debug (&0xff)     = 0x00 = 0     ->  (34.23.0)   coincide
program = (ver >> 24) & 0xff = 0x00 = 0                   coincide
```

## Y la estructura de cabecera, validada por dos vias

Los offsets que use en `115` estan **confirmados por gcc con la cabecera real**, no de
memoria. Y hay **dos layouts distintos** de `common_firmware_header` en este arbol, y
elegir el equivocado no da un error visible:

El que usa el driver (`amdgpu_ucode.h:30-41`), medido con gcc:

```
sizeof = 32
ucode_version           @ 16      <-- el que leo
ucode_size_bytes        @ 20
ucode_array_offset_bytes@ 24
crc32                   @ 28
```

El que casi use por error (el de `atomfirmware.h`, con `USHORT` en vez de `uint32_t`):

```
sizeof = 30
ucode_version           @ 14      <-- el equivocado
```

**La diferencia es de 2 bytes**, y da `ucode_version` en un sitio que no es el suyo. Un
error de 2 bytes no produce basura visible: produce un numero plausible. Es el mismo
peligro que el desfase de 108 de `104`, pero en una dimension mas pequena y **por eso mas
peligroso**, porque un error de 108 se nota y uno de 2 no.

**Y el caso que de verdad importa**: el header del blob declara `header_size_bytes = 36`.
Con el layout correcto, `sizeof(smc_firmware_header_v1_0) = 32 + 4 = 36`. **Coincide.**
Con el equivocado, 30 + 4 = 34. **No coincide.**

O sea: **el propio fichero dice que su header son 36 bytes, y solo un layout da 36.** Esa es una validacion que no necesita gcc, y la hice sin darme cuenta.

## Lo que queda cerrado, y lo que queda abierto

Cerrado, por primera vez en la sesion, **el origen fisico del corpus**:

- `FW_SMC_BLOB_IS_THIS_GPU = PROVEN`
- `FW_SDMA_BLOB_IS_THIS_GPU = PROVEN`
- `VBIOS_IN_CORPUS_IS_THIS_GPU = PROVEN`
- `SMC_HDR_UCODE_VERSION_IS_32BIT_NOT_TRUNCATED = PROVEN_DERIVED`: la rama SMC no castea,
  la otra si. Consecuencia util: **para leer la version del SMC hay que ir por
  `adev->pm.fw_version`, no por el `info->version` de la rama generica.**

**Y sigue abierto, y ahora con mas precision**: el contenido de la region de 220 bytes
reservados (`115`), y el valor en ejecucion de `SMU74_Firmware_Header.DpmTable`. El blob
sigue siendo la imagen, no el estado: `DpmTable` **sigue valiendo 0 ahi**, porque lo
escribe el firmware al arrancar. Lo que he confirmado es **que el fichero es el
correcto**, lo cual era el presupuesto que faltaba, pero **no el valor**.

## Los errores que cometi hoy, y por que los cuenta este documento

Tres en esta tanda, y los tres **del mismo tipo, silenciosos, y con el mismo sintoma: un numero
plausible en el offset equivocado**:

1. **Compile una struct empaquetada sin `pack`.** Offset 54 en vez de 53.
2. **Un regex de extraccion que descarto `ATOM_COMMON_TABLE_HEADER`** por no ser escalar.
   4 bytes de mas.
3. **Escribi el layout de `common_firmware_header` de memoria**, con `USHORT` donde el
   driver usa `uint32_t`. Offset 14 en vez de 16.

El primero y el tercero me los cazó **el mismo mecanismo**: una comprobación cruzada. El
segundo, por un guard que puse antes del dato importante.

**Lo que los tres tienen en comun, y que es la regla que sale de todo esto:**

> **Un numero plausible en el offset equivocado es indistinguible de un numero correcto.**
> No se caza mirando el numero. Se caza **midiendo el mismo dato por otro camino**:
> `sizeof` contra `usTableSize`, `ucode_version` contra lo que reporta el driver, el orden
> termico contra la temperatura real.

Ese es el motivo por el que, en esta sesion, casi todos los hallazgos buenos salieron de
**cruzar dos medidas independientes**, y casi todos los malos, de **leer una sola**.

## Clasificacion

- `FW_SMC_BLOB_IS_THIS_GPU = PROVEN`: `ucode_version @16 = 0x00221700` en el blob, y
  `0x00221700 (34.23.0)` en la captura. **Mismo offset, mismo valor, sin cast.**
- `FW_SDMA_BLOB_IS_THIS_GPU = PROVEN`: `ucode_version = 0x0000003A` coincide con
  `SDMA0 firmware version 0x0000003a`. Via independiente de la anterior.
- `SMC_VERSION_SURVIVES_UNTRUNCATED = PROVEN_DERIVED`: la rama SMC asigna
  `info->version = adev->pm.fw_version` sin cast; la rama no-SMC castea a `uint16_t`. La
  cuenta `>>16/>>8/&0xff` reproduce exactamente `(34.23.0)` y `program = 0`.
- `COMMON_FIRMWARE_HEADER_OFFSETS_MEASURED = PROVEN`: `sizeof = 32`, `ucode_version @ 16`,
  `ucode_size_bytes @ 20`, `ucode_array_offset_bytes @ 24`, `crc32 @ 28`, con gcc sobre
  `amdgpu_ucode.h`.
- `TWO_COMMON_HEADER_LAYOUTS_EXIST = PROVEN`: `amdgpu_ucode.h` (32 B, `ucode_version@16`) y
  `atomfirmware.h` (30 B, `ucode_version@14`). **Elegir el equivocado no da error visible.**
- `HEADER_SIZE_BYTES_SELLS_THE_LAYOUT = PROVEN_DERIVED`: el blob declara 36;
  `sizeof(smc_firmware_header_v1_0)` = 36 **solo** con el layout correcto. Validacion sin
  gcc, disponible desde el propio fichero.
- `115_116_OFFSETS_ARE_CORRECT = PROVEN`: los offsets de `115` (blob) y `116` (VBIOS) se
  sostienen tras la revision. **No habia que corregirlos.**
- `CORPUS_IS_PHYSICALLY_ANCHORED_TO_THIS_GPU = PROVEN_DERIVED`: los tres artefactos
  (SMC, SDMA, VBIOS) son los de `dev=0000:01:00.0` en esta maquina.
- `CAPTURE_PROVENANCE_IS_THE_CORPUS = PROVEN`: la cadena
  `amdgpu_kms.c:1903` usa `firmware version`; la de `amdgpu_dev_coredump.c:163` usa
  `fw version`. La captura tiene la **primera**, luego salio de `amdgpu_kms.c`, **que esta en
  mi corpus**. Verificado por la cadena exacta, no por el kernel instalado.
- `DPM_TABLE_RUNTIME_VALUE_STILL_UNKNOWN = NOT_AVAILABLE`: sin cambio. El blob es la
  **imagen**, no el estado de ejecucion. `115` sigue en pie.
- `TWO_BYTE_OFFSET_ERRORS_ARE_THE_DANGEROUS_ONES = PROVEN_DERIVED`: un error de 108 B se
  nota; uno de 2 B produce un numero plausible. **El tamano del error no es su
  gravedad.**

## Lo que esto obliga a hacer en un driver propio

1. **Validar el tamano del registro contra el propio registro.** El
   `header_size_bytes` del firmware (36) tiene que ser igual a `sizeof` de la struct que
   uno usa. Es una linea, no necesita gcc, y **es lo unico que distingue un layout de otro
   cuando la struct tiene 30 o 32 bytes y todo lo demas parece bien**.
2. **No asumir que dos cabeceras con el mismo nombre son la misma.** En este arbol hay dos
   `common_firmware_header` distintos, en ficheros distintos, con `uint32_t` contra
   `USHORT`. `NAME_MATCH != SEMANTIC_MATCH` aplicado a una struct: el nombre coincide y
   el offset no.
3. Y para mi propia sesion, que es lo mas util: **todo hallazgo mio que se haya derivado
   de leer un solo sitio tiene que marcarse como "no cruzado"** hasta que tenga una segunda
   medida. He hecho eso en `104` con el hueco de 108: era un error de 108 B, que se veia.
   Los que no se ven son los de 2 y 4 bytes.