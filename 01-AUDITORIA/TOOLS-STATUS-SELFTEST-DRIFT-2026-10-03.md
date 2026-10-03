# TOOLS-STATUS-SELFTEST-DRIFT — 2026-10-03

NODE: `NODE-2026-10-03-01-TOOLSTATUS-DRIFT`
AGENT: AGENT-03 (rol semantica Polaris12/GFX8), sesion `sesion-d3`
WORK_CLASS: READ_ONLY sobre herramientas. No se toco hardware, ni
`tools/govcheck.py`, ni `tools/integridad.py`, ni ningun artefacto generado.

---

## 0. CONVENCION DE NOMBRES: cual use y por que

`01-AUDITORIA/` contiene dos formatos dominantes:

- informes: `<TEMA>-<YYYY-MM-DD>.<ext>` (p.ej. `R1-ACTORS-INVENTORY-2026-09-26.md`,
  `MIG-07.6-ADVERSARIAL-REVIEW-20260926T042000Z.md`, `HOST-C-DIAGNOSTIC-RECONCILIATION/`)
- capturas crudas: `<TEMA>-<YYYY-MM-DD>.raw-<tipo>.txt`

Y ya existe el precedente exacto de este trabajo:
`01-AUDITORIA/TOOLS-STATUS-AUTHORITY-AUDIT-2026-10-03.raw-capture.txt` y
`.raw-scope-probe.txt` (mtime 2026-10-03 13:56:19 -0300).

USE ESA CONVENCION:

```
01-AUDITORIA/TOOLS-STATUS-SELFTEST-DRIFT-2026-10-03.md                 (este informe)
01-AUDITORIA/TOOLS-STATUS-SELFTEST-DRIFT-2026-10-03.raw-capture.txt    (6 ejecuciones)
01-AUDITORIA/TOOLS-STATUS-SELFTEST-DRIFT-2026-10-03.raw-flagclass.txt  (8 ejecuciones)
```

Por que `01-AUDITORIA/` y no otro sitio: la auditoria de autoridad de
`TOOLS-STATUS.md` ya vive ahi, este nodo no produce un hallazgo de hardware
(eso es `06-INGENIERIA-INVERSA/findings/`) ni un experimento con la GPU
(eso es `03-EXPERIMENTOS/`), y abrir un arbol nuevo violaria §91.

---

## 1. PREGUNTA CAUSAL PRIMARIA

> El veredicto `TOOL_BROKEN` de `TOOLS-STATUS.md` para `integridad.py` (y el de
> `govcheck.py`) se refiere al fichero que esta ahora en disco? Y por que
> fallan sus selftests?

## 2. HIPOTESIS, ORDENADAS ANTES DE EJECUTAR

| id | hipotesis | apoyo inicial |
|---|---|---|
| H1 | ARTEFACTO DESFASADO: el veredicto se emitio contra otra version del fichero | `integridad.py` en disco difiere del registrado |
| H2 | EL SELFTEST FALLA DE VERDAD: la causa esta en el tool o en su entorno de ejecucion | ninguna, todavia |
| H3 | (añadida por analisis ESTATICO antes de ejecutar, §49) DESAJUSTE DE CONTRATO: el flag que pasa el runner no es el flag que la herramienta reconoce, y el `rc` que se lee pertenece a otro camino de codigo | `artifacts.py:741-742` pasa `--selftest`; `integridad.py:524` reconoce `--self-test` |

**DISCRIMINANTE UNICO (ejecutado, §4):** reejecutar ambos selftests y comparar
la clasificacion obtenida contra la registrada.

- Si `integridad.py` pasa → H1 sobrevive y el veredicto registrado es obsoleto.
- Si sigue fallando → H2 sobrevive y hay que clasificar el modo de fallo.

La lectura estatica de los dos puntos de entrada (hecha ANTES de ejecutar, y por
eso registrada aqui) ya hacia presagiar H3. Se ejecuto igualmente el
discriminante completo, porque el encargo obliga a no emitir veredicto sin
exit code ni hash del momento de ejecucion.

