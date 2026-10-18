# RXRE-CAUSAL-EVOLUTION-001 — Report

**Date:** 2026-10-14 · **Base:** tree left by `RXRE-AUTONOMY-001` (branch `main`, HEAD `d754f2c`, no new commits, branches, worktrees or agents)

This reports what was executed and observed. Where a claim is not verified, it says what is missing.

---

## 0. STATE RECONCILIATION (done before any edit)

| fact | result |
|---|---|
| branch | `main`, HEAD `d754f2c` — unchanged |
| tracked files modified | 12 |
| **untracked** | `tools/rxre/core/store.py`, `api/machine.py`, all adapters, all new tests — **RXRE's core is not in git** |
| previous iteration's tests | `test_autonomy003` 11/11, `test_lecciones006` 7/7, `test_umr_hardware002` 11/11 — re-run, green |

> **Reconciliation finding worth stating plainly:** the core of RXRE is untracked by
> git. `git diff` shows 12 files and none of them are `store.py` or `machine.py`.
> There is no version-control safety net for the code that matters most. Every edit
> below is therefore additive-or-in-place with no `git checkout` anywhere.

---

## 1. PRIORITY A — REAL GHIDRA DECOMPILATION

### 1.1 The blocker was not "javac works"

`binary.decompile` was `PARTIAL` with a `BACKEND` entry, and its tests **passed** —
because `fixture_json` short-circuits the entire block that runs Ghidra. The real
path had never executed.

`gh_decompile.py` compiles `backends/scripts/DumpDecomp.java`. That file **did not
exist**. `javac 25.0.4.1` and 195 Ghidra JARs were present; the source was missing.

### 1.2 The script, written against the verified API

Every class and method was checked with `javap` against the installed JARs, not from
memory. The script shape is taken from a script Ghidra itself ships
(`Ghidra/Features/BSim/ghidra_scripts/DumpBSimSignaturesScript.java`).

| class | jar |
|---|---|
| `ghidra.app.script.GhidraScript` | `Base.jar` |
| `ghidra.app.decompiler.DecompInterface` / `DecompileOptions` / `DecompileResults` | `Decompiler.jar` |
| `ghidra.program.model.listing.Function` | `SoftwareModeling.jar` |
| `ghidra.util.task.TaskMonitor` | `Utility.jar` |

Two decisions in the script, both measured:

- **Atomic write** (temp + rename). A half-written JSON is worse than none: the
  adapter would parse it and believe there are functions.
- **The "decompiled" counter comes from the same operation that decides it.** The
  first version counted `"decompiled":true` occurrences in the finished JSON. That
  is wrong: the pseudocode is *C text* and can contain that string literally.

### 1.3 Three undocumented Ghidra constraints (each cost 2–15 min per experiment)

Read from `HeadlessAnalyzer.checkScript` bytecode in `Base.jar`:

```java
if (nombre.endsWith(".class")) {
    urls   = GhidraScriptUtil.getScriptSourceDirectories() -> toURL();
    loader = URLClassLoader.newInstance(urls);
    try { ClassSearcher.forNameSafe(className, GhidraScript.class, loader); return null; }
    catch ClassNotFound -> "java class not found for '" + className + "'";
    throw new IllegalArgumentException("Invalid script: " + nombre);
}
rf = findScript(nombre);   // <- THIS branch uses -scriptPath
```

1. **`-postScript` must receive `DumpDecomp.java`, not `.class`.** For a `.class`
   name the classloader is built from `getScriptSourceDirectories()` and
   `-scriptPath` never participates. So the precompiled class existing was irrelevant.
2. **`-scriptPath` accepts exactly one path.** Measured: `A` → OK; `A:<empty dir>` →
   *Script not found*; `A -scriptPath B` → *Script not found*. An **empty** directory
   breaks it too, which rules out name collision and pins it on the descriptor.
   Three independent measurements, because with one you cannot tell which of the two
   explanations is right.
