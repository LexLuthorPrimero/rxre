# IDEA I-05 — GPU FRAME RECORDER FOR GFX8: ARCHITECTURE

> **Fase:** FASE R-3 — DOCUMENTARY NOVELTY AUDIT (SOLO DOCUMENTAL, no implementación; DISEÑO, no código)
> Target: RX 550 = Polaris12 (GFX8): 8 CUs / 512 SP / 16 ROPs / 512 KB L2 / bandwidth
> nominal/estimado 96–112 GB/s; bandwidth real `UNKNOWN`.
>
> **RECONCILIACIÓN 2026-09-24:** la ruta source-level RADV auditada es
> `radv_device_init_rgp()` → `radv_sqtt_init()`. `si_init_sqtt()` pertenece a RadeonSI
> y no prueba RADV/GFX8. La existencia de código no prueba una captura real en Polaris12.
> `gfx902` no es el target nominal de este documento.

## 1. DESIGN SPACE — WHAT A "FRAME RECORDER" MEANS HERE

Three legitimate capture tiers for GFX8, in order of increasing depth and implementation cost:

| Tier | What it records | Tool precedent | Feasibility on Polaris12 |
|---|---|---|---|
| **T0 — API** | Every Vulkan call + timing (draws, buffers, barriers) | api_dump / gfxreconstruct / RenderDoc | DONE by others; no need to build |
| **T1 — Kernel/queue** | Job lifecycle: submit → run → done, vblank, fences | trace-cmd + GPUVis | DONE by GPUVis; reuse |
| **T2 — SQTT** | Per-wavefront shader occupancy/stall trace inside each frame (the "expensive" slot) | RADV `MESA_VK_TRACE=rgp` (source-level) | Runtime GFX8 y viewer/decoder `UNKNOWN`; capability audit required |

El valor potencial de I-05 se concentra en **T2 analysis**. Sections 2–4 describe una
arquitectura candidata: captura RADV → `.rgp` → decoder SQTT GFX8 (v2.2) → viewer; cada
etapa requiere capability audit y no se presupone disponible.

## 2. END-TO-END PIPELINE (target architecture)

```
 Vulkan app (game/benchmark) on RX 550
   │  (RADV → GFX8/Polaris12; gfx902 no es el target)
   ▼
 RADV frontend  ──MESA_VK_TRACE=rgp──►  .rgp capture file (SQTT streams, SQTT_VERSION_2_2)
   │                                          (cualquier ajuste externo de perfil requeriría autorización separada)
   ▼
 RGP-format container reader  (parse header, sections; open format per AMD RGP manual + Mesa ac_rgp.c)
   ▼
 SQTT packet decoder  (SQTT_VERSION_2_2: token stream → per-CU/per-SE wavefront events, PC, stall states)
   ▼
 Per-frame aggregation  (group by frame id / draw call / submission; build wavefront timeline)
   ▼
 Viewer / exporter   (timeline UI and/or JSON/CSV export like rgp-inspect)
```

## 3. COMPONENTS AND PROVENANCE

1. **Capture layer — source-level route, runtime no confirmado.** La evidencia RADV auditada
   es `radv_device_init_rgp()` → `radv_sqtt_init()`. `si_init_sqtt()` pertenece a RadeonSI
   y no demuestra RADV/GFX8. Que el código exista no prueba una captura real en `1002:699f`.
   Cualquier ajuste externo de perfil sería una escritura separada, sujeta a autorización.
2. **Container reader — the least-known part.** RGP `.rgp` is a binary format documentado
   en fuentes; `rgp-inspect` upstream implementa una ruta moderna, pero orientada a
   `gfx1201`. No se presupone un reader GFX8 ni un fork barato.