---

## 3. ESTADO DE PARTIDA, MEDIDO

Fuente: `sha256sum` y `wc -l` sobre el arbol, en este workspace, no el informe.

```
2026-10-03T14:11:15-03:00   lineas=882   tools/govcheck.py     882  959bf46be6125e9870ee548314e859cfd9d1fd4fc54df4a5a9a7927682cfce80
2026-10-03T14:11:15-03:00   lineas=555   tools/integridad.py   555  170590c79ad845c36bfc68518abaab3d075d03592bb2678d113b83c5c1c43726
```

(La cifra de govcheck es 882 con `wc -l` y 883 con `splitlines()`, porque
el fichero no termina en newline. `TOOLS-STATUS.md:44` registra 883, que es el
`splitlines()`. No es una discrepancia de contenido: es un criterio de conteo
distinto, medido en `artifacts.py:764` (`len(txt.splitlines())`).)

Comparado con lo que registra `TOOLS-STATUS.md` (generado 2026-10-03 09:31:19 -0300):

| herramienta | artefacto | disco (sha256[:16] / lineas splitlines) | veredicto de coincidencia |
|---|---|---|---|
| `govcheck.py` | `959bf46be6125e98` / 883 | `959bf46be6125e98` / 883 | **COINCIDE** |
| `integridad.py` | `088174d738654a0e` / 493 | `170590c79ad845c3` / 555 | **NO COINCIDE — deriva** |

Ambos ficheros estan **untracked** en git (`git status --porcelain` -> `??`), asi
que **no hay historial del que recuperar la version `088174d738654a0e`**. Ver
§6 FALTANTE.

---

## 4. EJECUCIONES — EL DISCRIMINANTE

Fuente de los exit codes: leidos del shell, `EXIT_CODE=` en la captura cruda.
Volcada completo, con timestamp y hash por ejecucion, en
`01-AUDITORIA/TOOLS-STATUS-SELFTEST-DRIFT-2026-10-03.raw-capture.txt`
(sha256 `4c065257fcc4020955a4ba5cd4132e2158098470665eb0941bfca2e664bf98ec`,
14978 bytes, 222 lineas, 6 registros `EXIT_CODE=`; verificado no vacio ANTES de
consumirlo).

### 4.1 `govcheck.py` — el runner SI le pasa el flag correcto

Punto de entrada: `tools/govcheck.py:728` `ap.add_argument("--selftest")`,
`tools/govcheck.py:730-731` `if a.selftest: return selftest()`. **Verificado por
lectura.** Es argparse, asi que el flag existe.

| # | ts_utc | comando | EXIT_CODE | stdout |
|---|---|---|---|---|
| A1 | 2026-10-03T17:15:xx Z | `python3 tools/govcheck.py --selftest` | **1** | 1795 B |
| A2 | 2026-10-03T17:15:xx Z | `python3 tools/govcheck.py --selftest` | **1** | 1795 B |
| R1 | 2026-10-03T17:25:23Z | `python3 tools/govcheck.py --selftest` | **1** | identico |
| R2 | 2026-10-03T17:25:30Z | `python3 tools/govcheck.py --selftest` | **1** | identico |

Salida identica byte a byte entre ejecuciones:
`sha256(govcheck.A1.out) = sha256(govcheck.A2.out) = d831f833ae0cf74265455e0e53fb361bc1756e0191f9fae6272b56822613eb3b`.
**Rango intra-run = 0. Determinista.**

Las ejecuciones R1/R2 son mias. Las ejecuciones del coordinador de las
16:48:21Z / 16:48:21Z (2026-10-03) estan en
`01-AUDITORIA/TOOLS-STATUS-AUTHORITY-AUDIT-2026-10-03.raw-capture.txt` y dan
**EXIT_CODE=1** con el mismo `RESULT: FAIL (24 comprobaciones)`. **Cuatro
ejecuciones independientes, mismo resultado.** No es ruido.

