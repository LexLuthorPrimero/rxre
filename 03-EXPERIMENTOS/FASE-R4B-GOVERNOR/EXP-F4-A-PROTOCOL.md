# EXP-F4-A PROTOCOL — Governor frametime-feedback read-only (FASE R-4B)

> **Directorio:** `experiments/FASE-R4B-GOVERNOR/`
> **Fase:** FASE R-4B — EXP-F4-A GOVERNOR READ-ONLY
> **Fecha:** 2026-09-22
> **Versión:** 2.1 (alineación de tiempos DIST/R4 pre-ejecución; v2.0 = revisión metodológica; sin cambios de
> umbrales ni criterios). **Estado del ítem:** PROTOCOLO REVISADO / **AWAITING SECOND CONFIRMATION FOR EXECUTION**
> **Cambio Vs 1.0:** el éxito ya NO se define como "p99 ≥15 % menor que FIXED s=1.00" (confundía el mecanismo de
> feedback con la reducción deliberada de render-scale). El éxito ahora evalúa la **calidad de regulación del
> lazo** alrededor de un **objetivo absoluto T pre-committed** (definido en §6), con criterios de overshoot,
> oscilación, convergencia, reproducibilidad, calidad-óptima y respuesta a disturbios. FIXED s=1.00 permanece
> como control de referencia, pero sus estadísticos se reportan de forma descriptiva (§12, preguntas A–E).
> **Regla de esta entrega:** NO se ha creado código, NO se ha compilado, NO se ha ejecutado nada.
> **Regla de cambio de umbrales:** todos los umbrales quedan fijados en este documento. **Ninguno** se introduce,
> modifica o "afina" después de observar resultados (prohibición de post-hoc).
> **Constante general:** programación de contadores y toda escritura del sistema siguen **NO AUTORIZADAS**;
> este protocolo es **read-only absoluto**.

---

## 0. Pregunta experimental (única)

> ¿Puede el governor utilizar **frametime como señal de feedback** para **mantener el rendimiento alrededor
> de un objetivo definido** mediante ajustes de render-scale, con histéresis, y **sin contadores HW ni
> escrituras GPU**?

El objeto de estudio es el **mecanismo de feedback** (detectar → decidir → actuar → volver a medir), NO la
velocidad absoluta de render. Esta fase NO valida juegos reales, NO implementa un governor permanente, NO es
un benchmark de "FPS máximo" (prohibición §15).

---

## 1. Hipótesis (falsable)

- **H2 (mecanismo):** un governor frametime-feedback por ventana rodante, con histéresis y actuador
  render-scale (únicos actuador), **mantiene p99 cerca de un objetivo T pre-committed**, converge en tiempo
  acotado, evita overshoot y oscilación sostenida, responde reproduciblemente a cambios de carga, y converge
  al **mayor render-scale compatible con T**. Sin contadores HW ni escrituras GPU.
- **H2r (ante hipótesis nula/referencia):** el mismo workload a calidad fija s=1.00 viola T por construcción
  (§6) y su p99 > T; la comparación con FIXED se reporta como **pregunta aparte** (§12-E), nunca como
  criterio único de éxito.
- **Falsación:** cualquiera de los criterios F1–F6 de §13 (incluida la curva render-scale→frametime plana o
  no monótona, imposible de gobernar).

## 2. Workload GPU-bound reproducible

**Riesgo documentado (MASTER v2.10, ES-01/F2, DESIGN-GRAPHICS §4):** los sintéticos Vulkan previos son
**fetch-latency bound** (frametime ∝ fetch, power invariante, SCLK/MCLK máximos). Para que render-scale sea un
actuador real, el workload debe ser **fragment/banda/ROP-bound**. Harness = **Diseño B "gráfica pesada"** de
`DESIGN-GRAPHICS.md` (seleccionado en esa fase para presionar la ruta gráfica real):

- **Offscreen, sin presentación** (sin swapchain): el frametime mide trabajo GPU puro + envío CPU.
- **Vertex:** fullscreen triangle *bufferless* (3 vértices, UV de `gl_VertexIndex`).
- **Fragment (por píxel):**
  - UV fragmentados derivados de `gl_FragCoord` (escala grande + offset por capa) → accesos incoherentes;
  - **4 samples** de 4 texturas **4096² RGBA8** (≈ 64 MiB c/u, ≈ 256 MiB total > 512 KB L2) → misses L1/L2 → DRAM;
  - cadena de **~24 fma** sobre los samples (mantiene ALU/SCLK alta);
  - **salida de alta varianza** (bits de `gl_FragCoord` mezclados con samples) → derrota DCC → el CB sale a DRAM;
  - **blending ADITIVO** → read-modify-write del CB por capa.
