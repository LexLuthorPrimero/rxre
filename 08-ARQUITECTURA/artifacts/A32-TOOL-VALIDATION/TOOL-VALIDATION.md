# TOOL-VALIDATION — AGENT-32

<!-- GENERADO POR MEDICION, no escrito a mano. Artefactos:
     selftest-observado.tsv, fixture-clasificacion.json
     Regenerar: python3 tools/A32/run_selftests.py && python3 tools/A32/classify_fixture.py -->

AGENCIA=RX550-INVESTIGACION (AGENT-32 TOOL VALIDATION)
WORK_CLASS=validacion-de-instrumentacion
RUNTIME=SI · user namespace no necesario · sin sudo · GPU=INTACTA
CERROJO=.write-lock/a32-toolv tomado · SIN COMMITS
fecha=2026-10-03

---

## 0 · QUE AFIRMA ESTE DOCUMENTO

`TOOLS-STATUS.md` marca 65 de 72 herramientas `TOOL_VALIDATED`. Esa
etiqueta se define asi, en el propio fichero:

> `TOOL_VALIDATED` — *el selftest existe y pasa*

Eso es **SELF-TESTED**, no `VALIDATED`. En la escalera de AGENT-32
(`IMPLEMENTED -> SELF-TESTED -> VALIDATED -> TRUSTED`) la etiqueta salta un
escalon, y el escalon que salta es exactamente el que exige la
`INDEPENDENT CROSS CHECK`.

**Medido: 4 de las 65 filas `TOOL_VALIDATED` son incorrectas.** Y el
defecto de raiz no es un error de cuatro filas: es que **el veredicto se
calcula contra un corpus que se esta moviendo mientras se mide**.

---

## 1 · LO QUE MIDIO, Y COMO

Dos mecanismos DISTINTOS, a proposito: `TOOLS-STATUS.md` lo genera
`artifacts.py`, asi que reejecutar `artifacts.py` no seria un contraste,
seria el mismo tester.

```
$ python3 run_selftests.py        # 72 herramientas, invocadas como subproceso
herramientas vistas : 72
filas en TSV        : 73  -> artefacto VALIDO
  TOOL_SELFTEST_PASS   60
  TOOL_SELFTEST_FAIL    4
  TOOL_RC_OTHER         2
  TOOL_TIMEOUT          1
  TOOL_SOURCE_ONLY      5
```

Cada fila guarda rc, bytes de stdout, bytes de stderr, duracion y si
expiro. Ninguna salida se encadena a `head`: cada log va a su fichero
(AGENTS.md 28, SIGPIPE). Un timeout se clasifica aparte: no es un fallo.

---

## 2 · LAS CUATRO FILAS INCORRECTAS

| herramienta | registro dice | observacion | veredicto real |
|---|---|---|---|
| `implgate.py` | `TOOL_VALIDATED` | `RESULT: FAIL (1)` rc=1 | la herramienta es correcta; su fixture no (ver 3) |
| `integridad.py` | `TOOL_VALIDATED` | rc=1, 4729 B | **no tiene selftest**: ejecuta la auditoria e imprime `FALLA: DUPLICADOS 1, TEXTO 1, SIN_DECL 1, CONTAMINADOS 15` |
| `citas.py` | `TOOL_VALIDATED` | **timeout >180 s, 0 B stdout, 0 B stderr** | verde sobre una herramienta que no termina y no produce una palabra |
| `atom_chain.py` | `TOOL_UNVALIDATED`, `declara selftest: si` | rc=2 | el flag real es `--self-test <f>` (con guion y argumento), no `--selftest` |

`integridad.py` es una **regresion del defecto ya documentado**: el
hallazgo `FINDING-TOOLREG-FALSE-VERDICT.md` 5.3 lo movio de `TOOL_BROKEN`
a `TOOL_UNVALIDATED` por no declarar selftest; hoy la tabla lo devuelve a
`TOOL_VALIDATED`. El defecto no se corrigio, se reintrodujo.

Y el mas peligroso no es un rojo: es **`citas.py`, verde, colgado y mudo**.
Un instrumento que no termina no puede ser la evidencia de nada.

---

## 3 · EL HALLAZGO DE RAIZ: EL SELFTEST DE `implgate.py` NO ES HERMETICO

`implgate.py` sale rojo con:

```
FAIL un numero inexistente devolvio 'AMBIGUO(2): 999-correccion-a-105-no-hay-an,
                                     999-el-corpus-de-definiciones-'
```

La lectura apresurada es "la herramienta esta rota". **Es la herramienta
correcta y el fixture comprometido.** Discriminante, no opinion:

- `implgate.py:71` — `ROOT_SELFTEST = <tools>/..` = **la raiz real del proyecto**
- `implgate.py:226` — `cerrada_en()` hace `os.listdir(findings)`
- `implgate.py:313` — el vector espera que **`"999"` no exista**

Ese `"999"` es una constante magica cuya validez dependia del tiempo. El
corpus la alcanzo hoy. Comprobado:

```
$ python3 tools/nextnum.py --check 999 --json
{"numero":"999","n":2,"unico":false, "ficheros":[...x2...]}
```

Un selftest que lee el mundo mutable del proyecto **no es reproducible**:
cualquier agente que escriba un hallazgo lo pone rojo sin haber tocado la
herramienta. Clasificar eso como `TOOL_BROKEN` seria un veredicto falso,
y `TOOLS-STATUS.md` no tiene ninguna columna para distinguirlo.

### 3.1 · Por que existe el 999 duplicado

`nextnum.py` existe para impedir exactamente esto, y no lo impidio:

```
$ python3 tools/nextnum.py --reservar 1005 --json
{"n":"1005","estado":"MALO","motivo":"el numero debe ser de 3 cifras"}
```

- `tools/nextnum.py:86` — `NUM_RX = re.compile(r"^(\d{3})[-_](.+)\.md$")`
- `tools/nextnum.py:149` — rechaza todo lo que no sea `^\d{3}$`

El dominio del mecanismo de reserva es **001–999**. El corpus ya tiene
cuatro hallazgos de cuatro cifras, y **dos colisionan**:

```
1000-de-pci-enumeration-a-gpu-ready-la-secuencia-completa.md
1000-eng-invalidate-es-gfx9-y-no-gfx8.md      <-- 1000 duplicado
1002-correccion-a-105-...md
1010-el-limite-de-paginas-de-ttm-...md
```

**Todo numero >= 1000 queda fuera del guard de colisiones.** 999 y 1000
son las dos colisiones que deja esa puerta abierta.

---

## 4 · CUANTAS HERRAMIENTAS COMPARTEN EL DEFECTO DE `implgate.py`

Clasificacion **ESTATICA** del cuerpo de cada `selftest` (68 ficheros
`.py`/`.sh`): `HERMETICO` si crea su propio directorio temporal;
`ACOPLADO_AL_CORPUS` si lee rutas del proyecto sin directorio temporal.

```
HERMETICO              16
ACOPLADO_AL_CORPUS     10
MIXTO                  4
INDETERMINADO          22
SIN_SELFTEST           16
```

**Solo 16 de 68 selftests son demostrablemente reproducibles.** 14 leen
el corpus vivo. 22 son `INDETERMINADO`, que **no es verde**: es ausencia de
evidencia, y se queda como ausencia de evidencia.

LIMITACION DECLARADA: esto es analisis estatico de texto, no ejecucion.
Clasifica el *fixture*, no la correccion. Un selftest hermetico todavia
puede ser incorrecto; uno acoplado puede ser correcto mientras el corpus
cambie.

---

## 5 · `govcheck.py`: TAMBIEN ES UN ROJO FALSO (CORRIJO MI PROPIA REDACCION)

**Me equivoque en la primera redaccion de este documento.** Escribi que el
veredicto `TOOL_BROKEN` era correcto y solo la causa estaba refutada. **Es
incorrecto: el veredicto tambien es falso.** Lo discrimine ejecutando la
funcion del propio govcheck sobre el fixture del vector que falla:

```
$ donde_esta(RAIZ, "AGENTS.md: TOOL_UNVALIDATED no puede cerrar una
                       afirmacion critica", versiones_agentes(RAIZ))
  estado   = 'EN_VIGENTE'          <-- el vector exige 'SOLO_ANTES'
  decidio  = 'tool_unvalidated'    <-- correcto
  terminos = ['afirmacion','cerrar','critica','puede','tool_unvalidated']
```

