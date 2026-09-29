# MINI-TEST 7.3-B — RAMP CON GOVERNOR ACTIVO (PLAN, N=2)

**Estado:** EJECUTADO (N=2, 2026-09-23 01:19–01:39) — resultados en
`RESULTADOS-MINITEST-7.3-B.md`. Conclusión: NO cabe DIST íntegro desde ≤50 °C
(ramp medida 0.246–0.252 °C/s). La entrada ≤35 °C es una opción histórica no verificada;
no se declara viable.
**S2/veredicto:** este mini-test NO forma parte de S2 ni del veredicto R-4B. La corrida
posterior S2-v2.3 fue INICIADA/PARADA D; no se reintenta. Sus resultados no entran en T,
s\*, R1–R7 ni en el veredicto.
**Base:** S1-v2.2 íntegra e inmutable (`results/session1-v22/`).

---

## 1. Objetivo (exactamente 7.3-B)

Convertir en **dato** el UNKNOWN de la propuesta v2.3:

> ¿Cuál es la rampa de carga de la RX 550 con el governor activo (bajando render-scale)
> partiendo de una condición térmica controlada (DN-07), y permite esa rampa que R7/DIST
> se ejecute **íntegramente** (200 s, 10 ventanas) sin segmentar y sin confusor térmico nuevo?

## 2. Invariantes (READ-ONLY absoluto)

- NINGUNA escritura sysfs/kernel/contadores. Única escritura: `results/minitest-ramp-gov/`
  y `control_scale.txt` dentro de esa carpeta (mecanismo governor ya autorizado en v2.2).
- NO se modifica `governor.py`, `harness/app_vulkan.c` (y build), `analyze.py`, workload,
  seed `0x5EED0000`, textura, N=4. `T=9.168 ms` y `s\*=0.75` se USAN como entrada
  (FREEZE de S1-v2.2), no se cambian.
- NO se toca Kalm, Mesa, kernel, firmware, DPM, power1_cap (35 W intacto).
- S1-v2.2 y S1 v2.1 no se tocan.

## 3. Condición operativa previa (DN-07) y registro

Antes de CADA réplica y tras ella: **`temp1_input ≤50 °C sostenido ≥30 s ∧ SCLK nivel 0 ∧ P<4 W`**
(6 muestras consecutivas de 5 s). Se registra el tiempo real en `cooldown_prev.tsv` /
`cooldown_post.tsv` (formato v2.2: label, inicio/fin mono_ns, dur_ms, ret_temp/sclk/power).
Además se registra el estado exacto de partida (temp/SCLK/MCLK/power) en `initial_state.txt`.

Como la GPU está operativa a 33 °C, el cooldown previo puede ser corto (≥30 s por protocolo);
NO se fija ningún tope a priori (la condición es operativa, no un tiempo).

## 4. Carga y controlador (idénticos a R7/DIST de v2.2)

- Harness: `governor_harness --mode dist --warm 5 --duration 200 --out <rep>/run
  --control <rep>/control_scale.txt --vendor 0x1002 --device 0x699F --seed 0x5EED0000`
  (el harness aplica N:4→8 a t=+60 s y 8→4 a t=+120 s internos; `--warm 5` excluido).
- Governor: `governor.py --frames run_frames.tsv --control control_scale.txt
  --t0-us <m0> --T-ms 9.168 --duration 200 --trace governor_trace.tsv`
  (mismo binario y reglas: banda [0.90,1.10]·T, 0/ventana de 20 s anclada a t0 absoluto).
- Telemetría: `telemetria.sh 260 <rep>/telemetry.csv` (10 Hz, cubre warm+200 s+cierre).
- Orden de arranque idéntico a run_all_v22 (trial dist): telemetría → harness bg →
  esperar m0 → governor fg → wait harness → wait telemetría.

## 5. Seguridad (monitor pasivo + aborto, sin writes)

- Monitor cada 5 s durante la carga que registra `ts_epoch_s;temp_mC;sclk_nivel;sclk_mhz;power_uW`
  en `monitor_carga.tsv` (solo lectura).
- **Aborto de seguridad:** si `temp ≥ 96.0 °C` (margen de 1 °C bajo `temp1_crit` 97 °C),
  se envía SIGTERM al harness y al governor (parada operativa, NO es una escritura; se
  documenta la causa). En régimen de error, el throttle natural (~92–93 °C, SCLK→551 MHz,
  P cae) estabiliza la temperatura muy por debajo; el corte en 96 solo cubre un escenario
  anómalo. Se registra en `log.txt`.

