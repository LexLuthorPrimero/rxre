# EXPERIMENT-CANDIDATES.md — Experimentos Candidatos Derivados del Mapa

> **IDEAS DEL USUARIO (fuera de alcance de este documento):** 184 ideas
> originales del usuario (`R-NEW-*`, `METH-NEW-*`, `N-INT-*`) están
> clasificadas y trazadas en `../../IDEA-REGISTER.md`. Este documento sigue
> siendo exclusivamente el registro de **candidatos de experimento** con
> checklist de 8 preguntas. Las ideas no se convierten en candidatos aquí sin
> pasar el checklist.

**Fecha:** 2026-09-21
**Versión:** 1.0
**Regla:** NO ejecutar. Solo documentar. Cada candidato debe responder al checklist de 8 preguntas (Regla 19).

---

## Checklist Obligatorio (Regla 19) — Para CADA Candidato

Antes de proponer un experimento, responder **SÍ** a TODAS:

1. ¿Existe en Polaris12?
2. ¿Está disponible en nuestra pila Linux/RADV?
3. ¿Puede utilizarse desde software?
4. ¿Es relevante para un cuello de botella real?
5. ¿Podemos medir su efecto?
6. ¿Es reversible?
7. ¿Cuál es el coste/riesgo?
8. ¿Existe evidencia de que pueda mejorar rendimiento?

Si alguna respuesta es NO → **DESCARTAR** o marcar como **DESCONOCIDO**.

---

## Categoría 1: GEOMETRÍA (GEO-01 a GEO-08)

### GEO-01: Vertex Throughput
- **Hipótesis**: Vertex shader pesado + muchos draw calls satura vertex processing → revela bottleneck VS/IA
- **Variable**: Complejidad VS (ALU, texture fetches) + `instanceCount` / draw calls
- **Constantes**: FS simple, resolution 1920x1080, MSAA 1x, 4 layers
- **Métrica**: FPS, frametime, `vertex_busy` (radeontop), VS invocations (pipeline stats)
- **Herramienta**: `VkQueryPool` pipeline statistics (`VK_QUERY_PIPELINE_STATISTIC_VERTEX_SHADER_INVOCATIONS_BIT`)
- **Confirmación**: FPS ↓ correlaciona con `vertex_busy` ↑ y VS invocations ↑
- **Refutación**: FPS estable, `vertex_busy` bajo
- **Riesgos**: CPU bottleneck en draw calls (mitigar: `vkCmdDrawIndexedIndirect`)
- **Root**: No
- **Recompilación**: Vertex shader
- **Mesa/amdgpu mod**: No
- **Reversible**: Sí
- **Evidencia**: GPUOpen "Graphics Work Distribution" — VS waves 1 per CU

### GEO-02: Primitive Throughput
- **Hipótesis**: Triángulos microscópicos (1-2 px) saturan rasterizer/primitive assembly
- **Variable**: Tamaño primitiva (1px, 2px, 4px, 8px, 16px), primitivas/frame
- **Constantes**: VS simple (pass-through), FS simple, 1920x1080
- **Métrica**: FPS, `rasterizer_busy`, primitive rate (pipeline stats: `INPUT_ASSEMBLY_PRIMITIVES_BIT`)
- **Herramienta**: Pipeline statistics query
- **Confirmación**: FPS ↓ con primitivas pequeñas, `rasterizer_busy` → 100%
- **Refutación**: FPS estable, `rasterizer_busy` < 50%
- **Riesgos**: Vertex buffer size grande (GTT/VRAM)
- **Root**: No
- **Recompilación**: VS simple, geometry simple
- **Reversible**: Sí
- **Evidencia**: Polaris whitepaper "aggressive primitive culling"

