# 245 · Cien números de hallazgo duplicados, y por qué una reserva que no es atómica los produce

```
CLASSIFICATION=MEASUREMENT+TOOLING · TRACK=VERIFICATION
CORPUS=RESEARCH/working/RX550-INVESTIGACION · HARDWARE_SCOPE=NONE
WORK_CLASS=READ_ONLY/EVIDENCE+WRITE_LOCAL · WRITE_LOCAL=PROPIOS · MODIFICATIONS_CORPUS=0
RUNTIME=NOT_RUN · GPU INTACTA · CERROJOS=0
```

## Qué resuelve

`nextnum.py` existe para que un número de hallazgo no se repita. Y sin embargo,
medido sobre el directorio de hallazgos de este proyecto:

```
ficheros de hallazgo:      323
numeros distintos:         197
numeros duplicados:        100
  de ellos reparables:      44
  de ellos ambiguos:        56
```

**126 ficheros de más.** La causa estaba ya documentada —agentes en paralelo
reservan el mismo número en la misma ventana de segundos— pero nunca se había
**medido**. Y medirla cambia la categoría del problema: no es un accidente
puntual, es una tasa del 33 % de los números.

## 1 · Por qué el número duplicado no es cosmético

La convención del proyecto es citar por **nombre completo**, no por número, y
existe una herramienta (`citeambig.py`) cuya razón de ser es exactamente que
`findings/176` puede no identificar un documento.

Con 100 números duplicados, esa ambigüedad no es un caso: es la norma en un
tercio del corpus. Y el coste no es simétrico: cuando un número está duplicado,
`nextnum.py --check NNN` lo dice, pero `grep findings/NNN` devuelve **dos**
ficheros y no hay regla honesta para elegir.

Precedente de que renumerar es aceptable: `tools/REF-EXCEPTIONS.txt` ya
documenta un caso anterior —

> esa sesion lo renombro a `023-pte-productor-sdma-gfx8.md` al resolver una
> colision de indice, y 021 CUENTA esa colision

— y explica por qué corregir la referencia **empeoraría** el registro histórico.
Es exactamente la razón por la que aquí no se corrige ninguna cita: se mueve el
fichero, y el texto que contaba la colisión sigue contando una colisión.

## 2 · La herramienta, y la regla que decide

`tools/dupenum.py`. Dos clases, y la que no se aplica se dice en pantalla:

```
SEGURO    grupo de exactamente 2 ficheros
AMBIGUO   todo lo demas: no se toca, y se reporta por que
```

La regla de seguridad tiene cuatro condiciones, y el desempate cuando **ninguno**
de los dos está citado es una convención declarada, no una verdad:

```
  0 citados   los dos se pueden mover; se queda el MAS ANTIGUO (mtime)
  1 citado    se mueve el otro. El citado no se toca JAMAS
  2 citados   no se mueve ninguno
  grupo > 2   no se mueve ninguno: con tres habria que elegir cual se queda,
              que ya es una decision de contenido y no de numero
```

Lo que **no** hace, por decisión:

```
  NO borra nada. Renumerar mueve el fichero y corrige SU cabecera y SUS
  referencias internas. El texto del hallazgo no se toca.
  NO desambigua citas por numero desnudo. Una cita que solo dice findings/202
  no se puede arreglar automaticamente, y se reporta en vez de inventarse.
  NO decide cual de los dos duplicados tiene razon. Eso se lee, no se elige.
```

### Las cuatro condiciones tienen dientes

Una condición que se puede quitar sin que nada falle no protege nada. Se
quitó cada una por separado:

| condición quitada | resultado |
|---|---|
| grupo de exactamente 2 | el vector de 3 ficheros pasa a SEGURO — **detectado** |
| solo el que NO tiene citas | se libera el fichero **citado** — detectado |
| destino ocupado | se pisa un fichero existente — detectado |
| cabecera sin número | renumera a ciegas — detectado |

