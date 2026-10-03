# 217  Polaris12 lee la direccion de la tabla de registros MC y nunca la usa, y Tonga ni Iceland tampoco

WORK_CLASS=READ_ONLY · WRITE_EXECUTION=NONE · MODIFICATIONS 0

## El hallazgo, en una frase

`polaris10_smumgr.c:2528` lee `mc_reg_table_start` de la cabecera del firmware y lo guarda
en un campo compartido, y **ninguna linea de la ruta de Polaris12 lo vuelve a leer**. Y la
tabla que ese campo apuntaria, `smu_data->mc_reg_table`, **tambien se rellena y nunca se
lee**. Dos cadenas muertas, del mismo subsistema.

## Las tres verificaciones, independientes

### 1. Busqueda por nombre exacto en todo el arbol

```
smumgr/ci_smumgr.h:64          campo declarado
smumgr/smu7_smumgr.h:46        campo declarado
smumgr/polaris10_smumgr.c:2528 SOLO ASIGNACION
smumgr/fiji_smumgr.c:2482      SOLO ASIGNACION
smumgr/vegam_smumgr.c:261      SOLO ASIGNACION
smumgr/tonga_smumgr.c:2173     uso (direccion de copia)
smumgr/tonga_smumgr.c:2200     uso (copia)
smumgr/tonga_smumgr.c:2795     asignacion
smumgr/iceland_smumgr.c:1794   uso
smumgr/iceland_smumgr.c:1816   uso
smumgr/iceland_smumgr.c:2317   asignacion
smumgr/ci_smumgr.c:1836        uso
smumgr/ci_smumgr.c:1858        uso
smumgr/ci_smumgr.c:2416       asignacion
```

El recuento por fichero separa los dos grupos sin ambiguedad:

| familia | SMU | sitios de `mc_reg_table_start` | sube la tabla |
|---|---|---:|---|
| Iceland | 7.1 | 3 | si |
| Tonga | 7.2 | 3 | si |
| CI | 7.3 | 3 | si |
| **Fiji** | 7.3 | **1** | **no** |
| **Polaris12** | 7.4 | **1** | **no** |
| **VegaM** | 7.5 | **1** | **no** |

**Y esto no es generacional**, que es lo que habria sido la explicacion facil: Fiji es 7.3
y CI es 7.3, y estan en lados opuestos. La frontera no es la version de la SMU.

### 2. El campo, no solo la direccion

Buscando `smu_data->mc_reg_table` (sin `_start`), Polaris10 tiene **una** aparicion:

```
polaris10_smumgr.c:2571    pp_atomctrl_mc_reg_table *mc_reg_table = &smu_data->mc_reg_table;
```

Y esa linea es la **escritura** del puntero, no una lectura del contenido. Las dos lineas
siguientes la rellenan. En Tonga hay 8 lecturas del campo, en Iceland 8, en CI 8.

Ademas el **tipo del campo delata el motivo**:

| fichero | tipo del campo |
|---|---|
| `tonga_smumgr.h:71` | `struct tonga_mc_reg_table` |
| `iceland_smumgr.h:67` | `struct iceland_mc_reg_table` |
| `ci_smumgr.h:72` | `struct ci_mc_reg_table` |
| **`polaris10_smumgr.h:63`** | **`pp_atomctrl_mc_reg_table`** |

Las tres primeras familias tienen un struct **intermedio, de familia**, y el flujo es:
VBIOS -> struct de familia -> **conversion** -> formato SMC -> **copia** a la SRAM.
La cuarta escribe **directamente el struct crudo del VBIOS** en el campo, y no hay
conversion ni copia. El eslabon que falta es justamente el que las otras tres tienen.

### 3. La herramienta propia, que lista los 13 destinos

`smc_copy_scope` sobre `polaris10_smumgr.c` da **13 escrituras** a la SRAM del SMC, y sus
13 destinos son: `vr_config_address`, `graphics_level_address` (x3), `pm_fuse_table_offset`,
`array` (x2), `arb_table_start`, `tmp` (x2), `dpm_table_start + SystemFlags`,
`fan_table_start`, `dpm_table_start + LowSclkInterruptThreshold`.

**`mc_reg_table_start` no aparece.** Es la misma conclusion que por grep, y sale por una
herramienta distinta.

## Donde se invoca, y por que el trabajo se hace igualmente

El punto de llamada es generico, no de familia:

```c
/* smu7_hwmgr.c:1572-1583 */
tmp_result = smu7_enable_voltage_control(hwmgr);
PP_ASSERT_WITH_CODE(tmp_result == 0, "Failed to enable voltage control!", result = tmp_result);

tmp_result = smu7_construct_voltage_tables(hwmgr);
PP_ASSERT_WITH_CODE((0 == tmp_result), "Failed to construct voltage tables!", result = tmp_result);

smum_initialize_mc_reg_table(hwmgr);        /* <-- :1582, el retorno se pierde */
```

Y mas abajo, en la misma funcion, `:1622`:

```c
tmp_result = smum_init_smc_table(hwmgr);
```

