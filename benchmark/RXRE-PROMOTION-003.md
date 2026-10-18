# RXRE-PROMOTION-003 — PROMOVER INFRAESTRUCTURA DE CHECKOUT LIMPIO

**Tarea:** promover a `main` los dos commits validados de la
infraestructura de pruebas y reparación de `TRACE_CALL`:

```text
5e2b64f  fix: make RXRE tests reproducible from clean checkout
9a31eaa  fix: restore trace call behavior in clean checkout
```

La secuencia se verificó por **ancestry** (`git show -s --format='%H %P'`),
no por mensajes de commit.

**STOP GATE: `RXRE_INFRA_TRACE_CALL_PROMOTED`**

Las 7 obligaciones se cumplen (ancestry verificada, commits auditados,
`main` avanzó al commit esperado, fixture independiente del corpus pasa,
pruebas de `TRACE_CALL` pasan, contrato `forward`/legacy cubierto,
worktree principal intacto).

---

## 1. REPOSITORY_BEFORE

| Magnitud | Valor |
|---|---|
| `ROOT` | `/home/lucas/Escritorio/rxre` |
| `MAIN_REF` (antes) | `53de0098f43d8ab8340603204675a1a2e0faabef` (el baseline conocido; **no** había avanzado) |
| `MAIN_WORKTREE` | `/home/lucas/Escritorio/rxre` |
| `MAIN_WORKTREE_BRANCH` | `migration/validated-legacy-work` |
| `MAIN_WORKTREE_HEAD` | `9ce74c53ba5a356fed9893c5f62b32e01f9d883a` |
| `MAIN_WORKTREE_STATUS_HASH` (antes) | `0e64b8f51985366df98d5c3b208ff2ba5a014f980cab286e4e43858465f554c8` |
| dirty (antes) | 235 (sesión concurrente activa) |

**Dato estructural decisivo:** `main` **no** está desprotegida en el
worktree principal. Está desprotegida (checked out) en
`/home/lucas/.rxre-wt/promotion-002` @ `53de009 [main]` (worktree de
RXRE-PROMOTION-002). Esto determina la mecánica del fast-forward (§5).

`git cat-file -t 5e2b64f` → `commit`; `git cat-file -t 9a31eaa` →
`commit`. Ambos existen.

---

## 2. COMMIT_AUDIT

### `5e2b64f` — 14 ficheros, 3317 inserciones

```text
tools/rxre/api/__init__.py                 0
tools/rxre/api/envelope.py               150
tools/rxre/api/request.py                431
tools/rxre/backends/__init__.py            0
tools/rxre/backends/adapters/__init__.py   0
tools/rxre/backends/adapters/rz_inspect.py 485
tools/rxre/backends/contract.py          327
tools/rxre/backends/decision.json         41
tools/rxre/backends/dispatch.py          388
tools/rxre/backends/registry.py          281
tools/rxre/cli.py                        216
tools/rxre/commands/handlers.py          467
tools/rxre/commands/query.py             526
tools/rxre/rxre                            5   (mode 100755)
```

**Versiona ÚNICAMENTE la dependencia transitiva** necesaria para ejecutar
la suite (`api`, `commands`, `backends`, `cli.py`, `rxre`). No incluye
`trace_path.py`, ni `relations.py`, ni `reg_resolve.py`, ni `findings`,
ni `REGISTER_FIELDS`.

### `9a31eaa` — 5 ficheros, 242 inserciones, 2 deletiones

```text
tools/rxre/commands/handlers.py            11 +-   (lee `forward` primero)
tools/rxre/core/engine.py                  10 +-   (_normaliza_paso lee `forward` primero)
.../trace-call-002/.../callgraph.c         13 ++   (fixture)
.../trace-call-002/.../amd_asic_type.h    14 ++   (enum mínimo)
tools/rxre/tests/test_trace_call_fixture002.py 196 ++
```

**Corrige la interpretación del contrato JSON del adaptador.** El motor
`trace_path.py` 1.1.0 emite el árbol bajo `forward`; el adaptador
(`handlers.trace`, `engine._normaliza_paso`) seguía leyendo
`chain`/`results`/`nodes` (claves de la 1.0.0). La reparación lee
`forward` primero y conserva fallback legacy:

```python
# handlers.py:313
res = (d.get("forward") or d.get("chain")
       or d.get("results") or d.get("nodes") or [])
# engine.py:226
for n in (d.get("forward") or d.get("results")
          or d.get("chain") or []):
```

**Verificaciones de alcance (vacío = no modificado):**

- `git diff 53de009..9a31eaa -- tools/trace_path.py` → **vacío**
  (ninguno de los dos commits modifica el motor para ocultar el fallo).
