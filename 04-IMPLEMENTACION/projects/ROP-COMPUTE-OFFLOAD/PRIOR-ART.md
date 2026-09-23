# IDEA I-04 — ROP OFFLOAD TO COMPUTE: PRIOR ART SURVEY

Novelty status per item tracked. Sources ranked: primary (papers, vendor docs, official SDKs) > community.

**Idea under audit:** "Execute rasterization/visibility/shading and ROP-type work (depth test, blend, MSAA resolve) in compute shaders instead of the fixed-function graphics pipeline — on the assumption that ROPs saturate while CUs sit idle, so compute is 'free.'"

**CRITICAL THEORETICAL PREMISE CHECK (per task instructions):**

> Are CUs actually free when ROPs are busy?

On GCN4 (Polaris12) the premise breaks down as stated:
- ROP (render backend) work is *downstream* of fragment shading. Pixel shaders are exported to the render backends *after* shading (ChipsAndCheese GCN analysis). CUs are already toiling on fragment work before the ROPs see a byte. ROP saturation implies the CU array already delivered huge amounts of shading work — the CUs are NOT idle.
- Per Beyond3D community analysis (GCN-era, thread "ROPs and GCN cores"): "If your rendering shader is ROP bound you can for example use the remaining CU resources by running a compute shader simultaneously (asynchronous compute)." That is the *correct* framing — the offload opportunity is during ROP-bound *draws* with complementary work (async compute), not by moving ROP work into compute.
- CU/ROP balance on Polaris12 (RX 550): 8 CUs (512 shaders) / 16 ROPs (2 render backends) / 32 TMUs / 512 KB L2 / 128-bit GDDR5 (~112 GB/s). Render-backend color caches and depth caches are ~16 KB/4 KB per RBE tier on GCN and bypass L2 (ChipsAndCheese; GCN whitepaper).

**Actual throughput relationship (GCN, from primary/authoritative sources):**
- Tahiti-class GCN: 1 rasterizer per 16 CUs; each CU ~1 wave of 64 lanes needed per SIMD (4 SIMDs/CU) for full throughput. Small chips (8 CUs) have very little fork to give any engine extra work — occupancy is the floor, not the ceiling. (ChipsAndCheese)
- Compute writes go L1→L2→DRAM and can use atomics in L2 (16 atomics/line/cycle per slice, GCN whitepaper). Fragment color/depth writes go to render-backend tile caches and *bypass L2*, with delta color compression (DCC) applied at RBE (Polaris whitepaper; GCN whitepaper). So "ROP-offloaded-to-compute" does NOT reproduce CB bypass: it routes everything through L1→L2→memory, losing DCC/HTILE and tile-cache write absorption.
- ROP write capability per GCN architecture (Beyond3D 2014 analysis): per input-set a ROP can write up to 4×4 floats = 64 B; a compute thread that issues a store would be limited to ~8 B per store with bank-conflict exposure. Hardware ROPs also own MSAA replication, late depth/stencil, and coverage at *sample* frequency — all things compute must re-implement in software per sample atomics.

---

## 1. DIRECT PRIOR ART — SOFTWARE/COMPUTE RASTERIZATION (the core subject)

### Academic
1. **CUDARaster — Laine & Karras, 2011, HPG** "High-Performance Software Rasterization on GPUs"
   - Fully software pipeline (triangle setup, bin rasterizer, coarse+fine rasterizer) in CUDA; enforces API ordering (alpha blending, deterministic output, hole-free rasterization); supports MSAA.
   - Result: **within 2–8× of the hardware graphics pipeline on a top GPU**. The GOTO reference for ROP-emulation cost. Introduces the exact techniques (64-bit packed atomicMin depth, per-tile queues, coverage masks).
   - https://research.nvidia.com/sites/default/files/pubs/2011-08_High-Performance-Software-Rasterization/laine2011hpg_paper.pdf
   - Open source: https://code.google.com/p/cudaraster/ (now mirrored, e.g. https://github.com/uberto/rasterizer or forks)

2. **FreePipe — Liu, Huang, Fu, Dubó 2010** (I3D) — first to propose `atomicMin` per-pixel direct rasterization without fragment sorting — cited by CuRast. Multi-fragment focus.

3. **cuRE — Kenzel et al. 2018** (TVCG/HPG) "A High-Performance Software Graphics Pipeline on the GPU" — streaming multi-stage software rasterizer (subset of CUDARaster ideas with streaming). Several× slower than hardware for general scenes.

4. **CuRast — Schütz, Lipp, Kristmann, Wimmer 2026 (TU Wien)** "Cuda-Based Software Rasterization for Billions of Triangles"
   - 3-stage compute rasterizer (1 thread/tiny tri → 1 warp/medium → 64 threads/large); 64-bit `atomicMin` vis buffer (28-bit depth + 36-bit triangle id).
   - Results: **2–5× faster than Vulkan hardware path on massively dense/instanced geometry; Vulkan 10× faster on typical game-like scenes** (Sponza). Opaque only — "blending/transparency slows the pipeline down", deferred to later passes.
   - Key quote of relevance to this audit: even for the *best case* (mico-poly dense geometry) the win is only when triangle size is ~1 pixel; for "small models producing large triangles… Vulkan remains 10x faster."
   - https://arxiv.org/html/2604.21749 ; https://github.com/m-schuetz/CuRast
   - **Directly contradicts the premise that "ROP-saturated+compute-free = faster" for ordinary scenes.**

