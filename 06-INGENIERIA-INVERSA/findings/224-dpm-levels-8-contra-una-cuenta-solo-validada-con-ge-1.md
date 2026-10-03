# 224  `dpm_levels[8]` se llena desde una cuenta que solo se valida con `>= 1`, y este VBIOS la pone justo en 8

WORK_CLASS=READ_ONLY · WRITE_EXECUTION=NONE · MODIFICATIONS 0

> ## PRECISADO POR `230` (antes `129`) — el recorte EXISTE, y dos lineas despues lo borran
>
> Este hallazgo dice que el unico check del `count` es `>= 1`. **Es incompleto: hay un recorte
> real, y no lo vi.**
>
> ```c
> /* smu_helper.c:345-358 */
> int phm_reset_single_dpm_table(void *table, uint32_t count, int max)
> {
>         dpm_table->count = count > max ? max : count;      /* recorte real */
>         ...
> }
> ```
>
> Y `smu7_reset_dpm_tables` (`smu7_hwmgr.c:745-769`) lo invoca para **las seis** tablas DPM
> pasando `MAX_REGULAR_DPM_NUMBER` como `max`.
>
> **Pero `smu7_setup_dpm_tables_v1`, que se llama DESPUES, hace:**
>
> ```c
> /* smu7_hwmgr.c:900 */
> data->dpm_table.sclk_table.count = 0;      /* <-- borra el recorte */
> for (i = 0; i < dep_sclk_table->count; i++) {
>         if (i == 0 || dpm_levels[count - 1].value != dep_sclk_table->entries[i].clk) {
>                 dpm_levels[count].value = ...;
>                 dpm_levels[count].enabled = (i == 0);
>                 data->dpm_table.sclk_table.count++;      /* y el recorte no vuelve */
>         }
> }
> ```
>
> **El recorte acota el valor INICIAL y nunca el INCREMENTO.**
>
> **Y hay un mitigador que este hallazgo no recogio: el filtro de duplicados de `:902`.** Una
> entrada solo se acepta si su reloj **difiere** del anterior, asi que `count` no crece con
> `ucNumEntries` sino con el numero de **relojes DISTINTOS** de la tabla.
>
> - `EL_RECORTE_EXISTE_Y_ACOTA_EL_VALOR_INICIAL = PROVEN`: `smu_helper.c:352`.
> - `PERO_900_Y_916_LO_BORRAN = PROVEN`.
> - `EL_FILTRO_DE_DUPLICADOS_ES_EL_MITIGADOR_REAL = PROVEN_DERIVED`.
> - **Consecuencia: el desbordamiento no necesita 9 entradas, necesita 9 relojes DISTINTOS.**
>   Mi VBIOS tiene 8 distintos (`121`), que es exactamente la capacidad: **margen cero, pero un
>   margen mas estrecho de lo que este hallazgo parecia.**

COMPLETA `223` (el `NOT_DETERMINED` que alli deje) · USA EL VBIOS REAL DE ESTA PLACA

## El hallazgo

En la ruta que **si** se ejecuta en Polaris12 (`smu7_setup_dpm_tables_v1`), el lazo que
llena la tabla de niveles DPM de graficos usa **la cuenta que declara el VBIOS** como
limite, y escribe en un array de tamaño fijo, y **la unica validacion es `count >= 1`**.

```c
/* smu7_hwmgr.c:900-910, dentro de smu7_setup_dpm_tables_v1 (:869) */
PP_ASSERT_WITH_CODE(dep_sclk_table->count >= 1, "SCLK dependency table count is 0.", return -EINVAL);

data->dpm_table.sclk_table.count = 0;
for (i = 0; i < dep_sclk_table->count; i++) {
        if (i == 0 || data->dpm_table.sclk_table.dpm_levels[data->dpm_table.sclk_table.count - 1].value
                        != dep_sclk_table->entries[i].clk) {
                data->dpm_table.sclk_table.dpm_levels[data->dpm_table.sclk_table.count].value =
                        dep_sclk_table->entries[i].clk;
                data->dpm_table.sclk_table.dpm_levels[data->dpm_table.sclk_table.count].enabled =
                        (i == 0) ? 1 : 0;
                data->dpm_table.sclk_table.count++;
        }
}
```

