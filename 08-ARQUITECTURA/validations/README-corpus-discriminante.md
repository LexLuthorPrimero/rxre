# Corpus discriminante llvmpipe — especificación para IA-2

**Ámbito**: `08-ARQUITECTURA/` — IA-3 (Arquitecto)
**Fecha**: 2026-09-29 · **Ronda**: 9
**Resuelve**: peticiones `Q-2` y el requisito `F6`/`F7` de `003-fase3-pipeline-grafico.md` §7
**Destinatario**: `@IA-2` (implementación del probe de Fase 3)
**Clasificación**: `DOCUMENTATION` + artefacto de datos. No he ejecutado nada en la GPU.

---

## 1. Artefacto

```
casos_llvmpipe_unico.json
649 casos, 185 047 bytes
sha256  4e9de0a3f8d84ac2ce0f334539d4325da4cc9fb3aefaadeffdc6cff13e7d7d24
```

Verificado tras escribir: JSON parseable, 649 entradas, sha256 recalculado sobre el fichero en
su ruta final.

## 2. Qué contiene y por qué

**649 triplas `(a0, a1, i)`** — no 649 pares de endpoints. En cada tripla, el alfa que devuelve
`llvmpipe` difiere **a la vez** del redondeo de la especificación Microsoft y del truncamiento de
`bcdec`. Ese es el requisito de construcción:

```
spec(a0,a1,i)  !=  trunc(a0,a1,i)   y   llvmpipe(a0,a1,i) != spec   y   != trunc
```

Un caso donde solo difieren dos de los tres no discrimina nada: el hardware real podría coincidir
con cualquiera de los dos. Aquí las tres respuestas son **distintas**, así que la categoría en la
que cae el resultado identifica el origen.

### 2.1 Distribución — y por qué importa para el diseño

| Rama | Índice `i` | Triplas | `llvmpipe` vs `spec` | Distancia |
|---|---|---|---|---|
| `a0 <= a1` | 5 | 378 | **menor** | exactamente **2** |
| `a0 > a1` | 5 | 50 | **mayor** | exactamente **1** |
| `a0 > a1` | 7 | 221 | **mayor** | exactamente **1** |
| | | **649** | | |

**Los índices discriminantes son solo `i=5` e `i=7`.** Ningún otro índice produce un caso donde
llvmpipe difiera de ambos. Es una consecuencia de la aritmética: los pesos fijos de llvmpipe
(`255*64/5` y `255*64/7`) sólo divergen de la fórmula de la especificación en el tramo alto de
cada rampa.

**Concentración fuerte**: 221 de las 649 triplas provienen de una sola diferencia de endpoints
`a0 - a1 = 209`. Otras 378 siguen el patrón `a0 = 0`, `a1 = 197 + 5k`. El conjunto está muy
agrupado y **no** es una muestra representativa del espacio de endpoints. Es correcto para lo que
se busca — un discriminante — y **no** lo usaría para caracterizar la rampa en general. Para eso
sigue mandando el corpus de 64 bloques de `003` §2.

## 3. Formato del bloque BC3

Cada caso trae el bloque listo en `block_hex`, 16 bytes:

```
offset  0..1    a0, a1                       (2 bytes, big-endian)
offset  2..7    índices de ALFA              (6 bytes = 48 bits, 3 bits por texel, LSB primero)
offset  8..15   nada                         (16 bytes de bloque: color forzado a negro)
```

**El color es un control, no un dato.** `c0 = c1 = 0` y todos los índices de color en 0, así que
los canales RGB deben salir exactamente 0 al muestrear. Es el control `S5` de `003` §5.1. Si el
RGB sale distinto de 0, el corpus no es el que crees — y es un fallo del camino de medición, no
un hallazgo sobre la rampa.

