# FASE F — GEOMETRY INVESTIGATION — Documento de Diseño

> **Archivo:** `FASE-F-GEOMETRY-INVESTIGATION-DESIGN.md`
> **Fase:** FASE R-2 — COMPLETE PROJECT DOCUMENTATION & ECOSYSTEM ARCHITECTURE (R-2.4)
> **Fecha:** 2026-09-22 — Modo SOLO DOCUMENTAL (DISEÑO; NO ejecutado)
> **Clasificación:** [DISEÑADO] — protocolos completos por candidato GEO-01..08.
> **Estado global:** **PENDIENTE de ejecución**. Fuente de candidatos: `experiments/POLARIS12-MAP/EXPERIMENT-CANDIDATES.md` (v1.0, 2026-09-21).

---

## 1. Objetivo

Diseñar la investigación de **geometría** (rasterización/primitivas/vertex/instancing/culling) sobre
Polaris12 para discriminar qué etapa del front-end de geometría es el cuello real, conectando con la
evidencia histórica (E3/E5/E5b: geometría = coste dominante >1.26×; FASE D etapa 2: vgt/pa/sh ≈ 29–39 %
y sx 86 % en el brazo A vs 0 % en B; R-15 Superposition: diferencia = geometría/vertex/post-proceso real).

## 2. Alcance y límites

- **SÍ:** diseño de los 8 experimentos GEO-01..08 (hipótesis, mecanismo, contador potencial, workload
  necesario, variables, controles, riesgos, confounders, criterios de éxito/resultado negativo,
  dependencias). Clasificación de prioridad en la Matriz J.
- **NO (sin autorización):** ejecutar, programar contadores, instalar software, modificar Mesa, sheds del
  sistema, escritura sysfs fuera de corrida autorizada. Varios candidatos piden `radeontop` (read-only) o
  pipeline stats de Vulkan — los primeros requieren que FASE K (Lab) exista y los segundos pueden hacer
  uso de extensiones de Vulkan desde el workload, pero nada se ejecuta hoy.
- **Regla 19:** todos los candidatos respondieron el checklist de 8 preguntas en su fuente
  (EXPERIMENT-CANDIDATES.md §9); en este diseño se deja **explícito** por candidato. Si en la revisión
  actual algún punto cambia (ej. "mesa/amdgpu mod"), se refleja abajo.

## 3. Candidatos GEO-01..08 — Fichas de diseño

> Convención de validación: **CONFIRMADO/REFUTADO** son juicios al PROMOVER un resultado; en el diseño se
> escribe la condición de cada uno sin afirmarlo. **HIPÓTESIS** es el estado previo de todos.

### GEO-01 — Vertex Throughput
- **HIPÓTESIS DESEADA:** vertex shader pesado + muchos draws satura el front-end VS/IA.
- **MECANISMO TARGET:** unidades VS (y pipeline IA→VGT) del GCN; no hay contador directo sin programar —
  proxy: `vertex_busy` (radeontop) + VS invocations (pipeline stats Vulkan).
- **CONTADOR POTENCIAL (FASE M, solo documentación):** SPI PERF_VS_BUSY=1 / VS_WAVE=10; SQ_VS PERF_SEL_WAVES=4.
- **WORKLOAD NECESARIO:** workload GRÁFICO custom (DISEÑADO en `WORKLOAD-SINTETICO/DESIGN-GRAPHICS.md`)
  con `vkCmdDrawIndexedIndirect` para evadir el CPU-bottleneck de draw calls; VS con depth de ALU variable
  y fetches; `instanceCount` como palanca.
- **VARIABLE INDEPENDIENTE:** complejidad VS (nº de ALU ops, nº de texture fetches) × `instanceCount`.
- **VARIABLE DEPENDIENTE:** FPS, frametime p50/p99, `vertex_busy`, VS invocations.
- **CONTROL:** FS simple, 1920×1080, MSAA 1x, 4 layers; seeds/duraciones de la tabla de control común.
- **RIESGO:** CPU-bottleneck de draw calls → mitigado con `vkCmdDrawIndexedIndirect` (documentado).
- **CONFOUNDERS:** diferencia de shader ESB (Early Significance Break), compilación de shader (ACO), cache
  de instrucciones; coexistencia con FS.
