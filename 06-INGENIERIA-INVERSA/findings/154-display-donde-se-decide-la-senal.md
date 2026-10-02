# 154 · Dónde se decide la señal: un `switch` sobre el id de conector del firmware

```
CLASSIFICATION=DOCUMENTATION · TRACK=STATIC
CORPUS=RESEARCH/working/linux-7.1.3 · HARDWARE_SCOPE=HOST-C/RX550/0000:01:00.0
WORK_CLASS=READ_ONLY/EVIDENCE · WRITE_EXECUTION=NONE · MODIFICATIONS=0
RUNTIME=NOT_RUN · GPU INTACTA
```

## Qué resuelve

**El `NOT_DETERMINED` que lleva abierto desde `150`, y que cinco notas han estado
rodeando.** Cerrado, con fichero, línea y función: **`display/dc/link/link_factory.c`,
función `construct_phy`, `L626-671`.**

**Y confirma por segunda vía la derivación de `153`.**

## 1 · El `switch`, y sobre qué se decide

`link_factory.c:626-671`, dentro de `construct_phy` (`L487-849`):

```c
        switch (link->link_id.id) {
        case CONNECTOR_ID_HDMI_TYPE_A:
                link->connector_signal = SIGNAL_TYPE_HDMI_TYPE_A;
        case CONNECTOR_ID_SINGLE_LINK_DVID:
        case CONNECTOR_ID_SINGLE_LINK_DVII:
                link->connector_signal = SIGNAL_TYPE_DVI_SINGLE_LINK;
        case CONNECTOR_ID_DUAL_LINK_DVID:
        case CONNECTOR_ID_DUAL_LINK_DVII:
                link->connector_signal = SIGNAL_TYPE_DVI_DUAL_LINK;
        case CONNECTOR_ID_VGA:
                link->connector_signal = SIGNAL_TYPE_RGB;
        case CONNECTOR_ID_DISPLAY_PORT:
        case CONNECTOR_ID_MXM:
        case CONNECTOR_ID_USBC:
                link->connector_signal = SIGNAL_TYPE_DISPLAY_PORT;
        case CONNECTOR_ID_EDP:
                link->connector_signal = SIGNAL_TYPE_EDP;
```

**Y `link_id` viene del firmware, dos líneas y veinte más arriba** (`L518-519`):

```c
        link->link_id =
                bios->funcs->get_connector_id(bios, init_params->connector_index);
```

**⇒ La cadena completa es de tres saltos, y los tres son de software y firmware:**

```
 1  el Display Manager pasa un connector_index  (un número)
 2  el ATOM BIOS devuelve link_id, un graphics_object_id cuyo campo .id es un
    CONNECTOR_ID_*
 3  un switch sobre ese .id elige uno de 6 SIGNAL_TYPE_*
```

`PROVEN_DERIVED`. Y **`connector_index` es el único parámetro que entra del mundo
externo**, y es un índice, no un nombre.

## 2 · El colapso: 16 ids de conector → 6 señales

Contados por programa sobre las cabeceras de `display/`:

| `CONNECTOR_ID_*` | valor |
|---|---|
| `UNKNOWN` | 0 |
| `SINGLE_LINK_DVII` | 1 |
| `DUAL_LINK_DVII` | 2 |
| `SINGLE_LINK_DVID` | 3 |
| `DUAL_LINK_DVID` | 4 |
| `VGA` | 5 |
| `HDMI_TYPE_A` | 12 |
| `LVDS` | 14 |
| `PCIE` | 16 |
| `HARDCODE_DVI` | 18 |
| `DISPLAY_PORT` | 19 |
| `EDP` | 20 |
| `MXM` | 21 |
| `WIRELESS` | 22 |
| `MIRACAST` | 23 |
| `USBC` | 24 |
| `VIRTUAL` | 100 |

**Diecisiete valores, y la numeración es dispersa: 0-5 correlativos, luego 12, 14, 16,
18-24, y 100.** `PROVEN`.

**⇒ No es una enumeración: es un espacio de nombres asignado por el firmware.** Los
huecos entre 6 y 11, y el salto a 100 para `VIRTUAL`, son huecos de verdad. Y el
campo `.id` es de 8 bits (`153`), así que 100 cabe con holgura.

**Y el `switch` sólo cubre nueve de los diecisiete**, que colapsan en seis señales.
Cinco ids **no tienen caso**: `PCIE` (16), `HARDCODE_DVI` (18), `WIRELESS` (22),
`MIRACAST` (23), `VIRTUAL` (100). `PROVEN`, por recuento.

