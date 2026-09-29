# CLOSED-LOOP QUALITY GOVERNOR (I-08) — PROJECT README

**Status:** Phase R-3 documentary novelty audit (DOCUMENTAL ONLY, no implementation).

**Idea:** Build a *closed-loop quality governor* for the RX 550: a controller that, based on **read-only** signals (`W_SMU`/`power1_input`, DPM clocks, GPU busy/radeontop, memory, frametime, kalm telemetry), adjusts a *quality actuator* (render resolution scale / quality level) to hold a target frametime — the same loop consoles and game engines ship, but driven **without hardware counters and without any sysfs write**.

## DEFINITIONS (used everywhere in this project)
- **CONTROL VARIABLE (CV):** the quality knob the loop moves (render resolution scale factor, e.g. 0.5×–1.0×; or quality level).
- **FEEDBACK SIGNAL (measured output):** what the loop observes — frametime (ms), GPU busy %, `W_SMU`, clock states (read-only).
- **SETPOINT:** the target frametime (e.g. 16.7 ms @60 fps) the loop tries to hold.
- **ACTUATOR:** the mechanism that changes the CV (viewport/dynamic-resolution scale inside a renderer; NOT DPM/clock writes — those are prohibited).
- **SAMPLE RATE / CONTROL PERIOD:** how often the controller reads the feedback and recomputes the CV (per-frame vs. per-control-window).
- **HYSTERESIS:** a dead-band so small frametime jitter does not cause resolution oscillation (scale changes are discrete steps, held N windows — Unity HDRP pattern).
- **LOOP LATENCY:** delay from "GPU slowed down" to "resolution actually lowered" (feedback read + controller decision + actuation next frame).
- **STABILITY:** no oscillation between min/max quality under constant load; convergences, no limit cycles.
- **HARDWARE COUNTERS:** GFX8 PERF_SEL event counters — NOT AUTHORIZED for this project (FASE D/M). The governor must not depend on them.
- **GOVERNMENT-FREE:** no sysfs write (no cap/DPM/SCLK/MCLK writes). Permanent rule, decisions.md DN-12.

## KEY FACTS ABOUT THE HARDWARE TARGET
RX 550 = Polaris12: 8 CUs (512 SP), ~1.2 TFLOPs FP32, 16 ROPs, 512 KB L2, 96–112 GB/s nominal/estimado (real `UNKNOWN`; 128-bit GDDR5), GCN4, ~50 W TBP. Telemetry that exists read-only: `power1_input`/`W_SMU`, `pp_dpm_sclk`/`pp_dpm_mclk` (read), `mem_info_*`, GPU busy (radeontop/amdgpu_top), frametime from an app or from `fdinfo`/`perf`. No GFX8 hardware counters available without programming (prohibited).

## CRITICAL PREMISE CHECK (the one thing to NOT assume)
A governor needs an **actuator** — something that changes quality. On a locked driver:
- The GPU's clock/power **cannot be an actuator** here (writes prohibited), so the loop must act through the **application's own render scale** (dynamic-resolution knob exposed by the engine/app), or through a workload we control (the synthetic one).
- The feedback must be **stable to read**: `power1_input` is a 10-Hz sysfs sample with latency/noise; frametime is the cleanest real-time signal; `gpu_busy` is averaged.

Thus the honest formulation of this idea is: **"a dynamic-resolution (quality) governor whose feedback is read-only sysfs telemetry + frametime, targeting the RX 550, demonstrated on a controllable workload — no counter programming, no sysfs writes."** The control law itself (proportional frametime-error → stepped scale) is well-known; the novel-*ish* claim is strictly the *no-counters, no-writes, low-end-GCN4* packaging.

## DOCS IN THIS DIRECTORY
1. `PRIOR-ART.md` — the survey: consoles (Diablo III X1X/PS4P), Intel DRR, Unity/Unreal DRS, mobile DRS, DVFS/frame-rate governor control theory, cloud-gaming adaptive rendering, academia.
2. `POLARIS12-FEASIBILITY.md` — numeric feasibility on RX 550: which signals are usable, what the actuator can be without writes, control-loop timing (sampling, hysteresis, stability).
3. `EXPERIMENT-DESIGN.md` — measurement-first test plan: proof the loop converges, holds setpoint, and doesn't oscillate — all read-only.
4. `RISKS.md` — how the loop misbehaves (oscillation, overshoot, latency, power coupling).
