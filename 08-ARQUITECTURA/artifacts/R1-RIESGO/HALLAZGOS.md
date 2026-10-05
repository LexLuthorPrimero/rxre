# R1-RIESGO — la interlusa de seguridad no ve el código, y el flag del selftest no es un argv

<!-- ORIGEN: MEDIDO con tools/riesgo.py. Artefacto: riesgo.json (199 filas).
     Regenerar: python3 tools/riesgo.py --json > 08-ARQUITECTURA/artifacts/R1-RIESGO/riesgo.json -->

```
AGENCIA=RX550-INVESTIGACION · AGENT RE/TOOLING
WORK_CLASS=validacion-de-instrumentacion
RUNTIME=NO · sin sudo · sin ejecucion de terceros · GPU=INTACTA
escritura=2 ficheros NUEVOS.  Ningun fichero existente modificado.
herramienta   tools/riesgo.py 1.0.0
sha256        dd4fc3c5413e4519
artefacto     08-ARQUITECTURA/artifacts/R1-RIESGO/riesgo.json
sha256        c2a074f33c80d53e
reproducible  7eb44bda35049c5cd4b4241a4d82e8bf0431b2f7f455cf8a7f7bce12f3f89cd0

selftest      20 vectores, 0 fallos, rc=0   (HERMETICO: verificado en copia aislada y otro cwd)
```

**Sobre el hash de esta cabecera.** Se cito `f7fb8965…` y luego `c1755c1b…`
en versiones anteriores de este documento, y los dos quedaron obsoletos al
seguir editando `riesgo.py`. Ninguno se conserva como si valiera: un hash
obsoleto en un bloque de procedencia es exactamente la clase de mentira que
este trabajo denuncia. El de arriba es el vigente **en este momento**, y
`git hash-object tools/riesgo.py` lo verifica sin leer este documento.

## 0 · QUE AFIRMA ESTE DOCUMENTO

El proyecto tiene una interlusa que decide si una herramienta puede ejecutarse:
`toolreg.run_selftests()`, que la implementa con `declares_read_only()` más dos
regex sobre el **texto** del fichero. Este documento mide la distancia entre lo
que esa interlusa responde y lo que el **código** hace.

**La distancia existe, y en un punto no es ruido: son cinco herramientas, y
tres de ellas abren el nodo de la GPU.**

Que la interlusa tenga ruido no es una opinion. `toolreg.py:441-441` razona
sobre el riesgo de ejecutar codigo de otra sesion en un arbol donde se trabaja a
veces, y su propia respuesta al ruido esta escrita en el fichero: *"an interlock
that cries wolf on a spelling gets ignored, and then it protects nothing"*. Este
documento mide cuantos lobos hay.

---

## R1-01 · HUECO DE LA INTERLUSA — 5 herramientas, 3 con la GPU

`HUECO_GATE` = el código ejecuta una operación de las que la interlusa debería
vetar, y `toolreg` **no las rechaza**. **MEDIDO: 7 de 199.**

| herramienta | capabilities medidas | severidad | qué lo hace |
|---|---|---|---|
| `revkit/captura.py` | `PROC_PRIV` | **CRITICO** | `:219` `subprocess.run(["sudo","-S","-k","bash","-c",script,…])` |
| `revkit/mmo.py` | `PROC_PRIV` | **CRITICO** | `:130` `cmd = ["sudo","-S","-k","bash","-c",…]` en `sudo_read()` |
| `08-ARQUITECTURA/tools/amdmmr.c` | `DEVICE_OPEN_RDWR` `IOCTL_AMDGPU` `IOCTL_MMR` | **ALTO** | `:73` `open(nodo, O_RDWR)` + `AMDGPU_INFO_READ_MMR_REG` |
| `08-ARQUITECTURA/tools/amdinfo.c` | `DEVICE_OPEN_RDWR` `IOCTL_AMDGPU` | **ALTO** | `:54` `open(nodo, O_RDWR)` + `ioctl(…, DRM_IOCTL_AMDGPU_INFO, …)` |
| `08-ARQUITECTURA/tools/amdioread.py` | `IOCTL_AMDGPU` | **ALTO** | dentro de `PROBE_C`, la constante C que compila y ejecuta (ver R1-05) |
| `08-ARQUITECTURA/tools/vbiosread.py` | `IOCTL_AMDGPU` | **ALTO** | `:88` `open(nodo, O_RDWR)` + `AMDGPU_INFO_VBIOS`, igual vía `PROBE_C` |
| `09-POWER-CLOCKS/tools/rx550_hold.c` | `DEVICE_OPEN_RDWR` `POWER_HOLD_RT` | **ALTO** | `:23` `open(node, O_RDWR|O_CLOEXEC)` y `sleep()` |