**Y hay una asimetría en la granularidad que dice algo:** el firmware distingue
`DVID` de `DVII` — DVI digital de un enlace contra DVI integrado, que es
HDMI-like — y el driver **colapsa ambos a `DVI_SINGLE_LINK` o `DVI_DUAL_LINK`.**
**El vocabulario del hardware es más fino que el del driver, y el driver lo pierde en
este punto.** `PROVEN_DERIVED`.

## 3 · Y una segunda pasada, que el driver explica en voz alta

`link_factory.c:715-720`, **después** del `switch`:

```c
        /* For external DP bridge encoders:
         * Set the connector signal to DisplayPort so that they can work with
         * the pre-existing code paths for DP without a lot of code churn.
         */
        if (link->ext_enc_id.id != ENCODER_ID_UNKNOWN)
                link->connector_signal = SIGNAL_TYPE_DISPLAY_PORT;
```

**El driver dice que sobreescribe la señal física por razones de compatibilidad de
código.** `PROVEN`, y es la observación más honesta de esta tanda sobre el design de
amdgpu.

**⇒ `connector_signal` no es una verdad física: es una pista de enrutamiento, y un
puente DP se disfraza de DP para que el código existente funcione.** Eso explica por
qué existe `dc_connection_analog_load` en `152` y por qué `signal_type` e
identidad física son cosas distintas.

**Y hay un tercer filtro, más adelante** (`L762-771`), que cruza la señal con el
tipo de dispositivo que declara el firmware:

```c
                if (link->device_tag.dev_id.device_type == DEVICE_TYPE_CRT &&
                    link->connector_signal != SIGNAL_TYPE_RGB &&
                    link->ext_enc_id.id == ENCODER_ID_UNKNOWN)
                        continue;
                if (link->device_tag.dev_id.device_type == DEVICE_TYPE_LCD &&
                    link->connector_signal == SIGNAL_TYPE_RGB)
                        continue;
```

**Un CRT se descarta si la señal no es RGB, y un LCD se descarta si la señal es
RGB.** **⇒ El tipo de señal y el tipo de dispositivo declarado por el firmware tienen
que estar de acuerdo, y si no, el camino se descarta.** `PROVEN_DERIVED`.

**⇒ El valor final de `connector_signal` es el resultado de tres filtros
sucesivos — el `switch` del id, la sobreescritura por puente DP, y la coherencia con
el tipo de dispositivo — no de una decisión.** `PROVEN_DERIVED`.

## 4 · Y se registra

```c
        LINK_INFO("Connector[%d] description: signal: %s\n",
                  init_params->connector_index,
                  signal_type_to_string(link->connector_signal));
```

**El driver imprime el conector, su índice y la señal resuelta, con la función
`signal_type_to_string` de `150`.** Es un punto de observación del log del DC, si el
logging está activo. `PROVEN`.

## 5 · La confirmación de `153`, por una vía independiente

`153` derivó que `object_enum_id` es el índice de la ruta de display **contando que
hay siete `ENUM_ID_*` y comparándolo con `MAX_NUMBER_OF_EXT_DISPLAY_PATH 7`**.

**Y la búsqueda del mapa de carriles, en `L785-790`, compara los tres campos en este
orden:**

```c
                if (path->device_connector_id.enum_id == link->link_id.enum_id &&
                    path->device_connector_id.id      == link->link_id.id &&
                    path->device_connector_id.type    == link->link_id.type) {
                        link->ddi_channel_mapping = path->channel_mapping;
```

**`enum_id` es el primer campo de la comparación, y es el que empareja una ruta del
firmware con un enlace.** **Dos derivaciones independientes del mismo hecho —una por
recuento de valores, otra por orden de comparación en la búsqueda— y coinciden.**
`PROVEN_DERIVED`, y esa es la clase de corroboración que `140` degradó a
`CORROBORATED` por venir de una sola fuente; aquí son dos.

**Y `153` también acertó en que el mapa viene de la tabla de firmware**: la línea
`DC_LOG_DC("BIOS object table - ddi_channel_mapping: 0x%04X", ...)` lo dice con
esas palabras, dos veces, en `L792-793` y `L800-801`.

## Lo que NO cierra

