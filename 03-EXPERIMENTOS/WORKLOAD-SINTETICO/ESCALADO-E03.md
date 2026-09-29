# ESCALADO-E03 — Fase de Escalado Controlado (screening de ejes sobre el workload gráfico BASE)

Fecha: 2026-09-21. Binario: `main-graphics` (con `--msaa` añadido; BASE E-03 intacto en
`runs/exploratorio-03-corrected/`). Metodología y evidencia: R-12 en `RESEARCH.md`.

## 1. Metodología (común a toda variante)

- Misma resolución 1920×1080, warmup 5 s, duration 20 s, selección explícita RX 550
  (ICD + verificación de `0x699f`; `MESA_VK_DEVICE_SELECT` era opcional).
- Telemetría 10 Hz (34 s) con pre/post-flight de DPM (sclk/mclk/busy/vram/gtt/power/temp)
  y filtrado de `journalctl` (`GPU fault|VM fault`).
- UNA corrida por configuración (screening; sin significancia estadística).
- Regla de seguridad: ante VM fault, reset, device lost, OOM, asignación imposible, corrupción o
  temperatura anómala → detener ESA configuración y documentar. NO se activó ningún caso.
- Referencia: E-03 BASE = `runs/exploratorio-03-corrected` (15.75 W en régimen estable al inicio de
  la sesión). Como las corridas sucesivas calentaron el entorno (42→64 °C), se re-ejecutó BASE al
  FINAL de la sesión (`A0-base-reeval` = 16.08 W) para medir la deriva térmica: **±0.33 W de ruido
  ambiental** que enmascara cualquier Δ < ~0.4 W por parámetro.

## 2. Indicador de régimen estable

Para aislar la fase activa se filtraron las filas de telemetría con `gpu_busy ≥ 95`, SCLK en el
nivel 7 (`1071Mhz*`) y MCLK en `1500Mhz*` (en régimen de trabajo verdadero, sin arranque ni cola).

## 3. Tabla comparativa (régimen estable)

| Variante (cambio vs BASE) | power_avg | power_max | MCLK (m. 1500) | mem_busy | gpu_busy | fps | frametime_ms | estabilidad |
|---|---|---|---|---|---|---|---|---|
| **E-03 BASE** (referencia, inicio) | 15.75 W | 15.80 | 220/277 | 35.9 % | 100 % | 8.95 | 112.1 | OK (exit 0, 0 faults) |
| **A1** — layers 8 (overdraw 2×) | 15.76 W | 15.80 | 220/292 | 35.9 % | 100 % | 4.50 | 222.8 | OK |
| **A2** — layers 16 (overdraw 4×) | 15.78 W | 15.80 | 225/297 | 36.0 % | 100 % | 2.30 | 442.5 | OK |
| **B1** — FMA 48 | 15.94 W | 16.17 | 219/295 | 35.9 % | 100 % | 8.95 | 112.1 | OK |
| **B2** — FMA 96 | 16.18 W | 16.21 | 221/298 | 35.9 % | 100 % | 8.95 | 112.1 | OK |
| **C1** — tex 6144² (584 MiB) | 16.01 W | 16.18 | 220/295 | 36.0 % | 100 % | 8.95 | 112.1 | OK |
| **C2** — tex 8192² (1.03 GiB) | 16.09 W | 16.27 | 220/282 | 35.9 % | 100 % | 8.95 | 112.0 | OK |
| **D1** — MSAA 4x | 15.94 W | 16.18 | 221/293 | 35.9 % | 100 % | 8.95 | 112.3 | OK |
| **D2** — MSAA 8x | 16.11 W | 16.21 | 220/297 | 35.9 % | 100 % | 8.90 | 112.5 | OK |
| **A0-base-reeval** (BASE al final) | 16.08 W | 16.18 | 216/216 | 35.9 % | 100 % | 8.95 | 112.1 | OK |
| **E1** — FMA96+tex8192+MSAA8 | 16.17 W | 16.27 | 220/297 | 35.9 % | 100 % | 8.90 | 112.4 | OK |

Nota: `gpu_busy` y `mem_busy` informados solo en la ventana de régimen estable (100 % / ~36 %).

## 4. Interpretación por eje

- **A — Overdraw (layers 8/16)**: SIN EFECTO en potencia. El frametime escala EXACTAMENTE lineal
  (112→223→443 ms = 1×, 2×, 4× del trabajo por frame) pero, como el GPU ya estaba al 100 % de
  utilization con SCLK 1071 fijo, el trabajo añadido por frame solo baja el FPS: la potencia queda
  fijada por trabajo-por-segundo = utilización × reloj (constante). Mecanismo: útil para cargar el
  pipeline por frame, inútil para subir W.
