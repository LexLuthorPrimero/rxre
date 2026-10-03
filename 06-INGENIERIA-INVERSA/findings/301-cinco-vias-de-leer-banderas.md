# 301 · Hay cinco vías de leer banderas, y ninguna era `add_argument` salvo una

```text
CLASSIFICATION=MEASUREMENT+TOOL+ERROR · TRACK=TOOLING
CORPUS=NINGUNO (el proyecto) · HARDWARE_SCOPE=NONE
WORK_CLASS=READ_ONLY/EVIDENCE+WRITE_LOCAL · WRITE_LOCAL=PROPIOS · MODIFICATIONS_CORPUS=1
RUNTIME=NOT_RUN · GPU INTACTA · CERROJOS=0
```

## Qué resuelve

El `NEXT_ACTION` de `300` era una herramienta del proyecto que hiciese lo que un
script de un solo uso hizo mal: sacar las banderas de todas las herramientas por
**las dos vías** que existen, y **decir cuántas no ha podido clasificar** en vez de
callarse.

Antes de escribirla había una pregunta de una línea que era mía y sin comprobar:
si el control de corpus habría visto mi cambio en `gmmio_inventory.py`.

## 0 · La pregunta de una línea: `NOT_APPLICABLE`

```text
  corpus_guard.py:51   "RESEARCH/working/linux-7.1.3"
  toolkit.py:87        CORPUS_PATH = re.compile(r"RESEARCH/working|linux-7\.1\.3")
```

El corpus del proyecto, por la definición de sus propios dos validadores, es **una
ruta**: el árbol del kernel en `RESEARCH/working/`. `08-ARQUITECTURA/tools/` es
código del proyecto, no corpus, y lo que está versionado lo cubre `git`.

```text
  la edicion de gmmio_inventory.py estaba FUERA del corpus por definicion
  el control de corpus no deberia avisar, y no avisa: correcto
  MODIFICATIONS_CORPUS=1 en la cabecera, y 1 significa "codigo del proyecto",
  no "el corpus del kernel"
```

Pregunta cerrada. Y el patrón del `CONTRACT` lo dice solo: `MUTATES_CORPUS=no` en
`gmmio_inventory.py` era correcto.

## 1 · La herramienta, y por qué tiene que clasificar en vez de contar

`tools/flags_inventory.py`, 17 vectores, `CONFORME` según
`toolcheck.REQUIRED_MARKS` (las cuatro marcas: `WORK_CLASS`, `WRITE_EXECUTION`,
`VERSION`, `LIMITACIONES`).

Lo que la distingue de un `grep -- "--"` no es que encuentre más: es que **cada
cadena va a una clase, y hay una clase para lo que no sabe**.

```text
  ARGUMENTO       se la pasa a add_argument              460
  MANUAL          comparada contra algo de sys.argv      171
  DELEGADA        se la pasa a un hijo (git, otro .py)     37
  PROSA           esta dentro de un docstring             412
  SIN_CLASIFICAR  no encaja en ninguna de las cuatro      311
  ....................................................................
  TOTAL                                                  1391
  ficheros 151   herramientas con error de parseo: 0
```

Y el número del cajón es el que vale, porque es donde la herramienta **no sabe** y
por lo tanto no debe afirmar.

## 2 · El resultado: cinco vías, y solo una era la que se buscaba

```text
  via 1   ap.add_argument("--json", ...)            460 banderas    la que buscaba
  via 2   if "--strict" in args                      171 banderas    toolkit, y 30 mas
          args = sys.argv[1:]
  via 3   argv.index("--depth")                    NO CONOCIDA
  via 4   a.startswith("--commits")                 NO CONOCIDA
  via 5   if a == "--quick": elif a == "--full"     NO CONOCIDA
  via 6   ("--" + f) in args                       POR CONSTRUCCION IMPOSIBLE
```

Las tres desconocidas, con su fichero y su línea:

```text
  aperture.py          L283   rel = argv[argv.index("--cabecera") + 1]
  causal_chain.py      L232   i = sys.argv.index("--depth")
  causal_map.py        L438   objetivo = args[args.index("--claims") + 1].lower()
  commitmsg_lint.py    L114   if any(a.startswith("--commits") for a in argv):
  driver_offsets.py    L428   base = argv[argv.index("--fichero") + 1]
  causal_chain.py      L275   reg = opt("--register")
  bench.py             L874   if a == "--quick":
```

Y `asic_table.py:259` tiene `if ("--" + f) in args:`, que **no se puede clasificar
por construcción**: la bandera no existe como constante en el fuente, se construye
en tiempo de ejecución. Esa no es una limitación del extractor: es una limitación
de lo que el fuente declara.

```text
  UNA HERRAMIENTA QUE CONSTRUYE SU BANDERA NO TIENE BANDERAS EN EL FUENTE
  TIENE UN CONSTRUCTOR DE BANDERAS, Y ESO NO LO VE NINGUN ANALISIS ESTATICO
```

## 3 · Y la herramienta contradijo una cuenta mía

El vector decía que `toolkit` tiene siete banderas propias, y la cuenta de siete
venía de un `grep` mío. **La herramienta dice cinco.**

```text
  --register          L359   if "--register" in args
  --selftest-ajenas   L396   if "--selftest-ajenas" in args
  --strict            L491   strict = "--strict" in args
  --table             L559   if "--table" in args or not args
  --sin-fallar        L624   if "--sin-fallar" not in args
```

Y las otras dos que yo contaba, con su clase:

```text
  --write            L237   if "--write" not in txt:
                             busca ESA CADENA en el contenido de otra
                             herramienta, para auditar su tabla de sysfs
                             -> SIN_CLASIFICAR, y NO es propia

  --error-unmatch    L275   git ls-files --error-unmatch rel
                             es un argumento de git
                             -> DELEGADA
```

Un `grep` no puede distinguir una bandera propia de una cadena que la herramienta
busca en el fichero de otro. Es la misma razón por la que `298` metió `--self` en
la fila de `toolkit`, y la herramienta ha pagado 169 líneas de error por ese mismo
motivo.

```text
  298   303 lineas, una fila con una bandera que no existe
  300   472 lineas, la fila corregida
  301   612 banderas propias en 151 ficheros, y el self-test que lo comprueba
```

## 4 · Cuatro fallos míos en la herramienta, y uno solo lo vio la mirada

Todos los vector los encontraron. El cuarto no.

### Uno · `anota` recibía `clase` y no lo usaba

```python
  def anota(lineno, clase, como):
      if clave not in vistos:
          vistos[clave] = {"linea": lineno, "clase": None, ...}
                                    ^^^^^^ el parametro existe y se ignora
```

937 banderas encontradas, **937 sin clasificar**. El resumen del propio
self-test lo decía en una línea y yo estaba mirando a los vectores.

### Dos · En `if "--strict" in args:` miraba el lado equivocado

La bandera está a la **izquierda** de la comparación y el nombre de `argv` a la
derecha. El código busco el nombre en `n.left`, que es una `Constant`. Resultado:
cero `MANUAL` en todo el proyecto.

### Tres · Un docstring es un nodo `Constant`, y su valor no empieza por `--`

Es un solo nodo con texto multilínea. `valor.startswith("--")` sobre el nodo entero
no puede encontrar nunca nada dentro. Ahora se busca con `findall` dentro del texto,
que es lo que un docstring es.

### Cuatro · `---` no es una bandera, y yo lo contaba

```text
  binfacts.py     L254   print("--- SIMBOLOS ---")
  corpus_guard.py L259   print(f"--- comando devuelto {r.returncode} ---")
  docscan.py      L69    print("--- CADENAS ---")
```

Un predicado `startswith("--")` los acepta. Ahora exige **letra detrás** de los dos
guiones, con un único `_es_flag()` usado por las cuatro vías:

```text
                     antes    despues
  TOTAL               1425      1386
  SIN_CLASIFICAR       348       311
  MANUAL               170       169
  DELEGADA              39        36
```

