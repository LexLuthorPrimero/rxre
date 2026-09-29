# ASSUMPTION-AUDIT — Auditoría de Premisas de las Fusiones

> **Archivo:** `ASSUMPTION-AUDIT.md`
> **Fase:** FASE R-3.1 — FUSION ARCHITECTURE AUDIT
> **Fecha:** 2026-09-22 — READ-ONLY
> **Estados:** VERIFIED · PARTIALLY VERIFIED · PLAUSIBLE · UNKNOWN · CONTRADICTED · REQUIRES EXPERIMENT
> **Regla:** ninguna premisa se aceptó como hecho; cada afirmación del enunciado se clasificó. Las que
> necesitan medir en HW, se listan como REQUIRES EXPERIMENT y NO se ejecutaron.

---

## 1. Auditoría línea por línea (premisas del enunciado)

| # | Premisa | Estado | Evidencia / mecanismo |
|---|---|---|---|
| 1 | "Los ROPs están saturados" | **REQUIRES EXPERIMENT** | Nunca medido con contadores en este proyecto (radeontop rop_busy es agregado, sin per-ROP). E3/E5 muestran MSAA-cost, no ROP-util. ROP-busy alto ≠ CU idle (PS corre antes del RBE en el mismo array CU). |
| 2 | "Las CUs están ociosas" | **PARTIALLY VERIFIED / CONTRADICTED según fase** | Fetch-bound (ES-01) → hay latencia y CU idle alosible. ROP-heavy → NO (PS ya usó los CUs). "CUs libres mientras graphics corre" como regla general = CONTRADICTED |
| 3 | "El color es el cuello de botella" | **UNKNOWN** | Sin contadores CB (bloqueado); E5b descartó ALU pero no aisló color vs depth vs MSAA-resolve |
| 4 | "32×32 RGBA = unidad natural del HW" | **CONTRADICTED (HW unit)** / KNOWN VARIANT (tile lógico) | GCN: raster 8×8, HTILE 8×8, DCC bloques 64/128/256 B; 32×32 es práctica de la industria (PowerVR/Mali/Adreno), NO una constante de GCN |
| 5 | "Un tile de 4 KB permanece en L2" | **UNKNOWN local** / source-level claim | CB/DB bypassa L2 está documentado para la familia GFX8, pero la confirmation en este ASIC es `UNKNOWN`; la ruta compute requiere medida |
| 6 | "512 KB de L2 permite mantener tiles residentes" | **CONTRADICTED como control local** | No hay API de residencia/pinning userspace confirmada; 512 KB no demuestra residency de framebuffer |
| 7 | "PCIe es el cuello dominante" | **PARTIALLY VERIFIED (host path)** / no universal | Gen2×4 ≈2.0 GB/s vs 96–112 GB/s nominal/estimado VRAM (×48–80); bandwidth VRAM real `UNKNOWN`; VIS-VRAM 256 MiB observational. |
| 8 | "GTT puede superar efectivamente al camino VRAM relevante" | **CONTRADICTED como paridad de bandwidth**; PARTIALLY VERIFIED para datos que ya cruzan PCIe | DCC es compresión interna-GPU (Color Block), no PCIe; TTM moverate 8 MB/s; GTT+compresión no cierra ×24–32. Solo re-lectura por L2 amortizada es defendible |
| 9 | "TAA jitter puede funcionar como motion vector" | **CONTRADICTED** | Jitter = offset subpixel de proyección; no codifica object motion ni disocclusion (TAA survey, Playdead separan _JitterUV de _Velocity; Hanika'21 usa correspondencias, no jitter) |
| 10 | "El jitter puede predecir qué texturas serán necesarias" | **PLAUSIBLE mecánicamente / NOVELTY UNKNOWN** | La predicción de texturas existe por cámara (Dumont'03, UE/idTech) pero NO está alimentada por jitter; el jitter apenas informa ≤1 px. Recuperación: cámara/matrices, no jitter |
| 11 | "Compute puede sustituir eficazmente trabajo de ROP" | **CONTRADICTED como ganancia** | CUDARaster 2–8× más lento que HW; UAV writes deshabilitan DCC (GPUOpen); depth-visible pierde compresión; en 32 SP/ROP el balance es el peor |
| 12 | "Compute queue está realmente libre durante graphics" | **CONTRADICTED como regla** / REQUIRES EXPERIMENT | ACE/HWS son family-level; nº ACEs, overlap y capacidad local son `UNKNOWN`. Las 8 CUs/L2/BW son compartidas; no se presupone queue libre. |
| 13 | "Polaris12 puede mantener suficiente concurrencia graphics+compute" | **PLAUSIBLE / UNKNOWN (sin medir)** | Estructura lo permite; número de ACE de Lexa desconocido (sin hoja pública); cuantía sin degradación NO medida |
| 14 | "Optical flow puede ejecutarse con suficiente margen" | **CONTRADICTED en 1080p** / PLAUSIBLE en 540p/720p | Est. 9–11 ms/frame@1080p vs presupuesto 16.7 ms; AFMF/FSR3 sin soporte GCN (API); latencia +20–30 ms |
| 15 | "Una Vulkan layer puede interceptar suficiente información" | **PARTIALLY VERIFIED** | Layers ven vkCmdPushConstants/descriptors/resources (VIL, RenderDoc). No hay metadata de jitter estándar → interpretación dependence del engine / heurística |
| 16 | "RGP no soporta Polaris12" | **PARTIALLY VERIFIED** | RGP 2.x = RDNA-only; la compatibilidad GCN-era de RGP 1.x/CodeXL es histórica y no confirma runtime/viewer GFX8 local. ROCm thread-trace no lista gfx8; SPM en GFX8 = `UNKNOWN`. |
| 17 | "Nadie implementó TBDR software sobre IMR" | **NOVELTY UNKNOWN** | No se encontró producto publicado; freedreno binning es HW-fused; no hay evidencia de ausencia |
| 18 | "Nadie construyó frame recorder equivalente para GFX8" | **UNKNOWN / gap parcial** | No se confirmó un viewer GFX8 en las fuentes auditadas; RGP 1.x podría cubrirlo, pero no se verificó. |
| 19 | "Nadie realizó closed-loop renderer basado en counters en PC" | **PARTIALLY VERIFIED (ausencia)** | Consolas = estándar; PC: DRS de motores + Radeon Boost/RSR (heurística, no counters); no encontrado governor counter-driven en PC desktop → NOVELTY UNKNOWN |
| 20 | "La combinación concreta de estas técnicas es nueva" | **NOVELTY UNKNOWN** | No encontrada la combinación exacta; componentes todos KNOWN; probar en DB/patentes antes de afirmar |

## 2. Premisas complementarias descubiertas durante la auditoría

| Premisa | Estado | Nota |
|---|---|---|
| "DCC reduce tráfico PCIe" | **CONTRADICTED (unsupported)** | GPUOpen lo atribuye al bandwidth interno GPU; LinuxReviews lo afirmaba sin fuente |
| "DCC activo para imágenes GTT" | **UNKNOWN** | si_dcc path para HOST_VISIBLE no device-local en GFX8 a verificar |
| "L2 es destino controlable" | **CONTRADICTED** | sin residencia/pinning; solo hints VM/flush |
| "Polaris12 tiene 2 ACE" | **UNKNOWN** | inherencia GCN4 low-end; sin hoja oficial Lexa |
| "RX550 = 8 CUs" | **VERIFIED local / con variante** | 512 SP (8 CU) confirmado en docs del proyecto; existe SKU RX550 640 SP (10 CU) — validar identidad física |

## 3. Resumen cuantitativo

- **VERIFIED:** 1 (PCIe host-predict) + hechos de sistema (PCIe Gen2×4, VIS 256 MB, GTT 6.2 GB, moverate).
- **CONTRADICTED:** 9 (4, 5, 6, 8, 9, 11, 12, 14, y DCC-PCIe) — la mayoría son los "fundamentos" de las
  fusiones F2/F3/F5/F6.
- **PARTIALLY VERIFIED:** 5 (2, 15, 16, 19, +RGP-era).
- **PLAUSIBLE:** 2 (10, 13).
- **UNKNOWN:** 5 (3, 18, ACE, DCC-GTT, combinación total).
- **REQUIRES EXPERIMENT:** 2 (1, 12) + las derivadas de medición (BW PCIe real, DCC-GTT).

## 4. Conclusión transversal
El grueso de las premisas que sostenían las fusiones **de la capa de hardware/memoria (F2, F3, F5, F6) fue
CONTRADICTED o degradado a UNKNOWN**, mientras que las premisas de **capa de aplicación/software (F1
observabilidad, F4 governor read-only, F7 como sistema) sobreviven condicionalmente**. Esto no decide qué
fusiones "ganan": documenta el estado de la evidencia tal como está.