La logica de `govcheck.py` es **correcta**: normaliza bien (el texto real de
`AGENTS.md:909` es `` `TOOL_UNVALIDATED` no puede cerrar afirmación crítica. ``
con backticks y acentos, y la herramienta los descarta correctamente),
elige bien el termino raro, y acierta el estado.

El vector esta **OBSOLETO**: afirma que la proposicion "perdio su
documento", y la proposicion **sigue vigente** en `AGENTS.md:909`. El
rojo no lo produce un defecto de la herramienta.

Lo que **no** se sostiene es la causa que el hallazgo
`FINDING-TOOLREG-FALSE-VERDICT.md` 8 le atribuye:

> *"deriva `RAIZ` de su propia ruta (linea 76), asi que en este workspace
> lee el `AGENTS.md` de rol de 548 B"*

Medido: el fichero que lee es de **30295 B**, sha `5d33ccab`, **byte a byte
igual a `git show HEAD:AGENTS.md`**. No son 548 B. La causa registrada no
explica el rojo, y el rojo sigue sin causa validada.

### 5.1 · Y el `AGENTS.md` que todos las herramientas leen

El `AGENTS.md` de la raiz tiene **6 bind mounts apilados**, y el orden
real se resuelve por la cadena de `parent ID` (no por el orden del
fichero `mountinfo`). De abajo a arriba:

```
mid=1750  519 B  06-DRIVER-C-ASM-PERFORMANCE     (base, padre 44 = raiz)
mid=1560  548 B  05-TOOLING-AUTOMATION
mid=1397  489 B  04-RUNTIME-PROBING
mid=1261  466 B  03-GPU-SEMANTICS
mid=1152  604 B  02-SOFTWARE-GPU
mid=1070 30295 B 01-COORDINACION               (SUPERIOR, gana)
```

El contenido visible es correcto **por casualidad del orden de montaje**:
la capa de arriba resulta ser la unica de 30295 B, y ademas es
byte-identica al fichero de git. Si se reaplica cualquiera de las cinco
capas cortas, el fichero canonico de gobernanza que leen `govcheck.py`,
`lint.py` y `docscan.py` pasa a ser un rol de 519 B sin avisar.

---

### 5.2 · `citas.py`: NO ESTA COLGADO. ES O(corpus), Y EL CORPUS CRECIO

Deje escrito que no sabia si era lento o colgado. **Es lento, y la razon
esta medida.** `citas.py:68-72`:

```python
for pat in ("**/*.c", "**/*.h"):
    for f in glob.glob(os.path.join(raiz, pat), recursive=True):
        ...
        for i, l in enumerate(fh, 1):      # lee TODAS las lineas
```

Su selftest recorre **todo** el arbol del proyecto. Medido:

```
ficheros .c/.h bajo la raiz     : 72089
de los cuales, arboles de kernel: 71786
RESEARCH/                        : 2,9 G
```

O sea: el 99,6 % del trabajo lo aporta el corpus de Linux que otro agente
trajo a `RESEARCH/`. Despues de 5 min el proceso seguia con **0 bytes**
de salida, porque no emite nada hasta terminar el barrido.

**No es un cuelgue: es un fixture no hermetico cuyo coste escala con el
proyecto.** En el registro sigue siendo `TOOL_VALIDATED`, y es la fila mas
peligrosa de las tres: un instrumento que no termina jamas no puede ser la
evidencia de nada, y encima sale verde.

Detenido con `SIGTERM` tras el diagnostico, para no robar CPU a los otros
agentes.

---

### 5.3 · LOS TRES SON EL MISMO DEFECTO

| herramienta | sintoma | causa unica |
|---|---|---|
| `implgate.py` | rojo falso | centinela `"999"` expiro al crecer el corpus |
| `govcheck.py` | rojo falso | el vector afirma una proposicion que sigue vigente |
| `citas.py` | verde que no acaba | el fixture lee 72089 ficheros del proyecto |

Tres sintomas distintos, una sola causa: **los selftests no son
hermeticos; viven dentro del proyecto que miden.** Por eso sus veredictos
no son reproducibles, y por eso un `VALIDATED` sobre ellos no es una
afirmacion, es una fotografia.

Y el modo de fallo dominante **no es un error de codigo en las
herramientas**. De las cuatro filas que el registro da por buenas y no lo
son, tres son acoplamiento al corpus y una (`integridad.py`) es que no
tiene selftest. **Ninguna de las cuatro es un bug de logica.**

