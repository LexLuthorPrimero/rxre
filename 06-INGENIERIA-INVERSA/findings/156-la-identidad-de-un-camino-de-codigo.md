# 156 · La identidad de un camino de código la da la tabla de punteros, no el nombre de la función

```
CLASSIFICATION=DOCUMENTATION · TRACK=STATIC
CORPUS=RESEARCH/working/linux-7.1.3 · HARDWARE_SCOPE=HOST-C/RX550/0000:01:00.0
WORK_CLASS=READ_ONLY/EVIDENCE · WRITE_EXECUTION=NONE · MODIFICATIONS=0
RUNTIME=NOT_RUN · GPU INTACTA
```

## Qué resuelve

**Tres afirmaciones mías refutadas, por la misma causa y en las dos direcciones.** Y
el mecanismo que las resuelve, que es una sola cosa: **una función se llama
`dce110_*` y puede ser el camino de DCE 11.2, porque lo que decide es quién la mete
en su tabla de punteros y quién construye el objeto.**

## 1 · El campo que esta máquina tiene y DCE 10.0 no

`dce_stream_encoder.c:322-323`, y el guard es la propia tabla de swizzle:

```c
        if (enc110->se_mask->DP_VID_M_DOUBLE_VALUE_EN)
                REG_UPDATE(DP_VID_TIMING, DP_VID_M_DOUBLE_VALUE_EN, 1);
```

**`147` llamó "comprobación de presencia" a este patrón sin nombrarlo. Aquí está la
instancia concreta: `if (se_mask->FIELD)`.** La máscara CERO **es** el test, y el
mismo código se comporta distinto en DCE 10.0 y en DCE 11.2 según lo que diga la
tabla. `PROVEN`.

**Y `mmDP_VID_TIMING` tiene siete copias**, lo que responde a una pregunta abierta
desde `151`:

| registro | offset | diferencia |
|---|---|---|
| `mmDP0_DP_VID_TIMING` | `0x4aa8` | — |
| `mmDP1_DP_VID_TIMING` | `0x4ba8` | `0x100` |
| `mmDP2_DP_VID_TIMING` | `0x4ca8` | `0x100` |
| `mmDP3_DP_VID_TIMING` | `0x4da8` | `0x100` |
| `mmDP4_DP_VID_TIMING` | `0x4ea8` | `0x100` |
| `mmDP5_DP_VID_TIMING` | `0x4fa8` | `0x100` |
| `mmDP6_DP_VID_TIMING` | **`0x54a8`** | **`0x500`** |

**Siete declarados, y el paso NO es constante: cinco de `0x100` y el último de
`0x500`.** Medido por programa; mi primera versión de esta nota afirmó "paso constante" y el programa imprimió `paso constante: False` antes de que lo leyera.

**⇒ Siete salidas de vídeo DisplayPort replicadas en el mapa de registros de DCE
10.0.** Es el mismo número que `MAX_NUMBER_OF_EXT_DISPLAY_PATH` de `153` —7— por un
camino distinto: uno es la constante del firmware, el otro el factor de replicación
del registro. `PROVEN_DERIVED`, y **la concordancia de dos números que no tienen por
qué coincidir, por tercera vez en esta tanda** (las otras dos: `8+4+4+16=32` en
`153` y `ENUM_ID_1..7` contra `MAX_NUMBER_OF_EXT_DISPLAY_PATH`).

**Y la salida de DVI, en el mismo bloque:** `mmDP_VID_TIMING` es la copia 0 y hay
`DIG_FE_CNTL` en la lista de swizzle, que es el selector de fuente digital. **El
`SELECT` está en `dce112_resource.c`, el `DP_VID_TIMING` está en `gmc_v8_0.c` — dos
dominios.**

## 2 · Las tres refutaciones

### R1 — `155`: «DCE 11.2 no usa el tipo `dce110_stream_encoder`»

**`REFUTED`.** Conté las apariciones en `dce112_hwseq.c` — cero — y generalicé de un
fichero al chip.

```c
dce112_resource.c:513   struct dce110_stream_encoder *enc110 =
dce112_resource.c:514           kzalloc_obj(struct dce110_stream_encoder);
dce112_resource.c:519   dce110_stream_encoder_construct(enc110, ctx, ctx->dc_bios, eng_id, ...
```

**El propio recurso de DCE 11.2 reserva un `dce110_stream_encoder` y lo construye con
el constructor de DCE 11.0.** `PROVEN`.

