# 907 · El ventilador no se sube al SMC, y la clasificación de escrituras queda medida

> ## CORRECCION — este hallazgo esta REFUTADO en parte. Ver `935`.
>
> ```
> CLAIM-907 v1   el driver copia 8 bytes de un puntero donde el firmware espera 96
>                VALIDATED
> CLAIM-907 v2   REFUTED    -> 935-907-queda-refutada-la-tabla-de-ventilador-se-entrega-entera.md
> ```
>
> **Causa exacta, medida:** hay **dos** variables distintas llamadas `fan_table`.
> La de `:436`, en `polaris10_populate_bapm_parameters_in_dpm_table`, es un
> **puntero** de tipo `pp_advance_fan_control_parameters`, y `sizeof` de ella da 8.
> La de `:2170`, en `polaris10_thermal_setup_fan_table`, es un **struct en la
> pila** `SMU74_Discrete_FanTable`, y `sizeof` de ella da **36**. El `sizeof` de
> `:2255` pertenece a la **segunda** funcion, luego vale 36 y la copia es
> completa. `NAME_MATCH != SEMANTIC_MATCH`.
>
> **Lo que sigue valiendo de este hallazgo:** la clasificacion de las 13
> escrituras, que no depende de la variable `fan_table` y sigue siendo correcta.
>
> **Lo que era falso:** que los parametros de ventilador no lleguen al SMC. En mi
> placa **si llegan**, por dos rutas: la copia de 36 bytes a
> `SMU74_Firmware_Header.FanTable`, y los campos de `advanceFanControlParameters`
> por mensajes PPSMC sueltos en `:2258-2272`. Ademas la curva de ventilacion
> (40/65/85 C -> 20/40/60 %, histeresis 3, techo 4000 RPM) esta en mi VBIOS y las
> cinco guardas de la ruta pasan.
>
> **El texto de abajo se conserva integro y sin corregir**, a proposito: es la
> v1, y el mecanismo del error forma parte de la evidencia.

WORK_CLASS=READ_ONLY · WRITE_EXECUTION=NONE · MODIFICATIONS 0 · AUTHORIZATION NONE · AUTORIA=AGENTE-SMU

> ## Resultado
>
> **Defecto real, medido, y relevante para el objetivo del proyecto.** `:2254`
> copia **8 bytes de un puntero del host** donde el firmware espera **96 bytes de
> parámetros de ventilador**. Los parámetros de control de ventilador no llegan al
> SMC.
>
> Y con la premisa restaurada de `:2118`, la clasificación de las 13 escrituras
> queda medida con la herramienta validada y **todos los offsets viniendo de
> `btfq`**: `TAPADA 4`, `VIVA 3`, `SIN_ORDEN 1`, `NO_RESUELTO 5`.

## 1. El defecto del ventilador

Tres measurements independientes:

```
$ btfq.py size pp_advance_fan_control_parameters
      size_declarado=96   ultimo_campo_ends=96   OK          <- el BTF del modulo cargado

polaris10_smumgr.c:436-437
      struct pp_advance_fan_control_parameters *fan_table =
              &hwmgr->thermal_controller.advanceFanControlParameters;

polaris10_smumgr.c:2254-2256
      res = smu7_copy_bytes_to_smc(hwmgr, smu_data->smu7_data.fan_table_start,
                      (uint8_t *)&fan_table, (uint32_t)sizeof(fan_table),
                      SMC_RAM_END);
```

`sizeof(fan_table)`, con `fan_table` siendo un **puntero**, vale **8** en x86-64.
Y `(uint8_t *)&fan_table` es la dirección de la **variable puntero**, no del
estructo.

**Lo que se copia son 8 bytes de una dirección virtual del host.** Lo que el
firmware espera en `fan_table_start` son los 96 bytes de
`advanceFanControlParameters`.

La intención era evidentemente `sizeof(*fan_table)`, o el `sizeof` del miembro. Es
un `sizeof` de puntero donde debía haber un `sizeof` de objeto. Clásico, y el
cast a `(uint8_t *)&` lo hace parecer intencionado.

### Por qué importa para este proyecto

El objetivo es **rendimiento sostenido**, y el ventilador es el límite térmico de
una RX 550 de 35 W en una caja de 2015. Si los parámetros de control no llegan al
SMC, entonces:

- El SMC los lee como basura, o usa sus propios valores por defecto de ROM.
- Los parámetros que el driver calcula en `thermal_controller.advanceFanControlParameters`
  —ganancia de borde, de hotspot, playable limit, etc.— **no se aplican**.
- El control de ventilador efectivo lo decide el firmware, no el driver.

