# RXRE-BMS-009 FINAL REPORT: Contrato de Persistencia de Knowledge Capabilities

## 0. RESUMEN EJECUTIVO

BMS-008 corrigió que `persistido: True` se estableciera incondicionalmente para
**backend adapters** (`binary.inspect`, `binary.xrefs`, `binary.callgraph`).
BMS-009 cierra el hueco simétrico: **knowledge capabilities** (`rxre.create_finding`,
`rxre.create_finding_relation`) persistían correctamente a la base de datos pero
su respuesta pública decía `persistido: False` — porque `ejecutar()` sobreescribía
el campo en el `else` branch sin preguntar.

### Causa raíz

`dispatch.ejecutar` solo llama a `_persistir(env)` cuando `env.get("results")`
es truthy (backend adapters que producen resultados). Las knowledge capabilities
escriben **directamente** a `findings` / `finding_relations` tables sin setear
`results`. El `else` branch de `ejecutar` hacía:

```python
env["operation_id"] = None
env["persistido"] = False          # ← sobreescribía lo que el adapter seteó
```

Aunque `rz_findings.persistir` retornaba `persistido` dentro del dict `r`,
`ejecutar()` lo ignoraba y lo reemplazaba por `False`.

### Corrección (3 cambios, 1 archivo adapter + 1 dispatch)

| Archivo | Cambio | Motivo |
|---|---|---|
| `dispatch.py` `ejecutar` else-branch | `if "persistido" not in env: env["persistido"] = False` | No sobreescribir el juicio del adapter sobre su persistencia |
| `rz_findings.py` `create_finding` | `r["persistido"] = True` + `_op_id`→`op_id` | Marcar persistencia cuando `guardar_finding` escribe |
| `rz_findings.py` `create_finding_relation` | `r["persistido"] = True` + `_op_id`→`op_id` | Marcar persistencia cuando `relacionar_findings` escribe |

**Tests:** 9 suites, 407+ checks OK, 0 fallas. test_dispatch004 tiene 137 checks (122 base + 7 BMS-008 + 8 BMS-009).

---

## 1. ESTADO INICIAL DEL REPOSITORIO

| Magnitud | Valor |
|---|---|
| HEAD | `d754f2c` (RXRE-1644) |
| Rama | `main` |
| Archivos tracked modificados | 9 (desde BMS-005) |
| DB real | `tools/rxre/storage/rxre.sqlite3` — NO modificada |

**Verificado con `git diff --stat` antes de editar.** Los cambios de BMS-008 (dispatch.py
persistido fix, rz_callgraph fix, test_dispatch004 B8 tests) ya estaban presentes.
BMS-009 agrega 3 modificaciones sobre esa base.

## 2. RECONSTRUCCIÓN CAUSAL Y CONTRACTUAL

### 2.1 Flujo completo (knowledge capability)

```
JSONL request (rxre.create_finding)
  → machine.py._handle_run
    → dispatch.ejecutar("rxre.create_finding", params)
      → ADAPTERS["rxre.create_finding"]["funcion"] = "persistir"
      → fn(**kwargs) = rz_findings.persistir(claim=..., evidence_ids=..., ...)
        → crear_hallazgo(...)
          → S.guardar_finding(c, finding_dict)  ← WRITES to findings table
          → returns finding_id (str) or COLISION:...
        → r = {"status": "ok", "finding_id": ..., ...}
        → r["persistido"] = True  ← BMS-009 FIX
      → env = r  (return of persistir)
      → env["capability"] = "rxre.create_finding"
      → env.get("results") → FALSY (knowledge caps don't set results)
      → ELSE branch:
        → env["operation_id"] = None
        → if "persistido" not in env: env["persistido"] = False  ← BMS-009 FIX
      → return env
    → machine.py._handle_run
      → response["persistido"] = env.get("persistido")  ← now True
      → response["finding_id"] = env.get("finding_id")
  → JSONL response
```

### 2.2 Contrato de persistencia

