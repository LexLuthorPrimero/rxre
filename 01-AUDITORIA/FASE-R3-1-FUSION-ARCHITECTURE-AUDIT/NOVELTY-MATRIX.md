# NOVELTY-MATRIX — Novedad de las 7 fusiones (técnica / combinación / aplicación)

> **Archivo:** `NOVELTY-MATRIX.md`
> **Fase:** FASE R-3.1 — FUSION ARCHITECTURE AUDIT
> **Fecha:** 2026-09-22 — READ-ONLY
> **Estados:** KNOWN · KNOWN VARIANT · RELATED PRIOR ART · PARTIALLY NOVEL · POTENTIALLY NOVEL ·
> NOVELTY UNKNOWN · CONTRADICTED BY PRIOR ART. Nunca "PROVEN NOVEL".

---

| Fusión | A. Componentes | B. Combinaciones conocidas | C. Arquitectura específica propuesta | D. Aplicación Polaris12/low-end | E. Novedad real |
|---|---|---|---|---|---|
| **F1 — jitter dual-consumer** | KNOWN (TAA jitter; reproyección solo-cámara; predicción de texturas por cámara) | KNOWN VARIANT (reproyección + TAA en motores; predicción por cámara en UE/Unity) | KNOWN VARIANT parcial: alimentación conjunta (reproyección + textura) desde UNA señal jitter | No encontrado el combo exacto en FUENTE pública; NS. específica + restrictiva | **KNOWN VARIANT** (núcleo) / **POTENTIALLY NOVEL** solo en la alimentación conjunta / **NOVELTY UNKNOWN** |
| **F2 — tile atómico** | KNOWN (TBDR, tiling HW, partial redraw, L2 residency en Ampere+, DCC/HTILE) | KNOWN VARIANT (binning HW; bucket rendering; partial updates) | CONTRADICTED (tile único común) — agrupación artificial de granularidades; 32×32 ≠ unidad HW | NOVELTY UNKNOWN (medida software-tiling Polaris12 no publicada) | **CONTRADICTED BY PRIOR ART** (residencia L2) + tile lógico app = **KNOWN VARIANT** |
| **F3 — memoria invertida** | KNOWN (DCC, GTT, TTM, page migration, compresión delta) | KNOWN (manejo de working set, sparse streaming en engines) | PLANIDÉ CONTRADICTED en paridad de bandwidth; sub-claim hot-set real = RELATED PRIOR ART | Aplicación a GCN4 low-end no documentada | **CONTRADICTED** (paridad BW) / hot-set app = **RELATED PRIOR ART** / aplicación = **NOVELTY UNKNOWN** |
| **F4 — auto-observación** | KNOWN (contadores GCN, DRS/governor, frame recorder, orchestrator) | KNOWN (consolas: contour + governor; PC: DRS de motores) | Governor frametime PID = KNOWN VARIANT; "counter-driven en PC desktop" no encontrado | Aplicación read-only GCN4 = no documentada | **KNOWN VARIANT** (loop) / contadores-PC = **NOVELTY UNKNOWN** (ausencia parcial) |
| **F5 — bypass unidad saturada** | KNOWN (software raster, compute blending, async) | KNOWN VARIANT (CUDARaster = 2011; CuRast'26; Doom ET binning) | CONTRADICTED en premisa de ganancia (misma array CU; 32 SP/ROP; DCC/HTILE perdidos) | Sin medición GCN publicada del swap | **KNOWN VARIANT** / premisa **CONTRADICTED BY PRIOR ART** (mecanismo) |
| **F6 — reconstrucción en compute** | KNOWN (optical flow est., reprojección, interpolación) | KNOWN VARIANT (= AFMF/FSR3/lsfg, productas enviadas) | Overlap async en GCN4 = PLAUSIBLE sin medir | GCN sin soporte oficial (AFMF 2.x/FSR3 = RDNA) | **KNOWN VARIANT** (idéntica a stack AMD) / concurrency low-end = **NOVELTY UNKNOWN** |
| **F7 — mini-engine** | KNOWN (todos los componentes) | KNOWN (CuRast compute-raster; voxeles; tile-based embedded: EmberGL) | Combinación completa TBDR-SW+FG+memoria invertida en GCN4 low-end | No encontrada públicamente (a verificar en patentes) | **POTENTIALLY NOVEL** (combinación, sin confirmar) — componentes KNOWN |

## Lecturas
- **Ninguna fusión es "PROVEN NOVEL".** Donde no se halló prior art, se usó NOVELTY UNKNOWN.
- **F7** es la única candidata a NOVELTY real, y solo *por combinación* — sujeto a chequeo de patentes y a que
  F5/F6 no sean falsadas del todo.
- Las fusiones cuyo núcleo es "evidencia de topología" (F2, F5, F6) quedan en CONTRADICTED; su "novedad" no
  se evalúa como contribución sino como afirmación refutada.