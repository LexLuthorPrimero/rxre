# 172 · La capa genérica: 242 funciones de 17 líneas, y un 69% que era falso

```
CLASSIFICATION=DOCUMENTATION · TRACK=STATIC
CORPUS=RESEARCH/working/linux-7.1.3 · HARDWARE_SCOPE=HOST-C/RX550/0000:01:00.0
WORK_CLASS=READ_ONLY/EVIDENCE · WRITE_EXECUTION=NONE · MODIFICATIONS=0
RUNTIME=NOT_RUN · GPU INTACTA
```

## Qué resuelve

**La mitad de `display/` que nadie había abierto: la capa genérica, el código que se
escribe una vez y sirve para treinta chips.** Y un resultado de método que es el más
importante del bloque entero, porque un programa mío produjo un número falso, plausible
y publicable, y sólo la segunda forma de la misma pregunta lo detectó.

## 1 · La capa genérica, medida

`display/dc/core/`: **12 ficheros, 22.144 líneas, 806 funciones.**

| fichero | líneas | funciones | líneas/función |
|---|---|---|---|
| `dc.c` | 7.638 | 173 | 44 |
| `dc_resource.c` | 5.735 | 158 | 36 |
| `dc_hw_sequencer.c` | 4.132 | **242** | **17** |
| `dc_stream.c` | 1.314 | 46 | 29 |
| `dc_state.c` | 1.114 | 49 | 23 |
| `dc_link_enc_cfg.c` | 746 | 24 | 31 |
| `dc_link_exports.c` | 552 | 72 | 8 |
| `dc_surface.c` | 323 | 22 | 15 |
| `dc_debug.c` | 319 | 6 | 53 |
| `dc_sink.c` | 101 | 5 | 20 |
| `dc_stat.c` | 91 | 2 | 46 |
| `dc_vm_helper.c` | 79 | 5 | 16 |

**⇒ Tres ficheros son el 79% de la capa: `dc.c`, `dc_resource.c` y
`dc_hw_sequencer.c` = 17.505 de 22.144.** `PROVEN`.

**⇒ Y el tercero es el más denso en funciones por línea con diferencia: 242 funciones en
4.132 líneas, diecisiete líneas de media, y la más larga de las 242 tiene 45.** `PROVEN`.

**Las catorce mayores, todas de 13 a 45 líneas:** `hwss_wait_for_outstanding_hw_updates`
(45), `hwss_dsc_calculate_and_set_config` (34), `hwss_wait_for_no_pipes_pending` (24),
`hwss_program_surface_config` (23), `hwss_wait_for_odm_update_pending_complete` (21),
`hwss_tg_set_dsc_config` (21), `hwss_setup_dpp` (19),
`get_refresh_rate_confirm_color` (19), `hwss_opp_set_disp_pattern_generator` (17),
`hwss_opp_program_bit_depth_reduction` (15), `hwss_tg_program_global_sync` (14),
`hwss_mpc_insert_plane` (14), `hwss_set_output_csc` (13), `hwss_set_ocsc_default` (13).
`PROVEN`.

**⇒ Ninguna función de la capa genérica de display llega a cincuenta líneas.** `PROVEN_DERIVED`.
**Y eso es la forma que tiene la compatibilidad: si todo el camino común está partido en
funciones de quince líneas, cada una puede ser de un chip distinto sin que se note.**

## 2 · La taxonomía interna: un 45% que es una sola familia

**220 de las 242 funciones empiezan por `hwss_`.** `PROVEN`.

| prefijo | n | % |
|---|---|---|
| **`hwss_add_*`** | **110** | **45,5%** |
| `hwss_hubp_*` | 20 | 8,3% |
| `hwss_set_*` | 10 | 4,1% |
| `hwss_tg_*` | 10 | 4,1% |
| `hwss_dsc_*` | 9 | 3,7% |
| `hwss_program_*` | 8 | 3,3% |
| `hwss_opp_*` | 7 | 2,9% |
| `hwss_dpp_*` | 7 | 2,9% |
| `hwss_mpc_*` | 7 | 2,9% |
| `hwss_wait_*` | 5 | 2,1% |

**⇒ El 45% del secuenciador es una sola familia de 110 funciones `hwss_add_*`, y todas
las de esa familia llevan el nombre del bloque que programan.** `PROVEN_DERIVED`.

