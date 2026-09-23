# SOFTWARE-CAPABILITIES.md — Capacidades Expuestas por Capa de Software

**Fecha:** 2026-09-21  
**Versión:** 1.0  
**Alcance:** Qué capacidades de hardware Polaris12/GFX8 son expuestas/utilizables desde cada capa de la pila de software

---

## Matriz de Capacidades por Capa

| Capacidad Hardware | Linux/amdgpu (Kernel) | Mesa radeonsi (OpenGL) | RADV (Vulkan) | ACO (RADV Compiler) | Herramientas Userspace |
|---|---|---|---|---|---|
| **Shader/ALU** | Scheduler HWS, wave launch | NIR→LLVM→ISA | NIR→ACO→ISA | ACO IR→ISA (DPP, SDWA, 16-bit) | radeontop, perf, RGP |
| **SIMD** | HWS dispatch, wave slots | Implícito | Implícito | Scheduling, wave32/64 | radeontop (agregado) |
| **VGPR/SGPR** | Register state save/restore | LLVM regalloc | ACO regalloc | ACO regalloc (greedy) | compiler stats, RGP |
| **Occupancy** | HWS resource management | Implícito | Implícito | Scheduler (ILP vs occ) | radeontop (est.), RGP |
| **LDS** | SPI allocation | NIR→LLVM | NIR→ACO | Allocation, bank conflict | compiler stats |
| **Texture Units** | TEX config | `tex_*` ops | `image_sample` | `image_*` ops | radeontop tex_busy |
| **Texture Cache** | V$ config | Implícito | Implícito | Cache hints | radeontop (parcial) |
| **L2 Cache** | L2 config, slices | Implícito | `radv_flush_caches` | — | radeontop (parcial) |
| **Rasterizer** | Config init | `glDraw*` | `VkPipelineRasterizationState` | — | radeontop |
| **Vertex** | Shader cores | VS, TES, GS | VS, TES, GS | — | radeontop |
| **Geometry** | Primitive assembly | TES/GS | TES/GS | — | radeontop |
| **ROP/Render Backend** | Config | `glBlend*`, `glDepth*` | `VkPipelineColorBlendState`, `VkPipelineDepthStencilState` | — | radeontop rop_busy |
| **DCC** | Register config | `glEnable(GL_FRAMEBUFFER_SRGB)` | `radv_image_can_enable_dcc`, `radv_disable_dcc` | — | dmesg, driconf |
| **Depth/HTILE** | Register config | `glEnable(GL_DEPTH_TEST)` | `radv_htile_enable` | — | radeontop depth_busy |
| **MSAA/FMASK** | Sample config | `glEnable(GL_MULTISAMPLE)` | `VkPipelineMultisampleStateCreateInfo`, `sampleShadingEnable` | — | vulkaninfo sample_counts |
| **Framebuffer** | Memory controller | `glDrawBuffers` | `VkRenderPass`, `VkFramebuffer` | — | radeontop |
| **Memory Controller** | `pp_dpm_mclk`, DPM policy | N/A | N/A | N/A | `pp_dpm_mclk`, radeontop |
| **GDDR5/VRAM** | `mem_info_*` sysfs | Buffer allocation | `VkMemoryPropertyFlags` | N/A | `mem_info_*`, radeontop |
| **GTT** | GART management | Buffer allocation | `VK_MEMORY_PROPERTY_HOST_VISIBLE_BIT` | N/A | `mem_info_gtt_used` |
| **PCIe** | `amdgpu_pcie.c`, ASPM | N/A | N/A | N/A | `lspci -vvv` |
| **SDMA** | `amdgpu_sdma.c` | `glCopyBuffer` | `VkCmdCopyBuffer/Image` | N/A | dmesg |
| **ACE/Async Compute** | HWS, CU reservation | Limitado | `VK_QUEUE_COMPUTE_BIT`, `VkQueueSubmit` | — | vulkaninfo queues |
| **PowerPlay/DPM** | `pp_dpm_sclk/mclk`, `power1_input`, `power_dpm_force_performance_level` | N/A | N/A | N/A | sysfs, radeontop |
| **Clock Gating** | Hardware-only | N/A | N/A | N/A | N/A |
| **Voltage/Freq** | `ppfeaturemask`, SPPT | N/A | N/A | N/A | `ppfeaturemask`, dmesg |
| **Sparse Resources** | VM management | `GL_ARB_sparse_texture` | `VK_EXT_sparse_resource` | — | vulkaninfo |
| **Descriptors** | Root table, USER-DATA SGPR | `glBind*` | Descriptor Sets, Push Constants | — | shader stats |
| **RADV Workarounds** | N/A | N/A | driconf, env vars | — | `/usr/share/drirc.d/00-radv-defaults.conf` |
| **Shader Compiler** | N/A | LLVM | ACO (default) / LLVM | ACO IR→ISA | `RADV_DEBUG=aco,llvm` |
| **Cache Behavior** | Flush/inv registers | `glFlush` | `radv_flush_caches` | — | `RADV_DEBUG=flush` |
| **Sync/Barriers** | Fence, semaphore | `glFenceSync` | `VkFence`, `VkSemaphore`, `VkEvent`, `VkCmdPipelineBarrier` | — | `VK_QUEUE_*` |
| **Pipeline Stats** | N/A | `GL_ARB_pipeline_statistics_query` | `VkQueryPool` pipeline statistics | N/A | `VkQueryPool` |
| **HW Perf Counters** | PMU, `amdgpu` PMU | N/A | `RADV_DEBUG=perfcounters` | N/A | UMR, radeontop, perf |

