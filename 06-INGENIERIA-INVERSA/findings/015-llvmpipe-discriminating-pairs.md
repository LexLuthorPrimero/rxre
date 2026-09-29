# 015 — Q-2: las 649 TRIPLAS discriminantes, reproducidas y verificadas

**Fecha**: 2026-09-29 · **Ámbito**: `06-INGENIERIA-INVERSA/` · **Host**: `HOST-C` (vivo)
**Petición**: IA-2, desde el commit `1e28733`
**Estado**: `CONFIRMADO` el recuento de `1e28733`, con tres correcciones:
el universo son **triplas** y no pares, la aritmética vive en otro
directorio, y **una división en 271/378 que yo mismo propuse era falsa**.

> **Corrección registrada (2026-09-29).** Una versión anterior de este
> documento afirmaba que las 649 se dividían en 271 discriminantes robustos y
> 378 débiles, y que los 378 comparaban «una constante contra un valor
> calculado». **Es falso.** Las 378 caen todas en el código 5, que las tres
> implementaciones interpolan. La división real es por **rama**, no por poder
> probatorio, y las 649 son equivalentes. Ver §«La división falsa» más abajo.

> **Enmienda registrada (2026-09-29, 04:40).** Se traza la ruta estática que
> va del sampler `NEAREST` del árbol de Mesa leído hasta `lp_build_lerpdxta()`,
> en 8 saltos. Eso **eleva** una clasificación de `NOT_DETERMINED` a
> `EVIDENCE` en un eje —la ruta definida por el árbol— y **no cierra** los dos
> que quedan: que el binario instalado venga de ese árbol, y que la ruta sea la
> observada en ejecución. Ver §«Ruta efectiva, por trazado». El documento no
> anticipa el resultado de `RUNTIME_EXECUTION`; sólo evita que un
> `NOT_DETERMINED` demasiado ancho sobreviva a evidencia ya reunida.

> **Segunda enmienda (2026-09-29, 04:58).** El eje *«árbol fuente leído =
> binario instalado»* pasa de `NOT_DETERMINED` a **`SUPPORTED` con salvedad**,
> por la cadena de identidad del binario y la auditoría del intervalo de
> versiones. Ver §«Procedencia del binario». **El eje de ejecución no se
> toca**: `llvmpipe ejecutado` y `modelo ↔ ejecución` siguen
> `NOT_DETERMINED`, y este resultado **no reduce** la necesidad de
> `RUNTIME_EXECUTION`. Queda un solo discriminante.

---

## Qué se pide y qué hay

La tarea era: generar un corpus con los casos donde llvmpipe difiere de
**ambas** referencias (spec `+3/+2` y truncamiento), para que un test pueda
distinguir hardware de llvmpipe.

| | |
|---|---|
| Generador | `06-INGENIERIA-INVERSA/llvmpipe_pairs.py` |
| Corpus materializado | `08-ARQUITECTURA/validations/casos_llvmpipe_unico.json` (commit `5c02833`, IA-3) |
| Conteo verificado | 136 686 / 42 170 / 93 867 / **649** |

El corpus en disco lo escribió IA-3 en `5c02833` e incluye `block_hex` con el
bloque BC3 de 16 bytes ya codificado, que es lo que necesita el test de GPU.
**No se sustituye**: es más completo que lo que este documento produciría, y
su conjunto de 649 casos coincide exactamente con el de aquí, con los mismos
valores esperados (verificado caso a caso, 0 diferencias).

---

## Estado de los artefactos

Cuatro niveles, y no son intercambiables:

```
DISEÑADO      alguien decidió que iva a existir
IMPLEMENTADO  hay código en disco
EJECUTADO     ese código se ha corrido y ha producido salida
VALIDADO      su salida se ha comparado contra algo independiente
```

Un artefacto puede estar en cualquiera de los cuatro. `DISEÑADO` no implica
`IMPLEMENTADO`, y este proyecto se ha olvidado de esa distinción con los dos
artefactos de la sección siguiente.

### Existen y están validados

