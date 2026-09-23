# I-02 — PRIOR ART — TEMPORAL TILE DELTA REUSE

> Fuente primaria > comunidad. Fecha de búsqueda: 2026-09-22. Consultas base:
> "temporal tile reuse rendering", "temporal rendering reuse frame", "frame tile reuse",
> "dirty tile rendering", "partial frame rendering", "incremental rendering GPU",
> "temporal reprojection tile", "render target reuse frame", "static tile caching",
> "AMD render target reuse", "tile-based temporal reuse Vulkan", "tiled rendering delta
> compression", "frame coherence tiling", "Vulkan dirty region partial rendering",
> "EGL partial update", "VK_EXT_dirty_region".

---

## 1. ACADÉMICO — MICROARQUITECTURA TBR (el núcleo del estado del arte)

### 1.1 Rendering Elimination (RE) — HPCA 2019
Autores: Martí Anglada, Enrique de Lucas, Joan-Manuel Parcerisa, Juan L. Aragón, Pedro Marcuello, Antonio González (UPC).
Descubre redundancia de tiles entre frames ADELANTE de la rasterización mediante **signatures de los inputs del tile** y
**salta toda la Raster Pipeline** del tile redundante en una GPU TBR. Resultados: speedup **1.74×** y **43% energy** en
aplicaciones Android.

- DOI/arXiv: https://arxiv.org/abs/1807.09449
- HTML: https://arxiv.org/html/1807.09449v1
- PDF autor: https://people.ac.upc.edu/jmanel/papers/hpca-2019-RE.pdf
- Research report: https://www.ac.upc.edu/app/research-reports/html/RR/2019/5.pdf

> **Hallazgo clave para I-02:** el estudio CUANTIFICA frame-to-frame coherence: con movimientos de cámara moderados
> (>90% de tiles idénticos entre frames consecutivos, Figura 2 del paper). Cita además Transaction Elimination y
> Fragment Memoization como técnicas previas de explotación de la coherencia entre frames.

### 1.2 Transaction Elimination (TE) — ARM (técnica comercial)
TE compara una **signature de los colores de un tile** contra el frame previo y, si coinciden, evita la **escritura a
memoria** del tile. NO salta el shading; solo el writeback. Descrito y comparado en el paper RE (§1). Es una técnica
comercial en GPU móviles ARM. (Primary source: artículo RE; documentación ARM no recuperada en este pase.)

### 1.3 Fragment Memoization — Arnau et al.
Cache LUT de firmas de inputs de fragmento → hit reusa el color y evita el shader. Limitación: reuso de distancia de
una frame completa. Citado en RE. Predecesor directo a nivel fragmento.

### 1.4 LIBRA — MICRO 2024
Autores: Aurora Tomás, Juan L. Aragón, Joan-Manuel Parcerisa, Antonio González (UPC).
Scheduler de tiles que explota **frame-to-frame coherence para predecir tiles "hot/cold"** y emparajar el demand de
memoria. Confirma (>80% de tiles con <20% de diferencia de accesos DRAM entre frames).
- DOI: https://doi.org/10.1109/micro61859.2024.00081

### 1.5 Frame-to-frame coherence como fenómeno
Documentado en RE (Fig 2) y LIBRA (Fig 8). También en la survey de temporal coherence de Scherzer (ver §2.3).

---

## 2. ACADÉMICO — REUSO TEMPORAL DE IMAGEN (nivel píxel/imagen)

### 2.1 Real-Time Reprojection Cache (RRC) — Nehab et al. 2007 / Scherzer et al. 2007
Cache de shading en buffer full-screen; reproyección inversa para reusar cómputo de shading entre frames; hit-ratio
>90% típico. Base de teoría del "reuse" por reproyección (enlaza directamente con I-03).
- Princeton TR 749: https://www.cs.princeton.edu/techreports/2006/749.pdf
- Nehab et al. ACM: https://gfx.cs.princeton.edu/gfx/pubs/Nehab_2007_ARS/NehEtAl07.pdf
- GFX2008 (análisis overhead: 1/2/3-pass): https://www.cse.ust.hk/~psander/docs/scache.pdf

