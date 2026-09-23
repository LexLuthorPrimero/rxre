# IDEA I-06 — PREDICTIVE GHOST CACHE: POLARIS12 FEASIBILITY
# ANÁLISIS DE VIABILIDAD EN POLARIS12 (RX 550 / GCN4)

Target: RX 550, Polaris 12 / Lexa.
**Confirmed specs (primary/aggregate sources: AMD RX 550 page, TechPowerUp DB, VideoCardz):**
- 8 CUs × 64 shaders = **512 stream processors**; 32 TMUs; **16 ROPs** (2 render backends)
- L2 = **512 KB**; L1D (V$) = **16 KB/CU** (texture vector cache); scalar K$ 16 KB/4 CUs; instruction cache
- 128-bit GDDR5 @ 7 Gbps → **~112 GB/s**; boost ~1183 MHz → ~1.2 TFLOPs FP32
- 4th-gen GCN: ACEs + HWS + Quick Response Queue + compute unit reservation (Polaris whitepaper)
- Sources: https://www.amd.com/en/products/graphics/radeon-rx-550 ; https://www.techpowerup.com/gpu-specs/radeon-rx-550.c2947 ; https://videocardz.com/68830/amd-launches-radeon-rx-550-for-79-usd

---

## 1. WHERE THE LATENCY ACTUALLY LIVES (what a "ghost cache" would attack)

ES-01 evidence (in-repo, VERIFIED): the synthetic workload is **fetch-bound** — frametime ∝ fetch;
p50 flat, p99 dominated by fetch; power stable at cap (auto-pacing). The delayed service is:
**texture request → L1 miss (16 KB/CU) → L2 (512 KB) → VRAM via MCDs / GTT**. CB/DB **bypass L2**
(color/depth via RBE tile caches + DCC/HTILE), so depth bandwidth is NOT the fetch problem — textures
are.

| Stage | Size/description on Polaris12 | Role in "ghost cache" |
|---|---|---|
| L1 V$ (texture) | 16 KB per CU × 8 CUs = 128 KB total | the *fast* tier the predictor wants to hit |
| L2 | 512 KB total | tiles that miss → L2; the partition point |
| VRAM | 2 GB GDDR5 @ 112 GB/s | the *resident* tier |
| GTT/system | PCIe | worst case ES-01 lives here |

## 2. THE HARDWARE/CONTROL PROBLEM (why "hardware ghost cache" is contradicted)

1. **No L2/texture-cache residency control on GCN4.** CUDA-style `persistingL2` / access-policy
   windows are **Ampere+ (cc≥8.0)**; AMD has no equivalent exposed on Polaris. You cannot "pin"
   predicted tiles into L2 from userland.
2. **No software prefetch instruction for textures on RADV/Vulkan-GCN4.** The only prefetch
   primitives in the stack are CPU (`cudaMemPrefetchAsync`/PTX — NVIDIA-only) or engine-side
   residency requests. Polaris12's L1/L2 arbiter is demand-driven.
