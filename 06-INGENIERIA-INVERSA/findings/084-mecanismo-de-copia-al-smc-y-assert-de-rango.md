# 084 · El mecanismo de copia al SMC: dword a dword, MSB primero, con assert de rango

WORK_CLASS=READ_ONLY · WRITE_EXECUTION=NONE · MODIFICATIONS 0

## Que se corrige en mi propia caracterizacion

A lo largo de la auditoria de `083` trataba el quinto argumento de `smu7_copy_bytes_to_smc`
como una bandera. **No lo es.** Es el limite superior de la RAM del SMC, y el driver
comprueba con el que la copia no se sale. La suposicion era mia y hacia que el
parametro pareciera intercambiable, que es exactamente lo contrario de lo que es.

Firma real, `pm/powerplay/smumgr/smu7_smumgr.h:56` y `smumgr/smu7_smumgr.c:49`:

```c
int smu7_copy_bytes_to_smc(struct pp_hwmgr *hwmgr, uint32_t smc_start_address,
                           const uint8_t *src, uint32_t byte_count, uint32_t limit);
```

## Las dos comprobaciones que hace

`smumgr/smu7_smumgr.c:58-59`, antes de tocar nada:

```c
PP_ASSERT_WITH_CODE((0 == (3 & smc_start_address)),
        "SMC address must be 4 byte aligned.", return -EINVAL);
PP_ASSERT_WITH_CODE((limit > (smc_start_address + byte_count)),
        "SMC address is beyond the SMC RAM area.", return -EINVAL);
```

Esto **cierra el riesgo que `081` dejo abierto**. Alli escribi que si
`dpm_table_start` estuviera cerca del final de la RAM, la diferencia entre 1012 y 1776
bytes decidiria si la subida cabe, y lo deje como `NOT_DETERMINED`.

No es `NOT_DETERMINED`: la comprobacion existe, se ejecuta en cada copia, y devuelve
`-EINVAL`. Una tabla truncada **no** se cuela en silencio por el desbordamiento de
rango. Devuelve error, y el llamante hace `PP_ASSERT_WITH_CODE(0 == result, ...)`.

Consecuencia: un error de tamano en la copia se manifestaria como un fallo de
`polaris10_init_smc` o del equivalente, no como voltaje erratico. El sintoma que si es
silencioso es el **contenido**: copied los bytes correctos en la direccion correcta y el
contenido estaba mal.

## El limite y la ventana

`SMC_RAM_END = 0x40000` = 262144 bytes, en `smumgr/polaris10_smumgr.h:33`,
`smumgr/smu7_smumgr.h:30` y `smumgr/vegam_smumgr.h:32`.

Con la copia de la tabla DPM (`polaris10_smumgr.c:2118`):

```
dpm_table_start + 108 + 1776 < 0x40000
dpm_table_start + 1884        < 262144
dpm_table_start               < 0x3F8A4   (260260)
```

Verificado por gcc. Una version anterior de este documento decia `261924` en decimal
para ese mismo `0x3F8A4`: la aritmetica estaba mal, el hexadecimal no. Corregido.

## La direccion la elige el firmware, no el host

`polaris10_smumgr.c:131-136`:

```c
PP_ASSERT_WITH_CODE(0 == smu7_read_smc_sram_dword(hw,
                SMU7_FIRMWARE_HEADER_LOCATION + offsetof(SMU74_Firmware_Header, DpmTable),
                &dpm_table_start, 0x40000),
        "[AVFS][...] SMU could not communicate starting address of DPM table",
        return -1);
```

El host **pregunta al firmware** donde esta la tabla. No la coloca.

Medido:

| magnitud | valor |
|---|---|
| `SMU7_FIRMWARE_HEADER_LOCATION` | `0x20000` |
| `sizeof(SMU74_Firmware_Header)` | 180 |
| `offsetof(SMU74_Firmware_Header, DpmTable)` | 52 (`0x34`) |
| direccion absoluta del campo | `0x20034` |
| ventana de RAM del SMC | `[0, 0x40000)` = 256 KB |

