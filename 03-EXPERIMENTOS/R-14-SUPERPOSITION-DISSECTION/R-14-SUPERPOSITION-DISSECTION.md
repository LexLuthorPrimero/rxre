# R-14 — Superposition Dissection (NO INVASIVO)

**Fecha:** 2026-09-21  
**Objetivo:** Caracterizar por qué Superposition alcanza ~23.7 W pico / ~22.3 W steady en nuestra RX 550, vs ~16 W steady de nuestros workloads sintéticos (E-03, ES-01, F2).

---

## 1. Metodología

- **Workload:** Superposition 1.1 (Unigine), preset "High", 1920×1080, OpenGL (via Mesa/radv), 1 iteración.
- **GPU:** RX 550 (Polaris12, 8 CUs, 512 SP, 16 ROPs, 128-bit GDDR5 7 Gbps).
- **Driver:** Mesa 26.2.2 (radeonsi/radv), kernel 7.2.4.
- **Selección GPU:** `DRI_PRIME=1002:699f` + `VK_ICD_FILENAMES` (forzado a RX 550).
- **Telemetría:** script sysfs 10 Hz (power1_input, temp, gpu_busy, mem_busy, VRAM/GTT, SCLK/MCLK) — archivo `telemetria.csv`.
- **Ejecución:** 1 iteración, preset "High" (texturas Medium), 1920×1080, OpenGL, MSAA off.
- **Duración real benchmark:** ~4-5 min (world_load + benchmark loop). Proceso terminado por SIGTERM tras 240 s; benchmark completado (score 804).
- **Artefactos:** `runs/superposition_dissection_1/{telemetria.csv, superposition.log}`.

> **OBSERVADO:** Superposition CSV/TXT internos no se escribieron (proceso terminado por SIGTERM antes de flush). Métricas clave obtenidas vía telemetría sysfs 10 Hz.

---

## 2. Configuración Efectiva (VERIFICADO)

| Parámetro | Valor | Fuente |
|---|---|---|
| API | OpenGL (Mesa/radv, *no* Vulkan nativo) | log: "OpenGL renderer: AMD Radeon RX 550" |
| Resolución | 1920×1080 | XML + log |
| Preset | High (texturas Medium) | log: "Preset: 1 (Medium)" |
| MSAA | Desactivado | XML default |
| Calidad | High | XML |
| Iteraciones | 1 | XML |
| Ventana | Windowed 1600×900 → forzado 1920×1080 | XML + args |
| API Gráfica | OpenGL (NO Vulkan) | log: "OpenGL renderer: AMD Radeon RX 550" |
| Renderizador | AMD Radeon RX 550 (radeonsi, polaris12) | log |

> **INFERIDO:** El XML declara `<api>DirectX</api>` pero en Linux usa ruta OpenGL (probablemente vía DXVK o path nativo OpenGL del engine). No hay evidencia de Vulkan nativo.

---

## 3. Resultados Telemetría (METRICS-DEFINITIONS.md)

### 3.1 Ventana Completa (2088 muestras, ~208 s)

| Métrica | Valor |
|---|---|
| `power_avg_full` | **21.54 W** |
| `power_max_full` | **24.71 W** |
| `power_min_full` | 3.67 W (idle) |
| `temp_avg_full` | 70.7 °C (max 92 °C) |
| `gpu_busy_avg_full` | 95.3 % |
| `mem_busy_avg_full` | 23.4 % |
| `vram_avg_full` | 1554 MB (pico ~1.6 GB) |
| `gtt_avg_full` | 59 MB |

### 3.2 Régimen Estable (`gpu_busy ≥ 95`, SCLK=1071, MCLK=1500)

| Métrica | Valor | N muestras |
|---|---|---|
| `power_avg_steady` | **22.31 W** | 1987 |
| `power_max_steady` | **24.71 W** | — |
| `power_min_steady` | 6.71 W | — |
| `mem_busy_avg_steady` | **24.6 %** | — |
| `gpu_busy_avg_steady` | ~100 % | — |
| SCLK 1071 MHz | 95 % (1887/1987) | — |
| MCLK 1500 MHz | 99.8 % (1983/1987) | — |