---

## 6 · ERROR PROPIO, RETRACTADO

Mi primera ejecucion marco `CONTAMINADO`: el hash de `git status` cambio
(`ee5a33ba` -> `d813136e`). **Lo retracto.** Medí la deriva de fondo con
cuatro muestras y no haciendo nada:

```
15:57:22  d813136e  625 entradas
15:57:37  cc2ac8b8  626
15:57:52  d65459f9  628
15:58:08  447002bf  629
```

Cuatro cambios en 46 s. Los escriben **otros agentes**: durante el turno
aparecieron los hallazgos 998, 999, 1002 y dos herramientas nuevas
(`tools/gttlimit.py`, `tools/rx550-continua-supervisa`).

`git status` **no es un detector de contaminacion valido en este
workspace**: su tasa de falso positivo no es cero. Es el mismo error que
`FINDING-TOOLREG-FALSE-VERDICT.md` ya cometio una vez — confundir un rc
con un fallo — y lo cometi yo, un turno, con otro detector.

---

## 7 · ESTADO POR HERRAMIENTA

Escalera de AGENT-32. `NOT_TRUSTED` = no puede sostener una afirmacion
critica. No es "rota": es "no comprobada".

Cruce de los DOS ejes medidos — veredicto de ejecucion x clase de fixture.
Las cifras son del cruce, no una tabla escrita a mano:

| estado | n |
|---|---|
| `TRUSTED` | **0** |
| `VALIDATED` | **0** |
| `SELF_TESTED_REPRODUCIBLE` (hermetico + rc=0) | 16 |
| `SELF_TESTED_NO_REPRODUCIBLE` (acoplado o mixto + rc=0) | 12 |
| `SELF_TESTED_FIXTURE_INDETERMINADO` (rc=0, sin firma) | 32 |
| `NOT_TRUSTED_SELFTEST_ROJO` | 4 |
| `NOT_TRUSTED_FIXTURE_OBSOLETO` (logica correcta, rojo falso) | 2 |
| `NOT_TRUSTED_NO_TERMINA` (O(corpus), verde en el registro) | 1 |
| `NOT_TRUSTED_NO_EJECUTABLE` (`.c` sin binario ejecutable) | 5 |
| **total** | **72** |

`NOT_TRUSTED_SELFTEST_ROJO` = `integridad.py` (sin selftest, rc=1 es una
auditoria), `oracle.sh`, `atom_chain.py` (flag `--self-test`),
`validate_rx550_final.py` (no acepta el flag).
`NOT_TRUSTED_FIXTURE_OBSOLETO` = `govcheck.py`, `implgate.py`.

**Ninguna herramienta llega a `VALIDATED`.** Ninguna tiene
`INDEPENDENT CROSS CHECK` registrada. El maximo alcanzado por el conjunto
es `SELF_TESTED`, y 16 de 72 son ademas reproducibles.

LIMITACION DE LA CLASE `SIN_SELFTEST` (esta vez la estoy midiendo el fallo):
mi clasificador busca `def selftest*`. Eso da `SIN_SELFTEST` para
`atom_chain.py`, `integridad.py`, `oracle.sh` y `citas.py`, **y los cuatro
SI tienen selftest** — el flag se llama `--self-test` (con guion), o el
fichero es `.sh`, o el "selftest" es en realidad una auditoria que ignora el
flag. `SIN_SELFTEST` significa "no encontre un `def selftest*`", no "no
tiene selftest". Por eso los 4 slipped into `NOT_TRUSTED_*` por su
comportamiento observado y no por la clase estatica.

### 7.0 · Y el denominador tambien se movio

`gttlimit.py` (6801 B) lo creo otro agente **durante** mi medicion:

```
poblacion AHORA : 73        (66 .py + 2 .sh + 5 .c)
poblacion VISTA : 72
EN DISCO PERO NO EJECUTADO: ['gttlimit.py']
```

Asi que **72 es una cota inferior que ya caduco**, y `TOOLS-STATUS.md`
dice 72. El denominador del registro es tan movido como su numerador: una
tabla de herramientas sin `observado_en` no puede saber si esta completa.

### 7.1 · Los cinco `.c` no se pueden validar tal como se entregan

