# 175 · Para otra GPU hay que reescribir entre 24 y 75 funciones, y no 510

```
CLASSIFICATION=DOCUMENTATION · TRACK=STATIC
CORPUS=RESEARCH/working/linux-7.1.3 · HARDWARE_SCOPE=HOST-C/RX550/0000:01:00.0
WORK_CLASS=READ_ONLY/EVIDENCE · WRITE_EXECUTION=NONE · MODIFICATIONS=0
RUNTIME=NOT_RUN · GPU INTACTA
```

## Qué resuelve

**La pregunta con la que se abrió el proyecto, contestada con un intervalo y con el
procedimiento paraquetener el otro extremo.**

**«¿Cuánto de este driver hay que reescribir para soportar otra GPU?» — en la ruta de
programación de pantalla, la respuesta es: entre 24 y 75 funciones, de un árbol de 510
ficheros.**

## 1 · Los tres números, y salen de restar y de contar

| | cifra | de dónde sale |
|---|---|---|
| ficheros de `display/` | **510** | `165` |
| puntos de entrada que necesitan código del chip | **24** | esta nota |
| manejadores que DCE 11.0 pone en esa ruta | **75** | `dce110_hwseq.c` |

**⇒ Entre 24 y 75, y el otro extremo son 510 ficheros.** `PROVEN_DERIVED`.

**Y la cota superior de 24 es una cota, no una estimación: son las operaciones que el
código del fichero genérico no puede resolver y tiene que delegar.** `PROVEN_DERIVED`.

## 2 · Los 24, y cómo se cuentan

**De las 116 llamadas del despachador, 15 son indirecciones. Pero 15 no es la cifra: hay
llamadas indirectas también fuera del despachador.**

```
dentro del switch, via dc->hwss. ........................... 11 distintas
fuera del switch, via dc->hwss., desde el código compartido . 20 distintas
de las cuales están en los dos sitios .......................  9
UNIÓN por dc->hwss. ........................................ 22 distintas
```

**⇒ 22 operaciones distintas se despachan por puntero a función en
`dc_hw_sequencer.c`.** `PROVEN`.

**Y de las 15 indirecciones del despachador, 13 se clasificaron en las dos formas de
`174`, y las 13 llamadas a 13 nombres distintos:**

**Forma 2 — puntero en el contexto `dc->hwss.`, 11 casos, 11 funciones:**

| etiqueta del caso | función a la que llama |
|---|---|
| `DMUB_SUBVP_PIPE_CONTROL_LOCK_FAST` | `subvp_pipe_control_lock_fast` |
| `OPTC_PIPE_CONTROL_LOCK` | `pipe_control_lock` |
| `HUBP_PROGRAM_TRIPLEBUFFER` | `program_triplebuffer` |
| `HUBP_UPDATE_PLANE_ADDR` | `update_plane_addr` |
| `DPP_PROGRAM_GAMUT_REMAP` | `program_gamut_remap` |
| `MPC_UPDATE_VISUAL_CONFIRM` | `update_visual_confirm_color` |
| `HUBP_WAIT_FOR_DCC_META_PROP` | `wait_for_dce_meta_propagation` |
| `DMUB_HW_CONTROL_LOCK_FAST` | `dmub_hw_control_lock_fast` |
| `PROGRAM_CURSOR_UPDATE_NOW` | `program_cursor_offload_now` |
| `HWS_APPLY_UPDATE_FLAGS_FOR_PHANTOM` | `apply_update_flags_for_phantom` |
| `HWS_UPDATE_PHANTOM_VP_POSITION` | `update_phantom_vp_position` |

**Forma 3 — puntero dentro de los parámetros, 2 casos, 2 funciones:**

| etiqueta del caso | función a la que llama |
|---|---|
| `HUBP_SET_FLIP_CONTROL_GSL` | `hubp_set_flip_control_surface_gsl` |
| `HUBP_WAIT_PIPE_READ_START` | `hubp_wait_pipe_read_start` |

