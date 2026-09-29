# HYPOTHESIS REGISTER — H1–H12

**STATUS:** DRAFT/CONFLICT — registro textual provisional
**LAST AUDITED:** 2026-09-24
**PURPOSE:** registro textual provisional para una futura vista visual `02-HIPOTESIS-H1-H12.md`.

Este archivo no es un diagrama, no autoriza experimentos y no convierte una hipótesis en un resultado. Las etiquetas `REQUIRES EXPERIMENT` y `REQUIRES CAPABILITY AUDIT` son estados de planificación, no resultados.

> **Reconciliación 2026-09-24:** R-4B/D6, W_SMU, MCLK, bandwidth y catálogo GFX8
> se interpretan según las fuentes canónicas corregidas. El registro permanece
> `DRAFT/CONFLICT`; H12 sigue bloqueado para una conclusión causal hasta
> completar la capacidad WSI/present timing que falta.
>
> **Addenda H12-2 (2026-09-24):** la auditoría de r1/r2/r3 y la fuente primaria
> `01-AUDITORIA/FASE-H12-2-WSI-DOCUMENTATION/H12-2-XDG-SHELL-VULKAN-WSI-EVIDENCE.md`
> confirman `xdg_toplevel.state=4 = activated` y refutan la regla absoluta
> «configure post-present = conflicto». La capa de capacidad WSI queda
> `PARTIALLY CONFIRMED`; la causalidad H12 (GPU completion vs VSync/WSI) sigue
> `UNKNOWN`. No se autoriza una nueva ejecución.

## Alcance de los identificadores

Los identificadores `H1`–`H12` de este registro son preguntas de investigación de nivel proyecto, pendientes de una vista visual futura. No reemplazan los identificadores locales `H1`, `H2`, etc. que aparecen en documentos de fases, proyectos o auditorías con otros significados. Si una fuente usa un ID local, debe citarse con su documento y alcance; no debe fusionarse automáticamente con este registro.

Las preguntas siguientes son investigación propuesta derivada de la evidencia y del diseño existentes. Ninguna tiene un resultado de causalidad atribuido por este archivo. Una vez armonizado, este registro será la fuente textual de `02-HIPOTESIS-H1-H12.md`.

## Reglas de evidencia

- `PARTIALLY_VERIFIED`: existe evidencia local o externa parcial, pero no causalidad completa.
- `REQUIRES EXPERIMENT`: falta una intervención/medición local.
- `REQUIRES CAPABILITY AUDIT`: falta enumeración o confirmación de capacidad local.
- `UNKNOWN`: no existe evidencia suficiente en el estado actual.
- Un resultado `INCONCLUSIVE` no se transforma en `VALIDATED` ni `SUPPORTED`.
- `power1_input` se expresa como `W_SMU`/potencia estimada por sensor SMU; no como vatímetro independiente.
- `mem_busy_percent` es proxy; no es bandwidth.
- MCLK se trata como MCLK reportada; no como DRAM data rate efectiva.
- La compatibilidad histórica de una herramienta no implica soporte runtime actual.
- Para el addenda H12-2, los estados de cierre se expresan únicamente como
  `CONFIRMED`, `REFUTED`, `PARTIALLY CONFIRMED`, `CONFLICT` o `UNKNOWN`; las
  etiquetas de planificación históricas no se convierten en resultados.

## Fuentes de referencia

