# AGENTS.md — RX550-INVESTIGACION

## Scope and identity

These are persistent project instructions for OpenCode V2. This file applies to the project root and its subdirectories. It does not grant authorization to execute anything.

Project: reproducible investigation of the RX 550 Polaris12/GFX8, its power/clock/VRAM/I/O boundaries, workload behavior, and evidence quality.

Canonical navigation and state:

- `01-AUDITORIA/DOCUMENTATION-ROUTER/DOCUMENTATION-ROUTER.md` — **START HERE for any documentation question**
- `README.md`
- `PROBLEM-STATUS-FINAL.md` — current problem matrix
- `PATCH-REGISTRY-FINAL.md` — current corrections registry
- `04-IMPLEMENTACION/IMPLEMENTATION-SAFETY-RULES.md`
- `04-IMPLEMENTACION/C1-ISOLATION-DESIGN-v1.0.md`
- `04-IMPLEMENTACION/C1-ISOLATION-AUTOMATOR.md`
- `01-AUDITORIA/FASE-C1-RUNTIME-PREFLIGHT/`

`00-INDICE/MASTER-RESEARCH-STATUS.md` and `00-INDICE/R2-GLOBAL-DOCUMENTATION-MAP.md` are
historical navigation. `MASTER-RESEARCH-STATUS.md` has 30 inbound references but **does not
hold the current state**: its 2026-09-25 overlay delegates to the root documents above. Do not
enter through it to answer a current-state question.

The project prioritizes reproducible evidence over hypotheses, rankings, convenience, or optimistic interpretation.

## PROPOSED_AGENTS_ROUTING_RULES

Routing rules. These govern **how to find documentation**, not what to execute. They grant no
authorization of any kind.

1. **Use the router first.** Before reading documentation in this project, open
   `01-AUDITORIA/DOCUMENTATION-ROUTER/DOCUMENTATION-ROUTER.md` and classify the question by
   `QUESTION_TYPE` and `TOPIC`. It gives the `PRIMARY` source for all 68 topics.
2. **Never sweep the repository for a localized question.** Do not list, grep or read broadly
   to answer a question the router can route. The repository has 1576 documentation rows of
   which 1321 are raw measurement artifacts.
3. **Declare `TEMPORALITY` and `HOST_SCOPE`** with any factual answer about state.
4. **Three host identities coexist and none may be assumed equivalent:**

   | `HOST_SCOPE` | SO | kernel | Mesa | RX550 `cardN` |
   |---|---|---|---|---|
   | `HOST-A` | Nobara 44 | `7.2.4` / `7.2.6` | 26.2.2 / 26.2.3 | `card1` |
   | `HOST-B` | Nobara 43 | `6.18.2-…fc43` | 25.3.2 | `card2` |
   | `HOST-C` | Nobara 44 | `7.1.3-…fc44` | 26.2.3 | `card1` |

   `HOST-A` = previous disk (1444 rows). `HOST-B` = capture 2026-09-25T13:58Z, the root
   documents. `HOST-C` = the live host, described by only 2 documents. `UNKNOWN` = the document
   declares no host (1406 rows) — never silently assign one.
5. **Historical evidence is not current state.** If a current-state question has only
   historical evidence, answer `CURRENT_EVIDENCE=NOT_AVAILABLE`, state what historical evidence
   exists, and mark it historical. Do not present it as current.
6. **`PRIMARY` before `SECONDARY`.** Do not read `SECONDARY` if the `PRIMARY` answers fully.
7. **Follow `RAW` only when needed,** and always via
   `EXPERIMENT_DIR → EXPERIMENT_MD → artifact`. Never open a raw artifact before reading the
   `.md` that interprets it.
8. **Never convert `UNKNOWN`, `NOT_AVAILABLE` or `CONFLICT` into `PASS`, and never convert
   `HISTORICAL` into `CURRENT`.**
9. **Preserve `CONFLICT`.** When sources disagree, return both with their `TEMPORALITY` and
   `HOST_SCOPE`. Do not pick one. There are 6 registered conflicts; see router §2.
10. **`NOT_AVAILABLE` is a valid final answer.** Do not create documentation to fill a gap.
    `BACO`, `FIREFOX`, `GRUB` and `UDEV` have no primary source by design.
11. **Consult external documentation when local evidence is insufficient** — for upstream
    kernel/Mesa behavior, API facts, or when the user asks for external current information.
    Mark the result `EXTERNAL`; never present it as evidence about this host.
12. **Report broken references, do not repair them.** Use
    `REFERENCE_STATUS=BROKEN` with its `REASON` (`REORG-2026-09-23`, `OLD-DISK-FILE`,
    `RUNTIME-UNVERSIONED`, `AMBIGUOUS-PATH`).