### 2.2 The Render Cache — Walter, Drettakis, Parker 1999
Cache de puntos sombreados + reproyección + sampling prioritario; **detecta regiones de cambio y concentra muestras**.
Antecesor conceptual del dirty-region en renderers progresivos.
- https://www.graphics.cornell.edu/~bjw/rencache.pdf

### 2.3 Temporal coherence survey — Scherzer et al. 2010/2012
Survey sistemática de explotación de temporal coherence (RRC, refresh, amortized sampling). Enlace a todas las técnicas
anteriores.
- https://www.cg.tuwien.ac.at/research/publications/2010/scherzer2010d/scherzer2010d-paper.pdf
- Journal version: https://www.cse.ust.hk/~psander/docs/tempcoj.pdf

### 2.4 An Incremental Rendering VM — ACM 2015
Capa incremental sobre OpenGL/DX con complejidad O(Δ) del cambio, mediante program synthesis. Reuso de resultado
entre frames a nivel de operaciones de comando.
- https://dl.acm.org/doi/10.1145/2790060.2790073

### 2.5 HiPR — SIGGRAPH 2026 RTL
Hierarchical Progressive Rendering: scheduling de tiles por prioridad tras una edición de escena; tiles sin transporte
descubierto **reusan la radiance del frame previo** hasta ser renderizados. Reuso temporal por tile en path tracing.
- https://graphics.cs.utah.edu/research/projects/hipr/HiPR-SIGGRAPH2026-RTL.pdf

---

## 3. ACADÉMICO / HISTÓRICO — HARDWARE QUE REUSA POR NIVELES/CAPAS

### 3.1 Talisman — Torborg & Kajiya, SIGGRAPH 1996 (Microsoft)
Arquitectura "chunked" (tiles 32×32) con **image layers que se reutilizan varios frames** y se warpean con affine en el
compositor; update rates variables por objeto; compresión TREC de chunks; y **reuso temporal = factor ~3×** de reducción
de rendering. La apuesta comercial más importante de temporal tile reuse en hardware de escritorio (nunca se vendió como GPU commodity pero sentó precedente).
- DOI: https://doi.org/10.1145/237170.237274
- MSR: https://www.microsoft.com/en-us/research/publication/talisman-commodity-realtime-3d-graphics-for-the-pc/
- Análisis: https://auth.vgamuseum.info/images/doc/unreleased/talisman_microreport.pdf

### 3.2 Priority Rendering / ARP — Regan & Pose, SIGGRAPH 1994
Address Recalculation Pipeline + image composition → **objetos se redibujan solo cuando su imagen cambia más que un
umbral** (θ_t). Reducciones de un orden de magnitud en objetos renderizados. Precedente directo de "re-render on change"
a nivel de objetos (no tiles).
- DOI: https://doi.org/10.1145/192161.192192

### 3.3 Rendering with Coherent Layers — Lengyel & Snyder, SIGGRAPH 1997
Factorización de capas + warps de imagen para reusar renders por varios frames; regulación fidelity/recursos con
fiducials. Documenta explícitamente: **shadows/reflections como capas separadas que se actualizan a distinta tasa**.
- DOI: https://doi.org/10.1145/258734.258856

---

## 4. MÓVIL / TBR — APIs Y EXTENSIONES DE "PARTIAL / DAMAGE"

### 4.1 EGL_KHR_partial_update + EGL_EXT_buffer_age
"Buffer damage" + edad de backbuffer → reparar solo lo obsoleto. Es la base de daño por rectángulos en compositores.
- https://registry.khronos.org/EGL/extensions/KHR/EGL_KHR_partial_update.txt

### 4.2 VK_KHR_incremental_present (VkPresentRegionKHR)
Damage rectangles para presentación (hereda EGL_KHR_swap_buffers_with_damage). **No re-renderiza**: optimiza el present.
- https://docs.vulkan.org/refpages/latest/refpages/source/VK_KHR_incremental_present.html

### 4.3 renderArea parcial en Vulkan (samsung dev article)
`renderArea` se usa explícitamente para "partial updates of dirty areas"; el tiler puede limitar procesado si el área
está alineada a la grilla de tiles (`vkGetRenderAreaGranularity`).
- https://developer.samsung.com/galaxy-gamedev/resources/articles/renderpasses.html

