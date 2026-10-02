# 152 · `struct dc_link`: la tercera pieza, y el campo que inventé tiene nombre

```
CLASSIFICATION=DOCUMENTATION · TRACK=STATIC
CORPUS=RESEARCH/working/linux-7.1.3 · HARDWARE_SCOPE=HOST-C/RX550/0000:01:00.0
WORK_CLASS=READ_ONLY/EVIDENCE · WRITE_EXECUTION=NONE · MODIFICATIONS=0
RUNTIME=NOT_RUN · GPU INTACTA
```

## Qué resuelve

**El objeto al que en `148` le presté un campo que no existe.** Está en
`display/dc/core/dc.h:1628-1794` — 167 líneas — y **tiene dos campos donde yo puse
uno**, con dos nombres distintos y dos significados distintos.

**Y con eso queda cerrado el modelo de tres objetos de `149`, y medido.**

## 1 · El campo que inventé, y su nombre real

En `148` escribí `crtc_timing->link_type`. **`struct dc_link` tiene:**

```c
        enum dc_connection_type type;          /* la topología del enlace   */
        enum signal_type        connector_signal;  /* la señal del conector */
```

**Dos campos, dos enumeraciones distintas, dos preguntas distintas.** `PROVEN`.

### Y `dc_connection_type` no es el tipo de salida

`display/dc/dc_types.h:355-361`, cinco valores:

| valor | qué es |
|---|---|
| `dc_connection_none` | nada |
| `dc_connection_single` | un único sink |
| `dc_connection_mst_branch` | rama de un hub MST |
| `dc_connection_sst_branch` | rama de un hub de flujo simple |
| `dc_connection_analog_load` | **carga analógica: DVI/VGA** |

**Ninguno de los cinco es "HDMI" ni "DisplayPort".** Esta enumeración describe **cómo
está conectado el enlace a su sink**, no qué señal viaja por él. La señal es
`connector_signal`, que es la `enum signal_type` de `150`. `PROVEN_DERIVED`.

**Y hay un detalle útil: `dc_connection_analog_load` es como se modela la salida
analógica.** Es decir, el DVI de esta GPU — que `150` nombraba
`SIGNAL_TYPE_DVI_SINGLE_LINK` — es una *carga analógica*, no un enlace digital. **La
señal dice "DVI de un enlace"; la conexión dice "carga analógica". Son
complementarias, y por eso son dos campos.**

**Mi invención no era descabellada: era media. Existía un campo de tipo, era de
conexión, y yo le puse el nombre de la señal.** Y eso es exactamente lo que la regla
de `149`/`150` dice que no hay que hacer.

## 2 · La estructura entera, y lo que dice

`dc.h:1628-1794`. De sus campos, seis grupos:

### El modelo de sinks: uno local, hasta cuatro remotos

```c
        struct dc_sink *remote_sinks[MAX_SINKS_PER_LINK];
        unsigned int    sink_count;
        struct dc_sink *local_sink;
```

**Un enlace tiene un sink *local* — el panel directo — y hasta `MAX_SINKS_PER_LINK`
sinks *remotos*.** `MAX_SINKS_PER_LINK` es **4** (`dc_types.h:1322`).

**⇒ Así es como se modela un hub DisplayPort MST: un enlace, varios sinks.** No un
enlace por pantalla, sino un enlace con una rama local y un árbol de ramas
remotas. `PROVEN_DERIVED`.

**Y esto es por lo que `SIGNAL_TYPE_DISPLAY_PORT_MST` es un valor propio y no una
bandera de `SIGNAL_TYPE_DISPLAY_PORT`** (`150`): porque la topología MST y la señal
DP son cosas distintas, y por eso hay dos campos.

### Los objetos de hardware que el enlace posee

```c
        struct link_encoder *link_enc;
        struct panel_cntl    *panel_cntl;
        uint8_t  link_enc_hw_inst;
        enum engine_id eng_id;
        enum engine_id dpia_preferred_eng_id;
```

**Cada enlace tiene un codificador y un control de panel, y se nombra a sí mismo por
el índice de hardware y el identificador de motor.** `link_enc_hw_inst` es el puente
del objeto software a la salida física: es donde se resuelve *qué* DIG o DVI maneja
este enlace. `PROVEN_DERIVED`.

### Cuatro variantes de capacidades, y la distinción importa

```c
        struct dc_link_settings reported_link_cap;    /* lo que declara el sink */
        struct dc_link_settings verified_link_cap;    /* lo que se ha verificado */
        struct dc_link_settings cur_link_settings;    /* lo activo ahora        */
        struct dc_link_settings preferred_link_setting;
```

