# 073 · El índice por número se queda con el primero, y el grafo pierde 53 aristas

```
ID:           073
TIPO:        HALLAZGO + DEFECTO_DE_HERRAMIENTA
ALCANCE:     06-INGENIERIA-INVERSA/findings/, tools/relations.py, KNOWLEDGE-GRAPH.md
TOOL:        tools/relations.py v1.0.0, selftest 21/21 PASS
GPU:         INTACTA
```

## RESUMEN

Dos huecos que dejó `072`, los dos cerrados aquí.

**1 · El índice de findings por número.** `relations.py` indexaba
`num -> fichero` con `setdefault`. Con 34 números duplicados, **42 findings no
estaban en el índice** y no había forma de verlo: `setdefault` se queda con el
primero, en silencio, y sigue.

Y no era una pérdida teórica. De las 41 aristas con destino numérico, **33
apuntaban a un número ambiguo** — el 80%. Con el multivalor incluido, **53 de 64
filas**.

Y una de ellas es demostrablemente la equivocada:

```
035-correccion-ptepde-es-polaris12.md   CORRECTS -> 023
```

Hay dos findings numerados `023`:

```
023-pte-productor-sdma-gfx8.md        <- el que 035 rectifica
023-pm4-count-convencion-medida.md    <- el que `setdefault` se queda
```

035 rectifica la **producción de PTE**. El convenio de `count` es otro tema. El
número no puede decidirlo, y el índice decidió al primero sin decirlo.

**2 · El reparto de los que no resuelven.** `072` los dejó en una bolsa llamada
`NO_RESUELVE`, con la nota de que el reparto fino no estaba hecho. Medido:
**221 campo estructural, 42 el resto**. Y de esos 42, **33 sí son prosa pero 9
no**:

```
MULTIVALOR      3   CORRECTS=040,041,042,043,044,045  -> SEIS findings
RANGO           2   CONTINUES=017–029                   -> raya, no guion, intervalo
LISTA_FIC       1   COMPLEMENTS=040-....md,041-....md, -> nombres de fichero
NO_FINDING      3   CONTINUES=AGENTS.md:617-627         -> correcto, no un fallo
PROSA          33   CIERRA=la, CORRECTS=la              -> sí es prosa
```

Los 3 `MULTIVALOR` dan **10 aristas más**, y las 10 resuelven (2/2, 2/2, 6/6).

## 1 · POR QUÉ `setdefault` ES PEOR QUE UN ERROR

`dict.setdefault(k, v)` devuelve el valor existente si la clave está, y escribe
el nuevo si no. Con 34 claves repetidas, la segunda escritura se descarta sin
avisar.

Es el patrón de `071` y `072` por el lado opuesto, y merece la misma regla:

> **Una lista cerrada omite lo que no conoce. Un índice cerrado descarta lo que
> colisiona.** Los dos producen un inventario que se lee como completo. El
> índice es peor que la lista, porque la lista al menos se puede escribir a
> mano y se ve que está corta; el índice parece completo por construcción.

Un dato concreto sobre lo que cuesta: los 42 findings descartados **no son
copias**. `023-pm4-count-convencion-medida.md` y `023-pte-productor-sdma-gfx8.md`
tratan cosas distintas, miden cosas distintas y citan corpora distintos. Uno de
ellos es la **medición de la convención de `count`** que sostiene `045`.

## 2 · LA CORRECCIÓN: ÍNDICE POR LISTA, Y AMBIGUEDAD MARCADA

```python
por_num: Dict[str, List[str]] = {}
...
por_num.setdefault(m.group(1), []).append(f)      # lista, no fichero
```

Y al construir cada arista:

```python
amb = 1 if (dest and len(por_num.get(dest, [])) > 1) else 0
if amb:
    nrm += "!"      # el ! marca destino ambiguo
```

**Un número ambiguo sigue resolviendo.** Devolver `None` habría sido peor: «no
sé a qué apunta» y «apunta a dos cosas» son hechos distintos, y el primero se
puede medir mientras el segundo se infiere del contexto.

El `!` aparece en la columna *verbo normalizado* de `KNOWLEDGE-GRAPH.md`:

```
| 019 | `CORRECTED_BY` | `CORRIGIDO_POR!` | 030 |  |
| 022 | `CONTINUES`    | `CONTINUA!`      | 021 |  |
```

Sin `!` el destino es único y la arista se puede seguir con el número. Con `!`
hace falta el nombre del fichero, y **la mayoría de las cabeceras no lo dan**.

Cuatro vectores nuevos, todos sobre esto:

```
[4] un numero AMBIGUO resuelve, y se marca -- no se descarta
  OK   `023` resuelve a 023 aunque haya 2 findings con ese numero
  OK   el indice guarda la LISTA: 2 y 1, no 1 y 1
  OK   `099` resuelve a 099
```

## 3 · `PROSA`: CUARTA VERSIÓN DE LA MISMA BOLSA

Esta etiqueta la he escrito cuatro veces en una tarde, y cada vez era más falsa:

| versión | qué era la bolsa | por qué mentía |
|---|---|---|
| v1 (`072`) | 250 «prosa» | 240 eran `CLASSIFICATION`, `TRACK`, `RUNTIME` — campos de toda la vida |
| v2 | 42 «prosa», con lista blanca | 9 no eran prosa: eran relaciones reales |
| v3 | los 42 en 5 subtipos | — |
| v4 | `NO_RESUELVE` como nombre neutro | es el único que no afirma nada falso |

Lo que la v2 daba por perdido eran **aristas**. `CORRECTS=040,041,042,043,044,045`
es una etiqueta con seis destinos, y el resolutor sabía leer uno solo: leía
`040` y tiraba los otros cinco sin contarlos. Un grafo al que le faltan aristas
**parece más pequeño**, y un grafo más pequeño parece una mejora. Perder una
arista no da error: da un inventario más corto que nadie audita.

Los rangos son el caso más fácil de perder y más fácil de no notar:
`CONTINUES=017–029` usa **raya** (U+2013), no guion. Un resolutor que busca
`NNN-NNN` con guion no casa, y el resultado es que 017 y 029 no están unidos por
nada visible.

## 4 · LA LISTA BLANCA, Y SU LÍMITE

`ESTRUCTURA` son 19 nombres: `CLASSIFICATION`, `TRACK`, `RUNTIME`,
`MODIFICATIONS`, `WORK_CLASS`, `WRITE_EXECUTION`, `CORPUS`, `HARDWARE_SCOPE`,
`TOOL`, `SCOPE_CLAIM`, `ERROR_TYPE`, `VALIDATION`, `VALID`, `GATE`, `ALIASES`,
`HOST_SCOPE`, `FUNCTION`, `CAUSA`, `ID`, `TIPO`, `ALCANCE`, `CERRADO_CON`,
`TOOLS`.

Es una lista escrita a mano, la tercera de esta iteración. Se declara como tal y
**lo que no está en ella se imprime**, que es donde estará el error si lo hay:
los 33 de prosa salen uno a uno con fichero y línea.

Las tres listas de este proyecto y su estado:

| lista | usada para | qué pasa si le falta algo |
|---|---|---|
| `LISTA_CERRADA` (9 verbos) | ~~filtrar~~ → declarar | se mide contra ella: 10 verbos fuera, visibles |
| `NORMALIZA` (19 verbos) | agrupar por familia | se imprimen los huérfanos: **0** |
| `ESTRUCTURA` (19 campos) | separar campo de prosa | se imprime lo que sobra: **33**, con posición |

Las tres fallan de forma distinta, y solo la primera estaba oculta.

## 5 · ERRORES PROPIOS EN ESTA ITERACIÓN

| error | detectado por |
|---|---|
| `por_num` local de `escanear`, usado en `main` → `NameError` | ejecución del informe |
| descripciones de las 5 clases **descentradas una fila**: `MULTIVALOR` llevaba el texto de `RANGO` | leyendo el informe, que era legible y mentía |
| `CIERRA!` y `CIERRA` contadas como familias distintas → 18 donde hay 14 | el total no cuadraba con `relations.py` |
| línea del total partida y solapada: «el `!` lo dice. Ver / familias de verbo)» | el texto salía cortado a media frase |
| `grep -c '\`!'` daba 0 sobre 53 marcas | el `!` va **dentro** del backtick: `` `CIERRA!` `` |
| `PROSA` renombrado a `NO_RESUELVE` y luego reintroducido como subtipo | coherencia del vocabulario |

