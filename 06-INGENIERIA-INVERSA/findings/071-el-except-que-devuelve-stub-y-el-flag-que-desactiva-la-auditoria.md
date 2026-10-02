# 071 · El `except` que devuelve un stub, el flag que desactiva la auditoría, y la referencia que no es un error

```
ID:           071
TIPO:        DEFECTO_DE_HERRAMIENTA + HALLAZGO
ALCANCE:     tools/artifacts.py, tools/frontier.py, 06-INGENIERIA-INVERSA/findings/
CERRADO_CON: por qué se sabe que ya no se repite
TOOL:        artifacts.py v1.0.0, selftest 14 vectores PASS
GPU:         INTACTA. Nada de esto tocó hardware.
CORRIGE_LA_POLITICA: no. PERO CORRIGE UNA AFIRMACIÓN MÍA ANTERIOR.
```

## RESUMEN

Construí `tools/artifacts.py` para generar los siete artefactos que `AGENTS.md`
§AUTOMATIZACIÓN DE DOCUMENTACIÓN exige y que no existían. Al hacerlo aparecieron
**cinco defectos encadenados, cuatro de ellos del mismo tipo**: un fallo que en
vez de error produce un resultado plausible. Es la quinta vez que esa clase
ocurre en este proyecto, y ya merece su propia regla.

Los cinco, con su medición:

| # | defecto | síntoma | por qué NO se vio |
|---|---|---|---|
| 1 | medición con `isfile()` relativo | «2745 referencias rotas de 5510», el 50% | el número era plausible |
| 2 | regex que no admite `/` | 157 «rotas» que eran colas de nombre | el número era plausible |
| 3 | clasificación por la palabra `selftest` | 24 de 25 herramientas `TOOL_VALIDATED` | el número era plausible |
| 4 | `except` que devuelve un stub | `OPEN-FRONTIERS.md` de 189 B, con tablas vacías | el fichero **existe** |
| 5 | `--solo-referencias` con `return 0` antes de auditar | 0 líneas impresas, rc=0, con 293 rotas | el código de salida era 0 |

Cinco de cinco. Ningunoilinizó: los cinco devolvieron algo que parecía un
resultado.

## 1 · LA MEDICIÓN FALSA QUE ABRIÓ TODO

`AGENTS.md` exige ocho artefactos. Siete no existían. Y `audit_citations.sh`
—que es lo que se ejecuta antes de cada hallazgo— **sólo comprueba citas AL
CORPUS**, nunca referencias a otro documento DEL PROYECTO.

Medí eso por primera vez así:

```python
existe = os.path.isfile(ref)                  # ← aquí está el fallo
```

`isfile()` con ruta relativa al directorio actual. Cualquier fichero que viviera
en un subdirectorio salía como inexistente:

```
referencias a .md del proyecto: 5510
inexistentes:                  2745   (50%)
```

**Cincuenta por ciento.** Escrito en `051` como resultado, y leído allí como
«la cadena de evidencia del proyecto está rota y la auditoría tiene un agujero
del tamaño de esa cadena».

Con el árbol indexado antes de decir que algo no existe:

```
referencias a .md del proyecto: 6356
resuelven contra el índice:     6063   (95%)
NO resuelven:                    293   (5%)
```

**Corrección de lo que afirmé en `051`, y es mía**: escribí que `056` citaba
`OPEN-FRONTIERS.md:38-43` *«como si existiera»* y que era *«una cita a un
fichero que no está»*. **Es falso: el fichero existe.** El error no fue el
regex, fue medir la ausencia con un método que no busca.

> **REGLA QUE ESTE CASO IMPONE**: *«no existe»* sólo es un dato si el índice
> sobre el que se searched está construido, y su tamaño se imprime junto al
> resultado. Un `not found` sin cota no es una medida: es un olvido. Y «50% de
> las referencias rotas» era la clase de cifra que hace que alguien actúe sobre
> un inventario equivocado durante semanas.

## 2 · EL REGEX QUE NO ADMITÍA SUBDIRECTOR

Corregido lo anterior, el segundo intento dio 157 «rotas» cuyos nombres eran
`3-B.md`, `E1E3.md`, `04-09.md`, `2026-09-24.md`: todos empiezan por dígito o
son la cola de un nombre más largo. El patrón era:

```
([A-Z0-9][A-Z0-9_-]{2,}(?:-[A-Z0-9_]+)*\.md)
```