5. **LucidRaster — Jakubowski 2024** "Real-Time GPU Software Rasterizer for Exact OIT"
   - Compute-shader software rasterizer (Vulkan GLSL) for exact order-independent transparency; binning 32×32, depth-sorted fragment lists, software blending; 3× slower than hardware alpha blending on average but beats Moment-based OIT.
   - https://arxiv.org/pdf/2405.13364 ; https://nadult.github.io/lucid/ ; https://github.com/nadult/lucid
   - Explicitly notes compute-raster work on AMD: works on Linux (RX 6700 XT) but Intel/Windows-AMD subgroup paths are slow/broken — platform fragility evidence.

6. **Schütz & Wimmer 2019** "Rendering Point Clouds with Compute Shaders" — custom framebuffer = SSBO with 64-bit atomicMin (40-bit depth + 24-bit color) + resolve pass; 1-pixel points 10× faster than fixed pipeline, but scales linearly with point size — the fixed pipeline wins above ~1 px. https://arxiv.org/abs/1908.02681

7. **Nanite — Karis et al. (Epic) SIGGRAPH 2021** "real-time rendering in Unreal" cluster software rasterizer — compute micro-poly rasterizer ~3× the hardware pipeline for small triangles; falls back to hardware for large. This is a *specialized* rasterizer, not ROP offload. https://advances.realtimerendering.com/s2021/index.htm

### Open-source implementations (community/primary)
8. **ComputeShader byteslither / Magnexis/compute-shader-software-rasterizer** — full compute-only pipeline in HLSL/D3D12: CS transform, setup+cull, tile binning (16×16), fine rasterize, packed 64-bit atomic depth+color, present; "Not in the sense of a production-ready universal replacement… a programmable compute rasterizer prototype." https://github.com/magnexis/compute-shader-software-rasterizer

9. **StarsX/ComputeRaster** — compute vertex processing, bin rasterization, tile (coarse) rasterization and pixel (fine) rasterization. https://github.com/StarsX/ComputeRaster

10. **nvpro-samples vk_lod_clusters** (`render_raster_clusters_sw.comp.glsl`) — production-quality NV Vulkan sample implementing Nanite-style **software rasterizer compute shader using 64-bit atomics** (`u64image2D`, `imageAtomicMax`), texture gradients, alpha test. Demonstrates that NRD-style software raster is a solved reference in the NV sample codebase. https://github.com/nvpro-samples/vk_lod_clusters/blob/main/shaders/render_raster_clusters_sw.comp.glsl

11. **OmarShehata/webgpu-compute-rasterizer** — tutorial compute rasterizer (WebGPU/WGSL) using `atomicMin`, per-component color atomics; explicit depth buffer guidance. https://github.com/OmarShehata/webgpu-compute-rasterizer/blob/main/how-to-build-a-compute-rasterizer.md

12. **Florian Köhler et al.** compute-shader sprite rendering (cited in LucidRaster paper).

### Commercial/industrial
13. **Epic Nanite** (as above) — shipped AAA use of compute rasterization (specialized, opaque micro-poly).
14. **AMD / NVIDIA driver engineering** — the modern engines run post/blur/lighting as compute (GPUOpen recommendations; DOOM uses compute heavy async). Not ROP offload.
15. **US20090073168A1 "Fragment shader bypass in a GPU"** (VIA Technologies) — patent for bypassing fragment shading in a unified shader unit in *hardware configuration*, diverting interpolated attributes straight to the pixel blender. This is hardware-side fragment-shader bypass, adjacent-but-not-compute idea. https://patents.google.com/patent/US20090073168A1/en

---

## 2. THE "ROP SATURATED → ASYNC COMPUTE" LITERATURE (the actual CDN-correct framing)

16. **AMD GPUOpen — "Leveraging Asynchronous Queues for Concurrent Execution"** — Async compute fills gaps while graphics staggers on ROP/geometry work; they explicitly say threads sharing a CU share GPRs/LDS and tasks that use all resources prevent overlap; overlap is only a win when bottlenecks are *complementary*.
   - https://gpuopen.com/learn/concurrent-execution-asynchronous-queues/
17. **AMD GPUOpen — "Maxing out GPU usage in nBodyGravity"** — The exact demonstration of the correct pattern: shadow-map passes are "very heavy on the rasterizer" and leave "most compute units idle" → run simulation compute *next to* rendering. 15% whole-GPU gain (Fury X), only because roughly half the gfx workload was compute anyway.
   - https://gpuopen.com/learn/maxing-out-gpu-usage-in-nbodygravity/