| IDs | Evidencia o diseño de partida |
|---|---|
| H1, H12 | `03-EXPERIMENTOS/M1-cap-35-30/RESULTADOS-M1.md`; `04-IMPLEMENTACION/FASE-K-PERFORMANCE-LAB-DESIGN.md` |
| H2 | `03-EXPERIMENTOS/FASE-R4B-GOVERNOR/EXP-F4-A-RESULTADOS-v2.3.md`; `03-EXPERIMENTOS/FASE-R4B-THERMAL-TEST/RESULTADOS-TEST-TERMICO.md` |
| H3 | `03-EXPERIMENTOS/M1-cap-35-30/RESULTADOS-M1.md`; `04-IMPLEMENTACION/FASE-K-PERFORMANCE-LAB-DESIGN.md` |
| H4, H5 | `04-IMPLEMENTACION/FASE-I-POWERPLAY-DPM-DESIGN.md`; `04-IMPLEMENTACION/FASE-L-RX550-TUNER-DESIGN.md`; `03-EXPERIMENTOS/FASE-R4A-BANDWIDTH-REAL/EXP-F3-A-BANDWIDTH-REAL.md`; `03-EXPERIMENTOS/M1-cap-35-30/RESULTADOS-M1.md` |
| H6 | `03-EXPERIMENTOS/FASE-R4A-BANDWIDTH-REAL/EXP-F3-A-BANDWIDTH-REAL.md`; `04-IMPLEMENTACION/FASE-G-MEMORY-VRAM-GTT-DESIGN.md` |
| H7 | `05-FUENTES-EXTERNAS/FASE-R0-EXTERNAL-KNOWLEDGE/R0-2-POWERPLAY-MCLK-SMU7.md`; `03-EXPERIMENTOS/M1-cap-35-30/RESULTADOS-M1.md`; `03-EXPERIMENTOS/WORKLOAD-SINTETICO/RESEARCH.md` |
| H8 | `03-EXPERIMENTOS/FASE-R4B-GOVERNOR/EXP-F4-A-RESULTADOS-v2.3.md`, sección D7/causa probable |
| H9 | `04-IMPLEMENTACION/projects/ASYNC-AUX-RENDERER/EXPERIMENT-DESIGN.md`; `01-AUDITORIA/IMPLEMENTATION-READINESS/IMPLEMENTATION-READINESS-AUDIT.md` |
| H10 | `03-EXPERIMENTOS/ep05-mesa-custom-20260919-212249/RESULTADOS-EP05.md`; `05-FUENTES-EXTERNAS/FASE-R0-EXTERNAL-KNOWLEDGE/R0-3-MESA-WORKAROUNDS-POLARIS12.md` |
| H11 | `04-IMPLEMENTACION/projects/CLOSED-LOOP-QUALITY-GOVERNOR/EXPERIMENT-DESIGN.md`; `03-EXPERIMENTOS/FASE-R4B-GOVERNOR/EXP-F4-A-RESULTADOS-v2.3.md`, sin resultado de H11 |
| H12 | `03-EXPERIMENTOS/M1-cap-35-30/RESULTADOS-M1.md`; `04-IMPLEMENTACION/FASE-P-FRAME-GENERATION-UPSCALING-DESIGN.md`; `01-AUDITORIA/FASE-H12-2-WSI-DOCUMENTATION/H12-2-XDG-SHELL-VULKAN-WSI-EVIDENCE.md`; capacidad WSI parcialmente auditada, causalidad `UNKNOWN` |

## Resumen

