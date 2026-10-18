# GRAFO-CLAVE-NO-UNICA — todos los grafos del proyecto están indexados por un número que no es único

```text
AGENCIA=RX550-INVESTIGACION · WORK_CLASS=AGENT-MAIN-TOOLDESIGN
GENERADO=2026-10-04T11:05:45-03:00 · MEDIDO=EN ESTA HOST, EJECUTANDO las herramientas
AFECTADO=tools/relations.py · tools/claims.py · tools/artifacts.py · tools/frontier.py
ESCRITURA=UN fichero nuevo (08-ARQUITECTURA/tools-nounica/medir_clave_no_unica.py) y ESTE informe
GPU INTACTA · WRITE_EXECUTION=NONE sobre findings/ · MODIFICATIONS=0 sobre 06-INGENIERIA-INVERSA/
```

## 1. Qué se ha medido, y con qué

El encargo pedía medir, no leer. Todo lo que sigue sale de **ejecuciones**, y cada
tabla dice de dónde. El banco de medición es una herramienta nueva, y está
declarada en §8 con el motivo por el que no existía.

### 1.1 Instantánea del árbol

El proyecto tiene otras sesiones escribiendo en `findings/` mientras esto corre, así
que las cifras van ancladas a una instantánea concreta. La publica
`medir_clave_no_unica.proveniencia()`:

| dato | valor |
|---|---|
| momento | `2026-10-04T11:05:45-03:00` |
| ficheros `.md` en `findings/` | **558** |
| sha256 de la lista ordenada de nombres | `b4764cd7ef7515a03047c19d7efeef75e878a0e002bf6d7fb36826dd29f3f98d` |
| sha256 `tools/relations.py` | `240506f0e454933a…` |
| sha256 `tools/claims.py` | `f11e0d40598f65e7…` |
| sha256 `tools/artifacts.py` | `1cbddca54338a7f7…` |
| sha256 `08-ARQUITECTURA/tools/findings_index.py` | `fb2fe26eb3700634…` |
| sha256 `medir_clave_no_unica.py` | `9b8c80490ac51ffd…` |

### 1.2 DERIVA DETECTADA DURANTE LA SESIÓN

**El árbol cambió dos veces mientras medía.** No es una sospecha: lo vi porque dos
ejecuciones del mismo comando dieron poblaciones distintas.

| momento | ficheros `.md` | números distintos | colisiones |
|---|---|---|---|
| 10:44 | 557 | 456 | 74 |
| 10:58 | 558 | 457 | 74 |
| 11:05 | 558 | 457 | 74 |

La causa es `1055-hwip-convierte-el-filtro-en-conclusion.md`, escrito a las 10:57
por otra sesión (`ls -lt` sobre `findings/*.md`). **Este informe usa solo la fila de
las 11:05.** Sin el sha de la lista de nombres, cualquier cifra de aquí sería
irrederivable: dos ejecuciones darían dos poblaciones y las dos serían correctas.

Es la misma clase de problema que el hallazgo 259 documenta para los hallazgos,
pero para las **cifras**: un número sin instantánea no es un dato, es el número
que casó.

---

## 2. El mecanismo tiene dos causas, y solo se había medido una

El hallazgo 259 atribuyó el problema a la **renumeración**: dos sesiones numeran a
la vez y un número acaba en dos ficheros. Eso es cierto, y `findings_index.py` lo
mide bien. Pero al bajar al código de los consumidores aparece un **segundo
mecanismo, independiente**, que no aparece en ninguna de las 74 colisiones porque
en `findings_index.py` los cuatro dígitos sí se ven.

### 2.1 Cuatro criterios de índice para el mismo directorio

MEDIDO con `medir_clave_no_unica.comparar_indices()`, que reconstruye cada índice
con el regex **y la convención de reserva** de la herramienta que lo usa:

| consumidor | regex | claves | documentos | nodos con >1 documento | documentos fundidos en otros nodos | números reales que no ve |
|---|---|---|---|---|---|---|
| `findings_index.py` | `^(\d{3,4})-` | 457 | 558 | 74 | **101** | 0 |
| `artifacts.py` | `^(\d{3,4})[-_](.+)\.md$` | 457 | 558 | 74 | **101** | 0 |
| `relations.py` | `^(\d{3})[-_](.+)\.md$` + reserva `f[:3]` | 416 | 558 | 77 | **142** | **41** |
| `claims.py` | `^(\d{3})[-_]` + reserva `f[:3]` | 416 | 558 | 77 | **142** | **41** |
| `frontier.py` | `^(\d{3})` + `continue` (sin reserva) | 416 | 558 | 77 | 142 | **41** |

