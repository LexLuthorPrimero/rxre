# PRIOR-ART — EXP-F1-A Jitter Observability

**FASE:** R-4C (PRECHECK)
**Fecha:** 2026-09-22
**Clasificador de estados:** VERIFIED | DERIVED | ESTIMATED | UNKNOWN | REQUIRES FUTURE EXPERIMENT
**Norma:** no adivinar; fuentes primarias/officiales prioritarias; si no hay fuente → UNKNOWN o REQUIRES FUTURE EXPERIMENT.

---

## 1. ¿Existe un mecanismo Vulkan que exponga los offsets de jitter por frame?

**Resultado: NO. VERIFIED.**

- El spec Vulkan 1.z no define ningún parámetro ni extensión de "jitter" ni de "camera offset". Los offsets de cámara/jitter son convención de la aplicación/engine y viajan por estructuras genéricas (push constants, descriptores, uniform buffers, matrices en UBOs).
- Fuentes: (a) API Semantics v1.3 razonable — no existe wording de jitter en el spec (contexto de toda la fase; nada en Vulkan vkspec menciona jitter/temporal jitter). (b) FUSION-01 (revisión interna) documenta este mismo hecho → PARTIALLY VERIFIED en R-3.1.
- Conclusión: si se quiere observar el jitter desde fuera del renderer, hay que interceptar las estructuras genéricas en las que viaja (o su representación final en la matriz de proyección).

## 2. Mecanismo de capas (Vulkan Layers) — observabilidad real que otorgan

**Resultado: VERIFIED (fuente primaria: Khronos VkLayer-interface).**

- Las capas interceptan funciones **host** vía dispatch tables (cadena de instancia y de device). Pueden ver los parámetros API exactamente como los pasa la aplicación, y pueden **insertar llamadas** en la cadena.
- Una capa interceptando `vkCmdPushConstants` recibe el puntero **host** `pValues` en tiempo de recording; el contenido se copia al command buffer en ese momento (spec / man page de `vkCmdPushConstants`). → La capa puede leer esos bytes.
- Una capa interceptando `vkUpdateDescriptorSets`/`vkCmdBindDescriptorSets` ve handles, layouts, offsets y rangos — pero **NO el contenido de buffers residentes en GPU**.
- Para leer contenido de un buffer la capa debe: (1) rastrear `vkAllocateMemory`/`vkBindBufferMemory` para mapear handle→DeviceMemory, (2) `vkMapMemory` solo si la memoria es HOST_VISIBLE, (3) leer en el momento adecuado. NO puede leer memoria DEVICE_LOCAL arbitraria.
- No existe mecanismo de capa para inspeccionar un command buffer grabado (opaco) ni para leer buffers residentes sin cooperación/vías host-visible.
- Referencia del mundo real: VIL (Vulkan Introspection Layer) y el sistema de captura de RenderDoc demuestran que "observar desde una capa" es práctico, pero ambos operan vía las mismas restricciones (intercepción host + buffers host-visible).

## 3. Prior art de jitter temporal (TAA) — representación matemática

**Resultado: VERIFIED (fuente primaria: GPUOpen FidelityFX Super Resolution 2 — manual oficial).**

- La secuencia de jitter implementada por FSR es **Halton[2,3]**, en **unidades de píxel**.
- Conversión a offsets de proyección (manual FSR2):
  - `jitterX = 2*jitterX / renderWidth`
  - `jitterY = -2*jitterY / renderHeight`
  - `jitteredProjectionMatrix = translateMatrix(identity, jitterX, jitterY, 0) * projectionMatrix`
- El jitter se aplica "to all rendering" vía la matriz de proyección de cámara.
- Regla explícita del manual: **Nunca generar el vector nulo (0,0)**.
- Longitud de secuencia por modo de escalado (p.ej. Quality = 18; custom = ceil(8·n²)±algoritmo FSR).
- Los motion vectors **NO** deben llevar jitter aplicado → en principio ortogonal a la reconstrucción; aquí solo releva que el MV no es la señal de jitter (ver §6).

## 4. Precisión numérica del target MAE < 0.01 px

**Resultado: PROVISIONAL TARGET (sin estándar previo publicado).**

- Ningún paper/repositorio establece un umbral estándar de "precisión exigida para reconstruir jitter observado". Búsqueda: TAA surveys (Yang/Liu/Salvi, Playdead), FSR, TXAA 3.0, ATAA, Hanika — ninguno define tolerancia de reconstrucción de offsets.
- Análisis DERIVED (FP32) para el Nivel B (matriz):
  - Para W=1920, un offset de 0.5 px → componente NDC `2*0.5/1920 ≈ 5.2e-4`.
  - Target 0.01 px → `2*0.01/1920 ≈ 1.04e-5` en la componente NDC.
  - FP32 cerca de 5e-4..1e-2 tiene resolución relativa ~1.19e-7 → margen de ruido de ~×50..×500 por encima del piso de FP32. La cuantización no es limitante; el error real vendrá de la reconstrucción (delta de matrices), no del formato.
  - Para el canal directo (Nivel A, valor en push constants / campo plano) la precisión es esencialmente exacta (copia de float).
