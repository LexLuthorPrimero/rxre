# 184 · Las 21 guardas de identidad de chip, la cadena que las resuelve, y por qué la poda no es usable todavía

```
CLASSIFICATION=DOCUMENTATION+TOOLING · TRACK=STATIC
CORPUS=RESEARCH/working/linux-7.1.3 · HARDWARE_SCOPE=HOST-C/RX550/0000:01:00.0
WORK_CLASS=READ_ONLY/EVIDENCE · WRITE_LOCAL=PROPIOS · MODIFICATIONS_CORPUS=0 · WRITE_EXECUTION=NONE
RUNTIME=NOT_RUN · GPU INTACTA
```

## Qué resuelve

**La jugada que `181` nombró: bajar la cota de 27,8% podando las guardas de ASIC. Y el
resultado son tres cosas: dos cerradas y una que queda declarada inservible.** `PROVEN`.

**⇒ De 1.112 `switch` en `display/`, exactamente 21 tienen etiquetas de identidad de
chip. Esos 21 son el coste entero de bajar la cota, y se enumeran solos.** `PROVEN`.

**⇒ Y la cadena que dice qué valor toma cada variable en esta placa está escrita de
principio a fin en el corpus, con cita para cada eslabón.** `PROVEN`.

**⇒ Y la poda, con el mapa correcto y los 21 sitios, da 12,0% — y ese número NO es
usable, porque elimina 407 de las 498 funciones alcanzables de `dc/hwss/`, y
`dce110_hwseq.c` es precisamente el código de esta placa.** `REFUTED`.

## 1 · Los 21 puntos de decisión, y sólo 21

**Censo automático: `switch` cuya etiqueta de `case` empieza por `DCE_VERSION_`,
`DCN_VERSION_`, `CHIP_`, `AMDGPU_FAMILY_`, `FAMILY_` o `REV_`.**

**⇒ 1.112 `switch` en total, 21 con etiquetas de identidad de chip.** `PROVEN`.

| fichero:línea | variable | etiquetas |
|---|---|---|
| `amdgpu_dm/amdgpu_dm.c:2348` | `adev->asic_type` | 22 etiquetas |
| `amdgpu_dm/amdgpu_dm.c:5768` | `adev->asic_type` | 20 etiquetas |
| `amdgpu_dm/amdgpu_dm.c:5995` | `adev->asic_type` | 20 etiquetas |
| `amdgpu_dm/amdgpu_dm_plane.c:744` | `adev->family` | 12 etiquetas |
| `amdgpu_dm/amdgpu_dm_pp_smu.c:759` | `ctx->dce_version` | 4 etiquetas |
| `dc/basics/dce_calcs.c:49` | `asic_id.chip_family` | 3 etiquetas |
| `dc/bios/command_table_helper.c:38` | `dce` | 10 etiquetas |
| `dc/bios/command_table_helper2.c:39` | `dce` | 32 etiquetas |
| `dc/clk_mgr/clk_mgr.c:152` | `asic_id.chip_family` | 17 etiquetas |
| `dc/clk_mgr/clk_mgr.c:393` | `clk_mgr_base->ctx->asic_id.chip_family` | 10 etiquetas |
| `dc/core/dc.c:6001` | `dc->ctx->asic_id.chip_family` | 4 etiquetas |
| **`dc/core/dc_resource.c:141`** | **`asic_id.chip_family`** | **17** |
| **`dc/core/dc_resource.c:272`** | **`dc_version`** | **32** |
| `dc/dc_helper.c:692` | `version` | 32 etiquetas |
| `dc/dc_spl_translate.c:85` | `plane_state->ctx->dce_version` | 4 etiquetas |
| `dc/dml2_0/dml21/dml21_translation_helper.c:44` | `dcn_version` | 2 etiquetas |
| `dc/dml2_0/dml2_wrapper.c:61` | `in_dc->ctx->dce_version` | 6 etiquetas |
| `dc/gpio/hw_factory.c:64` | `dce_version` | 32 etiquetas |
| `dc/gpio/hw_translate.c:68` | `dce_version` | 32 etiquetas |
| `dc/link/protocols/link_edp_panel_control.c:846` | `link->ctx->asic_id.chip_family` | 4 etiquetas |
| `dc/soc_and_ip_translator/soc_and_ip_translator.c:12` | `dc_version` | 2 |

