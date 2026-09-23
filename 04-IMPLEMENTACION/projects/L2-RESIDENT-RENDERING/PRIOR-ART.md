# IDEA I-09 — L2-RESIDENT INTERNAL RESOLUTION: PRIOR ART SURVEY

Novelty status per item tracked. Sources ranked: primary (vendor docs, papers, source) > community.

**Idea under audit:** "Render at a reduced internal resolution chosen so the whole framebuffer (or its hot tiles) fits in the L2 cache; keep it resident across passes (deferred re-read, effects) so DRAM bandwidth for color/depth drops to near zero."

**CRITICAL ARCHITECTURE PREMISE CHECK (per task instructions):**

> Can a render target be "L2-resident" on Polaris12?

- GFX6–GFX8 L2 = **shader cache only**. Render Backend (CB/DB), Copy Engine, Command Processor **bypass L2** and write directly to the memory controller (Mesa-dev, Marek Olšák ~2019: "GFX6-8: L2 used by shaders only. GFX9-10: used by everything"; GCN whitepaper §cache; GPUOpen RDNA cache-hierarchy slides).
- ➡ A framebuffer rendered through the fixed-function CB/DB path **never enters L2** — "resident in L2" is physically impossible for render-pass attachments on GFX8. The only L2-resident data class is **shader/compute memory traffic** (textures, SSBOs, image load/store).
- **L2 = 512 KB** on Polaris12. Even the most optimistic internal target (e.g., 320×180 RGBA8 = 230 KB) is ~45% of the entire L2 and must share it with every texture/vertex the pass samples. The "chosen resolution" premise collapses to "a sub-frame that fits in 1/2 of a 2010-era last-level cache."

---

## 1. DIRECT PRIOR ART — CACHE-RESIDENT / MMU RESIDENT RENDERING

### Vendor (primary)
1. **NVIDIA CUDA L2 Cache Control — Access Policy Windows / persisting L2 (Ampere, CC 8.0+)** (primary).
   - Exposes L2 persistence + set-aside: a subset of L2 can be *carved out* to hold specific data across kernels. This is the flagship "cache residency" precedent — but it is a **CUDA VM feature for data**, targets L2 ≥ 40 MB parts, and is not a framebuffer-abstraction. GCN4 has no equivalent.
   - https://docs.nvidia.com/cuda/cuda-c-programming-guide/index.html#l2-cache-control
2. **AMD — none. No L2 residency API exists for GCN/Polaris.** Polaris12 even lacks an exposed L2 partitioning knob in userspace (hardware/firmware-only). L2 hit/miss counters are not exposed to radeontop; RCP lists `L2CacheHit` counters per hardware block but availability on GFX8/SPM is unconfirmed. → the *measurement* half of I-09 is gated on tooling that may not exist for this chip.
3. **AMD GPUOpen — DCC overview (2016-03-14); radeonsi TC-compatible HTILE (Mesa-dev, Oct 2016)**.
   - The real "keep it small / keep it compressed" mechanism AMD ships: delta-color compression at the RBE + depth compression. These reduce DRAM color/depth traffic *in hardware* for every render, without any cache-residency trick. If your goal is "less DRAM traffic for the framebuffer," DCC/HTILE already do it; cache-residency adds nothing on the write side.
   - https://gpuopen.com/learn/dcc-overview/ ; https://lists.freedesktop.org/archives/mesa-dev/2016-October/

### Academic
4. **GSPC — "Efficient management of last-level caches in graphics processors for 3D scene rendering workloads" (ACM/IEEE, ICCAD 2013)** (primary, peer-reviewed).
   - Manages an **8 MB LLC** for 3D-render workloads; **avg 13.1% LLC miss reduction, up to 18.2% speedup**. Directly relevant: (a) it targets the *texture/vertex working set*, not framebuffer color; (b) its LLC is 8 MB — 16× Polaris12's L2; (c) it proves cache-resident *shader-path* data is where wins live, which is exactly the shader-path half of I-09, not the CB half.
   - https://dl.acm.org/doi/10.1145/2463209.2488828 (ICCAD 2013)
5. **AutoScratch (MLSys 2023)** (primary, peer-reviewed) — L2 residency controls on **NVIDIA Ampere A100/A40** for scratchpad caching; measures set-aside effect on bandwidth-bound kernels. Ampere-era, ≥40 MB L2, VM-managed persistence. Same conclusion: residency is a *data* (compute) feature on modern big-L2 parts; nothing analogous on 2016 GCN4.
   - https://proceedings.mlsys.org/
6. **"Cache-aware/working-set rendering" line** (pre-GSPC; e.g., tile/working-set analyses of texture accesses) — general support that *read* locality is where cache management helps in 3D, consistent with GSPC; none propose framebuffer-L2 residency because framebuffer writes on their target HW (IMR desktop) don't route through central cache.

### Hardware-side precedent
7. **TBDR mobile parts (Imagination PowerVR, Apple A-series, Adreno)**: on-chip tile stores *are* "framebuffer resident on die" — but the mechanism is a dedicated tile memory plus RBE-managed transient attachments, **not the L2**. On GFX8 the only candidate on-die framebuffer storage is the RBE tile cache + DCC (hardware, already used). TBDR comparison (see I-01) makes clear GFX8 has no tile-store, so "residency" can only be shader-path.

## 2. PRIOR ART FOR THE SURVIVING SUB-CLAIM (compute path re-read)
- **Vulkan image-store everything** (I-04 audit): compute image store → V$/L2→DRAM, no DCC/HTILE. Re-reading that image in another compute/fragment pass hits L2 only if the working set fits and is not evicted. This is a *data-locality* claim that generic cache block replacement studies (GSPC, NVIDIA persistence docs) already cover; the **Polaris-specific numbers** (512 KB, no eviction control, no counter) are the unknown.
- **No found prior art** implementing "framebuffer resident in L2 on AMD GCN"; the wide-search absence is recorded as **NOVELTY UNKNOWN** (not "nobody does it").

---

## 3. SYNTHESIS — WHERE I-09 ACTUALLY LANDS

| Sub-claim | Status | Evidence |
|---|---|---|
| "Render-pass attachment lives in L2 on Polaris12" | **CONTRADICTED BY PRIOR ART** | CB/DB bypass L2 on GFX8 (GCN whitepaper; Mesa-dev 2019) |
| "Lower internal res → frame fits L2" | **CONTRADICTED/IMPOSSIBLE** on CB path; viable only via compute path at ≤230 KB = 45% of L2 | 512 KB L2 spec; working-set contention |
| "Compute-written internal target re-read multiple times uses L2" | **RELATED PRIOR ART / PARTIALLY NOVEL as a GCN4 combo** | GSPC (LLC caching of data), NVIDIA L2 persistence, AutoScratch; no GCN4-specific work found |
| "DCC/HTILE already minimize framebuffer DRAM traffic" | **KNOWN** | GPUOpen DCC, radeonsi HTILE |
| "L2 residency measurable on Polaris12" | **UNKNOWN/BLOCKED** | no L2 counters in radeontop; RCP `L2CacheHit` unconfirmed on GFX8 |

**Novelty verdict (whole idea):** CONTRADICTED BY PRIOR ART for the headline (framebuffer-in-L2 on
GFX8). The compute-path sub-claim is PARTIALLY NOVEL as a *Polaris-specific* experiment but sits
on well-documented general mechanisms; its novelty is target-hardware platforming, not mechanism.