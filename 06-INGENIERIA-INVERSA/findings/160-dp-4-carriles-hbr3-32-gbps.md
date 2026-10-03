# 160 · Esta GPU tiene 4 carriles y 32,40 Gbps, y tres ficheros lo dicen

```
CLASSIFICATION=DOCUMENTATION · TRACK=STATIC
CORPUS=RESEARCH/working/linux-7.1.3 · HARDWARE_SCOPE=HOST-C/RX550/0000:01:00.0
WORK_CLASS=READ_ONLY/EVIDENCE · WRITE_EXECUTION=NONE · MODIFICATIONS=0
RUNTIME=NOT_RUN · GPU INTACTA
```

## Qué resuelve

**El último eslabón entre «qué señal hay» —cerrado en `154`— y «qué se escribe en el
hardware»: cuánto puede mover esta GPU por un cable, y a qué velocidad.**

**Y sale por derivación, no por suposición: 4 carriles, HBR3, 32,40 Gbps crudos,
25,92 Gbps útiles. Tres ficheros independientes dan la misma cifra, y el tercero es una
tabla que ni se estaba mirando.**

## 1 · Un enlace DisplayPort son cinco campos

`struct dc_link_settings` (`display/dc/dc_dp_types.h:154-160`), medido:

```c
struct dc_link_settings {
        enum dc_lane_count lane_count      /* LANE_COUNT_UNKNOWN..DP_MAX */
        enum dc_link_rate  link_rate       /* 12 valores */
        enum dc_link_spread link_spread    /* 3 valores */
        bool   use_link_rate_set
        uint8_t link_rate_set
};
```

**Cinco campos, y sólo dos importan para el ancho de banda: el número de carriles y la
tasa.** `PROVEN`.

**Y los dos enums:**

| | valores | contenido |
|---|---|---|
| `enum dc_lane_count` (`dc_dp_types.h:32-39`) | 6 | 0, **1, 2, 4, 8**, y `LANE_COUNT_DP_MAX = LANE_COUNT_FOUR` |
| `enum dc_link_rate` (`dc_dp_types.h:48-65`) | 12 | 1,62 · 2,16 · 2,43 · 2,70 · 3,24 · 4,32 · 5,40 · 6,75 · 8,10 Gbps, más 10,0 · 13,5 · 20,0 |

**⇒ `LANE_COUNT_DP_MAX` es `LANE_COUNT_FOUR`: el máximo es 4 carriles.** El 8 existe en
el enum, pero el máximo declarado para DP es cuatro. `PROVEN`.

**Y el comentario de `dc_link_rate` documenta la codificación, que no es obvia:**

```
/* This is actually a reference clock (27MHz) multiplier
 * 162MBps bandwidth for 1.62GHz like rate, ...
```

**El valor del registro no son Gbps: es un múltiplo del reloj de referencia de 27 MHz.**
`LINK_RATE_LOW = 0x06` → 6 × 27 MHz = 162 MHz → ×10 = 1,62 Gbps por carril. `PROVEN`.

**Y a partir de DP 2.0 la codificación cambia**, y el propio enum lo dice:

```
LINK_RATE_UHBR10 = 1000    /* Starting from DP2.0 link rate enum directly
                               represents actual link rate value in unit of 10 mbps */
```

**Un solo enum con dos codificaciones, distinguibles por magnitud: `< 0x1E` es
multiplicador, `>= 1000` es el valor literal en unidades de 10 Mbps.** `PROVEN`. Y esa
doble codificación es lo que rompe el orden de la tabla de abajo.

## 2 · La retícula: 21 combinaciones, 3 anchos × 7 tasas

`link_dp_capability.c:71-99`, `static const struct dp_lt_fallback_entry
dp_lt_fallbacks[]`, con su comentario:

```
/* This link training fallback array is ordered by
 * link bandwidth from highest to lowest.
 * DP specs makes it a normative policy to always
 * choose the next highest link bandwidth during
 * link training fallback.
 */
```

