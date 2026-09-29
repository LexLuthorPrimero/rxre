# EVIDENCE-MATRIX.md — Matriz de Evidencia × Conclusión × Clasificación

**Fecha:** 2026-09-21
**Versión:** 1.0
**Fuente:** AUDIT-001.md, ERRATA.md, METRICS-DEFINITIONS.md

> **Reconciliación terminológica 2026-09-24:** `draw real` se expresa como `W_SMU`,
> potencia estimada por sensor SMU; no existe vatímetro independiente.

---

## Leyenda de Clasificación

| Código | Significado |
|---|---|
| **VERIFICADO** | Medido/confirmado repetible en condiciones documentadas |
| **REPRODUCIBLE** | Comportamiento actual estable y repetible |
| **OBSERVADO** | Visto al menos una vez, sin repetición confirmada |
| **NO REPRODUCIBLE** | Histórico no reproducible, NO es hecho operacional |
| **HIPÓTESIS** | Candidata sin confirmar |
| **DESCARTADO** | Refutado con evidencia |
| **INVALIDADO** | Contradicho por nueva evidencia (ver ERRATA) |
| **DESCONOCIDO** | Sin explicación |

---

## Matriz Principal: Experimentos Históricos

| Experimento | Fecha | Conclusión Principal | Evidencia Clave | Clasificación |
|---|---|---|---|---|
| **E1** (vk-phong 640p) | 17/09 | power1≈25W, SCLK 350-390, MCLK 1250-1500, 1285 FPS | EP-08 (telemetría RX 550 real), EP-06 (no reproducible) | **NO REPRODUCIBLE** |
| **E3** (vk-phong 1080p) | 17/09 | power1≈25W, SCLK 350-390, MCLK 1250-1500, 443 FPS | EP-08, EP-06 | **NO REPRODUCIBLE** |
| **E5** (línea completa 1080p) | 17/09 | 25-31 W, MCLK 1250-1500, 74-92°C | EP-05 (CUSTOM ≠ STOCK), EP-06 (no reproducible) | **NO REPRODUCIBLE** |
| **Fase A** (sweep) | 18/09 | Curva plana cap 25W→35W no liga SCLK | EP-06 soak, Fase B | **VERIFICADO** |
| **Fase B** (cap probe) | 19/09 | Cap 25W no liga SCLK (1071 MHz libre) | EP-06 soak 1/2 | **REPRODUCIBLE** |
| **EP-06** Soak + Réplica | 19/09 | Régimen E1/E3 no reproducible ni frío ni caliente; draw máx 13.6 W | Soak 1/2/réplica final | **VERIFICADO** |
| **EP-05** Mesa CUSTOM A/B | 19/09 | CUSTOM vs STOCK indistinguibles (ΔFPS≤1%, ΔP≤0.3W); no reproduce E5 | Maps `/proc/<pid>/maps`, glxinfo | **VERIFICADO** (para 3 escenas) |
| **M1** (vkmark 35/30W) | 20/09 | Draw 12.27 W @35W → NO DISCRIMINATIVO; ΔFPS=0, ΔSCLK=0 | 10 runs pareados, IC95% | **VERIFICADO** |
| **Superposition** | 20/09 | 18.8 W avg / 23.7 W max fase activa; <27 W umbral | `telemetria_bare3.csv`, score 804 | **OBSERVADO** |
| **GravityMark** 200k | 20/09 | 12.4 W avg / 14.8 W max; VRAM 2.1 GB | `RESULTADO.md` | **OBSERVADO** |
| **E-03 Corregida** | 21/09 | 13.4 W avg full / 15.75 W avg steady; MCLK 1500 activo | `telemetria.csv`, 0 faults | **VERIFICADO** |
| **ES-01** Escalado | 21/09 | A/B/C/D/E = SIN EFECTO potencia; auto-pacing fetch-bound | 10 runs, steady window | **VERIFICADO** |
| **F2** (8 fetches) | 21/09 | Frametime 2×, potencia INVARIANTE (15.76 vs 16.13 W) | Control E1 vs F2 | **VERIFICADO** |

---

## Matriz: Conclusiones Transversales

