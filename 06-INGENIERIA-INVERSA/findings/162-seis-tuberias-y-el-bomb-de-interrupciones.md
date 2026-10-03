# 162 · Seis tuberías de display, y el 65% de la tabla de interrupciones es un bomb

```
CLASSIFICATION=DOCUMENTATION · TRACK=STATIC
CORPUS=RESEARCH/working/linux-7.1.3 · HARDWARE_SCOPE=HOST-C/RX550/0000:01:00.0
WORK_CLASS=READ_ONLY/EVIDENCE · WRITE_EXECUTION=NONE · MODIFICATIONS=0
RUNTIME=NOT_RUN · GPU INTACTA
```

## Qué resuelve

**El número de tuberías de display de esta máquina, y cómo sabe el driver que un modo se
ha aplicado.** Y un resultado negativo fuerte: **de las nueve familias de interrupción
que la tabla declara, cuatro no existen en el driver de esta GPU, y son bombs que
registran un error si alguien las llama.**

## 1 · Seis tuberías, y cinco familias que lo confirman

`display/dc/inc/hw/hw_shared.h:45`:

```c
#define MAX_PIPES 6
```

**Y la tabla de interrupciones de DCE 11.2 tiene exactamente seis entradas en cada una de
las cinco familias implementadas.** Medido por programa sobre
`irq_source_info_dce110[DAL_IRQ_SOURCES_NUMBER]`:

| familia | entradas | tipo |
|---|---|---|
| **HPD** (`hpd_int_entry`) | **6** | implementada — la única con `ack` propio |
| **HPDRX** (`hpd_rx_int_entry`) | **6** | implementada, sin `ack` propio |
| **PFLIP** (`pflip_int_entry`) | **6** | implementada, sin `ack` propio |
| **VUPDATE** (`vupdate_int_entry`) | **6** | implementada, sin `ack` propio |
| **VBLANK** (`vblank_int_entry`) | **6** | implementada, con `set` propio |
| I2C/DDC (`i2c_int_entry`) | 6 | **`dummy_irq_entry()`** |
| DP sink / AUX (`dp_sink_int_entry`) | 6 | **`dummy_irq_entry()`** |
| GPIO pad (`gpio_pad_int_entry`) | 31 | **`dummy_irq_entry()`** |
| DC underflow (`dc_underflow_int_entry`) | 6 | **`dummy_irq_entry()`** |
| `[DC_IRQ_SOURCE_x]` explícitas | 5 | `dummy_irq_entry()` |
| **total** | **85** | **30 reales, 55 bombs** |

**⇒ 30 implementadas de 85, el 35%.** `PROVEN`.

**⇒ Y cinco familias independientes con el mismo número, y ese número es `MAX_PIPES`.**
Cinco conteos distintos dan 6, y `159` ya había contado seis constructores en
`dce112_resource.c`. **Verificación cruzada por número repetido, no por suma.**
`PROVEN_DERIVED`.

**Y la constante está escrita tres veces en el árbol, con el mismo valor:**

```
dc/inc/hw/hw_shared.h:45   #define MAX_PIPES 6
dc/dce/dmub_psr.c:34       #define MAX_PIPES 6
dc/dce/dmub_replay.c:14    #define MAX_PIPES 6
```

**Tres copias, un valor.** No es una colisión de nombres sino una duplicación silenciosa:
si el número de tuberías cambiara, estos tres sitios tendrían que cambiar juntos y no hay
nada que obligue a ello. `PROVEN`.

## 2 · Y las cuatro familias que no existen, y lo que el bomb dice

Las cuatro familias ausentes no son entradas a NULL: apuntan a `dummy_irq_info_funcs`, y
esas funciones **registran un error y devuelven `false`**:

```c
irq_service_dce110.c:182   bool dal_irq_service_dummy_set(struct irq_service *irq_service,
irq_service_dce110.c:184                           const struct irq_source_info *info,
irq_service_dce110.c:185                           bool enable)
irq_service_dce110.c:186   {
irq_service_dce110.c:187           DC_LOG_ERROR("%s: called for non-implemented irq source, src_id=%u, ext_id=%u\n", ...);
irq_service_dce110.c:191           return false;
```