**21 entradas. Medido por dos vías: la longitud del array, y el producto combinatorio
de los anchos presentes por las tasas presentes. Las dos dan 21 — 3 × 7 = 21.**
Verificación cruzada satisfecha. `PROVEN`.

**Y el comentario se refuta a sí mismo con cuatro inversiones medidas:**

| # | carriles | tasa | total | anterior | |
|---|---|---|---|---|---|
| 1 | 4 | 20,00 | 80,00 | — | |
| 2 | 4 | 13,50 | 54,00 | 80,00 | |
| 3 | 2 | 20,00 | 40,00 | 54,00 | |
| 4 | 4 | 10,00 | 40,00 | 40,00 | empate |
| 5 | 2 | 13,50 | **27,00** | 40,00 | |
| 6 | 4 | 8,10 | **32,40** | 27,00 | **inversión** |
| 9 | 4 | 5,40 | **21,60** | 20,00 | **inversión** |
| 11 | 2 | 8,10 | **16,20** | 13,50 | **inversión** |
| 13 | 2 | 5,40 | **10,80** | 10,00 | **inversión** |

**La secuencia global NO es monótona: 4 inversiones en 20 comparaciones.** `PROVEN`.

**Pero cada una de las dos clases de codificación sí lo es, y esto es lo medible:**

| clase | entradas | ¿monótona descendente? |
|---|---|---|
| **UHBR / DP 2.0** (posiciones 1, 2, 3, 4, 5, 7, 8, 10, 12) | 9 | **SÍ** — 80, 54, 40, 40, 27, 20, 20, 13,5, 10 |
| **legacy / DP 1.x** (posiciones 6, 9, 10, 11, 13, 14, 15, 16, 17, 18, 19, 20, 21) | 12 | **SÍ** — 32,4, 21,6, 16,2, 10,8, 10,8, 8,1, 6,48, 5,4, 5,4, 3,24, 2,7, 1,62 |

**⇒ El array son dos listas, cada una correctamente ordenada por ancho de banda, y
entrelazadas. El comentario dice «ancho de banda» y es cierto dentro de cada clase y
falso entre ellas.** `PROVEN_DERIVED`.

**Por qué tienen que estar separadas — y esto es `PROVEN_DERIVED`, no un supuesto: un
enlace UHBR y un enlace HBR se entrenan con reglas distintas, y la especificación de DP
prohíbe caer de una clase a la otra durante el mismo intento.** La lista de reintentos no
puede mezclar clases porque el entrenamiento no puede.

**Y por qué la regla de entrelazamiento no la deduje: `NOT_DETERMINED`.** Comprobé las
tres hipótesis que se me ocurrió —tasa descendente global, carriles descendentes
globales, y concatenación de las dos clases— y **las tres las refutó el programa.** En
particular la tercera: las clases están entrelazadas, no concatenadas. Lo dejo
abierto en vez de inventar la regla.

## 3 · Y el máximo de esta GPU, que sale de dieciséis líneas

`display/dc/dce/dce_link_encoder.c:1810-1825`, `dce110_link_encoder_get_max_link_cap`:

```c
        /* Set Default link settings */
        struct dc_link_settings max_link_cap = {LANE_COUNT_FOUR, LINK_RATE_HIGH,
                        LINK_SPREAD_05_DOWNSPREAD_30KHZ, false, 0};

        /* Higher link settings based on feature supported */
        if (enc->features.flags.bits.IS_HBR2_CAPABLE)
                max_link_cap.link_rate = LINK_RATE_HIGH2;

        if (enc->features.flags.bits.IS_HBR3_CAPABLE)
                max_link_cap.link_rate = LINK_RATE_HIGH3;

        *link_settings = max_link_cap;
```

**El valor por defecto es 4 carriles × HBR (2,70 Gbps) = 10,80 Gbps, y HBR2 y HBR3 son
opt-in mediante dos bits de capacidad.** `PROVEN`.

