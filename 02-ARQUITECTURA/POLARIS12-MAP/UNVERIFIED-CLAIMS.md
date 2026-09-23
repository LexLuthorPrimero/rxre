# UNVERIFIED-CLAIMS.md — Afirmaciones Sin Evidencia Verificada

**Fecha:** 2026-09-21  
**Versión:** 1.0  
**Propósito:** Registrar todas las afirmaciones técnicas que aparecen en documentación, foros, whitepapers o conversaciones pero que **no han sido verificadas experimentalmente en nuestra RX 550** ni corroboradas con fuentes primarias cruzadas.

**Regla:** Nada de esto se usa para diseñar experimentos hasta ser verificado. Cada entrada debe resolverse como **VERIFICADO**, **REFUTADO** o **DESCONOCIDO** antes de usarse.

---

## Formato de Entrada

| Campo | Descripción |
|---|---|
| **Claim** | La afirmación textual |
| **Fuente** | Dónde se encontró (URL, doc, persona) |
| **Subsistema** | ID A–AJ |
| **Estado Actual** | NO VERIFICADO / EN INVESTIGACIÓN / REFUTADO / VERIFICADO |
| **Evidencia Necesaria** | Qué experimento/lectura confirmaría/refutaría |
| **Prioridad** | ALTA / MEDIA / BAJA |
| **Riesgo si Falso** | Qué experimentos/conclusiones se verían afectados |

---

## Claims por Subsistema

### A. Shader/ALU

| Claim | Fuente | Estado | Evidencia Necesaria | Prioridad |
|---|---|---|---|---|
| "Polaris12 CU = 64 stream processors = 64 lanes SIMD × 1 instruction/4 cycles" | Polaris Whitepaper, GCN Whitepaper | **DOCUMENTADO** (no verificado en nuestra GPU) | `vulkaninfo` + `radeontop` VALU busy vs teórico | MEDIA |
| "FP64 rate = 1/16 en Polaris12" | GCN Whitepaper, TechPowerUp | **DOCUMENTADO** | Kernel compute FP64 benchmark vs FP32 | BAJA |
| "16-bit ops single-rate en GCN4+" | GPUOpen "GCN3/4/5 16-BIT OPERATION SUPPORT" | **DOCUMENTADO** | Shader con f16 packed vs f32 throughput | MEDIA |
| "DPP (Data Parallel Primitives) zero-latency cross-lane" | GPUOpen "DPP – DATA PARALLEL PRIMITIVES" | **DOCUMENTADO** | Shader con DPP vs LDS permute latency | MEDIA |
| "VALU peak = 64 instrucciones/ciclo/CU" | GPUOpen Advanced Shader Programming | **DOCUMENTADO** | `radeontop` VALU busy @ 1071 MHz vs teórico | MEDIA |

### B. SIMD / Scheduler

| Claim | Fuente | Estado | Evidencia Necesaria | Prioridad |
|---|---|---|---|---|
| "HWS virtualiza colas → any number of queues supported" | Polaris Whitepaper | **DOCUMENTADO** | `vulkaninfo` queue counts vs HWS behavior | BAJA |
| "4 wavefronts/clk dispatch per ACE" | Polaris Whitepaper | **DOCUMENTADO** | UMR wave launch tracking | BAJA |
| "Wave launch = 1 wave/CU antes de mover a siguiente CU" | GPUOpen "Graphics Work Distribution" | **DOCUMENTADO** | UMR wave distribution tracking | BAJA |

### C. VGPR/SGPR / Occupancy

| Claim | Fuente | Estado | Evidencia Necesaria | Prioridad |
|---|---|---|---|---|
| "VGPR granularity = 4, SGPR granularity = 8 (GFX8)" | GCN3 ISA, LLVM AMDGPU | **VERIFICADO** (ISA) | Compiler stats (`-Rpass-analysis=kernel-resource-usage`) | ALTA |
| "Occupancy limitada por VGPRs: ≤64→10 waves/SIMD, ≤256→3 waves/SIMD" | GPUOpen "Occupancy Explained", ORNL slides | **DOCUMENTADO** | Compiler stats + radeontop occupancy | ALTA |
| "Spilling VGPRs → scratch memory (global, usa vm_cnt)" | ROCm Blogs "Reading AMD GPU ISA" | **DOCUMENTADO** | Shader con alto VGPRs → scratch size + vm_cnt | MEDIA |

### E. LDS