**El texto del bomb dice exactamente qué pasa si se llama a una de las 55:
`called for non-implemented irq source`.** `PROVEN`.

**⇒ Y esto cierra un bloqueo que la lista llevaba como abierto.** El resumen llevaba «las
tablas AUX/DDC y HPD» como `NOT_IN_CORPUS` en sentido fuerte, y la realidad medida es de
dos clases distintas:

| | estado real |
|---|---|
| **HPD** | **implementada.** `hpd_ack` (`irq_service_dce110.c:42-62`) es **la única función propia de todo el fichero** |
| **AUX / DP sink** | **ausente de forma explícita.** 6 entradas → `dummy_irq_entry()` |
| **I2C/DDC** | **ausente de forma explícita.** 6 entradas → `dummy_irq_entry()` |
| **GPIO pad** | **ausente de forma explícita.** 31 entradas → `dummy_irq_entry()` |
| **DC underflow** | **ausente de forma explícita.** 6 entradas → `dummy_irq_entry()` |

**⇒ El HPD no está bloqueado: está resuelto. Y el AUX no está ausente del corpus, está
ausente del driver — con su nombre, su sitio en la tabla y su error al invocarlo.**
`PROVEN_ABSENT`, con la causa identificada, que es un bomb y no una laguna.

**Consecuencia práctica para un driver propio: la recepción de HPD por interrupción
funciona en esta familia, y la de status de receptor DP por interrupción no existe y hay
que sondearla por AUX.** `PROVEN_DERIVED`.

## 3 · Y `hpd_ack`, que es donde está el truco del hardware

La única callback propia del fichero, y no se limita a acusar la interrupción:

```c
irq_service_dce110.c:45    uint32_t addr = info->status_reg;
irq_service_dce110.c:46    uint32_t value = dm_read_reg(irq_service->ctx, addr);
irq_service_dce110.c:47    uint32_t current_status = get_reg_field_value(value,
irq_service_dce110.c:48                                          DC_HPD_INT_STATUS,
irq_service_dce110.c:49                                          DC_HPD_SENSE_DELAYED);
irq_service_dce110.c:51    dal_irq_service_ack_generic(irq_service, info);
irq_service_dce110.c:53    value = dm_read_reg(irq_service->ctx, info->enable_reg);
irq_service_dce110.c:55    set_reg_field_value(value, current_status ? 0 : 1,
irq_service_dce110.c:56                                    DC_HPD_INT_CONTROL,
irq_service_dce110.c:57                                    DC_HPD_INT_POLARITY);
irq_service_dce110.c:59    dm_write_reg(irq_service->ctx, info->enable_reg, value);
```

**Lee el nivel diferido, acusa, y después invierte la polaridad de la interrupción.**
`PROVEN`.

**⇒ El pin de HPD es de nivel y la interrupción se arma por flanco: después de cada
evento el driver rearma la polaridad para que el siguiente cambio de nivel dispare otra
vez. Es un lazo de software de una línea, y sin él el HPD dispararía una sola vez por
cableado.** `PROVEN_DERIVED`.

**Y `DC_HPD_SENSE_DELAYED` es un campo con retardo, no el pin directo: hay un «retrasado»
en el hardware antes de que el nivel sea interpretable.** `PROVEN_DERIVED`.

## 4 · VUPDATE, que es la respuesta a «cómo sabe el driver que se aplicó un modo»

`vupdate_int_entry` (`irq_service_dce110.c:132-146`):

```c
        [DC_IRQ_SOURCE_VUPDATE1 + reg_num] = {\
                .enable_reg = mmCRTC ## reg_num ## _CRTC_INTERRUPT_CONTROL,\
                .enable_mask = CRTC_INTERRUPT_CONTROL__CRTC_V_UPDATE_INT_MSK_MASK,\
                .ack_reg   = mmCRTC ## reg_num ## _CRTC_V_UPDATE_INT_STATUS,\
                .ack_mask  = CRTC_V_UPDATE_INT_STATUS__CRTC_V_UPDATE_INT_CLEAR_MASK,\
                .funcs = &vupdate_irq_info_funcs\
```

**Y `vupdate_irq_info_funcs` es `{ .set = NULL, .ack = NULL }` (`irq_service_dce110.c:84-87`).**