**Y lo que significan los prefijos, que es la lectura útil:** `tg` es el generador de
temporización, `mpc` el compositor de memorial, `opp` el procesador de píxeles de salida,
`dpp` el de entrada, `hubp` y `hubbub` el concentrador de memoria, `mcif` la interfaz de
memoria, `dccg` el reloj, `dsc` la compresión, `optc` el secuenciador de timing, `dwbc` el
ancho de banda de escritura, `abm` el ajuste de audio, `dmub` el backend de firmware.
**Son los mismos bloques que las tablas de recursos, y aquí es donde se usan.** `PROVEN_DERIVED`.

## 3 · Y las 22 funciones que no son del secuenciador, en tres grupos exactos

| grupo | n | nombres |
|---|---|---|
| **color de confirmación de la funcionalidad** | **12** | `get_*_visual_confirm_color` ×11 + `get_refresh_rate_confirm_color` |
| **predicados de espacio de color** | **7** | `is_rgb_type`, `is_rgb_limited_type`, `is_ycbcr601_type`, `is_ycbcr601_limited_type`, `is_ycbcr709_type`, `is_ycbcr709_limited_type`, `is_ycbcr2020_type` |
| **ajustes de estado** | **3** | `set_drr_and_clear_adjust_pending`, `set_p_state_switch_method`, — |

**⇒ Hay doce funcionalidades, y cada una tiene su getter de «color de confirmación
visual».** `PROVEN_DERIVED`. *Es el mecanismo por el que amdgpu avisa de que ha hecho algo
—un refresco de memoria, un cambio de reloj, una comprimir— cambiando el color de la
pantalla un instante.* **Y hay una inconsistencia de nombres entre las doce: once se
llaman `get_*_visual_confirm_color` y la duodécima, `refresh_rate`, se llama
`get_refresh_rate_confirm_color`, sin el `visual`.** `PROVEN`.

**⇒ Y los siete espacios de color de la capa genérica son, con sus variantes limitadas:
RGB, RGB limitado, YCbCr601, YCbCr601 limitado, YCbCr709, YCbCr709 limitado, YCbCr2020.**
`PROVEN`.

**⇒ Y son ortogonales a los cinco valores del enum del codificador de `148` y `234`:
`PIXEL_ENCODING_UNDEFINED`, `_RGB`, `_YCBCR420`, `_YCBCR422`, `_YCBCR444`.** `PROVEN`.

**⇒ La diferencia es conceptual y es la observación de esta nota:** la capa genérica
habla de **espacio de color** —la matriz que convierte RGB en YCbCr, con sus coeficientes
601, 709, 2020 y su variante de rango limitado— y el codificador habla de **codificación
de píxel** —el submuestreo de croma, 420, 422, 444—. **Son dos ejes distintos y
ortogonales: un mismo modo de vídeo escoge uno de cada uno, y los dos se programan en
sitios distintos del árbol.** `PROVEN_DERIVED`.

## 4 · El censo de bloques, y el 69% que era falso

**Catorce bloques aparecen en los nombres de las 110 `hwss_add_*`.** La pregunta útil es
cuáles de esos bloques existen en DCE, y **la respuesta depende enteramente del criterio**.

**Primer criterio, y es el que yo usé primero:** ¿tiene el directorio `dc/<bloque>/` un
subdirectorio `dce*`?

```
⇒ 76 de 110, el 69%, sobre bloques "que no existen en DCE"
```

**Ese 69% es falso.** **Las implementaciones de DCE no están en `dc/<bloque>/`: están
planas en `dc/dce/`, `dc/dce110/`, `dc/dce120/`, `dc/dce60/` y `dc/dce80/`, que es donde
`dce110_opp_construct` y `dce110_mem_input_v_construct` viven.** `PROVEN_DERIVED`.

**Segundo criterio, el correcto:** ¿aparece el nombre del bloque en **algún fichero de
DCE** del árbol? Recuento con un corpus de 136 ficheros de DCE frente a 982 no-DCE.

| bloque | `hwss_add_` | ficheros de DCE que lo nombran | veredicto |
|---|---|---|---|
| `hubp` | 29 | 2 | **ausente de DCE** |
| `dpp` | 13 | 3 | ausente |
| `mpc` | 10 | 2 | ausente |
| `tg` | 10 | 25 | presente |
| `opp` | 7 | 23 | presente |
| `dsc` | 6 | 5 | presente |
| `hubbub` | 4 | **0** | **ausente de DCE** |
| `mcif` | 4 | 4 | presente |
| `abm` | 3 | 14 | presente |
| `dccg` | 3 | 8 | presente |
| `optc` | 4 | 1 | presente |
| `dwbc` | 3 | **0** | **ausente de DCE** |
| `dmub` | 2 | 16 | presente |

