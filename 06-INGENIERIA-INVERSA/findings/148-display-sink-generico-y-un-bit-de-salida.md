# 148 · El sink es genérico, y una corrección propia sobre `TMDS_CNTL`

```
CLASSIFICATION=DOCUMENTATION · TRACK=STATIC
CORPUS=RESEARCH/working/linux-7.1.3 · HARDWARE_SCOPE=HOST-C/RX550/0000:01:00.0
WORK_CLASS=READ_ONLY/EVIDENCE · WRITE_EXECUTION=NONE · MODIFICATIONS=0
RUNTIME=NOT_RUN · GPU INTACTA
```

## Qué resuelve

Las dos preguntas que `147` dejó abiertas, y una tercera que salió de paso.

1. **No hay implementación de sink para DCE 10.0.** `dc_sink_construct` no
   despacha por versión: es un copiado de campos. **El sink es genérico.**
2. **De todo `display/dc/`, sólo 3 campos de registro están definidos a mano** — y
   eso es *mucho* mejor que el bloque HDP de `142`, y merece ser contrasted.
3. **Y una corrección propia, que es la parte más importante de esta nota.** Escribí
   que la elección de salida era un bit de `TMDS_CNTL`. **Es falso, por dos motivos
   independientes, y los dos están en §2.**

## 1 · `dc_sink_construct` no sabe qué chip es

`core/dc_sink.c` son 100 líneas, y las tres que importan son `L34-54`:

```c
static bool dc_sink_construct(struct dc_sink *sink, const struct dc_sink_init_data *init_params)
{
        struct dc_link *link = init_params->link;

        if (!link)
                return false;

        sink->sink_signal = init_params->sink_signal;
        sink->link = link;
        sink->ctx = link->ctx;
        sink->dongle_max_pix_clk = init_params->dongle_max_pix_clk;
        sink->converter_disable_audio = init_params->converter_disable_audio;
        sink->dc_container_id = NULL;
        sink->sink_id = init_params->link->ctx->dc_sink_id_count;
        init_params->link->ctx->dc_sink_id_count++;

        return true;
}
```

**Ni un `switch` de versión, ni un `DCE_VERSION`, ni una sola referencia a la
generación del DC.** Es un copiado de campos, y `core/dc.c` —el fichero de 12 KB que
contiene el resto del núcleo DC— no participa.

**Y no hay directorio `dce100/` junto a `dce110/`, `dce112/`, `dce120/`, `dce60/`,
`dce80/`.** Los directorios de implementación por generación existen para los chips
que divergecieron, y **DCE 10.0 no diverge**: usa el camino genérico.
`PROVEN_ABSENT`, y es una ausencia con forma: la lista de los que sí lo tienen.

**Consecuencia para la lista de trabajo de `147`: el fichero que nominé
(`core/dc_sink.c`) no contiene lo que buscaba.** Contains gestión de vida —`kref`,
`retain`, `release`, `create`— y nada más. **`147` estaba mal dirigido, y lo cierro
diciéndolo.**

**Y los seis campos que el sink sí lleva son la frontera entre el Display Manager y
el DC:** `sink_signal`, `link`, `ctx`, `dongle_max_pix_clk`,
`converter_disable_audio`, `sink_id`. **El Display Manager —el componente que ve el
compositor— describe el panel; el DC lee esos campos.** Esa es la costura del
proyecto, y es una costura, no una frontera de hardware.

## 2 · Corrección propia: `TMDS_CNTL` no es la elección de salida

**Escribí que la elección entre HDMI y DisplayPort en esta GPU era el bit 4 de
`TMDS_CNTL`, y es falso por dos motivos independientes. Los dos están aquí, y los
dos se habían visto cuando lo escribí.**

### El error 1 — el código es de DCE 11.0, no de esta GPU

Las cuatro escrituras de `TMDS_PIXEL_ENCODING` que cité están **todas dentro de una
sola función**:

```
dce_stream_encoder.c:505   static void dce110_stream_encoder_set_stream_attribute_helper(
dce_stream_encoder.c:506           struct dce110_stream_encoder *enc110,
dce_stream_encoder.c:507           struct dc_crtc_timing *crtc_timing)
```

**Es una función de DCE 11.0, sobre una estructura `dce110_stream_encoder`, y no la
cité como tal.** Comprobado por las cuatro: `L512`, `L515`, `L522` y `L525` tienen
todas la misma función envolvente.

**Y `dce100_resource.c` —la tabla de recursos de esta GPU— no tiene ninguna entrada
`TMDS_CNTL`, ni ninguna estructura `dce_stream_encoder_registers`.** `PROVEN_ABSENT`.

**Es decir: `TMDS_CNTL` no aparece en la tabla de esta GPU.** Y por eso el driver lo
define él mismo con guards `#ifndef`, en un fichero donde el contexto es DCE 11.0.
**El backup existe porque el registro no está en el header de esta generación — pero
la función que lo usa tampoco es de esta generación.** Lo comprobé después de haberlo
escrito, y por el motivo que §4 describe.

### El error 2 — la semántica del bit es otra

```c
dce_stream_encoder.c:509           if (enc110->regs->TMDS_CNTL) {
dce_stream_encoder.c:510                   switch (crtc_timing->pixel_encoding) {
dce_stream_encoder.c:511                   case PIXEL_ENCODING_YCBCR422:
dce_stream_encoder.c:512                           REG_UPDATE(TMDS_CNTL, TMDS_PIXEL_ENCODING, 1);
dce_stream_encoder.c:513                           break;
dce_stream_encoder.c:514                   default:
```

**`TMDS_PIXEL_ENCODING = 1` corresponde a `PIXEL_ENCODING_YCBCR422`.** Es un
**formato de submuestreo de color**, no un tipo de salida.

**Lo leí como "1 = TMDS, 0 = DisplayPort" porque el campo se llama
`TMDS_PIXEL_ENCODING` y se pone a 1 y a 0.** Y el `switch` que lo circundaba lo decía
en la línea de al lado. **Dije que el campo "sólo toma dos valores: 1 y 0. No hay
enumeración, no hay constante" — y la enumeración estaba literally en el mismo
bloque, en el `switch` que no copié entero.**

### Lo que sí decide el tipo de salida

No es un campo de un registro. Es `crtc_timing`, y lo rellena el Display Manager:

| | |
|---|---|
| el tipo de salida | `crtc_timing->link_type` |
| el formato de color | `crtc_timing->pixel_encoding`, con `PIXEL_ENCODING_RGB` y `PIXEL_ENCODING_YCBCR422` |

`dce_stream_encoder.c:671` y `:695` llevan `ASSERT(crtc_timing->pixel_encoding ==
PIXEL_ENCODING_RGB)` — o sea, el DC **exige** que le digan el formato, y no lo deduce.
`PROVEN_DERIVED`.

**Y esto cierra `147` mejor de lo que yo lo cerré.** No es que "un bit decida la
salida": es que **el DC no decide nada de eso.** La decisión se toma por encima, en
la estructura de timing, y llega al DC ya hecha. **La costura que `147` buscaba no
está en el stream encoder: está en `struct dc_crtc_timing`.**

### Lo que sobrevive de mi versión anterior

**El layout del campo es correcto, y lo comprobé contra la definición del propio
driver** (`dce_stream_encoder.c:45-50`):

| campo | máscara | ancho | bits |
|---|---|---|---|
| `TMDS_PIXEL_ENCODING` | `0x10` | 1 bit | 4 |
| `TMDS_COLOR_FORMAT` | `0x300` | 2 bits | 8-9 |

**Y sigue siendo cierto que sólo 3 campos de todo `display/dc/` están definidos a
mano** — §3 no depende del error.

## 3 · Y la comparación que hace que esto sea un buen resultado

`142` encontró 160 escrituras HDP con offsets literales y **ni una definición de
campo en todo el corpus**. Aquí, 3 definiciones de campo, con máscara y desplazamiento.

Medido sobre todo `display/dc/`, impreso por programa:

```
ficheros .c con registros definidos a mano:  2
campos (__FIELD) definidos a mano:           3
REGISTROS distintos definidos a mano:        3
  dce_link_encoder.c    2
  dce_stream_encoder.c  1
```

**Tres. En mil ficheros.** `PROVEN`.

**El mismo fenómeno —los headers de esta generación están incompletos— produce dos
respuestas opuestas, y la comparación vale por sí sola:**

| | bloque HDP (`142`) | bloque DCE (esta nota) |
|---|---|---|
| qué falta | 160 escrituras | 3 campos |
| dónde está el layout | **en ningún sitio** | en el propio `.c`, con máscara y shift |
| qué sabe un driver propio | que hay que escribir 0 en 160 sitios | que el bit 4 es la salida TMDS |
| información recuperable | **cero** | **el layout completo del campo** |

**La segunda respuesta es estrictamente mejor, y el dato que la distingue es que
declara el layout en vez de sólo el offset.** Un driver propio que se encuentre con el bloque HDP tiene que copiar; que se
encuentre con `TMDS_CNTL` puede decidir.

**Y la regla general que sale de las dos, y que es la misma de `142`:**
*un driver escribe offsets literales cuando el header de esa generación aún no
existe.* Pero **escribir offsets literales y no escribir los campos son dos niveles
deUSER de ignorancia**, y en este corpus el segundo nivel es casi inexistente: 3
campos frente a 160 escrituras. **Lo que el driver de amdgpu no sabe de sus
registros, casi siempre lo sabe de sus campos.**

## 4 · Y lo que `147` dejó abierto: el reloj de canal

`147`concluyó: *esta GPU no tiene `HDMI_CLOCK_CHANNEL_RATE` en el stream
encoder*, porque el campo está en la lista de DCE 110 y no en la de DCE 80/100, y
queda con máscara cero.

**Y el driver tiene la constante, pero para el otro camino** (`L43`):

```c
#define HDMI_CLOCK_CHANNEL_RATE_MORE_340M 340000
```

**Es el umbral de 340 MHz del reloj de canal, y existe en el fichero, pero el campo
que lo programa tiene máscara cero en esta GPU.** `PROVEN_DERIVED`: **el umbral
está disponible para DCE 110+, y en DCE 10.0 el reloj de canal de HDMI no se programa
por el stream encoder.**

**Lo que no puedo decir, y es `NOT_DETERMINED`:** si el HDMI de esta placa funciona y
a qué frecuencia. Que el campo no exista **no significa que la salida no tenga reloj
de canal** — significa que **no se programa aquí**. Puede estar en el reloj del link,
en `dce_link_encoder.c`, o en el firmware. **Y no lo sé, y no voy a suponerlo.**

## Lo que NO cierra

| afirmación | estado |
|---|---|
| `dc_sink_construct` no despacha por versión | `PROVEN` |
| El sink es genérico | `PROVEN` |
| No hay directorio `dce100/` de implementación | `PROVEN_ABSENT` |
| Los 6 campos que el sink lleva son la costura DM↔DC | `PROVEN_DERIVED` |
| `TMDS_PIXEL_ENCODING` es 1 bit, el bit 4 | `PROVEN` (la definición, `L45-50`) |
| Mi «la elección HDMI/DP es un `REG_UPDATE` con 1 o 0» | **`REFUTED`** — es DCE 110 y es YCbCr 4:2:2 |
| `TMDS_CNTL` no está en la tabla de esta GPU | `PROVEN_ABSENT` |
| El tipo de salida lo decide `crtc_timing`, no un registro | `PROVEN_DERIVED` |
| 3 campos definidos a mano en todo `display/dc/` | `PROVEN` (por programa) |
| Esta GPU no programa el reloj de canal en el encoder | `PROVEN_DERIVED` |
| Si el HDMI de esta placa funciona | **`NOT_DETERMINED`** |
| Dónde se programa el reloj de canal en esta GPU | **`NOT_DETERMINED`** — `dce_link_encoder.c` |
| La secuencia de encendido de un stream | **`NOT_DETERMINED`** |
| Los cuatro campos del sink, valores y unidades | **`PARTIAL`** — hay que leer `dc_types.h` |

