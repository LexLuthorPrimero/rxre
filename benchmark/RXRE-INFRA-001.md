# RXRE-INFRA-001 — SUITE DE TEST REPRODUCIBLE DESDE UN CLEAN CHECKOUT

**Tarea:** versionar los módulos fuente no rastreados que hacen que
`tools/rxre/tests/test_rxre.py` falle con `ModuleNotFoundError: No module named 'api'`.
**Clase:** infraestructura de reproducibilidad. **No** añade capacidades.
**Frontera dura:** NUNCA tocar `0000:00:02.0` (Intel HD 4600 / i915 / fb0 / consola).
Target exclusivo: la RX550 (`0000:01:00.0`). Esta tarea no toca hardware.

**STOP GATE: `RXRE_TEST_INFRA_NOT_VALIDATED`**

La corrección de infraestructura está **completa** (el `ModuleNotFoundError`
desaparece; la suite ejecuta sus 14 grupos desde un clean checkout), pero la
puerta exige **"la suite ejecuta desde un clean checkout Y las pruebas
relevantes pasan"**, y **no todas pasan**. Los dos bloqueadores son
**preexistentes, independientes de esta corrección y fuera de alcance**:
una regresión en el `tools/trace_path.py` comprometido (`TRACE_CALL`, protegido)
y el corpus externo `RESEARCH/` (dato externo, no versionado por diseño).
No se cuenta un import exitoso como una suite aprobada; no se modifica otra
capability para forzar el resultado.

---

## 1. REPOSITORY_STATE

| Magnitud | Valor |
|---|---|
| `main` (baseline) | `53de0098f43d8ab8340603204675a1a2e0faabef` |
| Rama del fix | `fix/reproducible-test-suite` |
| Commit del fix | `5e2b64f` (único commit: `fix: make RXRE tests reproducible from clean checkout`) |
| Worktree del fix | `/home/lucas/.rxre-wt/reproducible-test-001` |
| Worktree de validación | `/home/lucas/.rxre-wt/infra-validate-clean` (detached @ `5e2b64f`) |
| Worktree principal | `/home/lucas/Escritorio/rxre` @ `9ce74c5` [`migration/validated-legacy-work`] |
| `MAIN_WORKTREE_MODIFIED` | **NO** — HEAD sin cambios, nada staged por esta tarea, los 14 módulos siguen `??` (no rastreados) ahí, sin reset/clean/stash/add/commit |

El worktree principal tiene ~231 ficheros sucios y una **sesión concurrente
activa** (escribe `benchmark/RXRE-CAPABILITY-01{2,3}.md`, artefactos de
build del driver, findings, etc. durante esta tarea). Esos cambios son de la
sesión concurrente, **no** de esta tarea. El trabajo de INFRA-001 se hizo
íntegramente en los worktrees aislados bajo `/home/lucas/.rxre-wt/`.

Ficheros del fix (14, la clausura transitiva mínima del punto de entrada
`test_rxre.py`, determinada con la maquinaria real de import de Python y
`runpy -v`, no con `ast` estático):

```text
tools/rxre/api/__init__.py          tools/rxre/backends/registry.py
tools/rxre/api/envelope.py          tools/rxre/backends/adapters/__init__.py
tools/rxre/api/request.py           tools/rxre/backends/adapters/rz_inspect.py
tools/rxre/commands/handlers.py     tools/rxre/backends/decision.json
tools/rxre/commands/query.py        tools/rxre/cli.py
tools/rxre/backends/__init__.py     tools/rxre/rxre          (mode 0755)
tools/rxre/backends/contract.py
tools/rxre/backends/dispatch.py
```

`tools/rxre/commands/` es un **paquete de espacio de nombres** (sin
`__init__.py`; válido en Python 3.3+). `tools/rxre/backends/decision.json`
lo carga `backends/registry.py` (líneas 56 y 239), por eso es parte de la
clausura aunque no sea `.py`.

---

## 2. OBJECTIVE_AND_SCOPE

**Pregunta causal:** ¿por qué `test_rxre.py` no se puede ejecutar desde un
clean checkout de `53de009`, y cuál es el conjunto mínimo de ficheros que hay
que versionar para que sí?

**Alcance (dentro):** los módulos fuente que `test_rxre.py` importa
transitivamente (`api`, `commands`, `backends`, `cli.py`, `rxre`).

