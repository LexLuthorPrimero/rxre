# IDEA I-05 — GPU FRAME RECORDER FOR GFX8: ARCHITECTURE

> **Fase:** FASE R-3 — DOCUMENTARY NOVELTY AUDIT (SOLO DOCUMENTAL, no implementación; DISEÑO, no código)
> Target: RX 550 = Polaris12 (GFX8): 8 CUs / 512 SP / 16 ROPs / 512 KB L2 / 112 GB/s.

## 1. DESIGN SPACE — WHAT A "FRAME RECORDER" MEANS HERE

Three legitimate capture tiers for GFX8, in order of increasing depth and implementation cost:

| Tier | What it records | Tool precedent | Feasibility on Polaris12 |
|---|---|---|---|
| **T0 — API** | Every Vulkan call + timing (draws, buffers, barriers) | api_dump / gfxreconstruct / RenderDoc | DONE by others; no need to build |
| **T1 — Kernel/queue** | Job lifecycle: submit → run → done, vblank, fences | trace-cmd + GPUVis | DONE by GPUVis; reuse |
| **T2 — SQTT** | Per-wavefront shader occupancy/stall trace inside each frame (the "expensive" slot) | RADV `MESA_VK_TRACE=rgp` (write side) | Write-side present; **viewer missing** → the I-05 core |

The value of I-05 concentrates in **T2 analysis**. Sections 2–4 therefore describe the minimal architecture for a T2 pipeline: capture on RADV → RGP-format `.rgp` → GFX8 SQTT (v2.2) decoder → viewer.

## 2. END-TO-END PIPELINE (target architecture)

```
 Vulkan app (game/benchmark) on RX 550
   │  (VK_ICD_FILENAMES → RADV for gfx902)
   ▼
 RADV frontend  ──MESA_VK_TRACE=rgp──►  .rgp capture file (SQTT streams, SQTT_VERSION_2_2)
   │                                          (requires profile_peak sysfs write → DNS-12 gate)
   ▼
 RGP-format container reader  (parse header, sections; open format per AMD RGP manual + Mesa ac_rgp.c)
   ▼
 SQTT packet decoder  (SQTT_VERSION_2_2: token stream → per-CU/per-SE wavefront events, PC, stall states)
   ▼
 Per-frame aggregation  (group by frame id / draw call / submission; build wavefront timeline)
   ▼
 Viewer / exporter   (timeline UI and/or JSON/CSV export like rgp-inspect)
```

## 3. COMPONENTS AND PROVENANCE

1. **Capture layer — reuse Mesa, don't build.** RADV already emits RGP-format `.rgp` with SQTT for GFX8 (verified in source: `ac_sqtt.c` gfx8 regs; `ac_rgp.c` GFXIP_8 → SQTT_VERSION_2_2; `si_init_sqtt` accepts gfx_level ≥ GFX8). No new driver code needed. The only blocker is the `profile_peak` sysfs write during peak profiling for SQTT — a **DN-12 authorization-gated step**, not a design problem.
2. **Container reader — the least-known part.** RGP `.rgp` is a documented-in-practice binary format; primary references are AMD's RGP manual and Mesa's `ac_rgp.c` (which writes it). A reader mirrors the writer. `rgp-inspect` already implements a reader for modern RGP files — a fork/extension is the cheapest route (see §6).
3. **SQTT v2.2 decoder — the true build effort.** Tokens (wave start/stop, program counter, stall reason, scheduler events) must be decoded for the GFX8 SQTT version. Mesa's `ac_sqtt.c` has GFX8 register definitions; the trace-packet grammar is shared with newer SQTT versions but register/opcode differences for v2.2 must be audited. This is the component no open tool currently ships for v2.2.
4. **Aggregation & viewer — commodity.** Timeline rendering (GPUVis-style or web-based) is known work. Alternatively pipeline decoded JSON into `rgp-inspect`-style CSV for Pandas/Excel analysis.

## 4. POLARIS12 DATA VOLUME BOUNDS (why the design is tractable)

8 CUs / 2 SEs (Polaris12: 1 SE, 8 CUs — see R0-4). SQTT traces scale with active wavefronts × program counter sampling. Compared to RDNA (many more CUs/tokens), a GFX8 8-CU trace is *smaller*; the decoder/renderer does not need RDNA-class throughput. Practical expectation (hypothesis, unverified): per-frame SQTT capture at 1080p30 on 8 CUs yields tens of MB/minues of trace tokens — within any modern parser's capability. `[HIPÓTESIS]`

## 5. DEPENDENCIES / RESTRICTIONS

- **`profile_peak` sysfs write** — REQUIRED by RADV SQTT peak path. Subject to DN-12: needs explicit authorization + snapshot/readback/restore + display-on-Intel failsafe.
- **Counter programming NOT authorized** — T2 (SQTT) is NOT a counter reader; SQTT is a trace mechanism, distinct from GRBM/SQ PERF_SEL counters (FASE D/M). The design must not drift into PERF_SEL programming.
- **AMDVLK irrelevant** — EOL for GFX8 (Oct 2023). RADV is the only Vulkan path.
- **RGP GUI** — only relevant as an optional cross-check if RGP ≤1.16 binaries are obtainable and load GFX8 traces (`[NO VERIFICADO]`).
- **Viewer preference**: terminal/web/CSV (like rgp-inspect) over a full GUI — much smaller surface for a documentary-first project.

## 6. BUILD ROUTES (ranked by risk; documentary evaluation only)

| Route | Description | Risk | Rationale |
|---|---|---|---|
| **R1** | Fork `rgp-inspect`; add SQTT_VERSION_2_2 decoder support | Medium | Existing reader/writer/JSON pipeline; only the v2.2 grammar is new. Decoder targets gfx1201 today — a GFX8 backport is plausible but not verified. `[HIPÓTESIS]` |
| **R2** | Custom minimal reader+decoder reading RGP manual + Mesa `ac_rgp.c`/`ac_sqtt.c` as spec | High | Ground-up; accurate but much larger effort; risk on undocumented packet details |
| **R3** | Skip SQTT: build only a T1 (kernel timeline) + T0 (API) recorder combining GPUVis + api_dump | Very low | Already solved; adds little novelty; provides an immediate "frame recorder" deliverable |

## 7. OPEN QUESTIONS (to be closed before any code)

1. Does the current RGP GUI (2.x) load GFX8-era `.rgp`? If yes → all-work-done, I-05 becomes trivial reuse. `[NO VERIFICADO]`
2. Can `rgp-inspect`'s decoder be pointed at SQTT_VERSION_2_2 with modest changes (structure shared) or does v2.2 need a full new grammar? `[NO VERIFICADO]`
3. Does RADV actually emit valid SQTT v2.2 on Polaris12 in practice (source says yes; empirical run needs `profile_peak` authorization)? `[HIPÓTESIS → needs authorized run]`
4. Does reading SQTT perturb the GPU enough to distort the frame being recorded (observability perturbation)? `[NO VERIFICADO]`

## 8. SUMMARY

The architecture is: **reuse** Mesa's SQTT writer (T2 write-side) + GPUVis/api_dump (T0/T1); **build** only the missing GFX8 SQTT v2.2 decoder/viewer (the single genuine gap). Everything else in the "recorder" already exists on this stack. The design remains documentary; nothing runs until authorization gates (notably `profile_peak`) are passed.