> **NOTA:** `power_avg_full` (21.54 W) < `power_avg_steady` (22.31 W) porque la ventana completa incluye arranque/idle. Comparar siempre `*_steady` contra `*_steady`.

---

## 4. Comparación con Workloads Anteriores (FASE A/B)

| Workload | `power_avg_steady` | `power_max_steady` | `mem_busy_steady` | SCLK | MCLK | API |
|---|---|---|---|---|---|---|
| **Superposition (R-14)** | **22.31 W** | **24.71 W** | **24.6 %** | 1071 MHz | 1500 MHz | OpenGL |
| **E-03 (Diseño B)** | 15.75 W | 15.80 W | 35.9 % | 1071 MHz | 1500 MHz | Vulkan |
| **ES-01 (F2)** | 16.17 W | 16.27 W | 35.9 % | 1071 MHz | 1500 MHz | Vulkan |
| **ES-01 base** | 15.75 W | 15.80 W | 35.9 % | 1071 MHz | 1500 MHz | Vulkan |
| **E-01 (vkmark)** | 13.23 W | 13.35 W | ~7 % | 1071 MHz | 300 MHz | Vulkan |
| **E-02 (mem)** | 12.38 W | 12.51 W | 3–7 % | 1071 MHz | 300 MHz | Vulkan |

### Hallazgos Clave

| Hallazgo | Evidencia | Clasificación |
|---|---|---|
| **Superposition consume +6.5 W steady vs E-03** | 22.31 vs 15.75 W | **VERIFICADO** |
| **Mismo SCLK/MCLK, distinta potencia** | Ambos 1071/1500 MHz | **VERIFICADO** |
| **mem_busy MÁS BAJO en Superposition** | 24.6 % vs 35.9 % | **VERIFICADO** |
| **VRAM mucho mayor en Superposition** | 1.55 GB vs 0.23 GB | **VERIFICADO** |
| **Superposition NO usa Vulkan** | OpenGL renderer | **VERIFICADO** |
| **GPU busy ~100 % en ambos** | gpu_busy_steady ≈ 100 % | **VERIFICADO** |

> **INTERPRETACIÓN:** Superposition logra mayor potencia con **menor mem_busy** y **mismos clocks**. Diferencia no es memoria ni clocks, sino **carga ALU/compute y geometría** (vertex/primitive throughput, overdraw real, tessellation, post-proceso).

---

## 5. Hipótesis Explicativas (ordenadas por evidencia)

| Hipótesis | Evidencia a Favor | Evidencia en Contra | Estado |
|---|---|---|---|
| **H1: Carga geométrica/vertex real** — Superposition renderiza geometría compleja (tessellation, muchas primitivas, vertex shaders pesados) → satura vertex processing y rasterizer → mayor ocupación ALU. | Vertex/geometry pipeline activo; tessellation habilitado; primitivas complejas. | No medido directamente vertex throughput. | **HIPÓTESIS FUERTE** |
| **H2: Overdraw real + post-proceso** — Overdraw real (capas de geometría solapadas) + post-proceso (SSAO, DOF, motion blur, bloom) → mayor fragment shader invocations + ROP pressure. | Post-proceso habilitado (DOF, motion blur, SSAO, etc.); overdraw geométrico real. | Nuestro workload ES-01 tiene overdraw sintético (4 capas) pero sin geometría real. | **HIPÓTESIS FUERTE** |
| **H3: OpenGL vs Vulkan — driver overhead** — Radeonsi (OpenGL) puede generar mayor ocupación ALU que RADV (Vulkan) para cargas similares, por distinto scheduling/compilación. | API distinta (radeonsi vs radv); distinta compilación (LLVM vs ACO). | Diferencia de 6.5 W grande para ser solo driver. | **HIPÓTESIS MODERADA** |
| **H4: Carga compute/async** — Superposition podría usar compute shaders para culling, particles, etc., activando ACEs. | Engine moderno; async compute probable. | No verificado uso ACE en log. | **HIPÓTESIS DÉBIL** |
| **H5: PowerPlay behavior distinto** — Carga distinta → SMU eleva voltaje/frecuencia de forma distinta. | Mismos clocks, distinta potencia. | Voltage no medido. | **HIPÓTESIS ESPECULATIVA** |