Resultado: **23 OK, 1 FAIL**:

```
  FAIL una proposicion con terminos del vigente se resuelve EN_VIGENTE
  RESULT: FAIL (24 comprobaciones)
```

### 4.2 `integridad.py` — aqui el flag NO es el que la herramienta reconoce

Punto de entrada: `tools/integridad.py:519-525` (parsing manual de argv).
**Verificado por lectura:**

```python
def main(argv):
    a = argv[1:]
    ...
    if "--self-test" in a:        # <--integridad.py:524  SOLO "--self-test"
        r = self_test()
```

El runner, en cambio, pasa `--selftest` sin guion interior
(`tools/artifacts.py:741-742`, literal leido):

```python
cmd = ([sys.executable, p, "--selftest"] if f.endswith(".py")
       else [p, "--selftest"])
```

| # | ts_utc | comando | EXIT_CODE | que se ejecuto de verdad |
|---|---|---|---|---|
| A3 | 2026-10-03T17:15:xx Z | `python3 tools/integridad.py --selftest` | **1** | la AUDITORIA de `findings/`, no el selftest |
| A4 | 2026-10-03T17:15:xx Z | `python3 tools/integridad.py --selftest` | **1** | identico (1594 B, sha `4ef25586...`) |
| A5 | 2026-10-03T17:15:xx Z | `python3 tools/integridad.py --self-test` | **0** | el SELFTEST: `---> 27 casos, 0 fallos` |
| A6 | 2026-10-03T17:15:xx Z | `python3 tools/integridad.py --self-test` | **0** | identico salvo el nombre del temporal |
| R3 | 2026-10-03T17:25:37Z | `python3 tools/integridad.py --selftest` | **1** | la AUDITORIA |
| R4 | 2026-10-03T17:25:37Z | `python3 tools/integridad.py --selftest` | **1** | la AUDITORIA |
| R5 | 2026-10-03T17:25:37Z | `python3 tools/integridad.py --self-test` | **0** | el SELFTEST |
| R6 | 2026-10-03T17:25:37Z | `python3 tools/integridad.py --self-test` | **0** | el SELFTEST |

Las dos ultimas lineas de stdout, que son las que distinguen los dos caminos:

```
--selftest  ->  "    ---> FALLA: DUPLICADOS 1, CONTAMINADOS 6"      (rc=1)
--self-test ->  "    ---> 27 casos, 0 fallos"                        (rc=0)
```

Determinismo: `--selftest` byte-identico entre las 2+2 ejecuciones
(`4ef25586...` 4 veces). `--self-test` difiere en **una sola linea** y solo en el
nombre del temporal aleatorio (`/tmp/integridad_v7vsimo2` vs
`/tmp/integridad_m8zwgdql`); el recuento `27 casos, 0 fallos` es identico.
**Rango intra-run = 0 en el resultado, ruido cosmetico en el path del temporal.**

Las ejecuciones del coordinador de las 16:48:21Z dan lo mismo: `--selftest`
EXIT_CODE=1 (1594 B) y `--self-test` EXIT_CODE=0 (2613 B, `27 casos, 0 fallos`).
**Seis ejecuciones por flag. Todas iguales.**

### 4.3 Que Clasificacion produce HOY cada fichero, con el mapeo del runner

Mapeo leido en `tools/artifacts.py:744-751`:

```
rc == 0            -> TOOL_VALIDATED,   detalle "selftest pasa"
rc == 1            -> TOOL_BROKEN,       detalle "el selftest FALLA"
rc otro            -> TOOL_UNVALIDATED,  detalle "selftest no soportado (rc=%d)"
TimeoutExpired     -> TOOL_PARTIAL,      detalle "el selftest expira"
```

| fichero | rc con el flag que pasa el runner | clasificacion que produziria HOY | detalle que escribiria | ¿describe lo que ocurrio? |
|---|---|---|---|---|
| `govcheck.py` | 1 | `TOOL_BROKEN` | `el selftest FALLA` | **SI** — el selftest corrio y fallo |
| `integridad.py` | 1 | `TOOL_BROKEN` | `el selftest FALLA` | **NO** — el selftest NO corrio; el rc es de la auditoria |

