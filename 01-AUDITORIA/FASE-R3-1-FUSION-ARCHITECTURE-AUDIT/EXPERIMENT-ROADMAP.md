# EXPERIMENT-ROADMAP — Diseño de experimentos futuros (SOLO DISEÑO, no ejecutar)

> **Archivo:** `EXPERIMENT-ROADMAP.md`
> **Fase:** FASE R-3.1 — FUSION ARCHITECTURE AUDIT
> **Fecha:** 2026-09-22 — READ-ONLY
> **Regla:** cada experimento queda diseñado con hipótesis falsable, variables, controles, baseline,
> metricas y rollback. **NINGUNO se ejecuta.** Los que involucren contadores/sysfs-writes requieren
> autorización previa (D-3/marco L) y se marcan explícitamente.

---

## EXP-F1-A — Observabilidad del jitter (precondición de F1)

- **Hipótesis:** un harness Vulkan propio genera TAA-jitter deliberado; un intérprete (fuera del harness) que
  observa push constants/matrices recupera el offset de jitter con error < 0.01 px.
- **VI:** presencia del jitter (sí/no); **VD:** error de reconstrucción del offset, ratio de detección.
- **Controles:** harness determinista; matrices de cámara conocidas. **Baseline:** reconstrucción del offset
  vía delta de matriz (ground truth).
- **Workload:** harness sintético haría-frame (WORKLOAD-SINTETICO F2/estática). **Duración/repeticiones:**
  sesión corta, ≥30 runs; **métricas:** MAE de reconstrucción, tasa de falsos positivos.
- **Éxito:** MAE < 0.01 px, FP < 1%. **Falsación:** MAE > 0.1 px → layer no puede observar jitter en la
  práctica. **Riesgos/rollback:** read-only; sin instalación (god: si requiere layer out-of-tree, autorizar).

## EXP-F2-A — Granularidad de tile lógico (16/32/64) en Polaris12

- **Hipótesis:** el binning de render por tiles de 32×32 (vs 16/64 y fullscreen) cambia el frametime del
  filler en escena controlada llena de overdraw, y el cruce coincide con bloques DCC/HTILE (8×8).
- **VI:** tamaño de tile y renderArea; **VD:** frametime, power, rate de fill (read-only).
- **Controles:** misma escena, mismo orden de draw, sin post-procesado. **Baseline:** fullscreen render.
- **Workload:** zoom-in/poly-ético controlado; **reps ≥15; métricas:** μ, p99, power W. **Éxito:**
  diferencia >3% en p99 reproducida. **Falsación:** sin diferencia → "tile" no es relevante para
  frametime en este GPU.
- **Riesgo/rollback:** read-only; sin cambios de estado.

## EXP-F3-A — Bandwidth real PCIe/GTT/VRAM de esta máquina (confirmación de F3)

- **Hipótesis:** el payload real PCIe Gen2×4 ≈ <2 GB/s; VIS/GTT paths difieren de forma medible.
- **VI/VD:** transfer size → alcanzado GB/s (GTT, VIS, VRAM, DMA); VA: moverate (default).
- **Método:** `debugfs:/amdgpu_benchmark` (read-only kernel debugfs, no write de estado), gpu-pcie-bench-style
  (read-only), en ventana autorizada (debugfs read = permitido).
- **Éxito:** números empíricos para reemplazar estimaciones; **Falsación (del supuesto):** si GTT real ≈
  ~2 GB/s y VIS ≈ similar → corrobora el modelo; si GTT o VIS sorprendentemente <, ajustarlo.
- **Riesgo/rollback:** reads only; no tocar moverate ni VM.

## EXP-F4-A — Governor frametime-feedback read-only (sin contadores)

- **Hipótesis H2:** frametime vs render-scale es **no-lineal bajo DPM** (la curva presenta un umbral); un
  governor con histéresis mantiene p99 ≤T sin caer en oscilación.
- **VI:** escala de render; **VD:** frametime μ/p99, power leído en sysfs (read-only), etiqueta DPM
  (read-only).
- **Controles:** regime DPM fijo declarado; workload GPU-bound (harness con knob de escala); **baseline:**
  calidad fija.
- **Reps ≥30 por punto; metrics: μ/p99/overshoot.** **Éxito:** governor reduce p99 ≥15% vs fijo en
  workstation, con IM seconds de oscilación nula. **Falsación:** p99 peor o inestable → gobernanza no aporta.
- **Riesgo/rollback:** read-only absoluto; sin writes.

## EXP-F5-A — Bypass de unidad saturada (FUSIÓN 5 — EXPERIMENTO MÍNIMO OBLIGATORIO)

Pregunta a responder (sin asumir respuesta):
> ¿Existe algún workload en Polaris12 donde trasladar trabajo de framebuffer/fixed-function hacia compute
> produzca una mejora neta?

- **Hipótesis (falsable):** existe una configuración (resolución, blend, MSAA, overdraw) donde:
  compute-path (render→SSBO/UAV→blit) vence a graphics-path (render→attachment) en FPS/p99, con corrección
  de DCC-status y bandwidth.
- **VI:** path (A graphics vs B compute) × blend mode (none/ONE-ONE/alpha) × MSAA (1/4) × resolución
  (720p/1080p); **VD:** FPS, frametime, power; **VA:** utilización radeontop (read-only): rop_busy, cu_busy.
- **Controles:** mismo draw-count, mismo shader de base, sin vsync; **baseline:** path A idéntico escena.
- **Workload:** cuadrado lleno alpha-blend (fill-rate stress); **réplicas ≥30.** **Métricas:** μ/p99, W.
- **Éxito:** compute-path ≥ +10% FPS en AL MENOS una config, reproducido (2 sesiones independientes).
- **Falsación:** si en ninguna config compute gana (o gana solo donde ROP≈0 → no es saturación) →
  CONFIRMADO el veredicto REJECTED con datos locales. **Riesgos:** medir mal el "busy"; incluir en el
  report la banda de DCC-status para evitar falsos +.
- **Rollback:** nada se escribe; requiere runs autorizados (benchmark harness).

## EXP-F6-A — Concurrencia graphics+compute en 8 CUs (precondición de F6)

- **Hipótesis:** un kernel compute ligero lanzado cada frame (ACE) se ejecuta sin degradar >N% el frametime
  de graphics, cuando la escena es fetch-bound; en escena fill-bound sí degrada.
- **VI:** charge computación (0/light/heavy) × tiipo escena (fetch/fill); **VD:** frametime graphics, util,
  power. **Control:** mismo graphics; **baseline:** sin compute. **Reps ≥30.**
- **Éxito:** en fetch-bound, degradación <5%. **Falsación:** degradación >10% en ambos → concurrencia
  inútil aquí. **Rollback:** read-only.

## EXP-F7-ROADMAP (arquitectura, no experimento unitario)
Nada se ejecuta como "mini-engine": se valida por piezas (EXP-F2-A, F3-A, F6-A) y recién entonces se
reconsidera la combinación. Criterio de entrada a F7: al menos dos piezas F2/F3/F6 con señal positiva.