De ahi que la pregunta "¿caben 1776 bytes?" no tenga respuesta estatica: depende del
valor que el firmware tenga escrito en `0x20034`, que esta en la SRAM del SMC, no en el
corpus. `SMC_RESERVED_TABLE_SIZE` sigue siendo `RUNTIME_MISSING`, pero ahora se sabe
**quien** lo decide y **que** lo comprobaria.

## Como se escribe de verdad: dword a dword, MSB primero

La copia no es `memcpy`. `smu7_smumgr.c:63-77`:

```c
while (byte_count >= 4) {
        /* Bytes are written into the SMC addres space with the MSB first. */
        data = src[0] * 0x1000000 + src[1] * 0x10000 + src[2] * 0x100 + src[3];
        result = smu7_set_smc_sram_address(hwmgr, addr, limit);
        ...
        cgs_write_register(hwmgr->device, mmSMC_IND_DATA_11, data);
        src += 4;  byte_count -= 4;  addr += 4;
}
```

Cada palabra se monta a mano con el primer byte en el bit 31. Un `memcpy` al SMC estaria
byte-swapeado.

## El resto, que es lo que hace validas las copias de 1 byte

`smu7_smumgr.c:79-109`. Si sobran bytes, **no** se escribe una palabra entera: lee la
que hay, la conserva, y sustituye solo la parte alta.

```c
original_data = cgs_read_register(hwmgr->device, mmSMC_IND_DATA_11);
extra_shift = 8 * (4 - byte_count);
while (byte_count > 0) { data = (0x100 * data) + *src++; byte_count--; }
data <<= extra_shift;
data |= (original_data & ~((~0UL) << extra_shift));
```

Comprobado con los tres casos, porque es lo que hace que `sizeof(u8)` sea una copia
**completa** y no una escritura de un byte con los otros tres de rubbish:

| `byte_count` | `extra_shift` | bytes conservados | posicion del nuevo dato |
|---|---|---|---|
| 1 | 24 | los 3 bajos del original | bits 31..24 |
| 2 | 16 | los 2 bajos | bits 31..16 |
| 3 | 8 | el byte bajo | bits 31..8 |

En los tres, `(~0UL) << extra_shift` es la mascara de los bits altos y su complemento
son los bits que **no** se tocan. Coherente con "MSB first".

Por eso las 18 copias de 1 byte y las 12 de 4 bytes de la auditoria de `083` son
correctas por construccion, y no por casualidad.

## Lo que esto NO dice

No dice que hace el firmware con los bytes. No dice si el orden MSB primero es el que el
firmware espera: eso solo lo dice el firmware, y no esta en el corpus.

No dice que el contenido de la tabla sea correcto. La tabla se rellena en
`polaris10_populate_all_graphic_levels` y las funciones de voltaje, y eso es otra linea.

## Clasificacion

- `SMC_COPY_MECHANISM = PROVEN`: dword a dword, MSB primero, con ruta de resto que
  preserva los bytes no escritos.
- `SMC_COPY_RANGE_CHECK = PROVEN`: dos asserts, alineacion de 4 y `limit > addr + n`,
  ambos devuelven `-EINVAL`.
- `SMC_RAM_LIMIT = PROVEN`: `0x40000` = 262144 bytes.
- `SMC_TABLE_ADDRESS_ORIGIN = FIRMWARE_OWNED`: el host lo lee de `0x20034`, no lo elige.
- `SMC_RESERVED_TABLE_SIZE = RUNTIME_MISSING`: lo decide el valor en la SRAM del SMC.
- `SMC_COPY_TRUNCATION_SILENT = REFUTED`: el desbordamiento de rango da error, no
  voltaje erratico. El sintoma silencioso posible es de contenido, no de longitud.