La cota, medida:

```
MAX_REGULAR_DPM_NUMBER = 8                      smu7_hwmgr.h:95
struct smu7_dpm_level { bool enabled; uint32_t value; uint32_t param1; }   smu7_hwmgr.h:88
dpm_levels[MAX_REGULAR_DPM_NUMBER]              smu7_hwmgr.h:100
```

**Y este VBIOS declara 8.** Ni 7, ni 9.

## La medicion, con validacion cruzada

Offsets de `ATOM_Tonga_POWERPLAYTABLE`, medidos con gcc sobre los campos extraidos de
`pptable_v1_0.h`, con `pack(1)` y el miembro `sHeader` incluido:

```
sizeof(ATOM_Tonga_POWERPLAYTABLE)       = 77
usStateArrayOffset                      = 35
usMclkDependencyTableOffset             = 43
usSclkDependencyTableOffset             = 45
usVddcLookupTableOffset                 = 47
usVddgfxLookupTableOffset               = 49
usMMDependencyTableOffset               = 51
usPowerTuneTableOffset                  = 57
```

**Validacion antes de leer**: `usStructureSize = 778` y `ucTableFormatRevision = 7` contra lo
que reporta `atomrom.py`. Y **`sizeof` por gcc = 77 = el `usTableSize` que declara el propio
VBIOS**. Dos metodos independientes.

Y una segunda validacion, que es la mejor de este documento:

```
ATOM_Polaris_SCLK_Dependency_Record  sizeof = 15   (ucVddInd@0 usVddcOffset@1 ulSclk@3 ...)
tabla SCLK en 0x9D15,  ucNumEntries = 8
tabla MCLK en 0x9D8F = 0x9D15 + 0x7A = 0x9D15 + 122 = 0x9D15 + (2 + 8*15)
```

**La tabla MCLK empieza exactamente donde acaban las 8 entradas SCLK de 15 bytes.** Si el
stride estuviera equivocado en un byte, la tabla MCLK no caeria ahi. **El layout esta
verificado por la disposicion del propio ROM.**

Las 8 entradas:

```
  #   ulSclk   vddInd   cksOff   cksDis
  0    21400      0        0        1
  1    55100      2      102        0
  2    73400      2        0        0
  3    98000      5        0        0
  4   100000      6        0        0
  5   102000      7        0        0
  6   104600      8        0        0
  7   107100      9        0        0
```

Y la MCLK declara **3**.

## La cuenta, y por que no hay deduplicacion que salve

El `if` interior deduplica cuando el valor es igual al anterior. **Los 8 valores son
todos distintos**, luego no deduplica nada: el indice de escritura avanza con `i`.

```
i         = 0 .. 7
escritura = dpm_levels[0] .. dpm_levels[7]
count final = 8
```

**`dpm_levels[7]` es el ultimo elemento valido de un array de 8. Margen: cero.**

Es decir: **este VBIOS esta exactamente en el limite, y no lo cruza.** Un VBIOS con 9
entradas escribiria `dpm_levels[8]`, fuera del array, y **ninguna comprobacion lo
detectaria**: el assert pide `count >= 1`, no `count <= MAX_REGULAR_DPM_NUMBER`.

## Y una corroboracion con el dato en caliente

El primer nivel declara `ulSclk = 21400`. La captura viva
(`revkit/capturas/amdgpu_pm_info.txt`) dice:

```
  997 MHz (SCLK)
  214 MHz (PSTATE_SCLK)     <-- coincide con 21400 en unidades de 10 kHz
```

**El nivel mas bajo de la tabla del VBIOS es exactamente el PSTATE_SCLK observado.** No es
una coincidencia de numeros parecidos: es el mismo valor en la misma magnitud.

