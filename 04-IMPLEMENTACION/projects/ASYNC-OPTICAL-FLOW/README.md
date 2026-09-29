# ASYNC OPTICAL FLOW FRAME GENERATION — PROJECT README

**Status:** Phase R-3 documentary novelty audit (DOCUMENTAL ONLY, no implementation).

**Idea:** explorar una implementación de optical flow/interpolation sobre queues
compute lógicas de Polaris12; la familia documenta ACE/HWS, pero el número local de ACEs,
la reserva de CUs y el overlap efectivo son `UNKNOWN`. No se presupone una máquina de
dos ACE.

## DEFINITIONS (used everywhere in this project)
- **REAL FPS:** frames actually rendered by the 3D pipeline (GPU frame rate; the only number that drives real performance/latency).
- **GENERATED FPS:** displayed frames per second after inserting interpolated frames. Can exceed REAL FPS; pure smoothness, not throughput.
- **FRAME TIME:** ms per real rendered frame (time budget for each real frame).
- **LATENCY:** end-to-end input-to-photon delay, including optical-flow estimation overhead + one extra (generated) frame's worth of buffering (interpolation needs the *next* real frame → inherent +1 frame, ~16.7 ms @60, plus flow time).
- **POWER:** additional GPU power estimated by SMU (`W_SMU`) from the flow+interp compute; physical draw is `UNKNOWN`; a 50 W TBP entry is a constraint.

## KEY FACTS ABOUT THE HARDWARE TARGET
RX 550 = Polaris12: 8 CUs (512 SP), ~1.2 TFLOPs FP32, 16 ROPs, 512 KB L2,
96–112 GB/s nominal/estimado (128-bit GDDR5; real `UNKNOWN`), GCN4. La familia
documenta ACEs/HWS, pero el número de ACEs y cualquier reserva de CUs por Vulkan
son `UNKNOWN`; no se presupone overlap hardware.

## CRITICAL PREMISE CHECK (do NOT assume free CUs)
En este chip todo recurso shader pertenece al array de 8 CUs. "Async compute" como
capacity family-level se describe mediante un ACE/HWS scheduler, pero una queue Vulkan
lógica no prueba ACE físico ni overlap. Si el workload es GPU-bound, las queues
compiten por CUs/L2/DRAM; el coste y el posible solapamiento quedan `UNKNOWN` y deben
medirse. No se presupone una máquina de dos ACE.

## DOCS IN THIS DIRECTORY
1. `PRIOR-ART.md` — the survey (academic/commercial/community + hardware units).
2. `POLARIS12-FEASIBILITY.md` — numeric feasibility on RX 550 incl. cost extrapolation.
3. `EXPERIMENT-DESIGN.md` — how to measure flow cost, latency, artifacts on this chip.
4. `RISKS.md` — what can go wrong.
