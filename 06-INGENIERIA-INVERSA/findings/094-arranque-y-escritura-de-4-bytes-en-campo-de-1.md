# 094 · El arranque: de donde salen los voltajes de boot, y una escritura de 4 bytes en un campo de 1

WORK_CLASS=READ_ONLY · WRITE_EXECUTION=NONE · MODIFICATIONS 0

## De donde salen los valores de arranque

No estan cocidos en el driver. Vienen de la tabla de firmware del VBIOS:

`smu7_hwmgr.c:3636-3653`, en `smu7_dpm_patch_boot_state`:

```c
fw_info = (ATOM_FIRMWARE_INFO_V2_2 *)smu_atom_get_data_table(hwmgr->adev, index, &size, &frev, &crev);
if (!fw_info)
        /* During a test, there is no firmware info table. */
        return 0;

data->vbios_boot_state.sclk_bootup_value  = le32_to_cpu(fw_info->ulDefaultEngineClock);
data->vbios_boot_state.mclk_bootup_value  = le32_to_cpu(fw_info->ulDefaultMemoryClock);
data->vbios_boot_state.mvdd_bootup_value  = le16_to_cpu(fw_info->usBootUpMVDDCVoltage);
data->vbios_boot_state.vddc_bootup_value  = le16_to_cpu(fw_info->usBootUpVDDCVoltage);
data->vbios_boot_state.vddci_bootup_value = le16_to_cpu(fw_info->usBootUpVDDCIVoltage);
data->vbios_boot_state.pcie_gen_bootup_value  = smu7_get_current_pcie_speed(hwmgr);
data->vbios_boot_state.pcie_lane_bootup_value = smu7_get_current_pcie_lane_number(hwmgr);
```

El comentario **"During a test, there is no firmware info table"** es la pista: el
conductor contempla que falte.

## Dos sitios donde faltar datos se convierte en exito

### 1. El VBIOS sin tabla de firmware

Si `fw_info` es nulo, la funcion **devuelve 0** y `vbios_boot_state` se queda entero en
ceros, porque el `struct smu7_hwmgr` se crea con `kzalloc_obj`
(`smu7_hwmgr.c:3030`). El driver no distingue "no hay VBIOS" de "arranca a cero".

### 2. El nivel de arranque no encontrado

`polaris10_populate_smc_boot_level`, `polaris10_smumgr.c:1577-1615`:

```c
table->GraphicsBootLevel = 0;
table->MemoryBootLevel  = 0;

result = phm_find_boot_level(&(data->dpm_table.sclk_table),
                data->vbios_boot_state.sclk_bootup_value,
                (uint32_t *)&(table->GraphicsBootLevel));
if (result) {
        table->GraphicsBootLevel = 0;
        result = 0;                     /* <- el error se borra */
}


result = phm_find_boot_level(&(data->dpm_table.mclk_table), ..., &table->MemoryBootLevel);
if (result) {
        table->MemoryBootLevel = 0;
        result = 0;                     /* <- otra vez */
}
...
return 0;                               /* y la funcion devuelve 0 SIEMPRE */
```

**La funcion no puede devolver un fallo.** Los dos `result = 0` lo borran y el `return`
es un `0` literal, no `result`. Quien la llame no tiene forma de saber si el nivel de
arranque se encontro o se dio por defecto.

> **CORRECCION IMPORTANTE 2026-10-02.** Este documento afirmaba que el
> `GraphicsBootLevel` que acaba en la SRAM del SMC es el que produce
> `phm_find_boot_level`. **Es falso, y lo es por la razon mas incomoda posible: por que
> ese valor se descarta.** Hay un **segundo escritor del mismo campo**, en
> `polaris10_populate_smc_initailial_state` (`:1627-1633`), que se ejecuta **despues**
> (llamada en `:1992`, la de este documento en `:1988`) y lo **sobrescribe** con un indice
> belonging a otro espacio de indices. Como `table` es `&(smu_data->smc_state_table)`
> (`:1921`), las dos escrituras van al **mismo byte de la misma struct**.
>
> O sea: todo el analisis de este documento sobre el valor final de
> `GraphicsBootLevel` describe un valor que se pisa siete lineas despues de su funcion.
> Lo que sobrevive y sigue siendo valido es el analisis del **desbordamiento de 4 bytes**
> (el `(uint32_t *)` sobre un campo de 1 byte), porque ese lo hace la primera
> escritura. Ver `098` para el valor que llega de verdad.