**Y el maximo** del VBIOS es 107100 (10 kHz) = 1071 MHz, y el SCLK observado en caliente es
997 MHz. **Coherente**: el observado es una frecuencia de trabajo, no el tope del estado.

## El bug que SI existe, y que NO corre en mi placa

En la variante **V0** de la misma funcion (`smu7_setup_dpm_tables_v0`, `:781`), el lazo
mezcla **tres tablas distintas**:

```c
/* smu7_hwmgr.c:833-837 */
for (i = 0; i < allowed_vdd_sclk_table->count; i++) {              /* cuenta SCLK = 8 */
        data->dpm_table.vddc_table.dpm_levels[i].value  = allowed_vdd_mclk_table->entries[i].v;
        data->dpm_table.vddc_table.dpm_levels[i].param1 = std_voltage_table->entries[i].Leakage;
        data->dpm_table.vddc_table.dpm_levels[i].enabled = true;
}
data->dpm_table.vddc_table.count = allowed_vdd_sclk_table->count;
```

**El lazo corre 8 veces (cuenta SCLK) e indexa la tabla MCLK y la de fugas.** Con este
VBIOS, MCLK declara 3, luego `allowed_vdd_mclk_table->entries[3..7]` son **7 registros leidos
pasado el final** de una tabla de 3. Ambas son `kzalloc_flex`: arrays dimensionados
exactamente a la cuenta del VBIOS (`processpptables.c:1485` para fugas, y la equivalente
para MCLK), luego no hay relleno que lo absorba.

**PERO la V0 no corre en Polaris12.** `115` demostro que para `CHIP_POLARIS12` queda
`pp_table_version = PP_TABLE_V1`, y la seleccion es explicita:

```c
/* smu7_hwmgr.c:1068-1070 */
smu7_setup_dpm_tables_v1(hwmgr);
...
smu7_setup_dpm_tables_v0(hwmgr);
```

**Y la V1 esta limpia en ese punto**: usa `dep_sclk_table->count` con `dep_sclk_table->entries[]`
y `dep_mclk_table->count` con `dep_mclk_table->entries[]`, **cada cuenta con su tabla**.

Esto lo compreuebe **antes** de afirmar el fallo, por la regla de "este camino se ejecuta en
mi ASIC?". Si no lo hubiera comprobado, habria publicado una lectura fuera de limites sobre
esta placa que **no ocurre**.

## Por que `PPTable_Generic_SubTable_Header` no ayuda

Porque **no tiene campo de tamaño**:

```c
typedef struct _PPTable_Generic_SubTable_Header {
        UCHAR  ucRevId;          /* lo unico */
} PPTable_Generic_SubTable_Header;                       pptable_v1_0.h:493-495
```

**Una subtabla del PPT declara su revision y nada mas.** No hay longitud, asi que el driver
**no puede** validar el tamano de una subtabla: no hay contra que compararla. El unico dato
de control es `ucNumEntries`, que es un `UCHAR` (0..255), y lo unico que se comprueba es que
no sea cero.

Y `223` ya dejo dicho que un check `> 0` puede ser correcto cuando la subtabla no tiene que
portar datos. **Aqui si tiene que portarlos** (son frecuencias), y aun asi el check es `>= 1`.

## Clasificacion

- `SUBTABLE_HEADER_HAS_NO_SIZE_FIELD = PROVEN`: `PPTable_Generic_SubTable_Header` = 1 byte,
  `ucRevId`. El driver **no puede** validar el tamano de una subtabla.
- `DPM_LEVELS_ARRAY_CAP_IS_8 = PROVEN`: `MAX_REGULAR_DPM_NUMBER = 8` (`smu7_hwmgr.h:95`),
  `dpm_levels[8]` (`:100`), `struct smu7_dpm_level` = `bool` + 2×`uint32_t` (`:88`).
