# HARDWARE-ROUTES.md — Rutas de Hardware por Subsistema (Cadena Completa)

**Fecha:** 2026-09-21  
**Versión:** 1.0  
**Formato:** Para cada subsistema: Hardware Polaris12 → Documentación/ISA/Registros → Linux/amdgpu → Mesa/radeonsi/RADV → Herramienta de observación → Métrica observable → Experimento potencial → Limitación conocida

---

## A. Shader/ALU (VALU + SALU)

### Hardware Polaris12
- **VALU**: 4 SIMD/CU × 16 lanes = 64 lanes/CU × 8 CUs = 512 lanes totales
  - Instrucciones VALU: VOP1, VOP2, VOP3, VOPC, VINTRP
  - FP32 FMA: 1/ciclo/lane (64 FMA/ciclo/CU teórico)
  - FP64: 1/16 rate (GCN4 config)
  - 16-bit: single-rate (packed) en GCN4+
  - DPP (Data Parallel Primitives): cross-lane ops sin LDS
  - SDWA: Sub-DWord Addressing (8/16-bit pack/unpack)
- **SALU**: 1 por CU (32-bit scalar ALU)
  - Control flow, address generation, pointer arithmetic
  - Scalar memory (SMEM) para loads de constantes/descriptors
  - Latencia: ~4 ciclos

### Documentación/ISA/Registros
- **ISA**: GCN3/GFX8 (GCN4/Polaris) — `R1200_ISA.book`, GCN3 ISA Reference
- **Registros clave**: `compute_pgm_rsrc1_vgprs`, `compute_pgm_rsrc1_sgprs`, `compute_pgm_rsrc2`
- **VGPRs**: 256 por wave (granularidad 4), hasta 256 AGPRs (MFMA, no en GFX8)
- **SGPRs**: 102 por wave (granularidad 8/16), VCC en SGPRs altos

### Linux/amdgpu
- Kernel: `drivers/gpu/drm/amd/amdgpu/gfx_v8_0.c` (GFX8/Polaris)
- Firmware: `polaris10_ce.bin`, `polaris10_pfp.bin`, `polaris10_me.bin`, `polaris10_mec.bin`
- Scheduler: HWS (Hardware Scheduler) — virtualiza colas compute/graphics

### Mesa/radeonsi/RADV
- **radeonsi** (OpenGL): LLVM backend + NIR → ISA
- **RADV** (Vulkan): LLVM backend + **ACO** (por defecto en GFX8+) → ISA
- ACO optimiza: ILP, DPP, SDWA, register allocation, scheduling
- Shader info: `radv_pipeline_get_shader_info()`, `radv_shader_info`

### Herramientas de Observación
| Herramienta | Qué Mide | Acceso |
|---|---|---|
| **radeontop** | VALU busy %, SALU busy %, shader busy | userspace |
| **umr --read-counter** | Contadores VALU/SALU (si expuestos) | userspace (needs drm master) |
| **perf + amdgpu PMU** | `amdgpu/*` events (cycles, instructions) | root (perf_event_paranoid) |
| **Shader compiler stats** | SGPR/VGPR/LDS/scratch/occupancy | compile-time (`-Rpass-analysis=kernel-resource-usage`) |
| **RGP (Radeon GPU Profiler)** | ISA, occupancy, bottlenecks | Requiere Windows/Linux + driver |

### Métricas Observables
- `VALU_busy_percent` (radeontop): % ciclos VALU activo
- `SALU_busy_percent` (radeontop): % ciclos SALU activo
- `shader_busy_percent`: combinado
- `SGPRs_used`, `VGPRs_used`, `occupancy_waves_per_SIMD` (compile-time)

### Experimentos Potenciales
1. **ILP vs Occupancy**: Variar VGPRs (unroll factor) → medir occupancy vs IPC
2. **DPP/SDWA impact**: Shader con/sin cross-lane ops → medir VALU busy
3. **Wave32 vs Wave64**: Forzar wave size en RADV (`RADV_FORCE_WAVE64=1/0`) → medir occupancy

### Limitaciones Conocidas
- **GFX8 no tiene MFMA/AGPRs** (solo GFX9+)
- **No AGPRs** → no matrix math acceleration
- **FP64 1/16 rate** en Polaris12
- **Occupancy limitada por VGPRs** (granularidad 4) y LDS

---

## B. SIMD

### Hardware Polaris12
- **4 SIMD por CU** × 8 CUs = 32 SIMDs totales
- Cada SIMD: 16 lanes, 10 wavefront slots (hasta 40 waves/CU)
- Wavefront = 64 threads (tarda 4 ciclos en emitir instrucción completa)
- Instruction buffer: 10 entries por SIMD (40 waves/CU máx)
- Issue: 1 instrucción/ciclo/SIMD desde wave distinta (round-robin)
- Multi-issue: hasta 5 instr/ciclo/SIMD de waves distintas (VALU, VMEM, SALU, SMEM, LDS, Branch, Export)

### Documentación/ISA
- **Whitepaper GCN**: "The CU front-end can decode and issue five instructions every cycle, to a mix of six vector and scalar execution pipelines"
- **GCN whitepaper**: "Each SIMD unit is assigned its own 40-bit program counter and instruction buffer for 10 wavefronts"

### Linux/amdgpu
- Scheduler HWS: despacha waves a SIMDs disponibles
- `gfx_v8_0.c`: configuración SIMD/CU en `gfx_v8_0_init()`

### Mesa/RADV
- RADV decide wave size (32 vs 64) heurísticamente
- Compute: `wave_size = 64` por defecto; `RADV_FORCE_WAVE64=0` fuerza 32
- Graphics: pixel shaders → wave64; vertex/compute → wave32

### Herramientas
| Herramienta | Métrica |
|---|---|
| **radeontop** | SIMD busy % (agregado) |
| **umr** | Estado SIMD, wave slots ocupados |
| **RGP** | Wave occupancy por SIMD, stall cycles |

