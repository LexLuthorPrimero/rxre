# RXRE-INFRA-002 — RESTAURAR TRACE_CALL EN CHECKOUT LIMPIO

**Tarea:** reparar la regresión de `TRACE_CALL` descubierta en
RXRE-INFRA-001. La suite ya importa desde un checkout limpio
(`5e2b64f`), pero dos pruebas de tracing fallan con el corpus
Linux 7.1.3.

**STOP GATE: `TRACE_CALL_CLEAN_CHECKOUT_RESTORED`**

Las 8 obligaciones se cumplen (reproducción, causa, preservación,
fixture desde checkout limpio, `test_trace_callers002.py`, pruebas
de tracing previamente fallidas con corpus, provenance, worktree
principal intacto). Limitación documentada: las pruebas
dependientes del corpus necesitan `RESEARCH/` (dato externo, no
versionado por diseño). El fallo de `mutate_reg_resolve009`
(REGISTER_IDENTITY) es **preexistente** y **fuera de alcance**
(REGISTer_IDENTITY protegido, corpus `working/` incompleto).

---

## 1. REPOSITORY_STATE

| Magnitud | Valor |
|---|---|
| `REPO_ROOT` | `/home/lucas/Escritorio/rxre` |
| `BASELINE_COMMIT` | `5e2b64f` (existe; ancestro incluye `53de009`) |
| `BASELINE_PARENT` | `53de009` |
| `MAIN_REF` | `main` @ `53de009`; worktree principal @ `9ce74c5` [`migration/validated-legacy-work`] |
| `CURRENT_WORKTREE` | `/home/lucas/.rxre-wt/trace-call-clean-fix-002` |
| `CURRENT_BRANCH` | `fix/trace-call-clean-checkout` |
| `DIRTY_STATE` (principal) | 234 ficheros (sesión concurrente activa) |

Worktree aislado creado desde `5e2b64f` con `-b
fix/trace-call-clean-checkout`. No se tocó el worktree principal
( sin reset/clean/stash/checkout forzado). El fix es el commit
`9a31eaa` (ver §12).

---

## 2. FAILURE_REPRODUCTION (FASE 1)

**Producer:** worktree limpio de `5e2b64f`, sin corpus y con
corpus (symlink de solo lectura a
`/home/lucas/Escritorio/rxre/RESEARCH`).

**`python3 tools/rxre/tests/test_rxre.py`:**

| Entorno | Exit | Resultado |
|---|---|---|
| sin corpus | 1 | `self-test FALLA (3)` |
| con corpus | 1 | `self-test FALLA (2)` |

**Las dos pruebas concretas que fallan CON corpus** (identificadas
por su línea en `test_rxre.py`, no por el conteo):

1. **Línea 303-306** — `trace de un simbolo real da ok con
   resultados`:
   ```python
   _r, e_ok_trace = jrun(["trace", "amdgpu_vm_init"])
   v("trace de un simbolo real da ok con resultados",
     e_ok_trace.get("status") == E.ST_OK and bool(e_ok_trace.get("results")),
     (e_ok_trace.get("status"), len(e_ok_trace.get("results", []))))
   ```
   Detalle del fallo: `('empty', 0)` — `status=empty`, 0 resultados.

2. **Línea 307-310** — `el simbolo real trae su ubicacion`:
   ```python
   v("el simbolo real trae su ubicacion",
     any(x.get("loc") and x["loc"] != "-" for x in e_ok_trace.get("results", [])
         if isinstance(x, dict)),
     [x.get("loc") for x in e_ok_trace.get("results", []) if isinstance(x, dict)][:2])
   ```
   Detalle del fallo: `[]` — ningún resultado tiene `loc`.

Ambas usan la MISMA consulta: `jrun(["trace", "amdgpu_vm_init"])`
→ CLI `rxre trace amdgpu_vm_init`.

**`python3 tools/rxre/tests/test_trace_callers002.py`:**
`RESULTADO: 0 fallos, 0 skips`, exit=0. **Pasa.**

**La tercera falla (sin corpus)** — `search VM_CONTEXT0_CNTL (0
res)` — es dependiente del corpus (desaparece con él); no es de
`TRACE_CALL`.

---

## 3. VERSION_COMPARISON (FASE 2)

