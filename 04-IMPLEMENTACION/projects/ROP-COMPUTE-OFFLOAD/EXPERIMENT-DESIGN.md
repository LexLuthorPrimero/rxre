# IDEA I-04 — ROP OFFLOAD TO COMPUTE: EXPERIMENT DESIGN

Documentary/measurement-only plan. No production feature. Goal: quantify the true cost/benefit on Polaris12 (RX 550) so the hypothesis "ROP saturated + CUs free → compute faster" is tested, not assumed.

## 0. HYPOTHESES TO TEST
- H1: ROPs are *not* the real bottleneck on Polaris12 for typical scenes. (Expect: TRUE — fill need is tiny relative to 16 ROPs @ 1183 MHz.)
- H2: A compute rasterizer is ≥2× slower than the fixed path on game-like geometry. (Expect: TRUE — CUDARaster/CuRast/LucidRaster scaling.)
- H3: Async-compute co-scheduling of *complementary* compute during fixed-function-bound passes yields a net win. (Expect: small win, ~5–15%, the AMD-documented baseline.)

## 1. TEST A — BASELINE THROTTLE POINTS (no new code)
Instrument the *existing* fixed pipeline to find what bottlenecks first:
1. Render a 1080p scene with trivial shader (flat color) at high overdraw → observe if ROP/fill bound. Use Radeon GPU Profiler / `CodeXL` / VK timing: check `Pixel fill`, `Shader utilization`, `L2` counters.
2. Repeat with a PBR-ish shader → observe CU/ALU bound.
3. Read-back counters available on GCN4 (SPM) or simply time draws.
Expected output: a table of "which stage caps the frame per scene type." If no scene shows ROP-first, the idea is dead on arrival measurement-wise (still document it).

## 2. TEST B — STEPPED COMPUTE SUBSTITUTION
To isolate ROP-offload cost without a full renderer, replace stages incrementally (all in Vulkan, low-level AMD path):
- **B1. Compute "visibility only":** dispatch compute that writes a packed 64-bit depth+id visibility buffer to a UAV (`u64` atomicMin), resolve with a compute pass → compare vs hardware depth-only pass. Measure: atomics throughput, L2 line contention, total time.
- **B2. Compute "shade from vis":** shade the vis buffer in compute; compare vs hardware G-buffer/shading pass. Measure: texture-locality penalty (the documented compute-vs-fragment shading-order problem, stackexchange #9956).
- **B3. Compute "blend":** append per-pixel sorted fragment lists, blend in software (LucidRaster-style) for translucent geometry → compare vs hardware alpha blend.
- **B4. MSAA:** run all of the above at 2×/4× with software sample masks vs HW MSAA; record Θ(n·k) scaling.
This mirrors published pipelines (Laine, CuRast, Lucid). Every step gets a matrix entry `[time, bandwidth estimated, VRAM delta]`.

## 3. TEST C — ASYNC-COMPUTE CO-SCHEDULE (the legitimate variant)
1. Shadow-map or depth-prepass (ROP/geometry-bound) on the graphics queue.
2. Independent compute (light tile culling, blur, AO, or a synthetic ALU kernel) on the ACE compute queue.
3. Compare sequential vs queued/async with fences; tune with CU reservation (`VK_AMD`/DX12-equivalent ROI on Polaris12) and wave limiting (AMD GDC17).
This establishes the *realizable* ceiling the ROP-offload redesign would even be competing with.

## 4. TEST D — ENVELOPE / BANDWIDTH ACCOUNTING
- Record max mem-BW drawn: hardware path scalar (RBE compressed write) vs compute path (vis-write + resolve-read). Compute bound from DRAM counters, not just wall clock.
- Compute L2-traffic: DX12/Vulkan doesn't expose L2 counters cleanly on GCN4; estimate from instruction counts + published GCN L2 slice bandwidth (64 B/cycle/slice; RX 550 ≈ 4–8 slices → ≈ 380–760 GB/s theoretical, i.e. ~3–7 MB/frame of useful residency at 60 fps) and treat L2 residency as the deciding metric: >0.5 frame of live data = thrash.

## 5. METRICS / PASS/FAIL GATES
- Time per pass (µs), frame delta.
- Fragments/pixel (depth complexity) sweep: 1, 2, 5, 10.
- MSAA sweep: off, 2×, 4×.
- Resolution sweep: 720p/1080p/1440p.
- PASS = compute path within 1.5× of hardware **and** a real scene where ROPs were bottleneck #1. Anything else records FAIL against the claim and feeds the async variant instead.

## 6. TOOLING
- RADV on Linux (Mesa) for Vulkan timestamps + `VK_EXT_debug_utils`; or AMDVLK for profiling.
- Reference counters: `RadeonGPUProfiler` app on DX12, or `perfetto`/`GPUPerfAPI` if available.
- Reference implementations to diff against: nvpro-samples `render_raster_clusters_sw.comp.glsl`, WebGPU compute rasterizer tutorial, FidelityFX SDK (compute raster patterns).