### GEO-03: Index/Vertex Buffer Bandwidth
- **Hipótesis**: Streaming VBO/IBO grandes estresa PCIe/GTT/VRAM bandwidth
- **Variable**: Tamaño VBO/IBO (64MB, 256MB, 512MB, 1GB), update frequency (frame/frame)
- **Constantes**: Draw simple, FS/VS simples
- **Métrica**: FPS, `mem_busy`, GTT/VRAM usage, PCIe throughput (lspci contadores)
- **Herramienta**: `mem_info_gtt_used`, `mem_info_vram_used`, `lspci` contadores
- **Confirmación**: FPS correlaciona con buffer size, `mem_busy` ↑
- **Refutación**: FPS estable, `mem_busy` bajo
- **Riesgos**: OOM si excede VRAM/GTT
- **Root**: No
- **Recompilación**: No (cambio en buffer creation)
- **Reversible**: Sí

### GEO-04: Instancing
- **Hipótesis**: Instancing masivo (100k+ instances) con VS per-instance revela VS throughput vs instancing overhead
- **Variable**: Instance count (100, 1k, 10k, 100k, 1M), VS per-instance work
- **Constantes**: 1 draw call, 1 VBO + instance buffer, FS simple
- **Métrica**: FPS, `vertex_busy`, VS invocations, draw call overhead
- **Herramienta**: `vkCmdDrawIndexed` con `instanceCount`, pipeline stats
- **Confirmación**: FPS escala linealmente con instances hasta límite VS
- **Refutación**: FPS plano (overhead domina)
- **Riesgos**: Instance buffer size
- **Evidencia**: GPUOpen "Compute shaders can enable fixed wave grouping via Workgroups"

### GEO-05: Many Small Primitives (Overdraw Geométrico)
- **Hipótesis**: Overdraw geométrico real (vs fragment-only) estresa ROP + early-Z + HTILE
- **Variable**: Capas geométricas (1, 4, 16, 64), primitivas solapadas, depth complexity
- **Constantes**: VS/FS simples, depth attachment, early-Z habilitado
- **Métrica**: FPS, `rop_busy`, `depth_busy`, overdraw factor (pipeline stats FS invocations / pixels)
- **Herramienta**: Pipeline stats (`FRAGMENT_SHADER_INVOCATIONS_BIT` / pixels)
- **Confirmación**: Overdraw factor ↑ → FPS ↓, `rop_busy`/`depth_busy` ↑
- **Refutación**: FPS estable, `rop_busy` bajo
- **Evidencia**: GPUOpen "Fill-rate, overdraw and MSAA stress render back-end"

### GEO-06: Large Triangles (Viewport Culling)
- **Hipótesis**: Triángulos gigantes (full-screen +) prueban viewport culling / scissor / viewport transform
- **Variable**: Tamaño triángulo (1.5x, 2x, 4x, 10x viewport), viewport/scissor config
- **Constantes**: VS/FS simples
- **Métrica**: FPS, `rasterizer_busy`, primitive throughput
- **Herramienta**: radeontop
- **Confirmación**: Triángulos > viewport → culling eficiente, FPS estable
- **Refutación**: FPS degrada (no culling)

### GEO-07: Geometric Overdraw (Depth + Layers)
- **Hipótesis**: Overdraw con depth test real (vs blending aditivo) prueba early-Z / HTILE efficiency
- **Variable**: Capas con depth test (1, 4, 16), depth func (LESS, ALWAYS), early-Z forced
- **Constantes**: VS/FS simples, depth attachment, HTILE
- **Métrica**: FPS, `depth_busy`, `rop_busy`, early-Z rate (si medible)
- **Herramienta**: radeontop depth_busy, pipeline stats
- **Confirmación**: Early-Z reduce FS invocations → FPS > blending aditivo
- **Refutación**: Mismo FPS que blending (early-Z inefectivo)

### GEO-08: Vertex + Fragment Simultáneo
- **Hipótesis**: Carga balanceada VS+FS revela bottleneck compartido (scheduler, cache, bandwidth)
- **Variable**: VS complexity × FS complexity (matrix 3×3: low/med/high × low/med/high)
- **Constantes**: 1920x1080, MSAA 1x, 1 layer
- **Métrica**: FPS, `vertex_busy`, `shader_busy`, `mem_busy`, frametime
- **Herramienta**: radeontop, pipeline stats
- **Confirmación**: FPS limitado por min(VS throughput, FS throughput, bandwidth)
- **Refutación**: FPS determinado solo por una etapa

