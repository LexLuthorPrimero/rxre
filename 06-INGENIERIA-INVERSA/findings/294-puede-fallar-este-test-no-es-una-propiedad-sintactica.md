# 294 · «¿Puede fallar este test?» no es una propiedad sintáctica

```text
CLASSIFICATION=MEASUREMENT+NEGATIVE_RESULT+LIMITATION · TRACK=TOOLING
CORPUS=NINGUNO (el proyecto) · HARDWARE_SCOPE=NONE
WORK_CLASS=READ_ONLY/EVIDENCE+WRITE_LOCAL · WRITE_LOCAL=PROPIOS · MODIFICATIONS_CORPUS=0
RUNTIME=NOT_RUN · GPU INTACTA · CERROJOS=0
```

## Qué resuelve

El `NEXT_ACTION` era: los tres vectores de esta sesión que no podían fallar
comparten una forma, y se puede medir sobre el propio código. Se intentó dos
veces, con dos detectores distintos, y **los dos dieron un número plausible y
falso**.

```text
  detector 1     0 de 411 vectores no pueden fallar
  detector 2   366 de 486 vectores no pueden fallar
  la verdad      3 lo fueron, y ya están corregidos
```

## 1 · Lo que había que detectar, y de dónde salió

Los tres casos, con la forma exacta que tenían en el fichero:

```text
  toalaudit   vec("...", sello(inv) != s1 or True, True)        or True
  lint        vec("...", ..., True) con el valor True literal
  govcheck    vec("...", _zz.get("decidio") not in (..., None, ""))  mas estricto
              que la regla, y por eso fallaba en verde
```

Y una cuarta forma que no es un test sino su negativa:

```text
  lint        vec("una seccion con acentos se compara sin acentos",
                  normalizar(...) == normalizar(...))

  normalizar() quita acentos como CONSECUENCIA de conservar [^A-Z0-9]
  ese test no podia fallar: ejercita una funcion donde el fallo no ocurre
```

## 2 · El primer detector no veía nada

```
  caso REAL   or True                        -> no detectado
  caso REAL   or True en dos lineas          -> no detectado
  caso REAL   se compara consigo mismo       -> no detectado
  sintetico   literal True                   -> no detectado
  sintetico   and False                      -> DETECTADO
```

Uno de cinco. Y en el árbol dio **0 de 411**, lo cual se leía como «el proyecto
está limpio» y en realidad era **ceguera**: el `or True` que busco estaba en
`toalaudit.py` hasta hace dos horas, y ese detector no lo veía.

Un detector que da 0 cuando hay un caso conocido es peor que no tener detector,
porque su salida tiene forma de dato.

## 3 · El segundo detector marcaba tres de cada cuatro

```
  vectores totales: 486   NO PUEDEN FALLAR: 366
```

Incluía **dos casos sintéticos que eran sanos**, y la causa es de una línea:

```python
  re.match(r'^\(?\s*(True|False|1|0|\'[^\']*\'|"[^"]*")\s*\)?\s*,', t)
```

`t` es el texto de la llamada **empezando por el nombre del vector**, y el nombre
es una cadena entrecomillada. El patrón comparaba contra el nombre, no contra la
expresión:

```text
  texto de la llamada   '"un vector sano", len(x) > 0)'
  mi patron             ^\( ? literal ,   ->  True

  o sea, casa con "un vector sano", no con len(x) > 0
```

Por eso salían 366: **todos los vectores del proyecto tienen nombre entrecomillado**,
o sea todos.

## 4 · La razón por la que la pregunta no tiene respuesta con grep

Las dos formas que sí se pueden ver sin evaluar —`or True` y `and False`— son
tautologías por construcción. Pero **«este test puede fallar» no es una propiedad
sintáctica**: depende de si la expresión que afirma es falsa ante el estado real
del proyecto, y eso sólo se sabe ejecutando.

```text
  la forma estatica que se puede mirar:
    "la comprobacion es una tautologia"        <- se ve

  la pregunta que hace falta:
    "si el codigo estuviera mal, este vector caeria?"   <- no se ve
```

Y hay una razón más fuerte: **una comprobación puede no ser tautológica y aun
así no poder detectar el fallo que dice detectar.** El test de `normalizar()` es
el ejemplo limpio: afirma algo cierto sobre acentos, y es cierto para siempre,
porque la función no puede tener ese fallo. No es una tautología sintáctica. Es
un test sobre una propiedad inconmovible.

