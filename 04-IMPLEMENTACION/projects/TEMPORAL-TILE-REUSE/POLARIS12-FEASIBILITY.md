# I-02 — POLARIS12-FEASIBILITY — TEMPORAL TILE DELTA REUSE

> Fecha: 2026-09-22 · FASE R-3 · DOCUMENTAL ONLY
> Hardware de referencia: RX 550 (Polaris12 / GFX8 / GCN 1.2+), PCI 1002:699f, amdgpu, 35W cap,
> SCLK 1071 MHz, MCLK 1500 MHz, 128-bit GDDR5.

## 1. HECHOS POLARIS12 RELEVANTES (entorno aportado, no verificado en este pase)

| Hecho | Implicación para I-02 |
|---|---|
| **IMR** (no TBR). Rasterización de primitivos en orden de entrada | No hay "tile de HW" nativo → la grilla de tiles es **software** |
| 8 CUs / 512 shaders, 16 ROPs, 2 RBs | Bajo compute + bajo fill: el skip de shading/fill ES el recurso más caro de ahorrar |
| L2 512 KB (2×256 KB) | Pequeño; agenda cache-friendly |
| **CB/DB bypassan L2** (color/depth writes → memory controller directo) | (a) escribir un tile cuesta DRAM siempre; evitar escritura = ahorro real de banda; (b) leer el frame previo para comparar = coste DRAM (mitigable con DCC si el buffer sigue comprimido); (c) no hay writeback cache que "coalesca" writes repetidos |
| DCC (GCN1.2+, 256B blocks) | Apply partial-writes rompen compresión de bloque → **una grilla de tiles alineada a 256B** evita decompress/recompress por bloque; +S beschrieb dazu en riesgo w/ loading DCC buffer |
| HTILE (hierarchical-Z por tile 8×8) | Mecanismo HW de resumen de depth por tile: base ya existente para "did depth change here?" |
| V$ 16 KB/CU (textura) | Cache de texturas por CU; un tile-reuse no toca esto (shading skip tampoco lee texturas) |
| 128-bit GDDR5, MCLK 1500 MHz | Bandwidth limitada (~96 GB/s); DCC + skip de tile ahorran ambos |

> Pitfall de lectura: en Polaris12 DCC está **no deshabilitado** por defecto para render targets Vulkan usados solo como
> color (shared_mode exclusive, sin storage, sin mutable → DCC activo). Si el experimento crea los buffers "previous frame"
> con VK_SHARING_MODE_CONCURRENT o VK_IMAGE_USAGE_STORAGE_BIT, DCC se apaga y se pierde la ventaja (ver GPUOpen RDNA3/AAA docs, PRIOR-ART §6).

## 2. ¿QUÉ SIGNIFICA "REUSAR UN TILE" EN IMR (vs TBR)?

En **TBR/TBDR**: el HW tiene el tile en tile-memory; "reusar" = no escribir a memoria (Transaction Elimination) o no
rasterizar (Rendering Elimination). La ganancia de RE viene de saltar **raster + shader** + no escribir.

En **IMR (Polaris12)** NO existe esa granularidad HW. Reusar = una de estas tres estrategias de software:

| Estrategia | Descripción | Estado |
|---|---|---|
| (a) **No redibujar** — preservar el frame que ya está en el backbuffer y pintar solo regiones cambiadas | Requiere preservación del contenido previo (memoria) + loadOp LOAD para depth/color por región + scissor/renderArea | Método conocido en estándares EGL partial update / renderArea; **el swapchain de Vulkan estándar NO garantiza preservación** (buffer age es EGL-only; con VK_KHR_swapchain solo el contenido previo "típicamente" persiste, sin garantía formal) |
| (b) **Verificar cambio y saltar geometría** — cull/prune de draw calls cuyo screen-space impacto está en tiles sin cambio | Equivale a occlusion culling *temporal* a nivel CPU/compute; pasa de O(frame) a O(Δ); requiere predict de extents por objeto | Precedente: priority rendering (Regan&Pose), coherent layers, culling jerárquico estándar; la variante *temporal* (no HSR geométrica) es rara |
| (c) **Comparar tiles y <skip> del pixel shading** | En IMR no se puede "saltar" un píxel a mitad de pipeline; el compare es UN PASO ADICIONAL, no un skip | Solo en TBR el compare sale gratis a nivel de pipeline; en IMR el compare cuesta tan caro (leer frame completo) que la viabilidad depende del cuello real (F2) |