### 4.4 Khronos Vulkan-Guide — TBR best practices (loadOp/storeOp, TRANSİENT, lazy)
Loadop/storeOp DONT_CARE/LOAD para evitar cargar tiles si se sobrescribe todo, y guardar si se reusa.
- https://github.com/KhronosGroup/Vulkan-Guide/blob/main/chapters/tile_based_rendering_best_practices.adoc

### 4.5 VK_QCOM_tile_shading + Adreno FlexRender
Qualcomm puede operar IM o TBDR por workload. Expone tile memory y despachos por tile.
- https://docs.vulkan.org/refpages/latest/refpages/source/VK_QCOM_tile_shading.html

### 4.6 VK_EXT_conditional_rendering / VK_EXT_discard_rectangles
Mecanismos para no ejecutar comandos (conditional rendering) o descartar regiones (discard rects). Herramientas
relacionadas, no específicamente temporales.
- Conditional: https://github.khronos.org/Vulkan-Site/samples/latest/samples/extensions/conditional_rendering/README.html
- Discard: https://vulkan.lunarg.com/doc/view/1.4.350.1/linux/antora/refpages/latest/refpages/source/vkCmdSetDiscardRectangleEXT.html

### 4.7 VK_EXT_dirty_region — **NO EXISTE** (corrección)
Verificado contra el `vk.xml` oficial (repo KhronosGroup/Vulkan-Docs) el 2026-09-22: no hay extensión con ese nombre.
La única coincidencia textual en el registro es `dirtyIntraRefreshRegions` (video codec, no rendering). No citar como vía directa.

---

## 5. ESCRITORIO — DAMAGE TRACKING EN COMPOSITORS Y 2D (PRUEBA DE VIABILIDAD PRÁCTICA)

- **Zink/Mesa partial updates & damage**: plumbaa EGL partial update → VK_KHR_incremental_present en drivers de
  escritorio (llvmpipe/drisw/zink). Muestra que la infraestructura desktop existe.
  - https://www.phoronix.com/news/Zink-Partial-Updates-Damage
- **Mutter (GNOME) y KWin (KDE Plasma)** soportan EGL_KHR_partial_update (referido en el artículo de Phoronix).
- **Mozilla WebRender**: tile-cache con dirty/valid rects por tile en el compositor del navegador (GPU).
  - https://doc.servo.org/webrender/tile_cache/index.html
  - Struct `Tile` con `device_dirty_rect`, `world_valid_rect`: https://doc.servo.org/webrender/tile_cache/struct.Tile.html
- **vello/netrender** (renderer vectorial Rust + wgpu): TileCache con hashing de dependencias por tile, frame-stamping,
  eviction RETAIN_FRAMES; overlay de tiles dirty por debugging.
  - https://docs.rs/netrender/latest/netrender/tile_cache/index.html
  - Implementación: https://docs.rs/netrender/latest/src/netrender/tile_cache/mod.rs.html
- **tileink** (renderer vectorial): DamagePlan con changed_tiles, dirty ratios, full_redraw thresholds.
  - https://docs.rs/tileink/latest/src/tileink/wgpu/incremental.rs.html
- **webcore** (mock UI renderer tiled-scroll): tiles 512×512 lógicos reusadas durante scroll, invalidación por rect.
  - https://docs.rs/webcore/latest/src/webcore/renderer/tiles.rs.html
- **Blinc UI**: damage-aware compositor, blit de cache + re-dispatch de primitivas cambiadas con scissor.
  - https://blinc.rs/docs/architecture/gpu-rendering.html
- **Pulp partial repaint**: repaint solo de la región dañada con escalado a full si hay filtros/hazards.
  - https://generouscorp.com/pulp/partial-repaint.html
- **rust-damage-rects**: crate de acumulación/coalescing de dirty rects.
  - https://github.com/goliajp/rust-damage-rects

> Conclusión: a nivel **2D/compositor/UI**, el dirty-tile rendering es un estándar. A nivel **3D IMR desktop**, no se halló
> IMplementación de skip por tile.

---

## 6. COMERCIAL / COMPRESIÓN AMD (lo que Polaris12 ya hace — contexto crítico)

