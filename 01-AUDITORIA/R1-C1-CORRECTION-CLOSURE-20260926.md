# R1 · C1 CORRECTION CLOSURE — cierre documental de `AGENTS_V3_RACE_STRICTER_THAN_COLLECTOR`

```text
RECORD_ID=R1-C1-CORRECTION-CLOSURE-20260926
CREATED_UTC=2026-09-26
WORK_CLASS=DOCUMENTATION
SCOPE=closure of the DRM/FD-attribution correction line inside C1
TARGET=01-AUDITORIA/FASE-C1-RUNTIME-PREFLIGHT/privileged_read_collector.py
STATUS=C1_CORRECTION_LINE=CLOSED
C1_OVERALL=NOT_CLOSED   (see §9 LIMITACIONES)
COMMIT=df2406ac9f5744cf4e1a5624aecc423f5b9089a8
COLLECTOR_SHA256=9b6e8d7d0f4dcd6fabc774db745a0a9fce718f513b40376aad8a56d202eccff4
AGENTS_MD_SHA256=52315f993e73ea7c37048bc22c0f8dd40eadd4cef6ca8cc89b5d2de8eef74422
```

This record documents what was learned while correcting one defect line. It does
**not** claim C1 as a whole is finished, does not close any pre-existing open
finding, and does not resolve any pre-existing documented conflict.

---

## 1 · REQUIREMENT ORIGIN

### 1.1 The requirement as recorded

`AGENTS.md` §`Ownership` (lines 173-186) states:

- do not declare `OWNERSHIP=FULL` from `lsof`, `fuser` or a partial `/proc` scan;
- `FULL` requires complete attributable evidence for the RX550's card and render
  nodes, **identified by PCI identity rather than by node name**, plus
  user/root namespaces, DRM FDs, writers, agents, PM, governor, IRQ, scheduler,
  read-ahead, storage, Btrfs, guard and restore;
- if FD visibility is incomplete, a permission is denied, root namespaces are not
  covered, a client is active or a writer is unresolved, then `OWNERSHIP != FULL`;
- "This is a requirement, not a description of any implementation."

`01-AUDITORIA/DOCUMENTATION-ROUTER/DOCUMENTATION-ROUTER.md:225` cites
`` `AGENTS.md` §Ownership `` among the sources for the `OWNERSHIP` topic, and
records that topic as `PARTIAL` with `CURRENT_EVIDENCE=NOT_AVAILABLE`, sourced
from `C1-PREFLIGHT-20260925T061932Z-PRIV.json`. That is the provenance link
that exists in the repository, and that recorded status is prior evidence which
this record does not supersede.

**`UNKNOWN`** — whether the text of `AGENTS.md` §`Ownership` is human-authored
or agent-authored. No evidence in the repository settles authorship. This record
therefore says "the requirement as recorded in `AGENTS.md`" and does not
attribute an author.

### 1.2 Agent formalisation

`privileged_read_collector.py:1546` defines `OWNERSHIP_CRITERION_ROWS`, eleven
rows, under the comment at `:1543-1545` stating that the `AGENTS.md`
11-condition matrix is the only ownership verdict and that the legacy boolean
is non-authoritative. The eleven row names and their descriptions are
**agent-created identifiers** that instantiate the requirement. They are not
verbatim requirement text.

### 1.3 Names created during this correction line

| Name | Created by | Where |
|---|---|---|
| `unresolved_target_count` | agent | `scan_fds()` result |
| `pid_gone()` | agent | module-level, tri-state liveness re-check |
| `fd_absence_proven_pids` | agent | coverage accumulator + `root_coverage` export |
| `drm_fd_enumeration_state()` | agent | R1 line, pre-dates this correction |
| `ObserveExecutionTests`, `LivenessRecheckTests`, `VanishedAbsenceContractTests` | agent | `test_drm_fds_enumerated_behavioral.py` |
| `AGENTS_V3_RACE_STRICTER_THAN_COLLECTOR` | agent | defect ID used in this record |

---

## 2 · THE CONCEPTUAL DEFECT

The corrected line turned on one distinction that the previous implementation
did not represent at all:

> **A process disappearing does not by itself prove that the process did not
> hold the qualifying resource.**

Everything else follows from that. The pre-correction implementation:

1. `scan_fds()` could lose a target-resolution error. When `os.readlink()` on an
   existing FD failed, the loop executed `continue` **before** testing the target
   against the device set, so the FD was never counted as a DRM candidate and
   never recorded as unknown.
2. `PROCESS_DISAPPEARED` was routed to a diagnostic counter (`fd_race_pids`)
   without blocking the empty-universe conclusion, so a vanished PID could
   certify "0 DRM fds found".
3. `drm_fds_enumerated` collapsed materially different worlds. With
   `found=0`, `blocked=0`, `fd_race_pids=1` it returned `PASS` with the reason
   string `universe enumerated, 0 DRM fds found across N PIDs, 1 benign race(s)`.
4. Three worlds were byte-indistinguishable in the coverage vector: a PID that
   disappeared **with proven absence**, one that disappeared **without proof**,
   and one whose FD target could not be read. All three produced the same dict.
5. There was no key that could express "absence of the resource was proven".
   `fd_absence_proven_pids` did not exist.

`OBSERVED` — established by executing the pre-correction code paths against
synthetic fixtures and by the mutation falsification recorded in
`R1-DRM-FDS-ENUMERATED-FIX-RECORD-20260926.md`.

---

## 3 · DEFECT CHAIN

Ordering is by fix record and commit evidence, not by filesystem mtime. **No
mtime is used as chronology anywhere in this record.**

### 3.1 DEFECT-03 — closure scoping in `main() > observe()`

| | |
|---|---|
| Identification | `nonlocal` counters inside `observe()` did not close over `main()`'s scope |
| Evidence | `R1-DEFECT-03-FIX-RECORD-20260926.md`: `HASH_BEFORE=ae115054…`, `HASH_AFTER=1078cc7c…`, `BEHAVIOURAL_TEST=ADDED test_defect03_behavioral.py 9 tests PASS` |
| Root cause | counters assigned in the closure were not the counters read in `main()` |
| Correction | `nonlocal` declarations; verified by executing the extracted `observe()` body |
| Verification | 9 behavioural tests, executed against real extracted source, not inspected text |
| Final state | `CLOSED` per its own record |
| Falsification | a `main()` execution where the five counters diverge from the values `observe()` accumulated |

`NOTE` — this file was **modified during the C1 correction line**: the
correction added a `proc_root` parameter to `observe()`, which required adding
`DEFAULT_PROC_ROOT` and a `pid_gone` stub to this test's harness namespace. The
test's subject (counter scoping) was not changed. `UNKNOWN` — the pre-modification
hash of this file was never recorded, so the modification is attested by the work
log, not by a hash pair.

### 3.2 DEFECT-04 — `total_pids` contract between producer and consumer

| | |
|---|---|
| Identification | `root_coverage` exported `TOTAL_PIDS` but the matrix read `coverage["total_pids"]` strictly |
| Evidence | `R1-DEFECT-04-FIX-RECORD-20260926.md`; enforced today by `test_defect04_behavioral.py` `test_a_missing_total_pids_is_a_loud_failure` |
| Root cause | producer and consumer disagreed on the key name and on strictness |
| Correction | lowercase `total_pids` exported from the same accumulator cell that `TOTAL_PIDS` is derived from |
| Verification | 13 tests, including a reconstruction that must yield exactly the 20-key pre-fix shape |
| Final state | `CLOSED`; key count now 29 after the correction line added `fd_absence_proven_pids` |
| Falsification | dropping the lowercase key must raise `KeyError` in `drm_fd_enumeration_state` |

### 3.3 DEFECT-05 — storage whole-disk attribute base

