# 300 · `--self` no era el self-test de `toolkit`, y por eso las 303 de `298` eran 472

```text
CLASSIFICATION=ERROR+MEASUREMENT+NEGATIVE_RESULT · TRACK=TOOLING
CORPUS=NINGUNO (el proyecto) · HARDWARE_SCOPE=NONE
WORK_CLASS=READ_ONLY/EVIDENCE+WRITE_LOCAL · WRITE_LOCAL=PROPIOS · MODIFICATIONS_CORPUS=0
RUNTIME=NOT_RUN · GPU INTACTA · CERROJOS=0
```

## Qué resuelve

El `NEXT_ACTION` de `299` eran los vectores de ruta de `fingerprint` y `toolkit`,
más una pregunta que había quedado abierta: por qué el inventario de banderas
salía **vacío** para `toolkit`, y qué significa el `rc=1` de `toolkit --self`.

Las tres cosas están contestadas, y la segunda era un **error en un hallazgo ya
escrito**.

## 1 · La pregunta del inventario: no usa argparse

`toolkit` lee `sys.argv[1:]` a mano y compara con `in`:

```python
  356  def main():
  357      args = sys.argv[1:]
  359      if "--register" in args:
  396      if "--selftest-ajenas" in args:
  491      strict = "--strict" in args
  559      if "--table" in args or not args:
  624          if "--sin-fallar" not in args:
```

De las tres hipótesis del `NEXT_ACTION` —otra forma de `add_argument`, lectura a
mano, o Bandera inexistente— **la correcta es la segunda**: lectura a mano. Y el
inventario no dijo «no hay banderas», sino que **buscó en el sitio equivocado y
no lo dijo**. Es el fallo de `296` y `299` por tercera vez: una regla que no
cubre un caso, y el caso cae en el cajón de «nada» en vez de decir «no he mirado
aquí».

## 2 · El error: `--self` no existe en `toolkit`

Y esto es lo que importa, porque `--self` es lo que se puso en la tabla de
`298`.

```text
  toolkit --self               rc=1    cae en la ruta de INFORME
  toolkit --table              rc=1    ruta de informe
  toolkit --strict             rc=1    ruta de informe
  toolkit --selftest-ajenas    rc=0    ESTE es el self-test
```

`--self` no está en la lista de arriba. Al no ser `--register`, ni
`--selftest-ajenas`, ni tener `--table`, cae en el `if ... or not args` de la
línea 559 y ejecuta **el informe entero**, y sale con `rc=1` informando de quince
herramientas ajenas.

O sea que la fila de `toolkit` en la tabla de cobertura de `298` no comparaba
self-test contra banderas. **Comparaba informe contra banderas.** De ahí que
dijera 241 líneas de self-test y 4 nuevas: el «self-test» era el propio informe.

Con la bandera buena:

```
                       298 (con --self)      300 (con --selftest-ajenas)
  self-test                     241                       129
  + banderas                   246                       259
  NUEVAS                         4                       173
  total                        246                       302
```

```text
  LAS 303 DE 298 ERAN 472
```

Y el desglose correcto de las 472:

```
  herramienta            self-test + banderas  NUEVAS   total
  lint.py                       376         217       53     429
  nextnum.py                    231          86       32     263
  govcheck.py                   347         392      143     490
  fingerprint.py                179         172       71     250
  toolkit.py                    129         259      173     302
  ...................................................................
  LINEAS QUE EL SELF-TEST SOLO NO EJECUTABA Y SI:  472
```

**`298` no se corrige.** Los hallazgos escritos no se reescriben, y menos cuando
el error no está en el texto sino en una cifra que alguien pueda reutilizar. Esto
es la corrección, con la causa y con las dos cifras.

### Y de paso: `toolkit` no puede combinar su self-test con una bandera

```text
  --selftest-ajenas   corta en el `return` de la linea 456
  --strict            se lee en la linea 491
  --sin-fallar        se mira en la linea 624
```