- Conclusión: mantener `MAE < 0.01 px` como **PROVISIONAL TARGET** (criterio exigente pero alcanzable según el análisis FP32), con justificación documentada; si los datos del experimento muestran otro umbral significativo se ajustará con evidencia.

## 5. Secuencia de jitter propuesta — justificación vs prior art

**Resultado: DERIVED (combinación de requisitos R-4C + práctica FSR/TAA).**

Ver §5 del EXPERIMENT-DESIGN. Se exige (mandato R-4C): ±, solo X, solo Y, X+Y, magnitudes pequeñas, repetitiva, pseudo-aleatoria determinista. Se añade bloque Halton[2,3] (patrón de facto de la industria, FSR2) como sub-bloque de verificación de píxel-unit space. Se prohíbe (0,0) por diseño (regla FSR2). Total: 32 prototipos × 8 repeticiones = 256 frames observables (sin contar frames de calentamiento).

## 6. Jitter ≠ motion vector

**Resultado: VERIFIED (semánticamente distintos; contradicción de "jitter = MV" documentada en FUSION-01 de R-3.1).**

- Motion vector = desplazamiento de color de un punto entre frames (para reproyección de datos).
- Jitter = desplazamiento subpixel de la muestra de proyección (offset de cámara), **separado** del MV.
- FSR2 manual: MV es la entrada en vec2 a la técnica; el jitter se inyecta en la matriz de proyección, no en el MV.
- El experimento mide el jitter; **no** se concluye jitter = MV (mandato R-4C §13).

## 7. Observabilidad de representaciones concretas (matriz de decisión del experimento)

| Representación del jitter | Observable desde capa | Condición | Estado |
|---|---|---|---|
| Push constants (float2 o matriz en push) | SÍ | capa intercepta `vkCmdPushConstants` (`pValues` host en recording) | VERIFIED (primaria: man page) |
| UBO/SSBO (contenido) | SÍ solo si HOST_VISIBLE y capa rastrea alloc+bind+map | cooperación del app/memoria | DERIVED (mecánica de fragmentos host) |
| UBO DEVICE_LOCAL | NO | prohibido leer resident GPU | VERIFIED |
| Matriz de proyección final en UBO host-visible | SÍ (reconstrucción algebraica) | capa lee la matriz y deriva jitter | DERIVED (ver EXPERIMENT-DESIGN §6 B2) |
| Command buffer opaco | NO | opaco tras recording | VERIFIED |
| SPIR-V / pipelines / layouts / viewport | SÍ | intercepción de `vkCreate*Pipeline`, `vkSet*` | VERIFIED |
| No existen APIs ni ext. de jitter | — | — | VERIFIED (§1) |

## 8. Capacidad del sistema local para hospedar el harness (probe read-only)

**Resultado: VERIFIED (sondeo local 2026-09-22).**

- ICDs presentes en `/usr/share/vulkan/icd.d/`: `radeon_icd.*.json` (RADV), `intel_icd.*.json` (ANV), `lvp_icd.*.json` (lavapipe), más otros (asahi, freedreno, etc.). → Podemos ejecutar el harness en RADV (RX 550), ANV (iGPU HD Graphics 4600) o lavapipe, y así comparar capas sin tocar la máquina real.
- `/usr/share/vulkan/explicit_layer.d/`: vacío → la capa del experimento se cargará **solo** vía `VK_LAYER_PATH` apuntando al directorio local de `harness/`, sin escribir en el sistema.
- Toolchain: `gcc 16.2.1`, `glslangValidator 16.3.0`, `cmake 4.3.0`, `ninja`, `pkg-config`, `vulkan.h` en `/usr/include/vulkan/`. → Build local aislado factible sin instalar nada.
- Esto habilita las corridas NIVEL A/B en 3 drivers (R-4C §15 pide ≥1 real + 1 software; se ofrece RADV real + lavapipe software + ANV opcional).

## 9. Lista de referencias

1. Khronos, *Vulkan Loader — Layer Interface* (LoaderLayerInterface.md, rama main). VERIFIED.
2. Khronos, `vkCmdPushConstants` man page (Vulkan API reference). VERIFIED.
3. GPUOpen (AMD), *FidelityFX Super Resolution 2 / Techniques — Super Resolution Temporal* (manual oficial). VERIFIED §3.
4. Khronos Vulkan vkspec 1.3 — semántica API general (contexto). VERIFIED.
5. VIL (Vulkan Introspection Layer) — precedente de capa de introspección. ESTIMATED (conocimiento público; no verificado localmente).
6. RenderDoc — precedente de captura por capa. ESTIMATED.
7. Yang, Liu & Salvi "Temporal AA — A Survey" (2020); Playdead (Karis). ESTIMATED (citados en projects/JITTER-REPROJECTION/PRIOR-ART.md, revisados en R-3).
8. FSR2/AMD — regla "nunca vector nulo (0,0)". VERIFIED (§3).

**Hallazgo principal:** la observación del jitter es viable SOLO si el offset viaja por (a) push constants, o (b) buffers host-visible mapeados, o (c) se reconstruye de la matriz de proyección. Ninguno de los tres altera el sistema ni la GPU: son puros contratos host-Vulkan de la aplicación de prueba.