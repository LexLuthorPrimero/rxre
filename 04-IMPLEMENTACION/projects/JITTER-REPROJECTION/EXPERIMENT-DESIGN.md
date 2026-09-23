# I-03 — EXPERIMENT-DESIGN — TAA JITTER AS REPROJECTION SIGNAL

> FASE R-3 — DISEÑO DOCUMENTAL (no ejecución). Objetivo: definir qué se mediría para cuantificar
> la calidad y costo de la **reproyección solo-cámara** (sin MVs por objeto) en Polaris12,
> y cómo la señal resultante alimenta a I-02 (tile locked map).
> Integración directa con I-02 `EXPERIMENT-DESIGN.md` §3/§4.

## 1. HIPÓTESIS (H2)

> **H2a:** La reproyección solo-cámara (depth + matrices + jitter) produce un frame reproyectado tal que, para una
> escena **sin objetos dinámicos**, la diferencia pixel-wise entre el frame reproyectado y el actual es < ε en >99%
> de los píxeles, y el costo total de la señal es < 1 ms en Polaris12 720p.
>
> **H2b:** Para una escena con N objetos en movimiento a velocidad v, la frazione de píxeles donde la
> reproyección solo-cámara produce error > ε crece linealmente (o más rápido) con N·v, y el error se concentra
> en los bordes de disocclusion.
>
> **H2c (para I-02):** Los tiles que la señal solo-cámara marca como "locked" (error < ε) se pueden re-render en
> `T_partial` con calidad idéntica a `T_full`, y el ahorro de frametime es función lineal de la fração de tiles locked.

Sub-hipótesis:
- H2a-b: la señal solo-cámara es **exacta** para cámara estática y **falla proporcionalmente** con movimiento de objetos.
- H2d: el coste de la señal se descompone en depth read (≈ 1 pass de 720p, L2-friendly) + matmul (≈ 1 dispatch CU)
  + comparación (≈ 1 pass de 720p, O(1) por píxel) → el total es ~0.3–0.5 ms (estimación analítica, a medir).

## 2. MÉTODO DE EVALUACIÓN

### 2.1 Ground Truth para la señal
- **Frame reproyectado** = blit de la imagen de historia usando la UV calculada de `p_{t-1} = M_{t-1} · M_t^{-1} · p_t`
  con depth buffer `t`.
- **Error de reproyección** = diferencia absoluta por canal RGB entre frame reproyectado y frame real de referencia.
- **Definición de "locked"**: un tile 32×32 está locked si `mean_error(tile) < ε` y `max_error(tile) < 2ε`
  (con ε = 8/255 = ~3%, definido por defecto; parametrizable).
- **Definición de "dinámico"**: tile no locked.

### 2.2 Escenas sintéticas (mismas que I-02 S0–S4, reutilización)

| Escena | Descripción | F2 |
|---|---|---|
| S0 | Cámara estática, 0 dinámicos | H2a: error ≈ 0 → todos los tiles locked |
| S1 | Cámara estática, k objetos dinámicos (velocidad uniforme v) | H2b: error proporcional a N·v; tiles con error > ε dinámicos |
| S2 | Cámara en traslación uniforme (1°/frame) + sin dinámicos | Cámara se mueve: ¿cuántos tiles siguen lockeados? (test de "cámara lenta") |
| S3 | S1 + bloom/tonemap full-frame | Aísla la contribución de post al error de lock |
| S4 | S1 + luz puntual que orbita (sin movimiento geométrico) | Tiles "estáticos" pero con cambio de iluminación → ghosting si se re-renderizan con historia; mide la fragilidad del lock |

### 2.3 Parámetros a barrer
- Velocidad del objeto v ∈ {0, 1, 2, 4, 8} px/frame (controlada).
- Número de objetos dinámicos k ∈ {0, 1, 3, 8, 20} (para barrido de densidad).
- Threshold ε ∈ {4/255, 8/255, 16/255, 32/255} (análisis de sensibilidad del umbral).
- Jitter mode: sin jitter / jitter estándar TAA (Hilbert 4×4) / jitter random ±0.5px.

### 2.4 Métricas
1. **Accuracy**: mean error, max error, % de píxeles con error < ε, por tile — mapa 2D (heatmap).
2. **Tile lock rate**: % de tiles locked vs N·v → curva de degradación.
3. **Coste total**: frametime del reprojection pass completo (depth read + matmul + sample + comparación) → μs.
4. **Coste descompuesto**: (a) depth read (muestrear depth con bilinear), (b) matmul por tile, (c) sample history, (d) comparación por tile → tiempos por fase.
5. **Para I-02**: correlación entre tile locked → re-rendered vs full render → ahorro de frametime real (se une a H2c).

## 3. DISEÑO EXPERIMENTAL (MATRIZ)

### Matriz A: Evaluación de la señal (I-03)

