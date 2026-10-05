# 1507 — El instrumento mentía en la columna que existía para no mentir: `indeterminado` salía como `no`

```
AUTOR=AGENTE-INSTR
FECHA=2026-10-05
TIPO=ERROR + CORRECCION
ESTADO=PROVEN (que el defecto existió) / CORREGIDO (que ya no)
ALCANCE=RXRE/tools/rxre_contracts.py, el instrumento MEDIDO, no el sujeto
MEDIDO=17 herramientas de revkit declaran `WRITES_FILES=indeterminado` y el
  informe las mostraba como `WRITES_FILES=no`
PRODUCER=rxre_contracts.py --json  -> leído el campo `declarado` y comparado con
  el campo `declarado_bruto` del contrato
ENCADENA=1505 (declaré los 17 como indeterminado y afirmé no mentir) ·
  1481 (el mismo modo de fallo: un valor con la forma correcta y la sustancia
  equivocada, esta vez en mi propio instrumento)
```

## Qué pasó

`1505` declaró 17 herramientas de `revkit` con `WRITES_FILES=indeterminado`, y
escribí en el hallazgo que esa era la forma de **no mentir** con el vocabulario
`yes`/`no` de `toolkit.py`.

Y a la vez, el instrumento que escribí para **comprobar** esas declaraciones
traducía así:

```python
declarado = ("WRITES_SYSFS=yes" if ...
             else ("WRITES_FILES=yes" if f["contrato"].get("WRITES_FILES") == "yes"
                   else "READONLY=yes, WRITES_FILES=no"))
```

Es decir: **todo valor distinto de `yes` se traducía a `no`.** `indeterminado`,
`only_with_--register`, cualquier cosa — salía `no`.

La tabla de `revkit` mostraba, para los 13 `READONLY`:

```
revkit/atomrom.py   0  READONLY=yes, WRITES_FILES=n  COINCIDE
```

y para los otros 17, `declarado` era `READONLY=yes, WRITES_FILES=no` con
veredicto `NO_DETERMINED`. **La columna que decía lo que la herramienta declara
decía `no` en 17 filas que dicen `indeterminado`.**

> el instrumento no puede mentir en la columna que existe para no mentir

## Cómo se detectó

No leyendo la tabla a ojo —eso también es un modo de fallo— sino **comparando la
columna con la fuente**. `declarado` es una traducción; el contrato en el fichero
es el hecho. Se añadió `declarado_bruto`, que sale del `re.Match` sin traducir, y
se comprobó que la traducción no invente:

```
$ rxre_contracts.py --solo-dir revkit --json | ...
  bootcheck.py   bruto=indeterminado  declarado=WRITES_FILES=indeterminado (FUERA DE VOCABULARIO)
  btfsnap.py     bruto=indeterminado  declarado=WRITES_FILES=indeterminado (FUERA DE VOCABULARIO)
  ...            (17 en total, las 17 literales)
```

Y el efecto en los recuentos fue el que delata el defecto:

| | antes del arreglo | después |
|---|---|---|
| `COINCIDE` | 31 | **44** |
| `NO_SOSTENIDAS` | 1 | 1 |
| `fuera_de_vocabulario` | *(no se medía)* | **17** |

Los 13 que desaparecieron de `NO_DETERMINED` **no se corrigieron**: cambió de
columna. Salieron de `NO_DETERMINED` porque su veredicto ya no los comparaba
contra un `no` inventado.

## La corrección

Ahora se traduce **solo si el valor está en el vocabulario cerrado**, y si no se
conserva el valor real y se marca:

```python
if bruto == "yes":       declarado = "READONLY=no, WRITES_FILES=yes"
elif bruto == "no":      declarado = "READONLY=yes, WRITES_FILES=no"
else:                    declarado = "WRITES_FILES=%s (FUERA DE VOCABULARIO)" % bruto
```

Y una declaración fuera de vocabulario **nunca** sale `COINCIDE`, porque un
valor que el validador no reconoce no puede coincidir con lo que el validador
entiende.

Tres vectores nuevos, y los tres miran el hecho:

- todo valor fuera de `yes`/`no` se **conserva literal** en la columna;
- ninguna de esas se reporta como si declarase `no`;
- una declaración fuera de vocabulario **jamás** sale `COINCIDE`.

**14 de 14 PASS.**

## Procedencia

- `STATIC` — `re.Match` del contrato en la cabecera, contra la traducción. Los
  dos campos conviven ahora en el JSON, así que la comparación es de datos y no
  de lectura.
- `COMANDO` — `python3 RXRE/tools/rxre_contracts.py --selftest` (14/14) y
  `--solo-dir revkit --json`.
- **Sin ejecución de ninguna herramienta.** Sin MMIO, sin TLB, sin insmod.
  **`GPU INTACTA`.**
- **No se ha modificado ninguna herramienta en este hallazgo**, solo el
  instrumento. Los 30 contratos de `revkit` de `1505` no se han tocado.

## Lo que NO se afirma

- **No se afirma que los 17 sean ahora correctos.** Se afirma que el informe ya
  no **afirma** una cosa distinta de la que dicen. `NO_DETERMINED` sigue siendo
  `NO_DETERMINED`: el destino de sus escrituras continúa sin resolverse.
- **No se ha tocado `_selftest_help_no_alloc.py`**, que sigue siendo el único
  `NO_SOSTENIDO` real: declara `WRITES_FILES=yes` y no tiene verbo de escritura
  propio. Hallazgo abierto de `1505`.
- **No se ha añadido `indeterminado` al vocabulario de `toolkit.py`.** Los 17
  contratos continúan siendo irreconocibles para ese validador, y eso es
  deliberado.

## Dos notas de método

**La primera: el defecto era exactamente el que el hallazgo denunciaba.**

`1505` dice, sobre `1481`: *«un número con la forma correcta y la sustancia
equivocada»*. El número con la forma correcta era `no`. La sustancia era
`indeterminado`. **Estaba en el instrumento que escribí para no mentir**, y
además en la columna cuyo único trabajo era ése.

Lo que lo delató no fue revisar el código con atención —lo escribí el mismo día
que el hallazgo— sino **guardar el dato sin traducir y comparar las dos
columnas**. Una traducción implícita es un sitio donde la verdad se pierde sin
que nadie lo note, y la forma barata de no perderla es tener las dos.

**La segunda: `INSTRUMENTO_QUE_MIENTE` es un estado que hay que poder nombrar.**

Si un instrumento miente, y su salida se cita como evidencia, entonces el
problema no es que el instrumento falle: es que **el agente que lo usa
desconfía de todo lo que dice**, incluido lo que dice bien. Por eso la
corrección no es «arreglar el `if`»: es añadir el campo bruto y tres vectores
que impidan que una traducción vuelva a decidir sola.

> un instrumento que miente no es un instrumento que falla: es uno que hace
> que sus resultados buenos dejen de ser creíbles

Y queda lo que no se ha tocado: **`tools/` tiene 3 contratos de 92**, y ahí la
columna `declarado` acaba de dejar de mentir, que es lo que hacía falta para
poder confiar en lo que diga de las 89 restantes.
