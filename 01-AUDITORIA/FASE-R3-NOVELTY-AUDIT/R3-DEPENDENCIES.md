# R-3 DEPENDENCY MATRIX — Dependencias de las Ideas R-3

> **Archivo:** `R3-DEPENDENCIES.md`
> **Fase:** FASE R-3 — ORIGINAL IDEAS, NOVELTY AUDIT & RESEARCH CANDIDATES
> **Fecha:** 2026-09-22 — Modo SOLO DOCUMENTAL
> **Clasificación:** [DISEÑADO]. Marcas: **CONFIRMED** / **LIKELY** / **POTENTIAL** / **UNKNOWN**.
> Relaciones con el ecosistema (BERRETA, GHOST, RX-Comp, Orquestador, FASE K/M/O/P/Q,
> WORKLOAD-SINTETICO) documentadas como POTENTIAL DEPENDENCY hasta tener evidencia.

---

## 1. Cadenas de dependencia por idea

### I-01 — TBDR emulation on IMR
```
TBDR-IMR
├─► Vulkan layer / compute binning (userland)          [LIKELY]
│    └─► geometry analysis (bin assign)                 [LIKELY]
│         └─► render pass control (renderArea/scissor)  [POTENTIAL: PFOB/GO-Assist en GFX8 no verificado]
├─► memory behavior (CB/DB bypass L2)                   [CONFIRMED]
├─► HTILE/DCC interaction (evitar romper)               [LIKELY]
└─► FASE Q (radeonsi TS/HTILE/DCC = "ya es el mecanismo HW")  [POTENTIAL → E]
```

### I-02 — Temporal Tile Delta Reuse
```
Temporal Tile Reuse
├─► frame history (prev color/depth)                    [CONFIRMED]
├─► tile detection (compare / renderArea parcial)       [LIKELY]
├─► reprojection (I-03 camera-only = lock detector)     [LIKELY]
├─► DCC alignment (evitar invalidar compresión)         [POTENTIAL]
├─► FASE K (runner A/B)                                 [LIKELY]
├─► WORKLOAD-SINTETICO (harness F2, escena estática)    [CONFIRMED]
└─► post-processing/shadows/particles (rompen el skip)  [CONFIRMED → límite de alcance]
```

### I-03 — Jitter as Reprojection Signal
```
Jitter Reprojection
├─► Vulkan observation (¿la escena usa TAA? → aplicar jitter)  [UNKNOWN]
├─► TAA identification (detectar pipeline TAA)          [UNKNOWN]
├─► reprojection (depth + matmul + bilinear)            [LIKELY]
└─► I-02 (proveer el "tile-lock" si cámara estática)    [LIKELY]
     └─► motion vectors REALES siguen necesarios para objetos  [CONFIRMED]
```

### I-04 — ROP offload to compute
```
ROP Offload
├─► compute rasterizer (visibilidad)                    [LIKELY — pero costoso]
├─► memory (SSBO/UAV atomics)                           [LIKELY]
├─► synchronization (order-dependent blend/depth)       [CONFIRMED — costo]
├─► async-compute co-scheduling (única pieza útil)      [LIKELY → BERRETA/ASY-01]
└─► FASE M / contadores (sin autorización → señal indirecta)  [UNKNOWN]
```

### I-05 — Frame Recorder GFX8
```
GFX8 Frame Recorder
├─► Vulkan interception (apitrace/gfxreconstruct)       [CONFIRMED]
├─► command capture                                   [CONFIRMED]
├─► timestamps (query timer; sin contadores)            [LIKELY]
├─► SQTT capture (RADV MESA_VK_TRACE=rgp)               [POTENTIAL: requiere build + profile_peak authorization]
├─► replay (gfxreconstruct)                             [CONFIRMED]
└─► FASE K (telemetría y runner como sustrato)          [LIKELY]
```

### I-06 — Predictive Ghost Cache
```
Predictive Ghost Cache
├─► camera/motion prediction (heurística)               [LIKELY]
├─► texture/tile working-set tracking                   [LIKELY]
├─► prefetch warm-up (userland; sin API HW en GCN4)     [CONFIRMED límite]
├─► amdgpu PRT/sparse (inestable en Polaris)            [UNKNOWN]
├─► GHOST (coordinación métricas, NO colisión)          [POTENTIAL DEPENDENCY]
└─► ES-01/F2 (p99 ∝ fetch → objetivo)                   [CONFIRMED]
```

### I-07 — Async Optical Flow Frame Generation
```
Async Optical Flow
├─► motion estimation compute (FFX OF: SEARCH/FILTER/UPSCALE)  [LIKELY]
├─► frame interpolation compute (warp/blend)            [LIKELY]
├─► async overlap (ACE)                                 [POTENTIAL: misma array CU, no hay bloque separado]
├─► synchronization (fence: flujo debe terminar antes de presentar)  [CONFIRMED]
├─► FASE P (frame generation/upscaling — se evalúa allí) [CONFIRMED relación]
├─► FASE K (separar REAL/GENERADO/latencia/power)       [LIKELY]
└─► potencia (adds sobre 35 W cap)                      [LIKELY]
```

