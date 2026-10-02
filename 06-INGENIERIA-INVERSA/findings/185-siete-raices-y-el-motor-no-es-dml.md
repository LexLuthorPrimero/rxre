# 185 · Siete raíces, 33,7%, y el motor de cálculo de esta placa no es DML sino `bw_calcs`

```
CLASSIFICATION=DOCUMENTATION+TOOLING · TRACK=STATIC
CORPUS=RESEARCH/working/linux-7.1.3 · HARDWARE_SCOPE=HOST-C/RX550/0000:01:00.0
WORK_CLASS=READ_ONLY/EVIDENCE · WRITE_LOCAL=PROPIOS · MODIFICATIONS_CORPUS=0 · WRITE_EXECUTION=NONE
RUNTIME=NOT_RUN · GPU INTACTA
```

## Qué resuelve

**La contradicción que `184` dejó abierta —«ni DML1 ni DML2 muestran camino de validación de
modo, y `using_dml2` está apagado»— y el punto abierto de `181` sobre `modules/`. Las dos
quedan cerradas, y por el camino sale la superficie de entrada completa del subsistema.**

**⇒ El subsistema de pantalla tiene SIETE puntos de entrada desde el exterior, y los siete
están citados.** `PROVEN`.

**⇒ Desde los siete se alcanzan 3.819 funciones y 149.588 de las 443.839 líneas: el 33,7%,
frente al 27,8% de `181` desde una sola raíz.** `PROVEN_DERIVED`.

**⇒ Y el motor de cálculo de modo de esta placa es `bw_calcs`, en `dc/basics/dce_calcs.c`,
llamado desde `dc/resource/dce112/dce112_resource.c:905`. No es DML1 ni DML2: es
aritmética pura, y por eso `179` lo clasificó como «sorth».** `PROVEN`.

## 1 · Las siete raíces, y dónde están

**`dc_create` es sólo construcción. La superficie de entrada se lee en dos tablas y ya está
cerrada:**

```c
display/amdgpu_dm/amdgpu_dm.c:3833   static const struct drm_mode_config_funcs amdgpu_dm_mode_funcs = {
                                              .atomic_check       = amdgpu_dm_atomic_check,
                                              .atomic_commit      = drm_atomic_helper_commit,
display/amdgpu_dm/amdgpu_dm.c:3840   static struct drm_mode_config_helper_funcs amdgpu_dm_mode_config_helperfuncs = {
                                              .atomic_commit_tail  = amdgpu_dm_atomic_commit_tail,
                                              .atomic_commit_setup = amdgpu_dm_atomic_setup_commit,
display/amdgpu_dm/amdgpu_dm.c:3799   static const struct amd_ip_funcs amdgpu_dm_funcs = {
                                              .early_init = dm_early_init,
                                              .sw_init    = dm_sw_init,
                                              .hw_init    = dm_hw_init,
```

**⇒ Las siete raíces, con su definición:**

| raíz | fichero:línea |
|---|---|
| `dc_create` | `display/dc/core/dc.c:1508` |
| `amdgpu_dm_atomic_check` | `display/amdgpu_dm/amdgpu_dm.c:238` |
| `amdgpu_dm_atomic_commit_tail` | `display/amdgpu_dm/amdgpu_dm.c:236` (definida en `:10938`) |
| `amdgpu_dm_atomic_setup_commit` | `display/amdgpu_dm/amdgpu_dm.c:235` |
| `dm_early_init` | `display/amdgpu_dm/amdgpu_dm.c:1069` |
| `dm_sw_init` | `display/amdgpu_dm/amdgpu_dm.c:2666` |
| `dm_hw_init` | `display/amdgpu_dm/amdgpu_dm.c:3087` |

**⇒ Y una de las siete está fuera del corpus: `.atomic_commit = drm_atomic_helper_commit`,
que es del core de DRM.** `PROVEN`. *Eso es la LIMITACIÓN 3 de `inst_closure.py` con cita:
el grafo entra y sale de `display/`, y la salida no se sigue.*

**⇒ Y una puerta que se descartó por su propia firma: `dm_display_funcs`
(`amdgpu_dm/amdgpu_dm.c:5863`) tiene 10 entradas y 6 son `NULL`, tres de ellas con el
comentario «never called for DC» y dos con «VBIOS parsing. DAL does it.».** `PROVEN`.
*Regla (g) aplicada al revés: comprobar qué variante se registra, no cuál parece la
principal. `amdgpu_dm_funcs` y `amdgpu_dm_mode_funcs` son las que cuentan.*