### El mecanismo, que es la parte transferible

Las cinco llegan a su ruta **a través de una variable**, no como literal en el
sitio de la llamada:

```c
const char *nodo = argc > 1 ? argv[1] : "/dev/dri/renderD129";
int fd = open(nodo, O_RDWR);
```

Cualquier clasificador que case el literal `"..."` pegado a `open(` no lo ve. Y
`FORBIDDEN_CALL` busca `/dev/(mem|kmem)`, que **no es la ruta que usa ninguna de
las cinco**: la ruta real de una GPU es `/dev/dri/renderD129`.

**`rx550_hold.c` es el caso que importa.** Sus 35 líneas, y su propósito
declarado en la línea 2:

> `keep amdgpu runtime-PM resumed so DPM and hwmon sysfs become readable`
> `Holding a render-node fd is enough; no root required.`

Es decir: **su función es mantener la GPU de la pantalla fuera de
runtime-suspend.** El registro `TOOLS-STATUS.md` lo marca `TOOL_UNVALIDATED`,
35 líneas, sin selftest — **idéntico a una herramienta que solo hace grep**. Lo
único que impide que se ejecute por accidente es que no está compilado. No hay
ninguna puerta que lo impida.

**La gravedad no es la destrucción: es la contaminación.** El propio docstring
explica por qué importa: con la GPU despierta, `pp_dpm_sclk` deja de devolver
`EBUSY` y las lecturas de power/clock dejan de ser lo que dicen ser. Un harness
que ejecute herramientas indiscriminadamente puede alterar **toda medición de
`09-POWER-CLOCKS` sin dejar rastro**. Es un confounder (AGENTS.md §50), y es
silencioso porque el número sale plausible.

Esto es lo que convierte en trampa el segundo defecto: **el arreglo obvious del
hueco de cobertura de `TOOLS-STATUS.md` —ejecutar las 118 filas que hoy nadie
ejecuta— pasa por encima de estas cinco sin ninguna interlusa.**

### Y las que también tocan el nodo sin ser hueco

`rx550_load.c`, `pcie_bandwidth.c` y `vulkan_compute_probe.c` abren sysfs con
`O_RDONLY` o `fopen(...,"r")`. No son hueco: la interlusa no las rechaza y el
código no hace nada prohibido. Se listan porque comparten el patrón de ruta por
variable, y si mañana alguien cambia un `"r"` por un `"w"` el hallazgo tiene que
volver a aparecer. `riesgo.py --explain <herramienta>` las trae.

### `vbiosread.py` lee, y lo dice bien

Esta fila estaba mal en la primera medición y por eso se deja escrita. Marcaba
`vbiosread.py` con "declara `WRITES_GPU=no` y emite ioctl DRM", y **eso es
falso**: `AMDGPU_INFO_VBIOS` es una ioctl de **lectura**, y `WRITES_GPU=no` es
una declaración honesta. El defecto era de la regla de `riesgo.py`, que
conflacionaba *emitir una ioctl* con *escribir*. Corregida, y con vector de
regresión (`FP_4`).

Lo que queda de `vbiosread.py` es que abre el nodo con `O_RDWR`, que da un
descriptor escribible aunque la ioctl sea de lectura. Eso se afirma como lo que
es —un descriptor escribible— y no como una mentira.