| Claim | Fuente | Estado | Evidencia Necesaria | Prioridad |
|---|---|---|---|---|
| "LDS = 64 KB/CU en Polaris12 (vs 32 KB en GCN3 ISA)" | Polaris Whitepaper vs GCN3 ISA (32 KB) | **CONFLICTO** | `umr --read-config` o kernel source `gfx_v8_0.c` | ALTA |
| "LDS bandwidth = 128 bytes/ciclo/CU (32 banks × 4 bytes)" | GCN Whitepaper | **DOCUMENTADO** | Shader LDS-heavy + radeontop | MEDIA |
| "32 atomic units (int + float max/min/cmpxchg)" | GCN ISA | **DOCUMENTADO** | Shader atomic-heavy | BAJA |

### F. Texture Units / G. Texture Cache

| Claim | Fuente | Estado | Evidencia Necesaria | Prioridad |
|---|---|---|---|---|
| "1 TEX unit per SIMD = 16 TEX units totales (Polaris12)" | GPUOpen "Understanding Memory Coalescing" | **DOCUMENTADO** | `radeontop` tex_busy vs throughput teórico | MEDIA |
| "Filtered 128-bit texels = 64 clks/wave; point sampled 128-bit = 16 clks/wave" | GPUOpen "Understanding Memory Coalescing" | **DOCUMENTADO** | Shader con fetches filtrados vs point-sampled latency | MEDIA |
| "V$ = 16 KB/CU, 4-way, write-through" | GCN Whitepaper | **DOCUMENTADO** | Shader con working set > 16KB vs ≤ 16KB | MEDIA |
| "V$ miss → L2 → DRAM latency ~350 ciclos (miss L2)" | AMD Engine Optimization Hot Lap (Vega) | **INFERIDO** (no Polaris específico) | Shader con random access vs sequential | ALTA |

### H. L2 Cache

| Claim | Fuente | Estado | Evidencia Necesaria | Prioridad |
|---|---|---|---|---|
| "L2 = 512 KB en Polaris12 (vs 1 MB en P10/P11)" | igor'sLAB RX 550 review | **VERIFICADO** (fuente externa) | `umr --read-config` L2 size | ALTA |
| "L2 16-way, 64B lines, write-back, write-allocate" | GCN Whitepaper | **DOCUMENTADO** | `umr --read-config` | MEDIA |
| "En Polaris, Copy Engine + CP + Render Backend BYPASAN L2" | GPUOpen RDNA Architecture | **DOCUMENTADO** (RDNA doc, aplicar a Polaris) | Verificar en `gfx_v8_0.c` / dmesg | ALTA |

### I–L. Graphics Pipeline (Rasterizer, Vertex, Geometry)

| Claim | Fuente | Estado | Evidencia Necesaria | Prioridad |
|---|---|---|---|---|
| "2 Rasterizers, 1 prim/clk, 16 pix/clk" | GCN Whitepaper | **DOCUMENTADO** | `radeontop` rasterizer_busy | MEDIA |
| "Vertex waves: 1 per CU antes de mover a siguiente" | GPUOpen Advanced Shader Programming | **DOCUMENTADO** | UMR wave distribution | BAJA |
| "Aggressive Primitive Culling en Polaris" | Polaris Whitepaper | **DOCUMENTADO** | Shader con primitivas degeneradas vs culling | BAJA |

### M. ROP / N. DCC / O. HTILE / P. MSAA

| Claim | Fuente | Estado | Evidencia Necesaria | Prioridad |
|---|---|---|---|---|
| "CB/DB bypass L2 en GFX6-8 (escriben directo a memory controller)" | GCN Whitepaper (Tahiti), Mesa-dev 2019 | **DOCUMENTADO** (GCN1) / **INFERIDO** (GFX8) | Verificar en `gfx_v8_0.c` / CB bandwidth | ALTA |
| "DCC lossless, bloques dinámicos, pico 8:1 (256B)" | Polaris Whitepaper | **DOCUMENTADO** | `radv_disable_dcc` vs DCC on → mem_busy | ALTA |
| "RADV habilita DCC por defecto en color attachments GFX8+" | RADV commit ff8b0f6 | **VERIFICADO** (commit) | `radv_disable_dcc=1` vs default | ALTA |
| "RADV NO habilita DCC para MSAA 4x/8x por defecto" | mesa-dev 2018-November | **VERIFICADO** (lista) | `radv_image_can_enable_dcc` code | ALTA |
| "MSAA 8x: SHS=1, CCS=8 → blend/ROP por muestra" | RasterGrid MSAA Primer | **DOCUMENTADO** | Sample shading vs no sample shading | ALTA |
| "FMASK = fragment mask para MSAA compresión" | GCN Whitepaper | **DOCUMENTADO** | MSAA 8x vs 1x mem_busy | MEDIA |

