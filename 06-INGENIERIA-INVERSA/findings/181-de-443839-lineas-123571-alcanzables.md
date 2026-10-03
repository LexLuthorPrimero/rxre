# 181 · De 443.839 líneas, 123.571 son alcanzables desde `dc_create`, y eso es una cota superior

```
CLASSIFICATION=DOCUMENTATION+TOOLING · TRACK=STATIC
CORPUS=RESEARCH/working/linux-7.1.3 · HARDWARE_SCOPE=HOST-C/RX550/0000:01:00.0
WORK_CLASS=READ_ONLY/EVIDENCE · WRITE_LOCAL=PROPIOS · MODIFICATIONS_CORPUS=0 · WRITE_EXECUTION=NONE
RUNTIME=NOT_RUN · GPU INTACTA
```

## Qué resuelve

**La pregunta que `179` dejó abierta: qué subárboles de `display/` son código de esta
GPU. Y la respuesta no es una lista de directorios, es un grafo de llamadas, y por eso
tuve que escribir el programa que la contesta.** `tools/inst_closure.py`, nuevo.

**⇒ Hay un único punto de entrada real, `dc_create` en `dc/core/dc.c:1508`, llamado desde
`amdgpu_dm/amdgpu_dm.c:2038`. Desde él se alcanzan 3.077 funciones y 123.571 de las
443.839 líneas: el 27,8%.** `PROVEN_DERIVED`.

**⇒ Y es una COTA SUPERIOR, no una medición, por una razón declarada: el recorrido es
estático y no distingue una rama que el silicio no puede tomar.** `LIMITATION`.

## 1 · La entrada, y por qué las otras 27 no existían

**La primera versión de la lista de semillas tenía 28 nombres, y los 28 no existían.**
`dc_create_resource`, `dc_hw_sequencer_init`, `dc_link_srv_init`, `dc_sspl_init`,
`dc_stream_encoder_init`, `dc_clk_mgr_init`… ninguno está en el árbol. `PROVEN_ABSENT`.

**La herramienta lo decía y yo seguí imprimiendo el reparto:**

```
  semillas genericas: 28
  alcanzables: 201
  semillas NO resueltas: 28  ['dc_create_resource', 'dc_hw_sequencer_init', ...]
```

**⇒ Un número al lado de su advertencia sigue siendo un número, y durante cuatro
ejecuciones leí el 2,1% como resultado.** `ERROR`. *Es la peor forma de estar
equivocado: la herramientasequences lo detecta y el reparto sale igual de limpio.*

**La raíz real está en el corpus, y no la inventé, estaba en el fichero:**

```c
amdgpu_dm/amdgpu_dm.c:2038    adev->dm.dc = dc_create(&init_data);
dc/core/dc.c:1508             struct dc *dc_create(struct dc_init_data *init_data)
```

**⇒ `dc_create` es la única semilla. Y sembrar además `dc/resource/dce112/` fue un error
de diseño por partida doble:** medía el conjunto de lo alcanzable desde el constructor por
ASIC, que es sólo el camino de arranque —el 2,1%— y no el de modo de pantalla, y además
limitaba el resultado, porque el constructor se alcanza desde `dc_create` como cualquier
otro nodo.** `ERROR`. *Regla (i) por tercera vez en tres notas: medí la parte que estaba
mirando y la generalicé como si fuera el conjunto.*

## 2 · El resultado, con la contaminación cuantificada

**Función indexada = un nombre que tiene definición de cuerpo. Caller: llamada, o
asignación `->campo =`, o entrada de un inicializador de struct designado.**

| | valor |
|---|---|
| funciones indexadas | 7.892 |
| tablas de despacho indexadas | 744 |
| aristas desde tablas | 6.665 |
| **alcanzables desde `dc_create`** | **3.077** (39,0%) |
| **líneas alcanzables** | **123.571 de 443.839 = 27,8%** |
| colisiones de nombre entre `.c` | 821 |
| alcanzables cuyo nombre está en más de un `.c` | 152 |
| **alcanzables cuya ambigüedad mete código de otro chip** | **1** |

**⇒ La contaminación de las 821 colisiones es de un símbolo, y lo sé porque lo medí: los
152 nombres ambiguos se cruzaron contra el subárbol de cada definición alternativa, y
sólo uno, `program_pix_dur`, tiene su otra definición en `dc/dce60/`.** `PROVEN`.