**Los cinco criterios son distintos y tres de ellos son de tres dígitos.**

### 2.2 El truncamiento `f[:3]`, que es un mecanismo de fusión diferente

`relations.py:252` y `claims.py:805` hacen:

```python
num = m.group(1) if m else f[:3]
```

Un hallazgo de cuatro dígitos no casa con `^(\d{3})[-_]`, así que recibe `f[:3]`:
**1054 pasa a ser el nodo `105`**. MEDIDO con `medir_truncamiento_f3()`:

| nodo | documentos de cuatro dígitos que caen dentro |
|---|---|
| `100` | 5 |
| `101` | 3 |
| `102` | 10 |
| `103` | 8 |
| `104` | 10 |
| `105` | 6 |
| **total** | **42** |

Y **los 42** caen en un nodo que **además tiene un hallazgo de tres dígitos real**.
O sea: el nodo `105` son seis documentos —el 105 de tres dígitos y los cinco
hallazgos 1050 a 1054— y para `relations.py` y `claims.py` es **un** nodo.

Esto no es la renumeración del 259: es un regex de tresApplied a un árbol que ya
llegó a cuatro dígitos. Las dos colisiones se suman: 101 documentos fundidos por
renumeración (según el criterio más amplio) más 41 por truncamiento, **142 en las
herramientas que sólo ven tres dígitos**.

> Y el proyecto **escribió** sobre esto. `1002-correccion-a-105-...md` es un
> hallazgo de cuatro dígitos que trata precisamente de la numeración, y para
> `relations.py` es el nodo `100`.

### 2.3 `frontier.py` asigna donde los demás acumulan

`tools/frontier.py:613-621`, dentro de `main()`:

```python
indices: Dict[str, List[Tuple[str, str]]] = {}
...
    mnum = re.match(r"^(\d{3})", f)
    if not mnum:
        continue
...
    indices[mnum.group(1)] = [(f, txt)]
```

No es `setdefault`: es **asignación**, así que de cada número se queda **el último
fichero en orden alfabético** y los anteriores desaparecen del índice de "qué
hallazgos pueden cerrar un hueco". MEDIDO con `medir_indice_frontier()`, que
replica esas nueve líneas literalmente porque no están en ninguna función
alcanzable:

| dato | valor |
|---|---|
| claves en su índice | 416 |
| documentos de tres dígitos que desaparecen del índice | **100** |
| números afectados | 77 |

Los otros 42 (los de cuatro dígitos) no desaparecen: nunca entraron, por el
`continue` de la línea 618. **100 + 42 = 142**, que es la misma cifra de
documentos fundidos de la tabla 2.1. Cuadra.

Y este índice **no es observable desde fuera**: su salida `--json` no expone las
aristas de cierre. Ver §7.

---

## 3. (a) y (b) — tabla por consumidor

Fuente: `medir_clave_no_unica.medir()` → clave `por_consumidor`. Cada fila es el
grafo que la herramienta construye de verdad, no una descripción de lo que
debería construir.

| consumidor | nodos | documentos que esos nodos representan | **documentos que el grafo NO distingue** | nodos ambiguos | nodos que funden 3 o más | aristas | aristas a nodo ambiguo | aristas a nodo inexistente | aristas desde origen ambiguo |
|---|---|---|---|---|---|---|---|---|---|
| `relations.py` (y `KNOWLEDGE-GRAPH.md`, que lo consume) | 117 | 208 | **91** | 47 | 24 | 190 | **103** | 0 | **103** |
| `claims.py:retracciones` | 33 | 73 | **40** | 17 | 11 | 31 | 19 | 0 | 16 |
| `artifacts.py gen_contradictions` | 36 | 73 | **37** | 16 | 9 | 31 | 16 | 0 | 15 |
| `artifacts.py gen_current_state` | 34 | 54 | **20** | 15 | 6 | 34 | 20 | **1** | 13 |
| `artifacts.py gen_evidence_matrix` | 28 | 47 | **19** | 12 | 7 | 22 | 10 | 0 | 8 |

### 3.1 La premisa del encargo, comprobada

> «el 40 por ciento de los nodos son dos o tres documentos fundidos en uno»

MEDIDO, y es exacto para el grafo más grande: en `relations.py`,
**47 nodos ambiguos de 117 = 40,2 %**. En los otros cuatro oscila entre el 45 % y
el 59 % (`current_state`: 15/34 = 44 %; `claims`: 17/33 = 52 %;
`contradictions`: 16/36 = 44 %; `evidence_matrix`: 12/28 = 43 %). **La premisa
se sostiene**, y el máximo de la columna "documentos que el grafo no distingue"
—`relations.py`, 91 de 208— es el peor caso.

