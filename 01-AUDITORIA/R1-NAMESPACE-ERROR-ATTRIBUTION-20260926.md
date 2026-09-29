# R1 · NAMESPACE-ERROR-ATTRIBUTION — cierre del gap actual de causa en namespaces

```text
RECORD_ID=R1-NAMESPACE-ERROR-ATTRIBUTION-20260926
CREATED_UTC=2026-09-26
WORK_CLASS=DOCUMENTATION
SCOPE=close the current observability gap in the /proc namespace surface
TARGET=01-AUDITORIA/FASE-C1-RUNTIME-PREFLIGHT/privileged_read_collector.py
COLLECTOR_SHA256=63c8feca01dd448588db25cafbce5f9fd0a7d903038a099890d8abdf29dc8eb6
TEST_MED_REVIEW_SHA256=caa3f2bb6ea740913aee4c49c954f85f008998d703d083ffc1fea2246d0211b0
TEST_DEFECT04_SHA256=20688eb54390d2653360020e77e2b8539a9d393161a8acc874790bde12ac80dd
TEST_DRM_FDS_SHA256=bc1f57e33967e3bd6fbf86d5e9db310129ae7ca1d7cc48126b248916e033f94b
SUITE=296/296 OK
MUTATIONS_DETECTED=5/5
STATUS_CURRENT_GAP=IMPLEMENTED_VERIFIED
STATUS_HISTORICAL_MED2=CLOSED_AS_HISTORICAL_NOT_REWRITTEN
R1_GLOBAL=OPEN
COMMIT=NOT_MADE  (working tree only; no git add, no commit authorised)
```

This record closes the **current** gap. It does **not** rewrite history, does not
reclassify a historical verdict, and does not close R1.

---

## 1 · HISTORICAL_MED2 — preserved verbatim, not rewritten

| | |
|---|---|
| Finding | `R1-COLLECTOR-INDEPENDENT-REVIEW-20260925.md:127` — *"MED-2 · Los namespaces colapsan todos los modos de fallo en el string `UNAVAILABLE`"*. Body: `read_link` distinguishes `PermissionError` from `FileNotFoundError` in its `error` field, `proc_meta` discards it. Judged *"aplicación inconsistente de la regla que el propio GAP 6 creó"*, because `maps` has `MAPS_PERMISSION_DENIED` and namespaces had no equivalent. |
| Verdict | `R1-DEFECT-FIX-RECORD-20260926.md:209` — **`NON_BLOCKING_LIMITATION`**, rationale *"la dirección peligrosa (lectura denegada contada como cubierta) está cerrada"*. |
| Also recorded | `R1-COLLECTOR-INDEPENDENT-REVIEW-20260925.md:177` lists MED-2 as a caveat in the design table. |
| Still open elsewhere | `COLLECTOR-FIX-RECORD-20260925.md:230` lists MED-2 among the still-open items. |

**That verdict is not changed here.** It was reached under the methodology then
in force, and it was correct under it: the dangerous direction — a denied read
counted as covered — was and remains closed. `*_namespace_complete` is still
`ok == total`; this correction did not touch it.

**Why a new requirement appeared afterwards.** `AGENTS.md` V3 (`6fe40b2`) added
rules that the pre-V3 text (`54b3ea8`) does not contain — the pre-V3 file has
**zero** occurrences of each:

| Rule | pre-V3 | V3 |
|---|---|---|
| `A name is not a measurement.` (`AGENTS.md:40`) | 0 | 1 |
| `A swallowed error is not evidence of absence.` (`:76`) | 0 | 1 |
| `Classify a failure before scoring it.` (`:80`) | 0 | — |
| `RACE` / `COVERAGE_LOSS` (`:83`, `:85`) | 0 / 0 | 5 / 2 |

The historical review is untracked, so the filename date `20260925` is not commit
evidence; the content mismatch with `54b3ea8` is the hard datum.

---

## 2 · CURRENT_GAP — what V3 requires that the implementation did not do

Two V3 rules bear on this surface, and neither existed when MED-2 was classified:

- **`:76` swallowed error** — *"If a read failure is discarded and replaced by
  an empty value … the failure must be surfaced."* `read_link` produced the
  reason; `proc_meta` replaced it with the literal `"UNAVAILABLE"`.
- **`:40` a name is not a measurement** — `user_namespace_denied` is a counter
  whose **name** asserts a permission fact. A PID that vanished incremented it,
  so the exported evidence asserted a cause that was never established.

What the gap did **not** do: it never changed a verdict. That is why the
historical verdict was defensible, and why this record separates the two rather
than reclassifying.

---

## 3 · CURRENT_CORRECTION

**Root cause.** `proc_meta` discarded `read_link`'s error; `observe` had no
classifier for this surface, so every cause landed in the same bucket.

**Consequence.** `*_namespace_denied` could assert a permission cause that no
evidence supported.