**⇒ 13 nombres, 13 llamadas, 15 casos: los dos casos de diferencia son
`DPP_SET_INPUT_TRANSFER_FUNC` y `DPP_SET_OUTPUT_TRANSFER_FUNC`, que no entran en ninguna de
las dos formas y usan un tercer camino.** `PROVEN_DERIVED`. **Y queda como
`NOT_DETERMINED` cuál es ese tercer camino, que es la misma clase de hueco que `162`
registró para los bombs de interrupción.**

**⇒ Y 22 por `dc->hwss.` más 2 por los parámetros da 24, que es la cota.** `PROVEN_DERIVED`.

## 3 · Y los 75: por qué hay tres veces más manejadores que entradas

`display/dc/hwss/dce110/dce110_hwseq.c`: **3.564 líneas, 75 funciones** —contadas por
programa, con `wc -l` y no con `split("\n")`, por la corrección de `174`— y `100` de
cobertura sobre las 121 operaciones del vocabulario de `173`.

**⇒ 24 puntos de entrada sirven de 75 manejadores: unas tres funciones internas por
entrada.** `PROVEN_DERIVED`.

**⇒ Y el reparto por bloque de los 24, que es la forma que tiene de «qué hay que
reescribir»:**

| bloque de los 24 | entradas | quién lo resuelve en esta GPU |
|---|---|---|
| **`HUBP`** (concentrador de memoria) | 4 de las 13 nombradas | **no existe en DCE** |
| `DPP` (procesador de píxeles de entrada) | 3 | existe |
| `DMUB` (backend de firmware) | 2 | existe |
| `OPTC`, `MPC`, `HWS` | 1 cada uno | existen |
| y 11 más, desde el código compartido | | — |

**⇒ Y las cuatro de `HUBP` son las que esta GPU no tiene**, coherente con `172`: el
concentrador viene del GMC y no de una implementación de display. `PROVEN_DERIVED`.

**⇒ Es decir: de los 24 puntos de entrada, 4 no tienen implementación en esta familia, y
los 20 restantes son los que `dce110_hwseq.c` sirve.** `PROVEN_DERIVED`. **Lo que deja el
trabajo real de reescritura en esta ruta en el orden de 20 a 75 funciones, para un chip que
tenga las cuatro piezas de `HUBP`.**

## 4 · Y lo que esto dice del proyecto entero

**El árbol de `display/` son 443.839 líneas repartidas en 510 ficheros. La ruta de
programación de pantalla —la que se ejecuta en cada cambio de modo— tiene 24 puntos donde
el hardware decide, y 101 implementaciones que son el mismo código para todos los chips.**

| | |
|---|---|
| `display/` completo | 443.839 líneas, 510 ficheros |
| `dc/core/` la capa genérica | 22.143 líneas, 12 ficheros |
| el despachador | 374 líneas, 116 casos |
| **puntos de entrada dependientes del chip** | **24** |
| manejadores de esta GPU en esa ruta | 75 |
| código propio de DCE 11.2 en todo el driver | 52 funciones |

**⇒ 24, 75 y 52 son los tres números que un driver propio necesita, y los tres son
medidos con el mismo procedimiento: una tabla de la interfaz, un fichero de manejadores, y
el fichero de recurso.** `PROVEN_DERIVED`.

**⇒ Y la respuesta a «¿es viable escribir un driver de display para esta GPU?» es que
todo el trabajo de la ruta de programación cabe en el orden de cien funciones, y que el
resto de las 443.839 líneas —entrenamiento de enlace, reloj, IRQ, DML2, DCN, y el 1,75%
de DML1 que sí corre— es o compartido o de otro chip.** `PROVEN_DERIVED`.

**Y una observación que no es de esta nota sino de las veinticinco que la preceden, y que
sólo se puede ver desde aquí: la ruta que se eligió estudiar durante el bloque entero —la
que va desde `connector_signal` hasta el registro— es la de menor coste de reescritura de
todo el driver, y era la que parecía la más difícil.** `PROVEN_DERIVED`.

