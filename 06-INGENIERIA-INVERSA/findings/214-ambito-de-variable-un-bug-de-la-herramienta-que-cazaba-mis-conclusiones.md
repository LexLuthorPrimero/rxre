# 214  Un bug de mi herramienta daba rangos falsos, y el caso que lo fija

WORK_CLASS=READ_ONLY · WRITE_EXECUTION=NONE · MODIFICATIONS 0

## El bug

`smc_copy_scope` resolvia las variables locales de direccion **una sola vez para todo el
fichero**. El codigo real define la **misma variable con distintos valores en dos
funciones**:

```c
/* polaris10_populate_all_graphic_levels, :1046 */
uint32_t array = smu_data->smu7_data.dpm_table_start + offsetof(..., GraphicsLevel);
uint32_t array_size = sizeof(struct SMU74_Discrete_GraphicsLevel) * SMU74_MAX_LEVELS_GRAPHICS;

/* polaris10_populate_all_memory_levels, :1215 */
uint32_t array = smu_data->smu7_data.dpm_table_start + offsetof(..., MemoryLevel);
uint32_t array_size = sizeof(SMU74_Discrete_MemoryLevel) * SMU74_MAX_LEVELS_MEMORY;
```

`array` y `array_size` tienen el mismo nombre y valores distintos. Al resolverlos una vez
para el fichero entero, **la segunda funcion heredaba los valores de la primera**.

Consecuencia concreta antes del arreglo:

| escritura | lo que decia | lo correcto |
|---|---|---|
| `:1243` | `236..683`, 448 B | **`708..803`, 96 B** |

Es decir: la herramienta atribuia a `MemoryLevel` el rango de `GraphicsLevel`, y un
tamanio de 448 bytes donde el codigo copia 96. **Un numero plausible y falso**, que es el
fallo que esta herramienta existe para evitar.

Y es el **mismo error de base de referencia** que cometi a mano cuatro veces: usar un
contexto que no es el del objeto. En la herramienta es `array` de otra funcion; en mis
cuentas manuales era la struct equivocada.

## El arreglo, en dos dimensiones

**1. Ambito por funcion.** Cada variable se resuelve en el ambito de la funcion que la
declara, y se consulta en el ambito de la escritura. El mapa se indexa por el **indice**
de la funcion en las dos operaciones: antes se indexaba por el inicio y se consultaba por
el indice, las dos claves no coincidian, el mapa se llenaba y **nunca se consultaba**, y la
herramienta devolvia cero escrituras sin decirlo.

**2. Los contadores tambien son locales.** `array_size` es un contador de tamano, y vale
448 en una funcion y 96 en la otra. Con un unico `--contador array_size=448` de la linea
de ordenes, una pisaba a la otra. Ahora cada funcion tiene sus contadores, y el global
sirve solo de respaldo.

**3. Los multiplicadores son `#define`, no numeros.** El codigo no dice `* 8`, dice
`* SMU74_MAX_LEVELS_GRAPHICS`. La herramienta los lee ahora de las cabeceras, con
**resolucion de alias en cadena**: `SMU74_MAX_LEVELS_GRAPHICS` vale
`SMU__NUM_SCLK_DPM_STATE`, que vale `8`. Con tope de profundidad, para que un ciclo de
alias no se convierta en un bucle infinito que devuelva un 0.

## El resultado, ya correcto

```
:1143  236..683  448 B   polaris10_populate_all_graphic_levels   (GraphicsLevel)
:1243  708..803   96 B   polaris10_populate_all_memory_levels    (MemoryLevel)
:2115  108..1883 1776 B  polaris10_init_smc_table
:2396  1692..1695   4 B  polaris10_update_sclk_threshold
:140   112..115     4 B  polaris10_setup_graphics_level_structure
:164   1592..1593   2 B  polaris10_setup_graphics_level_structure
```

Y las seis son `VIVA` respecto a la copia de `:2118` (la herramienta decia `:2115`; corregido al anclar la llamada), porque estan en **funciones
distintas** y la herramienta **no afirma cobertura entre funciones**: es lo que
`213` documento como limitacion, y aqui se ve en el resultado real.

## El caso que lo fija

El self-test **no lo habria cazado**: los fixtures tenian una sola funcion, donde no hay
colision posible de nombres. Anadi el **caso 18**, con dos funciones que definen la misma
variable con offsets distintos:

```
static int g(...)  { uint32_t array = ... + offsetof(T, GraphicsLevel); ... 448 ... }
static int m(...)  { uint32_t array = ... + offsetof(T, MemoryLevel);   ... 96  ... }
```

que exige `236` y `708` respectivamente. Si el bug vuelve, el caso falla.

Es el mismo patron que el caso 12 de `uninit_copy`: **un fixture que solo contiene el
caso que ya sabes buscar no puede cazar un bug de ambito.**

## Lo que este bug habria costado si no lo hubiera visto

El valor falso era `236..683` para `MemoryLevel`, es decir: la invasion de `GraphicsLevel`
que `211` calcula. Y **`211` la calcula y la documenta**.