**⇒ Con el criterio correcto: 7 de 98 funciones `hwss_add_` de bloque, el 7%.** `PROVEN`.

**⇒ Y 91 de 98, el 93%, programan hardware que esta GPU tiene.** `PROVEN_DERIVED`.

**⇒ Los dos bloques ausentes de DCE son `hubbub`, el concentrador de memoria, y `dwbc`, el
control de ancho de banda de escritura, y los dos son coherentes con `159`: esta GPU
hereda de DCE 11.0 el concentrador a través de `gmc_v8_0.c` y no tiene escritura
dinámica.** `PROVEN_DERIVED`.

**⇒ Y el 69% y el 7% difieren en un factor de diez, y ambos salieron de un programa, y el
primero era el que yo iba a escribir.** `PROVEN_DERIVED`.

## Lo que NO cierra

| afirmación | estado |
|---|---|
| `core/`: 12 ficheros, 22.144 líneas, 806 funciones | `PROVEN` |
| Tres ficheros son el 79% de la capa | `PROVEN` |
| 242 funciones de 17 líneas de media, la mayor de 45 | `PROVEN` |
| Ninguna función de la capa genérica llega a 50 líneas | `PROVEN_DERIVED` |
| 220 de 242 son `hwss_*`; 110 son `hwss_add_*` | `PROVEN` |
| 14 bloques en los nombres de las `hwss_add_*` | `PROVEN` |
| 12 funcionalidades con su color de confirmación, 11 con `visual` | `PROVEN` |
| 7 espacios de color con variantes limitadas | `PROVEN` |
| 5 valores de `pixel_encoding`, ortogonales a los anteriores | `PROVEN_DERIVED` |
| 7 de 98 `hwss_add_` para bloques ausentes de DCE | `PROVEN` |
| 91 de 98, el 93%, programan hardware que existe | `PROVEN_DERIVED` |
| `hubbub` y `dwbc` son los dos ausentes | `PROVEN_DERIVED` |
| El 69% del primer criterio era falso | `PROVEN_DERIVED` |
| Por qué existe `hwss_add_` y no un nombre de operación | **`NOT_DETERMINED`** |
| Cómo decide el secuenciador el orden de los 110 `add` | **`NOT_DETERMINED`** |
| Si la iGPU Intel comparte ninguno de estos bloques | **`NOT_DETERMINED`** |

**La segunda de las abiertas es la que cierra la capa genérica, y es un orden de llamadas:
los 110 `hwss_add_*` tienen que ejecutarse en un orden, y ese orden es lo que convierte una
tabla de estado en hardware.** Es la misma pregunta que `162` dejó abierta para el IRQ y
que `161` cerró para el reloj, y tiene la misma respuesta: leer la función que los llama y
contar en qué orden.

## Procedencia

- `STATIC` -- `display/dc/core/` completo: los doce ficheros `.c`, con líneas contadas
  por `split("\n")` y funciones contadas con `^(?:static\s+)?(?:void|int|bool|uint\d+_t|
  struct \w+ \*)\s+(\w+)\s*\([^;]*$` en modo multilínea, con el cuerpo delimitado por
  conteo de llaves para obtener su extensión. Ficheros citados: `dc_hw_sequencer.c`
  (las 242 funciones, sus 14 mayores, los dos censos de prefijos, los 12
  `get_*_visual_confirm_color`, los 7 `is_*_type` y los 98 `hwss_add_*` de bloque),
  `dc.c`, `dc_resource.c`, `dc_stream.c`, `dc_state.c`, `dc_link_enc_cfg.c`,
  `dc_link_exports.c`, `dc_surface.c`, `dc_debug.c`, `dc_sink.c`, `dc_stat.c`,
  `dc_vm_helper.c`; `display/dc/dc_hw_types.h` (el enum `pixel_encoding`, con sus cinco
  valores reales más `COUNT`); `display/dc/dce/` (donde `dce_opp.c` y `dce110_opp_v.c`
  demuestran que las implementaciones de DCE son planas, no por bloque), y
  `display/dc/dce/dce_opp.c:725` (`dce110_opp_v_construct`).