Que un detector de riesgo produzca un falso positivo sobre la herramienta
*correcta* del árbol es la mitad del trabajo: la otra mitad es que se note.

---

## R1-02 · EL FLAG DEL SELFTEST — 22 herramientas, y una de ellas es aguda

Los tres harnesses del proyecto resuelven el flag del selftest con la misma
lista (`artifacts.py:732`, `toolreg.py:239`):

```python
GRAFIA_SELFTEST = ("--selftest", "--self-test", "selftest")
```

**La tercera grafía no lleva guiones.** Casa con el **nombre de la función** y
produce una palabra que ninguna comparación de argv puede verificar.

MEDIDO: **22 de 199** herramientas son preguntadas por un flag que no existe
como token argv. **9 de ellas tienen un `--self` real que nadie pregunta.**

### El caso agudo: `amdioread.py`

```
pregunta=  'selftest'      <- la palabra suelta, porque def selftest() la contiene
real=      ['--self']      <- lo que el codigo compara de verdad
```

Su `main` (`:282`) es `if "--self" in argv`. Preguntada por `selftest`, la
comparacion falla y **cae en la ejecucion normal**, que:

1. `compilar_probe()` — escribe un `.c` con `open(src,"w")` y llama a `gcc`;
2. ejecuta el binario, que hace `open(argv[1], O_RDWR)` sobre
   `/dev/dri/renderD129`;
3. emite `ioctl(fd, DRM_IOCTL_AMDGPU_INFO, &info)`.

Y la interlusa la da por **segura**: su cabecera declara `CONTRACT: READONLY=yes`
y `WRITES_GPU=no`, que `declares_read_only()` acepta, y no hay patrón prohibido
en el texto. **La herramienta que la política considera de solo lectura, cuando
se la ejecuta con el flag que la propia política calcula, emite un ioctl DRM
sobre la GPU de la pantalla.**

### Consecuencia de alcance

Este defecto no es de una herramienta: es de las **tres** harnesses, que
comparten la lista. Cualquier herramienta cuyo flag real sea otro —`--self`,
`--check`, `--probe`— recibe una pregunta que no puede entender, y una pregunta
que no se entiende **no produce un error: produce la ejecución normal**. Para una
herramienta de análisis eso es ruido. Para una de hardware es un ioctl.

Los otros casos incluyen `--self-test` preguntando a un fichero que sólo
acepta `--selftest`, y `--selftest` a uno que sólo acepta `--self-test`
(`revkit/gfx8blocks.py`, `_selftest_help_no_alloc.py`). La lista completa está
en `riesgo.json`, y `riesgo.py --explain <herramienta>` la trae por fila.

---

## R1-03 · LA CABECERA MIENTE — 8 herramientas

**Severidad EPISTÉMICA, no de seguridad.** Un contrato que no describe su
código es un problema de honestidad del registro, no un riesgo para la máquina.
Se separa explícitamente para que no se lea con el mismo peso que R1-01.

| herramienta | contradicción | quién la arregla |
|---|---|---|
| `08-ARQUITECTURA/tools/amdioread.py` | `WRITES_FILES=no`, y abre en escritura | quien escribe el código |
| `08-ARQUITECTURA/tools/toolkit.py` | `WRITES_FILES=no`, y abre en escritura | quien escribe el código |
| `08-ARQUITECTURA/tools/inst_closure.py` | `WRITES_FILES=no`, y abre en escritura | quien escribe el código |
| `08-ARQUITECTURA/tools/struct_rw.py` | `WRITES_FILES=no`, y abre en escritura | quien escribe el código |
| `tools/oracle_drift.py` | `WRITES_FILES=no`, y abre en escritura | quien escribe el código |
| `tools/reservas_gate.py` | `READONLY=yes`, y el código escribe ficheros | quien escribe el código |
| `08-ARQUITECTURA/tools/ambig_citas.py` | la **cabecera** se contradice: `READONLY=yes` y `WRITES_FILES=yes` | quien escribe la cabecera |
| `08-ARQUITECTURA/tools/huella.py` | la **cabecera** se contradice: `READONLY=yes` y `WRITES_FILES=yes` | quien escribe la cabecera |
| `08-ARQUITECTURA/tools/vbiosread.py` | la **cabecera** se contradice: `READONLY=yes` y `WRITES_FILES=yes` | quien escribe la cabecera |

