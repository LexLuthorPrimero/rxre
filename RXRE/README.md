# RXRE — AI-native reverse engineering platform

**Estado real, no deseado: FASE 0 completada. FASE 1 no empezada.**

Este directorio existe porque el project's tooling ya era grande (217
herramientas inventariadas) y no tenía una plataforma que lo conectara. La
primera tarea no fue construir esa plataforma: fue **medir qué hay**, porque
construirla sin medir habría producido una segunda colección de herramientas
al lado de la primera.

| | |
|---|---|
| instrumento | `rxre_boot` · `rxre_frontier` · `rxre_contracts` · `rxre_deleg` · `rxre_touch` |
| artefacto | `artifacts/BOOTSTRAP-001.json` (sha256 `a5437da2…`) |
| vectores | **19** · **22** · **17** · **10** · **18** = **86** — todos PASS |
| hallazgo | `1481` `1487` `1491` `1501` `1505` `1507` `1510` `1513` `1515` `1517` `1519` |
| runner | `08-ARQUITECTURA/tools/toolkit_cross.py` los cruza (sección 4) |

---

## Lo que este directorio NO es

No es una reimplementación de nada. `tools/` sigue siendo la verdad:

```
tools/rxre.py      orquestador de catálogo ejecutable, 188 vectores
tools/toolreg.py   el registro: UNA sola lista de 217 herramientas
tools/prov.py      procedencia declarada en el corpus de hallazgos
tools/relations.py vocabulario real de relaciones entre hallazgos
```

`rxre_boot.py` **carga** esos tres y no vuelve a recorrer el árbol por su cuenta.
Un segundo catálogo de herramientas divergente es exactamente el problema que
`rxre.py` existe para eliminar, y no se reintroduce aquí.

---

## Resultado de FASE 0 (los doce artefactos, medidos)

`python3 RXRE/tools/rxre_boot.py` imprime el resumen; `--json` da el informe
completo; `--out` lo persiste.

### 1. TOOL INVENTORY — 217 entradas, de `toolreg`, no recalculado

```
tools                                97
08-ARQUITECTURA/tools                74
revkit                               33
04-IMPLEMENTACION/rx550-driver/tools  6
09-POWER-CLOCKS/tools                 4
04-IMPLEMENTACION/tools               2
01-AUDITORIA/tools                    1
```
python 192 · c 15 · shell 10. 157 declaran `--selftest`, 114 declaran
seguridad, 56 declaran límites. **0 rutas del inventario que no existan.**

### 2. CAPABILITY MATRIX — el hueco real

| | |
|---|---|
| filas del catálogo `CAP` | 26 |
| herramientas distintas | 25 |
| capacidades declaradas | 28 (+1 solo-refutada = 29) |
| **entradas del registro SIN capacidad** | **213 de 217** |

### 3. DEPENDENCY GRAPH — 165 aristas, y una cota

```
import          48
from-import      7
ruta-en-cadena 110
```
**Y el límite, que es la cifra que importa:** **172 llamadas por `subprocess`
NO son aristas**. El grafo es una **cota inferior** del acoplamiento real, y
no se acerca al orden de magnitud.

### 4. INPUT/OUTPUT MAP — parseo estático, sin ejecutar

101 con `--json` · 158 con `--selftest` · **93 con las dos** · 65 con `--selftest`
pero sin `--json` · 8 con `--json` pero sin `--selftest` · 51 con ninguna.
`--help-probe` existe y registra el rc; **no se usó** para `1481`, así que
`1481` no afirma que nada arranque.

### 6. DATA FORMAT MAP — extensiones *citadas*, no *producidas*

`.md` 797 menciones / 45 herramientas · `.h` 392 / 66 · `.txt` 37 / 19 ·
`.json` 24 / 13 · `.tsv` 18 / 8. Una herramienta que cite `.json` puede no
emitir ninguno: se cuentan **extensiones que el código cita**, no formatos que
produce.