### Limitaciones
- **No observabilidad directa por SIMD** en radeontop (solo agregado)
- **HWS opaco**: despacho interno no expuesto a userspace
- **Wave occupancy real** solo visible via UMR/RGP

---

## C. VGPR/SGPR

### Hardware Polaris12 (GFX8)
| Registro | Por Wave | Granularidad | Total por CU |
|---|---|---|---|
| **VGPRs** | 256 máx | 4 (grupos de 4) | 256 KB (64 KB/SIMD × 4) |
| **SGPRs** | 102 máx | 8/16 | 12.8 KB (compartidos por CU) |
| **VGPR granularity** | 4 registers | — | — |
| **SGPR granularity** | 8 (GFX8) / 16 (GFX9+) | — | — |

### Documentación/ISA
- **ISA GCN3**: `compute_pgm_rsrc1_vgprs = (workitem_vgpr_count-1)/4`
- **ISA GCN3**: `compute_pgm_rsrc1_sgprs = (wavefront_sgpr_count-1)/8` (GFX8)
- **VGPR allocation**: grupos de 4; SGPRs: grupos de 8 (GFX8)
- **VCC**: 2 SGPRs altos reservados; FLAT_SCRATCH, XNACK también en SGPRs altos
- **Spilling**: VGPRs → scratch memory (global memory, lento); SGPRs → VGPRs si presión

### Linux/amdgpu
- Kernel: `amdgpu_vm.c`, `amdgpu_ring.c` — gestión de registers state
- `amdgpu_ib.c`: command buffer validation de register usage

### Mesa/RADV
- **radeonsi**: LLVM register allocator → spilling heuristics
- **RADV/ACO**: Register allocator propio; `-Rpass-analysis=kernel-resource-usage` para stats
- **Compiler flags**: `amdgpu-schedule-metric-bias` (occupancy vs latency), `amdgpu-vgpr-threshold-percent`

### Herramientas
| Herramienta | Métrica | Momento |
|---|---|---|
| **hipcc -Rpass-analysis=kernel-resource-usage** | SGPRs, VGPRs, LDS, scratch, occupancy | Compile-time (ROCm) |
| **glslang + spirv-tools** | Aproximado | Compile-time |
| **RGP** | Register pressure timeline | Runtime (requiere driver) |
| **radeontop** | No expone registers directamente | — |

### Limitaciones
- **Spilling a scratch** = acceso a VRAM global (lento, usa `vm_cnt`)
- **SGPR pressure** → reduce occupancy más agresivamente (SGPRs compartidos por CU)
- **Granularidad VGPR=4** → saltos de ocupación discretos

---

## D. Occupancy

### Hardware Polaris12
| Recurso | Límite por SIMD | Límite por CU (4 SIMD) |
|---|---|---|
| Wavefront slots | 10 | 40 |
| VGPRs (256/wave) | 2560 | 10240 |
| SGPRs (102/wave) | 1020 | 4080 |
| LDS (64 KB/CU) | — | 64 KB |
| Barriers | 16 por par SIMD | 32 |

### Tabla Ocupación vs VGPRs (GCN4/Polaris)
| VGPRs/wave | Waves/SIMD | Waves/CU | % Ocupación teórica |
|---|---|---|---|
| ≤ 64 | 10 | 40 | 100% |
| ≤ 72 | 8 | 32 | 80% |
| ≤ 80 | 8 | 32 | 80% |
| ≤ 96 | 6 | 24 | 60% |
| ≤ 128 | 5 | 20 | 50% |
| ≤ 168 | 4 | 16 | 40% |
| ≤ 256 | 3 | 12 | 30% |

### Linux/amdgpu
- HWS gestiona wave launch basado en recursos disponibles
- `gfx_v8_0.c`: `gfx_v8_0_get_cu_info()` reporta recursos

### Mesa/RADV
- **ACO**: Scheduler optimiza para occupancy vs ILP (`amdgpu-schedule-metric-bias=10` default)
- **Wave size**: Wave32 = doble ocupación teórica vs Wave64 (menos VGPRs/wave efectivos)

### Herramientas
| Herramienta | Métrica |
|---|---|
| **radeontop** | `occupancy` % (estimado) |
| **umr --read-counter** | Waves activas por SIMD (si contador expuesto) |
| **RGP** | Occupancy timeline, stall reasons |

### Limitaciones
- **Occupancy real ≠ teórica**: stalls, barriers, resource conflicts reducen occupancy efectiva
- **radeontop occupancy** = estimado, no preciso

---

## E. LDS (Local Data Share)

### Hardware Polaris12
- **64 KB por CU** (32 KB según ISA GCN3, 64 KB según whitepaper Polaris — **Polaris12 = 64 KB**)
- **32 banks**, 512 entries/bank × 4 bytes = 64 KB
- **128 bytes/ciclo/CU** bandwidth (32 banks × 4 bytes × 1 clk)
- **32 atomic units** (int + float max/min/cmpxchg)
- **LDS allocation**: per work-group (compute) o per-wavefront (graphics)
- **Allocation granularity**: 64 Dwords (256 bytes), 64-Dword alignment

### Documentación/ISA
- **ISA**: `LDS_ALLOC` register, `M0` register para size clamping
- **LDS ops**: `ds_read/write/bpermute/permute/atomic/add/min/max/and/or/xor`
- **Bank conflicts**: accesos a mismo bank en mismo ciclo → ciclos adicionales

### Linux/amdgpu
- `gfx_v8_0.c`: LDS initialization en `gfx_v8_0_init()`
- SPI (Shader Processor Interpolator) gestiona LDS allocation

### Mesa/RADV
- **radeonsi/RADV**: LDS allocation en shader prolog/epilog
- **Compute**: workgroup size determina LDS usage
- **Graphics**: interpolación, parameter cache usan LDS

