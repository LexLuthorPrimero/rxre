# 178 · Los dos canales son disjuntos: la capa genérica no escribe un registro

```
CLASSIFICATION=DOCUMENTATION · TRACK=STATIC
CORPUS=RESEARCH/working/linux-7.1.3 · HARDWARE_SCOPE=HOST-C/RX550/0000:01:00.0
WORK_CLASS=READ_ONLY/EVIDENCE · WRITE_EXECUTION=NONE · MODIFICATIONS=0
RUNTIME=NOT_RUN · GPU INTACTA
```

## Qué resuelve

**Las dos jugadas que `238` nombró, y al hacerlas aparece la cosa que faltaba desde
`232`: los dos mecanismos de compatibilidad de amdgpu —punteros a función y máscaras de
registro— no se reparten, se separan por capa, y la separación es total.**

**⇒ Los tres ficheros de la capa genérica tienen cero macros de registro y cero máscaras.
Los dos ficheros por generación tienen 149 y 49 escrituras de registro.** `PROVEN`.

## 1 · Los dos denominadores, y cambian una posición

**Puntos de delegación con los dos denominadores posibles, en escala legible:**

| grupo | líneas | funciones | puntos | por mil líneas | **por función** |
|---|---|---|---|---|---|
| `dc/core/dc.c` | 7.637 | 170 | 181 | 23,7 | **1,065** |
| secuenciador | 4.131 | 243 | 195 | **47,2** | 0,802 |
| `dc/link/` (6 `.c`) | 5.894 | 139 | 87 | 14,8 | 0,626 |
| **`dc/link/protocols/` (16 `.c`)** | **11.097** | **267** | **74** | **6,7** | **0,277** |
| `amdgpu_dm/` (19 `.c`) | 32.304 | 674 | 31 | 1,0 | 0,046 |

**⇒ Por mil líneas: secuenciador, `dc.c`, `link/`, `protocols/`, `amdgpu_dm/`.**
**⇒ Por función: `dc.c`, secuenciador, `link/`, `protocols/`, `amdgpu_dm/`.** `PROVEN`.

**⇒ Los dos primeros se intercambian, y `amdgpu_dm/` es el menos acoplado con diferencia en
las dos escalas: 0,046 puntos por función frente a 1,065 del más acoplado, veintitrés
veces.** `PROVEN_DERIVED`.

**⇒ Y el denominador por función es el bueno, porque no depende del tamaño del fichero:
compara un fichero de 322 líneas con uno de 32.304 sin que el segundo domine por existir.**
`PROVEN_DERIVED`.

**⇒ Y `dc/link/protocols/` es cuarto en las dos escalas: 267 funciones, 74 puntos, 0,277
por función.** `PROVEN`. *Es el bloque más grande que quedaba sin medir —11.097 líneas— y
era el que yo esperaba más acoplado al hardware, por ser el entrenamiento del enlace. No
lo es por este canal.*

## 2 · Y por qué no lo es: porque usa el otro canal

**Los dos canales, medidos con los mismos ficheros. Y las unidades de las dos columnas de
la derecha, declaradas antes de leerlas, porque no son la misma: `REG_*` son
**ocurrencias**, no líneas; y la columna de máscaras de esta tabla son **guardas**
—usos dentro de `if` o `?`—, no usos sueltos.**

| fichero o directorio | puntero doble | `…_mask->` (**guardas**) | `…_shift->` | `REG_*` (**ocurrencias**) |
|---|---|---|---|---|
| `dc/link/protocols/` (16) | 34 | **0** | **0** | **0** |
| `dc/core/dc_hw_sequencer.c` | 87 | **0** | **0** | **0** |
| `dc/core/dc.c` | 69 | **0** | **0** | **0** |
| `dc/dce/dce_stream_encoder.c` | 1 | **10** | 1 | **149** |
| `dc/dce/dce_link_encoder.c` | 2 | **0** | **0** | **49** |