3. **PRT / sparse residency is fragile on Polaris.** Vulkan `sparseBinding` exists (amdgpu PRT),
   but community + 2026 amd-gfx threads document crashes/instability on Polaris-class cards
   (CachyOS#930; lists.freedesktop.org amd-gfx/2026-March). A predictor that *spares/pages* tiles
   ahead would bet on a broken-on-this-chip feature.
4. **`mem_busy` ≠ bandwidth** (METRICS-DEFINITIONS caveat). Any "reduced fetch" claim must be
   measured via frametime/faults/tile residency, not `mem_busy` %.

## 3. WHAT IS GENUINELY FEASIBLE (the surviving sub-claim)

**Software predictive "ghost" service, userland, no kernel/HW change:**
- Mirror engine prefetch behavior (UE/Unity already do camera-based mip preload; ID5 did
  feedback buffer + page upload). The *novel* twist = make the *prediction* explicit, GPU-side
  (or timer-side) and *score* it against the fetch-bound p99.
- Mechanism options, ranked by feasibility on Polaris12:
   1. **Object/mip residency hinting** — engine already has camera + per-object bounds; prefetch
      images into VRAM (`GTT→VRAM` copies) N frames ahead, gated by predicted camera. **KNOWN at
      engine level (Unity `SetPreloading`, UE `r.Streaming.**)`; dose done by *our own synthetic*
      harness = not novel engineering, but measurable.
   2. **Vulkan `sparseBinding` "reserve"** — pre-mapped sparse image whose backing pages are
      filled ahead of camera. Feasible *on paper*; **PRT instability risks corrupting results**.
   3. **Micro-prefetch warm-up** — issue small *read-only* texture samples (a 4×4 region of the
      predicted mip) F frames early, so the *read path* L1/L2 warms without full virtual-texture
      machinery. This uses only the *existing* demand cache (a "ghost" in behavior: touch tiles you
      guess, with a touch-pass on the ACE/GFX queue). **This is the closest to "ghost cache" that
      Polaris12 supports — and the ONLY mechanism that exercises L1/L2 at all.**

## 4. QUANTITATIVE BOUNDS (scaled from known references)

- Texture working set in HE level (Hakura & Gupta'97; n-body style): individual texture working
  sets fit in 16 KB; the *composite* scene working set is what exceeds L1. A "ghost warm-up" that
  wins p99 must **already reside in L2** (512 KB) when the frame starts, or be fetched *before*
  the stall. At 112 GB/s, a 1 MB texture = ~9 µs VRAM→L2 → one full frame (16.6 ms) of slack if the
  touch happens 1+ frames ahead. The time budget for prediction slack is essentially free; the
  question is *accuracy + pollution*.
- **Pollution risk quantification:** prefetching text that *won't be used* evicts valid L1/L2 lines.
  From prefetch-policy literature (ARC/Bypass/IPDPS): a ≥2× on accuracy is typically needed for
  wins. Dumont'03 showed perceptually-guided *prediction camera* accuracy is scene-dependent;
  UE's shipped hidden-primitive prefetch (`HiddenPrimitiveScale`) exists precisely because
  *camera prediction is imperfect*.

## 5. INTERACTION WITH ESTABLISHED IN-REPO FACTS

- **ES-01 (fetch-bound, p99 ∝ fetch):** supports the idea's *premise* (fetch is the pain) and
  *rejects its lazy form* (throwing fetch at the problem doesn't change p50; only *reordering*
  ahead could move p99). The natural experiment = same F1/F2 workloads, one "ahead" (warm-up)
  vs one reactive (control), same capping regime.
- **GHOST (in-repo project):** I-06 overlaps GHOST's localidad/asignación scope. Differentiation:
  GHOST = *allocation/ordering* of the working set (GTT vs VRAM, wiring); I-06 = *temporal
  prediction & warm-up* (what/when to load). Keep them separate (no-fusion rule) but coordinate
  G-metrics.

## 6. FEASIBILITY VERDICT (Polaris12)

- **Hardware-cache ghost layer (predict→pin L2):** **NOT FEASIBLE / CONTRADICTED BY HARDWARE** —
  no L2-residency or texture-prefetch API on GCN4; PRT unreliable.
- **Software predictive "ghost" warm-up/residency:** **PARTIALLY FEASIBLE** — implementable with
  existing Vulkan + synthetic harness + runner K, **without kernel/driver changes**, exercising
  L1/L2/L2-vs-VRAM through *real sampled reads*. Its *novelty* is thin at engine level (UE/Unity
  already do camera-based preloads); its surviving *novel sub-claim* is "explicit camera-forward
  prediction **combined with a read-path warm-up pass** on a *fetch-bound desktop IMR* measured
  against p99" — not found in primary sources.

**Bottom line:** the *prediction* half is KNOWN VARIANT (Dumont'03, UE, Unity, id5, NeuralPVS);
the *cache mechanism* half is NOT FEASIBLE as hardware on GCN4; the *only* realizable artifact is
a **userland warm-up prediction service**, whose documentation value (fetch-bound IMR + p99) is
real but whose novelty is a thin, specific sub-claim. → **RECOMMENDED STATUS: C** (refine to that
sub-claim; do NOT pursue hardware-cache angle).