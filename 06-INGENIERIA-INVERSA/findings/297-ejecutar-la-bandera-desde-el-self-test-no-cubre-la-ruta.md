# 297 · Ejecutar la bandera desde el self-test no cubre la ruta, y el motivo es que el hijo es otro proceso

```text
CLASSIFICATION=MEASUREMENT+NEGATIVE_RESULT+ERROR · TRACK=TOOLING
CORPUS=NINGUNO (el proyecto) · HARDWARE_SCOPE=NONE
WORK_CLASS=READ_ONLY/EVIDENCE+WRITE_LOCAL · WRITE_LOCAL=PROPIOS · MODIFICATIONS_CORPUS=0
RUNTIME=NOT_RUN · GPU INTACTA · CERROJOS=0
```

## Qué resuelve

El `NEXT_ACTION` de `296` era: la acción útil es **ejecutar las ramas**, y eso
son las banderas de línea de órdenes de cada herramienta desde su propio
self-test. Se midió antes de escribir, que es la parte que se hizo bien:

```text
  lint.py        --censo      base 367  ruta  79   12 lineas nuevas
  lint.py        --json       base 367  ruta 177   31 lineas nuevas
  govcheck.py    --json       base 348  ruta 255    5 lineas nuevas
  nextnum.py     --json       base 222  ruta  77   23 lineas nuevas
  fingerprint.py --json       base 172  ruta 173   71 lineas nuevas
  toolkit.py     --sin-fallar base 242  ruta 239    3 lineas nuevas
  toolkit.py     --strict     base 242  ruta 234    1 lineas nuevas
  ..........................................................................
  TOTAL                                                              146
```

Ciento cuarenta y seis. No «quince», que es lo que se había predicho: el
clasificador por forma de `296` veía 15 líneas de `BANDERA`, y la superficie real
era casi diez veces mayor. **Cada herramienta prueba su lógica y nunca su
informe.** `fingerprint` ejecuta 172 líneas en su self-test y 173 en la ruta de
informe, con 71 que no se solapan.

Y el discriminante también existía, que era no esperar a tener el número sino
medirlo: se escribieron los vectores y se volvió a medir.

```text
  lineas que ejecuta el self-test, antes y despues
    lint.py       367 -> 377   (+10)
    nextnum.py    222 -> 232   (+10)
                                        +20
```

## 1 · Y el resultado no es el que se prometió
prometió

**Veinte, no ciento cuarenta y seis.** Y la razón es mecánica, y se puede decir en
una línea:

```text
  el self-test llama a la herramienta con la bandera EN UN SUBPROCESO
  el settrace del padre NO ve al hijo
  asi que lo medido es la linea del self-test que lanza la llamada,
  no la ruta de informe del hijo
```

`trace` sí sigue a los hijos —por eso producía un `.cover` de 8 086 líneas— y lo
hace mezclando ficheros. `settrace` no los sigue, y por eso mide limpio pero
mide otra cosa. **Las dos herramientas tienen justo el defecto de la otra**, y el
discriminante que hace falta es un tercero: trazar al hijo también, pero por
fichero.

```text
  trace        sigue al hijo   y mezcla ficheros     ->  no referenciable
  settrace     no sigue al hijo y no mezcla nada    ->  no ve la ruta
  lo que hace falta                                ->  NO CONSTRUIDO
```

## 2 · Los vectores se escribieron, y tres de ellos eran mentira

Al escribirlos, tres cosas salieron mal, y las tres producen el mismo síntoma:
**vectores que pasan probando otra cosa**.

### Una · 25 vectores que no eran vectores

```python
  for _flag in "--censo --solo ANGLICISMO":        # <- una CADENA
```

Iterar una cadena da **letra por letra**. Los vectores se llamaban

```text
  OK la ruta c no revienta    rc=2
  OK la ruta e no revienta    rc=2
  OK la ruta n no revienta    rc=2
  OK la ruta s no revienta    rc=2
  OK la ruta o no revienta    rc=2
  ... y 20 mas
```