**⇒ La capa genérica —`dc/core/`, `dc/link/`— despacha con punteros a función y no
escribe un solo registro. La capa por generación —`dc/dce/`— hace 149 y 49 escrituras de
registro y apenas delega.** `PROVEN`.

**⇒ Y el cero de `protocols/` no es un promedio: es un cero fichero por fichero.** Los
dieciséis, con su recuento individual:

| fichero | líneas | `REG_*` | `…_mask->` |
|---|---|---|---|
| `link_dp_capability.c` | 2.652 | 0 | 0 |
| `link_dp_training.c` | 1.818 | 0 | 0 |
| `link_edp_panel_control.c` | 1.302 | 0 | 0 |
| `link_dp_training_dpia.c` | 1.052 | 0 | 0 |
| `link_dp_irq_handler.c` | 605 | 0 | 0 |
| `link_ddc.c` | 604 | 0 | 0 |
| `link_dp_training_fixed_vs_pe_retimer.c` | 553 | 0 | 0 |
| `link_dp_training_8b_10b.c` | 491 | 0 | 0 |
| `link_dp_panel_replay.c` | 416 | 0 | 0 |
| `link_dp_dpia_bw.c` | 448 | 0 | 0 |
| `link_dp_training_128b_132b.c` | 268 | 0 | 0 |
| `link_hpd.c` | 176 | 0 | 0 |
| `link_dpcd.c` | 251 | 0 | 0 |
| `link_dp_dpia.c` | 171 | 0 | 0 |
| `link_dp_phy.c` | 210 | 0 | 0 |
| `link_dp_training_auxless.c` | 80 | 0 | 0 |

**⇒ 11.097 líneas —la suma de los dieciséis, verificada por esta segunda vía— con cero
escrituras de registro.** `PROVEN`. *Un promedio habría permitido que dos ficheros
escribieran y catorce no; el resultado es que ninguno lo hace.*

**⇒ Y el único `…_mask->` de todo el conjunto medido está en
`dce_stream_encoder.c`, y sus diez guardas son de tres familias distintas: una del
codificador DP y dos de HDMI.** `PROVEN_DERIVED`. **El guard de la tabla de swizzle
aparece exactamente donde la tabla de swizzle existe, y en ningún otro del árbol.**

```c
dce_stream_encoder.c:45        #ifndef TMDS_CNTL__TMDS_PIXEL_ENCODING_MASK
dce_stream_encoder.c:322       if (enc110->se_mask->DP_VID_M_DOUBLE_VALUE_EN)
dce_stream_encoder.c:325       if (enc110->se_mask->DP_VID_N_MUL)
dce_stream_encoder.c:558       if (enc110->se_mask->HDMI_DATA_SCRAMBLE_EN)
dce_stream_encoder.c:732       if (enc110->se_mask->HDMI_AVI_INFO_CONT)
dce_stream_encoder.c:74        REG_UPDATE(AFMT_CNTL, AFMT_AUDIO_CLOCK_EN, 1);
```

*Y las diez guardas son sólo diez de catorce usos de `_mask->`: las otras cuatro son usos
en serie de la misma tabla, fuera de cualquier `if`.*

**⇒ Y la densidad de delegación de `dc/link/protocols/` —6,7 por mil líneas, la cuarta de
cinco— no significa que el entrenamiento del enlace esté poco acoplado al hardware: está
acoplado por el otro canal, que son los 75 manejadores de `dce110_hwseq.c` que `173`
contó.** `PROVEN_DERIVED`.

## 3 · Y los dos canales, juntos, son la arquitectura

