# R1-DEFECT-04-FIX-RECORD-20260926

```text
RECORD_ID=R1-DEFECT-04-FIX-RECORD-20260926
CREATED_UTC=2026-09-26T03:02:57Z
SCOPE=A1 only, as authorized
TARGET=01-AUDITORIA/FASE-C1-RUNTIME-PREFLIGHT/privileged_read_collector.py
WORK_CLASS=STATIC_IMPLEMENTATION
DEFECT_04=CLOSED
```

This record documents a single authorized change. It is a new record and does
not modify any prior evidence. Historical artifacts keep their original state.

## 1. Root cause

`main()` builds `root_coverage` at L2293. The live `/proc` sweep counts PIDs in
a single accumulator, `coverage`, created at L1907 and incremented at
`coverage["total_pids"] += 1` (L2023).

`root_coverage` carries two naming families. Nine keys are UPPERCASE
(`TOTAL_PIDS`, `ROOT_PIDS`, `USER_PIDS`, `UID_UNKNOWN_PIDS`,
`LATE_OBSERVED_PIDS`, `ROOT_FD_COVERAGE`, `ROOT_MAPS_COVERAGE`,
`ROOT_NAMESPACE_COVERAGE`, `USER_NAMESPACE_COVERAGE`); the rest are lowercase.
The partition is not principled: the six namespace counters are lowercase while
the five PID counters are UPPERCASE, and both are counts.

`ownership_matrix` receives that dict as a **pure alias**
(`coverage = context['root_coverage']`, L1451 — no transform, no copy) and reads
it with 13 `[ ]` subscripts and **zero** `.get()` calls, so nothing hides a
missing key. It reads 10 distinct keys, 9 of which are in the lowercase family.
The tenth is `total_pids`, which the producer emits as `TOTAL_PIDS`.

Therefore every run that reached the matrix died at the first read:

```text
KeyError: 'total_pids'
```

Classification: `OBSERVED` (reproduced in memory, and seen in run 3 evidence
`R1-20260926T024340Z.json`).

## 2. Decision: A1

Emit `total_pids` into `root_coverage` alongside the existing `TOTAL_PIDS`,
both read from the same accumulator cell.

```python
"TOTAL_PIDS": coverage["total_pids"],   # pre-existing, retained
"total_pids": coverage["total_pids"],   # added by A1
```

`TOTAL_PIDS == total_pids` holds **by construction**, not by convention: both
expressions read the same dictionary cell of the same accumulator, in the same
run, at dict-literal evaluation time. The producer has exactly one accumulator
(L1907), exactly one `root_coverage` assignment, and zero reassignments of
either key — verified before the change.

### Why A2 was not chosen

A2 (rename `TOTAL_PIDS` → `total_pids`) was ruled out **by explicit user
restriction**, not by evidence. It also carried a known consequence recorded
during diagnosis: `COLLECTOR-CHANGE-RECORD-20260925.md:58` names `TOTAL_PIDS` as
an emitted key of `root_coverage`, so renaming changes a documented output key
and leaves the five PID counters split 4 UPPERCASE / 1 lowercase.

### Why C was not chosen

C (pass the raw accumulator into `matrix_context` as a second input) was ruled
out **by explicit user restriction**. Its measured cost was 16 call sites across
5 test files that construct a `root_coverage` and invoke the real
`ownership_matrix`.

### Cost accepted by A1

`root_coverage` now carries one fact under two names. This is deliberate and
bounded: the two names are emitted from a single expression, so they cannot
diverge within a run. The scope of the duplication is exactly one key.

## 3. Minimal diff

`+8` lines (`1` code, `7` comment), `2766 → 2774` lines, `110930` bytes.
Against the verified pre-image (`HASH_BEFORE`):

```diff
@@ -2292,6 +2292,14 @@
       # "complete" -- it is unobserved, and is reported FAIL.
       root_coverage = {
           "TOTAL_PIDS": coverage["total_pids"],
+        # DEFECT-04 / fix A1: ownership_matrix reads the live-sweep total under
+        # the accumulator's own name, "total_pids" (the only key it needs that
+        # the UPPERCASE record family above does not carry).  Both names are
+        # emitted from the same accumulator cell, so TOTAL_PIDS == total_pids
+        # for a given run by construction, not by convention.  The UPPERCASE
+        # name is retained because COLLECTOR-CHANGE-RECORD-20260925.md:58
+        # documents it as part of the emitted root_coverage schema.
+        "total_pids": coverage["total_pids"],
           "ROOT_PIDS": coverage["root_pids"],
           "USER_PIDS": coverage["user_pids"],
           "UID_UNKNOWN_PIDS": coverage["uid_unknown_pids"],
           "LATE_OBSERVED_PIDS": coverage["late_observed_pids"],
           "ROOT_FD_COVERAGE": f"{coverage['fd_complete_pids']}/{coverage['total_pids']}",
```

No other line of the collector was touched. No refactor. No other key renamed.

