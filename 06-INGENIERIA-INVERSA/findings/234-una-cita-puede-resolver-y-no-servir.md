# 234  Se puede resolver una cita y que no signifique nada: 97 de 203 citas de hallazgos no dicen a qué hallazgo se refieren

```
CLASSIFICATION=TOOLING+MEASUREMENT · TRACK=VERIFICATION
CORPUS=RESEARCH/working/linux-7.2.8 · HARDWARE_SCOPE=NONE
WORK_CLASS=READ_ONLY/EVIDENCE · WRITE_LOCAL=PROPIOS · MODIFICATIONS_CORPUS=0
RUNTIME=NOT_RUN · GPU INTACTA · CERROJOS=0
```

## Qué resuelve

Hay dos preguntas distintas sobre una cita de hallazgo, y este proyecto
respondía a una:

| pregunta | quién la responde | estado |
|---|---|---|
| ¿el fichero existe? | `reftriage.py` | respondida |
| ¿resuelve la cita? | `treescope.py` | respondida |
| **¿sostiene el hallazgo citado lo que se le pide?** | **nadie** | **sin medir** |
| ¿a cuál de varios se refiere? | nadie | sin medir |

La tercera es la que produjo **cuatro oscilaciones seguidas** del mismo nombre de
opcode en el driver propio (`findings/147`). La cuarta es la que hace que citar
por número desnudo deje de ser una convención menor.

`tools/citeambig.py` responde a la cuarta. La tercera sigue sin respuesta y es
un hueco declarado, no un olvido.

## 1 · El número, con dos denominadores

```
poblacion        hallazgos  269 en 164 numeros, 82 numeros con mas de un fichero

prosa  (.md/.txt/.mk)   45 citas = 22 COMPLETA +  0 TRUNCADA +  9 DESNUDO + 14 AMBIGUA
                              conformes 48.9%    a corregir  23 de  45

codigo (.c/.h/.py)     158 citas = 83 COMPLETA +  7 TRUNCADA + 15 DESNUDO + 53 AMBIGUA
                              conformes 52.5%    a corregir  75 de 158
```

**97 de 203 citas no identifican un hallazgo unívocamente.** Casi la mitad en las
dos poblaciones, y el reparto es parejo: no es un problema de una zona del
proyecto.

Los dos denominadores están separados porque son dos poblaciones distintas. Una
citación en prosa es una referencia; una cadena `findings/035` dentro de un
docstring es un **ejemplo**. Sumarlas produce un número que no describe nada, y
eso ya pasó: antes de separarlas, esta misma herramienta aparecía en su propio
informe como fuente de citas, citando sus propios fixtures sintéticos. Es el
modo de fallo más incómodo de una herramienta de medición — el instrumento
contaminando lo que mide — y sólo se ve mirando la salida completa, no el
resumen.

## 2 · Las cuatro clases, y por qué TRUNCADA hacía falta

```
COMPLETA   findings/147-slug.md    conforme
TRUNCADA   findings/147-slug       le falta el .md
DESNUDO    findings/147             resuelve, y hay un solo fichero
AMBIGUA    findings/035             resuelve a N ficheros distintos
```

`TRUNCADA` no estaba en el diseño inicial y se añadió por un motivo concreto:
**una cita `findings/147-slug` sin extensión no la veía ninguna clase.** La regex
de cita desnuda exige que el número no vaya seguido de nada, y la de cita
completa exige el `.md`. Quedaba invisible. Una clase invisible no es una clase
pequeña: es un hueco que el informe afirma no tener.

Y la ambigua importa porque hay **82 números con más de un fichero**, y crecen
solos: los agentes paralelos escriben a la vez y numeran por su cuenta. El caso
concreto que laabayó está en `findings/147 §4`: `rx550_pm4.h` citaba
«findings/035» y hay dos ficheros con ese número, uno de ellos
`035-block-size-tres-claims-y-un-log.md`, que no tiene nada que ver con el
nombre del opcode.

## 3 · Los seis defectos que la herramienta encontró en sí misma

Los dieciséis vectores del selftest existen porque la versión anterior fallaba
en ellos. **Ninguno es hipotético y cinco tienen dientes comprobados** — se
rompió el código a propósito y se vio fallar el vector.

1. **Un `bytearray` que decía hacer un trabajo que no hacía.** Marcaba como
   "consumido" lo ya citado de forma completa, pero el mecanismo real era el
   lookaheahead `(?![\w-])` de la regex de cita desnuda, que ya rechaza cualquier
   cosa seguida de `-`. **El vector que lo probaba pasaba igual con el bytearray
   roto**, que es como se descubrió. Era código muerto con un comentario que
   afirmaba ser necesario.

2. **`(?<!\.)` ausente: una cita completa con punto final se contaba dos veces.**
   `findings/003-slug.md.` dejaba la cola máxima terminando en `.`, el
   lookbehind de `.md` miraba `md.` y pasaba, y la cita salía a la vez como
   COMPLETA y como TRUNCADA. **Un clasificador que cuenta dos veces es peor que
   uno que no cuenta**: el total deja de ser un total y el porcentaje deja de
   describir nada.

3. **`(?<![\w-])`: mal, no solo inútil.** Deja la clase TRUNCADA **vacía**. La
   cola de una cita truncada acaba en letra (`o` en `findings/002-uno`) y un
   lookbehind que prohíbe terminar en carácter de palabra rechaza justo el caso
   que hay que detectar. Peor: una clase vacía *parece* que no hay nada que
   clasificar.