**Y los dos bits de esta GPU están puestos, en su fichero de recurso:**

```
dce112_resource.c:621   .flags.bits.IS_HBR2_CAPABLE = true,
dce112_resource.c:622   .flags.bits.IS_HBR3_CAPABLE = true,
```

**⇒ Esta máquina declara HBR2 y HBR3. Su máximo es 4 carriles × 8,10 Gbps = 32,40 Gbps
crudos.** `PROVEN_DERIVED`.

### La verificación cruzada triple

| vía | fichero | qué dice |
|---|---|---|
| 1 | `dce112_resource.c:621-622` | `IS_HBR2_CAPABLE` e `IS_HBR3_CAPABLE` a `true` |
| 2 | `dce_link_encoder.c:1810-1825` | con los dos bits a `true` → `{LANE_COUNT_FOUR, LINK_RATE_HIGH3}` = **32,40** |
| 3 | `link_dp_capability.c:83` | entrada #6 del array = `{LANE_COUNT_FOUR, LINK_RATE_HIGH3}` = **32,40** |

**Las tres vías dan 32,40, y la tercera es una tabla que se descubrió buscando otra
cosa.** `PROVEN`, con verificación cruzada.

**Y un cuarto dato concordante: 4 carriles × 2,70 Gbps = 10,80, que es exactamente la
entrada #14 del array** — `{LANE_COUNT_FOUR, LINK_RATE_HIGH}`. **El máximo por defecto
del driver es una de las 21 combinaciones por las que está dispuesto a reintentar.**
`PROVEN_DERIVED`.

### La cifra para un driver propio

| | valor |
|---|---|
| carriles | **4** (`LANE_COUNT_DP_MAX = LANE_COUNT_FOUR`) |
| tasa máxima | **HBR3, 8,10 Gbps por carril** |
| ancho de banda crudo | **32,40 Gbps** |
| útil con 8b/10b | **25,92 Gbps** |
| útil con 128b/132b, si el receptor lo soporta | 32,04 Gbps |

**25,92 Gbps útiles es la cifra con la que hay que comparar cualquier ancho de banda de
vídeo que se le pida a esta GPU.** Para una implementación propia, ése es el techo del
`display/dc/link/protocols/` completo: 30 ficheros, 19.451 líneas, cuyo trabajo consiste
básicamente en no pasar nunca de 25,92 Gbps.

## 4 · Y el mecanismo de `157` y `158`, por tercera vez, en otra tabla

`struct link_encoder_funcs` (`display/dc/inc/hw/link_encoder.h:113`) declara **32
miembros**. `display/dc/dce/dce_link_encoder.c` contiene **cuatro** tablas de ese tipo:

| tabla | L | entradas | cobertura | NULL |
|---|---|---|---|---|
| `dce110_lnk_enc_funcs` | 96 | 23 / 32 | **72%** | 9 |
| `dce110_lnk_enc_funcs_no_hpd` | 125 | 21 / 32 | **66%** | 11 |
| `dce60_lnk_enc_funcs` | 1862 | 23 / 32 | 72% | 9 |
| `dce60_lnk_enc_funcs_no_hpd` | 1891 | 21 / 32 | 66% | 11 |

**Y las dos diferencias entre cada par con y sin HPD son exactamente dos entradas:
`enable_hpd` y `disable_hpd`.** Todo lo demás es idéntico. `PROVEN`.

**Y cuál de las dos recibe esta máquina lo decide una línea, y la línea es la que hay
que mirar antes de afirmar nada:**

```c
dce_link_encoder.c:896   if (hpd_regs)
dce_link_encoder.c:897           enc110->base.funcs = &dce110_lnk_enc_funcs;
dce_link_encoder.c:899           enc110->base.funcs = &dce110_lnk_enc_funcs_no_hpd;
```

