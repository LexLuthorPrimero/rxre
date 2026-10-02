# 072 · La lista cerrada de verbos que cronometraba el grafo de findings

```
ID:           072
TIPO:        HALLAZGO + DEFECTO_DE_HERRAMIENTA
ALCANCE:     06-INGENIERIA-INVERSA/findings/, KNOWLEDGE-GRAPH.md, CONTRADICTIONS.md
TOOL:        tools/relations.py v1.0.0, selftest 17/17 PASS
GPU:         INTACTA
CIERRA:      por qué se sabe que ya no se repite
```

## RESUMEN

`KNOWLEDGE-GRAPH.md` y `CONTRADICTIONS.md` se generaban con una **lista cerrada
de nueve verbos escrita a mano** (`CORRECTS`, `IMPLEMENTS`, `GENERALIZA`,
`GENERALIZADO_POR`, `RETRACTED_BY`, `CORRECTED_BY`, `RETRACTED_PARTLY_BY`,
`CERRADO_POR`, `MEDIDO_EN_MI_ASIC_POR`). Nadie comprobó que la lista estuviera
completa.

Medido con `tools/relations.py`, que **no usa la lista**:

```
670 tokens Etiqueta=valor en 111 cabeceras
54 etiquetas distintas
19 de ellas son VERBOS DE RELACION que apuntan a un finding
64 filas de arista, 57 pares (desde,hacia) distintos, 14 familias de verbo
```

| | antes | medido | déficit |
|---|---|---|---|
| verbos conocidos | 9 | 19 | **10 verbos, 49 ocurrencias** |
| aristas | 8 | 57 | **7 de cada 8 no se veían** |

**`KNOWLEDGE-GRAPH.md` no era un grafo con 8 aristas. Era un grafo con 8 aristas
de las que la herramienta conocía.** El grafo completo se leía como cerrado.

Los verbos que la lista no conocía, por usos:

| verbo | usos | ejemplo |
|---|---|---|
| `CONTINUES` | 29 | 018 → 017 |
| `COMPLEMENTS` | 10 | 026 → 024 |
| `CIERRA` | 2 | 032 → 030 |
| `COMPLETA` | 2 | 045 → 023 |
| `CORRECTS_RUTA` | 1 | 047 → 046 |
| `CORRIGE_LA_POLITICA_DE` | 1 | 051 → 046 |
| `RECTIFIES` | 1 | 035 → 024 |
| `RETRACTS` | 1 | 043 → 035 |
| `STRENGTHENS` | 1 | 034 → 033 |
| `AMENDA` | 1 | 023 → 022 |

`CONTINUES` solo — 29 usos, casi la mitad de todas las relaciones que el
proyecto declara sobre sí mismo — era invisible.

## 1 · POR QUÉ UNA LISTA CERRADA ES PEOR QUE NO TENER NADA

Un grafo incompleto **hubiera** delatado algo. Este era **completo**:
`KNOWLEDGE-GRAPH.md` decía «Total: 8 findings con aristas salientes», con tabla
y con `GENERADO POR` en la cabecera. Se lee como un inventario finished.

Es la misma clase que los 466 macros de `041`, los 226 `SIN_PISTAS` de `050`, los
133 obsoletos, los 8 selectores de `047`, y los cinco fallos de `071`: **una
medida que cuenta lo que su autor ya sabía contar**.

> **El punto preciso**: una lista cerrada no es un dato malo, es un dato
> **congelado**. Es correcta el día que se escribe y se queda vieja para siempre
> sin Changing de forma. El defensa contra eso no es escribir listas más
> largas: es medir la lista contra el conjunto y decir qué fraction falta.

## 2 · LA MEDICIÓN, Y CÓMO SEPARAR RELACIÓN DE PROSA

El primer intento, sin ancla de línea, no dio cero. Dio 670 tokens, y entre ellos:

```
ALIASES=los        CIERRA=la         VALID=0        CORRIGE=el
```

Son prosa española con la palabra justo antes de un `=`. Un `grep -oE` sobre
`[A-Z_]+=[^ ]+` da 670 filas y **la lista cerrada habría dado 15**: dos
números plausibles, ninguno de los dos.