### R–U. Memory System

| Claim | Fuente | Estado | Evidencia Necesaria | Prioridad |
|---|---|---|---|---|
| "MCLK DPM policy 128-bit: mclk_activity=20, up_hyst=5, down_hyst=16" | amd-gfx list 2020-09 | **VERIFICADO** (fuente primaria) | `pp_dpm_mclk` behavior vs policy | ALTA |
| "MCLK up threshold: actividad memoria sostenida ≥ ~20%" | amd-gfx list 2020-09 | **DOCUMENTADO** | Workload con mem_busy controlado | ALTA |
| "VRAM 2 GB GDDR5 128-bit 7 Gbps = 112 GB/s" | TechPowerUp, igor'sLAB | **VERIFICADO** | `lspci`, `radeontop` | ALTA |
| "Polaris12 L2 = 512 KB (P10/P11 = 1 MB)" | igor'sLAB | **VERIFICADO** | `umr --read-config` | ALTA |

### Z. PowerPlay/DPM

| Claim | Fuente | Estado | Evidencia Necesaria | Prioridad |
|---|---|---|---|---|
| "SCLK niveles: 0:214, 1:551, 2:734, 3:980, 4:1000, 5:1020, 6:1046, 7:1071 MHz" | `pp_dpm_sclk` sysfs observado | **OBSERVADO** (nuestro sistema) | `cat /sys/class/drm/card1/device/pp_dpm_sclk` | ALTA |
| "MCLK niveles: 0:300, 1:625, 2:1500 MHz" | `pp_dpm_mclk` sysfs observado | **OBSERVADO** (nuestro sistema) | `cat /sys/class/drm/card1/device/pp_dpm_mclk` | ALTA |
| "power1_input = estimador SMU (µW), no vatímetro físico" | Kernel docs `amdgpu/thermal.html` | **VERIFICADO** (docs kernel) | Comparar con vatímetro físico (si disponible) | ALTA |
| "ppfeaturemask = 0xfff7bfff en nuestra RX 550" | sysfs observado | **OBSERVADO** | `cat /sys/class/drm/card1/device/ppfeaturemask` | MEDIA |
| "Polaris fine-grained clock gating > GCN previo" | Polaris Whitepaper | **DOCUMENTADO** | No observable directamente | BAJA |

### AE. RADV Workarounds

| Claim | Fuente | Estado | Evidencia Necesaria | Prioridad |
|---|---|---|---|---|
| "radv_disable_shrink_image_store reduce faults 4→2" | R-11 (nuestro experimento) | **OBSERVADO** (nuestro experimento) | Re-ejecutar con/without | ALTA |
| "radv_wait_for_vm_map_updates sin efecto concluyente" | R-11 (nuestro experimento) | **OBSERVADO** (nuestro experimento) | Re-ejecutar | MEDIA |

### AJ. HW Performance Counters

| Claim | Fuente | Estado | Evidencia Necesaria | Prioridad |
|---|---|---|---|---|
| "UMR funciona en GFX8/Polaris para leer contadores" | UMR docs, ROCm | **NO VERIFICADO** | Instalar UMR + `umr --list-counters` | **ALTA** |
| "GPUPerfAPI soporta GFX8" | GPA docs | **NO VERIFICADO** | Instalar GPA + test | MEDIA |
| "radeontop --list-counters expone contadores HW" | radeontop source | **NO VERIFICADO** | `radeontop --list-counters` | ALTA |
| "perf + amdgpu PMU expone eventos GFX8" | Kernel config | **NO VERIFICADO** | `perf list | grep amdgpu` | ALTA |
| "RADV_DEBUG=perfcounters expone contadores" | Mesa source | **NO VERIFICADO** | `RADV_DEBUG=perfcounters` + vulkan app | MEDIA |

---

## Claims de Nuestra Investigación Propia (FASE A / ES-01 / F2)