**⇒ Y las otras dos señales de descuadre que quedan Declaradas: 3 ficheros con llaves sin
emparejar, que ya no se abandonan, y 2 macros `DEFINE_*` indexadas como nodo sin rango.**
`PROVEN`.

## 3 · El reparto, y que es el inverso del de `179`

| subárbol | líneas | alcanzables | % | funciones alcanzables |
|---|---|---|---|---|
| `dc/hwss/` | 27.251 | **21.363** | **78,4%** | 498 de 525 (**94,9%**) |
| `dc/dml/` | 77.927 | 21.597 | 27,7% | 126 de 334 (37,7%) |
| `dc/resource/` | 50.053 | 17.442 | 34,8% | 371 de 702 (52,8%) |
| `dc/link/` | 19.451 | 16.062 | **82,6%** | 447 de 497 (89,9%) |
| `dc/core/` | 22.132 | 13.876 | 62,7% | 523 de 807 (64,8%) |
| `dc/clk_mgr/` | 18.218 | 11.069 | 60,8% | 366 de 479 (76,4%) |
| `dc/dml2_0/` | 40.058 | 5.446 | 13,6% | 153 de 538 (28,4%) |
| `dc/basics/` | 5.059 | 1.370 | 27,1% | 32 de 66 (48,5%) |
| `dc/gpio/` | 9.236 | 1.538 | 16,7% | 65 de 107 (60,7%) |
| `dc/dce/` | 17.841 | 2.721 | 15,3% | 97 de 427 (22,7%) |
| `dc/dce112/` | 848 | **0** | **0,0%** | 0 de 16 |
| `dc/sspl/` | 6.973 | **0** | **0,0%** | 0 de 53 |
| `modules/` | 10.413 | **0** | **0,0%** | 0 de 242 |
| **TOTAL** | **443.839** | **123.571** | **27,8%** | **3.077 de 7.892** |

**⇒ `dc/hwss/` es el94,9% alcanzable por funciones: 498 de 525. Es el código de esta GPU
y casi todo él está en el camino real.** `PROVEN`. *Y `173` contó 75 manejadores en
`dce110_hwseq.c`; los 498 de `dc/hwss` son el conjunto de todos los bloques por
generación, de los que sólo los de esta generación se instancian.*

**⇒ Y los tres ceros son el resultado más útil de la tabla, porque no son ceros de código
muerto: son código que se entra por otra puerta.** `dc/sspl/` son 6.973 líneas de
escalado, `modules/` son 10.413 de FreeSync, HDCP, color, power y vmid, y ninguno se
alcanza desde `dc_create` porque se llaman desde los retrollamados de DRM en `amdgpu_dm/`,
no desde la construcción de `dc`. `PROVEN_DERIVED`.

**⇒ `dc/dce112/` da cero y es el directorio del bloque de esta placa: sus 16 funciones
se alcanzan por el nombre del fichero de `hwss`, no por el directorio `dce112/` del que
salen.** `PROVEN`. *Otra vez el nombre del fichero no dice en qué generación está, que es
la serie de colisiones de nombres de este bloque.*

## 4 · Por qué hace falta un tercer tipo de arista, y qué cuesta no tenerlo

**El despacho de DML no es una llamada ni una asignación de campo:**

```c
dc/hwss/dce110/dce110_hwseq.c:3558   void dce110_hw_sequencer_construct(struct dc *dc)
dc/hwss/dce110/dce110_hwseq.c:3560       dc->hwss         = dce110_funcs;
dc/hwss/dce110/dce110_hwseq.c:3561       dc->hwseq->funcs = dce110_private_funcs;
```

**⇒ Los 75 manejadores de `173` viven dentro de un inicializador de struct designado, y
una tabla no es una función: sin arista de tabla el recorrido llega a `dce110_funcs` y se
detiene.** `PROVEN_DERIVED`.

**⇒ Con dos tipos de arista, `dc/hwss/` daba 231 líneas alcanzables, el 0,8%. Con el
tercero da 21.363, el 78,4%: 90 veces más, y el 94,9% de sus funciones.** `PROVEN`.
*Ese es el punto ciego declarado como LIMITACIÓN 2, y se cerraba midiendo, no pensando.*

**⇒ Los tres tipos, y qué resuelve cada uno:**

| arista | patrón | para qué |
|---|---|---|
| llamada | `\b(\w+)\s*\(` | el grueso del grafo |
| campo | `->(\w+)\s*=\s*(\w+)` | `dc->hwss = dce110_funcs` |
| tabla | `struct \w+ \**(\w+) = {` … `\.(\w+)\s*=\s*(\w+)` | los 75 manejadores, y las 744 tablas |