- **Delta Color Compression (DCC)** — AMD GPUOpen (2016). Compresión de render targets en bloques; el CB comprime/descomprime
  colors; "fast clears"; partial-writes (blend) requieren read-decompress-update-write. Vigente en RDNA3. **Polaris12/GCN
  es GCN1.2+ → DCC disponible.**
  - https://gpuopen.com/learn/dcc-overview/
- **RDNA3 Beyond current gen** — DCC blocks de 256B (bloques 8×8 @ 4BPE); escribidas parciales de bloque degradan la compresión;
  recomendación wave64/8×8 thread-groups. Aplica directamente a cómo se debe alinear una grilla de tiles para no romper DCC.
  - https://gpuopen.com/download/RDNA3_Beyond-the-current-gen-v4.pdf
- **Optimizing a AAA Vulkan game (2019)** — DCC se desactiva con VK_SHARING_MODE_CONCURRENT / VK_IMAGE_USAGE_STORAGE_BIT /
  MUTABLE_FORMAT; _SAMPLED_ reduce eficiencia; +5–10% en algunos títulos.
  - https://gpuopen.com/download/Vulkanised2019_06_optimising_aaa_vulkan_title_on_desktop.pdf
  - (Mismo, Khronos): https://www.khronos.org/assets/uploads/developers/presentations/06-Optimising-aaa-vulkan-title-on-desktop-May19.pdf
- **RADV DCC en GFX12/RDNA4 (2025)** — DCC como feature clave de performance p/ valide la relevancia continua.
  - https://www.phoronix.com/news/Mesa-RADV-Lands-RDNA4-DCC
- **HTILE** (hierarchical-Z de AMD, metadata por tile de depth): activa en GCN para early-Z/HSR; es la base HW del "depth
  change detection" por tile. (Documentación diminuta: se infiere del diseño GCN; no se halló doc primary en este pase —
  marcado como KNOWN por arquitectura, cita técnica indirecta en DCC/GPUOpen y en papers de compression de depth.)

---

## 7. OPEN SOURCE IMPLS (relacionados, ninguno = IMR desktop tile-skip)

| Impl | Nivel | Enlace |
|---|---|---|
| FSR2 (AMD, MIT) | temporal reuse p/ upscaling (no tile-skip) | https://gpuopen.com/fidelityfx-superresolution-2/ |
| Intel GameTechDev TAA (MIT) | reproyección temporal | https://github.com/GameTechDev/TAA |
| playdead/temporal (MIT) | TAA con reproyección | https://github.com/playdeadgames/temporal |
| vello/netrender/tileink | tile-cache 2D | ver §5 |
| Mozilla WebRender | tile-cache compositor | ver §5 |
| Mesa/Zink | damage plumbing desktop | https://www.phoronix.com/news/Zink-Partial-Updates-Damage |
| Magpie (MIT) | upscaler externo (discute reproyección sin MV) | https://github.com/Blinue/Magpie/discussions/375 |
| Fwog (MIT) | ejemplo reproyección con jitter en compute | https://github.com/JuanDiegoMontoya/Fwog/blob/main/example/shaders/rsm/Reproject.comp.glsl |

---

## 8. PATENTES

**NO auditadas en este pase.** Notas: (1) Transaction Elimination (ARM) y otras técnicas de bandwidth móviles son
comerciales y es prudente asumir cobertura de patentes; (2) Rendering Elimination es trabajo académico UPC (posible
patente no verificada). Cualquier desarrollo posterior del claim IMR requiere audit de patentes separado. Estado de ese
eje: **NOVELTY UNKNOWN (patentes)**.

---

## 9. SÍNTESIS PARA I-02

1. La **metodología** (dirty tracking por tile, firmas, reuso de resultados previos, damage rects) es **KNOWN** y madura.
2. El **dominio** donde es nativo es TBR/TBDR móvil (RE) y composición/UI 2D (WebRender, vello, compositors).
3. Lo **no documentado** en las fuentes encontradas: una implementación de **skip de shading/fill por tile en un IMR de
   escritorio commodity (Polaris12)** con interacción explícita con **DCC/HTILE y la ruta CB/DB que bypassa L2**.
   Ese es el único hueco genuino → **POTENTIALLY NOVEL** solo en ese alcance. TODO lo demás es KNOWABLE por el corpus
   citado.