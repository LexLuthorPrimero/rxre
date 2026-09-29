# POLARIS12-MAP.md — Mapa Principal de Capacidades Polaris12/GFX8

**Fecha:** 2026-09-21
**Versión:** 1.1
**Alcance:** Índice navegable de todos los subsistemas A–AJ con enlaces a documentación detallada
**Metodología:** Cada entrada sigue la cadena: Hardware Polaris12 → Documentación/ISA/Registros → Linux/amdgpu → Mesa/radeonsi/RADV → Herramienta de observación → Métrica observable → Experimento potencial → Limitación conocida

> **RECONCILIACIÓN 2026-09-24:** separar capacidad nominal, negociación local y
> capacidad runtime. PCIe Gen2×4 y 2 GiB VRAM son observaciones R-4A; 96–112 GB/s es
> estimación nominal/derivada y el bandwidth real es `UNKNOWN`. El número de ACEs de
> Polaris12 y la reserva de CUs por Vulkan son `UNKNOWN`. Una cola compute lógica no
> demuestra overlap.

> **ADDENDA FOCALIZADA 2026-09-24:** la reconciliación de ASIC, counters, telemetría y
> valor informacional está en
> [`COUNTERS-ASIC-TELEMETRY-KNOWLEDGE-ADDENDUM-2026-09-24.md`](../COUNTERS-ASIC-TELEMETRY-KNOWLEDGE-ADDENDUM-2026-09-24.md).
> La addenda no reemplaza las tablas históricas; interpreta sus filas según las capas
> `source/catalog → API exposure → runtime capability → physical counter validation`.
> En particular, un catálogo GFX8 no prueba un selector válido para `1002:699f`, y
> `gpu_busy_percent`/`mem_busy_percent`/`pcie_bw` no son PMU programables.

### Lectura vigente de la cadena GPU → counters → telemetry → workload → bottleneck

| Capa | Estado vigente | Regla de no sustitución |
|---|---|---|
| Identidad local | `CONFIRMED`: `1002:699f`, Polaris12/GFX8 | No fuerza equivalencia comercial Baffin |
| Catálogo GFX8 | `SUPPORTED` como catálogo | No prueba ASIC, selector ni runtime |
| API | RADV GFX8: `NOT_AVAILABLE` para `VK_KHR_performance_query`; radeonsi: `SUPPORTED` sólo source-level | Source/API no equivale a capacidad local |
| Runtime/PMU | PMU mainline GFX8: `NOT_AVAILABLE` como PMU confirmado | No asumir backport ni PMU física |
| Telemetría | `gpu_busy_percent`, `mem_busy_percent`, `pcie_bw`: `SUPPORTED` como proxy/accounting | No convertir proxy en bandwidth, vatímetro o WSI |
| Validación física | `UNKNOWN`; programación prohibida | No usar selectores para causalidad |
| Atribución | `HYPOTHESIS`/`UNKNOWN` hasta separar CPU, GPU, memoria y WSI | No ofrecer tuning como resultado |

---

## Tabla Maestra de Subsistemas (A–AJ)

