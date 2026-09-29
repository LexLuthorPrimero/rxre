# PRECHECK REPORT — EXP-F1-A Jitter Observability (FASE R-4C)

**Fecha:** 2026-09-22
**Estado del ítem:** PRECHECK COMPLETE / AWAITING AUTHORIZATION
**Mandato seguido:** instrucciones §0–§20 de FASE R-4C.

---

## A. Documentación revisada

1. `01-AUDITORIA/FASE-R3-1-FUSION-ARCHITECTURE-AUDIT/FUSION-01-JITTER-DUAL-CONSUMER.md` — motores codifican jitter en matrices/push constants; sin extensión Vulkan de jitter; capa PARTIALLY VERIFIED; "jitter = MV" CONTRADICTED en R-3.1.
2. `04-IMPLEMENTACION/projects/JITTER-REPROJECTION/EXPERIMENT-DESIGN.md` — hipótesis H2a-c (jitter gen/obs separadas).
3. `04-IMPLEMENTACION/projects/JITTER-REPROJECTION/PRIOR-ART.md` — surveys TAA (Yang/Liu/Salvi, Playdead), TXAA 3.0, ATAA, Hanika.
4. `04-IMPLEMENTACION/projects/BERRETA/BERRETA-DESIGN.md` — fuera de integración (referencia).
5. `04-IMPLEMENTACION/FASE-P-FRAME-GENERATION-UPSCALING-DESIGN.md` — referencias a lsfg-vk/FMF (capas).
6. `MASTER-RESEARCH-STATUS.md` v2.8 (base).

## B. Prior art relevante

- FSR2/GPUOpen (primario): jitter Halton[2,3] píxel-unit; `jitterX=2·j/9; jitterY=-2·j/h`; inyección por matriz de proyección; prohibición de (0,0); MV sin jitter.
- Khronos LoaderLayerInterface.md (primario): capas interceptan funciones host vía dispatch tables; pueden insertar llamadas; ver parámetros host.
- `vkCmdPushConstants` man page (primario): `pValues` host copiado en recording.
- VIL / RenderDoc: precedentes de introspección vía capa (ESTIMATED).
- Detalle y referencias en `PRIOR-ART.md` (Anexo de este PRECHECK).

## C. APIs Vulkan seleccionadas

- `vkCreateInstance` (activamos capa explícita por nombre).
- `vkCmdPushConstants` (NIVEL A: canal directo de jitter).
- `vkCreateGraphicsPipelines` + `vkCreatePipelineLayout` (layouts/descriptores; NIVEL B).
- `vkCreateBuffer`, `vkAllocateMemory`, `vkBindBufferMemory`, `vkMapMemory`, `vkUpdateDescriptorSets`, `vkCmdBindDescriptorSets` (UBO per-frame host-visible; NIVEL B).
- `vkCmdBeginRenderPass`/draw/`vkQueueSubmit`/`vkQueuePresentKHR` (ciclo de frames).

## D. Mecanismo de observación propuesto

- Capa `VK_LAYER_ITERATIVERO_jitter_observer` (cargada por `VK_LAYER_PATH` local, nunca sistema).
- NIVEL A: lee `pValues` de `vkCmdPushConstants` en el instante de recording.
- NIVEL B: rastrea alloc+bind (handle→memory), valida HOST_VISIBLE, mapea, y **reconstruye** el jitter resolviendo `Δ = M_base⁻¹·M_jit` → `jx_px = tx·W/2`, `jy_px = −ty·H/2`.

## E. Limitaciones conocidas

1. Sin memoria host-visible el contenido de buffers NO es observable (DEVICE_LOCAL prohibido leer) — limita generalización a engines reales con UBO device-local.
2. Push constants solo legibles en el momento del `vkCmdPushConstants` (CB opaco tras recording).
3. No se inspeccionan CBs internos ni el estado de GPU.
4. Capa solo funciona si el loader respeta `VK_LAYER_PATH` (normal user, sin elevación → sí; verificado en PRIOR-ART §8).

## F. Secuencia de jitter propuesta

Ver EXPERIMENT-DESIGN §5: bloques de magnitudes {0.5, 0.25, 0.125, 0.0625, 0.01 px} × 8 direcciones (±, x/y, x±y) + bloque Halton[2,3] (no (0,0)) + zona deterministic pseudo-random; 256+64 frames/corrida; GT en canal independiente.

## G. Criterios de éxito

PASS / PARTIAL / FAIL / BLOCKED — definidos en EXPERIMENT-DESIGN §8 (NIVEL B reconstrucción MAE<0.01 px como condición central; PROVISIONAL TARGET justificado).

## H. Archivos a crear (tras autorización)

```
projects/...  → NO toca
harness/
harness/jittergen.c        (generador GT, secuencia)
harness/app_vulkan.c       (inyección A/B, VP/matrices)
harness/glsl/*.vert|*.frag
harness/layer/layer.c      (observadora)
harness/layer/VkLayer_iterativero_jitter_observer.json
harness/scripts/compare.py
results/*.json   logs/*.log
```
(En PRECHECK: solo los 4 MD de esta carpeta, ya creados.)

