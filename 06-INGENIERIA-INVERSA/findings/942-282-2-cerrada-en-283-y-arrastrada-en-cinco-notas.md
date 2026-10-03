# 942 — `282-2` estaba cerrada desde la nota 283 y la arrastré como abierta en cinco notas. El instrumento que lo detecta está construido

Estado: `PROVEN` el error propio. Herramienta nueva: `fronteras.py`, 12 de 12.
Alcance: `06-INGENIERIA-INVERSA/findings/`, 446 notas.
AUTORIA=AGENTE-SMU

## Qué pasó

Iba a empezar a trabajar en `282-2` —«¿se puede leer y escribir sin carrera?»— porque la había listado
como el más barato de los frentes abiertos. Buscando el enunciado exacto encontré la nota `283`, y su
último párrafo dice:

```
PENDIENTE=282-2 | ESTADO=RESOLVED por esta nota
           | RESOLUCION=buffer de dos regiones disjuntas; control 40/40
```

**Estaba cerrada.** Los tres kernels escribían su resultado en `d[i]`, dentro de la misma región que
recorrían leyendo; partiendo el buffer en dos regiones contiguas y disjuntas, el control pasó de
**0 de 40** a **40 de 40** en las tres configuraciones que fallaban.

Y yo la había listado como abierta en las notas **928, 930, 933, 934 y 938**. Todas escritas después
del cierre. Todas copiando la lista de la anterior.

## Por qué no es un fallo de búsqueda

Esto no es «no fui a mirar». El bloque `PENDIENTE` de `282` estaba en el fichero, y también estaba en
`283`. Lo que hice fue leer el `PENDIENTE` de `282` al abrir el trabajo, anotarlo como abierto, y
copiarlo. **El `PENDIENTE` se lee una vez, al abrir el frente; después solo se propaga.**

Es la diferencia entre una frontera y una frontera-NEXT: una frontera es un estado que alguien tiene
que mantener, y si el mantenimiento es manual y silencioso, se pudre. Lo más grave no es que la
llamara abierta: es que **cinco notas mías son menos útiles de lo que parecen**, porque ofrecen trabajo
que ya está hecho.

Y hay un agravante concreto: `283` **corrobora** el discriminante de `282` con instrumento válido
(razones VRAM/RAM de 1,0086, 0,9977 y 1,0013 con control 11 de 11). Es decir, la nota que cerraba
`282-2` también reforzó el titular de `282`, que es lo que yo iba a volver a medir en `933` sin
saber que ya estaba corroborado dos veces.

## El instrumento

`fronteras.py`, en `08-ARQUITECTURA/tools/`. Hace dos passes y los separa porque son cosas distintas:

1. **La línea de verdad.** Todo bloque `PENDIENTE=<id> | ESTADO=<estado>`, en orden de nota. Es la
   cronología autoritativa de cada frente.
2. **Las menciones en prosa.** Cualquier línea que hable de un id con palabras de estado («sin tocar»,
   «más barata», «abierta», «siguen como estaban»). No mandan, pero es **donde se propaga el error**,
   y por eso hay que mirarlas aparte.

Un frente es **rancio** cuando su último estado es cerrado y una nota *posterior* vuelve a hablar de él
como si estuviera abierto.

```
--- RUNCIAS ---
  282-2  cerrado en la nota 283 con ESTADO=RESOLVED por esta nota
      nota 928   ... Sin tocar, y mas barata que `282-1`.
      nota 930   ... sigue sin tocar y es más barata que ...
      nota 933   ... sin tocar, y más barata que ...
      nota 934   ... sin tocar, y más barata que ...
      nota 938   ... sin cambios, siguen como estaban.
  1 rancias
```

Ahora: **0 rancias**. Las cinco correcciones están hechas.

## Los cuatro fallos del instrumento, que son la parte útil

**1. El parser por posición encontraba 5 ids de 65.** Exigía `ESTADO=` justo después del primer `|`, y
las declaraciones reales llevan un `HALLAZGO=` en medio:

```
PENDIENTE=246-1 | HALLAZGO=246-*.md | ESTADO=NOT_DETERMINED
```