- **Overdraw:** **N=4 capas fullscreen** fijas en TODO el experimento (base de DESIGN-GRAPHICS §4; rango
  documentado 1–8). SOLO los trials de disturbio (§7/§9) conmutan N: 4→8→4 como perturbación de carga
  (push constant del propio harness; no es cambio de sistema).
- **Render pass:** 1 color attachment `R8G8B8A8_UNORM`, base **1920×1080**; sin MSAA.
- **Bucles:** fence por frame → frametime por fence (`clock_gettime` MONOTONIC, µs); sin vsync (offscreen).
- **Presupuesto VRAM:** ~256 MiB texturas + ≤ 8 MiB CB < 1 GiB → sin OOM (RX 550 2 GiB).
- **Determinismo:** todo derivado de `gl_FragCoord` y push constants (N, seed fija); sin estado aleatorio.

## 3. Resolución / base de referencia

- Base full-res: **1920×1080** offscreen (render target fijo 1920×1080).
- El **único actuador** es el **render-scale** = viewport/scissor `(⌊s·W⌋, ⌊s·H⌋)`; píxeles sombreados ∝ s².
  El framebuffer físico NO cambia. N, texturas, shader, seed: constantes pre-committed (§2).

## 4. Conjunto exacto de render-scales

| Escala s | area_fraction = s² | Viewport (aprox. 1920×1080) |
|---|---|---|
| 1.00 | 1.0000 (100 %) | 1920×1080 |
| 0.87 | 0.7569 (75.7 %) | 1670×940 |
| 0.75 | 0.5625 (56.3 %) | 1440×810 |
| 0.62 | 0.3844 (38.4 %) | 1190×670 |
| 0.50 | 0.2500 (25 %) | 960×540 |

5 pasos discretos (motor DRS estándar, ~√2 por paso en área ⇒ p99 sensible al salto). Cada fila registra
**siempre** `(s, area_fraction)` junto a sus métricas de rendimiento (§11): regla anti-"mejora sin costo".

## 5. Cuantización temporal

- **Ventana de monitor del governor:** **20 s** (windows rodantes de 20 s alineadas al inicio de trial).
- **Telemetría sysfs:** **10 Hz** (patrón `telemetria.sh` validado; card1/hwmon2, solo lectura).
- **Frametime:** por frame (fence); cada ventana de 20 s ≈ 600–2400 frames según fps → p99_window estable.
- **Warm-up global de sesión:** 30 s a s=1.00 (asentar DPM/térmico), excluido.
- **Warm-up de transición por trial:** 5 s al estado inicial del trial, **sin registrar**.
- **Duración de trials (medida, sin warm):**
  - Phase 1 open-loop block: **20 s** medidos (25 s con warm) por escala y pass.
  - Trial **GOVERNOR**: **120 s** medidos (6 ventanas de 20 s) → convergencia ≤80 s + ≥40 s de régimen.
  - Trial **FIXED**: **60 s** medidos (3 ventanas).
  - Trial **DISTURBIO**: **200 s** medidos (10 ventanas de 20 s; step de carga a +60 s y retorno a +120 s, §9).
- **Ventana mínima entre cambios de escala:** **40 s** (2 ventanas consecutivas fuera de banda) — §10.

## 6. Calibración pre-committed y definición de T (target) y s* (calidad óptima)

**Regla de oro anti-post-hoc:** T y s* se derivan **exclusivamente** de datos **open-loop** (controlador
APAGADO, escalas fijas) y se **congelan en el manifest** (sha256) **antes** de la primera trial de governor.
Las corridas del governor NUNCA participan en la definición de T; ninguna revisión posterior los altera.
**Orden estricto de ejecución (verificación explícita):** la **Fase 1 termina por completo** (los 15 bloques
open-loop + los GATEs de §6.1.4, §6.1.5 y §6.3) **antes** de calcular T/s*, y el **FREEZE(T, s*, sha256)
queda registrado en el manifest antes de que comience la primera corrida del governor (Phase 2)**. Ningún
proceso del governor se lanza durante la Fase 1.
**Inmutabilidad total:** ningún resultado de GOVERNOR (ni de FIXED/DIST) puede modificar **retrospectivamente**
T, s*, ni los criterios R1–R7 (§12) ni los umbrales F1–F6 (§13). Cambiar cualquiera tras observar resultados
es **parada C** ("nueva clase") → documentar y detener.

