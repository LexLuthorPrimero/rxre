# 098 · GraphicsBootLevel tiene dos escritores y el segundo pisa al primero con otro espacio de indices

WORK_CLASS=READ_ONLY · WRITE_EXECUTION=NONE · MODIFICATIONS 0

## Por que este documento corrige a 094

`094` afirmo que el `GraphicsBootLevel` que sube a la SRAM del SMC es el que produce
`phm_find_boot_level` sobre la tabla DPM deduplicada. **Es falso.** El valor se descarta.

No por un error de lectura, sino porque hay un segundo escritor del mismo campo que se
ejecuta despues y lo sobrescribe. Y lo que escribe ese segundo no es "el mismo valor
mejor calculado": es un indice de un **espacio de indices distinto**.

## Los dos escritores, y que escriben en la misma struct

No son dos structs. `polaris10_smumgr.c:1921`:

```c
struct SMU74_Discrete_DpmTable *table = &(smu_data->smc_state_table);
```

Asi que `table->GraphicsBootLevel` (escritor 1) y
`smu_data->smc_state_table.GraphicsBootLevel` (escritor 2) son **el mismo byte de la
misma struct**. Busqueda por nombre exacto en todo `pm/powerplay/`: 6 escrituras en
`polaris10_smumgr.c`, dos de ellas en el mismo campo.

### Escritor 1: `polaris10_populate_smc_boot_level`, indice de la TABLA DPM

`smu7_hwmgr.c` / `polaris10_smumgr.c:1583-1592`. Toma
`data->vbios_boot_state.sclk_bootup_value` y lo busca en
`data->dpm_table.sclk_table`, que es la tabla **ya deduplicada**:

```c
result = phm_find_boot_level(&(data->dpm_table.sclk_table),
                data->vbios_boot_state.sclk_bootup_value,
                (uint32_t *)&(table->GraphicsBootLevel));
```

Indice en el espacio `[0, sclk_table.count)`.

### Escritor 2: `polaris10_populate_smc_initailial_state`, indice del PPT

`polaris10_smumgr.c:1625-1633`:

```c
count = (uint8_t)(table_info->vdd_dep_on_sclk->count);   /* el del PPT, sin deduplicar */

for (level = 0; level < count; level++) {
        if (table_info->vdd_dep_on_sclk->entries[level].clk >=
                hw_data->vbios_boot_state.sclk_bootup_value) {
                smu_data->smc_state_table.GraphicsBootLevel = level;
                break;
        }
}
```

Indice en el espacio `[0, vdd_dep_on_sclk->count)`, que es el **PPT crudo**, sin pasar
por la deduplicacion.

## El orden, verificado

Dentro de `polaris10_init_smc_table` (`:1913`):

```c
result = polaris10_populate_smc_boot_level(hwmgr, table);          /* 1988 */
PP_ASSERT_WITH_CODE(0 == result, "Failed to initialize Boot Level!", return result);

result = polaris10_populate_smc_initailial_state(hwmgr);          /* 1992 */
PP_ASSERT_WITH_CODE(0 == result, "Failed to initialize Boot State!", return result);
```

**El escritor 2 va cuatro lineas despues del escritor 1 y no mira lo que este escribio.**
Lo que queda en `smc_state_table.GraphicsBootLevel` es el valor del escritor 2.

Y no solo eso: el escritor 2 **no tiene rama de fallo**. Si ninguna entrada del PPT
supera el reloj de arranque, el bucle termina sin hacer nada y el campo conserva lo que
dejara el escritor 1. O sea que el valor final es **una de dos cosas sin indicacion de
cual**:

- el indice del PPT, si alguna frecuencia del PPT es mayor o igual al reloj de arranque;
- el resultado de `phm_find_boot_level`, si ninguna lo es.

Y ambos son silenciosos.

## Por que los dos espacios de indices no coinciden

La deduplicacion, `smu7_hwmgr.c:901-912` (verificada en mi corpus, no en el del agente):

