# FASE-R3-FINAL-REPORT — Informe Final de FASE R-3 (ORIGINAL IDEAS, NOVELTY AUDIT & RESEARCH CANDIDATES)

> **Archivo:** `FASE-R3-FINAL-REPORT.md`
> **Fase:** FASE R-3 — ORIGINAL IDEAS, NOVELTY AUDIT & RESEARCH CANDIDATES
> **Fecha:** 2026-09-22 — Modo SOLO DOCUMENTAL
> **Clasificación:** [COMPLETADA]. Investigación documental y web; **nada se implementó, ejecutó ni instaló**.
>
> **Reconciliación 2026-09-24:** las afirmaciones de ACE/CU-reservation, SQTT/RGP,
> GPUPerfAPI y cualquier cifra de ACE que aparecen en este informe son source-level o hipótesis. No
> describen capacidad runtime de `1002:699f`; H12 y toda capability audit siguen abiertas.
> **Ubicación:** `01-AUDITORIA/FASE-R3-NOVELTY-AUDIT/` (matrices) + `04-IMPLEMENTACION/projects/` (10 directorios de ideas).

---

## A. RESUMEN EJECUTIVO

FASE R-3 realizó una auditoría de novedad y viabilidad de 10 ideas propuestas (I-01…I-10) mediante
búsqueda web en múltiples fuentes (AMD GPUOpen, Khronos, Mesa, NVIDIA, academias/papers, open source,
comunidad técnica y consolas). Cada idea tiene su directorio con prior art, factibilidad Polaris12,
diseño de experimento (no ejecutado) y riesgos. La regla de novedad se aplicó severamente: **ninguna
afirmación de originalidad se verificó positiva**; las ausencias se registran como NOVELTY UNKNOWN y los
reclamos base refutados se marcan CONTRADICTED/REJECTED por prior art o topología, según
corresponda; la evidencia local que no se midió permanece `UNKNOWN`.

Resultado global: **0 ideas "PROVEN NOVEL"**; **1 POTENTIALLY NOVEL en determinadas condiciones**
(sub-variante compute de I-09, condicionada); varias PARTIALLY NOVEL; varias KNOWN VARIANT. Ninguna idea de
rendimiento sobrevive sin matices a la topología real de Polaris12; el bypass CB/DB es
source-level de familia y la confirmación local permanece `UNKNOWN` (8 CUs/16 ROPs,
fetch-bound ES-01).

## B. RESPUESTA A LAS 10 PREGUNTAS DEL INFORME

### 1. ¿Qué ideas ya existen?
- **I-04 (ROP→compute)** existe desde hace décadas (Laine & Karras 2011 CUDARaster; FreePipe; CuRast 2026).
- **I-07 (optical flow FG)** ES el stack enviado por AMD (AFMF/FSR3, todo en shaders async).
- **I-10 (async aux renderer)** es técnica madura y enviada (DOOM, Cyberpunk GDC23, Frostbite, Division 2).
- **I-08 (quality governor / DRS)** existe en consolas y motores (Unity HDRP, Unreal, Intel DRR).
- **I-01 (tiling/binning)** existe en mobile TBDR (PowerVR/Apple/Adreno) y en el binning pass de freedreno;
  AMD lo hace en HW con RB tile-cache + HTILE + DCC.