| Conclusión | Evidencia | Clasificación | Notas |
|---|---|---|---|
| **Cap 25W liga SCLK en RX 550** | Fase B, EP-06 | **INVALIDADO** | SCLK 1071 MHz con cap 25W y 70-71°C |
| **Kalm impone cap 25W** | EP-06, journal 17/09 | **INVALIDADO** | Régimen 25W ocurrió SIN kalm |
| **power1_input = potencia real** | EP-06, SMU docs | **INVALIDADO** | Es estimador SMU; `W_SMU` máxima observada 13.6 W |
| **Mesa CUSTOM causa E5** | EP-05 A/B | **INVALIDADO** | CUSTOM = STOCK; no reproduce E5 |
| **E1/E3 midieron iGPU** | EP-08 (mem_info_*) | **REFUTADO** | Telemetría = RX 550 (amdgpu card1) |
| **SCLK 1071 MHz = máximo DPM** | pp_dpm_sclk (nivel 7*) | **VERIFICADO** | Nivel 7 = 1071 MHz |
| **MCLK 1500 MHz = máximo DPM** | pp_dpm_mclk (nivel 2*) | **VERIFICADO** | Nivel 2 = 1500 MHz |
| **Régimen E1/E3 reproducible** | Fase B + EP-06 | **INVALIDADO** | No reproducible con params autorizados |
| **W_SMU máximo observado** | EP-06 (13.6 W) + Superposition (23.7 W) | **OBSERVADO** | Superposition > EP-06 |
| **Fetch-bound = cuellos de botella** | ES-01 + F2 (frametime ∝ fetches) | **VERIFICADO** | 8 fetches = 2× frametime, power invariante |
| **Auto-pacing GPU** | ES-01 + F2 | **HIPÓTESIS** | Más fetches → menos fps → misma potencia |

---

## Matriz: Kalm por Experimento

| Experimento | Fecha | kalm-gpu.service | kalm real (py) | Estado Kalm | Nota |
|---|---|---|---|---|---|
| E1/E3/E5 | 17/09 | **INACTIVO** (muerto 18/09) | **NO ACTIVO** | SIN kalm | Régimen 25W ocurrió SIN kalm |
| Fase A sweep | 18/09 | inactive | ACTIVO (PID 4086/4087) | CON kalm | Régimen libre 1071 MHz |
| Fase B cap | 19/09 | inactive | ACTIVO | CON kalm | Cap 25W no liga |
| EP-06 soak | 19/09 | inactive | ACTIVO | CON kalm | Régimen libre |
| EP-05 A/B | 19/09 | inactive | ACTIVO | CON kalm | CUSTOM = STOCK |
| M1 | 20/09 | inactive | ACTIVO | CON kalm | M1 NO DISCRIMINATIVO |
| Superposition | 20/09 | inactive | ACTIVO | CON kalm | 23.7 W pico |
| E-03 corr | 21/09 | inactive | ACTIVO | CON kalm | 13.4/15.75 W |
| ES-01/F2 | 21/09 | inactive | ACTIVO | CON kalm | Auto-pacing |

**Conclusión transversal:** Kalm **no fue causa** del régimen 25W/360MHz; ocurrió cuando Kalm estaba **inactivo**. Con Kalm activo, la GPU opera en régimen libre (1071 MHz).

---

## Matriz: Mesa/ICD por Experimento

| Experimento | Mesa Usado | ICD Vulkan | Renderer GL | Verificación |
|---|---|---|---|---|
| E1/E3/E5 (17/09) | **SYSTEM MESA** (stock) | System radeon_icd | radeonsi | EP-05 maps no apuntan a `/opt/` para ese día; EP-05 A/B usa stock como baseline |
| Fase A/B | **SYSTEM MESA** | System radeon_icd | radeonsi | EP-06 usa stock |
| EP-05 CUSTOM | **CUSTOM MESA** (`/opt/mesa-26.2.2-rx550-haswell`) | `/opt/.../radeon_icd` | radeonsi (git-3281a69a8b) | Maps: `/opt/.../libgallium-26.2.2.so` |
| EP-05 STOCK | **SYSTEM MESA** | System radeon_icd | radeonsi (26.2.2) | Maps: `/usr/lib64/libgallium-26.2.2.so` |
| M1 | **SYSTEM MESA** | System radeon_icd | radeonsi | Maps + glxinfo verificados |
| Superposition | **SYSTEM MESA** (probable) | System radeon_icd | radeonsi | `DRI_PRIME=1002:699f` + binary directo; sin env CUSTOM |
| GravityMark | **SYSTEM MESA** (probable) | System radeon_icd | — (Vulkan) | `VK_ICD_FILENAMES=system` + `MESA_VK_DEVICE_SELECT` |
| E-03 corr | **SYSTEM MESA** | System radeon_icd | — (Vulkan) | Binario `main-graphics` compila contra system |
| ES-01/F2 | **SYSTEM MESA** | System radeon_icd | — (Vulkan) | Mismo binario |

**Nota:** Para Superposition y GravityMark la clasificación es **probable SYSTEM MESA** (basado en ausencia de variables de entorno CUSTOM y uso de ICD system). Clasificado como **OBSERVADO** no VERIFICADO por ausencia de `/proc/maps` capturado en esos runs.

---

## Matriz: DPM/Clocks por Experimento

