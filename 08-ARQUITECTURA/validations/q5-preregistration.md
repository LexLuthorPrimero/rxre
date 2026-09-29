# Q-5 — Pre-registro: qué decidirá el resultado, ANTES de ejecutarlo

**Ámbito**: `08-ARQUITECTURA/` — IA-3 (Arquitecto)
**Fecha**: 2026-09-29 · **Ronda**: 12
**Estado**: `PREREG` — escrito **antes** de ejecutar. Se commitea antes del resultado.
**Autorización**: Safety aprobada para `Q-5` (ejecución de cliente Vulkan sobre `10005:0000`).
**Trazabilidad**: `F4-AD-28` §4 tabla de dependencias; petición `Q-5` de
`006-p9-hardware-vs-software.md` §10 y `README-corpus-discriminante.md` §8.

---

## 1. Qué pregunta intenta resolver `Q-5`

**No** es «¿decodifica llvmpipe BC3?». Eso ya se sabe por lectura del fuente.

La pregunta es:

> **¿El modelo Python de `lp_build_lerpdxta` que produce los `expect_llvmpipe` de los 649 casos
> predice lo que llvmpipe REAL devuelve?**

El modelo es una **reimplementación** (`/tmp/opencode/lp_final.py`), no una ejecución. Si está
mal, los 649 casos del corpus tienen los valores esperados equivocados y el test de Fase 3
compararía la RX 550 contra un modelo defectuoso — **con apariencia de funcionar**. Ese es el
escenario de falso `PASS` que `Q-5` existe para cerrar.

## 2. Predicción concreta del modelo

Para cada par de endpoints `(a0, a1)` y cada índice `i ∈ 2..7`, el modelo predice un valor de
alfa de 8 bits según (`lp_bld_format_s3tc.c:817-877`, transcrito con los tipos del fuente,
incluido el wrap de i16):

```
weight5 = 16320/5 = 3264          weight7 = 16320/7 = 2331
weight  = (a0 > a1) ? weight7 : weight5
w       = (weight * (i-1)) >> 6          # 16 bits, desplazamiento LÓGICO
d       = a1 - a0                        # i16 con signo
t       = ((d * w) en i16) >> 8          # con wrap de 16 bits
result  = a0 + (t & 0xff)                # i8, con wrap
if a0 <= a1 and i == 6: result = 0
if a0 <= a1 and i == 7: result = 255
```

**Invariantes que el modelo afirma** (predicciones comprobables, no descriptivas):

| # | Invariante |
|---|---|
| I-1 | `i=0` → exactamente `a0`; `i=1` → exactamente `a1`, para los 65 536 pares |
| I-2 | `i=6` → `0` y `i=7` → `255` cuando `a0 <= a1`, para los 32 896 pares de esa rama |
| I-3 | El resultado es **independiente del color**: los bloques del corpus son de color negro, y el canal alfa no debe verse afectado |
| I-4 | `a0 == a1` produce rampa de 6 valores (`a1-a0 == 0` ⇒ `t == 0` ⇒ `a0 + 0`) |
| I-5 | Los 649 casos del corpus: `llvmpipe ≠ spec` y `llvmpipe ≠ trunc` **y** `spec ≠ trunc` |

## 3. Qué observación de llvmpipe podría falsarlo o confirmarlo

**Observación falsadora**: un solo par `(a0, a1, i)` donde el valor leído de llvmpipe difiera del
`expect_llvmpipe` del modelo. Con barrido **exhaustivo** sobre los 65 536 pares de endpoints ×
8 índices = **524 288** observaciones de alfa, una discrepancia es una discrepancia.

**Observación confirmadora**: coincidencia en las 524 288. No es una muestra: es el dominio
completo de la entrada del decodificador de alfa BC3. Ningún otro par puede existir.

**Por qué barrido exhaustivo y no los 649** — **CORREGIDO, ver enmienda 2.**

La redacción original de este párrafo decía que los 649 son *«un subconjunto
seleccionado por la predicción del modelo»* y que validar el modelo sobre ellos
es *«comparar el modelo consigo mismo»*. **La primera afirmación es falsa.**

La pertenencia al corpus no la decide el modelo de llvmpipe. Un caso entra si
**las tres** implementaciones difieren entre sí:

```
llvmpipe ≠ spec   ∧   llvmpipe ≠ trunc   ∧   spec ≠ trunc
```