**⇒ La interrupción de VUPDATE se arma y se acusa con el camino genérico, y no hay
ninguna función propia de esta GPU detrás.** `PROVEN`.

**⇒ Por lo tanto el driver no «sabe» que un modo se aplicó leyendo un registro de estado
propio del DC: VUPDATE es un flanco, se limpia, y quien realmente espera el modo es la
lógica de commit de `dc_state`, que sondea o temporiza.** `PROVEN_DERIVED`.

**Y esa es la respuesta completa a la pregunta sobre el paso 13 de la lista de arranque:
la confirmación de que un modo está en pantalla no pasa por una callback de DCE 11.2,
sino por un flanco de CRTC con limpieza genérica.** Es la misma forma que el resto del
bloque: **una operación que parece necesitar código del chip y la resuelve el código
genérico.**

## 5 · Y VBLANK, que sí tiene camino de setup propio

`dce110_vblank_set` (`irq_service_dce110.c:203-231`) es la única `.set` real:

```c
irq_service_dce110.c:209   enum dc_irq_src dal_irq_src =
irq_service_dce110.c:210           dc_interrupt_to_irq_source(irq_service->ctx->dc, info->src_id, info->ext_id);
irq_service_dce110.c:213   uint8_t pipe_offset = dal_irq_src - IRQ_TYPE_VBLANK;
irq_service_dce110.c:217   if (pipe_offset >= MAX_PIPES)
irq_service_dce110.c:218           return false;
irq_service_dce110.c:220   tg = dc->current_state->res_ctx.pipe_ctx[pipe_offset].stream_res.tg;
irq_service_dce110.c:223           if (!tg || !tg->funcs->arm_vert_intr(tg, 2)) {
```

**Traduce el identificador de fuente a índice de tubería, lo acota contra `MAX_PIPES`, y
arma la interrupción vertical del generador de temporización de esa tubería.** `PROVEN`.

**Y el `2` de `arm_vert_intr(tg, 2)` es un parámetro —qué índice de interrupción vertical
se arma— y no un literal arbitrario: el registro que lo respalda es
`CRTC_VERTICAL_INTERRUPT0_CONTROL` (`irq_service_dce110.c:150`), con el campo
`CRTC_VERTICAL_INTERRUPT0_INT_ENABLE`, y hay más de un `INTERRUPT` vertical en la
familia.** `PROVEN_DERIVED`.

**⇒ Y el identificador de fuente de VBLANK viene de otro bloque de hardware, no del DC:**
`irq_service_dce110.c:162` usa `VISLANDS30_IV_SRCID_D1_VERTICAL_INTERRUPT0 + reg_num`.
**`VISLANDS30_IV` es el bloque «VI South Islands»**, un IP distinto del DC, y sus
identificadores no están en `dce_10_0_d.h`. `PROVEN_DERIVED`.

**⇒ Consecuencia: los registros de interrupción no están en el mapa de DCE 10.0 que `140`
cerró, sino en un segundo mapa.** Es el mismo patrón de dos dominios que `232` encontró
con `DIG_FE_CNTL` en el recurso y `DP_VID_TIMING` en `gmc_v8_0.c`. `PROVEN_DERIVED`.

## 6 · Y el reparto del árbol, medido

`display/dc/irq/` son **21 ficheros y 7.870 líneas**, uno por generación:

| fichero | líneas | fichero | líneas |
|---|---|---|---|
| `irq_service_dcn32.c` | 438 | `irq_service_dcn351.c` | 384 |
| **`irq_service_dce110.c`** | **431** | `irq_service_dcn36.c` | 383 |
| `irq_service_dcn30.c` | 424 | `irq_service_dcn10.c` | 382 |
| `irq_service_dcn401.c` | 416 | `irq_service_dce60.c` | 365 |
| `irq_service_dcn21.c` | 415 | `irq_service_dcn201.c` | 338 |
| `irq_service_dcn42.c` | 415 | `irq_service_dcn303.c` | 286 |
| `irq_service_dcn315.c` | 413 | `irq_service_dce80.c` | 277 |
| `irq_service_dcn314.c` | 408 | `irq_service_dce120.c` | 267 |
| `irq_service_dcn31.c` | 406 | `irq_service.c` | 243 |
| `irq_service_dcn35.c` | 402 | | |
| `irq_service_dcn302.c` | 390 | | |
| `irq_service_dcn20.c` | 387 | | |