| fuente | binario | veredicto |
|---|---|---|
| `pm4decode.c` 18048 B | **NO** | no compilado: no existe `pm4decode` |
| `kdeps.c` 8681 B | **NO** | no compilado: no existe `kdeps` |
| `pm4dw.c` | `pm4dw` 30640 B | binario de 2026-10-01, fuente de 2026-10-01 |
| `rx550ref.c` | `rx550ref` 30808 B | idem |
| `rx550pm4val.c` | `rx550pm4val` 30120 B | idem |

`pm4decode.c` es el decodificador PM4 del proyecto y **no tiene
ejecutable**: `TOOLS-STATUS.md` lo llama `TOOL_PARTIAL`, pero no es que
expire su selftest; es que no hay nada que ejecutar. Un `.c` no es una
herramienta, es una fuente.

---

## 8 · LO QUE ESTA ABIERTO, Y NO LO HE TOCADO

1. **`nextnum.py` no puede numerar nada `>= 1000`.** El corpus ya paso su
   dominio. Mientras tanto, cada hallazgo de cuatro cifras nace sin
   reserva atomica, y 999 y 1000 estan duplicados. Repararlo cambia el
   numerado de un corpus de 509 ficheros: no es decision mia.
2. **Los dos fixtures obsoletos hay que arreglarlos, y no se como.** El de
   `govcheck.py` exige que la proposicion `TOOL_UNVALIDATED no puede cerrar
   una afirmacion critica` este **retirada**, y hoy esta **vigente** en
   `AGENTS.md:909`. O se retira la proposicion, o se reescribe el vector.
   Ninguna de las dos me corresponde: la primera cambia la gobernanza del
   proyecto, la segunda decide si el gate tiene dientes.
3. **Los 6 bind mounts sobre `AGENTS.md` siguen montados** (5.1). El
   contenido visible es correcto por orden de apilado, no por integridad.
   Desmontarlos necesita `sudo`.
4. **`74` numeros duplicados** (`nextnum.py --rellenar`, 175 de 509
   documentos). MEDIDO. Que cada uno sea defecto y no convencion
   `NNN-correccion-a-XXX` esta **NOT_DETERMINED**: no he auditado uno a
   uno y lo afirmo.

### Lo que YA NO esta abierto (cerrado este turno)

- ~~`govcheck.py` en rojo sin causa~~ → **causa establecida**: fixture
  obsoleto, logica correcta. El rojo es falso (5).
- ~~`citas.py`: lento o colgado~~ → **lento**: O(corpus), 72089 ficheros,
  71786 de ellos arboles de kernel (5.2).
- ~~4 filas del registro incorrectas~~ → **3 con causa establecida**
  (`integridad.py`, `implgate.py`, `citas.py`). La cuarta
  (`atom_chain.py`) es un contrato de flag, no un defecto de logica.

## 9 · QUE HARIA FALAR LA SEGUNDA VEZ

La columna que falta en `TOOLS-STATUS.md` no es otra etiqueta: es una
**condicion de validez**:

```
herramienta | veredicto | observado_en | huella_del_corpus | VALIDO | EXPIRADO
```

Un `VALIDADO` sin `huella_del_corpus` no se puede defender cuando el
corpus cambia cuatro veces en cuarenta y seis segundos.

---

## 10 · ESTADO

```
TOOLS-STATUS.md          NO TOCADO: este trabajo no lo regenera
artefactos               08-ARQUITECTURA/artifacts/A32-TOOL-VALIDACION/ (5 ficheros)
harness                  run_selftests.py, classify_fixture.py  (REPRODUCIBLE)
autopista                el propio documento se auto-audita; por eso se hallaron
                         482 NUL que lo hacian binario para grep/sed
numero de hallazgo       NINGUNO: nextnum.py rechaza 1005 ("debe ser de 3 cifras")
GPU                      INTACTA
commits                  NINGUNO
cerrojo                  .write-lock/a32-toolv liberado
```

### Lo que pido a la autoridad

`nextnum.py` no me deja numerar un hallazgo porque **su dominio se quedo
corto**, y por eso este documento no tiene numero. No lo he numerado a
mano para no crear la quinta colision: seria repetir el defecto que
senalo. Decision de numerado y de quien repara `govcheck.py`: **autoridad,
no agente**.