```c
data->dpm_table.sclk_table.count = 0;
for (i = 0; i < dep_sclk_table->count; i++) {
        if (i == 0 || data->dpm_table.sclk_table.dpm_levels[data->dpm_table.sclk_table.count - 1].value !=
                        dep_sclk_table->entries[i].clk) {
                data->dpm_table.sclk_table.dpm_levels[data->dpm_table.sclk_table.count].value =
                        dep_sclk_table->entries[i].clk;
                data->dpm_table.sclk_table.dpm_levels[data->dpm_table.sclk_table.count].enabled =
                        i == 0;
                data->dpm_table.sclk_table.count++;
        }
}
```

El criterio es `dpm_levels[count-1].value != entries[i].clk`: **solo compara contra el
ultimo nivel insertado**, no contra la tabla entera. Consecuencias, y las dos importan:

- **Duplicados consecutivos** (`A, A, A`): eliminados.
- **Duplicados no consecutivos** (`A, B, A`): **sobreviven**. La tabla DPM contiene el
  mismo valor de reloj en dos niveles distintos, y su `count` es **menor** que el
  `count` del PPT.

Por construccion, siempre que haya **cualquier** duplicado en el PPT:

```
sclk_table.count  <  vdd_dep_on_sclk->count
```

Los dos espacios de indices tienen distinta longitud. El escritor 2 escribe un indice
que en el espacio del escritor 1 apunta a otro nivel, o directamente no existe.

Consecuencia concreta. Una version anterior de esta seccion traia un ejemplo mal
construido (`A, B, A` con boot `A`), y **la simulacion lo refuto**: en `A, B, A` el
segundo `A` **si** se inserta, porque se compara contra `dpm_levels[count-1]` que es `B`
y difiere, asi que `count` queda en 4 y el indice 2 vuelve a valer `A`. Eso no es un
desplazamiento de indice: es un **nivel duplicado**, que es el otro defecto.

Los casos que **si** producen un indice desplazado los encontre por busqueda sobre el
codigo literal de `:901-912` y `:1627-1633`, y son estos:

| PPT | boot | escritor 2 escribe | lo que hay en ese indice de la tabla DPM | |
|---|---|---:|---|---|
| `[300, 300, 500, 900]` | 500 | **2** | **900** | nivel equivocado |
| `[500, 300, 900, 1200]` | 300 | **0** | **500** | nivel equivocado |
| `[300, 500, 500, 900]` | 900 | **3** | **no existe** | fuera de rango |
| `[300, 300, 500, 900]` | 900 | **3** | **no existe** | fuera de rango |

El primero es el mas claro, y **no requiere un PPT desordenado**: `[300, 300, 500, 900]`
es una tabla perfectamente ordenada y con un unico duplicado, que es la forma mas normal
de duplicado posible. La deduplicacion la colapsa a `[300, 500, 900]` con `count` = 3.
El escritor 2 recorre el PPT crudo, ve que `500 >= 500` en el indice 2, y escribe **2**.
En la tabla DPM el indice 2 es **900**.

**El firmware recibe el indice del nivel de 900 MHz como nivel de arranque, cuando el
reloj de arranque es de 500.** No es un valor raro: es un nivel mas rapido. Que eso
pida mas reloj del que deberia, o active un nivel que el hardware no soporta a ese
voltaje, es `SEMANTIC_MISSING`. El indice equivocado, dado un PPT con un duplicado, es
`PROVEN`.

## Y esto se junta con el "gana el ultimo" de `phm_find_boot_level`

`094` ya habia establecido que `phm_find_boot_level` (smu_helper.c:447-452) **no tiene
`break`**: recorre todo y, si encuentra dos coincidencias, **gana el indice mas alto**.

Con duplicados no consecutivos en la tabla DPM, eso **si se manifiesta**. Los dos
defectos apuntan al mismo fenomeno: la deduplicacion no garantiza unicidad.

