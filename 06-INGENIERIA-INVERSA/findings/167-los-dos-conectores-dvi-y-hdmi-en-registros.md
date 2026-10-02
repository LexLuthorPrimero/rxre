# 167 · Los dos conectores que existen: 4 carriles el HDMI, 8 el DVI de doble enlace

```
CLASSIFICATION=DOCUMENTATION · TRACK=STATIC
CORPUS=RESEARCH/working/linux-7.1.3 · HARDWARE_SCOPE=HOST-C/RX550/0000:01:00.0
WORK_CLASS=READ_ONLY/EVIDENCE · WRITE_EXECUTION=NONE · MODIFICATIONS=0
RUNTIME=NOT_RUN · GPU INTACTA
```

## Qué resuelve

**Los registros concretos que escriben los dos conectores que esta placa tiene, y la
resolución completa de las tres afirmaciones de `148`** — dos confirmadas, una con la
evidencia rehecha.

**Y un número que `160` dejó suelto: el `LANE_COUNT_EIGHT` del enum no es un valor
muerto, es el DVI de doble enlace.**

## 1 · Los cuatro setters, y lo que pide cada uno al BIOS

Los cuatro de `157`, con sus parámetros reales (`dce_stream_encoder.c`):

| setter | L | `cntl.signal` | `cntl.lanes_number` | `pixel_clock` | audio |
|---|---|---|---|---|---|
| **DP** | 267 | (no pide setup) | — | — | — |
| **HDMI** | 534-596 | `SIGNAL_TYPE_HDMI_TYPE_A` | **`LANE_COUNT_FOUR`** | `actual_pix_clk_khz` | el argumento |
| **DVI** | 651-674 | `DVI_DUAL_LINK` : `DVI_SINGLE_LINK` | **`LANE_COUNT_EIGHT` : `LANE_COUNT_FOUR`** | `pix_clk_100hz / 10` | `false` |
| **LVDS** | 677-696 | `SIGNAL_TYPE_LVDS` | `LANE_COUNT_FOUR` | `pix_clk_100hz / 10` | `false` |

**⇒ El HDMI de esta GPU se programa como un enlace TMDS de 4 carriles. El DVI, de 8 si
es doble enlace y de 4 si es simple.** `PROVEN`.

**⇒ Y eso resuelve el cabo suelto de `160`:** el enum `dc_lane_count` declara 0, 1, 2, 4,
8, y `160` dejé escrito «el 8 existe en el enum pero `LANE_COUNT_DP_MAX` es 4». **El 8 no está
de más: es `DVI_DUAL_LINK`.** Un enlace TMDS de doble enlace necesita 8 carriles porque
lleva 2 pares de pares de datos más el par de reloj, y el DVI de simple, 4. `PROVEN_DERIVED`.

**⇒ Y los tres setters que existen empiezan igual, con una llamada al BIOS:**

```c
dce_stream_encoder.c:551   if (enc110->base.bp->funcs->encoder_control(
dce_stream_encoder.c:552           enc110->base.bp, &cntl) != BP_RESULT_OK)
dce_stream_encoder.c:553           return;
dce_stream_encoder.c:667   (idéntico, en el setter de DVI)
dce_stream_encoder.c:691   (idéntico, en el setter de LVDS)
```

**⇒ Décimo punto de contacto con firmware, y de la misma clase que el reloj de `161`:** la
programación del enlace TMDS la hace el BIOS con `ENCODER_CONTROL_SETUP`, y el driver sólo
le pasa el tipo de señal, los carriles, el reloj de píxel, la profundidad de color y si
quiere audio. **Y si el BIOS dice que no, el setter vuelve sin hacer nada más.** `PROVEN_DERIVED`.

**Y el tipo de señal que se le pasa es el mismo `connector_signal` que decidió el `switch`
de `154` y el mismo enum de `150`.** La cadena de `166` cierra aquí, en la frontera con el
firmware: `connector_signal` → `cntl.signal` → el BIOS. `PROVEN_DERIVED`.

