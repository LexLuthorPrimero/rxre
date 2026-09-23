# IDEA I-05 — GPU FRAME RECORDER FOR GFX8: CAPABILITIES

> **Fase:** FASE R-3 — DOCUMENTARY NOVELTY AUDIT (SOLO DOCUMENTAL, no implementación)
> Target: RX 550 = Polaris12 (GFX8 / GCN 4.0): 8 CUs / 512 SP / ~1.2 TFLOPs / 16 ROPs / 512 KB L2 / 128-bit GDDR5 112 GB/s.

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
| SQTT capture (write side) | RADV `MESA_VK_TRACE=rgp` | Present in source (`ac_sqtt.c` gfx8 regs; `ac_rgp.c` GFXIP_8 → SQTT_VERSION_2_2; `si_init_sqtt` gfx_level≥GFX8) | Requires `profile_peak` sysfs write → **DN-12 authorization needed** (permanent rule: any sysfs write requires authorization + snapshot/readback/restore) |
| SQTT view/analyze (GFX8) | RGP 2.x / RDP / rgp-inspect | RGP 2.x = RDNA-only; RDP = RDNA; rgp-inspect targets gfx1201 | **GAP** — decoder for SQTT_VERSION_2_2 not present in any open tool |
| Hardware counters (GFX8) | GPUPerfAPI v3.11.1 | Tables present (~2304 rows), verified; v4.0+ removed GCN | Programming PERF_SEL requires MMIO writes → **NOT AUTHORIZED** (FASE M/D, DN-12) |

## 3. ABSENT / NOT VIABLE

- **AMDVLK** — EOL for Polaris/Vega (Oct 2023). Not usable for Vulkan on GFX8.
- **Radeon Developer Panel (RDP)** — RDNA-only (issue #36: non-RDNA unsupported).
- **RGP 1.x GUI on a modern system** — whether the old GCN-era profiler still runs/loads GFX8 `.rgp` is **NOT VERIFIED**; legacy binaries may be gone.
- **Counter-based frame recorder** — requires PERF_SEL/MMIO writes = programming → outside authorization; documentary only.

## 4. IMPLICATION FOR THE PROJECT

The physically-available "recorder" on this machine, within the project's no-write/no-programming constraints, is the **API + kernel tier** (RenderDoc, api_dump, gfxreconstruct, GPUVis/ftrace). The SQTT tier (real wavefront traces) is available only if `profile_peak` is authorized, and even then there is **no open GFX8 SQTT viewer**: the trace can be captured, but not analyzed with existing open tooling. Closing that viewer/analyzer gap is exactly what I-05 would have to own.

The RGP interop path (RenderDoc → embed `.rgp` → viewer) is validated on newer hardware; on GFX8 the writer exists in Mesa but the consumer (viewer) is what's missing. Confirmed fragily: RGP historically crashed loading radv captures (issue #98, fixed later) → format interop is real but version-sensitive.