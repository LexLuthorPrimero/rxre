# RESULTADOS — MINI-TEST 7.3-B: RAMP CON GOVERNOR ACTIVO (N=2)

**Fecha:** 2026-09-23 (01:19–01:39) · **Estado:** COMPLETADO (N=2 réplicas, 0 aborts)
**Plan/diseño:** `EXP-F4-A-MINITEST-RAMP-GOV-PLAN.md`
**Datos:** `runs/minitest-ramp-gov/rep1/`, `rep2/`
**Alcance:** investigativo, **NO forma parte de S2**. Resultados NO entran en T, s\*, R1–R7,
ni en el veredicto de R-4B. S1-v2.2 permanece íntegra e inmutable.

> **Pregunta que se resuelve:** ¿Cuál es la rampa real de la RX 550 con el governor activo
> (bajando render-scale) desde una condición térmica controlada DN-07, y permite esa rampa
> que R7/DIST se ejecute íntegramente (200 s, 10 ventanas) sin confusor térmico nuevo?

---

## 1. Condiciones de ejecución (idénticas a R7 en ambas réplicas)

| Parámetro | Valor | Nota |
|---|---|---|
| Harness | `--mode dist --warm 5 --duration 200` seed `0x5EED0000` | steps N:4→8→4 internos a t=+60/+120 s |
| Governor | `governor.py` T=9.168 ms, banda [8.251, 10.085] ms, ventana 20 s | binario y reglas sin tocar |
| entrada térmica (DN-07) | `temp ≤50 °C s30s ∧ SCLK nv0 ∧ P<4 W` | cooldown previo 30 s (GPU ya fría) |
| telemetría | `telemetria.sh` 10 Hz, 260 s | read-only |
| aborto de seguridad | temp ≥ 96 °C → SIGTERM | **0 activaciones** |
| verificación read-only | pre/post DPM+kalm | **idénticas en ambas réplicas (`ff9e8280bd`)** |

Entrada térmica real: **REP1 = 33 °C** (GPU venía del análisis previo), **REP2 = 45–46 °C**
(retorno DN-07 real). SCLK/MCLK iniciales 214/300 MHz nivel 0, P < 4 W (requisito cumplido).

## 2. Semántica temporal (respuesta a la pregunta C) — VERIFIED

Los pasos de carga caen EXACTAMENTE en las ventanas esperadas, en ambas réplicas:

| Evento | t programado | t en harness.log | Ventana afectada | layers en frames.tsv |
|---|---|---|---|---|
| step N:4→8 | +60 s | `DIST step: N=8 (t=+60.0 s)` | v3 (60–80 s) | v0–v2: 4 · v3: {4,8} · v4–v5: 8 |
| retorno N:8→4 | +120 s | `DIST retorno: N=4 (t=+120.0 s)` | v6 (120–140 s) | v6: {4,8} · v7–v9: 4 |

- Las ventanas del governor permanecen ancladas a `t0` absoluto (m0) sin re-anclaje.
- **p99 del governor_trace == p99 de frames.tsv en TODAS las ventanas** (coincidencia 1:1,
  p. ej. v3=18.62/18.62, v6=6.96/6.96, v9=10.62/10.62 REP1) → la carga no distorsiona la
  señal de la ventana. **La semántica de ventanas NO cambia por el cambio de carga.**

## 3. Respuestas A–I (evidencia por ventana)

### 3.1 REP1 (entrada 33 °C)

| v | w_s | p99 fr/tr (ms) | scale aplicada | action | T med/max (°C) | P med (W) | sclk min (MHz) | %<1071 |
|---|---|---|---|---|---|---|---|---|
| 0 | 0–20 | 11.45 | 1.00 | none | 48.5 / 52.0 | 22.04 | 1071 | 0 |
| 1 | 20–40 | 11.46 | 1.00→0.87 | LOWER | 55.1 / 58.0 | 22.09 | 1071 | 0 |
| 2 | 40–60 | 11.18 | 0.87 | none | 61.1 / 64.0 | 21.72 | 1071 | 0 |
| 3 | 60–80 | 18.62 | 0.87→0.75 | LOWER | 66.7 / 69.0 | 21.94 | 1071 | 0 |
| 4 | 80–100 | 18.53 | 0.75 | none | 71.7 / 74.0 | 21.96 | 1071 | 0 |
| 5 | 100–120 | 13.89 | 0.75→0.62 | LOWER | 76.6 / 79.0 | 22.07 | 1071 | 0 |
| 6 | 120–140 | 6.96 | 0.62 | none | 81.0 / 83.0 | 22.15 | 1071 | 0 |
| 7 | 140–160 | 4.90 | 0.62→0.75 | RAISE | 85.0 / 87.0 | 22.26 | 1071 | 0 |
| 8 | 160–180 | 7.02 | 0.75 | none | 89.1 / **91.0** | 22.63 | 1071 | 0 |
| 9 | 180–200 | 10.62 | 0.75 | none | 91.9 / **92.0** | 20.88 | **734** | **73.0** |