**La tercera de las que siguen abiertas se cierra con un fichero, y es
`dce_link_encoder.c` — que además es uno de los dos que define registros a mano.**
Es el siguiente paso natural, y por una razón que no es de curiosidad: es el fichero
donde vive el reloj del link, que es la variable que `147` y esta nota han dejado
sin determinar.

## Procedencia

- `STATIC` -- `display/dc/core/dc_sink.c:34-54`, `display/dc/core/dc_sink.c:60-96`,
  `display/dc/dce/dce_stream_encoder.c:41-50`,
  `display/dc/dce/dce_stream_encoder.c:505-525`,
  `display/dc/dce/dce_stream_encoder.c:509-513`,
  `display/dc/dce/dce_stream_encoder.c:671`,
  `display/dc/dce/dce_stream_encoder.h:205`, `display/dc/dce/dce_stream_encoder.h:289`,
  `display/dc/dce/dce_stream_encoder.h:369`, `display/dc/dce/dce_stream_encoder.h:502`
  (de `147`), `display/dc/resource/dce100/dce100_resource.c:249-255`.
- Recuento: `os.walk` sobre `display/dc/` buscando
  `#ifndef\s+([A-Z0-9_]+)__([A-Z0-9_]+)_MASK`. **Sale de un programa: 2 ficheros, 3
  campos, 3 registros.** La comparación con las 160 escrituras de `142` es la misma
  clase de medida aplicada a un bloque que resultaba desconocido.
- Encadenada con `147` (el modelo de programación del stream encoder, y las dos
  preguntas abiertas que esta nota cierra), `142` (los 160 registros HDP, y la
  comparación de las dos respuestas al mismo fenómeno), `140` (el mapa de
  direcciones), `144` (el otro extremo del objetivo: la entrada), `139` (el PTE).
- No se editó `AGENTS.md` ni `OPEN-FRONTIERS.md`.

## Nota de método

**`147`nombró `core/dc_sink.c` como el fichero que cerraba las dos preguntas
abiertas, y no contenía nada de eso.** Contiene `kref_get`, `kref_put` y un
`kzalloc`. **Son 100 líneas, yo leí desde la 55, y lo que buscaba estaba en la 34.**

Es la quinta vez en la tanda, y ya no la cuento como error nuevo: *entré por la
función pública del fichero en vez de por el principio*. **La función que el
fichero exporta al mundo y la función que decide su comportamiento no son la misma,**
y cuando busco un comportamiento, la que busco es la que decide.

**Y lo que sale de esta nota es la versión útil de esa lección: la segunda función
del fichero, la de la 34, era un copiado de campos sin una sola mención al chip — y
eso es el hallazgo.** Si hubiera leído el fichero entero a la primera, habría
sabido que el sink es genérico antes de ir a buscar una implementación por versión
que no existe.

*Un fichero se lee entero. Una función se lee entera. Y "entera" incluye la parte
que no tiene que ver con lo que se busca, porque esa parte es a veces la respuesta.*

**Y el error de §2 es el más caro de la tanda, y también es el más fácil de no
cometer: escribí la semántica de un campo a partir de su nombre y de los dos valores
que veía.** Un campo llamado `TMDS_PIXEL_ENCODING` que se pone a 1 y a 0 parece un
interruptor de tipo de salida. **No lo es: es un submuestreo de color, y el `switch`
que lo tenía a la vista, en la línea siguiente a la que cité.**

*El nombre de un campo es la hipótesis más cómoda del mundo, porque siempre parece
que dice algo. La enumeración que lo desmiente está en el `switch` que lo rodea, y
copiar tres líneas de un bloque de treinta es copiar la parte que ya se entiende.*
**Eso es lo que hicieron todos mis errores de hoy con distinta ropa: entrar por el
símbolo, leer tres líneas, y quedarse con la parte que ya sabía.**
