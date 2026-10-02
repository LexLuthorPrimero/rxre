# 099 · El retorno del setup de tablas DPM se ignora: con el PPT ausente, 8 y 4 niveles de valor cero

WORK_CLASS=READ_ONLY · WRITE_EXECUTION=NONE · MODIFICATIONS 0

## El fallo

`smu7_hwmgr.c:1067-1068`, dentro de `smu7_setup_default_dpm_tables`:

```c
smu7_reset_dpm_tables(hwmgr);

if (hwmgr->pp_table_version == PP_TABLE_V1)
        smu7_setup_dpm_tables_v1(hwmgr);          /* 1068: sentencia suelta */
else if (hwmgr->pp_table_version == PP_TABLE_V0)
        smu7_setup_dpm_tables_v0(hwmgr);          /* 1070: tambien suelta */

smu7_setup_default_pcie_table(hwmgr);
```

El valor de retorno de `smu7_setup_dpm_tables_v1` **no se asigna, no se comprueba y no
se propaga**. Es una sentencia suelta dentro de un `if` sin otra cosa que hacer con la
expresion.

Y no es que el resto de la funcion descarte resultados: la linea siguiente
(`:1072`) opera sobre el resultado de `smu7_setup_default_pcie_table`, y `:1075-1076`
copia la tabla. El patron "comprueba el resultado" **existe en esa misma funcion**; lo
que falta es aplicarlo a la llamada que decide el contenido de los niveles.

## Que queda en los contadores si el setup falla

La cadena completa, verificada linea a linea:

**Paso 1.** `smu7_reset_dpm_tables` (`:743`) hace `memset(&(data->dpm_table), 0x00,
sizeof(data->dpm_table))`. **Todos los valores a cero**, contadores incluidos.

**Paso 2.** Luego fija los contadores al minimo (`:745-753`):

```c
phm_reset_single_dpm_table(&data->dpm_table.sclk_table,
                smum_get_mac_definition(hwmgr, SMU_MAX_LEVELS_GRAPHICS),
                MAX_REGULAR_DPM_NUMBER);
phm_reset_single_dpm_table(&data->dpm_table.mclk_table,
                smum_get_mac_definition(hwmgr, SMU_MAX_LEVELS_MEMORY),
                MAX_REGULAR_DPM_NUMBER);
```

**Paso 3.** `polaris10_get_mac_definition` (`:2467-2470`) devuelve
`SMU74_MAX_LEVELS_GRAPHICS` y `SMU74_MAX_LEVELS_MEMORY`, que son 8 y 4
(`smu74.h:32`, `:33`, `:134-135`). Y `MAX_REGULAR_DPM_NUMBER` es 8
(`smu7_hwmgr.h:95`).

**Paso 4.** `phm_reset_single_dpm_table` (smu_helper.c:352) hace
`dpm_table->count = count > max ? max : count;` o sea el **minimo de los dos**.

Resultado: `sclk_table.count = min(8,8) = 8` y `mclk_table.count = min(4,8) = 4`.

**O sea: tras el reset, los contadores NO valen cero. Valen 8 y 4, con los ocho y los
cuatro valores de frecuencia a cero.**

Eso es lo que hace el fallo peligroso: `count` es un numero valido y grande, asi que
todo el codigo aguas abajo cree que hay ocho niveles de graficos y cuatro de memoria,
cuando en realidad las frecuencias son todas cero.

## Y por que el setup puede fallar sin que se note

`smu7_setup_dpm_tables_v1` retorna `-EINVAL` en estos casos (`:879-897`):

- `!hwmgr->pptable` (`:885-887`)
- `dep_sclk_table == NULL` (`:888-890`)
- `dep_mclk_table == NULL` (`:895-897`)

`dep_sclk_table` sale de `table_info->vdd_dep_on_sclk` (`:882`), y ese puntero se queda
**nulo** cuando el PPT no tiene tabla de dependencia: el productor
`get_sclk_voltage_dependency_table` solo se invoca si
`powerplay_table->usSclkDependencyTableOffset != 0`
(`process_pptables_v1_0.c:829`), y si no, el puntero conserva el `NULL` con que se creo
(`:815`).

Y el punto que cierra el circuito: **el parser del PPT retorna 0 en ese caso**, asi que
`pptable_init` **tambien** reporta exito, y `hwmgr_hw_init` no aborta. Un PPT sin tabla
de dependencia de reloj pasa las dos capas de inicializacion sin levantar una sola
advertencia.

