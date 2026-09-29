# IDEA I-05 — GPU FRAME RECORDER FOR GFX8: CAPABILITIES

> **Fase:** FASE R-3 — DOCUMENTARY NOVELTY AUDIT (SOLO DOCUMENTAL, no implementación)
>
> **RECONCILIACIÓN 2026-09-23:** la ruta RADV source-level auditada es
> `radv_device_init_rgp()` → `radv_sqtt_init()`. La presencia de `ac_sqtt.c` no prueba
> una captura real en Polaris12. `si_init_sqtt()` es RadeonSI y no evidencia RADV/GFX8.
> `rgp-inspect` upstream está orientado a `gfx1201`; no se asume soporte GFX8.
> Target: RX 550 = Polaris12 (GFX8 / GCN 4.0): 8 CUs / 512 SP / ~1.2 TFLOPs / 16 ROPs / 512 KB L2 / 128-bit GDDR5 96–112 GB/s nominal/estimado; real `UNKNOWN`.

What the RX550 triangle (app − RADV/Mesa − kernel/amdgpu) can actually deliver for "recording a frame" in 2026, categorized by capture tier. All statements are documentary (verified from source or flagged).

## 1. PROVEN / AVAILABLE TODAY (no new code, no authorization issue)

| Tier | Tool | Works on Polaris12? | Nature | Notes |
|---|---|---|---|---|
| API frame dump | VK_LAYER_LUNARG_api_dump | Yes (Vulkan) | text/HTML/JSON of every call | Timestamps; `output_range`, `pre_dump`, `file` options |
| API capture/replay | gfxreconstruct | Yes | Vulkan capture/replay | `page_guard`/`userfaultfd`; deterministic replay |
| API frame capture+viewer | RenderDoc 1.40+ | Yes (Vulkan 1.4 on Linux) | Draw/resource capture, frame viewer | RGP interop via "Create New RGP Profile" |
| API call trace | apitrace | Yes (GL/EGL; limited Vulkan) | GL traces | Legacy tool |
| Kernel job timeline | ftrace/trace-cmd + GPUVis | Yes (amdgpu tracepoints) | Queue/job timeline, vblank, fence | GPUView-style; no counter programming |

Key kernel tracepoints (verified): `gpu_scheduler` stable uAPI (`drm_sched_job_queue`, `drm_sched_job_run`, `drm_sched_job_done`, `drm_sched_job_wait_dep`), vendor `amdgpu_cs_ioctl`, `amdgpu_sched_run_job`, `amdgpu_bo_create`, `amdgpu_bo_move`, `amdgpu_iv`, `drm_vblank_event`. Source: https://eunomia.dev/tutorials/xpu/gpu-kernel-driver/

## 2. PRESENT IN SOURCE / PLAUSIBLE — GATED

| Tier | Tool | Status on GFX8 | Gate |
|---|---|---|---|
| SQTT capture (write side) | RADV `MESA_VK_TRACE=rgp` | Source-level path `radv_device_init_rgp()` → `radv_sqtt_init()`; runtime GFX8 no confirmado | `REQUIRES CAPABILITY AUDIT`; cualquier ajuste externo de perfil sería autorización separada |
| SQTT view/analyze (GFX8) | RGP 2.x / RDP / rgp-inspect | RGP 2.x/RDP = RDNA; `rgp-inspect` upstream orientado a `gfx1201` | **UNKNOWN/GAP**: no se confirma decoder GFX8 |
| Hardware counters (GFX8) | GPUPerfAPI `v3.17` / `v3.11.1` histórico | 2304 filas de catálogo, no eventos validados para `1002:699f` | Programación PERF_SEL: **NO AUTORIZADA** |

## 3. ABSENT / NOT VIABLE

- **AMDVLK** — EOL for Polaris/Vega (Oct 2023). Not usable for Vulkan on GFX8.
- **Radeon Developer Panel (RDP)** — RDNA-only (issue #36: non-RDNA unsupported).
- **RGP 1.x GUI on a modern system** — whether the old GCN-era profiler still runs/loads GFX8 `.rgp` is **NOT VERIFIED**; legacy binaries may be gone.
- **Counter-based frame recorder** — requires PERF_SEL/MMIO writes = programming → outside authorization; documentary only.

## 4. IMPLICATION FOR THE PROJECT

The physically-available recorder within the project's no-write/no-programming constraints is
the **API + kernel tier**. SQTT remains `REQUIRES CAPABILITY AUDIT`: source code suggests a
possible route, but no real GFX8 capture or open decoder is confirmed. A hypothetical viewer
gap is not a runtime capability claim.
