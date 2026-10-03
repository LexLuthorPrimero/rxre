# 230  La segunda frontera, barrida: 5 arrays fijos, uno con margen cero y dos hipótesis refutadas

WORK_CLASS=READ_ONLY · WRITE_EXECUTION=NONE · MODIFICATIONS 0

**Barre el alcance que `226` (antes `226`) declaro explicitamente fuera de si mismo.** Dos hipotesis mias
quedan refutadas antes de publicarlas, `224` (antes `224`) sale **precisado**, y aparece una instancia nueva
del patron de `227` (antes `227`) en la ruta de overdrive, que es de usuario.

## La herramienta

`ppt_validate.py` v2.0.0. **55 pruebas, 0 fallos, `TOOL_VALIDATED`** (29 de la frontera 1, 26 de
la nueva). Modo `--frontera {ppt,smu,ambas}`.

La pregunta es la misma que en la frontera 1 —capacidad contra cuenta— pero el alcance es otro:
alli el limite lo pone una `kzalloc_flex`, aqui lo pone **una capacidad escrita en la
cabecera**, y la cuenta que la gobierna es un **campo de runtime**.

## El mapa de los 5 arrays fijos de `smu7_hwmgr.h`

```
array                    cap   escrituras   cota del lazo                        veredicto
performance_levels         2         8      i < performance_level_count        SEGURO por construccion
dpm_levels                 8        23      i < dep_*.count (del VBIOS)         MARGEN CERO
leakage_id                 8         4      i < SMU7_MAX_LEAKAGE_COUNT         SEGURO: la cota ES la capacidad
actual_voltage             8         4      i < SMU7_MAX_LEAKAGE_COUNT         SEGURO: la cota ES la capacidad
voting_rights_clients      8         0      (todas con indice literal)          SEGURO
```

**LosIndices literales se descartan a proposito**: `[0]`, `[1]`, `[3]` no pueden desbordar por si
mismos. El `grep` si los cuenta, y por eso `voting_rights_clients` sale 0 en la herramienta y 8 en
el grep. **Ahi la herramienta tiene razon y el filtro miente.**

`leakage_id` y `actual_voltage` son **el patron bueno**: el lazo esta acotado por la propia macro
de capacidad, no por un contador de runtime. **Es lo que un driver propio deberia escribir.**

## Hipotesis refutada 1: `performance_levels[2]`, el mas estrecho del fichero

Es el array mas apretado del archivo (capacidad **2**) y sus bucles usan un **contador de
runtime**. Facil de declarar como margen cero. **Refutada:**

```c
/* smu7_hwmgr.c:3426, en smu7_apply_state_adjust_rules */
smu7_ps = cast_phw_smu7_power_state(&request_ps->hardware);

/* smu7_hwmgr.c:3733-3745, en smu7_get_pp_table_entry_callback_func_v1 */
performance_level = &(smu7_power_state->performance_levels
                        [smu7_power_state->performance_level_count++]);
PP_ASSERT_WITH_CODE(
        (smu7_power_state->performance_level_count < smum_get_mac_definition(hwmgr, SMU_MAX_LEVELS...)),
        "Performance levels exceeds SMC limit!", return -EINVAL);
PP_ASSERT_WITH_CODE(
        (smu7_power_state->performance_level_count <
                        hwmgr->platform_descriptor.hardwareActivityPerformanceLevels),
        "Performance levels exceeds Driver limit!", return -EINVAL);
```

**`smu7_ps` y `smu7_power_state` son el MISMO tipo.** Y cada `ATOM_Tonga_State` aporta
exactamente **dos** niveles, el de `IndexLow` (`:3733`) y el de `IndexHigh` (`:3761`). El guardia
de `:3742` corta un tercero, y `hardwareActivityPerformanceLevels` vale
`SMU7_MAX_HARDWARE_POWERLEVELS = 2` (`:3067-3068`).

**Capacidad 2 = Low + High. Exactamente el tamano correcto.** Un estado de potencia tiene
exactamente dos relojes, uno por Polo.

**Ademas: en `:3733` solo se CALCULA un puntero.** Las escrituras de verdad empiezan en `:3748`,
ya tras el guardia. **Check-after-write aparente que no es tal**, porque `performance_level =
&arr[count++]` no escribe memoria.

- `PERFORMANCE_LEVELS_2_ES_EXACTAMENTE_LOW_MAS_HIGH = PROVEN_DERIVED`
- `LA_ESCRITURA_NO_OCURRE_HASTA_TRAS_EL_GUARDIA = PROVEN`: `:3733` calcula puntero, `:3748` escribe.

## Hipotesis refutada 2: `:914` lee `entries[count]`

Al ver `if (overdriveLimit.engineClock == 0) overdriveLimit.engineClock = dep_sclk_table->entries[i-1].clk;`
despues de un bucle, el `i` vale `count` y **`entries[count]` seria una lectura fuera de
limites.** Casi lo escribo.

**Es `entries[i - 1]`, no `entries[i]`.** Con `i == count` es la ultima entrada valida.
**Refutada antes de escribir.**

## `224` (antes `224`) sale precisado: el recorte existe, y lo tira dos lineas despues

