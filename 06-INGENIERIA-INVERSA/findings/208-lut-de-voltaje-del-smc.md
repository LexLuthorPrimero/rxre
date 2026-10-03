# 208  La LUT de voltaje del SMC: tres rails, una sola tabla, y una asimetria sin explicar

WORK_CLASS=READ_ONLY · WRITE_EXECUTION=NONE · MODIFICATIONS 0

## Lo que hay en la tabla

Medido, no estimado:

```
SMIO_Pattern   4 bytes    Voltage u16 @0   Smio u8 @2   padding u8 @3
SMIO_Table    16 bytes    Pattern[SMU_MAX_SMIO_LEVELS]   = 4 x 4
SMU_MAX_SMIO_LEVELS = 4
```

Y en la tabla DPM:

```
SmioTable1   offset 124   16 bytes    SMIO_Table
SmioTable2   offset 140   16 bytes    SMIO_Table
SmioMask1    offset 116    4 bytes    uint32_t
SmioMask2    offset 120    4 bytes    uint32_t
Smio         offset 1320  128 bytes    uint32_t[SMU74_MAX_ENTRIES_SMIO], y ese valor es 32
```

## Como se rellena

Tres funciones, y las tres estan **condicionadas a que el rail se controle por GPIO**:

`polaris10_smumgr.c:770-772`, el orden de llamada:

```c
polaris10_populate_smc_vddc_table(hwmgr, table);
polaris10_populate_smc_vddci_table(hwmgr, table);
polaris10_populate_smc_mvdd_table(hwmgr, table);
```

Cada una, si su rail es `SMU7_VOLTAGE_CONTROL_BY_GPIO`, escribe su LUT:

```c
count = data->vddci_voltage_table.count;
if (SMU7_VOLTAGE_CONTROL_BY_GPIO == data->vddci_control) {
        if (count > SMU_MAX_SMIO_LEVELS)
                count = SMU_MAX_SMIO_LEVELS;
        for (level = 0; level < count; ++level) {
                table->SmioTable1.Pattern[level].Voltage =
                        PP_HOST_TO_SMC_US(entries[level].value * VOLTAGE_SCALE);
                table->SmioTable1.Pattern[level].Smio = (uint8_t) level;
                table->Smio[level] |= entries[level].smio_low;
        }
        table->SmioMask1 = data->vddci_voltage_table.mask_low;
}
```

Con los tres modos posibles (`smu7_hwmgr.h:32-35`):

```
SMU7_VOLTAGE_CONTROL_NONE        0x0
SMU7_VOLTAGE_CONTROL_BY_GPIO     0x1
SMU7_VOLTAGE_CONTROL_BY_SVID2    0x2
SMU7_VOLTAGE_CONTROL_MERGED      0x3
```

**Un rail que no se controle por GPIO no contribute LUT ninguna.** La tabla se queda
como estuviera. O sea: si ninguno de los tres rails es GPIO, el firmware recibe la LUT
de voltaje **vacia**, y no hay ningun campo que le diga que esta vacia.

## Tres cosas que no son obvias

### 1. `SmioTable1` la escriben dos funciones

`polaris10_populate_smc_vddc_table` y `polaris10_populate_smc_vddci_table` escriben las
**mismas** dos estructuras, `SmioTable1.Pattern[]` y `SmioMask1`. Por el orden de
llamada, **gana VDDCI**: si los dos rails son GPIO, la LUT que sube el host es la de
VDDCI y la de VDDC se pierde sin dejar rastro.

No es un fallo: puede ser la decision correcta, con el rail de memoria tomando
precedencia. Lo que si es cierto es que **solo hay sitio para un rail**, y cual de los
dos gana lo decide el orden de dos lineas, no un campo de la tabla.

### 2. `table->Smio[level] |= ...` acumula entre rails

El `|=` en vez de `=` significa que los tres rails van escribiendo **en el mismo array**.
Si dos rails son GPIO y ambos usan el mismo indice de nivel, sus bits se mezclan en la
misma palabra. Si el firmware lee `Smio[level]` como "los bits SMIO para este nivel", un
`|=` acumulado es lo que hace falta. Si lo lee por rail, no lo es.

No se puede decidir desde el host: es `FW_SMU_INTERPRETATION`, y sigue `NOT_IN_CORPUS`.

### 3. El array tiene 32 entradas y se escriben 4