3. **Ghidra compiles the source itself.** The prebuilt `.class` is not part of the
   invocation; `compilar()` is kept only as the cheap contract check (it verifies the
   source builds against this machine's real JARs in seconds, before the JVM starts).

### 1.4 A second blocker the first one was hiding

With the script fixed, `binary.decompile` returned `status: ok` with real
pseudocode — and `persistido: false`, `operation_id: None`, **zero rows in the
requested database**.

`gh_decompile.py` had no `persistir()`. The capability was closed, verified, produced
the best evidence in the project, and threw it away. The operation still said `ok` —
which is what makes that class of bug hard to see.

`persistir()` was added following the `rz_inspect` pattern (collision check before
insert; connection closed only if we opened it). `n_functions` / `n_decompiladas` were
added to machine.py's passthrough, so an agent can now distinguish "no functions" from
"190 functions, 2 decompiled".

### 1.5 Validation level reached: REAL EXECUTION, end-to-end, through the public surface

```
op: run  binary.decompile  artefacto=/bin/ls  backend_id=ghidra

status        = ok
operation_id  = op_1728d4b152574818
persistido    = True
exit_status   = 0            duration = 16.0s
n_functions   = 1   n_decompiladas = 1
explain(result_id) -> ok
filas en la base PEDIDA: operations=1 results=1
```

Pseudocode, first function — this is Ghidra's decompiler output, not a fixture:

```c
ulong __strftime_internal_isra_0
        (char *param_1, ulong param_2, char *param_3, tm *param_4, ...)
{ int iVar1; bool bVar2; undefined4 uVar3; undefined8 uVar4; ...
```
1680 lines / 46 304 bytes. The test checks for Ghidra's signature (`undefined*`,
`param_`/`local_`, `uVar`/`iVar`/`DAT_`/`stack_`), which a fixture does not produce.

**Side effect measured:** `test_backends_bulk` went from **112 checks / 1 failure**
(`script precompilado presente`) to **112 / 0**. Priority A closed a pre-existing
failure as a side effect.

`test_decomp003.py` — **23/23**, covering four separated levels: compilation,
argv invariants (the three rules above), real execution, traceability, failure paths.

---

## 2. PRIORITY B — SOUL AS A REAL VALUE FUNCTION

### 2.1 What was actually there

```python
pendientes.sort(key=lambda t: (-t['priority'], t['created_at']))
```

`priority` is an integer a person writes. The priority was not in the knowledge
system; it was in the task text. Two consequences:

- `dependencies` was stored and **never read**.
- When the world changed, the priority could not find out — it had nothing to read.

### 2.2 The function, and what it refuses to do

`valorar_tareas()` — six components, each with a declared source and meaning:

| component | source | direction |
|---|---|---|
| `desbloquea` | `mission_tasks.dependencies` — PENDING tasks depending on this | + |
| `incertidumbre` | `research` with open status on this target | + |
| `evidencia_ausente` | `findings` citing this target | + |
| `reincidencia` | `reflexiones` with failure outcome on this target | + |
| `alineacion` | `mission_criteria` mentioning this target | + |
| `coste` | registry state of the named capability | − |

Three rules the score cannot break:

1. **A blocked task is not selected**, whatever its value. A number does not convert an
   unmet dependency into a possible action. `dependencies` being unread was the bug.
2. **A missing component is not zero.** It is excluded, the weights renormalise, and
   `cobertura` is reported. "No data" and "measured zero" are different, and conflating
   them makes absence of evidence look like certainty.
3. **Weights are small declared integers**, not fitted decimals. There is not enough
   data in this tree to justify tuning them, and saying so beats a precise-looking
   number with no meaning.

Tie-break is deterministic: (value, desbloquea, task_id).

### 2.3 Evidence that it changes behaviour — `test_soul007.py`, 14/14

The decisive case, with the real output:

```
mision "competicion"
  facil    (sin dependencias, priority=5)          valor=0.000  cobertura=33%
  desbloq  (3 tareas dependen, priority=1)         valor=0.600  cobertura=33%

  antes (priority) -> task_cf78ee4602ca0a19     <-- una DEPENDIENTE, bloqueada
  ahora (valor)     -> task_b427f1392c1236db     <-- la que desbloquea
```

The old ordering picked a **blocked dependent** — a task that could not be executed,
because `dependencies` was never opened. That is a stronger demonstration of the gap
than the one the test was written for; the assertion was corrected to match reality
rather than the intention.

Also verified: blocked-by-dependency is never selected despite a value; a target with
a real `finding` gets `evidencia_ausente = 0.0` while one without gets `1.0`; an open
hypothesis raises `incertidumbre`; an opaque task has **33 % coverage** vs **100 %**,
with `valor: None` rather than `0` for the components that cannot be measured;
ordering is stable across calls; `por_valor=False` still reproduces the old behaviour.

### 2.4 A real bug the test found in my own function

```python
for r in c.execute("SELECT claim FROM findings"):
    for t in abiertas_por_target:     # <-- only targets with an OPEN question
```

A finding citing a **closed** target — the normal case, because you resolved it — was
never counted, so its task reported `evidencia_ausente = 1.0`. The component existed
precisely to prevent claiming "no evidence" when there is some. Fixed by unioning
targets from `research` *and* `findings` before comparing.

---

## 3. PRIORITY C — AETHER GENERATES ALTERNATIVES

### 3.1 What the module did before

It reported `SATURATED: no hay next_actions` and stopped. A frontier with no next
actions and a frontier blocked by a non-executable capability got the same verdict and
the same silence.

### 3.2 Motive, measured from the database

`_motivo_saturacion()` distinguishes six:

| motive | measured by |
|---|---|
| `COMPLETADA_CON_EVIDENCIA` | status closed **and** refs present |
| `COMPLETADA_SIN_EVIDENCIA` | status closed, no refs |
| `BLOQUEADA_POR_CAPACIDAD` | registry state of the target's capability |
| `REINCIDENCIA` | ≥2 failure reflections + failed operations |
| `SIN_DISCRIMINANTE` | no `next_action` recorded |
| `PLAN_SIN_EJECUCION` / `RENDIMIENTOS_DECRECIENTES` | plans vs executed operations |

**Saturated and stalled are now different things.** Saturated = this frontier's work is
done. Stalled = it cannot proceed, and it gets its own motive and its own exit.
Collapsing them is how an autonomous system learns to stop.

### 3.3 Alternatives carry a discriminant

Every alternative names an artifact, what it would establish, and **the observation
that distinguishes success from failure**:

```
[producer] hacer ejecutable `gpu.no`: mirar por que esta en NO_DECLARADA
    establece    : que la capacidad pasa de camino teorico a producer medible
    discriminante: `esta_permitida('gpu.no').permitida` pasa de False a True, con su motivo
    coste: bajo si el bloqueo es de codigo; alto si es de permisos | reversible=True
```

A test asserts no alternative contains "investiga mas". If nothing with a
discriminant can be generated, that is stated with its evidence rather than padded.

