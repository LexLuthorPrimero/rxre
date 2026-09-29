# IDEA I-05 — GPU FRAME RECORDER FOR GFX8: STATE OF THE ART

> **Archivo:** `04-IMPLEMENTACION/projects/GFX8-FRAME-RECORDER/STATE-OF-THE-ART.md`
> **Fase:** FASE R-3 — DOCUMENTARY NOVELTY AUDIT (SOLO DOCUMENTAL, no implementación)
> **Fecha:** 2026-09-22
> **Target:** RX 550 = Polaris12 (GFX8 / GCN 4.0): 8 CUs, 512 SP, ~1.2 TFLOPs FP32, 16 ROPs, 512 KB L2, 128-bit GDDR5, **96–112 GB/s nominal/estimado; real `UNKNOWN`**, 2 GB VRAM (SKU).
> **Clasificación de hechos:** `[VERIFICADO]` = confirmado por fuente primaria consultada · `[HIPÓTESIS]`/`[NO VERIFICADO]` = no confirmado.
>
> **RECONCILIACIÓN 2026-09-24:** la ruta RADV source-level es
> `radv_device_init_rgp()` → `radv_sqtt_init()`. La existencia de `ac_sqtt.c` no prueba
> una captura real GFX8; `si_init_sqtt()` es RadeonSI. `rgp-inspect` upstream está
> orientado a `gfx1201` y no se asume decoder GFX8. El issue #98 documenta un crash,
> pero no se identificó un fix verificado.

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

**Lectura:** el timeline queue/job de ftrace está documentado para amdgpu de la era
Polaris y no requiere programación de contadores; no se ejecutó ni se certificó aquí
en la RX550 local.

## 3. WAVEFRONT / SQTT (Shader Queue Thread Tracing) CAPTURE — the "real" GPU frames
7. **Radeon GPU Profiler (RGP)** — AMD's proprietary profiler.
   - Current **RGP 2.x** official support matrix is **RDNA only** (RX 9000/7000/6000/5000, RDNA APUs) `[VERIFICADO]` — https://gpuopen.com/rgp/ , https://github.com/GPUOpen-Tools/radeon_gpu_profiler
   - **Historical RGP 1.x supported GCN-era cards** (Polaris/RX400/RX500, Fiji, Vega) per
     GDC/marketing era and 2018 TechPowerUp coverage `[SOURCE-HISTORICAL; runtime local UNKNOWN]`
     — https://www.techpowerup.com/242615/
   - **Not verified:** whether the *current* RGP GUI still loads GFX8-era `.rgp` captures, or whether a GCN-era RGP ≤1.16 binaries are still downloadable/functional. Everything else here depends on that. `[NO VERIFICADO]`
8. **Radeon Developer Panel (RDP) `[VERIFICADO]`** — current releases are RDNA-only; open issue tracker records requests to support non-RDNA (GPUOpen-Tools/radeon_developer_panel issue #36). Not a GFX8 path.
9. **Mesa/RADV — `MESA_VK_TRACE=rgp` `[SOURCE-LEVEL; RUNTIME UNKNOWN]`** — la ruta auditada
   es `radv_device_init_rgp()` → `radv_sqtt_init()`. La existencia de soporte SQTT en
   source no prueba que la RX550 emita una captura válida; `si_init_sqtt()` pertenece a
   RadeonSI y no es evidencia RADV/GFX8.
   - https://docs.mesa3d.org/envvars.html
   - https://docs.mesa3d.org/drivers/radv.html
   - **Constraint:** `ac_check_profile_state()` solo lee el estado del perfil. Cualquier
     establecimiento externo de `profile_peak`/performance level sería una escritura
     separada, sujeta a autorización; no se ejecuta aquí.
10. **RGP crashes on RADV-exported profiles — issue observed; fix no confirmado** — el issue #98
    documenta un crash al cargar una captura RGP de RADV. En la evidencia auditada no se
    identificó commit/release que pruebe que el problema quedó corregido.
    - https://github.com/GPUOpen-Tools/radeon_gpu_profiler/issues/98

**Lectura:** la ruta source-level de captura RGP/SQTT para GFX8 está documentada en Mesa,
pero la captura runtime en Polaris12 y el visor/analizador GFX8 son `UNKNOWN`. No se
concluye que el visor falte; se requiere capability audit.

## 4. COUNTER-BASED CAPTURE (event-ID tables) — the GFX8 special case
11. **GPUPerfAPI `[CATALOG ONLY]`** — `v3.17` es la referencia operativa de tablas GFX8;
    `v3.11.1` queda como extracción histórica. Las ~2304 filas expuestas no equivalen a
    eventos únicos/validados para `1002:699f`; v4.0+ eliminó GCN. Referencia: `R0-1`.
    - https://github.com/GPUOpen-Tools/gpu_performance_api
12. **CodeXL `[VERIFICADO]`** — EOL/archived; historically bundled GPUPerfAPI for VI (Polaris) counter access; not maintained in 2026.
13. **RadeonTop `[VERIFICADO]`** — operational load via `gpu_busy`/registers only; no PERF_SEL event values. Reading utilization/busy is fine; event-count capture is not offered.
    - https://github.com/clbr/radeontop
14. **Counter *programming* is NOT AUTHORIZED on this project** (`decisions.md` DN-12; FASE M/M-D). A "frame recorder" that reads event IDs would require `GRBM_PERFCOUNTERn_SELECT`/`SQ_PERF_SEL` writes → **not buildable today** regardless of the tables. Any design must therefore be counter-free (SQTT-style, API-level, timestamps).

## 5. RGP-FORMAT DECODERS / ANALYZERS (what a GFX8 viewer could be)
15. **`rgp-inspect` (`hlky/rgp-inspect`) `[UPSTREAM REVIEWED; NO GFX8 SUPPORT CLAIM]`** — el
    upstream auditado se presenta como CLI Windows/Python orientada a `gfx1201`; no es una
    ruta Rust/Linux GFX8 confirmada.
    - https://github.com/hlky/rgp-inspect
16. **AMDVLK EOL for Polaris/Vega (Oct 2023) `[VERIFICADO]`** — AMD stopped shipping the closed Vulkan driver for GFX8 class. On Linux the only realistic Vulkan path for Polaris12 is **RADV** (Mesa). Frame recording must target RADV.
    - https://videocardz.com/newz/amd-officially-drops-vulkan-driver-support-for-polaris-and-vega-architectures-on-linux

## 6. SYNTHESIS — where a "GFX8 frame recorder" would NOT be redundant
| Tier | Today's best GFX8-capable tool | Open? | Counter-free? |
|---|---|---|---|
| API frame capture | RenderDoc / gfxreconstruct / apitrace | yes | yes |
| Call dump + timestamps | VK_LAYER_LUNARG_api_dump | yes | yes |
| Kernel queue timeline | tracepoints + GPUVis | yes | yes |
| Wavefront/SQTT capture | Mesa/RADV source-level path; runtime GFX8 `UNKNOWN` | source-level only | `REQUIRES CAPABILITY AUDIT` |
| SQTT **view/analyze** (GFX8) | **UNKNOWN/GAP** — RGP 2.x/RDP = RDNA; `rgp-inspect` = gfx1201 | no GFX8 support confirmed | — |
| HW event counters (GFX8) | GPUPerfAPI catalog (`v3.17`; `v3.11.1` historical) | catalog only | NO — programming not authorized |

El posible hueco novelty es el visor/analizador SQTT/RGP para GFX8; su existencia,
novedad y viabilidad son `UNKNOWN`. Este es el núcleo candidato de I-05, no un hecho.