| | |
|---|---|
| Identification | whole-disk attributes read from the partition node |
| Evidence | `test_defect05_behavioral.py` docstring: `resolve_block_device()` computes `parent_sysfs`, both consumers used `ROOT_BLOCK_SYSFS`; "In R1 run 4 this produced 416 ERROR reads (16 initial + 400 across 25 samples)" |
| Root cause | `queue/` and `device/` exist only on whole-disk sysfs nodes |
| Correction | `OBSERVED` in the collector at `:1480-1487` (`disk_sysfs = disk_level_sysfs(storage) or block_sysfs`, comment `DEFECT-05`) |
| Verification | 32 tests, incl. a synthetic replica tree |
| Final state | code corrected and covered |
| **`NOT_AVAILABLE`** | a `R1-DEFECT-05-FIX-RECORD-20260926.md` **does not exist**. The fix record for this defect is missing from the repository. This is a documentation gap, not a claim that the fix is unverified. |

### 3.4 fdinfo path — `scan_fds()` fdinfo route

| | |
|---|---|
| Identification | fdinfo read from `/proc/<pid>/fd/fdinfo/<n>`, which does not exist |
| Evidence | `R1-FDINFO-PATH-FIX-RECORD-20260926.md`: `DEFECT_SCAN_FDS_FDINFO_PATH=CLOSED`; code comment at `scan_fds()` states the previous `fd_path.parent ("fd")` produced `/proc/<pid>/fd/fdinfo/<n>`, "so every DRM client was recorded with an empty fdinfo" |
| Root cause | fdinfo is a sibling of `fd/`, not a child |
| Correction | path built from `fd_dir.parent` |
| Verification | 17 tests, incl. `test_scan_fds_reports_attribution_for_each_matched_client` and a failure-visibility test |
| Final state | `CLOSED` per its own record |
| Falsification | a matched DRM client whose `fdinfo` is empty while the path is correct |

### 3.5 DEFECT-06 — G-06 summary must derive from read state

| | |
|---|---|
| Identification | `gap_results["G-06"]["summary"]` was a string literal asserting observation unconditionally |
| Evidence | `test_defect06_behavioral.py` docstring: the summary claimed values were observed "In R1 run 4 every one of the 16 queue reads was ERROR"; the entry is located in the real `gap_results` assignment and that exact AST node is compiled and evaluated |
| Root cause | prose not derived from state |
| Correction | the node is now a call; evaluating it runs the real derivation |
| Verification | 20 tests over cases A-D, executed against the real AST node |
| Final state | 20 tests pass; the fix record for DEFECT-06 is **`NOT_AVAILABLE`** (no `R1-DEFECT-06-FIX-RECORD` exists) |

### 3.6 `R1_4_ATTRIBUTION_STATE_UNRECOVERABLE` — **still OPEN, not closed here**

Quoted from `R1-DRM-FDS-ENUMERATED-FIX-RECORD-20260926.md:233`:

```text
FINDING_ID=R1_4_ATTRIBUTION_STATE_UNRECOVERABLE
STATUS=OPEN
ROOT_CAUSE=R1-4 ran with a broken fdinfo route and a proxy-scored row, so the
  DRM/PASID attribution state of that run is not derivable from its own evidence
IMPACT=the row's PARTIAL state from 2026-09-25 cannot be confirmed or superseded
SCOPE=not a code defect; requires a decision on whether to re-run or to annotate
```

This record **does not close it** and **does not re-run R1-4**. Its own scope
requires a decision that has not been taken.

### 3.7 `AGENTS_V3_RACE_STRICTER_THAN_COLLECTOR` — the corrected defect

| | |
|---|---|
| Identification | `drm_fd_enumeration_state()` returned `PASS` on a sweep whose only anomaly was a vanished PID, with no evidence that the PID held no DRM resource |
| Evidence | `AGENTS.md` (commit `6fe40b2`) §measurement discipline requires **two independent facts** for `RACE`: disappearance proven **and** evidence it held no qualifying resource; the implementation satisfied neither as a precondition |
| Root cause | `CONTRACT_MISMATCH` primary — the two-fact rule did not exist when the code was written; the pre-V3 `AGENTS.md` at `54b3ea8` (12649 bytes) contains **0** occurrences of `RACE`, `COVERAGE_LOSS`, `disappear`, `desaparec`, `proceso`. Secondary `WRONG_CONDITION` for the per-FD readlink case, which contradicts the R1 record's own words ("a per-FD `readlink` failure … is lost coverage"). Also `LOSS_OF_EVIDENCE` in `scan_fds()`. Also `TEST_GAP` in which the suite asserted the wrong behaviour |
| Correction | §4 |
| Verification | §4.6, §5 |
| Final state | `FIXED`; falsified by mutation and re-measured on real `/proc` |
| Falsification | a real vanished PID, absence unproven, and a `PASS` result |

