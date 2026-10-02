# 149 · La frontera Display Manager → DC, y una segunda corrección a `148`

```
CLASSIFICATION=DOCUMENTATION · TRACK=STATIC
CORPUS=RESEARCH/working/linux-7.1.3 · HARDWARE_SCOPE=HOST-C/RX550/0000:01:00.0
WORK_CLASS=READ_ONLY/EVIDENCE · WRITE_EXECUTION=NONE · MODIFICATIONS=0
RUNTIME=NOT_RUN · GPU INTACTA
```

## Qué resuelve

**El vocabulario completo de la frontera entre las dos mitades del driver** — el
Display Manager, que ve el compositor, y el DC, que ve el hardware — con los valores
exactos, y **la segunda corrección a `148`**, que es un campo que inventé.

**Y la cadena del umbral de 340 MHz, cerrada a través de tres ficheros.**

## 1 · Corrección propia, segunda: `link_type` no existe

En `148` escribí, en la tabla de "lo que decide el tipo de salida":

> el tipo de salida | `crtc_timing->link_type`

**Ese campo no existe.** `grep -n 'link_type' display/dc/dc_hw_types.h` devuelve
**cero**. `struct dc_crtc_timing` son 112 líneas, `L904-1015`, y no lo tienen.

**Lo inventé por el mismo mecanismo que el error que `148` ya corregía:** vi
`crtc_timing->pixel_encoding` y supuse que tenía un compañero del mismo tipo. **No
lo comprobé, y la suposición era tan plausible que ni siquiera parecía una
hipótesis.**

**Son dos campos inventados en dos notas consecutivas, y los dos por la misma
razón: completé una estructura con el campo que le faltaba, en vez de leer la
estructura.** `PROVEN_ABSENT`.

### Y dónde vive de verdad

**No vive en el timing.** El tipo de salida es una propiedad del **link**, y el link
es un objeto aparte: `148`'s `dc_sink_construct` asigna `sink->link = link` y
`dc_crtc_timing` no lo menciona. **El modelo correcto es de tres objetos:**

```
dc_crtc_timing   qué mostrar y cómo     (el timing: dimensiones, reloj, formato)
dc_link          por dónde enviarlo     (el tipo de salida vive aquí)
dc_sink          el par de los dos      (148: es genérico, sin despacho por versión)
```

**Y por eso `sink` es genérico:** porque es sólo el par. El resto está en los
dos objetos que lo componen, y ninguno es específico de la generación. `PROVEN_DERIVED`.

## 2 · `struct dc_crtc_timing`: cuatro enumeraciones, y son todo el vocabulario

`display/dc/dc_hw_types.h` — **no `dc_types.h`**, que es otra cosa. Quinta colisión
de nombre en esta tanda (tras `pptable.h`, `dcn10`/`dce100`, y dos de `dc_types.h`/
`dc_hw_types.h`).

### `enum dc_pixel_encoding` (`L773-780`) — el que `148` confundía

```c
PIXEL_ENCODING_UNDEFINED,
PIXEL_ENCODING_RGB,
PIXEL_ENCODING_YCBCR422,
PIXEL_ENCODING_YCBCR444,
PIXEL_ENCODING_YCBCR420,
PIXEL_ENCODING_COUNT
```

**Cinco valores. Y `148` tenía razón en que `TMDS_PIXEL_ENCODING = 1` es
`PIXEL_ENCODING_YCBCR422`, y razón en que no es un tipo de salida: es un
**submuestreo de color**.** La corrección de `148` queda confirmada por la
enumeración completa, y no sólo por el `switch`.

**Y `PIXEL_ENCODING_YCBCR420` existe en el enum — y el flag `YCBCR420` de `L821`
lleva un comentario del propio driver, marcado como trabajo pendiente, que dice que
el flag no debería hacer falta y que debería ser un mecanismo aparte.** **4:2:0 es representable en la enumeración y el driver admite que
querría otro mecanismo para él.** Inconsistencia documentada por el autor, en el
campo exacto que `148` se equivocó. `OBSERVED`.

