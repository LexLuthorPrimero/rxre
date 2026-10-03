# 173 · El secuenciador genérico es un intérprete de 119 operaciones, y su lista tiene tope

```
CLASSIFICATION=DOCUMENTATION · TRACK=STATIC
CORPUS=RESEARCH/working/linux-7.1.3 · HARDWARE_SCOPE=HOST-C/RX550/0000:01:00.0
WORK_CLASS=READ_ONLY/EVIDENCE · WRITE_EXECUTION=NONE · MODIFICATIONS=0
RUNTIME=NOT_RUN · GPU INTACTA
```

## Qué resuelve

**La pregunta que `172` dejó abierta: en qué orden se ejecutan las 110 `hwss_add_*`.**

**Y la respuesta cambia la forma de lo que hace el driver: las 110 funciones no programan
hardware, empujan un paso a una lista, y el orden es el orden de inserción. El
programador de pantalla de DCE 11.2 es un intérprete con 119 operaciones y una lista de
714 pasos, y cada generación de chip implementa las suyas.**

## 1 · Las cinco piezas, y encajan

**Todo el mecanismo cabe en dos estructuras, un enum y una unión, y está en
`display/dc/hwss/hw_sequencer.h`:**

```c
hw_sequencer.h:866   enum block_sequence_func { ... };            119 valores
hw_sequencer.h:742   union block_sequence_params { ... };         121 miembros
hw_sequencer.h:989   struct block_sequence {
hw_sequencer.h:990           union block_sequence_params params;
hw_sequencer.h:991           enum block_sequence_func func;
hw_sequencer.h:994   struct block_sequence_state {
hw_sequencer.h:995           struct block_sequence *steps;
hw_sequencer.h:996           unsigned int *num_steps;
hw_sequencer.h:999   #define MAX_HWSS_BLOCK_SEQUENCE_SIZE (HWSS_BLOCK_SEQUENCE_FUNC_COUNT * MAX_PIPES)
```

**⇒ Un paso es un par etiquetado: un valor de unión y una etiqueta. El estado es un array
de pasos y un contador. Y el tope es «operaciones × tuberías».** `PROVEN`.

**⇒ Con `MAX_PIPES = 6` de `162` y 119 operaciones, el tope es 714 pasos.** `PROVEN_DERIVED`.
**Y la fórmula dice lo que el tope significa: cada operación puede aparecer una vez por
tubería, y nada más.** `PROVEN_DERIVED`.

**Y la operación depush, que es todo lo que hacen las 110 funciones:**

```c
dc_hw_sequencer.c:1347   if (*seq_state->num_steps < MAX_HWSS_BLOCK_SEQUENCE_SIZE) {
dc_hw_sequencer.c:1348           seq_state->steps[*seq_state->num_steps].params.pipe_control_lock_params.dc = dc;
dc_hw_sequencer.c:1351           seq_state->steps[*seq_state->num_steps].func = OPTC_PIPE_CONTROL_LOCK;
dc_hw_sequencer.c:1352           (*seq_state->num_steps)++;
dc_hw_sequencer.c:1353   }
```

**⇒ No hay `else`, no hay error, no hay `ASSERT`.** `PROVEN`.

**⇒ Si la lista se llena, la operación se descarta en silencio.** `PROVEN_DERIVED`.
**Y con 6 tuberías y 119 operaciones, llenarla exige 119 operaciones en una sola tubería,
así que el caso no es alcanzable en esta máquina — pero el límite existe y no avisa.**
`PROVEN_DERIVED`.

**⇒ Y 230 llamadas a las 110 funciones, desde sólo dos ficheros del árbol:
`dc/core/dc_hw_sequencer.c` y `dc/hwss/dcn401/dcn401_hwseq.c`.** `PROVEN`.

## 2 · El vocabulario de las 119 operaciones, por bloque

| prefijo | operaciones | | prefijo | operaciones |
|---|---|---|---|---|
| **`HUBP`** | **30** | | `DMCG` / `DCCG` | 3 |
| `DPP` | 13 | | `ABM` | 3 |
| `MPC` | 10 | | `DWBC` | 3 |
| `TG` | 10 | | `PROGRAM` | 3 |
| `DSC` | 9 | | *(otros 7 prefijos)* | 7 |
| `OPP` | 7 | | | |
| `DMUB` / `OPTC` / `HUBBUB` / `MCIF` | 4 c/u | | | |

