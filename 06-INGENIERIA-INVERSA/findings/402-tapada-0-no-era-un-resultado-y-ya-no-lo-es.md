# 402 · `TAPADA 0` no era un resultado, y la constante que lo decía ya estaba en el código

WORK_CLASS=READ_ONLY · WRITE_EXECUTION=NONE · MODIFICATIONS 1 (`tools/smc_copy_scope.py`)

> ## Resultado
>
> `smc_copy_scope` 1.4.0 → **1.5.0**. El reparto real de las 13 escrituras de
> `polaris10_smumgr.c` es **7 `SIN_ORDEN`, 3 `VIVA`, 3 `NO_RESUELTO`**, y coincide
> **cifra por cifra** con lo que `278` había calculado a mano. La herramienta ya
> no imprime un `TAPADA 0` que no significaba nada.
>
> Y el aviso de entrada sin usar ha encontrado **una que yo llevaba pasando desde
> el principio de la rama y que nunca se ha usado**.

## El defecto: dos afirmaciones en un solo caso

En `decide()`, el bucle de tapadores hacía `continue` cuando el candidato estaba
en **otra función**:

```python
if a.funcion != b.funcion:
    # El orden textual SOLO es el orden real dentro de una misma funcion.
    continue
```

Y al no encontrar tapador caía siempre en `CASE_UNCOVERED`. Eso mete en el mismo
cubo dos cosas que no son lo mismo:

1. **Nadie contiene este rango.** Entonces está libre de verdad: nadie lo pisa ni
   ahora ni luego. Eso **es un resultado**.
2. **Alguien lo contiene, pero en otra función**, donde el orden textual no es el
   de ejecución. Entonces no se puede decir que esté libre: solo que **no se ha
   comparado**.

`278` ya lo decía de esta forma: «`262` decía que `TAPADA 0` no era un
resultado sino la ausencia de comparación. Tenía razón». Lo que faltaba era que
la herramienta lo dijera.

### Y la constante ya existía

```python
CASE_NO_ORDER = "SIN_ORDEN"     # :62
...
sel = [e for e in todas if e.caso != CASE_NO_ORDER]   # :1763, se filtra del resumen
```

`CASE_NO_ORDER` estaba definida y se usaba para **filtrarla del resumen**, y **no
la asignaba nadie en ninguna parte del fichero**. El vocablo estaba en el código
como nombre y no como comportamiento.

Eso es un tipo deiquelycierto de deuda: no es que falte el concepto, es que
**está escrito y no hace nada**. El filtro era una manera de callar una categoría
que nunca se rellenaba, lo que hacía el filtro indistinguible de una decisión.

## El arreglo

```python
posibles = [b for b in escrituras
            if b.ini is not None and b is not a
            and a.base == b.base
            and a.ini >= b.ini and a.fin <= b.fin]
sin_ordenar = [b for b in posibles if a.funcion != b.funcion]
if sin_ordenar:
    a.caso = CASE_NO_ORDER
    a.nota += "; SIN ORDEN: " + ...
else:
    a.caso = CASE_UNCOVERED
```

El detalle que importa: **el filtro es sobre `funcion`, no sobre «hay algo que lo
contenga»**. Un tapador posible de la **misma** función que aparece **antes** en
el texto no cuenta, porque si `b` contenía a `a` y `b` va antes, entonces `a` se
escribe **después** y **pisa** a `b`. Es al revés, y `a` queda libre de verdad.
Sin ese matiz, un «hay algo que lo contiene» mal_filtered habría turning
`SIN_ORDEN` cosas que sí son `VIVA`.

## Los tres vectores, y el que faltaba

Escribí **tres**, no uno, porque `SIN_ORDEN` se puede hacer pasar de dos formas.

- **caso O**: la escritura cuyo único tapador posible está en otra función →
  `SIN_ORDEN`. Reproduce `:149` frente a `:2118`.
- **caso P**: una escritura que **nadie** contiene → `VIVA`. Sin este, el caso O
  pasaría **por casualidad** y el distinguir sería mentira.
- **caso Q**: un tapador posible de la **misma** función que aparece **antes** →
  `VIVA`. Sin este, el distinguir del caso O también pasaría si se hubiera escrito
  «hay *algo* que lo contiene» sin mirar de dónde.

