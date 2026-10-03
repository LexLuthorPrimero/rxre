# 237  La densidad de delegación: 26 por mil líneas, y el stream hace una

```
CLASSIFICATION=DOCUMENTATION · TRACK=STATIC
CORPUS=RESEARCH/working/linux-7.1.3 · HARDWARE_SCOPE=HOST-C/RX550/0000:01:00.0
WORK_CLASS=READ_ONLY/EVIDENCE · WRITE_EXECUTION=NONE · MODIFICATIONS=0
RUNTIME=NOT_RUN · GPU INTACTA
```

## Qué resuelve

**La generalización que `175` nombró: repetir el recuento de puntos de delegación en los
cuatro subsistemas. Al hacerlo, `175` queda corregido por un factor de cuatro y medio, y
aparece una medida que ordena los subsistemas de forma distinta que las coberturas de
tabla.**

**⇒ El secuenciador tiene 108 puntos de delegación, no 24.** `PROVEN`.

## 1 · La corrección de `175`, y su causa

| mecanismo | puntos distintos |
|---|---|
| por `dc->hwss.` | **21** |
| por `<obj>->funcs->` | **87** |
| unión | **108** |
| en común entre los dos | **0** |

**⇒ Los dos mecanismos son disjuntos.** `PROVEN`.

**⇒ `175` contó 24 —las 21 de `dc->hwss.` más 2 de los parámetros— y no contó las 87 que
pasan por un puntero dentro de un objeto que llega en los parámetros o en el estado.** `PROVEN_DERIVED`.

**⇒ Y el 24 no era un error de aritmética sino de alcance, el mismo de `165`, `172` y
`174`: medí la parte que estaba mirando y la generalicé.** `PROVEN_DERIVED`.

## 2 · La densidad, que es la medida homogénea

**Puntos de delegación distintos por mil líneas del código compartido del subsistema:**

| subsistema | líneas | puntos | **por mil líneas** |
|---|---|---|---|
| **secuenciador** | 4.131 | 108 | **26,1** |
| reloj | 510 | 5 | 9,8 |
| interrupciones | 674 | 4 | 5,9 |
| codificador de enlace | 2.043 | 2 | 1,0 |
| **codificador de stream** | 1.602 | **1** | **0,6** |

**⇒ El secuenciador es el punto caliente, con una orden de magnitud sobre el codificador
de stream y veintiséis sobre el reloj.** `PROVEN_DERIVED`.

**⇒ Y el codificador de stream hace un solo puntero a función en 1.602 líneas de código
compartido.** `PROVEN`. *Es el subsistema con la tabla más medida del bloque —22 de 38, el
58% de `157`— y es el que casi no delega: sus 22 entradas se rellenan una vez, en el
constructor.*

## 3 · Y las dos medidas ordenan los subsistemas al revés

| subsistema | cobertura de tabla | **densidad** |
|---|---|---|
| codificador de enlace | **72%** (23 de 32) | **1,0** |
| secuenciador | 63% (75 de 119) | **26,1** |
| codificador de stream | 58% (22 de 38) | 0,6 |
| reloj | **8%** (2 de 25) | **9,8** |

**⇒ El subsistema con más tabla cubierta es el segundo menos delegante, y el que menos
tabla tiene cubierta es el tercero más delegante.** `PROVEN_DERIVED`.

| | qué mide | para qué sirve |
|---|---|---|
| **cobertura de tabla** | cuántas operaciones de la interfaz tienen implementación | cuánto driver hay que escribir |
| **densidad de delegación** | cuántas líneas del código compartido salen hacia el chip | dónde está el acoplamiento al hardware |

**⇒ El reloj tiene las dos cosas: 8% cubierto y densidad 9,8, porque tiene pocas
operaciones y todas son el BIOS.** `PROVEN_DERIVED`. *Y el codificador de enlace tiene la
contraria: 32 operaciones, 72% cubierto, y delega en dos sitios.*

**⇒ Y esto matiza «la interfaz es tanto mayor cuanto menos lo sube el hardware», que es
cierto y no basta: una interfaz grande no implica muchos puntos de acoplamiento.** La de
enlace tiene 32 operaciones y delega en dos. `PROVEN_DERIVED`.

## 4 · Y la tensión de 108 contra 75, que tiene explicación

**108 puntos de delegación y 75 funciones en `dce110_hwseq.c`.** Si cada punto fuese una
función, harían falta 108. `PROVEN_DERIVED`.