13. **No historical patch is applied to the current host.** All 13 `SYSTEM_PATCH` entries in
    `01-AUDITORIA/PATCH-RECOVERY/PATCH-REGISTRY-RECOVERED.md` §B have `NEW_DISK_APPLIED=NO`,
    verified 2026-09-25T22:22Z. The router recognizes `STATIC_PROJECT_PATCH`, `SYSTEM_PATCH`,
    `EVIDENCE` and `HYPOTHESIS`; it never applies, cherry-picks or builds any of them.
14. **This file holds rules, not the documentation database.** Do not copy topic tables or
    source paths here.
15. **A version or an installed package is not proof of operation.** When stating the state of
    a driver, service or system on a host, use the router's operational tokens and do not
    substitute one for another:
    `VERSION_PRESENT` ≠ `PACKAGE_PRESENT` ≠ `DRIVER_PRESENT` ≠ `DRIVER_OPERATIONAL` ·
    `SERVICE_PRESENT` ≠ `SERVICE_ACTIVE` · neither implies `SYSTEM_CHANGE_APPLIED`.
    Observed on the live host: `mesa-dri-drivers` is `PACKAGE_PRESENT` but
    `mesa-vulkan-drivers` is **absent**, so `DRIVER_OPERATIONAL` for RADV is `NOT_AVAILABLE`;
    `kalm*` and `system-autopilot*` are `SERVICE_ABSENT` (0 units), never `SERVICE_ACTIVE`.
    Router §3bis carries the full table.

Supporting structures, loaded on demand: router metadata
`01-AUDITORIA/DOCUMENTATION-ROUTER/DOCUMENTATION-INVENTORY-ROUTING.tsv` (1576 rows, includes
`EXPERIMENT_DIR`, `EXPERIMENT_MD`, `HOST_SCOPE`, `HOST_SCOPE_BASIS`); thematic knowledge
`01-AUDITORIA/DOCUMENTATION-CENSUS/DOCUMENTATION-TOPICS.md`; gaps and conflicts
`01-AUDITORIA/DOCUMENTATION-CENSUS/DOCUMENTATION-GAPS.md`. The census inventory
`01-AUDITORIA/DOCUMENTATION-CENSUS/DOCUMENTATION-INVENTORY.tsv` is frozen; the routing TSV is
derived from it and adds fields without altering it.

## Evidence vocabulary

Use these labels consistently:

- `OBSERVED`: directly read or recorded from a source.
- `SUPPORTED`: supported by the defined evidence and gates.
- `PLAUSIBLE`: plausible but not established.
- `UNKNOWN`: evidence is insufficient.
- `NOT_AVAILABLE`: the required source or artifact is unavailable.
- `CONFLICT`: sources disagree.
- `FAIL`: an explicit gate failed.
- `DEFERRED`: intentionally not performed or requires later authorization.

Never convert `UNKNOWN`, `NOT_AVAILABLE`, or `CONFLICT` into `PASS` by inference. Use `SOURCE=UNKNOWN` when no source exists.

Always separate:

1. observed fact;
2. interpretation;
3. hypothesis;
4. causal claim.

Correlation, coincidence, a closed FD, a quiet unit, a static test, or a plausible mechanism is not proof of causality.

## Investigation method

When a question is not confirmable:

1. Read the relevant existing project documents and preserved evidence first.
2. Consult official documentation or other reliable sources when the project documents do not resolve a factual interface or tool behavior.
3. Prefer safe, read-only investigation when more evidence is needed.
4. Do not invent paths, values, thresholds, hashes, timestamps, identities, or results.
5. Do not stop solely because evidence is missing if it can be obtained by a safe, authorized read; stop and mark `DEFERRED` when the next step requires prohibited authority or mutation.

Record provenance for every new claim: source, timestamp, value, classification, and limitations.

## Safety and authorization

Never execute destructive, privileged, persistent, or system-changing actions without explicit user authorization for that exact action. Never broaden an existing authorization.

Classify work explicitly as one of:

- `READ_ONLY/EVIDENCE`
- `DOCUMENTATION`
- `STATIC_IMPLEMENTATION`
- `RUNTIME_PREFLIGHT`
- `RUNTIME_EXECUTION`
- `SYSTEM_CHANGE`

Unless explicitly authorized, do not:

- run C1, `run_c1()`, or `C1 --run`;
- create or materialize runtime v2;
- use `sudo` or privileged authentication;
- run `systemctl stop/start/restart` or modify services;
- stop, kill, pause, or isolate processes;
- write GPU, PM, governor, IRQ, scheduler, read-ahead, `/dev/sda`, or other sysfs;
- run benchmarks, A/B, tuning, GFX8 counters, SMART, scrub, or invasive Btrfs reconciliation;
- commit changes.

A mechanism being available is not authorization to use it. `SUDO_AVAILABLE=YES` does not authorize sudo. A static test pass is not runtime validation.

