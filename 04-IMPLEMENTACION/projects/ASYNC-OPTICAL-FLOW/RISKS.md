# IDEA I-07 — ASYNC OPTICAL FLOW FRAME GENERATION: RISKS

## 1. THE PREMISE RISKS (highest priority)
- **"CUs free" is false by construction on RX550.** 8 CUs are the only shaders. Flow compute and game compute interleave in the ACEs; any GPU-bound game loses exactly the flow cost from REAL FPS (GPUOpen async doc: shared GPR/LDS/cache; nBodyGravity: only complementarity pays; Division2: async can stall gfx). Risk: entire project collapses to slight-smoothed-low-res. Severity: HIGH; likelihood: certain at 1080p.
- **Fence/queue overhead per generated frame** on a tiny GPU eats the "free" windows; AMD guidance: command lists must be big enough to amortize fences. GSync interplay etc.

## 2. PERFORMANCE RISKS
- **Flow ALU density:** 7-iteration, 256-candidate SAD chain at ≥2–20 ms/generated frame on this silicon (extrapolated from FSR3's own 5700XT numbers). Even 540p may miss the 60-fps latch budget.
- **Memory:** luma pyramids + flow + interp surfaces + double-buffering in async mode ≈ +100–170 MB @1080p (FSR3 tables) on a 2 GB VRAM SKU with ~112 GB/s → cache/DRAM thrash spikes, hitching, fan.
- **CPU/pacing:** interpolation needs frame pacing; FSR3/swapchain "busy-wait" pacing on low-end drivers can itself hitch (TechPowerUp Forspoken = pacing issues list).

## 3. LATENCY RISKS
- **Software flow is on the critical path:** latency ≈ +1 real frame (await the *next* sample) + flow time. At 60 real fps → +16.7 ms minimum before flow 0 ms; realistically +22–40 ms here vs <16 ms for DLSS3 on RTX40 (hardware flow). Anti-Lag is not available at this tier; no mitigation except reducing base res/fps.
- Double-frame-buffered window → input feels "behind"; motion compensation errors make it worse under cursor-corner pans.

## 4. QUALITY / ARTIFACT RISKS
- **No per-object MVs** (game-agnostic flow-only interpolation is exactly the AFMF compromise; AFMF2 even worse without MVs; PC Gamer). Disocclusion ghosts, HUD swimming, thin-edge shimmer, scene-cut zero-flow pops — all documented FFX-FI caveats (vklayer project; FSR3 reviews).
- **Base-rate floor:** below ~60 real fps artifact rate explodes (AMD official). On this GPU the attractive cases (30→60) are precisely the ones AMD says to avoid. Risk: feature only "works" where nobody needs it.

## 5. HARDWARE / PLATFORM RISKS
- **GCN4 + Linux + Vulkan edge cases:** LucidRaster notes AMD-Windows-Vulkan subgroup slowness (2–3×); RADV path should be used; D3D12 experiments risk wasting time on driver-side regressions.
- **CU reservation on 8 CUs** may not even be materially usable (reserving 1 CU = −12.5% for the game). Wave limiting APIs may not exist for Polaris12-class RADV → the "two ACE" capability is real (GCN whitepaper: multiple ACEs, HIWS) but practical partitioning is coarse.
- **No VK_NV_optical_flow** on AMD → FFmpeg/`fruc` cross-check impossible; must rely on SW reference (FFX).

## 6. COST / SCOPE RISKS
- High engineering cost to reproduce FFX SDK in Vulkan, no unique algorithm contribution (prior art covers it), no realistic end-user win on RX550 weight-class → the project's ROI is documentation/measurement only.

## 7. SCORECARD
| Risk | Likelihood | Severity | Mitigation |
|---|---|---|---|
| CUs-not-free premise fails | Certain | Fatal to perf goal | Stage A/B occupancy gates before any build |
| OF+FI exceeds 60-fps-gap budget | High | Fatal | 540p/720p off; accept doc-only |
| Added latency > +1 frame + 10 ms | Near-certain | High | document honestly; no Anti-Lag crutch |
| Artifact pop at acceptable pace | High | Medium | FFX reference + artifact gate D |
| 2 GB VRAM / bandwidth pressure | High | Medium | 720p-only working set; monitor DRAM |
| Windows/AMD subgroup slowdowns | Medium | Low | RADV first |

## 8. OUTCOME
If Stage A/B fail (likely), the correct release is a documentation deliverable: RX550 cannot sustain 1080p async-optical-flow frame generation with usable quality/latency; the feature is a KNOWN-VARIANT platforming of AMD's own FSR3/AFMF software stack and is recommended **D (do not implement)** on this hardware, with the *measured feasibility report* as the sole artifact.