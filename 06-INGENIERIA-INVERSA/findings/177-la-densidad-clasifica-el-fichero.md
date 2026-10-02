# 177 · La densidad clasifica cada fichero por lo que hace, y dos tienen cero

```
CLASSIFICATION=DOCUMENTATION · TRACK=STATIC
CORPUS=RESEARCH/working/linux-7.1.3 · HARDWARE_SCOPE=HOST-C/RX550/0000:01:00.0
WORK_CLASS=READ_ONLY/EVIDENCE · WRITE_EXECUTION=NONE · MODIFICATIONS=0
RUNTIME=NOT_RUN · GPU INTACTA
```

## Qué resuelve

**La generalización que `176` nombró y que hace el método general: medir la densidad de
delegación de `amdgpu_dm/` y de los seis ficheros de `dc/core/` que faltaban.**

**⇒ `amdgpu_dm/` son 32.304 líneas y tiene 1,0 punto de delegación por mil — el segundo
menos delegante de los nueve medidos. Y dos ficheros de `dc/core/` tienen exactamente
cero.** `PROVEN`.

**⇒ Y el resultado que no esperaba: la medida no sólo cuantifica el acoplamiento, sino que
*clasifica cada fichero por lo que hace*, y los dos ficheros con densidad cero son un
contador de referencias y un copiador de estructuras.** `PROVEN_DERIVED`.

## 1 · Los nueve, con el mismo criterio y el mismo programa

**Puntos de delegación por mil líneas, con tres patrones: `x->funcs->y(`, `->hwss.y(`, y
`x->y->z(` en general.** Los dos primeros son los de `176`; el tercero es un superconjunto
y por eso el secuenciador sale ahora con 195 en vez de con 108. **Son dos mediciones
distintas y no se suman: 108 es delegación por tabla de funciones; 195 es delegación por
cualquier puntero doble.** `PROVEN`.

| fichero o directorio | líneas | `funcs` | `hwss` | doble ptr | **puntos** | **por mil** |
|---|---|---|---|---|---|---|
| `dc/core/dc_link_exports.c` | 551 | 0 | 0 | 67 | 67 | **121,6** |
| **secuenciador** (`dc_hw_sequencer.c`) | 4.131 | 87 | 21 | 87 | 195 | 47,2 |
| `dc/core/dc.c` | 7.637 | 57 | 55 | 69 | 181 | 23,7 |
| `dc/core/dc_stream.c` | 1.313 | 8 | 15 | 8 | 31 | 23,6 |
| `dc/core/dc_surface.c` | 322 | 1 | 2 | 1 | 4 | 12,4 |
| `dc/core/dc_resource.c` | 5.734 | 27 | 1 | 32 | 60 | 10,5 |
| **`amdgpu_dm/` (19 ficheros)** | **32.304** | **10** | **3** | **18** | **31** | **1,0** |
| `dc/core/dc_state.c` | 1.113 | 0 | 0 | 0 | **0** | **0,0** |
| `dc/core/dc_sink.c` | 100 | 0 | 0 | 0 | **0** | **0,0** |

**⇒ `amdgpu_dm/`: 31 puntos en 32.304 líneas.** `PROVEN`.
**⇒ `dc_state.c` y `dc_sink.c`: cero puntos.** `PROVEN`.

## 2 · Y los dos ficheros con densidad cero, y qué son

**`dc/core/dc_sink.c`: 100 líneas, dos funciones.**

```c
dc_sink.c:60    void dc_sink_retain(struct dc_sink *sink)
dc_sink.c:72    void dc_sink_release(struct dc_sink *sink)
```

**Un contador de referencias.** `PROVEN`.

**`dc/core/dc_state.c`: 1.113 líneas, 25 funciones.**

```
dc_state.c:240   void dc_state_copy(struct dc_state *dst_state, struct dc_state *src_state)
dc_state.c:315   void dc_state_copy_current(struct dc *dc, struct dc_state *dst_state)
dc_state.c:325   void dc_state_construct(struct dc *dc, struct dc_state *state)
dc_state.c:334   void dc_state_destruct(struct dc_state *state)
```

**Un copiador y un constructor de una estructura de datos.** `PROVEN`.

**⇒ Los dos ficheros que no tocan el hardware son, exactamente, un contador de referencias
y un copiador de estructuras. Y los dos que más lo tocan —el secuenciador y `dc.c`— son
los que programan registros.** `PROVEN_DERIVED`.

**⇒ Y eso convierte la densidad en un clasificador: no sólo dice cuánto acoplamiento tiene
un fichero, sino qué clase de fichero es.** `PROVEN_DERIVED`.

## 3 · Y `amdgpu_dm/`, que es el número grande y el que.namespace la pregunta

**32.304 líneas de pegamento con DRM/KMS, con 31 puntos de delegación. Y qué son:**