y **pasaban todos**: `sys.executable + ["-","-","c","e","n","s","o"]` sale con
`rc=2` y sin traza, que es exactamente lo que el vector pedía.

Y el recuento de vectores subió de 33 a 58, es decir **el número que había que
vigilar se falseó solo, precisamente por añadir los vectores que lo vigilan**.

### Dos · `nextnum` perdió 110 líneas de self-test

Al insertar el bloque, una INDEXación por línea se comió desde
`print("=" * 72)` hasta el final del self-test. El fichero pasó de 522 a 412
líneas, y el self-test seguía ejecutándose y **siguiendo en verde** con 17
vectores de los que quedaban 105 menos.

Lo detectó una medición que no buscaba eso:

```text
  nextnum.py   222 -> 117   (-105)
```

Un self-test que pierde tres quarters de sus vectores y sigue en verde. Se
restauró desde `/tmp/opencode/nn.bak`, que era la copia buena, y se reaplicó
sólo el bloque nuevo: 522 → 545 líneas, +23, que es exactamente el tamaño del
bloque insertado.

### Tres · `_v` no existe en `nextnum`

`nextnum` no tiene helper de vectores: escribe `if cond: print FAIL; fallos += 1`
en línea. Poner `_v(...)` produjo un `NameError` en la primera ejecución. El
bloque se reescribió en el idioma que ya tenía.

## 3 · Lo que sí queda, y es poco pero es cierto

```text
  los vectores de la ruta de informe EXISTEN y pasan
    lint.py     --censo, --solo ANGLICISMO
    nextnum.py  --json, --check 291
    govcheck.py  (no: la etiqueta de resultado es distinta y quedo fuera)
    fingerprint (idem)

  y cubren +20 lineas del PADRE, que son las del propio self-test
```

Que es lo que se esperaba saber antes de empezar: **ejecutar la bandera desde el
self-test no es una operación gratuita**, cuesta un subproceso completo por
bandera —`lint --json` son 23,7 s— y sin trazar al hijo no se puede demostrar que
haya cubierto nada.

## 3 bis · La tercera herramienta, y el número que sí es el bueno

`trace` sigue a los hijos y mezcla ficheros. `settrace` no los sigue y no mezcla
nada. Los dos miden mal cosas distintas, y faltaba el tercero.

Y el tercero no necesita trazar procesos: **necesita que el hijo se preste.** El
`BOOTSTRAP` que `295` escribió para medir el self-test recibe la ruta del script, lo
ejecuta con `sys.settrace` puesto dentro, y le dice al script que escriba su propio
`lineas.json`. Eso ya estaba hecho. Lo que no se penso es que **sirve también para
una invocación con banderas cualquiera**.

```python
  cobertura_de_ruta(raiz, rel, flag_selftest, banderas)
      self-test      lineas_de_invocacion(rel, [flag_selftest])
      con banderas   union de lineas_de_invocacion(rel, b) para cada b
      nuevas         las que las banderas aportan y el self-test no
```

Y el resultado es el número que de verdad responde a la pregunta de `296`:

```
  herramienta            self-test   + banderas   NUEVAS    total
  lint.py                     377         218        53       430
  nextnum.py                  232          87        32       264
  govcheck.py                 348         393       143       491
  fingerprint.py              172         173        71       243
  toolkit.py                  242         246         4       246
  ...................................................................
  LINEAS QUE EL SELF-TEST SOLO NO EJECUTABA Y SI:  303
```

**Trescientas tres.** No las 20 de `297` —que era el número de la medición
equivocada— ni las 146 de la primera medición, que sumaba máximos por bandera sin
unir.

