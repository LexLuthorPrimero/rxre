# IDEA I-05 — GPU FRAME RECORDER FOR GFX8: PRIOR ART

Novelty audit. Sources ranked primary > community. The subject decomposes into (A) API-level capture, (B) queue/job timeline, (C) SQTT / wavefront capture on GCN/GFX8, (D) SQTT/RGP viewer and analyzer, (E) counter-based profiling, (F) the specific Polaris12 platform constraint.

## 1. API-LEVEL CAPTURE / REPLAY (no GPU internals) — FULLY COVERED
1. **RenderDoc** `[VERIFICADO]` — Vulkan 1.4 Linux, GPU-agnostic, works on RADV/Polari. RGP interop embeds `.rgp` in `.rdc` (bidirectional since RGP 1.2). No hardware counters, no wavefront view; but captures every API call/draw/resource. **Source:** https://renderdoc.org/docs/behind_scenes/vulkan_support.html ; https://renderdoc.org/docs/how/how_rgp_profile.html
2. **gfxreconstruct** `[VERIFICADO]` — GPU-agnostic Vulkan capture/replay on Linux; `page_guard` / `userfaultfd`. Deterministic replay for perf testing. **Source:** https://vulkan.lunarg.com/doc/view/latest/linux/capture_tools.html
3. **apitrace** `[VERIFICADO]` — GL/EGL/D3D + limited Vulkan. Good for call logging; not for GPU-internal profiling. **Source:** https://github.com/apitrace/apitrace/blob/master/docs/USAGE.markdown
4. **VK_LAYER_LUNARG_api_dump** `[VERIFICADO]` — text/HTML/JSON Vulkan call dump with timestamps. Useful for lightweight per-frame call sequences. **Source:** https://vulkan.lunarg.com/doc/view/latest/windows/api_dump_layer.html

**Novelty tag:** All of the above are known, shipped, and GPU-agnostic. Building a new API capture tool offers zero novelty.

## 2. KERNEL / QUEUE TIMELINE RECORDING — FULLY COVERED
5. **Linux DRM tracepoints** `[VERIFICADO]` — stable `drm_sched_job_{queue,run,done,wait_dep}` uAPI + vendor `amdgpu_{cs_ioctl,sched_run_job,bo_create,bo_move,iv}` + `drm_vblank_event`. Enables amdgpu job lifecycle recording via `trace-cmd`/ftrace/perf without counter programming. **Source:** https://eunomia.dev/tutorials/xpu/gpu-kernel-driver/
6. **GPUVis** (`mikesart/gpuvis`) `[VERIFICADO]` — MIT, GPUView-like Linux profiler. Reads ftrace of amdgpu events, builds colored HW queue / SW→HW / vblank / fence timelines per-frame. Last push 2026-01-14; covers Polaris-era amdgpu. **Source:** https://github.com/mikesart/gpuvis ; https://github.com/mikesart/gpuvis/wiki/Overview

**Novelty tag:** Kernel job-timeline recording on Polaris is known, open, and functional via GPUVis. No novelty here.

## 3. SQTT / WAVEFRONT CAPTURE (the GCN4/GFX8 layer)
7. **RGP 1.x (historical, GCN-era)** `[VERIFICADO]` — shipped SQTT capture support for GCN cards including Polaris/RX400/RX500 (GDC 2018 RGP 1.2 announcement; TechPowerUp confirmed Polaris support). SQTT_VERSION_2_2 corresponds to GFX8. **Source:** https://www.techpowerup.com/242615/ ; AMD GPUOpen RGP documentation era
8. **RGP 2.x (current, RDNA-only)** `[VERIFICADO]` — current official support matrix: RX 9000/7000/6000/5000 + RDNA APUs. No GFX8 listed. **Source:** https://gpuopen.com/rgp/ ; https://github.com/GPUOpen-Tools/radeon_gpu_profiler
9. **Mesa/RADV `MESA_VK_TRACE=rgp` SQTT writer for GFX8** `[VERIFICADO]` — source code confirms: `ac_sqtt.c` includes GFX8 register set; `ac_rgp.c` maps `GFXIP_8 → SQTT_VERSION_2_2`; `si_init_sqtt` in radeonsi accepts `gfx_level >= GFX8`. RADV captures RGP-format `.rgp` files containing SQTT streams on GFX8. **Source:** docs.mesa3d.org/drivers/radv.html ; Mesa upstream source
10. **`profile_peak` write dependency** `[VERIFICADO]` — RADV SQTT peak profiling requires writing `profile_peak` sysfs node. This is a sysfs write, subject to DN-12 / project permanent rule (authorization required for any sysfs write). **Source:** Mesa `ac_check_profile_state()`
11. **RGP-RADV crash / fix** `[VERIFICADO]` — RGP 2.0.0.19 crashed on radv `.rgp` captures; fixed in later releases. Confirms interop is intended but historically fragile. **Source:** https://github.com/GPUOpen-Tools/radeon_gpu_profiler/issues/98
12. **RGPR format heritage** — RGP's `.rgp` format includes SQTT packet streams. The decoder exists in two places: (a) RGP's own proprietary viewer (RDNA-only in 2.x), (b) `rgp-inspect` (see §4). There is no open decoder tuned to SQTT_VERSION_2_2 today.

