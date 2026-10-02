# 125 · Casi la mitad de las afirmaciones de multiplicidad del corpus no son corroboraciones

```text
PENDIENTE=17-INFLADAS-DE-CORROBORACION | HALLAZGO=125-casi-la-mitad-de-las-multiplicidades-no-son-corrobora.md | ESTADO=NOT_DETERMINED | NECESITA=CORPUS | ALCANZABLE_SIN_ROOT=si
```

## Las 17 candidatas INFLADA_DECLARADA de este hallazgo no son legibles por
maquina: la ventana de +-2200 caracteres las tasa mal en los hallazgos
largos. Decidir cual es deuda real exige leer, y son 17 filas. No se ha
hecho, y por eso no se afirma que sean infladas.


`CLASSIFICATION=METHODOLOGY` · `TRACK=STATIC` · `WORK_CLASS=READ_ONLY/EVIDENCE`
`WRITE_EXECUTION=NONE` · `MODIFICATIONS=0` · `RUNTIME=NOT_RUN` · `GPU INTACTA`
`HERRAMIENTA_NUEVA=tools/corroboration.py` (`TOOL_VALIDATED`, 16 vectores)
`CONTINUES=122` · `GENERALIZA=122` (que dejó "la cuenta es de este paquete" sin medir)

## Cuestión principal

`122` encontró que una marca afirmaba `PROVEN` por «dos familias de headers
independientes» y la afirmación era cierta para 3 de 4 campos. Su propio
confounder decía: *«la cuenta es de este paquete»*.

La pregunta es: **¿cuántas afirmaciones de multiplicidad hay en los 207
hallazgos, y cuántas de las que dicen "N fuentes" son realmente N fuentes?**

## Criterio de terminación

Buscar el sintagma de multiplicidad con su número declarado, y comprobar si el
texto nombra al menos esa cantidad de ficheros distintos. **Cumplido: 67
afirmaciones, y 32 de ellas no son corroboraciones.**

## Respuesta

```
DENOMINADOR_DE_UN_NEGATIVO   32   47.8 %
INFLADA_DECLARADA            17   25.4 %
RESPALDADA                   15   22.4 %
NO_COMPROBABLE                3    4.5 %
```

**Casi la mitad de las afirmaciones de multiplicidad del corpus son alcances de
medición, no redundancias.** El caso canónico es `018:194`:

```
| Que GFX8 no expone ack de invalidación | `PROVEN_ABSENT` | 5 cabeceras GMC, 0 coincidencias |
```

«5 cabeceras» ahí es **el denominador de un resultado negativo**: se
buscaron cinco cabeceras y hubo cero coincidencias. Leído como afirmación de
corroboración produce un `INFLADA_DECLARADA` sobre un texto que dice
literalmente `0 coincidencias` y `PROVEN_ABSENT`. Y ese hallazgo tiene 188
líneas mencionando `_sh_mask.h`: las cinco fuentes **sí** están nombradas, en
una tabla fuera de la ventana de mi lectura.

Sin la clase de exclusión, las 17 «infladas» son ruido. Con ella quedan 17, y
**no he verificado una por una**: son candidatas, no deuda.

## La ambigüedad de fondo: «N fuentes» significa dos cosas

«N cabeceras» es:

1. **el alcance de una medición** —«busqué N y encontré M»— o
2. **una redundancia** —«N fuentes independientes confirman»—

y el proyecto usa las dos con la misma frase. La distinción no está escrita
en ninguna parte y la herramienta tiene que deducirla del contexto, que es
por lo que su clase es `DENOMINADOR_DE_UN_NEGATIVO` y no `NO_ES_CORROBORACION`:
es una inferencia, no una convención.

**Regla**: cuando se escriba «N fuentes», decir de qué son esas N: el alcance
de una búsqueda o la cantidad de fuentes que se corroboran.

## `034`: la palabra «independientes» en el documento que ya cayó por un contraste falso