No admitía `/`. `FASE-R4B-GOVERNOR/3-B.md` se capturaba como `3-B.md` — y como
`3-B.md` tampoco existía, salía rota.

**La corrección no fue «permitir `/`»**: fue indexar los nombres por dos vías
(nombre base y ruta relativa) y distinguir si la referencia casaba con la ruta
escrita o sólo con el nombre. De ahí salió la clase `RUTA_EQUIVOCADA`.

> Coincidencia parcial por subcadena: la quinta forma documentada, y la más
> silenciosa, porque la cola de un nombre es un nombre que existe.

## 3 · CLASIFICAR HERRAMIENTAS POR LA PALABRA «selftest»

`AGENTS.md` §AUTOMATIZACIÓN DE VALIDACIÓN exige clasificar cada herramienta como
`TOOL_VALIDATED` / `TOOL_PARTIAL` / `TOOL_UNVALIDATED` / `TOOL_BROKEN`. La
primera versión de `TOOLS-STATUS` decidía así:

```python
tiene_selftest = "selftest" in txt          # ← así, no
```

Resultado: **24 de 25 herramientas `TOOL_VALIDATED`**, incluida `artifacts.py`,
que no tiene selftest. Porque su propia prosa dice «ejecuta el selftest».

Es el defecto de las 466 macros y los 133 obsoletos, en forma de código:
**buscar la evidencia en el sitio donde se declara en vez de donde se
comprueba.** Se corrige ejecutando:

```python
r = subprocess.run([sys.executable, p, "--selftest"], timeout=120)
if r.returncode == 0:   TOOL_VALIDATED     # el selftest existe y PASA
elif r.returncode == 1: TOOL_BROKEN         # existe y FALLA
```

Que `TOOL_BROKEN` sea una clase propia importa: *«el selftest falla»* y *«no hay
selftest»* son información distinta, y colapsarlos hace que una herramienta rota
parezca recién made.

## 4 · EL `except` QUE DEVUELVE UN STUB — EL PEOR DE LOS CINCO

`gen_open_frontiers()` delegaba en `frontier.py` importando funciones internas.
Llamaba a dos que **no existen**:

```
F._init_clase_por_seccion()   # de la PRIMERA versión de frontier, que se reescribió
F.cargar()                     # se llama cargar_claims()
```

`AttributeError`. Y el manejador:

```python
except Exception as e:
    return ("# OPEN-FRONTIERS\n\n%s\n\nfrontier.py no ejecutable: %s\n" % (SELLADO, e))
```

`OPEN-FRONTIERS.md` se escribió con **189 bytes**: título, marca de generado, y
la frase del error. Las dos tablas, vacías.

> **Éste es el peor modo de fallo posible, y es el que este proyecto lleva
> cinco hallazgos prohibiendo**: *devolver algo plausible en vez de fallar*.
> Un artefacto de 189 bytes no obliga a mirar. Un artefacto ausente obliga.

Lo que lo hace peor es que **escribí un guardia para cazarlo y no cazaba**:

```python
if len(filas) < 5:
    out += ["> AVISO: %d documentos..."]
```

El guardia está *después* del `return` del `except`. El camino que debía cubrir
no lo cubría. Peor que no escribirlo, porque da la sensación de estar
cubierto.

**Tres cambios, en este orden:**

1. La delegación pasa a ser por **salida**: `frontier.py --json`, no
   funciones internas. Un interno que se renombra deja de existir en el
   llamador en silencio; un `--json` con contrato estable es lo que se puede
   auditar. Motivo además de robustez: si `artifacts.py` reimplementara la
   clasificación, habría dos recuentos del mismo conjunto divergiendo sin que
   nadie lo note.
2. **Cualquier fallo al generar lanza**, y `main()` no escribe nada: un
   artefacto a medias es un fichero que existe y no dice nada.
3. El guardia deja de existir, porque el camino que vigilaba ya no existe. Un
   guardia sobre código muerto es otro guardia que no cubre nada.

`OPEN-FRONTIERS.md` pasó de **189 B a 22 353 B** con la tabla de 243 huecos.

## 5 · EL FLAG QUE DESACTIVABA LA AUDITORÍA

`--solo-referencias` significa «sólo audita referencias». Su implementación:

```python
if not args.solo_referencias:
    ... generar artefactos ...

if args.solo_referencias:
    return 0                      # ← aquí

print("AUDITORIA DE REFERENCIAS INTERNAS")
```