Los dos contrapesos son la parte que hace que el primero signifique algo.

**Failure check**: reintroduciendo el defecto (`sin_ordenar = []`), `exit=3`:

```
casoO: la escritura cuyo tapador esta en otra funcion debe ser SIN_ORDEN, no VIVA:
       sin el orden de ejecucion no se puede decir que este libre
```

27 vectores, `exit=0`.

## El reparto real, que es el hallazgo

```
RESUMEN
  Dentro de una MISMA funcion el orden textual ES el de ejecucion:
    TAPADA          0  la escritura posterior contiene su rango completo
    VIVA            3  nadie la contiene: esta libre de verdad
  SIN_ORDEN       7  otra funcion contiene su rango, pero entre funciones
                         el orden textual no es el de ejecucion: NI VIVA NI TAPADA
  NO_RESUELTO     3  sin rango: no se puede afirmar cobertura
AVISO: 1 --sizeof sin usar: SMU74_Discrete_FanTable
```

Cada línea dice **qué mide**, que era el otro mitad del encargo.

| caso | líneas | qué es |
|---|---|---|
| `SIN_ORDEN` | `:142` `:149` `:157` `:166` `:1146` `:1246` `:2398` | `:2118` las contendría; el orden no está |
| `VIVA` | `:1511` `:2118` `:2254` | otra base (`arb_table_start`, `fan_table_start`) o nada la contiene |
| `NO_RESUELTO` | `:654` `:1872` `:1881` | `PROVEN_ABSENT`: direcciones que decide el firmware |

**Las siete `SIN_ORDEN` son exactamente las siete escrituras DPM** que `278`
calculó a mano que caen dentro de `108..1883`. La herramienta ha encontrado
`:2118` como tapador posible de las siete y ha dicho, una a una, que **no puede
ordenarlas**.

Y `:2398` —la que `278` dejó a mano como `NOT_DETERMINED` porque «el orden de
ejecución decide y no lo he trazado»— **ahora tiene categoría**, y la categoría
dice justo lo que faltaba: hay una tapadora posible en otra función y el orden no
está. Lo que era una omisión mía es un límite declarado.

## El aviso de entrada sin usar, y lo que encontró

Segunda parte del encargo: que un `--sizeof` o `--contador` ignorado no se pierda
en silencio. Implementado con una subclase de `dict` que anota qué claves se han
**consultado** de verdad:

```python
class Medido(dict):
    def get(self, k, default=None):
        if k in self:
            self.usadas.add(k)
        return dict.get(self, k, default)
```

Solo se envuelven los dict que se construyen desde la línea de órdenes, no los de
los vectores: el aviso debe hablar **solo de lo que el usuario ha escrito**, que
es lo único que puede corregir.

**Y cazó uno mío, de verdad:**

```
AVISO: 1 --sizeof sin usar: SMU74_Discrete_FanTable
        si un nombre esta mal escrito, el NO_RESUELTO que produce no es
        limite del fichero: es una entrada ignorada.
```

`sizeof(SMU74_Discrete_FanTable)` aparece **0 veces** en `polaris10_smumgr.c`. La
escritura de `:2254` usa `sizeof(fan_table)` — una **variable**, no el tipo — así
que el 36 le llega por `--sizeof fan_table=36`. **Llevaba `--sizeof
SMU74_Discrete_FanTable=36` en la línea de órdenes desde el principio de la rama y
nunca ha tenido efecto.** No cambió ningún resultado, porque había otro
nombre que sí valía, pero estaba ahí ocupando sitio y dando la impresión de que
`:2254` se resolvía por la vía que yo creía.

Es el mismo defecto que el shadow de `__contadores__` que corrigió `500`, visto
desde fuera: **un argumento que se acepta y se ignora**. Por dentro lo arreglé en
`500` sin cerrar el hueco de fuera, y aquí lo cierro. La lección es la que escribí
en `500` y que no aplique.

## Lo que no tiene vector, y lo digo