### R2 — `148`: «las cuatro escrituras están en código de DCE 11.0, no en el de esta GPU»

**`REFUTED`.** `dce110_stream_encoder_set_stream_attribute_helper` —la función que
`148` declaró ajena a esta máquina— **es el cuerpo compartido de dos operaciones
públicas:**

```
dce110_stream_encoder_hdmi_set_stream_attribute   L534  ->  llama a la helper en L555
dce110_stream_encoder_dvi_set_stream_attribute    L651  ->  llama a la helper en L673
```

**No es una función auxiliar de DCE 11.0: es la implementación común de los
setters de HDMI y de DVI.** Y ambos setters, y el setter de DP, están en la misma
tabla:

```c
dce_stream_encoder.c:1525   static const struct stream_encoder_funcs dce110_str_enc_funcs = {
dce_stream_encoder.c:1526           .dp_set_stream_attribute =
dce_stream_encoder.c:1527           dce110_stream_encoder_dp_set_stream_attribute, ...
```

**Y esa tabla es la de esta máquina, por R1.** `PROVEN_DERIVED`.

### R3 — `148`: «el umbral de 340 MHz no es programable en esta GPU»

**Ya `REFUTED` en `155`**, y R2 explica por qué: no es que el campo no existiera, es
que la función que lo escribe se llama `dce110_*` y yo tomé el nombre por la
pertenencia.

## 3 · El error, y su forma exacta

**Tres errores, y los tres son el mismo: yo afirmé algo sobre el chip a partir de
una observación de un fichero o de un nombre.**

| | lo observado | lo afirmado | dirección |
|---|---|---|---|
| `148` R2 | una función llamada `dce110_*` | "es código de DCE 11.0" | **existencia de más** |
| `148` R3 | el campo no estaba en la lista `DCE80_100` | "no existe en esta GPU" | **existencia de menos** |
| `155` R1 | 0 apariciones en `dce112_hwseq.c` | "DCE 11.2 no usa el tipo" | **ausencia de más** |

**Y los tres se habrían evitado con la misma pregunta, que es la de `155`: ¿qué
variante se instancia?** En los tres casos la respuesta estaba a una línea de la que
ya tenía.

**Lo especialmente incómodo: R1 era una corrección de R2, y R1 es el mismo error que
R2.** Corregí una generalización excessive haciendo otra generalización excessive,
en dirección contraria. `PROVEN_DERIVED` sobre el patrón, y es el peor error de la
tanda por una razón concreta: **un error de generalización corregido con otro error de
generalización no se corrige, se desplaza.**

## 4 · La regla, y es la más fuerte de la tanda

> **La identidad de un camino de código la establece la tabla de punteros a función y
> el constructor del objeto. Ni el nombre de la función, ni el del fichero donde está,
> ni el de la macro que la lista.**

**Los tres hechos que lo destacan, y los tres en un solo fichero:**

```
dce112_resource.c:519   dce110_stream_encoder_construct(...)   <- quién construye
dce_stream_encoder.c:1525  dce110_str_enc_funcs               <- qué tabla recibe
dce_stream_encoder.c:322   if (enc110->se_mask->FIELD)        <- qué campos existen
```

**El nombre `dce110_` aparece en los tres, y en ninguno de los tres significa
"esto sólo se ejecuta en DCE 11.0".** Significa "este es el código de la generación
11.0 **y sus sucesoras**, porque la successors no reescribieron la tabla".

**Y eso explica por qué la tabla de swizzle de `147` existe en absoluto: no es
decoración, es el mecanismo de compatibilidad.** Un campo que no existe en tu
generación tiene máscara cero; un campo que existe la tiene; y **el mismo código, sin
una sola condición de versión, sirve para las dos.** `PROVEN_DERIVED`, y es la
respuesta a por qué amdgpu puede mapear una RX550 — Polaris12, registros DCE 10.0— a
un camino de código de DCE 11.2 sin bifurcar una línea.

## Lo que NO cierra