### 7. PROVENANCE MAP — 217 analizadas, 9 sin ningún campo

`herramienta` 172 · `fuente` 90 · `tool` 60 · `ejecucion` 51 · `hash` 31 ·
`comando` 27 · `consumidor` 24 · `artefacto` 23. **Límite declarado:** se cuentan
**menciones** del nombre del campo; una en un comentario cuenta igual que una
escritura real.

### 8. EVIDENCE MAP — el dato viene del PRODUCTOR

`prov.py` invocado, **no reimplementado** (dos cifras para el mismo número es lo
que `1473` midió): 607 hallazgos con estado, D3 sin **2** (0.3 %), factor
D1/D3 **236.5×**.

### 9. DUPLICATION MAP — 4 nombres repetidos, **ninguno duplicado**

`contradict.py` · `fingerprint.py` · `huella.py` · `xref.py` — los cuatro existen
en `tools/` y en `08-ARQUITECTURA/tools/` con **sha256 distintos**. Mismo
nombre ≠ duplicación; son instrumentos distintos y el riesgo del `toolreg.py`
pisado (§4b de `rxre.py`) sigue vivo.

### 10. GAP MAP

- **5 capacidades sin proveedor**: `ISA_ANALYZE`, `RUNTIME_CLOCK`,
  `RUNTIME_INSPECT`, `STRUCT_OFFSET_LIVE` (ninguna viva) e
  `ISA_DECODE_DESDE_BYTES` (**probada imposible**, con la medición que lo prueba).
  Las 4 primeras ausencias verificadas por fuera con `command -v`: `rga`,
  `rocm-smi`, `drgn`, `clrxdisasm` no están.
- **213 herramientas no enrutables**, 74 de ellas en `08-ARQUITECTURA/tools`
  y 33 en `revkit`.

### 11. CORE CANDIDATES — por puntuación medida, no por opinión

Pesos declarados en el informe. `tools/ibref.py` 19.0 · `tools/toolreg.py` 16.5
· `tools/mmio.py` 14.5 · `tools/layoutcross.py` 14.0 · `tools/nextnum.py` 14.0.

### 12. MINIMAL ARCHITECTURE — derivada de la medición, no del esquema

| paso | qué | por qué |
|---|---|---|
| 1 | cerrar el catálogo de capacidades sobre 192 herramientas | sin esto, *«¿qué herramienta tengo para esto?»* no tiene respuesta para el 88 % del catálogo. **No requiere código nuevo: es medir.** |
| 2 | normalizar el vocabulario de relaciones | 42 etiquetas para 171 aristas no es consultable por relaciones. **No requiere base de datos: es un mapa a vocabulario cerrado, conservando el original.** |
| 3 | execution model con hash de entrada y salida | sin eso, repetir no distingue `IDENTICAL` de `EXPECTED_DIFFERENCE`. **No requiere backend nuevo: `rxre.cache2_put` ya guarda hash de clave y de valor.** |

---

## Uso

```bash
python3 RXRE/tools/rxre_boot.py                        # resumen
python3 RXRE/tools/rxre_boot.py --selftest             # 19 vectores
python3 RXRE/tools/rxre_boot.py --json --out /tmp/b.json
python3 RXRE/tools/rxre_boot.py --help-probe           # EJECUTA cada --help y registra rc
```

`--help-probe` es la **única** forma de que este instrumento afirme que una
herramienta arranca. Sin él, sólo afirma qué opciones declara su código.

---

## Garantías

- **SOLO LECTURA** del árbol. Escribe únicamente en `--out`.
- **Declara su contrato** (`# CONTRACT:`) como las 65 herramientas que lo hacen,
  **con un campo `TOUCHES_INTEGRATED` que el vocabulario de `toolkit.py` no
  tiene** — ver hallazgo `1487`. `WRITES_FILES` se declara
  `only_with_--out`, que está fuera del vocabulario `yes`/`no` **a propósito**:
  `no` sería una mentira que el validador no puede detectar, y `yes` haría creer
  que escribe sin que se le pida.
