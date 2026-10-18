# 1527 — Los operadores a ciegos no podrían encontrar los vectores de `run_all.py`: 0 de 32 sitios caen, y el que sí está sobre el defecto no lo nota

```text
AUTOR=AGENTE-INSTR
FECHA=2026-10-05 10:27 -03
TIPO=FACT + LIMITACION + NEGATIVE_RESULT (no construyo la herramienta)
ESTADO=PROVEN la ceguera / PROVEN que la capacidad existente NO alcanza
ALCANCE=tools/mutscore.py y 08-ARQUITECTURA/tools/run_all.py.  SOLO LECTURA
  + copias temporales fuera del arbol para ejecutar mutantes.
PRECEDE_A=1526 (los 12 vectores de run_all que no pueden fallar)
ENCADENA=1526 (los vectores no pueden fallar -> ¿puede el
  Detector de mutaciones del proyecto notarlo?  -> medido: NO, y por que
  -> y por eso NO se construye la herramienta que habia planeado
```

## La pregunta que `1526` dejó abierta, y el plan que casi construyo

`1526` demostró que 12 vectores de `run_all.py` no pueden fallar. Mi plan era
construir un detector de vectores inertes: algo que leyera las tuplas
`(label, args, want_lines, rc_tol)` y dijera cuáles aceptan su propia negación.

Antes de escribirlo, la pregunta por la que `mutscore.py` documenta haber
pasado — con dos detectores manuales que dieron **0 de 411** y **366 de 486**,
ambos falsos, en direcciones opuestas — es:

> **¿existe ya esa capacidad?** `mutscore.py` mide si un vector cae ante una
> mutación, que es exactamente lo que necesito. Y `mutscore.py` no la inventó:
> su docstring cita esa lección como la razón de ser de la herramienta.

Así que lo medí antes de escribir una línea.

## Lo que hay, y lo que cubre

```text
ALCANCE_CIEGO = ("tools/govcheck.py", "tools/nextnum.py", "tools/lint.py",
                 "tools/fingerprint.py", "08-ARQUITECTURA/tools/toolaudit.py")
```

Cinco ficheros. **`run_all.py` no está**, y `grep -n 'run_all' tools/mutscore.py`
no devuelve nada.

Lo primero que parecía la explicación —«no está en el alcance»— es lo de menos.
El alcance se amplía adding una ruta. La pregunta real es otra: **¿generarían los
operadores, sobre ese fichero, la mutación que hace falta?**

## Los tres operadores, sobre `run_all.py`

```text
  NEG_COND   17 sitios
  SWAP_CMP    9 sitios
  RET_NONE    6 sitios
```

(contra 61 / 26 / 31 en `tools/nextnum.py`, que sí está en el alcance). El
corredor **sí produce sitios**, así que la capacidad no está bloqueada por
falta de candidatas.

Y hay un resultado que parece bueno y es lo contrario. `NEG_COND` genera sitios
en la línea 82:

```python
82:  if ok and rc_tol is not None and rc not in (0, rc_tol):
```

Esa línea es, literalmente, el sitio donde vive el defecto. El operador la ve,
la toca, produce un mutante plausible… **y el vector sigue verde.** Está en
`1526`: esa lógica es inalcanzable porque `ok` ya es `False` cuando `rc=3`, y
el propio docstring de `run()` lo explica. El operador produce ahí un mutante
**estéril por construcción**, y no puede saberlo.

## La medición que lo cierra

Apliqué los 32 sitios a una **copia temporal** de `run_all.py` y ejecuté el
vector real de `fingerprint --self-test` con la función de ellos:

```text
mutaciones candidatas en run_all.py: 32
sitios que HACEN CAER el vector: 0 de 32
sobrevivientes: 32
ejemplos: [('NEG_COND',82), ('NEG_COND',107), ('NEG_COND',111),
           ('NEG_COND',113), ('NEG_COND',133), ('NEG_COND',493), ...]
```

**Cero de treinta y dos.** Ni uno. Y no es casualidad ni falta de sitios: es
que la mutación que este defecto necesita **no pertenece a la clase que los
operadores mutan**.