### 6.1 Fase 1 — caracterización open-loop (por sesión, controlador off)

1. **Passes por escala:** para cada s ∈ S, **B=3 bloques** de 20 s medidos, en passes
   **ascendente (1.00→0.50) → descendente (0.50→1.00) → ascendente** (15 bloques/sesión). La doble dirección
   verifica que la curva no dependa de la dirección de barrido (histéresis de la planta).
2. **Estadístico por bloque:** `p99_b(s,b)` = percentil 99 de los frametimes por-frame del bloque b a escala s.
3. **Estadístico de calibración:** `P99(s) = mediana_{b=1..3} p99_b(s,b)`.
4. **Validación de monotonía y poder de discriminación (GATE pre-committed):** exigir que P99(s) sea
   **no creciente** en s y que existan **≥2 pasos consecutivos con reducción ≥3 %**. Si la curva es plana,
   no monotónica o con escalones <3 % → **hipótesis H2 no testable** → parada D + GAP (prohibido "afinar").
5. **Sanity gate de rango:** exigir **5 ms ≤ P99(1.00) ≤ 200 ms**; fuera → parada D (workload mal acondicionado
   para ventanas de 20 s), sin retuning.

### 6.2 Definición de T (objetivo absoluto)

- **Métrica objetivo:** T es un **objetivo absoluto sobre el p99 del frametime por-frame** (ms), el mismo
  estadístico p99 que usa el lazo y el que cita la roadmap EXP-F4-A/H2 ("mantiene p99 ≤ T") y FUSION-04 §4.
- **Fórmula (pre-committed, fijada en este documento):**

  ```
  T = 0.80 · P99(s=1.00)
  ```

  donde `P99(1.00)` es la mediana de los 3 bloques open-loop a escala completa.
- **Qué muestras entran:** SOLO los 3 bloques open-loop de s=1.00 (Fase 1), controlador apagado.
- **Por qué 0.80 (justificado en el protocolo, no elegido con datos):** exige una reducción del **≥20 %** de p99
  frente al full-scale natural. (i) No trivial: 20 % ≫ variabilidad inter-bloque esperada (GATE §6.1.4 pide
  pasos ≥3 %; 20 % son >3 pasos de resolución típicos); (ii) alcanzable por diseño: se **verifica** en
  §6.3 que ∃ s con P99(s) ≤ T (si no, parada D); (iii) garantiza que s=1.00 **viola** T por construcción
  (0.80 < 1) ⇒ el governor SIEMPRE tiene que actuar al menos una vez ⇒ el mecanismo se ejercita; (iv) es
  **estrictamente más exigente** que el "≥15 % vs fijo" que ejemplifica la roadmap EXP-F4-A, y al estar
  fijado antes de ejecutar evita selección post-hoc.
- **T es un valor numérico en ms** (resolución 0.001 ms) congelado en el manifest antes de Phase 2.

### 6.3 Definición de s* ("mayor render-scale posible compatible con el objetivo")

```
s* = max{ s ∈ {1.00, 0.87, 0.75, 0.62, 0.50} : P99_open-loop(s) ≤ T }
```

- **Regla determinista predefinida:** s* = mayor render-scale del conjunto literal
  **{1.00, 0.87, 0.75, 0.62, 0.50}** (_únicos_ 5 escalas de §4) tal que `P99_open-loop(s) ≤ T`, siendo
  `P99_open-loop(s)` la mediana de los 3 bloques open-loop de la Fase 1 (§6.1) y `T` el valor de §6.2.
  **Los únicos datos que entran en el cálculo son los de la Fase 1 OPEN-LOOP** (controlador apagado,
  escalas fijas). **Ningún dato de la Fase 2 GOVERNOR (ni FIXED ni DIST) participa en el cálculo de s*.**
- s* es la **referencia de calidad-óptima**: la mayor escala que, según la curva open-loop (planta, sin lazo),
  mantiene p99 ≤ T. Es la "verdad terreno" del actuador ideal.
