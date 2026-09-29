# IDEA I-07 — ASYNC OPTICAL FLOW FRAME GENERATION: PRIOR ART

Novelty audit. Sources ranked primary > community. The subject decomposes into (A) how optical-flow is computed on GPUs in software, (B) how it is accelerated in hardware, (C) how frame generation integrates & costs, (D) async-compute on GCN4.

## 1. HARDWARE OPTICAL FLOW (context — the "easy" path the RX550 does NOT have)
1. **NVIDIA Optical Flow Accelerator (NVOFA) + SDK** — dedicated fixed-function unit (Turing-lite / Ampere+); Vulkan extension `VK_NV_optical_flow` adds a dedicated **optical flow queue** (`VK_QUEUE_OPTICAL_FLOW_BIT_NV`), block-wise flow vectors, temporal hints, backward flow; FRUC reference (NvOFFRUC). Explicit hardware baseline to contrast software cost.
   - https://developer.nvidia.com/blog/accelerated-motion-processing-brought-to-vulkan-with-optical-flow-sdk/
   - https://docs.vulkan.org/spec/latest/chapters/VK_NV_optical_flow/optical_flow.html
2. **AMD (Polaris12): NO dedicated optical flow hardware.** Per AMD marketing: FMF/FSR3 does "all the calculations in the GPU's shaders using asynchronous compute capacity," no special block required — this is precisely the software/compute approach under audit.

## 2. AMD'S SHIPPED SOFTWARE OPTICAL FLOW + FRAME GENERATION (the decisive prior art)
3. **AMD Fluid Motion Frames (AFMF / AFMF2 / AFMF2.1)** — driver-level frame generation using optical flow, in AMD Adrenalin. AFMF2.1 supports Vulkan & OpenGL, Ryzen/Radeon 700/800M, RX 6000/7000 dGPUs. Compute-based (async compute), latency-reducing companion (Anti-Lag). Dependencies/notes in documents.
   - https://www.amd.com/en/products/software/adrenalin/afmf.html
   - PC Gamer writeup: FMF "does all the calculations in the GPU's shaders using asynchronous compute capacity"; performance "at least partially contingent on how much of the GPU's async compute is being used by the game"; latency trade-off. https://www.pcgamer.com/amd-fsr-3-and-fluid-motion-frames/
4. **AMD FidelityFX SDK — Optical Flow technique (1.1+) & Frame Interpolation** (GPUOpen; primary technical doc). This is the *open, reference* implementation of the exact idea:
   - Luminance pyramid (6 levels, ping-ponged), scene-change detection via 9-region histograms.
   - **Search pass:** per 8×8 block, 24×24 search area (16×16 = 256 SAD cases); **filter pass:** 3×3 median; **upscale pass** ×7 iterations.
   - Output: block-based flow `R16G16_SINT` at (W/8, H/8), plus `R32_UINT` scene-change resource.
   - Frame Interpolation: 9-stage pipeline (setup, estimate-interpolated-depth, game-MV field, inpainting pyramid, optical-flow field, disocclusion, interpolation, inpaint).
   - Async-compute: OF+FI can run on presentation queue OR async queue (`FFX_FSR3_ENABLE_ASYNC_WORKLOAD_SUPPORT`, `allowAsyncWorkloads`); async requires double-buffering and increases memory.
   - https://gpuopen.com/manuals/fidelityfx_sdk/techniques/optical-flow/ ; https://github.com/GPUOpen-LibrariesAndSDKs/FidelityFX-SDK/blob/fsr3-v3.0.4/docs/techniques/optical-flow.md ; https://github.com/GPUOpen-LibrariesAndSDKs/FidelityFX-SDK/blob/fsr3-v3.0.3/docs/techniques/frame-interpolation.md
5. **FSR 3 / FSR 3.1 — full shipped frame-generation pipeline** (AMD GPUOpen):
   - FSR3 = FSR2 upscaling + FFX Optical Flow + Frame Interpolation; game/engine-integration + swapchain pacing; usable on "AMD Radeon RX 5000 series and above / NVIDIA RTX 20 and above", SM6.2+.
   - Latency: "Interpolating a frame adds latency – this is by design." Base-fps floor: 60 recommended (FSR3) / 70 (AFMF); "below 60 fps not recommended… artifacts."
   - **Official measured overhead (SDK sample, async OFF, PIX):**
     - RX 5700 XT (RDNA1, GCN-family ISA): 1080p Native AA FG cost ~2.2 ms; 4K Native AA ~8.0 ms; Upscaling 4.7 ms. Even this 36-CU / far-faster-than-RX550 card eats **2.2–8 ms per generated frame**.
     - RX 6800 XT: 1080p NativeAA FG 1.0 ms; 4K 4.2 ms. RX 7900 XTX: 0.7–2.4 ms.
   - **Memory:** upscaling-only → +FG. 1080p: 169→267 MB (present queue); up to 984 MB @4K async.
   - Sources: https://gpuopen.com/fidelityfx-super-resolution-3/ ; https://gpuopen.com/download/AMD_FidelityFX_Super_Resolution_3-Overview_and_Integration.pdf ; https://gpuopen.com/news/fsr3-in-games-technical-details/
