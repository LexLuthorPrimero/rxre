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

**Novelty tag:** la grabación de timeline kernel en amdgpu era Polaris está documentada
como herramienta upstream; no se certificó ni ejecutó en esta unidad. No hay novedad
propuesta en esa capa.

## 3. SQTT / WAVEFRONT CAPTURE (the GCN4/GFX8 layer)
7. **RGP 1.x (historical, GCN-era)** `[SOURCE-HISTORICAL; runtime local UNKNOWN]` —
   las fuentes de la época describen captura SQTT para GCN/Polaris; no prueban que un
   binario/viewer actual cargue GFX8. **Source:** https://www.techpowerup.com/242615/ ;
   documentación histórica de AMD GPUOpen RGP.
8. **RGP 2.x (current, RDNA-only)** `[VERIFICADO]` — current official support matrix: RX 9000/7000/6000/5000 + RDNA APUs. No GFX8 listed. **Source:** https://gpuopen.com/rgp/ ; https://github.com/GPUOpen-Tools/radeon_gpu_profiler
9. **Mesa/RADV `MESA_VK_TRACE=rgp` SQTT writer for GFX8** `[SOURCE-LEVEL; RUNTIME UNKNOWN]` — la ruta auditada es `radv_device_init_rgp()` → `radv_sqtt_init()`. La presencia de `ac_sqtt.c` no prueba una captura real en Polaris12; `si_init_sqtt` pertenece a RadeonSI. **Source:** docs.mesa3d.org/drivers/radv.html ; Mesa upstream source
10. **Ajuste de perfil** `[REQUIRES CAPABILITY AUDIT]` — `ac_check_profile_state()` solo lee
    el estado del perfil. Cualquier establecimiento externo de `profile_peak`/performance level
    sería una escritura separada, sujeta a autorización; no se ejecuta aquí. **Source:** Mesa
    `ac_check_profile_state()`
11. **RGP-RADV crash / fix** `[ISSUE OBSERVED; FIX NOT CONFIRMED]` — el issue #98 documenta
    un crash con capturas RGP de RADV; no se identificó commit/release que pruebe el fix.
    **Source:** https://github.com/GPUOpen-Tools/radeon_gpu_profiler/issues/98
12. **RGP format heritage** — `.rgp` incluye streams SQTT. El decoder propietario de
    RGP 2.x es RDNA-only; `rgp-inspect` se auditó para `gfx1201`. La cobertura de un
    decoder GFX8/SQTT_VERSION_2_2 es `UNKNOWN`; no se afirma ausencia absoluta.

**Novelty tag:** la captura SQTT de GFX8 es una **posibilidad source-level**, no una capacidad
runtime confirmada; el visor/decoder GFX8 es un gap/UNKNOWN. Aquí podría estar el valor de
I-05 si una capability audit confirma la ruta.

## 4. RGP-FORMAT VIEWER / DECODER — THE GAP
13. **RGP proprietary viewer (AMD)** `[SOURCE-LEVEL / NOT VERIFIED]` — RDNA-only in
    2.x; whether an old RGP binary loads GFX8 traces is `UNKNOWN` (requires an old binary).
14. **`rgp-inspect` (`hlky/rgp-inspect`)** `[UPSTREAM REVIEWED; NO GFX8 SUPPORT CLAIM]` — el
    upstream auditado se presenta como CLI Windows/Python orientada a `gfx1201`; no es una
    ruta Rust/Linux GFX8 confirmada. **Source:** https://github.com/hlky/rgp-inspect

**Novelty tag:** **PARTIALLY NOVEL / NOVELTY UNKNOWN.** No se confirma un visor abierto GFX8;
    la viability de un backport o de RGP histórico queda `UNKNOWN`.

## 5. COUNTER-BASED PROFILING (GFX8 PERF_SEL tables) — ACCESS-BLOCKED
15. **GPUPerfAPI** `[CATALOG ONLY]` — `v3.17` es la referencia operativa de tablas GFX8;
    `v3.11.1` queda como extracción histórica. ~2304 filas expuestas no equivalen a eventos
    únicos/validados para Polaris12. v4.0+ eliminó GCN. **Source:** https://github.com/GPUOpen-Tools/gpu_performance_api ; local audit `FASE-R0/R0-6`
16. **CodeXL** `[VERIFICADO]` — EOL/archived; historically integrated GPUPerfAPI with VI (Polaris) counter access. Not maintained; binary not reliably available.
17. **Counter programming NOT AUTHORIZED** — FASE M/D (decisions.md DN-12, permanent rule). Any "frame recorder" that programs GRBM/GRBM2/SQ counters requires sysfs MMIO writes → not buildable in the current project state. Counter tables are knowledge-only at this time.

**Novelty tag:** Counter tables are documented as source-level catalog (GPUPerfAPI v3.17;
v3.11.1 historical), pero la aplicabilidad runtime/ASIC es desconocida. Usarlos requiere una
gate de autorización aún no alcanzada. El recorder debe diseñarse sin contadores.

## 6. AMDVLK EOL AND THE RADV-ONLY REALITY
18. **AMDVLK dropped Polaris/Vega (Oct 2023)** `[VERIFICADO]` — AMD stopped shipping the closed Vulkan driver for GCN-era on Linux. RADV (Mesa) is now the only maintained Vulkan path. Any GFX8 frame recorder must target RADV. **Source:** https://videocardz.com/newz/amd-officially-drops-vulkan-driver-support-for-polaris-and-vega-architectures-on-linux

## 7. NOVELTY TAG ASSESSMENT

| Layer | Coverage | Gap? |
|---|---|---|
| API capture (draw/resource) | RenderDoc, gfxreconstruct, apitrace | No |
| Queue/job timeline | tracepoints + GPUVis | No |
| SQTT/wavefront capture (write side) | RADV source-level path; GFX8 runtime `UNKNOWN` | `REQUIRES CAPABILITY AUDIT`; no write assumed |
| SQTT/RGP **viewer for GFX8** | RGP 2.x = RDNA-only; rgp-inspect = gfx12 | **UNKNOWN / CANDIDATE GAP** |
| Counter tables | GPUPerfAPI v3.17 catalog / v3.11.1 historical | Catalog only; write not authorized |

**Verdict:** the specific formulation — "build a GFX8 SQTT/RGP viewer/analyzer on Linux,
to fill the gap left by RGP 2.x dropping GCN" — is **PARTIALLY NOVEL / NOVELTY UNKNOWN**.
The candidate gap and whether it is a trivial port or requires reverse engineering remain
`UNKNOWN`; capture-side runtime capability is also unconfirmed.

**Recommended path if pursued:** verification-first: (1) locate RGP 1.x binaries, test loading GFX8 `.rgp` on current GUI; (2) attempt to feed GFX8 `.rgp` into rgp-inspect, identify what breaks; (3) only if (1)+(2) fail, invest in a custom SQTT v2.2 decoder. No sysfs writes (profile_peak) occur without explicit DN-12 authorization.