**⇒ Los dos de `dc/core/dc_resource.c` son los que importan, y están en la misma función
lógica: uno deriva la versión y el otro la despacha.** `PROVEN_DERIVED`.

**⇒ Y una corrección de método sobre el propio censo: un patrón más laxo
(`AMDGPU_` en vez de `AMDGPU_FAMILY_`) daba 23, y los 2 de más eran falsos positivos —
`amdgpu_dm_color.c:857` sobre funciones de transferencia y `amdgpu_dm_irq.c:680` sobre
HPD. Ninguna de las dos variables es identidad de chip.** `ERROR`. *Regla (j): un criterio
de clasificación tiene que mencionar la misma cosa que la pregunta.*

## 2 · La cadena de identidad, de 0x699F a `DCE_VERSION_11_2`

**Cada eslabón con su cita, y ninguno supuesto:**

```c
amdgpu/amdgpu_drv.c:2041        {0x1002, 0x699F, PCI_ANY_ID, PCI_ANY_ID, 0, 0, CHIP_POLARIS12},
amdgpu/amdgpu_device.c:1980     case CHIP_POLARIS12:
amdgpu/amdgpu_device.c:1987             adev->family = AMDGPU_FAMILY_VI;
display/amdgpu_dm/amdgpu_dm.c:1910       init_data.asic_id.chip_family = adev->family;
display/dc/core/dc_resource.c:141   switch (asic_id.chip_family) {
display/dc/core/dc_resource.c:170       case FAMILY_VI:
display/dc/core/dc_resource.c:178           if (ASIC_REV_IS_POLARIS12_V(asic_id.hw_internal_rev)) {
display/dc/core/dc_resource.c:179               dc_version = DCE_VERSION_11_2;
```

**⇒ El identificador de PCI que se mide con `lspci` —0x699F, "Lexa PRO"— lleva a
`CHIP_POLARIS12`, y de ahí a `AMDGPU_FAMILY_VI` por la rama no-APU de
`amdgpu_device.c:1984-1987`, y de ahí a `DCE_VERSION_11_2` por
`resource_parse_asic_id`.** `PROVEN`.

**⇒ Y `FAMILY_CZ` da `DCE_VERSION_11_0` y `FAMILY_VI` da `11_2`: son dos familias
distintas para el mismo GFX8, y esta placa es la segunda.** `PROVEN`. *Es la diferencia
entre Carrizo, que es APU, y Polaris10/11/12, que no lo es; `amdgpu_device.c:1984-1987`
las separa con `AMD_IS_APU`.*

**⇒ Y el `case` que sobrevive al despacho es `dc_resource.c:308-309`,
`DCE_VERSION_11_2` y `DCE_VERSION_11_22`, que llaman a `dce112_create_resource_pool`.**
`PROVEN`.

**⇒ De los 32 casos de `dc_create_resource_pool`, uno solo se ejecuta en esta placa.**
`PROVEN_DERIVED`. *Y por eso `dc/resource/dce110/` —1.561 líneas— es código muerto en esta
placa aunque sus bloques sean `dce110_`: el pool se crea por `dce112`, y son las
construcciones de bloque las que se llaman `dce110_`.*

## 3 · Y `151`, confirmado y localizado en una línea

**`151` afirmó que DML2 está apagado salvo que alguien encienda `DC_ENABLE_DML2` a mano.
Es cierto, y el sitio exacto es único:**

```c
display/amdgpu_dm/amdgpu_dm.c:2075    if (amdgpu_dc_debug_mask & DC_ENABLE_DML2) {
                                          adev->dm.dc->debug.using_dml2  = true;
                                          adev->dm.dc->debug.using_dml21 = true;
```