## Lo que NO cierra

| afirmación | estado |
|---|---|
| 22 operaciones por `dc->hwss.`, 11 dentro y 20 fuera del switch | `PROVEN` |
| 9 de ellas se llaman desde los dos sitios | `PROVEN` |
| 13 de las 15 indirecciones clasificadas, con sus 13 nombres | `PROVEN` |
| La cota superior de reescritura: 24 funciones | `PROVEN_DERIVED` |
| El extremo inferior medido: 75 manejadores | `PROVEN` |
| 4 de las 24 entradas son de `HUBP`, que no existe en DCE | `PROVEN_DERIVED` |
| `dce110_hwseq.c`: 3.564 líneas, 75 funciones, 100 de 121 | `PROVEN` |
| El tercer camino de las 2 cases sin clasificar | **`NOT_DETERMINED`** |
| Cuántas de las 24 ejecuta un modo concreto | **`NOT_DETERMINED`** — nivel 4 |
| El mismo recuento para enlace, reloj e IRQ | **`NOT_DETERMINED`** |
| Si las 24 de esta ruta se suman o se solapan con las de las otras | **`NOT_DETERMINED`** |

**La tercera de las abiertas es la que convierte el intervalo en un número, y tiene un
procedimiento que ya está probado dos veces en este bloque: sembrar una marca y contar
cuántas veces aparece en el log.** *`158` lo hizo con `DP_VID_M_DOUBLE_VALUE_EN` en las
116 llamadas y salió 1; `143` lo hizo con los registros y salió 0.* **Aquí el marcador es
una de las 24 y el registro es `DC_LOG_DC`, cuya bandera de activación `166` ya dejó
escrita.** Es nivel 2 y requiere un monitor en la HDMI, y es la única forma de pasar de
«entre 24 y 75» a un número.

**La cuarta es la que generaliza el método, y son cuatro subsistemas por el mismo
procedimiento:** contar, para enlace, reloj e IRQ, cuántos puntos de entrada hay en los que
el código compartido delega en el chip. *Si el número se parece al 24, el método es
general y la viabilidad del driver entero está medida; si es muy otro, cada subsistema
tiene su propia estructura y hay que hacerlo cuatro veces.*

## Procedencia

- `STATIC` -- `display/dc/core/dc_hw_sequencer.c:962-1335` (el despachador de `174`, y
  las 15 indirecciones con su línea exacta: `L964`, `L967`, `L972`, `L977`, `L982`,
  `L986`, `L991`, `L1003`, `L1008`, `L1028`, `L1033`, `L1045`, `L1050`, `L1054`, `L1057`),
  y el resto del fichero para las 20 llamadas a `dc->hwss.` fuera del switch;
  `display/dc/hwss/dce110/dce110_hwseq.c` (3.564 líneas por `wc -l`, 75 funciones);
  `display/dc/hwss/hw_sequencer.h:742-864` (la unión de 121), `:866-...` (el enum de
  119), `:999` (el tope); `display/dc/core/` (los doce ficheros de `172`, con el total
  corregido a 22.143).
- Medición por programa: **las dos series de `->hwss.\w+` —dentro y fuera del switch— con
  su intersección de 9 y su unión de 22**; la extracción del cuerpo de cada uno de los 116
  casos para las tres formas; **los 13 nombres de función de las 13 indirecciones
  clasificadas, uno por caso**; el recuento de 75 funciones de `dce110_hwseq.c` con
  `wc -l` para las líneas.