**Fuera de alcance (y por qué):**

- `tools/trace_path.py` — capability `TRACE_CALL`. Protegido: la tarea prohíbe
  modificar `TRACE_CALL`. Su regresión es un bloqueador preexistente, no la
  causa del `ModuleNotFoundError`.
- `RESEARCH/` — corpus del kernel (dato externo). No se versiona: son ~50 MB
  de fuentes del kernel, no módulos fuente del proyecto.
- `api/machine.py` — sin importers (WIP de la sesión concurrente); no está en
  la clausura.
- `adapters/`, `storage/` (`rxre.sqlite3` ~50 MB), `fixtures/` (datos binarios
  de test), `tools/pm4ops.py`, `tools/prov.py` — no están en la clausura de
  import de `test_rxre.py`.

**Contrato de no-intervención:** la corrección **no modifica ningún fichero
rastreado**; solo añade los 14 módulos no rastreados, copia byte-fiel de la
sesión concurrente.

---

## 3. BASELINE_REPRODUCTION (FASE 1)

**Producer:** clean checkout de `53de009` (worktree `promotion-002`, sin los
módulos no rastreados, verificado: `tools/rxre/api` ausente).

```text
$ python3 tools/rxre/tests/test_rxre.py
Traceback (most recent call last):
  File ".../tools/rxre/tests/test_rxre.py", line 29, in <module>
    from api import envelope as E  # noqa: E402
    ^^^^^^^^^^^^^^^^^^^^^^^^^^^^^
ModuleNotFoundError: No module named 'api'
EXIT=1
```

**Observación:** la suite **no llega a ejecutar ningún test**. Muere en la
fase de import, línea 29. `fails = []` (línea 31) nunca se alcanza.

**Evidencia:** `ModuleNotFoundError: No module named 'api'` — el módulo
`api` existe y es completo en el worktree concurrente, pero **no está
rastreado** en `53de009`. Un clean checkout de `53de009` no lo contiene.

---

## 4. DEPENDENCY_INVENTORY (FASE 2)

**Lo que `53de009` sí rastrea** (bajo `tools/rxre/`):

- `core/` — 9 ficheros (`dispatch.py`, `relations.py`, `target.py`, ...)
- `tests/` — 37 ficheros (`test_rxre.py`, `test_trace_callers002.py`, ...)

**Lo que NO rastrea** (presente en el worktree concurrente, ausente en
`53de009`): `api/`, `cli.py`, `commands/`, `backends/`, `adapters/`,
`storage/`, `fixtures/`, `rxre`.

**Clausura de import real** (medida con `python3 -m runpy -v` + la maquinaria
de import, no con `ast` — `ast` tenía un bug de paquete de espacio de
nombres): 9 módulos importables, todos importan **OK** en el worktree
concurrente. La clausura está cerrada: no hay import pendiente.

**Método de determinación del conjunto mínimo:** se partió de
`test_rxre.py` y se resolvió la clausura transitiva **con el import real de
Python** (no estático), porque `commands/` es un paquete de espacio de
nombres que `ast` no modela. `test_rxre002.py` importa `commands.query`,
`commands.handlers` y `api.request`, lo que justifica versionar el conjunto
completo y no solo `api`.

**Integridad de la copia (gate FASE 2):** se registraron los sha256 de los
ficheros no rastreados de la sesión concurrente **antes** de leer/copiar;
ningún fuente cambió durante la inspección. `COPY_MISMATCH = []`. Los 14
ficheros copiados son sha256-idénticos a los del worktree concurrente; `rxre`
conserva el bit ejecutable (`0755`).

---

## 5. ROOT_CAUSE (FASE 3)

**Clasificación: `MISSING_TRACKED_SOURCE`**

Los módulos fuente **existen y están completos** en el worktree concurrente,
pero **no están rastreados** en el commit baseline `53de009`. Por tanto un
clean checkout de `53de009` carece de ellos y `from api import envelope`
( línea 29 de `test_rxre.py`) lanza `ModuleNotFoundError`.

**Cadena causal:**

```text
commit 53de009  →  no rastra api/ commands/ backends/ cli.py rxre
        ↓
clean checkout  →  árbol sin esos módulos
        ↓
test_rxre.py:29  →  from api import envelope
        ↓
ModuleNotFoundError: No module named 'api'   (EXIT=1, 0 tests ejecutados)
```

