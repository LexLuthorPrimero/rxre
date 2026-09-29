# PRIOR-ART-INDEX — Índice consolidado de prior art (R-3 ⇄ R-3.1)

> **Archivo:** `PRIOR-ART-INDEX.md`
> **Fase:** FASE R-3.1 — FUSION ARCHITECTURE AUDIT
> **Fecha:** 2026-09-22 — READ-ONLY
> **Función:** reconciliar fuentes citadas en R-3 (10 ideas) y en R-3.1 (7 fusiones) en un solo índice
> por área; **no** duplica los documentos (apunta a los archivos donde se discuten).

---

## 1. Rasterización y tiling (F2, F5, F6, F7)

| Fuente | Qué aporta | Dónde se discute |
|---|---|---|
| Laine & Karras, CUDARaster, HPG 2011 | software raster ≈ 2–8× más lento que HW pipeline; premisa del "swap" | R-3 I-04; FUSION-05; FUSION-07 |
| CuRast (TU Wien, 2026) | rasterizador compute solo gana con primitivas pixel-sized/instanced; no probado en GCN | R-3 I-04; FUSION-05; FUSION-07 |
| LucidRaster (OIT exacta, ~3× más lenta) | límite real del compute-blend | R-3 I-04; FUSION-05 |
| NT lib vk_lod_clusters (NVIDIA) | SW raster en compute para LOD | R-3 I-04; FUSION-07 |
| Vulkan TBR/IMR guide; radeonsi tile-swizzle; freedreno binning (Rob Clark) | binning HW-fused, no TBDR software | R-3 I-01/I-02; FUSION-02; FUSION-07 |
| AMD Vega DSBR (bin grid) | binning una-vía HW | R-3 I-01; FUSION-02; FUSION-07 |
| PowerVR TBDR / Apple Metal imageblocks / Mali TBR | tile stores dedicados (NO L2) — contraste con GFX8 | R-3 I-01/I-09; FUSION-02; FUSION-07 |
| Adreno FlexRender | switch IMR/TBR híbrido | R-3 I-02; FUSION-02 |
| DOOM Eternal 256×256 coarse tiles | culling por tiles, no render-tiling | FUSION-02; FUSION-07 |
| EmberGL, llvmpipe/SwiftShader, Atomontage/Outcast lineage | renderers SW/embedded (resource profile distinto) | FUSION-07 |

## 2. Memoria / caching (F2, F3, F7)