---

## Diferenciación OpenGL vs Vulkan (Capacidades Críticas)

| Aspecto | OpenGL (radeonsi) | Vulkan (RADV) | Impacto |
|---|---|---|---|
| **Pipeline State** | Estado global implícito | `VkPipeline` explícito (cacheable) | Vulkan: menos driver overhead |
| **Memory Management** | `glBufferData` implícito | `VkBuffer` + `VkDeviceMemory` explícito | Vulkan: control total |
| **Synchronization** | `glFenceSync` (coarse) | `VkFence`, `VkSemaphore`, `VkEvent`, `VkCmdPipelineBarrier` (fine) | Vulkan: control granular |
| **Descriptor Management** | `glBind*` (bind point) | Descriptor Sets + Push Constants (explícito) | Vulkan: menos bind overhead |
| **Async Compute** | Muy limitado | `VK_QUEUE_COMPUTE_BIT` + ACE queues | Vulkan: overlap real |
| **Sparse Resources** | `GL_ARB_sparse_texture` | `VK_EXT_sparse_resource` (más completo) | Vulkan: más control |
| **DCC Control** | Implícito | `radv_disable_dcc`, `radv_disable_dcc_stores` | Vulkan: control explícito |
| **Sample Shading** | `glEnable(GL_SAMPLE_SHADING)` | `sampleShadingEnable` + `minSampleShading` | Igual hardware |
| **Push Constants** | N/A (uniform buffers) | 256 bytes max (GFX8) | Vulkan: low-latency constants |
| **Pipeline Cache** | Shader cache implícito | `VkPipelineCache` explícito | Vulkan: reproducible builds |

---

## Capacidades SOLO en Vulkan/RADV (No en OpenGL/radeonsi)

| Capacidad | Descripción | Uso en Nuestro Workload |
|---|---|---|
| **Descriptor Sets** | Agrupación explícita de recursos | `fragment.frag` usa `set=0, binding=0` array `sampler2D tex[4]` |
| **Push Constants** | 256 bytes, low-latency | `PCFrag` struct (28 bytes) |
| **Render Passes** | Explícitas, subpasses | `VkRenderPass` + `VkFramebuffer` offscreen |
| **Pipeline Layout** | Explícita | `VkPipelineLayout` + `VkPipeline` |
| **Async Compute Queues** | `VK_QUEUE_COMPUTE_BIT` | No usado en workload actual |
| **Pipeline Statistics Queries** | `VK_QUERY_TYPE_PIPELINE_STATISTICS` | No usado |
| **Pipeline Cache** | `VkPipelineCache` | No usado |
| **Sparse Resources** | `VK_EXT_sparse_resource` | No usado |
| **Sample Shading** | `sampleShadingEnable` + `minSampleShading` | No usado (MSAA sin sample shading) |