- **`exit 0` no significa resultado válido**: cada sección imprime su estado y
  el informe lleva `estado` por bloque.
- **`toolreg` es la única fuente del inventario.** Si pierde la interfaz
  (`inventory`, `run_selftests`, `TOOL_DIRS`), esto dice **qué** falta y sale
  con rc=1 en vez de inventar un catálogo paralelo.
- **Ningún vector apagado.** Los que se escribieron con `else True` o con una
  resta cuyos lados se cancelan se sustituyeron por la partición real.

### Una reparación, y cómo se comprobó que fue fiel

Un `sed` mío sustituyó el primer `#` de cada línea del fuente y damaged 147
líneas: comentarios perdidos y dos literales rotos. Se reparó mecánicamente —
restaurar los comentarios en línea, y comentar iterativamente lo que `ast.parse`
reportara — hasta que el fichero parseó.

**La prueba de que la reparación fue fiel no es que parsee: es que el artefacto
salga igual.** Se guardó el JSON de antes del daño y se comparó campo a campo:

| invariante | antes | después |
|---|---|---|
| capacidades declaradas | 28 | **28** |
| filas del catálogo | 26 | **26** |
| refutadas / solo-refutadas | 3 / `ISA_DECODE_DESDE_BYTES` | **igual** |
| aristas de dependencia | 165 | **165** |
| `subprocess` no-`arista` | 172 | **172** |
| rutas inexistentes | 0 | **0** |
| nombres duplicados + sha12 | 4 | **4, sha12 idénticos** |
| huecos sin proveedor | 5 | **5, mismos nombres** |

Y los únicos campos que cambian son los que dependen de **cuántas entradas hay
hoy** en el árbol (`entradas` 217→220, `no_enrutables` 213→216): otra sesión
está escribiendo, y eso ya está declarado como confounder en `1481`.

Dos cosas que el parseo **no** cazó y que hubo que encontrar mirando: `ENSAMBLADO`
y `VECTORES` son identificadores válidos, así que fallan en **runtime**, no en
sintaxis. *Un fichero que parsea puede seguir roto.*

## Estructura

```
RXRE/
├── README.md               este fichero: comportamiento verificable
├── tools/rxre_boot.py      FASE 0 — el mapa del tooling (19 vectores)
├── tools/rxre_frontier.py  dónde está la frontera dura y quién la nombra (21)
└── artifacts/              BOOTSTRAP-001.json
```

`ARCHITECTURE.md`, `API.md`, `DATA-MODEL.md`, `PROVENANCE.md`,
`AGENT-PROTOCOL.md`, `TOOL-REGISTRY.md`, `CAPABILITIES.md`, `VALIDATION.md`,
`SECURITY.md`, `ROADMAP.md`, `core/`, `api/`, `storage/`, `adapters/`,
`fixtures/`, `tests/` — **no se crean todavía.** Escribirlos ahora sería
documentación decorativa sobre una arquitectura que no existe (§38), y el
`ROADMAP.md` que sí importa es el de `1481`: los tres pasos de la tabla de
arriba, en ese orden.

---

## `rxre_frontier.py` — la frontera dura, legible

`1487` encontró que el contrato de seguridad **no tiene ningún campo para la
frontera de AGENTS.md**. Esto no la valida: la hace **legible**.

```
integrada (de sysfs)      0x8086:0x0412
discreta  (de sysfs)      0x1002:0x699f
indice de la integrada    card0          <- leido, no supuesto

19 herramientas nombran un nodo de /sys
12 tocan el dominio de la integrada
   POR_INDICE     4   en CODIGO, por POSICION
   POR_PADRE      8   nombran /sys/class/drm sin concretar
   POR_IDENTIDAD  0

ESCRIBEN en /sys (AST)    0     <- NOT_FOUND, NO PROVEN_ABSENT
declaran TOUCHES_INTEGRATED  0
tienen contrato (de las 12)  4
```

