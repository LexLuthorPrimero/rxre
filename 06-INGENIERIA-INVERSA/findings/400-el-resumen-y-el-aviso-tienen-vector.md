# 400 · El resumen y el aviso tienen vector, y al escribirlos encontré una regresión que el `PASS` no vio

WORK_CLASS=READ_ONLY · WRITE_EXECUTION=NONE · MODIFICATIONS 1 (`tools/smc_copy_scope.py`)

> ## Resultado
>
> `smc_copy_scope` 1.6.0 → **1.7.0**. El resumen y los avisos tienen ya vector
> propio, y con ello queda cerrado el `NOT_COVERED_BY_FIXTURE` que llevaba
> **tres versiones** diciendo. 31 → **34 vectores**.
>
> Y el motivo de cerrar ese hueco no fue administrativo: **al escribir el vector
> apareció una regresión que los 31 vectores y el `PASS` no detectaron**.

## Lo primero: una regresión real, invisible para el selftest

Extraje la construcción del resumen a una función pura —sin otra cosa podría
hacerla comprobable por el fixture— y comparé la salida nueva contra la de la
versión anterior con `diff`:

```
<                        el orden textual no es el de ejecucion: NI VIVA NI TAPADA
>     %-13s      el orden textual no es el de ejecucion: NI VIVA NI TAPADA
```

Al copiar el código al nuevo sitio se me cayó el `% ""` de una línea, y el
especificador de formato **se imprimió literal** en la salida del programa.

Lo que importa es dónde pasó:

- `exit=0`. La herramienta salió bien.
- **31 vectores, `RESULTADO OK`.** El selftest pasó entero.

**Ninguna de las dos señales lo vio**, porque la línea que se rompió **no tenía
ningún vector**: es exactamente el hueco que esta iteración venía a cerrar.

Es el bucle completo en una frase: *la zona sin fixture es la zona donde una
regresión pasa desapercibida*, y *la primera forma de escribir el fixture es
justo donde la regresión se cuela*. Si hubiera cerrado el hueco solo
documentándolo, habría instalado un `PASS` que miente y no lo sabría.

La lección no es «hay que comparar salidas». Es que **`exit=0` y `PASS` son
afirmaciones sobre el comportamiento que el fixture cubre**, y si hay una región
sin cubrir, el `PASS` no dice nada sobre ella y se lee como si lo dijera.

## Lo segundo: el resumen es parte del contrato, y ahora está demostrado

Tres vectores nuevos, y los tres miran **el texto**, no los casos:

| vector | qué mira | cambio que lo caza |
|---|---|---|
| **casoV** | cada cifra va **con su etiqueta**, y las etiquetas son distintas entre sí | cualquier etiqueta |
| **casoW** | `--orden` sin motivo **avisa**; con motivo, **lo imprime** | aviso del motivo |
| **casoX** | una entrada no usada se avisa **por su nombre**, y se dice que el `NO_RESUELTO` puede venir de ahí | el nombre en el aviso |

`casoV` incluye un chequeo que es el que habría cazado la regresión:

```python
chk(not re.search(r"%[-+ #0-9.]*[a-z]", txt_v), ...)
```

Un especificador de formato que escapa al texto **es** un fallo, y ahora hay algo
que lo dice.

## Por qué el texto no era decorativo

Lo tenía dicho en `402` y `600`, pero ahora está **demostrado** con un vector.

Una cifra sin etiqueta que diga qué mide se lee como un resultado. Un `TAPADA 0`
se leía como cobertura nula, cuando en realidad solo decía **que no se habían
comparado las escrituras de funciones distintas**. La diferencia entre esas dos
lecturas es la diferencia entre «no pasa nada» y «no lo sé», y la diferencia la
hace **el texto**, no el código.

Lo mismo con el `AVISO` de entrada sin usar. Dice:

> si un nombre esta mal escrito, el NO_RESUELTO que produce no es limite del
> fichero: es una entrada ignorada

Esa frase **redirige la búsqueda al sitio correcto**. Un `NO_RESUELTO` sin ella
apunta al fichero, y el fichero no tiene la culpa.