---

## Capacidades SOLO en OpenGL/radeonsi (No en Vulkan/RADV)

| Capacidad | Descripción |
|---|---|
| **Legacy Bind Points** | `glBindBuffer`, `glBindTexture`, `glBindVertexArray` |
| **Implicit State** | Estado global de pipeline |
| **Immediate Mode** | `glBegin`/`glEnd` (deprecated pero presente) |
| **Display List / Display Lists** | `glNewList`/`glEndList` (legacy) |

---

## Variables de Entorno RADV Relevantes

| Variable | Efecto | Usada en Nuestro Workload |
|---|---|---|
| `RADV_DEBUG=aco,llvm,perfcounters,flush` | Debug compiler/counters | No |
| `RADV_PERFTEST=aco,llvm,cs` | Force compiler | No |
| `RADV_DEBUG=nodcc` | Deshabilita DCC | **Sí** (probado en R-11) |
| `RADV_DEBUG=nodcc_mips,nodcc_stores` | DCC granular | No |
| `RADV_PERFTEST=sample_rate_shading` | Force sample shading | No |
| `RADV_FORCE_WAVE64=0/1` | Force wave size | No |
| `RADV_DEBUG=startup,info` | Startup info | No |
| `MESA_VK_DEVICE_SELECT=1002:699f` | Device selection | **Sí** (obligatorio) |
| `VK_ICD_FILENAMES=/usr/share/vulkan/icd.d/radeon_icd.x86_64.json` | ICD selection | **Sí** (obligatorio) |

---

## Capacidades NO Expuestas / NO Accesibles

| Capacidad | Por Qué No Accesible | Alternativa |
|---|---|---|
| **Clock Gating Control** | Hardware-only | — |
| **Voltage Control** | VBIOS/SPPT, requiere flash | — |
| **Per-CU Power Gating** | Hardware/firmware | — |
| **L2 Partition Control** | Hardware/firmware | — |
| **Per-SIMD Clock Control** | Hardware-only | — |
| **Direct Register Access** | Kernel-only | UMR (read-only) |
| **Per-SIMD Wave Control** | HWS opaco | — |
| **Voltage/Frequency Curves** | VBIOS/SPPT (flash) | — |
| **Per-ROP Control** | Hardware-only | — |
| **Memory Controller Registers** | Firmware | — |
| **GDS (Global Data Share) Explicit** | Solo compute shaders | Compute shader |
| **Hardware Performance Counters** | Requiere UMR/perf/PMU | UMR (read-only) |

---

## Capacidades Requeridas por Nuestro Workload Actual

| Capacidad | Usada | API | Verificada |
|---|---|---|---|
| **Vulkan 1.1** | Sí | Vulkan | ✅ |
| **Descriptor Sets (array sampler2D)** | `tex[4]` | Vulkan | ✅ |
| **Push Constants** | `PCFrag` (28 bytes) | Vulkan | ✅ |
| **Offscreen Rendering** | `VkRenderPass` + `VkFramebuffer` | Vulkan | ✅ |
| **Offline Texture Upload** | `vkCmdCopyBufferToImage` | Vulkan | ✅ |
| **MSAA 1x/4x/8x** | `--msaa` | Vulkan | ✅ |
| **Device Selection** | `MESA_VK_DEVICE_SELECT` | Vulkan | ✅ |
| **Pipeline Statistics** | No | — | — |
| **Async Compute** | No | — | — |
| **Sample Shading** | No | — | — |
| **Sparse Resources** | No | — | — |

---

## Capacidades Faltantes para Experimentos Futuros

