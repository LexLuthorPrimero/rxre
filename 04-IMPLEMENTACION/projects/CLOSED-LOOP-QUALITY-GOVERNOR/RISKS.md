# IDEA I-08 — CLOSED-LOOP QUALITY GOVERNOR: RISKS

Documentary risk register. Every risk = what can go wrong + how the experiment detects/mitigates it, all within the read-only/no-write/no-counters constraint.

## R1 — OSCILLATION / LIMIT CYCLE (highest-priority control risk)
- **Mechanism:** proportional loop with no dead-band cycles the scale between min/max when load varies (scene bursts).
- **Mitigation:** shipped-pattern hysteresis (Unity HDRP: K consecutive windows + 1/N steps), min-hold-time, and conservation (aggressive down, conservative up / Unity sample). Any observed oscillation is the *failure* outcome in H3 and must be reported, not papered over.

## R2 — NON-MONOTONIC ACTUATION (GCN4-specific)
- **Mechanism:** lowering scale reduces GPU load → DPM/SMU may drop SCLK → frametime gained << pixel-linearity; in some windows the SMU may even recover and re-ramp (hunting), so the same scale does not always yield the same frametime.
- **Mitigation:** tag every run by pp_dpm_sclk regime; report the sclk(scale) curve (H2); design the controller to treat gain as variable (slower, windowed adaptation). **Do NOT assume linear scaling.**

## R3 — POWER-SIGNAL PATHOLOGY
- **Mechanism:** power1_input is 10-Hz board-power including controller/display overhead; SMU power-management lag makes it a lagged, noisy feedback.
- **Mitigation:** never use it as primary closed-loop signal; keep it as an auxiliary/confounder only (H4 tests and documents why).

## R4 — NOT-GPU-BOUND WORKLOAD INVALIDATES EVERYTHING
- **Mechanism:** if the synthetic load is CPU/GPU-idle or power-limited, the governor has no authority and curves are flat.
- **Mitigation:** validate gpu_busy ≈ high AND regime tags on every run (PLAYBOOK: METRICS-DEFINITIONS' busy≠BW; use regime guard per TEST D).

## R5 — PLATFORM / CONFIG DRIFT
- **Mechanism:** kernel/Mesa/DPM override, kalm mediation, VRAM pressure on 2 GB SKU, display-on-Intel condition not re-checked.
- **Mitigation:** verify 1002:699f + no R550 display + temp <90 °C (DN-07) + mem_info_vram/GTT log per run. Never assume prior state (DN-13).

## R6 — SCOPE CREEP INTO PROHIBITED TERRITORY
- **Mechanism:** "the loop would work better with DPM writes / counters" temptations.
- **Mitigation:** hard boundary — no sysfs writes, no PERF_SEL programming, no Mesa/driver/kernel change. Anything needing those is re-classified as out of scope (and that is *itself* a documented finding: hardware-counter/DVFS actuator unavailable here).

## R7 — CLAIMING NOVELTY FROM A WELL-KNOWN PATTERN
- **Mechanism:** reporting the shipped proportional+hysteresis loop as "novel."
- **Mitigation:** prior-art section pins the pattern to consoles, Intel, Unity/UE (§PRIOR-ART). Any novelty claim is metered to a concrete, reusable GCN4 result (H2 coupling compensation) — otherwise classify as KNOWN VARIANT / status C.

## R8 — LOOP OBSERVABILITY DOUBLES AS PERTURBATION
- **Mechanism:** per-frame timber + sysfs polling alternates with the GPU's own power management, perturbing the very frametime being measured (Observability Perturbation, MASTER-PLAN transversal layer).
- **Mitigation:** measure overhead (idle frametime with vs without harness), keep sysfs poll rate modest (~1–10 Hz), report the harness's own cost; TELEMETRY_MODE discipline (MINIMAL for closed loop).