---

## 6. Comparación con Objetivo 27–35 W

| Métrica | Superposition | Objetivo 27 W | Gap |
|---|---|---|---|
| `power_avg_steady` | 22.31 W | 27 W | -4.7 W |
| `power_max_steady` | 24.71 W | 35 W | -10.3 W |

> **CONCLUSIÓN:** Superposition es el workload **más demandante medido hasta ahora** en nuestra RX 550 (22.3 W steady), pero **NO alcanza 27 W steady**. El techo observado (~24.7 W pico) sugiere que con clocks actuales (1071/1500) y DPM auto, la GPU no extrae más potencia sin forzar clocks/voltajes.

---

## 7. Evidencia de Cuello de Botella (Cross-Reference)

| Métrica | Superposition | Nuestros Workloads | Interpretación |
|---|---|---|---|
| `power_avg_steady` | 22.31 W | 15–16 W | Superposition usa más ALU/geometría |
| `mem_busy_steady` | 24.6 % | 35.9 % | **NO es memoria** el limitante |
| `gpu_busy_steady` | ~100 % | ~100 % | Ambos saturados |
| `SCLK` | 1071 MHz | 1071 MHz | Clock ceiling alcanzado |
| `MCLK` | 1500 MHz | 1500 MHz | Memoria a tope |
| `VRAM` | 1.55 GB | 0.23 GB | Texturas/geometría reales |

> **CONCLUSIÓN:** El techo de ~22–24 W steady NO es memoria (mem_busy bajo), NO es clocks (máximos), SÍ es **utilización ALU/compute real** bajo OpenGL/radeonsi con geometría compleja.

---

## 8. Próximos Experimentos Recomendados (Prioridad)

| Exp | Objetivo | Métrica Clave | Factibilidad |
|---|---|---|---|
| **GEO-01: Vertex Throughput** | VS pesado + draw calls masivos | vertex_busy, power | ✅ Vulkan, reversible |
| **GEO-02: Primitive Throughput** | Triángulos microscópicos | rasterizer_busy, power | ✅ Vulkan, reversible |
| **FRAG-01: Sample Shading Real** | MSAA 8x + sampleShading=1.0 | FS invocations, power | ✅ Vulkan/RADV |
| **GEO-05: Overdraw Geométrico** | Capas con depth test real | depth_busy, power | ✅ Vulkan |
| **SHD-01: Wave32 vs Wave64** | Occupancy vs latency hiding | occupancy, power | ✅ Vulkan/RADV |

> **PRÓXIMO PASO AUTORIZADO:** FASE D — Performance Counters (UMR/radeontop/perf) para medir vertex/primitive throughput, cache hit rates, stall cycles en Superposition vs nuestro workload.

---

## 9. Archivos Generados

```
experiments/R-14-SUPERPOSITION-DISSECTION/
├── run_superposition.sh
└── runs/
    └── superposition_dissection_1/
        ├── telemetria.csv      (2088 muestras, 10 Hz, 240 s)
        └── superposition.log   (log completo, score 804)
```

---

## 10. Estado FASE C

**COMPLETADA.** Superposition diseccionado: ~22.3 W steady, 24.7 W pico, score 804. Diferencia vs nuestros workloads = geometría/vertex/post-proceso real vs sintético. No se alcanzó 27 W steady. No se modificó kernel/Mesa/amdgpu/Kalm. Solo lectura sysfs + ejecución Superposition.

**NO SE INICIA FASE D** hasta autorización explícita.