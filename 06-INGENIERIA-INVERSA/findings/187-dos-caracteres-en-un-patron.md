# 187 · Dos caracteres en un patrón valían 1.534 funciones, y el 48,4% pasa seis pruebas

```
CLASSIFICATION=DOCUMENTATION+TOOLING · TRACK=STATIC
CORPUS=RESEARCH/working/linux-7.1.3 · HARDWARE_SCOPE=HOST-C/RX550/0000:01:00.0
WORK_CLASS=READ_ONLY/EVIDENCE · WRITE_LOCAL=PROPIOS · MODIFICATIONS_CORPUS=0 · WRITE_EXECUTION=NONE
RUNTIME=NOT_RUN · GPU INTACTA
```

## Qué resuelve

**El bug con reproductor de una línea que `185` nombró: `bw_calcs` no era alcanzable. Y la
causa eran dos caracteres en una expresión regular, no un error de diseño.** `PROVEN`.

**⇒ La línea real es `pool->base.funcs = &dce112_res_pool_funcs;` y un patrón
`->(\w+)\s*=\s*(\w+)` no casa por dos razones a la vez.** `PROVEN`.

**⇒ Con los dos arreglados: 5.353 funciones y 214.858 de las 443.839 líneas alcanzables
desde las siete raíces, el 48,4%, y las seis pruebas independientes de `185` pasan.** `PROVEN_DERIVED`.

## 1 · Los dos caracteres

```c
dc/resource/dce112/dce112_resource.c:1243    pool->base.funcs = &dce112_res_pool_funcs;
```

| lo que falla | lo que escribí | lo que hay |
|---|---|---|
| el nombre del campo tiene **dos niveles** | `(\w+)` | `base.funcs` |
| la tabla se asigna **por referencia** | `(\w+)` tras el `=` | `&dce112_res_pool_funcs` |

**⇒ Los dos fallos están en la misma línea de código, y por eso producían el mismo
síntoma y el síntoma era invisible: la tabla entera se caía del grafo.** `PROVEN`.

**⇒ Y lo que se caía con ella era `dce112_validate_bandwidth` —las 964 líneas de las
abs 893..964— y detrás `bw_calcs`, `calculate_bandwidth`,
`is_display_configuration_supported`, es decir la validación de ancho de banda de esta
placa.** `PROVEN`.

**⇒ Y hay un segundo lugar con el mismo defecto: `dc/resource/dce120/dce120_resource.c:919`
asigna la misma función, `.validate_bandwidth = dce112_validate_bandwidth`, y
`dce120_res_pool_funcs` existe como tabla.** `PROVEN`.

## 2 · Lo que valía, medido en tres pasos

| | raíces | patrones | funciones | líneas | % |
|---|---|---|---|---|---|
| `181` | 1 | 2 | 3.077 | 123.571 | 27,8% |
| `185` | 7 | 2 | 3.819 | 149.588 | 33,7% |
| **`187`** | **7** | **4** | **5.353** | **214.858** | **48,4%** |

**⇒ Los dos caracteres de la sección 1 valían 1.534 funciones y 65.270 líneas por sí
solos, sin cambiar ni una raíz.** `PROVEN_DERIVED`.

**⇒ Y `dc/hwss/` pasa de 498 de 525 funciones alcanzables a 522 de 525: el 99,4%.**
`PROVEN`. *Es lo que cabe esperar de un directorio que es el secuenciador de hardware de
esta placa, y que una herramienta con dos caracteres mal escritos dejaba en 94,9% por
casualidad y no por acierto.*

## 3 · Las seis pruebas, que es lo que valida la cifra

**Las mismas seis que `185` declaró como prueba de que el motor es `bw_calcs`. Con los dos
patrones arreglados las seis pasan:**

| prueba | en índice | alcanzable |
|---|---|---|
| `dce112_validate_bandwidth` (`dce112_resource.c:893`) | sí | **sí** |
| `bw_calcs` (`dc/basics/dce_calcs.c:3041`) | sí | **sí** |
| `bw_calcs_init` (`dc/basics/dce_calcs.c:2043`) | sí | **sí** |
| `calculate_bandwidth` (`dc/basics/dce_calcs.c:75`) | sí | **sí** |
| `is_display_configuration_supported` (`dc/basics/dce_calcs.c:2766`) | sí | **sí** |
| `dce112_res_pool_funcs` (`dce112_resource.c:1060`) | **no** | no |