- **CRITERIO DE ÉXITO:** FPS ↓ correlaciona con `vertex_busy` ↑ y VS invocations ↑.
- **CRITERIO RESULTADO NEGATIVO:** FPS estable con `vertex_busy` bajo → VS NO es cuello.
- **DEPENDENCIAS:** workload gráfico (R-2.9 / DESIGN-GRAPHICS), pipeline-stats Vulkan (implementable en el
  mismo workload), Lab K para telemetría estable. **Root: No.**

### GEO-02 — Primitive Throughput
- **HIPÓTESIS DESEADA:** triángulos microscópicos (1–16 px) saturan rasterizer/primitive assembly.
- **MECANISMO TARGET:** PA/SC (primitive assembly/rasterizer); proxy: `rasterizer_busy` (radeontop) +
  INPUT_ASSEMBLY_PRIMITIVES (pipeline stats).
- **CONTADOR POTENCIAL (FASE M):** PA_SU0 PERF_PAPC_PA_INPUT_PRIM=8, PA_SU0 PERF_PAPC_CLPR_CULL_PRIM=14;
  PA_SC QZ0_QUAD_COUNT=163.
- **WORKLOAD NECESARIO:** workload gráfico; VS passthrough, FS simple; primitivas de 1,2,4,8,16 px a
  densidad fija y primitivas/frame.
- **VARIABLES:** tamaño de primitiva × primitivas/frame.
- **DEPENDIENTES:** FPS, `rasterizer_busy`, primitive rate (pipeline stats).
- **CONTROL:** 1920×1080, FS simple, VS passthrough.
- **RIESGO:** tamaño de *vertex buffer* grande → GTT/VRAM (registrar `mem_info_gtt_used`).
- **CONFOUNDERS:** culling de primitive assembly (PAPC) puede descartar trabajo antes del raster; cache de
  IA.
- **CRITERIO DE ÉXITO:** FPS ↓ con primitivas pequeñas y `rasterizer_busy` → 100%.
- **CRITERIO RESULTADO NEGATIVO:** FPS estable, `rasterizer_busy` < 50% → PA/SC no es el cuello.
- **DEPENDENCIAS:** workload gráfico + pipeline stats. **Root: No.**

### GEO-03 — Index/Vertex Buffer Bandwidth
- **HIPÓTESIS DESEADA:** streaming de VBO/IBO grandes estresa PCIe/GTT/VRAM bandwidth.
- **MECANISMO TARGET:** rutas de memoria (fetch de vertex/index desde VRAM/GTT/host).
- **CONTADOR POTENCIAL (FASE M):** TCC/TCP (mem reads de vertex fetch) — ver FASE M; sin programación hoy.
- **WORKLOAD NECESARIO:** workload gráfico con VBO/IBO variables (64 MB…1 GB) y frecuencia de update.
- **VARIABLES:** tamaño VBO/IBO × upgrade frequency (frame/frame vs estático).
- **DEPENDIENTES:** FPS, `mem_busy`, `mem_info_gtt_used`/vram, (PCIe counters via lspci si existen).
- **CONTROL:** draw simple, VS/FS simples.
- **RIESGO:** OOM si excede VRAM/GTT → controlar con presupuesto de memoria; device lost.
- **CONFOUNDERS:** caché de vértices (vertex reuse), prefetch HW, y el modo de `mem_busy` del driver.
- **CRITERIO DE ÉXITO:** FPS correlaciona con tamaño de buffer y `mem_busy` ↑.
- **CRITERIO RESULTADO NEGATIVO:** FPS estable, `mem_busy` bajo → bandwidth de buffers no es cuello.
- **DEPENDENCIAS:** FASE G (modelo de memoria) para interpretación. **Root: No.**