| afirmación | estado |
|---|---|
| El `switch` está en `link_factory.c:626-671`, en `construct_phy` | `PROVEN` |
| El `switch` es sobre `link->link_id.id` | `PROVEN` |
| `link_id` viene de `bios->funcs->get_connector_id` | `PROVEN` |
| 9 casos colapsan en 6 señales | `PROVEN` (por recuento) |
| 17 `CONNECTOR_ID_*`, numeración dispersa | `PROVEN` (por programa) |
| 5 ids sin caso en el `switch` | `PROVEN` |
| El driver distingue DVID de DVII y colapsa ambos | `PROVEN` |
| La sobreescritura por puente DP está justificada en el código | `PROVEN` |
| La coherencia con el tipo de dispositivo filtra caminos | `PROVEN_DERIVED` |
| El resultado son tres filtros sucesivos | `PROVEN_DERIVED` |
| La decisión se registra con `signal_type_to_string` | `PROVEN` |
| `enum_id` es la ruta, por vía independiente | `PROVEN_DERIVED` |
| **`connector_signal` se decide aquí — cerrado desde `150`** | **`PROVEN_DERIVED`** |
| Cuál es el `connector_index` de esta placa | **`NOT_DETERMINED`** — se lee del BIOS |
| Cuántos de los 7 paths existen aquí | **`NOT_DETERMINED`** — firmware |
| `get_connector_id` y su tabla | **`NOT_IN_CORPUS`** — la tabla está en el firmware |
| Los `ENCODER_ID_*` distintos de `UNKNOWN` | **`NOT_IN_CORPUS`** |
| Si esta placa tiene DP, HDMI, VGA o LVDS | **`NOT_DETERMINED`** |

**Las dos primeras filas abiertas son la misma cosa, y las dos se leen del BIOS de la
placa: cuántos conectores hay y de qué tipo.** Y eso es un `RREG32` sobre una tabla
que no está en el corpus, o el log del DC si el logging está activo.

**Y la cuarta es `NOT_IN_CORPUS` en el sentido fuerte de `145`:** el
`get_connector_id` del BIOS devuelve un valor cuya tabla no existe en este corpus, y
por eso el paso 2 de la cadena no se puede derivar — sólo se puede leer del firmware.

## Procedencia

- `STATIC` -- `display/dc/link/link_factory.c:487-530` (firma y cuerpo inicial de
  `construct_phy`), `:518-519` (`get_connector_id`), `:596-672` (el `switch` y sus
  casos, más el `switch` de HPD de eDP), `:713-724` (la sobreescritura y el
  `LINK_INFO`), `:760-775` (el filtro de tipo de dispositivo), `:782-801` (la
  búsqueda del mapa de carriles y sus dos `DC_LOG_DC`),
  `display/dc/link/link_factory.c:917-925` (`link_construct`),
  `display/dc/link/link_factory.c:850` (`construct_dpia`),
  `display/dc/link/link_factory.c:927-944` (`link_create` y `kzalloc_obj`),
  `display/include/grph_object_id.h:227-232` (de `153`),
  `display/include/signal_types.h:34-45` y `:47-73` (de `150`).
- Recuentos por programa: los 17 `CONNECTOR_ID_*` con su valor, ordenados; el
  recuento de casos del `switch` frente al de señales resultantes; la identificación
  de los cinco ids sin caso.
- Encadenada con `153` (el identificador de objeto y la ruta del firmware, **confirmado
  por vía independiente**), `152` (los dos campos del enlace, y por qué
  `connector_signal` es una pista y no una verdad), `151` (los límites del DC, y el
  `kzalloc` que responde por el `false` de `using_dml2`), `150` (la enumeración de
  diez valores, **con este `NOT_DETERMINED` cerrado**), `149` (la frontera DM→DC).
- No se editó `AGENTS.md` ni `OPEN-FRONTIERS.md`.

## Nota de método

**Cinco notas rodeando un `switch`.** El nombre correcto del campo apareció en `152`
—`connector_signal`— y a partir de ahí la búsqueda era una línea. Lo que faltaba no
era el nombre: era **leer el fichero entero en vez de grepearlo**, que es la misma
condición que `148` sufrió, y que `154` ha cumplido por quinta repetición de la
misma instrucción.

*Y hay un detalle de la búsqueda que salió solo y que merece quedarse: cuando por fin
miré la lista de funciones del fichero, `link_construct` —el nombre que buscaba— resultó
ser un despachador de cinco líneas, y la función que hace el trabajo se llama
`construct_phy` y ocupa 363.* **El nombre que se busca por descripción rara vez es la
función que lo hace.** `link_construct` suena a "construir el enlace" y sólo elige
entre dos caminos; la que rellena 363 líneas de campos se llama `construct_phy` y su
nombre habla de hardware, no de software.

**Y la lección de fondo sigue siendo la de `153`, y esta nota la confirma por partida
doble:** los identificadores se leen en su definición, se cuentan, y se comprueban
contra la anchura que declaran. *Esta vez el identificador no es una estructura sino
un `switch`, y el mismo método —leer el bloque entero, contar los casos, cruzar el
recuento con el del otro sitio— es el que lo cierra.*
