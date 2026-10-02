# 150 · `enum signal_type`: declarada como máscara, consumida como enumeración

```
CLASSIFICATION=DOCUMENTATION · TRACK=STATIC
CORPUS=RESEARCH/working/linux-7.1.3 · HARDWARE_SCOPE=HOST-C/RX550/0000:01:00.0
WORK_CLASS=READ_ONLY/EVIDENCE · WRITE_EXECUTION=NONE · MODIFICATIONS=0
RUNTIME=NOT_RUN · GPU INTACTA
```

## Qué resuelve

**Dónde vive de verdad el tipo de salida** — el campo que yo inventé en `148` y que
`149`buscó en `dc_crtc_timing` para después confirmar que allí no está. **Y que la
enumeración que lo define está escrita como máscara de bits pero se usa como
enumeración de valor único, y que las dos lecturas no coinciden.**

**Y dos `grep` "decisivos" míos que estaban mal construidos, con su corrección
visible en la salida.**

## 1 · Dónde está, y por qué no lo encontré antes

**Ni en `dc_crtc_timing` (que `149`leyó entero, 112 líneas) ni en
`dc_hw_types.h`.** Está en:

```
display/include/signal_types.h          <- display/include/, no display/dc/include/
```

**Sexto fichero de esta familia en tres sitios distintos**, y hay **dos** directorios
`include/` bajo `display/`: `display/include/` (22 ficheros) y `display/dc/include/`.
**Mismo nombre, mismo árbol, distinto contenido.** `dc_types.h` y `dc_hw_types.h`
están en el segundo; `signal_types.h` en el primero.

**Y `dc_hw_types.h:31` lo dice: `#include "signal_types.h"`.** La pista estaba en la
primera línea del fichero que leí entero en `149`, y la pasé por alto porque ya
estaba respondiendo otra pregunta.

## 2 · Los diez valores, y el hueco del bit 8

```c
enum signal_type {                                       /* signal_types.h:34 */
        SIGNAL_TYPE_NONE             = 0L,        /* no signal */
        SIGNAL_TYPE_DVI_SINGLE_LINK  = (1 << 0),
        SIGNAL_TYPE_DVI_DUAL_LINK    = (1 << 1),
        SIGNAL_TYPE_HDMI_TYPE_A      = (1 << 2),
        SIGNAL_TYPE_LVDS             = (1 << 3),
        SIGNAL_TYPE_RGB              = (1 << 4),
        SIGNAL_TYPE_DISPLAY_PORT     = (1 << 5),
        SIGNAL_TYPE_DISPLAY_PORT_MST = (1 << 6),
        SIGNAL_TYPE_EDP              = (1 << 7),
        SIGNAL_TYPE_VIRTUAL          = (1 << 9),  /* Virtual Display */
};
```

**Diez valores, y el bit 8 no tiene nombre.** Del 0 al 7 son correlativos, y luego un
salto del 7 al 9. `PROVEN`, y el hueco está medido, no supuesto.

**Y dos detalles de nomenclatura que importan:**

- **`HDMI` se llama `SIGNAL_TYPE_HDMI_TYPE_A`.** "Type A" es el nombre del conector
  físico, no un estándar de señal. **El driver no dice "HDMI": dice qué señal y qué
  conector.**
- **MST está separada de DisplayPort.** No es "DP con MST", es un valor propio.

## 3 · Siete predicados, y dos son idénticos

`signal_types.h:76-140`, todos `static inline`, todos con `==`:

| predicado | cuerpo | |
|---|---|---|
| `dc_is_hdmi_tmds_signal` | `signal == SIGNAL_TYPE_HDMI_TYPE_A` | |
| `dc_is_hdmi_signal` | `signal == SIGNAL_TYPE_HDMI_TYPE_A` | **idéntico al anterior** |
| `dc_is_dp_sst_signal` | `== DISPLAY_PORT \|\| == EDP` | **excluye MST** |
| `dc_is_dp_signal` | `== DISPLAY_PORT \|\| == EDP \|\| == DISPLAY_PORT_MST` | incluye MST |
| `dc_is_embedded_signal` | `== EDP \|\| == LVDS` | |
| `dc_is_lvds_signal` | `== LVDS` | |
| `dc_is_rgb_signal` | `== RGB` | |
| `dc_is_dvi_signal` | hasta `L117`, con `return true` / `return false` separados | el único con cuerpo compuesto |
| `dc_is_tmds_signal` | hasta `L139`, igual | ídem |

**`dc_is_hdmi_tmds_signal` y `dc_is_hdmi_signal` tienen el mismo cuerpo, byte a
byte.** Dos nombres para la misma pregunta. `OBSERVED`, y no es un error: en HDMI,
"TMDS signal" e "HDMI signal" son la misma cosa por definición de la señal, y el
driver lo refleja duplicando la función.

**Y la distinción que sí está hecha es MST: `dc_is_dp_signal` incluye MST y
`dc_is_dp_sst_signal` no.** Son preguntas distintas —"¿es DisplayPort?" frente a
"¿es DisplayPort de flujo simple?"— y para eDP la respuesta es que sí a la primera y
no a la segunda. `PROVEN_DERIVED`.