Las 4 que usan `card0` en código lo hacen **bien**: `rxre.py` resuelve el reparto
leyendo sysfs, `fingerprint.py` mide la identidad de la iGPU (que es su
trabajo), `snapshot.py` fotografía el reparto, y `_selftest_runtime_obs.py` es
un control negativo. Ninguna cruza la frontera.

### Por qué 4 y no 9

La primera versión contaba `card0` sobre el **texto** y salían 9. La mayoría
eran **comentarios que explican que `card0` es la Intel** — el texto
documentando la frontera, no cruzándola. Separado con AST —el criterio que
`contract_exec.py` ya usa y `toolkit.py` ya pagó— baja a 4.

> el nombre del nodo en un comentario no es un acceso al nodo

### El instrumento falló cuatro veces, y las cuatro en verde

| fallo | qué decía el informe |
|---|---|
| `RAIZ` con un `dirname` de menos | «integrada: None» |
| regex que exigía comillas a ambos lados | «0 herramientas nombran /sys» |
| parser de identidad, dos veces | «`POR_INDICE` 0» |
| variable leída fuera de alcance | `NameError` |

El primero es el instructive: el vector comprobaba que la identidad «se resuelve
**o** se declara no resuelta», y con un `RAIZ` equivocado no se resolvía y se
declaraba — **las dos ramas pasan**.

> un vector con dos salidas aceptables no mide nada
>
> un parser que casi casa devuelve «no hay», que es peor que fallar
>
> normalizar sólo un lado de una comparación no es normalizar

Los cuatro tienen vector ahora. El que cazó el `RAIZ` no se relajó: **se añadió
el que faltaba**.

---

## `rxre_contracts.py` — medir el contrato antes de declararlo

Declarar un contrato es escribir una **afirmación** sobre lo que una
herramienta hace. `1505` construyó primero el instrumento que la **mide**, con el
criterio de `contract_exec.py` más una clase propia
(`LITERAL_EN_PROYECTO`) que hacía falta para distinguir dos riesgos que sin ella
salen iguales.

```
medidas sobre 192 herramientas
  contratos que COINCIDEN      31
  contratos NO SOSTENIDOS       1     <- con nombre, en hallazgos_declarados
  sin contrato declarado      124
  no medibles                   0
```

### El punto ciego que casi me hace acusar de más

La primera pasada marcó **21 `NO_SOSTENIDOS`**. Tres eran falsas:
`run_all.py` declara `WRITES_FILES=yes` y tiene **cero** `open(...,"w")` en su
AST — porque **escribe lanzando ~70 herramientas**. Su AST no ve nada porque no
escribe: delega.

Se añadió el verbo de escritura escritura como clase (`subprocess`, `os.remove`,
`shutil`, `write_text`, `io.open`) y **36 herramientas pasaron de `NO_SOSTENIDA`
a `NO_DETERMINED`**. 21 acusaciones falsas, retiradas.

> una escritura delegada no es una escritura que no exista

### `revkit`: de 0 a 30 contratos

El directorio con más acceso a hardware, con **ninguno**. Ahora **30 de 30, y
los 30 se sostienen con el código**. Verificado: los 30 tienen exactamente 7
campos `# CONTRACT:`, todos dentro de la cabecera de 4000 bytes que lee el
validador.

**17 se declararon `WRITES_FILES=indeterminado`, no `no`.** Se podía haber
puesto `no` y el validador no lo habría detectado: comprueba coherencia entre
contrato y código, no si la herramienta cumple. Eso es una afirmación que nadie
ha comprobado, y por tanto peor que `NO_DETERMINED`. Cada uno lleva escrito por
qué es indeterminado, y son 17 razones distintas.

### Dos vectores que estaban escritos para no fallar

Uno era `("...", True, None)`. El otro comparaba con un `else True`. Los dos
pasaban **siempre** — los escribí para no dejar el hueco, que es exactamente la
forma de apagarlo. Uno sigue **fallando deliberadamente** por un caso real.