La columna de quién la arregla está porque **son dos cosas distintas**.
"el código desmiente a la cabecera" la arregla quien programa. "la cabecera se
desmiente a sí misma" la arregla quien la escribe, y el código puede estar
perfecto. Juntas en una sola columna, la segunda parece un defecto de
programación y no lo es. MEDIDO: de 9 contradicciones, 3 son de cabecera.

El criterio no lo inventa `riesgo.py`. Es el del propio proyecto:
`contract_exec.py:3-12` documenta que `WRITES_FILES=yes` y `READONLY=no` es lo
que corresponde a una herramienta que escribe, y que declarar `WRITES_FILES=no`
era *"UNA DECLARACION FALSA"*. El eje de este hallazgo es **el mismo criterio
que `contract_exec.py` ya define, extendido de "una herramienta" a "el
registro"**. Nadie lo corría sobre el árbol.

**Lo que este hallazgo NO demuestra:** que escribir un fichero sea peligroso.
Varias de estas herramientas escriben su propio informe, que es trabajo legítimo.
Lo que es falso es la declaración, no la conducta.

---

## R1-04 · LA HERRAMIENTA QUE MIDE EL DEFECTO, ES EL DEFECTO

`toolreg.FORBIDDEN_CALL` encuentra **cuatro** ocurrencias en `riesgo.py`:
`insmod` y `/dev/mem`. Las cuatro están en los **fixtures de control negativo**
del selftest de este fichero (líneas 618, 624, 672, 678), no en código que se
ejecute. El veredicto de la interlusa es `REFUSED_UNSAFE`.

**No se ha tocado el fichero para que deje de darlo.** La tentación era
construir el fixture como `"S" + "/dev/mem"`; eso sería mentir sobre lo que el
test prueba, porque el fixture tiene que contener la palabra o no prueba el caso
que dice probar. Se deja el literal y se declara el rechazo.

Es la tercera muestra del mismo defecto —la interlusa no distingue una mención
de una acción— y la primera cuyo autor es esta herramienta. Un clasificador de
riesgo al que su propio gate no puede leer es el argumento más fuerte que hay
para que el gate mire el código.

---

## R1-05 · EL PUNTO CIEGO QUE ENCONTRÉ AL USAR LA HERRAMIENTA

Este se encontró **usando** `riesgo.py` sobre un caso real, no leyéndolo. Se
cuenta porque es el ciclo completo funcionando, y porque es el tercer defecto
propio de este trabajo.

**Síntoma:** `amdioread.py` salía `caps=[]`, severidad `NULO`. Conocido: su línea
104 es `int fd = open(argv[1], O_RDWR);` y su 115 un
`ioctl(fd, DRM_IOCTL_AMDGPU_INFO, &info)`. La herramienta afirmaba que no hacía
nada.

**Causa:** esa fuente C está dentro de una constante de cadena llamada
`PROBE_C`, que la herramienta compila con `gcc` y ejecuta. Un clasificador de
Python **no ve dentro de una cadena**.

**Por qué no es un caso raro:** escribir un `.c`, compilarlo y ejecutarlo es
justamente el patrón que se usa para alcanzar la ioctl de la capa DRM cuando no
se tiene un módulo que lo haga. Es lo que hace la herramienta de lectura de ASIC
del proyecto. Un clasificador que solo mira el lenguaje del fichero principal
tiene un punto ciego exactamente en el idioma que este proyecto usa para
saltarse sus propias limitaciones.

**Arreglo:** `riesgo.py` extrae las constantes que son fuente C y las pasa por
el detector de C, marcando las capacidades como heredadas y nombrando la
constante de la que vienen, porque una capacidad que viene de una cadena no es
del Python. Vector `FN_3`.