El valor por defecto es el **nivel 0**, que es un nivel de arranque valido. O sea: un
fallo produce un valor perfectly plausible.

### Compuestos

Los dos se pueden dar a la vez. Con un VBIOS sin tabla de firmware: voltages de arranque
a 0, relojes de arranque a 0, `phm_find_boot_level(0)` falla, nivel de arranque a 0, y
**todo el camino reporta exito**. La tabla DPM sube al SMC con voltajes de boot en cero.

Es el mismo patron de "produce algo plausible en vez de un error" que vengo documentando,
aqui en el driver y ademas a tres capas: VBIOS, busqueda de nivel, y la funcion que
agrega.

## La escritura de 4 bytes en un campo de 1

`phm_find_boot_level` recibe `(uint32_t *)` y escribe `*boot_level = i`, o sea cuatro
bytes. Los dos campos de destino son de **un byte**:

| campo | offset | bytes |
|---|---:|---:|
| `GraphicsBootLevel` | 1580 | 1 |
| `MemoryBootLevel` | 1590 | 1 |

Medido sobre `smu74_discrete.h:298-320`. Los vecinos que caen dentro de esos cuatro
bytes:

```
1576 UvdBootLevel              1584 VoltageInterval
1577 VceBootLevel              1585 ThermalInterval
1578 AcpBootLevel              1586 TemperatureLimitHigh  (u16)
1579 SamuBootLevel             1588 TemperatureLimitLow   (u16)
1580 GraphicsBootLevel   <--   1590 MemoryBootLevel   <--
1581 GraphicsVoltageChangeEnable      1591 MemoryVoltageChangeEnable
1582 GraphicsThermThrottleEnable      1592 BootMVdd  (u16)
1583 GraphicsInterval                 1594 MemoryInterval
```

O sea, la escritura de 4 bytes sobre `GraphicsBootLevel` pone a cero
`GraphicsVoltageChangeEnable`, `GraphicsThermThrottleEnable` y `GraphicsInterval`; y sobre
`MemoryBootLevel` pone a cero `MemoryVoltageChangeEnable` y **`BootMVdd`**, que es un
voltaje.

Es dos cosas a la vez: una violacion de aliasing estricto (escribir un `uint32_t` a
traves de un puntero a un `uint8_t`) y un desbordamiento de tres bytes.

### En esta ruta no se nota, y por que

Verificado el orden, que es lo unico que lo salva:

- `polaris10_init_smc_table` empieza en `polaris10_smumgr.c:1913`
- llama a `polaris10_populate_smc_boot_level` en la linea **1988**
- y los vecinos se escriben **despues**, en las lineas **2014-2025**:

```c
table->GraphicsVoltageChangeEnable  = 1;    /* 2014 */
table->GraphicsThermThrottleEnable = 1;    /* 2015 */
table->GraphicsInterval            = 1;    /* 2016 */
table->MemoryVoltageChangeEnable   = 1;    /* 2025 */
```

Y `BootMVdd` se escribe **dentro de la propia funcion**, despues del almacen de
`MemoryBootLevel` (`polaris10_smumgr.c:1607` frente a `:1600`).

Asi que los cuatro campos pisados se reescriben a 1 acto seguido, y `BootMVdd` se
reescribe dentro de la misma funcion. **El efecto observable en esta ruta es nulo.**

### Por que sigue siendo un hallazgo