## 4 · La medición que lo resuelve: 252 contra 4

Este es el resultado, y salió de un programa que recorre todo `drivers/gpu/drm/amd`
con dos expresiones regulares, Sustituyendo `&&` por un marcador antes de buscar el
AND bitwise:

```
COMPARACIONES CON == O != CONTRA SIGNAL_TYPE:   252
USOS CON AND BITWISE (&, no &&) SOBRE SIGNAL_TYPE:   4
```

**Y los cuatro son `& SIGNAL_TYPE_EDP`, y los cuatro están en el Display Manager:**

```
display/amdgpu_dm/amdgpu_dm_psr.c          & SIGNAL_TYPE_EDP
display/amdgpu_dm/amdgpu_dm_debugfs.c      & SIGNAL_TYPE_EDP
display/modules/power/power_helpers.c      & SIGNAL_TYPE_EDP
```

**⇒ La enumeración se DECLARA como máscara de diez bits y se USA como enumeración de
valor único en 252 sitios. Los cuatro sitios donde se usa como máscara hacen todos la
misma pregunta: "¿es un panel embebido?".** `PROVEN`, y el cociente 252/4 es el
dato.

### Por qué está escrita como máscara, entonces

**Porque una de las diez preguntas necesita poder preguntar por un bit.** `EDP` es el
único valor que se consulta con `&`, y es el único para el que tiene sentido preguntar
"¿está este bit?" sin haber mirado el valor completo: un panel embebido es una
propiedad que se quiere filtrar en una lista de modos, y `(signal & EDP)` lo dice en
una expresión.

**Y la ambigüedad es real, aunque hoy no esté activa.** `SIGNAL_TYPE_DISPLAY_PORT` es
`1<<5` = 32 y `SIGNAL_TYPE_EDP` es `1<<7` = 128. **El valor 96 sería "DP o EDP" bajo
semántica de máscara y "Unknown" bajo semántica de enumeración.** Las dos lecturas
discrepan, el código usa las dos, y **nadie combina dos bits con `&`** — no hay ni un
`(signal & (A | B))` en el árbol. `PROVEN_ABSENT` para la combinación, por programa.

**Para un driver propio, la regla es concreta y no es obvia: en esta API,
`signal_type` se trata como un valor, salvo la pregunta por EDP.**

## 5 · Y lo que esto hace con `147`/`148`/`149`

| nota | qué afirmó |
|---|---|
| `147` | DCE 10.0 no tiene `HDMI_CLOCK_CHANNEL_RATE` en el stream encoder |
| `148` | el umbral de 340 MHz existe como constante, y el campo no |
| `149` | el umbral sobrevive en el flag `LTE_340MCSC_SCRAMBLE` del timing |
| **`150`** | **"HDMI" es el valor 4 de una enum de diez; el reloj de canal de ese valor no es programable aquí** |

**Y aquí está el resumen del camino completo, que es lo que un driver propio
necesita para decidir una salida:**

```
 1  el Display Manager elige un valor de enum signal_type  (10 valores)
 2  lo mete en el link, y el sink es el par (link, timing)  (149)
 3  "es HDMI" es  (signal == SIGNAL_TYPE_HDMI_TYPE_A),  valor 4
 4  el formato de color y la profundidad van en crtc_timing,  no aquí  (149)
 5  el DC programa el stream encoder con 89 de 130 campos,  41 con máscara cero  (147)
 6  el reloj de canal de HDMI no se programa en esta GPU  (147, 148, 149)
```

**Seis pasos, y sólo el 6 necesita hardware. Los cinco primeros son `PROVEN` en este
corpus, y son exactamente la decisión que hay que tomar antes de encender un panel.**

## 6 · Y mis dos `grep` "decisivos", que estaban mal

Escribí dos comprobaciones para cerrar §4 y **las dos estaban mal construidas**,
y la salida lo dijo antes que yo:

| lo que escribí | lo que pasó |
|---|---|
| buscar `SIGNAL_TYPE_... &` para el AND bitwise | contaba 24, y la muestra era `== SIGNAL_TYPE_EDP &` — **el `&` de un `&&`** |
| buscar `SIGNAL_TYPE_... ==` para la igualdad | **0 resultados**, porque el código escribe `== SIGNAL_TYPE_...` — la constante va **después** |

**El primer patrón contaba los `&&` como si fueran AND bitwise, y el segundo estaba
invertido.** Si me hubiera fiado, esta nota habría dicho "24 usos con máscara" y "el
tipo de salida no se compara nunca con `==`", que son las dos cosas contrarias a la
verdad, y la segunda habría sido absurdo.

**Es la regla (d) de este proyecto, aplicada por cuarta vez hoy:** *ante un grep
vacío, o ante un grep con un número raro, la primera hipótesis es el patrón, no el
mundo.* Y el indicio estaba en la propia salida: un `&` pegado al final de una línea
que empezaba con `==` no es un AND bitwise, y un `grep` de igualdad que devuelve
cero en un fichero donde acabo de leer cien comparaciones no está diciendo que no
haya comparaciones.

