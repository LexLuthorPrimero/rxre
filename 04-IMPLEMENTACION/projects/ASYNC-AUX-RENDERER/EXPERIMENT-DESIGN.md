# IDEA I-10 — ASYNC AUXILIARY RENDERER: EXPERIMENT DESIGN

Documentary/measurement-only plan. No production feature. Goal: quantify whether an **auxiliary
render-style workload co-scheduled on the async compute (ACE) queue** reduces (or at least does not
hurt) frametime on Polaris12's fetch-bound synthetic. **This design is a WORKLOAD VARIANT of
BERRETA/ASY-01** — it must reuse that runner/harness, not introduce a new one.

## 0. HYPOTHESES TO TEST
- H1: Co-scheduling a *BW-independent async pass* (e.g., pre-post pass on stale buffers, or
  static-light shadowmap of frame N-1) leaves p50/p99 flat vs serial. (Expect: TRUE — the only
  marginal win available under power cap.)
- H2: Co-scheduling a *BW-heavy async pass* (SSR/AO reading same G-buffer depth) **hurts p99** —
  it competes for the very fetch path that bottlenecks ES-01. (Expect: TRUE, Division-2-style
  "async stalling the gfx pipe".)
- H3: True overlap benefit ("lower total time") exists only for passes with **zero dependency on
  the current frame** (fork before join). (Expect: mirrors Cyberpunk/Frostbite pattern; small on
  8 CUs.)

## 1. TEST A — API/CAP RE-CHECK (read-only, from BERRETA)
Reuse BERRETA queue-family verification: enumerate compute queue family on RADV/GFX8, confirm
timeline semaphore support, confirm 2 dispatch engines (SPM/ACTIVE counters read-only per FASE D
stage-3 audit). No writes.

## 2. TEST B — OVERLAP VARIANT A: BW-INDEPENDENT ASYNC (best case)
1. Fork async pass BEFORE frame: compute "bloom/bokeh downsample" or "static shadow update" that
   uses *(frame N-1)* data → join at frame end.
2. Compare vs serialized same work (p50/p99, mem_busy, power) N≥5 paired.
3. Sweep: async share 0→100% (across the BERRETA occupancy grid), power profile unchanged (cap on).

## 3. TEST C — OVERLAP VARIANT B: BW-HEAVY ASYNC (worst case)
1. Async SSR/AO variant reading depth+color from *current* G-buffer after semaphore → measures
   contention with GFX fetch path. Compare p99 vs serial. This is the falsification test for the
   naive "async rellena huecos" claim on this chip.

## 4. METRICS / PASS-FAIL GATES
- Δp50, Δp99 (async vs serial), N≥5, same cap regime, same telemetry as BERRETA.
- Power at cap must be **flat** (else result confounded).
- `mem_busy` recorded, NOT used as bandwidth truth (METRICS-DEFINITIONS).
- PASS (H1): p50/p99 within noise (no harm) AND work scheduled "for free".
- PASS (H2-expected): p99 worsens for BW-heavy async → claim "async ayuda en Polaris12" FALSE,
  documented.
- JOIN correctness: aux output must match serial output within epsilon (no async correctness bugs).

## 5. TOOLING
- Same as BERRETA: runner K, synthetic harness F, Vulkan, RADV, `rx550-torneo` read-only.
- No installs, no kernel/counter writes (FASE D stage-3 is audit-only).

## 6. CLARITY BOUNDARIES (avoid collisions)
- This is **not** ROP-offload (I-04, contradicted) and **not** a compute-replacement renderer.
- Must **not** duplicate BERRETA: if runner already exists there, PR adds only the *auxiliary
  workload variants* + results tables.