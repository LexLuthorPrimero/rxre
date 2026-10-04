# 107 · El parche de UVD escribe el byte 3 del DWORD 394 (1579), no Smio[5]: esa localizacion queda REFUTADA

> **H1 CORREGIDO EL 2026-10-04.** El titulo anterior decia «El parche de UVD escribe sobre Smio[5], no sobre BootVddc: correccion de 103». Ese
> enunciado ya no describe el estado del arbol. El veredicto vigente esta en este
> mismo fichero:
> - `:15` — la localizacion Smio[5] se refuta: «La localizacion `Smio[5]` se obtiene restando 108 a»
> - `:25` — el byte real: «es el **3** de esa palabra, o sea **1579**»
>
> Este parche toca **solo el H1** y esta marca. El cuerpo no se reescribe: la
> correccion del titulo tiene que quedar rastreable, o el titulo parece haber
> sido asi siempre.

WORK_CLASS=READ_ONLY · WRITE_EXECUTION=NONE · MODIFICATIONS 0

> **CORREGIDO POR `218` y `219`.** La localizacion `Smio[5]` se obtiene restando 108 a
> 1576 (`1468`), y ese hueco queda **REFUTADO**: `dpm_table_start` es la base literal.
> Quedan **REFUTED** `SMC_RAW_WRITE_HITS_SMIO5` y
> `SMC_RAW_WRITE_WRITES_INDEX_AS_BOOT_LEVEL`.
>
> **SE SOSTIENE**: `SMIO_IS_AN_INDEX_NOT_A_VOLTAGE` (independiente) y
> `SMIO5_IS_NEVER_WRITTEN_BY_ANY_PRODUCER`, aunque queda sin consecuencia: el parche ya no
> cae ahi.
>
> **Precision sobre el byte**: el ancla del parche de UVD es 1576, pero el byte que escribe
> es el **3** de esa palabra, o sea **1579** (`219`). Y el parche de VCE escribe el byte 1
> (1577), que si es donde esta `VceBootLevel`. Las dos mascaras son disjuntas: **no
> colisionan**.

## Este documento corrige a 103, y la correccion es de fondo

`210` afirmo que el parche de UVD reescribe **`BootVddc`**, el voltaje de arranque de la
memoria. **El campo es otro: es `Smio[5]`**, una entrada del array de indices SMIO.

El mecanismo de `210` sigue siendo correcto (el desfase de 108 bytes, la direccion mal
calculada, el camino vivo). Lo que estaba mal era **a que campo apunta la direccion mal
calculada**, y eso cambia el analisis por completo.

Es la **cuarta vez** que el mismo error produce un veredicto falso, y la cuarta con la
misma causa: sumar donde habia que restar.

## Las dos operaciones, con las direcciones ya alineadas

`polaris10_update_uvd_smc_table` (`:2292-2301`) y `..._vce_smc_table` (`:2328-2337`):

```c
/* UVD */
mm_boot_level_offset = dpm_table_start + offsetof(SMU74_Discrete_DpmTable, UvdBootLevel);
mm_boot_level_offset /= 4;
mm_boot_level_offset *= 4;
mm_boot_level_value = cgs_read_ind_register(..., mm_boot_level_offset);
mm_boot_level_value &= 0x00FFFFFF;
mm_boot_level_value |= smu_data->smc_state_table.UvdBootLevel << 24;
cgs_write_ind_register(..., mm_boot_level_offset, mm_boot_level_value);

/* VCE */
mm_boot_level_offset = dpm_table_start + offsetof(SMU74_Discrete_DpmTable, VceBootLevel);
mm_boot_level_offset /= 4;
mm_boot_level_offset *= 4;
mm_boot_level_value &= 0xFF00FFFF;
mm_boot_level_value |= smu_data->smc_state_table.VceBootLevel << 16;
```

Las direcciones, ya alineadas (`1576 % 4 == 0` y `1577 - 1577 % 4 == 1576`):

| parche | `offsetof` | alineado | posicion en la TABLA |
|---|---:|---:|---:|
| UVD | 1576 | 1576 | **1576** |
| VCE | 1577 | **1576** | **1576** |

Las dos escriben en **el mismo DWORD**, la posicion 1576 de la tabla.

## Y ahi, que hay

La copia inicial coloco la posicion 1576 de la tabla en el offset `1576 - 108 = 1468` de
la struct. Y en el offset 1468 esta:

```
Smio   offset 1448   128 B   = 32 entradas de 4 B
       byte 20  = celda 5, byte interno 0
```