*Y la corrección no fue "arreglar el patrón", fue hacer el programa que no puede
confundir `&` con `&&` y que cuenta los dos tipos de comparación en la misma
pasada.* Sustituir `&&` por un marcador antes de buscar es un minuto; hacerlo bien
a mano, con dos `grep` y un `sed`, es un camino a una afirmación falsa.

## Lo que NO cierra

| afirmación | estado |
|---|---|
| `signal_type` está en `display/include/signal_types.h` | `PROVEN` |
| Hay dos directorios `include/` bajo `display/` | `PROVEN` |
| Diez valores, bit 8 sin nombre | `PROVEN` (por programa) |
| `HDMI` = `SIGNAL_TYPE_HDMI_TYPE_A` = `1<<2` = 4 | `PROVEN` |
| Siete predicados, dos idénticos | `PROVEN` |
| MST en `dc_is_dp_signal` y no en `dc_is_dp_sst_signal` | `PROVEN` |
| 252 comparaciones con `==`, 4 con `&` | `PROVEN` (por programa) |
| Los 4 con `&` son EDP y están en el DM | `PROVEN` |
| No hay combinación de bits con `&` | `PROVEN_ABSENT` (por programa) |
| El valor 96 sería ambiguo | `PROVEN_DERIVED` |
| La decisión de salida se toma en 6 pasos | `PROVEN_DERIVED` |
| Dónde se elige el valor de `signal_type` | **`NOT_DETERMINED`** — está en el DM, en el connector detection |
| Si esta placa tiene un panel embebido | **`NOT_DETERMINED`** |
| Cómo se calcula `sink->link` | **`NOT_DETERMINED`** |

**Las dos primeras filas abiertas son el Display Manager, que es el componente que
nadie ha abierto en este proyecto y que `149` ya nombró como la otra mitad del
driver.** `display/amdgpu_dm/` está en el corpus, y es donde se decide el valor de
esta enumeración — es decir, dónde se decide, para esta GPU, si la salida es HDMI,
DisplayPort o LVDS.

## Procedencia

- `STATIC` -- `display/include/signal_types.h:26-33` (guard e include desde
  `dc_hw_types.h:31`), `:34-45` (`enum signal_type`), `:47-73`
  (`signal_type_to_string`, 10 casos + `default`), `:76-140` (los predicados);
  `display/dc/dc_hw_types.h:31`, `display/dc/dc_hw_types.h:904-1015` (de `149`);
  `display/amdgpu_dm/amdgpu_dm_psr.c`, `display/amdgpu_dm/amdgpu_dm_debugfs.c`,
  `display/modules/power/power_helpers.c` (los tres usos con `&`).
- Medición: `os.walk` sobre `drivers/gpu/drm/amd`, dos `re.findall` — una para
  `(SIGNAL_TYPE_\w+)\s*&(?!&)|(?<!&)\s*&\s*(SIGNAL_TYPE_\w+)` y otra para
  `(?:==|!=)\s*(SIGNAL_TYPE_\w+)` — después de sustituir `&&` por `__ANDAND__` en el
  texto. **De ahí salen el 252 y el 4, y son la base de §4.**
- Recuento de valores de la `enum`: `re.findall` sobre el cuerpo de la `enum`,
  10 valores con su expresión.
- **Los dos `grep` fallidos de §6 están documentados con su salida, porque un
  resultado que no se publica también es un resultado.**
- Encadenada con `149` (la frontera DM→DC, y el campo `link_type` que inventé),
  `148` (dos correcciones propias), `147` (los 89 de 130 campos y el reloj de canal
  ausente), `144` (el otro extremo del objetivo: la entrada), `140` (el mapa de
  direcciones).
- No se editó `AGENTS.md` ni `OPEN-FRONTIERS.md`.

## Nota de método

**La estructura del resultado ya no sorprende: el fichero que contiene la
respuesta estaba incluido por el fichero que leí entero en la nota anterior, en la
primera línea, y la pasé por alto porque ya estaba contestando otra pregunta.**

`dc_hw_types.h:31` es `#include "signal_types.h"`. `149` leyó las 112 líneas de
`dc_crtc_timing` y no miró la cabeza del fichero. **Y la respuesta a "dónde vive el
tipo de salida" estaba a treinta líneas de distancia de donde estaba la respuesta
anterior.**

*Un `#include` es una promesa de que el fichero existe y de que tiene algo que
aportar. Es el mismo argumento que el de `145` —"un include que no resuelve es un
NOT_IN_CORPUS con la medida"—, y funciona igual en positivo: un include que resuelve
es un NOT_IN_CORPUS resuelto, y la medida es el nombre del fichero.*

**Y la lección de §6 es la más transferible de la tanda, porque no es de lectura sino
de construcción:** *cuando un `grep` devuelve un número que no encaja con lo que uno
sabe, el número se sospecha en lugar del patrón.* Un programa que sustituya `&&` antes de
buscar `&` cuesta un minuto y elimina una clase entera de error; dos `grep` a mano
con el operador en el sitio equivocado cuestan una afirmación falsa.
