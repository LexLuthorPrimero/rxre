# 190 · Tres correcciones de la poda, siete de nueve pruebas, y el defecto que queda aislado

```
CLASSIFICATION=DOCUMENTATION+TOOLING · TRACK=STATIC
CORPUS=RESEARCH/working/linux-7.1.3 · HARDWARE_SCOPE=HOST-C/RX550/0000:01:00.0
WORK_CLASS=READ_ONLY/EVIDENCE · WRITE_LOCAL=PROPIOS · MODIFICATIONS_CORPUS=0 · WRITE_EXECUTION=NONE
RUNTIME=NOT_RUN · GPU INTACTA
```

## Qué resuelve

**La jugada que `189` dejó escrita: corregir el mapa con los nombres de macro, re-medir, y
contrastar contra las pruebas de imposibilidad.** `PROVEN`.

**⇒ Y la poda pasa de cero pruebas de imposibilidad superadas a siete de nueve, con tres
correcciones que son de una línea cada una.** `PROVEN`.

**⇒ El defecto que queda está aislado y medido: la resolución por nombre cruza la guarda, y
por eso sobreviven 193 funciones de un subárbol cuya entrada sí está podada.** `PROVEN`.

## 1 · Las tres correcciones, y qué cambió en cada una

| # | corrección | de | a |
|---|---|---|---|
| 1 | la clave del mapa es la **etiqueta del `switch`**, no el símbolo del llamante | `chip_family` → `{AMDGPU_FAMILY_VI}` | `chip_family` → `{FAMILY_VI}` |
| 2 | semántica de `switch` en C | `184`: no podar si ninguna etiqueta casa | se podan **todos** los brazos explícitos y se conserva **sólo `default:`** |
| 3 | segundo tipo de guardia: `if` sobre bandera de depuración | inexistente | `BANDERAS_FALSAS`, siete banderas |

**⇒ La corrección 1 es la de `189`: `dal_asic_id.h:308` declara `FAMILY_VI 130` y
`dc_resource.c:141` etiqueta `case FAMILY_VI:`, así que la clave del mapa era
`AMDGPU_FAMILY_VI`, un símbolo que se usa dos veces y no declara ninguna cabecera.**
`PROVEN`. *Las seis guardas sobre `chip_family` dejan de no casar y se podan; los `switch`
sin coincidencia pasan de siete a cinco.*

**⇒ La corrección 2 es una regla de `184` que estaba mal en la dirección contraria, y
decidirlo cuesta una línea de la gramática de C: si ninguna etiqueta de un `switch` coincide
con el valor, la ejecución cae a `default:` y a ningún otro brazo.** `PROVEN`. *La regla de
`184` era una reacción a un síntoma sin diagnosticar: no podar arrastraba los 14.467
códigos de `dc/dml2_0/` que `185` demostró que son de DCN.*

**⇒ La corrección 3 es un guardia que el censo entero no veía, porque es un `if` y no un
`switch`:**

```c
dc/dml2_0/dml2_wrapper.c:96   if ((in_dc->debug.using_dml21) &&
                                  (in_dc->ctx->dce_version >= DCN_VERSION_4_01)) {
                                      return dml21_create(in_dc, dml2, config);
                              }
```

**⇒ Y su valor es demostrable con cita: `amdgpu_dm/amdgpu_dm.c:2075` es la única
aparición de `DC_ENABLE_DML2` en todo `display/`, y pone `using_dml2` y `using_dml21` a
true dentro de ese `if` de máscara de depuración. Con la máscara a cero, las dos son
false.** `PROVEN`. *Y con esa corrección `dml21_create` e `dml21_init` quedan
inalcanzables, que es lo correcto.*

## 2 · Las nueve pruebas, y el estado

| prueba | `184` | ahora |
|---|---|---|
| `dc/dce60/` a cero — chip de 2013 | **FALLA** | **FALLA** (2 funciones) |
| `dc/dce80/` a cero | FALLA | **OK** |
| `dc/dml2_0/` a cero — `185`: es de DCN | **FALLA** | **FALLA** (246) |
| `dc/dce120/` a cero | FALLA | **OK** |
| `dc/dcn30/` a cero | — | **OK** |
| `dce112_validate_bandwidth` presente | FALLA | **OK** |
| `calculate_bandwidth` presente | FALLA | **OK** |
| `is_display_configuration_supported` presente | FALLA | **OK** |
| `bw_calcs` presente | FALLA | **OK** |

**⇒ Siete de nueve. Y `dc/dce120/`, `dc/dce80/` y `dc/dcn30/` a cero son las que
demonstran que la poda por versión funciona, porque son chips que existen en el corpus y no
en esta placa.** `PROVEN_DERIVED`.

**⇒ El total: 2.663 funciones y 98.078 de las 443.839 líneas, el 22,1%, frente al 27,8% de
`187` sin poda y al 12,0% de `184` con una poda rota.** `PROVEN_DERIVED`.