---

## 4 · THE CENTRAL DEFECT, BEFORE AND AFTER

### 4.1 `scan_fds()`

| | BEFORE | AFTER |
|---|---|---|
| FD target unreadable | `continue` before the device test; not counted, not recorded | `unresolved_target_count += 1`, error tagged `"stage": "target"`, FD never silently "not DRM" |
| Why `stage` matters | — | lets `observe()` tell a vanished **target** (resource unknown → lost coverage) from an `fdinfo` disappearance (resource already matched → characterisation incomplete) |

### 4.2 `pid_gone()`

Tri-state. `UNKNOWN` is a real outcome and is **never** collapsed into `GONE`; an
unreadable procfs entry is not evidence that a process is gone, and the failure
is surfaced in the returned `error`.

### 4.3 `observe()`

| | BEFORE | AFTER |
|---|---|---|
| PID-level disappearance | `fd_race_pids` only | `fd_race_pids` **and** `fd_universe_blocked_pids` |
| per-FD vanished target | `pid_raced = True` only | `pid_raced = True` **and** `pid_blocked = True` |
| absence proof | did not exist | clean table + no device match + `pid_gone() == GONE` → `fd_absence_proven_pids` |
| a PID with any scan error | — | can never be an absence proof |

Resulting invariant, verified on real data: **`races > 0` implies
`blocked > 0` or `found > 0`.**

### 4.4 `drm_fd_enumeration_state()`

`OBSERVED` verdict alphabet after the correction:
`{NOT_EVALUATED, UNKNOWN, PARTIAL, PASS}`. The string `RACE` is not and never was
a member of it — that is why the misclassification happened one level upstream
and was laundered downstream as `PASS`.

| | BEFORE | AFTER |
|---|---|---|
| `found=0, blocked=0, races=1` | `PASS` — "0 DRM fds found … 1 benign race(s)" | `UNKNOWN` — "absence NOT proven for 1 of them" |
| `found=0, races=1, absence_proven=1` | indistinguishable from the above | `PASS` — "absence of a DRM resource proven" |
| `found>0` with a vanished holder | "… 1 benign race(s)" | "… counted as diagnosis only" |
| all three `"benign race"` emissions | present | removed |

### 4.5 The four states the criterion must now separate

| World | Verdict |
|---|---|
| proven absence | `PASS`, and only then |
| unproven disappearance | `UNKNOWN` |
| unreadable target / lost coverage | `UNKNOWN` if nothing found, `PARTIAL` if a client was seen |
| proven DRM resource held | counted; characterisation `PARTIAL` if fdinfo incomplete; **never** called benign |

### 4.6 Falsification of the correction

- **Static, by mutation.** A throwaway copy of the collector with
  `and root_fd_disappeared == 0` added to the real `root_visibility_complete`
  expression made the race-invariance assertions fail on exactly
  `vanished=1, 5, 500` and nothing else.
- **Export contract.** Removing the `fd_absence_proven_pids` line from the
  `root_coverage` export made `test_root_coverage_exports_every_key` fail.
- **Real `/proc`, unprivileged.** One genuine kernel-produced
  `FileNotFoundError [Errno 2]` on `/proc/<pid>/fd/0` tagged `stage="target"`,
  `PROCESS_DISAPPEARED` → `race=1 blocked=1 proven=0` → `UNKNOWN`.
- **Real `/proc`, privileged.** 283 PIDs, `races=1 blocked=1 proven=0` →
  `PARTIAL`. `fd_absence_proven_pids = 0` in **both** privileged and
  unprivileged passes.

---

## 5 · METHOD LESSONS

1. **Absence of evidence is not evidence of absence.** A field that may be
   present must discriminate the empty universe, the object observed, and
   insufficient coverage.
2. **A swallowed error is not absence.** A discarded read failure replaced by an
   empty value is incomplete evidence and the failure must be surfaced.