Y este **no lo encontró ningún vector**, porque ningún vector sintético tenía un
separador ASCII. Salió al leer la salida, no el recuento. Un vector por
separador, y comprobado: **quedan 0 entradas que sean un `---`**.

### Y un vector mío que pasaba por la razón equivocada

```python
  v("--write NO es propia", clases.get("--write") not in ("ARGUMENTO", "MANUAL"))
```

`dict.get` devuelve `None` tanto si el valor **es** `None` como si la clave **no
existe**. El vector daba verde con la entrada desaparecida, que es justo lo que no
puede hacer un vector. Ahora exige presencia:

```python
  v("--write esta PRESENTE y NO es propia",
    "--write" in clases and clases["--write"] not in ("ARGUMENTO", "MANUAL"))
```

## 5 · El discriminante que declaré apuntaba al sitio equivocado

Escribí: «si alguna herramienta sale con cero banderas **y** el clasificador dice
que la ha mirado, entonces hay una tercera vía de lectura que nadie ha encontrado».

Resultado:

```text
  herramientas con CERO banderas propias: 18
```

Y esas 18 no son evidencia de una tercera vía: son herramientas sin banderas, que
es un hecho normal. **El cero no distingue nada.** El discriminante apuntaba a un
observable que no puede separarse.

Donde sí apareció la tercera vía es en `SIN_CLASIFICAR`, y no como una cifra sino
como una lista con fichero y línea. Esa es la lección del método, y es la quinta
vez de la misma serie:

```text
  EL RECUENTO DICE QUE HAY UN PROBLEMA
  Y LA LISTA DICE CUAL ES EL PROBLEMA
  Y SOLO CON LA LISTA SE PUEDE ACTUAR
```

## 6 · Lo que NO se establece

```text
  por que PROSA ha pasado de 408 a 412
    NOT_DETERMINED. Entre las dos mediciones lo unico que cambio fue el predicado
    `_es_flag` en las tres vias de codigo, que no toca la rama de docstrings. El
    invariante que SI se ha comprobado es que no hay entradas duplicadas
    (linea, clase, clave): 0 en las 1391
  si las 311 sin clasificar son todas banderas propias
    NO, y NO SE SABE CUANTAS LO SON. Hay al menos cinco vias no reconocidas y una
    que es imposible por construccion. El numero 311 es un techo de lo que esta
    herramienta no alcanza, no una cuenta de banderas escondidas
  cual es la bandera de self-test de cada herramienta
    DATO, NO HECHO. 106 de 148 tienen candidato segun el criterio "contiene test
    o self", y el criterio esta escrito en el codigo y es visible. `check_chain`
    aparece con DOS `--self-test`, en lineas distintas, y no se ha mirado por que
  que hacen esas 18 herramientas sin banderas propias
    SIN MIRAR. `atomrom`, `causa`, `cn7`, `cn8`, `correlate`, `estado`,
    `frame_budget`, `gmmio_inventory`, `ibpools`, `ibtrace`, `pm4_layout_audit`...
  si las banderas que extrae FUNCIONAN
    NO ESTA COMPROBADO, y es el limite declarado. Que `--strict` este en el fuente
    no dice que la ruta que abre no reviente. Eso lo comprueban los vectores de
    ruta de cada herramienta, que son otra cosa
```

## 7 · Trazabilidad

```text
  tools/flags_inventory.py            la herramienta, 17 vectores, CONFORME
  tools/toolcheck.py:57               REQUIRED_MARKS, las cuatro que faltaban
  08-ARQUITECTURA/tools/corpus_guard.py:51   lo que el corpus es, y por quien
  08-ARQUITECTURA/tools/toolkit.py:87        lo mismo, por la otra via
  tools/fingerprint.py:59             el docstring de gmmio, y el arreglo de 300
```

## 8 · Corrección de numeración

```text
  este fichero se escribio como 301, reservado con --reservar antes de escribir
  CORRECTED_BY: --reservar 301  RESERVADO
```
