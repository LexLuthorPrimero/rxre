# R1-DRM-FDS-ENUMERATED-FIX-RECORD-20260926

```text
RECORD_ID=R1-DRM-FDS-ENUMERATED-FIX-RECORD-20260926
CREATED_UTC=2026-09-26T04:40Z
FINDING_ID=DRM_FDS_ENUMERATED_DOES_NOT_VALIDATE_CLIENT_ID
SCOPE=drm_fds_enumerated scoring, as authorized
WORK_CLASS=STATIC_IMPLEMENTATION
FIX_STATUS=CLOSED
R1_EXECUTED=NO
SUDO_USED=NO
```

Historical evidence is untouched. This record is new.

## 1. ROOT_CAUSE

The row was scored on a global error proxy:

```python
"drm_fds_enumerated": "PASS" if gpu_proven and coverage["fd_error_count"] == 0 else "FAIL",
```

`fd_error_count` is a sum over every PID of every error of any kind. It cannot
distinguish four materially different worlds, and it was demonstrated to do so
by executing the real expression:

```text
0 errors, 0 DRM fds on the whole host           -> PASS
0 errors, 12 DRM fds, every fdinfo empty       -> PASS
0 errors, 12 DRM fds, all fully attributed     -> PASS
1 vanished process mid-sweep                    -> FAIL
```

Three compounding causes:

1. **The description named fields nobody inspected.** `drm-client-id`,
   `drm-pdev` and `pasid` appeared only as prose in the docstring, the row
   description and the capability matrix. No code parsed `fdinfo`.
2. **`root_coverage` did not export what the row needed.** Of the five fd
   counters the sweep computes, only `fd_error_count` reached the dict the
   matrix consumes, so the row could not have been correct even if attempted.
3. **The third state had been lost.** `OWNERSHIP-CLOSURE-ATTEMPT-20260925T232522Z.md:124`
   records this row as `PARTIAL` — "8 FDs / 6 PIDs readable; full set not
   enumerable". The implementation was binary.

## 2. SEMANTICS

`drm_fd_enumeration_state(coverage, gpu_proven)` returns `(state, reason)` and
distinguishes A-F:

| | Condition | State |
|---|---|---|
| A | GPU identity not proven | `NOT_EVALUATED` |
| A | universe not enumerable, 0 clients seen | `UNKNOWN` |
| A | universe not enumerable, clients seen | `PARTIAL` |
| B | universe enumerable, 0 DRM fds | `PASS` |
| C | fdinfo unreadable on some found fd | `PARTIAL` |
| D | `drm-client-id` absent on some read fd | `PARTIAL` |
| D | `drm-pdev` absent on some read fd | `PARTIAL` |
| E | `pasid` absent on some read fd | `PARTIAL` |
| — | all found fds fully attributed | `PASS` |

A vanished process is a **race**, not lost coverage: the FD it held died with
it. It is counted in `fd_race_pids` and reported in the reason, and it does not
by itself change the state. A denied or otherwise broken fd table, or a
per-FD `readlink` failure, is **lost coverage**, because that PID's client set
cannot be established.

Absence of any field is never counted as success.

### PASID

`pasid` is amdgpu-specific, so its absence is only meaningful once the matched
node is proven to be the amdgpu device — which `gpu_proven` and the device set
already establish. It is therefore required, and its absence yields `PARTIAL`
with the count reported. No availability was invented: the field is checked for
presence in the text actually read, never assumed.

`drm-client-id` and `drm-pdev` are DRM-core fields for a DRM file descriptor
and are likewise required.

## 3. WHAT WAS ADDED

```text
fdinfo_attribution(text)          presence of drm-client-id / drm-pdev / pasid
scan_fds()["attribution"]         per-sweep counts, 5 keys
coverage[...]                    7 new accumulator keys
root_coverage exports             7 new keys, so the matrix can score the row
fd_race_pids / fd_universe_blocked_pids   per-PID, each counted at most once
```

`root_coverage` grows from 21 to 28 keys. The client records in `matched` are
unchanged: still exactly `fd`, `target`, `fdinfo`.

## 4. FALSIFICATION

The pre-fix collector was reconstructed by re-applying the fdinfo fix to the
verified pre-fdinfo state; the result reproduces `HASH_BEFORE` **byte for
byte**.

```text
pre-fix  (fe0b740c…)  Ran 32  FAILED (failures=6, errors=22)
post-fix (6f722820…)  Ran 32  OK
```

The same seven scenarios through the real `ownership_matrix`, before and
after:

| Scenario | pre-fix | post-fix |
|---|---|---|
| complete sweep, 0 DRM fds | PASS | PASS |
| fds + fdinfo + client-id + pasid | PASS | PASS |
| fds found, fdinfo unreadable | FAIL | PARTIAL |
| fdinfo read, no attribution fields | PASS | PARTIAL |
| vanished process | FAIL | PASS |
| permission error | FAIL | PARTIAL |
| 10 attributed + 2 incomplete | PASS | PARTIAL |

**Pre-fix collapses seven materially distinct worlds into two states.** Four of
them — "no client at all", "twelve clients fully attributed", "twelve clients
with no attribution whatsoever", "ten attributed and two not" — all read
`PASS`. Post-fix each carries its own reason string, and the test
`test_every_required_case_yields_a_distinct_verdict_pair` asserts the seven
reasons are pairwise distinct.

