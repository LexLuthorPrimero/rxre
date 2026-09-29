# R-14 — Superposition Dissection (NO INVASIVO)

**Fecha:** 2026-09-21
**Objetivo:** Caracterizar la `W_SMU` observada de Superposition (~23.7 W pico /
~22.3 W steady) frente a ~16 W `W_SMU` steady de los workloads sintéticos (E-03, ES-01, F2).

---

## 1. Metodología

- **Workload:** Superposition 1.1 (Unigine), configuración efectiva `1600×900/Medium`, OpenGL
  (vía Mesa/radeonsi), 1 iteración. La petición/args `1920×1080/High` no coincide con el
  registro efectivo y no se usa como claim.
- **GPU:** RX 550 (Polaris12, 8 CUs, 512 SP, 16 ROPs, 128-bit GDDR5 7 Gbps).
- **Driver:** Mesa 26.2.2 (radeonsi/radv), kernel 7.2.4.
- **Selección GPU:** `DRI_PRIME=1002:699f` + ICD; verificar el device/contexto RX 550.
  `MESA_VK_DEVICE_SELECT` no es una garantía.
- **Telemetría:** script sysfs 10 Hz (`power1_input`/`W_SMU`, temp, gpu_busy, mem_busy,
  VRAM/GTT, SCLK/MCLK) — archivo `telemetria.csv`.

> **RECONCILIACIÓN DE EVIDENCIA (2026-09-24):** `power1_input` se interpreta como
> `W_SMU` (potencia estimada por sensor SMU), no como vatímetro. Los datos muestran una
> asociación direccional entre la carga de Superposition y la actividad de geometría/shader;
> no demuestran que un bloque concreto sea la causa de la potencia. `mem_busy_percent` es
> un proxy y no bandwidth. La formulación vigente es **observación/correlación**, no causalidad
> demostrada.
- **Ejecución:** 1 iteración, configuración efectiva `1600×900/Medium`, OpenGL, MSAA off.
- **Duración real benchmark:** ~4-5 min (world_load + benchmark loop). Proceso terminado por SIGTERM tras 240 s; benchmark completado (score 804).
- **Artefactos:** `runs/superposition_dissection_1/{telemetria.csv, superposition.log}`.

> **OBSERVADO:** Superposition CSV/TXT internos no se escribieron (proceso terminado por SIGTERM antes de flush). Métricas clave obtenidas vía telemetría sysfs 10 Hz.

---

## 2. Configuración Efectiva (VERIFICADO)

| Parámetro | Valor | Fuente |
|---|---|---|
| API | OpenGL (Mesa/radv, *no* Vulkan nativo) | log: "OpenGL renderer: AMD Radeon RX 550" |
| Resolución | **1600×900 efectiva** | log: window 1600×900; el arg 1920×1080 no coincide |
| Preset | **Medium** | log: "Preset: 1 (Medium)" |
| MSAA | Desactivado | XML default |
| Calidad | **Medium** | log/XML |
| Iteraciones | 1 | XML |
| Ventana | Windowed 1600×900 | log + args |
| API Gráfica | OpenGL (NO Vulkan) | log: "OpenGL renderer: AMD Radeon RX 550" |
| Renderizador | AMD Radeon RX 550 (radeonsi, polaris12) | log |

> **INFERIDO:** El XML declara `<api>DirectX</api>` pero en Linux usa ruta OpenGL (probablemente vía DXVK o path nativo OpenGL del engine). No hay evidencia de Vulkan nativo.

---

## 3. Resultados Telemetría (METRICS-DEFINITIONS.md)

> `power_*` significa `W_SMU` de `power1_input`; no es vatímetro independiente.

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

> **INTERPRETACIÓN:** Superposition logra mayor `W_SMU` con **menor `mem_busy`** y **mismos clocks**. La asociación con geometría/vertex/post-proceso es direccional; no identifica por sí sola el bloque causal ni excluye otros factores.

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
| `power_avg_steady` | 22.31 W | 15–16 W | Mayor `W_SMU`; correlación con trabajo de geometría/shader |
| `mem_busy_steady` | 24.6 % | 35.9 % | Proxy menor; no identifica el limitante causal |
| `gpu_busy_steady` | ~100 % | ~100 % | Ambos saturados |
| `SCLK` | 1071 MHz | 1071 MHz | Clock ceiling alcanzado |
| `MCLK` | 1500 MHz | 1500 MHz | MCLK reportada; no equivale a DRAM data rate efectiva |
| `VRAM` | 1.55 GB | 0.23 GB | Texturas/geometría reales |

> **CONCLUSIÓN:** el techo observado de ~22–24 W steady es una correlación con una carga
> geométrica/shader más intensa; no demuestra que ALU/compute sea el limitante único. `mem_busy`,
> clocks y VRAM son proxies/observaciones, no una explicación causal completa.

---

## 8. Próximos Experimentos Recomendados (Prioridad)

| Exp | Objetivo | Métrica Clave | Factibilidad |
|---|---|---|---|
| **GEO-01: Vertex Throughput** | VS pesado + draw calls masivos | vertex_busy, `W_SMU` | ✅ Vulkan, reversible |
| **GEO-02: Primitive Throughput** | Triángulos microscópicos | rasterizer_busy, `W_SMU` | ✅ Vulkan, reversible |
| **FRAG-01: Sample Shading Real** | MSAA 8x + sampleShading=1.0 | FS invocations, `W_SMU` | ✅ Vulkan/RADV |
| **GEO-05: Overdraw Geométrico** | Capas con depth test real | depth_busy, `W_SMU` | ✅ Vulkan |
| **SHD-01: Wave32 vs Wave64** | Occupancy vs latency hiding | occupancy, `W_SMU` | ✅ Vulkan/RADV |

> **SNAPSHOT HISTÓRICO — NO ES UNA AUTORIZACIÓN:** la propuesta de FASE D/UMR/radeontop/perf
> queda `REQUIRES AUTHORIZATION`; la programación de counters sigue congelada.

---

## 9. Archivos Generados

```
03-EXPERIMENTOS/R-14-SUPERPOSITION-DISSECTION/
├── run_superposition.sh
└── runs/
    └── superposition_dissection_1/
        ├── telemetria.csv      (2088 muestras, 10 Hz, 240 s)
        └── superposition.log   (log completo, score 804)
```

---

## 10. Estado FASE C

**COMPLETADA.** Superposition diseccionado: ~22.3 W steady, 24.7 W pico, score 804. La diferencia frente a los workloads sintéticos es una **correlación direccional** con geometría/vertex/post-proceso; no identifica causalidad última. No se alcanzó 27 W steady. No se modificó kernel/Mesa/amdgpu/Kalm. Solo lectura sysfs + ejecución Superposition.

**NO SE INICIA FASE D** hasta autorización explícita.
