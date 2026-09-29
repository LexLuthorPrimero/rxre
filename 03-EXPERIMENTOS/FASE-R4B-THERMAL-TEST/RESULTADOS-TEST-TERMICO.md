# RESULTADOS — TEST TÉRMICO READ-ONLY (EXP-F4-A / FASE R-4B)

**Fecha:** 2026-09-23 (00:06) · **Estado:** COMPLETADO (N=2 réplicas)
>
> **Nota de reconciliación 2026-09-24:** las cifras `power1_input`/`P` son `W_SMU`
> (estimador SMU), no vatímetro. Este test no evalúa el governor.
**Diseño/metodología:** `TEST-TERMICO-READONLY.md` (fuentes del proyecto, auditoría Kalm,
confinamiento read-only, condición de retorno, replicación).

> Investigación **separada** de EXP-F4-A. S1 permanece: **PARADA D / INCONCLUSIVA PARA EVALUACIÓN
> DEL GOVERNOR**. Este documento NO evalúa el governor.

---

## 1. Auditoría Kalm (VERIFICADO — ver TEST-TERMICO-READONLY.md §3)

| PID | Proceso | Servicio | Estado | Interacción con amdgpu |
|---|---|---|---|---|
| 4086 | `kalm-lite.py` | `kalm-lite.service` | active | **NINGUNA** (solo `vm.swappiness`, `vm.dirty_*` vía `/proc/sys`) |
| 4087 | `kalmd.py` | `kalm.service` | active | **NINGUNA** (solo afinidad IRQ `/proc/irq/*/smp_affinity_list`) |
| — | `kalm-gpu` | `kalm-gpu.service` | **inactive (dead) desde 18/09 14:34** | el binario escribiría `pp_dpm_*`/`power1_cap`, pero **no está activo**; 0 eventos en 4 días; 0 eventos en la ventana S1 |

**Conclusión: Kalm NO intervino en S1 ni en este test.** Documentado sin tocarlo.

## 2. Restauración read-only (verificada en ambas réplicas)

- `pre.txt` ↔ `post.txt`: niveles DPM activos **idénticos** (`ff9e8280bd` en ambas réplicas),
  `power1_cap` = 35 W nunca escrito, Kalm 4086/4087 intactos, SCLK/MCLK a nivel 0 (214/300 MHz)
  al cierre. GPU devuelta a estado idle comparable al inicial (≤50 °C, busy 0).

## 3. Métricas por réplica (A–J)

| Métrica | REP1 | REP2 | Interpretación |
|---|---|---|---|
| A. Temp inicial (°C) | 36.8 | 48.0 | REP2 parte 11 °C más caliente (retorno a ≤50 °C, no a frío) |
| B. SCLK inicial (MHz / nivel) | 214 / 0 | 214 / 0 | iguales |
| C. Temp vs tiempo (carga) | 61→70→77→83→88 °C @30..150 s | 62→70→78→84→89 °C @0..120 s | pendientes casi idénticas |
| D. SCLK vs tiempo (carga) | **1071 MHz sostenido** hasta 90 °C | **1071 MHz sostenido** hasta 90 °C | sin degradación ≤90 °C |
| E. t degradación sostenida SCLK (<1071, busy≥95, 10 muestras) | **NO OBSERVADO ≤90 °C** (corte por diseño) | **NO OBSERVADO ≤90 °C** | degradación solo ≥~92 °C (evidencia S1) |
| F. Temp en ese instante | — | — | S1: **92 °C** (p2/p3: SCLK 734→551 MHz sostenido) |
| G. Tiempo hasta 90 °C (s) | **169** (desde 37 °C) | **136** (desde 48 °C) | 90 °C no alcanzado a 92/97 en el test (corte) |
| H. Tiempo de recuperación: fin carga → retorno (s) | **270** | **255** | Δ=15 s (5.6 %) → reproducible |
| I. Temp/SCLK/`W_SMU` al final del cooldown | 49 °C / 214 MHz / 3.4 W | 49 °C / 214 MHz / 3.7 W | condición retorno alcanzada |
| J. Reproducibilidad | — | — | tasa ramp: 0.315 vs 0.310 °C/s (±1.6 %); recuperación ±5.6 % |

**Potencias (contexto, METRICS-DEFINITIONS):** `W_SMU` de carga ≈ **23.5 W** (~22.4 W media),
cap 35 W → **el cap no liga** en este test. La categoría thermal/power no se atribuye más
allá de la evidencia; el cap solo liga si la demanda alcanza el cap (aquí 23.5 < 35).

## 4. Curvas representativas (10 Hz; promediadas por tramo)

### 4.1 Heating (harness fixed s=1.00, 1920×1080, SCLK 1071 MHz durante todo el tramo)