## 2 · El 33,7%, y lo que las seis raíces nuevas añaden

| | 1 raíz (`181`) | 7 raíces |
|---|---|---|
| funciones alcanzables | 3.077 | **3.819** |
| líneas alcanzables | 123.571 | **149.588** |
| % de 443.839 | 27,8% | **33,7%** |
| `modules/` alcanzable | **0 funciones, 0 líneas** | **89 funciones, 3.951 líneas** |

**⇒ `modules/` pasa de cero a 89 funciones y 3.951 líneas, y eso cierra el punto que `181`
dejó abierto.** `PROVEN`. *FreeSync, HDCP, color, power y vmid se alcanzan desde los
retrollamados atómicos, no desde `dc_create` — era exactamente lo que `181`ía sospechoso
y no podía medir con una sola raíz.*

**⇒ Y el incremento es casi todo `modules/` y `amdgpu_dm/`: las seis raíces nuevas no
tocan el hardware de pantalla, sino el pegamento con KMS.** `PROVEN_DERIVED`.

**⇒ Y una comparación que hay que hacer con las dos cifras a la vista: 27,8% no era
«cuánto hay que reescribir», era «cuánto se alcanza desde la construcción».** `ERROR`.
*Es la misma forma de error que las cuatro de `184`: medir la parte —una raíz entre
siete— y generalizarla. Y en `181` el número estaba presentado como la cota del
subsistema entero, que no lo es.*

## 3 · La contradicción del motor, resuelta

**Las tres cosas que `184` declaró incompatibles son: ni DML1 ni DML2 alcanzables,
`using_dml2` apagado, y Polaris12 tiene que modear de algún modo. La tercera es la que
decide, y se resuelve leyendo quién llama a qué:**

```c
display/dc/resource/dce112/dce112_resource.c:905     if (bw_calcs(
display/dc/resource/dce112/dce112_resource.c:1415   bw_calcs_init(dc->bw_dceip, dc->bw_vbios, dc->c
display/dc/basics/dce_calcs.c:3041   bool bw_calcs(struct dc_context *ctx, ...)
display/dc/basics/dce_calcs.c:3078       calculate_bandwidth(dceip, vbios, data);
display/dc/basics/dce_calcs.c:75    static void calculate_bandwidth(...)
```

**⇒ `dc/basics/dce_calcs.c` es el motor de esta placa, y las dos llamadas que lo alcanzan
están en `dce112_resource.c`, el fichero de recurso de esta GPU.** `PROVEN`.

**⇒ Y por eso `dc/dml/` y `dc/dml2_0/` no aparecen: son de DCN, no de DCE.** `PROVEN_DERIVED`.
*Los 21 `switch` de `184` lo dicen con cita: `dml2_wrapper.c:61` y
`dml21_translation_helper.c:44` sólo tienen etiquetas `DCN_VERSION_*`, y `resource_parse_asic_id`
da `DCE_VERSION_11_2` a esta placa. Un motor cuyo selector sólo menciona `DCN_VERSION`
no puede ser el de un `DCE_VERSION`.*

**⇒ Y esto corrige el alcance de `151`, que lo decía de otra forma: `151` habla de DCE 10.0
y su título lo dice así, pero la regla general es de familia —DCE usa `dce_calcs`, DCN usa DML— y
en esta placa es `dce_calcs`.** `PROVEN_DERIVED`.

**⇒ Y encaja con `179` sin que haga falta suponer nada: `dce_calcs.c` es un fichero de
3.620 líneas con 0 delegaciones y 0 escrituras de registro, la clase «sorth».** `PROVEN`.
*Un motor de cálculo de modo que no toca ni el bus ni el silicio es aritmética, y `179` lo
dijo por otra vía antes de que nadie preguntara qué era.*

## 4 · Y un defecto de la herramienta con reproductor mínimo

**`bw_calcs` no aparece en el conjunto alcanzable, y sin embargo hay un caller suyo que es
semilla:** `dce112_resource.c:905`, dentro de un fichero cuyas funciones están todas en las
semillas. `PROVEN`.