| Fuente | Qué aporta | Dónde se discute |
|---|---|---|
| GPUOpen "New Tech: An Introduction to DCC" (AMD) | DCC = compresión interna Color Block; UAV writes la deshabilitan; no ahorra PCIe | R-3 I-01/I-09; FUSION-03; FUSION-05 |
| radeonsi HTILE (Olšák 2016); hw.md HTILE 8×8 | unidades HW 8×8; DCC bloques 64/128/256 B | R-3 I-01; FUSION-02 |
| LinuxReviews DCC pages | fuente DEBIL/refutada (la citaba como "reduce PCIe") — corregida | FUSION-03; ASSUMPTION-AUDIT #20 |
| Mesa-dev thread (ADDR_HTILE_BLOCKSIZE/64 etc.) | granularidades reales HTILE/DCC | FUSION-02 |
| CUDA L2 Control / AutoScratch (MLSys'23) / GSPC-ICCAD'13 | residencia L2 = NVIDIA Ampere+; inexistente en GCN4 | R-3 I-09; FUSION-02; FUSION-03 |
| TTM/page migration; moverate=8 MB/s | límite real de migración VRAM⇄GTT | FUSION-03 |
| Talisman (SIGGRAPH'96); Regan&Pose'94; HPCA'19 Rendering Elimination; LIBRA (MICRO'24); vello/netrender/WebRender tile cache; EGL_KHR_partial_update; VK_KHR_incremental_present | re-render parcial / delta (I-02) | R-3 I-02; FUSION-02 |
| Walter 1999, Nehab 2007 (render caches) | render cache por tile | R-3 I-02; FUSION-02 |

## 3. Reprojección / temporalidad / predicción (F1, F6)

| Fuente | Qué aporta | Dónde se discute |
|---|---|---|
| TAA survey (Yang/Liu/Salvi) | jitter ≠ MV (separación de términos) | R-3 I-03; FUSION-01 |
| Hanika, "Fast Temporal Reprojection without MVs" (JCGT 2021) | reproyección solo-cámara vía correspondencias | R-3 I-03; FUSION-01 |
| Playdead TAA; GameTechDev TAA; FSR2 (ref) | motores separan _Jitter de _Velocity | R-3 I-03; FUSION-01 |
| Dumont 2003 (perceptually-based texture caching, "prediction camera"); UE5 SVT; idTech5; Igehy 1998 | predicción/prefetch de texturas por cámara — NO por jitter | R-3 I-06; FUSION-01 |
| AMD FFX Optical Flow (SEARCH/FILTER/UPSCALE; 8×8/24×24); AFMF; FSR3 (5700XT FG 2.2 ms@1080p); lsfg-vk | frame generation / OF stack — la idea exacta de F6 | R-3 I-07; FUSION-06 |
| Romera 2023 (optical flow embedded perf/energy) | coste OF en GPU pequeña | R-3 I-07; FUSION-06 |

## 4. Observabilidad / herramientas (F1, F4)

| Fuente | Qué aporta | Dónde se discute |
|---|---|---|
| RGP 2.x (RDNA-only) vs RGP 1.x-era / CodeXL (GCN) | viewer SQTT GCN **UNKNOWN**; no soporte runtime local | R-3 I-05; FUSION-04 |
| RADV `MESA_VK_TRACE=rgp` (source-level SQTT); rgp-inspect (gfx1201); GPUVis; RenderDoc; gfxreconstruct; api_dump; GPUPerfAPI v3.17/v3.11.1 (catalog) | infra de captura ATG; runtime GFX8 y catálogo ASIC `UNKNOWN` | R-3 I-05; FUSION-04 |
| SPM (gfx9+/RDNA) — **no confirmado gfx8** | contadores por stream | FUSION-04 |
| Otterness & Anderson RTSS'21 (ACE/HWS scheduling) | concurrencia async GCN/RDNA | R-3 I-10; FUSION-06 |
| Otterness. DagsterSchedule | scheduling (cita de soporte) | FUSION-06 |

## 5. Control-loop / gobernanza (F4)

| Fuente | Qué aporta | Dónde se discute |
|---|---|---|
| Consolas DRS (Diablo III X1X/PS4P); Intel DRR whitepaper; Unity HDRP HDDynamicResolution; Unreal DRS; MVP++ + dynamic resolution | governor frametime-feedback = estándar enviado | R-3 I-08; FUSION-04 |
| He/MobiCom 2015; Nixon/HotPower 2014; Denes/TOG 2020 | oscilación/overshoot de gobernadores | R-3 I-08; FUSION-04 |
| Radeon Boost / RSR / Magpie | heuristic-based scaling (no counters) | R-3 I-08; FUSION-04 |

## Notas de reconciliación
1. **Fuentes idénticas** entre R-3 (ideas) y R-3.1 (fusiones): CUDARaster/CuRast/LucidRaster (I-04 ⇄ F5),
   TAA survey + Hanika (I-03 ⇄ F1), FFX OF/AFMF/FSR3 (I-07 ⇄ F6), DCC/HTILE (I-01/I-09 ⇄ F2/F3), freedreno/
   DSBR/TBDR (I-01 ⇄ F2/F7), DRS/governer (I-08 ⇄ F4), ACE/scheduling (I-10 ⇄ F6). El índice consolida sin
   duplicar.
2. Una fuente (LinuxReviews DCC) fue **degradada/refutada** durante R-3.1 (afirmaba que DCC reduce PCIe);
   se documenta la corrección en ASSUMPTION-AUDIT.
3. **Patentes NO auditadas** (igual que en R-3): ninguna afirmación de novedad/se basó en ausencia de
   patentes. Mantener como pendiente transversal.
4. URLs/citas completas viven en los README de cada idea de `projects/` (R-3); este índice solo agrupa.