**Conclusión arquitectural:** la única vía rentable en IMR parece (b): usar el cambio temporal para **dejar de emitir
trabajo** (draw calls/compute de regiones sin cambio), no para "saltar" trabajo ya emitido. La vía (c) es anti-viable en
IMR salvo que el compare sea delta-driven sobre regiones candidatas (las ya sabidas dinámicas).

## 3. ANÁLISIS POR COMPONENTE (re-suelto para Polaris12)

### DEPTH change detection
- HTILE da resumen por tile; pero HTILE es acel. HW de depth test, no una "historia" entre frames. Para detección
  temporal hace falta **comparar el depth buffer N-1 vs N** (o hacer signature por tile del depth, como hace RE con los
  inputs del tile).
- Coste en IMR: un compute pass por tile de 32×32 con hash = lectura DRAM de depth (con L2-bypass de DB... el depth
  buffer se lee via shader **con** L2, es read-only aquí) → coste ligero, pero hay que emitirlo cada frame.
- El dato útil NO es "depth cambió" sino **"qué tiles quedaron igual entre N-1 y N"** (para saltar su re-render).

### MOTION (change) detection
- Alternativas: (1) velocity buffer como señal auxiliar (los píxeles cuya MV ≈ MV estimada de cámara son "locked");
  (2) color/depth compare por tile (dos lecturas full-frame); (3) app-level dirty boxes.
- En el harness sintético, la fuente de verdad del "dirty" es el **app-level** conhecimento del escenario (mejor y más
  barato); el compare por tile solo sirve como *ground truth* o para medir.

### CAMERA movement
- Si la cámara se mueve, casi nada es idéntico: hay shift global + disocclusion. El reuse "exacto de tile" solo aplica a
  cámara estática o a regiones donde el movimiento no alcanza (o se reusa vía reproyección, tema de I-03).
- **Con cámara estática** (la mayor parte del tiempo en el harness sintético/escenas de referencia): la proporción de
  tiles idénticos puede llegar a >90% (RE Fig 2) → máximo upside.

### DYNAMIC OBJECTS
- AABB en screen-space → dirty box → re-render región + preservar el resto. Técnica estándar en UI/compositors
  (rust-damage-rects, WebRender). En 3D, la dificultad añadida: sombras/iluminación global (ver siguiente) y el depth
  buffer no se puede preservar por simple scissor si hay primitivos atravezando la caja.

### PARTICLES / SHADOWS / LIGHTING
- El movimiento de una sombra NO es el MV de la superficie que la proyecta (TAA survey; ATAA; DLSS4/FG). Una partícula
  cambia píxeles sin razón geométrica. La iluminación dinámica (point lights) revenue regional.