### GEO-04 — Instancing
- **HIPÓTESIS DESEADA:** instancing masivo (100k+ instances) revela VS throughput vs overhead de instancing.
- **MECANISMO TARGET:** VS por-instance (VGT→VS wave) vs overhead de setup.
- **CONTADOR POTENCIAL (FASE M):** VS invocations (SQ_VS WAVES), VGT.
- **WORKLOAD NECESARIO:** workload gráfico; `vkCmdDrawIndexed` con instanceCount 100..1M, VS per-instance.
- **VARIABLES:** instance count × trabajo VS per-instance.
- **DEPENDIENTES:** FPS, `vertex_busy`, VS invocations, overhead de draw.
- **CONTROL:** 1 draw call, 1 VBO + instance buffer, FS simple.
- **RIESGO:** instance buffer size.
- **CONFOUNDERS:** si el FS es trivial, el overhead de post-raster puede dominar; y el orden de waves.
- **CRITERIO DE ÉXITO:** FPS escala linealmente con instances hasta un tope VS.
- **CRITERIO RESULTADO NEGATIVO:** FPS plano → overhead dominante (instancing no es path crítico).
- **DEPENDENCIAS:** workload gráfico. **Root: No.**

### GEO-05 — Many Small Primitives (Overdraw Geométrico)
- **HIPÓTESIS DESEADA:** overdraw geométrico real (vs fragment-only) estresa ROP + early-Z + HTILE.
- **MECANISMO TARGET:** render back-end (CB) + depth pipeline (DB/HTILE).
- **CONTADOR POTENCIAL (FASE M):** CB PERF (export/quad), DB _QUAD_COUNT, SX.
- **WORKLOAD NECESARIO:** workload gráfico con capas geométricas solapadas (1,4,16,64) y depth complexity.
- **VARIABLES:** capas × primitivas solapadas × depth complexity.
- **DEPENDIENTES:** FPS, `rop_busy`, `depth_busy`, overdraw factor (FS_invocations / píxeles).
- **CONTROL:** VS/FS simples, depth attachment, early-Z habilitado, MSAA 1x.
- **RIESGO:** bajo (solo carga).
- **CONFOUNDERS:** early-Z efectivo (depende de orden de dibujo y del shader), HTILE enable dinámico.
- **CRITERIO DE ÉXITO:** overdraw ↑ → FPS ↓ con `rop_busy`/`depth_busy` ↑.
- **CRITERIO RESULTADO NEGATIVO:** FPS estable con `rop_busy` bajo → render back-end no es cuello.
- **DEPENDENCIAS:** workload gráfico. **Root: No.**

### GEO-06 — Large Triangles (Viewport Culling)
- **HIPÓTESIS DESEADA:** triángulos gigantes prueban viewport culling/scissor/viewport transform.
- **MECANISMO TARGET:** clip/vieWport geometry; proxy radeontop `rasterizer_busy`.
- **CONTADOR POTENCIAL (FASE M):** PA_SC (primitive y quad), PA_SU clipper (CLPR counts).
- **WORKLOAD NECESARIO:** workload gráfico con triángulos 1.5x,2x,4x,10x viewport; config viewport/scissor.
- **VARIABLES:** tamaño de triángulo × configuración viewport/scissor.
- **DEPENDIENTES:** FPS, `rasterizer_busy`, primitive throughput.
- **CONTROL:** VS/FS simples.
- **RIESGO:** bajo.
- **CONFOUNDERS:** el clip puede descender a réplicas de Quadrascan; dependencia del modo de clip preciso.
- **CRITERIO DE ÉXITO:** triángulos > viewport → culling eficiente y FPS estable.
- **CRITERIO RESULTADO NEGATIVO:** FPS degrada → no hay culling eficiente (investigar por qué).
- **DEPENDENCIAS:** workload gráfico. **Root: No.**

### GEO-07 — Geometric Overdraw (Depth + Layers)
- **HIPÓTESIS DESEADA:** overdraw con depth test real prueba early-Z / HTILE efficiency.
- **MECANISMO TARGET:** early-Z/HTILE (DB) vs blending aditivo (CB).
- **CONTADOR POTENCIAL (FASE M):** DB `_QUAD_COUNT` (P0/P1/P2/P3_HIZ_QUAD_COUNT), PA_SC EARLYZ_QUAD_COUNT.
- **WORKLOAD NECESARIO:** workload gráfico: capas con depth (1,4,16), depth func (LESS/ALWAYS), early-Z forzado,
  con attach de profundidad.