- **Reachability GATE (pre-committed):** si **ningún** s del conjunto {1.00, 0.87, 0.75, 0.62, 0.50} cumple
  `P99_open-loop(s) ≤ T` (bajo el GATE de monotonía §6.1.4 esto equivale a `P99_open-loop(0.50) > T`),
  entonces el objetivo es **inalcanzable** → se aplica **de inmediato y sin excepción el criterio de
  parada D** y **NO se ejecuta ninguna corrida del governor** (Phase 2 no comienza). Prohibido "afinar",
  replantear T o redefinir el conjunto de escalas.
- El gobernador será evaluado contra s* (§12, pregunta B/calidad-óptima R6).

## 7. Orden de condiciones (pre-committed)

Por sesión (×2 sesiones independientes, misma N=4, misma textura, misma seed):

```
Sesión: pre_flight → Fase 1 (open-loop, 15 bloques) → FREEZE(T, s*) en manifest
        → Phase 2 trials (alternados) → post_flight
```

- **Sesión 1 — Phase 2:** FIXED₁ → GOV₁ → FIXED₂ → GOV₂ → FIXED₃ → GOV₃ → DIST₁ → DIST₂
- **Sesión 2 — Phase 2 (contrabalanceo de orden):** GOV₁ → FIXED₁ → GOV₂ → FIXED₂ → GOV₃ → FIXED₃ → DIST₁ → DIST₂
- Par i = {FIXED_i, GOV_i} (i=1..3 por sesión) ⇒ **6 pares** en total (diseño pareado para §12-E).
- DIST₁/DIST₂ por sesión ⇒ **4 trials de disturbio** en total (§9/§12-R7).

**FIXED_i** se ejecuta en la condición de carga idéntica a GOV_i (mismo cierre de sesión, mismo workload N=4).

## 8. Control FIXED (referencia de calidad máxima)

- **FIXED:** render-scale **constante s=1.00**, 60 s medidos, controlador apagado. Representa la calidad
  máxima posible y — por construcción de T (§6.2) — **viola T**: `p99_FIXED > T`.
- **Rol:** (i) referencia de la pregunta E (§12); (ii) verificación de que la hipótesis nula
  "calidad fija s=1.00 mantiene el objetivo" es falsa por diseño; (iii) baseline de telemetría (power,
  SCLK, MCLK) a carga completa.
- **NO es un objetivo a superar en FPS**: sus métricas de rendimiento se reportan **junto a su escala
  (s=1.00, area=1.0)** y cualquier comparación se formula en §12-E como preguntas separadas.

## 9. Condición GOVERNOR y disturbios de carga

- **GOVERNOR:** comienza en s=1.00; controlador **externo** (proceso Python separado, §13) recalcula cada
  20 s el `p99_window` de la ventana rodante y aplica la regla §10 escribiendo el **único** archivo de
  control `control_scale.txt` que el harness lee en el límite de ventana. La señal de feedback es
  **exclusivamente frametime (fence)**; power/SCLK/MCLK son informativas (no alimentan el lazo).
- **GOVERNOR no conoce T por inspección de resultados:** recibe el valor T congelado del manifest como
  parámetro de arranque; la evaluación de éxito la hace el analista con los umbrales pre-committed (§12).
- **Disturbio de carga (DIST)** — test de "responde reproduciblemente a cambios de carga" (requisito 4/8):
  - Duración **200 s medidos** (10 ventanas de 20 s) con el governor activo.
  - **t=+60 s (inicio de ventana 4):** step de carga `N: 4 → 8` (doble overdraw, push constant del
    harness; sin cambio de sistema). Las 2 primeras ventanas (60–100 s) cargan con N=8 → p99 sube.
  - **t=+120 s (inicio de ventana 7):** retorno `N: 8 → 4`. Ventanas 7–8 (120–160 s) vuelven a N=4.
  - Se mide: latencia (en ventanas) desde cada evento hasta la **primera acción correcta** de bajada
    (tras el step a N=8) y de subida (tras el retorno a N=4); y la re-incorporación de p99 a la banda
    tras cada evento.
  - Predecible por el diseño: p99 sube al duplicar overdraw → el governor debe bajar escala ≤2 ventanas;
    al restaurar, p99 cae → debe subir escala ≤2 ventanas (con ventanas 9–10 de confirmación dentro del
    trial). Reproducible entre DIST trials y sesiones (R7).

## 10. Histéresis y regla exacta de subida/bajada (pre-committed)