El primer caso exigio corregir el vector, no la herramienta: el test de 3
ficheros los dejaba **a los tres sin citar**, con lo cual `len(sin_citas) == 3`,
ninguna de las dos ramas se cumplía y el `AMBIGUO` venía del número de ficheros
y no de las citas. Al quitar la condición el test seguía pasando.

**Un test que pasa sin ejercitar la condición que dice vigilar es peor que no
tenerlo**, porque da la impresión de que esa condición está vigilada.

## 3 · Lo aplicado, y la prueba de que no rompió nada

```
antes      323 ficheros   197 numeros   100 duplicados   ROTA 349
despues    325 ficheros   241 numeros    57 duplicados   ROTA 349
           +42 renumerados              -43 duplicados   0 citas rotas
```

`ROTA` **no se movió**. Eso es la comprobación que importa: se renumeraron 42
ficheros y ninguna referencia dejó de resolver. La coherencia se tiene por
diseño —solo se mueven ficheros con cero citas externas, comprobado por
`slug` completo y no por número, porque por número los dos duplicados darían la
misma cuenta y no se movería ninguno— pero **tenía que medirse igual**.

Mapa completo de las 42 renumeraciones, para poder revertir:
`/tmp/opencode/dupenum-mapa-20261002-134040.json`.

Los 57 `AMBIGUO` quedan sin tocar, y son un trabajo distinto: hay que **leer** los
dos hallazgos de cada número y decidir. Ninguna herramienta puede hacerlo, y una
que lo intentara estaría eligiendo contenido por regla.

## 4 · El caso queadogica la herramienta

De los 42 movidos, uno era el `242` de **otra sesión**:

```
202-la-ventana-de-registros-es-bar5-y-el-log-lo-dice.md          (esta sesion)
202-los-registros-caben-en-bar5-con-4x-de-holgura.md             (otra sesion)
```

Las dos llegaron a **BAR5 por separado**, y eso es corroboración
independiente del resultado, no una coincidencia: dos lecturas del mismo corpus
con el mismo código fuente.

La segunda estaba citada por **la primera**, y por eso la segunda era la
liberable: cero citas. Al renumerarla a `242`, la cita cruzada sobrevive intacta
y por fin **no es ambigua**:

```
242-...md:135  Otra sesión publicó `202-la-ventana-de-registros-es-bar5-y-el-log-lo-dice.md`
```

Antes de renumerar, `242` no identificaba nada. Ahora sí.

## 5 · La reserva no atómica, que es la causa de fondo

`nextnum.py` calcula el siguiente número libre leyendo el directorio. Entre que
lo lee y que el fichero aparece en disco, otro proceso puede leer lo mismo y
elegir el mismo número. Ninguna cantidad de cuidado dentro de la herramienta lo
arregla: **el defecto está en que la reserva no reserva**.

Las tres salidas reales, y solo la primera está al alcance:

```
  1  un fichero de bloqueo con flock, y un numero reservado que seokatiene
     hasta que el hallazgo se escribe. Es lo correcto y es una herramienta
     nueva, no un cambio de una linea.
  2  que dupenum.py se ejecute al FINAL de cada sesion, como una
     comprobacion y no al principio. Barato y reduce la tasa.
  3  aceptar el estado y medirlo. Que es lo que se ha hecho, y es peor que
     las dos anteriores pero no es cero: 100 -> 57, y el resto con nombre.
```

Lo que **no** hace ninguna de las tres: arreglar la causa raíz, que es que
`RESERVAR NUMERO ANTES DE ESCRIBIR` es una instrucción para una persona y no un
mecanismo. El mecanismo es `flock`, y no está hecho.

Mientras no lo esté, `dupenum.py` es la red, no la solución.

## 6 · Trazabilidad

```
  tools/dupenum.py              la herramienta, 7 comprobaciones, con dientes
  tools/nextnum.py              indice() y siguiente(), usados por composicion
  tools/REF-EXCEPTIONS.txt      el precedente de renumerar una colision
  /tmp/opencode/dupenum-mapa-*.json   mapa de las 42 renumeraciones
  findings/202  y  findings/242       el caso que la herramienta resolvio
```