**⇒ Las cinco primeras pasan y la sexta es correcta que falle: `dce112_res_pool_funcs` es
una tabla, no una función, y no está en el índice de funciones por construcción.**
`PROVEN`. *Un caso de prueba que falla por la razón correcta es una medida; uno que pasa
siempre no es nada.*

**⇒ Y el orden de las pruebas importa: en `185` fallaban las cinco, y la conclusión fue
falta era de la herramienta porque `bw_calcs` tenía un caller alcanzable. Si no se hubiera
comprobado el caller, la lectura habría sido que la función no se usaba.** `PROVEN_DERIVED`.

## 4 · Y la poda de `184` sigue sin ser usable, por una vía que no es la de antes

**Con los patrones corregidos, la poda da 2.666 funciones y 97.478 líneas, el 22,0%, y sigue
refutada. Pero la prueba que la refuta ahora es otra y es independiente.** `REFUTED`.

| | `184` | `187` |
|---|---|---|
| `dc/dce60/` alcanzable | 13,1% | **33,3%** |
| `dc/dce80/` alcanzable | 0,0% | 0,0% |
| `dc/hwss/` alcanzable | 90 de 525 | **318 de 525** |

**⇒ La primera prueba de `184` —«la poda se come el secuenciador de esta placa»— ya no
aplica: `dc/hwss` baja de 522 a 318 y no a 91.** `PROVEN`.

**⇒ Y la que la refuta ahora es la de `185`, y es cruzada: `dc/dml2_0/` sale 49,1%
alcanzable bajo la poda, y `185` demostró con cita que DML2 es de DCN, con selectores que
sólo contienen `DCN_VERSION_*`, mientras esta placa es `DCE_VERSION_11_2`.** `PROVEN_DERIVED`.

**⇒ Un resultado de una nota sirve para refutar un número de otra, y eso es más fuerte que
la comprobación interna que hizo el primer test de imposibilidad.** `PROVEN_DERIVED`.
*Regla (k) aplicada entre notas: el criterio de imposibilidad no tiene por qué estar en la
misma nota que el número.*

**⇒ El defecto sigue estando donde `184` lo localize: el censo de guardas mezcla etiquetas
entre `switch` vecinos, y tres siguen sin podar por contradicción —`dce_calcs.c:49` con
`FAMILY_VI` frente a `AMDGPU_FAMILY_VI` del mapa, `dc_resource.c:141` y
`dml2_wrapper.c:61`.** `NOT_DETERMINED`.

## Lo que NO cierra

| afirmación | estado |
|---|---|
| Los dos caracteres: punto en el campo y `&` en el valor | `PROVEN` |
| 5.353 funciones y 214.858 líneas, 48,4% | `PROVEN_DERIVED` |
| `dc/hwss/` al 99,4% de sus funciones | `PROVEN` |
| Las cinco pruebas de `bw_calcs` pasan | `PROVEN` |
| `dce112_res_pool_funcs` no es función y por eso no está | `PROVEN` |
| El 22,0% podado | **`REFUTED`** |
| El defecto del censo de guardas | **`NOT_DETERMINED`** |
| Cuánto baja la cota con el censo arreglado | **`NOT_DETERMINED`** |
| El alcance a través de `drm_atomic_helper_commit` | **`NOT_DETERMINED`** |

**La primera de las abiertas tiene el eslabón más pequeño de toda esta tanda: un `switch`
por neighbouring.** `NOT_DETERMINED`. *Y hay un dato que la acota: los tres switch que
quedan sin podar son `dce_calcs.c:49`, `dc_resource.c:141` y `dml2_wrapper.c:61`, y los
tres están en ficheros con más de un `switch` de identidad, que es exactamente la condición
del defecto.*

**Y la tercera sigue siendo la que hace la cifra utilizable: `.atomic_commit =
drm_atomic_helper_commit` está fuera del corpus, y el 48,4% es un techo porque hay un tramo
del grafo entre `display/` y el core de DRM que no se recorre.** `LIMITATION`.

## Procedencia

- `STATIC` -- `tools/inst_closure.py`. Los dos patrones reparados:
  `ASSIGN` pasa de `->\s*(\w+)\s*=\s*(\w+)` a `->\s*([\w\.]+)\s*=\s*&?\s*(\w+)`, y `CAMPO`
  de `\.\s*(\w+)\s*=\s*(\w+)` a `\.\s*(\w+)\s*=\s*&?\s*(\w+)`. `--selftest` con 23
  vectores, todos pasan.
