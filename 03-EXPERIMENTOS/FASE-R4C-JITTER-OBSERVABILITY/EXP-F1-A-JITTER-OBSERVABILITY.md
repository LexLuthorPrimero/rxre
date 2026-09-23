# EXP-F1-A — Jitter Observability — EXPERIMENT DESIGN

**FASE:** R-4C (PRECHECK)
**Estado:** PRECHECK COMPLETE / AWAITING AUTHORIZATION
**Fecha:** 2026-09-22
**Autor citado:** MASTER-RESEARCH-STATUS v2.9 (pendiente: actualizar al cerrar)

> Objetivo del PRECHECK: **entregar el diseño y el plan de ejecución** de un harness Vulkan que (a) genere una secuencia de jitter TAA subpíxel conocida y (b) establezca si una capa externa puede RECUPERAR esos offsets con la precisión requerida. Este documento es el diseño; su ejecución (crear/compilar/correr) **requiere autorización explícita**.

---

## 1. Pregunta del experimento

**Q1 (NIVEL A):** ¿Puede una capa Vulkan externa observar, con `MAE < 0.01 px` (PROVISIONAL TARGET, ver §3), una secuencia de jitter entregada por push constants en canal dedicado?
**Q2 (NIVEL B):** ¿Puede una capa Vulkan externa RECONSTRUIR el jitter (no leer el campo "jitter" rotulado), trabajando sobre la representación realista (matriz de proyección con jitter inyectado + estructura tipo per-frame), con `MAE < 0.01 px`?
**Q3 (transversal):** ¿La observación es estable entre drivers (RADV real / lavapipe software / ANV opcional)?

## 2. Terminología

| Término | Definición |
|---|---|
| GENERACIÓN | El harness produce la secuencia jitter de ground-truth (GT) y la inyecta por Vulkan (canal A o B). |
| OBSERVACIÓN | La capa INTERCEPTA los llamados host y RECONSTRUYE la secuencia. |
| RECONSTRUCCIÓN | Proceso por el cual la capa obtiene offsets a partir de la representación (no del campo rotulado). |
| Referencia (GT) | Canal separado (archivo JSON) escrito por el harness con `frame_id, jx, jy`. |
| Recovery | Canal de salida de la capa (JSON) con `frame_id, rjx, rjy`. |

## 3. Precisión requerida (PROVISIONAL TARGET)

- `MAE < 0.01 px` sobre la secuencia completa (horizontal y vertical eliminados de métrica, ver §7).
- Justificación (PRIOR-ART §4): sin estándar previo publicado; pero análisis FP32 para Nivel B (matriz) da margen ~×50..×500 sobre el piso FP32 para W=1920. Se mantiene como **PROVISIONAL TARGET**: si los resultados lo contradicen con evidencia (p.ej. fragilidad de reconstrucción de delta de matrices), se ajustará documentando la razón.
- Criterios adicionales de soporte: (a) correlación de fase de secuencia recuperada vs GT ≥ 0.999; (b) 100% de frames clasificados correctos bajo la tolerancia.

## 4. Separación GENERACIÓN vs OBSERVACIÓN

- **GENERADOR** = harness (aplicación Vulkan). Calcula secuencia, escribe `gt/<run>.json` (canal de referencia, independiente).
- **OBSERVADOR** = capa `VK_LAYER_ITERATIVERO_jitter_observer` (nombres estándar: prefijo `VK_LAYER_`). Lee solo lo que llega por Vulkan. Escribe `recovered/<run>.json`.
- Los dos canales NUNCA se comunican por archivos ni variables compartidas: solo por los datos que la capa ve en la cadena de dispatch.
- El comparador (post-procesado) yune por `frame_id`.

## 5. Secuencia de jitter (GENERACIÓN)

> Mandatos R-4C §4: positivos/negativos, solo X, solo Y, X+Y, magnitudes pequeñas, próxima al límite subpíxel, repetitiva, deterministic pseudo-random.

Diseño (combina requisitos + práctica FSR2/TAA, PRIOR-ART §5):