### I-08 — Closed-Loop Quality Governor
```
Closed-Loop Governor
├─► GFX8 counters → NO AUTORIZADOS → señal read-only    [CONFIRMED restricción]
├─► telemetry read-only (frametime/power/clocks/kalm)   [CONFIRMED]
├─► controller (PID/hysteresis sobre render-scale)      [LIKELY]
├─► actuación: render-scale de la app (sin writes HW)   [CONFIRMED límite]
├─► FASE K (runner + etiquetado DPM)                    [LIKELY]
└─► oscilación/estabilidad (hysteresis, sample rate)    [CONFIRMED riesgo de diseño]
```

### I-09 — L2-Resident Internal Resolution
```
L2-Resident
├─► frame size < L2 → NO prueba residencia (CB/DB bypass L2)  [CONFIRMED]
├─► L2 hit/miss counters (no expuestos; SPM bloqueado)  [UNKNOWN]
├─► compute-UAV re-read sub-claim                        [POTENTIAL — marginal]
└─► DCC/HTILE (mecanismo real de "mantener comprimido") [CONFIRMED alternativa]
```

### I-10 — Async Auxiliary Renderer
```
Async Auxiliary Renderer
├─► Vulkan async queues (compute/ACE)                   [REQUIRES CAPABILITY AUDIT]
├─► aux renderer (AO/SSR/Hi-Z/sombras)                  [LIKELY]
├─► synchronización con GFX queue (DAG de dependencias) [LIKELY]
├─► BERRETA/ASY-01 (misma pregunta: overlap ACEs/8 CU; count UNKNOWN) [POTENTIAL DEPENDENCY]
├─► power cap 35 W (enmascara overlap)                  [OBSERVED confounder]
└─► FASE K (runner timeline)                            [LIKELY]
```

## 2. Relaciones PAC del ecosistema (estado de dependencia)

| Proyecto/fase existente | Ideas R-3 relacionadas | Tipo | Estado |
|---|---|---|---|
| **BERRETA (ASY-01)** | I-04 (piezas async), I-10 (aux renderer async) | comparte pregunta de overlap ACE/8 CUs | **POTENTIAL DEPENDENCY** — no fusionar; documentar cruce |
| **GHOST** | I-06 (predictive), también FASE G-M1/M5 | prefetch/localidad/working set | **POTENTIAL DEPENDENCY** — no fusionar; I-06 = variante predictiva |
| **FASE G (memoria)** | I-01, I-09 (L2-bypass), I-06 (working set) | modelo de memoria | **LIKELY** — I-01/I-09 son lecturas de G; I-06 usa su modelo |
| **RX-Compression-Engine** | I-02 (delta/tile), I-09 (compresión) | compressión de tráfico | **POTENTIAL DEPENDENCY** (data-driven: si I-02 muestra delta útil) |
| **FASE K (lab)** | todas (runner/telemetría) | sustrato de medición sin contadores | **LIKELY** para TODAS |
| **FASE M (contadores)** | I-01/I-09/I-04/I-08 | solo si futuro cambia autorización (NO HOY) | **UNKNOWN** |
| **FASE O (gestores)** | I-08 (governor) | comparación de control de calidad | **POTENTIAL DEPENDENCY** marginal |
| **FASE P (FG/upscaling)** | I-07 (optical flow FG) | misma taxonomía REAL/PERCIBIDO | **CONFIRMED** relación conceptual |
| **FASE Q (Mesa)** | I-01 (radeonsi TS/HTILE/DCC), I-06 | observaciones de código | **POTENTIAL** (I-01 corpus para Q; sin tocar Mesa) |
| **WORKLOAD-SINTETICO** | I-02, I-03, I-05, I-08, I-10 | harness/cargas (F2 estático; escenas controladoras) | **CONFIRMED** (varias ideas lo usan como sustrato) |
| **Orquestador** | todas | integración de ruta de medición | **POTENTIAL** — nada de R-3 entra sin pasar la ruta K |

## 3. Reglas de lectura

1. **POTENTIAL DEPENDENCY ≠ fusión:** la relación se documenta, no se fusiona (regla de la fase).
2. **Autorización:** ninguna dependencia confiere permiso de ejecución; contadores y writes siguen NO
   AUTORIZADOS (I-05 SQTT, I-08 actuación HW, I-04/I-07/I-10 cómputo = requieren gobernanza).
3. **Las cadenas de I-01/I-09/I-04/I-07 derivan en negativas estructurales** (L2-bypass, 32 SP/ROP,
   bandwidth/power): sus dependencias de *ejecución* son las que menos importan; sus dependencias de
   *evidencia negativa* son lectura de código + medición documental.
4. **UNKNOWN se reserva** para: PFOB/GO/PLL suport Vulkan (I-01), detección de TAA y presencia física
   de la capacidad ACE/queue (I-10), y estado de SQTT/RGP (I-05, `UNKNOWN`).