**⇒ `DC_ENABLE_DML2` tiene UNA ocurrencia en todo `display/`, y `using_dml2` y
`using_dml21` sólo se ponen a true dentro de ese `if`.** `PROVEN_ABSENT` para cualquier
otra vía. `PROVEN`.

**⇒ Y una corrección de alcance a `151`: su título dice «DCE 10.0 usa DML1», y eso es
una afirmación sobre DCE 10.0, no sobre esta placa.** `ERROR`. *Mi resumen anterior de
`172` le había atribuido la medida de DML a esta nota, y `172` no menciona DML en
absoluto; la nota de DML es `151`. Confundir la nota de una medida con la de otra es la
misma clase de error que citar el fichero equivocado, y la regla es abrir la nota que
corrige, no su resumen.*

## 4 · Por qué el 12,0% podado no es un resultado

**La poda con el mapa correcto da 1.596 funciones y 53.142 líneas, el 12,0%, frente al
27,8% sin podar de `181`. Y es incorrecto.** `REFUTED`.

**La prueba, y es una impossibility test:** de los 1.481 símbolos que la poda elimina,
**407 están en `dc/hwss/`** — de las 498 funciones que `181` declaró alcanzables, la poda
deja 91. `PROVEN`.

**⇒ Y eso es imposible: `dc/hwss/dce110/dce110_hwseq.c` es el secuenciador de esta placa,
con los 75 manejadores que contó `173`, y su tabla se engancha desde
`dce112_hw_sequencer_construct`, que está en `dc/hwss/dce112/dce112_hwseq.c:152` y cuyo
único caller es alcanzable.** `PROVEN_DERIVED`.

**⇒ El defecto está en el censo de guardas, no en el mapa: los conteos por fichero son
sospechosos.** `dc/dc_helper.c:692`, `dc/gpio/hw_factory.c:64`,
`dc/gpio/hw_translate.c:68` y `dc_resource.c:272` tienen **32 casos cada uno**, y el
`switch (asic_id.chip_family)` de `dc_resource.c:141` reporta 17 etiquetas que incluyen
`AMDGPU_FAMILY_GC_10_3_6`, que **no son de esa función** sino de un `switch` posterior del
mismo fichero. `PROVEN`.

**⇒ El censo sigue mezclando etiquetas entre `switch` vecinos, y una guarda con etiquetas
equivocadas poda las líneas equivocadas.** `PROVEN_DERIVED`. *Se cambió el criterio de
«la próxima llave» a «profundidad de llaves» y mejoró —`resource_parse_asic_id` pasó de
contar 5 etiquetas a 17, que son las correctas— pero no quedó cerrado.*

**⇒ Y hay un segundo defecto, independiente: siete de los 21 `switch` se dejan sin podar
porque ninguna de sus etiquetas coincide con el valor declarado, y eso se reporta como
contradicción en vez de podarse.** `PROVEN`. *Lista: `dce_calcs.c:49`, `clk_mgr.c:152`,
`clk_mgr.c:393`, `dc_resource.c:141`, `dml2_wrapper.c:61`, `link_edp_panel_control.c:846`,
`soc_and_ip_translator.c:12`.*

**⇒ Y dos de esas siete se explicarían por una colisión de nombres que ya está en la
serie: el mapa declara `AMDGPU_FAMILY_VI` y `dce_calcs.c:49` etiqueta `FAMILY_VI`.** El
mismo valor, dos escrituras, y por eso no casa ninguna etiqueta. `PROVEN_DERIVED`.

**⇒ La regla generalizable, y es la de esta nota: cuando una herramienta devuelve un
número menor del que la evidencia independiente exige, el defecto es del criterio de la
herramienta y no del dato.** `PROVEN_DERIVED`.

## Lo que NO cierra