**No es** un bug de código, **no es** un problema de PYTHONPATH, **no es**
un fallo del corpus. Es un **defecto de versionado**: la fuente vive solo en
el worktree activo, no en el histórico.

---

## 6. FIX_APPLIED (FASE 4)

**Acción:** copiar los 14 ficheros de la clausura al worktree del fix y
confirmarlos en un único commit.

**Verificación de no-regresión:**

- Ningún fichero rastreado modificado (`git diff 53de009 --stat` sobre
  ficheros rastreados = vacío; solo `create mode` para los 14).
- Los 14 ficheros son copia byte-fiel (sha256 idéntico a la fuente
  concurrente).
- `from api import envelope` → OK (`SCHEMA_VERSION=1.0`).
- `python3 tools/rxre/rxre capabilities` → rc=0, envelope válido, desde un
  clean checkout.

**Commit único** `5e2b64f`:

```text
fix: make RXRE tests reproducible from clean checkout
14 files changed, 3317 insertions(+)
 create mode 100644 tools/rxre/api/__init__.py
 ... (13 create mode más)
 create mode 100755 tools/rxre/rxre
```

`__pycache__/` está en `.gitignore` (`__pycache__/`, `*.py[cod]`), así que
ejecutar los tests no ensucia `git status --short`.

**Lo que la corrección NO hace:** no toca `trace_path.py`, no versiona el
corpus, no añade stubs vacíos, no añade fallbacks silenciosos, no salta
tests, no pide PYTHONPATH manual.

---

## 7. CLEAN_CHECKOUT_VALIDATION (FASE 5)

**Producer:** worktree **nuevo** del commit del fix (`infra-validate-clean`,
detached @ `5e2b64f`). Es un **true clean checkout**: `RESEARCH/` está ausente
(porque es dato externo no rastreado). No es el árbol con ficheros
residuales.

| Prueba | Exit | Resultado |
|---|---|---|
| `test_rxre.py` | **1** | `self-test FALLA (3)` |
| `reg_resolve.py --selftest` | 0 | `RESULTADO OK · vectores conocidos reproducidos` |
| `mutate_reg_resolve009.py` (REGISTER_IDENTITY) | **2** | `FileNotFoundError: RESEARCH/working/linux-7.1.3/.../gmc_8_1_d.h` |
| `test_trace_callers002.py` | 0 | `RESULTADO: 0 fallos, 0 skips` |

**Detalle de `test_rxre.py` (3 fallos, sin corpus):**

```text
--human dice el estado empty    search VM_CONTEXT0_CNTL  (0 res)
trace de un simbolo real da ok con resultados ('empty', 0)
el simbolo real trae su ubicacion []
```

**Registro de resultados:**

- `BASELINE_TESTS` (clean `53de009`): la suite **no ejecuta** (import falla,
  EXIT=1, 0 tests).
- `INFRA_FIX_TESTS` (clean `5e2b64f`): la suite **ejecuta** los 14 grupos;
  2 de 4 categorías pasan (`selftest`, `test_trace_callers002`), 2 fallan
  (`test_rxre.py`, `mutate_reg_resolve009`).
- `REGISTER_IDENTITY_TESTS` (`mutate_reg_resolve009`): **FAIL** — necesita
  `RESEARCH/working/linux-7.1.3`, que no está versionado y, incluso presente,
  está incompleto (solo `include/linux/`), así que `chosen` es `None`.
- `TRACE_CALL_TESTS` (`test_trace_callers002`): **PASS** (0 fallos, 0 skips) —
  encuentra el corpus por la ruta absoluta de laboratorio
  `/home/lucas/Escritorio/rxre/RESEARCH/kernelbuild/linux-7.1.3`, por lo que
  pasa incluso sin corpus local.
- `FAILURES`: `test_rxre.py` (3 sin corpus / 2 con corpus);
  `mutate_reg_resolve009` (FileNotFoundError).
- `SKIPS`: 0 en `test_trace_callers002`; `mutate_reg_resolve009` no skipea,
  falla con error.
- `FULL_REGRESSION`: **no** — no se ejecutó la suite completa (solo las 4
  categorías relevantes de FASE 5).

---

## 8. DISCRIMINATING_EXPERIMENT

**Pregunta:** ¿los 2 fallos de `trace` los causa (a) la corrección de
infraestructura, (b) la ausencia del corpus, o (c) una regresión preexistente
del `trace_path.py` comprometido?

