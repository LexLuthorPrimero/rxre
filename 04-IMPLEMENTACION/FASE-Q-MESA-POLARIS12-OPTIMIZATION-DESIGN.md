# FASE Q — MESA POLARIS12 OPTIMIZATION RESEARCH — Documento de Diseño

> **Archivo:** `FASE-Q-MESA-POLARIS12-OPTIMIZATION-DESIGN.md`
> **Fase:** FASE R-2 — COMPLETE PROJECT DOCUMENTATION & ECOSYSTEM ARCHITECTURE (R-2.20)
> **Fecha:** 2026-09-22 — Modo SOLO DOCUMENTAL (DISEÑO; NO ejecutado)
> **Clasificación:** [DISEÑADO]. Sin modificación de Mesa. Trabajo = observación de código + diseño de
> cambios aislados futuros.
> **Estado global:** **PLANIFICADA** (roadmap). FASE Q NO autoriza tocar el driver.

---

## 1. OBJETIVO

Diseñar la investigación de **oportunidades de optimización específicas de Polaris12** dentro de
Mesa (radeonsi/RADV): inventario de puntos de brecha, solución para cada uno con condición/hiótesis,
y un pipeline de validación de cambios (aislado, A/B, réplicas, rollback). **No se modifica Mesa.

## 2. PUNTO DE PARTIDA (evidencia local)
- E3/E5/E5b: los costes dominantes son **MSAA/raster, geometría, textura multi-tap, HiZ, DCC** (funcionales,
  no atribuidos a ineficiencia de Mesa; E5b: "no se justifica aún un parche").
- FASE D etapa 2: diferencia A/B (ratio 1.41) correlaciona con geometría/vertex+export → pista de
  **ruta de raster/vertex** (SX 86% en A).
- R0-3: workarounds (MSAA sample loc, line filter) ya compensados por el driver.

## 3. INVENTARIO DE ÁREAS DE OPORTUNIDAD (por dominio Mesa)

| Dominio | Área | Candidatas observables en código (TIPO: documental) |
|---|---|---|
| **radeonsi (GL)** | textura/muestreo multi-tap | políticas de cache y format (DCC), neighbor sampling, ES |
| **radeonsi (GL)** | raster/EZ | MSAA sample loc (R0-3), early-Z heuristics, DB clears |
| **RADV (VK)** | pipeline (VS/FS) | H-5 shrink_image_store, H-6 wait_for_vm_map, H-7 partial_vs_wave (de FASE H) |
| **ACO/LLVM** | compilador | wave32/wave64 (SHD-01), unroll (SHD-02), 16-bit packed (SHD-03) |
| **RADV (VK)** | memoria | `radv_disable_dcc` (FRAG-02), asignaciones (G-M2) |
| **RADV (VK)** | scheduling/barriers | marking de barreras, compute overlap (ASY-01) |
| **radeonsi/RADV** | cache/presentación | clear/flush policies (clear_db_cache, R0-3) |

## 4. FICHA POR OPORTUNIDAD (plantilla obligatoria)

| Campo | Descripción |
|---|---|
| **FUENTE** | archivo/línea de Mesa (para documentar en este diseño) |
| **COMMIT** | commit/cambio que la introdujo o repara (si se conoce; NO inventar) |
| **GPU** | GFX8/Polaris12 |
| **CONDICIÓN** | cuándo aplica (estado de pipeline, formato, resolución) |
| **HIPÓTESIS** | qué mejoraría y por qué |
| **MÉTRICA** | cómo se probaría (FPS/frametime/power con runner K) |
| **WORKLOAD** | con qué carga (sintético/overlay/superposition) |
| **RIESGO** | de tocar el código (regresión, otros ASIC) |
| **REVERSIBILIDAD** | rollback (git o build alternativo) |
| **ESTADO** | corte de crecimiento: OBSERVADO→HIPÓTESIS→DISEÑO→... (nunca afirmado) |

## 5. PIPELINE DE VALIDACIÓN (regla de oro de Q)
```
OBSERVACIÓN (código) → HIPÓTESIS → DISEÑO (cambio AISLADO mínimo) → EXPERIMENTO A/B (runner K,
N≥5, IC95%) → RESULTADO → REPRODUCCIÓN (independiente) → DECISIÓN (aceptar/rechazar → gobernanza)
```
- **Cambio aislado:** una sola variable por cambio; mismo código base; diff mínimo; compilado local (nunca
  en el sistema o en Mesa SYSTEM).
- **Rollback:** guardar y poder revertir (gits/mesa-marcado); nunca correr con Mesa system modificada.
- **Autorización:** FASE Q por sí sola NO aplica cambios; cada cambio propuesto vuelve a gobernanza.

## 6. LIMITACIONES / CONFOUNDERS
- No hay contadores HW autorizados; la señal será indirecta (frametime/power) → CUIDADO con atribuir
  mejora a un cambio cuando hay efecto de power/clocks (E3/E5). El Lab K (estado/captura de reloj) lo
  mitiga parcialmente.
- Los costes funcionales no-ALU (E5b) significan que optimizaciones de shader/compilador pueden tener
  poco alcance; el margen real puede estar en raster/memoria (áreas H/P).

## 7. CONCLUSIÓN DEL DISEÑO
FASE Q queda **DISEÑADA** (inventario por dominio, ficha por oportunidad, pipeline de validación, límites).
**No se escribió ni recompiló nada de Mesa.** Las modificaciones futuras se limitan a sesión experimental
con rollback y solo después de autorización explícita. Todo lo de esta fase es observación de código
documentada o diseño de experimentos propuestos — sin afirmar ningún beneficio.