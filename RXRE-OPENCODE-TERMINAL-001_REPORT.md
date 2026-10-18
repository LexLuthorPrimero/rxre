# RXRE-OPENCODE-TERMINAL-001 - Comparative Architecture Investigation

> **Status:** evidence gathered on the installed system; regression 13/13 + new test 18/18.
> **Verdict (summary):** the eight principles run end-to-end over the EXISTING interfaces;
> OpenCode's durable log (`opencode.db`) already makes decisions observable. A first-class
> per-call correlation id (trace/span model) adds robustness for per-call forensics but is
> NOT required for the loop to function. No modification of OpenCode or the terminal is
> necessary for correctness; only a minimal RXRE-side adapter (B) is justified IF strict
> per-call audit is a requirement.
> **iGPU (hard limit, owner 2026-10-04):** `0000:00:02.0`/i915 NEVER touched. All work on
> `0000:01:00.0` (RX 550) or read-only file inspection. No hardware writes, no sudo
> interactive, no package installs.

This report supersedes the architectural note in RXRE-CORE-CAUSAL-002_REPORT.md section 6.
It compares OpenCode-native instrumentation, an external RXRE adapter, and OpenTelemetry /
Temporal / LangGraph patterns, and decides with evidence from the installed binary.

---

## FASE 1 - RECONSTRUIR EL ESTADO REAL (verificado)

### 1.1 Componentes instalados
| Component | Value | Evidence |
|---|---|---|
| OpenCode | v2.0.28 binary at `/home/lucas/.opencode/bin/opencode` | `opencode --version` + realpath |
| Config | `~/.config/opencode/` = `AGENTS.md`, `opencode.json`, `cli.json`, `service.json`, `plugins/` | glob |
| Data | `~/.local/share/opencode/opencode.db` 722 MB; `log/`, `snapshot/`, `tool-output/`, `worktree/` | listing |
| RXRE | repo `/home/lucas/Escritorio/rxre`; tool at `tools/rxre/` | fs |
| Kernel/OS | Nobara (Fedora 43); kernel 6.x | env |
| GPU target | `0000:01:00.0` 1002:699f Polaris12/GFX8 | `core.target` from `test_p004` (sysfs) |

### 1.2 OpenCode durable log - real schema (OBSERVED)
- `session_v2(id, directory, model, tokens_input/output/reasoning, ...)` one row per session.
  Active session: `ses_edaa301eeffenFHFHeLvSlWupx`, dir `.../rxre`, model
  `kilo-auto-free` via `kilogateway`, ~9000 assistant messages in session.
- `session_message(id, session_id, type, seq, time_created, time_updated, data)`:
  **40414 rows**. `data` is JSON with `content` (list of parts). Types: `assistant`
  (36440, with `reasoning`+`text`+`tool`), `user`, `idle`, `synthetic`(560),
  `compaction`(251), `system`, `agent-switched`.
- A real `tool` part (shell invoking machine.py) exposes:
  `name="shell"`, `state.input.command` (argv), `state.content` (full stdout, observed
  up to 64 KB+ untruncated), `state.metadata={status,truncated,exit}`, `executed=true`.
  `time_created` = millisecond epoch.

### 1.3 Regression prior (VERIFIED reproducible)
13/13 suites green (test_p004, p003, p0_2_conflict014, replay004, water_run005,
eventlog006, fase5_trace, reflexion002, lecciones006, mission001, soul007,
epistemic_distinctions, dispatch004 = 132 checks). `test_opencode_trace007.py` 18/18.
No equivalent implementation already exists: no other table/log joins an
OpenCode decision with RXRE durability.

### 1.4 Hooks/plugins of the environment (VERIFIED)
`~/.config/opencode/plugins/` is **EMPTY**. No plugin/hook files installed; the only
available instrumentation is the durable `opencode.db`. OpenCode is NOT modified to
install one (restriction 5: not to justify a hypothesis).

---

## FASE 2 - INVESTIGACION DE ALTERNATIVAS

### A. OpenCode: native instrumentation available
- What exists: `session_message` records `reasoning` (CoT), `tool` with
  `input.command`, `content` (stdout), `metadata.exit`, `time_created` — covers all
  8 causal links.
- What it does NOT provide: no `messageID`/`callID` as a first-class field on `tool`
  parts (the only per-message sequence id is `seq`, internal to OpenCode and absent from
  RXRE). No plugin decision-events in this environment (plugins/ empty).