Misma consulta, mismo corpus, mismo contexto:
`trace_path.py --from amdgpu_vm_init --kernel
<kernelbuild/linux-7.1.3> --depth 3 --json`.

| | `trace_path.py` versionado (`5e2b64f`) | `trace_path.py` concurrente (no comprometido) |
|---|---|---|
| `VERSION` | `1.1.0` | `1.0.0` |
| sha256 | `99a52434…d0185c9d23` | `9966817b…614305` |
| líneas | 1608 | 1174 |
| clave de salida | `out["forward"]` (L1202), `out["callers"]` (L1204) | `"results": results` (L892) |
| `forward` presente | SÍ | NO |
| `results` presente | NO | SÍ |

- `VERSIONED_BEHAVIOR`: emite el árbol bajo `forward`. Llamado
  **directamente**, devuelve el árbol completo (`amdgpu_vm_init`
  @ `amdgpu_vm.c:2608`, 15 hijos, con `loc`, `call_site`,
  `verdict`, `AMBIGUOUS_SYMBOL`, `PARCIAL`).
- `CONCURRENT_BEHAVIOR`: emite el árbol bajo `results`. Llamado
  por la CLI, devuelve `status=ok` (porque `handlers.trace`
  lee `results`).
- `QUERY_INPUT`: `--from amdgpu_vm_init --kernel <kernelbuild>
  --depth 3 --json`.
- `CORPUS_INPUT`:
  `/home/lucas/Escritorio/rxre/RESEARCH/kernelbuild/linux-7.1.3`.
- `OUTPUT_SCHEMA`: versionado =
  `{tool, version, chip, chip_value, forward[, callers]}`;
  concurrente = `{tool, version, chip, chip_value, ficheros_indexados,
  results, root}`.
- `CALL_GRAPH_RESULTS`: **el mismo árbol** por ambas versiones;
  solo difiere la **clave** que lo contiene.

**No se asume que la versión modificada es correcta por devolver
no-vacío.** La comparación muestra que la diferencia es de
**contrato de salida** (clave), no de contenido: el árbol es
idéntico.

---

## 4. ROOT_CAUSE (FASE 3)

**Clasificación: `OUTPUT_SCHEMA`** (diferencia de contrato entre
herramientas). No es `ARGUMENT_CONTRACT`, `CORPUS_SELECTION`,
`ENUM_RESOLUTION`, `FUNCTION_RESOLUTION`, `CALLSITE_EXTRACTION`,
`GRAPH_CONSTRUCTION`, `GRAPH_TRAVERSAL` ni `OTHER`.

**Camino completo inspeccionado:**

```text
CLI  rxre trace amdgpu_vm_init
  ↓  cli.py:206  -> handlers.HANDLERS["trace"](args)
argument parsing   (handlers.trace, _b_trace)
  ↓  _b_trace -> ["--from", target, "--kernel", _kernelbuild(), "--depth", "3", "--json"]
corpus resolution  (_kernelbuild() = ROOT/RESEARCH/kernelbuild/linux-7.1.3)
  ↓  subprocess: trace_path.py --from ... --json
enum/chip resolution  (resolve_enum_definition -> CHIP_POLARIS12=17)
  ↓
function definitions  (Index._scan -> by_name["amdgpu_vm_init"])
  ↓
call-site extraction  (call_sites(body))
  ↓
graph construction  (Index.reverse: callee -> [{caller, call_site, kind=DIRECT}])
  ↓
graph traversal  (expand: forward tree con depth/budget)
  ↓
output serialization  trace_path.py: out["forward"] = results   <-- 1.1.0
  ↓
_ _raw_json = {"tool":..., "version":"1.1.0", "forward":[...]}
  ↓
deserialización  handlers.py:305  res = d.get("chain") or d.get("results") or d.get("nodes")
  ↓  ^^^^ todas None con 1.1.0  ->  res=[]
envelope  status=ST_EMPTY, results=[]      <-- EL FALLO
```

**La rotura está en la deserialización del adaptador**, no en
`trace_path.py`. Evidencia reproducible:

1. `trace_path.py --from amdgpu_vm_init` **directo** → árbol
   completo bajo `forward` (la herramienta **no** está rota).
