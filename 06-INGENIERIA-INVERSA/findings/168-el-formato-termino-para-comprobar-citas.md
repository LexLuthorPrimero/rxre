# 168 · Declarar qué se cita para poder comprobar si la cita se sostiene: el formato `TERMINO=` y la clase que faltaba

```
CLASSIFICATION=TOOLING+MEASUREMENT · TRACK=VERIFICATION
CORPUS=RESEARCH/working/linux-7.2.8 · HARDWARE_SCOPE=NONE
WORK_CLASS=READ_ONLY/EVIDENCE · WRITE_LOCAL=PROPIOS · MODIFICATIONS_CORPUS=0
RUNTIME=NOT_RUN · GPU INTACTA · CERROJOS=0
```

## Qué resuelve

`234` cerró por dónde no cerraba: una cita de hallazgo puede **resolver**, **no ser
ambigua**, y aun así **no sostener** la afirmación para la que se cita. Eso no se
puede medir porque **el término que se cita no está escrito en ningún sitio**.
El hueco no era la herramienta: era el formato. Exactamente el mismo movimiento
que produjo `PENDIENTE=` en `AGENTS.md`, y por eso se repite aquí.

El formato, en `AGENTS.md` § LA CITA QUE SE SOSTIENE:

```text
CITA=<fichero.md> | TERMINO=<término literal que el fichero citado debe
                   contener> | ROL=<afirmación que la cita sostiene>
```

Y el resultado sobre el corpus, con nueve citas sembradas donde las referencias
oscilaron —el bloque PTEPDE de `rx550_pm4.h`:

```
CITA= declaradas: 9   SOSTENIDA 9   NO_SOSTENIDA 0
                    SIN_TERMINO 0   PLANTILLA 0   MAL_FORMADA 0
de las declaradas con TERMINO=, sostenidas: 100.0% (9 de 9)
```

**El 100 % no dice que las citas sean buenas.** Dice que las nueve están
comprobadas y que las nueve aguantan. La distinción importa: `citeambig.py
--sostiene` informaba «0 SOSTENIDA, 100 %» cuando la adopción era cero, porque
comparaba un conjunto vacío consigo mismo.

## 1 · El fallo que hace necesaria la regla de que `ROL=` sea obligatorio

`cruzadas()` aplanaba el texto del documento a una sola línea para tolerar las
citas partidas en varias líneas. Con el texto plano, el grupo `ROL=[^\n]+` del
**primer** `CITA=` se comía **todas** las citas siguientes del fichero, incluida
la plantilla del formato. El resultado medido:

```
SOSTENIDA  : []
NO_SOSTEN  : []
SIN_TERMINO: []
PLANTILLA  : [('doc.md', 'findings/020-a.md', 'SDMA_OP_GEN_PTEPDE')]
```

Una cita real clasificada como **plantilla**, y las cuatro restantes
desaparecidas. Un clasificador que se come el resto del fichero no mide el
fichero: mide su propia regex.

Arreglado dejando los saltos de línea —`\s*` ya los cubre— y haciendo el `ROL`
perezoso hasta el salto de línea **o hasta el siguiente `CITA=`**. Con eso, una
cita partida en tres líneas se analiza bien, y `MAL_FORMADA` queda para lo que de
verdad no encaja, no para eso.

## 2 · Un guardia que no disparaba

```python
rel = os.path.relpath(ruta, raiz)     # 'tools/citeambig.py'
if rel == YO_MISMO:                   # 'citeambig.py'
    continue
```

**Nunca excluyó nada.** La herramienta se citaba a sí misma y sus fixtures
sintéticos salían en el informe como citas reales — que es exactamente lo que
ocurrió en la ronda anterior con los docstrings. Comparaba una ruta relativa con
un nombre de fichero.

Ahora compara `os.path.basename(rel)`. Un guardia que nunca dispara no es un
guardia, y no lo era: llevaba dos rondas puesto y el informe que lo delata lo
decía en su propia sección, listándolo como fuente.

## 3 · Mención del formato no es cita

Al montar el formato aparecieron dos `SIN_TERMINO` que no eran citas:

```
AGENTS.md                          `
07-DRIVER/kernel/rx550_pm4.h       /TERMINO=/ROL=,
```

Son las menciones en prosa —`` `CITA=` `` y «se escribe `CITA=/TERMINO=/ROL=`»—
que el regex no puede distinguir de una cita real por contexto. El filtro es
**mecánico y no interpreta**: un fichero tiene extensión.

```python
RE_FICHERO_CITA = re.compile(r"^[^\s|]+\.(md|c|h|py|txt|mk|json|rst)$")
```

El filtro se aplicó primero **sólo al recuento** y no al bucle que rellena
`SIN_TERMINO`, de modo que las menciones se colaban por el otro lado. Las dos
cosas a la vez, o la reconciliación de clases deja de cuadrar.

## 4 · Lo que el formato no resuelve

`ROL=` es obligatorio y **la herramienta no lo comprueba**. Es deliberado, y por
eso hay que decirlo: el campo existe para obligar a declarar *qué* sostiene la
cita, no porque exista un modo mecánico de verificarlo. Sin `ROL=`, `TERMINO=` es
un término suelto y no hay forma de saber contra qué afirmación se compara —
que es la mitad del problema que `234` declaró abierto.

Lo que sí queda abierto y **no** se ha resuelto:

```
PENDIENTE=ROL= es obligatorio por convencion y no se comprueba; no hay forma
          mecanica de verificar que el hallazgo citado sostenga la afirmacion
          que ROL= declara
  | HALLAZGO=168-el-formato-termino-para-comprobar-citas.md
  | ESTADO=NOT_DETERMINED
  | NECESITA=un cross-check de ROL= que no sea "el termino aparece": tendria
  |          que comprobar que el hallazgo citado contiene una afirmacion del
  |          mismo tipo, lo que exige un clasificador de afirmaciones. No es
  |          alcanzable declarando un campo mas
  | ALCANZABLE_SIN_ROOT=si
```

Es la diferencia entre una comprobación de **presencia** y una de **sustancia**,
y la segunda no sale de un formato. Lo que sí sale de un formato es todo lo demás.

## 5 · Reconciliación por construcción

Ninguna clase se cuenta «a ojo». El total de `CITA=` declaradas en cada fichero
se compara con lo clasificado, y la diferencia es `MAL_FORMADA`:

```
declaradas = RE_NOMBRE_TRAS_CITA filtrado por fichero_es_cita
clasificadas = SOSTENIDA + NO_SOSTENIDA + PLANTILLA + SIN_TERMINO
MAL_FORMADA  = declaradas - clasificadas
```

Si algo no encaja en ninguna clase, el total **no cuadra y se dice**, en vez de
desaparecer. Con la versión anterior, sin reconciliación, un `CITA=` mal formado
era indistinguible de uno que nunca existió.

Y el sumatorio se comprueba con un `assert` en el informe, porque ya imprimió
una vez «159 citas = 3 + 3 + 3 + 3» sin protestar: un desglose que no suma no es
un desglose.

## Procedencia

```
AGENTS.md § LA CITA QUE SE SOSTIENE   el formato, escrito antes de la herramienta
tools/citeambig.py --sostiene         25 vectores, cinco con dientes comprobados
07-DRIVER/kernel/rx550_pm4.h         9 citas CITA= en el bloque PTEPDE
tonga_sdma_pkt_open.h:37             TERMINO=SDMA_OP_GEN_PTEPDE  -> SOSTENIDA
sdma_v4_0.c:1649                     TERMINO="count - 1"         -> SOSTENIDA
sdma_v3_0.c:987                      TERMINO=SDMA_OP_GEN_PTEPDE  -> SOSTENIDA
07-DRIVER/tests/test_pm4.c           208 checks, 0 failures
findings/167 §5                      el hueco que este formato no cierra
```

## CORRECCION POSTERIOR

Ninguna sobre lo afirmado. Dos advertencias sobre **cómo leer estas cifras**,
que es la parte que envejece:

1. **Nueve citas no son una muestra.** Es la adopción inicial, sembrada en un
   solo sitio porque es donde las referencias oscilaban. El 100 % mide esas
   nueve, no el proyecto.
2. **Un censo es una foto.** Los agentes paralelos siguen añadiendo hallazgos y
   citas mientras se mide. Las cifras de este documento valen para el estado en
   el momento en que se escribieron, y cualquier comparación con otro recuento
   necesita comprobar qué versión de la herramienta produjo cada una.
