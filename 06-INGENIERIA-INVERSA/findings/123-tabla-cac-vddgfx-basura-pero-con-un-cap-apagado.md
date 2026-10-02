# 123 · La tabla CAC de VDDGFX de esta placa contiene basura (`0xFF02`..`0xFF08`), y no se lee por un cap apagado

WORK_CLASS=READ_ONLY · WRITE_EXECUTION=NONE · MODIFICATIONS 0

COMPLETA `122` (los caps) · USA EL VBIOS REAL · cadena de tres hechos independientes que se
explican entre si

## El hallazgo, en dos partes

**Parte 1 · un defecto real de validacion**, que no depende de mi placa:

```c
/* process_pptables_v1_0.c:165-186 */
PP_ASSERT_WITH_CODE((0 != vddc_lookup_pp_tables->ucNumEntries),
        "Invalid CAC Leakage PowerPlay Table!", return 1);

table = kzalloc_flex(*table, entries, max_levels);          /* reserva max_levels */
table->count = vddc_lookup_pp_tables->ucNumEntries;         /* cuenta del VBIOS */
for (i = 0; i < vddc_lookup_pp_tables->ucNumEntries; i++) { /* escribe hasta la cuenta */
        ... entries[i] ...
}
```

**`max_levels` y `ucNumEntries` son dos variables distintas y no se comparan nunca.**
`max_levels` es un parametro que los dos call sites pasan **hardcodeado a 16**
(`:283` y `:292`), y `ucNumEntries` es un `UCHAR` del VBIOS: **0..255**.

Un VBIOS con 17 o mas entradas escribe fuera de la reserva. El unico check es que no sea
cero. **Es el mismo patron que `120`, y aqui es mas limpio**, porque las dos cantidades
estan **en la misma funcion**, a cuatro lineas de distancia, y no hay ninguna que las ligue.

**Parte 2 · lo que hace en MI placa esa tabla es basura, y no se lee.**

## La tabla CAC de VDDGFX de este VBIOS no contiene voltajes

```
tabla VDDGFX CAC @ 0x9CD3   ucRevId = 0   ucNumEntries = 8

bytes crudos:
0x9CD3  00 08  84 03 00 00 00 00 00 00  02 ff 00 00 00 00 00 00
0x9CE3  03 ff 00 00 00 00 00 00  04 ff 00 00 00 00 00 00 ...

leido como 4 x USHORT, stride 8:
  entrada 0: 900, 0, 0, 0           hex 0384
  entrada 1: 65282, 0, 0, 0        hex ff02     <-- 0xFF + indice
  entrada 2: 65283, 0, 0, 0        hex ff03
  entrada 3: 65284, 0, 0, 0        hex ff04
  entrada 4: 65285, 0, 0, 0        hex ff05
  entrada 5: 65286, 0, 0, 0        hex ff06
  entrada 6: 65287, 0, 0, 0        hex ff07
  entrada 7: 65288, 0, 0, 0        hex ff08
```

**`0xFF02` a `0xFF08` es un marcador `0xFF` seguido de un indice que sube de 2 a 8.** No es
un voltaje: el maximo razonable en una GPU esta alrededor de 1200 mV, y 65282 mV esta tres
veces por encima de lo que el siliconio acepta.

**El stride de 8 B esta confirmado**, porque 8 entradas desde `0x9CD5` terminan en `0x9D15`,
que es exactamente donde empieza la tabla SCLK. **El dato es malo, no la lectura.**

Y la tabla **VDDC** sibling esta bien: 10 entradas, 700, 750, 800, 850, 875, 900, 950, 1000,
1050, 1100 mV. Margen de 6 hasta las 16. Los tres CAC (`usCACLow/Mid/High`) estan a cero en
ambas: esta placa **no tiene datos de corriente** en el PPT.

## Y hay un indice que se sale de la tabla

La tabla SCLK (`0x9D15`) trae `ucVddInd` por nivel, y el driver lo usa como indice:

```c
/* smu7_hwmgr.c:2216-2221 */
if (data->vdd_gfx_control == SMU7_VOLTAGE_CONTROL_BY_SVID2) {
        for (entry_id = 0; entry_id < sclk_table->count; ++entry_id) {
                voltage_id = sclk_table->entries[entry_id].vddInd;
                sclk_table->entries[entry_id].vddgfx =
                        table_info->vddgfx_lookup_table->entries[voltage_id].us_vdd;
        }
}
```

Los ocho `ucVddInd` de mi VBIOS son **0, 2, 2, 5, 6, 7, 8, 9**. La tabla VDDGFX tiene **8
entradas, indices 0..7**.

**Los dos estados mas altos de graficos (1046 y 1071 MHz) indexan en 8 y 9, que no existen.**

Eso **no** es una invasion: la reserva es de `max_levels = 16`, asi que 8 y 9 estan dentro de
la memoria reservada y `kzalloc` los tiene a cero. **Se leen ceros.** No es una mancha de
heap, es un **fallo de busqueda silencioso**: el nivel mas rapido recibe voltaje 0.

## Por que no ocurre nada de esto en esta placa

**Porque el cap que abre esa puerta esta apagado**, y el cap viene del mismo VBIOS:

```c
/* smu7_hwmgr.c:1883-1889 */
if (phm_cap_enabled(hwmgr->platform_descriptor.platformCaps, PHM_PlatformCaps_ControlVDDGFX)) {
        if (atomctrl_is_voltage_controlled_by_gpio_v3(hwmgr, VOLTAGE_TYPE_VDDGFX, VOLTAGE_OBJ_SVID2)) {
                data->vdd_gfx_control = SMU7_VOLTAGE_CONTROL_BY_SVID2;
        }
}
```

Y `122` decodifico `ulPlatformCaps = 0x068000`: **el bit 0 (`ATOM_TONGA_PP_PLATFORM_CAP_VDDGFX_CONTROL`)
no esta activo.** Luego `PHM_PlatformCaps_ControlVDDGFX` **no** se fija, `vdd_gfx_control` se
queda en `SMU7_VOLTAGE_CONTROL_NONE` (0), y **la condicion de `:2216`, `:2300` y `:2319` es
falsa**.

**Tres hechos independientes, del mismo fichero, que se explican entre si:**

| # | hecho | donde |
|---:|---|---|
| 1 | la tabla CAC de VDDGFX es basura (`0xFF02`..`0xFF08`) | VBIOS `0x9CD3` |
| 2 | el cap `VDDGFX_CONTROL` esta apagado | VBIOS `0x9C0A + 19` |
| 3 | sin ese cap, `vdd_gfx_control != SVID2`, y la tabla no se lee | `smu7_hwmgr.c:1883` |

**El VBIOS de esta placa no activa VDDGFX, y por eso el VBIOS de esta placa no necesita que
su tabla de VDDGFX sea valida.**

## Y esa es precisamente la debilidad

**La seguridad aqui es accidental, no vigilada.**

- **Nadie** comprueba que un VBIOS que activa `VDDGFX_CONTROL` traiga una tabla CAC valida.
- **Nadie** comprueba que `ucVddInd` de la tabla SCLK quepa en la tabla CAC.
- **Nadie** comprueba `ucNumEntries <= max_levels`.

Las tres cosas se sostienen aqui por **coincidencia entre dos campos del VBIOS**, no por una
validacion. Y las tres son **cambios legitimos del PPT**: un firmware que quiera activar
control de VDDGFX en esta placa tendria que poner el cap a 1, y si no regenerase la tabla
CAC, el driver leeria 65282 mV y leeria ceros en los dos estados mas rapidos.

Es el mismo patron del borde de `120`, visto desde el otro lado: **el formato y el host
estan emparejados sin holgura y sin validacion, y la seguridad viene de que hoy los dos
lados encajan.**

## Clasificacion

- `MAX_LEVELS_AND_UCNUMENTRIES_ARE_NEVER_COMPARED = PROVEN`:
  `process_pptables_v1_0.c:168` reserva `max_levels`, `:172` fija `count = ucNumEntries`,
  `:174` itera hasta `ucNumEntries`, y el unico assert (`:165`) es `!= 0`.
