# IDEA I-01 — TBDR EMULATION ON IMR: PRIOR ART SURVEY

Novelty status per item tracked. Sources ranked: primary (vendor docs, papers, driver code, patents) > community.

**Idea under audit:** "Emulate tile-based deferred rendering (TBDR) on an immediate-mode renderer (IMR) — GPU Polaris12/RX550 — via software tiling: bin/filter geometry per screen tile, render per-tile with framebuffer transient/resident in on-chip cache, so color/depth bandwidth drops and the deferred pass reuses on-chip tiles."

**CRITICAL ARCHITECTURE PREMISE CHECK (per task instructions):**

> Can a *software* tile keep the framebuffer resident on Polaris12?

On GFX6–GFX8 the premise fails at the hardware boundary:
- **L2 (512 KB on Polaris12) is a shader cache only.** Render Backend (RB)/CB, Copy Engine and CP **bypass L2 and write directly to the memory controller** (Mesa-dev, Marek Olšák, ~2019: "GFX6-8: L2 used by shaders only. GFX9-10: everything"; GCN whitepaper; AMD GPUOpen RDNA presentation on cache hierarchy).
- Color/depth writes from the fixed-function path therefore **can never be L2-resident**. On-chip absorption of color/depth happens in the **RBE tile caches** (~16 KB color / ~4 KB depth per RBE tier) plus **DCC and HTILE** — already in hardware, already tiled, *before* the framebuffer is ever in DRAM.
- So "tile < L2 → tile stays in cache" is physically impossible for the CB/DB path. The only on-chip data that CAN be tile-resident is whatever the **shader/TC path** touches: textures, SSBOs, image load/store from compute. This re-frames the whole idea: the win (if any) lives in the *shader read path* (texture locality / compute image reuse), not in the CB write path.

---

## 1. DIRECT PRIOR ART — TILE-BASED PIPELINES (the core subject)

### Vendor / official
1. **Khronos Vulkan Guide — "Tile Based Rendering (TBR) Best Practices"** (primary).
   - Official guidance on render-pass design for TBR/IMR-agnostic code: merge passes, single subpass, loadOp/storeOp to avoid framebuffer round-trips, use depth and transient attachments.
   - **Directly relevant:** the guide's "use a render pass correctly" / "merge passes" / lazy clearing *is* the desktop-IMR-native version of what TBDR emulation tries to achieve — the IMR way is *compacting the render graph*, not tiling it.
   - https://docs.vulkan.org/guide/latest/tile_based_rendering_best_practices.html
2. **Apple — Metal Tile-Based Deferred Rendering TBDR docs** (primary, mobile glass).
   - Metal docs on tile shaders, imageblocks, raster-order groups; how memoryless render targets and `store_action_dont_care` keep GBuffers in on-chip tile storage (TBDR: no GBuffer DRAM traffic ever).
   - https://developer.apple.com/documentation/metal
3. **Imagination — "Does Tile-Based Deferred Rendering have a place in Desktop?" (Kristof Beets, 2025-11-18)** (primary, TBDR house).
   - Argues TBDR *does* have a desktop case (read/compact bandwidth, energy) — anchored in PowerVR/latest Imagination graphics; confirms the industry debate is **open** and **not settled**.
   - https://blog.imaginationtech.com/premium (exact slug: "does-tile-based-deferred-rendering-have-a-place-in-desktop")
4. **AMD — Vega "DSBR" (Draw Stream Binning Rasterizer)** (primary; also community teardown).
   - Vega added a primitive **binning pass and tile-based rasterization** enabling working-set reduction and geometry trimming — i.e., AMD's own existing attempt to add tile semantics to a GCN-family chip (Marek/GPUOpen discussion; NerdTechGasm "Vega Of Primitives & Pixels" walkthrough 2017-08).
   - https://gpuopen.com ; https://www.nerdtechgasm.com — DSBR bin buffer details in AMD Vega whitepaper slides.
5. **AMD Rafrae / radeonsi — "TC-compatible HTILE"** (mesa-dev, Marek Olšák, 2016-10-06) (primary, driver).
   - Patch enabling depth (HTILE) compression for texture cache consumers; canonical proof that **depth on GCN IS already compressed and tiled in the RB**, making a "software tile to compress depth" redundant.
   - https://lists.freedesktop.org/archives/mesa-dev/2016-October/
6. **AMD — DCC (Delta Color Compression) overview, GPUOpen 2016-03-14** (primary).
   - Render-backend-side delta color compression already reduces color bandwidth at the RBE; no shader software tiling needed to compress color writes. https://gpuopen.com/learn/dcc-overview/

### Open-source implementations
7. **freedreno/a6xx — binning pass + per-draw scissor optimization** (Mesa, Rob Clark; rework Karol Herbst) (primary, source).
   - Adreno 6xx tiled GPU: the driver adds a **binning pass** and optimizes it with **per-draw scissor** to skip bins (commit f079c00, 2020-05-13). Real, shipping proof that *driver-side software binning hardware exists in Mesa*. Reverse case: on Adreno the HW binner exists; here we ask the opposite (adding binning to an IMR).
   - https://gitlab.freedesktop.org/mesa/mesa/-/commit/f079c00...