O sea: **las dos mascaras escriben sobre `Smio[5]`, byte 0 de la celda.**

Con gcc, para no depender de mi parser:

```
sizeof(SMU74_Discrete_DpmTable) = 1884
offsetof(BootVddc)              = 1684
offsetof(BootVddci)             = 1686
offsetof(VceBootLevel)          = 1577
```

Y el campo que el parche **creia** modificar, `UvdBootLevel`, esta en el offset 1576, es
decir en la posicion `1576 + 108 = 1684` de la tabla. **No es donde escribe.**

## Que es `Smio`, y por que importa

`Smio[]` es el array de **indices** que dice al firmware que bit de `SmioTable1`,
`SmioTable2` y `SmioMask` usar para cada nivel de voltaje. Se construye con `|=` desde las
tablas de voltaje del host:

`polaris10_smumgr.c:674-683` (para VCE/VDDCI es el mismo patron, `:707` y `:732`):

```c
for (level = 0; level < count; level++) {
        table->SmioTable2.Pattern[level].Voltage = ...;
        /* Index into DpmTable.Smio. Drive bits from Smio entry to get this voltage level.*/
        table->SmioTable2.Pattern[level].Smio = (uint8_t) level;
        table->Smio[level] |= data->mvdd_voltage_table.entries[level].smio_low;
}
```

El comentario del propio driver lo dice: **`Smio` es el indice, no el voltaje.** Escriben
ahi los bits de salida del regulador, y el firmware los usa para elegir el nivel.

**Un nivel de arranque de UVD o de VCE no es un indice de SMIO.** Es un numero de la tabla
de niveles,tipicamente de 0 a 3. Puesto en `Smio[5]` byte 0, el firmware lo leeria como el byte
bajo de un indice de voltaje.

## El detalle que ATENUA el dano, y hay que decirlo

`SMU_MAX_SMIO_LEVELS = 4` (`smu74.h:132`). Los bucles que rellenan `Smio[]` recorren
`level < count` con `count <= 4`, o sea **escriben `Smio[0..3]`**.

**`Smio[5]` no lo escribe ningun productor.** El array se creo con `kzalloc` (`:339`), asi
que `Smio[4..31]` estan a cero, y `Smio[5]` sigue a cero.

O sea: lo que el parche pisa es un cero. El valor final de `Smio[5]` byte 0 es el nivel de
arranque, en vez de cero.

