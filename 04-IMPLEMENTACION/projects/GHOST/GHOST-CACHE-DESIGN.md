# GHOST — Ghost Cache — Documento de Diseño del Proyecto

> **Archivo:** `04-IMPLEMENTACION/projects/GHOST/GHOST-CACHE-DESIGN.md`
> **Fase:** FASE R-2 — COMPLETE PROJECT DOCUMENTATION & ECOSYSTEM ARCHITECTURE (R-2.15)
> **Fecha:** 2026-09-22 — Modo SOLO DOCUMENTAL (DISEÑO; NO implementado)
> **Clasificación:** [IDEA→HIPÓTESIS, NO VALIDADO]. **PROVISIONAL** — Ghost y Ghost Cache son conceptos.**
> **Estado global:** **IDEA**. Requiere evidencia de FASE G para ascender en el ciclo de vida.

---

## 1. OBJETIVO

Investigar si reorganizar el **acceso/alineado de la memoria de trabajo** de la GPU (prefetch, localidad,
elección GTT vs VRAM, working set) reduce el costo de "fetch-latency" que hoy caracteriza al workload
sintético (ES-01/F2: frametime ∝ fetches, power constante). "Ghost" = hipótesis de **localidad**,
"Ghost Cache" = hipótesis de **mecanismo de prefetch**.

## 2. SEPARACIÓN EXPLÍCITA de conceptos (regla de no-fusión)

| Concepto | Tipo | Estado |
|---|---|---|
| **GHOST** | Investigación de memoria (prefetch/localidad/working set) | IDEA (depende FASE G) |
| **GHOST CACHE** | Mecanismo hipotético de cache/prefetch de accesos | HIPÓTESIS (no validada) |
| **RX550-TUNER** | Tuner de perfiles PowerPlay/DPM | PROVISIONAL pero de otra área (control) |
| **EXPERIMENTOS DE MEMORIA (FASE G)** | G-M1..G-M5 ya diseñados | DISEÑADOS (read-only la mayoría) |

GHOST NO es RX550-Tuner; NO es una varita que toca el driver; usa el modelo de FASE G como fundamento.

## 3. QUÉ ESTUDIA (dominios)
- **VRAM vs GTT vs host memory vs PCIe** (el camino de FASE G).
- **Caches L0/L1/L2** (hit rate inferible solo con contadores — FASE M / D-3).
- **Localidad de acceso y working set** de los buffers/texturas del sintético.
- **Latencia vs bandwidth** cuando el fetch domina (F2).

## 4. EVIDENCIA NECESARIA para moverse IDEA→HIPÓTESIS→OBSERVADO→VALIDADO

| Escalón | Requisito | Fuente que lo habilita | Estado |
|---|---|---|---|
| **IDEA** | planteado el problema | este documento | ✅ (actual) |
| → **HIPÓTESIS** | FASE G confirma que el camino GTT / localidad explica la latencia de fetch | G-M1, G-M5 (read-only) | ⏳ pendiente |
| → **OBSERVADO** | variar localidad/working-set en workload y ver diferencia significativa (en FPS/p99) | experimento del proyecto con runner K | ⏳ pendiente |
| → **VALIDADO** | reproducción independiente + mecanismo claro (contadores HW D-3 o aislación) | FASE M / informe de validación K | ⏳ pendiente |

Cada salto emite un documento/estado nuevo (hipótesis confirmada etc.); NO se alcanza por declaración en
este archivo.

## 5. MECANISMOS HIPÓTESIS (solo para diseño de experimentos)
- GHOST-CACHE: agrupar/pin buffers en VRAM y ordenar accesos para maximizar hit L2 (reduce request al
  GTT/DRAM). Implica únicamente **custodiar la asignación** (API del driver), no tocar kernel.
- En la práctica el experimento es: mismo trabajo, 2 asignaciones (DEVICE_LOCAL vs HOST_VISIBLE; ya G-M2)
  y observation de `mem_busy`/frametime — la "hipótesis Ghost" es que si la diferencia es grande, la
  localidad es el cuello; si no, es latencia de red interna.

## 6. CONFOUNDERS (documentados)
- Migración dinámica por el driver (TTM) → hay que **verificar el alojamiento** (mem_info_*) no asumirlo.
- `mem_busy` no es % BW (METRICS-DEFINITIONS) → no usar como verdad de BW.
- La potencia LOADA (power-limited) puede enmascarar efectos (E3/E5).

## 7. MÉTRICAS Y WORKLOADS
- Workload: sintético FETCH (F2) con variación de alojamiento/localidad; N≥5; runner K; telemetría.
- Métricas: frametime p50/p99, mem_busy, mem_info_vram/gtt, power, faults.

## 8. DEPENDENCIAS
FASE G (modelo de memoria), FASE K (runner), y potencialmente FASE M (contadores para hit-rate). GHOST no
depende de RX550-Tuner. Ninguna instalación.

## 9. CONCLUSIÓN
GHOST queda **en IDEA** (con diseño de escalones de evidencia). Para ascender necesita que G-M1/G-M5
prueben que el camino de memoria explica la fetch-latency. **Se declara explícitamente que Ghost-Cache
es una HIPÓTESIS sin validar y que nada se ejecutó ni se instala.**