- **B — FMA (48/96)**: SIN EFECTO medible. fps idéntico (8.95) y Δpower dentro del ruido térmico
  (B2 16.18 vs base-reeval 16.08). El bucle de FMA tiene dependencias largas (cadena `a→b→c→d→acc`)
  que el scheduler oculta tras la latencia de muestreo; no llena ALU.
- **C — tex-size (6144/8192)**: SIN EFECTO en frametime/potencia (patrón de muestreo normalizado
  fijo → nº de fetches por frame constante; el footprint crece pero la "barrida" por frame no
  desplaza mem_busy). Solo aumenta VRAM real (584 MiB → 1.03 GiB) sin OOM.
- **D — MSAA (4x/8x)**: SIN EFECTO en frametime (~+0.15/+0.4 ms) y potencia. Contrario a lo previsto
  (R-12), el MSAA NO amplificó el tráfico de CB: el triángulo fullscreen cubre TODAS las muestras de
  cada píxel con el MISMO color del único fragment → hardware/RADV deduplican (color fragment / DCC),
  de modo que 8 muestras idénticas no generan 8× escrituras a DRAM.
- **E1 (combinación)**: 16.17 W — igual que la deriva; no aporta sobre los ejes individuales.

## 5. Clasificación de ejes

| Eje | Clasificación | Evidencia |
|---|---|---|
| A — Overdraw | **SIN EFECTO** (potencia); efectivo para frametime (lineal 2×/4×) | 15.76/15.78 vs 15.75/16.08 |
| B — FMA | **SIN EFECTO** | fps idéntico; Δ dentro de deriva térmica |
| C — tex-size | **SIN EFECTO** | fps idéntico; mem_busy clavada 35.9 % |
| D — MSAA | **SIN EFECTO** (deduplicación de muestras idénticas) | frametime casi idéntico a 8x |
| E — Combinación | **SIN EFECTO** aditivo | 16.17 ≤ ruido |

Ninguna variante violó el criterio de seguridad (todas exit 0, 0 faults, DPM restaurado); ninguna se
clasifica INESTABLE ni DESCARTADA por fallo.

## 6. Decisión de fase 2 (configuración más prometedora / candidatas)

- Ningún eje del espacio A–D mueve la potencia sostenida: la placa opera en un **equilibrio de
  latencia**, no de throughput (SCLK 1071 fijo + `mem_busy` 35.9 % + MCLK 1500). La `W_SMU`
  estable (~16 W en régimen) no responde a overdraw/FMA/tamaño-de-textura/MSAA en una sola corrida.
- **Configuración elegida para profundizar en fase 2**: **FMA 96 + tex 8192 + MSAA 8x** (la
  central tendencia más alta, 16.17 W, aunque dentro del ruido) **más una hipótesis nueva**: el
  escalado de potencia requiere cambiar la ESTRUCTURA del fragment, no sus parámetros:
  - romper las cadenas de dependencia FMA (acumuladores independientes) para subir IPC/throughput ALU;
  - aumentar nº de fetches de textura por fragmento (más TMU/DRAM activas) y/o per-sample shading con
    valor distinto por muestra (que sí genera MSAA heterogéneo no deduplicable).
- Se mantiene la hipótesis original en pie: **NO se declara nada sobre alcanzar 27–35 W** — hasta
  ahora, en este espacio de parámetros el workload se sostiene en ~16 W de régimen.

## 7. Resultados negativos y descartados (documentados)

- Overdraw no sube potencia (SIN EFECTO) aunque escala el trabajo por frame perfectamente.
- FMA no aporta (latencia oculta).
- tex-size no desplaza mem_busy (muestreo normalizado fijo).
- MSAA no amplifica banda (muestras idénticas → deduplicación); para forzarlo haría falta
  per-sample shading con valor por muestra, lo que cambia el shader (fase 2).
- Combinación E1: sin efecto aditivo detectable (16.17 ≈ base-reeval 16.08).
- Deriva térmica de la sesión comprobada con BASE al final: toda comparación debe usar la línea
  temporal de referencia adecuada (±0.33 W de confusión térmica).

## 8. Artefactos

`runs/escalado-01/{A0-base-reeval,A1-overdraw-8,A2-overdraw-16,B1-fma-8,B2-fma-16,C1-tex-6144,
C2-tex-8192,D1-msaa-4,D2-msaa-8,E1-comb-fma96-tex8192-msaa8}/{stdout.txt,stderr.txt,telemetria.csv,
pre_flight.txt,post_flight.txt,journal_pres.txt,exit.txt}`.

## 9. Estado

Fase de screening **concluida y detenida** (lo pedido: sin A/B 35 vs 30 W). La selección para fase 2
es la config E1 más la hipótesis estructural del §6; requiere una nueva consulta/autorización para
modificar el shader y re-escalar.

---