## 4. Hashes

Verified by two independent methods (`sha256sum`, `hashlib`); both agree.

```text
HASH_BEFORE=1078cc7c7c2e39308300f86ae17d8a075eb2624410eb26156c2d4525041b5121
HASH_AFTER =0769b405f00152d4f29ca262699d465fecfea00bf42a627847f2013596cc4613
```

`HASH_AFTER` was also re-derived from the file actually loaded by the test
interpreter via `importlib`, confirming the hash belongs to the executed file
and not to a sibling on disk.

The pre-image used for the diff above was reconstructed by removing the 8 added
lines and hashing the result: it reproduced `HASH_BEFORE` **byte for byte**, so
the diff is against the genuine previous state, not an approximation.

New test file:

```text
FILE=01-AUDITORIA/FASE-C1-RUNTIME-PREFLIGHT/test_defect04_behavioral.py
SHA256=7994de114a5cb5ab09cb3cb40a1f0490e5266117f072225d01900a69fe0a168f
BYTES=14674  LINES=370
```

## 5. Behavioral test

`test_defect04_behavioral.py`, 13 tests, 5 classes.

**Design constraint honored.** The test does not call `inspect.getsource()`, does
not search the source for a string, and does not pass because an expected name
appears in the implementation. `test_T31` is the counterexample this avoids: it
asserted that a `+=` line exists, which is true with and without the DEFECT-03
bug.

**How the producer is exercised.** The producer is a dict literal inside
`main()`, a ~500-line procedural function that cannot be invoked without root, a
`/proc` sweep and a live window. So the producer is **executed, not read**: the
real `ast.Dict` node is taken from the real module's AST, compiled, and evaluated
against representative live accumulators. Its output is then passed to the
**real, unmodified** `ownership_matrix`. Both ends of the contract are live code.

### Required demonstrations, and how each is met

| Requirement | Test | Result |
|---|---|---|
| before fix: `KeyError: 'total_pids'` | `PreFixReproductionTests` + whole-file run against the reconstructed pre-fix collector | `KeyError('total_pids')` |
| after fix: full execution | `ConsumerExecutionTests.test_ownership_matrix_completes_on_real_producer_output` | 11 criteria, `OWNERSHIP_CRITERION_STATE=PARTIAL` |
| `TOTAL_PIDS == total_pids` | `ProducerContractTests.test_both_names_are_emitted_and_agree` | equal |
| value reaches the evidence field | `ConsumerExecutionTests.test_the_counted_total_reaches_the_evidence_field` | `'across 283 PIDs'`, `'across 7 PIDs'` |
| removing either key is detected | `RegressionDiscriminationTests` (2 tests) | both caught, by different assertions |
| result contains the correct value | second accumulator uses a different total, so a constant cannot pass | `283` and `7` |

### Discrimination, measured

The **same** test file was run against two collectors:

```text
pre-fix  (HASH_BEFORE 1078cc7c…, 20 producer keys): Ran 13  FAILED (failures=3, errors=7)
post-fix (HASH_AFTER  0769b405…, 21 producer keys): Ran 13  OK
```

The 3 tests passing in both runs are invariant guards by design
(`test_pre_fix_producer_shape_raises_keyerror`,
`test_removing_the_lowercase_contract_key_is_caught`, and the
`ProducerExecutableTests`): they hold the pre-fix shape by dropping the added
key, so they must pass in both states.

### The two regressions are caught by different assertions

- Removing `total_pids`: caught twice — the producer-contract assertion reports
  the missing key, and executing the consumer raises `KeyError`.
- Removing `TOTAL_PIDS`: the consumer **still succeeds**. This regression is
  invisible to the execution path, which is precisely why it carries its own
  assertion against the executed producer output. Recorded so a future change
  does not remove the UPPERCASE key believing it is unused.

### Tests not modified

No existing test file was edited. All pre-existing tests construct `root_coverage`
fixtures with `total_pids` already, so the contract now matches them instead of
contradicting them — that is why the affected suite passed without edits.

### Authoring defects in this test, recorded for provenance

The test was executed three times. The first two runs failed on **defects in the
test, not in the collector**: a wrong helper name (`_load_consumer` vs
`_load_collector`, `NameError`), a missing `drop=` in the pre-fix
reproduction, and a malformed final assertion in the `TOTAL_PIDS` test. All three
were corrected. No collector line was changed in response to a test failure.

## 6. Suites

Affected suite — every file that invokes `ownership_matrix` or builds a
`root_coverage` fixture:

```text
test_collector_failure_modes.py      Ran 35  OK
test_med_review_classifications.py   Ran 26  OK
test_medium_fixes.py                 Ran 27  OK
test_privileged_read_collector.py    Ran 43  OK
test_r1_defects.py                   Ran 23  OK
test_defect03_behavioral.py          Ran  9  OK
test_defect04_behavioral.py          Ran 13  OK
```

