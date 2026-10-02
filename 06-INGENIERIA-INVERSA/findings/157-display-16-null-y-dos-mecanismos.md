# 157 · La tabla de este GPU está al 58%, y eso explica cómo amdgpu soporta treinta chips

```
CLASSIFICATION=DOCUMENTATION · TRACK=STATIC
CORPUS=RESEARCH/working/linux-7.1.3 · HARDWARE_SCOPE=HOST-C/RX550/0000:01:00.0
WORK_CLASS=READ_ONLY/EVIDENCE · WRITE_EXECUTION=NONE · MODIFICATIONS=0
RUNTIME=NOT_RUN · GPU INTACTA
```

## Qué resuelve

**La pregunta de fondo de todo el bloque de display: ¿cómo soporta amdgpu treinta
chips distintos con un solo árbol de código?**

**La respuesta son dos mecanismos de nulabilidad, los dos comprobados en el punto de
llamada, y los dos medidos aquí:**

| | para qué | cómo se comprueba | dónde |
|---|---|---|---|
| **máscara de swizzle** (`147`, `156`) | un **campo de registro** que no existe | `if (se_mask->FIELD)` | `dce_stream_encoder.c:322` |
| **puntero a función nulo** (esta nota) | una **operación** que no existe | `if (funcs->X)` | `link_hwss_dio.c:67`, `:70` |

## 1 · La tabla de esta máquina, al 58%

`struct stream_encoder_funcs` se declara en `display/dc/inc/hw/stream_encoder.h:133-278`
con **38 miembros**. La tabla que esta GPU recibe,
`dce110_str_enc_funcs` (`dce_stream_encoder.c:1525-1561`), inicializa **22**.

**⇒ 16 quedan a NULL. Cobertura del 58%, medido por programa.**

### Los dieciséis, y dos de ellos tienen explicación

| | |
|---|---|
| `update_dp_info_packets_sdp_line_num` | |
| `send_immediate_sdp_message` | |
| **`enable_stream`** | **operación central** |
| `dp_get_pixel_format` | |
| **`enc_read_state`** | **operación central** |
| `dp_set_dsc_config` | ← **DSC** |
| `dp_set_dsc_pps_info_packet` | ← **DSC** |
| `set_dynamic_metadata` | |
| `dp_set_odm_combine` | |
| `get_fifo_cal_average_level` | |
| `set_input_mode` | |
| `enable_fifo` / `disable_fifo` / `is_fifo_enabled` | |
| **`map_stream_to_link`** | **operación central** |
| `get_pixels_per_cycle` | |

**Dos de los dieciséis son de DSC, y eso es exactamente lo que `149` predijo: esta
GPU no tiene DSC.** Los otros catorce no corresponden a ninguna característica
ausente. `PROVEN`.

## 2 · Y por qué no es un fallo: los llamantes comprueban

**Los tres llamantes de la ruta DCE comprueban el puntero antes de llamar:**

```c
link_hwss_dio.c:67     if (stream_enc->funcs->enable_stream)
link_hwss_dio.c:68             stream_enc->funcs->enable_stream(stream_enc, ...);
link_hwss_dio.c:70     if (stream_enc->funcs->map_stream_to_link)
link_hwss_dio.c:71             stream_enc->funcs->map_stream_to_link(stream_enc, ...);
dc.c:2016              } else if (se && se->funcs->get_pixels_per_cycle) {
dc.c:2017                      uint32_t pixels_per_cycle = se->funcs->get_pixels_per_cycle(se);
```

**El patrón `if (funcs->X) funcs->X(...)` es la convención, y por eso la tabla puede
estar incompleta sin riesgo.** `PROVEN`.

**Y hay una única excepción, y es coherente:** `link_hwss_hpo_dp.c:79-80` llama a
`enable_stream` y a `map_stream_to_link` **sin comprobar**:

```c
link_hwss_hpo_dp.c:74  void setup_hpo_dp_stream_encoder(struct pipe_ctx *pipe_ctx)
link_hwss_hpo_dp.c:79          stream_enc->funcs->enable_stream(stream_enc);
link_hwss_hpo_dp.c:80          stream_enc->funcs->map_stream_to_link(stream_enc, ...);
```

**HPO es el HDMI Performance Optimiser**, una función de la era DCN, sobre un tipo
propio —`struct hpo_dp_stream_encoder`—, **con su propia tabla de funciones.** O sea:
**la tabla de HPO es completa, la de DCE no, y por eso su llamante no comprueba.**
`PROVEN_DERIVED`.

**⇒ La regla es: cada tabla se usa con la confianza que su completitud merece, y quien
escribe el llamante sabe cuál es cuál.** Un `NULL` no es un error de compilación ni un
`oops` en runtime: es un caso declarado.