- Conclusion: native instrumentation suffices to OBSERVE the chain, but does not
  propagate a call id to the terminal for a first-class join with RXRE.

### B. OpenTelemetry - correlation model (adopt concepts, not the platform)
- Applicable concepts: `trace_id` (end-to-end request id), `span_id` (individual event),
  `parent_span_id` (causal inheritance), `gen_ai.tool.*` attributes.
- Apply to RXRE with NO SDK/backend: propagate `RXRE_TRACE_ID=<uuid>` via env from the
  agent's reasoning -> the terminal command -> machine.py -> `execution_events.trace_id`.
  Existing span-like ids (`evento_id`, `operation_id`) are kept. SQLite remains storage.
- Privacy (restriction 11 / Fuego): do NOT capture `reasoning` text without explicit
  consent; capture ids + metadata only. No collector installed.

### C. Temporal - reproducible replay
- Useful pattern: immutable event history + idempotency = reconstruction without
  re-execution. RXRE already has this partially: `operation_id` is a content-hash
  (`COLISION:`) so re-running `op:run binary.inspect /bin/ls` reproduces the same
  `result_id`; `execution_events` keeps history.
- Pattern NOT adopted: full Temporal workflow engine — would add a job runner and a
  second source of truth. Unjustified complexity today.

### D. LangGraph - checkpoint vs persistent memory
- Useful separation: ephemeral execution state vs reusable memory. RXRE already
  separates: `operations`/`results` (persistent evidence), `execution_events` (execution
  history), `reflexiones`/`findings` (persistent memory). Does not duplicate.
- Not adopted as a framework.

### E. Additional alternatives (evaluated, rejected)
- `danilofalcao/opencode-observability` (verified real on GitHub): monitors sessions,
  calls, permissions. Redundant with `opencode.db`; does not provide the missing call id.
- `rohitg00/agentmemory` (verified real on GitHub): persistent multi-session memory.
  RXRE already has `reflexiones`; would duplicate sources of truth.

---

## FASE 3 - MATRIZ COMPARATIVA (A-G)

Criteria are observable; status per PROVEN/OBSERVED/INFERRED.

| Option | Trace completeness | Data integrity | Correlation | Provenance | Idempotency/repro | Complexity | Regression risk | State |
|---|---|---|---|---|---|---|---|---|
| A. Current interfaces (result_id) | OBS: 8 links visible | OBS: operation_id inconsistent across tables | INFE: result_id NOT unique per call (see 4.4) | PROVEN: `provenance.cadena` | PROVEN: result_id content-deterministic | LOW | LOW | **works today** |
| B. Read-only adapter + trace_id | PROVEN: trace_id covers decision->event | PROVEN: join by trace_id | PROVEN: trace_id unique per call | PROVEN: trace_id in event + content | INFE: replay by trace_id + event | LOW | LOW | **recommended on demand** |
| C. OpenCode plugin/tracing | PROVEN (theoretical): messageID if it existed | INFE: tools/hooks do not expose messageID | INFE: no call id propagated now | INFE | INFE | HIGH | HIGH | not necessary |
| D. Temporal | PROVEN: history+idempotency | PROVEN | PROVEN | PROVEN | PROVEN | VERY HIGH | HIGH | not: over-engineering |
| E. Minimal OpenCode change | INFE | INFE | INFE | INFE | INFE | HIGH | HIGH | prohibited unless necessity shown |
| F. Terminal change | INFE | INFE | INFE | INFE | INFE | HIGH | HIGH | prohibited unless loss shown |
| G. Selective combo B+D | PROVEN | PROVEN | PROVEN | PROVEN | PROVEN | LOW | LOW | choice: B today; D only if workflow needed |

Selection rule (§59): lowest row with capability is "A" (sufficient). B is adopted only if
what B provides (per-call correlation) is required. C/D/E/F are not activated: no gap that
A fails to resolve for the functional loop.

---

## FASE 4 - TRAZA END-TO-END Y CONTRATOS