| afirmación | estado |
|---|---|
| 1.112 `switch`, 21 con etiquetas de identidad de chip | `PROVEN` |
| La cadena 0x699F → `CHIP_POLARIS12` → VI → `DCE_VERSION_11_2` | `PROVEN` |
| Un solo `case` ejecutable de 32 en `dc_create_resource_pool` | `PROVEN_DERIVED` |
| `dc/resource/dce110/` es código muerto en esta placa | `PROVEN_DERIVED` |
| `DC_ENABLE_DML2`: una ocurrencia, y `using_dml2` off por defecto | `PROVEN_ABSENT` |
| El 12,0% podado | **`REFUTED`** |
| El 27,8% de `181` | `PROVEN_DERIVED` — sigue en pie |
| El censo de guardas mezcla etiquetas entre `switch` vecinos | `PROVEN_DERIVED` — defecto abierto |
| `FAMILY_VI` y `AMDGPU_FAMILY_VI`, el mismo valor con dos escrituras | `PROVEN_DERIVED` |
| Cuál es el motor de cálculo de modo de Polaris12 | **`NOT_DETERMINED`** |
| Cuánto baja la cota una vez arreglado el censo | **`NOT_DETERMINED`** |

**La quinta de las abiertas es una contradicción, no un hueco, y hay que resolverla antes
que nada: tras podar por `DCE_VERSION_11_2`, ni `dc/dml/` ni `dc/dml2_0/` muestran camino
de validación de modo, y `using_dml2` está apagado por defecto.** `NOT_DETERMINED`.
*Las tres cosas no pueden ser ciertas a la vez: o el motor de esta placa está en un
tercer sitio, o la poda cortó un camino legítimo, o `dc/dml/dcn10/` —que sólo incluye
`dc/resource/dcn10/dcn10_resource.h:30`, es decir, el pool de DCE 10.0— es el validador de
esta placa y `dc/resource/dce112/` lo alcanza por un camino que mi mapa no declara.*
**Es la contradicción que hay que abrir, y se abre leyendo `dce112_create_resource_pool`,
que son 25 funciones y ninguna ha sido leída.**

## Procedencia

- `STATIC` -- `tools/inst_closure.py`, ramas nuevas `--censo_guardas` y `--podar`, más
  `censo_guardas()`, `podar()` y `VALOR_POR_PLANTA`. `--selftest` con 22 vectores.
- `display/dc/core/dc_resource.c:141` (`switch (asic_id.chip_family)`), `:170`
  (`case FAMILY_VI`), `:178` (`ASIC_REV_IS_POLARIS12_V`), `:179`
  (`dc_version = DCE_VERSION_11_2`), `:266` (`dc_create_resource_pool`), `:272`
  (`switch (dc_version)`), `:308-309` (`case DCE_VERSION_11_2` / `11_22`),
  `display/amdgpu_dm/amdgpu_dm.c:1910` (`chip_family = adev->family`),
  `display/amdgpu_dm/amdgpu_dm.c:2075` (`DC_ENABLE_DML2`),
  `display/amdgpu_dm/amdgpu_dm.c:2038` (`dc_create(&init_data)`),
  `display/dc/core/dc.c:1508` (`dc_create`),
  `display/dc/hwss/dce112/dce112_hwseq.c:152` (`dce112_hw_sequencer_construct`),
  `display/dc/hwss/dce110/dce110_hwseq.c:3558` (`dce110_hw_sequencer_construct`),
  `display/dc/dml2_0/dml2_wrapper.c:61` (`switch (in_dc->ctx->dce_version)`),
  `display/dc/resource/dcn10/dcn10_resource.h:30` (`#include "dml/dcn10/dcn10_fpu.h"`).
- Fuera de `display/`, para cerrar la cadena de identidad:
  `amdgpu/amdgpu_drv.c:2041`, `amdgpu/amdgpu_device.c:1980`,
  `amdgpu/amdgpu_device.c:1984-1987`.
- Patrones del censo: `switch\s*\(\s*([\w\.\->\[\]]+)\s*\)` para el `switch`,
  `case\s+(\w+)\s*:` para las etiquetas, y el filtro de identidad
  `^(DCE_VERSION_|DCN_VERSION_|CHIP_|AMDGPU_FAMILY_|FAMILY_|REV_)`.