- Banda muerta alrededor de T: **banda = [0.90·T, 1.10·T]** (umbrales fijos 0.90/1.10).
- **BAJADA (reducir calidad):** si `p99_window > 1.10·T` durante **≥2 ventanas consecutivas (40 s)** →
  `s = next_lower(s)` (una fila en §4). Nunca por debajo de 0.50.
- **SUBIDA (recuperar calidad):** si `p99_window < 0.90·T` sostenido **≥2 ventanas consecutivas (40 s)** y
  s < 1.00 → `s = next_higher(s)`. Nunca por encima de 1.00.
- p99 dentro de banda → **no actuar** (zona muerta = histéresis; evita oscilar en el umbral).
- **Ventana mínima entre cambios = 40 s** (a lo sumo un paso por ventana de 20 s).
- **Oscilación sostenida (definición operacional):** ≥1 reversión de dirección (bajada seguida de subida, o
  viceversa) con p99 volviendo a cruzar el mismo umbral en **≤2 ventanas** de la reversión, en una misma
  trial. Cualquier trial que la presente se marca `OSCILLATION` y alimenta la falsación F3 (§13).

## 11. Métricas: calidad y rendimiento SIEMPRE simultáneos

**Regla de reporte (obligatoria):** cada fila de métrica de rendimiento de una condición incluye las columnas
`scale (s)` y `area_fraction (s²)` de la misma ventana. **Está prohibido** llamar "mejora de rendimiento" a
una reducción de frametime (o de p99) si simultáneamente descendió `area_fraction`. Formulación correcta:
"p99 cayó de X a Y (mayor rendimiento) **a costa de** area_fraction 1.0000 → 0.5625" (reporte conjunto).

Columnas por ventana/trial (registro separado, nunca mezclado):

| Métrica | Definición | Fuente |
|---|---|---|
| scale s | escala efectiva en la ventana | control_scale.txt |
| area_fraction | s² | derivada de s |
| frametime mean | μ de frametimes por-frame | fence, harness |
| frametime median | percentil 50 | fence |
| p95 / p99 | percentil 95 / 99 | fence |
| FPS derivado | 1000 / μ (SIEMPRE etiquetado **DERIVED**) | derivada, NUNCA contador externo |
| overshoot % | fracción de frames con frametime > T (por ventana y por trial) | fence vs T congelado |
| power_avg_full / steady / max_full / max_steady | METRICS-DEFINITIONS.md (obligatorio; N/A si no cumple steady) | sysfs hwmon2 10 Hz |
| SCLK / MCLK | distribución de niveles DPM activos (`*`) + etiqueta DPM | sysfs pp_dpm_* |
| gpu_busy / mem_busy | media en ventana medida | sysfs |
| temp1_input | media (contexto térmico) | sysfs |
| estabilidad | CV (σ/μ) del frametime intra-ventana + SD rodante | fence |
| oscilación | nº de cambios de escala y nº de reversiones por trial | control_scale.txt |

**Definiciones de potencia:** OBLIGATORIO conforme a `METRICS-DEFINITIONS.md` (steady: gpu_busy≥95,
sclk≥1071, mclk≥1500, ≥100 muestras; si no se cumple → N/A). Ventana de Phase 1 (20 s/bloque) y Phase 2
(120 s) son definiciones distintas → cualquier cruce histórico se etiqueta **NOT DIRECTLY COMPARABLE**.

## 12. Criterio estadístico: preguntas A–E y métricas R1–R7 (pre-committed)

**Principio:** el éxito se juzga por la **calidad de regulación** (R1–R7). La comparación con FIXED (E) es
**descriptiva y por preguntas separadas**, y NUNCA es criterio de éxito por sí sola. Ningún umbral nuevo tras
observar datos.

### 12.1 Métricas del lazo — GOVERNOR (por trial de regulación de 120 s; ventanas 1..6)

- **Región establecida (settle):** últimas 2 ventanas de la trial (v5–v6), tras convergencia esperada ≤80 s.
- **R1 — Mantenimiento de target (pregunta A):** `r = mediana(p99_window en settle)/T`. Éxito: en **≥5/6**
  trials `r ∈ [0.90, 1.10]`; además CI bootstrap 90 % de la mediana de r (n=6) ⊂ [0.90, 1.10].
  `r ≈ 1` (target alcanzado); `r < 0.90` = exceso de conservadurismo (calidad menor de la necesaria);
  `r > 1.10` = fallo de target.
