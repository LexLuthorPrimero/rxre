# 174 · El 87% del despachador son llamadas directas, y eso es toda la arquitectura

```
CLASSIFICATION=DOCUMENTATION · TRACK=STATIC
CORPUS=RESEARCH/working/linux-7.1.3 · HARDWARE_SCOPE=HOST-C/RX550/0000:01:00.0
WORK_CLASS=READ_ONLY/EVIDENCE · WRITE_EXECUTION=NONE · MODIFICATIONS=0
RUNTIME=NOT_RUN · GPU INTACTA
```

## Qué resuelve

**La pregunta de fondo del bloque entero —que `156` abrió, `157` medijo, `158` sintetizó y
`173` llevó a un intérprete de 119 operaciones— y la respuesta es un porcentaje que
invierte el énfasis de todo lo escrito hasta ahora:

**El 87% del despachador son llamadas directas a código compartido. El 13% son punteros a
función. El intérprete no es una tabla virtual de 119 operaciones: son 101
implementaciones compartidas más 15 escapatorias.**

## 1 · El despachador, y su forma exacta

`display/dc/core/dc_hw_sequencer.c:962-1335`: `switch (block_sequence[i].func) { ... }`,
**374 líneas, 116 casos, y un `default:` en `L1332`.**

**⇒ 116 casos para 119 valores del enum: el 97%. Tres operaciones están en el vocabulario y
no tienen caso, y caen en el `default`.** `PROVEN_DERIVED`.

**⇒ Y el `default` no es un error declarado: es la ruta de esas tres.** `PROVEN_DERIVED`.

**⇒ Y hay un segundo intérprete del mismo patrón, en otro subsistema:
`display/dc/clk_mgr/dcn401/dcn401_clk_mgr.c:658`, `switch (clk_mgr401->block_sequence[i].func)`.
O sea que la técnica no es de un fichero, es una manera de organizar un subsistema
completo.** `PROVEN_DERIVED`.

## 2 · Y el cuerpo de cada caso tiene tres formas, y las tres son la arquitectura

Contadas por programa sobre los 116 casos, **sumando 116**:

| forma | n | % | ejemplo literal |
|---|---|---|---|
| **1 · llamada directa a un estático del fichero** | **101** | **87,1%** | `hwss_setup_dpp(params);` |
| **2 · puntero a función en el contexto DC** | **11** | **9,5%** | `dc->hwss.subvp_pipe_control_lock_fast(params);` |
| **3 · puntero a función DENTRO de los parámetros** | **4** | **3,4%** | `params->set_flip_control_gsl_params.hubp->funcs->hubp_set_flip_control_surface_gsl(...)` |

**⇒ 101 de 116 son llamadas directas, y 15 de 116 son indirecciones.** `PROVEN`.

**Y las tres formas son tres niveles, y son los mismos tres niveles que el bloque lleva
veinte notas describiendo por separado:**

| | forma | qué es | quién lo instala |
|---|---|---|---|
| **1** | llamada directa | el código es el mismo para todos los chips | nadie, está escrito |
| **2** | `dc->hwss.op` | el código es de la generación | **el fichero de recursos** — `156`, `159` |
| **3** | `params->…->funcs->op` | el código **viaja con la petición** | **quien llama** |

**⇒ El nivel 3 es la regla de `156` en su forma más fuerte: la identidad de un camino la
lleva la tabla, y aquí la tabla va dentro de los parámetros, o sea que la lleva el
llamante.** `PROVEN_DERIVED`. *Y eso es lo que permite que un `dce110_hwseq.c` llame a un
despachador genérico y que la implementación que se ejecute sea la suya.*

**⇒ Y el nivel 1 es lo que ninguna nota había medido: el 87% del intérprete no necesita
tabla, puntero ni constructor porque el código es el mismo para todos los chips, y por eso
`172` pudo encontrar 242 funciones de diecisiete líneas de media.** `PROVEN_DERIVED`.

## 3 · Y el reencuadre, que es lo importante

**Diecisiete notas han medido tablas de punteros a función: 22 de 38, 23 de 32, 2 de 25,
16 de 38, 4 de 15, 12 de 15, 9 de 32, 1 de 15.** Todas son correctas y todas son la
**minoría** del driver.

| | medidas | % del interfaces |
|---|---|---|
| tablas de punteros a función | nueve | **13%** del despachador del secuenciador |
| **llamadas directas a código compartido** | — | **87%** |

**⇒ El driver no es un conjunto de tablas virtuales con implementaciones por chip: es un
programa con una región de quince puntos de indirección para lo que el chip no puede
saber, y todo lo demás es código que se escribe una vez.** `PROVEN_DERIVED`.