### Herramientas
| Herramienta | Métrica |
|---|---|
| **Compiler stats** | `LDS Size [bytes/block]`, `LDS blocks` |
| **RGP** | LDS usage timeline, bank conflicts |

### Limitaciones
- **Bank conflicts** no observables directamente en radeontop
- **LDS contention** entre waves en mismo CU

---

## F. Texture Units

### Hardware Polaris12
- **4 Texture Units por CU** (1 por SIMD) × 8 CUs = **16 TEX units totales**
- **Peak throughput**: 1 filtered 2×2 quad/clk/TEX unit (64-wide wave en 16 clks)
- **Filtered 128-bit texels**: 64 clks/wave (bilinear/trilinear/aniso)
- **Point sampled 128-bit**: 16 clks/wave
- **32-bit filtered**: 16 clks/wave
- **64-bit filtered**: 32 clks/wave
- **Address generation**: 4 texel addresses/clk → 16 sample addresses para 2×2 quad

### Documentación/ISA
- **GPUOpen "Understanding Memory Coalescing on GCN"**: Throughput tables
- **MIMG instructions**: `image_sample`, `image_load`, `image_store`
- **Sampler states**: filter, address mode, lod bias, anisotropy

### Linux/amdgpu
- TEX unit management en `gfx_v8_0.c` — parte de shader array

### Mesa/RADV
- **RADV**: `radv_tex_*` — descriptor sets, samplers, image views
- **Sampler pooling**: `radv_sampler_pool` para reutilizar samplers
- **Anisotropy**: max 16x (vulkaninfo reporta 16)

### Herramientas
| Herramienta | Métrica |
|---|---|
| **radeontop** | `tex_busy` % (texture unit busy) |
| **umr** | TEX unit counters (si expuestos) |

### Limitaciones
- **Texture cache (V$) = 16 KB/CU** (L1 vector cache) — no L2
- **V$ miss → L2 → DRAM** latencia ~350 ciclos (miss L2)
- **Coalescing**: 4 invocations (2×2 quad) grouped for L2 access

---

## G. Texture Cache (V$)

### Hardware Polaris12
- **V$ (Vector L1 Data Cache)**: 16 KB por CU, 4-way, 64B lines, LRU
- **Write-through, write-allocate** con dirty byte mask
- **Coherencia**: work-group coherent, eventual global consistency via L2
- **Servicio**: VMEM ops (load/store/image) → V$ → L2 → DRAM
- **Punto de coherencia**: L2 (distribuido, particionado por canal memoria)

### Documentación
- **GCN Whitepaper**: "The L1 data cache is 16KB and 4-way set associative with 64B lines... write-through, write-allocate"
- **GPUOpen**: "V$ miss → L2 → DRAM"

### Linux/amdgpu
- Cache management en `gfx_v8_0.c` — flush/invalidate via `S_DCACHE_INV`, `S_WBINVL1`

### Mesa/RADV
- **RADV**: `radv_flush_caches()` — `RADV_CMD_FLAG_FLUSH_VS` / `RADV_CMD_FLAG_INV_VCACHE`
- **Image layouts**: `VK_IMAGE_LAYOUT_SHADER_READ_ONLY_OPTIMAL` → cacheable

### Herramientas
| Herramienta | Métrica |
|---|---|
| **radeontop** | No expone V$ hit/miss directamente |
| **perf + amdgpu PMU** | Posibles eventos cache (verificar) |

### Limitaciones
- **No contadores V$ hit/miss expuestos en radeontop**
- **Coherencia relajada**: L1 work-group coherent, L2 globally coherent

---

## H. L2 Cache

### Hardware Polaris12 (Polaris12 = 512 KB)
- **512 KB total** (Polaris12) vs 1 MB (Polaris10/11) — confirmado igor'sLAB
- **16-way associative**, 64B lines, LRU
- **Write-back, write-allocate**
- **Particionado**: slices acoplados a controladores de memoria (2 canales × 256 KB = 512 KB)
- **Crossbar fabric**: CUs → L2 slices → memory controllers
- **Coherencia**: write-back, write-allocate; absorbe write misses de L1D
- **Clients en Polaris**: Solo CUs (shaders). Copy Engine, CP, Render Backend **bypasan L2** (escriben directo a memoria) — ver GPUOpen RDNA presentation

### Documentación
- **GCN Whitepaper**: "The distributed L2 cache in GCN is the central point of coherency"
- **GPUOpen RDNA**: "On the Polaris architecture only the CUs are clients of L2. Copy Engine, CP and Render Backend directly write to memory."

### Linux/amdgpu
- `gfx_v8_0.c`: L2 initialization, slices config
- `amdgpu_gmc.c`: memory controller config

### Mesa/RADV
- **RADV**: `radv_flush_caches()` — `RADV_CMD_FLAG_FLUSH_L2` para L2
- **DCC interaction**: DCC compressed blocks en L2

### Herramientas
| Herramienta | Métrica |
|---|---|
| **radeontop** | `l2_busy` % (si expuesto) |
| **perf** | Posibles eventos L2 (verificar) |

### Limitaciones
- **En Polaris, Render Backend bypassa L2** → CB writes no pasan por L2
- **No contadores L2 hit/miss expuestos en radeontop**

---

## I. Rasterizer

### Hardware Polaris12
- **2 Rasterizers** (Polaris10/11/12: 2)
- **Throughput**: 1 primitive/clk/rasterizer, 16 pixels/clk/rasterizer
- **Wavefront launch**: 1 wave (64 pixels) cada 4 clks/rasterizer
- **Total**: 2 rasterizers → 1 wave/2 clks → llena shader array
- **Primitive assembly**: triángulos, líneas, puntos, patches

