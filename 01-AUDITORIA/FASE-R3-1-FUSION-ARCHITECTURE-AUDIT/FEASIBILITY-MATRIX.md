# FEASIBILITY-MATRIX — Viabilidad técnica de las 7 fusiones

> **Archivo:** `FEASIBILITY-MATRIX.md`
> **Fase:** FASE R-3.1 — FUSION ARCHITECTURE AUDIT
> **Fecha:** 2026-09-22 — READ-ONLY
> **Estados:** HIGH / MEDIUM / LOW / UNKNOWN (categorías cualitativas justificadas, sin puntuaciones).

---

| Fusión | Evidencia existente | Viabilidad Vulkan | Dependencias no resueltas | Riesgo | Falsabilidad | Estado de prioridad |
|---|---|---|---|---|---|---|
| **F1 — jitter dual** | PARTIALLY VERIFIED (observación midió los layers); observación funciona | MEDIUM (layer/observación); MEDIUM (cooperation app para jitter) | paridad de jitter→matriz; interpretación engine-specific | MEDIO (ghosting, disocclusion, falla en objetos dinámicos) | ALTA (error de reproyección y working-set hit-rate medibles) | **NEEDS PRECONDITION** (observabilidad primera) |
| **F2 — tile atómico** | CONTRADICTED (residencia, unidad); sin medición cuantitativa | MEDIUM (binning app-side es posible) | residencia L2 (irresoluble en GFX8), DCC/HTILE driver-level | ALTO (sync/barriers; DCC invalidado) | ALTA (frametime microbenchmark 16/32/64) | **REJECTED/FALSIFIED** (versión fuerte) + tile-app **RESEARCH ONLY** |
| **F3 — memoria invertida** | VERIFIED (bandwidths); CONTRADICTED (paridad) | MEDIUM | medición BW real local; DCC-on-GTT UNKNOWN; moverate | MEDIO (contaminación de medición; GTT eviction) | ALTA (comparación GTT-vs-VRAM frametime/power) | **NEEDS PRECONDITION** (mediciones BW) |
| **F4 — auto-observación** | VERIFIED (telemetría read-only); contadores PARTIALLY VERIFIED | HIGH (governor app-side y layer con CAPTURA); contadores → autorización | de los contadores (D-3) y fixture cuantitativo | MEDIO (oscilación, actuación no lineal, lag de power) | ALTA (A/B governor vs fixed quality; p99) | governor read-only: **READY FOR FUTURE EXPERIMENT**; sistemas: **BLOCKED** (autorización) |
| **F5 — bypass ROP** | CONTRADICTED (mecanismo); constantes publicadas | MEDIUM (compute es factible a nivel API) | nada por resolver; es el premisa lo que falla | ALTO (bandwidth, atomics, DCC perdido) | ALTA (EXP-F5-A mínimo) | **REJECTED/FALSIFIED** como mejora; solo pieza async → BERRETA (**READY**) |
| **F6 — reconstrucción** | CONTRADICTED (presupuesto 1080p); PLAUSIBLE (overlap) | MEDIUM (FFX-style en compute; API OK) | concurrencia real por medir (11) | ALTO (latencia, power, artífices) | ALTA (calibración REAL/GENERADO/latencia) | **REJECTED/FALSIFIED** (1080p); **RESEARCH ONLY** (calibración 540/720p, FASE P) |
| **F7 — mini-engine** | CONTRADICTED en sus pilares; POTENTIALLY NOVEL la combinación | LOW-MEDIUM (sistema completo) | F5/F6 (falsadas) + mediciones F3 + autorizaciones | MUY ALTO (colapso por presupuesto de recursos) | ALTA por piezas (nunca por "motor" entero) | **BLOCKED / RESEARCH ONLY** (largo plazo) |

## Lecturas
- **F4 (governor read-only)** es la única con viabilidad HIGH end-to-end y sin dep-muerta: se puede ejecutar
  hoy con telemetría read-only, sin tocar el sistema.
- **F1** es viable pero arrastra una precondition de observabilidad; **F3** arrastra mediciones.
- **F2/F5/F6** quedan en REJECTED/FALSIFIED en sus versiones fuertes; solo sobreviven sub-piezas (tile app,
  async co-scheduling, calibración).
- **F7** depende de las falsadas → BLOCKED; solo podrá re-evaluarse si F2(tile)/F6 (calibración) dan señales
  positivas inesperadas.