1. **Prototipos de magnitud (bloque de 8 direcciones repetido a lo largo de la secuencia):**
   - `m = 0.5px` (típico TAA/MEGA)
   - `m = 0.25px`
   - `m = 0.125px`
   - `m = 0.0625px` (límite subpíxel)
   - `m = 0.01px` (target/aumento del límite)
2. **Direcciones (por cada magnitud):**
   - `(+m, 0)`, `(-m, 0)`, `(0, +m)`, `(0, -m)`, `(+m, +m)`, `(-m, +m)`, `(+m, -m)`, `(-m, -m)`
3. **Bloques de patrón bajo-discrepancia** (referencia industrial, FSR2 Halton[2,3] en píxel-unit):
   - 8 subpuntos Halton[2,3] ∈ [-0.5,0.5] px, con **prohibición explícita de (0,0)** (regla FSR2); se repite 2×.
4. **Secuencia repetitiva determinista de 40 frames** = 5 magnitudes × 8 direcciones; se repite 6 veces → **240 frames**, más un preludio de 4 frames (recalentamiento/descarte si el driver quiebra la cadena) y **16 frames Halton** → **256 frames observables** del bloque base.
5. **Sección pseudo-random determinista** (xorshift, seed fija): 64 frames extra para robustez a secuencia no ultra-regulada.

Total planificado: 240 + 16 + 64 = **320 frames observables** por corrida, + preludio de 4 (excluidos de métricas); 2 corridas por nivel/driver (estabilidad).

> **Regla anti-contaminación:** la secuencia se calcula ANTES de entrar a Vulkan; se escribe GT-archivo. La capa ve SOLO lo inyectado. La GT no se pasa a la capa.

## 6. Niveles de observabilidad

### NIVEL A — Directo (canal dedicado)

- Harness llama `vkCmdPushConstants(..., float2 pero = publica jitter en un rango push constante definido)`.
- La capa intercepta `vkCmdPushConstants` y lee `pValues` (host, en tiempo de recording — VERIFIED vía man page).
- Precaución de diseño: push constants se copian al CB durante recording; al terminar de grabar el CB la capa referenciaría memoria reutilizable → la capa **consume los valores en el instante de la llamada** (no difiere la lectura). Especifica exactamente esta semántica.

### NIVEL B — Indirecto/realista (reconstrucción)

- El harness inyecta el jitter **en la matriz de proyección de cámara** (exactamente el mecanismo FSR2: `M_jit = translate(identity, jx_ndc, jy_ndc, 0) · M_base`), donde `jx_ndc = 2·jx_px/W`, `jy_ndc = -2·jy_px/H`) y pasa esa matriz en un uniform host-visible (UBO tipo "per-frame").
- **NO** se rotula ningún campo "jitter": la matriz va como `mat4 projectionMatrix` (doble de los datos: también `mat4 viewMatrix` para contextualizar).
- La capa:
  1. Intercepta `vkCreateGraphicsPipelines`/layout para conocer el layout del descriptor y los slots; intercepta `vkUpdateDescriptorSets`/`vkCmdBindDescriptorSets` para saber qué UBO se vincula.
  2. Rastrea `vkAllocateMemory`+`vkBindBufferMemory` (handle→memory) y valida que la memoria sea `HOST_VISIBLE` (requisito, VERIFIED PRIOR-ART §2).
  3. `vkMapMemory` por rango del UBO y **reconstruye** el jitter resolviendo `M_jit` contra la base:
     - Leer `M_base` (provisto a la capa vía segundo slot "camera model" → la capa computa `Δ = M_base⁻¹ · M_jit` y extrae `tx,ty` del renglón de traslación).
     - `jx_px = tx·W/2`, `jy_px = -ty·H/2`.
  4. Recupera por frame y escribe `recovered/NIVEL-B.json`.

- Si el harness NO cooperara (buffer DEVICE_LOCAL, sin map) la observación del contenido es imposible → documentado en PRECHECK (limitación), pero aquí el harness es el "engine de prueba" que produce exactamente la representación realista de un engine real (matriz con jitter), para validar que la RECONSTRUCCIÓN algebraica funciona.

