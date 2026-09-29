# IDEA I-07 — ASYNC OPTICAL FLOW FRAME GENERATION: EXPERIMENT DESIGN

Measurement-only plan. Goal: quantify the four costs (REAL FPS / GENERATED FPS / FRAME TIME / LATENCY / POWER) for a compute optical-flow + frame-interp pipeline on Polaris12, pass-for-pass against AMD's published FFX numbers rather than inventing a new algorithm.

## 0. What we measure (defined in README)
REAL FPS, GENERATED FPS, FRAME TIME, added LATENCY (motion-to-photon), POWER delta, plus: per-stage times (pyramid build; 7×[search-filter-upscale]; interp stages), DRAM traffic per frame, artifact rate (labeled subjective or via flow-consistency metric).

## 1. STAGE A — CALIBRATION vs AMD REFERENCE
Run the FidelityFX Optical Flow + Frame Interpolation SDK on the RX550 (Linux RADV + Vulkan, GLSL4.50 SM6.2 path) at 540p/720p/1080p, present-queue and async-queue variants:
- Record per-pass µs with timestamps; compare against FSR3 published tables normalized to RX550 (~1.2 TFLOPs vs 5700XT 9.75 TFLOPs; scale ≈ ×8, but bandwidth is only ×4-ish so expect super-linear on filters).
- This *replaces* re-implementing: the reference is the prior art subject.

## 2. STAGE B — ISOLATE THE "FREE CU" PREMISE
- Occupancy sweep: capture RViz/RADV counters (or `amdgpu` perf) during a GPU-bound game-like workload (e.g., DXVK/Vulkan game or a deterministic synthetic scene) and during OF. Determine whether game CUs are truly idle while (a) ROP/geometry-bound shadow/depth passes run and (b) during shading-bound phases.
- Test with CU reservation only if a capability audit finds a real API/control surface; no
  se asume que `VkPhysicalDeviceProperties` sea un mecanismo de reserva. Wave limiting y
  número de ACEs quedan `UNKNOWN`.
- Expected: the "holes" are narrow shadow/prepass windows; measure and timestamp them.

## 3. STAGE C — LATENCY BUDGET TEST
- Use an input-latency loop (like TechteamGB/LDAT-flavored or a simple LED-to-screen method) with and without FG, at base 30/45/60 REAL FPS.
- Record: real-frame interval (RR), flow+interp time (F), observed motion-to-photon (M). Assert M ≥ RR + F + display. Compare to FSR3 claims (they publish latency cut ONLY because Anti-Lag+ coexists; unavailable on this GPU tier).

## 4. STAGE D — ARTIFACT GATE
- Offline: FFmpeg encode the 4 scenarios (with/without FG) side-by-side; apply a perceptual/consistency metric (e.g., flow inpainting error at disocclusion boundary statistic) plus human label campaign (few clips).
- Pass/fail: FG accepted only if, at the real-fps the test enables, artifacts stay below "uninteractable in fast camera pan" — else reject per AMD's ">60 base recommended".

## 5. STAGE E — POWER
- Read `amdgpu_pm_info` energy counter (socket power in mJ) over a 60 s window for each config: base real-fps only vs +FG. Record board limit headroom. Report W/frame-of-generation.

## 6. METRICS TABLE (per config: 540p/720p/1080p × {async off, async on} × {reservation, none})
| pass | µs | F-pps | DRAM est. | PWR | available gap at target fps |

## 7. TOOLING
- RADV (Vulkan) + `GPUPerfAPI`/`RD` (RenderDoc) + `rasdaemon`/`amdgpu_top` for power and L2/DRAM.
- FFX SDK: https://github.com/GPUOpen-LibrariesAndSDKs/FidelityFX-SDK (OpticalFlow + FrameInterpolation).
- Comparison videos/bench: FSR3 Forspoken (TechPowerUp) and FSR3 press deck (GPUOpen) for artifact and overhead baselines.

## 8. DECISION RULE
Proceed seed only if, at 720p with a light (~ROPs-beach) workload, OF+FI total < 6 ms AND added latency < +1 frame + 8 ms AND artifacts pass Stage D. Otherwise the feature is a documentation-only finding (recommended status as per audit).