El flag saltaba la auditoría y salía con **código 0**. Con 293 referencias
rotas en el proyecto. Cero líneas por stdout, cero por stderr.

Y `return 1 if n_rota else 0` estaba debajo, así que el código de salida
dependía del recuento… que nunca se calculaba.

Corregido. `rc=1`, 293 `ROTA`.

**El primer intento de vectorizar este defecto falló él mismo**, y es
informativo: el selector hacía

```python
cuerpo = src.split("solo_referencias")[-1]
```

y se troceaba con el **comentario** que menciona el flag, leía el `return` de
su propia prosa y se declaraba `FAIL` a sí mismo. Se cambió a inspección por
sangría sobre código sin comentarios: se busca un `return` a nivel de `main`
antes del bloque de auditoría.

> Un selector que se alarma de su propio comentario no selecciona el código.
> Es la versión textual de la coincidencia parcial.

## 6 · LA REFERENCIA ROTA QUE NO ERA UN ERROR

Quedaba **una** referencia rota en los findings, y era la que parecía la única
defensa de `021`:

```
021-write-lock-scoped-subdir-does-not-block.md:154  ->  022-pte-productor-sdma-gfx8.md
```

El fichero no existe. Pero `021` **cuenta una colisión de índice**: las dos
sesiones escribieron `022-` y una renombró la suya a `023-pte-productor-sdma-gfx8.md`.
La referencia no es un typo: es un nombre que existió.

Corregirla a `023-` haría que `021` contara una colisión entre dos ficheros
`022` cuando uno jamás tuvo ese nombre. **Se arreglaría la referencia
rompiéndola.**

Y junto a ella, cuatro en `051`: `CLAUDE.md`, `docs/config.md`, `docs/rules.md`,
`DESIGN.md`. Son **citas de nombres inexistentes usadas como ejemplo** de lo que
no existe. Citar un nombre roto convierte la cita en referencia rota; ningún
auditor puede distinguir «mire esto» de «menciono esto».

Por eso hay `tools/REF-EXCEPTIONS.txt`, y por eso el auditor tiene **tres**
clases y no dos:

```
ROTA               el fichero no existe y no hay razón       -> 293
ROTA_HISTORICA     no existe, y hay razón escrita             ->   6
RUTA_EQUIVOCADA    existe, pero no donde dice el texto        -> 3206
```

`RUTA_EQUIVOCADA` es casi toda la **convención** del proyecto: los findings se
citan por nombre desnudo y viven en un subdirectorio. Marcarlo como defecto
daba 3206 falsos positivos y enterraba los 293 reales.

> `RUTA_EQUIVOCADA` revela otra vez: `SGX` existe en `SOC15D_SGX`, pero no es
> el mismo símbolo. Un prefixo de espacio de nombres sí; una calificación no.

**Cierre real, medido:**

```
ROTA en 06-INGENIERIA-INVERSA/findings:  0
```

La cadena de evidencia del proyecto está limpia. La auditoría que la custodia
tenía un agujero del tamaño de esa cadena, y ese agujero era lo que había que
cerrar, no ocho ficheros nuevos.

## 7 · ERRORES PROPIOS EN ESTA MISMA ITERACIÓN

| error | cómo se detectó |
|---|---|
| `Contiene_componentes` **definida dos veces** en `frontier.py` (255 y 398), idénticas | `gen_open_frontiers` llamó una función inexistente; al arreglarlo apareció el duplicado. La segunda tapaba a la primera: comportamiento correcto por casualidad, y cualquier edición futura a una no habría surtido efecto |
| `contiene_componentes` en mi versión **esperaba que `c/subdir.md` no resolviera**, cuando el resolutor cae al nombre base y sí resuelve | vector de selftest `FAIL` |
| `SELECT * FROM`-style: `[...] or [...]` con `*` delante → `SyntaxError` | `ast.parse` |
| indentación rota al pegar el bloque de `principales` | `ast.parse` |
| firma de `Indice.resuelve` cambiada a tupla, `IndFalso` del selftest no actualizada → `ValueError` | ejecución del selftest |
| las 6 líneas de `REF-EXCEPTIONS.txt` escritas **con `#` delante**, que es justo lo que el parser descarta | `ROTA_HISTORICA: 0 (0 excepciones)` con las 6 visibles en el informe |
| `l[3:4].isdigit()` para quitar el `#`, con la línea `#   021-…`: índice equivocado |el mismo sintoma, 0 desbloqueadas |