| ID | Subsistema | Estado Hardware | Estado Linux/amdgpu | Estado Mesa/RADV | Observabilidad | Archivo Detalle |
|---|---|---|---|---|---|---|
| **A** | **Shader/ALU** | VERIFICADO | VERIFICADO | VERIFICADO | radeontop, perf, shader stats | [HARDWARE-ROUTES.md#A] |
| **B** | **SIMD** | VERIFICADO | VERIFICADO | VERIFICADO | radeontop, perf | [HARDWARE-ROUTES.md#B] |
| **C** | **VGPR/SGPR** | VERIFICADO | VERIFICADO | VERIFICADO | shader compiler stats, RGP | [HARDWARE-ROUTES.md#C] |
| **D** | **Occupancy** | VERIFICADO | VERIFICADO | VERIFICADO | radeontop, ROCm profiler | [HARDWARE-ROUTES.md#D] |
| **E** | **LDS** | VERIFICADO | VERIFICADO | VERIFICADO | shader compiler stats | [HARDWARE-ROUTES.md#E] |
| **F** | **Texture Units** | VERIFICADO | VERIFICADO | VERIFICADO | radeontop, perf | [HARDWARE-ROUTES.md#F] |
| **G** | **Texture Cache** | DOCUMENTADO | DOCUMENTADO | DOCUMENTADO | radeontop (parcial) | [HARDWARE-ROUTES.md#G] |
| **H** | **L2 Cache** | VERIFICADO | DOCUMENTADO | DOCUMENTADO | radeontop (parcial), perf | [HARDWARE-ROUTES.md#H] |
| **I** | **Rasterizer** | VERIFICADO | DOCUMENTADO | DOCUMENTADO | radeontop | [HARDWARE-ROUTES.md#I] |
| **J** | **Vertex Processing** | VERIFICADO | DOCUMENTADO | DOCUMENTADO | radeontop | [HARDWARE-ROUTES.md#J] |
| **K** | **Geometry** | VERIFICADO | DOCUMENTADO | DOCUMENTADO | radeontop | [HARDWARE-ROUTES.md#K] |
| **L** | **Primitive Assembly** | DOCUMENTADO | DOCUMENTADO | DOCUMENTADO | radeontop (limitado) | [HARDWARE-ROUTES.md#L] |
| **M** | **ROP/Render Backends** | VERIFICADO | DOCUMENTADO | DOCUMENTADO | radeontop | [HARDWARE-ROUTES.md#M] |
| **N** | **DCC/Color Compression** | VERIFICADO | DOCUMENTADO | DOCUMENTADO | dmesg, driconf | [HARDWARE-ROUTES.md#N] |
| **O** | **Depth/HTILE** | VERIFICADO | DOCUMENTADO | DOCUMENTADO | radeontop | [HARDWARE-ROUTES.md#O] |
| **P** | **MSAA/FMASK** | VERIFICADO | VERIFICADO | VERIFICADO | vulkaninfo, radeontop | [HARDWARE-ROUTES.md#P] |
| **Q** | **Framebuffer Writes** | VERIFICADO | DOCUMENTADO | DOCUMENTADO | radeontop, dmesg | [HARDWARE-ROUTES.md#Q] |
| **R** | **Memory Controller** | VERIFICADO | VERIFICADO | N/A | pp_dpm_mclk, radeontop | [HARDWARE-ROUTES.md#R] |
| **S** | **GDDR5** | VERIFICADO | VERIFICADO | N/A | radeontop, dmesg | [HARDWARE-ROUTES.md#S] |
| **T** | **VRAM** | VERIFICADO | VERIFICADO | DOCUMENTADO | mem_info_vram_used, radeontop | [HARDWARE-ROUTES.md#T] |
| **U** | **GTT** | VERIFICADO | VERIFICADO | DOCUMENTADO | mem_info_gtt_used, radeontop | [HARDWARE-ROUTES.md#U] |
| **V** | **PCIe** | VERIFICADO | VERIFICADO | N/A | lspci, dmesg | [HARDWARE-ROUTES.md#V] |
| **W** | **SDMA** | VERIFICADO | DOCUMENTADO | DOCUMENTADO | dmesg, radeontop | [HARDWARE-ROUTES.md#W] |
| **X** | **ACE/Async Compute** | DOCUMENTADO (familia) | **UNKNOWN** (queues lógicas no prueban ACE/overlap) | PARCIAL | vulkaninfo/fdinfo; capability audit | [HARDWARE-ROUTES.md#X] |
| **Y** | **DMA/Copy Engines** | VERIFICADO | DOCUMENTADO | DOCUMENTADO | dmesg, radeontop | [HARDWARE-ROUTES.md#Y] |
| **Z** | **PowerPlay/DPM** | VERIFICADO | VERIFICADO | N/A | pp_dpm_sclk/mclk, power1_input | [HARDWARE-ROUTES.md#Z] |
| **AA** | **Clock Gating** | VERIFICADO (whitepaper) | INFERIDO | N/A | N/A (hardware) | [HARDWARE-ROUTES.md#AA] |
| **AB** | **Voltage/Frequency** | VERIFICADO (whitepaper) | VERIFICADO (ppfeaturemask) | N/A | ppfeaturemask, dmesg | [HARDWARE-ROUTES.md#AB] |
| **AC** | **Sparse Residency** | DOCUMENTADO (Polaris) | DOCUMENTADO | DOCUMENTADO | vulkaninfo | [HARDWARE-ROUTES.md#AC] |
| **AD** | **Descriptors/Resources** | VERIFICADO | VERIFICADO | VERIFICADO | vulkaninfo, shader stats | [HARDWARE-ROUTES.md#AD] |
| **AE** | **RADV Workarounds** | N/A | N/A | VERIFICADO | driconf, dmesg | [HARDWARE-ROUTES.md#AE] |
| **AF** | **Shader Compiler** | N/A | N/A | VERIFICADO | shader stats, RGP | [HARDWARE-ROUTES.md#AF] |
| **AG** | **Cache Behavior** | DOCUMENTADO | DOCUMENTADO | DOCUMENTADO | radeontop (parcial) | [HARDWARE-ROUTES.md#AG] |
| **AH** | **Sync/Barriers** | VERIFICADO | VERIFICADO | VERIFICADO | vulkaninfo, shader stats | [HARDWARE-ROUTES.md#AH] |
| **AI** | **Pipeline Statistics** | VERIFICADO | VERIFICADO | VERIFICADO | vulkan pipeline stats | [HARDWARE-ROUTES.md#AI] |
| **AJ** | **HW Performance Counters** | SUPPORTED (catálogo GFX8 genérico) | **UNKNOWN** (runtime/ASIC) | SUPPORTED (catálogo; no API/runtime) | capability audit; programación NO AUTORIZADA | [HARDWARE-ROUTES.md#AJ] |

---

## Leyenda de Estados

| Estado | Significado |
|---|---|
| **VERIFICADO** | Confirmado por múltiples fuentes primarias + evidencia en nuestra RX 550 |
| **DOCUMENTADO** | Documentado en whitepaper/ISA/kernel/Mesa pero no verificado directamente en nuestra GPU |
| **INFERIDO** | Deducido lógicamente de especificaciones, sin evidencia directa en nuestro sistema |
| **PARCIAL** | Parcialmente accesible/verificable con herramientas actuales |
| **N/A** | No aplica (subsistema no expuesto a esa capa) |

---

## Capacidad Real vs. Teórica (Nuestra RX 550)

> **Corrección de alcance R-4A (2026-09-23):** no se deben confundir capacidad,
> negociación y verificación. El endpoint declara capacidad máxima PCIe Gen3×8,
> pero en esta plataforma el enlace negociado/verificado es **Gen2×4** por el techo
> del root port. El número de ACE y la reserva de CUs por Vulkan son `UNKNOWN`;
> no se fija `2` como capacidad local.

| Capacidad | Teórica (Polaris12/GFX8) | Real en Nuestra RX 550 | Evidencia |
|---|---|---|---|
| Compute Units | 8 (de 10, 2 deshabilitadas) | 8 | vulkaninfo, lspci, dmesg |
| Stream Processors | 512 (8×64) | 512 | vulkaninfo |
| SIMDs por CU | 4 | 4 | vulkaninfo, whitepaper |
| Wavefronts/SIMD | 10 (hasta 40/CU) | 10 | GPUOpen docs |
| Wavefront size | 64 threads | 64 | vulkaninfo, ISA |
| VGPRs por wave | 256 (granularidad 4) | 256 | ISA, compiler stats |
| SGPRs por wave | 102 (hasta 102, granularidad 8/16) | 102 | ISA, compiler stats |
| LDS por CU | 64 KB (32 banks) | 64 KB | ISA, whitepaper |
| Texture Units/CU | 4 (16 total) | 16 | GPUOpen, whitepaper |
| L1 Vector Cache (V$) | 16 KB/CU | 16 KB | GCN whitepaper |
| L1 Scalar Cache (K$) | 16 KB/4 CUs | 16 KB/4 CUs | GCN whitepaper |
| L2 Cache total | 512 KB (Polaris12) | 512 KB | igor'sLAB, whitepaper |
| ROPs | 16 | 16 | videocardz, whitepaper |
| Memory Bus | 128-bit GDDR5 | 128-bit | lspci, igor'sLAB |
| Memory Clock | 7 Gbps (1750 MHz) | 1500 MHz (DPM nivel 2) | radeontop, pp_dpm_mclk |
| ACEs | **UNKNOWN** (número de familia no reconciliado para Lexa) | **UNKNOWN** (no se fija 2) | family docs; capability audit requerida |
| Geometry Engines | 2 | 2 | whitepaper |
| Rasterizers | 2 | 2 | whitepaper |
| ROPs | 16 | 16 | videocardz |

---

## Diferenciación por API (OpenGL vs Vulkan)

| Subsistema | OpenGL/radeonsi | Vulkan/RADV | Diferencia Clave |
|---|---|---|---|
| Shader Compiler | LLVM-based (radeonsi) | LLVM-based (RADV) + ACO | RADV usa ACO por defecto en GFX8 |
| Descriptor Sets | Legacy (glBind*) | Descriptor Sets + Push Constants | Vulkan más explícito |
| Pipeline State | Monolithic state | Pipeline State Objects | Vulkan más granular |
| Synchronization | Implícita (glFinish) | Explícita (VkFence, VkSemaphore, VkEvent) | Vulkan más control |
| Memory Management | Implícita (buffer objects) | Explícita (VkBuffer, VkImage, VkDeviceMemory) | Vulkan más control |
| MSAA | glEnable(GL_MULTISAMPLE) | VkPipelineMultisampleStateCreateInfo | Igual hardware |
| DCC | radeonsi controla | RADV controla (driconf) | RADV más configurable |
| Async Compute | Limitado (GL) | Queue compute lógico; ACE físico no confirmado | Vulkan expone colas, no prueba ACE/overlap |
| Sparse Resources | ARB_sparse_texture | VK_EXT_sparse_resource | Vulkan más completo |

---

## Herramientas de Observación Disponibles (READ-ONLY)

| Herramienta | Qué Mide | Acceso | Requiere Root | Estado |
|---|---|---|---|---|
| **radeontop** | GPU busy, VRAM, GTT, clocks, Shader/Texture/Compute busy | userspace | No | **DISPONIBLE** como telemetría/proxy; no assume counters HW GFX8 |
| **umr** (Unified Memory Reporter) | Registros HW, database/debug, VRAM, rings | userspace (libdrm) | No (necesita drm master) | **SUPPORTED** como database/debug; selectores no validados |
| **radeontop --dump-ctrs** | Contadores HW (si expuestos) | userspace | No | **UNKNOWN** para GFX8 local |
| **perf + amdgpu PMU** | Contadores PMU (cycles, instructions, cache) | kernel PMU | Sí (perf_event_paranoid) | **NOT_AVAILABLE** como PMU GFX8 mainline confirmado |
| **radeontop --list-counters** | Contadores disponibles | userspace | No | **UNKNOWN**; no usar como validación ASIC |
| **radeontop --verbose** | Verbose output | userspace | No | **DISPONIBLE** |
| **vulkaninfo** | Límites HW, extensiones, formatos | userspace | No | **DISPONIBLE** |
| **glxinfo -B** | Renderer GL, versión Mesa | userspace | No | **DISPONIBLE** |
| **glslangValidator -V** | Shader validation | userspace | No | **DISPONIBLE** |
| **hipcc -Rpass-analysis=kernel-resource-usage** | SGPR/VGPR/LDS/occupancy | compile-time | No | **N/A (ROCm)** |
| **glslang + SPIRV-Tools** | Shader stats, CFG | compile-time | No | **DISPONIBLE** |
| **dmesg / journalctl** | Kernel logs, faults, DPM transitions | userspace | No | **DISPONIBLE** |
| **pp_dpm_sclk/mclk, pp_power_profile_mode** | DPM states | sysfs | No (read) | **DISPONIBLE** |
| **power1_input, temp1_input, gpu_busy_percent** | Power, temp, busy | sysfs/hwmon | No (read) | **DISPONIBLE** |
| **lspci -vvv** | PCIe link width/speed, capabilities | userspace | No | **DISPONIBLE** |
| **radeontop -l** | Lista contadores disponibles | userspace | No | **UNKNOWN**; no equivale a PMU/validación ASIC |

---

## Archivos del Mapa

| Archivo | Propósito |
|---|---|
| `POLARIS12-MAP.md` | Este índice navegable |
| `HARDWARE-ROUTES.md` | Rutas de hardware por subsistema (cadena completa) |
| `SOFTWARE-CAPABILITIES.md` | Capacidades expuestas por cada capa de software |
| `EXPERIMENT-CANDIDATES.md` | Experimentos candidatos derivados del mapa |
| `UNVERIFIED-CLAIMS.md` | Afirmaciones sin evidencia verificada |
| `../COUNTERS-ASIC-TELEMETRY-KNOWLEDGE-ADDENDUM-2026-09-24.md` | Addenda incremental de ASIC/counters/telemetría y ranking de valor informacional |

---

## Navegación Rápida por Subsistema (Ver HARDWARE-ROUTES.md)

### Shader/ALU Path (A, B, C, D, E)
```
A: Shader/ALU → VALU (16-wide SIMD × 4/CU) → SALU (1/CU) → ISA GFX8 → RADV/ACO → radeontop/perf
B: SIMD → 4 SIMD/CU, 16-wide, 10 waves/SIMD → 10 waveslots/SIMD → instruction buffer → radeontop
C: VGPR/SGPR → 256 VGPR/wave (gran 4), 102 SGPR/wave (gran 8/16) → compiler stats → RGP
D: Occupancy → 10 waves/SIMD (máx 40/CU) → VGPR/SGPR/LDS limit → radeontop, ROCm profiler
E: LDS → 64 KB/CU, 32 banks → LDS_ALLOC, DS_* instructions → compiler stats
```

### Texture/Memory Path (F, G, H, R, S, T, U)
```
F: Texture Units → 4 TEX/CU (16 total) → 1 TEX/SIMD → radeontop tex busy
G: Texture Cache → V$ (16KB/CU) + L2 → VMEM latency → radeontop (parcial)
H: L2 Cache → 512 KB (Polaris12), 16-way, 64B lines → slices per mem channel → radeontop/perf (parcial)
R: Memory Controller → DPM MCLK (300/1500 MHz) → pp_dpm_mclk → radeontop mem busy
S: GDDR5 → 128-bit, 96–112 GB/s nominal/estimado según módulo/VBIOS; real `UNKNOWN` → radeontop mem busy
T: VRAM → 2 GB GDDR5, DEVICE_LOCAL → mem_info_vram_used → radeontop
U: GTT → System memory aperture → mem_info_gtt_used → radeontop
```

### Graphics Pipeline (I, J, K, L, M, N, O, P, Q)
```
I: Rasterizer → 2 rasterizers, 16 pix/clk → primitive rate → radeontop
J: Vertex Processing → VS, TES, GS → vertex throughput → radeontop
K: Geometry → Primitive assembly, tessellation → primitive rate → radeontop
L: Primitive Assembly → 1 prim/clk/rasterizer → radeontop (limitado)
M: ROP/Render Backends → 16 ROPs, 64 Gpix/s → color/depth writes → radeontop
N: DCC → Lossless color compression, 8:1 max → radv_disable_dcc, driconf
O: Depth/HTILE → Z/stencil compression, early-Z → radeontop depth busy
P: MSAA/FMASK → 1x/2x/4x/8x, FMASK compression → vulkaninfo sample counts
Q: FB Writes → CB/DB bypass L2 (GFX8) → DCC/HTILE interaction → radeontop
```

### System/Control (R–AJ)
```
R: Memory Controller → MCLK DPM (300/1500) → pp_dpm_mclk
S: GDDR5 → 128-bit, 96–112 GB/s nominal/estimado; bandwidth real `UNKNOWN`
T: VRAM → 2 GB, DEVICE_LOCAL → mem_info_vram_used
U: GTT → System aperture → mem_info_gtt_used
V: PCIe → capacidad máxima del endpoint Gen3×8; **negociado/verificado local Gen2×4** → lspci / R-4A
W: SDMA → 2 copy engines → dmesg
X: ACE/Async Compute → número de ACEs `UNKNOWN`; queue family observable → capability audit
Y: DMA/Copy Engines → 2 SDMA engines → dmesg
Z: PowerPlay/DPM → SCLK/MCLK DPM, pp_power_profile_mode → sysfs
AA: Clock Gating → Fine-grained (whitepaper) → hardware-only
AB: Voltage/Freq → ppfeaturemask (0xfff7bfff) → sysfs
AC: Sparse Residency → PRT, Vulkan sparse → vulkaninfo
AD: Descriptors → 128-bit descriptors, SGPR preload → shader stats
AE: RADV Workarounds → driconf (shrink_image_store, etc.) → dmesg
AF: Shader Compiler → LLVM/ACO, DPP, SDWA, 16-bit → shader stats
AG: Cache Behavior → V$/K$/L2, DCC, HTILE → radeontop/perf
AH: Sync/Barriers → Fences, semaphores, events, VkCmdPipelineBarrier → vulkaninfo
AI: Pipeline Statistics → VkQueryPool pipeline statistics → vulkaninfo
AJ: HW Perf Counters → UMR, radeontop, perf, amdgpu PMU → UMR/radeontop
```

---

## Referencias Cruzadas

- `HARDWARE-ROUTES.md` → Cadena completa hardware→software→observación por subsistema
- `SOFTWARE-CAPABILITIES.md` → Qué expone cada capa (Linux, Mesa, RADV, Vulkan)
- `EXPERIMENT-CANDIDATES.md` → Experimentos derivados con hipótesis/métricas/riesgos
- `UNVERIFIED-CLAIMS.md` → Claims sin evidencia verificada

---

## FASE B — DECISION GATE

### A. Capacidades Confirmadas y Utilizables (VERIFICADO + Accesible Userspace)

**20 capacidades confirmadas/utilizables.**

| Capacidad | Hardware | Linux/amdgpu | Mesa/RADV | Herramienta Medición | Uso Inmediato |
|---|---|---|---|---|---|
| **Shader/ALU (VALU/SALU)** | 512 lanes, 64 FMA/ciclo/CU | HWS scheduler | ACO (default) + LLVM | radeontop VALU/SALU busy | ✅ Workload actual |
| **SIMD / Wavefronts** | 32 SIMDs, 10 waves/SIMD | HWS dispatch | Wave32/64 (RADV_FORCE_WAVE64) | radeontop (agregado) | ✅ Workload actual |
| **VGPR/SGPR / Occupancy** | 256 VGPR/wave, 102 SGPR/wave | Register state save/restore | ACO regalloc | Compiler stats, RGP | ✅ Workload actual |
| **LDS** | 64 KB/CU, 32 banks | SPI allocation | NIR→ACO LDS alloc | Compiler stats | ✅ Disponible |
| **Texture Units** | 16 TEX units (1/SIMD) | Config init | image_sample, samplers | radeontop tex_busy | ✅ Workload actual |
| **Rasterizer** | 2 rasterizers, 16 pix/clk | Config init | VkPipelineRasterizationState | radeontop rasterizer_busy | ✅ Disponible |
| **ROP / Render Backends** | 16 ROPs; bypass CB/DB→L2 documentado a nivel familia, local `UNKNOWN` | Register config | VkPipelineColorBlendState, DCC control | radeontop rop_busy | ✅ Workload actual |
| **DCC / Color Compression** | Lossless, 8:1 max | Register config | radv_disable_dcc, driconf | dmesg, mem_busy | ✅ Workload actual (off) |
| **MSAA / FMASK** | 1x/2x/4x/8x, FMASK | Sample config | VkPipelineMultisampleStateCreateInfo | vulkaninfo sample_counts | ✅ Workload actual |
| **Depth / HTILE** | Early-Z, HTILE compression | Register config | radv_htile_enable | radeontop depth_busy | ✅ Disponible |
| **VRAM / GTT** | 2 GB GDDR5, 1.75 GiB heap | mem_info_* sysfs | VK_MEMORY_PROPERTY_* | mem_info_*, radeontop | ✅ Workload actual |
| **PCIe** | Capacidad máxima del endpoint Gen3×8; **negociado/verificado local Gen2×4** | amdgpu_pcie.c | N/A | lspci -vvv / R-4A | ✅ Verificado local (Gen2×4) |
| **SDMA / Copy Engines** | 2 engines | amdgpu_sdma.c | VkCmdCopyBuffer/Image | dmesg | ✅ Workload actual (upload) |
| **ACE / Async Compute** | Número de ACEs `UNKNOWN`; familia GCN4 documenta queues/HWS | HWS virtualization (source-level) | `VK_QUEUE_COMPUTE_BIT` (queue logical) | vulkaninfo/capability audit | **REQUIRES CAPABILITY AUDIT** |
| **PowerPlay / DPM** | SCLK 8 niveles, MCLK 3 niveles | pp_dpm_sclk/mclk, power1_input | N/A | sysfs, radeontop | ✅ Workload actual |
| **Power Profiles** | pp_power_profile_mode | sysfs write (root) | N/A | pp_power_profile_mode | ⚠️ Requiere root |
| **Sparse Resources** | PRT/PRT2 (64KB tiles) | VM management | VK_EXT_sparse_resource | vulkaninfo | ✅ Disponible |
| **Descriptors / Push Constants** | 128-bit descriptors, 256B push | USER-DATA SGPR preload | Descriptor Sets, Push Constants | shader stats | ✅ Workload actual |
| **RADV Workarounds** | N/A | N/A | driconf, env vars | driconf, dmesg | ✅ Probados (R-11) |
| **Pipeline Statistics** | VkQueryPool | N/A | VK_QUERY_TYPE_PIPELINE_STATISTICS | VkQueryPool | ✅ Disponible |
| **Shader Compiler (ACO)** | DPP, SDWA, 16-bit, ILP | N/A | ACO default GFX8+ | RADV_DEBUG=aco, RGP | ✅ Workload actual |

### B. Capacidades Confirmadas Pero NO Observables Directamente (Hardware-Only / Firmware)

**9 capacidades confirmadas pero no observables (10 brutas, 1 duplicado: Per-CU Power Gating).**

| Capacidad | Evidencia | Por Qué No Observable |
|---|---|---|
| **Clock Gating (fine-grained)** | Polaris Whitepaper | Hardware-only, no registers expuestos |
| **Voltage/Frequency Curves** | VBIOS/SPPT | Requiere flash VBIOS |
| **L2 Partitioning / Slice Assignment** | Hardware/firmware | No expuesto a userspace |
| **Per-CU Power Gating** | Hardware/firmware | No expuesto |
| **Per-SIMD Clock Control** | Hardware-only | No registers expuestos |
| **Memory Controller Timing/Registers** | Firmware (SMU) | No expuesto |
| **Per-ROP Control** | Hardware-only | No registers expuestos |
| **Memory Controller Registers** | Firmware | No expuesto |
| **GDS Explicit Control** | Solo compute shaders | Requiere compute shader |

### C. Capacidades Observables Pero NO Controlables (Read-Only)

**13 capacidades observables pero no controlables.**

| Capacidad | Observable Via | Por Qué No Controlable |
|---|---|---|
| **SCLK / MCLK actual** | pp_dpm_sclk/mclk, radeontop, freq1_input | DPM automático (policy SMU) |
| **MCLK policy upstream 5/16/20 (source-level)** | R-4A readout local 3/16/20 no reconciliado; no trigger local confirmado | SMU firmware/BIOS local `UNKNOWN` |
| **GPU Busy / Mem Busy %** | radeontop, sysfs | Resultado, no control |
| **Temperature** | temp1_input, radeontop | Resultado, no control |
| **VRAM / GTT Usage** | mem_info_*, radeontop | Resultado, no control |
| **PCIe Link Width/Speed** | lspci -vvv | Hardware negotiation |
| **L2 Hit/Miss Rate** | No expuesto directamente | Requiere contadores HW |
| **V$ / L2 Hit/Miss** | No expuesto directamente | Requiere contadores HW |
| **Wave Occupancy Real** | radeontop (estimado), UMR/RGP | HWS opaco |
| **Wave Distribution per SIMD/CU** | UMR (si funciona) | HWS opaco |
| **L1/L2 Hit/Miss Rates** | Perf/PMU (si disponible) | Requiere contadores HW |
| **ROPs/Blend Unit Utilization** | radeontop rop_busy (agregado) | No per-ROP |
| **Shader Compiler Decisions** | ISA output (RGP) | Compiler heuristics |

### D. Capacidades Controlables y Medibles (Sweet Spot para Experimentos)

**11 capacidades controlables y medibles.**

| Capacidad | Control | Medición | Experimento Candidato |
|---|---|---|---|
| **Wave Size (32 vs 64)** | `RADV_FORCE_WAVE64=0/1` | radeontop occupancy, FPS | **SHD-01** (ALTA) |
| **MSAA + Sample Shading** | `sampleShadingEnable` + `minSampleShading` | FPS, frametime, FS invocations, power | **FRAG-01** (ALTA) |
| **Loop Unroll Factor** | `pragma unroll` | VGPRs, occupancy, FPS | **SHD-02** (MEDIA) |
| **MSAA Level** | `--msaa 1|2|4|8` | mem_busy, power, FPS | **FRAG-02** (MEDIA) |
| **Primitive Count/Size** | `vkCmdDraw` count/size | radeontop rasterizer_busy, FPS | **GEO-02** (ALTA) |
| **Instance Count** | `instanceCount` en draw | VS invocations, FPS | **GEO-04** (ALTA) |
| **Vertex Shader Complexity** | VS ALU ops | vertex_busy, FPS | **GEO-01** (ALTA) |
| **VRAM Working Set** | Allocation size | mem_info_vram/gtt, FPS | **MEM-01** (ALTA) |
| **Sparse Residency** | `VK_EXT_sparse_resource` | mem_info_vram, page faults | **MEM-03** (MEDIA) |
| **Async Compute Overlap** | Separate compute queue | Graphics FPS + compute throughput | **ASY-01** (MEDIA) |
| **Power Profile Mode** | `pp_power_profile_mode` write (root) | power, SCLK/MCLK, FPS | **PWR-01** (MEDIA) |

### E. Experimentos de Mayor Valor Informativo (Top 5)

| Rank | Experimento | Hipótesis Central | Valor Informativo | Factibilidad | Prioridad |
|---|---|---|---|---|---|
| **1** | **FRAG-01: Sample Shading Real (MSAA 8x + minSampleShading=1.0)** | Sample shading rompe auto-pacing → multiplica fragment work ×8 con valores distintos → power ↑, mem_busy ↑ | **CRÍTICO**: Rompe el auto-pacing fetch-bound demostrado en ES-01/F2 | ✅ Vulkan estándar, RADV soporta, reversible | **ALTA** |
| **2** | **SHD-01: Wave32 vs Wave64** | Wave32 duplica occupancy teórica → mejor latency hiding en shaders fetch-bound | Resuelve: ¿wave64 limita occupancy en fetch-bound? | ✅ `RADV_FORCE_WAVE64=0`, reversible | **ALTA** |
| **3** | **GEO-01: Vertex Throughput** | VS pesado + muchos draw calls revela bottleneck VS/IA vs FS | Identifica si VS es bottleneck oculto | ✅ Vulkan estándar, reversible | **ALTA** |
| **4** | **MEM-01: VRAM Pressure / Spilling** | Working set > VRAM → eviction a GTT → performance cliff | Cuantifica límite VRAM real vs heap reportado | ⚠️ Riesgo OOM, reversible reduciendo working set | **ALTA** |
| **5** | **GEO-02: Primitive Throughput** | Triángulos microscópicos saturan rasterizer/primitive assembly | Cuantifica límite rasterizer/primitive assembly | ✅ Vulkan estándar, reversible | **ALTA** |

### F. Experimentos Que Deben Descartarse (Por Ahora)

**11 experimentos que deben descartarse.**

| Experimento | Razón de Descarte |
|---|---|
| **PWR-02: MCLK Forcing** | Requiere autorización explícita + `--danger` + riesgo térmico; congelado por política |
| **PWR-03: Thermal Throttling** | 90 °C es confound de ventana, no es un límite de seguridad; 96 °C es abort configurado; requiere protocolo y autorización; congelado |
| **BIOS/SPPT/VBIOS Flash** | Riesgo permanente, fuera de scope, política prohibida |
| **ppfeaturemask Write** | Bits desconocidos, riesgo inestabilidad; solo read |
| **Kalm Write** | Política: no tocar Kalm |
| **Mesa System Modificación** | Política: no tocar Mesa system |
| **Kernel/GRUB/amdgpu Config** | Política: no tocar kernel/GRUB |
| **Clock Gating Control** | Hardware-only, no accesible |
| **Voltage/Frequency Curve Modification** | Requiere VBIOS flash, prohibido |
| **L2 Partition Control** | Hardware/firmware only |
| **UMR/GPUPerfAPI sin verificar** | No instalar herramientas sin verificar compatibilidad GFX8 primero |

### G. Claims que siguen sin evidencia (auditoría capability pendiente)

**Los claims de prioridad permanecen abiertos; no se convierten en una instrucción de
instalación o ejecución.** La numeración histórica de la tabla se conserva como trazabilidad.

| Claim | Subsistema | Acción Requerida |
|---|---|---|
| **UMR funciona en GFX8/Polaris para leer contadores** | AJ | **REQUIRES AUTHORIZATION** para instalación/uso; no está confirmado localmente |
| **GPUPerfAPI soporta GFX8** | AJ | **REQUIRES CAPABILITY AUDIT**; catálogo v3.17/documental, no runtime |
| **radeontop --list-counters expone contadores HW** | AJ | `radeontop --list-counters` |
| **perf + amdgpu PMU expone eventos GFX8** | AJ | `perf list | grep amdgpu` + kernel config |
| **LDS = 64 KB/CU en Polaris12 (vs 32 KB en ISA GCN3)** | E | `umr --read-config` o kernel source `gfx_v8_0.c` |
| **CB/DB bypass L2 en GFX8 (confirmar en Polaris12)** | M, H | Verificar en `gfx_v8_0.c` / medir CB bandwidth |
| **Fetch latency L2 miss ~350 ciclos en Polaris12** | F, G, H | Contadores HW L1/L2 miss rate (FASE D) |
| **MCLK 1500 sostenido requiere `mem_busy_percent ≥20 %`** | R | **UNKNOWN**: upstream 5/16/20 y readout local 3/16/20 no reconciliados; no es trigger local |
| **CB writes bypass L2 en GFX8 (confirmar en nuestra GPU)** | M, Q | Medir CB bandwidth vs L2 traffic |
| **DCC deshabilitado para MSAA 4x/8x en RADV (confirmar)** | N, P | `radv_image_can_enable_dcc` code review |

---

## Decisión de FASE B

**FASE B COMPLETADA.** El mapa POLARIS12 está documentado con:

- ✅ 5 archivos creados: `POLARIS12-MAP.md`, `HARDWARE-ROUTES.md`, `SOFTWARE-CAPABILITIES.md`, `EXPERIMENT-CANDIDATES.md`, `UNVERIFIED-CLAIMS.md`
- ✅ 36 subsistemas mapeados (A–AJ) con cadena hardware→software→observación
- ✅ Capacidad real vs teórica documentada para nuestra RX 550
- ✅ Diferenciación OpenGL vs Vulkan
- ✅ Herramientas de observación inventariadas
- ✅ 30+ experimentos candidatos con checklist Regla 19
- ✅ 80+ claims no verificados catalogados
- ✅ DECISION GATE completado con clasificación A–G

**Próximo paso autorizado: FASE C — R-14-SUPERPOSITION-DISSECTION.md**

Reconstruir con herramientas no invasivas qué hizo Superposition para alcanzar 23.7W pico vs nuestros ~16W steady.

**Próximo paso condicional: FASE D — Performance Counters**

Prueba de lectura read-only: UMR → GPUPerfAPI → radeontop → debugfs/perf. Determinar si contadores HW disponibles para medir L1/L2 hit/miss, VALU utilization, memory controller bandwidth, wave occupancy real.

**NO avanzar a FASE E–J hasta completar FASE C y D.**