- **R2 — Overshoot (pregunta C):** % de frames con frametime > T en settle. Éxito: ≤ 1 % en ≥5/6 trials y
  ≤ 2 % en todas. Se reporta además nº de ventanas con p99_window > 1.10·T (debe ser 0 en settle).
- **R3 — Oscilación (pregunta D):** 0 reversiones sostenidas (§10) en ≥5/6 trials.
- **R4 — Convergencia:** latencia (ventanas) desde el inicio del trial hasta p99 ∈ [0.90T,1.10T] durante
  2 ventanas consecutivas. Éxito: ≤ 4 ventanas (**80 s**) en ≥5/6 trials (ajuste v2.1: el límite de 3
  ventanas/60 s era incompatible con la histéresis de 2 ventanas mínimas de confirmación; 80 s es el
  mínimo estructural coherente con §10).
- **R5 — Reproducibilidad:** CV inter-trial de r (n=6) ≤ 10 %; distribución de r en Sesión 2 vs Sesión 1
  difiere ≤ 15 % en mediana. La predicción de dirección de cada cambio (traza de control_scale.txt) debe
  coincidir con la dirección de p99_window en ≥90 % de las decisiones (traza audible del lazo).
- **R6 — Calidad-óptima / mayor render-scale posible (pregunta B):**
  `Δ = step(s*) − step(s_settled)` (pasos respecto a s* de §6.3; step = posición en S).
  `s_settled` = escala en vigor durante el settle. **Éxito: Δ = 0 en ≥5/6 trials** (converge a la mayor
  escala compatible con T); se reporta además media/mín/máx de s en settle y el tiempo entre 1.00 y s*.
  `Δ ≥ 1` = el governor quedó en calidad menor de la necesaria (conservador); se cuantifica y reporta.
- **R7 — Respuesta reproducible a cambios de carga (DIST):** en las **4** trials de disturbio: latencia de
  primera acción correcta **≤ 2 ventanas** tras el step de subida (t=+60 s) y **≤ 2 ventanas** tras el
  retorno (t=+120 s); y re-incorporación de p99 a banda ≤ 2 ventanas tras cada evento. Éxito: las **4/4**
  trials cumplen ambos umbrales.

### 12.2 Pregunta E — Comparación con FIXED (descriptiva, no gate)

- Diseño pareado: par i = {FIXED_i, GOV_i} (6 pares); p99 de ambas condiciones en sus **últimas 2 ventanas**
  (settle para GOV; últimas 2 de FIXED, estacionario).
- Se reporta: diferencia relativa `(p99_GOV − p99_FIXED)/p99_FIXED` (media y CI bootstrap 90 %) y **el par de
  escalas (s_GOV, s_FIXED = 1.00)** en la misma fila. Un p99 menor en GOV casi siempre va acompañado de
  s_GOV < 1.00: esa reducción **no se presenta como ganancia** exclusiva del governor (regla §11).
- Wilcoxon pareado (n=6) sobre p99: se reporta el valor y el signo, etiquetado **descriptivo**; NO se usa
  como veredicto del mecanismo.
- **Reconciliación con la roadmap (EXP-F4-A, "reducción ≥15 % vs fijo"):** la cifra del 15 % no es criterio
  de éxito; como mucho es el valor ejemplar reportado en E, y la variable que representa sería exactamente
  `(p99_GOV − p99_FIXED)/p99_FIXED` **con s_GOV y area_fraction en la misma fila**. El requisito real de
  rendimiento queda embebido en T (reducción ≥20 % vs natural, §6.2), definido antes de ejecutar.

### 12.3 Veredicto global (pre-committed)

- **HIPÓTESIS APOYADA (governor read-only funciona como mecanismo)** si y solo si: R1 ∧ R2 ∧ R3 ∧ R4 ∧ R5 ∧
  R6 ∧ R7 cumplen sus umbrales (con las tolerancias escritas arriba). Clasificación de cada conclusión:
  **VERIFIED / DERIVED / ESTIMATED / UNKNOWN**; prohibido "PROVEN" para extrapolaciones (§15).
- **INCONCLUSO (limitación documentada)** si una sola métrica falla sin explicación atribuible.
- **FALSADO** si se da el caso de §13.

## 13. Falsación explícita (reconciliada con FUSION-04 §4 y roadmap EXP-F4-A)