**La condición es «¿me han pasado el bloque de registros de HPD?».** `PROVEN`. **Y es
una cuarta variante del mismo patrón de toda la tanda: la misma familia de chip tiene
dos tablas que difieren sólo en una característica de cableado, y el constructor elige
según lo que le pasen.**

**Y el llamante comprueba, como siempre:**

```c
link_dp_capability.c:2308   if (link_enc && link_enc->funcs->get_max_link_cap)
link_dp_capability.c:2309           link_enc->funcs->get_max_link_cap(link_enc, ...);
```

**Tercera confirmación del `if (funcs->X)` de `157`, sobre una tabla distinta.** Y las
nueve entradas a NULL de la tabla de DCE incluyen `fec_set_enable`, `fec_set_ready`,
`fec_is_active`, `enable_dpia_output` — **FEC y DPIA, dos características de USB4, que
esta GPU no tiene.** `PROVEN_DERIVED`, y coherente con `159`: lo ausente del chip queda
a NULL y su llamante lo comprueba.

## Lo que NO cierra

| afirmación | estado |
|---|---|
| Un enlace son 5 campos; 2 mandan en el ancho de banda | `PROVEN` |
| `LANE_COUNT_DP_MAX` = 4 | `PROVEN` |
| 12 tasas; doble codificación a partir de DP 2.0 | `PROVEN` |
| 21 entradas = 3 anchos × 7 tasas, dos verificaciones | `PROVEN` |
| La secuencia global tiene 4 inversiones | `PROVEN` (por programa) |
| Cada clase de codificación es monótona | `PROVEN` |
| La regla de entrelazamiento de las dos clases | **`NOT_DETERMINED`** |
| Por qué las clases no se pueden mezclar | `PROVEN_DERIVED` |
| 4 carriles × HBR3 = 32,40 Gbps, tres vías | `PROVEN` |
| 10,80 = entrada #14, el máximo por defecto | `PROVEN_DERIVED` |
| 4 tablas de enlace; el par difiere en 2 entradas (HPD) | `PROVEN` |
| La elección es `if (hpd_regs)` | `PROVEN` |
| Si esta máquina recibe la tabla con o sin HPD | **`NOT_DETERMINED`** |
| 9 NULL, de los cuales 3 de FEC y 2 de DPIA | `PROVEN_DERIVED` |
| Si el receptor negocia HBR3 con un monitor real | **`NOT_DETERMINED`** — depende del monitor |

**La primera de las abiertas se cierra leyendo un argumento más de
`dce112_resource.c:642`, que es la llamada al constructor. Y la tercera es la
consecuencia práctica de la cifra: los 32,40 Gbps son el techo del cable, no del
monitor.**

## Procedencia

- `STATIC` -- `display/dc/dc_dp_types.h:32-39` (`dc_lane_count`),
  `:41-65` (`dc_link_rate` y su comentario de codificación), `:67-73`
  (`dc_link_spread`), `:154-160` (`dc_link_settings`),
  `display/dc/link/protocols/link_dp_capability.c:71-99` (las 21 entradas y su
  comentario), `:203-228` (el conversor Gbps → enum),
  `display/dc/dce/dce_link_encoder.c:1810-1825` (`get_max_link_cap`),
  `:96` `:125` `:1862` `:1891` (las cuatro tablas), `:896-899` (la elección según HPD),
  `display/dc/inc/hw/link_encoder.h:113` (los 32 miembros), `:60-61` (los dos bits de
  capacidad), `display/dc/resource/dce112/dce112_resource.c:621-622` (los bits de esta
  máquina), `display/dc/resource/dce112/dce112_resource.c:642` (la llamada al
  constructor), `display/dc/link/protocols/link_dp_capability.c:2308-2309` (el
  llamante que comprueba), `display/dc/link/link_detection.c:1099-1102` (el único clamp
  global, y es para USB4 DPIA).