## 2 · Y las tres restricciones que el código impone, que no son del hardware

**DVI: sólo 8 bits RGB, y son `ASSERT`, no caminos de error.**

```c
dce_stream_encoder.c:671   ASSERT(crtc_timing->pixel_encoding == PIXEL_ENCODING_RGB);
dce_stream_encoder.c:672   ASSERT(crtc_timing->display_color_depth == COLOR_DEPTH_888);
```

**⇒ El DVI de esta familia sólo hace RGB de 8 bits por canal, y el driver lo afirma con
`ASSERT`.** `PROVEN`. **No hay `else`:** no es que el driver no sepa hacer otra cosa, es
que afirma que esta salida no la hace.

**LVDS: no llama al helper y no escribe ningún registro TMDS.**

```c
dce_stream_encoder.c:691   if (... encoder_control(...) != BP_RESULT_OK) return;
dce_stream_encoder.c:695   ASSERT(crtc_timing->pixel_encoding == PIXEL_ENCODING_RGB);
dce_stream_encoder.c:696   }
```

**⇒ El setter de LVDS termina después de la llamada al BIOS y un `ASSERT`: no programa
ningún registro de codificación de píxel.** `PROVEN`. **Y tiene sentido: el LVDS es
analógico, no lleva TMDS, así que no hay nada que codificar.** `PROVEN_DERIVED`.

**HDMI: es el único con la tabla de profundidad de color completa.**

```c
dce_stream_encoder.c:572   switch (crtc_timing->display_color_depth) {
dce_stream_encoder.c:573   case COLOR_DEPTH_888:    HDMI_DEEP_COLOR_DEPTH, 0
dce_stream_encoder.c:576   case COLOR_DEPTH_101010: HDMI_DEEP_COLOR_DEPTH, 1
dce_stream_encoder.c:587   case COLOR_DEPTH_121212: HDMI_DEEP_COLOR_DEPTH, 2
dce_stream_encoder.c:598   case COLOR_DEPTH_161616: HDMI_DEEP_COLOR_DEPTH, 3
```

**Cuatro profundidades, codificadas 0 a 3, y para las tres últimas
`HDMI_DEEP_COLOR_ENABLE` es 0 si el píxel es YCbCr 4:2:2 y 1 si no.** `PROVEN`.

**⇒ Las dos salidas de esta placa son asimétricas de una forma medible: el HDMI
programa profundidad de color, el DVI no puede.** `PROVEN_DERIVED`.

## 3 · Y la resolución de `148`, punto por punto

### Error 1 — «el código es de DCE 11.0, no de esta GPU» → **`REFUTED`**

Ya lo refutó `156` y lo confirmó `159`: `dce112_resource.c:519` construye un
`dce110_stream_encoder` con el constructor de DCE 11.0, y los cinco constructores de ese
fichero son `dce110_*`. **El helper y los tres setters están en el camino de esta
máquina.** `156` y `159` stands.

### Error 2 — «la semántica del bit es otra» → **`CONFIRMADO`, y nunca fue refutado**

```c
dce_stream_encoder.c:509   if (enc110->regs->TMDS_CNTL) {
dce_stream_encoder.c:510           switch (crtc_timing->pixel_encoding) {
dce_stream_encoder.c:511           case PIXEL_ENCODING_YCBCR422:
dce_stream_encoder.c:512                   REG_UPDATE(TMDS_CNTL, TMDS_PIXEL_ENCODING, 1);
dce_stream_encoder.c:514           default:
dce_stream_encoder.c:515                   REG_UPDATE(TMDS_CNTL, TMDS_PIXEL_ENCODING, 0);
```

**El `switch` es sobre `pixel_encoding`, no sobre el tipo de señal, y sólo distingue
YCbCr 4:2:2 de todo lo demás.** `148` lo dijo exactamente así: «es un formato de
submuestreo de color, no un tipo de salida». `PROVEN`.