**Los índices de alfa no se distribuyen de forma uniforme.** El índice `i` de la tripla se coloca
**únicamente** en la posición `p` del bloque donde `p % 8 == i`; las otras 15 posiciones llevan
índice 0. Como hay 16 texels y solo 8 códigos, cada código aparece exactamente dos veces, pero en
este bloque el código `i` aparece **2 veces** y el 0 aparece **14**.

Esto es intencionado y es la dependencia que la recepción de esta ronda señaló:

> Un corpus que suba los bloques sin codificar el índice no cubre nada.

Los bloques de `block_hex` ya vienen con los índices puestos. **No los regeneres** salvo que
verifiques que sabes hacerlo.

### 3.1 Verificación hecha por mí sobre los 649 bloques

| Comprobación | Resultado |
|---|---|
| `block[0] == a0` y `block[1] == a1` | 649/649 |
| `block[8..15] == 0` (color negro) | 649/649 |
| Los 8 códigos de alfa decodifican a `[i en p%8==i, 0 en el resto]` | 649/649 |
| El código `i` aparece en la posición `p = i` | 649/649 |
| Las posiciones `p=0` y `p=1` llevan índice 0 (control de endpoints `S6`) | 649/649 |
| `uv` del texel `p`: `x = p % 4`, `y = p / 4` | 649/649 |

## 4. Requisitos al subirlo a la GPU

| # | Requisito | Fuente |
|---|---|---|
| 1 | `VK_FORMAT_BC3_UNORM_BLOCK` (137), nunca `BC3_SRGB` (138) | `004` §3.3 |
| 2 | **`VK_IMAGE_TILING_OPTIMAL`** — obligatorio | `004` §5.6, medición propia |
| 3 | Filtrar por `vendorID == 0x1002 && deviceID == 0x699f`, **abortar** si no aparece | `F4-AD-23` |
| 4 | `VK_IMAGE_USAGE_SAMPLED_BIT \| VK_IMAGE_USAGE_TRANSFER_DST_BIT` | `003` §3 |
| 5 | **`VK_FILTER_NEAREST`**, no `LINEAR` | `F4-AD-28` §3 |
| 6 | El predictor llvmpipe usa `weight7 = 2331`, **con** el `>> 6` | §4.0 |

### 4.0 Sobre `Q-5` — el valor dudoso de mi modelo, y por qué no cambia nada

Revisando el trabajo de IA-1 (`015`, sin commitear al momento de escribir esto) encontré que su
transcripción usa `weight7 = 255*64/7 = 2330`. El valor entero correcto es **2331**
(`16320/7 = 2331`, resto 3).

Lo comprobé porque el número parecía erróneo, y la respuesta es que no lo es. `weight7` se consume
siempre como `(weight7 * (code-1)) >> 6`, y para todo `i` de 2 a 7 los dos valores dan el mismo
peso tras el desplazamiento:

| `i` | `2331*(i-1)>>6` | `2330*(i-1)>>6` |
|---|---|---|
| 2 | 36 | 36 |
| 5 | 145 | 145 |
| 7 | 218 | 218 |

Verificado sobre las **195 840** triplas de la rama `a0 > a1` — las únicas donde `weight7` se usa,
porque en la rama `a0 <= a1` se usa `weight5`: **0** cambian de resultado. El desplazamiento de
6 bits absorbe la diferencia de 1.

**Por qué lo declaro entonces**: el `expect_llvmpipe` de cada uno de los 649 casos de este JSON
usa `2331`. Si alguien reimplementa el predictor con `2330` y **omite** el `>> 6`, o lo aplica en
otro orden, los resultados no coincidirán y la comparación de `Q-5` fallará por una razón que no
es la que se busca. La constante correcta es `2331`.

Registrado también en `F4-AD-28` §5. **No he corregido `015`**: es ámbito de IA-1.

### 4.1 Por qué `NEAREST` y no `LINEAR`

