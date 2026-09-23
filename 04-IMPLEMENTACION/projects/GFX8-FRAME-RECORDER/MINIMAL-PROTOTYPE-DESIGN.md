# IDEA I-05 — GPU FRAME RECORDER FOR GFX8: MINIMAL PROTOTYPE DESIGN

> **Fase:** FASE R-3 — DOCUMENTARY NOVELTY AUDIT (SOLO DOCUMENTAL; diseño, NO implementación; ninguna ejecución hasta autorización).
> Target: RX 550 = Polaris12 (GFX8): 8 CUs / 16 ROPs / 512 KB L2 / 112 GB/s.

The minimal *experiment* that would prove (or kill) the I-05 core claim — i.e. that a GFX8 SQTT viewer is both needed and buildable — with the least effort and zero permanent system changes.

## 0. GOAL

Answer, with evidence, the four open questions in ARCHITECTURE §7. Every step is read-only and reversible except the explicit `profile_peak` authorization gate (step 3).

## 1. STEPPIENDO — QUESTIONS TO RESOLVE

| # | Question | Decision the answer feeds |
|---|---|---|
| Q1 | Does RADV on Polaris12 emit a valid `.rgp` with SQTT v2.2 in practice? | Is T2 capture even possible on this box? |
| Q2 | Does the current RGP GUI (2.x) load a GFX8-era `.rgp`? | Is the "viewer gap" real, or is AMD's tool still usable? |
| Q3 | Can `rgp-inspect` (or a fork) decode SQTT v2.2 with modest changes? | Build route R1 vs R2 (see ARCHITECTURE §6) |
| Q4 | What is the trace's data volume and its observability perturbation on 8 CUs? | Is a small viewer/analyzer even necessary vs. a text dump? |

## 2. EXPERIMENT PLAN (documentary → then, only with authorization, execution)

### Phase A — DOCUMENTARY ONLY (can do now; no code, no sysfs writes)
1. **Inventory versions:** kernel (`uname -r`), Mesa/RADV (`vulkaninfo`, `glxinfo`), amdgpu firmware; confirm `profile_peak` exists for the RX550; confirm `MESA_VK_TRACE` string values for the installed Mesa (`rgp`, `rmv`, `rra`, `ctxroll`). Record the exact matrices (DN-13 requirement).
2. **Static decode test:** inspect `Mesa/src/amd/ac_sqtt.c` + `ac_rgp.c` for GFX8 (`gfx_level == GFX8`) handling; confirm SQTT_VERSION_2_2 path; find what packet layout v2.2 uses vs v12. Produce a written "what the trace grammar looks like" memo.
3. **Read-only capability check:** enumerate tracepoints (`/sys/kernel/tracing` or `/sys/kernel/debug/tracing`), verify `gpu_scheduler`/`amdgpu_*` events present for the RX550 BDF. No writes.

### Phase B — AUTHORIZATION-GATED (needs DN-12 approval for `profile_peak`)
4. Capture a small synthetic Vulkan workload (own workload or a tiny VK sample) with:
   - `MESA_VK_TRACE=rgp` and a small, fixed number of frames (not the whole benchmark).
   - Right before capture, write `profile_peak` (this is the ONE gated sysfs write — with snapshot/readback/restore + GPU-not-display failsafe).
5. Verify the `.rgp` file is non-empty and parseable by inspecting headers (hexdump/documented offsets from RGP manual + Mesa writer), WITHOUT relying on AMD's GUI.

### Phase C — VIEWER EVALUATION
6. Feed the captured `.rgp` to:
   - RGP 2.x GUI (if obtainable for Linux/Windows-Wine) → does it load or refuse?
   - `rgp-inspect` (build from source for the installed Rust toolchain) → note the exact error/section recognized; classify how far it gets.
7. If `rgp-inspect` fails only at SQTT decodeword level: estimate the diff to add v2.2 support (= build route R1, low risk). If it fails structurally (container version): classify as R2.

## 3. PASS / FAIL / ABORT CRITERIA

| Result | Classification |
|---|---|
| `.rgp` captured; RGP 2.x loads it fully → **viewer gap is NULL** | I-05 → tooling reuse; low novelty; document only |
| `.rgp` captured; rgp-inspect parses container but not SQTT v2.2 → **gap REALS, decoder miss** | I-05 → PARTIALLY NOVEL; R1 buildable |
| `.rgp` captured; no open tool parsed → **gap REAL, grammar non-trivial** | I-05 → PARTIALLY NOVEL; R2 needed, bigger effort |
| `.rgp` capture fails or `profile_peak` refused → SQTT on Polaris12 not practically usable | I-05 → NOVELTY UNKNOWN; recorder limited to T0/T1 (already solved by GPUVis) |
| Any sysfs write attempted outside the explicit authorized `profile_peak` step | **ABORT** — violates DN-12 |

## 4. RESOURCES NEEDED
- Installed kernel + Mesa version matrix (already available from MASTER-PLAN §A).
- A small deterministic Vulkan workload (reuse existing in `WORKLOAD-SINTETICO` or a 10-line VK triangle; must support `MESA_VK_TRACE` env).
- Rust toolchain to build `rgp-inspect` (or read-only static analysis of its source if build is not desired) — checking tool availability is part of Phase A, no install of the Mesa system, no permanent changes.
- RGP 2.x installer (only for evaluation; may require WINE/Vulkan — evaluate feasibility first; do not run if it cannot identify a display-independent RX550).

## 5. DELIVERABLE (regardless of outcome)
One `RESULTADOS-*` document (DN-13 methodology style) recording: version matrices, tracepoints inventory, `.rgp` capture log, decode results per tool, data-volume estimate, perturbation observation, and the decision tree outcome (reuse vs build R1 vs R2 vs abandon). No production feature is promised; this is a prove-or-kill gate for the I-05 novelty claim.

## 6. CONSTRAINTS REFRESH
- **Documental only** until authorization; the only candidate sysfs write is the `profile_peak` step in Phase B, and only with full snapshot/readback/restore protocol.
- **No counter programming** (GRBM/PERF_SEL/MMIO writes remain prohibited; SQTT is a trace mechanism, not a counter).
- **No AMDVLK** (EOL); RADV only.
- **No permanent kernel/Mesa/driver changes.**