8. **Doom3 / id Tech "bins"/partitioned framebuffer** (industry, gameplay-era) — software architectural tiling of the screen to limit working set; conceptually the oldest "software tiling on IMR" ancestor in engine practice.
9. **Vulkan Forward+ tutorial (per-tile light lists via compute)** — tiling of *light assignment*, not raster; the standard shipped "tile" pattern on desktop (both Khronos tutorial and many engine blog posts).
   - https://docs.vulkan.org/tutorial/latest/
10. **Mesa radeonsi — GCN "tile swizzle" modes** (Marek Olšák, Phoronix 2017-08-01) (primary).
    - Confirms GFX8 has **hardware tiling/swizzling of buffers/attachments** in the driver already → on Polaris12 *surfaces are already tiled in DRAM*, so a "software tile layout" would add nothing the driver doesn't already do.
    - https://www.phoronix.com/news/GCN-Tile-Swizzle

### Academic
11. **"A sort-based deferred shading architecture for decoupled sampling" (linked ACM paper, 2013)** — decoupled shading sorts *samples*; the visibility/shading decoupling idea that tile-based deferred systems formalize.
    - https://dl.acm.org/doi/… (decoupled sampling family; see also "Decoupled deferred shading", Clarberg et al., HPG 2013).
12. **Binning / bin-buffer literature for stream rasterizers (typical desktop work)**: bin-buffer and ordered-background rasterization papers (e.g., "The bin buffer" style) — the established academic answer for "geometry reuse across tiles", used by Hyundai/Imagination/Eden. For desktop, geometry binning is studied mostly to *reduce vertex re-shading*, not framebuffer residency.
13. **Visibility buffers (Robust-fitting / NV "A Life of a Triangle", Killzone)**: shading-from-vis-buffer requires re-fetch of per-pixel ids — the *deferred* part the tile would try to make on-chip. On an IMR this is a DRAM vis buffer + second pass; without tile storage it does **not** reduce bandwidth (it adds it).

---

## 2. THE "TILE-IN-L2" CLAIM, DESKTOP-SPECIFIC

- **NVIDIA Ampere-era "L2 residency" (CUDA access policy windows)** and academic "AutoScratch" (MLSys 2023) show that on *modern* parts the L2 can hold embedded data on request — but GCN4 has **no user-exposed L2 policy control** and its L2 is tiny (512 KB = ~0.5 small-format 720p tile, vs 16 MB for a 1080p color+depth pair).
- **"Cache-aware rendering / working-set"** academic work (GSPC, ICCAD 2013: LLC management for 3D scenes, 8 MB LLC) targets the *texture/vertex working set*, and demonstrates average ~13.1% LLC miss reduction — explicit evidence that the *shader/TC* path is where cache-resident wins live, not the RB path.
- Polaris12 therefore has **no mechanism** by which a software tile's color/depth stays on-chip. The RBE tile-cache+DCC is the only on-chip framebuffer mechanism, and it exists in hardware already.

---

## 3. PATENTS / OTHER (scanned, no blocking primary found in public search)

- Imagination prior art on binning/tile buffers (TBDR lineage) is broad; no dead blocking patent surfaced for "software tiling of an IMR for residency" in the searches run (patent search was NOT exhaustive — mark NOVELTY of any *specific* mechanism as UNKNOWN).

---

## 4. SYNTHESIS — WHERE I-01 ACTUALLY LANDS

| Sub-claim | Status | Evidence |
|---|---|---|
| "Software tiling reduces CB color/depth bandwidth on GFX8" | **CONTRADICTED BY PRIOR ART** | RBE bypasses L2; DCC/HTILE already compress writes (Olšák patches, GPUOpen) |
| "Tile stays resident in L2 on Polaris12" | **CONTRADICTED BY PRIOR ART** | GFX8 L2 = shader-only; CB/DB never write L2 (GCN whitepaper, Mesa-dev) |
| "Binning/scissor to trim per-tile geometry is new" | **KNOWN / KNOWN VARIANT** | a6xx binning pass + per-draw scissor (freedreno), Vega DSBR, iD-bins |
| "Shader-path tile locality (textures/compute image reuse) helps" | **RELATED PRIOR ART** | GSPC LLC caching, Forward+, DCC-on-read, GCN tile swizzle (already tiled) |
| "Software deferred tile-emulation wins like a TBDR" | **KNOWN VARIANT / part. NOVELTY UNKNOWN** | Metal/adreno are HW TBDRs; no public "IMR software-TBDR" product found after wide search → absence = UNKNOWN, not proof of novelty |
| Framebuffer residency via compute (image load/store re-read) | **PARTIALLY NOVEL as a Polaris-specific combo** | mechanisms exist (L2 caches compute images); residency benefit unmeasured on GFX8 (I-09 thread overlaps) |

**Novelty verdict (whole idea):** KNOWN VARIANT (technique-level recombination of WS: binning-pass, scissor binning, render-pass merging, DCC/HTILE, tiled lighting). The headline "emulate TBDR residency on IMR" was **not** found implemented anywhere in the searches, which is recorded as **NOVELTY UNKNOWN** (not "nobody does it"). The RB-bypass-L2 fact independently makes the *residency* version non-viable on Polaris12.