**Y el bit que `148` cité en su versión original —«el bit 4 de `TMDS_CNTL`»— es
correcto:** el `#ifndef` de `dce_stream_encoder.h:35` define
`TMDS_CNTL__TMDS_PIXEL_ENCODING_MASK = 0x00000010L`, y `0x10` es el bit 4. **El registro
correcto, el bit correcto, la máscara correcta, y la interpretación equivocada — que es
justo lo que el error 2 de `148` dice que pasó.** `PROVEN_DERIVED`.

### `PROVEN_ABSENT` — «`TMDS_CNTL` no aparece en la tabla de esta GPU»

**⇒ La conclusión es correcta. La prueba venía del fichero equivocado, y el fichero
equivocado es el mismo de `160`.** `148` buscó en `dce100_resource.c`; la tabla de
recursos de esta máquina es `dce112_resource.c`, como probó `155`. **Décima colisión de
nombres, y la segunda vez que se resuelve de la misma manera: buscando el fichero por el
nombre de la función en vez de por el prefijo del recurso.** `PROVEN_DERIVED`.

**Y con el fichero correcto la respuesta es la misma, pero por otro motivo, y el motivo es
el hallazgo de esta nota.**

## 4 · El bloque `#ifndef`, y por qué existe: la tercera familia de máscaras

```c
dce_stream_encoder.h:34   #ifndef TMDS_CNTL__TMDS_PIXEL_ENCODING_MASK
dce_stream_encoder.h:35           #define TMDS_CNTL__TMDS_PIXEL_ENCODING_MASK       0x00000010L
dce_stream_encoder.h:36           #define TMDS_CNTL__TMDS_COLOR_FORMAT_MASK         0x00000300L
dce_stream_encoder.h:37           #define TMDS_CNTL__TMDS_PIXEL_ENCODING__SHIFT     0x00000004
dce_stream_encoder.h:38           #define TMDS_CNTL__TMDS_COLOR_FORMAT__SHIFT       0x00000008
dce_stream_encoder.h:39   #endif
```

**Y la lista de campos de esta máquina declara el mismo campo, en otro registro:**

```
dce_stream_encoder.h:312   SE_SF(DIG_FE_CNTL, TMDS_PIXEL_ENCODING, mask_sh),
dce_stream_encoder.h:313   SE_SF(DIG_FE_CNTL, TMDS_COLOR_FORMAT, mask_sh),
```

**Y la máscara que el `else if` necesitaría no existe en ningún header de DCE:**

```
dce_stream_encoder.c:519   } else if (enc110->regs->DIG_FE_CNTL) {
dce_stream_encoder.c:522                   REG_UPDATE(DIG_FE_CNTL, TMDS_PIXEL_ENCODING, 1);
```

**⇒ `DIG_FE_CNTL__TMDS_PIXEL_ENCODING_MASK` no existe en ningún `sh_mask.h` de DCE.** El
único sitio donde aparece es `include/asic_reg/dcn/dcn_3_2_1_sh_mask.h:28838`, y allí es
**un campo distinto, en el bit 28** (`0x10000000L`, shift `0x1c`) y en una instancia
`DIG0_`/`DIG1_`/`DIG2_` por DIG. Medido por programa. `PROVEN_ABSENT`.

**⇒ Por tanto la rama `else if` no puede compilar para DCE, y `enc110->regs->TMDS_CNTL` es
necesariamente distinto de cero en esta máquina.** No lo he leído de una tabla: **lo he
deducido del hecho de que la alternativa no compila.** `PROVEN_DERIVED`.

**⇒ Y el bloque `#ifndef` no es un apaño del driver: es la única definición de esas dos
máscaras en todo el árbol para DCE.** `PROVEN_DERIVED`. `148` lo afirmó («el driver lo
define él mismo con guards `#ifndef`, en un fichero donde el contexto es DCE 11.0») y es
cierto, y ahora el motivo está medido.