Complete suite (`unittest discover`, `01-AUDITORIA/FASE-C1-RUNTIME-PREFLIGHT`):

```text
Ran 176 tests   OK   (exit code 0)
```

`176 = 163` pre-existing (`154` + `9` from DEFECT-03) `+ 13` new. No regressions.

The `04-IMPLEMENTACION` suite is a different subsystem and does not import the
collector; `pytest` is not installed in this environment, so it was not
executed. `COLLECTOR_PROVENANCE` for it is unaffected either way. Classified
`NOT_RUN` rather than passed.

## 7. System effects

```text
SUDO_USED=NO
GPU_CHANGES=0
SYSFS_WRITES=0
SYSTEMD_CHANGES=0
STORAGE_WRITES=0
SERVICE_CHANGES=0
PROCESS_SIGNALS=0
R1_RUN_4=NOT_EXECUTED
COMMITS=0
```

Files touched: 1 modified (`privileged_read_collector.py`), 1 created
(`test_defect04_behavioral.py`), 1 created (this record). Repo state after:
`HEAD=c614678`, `commits=8`, `staged=360`, `untracked=27`.

Prior evidence preserved and re-verified untouched:
`R1-20260926T024340Z.json` (`04be7bc4…`),
`R1-20260926T005434Z.json` (`aa388953…`),
`R1-20260926T000649Z.json`, `R1-MEDIUM-FIX-RECORD-20260926.md` (`f1e56c01…`),
`R1-DEFECT-03-FIX-RECORD-20260926.md` (`eb386722…`),
`COLLECTOR-CHANGE-RECORD-20260925.md`, `AGENTS.md` (`d5fa85a4…`),
`ESTADOS-ES-EN.md` (`c858b5ae…`).

## 8. Limitations

1. **The test does not execute `main()` end to end.** It executes the real
   producer literal and the real consumer. The surrounding procedural body of
   `main()` — the `/proc` sweep itself — is not executed, because that requires
   root and a live window. So the fix is verified at the contract level, not at
   the runtime level.
2. **R1 run 4 was not executed**, as instructed. The fix is therefore
   `STATIC_IMPLEMENTATION` verified and not `RUNTIME_PREFLIGHT` verified. A
   passing test does not establish that a full sweep completes.
3. **`root_coverage` still mixes 9 UPPERCASE and 12 lowercase keys.** The
   partition remains unprincipled. A1 closed the functional defect; the naming
   inconsistency is untouched and out of the authorized scope.
4. **One fact is now carried under two names.** Bounded to one key and
   non-divergent within a run by construction, but it is a real cost of A1.
5. **The pre-fix baseline suite could not be observed to fail.** The 8 `root_coverage`
   test fixtures all provide `total_pids`, so nothing in the pre-existing suite
   covered this. The pre-fix failure set in §5 comes from running the new test
   against the reconstructed pre-fix collector, which is the honest form of that
   demonstration.

## 9. Findings kept separate

### 9.1 Collector exit code does not distinguish success from error

```text
FINDING_ID=COLLECTOR_EXIT_CODE_CONTRACT
STATUS=OPEN
CORRECTED_IN_THIS_RECORD=NO
```

The collector returns `EXIT_CODE=0` both on success and on an error payload. In
`R1-20260926T024340Z.json` the exit code was `0` while the payload carried
`collector_error` and a traceback. The error is distinguishable only by the
presence of `collector_error`, or by `COLLECTOR_STATUS=ABORTED` inside
`abort_payload`. A supervisor that reads only the exit code would report `PASS`.

Not corrected here, by instruction. Any future verification of R1 must inspect
the JSON, not the exit code.

### 9.2 Ownership-matrix fixtures are not validated against the real producer

```text
FINDING_ID=TEST_SUITE_INTEGRATION_GAP
STATUS=OPEN
CORRECTED_IN_THIS_RECORD=NO
```

Eight `root_coverage` fixtures across 5 test files are hand-built and passed to
the real `ownership_matrix`. They agreed with the consumer but not with the
producer, which is why 163 tests were green while DEFECT-04 was live. No test in
the suite executes `main()` end to end; a real sweep would have caught this on
2026-09-25.

`test_defect04_behavioral.py` closes the contract for the one key under test. It
does not close the general gap. Not modified in this fix, by instruction.

## 10. State

```text
DEFECT_04=CLOSED
ADVANCE_READINESS=ADVANCE_READY
R1_RUN_4_READY=YES
R1_RUN_4=NOT_EXECUTED
R1_RUN_4_AUTHORIZATION=REQUIRED
```

`ADVANCE_READY` refers to the static contract being correct and verified. It is
not a runtime validation and does not authorize execution. Per
`R1-PLAN-privileged-readonly-ownership.md`, `R1_AUTHORIZATION=REQUIRED` and
`R1_PRIVILEGE=ROOT_READ_ONLY`; run 4 needs a separate explicit authorization, and
§9.1 must be read alongside its result.