| ID | Hipótesis | Estado actual | Siguiente acción permitida |
|---|---|---|---|
| H1 | El cap solo liga después de un umbral de demanda | `PARTIALLY_VERIFIED / REQUIRES EXPERIMENT` | Capability audit y diseño de A/B; autorización separada si se propone una escritura |
| H2 | La deuda térmica predice mejor el throttling que la temperatura instantánea | `REQUIRES EXPERIMENT` | Diseñar bloques térmicos, no ejecutar |
| H3 | La tasa de transición DPM explica mejor p99/stutter que el clock medio | `REQUIRES EXPERIMENT` | Definir series de estado y endpoint |
| H4 | Runtime PM afecta el primer frame después de idle | `REQUIRES CAPABILITY AUDIT` | Verificar estados PM/display/bridge |
| H5 | ASPM afecta bursts PCIe | `REQUIRES CAPABILITY AUDIT` | Verificar upstream, bridge y replay |
| H6 | Existe un umbral VRAM/GTT antes de saturar PCIe | `REQUIRES EXPERIMENT` | Diseñar working-set ladder y DMA gate |
| H7 | MCLK presenta histéresis | `PARTIALLY_VERIFIED (policy only) / REQUIRES EXPERIMENT` | Separar política SMU de observación local |
| H8 | GPU busy 100% puede coexistir con starvation | `REQUIRES EXPERIMENT` | Diseñar timeline CPU/submit/fence/WSI |
| H9 | Una compute queue puede mejorar sin overlap hardware | `REQUIRES CAPABILITY AUDIT / REQUIRES EXPERIMENT` | Enumerar queues; no asumir ACE/CU reservation |
| H10 | Los workarounds Mesa dependen de la workload class | `PARTIALLY_VERIFIED (negative result for tested scope) / REQUIRES EXPERIMENT` | Diseñar A/B per-process aislado |
| H11 | Render scale cruza un umbral DPM/thermal | `REQUIRES EXPERIMENT` | Capability audit WSI y ladder de scale |
| H12 | M1 está limitado por presentación/VSync/WSI | `PARTIALLY CONFIRMED` (capacidad WSI); `UNKNOWN` (causalidad) | No ejecutar; conservar la capa de capacidad y diseñar una continuación autorizada sólo si se separa GPU completion de presentación |

## H1 — Cap después de un umbral de demanda

- **Pregunta causal:** ¿el cap modifica clocks y p99 cuando el workload se acerca a la demanda que activa la limitación?
- **Intervención:** cap como variable de diseño, una sola condición por vez; cualquier escritura requiere autorización separada.
- **Mediadores:** W_SMU, SCLK, MCLK, throttle status, clock residency, workload demand.
- **Outcome:** p99, throughput, cap-limited fraction.
- **Evidencia existente:** M1 no discriminó 30/35 W para `vkmark shading:phong`; el resultado no demuestra equivalencia universal.
- **Estado:** `PARTIALLY_VERIFIED / REQUIRES EXPERIMENT`.
- **No afirmar:** que 35 W sea óptimo o que el cap no pueda ayudar en otro workload.
- **Siguiente gate:** capability audit de workload y autorización separada para cualquier escritura de cap.

## H2 — Thermal debt

- **Pregunta causal:** ¿la temperatura acumulada predice mejor la pérdida de clocks y p99 que `T(t)` aislada?
- **Intervención:** temperatura inicial/bloques de duración, sin cambiar settings.
- **Mediadores:** temperatura, SCLK, RULC, fan, W_SMU, estado de cooldown.
- **Outcome:** tiempo a SCLK bajo, p99, recuperación.
- **Evidencia existente:** R-4B documenta rampas y thermal confounding; la métrica `thermal_debt` no ha sido validada.
- **Estado:** `REQUIRES EXPERIMENT`.
- **No afirmar:** que `t90≈221 s` sea operacional; es extrapolación no validada.
- **Siguiente gate:** definir T_ref y validar el modelo con bloques independentes.

## H3 — DPM transition rate

- **Pregunta causal:** ¿la cantidad de cambios de estado DPM explica tails aunque el clock medio sea similar?
- **Intervención:** workload steady frente a bursty, sin modificar DPM.
- **Mediadores:** dwell time, transition rate, entropy, queue gaps.
- **Outcome:** p95/p99, missed deadlines, frame interval variance.
- **Evidencia existente:** se observaron estados SCLK/MCLK y transiciones, pero no existe una métrica validada de transición.
- **Estado:** `REQUIRES EXPERIMENT`.
- **No afirmar:** que la telemetría de 10 Hz capture toda la dinámica.
- **Siguiente gate:** definir sampling y observer overhead.

## H4 — Runtime PM y primer frame

