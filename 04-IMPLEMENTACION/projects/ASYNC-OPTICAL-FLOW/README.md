# ASYNC OPTICAL FLOW FRAME GENERATION — PROJECT README

**Status:** Phase R-3 documentary novelty audit (DOCUMENTAL ONLY, no implementation).

**Idea:** Leverage Polaris12's two ACE async-compute engines + the graphics queue's residual capacity to run compute-side optical flow (block matching / SAD / pyramidal flow) and frame interpolation, generating extra frames between real renders — "AFMF-style frame generation, implemented in custom compute on a GCN4 low-end GPU."

## DEFINITIONS (used everywhere in this project)
- **REAL FPS:** frames actually rendered by the 3D pipeline (GPU frame rate; the only number that drives real performance/latency).
- **GENERATED FPS:** displayed frames per second after inserting interpolated frames. Can exceed REAL FPS; pure smoothness, not throughput.
- **FRAME TIME:** ms per real rendered frame (time budget for each real frame).
- **LATENCY:** end-to-end input-to-photon delay, including optical-flow estimation overhead + one extra (generated) frame's worth of buffering (interpolation needs the *next* real frame → inherent +1 frame, ~16.7 ms @60, plus flow time).
- **POWER:** additional GPU power draw from the flow+interp compute; on a 50 W TBP entry card is a hard constraint.

## KEY FACTS ABOUT THE HARDWARE TARGET
RX 550 = Polaris12: 8 CUs (512 SP), ~1.2 TFLOPs FP32, 16 ROPs, 512 KB L2, 112 GB/s (128-bit GDDR5), GCN4 (ACE + HWS + CU reservation + Quick Response Queue — Polaris whitepaper).

## CRITICAL PREMISE CHECK (do NOT assume free CUs)
On this chip every shader resource is the 8-CU array. "Async compute" = the same CUs, interleaved by the ACE scheduler (AMD GCN whitepaper; GDC17 "compute mixed with graphics"). If the game is GPU-bound, generated frames COMPETE with real frames for CUs, L2, and DRAM — the cost is additive. Only *complementary* bottlenecks (e.g. ROP/geometry-bound passes) hide this cost, and AFMF/FSR3 documents confirm the cost depends on async-compute headroom (PC Gamer; TechPowerUp Forspoken review).

## DOCS IN THIS DIRECTORY
1. `PRIOR-ART.md` — the survey (academic/commercial/community + hardware units).
2. `POLARIS12-FEASIBILITY.md` — numeric feasibility on RX 550 incl. cost extrapolation.
3. `EXPERIMENT-DESIGN.md` — how to measure flow cost, latency, artifacts on this chip.
4. `RISKS.md` — what can go wrong.