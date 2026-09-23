# R3-MASTER-PLAN-INTEGRATION-PROPOSAL — Propuesta de Integración R-3 (sin modificar MASTER-PLAN)

> **Archivo:** `R3-MASTER-PLAN-INTEGRATION-PROPOSAL.md`
> **Fase:** FASE R-3 — ORIGINAL IDEAS, NOVELTY AUDIT & RESEARCH CANDIDATES
> **Fecha:** 2026-09-22 — Modo SOLO DOCUMENTAL
> **Clasificación:** [PROPUESTA]. **MASTER-PLAN NO fue modificado** (regla de la fase: la propuesta se
> presenta antes de cualquier integración; nada se inserta automáticamente).

---

## 1. Principio de la propuesta

Solo las ideas con (a) prior art que permita una variante legítima, (b) viabilidad no contradicta por la
topología de Polaris12, y (c) valor medible con la telemetría read-only actual, merecen entrar al roadmap.
El resto se mantiene como hipótesis, candidata de investigación o descartada. **Esta propuesta es
condicional:** todo lo propuesto se valida primero con su EXPERIMENT-DESIGN correspondiente, y ninguna
entrada otorga autorización de ejecución.

## 2. Propuesta por idea

| IDEA | ¿ENTRA? | Fase de entrada (roadmap) | Estado al entrar | Dependencia principal | Documentación de referencia |
|---|---|---|---|---|---|
| I-01 TBDR-IMR | **NO** (catalogo como evidencia negativa) | — | DESCARTADA para rendimiento; fuente de "prueba negativa" (L2-bypass) | lectura FASE G (modelo de memoria) | `projects/TBDR-IMR/` (PRIOR-ART, POLARIS12-FEASIBILITY) |
| I-02 Temporal Tile Reuse | **SÍ**, como variante acotada | FASE K (post Lab) → bajo WORKLOAD-SINTETICO | RESEARCH CANDIDATE (HYPOTHESIS) | runner K; harness F2 (escena estática); I-03 tile-lock | `projects/TEMPORAL-TILE-REUSE/` |
| I-03 Jitter Reprojection | **SÍ**, reencuadrada como detector tile-lock | FASE K (post Lab), al servicio de I-02 | HYPOTHESIS (no "sin motion vectors" en general) | runner K; Vulkan observation | `projects/JITTER-REPROJECTION/` |
| I-04 ROP Offload | **PARCIAL**: solo pieza async-compute co-scheduling | FASE K/BERRETA (ASY-01) | RESEARCH CANDIDATE (no la ruta ROP completa) | BERRETA/ASY-01; runner K | `projects/ROP-COMPUTE-OFFLOAD/` (RISKS, FEASIBILITY) |
| I-05 GFX8 Frame Recorder | **SÍ** (máxima prioridad de propuesta) | Herramienta a implementar antes/paralela a K | RESEARCH CANDIDATE (B) | autorización `profile_peak`; RADV build SQTT (verificación) | `projects/GFX8-FRAME-RECORDER/` (5 docs) |
| I-06 Predictive Ghost Cache | **PARCIAL**: solo "software predictive warm-up" | FASE G (post G-M1/M5) | HYPOTHESIS (abandonar HW-cache angle) | FASE G; GHOST (coordinación) | `projects/GHOST-PREDICTIVE-CACHE/` |
| I-07 Async Optical Flow | **NO** (implementar); documentar calibración | FASE P (contexto FG/upscaling) | BLOCKED/DEFERRED (D) | FASE P; sin autorización de instalación | `projects/ASYNC-OPTICAL-FLOW/` (5 docs) |
| I-08 Closed-Loop Governor | **SÍ** (read-only, sin writes) | FASE K (post Lab) | HYPOTHESIS (C) con subir a B si H2 (DPM-coupling) da resultado | runner K; workload GPU-bound con control de escala | `projects/CLOSED-LOOP-QUALITY-GOVERNOR/` |
| I-09 L2-Resident | **NO** (headline); sub-variante compute condicionada | — (solo documento de negativa) | DESCARTADA (headline); D condicionado a contadores futuros | FASE G (lectura); nada ejecutable hoy | `projects/L2-RESIDENT-RENDERING/` |
| I-10 Async Aux Renderer | **SÍ**, absorbida como variante de workload | FASE BERRETA/ASY-01 | HYPOTHESIS (coordinada con BERRETA, no nueva ruta) | BERRETA/ASY-01; runner K; harness F | `projects/ASYNC-AUX-RENDERER/` |

## 3. Resumen numérico de la propuesta

- **Entran al roadmap (con gate de validación):** I-02, I-03 (como par), I-05 (herramienta), I-08,
  I-10 (como variante BERRETA) + pieza async de I-04 + pieza warm-up de I-06.
- **Se mantienen como HYPOTHESIS sin fecha:** el resto de I-06; I-03 en su alcance general.
- **Quedan DESCARTADAS o DEFERIDAS:** I-01 (E), I-09 (E headline; D condicionada), I-07 (D,
  no implementar), la parte full-ROP de I-04.
- **Fases de entrada sugeridas (sin insertar en MASTER-PLAN todavía):**
  1. **Herramienta:** I-05 (frame recorder) → fase "K herramienta profiler".
  2. **Lab K habilitado primero** (runner + harness F2).
  3. **Después K:** pares I-02+I-03, governor I-08, variantes I-10/I-04async/BERRETA.
  4. **Después FASE G:** I-06 (predictive warm-up) y FASE P: I-07 (documental).

## 4. Qué NO se propone

- No entrar ideas solo por "potencial": cada entrada arrastra su EXPERIMENT-DESIGN y su gate de
  medición con runner K.
- No crear vías de ejecución para ideas cuya premisa quedó CONTRADICTED (I-01/I-09/I-07/I-04-full) —
  ninguna "a prueba" de thema suelto.
- No modificar MASTER-PLAN en esta fase; cuando se acepte la propuesta, la inserción se hará respetando
  la Regla de actualización (mapa del proyecto, sin duplicar estado).