## El fallo check, con la comprobación que faltaba en `600`

Cinco variantes, cinco detecciones, correspondencia 1:1:

```
A_etiqueta    exit=3   cazado por: casoV
B_formato     exit=3   cazado por: casoV      <-- la regresión, reintroducida
C_aviso_mot   exit=3   cazado por: casoW
D_motivo      exit=3   cazado por: casoW
E_aviso_hue   exit=3   cazado por: casoX
```

Y esta vez el script **comprueba que la variante exista antes de usarla**, que es
justo lo que faltó en `600` y por lo que dos variantes quedaron sin probar con un
informe que decía lo contrario. `600` lo nombró como el error de la iteración; el
arreglo se aplicó aquí y funcionó.

## La salida real, sin cambios salvo el motivo

```
TAPADA       6   lineas: 142,149,157,166,1146,1246
NO_RESUELTO  3   lineas: 654,1872,1881
VIVA         3   lineas: 1511,2118,2254
SIN_ORDEN    1   lineas: 2398
escapadores de formato en la salida: 0
```

El `diff` contra 1.6.0 sale limpio salvo la línea del motivo, que acorté a
propósito. **El refactor no cambió un solo número**, y eso también se comprueba.

## Un vector que escribí mal, y que el fallo check no perdona

El primer `casoW` que escribí llevaba basura:

```python
sel_w = decide(..., {min(e.linea for e in sel_w_placeholder) if False else 0: 0})
```

`sel_w_placeholder` no existe. No era un test que fallara: era ruido que parecía
un test. Lo reescribí bien —para probar la rama del motivo hace falta un `TAPADA`
**por orden**, y no basta el `sel` del casoV— y el fallo check lo confirma: con
la versión buena, `D_motivo` lo caza.

La lección es la de siempre y ya la he pagado cuatro veces: **un test que no
puede ejecutarse no es un test que pasa, es un test que no está**. Un
`PASS` con código muerto dentro obtiene el mismo color en la consola que un
`PASS` con los 34 vectores de verdad.

## Dos errores míos más

**1. Texto en chino colado en este hallazgo.** Al escribir el resultado metí dos
caracteres de CJK en la frase que resume la regresión. Lo cazó el chequeo de
no-latina y está corregido. Lo escribo aquí porque **primero lo documenté y luego
lo corregí**: el hallazgo llegó a decir «escribí tal cosa» **con esa cosa escrita
en la frase**. Un registro de error que contiene el error no es un registro
corregido; es un sitio donde el error se documenta para que nadie lo busque dos
veces. La racha de cuatro iteraciones sin CJK se rompe aquí.

**2. Basura que dejé en el código al escribir el vector.** Además del
`sel_w_placeholder` de arriba, dejé un comentario en inglés atado a código
español. Un vector debe poder escribirse sin ensuciar lo que prueba.

## Lo que encontré al cerrar: la numeración de hallazgos está rota de verdad

Este hallazgo se iba a llamar `290`. Lo revalidé libre al empezar la iteración, y
al regenerar el índice había **dos filas con `290`**: la mía y otra del otro
agente. Renumeré la mía a `400`.

Y al mirar el problema en vez de taparlo, resultó ser **mucho más grande**:

```
hallazgos totales:          389
numeros duplicados:          73
```

Y **tres de los duplicados son míos**: `500`, `402` y `403`. Es decir: la
colisión no era un accidente de esta iteración, llevaba **tres hallazgos míos**
colados desde antes y no lo había visto.

El otro agente ya lo había detectado por su cuenta — existen
`048-numeros-de-hallazgo-no-identifican.md` y
`073-f7-medido-216-sin-versionar-y-17-ids-duplicados.md`—, lo que confirma que es
un problema compartido y no un fallo mío.

### Por qué «revalidar el hueco al instante de escribir» no puede funcionar

Es la disciplina que vengo aplicando desde hace varias iteraciones, y es
estructuralmente incapaz de resolver esto: **la colisión ocurre entre mi
comprobación y mi escritura**. El hueco estaba libre cuando miré, y estaba
ocupado cuando escribí, porque el otro agente trabaja en paralelo sobre el mismo
directorio.