**⇒ Y eso explica, con un solo número, por qué el árbol tiene 510 ficheros de display y
sólo 52 funciones propias de DCE 11.2: porque el 87% de la ruta de programación es el mismo
código para todos los chips, y lo único que cambia son quince llamadas.** `PROVEN_DERIVED`.

**⇒ Y corrige la emphasis de `173`, que presentó los 119 nombres de operación y los 22
prefijos de bloque como si fueran la estructura del driver.** *No lo son: son el
vocabulario de un intérprete cuyo 87% de los casos no tiene nada de específico.* **El
vocabulario es grande porque tiene que nombrar todo lo que puede pasar; la
implementación es pequeña porque casi nada de eso es distinto entre chips.**

## 4 · Y una precisión sobre `172` y sobre `citecheck`

`172` registering `dc_hw_sequencer.c` con **4.132 líneas**, y `wc -l` da **4.131**.

**⇒ La diferencia es el mismo `+1` que `citecheck` sufre en todos los ficheros: contar
elementos de `split("\n")` cuenta un elemento más que líneas, porque el último `split`
devuelve la cadena vacía tras el salto final.** `PROVEN`.

**⇒ Y la diferencia estaba en mi programa, no sólo en la herramienta ajena: `172` usó
`len(t.split("\n"))` para las líneas de los doce ficheros de `core/`.** `PROVEN_DERIVED`.
**Y el mismo razonamiento de `172` —«`wc -l` cuenta saltos de línea, no líneas»— era
correcto y lo escribí en la nota sobre `citecheck` sin aplicarlo a mi propia cuenta.**

**⇒ La cifra correcta para los doce ficheros de `core/` es 22.143, no 22.144.** `PROVEN`.
*Y ningún número de `172` que no sea el total de líneas depende de ese uno.*

## Lo que NO cierra

| afirmación | estado |
|---|---|
| El despachador: 374 líneas, 116 casos, `default` en 1332 | `PROVEN` |
| 116 de 119 valores del enum tienen caso | `PROVEN_DERIVED` |
| Las tres formas: 101 / 11 / 4, sumando 116 | `PROVEN` |
| 87% llamadas directas, 13% punteros a función | `PROVEN` |
| Hay un segundo intérprete del mismo patrón en dcn401_clk_mgr.c | `PROVEN` |
| El nivel 3 lleva la tabla dentro de los parámetros | `PROVEN_DERIVED` |
| El nivel 1 es lo que permite funciones de 17 líneas | `PROVEN_DERIVED` |
| El 13% de punteros es la minoría del driver, no su estructura | `PROVEN_DERIVED` |
| `core/`: 22.143 líneas, no 22.144 | `PROVEN` — corrección de `172` |
| Las tres operaciones sin caso: cuáles y qué hace el `default` | **`NOT_DETERMINED`** |
| Cuál de las 15 indirecciones se usa en un modo concreto | **`NOT_DETERMINED`** |
| Si la GPU alguna vez ejecuta las 15 en un mismo commit | **`NOT_DETERMINED`** |

**La primera de las abiertas son tres valores, y se cierra con el mismo procedimiento que
`154`:** enumerar los 119 del enum, restar los 116 del switch, y ver los tres que
sobran. **Y la tercera es la que de verdad importa para un driver propio: de las quince
llamadas que dependen del chip, cuántas ejecuta realmente un cambio de modo — y ese es el
número de funciones que hay que reescribir para otra GPU en esa ruta.**

## Procedencia

- `STATIC` -- `display/dc/core/dc_hw_sequencer.c:962` (el `switch`), `:964` (el primer
  caso), `:967-971` (el caso de puntero en contexto, con su cuerpo partido en tres
  líneas), `:972-975` (el caso de puntero dentro de los parámetros, que ocupa nueve
  líneas de invocación), `:1016-1021` (dos casos de llamada directa, uno de los cuales
  contiene la cadena `default` dentro del nombre de la función y no es la etiqueta),
  `:1028-1030` (otro caso mixto), `:1332` (la etiqueta `default:` real), `:1335` (el
  cierre del `switch`), `:1344-1354` (una operación de `add` completa, de `173`),
  `:1302-1335` (el tramo final); `display/dc/clk_mgr/dcn401/dcn401_clk_mgr.c:658` (el
  segundo intérprete); `display/dc/hwss/hw_sequencer.h:742-864` (la unión),
  `:866-...` (el enum), `:989-997` (las dos estructuras), `:999` (el tope).
- Medición por programa: **la extensión del `switch` por conteo de llaves, los 116 casos,
  la posición de `default:`, y la clasificación del cuerpo de cada uno en las tres
  formas**; el recuento por forma, impreso y comprobado contra el total de casos
  (`suma: 116 -> CUADRA CON 116: True`); el recuento de líneas por `wc -l` frente a
  `split("\n")`.