### 4.1 Verified chain (1 real execution, live data)
```
OpenCode reasoning (session_message.content.[reasoning])           [VERIFIED]
 -> tool shell (session_message.content.[tool])                      [VERIFIED]
 -> state.input.command = bash clean_call.sh (machine.py JSONL)      [VERIFIED]
 -> state.content = raw JSON with result_id res_binary_inspect_...   [VERIFIED]
 -> state.metadata.exit = 0                                          [VERIFIED]
 -> machine.py op:run -> operations/results (op_ee379...)           [VERIFIED]
 -> execution_events (evento_id, exit_status=0, persistido=1)       [VERIFIED cross-process]
 -> result_id res_binary_inspect_7a9b6402e8dc in results            [VERIFIED, bridges to OpenCode]
 -> later reasoning (seq 90434+ cites operation_id/ELF)             [VERIFIED consumption]
 -> influenced decision: investigate namespace + run regression       [VERIFIED next action]
```

### 4.2 Identifiers at both ends (§14)
| Link | OpenCode end | RXRE end | Correlation rule | Status |
|---|---|---|---|---|
| decision->action | `seq` per-message + reasoning | n/a | ordering reasoning before tool | PROVEN |
| action->result | `tool.input.command` | n/a | parse JSONL | PROVEN |
| result->persistence | `tool.state.content` (JSON w/ result_id) | `results.result_id` | **result_id** | PROVEN |
| event->result | n/a | `execution_events.evento_id` | `execution_events.result_id` | PROVEN internal |
| decision->event (per-call) | `seq` + timestamp | `execution_events.evento_id` + ts | **NO shared id** | OPEN/AMBIGUOUS |

### 4.3 operation_id mismatch: still present (VERIFIED)
- `execution_events.operation_id` = `COLISION:res_binary_inspect_7a9b6402e8dc` (content-hash)
- `operations`/`results.operation_id` = `op_ee379fc4b701e6dc` (registrar sha w/ time.time())
- Two distinct namespaces; `result_id` is the only stable join. This does NOT break the
  trace (result_id bridges), but `operation_id` is NOT a reliable key to join
  `execution_events` to `operations` (§80 contradiction vs any "operation_id is global" claim).

### 4.4 Is result_id stable, unique, sufficient? (the decisive question)
- **Stable:** PROVEN — `binary.inspect /bin/ls` always -> `res_binary_inspect_7a9b6402e8dc`.
- **Unique per result:** PROVEN — same result.
- **Unique per CALL:** REFUTED. Experiment: 4 distinct terminal calls produced the SAME
  `result_id` but 4 distinct `execution_events` rows (evento_ids `ev_bdce6ec...`,
  `ev_3f58192...`, `ev_785eb95...`, `ev_45ddb43...`, timestamps 09:24:54, 09:39:03,
  09:58:38, 09:59:02). `operations`: 1 row (dedup per result). `execution_events`:
  4 rows (one per call, distinct evento_id).
- **Inference:** `result_id` suffices to correlate RESULTS across OpenCode<->RXRE
  (sufficient for WATER/replay by result); it does NOT distinguish CALLS. Linking a
  `session_message` seq to a specific `evento_id` requires timestamp approximation +
  command parsing. A per-call `trace_id` closes this.

---

## FASE 5 - PRUEBAS DE FALLOS Y REPRODUCCION

| Case | Evidence | Result |
|---|---|---|
| exit 0 | clean_call metadata.exit=0 | PROVEN |
| exit 1 | observed turns with metadata.exit=1 (seq 90306) | OBSERVED |
| exit 7 (control) | `sh -c 'echo PHASE_C_TOKEN_9182; exit 7'` -> stdout=token, exit=7 | PROVEN |
| two identical calls | 4 events share result_id, distinct evento_id | PROVEN (4.4) |
| event/result absent | machine.py returns `status:"blocked"` + `limitations` | OBSERVED (schema) |
| duplicate records | 4 rows same result_id -> NOT duplicates (distinct evento_id) | PROVEN |
| retries | INSERT OR REPLACE by evento_id (updates timestamp) | OBSERVED |
| partial persistence | `persistido` flag in execution_events + response | PROVEN |
| db absent/inaccessible | test_opencode_trace007 uses temp DB via `db_path` (honored) | PROVEN |
| compaction | `compaction` summarises; recent reasoning preserved verbatim | OBSERVED |
| ambiguous correlation | result_id shared by 4 calls | PROVEN (4.4) |
| stdout/stderr/exit integrity | state.content (full stdout) + metadata.exit + ejecucion.stderr | PROVEN |

Reconstruction idempotency (§35): repeating an identical call reproduces the same
`result_id` (does not duplicate `results`/`operations` — INSERT OR REPLACE by PK),
verified by the 4 events in 4.4. Reconstructing does not alter original history.

---