Son tres condiciones, y el modelo participa en una sola. La selección no es un
subconjunto de los aciertos del modelo, sino el conjunto de los desacuerdos
entre tres implementaciones.

**Lo que sí era cierto, y sigue siendo la razón del barrido completo**: el
subconjunto es ciego a una clase concreta de error. Medido: ningún caso de los
649 cae donde `lp_build_lerpdxta()` y su caller `s3tc_dxt5_alpha_channel()`
difieren — ni en los códigos 0 y 1, ni en el 6/7 de la rama `a0 <= a1`. Un
modelo que omitiera el caller entero pasaría los 649 sin una sola discrepancia.
El barrido de las 524 288 no es ciego a eso.

**El criterio no cambia.** `PASS`/`FAIL` se sigue decidiendo sobre las 524 288.
Lo que cambia es el motivo, y el motivo corregido es más fuerte: el 649 es
insuficiente por ciegas, no por circular.

**Medido sobre el barrido completo** (enmienda 2): el conjunto de 649
discriminantes que produce es **idéntico** al del JSON de `5c02833` — 0 casos
sólo en uno, 0 sólo en el otro.

## 4. Criterio `PASS` / `FAIL` / `UNKNOWN` — fijado ANTES de ejecutar

| Resultado | Estado `Q-5` |
|---|---|
| Las **524 288** observaciones coinciden con el modelo, y el control negativo (§6) falla como debe | **`PASS`** |
| ≥1 discrepancia | **`FAIL`** — con el par `(a0, a1, i)`, el valor del modelo y el observado, y la causa determinada antes de tocar nada |
| No se puede ejecutar (compilación, ICD, formato, lectura) | **`NOT_DETERMINED`** — con el punto exacto del fallo |

**`UNKNOWN` no se usa como comodín.** Si el barrido corre y produce números, el resultado es
`PASS` o `FAIL`. La única fuente de `NOT_DETERMINED` es no poder obtener la observación.

## 5. Separación de clases — qué NO se concludes aunque el resultado sea `PASS`

Un `PASS` de `Q-5` establece **una sola** cosa: que mi transcripción de la aritmética coincide
con lo que lavapipe/llvmpipe devuelve en esta host, con este binario, en estos 524 288 casos.

| No establece | Por qué |
|---|---|
| Que `radeonsi` no tiene descompresor BC3 en CPU | `Q-3` es `FAIL` por método (`F4-AD-28` §4.1) y **no se reabre**. `Q-5` corre sobre llvmpipe, no sobre radeonsi |
| La respuesta de `AD-12` | `Q-5` no toca la RX 550. `AD-12` sigue `NOT_DETERMINED` |
| Que la RX 550 se comporte como el modelo | El modelo predice **llvmpipe**. Sobre hardware sólo sirve como referencia de *contaminación* |
| Que `lp_build_lerpdxta` sea la ruta efectiva del hardware | Es la ruta de llvmpipe. El hardware tiene texture unit |
| Que el árbol de Mesa leído sea el del binario | `Q-3` cerrado como método. Aquí comparo modelo contra **comportamiento**, que no necesita identificar el árbol |

## 6. Control negativo obligatorio — el test debe poder fallar

Un test que solo compara modelo contra llvmpipe y sale `0/524 288` no prueba nada si su
comparación está mal escrita. Antes de aceptar `PASS` hay que demostrar que la comparación
**detecta** una diferencia.

**Dos controles negativos, fijados aquí:**

| # | Control | Resultado exigido |
|---|---|---|
| `C-1` | Introducir un cambio de ±1 en un subconjunto del modelo y recomparar | el recuento de discrepancias debe ser **> 0**, y debe emitir los pares concretos |
| `C-2` | Sustituir el modelo por un predictor equivocado conocido (spec) | **524 288** discrepancias, no menos |

Si `C-1` o `C-2` no se comportan así, el harness de comparación está mal y el `PASS` no vale,
aunque las cifras den 0.

## 7. Posibles `MODEL_CHOICE` que NO serían error del oracle

Antes de declarar `FAIL`, hay que descartar que la discrepancia venga de una decisión de diseño
mía y no de un error de transcripción:

| # | `MODEL_CHOICE` | Cómo se distingue de un error |
|---|---|---|
| `M-1` | El barrido usa **`NEAREST`** | Con `LINEAR` el sampler interpola entre texels y mezcla la aritmética espacial. Si el resultado se parece a `spec` y no a `llvmpipe`, sospecho de esto |
| `M-2` | El barrido usa `VK_FORMAT_BC3_UNORM_BLOCK` (**UNORM**, no SRGB) | SRGB aplica una transformación que arruinaría la comparación |
| `M-3` | La imagen usa `VK_IMAGE_TILING_OPTIMAL` | LINEAR no tiene `SAMPLED_IMAGE` para BC3 en este host (`004` §5.6) |
| `M-4` | El canal leído es el **alfa** (byte 3 de RGBA8) | Leer el rojo daría 0 siempre, y todo «coincidiría» |
| `M-5` | El color se fuerza a negro y los índices de color a 0 | Si el color no fuera negro, el rojo sería ruido; el alfa no debería cambiar (`I-3`) |
| `M-6` | lavapipe (`libvulkan_lvp.so`) comparte `lp_bld_format_s3tc.c` con llvmpipe (GL) | Si no lo compartiera, el resultado sería coherente con lavapipe pero no con llvmpipe-GL. Sería un `LIMITATION`, no un `FAIL` del modelo |
| `M-7` | La orientación vertical: Vulkan tiene origen arriba-izquierda, OpenGL abajo-izquierda | Un flip vertical no cambia los valores de alfa por par, pero sí **qué par** cae en cada posición. Se detecta comparando la rampa completa de un bloque, no un solo texel |

### Enmienda 2 — `M-8`: el modelo debe incluir el caller, no sólo la subfunción

**Añadido por IA-1, 2026-09-29, tras medir la predicción exhaustiva.** No
sustituye a `M-1`..`M-7`; es de otra clase: no es una decisión de diseño del
experimento, es un requisito de transcripción fiel.

Yo levanté la hipótesis contraria —que el clamp de `i=6/7` de §2 no existía en
llvmpipe— y **era falsa**. Fui a la fuente:

```
lp_bld_format_s3tc.c:1000-1016, s3tc_dxt5_alpha_channel()

    alpha  = (alphac == 0) ? alpha0 : alpha1;    <- códigos 0 y 1
    alpha  = (alphac >  1) ? ainterp : alpha;    <- el resto
    code_s = alphac & ~sel_mask;                 <- ~0 cuando a0 <= a1
    alpha  = alpha & ~mask6;                     <- código 6 -> 0
    alpha  = alpha |  mask7;                     <- código 7 -> todos los 1
    alpha  = alpha & 0xff;                       <- 0xff == 255
```

**§2 de este documento es correcto.** El clamp existe, y sólo se aplica cuando
`a0 <= a1`, porque `code_s = alphac & ~sel_mask` se anula en la rama `a0 > a1`.

Lo que faltaba era la otra mitad: **`lp_build_lerpdxta()` no pone los códigos 0
ni 1.** Interpola y devuelve; quien pone `a0` y `a1` es el caller. Un modelo que
transcriba sólo la subfunción —como hice yo en el primer intento— predice basura
en `i=0` e `i=1`, y eso lo delata `I-1` de inmediato.

| # | `MODEL_CHOICE` | Cómo se distingue de un error |
|---|---|---|
| `M-8` | El modelo debe ser **`s3tc_dxt5_alpha_channel()` completo**: la interpolación de `lp_build_lerpdxta()` **más** la selección de `i=0`/`i=1` y el recorte de `i=6`/`i=7` de la rama `a0 <= a1` | Si `I-1` no se cumple en las 131 072 observaciones, el modelo no incluye el caller. Es el fallo más probable, y el único que los 649 **no** detectarían |

**Por qué `M-8` no estaba en la lista original**: los 649 son ciegos a esta clase
de error, por construcción. Ninguno trae `i=0` ni `i=1`, y ninguno trae `i=6` ni
`i=7` en la rama `a0 <= a1`. Un modelo sin caller pasa los 649 con 0/649
discrepancias. El barrido de las 524 288 no es ciego, y por eso `I-1` e `I-2` son
lo primero que hay que mirar si el resultado fuese `FAIL`.