| Experimento | SCLK Régimen | MCLK Régimen | power1_cap | power_avg_full | power_avg_steady |
|---|---|---|---|---|---|
| E1 (17/09) | 350-390 MHz | 1250-1500 MHz | 25W | ~25 W | N/A (no steady window def) |
| E3 (17/09) | 350-390 MHz | 1250-1500 MHz | 25W | ~25 W | N/A |
| E5 (17/09) | 600-750 MHz | 1250-1500 MHz | 25W | 25-31 W | N/A |
| Fase B cap25 | **1071 MHz** | 625 (picos 1500) | 25W | ~10-11 W | N/A |
| EP-06 soak | 1071 MHz | 625 (picos 1500) | 35W | 10-13 W | N/A |
| EP-05 CUSTOM | 1071 MHz | 625 (picos 1500*) | 35W | 9.4-12.2 W | N/A |
| M1 | 1071 MHz | 625 | 35W/30W | 12.27 W | N/A (M1 no usó steady window) |
| Superposition | 1071 + niveles bajos | 300-1500 | 35W | 13.8 W | **18.8 W** (fase activa) |
| E-03 corr | 1071 MHz | **1500 MHz** (220/277) | 35W | **13.4 W** | **15.75 W** |
| ES-01 base | 1071 MHz | 1500 MHz | 35W | 13.4 W | 15.75 W |
| F2 | 1071 MHz | 1500 MHz | 35W | 15.76 W | 15.76 W |

**Nota:** Solo E-03, ES-01, F2, Superposition (fase activa) tienen MCLK 1500 sostenido y reportan `power_avg_steady` ≥ 15 W.

---

## Matriz: Clasificación de Cuellos de Botella

| Workload | API | FPS | Frametime | GPU Busy | SCLK | MCLK | mem_busy | Cuello Identificado |
|---|---|---|---|---|---|---|---|---|
| vk-phong 640p (M1) | Vulkan | 74 | 13.5 ms | 99% | 1071 | 625 | 9% | **NO SCLK-bound** (FPS igual 340-1071) |
| vk-shading 1080p | Vulkan | 73 | 13.7 ms | 99% | 1071 | 625 | 9% | — |
| Superposition | OpenGL | ~45* | ~22 ms* | 100% | 1071 | 300-1500 | ? | **Geometría + Raster + Fragment real** |
| E-03 base | Vulkan | 8.95 | 112 ms | 80% (100% steady) | 1071 | 1500 | 28.6% (36% steady) | **Fetch-latency bound** |
| ES-01 A (layers 8) | Vulkan | 4.5 | 223 ms | 100% | 1071 | 1500 | 36% | **Fetch-latency bound** |
| ES-01 B (FMA 96) | Vulkan | 8.95 | 112 ms | 100% | 1071 | 1500 | 36% | **Fetch-latency bound** (ALU libre) |
| ES-01 C (tex 8192) | Vulkan | 8.95 | 112 ms | 100% | 1071 | 1500 | 36% | **Fetch-latency bound** |
| ES-01 D (MSAA 8x) | Vulkan | 8.90 | 112.5 ms | 100% | 1071 | 1500 | 36% | **Fetch-latency bound** (CB dedup) |
| F2 (8 fetches) | Vulkan | 4.55 | 222 ms | 100% | 1071 | 1500 | 36% | **Fetch-latency bound** (2× fetches = 2× ft) |

**Conclusión transversal:** Todos los workloads sintéticos Vulkan probados están en **fetch-latency bound** (mem_busy 36%, SCLK 1071 fijo, auto-pacing). Superposition (OpenGL, geometría real) rompe este patrón y alcanza mayor potencia.

---

## Gaps Identificados (DESCONOCIDO)

| Gap | Descripción | Prioridad Investigación |
|---|---|---|
| Causa raíz régimen 17/09 | Qué disparó SCLK 350 / MCLK 1250 / 25W en sesión 17/09 | **ALTA** |
| MCLK sostenido | Qué dispara MCLK 1250-1500 sostenido (hoy solo 625 + picos) | **ALTA** |
| Draw real máximo | Límite térmico/eléctrico real de la RX 550 (>13.6 W medidos) | **ALTA** |
| Bottleneck GL 640p | CPU submissions vs present vs VRAM/GTT | **MEDIA** |
| Origen "phong 1285 fps" | ¿Era otra ventana/superficie? | **BAJA** |
| Costo real DRAM | `mem_busy` ≠ % bandwidth; necesidad contadores HW | **ALTA** |
| DCC behavior real | ¿Superposition usa DCC? ¿Nuestro CB lo deshabilita? | **MEDIA** |
| PowerPlay internals | ppfeaturemask, DPM niveles intermedios, voltage behavior | **MEDIA** |
| PCIe x8 vs x4 | Link width/speed negociado real | **BAJA** |
| BIOS/fuses CUs | Unidades deshabilitadas: fuse/BIOS/físico | **BAJA** |
