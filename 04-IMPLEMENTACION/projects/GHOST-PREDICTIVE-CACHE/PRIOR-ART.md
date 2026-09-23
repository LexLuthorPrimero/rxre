# IDEA I-06 — PREDICTIVE GHOST CACHE: PRIOR ART SURVEY

Novelty status per item tracked. Sources ranked: primary (papers, vendor docs, official SDKs) > community.

**Idea under audit:** "Predice qué texturas/tiles/mips necesitará la GPU en frames *futuros* (cámara + patrones de acceso) y caliéntalas en L2/VRAM antes de que se pidan (ghost cache predictivo), recortando la latencia de fetch en Polaris12."

**Conceptos obligatorios separados (regla de no-fusión):**
1. **GHOST CACHE GENÉRICO** — cache que describe accesos *pasados* (ghost lists: ARC, bypass, MLOP) y prefetchers hardware/software genéricos. NO es predictivo de cámara.
2. **GHOST CACHE PREDICTIVO** — predicción *hacia delante* (cámara/visibilidad) de qué entrará en cache y prefetch anticipado.

---

## CONCEPTO 1 — GHOST CACHE GENÉRICO (patrones de acceso + anti-pollution)

### Academic
1. **ARC — Megiddo & Modha, USENIX FAST'03** "ARC: A Self-Tuning, Low Overhead Replacement Cache"
   - The canonical "ghost" structure: cache keeps *metadata (tags) only* of recently evicted entries (ghost lists), used to adapt between recency and frequency without storing data.
   - https://www.usenix.org/legacy/events/fast03/tech/full_papers/megiddo/megiddo.pdf
   - Terminology note: "ghost cache" almost always means *this* (tag-only bookkeeping), NOT predictive prefetch. **Naming collision is the #1 prior-art trap for IDEA I-06.**

2. **Bypass Buffer — Jongmin Lee et al., IPDPS 2013** "Bypassing Dramatic Cache Pollution..."
   - Tag-only buffer side-by-side with LLC; useless (bypass) lines go through metadata to avoid pollution. Evidence that "ghost" mechanisms aim at **collusion avoidance**, not prediction.
   - https://hzhou.wordpress.ncsu.edu/files/2022/12/Bypassing_ipdps13.pdf

3. **MLOP — Doshi, Vezzu, Vadlamani (2020)** "Machine Learning Optimization for Prefetch"
   - CNN picks prefetch offset/distance; predicts *the next memory access* from past (locality). Application-side, prediction-from-history, not camera.
   - https://arxiv.org/abs/2009.00715
   - Status: **KNOWN VARIANT** of concept 1 (predicts *demand*, not *visibility*).

### Hardware/ISA (GPU)
4. **NVIDIA CUDA L2 Cache Control** — `cudaStreamSetAttribute` with L2 access policy window / persisting L2; `cudaDeviceSetLimit(cudaLimitPersistingL2CacheSize)`, `cudaCtxResetPersistingL2Cache`.
   - IMPORTANT (Polaris relevance): this L2 persistence/residency API is **Ampere+ (compute capability ≥ 8.0)**. GCN4/Polaris12 has **NO such control**. Any software "ghost cache" on Polaris12 cannot manage L2 residency via a sanctioned API.
   - https://docs.nvidia.com/cuda/cuda-c-programming-guide/04-special-topics/l2-cache-control.html
   - (CUDA 13 guide; general pointer)

5. **CUDA prefetch instructions** — `cudaMemPrefetchAsync()` (managed memory, driver-level TLB/page migration), `prefetch.global.L2` PTX → *data* prefetch into L2/registers. Again NVIDIA-specific; on AMD/RADV there is **no equivalent** exposed.

### Community/practice
6. **GitHub "ghostcache" — THU-HAS/ghostcache (CCS 2025)** — security ghost cache "highly-accurate and efficient conflict factor" — *this* is what "ghost cache" returns in keyword searches post-2025. Attacks conflict in L2 via tag-only replay.
   - https://github.com/THU-HAS/ghostcache
   - Status: KNOWN (concept 1, security flavor); MUST be excluded from a predictive-prefetch reading.
7. General software prefetch literature (Intel/ARM guides, `prefetch` intrinsics) — KNOWN; predicts CPU line access, not GPU texture working set.
   - e.g. Intel "Data Prefetching" guide: https://www.intel.com/content/www/us/en/docs/intrinsics-guide/ ; Arm prefetch: https://developer.arm.com/documentation/dui0802/g/... (placement of concept-1 family)