**Para un driver propio esto es una medida, no un detalle**: si la ruta que
reimplemento tiene este defecto, y el firmware resulta funcionar con sus
defaults, entonces mi driver's job es explicitamente *mejorar* esa parte, y el
punto de partida medible es «el fan control actual es el del firmware, no el del
driver».

Y es un **`VIVA` sin cobertura**: nadie lo sobrescribe. La tabla de ventilador del
SMC recibe 8 bytes de puntero y nada más.

## 2. La clasificación de las 13 escrituras

Con la premisa restaurada —**`:2118` se ejecuta**, porque `usClockStretchAmount` =
2 y `:1696` no aborta— los seis pares `--orden` son legítimos: todas esas
escrituras caen en el rango `108..1883` y `:2118` copia ese rango entero.

```
smc_copy_scope 1.7.0 · VALIDATED, 34 vectores conocidos reproducidos
  1 ficheros · 13 escrituras · 101 offsets · 7 tamanos medidos
```

**Todas las medidas de esta tabla salen de `btfq`, ninguna de un probe mío.**

| | escritura | destino | veredicto |
|---|---|---|---|
| 1 | `:142` | `vr_config_address` | **TAPADA** por `:2118` |
| 2 | `:149` | `graphics_level_address` | **TAPADA** por `:2118` |
| 3 | `:157` | `graphics_level_address` | **TAPADA** por `:2118` |
| 4 | `:166` | `graphics_level_address` | **TAPADA** por `:2118` |
| 5 | `:654` | `pm_fuse_table_offset` | `NO_RESUELTO` |
| 6 | `:1146` | `array` (GraphicsLevel) | `NO_RESUELTO` |
| 7 | `:1246` | `array` (MemoryLevel) | `NO_RESUELTO` |
| 8 | `:1511` | `arb_table_start` | **VIVA** |
| 9 | `:1872` | `tmp` | `NO_RESUELTO` |
| 10 | `:1881` | `tmp` | `NO_RESUELTO` |
| 11 | `:2118` | `offsetof(SystemFlags)` = 108, 1776 B | **VIVA** |
| 12 | `:2254` | `fan_table_start`, 8 B de puntero | **VIVA** |
| 13 | `:2398` | `offsetof(LowSclkInterruptThreshold)` = 1692, 4 B | **SIN_ORDEN** |

```
TAPADA 4 · VIVA 3 · SIN_ORDEN 1 · NO_RESUELTO 5
```

**Las cuatro `TAPADA` son exactamente `:142`, `:149`, `:157`, `:166`** — las
cuatro escrituras AVFS. Confirma la predicción de `403` y cierra el escarabajo que
`608` había dejado abierto: **no sobreviven**, porque `:2118` las pisa.

## 3. Las siete medidas, y de dónde sale cada una

| medida | valor | fuente |
|---|---|---|
| `sizeof(SMU74_Discrete_DpmTable)` | 1884 | `btfq size` |
| `offsetof(SystemFlags)` | 108 | `btfq struct` |
| `offsetof(LowSclkInterruptThreshold)` | 1692 | `btfq struct` |
| `sizeof(SMU74_PIDController)` | 36 | `btfq size` |
| `sizeof(SMU74_Discrete_GraphicsLevel)` | 56 | `btfq size` |
| `sizeof(SMU74_Discrete_MemoryLevel)` | 24 | `btfq size` |
| `sizeof(SMU74_Discrete_MCArbDramTimingTable)` | 384 | `btfq size` |
| `sizeof(fan_table)` | **8** | puntero, x86-64 |
| `graphics_level_size` | **448** | `sizeof` de `[8]`, `:80` |

Y una ambigüedad que **BTF resolvió sin que yo eligiera**: `SMU74_MAX_LEVELS_MEMORY`
está definido en dos sitios con valores distintos —`kv_dpm.h:27` dice 4,
`ci_smumgr.h:27` dice 6— y el BTF lo zanja:

```
MemoryLevel   SMU74_Discrete_MemoryLevel[4]  @708   708+96=804 = byte de LinkLevel   OK
GraphicsLevel SMU74_Discrete_GraphicsLevel[8] @236  236+448=684 = byte de MemoryACPILevel  OK
```

**4**, no 6. Elegir entre dos `#define` contradictorios habría sido inventar; leer la
longitud del array en el binario no es.

## 4. Los cinco `NO_RESUELTO`, con su causa exacta

La herramienta los nombra uno a uno, y **son dos limitaciones suyas**, no del
fichero:

```
:654   destino no reconocido: pm_fuse_table_offset
:1872  destino no reconocido: tmp
:1881  destino no reconocido: tmp
:1146  contador sin valor conocido: array_size
:1246  contador sin valor connuegido: array_size
```

