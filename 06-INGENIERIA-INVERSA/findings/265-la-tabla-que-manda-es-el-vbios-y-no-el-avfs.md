# 265 · La tabla que manda es la del VBIOS, y el techo de SCLK es 1071 MHz

WORK_CLASS=READ_ONLY · WRITE_EXECUTION=NONE · MODIFICATIONS 0

> ## Que responde
>
> `263` dejó una pregunta: si la tabla de host y las constantes AVFS coinciden,
> la ruta AVFS es inocua; si difieren, el techo efectivo lo decide el VBIOS.
> **Difieren.** Y la que sobrevive es el VBIOS.

## La comparacion, con los dos lados medidos

**Lado B, lo que escribe la tabla de host.** La cadena real:

```
polaris10_smumgr.c:1067   for (i = 0; i < dpm_table->sclk_table.count; i++)
polaris10_smumgr.c:1069     polaris10_populate_single_graphic_level(hwmgr,
polaris10_smumgr.c:1070         dpm_table->sclk_table.dpm_levels[i].value, ...)
polaris10_smumgr.c:1071         &(smu_data->smc_state_table.GraphicsLevel[i]));
```

`dpm_table->sclk_table.dpm_levels[i].value` es **el valor crudo del registro SCLK
del VBIOS**, y la reconstruccion de `121` los deja:

| nivel | valor crudo | MHz |
|---:|---:|---:|
| 0 | 21400 | 214 |
| 1 | 55100 | 551 |
| 2 | 73400 | 734 |
| 3 | 98000 | 980 |
| 4 | 100000 | 1000 |
| 5 | 102000 | 1020 |
| 6 | 104600 | 1046 |
| 7 | 107100 | **1071** |

Dentro de `polaris10_populate_single_graphic_level` (`:955`):

- `:967  polaris10_calculate_sclk_params(hwmgr, clock, &curr_sclk_setting)`
- `:902  sclk_setting->SclkFrequency = clock;`   ← **asignacion directa, sin conversion**
- `:975  polaris10_get_dependency_volt_by_clk(hwmgr, vdd_dep_table, clock,
        &level->MinVoltage, &mvdd)`

Asi que **la frecuencia y el voltaje minimo de la tabla de host salen de las
tablas de dependencia del VBIOS**, no de ningun valor de compilacion.

**Lado A, las constantes AVFS** (`polaris10_smumgr.c:80-91`), primer campo del
`SMU_SclkSetting` de cada nivel:

```
0x30750000  0x409c0000  0x50c30000  0x60ea0000
0x70110100  0x80380100  0x905f0100  0xa0860100
```

## No es un cambio de unidad

Es la comparacion que hace falta y que se puede hacer sin inventar nada:

| nivel | VBIOS (host) | AVFS | cociente |
|---:|---:|---:|---:|
| 0 | 21400 | 0x30750000 = 812974080 | 37989 |
| 7 | 107100 | 0xa0860100 = 2693136640 | 25146 |

**El cociente no es constante**, asi que no es una conversion de unidades sino
**magnitudes distintas**. Y los `MinVoltage` tampoco coinciden: el host los saca
de `vdd_dep_on_sclk` del VBIOS (`:972`, `:975`), y el AVFS lleva literales
`0x100ea446`, `0x400ea446`, `0x740ea446`...

Un intento mio de decodificar `MinVoltage` como float32 **dio basura** —ceros
negativos y cifras de 10^30—, asi que **no es un IEEE754 plano** y descarto esa
decodificacion en vez de forzar un numero. La unidad del campo es
`SEMANTIC_MISSING`: la codificacion de `SMU_VoltageLevel` esta en el firmware,
no en las cabeceras de este corpus.

## Consecuencia

Por el orden ya probado en `263` (A en `2403`, B en `2407`), lo que queda en la
RAM del SMC es **la tabla derivada del VBIOS**:

- frecuencias SCLK: **214 a 1071 MHz**, con el `MinVoltage` de
  `vdd_dep_on_sclk` del VBIOS
- `MemoryLevel`: **96 bytes, cuatro niveles**, mientras el AVFS escribe **24
  bytes, un solo nivel** — la diferencia no es de contenido sino de cantidad

O sea que el techo de SCLK lo fija el **VBIOS en 1071 MHz**, y despues el
**firmware recibe 1071 MHz de SCLK** con un `MinVoltage` tomado de
`vdd_dep_on_sclk`. El AVFS no solo se sobrescribe: ademas A escribe un nivel de
memoria y B escribe cuatro.

## Y un detalle de nombre que no es menor

La constante se llama `avfs_graphics_level_polaris10`. Este fichero es el que
usa **POLARIS12** tambien (`chip_id = 17`, `hwmgr.c:500-501`). Es decir: una
tabla calibrada para **Polaris10** se aplica a **Polaris12**, y ademas se
sobrescribe. Son dos problemas independientes que apuntan al mismo sitio.

No afirmo que los valores AVFS sean "malos" para Polaris12. Afirmo que **no
llegan al hardware por esta ruta**, asi que su correccion o no es irrelevante
para el comportamiento de mi placa.

## Lo que esto NO dice

- **NO** afirmo que 1071 MHz sea el techo alcanzable. Es el tope que declara el
  VBIOS. La ruta de overdrive de `127` puede pasar de ahi, y
  `UL_MAX_OD_ENGINE_CLOCK = 180000` dice que si.
- **NO** he medido ningun reloj. `B_RUNTIME = NOT_EXECUTED`.
- **NO** he comparado el contenido byte a byte de las tablas, porque
  `SMU_VoltageLevel` no se puede decodificar desde este corpus. La comparacion
  que he hecho es de `SclkFrequency`, que si es un `uint32_t` directo (`:902`).

## Lo que si queda cerrado

- `THIS_GPU_EFFECTIVE_SCLK_CEILING_FROM_VBIOS_1071_MHZ = PROVEN`: el techo lo
  declara el VBIOS, y el camino que lo entrega a la RAM del SMC esta trazado
  hasta la llamada final.
- `AVFS_TABLE_IS_OVERWRITTEN = PROVEN`: orden de ejecucion de `263` mas esta
  comparacion.
- `HOST_TABLE_AND_AVFS_DISAGREE = PROVEN` en `SclkFrequency`, por cociente no
  constante.

## Estado epistemico que cambia

En `127` y `224` el techo de 1071 MHz estaba tratado como "el maximo de la tabla
de dependencias". Ahora queda Cornfirmado que es tambien **el maximo que llega al
SMC**, porque es la tabla que sobrevive. Eso refuerza la ruta B de overdrive como
la unica via por encima de ese numero, y no es un dato teorico: es lo que el
firmware recibe.

## Frontier siguiente

La codificacion de `SMU_VoltageLevel`. Si el firmware la entiende como un float
con una escala fija, entonces los `MinVoltage` del VBIOS y los del AVFS se
pueden comparar en milivoltios, y eso da el voltaje por nivel de reloj: la
curva V-f que decide si 1071 MHz es sostenible con el voltaje disponible. Es la
pieza que falta para poder afirmar un techo **real** en vez de un techo
**declarado**. Discriminante barato: buscar la escala en el firmware SMC del
corpus, que es `RUNTIME_MISSING` con lo que tengo.