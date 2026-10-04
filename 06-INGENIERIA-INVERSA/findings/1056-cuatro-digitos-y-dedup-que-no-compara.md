# 1056 — `\d{3}` fundía 142 documentos en nodos ajenos, y mi propio dedup no comparaba lo que guardaba

```text
AGENCIA=RX550-INVESTIGACION · WORK_CLASS=AGENT-MAIN-VALIDITY
GENERADO=2026-10-04 · MEDIDO=EN ESTA HOST
AFECTADO=tools/claims.py:128 (FINDING_RX) · :805 (num) · :829 (docs[num])
         tools/artifacts.py (el dedup, mio)
ORIGEN=08-ARQUITECTURA/GRAFO-CLAVE-NO-UNICA.md
ESTADO=PROBADO · REPARADO · 21 vectores PASS · refuta una linea de mi 1054
```

## Dos defectos, y los dos nacen de lo mismo

**Compara una cosa y guarda otra.** En `claims.py:805` el código decidía el número de
hallazgo, y en `artifacts.py` mi dedup decidía si una fila estaba repetida. Los dos
comparaban **una representación** del dato y guardaban **otra**.

## El primero: 142 documentos de 558 desaparecían

`tools/claims.py:128` era:

```python
FINDING_RX = re.compile(r"^(\d{3})[-_]")
```

**Tres dígitos exactos.** El número de hallazgo tiene tres **o cuatro**, y hay 42 ficheros
con cuatro. El regex no casaba con ellos, y la línea siguiente hacía lo peor que se puede
hacer con un número:

```python
num = m.group(1) if m else f[:3]        # ANTES
```

`f[:3]` de `1002-correccion-a-105-el-1024-no-es-el-anillo-de-interrupcion-y-el-real-tiene-4096.md`
es `"100"`. Luego **el hallazgo 1002 se atribuía al 100**, que es otro hallazgo.

Y `claims.py:829` hace `docs[num] = {...}`, que **asigna** en vez de acumular: de los N
documentos con la misma clave sobrevive el último procesado.

MEDIDO, con el código de antes, sobre el estado real de `findings/`:

```
ficheros .md                      558
claves que salen en docs          416
DOCUMENTOS QUE DESAPARECEN       142      el 25 %
```

| nodo | documentos que caen en el |
|---|---|
| `104` | **11** |
| `102` | **11** |
| `103` | 9 |
| `100` | 8 |
| `105` | 7 |
| `101` | 6 |

Cinco de esos seis son documentos de cuatro dígitos fundidos en un nodo de tres, y los
nodos `100`–`105` **existen** como hallazgos de tres dígitos. O sea que no era una
ambigüedad: era una atribución a un documento equivocado, y silenciosa, porque el nodo
destino existe y por eso parece una respuesta.

**Reparado** a `^(\d{3,4})[-_]`, y cuando el nombre no tiene forma de número ya **no se
elige un nodo**: se cuenta en `hallazgos_sin_numero`, se exporta en el JSON y se imprime
en el resumen. Medido 0 en el estado actual, que es lo correcto — y que **solo** puede
medirse porque ahora la lista existe.

```
ficheros .md         558
ANTES  claves=416    documentos que se pisan=142
AHORA  claves=457    documentos que se pisan=101
```

41 documentos recuperados, los 41 de cuatro dígitos, cada uno con su nodo. **Los 101 que
quedan son las 74 colisiones**, que son otro problema y está declarado como tal: ningún
dato del árbol dice cuál de los dos es el canónico, y eso es decisión, no herramienta.

## El segundo, y es mío: mi 1054 affirmations algo falso

El hallazgo 1054 dice, textual:

> *«aristas duplicadas: **0**  (antes: 4 = 72->041 x2 y 73->040 x2)»*

**Es falso. Eran 2.** El nodo `GRAFO-CLAVE-NO-UNICA` lo refutó, y tenía razón. Mi código:

```python
item = "%s-%s -> %s %s" % (...)
if item in corr or item in corr_ambigua or item in corr_rota:
    continue
if estado == "AMBIGUA":
    corr_ambigua.append("%s  [%d candidatos]" % (item, len(det)))
```

El guard busca `item`. Lo que se guarda es **`item` con un sufijo añadido**. Luego `item`
a secas nunca está en la lista, el `continue` nunca salta, y la fila se repite. MEDIDO
antes del arreglo:

```
2x  - `072-la-lista-cerrada-de-ve -> corregida por 041  [3 candidatos]`
2x  - `073-el-indice-por-numero-d -> corregida por 040  [3 candidatos]`
```

Las mismas dos que yo declaré arregladas. **Y el patrón es el de siempre, por cuarta vez
en la sesión:** la rama hermana (`retr`, línea 315) compara lo que guarda, y la mía
comparaba otra cosa. Igual que `constmap.py` (arregló el self-test, dejó la CLI), que
`drift.py` (arregló el informe, dejó la escritura), y que las tres ramas de 1054.

Reparado calculando la fila una vez y comparando **la fila**:

```python
fila = "%s  [%d candidatos]" % (item, len(det)) if estado == "AMBIGUA" else item
if fila in corr or fila in corr_ambigua or fila in corr_rota:
    continue
```

MEDIDO después: 30 filas, **0 duplicadas**.

> **Un hallazgo que dice «lo he arreglado» necesita el mismo trato que el que dice
> «no lo he arreglado».** Escribir que un defecto está cerrado y que siga vivo dos
> commits más abajo es peor que no haberlo escrito, porque alguien confía en ello.

## Lo que el nodo además midió, y que cambia la pregunta

Su resultado más incómodo, y lo comprobó con 200 elecciones de documento:

> **Ocho agregados —nodos, aristas, grado máximo, ciclos, orden topológico, camino más
> largo, bucles— dan el valor EXACTO MISMO en las 200 elecciones. Cero medido.**

Los números **no se mueven**. Lo que cambia es **la identidad**: las 200 elecciones dan
**200 conjuntos distintos de documentos** dentro de los ciclos.

Eso obliga a reformular la pregunta del 259. No es «las herramientas dan resultados
incorrectos», que es lo que el 259 afirmaba. Es:

> **Los números son invariantes y por eso no avisan.** El agregado es correcto sobre una
> población que la herramienta no puede distinguir, y eso es indistinguible de que sea
> correcto sobre la población real.

Y el caso concreto, buscado por él: la fila «`035` RECIBE de `043`» es **verdadera para
uno** de los tres ficheros `043` y **falsa para los otros dos**. Se comprobó con
`grep -ci "retract\|035"`. O sea que hay una afirmación con la forma correcta y el
contenido equivocado, y ninguna forma de verlo desde la salida.

## Lo que NO se afirma

- **No se ha resuelto la ambigüedad de los 101.** Es decisión de quien escribió los
  hallazgos, y no hay dato que la decida.
- **No se ha tocado `relations.py`, `frontier.py` ni `KNOWLEDGE-GRAPH.md`.** El nodo
  midió que `frontier.py:613-621` **asigna** en vez de acumular, con lo que **100
  documentos desaparecen** de su índice. No lo he reparado: es otra herramienta y otra
  puerta.
- **`EVIDENCE-MATRIX.md` es el peor consumidor**: 10 tokens apuntan a números con más de
  un fichero y no tiene ninguna marca que lo diga. No medido por mí.
- **No he regenerado ningún artefacto.** Todo se ha producido en memoria para medirlo.
- **El self-test de `claims.py` pasa con 21 vectores** (23 OK, 0 FAIL), y pasar el
  self-test no demuestra que la salida sea correcta: no tenía ningún vector con un
  nombre de cuatro dígitos, que es exactamente el hueco que dejó vivo el defecto.