O sea: `211` tiene una invasion de 108 bytes, y la herramienta, con el bug de ambito, le
daba exactamente el rango que produce esa invasion. Si no llego a mirar `:1243` por
separado, la invasion de `211` y el rango de la herramienta se habrian reforzado
mutuamente como "dos pruebas independientes de lo mismo", y no lo eran: **las dos salian
del mismo error de ambito**.

Eso no lo puedo comprobar ya, porque el bug ya esta corregido y el rango correcto es
`708..803`, de 96 bytes, sin invasion. Pero la hipotesis es coherente con lo que se ve:
`211` dice "MemoryLevel se sale del array en 108 bytes", y con el ambito correcto la
escritura de `:1243` es de 96 bytes en `708`, que **cabe entero** en el array real
(`600..695` desplazado 108, o `708..803` sin desplazar).

## Clasificacion

- `TOOL_SCOPE_LEAK = PROVEN`: `array` y `array_size` resueltos una vez para el fichero
  entero, con dos valores distintos en el codigo real. Caso 18.
- `TOOL_WRONG_RANGE_BEFORE_FIX = PROVEN_DERIVED`: `:1243` daba `236..683` en vez de
  `708..803`. Numero plausible y falso.
- `TOOL_MAP_KEY_MISMATCH = PROVEN`: el mapa se indexaba por el inicio de la funcion y se
  consultaba por el indice. **El mapa se llenaba y nunca se consultaba**, y la
  herramienta devolvia cero sin decirlo.
- `TOOL_MULTIPLIER_ALIAS = PROVEN`: `SMU74_MAX_LEVELS_GRAPHICS` -> `SMU__NUM_SCLK_DPM_STATE`
  -> `8`, resuelto en cadena con tope de profundidad.
- `TOOL_PER_FUNCTION_COUNTERS = PROVEN`: los contadores de tamano son locales a la
  funcion, con el global como respaldo.
- `TOOL_FIXTURE_WITH_SINGLE_FUNCTION_CANNOT_CATCH_SCOPE = PROVEN` el metodo: un fixture
  con una sola funcion no puede cazar un bug de ambito. Es el segundo caso de esta clase
  en la sesion, despues del caso 12 de `uninit_copy`.
- `FINDING_104_INVASION_NEEDS_RECHECK = PROVEN_DERIVED`: `211` calcula una invasion de
  108 bytes de `MemoryLevel`, y con el ambito correcto la escritura es de 96 bytes y
  **cabe**. La invasion de `211` queda **sospechosa** y hay que revisarla.

## Lo que hay que hacer con esto

1. **Revisar `211`**: la invasion de `MemoryLevel` sobre `LinkLevel` puede venir de este
   mismo error de ambito mio, no del codigo. Es la accion inmediata.
2. Y la regla, que es la segunda vez que sale: **una comprobacion que depende de un
   contexto tiene que declarar el contexto**. En la herramienta, la funcion. En mis
   cuentas, la base de coordenadas. Sin eso, dos errores del mismo tipo se refuerzan
   mutuamente y parecen una confirmacion.


## Y que NO cae: `096` se sostiene

Conviene decirlo, porque `096` tambien afirmaba una invasion y podria haber salido mal
por la misma causa. **No.**

La invasion de `096` es de la **tabla de arbitraje**, que tiene dimension propia:

```
entries[8][4] de 12 B = 384 B
ultimo elemento legitimo: entries[7][3] en el byte 372
ultimo alcanzable con j=7:  entries[7][7] en el byte 420
exceso: 36 B
```

Es una tabla de 384 bytes con entradas de 12, **sin relacion con el hueco de 108 de la
tabla DPM**. La aritmetica no comparte ninguna base con la que se corrigio `211`.

Y el caso realista (`mclk_count <= 4`) sigue limpio: `j` nunca pasa de 3, las 32 entradas
caen dentro, cero fuera, cero alias.

Lo que **si** queda en pie de las tres invasiones de la sesion:

| documento | invasion | estado tras las correcciones |
|---|---|---|
| `211` | `GraphicsLevel` invade `MemoryACPILevel` y `MemoryLevel` | **REFUTED**: `GraphicsLevel` acaba en 683, `MemoryACPILevel` en 684 |
| `211` | `MemoryLevel` invade `LinkLevel` (108 B) | **REFUTED**: acaba en 803, `LinkLevel` en 804 |
| `096` | `entries[7][j>=4]` sale 36 B del objeto de 384 | **`PROVEN`**: tabla aparte, sin relacion con el hueco |

Y la leccion de por que las dos primeras estaban mal y la tercera no: **las tres
decian 108 bytes**, lo cual es la firma de un unico error de calculo repetido, no de
tres defectos coincidentes. `096` decia 36, que es un numero que no aparece en ningun
sitio del hueco, y por eso era el unico que podia ser real.

**Cuando tres hallazgos independientes dan el mismo numero, sospechar del calculo antes
que de lahardware.** Es la regla, y en esta sesion la he tener que aplicar tres veces
antes de que saliera el error real, que era la quinta aparicion del mismo.
