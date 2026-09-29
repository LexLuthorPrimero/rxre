# IDEA I-07 — ASYNC OPTICAL FLOW FRAME GENERATION: POLARIS12 FEASIBILITY

RX550 target facts: 8 CUs / 512 SP / ~1.2 TFLOPs FP32 / 512 KB L2 / 16 ROPs / GCN4.
Bandwidth nominal/estimado 96–112 GB/s según módulo/VBIOS; bandwidth real `UNKNOWN`.

> **RECONCILIACIÓN 2026-09-24:** la familia GCN4 documenta ACEs/HWS, pero el número de
> ACEs de Polaris12 y cualquier reserva de CUs por Vulkan son `UNKNOWN`. Las extrapolaciones
> de coste de FSR3 no son mediciones locales y no prueban inviabilidad.

## 1. HOW MANY CUs WOULD OPTICAL FLOW NEED? (scaled from the FidelityFX reference)

Reference algorithm (FFX Optical Flow, GPUOpen primary doc): 7 iterations of [search 8×8-block over 24×24 → 16×16=256 SAD cases → 3×3 median filter → 2× upscale]. At 1080p: (1920/8)×(1080/8)=240×135=32,400 blocks × 7 iterations; at the 7 levels add finer blocks (hidden pyramid levels are separately dispatched). Each SAD case touches 64 pixels of prev luma.

- **Computation (per block):** ≈ 256 candidates × [SAD of 64 pixels (64 ADDs+saturates) ] + filter/upscale ≈ 20–30K integer ops → 32.4K blocks ≈ **0.65–1 Gint-op/frame just for the coarse level**, plus pyramid full-res passes for luma (7 resources, downscale chain) and histogram/scene-change.
- **Busiest full-res passes** (luma pyramid + final flow consume) are memory-bound more than ALU-bound (Romera JRTIP; Horn-Schunck roofline → memory-bound).
- **Perceptible budget on this chip:** 1.2 TFLOPs FP32 ≈ 0.6 Tint-op/s integer. A 30-fps game at 1080p gives 33 ms/frame; ÷2 for generation = ~16.5 ms budget for the whole OF+FI chain. The OF chain alone is in the multi-ms range (see below); there is no slack.

**Extrapolated cost from FSR3's own tables (async OFF, PIX), normalized to RX550:**
- RX 5700 XT (36 CUs → 9.75 TFLOPs): FG at 1080p NativeAA ≈ **2.2 ms**, 4K Native AA ≈ 8.0 ms; Upscale ≈ 4.7 ms@4K.
- Effective RX550/US reckoning: RX550 ≈ 1.21 TFLOPs. Scaling (TFLOPs ratio ≈ 8×;
  ceilings depend on 96–112 GB/s nominal/estimado, real bandwidth `UNKNOWN`):
  **1080p OF+FI ≈ 8–20 ms**, 720p ≈ 4–10 ms, 540p ≈ 2–5 ms.
- At 60-fps real, the RX550 has ~16.7 ms to generate one interpolated frame; extrapolation lands on or above that → **frame generation at 1080p consumes most or all of the available gap** even before game load. This is why AMD only lists RX 5000+ / RTX2000+ as recommended.

**Can it fit in async ACEs without hurting the graphics queue?** La familia GCN4
documenta queues/ACEs y posiblemente comparte la shader array; el número de ACEs y la
semántica de scheduling/overlap de esta unidad son `UNKNOWN`. No se presupone una API de
reserva de CUs. El impacto debe medirse.

## 2. MEMORY BANDWIDTH COST
Flow chain traffic ≈ per pair of frames: luma pyramids (7 levels × 2 buffers), 7 search passes each reading prev luma (256 candidates × up to ~2 kB neighborhood traffic core + block reuse), flow buffers (R16G16 at W/8,H/8 per level), scene-change histograms; interpolation adds: estimate depth pass, 2 MV fields + inpaint pyramids, disocclusion, interp, inpaint — all reading/writing at ~full-res.
- Estimate: ≥ 4–6 full-frame read passes + ~2–3 writes ≈ **35–60 MB por frame generado** a 1080p (estimación, no medición). Contra 96–112 GB/s nominal/estimado, el tiempo puro de bandwidth y el impacto real son `UNKNOWN`; no se concluye inviabilidad.
- On 2 GB VRAM RX550 SKUs: FSR3-style working set (+100–170 MB at 1080p, or more in async mode w/ double buffering) plus luma/flow surfaces is defensible at 720p/540p but tight at 1080p on the 2 GB cards.