**⇒ La explicación es la de `172`:** los 87 puntos de la forma `<obj>->funcs->` son
punteros que viven en objetos que llegan **dentro de los parámetros de la operación** —un
`hubp`, un `dpp`, un `mpc`— y **la tabla de funciones de esos objetos la instala el fichero
de recursos, y para los bloques que no existen en DCE no hay tabla que instalar.**
`PROVEN_DERIVED`.

**⇒ Y en particular las entradas de `HUBP` que `175` nombró no tienen implementación en
esta familia, porque `172` encontró que `HUBBUB` y `HUBP` no aparecen en ningún fichero de
DCE.** `PROVEN_DERIVED`.

**⇒ Es decir: de los 108 puntos, las de `HUBP` son inalcanzables en esta GPU, y el resto
se reparte entre los 75 manejadores de `dce110_hwseq.c` y las tablas de los objetos que
traen los parámetros.** `PROVEN_DERIVED`. **Y ésa es la razón de que 75 sea compatible con
108: no todos los puntos de delegación pasan por `dce110_hwseq.c`, y `175` no lo vio porque
sólo contó los que pasan.**

## 5 · Y lo que queda del número de viabilidad

| | `175` dijo | corregido |
|---|---|---|
| puntos de delegación del secuenciador | 24 | **108** |
| manejadores de esta GPU en esa ruta | 75 | 75 |
| **funciones que hay que reescribir** | 75 | **75** |

**⇒ El número de funciones que hay que escribir no cambia: sigue siendo 75, que es una
cifra medida contando funciones de un fichero.** `PROVEN`.

**⇒ Lo que estaba mal era el numerador del cociente, y la corrección lo hace el intervalo
más honesto, no más preciso: entre 75 y 108, con un caso por debajo del otro, que es la
señal de que la cuenta por dos mecanismos no es la cuenta buena.** `PROVEN_DERIVED`.

## Lo que NO cierra

| afirmación | estado |
|---|---|
| 108 puntos de delegación, no 24 | `PROVEN` — corrección de `175` |
| Los dos mecanismos son disjuntos, 0 en común | `PROVEN` |
| Densidades: 26,1 / 9,8 / 5,9 / 1,0 / 0,6 | `PROVEN` |
| El stream hace 1 puntero en 1.602 líneas | `PROVEN` |
| Cobertura y densidad ordenan al revés | `PROVEN_DERIVED` |
| Las entradas de `HUBP` son inalcanzables en esta GPU | `PROVEN_DERIVED` |
| 75 funciones que reescribir en la ruta de secuenciador | `PROVEN` |
| Cuántos de los 108 ejecuta un modo concreto | **`NOT_DETERMINED`** — nivel 4 |
| Densidad de `amdgpu_dm/`, 32.304 líneas de pegamento con DRM | **`NOT_DETERMINED`** |
| Densidad de `dc_surface`, `dc_state`, `dc_stream` | **`NOT_DETERMINED`** |
| Si los 5 del reloj y los 4 de las IRQ salieron del mismo criterio | **`NOT_DETERMINED`** |

**La segunda de las abiertas es la que hace el método general y no un dato de dos muestras:
`amdgpu_dm/` son 32.304 líneas y no se le ha hecho este recuento, y es el único directorio
grande de `display/` que queda sin él.** Es la misma operación, el mismo criterio y el
mismo programa, y se puede hacer hoy.

**La cuarta es una salvedad que escribo para no pasar por más precisa de lo que es: los 5
del reloj y los 4 de las interrupciones salieron de un recuento de nombres distintos por
fichero, y no de la doble clasificación de §1.** El número grande —108— sí está desglosado
por mecanismo y es auditable; los cinco pequeños no, y la diferencia de criterio podría
moverlos.

## Procedencia

- `STATIC` -- `display/dc/core/dc_hw_sequencer.c` (4.131 líneas por `wc -l`, y los dos
  conjuntos de nombres: `->\s*hwss\s*\.\s*(\w+)\s*\(` y
  `(\w+)\s*->\s*funcs\s*->\s*(\w+)\s*\(`, ambos en modo `re.S` para tolerar llamadas
  partidas en varias líneas); `display/dc/dce/dce_stream_encoder.c` (1.602 líneas),
  `display/dc/dce/dce_link_encoder.c` y `display/dc/dce/dce_link_encoder_dc.c` (2.043
  líneas sumadas), `display/dc/clk_mgr/dce100/dce_clk_mgr.c` (510),
  `display/dc/irq/irq_service.c` y `display/dc/irq/dce110/irq_service_dce110.c` (674
  sumadas); `display/dc/hwss/dce110/dce110_hwseq.c` (las 75 funciones, de `175`);
  `display/dc/inc/hw/stream_encoder.h:133`, `display/dc/inc/hw/link_encoder.h:113` y
  `display/dc/inc/hw/clk_mgr.h:299` (las tres tablas, de `157`, `167` y `161`).