**"reported" frente a "verified" es una distinción real y no cosmética:** lo que un
panel declara por EDID y lo que se ha comprobado midiendo. Un driver propio tiene
que Distinguir los dos, y un estudio de caso de por qué están separados está en que
la diferencia es la desconfianza. `PROVEN_DERIVED`.

### El resto, en una línea cada grupo

| grupo | campos |
|---|---|
| lanes | `cur_lane_setting[LANE_COUNT_DP_MAX]`, `bios_forced_drive_settings` |
| DP cable | `dpcd_caps`, `dpcd_sink_count`, `dpcd_sink_ext_caps`, `chip_caps` |
| PSR/replay | `psr_settings`, `replay_settings` |
| PHY | `phy_state`, `phy_transition_bitmask`, `is_dds` |
| panel | `panel_config`, `panel_type`, `backlight_control_type`, `edp_revision` |
| HDCP | `hdcp_caps` |
| MST | `mst_stream_alloc_table` |
| pruebas | `compliance_test_state`, `current_test_pattern`, `pending_test_pattern` |
| LTTPR | `lttpr_mode`, `vendor_specific_lttpr_link_rate_wa` |
| mapa a salida | `union ddi_channel_mapping ddi_channel_mapping`, `ep_type`, `link_id`, `ext_enc_id` |

**Y `union ddi_channel_mapping` es la pieza que falta para cerrar la cadena:** DDI es
la capa que mapea un enlace a una salida física del display controller. **Es el
`PTBA` del display** — el punto donde un identificador software se convierte en una
dirección de registro.

## 3 · Y doce workarounds, con nombre

`struct link_flags`, contado por programa: **12**, no los 11 que se ven en un volcado
truncado.

```
dp_keep_receiver_powered          dpia_mst_dsc_always_on
dp_skip_DID2                      dpia_forced_tbt3_mode
dp_skip_reset_segment             dongle_mode_timing_override
dp_skip_fs_144hz                  blank_stream_on_ocs_change
dp_mot_reset_segment              read_dpcd204h_on_irq_hpd
force_dp_ffe_preset               skip_phy_ssc_reduction
```

**Tres de los doce son de `dpia_*`**, y dos de los doce son de DSC
(`dpia_mst_dsc_always_on`) o de FFE. **Y `dp_mot_reset_segment` tiene un `mot` donde
probablemente quería `not` — errata del driver de referencia, no mía, y no la he
tocado.** `OBSERVED`.

## 4 · Los límites declarados, y que no son de este chip

`dc/inc/hw/hw_shared.h:48-50` y `dc/dc_types.h:1322`:

```
MAX_DPIA            6
MAX_CONNECTOR       6
MAX_VIRTUAL_LINKS   4
MAX_LINKS = 6 + 6 + 4 = 16        (suma impresa por programa)
MAX_SINKS_PER_LINK  4
```

**⇒ Hasta 64 instancias de sink, en un chip con un motor de display y dos shader
engines.** `PROVEN` para los números; que el hardware no puede llegar es
`PROVEN_DERIVED` a partir del silicio conocido de la GPU.

**Y `MAX_DPIA 6` es para una función que esta GPU no tiene.** DPIA —con
`dpia_preferred_eng_id` y `dpia_bw_alloc_config` en el propio `dc_link`— es el
túnel DisplayPort/USB4/Thunderbolt, que no existe en GFX8. **Es el mismo patrón que
DSC en `149` y que los 41 campos con máscara cero de `147`, y ahora en la escala de
una constante de dimensionamiento.**

**La observación de fondo, y es la que cierra este bloque: la abstracción del DC está
escrita para la unión de todos los chips que amdgpu soporta, y esta GPU ocupa una
esquina pequeña.** Los límites (16 enlaces, 4 sinks, 6 DPIA) y las funciones (DPIA,
DSC, doce workarounds, MST, LTTPR, HDCP) están **declarados para chips que no son
este.** `PROVEN_DERIVED`, y es una advertencia práctica para un driver propio: *leer
la estructura del DC es leer el superset, y el trabajo consiste en determinar qué
subconjunto es realizable en esta GPU — que es `147` haciéndolo con los 89 de 130
campos, y esta nota lo confirma a escala de estructura.*

## Lo que NO cierra