- **Pregunta causal:** ¿runtime PM produce wake/resume penalty después de idle?
- **Intervención:** runtime PM, solo en una fase autorizada.
- **Mediadores:** PM status, wake time, fence, primer trabajo GPU, display path.
- **Outcome:** first-frame latency, p95/p99, missed deadline.
- **Evidencia existente:** `runtime_status=active` y documentación de PM; no existe A/B local.
- **Estado:** `REQUIRES CAPABILITY AUDIT`.
- **No afirmar:** que runtime PM tenga efecto o que no lo tenga.
- **Siguiente gate:** confirmar PM/display/audio/bridge y método de medición.

## H5 — ASPM y PCIe

- **Pregunta causal:** ¿ASPM y bursts PCIe producen replay, latencia o frame tails?
- **Intervención:** ASPM, solo con autorización separada.
- **Mediadores:** LnkSta/LnkCap, replay delta, PCIe estimate, DMA latency.
- **Outcome:** throughput, p99, missed deadlines, energía.
- **Evidencia existente:** Gen2×4 local y documentación ASPM; no existe estado ASPM local confirmado.
- **Estado:** `REQUIRES CAPABILITY AUDIT`.
- **No afirmar:** que ASPM esté activo, inactivo o sea la causa.
- **Siguiente gate:** enumerar bridge/root port/ASPM y medir replay.

## H6 — Umbral VRAM/GTT

- **Pregunta causal:** ¿la presión de working set/placement produce un umbral antes del máximo PCIe?
- **Intervención:** working-set ladder y tipo de memoria, sin cambiar sistema.
- **Mediadores:** VRAM, VIS, GTT, GEM/VM, DMA, PCIe, residency.
- **Outcome:** p99, throughput, frame tail, DMA bandwidth.
- **Evidencia existente:** 2 GiB VRAM, 256 MiB VIS y ~6,2 GB GTT; bandwidth real UNKNOWN.
- **Estado:** `REQUIRES EXPERIMENT`.
- **No afirmar:** que `mem_busy` sea bytes/s o que PCIe sea el cuello.
- **Siguiente gate:** read-only memory capability audit y diseño de working sets.

## H7 — MCLK histéresis

- **Pregunta causal:** ¿MCLK presenta rising/falling hysteresis frente a working set?
- **Intervención:** rampa ascendente/descendente de memoria.
- **Mediadores:** MCLK reportada, dwell time, rising/falling edge, frame response.
- **Outcome:** recuperación, p99, estabilidad.
- **Evidencia existente:** política histórica 5/16/20 para SMU7/Polaris y MCLK 1500 observado en algunos workloads; trigger real no cerrado.
- **Estado:** `PARTIALLY_VERIFIED (policy only) / REQUIRES EXPERIMENT`.
- **No afirmar:** `mem_busy ≥20 → MCLK 1500` ni que MCLK reportada equivalga a DRAM data rate.
- **Siguiente gate:** separar source-level policy de observación local.

## H8 — GPU starvation

- **Pregunta causal:** ¿`gpu_busy=100%` puede coexistir con falta de trabajo submitido o WSI backpressure?
- **Intervención:** background/ownership/WSI controlado.
- **Mediadores:** CPU submit gap, fence, queue wait, GPU timestamps, busy.
- **Outcome:** GPU idle gaps, p99, missed deadline.
- **Evidencia existente:** el informe R-4B registra un patrón histórico durante S2 (`gpu_busy=100 %`, MCLK bajo y W_SMU bajo); la atribución a un cliente externo no fue verificada y S2 quedó `PARADA_D`.
- **Estado:** `REQUIRES EXPERIMENT`.
- **No afirmar:** que Xwayland, ChatGPT u otro cliente causaron la parada.
- **Siguiente gate:** instrumentación de timeline y control de clients.

## H9 — Compute queue