- T≥90 °C: **t≈171.9 s** · T≥92 °C: **t≈182.6 s** · primer tramo SCLK<1071 sostenido (≥15):
  **t≈187.1 s a 92 °C**.
- Ventanas limpias (SCLK 1071 mantenido ∧ T<90 °C): **v0–v7** (160 s). v8 roza T=91 con SCLK
  aún 1071; v9 ya degradada (73 % <1071). → **las últimas 1–2 ventanas del trial NO son válidas.**

### 3.2 REP2 (entrada 45 °C)

| v | w_s | p99 fr/tr (ms) | scale aplicada | action | T med/max (°C) | P med (W) | sclk min (MHz) | %<1071 |
|---|---|---|---|---|---|---|---|---|
| 0 | 0–20 | 11.47 | 1.00 | none | 58.9 / 62.0 | 22.04 | 1071 | 0 |
| 1 | 20–40 | 11.45 | 1.00→0.87 | LOWER | 65.1 / 68.0 | 22.20 | 1071 | 0 |
| 2 | 40–60 | 11.16 | 0.87 | none | 70.3 / 73.0 | 21.97 | 1071 | 0 |
| 3 | 60–80 | 18.63 | 0.87→0.75 | LOWER | 75.5 / 78.0 | 22.08 | 1071 | 0 |
| 4 | 80–100 | 18.52 | 0.75 | none | 80.2 / 83.0 | 22.11 | 1071 | 0 |
| 5 | 100–120 | 13.91 | 0.75→0.62 | LOWER | 84.6 / 87.0 | 22.41 | 1071 | 0 |
| 6 | 120–140 | 6.96 | 0.62 | none | 88.5 / **91.0** | 22.28 | 1071 | 0 |
| 7 | 140–160 | 7.33 | 0.62→0.75 | RAISE | 91.7 / **92.0** | 21.00 | **734** | **60.9** |
| 8 | 160–180 | 21.47 | 0.75 | none | 92.0 / **92.0** | 17.05 | **551** | **100** |
| 9 | 180–200 | 27.39 | 0.75→0.62 | LOWER | 92.0 / **92.0** | 15.25 | **551** | **100** |

- T≥90 °C: **t≈134.8 s** · T≥92 °C: **t≈144.4 s** · primer tramo SCLK<1071 sostenido:
  **t≈149.5 s a 92 °C**.
- Ventanas limpias: **v0–v5** (120 s). v6 roza 91 °C con SCLK 1071; v7–v9 degradadas
  (60.9 % → 100 % <1071, SCLK cae 734→551). → **la mitad final del trial NO es válida**
  (entrando 12 °C más caliente, la re-incorporación de R7 ocurre ya degradada).

### 3.3 Respuestas A–I resumidas

| # | Pregunta | Respuesta (evidencia) |
|---|---|---|
| A | ¿el governor responde durante la rampa? | **SÍ.** Acciones correctas y alineadas: LOWER tras p99>hi (v1/v3/v5), RAISE tras p99<lo (v7). Escala 1.00→0.62→0.75 en ambas réplicas. |
| B | latencia en ventanas | **Dentro de la especificación.** Primera LOWER en v1 (a 20–40 s, máx. esperado 2 ventanas); primera LOWER post-step en v3 (60–80 s); primera RAISE post-retorno en v7 (140–160 s). |
| C | ¿el cambio de carga modifica la semántica? | **NO.** Steps a +60/+120 exactos; ventanas ancladas a t0; trace vs frames 1:1 (§2). |
| D | temperatura | REP1 33→92 °C (max 160 s limpias); REP2 45→92 °C (max 120 s limpias). T<90 °C hasta ~135–172 s según entrada. |
| E | SCLK | 1071 sostenido en todas las ventanas "limpias"; degradación solo tras alcanzar ~92 °C (734/551 MHz). |
| F | p99 | Curva esperada a 1071: v0 11.45 (s=1.00) → v2 11.18 (0.87) → v3-4 18.6 (N=8) → v6 6.96 → v7 4.9 ms; en v9 REP2 27.4 ms = artefacto térmico (551 MHz), no propiedad del governor. |
| G | render-scale | 1.00 → 0.87 → 0.75 → 0.62 → (retorno) 0.75; mismo perfil en N=2. |
| H | throttling térmico | **SÍ se alcanza** en ambas réplicas ANTES del final del trial (REP1 v9, REP2 v7–v9). El governor NO evita el throttle en un DIST de 200 s desde ≤50 °C. |
| I | reproducibilidad N=2 | Ramp efectiva **0.252 vs 0.246 °C/s (Δ=2.1 %)**; T_max 92 °C ambas; perfil de acciones/escalas idéntico hasta la degradación; la diferencia es la T de entrada (33 vs 45 °C) que adelanta el cruce de 90/92 °C (~37 s). |

