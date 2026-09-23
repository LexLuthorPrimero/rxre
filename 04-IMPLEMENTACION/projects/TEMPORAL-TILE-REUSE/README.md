# I-02 — TEMPORAL TILE DELTA REUSE — Documentary Novelty Audit

> **Proyecto:** RX550/Polaris12 iterative rendering research
> **Fase:** FASE R-3 — Documentary novelty audit (SOLO DOCUMENTAL; no code, no system changes, no benchmarks, no installs)
> **Fecha:** 2026-09-22
> **Modo:** DOCUMENTAL ONLY
> **Archivo principal:** `projects/TEMPORAL-TILE-REUSE/`
> **Archivos:** `README.md`, `PRIOR-ART.md`, `POLARIS12-FEASIBILITY.md`, `EXPERIMENT-DESIGN.md`

---

## 1. IDEA EN UNA LÍNEA

Track, a frame granularity, which screen tiles change between consecutive frames
(temporal tile delta), and re-render **only the changed regions** on an immediate-mode
renderer (IMR) such as Polaris12, instead of re-rendering the full frame.

## 2. ESTADO

| Atributo | Valor |
|---|---|
| **IDEA** | I-02 — Temporal Tile Delta Reuse |
| **NOVELTY STATUS** | **PARTIALLY NOVEL** (per scope-resolved analysis in §4) |
| **Sub-claims** | 1) tile-level dirty tracking → KNOWN (TBR/TBDR, dirty-rect UI, damage APIs)<br>2) full re-render skip for unchanged tiles → KNOWN (Rendering Elimination, Transaction Elimination, priority rendering)<br>3) **per-tile shading/fill skip on a commodity desktop IMR (Polaris12) exploiting HTILE/DCC + CB/DB L2-bypass** → **not found in primary sources** (POTENTIALLY NOVEL)<br>4) "ajitter-señal jitter" relationship to I-03 → KNOWN VARIANT |
| **DOCUMENTAL depth** | 25+ primary/community sources cited in `PRIOR-ART.md` |
| **Patents** | NOT AUDITED in this pass (see §6 — flagged) |
| **RECOMMENDED STATUS** | **C** — refine scope to the IMR-specific claim before any development |

## 3. NOVELTY STATUS — RESUMEN POR NIVEL DE REUTILIZACIÓN