2. `rxre trace amdgpu_vm_init` → `status=empty`, `results=[]`,
   **pero** `_raw_json.forward` contiene el árbol completo.
   El árbol **se produce**; el adaptador **no lo extrae**.

**`status=empty` NO se interpreta como ausencia de llamadas**: el
árbol está en `_raw_json.forward`; `empty` es un fallo de
traducción del adaptador.

**Las pruebas fallidas ejercitan una interfaz DISTINTA de la que
cubre `test_trace_callers002.py`:**

- `test_rxre.py` → **CLI** `rxre trace` → `handlers.trace` →
  `_b_trace` → `trace_path.py --from` → **`handlers` deserializa
  `_raw_json`** (aquí está el fallo).
- `test_trace_callers002.py` → **subprocess directo**
  `trace_path.py --callers-of gmc_v8_0_gart_enable` → emite
  `callers` → **el TEST lo parsea él mismo** (no pasa por
  `handlers`/`engine`). Por eso `test_trace_callers002` **pasa**
  aunque `handlers` esté roto: **no ejercita el adaptador
  roto**.

**No se atribuye a `call_sites`/`calls_in`/enum/parser/corpus**:
`trace_path.py` funciona directamente; el corpus resuelve el enum;
el parser indexa `amdgpu_vm_init`. La causa es la clave de
deserialización.

---

## 5. MINIMAL_FIX (FASE 4)

Se repara **únicamente la causa** (la clave de deserialización) en
los dos consumidores del árbol, conservando compatibilidad hacia
atrás:

**`tools/rxre/commands/handlers.py`** (determina el envelope de la
CLI):
```python
res = (d.get("forward") or d.get("chain")
       or d.get("results") or d.get("nodes") or [])
```

**`tools/rxre/core/engine.py`** (`_normaliza_paso`, para los
pipelines `symbol.callers` / `symbol.callgraph` que componen
`trace`):
```python
for n in (d.get("forward") or d.get("results")
          or d.get("chain") or []):
    if isinstance(n, dict):
        res.extend(N.de_arbol_trace(n))
```

**Se lee `forward` primero** (la clave que `trace_path.py` 1.1.0
emite para `--from`) y **se conservan `chain`/`results`/`nodes`**
como compatibilidad con herramientas que aún emiten la forma
vieja (1.0.0).

**Capacidades promovidas de `TRACE_CALL` conservadas** (no se
restaura la 1.0.0, que eliminaría las mejoras validadas de la
1.1.0 — 1608 vs 1174 líneas):

`CALLERS_OF`, `FROM`, `CALLS`/`CALLED_BY`, `AMBIGUOUS_SYMBOL`,
`PROVENANCE`, `TRANSITIVE_PROVENANCE`, `DEPTH_BOUND`,
`NODE_BOUND`, `TIME_BOUND`, `LAZY_MACRO_EXPANSIONS`,
`INVERSE_CALL_GRAPH` — verificadas por `test_trace_callers002.py`
(0 fallos, 0 skips) y por las consultas `gmc_v8_0` (§6).

**No se duplica el motor de tracing**: se corrige el adaptador
(`handlers`/`engine`), no se añade un segundo motor ni se
revierte `trace_path.py`.

**Alcance (exacto):** 2 ficheros rastreados modificados
(`handlers.py`, `engine.py`) + fixture + test. **No** se tocó
`trace_path.py`, `relations.py`, `REGISTER_IDENTITY`
(`reg_resolve.py`, `mutate_reg_resolve009.py`), `REGISTER_FIELDS`,
`findings` ni `UUID`.

---

## 6. CALL_GRAPH_VALIDATION (FASE 6, consultas obligatorias)

**FORWARD** — `rxre trace gmc_v8_0_hw_init` (CLI, con corpus):
`status=ok`, 1 resultado. En el árbol:
```text
gmc_v8_0_hw_init  CALLS  gmc_v8_0_gart_enable
  callee loc      = gmc_v8_0.c:829     (CALLEE_DEFINITION)
  call_site       = gmc_v8_0.c:1228    (CALL_SITE)
```

**INVERSE** — `trace_path.py --callers-of gmc_v8_0_gart_enable`
(con corpus): `status=RESOLVED`, relaciones:
```text
gmc_v8_0_gart_enable  CALLED_BY  gmc_v8_0_hw_init
  edge       = CALLS
  call_site  = gmc_v8_0.c:1228
gmc_v8_0_hw_init  CALLED_BY  gmc_v8_0_resume
  edge       = CALLS
  call_site  = gmc_v8_0.c:1259
```