- `display/dc/resource/dce112/dce112_resource.c:1060`
  (`static const struct resource_funcs dce112_res_pool_funcs`), `:1064`
  (`.validate_bandwidth = dce112_validate_bandwidth`), `:1243`
  (`pool->base.funcs = &dce112_res_pool_funcs;`), `:893`
  (`dce112_validate_bandwidth`, cuerpo abs 893..964), `:905` (la llamada a `bw_calcs`),
  `:1415` (`bw_calcs_init`),
  `display/dc/resource/dce120/dce120_resource.c:919`
  (`.validate_bandwidth = dce112_validate_bandwidth`),
  `display/dc/basics/dce_calcs.c:75`, `:2043`, `:3041`, `:3078`, `:2766`,
  `display/dc/dml2_0/dml2_wrapper.c:61`.
- Los tres subárboles de la tabla de la sección 2 se imprimen con la misma rutina y el
  mismo denominador en las tres filas: `1000 × puntos / líneas` para el porcentaje, y el
  recuento de funciones sobre el índice de 7.892.
- **El vector T23 del selftest usa la línea real del corpus, y por eso cazó los dos
  defectos a la vez.** `PROVEN`. *Un fixture inventado con `x->funcs = tabla` habría
  pasado con uno solo de los dos arreglado, y es la razón por la que este bloque tiene
  una regla que no estaba escrita: un caso de prueba se copia del fichero, no del esquema
  que uno cree que tiene.*
- **Y la lección del orden, que es la que más cuesta: en `185` la cifra mejoró de 33,7% y
  la mejora presenters como cierre, y el defecto real era más pequeño que la mejora.** `ERROR`.
- Encadenada con `185` (**las siete raíces y el motor `bw_calcs`, y su bug con reproductor
  de una línea**), `184` (**las 21 guardas, y el `REFUTED` de su poda, que aquí se refuta
  por otra vía**), `183` (otra sesión), `181` (la primera cota, 27,8%), `180` (otra sesión),
  `179` (las cuatro clases), `178`, `173`, `172`, `167`, `165`, `151` (DML1 y DML2, y su
  alcance por familia), `159`, `156`, `149`, `140`.
- No se editó `AGENTS.md` ni `OPEN-FRONTIERS.md`, y no se añadió ningún fichero al corpus.

## Nota de método

**Dos caracteres, mil quinientas treinta y cuatro funciones, y ningún síntoma visible.**
*El síntoma que había era pequeño —una función que no aparecía en la lista— y el que había
**sido visible era grande y falso: la poda parecía razonable, `dc/hwss` bajaba de 498 a 91, y
eso parecía una poda agresiva pero razonable en lugar de un patrón roto.*

**La regla que sale de aquí es la más concreta que ha dado este bloque, y es de una línea:
*un caso de prueba se copia del fichero, no del esquema que uno cree que tiene*.** *El
fixture que yo escribí —`x->funcs = &tabla`— habría pasado con uno solo de los dos
defectos arreglado. El que copié de `dce112_resource.c:1243` los cazó los dos, porque en
el fichero real el campo tiene dos niveles y el valor lleva ampersand, y un fixture escrito
desde la idea de lo que hace el código no tiene por qué tener ninguno de los dos.*

**Y hay un segundo resultado de método, y es el que más me ha costado: en `185` la cifra
subió del 27,8% al 33,7% y yo lo presenté como un cierre, cuando el defecto real pesaba más
que la mejora.** *Una cifra que mejora es la más difícil de refutar, porque nadie mira dos
veces un número que va en la dirección que uno quiere. La regla es mirar el número que
empeora con el mismo rigor —`184` lo hizo, y por eso encontró que `dc/hwss` se caía a 91.*

**Y el tercero es el que más generaliza de esta tanda, y es un test de imposibilidad
cruzado entre notas: `185` demostró que DML2 es de DCN, y eso es lo que refuta el 22,0% de
`184`, y no el `dc/dce60` al 33%.** *Un criterio de imposibilidad puesto en una nota sólo
puede juzgar a los números de esa nota; puesto en el estado, puede juzgar a todos.*