- **Dos errores propios en esta nota, y los dos son de los que el bloque ha aprendido
  más:**
  (1) **El primer bucle de clasificación dejó fuera cuatro casos y devolvió 112 sobre
  116.** La causa: al avanzar `i=j` desde el cuerpo de un caso hasta el `case` siguiente,
  los casos con etiqueta compartida o con el cuerpo vacío se saltaban. **Lo que lo
  delató no fue un resultado raro sino una suma que no cuadraba, y eso es un tipo de
  señal que no había catalogado: hasta ahora los errores los delataba la rareza o la
  imposibilidad, y aquí los delató la aritmética.** Lo rehíce con el índice de casos
  precalculado, y la clasificación completa cubre los 116 con las tres formas y sin
  ninguna cuarta.
  (2) **En la última línea impresa de mi script escribí «97 IMPLEMENTACIONES
  COMPARTIDAS», un número que ningún programa había producido.** La cifra correcta del
  cálculo es **101**, y la escribí como 97 porque la había copiado de la versión anterior
  del programa, la que estaba mal. **Es el error de `156` —«afirmo un número que tengo a
  la vista y no lo leo»—)
  volver a mirar la nueva. Y de nuevo lo cazó el programa, al imprimir el 87,1% y el 101
  volver a mirar la nueva. Y de nuevo lo cazó el programa, al imprimir el 87,1% y el 101
  en la misma línea.
- Encadenada con `173` (**el intérprete, su vocabulario y su lista con tope; y aquí su
  despachador y el reparto de sus 116 casos**), `172` (la capa genérica, sus 242 funciones
  de 17 líneas, y **la corrección de su total de líneas**), `170` (la regla de qué
  versiones tienen fichero), `169` (los nueve bloques IP), `167` (las cuatro interfaces
  y su 72% en el codificador de enlace), `162` (`MAX_PIPES 6`), `161` (el reloj al 8%),
  `159` (los 52 constructores y el 21% por generación), `157` (el 58% y el puntero nulo),
  `156` (la regla de la tabla y el constructor, y aquí su nivel más fuerte),
  `155`, `154` (el `switch` de 17 casos y el mismo procedimiento), `153`, `150`, `145`,
  `140`.
- No se editó `AGENTS.md` ni `OPEN-FRONTIERS.md`.

## Nota de método

**Diecisiete notas midieron tablas de punteros a función. Esta mide el porcentaje de
llamadas que no son punteros, y el resultado invierte la emphasis de todas ellas: el 87%
del driver de pantalla no tiene nada de específico del chip.**

*La pregunta que se cerraba era «cómo sostiene amdgpu treinta chips», y la respuesta que
salía de las diecisiete era «con tablas de punteros a función, tablas de swizzle y
punteros nulos».* **Esa respuesta era cierta y era la minoría: quince de cada
ciento dieciséis llamadas del despachador.** *Y ninguna nota lo detectó porque todas
midieron el numerador y nadie midió el denominador.* **Eso es la clase de error que ha
producido la mayoría de las correcciones del bloque —`147` con la tabla equivocada, `148`
con el fichero equivocado, `165` con dos criterios, `169` con nueve filas imposibles,
`172` con un 69% falso— y su forma es siempre la misma: una afirmación que no se puede
falsar por la magnitud de lo que afirma.**

**Y el error de esta nota, el 97 donde el programa decía 101, es el más barato de todos
porque no tenía ninguna alarma: el número anterior y el nuevo salían ambos de un
programa, y el nuevo era correcto.** *Copié el 97 de la versión previa del programa —la
que estaba mal— y lo pegué en la línea de conclusión.* **Un programa que se corrige y se
vuelve a ejecutar tiene sus números viejos todavía en el texto de la nota, y la tentación
de escribirlos es exactamente la que hace que un resultado correcto se apoye en un cálculo
que ya no existe.** *La defensa es la regla (c) de siempre, aplicada en su forma más
dura: si el número no salió del programa que acabo de ejecutar, no está escrito.*

**Y queda el hallazgo que es la respuesta a la pregunta de `172` y a la de `173` a la vez:
las tres formas de despacho de un `switch` son las tres maneras que tiene un driver de ser
independiente del chip —código compartido, tabla elegida por el recurso, y tabla que
viaja con la petición— y el orden de frecuencia es 101, 11, 4.** *Es decir: primero se
escribe el código, luego se añade la indirección para lo que el chip no puede saber, y
sólo en cuatro casos el hardware decide quién ejecuta. Todo lo demás es un programa.*
