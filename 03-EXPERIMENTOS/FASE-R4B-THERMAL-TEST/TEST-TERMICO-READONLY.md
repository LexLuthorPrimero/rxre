# INVESTIGACIÓN TÉRMICA READ-ONLY — EXP-F4-A (FASE R-4B)

**Fecha:** 2026-09-22 · **Estado:** DISEÑO + EJECUCIÓN (resultados se completan al cierre)
**Objetivo:** caracterizar experimentalmente, **sin ninguna escritura**, por qué la sesión 1 de
EXP-F4-A alcanzó 92 °C (PARADA D, histéresis 58.3 %) y **cuánto tarda la RX 550 en volver a una
condición térmica comparable a la inicial**, para fundamentar un procedimiento de cooldown defendible
antes de repetir R-4B (NO relanzar S1 todavía; NO modificar el protocolo v2.1; NO crear v2.2).

> Esta investigación es **independiente de EXP-F4-A** y de `results/session1`. NO contamina ni
> modifica los datos de S1. S1 permanece registrada como **PARADA D / INCONCLUSIVA PARA EVALUACIÓN
> DEL GOVERNOR**. `P` en este protocolo significa `W_SMU` de `power1_input`, no vatímetro.

---

## 1. Preguntas a resolver

1. ¿Por qué S1 llegó a 92 °C? (¿throttling del workload vs intervención de Kalm vs DPM normal?)
2. ¿Cuánto tarda el die (edge, `temp1_input`) en degradar SCLK de forma sostenida bajo carga plena?
3. ¿A qué temperatura aparece la degradación sostenida de SCLK (<1071 MHz sostenido)?
4. ¿Cuánto tarda la GPU en volver a una condición comparable a la inicial tras retirar la carga?
5. ¿Es el comportamiento reproducible (patrón vs anomalía)?

## 2. Método de investigación (paso 1 de la orden)

### 2.1 Fuentes del proyecto consultadas (documentación propia primero)

- `MASTER-RESEARCH-STATUS.md` — estado Kalm; régimen histórico E1/E3/E5 [NO REPRODUCIBLE].
- `knowledge.md` — Kalm = `kalmd.py` (4087) + `kalm-lite.py` (4086); `kalm-gpu.service` muerto
  desde 18/09 14:34; DPM auto 1071 MHz; plateau térmico histórico 64 °C / máx 67 °C (escenas ligeras).
- `decisions.md` — **DN-07: política térmica «cooldown a ≤50 °C»** (protocolo frío de Fase B);
  DN-10: Kalm descartado como causa; DN-12/DN-13.
- `evidence.md` — E1/E3/E5 74–92 °C [NO REPRODUCIBLE]; EP-06 a 70–71 °C con 1071 MHz/~11 W.
- `03-EXPERIMENTOS/fase-a-discriminacion-.../RESULTADOS-FASE-A.md` — firma E1/E3 = power-target
  throttling de tarjeta caliente; escenas ligeras no llegan a 75–80 °C.
- `03-EXPERIMENTOS/fase-b-cap-probe-.../RESULTADOS-FASE-B.md` — cooldown ≤50 °C entre estados; from
  frío 37 °C; máx alcanzado 60 °C.
- `03-EXPERIMENTOS/ep06-soak-cap-20260919-205645/RESULTADOS-EP06.md` — soak ligero plateau 64 °C;
  pesado 67 °C; a 70–71 °C SCLK sigue 1071 MHz (el régimen E1 no se reproduce caliente).
- `01-AUDITORIA/AUDIT-001/METRICS-DEFINITIONS.md` — potencias; steady requires gpu_busy≥95,
  SCLK≥1071 MHz, MCLK≥1500 MHz, ≥100 muestras (también aplicables a contexto térmico).
- `03-EXPERIMENTOS/FASE-R4B-GOVERNOR/EXP-F4-A-PROTOCOL.md` — §14-D (histéresis>15 % → parada D).
- `03-EXPERIMENTOS/FASE-R4B-GOVERNOR/EXP-F4-A-RESULTADOS.md` — sección 1B (SESSION 1, parada D).
- `04-IMPLEMENTACION/projects/CLOSED-LOOP-QUALITY-GOVERNOR/EXPERIMENT-DESIGN.md` §4 — «90 °C
  es confound; 96 °C es el abort configurado (DN-07 thermal policy)».
- `04-IMPLEMENTACION/projects/CLOSED-LOOP-QUALITY-GOVERNOR/POLARIS12-FEASIBILITY.md` — temp es señal lenta de
  seguridad; DPM es confounder conocido.

### 2.2 Hechos verificados hoy (read-only, 2026-09-22 23:47)