### 3.2 Cuántos documentos puede ser una arista

Un número más XY documentos en el origen y Z en el destino produce hasta X·Y
aristas de documento distintas, y el grafo guarda una. MEDIDO:

| consumidor | aristas | pares de documentos que una arista puede ser | aristas con referente único |
|---|---|---|---|
| `relations.py` | 190 | **815** | 59 |
| `claims.py` | 31 | **206** | 10 |
| `gen_contradictions` | 31 | **165** | 12 |
| `gen_current_state` | 34 | 109 | 12 |
| `gen_evidence_matrix` | 22 | 71 | 11 |

**En `relations.py`, 131 de 190 aristas no tienen un referente único.** Y de
esas, 75 tienen los **dos** extremos ambiguos, así que el número de documentos
que una sola fila de `KNOWLEDGE-GRAPH.md` puede representar es de hasta 9
(`105` hacia `102`: 6 × 10).

### 3.3 El nombre que el proyecto ya escribió y la herramienta tiró

| consumidor | aristas con nombre de fichero en el token | aristas sólo con número |
|---|---|---|
| `relations.py` | 73 | 117 |
| `gen_contradictions` | 16 | 15 |
| `gen_current_state` | 17 | 17 |
| `gen_evidence_matrix` | 0 | 22 |
| `claims.py` | **0** | **31** |

`claims.py` sale con **0 de 31**: `retracciones()` devuelve sólo números
(`re.findall(r"CORRECTS=(\d{3})", texto)`), y el nombre que el autor escribió se
pierde ahí. Es el hallazgo 1054 medido sobre el alcance de 24 líneas, confirmado
aquí sobre las aristas que la función produce de verdad.

### 3.4 La arista rota, identificada

`gen_current_state` publica **1** corrección rota (el resto de las 2 "rotas" son
filas, no aristas: ver §6.1). Es `1011-el-grep-de-ad8-no-puede-distinguir-y-el-isa-si.md
-> corregida por 04-IMPLEMENTACION`, y es real: el token es una ruta, no un
hallazgo. Coincide con lo que midió el 1054.

---

## 4. (c) CONTRADICTIONS.md — el sentido

`gen_contradictions` (tools/artifacts.py:792) calcula el SENTIDO de cada arista
con una lista positiva de 12 verbos y la función `sentido()` de la línea 849. El
hallazgo 259 afirma que eso "produce resultados incorrectos sin ninguna señal".
**EsTrue a medias, y la parte media importa.**

MEDIDO con `medir_clave_no_unica.sentido_medido()`, que invoca `sentido()` con
cada candidato por separado:

| pregunta | número | cómo se comprobó |
|---|---|---|
| aristas de contradicción en el grafo | **31** | `contraste_con_artefactos`: el artefacto dice «31 aristas de contradiccion, 11 verbos» |
| con destino ambiguo | **16** | `len(docs_detras(dest)) > 1` |
| **el TEXTO del sentido depende del documento** | **0** | `sentido()` se invoca una vez por candidato, pasando el número como hace `artifacts.py:879`. Los candidatos de un número ambiguo **comparten ese número**, luego la llamada es idéntica |
| el REFERENTE es decidible leyendo el cuerpo del origen | **9** | se busca en el cuerpo de cada candidato del origen una cita por nombre (`\d{3}[a-z0-9-]*\.md`) a un candidato del destino |
| el REFERENTE es indecidible | **7** | ningún candidato del destino aparece nombrado |
| aristas cuyo token crudo resuelve exacto | **7** | el token lleva nombre de fichero |

**O sea: el texto impreso es invariante, y lo que no es invariante es a qué
documento se refiere.** `sentido()` no recibe un documento: recibe
`(num, num, verbo)`. No hay ningún grado de libertad quedependa de qué fichero
se elija, y por eso la frase sale idéntica y no puede avisar de nada.

Y esa frase puede ser verdad para un candidato y falsa para los otros. **Caso
concreto, buscado por mí y no por el 259:**

```
fila publicada:  035 | `RETRACTED_BY` | `RETRACTED_BY!` | 043 | 035 RECIBE de 043
destino 043, tres documentos:
    043-asercion-struct-mqd-contra-offsets.md      -> no retracta nada de 035
    043-pll-bsp-asi-pasi.md                         -> no retracta nada de 035
    043-vuelta-atras-035-y-036-leian-el-asic-equivocado.md  -> RETRACTS=035, 036
```

Comprobado leyendo, no suponiendo:

- `grep -ci "retract\|035"` sobre los dos primeros devuelve **0** en ambos.
- La cabecera del tercero dice, textual: `` `RETRACTS=035, 036 y parte de 037` ``.

**La frase «035 RECIBE de 043» es verdadera para uno de los tres candidatos y
falsa para los otros dos.** Y lo mismo con `036 --RETRACTED_PARTLY_BY--> 043`,
que el grafo también contiene.

Es exactamente el modo de fallo que el 259 describe, con un matiz que el 259 no
distingue: **el daño no está en que el cálculo del sentido sea incorrecto —el
cálculo es correcto—, sino en que la frase es un enunciado sobre un documento que
no identifica, y se publica sin marca.**

### 4.1 El origen también es ambiguo, y eso sí se deshace

`relations.py` graba el origen como un número, así que una arista desde un número
duplicado no dice qué documento la declara. Eso **se puede deshacer sin leer
prosa**: se busca el token literal `verbo=token` en las 18 primeras líneas de
cada candidato del origen, que es el mismo alcance que usa la herramienta.

MEDIDO con `medir_clave_no_unica.origen_declarante()`:

| consumidor | aristas con origen ambiguo | desambiguadas por búsqueda literal | sigue ambiguo |
|---|---|---|---|
| `relations.py` | 103 | **103** | 0 |
| `gen_contradictions` | 15 | **15** | 0 |
| `gen_evidence_matrix` | 8 | 7 | 0 (1 sin declarante) |
| `claims.py` | 16 | `NOT_APLICABLE` | `NOT_APLICABLE` |
| `gen_current_state` | 13 | `NOT_APLICABLE` | `NOT_APLICABLE` |

`NOT_APLICABLE` y no `0`: para esos dos, el campo «verbo» de la arista lo pone
este banco, no el autor, así que la búsqueda literal `verbo=token` no puede
encontrar nada. Un cero ahí sería un número sin significado, y se escribe
`NOT_APLICABLE`.

**Las 103 aristas de origen ambiguo de `relations.py` se desambiguan el 100 %**
con una búsqueda literal. Es el dato más accionable de este informe: la
ambigüedad del origen es **recuperable**, y la del destino no siempre.

---

## 5. (d) Qué cambia de resultado al elegir documento — y el cero medido

El encargo pedía el número del cambio. **Medido: en ocho agregados, el cambio es
cero.** Y es un cero que hay que escribir, no callar.

Método: se construyen **200 funciones de elección** deterministas (semilla fija
`20261004`) que asignan un documento a cada nodo, se calcula el grafo de
documentos de cada una, y se cuenta cuántos valores distintos toma cada campo.
`valores_distintos > 1` ⇔ el resultado depende del documento.

| consumidor | nodos | aristas | grado máximo | ¿ciclo? | nodos en ciclo | ¿orden topológico? | camino más largo (condensado) | autoloops | **campos que dependen** |
|---|---|---|---|---|---|---|---|---|---|
| `relations.py` | 117 | 190 | 18 | sí | 39 | no | 59 | 13 | **0 de 8** |
| `claims.py` | 33 | 31 | 5 | sí | 4 | no | 6 | 0 | **0 de 8** |
| `gen_contradictions` | 36 | 31 | 5 | sí | 5 | no | 6 | 0 | **0 de 8** |
| `gen_current_state` | 34 | 34 | 9 | sí | 4 | no | 4 | 1 | **0 de 8** |
| `gen_evidence_matrix` | 28 | 22 | 3 | no | 0 | sí | 4 | 0 | **0 de 8** |

Los valores son **idénticos en las 200 elecciones**, no sólo iguales entre
mínimo y máximo.

**Por qué, y por qué es correcto que sea así:** los ocho campos son agregados por
clave. El número de nodos es uno por clave, el de aristas es uno por arista
registrada, el grado máximo es el máximo sobre claves —y whichever documento
elijas para una clave, esa clave tiene los mismosdegreeedges—; y un ciclo entre
claves es un ciclo entre los documentos elegidos. **La invariancia de estos ocho
campos no dice que el grafo esté bien.** Dice que la ambigüedad no se ve en un
agregado.

### 5.1 Mi primera versión de esta medición decía otra cosa, y estaba mal

La primera versión comparaba el grafo fundido contra un **soplado** (todas las
combinaciones origen × destino). Ahí salía «6 de 8 campos CAMBIAN» en
`relations.py`, con el camino más más largo pasando de 59 a 391.