## 5. HISTORICAL ANNOTATION — R1-20260926T030435Z

```text
drm_fds_enumerated=FAIL   NO_INFORMATIVE_FOR_ATTRIBUTION
```

The recorded `FAIL` with `"1 FD read errors across 283 PIDs"` does **not**
demonstrate an absence of `drm-client-id` or PASID. The single error was
`root_fd_disappeared_count=1` with `root_fd_permission_denied_count=0` and
`root_visibility_complete_for_snapshot=true` — a process that vanished during
the sweep, which the collector's own code calls "a race, not an isolation
fact".

The available historical evidence therefore permits **no inference** about the
DRM/PASID attribution state of that run, in either direction. All twelve GPU
clients were recorded with `fdinfo: ''`, which under the corrected route means
the read failed; under the route in force at the time it means nothing.

The alternative `PASS` that the same expression would have produced is equally
insufficient: it would have been returned for a host with no DRM client at all.

The row's previous state, `PARTIAL`, is therefore not recoverable from R1-4 and
must not be read as superseded.

## 6. AUTO-REVISION

```text
PREVIOUS_CLAIM_REFUTED=YES
```

1. **"Con la ruta fdinfo reparada, esa fila puede recibir su significado
   pretendido."** — REFUTED, already recorded. The route supplies the data; the
   decision expression still looked at no DRM fact. Demonstrated by execution.
2. **"Contar los fallos de fdinfo hace que `drm_fds_enumerated` sea sensible a
   ellos por primera vez. Es la consecuencia correcta."** — REFUTED IN PART.
   It mixed fdinfo read failures with process-disappearance races in one
   bucket, which this row cannot separate. Now separated by reason.
3. **"`fd_error_count == 0` era un proxy suficiente."** — REFUTED. Executed:
   four different worlds returned PASS.
4. **"Un error de proceso desaparecido justificaba directamente FAIL."** —
   REFUTED. A vanished PID holds no FD after it dies; it is a race, reported
   but not scored as lost coverage.
5. **"El mero almacenamiento de `fdinfo` implicaba que la fila lo estaba
   utilizando."** — REFUTED. The value was copied into the bundle at L2139 and
   never read by any decision.

One claim from this session needed correcting mid-fix: I wrote a replacement
assertion in `test_privileged_read_collector.py` that was unreadable and then
wrong in intent. It now compares the row that degradation actually changes.

## 7. SCOPE HELD

```text
CLIENTS_PASID_ATTRIBUTABLE=UNCHANGED
  description and decision expression byte-identical
OWNERSHIP_CRITERION_ROWS=11 rows, same order
OWNERSHIP_EXTERNAL_ROWS=unchanged (writers_resolved R2, guard_and_restore R3)
R1_EXECUTED=NO  SUDO_USED=NO  COMMITS=0
```

Three pre-existing tests encoded the old rule and were updated rather than
deleted, each keeping its safety intent:

- `test_fd_error_can_never_produce_a_coverage_pass` — now asserts an fd error
  yields no PASS **unless** it is a classified race, and that the race is
  reported.
- `test_15b_boolean_false_does_not_change_the_matrix` — asserted `"17"` appeared
  in the evidence string, a proxy for the old format. It now asserts the matrix
  changes and that `drm_fds_enumerated` legitimately does not react to
  `fd_error_count` alone.
- `test_defect04_behavioral` — its accumulator fixtures gained the 7 new keys,
  and the pre-fix shape assertion now subtracts both the lowercase contract key
  and the attribution block to reach the historical 20.

`total_pids` is still read strictly with `[]`, so DEFECT-04's property — a
missing `total_pids` is a loud failure — survives. It is read inside the new
helper, and the DEFECT-04 contract test was widened to include that helper.

## 8. HASHES

```text
HASH_BEFORE=fe0b740c19c1557e779005d43e606348a62e28365cfcc1ad05f91f76aa40db2e
HASH_AFTER =6f722820221c75a67ac2…
```

Full `HASH_AFTER` and the four touched test files were verified with
`sha256sum` and `hashlib`; all agree. `R1-20260926T030435Z.json`
(`8806311b8f19a6f6…`) and `R1-20260926T024340Z.json` (`04be7bc4…`) re-verified
intact.

## 9. SYSTEM MUTATION

```text
SUDO_USED=NO   R1_EXECUTED=NO   COMMITS=0
/dev/dri/card1  e2:1  mtime 2026-09-25 23:57:49  unchanged
renderD129      e2:81 mtime 2026-09-25 18:54:56  unchanged
services running 32  unchanged
/run/user/1000/c1-*  0
```

The `card1` sysfs symlink mtime remains at the unexplained 2026-09-26T04:00:10Z
recorded in the previous fix record. `CAUSE=UNKNOWN`, unchanged by this work.

## 10. NEW FINDINGS

```text
FINDING_ID=R1_4_ATTRIBUTION_STATE_UNRECOVERABLE
STATUS=OPEN
ROOT_CAUSE=R1-4 ran with a broken fdinfo route and a proxy-scored row, so the
  DRM/PASID attribution state of that run is not derivable from its own evidence
IMPACT=the row's PARTIAL state from 2026-09-25 cannot be confirmed or superseded
SCOPE=not a code defect; requires a decision on whether to re-run or to annotate
```

No other defect was found during this fix.