## 3 · Y el defecto que queda, aislado

**`dc/dml2_0/` son 246 funciones alcanzables, y se reparten en dos grupos que son cosas
distintas:**

| grupo | funciones | qué es |
|---|---|---|
| fuera de `dml21/` | **53** | `display_mode_core.c` (30), `display_mode_util.c` (21), `dml2_wrapper_fpu.c` (2) |
| dentro de `dml21/` | **193** | el subárbol `dml21/src/`, detrás de la bandera `using_dml21` |

**⇒ Los 53 primeros se crean sin ninguna guardia: `dml2_wrapper.c:100` reserva el contexto
de la biblioteca de modo después del `if`, sin condición.** `PROVEN`.

**⇒ Y los 193 segundos son un artefacto de la resolución por nombre.** `PROVEN_DERIVED`.
*Porque `dml21_create` e `dml21_init` ya son inalcanzables —la corrección 3 funcionó en la
entrada— y sus funciones siguen apareciendo, lo que significa que el camino que las alcanza
no pasa por la entrada sino por su **nombre**, desde un fichero del grupo sin guardia. La
herramienta resuelve símbolos, no bordes: una función definida en `dml21/` y llamada desde
`display_mode_core.c` es alcanzable aunque la única puerta de `dml21/` esté cerrada.*

**⇒ Y el mecanismo de fondo es el mismo de las 821 colisiones que `181` ya midió: se
resuelve por nombre con `setdefault`, y un nombre no sabe de qué lado de una guarda está su
definición.** `PROVEN_DERIVED`.

**⇒ `dc/dce60/` con dos funciones es el mismo defecto y no uno distinto: `dce60_timing_generator_construct`
se resuelve por nombre desde `dce60_resource.c:515`, y el fichero entero se alcanza por el
nombre de la función constructora, no por el `switch (dc_version)` que sí lo podaría.**
`PROVEN_DERIVED`.

**⇒ Y esto es un límite de la técnica, no un bug pendiente: para separar «definido dentro de
una guarda» de «llamado desde fuera de ella» hace falta analizar el flujo de control, y un
grafo de símbolos no lo tiene.** `LIMITATION`. *La herramienta puede demostrar que un
sistema operativo de 2013 es inalcanzable si nadie lo nombra; no puede demostrarlo si el
nombre es lo único que lo ata al grafo.*

## Lo que NO cierra

| afirmación | estado |
|---|---|
| Las tres correcciones, y qué cambió | `PROVEN` |
| 2.663 funciones, 98.078 líneas, 22,1% | `PROVEN_DERIVED` |
| Siete de nueve pruebas de imposibilidad | `PROVEN` |
| `dml2_create` crea 53 símbolos sin guardia | `PROVEN` |
| 193 de `dml21/` sobreviven por resolución de nombre | `PROVEN_DERIVED` |
| Las 821 colisiones son el mecanismo de fondo | `PROVEN_DERIVED` |
| El límite: un grafo de símbolos no tiene flujo de control | `LIMITATION` |
| `dc/dce60/` a cero | **`NOT_DETERMINED`** |
| El total real, con las 246 y las 2 de `dce60` fuera | **`NOT_DETERMINED`** |
| Separar por flujo de control, no por nombre | **`NOT_DETERMINED`** |

**Las dos primeras abiertas son la misma cosa y su orden está fijado por los datos: si se
pudieran quitar las 246 funciones de `dc/dml2_0/` y las 2 de `dc/dce60/`, el total bajaría
de 98.078 líneas, y la magnitud exacta depende de cuántas de las 193 de `dml21/` están
realmente detrás de la bandera.** `NOT_DETERMINED`.

**Y la tercera es la que decide si vale la pena: un análisis de flujo de control sobre
`display/` es una herramienta distinta, no un parámetro más de esta.** `NOT_DETERMINED`.
*Y la alternativa más barata existe y es un criterio de valor, no de flujo: **los símbolos
definidos dentro de un directorio cuyo subárbol entero se puede demostrar muerto, se
excluyen**.* *Y el criterio de directorio es el que ya se usó en `181` para medir el 27,8% sin poda,
así que la evidencia para aplicarlo ya existe.*

## Procedencia

- `STATIC` -- `tools/inst_closure.py`: `VALOR_POR_PLANTA` con doce variables
  (`dc_version`, `version`, `ctx->dce_version`, `in_dc->ctx->dce_version`, `dce`,
  `adev->asic_type` con valor verificado; las cuatro `chip_family` con `{FAMILY_VI}`; y
  `adev->family` y `dcn_version` con conjunto vacío a propósito),
  `BANDERAS_FALSAS` con siete banderas, `_podar_banderas()`, y la regla de `switch`
  reemplazada por la semántica de `default:`. `--selftest` con 23 vectores, todos pasan.