6. **Third-party measurement (community, secondary):** FSR3 FG ~doubled FPS; latency higher than DLSS3 FG; VRR/FreeSync issues; requires base >= ~60 fps; ~200 MB VRAM @1080p, ~500 MB @4K (TechPowerUp Forspoken review). Quality critiques: disocclusion artifacts, particles, ghosting. https://www.techpowerup.com/review/forspoken-fsr-3/ ; https://www.techspot.com/article/2747-amd-fsr-3-tech/

## 3. OPEN-SOURCE / COMMUNITY SOFTWARE FLOW + FRAME-GEN IMPLEMENTATIONS
7. **lsfg-vk (PancakeTAS)** — Vulkan layer porting Lossless Scaling frame generation (LSFG 3.1) to Linux; hooks swapchain, benchmarks FG; users report poor results on Intel iGPUs; feat. request for dual-GPU offload (bandwidth/latency overhead noted). Directly shows the "port existing FG into a Vulkan layer" pattern.
   - https://github.com/PancakeTAS/lsfg-vk ; https://lsfg-vk.dev/
8. **FidelityFX Fern (frame-frame) integration projects:**
   - `xXJSONDeruloXx/vklayer` — production-grade Vulkan layer doing FFX Frame Interpolation w/ optical flow (async queues, swapchain pacing), SM6.2+/GLSL4.50 requirements, wave ops, LDS.
9. **FFmpeg `vf_fruc_vulkan`** — frame rate up-conversion using **NVIDIA Vulkan optical flow extension** (hardware flow → interpolation). https://www.ffmpeg.org/doxygen/trunk/vf__fruc__vulkan_8c.html
10. **Academic / embedded SW-optical-flow on GPUs:**
    - CSCI1290 Brown (2011): dense pyramidal LK optical flow in GLSL; even early on — needs runtime-compiled, resolution-specific shaders to beat CPU; heavy.
    - Romera et al. 2023 (JRTIP) — "Optical flow algorithms optimized for speed, energy and accuracy on embedded GPUs" (TV-L1, Horn-Schunck, LK, CUDA) — complete picture of how many kernels/iterations SW flow needs on weak GPUs; shared-memory stencil optimization dominates. https://doi.org/10.1007/s11554-023-01288-6
    - Motion-estimation-as-compute precedent in video encoders: HEVC ME on Fermi GPUs (Khemiri et al. 2017, SAD/SSD, huge block cost), and `pasvulkan`'s compute motion-estimate shader (BeRo) showing the practical shape of a block-matching kernel (workgroup per block, search loops, half/quarter-pel refinement, SATD). Also `oximedia-gpu` (Rust/WGSL) block-match pipeline. These give the *per-block compute cost* curve this audit needs.

## 4. ASYNC COMPUTE ON GCN4 / POLARIS (enabler, prior art)
11. **AMD GPUOpen — concurrent execution / async queues.** Tasks on different queues share CUs, LDS, GPRs, cache("threads sharing the same CU will share GPRs and LDS"; "different queues share their caches… more cache thrashing"). Compute work depends on how much async headroom exists. https://gpuopen.com/learn/concurrent-execution-asynchronous-queues/
12. **AMD GPUOpen — nBodyGravity (2016):** canonical async-compute case study on GCN (Fury X); 15% win only because gfx workload was ~half compute. https://gpuopen.com/learn/maxing-out-gpu-usage-in-nbodygravity/
13. **The Division 2 (GDC 2019):** "Async compute is stalling the gfx pipe! … on consoles: limit async compute occupancy"; parallelizing only *unalike* workloads is rewarded. https://gpuopen.com/download/gdc-2019-agtd1-efficient-rendering-in-the-division-2.pdf
14. **AMD Polaris whitepaper (Kanter):** ACEs + HWS y mecanismos de scheduling
  descritos para la familia. La aplicabilidad a Polaris12, el número de ACEs y una
  eventual reserva de CUs por API Vulkan son `UNKNOWN`; no se usa como capacidad local.
15. **GCN microarch details (ChipsAndCheese):** 16KB V$/CU, L2 slices, RBE color/depth caches bypassing L2, L2 atomics (16/line/cycle). https://chipsandcheese.com/p/gcn-amds-gpu-architecture-modernization

## 5. NOVELTY TAG ASSESSMENT
The *specific formulation* — "run FidelityFX-style optical-flow + frame interpolation on
Polaris12's async compute path for the RX550" — is **KNOWN VARIANT**: the algorithmic
elements are public. The local number of ACEs, reservation mechanism, overlap and benefit
are `UNKNOWN`; no `CUs are free` claim is made.
