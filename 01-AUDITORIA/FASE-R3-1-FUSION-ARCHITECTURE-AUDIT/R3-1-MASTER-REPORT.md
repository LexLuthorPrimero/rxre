# R3-1 MASTER REPORT — Auditoría de las Fusiones Arquitectónicas

> **Archivo:** `R3-1-MASTER-REPORT.md`
> **Fase:** FASE R-3.1 — FUSION ARCHITECTURE AUDIT
> **Fecha:** 2026-09-22 — READ-ONLY
> **Propósito:** responder las 10 preguntas del consejo **SOLO con la evidencia** auditada
> (ASSUMPTION-AUDIT, matrices, fusiones, roadmap). Nada de esto es decisión de implementación.

---

## Contexto en 2 líneas
7 fusiones agrupan 10 ideas de R-3. La auditoría clasificó 20 premisas del enunciado, cotejó prior art
y diseñó experimentos de falsación (no ejecutados). **Este informe informa el estado de la evidencia.**

## Respuestas ejecutivas

### Q1. ¿Cuál es la hipótesis mejor definida?
**FUSION-04 (EXP-F4-A): governor frametime-feedback read-only con histéresis.** Tiene la definición más
operativa (VD: p99; VI: render-scale; metodología A/B contra calidad fija), no depende de contadores y es
falsable hoy. Le sigue **FUSION-01 (EXP-F1-A)**: "un intérprete de capa recupera el offset de jitter con
MAE < 0.01 px".

### Q2. ¿Qué puente puede investigarse SIN Mesa/kernel?
**Las fusiones de la capa APPLICATION/LAYER: F1 (observabilidad), F4 (governor read-only), F6
(calibración/integración del harness), F5-sub-pieza (co-scheduling async BERRETA).** Nada de lo que toque
L2/DCC/HTILE/TTM (F2 residencia, F3 gestión real, F4 contadores, F5 falsación por counters) es realizable
hoy: exige kernel o driver.

### Q3. ¿Cuál tiene menos dependencias sin resolver?
**F4 (governor read-only)**: sus únicas dependencias son un workload GPU-bound con escala (harness existente)
y runner K — cero contadores, cero kernel. **F6-calibración** tiene dependencia única de FFX/costería en
shader. Todas las demás cuelgan de mediciones/contadores/autorizaciones.

### Q4. ¿Cuál es la más falsable?
**F5 (EXP-F5-A, el mínimo obligatorio)**: una config con blend/MSAA/resolución donde compute gane ≥10% FPS,
falsable con un par de paths A/B en el harness. También **F3 (EXP-F3-A)**: comparar GTT vs VRAM en frametime
acepta o niega el modelo de jerarquía. La más *profundamente* falsable (refuta su premisa base) es F5, que ya
es REJECTED/FALSIFIED a nivel de mecanismo.

### Q5. ¿Qué afirmaciones del enunciado quedan REFUTADAS/debilitadas?
| Afirmación | Veredicto |
|---|---|
| Los ROPs están saturados / las CUs están libres | REQUIRES EXPERIMENT (nunca medido) / CONTRADICTED como regla general |
| El tile 32×32 es unidad natural del HW | CONTRADICTED (8×8 HTILE/raster; 32×32 es práctica de industria) |
| El tile 4 KB permanece en L2 / 512 KB L2 permite residencia | **UNKNOWN local** (bypass CB/DB source-level; no API de residencia) |
| PCIe es el cuello dominante | **PARTIALLY VERIFIED** para el camino host; ×48–80 vs VRAM nominal/estimado; no universal |
| GTT puede competir con VRAM efectivo | CONTRADICTED en paridad de bandwidth (aunque DCC no ahorra PCIe; moverate 8 MB/s) |
| Jitter es equivalente a motion vector | CONTRADICTED (objetos dinámicos, disocclusion, recuperación por matrices no por jitter) |
| Compute puede sustituir ROP sin pérdida | CONTRADICTED (PS corre en los mismos CUs antes del RBE; 32 SP/ROP; UAV deshabilitan DCC) |
| Polaris12 puede mantener concurrencia graphics+compute "gratis" | **UNKNOWN / UNMEDIDO** (ACE/HWS family-level; nº ACEs, overlap y runtime local desconocidos; 8 CUs compartidas) |
| Polaris12 puede correr optical flow de frame generation | **CONTRADICTED en 1080p** (estimación; AFMF/FSR3 sin soporte GCN) |
| RGP no soporta Polaris12 | **PARTIALLY VERIFIED**: RGP 2.x=RDNA; compatibilidad GCN-era histórica no confirma runtime/viewer local |
| DCC reduce tráfico PCIe | CONTRADICTED (irrelevante, GPUOpen) |