## 6. Datos a medir (A–I del usuario)

| Letra | Métrica | Fuente |
|---|---|---|
| A | ¿el governor responde correctamente durante la rampa? | governor_trace.tsv (acción p99>hi → LOWER; p99<lo → RAISE) |
| B | latencia en ventanas | primera LOWER tras step +60 (referencia ≤2 ventanas), primera RAISE tras retorno +120 |
| C | ¿el cambio de carga modifica la semántica de las ventanas? | wb/we del trace alineadas a t0 absoluto; revisar steps internos no re-disparados (harness.log: primera aparición de cada step) |
| D | temperatura por ventana y traza | telemetry.csv alineada a m0 (T med/max por ventana) |
| E | SCLK por ventana | telemetry.csv (min, moda, % muestras <1071 por ventana) |
| F | p99 por ventana | governor_trace.tsv + verificación con frames.tsv |
| G | render-scale por ventana | governor_trace.tsv + control_scale.txt |
| H | ¿throttling térmico? | primer tramo sostenido (≥15 muestras) con SCLK<1071; T en ese instante |
| I | reproducibilidad N=2 | comparación rep1 vs rep2 (ramp °C/s, T_max, acciones, latencias, p99 por ventana) |

**Timestamps precisos:**
- inicio (m0): `run_m0.txt` (mono_us + epoch).
- primer cambio de carga (N:4→8): primera línea `[EXP-F4-A] DIST step: N=8` en harness.log
  + primer frame del frames.tsv con `layers=8` (correlación cruzada).
- retorno (N:8→4): primera línea `[EXP-F4-A] DIST retorno: N=4` + primer frame layers=4.
- respuesta del governor / cambio de scale: `governor_trace.tsv` (ventana k, wb/we, scale, action).
- estabilización: ventanas finales del trace con acción=none y p99 en banda.

## 7. Criterio de decisión (clasificación explícita, no "funcionó")

Basado en la evidencia de AMBAS réplicas:

1. **R7 ejecutable íntegramente sin segmentar (v2.3-final con 7.3-B)** si en ambas réplicas
   el trial completo (ventanas de medición v0–v9) se mantiene con SCLK 1071 (sin tramo
   sostenido ≥15 muestras <1071) y T < 90 °C durante todo el trial, con el governor
   respondiendo (primera LOWER tras +60 ≤ 2 ventanas; primera RAISE tras +120 ≤ 2 ventanas)
   — es decir, sin confusor térmico nuevo y con la lógica de ventanas intacta.
2. **R7 con condición térmica de entrada especial** si DIST cabe íntegramente pero roza/excede
   el umbral (T≥90 °C o SCLK<1071 solo en las ventanas finales) → 7.3-A (entrada ≤40 °C),
   con el t0 de ramp medido para calcular cuándo se cruzaría 90 °C.
3. **R7 requiere una modificación procedimental** si la ramp con governor no cabe y hay que
   cambiar el esquema temporal/cooldown intra-trial (no recomendado; documentar por qué).
4. **R7 no medible limpiamente con el diseño actual** si el governor deja de responder, o el
   comportamiento es irreproducible entre N=2, o el throttle aparece en ventanas de medición
   de forma no controlable → 7.3-C (marcación por ventana, DIAGNOSTIC — NOT FOR VERDICT).

## 8. Entregables y post-requisitos

- Datos: `results/minitest-ramp-gov/rep1/`, `rep2/` (telemetry.csv, frames.tsv, m0.txt,
  governor_trace.tsv, control_scale.txt, harness.log, monitor_carga.tsv, pre/post.txt,
  initial_state.txt, cooldown_prev/post.tsv, timings.txt, log.txt).
- Análisis: script read-only en `/tmp/opencode/analyze_minitest_ramp.py` — **PERDIDO / NO VERIFICABLE**.
- Documento: `RESULTADOS-MINITEST-7.3-B.md` (clasificación según §7).
- Verificación read-only pre/post (DPM/kalm/cap) y actualización SOLO de la documentación
  del mini-test (+ estado en MASTER). S2-v2.3 posterior quedó PARADA_D y no se reintenta.