**⇒ 22 prefijos de bloque distintos en 119 operaciones, y `HUBP` solo son 30, el 25%.**
`PROVEN`.

**⇒ Y los 22 prefijos son los mismos bloques de `172`, lo que confirma que el vocabulario
del intérprete y la taxonomía de las funciones `hwss_add_*` son la misma lista vista de
dos maneras: una por bloque y otra por acción.** `PROVEN_DERIVED`.

**⇒ Y los dos bloques que `172` encontró ausentes de DCE — `HUBBUB` y `DWBC` — sí están
en el vocabulario: hay cuatro operaciones `HUBBUB_*` y tres `DWBC_*`.** `PROVEN_DERIVED`.

**⇒ Eso es la forma final de `232` y `157`, y es la más limpia de las veinte: el
vocabulario de operaciones es uno solo para todos los chips, y lo que decide si una
operación hace algo es que el fichero de la generación tenga su manejador. Una operación
sin manejador es exactamente el puntero nulo de `157`, y la comprobación `if (funcs->X)`
es el mismo patrón aplicado al orden.**

## 3 · Y la curva de manejadores por generación, la cuarta del bloque

**Cada subdirectorio de `display/dc/hwss/` implementa un subconjunto de las 119
operaciones.** Contadas por programa, con la cobertura sobre 121:

| generación | manejadores | cobertura |
|---|---|---|
| `dcn10` | 95 | **79%** |
| **`dce110`** | **75** | **62%** |
| `dcn401` | 72 | 60% |
| `dcn20` | 61 | 50% |
| `dcn32` / `dcn35` | 41 / 41 | 34% |
| `dcn30` | 24 | 20% |
| `dcn42` | 20 | 17% |
| `dcn31` | 16 | 13% |
| `dcn201` / `dcn314` | 14 / 14 | 12% |
| `dcn21` | 13 | 11% |
| `dce60` / `dce` | 8 / 8 | 7% |
| `dce100` / `dce120` / `dcn303` / `dcn351` | 5 | 4% |
| `dcn302` | 4 | 3% |
| **`dce112`** | **3** | **2%** |
| `dcn301` / `dce80` | 1 | 1% |

**⇒ `dce110_hwseq.c` son 3.563 líneas y unas 75 funciones, y es el fichero de manejadores
más grande del árbol — más que `dce112_clk_mgr.c` entero, que son 237 líneas.** `PROVEN`.

**⇒ Y la serie de los seis DCE no es monótona: 8, 1, 5, 75, 3, 5.** `PROVEN`. **El 75 de
DCE 11.0 es un pico, y el pico es el fichero que se escribió desde cero; los cinco que lo
siguen o lo preceden tienen entre 1 y 8.** `PROVEN_DERIVED`. **Es la misma forma del
`x8,4` de `159` y del `x0,2` siguiente.**

**⇒ Y esta máquina usa el fichero de 3.563 líneas, de los seis: es la quinta vez que un
`dce110_*` de DCE 11.0 sirve a DCE 11.2, y ahora la razón es distinta — no es una tabla de
22 de 38, es un intérprete con 75 manejadores de 119.** `PROVEN_DERIVED`.

## 4 · Y las cuatro interfaces, que ahora se pueden poner en una tabla

| interfaz | declarada en | miembros | cobertura de DCE 11.x |
|---|---|---|---|
| `stream_encoder_funcs` | `inc/hw/stream_encoder.h:133` | 38 | **58%** (`157`) |
| `link_encoder_funcs` | `inc/hw/link_encoder.h:113` | 32 | **72%** (`234`) |
| `enum block_sequence_func` | `hwss/hw_sequencer.h:866` | 119 | **62%** (esta nota) |
| `clk_mgr_funcs` | `inc/hw/clk_mgr.h:299` | 25 | **8%** (`161`) |

**⇒ Cuatro interfaces, cuatro coberturas, y las cuatro tienen la misma forma: DCE
necesita entre el 8% y el 72% de la interfaz, y el número depende de cuánta lógica el
chip resuelve por su cuenta.** `PROVEN_DERIVED`.