18. **AMD GDC 2019 "Efficient rendering in The Division 2"** — async compute must be limited by occupancy on consoles; "Async and Graphics queue may compete... Competing for execution resources… parallelize unalike workloads." Table classifies Shadow Mapping as "ROP heavy" — meaning *don't* put more ROP-like work async, put memory/shader work there.
   - https://gpuopen.com/download/gdc-2019-agtd1-efficient-rendering-in-the-division-2.pdf
19. **Khronos Vulkan tutorial / async_compute sample** — the FRAGMENT→COMPUTE→FRAGMENT barrier "perf cliff"; shadow pass (fixed-function bound) is the canonical compute-overlap target; and a whole-compute presentation path exists as an alternative. https://github.khronos.org/Vulkan-Site/samples/latest/samples/performance/async_compute/README.html
20. **AMD "Advanced Shader Programming on GCN" (GDC 2017)** — wave-launch costs, V$/K$/I$ dynamics, wave limiting, compute mixed with graphics on the SAME CU array; establishes that on GCN compute and graphics genuinely share CUs. https://gpuopen.com/download/GDC2017-Advanced-Shader-Programming-On-GCN.pdf

---

## 3. THE SPECIFIC SUBSYSTEM OVERHEADS (asked in the task)

### Dispatch/synchronization/barrier overhead
- Khronos tutorials + GPUOpen nBodyGravity: swapping compute in needs fences/queues; "make sure each command list is big enough. This will allow performance gains from async compute to make up for the cost… of stalling on fences." On the RX 550-class card the absolute work is small, so fence/barrier overhead is proportionally huge.
- Doom & Division 2 GDC: memory barriers (`glDispatchCompute` + barrier before draw) mandatory when compute writes feed graphics; kernel-launch/barrier cost is a real tax (OmarShehata tut, Khronos forums).

### Depth testing in compute
- Academic standard is packed **64-bit atomicMin** (depth<<32 | id) — CuRast, CUDARaster (alpha counters), LucidRaster, point-cloud rasterizer. Order-dependent depth needs per-pixel serialization = atomic hotspots on the contended address. GCN handles 16 atomics/line/cycle *per L2 slice*; but a visibility buffer for 1080p is 2M lines with ~64 total slices on Polaris12-scale chip → massive serialization risk at high depth complexity.

### Blending in compute
- CUDARaster: blend requires *ordering* — feed fragments to ROP in API order — done per-tile with sorted fragment lists (extra passes). LucidRaster: software blending is its whole point and costs 3× generic hardware alpha-blend. CuRast dodges it entirely ("blending... can be a defining aspect... slow down opaque processing"). Polaris12 does NOT expose blend atomics like some mobile HW; you must build per-pixel accumulators + spinlocks/atomics = poor.

### MSAA in compute
- CUDARaster supports MSAA (per-sample masks) and reports it as cost multiplier. Skia's graphite software MSAA uses a 64×64 LUT for *coverage* masks to keep per-sample cost low (cost per sample though is real). General theory: MSAA in software = Θ(n·k) coverage/depth regardless, and you lose hardware post-AA/CC. Deferred+per-sample notes: per-sample shading kills perf (GTX 660 deck: 3 ms lighting at per-sample). https://github.com/google/skia/blob/03f555cf/src/gpu/graphite/sparse_strips/MSAA_LUT.h ; https://unseel.com/cs/anti-aliasing-msaa ; Khronos MSAA-deferred threads.
- PowerVR guide adds: alpha-blended MSAA edges get processed *in software per sample* and are costly — even on hardware that has tile buffers. https://docs.imgtec.com/performance-guides/graphics-recommendations/html/topics/msaa-performance.html

### Cache behavior / bandwidth
- GCN fragment color/depth writes: RBE tile caches **bypass L2** and support DCC (delta color compression) + depth compression — Polaris whitepaper ("more efficient delta color compression" listed as a Polaris feature; ~1.2× effective bandwidth version), GCN whitepaper: "Once the pixels fragments in a tile have been shaded, they flow to the Render Back-Ends (RBEs)."
- Compute writes: L1(data V$ 16 KB/CU)→L2 (512 KB)→DRAM. Writes are write-back/absorbed by L2, but a *prenter* of the visibility buffer is DRAM-resident and rewritten per frame; then a resolve pass reads it back again → net bandwidth far higher than the RBE path.
- **Conclusion — memory bandwidth is NOT better in compute.** Hardware path: O(fragment) DCC'd RBE writes, no L2 involvement. Compute path: O(fragment) atomic RMW to a DRAM vis buffer + O(pixel) resolve read + O(pixel) dedup/interp. That's ≥2× the memory traffic.

### Async-compute-device reality (Polaris12-specific)
- Polaris has ACEs + graphics command processor dispatching simultaneously to the same shader array (Polaris whitepaper, wccftech slide deck for Polaris10: 4 ACEs + 2 HWS; Polaris12 architecturally same family). CU reservation exists (Polaris whitepaper: compute unit reservation, Quick Response Queue) → the *supported* offload mechanism is reservation/scheduling, not ROP bypass.
- Polaris whitepaper (Kanter): "Polaris emphasizes efficiency and focuses on improving control logic and fixed-function graphics hardware to make the best use of the available compute units." i.e., AMD already optimized where CU vs FF work belongs.