**Experimento 1 — presencia del corpus** (symlink de solo lectura de
`RESEARCH/` dentro del clean checkout del fix):

```text
sin corpus  → test_rxre.py FALLA (3)   [search, trace, ubicacion]
con corpus  → test_rxre.py FALLA (2)   [trace, ubicacion]
```

El fallo `search VM_CONTEXT0_CNTL` **desaparece** con el corpus → es
**dependiente del corpus** (dato externo). Los 2 fallos de `trace`
**persisten con el corpus** → **no** son de corpus ni de la corrección.

**Experimento 2 — versión de `trace_path.py`** (`rxre trace amdgpu_vm_init`):

| Entorno | `trace_path.py` | Resultado |
|---|---|---|
| Clean checkout `5e2b64f` (corpus presente) | comprometido @`53de009`, `VERSION=1.1.0` | `status=empty`, `results=[]` |
| Worktree concurrente | no comprometido, `VERSION=1.0.0` | `status=ok`, árbol de llamadas completo (`amdgpu_vm_init @ amdgpu_vm.c:2608`, ...) |

**Conclusión:** los 2 fallos de `trace` los causa la **regresión en el
`tools/trace_path.py` comprometido @`53de009`** (`VERSION 1.1.0`, refactor
basado en `call_sites` que devuelve `List[Dict]`). La sesión concurrente
tiene en su árbol de trabajo (no comprometido) una vuelta a `VERSION 1.0.0`
(basado en `calls_in` que devuelve `Tuple[List,List,List]`) que sí produce el
árbol correcto. `git diff 53de009 -- tools/trace_path.py` muestra que la
versión comprometida **añade** `_STRING_LIT`, `_REF_ASSIGN`, `strip_strings()`
y `call_sites()`, y **elimina** `calls_in()`.

**Discriminante:** la misma fuente del corpus, la misma ausencia/presencia de
corpus, la misma corrección de infraestructura — el único variable que separa
`empty` de `ok` es el contenido de `trace_path.py`. Eso aísla la causa en la
capability `TRACE_CALL`, no en INFRA-001.

---

## 9. STOP_GATE

**`RXRE_TEST_INFRA_NOT_VALIDATED`**

La puerta exige: *la suite ejecuta desde un clean checkout **Y** las pruebas
relevantes pasan*.

- **La suite ejecuta desde un clean checkout: SÍ.** El `ModuleNotFoundError`
  desaparece; `test_rxre.py` corre sus 14 grupos. La corrección de
  infraestructura está **completa** para su propósito declarado
  (reproducibilidad del import).
- **Las pruebas relevantes pasan: NO.** 2 de 4 categorías fallan
  (`test_rxre.py`, `mutate_reg_resolve009`).

**Bloqueadores exactos (ambos preexistentes, ambos fuera de alcance):**

1. **`tools/trace_path.py` @`53de009` (TRACE_CALL, protegido).** Regresión
   `VERSION 1.1.0` que hace `trace amdgpu_vm_init` → `empty`. Causa 2 de los
   fallos de `test_rxre.py`. La corrección existe **solo** como cambio no
   comprometido de la sesión concurrente (vuelta a `VERSION 1.0.0`); no está
   en ningún commit y esta tarea no puede tocar `TRACE_CALL`.
2. **Corpus externo `RESEARCH/` no versionado.** Causa (a) 1 fallo de
   `test_rxre.py` (`search VM_CONTEXT0_CNTL`) cuando el corpus está ausente, y
   (b) el fallo de `mutate_reg_resolve009` (`FileNotFoundError` sobre
   `RESEARCH/working/linux-7.1.3`). El corpus es dato externo (no se
   versiona por diseño), y `RESEARCH/working/linux-7.1.3` está incompleto
   incluso cuando está presente.