| Señal | Estado |
|---|---|
| `temp1_input` idle | **39–42 °C** (S1 inició a 40 °C → condición comparable YA restablecida) |
| `temp1_crit` (edge, límite crítico) | **97 °C** |
| `temp1_crit_hyst` | -273150 (sin histéresis/lectura) |
| SCLK activo idle | nivel 0 (214 MHz) |
| MCLK activo idle | nivel 0 (300 MHz) |
| `power1_input` idle | 3.6–3.8 W |
| `power1_cap` | 35,000,000 µW (nunca escrito) |
| fan | `pwm1_enable=2` (auto), `pwm1≈86–103`, `fan1_input` no disponible |
| display | iGPU card0 (HDMI connected); card1 DVI-D/HDMI-A-2 **disconnected** |
| GPU busy ahora | 0 % (idle; nadie más usando card1) |
| harness | `03-EXPERIMENTOS/FASE-R4B-GOVERNOR/harness/build/governor_harness` OK |

**Dato nuevo medido en S1 (ya en `EXP-F4-A-RESULTADOS.md` §1B):** nuestro workload sintético
recalibrado (s=1.00, ~19.4 W) alcanza 81 °C en el bloque 5 del pass p1 y 92 °C sostenido en
p2/p3 con SCLK colapsado a 551 MHz. Las escenas ligeras históricas (9.4–13.6 W) nunca
superaron 71 °C → **el régimen térmico de S1 es nuevo y específico de este workload** (no es
throttling de escenas ligeras ni el régimen histórico E1/E3/E5).

## 3. AUDITORÍA KALM (paso 2 de la orden) — VERIFIED

### 3.1 Qué es cada PID (2026-09-22 23:44–23:47)

| PID | Proceso | Servicio | Estado | Qué escribe (solo lectura de fuentes) |
|---|---|---|---|---|
| 4086 | `/usr/bin/python3 /usr/local/bin/kalm-lite.py` | `kalm-lite.service` | **active (running)** | `/proc/sys/vm.swappiness`, `vm.dirty_ratio`, `vm.dirty_background_ratio` (según PSI de memoria/IO). **Sin contacto con GPU.** |
| 4087 | `/usr/bin/python3 /opt/kalm/kalmd.py` | `kalm.service` | **active (running)** | `/proc/irq/*/smp_affinity_list` (afinidad IRQ por topología). **Sin contacto con GPU/amdgpu.** |
| — | `/usr/local/bin/kalm-gpu` | `kalm-gpu.service` | **inactive (dead) desde 18/09 14:34** (TERM, Duration 11m58) | El binario SÍ escribiría `power_dpm_force_performance_level`, `pp_dpm_sclk`, `pp_dpm_mclk`, `power1_cap` (thermal governor), pero **NO ESTÁ ACTIVO**; sin eventos en journal en 4 días. |

### 3.2 Intervención durante S1 — descartada por evidencia

- Ventana S1 (23:28–23:40) en journal: todos los eventos son `[Kalm] IRQ … no smp_affinity_list,
  omitiendo` (kalmd, CPU-only) + eventos audit de sudo del lanzamiento. **CERO eventos de
  kalm-gpu**, **cero del subsistema amdgpu/drm/sclk/mclk/power/temp**.
- `kalm-gpu.service` no ha estado activo desde el 18/09 (4 días). No pudo intervenir.
- `kalmd.py` (el que conoce la GPU como «GPU class» para IRQ) únicamente escribe afinidad de IRQ
  del kernel (`/proc/irq`), que no afecta DPM/temperatura/potencia.
- ✔ **Conclusión: Kalm NO intervino en S1.** Su estado actual quedó documentado sin tocarlo.

## 4. DISEÑO DEL TEST TÉRMICO (paso 4 de la orden)

### 4.1 Confinamiento (read-only absoluto)

- **Único instrumento de medición:** `FASE-R4B-GOVERNOR/telemetry/telemetria.sh` (10 Hz, ya
  validado en R-4A/R-4C/S1). Solo lectura de sysfs hwmon/amdgpu.
- **Única carga:** `harness/build/governor_harness` en modo `fixed` a **s=1.00 fijo** (el mismo
  workload de Fase 1 de EXP-F4-A; su actuador es render-scale en la app, no escribe nada). **No
  se arranca governor, no hay Phase 2.**
- **Restricciones:** sin sysfs writes, sin registros, sin DPM writes, sin power-cap writes, sin
  Mesa/kernel/firmware, sin rx550-torneo, sin contadores HW. Solo `results/` de ESTA investigación.
- Al terminar cada réplica: cooldown a ≤50 °C (DN-07) y verificación de restauración (DPM
  idle + cap 35 W + kalm idénticos pre/post).

### 4.2 Variables medidas (todas via telemetria.sh, 10 Hz)

`ts_ns (epoch)`, `power_uW`, `temp_mC` (edge), `gpu_busy`, `mem_busy`, `vram_used`, `gtt_used`,
`sclk_level`, `sclk_mhz`, `mclk_level`, `mclk_mhz` + deriva `sclk_mhz` por ventanas de 5 s y
`temp` por tramos. Referencia temporal de la carga: `run_m0.txt` (línea 1 = mono µs, línea 2 =
epoch s) del harness.

### 4.3 Procedimiento por réplica (script `run_thermal_replicate.sh REP`)