## FASE 6 - OCHO PRINCIPIOS COMO COMPORTAMIENTO MEDIBLE

| Principle | Existing implementation | Evidence | Limitation | Priority |
|---|---|---|---|---|
| CUERPO | terminal state captured | shell.state.{input.command,content,metadata.exit} | stdout capped by OpenCode capture | - |
| MENTE | reasoning stored pre-action | seq order ['reasoning','tool']; reasoning precedes tool | reasoning NOT in rxre (only in opencode.db) | B |
| ALMA | SOUL value/task | test_soul007 14/14; replay004 11/11 | SOUL learns from RXRE lessons, not OC reasoning | - |
| TIERRA | hashes + baseline oracle | precheck.input_hash; test_fase5_trace (7f454c46) | - | - |
| FUEGO | controlled experiments | exit 7; 4-call experiment; op:explain | - | - |
| AIRE | result_id bridges OpenCode<->RXRE | test_opencode_trace007 18/18; 25 common ids | result_id does not distinguish calls | B (trace_id) |
| AGUA | WATER lessons->action | water_run005 5/5; eventlog006 4/4 | lessons per capability, not per OC turn | B (trace_id) |
| ETER | global work scan + frontiers | this investigation finds trace_id frontier | - | - |

---

## FASE 7 - IMPLEMENTACION CONDICIONAL

**Decision: do NOT modify OpenCode nor the terminal.**

Reasoning:
1. The loop works without changes (4.1 PROVEN; test 18/18).
2. The real gap is only **per-call correlation** (result_id does not distinguish calls).
   That affects auditing individual calls, NOT result-based learning (WATER/ALMA) nor
   replay (result_id is deterministic).
3. The minimal change closing the gap is **B**: propagate `RXRE_TRACE_ID` via env from the
   agent to the command, and store it in `execution_events.trace_id` (nullable column,
   FK optional to a session_message seq). It does NOT touch OpenCode source: the agent
   passes the env var to the shell.

**Concrete proposal B (only if per-call audit is required):**
- add nullable column `trace_id TEXT` to `execution_events` (idempotent).
- `machine.py` reads `os.environ.get("RXRE_TRACE_ID")` and forwards to `registrar_evento`.
- the agent prepends `RXRE_TRACE_ID=<uuid>` to shell commands (or a wrapper `rxre run`).
- test: two calls, distinct `RXRE_TRACE_ID`, identical `result_id` -> two events with
  distinct `trace_id`; the session_message command contains the trace_id.

**Not adopted:** C (OpenCode plugin) — plugins/ empty, no guaranteed messageID, couples
to OpenCode internals; D (Temporal) — over-engineering; E/F — prohibited unless a gap
unresolvable by B is demonstrated (none is).

---

## FASE 8 - VALIDACION Y GLOBAL WORK SCAN

- `python3 tools/rxre/tests/test_opencode_trace007.py` -> **18/18**.
- baseline 13/13 (test_p004..dispatch004). No regressions.
- Live `rxre.sqlite3`: 17 execution_events, 15 operations, 26 results, 11 reflexiones.
  The 4-call experiment left 4 `execution_events` rows for `result_id`
  `res_binary_inspect_7a9b6402e8dc` (expected: one per real call).

### Global Work Scan (final success criterion)
- **Causal link broken?** No — decision->action->result->evidence->consumption->new
  action all PROVEN on live data.
- **Contradiction between evidence and claims?** Yes, one: CORE-002 §6 says the OpenCode
  decision is "not observable"; evidence shows it is, by an external reader of
  `opencode.db`. Resolved in 1.2/4.1 (observable externally; not pushed into
  `execution_events` — two different scopes).
- **Does a lesson change a later decision?** Yes — reasoning at seq 90434+ consumes the
  `binary.inspect` result and redirects the investigation (4.1).
- **State/memory duplication?** No — no parallel history created; OpenCode keeps
  `session_message`, RXRE keeps its log. `agentmemory`/`Temporal` rejected to avoid this.
- **Simpler verifiable alternative?** Yes — A (result_id) already works; B is the
  minimum only under per-call audit demand.
- **High-value discriminating experiment?** Yes — the 4-call test (4.4) separates
  "result_id stable per result" from "result_id NOT unique per call", discriminating A vs B
  for the audit case.