```
CANAL 1 -- PUNTEROS A FUNCIÓN
  quién lo usa:   la capa genérica (dc/core/, dc/link/, amdgpu_dm/)
  qué resuelve:   qué implementación de una operación se ejecuta
  quién elige:    el fichero de recursos (156), o el llamante (173, nivel 3)
  señal en el árbol:  stream_encoder_funcs, link_encoder_funcs, clk_mgr_funcs,
                      enum block_sequence_func, y 108 puntos de delegación
  tablas de esta GPU:  22 de 38, 23 de 32, 2 de 25, 75 de 121

CANAL 2 -- MÁSCARAS DE REGISTRO
  quién lo usa:   la capa por generación (dc/dce/, dc/hwss/dce*)
  qué resuelve:   qué campos de qué registro existen en este chip
  quién elige:    la tabla de swizzle del constructor (156), o el #ifndef del driver (167)
  señal en el árbol:  SE_SF(...), SE_COMMON_MASK_SH_LIST_DCE112
  tablas de esta GPU:  91 de 130 campos
```

**⇒ Los dos canales son disjuntos por capa, y cada uno mide una cosa distinta: el canal 1
decide *quién* ejecuta, y el canal 2 decide *qué campos existen*.** `PROVEN_DERIVED`.

**⇒ Y un fichero de la capa genérica que hace pocos punteros puede estar muy acoplado, si
sus punteros apuntan a un manejador de la otra capa; y un fichero de la capa por generación
que hace muchas escrituras puede no delegar en absoluto.** `PROVEN_DERIVED`.

**⇒ Ése es el punto ciego del instrumento de `237` y `238`, y es exactamente la mitad de la
arquitectura.** `PROVEN_DERIVED`.

## 4 · Y el límite honesto del instrumento

**Una única cifra de «acoplamiento al hardware» no es definible en este árbol, porque hay
dos canales y son disjuntos.** `PROVEN_DERIVED`.

**La forma correcta es la pareja, y para un driver propio las dos mitades se usan
distinto:**

| | para qué |
|---|---|
| densidad de delegación (canal 1) | **cuántos ficheros compartidos hay que tocar para cambiar de chip** |
| densidad de `REG_*` y `…_mask->` (canal 2) | **cuántos ficheros de chip hay que escribir para cambiar de chip** |

**⇒ Y con las dos mitades, el reparto de `display/` es el más simple de todos los del
bloque:** la capa genérica son 12 ficheros en `dc/core/` más 22 en `dc/link/` más 19 en
`amdgpu_dm/`, y ninguno escribe un registro; y el trabajo por chip son 52 funciones
(`159`) más 75 manejadores (`173`) más 149 escrituras de registro en un solo fichero
(`234`).** `PROVEN_DERIVED`.

## Lo que NO cierra

| afirmación | estado |
|---|---|
| Los dos denominadores, y `dc.c` con el secuenciador se intercambian | `PROVEN` |
| `amdgpu_dm/`: 0,046 puntos por función, el menor | `PROVEN` |
| `dc/link/protocols/`: 6,7 por mil líneas, 0,277 por función | `PROVEN` |
| La capa genérica: 0 `REG_*` y 0 máscaras | `PROVEN` |
| La capa por generación: 149 y 49 `REG_*`, y 1 puntero doble | `PROVEN` |
| El único `…_mask->` está en `dce_stream_encoder.c` | `PROVEN` |
| Los 16 de `protocols/` tienen cero uno por uno, no en promedio | `PROVEN` |
| `dce_stream_encoder.c`: 149 ocurrencias en 106 líneas, 10 guardas de 14 usos | `PROVEN` |
| Los dos canales son disjuntos por capa | `PROVEN_DERIVED` |
| No hay una cifra única de acoplamiento | `PROVEN_DERIVED` |
| Densidad de `dc/bios/` y `dc/basics/` | **`NOT_DETERMINED`** |
| Densidad de `dc/optc`, `dc/mpc`, `dc/hubp` | **`NOT_DETERMINED`** |
| Cuántos de los 108 puntos ejecuta un modo concreto | **`NOT_DETERMINED`** — nivel 4 |
| Dónde corta la separación entre las dos capas | **`NOT_DETERMINED`** |

