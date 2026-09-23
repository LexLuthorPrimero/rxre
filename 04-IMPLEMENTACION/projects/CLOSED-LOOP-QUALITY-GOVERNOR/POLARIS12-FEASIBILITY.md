# IDEA I-08 — CLOSED-LOOP QUALITY GOVERNOR: POLARIS12 FEASIBILITY

RX550 facts: 8 CUs / 512 SP / ~1.2 TFLOPs / 512 KB L2 / 112 GB/s / 16 ROPs / GCN4, ~50 W TBP. Counter programming not authorized (FASE D/M), any sysfs write not authorized (DN-12) — actuator must be app render-scale only.

## 1. WHAT THE LOOP CAN ACTUALLY CONTROL (the binding constraint)

| Actuator | Allowed? | Feedback relevance on RX550 | Notes |
|---|---|---|---|
| App render resolution scale (dynamic-resolution knob) | YES (if workload/app exposes it) | High — per-pixel cost dominates (Intel DRR §2) | The only real actuator for "quality" |
| Viewport-scale / render-target allocation | YES (same as above, engine-side) | High | Unity/engine pattern |
| Quality level (LOD, effects) set | YES (app-side) | Medium | Discrete steps, coarse |
| DPM/SCLK/MCLK/cap writes | **NO** (DN-12; permanent rule) | n/a | Removes the DVFS-governor actuator class entirely |
| Hardware counters (PERF_SEL) as feedback | **NO** (FASE D/M) | n/a | Removes SSMDVFS/GUI-class feedback |

**Conclusion:** the loop control authority lives entirely in the **app's rendering scale**. The governor is a *policy* (scale selection) + a *conduit for read-only telemetry*, not a hardware controller. On a fixed game without an exposed DRS knob, the governor cannot act — it becomes observability-only. The feasibility test therefore requires a synthetic/app workload that exposes a scale knob.

## 2. READ-ONLY FEEDBACK SIGNALS ON THIS BOX (which are actually usable)

| Signal | Source | Sample availability | Latency/noise | Use in loop |
|---|---|---|---|---|
| **frametime** | app-side timer / Vulkan timestamps (that we instrument) | per-frame; cleanest | low, ±jitter | PRIMARY measured output (Intel/Unity/console pattern) |
| `power1_input` (W) | sysfs hwmon4 | 10 Hz (poll) | sampled, noisy, lag | secondary/auxiliary (NOT primary; DPM/thermal dynamics blur it) |
| GPU busy (gpu_busy) | sysfs + radeontop/amdgpu_top | ~1 Hz typical tools; faster via direct read | averaged | tertiary (confirms "GPU-bound not CPU-bound") |
| `pp_dpm_sclk`/`mclk` (read) | sysfs | on refresh | reflects DPM state, lags load | **confounder guard** (detect power-limited/clock-limited regimes — E3/E5 lesson) |
| mem_info_vram/gtt (read) | sysfs | on refresh | coarse | VRAM-pressure guard (2 GB SKU) |
| temp | sysfs | 1 Hz | slow | safety/thermal coupling note |

**Practical consequence:** the loop's only *fast, reliable, per-frame* signal is frametime. Everything else is auxiliary. A governor trying to react to `power1_input` at 10 Hz would add loop latency of ~100 ms+ and fight the SMU's own power management — a known anti-pattern vs. frametime-only control.

## 3. CONTROL-LOOP TIMING (numeric, on RX550 equivalent workloads)

Adopt the shipped pattern (Unity HDRP §review ← primary docs):
- **Per-frame sampling** of frametime; **evaluate every E frames** (E ≈ 8–15) using **average** GPU frame time over the window (this is exactly HDDynamicResolution: EvaluationFrameCount=15).
- **Step policy with hysteresis:** require **K consecutive windows** in the same direction before changing scale by **1/N** of the available range (HDRP: ScaleUpDuration=8 / ScaleDownDuration=4, steps 5/2). This alone is the oscillation suppressor.
- **Scale bounds:** RX550 realistic DSLR (dynamic resolution local range) at 1080p target: 0.75–1.00 for the synthetic (frame already GPU-bound). Below ~0.75 quality loss is obvious in the synthetic; measure, don't assume.
- **Loop latency estimate:** window (15 f @60 fps ≈ 250 ms) + K windows (4–8 → 1–2 s) before first actuation ≈ **1–2 s settle time** to a new scale, then frametime reacts next frame. Same ballpark as shipped DRS; acceptable and honest to document.

## 4. STABILITY / OSCILLATION ANALYSIS (what to verify, not assume)
- **Limit cycle risk:** load varies (scene 1 heavy, scene 2 light) → naive loop oscillates between min/max. Mitigations already proven in shipped systems: hysteresis counters (#4, #15), exponential backoff (#19), conservative-raise/aggressive-lower (Unity sample #5). I-08 must implement ≥ hysteresis + min-hold-time.
- **Power-vs-quality coupling on GCN4:** DPM scales SCLK with load; lowering resolution lowers load → SMU may also drop the clock → frametime may not improve proportionally (clocks chase utilization). The loop controller must be robust to *non-monotonic* actuation gains — **test on RX550, do not assume linear scaling.** This is the genuinely interesting measurement.

## 5. RESOLUTION / QUALITY LEVERAGE ON THIS CHIP (drives whether DRS is worth it)
- Per-pixel costs dominate modern renders; 1080p→720p (0.66×) ≈ halves pixel count; but Polaris12 is also **partially ROP/L2-bandwidth limited** (16 ROPs, 512 KB L2, 112 GB/s). Pixel-count scaling is therefore *less* than 1:1 on frametime here (unlike a fill-bound part). Expect: at 60 fps target, 0.75× scale buys a few ms of headroom, not the full Intel/console 2× — **hypothesis to measure** ([] `[HIPÓTESIS]`).

## 6. VERDICT
- **Technically plausible?** Yes — but only as **the app-side dynamic-resolution governor** (actuator = render scale), with frametime as the primary loop signal, hysteresis from shipped designs, and all observables read-only. The hardware-counter DVFS/governor class (what most of the future-work literature optimizes) is *excluded by project rules*, which makes this a **reduced-authority governor** — worth building to *measure* the GCN4-specific behavior (non-monotonic clock coupling in §4), not to demonstrate novel control theory.
- **Novelty:** KNOWN VARIANT (shipped consoles/engines + DVFS governor literature). Counter-free-frametime feedback is the norm, not the gap. Marginal value: constrained observability-only GCN4 measurement.
- **Recommended path if pursued:** measurement-first with the synthetic workload exposing a scale knob: (1) measure frametime  vs scale curve on RX550 (linearity!); (2) measure power-vs-frametime coupling; (3) then close the loop with hysteresis and verify no oscillation. No sysfs writes.