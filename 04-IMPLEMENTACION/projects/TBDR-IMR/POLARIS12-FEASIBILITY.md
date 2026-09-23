# IDEA I-01 — TBDR EMULATION ON IMR: POLARIS12 FEASIBILITY ANALYSIS

Target: RX 550, Polaris12/GFX8 (PCI 1002:699f).
**Confirmed specs (verified locally + aggregate primary sources):**
- 8 CUs × 64 shaders = **512 SP**; 16 ROPs (2 RBs); 32 TMUs; 1 GB DDR5 128-bit (~112 GB/s)
- **L2 = 512 KB** (2 slices × 256 KB), 16-way, 64 B lines, write-back/write-allocate; V$ = 16 KB/CU; K$ 16 KB/4 CUs; I$ 32 KB/4 CUs
- **L2 clients on GFX8 = shaders ONLY.** RB, Copy Engine, CP bypass L2 and go directly to the memory controller (GCN whitepaper §cache hierarchy; Mesa-dev 2019: "GFX6-8: L2 used by shaders only. GFX9-10: used by everything"; GPUOpen RDNA presentation on cache evolution)
- Fixed-function framebuffer path already tiled in HW: RBE tile color cache (~16 KB tier) + depth cache (~4 KB) + **DCC** (delta color compression) + **HTILE** in the RB (radeonsi TC-compatible HTILE, Marek Olšák 2016; GPUOpen DCC overview 2016).

---

## 1. THE CENTRAL QUESTION: WHAT WOULD A SOFTWARE TILE HAVE TO AVOID?

For a software tile to be a net win it must avoid sending color/depth to VRAM. On GFX8:

- **CB/DB writes bypass L2 entirely.** The RBE palette (color/depth tile caches + DCC/HTILE) is the only on-die framebuffer absorption; it is *already* tile-everything in fixed function.
- ⇒ A software "tile" that routes color/depth through the same CB/DB path automatically inherits DCC/HTILE+tile cache — there is nothing left for the tile to add on the write side.
- ⇒ A software tile that routes color/depth through the **shader/store path** (compute image store) would LOSE DCC/HTILE and the RBE tile cache (compute writes go V$→L2→DRAM with no RBE compression). That is strictly *worse* bandwidth, and equals optical-bandwidth of idea I-04 (compute rasterization), already **CONTRADICTED** for Polaris12 scenes.

## 2. IN THE OTHER DIRECTION: THE SHADER PATH (where cache residency CAN exist)

The only on-chip reuse I-01 could hope to engineer on GFX8 is in the **TC/shader path**:
- Textures, SSBOs, and compute image load/store data live in V$/L2 (16 KB/CU + 512 KB shared).
- If a deferred pass re-reads a G-buffer written *as a texture* (or a compute-written image), L2 can absorb **repeated reads** of the same tiles. This is the GSPC/LLC proposition (ICC) and the natural home for "L2-resident" claims — **overlapping I-09**.
- Quantify: 512 KB L2 / 1080p 8-bpc RGBA8 (≈8.3 MB) ≈ **6% of a frame**. Even a 320×180 internal target (230 KB) uses ~45% of L2. L2 must simultaneously hold textures/geometry working set; a "resident framebuffer tile" competes with everything else the shaders are sampling.

## 3. NUMERIC FEASIBILITY SWEEP (documentary estimates, no run)

| Approach | CB/DB write path | L2 involvement | Extra passes | Net vs IMR baseline |
|---|---|---|---|---|
| HW path today (RBE+DCC+HTILE) | compressed, tiled | none (bypass) | 0 | reference |
| SW tiling → CB/DB (scissor bins) | compressed, tiled (same HW) | none | +binning pass, +draw overhead | ≈ same writes; usually worse (overhead) |
| SW tiling → compute stores | uncompressed loss of DCC/HTILE | yes (V$→L2) | +store, +copyback, +resolve | worse bandwidth (I-04 result) |
| Tile-sorted **texture stream** (per-tile texture fetch) | unchanged | yes (read locality) | +binning/predication | the only direction with potential read-win; unproven on 8 CUs |

Per-pixel math at 1080p: full RGB-plane writes ≈ 8.3 MB/frame; DCC on flat/similar pixels typically cuts this several× at the RBE (GPUOpen claims up to ~2:1+ on scenes; exact ≤ depends on content). HTILE coarse depth rejects back-face/covered depth already in HW. The fixed path is *already* approximating a TBDR's write savings **at the RBE**, without any driver tiling.

## 4. COST / OVERHEADS OF A SOFTWARE TILER ON POLARIS12 (scaled from references)

- Binning pass on the CPU or a mesh-shader/compute pass: must parse the whole scene graph or triangle stream to append IDs into per-tile lists → extra dispatches, barriers, VRAM lists (bin buffers), then per-tile re-issue. On 8 CUs the fixed-cost of dispatch+fence (AMD GDC17: "make sure each command list is big enough") is proportionally huge relative to a 1080p scene.
- Driver-side implementation (Mesa radeonsi/RADV) is *already* a fully-tiled backend (GCN tile swizzle, DCC, HTILE). Adding *a second* software binning layer on top of the driver's own tiling = negative value.
- The legitimate kernel for such effort (like Adreno's binning pass) exists because those GPUs have **hardware binning + on-chip tile storage**, neither of which Polaris12 has; without tile storage the "deferred-in-L2" half of TBDR is void.

## 5. FEASIBILITY VERDICT

- **Technically implementable** (any IMR can scissor-bin and re-draw) but **structurally not beneficial on Polaris12**:
  1. CB/DB bypass L2 → framebuffer can never be L2-resident; the RBE tile cache+DCC/HTILE already does everything a "tile" would buy on the write side.
  2. Routing tiles through compute loses DCC/HTILE and forces L2 round-trips → strictly worse (I-04 precedent).
  3. The only cache-resident win available is **shader-path read locality**, which is a distinct idea (I-09) and has no dependency on TBDR emulation.
  4. 512 KB L2 << any meaningful framebuffer; the entire premise "tile fits in cache" has no cache to fit into on this part.
- Classification: **CONTRADICTED BY PRIOR ART (residency half); KNOWN VARIANT (binning/render-pass-merge half)**. As a *performance feature* on RX 550: **not viable**. As a *measurement exercise* (to prove the RBE-vs-L2 split empirically) it has some documentary/research utility, but that measurement belongs to I-09 instrumenting instead.