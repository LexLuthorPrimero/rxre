# PRE-FLIGHT / CALIBRACIÓN — EXP-F4-A (FASE R-4B) — REGISTRO

**Fecha:** 2026-09-22 · **Clasificación:** PRE-FLIGHT / CALIBRACIÓN — **NO es dato experimental de R-4B**

## 1. Propósito

Documentar la **calibración del harness** realizada ANTES de la corrida experimental válida
(sesiones 1 y 2 del protocolo v2.1). Ningún valor de esta hoja ingresa a `analyze.py` ni a las
decisiones T/s*/GATEs/R1–R7/F1–F6 del protocolo.

## 2. Cronología

1. **Build** del harness Diseño B (`harness/app_vulkan.c` + shaders → SPIR-V via glslangValidator,
   ninja). OK.
2. **Smoke test inicial** (logs descartados en `/tmp/opencode/f4a-smoke/` — **PERDIDO / NO VERIFICABLE**; fuera de `results/`):
   `governor_harness --mode fixed --scale 1.00 --warm 2 --duration 4`.
   → **P99(1.00) ≈ 3.8 ms** (n=1057).
3. **El primer workload NO superó el GATE de calibración** `P99(1.00) ∈ [5,200] ms` (3.8 < 5).
   La curva habría sido demasiado plana/ligera para ser gobernable y habría disparado parada D en Fase 1.
4. **Recalibración del fragment shader** (`harness/glsl/triangle.frag`), ÚNICA modificación de la
   pila de calibración:
   - taps de textura: 4 → **8** (2 por textura, todas 4096² RGBA8; camino de caché distinto, > L2)
   - cadena FMA: ~24 → **~90** (ALU/SCLK alta; salida dependiente de los 8 samples evita dead-code)
   - **INTACTO (fijado por protocolo/DESIGN-GRAPHICS §Diseño B):** W×H=1920×1080, N=4 capas
     (eje 1–8 solo para disturbio), 4 texturas 4096², blending aditivo, viewport+scissor por
     render-scale, push constants scale_w/scale_h/layer/seed, salida de alta varianza (derrota DCC).
5. **Smoke test post-recalibración** (logs descartados en `/tmp/opencode/f4a-s/` — **PERDIDO / NO VERIFICABLE**; duración 4 s por
   escala, 1 corrida/escala): curva **preliminar** de calibración

   | s | P99 [ms] preliminar |
   |---|---|
   | 1.00 | ≈ 11.43 |
   | 0.87 | ≈ 9.32 |
   | 0.75 | ≈ 7.02 |
   | 0.62 | ≈ 4.89 |
   | 0.50 | ≈ 2.85 |

   → monótona no creciente, reducciones 18–42 % por paso, queda holgadamente dentro de los GATEs.
   **Valores PRELIMINARES** (una corrida/escala, 4 s), NO valores oficiales.

## 3. Estatus de los valores citados

- **`P99(1.00)=11.4 ms`** y la curva **`11.4 → 2.9 ms`**: **PRELIMINARES** (calibración).
- Los valores **oficiales** serán los de Fase 1 open-loop (mediana de 3 bloques por escala, 20 s
  medidos cada uno) de cada sesión, calculados por `analyze.py phase1`.

## 4. Regla de no-ajuste

- T y s* se calculan **exclusivamente** de Fase 1 open-loop de cada sesión (nunca de calibración)
  y se **congelan en `fase1/manifest.json` con SHA256 antes de la primera corrida GOV** de esa
  sesión (`analyze.py phase1` freeze).
- Si durante la ejecución apareciera cualquier necesidad de cambiar workload, thresholds o
  protocolo: **NO se improvisa**; se detiene y se reporta.
