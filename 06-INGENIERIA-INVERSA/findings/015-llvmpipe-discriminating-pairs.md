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
2. `lp_build_lerpdxa` no es la función que llvmpipe usa realmente para BC3 en
   esta versión de Mesa. **`NOT_DETERMINED`.** El commit `1e28733` cita la
   función; este trabajo reproduce la función citada. Que sea la ruta efectiva
   en ejecución solo lo dirá Q-5.
3. El corpus de `5c02833` y la clasificación de este generador no coinciden.
   **Verificado: coinciden.** 649 casos, mismo conjunto, mismos valores
   esperados, 0 diferencias.

## Procedencia

- Árbol Mesa: `/home/lucas/mesa`, `26.1-branchpoint-1415-gc5e413533f4`
- Fuente de la aritmética: `src/gallium/auxiliary/gallivm/lp_bld_format_s3tc.c:817-877`
- Recuento original: commit `1e28733` (IA-3)
- Generador y clasificador: `06-INGENIERIA-INVERSA/llvmpipe_pairs.py`, commit `75e6b85`
- Corpus materializado: `08-ARQUITECTURA/validations/casos_llvmpipe_unico.json`, commit `5c02833` (IA-3), sha256 `4e9de0a3…`