| Claim | Fuente | Estado | Evidencia Necesaria | Prioridad |
|---|---|---|---|---|
| "Auto-pacing GPU: más fetches/frame → menos fps → misma fetches/seg → misma potencia" | ES-01 + F2 | **HIPÓTESIS SUSTENTADA** | Experimento controlado variable fetches | ALTA |
| "Clock-gating anula trabajo extra: unidades ociosas = 0 dynamic power" | ES-01/F2 + Polaris Whitepaper | **HIPÓTESIS COHERENTE** | Medir power vs work con clock gating deshabilitado (si posible) | ALTA |
| "Fetch-latency bound: miss L1/L2 → DRAM ~350 ciclos → bottleneck" | ES-01/F2 + AMD Hot Lap (Vega) | **HIPÓTESIS** | Contadores HW L1/L2 miss rate | ALTA |
| "MCLK 1500 sostenido solo con presión memoria real (Superposition)" | E-03, ES-01, Superposition | **OBSERVADO** | Comparar MCLK dist across workloads | ALTA |
| "Superposition alcanza 23.7W pico vs 16W nuestro workload" | EXPLORATORIO-GravityMark | **OBSERVADO** | Dissección Superposition (FASE C) | ALTA |

---

## Claims de Fuentes Secundarias (Requieren Verificación Primaria)

| Claim | Fuente Secundaria | Fuente Primaria Requerida | Estado |
|---|---|---|---|
| "Polaris12 = 8 CUs de 10 (2 deshabilitadas por fuse)" | TechPowerUp, videocardz | AMD whitepaper / kernel `gfx_v8_0.c` | **VERIFICAR** |
| "Polaris12 boost clock real 1141–1164 MHz (PowerTune)" | igor'sLAB | igor'sLAB article original | **VERIFICAR** |
| "GCN clock network = 20-35% total power" | Polaris Whitepaper | Whitepaper original | **DOCUMENTADO** |
| "21M flip-flops en Polaris" | Polaris Whitepaper | Whitepaper original | **DOCUMENTADO** |
| "R9 Nano 1 GHz = 8192 GFLOPS, 512 GB/s, 256 Gtex/s" | GPUOpen Advanced Shader Programming | AMD official specs | **DOCUMENTADO** (referencia R9 Nano, no RX 550) |

---

## Claims REFUTADOS por Nuestra Evidencia (Mover a ERRATA)

| Claim Original | Evidencia que Refuta | ERRATUM |
|---|---|---|
| "Kalm limitó a 25W" | Régimen 25W ocurrió SIN kalm (17/09) | ERRATUM-001 |
| "Cap 25W liga SCLK" | Fase B + EP-06: cap 25W con 1071 MHz | ERRATUM-001 |
| "power1_input = potencia real" | EP-06: draw real 13.6W vs power1_input 25W | ERRATUM-002 |
| "Mesa CUSTOM causó E5" | EP-05 A/B: CUSTOM = STOCK | ERRATUM-003 |
| "E1/E3 midieron iGPU" | EP-08: mem_info_* solo en amdgpu | ERRATUM-005 |
| "Métricas comparables sin etiquetar" | E-03: 13.40W (full) vs 15.75W (steady) | ERRATUM-004 |

---

## Plantilla para Nuevos Claims

Al encontrar un nuevo claim técnico:

```
| Claim | Fuente | Estado | Evidencia Necesaria | Prioridad |
|---|---|---|---|---|
| [Afirmación textual exacta] | [URL, doc, persona, commit] | [NO VERIFICADO / EN INVESTIGACIÓN / VERIFICADO / REFUTADO] | [Qué experimento/lectura confirmaría] | [ALTA/MEDIA/BAJA] |
```

---

## Resumen de Prioridades de Verificación

| Prioridad | Claims | Acción Inmediata |
|---|---|---|
| **ALTA** | LDS size (32 vs 64 KB), L2 size, UMR/perf counters, MCLK policy, CB bypass L2, DCC/MSAA, fetch latency | Instalar UMR, leer kernel source, test read-only |
| **MEDIA** | Texture unit throughput, LDS bandwidth, occupancy tables, DPP latency | Shader microbenchmarks |
| **BAJA** | Primitive culling, async compute queues, voltage curves | Documentar para futuro |

---

## Regla de Uso

> **Ningún claim en estado NO VERIFICADO o EN INVESTIGACIÓN se usa para diseñar experimentos.**
> 
> Solo claims **VERIFICADO** (fuente primaria + evidencia en nuestro sistema) o **DOCUMENTADO** (fuente primaria creíble, coherente con arquitectura) pueden usarse como base de diseño experimental.
> 
> Claims **INFERIDOS** requieren validación experimental antes de usarse.
> 
> Claims **REFUTADOS** se mueven a ERRATA y NO se usan.