**El soplado no es una función de elección válida.** No corresponde a ninguna
lectura que el proyecto pueda hacer: multiplica aristas que nunca coexisten. Lo
detecté porque `nodos` daba el mismo número en el fundido y en el «mínimo», lo
que es imposible si el mínimo fuera un grafo de documentos: es el mismo conjunto
de claves con otro nombre. Lo cambié por el muestreo de elecciones reales y dio
cero. **Es la décima vez esta sesión que mido el patrón en vez de la medición**,
que es lo que el propio 1054 documenta; lo dejo escrito porque el número
equivocado era más grande y más atractivo que el correcto.

### 5.2 Donde sí cambia: la identidad

Los agregados son invariantes; **la identidad de qué documento los ocupa, no**:

| consumidor | conjuntos distintos de documentos en ciclo (200 elecciones) | documentos distintos en el nodo de grado máximo |
|---|---|---|
| `relations.py` | **200** | **2** |
| `gen_contradictions` | **24** | **2** |
| `claims.py` | 8 | 3 |
| `gen_current_state` | 8 | 3 |
| `gen_evidence_matrix` | 1 | 1 |

En `relations.py`, **las 200 elecciones produjeron 200 conjuntos de documentos en
ciclo distintos**: no hay dos elecciones que coincidan. Eso significa que la
pregunta «¿qué documentos están en un ciclo?» no tiene respuesta con el grafo que
se publica, y que cualquier respuesta que dé un lector sobre el grafoPublished
depende de una elección que el artefacto no declara.

Y en `gen_evidence_matrix` los dos son 1: no hay ambigüedad *en estos campos*
porque **el grafo no declara ninguna** (ver §6.4), y por eso tampoco se puede
medir.

### 5.3 Lo que sí se puede afirmar del daño, con número

El daño medible no está en un agregado. Está en que **una fila del artefacto no
dice a qué documento se refiere**:

- `KNOWLEDGE-GRAPH.md`: 190 filas, **131 sin referente único**, 103 de ellas
  publicadas sin más marca que el nombre del verbo.
- `CONTRADICTIONS.md`: 31 filas, **16 con destino ambiguo**, y la columna
  `sentido` es una frase cuyo referente no se identifica.
- `CURRENT-STATE.md`: 32 filas, **12 rotuladas AMBIGUAS** — el único consumidor
  que declara el problema.
- `EVIDENCE-MATRIX.md`: 22 tokens de corrección, **10 apuntan a un número con más
  de un fichero, y el artefacto no lo dice en ninguna parte**.

Fila real, tal como la publica `gen_evidence_matrix`:

```
| 035 | correccion-ptepde-es-polaris12 | PROVEN x8, SDMA0_HWIP x4, ... | INTACTA | 043 023 | 9 |
```

`043` son tres documentos, `023` son dos, y la columna `reescribe` no lleva
ninguna marca. MEDIDO: 17 filas con `reescribe` no vacío, 22 tokens, **10 a
números con más de un fichero**.

---

## 6. Tres defectos que la medición destapó y no estaban en el encargo

### 6.1 `CURRENT-STATE.md` publica 2 filas duplicadas, y el 1054 dijo que no

MEDIDO sobre el texto que produce `gen_current_state()` en memoria
(`contraste_con_artefactos.current_state_dedup`):

| dato | valor |
|---|---|
| filas inequívocas | 18 |
| filas AMBIGUAS **publicadas** | **12** |
| items AMBIGUAS **distintos** | **10** |
| filas publicadas de más | **2** |
| filas rotas | 2 |
| filas de retracción | 8 |

Las dos repetidas, textuales:

```
- `072-la-lista-cerrada-de-ve -> corregida por 041  [3 candidatos]`
- `072-la-lista-cerrada-de-ve -> corregida por 041  [3 candidatos]`
- `073-el-indice-por-numero-d -> corregida por 040  [3 candidatos]`
- `073-el-indice-por-numero-d -> corregida por 040  [3 candidatos]`
```

**La causa**, en `tools/artifacts.py:481-484`:

```python
if item in corr or item in corr_ambigua or item in corr_rota:
    continue
...
if estado == "AMBIGUA":
    corr_ambigua.append("%s  [%d candidatos]" % (item, len(det)))
```

El guard busca `item` a secas; lo que se guarda es `item` **con el sufijo**
`"  [N candidatos]"`. La comparación nunca es cierta para una fila ambigua, así
que una ambigua repetida se publica tantas veces como aparece.

**Esto refuta una afirmación del hallazgo 1054**, que en su tabla de «antes y
después» dice `aristas duplicadas | 4 | 0`. Ejecutando la herramienta hoy, las
mismas dos filas que el 1054_IDENTIFICÓ como duplicadas (`072 → 041` y
`073 → 040`) **siguen duplicadas**. El 1054 arregló el duplicado de las filas
inequívocas —que es donde estaba el `setdefault`— y no vio que el guard de la
rama ambigua nunca casa.