3. **A race is not an absence.** This was the central defect.
4. **Partial coverage cannot produce `PASS`.**
5. **A function whose alphabet is too poor cannot express a correct verdict.**
   The row could only say `PASS/FAIL/UNKNOWN`; the correct distinction had to be
   pushed upstream into new counters.
6. **Tests must separate the worlds the criterion claims to separate.** The
   shipped suite paired its only race case with 12 already-attributed clients,
   so no case ever exercised "race with zero DRM fds" — the only world where the
   defect was visible.
7. **A test that restates constants inside itself proves nothing.**
   `test_medium_fixes.py::test_P44b_…` asserted `denied == 0 and other == 0`
   against literals written in the test body, never calling the collector, with
   its `vanished` parameter used only in a failure message. It was replaced by
   one that evaluates the collector's real expression.
8. **A green suite does not prove semantic correctness.** 98/98 passed while the
   defect was live, because two tests asserted the wrong behaviour, including
   the literal string `"benign race"`.
9. **Falsification tests carry the weight.** Every fix here was checked by
   mutating a copy of the code and requiring the new assertion to fail.
10. **A conclusion keeps its coverage limits.** The privileged pass established
    FD-read coverage; it did not establish engine activity.

---

## 6 · PRIVILEGED EVIDENCE — A/B

Measured in the same time window on the same committed collector.

| | A · unprivileged | B · root |
|---|---|---|
| `EUID` | 1000 | **0** |
| `PRIVILEGE_STATE` | `PRIVILEGE_NOT_ROOT` | `PRIVILEGE_OBSERVED_ROOT` |
| observable PIDs | 280 | 283 |
| `fd/` readable | 70 | **283/283** |
| `fdinfo/` readable | 70 | **283/283** |
| PIDs lost to coverage | 210 | **0** |
| `PERMISSION_DENIED` | 222 | **0** |
| `PROCESS_DISAPPEARED` | 1 | 1 |
| `unresolved_target_count` | 111 | 1 |
| `fd_race_pids` | 1 | 1 |
| `fd_universe_blocked_pids` | 212 | 1 |
| `fd_absence_proven_pids` | **0** | **0** |
| `drm_fds_found` | **1** | **12** |
| `drm-client-id` / `drm-pdev` / `pasid` | 1 / 1 / 1 | **12 / 12 / 12** |
| `drm_fds_enumerated` | `PARTIAL` | `PARTIAL` |

**The prior conclusion "1 DRM client" is REFUTED by widened coverage.** The
evidence that refuted it: `scan_fds()` under `euid 0` over the uid-0 PIDs that
were unreadable in pass A. The 12 clients are `systemd` (pid 1), `systemd-logind`
(pid 993), `kwin_wayland` (pid 1825, five on `card1` and four on `renderD129`)
and `Xwayland` (pid 1923).

**This was NOT a collector defect.** The collector scored the row `PARTIAL` in
both passes, never `PASS`, precisely because coverage was not established. A
verdict of `1` was an artefact of read coverage, correctly labelled incomplete.

`fd_absence_proven_pids = 0` in both passes: once full read coverage was
established, the collector still credited **no** absence, because the one
vanished PID had an unresolvable target. That is the V3 rule behaving correctly
under privilege.

Falsification: a further root pass finding a different client count, or a
`PERMISSION_DENIED` appearing under root (procfs `hidepid`, a sandbox), or a
`GONE` liveness result on a clean scan.

---

## 7 · PASID · DEBUGFS · ENGINE — four separate things

| Concept | Source | State | What it proves |
|---|---|---|---|
| `pasid` in `fdinfo` | `/proc/<pid>/fdinfo/<fd>` | **`OBSERVED`** 12/12 | the kernel exposes the field on that FD |
| DRM clients in debugfs | `/sys/kernel/debug/dri/129/clients` | **`PROVEN`** | 4 client entries, 715 bytes |
| engine activity | — | **`UNKNOWN`** | nothing established it |
| process → engine | — | **`NOT_AVAILABLE`** | no source relates them |

debugfs measurement, `EUID 0`, function `debugfs_client_attribution(identity)`:

```text
DEBUGFS_CLIENT_ATTRIBUTION = 'PROVEN'
reason                     = 'MINOR_DERIVED_AND_DRIVER_CONFIRMED'
derivation                 = 'minor 129 read from discovered render node renderD129'
clients_path               = '/sys/kernel/debug/dri/129/clients'
read_status                = 'OK'
amdgpu_device_count        = 1
clients                    = 715 bytes, 4 data rows
```

```text
                 command  tgid dev master a   uid      magic   name       id
            kwin_wayland  1825 129   n      n  1000          0  <unset>     47
          systemd-logind   993   1   y      y     0          0  <unset>     64
            kwin_wayland  1825   1   n      y  1000          1  <unset>     65
            kwin_wayland  1825   1   n      n  1000          0  <unset>     71
```

**Why these must not be combined.** `clients` carries `command`, `tgid`, `dev`,
`master`, `a`, `uid`, `magic`, `name`, `id` — no engine, no PASID. `fdinfo`
carries `drm-client-id`, `drm-pdev`, `pasid` — no command, no engine. Neither
`pasid` nor `drm-client-id` is engine state.

Direct evidence that the distinction is real and not pedantic: the one client
visible unprivileged (Xwayland, pid 1923) had `drm-client-id` and `pasid`
**present** while its own fdinfo reported `drm-total-cpu=0`,
`drm-resident-cpu=0`, `drm-resident-vram=0`. Attribution present, activity zero.

**`NOT_AVAILABLE` for process → engine.** `drm-client-id` and `clients.id` look
like the same key, but no collector function joins them, and the privileged
sweep recorded only the aggregate `12/12/12`, not the per-FD ids. The sweep
(~02:37) and the `clients` read (02:42) are different windows, in which ids may
be reassigned. **No mapping is asserted.** This is *not* recorded as a
`CONFLICT`; it is recorded as not measured.

---

## 8 · PM

`pm_snapshot(device_sysfs)`, `EUID 1000`, no privilege required.

```text
GPU_IDENTITY_STATUS     = PROVEN
device_sysfs            = /sys/class/drm/card1/device
PM_METRICS              = READ
paths read              = 27
amdgpu_parameters       = 96
paths NOT OK            = 12
```

`device_sysfs` is **not** a remembered path: it comes from
`GPU_NODE_PATHS["device_sysfs"]`, built at collector `:641` as
`sysfs_root/class/drm/<card>/device` with `<card>` derived from the proven BDF.

Values read (15 of 27):

```text
power/control               = auto
power/runtime_status        = suspended
power/autosuspend_delay_ms  = 5000
power/wakeup                = disabled
current_link_speed          = 5.0 GT/s PCIe
current_link_width          = 4
max_link_speed              = 8.0 GT/s PCIe
max_link_width              = 8
mem_info_vram_total         = 2147483648
mem_info_vram_used          = 5439488
mem_info_vis_vram_total     = 268435456
mem_info_vis_vram_used      = 5439488
mem_info_gtt_total          = 6194638848
mem_info_gtt_used           = 12226560
```

The 12 failures: `OSError [Errno 16] Device or resource busy` on
`gpu_busy_percent`, `mem_busy_percent`, `pp_power_profile_mode`, `pp_dpm_sclk`,
`pp_dpm_mclk`, `pp_dpm_pcie`, `pp_cur_state`, `pp_mclk_od`, `pp_num_states` and
three more; `FileNotFoundError` on `ppfeaturemask`. Consistent with
`runtime_status=suspended` — PP/DPM attributes on a suspended amdgpu device
return `EBUSY`.

**`PM_METRICS=READ` does NOT mean the whole PM surface was read.** The function
returns `READ` regardless of how many individual paths failed, and the
`pm_observed` row compares only `pm_status == "READ"`, so it would read `PASS`
with a third of the surface unreadable.

| Scope | Classification |
|---|---|
| basic PM state (`power/*`) | **`OBSERVED`** |
| complete PM surface | **`INCOMPLETE` / `LIMITATION`** |

**This semantics is recorded, not changed.** Correcting it would be a production
change and is out of scope.

Falsification: `power/runtime_status` becoming unreadable, or `EBUSY` clearing
once the device is active and the 12 attributes turning `OK` — which would show
the limitation came from suspension, not from the function.