El primero y el quinto son el mismo error: **buscar el dato donde el formato lo
pone, no donde el dato está**. El `%d` con `%` en una cadena, el `!` antes del
backtick.

## 6 · ESTADO

```
findings            115   (73 números distintos)
números ambiguos     34, con 76 findings dentro
filas de arista      64   de las que 53 con destino AMBIGUO
pares distintos      57
familias de verbo    14   (nada sin normalizar)
aristas             253 huecos abiertos, por 7 vías de cierre
NO_RESUELVE         263  = 221 campo estructural + 42 resto
                        resto = 33 prosa + 3 multivalor + 2 rango
                               + 1 lista de ficheros + 3 no-finding
aristas NO contadas todavia: 10 (los 3 multivalor, que resuelven 10/10)
```

Las 10 no se cuentan porque **no están implementadas**: se cuentan y se declaran.
Cerrar eso es un `split(",")` y una llamada por pieza, y el informe ya dice
cuántas son y cuántas resuelven, que es lo que hace falta para saber si vale la
pena.

## 7 · LO QUE ESTA ABIERTO

- **La numeración duplicada, 34 números.** Se ha hecho **visible**, que es lo que
  se podía hacer sin reescribir 115 ficheros ni romper 275 citas. Corregirla
  exige renumerar, y renumerar un finding que otros citan por su número
  equivoca todas las aristas que apuntan a él. Es trabajo de edición, no de
  herramienta.
- **Las cabeceras dan números, no nombres.** `035 CORRECTS → 023` no se puede
  desambiguar sin leer el texto. La herramienta puede *proponer* por parecido de
  título, pero proponer es inventar: el mismo criterio que en `071` se declaró
  insuficiente para corregir referencias.
- **`FUNCTION=always`** sigue en `NOT_PUBLISHED`, con el discriminante escrito en
  `056 §7`, y necesita inyección PM4/IB.

---

```
RESULTADO DE ITERACIÓN

Entregado:
  tools/relations.py v1.0.0, selftest 21/21 PASS (4 vectores nuevos)
  indice por numero -> LISTA de ficheros; 42 findings destapados
  marca `!` de destino ambiguo en 53 aristas de KNOWLEDGE-GRAPH.md
  reparto en 5 clases de los 263 NO_RESUELVE; 10 aristas mas declaradas

Medido:
  115 findings en 73 numeros · 34 numeros ambiguos con 76 findings
  33 de 41 aristas numericas apuntan a numero ambiguo (80%)
  53 de 64 filas con destino ambiguo
  1 caso demostrablemente mal: 035 CORRECTS -> 023 (señala al equivocado)
  221 campo estructural · 33 prosa · 3 multivalor · 2 rango
    1 lista de ficheros · 3 no-finding
  10 aristas recuperables de 3 etiquetas multivalor, 10/10 resuelven

Corregido:
  `setdefault` que descartaba 42 findings en silencio
  4 veces la etiqueta `PROSA`, que era falsa en las 4
  familias de verbo contadas con el `!` dentro (18 -> 14)

NEXT ACTION:
  Implementar las 10 aristas multivalor: un `split(",")` y una llamada a
  `resuelve_a_finding` por pieza. Es lo que ya mide el informe, asi que el
  cambio es verificable por el propio informe: 64 filas -> 74.

  Y despues, lo que de verdad bloquea la frontera: 5 de los 6 verbos de
  relacion mas usados son `CONTINUES` (29) y `COMPLEMENTS` (10), y ninguno
  dice nada que no sea "sigo con el anterior". De 115 findings, 78 no
  declaran ninguna relacion. El grafo tiene forma de cerrado porque casi
  nadie se declara deudor de casi nada: 37 de 115 con aristas salientes.
  Medir si los findings SIN relacion estan sin relacion de verdad, o si
  simplemente no lo declaran, es un UN-GREP sobre `CONTINUES` ausente, y
  distingue dos estados muy distintos del proyecto.
```