## 4. Conclusión del mini-test (la ramp real con governor activo)

**La ramp efectiva con governor activo es 0.245–0.252 °C/s — NO la estimación ≤0.21 °C/s
que propuso 7.3-B como condición de "cabe".** La bajada de escala reduce la potencia media
solo ~2–5 % (P_med 22.0–22.6 W ≈ 23.5 W del N=2 a s=1.00) porque a SCLK 1071 el workload
sigue demandando potencia aunque baje la resolución de render; el governor **aplana la curva
térmica parcialmente** (0.31 → 0.25 °C/s, ~19 % más lenta), pero **NO lo suficiente**.

Con la ramp medida, el presupuesto térmico (lineal, margen a 90 °C) es:

```
t_90 ≈ (90 − T_entrada) / 0.249  °C/s
  desde ≤50 °C  → ~160 s   (< 200 s → NO cabe; confunde el final)
  desde ≤40 °C  → ~201 s   (≈ el borde; último ~1 s roza, sin margen)
  desde ≤35 °C  → ~221 s   (cabe con 20 s de margen)
```

---

## 5. RESPUESTA AL CRITERIO DE DECISIÓN FINAL (plan §7)

**El mini-test NO demuestra que DIST pueda ejecutarse íntegramente desde ≤50 °C sin
confusor térmico nuevo.** Por lo tanto, **NO se prepara una v2.3-final con 7.3-B como
único tratamiento de DIST**. La clasificación formal, según el plan:

1. **R7 íntegro SIN segmentar y desde entrada ≤50 °C → NO demostrado.** En ambas réplicas
   el trial se degrada antes de la ventana 10 (REP1 v9, REP2 v7–v9). Una entrada ≤50 °C
   estándar NO basta para 200 s con la ramp medida.
2. **R7 con condición de entrada térmica especial → VIABLE, ahora cuantificado (7.3-A).**
   Con ramp medida 0.246–0.252 °C/s, **entrada ≤35 °C** deja hueco real (t_90 ≈ 221 s >
   200 s); **entrada ≤40 °C** queda en el filo (t_90 ≈ 201 s, sin margen). Consecuencias:
   cooldown previo a 35 °C (tramo 50→35 °C no medido; el cooldown post alcanzó 49 °C en
   ~260–280 s; el tramo final 49→35 °C tarda más, a registrarse en tiempo real con
   anti-deadlock 60 min); riesgo de no alcanzar ≤35 °C por ventilación ambiente → caer a 7.3-C
   con causa documentada (decisión pre-registrada).
3. **R7 requiere una modificación procedimental → NO ENCONTRADA NECESARIA.** El governor
   responde correctamente en régimen 1071; el único factor es el presupuesto térmico del
   trial de 200 s → se controla con la condición de entrada (procedimental, sin tocar código).
4. **R7 no medible limpiamente con el diseño actual → FALSO con la entrada adecuada.** El
   controlador funciona y la semántica es íntegra; el problema es puramente de presupuesto
   térmico del tramo final, resoluble con 7.3-A.

**Recomendación (con datos, sin ejecutar nada más):** adoptar **7.3-A con entrada ≤35 °C**
(no ≤40 °C, que queda sin margen según la ramp medida) para DIST₁/DIST₂, manteniendo la
regla de validación por ventana (T>90 °C o SCLK<1071 → `THERMALLY CONFOUNDED`) como red de
seguridad, y **7.3-C** como plan B pre-registrado si la entrada ≤35 °C es inalcanzable.

---

## 6. Verificación read-only (cumplida)

- ±0 escrituras sysfs/kernel: `power1_cap` 35 W intacto; `pp_dpm_sclk/mclk` idénticos
  pre/post en ambas réplicas (hash `ff9e8280bd`).
- Kalm 4086/4087 intactos y sin interacción con la GPU (auditoría TEST-TERMICO §1 vigente).
- 0 aborts de seguridad; GPU devuelta a idle (busy 0, SCLK nv0, T≈44 °C, P≈3.4 W).
- S1-v2.2 (`results/session1-v22/`) y S1 v2.1 (`results/session1/`) NO se tocaron.
- governor.py / harness / analyze.py / workload / seeds sin modificar.

## 7. Archivos y estado

- `runs/minitest-ramp-gov/rep{1,2}/`: telemetry.csv, frames.tsv, m0.txt, governor_trace.tsv,
  control_scale.txt, harness.log, governor.log, monitor_carga.tsv, pre/post.txt,
  initial_state.txt, cooldown_prev/post.tsv, timings.txt, log.txt.
- Análisis: `/tmp/opencode/analyze_minitest_ramp.py` (read-only).
- **Pendiente de decisión del usuario:** (a) elegir DIST 7.3-A (≤35 °C) / 7.3-C / combinación;
  (b) autorizar la ejecución de S2 bajo v2.3 con esa elección.