**Efecto sobre el hallazgo:** `HUECO_GATE` pasó de **5 a 7**. Los dos que
aparecieron son `amdioread.py` y `vbiosread.py`. Un instrumento con un punto
ciego no produce menos hallazgos: produce una lista que no se sabe hasta dónde
llega.

---

## 1 · RESULTADO NEGATIVO, Y POR QUÉ IMPORTA

Medido sobre los **176 `.py`** y los **13 `.c`** del árbol:

| | |
|---|---|
| escrituras a `/sys` o `/dev` | **0** |
| `sudo` como argumento de una llamada que crea proceso | **2** (R1-01) |
| aperturas de `/dev/mem` o `/dev/kmem` en código | **0** |
| autocoincidencias del propio `toolreg.py` | 1, ya exenta por `is_self` |
| `.sh` sin clasificar | **9** (limitación 1) |

**La interlusa no es ciega: es ruidosa.** No hay un solo falso negativo de
escritura privilegiada en la población Python. El problema es la precisión, y
eso tiene una consecuencia concreta: hoy nadie puede usar el rechazo como
prueba, porque el rechazo no significa nada.

Y un resultado negativo sobre `riesgo.py` mismo: de 199 herramientas, **ninguna**
abre `/dev/mem` o `/dev/kmem` en código, en ninguno de los siete directorios. El
patrón que la interlusa busca (`/dev/(mem|kmem)`) es el único que no aparece
— y las cinco que sí tocan la GPU usan `/dev/dri/renderD129`, que la interlusa
no busca. **La lista de lo prohibido no contiene lo que ocurre.**

---

## 2 · LO QUE ESTO NO PRUEBA, DECLARADO

- **`.sh` (9 ficheros): sin método.** Salen `NOT_CLASIFICABLE`, que **no es
  `PASA`**. Convertirlos en verde sería repetir el defecto que este trabajo mide.
- **Análisis estático.** No se ejecutó ninguna herramienta. Lo que aquí se afirma
  es lo que el código * dice*, no lo que hace. `rx550_hold.c` no se compiló ni se
  corrió para demostrar que despierta la GPU: se lee su propósito declarado en la
  línea 2, y eso es lo que la evidencia sostiene.
- **Dataflow de un solo salto.** Se resuelve una asignación o un ternario. Una
  ruta construida por concatenación en varios pasos sale como `RUTA_DINAMICA`:
  se sabe que hay llamada de acceso, no a qué nodo llega. El registro lo cuenta en
  `dinamicas`, que hoy es un número, no un veredicto.
- **Un `.c` sin compilar es una fuente.** Este trabajo no lo compila.
- **El eje de contradicción depende del vocabulario `CONTRACT`.** Si `READONLY`
  significara "no toca hardware" y no "no escribe", la sección R1-03 sería ruido.
  Se verificó contra `contract_exec.py`, que es donde ese vocabulario está
  definido. Es una dependencia explícita, no una certeza.
- **Dos falsos positivos míos, corregidos y con regresión.** Escribirlos aquí
  porque un detector de riesgo que no reporta sus errores no es un detector de
  riesgo, es una fuente de afirmaciones.

  1. `revkit/klog.py` salió `PROC_PRIV` porque la primera versión pedía `sudo`
     en el código limpio *más* alguna llamada con nombre de proceso en el mismo
     fichero. En `klog.py` lo único que hay es
     `print("  resource0 es root-only, asi que hace falta sudo.")`. Se corrigió
     exigiendo que `sudo` sea un literal **dentro** de la llamada. Vectores
     `FP_3` y `FN_2`.
  2. `vbiosread.py` salió con "declara `WRITES_GPU=no` y emite ioctl DRM". Es
     falso: `AMDGPU_INFO_VBIOS` es una ioctl de **lectura**, y la declaración es
     honesta. La regla conflacionaba *emitir ioctl* con *escribir*. Corregida, con
     vector `FP_4`.

  En los dos casos lo que se había confundido es **una mención con una acción**,
  o **leer con escribir**: la misma clase de error que el documento denuncia en
  `toolreg.py`, cometida por el instrumento que lo denuncia. Por eso el
  `--explain` de `vbiosread.py` importa tanto como su salida: sin él, este
  hallazgo se habría publicado.

