# R-3 FEASIBILITY MATRIX — Viabilidad de las 10 ideas en Polaris12

> **Archivo:** `R3-FEASIBILITY-MATRIX.md`
> **Fase:** FASE R-3 — ORIGINAL IDEAS, NOVELTY AUDIT & RESEARCH CANDIDATES
> **Fecha:** 2026-09-22 — Modo SOLO DOCUMENTAL
> **Clasificación:** [INVESTIGADO]. Estados permitidos: HIGH / MEDIUM / LOW / UNKNOWN.
> Definiciones por eje: ver sección 2.

---

## 1. Matriz de viabilidad

| ID | IDEA | COMPUTE COST | MEMORY COST | BANDWIDTH COST | IMPLEMENTATION COMPLEXITY | DRIVER COMPLEXITY | VULKAN COMPLEXITY | REVERSIBILITY | MEASURABILITY | POLARIS12 FIT | RESEARCH VALUE |
|---|---|---|---|---|---|---|---|---|---|---|---|
| I-01 | TBDR emulation on IMR | HIGH | HIGH | HIGH (software tile añade passes y pierde DCC/HTILE si va por compute) | HIGH | LOW (userland/con layer) | MEDIUM | HIGH (sin contadores: frametime/power señales indirectas) | LOW (CB/DB bypass L2) | LOW (duplica mecanismo HW existente: HTILE+DCC+RB tile-cache) | LOW |
| I-02 | Temporal Tile Delta Reuse | LOW (compare-pass) | MEDIUM (tile maps + historia) | MEDIUM (comparación lee frame previo) | LOW (harness) / HIGH (motor) | LOW | MEDIUM (readback/compute compare; renderArea parcial) | HIGH | HIGH (frametime+poder A/B; regiones visibles) | MEDIUM-HIGH (fill-limited 512 sh; DCC/HTILE ya cubren BW) | MEDIUM (valor sobre todo en escena estática) |
| I-03 | TAA jitter as reprojection signal | LOW (~0.3–0.5 ms @720p depth+matmul) | LOW | LOW | LOW | LOW | LOW | HIGH | HIGH | HIGH (como tile-lock de I-02) | MEDIUM (herencia: no es "sin MVs" para objetos) |
| I-04 | ROP offload to compute | HIGH (visibilidad + depth + blend + MSAA en compute) | HIGH (SSBO/UAV) | HIGH (pierde L2-bypass + DCC/HTILE; tráfico estrictamente peor) | HIGH | LOW (app-side) | HIGH | MEDIUM (riesgo de estado intermedio si se experimenta) | MEDIUM (constantes publicadas ya la refutan en este tier) | LOW (32 SP/ROP; CUs no libres) | LOW (negativa de alta calidad; piezas async aprovechables) |
| I-05 | GFX8 Frame Recorder | MEDIUM (decoder SQTT v2.2) | MEDIUM | MEDIUM | MEDIUM (phasable A–C) | MEDIUM (runtime SQTT en RADV no confirmado) | LOW (captura runtime `UNKNOWN`) | HIGH | HIGH (read-only; source-level no basta) | `UNKNOWN` (viewer/decoder GFX8 no confirmado) | HIGH (herramienta: solo tras capability audit) |
| I-06 | Predictive Ghost Cache | LOW (warm-up service) | MEDIUM (working set adicional) | MEDIUM-HIGH (prefetch puede competir con fetch real → ES-01 ya BW-bound) | MEDIUM-HIGH (servicio + heurística cámara) | HIGH (no existe API de prefetch/residencia L2 en GCN4; PRT inestable en Polaris) | MEDIUM | HIGH | MEDIUM (p99 de fetch medible; contaminación difícil de aislar) | MEDIUM (a nivel software warm-up) / LOW (a nivel HW-cache) | MEDIUM (delta real sobre engines reactive es desconocido) |
| I-07 | Async Optical Flow Frame Generation | HIGH (OF+FI ≈ 8–20 ms@1080p extrapolado FSR3) | HIGH (working set +100–170 MB) | HIGH (512 sh; 96–112 GB/s estimado, real `UNKNOWN`) | MEDIUM-HIGH (integrar FFX) | LOW | MEDIUM | HIGH (playa separada de Lab K; nunca entra a benchmarks reales) | HIGH (separar REAL/PERCIBIDO/latencia/poder) | `UNKNOWN` (no se presupone overlap/CU reservation) | MEDIUM (educativo; calibración 540p/720p) |
| I-08 | Closed-Loop Quality Governor | LOW (controller) | LOW | LOW (actúa sobre escala) | LOW-MEDIUM | LOW (read-only) | LOW | HIGH (sin writes) | HIGH (frametime + power + DPM read-only) | HIGH (loop sin contadores; incógnita H2: monotonicidad bajo DPM) | MEDIUM-HIGH (educativo + posible hallazgo DPM-quality) |
| I-09 | L2-Resident Internal Resolution | HIGH (como producto) / LOW (sub-variante compute) | MEDIUM | HIGH (framebuffer nunca en L2 en CB path) | HIGH (sin API de residencia) | HIGH (requeriría control que GCN4 no expone) | MEDIUM | MEDIUM | LOW (sin contadores L2 en radeontop; SPM bloqueado) | LOW (headline imposible) | LOW (negativa determinada por topología; sub-reclamo marginal) |
| I-10 | Async Auxiliary Renderer | MEDIUM (variante de workload) | MEDIUM | MEDIUM-HIGH (async BW compite con path ya saturado) | MEDIUM (como variante de BERRETA/ASY-01) | LOW | LOW (Vulkan async queue logical; ACE/overlap `UNKNOWN`) | HIGH | HIGH (runner K puede medir overlap via timeline) | MEDIUM (ACE family-level; count `UNKNOWN`) | MEDIUM (cuantificar overlap real, sin asumir 2 ACE) |