| Artefacto | Estado | Evidencia |
|---|---|---|
| `compressor/rx550_compress.c` | IMPLEMENTADO · EJECUTADO · VALIDADO | suite `test_compress`: `all checks passed`; introducido en `05c6297`, última modificación `44bc133` |
| `compressor/rx550_compress_avx2.s` | IMPLEMENTADO · EJECUTADO · VALIDADO | 6 instrucciones AVX2 medidas en el `.o`; bit-idéntico a la ruta C en 200 000 bloques |
| `decompressor/decompress_bc3.comp` | IMPLEMENTADO · EJECUTADO EN RX 550 · VALIDADO | `0/16384` discrepancias GPU vs CPU sobre 3 texturas; decisión `F4-AD-12` |
| `llvmpipe_pairs.py` | IMPLEMENTADO · EJECUTADO · VALIDADO | 649 contrastados contra `1e28733`; control negativo `rc=1` |

**El códec completo está implementado y validado.** El compresor es C + ASM
(portable, sin `-mavx2` a propósito, para que el despacho por detección de
CPU sea un mecanismo de seguridad y no un peligro); el descompresor es GLSL
compute, por `F4-AD-12`. La asimetría entre las dos lenguas es deliberada y no
es trabajo pendiente.

### Diseñados y prometidos, pero NO EXISTEN

| Artefacto | Prometido en | Estado real |
|---|---|---|
| `07-DRIVER/tests/test_llvmpipe_discriminator.c` | §«Cómo se valida» de una versión anterior | **NO EXISTE** |
| `07-DRIVER/tests/data/llvmpipe_649.bin` | §«Formato del fixture» de una versión anterior | **NO EXISTE** |

Se dejan escritos aquí, con su nombre exacto, para que no vuelvan a
aparecer citados como si existieran. Tres sesiones han trabajado ya sobre este
proyecto asumiendo que lo descrito en un documento existe; ese es el modo de
fallo que esta sección evita.

**Por qué no se construyen:**

- El clasificador en Python cubre la función que Q-5 necesita (`--ramp A0 A1`
  clasifica una rampa observada). `IMPLEMENTATION_IS_NOT_AUTHORITY`: que una
  versión anterior de este documento prometiera un `.c` no lo convierte en
  requisito.
- El corpus de `5c02833` ya trae `block_hex` con el bloque BC3 listo para
  subir a la GPU. Un fixture binario paralelo sería un segundo formato del
  mismo dato, con el riesgo de desincronizarse del primero.

### Estado de Q-5

**Dos enmiendas el mismo día.** La tabla de abajo no existió en esa forma al
escribir el documento.

- **04:40** — se traza la ruta estática, 8 saltos, del sampler `NEAREST` a
  `lp_build_lerpdxta()`. El eje *ruta efectiva* sube de `NOT_DETERMINED` a
  `EVIDENCE`. Ver §«Ruta efectiva, por trazado».
- **04:58** — el eje *árbol leído = binario instalado* pasa de
  `NOT_DETERMINED` a `SUPPORTED` con salvedad, por la cadena de identidad del
  binario y la auditoría del intervalo de versiones. Ver §«Procedencia del
  binario». Sustituye al `FAIL` por método de `Q-3` (`00f9051`).

**Ningún eje de ejecución se ha tocado.** `llvmpipe ejecutado` y
`modelo ↔ ejecución` siguen `NOT_DETERMINED`, y el segundo hallazgo **no reduce**
la necesidad de `RUNTIME_EXECUTION`. Queda un discriminante, no dos.

| Eje | Estado | Cómo se midió |
|---|---|---|
| Función identificada | **`FACT`** | `lp_bld_format_s3tc.c:817-877`, leído |
| Ruta efectiva para el sampler `NEAREST` | **`EVIDENCE`** | trazado estático, 8 saltos, §«Ruta efectiva» |
| Aritmética de los 649 | **`TEST`** | `q5_validate_llvmpipe.py`, 649/649, control negativo por mutación |
| Árbol fuente leído **=** binario instalado | **`SUPPORTED`** | §«Procedencia del binario», con `LIMITATION` explícita |
| llvmpipe ejecutado | **`NOT_DETERMINED`** | requiere `RUNTIME_EXECUTION` |
| Correspondencia modelo ↔ ejecución | **`NOT_DETERMINED`** | requiere `RUNTIME_EXECUTION` |

La cadena que el documento repite —llvmpipe **usa** `lp_build_lerpdxta` para
BC3— se descompone en tres afirmaciones que antes iban juntas y ahora no:

```
FUNCIÓN EXISTENTE      !=  RUTA DEFINIDA POR EL ÁRBOL LEÍDO
                      !=  RUTA OBSERVADA EN EJECUCIÓN
```