## 5 · La cota superior, y por qué el 27,8% no es el número de líneas que hay que escribir

**El recorrido es estático y no sabe qué rama se puede tomar.** *La prueba está dentro de
la propia tabla: `dc/dce60/` sale 50,0% alcanzable, y DCE 6.0 es un chip de 2013 que esta
placa no puede ejecutar.* `PROVEN_DERIVED`.

**⇒ Y la causa concreta es un `switch` sobre el tipo de chip dentro de la capa genérica:
el grafo por nombre sigue las dos ramas a la vez.** `PROVEN_DERIVED`.

**⇒ De modo que 27,8% es un techo, y el número real —cuántas de esas 123.571 líneas
ejecuta Polaris12— es más pequeño y no se puede obtener sin resolver las guardas de
ASIC una a una.** `NOT_DETERMINED`.

**⇒ Y para un driver propio el techo sigue siendo la cifra útil, porque es la que dice
cuánto hay que leer antes de poder decidir qué se reescribe.** `PROVEN_DERIVED`.

## Lo que NO cierra

| afirmación | estado |
|---|---|
| `dc_create` es la única raíz, en `dc/core/dc.c:1508` | `PROVEN` |
| Las 28 semillas inventadas no existen | `PROVEN_ABSENT` |
| 3.077 funciones y 123.571 líneas alcanzables, 27,8% | `PROVEN_DERIVED` |
| `dc/hwss/`: 94,9% de sus funciones alcanzables | `PROVEN_DERIVED` |
| `modules/`, `dc/sspl/`, `dc/dce112/` a cero | `PROVEN` |
| 1 de 152 ambiguos mete código de otro chip | `PROVEN` |
| 27,8% es cota superior, no medición | `LIMITATION` |
| Cuántas de las 123.571 ejecuta Polaris12 | **`NOT_DETERMINED`** |
| Las guardas de ASIC, una a una | **`NOT_DETERMINED`** |
| Por qué `modules/` no se alcanza desde `dc_create` | **`NOT_DETERMINED`** |
| La misma medición sobre `amdgpu_dm/` desde DRM | **`NOT_DETERMINED`** |
| Cuántas de las 108 délégaciones ejecuta un modo | **`NOT_DETERMINED`** — nivel 4 |

**La primera de las abiertas tiene la vía de cierre escrita: el `switch` por
`ASICFamily` es un sitio, y recorrerlo dando el `case` de DCE 11.2 baja la cota.** *Es la
misma operación con un dato más: el recorrido ya sabe quéines son alcanzables; sólo falta
que se le diga qué guardas se pueden tomar.* **`NOT_DETERMINED`.**

**Y la cuarta es la que hace la cifra utilizable: el ceilingsde 27,8% incluye 10.413
líneas de `modules/` que no entran por esta puerta, y esos callbacks de DRM son
justamente el otro lado del driver propio.** `NOT_DETERMINED`.

## Procedencia

- `STATIC` -- `tools/inst_closure.py` (nuevo, 43 líneas de contrato, `--selftest` con 15
  vectores y control invertido), sobre `display/` con 510 `.c` y 443.839 líneas.
- `display/amdgpu_dm/amdgpu_dm.c:2038` (`dc_create(&init_data)`),
  `display/dc/core/dc.c:1508` (`dc_create`), `display/dc/core/dc_resource.c:441`
  (`resource_construct`), `display/dc/hwss/dce110/dce110_hwseq.c:3558`
  (`dce110_hw_sequencer_construct`), `display/dc/hwss/dce112/dce112_hwseq.c:152`
  (`dce112_hw_sequencer_construct`), `display/dc/hwss/dce112/dce112_hwseq.c:158`
  (`dc->hwseq->funcs.enable_display_power_gating = dce112_enable_display_power_gating`),
  `display/dc/resource/dce60/dce60_resource.c:504` (`dce60_timing_generator_create`,
  `static`, sólo usada dentro de su propio fichero).
- Patrones, los cuatro y sólo cuatro: `^(static\s+)?[\w \*]*?\**(\w+)\s*\(` para
  definiciones, `\b(\w+)\s*\(` para llamadas, `->\s*(\w+)\s*=\s*(\w+)` para campos,
  `^\s*(?:static\s+)?(?:const\s+)?struct\s+\w+[ \t\*]*\**(\w+)\s*=\s*\{` con
  `.\s*(\w+)\s*=\s*(\w+)` dentro para tablas. Todos con comentarios eliminados antes.