**⇒ Y hay tres familias de máscaras, no dos:**

| familia | dónde | quién la pone |
|---|---|---|
| del header | `dce_10_0_sh_mask.h` y hermanos | AMD, generado |
| de la lista de swizzle | `SE_SF(...)` de `147` | la tabla de recursos de cada generación |
| **propia del driver** | el `#ifndef` de `dce_stream_encoder.h:34-39` | **el driver, a mano** |

**La tercera existe y `148` la vio sin saber para qué; esta nota explica su función: la
lista de la generación mueve un campo de registro y el código sigue escribiendo el
registro viejo, y alguien tiene que supplying la máscara del viejo.** `PROVEN_DERIVED`.

## 5 · Y el clamp del reloj de canal, que era `148` R3

```c
dce_stream_encoder.c:563   } else if (enc110->regs->DIG_FE_CNTL) {
dce_stream_encoder.c:564           REG_UPDATE_5(HDMI_CONTROL,
dce_stream_encoder.c:565                   HDMI_PACKET_GEN_VERSION, 1,
dce_stream_encoder.c:566                   HDMI_KEEPOUT_MODE, 1,
dce_stream_encoder.c:567                   HDMI_DEEP_COLOR_ENABLE, 0,
dce_stream_encoder.c:568                   HDMI_DATA_SCRAMBLE_EN, 0,
dce_stream_encoder.c:569                   HDMI_CLOCK_CHANNEL_RATE, 0);
```

**Y la lista `DCE112` declara los dos campos últimos** (`dce_stream_encoder.h:310-311`,
`SE_SF(HDMI_CONTROL, HDMI_CLOCK_CHANNEL_RATE, ...)` y `SE_SF(HDMI_CONTROL,
HDMI_DATA_SCRAMBLE_EN, ...)`), **y `dce112_resource.c` es la que los cablea** — ambas
macroejecuciones de la lista en `dce112_resource.c` son `SE_COMMON_MASK_SH_LIST_DCE112`.
`PROVEN`.

**⇒ Esta GPU toma la segunda rama y escribe cinco campos, no tres, y entre ellos
`HDMI_CLOCK_CHANNEL_RATE, 0`.** `PROVEN_DERIVED`.

**⇒ Y con eso queda cerrado `148` R3 desde el lado contrario al que se cerró en
`155`.** No es que el campo no exista y el driver no pueda tocarlo: **el campo existe, el
driver lo escribe, y escribe 0, que es la codificación del umbral bajo —≤340 MHz,
«usa el que viene por defecto».** `148` dijo «no es programable»; `155` dijo «el campo
existe»; las dos son verdaderas a medias y la verdad completa es que **se programa a un
valor que significa no cambiarlo.** `PROVEN_DERIVED`.

**Y la primera rama es la de los chips sin `HDMI_DATA_SCRAMBLE_EN`:**
`if (!enc110->se_mask->HDMI_DATA_SCRAMBLE_EN)`. **Dos centinelas distintos en el mismo
`if / else if`:** la máscara de campo de `156` en la condición del `if`, y la dirección de
registro de `156` en la del `else if`. `PROVEN_DERIVED`.

## Lo que NO cierra