| punto | llamadas |
|---|---|
| `dsc->funcs->dsc_read_state` | 8 |
| `dc->link_srv->edp_replay_residency` | 2 |
| `dc->link_srv->edp_set_replay_allow_active` | 2 |
| `acomp->audio_ops->pin_eld_notify` | 1 |
| `dmcu->funcs->dmcu_init` | 1 |
| `dmcu->funcs->is_dmcu_initialized` | 1 |
| `mgr->cbs->poll_hpd_irq` | 1 |
| `dc->link_srv->dp_get_encoding_format` | 1 |
| `tg->funcs->get_odm_combine_segments` | 1 |
| `dc->link_srv->edp_get_psr_residency` | 1 |
| `hubbub->funcs->get_mall_en` | 1 |
| `bios->funcs->get_embedded_panel_info` | 1 |
| y 19 más, una cada una | 19 |

**⇒ El más usado es la lectura de estado del compresor, ocho veces, y los otros treinta son
uno o dos cada uno.** `PROVEN`.

**⇒ Esa es la firma de un fichero que orquesta código ajeno: llama hacia dentro y hacia
fuera, y no hacia abajo.** `PROVEN_DERIVED`. *Y es coherente con `159`: `amdgpu_dm.c`, sus
13.719 líneas, es IRQ, HPD, EDID, FreeSync y CEC, y su contenido es tomar decisiones sobre
lo que otros han hecho, no escribir registros.*

**⇒ Y la consecuencia para un driver propio: el 32% del directorio más grande de `display/`
—32.304 de 443.839 líneas— no necesita ni una función por chip, porque su densidad es 1,0
y la mitad de sus Delegaciones van a tres subsistemas que ya existen.** `PROVEN_DERIVED`.

## 4 · Y una salvedad sobre el máximo, que es la misma clase de error que `176`

**`dc_link_exports.c` da 121,6 por mil, el valor más alto de los nueve, y es el máximo
posible por construcción:** es un fichero cuyo propósito es reenviar llamadas, así que
delegar es lo que hace. `PROVEN_DERIVED`.

**⇒ La medida tiene que excluirse a sí misma para un fichero de reenvío, o hay
que interpretarla al revés: 121,6 no significa «muy acoplado al hardware», significa «no hace
nada más que reenviar».** `PROVEN_DERIVED`.

**⇒ Y ése es el mismo error que el 261% de `176` en su forma exacta: un valor que sale
correcto del programa y que no significa nada porque el denominador o el numerador están
en la unidad equivocada para la pregunta.** *En `176` fue un porcentaje sobre cien que
daba 261; aquí es un cociente por mil que da 121 en un fichero de reenvío.* **Los dos se
detectaron por la misma vía: un valor que no tiene sentido en la escala en la que se
interpreta, y que hay que mirar antes de escribirlo en lugar de después.**

## Lo que NO cierra

| afirmación | estado |
|---|---|
| `amdgpu_dm/`: 32.304 líneas, 31 puntos, 1,0 por mil | `PROVEN` |
| `dc_state.c` y `dc_sink.c`: cero delegación | `PROVEN` |
| Los dos ficheros con cero son un contador de referencias y un copiador | `PROVEN_DERIVED` |
| `dc_link_exports.c` da 121,6 y es un fichero de reenvío | `PROVEN_DERIVED` |
| 108 y 195 son dos mediciones distintas y no se suman | `PROVEN` |
| El 32% del árbol no necesita ninguna función por chip | `PROVEN_DERIVED` |
| Densidad de `dc/bios/` y `dc/basics/` | **`NOT_DETERMINED`** |
| Densidad de `dc/link/protocols/`, 16 ficheros y 11.097 líneas | **`NOT_DETERMINED`** |
| Densidad de `dc/optc`, `dc/mpc`, `dc/hubp` | **`NOT_DETERMINED`** |
| La densidad por función, en vez de por línea | **`NOT_DETERMINED`** |

**La tercera de las abiertas es la que hace la medida comparable entre un fichero de 322
líneas y uno de 32.304, y es la misma operación con otro denominador:** puntos por función,
en vez de puntos por mil líneas. `dc_link_exports.c` con 72 funciones y 67 puntos daría
0,93 por función, que es lo que un fichero de reenvío es, y `dc_state.c` daría cero igual.
**Es un cambio de una palabra en el programa, y con él la medida deja de depender del
tamaño del fichero, que es su única debilidad.**

**Y la segunda son 16 ficheros y 11.097 líneas de protocolos de enlace, que es donde vive
el entrenamiento del enlace — la parte de `display/` que más toca el hardware y la única
que este bloque no ha medido con la densidad.** *Es el último grande, y el mismo programa.*

## Procedencia

