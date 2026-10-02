# 158 · La confianza la da el par (struct, tabla), no el chip

```
CLASSIFICATION=DOCUMENTATION · TRACK=STATIC
CORPUS=RESEARCH/working/linux-7.1.3 · HARDWARE_SCOPE=HOST-C/RX550/0000:01:00.0
WORK_CLASS=READ_ONLY/EVIDENCE · WRITE_EXECUTION=NONE · MODIFICATIONS=0
RUNTIME=NOT_RUN · GPU INTACTA
```

## Qué resuelve

La pregunta que `157` dejó abierta, y la cierra por el lado de la compatibilidad:
**si el conjunto de operaciones crece al subir de generación, o al cambiar de familia.**

**No crece al subir de generación. Crece al cambiar de familia, y al cambiarla cambia
el `struct`.** Medido: seis generaciones DCE, **una** tabla, veintidós entradas,
idénticas. El crecimiento de 22 a 35 ocurre sólo al dejar la familia DCE.

## 1 · Las doce tablas, y dos `struct` distintos

| | struct | miembros | tablas |
|---|---|---|---|
| codificadores DCE y DCN | `stream_encoder_funcs` | **38** | **11** |
| codificador HPO | `hpo_dp_stream_encoder_funcs` | **15** | **1** |

**Doce tablas, cincuenta y tres miembros declarados, dos tipos de interfaz.** `PROVEN`.

**Y hay una quinta colisión de nombres en la lista, y es el que me hizo equivocar:**

```
dc/dio/dcn30/dcn30_dio_stream_encoder.c:828    static const struct stream_encoder_funcs
                                               dcn30_str_enc_funcs = { ... }   29 entradas
dc/hpo/dcn31/dcn31_hpo_dp_stream_encoder.c:745  static const struct hpo_dp_stream_encoder_funcs
                                               dcn30_str_enc_funcs = { ... }   15 entradas
```

**Mismo nombre de tabla, `struct` distinto, fichero distinto, recuento distinto.**
Los cinco: `pptable.h`, `dcn10`/`dce100`, `dc_types.h`/`dc_hw_types.h`,
`display/include/`/`display/dc/include/`, y ahora éste. `PROVEN`.

## 2 · El contraste que sostiene la nota: el par, medido

| | struct | tabla | entradas | cobertura | NULL |
|---|---|---|---|---|---|
| **DCE 11.0/11.2 — esta máquina** | `stream_encoder_funcs` (38) | `dce110_str_enc_funcs` | **22** | **58%** | 16 |
| DCE analógico (VGA) | `stream_encoder_funcs` (38) | `dce110_an_str_enc_funcs` | **2** | **5%** | 36 |
| HPO DCN 3.1 | `hpo_dp_stream_encoder_funcs` (**15**) | `dcn30_str_enc_funcs` (HPO) | **15** | **100%** | **0** |

**Las tres, calculadas por programa sobre el mismo par `(struct, tabla)`.** `PROVEN`.

**⇒ La completitud de una tabla es una propiedad del par, no del chip.** El mismo
`struct` de 38 miembros está cubierto al 5%, al 58% y al 92% según la tabla que se le
ponga; y un `struct` de 15 miembros está cubierto al 100%. `PROVEN_DERIVED`.

**Esto es lo que explica, y por fin con la regla, por qué
`link_hwss_hpo_dp.c:79-80` no comprueba y `link_hwss_dio.c:67` sí:**

```
link_hwss_dio.c:67     if (stream_enc->funcs->enable_stream)      <- tabla al 58%: comprueba
link_hwss_hpo_dp.c:79  stream_enc->funcs->enable_stream(...)      <- tabla al 100%: no comprueba
```

**El llamante no necesita saber el chip. Necesita saber la tabla, y el contrato de la
tabla lo fija su `struct`.** `PROVEN_DERIVED`.

## 3 · Y corrige a `157`, que acertó la conclusión y se inventó la razón

