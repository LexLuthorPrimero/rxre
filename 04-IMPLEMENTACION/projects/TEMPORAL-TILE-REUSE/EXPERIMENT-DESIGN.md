# I-02 — EXPERIMENT-DESIGN — TEMPORAL TILE DELTA REUSE

> FASE R-3 — DISEÑO DOCUMENTAL (no ejecución). Objetivo: definir qué se mediría para falsar la hipótesis
> "el skip de tiles por delta temporal ahorra frametime en Polaris12". Antes de implementar, ver README §6:
> el claim se acota a escenas de cámara estática y partial redraw en IMR.
> Integración: brindar inputs a FASE K (benchmark). Uso del harness sintético existente y del runner K.

## 1. HIPÓTESIS FALSABLE (H1)

> **H1:** En Polaris12, para una escena con fracción de tiles cambiados *d*, re-renderizar únicamente los tiles
> cambiados (partial redraw con preservación del frame previo en imagen propia) tiene frametime menor que el
> render full, es decir `T_partial(d) < T_full`, para d por debajo de un umbral crítico.

Sub-hypótesis:
- H1a: la relación es aproximadamente lineal en d: T_partial(d) ≈ a·d + b (b = coste del pass de comparación + overhead).
- H1b: hay un umbral d* tal que para d > d* el compare+overhead supera el ahorro → invertir no rinde.
- H1c: la alineación a bloques DCC (32×32, múltiplo de 256B) evita degradación de compresión (implica enumerar
  decompress/write events via RGP/perfcounters, no solo frametime).
- H1d: el ahorro proviene de shading/fill (no de bandwidth): con ROP/shader-bound, T escala con d; streak: mostrar
  que con MCLK reducido (downclock) la pendiente cambia (bandwidth-bound → menos upside).

## 2. VARIABLES

| Variable | Rango | Notas |
|---|---|---|
| d = fracción de tiles cambiados | 0.0, 0.1, 0.25, 0.5, 0.75, 1.0 | Controlado en escena sintética; método: dinámica de objetos según plantilla de cambio |
| Granularidad de tile | 8×8, 16×16, 32×32, 64×64 | 32×32=baseline; 8×8 alisa HTILE; ver efectos de granularity en compare |
| Método de detección | app-level dirty boxes / compare GPU por tile | Comparar coste e impacto; app-level es la referencia |
| Scene type | cámara estática + 1..N dinámicos; cámara lenta; cámara rápida | Reproduce el dominio de RE (Fig 2) en IMR |
| Passes activos | solo color / color+depth / +post·global | Aísla el efecto del post full-frame |

Métricas (todas por contexto del harness/runner K):
- frametime por frame (μs), CDF/P99.
- densidad de fetch/textura-reads por tile (reporte existente F2).
- eventos de decompress DCC / write color (perfcounters/RGP si disponible en amdgpu; sino marker+contador de driver).
- fill-load (píxeles rasterizados por frame) y shader-load (instr/vertex/fragment).

## 3. ESCENAS SINTÉTICAS (DISEÑO)

- **S0 (control):** cámara estática, 0 objetos dinámicos → d=0 ideal. Marca el límite superior del ahorro y el coste b.
- **S1:** cámara estática, k objetos que rotan/trasladan en regiones disjuntas 32×32 → barrido de d por número de objetos.
- **S2:** cámara en traslación uniforme + pan → mide el colapso de tile-reuse bajo movimiento (disocclusion).
- **S3:** Estrés de post: S1 + Bloom+Tonemap full-frame → aísla el coste irreducible de post.
- **S4:** cámara estática + luz puntual que orbita (cambio de iluminación sin cambio geométrico) → expone el riesgo
  "perceptual change sin geometric change" (sombras/partículas) que PRIOR-ART §3.3 marca como requerimiento de capas.

## 4. DISEÑO EXPERIMENTAL (MATRIZ)