- Escenas × v × k: 5 escenas × 3 velocidades × 3 valores de k = 45 celdas.
- 300 frames por celda, 3 runs.
- Métricas 1–4 reportadas por celda.
- Hardware: Polaris12, 1071 MHz SCLK fijo (o rangos ya calibrados en F1/F2), VSync OFF, single-thread dispatch.

### Matriz B: Integración con I-02 (crossover)

- Usar S1 con k=5, v=2 como baseline.
- Comparar:
  - (a) Full render de tiles dinámicos + **skip de tiles locked** (reproyección solo-cámara) = I-02 partial.
  - (b) Full render sin skip = baseline.
  - (c) Full render + reproyección solo-cámara de **todos** los tiles (sin skip; solo como referencia de la calidad de la señal).
- Métrica: ahorro de frametime de (a) vs (b), y error pixel-wise de (c) vs (a) en los tiles locked.

## 4. PROCEDIMIENTO DE ANÁLISIS

1. **H2a**: en S0, verificar mean error ≈ 0 y % locked ≈ 100%. El error residual ≈ 0 es la firma de que la señal es exacta.
2. **H2b**: en S1 barrido de k×v, ajuste lineal de error medio vs N·v; extraer pendiente y R².
3. **H2c**: en Matriz B, medir ahorro de frametime de (a) vs (b); ajustar vs fracción de tiles locked.
4. **H2d**: reportar coste de reproyección en μs (decompuesto) → confirmar que es < 1 ms.
5. **Threshold sensitivity**: barrido de ε; reportar curva de % locked vs ε para cada escena.

## 5. CRITERIOS DE DECISIÓN (GATE)

| Resultado | Acción |
|---|---|
| H2a confirmada (< ε en 99%+ píxeles para S0, costo < 1 ms) | Señal usable para I-02; proceder con diseño de tile-skip |
| H2b: degradación lineal con N·v y error se concentra en bordes de disocclusion | Señal predecible; limitar uso de I-02 a escenas de cámara estática |
| H2c: ahorro de frametime ≈ fracción de tiles locked × coste de sombreo de escena completa | Confirmar que el ahorro es real y medible |
| Si H2a falla (error residual alto en S0) | Bug en implementación de reproyección; no avanzar |
| Si costo > 1 ms (H2d) | Señal demasiado cara para Polaris12; recomendar simplificación o abandonment |
| Si degradación con v > 1 px/frame supera 30% de tiles dinámicos para k=1 | I-02 solo viable en escenas casi completamente estáticas; documentar como limitación |

## 6. RIESGOS PREVISTOS

- **Double-sampling de depth**: el depth read es L2-friendly pero hay que preservar el depth buffer entre frames (loadOp LOAD en el tile/skip pass). En Polaris12 con L2 bypass en DB, la primera lectura cuesta DRAM; lecturas sucesivas van a L2 → acceptable.
- **Jitter mode**: el jitter afecta la UV final; si hay un bug en la compensación del jitter (Fwog formula), el error residual en S0 será alto → detectable inmediatamente.
- **Post-processing global**: S3 aísla si bloom/tonemap corrompe la señal; si lo hace, la integración I-02 debe post-procesar antes de la señal de tile-lock (o separar capas, como en I-02 §3).
- **Performance counters**: no hay RGP en Polaris12 (amdgpu); fallback = wall-clock por fase + amdgpu perfcounters si disponibles.

## 7. DEPENDENCIAS

- Harness sintético existente (F1/F2) + runner K.
- NUEVO: un **reprojection pass simple** (~100 líneas de compute): depth read → unproject → project → bilinear sample history → compare. Se implementa en el harness como parte del diseño, no del sistema.
- Sin instalación de paquetes, sin cambio al sistema operativo.

## 8. CONEXIÓN DIRECTA CON I-02

El output de este experimento (tiles locked map + costo de la señal + % de tiles lockeados) se alimenta
directamente como **input del diseño de I-02** (`EXPERIMENT-DESIGN.md` §3):
- S0/S1 locked maps → input a I-02 partial redraw.
- Coste de señal → se suma al costo de comparación de I-02 (§1 de I-02 design).
- % locked → d* (umbral de I-02) se recalcula con la señal real.

Ambos experimentos (I-02 y I-03) comparten escenas y hardware → se pueden ejecutar en la misma sesión
de benchmark (FASE K) con un solo harness extendido.

## 9. FORMULARIO FASE R-3 (MAPA)

- **Hipótesis:** H2a–H2d de §1.
- **Selectividad:** claim acotado: "señal de tile-lock por reproyección solo-cámara, 720p, cámara estática vs lenta vs dinámica".
- **Métricas:** % píxeles con error < ε; % tiles locked; costo reproyección (μs); ahorro de frametime vs I-02.
- **Umbral de aceptación:** H2a confirmada + costo < 1 ms + ahorro medible en Matriz B.
- **Documentado de estado:** este diseño + README/PRIOR-ART sostienen hasta la FASE G/K.