**Concept-1 verdict: KNOWN.** Ghost tags/lists that avoid pollution + prefetch-from-history are established (FAST'03→2020, HW prefetchers, CUDA L2). Nothing novel in describing *caches of past access patterns*. Applying it on GCN4 *for texture working sets* is at most a KNOWN VARIANT (and, without L2-residency control, an awkward fit).

---

## CONCEPTO 2 — GHOST CACHE PREDICTIVO (cámara/visibilidad → prefetch adelante)

### Academic — texture/cache prediction from camera
8. **Igehy, Eldridge, Proudfoot — "Prefetching in a Texture Cache Architecture" (Stanford, 1998/1999)**
   - The historical GOTO for *this* idea: a texture cache with **software prefetch** — the application/data predicts text; prefetches to hide latency (reported ~up to 30% gains on texture-bound workloads). Shows the *mechanism of "predict what texture you'll need"* is old and documented.
   - https://graphics.stanford.edu/papers/texture_prefetch/

9. **Hakura & Gupta — "The Design and Analysis of a Cache Architecture for Texture Mapping" (ISCA 1997)**
   - Standard texture cache analysis: small working sets (fits 16KB), tiling/blocking changes hit rate. Baseline for "texture working set fits/to cache" on GPUs.
   - https://graphics.stanford.edu/papers/texture_cache/

10. **Dumont, Pellacini, Kautz — "A Perceptually-Based Texture Caching Algorithm for Hardware-Accelerated Rendering" (EGRW 2003)**
    - The most direct prior art for a *predictive* camera: inserts a **"prediction camera" placed slightly in front of the view camera** to compute a `TextureIDMap` → predicts which mips/objects will be seen *next*; prefetches them into the texture cache, and evicts based on predicted access probability.
    - http://jamesferwerda.com/publications/r03_dumont01_egrw.pdf
    - Status: the *camera-forward prediction cam + prefetch* is **KNOWN and published 2003**. This is nearly exactly sub-claim 2 of I-06 at engine/cache level.
    - (Caveat: machine/infrastructure is old; but the *idea* is primary prior art.)

11. **WaSP — "Warp Scheduling to Mimic Prefetching in Graphics Workloads" (2024, arXiv 2404.06156)** — schedules warps so that *texture reads* issue early (prefetch-like) — GPU-level "simulate prefetch" inside the shading scheduler to hide texture latency. Indirect confirm: hiding texture latency is the *battle*; GPUs already do demand+software-prefetch tricks; the gap I-06 targets is "before the draw is even enqueued."
    - https://arxiv.org/abs/2404.06156

### Academic — visibility/working-set prediction (camera forward)
12. **NeuralPVS (2025, arXiv 2509.24677)** — learned *from-region* PVS; explicitly motivated by "prefetching/loading, streaming, and other applications where future visibility is needed." Academic state-of-the-art for *camera-predictive streaming*.
    - https://arxiv.org/pdf/2509.24677
    - Status: the *prediction* side of I-06 exists (learned PVS). Nothing about Polaris12 / no ghost-tag *cache* engineering.

13. **Prior PVS/workingset work** (conservative visibility → predicted set): Foster et al "Effective View Frustum..." (1997), "Streaming Rendering of Large Worlds with LSPS" — the concept "predict what is visible from a region and preload" is **KNOWN** since the 90s for huge-world streaming.

### Commercial/engines — camera-based texture streaming / virtual texturing
14. **Unreal Engine — texture streaming overview (Epic docs)**
    - Mip-level streaming with **camera-based** ideal mip computation (`r.Streaming.PoolSize`, hidden-primitive prefetch `r.Streaming.HiddenPrimitiveScale`, `bStreamingUseAsyncRequests`). The engine already *prefetches textures based on camera* → sub-claim 2 is shipped commercially.
    - https://dev.epicgames.com/documentation/en-us/unreal-engine/texture-streaming-overview
    - (You can tune how far "in front" of the camera to preload: `MipmapLevels`/`SamplingRegion`.)

15. **Unreal Engine — Streaming Virtual Texturing** (Epic docs)
    - **Explicit key quote (reactive, not predictive)**: "VT streaming is reactive by nature, meaning that the CPU doesn't know it needs to load a given VT tile until after it has already been required by a rendered frame."
    - https://dev.epicgames.com/documentation/unreal-engine/streaming-virtual-texturing-in-unreal-engine
    - Status: proves that **current shipped VTM trusts the *feedback from the previous frame*** (reactive). This is the exact gap I-06's *predictive* side claims to fill (predict-then-load vs feedback-load).

16. **id Tech 5 — van Waveren, "id Tech 5 Challenges: From Virtual Texture to Virtual Worlds" / SIGGRAPH**
    - VT feedback buffer + page upload; mip pyramid; collisions/thrash handling on a *scaled* PC facing limited page cache. Empirical bounds on "how much further you can prefetch" — the *CG-IT-5 lacks PC main-memory prediction*; thrash documented.
    - https://mrl.cs.vsb.cz/people/gaura/agu/05-JP_id_Tech_5_Challenges.pdf

17. **Unity — Mipmap Streaming (`StreamingController.SetPreloading`)** — allows preloading a target *mip* for a target *camera position*, i.e. explicit camera-forward prefetch API. KNOWN + shipped.
    - https://docs.unity.cn/2020.3/Documentation/Manual/TextureStreaming-API.html

### Driver/hardware — what Polaris12 (GCN4) actually supports (KEEP against sub-claim 3)
18. **amdgpu / RADV sparse-residency (Vulkan `sparseBinding`) on Polaris** — the *only* sanctioned way to "reserve texture pages ahead"; but PRT (page-demand paging) on Polaris has **long-standing userland breakage**.
    - Community: https://github.com/CachyOS/linux-cachyos/issues/930 (sparse/PRT crashes on Polaris/RX590 class)
    - Driver fix stream (AMD mailing list, 2026): https://lists.freedesktop.org/archives/amd-gfx/2026-March/141566.html
    - Status: mechanism exists but **fragile on GCN4** → a predictive-prefetch *service* would trip over PRT instability.

19. **radeonsi/RADV — no prefetch/residency API for texture L1/L2 on GCN4.** RADV exposes `VK_KHR_external_memory_LOCAL`/DRM fds + sparse, but no cache-management hints (SDK/control for texture read into L2 ahead of use). CUDA-parity L2 window DOES NOT exist on RDNA≤3, certainly not GCN4.

### Consoles (accelerating the "reactive" gap differently)
20. **PS5 Kraken / Xbox BCpack hardware decompression + DirectStorage** — next-gen IO *removes* the disk-latency motivation for prediction by making reactive loads so fast they look predictive (~GB/s decompression off CPUs). This is the counter-position: you don't need a *predictive ghost cache* if *reactive* disk→VRAM is near-instant.
    - https://www.digitaltrends.com/computing/consoles-still-have-advantage-hurting-pc-gaming (Kraken ≈ 9 Zen2 cores of decompression)
    - https://learn.microsoft.com/en-us/gaming/gdk/... (DirectStorage / BCpack, Xbox Game Dev Kit)

---

## 6. NEGATIVE / NO-CLAIM SECTION (per FASE R-3 "declara solo lo que no encontré")

Searched (list of search routes): `GPU texture prefetch prediction camera`, `ghost cache texture prefetcher GPU`, `predictive texture paging camera motion`, `UE VT reactive by nature`, `idTech5 feedback buffer page upload`, `CUDA L2 access policy window`, `RADV texture cache control GCN4`, `amdgpu PRT sparse Polaris`, `AMD texture cache prefetch`, `NeuralPVS prefetch`, `PC virtual texturing prediction forward`, `L2 residency programming GPU AMD`, `software texture tile prefetch next frame`.
**Not found (no primary source):** *any* shipped or published system that forms a **tag-level 'ghost cache' for texture tiles predicting *camera-forward* working sets on a desktop GCN4 IMR**, nor any firmware/driver that manages L2 residency of a predicted texture working set on Polaris12. The *prediction* is KNOWN (Dumont, UE preload, idTech feedback, NeuralPVS); the *cache-mechanism* (ghost tags on the GPU texture L1/L2 + forward prediction) is absent in primary sources → **POTENTIALLY NOVEL as an academic sub-claim**, but **hardware-unsupported** on Polaris12 (no L2 control, PRT fragile).

**CONTRADICTED-BY-HW:** sub-claim "wrap Polaris12 in a predictive *hardware-cache* ghost layer" — GCN4 has no L2/texture-cache residency or prefetch control exposed; CUDA-style L2 windows are Ampere+; PRT sparse is unstable on Polaris (2026 M-L thread). So the *hardware manifestation* is NOT feasible; only the *software* (engine/driver-adjacent) embodiment survives.

---

## 7. VERDICT SUMMARY (by concept)

| Sub-claim | Novelty | Feasibility on Polaris12 |
|---|---|---|
| Concept 1: ghost/tag caches (past patterns) | KNOWN | No sanctioned L2 residency → weak fit |
| Concept 2: camera-forward prediction + prefetch | KNOWN VARIANT (engines: UE/Unity/id; academic: Dumont2003, NeuralPVS) | Partly: engine-level already possible; *new* = GPU-side tag/prefetch service |
| Software predictive "ghost" service (predict → sparse/resident/copy-Ahead) | POTENTIALLY NOVEL (no primary source found on GCN4 desktop) | PARTIALLY FEASIBLE (userland; PRT risk) |
| Hardware-cache ghost layer on GCN4 | — | **CONTRADICTED** (no HW support) |