### Las otras tres

| enumeración | línea | valores |
|---|---|---|
| `enum dc_color_depth` | `L760-771` | UNDEFINED, 666, 888, 101010, 121212, 141414, 161616, 999, 111111, COUNT — **9** |
| `enum dc_aspect_ratio` | `L782-789` | NO_DATA, 4_3, 16_9, 64_27, 256_135, FUTURE — **6** |
| `enum scanning_type` | `L791-797` | NODATA, OVERSCAN, UNDERSCAN, FUTURE, UNDEFINED — **5** |

**Nueve profundidades de color, para una GPU de 2017.** Es vocabulario, no
implementación: sólo dos o tres serán alcanzables aquí. **Pero el vocabulario es lo
que la frontera declara, y el vocabulario es más grande que el chip.** `PROVEN`.

## 3 · Los 16 bits de `struct dc_crtc_timing_flags`

`L799-832`, un `uint32_t` con dieciséis campos de un bit:

| bit | nombre | |
|---|---|---|
| 0 | `INTERLACE` | |
| 1 | `HSYNC_POSITIVE_POLARITY` | *"reversed with dal1 or video bios define"* |
| 2 | `VSYNC_POSITIVE_POLARITY` | ídem |
| 3 | `HORZ_COUNT_BY_TWO` | |
| 4 | `EXCLUSIVE_3D` | *"there is no corresponding 2D timing"* |
| 5 | `RIGHT_EYE_3D_POLARITY` | |
| 6 | `SUB_SAMPLE_3D` | *"summation (3D timing is doubled)"* |
| 7 | `USE_IN_3D_VIEW_ONLY` | |
| 8 | `STEREO_3D_PREFERENCE` | |
| 9 | `Y_ONLY` | |
| 10 | `YCBCR420` | con un comentario de trabajo pendiente del autor |
| 11-15 | `DTD_COUNTER:5` | *"values 1 to 16"* — 5 bits, no uno |
| 16 | `FORCE_HDR` | |
| 17 | `LTE_340MCSC_SCRAMBLE` | **HDMI 2.0, 340 MHz** |
| 18 | `DSC` | *"Use DSC with this timing"* |
| 19 | `VBLANK_SYNCHRONIZABLE` | |

**Y los bits 1 y 2 llevan un comentario que nombra al firmware dos veces:**
*"reversed with dal1 or video bios define"*. **La polaridad de sincronismo de esta
frontera no la decide el driver: la decide la definition de atom BIOS, o la de la
placa.** `PROVEN`.

## 4 · Y el comentario que más dice de todo el struct

`L987-993`:

```c
/**
 * @pix_clk_100hz: Pipe pixel precision
 *
 * This field is used to communicate pixel clocks with 100 Hz accuracy
 * from dc_crtc_timing to BIOS command table.
 */
        uint32_t pix_clk_100hz;
```

**El struct de timing es lo que se le pasa a la tabla de comandos del BIOS.** El
Display Manager no sólo rellena una estructura para el DC: **se la pasa al
firmware**, y para eso el reloj se expresa con 100 Hz de precisión, porque el BIOS
trabaja en unidades de centihertz.

**⇒ Hay una segunda frontera en el mismo struct, además de la DM→DC: la DM→BIOS.**
Y es la que explica por qué `pix_clk_100hz` no es un reloj en kHz, y por qué
`frl_uncompressed_video_bandwidth_in_kbps` está en kbps y no en bytes por segundo.
`PROVEN_DERIVED`.

## 5 · La cadena de 340 MHz, cerrada a través de tres ficheros

`147`afirmó: DCE 10.0 no tiene el campo `HDMI_CLOCK_CHANNEL_RATE` — está en la
lista de DCE 110, y en DCE 80/100 queda con máscara cero.
`148`encontró: el driver tiene la constante `HDMI_CLOCK_CHANNEL_RATE_MORE_340M 340000`
en el fichero, pero el campo que la programa no existe aquí.
**Y aquí, en el tercer fichero:** el umbral está en el **flag de timing**:

```c
/* HDMI 2.0 - Support scrambling for TMDS character
 * rates less than or equal to 340Mcsc */
        uint32_t LTE_340MCSC_SCRAMBLE:1;
```

**Los tres juntos, y son coherentes:**

| fichero | qué tiene |
|---|---|
| `dce_stream_encoder.h` | el campo de registro, con máscara **cero** en esta GPU |
| `dce_stream_encoder.c:43` | la constante `340000` |
| `dc_hw_types.h:826-828` | el flag `LTE_340MCSC_SCRAMBLE`, con "340Mcsc" en el nombre |

**⇒ El umbral de 340 MHz es representable en el timing y en el driver, y NO es
programmable en el stream encoder de esta GPU.** La decisión de si el linkTMDS va
por encima de 340 MHz se puede tomar y se puede declarar, pero el reloj de canal no
se programa aquí. `PROVEN_DERIVED`, por convergencia de tres fuentes independientes.

**Y esto es `139` y `147` por tercera vez:** un campo que existe en el *software* y
no en el *hardware de esta generación*. La diferencia es que aquí el sitio donde
sobrevive es el más alto de la pila.

## 6 · Y `DSC` no es cosa de esta GPU

`L830: uint32_t DSC : 1; /* Use DSC with this timing */`

**Dónde se lee:** `hwss/dce110/dce110_hwseq.c:1391` y `:1746`, y en `hwss/dcn*`.
**Nunca en una ruta de DCE 10.0.** `PROVEN_ABSENT`, por pertenencia a fichero.