## Current project state

This is context recorded on 2026-09-25; re-read the canonical files before relying on it:

```text
PREFLIGHT=PARTIAL
P0=B__CONTAMINATED_REQUIRES_ISOLATION
OWNERSHIP=PARTIAL
C1=DEFERRED
GO_C1=NOT_AVAILABLE
C1_RUNTIME_VALIDATED=NO
C1_READY=NO
RUNTIME_MATERIALIZED=NO
RUNTIME_VALIDATED=NO
RESTORE_EXECUTED=NO
RESTORE_VALIDATED=NO
HDD_FAILURE=NOT_PROVEN
HDD_HEALTHY=UNKNOWN
BTRFS=CONFLICT
BTRFS_CAUSE=UNKNOWN
G-01=FAIL
G-02=FAIL
G-03=FAIL
G-04=UNKNOWN
G-05=UNKNOWN
G-06=UNKNOWN
G-07=UNKNOWN
G-08=DEFERRED
G-10=DEFERRED
AGENTS_MD=NOT_AVAILABLE ANTES DE ESTA OPERACIÓN
```

The latest preflight evidence is under `01-AUDITORIA/FASE-C1-RUNTIME-PREFLIGHT/`, especially the `C1-PREFLIGHT-20260925T060029Z` bundle and its supplement. It observed DRM clients, incomplete FD visibility, active agents, PM/governor/IRQ/storage context, and no runtime materialization. It did not authorize execution.

## C1

C1 remains deferred. The existence of the C1 implementation and the recorded `54/54` static/unit tests does not mean C1 is ready for runtime.

C1 requires a separately authorized runtime path with all defined gates, complete ownership proof, stable guard evidence, matched same-window Btrfs identity, explicit authorization, and verified restore. Do not promote a static result to `C1_RUNTIME_VALIDATED=YES`.

## Ownership

Do not declare `OWNERSHIP=FULL` merely because `lsof`, `fuser`, or a partial `/proc` scan shows a few clients. `OWNERSHIP=FULL` requires complete, attributable evidence for `card1`, `renderD129`, user/root namespaces, DRM FDs, writers, agents, PM, governor, IRQ, scheduler, read-ahead, storage, Btrfs, guard, and restore.

If FD visibility is incomplete, `PermissionError` exists, root namespaces are not covered, a client is active, or a writer is unresolved, then `OWNERSHIP != FULL`. Use `PARTIAL` or `UNKNOWN`; do not use “parece libre”.

## HDD and Btrfs

Maintain the distinction between storage symptoms, historical artifacts, current identity, and causality:

```text
HDD_FAILURE=NOT_PROVEN
HDD_HEALTHY=UNKNOWN
BTRFS=CONFLICT
BTRFS_CAUSE=UNKNOWN
```

Do not run invasive Btrfs reconciliation, scrub, SMART, or storage writes during an isolation gate without specific authorization. Do not convert historical errors into current failure or causal claims.

## Experiments

Do not run A/B, tuning, benchmarks, GFX8 counters, workload changes, or new experimental tests during an isolation gate unless the user explicitly authorizes that experiment. Preserve negative results and `NOT_RUN` states.

## Documentation and provenance

Preserve:

- source paths and source IDs;
- hashes and versions;
- timestamps and preflight IDs;
- commands and results;
- contradictions and conflicts;
- negative results;
- `UNKNOWN`, `NOT_AVAILABLE`, `DEFERRED`, and prior state;
- state before and after a write.

Never delete or overwrite historical evidence merely because newer evidence exists. Do not silently normalize historical claims into current claims. Do not modify code, runtime artifacts, or technical documents when the authorization is documentation-only.

## Recovery rule

Never begin an isolation operation without an independent, documented recovery path. TTY/recovery availability is an explicit gate. Define `RESTORE_PLANNED`, `RESTORE_EXECUTED`, and `RESTORE_VALIDATED` separately. If restore is partial, failed, or inconclusive, stop, preserve evidence, report `ABORT_RESTORE`/`RESTORE_UNRESOLVED`, and do not continue silently.

## Output

Use compact L1 output by default:

```text
STATE
CHANGED
OPEN
BLOCK
NEXT
EVIDENCE
```

Do not repeat unchanged data or add unnecessary decoration. Report one fact once unless needed to resolve a contradiction. Distinguish `OBSERVED` from interpretation and from authorization.

## OpenCode discovery reference

For OpenCode V2, this project-root `AGENTS.md` is the active persistent project instruction mechanism. OpenCode combines applicable global and project instruction files; do not assume `CLAUDE.md` or another configuration file is an active V2 equivalent. Reference: `https://opencode.ai/v2/docs/instructions`.

These instructions are constraints and methodology, not execution authorization. If a future instruction conflicts with a current user authorization, follow the narrower current authorization and record the conflict.