# FASE 2 — Modificación estructural del fragment (resultado)

## 10. Investigación (R-13, `RESEARCH.md`)

Ver `RESEARCH.md` §R-13: fragment throughput GFX8 (CU = 4 SIMD×16 lanes, ondas 64, ~350 ciclos de
latencia VMEM en miss L1/L2; TEX unit 1/CU, fetch filtrado 128-bit = 64 ciclos/onda; ocupación↔VGPR↔ILP
según GPUOpen/LLVM/ORNL; RADV: sampleRateShading=TRUE para GFX8; divergencia = paga ambos lados), con
metodología, fuentes URL, hechos, hipótesis e incertidumbres. **Conclusión principal:** el cuello del
workload es el camino FETCH→uso (no ALU: FMA 24→96 no válido; no DRAM: mem_busy 36 %), y las unidades
ociosas de GFX8 están clock-gateadas (whitepaper Polaris: fine-grained clock gating).

## 11. Modificación ÚNICA implementada

`src/fragment2.frag` seleccionable con `--frag fragment2.frag` (default `fragment.frag` = E1; binario
`main-graphics` nuevo md5 `de81536fd94fa51705ac792dff55d6f2`, `main` intacto). Cambio estructural
orientado al trabajo EFECTIVO por fragmento: **8 fetchs independientes realmente consumidos** (2×
E1), 8 cadenas FMA independientes (ILP) alimentadas por cada fetch, salida de entropía dependiente de
TODOS los resultados (no eliminable). Sin branch, sin loops enormes, sin cambios de textura/CB/MSAA/
seeds/duración/resolución/cap/clocks. VRAM idéntica a E1 (1.11 GiB, sin OOM).

## 12. Protocolo y resultado (control E1 antes, F2 después; misma CLI `--fma-iters 16 --tex-size 8192 --msaa 8`)

| Caso | shader | fps | frametime (ms) | power régimen | power max | mem_busy | SCLK/MCLK régimen | estabilidad |
|---|---|---|---|---|---|---|---|---|
| E1 original (runs/escalado-01/E1-comb-*) | fragment.frag | 8.90 | 112.4 | 16.17 W | 16.27 | 35.9 % | 1071/1500 (100 %) | exit 0, 0 faults |
| **F2-control** (mismo día, control) | fragment.frag | 8.90 | 112.4 | 16.13 W | 16.19 | 36.0 % | 1071/1500 (100 %) | exit 0, 0 faults |
| **F2** (intervención, 8 fetchs) | fragment2.frag | 4.55 | **221.7 (1.97×)** | **15.76 W** | 15.81 | **36.0 %** | 1071/1500 (100 %) | exit 0, 0 faults |

Smoke de referencia (640×480, tex 512): E1 14.4 ms/frame ↔ F2 28.3 ms/frame → el nº de fetchs escala
el frametime ~2× de forma exacta (detección del modelo fetch-bound).

## 13. Interpretación y clasificación

- La modificación **SÍ aumentó el trabajo real por fragmento** (2× fetchs a DRAM, todos consumidos) y
  el efecto se manifestó como **frametime 1.97×** — prueba directa de que el límite es la tasa de
  fetchs/latencia de memoria, no ALU ni CB.
- PERO la potencia de régimen NO subió (15.76 vs 16.13 W, Δ −0.4 W dentro de la deriva/noise) y
  `mem_busy` quedó clavado en 36.0 %: al doblar los fetchs por frame, el frametime también se dobla →
  **fetchs por segundo invariante → DRAM por segundo invariante → W al equilibrio del reloj**
  (SCLK 1071 + MCLK 1500 todo el run).
- Clasificación: **AUMENTO REAL DE CARGA (de cómputo por fragmento) y SIN CAMBIO en potencia/mem_busy**
  → para el objetivo del proyecto: **SIN CAMBIO (no discrimina)**. El GPU se autolimita al equilibrio
  de reloj; las unidades ociosas de GFX8 (clock gating) no suman consumo: trabaje o no el fragment,
  la `W_SMU` sostenida es ~16 W con DPM en auto.
- Regla del dueño aplicada: **el cambio no movió la potencia → NO se agrega más complejidad**;
  se documenta y DETIENE. No hay VM fault/reset/device lost/OOM.

## 14. Estado final de fase 2

Concluida y detenida. Registro completo: `RESEARCH.md` (R-13 + F2), Anexo B actualizado, artefactos en
`runs/escalado-01/F2-control-e1-frag/` y `runs/escalado-01/F2-fetch8-ilp/`. Se mantiene la conclusión:
en DPM auto y sin clocks forzados, este workload se sostiene en ~16 W y ningún parámetro o estructura
de fragment probada lo sube por encima de ~16 W sostenido. Sigue SIN ejecutarse el A/B 30 vs 35 W.