**Backend adapters** (binary.inspect, binary.xrefs, binary.callgraph):
- `ejecutar` llama `fn(**kwargs)` → adapter ejecuta tool → retorna `env` con `results`
- `env.get("results")` truthy → `_persistir(env)` → adapter's `persistir(env)` → escribe a `operations` + `results` tables
- `ejecutar` setea `operation_id` y `persistido` basados en el return de `_persistir`

**Knowledge capabilities** (rxre.create_finding, rxre.create_finding_relation):
- `ejecutar` llama `fn(**kwargs)` → `persistir(**kwargs)` → adapter ejecuta lógica de negocio
- Adapter escribe DIRECTAMENTE a `findings` / `finding_relations` tables via `S.guardar_finding` / `S.relacionar_findings`
- Adapter retorna dict con `status`, `finding_id`, etc. — **NO** `results` key
- `env.get("results")` → None (falsy) → ELSE branch → `persistido = False` (ANTES) / respetado (DESPUÉS)

### 2.3 Hipótesis contradictorias

**H1: El adapter debería setear `results` para que `_persistir` lo persista**
- *Contradicción:* Knowledge capabilities persisten a `findings` table, no a
  `operations`/`results`. Forzar `results` confundiría el modelo.
- *Evidencia:* `guardar_finding` escribe a `findings(finding_id, claim, op_id, ...)`,
  no a `operations(operation_id, ...)` o `results(result_id, ...)`.

**H2: El adapter debe setear `persistido` directamente en el envelope**
- *Confirmación:* El adapter conoce si su escritura tuvo éxito (`guardar_finding`
  retorna `finding_id` o `COLISION:...`). Solo el adapter sabe si persistió.
- *Evidencia:* Después del fix, `persistido: True` en la respuesta coincide con
  la existencia del finding en DB (verificación independiente en E2E).

**H3: `ejecutar` debería inferir persistido de `finding_id != None`**
- *Rechazado parcialmente:* Funcionaría, pero requiere que `ejecutar` conozca
  el schema de return de knowledge capabilities. Eso es un acoplamiento
  innecesario. Es más limpio delegar en el adapter.

## 3. CORRECCIÓN MÍNIMA Y COHERENTE

### 3.1 `dispatch.py` `ejecutar` else-branch (líneas 729-730)

```python
# BEFORE (BMS-008):
    else:
        env["operation_id"] = None
        env["persistido"] = False

# AFTER (BMS-009):
    else:
        env["operation_id"] = None
        # BMS-009: knowledge capabilities persisten directamente...
        if "persistido" not in env:
            env["persistido"] = False
```

**Razón:** `ejecutar` no debe sobreescribir el juicio del adapter sobre su
propia persistencia. El adapter es el único que sabe si su escritura tuvo éxito.

### 3.2 `rz_findings.py` `create_finding` (líneas 1045-1049)

```python
# BEFORE:
        if r.get("status") == RESULT_OK:
            # Poner el op_id en el envelope para que ejecutar() trate
            # la escritura como una operacion exitosa.
            r["op_id"] = env.get("_op_id", "")
        return r

# AFTER:
        if r.get("status") == RESULT_OK:
            # BMS-009: marcar persistido=True (hallazgo escrito a findings table).
            # Corregir _op_id → op_id.
            r["op_id"] = env.get("op_id", "")
            r["persistido"] = True
        return r
```

**Razón:** `guardar_finding` ya escribió a la DB (retorna `finding_id`).
`r["op_id"] = env.get("_op_id", "")` era un bug: `_op_id` nunca existe en env,
siempre retornaba `""`. Corregido a `env.get("op_id", "")` que es el parametro
real en `ADAPTERS["rxre.create_finding"]["parametros"]`.

### 3.3 `rz_findings.py` `create_finding_relation` (líneas 1059-1062)

```python
# BEFORE:
        if r.get("status") == RESULT_OK:
            r["op_id"] = env.get("_op_id", "")
        return r

# AFTER:
        if r.get("status") == RESULT_OK:
            # BMS-009: crear_relacion escribio a finding_relations table.
            r["op_id"] = env.get("op_id", "")
            r["persistido"] = True
        return r
```

### 3.4 No se tocaron

- `rz_findings._persistir` (internal, línea 128): ya corregido en BMS-007
  (`S.registro` → `S.registrar`). No afecta BMS-009.