*Desfalsificación*: si `gen_current_state()` publicara 10 filas AMBIGUAS y no 12,
esta sección cae. Se cuenta sobre el texto que produce la función, no sobre una
replicación.

### 6.2 La misma relación está en el grafo dos veces, en las dos direcciones

`pares_inversos()` (que cruza `RETRACTS`/`RETRACTED_BY` y `CORRECTS`/`CORRECTED_BY`):

| consumidor | pares ordenados distintos | pares inversos | aristas en un par inverso |
|---|---|---|---|
| `relations.py` | 172 | **6** | **12** |
| `gen_contradictions` | 31 | **6** | **12** |
| los otros tres | — | 0 | 0 |

Los seis, textuales:

```
019 <-> 030   CORRECTED_BY / CORRECTS
023 <-> 035   CORRECTED_BY / CORRECTS
030 <-> 019   CORRECTS / CORRECTED_BY
023 <-> 035   CORRECTED_BY / CORRECTS
035 <-> 043   RETRACTED_BY / RETRACTS
043 <-> 035   RETRACTS / RETRACTED_BY
```

(es decir, tres pares: 019↔030, 023↔035 y 035↔043, contados en las dos
orientaciones)

El generador calcula el SENTIDO de cada fila, y con eso podría parecer que el
problema está resuelto. No lo está: **`035` dice `RETRACTED_BY=043` y `043` dice
`RETRACTS=035`**, luego la misma relación son **dos** aristas, y cada una es un
ciclo de longitud 2 con la otra. Eso explica los ciclos que hay en cuatro de los
cinco grafos, y significa que el recuento de aristas de contradicción está
inflado por el factor que sea, y que el recuento de ciclos no mide lo que un
lector creería que mide.

### 6.3 Un autolooop sobre un nodo de tres documentos puede ser una arista real

`relations.py` marca `SELF` cuando `dest == num`. MEDIDO: 13 autoloops, de los
cuales **1** cae sobre un nodo con más de un documento:

```
096 --HALLAZGO--> 096    candidatos: 096-arbitraje-dram-sin-inicializar-y-tabla-de-ventilacion.md
                             096-el-discriminante-abc-no-es-cerrable-desde-el-corpus.md
                             096-se-mecanismo-de-fence-completo.md
```

Si los dos documentos que se nombran no son el mismo, eso no es un ciclo: es una
arista entre dos hallazgos distintos que el grafo publica como una relación consigo mismo.
No se ha decidido cuál de los dos documentos habla, y por tanto **no se puede
saber si es un error o un dato**. Es `NOT_DETERMINED`, y se escribe así.

### 6.4 `EVIDENCE-MATRIX.md` es el peor de los cinco, y por qué

No por tener másambigüedad: `gen_evidence_matrix` es el único con **cero
marcadores**. `tools/artifacts.py:252-254`:

```python
for rx in (r"RETRACTED_BY=(\d{3,4})", r"CORRECTS=(\d{3,4})",
           r"IMPLEMENTS=(\d{3,4})", r"GENERALIZAD[OA]_POR=(\d{3,4})"):
    retr += " " + ",".join(re.findall(rx, cab))
```

Sin marca de ambigüedad, sin guard de auto-referencia, y con `\d{3,4}` sobre las
**14** primeras líneas (mientras `gen_current_state` usa el fichero entero y
`relations.py` usa 18). MEDIDO: 22 tokens publicados, 10 a números con más de un
fichero, **0 marcas**.

Medido también, y en contra de lo que yo mismo había escrito en un borrador de
este informe: `gen_current_state` **no** publica ninguna auto-arista. Su guarda es
`if m.group(1) in str(det)`, una **comparación por subcadena**, y filtra el único
caso que hay:

```
030-page-walker-gfx8-2-niveles.md:117
  "el finding original queda marcado como `CORRECTED_BY=030` en lugar de
   reescrito, porque AGENTS.md §Documentación prohíbe sobrescribir evidencia
   histórica."
```

MEDIDO: `current_state_filtradas_por_la_guarda` = `['030 -> 030']`, y las 40
filas de corrección y retracción que publica el artefacto **no** incluyen ninguna
auto-arista. La prosa de `030-page-walker` describe la convención y la guarda la
descarta, que es lo correcto.

Lo dejo escrito porque es el **segundo** error de este informe que sólo aparece al
comparar con el artefacto y no con mi propia cuenta: el primero fue el soplado de
§5.1, y éste fue una **polaridad invertida** en una comprobación minha, que
medía "auto-aristas sin guarda" guardingando los casos **con** guarda. Un campo
cuya polaridad no se ha contrastado con la salida real es una fuente de cifras
invertidas, y por eso el nombre del campo dice lo que hace.