## 5 · El método que sí respondió, y es el que se ha usado todo el día

**Mutación**: cambiar el código que el vector vigila, y ver si cae.

```text
  toolaudit: --check readmitido entre las candidatas   cayo CONTROL POSITIVO
  toolaudit: busqueda de rutas anulada a proposito      cayo CONTROL POSITIVO
  lint:      sombreado de 'ln' restaurado               cayo "el campo linea"
  lint:      orden de acentos revertido                 cayeron 2 vectores
  nextnum:   flock desactivado                         cayo el vector de espera
  govcheck:  'agents' vuelve a decidir                 cayeron 2 vectores
  govcheck:  terminos() vuelve a partir acentos         cayeron 2 vectores
```

Siete provocaciones, siete caídas. **Ninguna la encontró un análisis del código**;
todas las encontró alguien cambiando una cosa y mirando.

Y hay un resultado del mismo método que ningún grep daría: el primer
`--check` readmitido **no cayó ningún vector**. El segundo, ya escrito
específicamente, cayó. Eso es el valor de la mutación sobre el análisis: no
sólo encuentra el fallo, encuentra **que el vector no lo cubría**.

## 6 · Por qué no se construye la herramienta

Porque sus dos versiones existentes dan 0 y 366, y una tercera sería un número
más. La clase de `lint` que registraría esto sería, ella misma, un detector que
no puede detectar lo que dice detectar — que es exactamente el fallo que este
hallazgo describe.

`AGENTS.md` §23 dice que una herramienta que falla pasa a `TOOL_INVALID` y no se
usa como evidencia. Una tercera versión empezaría por ahí.

Lo que sí se deja es la regla, que es más corta que la herramienta:

```text
  UN VECTOR PUEDE FALLAR  <=>  al cambiar el codigo que vigila, cae

  y si nunca se ha cambiado, no se sabe. Un vector que nunca ha caido
  es un vector cuya capacidad de detectar NO ESTA MEDIDA, y eso es
  distinto de que el test sea malo.
```

## 7 · Lo que NO se establece

```text
  cuantos vectores del proyecto no pueden caer ante una mutacion
    NO_CENSADO, y no censable por analisis. Requiere mutar cada uno de los
    486 uno a uno, y cada mutacion se paga en tiempo de ejecucion de la
    herramienta entera
  si los 486 estan bien
    NO SE AFIRMA. Se sabe que 7 mutaciones Strengthening coinciden con
    vectores, y que cada uno cae sin su mutacion
  si el proyecto tiene mas vectores que no pueden caer y no se han tocado
    POSIBLE, y es la respuesta honesta. Se han buscado dos veces con dos
    metodos y los dos fallaron; la tercera búsqueda sin mutar no aportaria
  la proporcion de mutaciones que finds un fallo
    NO MEDIDA. Es un numero de mutation score, y medirlo aqui costaria mas
    que el beneficio
```

## 8 · Lo que esto cierra, y lo que abre

Cierra la pregunta «¿puede una herramienta distinguir un test que puede fallar de
uno que no puede?» con la respuesta más incómoda: **no, y los dos intentos de
demostrar que sí fallaron en direcciones opuestas.**

Abre algo más pequeño y más útil, que es la regla del apartado 6, y que no
necesita herramienta: un vector que nunca ha caído no es un vector validado. Es un
vector de capacidad desconocida. La distinción importa porque `§88` llama
`SELF_TESTED` a haber pasado los vectores, y pasar vectores nunca ha exigido
que uno de ellos caiga alguna vez.

## 9 · Trazabilidad

```text
  los tres vectores reales, y donde estaban:
    tools/../toolaudit.py    el `or True` del sello
    tools/lint.py            el valor esperado literal
    tools/govcheck.py        el vector mas estricto que la regla
    tools/lint.py:602        el test de acentos inconmovible por construccion
  siete mutaciones, con su salida, en el registro de esta sesion
  AGENTS.md §23   una herramienta que falla es TOOL_INVALID y no se usa
```

## 10 · Corrección de numeración

```text
  este fichero se escribio como 294, reservado con --reservar antes de escribir
  CORRECTED_BY: --reservar 294  RESERVADO
```