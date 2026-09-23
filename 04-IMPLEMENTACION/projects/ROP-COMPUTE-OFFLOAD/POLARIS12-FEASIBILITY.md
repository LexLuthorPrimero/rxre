# IDEA I-04 — ROP OFFLOAD TO COMPUTE: POLARIS12 FEASIBILITY ANALYSIS

Target: RX 550, Polaris 12 / Lexa.
**Confirmed specs (primary/aggregate sources: AMD RX 550 page, TechPowerUp DB, VideoCardz):**
- 8 CUs × 64 shaders = **512 stream processors**; 32 TMUs; **16 ROPs** (2 render backends)
- L2 = **512 KB**; L1D (V$) = **16 KB/CU**; scalar (K$) 16 KB/4CUs; I$ 32 KB/4CUs
- 128-bit GDDR5 @ 7 Gbps → **~112 GB/s**; boost ~1183 MHz → ~1.2 TFLOPs FP32
- 4th-gen GCN, ACEs + HWS + Quick Response Queue + **compute unit reservation** (Polaris whitepaper)
- Sources: https://www.amd.com/en/products/graphics/radeon-rx-550 ; https://www.techpowerup.com/gpu-specs/radeon-rx-550.c2947 ; https://videocardz.com/68830/amd-launches-radeon-rx-550-for-79-usd ; https://sysrqmts.com/en/gpus/amd/polaris/radeon-rx-550

---

## 1. NUMERIC THROUGHPUT RELATIONSHIP (the required analysis)

**Fragment throughput vs CU throughput at 1183 MHz:**
- Pixel/fragment shading: 512 SP × 1183 MHz ≈ 1.21 TFLOPs. A "full" fragment shader at ~50 ALU ops + ~4 texture fetches: the CUs are the *first* thing to bottleneck.
- ROP fill: 16 ROP × 1183 MHz ≈ **18.9 Gpix/s** (2× rotate for depth+MSAA variants: 16 ROPs × 4 samples threads…). At 1080p (2.07 Mpix): hardware path = ~9,000 fps of pure fill. ROPs are effectively *never* the primitive bottleneck on a chip this fill, outside pathological full-screen trivially-shaded draws.
- Rasterizer feed: on GCN, one rasterizer per ~16 CUs; Polaris12 has 1 rasterizer. Pixel waves launch at 1 wave/4 cycles top; each CU needs 4+ resident waves to hide latency (AMD GDC17). With 8 CUs the entire GPU can hold ~32 resident pixel waves → the machine saturates fast and the rasterizer *stalls* on shading, not on ROPs.
- **Ratio check:** CUs(512 shaders) : ROPs(16) = 32 SP per ROP. High-end Tahiti: 2048:32 = 64 SP/ROP. Vega: 8-16 SP/ROP (as loads shrank per ROP). Polaris12 therefore sits at the *shader-heavy, ROP-light* end — exactly backwards for "ROPs saturated, CUs free." If ROPs ever approach saturation, the CUs are already at full tilt, not idle.

**CU-availability conclusion:** "ROPs saturated + CUs free = compute faster" is **contradicted for Polaris12**. The scenario requires either (a) trivial pixel-shaders at huge overdraw (RBE-bound) — where the CUs *would* be cheap — or (b) genuinely complementary workloads (the AMD-recommended async-compute use). In case (a) the whole game scene is trivial and a compute rasterizer still pays 2–10× (CuRast/Laine numbers); in case (b) the hardware rx for that is async compute + CU reservation, which Polaris12 already exposes natively.

## 2. OVERHEAD BREAKDOWN IF YOU DID IT IN COMPUTE (values scaled from known references)

| Overhead | CUDARaster (academic, top GPUs) | Polaris12 projection |
|---|---|---|
| Triangle setup + clipped + snapping | ~160 instr/triangle coverage calc ≈ 40% of hardware rasterizer throughput | worse: fewer SIMDs, no dedicated rasterizer |
| Attribute fetching + interpolation | biggest software weakness (plane equations, 64-bit arithmetic for >2048² viewports) | 1.2 TFLOP pool, divided by 8 CUs |
| Depth via 64-bit atomicMin | fine-grained but needs *L2 atomics* on DRAM layout | 512 KB L2, 16 atomic/line/cycle; 1080p vis buffer = 2M+ contested lines → serialization |
| Blending (opaque-safe, ordered) | per-tile sorted fragment lists; extra passes | +50–100% more passes, each a full dispatch+barrier |
| MSAA | per-sample masks + resolve; ~Θ(n·k) | software depth at sample rate; L2/DRAM pressure ×k |
| Dispatch + fence | "make sure each command list is big enough…stalling on fences" (AMD) | 8 CU chip → tiny command lists, proportionally huge sync cost |