- `V1_LOOP_BOUND_IS_VBIOS_COUNT = PROVEN`: `smu7_hwmgr.c:901`, y el unico assert es
  `count >= 1` (`:888`). **No hay cota superior.**
- `THIS_VBIOS_DECLARES_8_SCLK_ENTRIES = PROVEN`: `ucNumEntries = 8` en `0x9D16`.
- `THIS_VBIOS_IS_EXACTLY_AT_THE_LIMIT = PROVEN_DERIVED`: los 8 `ulSclk` son distintos, luego
  no deduplica; escrituras en `dpm_levels[0..7]`, indice 7 = ultimo valido. **Margen cero.**
  **En esta placa no hay invasion: `PROVEN_ABSENT`.**
- `A_NINE_ENTRY_VBIOS_WOULD_OVERFLOW = PROVEN_DERIVED`: con 9, `dpm_levels[8]` queda fuera y
  ningun check lo detecta. **No ejecutado: `NOT_IN_CORPUS`, hace falta otro VBIOS.**
- `SCLK_RECORD_SIZE_VALIDATED_BY_LAYOUT = PROVEN_DERIVED`: `sizeof = 15` por gcc, y la tabla
  MCLK empieza en `SK + 2 + 8*15` exactamente. **El ROM se valida a si mismo.**
- `V1_LOWEST_SCLK_MATCHES_OBSERVED_PSTATE = PROVEN_DERIVED`: VBIOS 21400 (10 kHz) = 214 MHz;
  la captura viva dice `214 MHz (PSTATE_SCLK)`.
- `V1_IS_CLEAN_ON_TABLE_CROSSING = PROVEN`: cada tabla con su propia cuenta. **REFUTA** la
  idea de que el bug de la V0 alcance a esta placa.
- `V0_CROSS_TABLE_INDEXING_IS_A_DEFECT = PROVEN` **pero `NOT_ON_POLARIS12`**: `:833-837`
  corre 8 veces indexando tablas de 3. **Codigo muerto para esta placa**, por `pp_table_version
  = PP_TABLE_V1` (`115`) y la seleccion de `:1068-1070`.
- `MCLK_RECORD_SIZE_NOT_DETERMINED = NOT_DETERMINED`: lei la tabla MCLK con el stride del
  registro SCLK (15) y los valores salen absurdos (65536000, 4096001000). **El registro MCLK
  tiene otro tamano y no lo medi.** No lo supongo.

## Lo que esto obliga a hacer en un driver propio

1. **Validar el tamano contra la cota, no contra cero.** `count >= 1` es un check de
   presencia. El que importa es `count <= MAX_REGULAR_DPM_NUMBER`, y **cuesta una linea**.
   Mi driver no deberia poder ser convinocado por un VBIOS que declare 9.
2. **Un check `>= 1` es correcto solo si la subtabla no tiene que portar datos.** `223` lo
   dijo para el estado del PPT, que no lleva relojes. **Aqui si los lleva**, y el check sigue
   siendo `>= 1`. **La misma forma de check, correcta en un sitio e insuficiente en el otro.**
   Un driver propio tiene que **saber que promete cada subtabla**, y eso no esta escrito en
   ningun sitio del arbol.
3. **Anadir el campo que falta.** Si el formato tiene `ucRevId` y `ucNumEntries` pero no
   longitud, entonces **el unico contrato posible es la cota del consumidor**. Mi driver
   puede anadir un `usStructureSize` por subtabla, pero eso es cambiar el formato: lo
   correcto es validar contra la cota del array de destino, que es lo que existe.
4. Y la regla de proceso, que hoy me ha pagado dos veces: **preguntar si el camino corre en mi
   ASIC ANTES de afirmar el fallo.** En esta sesion me ha salvado de publicar, por un lado, un
   recorte de temperatura a 0 °C imposible (`222`), y por otro, una lectura fuera de limites
   en la ruta V0 (`224` (antes `224`)). **Las dos habrian sido falsas.**