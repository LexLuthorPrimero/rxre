# 147 · El modelo de programación del stream encoder de DCE 10.0: 89 de 130 campos

```
CLASSIFICATION=DOCUMENTATION · TRACK=STATIC
CORPUS=RESEARCH/working/linux-7.1.3 · HARDWARE_SCOPE=HOST-C/RX550/0000:01:00.0
WORK_CLASS=READ_ONLY/EVIDENCE · WRITE_EXECUTION=NONE · MODIFICATIONS=0
RUNTIME=NOT_RUN · GPU INTACTA
```

## Qué resuelve

**El otro extremo del objetivo final.** `144` demostró que falta la entrada
—el ioctl—; esto es la salida: **cómo se programa un stream encoder en esta GPU**, con
el número exacto de campos que existen y los que no.

Y tres trampas de nombre, que en este corpus han sido la causa de tres errores
distintos.

## 1 · La estructura: dos tablas y una macro

`display/dc/dce/dce_stream_encoder.h` no expone prototipos. Expone **dos tablas**:

```c
struct dce_stream_encoder_shift {   /* 130 campos, uint8_t  */
        uint8_t AFMT_GENERIC_INDEX;
        ...
        uint8_t DIG_SOURCE_SELECT;
        uint8_t DAC_SOURCE_SELECT;
};

struct dce_stream_encoder_mask {    /* 130 campos, uint32_t */
        uint32_t AFMT_GENERIC_INDEX;
        ...
        uint32_t DIG_SOURCE_SELECT;
        uint32_t DAC_SOURCE_SELECT;
};
```

**Verificado por programa: los dos `struct` tienen exactamente los mismos 130
nombres, la diferencia simétrica en los dos sentidos es vacía.** `PROVEN`.

**Y una sola lista genera las dos.** `dce_stream_encoder.h:116-117`:

```c
#define SE_SF(reg_name, field_name, post_fix)\
        .field_name = reg_name ## __ ## field_name ## post_fix
```

Con `__SHIFT` sale `reg__FIELD__SHIFT` y con `_MASK` sale `reg__FIELD_MASK`. **Es
por eso que las dos tablas no pueden discrepar: no están escritas dos veces.**

**Y el modelo de programación del DCE sale de aquí:** el mismo campo lógico está en
posiciones de bit distintas en cada instancia de stream encoder, y por eso hay
tablas de *shift* y de *máscara* en lugar de acceso directo por nombre.

## 2 · Cuál de esas tablas usa esta GPU

`display/dc/resource/dce100/dce100_resource.c:249-255`:

```c
static const struct dce_stream_encoder_shift se_shift = {
                SE_COMMON_MASK_SH_LIST_DCE80_100(__SHIFT)
};

static const struct dce_stream_encoder_mask se_mask = {
                SE_COMMON_MASK_SH_LIST_DCE80_100(_MASK)
};
```

**Y hay seis directorios de tabla, uno por generación de DCE:** `dce60`, `dce80`,
`dce100`, `dce110`, `dce112`, `dce120`. **Para esta GPU es `dce100`.**

**Y el nombre de la macro dice algo importante: `DCE80_100`.** DCE 8.0 y DCE 10.0
**comparten la misma lista**, porque el layout del stream encoder es idéntico en
ambas. `PROVEN` por el nombre de la macro y por el contenido de las dos
definiciones, que son la misma.

## 3 · La descomposición, y el número que decide

Recuento de los `SE_SF` de cada lista, impreso por programa:

| lista | campos | registros distintos |
|---|---|---|
| `SE_COMMON_MASK_SH_LIST_DCE_COMMON` | 86 | 36 |
| `SE_COMMON_MASK_SH_LIST_DCE80_100` (delta de esta GPU) | **3** | 2 |
| **puestos para DCE 10.0** | **89** | |
| **dejados en cero** | **41** | |
| declarados en el `struct` | 130 | |

**Y el delta de DCE 10.0 sobre el conjunto común son tres campos, y son estos:**

```
+ TMDS_CNTL          . TMDS_PIXEL_ENCODING
+ TMDS_CNTL          . TMDS_COLOR_FORMAT
+ DAC_SOURCE_SELECT  . DAC_SOURCE_SELECT
```

**Eso es una afirmación fuerte y comprobable: el DCE 10.0 no añade ningún campo de
DisplayPort ni de audio sobre el conjunto común. Lo único que añade sobre DCE 6/8 es
codificación de píxel TMDS, formato de color TMDS, y el selector de salida DAC.**
`PROVEN`, por recuento.

