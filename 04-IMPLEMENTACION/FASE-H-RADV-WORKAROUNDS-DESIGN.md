# FASE H — RADV / WORKAROUNDS — Documento de Diseño

> **Archivo:** `FASE-H-RADV-WORKAROUNDS-DESIGN.md`
> **Fase:** FASE R-2 — COMPLETE PROJECT DOCUMENTATION & ECOSYSTEM ARCHITECTURE (R-2.6)
> **Fecha:** 2026-09-22 — Modo SOLO DOCUMENTAL (DISEÑO; NO ejecutado)
> **Clasificación:** [DISEÑADO]; datos de workarounds tomados de `R0-3-MESA-WORKAROUNDS-POLARIS12.md`
> ([VERIFICADO] documentalmente) y de la investigación de eventos FASE D.
> **Estado global:** **PENDIENTE** — cada workaround es un candidato de investigación, NO una modificación.

---

## 1. Objetivo

Diseñar la investigación de los **workarounds que Mesa/RADV aplica sobre Polaris12** para (a) entender el
comportamiento observado (ej. MSAA, líneas, early-Z, DCC) y (b) saber si alguno es **ispensable para un
workload sintético** o si puede explicar diferencias A/B ya existentes (en los que no se debe atribuir el
efecto al "modo MSAA" sin controlar el filtro).

## 2. Regla de oro

**Nada de la fase H modifica Mesa ni el sistema.** Los workarounds viven ya en el driver; la fase es
**explicativa e interpretativa** y sus candidatos son palancas de **workload** (no de driver) o de
**driconf/env var** ya soportados sin recompilar. Modificar el driver = FASE Q (y requiere autorización y
rollback).

## 3. Fichas por workaround (fuente: R0-3 + FASE D)

### H-1 `has_msaa_sample_loc_bug` (radeonsi) — censar el efecto
- **ORIGEN:** posta mesa-dev 2017-03 (si_pipe.c); flag `POLARIS10..POLARIS12 ∪ VEGA10 ∪ RAVEN`.
- **RUTA:** `si_emit_msaa_sample_locs` → `PA_SU_SMALL_PRIM_FILTER_CNTL` (R_028830): cuando
  `nr_samples==1`, el small primitive filter sigue usando sample locations (=0) si MSAA está off.
- **GPU AFECTADA:** Polaris12 incluido.
- **MOTIVO:** el filtro de primitivas pequeñas referencia sample locations; con nr_samples==1 no se emiten
  posiciones a menos que kernel/state lo requiera; regresión histórica bug #96908 (2016, fix d938b8c).
- **CONDICIÓN:** `nr_samples > 1 && !multisample_enable` → se deshabilita el filtro.
- **CÓDIGO:** R0-3 §2.2 (snipets). Para RADV el equivalente moderno debe leerse en la versión local al
  ejecutar (no se lee ahora).
- **EFECTO ESPERADO:** con MSAA off, primitivas < 1 px pueden salir coloreadas/repetidas en vez de
  filtradas; con MSAA on, correcto.
- **RIESGO:** bajo (documental). El riesgo de interpretar mal un A/B MSAA es ALTO si se ignoran los
  sample locations.
- **POSIBLE BENCHMARK:** barrido GEO-05/07 (primitivas pequeñas) con MSAA 1x vs 4x, igual FS → ver si el
  filtro explica parte del cociente MSAA 3.13× de E5.
- **ESTADO LOCAL histórico vs futuro:** en E3/E5/E5b el cociente MSAA 3.13× se midió con cap 35 W;
  re-examinar a la luz de este workaround antes de atribuirlo a raster en general.

### H-2 `LINE_FILTER_DISABLE` — líneas
- **ORIGEN:** `family <= CHIP_POLARIS12` (S_028830_LINE_FILTER_DISABLE).
- **RUTA:** mismo registro R_028830.
- **GPU AFECTADA:** Polaris12 previsto (family <= POLARIS12).
- **MOTIVO:** bug de filtrado de líneas de la familia GFX8/Polaris; driver deshabilita el filtro.
- **CÓDIGO:** R0-3 §2.2.
- **EFECTO ESPERADO:** líneas dibujadas sin filtro (aliased) si LINES enabled; en workload que solo usa
  triangles no aplica.
