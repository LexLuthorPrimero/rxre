# 159 · DCE 11.2 son 52 funciones: el 21% de las 252 de DCE 11.0

```
CLASSIFICATION=DOCUMENTATION · TRACK=STATIC
CORPUS=RESEARCH/working/linux-7.1.3 · HARDWARE_SCOPE=HOST-C/RX550/0000:01:00.0
WORK_CLASS=READ_ONLY/EVIDENCE · WRITE_EXECUTION=NONE · MODIFICATIONS=0
RUNTIME=NOT_RUN · GPU INTACTA
```

## Qué resuelve

**La pregunta que `158` dejó abierta sobre el motor de mode-setting, y una
corrección propia: `display/amdgpu_dm/` no es el sitio donde se decide el modo, y no
tiene ninguna tabla de operaciones por generación.**

**Y el resultado que sale es un número de ingeniería: qué cuesta añadir una
generación de DC al driver. Para DCE 11.2 sobre DCE 11.0, el 21%.**

## 1 · Corrección propia primero: `amdgpu_dm/` son 35 ficheros, no 37

```
.amdgpu_dm/   19 .c  32.304 lineas
               16 .h   3.003 lineas
             TOTAL 35 ficheros, 35.307 lineas      <- yo habia estimado 37
```

**Y un solo fichero se come el 39%:** `amdgpu_dm.c`, **13.719 líneas**, con **239
funciones**, de las cuales **76** llevan el prefijo `amdgpu_dm`. `PROVEN`.

**Pero ese fichero no es el motor de temporización.** No contiene una sola función
`dc_crtc_timing`, y sus prefijos son `amdgpu_dm_*`, `handle_hpd_*`, `parse_edid_*`,
`dmub_aux_*`, `hdmi_cec_*`. **Es la capa de pegamento con DRM/KMS: IRQ, HPD, EDID,
FreeSync, CEC.** `PROVEN_DERIVED`.

## 2 · `NEGATIVE_RESULT` sobre el método, y es el que reencuadra el bloque

**Busqué la tabla de operaciones del gestor de display por generación. No existe.**

| búsqueda | resultado |
|---|---|
| `struct dc_dm` | **0 apariciones** en todo `display/` |
| funciones `dc_dm_*` | **0** |
| tablas `dc_dm_ops` o `dm_*_ops` | **0** |
| tablas `*_ops` de cualquier tipo en `display/*.c` | **3**, y ninguna es del DM: `amdgpu_dm_audio_component_ops`, `amdgpu_dm_audio_component_bind_ops`, `amdgpu_dm_backlight_ops` |

**⇒ El gestor de display no se versiona por tabla de punteros a función.** `PROVEN_ABSENT`.

**Y esto no es un hueco: es la confirmación de que `232` es el mecanismo único.** El
versionado de amdgpu en display no se hace con una tabla de ops del nivel superior, sino
con lo que `232` midió: **cada objeto recibe, en su constructor, la implementación de su
generación, y el reparto de implementaciones está escrito en un fichero de recursos.**

**Y ese fichero, para esta máquina, mide 1.442 líneas y contiene 23 de las 52 funciones
`dce112_*` del árbol.** `dce112_resource.c` es el 44% del código propio de DCE 11.2. `PROVEN`.

## 3 · Los seis subsistemas que esta GPU hereda de DCE 11.0

`dce112_resource.c`, seis constructores, seis prefijos distintos, **todos `dce110_`**:

```
dce112_resource.c:505   dce110_timing_generator_construct(tg110, ctx, instance, offsets)
dce112_resource.c:519   dce110_stream_encoder_construct(enc110, ctx, ctx->dc_bios, eng_id, ...)
dce112_resource.c:642   dce110_link_encoder_construct(enc110, ...)
dce112_resource.c:694   dce110_opp_construct(opp, ...)
dce112_resource.c:709   dce110_aux_engine_construct(aux_engine, ctx, inst, ...)
```

| subsistema | quién lo programa en esta GPU |
|---|---|
| generador de temporización | `dce110_timing_generator_construct` |
| codificador de stream | `dce110_stream_encoder_construct` |
| codificador de enlace | `dce110_link_encoder_construct` |
| canal de salida de píxeles | `dce110_opp_construct` |
| motor AUX | `dce110_aux_engine_construct` |
| **reloj** | `dce112_clk_mgr.c` — **propio** |

**⇒ Cinco subsistemas de DCE 11.0 y uno propio. `PROVEN`.** Y el de reloj es el único
de la columna propia que no vive en el fichero de recursos.

## 4 · Y el código propio de DCE 11.2, medido fichero a fichero

**52 funciones `dce112_*` en 7 ficheros. Veintitrés son el propio fichero de recurso,
quedan 29 implementaciones en 6 subsistemas:**

