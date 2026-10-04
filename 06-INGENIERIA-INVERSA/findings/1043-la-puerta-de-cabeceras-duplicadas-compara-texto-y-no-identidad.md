# 1043 · La puerta de cabeceras duplicadas compara texto, no identidad, y es ciega al caso peligroso

`CLASSIFICATION=MEASUREMENT` · `TRACK=STATIC`
`CORPUS=N/A` · `HARDWARE_SCOPE=N/A` (ningún acceso a hardware)
`WORK_CLASS=READ_ONLY` · `WRITE_EXECUTION=ESCRIBE` (escribe solo en temporales) · `MODIFICATIONS=1`
`GPU INTACTA` · `MODIFIES_CODE=SI` (`revkit/cn8.py`)

---

## La pregunta

Un nodo concurrente, al atribuir entradas del ledger, encontró que `revkit/cn8.py`
tiene un control de cabeceras duplicadas escrito así:

```python
DEUDA_DUPES = {"TOOLS-STATUS.md"}
...
chk("docs/: las cabeceras duplicadas son solo las que ya se sabian",
    set(dupes) == DEUDA_DUPES, ...)
```

Con `==`, **haber pagado la deuda es una FALLA**. Y el mismo fichero, treinta
líneas antes, usa la polaridad correcta en el control hermano:

```python
DEUDA_FENCES = {"EVIDENCE-MATRIX.md", "MASTER-RESEARCH-STATUS.md"}
...
impares <= DEUDA_FENCES,                      # línea 508
_pagadas = sorted(DEUDA_FENCES - impares)     # línea 513
```

Es el **tercer** caso del mismo defecto en este árbol: una lista de deuda
acreditada que se comprueba con igualdad exacta en vez de con inclusión.

## MEDIDO

### 1. El rojo falso, y es exactamente lo que se diagnosticar

Estado antes del cambio, sobre el árbol real:

```
$ python3 revkit/cn8.py
    FALLA docs/: las cabeceras duplicadas son solo las que ya se sabian
          (con duplicados ahora: []; deuda acreditada: ['TOOLS-STATUS.md'])
```

`set(dupes) == []` porque el duplicado ya **no está** —`## TL-46` estaba escrito
dos veces byte a byte en `docs/TOOLS-STATUS.md`, un nodo lo reparó, y desde entonces
no hay ninguno—. Contra `DEUDA_DUPES = {'TOOLS-STATUS.md'}` eso es `False`.

**La puerta no había encontrado un defecto: había encontrado que el defecto que
buscaba ya no estaba.** Un control que se enciende porque su propia deuda está
pagada entrena a leer sus reds como hallazgos reales.

### 2. El arreglo, validado en las dos direcciones

`| DEUDA_DUPES` con informe de lo pagado, por el patrón de la línea 508:

| escenario | antes | después |
|---|---|---|
| árbol real, `TL-46` reparado, 0 duplicados | **ROJO** | **VERDE** + `info: deudas YA PAGADAS` |
| la deuda vuelve | VERDE | VERDE |
| **duplicado nuevo en un fichero NO acreditado** | ROJO | **ROJO** + `sin acreditar: ['EVIDENCE-MATRIX.md']` |

Lo tercero es la dirección que importa y **no se ha perdido**: un duplicado que no
estaba en la lista sigue saltando, y ahora el mensaje nombra cuál es.

Y esto pasó de `DERIVED` a `VALIDATED` porque **se ejecutó** `cn8.py`. Declaraba
`WRITE_EXECUTION=ESCRIBE`, y eso parecía una razón para no correrlo. MEDIDO que las
**19 escrituras del fichero van a temporales** —`_td3`, `_td4`, `td`— y que
`AQUI` solo se lee:

```
_raiz = os.path.join(_td3, "arbol")
copia = os.path.join(td, "atomrom_malo.py")
_r2   = os.path.join(_td4, "repo")
```

Es decir: la declaración es **conservadora**, no falsa. "Escribe" es cierto; lo que
no se comprobaba era *dónde*. Una declaración que no se puede usar para decidir si
algo es seguro es una declaración a medias: empuja a no medir.