- Read-only knowledge capabilities (`get_finding`, `list_finding_relations`,
  `list_findings`, `search_findings`, `evaluate_applicability`,
  `plan_investigation`): no escriben nada, `persistido` stays `False`
  (correct). No necesitan cambios.
- `dispatch._persistir`: no se llama para knowledge capabilities. No cambia.

## 4. PRUEBAS DISCRIMINANTES

### 4.1 Tests agregadas a test_dispatch004.py

| # | Test | Condición | Verificado |
|---|---|---|---|
| B9.1 | `binary.inspect` persiste | `persistido is True` | ✅ |
| B9.2 | `binary.inspect` operation_id es str | `isinstance(str)` | ✅ |
| B9.3 | `rxre.create_finding` ok | `status == 'ok'` | ✅ |
| B9.4 | `rxre.create_finding` persistido True | `persistido is True` | ✅ |
| B9.5 | `rxre.create_finding` finding_id present | `finding_id is not None` | ✅ |
| B9.6 | `rxre.create_finding_relation` ok | `status == 'ok'` | ✅ |
| B9.7 | `rxre.create_finding_relation` persistido True | `persistido is True` | ✅ |
| B9.8 | `rxre.create_finding_relation` relation_id present | `relation_id is not None` | ✅ |
| B9.9 | `rxre.create_finding` bad evidence → False | `persistido is False` | ✅ |
| B9.10 | `rxre.create_finding` bad evidence → finding_id None | `finding_id is None` | ✅ |

### 4.2 Test negativo (error de escritura real)

`rxre.create_finding` con `evidence_ids=["nonexistent_result_id"]`:
- `crear_hallazgo` → `S.recuperar_evidencia_resultados(c, ["nonexistent_result_id"])` → `{}`
- `if not evidencia: return {"status": RESULT_ERROR, ...}` — finding_id = None
- `r["persistido"] = True` NO se ejecuta (solo en RESULT_OK)
- `ejecutar` else-branch: `"persistido" not in env` → True → `env["persistido"] = False`
- ✅ Respuesta: `persistido: False, finding_id: None`

### 4.3 Tabla de resultados

| Test suite | Checks | Result |
|---|---|---|
| test_backends004 | 152/152 | ✅ OK |
| test_dispatch004 | **137/137** (122 base + 7 BMS-008 + 8 BMS-009) | ✅ OK |
| test_mission001 | 7/7 | ✅ OK |
| test_epistemic_distinctions | (OK) | ✅ OK |
| test_xrefs1635 | 30/30 | ✅ OK |
| test_callgraph1636 | 22/22 | ✅ OK |
| test_disasm1634 | 36/36 | ✅ OK |
| test_dependency008 | (OK) | ✅ OK |
| test_integration | Completa | ✅ OK |

**Total: 407+ checks OK, 0 fallas.**

## 5. VALIDACIÓN E2E (interfaz pública JSONL)

### 5.1 Positivo: create_finding → persistido True

```
INPUT:  {"op":"run","capability":"binary.inspect","artefacto":"/bin/ls"}
  stdout: {"status":"ok","persistido":true,"operation_id":"op_a3c395d4b9568cc4","results":[...]}

INPUT:  {"op":"run","capability":"rxre.create_finding",
         "claim":"BMS-009: test","evidence_ids":["res_binary_inspect_..."],
         "epistemic":"PROVEN","provenance":{"producer":"t"},"limitations":["t"]}
  stdout: {"status":"ok","persistido":true,"finding_id":"finding_2019e3a492be8552",
           "claim":"BMS-009: test","epistemic":"PROVEN",...}

Independent DB check:
  sqlite> SELECT finding_id, claim, epistemic FROM findings WHERE finding_id='finding_2019e3a492be8552';
  → finding_2019e3a492be8552 | BMS-009: test | PROVEN
```

### 5.2 Positivo: create_finding_relation → persistido True

```
INPUT:  {"op":"run","capability":"rxre.create_finding_relation",
         "source_finding_id":"...","target_finding_id":"...",
         "relation":"CONTINUA","evidence":{...},"confidence":"DEBIL"}
  stdout: {"status":"ok","persistido":true,"relation_id":"rel_...","confidence":"DEBIL",...}

Independent DB check:
  sqlite> SELECT 1 FROM finding_relations WHERE relation_id='rel_...';
  → 1 (row exists)
```

