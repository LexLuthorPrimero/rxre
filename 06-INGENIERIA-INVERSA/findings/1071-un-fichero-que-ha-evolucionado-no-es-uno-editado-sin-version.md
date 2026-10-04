# 1071 — un fichero que ha evolucionado no es lo mismo que un fichero que alguien editó sin subir la versión, y mi instrumento no lo distinguía

```text
AGENCIA=RX550-INVESTIGACION · WORK_CLASS=AGENT-MAIN-VALIDITY
CLASSIFICATION=SEMANTICA+DEFECT · TRACK=STATIC+MUTATION
GENERADO=2026-10-04 · MEDIDO=EN ESTA HOST
AFECTADO=tools/sello_prov.py  audita_campo(): version != real  ->  DIFIERE
         06-INGENIERIA-INVERSA/findings/1057-…md:12-13 (las dos apariciones)
ORIGEN=1070 §4 (el 1057 salio DIFIERE porque movi la herramienta que cita)
ESTADO=PROBADO · REPARADO · 57 vectores · 3 mutaciones detectadas
herramienta   tools/sello_prov.py 1.3.0
sha256        feaafdffb4870248
```

## 0 · Lo que la distinción separa

```text
DIVERGIO   el fichero HA EVOLUCIONADO.
           El documento habla de la version 1.0.0; el fichero ya es 1.1.0.
           La afirmacion del documento SIGUE SIENDO sobre 1.0.0, y ya no se
           puede comprobar contra 1.1.0 porque ya no es la misma cosa.
           No hay indicio de que nadie tocara nada.

DIFIERE    MISMA version, bytes distintos.
           Eso si es sospechoso: alguien toco el artefacto sin mover la
           version, y la suma declarada ya no describe nada de lo que hay
           ahi. Es el caso grave.
```

**Antes de este arreglo, los dos salían `DIFIERE`.** Y el `DIVERGIO` que acabo de
medir es **mío, y de hace dos iteraciones**: el `1057` cita `tools/sello_prov.py 1.0.0`
y la herramienta ya es `1.1.0`, porque la subí al arreglar las cuatro cosas que enumera
el `1058 §3`.

## 1 · POR QUÉ LA CONFUSIÓN ES PELIGROSA, Y NO SÓLO INCÓMODA

El proyecto entero se apoya en esta idea: **una cifra sin producer no es una
medición**. `1057` §0 es el ejemplo canónico de un hash sin producer, y su
reparación fue ponerle la receta al campo.

Si `DIVERGIO` y `DIFIERE` se reportan igual, ese razonamiento se vuelve contra sí
mismo:

> un bloque de procedencia cuyo hash no coincide con el fichero **no demuestra nada**
> → ni cuando el fichero **ha cambiado de versión por evolution normal**, que es lo
> que pasa cada vez que se arregla una herramienta, ni cuando alguien **lo ha editado
> en silencio**.

**El segundo caso es el que hay que ver primero, y es el que un `DIFIERE` único
enterraba.** Un instrumento que grita "las sumas no cuadran" por cada
`herramienta.py` que ha subido de versión entrena a ignorar el aviso — que es
exactamente lo que `1057` §2 le pasó a mi propio instrumento con `reproducible`, y lo
que su docstring llama *"un interlock que grita lobo por una errata deja de proteger
nada"*.

## 2 · LA REGLA, Y DÓNDE ESTÁ EN CÓDIGO

`audita_campo()`, rama de los campos **portador**, cuando el valor tiene forma de
versión:

```python
elif real != c["version"]:
    v["veredicto"] = "DIVERGIO"
    v["motivo"] = ("el fichero HA EVOLUCIONADO: el documento dice %s y el "
                   "fichero dice %s. La afirmacion del documento sigue siendo "
                   "sobre %s, que ya no esta" % ...)
```

`DIVERGIO` **no baja el código de salida**, por la misma razón que `SELLADO_PERDIDO`
no lo bajaba en `sello.py` (`1059` §6): es un hecho que hay que mirar, no un fallo. Un
`DIVERGIO` es el estado normal de un documento que habla de una versión antigua, que
es lo que deben hacer los documentos.

**Y la versión es el ancla.** El `1057` **no se ha corregido**: sigue declarando
`1.0.0`, y debe seguir declarándola, porque su afirmación es sobre el comportamiento
de `1.0.0` —el `SIN_RECETA` incondicional que el propio hallazgo denuncia—. Re-sellar
su hash al valor de `1.1.0` haría que el documento afirmara haber medido una
herramienta que no es la suya. **Un bloque de procedencia describe un artefacto
inmutable; la versión es lo que lo ancla.**

## 3 · LO QUE ESTA MEDICIÓN DICE DE MIS PROPIOS DOCUMENTOS

```text
1057:12  DIVERGIO  1.0.0 -> 1.1.0     la herramienta evolucionó
1057:13  DIFIERE   sha256 7d2bcc1f…    (consecuencia del anterior, no un evento aparte)
1058:13  EXISTE    VERSION coincide 1.1.0
1058:16  DIFIERE   sha256 9bc06ad8…    declarado al escribir el 1058; la herramienta
                                       se movió otra vez después
```