La ultima fila es el hallazgo: **`TOOL_BROKEN` para `integridad.py` es una
atribucion falsa, construida con un exit code de un camino de codigo que no es
el selftest.**

### 4.4 Poder de deteccion del selftest de `integridad.py`: DEMOSTRADO

Regla del nodo: si se afirma que el selftest DETECTA un fallo, hay que
reinsertar el defecto, ejecutar, registrar el numero y revertir.

Hecho sobre una **COPIA en `/tmp`**. `tools/integridad.py` no se toco: hash
identico antes y despues, verificado en la propia sonda.

| inyeccion | EXIT_CODE | salida |
|---|---|---|
| control: copia intacta | **0** | `---> 27 casos, 0 fallos` |
| `CASOS_SELFTEST_MINIMO = 999` (`integridad.py:333`) | **1** | `FALLO SELF_TEST_MUST_EXCEED_FIXTURE  solo 26 casos, minimo 999` y `---> 27 casos, 1 fallos` |
| nombre de funcion alterado | **1** | `Traceback ...` en stderr (ejercita la via de excepcion, no una asercion) |

`sha256(tools/integridad.py) = 170590c79ad845c3...` antes y despues: identico.
Copia de trabajo eliminada al terminar. **"revertir" = no habia nada que
revertir en el repositorio.**

Conclusion: el selftest de `integridad.py` **existe, corre y detecta**.
Capacidad de deteccion: **DEMOSTRADA**, no supuesta.

---

## 5. MODO DE FALLO DE `govcheck.py`: NO es un bug del extractor

El vector que falla es `tools/govcheck.py:677-682`:

```python
v1 = donde_esta(RAIZ, "AGENTS.md: sin evidencia sin unidad, y el registro "
                      "lleva su sello de tiempo", cs)
vec("una proposicion con terminos del vigente se resuelve EN_VIGENTE",
    v1["estado"] == "EN_VIGENTE")
```

Medido, no inferido (sonda `/tmp/opencode/medida_govcheck_RAIZ.py`, que importa
`govcheck` y llama `donde_esta`; no modifica el modulo):

```
RAIZ = .../03-GPU-SEMANTICS     (AGENTS.md de disco)
   v1 -> NO_DECIDIBLE   decide=None      el selftest exige EN_VIGENTE
   v2 -> NO_DECIDIBLE   decide=None      el selftest exige != NO_ENCONTRADA

RAIZ = /tmp/opencode/RAIZ-HEAD  (AGENTS.md = `git show HEAD:AGENTS.md`)
   v1 -> EN_VIGENTE     decide=evidencia          <-- el vector pasaria
   v2 -> EN_VIGENTE     decide=tool_unvalidated    <-- el vector pasaria
```

El mismo `cs` (66 citas de codigo) en los dos casos, porque el selftest tambien
lo usa. Lo unico que cambia es el documento.

Y el documento:

| documento | lineas | bytes | `sin evidencia sin unidad` | `TOOL_UNVALIDATED` | mtime |
|---|---|---|---|---|---|
| `AGENTS.md` de disco | 31 | 466 | 0 ocurrencias | 0 ocurrencias | 2026-10-03 13:16:24 -0300 |
| `AGENTS.md` en `HEAD` (git) | 1060 | 30295 | 0 ocurrencias | 2 ocurrencias | — |

La proposicion que el vector exige encontrar **no esta en ninguna de las 6
versiones de `AGENTS.md` del repositorio** (`6fb9113 0`, `daec702 0`,
`1bb4115 0`, `4a437ac 0`, `6fe40b2 0`, `54b3ea8 0`; fuente: `git log --format=%h
-- AGENTS.md` + `git show <c>:AGENTS.md | grep -c`).

Conclusion, con la fuente de cada cifra nombrada:

- `govcheck.py` esta clasificado `TOOL_BROKEN` de forma **REAL y reproducible**:
  el hash coincide con el artefacto y el fallo se reproduce en 4 ejecuciones
  deterministas. **H1 queda REFUTADA para este fichero.**
- La causa **no es un defecto del extractor**: con el documento versionado, el
  mismo `donde_esta` devuelve `EN_VIGENTE` con el termino que decide (`evidencia`).
  Es `ENVIRONMENT_FAILURE`: **el selftest tiene un fixture acoplado al documento
  vivo**, y el documento vivo de este workspace es un descriptor de rol de 31
  lineas en lugar del documento de gobernanza de 1060.
- H2 sobrevive para `govcheck.py` en el sentido de "algo falla de verdad", pero
  **la causa esta en el entorno, no en el tool**. Lo digo asi porque el
  encargo pedia exactamente esa distincion.

---

## 6. H1 / H2 / H3 — RESULTADO

| hipotesis | veredicto | observacion que la discrimina |
|---|---|---|
| H1 artefacto desfasado | **PARCIAL**: vive para `integridad.py`, **refutada** para `govcheck.py` | `integridad.py` en disco `170590c7` vs `088174d7` registrado; `govcheck.py` en disco `959bf46b` = registrado |
| H2 el selftest falla de verdad | **REFUTADA para `integridad.py`**; **CONFIRMADA con causa ENVIRONMENT para `govcheck.py`** | `integridad.py --self-test` -> EXIT 0, `27 casos, 0 fallos`, 6 ejecuciones; `govcheck.py --selftest` -> EXIT 1, 23/24 OK, 4 ejecuciones |
| H3 desajuste de contrato del flag | **CONFIRMADA, y es la que discrimina `integridad.py`** | `artifacts.py:741` pasa `--selftest`; `integridad.py:524` reconoce `--self-test`; con `--selftest` la salida es la de la auditoria (`DUPLICADOS 1, CONTAMINADOS 6`), no la del selftest (`27 casos, 0 fallos`) |

**La respuesta a la pregunta primaria, en una linea:** el veredicto de
`govcheck.py` si se refiere al fichero en disco y es real (pero por causa del
entorno); el veredicto de `integridad.py` **no es utilizable** —ni por obsolescencia
ni por fallo del selftest: su selftest pasa, y el `TOOL_BROKEN` se fabrico con el
exit code de otro camino de codigo.

**Alcance del defecto de clase, MEDIDO** (volcado en
`01-AUDITORIA/TOOLS-STATUS-SELFTEST-DRIFT-2026-10-03.raw-flagclass.txt`, sha256
`7cfa20e7dd67c9813b71b38318b874d89492c9638e42b5b9586123c3788a7602`, 2548 B):

| herramienta | `--selftest` | `--self-test` | veredicto que daria el runner |
|---|---|---|---|
| `integridad.py` | 1 | **0** | `TOOL_BROKEN` **FALSO** |
| `atom_chain.py` | 2 | 2 (exige `--self-test <f>`) | `TOOL_UNVALIDATED` (correcto, por rc) |
| `citas.py` | timeout 25 s | timeout 25 s | `TOOL_PARTIAL` (el runner usa 120 s) |
| `toolreg.py` | **0** | 2 (argparse lo rechaza) | `TOOL_VALIDATED` (correcto) |

`integridad.py` es la unica de esta clase cuyo flag desconocido cae en un camino
que devuelve exactamente **1**, que es el rc que el runner traduce a
`"el selftest FALLA"`. Por eso es la unica que produce un veredicto falso en vez
de un `TOOL_UNVALIDATED` inofensivo.

Aviso de metodo: un `grep` de los literales afirmaba que `toolreg.py` acepta
ambos flags. **Es falso**: medido, `toolreg.py --self-test` -> EXIT 2,
`unrecognized arguments`. Por coherencia con §16 del proyecto, la presencia de
una palabra no es evidencia; lo que cuenta es la ejecucion.

---

## 7. HALLAZGO COLATERAL: la columna `selftest` no es evidencia