`SAMPLED_IMAGE_FILTER_LINEAR_BIT` está presente en `0xd401`, así que `LINEAR` sería **legal** — y
por eso el fallo sería silencioso. Con filtrado lineal el sampler **además** de decodificar el
bloque interpola espacialmente entre texels vecinos. Eso destruye el aislamiento del índice `i` en
la posición `p`, y es exactamente la aritmética que `AD-12` no quiere medir.

`003` §3 especificaba `LINEAR` sin justificarlo. `NEAREST` aísla la decodificación del bloque.
Este requisito quedó formalizado en `F4-AD-28` §3.

## 5. Criterio de pase — y una corrección importante

> **NO apliques el criterio que circuló en la recepción de esta ronda**, que decía que las 649
> «deben caer en *Coincide con spec* (asumiendo que Polaris 12 sigue la spec Microsoft)».

Ese criterio **planetaría la respuesta de `AD-12` en el test**. Si el Polaris 12 trunca — que es
una de las dos respuestas posibles de `AD-12`, y la que `bcdec` sugiere — las 649 caerían
correctamente en *trunc* y el test lo reportaría como **fallo de un hardware que funciona bien**.
El criterio es incorrecto.

### 5.1 Criterio correcto

| Resultado en las 649 | Interpretación | Acción |
|---|---|---|
| **todas en `spec`, ninguna en `llvmpipe`** | hardware, redondeo | `AD-12` → redondeo. `rc=0` |
| **todas en `trunc`, ninguna en `llvmpipe`** | hardware, truncamiento | `AD-12` → truncamiento. `rc=1` |
| **cualquier caso en `llvmpipe`** | contaminación por software | `CONTAMINATED_LLVMPIPE`. `rc=3`. **No es un hallazgo sobre el hardware** |
| **repartidas entre spec y trunc** | regla mixta, no ninguna de las dos | `NOT_DETERMINED`. Se reporta, no se fuerza veredicto. `rc=2` |
| **ninguna coincide con ninguna de las tres** | regla distinta | `NOT_DETERMINED`. `rc=2` |

**La regla que decide el paso**: uniforme en `spec` **o** uniforme en `trunc`, y **cero** casos en
`llvmpipe`. El discriminante es independiente de cuál de las dos sea — por construcción del
conjunto, las tres respuestas son distintas en las 649, así que el hardware real **no puede**
caer en la categoría de software.

### 5.2 Por qué el criterio no depende de `AD-12`

```
si el hardware redondea  ->  649/649 caen en spec
si el hardware trunca    ->  649/649 caen en trunc
si fuera software        ->  649/649 caen en llvmpipe
```

Las tres ramas son excluyentes. La medición de `AD-12` es la **consecuencia** del resultado del
test, no su premisa. Invertir eso — como hace el criterio circulado — convierte una pregunta
abierta en un test que solo puede Confirmar una de las dos respuestas.

## 6. Breakdown que debe reportar el test

Cuatro categorías, con conteos, más el residuo:

```
=== VALIDACION DE LA MEDICION ===
  endpoints a0/a1 correctos   : N / N        (control S6; si falla -> rc=3)
  color de control RGB        : 0 no nulos   (control S5; si no -> revisar alineacion)
  observaciones totales       : N

=== CLASIFICACION (649 casos discriminantes) ===
  solo coincide con REDONDEO (+3/+2)  : n
  solo coincide con TRUNCAMIENTO       : n
  solo coincide con LLVMPIPE           : n      <- debe ser 0
  reparto spec/trunc mixto             : n      <- debe ser 0
  ninguno de los tres                  : n      <- debe ser 0

=== VEREDICTO ===
```

Y `rc` según §5.1. **El test debe devolver código distinto de cero ante fallo** — es el fallo ya
medido en este proyecto (`F4-AD-7` §2: un test que imprimía `[FAIL]` por `stderr` devolvía
`rc=0` y un CI reportaba verde). Comprobación `V-G` de `004` §4.

## 7. Lo que este corpus NO hace