- => el dirty tracking por geometría **subestima el cambio perceptual**: si se re-renderizan tiles "sin cambio geométrico",
  las sombras/partículas que les pasan por encima rompen la coherencia. Solución documentada: capas separadas
  (Lengyel-Snyder '97; XeSS-FG HUD-less). Es el mayor risco de correctness.

### HUD / POST-PROCESSING
- HUD estático = tiles perfectamente reusables; pero si el post-proceso (Bloom, DoF, Tonemap) es **full-frame**, el skip de
  tiles no afecta al coste de los passes de post (que ya son dominantes en 720p/1080p en este hardware).
- Separación de capas (render HUD en su propio target y componer al final) es la solución estándar; pero requiera un
  re-architect del pipeline del harness.

## 4. VEREDICTO DE VIABILIDAD EN POLARIS12

| Pregunta | Respuesta |
|---|---|
| ¿El ahorro es de compute/fill o banda? | Ambos, pero el win más limpio es **compute/fill** (512 shaders/16 ROP): saltar tiles = no emitir fragmentos. La banda del write ya está cubierta por la escritura innegable del frame; el ahorro de banda es principalmente el **no re-leer** texturas de la región saltada (bye fetch-bound, ver hallazgo F2). |
| ¿Vale la pena el pass de comparación? | Solo si no requiere leer el frame completo a DRAM cada frame (coste ~ 1 lectura full) — en harness sintético es aceptable; en general NO. Mejor usar app-level dirty boxes + HTILE hints. |
| ¿Granularidad del tile? | **32×32 px**, múltiplo de 8 (HTILE) y alineado a bloques DCC de 256B: buffer RGB8 de 32×32 = 4 KB → abarca horas DCC blocks enteros (32×32×(4B)=4096B → 16 bloques de 256B alineados). |
| ¿Preservación del backbuffer? | Vulkan estándar no garantiza buffer age; en el harness (no swapchain de pantalla real o usando present-modo de age) se puede garantizar manteniendo el frame previo en imagen propia sin presentar → **no es un blocker para el estudio de performance**, sí lo es para "skipping a pantalla" real. |
| ¿DCC interplay? | Mantener el frame previo comprimido (DCC) hace que leerlo para el compare sea barato; **no usar** CONCURRENT / STORAGE en esas imágenes. |
| ¿Dónde ganamos seguro (solo documentado en escenas de cámara estática)? | HUD/menú, RTS idle, vistas estáticas, "condiciones de referencia" del harness (F1/F2). En FPS con cámara libre, el upside se evapora (más disocclusion que tiles idénticos). |

**Veredicto: PARTIALLY FEASIBLE.** La técnica vive en un subconjunto de escenas (cámara indentada/estática, componentes
globales separados) y en el harness sintético; como técnica general de un engine de FPS 3D es anti-viable por post-full-frame
y por la imposibilidad de skip a mitad de pipeline en IMR.

## 5. NÚMEROS PRE-ANALÍTICOS (estimaciones de documento, NO medidas)

- Skip de tiles con densidad d (fracción de tiles cambiados): shade cost ≈ d × full; fill cost ≈ d × full (si regiones
  alineadas y DCC intacto).
- Compare pass full-frame ≈ 1 full read (colors) + hash reduction; en un buffer 1280×720: ~3.7 MB de lectura en color
  DCC-comprimido (~algunos cientos de KB reales si DCC activo) → order de décimas de ms, ~1–3% de budget → aceptable si
  d < 0.5–0.6.
- Presupuesto p/ 720p en Polaris12 (del contexto F1/F2 del proyecto): sombre el cuello de fetch; un skip de shading no
  reduce fetch salvo que la región saltada hubiera leído texturas → beneficio real depende de la densidad de textura-reads.
- Predicción de modelo: frametime(re-render parcial) ≈ coste_{draws cambiados} + coste_{compare} + overhead_{renderArea/scissor}
  vs frametime(full) — la diferencia materializa el máximo upside.

## 6. CONCLUSIONES DE VIABILIDAD

1. **Granularidad tile**: 32×32 software, alineado DCC/HTILE, definido en el harness; ver EXPERIMENT-DESIGN §2.
2. **La única vía rentable en IMR**: (b) próxima, no (c); es un "temporal culling / partial redraw", no un "skip HW".
3. **Las esquinas de correctness**: sombras/partículas (cambio perceptual sin cambio geométrico) y post full-frame.
4. **El backbuffer-previo debe ser una imagen propia** (no swapchain) preservada cada frame, con loadOp LOAD en depth y
   color si se reúne con renderArea parcial.
5. **DCC** es tanto aliado (frame previo comprimido) como trampa (usos de imagen que lo desactivan; partial-write de
   bloques). El harness debe respetar las reglas de GPUOpen.

Estado: **C** — refinable a un claim medible acotado a "partial redraw temporal en IMR Polaris12 para escenas de cámara
estática con splits por tile 32×32 alineado DCC/HTILE".