| Nivel de granularidad | Estado | Nota |
|---|---|---|
| **Objeto suelto** (layered sprites, per-object re-render) | KNOWN | Talisman (1996), Regan & Pose (1994), lengyel layers (1997), priority rendering |
| **Tile de hardware TBR** (16–32 px) | KNOWN | TBR/TBDR arquitectura; RE (HPCA'19) skips raster de tiles redundantes; TE (ARM) |
| **Dirty-rect / damage (compositor, UI, 2D)** | KNOWN | EGL_KHR_partial_update, VK_KHR_incremental_present, WebRender, vello/netrender, UI toolkits |
| **Tile software en IMR de escritorio (3D)** | **POTENTIALLY NOVEL** | No aparecen fuentes primarias que implementen skip de shading por tile en IMR de escritorio; los saves documentados son de ancho de banda (TBR), no de compute/fill en IMR |
| **"Nadie hace esto"** | NO CLAIMED | Se declara únicamente lo que la búsqueda no encontró |

## 4. ANÁLISIS RESUELTO POR COMPONENTE (I-02)

Véase `POLARIS12-FEASIBILITY.md` §3 para el detalle técnico. Resumen de vínculos con prior art:

- **DEPTH change detection** — HTILE (Polaris ya tiene metadata de tile de depth/resumen) + depth-buffer comparison → el mecanismo HW del resumen por tile es KNOWN (early-Z/hierarchical-Z); su uso **runtime entre frames** para el skip es lo no documentado.
- **MOTION detection** — velocity buffer / per-pixel cross-frame compare → KNOWN (TAA, FSR2, DLSS requieren motion vectors).
- **CAMERA movement** — affín global; el reuse de frame anterior bajo movimiento de cámara = reproyección sensu I-03 → KNOWN (reverse reprojection cache; TAA; Talisman affine warp).
- **DYNAMIC OBJECTS** — AABB/screen-space dirty boxes → KNOWN (damage rects; coherent layers; UID compositors).
- **PARTICLES / SHADOWS / LIGHTING** — estos NO se mueven con la geometría (shadow/reflection/particle motion es disjunto del MV de la superficie) → KNOWN limitation (DLSS4/FG, DLSS3 OFA, ATAA: TAA fails para shadows/reflections; Hanika: motion vectors imposibles para transparentías).
- **HUD / POST-PROCESSING** — HUD se puede separar (XeSS-FG composita HUD-less + UI); post global (bloom/blur) rompe el skip por tile salvo separación de capas → KNOWN technique (layered/compositor approach; XeSS HUD-less texture).

## 5. VEREDICTO RC-* (RÁPIDO)

| Métrica | Leyenda |
|---|---|
| **FEASIBILITY VERDICT (Polaris12/IMR)** | PARTIALLY FEASIBLE — como técnica de software en el harness sintético; alta dificultad en un engine general |
| **TECHNICAL PLAUSIBILITY** | HIGH (mecanismos individuales probados) / LOW-MEDIUM (combinación IMR: depende del cuello real del workload) |
| **IMPLEMENTATION COST** | HIGH (engine general) / LOW (workload sintético propio del proyecto) |
| **RISK** | Medium-High (artifacts de borde, semántica de buffer age, costo del pass de comparación, post-process global) |
| **DEPENDENCIES** | Harness sintético existente (F2), runner K, Vulkan, lecturas previo-frame color+depth; NINGUNA instalación nueva |
| **RECOMMENDED STATUS** | **C** (ver scale en §7) |

## 6. LIMITACIONES DEL AUDIT (transparencia)

1. **Patentes: NO auditadas** (no se consultaron bases de patentes en este pase). Se sabe que
   Transaction Elimination (ARM) y técnicas móviles asociadas son comerciales y muy probablemente
   patentadas. Si la combinación avanza a implementación comercial, se requiere audit de patentes aparte.
2. **"No encontré en 12+ búsquedas" ≠ "no existe"**: se declara solo lo que la búsqueda documental
   realmente cubrió (listado en `PRIOR-ART.md`).
3. Se corrige una cita tentativa: **`VK_EXT_dirty_region` NO existe en el registro Vulkan**
   (verificado contra `vk.xml` del repo oficial KhronosGroup/Vulkan-Docs, 2026-09-22). Las vías API
   reales para partial rendering / damage son `renderArea`, `VK_KHR_incremental_present`,
   `EGL_KHR_partial_update`/`EGL_EXT_buffer_age`, `VK_EXT_conditional_rendering`,
   `VK_EXT_discard_rectangles`, `VK_QCOM_tile_shading`.

## 7. ESCALA DE ESTADO RECOMENDADO (A/B/C/D/E)

- **A** — CONTRADICTED BY PRIOR ART / abandonar el claim.
- **B** — KNOWN tal como está formulado; usar como referencia, no como hipótesis propia.
- **C** — PARTIALLY NOVEL: refinar el alcance a un sub-claim específico y documentarlo.
- **D** — suficientemente concierto para formalizar una hipótesis concreta medible.
- **E** — pasar a diseño de experimento (FASE G/K) con el claim ya acotado.

---

## ANEXO — Formato ordenado (requerido por FASE R-3)

- **IDEA:** I-02 — Temporal Tile Delta Reuse.
- **NOVELTY STATUS:** PARTIALLY NOVEL.
- **KEY PRIOR ART (w/URLs):** lista completa en `PRIOR-ART.md`; highlights en §4 de este README.
- **OPEN SOURCE IMPLS:** vello/netrender/tileink, WebRender, FSR2, playdead temporal, GameTechDev TAA, Mesa/Zink damage plumbing (ver `PRIOR-ART.md` §7).
- **ACADEMIC:** RE (HPCA'19), LIBRA (MICRO'24), Talisman (SIGGRAPH'96), Regan&Pose (SIGGRAPH'94), coherent layers (1997), RRC (Nehab, Scherzer), render cache, incremental rendering VM, HiPR (2026).
- **COMMERCIAL:** ARM Transaction Elimination, TBR/TBDR móviles, Adreno FlexRender, compositors (Mutter/KWin EGL partial update), AMD DCC/HTILE.
- **POLARIS RELEVANCE:** alta para fill/shading-bound (512 shaders/16 ROPs); DCC+HTILE ya atacan bandwidth; L2-bypass de CB/DB implica que el ahorro real es de compute/fill, no necesariamente de bandwidth.
- **FEASIBILITY VERDICT:** PARTIALLY FEASIBLE (software, harness sintético; range restringido de escenas).
- **TECHNICAL PLAUSIBILITY:** MEDIUM (IMR general) / HIGH (escena estática-cámara).
- **IMPLEMENTATION COST:** LOW (sintético) — HIGH (engine).
- **RISK:** MEDIUM-HIGH.
- **DEPENDENCIES:** harness + runner K + Vulkan; sin instalaciones.
- **RECOMMENDED STATUS:** **C**.