---

## 9 · CURRENT LIMITATIONS — state, not defects

| Item | State | Why it cannot be closed by measurement |
|---|---|---|
| `ownership_matrix` | `DEFERRED` / `REQUIRES_MAIN_R1` | the matrix consumes `card_complete`, `render_complete`, `root_namespace_complete`, `user_namespace_complete`, which **no function emits**; they are computed inline in `main()`'s export. Consuming the matrix without `main()` would mean transcribing production expressions. The stored R1-4 bundle does carry all four, but it has 21 keys and no `drm_*`/`fd_*` block, so it is pre-fix and incomparable |
| Btrfs | `DEFERRED` / `REQUIRES_MAIN_R1` | `parse_mountinfo()` exists, but `btrfs_status` and `btrfs_observation` are built inline in `main()` and depend on parent-bundle admission |
| `active_agents` | `DEFERRED_BY_PROHIBITION` | `systemctl_rows()` is isolable but `systemctl` is prohibited; the filter that decides `active_service_rows` is inline in `main()` |
| engine activity | `UNKNOWN` | no authorised source exposes it; GFX8 counters prohibited |
| process → engine | `NOT_AVAILABLE` | needs a same-window capture of per-FD `drm-client-id` alongside `clients.id` |
| `R1_4_ATTRIBUTION_STATE_UNRECOVERABLE` | `OPEN` | pre-existing; its own scope requires a re-run-or-annotate decision that has not been taken |
| namespace denominators | `MEASURABLE_WITH_EXISTING_INTERFACE` | the six counters are already produced by `observe()`; the two `*_complete` booleans are inline in `main()` |

None of these is closed by inference here.

---

## 10 · GIT AND TRACEABILITY

```text
HEAD                    = df2406ac9f5744cf4e1a5624aecc423f5b9089a8
COLLECTOR_SHA256        = 9b6e8d7d0f4dcd6fabc774db745a0a9fce718f513b40376aad8a56d202eccff4
AGENTS_MD_SHA256        = 52315f993e73ea7c37048bc22c0f8dd40eadd4cef6ca8cc89b5d2de8eef74422
README_SHA256           = 4524f6f6f1bd9e699092dfd0a14fb8c0dc8ee6c8517c01ff0388b836297df45e
SUITE                   = 291/291 OK   (unittest discover in FASE-C1-RUNTIME-PREFLIGHT)
COMMIT_FILES            = 12 (1 production + 11 tests), exact
STAGED                  = 358   pre-existing, NOT part of C1
UNTRACKED               = 23    pre-existing, NOT part of C1
```

The 291 figure is the FASE-C1 unit suite under `unittest discover` measured
after the commit. It is **not** a resolution of the pre-existing `C1` test-count
`CONFLICT` recorded at `DOCUMENTATION-ROUTER.md:110`
(`24/24` vs `37/37` vs `44/44`, source
`DOCUMENTARY-RECONCILIATION-20260925.md` §`C1_TESTS` lines 187-201), which
concerns the C1 **isolation** test counts, a different scope. That conflict is
preserved unresolved and referred to its declared `CONFLICT_SOURCE`.

The 358 staged entries and 23 untracked entries pre-date this work, were not
audited, were not reverted, and are **not** claimed as C1 content.

---

## 11 · WHAT THIS RECORD DOES NOT CLAIM

- It does not claim C1 as a whole is closed.
- It does not close `R1_4_ATTRIBUTION_STATE_UNRECOVERABLE`.
- It does not resolve the pre-existing `C1` test-count `CONFLICT`.
- It does not assert authorship of `AGENTS.md` §`Ownership`.
- It does not assert an engine relation, nor engine activity.
- It does not use filesystem mtime as chronology. The unexplained
  `card1` sysfs symlink mtime of `2026-09-26T04:00:10Z` noted in
  `R1-DRM-FDS-ENUMERATED-FIX-RECORD-20260926.md` remains `CAUSE=UNKNOWN` and is
  **not** used here as evidence of anything.
- It does not supply the missing `R1-DEFECT-05-FIX-RECORD` or a DEFECT-06 record.