### Documentación
- **GCN Whitepaper**: "Tahiti has two rasterizers... each rasterizer can consume one primitive per clock and create a 64-wide wavefront every four cycles"
- **Polaris Whitepaper**: "Polaris enhances the command processing, geometry engines"

### Linux/amdgpu
- `gfx_v8_0.c`: rasterizer config en `gfx_v8_0_init()`

### Mesa/RADV
- **RADV**: `radv_rasterization_state` — `VkPipelineRasterizationStateCreateInfo`

### Herramientas
| Herramienta | Métrica |
|---|---|
| **radeontop** | `rasterizer_busy` % |

### Limitaciones
- **Primitive rate** no expuesto directamente

---

## J. Vertex Processing

### Hardware Polaris12
- **Vertex Shader (VS)**: se ejecuta en VALU (mismo hardware shader)
- **Throughput**: 1 VGPR wave launch por CU antes de mover a otra
- **V$ locality**: GCN prefiere agrupar vertex waves temporalmente en CU
- **Instancing**: soportado en hardware

### Documentación
- **GPUOpen Advanced Shader Programming**: "Vertex Shader waves are launched one per CU before moving to another CU"

### Mesa/RADV
- **RADV**: `radv_vs_*` — vertex input, attribute binding, instancing

### Herramientas
| Herramienta | Métrica |
|---|---|
| **radeontop** | `vertex_busy` % |

---

## K. Geometry

### Hardware Polaris12
- **Geometry Engine**: 2 (Polaris12)
- **Primitive throughput**: 1 prim/clk/engine
- **Tessellation**: soportado (HS, DS, TS) — mismo hardware shader
- **Primitive assembly**: culling, clipping, viewport transform
- **Aggressive Primitive Culling**: feature Polaris (whitepaper)

### Documentación
- **Polaris Whitepaper**: "aggressive primitive culling... helps improve performance"

### Mesa/RADV
- **RADV**: `radv_tess_*` — tessellation shaders

---

## L. Primitive Assembly

### Hardware Polaris12
- **Post-tessellation**: assembly de primitivas finales
- **Culling**: back-face, frustum, small primitive
- **Viewport transform**: clip → NDC → viewport

### Documentación
- **GCN Whitepaper**: Primitive assembly rates

---

## M. ROP / Render Backends

### Hardware Polaris12
- **16 ROPs** (Render Output Units / Render Backends)
- **Pixel fillrate**: 64 Gpix/s (teórico @ 1 GHz)
- **Color writes**: bypass L2 en GFX8 (escriben directo a memory controller)
- **Depth/Stencil**: compresión HTILE, early-Z, late-Z
- **Blend**: blend unit por ROP
- **DCC**: Delta Color Compression en color attachments

### Documentación
- **GCN Whitepaper**: "final pixel colors are written to the memory controllers and bypass the L2 cache"
- **Chip and Cheese**: "RBs... final pixel colors are written to the memory controllers and bypass the L2 cache" (Tahiti/GCN1, mismo diseño en Polaris/GCN4)
- **Mesa-dev 2019**: "GFX6-8: used by shaders only. GFX9-10: used by everything" (L2 para shaders; CB/DB flush propio)

### Linux/amdgpu
- Render backend config en `gfx_v8_0.c`

### Mesa/RADV
- **RADV**: `radv_render_pass_state` — color/depth attachments, DCC
- **DCC control**: `radv_image_can_enable_dcc()` — deshabilita DCC si: MSAA ≥ 4x, STORAGE/TRANSFER usage, LINEAR tiling, scanout

### Herramientas
| Herramienta | Métrica |
|---|---|
| **radeontop** | `rop_busy` %, `depth_busy` % |

### Limitaciones
- **CB/DB bypass L2 en GFX8** → tráfico CB no visible en L2 counters
- **DCC solo color attachments** (no depth/stencil en GFX8)

---

## N. DCC (Delta Color Compression)

### Hardware Polaris12
- **Lossless color compression** para render targets
- **Bloques dinámicos** según patrones de acceso/datos
- **Pico 8:1** (bloque 256B → 32B)
- **Polaris más agresivo** que gen anterior (whitepaper)
- **Shader cores leen y descomprimen transparentemente** (render-to-texture)

### Documentación
- **Polaris Whitepaper**: "DCC is lossless, divides the buffer into dynamically sized blocks... peak 8:1 (256 B); Polaris is more aggressive than gen 3"
- **GPUOpen DCC Overview**: Properties, usage flags que deshabilitan/degradan

### Linux/amdgpu
- DCC management en `gfx_v8_0.c` — register config

### Mesa/RADV
- **RADV**: Habilita DCC por defecto en color attachments (GFX8+)
- **Deshabilita DCC si**: `usage` incluye `TRANSFER_SRC/DST` o `STORAGE`, `MUTABLE_FORMAT`, `LINEAR` tiling, `scanout` (swapchain)
- **Env vars**: `radv_disable_dcc=1`, `radv_disable_dcc_mips`, `radv_disable_dcc_stores`
- **Commit RADV DCC**: `ff8b0f6` (Add DCC support)

### Herramientas
| Herramienta | Métrica |
|---|---|
| **radeontop** | No expone DCC hit/miss |
| **dmesg** | DCC enable/disable messages (con debug) |

### Limitaciones
- **MSAA 4x/8x**: RADV NO habilita DCC por defecto (`dcc_msaa_allowed` = false)
- **STORAGE usage** → deshabilita DCC
- **Scanout/swapchain** → deshabilita DCC

---

## O. Depth / HTILE

### Hardware Polaris12
- **HTILE (Hierarchical TILE)**: compresión jerárquica depth/stencil
- **Early-Z / Late-Z**: early depth test antes de fragment shader
- **Depth compression**: lossless, similar a DCC pero para depth
- **Stencil**: 8-bit stencil buffer

### Documentación
- **GCN Whitepaper**: Depth/Stencil compression

