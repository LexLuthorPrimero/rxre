# IDEA I-10 — ASYNC AUXILIARY RENDERER: PRIOR ART SURVEY

Novelty status per item tracked. Sources ranked: primary (papers, vendor docs, official SDKs) > community.

**Idea under audit:** "Ejecutar un *pipeline de render auxiliar* (segunda imagen: sombras, reflexión,
AO, Hi-Z, SSR, pre/post) en una cola **compute async (ACE)** en paralelo con la cola gráfica de un
IMR (Polaris12), para reducir el frametime."

**Concepto a no fundir:** NO es "compute-only renderer que sustituye a la GFX pipeline" (eso es I-04,
ROP-COMPUTE-OFFLOAD, ya CONTRADICTED). Es **co-programar** un auxiliar en la(s) cola(s) async.

---

## 1. HW: ASYNC COMPUTE EN GCN/POLARIS (el fundamento)

1. **AMD Polaris Architecture Whitepaper** (wccftech/AMD) — ACEs (Asynchronous Compute Engines),
   HWS (Hardware Scheduler), colas de dispatch paralelas, **compute unit reservation**, Quick
   Response Queue. Describe que el array de shaders se comparte entre colas → "asynchronous "
   no añade CUs, solo reordena/solapa pendientes.
   - https://www.techpowerup.com/gpu-specs/docs/amd-polaris-architecture.pdf
   - Status: KNOWN (primario vendor).

2. **AMD GDC17 "Advanced Shader Programming on GCN" / "Async Compute"** — presentación del modo
   recomendado: dispatch a cola compute mientras la GFX está ocupada; wave limiting, cache effects,
   cómo medir.
   - https://gpuopen.com/download/GDC2017-Advanced-Shader-Programming-On-GCN.pdf
   - Status: KNOWN (primario vendor).

3. **Otterness & Anderson (RTSS 2021), "Exploring AMD GPU Scheduling Details..."** — publicaron
   experimentos worst-case sobre ACE/HWS de chips GCN/RDNA: cuántos ACE, scheduling, colas por ACE.
   Relevante para "¿2 colas en Polaris12?" (confirmable por experimentación, no por ficha).
   - https://www.cs.unc.edu/~anderson/papers/rtss21.pdf https://doi.org/10.1109/RTSS52674.2021.00036
   - Status: KNOWN (académico).

4. **RADV docs (Mesa)** — estado de soporte: GFX8 (Polaris) → **Vulkan 1.4**; soporte de colas
   compute/async (ACE) y `VK_KHR_timeline_semaphore` en GFX8. Confirma que *mecánicamente* un
   Vulkan app en este chip puede crear cola compute adicional.
   - https://docs.mesa3d.org/drivers/radv.html
   - Status: KNOWN (primario driver).

## 2. SHIPPED / ENGINE USES (el corazón del análisis: la técnica YA se usa)

5. **DOOM (idTech6, Vulkan) — GDC 2016 / GPUOpen** — async compute para sombras+post mientras la
   GFX está en raster; ~7% ganancia de frame total (DF); "todos los pasos que no usan los CUs...
   computarlos en colas async".
   - https://gpuopen.com/learn/vulkan-and-modern-graphics-technology-doom/ (GPUOpen)
   - https://www.digitalfoundry.net/.../doom-vulkan (análisis comunitario)
   - Status: KNOWN (primario vendor+ingeniería).

6. **Cyberpunk 2077 — GDC 2023, "Building Night City" (CDPR)** — async-compute: **Hi-Z + SSAO
   durante los shadowmaps** en cola async, sync en fork-join; muestra *qué* es "auxiliar": pasos
   que pueden preceder al frame principal (SSR fuera de cola GFX).
   - https://media.gdcvault.com/gdc2023/Slides/Buildingnightcity_Tremblay_Charles.pdf
   - Status: KNOWN (primario).