**Y la comparación con la lista de al lado lo confirma.** `SE_COMMON_MASK_SH_LIST_DCE110`
(DCE 11.0) añade **siete** campos, entre ellos `HDMI_CONTROL.HDMI_CLOCK_CHANNEL_RATE`
y `AFMT_CNTL.AFMT_AUDIO_CLOCK_EN`.

**⇒ Esta GPU no tiene `HDMI_CLOCK_CHANNEL_RATE` en el stream encoder.** Es un hecho
sobre el chip, no sobre el driver, y sale de una comparación de dos listas. `PROVEN`.

## 4 · Los 41 que quedan en cero: agrupados

| prefijo | campos | qué son |
|---|---|---|
| `AFMT_*` | **20** | audio (HDMI audio format) |
| `DP_*` | **18** | DisplayPort MSA, timings y DB |
| `HDMI_*` | **3** | reloj de canal, scramble, DB |

**Y "quedan en cero" no es una hipótesis: en C, un campo de un `struct` estático que
no aparece en el inicializador se pone a cero.** Y una máscara de cero significa que
una escritura a ese campo no llega a ningún bit. `PROVEN_DERIVED`.

**De los 41, sólo 3 aparecen en la lista de DCE 110.** Los otros 38 no están en
ninguna lista: son campos declarados para chips que no han añadido lista, o
históricos.

### Y la comprobación que hacía falta: ¿se usan en esta GPU?

**32 de los 41 aparecen en algún `.c` de `display/dc/`.** Eso, por sí solo, habría
sido una alarma. La comprobación siguiente la deshace:

| campo | dónde se usa | ¿toca esta GPU? |
|---|---|---|
| `AFMT_AUDIO_CLOCK_EN` | `dce_stream_encoder.c:74`, `:740`, `:1388` | **no** — las tres están en funciones `dce110_*` |
| `DP_MSA_HSTART` | `dcn10_stream_encoder.c:444` | **no** — `dcn10` es DCN 1.0, no DCE 10.0 |
| `HDMI_CLOCK_CHANNEL_RATE` | 51 usos | **no** — es campo de DCE 110+ |
| `DP_DB_DISABLE` | 0 usos | inerte por construcción |

**Ninguno de los 41 se alcanza por la ruta de DCE 10.0.** `PROVEN_DERIVED`.

### Y hay una segunda red, visible en el código

`dce_stream_encoder.c:72-76`:

```c
/*we need turn on clock before programming AFMT block*/
        if (REG(AFMT_CNTL))
                REG_UPDATE(AFMT_CNTL, AFMT_AUDIO_CLOCK_EN, 1);

        if (REG(AFMT_VBI_PACKET_CONTROL1)) {
```

**El driver comprueba en tiempo de ejecución que el registro existe, antes de
escribir.** No es un guard de versión: es una **comprobación de presencia por
lectura**, y el registro inexistente devuelve cero.

**⇒ La tabla de swizzle con 41 ceros es la contrapartida estática de esas
comprobaciones en tiempo de ejecución.** El hardware no tiene esos campos, la tabla
lo dice una vez, y el código lo vuelve a preguntar en cadaregister que toca.
`PROVEN_DERIVED`, y es la misma idea que `133` (el MTYPE que no existe en GFX8) aplicada
a otro bloque.

## 5 · Tres trampas de nombre, y las tres han causado un error

| nombre | lo que parece | lo que es |
|---|---|---|
| `pptable.h` | page table | **PowerTune Play Table** — ventiladores y sensores |
| `dcn10_stream_encoder.c` | DCE 10.0 | **DCN 1.0** — otra generación, otro bloque |
| `dce100_resource.c` | — | **DCE 10.0** — ésta sí |

**`dcn10` y `dce100` se diferencian en dos letras y en una generación entera.** Y
`dcn10` está en `display/dc/dio/dcn10/`, mientras que la tabla de esta GPU está en
`display/dc/resource/dce100/`. **Dos directorios, dos familias, dos generaciones.**

**Las tres las cometí o las casi cometo en esta misma tanda:** `pptable.h` en `145`,
y `dcn10` frente a `dce100` en esta nota. **Un nombre de bloque de hardware en amdgpu
codifica la generación de tres formas distintas según la familia, y sólo una de ellas
es decimal.**

*Regla que sale de aquí: en `asic_reg/` y en `display/`, un nombre no es un
identificador, es una codificación. `dce100` es 10.0; `dcn10` es 1.0; `gfx_v8_0` es
8.0; `gmc_8_1` es 8.1. Y no hay un patrón: hay cuatro.*

## Lo que NO cierra