**Correction.** Five surgical changes, reusing what already existed:

1. `proc_meta` — `namespaces` **keeps its exact shape**
   (`link.get("value", "UNAVAILABLE")` unchanged). A parallel
   `result["namespace_errors"]` records `classify_proc_error(link["error"])`
   per failed namespace. The **existing** classifier is reused; no second
   taxonomy is introduced.
2. `observe` — `namespace_ok` is now fail-closed on two conditions:
   `bool(namespaces) and not namespace_errors and all(value != "UNAVAILABLE" …)`.
   Routing reuses the set comparison `main()` already applies to `/proc` read
   failures: `reasons <= {"PROCESS_DISAPPEARED", "PROCESS_DISAPPEARED_OR_EMPTY"}`
   → `*_namespace_disappeared`, otherwise `*_namespace_denied`. With no recorded
   cause the failure stays in `denied`, the fail-closed side.
3. Accumulator — `root_namespace_disappeared`, `user_namespace_disappeared`.
4. Export — those two keys, nothing else.
5. `ownership_matrix` — **evidence only**:
   `"{} ok / {} disappeared / {} denied / {} total"`. Verdict logic untouched.

**New evidence produced.** `root_namespace_disappeared`,
`user_namespace_disappeared`.

**Why these names.** They are **causal, not verdicts** — the same convention the
collector already uses for `fd_disappeared_pids` and `current_run_disappeared`.
No `*_namespace_race` exists anywhere in the accumulator or the export (verified).

**A vanished PID is not RACE in this surface.** V3's `RACE` (`:83`) requires two
independent facts: disappearance proven **and** evidence the process held no
qualifying resource. For an unreadable namespace the second fact is
unreachable — the namespaces were never read, so no evidence about them exists at
all. V3 `:89-91` is explicit: *"If it cannot be established whether it held the
relevant resource, do not classify it `RACE`; use `INCOMPLETE` or
`COVERAGE_LOSS`."* The namespaces **could not be read** → `COVERAGE_LOSS`.

**Consequences that did not change.** An unreadable namespace still makes
`namespace_ok` `False`; a namespace lost to disappearance is **not** counted as
covered; `*_namespace_complete` is still `ok == total`; incomplete coverage
remains fail-closed.

---

## 4 · CURRENT_VERIFICATION

| | |
|---|---|
| Production files modified | **1** — `privileged_read_collector.py` |
| Test files modified | **2** — `test_med_review_classifications.py`, `test_defect04_behavioral.py` |
| `test_drm_fds_enumerated_behavioral.py` | **unchanged** (`bc1f57e3…`); `ExportTests.REQUIRED` still 7 keys |
| Suite | **296/296 OK** (291 before, 5 added) |
| Behavioural tests | `Med2NamespaceBehaviour`, 5 methods, all passing |

**Case 1 — vanished process.** A process spawned and reaped by the test.
`user_namespace_disappeared == 1`, `user_namespace_denied == 0`,
`user_namespace_ok == 0`, `total == 1`, and completeness `False`.

**Case 2 — PermissionError.** `os.readlink` forced to raise.
`user_namespace_denied == 1`, `user_namespace_disappeared == 0`,
`user_namespace_ok == 0`, completeness `False`.

**Case 3 — control.** A live, readable synthetic tree: `user_namespace_ok == 1`,
both loss counters `0`.

**`ownership_matrix` evidence.** With one vanished and one denied PID, the row
`user_namespaces_covered` is `FAIL` and its `EVIDENCE` contains both
`disappeared` and `denied`.

**Fail-closed of `*_complete`.** The two completeness expressions are taken from
`main()`'s own `root_coverage` AST and evaluated over four populations:
`(vanished=0, ok=3, total=3) → True`; `(1, 2, 3)`, `(3, 0, 3)` and `(1, 3, 4)`
→ **`False`**. A vanished PID — including a fully vanished population — can never
satisfy completeness.

`test_permission_error_cannot_yield_a_pass` (exhaustive fail-closed, pre-existing)
remains green. `test_pre_fix_producer_shape_raises_keyerror` remains green with
the pre-DEFECT-04 shape still reconstructing to **20** keys.

---

## 5 · MUTATION — 5/5, and how the verification was strengthened

| Mutation | Result |
|---|---|
| M1 `proc_meta` discards the reason again | DETECTED `failures=1` |
| M2 `PROCESS_DISAPPEARED` counted as `denied` | DETECTED `failures=1` |
| M3 the `disappeared` counter removed | DETECTED `failures=1` |
| M4 any error counted only as `denied` | DETECTED `errors=2` |
| M5 `*_complete` widened to credit `disappeared` | DETECTED `failures=3` |
| control, unmutated | `rc=0 OK` |