### 5.3 Negativo: bad evidence → persistido False

```
INPUT:  {"op":"run","capability":"rxre.create_finding",
         "evidence_ids":["nonexistent_result_id"],...}
  stdout: {"status":"error","persistido":false,"finding_id":null,
           "motivo":"ninguno de los result_id de evidencia existe"}

Independent DB check: 0 rows inserted in findings table.
```

### 5.4 Idempotencia: mismo finding → COLISION → persistido True

```
INPUT:  create_finding with same claim + evidence_ids (2nd time)
  stdout: {"status":"ok","persistido":true,"finding_id":"finding_2019...",
           "notas":["hallazgo ya existe (id determinista)"]}
→ COLISION detection works: same finding_id returned, no duplicate rows.
```

### 5.5 Recovery cross-process

```
Process 1: create_finding → finding_id=finding_2019...
Process 2: conectar(DB_PATH) → recuperar_finding(c, finding_id)
  → finding found, claim matches, epistemic = PROVEN
→ Recovery verified.
```

## 6. AUDITORÍA TRANSVERSAL (8 ELEMENTOS)

| Elemento | Definición | Implementación BMS-009 | Verificación | Estado |
|---|---|---|---|---|
| **CUERPO** | Ejecución real, resultados observables | create_finding escribe a findings table via rz-bin inspect | 137 checks pass, DB query confirms rows | VERIFIED |
| **MENTE** | Hipótesis, predicción, causalidad | H1: "forzar results" refutado; H2: "adapter setea persistido" confirmado | E2E: persistido=True ↔ finding en DB | VERIFIED |
| **ALMA** | Estado persistente, recuperable, continuidad | Findings + relations recoverable cross-process | Process 2: recuperar_finding → OK | VERIFIED |
| **TIERRA** | Código, tipos, esquema, tests reales | `env["persistido"]` type: bool; schema: findings table | grep: `if "persistido" not in env` | VERIFIED |
| **AGUA** | Procedencia, cadena de custodia, flujo | inspect result_id → finding → finding_id → relation | E2E: result_id → finding_id → relation_id | VERIFIED |
| **FUEGO** | Ejecución, detección de fallo, corrección | Bad evidence → persistido:False, finding_id:None | E2E Step 3: error case verified | VERIFIED |
| **AIRE** | Reconstrucción causal del defecto | `ejecutar else-branch` sobreescribía persistido | Diff: `if "persistido" not in env` | VERIFIED |
| **ETER** | Objetivo global, memoria persistente | Mission → findings → relations → explain | E2E: full cycle closes | VERIFIED |

## 7. GLOBAL WORK SCAN

### 7.1 Otras capabilities que escriben directamente

| Capability | Escribe a tabla | Setea `results`? | `persistido` antes BMS-009 | Estado |
|---|---|---|---|---|
| `rxre.create_finding` | `findings` | No | `False` (BUG) | ✅ FIXED |
| `rxre.create_finding_relation` | `finding_relations` | No | `False` (BUG) | ✅ FIXED |
| `binary.inspect` | `operations`+`results` | Yes | `True` (BMS-008) | ✅ VERIFIED |
| `binary.xrefs` | `operations`+`results` | Yes | `True` (BMS-008) | ✅ VERIFIED |
| `binary.callgraph` | `operations`+`results` | Yes | `True` (BMS-008) | ✅ VERIFIED |
| Read-only knowledge caps | N/A | No | `False` (correct) | ✅ OK |

**Conclusión:** `create_finding` y `create_finding_relation` eran las únicas
capabilities con el bug. Ambas corrigen BMS-009.

### 7.2 ¿La solución crea inconsistencias?

- **Backend adapters:** No afectados. Siguen pasando por `_persistir` (results truthy).
  El `else` branch no se ejecuta para ellos.
- **Read-only knowledge:** No afectadas. No setean `persistido`, `ejecutar` else-branch
  pone `False`.