- **Cuatro defectos de la capa de poda, y los cuatro los delató un resultado imposible, no
  un programa de medida:**
  1. Desajuste de coordenadas: la línea de la guarda es absoluta al fichero y se
     indexaba contra un recorte de función. **Síntoma: la poda no modificaba ni una línea
     de 32 casos presentes, y `dc/dce60` seguía al 50%.**
  2. La otra mitad del mismo: se traducía la línea del `switch` y no las de cada `case`.
  3. Tiradas de etiquetas: en C las etiquetas consecutivas comparten cuerpo por
     *fall-through*. Podiendo etiqueta por etiqueta, `DCE_VERSION_11_22` —que no es de esta
     placa— se llevaba el cuerpo de `dce112_create_resource_pool` y `dc/resource` quedaba
     en 0,0%.
  4. Podar un `switch` cuyas etiquetas no contienen el valor declarado deja el `switch`
     vacío. **Síntoma: `amdgpu_dm_pp_smu.c:759` es un `switch (ctx->dce_version)` con las
     cuatro etiquetas `DCN_VERSION_*`, y `dc/hwss` pasó de 498 funciones alcanzables a 90.**
- **Seis nombres inventados en las sondas de esta iteración:** los seis validadores de DML
  que probé (`dcn10_dml_resource_validation`, `dml2_mode_configuration`, …) no existen;
  el nombre real del constructor deASIC es `dce64_create_resource_pool` y no
  `dce64_create_resource_pool`con el prefijo que yo esperaba; y `dp_train_dp.c` de la
  iteración anterior.
- Encadenada con `181` (**la cota del 27,8% y los 21 sitios que la bajan**), `180` (otra
  sesión: las ocho direcciones de registro), `179` (las cuatro clases), `178` (los dos
  canales), `173` (**los 75 manejadores, que son la prueba de que la poda es
  incorrecta**), `172` (la capa genérica), **`151` (DML1 y DML2, confirmado y acotado)**,
  `167`, `165` (**«cuánto de display es genérico»**), `159` (los 52 constructores),
  `156`, `149`, `140`.
- No se editó `AGENTS.md` ni `OPEN-FRONTIERS.md`, y no se añadió ningún fichero al corpus.

## Nota de método

**El resultado que importa de esta iteración es un número que no escribo.** *La poda da
12,0%, y ese número baja casi a la mitad el 27,8% de `181`, lo cual lo hace muy
atractivo; y sin el test de imposibilidad de la sección 4 habría entrado en el
informe como el cierre del bloque.* **La prueba que lo mató es que la poda eliminaba 407
de las 498 funciones de `dc/hwss/`, y `dce110_hwseq.c` es el secuenciador de esta
placa.** *Un número que mejora la conclusión anterior no merece más confianza que uno que
la empeora, y el que la empeora se investiga; el que la mejora se acepta.*

**Y el criterio es el más general de todo el bloque: cuando una herramienta da un número
menor del que la evidencia independiente exige, el defecto es del criterio, no del
dato.** *Es la regla (k) aplicada al revés de como la he usado hasta ahora: no «el
resultado delata el error de criterio» sino «el resultado viola una cota conocida y hay
que averiguar cuál de las dos cosas está mal».*

**Y los cuatro defectos de la capa de poda tienen la misma firma, que es la que más se ha
repetido en este bloque: coordenadas, coordenadas, estructura de C, y criterio.** *Las
dos primeras son el mismo error acumulado en dos sitios; la tercera es no conocer la
semántica de la construcción que se poda; la cuarta es no preguntarse qué valdría un
resultado imposible.*

**Y hay un hallazgo lateral que no era el objetivo y que vale por sí solo: la cadena de
identidad del chip, de `0x699F` a `DCE_VERSION_11_2`, está escrita entera en el corpus
con un solo eslabón no citado por mí, que es el identificador de PCI que lee `lspci`.**
*Y de ella sale que `dc/resource/dce110/` es código muerto en esta placa, 1.561 líneas
que compilan y no se ejecutan, porque el pool lo crea `dce112` aunque los bloques sean
`dce110_`. Un directorio por generación no dice si lo de dentro corre.*