> un vector que devuelve `True` no es un vector: es un comentario con forma de código

### Y luego el instrumento mintió (hallazgo `1507`)

La columna `declarado` traducía **todo** valor de `WRITES_FILES` distinto de
`yes` a `no`. Las 17 herramientas que declaran `indeterminado` —precisamente las
que se cuidaron de no mentir— aparecían en la tabla declarando `no`.

```
COINCIDE:  31  ->  44
fuera_de_vocabulario:  (no se medía)  ->  17
```

Los 13 que desaparecieron de `NO_DETERMINED` **no se corrigieron**: cambiaron de
columna. Se detectó guardando el dato **sin traducir** (`declarado_bruto`) y
comparando las dos columnas — una traducción implícita es donde la verdad se
pierde sin que nadie lo note.

Ahora se traduce solo si el valor está en `yes`/`no`; si no, se conserva literal
y una declaración fuera de vocabulario **nunca** sale `COINCIDE`.

> el instrumento no puede mentir en la columna que existe para no mentir

Y de ahí sale un estado que hay que poder nombrar: un instrumento que miente no
es uno que falla — es uno que hace que **sus resultados buenos dejen de ser
creíbles**. Por eso la corrección no fue «arreglar el `if`»: fue añadir el campo
bruto y tres vectores que impidan que una traducción vuelva a decidir sola.

---

## `rxre_deleg.py` — el acoplamiento que el grafo de imports no ve

`rxre_boot` declaraba 172 acoplamientos invisibles y los daba por no medidos.
Ahora están medidos, y el resultado **quitó la preocupación**:

```
llamadas a subprocess          176
  con programa literal           70
  SIN programa identificable    106
  invocan HERRAMIENTAS NUESTRAS  72    <-- todas en TABLAS
  invocan binarios EXTERNOS      57
```

**Ninguna de las 70 llamadas con literal invoca a una herramienta de este
proyecto.** Los 9 programas distintos son todos externos (`git` ×29, `gcc`,
`objdump`, `bash`, `nm`, `grep`…). Las 72 invocaciones entre hermanas están en
`run_all.py`, que las nombra en una **tabla** e itera treinta líneas más allá:

```python
tools = [("cierre de includes de gfx_v8_0.c", ["include_closure.py", ...], 0), ...]
run(label, ["python3", os.path.join(HERE, a[0])] + a[1:], ...)
```

El literal es visible; el `argv` que se ejecuta se construye con `a[0]`.

> una lista de herramientas es un grafo escrito como tabla

**Oráculo:** las 72 invocadas existen en disco. Las 72.

El **NIVEL 4** (destino por flujo de datos, sin `with` ni lista resoluble) **no se
mide** y se declara `NOT_DETERMINED`. No es un cero.

### Y el campo de la frontera ya tenía el precedente escrito

Declarar `TOUCHES_INTEGRATED` en 4 ficheros hizo que `toolkit.py` **rechazara su
propio autotest entero** y se negara a validar las 68. Era una regresión mía.

Lo rápido era quitar el campo de esos 4 — y eso habría dejado la frontera sin
declarar justo en las herramientas que `run_all` ejecuta. `toolkit.py` ya tenía
`CONTRATO_FLAGS` para exactamente este caso, con el precedente escrito dos veces
en su cuerpo (`EXIT_ON_SUCCESS`, `WRITES_GPU`). Cuatro líneas:

```
autotest        AUTOTEST FALLA  ->  autotest OK
flags conocidos        8        ->  9
```

> reconocer un campo no es comprobarlo — y el propio fichero lo dice

Es el primer fichero de validación que modifica esta sesión, y sólo porque
medirlo lo volvió necesario: `1487` propuso la acción y dejó su coste sin medir.
**El coste medido es una línea de código.**

---

## `rxre_touch.py` — el campo que se declaraba y nadie leía