- **I-02 (temporal tile reuse)** existe académico (HPCA'19, LIBRA MICRO'24, Talisman'96) y en
  EGL_KHR_partial_update / VK_KHR_incremental_present / render caches.
- **I-06 (predictive texture prefetch)**: la parte predictiva por cámara existe (Dumont et al. 2003,
  UE5/Unity streaming); la parte "GHOST tag/prefetch" académica (ARC, bypass buffers).

### 2. ¿Cuáles son variantes?
- **I-01** = variante de binning/TBDR aplicada a IMR (sin el tile store HW).
- **I-03** = variante de la reproyección solo-cámara (Hanika et al. 2021, TAA literature).
- **I-05** = variante de frame recorder (RGP/GPUVis/gfxreconstruct) enfocada al viewer SQTT GFX8.
- **I-06** = variante de streaming por cámara + caché de prefetch.

### 3. ¿Cuáles tienen antecedentes académicos?
Todas excepto I-05 (contada vía GPUView lineage). Destacados: I-04 (Laine/Karras 2011, Schütz 2026),
I-02 (Rendering Elimination HPCA'19, LIBRA MICRO'24), I-03 (Hanika JCGT 2021, TAA survey), I-06 (Igehy 1998,
Dumont 2003, NeuralPVS 2025), I-09 (GSPC ICCAD 2013, AutoScratch), I-08 (MobiCom 2015).

### 4. ¿Cuáles tienen implementaciones (open source / comerciales)?
- Open source: todas quería: I-04 (CUDARaster, CuRast, LucidRaster), I-07 (FidelityFX-SDK, lsfg-vk),
  I-10 (Vulkan-Samples), I-02 (vello/WebRender), I-05 (RADV SQTT, RenderDoc, gfxreconstruct), I-08 (Unity HDRP).
- Comercial: I-07 (AFMF/FSR3), I-08 (consolas/DRR), I-10 (DOOM/Cyberpunk), I-01 (TBDR móvil, DSBR).

### 5. ¿Cuáles son potencialmente novedosas?
- **I-05** (viewer SQTT v2.2 para GFX8): PARTIALLY NOVEL / NOVELTY UNKNOWN — condicionado a que RGP ≤1.16
  o rgp-inspect no lo cubran (verificar).
- **I-02+I-03 como par** (temporal tile-skip en IMR + reproyección solo-cámara como tile-lock): la
  combinación es un slice candidato; el bypass CB/DB es source-level y la confirmación local
  `UNKNOWN`; por ello la novelty queda condicionada.
- **I-09 sub-variante compute** (target compute-UV ≤230 KB releyendo): PARTIALLY NOVEL en GCN4, condicionado
  y marginal.

### 6. ¿Cuáles son técnicamente plausibles en Polaris12?
- **Plausibles (según evidencia): I-08** (governor read-only), **I-02/I-03** (escena estática, fill-limited
  512 sh), **I-10** (como variante de medición), **I-05** (herramienta, verify-first).
- **Headlines que no deben promoverse:** I-01/I-09 (CB/DB bypass documentado a nivel familia,
  local `UNKNOWN`), I-04 (full; CUs compartidas) e I-07 (estimación de coste; no causalidad).

### 7. ¿Cuáles requieren demasiado trabajo?
- I-01, I-09, I-04 (full): re-implementación de pipeline de visibilidad + residencia sin API → HIGH.
- I-07: integración completa FFX en una tarjeta donde la premisa falla → HIGH sin beneficio.
- I-02/I-03 en versión "motor": HIGH — por eso se acotan al harness sintético (LOW).

### 8. ¿Cuáles merecen investigación posterior?
- I-05 (herramienta, habilita todo el resto) — gate de verificación rápido.
- I-02+I-03 (par temporal, escena estática).
- I-08 (governor; la incógnita genuina H2 = acople DPM-calidad).
- I-10 y pieza async de I-04 → coordinadas con BERRETA/ASY-01.
- I-06 (solo software predictive warm-up, tras FASE G-M1/M5).

### 9. ¿Cuáles deben descartarse?
- **I-01 (DISCARD para rendimiento)** — el mecanismo HW (HTILE+DCC+RB tile-cache) ya cubre lo que el
  software tile intentaría; solo valor como "prueba negativa".
- **I-09 headline (E)** — L2-bypass hace la tesis imposible por topología.
- **I-07 (D, no implementar)** — implementación full del stack AFMF en RX550 contradicha por poder/bandwidth;
  permanece como calibración documental en FASE P.
- **I-04 full (E)** — constantes publicadas la refutan en este tier; solo se conserva la pieza async.

### 10. ¿Qué nuevas líneas de investigación aparecen?
1. **Verificación de cobertura SQTT de RGP 1.x** para I-05 (cerraría/abriría el gap de viewer).
2. **Cuantificación del overlap real de queues/ACEs en 8 CU fetch-bound** (I-10/I-04async
   + BERRETA): pregunta de
   medición, no de novedad.
3. **Acople DPM-calidad (H2 de I-08)**: ¿el frametime bajo DPM es no-monotónico? → determina si el governor
   read-only aporta algo reutilizable.
4. **Alcance real de EGL_KHR_partial_update / VK_KHR_incremental_present bajo X11/Wayland + DCC** como
   superficie para I-02 (align de tiles vs DCC).
5. **Corrección local de la FASE R-3: confirmar el número de ACEs de Lexa**; la cifra 2
   queda `UNKNOWN`, sin hoja oficial local.
6. **Nivel de tráfico delta real** en escenas estáticas con post-vs-sin-post (para dimensionar I-02).

## C. STATE OF NOVELTY FINAL POR IDEA (tabla corta)

| ID | Novedad (final) | Prior art principal | Viabilidad Polaris12 | Estado recomendado |
|---|---|---|---|---|
| I-01 | KNOWN VARIANT (+residencia CONTRADICTED) | Vulkan TBR; freedreno binning; DSBR; DCC/HTILE | LOW (L2-bypass) | E (o "prueba negativa") |
| I-02 | PARTIALLY NOVEL (skip IMR + HTILE/DCC) | HPCA'19; LIBRA; Talisman; partial_update | MEDIA-ALTA (estático) | C → B condicional |
| I-03 | KNOWN VARIANT (reproyección solo-cámara) | Hanika 2021; TAA survey; FSR2/DLSS guías | ALTA (como tile-lock) | C |
| I-04 | KNOWN VARIANT (premisa CONTRADICTED) | CUDARaster; CuRast; LucidRaster | LOW | B (solo pieza async) |
| I-05 | PARTIALLY NOVEL / UNKNOWN (viewer SQTT GFX8) | RGP; GPUVis; rgp-inspect | ALTA (herramienta) | B (verify-first) |
| I-06 | PARTIALLY NOVEL (cámarax GHOST en IMR sin HW-cache claim) | Igehy'98; Dumont'03; UE5 SVT | MEDIA (warm-up SW) | C |
| I-07 | KNOWN VARIANT (= AFMF/FSR3; premisa CONTRADICTED en tier) | FSR3/FMF; FFX OF; lsfg-vk | LOW | D |
| I-08 | KNOWN VARIANT (DRS sin contadores = norma) | Consolas DRS; Intel DRR; Unity HDRP | ALTA (read-only) | C → B si H2 |
| I-09 | CONTRADICTED (headline) / PARTIALLY NOVEL (sub-claim compute) | CUDA L2; GSPC; AutoScratch; DCC/HTILE | LOW | E (headline); D condicionado |
| I-10 | KNOWN VARIANT | GDC17/Cyberpunk/Frostbite/Division2; RTSS'21 | MEDIA | C (con BERRETA) |

## D. CHECKLIST DE FINALIZACIÓN DE FASE R-3

- [x] Las 10 ideas fueron investigadas (dirs `04-IMPLEMENTACION/projects/`).
- [x] Se buscó prior art (múltiples fuentes; inglés primario, cuando aplica otros idiomas).
- [x] Se revisaron papers (HPGA/MICRO/SIGGRAPH/JCGT/ICCAD/MLSys/MobiCom…).
- [x] Se revisaron proyectos open source (FidelityFX, Vulkan-Samples, Mesa, RenderDoc, gfxreconstruct…).
- [x] Se revisaron fuentes AMD/Vulkan/Mesa (GPUOpen, Khronos, docs.mesa3d, NVIDIA CUDA L2).
- [x] Se revisó relevancia específica Polaris12 (L2 512 KB; bypass CB/DB source-level con
  confirmación local `UNKNOWN`; 8 CU/16 ROP; ES-01 fetch-bound).
- [x] Las afirmaciones de originalidad fueron verificadas o rebajadas (se usó NOVELTY STATUS; ninguna
  "proven novel").
- [x] Existe matriz de novedad (`R3-NOVELTY-MATRIX.md`).
- [x] Existe matriz de viabilidad (`R3-FEASIBILITY-MATRIX.md`).
- [x] Existe matriz de dependencias (`R3-DEPENDENCIES.md`).
- [x] Cada idea tiene documento(s) propio(s).
- [x] Se separó innovación real de variante conocida.
- [x] Se identificaron ideas que deben descartarse (I-01, I-09 headline, I-04 full, I-07 implementación).
- [x] No se ejecutó ninguna implementación (solo documentos y noticias web).
- [x] No se modificó el sistema (sin writes; MASTER-PLAN NO modificado; sólo propuesta de integración).

## E. REGLA FINAL RESPETADA

La finalidad era intentar **refutar** las ideas, no demostrar que son nuevas. Las tesis base de I-01, I-04,
I-07 e I-09 fueron refutadas por prior art/topología; los residuos potencialmente novedosos quedaron
clasificados como PARTIALLY/POTENTIALLY NOVEL con el gate de evidencia correspondiente. **Ninguna idea se
declaró "PROVEN NOVEL".** I-05 queda como **gap de herramienta candidato/no demostrado** y
combinaciones de conocimiento previo (I-02+I-03) como candidatas para el laboratorio local;
la novelty y el runtime siguen `UNKNOWN`.