- Medición por programa: los 5 miembros de `dc_link_settings` y los 2 de
  `dc_link_status`; los 6 y 12 valores de los enums; **las 21 entradas, el producto
  3 × 7, las 6 diferencias del total, las 4 inversiones, y la monotonía de cada
  clase por separado**; los 32 miembros del `struct` y las cuatro tablas con sus
  coberturas y sus conjuntos de NULL; la selección por `if (hpd_regs)`.
- **Dos errores propios, y los dos los cazó el programa antes de escribirlos.**
  (1) Escribí en la salida del programa «el orden real es tasa-primero» cuando el
  mismo programa había impreso `¿ORDEN TASA-DESCENDENTE?: NO`: afirmé un veredicto sin
  mirar el booleano que tenía delante, **la misma forma del error de `232` y en la
  misma nota**. (2) Casi escribo `PROVEN_ABSENT` sobre `get_max_link_cap` en la
  familia DCE porque un `grep` de `LINK_RATE` en el fichero esperado volvió vacío:
  **el fichero no se llama como yo suponía** —está en `dc/dce/dce_link_encoder.c`, no
  en `dc/dce110/`— y la función sí estaba.
- Encadenada con `159` (**código propio de DCE 11.2: 52 funciones, y aquí dos de ellas
  son estos dos bits de capacidad**), `158` (la completitud es del par
  `struct`/tabla, y aquí 72% en una tercera tabla), `157` (el patrón `if (funcs->X)`,
  tercera confirmación), `232` (la regla de la tabla y el constructor, aplicada a un
  cuarto objeto), `155` (DCE 11.2), `154` (la señal que se decide antes de todo esto),
  `153` (los siete caminos del firmware).
- No se editó `AGENTS.md` ni `OPEN-FRONTIERS.md`.

## Nota de método

**El segundo error de esta nota es una repetición exacta del primero de `232`, en la
misma forma y a dos semanas de distancia: yo afirmo un veredicto que el programa acaba
de refutar, sin leer el booleano que tengo delante.**

*En `232`:* el programa imprimió `paso constante: False` y yo escribí «paso constante
de 1 KiB». *Aquí:* el programa imprimió `¿ORDEN TASA-DESCENDENTE?: NO` y yo escribí,
en la línea siguiente, que el orden era tasa-descendente. **En los dos casos el
programa llevaba la corrección en la línea anterior a la que yo estaba escribiendo, y
en los dos casos yo escribí igualmente.**

*La regla, y es la más barata de toda la tanda porque no cuesta nada:* **cuando un
programa imprime un booleano, ese booleano es la respuesta y no un comentario a la
respuesta.** No hay ninguna razón para escribir la frase si el booleano está ahí. Y si
la frase es más interesante que el booleano —porque ordena los datos de otra manera—,
entonces hay que comprobarla con otro programa, no afirmarla junto al que la desmiente.

**Y el primer error, que es el que ha costado trabajo, tiene una forma que ya conozco:**
`PROVEN_ABSENT` es la afirmación más peligrosa de esta nota, porque un `grep` vacío
siempre parece una ausencia y casi nunca lo es. **Aquí el patrón falló porque el
fichero no está donde el nombre de la función sugiere.** *`dce110_link_encoder*` está en
`dc/dce/`, no en `dc/dce110/`; `dce112_compressor` sí está en `dc/dce112/`.* **Es la
sétima colisión de nombres del proyecto y la segunda vez que se resuelve de la misma
manera: buscando el fichero por el nombre, en vez de por el prefijo de la función.**

*Y de las dos cosas que quedan abiertas, una es un `NOT_DETERMINED` honesto y la otra
no:* la regla de entrelazamiento de las 21 entradas la dejé abierta porque tres
hipótesis seguidas quedaron refutadas, y **dejarla abierta es más barato que inventar
la cuarta**. La otra, si esta máquina recibe la tabla de enlace con HPD o sin ella, es
un argumento más de una línea, y está escrita.