Y hay un tercero del mismo tipo: `phm_find_boot_level` escribe con `(uint32_t *)` sobre
un campo de **1 byte**. Ese desbordamiento lo analizo `094`; sigue siendo real y sigue
siendo la primera escritura. Pero al ser pisada por el escritor 2, los tres bytes que
sobrescribia (`GraphicsVoltageChangeEnable`, `GraphicsThermThrottleEnable`,
`GraphicsInterval`) **no quedan como los puse**: `:2014-2016` los pone a 1 despues, asi
que siguen ocultando lo que decia `094`. Lo que cambia es que el campo
`GraphicsBootLevel` en si no llega a la SRAM con el valor del escritor 1.

## El patron que esto revela, que es lo importante

**Un campo con dos escritores en el mismo pipeline, donde el segundo no comprueba el
resultado del primero, y donde los dos indices pertenecen a espacios que la
deduplicacion hace divergentes.**

No es un bug de un valor: es una ausencia de propietario del campo. En un driver propio,
un campo de la tabla que se escribe desde dos sitios con dos espacios de indices distintos
tiene que ser un error de diseño, no una cuestion de orden de llamadas. La unica defensa
es que los dos espacios sean identicos por construccion, y aqui no lo son.

## Lo que NO dice

No dice que esta placa tenga duplicados no consecutivos en su PPT. Eso requiere el VBIOS
de la placa: `RUNTIME_MISSING`. Con el PPT ordenado de forma creciente, que es lo normal
en una tabla de dependencia, los repetidos caen juntos, la deduplicacion los elimina y
`count` coincide con el del PPT: **el desajuste no se manifiesta**.

Por eso el valor final de `GraphicsBootLevel` es, de momento:
`RUNTIME_MISSING` si el PPT de esta placa esta ordenado; `PROVEN` el defecto, que no hay
ninguna comprobacion que lo evite.

No dice que el firmware use `GraphicsBootLevel` como indice de la tabla DPM. El nombre
del campo lo sugiere y el contrato lo requiere, pero lo que haga el firmware es
`NOT_IN_CORPUS`.

No dice que el escritor 2 sea un error de upstream que valga la pena reportar. Es un
patron de codigo, no un fallo demostrado.

## Clasificacion

- `SMC_BOOT_LEVEL_TWO_WRITERS = PROVEN`: `polaris10_smumgr.c:1583/1589` y `:1630`, mismo
  byte (`:1921`).
- `SMC_BOOT_LEVEL_SECOND_OVERWRITES = PROVEN`: llamadas en `:1988` y `:1992`, en ese
  orden, sin comprobar el valor anterior.
- `SMC_BOOT_LEVEL_INDEX_SPACES_DIFFER = PROVEN`: escritor 1 indexa
  `sclk_table` (deduplicado); escritor 2 indexa `vdd_dep_on_sclk` (crudo).
- `SMC_DEDUP_ONLY_ADJACENT = PROVEN`: `smu7_hwmgr.c:902-903` compara contra
  `dpm_levels[count-1]` unicamente. Verificado en mi corpus.
- `SMC_DEDUP_KEEPS_NONADJACENT = PROVEN`: `A, B, A` deja `count` con `A` en dos
  niveles.
- `SMC_DEDUP_MAKES_COUNT_SMALLER = PROVEN_DERIVED`: con cualquier duplicado,
  `sclk_table.count < vdd_dep_on_sclk->count`.
- `SMC_BOOT_LEVEL_SECOND_NO_FAIL_BRANCH = PROVEN`: si nada supera el arranque, el campo
  conserva el del escritor 1, sin indicar cual de los dos es.
- `SMC_FIND_BOOT_LEVEL_NO_BREAK_INTERACTS = PROVEN` el mecanismo,
  `RUNTIME_MISSING` si se manifiesta (requiere duplicados no consecutivos).
- `BOOT_LEVEL_094_VALUE_IS_DISCARDED = PROVEN`: lo que `094` analiza del valor final no
  llega a la SRAM.

## Correccion de `094`, en una linea

De `094` sobrevive el **desbordamiento de 4 bytes** y el hecho de que la funcion no
puede fallar. **No** sobrevive la afirmacion de que ese es el valor final de
`GraphicsBootLevel`. Este documento lo sustituye.