| afirmación | estado |
|---|---|
| HDMI: 4 carriles, reloj de píxel como argumento, audio sí | `PROVEN` |
| DVI: 8 carriles doble enlace, 4 simple | `PROVEN` |
| LVDS: 4 carriles, no escribe ningún registro TMDS | `PROVEN` |
| `LANE_COUNT_EIGHT` es el DVI de doble enlace | `PROVEN_DERIVED` |
| Los tres setters llaman a `encoder_control` del BIOS | `PROVEN` |
| Décimo punto de contacto con firmware | `PROVEN_DERIVED` |
| DVI: sólo RGB de 8 bits, y por `ASSERT` | `PROVEN` |
| HDMI: cuatro profundidades de color, codificadas 0 a 3 | `PROVEN` |
| `148` error 1: el código es de DCE 11.0 | **`REFUTED`** por `156` y `159` |
| `148` error 2: la semántica es YCbCr 4:2:2 | **`CONFIRMADO`**, nunca refutado |
| `148`: el bit 4 y la máscara 0x10 | `PROVEN_DERIVED` |
| `148` `PROVEN_ABSENT`: conclusión certa, prueba del fichero erróneo | `PROVEN_DERIVED` |
| `DIG_FE_CNTL__TMDS_PIXEL_ENCODING_MASK` no existe para DCE | `PROVEN_ABSENT` |
| La rama `else if` no puede compilar para DCE | `PROVEN_DERIVED` |
| Tres familias de máscaras, la tercera a mano | `PROVEN_DERIVED` |
| `HDMI_CLOCK_CHANNEL_RATE` se escribe a 0 = umbral ≤340 MHz | `PROVEN_DERIVED` |
| Si el HDMI de esta placa soporta 4K60 con 4 carriles TMDS | **`NOT_DETERMINED`** |
| Si el DVI de la placa es de simple o de doble enlace | **`NOT_DETERMINED`** |
| Qué devuelve `encoder_control` en esta máquina | **`NOT_DETERMINED`** — nivel 4 |

**La segunda de las abiertas es la única cerrable sin instrumentar, y es la que decide la
cifra de pantalla: un DVI de simple enlace con 4 carriles TMDS y 8 bits de color son
25,175 MHz de píxel, y a 4K60 hacen falta 533,25.** `PROVEN_DERIVED` del lado aritmético
y `NOT_DETERMINED` del lado de la placa.

## Procedencia

- `STATIC` -- `display/dc/dce/dce_stream_encoder.c:267-330` (setter de DP, de `156`),
  `:505-531` (el helper completo, con su `if / else if` sobre `TMDS_CNTL` y
  `DIG_FE_CNTL`), `:534-596` (el setter de HDMI completo, con su llamada al BIOS, su
  `if / else if` de `HDMI_CONTROL` y su `switch` de profundidad de color),
  `:651-674` (el de DVI, con sus dos `ASSERT`), `:677-696` (el de LVDS);
  `display/dc/dce/dce_stream_encoder.h:34-39` (el bloque `#ifndef`),
  `:67` `:69` `:84` (los `SRI` de `DIG_FE_CNTL`, `HDMI_CONTROL` y `TMDS_CNTL`),
  `:116-117` (`SE_SF`), `:307-313` (la macro `SE_COMMON_MASK_SH_LIST_DCE112`, con
  `HDMI_CLOCK_CHANNEL_RATE` y `HDMI_DATA_SCRAMBLE_EN` en `:310-311` y
  `DIG_FE_CNTL` en `:312-313`); `display/dc/resource/dce112/dce112_resource.c:513-519`
  (de `156`), y las dos ocurrencias de `SE_COMMON_MASK_SH_LIST_DCE112` en ese fichero;
  `include/asic_reg/dcn/dcn_3_2_1_sh_mask.h:28826-28838` (el único sitio del árbol donde
  existe `DIG_FE_CNTL__TMDS_PIXEL_ENCODING_MASK`, con shift `0x1c` y máscara
  `0x10000000`).
- Medición por programa: **la lista de `SE_SF` de la macro `DCE112` y sus campos**;
  **la búsqueda de `DIG_FE_CNTL__TMDS_PIXEL_ENCODING` en todo el árbol de drivers, que
  devuelve sólo el header de DCN 3.2.1**; los tres cuerpos de los setters, con su
  `cntl.signal`, `cntl.lanes_number`, `cntl.pixel_clock` y `cntl.enable_dp_audio`; los
  cuatro valores de `HDMI_DEEP_COLOR_DEPTH` y los dos de `HDMI_DEEP_COLOR_ENABLE`; los
  cuatro `#define` del bloque `#ifndef` con su valor decimal.