## I. Comandos planificados (ninguno ejecutado)

- Build: `glslangValidator -V`, `cmake -G Ninja -S harness -B harness/build`, `ninja -C harness/build`.
- Correr (por nivel y driver):
  `VK_ICD_FILENAMES=.../radeon_icd.x86_64.json VK_LAYER_PATH=$PWD/harness/layer ./harness/build/jitter_harness --level A --out results/...`
  Ídem para `lvp_icd.x86_64.json` (lavapipe) y opcionalmente `intel_icd.*.json` (ANV).
- Análisis: `python3 harness/scripts/compare.py gt/... recovered/... results/...`

## J. Riesgos

1. `VK_LAYER_PATH` ignorado en entorno — detección temprana: verificar en logs de la capa.
2. Memoria no host-visible en un driver → baja a FAIL/limitación (se documenta).
3. Orden de matrices (`M_base⁻¹·M_jit` vs `M_jit·M_base⁻¹`) — coherente con la definición FSR2; riesgo bajo, verificable por delta nula cuando jitter=(0) (prohibido) y por patrón conocido.
4. Latencia de lectura de UBO (map) tras submit → se sincroniza por `vkQueueWaitIdle` por frame si fuese necesario (solo lectura, sin impacto en driver real).
5. Variabilidad de FP32 — análisis muestra margen suficiente (PRIOR-ART §4).

## K. Por qué NO modifica el sistema

- Sin installs (nada en `/usr/share`, `/usr/local`, `XDG_DATA_HOME` del sistema).
- Sin cambios en Mesa/RADV/radeonsi/kernel/firmware/VBIOS/BIOS/PowerPlay/DPM/runtime-PM/rx550-torneo/registros/hw-counters.
- ICDs ya presentes; la capa vive en `harness/` local, activada solo por variable de entorno.
- No se mide rendimiento de la real ni se presenta como benchmark.
- Toda lectura de GPU se hace vía el propio Vulkan (blitt/copy en framebuffer software) — sin sysfs/debugfs/sudo.

---

## Checklist QA R-4C (§19) — verificación

| # | Ítem | Estado |
|---|---|---|
| 1 | Documentación del proyecto revisada | ✅ (EXP-DESIGN, FUSION-01, PRIOR-ART J,R, FASE-P) |
| 2 | Investigación externa cuando UNKNOWN | ✅ (Khronos layer spec, man page, GPUOpen FSR2; fallback webfetch) |
| 3 | API de capas Vulkan revisada | ✅ (LoaderLayerInterface.md) |
| 4 | Observabilidad de capas verificada (host, dispatch, insert) | ✅ |
| 5 | No asumir acceso a buffers GPU arbitrarios | ✅ (limitación documentada E1) |
| 6 | Jitter ≠ motion vector establecido | ✅ (PRIOR-ART §6, diseño MV fijo) |
| 7 | Ground truth independiente (canal separado) | ✅ (§4 diseño) |
| 8 | Secuencia no trivial (signos, ejes, magnitudes, repetitiva, pseudo-random) | ✅ (§5 diseño) |
| 9 | Métricas de error definidas (MAE, max, RMS, correctos/incorrectos) | ✅ (§7 diseño) |
| 10 | Criterios PASS/PARTIAL/FAIL/BLOCKED definidos | ✅ (§8) |
| 11 | Target MAE<0.01px justificado (PROVISIONAL) | ✅ (PRIOR-ART §4) |
| 12 | Sin niveles/representaciones de 0 irradia ni confusiones | ✅ |
| 13 | Sin integración BERRETA/Ghost/optical flow/frame gen/tile | ✅ (EXPERIMENT-DESIGN §10) |
| 14 | Sin benchmark de rendimiento de RX550 | ✅ (§10 + J) |
| 15 | Sin modificación Mesa/kernel/GPU/sysfs | ✅ (§K) |
| 16 | Sin escribir fuera de `03-EXPERIMENTOS/FASE-R4C-JITTER-OBSERVABILITY/`+harness local tras autorización | ✅ |
| 17 | No se creó trabajo ejecutable en PRECHECK | ✅ (solo 4 MD) |
| 18 | Próximo paso: requerimiento de autorización explícita | ⏸️ (esta sección) |
| 19 | Estado master refleja "PRECHECK COMPLETE / AWAITING AUTHORIZATION" | ✅ (v2.9 de MASTER-RESEARCH-STATUS) |

---

## Conclusión

El PRECHECK es **viable y completo**. NIVEL A: VERIFIED por mecánica de capa + `vkCmdPushConstants`. NIVEL B: DERIVED (host-visible + reconstrucción algebraica FSR-consistente). Sin ejecución de nada. **Now the harness creation/compilation/execution requires explicit authorization.**