3. **SQTT v2.2 decoder — the true build effort.** Tokens (wave start/stop, program
   counter, stall reason, scheduler events) must be decoded for the GFX8 SQTT version.
   Mesa's `ac_sqtt.c` has GFX8 register definitions; the trace-packet grammar is shared
   with newer SQTT versions but register/opcode differences for v2.2 must be audited.
   No open tool was confirmed in the audited sources; coverage remains `UNKNOWN`.
4. **Aggregation & viewer — candidate commodity.** Timeline rendering (GPUVis-style or
   web-based) is known work; no se presupone que `rgp-inspect` acepte GFX8.

## 4. POLARIS12 DATA VOLUME BOUNDS (why the design is tractable)

8 CUs / 2 SEs (Polaris12: 1 SE, 8 CUs — see R0-4). SQTT traces scale with active wavefronts × program counter sampling. Compared to RDNA (many more CUs/tokens), a GFX8 8-CU trace is *smaller*; the decoder/renderer does not need RDNA-class throughput. Practical expectation (hypothesis, unverified): per-frame SQTT capture at 1080p30 on 8 CUs yields tens of MB/minues of trace tokens — within any modern parser's capability. `[HIPÓTESIS]`

## 5. DEPENDENCIES / RESTRICTIONS

- **Ajuste de perfil** — cualquier establecimiento externo de `profile_peak`/performance
  level sería una escritura separada, no una propiedad de solo lectura of `ac_check_profile_state()`.
  Su necesidad para una captura real queda `REQUIRES CAPABILITY AUDIT`; no se autoriza aquí.
- **Counter programming NOT authorized** — T2 (SQTT) is NOT a counter reader; SQTT is a trace mechanism, distinct from GRBM/SQ PERF_SEL counters (FASE D/M). The design must not drift into PERF_SEL programming.
- **AMDVLK irrelevant** — EOL for GFX8 (Oct 2023). RADV is the only Vulkan path.
- **RGP GUI** — only relevant as an optional cross-check if RGP ≤1.16 binaries are obtainable and load GFX8 traces (`[NO VERIFICADO]`).
- **Viewer preference**: terminal/web/CSV (like rgp-inspect) over a full GUI — much smaller surface for a documentary-first project.

## 6. BUILD ROUTES (ranked by risk; documentary evaluation only)

| Route | Description | Risk | Rationale |
|---|---|---|---|
| **R1** | Evaluar `rgp-inspect` u otra herramienta upstream; no se asume un backport GFX8 | **UNKNOWN** | El upstream auditado es CLI Windows/Python orientada a `gfx1201`; no es una ruta Rust/Linux GFX8 confirmada. |
| **R2** | Custom minimal reader+decoder reading RGP manual + Mesa `ac_rgp.c`/`ac_sqtt.c` as spec | High | Ground-up; accurate but much larger effort; risk on undocumented packet details |
| **R3** | Skip SQTT: build only a T1 (kernel timeline) + T0 (API) recorder combining GPUVis + api_dump | Very low | Already solved; adds little novelty; provides an immediate "frame recorder" deliverable |

## 7. OPEN QUESTIONS (to be closed before any code)

1. Does the current RGP GUI (2.x) load GFX8-era `.rgp`? If yes → all-work-done, I-05 becomes trivial reuse. `[NO VERIFICADO]`
2. Can `rgp-inspect`'s decoder be pointed at SQTT_VERSION_2_2 with modest changes (structure shared) or does v2.2 need a full new grammar? `[NO VERIFICADO]`
3. Does RADV actually emit valid SQTT v2.2 on Polaris12 in practice (source says yes; empirical run needs `profile_peak` authorization)? `[HIPÓTESIS → needs authorized run]`
4. Does reading SQTT perturb the GPU enough to distort the frame being recorded (observability perturbation)? `[NO VERIFICADO]`

## 8. SUMMARY

The architecture is a **documentary hypothesis**: source-level RADV SQTT routes and
API/kernel capture tools may be reusable, but a real GFX8 capture, decoder availability
and runtime compatibility remain `UNKNOWN`. Nothing here runs or authorizes a write.
