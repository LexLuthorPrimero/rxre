# 506 · La puerta de `:2095`: el divisor DFS sí escribe en la tabla DPM, y el índice cuadra

WORK_CLASS=READ_ONLY · WRITE_EXECUTION=NONE · MODIFICATIONS 0

> ## Resultado
>
> El criterio que declaré en `505` era: «¿la búsqueda del divisor DFS escribe en
> la tabla DPM?». **Respuesta: sí.** Escribe **dos** campos:
> `table->Ulv.BifSclkDfs` y `table->LinkLevel[i-1].BifSclkDfs`.
>
> Y `bif_sclk_table` **está rellena** cuando `:2094` la lee, porque se rellena en
> `:1618`, **cuatro líneas antes** de `:1622`.
>
> La puerta de `:2095` queda **acotada a un rango de valores concretos de mi
> VBIOS**, que puedo extraer con `atomrom.py`. No es un `NOT_DETERMINED` de
> hardware: es un `EVIDENCE_MISSING` mío, y el insumo está en mi captura.

## La cadena, completa y en orden

```
smu7_hwmgr.c:1566  smu7_enable_dpm_tasks
   :1618   result = smu7_setup_default_dpm_tables(hwmgr)
              :1061  smu7_setup_default_dpm_tables
                :1072  smu7_setup_default_pcie_table
                  :666  if (pcie_table != NULL)
                  :680    smum_update_smc_table(hwmgr, SMU_BIF_TABLE)
                             :2374  polaris10_update_smc_table
                               :2347  polaris10_update_bif_smc_table  [2347..2362, leido COMPLETO]
                                 :2352  pcie_table = table_info->pcie_table
                                 :2359  for (i = 0; i < max_entry; i++)
                                 :2360    bif_sclk_table[i] = pcie_table->entries[i].pcie_sclk
   :1619   PP_ASSERT 0 == result  -> "return result"      <-- PUERTA
   :1622   tmp_result = smum_init_smc_table(hwmgr)
              :1913  polaris10_init_smc_table
                :2093  for (i = 0; i <= pcie_speed_table.count; i++)
                :2094    atomctrl_get_dfs_pll_dividers_vi(hwmgr, bif_sclk_table[i], &dividers)
                :2095    PP_ASSERT result == 0 -> return result   <-- LA PUERTA
                :2098    table->Ulv.BifSclkDfs        = dividers.pll_post_divider
                :2100    table->LinkLevel[i-1].BifSclkDfs = dividers.pll_post_divider
```

**`:1618` rellena el array y `:2094` lo lee.** `:1618` está antes que `:1622`, que
está antes que `:2094`. **El dato es válido cuando se usa.**

## `bif_sclk_table` no es una tabla del VBIOS: es un array del host

```c
polaris10_smumgr.h:62   uint32_t  bif_sclk_table[SMU74_MAX_LEVELS_LINK];
polaris10_smumgr.c:2360 smu_data->bif_sclk_table[i] = pcie_table->entries[i].pcie_sclk;
```

Lo que **sí** es del VBIOS es `table_info->pcie_table`. El array intermedio existe
porque el productor (`smu7_setup_default_pcie_table`) y el consumidor
(`polaris10_init_smc_table`) están en ficheros distintos.

## La puerta, y qué la decide

`atomctrl_get_dfs_pll_dividers_vi` (`ppatomctrl.c:486-523`, leído **completo**):

```c
pll_patameters.ulClock.ulClock = cpu_to_le32(clock_value);
result = amdgpu_atom_execute_table(adev->mode_info.atom_context,
        GetIndexIntoMasterTable(COMMAND, ComputeMemoryEnginePLL), ...);
```

Recibe un **escalar**, devuelve un **parámetro de salida** local, y **no tiene
ningún puntero a la tabla DPM**. Ejecuta la tabla `ComputeMemoryEnginePLL` del
VBIOS **una vez por cada `i`**.

Así que la puerta `:2095` es, exactamente:

> *Para todo `i` en `[0, pcie_speed_table.count]`, la tabla `ComputeMemoryEnginePLL`
> devuelve `result == 0` con `bif_sclk_table[i]` como reloj de entrada.*

Y **`bif_sclk_table[i]` viene de `pcie_table->entries[i].pcie_sclk`**, o sea de la
tabla PCIe del VBIOS. Los valores de entrada son, por tanto, **decodificables de mi
captura**.

## El índice cuadra, y lo comprobé porque parecía que no

El bucle de `:2093` lee `bif_sclk_table[i]` para `i` en `[0, count]` inclusive, es
decir **`count + 1` valores**. Y `bif_sclk_table` se rellena en `:2359` para
`i` en `[0, max_entry)`, es decir **`max_entry` valores**.

Con `data->dpm_table.pcie_speed_table.count = max_entry - 1` (`:679`), el bucle pide
`max_entry` valores y hay `max_entry` rellenos. **Coinciden exactamente, sin
desbordamiento.**

El mecanismo es el `+1` del `for` y el `count = max_entry - 1`: reservan una
entrada extra para el **nivel de boot**, que es lo que dice el comentario de
`:667-670`. Si `count` fuera `max_entry`, el bucle leería `bif_sclk_table[max_entry]`,
que no se rellena y valdría cero. **Está bien hecho**, y lo digo porque
`i <= count` con un array rellenado hasta `max_entry-1` es exactamente el patrón que
produce una lectura en cero cuando el código está mal escrito. Aquí no lo está.

