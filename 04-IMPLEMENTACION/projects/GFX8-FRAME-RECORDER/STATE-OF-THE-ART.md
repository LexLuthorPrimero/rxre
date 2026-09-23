# IDEA I-05 — GPU FRAME RECORDER FOR GFX8: STATE OF THE ART

> **Archivo:** `projects/GFX8-FRAME-RECORDER/STATE-OF-THE-ART.md`
> **Fase:** FASE R-3 — DOCUMENTARY NOVELTY AUDIT (SOLO DOCUMENTAL, no implementación)
> **Fecha:** 2026-09-22
> **Target:** RX 550 = Polaris12 (GFX8 / GCN 4.0): 8 CUs, 512 SP, ~1.2 TFLOPs FP32, 16 ROPs, 512 KB L2, 128-bit GDDR5, 112 GB/s, 2 GB VRAM (SKU).
> **Clasificación de hechos:** `[VERIFICADO]` = confirmado por fuente primaria consultada · `[HIPÓTESIS]`/`[NO VERIFICADO]` = no confirmado.

Survey of everything that can "record a frame" (API calls, queue/job timeline, wavefront/SQTT execution, counters) on the Vulkan stack, and which tiers GFX8/Polaris12 still reach today (2026). Sources ranked primary > community.

## 1. API-LEVEL CAPTURE / REPLAY (no GPU internals)
1. **RenderDoc** `[VERIFICADO]` — Vulkan/GL/D3D frame capture + replay; Vulkan 1.4 support on Linux (v1.40, released 2025-09-05). Integrates with RGP ("Create New RGP Profile", embeds `.rgp` in `.rdc`). Works on AMD APUs/integrated/dGPUs — GPU-agnostic above the API. Records *draws/resources*, not wavefronts, not counters.
   - https://renderdoc.org/docs/behind_scenes/vulkan_support.html
   - https://renderdoc.org/docs/how/how_rgp_profile.html
   - https://gpuopen.com/manuals/rgp_manual/renderdoc_and_rgp_interop/
2. **gfxreconstruct** `[VERIFICADO]` — LunarG Vulkan capture/replay, Linux + Windows, GPU-agnostic (runs on Polaris). Mechanisms: page_guard / userfaultfd. Good for "re-record a frame" and replay determinism, not for performance internals.
   - https://vulkan.lunarg.com/doc/view/latest/linux/capture_tools.html
3. **apitrace** `[VERIFICADO]` — GL/EGL/D3D trace/replay; Vulkan support (`vkTrace`) exists but limited on Linux. Old demo/trace workflow.
   - https://github.com/apitrace/apitrace/blob/master/docs/USAGE.markdown
4. **VK_LAYER_LUNARG_api_dump** `[VERIFICADO]` — LunarG validation-layer add-on: text/HTML/JSON dump of every Vulkan call with timestamps; `output_range`, `pre_dump`, file options. The "cheap call catalog" per frame.
   - https://vulkan.lunarg.com/doc/view/latest/windows/api_dump_layer.html

**Reading:** the "API frame recorder" category is fully covered by shipped, GPU-agnostic tools. Nothing new to build at this tier.

## 2. DRIVER / KERNEL QUEUE-TIMELINE CAPTURE (job lifecycle)
5. **Kernel tracepoints (amdgpu + drm) `[VERIFICADO]`** — stable uAPI `gpu_scheduler` set (`drm_sched_job_queue/run/done/wait_dep`) + vendor `amdgpu_*` events (`amdgpu_cs_ioctl`, `amdgpu_sched_run_job`, `amdgpu_bo_create`, `amdgpu_bo_move`, `amdgpu_iv`) + `drm_vblank_event`. Enable with /sys/kernel/debug/tracing (tracing_set_events / per-function filter as used by GPUVis).
   - https://eunomia.dev/tutorials/xpu/gpu-kernel-driver/
6. **GPUVis (`mikesart/gpuvis`) `[VERIFICADO]`** — MIT, Linux GPU profiler modeled on GPUView: reads trace-cmd/ftrace dumps of amdgpu (and drm/i915, tegra) events and draws HW queue timelines, SW→HW queue mapping, vblank, fence signaling. Supports kprobes/uprobes and kallsyms column symbolization. Last activity 2026-01-14; releases since v0.1 (2022-01-24). Wiki shows GPUView-style colored event tracks. This is the nearest open thing to a "queue timeline recorder" that still covers GCN-era amdgpu.
   - https://github.com/mikesart/gpuvis
   - https://github.com/mikesart/gpuvis/wiki/Overview

**Reading:** queue/job timeline recording exists and works on Polaris-era amdgpu via ftrace. Not proprietary-blocked, no counter programming involved.

## 3. WAVEFRONT / SQTT (Shader Queue Thread Tracing) CAPTURE — the "real" GPU frames
7. **Radeon GPU Profiler (RGP)** — AMD's proprietary profiler.
   - Current **RGP 2.x** official support matrix is **RDNA only** (RX 9000/7000/6000/5000, RDNA APUs) `[VERIFICADO]` — https://gpuopen.com/rgp/ , https://github.com/GPUOpen-Tools/radeon_gpu_profiler
   - **Historical RGP 1.x supported GCN-era cards** (Polaris/RX400/RX500, Fiji, Vega) per GDC/marketing era and per 2018 TechPowerUp coverage of RGP 1.2 `[VERIFICADO]` — https://www.techpowerup.com/242615/
   - **Not verified:** whether the *current* RGP GUI still loads GFX8-era `.rgp` captures, or whether a GCN-era RGP ≤1.16 binaries are still downloadable/functional. Everything else here depends on that. `[NO VERIFICADO]`