**Novelty tag:** SQTT capture on GFX8 is *supported in Mesa* but the **viewer/decoder for GFX8 RGP traces is a gap**. This is where I-05's value lives.

## 4. RGP-FORMAT VIEWER / DECODER — THE GAP
13. **RGP proprietary viewer (AMD)** `[VERIFICADO]` — RDNA-only in 2.x era; whether RGP ≤1.16 still loads GFX8 traces is **NOT VERIFIED** (need old binary). `[NO VERIFICADO]`
14. **`rgp-inspect` (`hlky/rgp-inspect`)** `[VERIFICADO]` — open-source Rust CLI for RGP capture/inspection; decodes SQTT streams to JSON/CSV. Current development targets **RDNA4 / gfx1201** (`gfx12`). A fork or extension to handle `SQTT_VERSION_2_2` (GFX8) is conceptually possible — the packet format structure is documented in AMD's RGP manual and Mesa source — but **not implemented today**. `[HIPÓTESIS]` (retro-portability not verified). **Source:** https://github.com/hlky/rgp-inspect

**Novelty tag:** **PARTIALLY NOVEL / NOVELTY UNKNOWN.** The gap is real (no open GFX8 SQTT viewer exists). Whether (a) rgp-inspect can be trivially extended to SQTT_VERSION_2_2, or (b) historical RGP ≤1.16 already works, determines whether this is actually novel or a trivial porting task.

## 5. COUNTER-BASED PROFILING (GFX8 PERF_SEL tables) — ACCESS-BLOCKED
15. **GPUPerfAPI v3.11.1** `[VERIFICADO]` — only open source with GFX8 counter tables (~2304 exposed rows). v4.0+ removed GCN. Tag `GPUOpen-Tools/gpu_performance_api` v3.11.1. **Source:** https://github.com/GPUOpen-Tools/gpu_performance_api ; local audit `FASE-R0/R0-6`
16. **CodeXL** `[VERIFICADO]` — EOL/archived; historically integrated GPUPerfAPI with VI (Polaris) counter access. Not maintained; binary not reliably available.
17. **Counter programming NOT AUTHORIZED** — FASE M/D (decisions.md DN-12, permanent rule). Any "frame recorder" that programs GRBM/GRBM2/SQ counters requires sysfs MMIO writes → not buildable in the current project state. Counter tables are knowledge-only at this time.

**Novelty tag:** Counter tables are documented and open (GPUPerfAPI v3.11.1), but using them requires an authorization gate not yet reached. The recorder must be designed as counter-free.

## 6. AMDVLK EOL AND THE RADV-ONLY REALITY
18. **AMDVLK dropped Polaris/Vega (Oct 2023)** `[VERIFICADO]` — AMD stopped shipping the closed Vulkan driver for GCN-era on Linux. RADV (Mesa) is now the only maintained Vulkan path. Any GFX8 frame recorder must target RADV. **Source:** https://videocardz.com/newz/amd-officially-drops-vulkan-driver-support-for-polaris-and-vega-architectures-on-linux

## 7. NOVELTY TAG ASSESSMENT

| Layer | Coverage | Gap? |
|---|---|---|
| API capture (draw/resource) | RenderDoc, gfxreconstruct, apitrace | No |
| Queue/job timeline | tracepoints + GPUVis | No |
| SQTT/wavefront capture (write side) | RADV MESA_VK_TRACE=rgp on GFX8 | No (but `profile_peak` write gate) |
| SQTT/RGP **viewer for GFX8** | RGP 2.x = RDNA-only; rgp-inspect = gfx12 | **YES — the gap** |
| Counter tables | GPUPerfAPI v3.11.1 (read only; write not authorized) | Knowledge gap only (tables exist) |

**Verdict:** The specific formulation — "build a GFX8 SQTT/RGP viewer/analyzer on Linux, to fill the gap left by RGP 2.x dropping GCN" — is **PARTIALLY NOVEL / NOVELTY UNKNOWN**. The gap is real; whether it is a trivial port (make rgp-inspect handle v2.2 packets) or requires non-trivial reverse engineering depends on verification steps not yet completed (§3 below). The capture side is fully covered; only the analysis/viewer tier is under-served.

**Recommended path if pursued:** verification-first: (1) locate RGP 1.x binaries, test loading GFX8 `.rgp` on current GUI; (2) attempt to feed GFX8 `.rgp` into rgp-inspect, identify what breaks; (3) only if (1)+(2) fail, invest in a custom SQTT v2.2 decoder. No sysfs writes (profile_peak) occur without explicit DN-12 authorization.