- **RIESGO:** bajo.
- **POSIBLE BENCHMARK:** primitivas de tipo línea (GEO complementario opcional) para cuantificar el
  impacto visual/perf — bajo valor, se anota como secundario.

### H-3 `clear_db_cache_before_clear` (driconf radeonsi_clear_db_cache_before_clear)
- **ORIGEN:** workaround de corrupción observada (ARK) que requiere flush del caché DB/Z antes del clear.
- **RUTA:** driconf opción en radeonsi.
- **GPU AFECTADA:** genérica (driconf por app).
- **EFECTO ESPERADO:** evitar corrupción Z; coste: flush extra en clears.
- **RIESGO:** N/A (opción por-app).
- **POSIBLE BENCHMARK:** comparar con/ sin opción en un workload con muchos clears de depth (GEO-07): si no
  hay corrupción visible, el costo extra de flush podría medirse (opción desactivada).

### H-4 `assume_no_z_fights`, `commutative_blend_add`
- **ORIGEN:** optimizaciones driconf de radeonsi (no erratas HW).
- **EFECTO:** permiten al compilador asumir ausencia de z-fights / conmutatividad del blend para optimizar.
- **RIESGO:** ALTO si se activan sin pipeline test (pueden romper imagen); solo medibles con app que los
  soporte. Se anotan como NO-CANDIDATO (no relevantes a nuestros benchmarks actuales).

### H-5 `shrink_image_store` (candidato a investigar documentalmente)
- **RUTA:** RADV; reduce el image store a lo mínimo requerido cuando el write es parcial (perf/lower mem BW).
- **ESTADO DOCUMENTAL:** mecanismo conocido en RADV; NO se ha verificado su estado en la versión local
  (26.2.2) ni en GFX8. Candidato de análisis de código (lectura local) en FASE Q, no de A/B aquí.

### H-6 `wait_for_vm_map` (candidato a investigar documentalmente)
- **RUTA:** RADV; sync/fence por map de memoria VB/IB antes de usar → afecta latencia de submit/tramado en
  workloads con mucha creación/destrucción de buffers.
- **ESTADO DOCUMENTAL:** presente en RADV; aplicable a nuestros patrones "upload/fetch" (E2 Parte C).
  Candidato de análisis de código; sin A/B en esta fase.

### H-7 `partial_vs_wave` (candidato a investigar documentalmente)
- **RUTA:** RADV VS; emite VS waves parciales según el número real de invocations (evita ondas casi vacías).
- **INTERÉS GEO:** con GEO-01 (draws de pocos vértices) el efecto puede ser grande; documentar en la ficha
  GEO-01 como posible confounder.

## 4. Cómo se integra con otras fases
- **FASE Q (Mesa optimization):** los candidatos de *código* (H-5/6/7) pasan a Q como **observaciones de
  código**, NO como propuestas de patch; Q exige pipeline de validación con rollback.
- **FASE F GEO-05/07:** interpretar cocientes MSAA/overdraw con H-1 presente.
- **FASE P:** FSR/upscaling interactúa con el filtro de pequeñas primitivas (H-1) al reducir resolución —
  cruzarlo en el diseño de P.
- **FASE G:** el `wait_for_vm_map` y el camino GTT están ligados → H-6 se cita en G-M5.

## 5. Conclusión del diseño

FASE H queda **DISEÑADA** y **PENDIENTE**: 7 candatos (H-1..H-7), de los cuales H-1 (MSAA sample loc) es
el de mayor potencia explicativa sobre resultados ya medidos (E3/E5: 3.13× MSAA) y H-5/6/7 requieren
solo **lectura local de código** (FASE Q) sin autorización adicional. **No se afirma ningún efecto nuevo
sobre el sistema; ningún trabajo de la fase se ejecutó.**