Y hay un detalle que cambia la lectura de todo lo anterior: **un self-test tiene más
líneas de las que se creía.** `govcheck`, que antes ejecutaba 348 líneas, con sus
banderas llega a 491. Lanzar un flag **sí ejecuta código propio**, y ese código
llevaba sin ejecutarse desde que se escribió la herramienta.

### Y un vector mío que afirmaba algo falso

El primer vector de esta parte miraba `len(banderas) > len(selftest)`, es decir, que
las banderas son un superconjunto del self-test. Es falso, y para `nextnum` pasa lo
contrario:

```
  nextnum.py  --selftest        234 lineas
  nextnum.py  --json + --check   87 lineas
```

Porque `--json` toma un camino **distinto**, no uno más largo. Lo que importa es la
unión, que es 264. El vector miraba la longitud equivocada y por eso fallaba.

## 4 · La regla, y el coste que tiene

```text
  UN VECTOR QUE LANZA LA HERRAMIENTA CON UNA BANDERA, SIN MIRAR AL HIJO,
    NO SE SABE SI HA CUBIERTO NADA
```

Que es más pequeño que `294` pero más concreto: **un test que delega en un proceso
y no observa el proceso tiene el mismo problema que uno que comprueba `exit 0`.**
No es que no sirva: es que sirve sin saber para qué.

Y el coste medido de hacerlo mal:

```text
  lint.py --json     23 757 ms   y cubre 0 lineas de la ruta en la medicion
  govcheck.py --json  7 247 ms   idem
  toolkit.py --strict   314 ms   idem
  nextnum.py --json      58 ms   idem
```

## 5 · Lo que NO se establece

```text
  cuantas de las 146 lineas quedarian cubiertas CON TRAZA AL HIJO
    NO MEDIDO. Es lo que hace falta y no esta hecho. La instrumentacion seria un
    bootstrap por hijo, con su propio settrace y su propio fichero de salida, y
    una union por ruta de fichero en vez de una mezcla
  si las 71 lineas de informe de `fingerprint` valen la pena
    NO SE SABE. Son las que masanas, y son las que un self-test que solo prueba
    logica deja sin tocar. Pero "sin tocar" no es "mal", y no se ha leido ninguna
  la cobertura de las otras tres herramientas sin cambio
    NO MEDIDA. Solo se han tocado `lint` y `nextnum`; `govcheck`,
    `fingerprint` y `toolkit` siguen como estaban, con sus vectores de ruta
    pendentes por la misma razon de etiqueta
  el numero de lineas del proyecto que un self-test ejecuta
    NOT_MEASURED, y es la cifra que haria falta para saber si todo esto es
    pequeno o grande
```

## 6 · Lo que esta vez se hizo bien, y es lo único que cambió

Antes de escribir el cambio se midió qué líneas cubre cada bandera:

```text
  146 lineas, con fichero y numero
```

Eso es lo que permitió descubrir que la predicción de «quince» era falsa por un
factor diez. **La medición previa evitó el error, y es lo contrario de lo que
pasó en `294`**, donde se escribió el detector y se miró el árbol después, y el
cero que salió era ceguera.

El fallo de esta iteración no fue de método: fue de ejecución. Inserts por
índice de línea un bloque en un fichero de 522 líneas, sin comprobar después
cuántas quedaban.

## 7 · Trazabilidad

```text
  findings/296 §3                          las 158 lineas sin ejecutar
  tools/mutscore.py lineas_del_selftest    el settrace, y su limite de hijo
  /tmp/opencode/nextnum_dañado.txt         la version con 110 lineas menos
  /tmp/opencode/nn.bak                     la copia buena desde la que se restauro
  tools/nextnum.py:522 -> 545              el unico cambio con numero verificado
  tools/lint.py:33 -> 35 vectores          y los 25 falsos que hubo en medio
```

## 8 · Corrección de numeración

```text
  este fichero se escribio como 297, reservado con --reservar antes de escribir
  CORRECTED_BY: --reservar 297  RESERVADO
```