- `git diff 53de009..9a31eaa -- tools/rxre/core/relations.py
  tools/reg_resolve.py tools/rxre/tests/mutate_reg_resolve009.py` →
  **vacío** (REGISTER_IDENTITY, `relations.py`, findings, UUID intactos).
- `git ls-tree 5e2b64f tools/rxre/rxre` → `100755` (modo ejecutable
  conservado; en el fast-forward aparece `create mode 100755`).
- No hay cambios funcionales ajenos a los informes: el único fichero
  rastreado tocado por `9a31eaa` en lógica es `handlers.py`/`engine.py`
  (la línea del contrato); el resto es fixture + test.

---

## 3. ANCESTRY

Verificada por `git show -s --format='%H %P %s'` (no por mensajes):

```text
5e2b64f20962da0e8e3f695fdbd78247c0236d04  53de0098f43d8ab8340603204675a1a2e0faabef  fix: make RXRE tests reproducible from clean checkout
9a31eaa0d992fa4ec1bd6167aabf7e8cd29075de  5e2b64f20962da0e8e3f695fdbd78247c0236d04  fix: restore trace call behavior in clean checkout
```

- `parent(5e2b64f) = 53de009` (exacto).
- `parent(9a31eaa) = 5e2b64f` (exacto).
- Cadena **lineal**: `53de009 → 5e2b64f → 9a31eaa`
  (`git log --oneline --ancestry-path main..9a31eaa` → solo esos dos).
- `git merge-base --is-ancestor main 9a31eaa` → **SÍ**: `main` (53de009)
  es ancestro de `9a31eaa` → **fast-forward válido**, sin merge commit.
- `git merge-base 53de009 9ce74c5 = 9ce74c5` → `migration/validated-legacy-work`
  (la rama de la sesión concurrente) es **ancestro** del baseline `main`.
  Por tanto avanzar `main` a `9a31eaa` **no introduce divergencia**: la
  rama concurrente sigue siendo ancestro de `main` promovido (verificado
  después de la promoción: `git merge-base --is-ancestor 9ce74c5 main` → SÍ).

---

## 4. TESTS_BEFORE_PROMOTION

En un checkout limpio temporal basado en `9a31eaa`
(`/home/lucas/.rxre-wt/promotion-infra-003-validate`, detached, **sin
copiar archivos de ningún worktree concurrente**):

| Prueba | Exit | Resultado |
|---|---|---|
| `test_trace_call_fixture002.py` | 0 | `self-test OK: contrato de trace ... sobre fixture independiente` |
| `test_trace_callers002.py` | 0 | `RESULTADO: 0 fallos, 0 skips` |
| `trace_path.py --selftest` | 0 | `RESULTADO OK · vectores conocidos reproducidos` |
| `test_rxre.py` (con corpus) | 0 | `self-test OK (14 grupos …)` |

**Consultas obligatorias `gmc_v8_0` (provenance validada):**

FORWARD — `rxre trace gmc_v8_0_hw_init` → `status=ok`:
```text
gmc_v8_0_hw_init  CALLS  gmc_v8_0_gart_enable
  CALLEE_DEFINITION = gmc_v8_0.c:829
  CALL_SITE          = gmc_v8_0.c:1228
  RELATION_TYPE      = DIRECTA
```

INVERSE — `trace_path.py --callers-of gmc_v8_0_gart_enable` → `STATUS=RESOLVED`:
```text
gmc_v8_0_gart_enable  CALLED_BY  gmc_v8_0_hw_init
  RELATION_TYPE (edge) = CALLS
  direction (relation) = CALLED_BY
  CALLER_DEFINITION    = gmc_v8_0.c:1203
  CALLEE_DEFINITION    = gmc_v8_0.c:829
  CALL_SITE            = gmc_v8_0.c:1228
```

La provenance (`caller_definition`, `callee_definition`, `call_site`)
corresponde a las líneas reales del corpus y es coherente con el vector
de regresión de `test_trace_callers002.py` (`caller_definition
gmc_v8_0.c:1203`, `call_site gmc_v8_0.c:1228`).

**No se declaró `FULL_REGRESSION`**: no se ejecutó la suite completa de
220 herramientas; se ejecutaron las categorías aplicables a esta
promoción.

---

## 5. PROMOTION_WORKTREE

| Worktree | Commit | Rama | Función |
|---|---|---|---|
| `/home/lucas/.rxre-wt/promotion-infra-003` | `53de009` | `promote/infra-003` | worktree aislado creado desde el `main` actual (según el enunciado) |
| `/home/lucas/.rxre-wt/promotion-infra-003-validate` | `9a31eaa` | (detached) | checkout limpio temporal para la validación previa |
| `/home/lucas/.rxre-wt/promotion-002` | `53de009`→`9a31eaa` | `main` | worktree donde `main` está desprotegida (checked out) |