`Smio[SMU74_MAX_ENTRIES_SMIO]` con `SMU74_MAX_ENTRIES_SMIO = 32` (`smu74.h:142`), o sea
128 bytes. El bucle escribe `level < count <= SMU_MAX_SMIO_LEVELS = 4`. Es decir: **112 de
los 128 bytes nunca los escribe el host.**

Y a diferencia de las demas tablas, `Smio[]` **no tiene ningun campo de contador** al
lado. `GraphicsLevel` viene con `GraphicsDpmLevelCount`, `UvdLevel` con
`UvdLevelCount`. `Smio[]` no tiene nada: su longitud utilizable la tiene que saber el
firmware por su cuenta, con su propia copia de `SMU_MAX_SMIO_LEVELS`.

Para un driver propio: si se rellenan menos de 4 niveles, no hay forma de declararlo en la
tabla. Es el unico array de la tabla DPM sin contador al lado.

## El limite SI se comprueba aqui

Contraste con `091`, donde el bucle de niveles no acotaba. Aqui si:

```c
if (count > SMU_MAX_SMIO_LEVELS)
        count = SMU_MAX_SMIO_LEVELS;
```

en las tres funciones. Y el limite coincide con el destino: `Pattern[4]` y se escribe
`level < 4`. Es el patron correcto — cota explicita, comprobada y coherente con el
destino. Lo que `091` echa de menos es precisamente esto.

## La asimetria que no puedo explicar

`SmioMask1` y `SmioMask2` **se intercambian de bytes**:

```c
CONVERT_FROM_HOST_TO_SMC_UL(table->SmioMask1);
CONVERT_FROM_HOST_TO_SMC_UL(table->SmioMask2);
```

y son `uint32_t`. Las entradas de `table->Smio[level]` **no se intercambian**, y tambien
son `uint32_t`, con el valor tomado del VBIOS ya en orden nativo
(`le32_to_cpu(lut->ulVoltageId)`).

Las dos cosas vienen de la misma lectura de VBIOS y van al mismo array de la misma
tabla. Que una se intercambie y la otra no puede ser correcto en los dos casos con la
misma logica. **No se cual de las dos es la que el firmware espera**, y no lo voy a
adivinar: decidirlo es leer el firmware, que no esta en el corpus.

Lo que si se puede decir: es la unica excepcion a la regla de `090`. Ahi se verifico que
los 63 campos de los structs de nivel cumplen "todo campo de mas de un byte se
intercambia con su ancho". Aqui hay 32 `uint32_t` que no se intercambian y 2 que si, en
la misma tabla.

## Lo que hace un driver propio

1. Rellenar la LUT solo para los rails que controle por GPIO, y ser consciente de que
   un rail no-GPIO no deja rastro.
2. Si dos rails son GPIO, saber que en `SmioTable1` gana el ultimo.
3. Acotar a 4, como hace el driver.
4. No poder declarar "solo tengo 2 niveles": no hay contador para `Smio[]`.
5. No decidir por cuenta propia si `Smio[]` se intercambia o no. Esa pregunta es del
   firmware.

## Clasificacion

- `SMC_SMIO_LAYOUT = PROVEN`: `SMIO_Pattern` 4 bytes, `SMIO_Table` = `Pattern[4]`,
  `Smio[32]` de `uint32_t` en el offset 1320.
- `SMC_SMIO_CLAMP_PRESENT = PROVEN`: `if (count > SMU_MAX_SMIO_LEVELS) count = 4`, en las
  tres funciones. Contraste con el bucle sin cota de `091`.
- `SMC_SMIO_GATED_BY_GPIO = PROVEN`: los tres rails solo contribuyen si son
  `SMU7_VOLTAGE_CONTROL_BY_GPIO`.
- `SMC_SMIO_TABLE1_OVERWRITTEN = PROVEN`: vddc y vddci escriben la misma tabla; gana
  vddci por el orden de las llamadas 770-771.
- `SMC_SMIO_ARRAY_NO_COUNT = PROVEN`: `Smio[]` no tiene contador al lado, y el host
  escribe 4 de 32 entradas.
- `SMC_SMIO_BYTESWAP_ASYMMETRY = PROVEN` la asimetria, `NOT_DETERMINED` cual de las dos
  es la correcta.

## Lo que esto NO dice

No dice si el firmware lee `Smio[]` como mascara por nivel o por rail. De ahi depende si
el `|=` acumulado es correcto.

No dice si el intercambio de `Smio[]` es un fallo o una excepcion deliberada. Es la
unica excepcion a la regla de `090` y no hay forma de decidirla desde el host.

No hay lectura de hardware aqui, no hay escritura, no hay `/sys`, no hay modulos.