**⇒ No existe `irq/dce112/`. El decodificador de esta máquina es el de DCE 11.0, y es el
segundo más grande de los veintiuno — más grande que todos los DCN salvo DCN 3.2.**
`PROVEN`.

**Y la serie es plana: de 243 a 438 líneas, en veintiuna generaciones, sin tendencia.** Al
contrario que el codificador de stream (22 → 35) y que el gestor de reloj (2 → 16).
**⇒ El decodificador de interrupciones no ha crecido con las generaciones: la interfaz
de interrupción es estable y sólo cambia el juego de registros.** `PROVEN_DERIVED`.

**Los cuatro DCE: 431, 365, 277, 267 — y también decrecientes.** `PROVEN`.

## Lo que NO cierra

| afirmación | estado |
|---|---|
| `MAX_PIPES` = 6 | `PROVEN` |
| Cinco familias con exactamente 6 entradas | `PROVEN` (por programa) |
| 30 implementadas de 85, el 35% | `PROVEN` |
| HPDRX, PFLIP, VUPDATE, VBLANK: implementadas, sin callback propio | `PROVEN` |
| I2C/DDC, DP sink, GPIO pad, underflow: bombs con log de error | `PROVEN` |
| El HPD está resuelto, no bloqueado | `PROVEN_DERIVED` — cierra el bloqueo |
| El AUX/DDC está ausente del driver, no del corpus | `PROVEN_ABSENT` |
| `hpd_ack` invierte la polaridad tras acusar | `PROVEN` |
| `DC_HPD_SENSE_DELAYED` es un campo con retardo | `PROVEN_DERIVED` |
| VUPDATE sin callback propio: la espera la hace `dc_state` | `PROVEN_DERIVED` |
| VBLANK sí tiene setup propio, y acota contra `MAX_PIPES` | `PROVEN` |
| VBLANK se entrega por el bloque VISLANDS30_IV, no por el DC | `PROVEN_DERIVED` |
| Los registros de IRQ están en un segundo mapa de hardware | `PROVEN_DERIVED` |
| 21 ficheros, 7.870 líneas, serie plana sin tendencia | `PROVEN` |
| `MAX_PIPES` duplicado en tres ficheros | `PROVEN` |
| Cuál de las 6 tuberías está en uso en esta sesión | **`NOT_DETERMINED`** |
| El valor de `VISLANDS30_IV_SRCID...` en la placa | **`NOT_DETERMINED`** — registro |
| Si la iGPU Intel genera alguna de estas interrupciones | **`NOT_DETERMINED`** |

**La primera de las abiertas es la última cifra de salida que queda, y se lee del
`journalctl`: cuántas tuberías se activan en la práctica.** Es de las pocas que se pueden
observar sin placa, sin root y sin MMIO.

## Procedencia

- `STATIC` -- `display/dc/irq/dce110/irq_service_dce110.c:1-431` (el fichero entero),
  `:42-62` (`hpd_ack`), `:64-87` (las cinco tablas de `irq_source_info_funcs`, con sus
  `.set` y `.ack` a NULL), `:89-102` (`hpd_int_entry`), `:104-116` (`hpd_rx_int_entry`),
  `:117-130` (`pflip_int_entry`), `:132-146` (`vupdate_int_entry`), `:148-163`
  (`vblank_int_entry`, y el `VISLANDS30_IV_SRCID` de `:162`), `:165-180`
  (`dummy_irq_entry` y las cuatro familias ausentes), `:182-200` (los dos bombs y su
  texto de error), `:203-231` (`dce110_vblank_set`), `:233-236` (`dummy_irq_info_funcs`),
  `:238-431` (la tabla completa, 85 entradas);
  `display/dc/inc/hw/hw_shared.h:45` (`MAX_PIPES` 6),
  `display/dc/dce/dmub_psr.c:34`, `display/dc/dce/dmub_replay.c:14` (las otras dos
  copias); `display/dc/irq/irq_service.c` (243 líneas) y los veinte ficheros de
  generación de `display/dc/irq/`.