---

## 3 · LO QUE SE PIDE A LA AUTORIDAD

Tres cambios. **Ninguno aplicado**: `toolreg.py`, `artifacts.py` y
`TOOLS-STATUS.md` son del agente principal, y `toolreg.py`, `drift.py` y
`constmap.py` estaban siendo modificados mientras esto se escribía.

1. **`GRAFIA_SELFTEST`: quitar `"selftest"` de la lista, o exigir que el flag
   tenga guiones.** Es el arreglo de una línea que elimina R1-02. while se
   acepta la grafía sin guiones, *toda* herramienta con otro flag recibe una
   pregunta que no entiende, y una pregunta que no se entiende produce la
   ejecución normal.

2. **`FORBIDDEN_CALL`: dejar de buscar solo `/dev/(mem|kmem)`.** Ninguna
   herramienta que abre la GPU de este árbol usa esa ruta; las cinco usan
   `/dev/dri/renderD129`. La lista de rutas prohibidas no contiene la ruta que
   importa.

3. **Antes de ejecutar las 118 filas de `TOOLS-STATUS.md` que hoy nadie
   ejecuta: cerrar R1-01.** Ejecutarlas sin cerrar el hueco pasa por encima de
   cinco herramientas, tres con la GPU, una de ellas con el propósito declarado
   de mantenerla despierta — que es exactamente lo que contaminaría las
   mediciones de power/clock del proyecto.

**Aviso de registro, y unacolsulta que no cierro.** `TOOLS-STATUS.md` queda una
fila corto respecto al árbol, porque `tools/riesgo.py` es nueva: son 201 filas y
199+1 herramientas. Regenerarlo es decisión del agente principal y no se ha
hecho aquí. Cuando se regenere, `riesgo.py` saldrá con el motivo que el propio
generador escribe para las filas que él no ejecuta —
*"enumerado; su selftest NO lo ejecuta este generador"* — y **esa fila es
honesta**: el registro constata que existe y que él no la ha medido.

Pero hay un detalle que no cierro, y lo dejo dicho en vez de encontrarle una
salida limpia: **`riesgo.py` declara `WORK_CLASS=READ_ONLY` y
`WRITE_EXECUTION=NONE`**, o sea que `toolreg.declares_read_only()` la acepta, y
aun así `FORBIDDEN_CALL` la rechaza por los fixtures. Si alguien arregla la
interlusa para que mire el código, tendrá que decidir qué hacer con una
herramienta que contiene literalmente lo que la política prohíbe, en un test que
necesita contenerlo. **Esa decisión es de gobernanza y no es mía.** Lo que sí
consta es el hecho: la política actual y esta herramienta son incompatibles, y
no por culpa del contenido del fichero.

```
ESTADO
  ficheros escritos   2, ambos nuevos
  ficheros modificados 0
  GPU                 INTACTA
  sudo                NO usado
  ejecuciones de terceros  NINGUNA
  commits             NINGUNO
  cerrojo             ninguno tomado: no se escribio en area con escritura ajena
```

## 4 · QUÉ HARÍA FALLAR ESTE TRABAJO OTRA VEZ

- Que `toolreg` se corrija y `HUECO_GATE` baje a 0 sin que el motivo sea una
  corrección: sería que el criterio se aflojó.
- Que un hallazgo nuevo sobre `RX550_HOLD`/`amdmmr` aparezca sin pasar por
  `riesgo.py`: significaría que hay una forma de acceso que este clasificador no
  ve, y sería la tercera limitation a resolver.
- Que las 9 herramientas de `.sh` sigan sin método dentro de tres meses. Es la
  limitación con más probabilidad de convertirse en algo routine, porque nadie
  la va a pagar: es la única que no tiene consecuencia visible el día que se
  salta.