FUSION-04 §4 define la hipótesis falsable como "un governor frametime-feedback con histéresis mantiene p99
frametime en workload GPU-bound… sin machacar la calidad percibida" y la roadmap EXP-F4-A como "p99 peor o
inestable → gobernanza no aporta". Operacionalmente, la hipótesis H2 queda **FALSADA** si se cumple
cualquiera de:

- **F1 — No converge:** en **≥2/6** trials de regulación, p99 no alcanza banda [0.90T, 1.10T] sostenida
  (2 ventanas) dentro del tiempo de trial (~120 s), habiendo espacio de escalas disponible (s* > 0.50).
- **F2 — Fuera de target sistemáticamente:** CI bootstrap 90 % de mediana(r) ∉ [0.90, 1.10] **o** r fuera de
  banda en **≥2/6** trials.
- **F3 — Oscilación sostenida:** ≥1 reversión sostenida (§10) en **≥2/6** trials.
- **F4 — No responde reproduciblemente a cambios de carga:** en **≥2/4** trials DIST, la latencia de primera
  acción correcta > 2 ventanas, o sin re-incorporación de p99 a banda tras el retorno.
- **F5 — Curva render-scale→frametime plana / no monótona:** falla el GATE de §6.1.4 (≥2 pasos ≥3 % y
  monotonía). Es el refutador de base: sin curva gobernable no hay mecanismo que validar (además parada D).
- **F6 — No reproducible entre réplicas:** CV inter-trial de r > 10 % o desviación inter-sesión > 15 % SIN
  explicación atribuible (p.ej. drift térmico de la DPM mal caracterizado).

**Regla de veredicto:** F5 por sí solo, **o** ≥2 de {F1,F2,F3,F4,F6} simultáneos ⇒ **FALSADO** ("la
gobernanza no aporta sobre este workload/harness", con datos locales). Un único fallo → INCONCLUSO +
limitación documentada. No se improvisa ninguna solución (parada §14-C/D).

## 14. Criterios de parada (A–D)

Detener **inmediatamente** (documentando el bloqueo) cuando:
- **A.** se hayan completado todas las condiciones y réplicas predefinidas (§4–§7); o
- **B.** el protocolo no pueda ejecutarse sin salir del alcance autorizado (escrituras sysfs, capas del
  sistema, WORKLOAD-SINTETICO/Mesa/kernel, etc.); o
- **C.** aparezca un resultado que requiera contadores, escrituras HW, modificaciones del sistema o una nueva
  clase de experimento (p.ej. el governor "requiere" per-frame counters para ser útil); o
- **D.** un UNKNOWN impida interpretar correctamente los resultados — incluye: fallo de los GATEs de
  calibración (§6.1.4, §6.1.5, §6.3), DPM cambiando mid-run sin explicación, kalm escribiendo (no esperado;
  verificación read-only), o histéresis de la curva open-loop >15 % ascendente↔descendente.

Bajo C/D se documenta el GAP y se detiene. No se inicia ninguna fase posterior.

## 15. Límites de interpretación (prohibiciones del mandato)

NO concluir automáticamente aunque el governor sea reproducible y funcional en este harness:
(1) mejora juegos reales; (2) mejora la RX 550 en general; (3) reduce consumo; (4) evita throttling;
(5) supera a DPM; (6) el frametime es sustituto de contadores; (7) valida FUSION-07/mini-engine F7.
**Tampoco** es un benchmark de "FPS máximo": la velocidad absoluta es contexto, el objeto de estudio es el
mecanismo de feedback. Cualquier mención de potencia con METRICS-DEFINITIONS y etiqueta
NOT DIRECTLY COMPARABLE donde proceda. Clasificaciones: VERIFIED/DERIVED/ESTIMATED/UNKNOWN; sin "PROVEN".

## 16. Entregables (tras ejecución y análisis)

- `EXP-F4-A-RESULTADOS.md`: resultados exactos (curva open-loop P99(s), T y s* congelados, tabla A–E por
  trial, R1–R7 con verificidad, hits/falls, falsación o apoyo, limitaciones y UNKNOWNs restantes, y el
  diff de traza del governor contra los umbrales pre-committed);
- actualización de `MASTER-RESEARCH-STATUS.md` **solo con resultados realmente observados**;
- detenerse: NO avanzar a otra fase automáticamente.