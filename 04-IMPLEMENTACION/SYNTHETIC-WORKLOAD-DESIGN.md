# SYNTHETIC-WORKLOAD-DESIGN — Diseño del Workforce Sintético Polaris12

> **Archivo:** `SYNTHETIC-WORKLOAD-DESIGN.md`
> **Fase:** FASE R-2 — COMPLETE PROJECT DOCUMENTATION & ECOSYSTEM ARCHITECTURE (R-2.9)
> **Fecha:** 2026-09-22 — Modo SOLO DOCUMENTAL (DISEÑO; NO implementado)
> **Clasificación:** [DISEÑADO]. Extiende el prototipo existente `experiments/WORKLOAD-SINTETICO/`
> (Vulkan COMPUTE `main` + diseño gráfico `DESIGN-GRAPHICS.md`). **Ningún código se escribió ni se
> ejecutó en esta fase.**
> **Estado:** work-in-progress de diseño; el prototipo actual permanece CONGELADO (sin cambios).

---

## 1. OBJETIVO
Diseñar el **workload sintético modular** que permita aislar, en Polaris12 (RX 550), cada subsistema de
interés (geometría, sombreado, memoria, fetch, VRAM, compute, async, potencia) con cargas
deterministas y telemetría reproducible, para servir de **baseline única** a FASE F (GEO), FASE G (MEM)
y a la comparación con Superposition (OpenGL) y un futuro juego real (FASE E).

## 2. ARQUITECTURA
- **Base existente (reusada, NO modificada hoy):** `WORKLOAD-SINTETICO/main` (Vulkan COMPUTE + SSBO),
  `main-graphics` (workload gráfico) y la selección estricta de GPU
  (`vendor=0x1002 device=0x699F`, `MESA_VK_DEVICE_SELECT=1002:699f`).
- **Diseño objetivo:** un **launcher Orquestador-Ligero** (`workload_launcher`) que reciba modo +
  parámetros y arme el shader/pipeline correspondiente; cada modo = programa/shader independiente,
  sin acoplar entre sí. Los modos se declaran como **modos de experimento**, no como productos.
- **Inyección de parámetros:** push constants (`iterations`, `stride`, `seed` ya existentes) + clamp de
  duración (`--duration`).

## 3. INPUTS
- GPU (fija auto-detectada o `--gpu 1002:699f`)
- Modo (`geometry|shading|memory|fetch|vram|compute|async|power`)
- Parámetros propios del modo (ver §5)
- Duración (`--duration`, por defecto 30 s), warm-up, repeticiones
- Semilla (`--seed`), determinismo launcher

## 4. PARAMETRIZACIÓN
Tabla de parámetros comunes (heredados): workgroups/iterations/stride/seed/vram; duración; warm-up;
resolución (modos gráficos); layers; MSAA; texturas (4×4096²); seeds `0x13579BDF`/`0x2468ACEO`.

## 5. MODOS (cada modo = hipótesis de subsistema)

| Modo | Qué estresa | Métricas objetivo | Estado diseño |
|---|---|---|---|
| **GEOMETRY** | VS pesado + IA/VGT/raster (GEO-01/02) | FPS, frametime, vertex_busy, VS invocations (pipeline stats), rasterizer_busy | Diseñado (depende `main-graphics` + pipeline stats) |
| **SHADING** | FS/ALU/VALU (conditionals/fma/loops) | FPS, `shader_busy`, VALU busy (si medible), power | Diseñado (reusa modos E-03/ES-01 B-ejes) |
| **MEMORY** | tráfico VRAM/L2 cuantificado (G-M4) | `mem_busy`, frametime, power | Diseñado (G-M4) |
| **FETCH** | fetch-latency (F2), ilustra auto-pacing | frametime/fetch ratio, mem_busy | **Ya validado** (F2, ES-01) |
| **VRAM** | presión VRAM/eviction (G-M3= MEM-01) | FPS cliff, `mem_info_vram_used`, page faults | Diseñado (BAJA prioridad, riesgo OOM) |
| **COMPUTE** | compute puro (ACE/graphics queue) | throughput, power | Basado en `main` (ya funciona) |
| **ASYNC** | overlap graphics+compute (ASY-01) | FPS graphics, compute throughput | Diseñado (colas separadas + timeline semaphores) |
| **POWER** | régimen de potencia (cap/perfiles) | poder iterator, pwr, temp | Diseñado (I-2/I-3, requiere autorización de writes) |