### Q6. ¿Qué prior art se encontró que minimiza la novedad?
En casi todo el rango: **CUDARaster'11/Laine-Karras + CuRast'26 (F5)**, **TAA survey + Hanika'21 (F1/F3)**,
**AFMF/FSR3/lsfg-vk (F6)**, **consolas + DRS de motores (F4)**, **HPCA'19/LIBRA/Talisman/partial_update
(I-02)**, **TBDR móvil/freedreno/DSBR (F2)**, **GSPC-ICCAD'13/AutoScratch/CUDA-L2 (F3/I-09)**. La frontera de
"novedad" se estrechó a: (a) **tile-lock para I-02 en IMR-desktop con HTILE/DCC** (duende parcial), (b)
**governor counter-driven en PC** (no encontrado, NOVELTY UNKNOWN), (c) **viewer SQTT GFX8** (gap a verificar),
(d) **la combinación completa de F7** (POTENTIALLY NOVEL, sin confirmar).

### Q7. ¿Qué queda POTENTIALMENTE nuevo (y cuánto vale)?
- **F7-combinación** (TBDR-SW + FG + memoria invertida en GCN4 low-end): la única con ETIQUETA
  POTENTIALLY NOVEL, pero subordinada a F5/F6 (falsadas) → **BLOCKED**, y pendiente de auditoría de patentes.
- **F1 "alimentación conjunta jitter→(reproyección+predicción)"**: POTENTIALLY NOVEL solo en esa unión
  estrecha; el resto es KNOWN VARIANT. **Ninguna es "PROVEN NOVEL".**

### Q8. ¿Qué necesita capitalizar FASE D-3 (contadores)?
- **(F2/F5 falsación cuantitativa)**: medir ROP/CU/alça para la "prueba negativa" (EXP-F5-A).
- **(F4 counter-driven)**: feedback de contadores per-frame — si y solo si obtiene autorización.
- **(F3)**: tráfico MC/L2 para el modelo de jerarquía (el resto de F3 se resuelve con EXP-F3-A sin
  contadores). Todo ello **queda BLOCKED por autorización** — R-3.1 no hizo ninguna de estas mediciones.

### Q9. ¿Qué necesita FASE J (integración de largo plazo)?
Solo lo que ya se **indicó como READY/RESEARCH**: governor read-only (F4), observabilidad de jitter (F1),
co-scheduling async BERRETA (F5-sub), y — si sobreviven — tile-lock estático (I-02+I-03). Nada de F2/F3
(residencia, hot-set HW) ni F6 (FG) es candidato a J hoy.

### Q10. ¿Cuál es la línea de investigación de largo plazo defendible?
**Línea read-only de observabilidad+control:** (1) EXP-F3-A (bandwidth real) → (2) EXP-F1-A (jitter
observable) → (3) EXP-F4-A (governor read-only) → (4) EXP-F2-A (tile granularidad, si hace sentido) →
(5) re-evaluar F7 solo si ≥2 piezas dieron señal positiva. Formulado como investigación descriptiva devlog,
sin pretender ganancia de HW. Todo con falsación explícita y huella cero.

---

## Checklist de cierre (21 puntos)
- [x] 1. ROP saturation NO asumido (REQUIRES EXPERIMENT).
- [x] 2. CU idle NO asumido (CONTRADICTED como regla).
- [x] 3. L2 residency NO asumido para attachments (CONTRADICTED: bypass CB/DB).
- [x] 4. PCIe NO asumido como cuello universal (solo camino host).
- [x] 5. Jitter ≠ motion vector documentado.
- [x] 6. Async compute ≠ free compute (PLAUSIBLE-UNMEDIDO).
- [x] 7. RGP/Polaris12 verificado con matiz (RGP 2.x vs 1.x-era).
- [x] 8. Event IDs ≠ autorización de programación (mantenido).
- [x] 9. Ninguna modificación de sistema realizada (todo read-only).
- [x] 10. Ningún experimento ejecutado (solo diseños en EXPERIMENT-ROADMAP).
- [x] 11. EXP-F5-A (mínimo obligatorio de la fusión 5) presente.
- [x] 12. FUSION-07 permanece conceptual/BLOCKED (no se diseñó motor).
- [x] 13. MASTER-RESEARCH-STATUS coherente (v2.7 con filas por fusión).
- [x] 14. MASTER-PLAN NO modificado durante R-3.1.
- [x] 15. Ninguna dependencia innecesaria creada (DEPENDENCY-MATRIX).
- [x] 16. NOVELTY STATUS respetado (nunca "PROVEN NOVEL").
- [x] 17. "Framebuffer-en-caché" (I-01/I-09 headline) documentado como CONTRADICTED.
- [x] 18. Estados de prioridad de investigación presentes (READY/NEEDS PRECONDITION/RESEARCH ONLY/BLOCKED/REJECTED).
- [x] 19. Experimentos diseñados incluyen: hipótesis, VI/VD, controles, baseline, workload, repeticiones, métricas, éxito, falsación, riesgos, rollback.
- [x] 20. Prior-art indexado y reconciliado R-3⇄R-3.1 (PRIOR-ART-INDEX).
- [x] 21. Este informe responde las 10 preguntas SOLO con evidencia.