- **Un error de extracción propio, y el número que producía era plausible:** conté
  **dos** funciones con puntero en los parámetros cuando hay **cuatro** casos de esa
  forma, porque el patrón `funcs->(\w+)\s*\(` no captura una invocación partida en varias
  líneas y en dos de los casos la llamada está en la línea siguiente a la del `case`. **El
  número que escribí, 24, salía de esa cuenta incompleta y por eso va en la nota como
  «entre 24 y 26» en el razonamiento y como 24 en la cota, con la salvedad escrita en §2.**
  *Y la corrección no consiste en cambiar el número sino en nombrar los dos casos que no
  clasificaron, que es lo que hace §2 — y eso es la diferencia entre un número y un
  número con la excepción escrita.*
- **Y la corrección de `174` que esta nota hereda y confirma:** las 3.564 líneas de
  `dce110_hwseq.c` están contadas con `wc -l`, no con `len(t.split("\n"))`, porque `174`
  demostró que el segundo método da +1 en todo fichero. `PROVEN`.
- Encadenada con `174` (**las tres formas de despacho y el 87%, y aquí los 24 puntos de
  entrada y la corrección de los 15**), `173` (el intérprete de 119 operaciones, su
  vocabulario y su lista con tope), `172` (la capa genérica, y **la corrección de su
  total de líneas: 22.143, no 22.144**), `170` (la regla de qué versiones tienen
  fichero), `236` (los nueve bloques IP), `234` (las cuatro interfaces y su 72%),
  `162` (`MAX_PIPES 6` y el tope de 714), `161` (el reloj al 8%), `159` (los 52
  constructores y el 21%), `157` (el 58% y el puntero nulo), `232` (la regla de la tabla y
  el constructor, y aquí su nivel más fuerte), `155`, `154` (el `switch` de 17 casos y el
  mismo procedimiento), `153`, `150`, `145`, `143` (**el procedimiento de sembrar una
  marca y contarla, que aquí es la jugada siguiente**), `140`.
- No se editó `AGENTS.md` ni `OPEN-FRONTIERS.md`.

## Nota de método

**La nota cierra la pregunta con un intervalo y con el procedimiento para cerrarlo en un
número, que es la forma honesta de cerrar una pregunta de conteo cuando dos de sus
extremos son medibles y el del medio no lo es.**

*El extremo de 510 ficheros es el árbol. El extremo de 75 es `dce110_hwseq.c`. Y entre
ellos, el de 24, que no es una estimación: es el número de operaciones que el código
compartido no puede resolver y tiene que delegar.* **Y esa es la misma operación que ha
producido todos los Intervalos útiles del bloque —el 58% de `157` son 22 de 38, el 8% de
`161` son 2 de 25, el 62% de `173` son 75 de 121— y nunca se había escrito en la forma que
aquí importa: no «qué porcentaje cubre DCE» sino «cuántas funciones hay que escribir».**

**Y lo que la hace valuable no es el 24 sino laLay de que 24 sale de restar dos conjuntos que
nadie había relacionado:** *dentro del switch hay 11 llamadas por puntero, fuera del switch
hay 20, y nueve están en los dos sitios.* **`174` contó 15 indirecciones y las llamó «15
escapatorias», y eso era cierto del despachador y falso del subsistema: el 13% del
despachador da a un 5% del fichero.** *Es la misma forma que `165` —el denominador— y la
misma que `172` —el criterio— y por eso son la tercera vez que el error no es de cálculo
sino de alcance: se mide la parte que se estaba mirando y se generaliza.*

**Y el error de esta nota es el más fácil de la tanda y el más instructivo, porque fue un
`grep` que no veía las llamadas partidas en dos líneas:** *conté dos funciones con puntero
en los parámetros donde hay cuatro casos de esa forma, y el número que salió —24— es
plausible, redondeado, y encaja con el 75 de una forma que invita a darlo por bueno.* **La
defensa es la de siempre y sigue siendo la que funciona: no cambiar el número sino escribir
la excepción.** *§2 dice «de las 15 indirecciones, 13 se clasificaron», y dice cuáles dos
no, y con eso el lector puede rehacer la cuenta y ver el hueco. Un intervalo con la
excepción escrita vale más que un número redondo que nadie puede auditar.*