`1513` añadió `TOUCHES_INTEGRATED` al vocabulario y el propio `toolkit.py` dijo
*«reconocer un campo no es comprobarlo»*. Esto paga esa deuda.

La pregunta de diseño va antes del código: **¿el campo significa *escribir* o
*mencionar*?** AGENTS.md prohíbe **escribir**. Y el proyecto **lee** la iGPU a
propósito — `fingerprint.py` mide `_id_pci("card0")` porque ése es su trabajo.

> un verificador que confunde lectura con infracción no verifica: acusa

```
74 declaran TOUCHES_INTEGRATED
  VERIFICABLE_LIMPIO        61
  NO_DETERMINED             13    declaran `no` SIN RESPALDO (delegan)
  INFRACCION                 0
118 NO declaran el campo
```

**0 infracciones**: nadie escribe en `/sys`, en `/dev/dri`, llama a `ioctl`, ni
borra un nodo de la GPU. Lo que se afirma es **`NOT_FOUND` sobre el código
leído**, no `PROVEN_ABSENT`.

### Tres defectos reales, y el patrón que comparten

| defecto | cómo se vio |
|---|---|
| daba veredicto a las **118 que no declaraban** | vector que pedía `veredicto is None` |
| declaró `remove` como verbo y **nunca lo comprobó** | vector que enumeraba los verbos |
| `delega` contaba **`nom == "run"`**, no `subprocess.run` | **cruzar dos instrumentos** |

El tercero no salió de ningún vector: salió de cruzar `TOUCHES_INTEGRATED` con
`WRITES_FILES` y ver que 3 filas no cuadtaban. `campos_pm4.py`, `pm4dec.py` y
`sello.py` tienen **cero** llamadas a `subprocess` — `grep` de dos segundos.

> un nombre de método no dice quién lo define

Ahora el AST exige el receptor `subprocess`, y **el recuento se hace por dos
caminos**: AST (156) y regex que exige el prefijo (169), con los 28 métodos de
nombre coincidente explicando la diferencia en vez de esconderla.

### Y la coherencia cruzada — dentro del instrumento, no a mano

En `1515` ese cruce lo ejecuté con un script de shell, porque fue lo que
reveló que `campos_pm4.py`, `pm4dec.py` y `sello.py` declaraban
`WRITES_FILES=no` **y** `TOUCHES_INTEGRATED=no` sin respaldo. Eso era un
artefacto **no reproducible**: la evidencia dependía de que alguien reescribiera
el script.

Ahora la regla está dentro de `rxre_touch`:

```
WRITES_FILES == "no"  =>  el veredicto de la frontera NO puede ser NO_DETERMINED
```

192 filas cruzadas, **0 incoherencias**, y la regla dice **por qué** cero es lo
correcto.

> un campo no se verifica solo: se verifica contra otro campo que mide otra cosa

En `1515` ese cruce lo ejecuté con un script de shell, porque fue lo que
reveló que `campos_pm4.py`, `pm4dec.py` y `sello.py` declaraban
`WRITES_FILES=no` **y** `TOUCHES_INTEGRATED=no` sin respaldo. Eso era un
artefacto **no reproducible**: la evidencia dependía de que alguien reescribiera
el script.

Ahora la regla está dentro de `rxre_touch`:

```
WRITES_FILES == "no"  =>  el veredicto de la frontera NO puede ser NO_DETERMINED
```

192 filas cruzadas, **0 incoherencias**, y la regla dice **por qué** cero es lo
correcto.

### Hubo que romper el cruce a propósito para probarlo

Tres vectores, los tres PASS — y eso no decía nada.

| mutación | resultado |
|---|---|
| romper el **cálculo** (`coherente = True`) | 3 PASS — **ciego** |
| `mmap` cuenta como delegación | sin efecto: `mmap` es **0** en el árbol |
| **`borra_otro` cuenta como delegación** | **2 FAIL**, nombrando `trace_path.py` |

> un vector que lee el resultado de un cálculo no vigila el cálculo