| afirmación | estado |
|---|---|
| Los dos `struct` tienen los mismos 130 nombres | `PROVEN` (por programa) |
| Una macro genera las dos tablas | `PROVEN` (`SE_SF`, `L116-117`) |
| Esta GPU usa la tabla `dce100` | `PROVEN` |
| DCE 8.0 y DCE 10.0 comparten lista | `PROVEN` (nombre de la macro) |
| El delta de DCE 10.0 son 3 campos | `PROVEN` (recuento) |
| 89 de 130 campos programados | `PROVEN` (recuento) |
| 41 en cero: 20 AFMT, 18 DP, 3 HDMI | `PROVEN` (recuento) |
| Esta GPU no tiene `HDMI_CLOCK_CHANNEL_RATE` | `PROVEN` |
| Ninguno de los 41 se alcanza por la ruta DCE 10.0 | `PROVEN_DERIVED` |
| El driver comprueba presencia de registro en runtime | `PROVEN` (`L73`, `L76`) |
| La secuencia completa para encender un stream | **`NOT_DETERMINED`** — requiere `core/dc_sink.c` y `dce_transform.c` |
| La anchura del panel, el timing y la sincronización | **`NOT_DETERMINED`** |
| Si el HDMI de esta placa usa un reloj de canal por otra vía | **`NOT_DETERMINED`** |

**Las tres últimas son un `NOT_DETERMINED` de `CORPUS`, no de hardware, y se cierran
con dos ficheros.** `core/dc_sink.c` y `dce/dce_transform.c` son, con lo ya cerrado
en `143`, `140` y `136`-`139`, la lista de trabajo completa de un driver propio que
quiera dibujar algo.

## Procedencia

- `STATIC` -- `display/dc/dce/dce_stream_encoder.h` (`SE_SF` en `L116-117`,
  `SE_COMMON_MASK_SH_LIST_DCE_COMMON` en `L119`, `..._DCE80_100` en `L291-295`,
  `..._DCE110` en `L297`, los dos `struct` en `L369` y `L502`),
  `display/dc/resource/dce100/dce100_resource.c:249-255` y `:257-262`,
  `display/dc/dce/dce_stream_encoder.c:62-76`, `:740`, `:1388`,
  `display/dc/dio/dcn10/dcn10_stream_encoder.c:444`,
  `display/dc/include/pptable.h` (falso positivo, de `145`).
- Recuentos: `re.findall` sobre las tres listas de macros y sobre los dos `struct`,
  y comparación de conjuntos en los dos sentidos. **Salen de un programa, y el 89/130
  y el 20/18/3 son el resultado, no una estimación.**
- La lista de ficheros `dceNNN_resource.c` y el recuento de los 40 subdirectorios de
  `display/dc/`: `find` + `os.walk`, impreso por programa.
- Encadenada con `146` (el Makefile no es un manifiesto, y `display/dc/` completo),
  `145` (el 99% del corpus, y la falsa corroboración de `pptable.h`),
  `144` (el otro extremo del objetivo: la entrada), `143` (la lista de arranque),
  `140` (el mapa de direcciones), `139` (el PTE, y el precedente de "un campo que no
  existe en este chip"), `133` (el MTYPE ausente en GFX8 — mismo patrón).
- No se editó `AGENTS.md` ni `OPEN-FRONTIERS.md`.

## Nota de método

**La lección de esta nota es una que ya conozco y me ha costado tres veces hoy:
un nombre de hardware es una codificación, no un identificador.**

`pptable.h` es un termostato. `dcn10` es DCN 1.0 y `dce100` es DCE 10.0. Y para
encontrar la tabla de esta GPU pasé por alto `dce100` — que no parece el nombre de
nada — y casi lo sustituyo por `dcn10`, que sí lo parece y es de otra generación.

**Y hay un segundo aprendizaje, que es el de fondo.** Cuando vi que 41 campos
quedaban en cero, la reacción fácil era "eso es un bug o una lista incompleta", y esa
reacción habría producido una nota falsa. **La pregunta que lo evitó fue "¿se usan
en esta GPU?", y la respuesta estuvo en el nombre de la función envolvente
(`dce110_update_generic_info_packet`) y en el nombre del fichero
(`dcn10_stream_encoder.c`).** **Ninguna de las dos cosas se ve en la lista de
campos; las dos se ven en el camino que lleva hasta ellos.**

*Una lista de campos que faltan dice qué falta. El camino que lleva a ellos dice si
importa.* Y el camino —el fichero, la función, la generación, el guard— es donde
está siempre la respuesta, y es donde hay que mirar antes de declarar nada.
