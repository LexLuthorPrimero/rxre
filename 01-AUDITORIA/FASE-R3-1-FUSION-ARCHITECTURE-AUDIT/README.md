# FASE R-3.1 — FUSION ARCHITECTURE AUDIT

> **Directorio:** `experiments/FASE-R3-1-FUSION-ARCHITECTURE-AUDIT/`
> **Fase:** FASE R-3.1 — FUSION ARCHITECTURE AUDIT (CAPA ESTRATÉGICA FASE R)
> **Fecha de cierre:** 2026-09-22
> **Modo:** **SOLO LECTURA (READ-ONLY)** — auditoría documental + investigación web. Sin modificaciones de
> sistema (Mesa/RADV/kernel/firmware/VBIOS/BIOS), sin registros ni contadores, sin PowerPlay, sin benchmarks
> nuevos, sin instalaciones, sin modificar MASTER-PLAN. NADA de esto es "implementación".

---

## Alcance
Auditoría de las **7 fusiones arquitectónicas** candidatas heredadas de FASE R-3 (ideas I-01…I-10 agrupadas),
clasificando cada premisa del enunciado, cotejando prior art (R-3 ⇄ R-3.1) y diseñando experimentos de
falsación **sin ejecutarlos**.

## Las 7 fusiones auditadas

| ID | Fusión | Veredicto (resumen) |
|---|---|---|
| FUSION-01 | "Jitter = doble consumidor" (reproyección + predicción de texturas) | **[NEEDS PRECONDITION]** observabilidad primero; jitter NO puede sustituir motion vectors |
| FUSION-02 | "El tile es la unidad atómica" | **[REJECTED/FALSIFIED]** versión fuerte (residencia L2, unidad 32×32); sobrevive tile lógico app-side |
| FUSION-03 | "Invertir la jerarquía de memoria" | **[NEEDS PRECONDITION]** mediciones de bandwidth real; paridad BW con VRAM contradicta |
| FUSION-04 | "El sistema se auto-observa y se auto-ajusta" | governor read-only **[READY FOR FUTURE EXPERIMENT]**; contadores **[BLOCKED]** (autorización) |
| FUSION-05 | "Bypass de la unidad saturada (ROP→compute)" | **[REJECTED/FALSIFIED]** como mejora (topología GCN4, 32 SP/ROP, DCC/HTILE perdidos); pieza async → BERRETA |
| FUSION-06 | "Reconstrucción completa en compute" | **[REJECTED/FALSIFIED]** en 1080p (presupuesto); **[RESEARCH ONLY]** calibración 540p/720p (FASE P) |
| FUSION-07 | "Mini-engine" (2+3+6) | **[BLOCKED / RESEARCH ONLY]** conceptual, depende de las falsadas; combinación POTENTIALLY NOVEL |

## Prioridades de investigación (no decisiones de implementación)

1. **READY FOR FUTURE EXPERIMENT:** FUSION-04 (governor read-only, EXP-F4-A).
2. **NEEDS PRECONDITION:** FUSION-01 (EXP-F1-A observabilidad), FUSION-03 (EXP-F3-A bandwidth real).
3. **READY como sub-pieza:** FUSION-05 → co-scheduling async con BERRETA (ASY-01).
4. **REJECTED/FALSIFIED:** FUSION-02, FUSION-05 (fuerte), FUSION-06 (1080p).
5. **BLOCKED (autorización):** todo lo que use contadores D-3 (F2 residencia, F4 counter-driven, F5 falsación).

## Documentos de esta fase

| Archivo | Contenido |
|---|---|
| `FUSION-01-JITTER-DUAL-CONSUMER.md` | Auditoría F1 |
| `FUSION-02-ATOMIC-TILE.md` | Auditoría F2 |
| `FUSION-03-INVERTED-MEMORY-HIERARCHY.md` | Auditoría F3 |
| `FUSION-04-CLOSED-LOOP-ORCHESTRATOR.md` | Auditoría F4 |
| `FUSION-05-UNIT-BYPASS.md` | Auditoría F5 |
| `FUSION-06-COMPUTE-RECONSTRUCTION.md` | Auditoría F6 |
| `FUSION-07-MINI-ENGINE.md` | Auditoría F7 |
| `ASSUMPTION-AUDIT.md` | Auditoría de 20 premisas (VERIFIED…REQUIRES EXPERIMENT) |
| `NOVELTY-MATRIX.md` | Novedad técnica/combinación/aplicación por fusión |
| `FEASIBILITY-MATRIX.md` | Viabilidad end-to-end |
| `DEPENDENCY-MATRIX.md` | Dependencias (D-3, layer, Mesa, kernel, RX-Compression, Ghost, BERRETA, Orquestador) |
| `IMPLEMENTATION-LAYER-MATRIX.md` | Capa de implementación |
| `EXPERIMENT-ROADMAP.md` | Diseños EXP-F1-A…F7 (F5-A mínimo) — NO ejecutados |
| `PRIOR-ART-INDEX.md` | Índice consolidado R-3 ⇄ R-3.1 |
| `R3-1-MASTER-REPORT.md` | Informe final (10 preguntas del consejo) |

## Reglas aplicadas (checklist)
- Ninguna premisa se tomó como hecho; todo se clasificó en ASSUMPTION-AUDIT.
- Ningún experimento se ejecutó; quedan SOLO como diseños (EXPERIMENT-ROADMAP).
- Ninguna idea se declaró "PROVEN NOVEL"; presencia de incertidumbre = NOVELTY UNKNOWN.
- MASTER-PLAN no fue modificado (solo se propusieron piezas en R-3).
- MASTER-RESEARCH-STATUS se actualiza al cierre de la fase (v2.7).
- Los Event IDs de R-0 siguen sin equivaler autorización de programación de contadores.