## 2. Definición de ejes

- **COMPUTE COST**: coste de cómputo adicional (shaders/waves) sobre las 8 CUs (512 SP).
- **MEMORY COST**: bytes adicionales de VRAM/GTT (buffers, historias, working sets).
- **BANDWIDTH COST**: tráfico DRAM adicional neto (96–112 GB/s nominal/estimado; real `UNKNOWN` para 128-bit GDDR5).
- **IMPLEMENTATION COMPLEXITY**: esfuerzo de aplicación/rendering.
- **DRIVER COMPLEXITY**: cuánto depende de funciones de driver/Mesa inexistentes o inestables.
- **VULKAN COMPLEXITY**: cuánto depende de extensiones/técnicas Vulkan avanzadas (renderArea parcial,
  async queues, UAV atomics, readback).
- **REVERSIBILITY**: facilidad de revertir sin dejar cambios en el sistema.
- **MEASURABILITY**: si el efecto puede medirse con la telemetría read-only actual (frametime, power,
  clocks, kalm) y runner K, SIN contadores HW.
- **POLARIS12 FIT**: adecuación a la topología real (L2-bypass, 8 CUs, 16 ROPs, fetch-bound ES-01).
- **RESEARCH VALUE**: valor potencial para el proyecto (no para el mundo).

## 3. Observaciones de viabilidad

1. **La medición sin contadores HW discrimina las ideas**: I-01/I-09/I-04 tienen measurability LOW porque
   su tesis se apoya en tráfico de memoria que la telemetría read-only no ve (CB/DB bypass L2).
2. **Las negativas baratas están donde la topología ya la determinó**: I-04 (32 SP/ROP), I-09/I-01
   (L2-bypass), I-07 (ancho de banda/power). No requieren experimento para ser consideradas desfavorables;
   solo una medición documental puntual las confirmaría.
3. **I-05 e I-08 son las únicas con HIGH en todos los ejes habilitadores** (reversibilidad, medibilidad,
   fit); I-05 además habilita la medición del resto.
4. **UNKNOWN no se usó**: cada eje se pudo estimar desde evidencia publicada y local. Los UNKNOWN que
   quedan son de *cuantificación* (¿cuánto es el overlap real de queues/ACEs, con count `UNKNOWN`?), marcados en los
   EXPERIMENT-DESIGN como preguntas de medición, no como incógnitas de viabilidad estructural.