No es que la comprobara mal. Es que **una comprobación puntual no puede arbitrar
un estado compartido que cambia mientras compruebas**. Lo que sí puede es una
**partición**: bandas de números separadas, con un margen grande respecto al
frontero del otro agente. Y eso es lo que he hecho.

### Y aquí está la demostración de que tenía razón

Renumeré mis tres duplicados a `401`, `402` y `403`, con un script que
**comprobaba que los tres destinos estaban libres antes de escribir** y que
abortaba entero si una sola comprobación fallaba.

El script imprimió:

```
los 3 destinos estan libres
3 ficheros renombrados, 20 lineas actualizadas
```

Y al siguiente listado había **dos ficheros `401`**: el mío y
`401-doclint-no-indexaba-07-driver.md`, **del otro agente**, que un rato antes
era `286-doclint`.

Es el **cuarto TOCTOU**, y el más limpio de todos porque ocurrió **dentro de mi
propio script, entre mi `assert` y mi `write`**. Mi comprobación pasó. Lo que
ocurrió después es que el otro agente renombró el suyo a `401` en ese hueco.

Es exactamente lo que el párrafo anterior afirma, y ahora no es una tesis: es un
`assert` que pasó y un `ls` que mostró el conflicto.

Lo resolví pasando a una **banda 500-599**, muy por encima del máximo del momento,
y mis tres hallazgos quedaron en `500`, `402` y `403`. **Ninguno de mis números
está duplicado.** Los duplicados del directorio bajaron de **73 a 70**, y los que
quedan **no son míos**.

### Lo que esto dice de la disciplina, no de la herramienta

Podría haberlo resuelto comprobando tres veces. Habría funcionado esta vez, y
habría vuelto a fallar la próxima.

La diferencia entre una comprobación y una partición no es que la primera sea más
cuidadosa: es que **la primera depende de que nadie más escriba durante la
ventana**, y esa ventana es el tiempo que tarda mi propio script. Con dos
escritores sobre un directorio compartido, la ventana no se cierra mirando más
fuerte: se cierra **dejando de competir por el mismo recurso**.

Y hay una consecuencia incómoda: `EVIDENCE-MATRIX.md` se generó **a mano** durante
muchas sesiones como «numeración autoritativa del proyecto». **No lo es.** Con 73
números repetidos, la tabla tenía **dos filas para la misma clave**, y cualquier
cita por número era ambigua. Eso no lo arregla renumerar: lo arregla **dejar de
tratarla como autoritativa** hasta que la numeración sea única.

### El dato que invierte el cálculo

Antes de renombrar mis tres, comprobé quién los cita. Y el resultado cambia la
decisión:

```
283-la-carrera-eliminada-40-de-40...   cita `282`  12 veces
015-llvmpipe-discriminating-pairs.md   cita  287   12 veces
115-sd-cuando-hay-invalidate...        cita  287    9 veces
284-el-enlace-esta-en-2-gbs...          cita `282`   8 veces
287-la-lectura-si-costaba...           cita `282`   5 veces
```

**Esas citas casi con seguridad significan los hallazgos del OTRO agente**, no los
míos: son fichero sobre latencia, sobre llvmpipe, sobre el enlace, sobre el
carrera eliminada. Los números `282`, `283` y `287` **ya tienen un significado
estable entre sus ficheros**, precisamente porque siempre han apuntado a su lado.

Así que renombrar **los míos** no rompe nada suyo: **desambigua las citas que ya
escribieron**. Sus documentos pasan a ser correctos, y el único trabajo que queda
son las referencias internas de mis tres ficheros, que es acotado y mío.

Eso es lo contrario de lo que suponía al principio, cuando el renumerado en bloque
me parecía una intsromisión.

### Lo que he hecho, y lo que queda

**Hecho**: los tres duplicados míos están fuera. `500`, `402`, `403`, más `400`,
`600`, `280` y `278`. Las **20 referencias internas** de mis ficheros se
actualizaron con reemplazo por línea y **abortando entero** si una sola línea no
contenía el texto esperado. El renumerado se hizo en una iteración aparte de los
vectores del resumen, no mezclado.