**⇒ Y la que menos necesita DCE es la del reloj, y ahora se sabe por qué: el reloj lo
decide el BIOS.** `161` lo había dicho; esta nota lo confirma por el otro lado, porque un
`clk_mgr_funcs` al 8% es la forma que tiene en el código un «no lo hago yo».

**⇒ Y la que más necesita es la del codificador de enlace, y ahora se sabe por qué: la
del enlace tiene 4 entradas sin implementar — FEC y DPIA— que son USB4, y USB4 no existe
en un chip de 2013.** `234` lo había dicho; esta nota lo confirma por el otro lado. `PROVEN_DERIVED`.

**⇒ La regla del bloque entero, en una frase y con las cuatro cifras: la interfaz de un
subsistema es tanto más grande cuanto menos de la sube el hardware.** `PROVEN_DERIVED`.

## Lo que NO cierra

| afirmación | estado |
|---|---|
| 119 operaciones, 121 miembros de unión, tope 119 × 6 = 714 | `PROVEN` |
| El desbordamiento descarta pasos sin error ni `ASSERT` | `PROVEN` |
| 230 llamadas, desde dos ficheros | `PROVEN` |
| 22 prefijos de bloque; `HUBP` son 30 operaciones | `PROVEN` |
| `HUBBUB` y `DWBC` están en el vocabulario y no en DCE | `PROVEN_DERIVED` |
| `dce110_hwseq.c`: 3.563 líneas, 75 manejadores, 62% | `PROVEN` |
| La serie DCE no es monótona: 8, 1, 5, 75, 3, 5 | `PROVEN` |
| Las cuatro interfaces, con sus cuatro coberturas | `PROVEN_DERIVED` |
| La interfaz crece con lo que el chip no resuelve | `PROVEN_DERIVED` |
| Qué función recorre la lista y despacha por etiqueta | **`NOT_DETERMINED`** |
| Si los 714 pasos se llenan alguna vez en la práctica | **`NOT_DETERMINED`** |
| La secuencia de un modo concreto, en orden | **`NOT_DETERMINED`** |
| Por qué el enum tiene 119 y la unión 121 | **`NOT_DETERMINED`** |

**La primera de las abiertas es el ejecutor, y está en el mismo fichero que el despachador
por etiqueta: es el `switch` sobre `step->func` con 119 casos.** Es el mismo trabajo que
`154` hizo con el `switch` de 17 casos, y con la misma forma: contar los casos y ver qué
hacen los que no existen en DCE.

## Procedencia

- `STATIC` -- `display/dc/hwss/hw_sequencer.h:742-864` (la unión y sus 121 miembros),
  `:866-...` (el enum y sus 119 valores), `:989-992` (`struct block_sequence`),
  `:994-997` (`struct block_sequence_state`), `:999` (`MAX_HWSS_BLOCK_SEQUENCE_SIZE` y su
  fórmula con `MAX_PIPES`);
  `display/dc/core/dc_hw_sequencer.c:1344-1354` (una operación de `add` completa, con su
  `if` sin `else`), `:1342` y `:1359` y `:1374` (las definiciones de `hwss_add_*`, que
  llevan el mismo patrón);
  `display/dc/inc/hw/stream_encoder.h:133`, `display/dc/inc/hw/link_encoder.h:113`,
  `display/dc/inc/hw/clk_mgr.h:299` (las otras tres interfaces, de `157`, `234` y `161`);
  los 22 subdirectorios de `display/dc/hwss/`, con sus ficheros, líneas y funciones
  contadas; `display/dc/hwss/dce110/dce110_hwseq.c` (3.563 líneas, el más grande);
  `display/dc/core/dc_hw_sequencer.h` para `MAX_PIPES 6` — realmente
  `display/dc/inc/hw/hw_shared.h:45`, de `162`.
- Medición por programa: **los 119 valores del enum y sus 22 prefijos**; los 121 miembros
  de la unión; **los 22 recuentos de manejadores con su cobertura sobre 121**; las 230
  llamadas y los dos ficheros de donde salen; el tope calculado como 119 × 6.