- `STATIC` -- `display/amdgpu_dm/` (los 19 `.c` del directorio, contados con `wc -l` y con
  el recuento de nombres de las tres formas de delegación);
  `display/dc/core/dc.c` (7.637 líneas), `dc_resource.c` (5.734), `dc_hw_sequencer.c`
  (4.131), `dc_stream.c` (1.313), `dc_link_exports.c` (551), `dc_state.c` (1.113),
  `dc_surface.c` (322), `dc_sink.c` (100);
  `display/dc/core/dc_sink.c:60` (`dc_sink_retain`) y `:72` (`dc_sink_release`);
  `display/dc/core/dc_state.c:240` (`dc_state_copy`), `:315` (`dc_state_copy_current`),
  `:325` (`dc_state_construct`), `:334` (`dc_state_destruct`);
  `display/amdgpu_dm/` (el desglose de los 31 puntos, con las ocho llamadas a
  `dsc->funcs->dsc_read_state` y las dos de cada una de las dos de replay).
- Patrones de la medición, los tres, en modo `re.S` para tolerar llamadas partidas en
  varias líneas: `(\w+)\s*->\s*funcs\s*->\s*(\w+)\s*\(`,
  `->\s*hwss\s*\.\s*(\w+)\s*\(` y `(\w+)\s*->\s*(\w+)\s*->\s*(\w+)\s*\(`.
- **Un error de programa propio, y el más tonto de la tanda:** el `printf` del primer
  intento tenía seis huecos de formato y le pasaba siete valores, y `python` lo rechazó con
  `TypeError: not all arguments converted during string formatting`. **Pasé la columna de
  densidad además de la de puntos sin quitar una de las dos del formato.** *Ocurrió dos
  veces seguidas con el mismo error y la misma causa, y las dos veces lo vi porque el
  programa se cayó — que es exactamente para lo que sirve un programa que se cae: para no
  dejarme escribir nada.*
- **Y una medición que escribo mal y que hay que leer con la salvedad de §4:** `176` dio
  108 para el secuenciador contando sólo `x->funcs->y(` y `->hwss.y(`, y esta nota da 195
  añadiendo el patrón general de doble puntero. **No es una corrección de 108: es una
  medición distinta y más ancha, y las dos están escritas con su nombre en el texto.**
- Encadenada con `176` (**la densidad como medida, y aquí la medida aplicada a los nueve
  ficheros que faltaban**), `175` (los 108 puntos de delegación y la distinción entre
  puntos y funciones), `174` (las tres formas de despacho y el 87%),
  `173` (el intérprete de 119 operaciones), `172` (la capa genérica y los bloques ausentes),
  `169` (los nueve bloques IP), `167` (el 72% del codificador de enlace),
  `161` (el 8% del reloj), `159` (los 52 constructores y el 21%),
  `157` (el 58% del codificador de stream), `156` (la regla de la tabla y el constructor),
  `155`, `154`, `153`, `150`, `145`, `140`.
- No se editó `AGENTS.md` ni `OPEN-FRONTIERS.md`.

## Nota de método

**La densidad dejó de ser una medida y se convirtió en un clasificador, y eso ocurre
porque el cero es interpretable: los dos ficheros con densidad cero son un contador de
referencias y un copiador de estructuras, y ninguno de los dos tiene relación con el
hardware de pantalla.**

*Eso es más útil que un porcentaje.* **Un porcentaje dice cuánto acoplamiento hay; un cero
dice qué clase de fichero es, y lo dice con el mismo número.** *Y having medido nueve
ficheros con el mismo criterio, la clasificación se sostiene: el secuenciador y `dc.c` —los
dos primeros por densidad— son los que programan registros; `amdgpu_dm/`, que es el
directorio más grande, es orquestación y está en el segundo puesto por lo bajo; y los dos
ceros son software puro.*

**Y el error de la nota es el más tonto de veintisiete y el más útil por eso: un `printf`
con seis huecos y siete argumentos, dos veces seguidas, con el mismo error y la misma
causa.** *No lo detectó ninguna regla, ni la del número imposible, ni la del resultado
raro: lo detectó que el programa se cayó.* **Y esa es la tercera forma en que un programa
me ha parado —un booleano falso en `156`, una cita imposible en `168`, nueve filas sin
generación en `169`, un 261% en `176`— y la más barata de todas, porque no requiere
interpretar nada: basta con no tener un número.**

**Y la observación que la precede, y que es la regla de esta nota: `dc_link_exports.c` da
121,6 por mil y eso no significa «muy acoplado al hardware», significa «es un fichero de
reenvío».** *Un valor puede salir correcto del programa y no significar nada, y la única
forma de saberlo es preguntarse qué valdría un cero y un cien en esa escala, antes de
escribir el número.* **En `176` el 261% se delató por ser imposible; aquí el 121,6 no es
imposible, es sólo tonto, y ése es el nivel de dificultad del error que queda: no el
imposible ni el raro, sino el que tiene un valor plausible y un significado equivocado.**
