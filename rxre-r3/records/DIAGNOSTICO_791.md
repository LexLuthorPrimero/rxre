# DIAGNÓSTICO R3 — 791 divergencias sobre `filenvercmp` en `/usr/bin/ls`

Fecha: domingo 2026-11-12 · Autor: diagnóstico autorizado exclusivamente
**No se corrigió ningún caso. No se modificó código del repo. Corpus y oráculo intactos.**

## 1. Clases encontradas (por posición de `.` en cada lado)

| Clase | Lado A | Lado B | Casos | Síntoma (recon → native) |
|---|---|---|---|---|
| A | Sin punto | Punto medio | 309 | recon=+1 → native=**negativo** |
| B | Punto medio | Sin punto | 309 | recon=-1 → native=**positivo** |
| C | Punto medio | Punto medio | 82  | recon=-1/-99 → native=+302/+303 |
| CZ | Punto trailing | Punto medio | 4 | recon=+1/99 → native=-303 |
| MC | Punto medio | Punto trailing | 4 | recon=99 → native=-303 |
| Z | Punto trailing | Sin punto | 34  | recon=-1 → native=**+** |
| SZ | Sin punto | Punto trailing | 35  | recon=+1 → native=**-** |
| P | Leading dot | Leading dot | 14  | signo OK nativo pero magnitud distinta |

**Suma = 791 ✓ (309+309+82+4+4+34+35+14=791)**

## 2. Evidencia empírica adicional (sondaje directo con sello integral)

Casos discriminantes sondeados con el binario sellado (`harness/probe4`):

| r(a,b) nativo | r | Interpretación provisional |
|---|---|---|
| `r("a.", "a!b")` | `13` | Sepa `.` gana en filenvercmp sobre `!` dentro de b = rama operativa A |
| `r("a!b", "a.")` | `-13` | Mirror de A |
| `r("a.", "a.1")` | `-1` | `.` < `1` dentro de extensión cuando ambos lados llevan `.` (clase C) |
| `r("a.", "a.0")` | `0` | `.0` == `.` — ambos lados están por debajo del techo alfa numérico |
| `r("a.", "a.bc")` | `303` | extensión alfabética en B → orden por extensión mayor |
| `r("a.", "a.abc")` | `303` | mismo comportamiento para extensión larga |
| `r("r('a.', 'a'))` | n/d | recalca antes de provocarla: bucle prohibitivo de /common/ |
| `r("abc", "a.")` | `-204` | filename vs filename con extensión — B-class |
| `r("a.", "ab")` | `204` | extensión solo en A — B-class |

**Lectura clave:** comparando `a.` vs `a.1` devuelve `-1` (i.e., `.` < `1`), pero `a.` vs `a.bc` devuelve `303` (i.e.,  `.` > `.bc` en alguna clase). Esto sugiere que el nativo integra una rama de comparación de "defensa por extensión" y no el dominio byte-lineal simple que recon implementó.

## 3. Causalidad a la vista

Recon filtra el byte-punto con un OR con `.`, produciendo `-1` para todos los pares que contienen `.` cualquiera que sea la posición. Los valores nativos toman en cuenta el punto como **parte** del dominio de comparación (en filenvercmp, el punto no es solo separador de extensión, es un byte más del orden de filtro).

**El punto no es un separador ordinario de filenvercmp tratado por `file_prefixlen`; es parte del universo de comparación.** Esto tiene dos consecuencias diferenciadas en Gym∷ estruct.

## 4. Aciertos / decisiones tomadas durante el diagnóstico

- Los 791 casos NO son homogéneos: indican al menos 2 códigos de bifurcación distintos en el nativo (rama `.no ext vs .ext` y rama `両 .ext vs .ext` con distinta ordenación en función de si la extensión empieza por letra o dígito).
- Importantes restricciones laterales: el primer carácter igual es `a` en los casos C y M/Z; los casos A/B contienen `a!b` (sign que recon picó mal `.`).

## 5. Separadores discriminantes sugeridos

Lo más eficaces para separar reglas son:
1. `a.` vs `a.0` (result `0`)
2. `a.` vs `a.1` (result `-1`)
3. `a.` vs `a.bc` (result `303`)
4. `a.` vs `a.abc` (result `303`)
5. `abc` vs `a.` (result `-204`)
6. `a.` vs `ab` (result `204`)
7. `.` vs `.a` (result `-1`)
8. `.` vs `a` (result `-1`)

## 6. Restricciones y estado de NO_CONFIRMADO
1. `filevercmp(".", ".a") = -1` y `filevercmp(".", "a") = -1` — **no confirmado** que estén en la misma rama; ambos son `-1`, que parece coincidencia accidentada.
2. `filevercmp(".", "a~")` y `filevercmp(".", "a")` ambos `-1` — **`NOT_DETERMINED`** oficialmente; puede ser que `.` < cualquier byte tras él, sin importar cuál.
3. Rama para archivos con extensión variable (`a.b.c`, `a.b1.c`, etc.) lleva la misma constante +303 en los dos casos que aparecen (b.c y b1.c) — podría ser invariante común en la rama.
4. `filevercmp(".", ".") = 0` — **no probado** (no se permite reconstrucción de cero); sí someter al oráculo, pero no aparece en corpus.

## 7. Conclusión provisional (sin corregir)

> **NOT_DETERMINED / PARTIAL.** Las 791 divergencias se agrupan en tres regiones de intervención separables del nativo:
> - región A/B: `a.` vs `a!b` (extensión vacía vs. aparente alfil);
> - región C: `.` en secuencia por byte-positivo (comparador número + alfabeto);
> - región Z/P: `.` pura trailing + leading (extensión vacía + leading dotled).

Ninguna de estas intervenciones es correción trivial de un solo byte — son tres segmentos independientes del decisor nativo, cada uno con su propio regla de desbordamiento. Ninguno es NOT_EXECUTED, todos son NOT_CONFIRMED hasta corregir y re-verificar contra oráculo sellado.

**El diagnóstico NO contiene corrección alguna. Corpus y oráculo permanecen intactos. `reconstruction/filenvercmp.c` sin modificar.**