### Mesa/RADV
- **RADV**: `radv_htile_enable()` — habilita HTILE para depth/stencil attachments
- **Layouts**: `VK_IMAGE_LAYOUT_DEPTH_STENCIL_ATTACHMENT_OPTIMAL`

---

## P. MSAA / FMASK

### Hardware Polaris12
- **Sample counts**: 1x, 2x, 4x, 8x (color)
- **FMASK**: Fragment Mask — compresión MSAA (similar a DCC pero para samples)
- **MSAA storage**: attachment N× más grande en memoria
- **SHS (Shader per Sample)**: 1 para MSAA básico; >1 para sample shading

### Documentación
- **RasterGrid MSAA Primer**: "SHS=1, CCS=N" — fragment shader 1×/pixel, CB almacena N muestras
- **Vulkan MSAA Sample**: "attachment N× bigger; stored/read multiplies bandwidth by N"
- **RADV mesa-dev 2018**: "RADV NO habilita DCC para MSAA 4x/8x por defecto"

### Mesa/RADV
- **RADV**: `radv_image_can_enable_dcc()` — `samples >= 2` requiere `dcc_msaa_allowed`
- **Sample Shading**: `VkPipelineMultisampleStateCreateInfo.sampleShadingEnable` + `minSampleShading`
- **Feature**: `sampleRateShading` (RADV habilita desde 2016)

### Herramientas
| Herramienta | Métrica |
|---|---|
| **vulkaninfo** | `sample_counts_cb` (bitmask: 1,2,4,8) |

### Limitaciones
- **DCC deshabilitado para MSAA 4x/8x** → CB writes uncompressed
- **Sample shading** multiplica fragment shader invocations × samples

---

## Q. Framebuffer Writes

### Hardware Polaris12
- **Color Buffer (CB)**: attachment de color (R8G8B8A8, etc.)
- **Depth/Stencil Buffer**: attachment depth/stencil
- **Blending**: blend unit por ROP (ONE/ONE aditivo, etc.)
- **CB writes**: bypass L2 en GFX8 → directo a memory controller
- **DCC**: comprime CB en escritura (si habilitado)

### Documentación
- **GCN Whitepaper**: "final pixel colors are written to the memory controllers and bypass the L2 cache"
- **Mesa-dev 2019**: "GFX6-8: used by shaders only. GFX9-10: used by everything" (CB/DB flush separado)

### Mesa/RADV
- **RADV**: `radv_fb_*` — framebuffer state, clearing, resolving

---

## R. Memory Controller

### Hardware Polaris12
- **2 Memory Controllers** (128-bit bus = 2 canales × 64-bit)
- **Cada canal**: 1 L2 slice (256 KB) + 1 memory controller
- **MCLK DPM**: niveles 300 MHz (piso) / 1500 MHz (máx)
- **DPM Policy (smu7)**: `mclk_activity = 20` (bus 128-bit), `up_hyst = 5`, `down_hyst = 16` (parche amd-gfx 2020)
- **MCLK up threshold**: actividad memoria sostenida ≥ ~20%

### Documentación
- **amd-gfx list 2020-09**: "para VRAM 128-bit (RX 460/550): `mclk_activity = 20`, `up_hyst = 5`, `down_hyst = 16`"

### Linux/amdgpu
- `smu7_hwmgr.c`: `pp_dpm_mclk` levels, activity thresholds
- `pp_dpm_mclk` sysfs: niveles y estado activo (`*`)

### Herramientas
| Herramienta | Métrica |
|---|---|
| **radeontop** | `mem_busy_percent`, `mclk` actual |
| **pp_dpm_mclk** | Niveles DPM, estado activo (`*`) |
| **power1_input** | Power draw (SMU estimate) |

---

## S. GDDR5

### Hardware Polaris12
- **128-bit bus** (2 canales × 64-bit)
- **7 Gbps** (data rate) → **112 GB/s** teórico peak bandwidth
- **2 GB** VRAM (Polaris12 Lexa PRO)
- **Data rate**: DDR = 2 transfers/clk → 7 Gbps = 1750 MHz clock efectivo

### Documentación
- **TechPowerUp / igor'sLAB**: 128-bit, 7 Gbps, 112 GB/s

### Herramientas
| Herramienta | Métrica |
|---|---|
| **lspci -vvv** | Link width, speed |
| **radeontop** | `mem_busy_percent` |

---

## T. VRAM

### Hardware Polaris12
- **2 GB GDDR5** (Polaris12 Lexa PRO)
- **DEVICE_LOCAL** (visible to GPU, no CPU)
- **Heap size reportado por RADV**: 1,879,048,192 bytes (~1.75 GiB de 2 GiB físicos)
- **GTT**: System memory aperture (visible CPU+GPU)

### Linux/amdgpu
- `amdgpu_gmc.c`: VRAM/GTT management
- `mem_info_vram_used`, `mem_info_gtt_used`, `mem_info_vram_total` en `/sys/class/drm/card1/device/`

### Mesa/RADV
- **RADV**: `radv_alloc_memory()` — `VK_MEMORY_PROPERTY_DEVICE_LOCAL_BIT`
- **Budget**: `vkGetPhysicalDeviceMemoryProperties2` → `VkPhysicalDeviceMemoryBudgetPropertiesEXT`

### Herramientas
| Herramienta | Métrica |
|---|---|
| **radeontop** | VRAM used, GTT used |
| **sysfs** | `mem_info_vram_used`, `mem_info_gtt_used`, `mem_info_vram_total` |

---

## U. GTT

### Hardware Polaris12
- **Graphics Translation Table**: aperture en memoria de sistema
- **Mapeo**: GPU virtual address → system physical address
- **Usado para**: buffers no DEVICE_LOCAL, staging, CPU-visible buffers
- **GTT size**: típicamente 1-2 GB (configurable)

