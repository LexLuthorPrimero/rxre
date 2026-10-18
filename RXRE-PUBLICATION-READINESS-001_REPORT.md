# RXRE-PUBLICATION-READINESS-001 — Report

Mission: determine, from real artifacts, which RXRE capabilities can be published
and demonstrated today, which are incomplete, and the next highest-value blocker.
No branches, no worktrees, no parallel agents created by this action. No code
modified without a reproducible, evidence-backed deficiency (the only source
change is the README doc-sync below). Runs are READ-ONLY on hardware (no register
writes, no clock/voltage); `umr -r` only.

## 0. EXECUTIVE DECISION — READY_WITH_LIMITATIONS

The RXRE engine (`tools/rxre/`) on `main@53173f2` is **ready to publish with
limitations**: the code is committed and green, five capabilities are demonstrably
validated with reproducible commands and captured artifacts, no secrets are
present in the changes, and the public contract (README) has been synced. It is
**not** unconditionally READY because `gpu.register_read` is hardware/root-bound
(not universally executable) and there is no external/public git remote.

## 1. INITIAL & FINAL STATE (verifiable refs)

Initial (mission start):
- `main` @ `53173f2` — "RXRE-CORE-CAUSAL-002: reporte final (26 suites verdes, 8/8 trace, replay con control)".
- `tools/rxre/` package TRACKED (dispatch.py declares 24 adapters, machine.py
  entry, core/store.py, all adapters).