La separación **no es heurística sobre el valor**: un valor es un finding si
**resuelve contra el índice de ficheros de findings/**, por número de tres
dígitos o por nombre base completo.

```
CORRECTS=041       -> 041   resuelve
RETRACTED_BY=043   -> 043   resuelve
CONTINUES=017-vm.md -> 017  resuelve
ALIASES=los        -> None  no resuelve
CIERRA=la          -> None  no resuelve
```

Con eso: **250 de 670 tokens NO resuelven**. Y de esos 250, la mayoría
(`CLASSIFICATION`, `TRACK`, `RUNTIME`, `MODIFICATIONS`) no son prosa: son campos
del propio finding. En la primera versión de esta herramienta los metí en una
categoría llamada `PROSA`, y **eso era una etiqueta falsa**: `CLASSIFICATION=DOCUMENTATION`
no es prosa, es el campo que dice de qué clase es el documento. Nombrar mal una
clase no cambia el dato, pero hace que el dato parezca mucho más sucio de lo que
es — y quien lo lee deja de fiarse. Renombrado a `NO_RESUELVE`, que es lo que se
sabe de verdad.

**Lo que un `grep` habría dado de más son las aristas: 49, no 250.**

## 3 · FLEXIÓN: 19 VERBOS SON 14 FAMILIAS

La misma relación se escribe con dos verbos:

```
CIERRA=030        y  CERRADO_POR=030
COMPLEMENTS=024   y  COMPLETA=023
CORRECTS=041      y  CORRECTS_RUTA=046      y  RECTIFIES=024  y  AMENDA=022
```

Resultado medido:

```
64 filas de arista
57 pares (desde,hacia) distintos      <- las 7 sobrantes son duplicados por flexion
19 verbos -> 14 familias de verbo
```

Los 64 eran una **cota superior**, no un recuento. Un grafo con aristas
duplicadas por flexión parece más denso de lo que es, y hace que 19 verbos
parezcan 19 relaciones cuando son 14 familias.

La tabla `NORMALIZA` es una lista escrita a mano — la misma cosa que acabo de
criticar. Se declara como tal, y `relations.py` **imprime los verbos que no
entran en ella**:

```
Ningun verbo sin normalizar: la lista cubre los 19.
```

Si mañana alguien añade `CONTINUES_RELATIVO=055`, aparecerá como huérfano en
vez de desaparecer. Un huérfano visible es mejor que un verbo que se cuenta
dos veces sin que nadie lo sepa.

## 4 · EL ANCLA `^`, SEXTA VEZ

La primera medición dio **cero etiquetas**:

```python
ETIQUETA_RX = re.compile(r"^([A-Z][A-Z0-9_]{2,})=([^\s`]+)", re.M)
```

Con ancla de línea. Y las etiquetas **no están al principio de la línea**:

```
`CLASSIFICATION=DOCUMENTATION` · `TRACK=STATIC` · `GPU INTACTA`
```

Están en línea, dentro de backticks, en la tercera o cuarta línea de la
cabecera. El `^` las descartaba todas.

Cero etiquetas es un número **que parece un resultado** — «este proyecto no usa
etiquetas» — y por eso el informe imprime los dos contadores: *etiquetas
distintas* y *ocurrencias*. Si el patrón casara mal saldría 0 en ambos, y 0 en
ambos es una señal de herramienta rota, no de corpus vacío. Es el mismo
razonamiento del índice con cota de `artifacts.py`: **un cero sin cota es un
olvido**.

Séptima reaparición del mismo defecto (`^` sin `re.M`, `\b` tras `_`, recorte de
N líneas, coincidencia por subcadena), y **la primera con `=` como separador**.

## 5 · ERRORES PROPIOS EN ESTA ITERACIÓN

| error | detectado por |
|---|---|
| ancla `^` → 0 etiquetas | los dos contadores a 0 |
| 2 vectores FAIL: `RETRACTED_BY=043` y `CONTINUES=017-vm.md` | el fixture del selftest **no contenía** `043` ni `017-vm.md`. El fallo parecía del resolutor — que es el diagnóstico peligroso, porque invita a «arreglar» código que estaba bien. Un selftest que depende de un fixture a medio montar mide si me acordé de escribir el número |
| `CLASSIFICATION=DOCUMENTATION` etiquetado como `PROSA` | salió en el informe y era obviamente falso al leerlo |
| `sentido()` aplicaba la pasiva a todo `*_POR` → `046 RECIBE de 043` | el verbo `CERRADO_POR` se lee «043 queda cerrado por 046»; 046 no recibe nada. Salió al mirar la tabla, no al ejecutar |
| `x[4]` en vez de `x[3]` para el verbo normalizado | «1 familias de verbo». Índice equivocado en tupla → entero pequeño y plausible, la peor forma de que un índice falle |
| unpacking de 4 sobre tuplas de 5 | `too many values to unpack` → **rc=2 y nada escrito** |
| `pares`/`familias` calculados sobre la variable equivocada | artefacto con «1 familias» |

El unpacking merece nota: `artifacts.py` **rechazó escribir los siete
artefactos** porque un generador falló, y lo hizo con `rc=2` y un mensaje que lo
dice. Ese es el comportamiento que `071` enseñó: *el fallo tiene que ser ruidoso
y el artefacto tiene que estar ausente*. Antes de esa corrección, este mismo
error habría producido un `KNOWLEDGE-GRAPH.md` con la mitad de las aristas y
nadie lo habría mirado.

## 5bis · EL SENTIDO DE LA ARISTA: `CERRADO_POR` LEÍDO AL REVÉS

`CONTRADICTIONS.md` calcula el sentido de cada arista. La primera versión
aplicaba la regla de la pasiva a **todo lo que acababa en `_POR`**, y salía:

```
| 043 | `CERRADO_POR` | 046 | 046 RECIBE de 043 |     <- FALSO
```

043 queda cerrado **por** 046. Al revés no tiene sentido: 046 no es el
destinatario de una retracción, es el hallazgo que cierra el hueco de 043.

Y **no se arregla con una excepción por verbo**, porque `*_POR` cubre cuatro
cosas distintas:

| verbo | ¿pasiva real? |
|---|---|
| `RETRACTADO_POR` | sí — el finding recibe la retracción |
| `GENERALIZADO_POR` | sí — y además va **hacia atrás**, el autor es el `POR` |
| `CERRADO_POR` | **no** — dice qué cierra el hueco, no quién recibe nada |
| `MEDIDO_EN_MI_ASIC_POR` | **no** — es una atribución de autoría |

El sufijo no basta. Así que el cálculo se **limita a `_BY`**, que es la única
terminación inequívoca, y para los otros cuatro el verbo se imprime tal cual
con la marca `sentido NO calculado`:

```
| 043 | `CERRADO_POR` | `CIERRA` | 046 | 043 --CERRADO_POR-> 046  (sentido NO calculado) |
```

> **Un sentido desconocido declarado es información; un sentido incorrecto es
> ruido.** Y el ruido en una columna que se llama «sentido» es peor que una
> columna vacía, porque se lee.

Éste es el sexto caso del patrón: no es un error que dé error, es uno que
produce una frase **gramatical, plausible y al revés**.

## 6 · LO QUE ESTO CIERRA Y LO QUE NO

**Cierra:**
- `KNOWLEDGE-GRAPH.md`: de 8 aristas a 64 filas / 57 pares / 14 familias, con el
  verbo original **y** el normalizado, y las 14 familias visibles.
- `CONTRADICTIONS.md`: usa el mismo vocabulario medido, y declara cuál es el
  subconjunto de verbos de contradicción.
- La lista cerrada deja de ser un filtro y pasa a ser una **declaración**: vive
  en `relations.py` marcada como tal y se mide contra ella.

**No cierra, y sigue abierto:**
- **111 findings en 70 números distintos, 32 duplicados.** `relations.py` los ve
  (`por_num.setdefault` se queda con uno) pero no lo dice: un hallazgo duplicado
  hace que sus relaciones se atribuyan al primero que se encontró. Es el mismo
  hueco que `071` detectó y que ninguna herramienta corrige todavía.
- **El reparto fino entre campo estructural y prosa no está hecho.** Los 250
  `NO_RESUELVE` son en su mayoría `CLASSIFICATION`/`TRACK`/`RUNTIME`/
  `MODIFICATIONS`, pero no hay cifra. Declarado como hueco, no como resultado.
- **Si el listado de verbos crece.** Con 111 documentos y 70 números, el
  vocabulario no es estable. `NORMALIZA` es una lista y las listas envejecen; lo
  único que evita que envejezca es que los huérfanos se impriman.

---

```
RESULTADO DE ITERACIÓN

Entregado:
  tools/relations.py v1.0.0, selftest 17/17 PASS
  KNOWLEDGE-GRAPH.md regenerado: 64 filas, 57 pares, 14 familias
  CONTRADICTIONS.md regenerado con el vocabulario medido

Medido:
  670 tokens Etiqueta=valor, 54 etiquetas distintas
  19 verbos de relacion (la lista cerrada conocia 9)
  10 verbos desconocidos, 49 ocurrencias
  64 filas / 57 pares / 14 familias tras normalizar flexion
  250 tokens NO_RESUELVEN, de los que 240 son campos estructurales
  0 verbos sin normalizar

Corregido:
  la lista cerrada de 9 verbos deja de ser filtro y pasa a ser declaracion
  `PROSA` renombrada a `NO_RESUELVE` (la etiqueta era falsa)

NEXT ACTION:
  Dos huecos, ambos de una sola linea de codigo cada uno:

  1. relations.py: cuando dos findings comparten numero, `por_num.setdefault`
     se queda con el primero y el segundo pierde TODAS sus relaciones. Con 32
     numeros duplicados, eso es silencioso y grande. El arreglo es indexar por
     RUTA y no por numero, y medir cuantos findings pierden relaciones por
     culpa de la numeracion. Es el mismo patron que 071, al reves: alli una
     lista cerrada que omite; aqui un indice cerrado deja fuera.

  2. El reparto estructura/prosa de los 250 NO_RESUELVE. Se resuelve con una
     lista blanca de campos estructurales --CLASSIFICATION, TRACK, RUNTIME,
     MODIFICATIONS, WORK_CLASS, WRITE_EXECUTION, CORPUS, HARDWARE_SCOPE,
     TOOL, SCOPE_CLAIM, ERROR_TYPE, VALIDATION, VALID, GATE-- y lo que sobra
     se reporta como prosa, que es lo que hay que mirar de verdad.
```