- **Pregunta causal:** ¿una compute queue reduce total frame time aunque no exista hardware overlap independiente?
- **Intervención:** misma carga en graphics queue frente a compute queue, con barriers controlados.
- **Mediadores:** per-queue time, wait, GPU gaps, SyncVal, clocks/thermal.
- **Outcome:** total frame time, p99, missed deadline.
- **Evidencia existente:** documentación de queues/async; no hay A/B local.
- **Estado:** `REQUIRES CAPABILITY AUDIT / REQUIRES EXPERIMENT`.
- **No afirmar:** que exista reserva de CUs por API Vulkan o que el número de ACEs sea 2.
- **Siguiente gate:** enumerar queue families y revisar barriers/semantics.

## H10 — Mesa por workload

- **Pregunta causal:** ¿DCC, sample-location, image-meta, line-filter o compile backend cambian solo determinadas workloads?
- **Intervención:** una opción Mesa por proceso.
- **Mediadores:** GPU time, format, MSAA, DCC, correctness, present path.
- **Outcome:** p99, throughput, VRAM/GTT, error de imagen.
- **Evidencia existente:** CUSTOM≈STOCK en tres escenas frías; no demuestra benefit general.
- **Estado:** `PARTIALLY_VERIFIED (negative result for tested scope) / REQUIRES EXPERIMENT`.
- **No afirmar:** que CUSTOM sea una optimización ni que ACO/LLVM sea superior.
- **Siguiente gate:** workload API-matched y A/B per-process.

## H11 — Umbral de render scale

- **Pregunta causal:** ¿cambiar render scale mueve el workload entre umbrales DPM/thermal?
- **Intervención:** ladder de scale, sin cambiar sistema.
- **Mediadores:** SCLK/MCLK, W_SMU, thermal, WSI, present timing.
- **Outcome:** p99, FPS producido, missed deadlines, energía por frame.
- **Evidencia existente:** R-4B tiene evidencia diagnóstica e inconclusa; no hay resultado de H11.
- **Estado:** `REQUIRES EXPERIMENT`.
- **No afirmar:** que render scale reduzca siempre energía o que R-4B sea SUPPORTED.
- **Siguiente gate:** resolver H12/WSI y fijar target workload.

## H12 — Presentación/VSync/WSI

- **Pregunta causal:** ¿el frametime de M1 está limitado por GPU completion o por WSI/VSync/presentación?
- **Intervención:** condiciones de superficie/presentación ya soportadas por una herramienta existente; no crear código nuevo en esta fase.
- **Mediadores:** submit, fence/query, GPU completion, present request, first pixel, target vblank.
- **Outcome:** GPU-to-visible delay, missed deadline, p95/p99, frame production.
- **Evidencia existente:** M1 tuvo una mediana de 13,514 ms y 74 FPS; H12-2 r3 confirmó target/queue/surface/FIFO/capacidades de timestamp, pero no separó offscreen/onscreen/VSync.
- **Hallazgo H12-2:** `state=4 = activated` en xdg-shell local 1.49; un configure posterior al primer present no es un `CONFLICT` normativo por timing. La causa exacta y la compatibilidad posterior del swapchain siguen `UNKNOWN`.
- **Estado:** `PARTIALLY CONFIRMED` para la capacidad/semántica WSI; `UNKNOWN` para la causalidad M1.
- **No afirmar:** que M1 sea VSync-limited o GPU-limited; que `wl_surface.frame` sea vblank; que `state=4` sea focus; ni que el segundo configure sea resize, fullscreen, maximización o error.
- **Siguiente gate:** no ejecutar; conservar el informe H12-2 y diseñar una continuación autorizada que separe GPU completion, `vkQueuePresentKHR`, WSI commit y presentación observable.

## Estados no resueltos

- El número físico de ACEs de Polaris12 es UNKNOWN.
- La equivalencia nominal `gfx803/gfx804` para `1002:699f` es UNRESOLVED; usar `Polaris12/GFX8` como forma neutral.
- El soporte runtime de `VK_AMD_gpa_interface`, RGP, SQTT, PMU, present timing, fdinfo, ASPM y counters detallados no está confirmado en esta placa.
- La taxonomía de estados debe armonizarse antes de convertir este registro en una vista LIVE.