- **No sustituye al corpus de 64 bloques.** Ese cubre ambas ramas con densidad y mide la rampa
  completa. Este solo discrimina software de hardware en 649 puntos. Los dos se necesitan; este
  no puede caracterizar la rampa (§2.1).
- **No cubre los índices 2, 3, 4 y 6.** No hay triplas discriminantes ahí. Si el sampler tuviera
  un defecto **solo** en esos índices, este corpus no lo detectaría. Para eso sigue mandando el
  corpus de 64 bloques.
- **No establece que llvmpipe sea la única implementación por software posible.** `radeonsi` y
  `RADV` no tienen descompresor BC3 en CPU (`F4-AD-27`), así que el único rival posible en este
  host es llvmpipe. Un driver distinto en otro host tendría otra aritmética.
- **No ejecuté nada.** No sé qué responderá la RX 550. `AD-12` sigue `NOT_DETERMINED`.

## 8. Procedencia — según `F4-AD-24` / `F4-AD-26`

| Dato | Grado | Fuente |
|---|---|---|
| Las 649 triplas y sus 3 valores esperados por tripla | **medido por mí** | Python en `/tmp/opencode/lp_final.py`, modelo de `lp_build_lerpdxta` con los tipos del fuente |
| `lp_build_lerpdxta` está en `lp_bld_format_s3tc.c:817-877` | **medido por mí** | lectura directa, `/home/lucas/mesa` |
| `s3tc_dxt5_alpha_channel` está en `:881-1020` | **medido por mí** | lectura directa |
| Árbol Mesa: `26.1-branchpoint-1415-gc5e413533f4`, commit `c5e4135…`, `VERSION 26.2.0-devel` | **medido por mí** | `git describe`, `cat VERSION` |
| 6 155 de los 136 686 pares discriminantes suffers overflow en el `mul` de 16 bits | **medido por mí** | `/tmp/opencode/lp_types.py` — corregí mi transcripción para modelar el wrap i16; el total 649 no cambió |
| 0 descompresores BC3 en `radeonsi` y `RADV` | **medido por mí** | `grep`, commit `1e28733` |
| `mesa-dri-drivers-26.2.3-1.fc44` instalado | **medido por mí** | `rpm -qa`, commit `9277e3c` |
| Que el árbol leído sea el binario instalado | **NO verificado** | `PLAUSIBLE`, no `OBSERVED`. Petición `Q-3` |

**Riesgo que asumo y declaro**: los valores `expect_llvmpipe` salen de una **reimplementación en
Python** de la aritmética de llvmpipe, no de haber ejecutado llvmpipe. Si mi transcripción
tuviera un error, los 649 casos serían los equivocados. **Cómo se cierra**: correr el mismo
barrido sobre el dispositivo `10005:0000` (llvmpipe) y comparar con `expect_llvmpipe`. Si
coinciden los 649, la transcripción es correcta. Es un test que **debe** tener poder de fallar
— si un `expect_llvmpipe` estuviera mal, la comparación falla y lo dice.

Esa verificación es la petición `Q-5`.

## 9. Peticiones

| # | Para | Petición | Bloquea |
|---|---|---|---|
| `Q-1` | `@IA-2` | predictor llvmpipe como **cuarta** categoría, escrito **independiente** de los otros dos | poder discriminante |
| `Q-2` | `@IA-2` | usar `casos_llvmpipe_unico.json` tal cual; no regenerar los bloques | cobertura de `F7` |
| `Q-3` | `@IA-1` | `nm -D`/`strings` sobre `radeon_dri.so` y `libvulkan_radeon.so` | convierte `PLAUSIBLE` en `OBSERVED` (§8) |
| `Q-5` | `@IA-2` | barrer el mismo corpus sobre `10005:0000` (llvmpipe) y comparar con `expect_llvmpipe` | valida mi transcripción (§8) |
| — | `@IA-1` | *(retirada)* qué árbol Mesa es el del build del proyecto | era informativo, ya no bloquea |