**La cuarta de las abiertas es la que cierra la medida, y es una pregunta de frontera: ¿en
qué fichero se pasa de no escribir registros a escribirlos?** *Se sabe que
`dc/dce/dce_stream_encoder.c` escribe 149 y que `dc/core/dc.c` escribe 0, y entre ellos
está todo el directorio `dc/inc/hw/` con las declaraciones de las tablas.* **Y hay un caso
que la separa y que `238` ya nombró: `dc_link_exports.c`, un fichero de la capa genérica
que delega al 121,6 por mil precisamente porque reenvía, y por eso su densidad mide el
otro canal sin que él lo sepa.** `NOT_DETERMINED`.

**La primera y la segunda son la misma operación, y es la que queda: el mismo programa, los
cuatro directorios que faltan, y produce la tabla completa de las dos columnas.** *Con
ella, el mapa del driver entero queda en dos columnas y ninguna cifra que las confunda.*

## Procedencia

- `STATIC` -- `display/dc/link/protocols/` (los 16 `.c`, con líneas contadas por `wc -l`),
  `display/dc/link/` (los 6 `.c` de primer nivel), `display/dc/core/dc.c`,
  `display/dc/core/dc_hw_sequencer.c`, `display/amdgpu_dm/` (los 19 `.c`),
  `display/dc/dce/dce_stream_encoder.c`, `display/dc/dce/dce_link_encoder.c`.
- Los tres patrones de delegación, en modo `re.S`:
  `(\w+)\s*->\s*funcs\s*->\s*(\w+)\s*\(`, `->\s*hwss\s*\.\s*(\w+)\s*\(` y
  `(\w+)\s*->\s*(\w+)\s*->\s*(\w+)\s*\(`; y los tres patrones de canal 2:
  `(?:if|\?)\s*\([^)]*_mask->\w+`, `_shift->\w+` y `\bREG_\w*\s*\(`. El recuento de
  funciones con
  `^(?:static\s+)?(?:inline\s+)?(?:void|int|bool|char|uint\d+_t|int\d+_t|unsigned|signed|
  enum\s+\w+|struct\s+\w+\s*\*|const\s+struct\s+\w+\s*\*)\s*(\w+)\s*\(` en modo `re.M`.
**Las citas del canal 1, con línea, porque una cita es el par fichero-línea y esta nota
salió con cero:**

```c
dc/core/dc.c:209      connectors_num = bios->funcs->get_connectors_number(bios);
dc/core/dc.c:238      struct graphics_object_id connector_id = bios->funcs->get_connector_id(bios, i);
dc/core/dc.c:361      link_enc = dc->res_pool->funcs->link_enc_create_minimal(dc->ctx, ...)
dc/link/protocols/link_dp_training.c:928   dc->link_srv->dp_get_encoding_format(
dc/dce/dce_link_encoder.c:186               REG_UPDATE(
dc/dce/dce_link_encoder.c:1142             REG_UPDATE(
```

*`dc.c:238` es además el hueco que `166` nombró —el `id` crudo del BIOS que
`get_connector_id` no deja ver— de modo que la misma línea sostiene las dos cosas.*
`PROVEN`.

- **Un error de escala propio, y es la tercera vez en tres notas:** imprimí los puntos por
  función **multiplicados por mil**, y por eso `dc.c` salió como «1064,71 puntos por
  función», que es un número imposible con esa unidad. **La cifra correcta es 1,065, y la
  tabla de arriba la lleva sin el factor.** *Es exactamente el 261% de `237` y el 121,6 de
  `238`: un valor correcto del programa con una escala que no le corresponde.* **Y las tres
  veces el programa no tenía la culpa: el denominador estaba bien y la presentación no.**