### 3. Y el defecto que el arreglo NO arregla: es ciega al caso peligroso

`cn8.py` compara **texto de cabecera**, no **identidad de entrada**. MEDIDO con dos
vectores idénticos salvo en cómo se reinserta la entrada:

| vector | qué se hace | qué ve `cn8.py` |
|---|---|---|
| A | cabecera reinsertada **byte a byte** | la ve |
| B | mismo `## TL-nn`, **otro cuerpo** | **VERDE, no ve nada** |
| C | mismo `## TL-nn`, anexo que cita otra herramienta | VERDE, y además una documentada se pierde del inventario |

MEDIDO en el árbol real, caso B:

```
$ python3 revkit/cn8.py        # tras insertar "## TL-NN" repetido con otro cuerpo
    OK    docs/: las cabeceras duplicadas son solo las que ya se sabian
```

**El caso histórico A era el benigno.** El que falta es el malo: cuando se
duplicó el `TL-46` lo que se duplicó fue el bloque entero —cabecera y cuerpo—, así
que el vector A era el que se dio. Un caso B no se parece a nada que haya pasado
aquí, y por eso la puerta nunca lo vio.

Y hay un tercer defecto en el mismo sitio, de la misma familia: cuando una entrada
duplicada **contiene** una entrada válida, la segunda absorbe a la primera porque
`docs_index()` parte por cabeceras y guarda en un `dict`. Eso es lo que produjo las
**13 atribuciones erróneas** que el nodo de atribución midió y reparó. Es decir: la
duplicación no era un defecto de bookkeeping, era la causa de un defecto de
atribución.

## LO QUE ESTA REGISTRADO Y LO QUE NO

**Arreglado:** la polaridad, en las dos direcciones verificadas.

**No arreglado y declarado:** la ceguera al caso B. Arreglarla es comparar el
*número* de la entrada y no su texto, y eso cambia lo que el control mide —de
"cabecera repetida" a "entrada repetida"—, así que no se ha hecho aquí.

**No es de este hallazgo, pero está en el mismo fichero y sale de la misma
ejecución:** otros dos controles de `cn8.py` fallan hoy y no tienen que ver con esto:

```
FALLA  unidad de los clocks CORROBORATED con el VBIOS real (rc=4)
FALLA  huerfanos recorre el corpus (leidos=307)
```

`rc=1` en ambos casos, antes y después. No los he tocado: son de otro nodo, y un
`rc=1` que uno se lleva puesto sin mirar los otros dos controles es exactamente el
defecto que este hallazgo describe.

## POR QUÉ ESTO ESTÁ SEPARADO DEL HALLAZGO DE ATRIBUCIÓN

Porque son dos preguntas y se responden con dos instrumentos:

- **¿A qué entrada pertenece esta herramienta?** `toolreg.tl_ownership()`, y su
  regla son tres niveles donde el tercero —mención— no atribuye, y un empate en el
  mismo nivel **no se elige**: se reporta el conjunto.
- **¿Esta entrada está duplicada?** `cn8.py`, que hasta ahora comparaba texto y
  ahora compara pertenencia a la deuda.

El primero ya no atribuye mal. El segundo no ve el caso que falta. Y un control que
no ve su propio caso de fallo no puede usarse para afirmar que el defecto está
cerrado: solo que el síntoma que motivó el arreglo ya no aparece.

## LO QUE NO ESTÁ HECHO

- El caso B sigue sin detección. La condición concreta: `cn8.py` construye `_seen`
  por **texto de cabecera**; debería hacerlo por el **número** que la cabecera
  declara.
- La lista `DEUDA_DUPES` se puede **podar** —el mensaje lo dice—, y no se ha podado.
  Podarla es correcto ahora,  pero es la clase de cambio que hace que un control
  un dia deje de mirar,  y merece su propio commit con su propia medicion.
- Los otros dos controles de `cn8.py` que fallan  —`unidad de los clocks`  y
  `huerfanos recorre el corpus`—  no son de este hallazgo y no se han tocado.