**The first mutation round detected only 3/5.** M4 and M5 were **missed**,
because `test_a_vanished_pid_can_never_make_the_row_pass` hardcoded
`user_namespace_complete: False` in its context and therefore never evaluated
`main()`'s real expression — the test was asserting its own literal, the same
failure mode as the earlier `test_P44b` and the `"benign race"` assertions. The
test was rewritten to extract the two completeness expression nodes from
`main()`'s AST and evaluate them over four populations. Second round: **5/5**.

This is recorded deliberately: a mutation that is not detected means the test is
weak, not that the code is right. Re-verified against the current state:
control `rc=0`, five mutants detected.

---

## 6 · SHAPE_CHANGE

| Structure | Before | After |
|---|---|---|
| `root_coverage` | **29** keys | **31** keys |
| coverage accumulator | 28 keys | **30** keys |

The two new keys are `root_namespace_disappeared` and
`user_namespace_disappeared`. They belong to the **namespace coverage** block,
**not** to the DRM attribution block; `ExportTests.REQUIRED` in
`test_drm_fds_enumerated_behavioral.py` remains at its seven DRM attribution keys
and was not extended.

`test_defect04_behavioral.py` was updated mechanically: the two keys were added
to its accumulator fixtures (which are contractually required to mirror the real
accumulator), the producer count moved `29 → 31`, and the **drop-reconstruction
set** grew from 8 to 10 entries so the pre-DEFECT-04 shape still reconstructs to
20 keys. That drop set is not the DRM attribution set; keeping the two apart is
what preserves the DEFECT-04 invariant.

**External consumers must account for this shape change.** Any artifact, fixture
or script that asserts a `root_coverage` key count, or that rebuilds it, needs
the two new keys. Re-scoring an **older stored bundle** is unaffected in the
verdict path: `ownership_matrix` reads the new keys with `.get(..., 0)` in the
evidence string only, and the verdict keys are the pre-existing ones.

---

## 7 · MED2_ID_COLLISION — recorded, not renamed

The identifier `MED-2` designates **two different findings**:

| Document | Date | Section | Finding |
|---|---|---|---|
| `R1-COLLECTOR-INDEPENDENT-REVIEW-20260925.md` | 20260925 | `:127` | namespaces collapse all failure modes into `"UNAVAILABLE"` |
| `R1-COLLECTOR-INDEPENDENT-REVIEW-2-20260926.md` | 20260926 | `:144` | no test covers the realistic case of MED-1 |

Review 2 numbers its own findings from `MED-1` again, so its `MED-2` is **not**
the review-1 `MED-2`. **No historical document is renamed.** This record cites by
document + date + line + description for that reason.

**Candidate identifier for the current gap:**
`NAMESPACE-ERROR-ATTRIBUTION-20260926`, as used in this record's title.
`UNKNOWN` whether the project adopts it: adopting an identifier is a naming
decision, not a finding, and it is not required by anything in `AGENTS.md`. If
the project prefers another, this record's references remain unambiguous because
they carry document, date, line and description.

---

## 8 · OPEN and UNKNOWN

| | |
|---|---|
| R1 global | **OPEN.** This is one surface of one criterion. Not closed here. |
| `user_namespaces_covered` | **not closed.** The privileged re-sweep has **not** been run since this change; the `83/84` figure predates it. |
| The `1/84` PID | `UNKNOWN` — whether it vanished or was genuinely denied cannot be determined without a privileged re-sweep. |
| Mixed causes in one PID | `UNKNOWN`, not observed. If a PID had both `PERMISSION_DENIED` and `PROCESS_DISAPPEARED` across its seven namespaces, `reasons <= {…}` routes it to `denied`: fail-closed and consistent with `main():2534-2537`. |
| `R1_4_ATTRIBUTION_STATE_UNRECOVERABLE` | `OPEN`, untouched. |
| Annotations owed to history | `R1-DEFECT-FIX-RECORD:209` and `R1-COLLECTOR-INDEPENDENT-REVIEW-20260925.md:127`/`:177` should carry a pointer to this record. **Not written here** — this round authorises documentation of the correction, not edits to historical records. |

`R1-C1-CORRECTION-CLOSURE-20260926.md` does not mention MED-2 and is not
contradicted by this record.

---

## 9 · WHAT THIS RECORD DOES NOT CLAIM

- It does not reclassify `MED-2 = NON_BLOCKING_LIMITATION`.
- It does not claim a verdict change: `*_namespace_complete` is unchanged, and
  every state in this surface was `COVERAGE_LOSS` before and after.
- It does not claim a vanished namespace is or is not `RACE` in general; only
  that V3's second fact is unreachable here, so the loss stays `COVERAGE_LOSS`.
- It does not claim the privileged re-sweep happened.
- It does not close `user_namespaces_covered`, `R1`, or `R1_4`.
- It is not committed. The collector is `63c8feca…` in the working tree; `HEAD`
  remains `df2406ac9f5744cf4e1a5624aecc423f5b9089a8` with the earlier
  `9b6e8d7d…` collector.