Eso **no es necesariamente inofensivo**: cero es un indice valido ("usa el nivel 0 de la
tabla de voltajes") y un nivel de arranque tambien es un numero pequeno. Los dos son
plausibles para el firmware, y por eso el resultado es **indistinguible sin conocer la
semantica**, que es `NOT_IN_CORPUS`.

La conclusion honesta: **el parche escribe en un campo que no es el suyo, con un valor que
no es del tipo de ese campo, sobre una celda que antes valia cero.** Eso es `PROVEN`. Lo
que el firmware haga con `Smio[5]` vale 2 o 3, es `SEMANTIC_MISSING`.

## Y los dos parches no se pisan entre si, contra lo que escribi en 103

`210` decia que VCE "pisa lo mismo que UVD" porque escribian en el byte medio en vez del
alto. **Es falso**, y lo verifique con las mascaras:

| parche | mascara | conserva | escribe |
|---|---|---|---|
| UVD | `&= 0x00FFFFFF` | bytes 0, 1, 2 | byte 3 |
| VCE | `&= 0xFF00FFFF` | bytes 0, 2, 3 | byte 2 |

Cada mascara **preserva el byte que la otra escribe**. Escriben en bytes distintos del mismo
DWORD y no se destruyen.

Lo que si es cierto: los dos terminan en el mismo DWORD, asi que si se ejecutan ambos en
la misma transicion de ungate (que es lo que ocurre, `amd_powerplay.c:1230` UVD y `:1233`
VCE), el resultado es un DWORD con dos celdas de `Smio` modificadas por dos valores de
nivel de arranque distintos.

## Por que `210` se equivoco, y la regla

Mi calculo fue: `offsetof(UvdBootLevel) + 108 = 1684 = offsetof(BootVddc)`, y de ahi
"el parche escribe en `BootVddc`".

Ese es el **mismo error** que corregi a mano en `211`. La copia inicial coloca el campo del
host en la posicion `offsetof + 108` **de la tabla**, lo que significa que la posicion
`offsetof` **de la tabla** contiene el campo del host que esta en `offsetof - 108`.

La confusion es entre dos enunciados:

- "el offset `X` de la struct esta en la posicion `X + 108` de la tabla" — **cierto**.
- "la posicion `X` de la tabla contiene el offset `X` de la struct" — **falso**.

Son el mismo numero en dos bases distintas, y por eso el primer calculo salia plausible.

**La regla**: para saber que hay en una posicion de la tabla, hay que mirar el offset
`posicion - 108` de la struct. Nunca `posicion`, y nunca `posicion + 108`.

## Lo que esto deja

`210` queda con el mecanismo y **sin el campo**. `211` y `213` quedan con el analisis de
cobertura de escrituras, que es independiente de esto.

Y aparece una limitacion de `smc_copy_scope` que ahora se ve desde dentro: la herramienta
**no ve ninguna de las dos escrituras**, porque busca `smu7_copy_bytes_to_smc` y estos son
`cgs_read_ind_register` / `cgs_write_ind_register`. En el fichero real hay **16 escrituras
registro a registro** en la ruta de Polaris12, y en las otras familias tambien (Tonga 32,
CI 33, Iceland 24, Fiji 22, VegaM 9).

O sea: **la clase es mas grande de lo que la herramienta cubre**, y el caso mas grave
queda fuera. Eso es una limitacion de alcance declarada, no un hallazgo, y es el
siguiente trabajo natural.

## Clasificacion

- `SMC_RAW_WRITE_HITS_SMIO5 = PROVEN_DERIVED`: posicion 1576 de la tabla = offset 1468 de
  la struct = `Smio` byte 20 = celda 5. **`PROVEN` el mecanismo, `DERIVED` el
  desplazamiento, y contradice a `210`, que decia `BootVddc`.**
- `SMC_RAW_WRITE_HITS_NOT_BOOT_VDDC = PROVEN`: `BootVddc` esta en 1684, y el parche
  escribe en la posicion 1576. `REFUTED` la afirmacion de `210`.
- `SMIO_IS_AN_INDEX_NOT_A_VOLTAGE = PROVEN`: `polaris10_smumgr.c:674-683`, con el
  comentario del propio driver en la linea 678.
- `SMIO5_IS_NEVER_WRITTEN_BY_ANY_PRODUCER = PROVEN_DERIVED`:
  `SMU_MAX_SMIO_LEVELS = 4` (`smu74.h:132`), bucles `level < count <= 4`. El valor previo
  es el cero del `kzalloc` de `:339`.
- `SMC_RAW_WRITE_WRITES_INDEX_AS_BOOT_LEVEL = PROVEN`: un nivel de arranque donde el
  firmware espera un indice de voltaje. Que el firmware lo distinga o no:
  `SEMANTIC_MISSING`.
- `SMC_TWO_RAW_WRITES_DO_NOT_CLOBBER = PROVEN`: `0x00FFFFFF` escribe byte 3 y
  `0xFF00FFFF` escribe byte 2; cada mascara preserva el byte de la otra. **Refuta** lo que
  decia `210`.
- `SMC_TWO_RAW_WRITES_SHARE_A_DWORD = PROVEN_DERIVED`: `1577 / 4 * 4 = 1576`, y UVD ya
  alineaba a 1576.
- `RAW_WRITE_COUNT_IS_LARGE = PROVEN`: 16 en `polaris10_smumgr.c`; y la clase existe en
  las otras familias. **Limitacion de alcance de `smc_copy_scope`, no hallazgo.**

## Lo que esto obliga a hacer en un driver propio

Una sola regla sale de las cuatro ocurrencias del mismo error:

> **Toda direccion que se calcule sumando un `offsetof` a una base tiene que pasar por una
> funcion que este verificada contra el layout en las dos bases.**

Y en concreto, para el caso de los parches registro a registro, que son distintos de las
copias:

1. La funcion de conversion tiene que tener un caso de prueba con **un destino real** (por
   ejemplo `BootVddc` en 1684) que verifique que la direccion calculada coincide con donde
   la copia inicial puso ese campo. Es un discriminante barato y habria cazado esto.
2. Un parche registro a registro **necesita su propia verificacion**: no pasa por la copia,
   asi que el assert de rango de la copia no lo cubre. Lo natural es releer el DWORD
   escrito y comparar con lo que se quiso escribir, una vez, al arrancar.
3. Y `Smio[]` es un indice, no un dato: cualquier escritura ahi tiene que justificarse por
   el contrato del firmware, no por "estoy cerca del campo que quiero".