---

## Categoría 2: MEMORIA / VRAM / GTT

### MEM-01: VRAM Pressure / Spilling
- **Hipótesis**: Presión VRAM real (working set > VRAM) fuerza eviction a GTT → degrada performance
- **Variable**: Working set VRAM (50%, 75%, 100%, 125%, 150% de VRAM física 2GB)
- **Constantes**: Workload compute/gráfico fijo
- **Métrica**: FPS, `mem_info_vram_used`, `mem_info_gtt_used`, page faults (dmesg), FPS
- **Herramienta**: `mem_info_vram_used`, `mem_info_gtt_used`, dmesg `evict`/`migrate`
- **Confirmación**: FPS cliff al exceder VRAM, GTT usage ↑, page faults
- **Refutación**: FPS estable hasta OOM
- **Riesgos**: OOM, device lost
- **Root**: No (pero OOM puede requerir reboot)
- **Reversible**: Sí (reducir working set)

### MEM-02: GTT vs VRAM Allocation Strategy
- **Hipótesis**: Allocation strategy (VRAM vs GTT vs HOST_VISIBLE) afecta bandwidth/latency
- **Variable**: `VkMemoryPropertyFlags`: `DEVICE_LOCAL` vs `HOST_VISIBLE|HOST_COHERENT` vs `HOST_CACHED`
- **Constantes**: Mismo workload, misma cantidad memoria
- **Métrica**: FPS, upload/download latency (timestamp queries), `mem_busy`
- **Herramienta**: Timestamp queries (`vkCmdWriteTimestamp`), radeontop
- **Confirmación**: `DEVICE_LOCAL` > `HOST_VISIBLE` > `HOST_CACHED` para GPU access
- **Refutación**: Sin diferencia medible

### MEM-03: Sparse Residency (PRT)
- **Hipótesis**: Partially Resident Textures permite working set > VRAM sin penalty si acceso es local
- **Variable**: Textura sparse 4GB (solo 256MB residente), patrón acceso (local vs random)
- **Constantes**: FS sampling, misma resolución
- **Métrica**: FPS, `mem_info_vram_used`, page faults, residency
- **Herramienta**: `VK_EXT_sparse_resource`, `mem_info_vram_used`
- **Confirmación**: Acceso local → FPS estable con low residency; random → page faults ↑
- **Refutación**: FPS cliff inmediato
- **Riesgos**: Complejidad implementación, driver bugs
- **Evidencia**: Polaris whitepaper "PRTs up to 32TB virtual memory"

### MEM-04: Copy Engine (SDMA) vs Graphics Queue Upload
- **Hipótesis**: SDMA queue para uploads async libera graphics queue → mejor overlap
- **Variable**: Upload path: graphics queue vs SDMA queue (compute queue con copy)
- **Constantes**: Mismo tamaño upload (256MB, 1GB), mismo timing
- **Métrica**: Upload latency (timestamp), graphics queue occupancy, FPS
- **Herramienta**: Timestamp queries, `vkQueueSubmit` en queues separadas
- **Confirmación**: SDMA upload no bloquea graphics queue → FPS estable durante upload
- **Refutación**: Mismo stall en graphics queue

---

## Categoría 3: FRAGMENT / RASTER / MSAA