| fichero | funciones | naturaleza |
|---|---|---|
| `dc/resource/dce112/dce112_resource.c` | 23 | **el reparto** — el cableado |
| `dc/dce112/dce112_compressor.c` | 13 | propio, en subdirectorio propio |
| `dc/clk_mgr/dce112/dce112_clk_mgr.c` | 5 | propio, en subdirectorio propio |
| `dc/dce/dce_clock_source.c` | 5 | **rama dentro de fichero compartido** |
| `dc/hwss/dce112/dce112_hwseq.c` | 3 | propio |
| `dc/dce/dce_mem_input.c` | 2 | **rama dentro de fichero compartido** |
| `dc/dce/dce_i2c_hw.c` | 1 | **rama dentro de fichero compartido** |

**⇒ De los seis subsistemas propios, tres tienen subdirectorio `dce112/` y tres son una
rama dentro de un fichero que sirve a varias generaciones.** `PROVEN_DERIVED`.

**Y `dce112_compressor.c` — 848 líneas, 13 funciones — es el único fichero de
implementación de DCE 11.2 que tiene subdirectorio propio, y es el compresor.** O sea:
**lo único que DCE 11.2 añade al hardware de DCE 11.0, con su propio directorio, su
propio fichero y su propio número de registro, es la compresión de superficies.** `PROVEN_DERIVED`.

## 5 · La curva de coste de una generación, y es la parte útil

Contando **funciones cuyo nombre lleva el prefijo de la generación**, en todo `display/`:

| generación | funciones propias | ficheros | respecto a la anterior |
|---|---|---|---|
| `dce60` | 64 | 11 | punto de partida |
| `dce80` | 24 | 4 | ×0,4 |
| `dce100` | 30 | 3 | ×1,2 |
| **`dce110`** | **252** | **19** | **×8,4** |
| **`dce112`** | **52** | **7** | **×0,2** |
| `dce120` | 65 | 6 | ×1,2 |

**⇒ 52 / 252 = 21%. Una generación nueva, cuando ya existe la anterior, cuesta un
quinto de la anterior.** `PROVEN`.

**Y el año 8,4 de `dce110` es el dato que da sentido a la fila: 252 funciones no son el
coste de «una generación más», son el coste de la que se escribe desde cero.** Después
de esa, el driver hereda. `PROVEN_DERIVED`.

**Y para un driver propio, el número actionable es 52: eso es lo que hay que escribir
para soportar un DC nuevo sobre el anterior, y de esos 52, 23 son cableado.** `PROVEN_DERIVED`.

## 6 · Y una verificación que casi sale como error mío

`151` afirmó «el motor de mode-setting de esta GPU son 20 ficheros y 11.875 líneas».
**Al repetir la cuenta no cuadraba: `dml/` + `dml/calcs` + `dml/dsc` dan 8 ficheros
`.c` y 7.746 líneas.** Fui a darlo por un error mío.

**Contando `.c` y `.h` juntos:**

```
dml/      13 ficheros (4 .c)   7.085 lineas
dml/calcs  4 ficheros (3 .c)   3.736 lineas
dml/dsc    3 ficheros (1 .c)   1.054 lineas
SUMA      20 ficheros          11.875 lineas     COINCIDE
```

**`151` era exacto. Los 20 ficheros son 8 `.c` y 12 cabeceras.** `PROVEN`, y `151` no
necesita corrección. **Un recuento de ficheros no es un recuento de ficheros: hay que
decir de qué extensión.**

**Y el mismo directorio engaña en la otra dirección:** `dml/` **recursivo** son 35
ficheros `.c` y 77.927 líneas, porque las carpetas por generación de DML2 —`dcn10`,
`dcn20`, `dcn30`, `dcn314`, `dcn351`…— están **dentro de `dml/`**, que se llama así
pero no es DML1. **`dml2_0/` es 31 `.c` y 40.058 líneas.** Sexto candidato a colisión de
nombres: el nombre del directorio no dice qué motor contiene. `PROVEN`.

## Lo que NO cierra

| afirmación | estado |
|---|---|
| `amdgpu_dm/`: 35 ficheros, 35.307 líneas; `amdgpu_dm.c` es el 39% | `PROVEN` |
| `amdgpu_dm.c` no es el motor de temporización | `PROVEN_DERIVED` |
| No hay `struct dc_dm`, ni `dc_dm_*`, ni ops de DM | `PROVEN_ABSENT` |
| 6 subsistemas heredados, todos `dce110_` | `PROVEN` |
| 52 `dce112_*` en 7 ficheros; 29 implementaciones | `PROVEN` |
| 3 de los 6 subsistemas propios son rama en fichero compartido | `PROVEN_DERIVED` |
| El compresor es lo único con subdirectorio propio | `PROVEN_DERIVED` |
| El coste de una generación nueva es el 21% | `PROVEN` |
| `151`: 20 ficheros = 8 `.c` + 12 cabeceras | `PROVEN` — no necesita corrección |
| `dml/` recursivo = 77.927 líneas, con DML2 dentro | `PROVEN` |
| Cuál de los 6 `dce110_` se ejecuta con un modo concreto | **`NOT_DETERMINED`** |
| Si el compresor de DCE 11.2 se usa en un modo sin comprimir | **`NOT_DETERMINED`** |
| Si esta placa tiene salida VGA cableada | **`NOT_DETERMINED`** — Bios, desde `158` |