Tres llamadas en la misma funcion. **Las otras dos capturan el retorno y lo envuelven en
`PP_ASSERT_WITH_CODE`. La tercera lo descarta.** Es el mismo patron que `099`
(`smu7_setup_dpm_tables_v1` en `:1068`), pero aqui en codigo compartido por todas las
familias SMU7, no en el fichero de Polaris12.

Que se ejecute en mi ASIC es cierto: `chip_id = 17` es `CHIP_POLARIS12` y
`polaris10_smumgr.c` es la ruta viva (`hwmgr.c:154-157`), y `.initialize_mc_reg_table =
polaris10_initialize_mc_reg_table` esta cableado en su tabla de funciones.

## Lo que hace ese trabajo, y por que no es una fuga

`polaris10_initialize_mc_reg_table` (`:2568-2577`):

```c
memset(mc_reg_table, 0, sizeof(pp_atomctrl_mc_reg_table));
return atomctrl_initialize_mc_reg_table_v2_2(hwmgr, module_index, mc_reg_table);
```

Y `atomctrl_initialize_mc_reg_table_v2_2` (`ppatomctrl.c:173-212`) **no reserva memoria**:
recibe `table` ya apuntado y lo rellena. Hace tres cosas:

1. `smu_atom_get_data_table(..., VRAM_Info, ...)` — busca la tabla VRAM_Info del VBIOS.
2. `atomctrl_set_mc_reg_address_table(reg_block, table)` — tabla de direcciones.
3. `atomctrl_retrieve_ac_timing(module_index, reg_block, table)` — tiempos AC.

**No hay fuga**: el destino es `smu_data->mc_reg_table`, que vive en el struct del
smumgr. Lo que hay es **trabajo de arranque hecho y descartado**: una busqueda en el
VBIOS, una conversion de indices y una extraccion de tiempos AC, en cada arranque, cuyo
resultado no consume nadie.

## Y ahora la parte que hay que degradar, que es lo importante

**En Polaris12 el retorno descartado no tiene consecuencia en la SMC.** No porque estea
bien, sino porque la tabla **nunca se sube**: no hay nada a lo que el error pueda afectar.
Asi que el fallo "se inicializa la tabla MC con un error y se sube a medias" que el patron
de `099` sugiere **no ocurre en mi placa**.

Y en Tonga, Iceland y CI **si** ocurriria: si `atomctrl_initialize_mc_reg_table_v2_2`
falla a mitad, `smu_data->mc_reg_table` queda a medias, y
`tonga_populate_initial_mc_reg_table` copia `sizeof(SMU72_Discrete_MCRegisters)` de eso a
`mc_reg_table_start` sin comprobar nada. Eso es un defecto real, pero **no es de mi ASIC**:
`RUNTIME_MISSING`, y sin placa no se puede observar.

Aqui esta el valor del hallazgo, y es una inversion:

> **El mismo defecto es inocuo en mi chip y dañino en otro.** En Polaris12 es trabajo
> desperdiciado; en Tonga es una subida de tabla a medias. Un analisis estatico limitado a
> mi ASIC puntuaria esto como inocuo, y lo puntuaria bien: **es inocuo ahi.**

Eso no lo hace un error. Es la clase de cosa que hay que tener en cuenta al escribir un
driver propio: **"desperdicio" y "daño" son categorias distintas**, y mi placa es
precisamente el caso en que es desperdicio. Un driver propio no tiene que evitar el daño
aqui; tiene que evitar **el trabajo que no se usa**, porque el trabajo de arranque tiene
presupuesto.

## Lo que NO se puede determinar

- **Si el firmware rellena la tabla de registros MC por su cuenta.** La cabecera anuncia
  una direccion para ella; puede que el firmware la cargue desde su propia copia en ROM y
  que no necesite al host. **Es `NOT_IN_CORPUS`**: el firmware no esta en el arbol, y
  ninguna afirmacion sobre esto es mia sin el binario.
- **Que el firmware lea ese campo**. `SEMANTIC_MISSING`, como en `210`.

Por eso el hallazgo **no dice** "Polaris12 no inicializa la tabla de registros MC, y eso es
un fallo". Dice: **el host lee una direccion, rellena una tabla, y no hace nada con
ninguna de las dos cosas**, y el trabajo se hace en cada arranque.

## Dos cosas del propio proceso, que registro porque una casi me produjo un error

**Fallé un nombre de struct.** Pedi `SMU74_Discreet_PmFuses` y el real es
`SMU74_Discrete_PmFuses`. La herramienta **aviso** en vez de devolver cero en silencio:

```
aviso: gccverify no devolvio offsets de struct SMU74_Discreet_PmFuses;
       las escrituras con ese offsetof quedaran NO_RESUELTO
```

Eso es exactamente lo que exige la regla de que **un nombre mal buscado produce un `0` que
no es ausencia**. Si la herramienta no hubiera avisado, yo habria leido "0 offsets" como
"la struct no existe" y habria publicado una afirmacion falsa. **El aviso es lo que salva
la afirmacion.**