## Un caso en el que `bif_sclk_table` sí quedaría en cero

`polaris10_update_bif_smc_table` solo se llama desde la rama `:666 if (pcie_table
!= NULL)`. En la rama `else` (`:681`) hay **seis entradas PCIe hardcodeadas** y
**`bif_sclk_table` no se rellena**.

Y antes, `:645-647` retorna `-EINVAL` si no hay niveles PCIe:

```c
PP_ASSERT_WITH_CODE((data->use_pcie_performance_levels ||
        data->use_pcie_power_saving_levels), "No pcie performance levels!", return -EINVAL);
```

En cualquiera de los dos casos, `bif_sclk_table` queda en cero y `:2094` pide un
divisor DFS para un reloj de **0 MHz**. **Eso sí sería un caso real de lectura en
cero**, y es lo que había que mirar.

Para mi placa no lo puedo afirmar sin dos datos que no he verificado: si mi VBIOS
tiene `pcie_table` con entradas, y si `use_pcie_performance_levels` o
`use_pcie_power_saving_levels` están activos.

## Sobre la revisión, y por qué aquí no aparece

La condición de `smu7_hwmgr.c:1975` es `device == 0x699F && revision == 0xCF`, y mi
revisión sigue siendo `0xC7` de un portador secundario. Aquí **no aparece**: el
bloque solo quita `PowerContainment`, `enable_tdc_limit_feature`,
`enable_pkg_pwr_tracking_feature` y `ClockStretcher`, y ninguno decide si
`bif_sclk_table` se rellena.

Lo digo porque es la diferencia entre las dos cosas: **mi revisión es
discriminante en `505` y no lo es aquí**, y no es lo mismo «no me he enterado» que
«aquí no importa».

## Dos cosas que la pregunta de `505` no contestaba

1. **Si la búsqueda del divisor DFS toca la tabla DPM: sí**, en dos campos. No es
   una puerta que solo pueda fallar: su resultado **es contenido** de la tabla.
2. **Si el fallo puede girar el contenido aunque la copia se haga: no.** Si `:2095`
   salta, `return result` aborta `init_smc_table` **antes** de `:2118`, así que no
   hay versión de la tabla en la que la copia ocurra con `BifSclkDfs` a cero. Son
   las dos caras: la puerta es *todo o nada*.

Eso refina lo que `502` decía. No es «una puerta más entre 16»: es la puerta que
**decide el contenido de dos campos**, y si cae, cae la copia entera.

## Lo que NO afirmo

- **NO** afirmo que la puerta pase. Necesito los `pcie_sclk` de mi VBIOS y ejecutar
  mentalmente `ComputeMemoryEnginePLL`, que **no está en mi corpus**
  (`EVIDENCE_MISSING`).
- **NO** afirmo que mi VBIOS tenga `pcie_table` ni cuántas entradas tiene.
- **NO** afirmo nada de `use_pcie_performance_levels` /
  `use_pcie_power_saving_levels`, que se ponen en `smu7_init_dpm_defaults`
  (`:1803`) y no he seguido.
- **NO** he medido hardware. `B_RUNTIME = NOT_EXECUTED`; hace falta
  `Autorizo WRITE_EXECUTION para B_EXPERIMENT`.
- **NO** he modificado código. `MODIFICATIONS 0`.

## Lo que sí se ha cerrado

De las 16 puertas de `:1913`-`:2118`:

- `:2005` (clock stretcher) — **cerrada en `505`** con las cuatro condiciones
  medidas.
- `:2095` (divisor DFS) — **acotada**: se sabe exactamente qué la decide, de dónde
  salen sus entradas, y que su resultado **es contenido** de la tabla.
- Las otras 14 son populates que devuelven su propio `result`. Ninguna está
  analizada.

Y el estado del `TAPADA 0`/`SIN_ORDEN` de la copia no cambia: la cobertura depende
de que `:2118` se ejecute, y eso depende de 15 puertas, de las cuales **una está
cerrada**.

## Frontier siguiente

**Decidir si mi VBIOS tiene tabla PCIe y con cuántas entradas**, que es el dato que
falta para la rama del `else` de `:681`.

Es una lectura de la captura, no un rastreo de código: el master data table tiene la
ubicación de la tabla PCIe, y `atomrom.py` ya valida las unidades de los objetos
VBIOS. Con el número de entradas y los valores de `pcie_sclk`, la condición de
`:666` queda resuelta, y con ella queda resuelto si `bif_sclk_table` puede estar en
cero en mi placa.

Criterio de cierre: `count` y los `pcie_sclk` de mi VBIOS, leídos de la captura.
Con eso `:666` pasa a `PROVEN` o `REFUTED`, y el caso de lectura en cero queda
descartado o confirmado.

Y si `ComputeMemoryEnginePLL` resulta estar en el VBIOS —que es donde lo ejecuta
`amdgpu_atom_execute_table`—, **esa es la tabla que decide la PLL del reloj de
memoria**, y entonces el contenido de `BifSclkDfs` pasa a ser un dato derivable.
Eso sería el eslabón entre la tabla DPM y los relojes, que es la pregunta con la
que empezó esta rama.