| | la mutación que hace falta |
|---|---|
| forma | `rc_ok=[0, rc_tol]` → `rc_ok=[0]` |
| qué es | un **literal dentro de una lista** |
| `NEG_COND` | añade `not` a un `if` |
| `SWAP_CMP` | voltea `==` / `!=` |
| `RET_NONE` | borra un `return` |

Ninguno de los tres toca una lista de enteros. **La capacidad que falta es
específica de la forma del defecto, y no es la que existe.**

Y hay una segunda razón, más honda que la anterior, y la dejó ver el propio
`mutscore.py` en su docstring:

```text
NO comprueba que una herramienta diga la verdad. `toolcheck.py:187` lo dice de si
mismo, y esta herramienta tiene el mismo limite: comprueba que un vector CAIGA
ante una mutacion, y no que el vector mire lo que dice mirar.
```

Mutando `run_all.py` se pregunta «¿el vector cae?». Pero el vector que hay que
probar es **`fingerprint.py` roto**, y `run_all.py` es el que **decide si se
nota**. La mutación correcta —la que lo demuestra— es sobre la *herramienta*:

```
fingerprint.py --self-test   inyectado con una FALLA   ->  rc=1
run_all vector con rc_ok=[0,1]                          ->  ok=True
```

Eso es exactamente lo que hice en `1526`, y por eso se sabe. La lección es que
**mutar el corredor y mutar la herramienta son cosas distintas**, y para este
defecto hace falta lo segundo.

## Lo que NO construí, y por qué

No escribí el detector de vectores inertes, y esa decisión viene de la
medición, no del cansancio:

1. **`mutscore.py` cubre el mecanismo que ya existe.** Añadir `run_all.py` a
   `ALCANCE_CIEGO` daría 32 sitios que **no detects**, y un informe con 32
   supervivientes sería ruido que oculta el problema real.
2. **El defecto es un literal en una lista**, fuera de los tres operadores.
   Habría que escribir un cuarto operador de purpose único, y con un solo
   fichero consumidor.
3. **El instrumento que hace falta es de otra clase**: no «¿el vector cae?» sino
   «¿`rc_ok` acepta el rc que la herramienta devuelve al fallar?». Eso se
   comprueba leyendo `rc_tol` y el contrato del flag, que es análisis estática
   pura — y eso **no es `mutscore.py`**, es otra herramienta, con otro nombre y
   otro contrato.

Construirla ahora, sin medir primero cuántos de los 12 son realmente inertes de
forma distinta, sería §98: automatización para poder decir que existe.

## Procedencia

- **Ejecución, no lectura**, para el 0 de 32: copia temporal fuera del árbol,
  `importlib` sobre la copia, llamada a `run_all.run()` con los argumentos
  exactos del vector. Nada del árbol de fuentes fue modificado.
- `CROSS-CHECK` del alcance: por `grep` (`run_all` ausente de `mutscore.py`) y
  por lectura de `ALCANCE_CIEGO` (5 rutas, `run_all.py` no entre ellas).
- **control de validador**: el mismo experimento contra `tools/nextnum.py`,
  que sí está en el alcance, para no atribuir a los operadores una ceguera que
  fuera del mutador. Salida: 61/26/31 sitios, frente a 17/9/6.
- `NEGATIVE_RESULT` — no se construyó la herramienta, y queda escrito por qué.
- `NOT_DETERMINED` — cuántos de los 12 vectores son inertes **por el mismo
  mecanismo** (`rc_tol=1`) frente a otros. Está medido que los 12 lo son; no
  está medido que no haya un segundo mecanismo. **Cero escrituras en hardware.**

## Nota

El plan de este turno era escribir un detector. La medición de media hora lo
descartó, y el valor de esto está en eso y no en el detector:

> Si hubiera añadido `run_all.py` a `ALCANCE_CIEGO` sin medir, el informe
> habría dicho «32 sitios, 32 supervivientes» y yo habría escrito que el
> problema era que el corredor estaba fuera del alcance. Habría sido verdad
> sobre el informe y falso sobre la causa, que es la forma más común de
> cerrar mal una frontera.