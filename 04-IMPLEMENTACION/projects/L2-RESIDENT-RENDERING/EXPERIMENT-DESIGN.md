# IDEA I-09 — L2-RESIDENT INTERNAL RESOLUTION: EXPERIMENT DESIGN

Documentary/measurement-only plan. Goal: measure whether a compute-written target can be L2-resident on Polaris12 at all, whether re-reads absorb in L2, and demonstrate the CB/DB-bypass fact that retires the headline. No production feature.

## 0. HYPOTHESES TO TEST (read-only measurement)
- H1: Render-pass attachments on GFX8 never touch L2 (CB/DB bypass). Expected: confirmed via counters if available; else via timing signatures.
- H2: A compute-written target (image store) can be re-read several times with DRAM traffic only for the *first* read (L2 residency) when the target fits in ~45% of L2 (≤230 KB).
- H3: As target size grows toward 512 KB, re-read cost rises to DRAM-level (eviction) — the "residency" collapses.
- H4: No usable L2 hit counter exists on Polaris12 via radeontop/AMD_performance_monitor/RCP → measurement blocked, result recorded as UNKNOWN.

## 1. TEST A — DEMONSTRATE CB/DB-BYPASS (retires the headline)
- **A1.** Render a flat-color 1080p pass and a 240×135 pass (both fixed render-pass). Instrument with any visible counters: `CBD_run`, `CB_BUSY`, `SHADER_MEM`/TC counters, DRAM read/write via `perf` + amdgpu PMU (`mem_read`, `mem_write`).
- **A2.** Compare DRAM write traffic vs theoretical framebuffer size: writes should appear ≈ after DCC compact (i.e., traffic tracks framebuffer, NOT ~0). If L2 were absorbing writes you'd expect near-zero DRAM; DCC only compresses a few×, not to zero.
- **A3.** Repeat with a *huge* framebuffer impossible to cache (e.g., 4096×4096): if per-pass cost scales with size (no flat-cap), writes are DRAM-resident despite anything "fitting" — direct evidence against "small = resident."
- **Expected:** writes are DRAM-bound regardless of size; resident-in-L2 for CB path refuted by the A3 scaling with A1/A2 asymptotic behavior.

## 2. TEST B — COMPUTE-WRITTEN TARGET ACROSS SIZES (the only plausible route)
- **B1.** Compute pass writes a 160×128 RGBA8 target (80 KB) via `imageStore` (GENERAL layout, UAV).
- **B2.** A second fragment/compute pass reads it M times (M = 1..16), trivially (e.g., sum into an output).
- **B3.** Sweep target: 160×128 (80 KB), 320×180 (230 KB), 480×270 (518 KB), 640×360 (922 KB). Repeat M-sweep at each.
- **Metrics:** per-read-pass time (µs, Vulkan timestamps); DRAM traffic via amdgpu PMU if permitted; relative cost ≤230 KB vs >512 KB is the residency signature.
- **Expected:** ≤230 KB shows sublinear re-read cost (L2 absorbs); ≥518 KB shows flat linear (DRAM) — reproducing H2/H3 if real.

## 3. TEST C — CONTENDED WORKING SET (realism)
- **C1.** Same as B at 320×180, but add a texture-bound shader concurrently to evict the target (typical scene).
- **C2.** Same at 320×180 with geometry/stream flush between passes (workset pressure).
- **Expected:** residency benefit β vanishes under contention — proving that in real scenes the "resident target" is a mirage on 512 KB/no-pinning HW.

## 4. TEST D — DCC/HTILE vs COMPUTE-WRITE (the control)
- **D1.** Same scene rendered into a fixed render-pass (DCC+HTILE) vs into compute image store (no DCC). Measure DRAM traffic.
- **D2.** Compare color quality-adjusted DRAM bytes per frame.
- **Expected:** fixed RBE path ≤ compute path in traffic for typical content (DCC cheap, compute uncompressed) — confirming that chasing L2 residency is the wrong lever vs what the RBE already does.

## 5. COUNTER-AVAILABILITY GATE (must-do before interpreting anything)
Audit (read-only, per project rules) which L2 counters exist for GFX8:
- Try GPUOpen RCP `CacheHit`/`L1CacheHit`/`L2CacheHit` blocks on Polaris12 (SPM).
- Try `AMD_performance_monitor`/Gallium HUD L2 selectors on radeonsi/RADV.
- Cross-check GPUPerfAPI v3.17 catalog tables and the historical v3.11.1 extract
  (`R0-1…REFERENCE.txt`); neither proves L2 runtime support.
- **If none available:** record "no L2 hit/miss insight on GFX8" as a finding; Tests B/C then rely on per-pass timing + DRAM PMU alone (weaker but valid signatures).

## 6. METRICS / PASS/FAIL GATES
- Per-pass time (µs) @ fixed SCLK (DPM auto, uncontrolled fan, cooldown antes de cada run → usar rx550-torneo).
- DRAM read/write bytes (perf/amdgpu PMU) and V$/L2 proxy counters if they appear.
- FLAT = per-read cost constant across M (DRAM-resident). SUBLINEAR = L2 residency (≤230 KB target, no contention).
- PASS (for the sub-claim) = sublinear signature at ≤230 KB **and** survival under contention ≥50%.
- FAIL (headline) = CB-bypass demonstrated / no counters / no sublinear signature → supports RECOMMENDED STATUS E/D.

## 7. TOOLING
- RADV (stock or /opt custom Mesa 26.2.2), Vulkan timestamp queries + `VK_EXT_debug_utils`.
- `perf`/amdgpu PMU counters; rx550-torneo as runner; RCP/AMD_performance_monitor/GPUPerfAPI for L2 audit (all read-only).
- No kernel/Mesa modifications; no sysfs writes; no installs (project NO AUTORIZADO rules).