`157` afirmó: «la tabla de HPO es completa, la de DCE no, y por eso su llamante no
comprueba». **La conclusión era correcta. La razón la di por buena sin medirla, y
además afirmé «su propia tabla» creyendo que era el mismo `struct`.**

**No lo es: HPO tiene su propio `struct`, de quince miembros, y lo cumple entero.**

```
dcn31_hpo_dp_stream_encoder.c:745   15 entradas sobre 15 miembros   COMPLETA
```

**Y las dos operaciones que `157` dijo que vivían «en la tabla de HPO» no son de HPO:**
`enable_stream` y `map_stream_to_link` están en **3 de las 11** tablas de
`stream_encoder_funcs` — `dcn35`, `dcn42`, `dcn401` — **y en ninguna de las otras ocho**,
DCE incluida. `PROVEN`.

**Es decir: lo que `157` Tomato por «explicación» era una coincidencia de nombre.** La
explicación real es otra y es más fuerte: **HPO necesitaba un conjunto de operaciones
distinto, así que se dio un `struct` distinto, y un `struct` distinto con una tabla
propia da la opción de poder exigir completitud.**

## 4 · La familia DCE no crece, y se mide en seis ficheros

**Seis recursos DCE cablean la tabla digital:**

```
dc/resource/dce60/dce60_resource.c:617      dc/resource/dce110/dce110_resource.c:538
dc/resource/dce80/dce80_resource.c:623      dc/resource/dce112/dce112_resource.c:519
dc/resource/dce100/dce100_resource.c:500    dc/resource/dce120/dce120_resource.c:779
```

**Los seis llaman a `dce110_stream_encoder_construct` (`dce_stream_encoder.c:1563`), que
pone `&dce110_str_enc_funcs` (`L1572`).** Seis generaciones —6.0, 8.0, 10.0, 11.0,
11.2, 12.0— **una tabla, veintidós entradas, el mismo conjunto.** `PROVEN`.

**⇒ El identificador `dce110_` de esa tabla no significaDCE 11.0: significa «la
generación en la que se escribió», y las cinco siguientes la heredaron tal cual.** Es
`156` rectificado por el lado de la aritmética: **seis ficheros de recursos distintos
reducidos a un solo receptor.**

### Y el codificador analógico, que es la respuesta sobre VGA

```
dce60_resource.c:612    dce110_analog_stream_encoder_construct(...)
dce80_resource.c:618    dce110_analog_stream_encoder_construct(...)
dce100_resource.c:495   dce110_analog_stream_encoder_construct(...)
```

**Sólo tres. Ni `dce110`, ni `dce112`, ni `dce120`.** `PROVEN`.

**⇒ Esta máquina —que es `dce112_resource.c:519`— no tiene codificador de stream
analógico. No hay camino VGA en el driver para este chip.** `PROVEN_ABSENT`, y es la
primera respuesta firme a la pregunta que venía abierta desde `151`: «cuáles son
DP/HDMI/VGA/LVDS». **VGA: ninguno en esta ruta.**

**Y su tabla tiene dos entradas, y son las dos de selección de salida digital:**

```
dce_stream_encoder.c:1581   static const struct stream_encoder_funcs dce110_an_str_enc_funcs = {
dce_stream_encoder.c:1582           .dig_connect_to_otg = dig_connect_to_otg,
dce_stream_encoder.c:1583           .dig_source_otg = dig_source_otg,
```

**Un codificador analógico sólo sabe elegir por dónde sale la señal.** Coherente: un
CRT no tiene temporización digital que programar. **Y el 5% de cobertura no es una
carencia: es un `struct` de 38 del que esa salida sólo necesita dos.** `PROVEN_DERIVED`.

## 5 · La «curva» no es una curva, y la secuencia medida

Ordenando por generación DCN, sobre la base de 38:

| tabla | entradas | % | respecto a la anterior |
|---|---|---|---|
| `dce110` (esta máquina) | 22 | 58% | — |
| `dcn10` | 23 | 61% | +2, −1 (`lvds_set_stream_attribute`) |
| `dcn20` | 30 | 79% | +7 |
| `dcn30` | 29 | 76% | **+0, −1** (`send_immediate_sdp_message`) |
| `dcn32` | 30 | 79% | +2, −1 (`get_fifo_cal_average_level`) |
| `dcn35` | 35 | **92%** | +5 |
| `dcn42` | 32 | 84% | +0, **−3** (`dp_set_odm_combine`, `get_pixels_per_cycle`, `is_fifo_enabled`) |
| `dcn314` | 32 | 84% | +2, **−2** (`enable_stream`, `map_stream_to_link`) |
| `dcn401` | 33 | 87% | +2, −1 (`is_fifo_enabled`) |

**Secuencia: 22, 23, 30, 29, 30, 35, 32, 32, 33. NO es monótona: tres caídas.** `PROVEN`.

**Y las tres caídas no son pérdidas, son mudanzas:** la unión de las once tablas pone
los **38** miembros, y **ninguna tabla individual los pone todos.** Máximo alcanzado:
**35 de 38, el 92%, `dcn35`.** `PROVEN`.

**⇒ La constante estructural es esta: toda operación la implementa alguna generación, y
toda generación deja alguna operación a NULL.** No hay un punto en la serie en el que
la tabla esté completa, porque la completitud no es el objetivo: es la seguridad de
`if (funcs->X)`. `PROVEN_DERIVED`.

**Y por eso el orden de las carpetas no es un linaje**: `dcn314` y `dcn401` son
generaciones Navi paralelas a `dcn35`, no sucesoras suyas. La serie ordenado da
`35 → 32 → 32 → 33`, que es un descenso aparente y no una historia. `PROVEN_DERIVED`.

## Lo que NO cierra

| afirmación | estado |
|---|---|
| 12 tablas, 2 `struct`, 38 + 15 miembros | `PROVEN` (por programa) |
| La unión de las 11 pone los 38; ninguna los pone todos | `PROVEN` |
| Máximo 35 de 38 (`dcn35`, 92%) | `PROVEN` |
| La completitud es del par (struct, tabla) | `PROVEN_DERIVED` |
| HPO: 15 sobre 15, 100%, y por eso su llamante no comprueba | `PROVEN` |
| `157`: por qué HPO no comprueba | **CORREGIDA** — razón equivocada |
| `enable_stream` en 3 de 11 tablas, no es de HPO | `PROVEN` |
| 6 generaciones DCE, una tabla, 22 entradas idénticas | `PROVEN` |
| DCE 11.2 no construye codificador analógico | `PROVEN_ABSENT` |
| ⇒ Sin camino VGA en esta máquina | `PROVEN_ABSENT` (en el driver) |
| El analógico sólo sabe elegir DIG: 2 de 38 | `PROVEN_DERIVED` |
| La serie no es monótona; tres caídas son mudanzas | `PROVEN` |
| `dcn314`/`dcn401` paralelos a `dcn35`, no sucesores | `PROVEN_DERIVED` |
| Si la placa tiene un conector VGA cableado a otro punto | **`NOT_DETERMINED`** |
| Cuál de las 22 se llama en la práctica aquí | **`NOT_DETERMINED`** |
| Si el Bios expone VGA aunque el driver no lo use | **`NOT_DETERMINED`** |

**La primera de las abiertas, y sólo una, es de hardware: si la placa tiene un
conector VGA que el driver ignora. Se lee del Bios, y con eso se cierra el conjunto de
salidas físicas de esta máquina.**

## Procedencia