Ahora parsea **por campos**, no por posición: divide en `|`, busca el campo `PENDIENTE=` y el campo
`ESTADO=` estén donde estén. **29 declaraciones reales de 65 apariciones**, y las 36 restantes son la
palabra «pendiente» en prosa — verificado una a una, no supuesto.

**2. `PENDIENTE=` en prosa entraba en la cronología.** El marcador es un *campo*, no una subcadena.
Ahora una línea solo cuenta como declaración si **los dos** campos están en ella.

**3. Mi propio agrupamiento de estados estaba mal, y lo vi porque el informe imprime los estados
crudos.** Había puesto `NOT_IMPLEMENTED` en el conjunto de los que cierran. Es falso:
`NOT_IMPLEMENTED` es el primer paso de la cadena de estados de una implementación (§87), o sea que
dice que **no** está hecho. Contarlo como cierre dejaba **5 frentes fuera de la lista de abiertas**.

Por eso el informe imprime la tabla cruda en vez de solo el veredicto: una agrupación sostenida con un
veto propio que nadie discutió es una clasificación que se traga uno. Al verla, estaba mal.

**4. El linter señaló su propia corrección como defecto.** Al tachar las cinco menciones con `~~`, el
scáner siguió viendo «sin tocar» dentro del tachado y reporto las cinco como rancias. La corrección se
había escrito de una forma que el instrumento no entendía.

El arreglo correcto es que **el instrumento entienda la convención**, no que la nota se escriba de otra
forma: `~~...~~` es historia, no afirmación. Un linter que señala su propia corrección como defecto
obliga a corregir sin conservar el contexto, y eso es peor que el defecto.

Y el vector del self-test que lo veto también estaba mal: tenía las palabras de estado **fuera** del
tachado, así que no vetaba nada. **Un veto que no veto es peor que no tenerlo**, porque ocupa una línea
del self-test y da la impresión de que hay una garantía.

## Límites, y son reales

- Solo lee `findings/*.md`. No toca el corpus.
- Hay **13 estados distintos en uso** y no todos significan lo mismo. Este informe los agrupa por
 familia y muestra el crudo; no decide cuál es el correcto. La agrupación es discutible y la tabla
  está ahí para que se pueda discutir.
- **Cuatro declaraciones reales se escapan**: en las notas 115 y 220 el `ESTADO=` está en la línea
  siguiente. Un frente sin estado no puede ser rancio, así que quedan fuera del control. No se ha
  No esta arreglado; esta anotado.
- No decide cuál de dos notas tiene razón. Solo señala que se contradicen.

## Instrumentos

`08-ARQUITECTURA/tools/fronteras.py`, 12 de 12, con veto propio sobre `NOT_IMPLEMENTED` y sobre `~~`.
Los vectores del self-test salen de notas que existen: el caso bueno es `282-2` cerrado en 283, y el
caso malo es exactamente el mismo.

## Lo que este instrumento compra

Hay **18 fronteras abiertas de verdad** según la cronología, y cinco de ellas son `NOT_DETERMINED` de
notas 246–262, es decir de hace tiempo. La lista abierta real es corta y ahora es fiable, que es la
condición para que un planificador sirva de algo.

Un frente que nadie cierra es peor que un frente que nadie abre, porque ocupa el planificador.

## Lo que queda abierto

- **Las 4 declaraciones con `ESTADO=` en la línea siguiente**, fuera del control. Barato: el parser
  puede mirar el bloque completo en vez de la línea.
- **`271-1` está en `REOPENED` desde la nota 276** y `277-1` y `281-1` en `OPEN` desde su nota de
  origen. Son los tres mas antiguos del conjunto. `271-1` es el mas relevante porque `REOPENED` significa
  que alguien decidió reabrirlo y no consta que se cerrara.
- **El resto de la lista abierta**: 246-1, 253-1, 254-1, 255-1, 257-1, 258-1, 258-2, 258-4, 261-1,
  262-1, 262-2, `ABC-NO-CERRABLE-DESDE-CORPUS`, `D-ORDEN-EJECUCION-INVALIDACION`. Ninguna mirada en
  esta vuelta.