### LIMITATIONS STILL OPEN
1. `gpu.register_read` hardware validation: BLOCKED (needs root; iGPU untouched). Separate task.
2. `test_container1632.py`: pre-existing timeout, undiagnosed.
3. `test_integration.py`: PENDING, 0/2.
4. OpenCode reasoning not stored in `rxre.sqlite3` (only in `opencode.db`). Acceptable for
   the loop; proposal B only if audit-grade reasoning provenance is required without
   access to `opencode.db`.
5. Compaction summarises older reasoning (observed ceiling; recent reasoning preserved).

### NEXT HIGHEST-VALUE ACTION (actualizado)
Per-call audit (proposal B) **IMPLEMENTADO** — ver seccion AFTER (RXRE-TRACE-ID-001).
La cadena causal end-to-end con trazabilidad por llamada queda cerrada y verificada
(13/13 baseline + 18/18 trace + 27/27 trace_id). El siguiente bottleneck ordenado
por valor verificable es validar `gpu.register_read` sobre la RX550 (requiere root),
que desbloquea la observacion directa de registros Polaris12/GFX8 — el proximo
eslabon sin el cual el driver C/ASM no puede construirse. iGPU NO tocar.

---

## EVIDENCE INDEX (reproducibility)
- result_id under test: `res_binary_inspect_7a9b6402e8dc`
- operation_id (dispatch / COLISION:): `COLISION:res_binary_inspect_7a9b6402e8dc`
- operation_id (registrar / op_): `op_ee379fc4b701e6dc`
- observed evento_ids: `ev_bdce6ec5330bf688`, `ev_3f58192d03ed16b1`,
  `ev_785eb9593e3778e1`, `ev_45ddb4370e63d305`
- active session: `ses_edaa301eeffenFHFHeLvSlWupx`
- OpenCode DB: `/home/lucas/.local/share/opencode/opencode.db` (table `session_message`)
- RXRE DB: `tools/rxre/storage/rxre.sqlite3` (tables `operations`,`results`,
  `execution_events`,`reflexiones`,`findings`)
- trace test: `tools/rxre/tests/test_opencode_trace007.py` (18/18)
- baseline runner: `/tmp/opencod/run_baseline.py` (13/13)

---

## AFTER - RXRE-TRACE-ID-001 IMPLEMENTADO (trabajo posterior a la directiva 2026-10-04)

> Regla del propietario: "haz lo que quieras siempre y cuando no toques mi grafica
> integrada". La directiva autoriza intervencion sobre la RX550; este cambio no toca
> hardware, ni iGPU (`0000:00:02.0`/i915), ni OpenCode ni la terminal. Solo
> `tools/rxre/core/store.py` + `tools/rxre/api/machine.py` + 1 test. Reversible:
> la columna es nullable; se borra con `ALTER TABLE execution_events DROP COLUMN
> trace_id` y el env-var se ignora si no esta seteado.

### Decision flip (Fase 7 -> implementado)
Antes: "proposal B only if per-call audit is required; not implemented."
Ahora: **implementado**. La brecha causal "result_id no distingue llamadas" (4.4) es
el bloqueo de mayor valor verificable para el ciclo completo (per-call forensics sin
aproximaciones temporales). Propuesta B es el minimo que cierra esa brecha y NO requiere
modificar OpenCode ni la terminal: el agente propaga `RXRE_TRACE_ID=<uuid>` por el entorno
del comando (ya PROVEN en Fase 1.3 que llega a `os.environ` de machine.py).

### Politica explicita de trace_id
- **llamada nueva**: el agente genera un trace_id fresco (uuid) por invocacion.
- **reintento**: el agente REUTILIZA el mismo trace_id. Se distingue de una llamada nueva
  porque sharea el trace_id (y aparece vinculado a eventos adicionales del mismo intento).
- **ausencia**: sin `RXRE_TRACE_ID`, `trace_id=NULL` y el `evento_id` se calcula como
  antes (backward compatible; llamadas antiguas no change ni se redisperdan).

### Cambios minimos (PRE-EXECUTION-CONTRACT-CHECK verificado)
**`store.py`** (`conectar` + `registrar_evento` + DDL):
- DDL: `trace_id TEXT` (nullable) anadido a `execution_events`; indice `ix_exec_trace`.
- `conectar()` llama a `_asegurar_columna_trace_id(c)` (mirror del patron existente
  `_asegurar_columnas_reflexiones`): idempotent (PRAGMA table_info + ALTER IF-missing);
  migra bases viejas sin tocar rows existentes (trace_id=NULL).