- Medición por programa: **los dos conjuntos de nombres y su intersección, que da 21, 87,
  108 y 0**; **las cinco densidades, cada una con su numerador, su denominador y su
  cociente**; la tabla de las dos medidas ordenadas de forma distinta.
- **Dos errores propios, y el primero es el que hace la nota útil:**
  (1) **Imprimí una columna de porcentajes que no significa nada:** dividí un número de
  llamadas por un número de líneas, y salió «261,4%» para el secuenciador — más de dos
 cientos sesenta por ciento de las líneas son delegaciones. **Un porcentaje sobre cien que
  da 261 no es un dato raro: es un dato imposible, y lo imposible es la señal.** Lo
  correcto era un cociente por mil líneas, que no tiene techo natural, y ése es el que
  acabó midiéndose, dos llamadas después.
  (2) El primer recuento de `->hwss.` dio 21 en lugar de las 22 de `175`, porque el patrón
  no captura una llamada cuya apertura está en la línea siguiente. **Y la corrección de
  `175` depende de no arrastrar ese menos uno: dos recuentos con dos patrones distintos no
  se pueden comparar.**
- **Y una corrección de alcance en `175`:** presentó los 24 como «el número de puntos de
  entrada que hay que reescribir», y no es ése. **El número de funciones que hay que
  escribir es 75, que es una cuenta de funciones de un fichero, y no depende de cómo se
  cuenten los puntos de delegación.** La distinción que faltaba en `175` es entre *puntos
  de salida al chip* y *funciones que hay que escribir*, y no son el mismo número.
- Encadenada con `175` (los 24 puntos, corregidos aquí a 108, y la distinción que faltaba
  entre puntos y funciones), `174` (las tres formas de despacho y el 87%), `173` (el
  intérprete de 119 operaciones), `172` (los bloques ausentes de DCE, que son la
  explicación de §4), `167` (el 72% del codificador de enlace), `162` (`MAX_PIPES 6` y los
  bombs), `161` (el 8% del reloj), `159` (los 52 constructores), `157` (el 58% del
  codificador de stream), `156` (la regla de la tabla y el constructor), `155`, `154`,
  `153`, `150`, `145`, `140`.
- No se editó `AGENTS.md` ni `OPEN-FRONTIERS.md`.

## Nota de método

**El error de esta nota es un porcentaje de 261, y es la primera vez en veintiséis notas que
el delator no es sólo la rareza ni sólo la imposibilidad, sino las dos, y que aun así el
dato llegó a imprimirse.**

*Dividí un número de llamadas por un número de líneas.* **El resultado fue «261,4%»,
imposible como porcentaje de ocupación, y lo imposible es la señal que la nota anterior usó
con éxito y que aquí no usé: leí la línea siguiente.** **El número correcto —26,1 por
mil— salió de los mismos datos con otro denominador, y significa algo porque no tiene
techo.**

**Y la observación de fondo es la más útil del bloque: los dos datos de esta nota
—cobertura de tabla y densidad de delegación— contestan preguntas distintas, y el bloque
llevaba veintiséis notas usando sólo la primera.**

*La cobertura mide cuántas operaciones de la interfaz están implementadas, y responde
«cuánto driver hay que escribir». La densidad mide cuántas líneas del código compartido
salen hacia el hardware, y responde «dónde está el acoplamiento».* **Y dan ordenaciones
opuestas: el codificador de enlace es primero en cobertura y penúltimo en densidad, y el
reloj es último en cobertura y tercero en densidad.** **Con una sola de las dos, el mapa
del driver que el bloque llevaba veintiséis notas construyendo era sistemáticamente
incorrecto en un lado: parecía que el acoplamiento al hardware estaba donde la interfaz es
más grande, y está donde el código compartido hace más saltos.**

*Y la lección del método es la de siempre con un caso nuevo:* **medir la parte que se está
mirando y generalizarla es el error dominante de esta tanda, y no lo detecta ni un
resultado raro ni uno imposible cuando la parte medida es plausible.** *`175` contó 24
puntos de delegación: un número pequeño, verosímil, con la forma de una cifra de
ingeniería. El número grande, 108, no se parecía a nada que yo esperara de un fichero de
4.131 líneas, y por eso no lo busqué.*