`224` (antes `224`)dijo que el unico check del count es `>= 1`. **Habia un recorte que no vi:**

```c
/* smu_helper.c:345-358 */
int phm_reset_single_dpm_table(void *table, uint32_t count, int max)
{
        struct vi_dpm_table *dpm_table = (struct vi_dpm_table *)table;
        dpm_table->count = count > max ? max : count;          /* <-- recorte real */
        for (i = 0; i < dpm_table->count; i++)
                dpm_table->dpm_level[i].enabled = false;
        return 0;
}
```

Y `smu7_reset_dpm_tables` (`smu7_hwmgr.c:745-769`) lo llama para **las seis** tablas DPM
pasando `MAX_REGULAR_DPM_NUMBER` como `max`.

**Y aqui esta la precision que cambia el hallazgo:**

```c
/* smu7_hwmgr.c:900, en smu7_setup_dpm_tables_v1, que se llama DESPUES */
data->dpm_table.sclk_table.count = 0;                 /* borra el recorte */
for (i = 0; i < dep_sclk_table->count; i++) {
        if (i == 0 || dpm_levels[count - 1].value != dep_sclk_table->entries[i].clk) {
                dpm_levels[count].value = dep_sclk_table->entries[i].clk;    /* :905 */
                dpm_levels[count].enabled = (i == 0);                        /* :908 */
                data->dpm_table.sclk_table.count++;                           /* :910 */
        }
}
```

**El recorte acota el valor INICIAL y nunca el INCREMENTO.** `:900` y `:916` ponen `count = 0`
justo después de que el recorte lo fijara.

Y hay un mitigador que `224` (antes `224`) no recogio: **el filtro de duplicados de `:902`.** Una entrada solo
se acepta si su reloj **difiere** del anterior. Asi que `count` no crece con `ucNumEntries`, sino
con el numero de **relojes DISTINTOS** de la tabla.

- `EL_RECORTE_EXISTE_Y_ACOTA_EL_VALOR_INICIAL = PROVEN`: `smu_helper.c:352`, invocado con
  `MAX_REGULAR_DPM_NUMBER` en las seis tablas (`:745-769`).
- `PERO_900_Y_916_LO_BORRAN = PROVEN`: `count = 0` despues del reset.
- `EL_BOTE_REAL_LO_DA_EL_NUMERO_DE_RELOJES_DISTINTOS = PROVEN_DERIVED`: filtro de `:902` y `:918`.
- `MI_VBIOS_TIENE_8_RELOJES_DISTINTOS_QUE_ES_LA_CAPACIDAD = PROVEN`: `121`, margen cero.

**Asi que `224` (antes `224`) se queda en pie con un matiz: el desbordamiento no necesita 9 entradas, necesita
9 relojes distintos.** Es mas dificil de alcanzar, no mas facil.

## Lo nuevo: dos indices `count - 1` sin ninguna guarda, en la ruta de overdrive

```c
/* smu7_hwmgr.c:5220-5244 */
static int smu7_set_sclk_od(struct pp_hwmgr *hwmgr, uint32_t value)
{
        ...
        ps = hwmgr->request_ps;
        if (ps == NULL) return -EINVAL;                 /* el unico guardia */
        smu7_ps = cast_phw_smu7_power_state(&ps->hardware);

        smu7_ps->performance_levels[smu7_ps->performance_level_count - 1].engine_clock =
                golden_sclk_table->dpm_levels[golden_sclk_table->count - 1].value * value / 100 +
                golden_sclk_table->dpm_levels[golden_sclk_table->count - 1].value;
        return 0;
}
```

**Dos indices `count - 1` y ni una sola comprobacion de que ninguno sea cero.** Con cualquiera
de los dos contadores a cero, salen `performance_levels[-1]` y `dpm_levels[-1]`.

**Y son alcanzables, por puntero a funcion — la misma trampa que `227` (antes `227`):**

```
smu7_hwmgr.c:5896   .set_sclk_od = smu7_set_sclk_od,
amd_powerplay.c:748  if (hwmgr->hwmgr_func->set_sclk_od == NULL) {
amd_powerplay.c:753  return hwmgr->hwmgr_func->set_sclk_od(hwmgr, value);
amd_powerplay.c:1572 .set_sclk_od = pp_dpm_set_sclk_od,        (en la tabla que se expone al usuario)
```

**Es la misma clase que `:1515` y `:1517` de `227` (antes `227`):** un indice derivado de un contador, sin
guardia. Pero aqui **no hay ni el `if (count < 1) return -EINVAL` que si tenia
`smu7_get_profiling_clk`**, y **la ruta la dispara el usuario**.

- `DOS_INDICES_COUNT_MENOS_1_SIN_GUARDA = PROVEN`: `smu7_set_sclk_od` (`:5238-5241`) y
  `smu7_set_mclk_od` (`:5262` en adelante).
- `ALCANZABLE_DESDE_EL_IOCTL = PROVEN`: `amd_powerplay.c:753`, cableado en `:1572`.
- `NINGUNO_DE_LOS_DOS_CONTADORES_SE_COMPRUEBA = PROVEN`: el unico guardia es `ps == NULL`.
- `CUANDO_SI_ES_ALCANZABLE = NOT_DETERMINED`: depende de si un `count` puede estar a cero, que es
  la cadena de `099` + `:1087 return 0`. **No lo afirmo en ninguna direccion.**