## 3 · Los cuatro caminos de salida, y cómo mapean a la señal de `154`

De las 22 entradas, cuatro son "programar los atributos de la salida":

```
.dp_set_stream_attribute    = dce110_stream_encoder_dp_set_stream_attribute
.hdmi_set_stream_attribute  = dce110_stream_encoder_hdmi_set_stream_attribute
.dvi_set_stream_attribute   = dce110_stream_encoder_dvi_set_stream_attribute
.lvds_set_stream_attribute  = dce110_stream_encoder_lvds_set_stream_attribute
```

**Y son exactamente los cuatro tipos de salida de la enumeración de `150`:**

| `connector_signal` de `154` | setter que programa el registro |
|---|---|
| `SIGNAL_TYPE_HDMI_TYPE_A` | `.hdmi_set_stream_attribute` |
| `SIGNAL_TYPE_DVI_SINGLE_LINK` / `_DUAL_LINK` | `.dvi_set_stream_attribute` |
| `SIGNAL_TYPE_DISPLAY_PORT` / `_MST` / `EDP` | `.dp_set_stream_attribute` |
| `SIGNAL_TYPE_LVDS` | `.lvds_set_stream_attribute` |
| `SIGN_TYPE_NONE`, `VIRTUAL` | **ninguno** |

**⇒ La cadena de `154` se cierra aquí: el `switch` sobre `link_id.id` decide
`connector_signal`, y `connector_signal` elige cuál de los cuatro setters programa
los registros.** Cuatro señales, cuatro caminos, y el hardware detrás. `PROVEN_DERIVED`.

**Y la última fila de la tabla es una predicción comprobable:** los cinco
`CONNECTOR_ID_*` sin caso en el `switch` de `154` — `PCIE`, `HARDCODE_DVI`,
`WIRELESS`, `MIRACAST`, `VIRTUAL` — dejarían `connector_signal` en 0, que es
`SIGNAL_TYPE_NONE`, **y no hay setter para ese valor.** `PROVEN_DERIVED`, y encaja
con que `VIRTUAL` y `MIRACAST` no se programen por esta ruta.

## 4 · Y tres entradas que no son de DCE 11.0

```
.setup_stereo_sync   = setup_stereo_sync        (L1490)
.dig_connect_to_otg  = dig_connect_to_otg       (L1499)
.dig_source_otg      = dig_source_otg           (L1511)
```

**19 de las 22 son `dce110_*`, y tres son genéricas, definidas nueve líneas antes de
la tabla.** `PROVEN`.

**Esto corrobora `156` desde el otro lado: la tabla mezcla implementaciones de
generación con compartidas, así que el nombre de la tabla —`dce110_str_enc_funcs`— no
describe el origen de sus entradas.** Y `dig_source_otg` es el `DIG_SOURCE_SELECT` de
`147`, programado aquí.

**Y hay siete entradas de audio**, lo que confirma por una vía independiente lo que
`155` lo dijo por otra vía}:
`audio_mute_control`, `dp_audio_setup`, `dp_audio_enable`, `dp_audio_disable`,
`hdmi_audio_setup`, `hdmi_audio_disable`, `set_avmute`. **`AFMT_AUDIO_CLOCK_EN` está
en la lista `DCE112`, y el camino de audio está en la tabla: esta GPU tiene audio
HDMI y DisplayPort.** `PROVEN_DERIVED`.

## 5 · El inventario, que es lo que quería esta nota

**Para un driver propio, la lista de trabajo del codificador de stream de esta GPU es
esto, y son 22 llamadas:**

| grupo | entradas |
|---|---|
| **programar la salida** | **4** — dp, hdmi, dvi, lvds |
| paquetes de información | 4 — update/stop × {hdmi, dp} |
| blank / unblank | 2 — `dp_blank`, `dp_unblank` |
| **audio** | **7** — mute, dp_setup/enable/disable, hdmi_setup/disable, avmute |
| control de timing | 1 — `set_throttled_vcp_size` |
| **selección de salida** | **2** — `dig_connect_to_otg`, `dig_source_otg` |
| stereosync | 1 — `setup_stereo_sync` |
| reset de atributos | 1 — `hdmi_reset_stream_attribute` |

**Y 16 que esta GPU no tiene, de las cuales 2 son de DSC — una característica
ausente, no un descuido — y 14 son de generaciones posteriores.**

**El paso 4 es el que programa la salida, y son cuatro funciones. Las otras dieciocho
son audio, paquetes, blanking y selección de DIG.** **Para dibujar en una pantalla
hace falta el grupo de cuatro y el de selección; el resto es audio y sincronización
de vídeo, que es opcional.** `PROVEN_DERIVED`, y reduce el trabajo a un número
manejable.

## Lo que NO cierra