### Linux/amdgpu
- `amdgpu_gart.c`: GART management
- `mem_info_gtt_used` en sysfs

### Mesa/RADV
- **RADV**: `VK_MEMORY_PROPERTY_HOST_VISIBLE_BIT` → GTT

---

## V. PCIe

### Hardware Polaris12
- **PCIe 3.0 x8** (negociado; capaz x16 pero cableado x8 en RX 550)
- **Throughput**: ~8 GB/s bidireccional (x8 Gen3)
- **ASPM**: Active State Power Management (L0s/L1)

### Linux/amdgpu
- `amdgpu_pcie.c`: PCIe config, ASPM
- `lspci -vvv`: `LnkCap`, `LnkSta`

### Herramientas
| Herramienta | Métrica |
|---|---|
| **lspci -vvv** | `LnkCap: Port #0, Speed 8GT/s, Width x8`, `LnkSta: Speed 8GT/s, Width x8` |

---

## W. SDMA (Copy Engines)

### Hardware Polaris12
- **2 SDMA engines** (DMA copy commands)
- **Colas dedicadas** para copy operations
- **Bypass shader array** para copy/clear/fill operations
- **Polaris**: Copy Engine bypassa L2 (escribe directo a memoria)

### Documentación
- **GPUOpen RDNA**: "On the Polaris architecture only the CUs are clients of L2. Copy Engine... directly write to memory"

### Linux/amdgpu
- `amdgpu_sdma.c`: SDMA ring initialization

### Mesa/RADV
- **RADV**: `radv_cmd_buffer_copy_buffer`, `radv_cmd_buffer_copy_image` → SDMA queue

---

## X. ACE / Async Compute

### Hardware Polaris12
- **2 ACEs** (Asynchronous Compute Engines)
- **8 queues por ACE** (16 queues totales)
- **Dispatch**: 1 wavefront/clk/ACE → 2 wavefronts/clk total
- **HWS (Hardware Scheduler)**: virtualiza colas (3rd/4th gen GCN)
- **CU Reservation**: `VkPipelineShaderStageCreateInfoWaveLimitAMD` (extensión AMD)

### Documentación
- **Polaris Whitepaper**: "Each ACE block... can dispatch up to four wavefronts/workgroups to the shader engines from any compute queue at any time"

### Linux/amdgpu
- `amdgpu_hws.c`: HWS scheduler
- `amdgpu_ctx.c`: context management

### Mesa/RADV
- **RADV**: `radv_queue_submit()` — compute queue usa ACE
- **Vulkan**: `VK_QUEUE_COMPUTE_BIT` → ACE queue

---

## Y. DMA / Copy Engines

### Hardware Polaris12
- **2 DMA engines** dedicados para copy commands
- **SDMA engines** (ver W)

---

## Z. PowerPlay / DPM

### Hardware Polaris12
- **PowerPlay**: SMU (System Management Unit) firmware
- **DPM (Dynamic Power Management)**: estados de reloj/voltaje
- **SCLK DPM**: 8 niveles (0: 214 MHz ... 7: 1071 MHz)
- **MCLK DPM**: 3 niveles (0: 300 MHz, 1: 625 MHz, 2: 1500 MHz)
- **power1_cap**: límite de potencia (µW) — configurable via sysfs
- **power1_input/average**: estimador SMU (µW)
- **power_dpm_force_performance_level**: `auto` | `low` | `high` | `manual` | `profile_standard` | `profile_min_sclk` | `profile_min_mclk` | `profile_peak`

### Documentación
- **Kernel docs**: `amdgpu/thermal.html` — power1_average/input, DPM, pp_dpm_sclk/mclk
- **amd-gfx list 2020-09**: MCLK DPM policy para 128-bit

### Linux/amdgpu
- `amdgpu_pm.c`: `amdgpu_pm_set_power_limit()`, `amdgpu_dpm_set_power_profile()`
- `smu7_hwmgr.c`: SCLK/MCLK DPM para Polaris (smu7)

### Sysfs Nodos (read-only en operación normal)
```
/sys/class/drm/card1/device/
├── power1_cap                 # Límite potencia (µW)
├── power1_input               # Potencia instantánea (µW)
├── power1_average             # Potencia promedio (µW)
├── power1_cap_max             # Límite máximo (35W en esta RX 550)
├── power_dpm_force_performance_level
├── pp_dpm_sclk                # Niveles SCLK + * activo
├── pp_dpm_mclk                # Niveles MCLK + * activo
├── pp_power_profile_mode      # Perfiles disponibles + activo
├── temp1_input                # Temperatura (m°C)
├── gpu_busy_percent           # GPU busy %
├── mem_busy_percent           # Memory busy %
├── freq1_input                # SCLK actual (Hz)
└── ppfeaturemask              # Feature mask (0xfff7bfff)
```

### Herramientas
| Herramienta | Métrica |
|---|---|
| **radeontop** | power, temp, sclk, mclk, busy%, mem_busy% |
| **sysfs read** | Valores exactos de nodos arriba |

---

## AA. Clock Gating

### Hardware Polaris12
- **Fine-grained clock gating** (whitepaper Polaris: "even more fine grained clock gating than previous GCN")
- **Nivel**: per-block, per-clock
- **Efecto**: unidades ociosas no consumen dynamic power
- **No expuesto a software** — hardware-only

### Documentación
- **Polaris Whitepaper**: "Polaris has even more fine grained clock gating than previous GCN to save power and improve performance"

### Limitaciones
- **No controlable por software** — decisión hardware basada en utilization
- **Explica auto-pacing**: unidades ociosas = 0 dynamic power

---

## AB. Voltage / Frequency Behavior

### Hardware Polaris12
- **Voltage/Frequency curves**: definidas en VBIOS/SPPT (Smart Power Play Table)
- **ppfeaturemask**: bitmask de features habilitadas (actual: `0xfff7bfff`)
- **DPM states**: voltage + frequency por nivel
- **Thermal throttling**: si temp > threshold → reduce clocks/voltage