## 6. VARIABLES CONTROLABLES (por modo; todo lo OTRAS se declara constante)
Ver §4 y fichas FASE F/G. Regla: en cada corrida se declara qué cambia y qué queda fijo (plantilla de
medida de la Matriz J).

## 7. TELEMETRÍA
- **sysfs amdgpu** (hilo dedicado): gpu_busy, mem_busy, power1_average/input (µW), temp, pwm,
  pp_dpm_state, pp_dpm_sclk/mclk (niveles activos), mem_info_vram/gtt_used.
- **Frame-level:** log CSV con FPS y frametime p50/p99 (MangoHud o timing propio).
- **Pipeline stats (opcional):** VS/FS invocations vía `VkQueryPool` (GEO-01/02/07).
- **Timestamp queries** para latencia (G-M2/MEM-02).
- Frecuencia de muestreo: ver plantilla FASE E (§5.4) — 4-10 Hz sysfs; determinista por label.

## 8. MÉTRICAS
power_avg_full / power_avg_steady / power_max; FPS; frametime p50/p99; SCLK/MCLK distribución; busy%  ;
mem_busy%; `mem_info_*`; detección de faults. **ETIQUETAR SIEMPRE** definiciones idénticas a
METRICS-DEFINITIONS (AUDIT-001): "NOT DIRECTLY COMPARABLE" si la ventana/definición cambia.

## 9. WARM-UP / REPETICIONES
- Warm-up 5 s (mayor si el workload tarda en estabilizarse térmicamente; registro de temp_inicial).
- Repeticiones N≥5 pareadas por celda (bloques A/B intercalados) siguiendo el diseño de FASE D (6/6 runs
  válidos A/B×3) y M1 (10 runs pareados).

## 10. VALIDACIÓN
Cada corrida = `manifest` (parámetros) + `pre_flight`/`post_flight` (state sysfs) + `journal` +
`stderr/stdout`. Clasificación VALID/INVALID/OUTLIER/REPEATABLE (criterios FASE E §5.6) y firma de
**artefactos hasheados** (sha256) como en M1.

## 11. DETERMINISMO
Semillas fijas, shaders inmutables (hash del shader en el manifest), MISMA versión de la GPU/última
condición (reset en `state`), orden de corridas intercalado; en cada corrida se registra el
**state hash** del entorno (DPM/cap) para detectar deriva.

## 12. BASELINE
- **Baseline oficial:** E-03 corregida (Diseño B, `runs/exploratorio-03-corrected/`) — 13.4 W full /
  15.75 W steady, MCLK 1500 activo, 0 faults. **Se cita, NO se re-ejecuta** (código congelado).
- Para cada modo nuevo, se crea su propia baseline y se compara contra E-03 con **etiqueta
  NOT DIRECTLY COMPARABLE** cuando la definición varíe.

## 13. FAILURE MODES
- device lost / VK_ERROR_DEVICE_LOST → capturar en journal, marcar INVALID, guardar dmesg.
- OOM (G-M3) → abort a tiempo (presupuesto de memoria), device lost posible → requiere reintento de
  sesión autorizada.
- Timeout de fence (frametime extremo) → usar `--duration` con backup timeout y abort limpio.
- DPM/cap no restaurado → detección en post_flight (estado != esperado) → bloquear siguiente corrida.

## 14. INTEGRACIÓN con rx550-torneo y K/L
- **rx550-torneo:** la herramienta NO ejecuta el workload; el workload define su propio runner. La
  integración es de **estado**: cada corrida registra el régimen actual de rx550-torneo
  (perfil/cap/state) para interpretación. Sin acoplamiento de código.
- **FASE K (Lab):** el launcher es el candidato a **runner estándar** del Lab (metadata/validation/
  hashing); se diseña para que K lo adopte sin reemplazar nada del congelado.
- **FASE L (Tuner):** los modos POWER / MCLK probing se ejecutan SOLO cuando L autoriza writes con
  snapshot+restore.

## 15. Conclusión del diseño
El workload sintético está **DISEÑADO** como framework modular de 8 modos sobre el prototipo existente
(CONGELADO). Nada se escribió ni ejecutó en R-2. Los modos **FETCH/COMPUTE** ya tienen evidencia real
(ES-01/F2/E-03); los demás requieren solo la implementación del launcher (futura fase de código, no
autorizada) y los gates de FASE J.