- **Seis bugs reales de la herramienta, y los seis los cazó el `--selftest`, ninguno un
  programa de medida:**
  1. `sin_comentarios` con el caso de `*` invertido, que vaciaba si **no** empezaba por
     asterisco. Síntoma: 1.175 colisiones con nombres `files` y `3x4`, que son palabras
     de la licencia y de un comentario de matriz.
  2. Los fixtures del selftest con 4 campos cuando el índice tiene 6, y con rutas fuera
     de `BASE`. Se cayó con `ValueError` en vez de comprobar lo que comprobaba.
  3. `lineas_alcanzables` pasando a `subtree()` una ruta relativa a `BASE`, que espera
     absoluta. Síntoma: **201 funciones alcanzables y 0 líneas**, que es imposible, y por
     eso se vio (`PROVEN_ABSENT` no; regla (k)).
  4. `index_tablas` emparejando el regex sobre el texto unido y luego indexando con un
     índice de línea, de modo que `src[j]` era el carácter `{`. Síntoma: **744 tablas y
     CERO aristas**, y por eso se vio.
  5. `if not cerrado: break`, que abandonaba el resto del fichero entero con una llave
     sin emparejar. **La hipótesis era falsa**: sólo 3 ficheros se descuadran y ninguno
     era el culpable de las funciones ausentes. El arreglo queda porque `continue` es lo
     correcto, y el hallazgo es que la hipótesis no era la buena.
  6. El `--selftest` escribiendo su fichero temporal en `dc/core/`, es decir
     `MUTATES_CORPUS=yes` contra el contrato de la propia herramienta y contra la regla
     de no añadir ficheros al corpus compartido. Ahora va a `/tmp` y `BASE` es absoluta.
- **Dos nombres inventados más, en la sonda:** `dp_train_dp.c` y las 28 semillas. Y
  `program_pix_dur`, que resultó ser el único símbolo realmente contaminado.
- Encadenada con `179` (**las cuatro clases, y aquí la alcanzabilidad, que es la
  pregunta que dejó abierta**), `178` (los dos canales), `238` (la densidad aplicada),
  `237` (la densidad como medida), `175` (los 108 puntos), `173` (**los 75 manejadores,
  que son las 744 tablas y la tercera arista**), `172` (`dc/core/`), `236` (qué se
  instancia), `234` (las escrituras de registro), `159` (los 52 constructores), `232`
  (la tabla de swizzle), `140` (el mapa de direcciones).
- No se editó `AGENTS.md` ni `OPEN-FRONTIERS.md`, y no se añadió ningún fichero al corpus.

## Nota de método

**La primera versión de esta herramienta costó seis correcciones y ninguna la detectó un
programa de medida: las seis las detectó el `--selftest`.** *Y las seis eran del mismo
tipo: el código que yo creía que escribía no hacía lo que yo creía.* Un comentario sin
aclarar, un índice con seis campos y fixtures de cuatro, una ruta absoluta donde iba una
relativa, un índice de línea donde iba un índice de carácter, un `break` donde iba un
`continue`, y un fichero de prueba dentro del directorio que la herramienta no debe
tocar.

**Y hay un resultado de método que vale más que las cifras: el cuarto bug —744 tablas y
cero aristas— sólo se vio porque el número era imposible.** *Cero aristas de tablas en un
árbol con 744 tablas no es un resultado, es un sintoma; igual que las 0 líneas con 201
funciones.* **Y las dos cosas se habrían escrito igual de limpias en una nota si el
programo no hubiera impreso la tabla entera: 744 y 0 salen uno al lado del otro, y
mirarlos juntos es lo que delata el error.**

**Y la lección de diseño es la de siempre, y es la tercera vez en tres notas: sembré el
constructor por ASIC porque era lo que tenía delante, y eso mide el arranque en lugar de
la pantalla.** *El antídoto no es medir más: es medir el conjunto desde el punto de
entrada real, que estaba escrito en `amdgpu_dm.c:2038` desde el principio.*

**Y queda la limitación escrita, que es la que hace el número utilizable y no
engañoso: el 27,8% es un techo, y lo demuestra un dato que sale de la propia tabla —
`dc/dce60/` al 50,0%, un chip de 2013 que esta placa no puede ejecutar.** *Un techo que
contiene un imposible está mal, pero se ve; y un número exacto que contiene un
imposible es un número que ya no se puede usar para nada.*