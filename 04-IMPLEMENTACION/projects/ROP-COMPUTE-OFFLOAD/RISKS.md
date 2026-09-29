# IDEA I-04 — ROP OFFLOAD TO COMPUTE: RISKS

## 1. CORRECTNESS / API SEMANTICS
- **Ordering:** API requires in-order fragment execution for blend and deterministic output (CUDARaster enforces it; Laine §ordering). Compute loses it → *wrong images* unless you re-sort or sacrifice deterministic output. High severity.
- **Hole-free rasterization:** D3D/VK raster rules (top-left, pixel centers) must be reproduced bit-exactly; CUDARaster dedicates a stage to it; off-by-one at edge treads = artifacts. Medium-high.
- **Depth precision / format:** packing depth into 64-bit ints loses mantissa bits (CuRast uses 28-bit depth = reduced precision) → z-fighting risk. High for exactness-focused projects.
- **MSAA coverage semantics:** sample-position-dependent behavior must be emulated per sample; 「hardware does this at sample frequency」— software replication is a conformance minefield.

## 2. PERFORMANCE TRAPDOORS (specific to Polaris12)
- **Atomic contention:** 2M+ 1080p vis-buffer lines hit one 512 KB L2. At 60 fps you have 33 ms/frame to eat ~2M RMW + resolve reads through the nominal/estimated
96–112 GB/s DRAM path (real bandwidth `UNKNOWN`) and a ~0.5 MB L2 → thrash is plausible. The
"free CU" premise is not established.
- **Wave-launch / dispatch tax:** 8-CU chip = every dispatch is tiny; barriers, `s_endpgm`, descriptor loads (AMD GDC17 wave-launch costs) eat a big % of a 1080p pass.
- **Fragment vs compute shading order (pixel-locality):** compute ordering of a naive grid is usually ≥2× worse than fragment traversal (StackOverflow 42127601 / CGSE 9956). Substantive risk of retrograde performance even for fancy "shade the vis buffer" work.
- **Texture gradient (quad) emulation:** GCN fragment quad-derivatives are hardware; compute must compute them manually (CuRast mipmap footprint code) — extra ALU + risk of mip-mismatch shimmer.
- **Driver/blend-atomics absence:** GCN has no shared-memory-based ROP-equivalent; per-pixel spinlock/serialization patterns do not map to GCN's LDS atomic strengths. Pain point: imageAtomic* on RGBA is limited; you end up with u32 channel encoding + extract/merge asset cost.

## 3. MEMORY / POWER
- **DRAM pressure higher, not lower** (vis buffer + resolve double-read). On a
  nominal/estimated 96–112 GB/s, 2 GB DRAM part (real bandwidth `UNKNOWN`), this may
  degrade other traffic; the magnitude is unmeasured.
- **No DCC/HTILE:** motion runs without the very compression AMD optimized Polaris to do (whitepaper: "more efficient delta color compression"). Larger effective bandwidth footprint → power up.
- **VRAM working set:** 1080p RGBA8 + R32 vis + depth ≈ +12–20 MB/work; 2 GB parts on 4 GB boards mostly OK, but 2 GB SKUs get tight with FSR-like chains (FSR3 overhead table: 100–170 MB at 1080p).

## 4. HARDWARE/ENVIRONMENT
- **AMD GCN4 driver quirks (from LucidRaster):** subgroup instructions slow on AMD Windows Vulkan; AMD Linux fine. If the harness runs Windows/D3D12, expect 2–3× slowdowns in software raster paths unrelated to the algorithm.
- **GCN4 sparsity of compute resources:** 8 CUs are *all* the shaders; there's no
  separate compute block. Any claimed "compute unit free while ROP busy" must be proved
  with a capability/occupancy audit, not assumed.

## 5. SCOPE / VALUE RISK
- Worst case: months of work reproducing correctness (ordering, raster rules, MSAA, gradients) for a feature that published literature says loses 2–10× on typical scenes against this exact chip. The experiment design (B-test stepped substitution) exists precisely to fail-fast before investing in full-pipeline effort.
- If the real target is "more GPU work usable while ROP/geometry-bound," async compute
  remains una hipótesis; no se presupone que exista reserva de CUs por API Vulkan. La
  alternativa debe compararse mediante capability audit y, posteriormente, un experimento
  autorizado.

## 6. RISK SCORECARD
| Risk | Likelihood | Severity | Mitigation |
|---|---|---|---|
| Compute raster slower than HW (2–10×) | Certain (lit) | High | Stepped B-test, gate at 1.5× |
| Atomic/L2 thrash at 1080p | High | High | 720p/1080p sweep, count DRAM not wall |
| API-semantics holes (order, MSAA, rules) | Certain w/o discipline | Medium | Copy Laine pipeline structure |
| Async-co-schedule win < 15% | `UNKNOWN` | `UNKNOWN` | Capability audit; no tuning de CU reservation sin API confirmada |
| Windows AMD driver perf drift | Medium | Medium | Primarily run RADV/Linux; D3D12 only as cross-check |