### FRAG-01: Sample Shading Real (MSAA + Per-Sample)
- **Hipótesis**: Sample shading real (MSAA 8x + `sampleShadingEnable` + `minSampleShading=1.0`) multiplica fragment work ×8 con valores distintos → rompe auto-pacing
- **Variable**: `sampleShadingEnable` + `minSampleShading=1.0` vs MSAA 8x sin sample shading
- **Constantes**: 1920x1080, 4 layers, FS con `gl_SampleID`/`gl_SamplePosition` en hash
- **Métrica**: FPS, frametime, `shader_busy`, `mem_busy`, power, FS invocations (pipeline stats)
- **Herramienta**: `VkPipelineMultisampleStateCreateInfo.sampleShadingEnable=true`, `minSampleShading=1.0`, pipeline stats
- **Confirmación**: FS invocations ×8, frametime ~8×, power ↑, mem_busy ↑
- **Refutación**: FPS/frame-time invariante (dedup persiste)
- **Evidencia**: RADV habilita `sampleRateShading` desde 2016; `ps_iter_samples = samples × minSampleShading`
- **Riesgos**: Frametime muy alto (timeout fence), OOM (CB 8x MSAA)

### FRAG-02: MSAA + DCC Interaction
- **Hipótesis**: DCC deshabilitado para MSAA 4x/8x → CB writes uncompressed → mem_busy ↑
- **Variable**: MSAA 1x (DCC on) vs 4x/8x (DCC off) con mismo FS entropy
- **Constantes**: FS high entropy, 1920x1080, 4 layers
- **Métrica**: `mem_busy`, power, CB bandwidth (si medible), frametime
- **Herramienta**: `radv_disable_dcc=1` (control), radeontop mem_busy
- **Confirmación**: MSAA 8x sin DCC → mem_busy ↑ vs MSAA 1x con DCC
- **Refutación**: mem_busy igual

### FRAG-03: Blend Mode / ROP Pressure
- **Hipótesis**: Blend modes complejos (SRC_ALPHA, ONE_MINUS_SRC_ALPHA, MIN, MAX) estresan ROP blend unit
- **Variable**: Blend mode: ONE/ONE (aditivo), SRC_ALPHA/ONE_MINUS_SRC_ALPHA, MIN, MAX, pantalla
- **Constantes**: 4 layers, 1920x1080, FS high entropy
- **Métrica**: FPS, `rop_busy`, frametime
- **Confirmación**: Blend complejo → `rop_busy` ↑, FPS ↓
- **Refutación**: `rop_busy` invariante

### FRAG-04: Attachment Format / Compression
- **Hipótesis**: Formato attachment afecta DCC efficiency y bandwidth
- **Variable**: Format: R8G8B8A8_UNORM (DCC), R16G16B16A16_SFLOAT (no DCC), R32G32B32A32_SFLOAT
- **Constantes**: FS entropy alta, 1920x1080, MSAA 1x
- **Métrica**: `mem_busy`, power, frametime
- **Confirmación**: Formatos sin DCC → mem_busy ↑, power ↑
- **Refutación**: Sin diferencia

---

## Categoría 3: SHADER / COMPILER

### SHD-01: ILP vs Occupancy (Wave32 vs Wave64)
- **Hipótesis**: Wave32 duplica occupancy teórica → mejor latency hiding en shaders memory-bound
- **Variable**: `RADV_FORCE_WAVE64=0` (wave32) vs default (wave64)
- **Constantes**: Mismo shader (fetch-bound), 1920x1080, 4 layers
- **Métrica**: FPS, occupancy (radeontop), frametime, VALU busy
- **Herramienta**: `RADV_FORCE_WAVE64=0`, radeontop occupancy
- **Confirmación**: Wave32 → occupancy ↑, frametime ↓ (mejor latency hiding)
- **Refutación**: Frametime igual o peor
- **Evidencia**: GPUOpen "Wave32 vs Wave64... Wave32 lower latency... 2x Wave32 on RDNA"

