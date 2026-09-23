# FUSION 06 — "RECONSTRUCCIÓN COMPLETA EN COMPUTE"

> **Archivo:** `FUSION-06-COMPUTE-RECONSTRUCTION.md`
> **Fase:** FASE R-3.1 — FUSION ARCHITECTURE AUDIT
> **Fecha:** 2026-09-22 — READ-ONLY
> **Categoría de fusión:** BERRETA + optical flow + async auxiliary + TAA jitter
> Model: Frame N ; Compute: Frame N + Frame N−1 → optical flow → reproyección → frame intermedio N+0.5

---

## 1. Separación de términos (obligatoria, del enunciado)

| Término | Definición | Estado en prior art |
|---|---|---|
| Optical flow | campo de flujo denso estimado (bloque / LK) | **amdgpu ∈ compute** variando (Romera'23; FFX Optical Flow exacto: SEARCH/FILTER/UPSCALE, bloques 8×8, SAD 24×24/256) |
| Motion estimation | coincidencia de bloques (familia SAD/SSD) | FSR3/AFMF, lsfg-vk lo hacen en shaders |
| Reprojection | re-mapeado historia→actual con depth/MV | Hanika'21 (sin MV usa correspondencias); TAA estándar |
| Frame interpolation | warp/blend de 2 frames → N+0.5 | AFMF/FSR3 = productos enviados |
| Frame generation | sintetizar frames NO renderizados | FDX/AFMF/lsfg — incluido el "F" que no es render real |
| Temporal reconstruction | calidad temporal (TAA/TSR) | distincto de FG; NO confundir |

**Métrica obligatoria:** REAL FPS, GENERATED FPS, frame time, displayed FPS, latency, GPU util, power,
image quality — separadas siempre (Lab K).

## 2. Auditado: concurrencia async en GCN4

- **ACE + HWS multi-cola en GCN4 = VERIFIED** (Polaris whitepaper: "ACE ACE / HWS / GRAPHICS CP / HWS / ACE
  ACE"; scheduling << Otterness & Anderson RTSS'21).
- **Número de ACE habilitados en Polaris12 (Lexa): UNKNOWN** (sin hoja pública Lexa; asumidas 2 en R-2 como
  low-end GCN4, but flagged).
- **Concurrencia sin degradación: PLAUSIBLE pero NO medido.** Mismos 8 CUs comparten wavefront slots; L2
  512 KB y path de 112 GB/s son compartidos. En workload fetch-bound con colgados de CUs/bandwidth, el
  overlap puede ocultar el coste; en workload que satura, degrada. cuantía = pregunta experimental (EXP-F6-A).

## 3. Auditado: presupuesto de tiempo en Polaris12

- No hay soporte FSR3/AFMF oficial para GCN (AFMF 2.x: RX 7000/6000, Ryzen 700M; FSR3: RX 5700+, RDNA1+).
  **AFMF/FSR3 en Polaris: CONTRADICTED por API** (las ideas corren igual — lsfg-vk — pero fuera de soporte).
- Coste estimado (aritmética, no medición): ~9–11 ms/frame@1080p (5700XT ≈ 40 CU/9.75 TFLOPS/448 GB/s vs
  nuestros 8 CU/1.2 TFLOPS/112 GB/s ≈ ×5 compute, ×4 BW). Frente a presupuesto de ~16.7 ms (60 fps), el
  OF+FI **consume el presupuesto completo** → solo viable a resoluciones reducidas (540p/720p) o con
  concurrency real descontada.
- Latencia: +1 frame real + tiempo de flujo ≈ +20–30 ms (pésimo para input, aceptable solo para video).

## 4. Falsabilidad (como sistema)

Falsa: "Polaris12 genera frame intermedio con coste oculto". Falsable con calibración: medir REAL fps, generado,
latencia, power y calidad en harness con kernels FFX-style a 540/720p, con y sin overlap async. El enunciado
"compute concurrente sin degradar graphics significativamente" = **PLAUSIBLE-UNMEDIRABLE** hasta EXP-F6-A.

## 5. Veredicto de fusión

- **RECONSTRUCCIÓN completa en compute** en Polaris12: **REJECTED/FALSIFIED** como feature de rendimiento en
  1080p (presupuesto y bandwidth), consentida solo como calibración educativa/documental (540p/720p) en la
  órbita de FASE P. 
- La **única parte plaus-blessed** es la concurrencia async medida (BERRETA/ASY-01) y el "reconstruction is
  perceptual, never throughput".
- **Novedad:** KNOWN VARIANT (= AFMF/FSR3/lsfg stack); concurrencia en low-end GCN4 sin medición =
  NOVELTY UNKNOWN.