La segunda está establecida por lectura. La tercera, no. Este documento
reproduce **la función que cita `1e28733`**, transcrita del árbol
`26.1-branchpoint-1415-gc5e413533f4`. Lo que añade la enmienda es que la
transcripción **no está huérfana**: hay un camino estático desde el sampler
hasta ella. Lo que no añade es ninguna afirmación sobre ejecución.

### Ruta efectiva, por trazado

Del punto de entrada del sampler a la función transcrita, en el árbol
`26.1-branchpoint-1415-gc5e413533f4`:

```
lp_build_sample_image_nearest()          lp_bld_sample_aos.c:431
  └─ lp_build_sample_fetch_image_nearest()   lp_bld_sample_aos.c:363
       └─ lp_build_fetch_rgba_aos()          lp_bld_format_aos.c:468
            └─ lp_build_fetch_s3tc_rgba_aos()    lp_bld_format_s3tc.c:2175
                 └─ s3tc_dxt5_to_rgba_aos()         :2150
                      └─ s3tc_dxt5_full_to_rgba_aos()  :1032
                           └─ s3tc_dxt5_alpha_channel() :881
                                └─ lp_build_lerpdxta()  :985 -> :817
```

Tres decisiones del trazado que **no** son obvias y que un lector podría dar
por hechas sin comprobarlas:

1. **Es la rama `NEAREST`, no la `LINEAR`.** En `lp_bld_sample_aos.c:963` el
   dispatch es `if (img_filter == PIPE_TEX_FILTER_NEAREST)`. Ese es el filtro
   que exige `F4-AD-28` §3, y por eso el trazado empieza en `NEAREST` y no en
   una ruta intermedia. La rama `LINEAR` pasa por
   `lp_build_sample_fetch_image_linear()` (`:552`) y llega a la misma función,
   pero interpola espacialmente después: usaría la misma aritmética de bloque
   **más** una mezcla de texels vecinos.
2. **El S3TC dispatch está en `lp_build_fetch_rgba_aos`, no en el sampler.**
   `lp_bld_format_aos.c:730`, bajo `format_desc->layout == UTIL_FORMAT_LAYOUT_S3TC`.
   Ese layout cubre **BC3 y BC4**: la función `s3tc_dxt5_*` es la ruta de DX5
   cuando el formato es `BC3_UNORM_BLOCK`, que es el que se mide.
3. **Hay una segunda implementación SOA** —`lp_build_sample_image_nearest()` en
   `lp_bld_sample_soa.c:973`— que **no** pasa por `lp_build_lerpdxta`: su
   `grep` de `s3tc` da una única coincidencia, un comentario. Esa variante
   termina en `lp_build_fetch_rgba_soa()` (`lp_bld_format_soa.c:409`), que a
   su vez **sí** llama a `lp_build_fetch_rgba_aos()` (`:791`, `:854`, `:883`),
   y por tanto reconverge en la misma función de la aritmética. El comentario
   del fuente lo dice: *"Try calling lp_build_fetch_rgba_aos for all pixels.
   Should only really hit subsampled, compressed (for s3tc srgb and rgtc
   too)"*.

**Conclusión limitada a lo que esto establece:**

> El árbol de Mesa inspeccionado contiene una cadena estática que conduce desde
> el sampler `NEAREST` hasta `lp_build_lerpdxta()`. Esto establece evidencia
> sobre la ruta **definida por ese árbol fuente**, pero no demuestra todavía que
> el binario/ICD instalado haya sido compilado a partir de ese árbol ni que esa
> ruta sea la observada durante ejecución.

**Por qué el segundo hueco no lo subsana `RUNTIME_EXECUTION`.** Ejecutar
llvmpipe observa *qué hace*, no *qué código tiene delante*. Las dos
incertidumbres son independientes, y confundirlas haría creer que basta con
ejecutar para resolver la procedencia. Se resuelven por vías distintas:

| Incertidumbre | Se cierra con |
|---|---|
| Qué código hay detrás del binario | cadena RPM + Build-ID + auditoría del intervalo de versiones |
| Qué código se ejecuta | una ejecución observada, `RUNTIME_EXECUTION` |

### Procedencia del binario

Medido el 2026-09-29, por mí. Sustituye al `FAIL` por método de `Q-3`
(`00f9051`): aquel buscado símbolos, y un símbolo no distingue dos revisiones
del mismo fichero fuente. Esto usa la **cadena de identidad** que el
instalador sí escribe.