| afirmación | estado |
|---|---|
| El guard `if (se_mask->FIELD)` es la prueba de presencia | `PROVEN` |
| `mmDP_VID_TIMING` tiene 7 copias, paso no uniforme | `PROVEN` (por programa) |
| Siete salidas de vídeo DP en el mapa de registros | `PROVEN_DERIVED` |
| 7 = `MAX_NUMBER_OF_EXT_DISPLAY_PATH`, por vía independiente | `PROVEN_DERIVED` |
| `155`: DCE 11.2 no usa `dce110_stream_encoder` | **`REFUTED`** |
| `148`: la helper es código de DCE 11.0, no de esta GPU | **`REFUTED`** |
| `148`: el reloj de canal no es programable | **`REFUTED`** |
| La helper es el cuerpo compartido de los setters de HDMI y DVI | `PROVEN` |
| Los tres caminos están en `dce110_str_enc_funcs` | `PROVEN` |
| La tabla de swizzle es el mecanismo de compatibilidad | `PROVEN_DERIVED` |
| `dce120` y `dce60` también usan el tipo | `PROVEN` (aparecen en sus recursos) |
| Por qué el salto de DP5 a DP6 es `0x500` y no `0x100` | **`NOT_DETERMINED`** |
| Cuántas de las 7 salidas existen en esta placa | **`NOT_DETERMINED`** — firmware |
| Si el reloj de canal de esta GPU se programa en la práctica | **`NOT_DETERMINED`** |
| `DP_VID_M_DOUBLE_VALUE_EN`, qué significa "M DOUBLE VALUE" | **`NOT_DETERMINED`** |

**La primera de las abiertas es la única que se puede cerrar leyendo el header de
registros, y es la que explica el último número raro de esta tanda: un factor de
replicación no uniforme con un salto de `0x500` en la última copia.**

## Procedencia

- `STATIC` -- `display/dc/dce/dce_stream_encoder.c:267-330` (el setter de DP y el
  guard de la máscara), `:505-560` y `:651-680` (los setters de HDMI y DVI, y las
  llamadas a la helper), `:1490-1532` (`dce110_str_enc_funcs` y sus entradas),
  `display/dc/resource/dce112/dce112_resource.c:513-519` (la reserva y la
  construcción del encoder), `:300-304` (la macro de swizzle, de `155`),
  `display/dc/dce/dce_stream_encoder.h:314` `:327` `:497` `:630` (el campo en las dos
  listas y en los dos `struct`), `display/include/grph_object_ctrl_defs.h:274`
  (de `153`).
- Medición, por programa: el paso entre las siete copias de `DP_VID_TIMING`, impreso
  con las seis diferencias y el veredicto `paso constante: False`; el recuento de
  ficheros que contienen `dce110_stream_encoder`; la función envolvente de `L322`,
  de `L555` y de `L673`.
- **Un error mío dentro de esta nota, y el programa lo cazó:** mi primer script
  imprimió `paso constante: False` y a la vez calculó `256 // 1024 = 0 KiB`, y yo
  iba a escribir "paso constante de 1 KiB". **Ni el booleano ni la división se leen
  antes de escribir.**
- Encadenada con `155` (**cuyo `PROVEN_ABSENT` esta nota refuta**), `153` (las siete
  rutas del firmware, con las que concuerda el recuento de copias),
  `148` (**dos de sus tres afirmaciones refutadas**), `147` (la tabla de swizzle y el
  patrón del guard), `151` (los límites del DC, y el `NOT_DETERMINED` de cuántos DIG
  hay que este cabo cierra), `145` (la comprobación cruzada como método).
- No se editó `AGENTS.md` ni `OPEN-FRONTIERS.md`.

## Nota de método

**Tres refutaciones mías en una nota, y las tres del mismo error, y una de ellas era
una corrección de otra del mismo error.** Eso es lo que hace que este bloque de notas
-sea distinto de los anteriores: no he encontrado un hecho nuevo, he encontrado que
**la forma de mis errores tiene una causa identificable.**

*Y esa causa es una sola: yo afirmo sobre el chip a partir de una observación del
fichero.* En las dos direcciones —`148` afirmó existencia donde había un nombre, `155`
afirmó ausencia donde había un cero— y en las dos el mismo nombre o el mismo cero
significaba exactamente lo contrario de lo que yo leí.

**La regla que sale es la de `155`, y su inversa, juntas:** no preguntes
qué función se está ejecutando, y no preguntes tampoco cuál no se está ejecutando.
Pregunta qué tabla de punteros recibe el objeto y quién lo construyó.** Las dos
preguntas que yo hacía —"¿esta función es de esta generación?" y "¿esta generación
usa esta función?"— son la misma pregunta mal hecha, porque responden por el nombre
en vez de por el cableado.

**Y hay una observación de coste que vale por todas:** las tres refutaciones se
cerraron en **una** invocación de shell cada una, después de cuatro notas de
trabajo. *El trabajo no estaba en la búsqueda; estaba en no comprobar el cableado
antes de afirmar.*