---

## 7. Lo que NO se ha podido determinar, y por qué

| pregunta | estado | qué falta |
|---|---|---|
| ¿De cuál de los seis documentos del nodo `105` habla cada fila de `KNOWLEDGE-GRAPH.md` que sale de un hallazgo de cuatro dígitos? | `NOT_DETERMINED` | `relations.py` graba `num = f[:3]` para esos ficheros y **no guarda el nombre del origen**. La arista no lleva información suficiente. Para el **destino** sí se puede, con el token crudo: 7 de las 16 aristas de contradicción lo traen |
| ¿Cuántos huecos de `OPEN-FRONTIERS.md` se declaran obsoletos por un hallazgo que no es el que lo cierra? | `NOT_VERIFIABLE` | Las aristas de cierre de `frontier.py` (`obsoleto_por`) **no se exponen en `--json`**: se rellenan en `main()` y no llegan a la salida. Los 100 documentos que su índice de overwrite pierde no son contables desde la herramienta |
| ¿El índice de `frontier.py` cambia algún veredicto, o solo pierde candidatos? | `NOT_VERIFICABLE` | Por lo anterior. Se midió **el tamaño de la pérdida** (100 documentos, 77 números) replicando `frontier.py:613-621` porque no están en ninguna función, pero **el efecto sobre `n_obsoletos` no se puede observar** |
| ¿Qué documento es el canónico de cada una de las 74 colisiones? | `NOT_DETERMINED` | Ningún dato del árbol lo dice. Lo dice el 259 y se sigue diciendo: es trabajo de decisión, no de herramienta |
| ¿Las 2 filas «rotas» de `CURRENT-STATE.md` son las mismas que midió el 1054? | `PARCIAL` | Una sí es la misma (`1011 → 04-IMPLEMENTACION`). La segunda es `1054 → 040-smu-...`, y la produce la **propia prosa del 1054**, que escribe el token abreviado `` `CORRECTS=040-smu-...` ``. `grep -o` sobre `1054-*.md` devuelve 1 aparición. Es un fantasma de prosa, no una referencia rota, y no lo había contado nadie |
| ¿Qué aristas de `relations.py` con origen ambiguo son correctas? | `NOT_APPLICABLE` por arista, `RESUELTA` en bloque | Las **103** se desambiguan el 100 % por búsqueda literal (§4.1). Lo que no se sabe es si el **destino** de cada una es el que el autor quiso, y eso exige leer |
| El autolooop `096 → 096` | `NOT_DETERMINED` | Falta decidir cuál de los tres documentos `096-*.md` declara `HALLAZGO=096`. No es un dato que se pueda leer de la arista |

---

## 8. Decisiones, y por qué

### 8.1 Se ha escrito UNA herramienta nueva, y está aquí

`08-ARQUITECTURA/tools-nounica/medir_clave_no_unica.py`, **1209 líneas** (131
vacías, 106 de comentario o docstring), sha256 `9b8c80490ac51ffd…`. Directorio
nuevo, declarado, porque `tools/` tiene otra sesión escribiendo y una puerta que
corre los self-tests con `cwd=tools/`.

**Por qué hace falta y no se entrega solo la medición.** Leí
`relations.py`, `claims.py` y `findings_index.py` enteros, y `artifacts.py` en las
funciones que importan. Lo que hay:

- `findings_index.py` mide las 74 colisiones y tiene `--colisiones` y `--json`.
  **No baja a los grafos**: no sabe cuántas aristas apuntan a un número ambiguo.
- `relations.py` marca las aristas ambiguas con `!` y las cuenta. **No cuenta la
  población** que hay detrás, no calcula grado, camino, orden topológico ni
  ciclos, y su índice es de tres dígitos con reserva `f[:3]`.
- `artifacts.py:resolver_destino` clasifica un token en cuatro estados, y **solo
  se usa en `gen_current_state`**. No lo usan `gen_knowledge_graph`,
  `gen_contradictions` ni `gen_evidence_matrix`, que son los que más aristas
  ambiguas tienen.
- `claims.py:retracciones` construye aristas y **no tiene ningún marcador de
  ambigüedad**.

Lo que no existe en ninguna parte es la **cruce**: para cada consumidor, nodos,
población, aristas afectadas y resultado calculado. Eso es lo que hace el banco.

