# IDEA I-01 — TBDR EMULATION ON IMR: EXPERIMENT DESIGN

Documentary/measurement-only plan. No production feature. Goal: empirically measure what happens when you try to tile an IMR scene on Polaris12 — where does bandwidth actually land, and does the "tile < L2" claim survive real counters?

## 0. HYPOTHESES TO TEST (read-only measurement)
- H1: The fixed-function CB/RBE path already writes the framebuffer with DCC+HTILE in tiles; the write-bandwidth "win" of TBDR emulation is zero or negative.
- H2: Routing tile color/depth through compute shaders (image store) strictly increases bandwidth (loses DCC/HTILE, adds L2/DRAM traffic).
- H3: The only direction where on-chip residency *could* help is **shader-path read locality** — i.e., re-reading the same tile as a texture; L2 residency of a compute-written image across passes is unmeasurable on GFX8 but has a ceiling of ~0.5 frame at 512 KB.

## 1. TEST A — MEASURE THE REAL RBE/DCC/HTILE WRITE PATH (baseline, no code)
Instrument the **existing pipeline** to characterize the fixed-function framebuffer path.
- **Tool:** GPUOpen RCP (Radeon GPU Profiler) `CacheHit` / `L1CacheHit` / `L2CacheHit` counters; if unavailable on Polaris12 in RCP, fall back to `AMD_performance_monitor` via Gallium HUD or `perf` to observe `SHADER_MEM` traffic vs `CB_DB_BUSY`.
- **Workloads (read-only):**
  - Flat color 1080p fill (trivial shader → RBE-saturated) — record: `CB_DB_busy`, `CB_write`, `DB_write`, any `L2_*` counters visible.
  - PBR/textured PBR 1080p — record same; check if `L2` ever sees RB writes (expect: never on GFX8).
- **Expected output:** proof that in the fixed path, RBE writes **never touch L2** — the "tile-in-L2" hypothesis is dead on arrival at the hardware level. If this counter-truth can be documented, it is the whole conclusion.

## 2. TEST B — COMPUTE STORED TILES (the "I-04 variant" on a per-tile basis)
To isolate the per-tile cost without a full renderer, replace the RBE write with a compute image store:
- **B1.** Render a small scene; instead of a standard render-pass, dispatch a compute pass that writes the scene's color + depth via `imageStore` (VK_IMAGE_LAYOUT_GENERAL, format RGBA8) into a **tiled layout** (one dispatch per tile, tile coordinates dispatched as thread groups).
- **B2.** Repeat at a fixed tile size (64×64, 128×128, 256×256) and sweep the tile size.
- **B3.** Run the same scene with the **standard render-pass** as a reference.
- **Metrics:** wall time (µs per pass); DRAM bandwidth via `perf` + `power1_input` correlation; VRAM usage delta.
- **Expected output:** compute-path tiles are 2–10× slower and use more bandwidth than the RBE path (CuRast/Laine scaling); confirms DCC/HTILE loss is not recouped by tile locality.

## 3. TEST C — SHADER READ-LOCALITY (the only plausible win direction)
Separate the "residency" question from the write question:
- **C1.** Write a render target via the standard RBE (DCC+HTILE on). In a second pass, read it as a texture N times (N = 2, 4, 8) with a simple shader.
- **C2.** Same, but write the target via compute image store (no DCC/HTILE), then read as a texture N times.
- **C3.** Compare the per-pass time of the read phase across C1 and C2, and across N.
- **Rationale:** If L2 absorbs re-reads in C1, the *second* pass should be faster than DRAM; C2 is the lossy baseline. If C1 shows no L2 residency benefit, the whole idea of "L2-resident tiling for deferred" is dead even for reads.
- **Expected output:** L2 residency of a 1080p target (8+ MB >> 512 KB L2) is impossible; a 320×180 internal target (230 KB) *might* partially sit in L2, but only if the rest of the scene's texture/geometry working set doesn't evict it — measure via `L2CacheHit` (if available) or by observing that C1-per-pass is flat across N (indicating DRAM-resident, not L2-resident).

## 4. TEST D — BINNING PASS OVERHEAD (cost of adding a geometry bin)
Quantify the *overhead* of adding a screen binning pass on Polaris12:
- **D1.** Full-scene draw at 1080p; record per-draw overhead (Vulkan timestamp queries).
- **D2.** Same scene, but split into 4×4 screen bins (scissor per bin); record total draw time.
- **D3.** Sweep bin count: 2×2, 4×4, 8×8, 16×16.
- **Expected output:** a U-shaped curve — too few bins = no locality win, too many bins = dispatch/scissor overhead dominates on 8 CUs; the minimum point (if it exists) quantifies whether driver-level binning on this chip could ever beat the monolithic draw.

## 5. METRICS / PASS/FAIL GATES
- Time per pass (µs).
- DRAM bandwidth (estimated via power delta or `perf` HW counters if available).
- `L2CacheHit` / `L2Hit` delta between baseline and compute-tile path (if available; if not, report "counters unavailable" — a finding in itself).
- PASS = any test shows ≥10% bandwidth reduction *and* ≥10% latency improvement on a real-scene workload. FAIL = everything shows overhead or no change. Based on architecture, expect **FAIL on the write side** and a **measurement-limited result** on the read side.

## 6. TOOLING
- RADV on Linux, Mesa 26.2.2 (stock or /opt custom) — Vulkan timestamp queries + `VK_EXT_debug_utils`.
- GPUOpen RCP (`CacheHit` / `L2CacheHit` counters if GFX8 SPM exposes them).
- `AMD_performance_monitor` via Gallium HUD (if SPM counters are visible there).
- `perf` + `amdgpu` driver PMU for `gpu_busy`, `mem_read`, `mem_write`.
- rx550-torneo runner for controlled DPM conditions (auto, fan uncontrolled, cooldown between runs).