## La tabla que se sube al SMC

`polaris10_init_smc_table` corre igualmente (es invocado desde `smu7_hw_init`,
`smu7_hwmgr.c:1622`), y el bucle de niveles (`polaris10_populate_all_graphic_levels`,
`:1067-1078`) itera `count` veces, o sea **8 veces**, con frecuencias todas cero. Los
ocho `GraphicsLevel[]` se llenan con datos derivados de una frecuencia de 0 Hz.

Y la copia a la SRAM es de tamaño fijo
(`sizeof(SMU74_Discrete_GraphicsLevel) * SMU74_MAX_LEVELS_GRAPHICS`, `:1048-1049`),
asi que los **ocho** niveles viajan al firmware, con el ultimo byte del rango de la
tabla entero a cero y ningun hueco detectable por tamano.

## Y `smc_state_table` no se limpia nunca

Confirmado por busqueda: el **unico** `memset` de `polaris10_smumgr.c` esta en `:2574`
y es para `mc_reg_table`. No hay ninguno para `smc_state_table`.

El unico cero del que parten los campos no escritos viene de `kzalloc_obj` en
`polaris10_smu_init` (`:339`), que ocurre **una sola vez**. Por eso el valor de los
niveles no escritos es cero en la primera ejecucion, y **residual de una ejecucion
anterior** si la tabla se vuelve a construir. Es el mismo patron que `096`, pero aqui
el agregado no es de pila: es un miembro del contexto, y por eso el valor depende de
si la funcion se ejecuta una o varias veces.

## Lo que esto NO dice

No dice que el PPT de esta placa tenga el desplazamiento a cero. Es un dato del VBIOS:
`RUNTIME_MISSING`. **La falta de comprobacion es `PROVEN`**; que se dispare depende del
VBIOS de la placa.

No dice que el firmware rechace una tabla con frecuencias a cero. Que hace con ella es
`NOT_IN_CORPUS`.

No he medido si `smu7_setup_dpm_tables_v1` se puede llamar mas de una vez sobre el mismo
contexto, que es lo que decide si el caso de la_execucion anterior llega a iniciar. Es
`EVIDENCE_MISSING`, y lo dejo declarado como tal en vez de suponerlo.

## Clasificacion

- `SMT_SETUP_DPM_RETURN_IGNORED = PROVEN`: `smu7_hwmgr.c:1068`, sentencia suelta. El
  patron de comprobar existe en `:1072` y `:1075-1076` de la misma funcion.
- `SMT_RESET_SETS_COUNTS_TO_8_AND_4 = PROVEN_DERIVED`: `memset` en `:743`,
  `phm_reset_single_dpm_table` con `min` (smu_helper.c:352),
  `polaris10_get_mac_definition` `:2467-2470`, `MAX_REGULAR_DPM_NUMBER` = 8.
  Los valores quedan a cero por el `memset` de `:743`.
- `SMT_NO_ZERO_COUNT_PATH = PROVEN`: si V1 falla, `count` no es 0 sino 8 y 4. Un
  consumidor que compruebe `count > 0` no detecta nada.
- `SMT_NULL_DEP_TABLE_FROM_ZERO_OFFSET = PROVEN` el mecanismo,
  `process_pptables_v1_0.c:815` y `:829`.
- `SMT_PPT_INIT_RETURNS_SUCCESS_WITHOUT_DEP_TABLE = PROVEN`: el parser retorna 0,
  `hwmgr_hw_init` no aborta. Dos capas de exito sobre datos ausentes.
- `SMT_SMC_STATE_TABLE_NEVER_CLEARED = PROVEN_ABSENT`: unico `memset` del fichero en
  `:2574`, para `mc_reg_table`.
- `SMT_DPM_TABLE_FIXED_SIZE_COPY = PROVEN`: `:1048-1049` y la copia, independiente del
  valor de `count`.

## Lo que esto obliga a hacer en un driver propio

**Comprobar el retorno de la construccion de tablas antes de usarlas.** Es una linea, y
es la que falta. Un driver propio que no la escriba hereda exactamente este fallo: ocho
niveles que parecen ocho y son ocho ceros.

Y **limpiar el destino una vez, no confiar en el `kzalloc` de arranque**: si la tabla se
puede reconstruir (OverDrive, cambio de PPT, parcheo), el cero de la primera vez no
sigue ahi. La regla es la de `096` pero aplicada al contexto y no a la pila.