### Estructura del harness (contaminación controlada)

```
harness/
  jittergen.c        (secuencia + GT writer)
  app_vulkan.c       (GENERACIÓN: inyecta por A o B; un solo VP per frame)
  glsl/              (shaders; MV fijo; jitter NO en MV — PRIOR-ART §6)
  layer/             (VK_LAYER_ITERATIVERO_jitter_observer: manifest+lib)
  scripts/compare.py (une GT+recovered; métricas)
```

## 7. Métricas de error

- `error_x = rj_x − gt_x`; `error_y = rj_y − gt_y`.
- `MAE_X`, `MAE_Y`, `MAE_total = media(|error_total euclidiano|)`.
- `max_error` por eje; `RMS` por eje.
- `frames correctos` = dentro de los `0.01 px` de tolerancia; `frames incorrectos` = fuera (se reporta sin ocultar outliers).
- Correlación de fase de la secuencia recuperada vs GT (Pearson sobre la serie temporal de un eje).
- Resultado vía archivo `results/<run>.json` (solo tras autorización).

## 8. Criterios de éxito

- **PASS:** NIVEL B (reconstrucción, NO lectura de campo rotulado) consigue MAE<0.01 px en la corrida canónica; NIVEL A idem; preludio/descartes excluidos documentadamente.
- **PARTIAL:** NIVEL A pasa; NIVEL B falla en reconstrucción pero pasa leyendo el offset plano del UBO (sin denominarlo jitter); o estable en un solo driver.
- **FAIL:** la capa no recupera (MAE>target en condiciones definidas).
- **BLOCKED:** por API/loader/driver (p.ej. la cadena de la capa no alcanza; `VK_LAYER_PATH` ignorado de forma verificada).

## 9. Ejecución planificada (NO ejecutar sin autorización)

Compilación y corrida **local y aislado** en `harness/` (nada al sistema, nada a GPU-driver/kernel):

1. `glslangValidator` → SPIR-V; `gcc`+`cmake`/`ninja` → binarios (todo en `harness/build`).
2. Corrida NIVEL A y NIVEL B, cada una en 2 drivers:
   - **RADV (RX 550 real)** → `VK_ICD_FILENAMES=.../radeon_icd.x86_64.json`
   - **lavapipe (software)** → `lvp_icd.x86_64.json`
   - (opcional ANV → `intel_icd.*.json`)
   - Capa: `VK_LAYER_PATH=$(pwd)/harness/layer` (sin elevación, se respeta — PRIOR-ART §8).
3. `python3 scripts/compare.py` → métricas.
4. Interpretación → tablas VERIFIED/DERIVED/ESTIMATED/UNKNOWN/REQUIRES FUTURE EXPERIMENT.

## 10. ¡Límites/no haré!

- No modifico Mesa/RADV/radeonsi/kernel/firmware/VBIOS/BIOS/PowerPlay/DPM/runtime-PM/rx550-torneo/GPU registers/HW counters.
- No benchmarks de rendimiento de la RX 550; el harness solo genera una secuencia de frames con un quad/fullscreen pass; nada mide FPS/bandwidth en la real.
- No se presenta como benchmark GPU.
- No integrar BERRETA, Ghost Cache, optical flow, frame generation, tile reuse, governor.
- No concluir "jitter = motion vector".
- No instalar nada en `/usr/share`, `/usr/local`, etc. Los ICDs ya existen; la capa vive en `harness/`.

## 11. Productos tras autorización (fuera de alcance del PRECHECK)

`harness/`, `results/`, `logs/`, scripts de comparación, reporte EXP-F1-A final con estados y criterios PASS/PARTIAL/FAIL/BLOCKED.

---

**Valoración del PRECHECK:** viabilidad VERIFIED para NIVEL A (mecánica de capa + `vkCmdPushConstants`), DERIVED para NIVEL B (memoria host-visible + reconstrucción algebraica FSR-consistente). Las únicas incógnitas reales (estabilidad por driver, datos concretos) son exactamente lo que el experimento medirá.