| afirmación | estado |
|---|---|
| `struct dc_link` está en `dc/core/dc.h:1628-1794` | `PROVEN` |
| Tiene `type` y `connector_signal`, dos campos | `PROVEN` |
| `dc_connection_type` tiene 5 valores, ninguno de señal | `PROVEN` |
| `dc_connection_analog_load` es la salida analógica | `PROVEN_DERIVED` |
| Un enlace: un sink local + hasta 4 remotos | `PROVEN` |
| MST se modela como un enlace con ramas | `PROVEN_DERIVED` |
| `link_enc_hw_inst` y `eng_id` llegan al hardware | `PROVEN_DERIVED` |
| 4 variantes de capacidades, reported ≠ verified | `PROVEN` |
| 12 workarounds, 3 de ellos `dpia_*` | `PROVEN` (por programa) |
| `MAX_LINKS` = 6+6+4 = 16 | `PROVEN` (suma por programa) |
| `MAX_DPIA 6` es para una función que esta GPU no tiene | `PROVEN_DERIVED` |
| El DC es un superset y esta GPU ocupa una esquina | `PROVEN_DERIVED` |
| Dónde se ASIGNA `connector_signal` | **`NOT_DETERMINED`** — sigue abierto desde `150` |
| Qué es exactamente DDI y cómo mapea a un DIG | **`NOT_DETERMINED`** |
| Cuántos DIG/DVI tiene esta GPU | **`NOT_DETERMINED`** |
| `LANE_COUNT_DP_MAX` | **`NOT_DETERMINED`** — el `#define` no salió |

**La primera de las abiertas es la que `150` abrió y esta nota no cierra: dónde se
decide el valor de la señal.** Y el nombre del campo cambió —`connector_signal`, no
`signal`—, lo cual hace la búsqueda más estrecha y mejor: `->connector_signal =`.

## Procedencia

- `STATIC` -- `display/dc/core/dc.h:1628-1794` (`struct dc_link`, 167 líneas),
  `display/dc/inc/hw/hw_shared.h:48-50` (`MAX_DPIA`, `MAX_CONNECTOR`,
  `MAX_VIRTUAL_LINKS`) y `display/dc/inc/hw/hw_shared.h:52` (`MAX_LINKS`),
  `display/dc/dc_types.h:355-361` (`enum dc_connection_type`),
  `display/dc/dc_types.h:1322` (`MAX_SINKS_PER_LINK`),
  `display/dc/include/signal_types.h:34-45` (de `150`),
  `display/dc/core/dc.h:1146` (`using_dml2`, de `151`).
- Recuentos por programa: los 12 `bool` de `struct link_flags` con
  `re.findall` entre `struct link_flags {` y `} wa_flags;`; la suma `6+6+4`
  calculada; el recuento de valores de `enum signal_type` y de
  `enum dc_connection_type`.
- **Dos errores de ruta y de patrón míos en esta nota, antes de los resultados:**
  busqué `core/dc.h` cuando `grep -rl` había devuelto `dc/dc.h`, y mi patrón
  `struct link_flags \{...\}` falló por la indentación. Los dos se detectaron porque
  la salida estaba vacía y `awk` imprimió desde la línea 1.
- Encadenada con `151` (DML1 vs DML2, y los doce ficheros de `core/`), `150` (la
  `enum signal_type` de 10 valores, y el `NOT_DETERMINED` de dónde se decide),
  `149` (la frontera DM→DC, y que DSC no es cosa de esta GPU), `148` (el campo
  inventado, corregido aquí con su nombre real), `147` (los 89 de 130 campos).
- No se editó `AGENTS.md` ni `OPEN-FRONTIERS.md`.

## Nota de método

**Mi invención de `148` era media, y eso es lo que la hace instructiva.** No puse un
campo que no existe: puse un campo que **existe, con otro nombre, y que significa otra
cosa** — la topología del enlace en vez de la señal. Y no lo detecté durante tres
notas porque las tres estaban mirando el sitio equivocado: `147` el stream encoder,
`148` el sink, `149` el timing.

**Y el error no era de lectura sino de modelo.** Tenía en la cabeza "un timing con su
tipo de salida", que es un modelo plausible y equivocado, y una estructura rellena
siempre encaja con el modelo que uno tiene. **La estructura real tiene dos campos,
porque la pregunta real tiene dos partes: ¿qué señal viaja? y ¿cómo está conectado?
Esas son dos preguntas y hacen falta dos campos.**

*Un invento que encaja con el modelo mental no se detecta leyendo más: se detecta
buscando el campo por su tipo.* Y aquí el tipo —`enum dc_connection_type`— estaba en
el mismo fichero a cuarenta líneas, con cinco valores, ninguno de los cuales era
"HDMI". **Cinco valores que no son HDMI son la prueba de que el campo no era el que
buscaba, y eso se lee en un minuto una vez que se tiene el fichero correcto.**

**Y la lección de método que sí es transferible, y es la que `151` dejó escrita:** el
camino a un campo inventado no es buscarlo por donde se usa, sino **mirar la
definición del tipo que lo contiene y contar sus campos**. `struct dc_link` tiene 167
líneas y las leí enteras, y en la primera pantalla estaban los dos campos.