| t (s) | REP1 temp (°C) | REP2 temp (°C) |
|---|---|---|
| 0 | 51 | 62 |
| 30 | 61 | 71 |
| 60 | 69 | 78 |
| 90 | 77 | 84 |
| 120 | 84 | 89 |
| 150 | 88 | — (ya cortada al 90 °C a los 136 s) |

### 4.2 Cooldown (pasivo, PWM auto; SCLK cae a 214 MHz al quitar carga)

| t desde fin carga (s) | REP1 temp (°C) | REP2 temp (°C) |
|---|---|---|
| 0 | 74 | 75 |
| 60 | 65 | 65 |
| 120 | 58 | 57 |
| 180 | 53 | 52 |
| 240 | 50 | 49 |

## 5. Separación de factores (VERIFIED)

| Factor | Evidencia |
|---|---|
| Calentamiento del workload | curva lisa desde 37–48 °C bajo s=1.00; 0.31 °C/s; power_max 23.5 W |
| Throttling térmico | ausente ≤90 °C (SCLK 1071 sostenido); en S1 degradación sostenida solo ≥92 °C |
| Intervención de Kalm | descartada (§1: código + journal + servicio dead) |
| DPM normal | rampa de nivel con la carga (214→1071 en ~1 s de arranque); sin colapsos ≤90 °C |

## 6. PROPUESTA DE COOLDOWN BASADA EN DATOS

Condición de retorno (objetiva, DN-07, alcanzada en ambas réplicas):
**`temp1_input ≤ 50 °C` sostenido ≥30 s ∧ SCLK nivel 0 ∧ power < 4 W**.
Tiempo medido: **255–270 s (~4.3–4.5 min) desde ~74 °C**, extrapolando desde 90 °C ≈ 270–300 s.

**Recomendación para repetir R-4B (requiere autorización; no se modifica v2.1 sin tu orden):**

1. **Entre passes de FASE 1 (p1→p2→p3):** insertar cooldown pasivo hasta la condición de
   retorno (255–270 s medidos). En S1 el colapso apareció en p2 (6º bloque), empezando p2 con el
   die a ~81 °C tras p1 sin pausa → cooldown después de cada pass evita el punto de degradación.
2. **Alternativa mínima (si se quiere preservar duración):** cooldown solo **entre p1 y p2** y
   **entre p2 y p3** (2 pausas de ~4.5 min), que es exactamente donde S1 degradó.
3. **No es necesario** cooldown intra-pass (bloques de 20 s): en el test, 5 bloques equivalentes
   (~150 s) llevan de 37→88 °C, por debajo del umbral de degradación (92 °C) — pero el 5º bloque
   quedaría al borde (88–90 °C). Si se quiere margen: cooldown también entre bloque 4 y 5 de cada
   pass (medir primero el efecto, no asumir).
4. **FASE 1 completo sería repetible sin throttle si todos los passes parten de ≤50 °C**, como
   observación limitada al protocolo y workload ensayados; no es una garantía general de seguridad.
   En el tramo p1 (40→81 °C en S1) no se observó degradación; el problema observado fue la acumulación p1→p2 sin pausa.

**Riesgos/confusores declarados:** ventilación ambiente no controlada (fAN PWM auto) → la
condición es operativa (temp/SCLK/power), no un tiempo fijo; `power1_input` es estimador SMU
ruidoso (solo contexto); N=2 réplicas realizadas y consistentes; NO se aumentó Medición.

## 7. Limitaciones / NO demostrado

- Este test **NO alcanzó** 92–97 °C (corte por diseño a 90 °C para no estresar innecesariamente)
  → la cola alta de la curva (91→97 °C) y el tiempo hasta `temp1_crit` (97 °C) quedan **UNKNOWN**
  medidos en este test; el punto de degradación sostenida (E/F) se toma de S1 (92 °C) y NO está
  revalidado aquí.
- No hay cooldown forzado por ventilador/pwm (sin writes) → solo cooldown pasivo del SRP.
- La extrapolación 90→50 °C (270–300 s) es del tramo medido 74→50 (240 s) + 16 °C adicionales;
  puede sobreestimarse el primero ~15 s (ver REP2).

## 8. Entregables / estado

- Datos: `runs/rep1/`, `runs/rep2/` (telemetry.csv 10 Hz, pre/post, timings, harness.log).
- **NO** se modificó `EXP-F4-A-PROTOCOL.md` (v2.1 intacta), **NO** v2.2, **NO** se relanzó S1,
  **NO** se tocó Kalm, **NO** cambió ninguna condición experimental de R-4B.
- Pendiente: tu decisión sobre cooldown / período de repetición (ver pregunta del agente).