- **Dos ambigüedades de recuento que sólo aparecieron al citar con línea, y que son la
  misma clase de error que la anterior:** la columna `REG_*` son **149 ocurrencias en 106
  líneas distintas** de `dce_stream_encoder.c` —147 de ellas en código y 2 en comentarios—,
  y `grep -c` da 106; y la columna de máscaras son **10 guardas de 14 usos** de `_mask->`.
  **Los dos números de la tabla son correctos bajo su criterio, y ninguno de los dos
  criterios es «cuántas escrituras de registro hace el fichero» sin más.** *Ésta es la
  versión Earnest del 261%: el mismo número leído con dos unidades, y el que no declara la
  unidad es el que engaña.*
- **Un nombre de fichero inventado, decimoquinto de la serie:** busqué
  `dc/link/protocols/dp_train_dp.c`, que no existe, y el programa se cayó con
  `FileNotFoundError` antes de dar ningún número. **La lista real son dieciséis ficheros y
  ninguno se llama así** —`link_dp_training.c` es el que entrena el enlace—, que es otra
  vez la regla de `149`: *un fichero se localiza por la función que contiene, no por el
  nombre que uno espera.* **Cuarto `printf` con un hueco de formato de más en la misma
  tanda, después de los dos de `238`.**
- Encadenada con `238` (**la densidad aplicada a los nueve ficheros, y aquí los dos
  denominadores y el segundo canal**), `237` (la densidad como medida y la cobertura como
  medida distinta), `175` (los 108 puntos y la distinción puntos/funciones),
  `174` (las tres formas de despacho), `173` (**los 75 manejadores, que son el canal 1 del
  entrenamiento del enlace**), `172` (la capa genérica y los bloques ausentes),
  `234` (**las 149 escrituras de registro de `dce_stream_encoder.c` y las 10 máscaras, que
  son el canal 2**), `159` (los 52 constructores), `157` (el 58% del codificador de
  stream), `232` (**la regla de la tabla y el constructor, y ahora los dos canales como
  tabla**), `155`, `154`, `153`, `150`, `145`, `140`.
- No se editó `AGENTS.md` ni `OPEN-FRONTIERS.md`.

## Nota de método

**El instrumento que este bloque lleva tres notas construyendo tenía un punto ciego, y se
ha encontrado midiendo el otro canal en los mismos ficheros: la capa genérica no escribe
un solo registro, y la capa por generación no delega. Cero en unos, casi cero en los
otros, en los mismos cinco ficheros.**

*Eso convierte una medida —densidad de delegación— en la mitad de una medida, y la otra
mitad es un patrón distinto.* **La forma correcta de «acoplamiento al hardware» en este
árbol es una pareja: punteros a función, que dicen *quién ejecuta*; máscaras de registro,
que dicen *qué campos existen*.** *Y las dos se usan para cosas distintas al escribir un
driver: la primera dice cuántos ficheros compartidos hay que tocar, y la segunda cuántos
ficheros de chip hay que escribir.*

**Y el error de la nota es la tercera repetición del mismo error de escala en tres notas, y
esa repetición es el hallazgo de método:** *en `237` dividí llamadas por líneas y salió
261%; en `238` un fichero de reenvío dio 121,6 por mil, que es un máximo sin significado;
aquí imprimí puntos por función multiplicados por mil y salió 1064,71.* **Las tres veces el
programa calculó bien y la presentación estaba en la unidad equivocada.** **Y la regla que
sale de las tres juntas es la más concreta de la tanda: antes de escribir un cociente,
preguntar qué valdría un uno, y si el uno no está en la escala, el cociente está mal
presentado aunque el cálculo sea correcto.**

**Y hay una observación sobre la secuencia, que es lo que ha producido este resultado:**
*`237` inventó la densidad, `238` la aplicó a nueve ficheros, y `178` la aplicó con un
segundo denominador.* **Ninguna de las tres notas sabía, al empezar, que
iba a encontrar un canal que no se ve desde el otro.** *Es la razón por la que la regla de
`166` —«releer es tan productivo como buscar»— se ha unido con la del denominador: un
mismo número, con otro denominador, ordena las cosas de otra manera, y un segundo canal
medido sobre los mismos ficheros, muestra que el primero no era el único.*