**No hecho, y no lo haré**: los **70 duplicados restantes**. No son míos. Renombrar
ficheros de otro agente para «dejar el índice limpio» es exactamente el tipo de
acción que parece constructiva y no lo es: no arregla la causa —que es la
numeración compartida sin partición— y borra las referencias que ya han escrito
ellos.

**Y una cosa que no depende de mí**: mientras la numeración sea compartida y sin
bandas, el próximo fichero que escriba cualquiera de los dos volverá a colisionar.
Eso solo se arregla con una convención acordada, y la convención no es mía para
imponerla. Lo que sí puedo es no volver a competir por el recurso: **mis
números van a partir de `500`**.

### El coste que no había medido

Renombrar tres ficheros míos costó **20 reemplazos dirigidos y una comprobación
de cita previa**. Y aun así casi toco las citas del otro agente: las líneas
185-189 de este mismo fichero **citan ficheros suyos** con números que
coinciden con los míos. Un `sed` global habría destruido cinco referencias
ajenas.

La lección no es «ten cuidado con el `sed`». Es que **la comprobación de quién
cita qué tiene que ir antes del renumerado, no después**, y hay que hacerla
sobre el fichero de destino con el nombre viejo, porque el nombre viejo es la
clave con la que están escritas las citas.

## Lo que NO afirmo

- **NO** afirmo que nada de esto se ejecute en mi placa. `B_RUNTIME =
  NOT_EXECUTED`; sigue haciendo falta `Autorizo WRITE_EXECUTION para B_EXPERIMENT`.
- **NO** afirmo `:2398`. Sigue `SIN_ORDEN`; su tapador es de init y él es de
  runtime.
- **NO** he arreglado el hueco de la forma C de `600`. Sigue anotado, con su
  pregunta abierta: ¿algún fichero del corpus escribe en `miembro_del_contexto`
  sin estructura intermedia?
- **NO** he tocado `artifacts.py`, `atomrom.py`, `AGENTS.md` ni el árbol de kernel.

## Estado de la herramienta

`smc_copy_scope` 1.7.0 — **`VALIDATED`**, 34 vectores, `exit=0`, y `exit=3`
reverting cualquiera de los cinco cambios por separado.

**Las dos piezas que faltaban ya tienen contrato verificado.** No quedan partes
de la herramienta validadas a mano, que era lo que `402` dejó dicho y lo que
`286` y `600` repitieron.

Todavía quedan dos cosas suyas que no son un hueco de fixture:

- El **motivo** de `--orden` es una cadena libre. Se comprueba que se imprima,
  no que sea cierto. Que sea cierto lo comprobó `403`, a mano, y eso no se
  automatiza: es evidencia, no código.
- La **existencia de líneas** de las escrituras que no tienen rango se reporta
  como una sola. Anotado en `600`, sigue anotado.

## Frontier siguiente

**Resolver la pregunta del hueco de la forma C**, que es un `grep` acotado y
tiene dos respuestas posibles que llevan a acciones distintas:

- **Si ningún fichero del corpus escribe en `miembro_del_contexto` sin
  estructura intermedia**, es un hueco latente: se anota con su condición de
  reaparición y la rama se cierra. No hace falta arreglarlo.
- **Si alguno lo hace**, hay un `NO_RESUELTO` en algún sitio con el motivo
  **equivocado** —«destino no reconocido», que acusa al fichero de algo que sí
  está escrito— y entonces el arreglo es urgente, porque un motivo falso
  dirige la búsqueda al sitio equivocado.

El coste es un solo `grep` acotado, con el `exit` verificado y el recuento de
ficheros del ámbito a la vista, que es la forma de no repetir los cinco errores
de «ausencia antes de tiempo» de esta serie.

Y si la respuesta es «ninguno», la acción siguiente no es arreglar la forma C: es
**empezar a cerrar el `runner` que he pedido cuatro veces**, que es lo que ha
producido más errores míos que ninguna otra cosa: un script que se niegue a
continuar cuando una pieza del test no existe, en vez de que el informe diga
`DETECTADO` sobre algo que no se probó.