**⇒ Y `bw_calcs_init` —el otro nombre del mismo fichero— SÍ aparece.** `PROVEN`. *Dos
llamadas al mismo fichero desde el mismo fichero de recurso, y sólo una llega: el defecto
está en cómo se indexa o en cómo se recorre `dce112_resource.c`, no en el grafo.*

**⇒ Es el reproductor mínimo del defecto pendiente: un símbolo alcanzable desde una semilla
que no está en el cierre, dentro de un fichero de 848 líneas con 16 funciones, en el que la
mitad de las llamadas sí llegan.** `NOT_DETERMINED`.

**⇒ Y por eso la cifra del 33,7% es también un techo, y por un motivo distinto del de
`184`: aquí la omisión es de la herramienta, no de una guarda mal podada.** `LIMITATION`.
*En `184` sobraba alcance; aquí falta, y las dos cosas se distinguen mirando si el símbolo
omitido tiene un caller alcanzable: si lo tiene, es un bug de la herramienta; si no lo tiene,
es una poda que funciona.*

## Lo que NO cierra

| afirmación | estado |
|---|---|
| Siete raíces de entrada, todas citadas | `PROVEN` |
| 3.819 funciones y 149.588 líneas, 33,7% | `PROVEN_DERIVED` |
| `modules/`: 0 → 89 funciones, 3.951 líneas | `PROVEN` |
| `dc/basics/dce_calcs.c` es el motor de esta placa | `PROVEN` |
| DML1 y DML2 son de DCN, no de DCE | `PROVEN_DERIVED` |
| `dm_display_funcs` tiene 6 entradas `NULL` | `PROVEN` |
| `bw_calcs` inalcanzable desde una semilla que sí lo llama | **`NOT_DETERMINED`** — bug |
| Cuánto sube el 33,7% arreglado ese defecto | **`NOT_DETERMINED`** |
| El alcance a través de `drm_atomic_helper_commit` | **`NOT_DETERMINED`** |
| El número podado con las siete raíces | **`NOT_DETERMINED`** |

**La primera de las abiertas es un bug con reproductor de una línea, y es lo que hay que
hacer siguiente: `bw_calcs` se llama desde `dce112_resource.c:905` y no está en el cierre.**
`NOT_DETERMINED`. *Y el vector de prueba es el propio fichero: 16 funciones, 848 líneas,
semillas todas, y la mitad de las llamadas sí llegan. Con eso el `--selftest` puede llevar un
caso que falle.*

**Y la tercera es la que hace la cifra utilizable de verdad: `drm_atomic_helper_commit` está
fuera de `display/`, y entre `display/` y el core de DRM hay un tramo del grafo que no se
recorre.** `NOT_DETERMINED`. *Es el mismo borde que las LIMITACIONES 1 a 3 de
`inst_closure.py`, y ahora está localised a una llamada concreta en vez de ser una
declaración general.*

## Procedencia

- `STATIC` -- `tools/inst_closure.py` con siete raíces en lugar de una; sin cambios de
  código respecto a `184` salvo la lista de semillas. `--selftest` sigue en 22 vectores y
  pasa.
- `display/amdgpu_dm/amdgpu_dm.c:3799` (`amd_ip_funcs amdgpu_dm_funcs`), `:3833`
  (`drm_mode_config_funcs amdgpu_dm_mode_funcs`), `:3840`
  (`drm_mode_config_helper_funcs`), `:5863` (`amd_display_funcs dm_display_funcs` con sus
  10 entradas y sus 6 `NULL`), `:235`, `:236`, `:238`, `:1069`, `:2666`, `:3087`, `:10938`,
  `:2038` (`dc_create(&init_data)`), `:3208` y `:3641` y `:10641` (los tres
  `dc_commit_streams` de `amdgpu_dm/`), `:2075` (`DC_ENABLE_DML2`),
  `display/dc/core/dc.c:1508` (`dc_create`), `:2444` (`dc_commit_streams`),
  `:3913` (`dc_dmub_update_dirty_rect`), `:1408` / `:4164` / `:4265` (los tres
  `if (!dc->debug.using_dml2)`, los tres `set_p_state_switch_method`),
  `display/dc/core/dc_resource.c:272` (el `switch (dc_version)`), `:308-309`,
  `:5657` (`resource_init_common_dml2_callbacks`),
  `display/dc/core/dc_link_enc_cfg.c:619` (`link_enc_cfg_validate`, que es un validador de
  asignación de codificadores y **no** el calculador de modo),
  `display/dc/resource/dce112/dce112_resource.c:905` (`bw_calcs`), `:1415` (`bw_calcs_init`),
  `display/dc/basics/dce_calcs.c:75` (`calculate_bandwidth`), `:2043` (`bw_calcs_init`),
  `:3041` (`bw_calcs`), `:3078` (la llamada a `calculate_bandwidth`),
  `display/dc/resource/dce110/dce110_resource.c:982` y `:1533` (las mismas dos llamadas,
  desde el pool de DCE 11.0, que `184` declaró muerto en esta placa),
  `display/dc/resource/dce120/dce120_resource.c:1269` (idem para 12.0),
  `display/dc/dml2_0/dml2_wrapper.c:61`, `display/dc/dml2_0/dml21/dml21_translation_helper.c:44`.
