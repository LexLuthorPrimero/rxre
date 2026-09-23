# IDEA I-08 — CLOSED-LOOP QUALITY GOVERNOR: EXPERIMENT DESIGN

Documentary/measurement-only plan. No production feature, no sysfs writes, no counter programming. Goal: **measure whether a frametime-feedback quality governor behaves on Polaris12 as the shipped designs predict** — the curve shape, the clock coupling, and whether the loop stays stable.

## 0. HYPOTHESES TO TEST
- H1: On RX550, frametime scales **sub-linearly** with render scale (fill/ROP/L2-bound rather than pure pixel-bound). (Expect: sub-linear — the DRS leverage is smaller than on fill-bound consoles.) `[HIPÓTESIS]`
- H2: Lowering the scale does NOT yield proportional frametime gain because DPM lowers SCLK as load drops, coupling clock to quality. (Expect: strong coupling visible in pp_dpm_sclk read-back — the interesting GCN4 result.) `[HIPÓTESIS]`
- H3: A hysteresis + settle-window loop (Unity HDRP pattern) converges and holds setpoint on this chip with no limit-cycle oscillation on a stationary scene. (Expect: passes — that's the shipped design' property.) `[HIPÓTESIS]`
- H4: Power signals (power1_input 10 Hz) are too lagged/noisy to be the primary feedback; frametime-only beats power-feedback in setpoint hold. (Expect: TRUE → confirm frametime-primary design.) `[HIPÓTESIS]`

## 1. PRE-REQUISITES (what must exist first)
- A **controllable workload** exposing a render-scale knob (or quality-level knob) — the synthetic workload (§J of MASTER-PLAN) or a tiny VK/GL demo with dynamic resolution enabled and a per-frame scale parameter exposed (e.g. read from env/fifo). It must run GPU-bound at the target (else the governor has nothing to act on) — validated with gpu_busy.
- A **feedback harness** producing frametime per frame (Vulkan timestamps or present-time intervals) and reading sysfs (power1_input, pp_dpm_sclk/mclk, gpu_busy, mem_info, temp) read-only, logged to CSV (DN-13 schema).
- Governance **policy module** implementing the control law with params: E (evaluation window), K (settle windows), N (steps), min/max scale, setpoint frametime.

## 2. TEST A — OPEN-LOOP SCALE CURVE (H1, H2) [read-only]
Sweep scale from 1.00 down to 0.60 in steps (e.g. 0.10) on a GPU-bound synthetic load at 1080p; at each step hold steady N≥5 windows and record: frametime p50/p99, power mean, pp_dpm_sclk state, gpu_busy.
- OUTPUTS: `frametime(scale)` curve (linearity test for H1); `sclk(scale)` + `power(scale)` (H2 evidence).
- Optional variant: repeat at fixed clock impossible (no writes) → state the DPM-confounded condition explicitly (DN-13: what cannot be concluded).
- Tools: vulkan timestamps/timer in harness; sysfs reads; radeontop for gpu_busy cross-check.

## 3. TEST B — CLOSED LOOP, HOLD AND PERTURBATION [read-only]
Close the loop with the policy module (hysteresis parameters), setpoint = 60 fps @1080p, stationary scene → verify convergence ≤2 s, no oscillation (scale series monotone → settles; frametime p50 near setpoint). Then inject a step load change (scene swap or workload intensity change mid-run in the synthetic) and record transient: overshoot, recovery time, no limit cycle across ≥60 s (H3).
- PASS if: p50 frametime within ±10 % of setpoint after settle; scale changes ≤4 in 60 s steady-state; no oscillation at min/max bounce.
- Metrics: scale(t), frametime p50/p99, power(t), sclk(t) — same CSV schema.

## 4. TEST C — POWER-FEEDBACK CONTRAST (H4) [read-only, comparative]
Same loop but drive it from power1_input (sampled 10 Hz, averaged over windows) instead of frametime. Compare setpoint hold (σ frametime, count of dropped frames) vs TEST B.
- Judgment: if power-driven hold is worse, H4 supported → frametime-primary is correct design choice (and matches shipped engines' choice).
- Caveat documented: power1_input is board-power, also includes DCLK/display-lite/controller overhead noise → structural disadvantage on this card. Record it to justify the choice.

## 5. TEST D — CONFOUNDER / REGIME GUARDS (validation of measurements)
- Record pp_dpm_sclk/mclk along all runs → identify power-limited vs clock-limited vs compute-bound regimes (E1/E3/E5 lesson: never assume the regime). Tag each run by regime.
- Record temp; abort/cool if >90 °C (DN-07 thermal policy).
- Check mem_info_vram/GTT: 2 GB SKU; if VRAM pressure appears, tag run (may invalidate frametime comparisons).
- Verify GPU identity (PCI 1002:699f) and display-on-Intel condition per MASTER-PLAN failsafe before any run.

## 6. METRICS / GATES SUMMARY
| Metric | Gate | Feeds |
|---|---|---|
| frametime(scale) linearity | report slope/intercept; any slope <0.5 pixel-proportional ⇒ H1 | H1 verdict |
| sclk vs scale | report; coupling magnitude | H2 verdict |
| convergence time | ≤2 s on stationary scene | H3 partial |
| steady-state scale changes | ≤4 per 60 s (stationary) | H3 (stability) |
| setpoint hold σ | ≤10 % for TEST B, better than TEST C | H4 |
| dropped/duplicated frames | report | ROS-free run sanity |

## 7. TOOLING / ENVIRONMENT
- Vulkan/GL app harness instrumented (frametime), scale knob read from env or fifo.
- sysfs reads via the rx550-torneo-style telemetry pattern (read-only); NO writes, NO `profile_peak`, NO cap/DPM writes.
- Logs per run `runs/<run-id>/` with RESULTADOS-*.md (DN-13) — mirroring existing experiments layout (telemetry.csv + stdout + audit).
- Statistical method: paired/stepped windows with p50/p99 and a priori gates; N≥5 per config; report IC (consistency with M1/M2 methodology).

## 8. BOUNDARIES / NOT DOING
- NO sysfs writes of any kind; NO counter programming; NO driver/kernel/Mesa modification (Mesa CUSTOM only as instrument if needed, not as tuner).
- NO production feature promised; the outputs are measurements and a documented control-law implementation on GCN4 with a controllable workload.
- If the workload can't reach a GPU-bound regime, the experiment does not close H1–H3 (document as unverifiable on this box, not as success/failure).

## 9. DECISION OUTCOME SPACE
| Outcome | Meaning |
|---|---|
| H1 TRUE, H4 TRUE | Governor is *app-side DRS policy wrapped around frametime*; low statistical novelty but interoperable, measurement-hardened on GCN4 |
| H1 FALSE (linear) | Stronger DRS leverage than expected → better case for the governor to be useful at 720p? measure; document IC |
| H2 STRONG coupling | Actuation entangled with DPM: document; governor must be slower/DC — feeds loop param choice; partial novelty claim on GCN4 coupling |
| Loop oscillates (H3 FALSE) | Repeat with shipped-parameter tuning (UHD-style) to confirm; if still, note GCN4-specific instability → worth documenting as a negative |

Classification: `KNOWN VARIANT` — engineering/measurement of a well-known pattern on a specific low-end GCN4 target; recommended status **C** (document/measure), with an optional PARTIALLY NOVEL claim only if a concrete, reusable GCN4-specific result (e.g. DPM-coupling compensation) emerges from H2.