**Mecánica del fast-forward (decisión registrada):** `main` está
desprotegida en `promotion-002`, **no** en el worktree principal
(`Escritorio/rxre`, que está en `migration/validated-legacy-work`). Una
rama desprotegida solo puede avanzarse de forma **consistente**
(ref + índice + árbol de trabajo juntos, sin dejar el worktree huérfano
ni bloquear futuros checkouts de `main`) en el worktree donde está
desprotegida. Por tanto el fast-forward se ejecutó allí:

```text
git -C /home/lucas/.rxre-wt/promotion-002 merge --ff-only 9a31eaa
```

Salida: `Actualizando 53de009..9a31eaa / Fast-forward` —
**18 ficheros, 3558 inserciones, 1 deletion**; `create mode 100755
tools/rxre/rxre`. **Sin squash, sin reescritura de hashes, sin merge
commit innecesario, sin cherry-pick** (los commits ya están en la cadena
lineal).

`promotion-infra-003` (rama `promote/infra-003`) cumplió el rol de
worktree aislado de la promoción y de preparación; la validación se
ejecutó desde el checkout limpio `promotion-infra-003-validate` @ `9a31eaa`.
En ningún momento se tocó el worktree principal (`Escritorio/rxre`):
no `reset`, `clean`, `stash`, `checkout forzado`, `add` ni `commit`
sobre él.

---

## 6. MAIN_REF_BEFORE

```text
53de0098f43d8ab8340603204675a1a2e0faabef
```

(El baseline conocido. Verificado inmediatamente antes de la promoción:
`git rev-parse main` → `53de009…`; no había avanzado.)

## 7. MAIN_REF_AFTER

```text
9a31eaa0d992fa4ec1bd6167aabf7e8cd29075de
```

`main` avanzó al commit esperado. `git -C promotion-002 branch
--show-current` → `main`; `rev-parse HEAD` → `9a31eaa…`; `status` →
limpio (solo `?? benchmark/RXRE-PROMOTION-002.md`, entregable sin
rastrear, ajeno a la promoción).

Destino alcanzado:

```text
53de009
    |
    v
5e2b64f
    |
    v
9a31eaa
    |
    v
main
```

---

## 8. TESTS_AFTER_PROMOTION

En el commit promovido (`main @ 9a31eaa`, checkout limpio en
`promotion-002`, **sin copiar de ningún worktree concurrente**):

| Prueba | Exit | Resultado |
|---|---|---|
| `trace_path.py --selftest` | 0 | `RESULTADO OK · vectores conocidos reproducidos` |
| `test_trace_call_fixture002.py` | 0 | `self-test OK: contrato de trace … sobre fixture independiente` |
| `test_trace_callers002.py` | 0 | `RESULTADO: 0 fallos, 0 skips` |
| `test_rxre.py` (con corpus) | 0 | `self-test OK (14 grupos …)` |

Las pruebas aplicables se repitieron desde el checkout limpio del commit
promovido y pasan.

---

## 9. CLEAN_CHECKOUT

- La validación se ejecutó desde un **checkout limpio** de `9a31eaa`
  (`promotion-infra-003-validate`, detached), sin copiar archivos de
  ningún worktree concurrente.
- **Sin corpus externo** (`RESEARCH/` ausente, porque es dato externo no
  versionado por diseño): pasan las pruebas **independientes del corpus**
  (`test_trace_call_fixture002.py`, `trace_path --selftest`,
  `test_trace_callers002.py` — esta última resuelve el corpus por la
  ruta absoluta de laboratorio).
