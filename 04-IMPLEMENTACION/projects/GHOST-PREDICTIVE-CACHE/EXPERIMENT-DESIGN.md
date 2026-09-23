# IDEA I-06 — PREDICTIVE GHOST CACHE: EXPERIMENT DESIGN

Documentary/measurement-only plan. No production feature. Goal: quantify whether an
**explicit camera-forward prediction + L1/L2 read-path warm-up** moves the **p99** of the
fetch-bound synthetic workload (ES-01). The hardware-cache ("pin L2") variant is declared
NOT FEASIBLE in `POLARIS12-FEASIBILITY.md` and is excluded from design.

## 0. HYPOTHESES TO TEST
- H1: A `warm-up` pass that touches *predicted* texture regions 1–2 frames ahead reduces p99
  vs an identical reactive workload (same camera path). (Expect: small win in p99; no win in p50 —
  ES-01 p50 is capped/flat.)
- H2: Prediction accuracy ≥ threshold needed to beat pollution — a warm-up pass that confronts
  the accuracy–eviction tradeoff. (Expect: accuracy ~70–90% from camera+history on the synthetic;
  below a threshold it degrades p99.)
- H3: The warm-up *read pass* itself is cheap on Polaris12 (a few texture loads w/o full
  shader) relative to the fetch p99 it saves. (Expect: pass cost << one fetch-bound frame.)

## 1. TEST A — BASELINE (control, no-new-code)
1. Run existing F2/FETCH workloads on runner K, fixed synthetic camera path; capture
   `frametime p50/p99`, `mem_busy`, `mem_info_vram/gtt`, faults. (Data likely already exists in
   ES-01; re-run N≥5 to get paired statistics.)
2. Record per-frame **L2 miss behavior** indirectly: since no counter writes are authorized
   (FASE D stage3 design/audit only), use `mem_busy`+faults+timing across (VRAM-resident) vs
   (GTT-resident) data (ties to GHOST G-M1/G-M2).

## 2. TEST B — WARM-UP PASS (the only realizable "ghost")
Implementation sketch (userland Vulkan, harness synthetic workload, no kernel changes):
- B1. **Predictor:** per-frame compute a small "tile hitlist" = text/mip regions predicted to be
  fetched next frames. Prediction = camera frustum extrapolated one/two frames ahead + last-frame
  map (choose *simplest* predictors first: frustum-extrapolation; velocity-based; history).
- B2. **Warm-up:** before the frame's real draw, run a *thin* compute/pixel pass that samples the
  predicted regions (just enough text fetches to warm L1→L2→VRAM read path), on the ACE queue or
  idle time slots. No writes to the frame; read-only touches.
- B3. **Accuracy capture:** "would-have-been-used" ground truth recorded from the *actual* fetch
  set of the frame (who reads textures). Score predictor (precision/recall) per frame.
- Sweep: slack in frames (0,1,2,3), prediction mode (extrapolated camera / velocity / history),
  scene density, GTT-vs-VRAM resident data.

## 3. TEST C — POLLUTION MATRIX
- Input the SAME total fetch count, but vary *accuracy* by deliberately corrupting a fraction of
  the hitlist (0%, 25%, 50%, 75%) → measure p99 delta. Produces the accuracy-vs-p99 curve that
  decides whether the predictor is worth anything (prefetch literature: needs ~≥2× accuracy).

## 4. METRICS / PASS-FAIL GATES
- Δp99 (warm vs control) across N≥5 paired runs; p50 must stay flat (no pollution-induced
  regression in p50).
- Precision/recall of predictor per frame (from ground-truth fetch set).
- `mem_busy`/faults recorded but NOT used as bandwidth truth (METRICS-DEFINITIONS).
- PASS: Δp99 ≥ 8% AND p50 flat (within noise); predictor accuracy ≥ 2×-to-beat threshold.
  FAIL-if-pollution: p50 regresses or p99 worsens with warm-up at high accuracy.

## 5. TOOLING
- Existing runner K, synthetic harness (F1/F2), Vulkan; `rx550-torneo` read-only metrics.
- No installs, no kernel/counter writes (FASE D stage-3 audit only).

## 6. RELEVANCE STRINGENT CHECK
Because UE/Unity/id5 already do camera-based prefetch, the experiment must document WHAT IS NEW:
- New-to-us: (a) a read-path **warm-up pass** (not residency hint) on a fetch-bound *desktop IMR*;
  (b) explicit per-frame **prediction score** vs the real fetch set; (c) quantification on
  Polaris12/RX550 — a class never measured this way in primary sources found.
- What is NOT claimed: no L2 pinning (hardware unsupported), no "free perf" outside fetch-bound
  regimes, no accuracy—pollution law beyond what the sweep measures.