**El resumen y el aviso no tienen vector del selftest.** Los probé con
`OUTPUT VALIDATION` —lejos del fixture, sobre el fichero real, con un
`--sizeof SMU74_NombreQueNoExiste=999` deliberadamente mal escrito para forzar el
camino— y el aviso salió. Pero eso es una comprobación manual, no una del fixture.

Estado honesto: **`decide()` tiene 3 vectores; el resumen y el aviso tienen
`NOT_COVERED_BY_FIXTURE`**. Es la misma clase de hueco que arrastró esta rama desde
`275`, y la razón por la que `262` decía que `TAPADA 0` no era un resultado: **el
fixture cubría `decide()`, no lo que se le enseña a quien lee.**

## Un cuarto error de comprobador mío

El extractor que usé para el reparto usaba `.*` **voraz**:

```python
sed 's/.*polaris10_smumgr.c:\([0-9]*\).*/\1/'
```

Como la nota de `SIN_ORDEN` **cita el tapador** (`SIN ORDEN: polaris10_smumgr.c:2118`),
el voraz se quedaba con el número de `:2118` y **siete escrituras diferentes
salían todas como `:2118`**. Era el cuarto error de comprobador de esta sesión, y
del mismo tipo que los tres de `280`: un patrón que busca una coincidencia que
**aparece dos veces** en la misma línea y elige la que no quiere.

Con `re.match` y un grupo por posición, sin `.*`, el reparto sale limpio. La regla
que se repite entre `280` y aquí: **cuando el texto que se busca aparece más de
una vez, un `.*` es una fuente de números falsos silenciosa**, y hay que contar las
ocurrencias antes de fiarse del resultado.

## Lo que NO afirmo

- **NO** afirmo que `:2118` se ejecute después de `:149`. Sigo sin trazarlo.
  `SIN_ORDEN` **es** esa falta de traza, puesta en el sitio donde se ve.
  `263` ya mostró el orden de `init_overdrive_limits`, que es otro camino.
- **NO** afirmo que `:2118` se ejecute en mi placa. `B_RUNTIME = NOT_EXECUTED`,
  sigue haciendo falta `Autorizo WRITE_EXECUTION para B_EXPERIMENT`.
- **NO** he tocado `artifacts.py` ni `atomrom.py`: son del otro agente.
- **NO** he medido hardware, ni escrito en `/sys`, ni cargado módulos.
- **NO** he tocado el corpus de kernel. Lo único modificado es
  `tools/smc_copy_scope.py`.

## Estado de la herramienta

`smc_copy_scope` 1.5.0 — **`VALIDATED`**, 27 vectores, `exit=0`, y `exit=3` con el
defecto de `SIN_ORDEN` reintroducido.

Sobre `polaris10_smumgr.c`, con las entradas completas de gcc: **10 rangos
correctos, 0 falsos, y por fin un reparto con tres categorías que significan tres
cosas distintas** en vez de un `TAPADA 0` que no significaba ninguna.

## Frontier siguiente

**Trazar el orden entre `polaris10_setup_graphics_level_structure` y
`polaris10_init_smc_table`.** Es el único `SIN_ORDEN` que se puede cerrar sin
hardware, y son siete escrituras.

`263` ya probó un orden en otro camino: `init_overdrive_limits` se llama desde
`amdgpu_device_fw_loading` en `2403`, y `phase2` —que lleva a `pp_hw_init` → `hwmgr_hw_init`→ `polaris10_init_smc_table`— en `2407`. Ese es el mismo esqueleto. La pregunta es si
`polaris10_setup_graphics_level_structure` está antes o después de `:2407`, y si lo
está, por qué camino.

Criterio de cierre: los siete `SIN_ORDEN` pasan a `TAPADA` con `:2118` como
tapador, **o** se convierten en `VIVA` con la prueba de que van después. Lo que no
puede terminar es en `SIN_ORDEN`: o se responde, o la herramienta gana un canal
para decirlo distinto de como lo dice hoy, que es una nota larga pegada al
destino.

Y la segunda, más pequeña y de la misma familia: **dar vectores al resumen y al
aviso**, o marcarlos como no cubiertos en el `TOOLS-STATUS`. Un hueco
reconocido es un hueco; un hueco que se presenta como cerrado es peor que ninguno.