| Experimento Futuro | Capacidad Requerida | Disponible | Cómo Habilitar |
|---|---|---|---|
| **GEO-01 (Vertex Throughput)** | Vertex shader heavy, many draw calls | ✅ Vulkan | `VkPipeline` + many `vkCmdDraw` |
| **GEO-02 (Primitive Throughput)** | Many small primitives | ✅ Vulkan | `VK_PRIMITIVE_TOPOLOGY_TRIANGLE_LIST` |
| **GEO-03 (Index/Vertex Bandwidth)** | Large VBO/IBO streaming | ✅ Vulkan | `VkBuffer` + `VK_BUFFER_USAGE_TRANSFER_DST_BIT` |
| **GEO-04 (Instancing)** | `instanceCount` en `vkCmdDraw` | ✅ Vulkan | `vkCmdDrawIndexed` con `instanceCount` |
| **GEO-05 (Many Small Primitives)** | Overdraw geométrico | ✅ Vulkan | Many small triangles |
| **GEO-06 (Large Triangles)** | Few large primitives | ✅ Vulkan | Single large triangle |
| **GEO-07 (Geometric Overdraw)** | Depth + multiple layers | ✅ Vulkan | Depth attachment + layers |
| **GEO-08 (Vertex+Fragment)** | Simultaneous heavy VS+FS | ✅ Vulkan | Both shaders heavy |
| **Sample Shading** | `sampleShadingEnable` + `minSampleShading=1.0` | ✅ Vulkan | `VkPipelineMultisampleStateCreateInfo` |
| **Async Compute** | `VK_QUEUE_COMPUTE_BIT` + ACE | ✅ Vulkan | Separate compute queue |
| **Sparse Resources** | `VK_EXT_sparse_resource` | ✅ Vulkan | `VK_BUFFER_CREATE_SPARSE_BINDING_BIT` |
| **Pipeline Statistics** | `VkQueryPool` | ✅ Vulkan | `VK_QUERY_TYPE_PIPELINE_STATISTICS` |
| **HW Perf Counters** | UMR/perf | **VERIFICAR** | Instalar UMR, configurar perf |

---

## Resumen: Qué Podemos Controlar vs Solo Observar

| Controlable (Userspace) | Solo Observable (Read-Only) | Hardware-Only (No Accesible) |
|---|---|---|
| Pipeline state (Vulkan) | GPU busy % (radeontop) | Clock gating |
| Descriptor sets / push constants | VRAM/GTT usage (sysfs/radeontop) | Clock gating per-block |
| Render pass / framebuffer | Power draw (power1_input) | Voltage curves |
| MSAA / Sample shading | Temperature (temp1_input) | Voltage/Freq curves (VBIOS) |
| Async compute queues | SCLK/MCLK DPM states (sysfs) | L2 partitioning |
| Sample shading | GPU busy % (radeontop) | Per-SIMD clock |
| Sparse resources | MCLK/SCLK (pp_dpm_*) | Per-ROP control |
| Pipeline cache | mem_busy % (radeontop) | L2 slice assignment |
| Shader selection (ACO vs LLVM) | PCIe link (lspci) | Memory controller registers |
| DCC enable/disable (env) | VRAM/GTT usage (sysfs/radeontop) | Per-CU power gating |
| Sample shading enable | DPM states (pp_dpm_*) | Memory controller timing |
| Pipeline statistics queries | Pipeline stats (VkQueryPool) | Hardware perf counters (UMR/perf) |

---

## Resumen para Nuestro Workload Sintético

**Lo que usamos (y funciona):**
- Vulkan 1.1 + RADV + ACO
- Descriptor sets + Push constants (28 bytes)
- Offscreen rendering (VkRenderPass + VkFramebuffer)
- MSAA 1x/4x/8x (validado contra `sample_counts_cb`)
- Texture upload via `vkCmdCopyBufferToImage` (host → GPU)
- Device selection (`MESA_VK_DEVICE_SELECT` + `VK_ICD_FILENAMES`)

**Lo que NO usamos (pero podríamos):**
- Sample shading (requiere `sampleShadingEnable` + `minSampleShading=1.0`)
- Async compute (ACE queues)
- Pipeline statistics (overdraw measurement)
- Sparse resources
- Pipeline cache

**Lo que NO podemos hacer (limitaciones):**
- Controlar clock gating / voltage
- Acceder contadores HW directamente (requiere UMR/perf)
- Modificar curvas voltage/freq (requiere VBIOS flash)
- Controlar L2 partitioning / per-CU power