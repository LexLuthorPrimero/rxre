# 500 · El shadow de los contadores, y que el mensaje acusa al fichero de algo que sí tiene

WORK_CLASS=READ_ONLY · WRITE_EXECUTION=NONE · MODIFICATIONS 1 (`tools/smc_copy_scope.py`)

> ## Resultado
>
> `smc_copy_scope` 1.3.0 → **1.4.0**. La rama queda **cerrada**: **10 escrituras
> resueltas, 0 sin resolver en principio**, y las 3 que quedan sin resolver son
> las `PROVEN_ABSENT` de siempre. Y el hueco que se persiguió al final de `280`
> no era un hueco del shadow: **el identificador desnudo nunca fue candidato**.

## El criterio de cierre, cumplido

Declarado en `280`: `:149` debe dar `236..683 448B` **sin** que haya que pasar
`--contador graphics_level_size`, porque el valor está en `:128`.

```
:149  graphics_level_address  tam=236..683 448B
      (variable local graphics_level_address + contador graphics_level_size)
```

El motivo dice `contador graphics_level_size`: leído del fichero, no de la línea
de órdenes. `RESUMEN: VIVA 10 · NO_RESUELTO 3`.

## Eran tres defectos, no uno

Escribí los vectores **antes** de dar el arreglo por bueno, y eso decidió la
iteración: los dos vectores nuevos **fallaron** con mi arreglo ya aplicado. Si los
hubiera escrito después, habría publicado un arreglo que no arregla.

### A · el shadow del mapa local

```python
# antes
ctx_cont = ctx_amb.get("__contadores__", contadores)
# ahora
ctx_cont = dict(contadores)
ctx_cont.update(ctx_amb.get("__contadores__", {}))
```

`:739` creaba la clave `__contadores__` para **toda** función con cualquier
sentencia reconocida, aunque quedara vacía. Como la clave existía siempre, el
`.get` con valor por defecto nunca llegaba a mirar el global, y un `--contador`
que el usuario acababa de escribir **se perdía en silencio**.

### B · el `sizeof` a secas no era un contador

El patrón de contadores locales exigía `sizeof(T) * CONSTANTE`. La forma
`graphics_level_size = sizeof(avfs_graphics_level_polaris10);` no casa. Al caer a
`RE_LOCAL_ADDR`, `resuelve_destino` devuelve `None` —un `sizeof` no es un
`offset`— y el valor se perdía.

### C · el que de verdad importaba

**Un identificador desnudo nunca fue candidato a tamaño.** En los dos regex que
deciden si un argumento es un contador:

```python
# antes
r"^\(?\s*(?:uint32_t|uint16_t|uint8_t|unsigned|int)\s*\)?\s*([A-Za-z_]\w*)$"
# ahora: el grupo del tipo pasa a ser opcional
r"^\(?\s*(?:(?:uint32_t|...)\s*\)?\s*)?([A-Za-z_]\w*)$"
```

El grupo del tipo era **obligatorio**. Un argumento como `graphics_level_size`,
que en `:151` va **a secas** sin cast, no casaba nunca: no era ni un `sizeof`, ni
un número, ni un «contador conocido». Los tres filtros lo rechazaban y el
argumento desaparecía.

**Este es el que cerro el hueco, y no lo había detectado en `280`.** En `280` atribuí
el fallo al shadow y al patrón del `sizeof`. Los dos eran reales, pero ninguno
era lo que rompía `:149`. Lo que lo rompía estaba una línea más abajo.

## El mensaje mentía, y eso era lo peor

`:149` reportaba `tamano: sin argumento de tamano`.

**El argumento de tamaño está escrito en el fichero**, en `:151`. La herramienta
no lo esaba, pero el motivo que daba era «no hay argumento», que es una
afirmación sobre el fichero **y es falsa**. Un `NO_RESUELTO` honesto habría sido
`contador sin valor conocido: graphics_level_size`: dice la verdad, y señala la
línea exacta a mirar.

Arreglado: un argumento que **es** un identificador pero cuyo valor se desconoce se
guarda aparte, y si nada mejor casa se usa ese para que `resuelve_tamano` produzca
el mensaje verdadero.

Esto es `SEMANTIC_MISSING` en la forma más peligrosa: no es un dato que falta, es
una etiqueta que **describe mal al corpus**. Una herramienta que acusa al fichero
de no declarar algo que sí declara dirige la búsqueda al sitio equivocado, y el
error cuesta más que el hueco original.

## La validación, y por qué esta vez sí

**Escribí los vectores primero.** El orden importa: al revés, el fixture no
detecta el defecto y el arreglo se publica sin comprobar.

- **caso M**: una función con contador local propio (`array_size`) que además usa
  un contador que solo viene de la línea de órdenes (`lote`). Cazaría el shadow.
- **caso N**: `x = sizeof(T)` a secas, sin multiplicador. Cazaría el patrón.

Los dos fallaron con el arreglo aplicado. Corregido el identificador desnudo, los
dos pasan.

**Failure check por cambio, no en bloque.** Tres variantes, cada una revirtiendo
**un solo** cambio:

| revertido | `exit` | lo cazan |
|---|---|---|
| A · el shadow | 3 | solo caso M |
| B · el `sizeof` a secas | 3 | solo caso N |
| C · el tipo opcional | 3 | caso M **y** caso N |

Correspondencia **1:1**. Los tres cambios son necesarios y ninguno sobra: no hay
código muerto. 24 vectores, `exit=0`.

## El recuento final de la rama

```
10 escrituras resueltas, con el rango que dice gcc
3 sin resolver en principio: direcciones que decide el firmware
0 rangos falsos
```

| línea | destino | rango | base |
|---|---|---|---|
| `:142` | `VRConfig` | 112..115 | `dpm_table_start` |
| `:149` | `GraphicsLevel` | **236..683** | `dpm_table_start` |
| `:157` | `MemoryLevel` | 708..731 | `dpm_table_start` |
| `:166` | `BootMVdd` | 1592..1593 | `dpm_table_start` |
| `:1146` | `GraphicsLevel` | 236..683 | `dpm_table_start` |
| `:1246` | `MemoryLevel` | 708..803 | `dpm_table_start` |
| `:2118` | copia | 108..1883 | `dpm_table_start` |
| `:2398` | `LowSclkInterruptThreshold` | 1692..1695 | `dpm_table_start` |
| `:1511` | `arb_table_start` | 0..383 | **otra base** |
| `:2254` | `fan_table_start` | 0..35 | **otra base** |

Los diez contrastan con medidas de gcc tomadas todas en esta cadena: 112, 236,
708, 1592, 108, 1692, 384, 36.

## La lección, y es la que ya estaba pagada

En `280` escribí que el hueco restante era el shadow. **Era el shadow, y no era
el hueco.** Había tres defectos encadenados, cada uno delante del siguiente, y el
primero tapaba al tercero.

Es la tercera vez que un diagnóstico mío nombra un defecto real pero no **el**
defecto: el `SIZE` de `:1704`, el `:654` de `275`, y ahora este. En los tres casos
el defecto que nombré **existía** y arreglarlo Avanzó de verdad. El patrón que se
repite no es «me equivoco de archivos»: es **que un hueco visible puede tener
varias causas y pararse en la primera que se ve**.

La diferencia entre este caso y `275` es que allí no comprobé el input antes de
atribuir el hueco a la herramienta, y aquí lo comprobé. La disciplina que funcionó
fue otra, y es la que hay que automatizar: **escribir el test que falla antes de
escribir el arreglo**, y revertir **cada** cambio por separado para ver cuál lo
caza. Con un cambio bloque la correspondencia 1:1 no se ve, y un arreglo a medias
—que arregla el síntoma y no la causa— pasa igual.

## Lo que NO afirmo

- **NO** afirmo que `:2118` se ejecute en mi placa. `B_RUNTIME = NOT_EXECUTED`,
  sigue haciendo falta `Autorizo WRITE_EXECUTION para B_EXPERIMENT`.
- **NO** afirmo el orden entre `:2398` y `:2118`. Sigue `NOT_DETERMINED`, y es el
  único punto abierto de la cobertura.
- **NO** he tocado `artifacts.py` ni `atomrom.py`: son del otro agente.
- **NO** he medido hardware, ni escrito en `/sys`, ni cargado módulos.
- **NO** he tocado el corpus de kernel. `smc_copy_scope.py` es mío y es lo único
  modificado.

## Estado de la herramienta

`smc_copy_scope` 1.4.0 — **`VALIDATED`**, 24 vectores, `exit=0`, y `exit=3`
reverting cualquiera de los tres cambios por separado.

En el fichero real: **10 rangos correctos, 0 falsos, 0 huecos propios.** Los 3
`NO_RESUELTO` restantes son `PROVEN_ABSENT` por diseño: direcciones que lee el
firmware del SMC y que no son determinables estáticamente.

## Frontier siguiente

**El `TAPADA 0` es lo último que queda, y es un problema de la herramienta, no
del código.** El resumen dice que lo compara en orden textual, y lo admite en su
propio pie, pero lo imprime como si fuera un resultado.

Es un dato que **no depende del reloj**: son rangos de un `struct` y de otro
`dpm_table_start`, y la pregunta «¿está este rango dentro de aquel?» es
aritmética. Con los diez rangos ya medidos, la cobertura se puede calcular
entera, y `278` ya la hizo a mano: las seis escrituras DPM caen dentro de
`108..1883`.

El criterio de cierre es que la herramienta deje de **mostrar** `TAPADA 0` como
cifra y lo distinga explícitamente entre «ninguna tapada» y «no se ha comparado
por falta de orden de ejecución», que son dos afirmaciones distintas. Y una
segunda cosa, más pequeña pero de la misma familia: que **`smc_copy_scope` avise
cuando un `--contador` o un `--sizeof` que le han pasado no se ha usado**, porque
un argumento ignorado en silencio es el mismo defecto que acabo de arreglar, y lo
he arreglado **por dentro sin cerrar el hueco de fuera**.