| Dato | Valor | Cómo se midió |
|---|---|---|
| Paquete | `mesa-libgallium-26.2.3-1.fc44.x86_64` | `rpm -qf` |
| SRPM declarado | `mesa-26.2.3-1.fc44.src.rpm` | `%{SOURCERPM}` |
| sha256 del `.so` | `9725973f873b42751f8c9d9862986dffac51ed8bb47ace13124f298d140e4d1e` | `sha256sum` |
| Build-ID | `40bd61677c87355ec3a60949323dfc2473a56ace` | `file` |
| El enlace Build-ID resuelve a este `.so` | **sí**, y `rpm -qf` sobre el enlace da el paquete | `readlink -f` + `rpm -qf` |
| Árbol analizado | `c5e4135` (`26.1-branchpoint-1415`), 16 mayo 2026 | `git describe` |
| Branchpoint de la serie | `5b20089` (`26.2-branchpoint`), 3 julio 2026 | `git rev-parse` |
| `c5e4135` es ancestro de `26.2-branchpoint` | **sí**, verificado | `git merge-base --is-ancestor` |

**Auditoría del intervalo** `c5e4135..26.2-branchpoint`, sobre la ruta trazada:

| Fichero | Commits | Efecto |
|---|---:|---|
| `lp_bld_format_s3tc.c` | **0** | la aritmética, literalmente intacta |
| `lp_bld_sample_aos.c` | **0** | el sampler `NEAREST`, intacto |
| `lp_bld_format_aos.c` | 1 | `5bb025f953a`, **sólo big-endian** |
| `lp_bld_format_soa.c` | 0 | — |
| `lp_bld_sample_soa.c` | 4 | `min_lod`, sparse residency, filtrado de cube maps. Ninguno toca `lp_build_sample_image_nearest()` |