`tools/artifacts.py:781-783` escribe la columna asi:

```python
"| `%s%s` | %d | %s | `%s` | `%s` |"
% (..., "si" if x["st"] else "NO", ...)
```

`x["st"]` es `detalle`, y `detalle` es **una cadena no vacia SIEMPRE**, con
incluido el valor inicial `"sin selftest"` (`artifacts.py:735-736`). La condicion
no puede ser falsa. **La columna `selftest` dice `si` en las 70 filas.**

Consecuencia observada: `TOOLS-STATUS.md:21` declara `atom_chain.py` con
selftest `si`, y medido, esa herramienta **no tiene un selftest invocable por el
runner**: `atom_chain.py` acepta `--self-test <fichero>` y sin argumento devuelve
`uso:` con rc=2. Es el mismo `NOT_FOUND -> PROVEN_ABSENT` que el propio
`artifacts.py:725-730` dice querer evitar.

Este hallazgo es colateral: no es la pregunta primaria, pero comparte raiz con
ella (contrato de invocacion no declarado) y afecta a la misma columna que decide
que herramienta cierra una afirmacion critica.

---

## 8. FALTANTE

1. **Que flag aceptaba la version `088174d738654a0e` de `integridad.py`:
   `NOT_DETERMINED`.** El fichero no esta en el arbol y `tools/integridad.py`
   esta untracked, asi que no hay historial. **No puedo afirmar** que la version
   de 493 lineas aceptase `--selftest`, y por tanto **no puedo fechar** cuando
   aparecio el desajuste. Si el coordinador tiene el volcado de la generacion del
   2026-10-03 09:31:19 o un snapshot, esto se cierra en un minuto.
2. **Modo de fallo de `govcheck.py`: acotado, NO cerrado.** No he ejecutado el
   selftest **completo** de `govcheck` con el `AGENTS.md` versionado sustituido:
   `citas_de_codigo(RAIZ)` tambien lee el arbol, y una raiz replicada en `/tmp`
   cambiaria el conjunto de citas y, con el, el resultado de otros vectores. Lo
   medido es el vector que falla, aislado, con el mismo `cs` de 66 citas. Que el
   selftest completo pasaria con el documento correcto es
   `PROVEN_DERIVED`, no `OBSERVED`.
3. **No he regenerado `TOOLS-STATUS.md` ni ningun artefacto generado.** Es
   decision del coordinador y ademas invalidaria la fila bajo auditoria. Mi
   afirmacion sobre lo que el runner escribiria hoy es `PROVEN_DERIVED` de
   (exit code medido) x (mapeo leido).
4. **No he verificado las otras 68 filas** de la tabla. La columna `estado` solo
   esta verificada para 2 de 70 herramientas.

## 9. LO QUE NO ESTOY AFIRMANDO

- No afirmo que `integridad.py` sea una herramienta correcta. Afirmo, y esta
  medido, que **su selftest pasa** y que tiene poder de deteccion demostrado.
  Que la herramienta acierte al auditar la banda 900+ es otra pregunta, y su
  salida dice que encuentra 1 duplicado y 6 contaminados: eso es un resultado
  sobre hallazgos, fuera del alcance de este nodo.
- No afirmo quien sustituyo el `AGENTS.md` de 1060 lineas por el de 31. Solo que
  hoy son ficheros distintos (`git status` -> ` M AGENTS.md`, mtime
  2026-10-03 13:16:24, anterior a mi sesion).
- No afirmo nada sobre hardware. Este nodo no ha tocado la GPU.

## 10. FALSIFICACION: que observacion refutaria cada afirmacion