- `STATIC` -- `display/dc/inc/hw/stream_encoder.h:133-278` (los 38 miembros),
  `display/dc/hpo/dcn31/dcn31_hpo_dp_stream_encoder.c:745-775` (el `struct` de 15 y su
  tabla), `display/dc/dce/dce_stream_encoder.c:1563-1579` (el constructor digital),
  `:1581-1584` (la tabla analógica), `:1586-1600` (el constructor analógico),
  `display/dc/resource/dce112/dce112_resource.c:519`,
  `display/dc/resource/dce110/dce110_resource.c:538`,
  `display/dc/resource/dce120/dce120_resource.c:779`,
  `display/dc/resource/dce100/dce100_resource.c:495` `:500`,
  `display/dc/resource/dce80/dce80_resource.c:618` `:623`,
  `display/dc/resource/dce60/dce60_resource.c:612` `:617`,
  `display/dc/dio/dcn30/dcn30_dio_stream_encoder.c:828`,
  `display/dc/link/hwss/link_hwss_dio.c:67-71`,
  `display/dc/link/hwss/link_hwss_hpo_dp.c:74-81`.
- Recuento por programa: los 38 y los 15 miembros de cada `struct`; las 12 tablas con
  su número de entradas; **la unión de las once frente a los 38**; los deltas de cada
  tabla respecto de la anterior; la presencia de `enable_stream` y
  `map_stream_to_link` en cada una de las 12; los 6 ficheros que cablean cada uno de
  los dos constructores.
- Encadenada con `157` (**esta nota le corrige la razón**), `156` (la identidad por la
  tabla y el constructor — y aquí, por fin, contada), `155` (DCE 11.2),
  `151` (**cierra su `NOT_DETERMINED` sobre VGA**), `149` (DSC ausente), `147` (la
  tabla de swizzle, el otro mecanismo de nulabilidad), `154` (la señal).
- No se editó `AGENTS.md` ni `OPEN-FRONTIERS.md`.

## Nota de método

**El error de `157` fue un nombre, y el de esta nota era el mismo nombre; pero el
descubrimiento útil no es ninguno de los dos, es la existencia de la segunda interfaz.**

*`157` vio un `if` sin comprobar, se aprestó a explicarlo con que «la tabla de HPO es
completa», y esa frase era verdad. Lo que no sabía es que había un segundo `struct` de
tablas, con quince miembros, en otra carpeta, con otro nombre de fichero — y que
«completo» es relativo al `struct`.* La afirmación verdadera llegó antes que el
concepto que la sostiene, y por eso no se podía comprobar: **no había nada que
comprobar hasta que se miró el `struct` de HPO.**

**Y esa es la forma general del error de esta tanda por segunda vez: la conclusión
correcta con el soporte equivocado.** Ya ocurrió con `151` («"dcn" not in lista» es
igualdad, no subcadena — conclusión correcta, prueba mal construida) y con `150` (dos
`grep` mal formados). **La conclusión acertada es más frecuente de lo que parece, y
es también la peligrosa: no señala nada roto, así que no se investiga, y el concepto
que falta se queda sin escribir.**

*La regla que sale es de una frase:* **antes de afirmar que un conjunto de datos está
completo, hay que contar contra qué se compara.** `157` trató "completo" como
adjetivo; esta nota lo trata como cociente, y el cociente necesita dos números
medidos.

**Y el resultado de fondo es el que pedía la pregunta de `157`, y es un contraejemplo
a la intuición:** la serie de tablas de stream encoder **no es una curva de crecimiento
por generación — no crece dentro de la familia DCE, se queda clavada en 22 mientras seis
generaciones la heredan.** El driver no envejece por acumulación de operaciones;
envejece por **bifurcación de familia**, y en el único sitio donde el conjunto de
operaciones hubo que ser de verdad otro — HPO — es donde existe un `struct` aparte, con
quince miembros y una tabla que los cumple todos.

*Ese es el resultado que le sirve a un driver propio:* **no hay que implementar 38
operaciones.** Hay que implementar las que tu chip pueda, dejar el resto a `NULL`, y
usar `if (funcs->X)` en cada punto de llamada. HPO lo demuestra por el otro lado: si
tu conjunto de operaciones es pequeño y tus tablas lo cubren entero, puedes saltarte
la comprobación — pero sólo porque declaraste una interfaz a tu medida en vez de
heredar la de otro.*