- `MAX_LEVELS_IS_HARDCODED_16_AT_BOTH_CALL_SITES = PROVEN`: `:283` y `:292`.
- `UCNUMENTRIES_IS_UCHAR_SO_UP_TO_255 = PROVEN`: hasta 255 contra una reserva de 16.
- `A_17_ENTRY_VBIOS_WOULD_OVERFLOW = PROVEN_DERIVED`: `NOT_EXECUTED`, hace falta otro VBIOS.
- `THIS_BOARD_VDDGFX_CAC_TABLE_IS_GARBAGE = PROVEN`: `0xFF02`..`0xFF08` en `0x9CD3+2`,
  `ucRevId = 0`. **No son voltajes.**
- `RECORD_STRIDE_OF_8_IS_CONFIRMED = PROVEN_DERIVED`: 8 entradas desde `0x9CD5` terminan en
  `0x9D15`, que es la tabla SCLK. **El dato es malo, no la lectura.**
- `THIS_BOARD_VDDC_CAC_TABLE_IS_VALID = PROVEN`: 700 a 1100 mV, 10 entradas, margen 6. Los
  tres campos CAC a cero: **esta placa no lleva datos de corriente en el PPT.**
- `THIS_BOARD_SCLK_VDDIND_MAX_IS_9_BUT_TABLE_HAS_8 = PROVEN`: `ucVddInd` = 0,2,2,5,6,7,8,9.
  Los dos estados mas rapidos indexan fuera.
- `OUT_OF_RANGE_READ_RETURNS_ZERO_NOT_HEAP_STAIN = PROVEN_DERIVED`: la reserva es de 16 y
  `kzalloc` la pone a cero, asi que `entries[8].us_vdd` y `entries[9].us_vdd` valen 0.
  **No es corrupcion de memoria: es voltaje cero en los dos estados mas rapidos.**
- `VDDGFX_CONTROL_IS_OFF_ON_THIS_BOARD = PROVEN_DERIVED`: bit 0 ausente de `0x068000` (`122`).
- `VBIOS_TABLE_IS_NEVER_READ_ON_THIS_BOARD = PROVEN_DERIVED`: sin el cap, `vdd_gfx_control`
  queda en `NONE` (`:1883-1889`), y `:2216`, `:2300` y `:2319` son falsas. **Los tres hechos
  se explican entre si.**
- `SAFETY_HERE_IS_ACCIDENTAL = PROVEN_DERIVED`: ninguna de las tres validaciones existe. La
  seguridad viene de que hoy los dos lados del VBIOS encajan.

## Lo que esto obliga a hacer en un driver propio

1. **Comparar la reserva con la cuenta, siempre, aunque esten a cuatro lineas.**
   `if (ucNumEntries > max_levels) return -EINVAL;` es una linea y elimina una familia
   entera de fallos. **Un parametro de capacidad que no se comprueba es un parametro
   decorativo.**
2. **Validar los datos, no solo el rango.** `0xFF02` esta dentro del rango de un `USHORT`, asi
   que **ningun check de rango lo detecta**. Mi driver tiene que validar que un voltaje este
   en un rango **plausible** (por ejemplo 500-1200 mV para esta familia), no solo que quepa
   en el tipo. **Es la diferencia entre "parseado" y "validado".**
3. **Comprobar que un indice de una tabla cabe en la otra.** `ucVddInd` viene de una tabla y
   se usa para indexar otra, y **nadie mira que quepa**. Es la comprobacion de una linea mas
   con un mensaje claro.
4. **Y la regla general, que es la de todo este bloque desde `120`:** *la seguridad no puede
   depender de que hoy los dos lados encajen.* Las tres validaciones que faltan aqui
   estan todas en el hueco entre **"el VBIOS declara"** y **"el driver lo usa"**. Ese hueco es
   el sitio donde tiene que estar el trabajo, y **no hay ninguna linea de codigo ahi**.