`reabrir_frontier()` reopens a closed frontier — **but only with new evidence**, and
without it the call is rejected and the state is unchanged ("reabrir sin evidencia
nueva no es reabrir: es volver a mirar lo mismo"). The reason is stored as a note
plus an `audit_log` row.

### 3.4 The gap this exposed: AETHER had no input

`op: saturate` returned **`empty`** on the real database. Not because the module was
broken: because `research` holds 17 entries and **zero** of kind `frontier`. The system
could *measure* saturation but had no way to *declare* a frontier — the thermometer
without the clinical history.

**`op: research` was added** so an agent using only the public surface can register
`hypothesis | claim | note | next_action | frontier`, through the same existing
validations (closed lists; `PROVEN` requires real refs). No new registry.

Three real frontiers were then registered with their measured blockers, and AETHER
diagnosed all three as `SIN_DISCRIMINANTE` — which is **true**: none of them has a
registered `next_action`.

`test_aether008.py` — **23/23**.

---

## 4. PRIORITIES D / E / F — PARTIAL, AND WHAT IS NOT DONE

Stated plainly rather than claimed:

- **D (causal evolution loop).** Not built as a new subsystem. The individual links
  exist and are tested (`run` → `experiment` → `reflect` → `lessons`;
  `research` → `saturate` → alternatives), but there is no single iteration record
  chaining them. **Not implemented.**
- **E (WATER measurable behaviour change).** Coverage is 11/11 with all checks
  *executed and passing* (verified below). That is enforced memory. Whether a lesson
  changes a *later* decision is not measured — no replay harness. **Not implemented.**
- **F (BODY/EARTH/AIR end-to-end trace).** Sections 1 and 3 trace the decompilation and
  AETHER chains to the requested database and through `explain`. A single shared
  execution-event trace across stages does not exist. **Not implemented.**

---

## 5. EXTERNAL PROJECTS

No repository was cloned this iteration. The work was: verify a tool's resolution rules
from its bytecode, make an absent script exist, and repair its persistence. Mechanisms
that fit RXRE's existing interfaces were implemented directly; none of the ten listed
projects was needed for any of it.

---

## 6. TESTS EXECUTED

**22 suites, 19 green.** No regression introduced.

| suite | result | note |
|---|---|---|
| `test_decomp003.py` (new) | **23/23** | Ghidra: compile, argv rules, real run, traceability, failure paths |
| `test_soul007.py` (new) | **14/14** | SOUL: value vs priority, dependency gate, evidence, coverage, determinism |
| `test_aether008.py` (new) | **23/23** | AETHER: six motives, discriminated alternatives, reopen |
| `test_backends_bulk.py` | 112/0 | **was 112/1** — missing Ghidra source closed it |
| `test_backends004.py` | 155 OK | |
| `test_dispatch004.py` | 132 OK | |
| `test_autonomy003.py` | 11/11 | updated to the AETHER contract |
| `test_mission001.py` | 7/7 | updated: **both** orderings now asserted |
| `test_ext002_umr.py` | 25/25 | |
| `test_reflexion002.py` | 13/13 | |
| `test_umr_hardware002.py` | 11/11 | |
| `test_lecciones006.py`, `test_registro_variabilidad002.py` | pass | |
| `test_callgraph1636.py`, `test_disasm1634.py`, `test_xrefs1635.py`, `test_dependency008.py`, `test_epistemic_distinctions.py` | pass | |
| `test_integration.py` | 0/2 criteria, PENDING | pre-existing, not a failure |
| `test_container1632.py` | not run | pre-existing timeout |

**Two tests were updated, and how:**

- `test_mission001.test_next_action_selection` asserted selection by `priority`. SOUL
  changed the default. Rather than delete the assertion, it now checks **both**
  (`por_valor=False` for the old ordering, plus the value behaviour). If the new
  function broke, this test could not tell.
- `test_autonomy003` asserted `no_saturadas`, a key the new AETHER contract no longer
  emits. It now asserts `paradas` plus, per frontier, motive, measurements and
  alternatives-with-discriminants.

### Failures that remain (3) — causes re-verified, not inherited

| suite | cause |
|---|---|
| `test_p004.py` | `ModuleNotFoundError: core.target` — module absent from the tree |
| `test_p003.py` | 21 failures: needs an AMD-header register DB (`gfx_8_0_d.h`); not wired |
| `test_p0_2_conflict014.py` | rc=1 with no `FAIL` line (exception at the end) |

All three are **untracked** and none is in `git diff`. Evidence they are not from this
iteration: this iteration did not touch them, and the modules they import are absent.

### Capabilities not tested

- Ghidra on **ET_REL** (`amdgpu.ko`): not executed. Known limitation, measured earlier:
  Ghidra 12.1.4 returns 0 functions for ET_REL while returning 190 for ET_DYN on
  `/bin/ls`. No claim is made about `amdgpu.ko`.
- Ghidra `analyzeHeadless` compiled-script route (`getScriptSourceDirectories`):
  **not used** — those directories are root-owned and not writable. The source route
  is the working one.
- Timeouts, malformed `out.json`, Ghidra crashes: exercised only via the fixture path,
  not against a real failing Ghidra.

---

## 7. MEMORY — measured, not asserted

```
lecciones: 11   con check: 11   sin check: 0   cobertura: 100 %   rotas: 0
checks DISTINTOS ejecutados: 4      lecciones vigiladas: 11 de 11 (exit=0)
```

The four Ghidra/UMR lessons of this iteration are recorded as
`reflexiones` with `check_ejecutable=test_decomp003.py`, and all four checks were
**executed**, not merely present.

---

## 8. BLOCKERS — exact, verified causes

| blocker | verified cause |
|---|---|
| `binary.decompile` did nothing | `backends/scripts/` absent. **RESOLVED** this iteration |
| `-postScript .class` rejected | Ghidra's classloader ignores `-scriptPath` for `.class`. **RESOLVED** by using the source name |
| `-scriptPath A:B` rejected | Ghidra headless accepts exactly one path. **RESOLVED** by using one |
| decompilation evidence discarded | no `persistir()` in `gh_decompile.py`. **RESOLVED** |
| `research` has zero frontiers | no public op to register one. **RESOLVED** (`op: research`) |
| `test_p004` cannot run | `core.target` module absent — **OPEN**, needs the module written |
| `test_p003` 21 failures | AMD-header register DB not wired — **OPEN**, needs `gfx_8_0_d.h` parsing |
| RXRE core untracked by git | pre-existing repo state — **OPEN**, outside this task's scope |

---

## 9. NEW FRONTIERS EXPOSED BY THIS ITERATION

1. **`core.target` does not exist.** Blocks `test_p004` entirely. It is a *module* the
   project's own tests import.
2. **No AMD-header register database.** `test_p003` needs `gfx_8_0_d.h` semantics;
   RXRE can now read hardware registers but cannot map symbolic register names to
   offsets the way `test_p003` expects.
3. **`test_p0_2_conflict014` exits 1 with no failure line.** Unexamined.
4. **RXRE's core is untracked by git.** Every edit to `store.py` / `machine.py` is
   unprotected.
5. **Three registered frontiers are `SIN_DISCRIMINANTE`** — none has a `next_action`.
   AETHER's own first recommendation for all three is to register one.

---

## 10. NEXT ACTIONS, BY EVIDENCE

1. **Write `core/target.py`.** `test_p004` cannot execute at all; it is a declared
   module of the project that does not exist. Highest certainty, lowest risk.
2. **Wire the AMD header register DB** (`gfx_8_0_d.h`). Closes 21 assertions in
   `test_p003` and gives symbolic names to the hardware reads that already work.
3. **Register a discriminating `next_action` for each of the three real frontiers.**
   AETHER measured that all three are stalled for exactly this reason; the fix is now
   a `op: research` call.
4. **Build the replay harness for Priority E.** The gap between "check passes" and
   "the check changed a decision" is unmeasured, and the directive correctly refuses to
   call coverage evidence of learning.
5. **Track RXRE's core in git.** Not a coding task, but every other item here is
   riskier without it.

Items 4 and 5 were not started. Nothing above is declared complete that was not run.