La segunda falló porque **`mmap` es 0**: los datos estaban limpios, y un vector
que vigila una propiedad que nadie viola no se prueba así — hay que mutar algo
que **cree** la violación.

> un vector que vigila una propiedad que nadie viola no se prueba: se rompe

La tercera además reventó con `KeyError`, porque el motivo interpolaba
`vb["delega"]`. Eso es **ruido, no detección** — un fallo que revienta no es un
vector que falla.

### Y la integración con `toolkit.py` NO se hace, con el coste medido

Medí antes de hacerlo, que es lo que `1513` hizo mal:

- **coste**: `08-ARQUITECTURA/tools/` → `RXRE/tools/` son **4 niveles, ningún
  módulo común**: import por `sys.path` o ruta absoluta, acoplando dos árboles.
- **ganancia**: `toolkit.py` valida **68** ficheros; `rxre_touch` mide **192**.
- **decisión**: el proyecto **ya respondió** a esto en `toolkit_cross.py` — *«No
  se comprueba nada nuevo. Se CRUZAN lo que las seis ya saben»*.

Importar habría acoplado dos árboles para obtener una cobertura que el cruce ya
da, y más ancha. La razón queda en `por_que_no_se_importa`.

> la integración obvia no es la correcta cuando el proyecto ya escribió por qué no lo hace

---

## Los cinco están en un runner: `toolkit_cross.py`, sección 4

**Se invokan por ruta, no se importan** — y esa decisión se tomó antes de
escribir código, por la razón que el propio `toolkit_cross.py` ya tiene escrita:
*«No se comprueba nada nuevo. Se CRUZAN lo que las seis ya saben»*.

> dos módulos que comparten memoria no sirven para mutar uno al otro, que es
> justo lo que un cruce sirve

La primera ejecución dio **3 de 5**, no 5 de 5: yo había puesto
`EXIT_ON_SUCCESS=0` en la prosa, y la línea `# CONTRACT:` quedaba **fuera de la
cabecera de 4000 bytes** — el mismo recorte que leen `rxre_contracts` y el cruce.

> un campo escrito en prosa es un campo que no existe

### Y para probar que el cruce cruza hubo que romperlo dos veces

| mutación | ¿detectada? |
|---|---|
| vector de `rxre_deleg` cambiado a `True` | **no** — y no era mutación: eso lo hace *pasar* |
| `rc` calculado y **no comparado** (fallo real del cruce) | **no** |
| vector forzado a `False` | **sí**: `SELFTEST rc=1`, 4 de 5 |

La segunda fila es la importante: la primera versión **calculaba** el `rc` del
selftest y el veredicto salía sólo del contrato. El valor estaba ahí, evaluado, y
sin usar.

> un cruce que no mira el rc de lo que cruza, cruza el contrato

### El patrón por quinta vez

| | |
|---|---|
| `1507` | la columna `declarado` traducía `indeterminado` a `no` |
| `1515` | se daba veredicto a quien no declaró |
| `1515` | `remove` declarado y nunca comprobado |
| `1517` | un vector leía el resultado del cálculo que debía vigilar |
| `1519` | el cruce calculaba el `rc` y no lo comparaba |

Cinco, en cuatro instrumentos, y **ninguno falló**: todos salían verdes.

> un valor calculado y no comparado no es una medición: es un trabajo sin resultado

> la prueba de que un cruce funciona no es que dé verde: es que **dé rojo cuando debe**, con el nombre de quien lo tiene

### El patrón que los tres comparten

`1507` traducía `indeterminado` a `no`. Aquí se daba veredicto a quien no
declaró. Aquí `remove` estaba declarado y nunca comprobado.

No son tres bugs: es **la misma forma**. *Declarar algo y no comprobarlo sale
verde siempre*, porque no hay nada que pueda ponerse rojo. Y en los tres la
columna o el campo **parecía** hacer su trabajo.

Por eso la defensa no es «más vectores», sino **cruzar dos instrumentos que
miden cosas distintas y exigir que cuadren**.