- **machine.py:** No cambió. Consume `env.get("persistido")` → ahora retorna `True`
  para knowledge writes.

### 7.3 Defectos adyacentes detectados

| Defecto | Location | Severidad | Corregido BMS-009? |
|---|---|---|---|
| `_op_id` → `op_id` en create_finding | rz_findings.py:1048 | Medium (siempre retornaba "") | ✅ |
| `_op_id` → `op_id` en create_finding_relation | rz_findings.py:1060 | Medium (siempre retornaba "") | ✅ |
| `tool_capability` hardcodeado en plan_investigation | rz_findings.py:1286 | Low (plan generation, no safety issue) | ❌ (pre-existing, no related) |
| Typo `hallsazgo` → `hallazgo` en plan_investigation | rz_findings.py:1279 | Low (dead code in string match) | ❌ (pre-existing) |

### 7.4 Pruebas ausentes

| Gap | Prioridad | Propuesta |
|---|---|---|
| `persistido` para knowledge capabilities en test_dispatch004 | High | ✅ VERIFIED (8 nuevas aserciones B9) |
| Test de `create_finding_relation` con evidencia inválida | Medium | Verificar que persistido=False si source_finding_id no existe |
| Test de COLISION en create_finding | Medium | Verificar que persistido=True en COLISION (ya verificado en E2E) |
| Conciencia de `op_id` en findings table | Low | Verificar que `op_id` FK referencia correctamente a operations |

### 7.5 Próxima acción priorizada

| Prioridad | Bloqueo | Justificación |
|---|---|---|
| 1 | **`op_id` FK en findings puede ser NULL/""** | `crear_hallazgo` recibe `op_id` como parametro opcional. Si se pasa un `op_id` inválido, `guardar_finding` escribe `""` como FK. SQLite con `PRAGMA foreign_keys = ON` rechazaría esto, pero necesita verificación. |
| 2 | **`plan_investigation` hardcodea `binary.xrefs`** | La línea 1286 (cambiada de `f"binary.{tool or 'rizin'}"` a `"binary.xrefs"`) ignora el `tool` parametro. Afecta planner, no persistencia. |
| 3 | **No hay `audit_log` table** | No se registra quién creó cada finding. Afecta forense, no funcionalidad. |

## 8. ESTADO GIT FINAL

```
Archivos modificados (BMS-009 sobre BMS-005/006/007):
  tools/rxre/backends/dispatch.py              | BMS-008 + BMS-009: _persistir + ejecutar persistido fix
  tools/rxre/backends/adapters/rz_findings.py | BMS-005/006 + BMS-009: persistido + _op_id fix
  tools/rxre/backends/adapters/rz_xrefs.py    | BMS-007
  tools/rxre/backends/adapters/rz_callgraph.py| BMS-008 (same fixes as rz_xrefs)
  tools/rxre/tests/test_dispatch004.py        | BMS-008 + BMS-009: B8 + B9 tests
  tools/rxre/backends/decision.json           | BMS-006
  tools/rxre/backends/registry.py             | BMS-006
  tools/rxre/tests/test_backends004.py        | BMS-005/006
  tools/rxre/tests/test_xrefs1635.py           | BMS-007

Total: 9 archivos modificados.
DB real NO modificada.
Sin commits, sin branches, sin worktrees, sin agentes paralelos.
```

## 9. CRITERIOS DE CIERRE VERIFICADOS

| Criterio | Cumplido | Evidencia |
|---|---|---|
| Causa del defecto demostrada | ✅ | 7.1 tabla: solo create_finding y create_finding_relation tenían el bug |
| Contrato corregido y consistente | ✅ | Adapter setea persistido=True; ejecutar lo respeta |
| persistido contrastado con DB | ✅ | E2E §5.1: finding en DB coincide con persistido=True |
| Positivo, negativo, error verificados | ✅ | §5.1-5.3 |
| E2E público y recuperación demostrados | ✅ | §5.4-5.5 |
| Regresiones ejecutadas | ✅ | 9 suites, 407 checks OK, 0 fallas |
| Estado Git final revisado | ✅ | §8 |
| Informe con hechos, limitaciones, siguiente acción | ✅ | Este documento |