### Documentación
- **Kernel**: `ppsmc.h` — `PP_FEATURE_MASK_*` defines
- **ppfeaturemask bits**: decodificar desde kernel source

### Herramientas
| Herramienta | Qué Muestra |
|---|---|
| **ppfeaturemask** (sysfs) | Bitmask actual (`0xfff7bfff`) |
| **dmesg** | DPM transitions, voltage changes |

### Limitaciones
- **No modificar ppfeaturemask** sin conocimiento exacto de bits
- **VBIOS/SPPT** define curves — no modificable en runtime sin flash

---

## AC. Sparse Residency (PRT / PRT2)

### Hardware Polaris12
- **PRT (Partially Resident Textures)**: Vulkan `VK_EXT_sparse_resource`
- **Tile size**: 64 KB (page size)
- **Max sparse resources**: limitados por VA space
- **PRT2** (GCN4+): sparse buffers, sparse images 3D, mip tail packing

### Documentación
- **Vulkan Spec**: `VK_EXT_sparse_resource`, `VK_EXT_sparse_resource2`
- **Whitepaper Polaris**: "Partially Resident Textures (PRTs)... up to 32TB virtual memory"

### Mesa/RADV
- **RADV**: `radv_sparse_*` — sparse binding, residency management
- **Features**: `sparseBinding`, `sparseResidencyImage2D`, `sparseResidencyBuffer`

---

## AD. Descriptors / Resource Paths

### Hardware Polaris12
- **Descriptor Sets**: 128-bit descriptors (image + sampler combinados en RADV)
- **Root Table**: 64-bit pointers → convertidos a 128-bit descriptors en runtime
- **USER-DATA SGPRs**: 16 SGPRs preload antes de wave launch (driver/fixed function + descriptors)
- **Push Constants**: 256 bytes máx (Vulkan limit GFX8)
- **Dynamic Descriptors**: offsets en USER-DATA SGPRs

### Documentación
- **GPUOpen Advanced Shader Programming**: "Root-table CBVs are 64-bit pointers converted to 128-bit descriptors at run-time... 16 SGPRs can be pre-loaded before shader start"

### Mesa/RADV
- **RADV**: `radv_descriptor_set_*` — layout, binding, pooling
- **Descriptor Pool**: `radv_descriptor_pool_alloc()`
- **Push Constants**: `VkPushConstantRange` (max 256 bytes GFX8)

---

## AE. RADV Workarounds (driconf)

### Workarounds Conocidos (GFX8/Polaris)
| Workaround | Bug | Juegos | Estado en driconf |
|---|---|---|---|
| `radv_disable_shrink_image_store` | The Surge 2, World War Z | imageStore shrink | Habilitado por defecto en algunos |
| `radv_wait_for_vm_map_updates` | Forza Horizon | VM map timing | Habilitado por defecto |
| `radv_disable_dcc` | DCC bugs | Varios | `radv_disable_dcc=1` env |
| `radv_disable_dcc_mips` | DCC mipmaps | — | — |
| `radv_disable_dcc_stores` | DCC stores | — | — |

### Fuente
- `/usr/share/drirc.d/00-radv-defaults.conf` en sistema
- **R-11**: Nuestro workload probó ambos — `shrink_image_store` reduce 4→2 faults, `wait_for_vm_map_updates` sin efecto concluyente

### Mesa/RADV
- **driconf**: `/usr/share/drirc.d/00-radv-defaults.conf`
- **Env overrides**: `RADV_DEBUG=...`, `RADV_PERFTEST=...`

---

## AF. Shader Compiler (LLVM / ACO)

### Compiladores
| API | Backend | Optimizaciones Clave |
|---|---|---|
| **OpenGL (radeonsi)** | LLVM | NIR → LLVM IR → ISA; standard LLVM opts |
| **Vulkan (RADV)** | **ACO** (default GFX8+) / LLVM | NIR → ACO IR → ISA; DPP, SDWA, register allocator propio, scheduling |

### Optimizaciones Clave (ACO)
- **DPP (Data Parallel Primitives)**: cross-lane ops sin LDS (`v_perm_b32`, `ds_permute`)
- **SDWA**: Sub-DWord Addressing (8/16-bit pack/unpack en VGPRs)
- **16-bit ops**: `AMD_gpu_shader_half_float` (single-rate en GCN3+)
- **Register allocation**: greedy + spill heuristics
- **Scheduling**: ILP vs occupancy (`amdgpu-schedule-metric-bias=10`)
- **Loop unrolling**: heurístico, controlable con `pragma unroll`

### Herramientas
| Herramienta | Uso |
|---|---|
| **glslangValidator -V** | Validar GLSL → SPIR-V |
| **spirv-dis** | Disassemble SPIR-V |
| **RADV_DEBUG=llvm,aco** | Ver IR/ISA generado |
| **RGP** | ISA final, register pressure, occupancy |

### Limitaciones
- **No control directo** de decisiones de compilador desde userspace
- **Debug info** limitado en release builds

---

## AG. Cache Behavior

### Jerarquía Completa (Polaris12/GFX8)
```
L1 I$ (Instruction)     : 32 KB per 4 CUs, 4-way, 64B lines
L1 K$ (Scalar/Constant) : 16 KB per 4 CUs, 4-way, 64B lines
L1 V$ (Vector/Data)     : 16 KB per CU, 4-way, 64B lines, write-through
L2 (Unified)            : 512 KB total, 16-way, 64B lines, write-back
    → 2 slices (1 per memory channel), 256 KB cada una
DRAM                    : GDDR5 128-bit, 7 Gbps, 112 GB/s
```