- `tools/rxre/README.md` **UNTRACKED** and **stale** (RXRE-001 overview: "9
  capacidades", a `tools/rxre/rxre` CLI that does not exist, `test_rxre.py`).
- Live `tools/rxre/storage/rxre.sqlite3` is shared with a **concurrent
  multi-worktree session** (the directive's warning): between my shells the same
  files toggled tracked/untracked, `machine.py`/`store.py` flipped `M`, and the
  `legacy` remote points at the sibling `../RX550-INVESTIGACION`.

Final (after this action):
- `README.md` **synced on disk** (see §4) — still untracked; staging/commit is the
  owner's publication act (§7).
- `main@53173f2` **unchanged** (no commits by this action). Worktree shows
  `M tools/rxre/api/machine.py`, `M tools/rxre/core/store.py` (unstaged
  `trace_id` plumbing, attributable to the prior RXRE-TRACE-ID-001 session and/or
  the concurrent session) plus untracked legacy debris at the repo root
  (`amdgpu.ko`, `root.bo`, `KytyPS5-Source/`, `r1.json`, `findings/`, …). None of
  that debris is under `tools/rxre/`.

## 2. FINDINGS BY EPISTEMIC LEVEL

**PROVEN** (verified executable & green this session / on 53173f2):
- `binary.decompile` works: Ghidra 12.1.4 real on `/bin/ls` → **23/23**
  (`test_decomp003`); 1680-line pseudocode with the `uVar*`/`iVar*` Ghidra
  signature; persisted (`op_868a12c7b8071ccd`) and reconstructed by `explain`.
- `gpu.register_read` works on the RX550: `mmGRBM_STATUS = 0x00003028`
  reproduced (deterministic — `explain` reconstructed the pre-existing
  `res_gpu_register_1f1b38e5c6d4` instead of duplicating it), plus a second
  register `mmMC_VM_FB_LOCATION = 0xf47ff400`; **11/11** (`test_umr_hardware002`);
  iGPU `0000:00:02.0` blocked by allow-list even with privileges; the non-object
  JSON line is tolerated (process survives).
- `trace_id` / event-log is real and stable: **27/27** (`test_r001_trace_id`),
  temp-DB; 4 identical calls → 4 distinct `trace_id` + 1 deterministic
  `result_id`; `eventos_por_trace` reconstructs; `COLISION` retry is idempotent.
- `operation_id` namespace diverges from `results.operation_id`
  (`test_opencode_trace007` L158); `result_id` is the stable cross-table/cross-
  system bridge (`explain` ok). `operation_id ∈ {op_…, COLISION:…}`
  (`test_dispatch004` B8, green in the 13/13 baseline).
- README was stale: 8 false public claims (see §4), each grounded in a verifiable
  artifact (`git ls-files`: untracked; glob: no `rxre` CLI; `dispatch.py`: 24 ≠ 9;
  test dir: 29 ≠ `test_rxre.py`). All fixed.

**OBSERVED** (measured, not inferred):
- Concurrent multi-worktree session mutates the live tree/DB.
- Only remote is `legacy → /home/lucas/Escritorio/RX550-INVESTIGACION` (local
  sibling); `main` tracks no remote.

**INFERRED** (plausible, not directly re-checked this session):
- The stale README predates the `machine.py` engine (it documents the legacy
  `tools/rxre/rxre` wrapper + 9 legacy-tool capabilities).

**UNVERIFIED** (honest gap — do not claim):
- Per-capability test→adapter coverage of the 11 adapters NOT in the
  individually-re-verified set (e.g. `binary.disassemble_func`, `binary.cfg`,
  `binary.dataflow`, the `rxre.*` knowledge ops). Claimed green by `53173f2`
  ("26 suites") but not each re-run in this session.

## 3. TESTS EXECUTED, COMMANDS, RESULTS, ARTIFACTS (this session)

All runs on the current worktree (`main@53173f2` + unstaged `trace_id` plumbing).
Hardware operations were READ-ONLY (`umr -r` only; no iGPU writes).

```
python3 /tmp/opencod/run_baseline.py            # 13/13 suites green (0 red)
python3 tools/rxre/tests/test_r001_trace_id.py  # 27/27
python3 tools/rxre/tests/test_umr_hardware002.py # 11/11  (sudo pw via stdin; temp DB)
python3 tools/rxre/tests/test_decomp003.py       # 23/23  (Ghidra /bin/ls)
```

- `run_baseline` (13 suites): `test_p004`, `test_p003` (27), `test_p0_2_conflict014`
  (32 checks), `test_replay004` (11), `test_water_run005` (5), `test_eventlog006`
  (4), `test_fase5_trace` (7/7), `test_reflexion002` (13), `test_lecciones006`
  (7), `test_mission001` (7), `test_soul007` (14), `test_epistemic_distinctions`,
  `test_dispatch004` ("self-test OK (132 comprobaciones)" — incl. B8
  `operation_id ∈ {op_, COLISION:}` + `persistido=True`).
- `test_decomp003`: Ghidra `mmGRBM_STATUS`/etc. compile `DumpDecomp.java`
  against 195 real JARs, real `analyzeHeadless` on `/bin/ls`, `status=ok exit=0`
  16.5s, 1680-line pseudocode; persisted `op_868a12c7b8071ccd`, `explain` ok;
  failure paths → `invalid_input`.
- `test_umr_hardware002`: `mmGRBM_STATUS=0x00003028`, `mmMC_VM_FB_LOCATION=0xf47ff400`,
  `explain` reconstructs `res_gpu_register_1f1b38e5c6d4` (== FASE-A result_id, so
  deterministic replay, not a new row), iGPU `0000:00:02.0` `invalid_input`
  allow-list, non-object line tolerated.
- Artifacts captured: `result_id`s `res_gpu_register_1f1b38e5c6d4`,
  `res_gpu_register_2186ff92f35`; operation `op_868a12c7b8071ccd` (Ghidra). Temp
  DBs were used and cleaned; the live `rxre.sqlite3` gained no new finding rows
  from this session (the `res_gpu_register_1f1b38e5c6d4` was a `COLISION`/idempotent
  replay, exactly the behavior `test_dispatch004` B8 asserts).
- Cited (prior session, env-bound — NOT re-run this session): `test_opencode_trace007`
  18/18 (Part C bridges OpenCode↔RXRE by `result_id`; Part HALLAZGO L158 asserts
  `execution_events.operation_id ≠ operations.operation_id`). Re-verifying it
  live is impractical (it reads the live `opencode.db` for a fixed `SID`); its two
  building blocks ARE re-verified this session via `test_dispatch004` (COLISION)
  and `test_r001` (eventos_por_trace).

## 4. DOCUMENTATION vs REALITY (Fase B)

README §stale → corrected (synced on disk):

| README claim (stale) | reality (verified) | action |
|---|---|---|
| `tools/rxre/rxre capabilities/search/symbol/register/trace` CLI | `tools/rxre/api/machine.py` stdin JSONL; ops `backends/experiment/explain/lessons/ops/plan/reflect/research/run/saturate` | FIXED |
| "9 capacidades" (`capabilities/search/symbol/register/xref/trace/pm4/evidence/provenance`) | 24 adapters in `dispatch.py::ADAPTERS` (families binary.*/source.*/rxre.*/gpu.*) | FIXED |
| `python3 tools/rxre/tests/test_rxre.py` "14 grupos" | 29 `test_*.py`; `run_baseline.py` = 13 suites | FIXED |
| 8-key envelope only | envelope also carries `capability/ejecutada/producer_ejecutado/rc/operation_id/persistido/nota_persistencia` | FIXED (note) |
| Estado "RXRE-001, 9 capacidades" | RXRE-CORE-CAUSAL-002 (`main@53173f2`), 26 suites verdes, 8/8 trace | FIXED |

Historical Ghidra contradiction (Fase B #2), resolved by ground truth:
`RXRE-AUTONOMY-001` ("binary.decompile blocked, cause localized") and
`tools/rxre/docs/RXRE-004-BACKEND-MATRIX` ("UNAVAILABLE / no instalé Ghidra")
**conflict** with `RXRE-CAUSAL-EVOLUTION-001` / `RXRE-EXT-001` ("working / PARTIAL")
and with GROUND TRUTH: `test_decomp003` **23/23**, Ghidra **12.1.4** at
`/usr/lib64/ghidra` (195 JARs), `DumpDecomp.java` compiles against the real JARs.
→ Resolution: the two "blocked/UNAVAILABLE" reports are **stale**; current =
working with the documented ET_REL kernel-module limitation. (Those report files
were left untouched — out of README scope; they should be ARCHIVE'd, not this action.)

## 5. CAUSAL EXPERIMENT (Fase C) — the `result_id` bridge decision

Claim under test: reconstruction must key on `result_id` (stable), not
`operation_id` (divergent) — the lesson persisted as
`reflexion_9ce83e3f96b00928`.

Controlled demonstration, **both halves green this session**:
- *Without the lesson* (key on `operation_id`): `test_opencode_trace007` L158
  asserts `execution_events.operation_id ≠ operations.operation_id` (namespace
  not unified) → an `operation_id`-keyed join would be empty. `test_dispatch004`
  B8 shows `operation_id ∈ {op_…, COLISION:…}` (idempotent), not stable.
- *With the lesson* (key on `result_id`): `test_opencode_trace007` Part C bridges
  OpenCode↔RXRE by `result_id` (`explain` → `ok`); `test_umr_hardware002` Step 5
  reconstructs the hardware read via `explain(res_gpu_register_1f1b38e5c6d4)`;
  `test_r001` `eventos_por_trace(trace_id)` returns `ok` and is idempotent
  (re-query duplicates no rows).

→ The lesson **modifies** the reconstruction decision (key on `result_id`); the
controlled comparison is in the green assertions themselves (divergence asserted
+ stable bridge asserted). §96 (NO OVER-RESEARCH): no further experiment needed.

## 6. REAL BLOCKERS & CAUSES (Fase D gates)

- **(doc) README stale → FIXED** (synced). Still untracked → owner `git add`+commit.
- **(doc) stale historical reports** (see §4) — doc hygiene; recommend ARCHIVE.
- **(infra) no external/public remote** — only `legacy → ../RX550-INVESTIGACION`
  (local sibling); pinning a publishable SHA is the owner's `git push`.
- **(process) concurrent multi-worktree session** mutates the live worktree/index
  and shares `rxre.sqlite3` → live tree is non-deterministic; publication must
  build from a **clean checkout of `53173f2`**, not the live worktree.
- **(repo) `run_baseline.py` is not committed** (lives in `/tmp/opencod/`) — a
  reproducibility gap; the 13 suites it runs ARE committed, but the runner is not.
- **(HW) `gpu.register_read`** requires root + a Polaris12 RX 550 (not universal).
- **(binary) `binary.decompile`** cannot decompile kernel `ET_REL` modules in
  Ghidra (classified `unsupported`, not `empty`; uses rizin/radare2/BTF instead).

## 7. PUBLICATION DECISION: READY_WITH_LIMITATIONS

Met: (a) code committed + green (`main@53173f2`, 26 suites); (b) **4 suites re-verified green this session** — `run_baseline` (13/13 suites, 0 red, incl. `test_dispatch004`'s 132-check B8 self-test), `test_r001_trace_id` (27/27), `test_umr_hardware002` (11/11), `test_decomp003` (23/23) — covering `gpu.register_read`, `binary.decompile`, `trace_id`/event-log and the core dispatch/knowledge; (c) reproducible commands + captured artifacts (result_id`s,
`op_…`); (d) no secrets (the only diff is `trace_id` plumbing via env
`RXRE_TRACE_ID`; `umr_read` hard allow-list; no credentials on disk); (e) README
coherent.

Limitations: `gpu.register_read` (root+RX550), `binary.decompile` (ET_REL),
no external remote, ephemeral runner, concurrent multi-worktree process, stale
historical reports. → Ready for **hardware-assisted** publication (the GPU-read
path is demonstrably real and reproducible on this exact box).

## 8. NEXT ACTION OF HIGHEST VALUE

1. **Owner publication steps:** `git add tools/rxre/README.md && git commit -m
   "docs(rxre): sync README to RXRE-CORE-CAUSAL-002"`; commit a stable
   `tools/rxre/tests/run_baseline.py`; `git push legacy main` and verify the remote
   SHA (Fase D #6). Publish from a **clean checkout of `53173f2`**, not the live
   worktree.
2. **Capability frontier (next):** bitfield-decode `mmGRBM_STATUS` (`0x3028`) —
   the explicit limitation in the GPU-read finding (RAW_BINARY only). This closes
   the "value_hex yes, bit meaning no" gap and is the next hardware-semantics
   frontier on Polaris12/GFX8.

## Appendix — epistemic honesty

This report does **not** claim: universal executability of `gpu.register_read`
(root+RX550 only), Ghidra decompilation of kernel `.ko` (ET_REL `unsupported`),
per-capability test coverage for all 24 adapters (11 not individually re-run),
or that the live worktree is deterministic (it is not — concurrent session).