`5bb025f953a` (*"gallivm: fix small_unorm -> unorm8 fetch path on
big-endian"*) es el único cambio en la zona, y su propio diff lo acota:
`#if UTIL_ARCH_BIG_ENDIAN ... #else ... j * type.width`. Esta máquina es
`x86_64` little-endian, y la rama tocada no es además la de S3TC sino la del
*fast path* `small_unorm`.

**Afirmación que esto sostiene, y su límite exacto:**

> La identidad del commit que produjo el binario **no** está establecida. Pero
> la ruta relevante analizada **no presenta cambios funcionales** entre el árbol
> examinado y el branchpoint de la serie 26.2, salvo un cambio condicionado a
> big-endian que no aplica a esta máquina.

Eso es más fuerte que la igualdad literal, y sobrevive al hueco que no puede
cerrarse: **cualquiera que sea el commit exacto dentro de ese intervalo, el
comportamiento de la ruta es el mismo.** Un argumento así no depende de
identificar el commit.

`LIMITATION` de este eje, explícita:

1. El commit exacto del point release `26.2.3` **no** está identificado. El
   clon no tiene tags de point release: `git tag -l "26.2*"` devuelve sólo
   `26.2-branchpoint`.
2. El SRPM `mesa-26.2.3-1.fc44.src.rpm` **no está en disco**. No se puede
   verificar la cadena de build.
3. **Parches downstream de Fedora no descartados.** Si Fedora aplicó un parche
   a `lp_bld_format_s3tc.c` o a la ruta del sampler, esta auditoría del
   *upstream* no lo ve. Declarado, no descartado.

Por (1)-(3) el eje es `SUPPORTED` **con salvedad**, y la salvedad viaja como
campo aparte, no como categoría nueva: `AGENTS.md` §Evidence vocabulary tiene
una lista cerrada y no incluye ninguna variante de caveat, y el precedente del
repo es el mismo —`PASS_CON_CAVEATS` con la salvedad en el identificador
(`R1-COLLECTOR-INDEPENDENT-REVIEW-20260925.md:199`) y el detalle en campo
`LIMITATION`—. Un token nuevo sería más fácil de citar mal.

**Y esto no reduce la necesidad de `RUNTIME_EXECUTION`.** Ahora sabemos mucho
mejor qué código esperamos detrás del binario; seguimos sin saber, por
observación, que una ejecución concreta de llvmpipe atraviese
`NEAREST → lp_build_fetch_rgba_aos() → lp_build_fetch_s3tc_rgba_aos() →
s3tc_dxt5_* → lp_build_lerpdxta()`. El discriminante que queda **es uno solo**.

### Qué queda pendiente, con precisión

### Qué queda pendiente, con precisión

1. **Q-5**: queda **un** hueco, no dos. Cerrado el de procedencia (§«Procedencia
   del binario»). El que sigue es **ejecución**: demostrar por observación que
   llvmpipe atraviesa la cadena trazada. Eso requiere `RUNTIME_EXECUTION` y
   nada más lo sustituye. Con él cerrado, el clasificador compara contra una
   referencia correcta **y alcanzada**.
2. **AD-12**: el comportamiento real de redondeo o truncamiento del sampler de
   la RX 550. `NOT_DETERMINED`, y es la medición que el corpus de 649 existe
   para interpretar. **No lo adelantaría Q-5 ni aunque su único hueco se
   cerrara**: Q-5 establece la aritmética de un rival de software, AD-12
   pregunta por el hardware. Son dos mediciones sobre dos dispositivos.
3. **El driver exclusivo**: `07-DRIVER/`, que es trabajo de Fase 4 y no de
   este documento.

---

## La aritmética de llvmpipe, transcrita

Fuente: `/home/lucas/mesa/src/gallium/auxiliary/gallivm/lp_bld_format_s3tc.c`,
`lp_build_lerpdxta()`, líneas 817-877. **Nota de ubicación**: `1e28733` la cita
como `lp_bld_format_s3tc.c:817-877`, que es correcto; el directorio es
`src/gallium/auxiliary/gallivm/`, no `src/gallium/drivers/`.

La función no interpola directamente. Trabaja en 16 bits con pesos fijos:

```
weight5 = 255*64/5  =  3264      (truncado)
weight7 = 255*64/7  =  2330      (truncado)
weight  = (a0 > a1) ? weight7 : weight5

code    = code - 1                       # code es el índice i, 2..7
weight  = (weight * code) >> 6
delta   = a1 - a0
ainterp = (delta * weight) >> 8
result  = a0 + ainterp
```

Las tres diferencias respecto a la especificación Microsoft:

| | spec | llvmpipe |
|---|---|---|
| pesos | `(8-i)*a0 + (i-1)*a1 + 3` | `255*64/5` o `255*64/7`, **pretruncados** |
| interpolación | ponderación directa por pesos | `>>6` y `>>8`, dos desplazamientos encadenados |
| signo | `delta` implícito en los pesos | `delta = a1 - a0`, **negativo** cuando `a0 > a1`, y multiplicado por un peso *creciente* |

Ese último punto es la causa de que llvmpipe no sea ni spec ni trunc: con
`delta` negativo y `weight` creciente en `i`, el término `delta*weight` se
**suma** en vez de restar, y el resultado no coincide con ninguna de las dos
referencias en los casos donde los desplazamientos difieren.

---

## El universo: TRIPLAS, no pares

El commit `1e28733` reporta **136 686** casos divergentes. El universo de
**pares** `(a0, a1)` es `256 × 256 = 65 536`. **136 686 no cabe como recuento
de pares.**

Son **triplas** `(a0, a1, code)` con `code ∈ 2..7`: `65 536 × 6 = 393 216`
triplas. Los números del commit reproducen exactamente esa cuenta:

```
$ python3 llvmpipe_pairs.py --classify
  pares  (a0, a1) en 0..255   : 65536
  triples (a0, a1, code) 2..7 : 393216

    spec != trunc  (divergentes)   :  136686
      llvmpipe == spec   (+3/+2)   :   42170   30.85 %
      llvmpipe == trunc  (bcdec)   :   93867   68.67 %
      llvmpipe == NINGUNA          :     649    0.47 %
```

| Categoría | Triplas | % de las divergentes |
|---|---|---|
| `llvmpipe` coincide con spec `+3/+2` | 42 170 | 30.85 |
| `llvmpipe` coincide con truncamiento | 93 867 | 68.67 |
| **`llvmpipe` no coincide con ninguna** | **649** | **0.47** |

**Sobre el denominador de los porcentajes**: el 30.8 % y el 68.6 % de `1e28733`
son correctos *sobre 136 686*. Sobre el total de 393 216 triples serían 10.7 %
y 23.9 %. La cifra absoluta coincide en ambos casos; el denominador no. No es
una discrepancia, es una base distinta, pero quien lea ambos documentos tiene
que saber cuál está usando.

---

## La división falsa: 271 «robustos» y 378 «débiles»

**Se retiró.** Una versión anterior de este proyecto afirmó que las 649 se
dividían en 271 discriminantes de aritmética real y 378 que solo distinguían
por definición de rama, y **`discriminante_por_aritmetica: false`** se
propagó al criterio de pase.

El argumento era: en la rama `a0 <= a1` la spec y el trunc **fijan** los
códigos 6 y 7 a 0 y 255 mientras llvmpipe los interpola, así que comparar ahí
es comparar una constante contra un valor calculado.

**Es falso.** Reparto real de las 649, medido:

| rama | código | casos |
|---|---|---:|
| `a0 <= a1` | 5 | **378** |
| `a0 > a1` | 5 | 50 |
| `a0 > a1` | 7 | 221 |

Los 378 caen **todos en el código 5**, que las tres implementaciones
interpolan. **Ninguna** de las 649 cae en el código 6 ni en el 7 de la rama
`a0 <= a1`, que es donde las tres no serían comparables.

**Las 649 son equivalentes en poder discriminante.** El criterio de pase se
aplica a las 649 sin jerarquía. `branch` y `code` se conservan como metadatos
informativos, no como criterio.

### Cómo se resolvió la duda, y por qué no movía ninguna cifra

La preocupación era legítima: hay que comprobarlo, no suponerlo. Se
implementaron los dos universos y se midieron:

- `TODOS`: compara los códigos 2..7 en ambas ramas.
- `COMUN`: compara solo los códigos que las tres implementaciones definen
  (2..7 si `a0 > a1`; 2..5 si `a0 <= a1`).

**Ambos dan el mismo conjunto de discriminantes**: 0 casos de diferencia en
cualquier dirección. La pregunta era correcta y la respuesta es que no tenía
consecuencia sobre el corpus.

---

## Lo que el corpus demuestra y lo que no

**Las 649 son un discriminante válido, pero no bastan solas.** Un discriminante
necesita que las categorías sean mutuamente excluyentes para la implementación
correcta:

- La spec y `rx550_alpha_palette_for_test()` coinciden en las 136 686 triplas
  divergentes: el codificador de este proyecto sigue la especificación.
- llvmpipe coincide con spec en 42 170 y con trunc en 93 867.

Es decir: **de las 136 686 divergentes, 42 170 NO distinguen llvmpipe de la
spec.** Un corpus construido solo con esas categorías pasaría aunque el
resultado se hubiera computado por software. El valor está en la categoría
`NINGUNA`, y un test debe exigir cobertura de las **tres** categorías, no solo
presencia de bloques.

## Formato del corpus materializado

`08-ARQUITECTURA/validations/casos_llvmpipe_unico.json`, commit `5c02833`
(sha256 `4e9de0a3…`). Cada caso trae:

| Campo | Contenido |
|---|---|
| `a0`, `a1`, `index` | La tripla |
| `branch` | `a0>a1` o `a0<=a1` — metadato informativo |
| `expect_spec`, `expect_trunc`, `expect_llvmpipe` | Los tres valores calculados |
| `block_hex` | El bloque BC3 de 16 bytes ya codificado |
| `pos_texel`, `uv_x`, `uv_y` | Dónde leer el resultado |

**No lleva `discriminante_por_aritmetica`.** Las 649 son equivalentes y el
campo sería un nivel de jerarquía que no corresponde a los datos.

---

## Cómo se valida hoy

`llvmpipe_pairs.py` es a la vez generador y clasificador. Dos modos:

| Comando | Qué hace |
|---|---|
| `--classify` | Recorre las 393 216 triplas, calcula los tres valores de cada una, deduce la categoría por comparación y contrasta el recuento contra `1e28733`. Devuelve `1` si no coincide. |
| `--ramp A0 A1` | Imprime las tres rampas de un par y, código a código, en cuál cae llvmpipe. Es la operación que necesitará Q-5. |

No hay test en C. Una versión anterior de este documento prometía
`07-DRIVER/tests/test_llvmpipe_discriminator.c` y un fixture binario
`llvmpipe_649.bin`; **ninguno de los dos existe**. Se retiran las promesas: un
documento que describe entregables no escritos induce a crearlos.

El clasificador en Python cubre la función que Q-5 necesita, así que no hay
razón metodológica para escribir otro en C.

### Control negativo, ejecutado

Que el contraste con `1e28733` no sea una tautología se comprueba rompiendo la
fórmula y viendo que el script lo nota:

```
$ sed -i 's/(delta \* w) >> 8/(delta * w) >> 7/' llvmpipe_pairs.py
$ python3 llvmpipe_pairs.py --classify
    calculado   136686   1269   1272 134145
    commit     136686  42170  93867   649   NO COINCIDE
$ echo $?
1
```

Un `>>7` en lugar de `>>8` es una desviación de un bit en la aritmética de
llvmpipe. El recuento pasa de 649 a 134 145 y el proceso falla.

**Y por qué ya no hay un `EXPECTED` con cifras inventadas.** La versión
anterior tenía:

```python
EXPECTED = {UNIVERSE_TODOS: (136686, 42170, 93867, 649),
            UNIVERSE_COMUN: (136686, 42170, 41817, 271)}   # fila inventada
```

La fila de `COMUN` la escribí al ver mi propia salida, y el script no se quejó
porque la acumulación de discriminantes no comprobaba el universo. Era una
comparación consigo mismo. Ahora el único número que este proyecto no produce
es el 649 de `1e28733`, una derivación independiente sobre el mismo árbol; que
las dos coincidan sí es evidencia.

---

## Falsificación

Este trabajo se refutaría con:

1. La transcripción de `lp_build_lerpdxa` no coincide con el C de Mesa para
   alguna tripla. El recuento coincidiría por casualidad — improbable con
   393 216 casos, pero es la comprobación que corresponde.
2. `lp_build_lerpdxta` no es la función que llvmpipe usa realmente para BC3 en
   esta versión de Mesa. **Parcialmente cerrado, y el resto `NOT_DETERMINED`.**
   El commit `1e28733` cita la función; este trabajo reproduce la función
   citada **y ha trazado que el sampler `NEAREST` del árbol leído llega hasta
   ella** (8 saltos, §«Ruta efectiva»). Lo que queda abierto es doble: que el
   binario instalado venga de este árbol, y que la ruta sea la observada en
   ejecución. Un trazado estático no puede cerrar ninguno de los dos, y
   presentarlos como cerrados sería el error inverso al que este documento
   corrige.
3. El corpus de `5c02833` y la clasificación de este generador no coinciden.
   **Verificado: coinciden.** 649 casos, mismo conjunto, mismos valores
   esperados, 0 diferencias.

## Procedencia

- Árbol Mesa: `/home/lucas/mesa`, `26.1-branchpoint-1415-gc5e413533f4`
- Fuente de la aritmética: `src/gallium/auxiliary/gallivm/lp_bld_format_s3tc.c:817-877`
- Recuento original: commit `1e28733` (IA-3)
- Generador y clasificador: `06-INGENIERIA-INVERSA/llvmpipe_pairs.py`, commit `75e6b85`
- Validación de la aritmética: `06-INGENIERIA-INVERSA/corpus/q5_validate_llvmpipe.py`, commit `d07aaac` — 649/649, con control negativo por mutación
- Cadena `NEAREST` → `lp_build_lerpdxta`: trazada por mí el 2026-09-29, 8 saltos, todos por lectura. Ficheros citados: `lp_bld_sample_aos.c:363,431,963` · `lp_bld_format_aos.c:468,730` · `lp_bld_format_s3tc.c:881,985,1032,2150,2175`. **Grado**: `EVIDENCE` sobre el árbol leído, no sobre el binario
- `Q-3` (binario instalado = árbol leído): `FAIL` por método, commit `00f9051`. **Sustituido** por §«Procedencia del binario», que usa la cadena RPM + Build-ID + auditoría del intervalo en vez de símbolos
- Paquete del `.so`: `mesa-libgallium-26.2.3-1.fc44.x86_64`, sha256 `9725973f…4e1e`, Build-ID `40bd6167…6ace`. Medido por mí con `rpm -qf`, `sha256sum`, `file`, `readlink -f`
- Intervalo auditado: `c5e4135..26.2-branchpoint` en `src/gallium/auxiliary/gallivm/`. 0 commits en `lp_bld_format_s3tc.c` y `lp_bld_sample_aos.c`; 1 en `lp_bld_format_aos.c` (`5bb025f953a`, big-endian); 4 en `lp_bld_sample_soa.c` (min_lod, sparse, cube). Medido con `git log --oneline c5e4135..26.2-branchpoint -- <fichero>`
- Corpus materializado: `08-ARQUITECTURA/validations/casos_llvmpipe_unico.json`, commit `5c02833` (IA-3), sha256 `4e9de0a3…`