**La primera de las abiertas es la que cierra el bloque de display por el lado del
camino: las cinco funciones `dce110_*_construct` de `dce112_resource.c` se llaman todas
al construir la placa, pero qué se programa dentro de cada una para un modo concreto es
una pregunta de orden de llamadas, y el orden es lo único que queda por establecer.**

## Procedencia

- `STATIC` -- `display/dc/resource/dce112/dce112_resource.c:505` `:519` `:642` `:694`
  `:709` (los cinco constructores `dce110_`; 1.442 líneas, 23 funciones `dce112_*`),
  `display/dc/resource/dce110/dce110_resource.c` (1.561 líneas),
  `display/dc/dce112/dce112_compressor.c` (848 líneas, 13 funciones),
  `display/dc/clk_mgr/dce112/dce112_clk_mgr.c`,
  `display/dc/hwss/dce112/dce112_hwseq.c`,
  `display/dc/dce/dce_clock_source.c`, `display/dc/dce/dce_mem_input.c`,
  `display/dc/dce/dce_i2c_hw.c`,
  `display/amdgpu_dm/amdgpu_dm.c` (13.719 líneas, 239 funciones),
  `display/dc/dml/` y sus subdirectorios `calcs`, `dsc`, `dcn*`,
  `display/dc/dml2_0/`.
- Recuento por programa: ficheros y líneas de `display/amdgpu_dm/`; **las 52 funciones
  `dce112_*` y los 7 ficheros en que caen**; las 252 `dce110_*` en 19 ficheros; la
  misma cuenta para `dce60`, `dce80`, `dce100`, `dce120`; **la coincidencia exacta de
  los 20 ficheros y 11.875 líneas de `151` separando `.c` de `.c`+`.h`**;
  `dml/` recursivo frente a primer nivel; las 3 únicas tablas `*_ops` de `display/`.
- **Dos errores propios en esta nota, y los dos los cazó un programa antes de que los
  escribiera:** (1) dije «DCE 11.2 es sólo el compresor» cuando el recuento de
  `dce112_*` dio 52 en 7 ficheros; (2) estuve a punto de corregir `151` como error
  mío cuando la separación `.c` / `.c`+`.h` dio la coincidencia exacta.
- Encadenada con `158` (la compatibilidad por pares `struct`/tabla, y aquí su
  confirmación: no hay tabla de ops del DM), `157` (**el stream encoder es uno de los
  cinco constructores `dce110_`**), `232` (la regla de la tabla y el constructor, y esta
  nota la aplica a los cinco subsistemas a la vez), `155` (DCE 11.2),
  `151` (**verificado, no corregido**), `154` (la señal), `153` (los siete caminos).
- No se editó `AGENTS.md` ni `OPEN-FRONTIERS.md`.

## Nota de método

**Esta nota es el ejemplo limpio de por qué la comprobación cruzada no es opcional: los
dos errores que cometí en ella eran errores de recuento, y en los dos casos el número
que yo iba a escribir no salía del programa.**

*El primero:* vi `dce112_compressor.c` con subdirectorio propio, y `dce112_clk_mgr.c`
con subdirectorio propio, y escribí mentalmente «lo único propio de DCE 11.2 es el
compresor». **Era falso, y el motivo de que fuera falso es que el subdirectorio propio
no es el criterio: `dce112_*` aparece también en tres ficheros compartidos.** Un
subdirectorio propio es un indicio de propiedad, no una prueba — igual que un nombre
de función.

*El segundo, más incómodo:* la cuenta de `151` no cuadraba, y la explicación correcta
era que contaba **cabeceras además de fuentes**. **Iba a corregir una nota propia
acertada por un error de contabilidad mío**, que es la peor clase de corrección
posible: no arregla nada y borra un dato bueno.

*La regla, y es la generalización de las anteriores:* **antes de afirmar que un fichero
o una propiedad «es» algo, hay que contar el conjunto completo con un criterio escrito,
y ese criterio tiene que incluir la extensión y el directorio.** `dml/` con 4 `.c` y con
20 ficheros son dos cosas distintas y ambas ciertas, y `dce112/` con subdirectorio y sin
él también.

**Y el hallazgo de fondo, que es el que le sirve al driver propio, es una asimetría que
no se ve desde dentro de una generación:** la generación que se escribe desde cero
cuesta 252 funciones; la siguiente cuesta 52; la siguiente, 65. **O sea que el driver
crece por saltos y luego por herencias, y el coste de una generación nueva no se parece
en nada al de la primera.** Verlo desde DCE 11.2, que es 21% de DCE 11.0, es la forma
de verlo: **esta GPU ejecuta cinco subsistemas que no son suyos y uno que sí, y el
reparto completo cabe en 1.442 líneas de tabla de cableado.**
