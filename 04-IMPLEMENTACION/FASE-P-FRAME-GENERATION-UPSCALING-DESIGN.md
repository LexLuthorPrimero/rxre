# FASE P — FRAME GENERATION & UPSCALING RESEARCH — Documento de Diseño

> **Archivo:** `FASE-P-FRAME-GENERATION-UPSCALING-DESIGN.md`
> **Fase:** FASE R-2 — COMPLETE PROJECT DOCUMENTATION & ECOSYSTEM ARCHITECTURE (R-2.19)
> **Fecha:** 2026-09-22 — Modo SOLO DOCUMENTAL (DISEÑO; NO ejecutado)
> **Clasificación:** [DISEÑADO]. Separación estricta RENDIMIENTO REAL vs PERCIBIDO.
> **Estado global:** **PLANIFICADA**. No se instaló nada (lsfg-vk, FSR, etc. no instalados).

---

## 1. OBJETIVO

Diseñar la investigación de **técnicas de frame generation y upscaling** (lsfg-vk, FSR, upscaling,
Vulkan layers, inyección/interposición) sobre Polaris12/RX 550 para saber su viabilidad, costo de
latencia, calidad y compatibilidad, **sin** mezclar jamás sus resultados con los benchmarks reales del
Lab.

## 2. SEPARACIÓN RIGUROSA de conceptos

| Cantidad | Definición | Dónde se usa |
|---|---|---|
| **REAL FPS** | frames renderizados por la GPU realmente (win/benchmark nativo, sin capas) | ÚNICA métrica para Lab K/benchmarks oficiales |
| **GENERATED FRAMES (FG)** | frames sintetizados por una capa (lsfg/fsr-fg) entre frames reales | idea de "fluidez percibida"; NUNCA en Lab K |
| **PERCEIVED SMOOTHNESS** | experiencia subjetiva (frametime consistent, sin stutter) mejorada por FG/upscale | informe cualitativo si aplica |

**Regla: ninguna capa de FG/upscaling entra en los benchmarks del Lab K.** Los números de FG se reportan
como tal, nunca como rendimiento real.

## 3. TÉCNICAS A EVALUAR (inventario y viabilidad en Polaris12)

| Técnica | Tipo | ¿Soporta GFX8/Polaris12? | Riesgo/odep | Nota |
|---|---|---|---|---|
| **lsfg-vk** | layer de frame generation (Linux, via Vulkan layer) | parcial (FGM requiere HW moderno; lsfg puede no funcionar en GFX8 → VERIFICAR) | layer externo; instalación NO autorizada aún | Se evalúa si corre en RADV/GFX8 |
| **FSR 1/2/3 (scaling)** | upscaling temporal/espacial | FSR2/3 requieren jitter+blueprint, algos en shader; RADV puede correr con precision - hay que probar | no cambia GPU, agrega carga de shader | uptarge 2.0 = "render más bajo + upscale" |
| **FMF/Vulkan layer (interp.)** | interpolación de frames | requiere acceso a motion vectors; layer externo | riesgo de latencia | evaluar |
| **Gamescope/FSR nativas** | compositor+upscale | Gamescope ya referida en BUILD_SPEC (§32) como capa opcional | puede sumarse sin alterar Lab | documentar |

## 4. CÓMO SE MEDIRÍA (diseño)
- **Frame pacing interno:** medir FPS real del render (sin layer) y luego FPS percibido CON layer; reportar
  AMBOS por separado con labels inequívocos.
- **Latencia:** uso de timestamp queries/fence del render para estimar el retraso introducido (approx).
- **Uso del Lab:** NUNCA. Comparaciones en una **jaula aparte** (workload puede ser Superposition o el
  juego-E de FASE E), con telemetría igual K pero RESULTADOS etiquetados "real"/"perceived".

## 5. HIPÓTESIS (sin afirmar)
- H-P1: lsfg-vk / FSR-FG en GFX8 no funcionará (por requerimiento de HW moderno) o introducirá latencia
  mayor que el beneficio → no viable en nuestro GPU.
- H-P2: el upscaling (FSR) en resoluciones bajas + presentación a 1080 permite jugar a resoluciones de
  render más bajo con fluidez percibida similar, SIEMPRE que la CPU (i7-4790) no quede limitada por el
  pipeline de upscale.

## 6. CONFOUNDERS / RIESGOS
- La capa afecta composición/presentación (compositor Wayland) → comparar en ventana y fullscreen.
- Capas pueden modificar frametime del compositor (stutter) que no es el GPU.
- Riesgo: dañar la instalación → instalación/uso SOLO bajo autorización; capas se habilitan por
  variable de entorno por-proceso (nada permanente).

## 7. CONCLUSIÓN DEL DISEÑO
FASE P queda **DISEÑADA** (separación REAL/PERCIBIDO, inventario, método de medición, hipótesis,
confounders) y **PENDIENTE**. **La tecnología de FG/upscaling NO se instala ni se usa en los benchmarks
reales del Lab K.** Cualquier resultado futuro se etiquetará explícitamente como "PERCIBIDO" y nunca como
mejora de throughput real.