De las 17 candidatas, una merece nombrarse porque es el caso donde el término
tiene más peso del que se ha ganado:

```
034:14   Eso da DOS fuentes de verdad independientes dentro del corpus:
         el comentario que documenta el paquete, y el codigo que lo emite.
         Y coinciden 28/28, sin una sola discrepancia.
```

**`034` no tiene ninguna sección de corrección**: ni `CORRECTED_BY`, ni
`CORRIGE`, ni `RETRACCIÓN`. La afirmación está viva.

Y es el documento con **un contraste falso ya demostrado**. Su variante de
`count` fue retractada porque el «los otros dos productores de esta ASIC
concuerdan» **leía también `sdma_v4_0.c`**. El texto que lo dice está en un
comentario de `07-DRIVER/kernel/rx550_pm4.c`, es decir **fuera** del hallazgo
Y es el documento con **un contraste falso ya demostrado**. Su variante de

**Matiz que debo a la evidencia y no a la retórica**: `cikd.h` y el `.c`
emisor **son ficheros distintos**, no dos partes del mismo fichero — lo
verifiqué después de suponer lo contrario. Lo que no los hace independientes es
otra cosa, y es más fuerte: un comentario que documenta un layout y el código
que lo implementa son **una especificación y su implementación**. Si el
comentario está mal, el código coincide con él porque ambos descienden de la
misma especificación, no porque se hayan medido el uno contra el otro. La
ausencia de discrepancia entre specification e implementación **no es una
prueba**: es lo que se esperaría aunque ambas estuvieran equivocadas.

## Clasificación

| afirmación | estado |
|---|---|
| 67 afirmaciones de multiplicidad en 207 hallazgos | `MEASUREMENT` |
| 32 (48 %) son denominadores de un resultado negativo | `MEASUREMENT` |
| 17 declaran más fuentes de las que nombran en la ventana | `MEASUREMENT` — candidatas, **no verificadas una a una** |
| «N fuentes» es ambiguo entre alcance y redundancia | `PROVEN` — caso canónico `018:194` |
| Que las 17 sean infladas de verdad | `NOT_DETERMINED` — el ruido de la primera versión era del 20 %, y esta clase tiene el mismo riesgo |
| `034` no tiene sección de corrección | `PROVEN` — 0 coincidencias de `CORRECTED_BY`/`RETRAC` en el fichero |
| `034` llama «independientes» a un par especificación/implementación | `PROVEN` — `034:14-16`, `034:104-112` |
| Que eso invalide el 28/28 | `NOT_DETERMINED` — el recuento puede seguir siendo correcto; lo que no se sostiene es la palabra «independientes» |
| Que `doc` y `real` estén en ficheros distintos | `PROVEN` — `cikd.h` y el `.c` emisor |

## Confounders

- **La ventana es ±2200 caracteres, no el documento.** Una fuente nombrada en
  un apartado distante cuenta como no nombrada, y eso infla `INFLADA_DECLARADA`
  justo en los hallazgos largos, que son los más scrupulosos. El primer
  primer intento de esta herramienta decia 20 infladas y las tres primeras
  eran ruido: un `grep`, un puntero `CONTINUES=` y un glob.
- **La ventana es la causa de que la primera versión pareciera AIP.** Y es un
  recordatorio de que un filtro que acepta un comando como nombre de fichero no
  mide: cuenta.
- **No se ha aplicado este criterio a otro paquete.** `WAIT_REG_MEM` no es el
  único; `SET_SH_REG` o `INDIRECT_BUFFER` pueden dar otro reparto.
- **La detección de sintagma es léxica.** No distingue «dos fuentes» de «las
  dos fuentes de arriba», y la segunda se cuenta una vez.

`WRITE_EXECUTION=NONE`. `MODIFICATIONS=0`: el árbol de Linux 7.2.8 no se ha
tocado. `GPU INTACTA`.