**Provenance correcta** (corresponde a líneas reales del corpus,
coherente con `test_trace_callers002.py`):
`caller_definition gmc_v8_0.c:1203`, `callee_definition
gmc_v8_0.c:829`, `call_site gmc_v8_0.c:1228`.

---

## 7. FIXTURE_TESTS (FASE 5)

**Fixture mínimo, independiente del corpus Linux**
(`tools/rxre/tests/fixtures/trace-call-002/`):

```text
drivers/gpu/drm/amd/callgraph.c      # void callee(void) L6; void caller(void) L10; callee(); L12
include/drm/amd_asic_type.h          # enum amd_asic_type { CHIP_POLARIS12, /* 17 */ };
```

El `.c` vive bajo `drivers/gpu/drm/amd/` porque `trace_path.py`
indexa por defecto `<kernel>/drivers/gpu/drm/amd` (L980). El enum
es el contexto mínimo que `trace_path` requiere: sin él responde
`rc=2` ("CHIP_POLARIS12 no esta en include/drm/amd_asic_type.h").

**Test** `tools/rxre/tests/test_trace_call_fixture002.py` (31
aserciones, 3 caminos, ejecuta el `trace_path.py` **real**, sin
simular ni falsear):

- **Camino 1** directo `--from caller`: caller, callee, CALL_SITE,
  CALLER_DEFINITION, CALLEE_DEFINITION, RELATION_TYPE (`DIRECTA`),
  `verdict=NO_CONDICIONAL`.
- **Camino 2** inverso `--callers-of callee`: `STATUS=RESOLVED`,
  `edge=CALLS` (RELATION_TYPE), `relation=CALLED_BY`,
  CALLER_DEFINITION L10, CALLEE_DEFINITION L6, CALL_SITE L12.
- **Camino 3** `handlers.trace` + pipeline `symbol.callgraph`
  (apuntando el corpus al fixture): `STATUS=ok`, resultados no
  vacíos, CALLER/CALLEE_DEFINITION, CALL_SITE, RELATION_TYPE,
  etapa `callchain` aporta nodos normalizados.

**Detector de regresión (demostrado):** sobre `5e2b64f` **sin el
fix**, el test **FALLA** (8 aserciones: `handler.STATUS=ok ::
empty`, `pipeline` vacío, …) mientras los caminos 1-2 (directos)
**pasan**. Con el fix: **31 OK, 0 fallos**. El fallo se detecta
por el camino 3 (handler/pipeline), que es exactamente el adaptador
roto.

---

## 8. CORPUS_TESTS (FASE 6, corpus real Linux 7.1.3)

| Prueba | Exit | Resultado |
|---|---|---|
| `test_trace_callers002.py` | 0 | `RESULTADO: 0 fallos, 0 skips` |
| `rxre trace gmc_v8_0_hw_init` (forward) | 0 | `gmc_v8_0_gart_enable @ gmc_v8_0.c:829 call_site=gmc_v8_0.c:1228` |
| `trace_path.py --callers-of gmc_v8_0_gart_enable` (inversa) | 0 | `CALLED_BY gmc_v8_0_hw_init edge=CALLS call_site=gmc_v8_0.c:1228` |
| `trace_path.py --selftest` | 0 | `RESULTADO OK · vectores conocidos reproducidos` |

Corpus: `/home/lucas/Escritorio/rxre/RESEARCH/kernelbuild/linux-7.1.3`
(completo; tiene `include/drm/amd_asic_type.h`). El corpus
`working/linux-7.1.3` está incompleto (solo `include/linux/`) y
**no** se usa para `trace` (`_b_trace` apunta a `kernelbuild`).

---

## 9. GENERAL_SUITE (FASE 6)

| Prueba | Exit | Resultado |
|---|---|---|
| `test_rxre.py` (con corpus) | 0 | `self-test OK (14 grupos …)` — **las 2 fallas de tracing desaparecen** |
| `test_rxre.py` (sin corpus) | 1 | `FALLA (3)` — dependientes del corpus (ver §10) |
| `reg_resolve.py --selftest` | 0 | `RESULTADO OK` (REGISTER_IDENTITY, inafectado) |
| `mutate_reg_resolve009.py` | 2 | `FAILED (errors=1)` — **preexistente**, ver abajo |