- `registrar_evento`: si `env["trace_id"]` esta presente, se PLIEGA en `evento_id`
  (`sha(ejecucion+op+cap+op_id + "|" + trace_id)`) para garantizar que llamadas distintas
  conservan filas independientes aunque su `ejecucion` colisionara; si ausente, formula
  original (backward compatible). INSERT OR REPLACE conserva idempotencia.
- Nuevo helper de lectura `eventos_por_trace(c, trace_id)` -> reconstruye
  llamada -> evento -> resultado APUNTANDO a result_id (no duplica).

**`machine.py`** (`_handle_run`, simetria en `_handle_plan`):
- `env["trace_id"] = os.environ.get("RXRE_TRACE_ID")` (propagacion env -> envelope).
- response incluye `"trace_id"` (observable en stdout/session_message.state.content).
- No altera argumentos funcionales del comando. No toca OpenCode/terminal.

### Evidencia (4 llamadas identicas, DB temporal, aislada)
`test_r001_trace_id.py` -> **27/27**:
- C1: 4 llamadas identicas -> MISMO `result_id` (`res_binary_inspect_7a9b6402e8dc`). PROVEN.
- C2: 4 `trace_id` distintos, 4 `evento_id` distintos. PROVEN.
- C3: join 1:1 `trace_id` -> `evento_id`; todo evento trazado enlazado al `result_id` comun. PROVEN.
- Backward compat: llamada sin trace_id -> `trace_id=NULL`, `evento_id` formula original (no colision con filas trazadas). PROVEN.
- Retry vs new: mismo `trace_id` en 2 llamadas -> 2 eventos linkables (op_ + COLISION), distingibles de un `trace_id` nuevo. PROVEN.
- `eventos_por_trace` idempotent (re-query no duplica ni altera filas). PROVEN.

### Prueba viva sobre el live DB (end-to-end agente -> RXRE)
Agente setea `RXRE_TRACE_ID=live_e2e_<ts>` en un comando real `binary.inspect /bin/ls`
(read-only, sin hardware):
- `execution_events.trace_id` = `live_e2e_<ts>` en `tools/rxre/storage/rxre.sqlite3`. PROVEN.
- `trace_id` en response == el del evento; `evento.result_id` == `result_id` de response
  (`res_binary_inspect_7a9b6402e8dc`). PROVEN.
- `op:explain <result_id>` reconstruye la cadena. PROVEN.

Cadena causal completa ahora con correlacion directa por id (no aproximada por timestamp):
OpenCode `session_message.content[tool].state.input.command` (contiene `RXRE_TRACE_ID=...`)
  -> machine.py `response.trace_id`
  -> `execution_events.trace_id`
  -> `result_id` -> `results`/`operations` -> `explain`.

### Migracion y no-regresion
- Live `rxre.sqlite3`: migrada (columna + indice); **17 rows preexistentes intactos**
  (trace_id=NULL). Total rows tras E2E: 18 (17 antiguos + 1 trazado).
- Baseline `/tmp/opencod/run_baseline.py` -> **13/13** (eventlog006 4/4, fase5_trace 7/7,
  dispatch004 132 checks, soul007 14/14, water_run005 5/5...).
- `test_opencode_trace007.py` -> **18/18** post-implementacion.
- `test_r001_trace_id.py` -> **27/27**.

### Scope boundary (iGPU hard limit)
La prueba viva usa `binary.inspect /bin/ls` (solo file I/O). No se abre
`0000:00:02.0`/i915, ni fb0, ni el DRM master de la Intel. La consola sigue siendo i915drmfb.
La RX550 (`0000:01:00.0`) ya tenia el rango VGA legacy preexistente; este cambio no programa
su salida de display (fuera de scope: se requiere permiso explicito del owner para eso).

### Bloqueos cerrados / abiertos
- **CERRADO:** correlacion por llamada (trace_id) - el bloque de 4.4 (result_id no distingue
  llamadas) se resuelve con un id estable por llamada.
- **ABIERTO (deferido a Fase 5):** mismatch de namespaces `operation_id`
  (`COLISION:` en execution_events vs `op_` en operations/results). No afecta la trazabilidad
  (result_id es la clave estable y trace_id la clave por llamada); se deja para when se
  requiera unificar operation_id.
- **ABIERTO (hard owner):** validacion `gpu.register_read` sobre la RX550 - requiere root;
  iGPU nunca tocare.