**Y una limitacion real de la herramienta** (`TOOL_PARTIAL`):
`SMU74_Discrete_MCArbDramTimingTable` no devuelve offsets porque **su unico miembro es un
array de dos dimensiones**:

```c
struct SMU74_Discrete_MCArbDramTimingTable {
        SMU74_Discrete_MCArbDramTimingTableEntry entries[SMU__NUM_SCLK_DPM_STATE][SMU__NUM_MCLK_DPM_LEVELS];
};
```

`gccverify` recorre campos escalares y no entra en arrays. El nombre es correcto y la
struct existe; lo que falta es soporte de arrays, no informacion. **Distinguir "no existe"
de "no lo se leer" es precisamente el trabajo**, y aqui la herramienta no puede.

De paso, ese limite dio una **comprobacion independiente de `096`**: la aritmetica del
encabezado da `8 x 4 x 12 = 384` bytes, y coincide con los 384 medidos con gcc. La
invasion de 36 B sobre la tabla de arbitraje queda confirmada por una via que no pasa por
`offsetof`.

## Clasificacion

- `MC_REG_TABLE_START_IS_DEAD_ON_POLARIS12 = PROVEN`: busqueda por nombre exacto en todo
  el arbol; una sola aparicion en `polaris10_smumgr.c` (`:2528`, asignacion) y ninguna
  lectura. Confirmado ademas por `smc_copy_scope` (13 destinos, ninguno es este).
- `MC_REG_TABLE_FIELD_IS_WRITE_ONLY_ON_POLARIS12 = PROVEN`: una sola aparicion
  (`:2571`), que es la escritura del puntero.
- `MC_REG_TABLE_SPLIT_IS_3_TO_1_NOT_GENERATIONAL = PROVEN`: Iceland/Tonga/CI suben la
  tabla, Fiji/Polaris12/VegaM no; **Fiji y CI son las dos 7.3**, asi que la version de la
  SMU no explica el corte.
- `MC_REG_TABLE_RAW_VBIOS_TYPE_IS_THE_TELL = PROVEN`: `polaris10_smumgr.h:63` declara
  `pp_atomctrl_mc_reg_table`, no un struct de familia con paso de conversion.
- `MC_REG_TABLE_INIT_RETURN_IS_DISCARDED = PROVEN`: `smu7_hwmgr.c:1582`, mientras `:1572`
  y `:1577` en la misma funcion lo capturan y lo envuelven en `PP_ASSERT_WITH_CODE`.
- `MC_REG_TABLE_INIT_IS_NOT_A_LEAK = PROVEN`: `atomctrl_initialize_mc_reg_table_v2_2`
  (`ppatomctrl.c:173`) recibe el puntero y no reserva.
- `MC_REG_TABLE_DISCARDED_RETURN_HARMLESS_ON_POLARIS12 = PROVEN_DERIVED`: no hay subida,
  luego no hay SMC a la que afectanr. **Degradacion deliberada** de la consecuencia.
- `MC_REG_TABLE_DISCARDED_RETURN_HARMFUL_ON_TONGA = PROVEN_DERIVED` pero
  `NOT_MY_ASIC`: `tonga_populate_initial_mc_reg_table` (`:2200`) copia el struct a medias
  si la inicializacion fallo.
- `MCREG_READ_DOES_NOT_ACCUMULATE_ERROR_IS_SHARED_NOT_A_DEFECT = PROVEN`: `:2522-2528` es
  identico a `tonga_smumgr.c:2789-2795`, con guarda `if (!result)` en ambos. **Decision de
  diseno comun, no defecto de Polaris12.**
- `SMC_COPY_SCOPE_CANNOT_RESOLVE_ARRAY_MEMBERS = TOOL_PARTIAL`:
  `SMU74_Discrete_MCArbDramTimingTable` tiene un solo miembro y es un array 2D.
- `ARB_TABLE_SIZE_CROSS_CHECKED_BY_ARITHMETIC = PROVEN_DERIVED`: `8 x 4 x 12 = 384` en el
  encabezado, coincide con los 384 de gcc. Segunda via para `096`.

## Lo que esto obliga a hacer en un driver propio

Tres reglas, y las tres salen de lo mismo:

1. **Un dato que se lee y no se usa, se borra.** Si la cabecera del firmware anuncia una
   direccion y el driver no va a escribir ahi, **no la lea**. Leerla cuesta una lectura de
   la SRAM y un campo en un struct compartido, y deja en el codigo la **apariencia** de un
   contrato que no existe.
2. **El tipo del campo dice si hay pipeline.** Que el campo sea el **struct crudo de
   origen** en vez de uno de destino es, en este caso, la unica señal de que falta el paso
   de conversion. En un driver propio: un campo de "datos interpretados" y otro de "datos
   en bruto", nunca el mismo.
3. **Un retorno ignorado hay que auditarlo por el otro lado de la llamada**, no por el
   del que llama. Aqui el patron de `099` se cumple en el codigo compartido, y **la
   consecuencia depende de si el dato se consume**. Por eso `215` y `099` juntos no bastan:
   hace falta la pregunta "¿quien lee esto?" antes de afirmar el fallo.