**Lo que hace, y lo que no hace.** Llama a `relations.escanear()`,
`claims.retracciones()`, `artifacts.resolver_destino()`, `artifacts.gen_*()` y
`frontier.py --json`. No reimplementa ninguna de esas lógicas. Lo único que
replica es `frontier.py:613-621` (declarado en el docstring y en §2.3, porque
está dentro de `main()` y no es alcanzable) y la función `sentido()`, que es una
closure local; esa copia **se autocomprueba**: produce cadenas que salen
**literales** en el artefacto que genera la función original, 31 de 31.

**Lo que deliberadamente NO hace:** no escribe ningún fichero del proyecto, no
toca `tools/`, no edita ningún hallazgo, no abre `/dev/dri`, y no regenera
`CURRENT-STATE.md`, `KNOWLEDGE-GRAPH.md`, `CONTRADICTIONS.md` ni
`EVIDENCE-MATRIX.md`. Los cuatro artefactos se producen **en memoria** para
medirlos, y su texto aparece en §6.1 y §5.3.

### 8.2 `sys.path` anclado a la ruta del módulo

```python
_AQUI = os.path.dirname(os.path.abspath(__file__))
ROOT  = os.path.dirname(os.path.dirname(_AQUI))
```

No al directorio de trabajo. El hallazgo 1051 encontró tres herramientas cuyo
`--repo` por defecto era el cwd, y esa es exactamente la clase de error: una
herramienta que sólo da el árbol correcto cuando la llamas desde el sitio
correcto.

### 8.3 `resolver_destino` importado, no reimplementado

Se importa de `tools/artifacts.py` y se usa en `grafo_current_state()`, con el
mismo `bynum` que construye `gen_current_state`. Sus cuatro estados se cuentan:
MEDIDO en esta instantánea, 53 coincidencias de `RX_CORR` → **19 RESUELTA, 13
AMBIGUA, 2 INEXISTENTE, 19 NO_REFERENCIA**.

### 8.4 Los agregados se miden por muestreo, no por cotas

200 elecciones con semilla fija. Una cota —el soplado de §5.1— no es una función
de elección válida y dio un número mayor y equivocado. El muestreo sí responde a
la pregunta: «¿cuántos valores distintos toma este campo al elegir documento?».

### 8.5 No se ha hecho commit

Ni se ha editado ningún hallazgo. Los números 1055, 1056 y siguientes que aparezcan
mientras se lea esto son de otra sesión y no invalidan este informe: lo que lo
invalidaría es un cambio en `tools/`, y sus hashes están en §1.1 para
comprobarlo.

---

## 9. Resumen para quien solo lea esto

1. **El 40 % es real.** En `KNOWLEDGE-GRAPH.md`, 47 de 117 nodos son dos o tres
   documentos: 91 documentos que el grafo no distingue.
2. **El daño no es un error: es un grafo coherente con una población fundida.**
   131 de 190 aristas no tienen referente único. En `CONTRADICTIONS.md`, 16 de 31.
3. **Los agregados no lo delatan.** Ocho campos escalares dan **exactamente el
   mismo valor** en 200 elecciones de documento distintas. Cero medido, con el
   método a la vista. Lo que cambia es **qué documento** ocupa cada nodo: en
   `relations.py` las 200 elecciones dan 200 conjuntos de documentos en ciclo
   distintos.
4. **El SENTIDO de `CONTRADICTIONS.md` es invariante y por eso no avisa.**
   `sentido()` recibe dos números, no dos documentos. La frase «035 RECIBE de 043»
   es verdadera para uno de los tres `043` y falsa para los otros dos.
5. **Hay un segundo mecanismo, medido y no registrado:** el truncamiento `f[:3]`
   mete 42 hallazgos de cuatro dígitos dentro de nodos de tres, y los 42 caen en
   nodos que ya tienen un hallazgo real. Suma 41 documentos fundidos a los 101 de
   la renumeración.
6. **Dos defectos medidos que no estaban en el encargo:** `CURRENT-STATE.md`
   publica 2 filas duplicadas porque el guard de deduplicación busca el `item`
   sin el sufijo que se le añade al guardarlo (§6.1), lo que **refuta** el «aristas
   duplicadas: 0» del hallazgo 1054; y `relations.py` guarda **12 aristas** que
   son **6 relaciones** puestas en las dos direcciones, lo que explica los ciclos
   de cuatro de los cinco grafos (§6.2).
7. **Lo accionable y medido:** las 103 aristas con origen ambiguo de
   `relations.py` se desambiguan **el 100 %** con una búsqueda literal del token
   en las 18 primeras líneas del origen (§4.1). La del destino, no siempre: 7 de
   16 la resuelven y 9 de 16 la resuelven leyendo el cuerpo.