# 186 · «682 afirmaciones abiertas» no era un resultado: 392 eran filas de tabla, y de las 293 de prosa sólo 22 llevan la marca en su propia frase

```
CLASSIFICATION=TOOLING+MEASUREMENT · TRACK=VERIFICATION
CORPUS=RESEARCH/working/linux-7.1.3 · HARDWARE_SCOPE=NONE
WORK_CLASS=READ_ONLY/EVIDENCE · WRITE_LOCAL=PROPIOS · MODIFICATIONS_CORPUS=0
RUNTIME=NOT_RUN · GPU INTACTA · CERROJOS=0
```

## Qué resuelve

Este hallazgo empieza siendo un intento de elegir la siguiente tarea, y termina
siendo sobre por qué **no se puede elegir con esa herramienta**. Que es más
útil, porque la elección de tarea es el punto donde un número falso se convierte
en trabajo equivocado.

`tools/frontier.py` responde «qué hace falta para cerrar cada hueco». Su titular
era:

```
afirmaciones abiertas: 685
  clases: NOT_DETERMINED=656, NOT_PROVEN=21, UNKNOWN=8
```

Y ese titular **no era defendible**, por tres razones medidas.

## 1 · El 57 % no son afirmaciones

```
de las cuales FILAS DE TABLA, que no son afirmaciones: 392 (57%)
prosa real: 293   con marca en su propia frase: 22 (8%)
```

Una fila de tabla es esto:

```
| Cuánta VRAM física tiene la placa por detrás de la de arranque | `NOT_DETERMINED` |
```

Eso es **una celda**. No tiene verbo, no termina en punto, y su estado lo decide
la columna de al lado, no el texto. La herramienta la extraía como si fuera una
frase y la clasificaba por su contenido, lo que produce etiquetas con apariencia
de accionables y sin base: de las 22 afirmaciones con marca fuerte, **39 sobre 61
eran filas** en el recuento anterior.

La causa es mecánica y ahora está marcada: `claims.py` no distinguir una fila de
una frase, porque el extractor no mira la línea de origen. Ya lo hace
(`es_fila`), y `frontier.py` lo propaga.

## 2 · La clasificación no puede elegir la tarea

Después de excluir filas quedan 293, y de ésas **22** llevan la marca en su
propia frase. Las otras 271 se clasifican desde el párrafo, la sección o el
documento entero — y el propio `frontier.py` avisa de que ésa es la forma más
débil, porque el contexto se propaga:

```
    'fuerte' = la marca aparecio en la FRASE del propio hueco. Si vino
    del parrafo, de la seccion o del documento entero, baja puntos,
```

Es decir: **la herramienta dice que su mayoría de etiquetas son de la forma
débil**, y el titular no lo decía. Con la vía desglosada sobre las 22 fuertes:

```
RUNTIME_ACTIVO 9 · SPEC_NO_PUBLICADO 6 · POR_DEFINICION 4
DIFERENCIAL 2 · UN_REGISTRO 1
```

Y el caso fuerte que queda para «cerrar leyendo un registro» está mal
clasificado. Lo comprobé leyendo el fichero, no la extracción:

```
045-la-convencion-de-count-nunca-se-midio-en-mi-asic.md:142
  marca en la frase: "…cuya resolución depende de un registro. Cerrarlo es un
  RUNTIME con discriminante claro, o…"
  registros nombrados por la frase: []
```

La frase dice **RUNTIME** y no nombra ningún registro, y está clasificada como
`UN_REGISTRO`. **Una de una, mal.** Y `frontier.py` nombra precisamente ese caso
como el más débil que tiene: *«deducir la via solo de que la frase menciona un
registro»*.

## 3 · Qué se arregló y qué no

**Arreglado en el instrumento:**

- `claims.py` marca `es_fila` en cada afirmación, mirando la línea de origen.
- `frontier.py` propaga la marca y **el titular lleva su propio denominador**:
  cuántas son filas, cuántas son prosa, y cuántas llevan marca fuerte.
- Dos filtros nuevos, `--prosa` y `--fuerte`, que se aplican **antes** de contar
  y no después. Un filtro que actúa sobre el informe deja el titular diciendo una
  cosa y la tabla otra, y la tabla es la que se lee.

**No arreglado, y hay que decirlo:**

- La clasificación por palabras sigue siendo por palabras. Filtrar deja 22, pero
  **1 de 22 está mal clasificada**, así que el error del clasificador no se
  corrige con un filtro: se corrige leyendo. Y ahora se sabe cuántas hay que
  leer: 22, no 685.
- `SIN_PISTAS` son 24 en la prosa y ninguno tiene marca: son afirmaciones que no
  dicen qué haría falta para cerrarlas. No son ruido, son trabajo sin decidir, y
  por eso son las más baratas de triage y las que ninguna herramienta ordena.

## 4 · Por qué esto importa más de lo que parece

Estuve a punto de cerrar las tres `UN_REGISTRO` fuerte como «cerrables leyendo un
registro», que es NIVEL 2 y por tanto autorizado. Habría leído un registro para
responder una pregunta mal formulada, y habría escrito que ese registro
respondía algo.

El patrón es el de siempre, con un matiz nuevo: **no fue un número inventado por
mí, fue un número producido por una herramienta que yo como fiable y con la
que ya había fallado tres veces**. La defensa no es leer con más cuidado: es
que el instrumento no pueda emitir un titular sin su denominador. Por eso el
titular ahora lleva tres cifras y no una.

## Procedencia

```
tools/frontier.py              titular con denominador, filtros --prosa --fuerte
tools/claims.py                es_fila por linea de origen
frontier.py --prosa --fuerte    22 afirmaciones, 1 mal clasificada de 22
045-...:142                    leido en el fichero: la frase dice RUNTIME
164-...:158                    leido en el fichero: una tabla de "Lo que NO cierra"
frontier.py:390 del propio       el texto ya advertia de que su via mas debil es
                                la que resulta estar mal clasificada
findings/167, 180              el mismo patron: un total sin denominador
```

## CORRECCION POSTERIOR

Ninguna. Y una advertencia sobre las cifras: **el corpus crece mientras se
miden**, porque hay agentes escribiendo en paralelo. Medido en dos momentos
separados de esta misma ronda: 682 → 685 afirmaciones, 390 → 392 filas,
22 → 22 de prosa fuerte. Las proporciones se sostienen; las absolutas no, y por
eso el hallazgo da porcentajes junto a los números y no sólo los números.