- **Seis nombres de función inventados en las sondas de esta iteración, todos por buscar un
  validador de modo por el nombre que yo esperaba en vez de por su relación:**
  `dcn10_dml_resource_validation`, `dcn10_validate_dml_mode`, `dcn10_dml_mode_calculate`,
  `dml2_mode_configuration`, `dcn20_dml_resource_validation`, `dcn10_fpu_init`. **Ninguno
  existe.** *El nombre real se encontró por relación —el validador de la capa genérica está
  donde el commit lo llama, no donde el modelo se calcula— y llegó a `bw_calcs` desde
  `dce112_resource.c:905` en tres pasos.*
- **Dos salidas por la vía equivocada, y las dos se detectaron por el nombre:**
  `dm_display_funcs` parecía la tabla principal y tiene 6 de 10 entradas a `NULL`; y
  `link_enc_cfg_validate` parecía el validador de modo y valida la unicidad de la
  asignación de codificadores. *Regla (g) y regla de relación-first, violated las dos en la
  misma iteración.*
- Encadenada con `184` (**las 21 guardas y la cadena de identidad; y aquí la contradicción
  que dejó**), `183` (otra sesión), `181` (**la cota del 27,8% desde una sola raíz, y sus
  dos puntos abiertos: `modules/` y las guardas**), `180` (otra sesión), `179` (**las cuatro
  clases, y que `dce_calcs.c` era «sorth»**), `178` (los dos canales), `173`, `172`, `167`,
  `165`, **`151` (DML1 y DML2, y aquí su alcance corregido a familia en vez de a chip)**,
  `159`, `156`, `149`, `140`.
- No se editó `AGENTS.md` ni `OPEN-FRONTIERS.md`, y no se añadió ningún fichero al corpus.

## Nota de método

**La contradicción de `184` no se resolvió buscando el validador, sino dejando de buscarlo.**
*Yo llevaba cuatro sondeos preguntando «cuál es la función de validación de modo», con
cuatro nombres inventados, y el nombre correcto no se encuentra: se llega.* **La relación
—el motor de esta placa tiene que ser llamado por el fichero de recurso de esta placa—
se cierra en tres pasos desde `dce112_resource.c:905`, y de paso aparece que el motor es
`bw_calcs` y que DML es de DCN.** *Regla de relación-first aplicada por fin a este dominio:
el nombre es índice, la relación es evidencia.*

**Y la contradicción tenía una forma que la hacía obvia si se hubiera mirado el conjunto y
no la rama: `dce_calcs.c` estaba clasificado como «sorth» desde `179` —cero delegación,
cero escrituras de registro— y eso ya decía que no toca el hardware.** *Tres notas antes de
que la pregunta se hiciera, la respuesta estaba en una tabla.*

**Y el otro resultado es la misma lección de `184` aplicada a `181`, y ya es la segunda vez
que sale en la misma forma: `181` presentó el 27,8% como la cota del subsistema, y era la
cota de una de las siete raíces.** *Medir la parte que se está mirando y generalizarla: es
el error dominante de esta tanda y aparece por tercera vez, siempre en la misma dirección
—un número que describe un subconjunto presentado como el conjunto— y siempre detenido por
un resultado imposible o una apertura que se nota al compararlo con algo ya medido.*

**Y queda un principio pequeño que resultó útil más de una vez: un cierre que va de `dc_create`
a un conjunto grande no prueba que el cálculo esté completo, si el conjunto no contiene la
función que hace el cálculo que te importa.** *Aquí la prueba es `calculate_bandwidth`: no
está, y eso invalida la palabra «cota» más que cualquier discusión sobre porcentajes.*