### Coherencia
- **L1 V$**: work-group coherent, eventual global via L2
- **L2**: globally coherent, write-back, write-allocate
- **CB/DB (GFX8)**: bypass L2 → memory controller directo
- **Flush/Inv**: `S_DCACHE_INV`, `S_WBINVL1` (L1); `S_INV_VCACHE`, `S_FLUSH_L2` (L2)

### Documentación
- **Mesa-dev 2019**: "GFX6-8: L2 used by shaders only. GFX9-10: used by everything"

---

## AH. Synchronization / Barriers

### Vulkan (RADV)
| Primitiva | Uso | Hardware |
|---|---|---|
| **VkFence** | Host-GPU sync | CS/GFX queue completion |
| **VkSemaphore** | GPU-GPU sync | Timeline / binary |
| **VkEvent** | Fine-grained GPU-GPU | `vkCmdSet/ResetEvent`, `vkCmdWaitEvents` |
| **VkCmdPipelineBarrier** | Cache flush/invalidate, layout transitions | `CMD_WAIT`, `S_WAITCNT`, cache flush |
| **VkCmdWaitIdle** | Drain queue | — |
| **Buffer/Image Memory Barriers** | Layout transitions, access masks | `CMD_WAITCNT`, cache ops |

### OpenGL (radeonsi)
- `glFinish`, `glFenceSync`, `glClientWaitSync`
- `glMemoryBarrier` → cache flushes

### Hardware
- **S_WAITCNT**: espera contadores (`vm_cnt`, `lgkm_cnt`, `exp_cnt`)
- **Barriers**: 16 por par SIMD, 32/CU

---

## AI. Pipeline Statistics (Vulkan)

### Queries Disponibles (VkQueryPool)
| Estadística | Descripción |
|---|---|
| `VK_QUERY_PIPELINE_STATISTIC_INPUT_ASSEMBLY_VERTICES_BIT` | Vértices procesados por IA |
| `VK_QUERY_PIPELINE_STATISTIC_INPUT_ASSEMBLY_PRIMITIVES_BIT` | Primitivas ensambladas |
| `VK_QUERY_PIPELINE_STATISTIC_VERTEX_SHADER_INVOCATIONS_BIT` | VS invocations |
| `VK_QUERY_PIPELINE_STATISTIC_GEOMETRY_SHADER_INVOCATIONS_BIT` | GS invocations |
| `VK_QUERY_PIPELINE_STATISTIC_GEOMETRY_SHADER_PRIMITIVES_BIT` | GS output primitives |
| `VK_QUERY_PIPELINE_STATISTIC_CLIPPING_INVOCATIONS_BIT` | Primitivas en clipping |
| `VK_QUERY_PIPELINE_STATISTIC_CLIPPING_PRIMITIVES_BIT` | Primitivas out clipping |
| `VK_QUERY_PIPELINE_STATISTIC_FRAGMENT_SHADER_INVOCATIONS_BIT` | **FS invocations** (clave para overdraw) |
| `VK_QUERY_PIPELINE_STATISTIC_TESSELLATION_CONTROL_SHADER_PATCHES_BIT` | TC patches |
| `VK_QUERY_PIPELINE_STATISTIC_TESSELLATION_EVALUATION_SHADER_INVOCATIONS_BIT` | TE invocations |
| `VK_QUERY_PIPELINE_STATISTIC_COMPUTE_SHADER_INVOCATIONS_BIT` | CS invocations |

### Mesa/RADV
- **RADV**: `radv_CmdBegin/EndQuery()` — `VK_QUERY_TYPE_PIPELINE_STATISTICS`

---

## AJ. Hardware Performance Counters

### Hardware Polaris12
- **Performance Monitoring Unit (PMU)** en hardware
- **Contadores programables** por CU/SIMD/TEX/ROP/L2/MC
- **Eventos**: cycles, instructions, cache hits/misses, busy cycles, stall cycles, bandwidth

### Acceso
| Método | Herramienta | Estado |
|---|---|---|
| **UMR** (Unified Memory Reporter) | `umr --list-counters`, `umr --read-counter` | **INSTALABLE** (needs drm master) |
| **GPUPerfAPI (GPA)** | `GPA_GetCounterNames`, `GPA_OpenContext` | **VERIFICAR** compatibilidad GFX8 |
| **radeontop** | `--list-counters`, `--dump-ctrs` | **VERIFICAR** |
| **perf + amdgpu PMU** | `perf list | grep amdgpu` | **VERIFICAR** kernel config |
| **amdgpu PMU** | `perf stat -e amdgpu/.../` | **VERIFICAR** kernel config |
| **Mesa debug** | `RADV_DEBUG=perfcounters` | **VERIFICAR** implementación |

### Métricas Objetivo (si disponibles)
- `SQ_WAVES` / `SQ_ACTIVE_WAVES` — waves activas
- `VALU_INSTS` / `VALU_UTILIZATION` — ALU utilization
- `TEX_INSTS` / `TEX_CACHE_HIT/MISS` — texture cache
- `L2_CACHE_HIT/MISS` — L2 cache
- `MC_READ/WRITE_BYTES` — memory controller bandwidth
- `SQ_WAVE_CYCLES` — wave cycles
- `SQ_STALL_CYCLES` — stall cycles (VMEM, EXP, LGKM)

### Limitaciones
- **GFX8/Polaris soporte en herramientas modernas**: verificar compatibilidad real
- **UMR**: requiere `drm master` (no root, pero X/Wayland no usa drm master)
- **perf_event_paranoid**: puede requerir `sysctl -w kernel.perf_event_paranoid=-1`

---

## Referencias de Navegación
- `POLARIS12-MAP.md` → Índice principal
- `SOFTWARE-CAPABILITIES.md` → Capacidades por capa de software
- `EXPERIMENT-CANDIDATES.md` → Experimentos derivados
- `UNVERIFIED-CLAIMS.md` → Claims sin evidencia