1. **Pre-check/snapshot:** gpu_busy=0, display en Intel, DPM idle, cap 35 W, kalm PIDs →
   `runs/repREP/pre.txt`.
2. **Telemetría continua** (una sola corrida sin huecos cubriendo calentamiento + cooldown):
   `telemetria.sh 1500 telemetry.csv &` (≈25 min tope).
3. **Carga:** harness `fixed s=1.00, warm 0, duration 300 s` (5 min a carga plena) con
   `VK_ICD_FILENAMES` radeon. Registra inicio/fin reales.
4. **Cooldown (pasiva, pwm auto):** polling read-only de `temp1_input` cada 5 s hasta condición
   de retorno — **temp ≤ 50 °C sostenido ≥30 s** (DN-07) **Y** nivel SCLK activo = 0 (214 MHz)
   **Y** power < 4 W. Tope 900 s; registrar Δt fino mediante el CSV real (no del polling).
5. **Post/snapshot:** `runs/repREP/post.txt` idéntico al pre; kill telemetría.
6. **Análisis read-only** (`analyze_thermal.py`) sobre `telemetry.csv` + tiempos reales:
   A temperatura inicial; B SCLK inicial; C temp vs t; D SCLK vs t; E instante de degradación
   sostenida de SCLK (<1071 MHz sostenido ≥10 muestras consecutivas con busy≥95); F temp en ese
   instante; G tiempo hasta 92 °C (y hasta temp1_crit); H tiempo de recuperación (fin carga →
   condición de retorno); I temp/SCLK al final del cooldown; J reproducibilidad (comparar REP1 vs
   REP2: ΔT(R), Δt_degradación, Δt_recovery).

### 4.4 Replicación (paso 7)

**N=2 réplicas** consecutivas (cada una arranca desde la condición de retorno de la anterior,
es decir desde ≤50 °C / SCLK 214 / power <4 W, estado comparable al inicio). Suficiente para
distinguir patrón reproducible vs anomalía sin prolongar innecesariamente el uso de GPU. Si la
dispersión entre REP1 y REP2 fuera grande (>30 % en tiempos clave), se documenta como no
reproducible y NO se aumenta N sin autorización.

### 4.5 Condición objetiva de «estado comparable al inicial» (paso 9)

Definida **pre-experimentalmente** con la documentación del proyecto y verificada con los datos:

> **RETORNO = `temp1_input ≤ 50 °C` sostenido ≥30 s ∧ SCLK activo = nivel 0 (214 MHz) ∧
> `power1_input < 4 W`.** Justificación: DN-07 fija cooldown a ≤50 °C para iniciar experimentos;
> 50 °C deja margen de ~47 °C bajo el límite de abort configurado de 96 °C y ~42 °C bajo
> el punto de degradación observado (≥89–92 °C) en los casos ensayados. Esto **no garantiza**
> que un siguiente bloque reentre en régimen pleno; la exclusión se decide por las gates
> y la telemetría de cada corrida.
> La verificación post-réplica se limita a los casos ensayados; no constituye garantía general.

## 5. Interpretación separada (paso 6)

| Factor | Cómo se separa |
|---|---|
| Calentamiento del workload | temp/SCLK/power en la ventana de carga (harness activo) sobre curva lisa desde 39–42 °C |
| Throttling térmico | degradación SCLK sostenida coincidiendo con temp≈90+ °C, ausente en frío |
| Intervención de Kalm | excluida por §3 (journal + código + estado del servicio) |
| Comportamiento DPM normal | nivel SCLK por ventanas; rampa DPM entre bloques ≤1 nivel es normal; colapso a 551 sostenido = throttle |

## 6. Entregables de esta fase (paso 11–12)

- Este documento (diseño + fuentes + metodología).
- `runs/rep1/`, `runs/rep2/` con `telemetry.csv`, `pre.txt`, `post.txt`, `log`.
- `RESULTADOS-TEST-TERMICO.md`: A–J, curvas temp(t)/SCLK(t), separación de factores, tabla de
  tiempos por réplica, **propuesta de cooldown basada en datos**, riesgos/confusores.
- **NO** se modifica `EXP-F4-A-PROTOCOL.md` (v2.1 queda intacta); **NO** se crea v2.2; **NO** se
  relanza S1; **NO** se detiene Kalm. Tras entregar, detener y preguntar.

## 7. Riesgos y confusores declarados

- `power1_input` es estimador SMU ruidoso (nota METRICS-DEFINITIONS); se usa como contexto, la
  métrica principal térmica es `temp1_input` (edge).
- La cooldown depende del entorno (fan PWM auto, caja); la condición de retorno es operativa por
  temp/SCLK/power, no por tiempo absoluto.
- ventilación ambiente no controlada → RÉPLICAS lo evalúan; si difieren, se resta INRIA y se nota.
- El harness no recoge frames durante el cooldown (no hay carga) → solo telemetría.
- NO se evalúa el governor aquí: esta fase solo caracteriza el régimen térmico del workload.