Porque lo que lo neutraliza es el **orden de unas sentencia** en una funcion, no una
invariante. Si alguien mueve `polaris10_populate_smc_boot_level` despues del bloque de
las lineas 2014-2025, los cuatro campos se quedan a cero y no hay ningun aviso: el host
cree que ha puesto a 1 los flags de cambio de voltaje y el throttle termico de graficos.

Un driver propio no debe copiar el`(uint32_t *)&campo_de_un_byte`. Es un `uint8_t` y
 punto.

## Lo que NO es un bug: la conversion de tipo de phm_find_boot_level

`phm_find_boot_level` hace `(struct vi_dpm_table *)table` sobre un puntero `void *`, lo
cual huele. Comprobado:

```
vi_dpm_level     12 bytes    enabled @0 (1B)   value @4 (4B)   param1 @8 (4B)
smu7_dpm_level   12 bytes    enabled @0 (1B)   value @4 (4B)   param1 @8 (4B)
```

Y las dos tablas empiezan igual: `uint32_t count` seguido del array de niveles. La
conversion es **compatible**, medida y no supuesta. La funcion se usa con ambos tipos
indistintamente y Es correcto.

## Un detalle mas: phm_find_boot_level no tiene break

```c
for (i = 0; i < dpm_table->count; i++) {
        if (value == dpm_table->dpm_level[i].value) {
                *boot_level = i;
                result = 0;
        }
}
```

Sigue recorriendo despues de encontrar. Si dos entradas tienen el mismo valor, **gana
la ultima**, no la primera. Con una tabla deduplicada da igual; con duplicados, el nivel
de arranque es el mayor indice, no el menor.

## Clasificacion

- `SMC_BOOT_VALUES_FROM_VBIOS = PROVEN`: `ATOM_FIRMWARE_INFO_V2_2` ->
  `vbios_boot_state`, en `smu7_dpm_patch_boot_state`.
- `SMC_BOOT_PATCH_LIVE = PROVEN`: `smu7_hwmgr_funcs` (`:5857`) se asigna a
  `hwmgr->hwmgr_func` en `:5940` y **Polaris12 no lo sobreescribe**, luego
  `smu7_dpm_patch_boot_state` es el camino vivo.
- `SMC_BOOT_MISSING_VBIOS_RETURNS_SUCCESS = PROVEN`: sin tabla de firmware devuelve 0
  con el estado de arranque a cero.
- `SMC_BOOT_LEVEL_ALWAYS_RETURNS_ZERO = PROVEN`: dos `result = 0` y un `return 0`
  literal. La funcion no puede fallar.
- `SMC_BOOT_LEVEL_DEFAULT_IS_VALID = PROVEN`: el valor por defecto es el nivel 0, que es
  valido.
- `SMC_BOOT_LEVEL_WRITE_OVERRUN = PROVEN`: `*(uint32_t*)` sobre un campo de 1 byte, con
  tres vecinos dentro, uno de ellos `BootMVdd`.
- `SMC_BOOT_LEVEL_OVERRUN_MASKED_BY_ORDER = PROVEN`: los vecinos se reescriben a 1 en
  las lineas 2014-2025, despues de la llamada en 1988. Efecto observable nulo.
- `SMC_FIND_BOOT_LEVEL_ALIAS_SAFE = PROVEN`: `vi_dpm_level` y `smu7_dpm_level` miden 12
  bytes con los mismos offsets. No es un bug.
- `SMC_FIND_BOOT_LEVEL_NO_BREAK = PROVEN`: con valores duplicados gana el ultimo indice.

## Lo que esto NO dice

No dice que falte la tabla de firmware en esta placa. No he leido el VBIOS: es un
hallazgo estatico sobre la ruta de codigo.

No dice que un nivel de arranque 0 estuviera mal en ningun caso concreto. Es un valor
valido; lo que no se puede distinguir es si es el que toca.

No hay lectura de hardware aqui, no hay escritura, no hay `/sys`, no hay modulos.