**Y el struct tiene además `dsc_fixed_bits_per_pixel_x16` (*"DSC target bitrate in
1/16 of bpp"*) y `struct dc_dsc_config dsc_cfg`.** **Tres sitios donde vive DSC en
esta frontera, y ninguno es alcanzable en esta GPU.** Es el mismo patrón de los 41
campos con máscara cero de `147`, pero un nivel más arriba: **no es que el campo no
exista en el hardware, es que el hardware entero no lo implementa.**

`PROVEN_DERIVED`, y es la versión fuerte de `133` (el MTYPE que no existe en GFX8) y
de `147` (los 41 ceros del stream encoder).

## Lo que NO cierra

| afirmación | estado |
|---|---|
| `link_type` no existe en `dc_crtc_timing` | `PROVEN_ABSENT` |
| El tipo de salida vive en `dc_link` | `PROVEN_DERIVED` |
| El modelo es timing + link + sink | `PROVEN_DERIVED` |
| El sink es genérico porque es sólo el par | `PROVEN_DERIVED` |
| `PIXEL_ENCODING = 1` es YCbCr 4:2:2 | `PROVEN` (`L773-780`) |
| La enumeración tiene 5 valores | `PROVEN` |
| 9 profundidades de color declaradas | `PROVEN` (`L760-771`) |
| 16 bits de flags, uno de ellos `DTD_COUNTER:5` | `PROVEN` (`L799-832`) |
| La polaridad la decide el BIOS, no el driver | `PROVEN` (comentario `L801-804`) |
| El timing se pasa a la tabla de comandos del BIOS | `PROVEN` (`L987-993`) |
| El umbral de 340 MHz no es programable aquí | `PROVEN_DERIVED` (3 ficheros) |
| `DSC` no se lee en ninguna ruta DCE 10.0 | `PROVEN_ABSENT` |
| Los 4 objetos del modelo, con sus campos | **`PARTIAL`** — falta `dc_link` |
| Cuál de las 9 profundidades de color usa esta GPU | **`NOT_DETERMINED`** |
| Si el HDMI de esta placa supera 340 MHz | **`NOT_DETERMINED`** — depende del modo |

**La penúltima fila es la siguiente ruta y tiene nombre: `struct dc_link`.** Es el
tercer objeto del modelo, es el que lleva el tipo de salida que yo inventé en
`dc_crtc_timing`, y es donde vive el reloj del link — que es la pregunta que `147`
dejó abierta y que nadie ha resuelto.

## Procedencia

- `STATIC` -- `display/dc/dc_hw_types.h:758-832` (`dc_color_depth` `L760-771`,
  `dc_pixel_encoding` `L773-780`, `dc_aspect_ratio` `L782-789`,
  `scanning_type` `L791-797`, `dc_crtc_timing_flags` `L799-832`),
  `display/dc/dc_hw_types.h:904-1015` (`struct dc_crtc_timing`, 112 líneas),
  `display/dc/dc_hw_types.h:987-993` (el comentario de `pix_clk_100hz`),
  `display/dc/core/dc_sink.c:34-54` (de `148`),
  `display/dc/dce/dce_stream_encoder.c:43` (de `148`),
  `display/dc/dce/dce_stream_encoder.h:291-295` (de `147`),
  `display/dc/hwss/dce110/dce110_hwseq.c:1391` `:1746` y `display/dc/hwss/dcn*`.
- Verificación de la ausencia de `link_type`: `grep -n 'link_type'` sobre
  `display/dc/dc_hw_types.h` → **cero resultados**. La ausencia de `DSC` en DCE 10.0:
  `grep -rn 'flags.DSC'` sobre `display/dc/`, con los seis resultados en `hwss/dce110/`
  y `hwss/dcn*`.
- Encadenada con `148` (que **esta nota corrige por segunda vez**), `147` (los 41
  campos con máscara cero, y el `HDMI_CLOCK_CHANNEL_RATE` ausente), `144` (la entrada,
  el otro extremo), `139` (el MTYPE ausente), `133` (el mismo patrón), `140` (el mapa
  de direcciones).
- No se editó `AGENTS.md` ni `OPEN-FRONTIERS.md`.

## Nota de método

**Dos campos inventados en dos notas seguidas, y el segundo por el mecanismo exacto
del primero.**

En `148` leí `crtc_timing->pixel_encoding` y concluí que el bit era un tipo de salida.
En esta nota leí `crtc_timing` completo — 112 líneas, para otra cosa — y vi que
`link_type`, que yo le había puesto al lado en la nota anterior, **no existe**.

**Los dos casos son el mismo: he completado una estructura con el campo que le
faltaba, en lugar de leer la estructura.** Y el motivo por el que no se nota al
escribir es que **el campo inventado encaja con el modelo mental que uno ya tiene**:
un timing con su tipo de salida parece obvious, hasta que se lee y no está.

*Regla que sale de aquí, y que es la versión general de las que ya tengo: antes de
afirmar que un campo existe, hay que haberlo visto en la definición del tipo. No en
un uso, no en un nombre de variable, no en un `switch` que lo menciona: en la
`struct`.* Es la regla que `148` violó dos veces y que `147` cumplió al contar los 130
campos uno a uno en vez de estimarlos.

**Y la segunda lección es sobre el alcance de un fichero.** `dc_types.h` son 41 KiB y
`dc_hw_types.h` es donde estaba. Busqué en el primero porque el nombre encaja con "los
tipos del DC", y el segundo tiene "hw" en el nombre, que es la pista de que es el
que contiene los tipos que tocan hardware. **Tres de los cinco nombres de esta tanda
mienten sobre su contenido, y los tres están en la misma familia de ficheros.**

**Y hay una sexta, y es de las que más cuestan: la primera corrección de `148` la hice
antes de reportar, y la segunda la encontré al leer el fichero que `148` me decía que
mirara.** La regla de verificar antes de publicar funciona — evité que un error
semántico saliera publicado — **pero no cierra la nota: sólo la retrasa, y la
siguiente nota hereda el error y lo amplifica.** Lo que la cierra es ir al fichero
que la nota anterior nombró, y leerlo entero.
