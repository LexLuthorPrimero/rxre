# IDEA I-09 — L2-RESIDENT INTERNAL RESOLUTION: POLARIS12 FEASIBILITY ANALYSIS

Target: RX 550, Polaris12/GFX8 (PCI 1002:699f).
**Confirmed specs (verified locally + primary sources):**
- 8 CUs × 64 shaders = **512 SP**; 16 ROPs / 2 RBs; 32 TMUs; 128-bit GDDR5 (~112 GB/s)
- **L2 = 512 KB** (2 slices × 256 KB), 16-way, 64 B lines, write-back/write-allocate; V$ = 16 KB/CU
- **GFX6–8: L2 is used by shaders only.** CB/DB, Copy Engine, CP bypass L2 (GCN whitepaper; Mesa-dev 2019; GPUOpen RDNA cache-hierarchy slides)
- DCC (delta color) + HTILE (depth) compression implemented in the RB/RBE; textures and compute images use V$→L2→DRAM.
- **No userspace L2 residency/partitioning control on GCN4.** L2 hit/miss not exposed to radeontop; RCP has `L2CacheHit` counters by block but GFX8/SPM availability unconfirmed.

---

## 1. THE HEADLINE FAILS AT THE HARDWARE BOUNDARY

"Make the internal-resolution framebuffer resident in L2" cannot work on the fixed-function path:

- **CB/DB writes never enter L2** on GFX8. A color/depth render-pass attachment is written by the RBE (DCC/HTILE compressed) directly to the memory controller. Whether the internal resolution is 1080p or 240×135, **zero bytes of the framebuffer go through L2**. There is no residency to optimize — the mechanism is absent, not undersized.
- Even reading the target back (as a texture in a later pass) is a **shader-path read** that must come from DRAM (DCC-decompressed at the texture unit) because it was never cached on the write side.
- ⇒ The premise behind "choose a resolution that fits L2" (small target = cached) is **void on the CB path**: the cache-on-die that the idea tries to exploit simply does not exist for that path.

## 2. THE ONLY VIABLE ROUTE IS THE SHADER/COMPUTE PATH

A target **written by compute** (image store / UAV) does go V$→L2→DRAM, so L2 *can* absorb repeated shader reads of it *if* it stays resident:

- Max "resident" RT: a 320×180 RGBA8 target = **230 KB = 45% of the 512 KB L2**. Even 480×270 RGBA8 = 518 KB = **exceeds the entire L2**.
- That 45% competes with every texture/flatten/geometry stream the pass samples. GFX8 L2 replacement is ordinary LRU-ish; there is **no set-aside**, no pinning, no way to protect the target from eviction.
- V$ 16 KB/CU further splits data across CUs (not a shared pool). Working set behavior is workload-dependent; no instruction-level control.
- Compute path **loses DCC/HTILE**: raw stores to DRAM, no RBE compression. Whatever write-bandwidth the RBE+HTILE saves on the fixed path (typically ≥2:1 on similar content per GPUOpen) is forfeited to gain a *fragile* read-side residency that shares a tiny pool.
- Multiple passes that each *re-read* the same compute-written tile are the one plausible win (repeat-read locality). That is the classic L2-locality regime — but on GCN4, with no counter, and with a target that must stay under ~45% of a 1 MB-class cache shared with the real workload, the expected value is low.

## 3. NUMERIC SWEEP (documentary estimates)

| Approach | Target size (RGBA8) | Fits L2? | CB/DB L2 path | DCC/HTILE | Net |
|---|---|---|---|---|---|
| Fixed render-pass 1080p | 8.3 MB | No (6%) | bypass — never in L2 | Yes | reference |
| Fixed render-pass 320×180 | 230 KB | Would fit (45%) — **but bypass, so pointless** | bypass — never in L2 | Yes | no L2 benefit |
| Compute image store 320×180, read ×4 | 230 KB | Yes in theory, if not evicted | L2 path yes | No (lost) | fragile read-win; write-lossy |
| Compute image store 480×270 | 518 KB | No (>L2) | L2 path yes | No | thrash |

- At a "balanced" regime of 230 KB, potential read savings are bounded by what the replacement policy lets survive — and every texture sample in the same pass competes. Against DCC+HTILE on the RBE path, the compute alternative has to beat a **compressed, already-optimized** write with an *uncompressed, contestable* cache. Expected: net-negative.

## 4. COST / OVERHEADS
- No format/instrumentation support on GFX8 to *set* residency or *measure* it (counters). Measuring would need SPM/GPUPerfAPI GFX8 tables (partially documented in-project via GPUPerfAPI v3.11.1 catalog) and possibly new kernel/driver access = **NO AUTORIZADO** under current project rules.
- Even measurement is uncertain: RCP `L2CacheHit` availability on Polaris12 SPM is unconfirmed; radeontop has no L2 counters; `AMD_performance_monitor` may or may not surface `L2` on GFX8.

## 5. FEASIBILITY VERDICT

- **Headline (framebuffer resident in L2) — NOT VIABLE on Polaris12:** the CB/DB path bypasses L2 entirely (hardware fact), so no internal resolution choice can make a *render-pass* attachment L2-resident.
- **Compute-path sub-variant — MARGINALLY POSSIBLE but low expected value:** works only for targets ≤ ~230 KB and only if the working set doesn't evict them; it forfeits DCC/HTILE; and it cannot be measured with current authorized tooling. It is the same instinct as generic LLM-aware caching (GSPC) applied to a 512 KB/no-control device.
- Classification: **CONTRADICTED BY PRIOR ART** (hardware topology makes the headline impossible) with the surviving sub-claim classed **PARTIALLY NOVEL / LOW FEASIBILITY** (mechanism known; Polaris-specific platforming only; blocked measurement).
- A "*negative*" experimental value exists: an experiment to *demonstrate* that CB/DB never touch L2 on this chip (via counters/telemetry) would conclusively retire both I-01's and I-09's framebuffer-residency premises A/B — but that belongs to I-01 TEST A instrumenting, not to building a feature.