**Regla**: si la discrepancia se explica por un `MODEL_CHOICE` de esta tabla, se corrige el
**modelo del experimento** y se vuelve a ejecutar. **No se modifica el `expect_llvmpipe` del
corpus** para que coincida con lo observado — eso sería ajustar el resultado esperado al
resultado obtenido, que es el patrón que este proyecto ya ha pagado dos veces.

## 8. Procedimiento y captura

| Paso | Acción | Evidencia a conservar |
|---|---|---|
| 1 | Compilar el harness Vulkan en `/tmp/opencode/q5/` (**fuera** del repo: no es ámbito de código de ninguna IA) | comando, `gcc -v`, warnings |
| 2 | Compilar el fragment shader con `glslangValidator` | comando, versión |
| 3 | Ejecutar sobre `10005:0000` con filtrado por PCI identity | salida completa, `deviceName` |
| 4 | Volcar las 524 288 observaciones de alfa a fichero binario | sha256 del volcado |
| 5 | Comparar con el modelo Python | recuento de discrepancias, primeros pares |
| 6 | Ejecutar `C-1` y `C-2` | recuentos, confirmando que el harness discrimina |
| 7 | Emitir estado | este documento + `F4-AD-28` §4 |

**Harness fuera del repo, evidencia dentro.** `06-INGENIERIA-INVERSA/` y `04-IMPLEMENTACION/`
no se tocan. El harness no es el probe de Fase 3 — es la validación del oracle — y no se versiona
como código de otra IA.

---

## Enmienda 1 — Predicción exhaustiva registrada ANTES de ejecutar

**IA-1, 2026-09-29. CPU pura: no se ejecutó llvmpipe, no se abrió Vulkan, no se tocó la RX 550.
El criterio `PASS`/`FAIL` de §4 NO se modifica.**

El objetivo era gastar la autorización sólo si la predicción ya es correcta. Resultado:

| Medida | Valor |
|---|---|
| Observaciones generadas | **524 288** (coincide con §3) |
| Discrepancias contra una referencia en C con los tipos reales (`int16_t`/`uint16_t`, wrap explícito, desplazamiento lógico) | **0 de 524 288** |
| `I-1` (`i=0 → a0`, `i=1 → a1`) | **131 072 de 131 072** |
| `I-2` (`a0 <= a1`: `i=6 → 0`, `i=7 → 255`) | **65 792 de 65 792** |
| sha256 del volcado de la predicción | `2435189d8e1e7284bbc3da1fc44b2d82bc1b86f832e0cbc7eab28e62b14d0845` |

Reparto por categoría del barrido completo:

| | |
|---|---:|
| las tres coinciden (no informa) | 387 602 |
| sólo coincide con spec | 42 170 |
| sólo coincide con trunc | 93 867 |
| **sólo coincide con llvmpipe** | **649** |

**El conjunto de 649 discriminantes que produce el barrido es idéntico al del
JSON de `5c02833`**: 0 casos sólo en uno, 0 sólo en el otro. Y los 649
`expect_llvmpipe` del JSON los reproduce esta predicción sin una sola excepción.

Controles negativos del cotejo, exigidos por §6 antes de aceptar un `PASS`:

| Control | Resultado |
|---|---|
| 100 observaciones mutadas +1 | **100** discrepancias detectadas |
| Sustitución del modelo por spec (equivalente a `C-2`) | **141 016** discrepancias detectadas |

**Artefactos**: `06-INGENIERIA-INVERSA/corpus/q5_predict_full.py` (predicción) y
`06-INGENIERIA-INVERSA/corpus/q5_ref_c.c` (referencia en C), commit `0e19a2f`.

**Sobre la referencia en C, y por qué el primer intento no valía nada.**
La escribí implementando sólo `lp_build_lerpdxta()`, igual que mi modelo en
Python, y por eso **coincidieron en las 524 288**. Eso no era un control: eran
dos transcripciones del mismo texto, con el mismo error, comprobándose entre sí.
Corregidas ambas a `s3tc_dxt5_alpha_channel()` completo, la coincidencia de 0
discrepancias sí significa algo: son dos representaciones del mismo tipo de
dato, `int16_t`/`uint16_t` frente a la aritmética emulada con `& 0xFFFF`, y la
capa del caller está en una y no en la otra.

Ésta es la razón de que el barrido exhaustivo sea el criterio correcto y no una
formalidad: es el único que obliga a transcribir la función **completa**, porque
es el único que incluye `i=0` e `i=1`.