- **Con corpus** (symlink de solo lectura): pasa `test_rxre.py`
  (`self-test OK 14 grupos`). **Limitación documentada:** las pruebas
  dependientes del corpus (`test_rxre.py` sin `RESEARCH/`) necesitan el
  corpus externo; su ausencia **no** es un fallo de infraestructura
  (§"no interpretar los fallos dependientes del corpus como fallos de
  infraestructura").

---

## 10. MAIN_WORKTREE_INVARIANT

Capturados antes y después (`git rev-parse HEAD`, `git status --short`):

| Comprobación | Antes | Después de la promoción | Final (con este informe) |
|---|---|---|---|
| `HEAD` | `9ce74c5…` | `9ce74c5…` | `9ce74c5…` (**sin cambio**) |
| rama | `migration/validated-legacy-work` | idem | idem (**sin cambio**) |
| dirty | 235 | 235 | 236 (**+1, ver abajo**) |
| `STATUS_HASH` crudo | `0e64b8f5…f554c8` | `0e64b8f5…f554c8` | `780fd5d4…a620` |
| `STATUS_HASH` excl. este informe | `0e64b8f5…f554c8` | `0e64b8f5…f554c8` | `0e64b8f5…f554c8` (**idéntico**) |

**`MAIN_WORKTREE_MODIFIED = NO`.**

Medición precisa: la promoción en sí (el fast-forward de `main`) **no**
alteró el worktree principal — capturado inmediatamente después de la
promoción y antes de escribir este informe, `STATUS_HASH` era
`0e64b8f5…` con 235 entradas, **idéntico** al estado previo. El único
delta posterior es **exactamente una línea nueva sin rastrear**:
`?? benchmark/RXRE-PROMOTION-003.md` (este entregable; por convención
del proyecto los informes `benchmark/*.md` son entregables sin
rastrear). Al **excluir** esa única línea, el hash del estado vuelve a
`0e64b8f5…` — **idéntico** al estado previo. Los 235 cambios
concurrentes de la sesión (114 ficheros rastreados modificados + 121
sin rastrear) se conservan **exactamente**; esta tarea **no** modificó
ningún fichero rastreado ni ningún fichero de la sesión concurrente en
el worktree principal.

La rama principal de desarrollo (`migration/validated-legacy-work`) y sus
cambios concurrentes se conservan **exactamente**. Además, `9ce74c5`
sigue siendo ancestro de `main` promovido
(`git merge-base --is-ancestor 9ce74c5 main` → SÍ): la promoción **no**
introdujo divergencia respecto a la sesión concurrente. El fast-forward
avanzó **solo** la referencia `main`; no tocó `migration/validated-legacy-work`
ni el árbol de trabajo principal.

---

## 11. FINAL_CLASSIFICATION

**`RXRE_INFRA_TRACE_CALL_PROMOTED`**

Las 7 obligaciones del STOP GATE:

1. **ancestry verificada** — SÍ: `53de009 → 5e2b64f → 9a31eaa`, lineal,
   por `%H %P` (§3).
2. **commits auditados** — SÍ: `5e2b64f` versiona solo la dependencia
   transitiva; `9a31eaa` corrige el contrato JSON del adaptador (lee
   `forward`, conserva fallback legacy); ninguno modifica `trace_path.py`
   ni `relations.py` ni REGISTER_IDENTITY (§2).
3. **`main` avanzó al commit esperado** — SÍ: `53de009` → `9a31eaa`
   (§6, §7).
4. **fixture independiente del corpus pasa** — SÍ: antes (§4) y después
   (§8), exit=0.
5. **pruebas de `TRACE_CALL` pasan** — SÍ: `test_trace_callers002.py`
   `0 fallos, 0 skips`; `gmc_v8_0` forward e inversa con provenance
   correcta (§4).
6. **contrato `forward`/legacy cubierto** — SÍ: `d.get("forward")`
   primero + `d.get("chain")`/`results`/`nodes` como fallback (§2).
7. **worktree principal intacto** — SÍ: `MAIN_WORKTREE_MODIFIED = NO`;
   el `STATUS_HASH` crudo cambió **solo** por este entregable sin
   rastrear, y al excluirlo es **idéntico** al estado previo; `HEAD`
   y rama sin cambio (§10).

**Limitación abierta (no es de esta tarea):** las pruebas dependientes del
corpus necesitan `RESEARCH/` (dato externo no versionado por diseño). Sin
él, `test_rxre.py` (sin corpus) reporta las 3 fallas dependientes del
corpus; **no** es un fallo de infraestructura de la promoción.

---

## 12. GLOBAL_WORK_SCAN

**Lo que se movió de estado:**

- `main`: `53de009` → **`9a31eaa`** (fast-forward lineal).
- `TRACE_CALL` en `main`: **promovido** (la regresión de
  `RXRE-INFRA-002` y la reproducibilidad de `RXRE-INFRA-001` son ahora
  parte de `main`).

**No se implementó nada nuevo.** Esta tarea es una promoción de refs, no
desarrollo de capacidades.

**Fronteras abiertas (registradas, NO iniciar):**

- `TRACE_DATA_INTEGRATION` — integrar datos de traza (acceso READ/WRITE
  a registros). La sesión concurrente ya añade un adaptador `trace_data`
  (no comprometido); no es de esta tarea.
- `REGISTER_FIELDS_KEYING` — cómo se indexan los campos de registro por
  clave.
- `RELATION` — identidad y semántica de las relaciones entre símbolos.
- `PROVENANCE` — cadena de provenance transitiva.
- `SEMANTICS` — validación de semántica de hardware.

**Frontera dura reafirmada:** esta tarea **no** tocó `0000:00:02.0`, `i915`,
`fb0` ni la consola. Ningún dispositivo DRM distinto de `0000:01:00.0`.
Ninguna escritura de hardware. La única ref modificada fue `main`
(fast-forward a `9a31eaa`); el worktree principal y la rama concurrente
quedaron intactos.