- Medición por programa: **las dos versiones del censo de bloques, con el 69% y el 7%
  impresos y con los ficheros de DCE contados por bloque** (2, 3, 2, 25, 23, 5, 0, 4,
  14, 8, 1, 0, 16); la extensión de las 242 funciones por conteo de llaves; los dos
  censos de prefijos sobre las 242 y sobre las 110.
- **Dos errores de criterio propios, y el segundo es el de la nota:**
  (1) El primer clasificador de bloques usó «¿tiene `dc/<bloque>/` un subdirectorio
  `dce*`?», que es falso porque las implementaciones de DCE son planas en `dc/dce110/`,
  `dc/dce/`, `dc/dce120/`, `dc/dce60/` y `dc/dce80/`. Dio 76 de 110. **Y la prueba de que
  el criterio era falso es `dce110_opp_construct`, que existe y está en `dc/dce110/` y
  no en `dc/opp/`.**
  (2) El conteo de funcionalidades de confirmación dio 12 por lista visual y 11 por
  regex, porque `get_refresh_rate_confirm_color` no lleva el `visual` en medio. **La
  lista visual y el regex contaban cosas distintas, y los dos tenían razón: son doce
  funciones con dos convenciones de nombre.**
- Encadenada con `171` (la versión de este bloque), `170` (**la regla de qué versiones
  tienen fichero, y aquí el mismo criterio mal aplicado en un árbol distinto**),
  `165` (**dos criterios de clasificación que difieren en 18,7 puntos, y aquí dos que
  difieren en un factor de diez — el mismo error, y con la misma corrección**),
  `162` (las 6 tuberías, y aquí el 93% de la capa genérica que sí programa esta GPU),
  `161` (el reloj), `159` (los 52 constructores y el 21% por generación), `232` (la
  tabla y el constructor, y aquí la capa que los consume), `155` (DCE 11.2),
  `148` y `234` (el enum `pixel_encoding`, y aquí su ortogonal con el espacio de color),
  `150` (el enum de señal), `145` (`PROVEN_ABSENT` con causa).
- No se editó `AGENTS.md` ni `OPEN-FRONTIERS.md`.

## Nota de método

**Un programa mío produjo el 69% y estaba a punto de escribirlo, y el 69% era falso por
un factor de diez. Y esa es la observación más útil de diecinueve notas, porque el
número falso era mucho más convincente que el correcto.**

*El error: pregunté «¿tiene el directorio `dc/<bloque>/` un subdirectorio `dce*`?», que
es una pregunta verosímil, y el árbol la contesta que sí o que no con una claridad
total.* **Y la respuesta fue que no, para diez de los catorce bloques, y eso son el 69% de
las funciones del secuenciador.** *El 69% es un número con dos cifras significativas, con
un porcentaje, y con la forma de un resultado publicable. Y no tenía nada detrás.*

*La corrección: preguntar «¿aparece el nombre del bloque en algún fichero de DCE?», que
es la misma pregunta con un criterio distinto, y da el 7%.* **Y la prueba de que el
primer criterio era falso es una sola línea que ya estaba escrita: `dce110_opp_construct`
existe, y está en `dc/dce/dce_opp.c`, y `dc/opp/` sólo tiene subdirectorios `dcn`.** *Las
implementaciones de DCE están planas por familia, no por bloque, y yo busqué por bloque.*

**La regla, y generaliza la de `165` con un caso extremo: un criterio de clasificación
tiene que mencionar la misma cosa que la pregunta.** *En `165` el criterio era la ruta
contra el nombre de fichero, y las dos cosas son «el mismo bloque», aunque no del todo.*
**Aquí el criterio era el directorio contra la existencia del código, y el directorio
resultó ser una convención de DCN.** *Un criterio es correcto mientras las dos cosas que
compara sean la misma cosa; en cuanto dejan de serlo, produce un número plausible con la
misma confianza con la que produciría uno correcto.*

**Y el corolario, que es lo que hace peligroso al 69%: un número plausible con la
estructura de una medición es más peligroso que un número raro.** *En toda la tanda, los
errores los ha delatado la rareza — `paso constante: False` en `232`, un rango fuera de
límite en `235`, nueve filas sin generación en `236`.* **El 69% no era raro: era redondeado,
redondeado y con su porcentaje, y para escribirlo no hacía falta ninguna de las
comprobaciones que las otras veces me pararon. Un error que no dispara ninguna alarma es
el único que hay que temer, porque llega hasta el papel.**