8. **Radeon Developer Panel (RDP) `[VERIFICADO]`** — current releases are RDNA-only; open issue tracker records requests to support non-RDNA (GPUOpen-Tools/radeon_developer_panel issue #36). Not a GFX8 path.
9. **Mesa/RADV — `MESA_VK_TRACE=rgp` `[VERIFICADO]`** — RADV (Vulkan 1.4+ for GFX8) has a built-in capture writer that exports **RGP-format** `.rgp` files (trace types: `rmv`, `rgp`, `rra`, `ctxroll`). SQTT (thread trace) support exists in source for GFX8 (`ac_sqtt.c` gfx8 registers; `ac_rgp.c` maps GFXIP_8 → `SQTT_VERSION_2_2`; RadeonSI `si_init_sqtt` accepts `gfx_level >= GFX8`).
   - https://docs.mesa3d.org/envvars.html
   - https://docs.mesa3d.org/drivers/radv.html
   - **Constraint (project-relevant):** SQTT peak profiling path calls `ac_check_profile_state()`, which RADEON performs by writing the sysfs `profile_peak` node → **that is a sysfs write**. Per `decisions.md` (DN-12 + permanent rule) any sysfs write requires prior authorization + snapshot/readback/restore. RADV SQTT capture on this machine is therefore **authorization-gated**, not "free".
10. **RGP crashes on RADV-exported profiles — known defect, fixed `[VERIFICADO]`** — upstream issue (crash loading radv RGP capture in RGP 2.0.0.19; fixed in later releases). Confirms both that the format is interoperable in principle AND that the upload path has historically been fragile.
    - https://github.com/GPUOpen-Tools/radeon_gpu_profiler/issues/98

**Reading:** the *writer* side of RGP-format capture for GFX8 exists (Mesa). The missing piece would be a *viewer/analyzer* for GFX8 RGP/SQTT captures (see rgp-inspect below), because AMD's own viewers went RDNA-only.

## 4. COUNTER-BASED CAPTURE (event-ID tables) — the GFX8 special case
11. **GPUPerfAPI `[VERIFICADO]`** — the only **open** source with complete GFX8 counter tables today is **v3.11.1** (`GPUOpen-Tools/gpu_performance_api` tag v3.11.1; header files `gpa_hw_counter_gfx8*.cc`, `public_counter_names…`; ~2304 exposed counter rows). v4.0+ **removed GCN (GFX8/GFX9)**. Referenced in local audit `FASE-R0/R0-6`.
    - https://github.com/GPUOpen-Tools/gpu_performance_api
12. **CodeXL `[VERIFICADO]`** — EOL/archived; historically bundled GPUPerfAPI for VI (Polaris) counter access; not maintained in 2026.
13. **RadeonTop `[VERIFICADO]`** — operational load via `gpu_busy`/registers only; no PERF_SEL event values. Reading utilization/busy is fine; event-count capture is not offered.
    - https://github.com/clbr/radeontop
14. **Counter *programming* is NOT AUTHORIZED on this project** (`decisions.md` DN-12; FASE M/M-D). A "frame recorder" that reads event IDs would require `GRBM_PERFCOUNTERn_SELECT`/`SQ_PERF_SEL` writes → **not buildable today** regardless of the tables. Any design must therefore be counter-free (SQTT-style, API-level, timestamps).

## 5. RGP-FORMAT DECODERS / ANALYZERS (what a GFX8 viewer could be)
15. **`rgp-inspect` (`hlky/rgp-inspect`) `[VERIFICADO]`** — open-source CLI to capture and inspect `.rgp` traces; decodes SQTT streams to JSON/CSV; current development targets **RDNA4 / gfx1201**. RGP format heritage means a GFX8/SQTT-2.2 retrofit is *conceptually* possible but not present today.
    - https://github.com/hlky/rgp-inspect
16. **AMDVLK EOL for Polaris/Vega (Oct 2023) `[VERIFICADO]`** — AMD stopped shipping the closed Vulkan driver for GFX8 class. On Linux the only realistic Vulkan path for Polaris12 is **RADV** (Mesa). Frame recording must target RADV.
    - https://videocardz.com/newz/amd-officially-drops-vulkan-driver-support-for-polaris-and-vega-architectures-on-linux

## 6. SYNTHESIS — where a "GFX8 frame recorder" would NOT be redundant
| Tier | Today's best GFX8-capable tool | Open? | Counter-free? |
|---|---|---|---|
| API frame capture | RenderDoc / gfxreconstruct / apitrace | yes | yes |
| Call dump + timestamps | VK_LAYER_LUNARG_api_dump | yes | yes |
| Kernel queue timeline | tracepoints + GPUVis | yes | yes |
| Wavefront/SQTT capture | Mesa `MESA_VK_TRACE=rgp` (SQTT 2.2 for GFX8) | yes | needs `profile_peak` write |
| SQTT **view/analyze** (GFX8) | **GAP** — RGP 2.x = RDNA; RDP = RDNA; rgp-inspect = gfx12 | open only for gfx12 | — |
| HW event counters (GFX8) | GPUPerfAPI v3.11.1 tables (read-side) | yes | NO — programming not authorized |

The only genuinely unfilled slot is the **SQTT/RGP viewer-analyst for GFX8**. This is the candidate "novel" core of I-05.