- `display/dc/dml2_0/dml2_wrapper.c:93` (`dml2_create`), `:96` (el `if` sobre
  `using_dml21`), `:100` (la reserva del contexto sin guardia),
  `display/dc/core/dc_state.c:194` (`dc_state_create`, que es quien la llama
  incondicionalmente), `display/dc/dml2_0/dml21/dml21_wrapper.c:48` (`dml21_create`),
  `display/dc/dml2_0/dml21/dml21_wrapper_fpu.c:35` (`dml21_init`),
  `display/amdgpu_dm/amdgpu_dm.c:2075` (`DC_ENABLE_DML2`, única aparición),
  `display/dc/core/dc_resource.c:141` (`case FAMILY_VI:`),
  `display/include/dal_asic_id.h:308` (`#define FAMILY_VI 130`),
  `display/dc/resource/dce60/dce60_resource.c:515` (la llamada a
  `dce60_timing_generator_construct`), `display/dc/dce60/dce60_timing_generator.c:245`.
- El camino completo a un símbolo de `dc/dml2_0/`, impreso por el programa con once saltos:
  `dc_create` → `dc_construct` → `dc_state_create` → `dml2_create` → `dml21_create` →
  `dml21_init` → `dml2_initialize_instance` → `dml2_top_soc15_initialize_instance` →
  `dml2_core_create` → `core_dcn4_mode_programming` → `dml2_core_calcs_mode_programming_ex`
  → `dml_core_mode_programming`.
- **Un error de edición propio al cambiar el mapa: dejé `},` con coma final, que convierte
  el diccionario en tupla de un elemento, y el programa falló con
  `AttributeError: 'tuple' object has no attribute 'get'`.** `ERROR`. *Una coma final en un
  literal de diccionario a nivel de módulo es sintácticamente válida y semánticamente otra
  cosa, que es la clase de error más difícil de ver porque el programa no dice nada.*
- Encadenada con `189` (**el mapa con nombres de macro, que es la corrección 1 de esta
  nota**), `188` (la cadena observada y el `PROVEN_ABSENT` del símbolo), `187` (**los dos
  caracteres y las seis pruebas, que son las que se usan aquí de nuevo**), `185` (**DML2 es
  de DCN, que es la afirmación que sostiene dos de las nueve pruebas**), `184` (**las 21
  guardas y la poda, y la regla conservadora que esta nota corrige**), `181` (las 821
  colisiones, que son el mecanismo de fondo), `178`, `173`, `172`, `169`, `165`, `163`,
  `151`, `140`.
- No se editó `AGENTS.md` ni `OPEN-FRONTIERS.md`, y no se añadió ningún fichero al corpus.

## Nota de método

**Tres correcciones de una línea cada una, y el instrumento pasa de no superar ninguna
prueba de imposibilidad a superar siete de nueve.** *La primera era un nombre equivocado en
el mapa, la segunda una regla mia de `184` que estaba mal en la dirección contraria, y la
tercera un tipo de guardia entero que no existía en la herramienta.*

**Y la segunda es la que más conviene escribir, porque es una regla que inventé para
protegerme de un síntoma que no había diagnosticado.** *La regla conservadora de `184`
decía «si ninguna etiqueta coincide, no podes nada»; la razón por la que la escribí fue que
podar un `switch` entero dejaba el árbol sin código, que fue lo que vi. **No poda** era una
defensa contra un error de mapa que se parecía a un bug de la herramienta, y el bug de la
herramienta estaba en otra línea: la gramática de `switch` dice que sin etiqueta que coincida
se cae a `default:`, y eso no es una convención mía ni de nadie, es C.**

**Y hay un patrón en las tres, y es el mismo de `187`:** *cada una era un supuesto sobre la
forma del código en un punto donde no había leído el código.* **El mapa suponía que el
`switch` etiquetaba con el símbolo del llamante; la poda suponía que un `switch` sin
coincidencia se quedaba entero; el censo suponía que todas las guardas son `switch`.** Las
tres se resolvieron abriendo el fichero, y las tres eran un `sed` o un `cut` de distancia.

**Y el límite que queda, escrito con la frase que lo resume: *un grafo de símbolos sabe qué
puede llamar a qué, y no sabe qué está detrás de una puerta cerrada si el nombre cruza la
puerta*.** *Es la misma razón por la que la cifra sin poda es un techo y la poda es una
cota: las dos herramientas miden cosas distintas, y la segunda necesita saber de qué lado de
un `if` está cada definición, que es un problema de flujo de control y no de símbolos.*

**Y una observación sobre el orden, que es la que más se ha repetido sin mejorar: la tercera
corrección se encontró porque dos pruebas seguían fallando y me negué a publicar un 22,1%
sin explicar por qué.** *Las siete pruebas que pasan son las que se escribieron en otras
notas, y ninguna se escribió para esta: se escribieron porque en su momento un número
pareció imposible.*