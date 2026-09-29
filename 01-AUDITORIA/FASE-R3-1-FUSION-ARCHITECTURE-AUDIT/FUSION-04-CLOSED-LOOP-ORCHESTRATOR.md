# FUSION 04 — "EL SISTEMA SE AUTO-OBSERVA Y SE AUTO-AJUSTA"

> **Archivo:** `FUSION-04-CLOSED-LOOP-ORCHESTRATOR.md`
> **Fase:** FASE R-3.1 — FUSION ARCHITECTURE AUDIT
> **Fecha:** 2026-09-22 — READ-ONLY
> **Categoría de fusión:** GFX8 Frame Recorder + HW counters + Closed-loop Quality Governor + Orquestador
> OBSERVATION → CLASSIFICATION → DECISION → QUALITY CHANGE → OBSERVATION

---

## 1. Auditado: qué contadores pueden medirse en GFX8

Datos locales R-0/R-1 (reconciliación 2026-09-24): GPUPerfAPI v3.17 contiene un
catálogo GFX8 genérico y v3.11.1 conserva la extracción histórica; 2304 filas no
equivalen a 2304 eventos validados para `1002:699f`. GRBM=2/SQ=4 son entradas de
catálogo, no validación ASIC; no existe rango semánticamente seguro.

**Punto crítico conservado: R-0 Event IDs ≠ autorización de programación.** Documentar contador ≠ permitido
programarlo. D-3 counter-programming sigue **NO AUTORIZADO**; esta fase solo audita viabilidad.

| Capacidad | Estado | Nota |
|---|---|---|
| Contadores GFX8 (GPUPerfAPI v3.17; v3.11.1 histórico) | **PARTIALLY RECONCILED / CATALOG ONLY** | no valida ASIC, semántica ni programación |
| Resolución temporal / por frame | PARTIALLY VERIFIED | PerfStudio/CodeXL mostraba per-draw y per-kernel timelines a ~60fps (legacy) |
| Reset/segmentación | PLAUSIBLE | requieren readouts frecuentes y ventanas de reset alineadas a frame (no verificado GFX8) |
| SPM (Streaming Performance Monitor) | **UNKNOWN** | referencias SPM son gfx9+/RDNA; NO confirmar SPM en Polaris12 |
| SQTT (thread trace) | **UNKNOWN / REQUIRES CAPABILITY AUDIT** | existen rutas source-level; captura real GFX8 no confirmada |
| RGP soporte Polaris12 | **UNKNOWN** | RGP 2.x = RDNA-only; compatibilidad GCN histórica no implica runtime local |
| Interfaz read-only (frametime/power/clocks/kalm/radeontop) | VERIFIED | es la telemetría disponible HOY |

## 2. Separar telemetría / profiling / control loop

- **Telemetría (bucle del governor read-only):** power (35 W cap), SCLK/MCLK DPM, frametime, kalm — VA HOY.
- **Profiling (diseño GFX8 recorder):** captura/dump + timeline — PARTIALLY VIABLE (legacy tools, SQTT).
- **Control loop (governor):** lazo con actuación = **render-scale de la app** (sin writes HW). Actuación de
  DVFS en driver NO disponible (no autorizada + DPM write sin marco L).

## 3. Dimensiones de control del lazo (analizadas, NO diseñadas)

| Dimensión | Valor/estado |
|---|---|
| Variable controlada (actuador) | render-scale app (resolución) — resolver |
| Señal de feedback | frametime (lectura roll) + power (sysfs) |
| Frecuencia de muestreo | propuesta: por-frame (frametime) y ~1 Hz (power) |
| Latencia de control | 1–2 frames si el lazo es por-frame |
| Histéresis | requerida (oscilación reportada en DRS: MobiCom'15, Denes'20) |
| Oscilación/overshoot | riesgo real con actuación no-lineal (render-scale→frametime no es lineal) |
| Intervalo mínimo de cambio de calidad | a definir en EXPERIMENT (no ahora) |

Prior art de lazo cerrado: **consolas** = DRS estándar; **PC** = motores (Unity HDRP, Unreal DRS) y Radeon
Boost/RSR (basados en movimiento/percepción, NO en HW counters). **No se encontró gobierno por contadores
HW en PC desktop publicado** → el gap de "counter-driven governor en PC" es **PARTIALLY VERIFIED como
ausencia** (NOVELTY UNKNOWN), pero el governor sin contadores (frametime-feedback) es **KNOWN VARIANT**.

## 4. Falsabilidad de la fusión

Hipótesis falsable (read-only, sin contadores): *"un governor frametime-feedback con histéresis reduce p99
frametime en workload GPU-bound sin machacar la calidad percibida, comparado con calidad fija"*. Falsable con
A/B en harness. La hipótesis counter-driven ("los contadores añaden señal útil sobre frametime-only") **no
puede probarse NO-hoy** (conteadores NO AUTORIZADOS) → requiere D-3 autorización.

## 5. Veredicto de fusión

- **Governor read-only** = estadio REALISTA y priorizable (READY FOR FUTURE EXPERIMENT, con historial).
- **"Auto-observación" counter-based** = **BLOCKED** por autorización (D-3) + incertidumbre de per-frame
  (SPM UNKNOWN, SQTT legacy).
- **Fusión 4 como sistema completo** = NEEDS PRECONDITION (herramientas verificadas + autorización).