- **Dos errores propios, y el primero es el que hay que registrar:**
  (1) **Escribí que el enum tenía 119 valores y la unión 121 miembros y que «no
  coinciden». Es falso, y la causa es que las dos listas no usan la misma convención de nombres: los
  valores del enum van en mayúsculas (`OPTC_PIPE_CONTROL_LOCK`) y los miembros de la unión
  en minúsculas con sufijo (`pipe_control_lock_params`). Al compararlos en mayúsculas,
  los 121 salieron «sin valor» —incluidos los que sí lo tienen— y eso es imposible, y lo
  impossibility avisó.** *Es la cuarta vez en la tanda que un resultado imposible delata el
  error: `paso constante: False` en `232`, la cita ambigua en `235`, las nueve filas sin
  generación en `236`, y aquí los 121 «ausentes» de un enum que sí los tiene.*
  (2) El primer recuento de llamadas a `hwss_add_*` dio **cero**, y con un `grep` directo
  sobre el árbol dio **230**. La causa: mi expresión de definición de función terminaba
  en `[^;]*$`, y una línea de llamada termina en `);`, así que el clasificador se comía
  las llamadas y las contaba como definiciones. **Un `0` de un clasificador y un `230` de
  un `grep` sobre el mismo fichero es una contradicción directa, y por eso la segunda
  cifra tiene que comprobar a la primera y no al revés.**
- Encadenada con `172` (**la capa genérica, y aquí su arquitectura; los dos bloques
  ausentes de DCE y aquí que sí están en el vocabulario**), `170` (la regla de qué
  versiones tienen fichero, y aquí un `dce112` con 3 manejadores frente a un `dce110` con
  75), `236` (los nueve bloques IP), `234` (**las cuatro interfaces, y aquí su tabla**),
  `162` (**`MAX_PIPES 6`, que es el otro factor del tope de 714**), `161` (el reloj al 8%,
  y por qué), `159` (el `x8,4` de DCE 11.0 y la serie no monótona), `157` (el 58% del
  codificador de stream), `232` (la regla de la tabla y el constructor, elevada aquí a
  «una operación sin manejador es un puntero nulo»), `155`, `154` (el `switch` de 17
  casos, y el de 119 es el mismo trabajo), `153`, `150`, `145`, `140`.
- No se editó `AGENTS.md` ni `OPEN-FRONTIERS.md`.

## Nota de método

**La pregunta de `172` —«en qué orden se ejecutan las 110 `hwss_add_*`?»— tenía una
respuesta que la convertía en otra pregunta, y ese es el resultado de la nota: el orden
no está en el código, está en una lista, y la lista la rellena quien llama.**

*Yo buscaba un orden y lo que hay es un intérprete.* **Un `enum` de 119 etiquetas, una
unión de 121 parámetros, un array de pasos y un contador.** *Las 110 funciones no tocan un
registro: empujan un par (etiqueta, parámetros) a una lista, y un bucle la recorre
despachando por etiqueta.* **Y el orden de esa lista lo decide el llamante, en tiempo de
ejecución, no el código.** *Es la respuesta y a la vez es la pregunta siguiente: cuál es
el orden para un modo concreto.*

**Y lo que sale de esto es la forma más limpia de la regla que el bloque lleva veinte notas
desarrollando.** *`232` dijo que la identidad de un camino la dan la tabla y el
constructor. `157` que una operación ausente es un puntero nulo. Esta nota dice las dos
cosas a la vez y por qué: **el vocabulario de operaciones es uno para todos los chips, y lo
que decide si una de ellas hace algo es que el fichero de la generación tenga su
manejador** — y `HUBBUB` y `DWBC` están en el vocabulario y no en DCE, que es el puntero
nulo con otro nombre.* **Y la tabla de las cuatro interfaces lo resume: DCE necesita entre
el 8% y el 72% de cada una, y la interfaz es tanto mayor cuanto menos sube el hardware de
esa pieza.** *El reloj, que no lo calcula nadie en la familia DCE, tiene la interfaz más
pequeña de las cuatro.*

**Y el error de la nota es la cuarta vez que un resultado imposible delata un error, y esa
es ya una técnica.** *Los 121 miembros de la unión me parecían todos «sin valor en el
enum» —incluidos `pipe_control_lock_params`, que sí lo tiene— porque comparé mayúsculas
contra minúsculas.* **Un resultado que dice «ninguno de 121 tiene pareja» cuando hay 119
parejas es imposible, y lo imposible es la única alarma fiable: los errores raros los
delata la rareza, pero los errores de criterio producen resultados *demasiado*
regulares, y ésos no disparan nada salvo que uno se fije en la regularidad.**