**Por qué no `VALIDATED`:** contar el import exitoso como suite aprobada sería
exactamente la trampa que la puerta prohíbe ("no contar un import exitoso
como una suite aprobada"). Modificar `trace_path.py` para poner `test_rxre.py`
verde sería la otra trampa prohibida ("no modificar otras capabilities para
forzar el resultado"). La clasificación honesta es `NOT_VALIDATED`, con la
corrección de infraestructura registrada como **éxito parcial completo** y los
bloqueadores documentados con precisión.

**Contrato de desbloqueo (para que un futuro trabajo valide INFRA-001):**

- Cerrar la regresión de `TRACE_CALL` (comprometer la vuelta a `VERSION 1.0.0`
  o equivalente) **en su propia tarea**, no aquí.
- Decidir si `RESEARCH/` se versiona o se publica como artefacto externo con
  hash; mientras sea externo, `mutate_reg_resolve009` y el `search`
  corpus-dependiente no pueden pasar desde un clean checkout.

---

## 10. DECISION_LOG

| Decisión | Por qué | Evidencia | Alternativas rechazadas | Reversibilidad |
|---|---|---|---|---|
| Versión solo los 14 módulos de la clausura | Es el mínimo que hace que `test_rxre.py` importe; nada más es necesario | clausura de import real; `test_rxre002.py` importa `commands.*`/`api.request` | versionar `adapters/`, `storage/`, `fixtures/`, `RESEARCH/` (no están en la clausura / son datos) | reversible (commit aparte) |
| Corpus `RESEARCH/` NO versionado | Dato externo (~50 MB de fuentes del kernel), no módulo fuente del proyecto | `git ls-files RESEARCH/` = 0 ficheros | symlink, submódulo, git-lfs (añade dependencias de infraestructura) | n/a |
| `commands/` como paquete de espacio de nombres | No tiene `__init__.py`; válido en Python 3.3+ | inspección del árbol | añadir `__init__.py` (modifica semántica de la sesión concurrente) | reversible |
| Clasificación `NOT_VALIDATED` | La puerta exige que las pruebas relevantes pasan, y no pasan | §7, §8, §9 | `VALIDATED` (contaría el import como suite aprobada) | reversible (re-clasificar al cerrar los bloqueadores) |
| No tocar `trace_path.py` | `TRACE_CALL` protegido; la corrección es trabajo no comprometido de otra sesión | §8 (experimento 2) | aplicar la vuelta a `VERSION 1.0.0` aquí (robaría/forzaría el resultado) | n/a |
| Entregable `benchmark/*.md` no rastreado | Convención del proyecto: los informes `benchmark/` son ficheros no rastreados en el worktree principal | `git status --short -- benchmark/` (24 `??`) | confirmarlo en el fix (mezclaría informe con código) | reversible |

---

## 11. GLOBAL_WORK_SCAN

**Lo que se movió de estado:**

- `MISSING_TRACKED_SOURCE` → **resuelto** (los 14 módulos están versionados en
  `5e2b64f`; el `ModuleNotFoundError` desaparece).
- `RXRE_TEST_INFRA` → **NOT_VALIDATED** (puerta no cumplida; bloqueadores
  preexistentes documentados).

**Fronteras abiertas (registradas, NO iniciar):**

- `REGISTER_FIELDS_KEYING` — cómo se indexan los campos de registro por clave.
- `TRACE_DATA_INTEGRATION` — integrar los datos de traza (el `trace_path.py`
  comprometido es la punta de esta frontera).
- `RELATION` — identidad y semántica de las relaciones entre símbolos.
- `PROVENANCE` — cadena de provenance transitiva.
- `SEMANTICS` — validación de semántica de hardware (el `selftest` de
  `reg_resolve` declara explícitamente "NO valida semantica de hardware").

**Lo que NO se pudo hacer y por qué:**

- No se pudo poner `test_rxre.py` verde: el bloqueador es `trace_path.py`
  (`TRACE_CALL`, protegido) y su corrección vive en el árbol no comprometido
  de otra sesión.
- No se pudo pasar `mutate_reg_resolve009`: el corpus `RESEARCH/` es externo
  y `working/linux-7.1.3` está incompleto.
- No se ejecutó `FULL_REGRESSION`: solo las 4 categorías relevantes de FASE 5
  estaban en alcance.

**Próxima acción legítima (fuera de INFRA-001):** cerrar la regresión de
`TRACE_CALL` en su propia tarea (comprometer la vuelta a `VERSION 1.0.0` con
su propio hallazgo y validación), lo que desbloquearía 2 de los fallos de
`test_rxre.py` sin tocar la infraestructura.

**Frontera dura reafirmada:** esta tarea no tocó `0000:00:02.0`, `i915`,
`fb0`, ni la consola. No se declaró ningún dispositivo DRM que no sea
`0000:01:00.0`. Ninguna escritura de hardware ocurrió.