Nótese el patrón: **casi todos los errores se detectaron porque una cifra no
cuadraba con lo que el informe prometía.** `ROTA_HISTORICA: 0 (0 excepciones)`
mientras el fichero tenía 6 líneas. Ésa es la razón por la que los contadores
se imprimen con su cota.

## 8 · REGLA

> **Cuando una ruta de código pueda fallar, el fallo tiene que ser ruidoso y el
>artefacto tiene que estar AUSENTE.**
>
> Tres reglas concretas, todas nacidas de los cinco casos:
>
> 1. **Un `except` que devuelve un valor es un `except` que oculta un fallo.**
>    Si hay que distinguir «no aplica» de «no pude calcularlo», que devuelva el
>    segundo, o que lance.
> 2. **Toda referencia entre herramientas va por salida estable (`--json`), no
>    por función importada.** Un interno que se renombra desaparece en
>    silencio; un contrato de salida se puede auditar con `grep`.
> 3. **Un guardia no cuenta si no cubre el camino que dice cubrir.** Comprobar
>    que el guardia está *alcanzable* es parte de escribirlo.

## 9 · LO QUE ESTO CIERRA Y LO QUE NO

**Cierra:**
- Los 7 artefactos de `AGENTS.md` que faltaban, generados por herramienta y
  marcados como generados (un artefacto editado a mano se desincroniza en la
  siguiente ejecución sin que haya forma de saber cuál de las dos cosas es).
- La auditoría de referencias internas, que `audit_citations.sh` no hacía.
- El duplicado de `contiene_componentes` en `frontier.py`.
- `frontier.py` sigue con sus 12 vectores PASS tras quitar 46 líneas muertas.

**No cierra, y sigue abierto:**
- **293 `ROTA` fuera de `findings/`**, en `01-AUDITORIA` (112), `02-ARQUITECTURA`
  (81), `00-INDICE` (76). No se corrigen: buscar el destino por parecido de
  nombre sería inventar a qué documento quería referirse el autor.
- **`CLAUDE.md`, `docs/config.md`, `docs/rules.md`, `DESIGN.md`**: documentos de
  configuración citados por todo el proyecto y ausentes del árbol.
- **`CONTRADICTIONS.md` tiene 15 aristas y `KNOWLEDGE-GRAPH.md` 8** — conjuntos
  pequeños y reales, pero cuya completitud depende de que las cabeceras usen las
  eight etiquetas que se leen. No hay verificación de que esas etiquetas sean las
  que se usan; hay `RETRACTED_BY`, `CORRECTED_BY`, `CERRADO_POR`, `CORRIGE_LA_POLITICA`,
  `MEDIDO_EN_MI_ASIC_POR`… y no se comprobó si hay más.

---

```
RESULTADO DE ITERACIÓN

Entregado:
  tools/artifacts.py v1.0.0, selftest 14/14 PASS
  tools/REF-EXCEPTIONS.txt, 6 excepciones con razón
  7 artefactos generados: EVIDENCE-MATRIX (13.8 kB), CURRENT-STATE,
    KNOWLEDGE-GRAPH, OPEN-FRONTIERS (22.4 kB), NEGATIVE-RESULTS,
    CONTRADICTIONS, TOOLS-STATUS
  Auditoría de referencias internas: 6374 examinadas,
    293 ROTA / 6 ROTA_HISTORICA / 3206 RUTA_EQUIVOCADA,
    0 ROTA en 06-INGENIERIA-INVERSA/findings/

Corregido:
  021:154 re-etiquetado ROTA_HISTORICA (no era un error)
  051: afirmación retractada sobre OPEN-FRONTIERS.md
  frontier.py: duplicado de contiene_componentes eliminado (46 líneas)
  artifacts.py: --solo-referencias ya no salta la auditoría

Retractado:
  «2745 de 5510 referencias internas rotas (50%)» — era 293, por isfile() relativo
  «056 cita OPEN-FRONTIERS.md como si no existiera» — el fichero existe

NEXT ACTION:
  Verificar qué etiquetas de relación usan REALMENTE las cabeceras de los
  findings, contra la lista cerrada queKNOWLEDGE-GRAPH y CONTRADICTIONS
  asumen. Es el mismo patrón que este hallazgo por el otro lado: una
  herramienta que cuenta con una lista de etiquetas escrita a mano no sabe
  si esa lista está completa, y produce un recuento plausible.
  Es UN-GREP, pero del conjunto de valores distintos que aparecen, no de
  los que la herramienta ya conoce.
```