- **Cuatro fallos de patrón propios en esta nota, todos del mismo tipo y todos cazados
  antes de escribir:** (1) mi extractor de cuerpo de función cerró en dos líneas porque
  contó las llaves de la firma antes del `{` real, y devolvió «NINGUNO DIRECTO» para los
  registros; (2) el parser de macro con continuaciones de línea `\` no contó las entradas
  de `SE_COMMON_MASK_SH_LIST_DCE112` — dio 0 en tres intentos; (3) busqué
  `struct dce110_str_enc_registers` y devolvió 0 campos por un `re` que sólo cogía
  líneas que empiezan por tabulador; (4) leí `SE_COMMON_REG_LIST_DCE_BASE` y conté 4
  registros cuando la macro sigue más allá del punto donde corté. **Los cuatro habrían
  producido una tabla de campos vacía y un `PROVEN_ABSENT` falso, y el (4) casi lo
  casi peor: estuve a punto de escribir que `TMDS_CNTL` no está en la lista de
  que es lo que `148` dedujo mal y lo que yo iba a repetir.**
- Encadenada con `166` (**los dos conectores que existen, y aquí los registros que
  escribirían**), `160` (**los 4 carriles, y aquí que el HDMI los usa y que el `8` del
  enum es el DVI doble enlace**), `158` (los cuatro setters, y aquí sus cuerpos),
  `157` (la tabla y la cobertura del 58%), `156` (**los dos centinelas —máscara de campo
  y dirección de registro— en un solo `if / else if`**), `155` (DCE 11.2 y la lista
  `DCE112` de 91 de 130), `154` (el `connector_signal` que se le pasa al BIOS),
  `153` (los siete paths), `150` (el enum de señal, del que salen los cuatro `cntl.signal`).
- No se editó `AGENTS.md` ni `OPEN-FRONTIERS.md`.

## Nota de método

**El bloque `#ifndef` lleva desde `148` en el corpus, citado como una rareza («el driver
lo define él mismo con guards `#ifndef»), y nadie se preguntó de qué servía. Se responde
con un `grep` de un símbolo: el nombre de la máscara que la rama alternativa necesitaría.**

*La pregunta útil no era «qué hace este `#ifndef`» sino «¿qué pasaría si no estuviera».* **Y
la respuesta es que el fichero no compilaría, porque `DIG_FE_CNTL__TMDS_PIXEL_ENCODING_MASK`
no existe en ningún header de DCE.** *Una rama de código que no puede compilar es la
prueba más fuerte que hay de que la otra rama es la que se ejecuta, y es una prueba que no
requiere leer una tabla: se obtiene de la existencia de un símbolo ausente.*

**Y el segundo resultado es de método, y es el más incómodo de la tanda: la
conclusión de `148` era correcta y su prueba venía del fichero equivocado, y son dos
cosas que hay que registrar por separado.**

*Una conclusión correcta con la prueba equivocada es el estado más peligroso de un
proyecto de investigación, porque no señala nada roto.* Si `148` hubiera escrito «`TMDS_CNTL`
no está en la lista de esta GPU» sin decir en qué fichero lo buscó, la afirmación habría
sido correcta y habría durado. **Al decir el fichero, se vuelve comprobable, y al
comprobarlo se descubre que el fichero era el de otra generación — la décima colisión de
nombres, y la segunda vez que se resuelve igual que en `160`: el fichero se busca por el
nombre de la función, y el nombre de la función no dice en qué generación está.** **Y esa
es la defensa que ya funcionó: abrir la nota que corrige, no el resumen de la nota que
corrige. Como en `140` con los 976 GiB, y como en `159` con los 20 ficheros.**
