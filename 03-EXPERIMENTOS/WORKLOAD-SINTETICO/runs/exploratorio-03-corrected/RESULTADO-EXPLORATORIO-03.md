# RESULTADO — EXPLORATORIO-03 (Diseño B, configuración base) — VÁLIDA

Fecha: 2026-09-21.
Binario: `main-graphics` (corrección del generador aplicada, ver R-11 / enmienda An.
A de DESIGN-GRAPHICS.md). La corrida previa (tainted) quedó en `runs/exploratorio-03/`.

## Configuración ejecutada (base exacta de DESIGN-GRAPHICS.md, sin cambios)

| Parámetro | Valor | | Parámetro | Valor |
|---|---|---|---|---|
| Resolución | 1920×1080 | | FMA/fragmento | 24 |
| Formato CB | R8G8B8A8_UNORM | | Seeds | 0x13579BDF / 0x2468ACE0 |
| MSAA | 1x | | Warmup | 5 s |
| Texturas | 4 × 4096² (4×64 MiB) | | Duración medida | 20 s |
| Capas (overdraw) | 4 | | Blending | ONE/ONE aditivo |
| Present | OFF (offscreen) | | DCC | ON por defecto |

## Resultado del binario

- `result: EJECUCIÓN_VÁLIDA`; exit code **0**; stderr vacío (0 B).
- `frames: warmup=45 measure=179`; `fps: 8.950`.
- `frametime_ns: min=112013624 avg=112104549 max=112505285 p50=112102507`.
- `vram: heap=1879048192 images=277317656` (264.5 MiB de imágenes, sin OOM ni aborto de
  presupuesto; `sample_counts_cb=15`).

## Validez (criterio ampliado R-11/E-03 §13)

- **0** líneas `GPU fault|VM fault` en `journalctl` en el rango temporal del run
  (`journal_pres.txt` vacío; ventana `[start_wall_ns, end_wall_ns]`).
- DPM intacto: pre_flight == post_flight (`0: 214Mhz *`, `0: 300Mhz *`, gpu_busy=0,
  vram=5.4 MiB, gtt=11.2 MiB), sin resets ni timeouts.
- Identificación computacional con la corrida tainted: misma config, mismo fps 8.950,
  mismo nº de frames y misma reserva de imágenes → misma carga, ahora sin faults.

## Telemetría (277 muestras @ ~10 Hz, rango amplio 32 s)

| Métrica | Valor |
|---|---|
| power (uW) | avg **13 395 054** (13.40 W); min 3 379 000 (piso idle); **max 15 805 000** (15.81 W) |
| temp (mC) | avg 51 090 (51.1 °C); exterior 42→48 °C |
| gpu_busy (%) | avg 80.0 (100 % en régimen; el avg incluye arranque) |
| mem_busy (%) | avg 28.6 (36–49 % en régimen estable) |
| SCLK | 1071 MHz en 223/277 muestras (80.5 %) |
| MCLK | **1500 MHz en 220/277 muestras (79.4 %)** — DRAM ACTIVADA |
| vram_used (B) | avg 234 919 662 (224 MiB) |
| gtt_used (B) | avg 232 532 996 (222 MiB; staging host 256 MiB del upload) |

## Interpretación

- El mecanismo buscado SE ACTIVÓ: MCLK pasó del piso 300 MHz a 1500 MHz durante toda la fase
  activa (R-07: `mem_busy ≥ ~20 %` sostenido sube MCLK) — primera vez en esta sesión.
- draw: 13.4 W avg / 15.8 W pico; por debajo del techo gráfico de la placa (Superposition
  18.8/23.7 W). NO discrimina aún 35 vs 30 W → la corrida es VÁLIDA (no discriminatoria) y queda
  cerrado el objetivo exploratorio de UNA corrida controlada.

## Clasificación final

**VÁLIDA** (ejecutó correcto; 0 faults; telemetría completa; DPM restaurado). El resultado es
insumo para una fase futura que escale parámetros del workload (overdraw/MSAA/FMA/tex-size) hacia el
rango 27–35 W.

## Artefactos

- `stdout.txt`, `stderr.txt` (vacío), `telemetria.csv`, `pre_flight.txt`, `post_flight.txt`,
  `journal_pres.txt` (vacío tras filtrado de `GPU fault|VM fault`).