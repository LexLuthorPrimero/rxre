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

- **ACE + HWS multi-cola en GCN4 = DOCUMENTADO A NIVEL FAMILIA/source-level** (Polaris
  whitepaper y fuentes de scheduling); no confirma la configuración runtime de Lexa.
- **Número de ACE habilitados en Polaris12 (Lexa): `UNKNOWN`** (sin hoja pública/local;
  no se asumen 2).
- **Concurrencia sin degradación: `UNKNOWN` / no medido.** Las mismas 8 CUs comparten
  wavefront slots; L2 512 KB y bandwidth VRAM nominal/estimado 96–112 GB/s (real
  `UNKNOWN`) son compartidos. La cantidad de overlap es una pregunta experimental
  (`EXP-F6-A`), no una capacidad presupuesta.

## 3. Auditado: presupuesto de tiempo en Polaris12

- No hay soporte FSR3/AFMF oficial para GCN (AFMF 2.x: RX 7000/6000, Ryzen 700M; FSR3: RX 5700+, RDNA1+).
  **AFMF/FSR3 en Polaris: CONTRADICTED por API** (las ideas corren igual — lsfg-vk — pero fuera de soporte).
- Coste estimado (aritmética, no medición): ~9–11 ms/frame@1080p (5700XT ≈ 40 CU/9.75 TFLOPS/448 GB/s vs
  nuestros 8 CU/1.2 TFLOPS/96–112 GB/s nominal/estimado; bandwidth real `UNKNOWN`). Frente a
  ~16.7 ms (60 fps), el OF+FI **podría consumir el presupuesto completo**; la viabilidad y
  el overlap real quedan `UNKNOWN`.
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