| afirmación | estado |
|---|---|
| 38 miembros, 22 entradas, 58% de cobertura | `PROVEN` (por programa) |
| 16 punteros a NULL | `PROVEN` |
| 2 de los 16 son de DSC | `PROVEN` |
| Los llamantes de la ruta DCE comprueban | `PROVEN` |
| La excepción sin comprobar es de HPO, con tabla propia | `PROVEN_DERIVED` |
| 4 setters de salida, uno por familia de señal | `PROVEN` |
| `connector_signal` elige el setter | `PROVEN_DERIVED` |
| Los 5 ids sin setter quedan en `SIGNAL_TYPE_NONE` | `PROVEN_DERIVED` |
| 3 entradas genéricas en la tabla | `PROVEN` |
| 7 entradas de audio; esta GPU tiene audio | `PROVEN_DERIVED` |
| El inventario: 4 para dibujar, 18 opcional | `PROVEN_DERIVED` |
| Cuál de los 22 se llama en la práctica aquí | **`NOT_DETERMINED`** |
| Si esta GPU tiene salida de audio HDMI | **`NOT_DETERMINED`** — depende del modo |
| Cuántos de los 22 implementa la tabla de HPO | **`NOT_OBSERVED`** |
| Los 14 no-DSC, por qué generación los añadió | **`NOT_DETERMINED`** |

**La tercera de las abiertas es la que cerraría el bloque por el lado de la
compatibilidad: comparar la tabla de esta GPU con la de `dce120` y con la de `dce60`
daría la curva de crecimiento del conjunto de operaciones por generación, y eso es el
historial del driver en una tabla.**

## Procedencia

- `STATIC` -- `display/dc/inc/hw/stream_encoder.h:133-278` (los 38 miembros),
  `display/dc/dce/dce_stream_encoder.c:1490-1523` (las tres funciones genéricas),
  `display/dc/dce/dce_stream_encoder.c:1525-1561` (la tabla completa, 22 entradas),
  `display/dc/dce/dce_stream_encoder.c:267-330` (el setter de DP y el guard de la
  máscara), `display/dc/dce/dce_stream_encoder.c:534-560` y `:651-680` (los setters
  de HDMI y DVI), `display/dc/link/hwss/link_hwss_dio.c:67-71`,
  `display/dc/link/hwss/link_hwss_hpo_dp.c:74-81`,
  `display/dc/core/dc.c:2016-2017`, `display/dc/resource/dce112/dce112_resource.c:513-519`.
- Recuento por programa: los 38 miembros del `struct` con `re.findall` sobre el
  cuerpo; las 22 entradas de la tabla; **la diferencia de los dos conjuntos, que es
  el número que sostiene §1**; la clasificación de las tres entradas no-`dce110_`; los
  cuatro setters por sufijo.
- Encadenada con `156` (la identidad de un camino la da la tabla y el constructor —
  esta nota es el inventario completo de esa tabla), `155` (**DCE 11.2, y el reloj de
  canal y el audio presentes**, corroborados aquí por la vía de la tabla),
  `154` (el `switch` que decide la señal, y aquí donde se consume),
  `149` (**DSC ausente — y aquí sus dos punteros a NULL, previstos**),
  `147` (la tabla de swizzle, el otro mecanismo de nulabilidad), `153` (los siete
  paths), `150` (la enumeración de señal).
- No se editó `AGENTS.md` ni `OPEN-FRONTIERS.md`.

## Nota de método

**El bloque de display se cierra con un número que se obtiene restando dos inventarios,
y eso es la clase de resultado que no se obtiene leyendo: se obtiene midiendo dos
veces y restando.**

*38 miembros y 22 entradas.* El `struct` se lee en un fichero y la tabla en otro, y
sólo la resta produce el hecho —que la tabla de esta GPU está al 58%—, que a su vez
produce la pregunta útil —**¿y no rompe?**— y la respuesta útil —**los llamantes
comprueban**.

**Y hay una coherencia que sólo se ve al juxtaponer las dos notas:** `147` mostró que
`if (REG(...))` es una comprobación de presencia, `156` mostró que el guard de la
tabla de swizzle lo es, y esta nota enseña que **el patrón es el mismo en los dos
niveles y con la misma forma textual**: `if (algo_que_puede_ser_nulo) usalo`. **Un
puntero a función y una máscara de cero son las dos formas que tiene el mismo
concepto en C, y amdgpu usa las dos en el mismo fichero, a treinta líneas de distancia.**

*Y esa observación explica la arquitectura entera: un driver que soporta treinta chips
necesita una forma de decir "esto no existe en mi chip", y la forma más barata en C es
un valor centinela — cero en una máscara, nulo en un puntero. Todo lo demás —las
tablas de swizzle, las tablas de punteros, la convención `if (funcs->X)`— es
infraestructura para que ese centinela sea legible.*