## 3. LATENCY BUDGET
Frame generation inherently waits for *two real frames* (prev + next) → interpolated frame displayed exactly one real-frame-interval *after* the second real frame. At 60 fps real that's +16.7 ms before you *start* flow+interp; add flow/‑FI compute (2–8 ms at 1080p, higher on this chip) → total added latency **≈ +1 real frame + flow time ≈ 20–30 ms** at 1080p30 real / 60 generated. FSR3 docs: "Interpolating a frame adds latency – this is by design"; measured pure-added latency is real even at RX7000-class. On RX550 the added latency is proportionally larger (slower flow) and cannot be mitigated without an Anti-Lag-class input-pipe feature (Anti-Lag 2 is RX5000-class-era; on Polaris12 only Radeon Anti-Lag legacy is available).

## 4. ARTIFACT RATE — ESTIMATED vs HARDWARE FLOW
- SW block-based flow (8×8, SAD) has known artifact set: disocclusion seams, thin-edge/high-contrast boundary flicker, HUD/UI "swimming", ghosting, no-single-object-confidence → median filters smear small motion, scene cuts get zero-flow fallback (FFX docs scene-change; vklayer notes; FSR3 reviews). HW flow (NVOFA/temporal hints, NvOFFRUC / FFmpeg) improves cost & temporal stability — AMD's FSR3-with-game-MVs exists precisely because flow-only interpolation underperforms (PC Gamer: AFMF2 motion-vector-less compromise).
- Base-rate restriction: below ~60 fps real the artifact rate explodes (AMD official guidance) → on RX550 the *only* regime where this is viable (720p lower detail) is also the regime where games already push 60+ and need FG the least → circular.

## 5. POWER
- RX550 TBP ≈ 50 W. Optical-flow compute actively spins ALL 8 CUs + L2/DRAM for 2–8+ ms/frame → realistic **+5–15 W** (order-of-magnitude: FSR3 bumps are not free and this chip is bandwidth-poor). Cards on PCIe-slot power only could hit board limits under sustained FG.

## 6. FPS MODELING (real vs generated, honest numbers)
| Config | REAL fps | GEN fps (displayed) | frame time | latency added | effort |
|---|---|---|---|---|---|
| 720p, unaided game | 45 | 90 | 22 ms | +~22–40 | flow thruput limited |
| 720p, light game | 60 | 120 | 16.7 ms | +~18–30 | marginal |
| 1080p, typical | 30 | 60 | 33 ms | +~34–55 | infeasible (flow alone ~8–20 ms) |
| 1080p, ROP-bound depth-y | 60 | 120 | 16.7 ms | +~18–28 | only hidden-if wow complement |

Rule: GENERATED FPS = REAL FPS × 2 only while REAL FPS itself doesn't drop from the flow stealing CUs/bandwidth; on RX550 the flow eats the CU budget that would otherwise keep REAL FPS up. Realistically: this GPU should use FG only at ≤720p with an already-frame-time-light scene, and the *honest* win is smoothness at very low resolution — never a throughput gain.

## 7. VERDICT
- **Technically plausible?** La maquinaria algorítmica es pública, pero la capacidad local,
  overlap, bandwidth efectivo y beneficio en RX550 son `UNKNOWN`; las extrapolaciones FSR3
  no sustituyen una medición.
- **Novelty:** `KNOWN VARIANT` como algoritmo; la aplicabilidad/impacto en Polaris12 es
  `REQUIRES CAPABILITY AUDIT` y `REQUIRES EXPERIMENT`.
- Recommended path: measurement-first, sin declarar inviabilidad ni viabilidad antes de
  evidencia local.