### SHD-02: Loop Unroll / ILP Optimization
- **Hipótesis**: Unroll factor óptimo maximiza ILP sin spilling → mejor latency hiding
- **Variable**: `pragma unroll` factor (1, 2, 4, 8, 16, 32, 64, 128)
- **Constantes**: Shader fetch-bound, 1920x1080, 4 layers
- **Métrica**: FPS, VGPRs (compiler stats), occupancy, frametime
- **Herramienta**: Shader compiler stats (`-Rpass-analysis=kernel-resource-usage`), radeontop
- **Confirmación**: Unroll óptimo → VGPRs ↑ moderado, occupancy mantenida, frametime ↓
- **Refutación**: Unroll alto → VGPRs ↑↑, occupancy ↓↓, frametime ↑
- **Evidencia**: ORNL "Loop unrolling influences register pressure... SW4CK unroll hot loop → 50% speedup"

### SHD-03: 16-bit Ops / Packed Math
- **Hipótesis**: Packed 16-bit math (SDWA, `V_CVT_PKRTZ_F16_F32`) duplica throughput para datos 16-bit
- **Variable**: Shader con datos f32 vs f16 packed (donde precisión permite)
- **Constantes**: Mismo algoritmo, misma resolución
- **Métrica**: FPS, VALU throughput (si medible), VGPR usage
- **Confirmación**: f16 packed → 2x VALU throughput para ops compatibles
- **Refutación**: Sin mejora (overhead packing > ganancia)

### SHD-04: DPP / Cross-Lane Ops
- **Hipótesis**: DPP (Data Parallel Primitives) permite cross-lane sin LDS → reduce latency vs LDS permute
- **Variable**: Shader con `ds_permute` vs `v_perm_b32` / DPP para reducciones/broadcast
- **Constantes**: Mismo algoritmo reducción, 1920x1080
- **Métrica**: FPS, latency (timestamp), LDS usage
- **Confirmación**: DPP → latency ↓, LDS usage ↓
- **Refutación**: Sin diferencia medible

---

## Categoría 4: ASYNC COMPUTE / OVERLAP

### ASY-01: Graphics + Compute Overlap
- **Hipótesis**: Compute shader en ACE queue overlap con graphics queue → utiliza SIMDs ociosos durante stalls
- **Variable**: Compute workload intensity (0%, 25%, 50%, 75%, 100% SIMDs) en compute queue paralela
- **Constantes**: Graphics workload fijo (E-03 base), compute shader memory-bound
- **Métrica**: FPS graphics, compute throughput, `shader_busy` total, `mem_busy`
- **Herramienta**: Separate queues (`VK_QUEUE_GRAPHICS_BIT` + `VK_QUEUE_COMPUTE_BIT`), timeline semaphores
- **Confirmación**: Graphics FPS estable, compute throughput > 0 → overlap real
- **Refutación**: Graphics FPS ↓ proporcional a compute load (contención)

### ASY-02: Copy Engine Overlap
- **Hipótesis**: SDMA copy engine overlap con graphics → uploads no bloquean graphics
- **Variable**: Upload size (100MB, 500MB, 1GB) en SDMA vs graphics queue
- **Constantes**: Graphics workload continuo, upload periódico
- **Métrica**: Graphics frametime stability, upload latency
- **Confirmación**: SDMA upload → graphics frametime estable; graphics queue upload → frametime spikes

---

## Categoría 5: POWER / DPM / THERMAL

### PWR-01: Power Profile Modes
- **Hipótesis**: `pp_power_profile_mode` afecta SCLK/MCLK curves y power draw
- **Variable**: Profile: `3D_FULL_SCREEN`, `POWER_SAVING`, `VIDEO`, `COMPUTE`, `CUSTOM`
- **Constantes**: Workload fijo (E-03 base), medir steady state
- **Métrica**: `power_avg_steady`, `power_max`, SCLK/MCLK distribución, FPS
- **Herramienta**: `pp_power_profile_mode` write (requiere root), telemetría
- **Confirmación**: Profile COMPUTE → SCLK ↑, MCLK ↑, power ↑, FPS ↑
- **Refutación**: Sin diferencia entre perfiles
- **Riesgos**: Requiere root, write sysfs (snapshot + restore obligatorio)