- **VARIABLES:** capas × depth fun c × early-Z forzado.
- **DEPENDIENTES:** FPS, `depth_busy`, `rop_busy`, early-Z rate (si medible).
- **CONTROL:** VS/FS simples, depth attachment, HTILE.
- **RIESGO:** bajo.
- **CONFOUNDERS:** el driver puede deshabilitar early-Z por writes en el FS (evitar), el reorder de
  depth streams.
- **CRITERIO DE ÉXITO:** early-Z reduce FS invocations → FPS > blending aditivo.
- **CRITERIO RESULTADO NEGATIVO:** mismo FPS que blending → early-Z inefectivo (RADV workaround, ver FASE H).
- **DEPENDENCIAS:** FASE H (workaround MSAA/early-Z). **Root: No.**

### GEO-08 — Vertex + Fragment Simultáneo
- **HIPÓTESIS DESEADA:** carga balanceada VS+FS revela bottleneck compartido (scheduler, cache, bandwidth).
- **MECANISMO TARGET:** contendencia en schedulers/SIMDs/cache compartidos.
- **CONTADOR POTENCIAL (FASE M):** SPI VS/PS busy+wave, SQ busy, GRBM GUI_ACTIVE.
- **WORKLOAD NECESARIO:** workload gráfico con matriz 3×3 (VS low/med/high × FS low/med/high).
- **VARIABLES:** VS complexity × FS complexity (9 celdas).
- **DEPENDIENTES:** FPS, `vertex_busy`, `shader_busy`, `mem_busy`, frametime.
- **CONTROL:** 1920×1080, MSAA 1x, 1 layer.
- **RIESGO:** bajo.
- **CONFOUNDERS:** FLEXIBILIDAD de programación (hardware puede ejecutar VS en paralelo a FS), interhazes
  de UB/cache compartida dominate las mediciones simples.
- **CRITERIO DE ÉXITO:** FPS limitado por min(VS, FS, bandwidth) — se identifica la etapa que domina.
- **CRITERIO RESULTADO NEGATIVO:** FPS determinado por una sola etapa → cuello único, no compartido.
- **DEPENDENCIAS:** resultados GEO-01, GEO-02, GEO-05 para interpretar los dominios. **Root: No.**

## 4. Variables de control común (heredadas de EXPERIMENT-CANDIDATES.md §Variables de Control)

Resolución 1920×1080 · Layers 4 (salvo GEO-08=1) · Textures 4×4096² · Seeds fijas `0x13579BDF`/
`0x2468ACEO` · Warmup 5s · Duration 20s · MSAA 1x (salvo experimento MSAA, FASE F fuera de scope) ·
Mesa SYSTEM (congelado) · Kalm estado real a registrar · power1_cap 35,000,000 µW · DPM auto.

## 5. Reglas de interpretación

- **Correlación ≠ causalidad.** Un resultado de GEO-05/07 que "soporta" ROP/DB es únicamente
  **CONSISTENTE CON** hasta no aislar la unidad con contadores o con un experimento de exclusión.
- Todo experimento F se registra con la plantilla `EXPERIMENT ID: GEO-XX-rN` y clasificación
  VALID/INVALID/OUTLIER/REPEATABLE de FASE E §5.6.

## 6. Relación con la Matriz J

Los 8 candidatos pasan a `EXPERIMENT-PRIORITY-MATRIX.md` (§R-2.8) con criterios: valor informativo,
dependencias, riesgo, reversibilidad, reproducibilidad, coste, calidad de métricas, evidencia previa,
capacidad discriminatoria, riesgo de confounders → salida ALTA/MEDIA/BAJA/BLOQUEADOS.

## 7. Conclusión del diseño

FASE F queda **DISEÑADA** (8 fichas completas) y **PENDIENTE**. Ningún GEO-XX ha sido ejecutado ni
validado. La evidencia histórica (E3/E5b, FASE D, R-15) sugiere priorizar GEO-01/02 (vertex/primitivas)
y GEO-05/07 (render-back-end/depth), pero eso es una **selección informada para la Matriz J**, no un
resultado experimental.