**Las dos primeras son huecos de resolución de destino**, y son del mismo tipo que
el bug de ámbito que `214` ya documentó. La herramienta lo dice en vez de suponer,
que es lo correcto.

**La segunda es un límite real de diseño**: `array_size` es un contador con
**dos valores distintos** en el mismo fichero —

```
:1048  array_size = sizeof(SMU74_Discrete_GraphicsLevel) * SMU74_MAX_LEVELS_GRAPHICS  = 56*8 = 448
:1217  array_size = sizeof(SMU74_Discrete_MemoryLevel) * SMU74_MAX_LEVELS_MEMORY       = 24*4 =  96
```

— y `--contador` los indexa **por nombre plano**, así que uno no puede declarar los
dos.

**Y aquí hay una tentación que registro como tentación:** podría haber pasado
`--contador array_size=448`, que habría resuelto `:1146` **bien** y `:1246` **mal**
— 448 donde son 96. Habría dado `TAPADA 6` y un número limpio, y sería falso.

Es el error «plausible y falso» del día, en su forma más difícil de detectar: no
es un cero, es un número **más** plausible que el correcto. No lo pasé.

## 5. Lo que la herramienta se vigiló a sí misma

Tres veces durante esta iteración la herramienta **[avisa] de mis entradas
ignoradas**, que es exactamente el defecto que se repite en este proyecto:

```
AVISO: 1 --contador sin usar: graphics_level_size
        si un nombre esta mal escrito, el NO_RESUELTO que produce no es
        limite del fichero: es una entrada ignorada.
```

Eso es `SILENT_ZERO_IS_A_CLAIM` cubierto por el propio instrumento: si yo meto una
entrada mal, el `NO_RESUELTO` resultante no se confunde con un límite del código.
Es la razón por la que los cinco `NO_RESUELTO` de aquí **sí son creíbles**: están
declarados, no son silencios.

Y un aviso mío que salió: **olvidé `--sizeof SMU74_PIDController=36`** en una
corrida, y eso dejó a `:2118` sin rango, que a su vez rechacé los seis `--orden`, y
el resultado pasó de `TAPADA 4` a `TAPADA 0` **sin que nada pareciera roto**.

**Un `TAPADA 0` por una entrada que falta es indistinguible de un `TAPADA 0` real.**
Por eso el `AVISO` importa tanto, y por eso este párrafo va en el hallazgo y no en
el informe.

## 6. Errores de esta iteración

**1.** Primer intento: `--orden` con las líneas equivocadas. Di por hecho que
`1511/2254/2398` eran los tapadores, y son las **seis** que nombran a `:2118`. Salió
`TAPADA 0` y no entendí por qué.

**2.** Segundo intento: omití `SMU74_PIDController` y rompí `:2118`. Ya descrito.

**3.** Añadí `--contador array_size_graphics` y `array_size_memory` por separado.
La herramienta me los devolvió como no usadas, con el motivo.

**4.** Dije `graphics_level_size` = 56 sin mirar que
`avfs_graphics_level_polaris10` es **`[8]`** (`:80`). Son 448.

**5.** Escribí un contraste por diferencia de arrays que salió mal —dividí la
diferencia de bytes entre el número de bits de un elemento en vez de entre
elementos— y me dio «1 elementos» para todos. **Lo detecté porque no cuadraba con
los `[N]` declarados, y lo descarté.** El dato bueno es el `[N]` de BTF, no mi
cálculo.

Cinco, y de nuevo todos de la misma familia: una suposición mía actuando como
medición dentro de un pipeline que ya funcionaba.

## 7. Frontier siguiente

**Cerrar los cinco `NO_RESUELTO` con dos arreglos a `smc_copy_scope`, que es mi
herramienta y está bajo mi `--solo`.**

Son dos huecos concretos y los dos son del instrumento, no del código:

```
A) contadores indexados por punto de uso, no por nombre plano
   array_size@1048 = 448   array_size@1217 = 96
   -> los dos son VIVOS y ambos caen en el rango que :2118 copia
   -> resolverlos sube TAPADA de 4 a 6 y cierra la cuenta de 502

B) destinos por puntero local mas profundo: pm_fuse_table_offset, tmp
   -> mismo patron que el bug de ambito de 214, ya conocido
```

Con A y B, las 13 escrituras quedan clasificadas y la pregunta «quién escribe cada
byte de los 1776» pasa de `PARCIAL` a cerrada — que es lo que `502` pedía.

**Criterio de cierre: las 13 escrituras con veredicto, sin ningún `NO_RESUELTO`, y
el reparto final de las 95 tablas del rango copiado.**