| afirmacion | refutada por |
|---|---|
| `integridad.py --self-test` -> 0 / `27 casos, 0 fallos` | una ejecucion con otro `sha256` que devuelva != 0, o una lectura de `integridad.py:519-531` mostrando que `--selftest` entra en `self_test()` |
| el `TOOL_BROKEN` de `integridad.py` es hoy una atribucion falsa | una lectura de `artifacts.py:744-751` que no mapee `rc==1` a `TOOL_BROKEN`, o un `rc != 1` de `integridad.py --selftest` |
| `govcheck.py` falla por entorno, no por el extractor | `v1` devolviendo `EN_VIGENTE` con el `AGENTS.md` de disco, o `donde_esta` que no lea `AGENTS.md` |
| el veredicto de `integridad.py` se emitio contra otra version | una copia de `integridad.py` con `sha256 = 088174d738654a0e...` y 493 lineas en cualquier sitio accesible |
| la columna `selftest` dice siempre `si` | `artifacts.py:781-783` con una condicion que pueda ser falsa para alguna fila |

## 11. ACCION DISCRIMINANTE PROPUESTA — NO APLICADA

Este nodo es diagnostico. Lo que nombro, sin tocarlo:

1. **El arreglo NO es tocar `integridad.py`.** Es que `artifacts.py` **no puede
   escribir "el selftest FALLA" a partir de un `rc` cuyo origen no conoce.** El
   `rc=1` de `integridad.py --selftest` es el veredicto de una auditoria de
   ficheros, no de un selftest. Arreglo minimo: que el runner distinga
   "el flag no esta soportado" de "el flag se ejecuto y fallo" — por ejemplo
   pasando `--selftest` **y** `--self-test`, o exigiendo que la herramienta
   responda a un flag de identidad antes de atribuir otro codigo de salida. Sin
   eso, la columna puede volver a fabricar un `TOOL_BROKEN` falso en cualquier
   herramienta que tenga un camino principal que devuelva 1.
2. **Un contrato de invocacion unico y declarado** (que flag, que argumentos, que
   significa cada `rc`). Hoy no existe, y su ausencia es la raiz comun de §6 y §7.
3. **`govcheck.py`**: los vectores `v1`/`v2` no deben depender del documento vivo
   sin decirlo. O son un test de entorno y se declaran como tales, o se
   convierten en un fixture en `/tmp`. Lo que no puede ser es un selftest cuya
   mitad de la autoridad depende de que un `AGENTS.md` de otro workspace diga
   una frase.
4. **Regenerar `TOOLS-STATUS.md` con la herramienta** (no a mano) despues de 1,
   y hasta entonces **no citar la fila `integridad.py ... TOOL_BROKEN` como
   evidencia de nada.**

## 12. INTEGRIDAD DE ESTE NODO

Los 7 artefactos generados, sin tocar (mtime de 09:27-09:31, mi sesion empieza a
las 14:11):

```
CONTRADICTIONS.md     09:28:34  4174ffaba99ef305
CURRENT-STATE.md       09:27:34  3e669219f577940c
EVIDENCE-MATRIX.md     09:27:35  e89171ff62d4f58c
KNOWLEDGE-GRAPH.md     09:27:37  b4fc1af6f558f000
NEGATIVE-RESULTS.md    09:28:33  8c0b7a8989075e42
OPEN-FRONTIERS.md      09:28:32  b12b7b46f430b2ac
TOOLS-STATUS.md        09:31:19  456be55282307713
```

Herramientas, sin tocar: `govcheck.py` mtime 03:31:02 sha `959bf46b`;
`integridad.py` mtime 10:50:14 sha `170590c7`.

`.write-lock/`: **no lo he abierto ni cerrado**. Su mtime se movio a las
14:18:42 durante mi sesion; mis unicos comandos sobre esa ruta fueron `stat` y
`ls`, de solo lectura. Lo declaro en vez de suppose lo contrario.

Ficheros escritos por este nodo (3, todos nuevos, ninguno generado):

```
01-AUDITORIA/TOOLS-STATUS-SELFTEST-DRIFT-2026-10-03.md
01-AUDITORIA/TOOLS-STATUS-SELFTEST-DRIFT-2026-10-03.raw-capture.txt
01-AUDITORIA/TOOLS-STATUS-SELFTEST-DRIFT-2026-10-03.raw-flagclass.txt
```