**`mutate_reg_resolve009` (REGISTER_IDENTITY) falla por causa
ajena a este fix:** necesita `RESEARCH/working/linux-7.1.3`, que
está incompleto (solo `include/linux/`), así que `chosen` es
`None`. Este fallo **ya existía en `5e2b64f`** (medido en
RXRE-INFRA-001, antes de cualquier cambio de esta tarea) y **no**
es de `TRACE_CALL`. Esta tarea **no** modifica
`REGISTER_IDENTITY` (prohibido), así que el fallo permanece y se
registra como limitación abierta, no como regresión de este fix.

**`FULL_REGRESSION` NO se declara**: solo se ejecutaron las
categorías de FASE 6 (fixture, trace_call, general_suite,
regresion gmc_v8_0, register_identity). No se ejecutó la suite
completa de 220 herramientas.

---

## 10. CLEAN_CHECKOUT_VALIDATION (FASE 7)

**Segundo worktree limpio** desde el commit del fix
(`/home/lucas/.rxre-wt/infra002-clean-validate` @ `9a31eaa`,
detached). **Sin copiar archivos de ningún worktree concurrente.**

- **El fix forma parte del commit**: `get("forward")` está presente
  en `handlers.py` y `engine.py` en el checkout limpio (no es un
  cambio local sin seguimiento).
- **Sin corpus** (`RESEARCH/` ausente, porque es dato externo no
  versionado):
  - `test_trace_call_fixture002.py` → **PASS** (exit=0): demuestra
    que la funcionalidad de tracing general funciona **sin** el
    corpus Linux, sobre el fixture.
  - `trace_path.py --selftest` → **PASS**.
  - `test_trace_callers002.py` → **PASS** (0 fallos, 0 skips;
    resuelve el corpus por la ruta absoluta de laboratorio).
  - `test_rxre.py` → **FALLA (3)**: las 3 fallas son
    **dependientes del corpus** (`search VM_CONTEXT0_CNTL`, `trace
    amdgpu_vm_init`, `ubicacion`). **Limitación documentada**: el
    corpus `RESEARCH/` es dato externo, no versionado por diseño,
    así que las pruebas que lo necesitan no pueden pasar en un
    checkout limpio sin él.
- **Con corpus** (symlink de solo lectura): `test_rxre.py` →
  **`self-test OK (14 grupos)`**, exit=0. Las pruebas de tracing
  previamente fallidas **pasan con el corpus correspondiente**.

---

## 11. MAIN_WORKTREE_INVARIANT

| Comprobación | Valor |
|---|---|
| HEAD del worktree principal | `9ce74c5` (**sin cambios**) |
| rama | `migration/validated-legacy-work` (**sin cambios**) |
| staged (índice) | vacío (**nada staged por esta tarea**) |
| `MAIN_WORKTREE_MODIFIED` | **NO** |

El worktree principal sigue siendo el de la sesión concurrente.
Sus `handlers.py:305` y `engine.py:219` **todavía leen
`chain`/`results`** (versión sin arreglar de la sesión
concurrente): el fix **no** se escribió en el worktree principal.
El fix existe **solo** en el commit `9a31eaa` y en los worktrees
aislados de esta tarea. La sesión concurrente arregla el mismo
sintoma por otra vía (mantiene `trace_path.py` en 1.0.0, que emite
`results`); esta tarea elige la vía que **preserva la 1.1.0**
(arreglar el adaptador), como manda el enunciado.

---

## 12. COMMIT

| Magnitud | Valor |
|---|---|
| `COMMIT` | `9a31eaa` |
| `PARENT` | `5e2b64f` |
| `BRANCH` | `fix/trace-call-clean-checkout` |
| `WORKTREE` | `/home/lucas/.rxre-wt/trace-call-clean-fix-002` |
| `FILES_CHANGED` | 5 (242 insertiones, 2 deletiones) |