Los cuatro DIFIERE de `1057` y `1058` son **consecuencias de mis propias
iteraciones**, no de nadie que haya editado un artefacto en silencio. Con la
distinción, eso se lee sin ambigüedad: `DIVERGIO` es lo que pasa cuando el proyecto
avanza; `DIFIERE` a secas sería lo que pasa cuando alguien miente por omisión.

**Y queda una corrección pendiente, y la digo:** los bloques de `1057` y `1058`
declaran una versión y un hash que ya no corresponden al fichero. La forma correcta de
dejarlos es **añadir la línea de "estado actual"**, sin tocar la del estado medido:

```ejemplo
herramienta   tools/sello_prov.py 1.0.0   <-- la que se midió
sha256        7d2bcc1f3f76fc23
herramienta   tools/sello_prov.py 1.1.0   <-- estado actual, medido en 2026-10-04
```

> **La valla dice `ejemplo`, y eso no es decorativo.** Hace falta porque
> **`sello_prov` no puede distinguir una declaración de una cita**: ve los mismos
> bytes en los dos sitios. MEDIDO: al escribir este documento, el instrumento lo
> auditó a sí mismo yándolo `DIVERGIO`, porque su bloque de ejemplo es
> sintácticamente idéntico al de su cabecera.
>
> Y **la vía barata no funciona**: la sangría NO discrimina, porque los **99**
> campos de procedencia del árbol están **todos** en vallas de sangría 0, y el
> bloque de ejemplo también. Así que el opt-out es explícito y va en el *info
> string* de la valla — `ejemplo`, `cita`, `citado`, `no-sellar`, `ilustrativo`
> — que es donde markdown guarda esa información. Una heurística habría sido
> más cómoda y habría sido una suposición vestida de regla.
>
> Antes de esta reparación el mismo papel lo hacía elidir el digest, como en
> `ATOMBIOS-DECODER.md:331` (`sha256 c80bb5ff...402f150`). Funciona a medias:
> quita el `DIFIERE` pero no el `DIVERGIO`, porque `herramienta <path> 1.0.0`
> sigue siendo un campo bien formado. **La convención del digest elidado se queda
> como suplementaria; la marca es la que manda.**

Eso es trabajo de edición, es pequeño, y **no lo hago en esta iteración** porque
mezclar la reparación de un documento con la escritura de otro sobre el mismo
fichero es la forma de que los dos salgan mal.

## 4 · LAS MUTACIONES

```text
M25  la distincion se borra y todo vuelve a DIFIERE   -> FALLA V5
M26  misma version con otros bytes se marca DIVERGIO    -> FALLA 14 vectores
M27  la marca de cita se ignora                        -> FALLA V21b
```

`M27` es la tercera vía por la que este trabajo ha tenido que añadir vectores: la
marca de cita es una **bifurcación**, y una bifurcación sin vector es una
bifurcación que nadie ha probado. El vector `V21d` cubre el otro lado —`ejemplo`
escrito *dentro* de la valla, no en el info string, **no** marca— que es el modo de
equivocarse que haría falta para que la marca fuera un parche.

`M26` es la importante, y es la que **no habría existido sin el vector nuevo `V5b`**:

```text
  herramienta   her.py 1.0.0      <- la versión coincide
  sha256        aaaaaaaaaaaaaaaa  <- los bytes NO
```

Eso es `DIFIERE` y no `DIVERGIO`, y es el caso grave. Sin `V5b` un instrumento
podría marcar como *"el fichero evolucionó"* el caso de **alguien que editó un
artefacto sin subirle la versión**, que es el escenario para el que un sello existe.

`V5` es el espejo: versión equivocada con bytes correctos, que es exactamente mi
caso, y es `DIVERGIO`.

**54 vectores, 0 fallos.**

## 5 · Lo que NO hace esta reparación

- **No corrige los bloques de `1057` ni de `1058`.** §3 dice por qué y qué es lo que
  haría falta.
- **No cambia el `rc`.** `DIVERGIO` sale por `rc=3`, igual que `AMBIGUO` y
  `SIN_RECETA`: se ve y se cuenta, no bloquea.
- **No re-sella nada**, y no toca el manifiesto de evidencia.
- **No implementa la regla del ancla.** `DIVERGIO` **detecta** la divergencia; no
  impide que alguien escriba un bloque que apunte a una versión que no existe, que es
  el caso `MALFORMADO` que ya estaba covered.
- **No toca la GPU, ni el driver, ni mide rendimiento.**

## 6 · PROCEDENCIA

```text
regla     audita_campo(), rama de campos portador, version != VERSION del fichero
vectores  V5  version equivocada + bytes correctos -> DIVERGIO
          V5b version correcta + bytes equivocados -> DIFIERE
mutaciones M25 (se borra la distincion)  M26 (se invierte)   las 2 detectadas
medida    1057/1058 sobre el arbol real: 2 DIVERGIO, 4 DIFIERE, 2 EXISTE
self-test 54 vectores, 0 fallos
escrituras 0 en el arbol.
```

**Lo que este documento NO prueba.** No prueba que la distinción sea útil en general:
la tengo sobre **cuatro casos de dos documentos**, todos míos, y dos de ellos
consecuencia de la misma causa. No hay todavía un caso real de "editado sin subir la
versión" en este árbol, así que `DIVERGIO` está **observado pero no discriminado por
un caso positivo ajeno**. Y no prueba nada sobre la GPU ni sobre rendimiento.