O sea que `toolkit --selftest-ajenas --strict` **no prueba `--strict`**: se sale
antes. Por eso los vectores de ruta de `toolkit` lanzan otro proceso y no
extienden la lista de argumentos, y está escrito en el bloque para que no se
«simplifique» después.

## 3 · Un `SyntaxWarning` que salía en cada ejecución, y no estaba donde decía

`toolkit --self` escribía en stderr, en cada llamada:

```
  <unknown>:91: SyntaxWarning: "\w" is an invalid escape sequence.
```

`<unknown>` no es `toolkit.py`. `<unknown>` es el nombre que `ast` da al código
que compila desde una cadena, y `toolkit.py:298` hace justo eso:

```python
  298      tree = ast.parse(txt)
  299      d = ast.get_docstring(tree)
```

`toolkit` parsea **las 59 herramientas** del directorio para leer su contrato. El
defecto estaba en el fichero que analysaba, no en el que analysizaba. Y el
autorreportarse era el único camino para verlo: la herramienta que valida a todas
las demás es la que más escupe ruido.

```text
  gmmio_inventory.py:79   """{REG: {CAMPO: (mask, shift)}} desde un header _sh_mask.h.
  gmmio_inventory.py:91   queda '_MASK'. Ademas (\w+) incluye '_', asi que el separador...
```

La 91 es **prosa dentro de un docstring**, no una expresión regular: el texto
explica por qué `(\w+)` desambigua el campo del registro, y al escribirlo sin
comillas crudas Python avisa.

### Arreglado, y probado que no cambia nada

Añadir la `r` delante de las tres comillas no es lo de siempre: si dentro hubiera
`\"` o `\\`, el texto **renderizado** cambiaría, y ese texto lo lee `toolkit.py:299`
con `ast.get_docstring`. Así que la pregunta no era «¿compila?», sino «¿queda
igual?», y se responde comparando el valor parseado del original con el de una
copia a la que solo se le añade una letra:

```text
  docstring del original    L79..L101    1248 chars
  docstring con la r        L79..L101    1248 chars
  ¿el texto sale IGUAL?     SI, IDENTICO
  ¿queda algún SyntaxWarning? no queda ninguno
```

Y el barrido del árbol entero, con el fichero abierto y cerrado bien:

```text
  ficheros analizados: 148
  con SyntaxWarning o SyntaxError: 0
```

### Y casi cuento 148 defectos que eran míos

El primer barrido dio **`ResourceWarning` en L8 de los 148 ficheros**. Eso lo
produce el propio barrido, que abría los ficheros sin cerrarlos y además activaba
`simplefilter("always")`. Ciento cuarenta y ocho herramientas «defectuosas» que
no lo eran.

```text
  294  un detector que da una cifra Iso se mira primero a si mismo
  300  y en este caso la cifra era 148, y era mentira
```

## 4 · El vector que escribí estaba mal, y lo supe porque lo provoqué

Los vectores de ruta comprueban «no revienta». Provocados de cuatro maneras:

```
  caso                                rc    detectado
  el original, sin tocar              0/1   (correcto: OK)
  A) raise en la ruta de informe      1     SI
  B) sintaxis rota en el modulo       1     NO  <-- SE CUELA
  C) exit codigo 97, imposible        97    SI
```

**B se colaba.** Una herramienta con la sintaxis rota sale con `rc=1`, escribe
`SyntaxError` en stderr, y **no escribe traceback**. Un predicado que buscase
solo el traceback la daba por buena. Y un módulo que no compila es el peor caso
posible: no se puede ni cargar.

Reforzado a siete marcas más la salida no vacía:

```python
  MARCAS_DE_ROTO = ("Traceback (most recent call last)", "SyntaxError",
                    "IndentationError", "TabError", "NameError",
                    "AttributeError", "ImportError")
  ... and (_pr.stdout or "").strip() != ""
```

Y vuelto a provocar, ahora en las dos herramientas:

```
  fingerprint.py  SIN TOCAR   rc=0   OK
     raise en la ruta   rc=1   detectado=SI
     sintaxis rota      rc=1   detectado=SI
     rc imposible       rc=97  detectado=SI
     imprime nada       rc=0   detectado=SI
  toolkit.py       SIN TOCAR   rc=1   OK
     raise en la ruta   rc=1   detectado=SI
     sintaxis rota      rc=1   detectado=SI
     rc imposible       rc=97  detectado=SI
     imprime nada       rc=1   detectado=SI
```

Las dos herramientas intactas pasan, y las ocho provocaciones se detectan.

## 5 · Y el discriminante que había predicho no era el bueno

El `NEXT_ACTION` decía: «`mutscore --cobertura` tiene que subir la columna
`NUEVAS` de `fingerprint` de 71». **No sube. Sigue en 71.**

Porque los vectores de ruta lanzan un **subproceso**, y el `settrace` del padre no
ve al hijo. Es el mismo tropiezo de `297`, y la cuarta vez que sale:

```text
  297  un test que delega en un proceso y no observa el proceso
  299  y un auditor que delega en el audited
  300  y un vector que delega en un subproceso TAMPOCO anade cobertura,
       aunque si anade deteccion
```

Que es la distinción que faltaba y que conviene escribir:

```text
  UN VECTOR DE RUTA COMPRA DETECCION, NO COBERTURA
    si la ruta de informe se rompe, el self-test lo dice
    y no por eso el self-test ejecuta mas lineas de las que ejecutaba
  LA COBERTURA LA COMPRA --cobertura, que traza al hijo
```

El self-test de `fingerprint` pasó de 171 a 179 líneas, que son las del propio
bloque del vector y nada más.

## 6 · Lo que NO se establece

```text
  si el inventario de banderas debe aprender a leer argv a mano
    NO DECIDIDO. Se ha comprobado que `toolkit` es el unico de las cinco
    herramientas de la suite, pero no se ha mirado quantas de las otras 124
    herramientas del proyecto hacen lo mismo. Y el inventario que lo meas
    era un script de /tmp, no una herramienta del proyecto: no existe
  las 169 lineas de diferencia entre 303 y 472
    MEDIDAS y de donde salen: la fila de toolkit. 129 en vez de 241 de
    "self-test", y 173 nuevas en vez de 4. Lo que pasa es que `--self` era el
    informe, y comparar el informe contra las banderas da una diferencia
    pequena que no queria decir nada
  el resto de las 124 herramientas
    SIN MEDIR. De ellas solo se sabe que 15 estan SIN VERSIONAR, que es lo que
    informa el propio toolkit
  si el SyntaxWarning era el unico defecto de ese genero
    NO. El barrido solo miraba `SyntaxWarning` y `SyntaxError`. No ha mirado
    DeprecationWarning, ni ResourceWarning en condiciones reales, ni los avisos
    que aparecen al EJECUTAR y no al parsear
  gmmio_inventory: si el arreglo es el unico posible
    No hace falta que lo sea. Es el que no cambia el texto, y eso esta medido
```

## 7 · Trazabilidad

```text
  /tmp/opencode/docstring_crudo2.py   la comparacion del docstring, con ast
  /tmp/opencode/provocar_ruta.py     las cuatro provocaciones, la primera vez
  /tmp/opencode/reforzar_ruta.py     el predicado reforzado
  tools/fingerprint.py               vector de ruta, 20 -> 22 comprobaciones
  08-ARQUITECTURA/tools/toolkit.py   vector de ruta en --selftest-ajenas
  08-ARQUITECTURA/tools/gmmio_inventory.py:79   la r, unica modificacion de corpus nulo
  tools/mutscore.py                  CASOS_COB con --selftest-ajenas
```

## 8 · Corrección de numeración y de cifra

```text
  este fichero se escribio como 300, reservado con --reservar antes de escribir
  CORRECTED_BY: --reservar 300  RESERVADO

  CORRIGE A findings/298 §3bis
    la tabla de cobertura y la cifra de 303 lineas
    motivo: una de las cinco filas usaba `--self`, que no es la bandera de
    self-test de `toolkit`, sino su ruta de informe
    298 NO SE EDITA. Esta seccion es la correccion
```