7. **Frostbite FrameGraph — GDC 2017 (O'Donnell, DICE)** — el DAG de pasos *programa qué pasa a la
   cola async automáticamente*; async AO filtering; coste/BW shared; dependency edges. (El "¿qué
   tan automática es la decisión async?" → KNOWN y resuelto por DICE.)
   - https://www.ea.com/frostbite/news/frostbite-framegraph-extensible-rendering-architecture-in-frostbite
   - Status: KNOWN (primario).

8. **The Division 2 — GDC 2019 (AMD/Ubi)** — límites de async-compute: "async stalling the gfx
   pipe", en consola se *limita la ocupación* de async para no robar CUs; clasifica sombras como
   "ROP-heavy" (no async-friendly). Tabla clave para "qué auxiliar NO meter".
   - https://gpuopen.com/download/gdc-2019-agtd1-efficient-rendering-in-the-division-2.pdf
   - Status: KNOWN (primario vendor).

9. **Rockstar — "Game mech optimizations" (repo público)** — R* documenta SSR async (compute sobre
   buffers separados en cola async) en sus terceros: el patrón *"renderer auxiliar completo"* existe.
   - https://github.com/rockstar-games/game-mechanics-optimizations
   - Status: KNOWN (primario).

10. **Vulkan-Samples — async_compute** — ejemplo oficial Khronos de solapar un paso compute con el
    graphics pipeline en cola async (espera/join con semáforos).
    - https://github.com/KhronosGroup/Vulkan-Samples/blob/main/samples/perf/async_compute/
    - Status: KNOWN (primario Khronos).

11. **Khronos/Unofficial "Vulkan asynchronous compute" tutorial/blog** — patrones fork-join,
    "Ordering Guarantees", costo de semáforo/colas. (comunitario; confirmatorio.)
    - https://vkguide.dev/ y blogs de AMD.

## 3. SUB-CLAIM "AUXILIARY RENDERER" AÚN MÁS ESPECÍFICO (segunda apertura/segundo render del mundo en async)

- **R* async SSR** (§9) es el ejemplo más cercano de "un renderer de *reflexión* (segunda imagen del
  mundo desde la cámara, en buffers propios) en cola async".
- **Cyberpunk async SSR/Hi-Z/SSAO** (§6) idem.
- **No se encontró en fuentes primarias** una implementación *en Polaris12/RX550 específicamente*
  que *mida* overlap real con queues/ACEs (count `UNKNOWN`) + fetch-bound. Ese hueco de medición es documental (no de
  invención de la técnica).

## 6. BUSCADO Y NO ENCONTRADO (por FASE R-3)
Rutas: `async compute GCN overlap`, `AMD ACE two queues Polaris async renderer`, `auxiliary renderer
async compute Vulkan`, `async SSR`, `Cyberpunk async HiZ SSAO GDC`, `Frostbite FrameGraph async`,
`Division 2 async compute`, `DOOM Vulkan async`, `RADV async compute GFX8`, `Polaris12 overlap
measurement`, `RX550 async compute`, `render shadow async compute GCN`, `second virtual camera async`.
**No encontrado:** ninguna medición pública del *winner* de overlap en una Polaris12/8-CUs/2ACE con
cuello de fetch específico; toda la literatura es sobre chips grandes (≥36 CUs) o consolas.

## 7. VERDICT SUMMARY
| Sub-claim | Novelty | Feasibility Polaris12 |
|---|---|---|
| Async compute GCN (mecanismo) | KNOWN | Soporte confirmado (RADV GFX8, 2 colas) |
| Auxiliar async (AO/SSR/Hi-Z/shadows) | KNOWN / SHIPPED (Cyberpunk, R*, Frostbite, DOOM) | API ok; beneficio por medir |
| **Medición cuantitativa en Polaris12 fetch-bound** | No encontrada en primarias (documental gap) | Solo por experimentación (BERRETA/ASY-01) |
