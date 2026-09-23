# FUSION 01 — "LA SEÑAL ES UNA, LOS CONSUMIDORES SON DOS" (jitter dual-consumer)

> **Archivo:** `FUSION-01-JITTER-DUAL-CONSUMER.md`
> **Fase:** FASE R-3.1 — FUSION ARCHITECTURE AUDIT
> **Fecha:** 2026-09-22 — READ-ONLY
> **Categoría de fusión:** ARQUITECTURA DE SEÑAL COMÚN (TAA jitter → reproyección temporal + predicción de tiles/texturas)

---

## 1. Componentes audited

- TAA sub-pixel jitter (componente conocido — TAA survey, Yang/Liu/Salvi).
- BERRETA (overlap async / reuso de trabajo, del ecosistema).
- Ghost Cache predictivo (predicción por cámara → pre-cálculo de accesos).

## 2. Cómo exponen los engines el jitter (evidencia)

| Engine/sistema | Exposición del jitter | Alcanza shaders vía |
|---|---|---|
| Unreal Engine (TAA/TSR) | desplazamiento de la matriz cámara/proyección; patrón de posiciones fijo | matrix cam proyectada; shaders ven matrices de-jittered con flag |
| Unity (TemporalAntialiasing.cs) | `GetJitteredProjectionMatrix()`, `Vector2` jitter normalizado | `_JitterUV`, matriz de proyección jittered |
| FSR2 | app entrega el jitter (Halton(2,3)) y lo compone en la matriz | uniform del upscaler |

**Conclusión:** el "jitter" NO se expone como metadata; se codifica como delta de matriz o push constant.
Detectarlo desde afuera requiere heurística (delta de matrices, patrón Halton conocido, reflexión de shader) —
**no hay extensión Vulkan que exponga offsets subpixel por frame** (solo `VK_EXT_present_timing`, no jitter).

## 3. ¿Puede una Vulkan layer observarlo?

**PARTIALLY VERIFIED (KNOWN VARIANT).** Los layers son interceptores de pleno derecho y ven
`vkCmdPushConstants`, updates de descriptors y recursos; el Vulkan Introspection Layer (VIL) lee contabilidades
de buffers/uniform-buffers por draw; RenderDoc obtiene constant blocks / push constants vía Python API. PERO:
interpretar el dato requiere conocimiento del layout del engine o heurística. La observación es posible; la
**interpretación automática** es dependiente del engine.

## 4. ¿Jitter ≠ motion vector? (núcleo de la auditoría)

**CONTRADICTED por prior art.** Desde el TAA survey y el shader de Playdead (`_JitterUV` separado de
`_VelocityBuffer`), el jitter es la secuencia de offsets subpixel de proyección; NO codifica:
- **object motion** (movimiento per-objeto → requiere motion vectors o correspondencias densas);
- **disocclusion** (necesita depth/history validation);
- **camera pose** completa (el jitter es el *offset de proyección*, no el *delta de pose*);

**Hanika et al. 2021** ("Fast Temporal Reprojection without Motion Vectors") NO usa jitter: usa
correspondencias de imagen densas (patch-match); **ATAA** documenta dónde la reproyección falla sin mejores
señales (sombras/reflejos). Distinción requerida (del enunciado) auditada:

| Señal | Qué codifica | Recuperable del jitter? |
|---|---|---|
| CAMERA MOTION | delta de pose | Solo la componente de proyección ya aplicada — incompleto |
| OBJECT MOTION | movimiento de objetos | NO |
| PIXEL MOTION | movimiento de imagen agregado | parcial, ambiguo |
| JITTER | offset subpixel deliberado | la propia secuencia (dato), no la dinámica |
| MOTION VECTORS | flujo vectorial por píxel | NO |
| REPROJECTION TRANSFORM | mapeo historia→actual | requiere matrices, no solo jitter |

**Resultado:** la hipótesis "jitter delta = motion vector" es **FALSA**. La arquitectura necesita señales
adicionales (matrices de cámara reales, depth, y MVs para objetos dinámicos). El jitter solo puede servir de
**disparador de temporalidad** (identificar que el renderer usa TAA / que la cámara está quieta o se movió ≤1
pixel), no de vector completo.

## 5. ¿Puede el jitter predecir tiles de textura?

**NOVELTY UNKNOWN / PLAUSIBLE mecánicamente.** La predicción por cámara existe (Dumont 2003 — "prediction
camera"; UE streaming por cámara; idTech5 feedback+paging), pero ninguna fuente combina "jitter → predicción
de texturas". El jitter contiene información de *subpixel apenas*; para predecir qué texturas vienen se
necesita la trayectoria de cámara (no el jitter). Ghost predictivo (I-06) debe usar cámara/matrices, NO jitter.

## 6. Falsabilidad

Hipótesis falsable: *"un detector de cámara-estática + reproyección solo-cámara puede congelar tiles
texturales sin error visible durante X frames en escena estática"* — falsable midiendo error de reproyección
y tasa de hit del working-set de texturas. La afirmación fuerte ("una sola señal alimenta reproyección Y
predicción") es **falsa por construcción** (señal insuficiente).

## 7. Veredicto de fusión

- **Sobrevive como:** "temporalidad por cámara-estática → tile-lock (I-02) + prefetch conservador (I-06)".
- **Muere como:** "jitter único vector de re-proyección y predicción".
- **Novedad:** KNOWN VARIANT (componentes) + PARTIALLY NOVEL (alimentación conjunta observada — no
  documentada); NOVELTY UNKNOWN en la aplicación conjunta.
- **Estado:** **NEEDS PRECONDITION** (requiere probar observabilidad del jitter en harness propio).