### PWR-02: MCLK Forcing (si autorizado)
- **Hipótesis**: Forzar MCLK 1500 MHz sostenido elimina MCLK downclock → mem_busy ↑ → power ↑
- **Variable**: `power_dpm_force_performance_level=high` + `pp_dpm_mclk` force level 2
- **Constantes**: Workload fetch-bound (E-03 base)
- **Métrica**: `mem_busy`, `power_avg_steady`, FPS, frametime
- **Riesgos**: **Requiere autorización explícita + `--danger`**, thermal risk
- **Estado**: **CONGELADO** — solo si autorizado explícitamente

### PWR-03: Thermal Throttling Characterization
- **Hipótesis**: Temperatura > threshold → throttling SCLK/MCLK → performance cliff
- **Variable**: Workload intensity + artificial heating (furmark) hasta 90°C
- **Constantes**: Monitoreo continuo temp, SCLK, MCLK, FPS
- **Métrica**: Temp threshold, SCLK/MCLK drop point, FPS cliff
- **Riesgos**: **Thermal risk** — 90 °C marca confound; 96 °C es el abort configurado
- **Estado**: **CONGELADO** — heating artificial y cualquier pause requieren autorización

---

## Resumen de Candidatos por Prioridad (Regla 10)

| Prioridad | Candidatos | Justificación |
|---|---|---|
| **ALTA** | FRAG-01 (Sample Shading), GEO-01/02, MEM-01, SHD-01 | Directamente atacan cuellos identificados (fetch-bound, vertex/raster, VRAM pressure, wave size) |
| **MEDIA** | GEO-02/03/05, FRAG-02, SHD-02, ASY-01 | Atacan cuellos secundarios, medibles, reversibles |
| **BAJA** | GEO-03/04/06/07/08, FRAG-03/04, SHD-02/03/04, ASY-02 | Valor informativo menor, mayor complejidad |
| **CONGELADO** | PWR-02, PWR-03 | Requieren autorización explícita + riesgo térmico |

---

## Variables de Control Comunes (Para TODOS los Experimentos)

| Variable | Valor Fijo | Por Qué |
|---|---|---|
| Resolution | 1920x1080 | Baseline consistente |
| Layers | 4 | Overdraw baseline |
| Textures | 4 × 4096² | Working set fijo |
| Seeds | 0x13579BDF / 0x2468ACEO | Determinismo |
| Warmup | 5s | Estabilización térmica/DPM |
| Duration | 20s | Ventana medida |
| MSAA | 1x (salvo experimento MSAA) | Baseline |
| Seeds | Fijas | Reproducibilidad |
| Mesa | SYSTEM MESA | Congelado |
| Kalm | Activo (no tocar) | Estado actual |
| power1_cap | 35,000,000 µW | Baseline |
| DPM | auto | Baseline |

---

## Plantilla de Registro de Experimento (Para Ejecución Futura)

```
EXPERIMENT ID: GEO-01-r1
BASELINE: E-03 base (commit hash)
VARIABLE CHANGED: VS complexity (ALU ops 0→500)
UNCHANGED: Resolution, layers, textures, FS, MSAA, seeds, warmup, duration
HARDWARE STATE: cap=35W, DPM=auto, temp_start=XX°C
SOFTWARE STATE: Mesa SYSTEM, RADV+ACO, Kalm activo
DRIVER/ICD: RADV system, VK_ICD_FILENAMES=system
KALM STATE: Activo (PID XXXX)
POWER CAP: 35,000,000 µW
WORKLOAD PARAMS: VS_ALU_OPS=500
DURATION: 20s
WARMUP: 5s
TELEMETRY: 10 Hz, 34s (pre+run+post)
METRICS: power_avg_full, power_avg_steady, power_max, FPS, frametime, vertex_busy, shader_busy, mem_busy, SCLK/MCLK dist
RAW ARTIFACTS: runs/GEO-01-r1/{stdout,telemetry.csv,pre_flight,post_flight,journal}
RESULT: [PENDING]
VALIDITY: [PENDING]
LIMITATIONS: [PENDING]
REPRODUCIBILITY: [PENDING]
```
