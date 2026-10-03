# 311 · La vista de fronteras no identificaba sus propias filas, y el 71% apuntaba a la línea equivocada

```
PENDIENTE=311-1 | HALLAZGO=311-la-vista-de-fronteras-no-identificaba-sus-filas-y-apuntaba-a-la-linea-equivocada.md
             | ESTADO=PROVEN
             | NECESITA=CORPUS | ALCANZABLE_SIN_ROOT=si
```

## El defecto de la línea, medido

Una tabla markdown entera es **un párrafo**, porque no hay línea vacía que la
corte. `claims.extraer()` usaba la línea de inicio del párrafo para cada
clasificación que encontraba dentro. Consecuencia medida sobre el corpus:

```
  filas de clasificacion extraidas        6243
  la linea publicada contiene su token     1780   (28,5%)
  la linea publicada NO contiene su token  4463   (71,5%)
```

Toda la frontera del proyecto vive en tablas — es donde los hallazgos
escriben sus resultados. Ir a `OPEN-FRONTIERS.md` a ver un hueco significaba
caer en la fila equivocada **cuatro de cada cinco veces**.

Arreglo: el desplazamiento del token dentro del texto del párrafo se convierte
a línea contando saltos. Es exacto, porque el texto del párrafo es la
concatenación de líneas consecutivas.

```
  ANTES   linea correcta 1780   incorrecta 4463   (71,5% mal)
  AHORA   linea correcta 6243   incorrecta    0   ( 0,0% mal)
```

El criterio de comprobación es que **la línea publicada contenga el token**, no
"sea la primera fila con esa clase": un primer intento de verificación usó esa
heurística y dio un 66% de fallo que no existía. El oráculo estaba roto, no la
herramienta.

## El defecto de la identidad, medido

La tabla publicaba `finding | linea | clase | via | ...`. **No había columna
de fichero**, y el número de hallazgo no es único: hay 74 números con dos o
tres ficheros.

```
  filas SIN_PISTAS con numero colisionado   25 de 93  (27%)
```

Una de cada cuatro filas no se podía atribuir ni leer. Peor: al intentar
corregirlo a mano, buscar "el fichero del 050" devuelve tres ficheros y dos de
ellos tienen la línea citada VACÍA. La ambigüedad no era un problema del
lector: era del artefacto.

El dato **ya estaba calculado**: `frontier.py` mete `documento` en cada hueco
desde su línea 193, y `artifacts.py` lo traía en el índice 1 de la tupla desde
siempre. Solo faltaba imprimirlo.

## Lo que este fallo falseaba

La cifra de `SIN_PISTAS` no era 93.

```
  lo que declaran AGENTS.md y ESTADO.md   93
  lo que hay                              107
```

Y una medición propia intermedia ("el 47% de los SIN_PISTAS no son
afirmaciones") salió **falsa**, y la causa fue este mismo defecto: al resolver
el número a fichero se elegía uno de los colisionados, y en los casos donde el
correcto decía algo y el otro decía otra cosa, la clasificación dependía de
cuál se abriera. Con la columna de fichero, el mismo análisis da **2 de 107 no
son afirmaciones** (dos encabezados de sección).

## El límite que queda, declarado

Clasifiqué las 1071 filas buscando "mención" en vez de "afirmación":

```
  afirmacion                                            891
  MENCION (habla del token, no afirma el token)          180   (17%)
    cita o blokquote del propio proyecto                  23
    determinante delante ("el `NOT_DETERMINED` que…")     57
    la linea describe el token (registró, corrige, hueco)  95
    otra causa                                                 5
```

**Y la regla no sirve.** Las 23 de blokquote son enmiendas del propio
proyecto que cuentan una transición de estado **y** nombran un hueco real que
sigue abierto. Las 57 con determinante incluyen "Cerrar el `NOT_DETERMINED` que
`023` dejó sobre cuál es el referente exacto del −1", que es una afirmación
abierta que además dice cómo cerrarse.

O sea: la separación entre "mencionar el token" y "afirmar el token" no es de
línea. Es de intención, y la intención no está en el texto de la línea.

**Consecuencia operativa: la vista produce una lista de CANDIDATOS.** Un 17%
hay que leerlo. Eso es aceptable si se dice; no lo es si el número se presenta
como si las 1071 fueran afirmaciones.

## Que NO se ha hecho

No se ha añadido una regla al clasificador para "limpiar" las menciones. Se
probó implícitamente al analizarlas y la regla recorta huecos reales. Un filtro que sube el recorte del 17% al 0% borrando afirmaciones es un
filtro que miente: cambia una lista con 17% de ruido por una lista que no tiene
lo que dice.

## Tesis que sostiene

Un artefacto que resume el estado tiene que poder señalar **dónde**. Si no
puede señalar el fichero y la línea, no es un índice: es un agregado, y
agregado no se puede ir a mirar.

El symptom y la causa estaban separados: "la línea no cuadra" y "no sé qué
fichero es" parecían dos problemas de datos, y eran uno solo del instrumental.

## Como reproducirlo

```python
# el oráculo: la linea publicada tiene que CONTENER el token de su clase
for f in findings/*.md:
    for x in claims.extraer(lineas_de(f)):
        if ("`%s`" % x["clase"]) not in lineas_de(f)[x["linea"]-1]:
            mal += 1
```