Matriz 4×2×2 cuantitativa para H1/H1d:
- granularidad {16,32} × detección {app, compare} × post {off, on}; 16 celdas; 300 frames/celda; 3 runs.
- Profile del frame: phases [compare (si GPU), draws parciales, resolve, post].
- A cada celda: reportar frametime CDF y componentes por fase.
- Factores de tasa de cambio: d∈{0,0.1,0.25,0.5} para baseline 32 px/app/post-off.

Controles: 
- Sin swapchain de display (fatiga de present no relevante): buffers de imagen propios + semáforo; o swapchain fijo 1-frame.
- Limitación de FPS OFF; VSync OFF; GPU en modo aleatorio? Slaw: fijar SCLK/MCLK según primeros experimentos (F1) para
  comparar cuello CPU vs GPU.
- Calibración de "tile cambiado": definición = ≥1 píxel difiere más de umbral ε (para robustez de cómputo) — nivel por
  canal >8/255; documentar sensibilidad.

## 5. PROCEDIMIENTO DE ANÁLISIS

1. Probar H1: regresión lineal T vs d (intercepto b = overhead de compare). Significancia ±.
2. Calcular umbral d* (igualación de costes). Comparar con d del mundo de la aplicación de referencia (contexto del
   proyecto: escena de escritorio/estática).
3. Confundouse de DCC: correlación entre T y eventos de decompress/write por bloque 256B; esperado: alinear 32×32 =>
  poco decompress; granularidad 8×8 se degrada.
4. Confirmar fuente del ahorro: coger T_full - T_partial del pasada de shading (instruction counters vía profiling del
  harness o tiempos shadow) vs cambio en bandwidth (MCLK swap) → relación con H1d.

## 6. CRITERIOS DE DECISIÓN (GATE)

- **Adoptar:** H1 confirmada con d* ≥ 0.5 y ganancia en la escena de referencia del proyecto ≥ umbral del proyecto
  (definido en FASE K/M project gates, ver MASTER-* ) y sin escalar coste/bug de DCC.
- **Rechazar:** umbral d* < 0.3 (no renta) o H1d dominante (el cuello es bandwidth, no fill → el skip no ataca el issue) 
  o efectos de decompress mayores que ahorro.
- **Parcial:** adoptar solo para HUD/menús (escenario real estático).

## 7. RIESGOS DE EJECUCIÓN PREVISTOS

- Disponibilidad de perfcounters de decompress en amdgpu/RGP para Polaris12: desconocida → fallback = tiempo por fase +
  contadores de driver (amdgpu_perfcounter) si exposibles.
- Semáforo/comunicación CPU-GPU del dirty-map: usa prioridad y GPU-timestamp del harness para no inflar b.
- La preservación del frame previo en imagen propia necesita loadOp LOAD y evitar formats que desactivan DCC
  (CONCURRENT/STORAGE/MUTABLE). Es un diseño, no un cambio de sistema: va en el harness nuevo (fork del existente).

## 8. DEPENDENCIAS

- Harness sintético existente (FASE F1/F2) + runner K (sin instalaciones nuevas; ver MASTER-PLAN FASE K).
- Acceso a amdgpu perfcounters/RGP *si se confirma* (preámbulo de ejecución en FASE G, NO en este diseño).
- Sin instalación de paquetes. Sin cambios al sistema operativo.

## 9. TIEMPO-/BUDGET ESTIMATE (DOCUMENTO)

- Implementación del partial-redraw sintético: medio (harness existente, ~1 región de código nueva).
- Medición: 20–60 min GPU-time (matriz completa).
- Análisis: 1 día.
El coste real de un engine general queda FUERA de alcance (alto) y se marcará como tal.

## 10. ANEXO — FORMULARIO FASE R-3 (MAPA)

- **Hipótesis:** H1/H1a-H1d de §1.
- **Selectividad:** claim acotado: partial redraw temporal en IMR, cámara estática, tile 32×32 alineado DCC/HTILE.
- **Métricas:** frametime CDF/P99 por d; overhead compare; eventos DCC/decompress; density de fetch (F2).
- **Umbral de aceptación:** ver GATE §6.
- **Documentado de estado:** README/POLARIS12-FEASIBILITY sostienen hasta la FASE G/K.