References: https://research.nvidia.com/sites/default/files/pubs/2011-08_High-Performance-Software-Rasterization/laine2011hpg_paper.pdf ; https://aarxiv.org/… (CuRast); https://nadult.github.io/lucid/ ; https://gpuopen.com/download/GDC2017-Advanced-Shader-Programming-On-GCN.pdf

## 3. CACHE / BANDWIDTH EXAMINATION

- Fragment path today: pixel shader export (per-quad) → RBE color cache (16 KB tier) + depth cache (4 KB) → DCC/depth-compression → DRAM, L2 bypass. Polaris adds improved DCC (whitepaper). That is the leanest write path on-die.
- If you route visibility through compute: per-fragment 64-bit atomicMin write L1→L2→DRAM (vis buffer resident in DRAM), then a shade-from-vis buffer read, then a resolve/interp pass. Traffic ≈ fragment writes + per-pixel reads + per-pixel dedup ≥ **2–3× the framebuffer traffic of the RBE path**, plus total loss of DCC/HTILE benefits for the target (HTILE/hi-Z useless since nothing uses HiZ hardware; you'd have to emulate the coarse reject in software).
- L2 is 512 KB = ~0.5 frames of a 1080p 32-bit depth+color pair (≈16 MB). No meaningful tile-residency; every compute pass thrashes L2.

**Verdict on the specific question "is memory bandwidth actually better?": No — it is objectively worse** (compute path adds an intermediate buffer + resolve; RBE path is a single compressed write).

## 4. MSAA, DEPTH, BLEND IN COMPUTE vs POLARIS12 HARDWARE

- Blend: RBE alpha-blend is fire-and-forget, in hardware, with DCC. Compute blend at 64-bit atomic footprint per pixel on 2M lines on 8 CUs — the exact hotspot the RBE design exists to avoid.
- Deferred-style "shade from vis buffer": on RX 550 the vis buffer route also loses alpha-tested/coarse geometry savings that FreePipe/CuRast exploit *only* at pixel-sized triangles, which aren't what 1080p console-style scenes look like.

## 5. THE SUPPORTED OFFLOAD MECHANISM ALREADY EXISTS

- Polaris whitepaper documents **CU reservation** and **Quick Response Queue**: an ACE compute queue can reserve specific CUs and get prioritized — the sanctioned way to co-schedule compute wiggle work next to ROP/geometry-heavy passes. It does not move ROP work into compute; it moves *independent compute* next to ROP-bound work.
- GPUOpen guidance (nBodyGravity, async queues, Division2): populate the compute gap with *memory-hit or ALU work with no dependency*, not with more visibility work.

## 6. FEASIBILITY VERDICT

- Technically implementable (references existing, APIs VLK12/DX12 expose both compute + fixed path), but **not beneficial on Polaris12**:
  1. CU/ROP balance is wrong (32 SP/ROP).
  2. Every published comparison (Laine 2–8×; CuRast 10× worse on game-like scenes; LucidRaster 3× on blend) puts software rasterization **slower** than hardware on typical-geometry scenes.
  3. The premise of "free CUs" is contradicted: ROP busy → CUs already delivered the fragments.
  4. Bandwidth is strictly worse (L1→L2→vis→resolve vs RBE bypass + DCC).
  5. Async-compute + CU reservation already provides the legitimately *winning* version of the same instinct at ~15% (AMD nBody, Fury X; bigger on polaris-class with complementary workloads).
- Possible narrow *novel experimental* value: a pure-compute rasterizer on Polaris12 as a **measurement rig** for "how bad is L2-atomic visibility on GCN4-low-end" — but as a performance feature on this chip it is classified **CONTRADICTED BY PRIOR ART**. As research the idea is KNOWN VARIANT (well-established technique, novel only in target-hardware platforming).