Ficheros:
```text
M  tools/rxre/commands/handlers.py                              (+11/-1)
M  tools/rxre/core/engine.py                                    (+10/-1)
A  tools/rxre/tests/fixtures/trace-call-002/drivers/gpu/drm/amd/callgraph.c
A  tools/rxre/tests/fixtures/trace-call-002/include/drm/amd_asic_type.h
A  tools/rxre/tests/test_trace_call_fixture002.py
```

Mensaje: `fix: restore trace call behavior in clean checkout`.
Sin cherry-pick, sin promover a `main`.

---

## 13. FINAL_CLASSIFICATION

**`TRACE_CALL_CLEAN_CHECKOUT_RESTORED`**

Las 8 obligaciones del STOP GATE:

1. **Regresión reproducida antes del fix** — SÍ: sobre `5e2b64f`,
   `test_rxre.py` falla (2 con corpus) y el fixture test falla (8
   aserciones en handler/pipeline).
2. **Causa localizada** — SÍ: `OUTPUT_SCHEMA`, el adaptador
   deserializa `chain`/`results`/`nodes` pero `trace_path.py`
   1.1.0 emite `forward` (§4).
3. **La corrección preserva las capacidades validadas** — SÍ:
   `test_trace_callers002.py` pasa (0 fallos, 0 skips);
   compatibilidad hacia atrás con las claves viejas; no se
   restaura la 1.0.0 (§5).
4. **El fixture pasa desde un checkout limpio** — SÍ: en
   `infra002-clean-validate` @ `9a31eaa`, sin corpus, exit=0 (§10).
5. **`test_trace_callers002.py` pasa** — SÍ (§8).
6. **Las pruebas de tracing previamente fallidas pasan con el
   corpus** — SÍ: `test_rxre.py` `self-test OK (14 grupos)` con
   corpus (§9, §10).
7. **La provenance se mantiene correcta** — SÍ: `gmc_v8_0`
   `call_site=gmc_v8_0.c:1228`, definiciones en sus líneas reales
   (§6).
8. **No se alteró el worktree principal** — SÍ: `MAIN_WORKTREE_
   MODIFIED = NO` (§11).

**Limitación abierta (no es de esta tarea):** las pruebas
dependientes del corpus (`test_rxre.py` sin `RESEARCH/`, y
`mutate_reg_resolve009` con `working/` incompleto) necesitan el
corpus externo. `RESEARCH/` es dato externo no versionado por
diseño; `working/linux-7.1.3` está incompleto. El fallo de
`mutate_reg_resolve009` es **preexistente** y **fuera de alcance**
(`REGISTER_IDENTITY` protegido).

---

## 14. GLOBAL_WORK_SCAN

**Lo que se movió de estado:**

- `TRACE_CALL` (clean checkout): `REGRESSED` → **`RESTORED`**
  (`9a31eaa`).
- `test_rxre.py` tracing: `FAIL` → **`PASS`** (con corpus).
- `symbol.callers` / `symbol.callgraph` (pipelines): normalizaban
  0 nodos → **normalizan el árbol completo** (engine.py).

**Fronteras abiertas (registradas, NO iniciar):**

- `TRACE_DATA_INTEGRATION` — integrar datos de traza (READ/WRITE
  acceso a registros). El concurrente ya añade un adaptador
  `trace_data` (no comprometido); no es de esta tarea.
- `REGISTER_FIELDS_KEYING` — cómo se indexan los campos de registro
  por clave.
- `RELATION` — identidad y semántica de las relaciones entre
  símbolos.
- `PROVENANCE` — cadena de provenance transitiva.
- `SEMANTICS` — validación de semántica de hardware.

**Lo que NO se hizo y por qué:**

- No se restauró `trace_path.py` 1.0.0: eliminaría las mejoras
  validadas de la 1.1.0 (AMBIGUOUS_SYMBOL con candidatos, esquema
  `forward`/`callers`, 1608 vs 1174 líneas).
- No se duplicó el motor de tracing: se corrigió el adaptador.
- No se tocó `REGISTER_IDENTITY`/`REGISTER_FIELDS`/`relations.py`/
  `findings`/`UUID` (prohibido).
- No se declaró `FULL_REGRESSION` (no se ejecutó la suite completa).

**Frontera dura reafirmada:** esta tarea no tocó `0000:00:02.0`,
`i915`, `fb0` ni la consola. Ningún dispositivo DRM distinto de
`0000:01:00.0`. Ninguna escritura de hardware.