4. **`es_autocita` sólo se consultaba en la lista de ambiguas.** Con un número de
   un solo fichero —el caso mayoritario— la cita cae en DESNUDO y la rama no se
   ejecuta nunca. Se comprobó a mano, se vio que daba 0, y la 0 resultó ser
   cierta sólo por casualidad: un hallazgo sencillamente no se cita a sí mismo
   por número desnudo. Una rama que sólo se ejecuta en el caso raro no es una
   rama.

5. **Un vector que pasaba por el motivo equivocado.** «fuera de `findings/` no es
   autocita» usaba un fichero llamado `otro.md`: la comprobación del nombre
   bastaba y el vector seguía en verde **con la exclusión rota**. Se cambió a
   `010-notas.md`, fuera de `findings/` y con el mismo prefijo numérico que un
   hallazgo, para que la exclusión cargue de verdad. Verificado: rompiendo la
   exclusión, el vector falla.

6. **Un desglose que no sumaba.** El resumen del censo de código imprimía
   «159 citas = 3 + 3 + 3 + 3». Un error de indexado al partir el recuento, y lo
   imprimió **sin protestar**. Ahora hay un `assert` de que las clases suman el
   total, porque un total incoherente es un fallo de la herramienta, no una
   observación sobre el corpus.

## 4 · Y uno que es de rendimiento y no de exactitud

La primera versión recorría la raíz del proyecto entero, que incluye
`rx550-upstream-7.2.8/`: **691 MB** de árbol de Linux. Buscar ahí citas
`findings/NNN` es buscar algo que no puede haber, y la herramienta **agotó el
tiempo de espera de diez minutos** en una pregunta que se responde en once
segundos.

La lista de exclusiones declara **el motivo de cada entrada**, no sólo cuál es:
un directorio excluido sin razón escrita es una decisión invisible que alguien
revierte sin saber qué perder. El selftest comprueba que cada entrada tiene
motivo, y que el corpus queda fuera de verdad.

## 5 · Lo que esta herramienta NO hace

No verifica que el hallazgo citado **sostenga** la afirmación. Eso exige
comparar el término citado —`GEN_PTEPDE`, `count`, `vega10`— con el contenido
del hallazgo citado, y es la clase de fallo de `findings/147`. Es observable de
forma mecánica y por tanto automatizable, y no lo está:

```
PENDIENTE=una cita puede resolver, no ser ambigua, y aun asi no sostener la
          afirmacion para la que se cita
  | HALLAZGO=234-una-cita-puede-resolver-y-no-servir.md
  | ESTADO=NOT_DETERMINED
  | NECESITA=cross-check del termino citado contra el contenido del hallazgo
  |          citado, con lista de terminos por clase de afirmacion; el termino
  |          tiene que declararse, porque "el termino" no esta escrito en ningun
  |          sitio todavia
  | ALCANZABLE_SIN_ROOT=si
```

Sin ese campo `TERMINO=` no hay forma mecánica de saber **qué** se cita, y una
herramienta que adivina el término midiendo la conclusión equivocada es peor que
ninguna. Es el mismo problema que `routeaudit.py` encontró en `PENDIENTE=`: no
faltaba la herramienta, faltaba el formato.

## CORRECCION POSTERIOR

**`RESUELTO EN PARTE` por `168-el-formato-termino-para-comprobar-citas.md`.**

El hueco de §5 era de formato, no de herramienta, y así se resolvió: `AGENTS.md`
§ LA CITA QUE SE SOSTIENE define

```text
CITA=<fichero.md> | TERMINO=<término literal> | ROL=<afirmación sostenida>
```

y `citeambig.py --sostiene` mide si el término declarado aparece en el fichero
citado. Con nueve citas sembradas en `rx550_pm4.h`: **9 SOSTENIDA de 9**.

Lo que **no** queda resuelto es lo que el propio `235` declara pendiente:
comprobar que el hallazgo citado sostenga la *afirmación* que `ROL=` declara, y
no sólo que contenga el término. Eso es presencia frente a sustancia, y no sale
de declarar un campo más.

La cifra viva es la adopción: `citeambig.py --sostiene` informa `SIN_TERMINO` en
la misma línea que el resto precisamente para que un 100 % sobre nueve citas no
se lea como cobertura.

## Procedencia

```
tools/citeambig.py            16 vectores, todos con dientes comprobados
tools/citeambig.py --resumen  269 hallazgos, 203 citas, dos denominadores
findings/035-*                dos ficheros con el mismo numero: el caso real
findings/147 §4               el alcance de la clase AMBIGUA sobre el driver
AGENTS.md                     convencion de citar por nombre completo de fichero
```

## CORRECCION POSTERIOR

Ninguna. El número «97 de 203» de este hallazgo se midió con la versión de la
herramienta que excluye el corpus de Linux y separa prosa de código; las cifras
que aparezcan más adelante en otros documentos **no** son comparables con estas
sin comprobar qué versión produjo cada una, porque los agentes paralelos siguen
añadiendo hallazgos y citas mientras se mide.

Esa es la segunda mitad de la lección de este hallazgo, y la más fácil de
olvidar: un censo es una **foto**, no un número estable. Sin fecha, versión de la
herramienta y denominador, un recuento envejece sin que nadie lo note.