## Mis errores de esta tanda, todos en la herramienta

1. **`_conductor('x->n - 1')` devolvía `'x'`.** Mi `split` partia en el **`-` de `->`**, que no es
   un operador. **Lo cazó el self-test**, y habria contaminado toda la columna «conductor» del
   informe.
2. **El fixture era incoherente:** la cabecera declaraba `dpm_levels` y el codigo escribia
   `tabla`/`tabla2`, asi que el self-test no encontraba ninguna escritura. **Un fixture
   incoherente mide el fixture.**
3. **`_cuerpo_funcion` cogia el `{0}` de un inicializador.** `struct PP_Clocks minimum_clocks =
   {0};` — la firma es multilinea y `find('{', m.end())` encontraba el `{` del inicializador, no
   el del cuerpo. **6 de 8 escrituras salian como `(desconocida)`.** Reescrito con cierre del
   parentesis de parametros y salto de comentarios y cadenas.
4. **La regex exigia `->` justo antes del nombre del array**, y casi todas las escrituras son
   `data->dpm_table.sclk_table.dpm_levels[...]`, una cadena con puntos. **Encontraba 4 de 19.**
5. **El informe no estaba cubierto por el self-test**, asi que al renombrar una clave las 55
   pruebas pasaban y la herramienta **no corria**. Anadido.
6. **Un filtro de grep mio** (`grep -v "^./hwmgr/smu7_hwmgr.c:5[12]"`) excluyo justo las lineas
   donde estaban la definicion y las llamadas, y casi concluyo que `smu7_set_sclk_od` era codigo
   muerto. **Tercera vez en dos dias que un filtro me da un falso negativo.**

## Clasificacion

- `MAPA_DE_LOS_5_ARRAYS_FIJOS = PROVEN`: capacidad, escrituras y cota, por array
- `PERFORMANCE_LEVELS_2_ES_EXACTAMENTE_LOW_MAS_HIGH = PROVEN_DERIVED`
- `LA_ESCRITURA_NO_OCURRE_HASTA_TRAS_EL_GUARDIA = PROVEN`
- `LEAKAGE_ID_Y_ACTUAL_VOLTAGE_ESTAN_ACOTADOS_POR_SU_CAPACIDAD = PROVEN`: el patron bueno
- `VOTING_RIGHTS_CLIENTS_SOLO_CON_INDICES_LITERALES = PROVEN`
- `EL_RECORTE_EXISTE_Y_ACOTA_EL_VALOR_INICIAL = PROVEN`: `smu_helper.c:352`
- `PERO_900_Y_916_LO_BORRAN = PROVEN`
- `EL_FILTRO_DE_DUPLICADOS_LIMITA_A_RELOJES_DISTINTOS = PROVEN_DERIVED`
- `MI_VBIOS_TIENE_8_DISTINTOS_QUE_ES_LA_CAPACIDAD = PROVEN`
- `DOS_INDICES_COUNT_MENOS_1_SIN_GUARDA_EN_LA_RUTA_DE_OD = PROVEN`
- `ALCANZABLE_DESDE_EL_IOCTL = PROVEN`: `amd_powerplay.c:753`
- `MI_HIPOTESIS_SOBRE_914 = REFUTADA`: era `entries[i - 1]`
- `MI_HIPOTESIS_SOBRE_PERFORMANCE_LEVELS = REFUTADA`
- `CINCO_ERRORES_DE_LA_HERRAMIENTA = CORRECTED`, todos en el self-test o en la correccion

## Lo que esto obliga a hacer en un driver propio

1. **Un recorte en el reset no acota el relleno.** Aqui existe, se pasa la capacidad
   correctamente, y **dos lineas despues se tira con `count = 0`**. El recorte tiene que estar
   **donde se incrementa**, no donde se inicializa.
2. **Un indice `count - 1` exige `count >= 1` delante, siempre.** Sin excepcion. Y si hay dos
   indices en la misma expresion, **los dos**.
3. **El mitigador real no era el recorte: era el filtro de duplicados.** Un filtro que descarta
   repetidos reduce el numero de elementos aceptados, y **eso** es lo que impide el
   desbordamiento. **Un recorte que se tira no protege nada; un filtro en el bucle, si.**
4. **Acotar el lazo por la propia macro de capacidad**, como hace `leakage_id`, es el patron que
   quiero copiar: no depende de un contador que otro puede cambiar.
5. **La ruta de overdrive es de usuario y se carga con lo que el resto del driver no dejo
   afirmar.** `smu7_set_sclk_od` no comprueba nada porque confia en que los contadores estan bien.
   **Mi driver no va a confiar: va a comprobar.**

## Estado

Hallazgo **129**: la segunda frontera queda barrida con herramienta propia, `224` (antes `224`) precisado, dos
hipotesis refutadas y una instancia nueva del patron de `227` (antes `227`) **alcanzable desde el ioctl**.