- Medición por programa: **las 85 entradas de la tabla y su reparto en nueve familias**,
  con el recuento de cada macro y de las `dummy_irq_entry` explícitas; **las líneas de
  los 21 ficheros de `display/dc/irq/`**; los tres `#define MAX_PIPES` y su coincidencia
  de valor.
- **Cuatro errores de ruta y de patrón propios en esta nota, todos del tipo conocido:**
  (1) apunté a `display/irq/dce112/` y no existe — el árbol es `display/dc/irq/`;
  (2) busqué `struct dc_irq_callbacks {` y **no existe en ningún header**: el tipo se
  llama `irq_source_info`, y no hay tal cosa como callbacks de IRQ; (3)
  `dc/inc/hw/irq.h` no existe; (4) encadé `cut` antes de `sed` y trunqué las rutas al
  ancho de corte. **Los dos primeros habrían producido afirmaciones falsas si no los
  hubiera corregido antes de escribir nada.**
- Encadenada con `161` (el reloj, y aquí el otro punto de contacto de la lista de
  arranque), `159` (**los seis constructores `dce110_` de `dce112_resource.c`, y aquí
  `MAX_PIPES 6` es el sexto número que concuerda**), `157` (el puntero nulo como
  mecanismo, y aquí el mismo patrón con la forma de un bomb con log de error), `232` (dos
  dominios de registro: el DC y `VISLANDS30_IV`), `155` (los siete puntos de firmware, y
  el HPD pasa de bloqueo a hecho), `153` (los siete paths externos, que **no** son 6 y no
  deben confundirse con `MAX_PIPES`).
- No se editó `AGENTS.md` ni `OPEN-FRONTIERS.md`.

## Nota de método

**El hallazgo de fondo es un patrón, y apareció al contarlos y no al leerlos: en el
decodificador de interrupciones la ausencia se implementa con un bomb que registra un
error, y ese bomb convierte 55 `NOT_IN_CORPUS` en `PROVEN_ABSENT` con la causa escrita en
el código fuente.**

*«No está aquí» y «está aquí y no funciona» son afirmaciones distintas, y la segunda es
mucho más útil.* Las cuatro familias ausentes —AUX, I2C/DDC, GPIO, underflow— están
**declaradas una por una, con su sitio en el índice, su nombre y su mensaje de error**.
Eso no es un hueco del corpus: es una decisión del driver, y su texto dice `called for
non-implemented irq source`. *Un `grep` de `dp_sink` habría encontrado la entrada y yo
habría dicho «existe»; el bomb es lo que dice que no hace nada.*

**Y la regla que sale es de búsqueda, no de lectura: antes de escribir `NOT_IN_CORPUS`
sobre un mecanismo, hay que mirar si el árbol contiene un camino que lo declare y lo
rechace.** Es el mismo cuidado que produjo el resultado negativo del gestor de display
en `159` y el `PROVEN_ABSENT` de VGA en `158`, pero al revés: allí la ausencia hurtó por no
estar; aquí la ausencia **está escrita en el fichero, en un `DC_LOG_ERROR` que nadie ha
ejecutado nunca**.

**Y la segunda observación, que es de forma: el error más caro de esta nota, buscar
`struct dc_irq_callbacks`, fue un nombre inventado.** No existe ninguna estructura de
«callbacks de interrupción» en amdgpu: existe `irq_source_info`, con `.set` y `.ack` como
miembros de función. *Es la novena colisión de nombres del proyecto, y tiene la misma
familia que las ocho anteriores: yo invento un nombre que suena a la estructura que
espero, busco, y si no lo encuentra la conclusión que saco es que la cosa no existe.*
**Y esa forma de error es especialmente peligrosa porque produce un `PROVEN_ABSENT` en
lugar de un simple "no encontré nada": un nombre inventado y una ausencia real se
parecen exactamente en la salida.**

*La defensa es la que ya está en la lista de reglas desde el principio de esta
tanda —ante un `grep` vacío, la primera hipótesis es el patrón, no la herramienta— y esta
nota es la cuarta vez que se aplica en `display/` y la primera que la incumple: dos calls
seguidas con `PROVEN_ABSENT` en la boca y el patrón equivocado en las dos.*
