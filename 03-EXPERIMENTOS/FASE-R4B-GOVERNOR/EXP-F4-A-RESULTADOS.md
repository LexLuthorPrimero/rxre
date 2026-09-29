# EXP-F4-A — Governor Frametime-Feedback Read-Only (Render-Scale) — RESULTADOS

> **ADDENDA DE ESTADO D6 (2026-09-23):** este documento es **HISTÓRICO / NO VIGENTE**
> para el veredicto final: conserva la ejecución v2.1/v2.2 y sustenta el historial. La corrida
> v2.3 posterior tiene **S1 EJECUTADA/COMPLETADA**, **S2 INICIADA/PARADA D** y veredicto global
> **INCONCLUSO / INCONCLUSIVE**. La fuente canónica vigente es
> `EXP-F4-A-RESULTADOS-v2.3.md`; no se borra ni reescribe este historial.
> `P` en las tablas históricas significa `W_SMU` de `power1_input`, no vatímetro.

**FASE:** R-4B · **Protocolo:** v2.1 (cerrado, aprobado) · **Fecha:** 2026-09-22
**Harness:** `harness/app_vulkan.c` (Diseño B) · **Controlador:** `controller/governor.py` · **Telemetría:** `telemetry/telemetria.sh`
**Resultados crudos:** `FASE-R4B-GOVERNOR/results/session1/` y `session2/`

> Documento de resultados de la ejecución del protocolo (2 sesiones). Los veredictos se
> derivarían de `analyze.py` (phase1 + phase2 + final) sobre los logs crudos, **no** de
> afirmaciones ad hoc.
>
> **ESTADO ACTUAL:** **SESIÓN 1 (v2.2, protocolo con cooldown entre passes) COMPLETADA — GATEs
> Fase 1 TODOS PASS** (histéresis 0.26 %, throttling térmico eliminado en open-loop) → **FREEZE
> T=9.168 ms, s*=0.75, sha256 `6b6d6952…`** → **Phase 2 ejecutada (8/8 trials)**. La S1 original
> (v2.1) quedó como **PARADA D** (§1B) y se conserva íntegra como diagnóstico. Sesión 2 **NO
> iniciada** (detención solicitada tras S1). **Sin veredicto global.**
>
> Variación procedimental v2.2 documentada formalmente en `EXP-F4-A-PROTOCOL-v2.2.md` ANTES de
> ejecutar: cooldown pasivo entre passes (p1→p2→p3) con condición telemétrica
> `temp ≤50 °C sostenido ≥30 s ∧ SCLK nivel 0 ∧ P<4 W`. Nada más cambió del protocolo.

---

## 0. Resumen Ejecutivo

| Métrica | Resultado | Clasificación |
|---|---|---|
| GATEs Fase 1 (monotonía, ≥2 pasos ≥3 %, rango 5–200 ms, histéresis ≤15 %) | TBD | VERIFIED |
| T = 0.80·P99(1.00) open-loop | TBD | DERIVED |
| s* (mayor escala con P99_openloop ≤ T) | TBD | DERIVED |
| R1 concentración r ∈ [0.90,1.10] ≥5/6 (+ IC90) | TBD | VERIFIED/DERIVED |
| R2 overshoot ≤1 % en ≥5/6 | TBD | VERIFIED |
| R3 sin oscilación sostenida ≥5/6 | TBD | VERIFIED |
| R4 convergencia ≤4 ventanas (80 s) | TBD | VERIFIED |
| R5 reproducibilidad CV≤10 %, inter-sesión ≤15 %, dirección ≥90 % | TBD | DERIVED |
| R6 Δ(s*, s_settled)=0 en ≥5/6 | TBD | VERIFIED |
| R7 latencia DIST ≤2 ventanas (4/4) | TBD | VERIFIED |
| E (p99 settle GOV vs FIXED, pareada) | TBD | DERIVED |
| Falsación F1–F6 | TBD | — |

**Veredicto global:** TBD

---

## 1. Alcance y restricciones respetadas

- **Read-only:** sin escrituras sysfs/kernel/VBIOS/PowerPlay; sin contadores HW; sin registros GPU;
  sin Mesa custom; sin benchmarks externos. Único actuador: render-scale s del workload.
- Paradas íntegras A–D, R1–R7, F1–F6 aplicadas literalmente.
- Clasificaciones: VERIFIED / DERIVED / ESTIMATED / UNKNOWN / INCONCLUSIVE / FALSIFIED / SUPPORTED.
  Nunca "PROVEN". Frametime y FPS siempre separados.
- Potencia según `AUDIT-001/METRICS-DEFINITIONS.md` (exclusiones obligatorias, steady =
  gpu_busy≥95 ∧ SCLK≥1071 MHz ∧ MCLK≥1500 MHz, ≥100 muestras).

### 1.1 Calibración previa (PRE-FLIGHT, no experimental)

> **Importante:** el primer workload del harness no superó el GATE de calibración
> (P99(1.00) ≈ 3.8 ms < 5 ms) y se realizó una **recalibración del fragment shader** (8 taps y
> cadena FMA ~90) ANTES de la corrida experimental válida. Esa recalibración queda registrada en
> `PRE-FLIGHT-CALIBRACION-EXP-F4-A.md` y clasificada como **PRE-FLIGHT/CALIBRACIÓN**, NO como dato
> experimental de R-4B. Los valores de calibración (`P99(1.00)≈11.4 ms`, curva `11.4→2.9 ms`) son
> **PRELIMINARES**; los valores oficiales provienen exclusivamente de Fase 1 open-loop de cada sesión.

---

## 1B. SESIÓN 1 — PARADA D (Fase 1, §14-D) — REGISTRO COMPLETO

**Estado:** sesión 1 ejecutada (15/15 bloques open-loop) → GATE de histéresis FALLADO →
parada D por protocolo → Fase 2 y sesión 2 NO iniciadas. **Sin veredicto global.**

### 1B.1 GATEs Fase 1 (sesión 1) — detalle

| Gate | Resultado | Valor medido |
|---|---|---|
| P99(s) no creciente en s | **PASS** | sí (curva p1) |
| ≥2 pasos consecutivos ≥3 % | **PASS** | 4 pasos (18–42 %) |
| P99(1.00) ∈ [5,200] ms | **PASS** | 11.5 ms (p1) |
| Histéresis asc↔desc ≤15 % | **FAIL** | **58.3 %** (p2/p3 vs p1) |

### 1B.2 Curva open-loop real (15 bloques, sesión 1)

| s | p1 asc [ms] | p2 desc [ms] | p3 asc [ms] |
|---|---|---|---|
| 1.00 | 11.46 | 36.16 | 38.90 |
| 0.87 | 9.33 | 14.20 | 36.19 |
| 0.75 | 7.04 | 8.04 | 27.38 |
| 0.62 | 4.92 | 4.96 | 18.90 |
| 0.50 | 2.86 | 2.91 | 10.07 |

### 1B.3 Causa — throttling térmico (VERIFIED desde telemetría)

| Bloque | SCLK mediana [MHz] | temp máx [°C] | power_avg [W] |
|---|---|---|---|
| p1_s100 | 1071 | 57 | 19.4 |
| p1_s050 | 1071 | 81 | 19.8 |
| p2_s100 | **734** | 92 | 15.7 |
| p3_s100 | **551** | 92 | 14.7 |
| p3_s050 | **551** | 92 | 14.3 |

- El pass p1 (ascendente) corre con **SCLK 1071 MHz sostenido** (curva limpia, idéntica a la
  calibración: 11.46→2.86 ms).
- Al acumularse los 5 bloques de p1, el die alcanza 81 °C; p2 y p3 superan **92 °C** y SCLK cae
  hasta **551 MHz (nivel 1) sostenido**, inflando p99 a 36–39 ms en s=1.00 y a 10 ms en s=0.50.
- La "histéresis" ascendente↔descendente NO es del pipeline gráfico: es **degradación térmica**.
  El GATE §14-D cumplió su función de protección — la corrida no es válida para FREEZE.

### 1B.4 Verificaciones post-sesión 1

| Verificación | Resultado |
|---|---|
| GATEs | histéresis FAIL → parada D |
| manifest.json (FREEZE T,s*) | **NO generado** (correcto: freeze solo tras gates OK) |
| Integridad datos | 15/15 bloques con frames.tsv, m0.txt, telemetry.csv |
| DPM post-sesión | 214/300 MHz (idle) — idéntico a pre_flight → **sin writes de sistema** |
| power1_cap | 35,000,000 µW intacto, nunca escrito |
| kalm PIDs 4086/4087 | presentes y vivos |
| post_flight.txt | no generado (parada D aborta antes del snapshot) — suplido por la tabla anterior |

### 1B.5 Conclusión de la sesión 1

- **UNKNOWN/limitación principal:** la RX 550 con este workload sostenido alcanza el límite
  térmico (~92 °C) dentro de los 25 s de un bloque continuo, degradando SCLK a 551 MHz. El
  protocolo v2.1 no prevé entre-bloques; el GATE funciona como diseñado (parada D).
- **No se modificó** workload, thresholds, T, s*, escalas ni R1–R7/F1–F6 en respuesta a estos
  resultados (instrucción explícita del usuario).
- **No se declaró** veredicto global. Sesión 2 pendiente de autorización/corrección de
  procedimiento.

---

## 1C. SESIÓN 1 (v2.2) — GATEs PASS + FREEZE + PHASE 2 — REGISTRO COMPLETO

**Estado:** sesión 1 relanzada bajo **protocolo v2.2** (única variación: cooldown entre passes
de Fase 1, documentada formalmente en `EXP-F4-A-PROTOCOL-v2.2.md`; datos en
`results/session1-v22/`). Fase 1 **completa con GATEs PASS** → FREEZE(T, s*) → Phase 2
completa (8/8 trials). Sesión 2 NO iniciada. **Sin veredicto global.**

### 1C.1 GATEs Fase 1 (sesión 1-v2.2) — detalle

| Gate | Resultado | Valor medido |
|---|---|---|
| P99(s) no creciente en s | **PASS** | sí (curva p1) |
| ≥2 pasos consecutivos ≥3 % | **PASS** | 4 pasos (18–42 %) |
| P99(1.00) ∈ [5,200] ms | **PASS** | 11.46 ms |
| Histéresis asc↔desc ≤15 % | **PASS** | **0.26 %** (vs 58.3 % en S1-v2.1) |
| Reachability (existe s con P99≤T) | **PASS** | s*=0.75 (7.02 ms ≤ 9.168 ms) |

### 1C.2 Curva open-loop real v2.2 (15 bloques, con cooldown entre passes)

| s | p1 asc [ms] | p2 desc [ms] | p3 asc [ms] | P99 mediana [ms] |
|---|---|---|---|---|
| 1.00 | 11.46 | 11.45 | 11.46 | 11.46 |
| 0.87 | 9.36 | 9.33 | 9.35 | 9.35 |
| 0.75 | 7.02 | 7.02 | 7.02 | 7.02 |
| 0.62 | 4.92 | 4.90 | 4.90 | 4.90 |
| 0.50 | 2.85 | 2.85 | 2.85 | 2.85 |

> Comparación con S1-v2.1 (§1B.2): los passes p2/p3 ya **no** están inflados (en v2.1 llegaban a
> 36–39 ms en s=1.00 por throttling). La curva es estable e independiente de la dirección de
> barrido → la "histéresis" de v2.1 era artefacto térmico, confirmado.

### 1C.3 FREEZE (T, s*) y cooldowns reales

| Parámetro | Valor |
|---|---|
| T = 0.80·P99(1.00) | **9.168 ms** |
| s* | **0.75** |
| sha256 manifest | `6b6d69522e60452934fed0cf3b94ec32f365e0535bb7afcb2326888d077d67ca` |
| frozen.sha256 | `6b6d69522e604529…` |
| Cooldown 1 (p1→p2) duración real | **180 s** (condición: 49 °C ∧ SCLK nivel 0 ∧ 3.68 W) |
| Cooldown 2 (p2→p3) duración real | **225 s** (condición: 49 °C ∧ SCLK nivel 0 ∧ 3.39 W) |

> Expectativa inicial ~270 s (test térmico REP1/REP2: 255–270 s); el retorno real fue más rápido
> (180/225 s) porque la condición `temp ≤50 °C sostenido ≥30 s ∧ SCLK nv0 ∧ P<4 W` (telemétrica,
> no temporal) se cumplió antes. Sin tiempos asumidos: se siguió enfriando hasta cumplirla.

### 1C.4 Térmica y SCLK por bloque (v2.2) — diagnóstico

| Bloque | SCLK mediana [MHz] | temp máx [°C] | power_avg [W] |
|---|---|---|---|
| p1_s100 → p1_s050 | **1071** (todos) | 55 → 79 | 18.7–19.5 |
| p2_s050 → p2_s100 | **1071** (todos) | 66 → 86 | 18.7–19.9 |
| p3_s100 → p3_s050 | **1071** (todos) | 67 → 86 | 18.9–19.7 |

> **SCLK 1071 MHz sostenido en los 15 bloques** (muestras sub-1071 solo 1.2–1.5 %, transitorios
> de inicio/fin de bloque). T_max p2/p3 = 86 °C — **nunca alcanzó el punto de degradación
> sostenida (~92 °C)**. vs S1-v2.1: p2_s100 734 MHz, p3_s100 551 MHz, T_max 92 °C (§1B.3).

### 1C.5 Phase 2 (orden fijo `fixed gov fixed gov fixed gov dist dist`)

| Trial | p99 settle [ms] | escala settle | overshoot settle [%] |
|---|---|---|---|
| fixed1 | 11.7 / 15.2 (win2–3) | 1.00 | 100 |
| fixed2 | 39.1 / 39.1 | 1.00 | 100 |
| fixed3 | 39.1 / 39.1 | 1.00 | 100 |
| gov1 | 27.3 / 27.4 | 0.75 (=s*) | 78–79 |
| gov2 | 27.4 / 27.4 | 0.75 | 85–86 |
| gov3 | 27.5 / 27.4 | 0.75 | 90–90 |
| dist1 | 10.2 / 10.1 | 0.50 | 14–18 |
| dist2 | 10.2 / 10.1 | 0.50 | 19–21 |

> **Clasificación FORMAL de Phase 2 (S1-v2.2): `DIAGNOSTIC / THERMALLY CONFOUNDED — NOT FOR
> VERDICT`.** NO se declara R1–R7 PASS ni FAIL con estos datos (auditoría de timestamps en
> `EXP-F4-A-PROTOCOL-v2.3-PROPUESTA.md` §1.2): 0 de 8 trials con ventanas de medición íntegras a
> SCLK 1071; solo fixed1 conserva v0–v1 limpias. La causa es **temperatura acumulada**: Phase 2
> heredó 84 °C de la Fase 1 (sin cooldown FREEZE→fixed1) y cada trial heredó 91–92 °C del anterior
> (sin cooldown entre trials) → SCLK 551 MHz desde ~v0 (degradación ≤4 s, ≥92 °C conocido de N=2).
> La duración del trial no es el factor primario: fixed1 (60 s, el más corto) degradó a los 41 s
> por entrar a 84 °C; la dirección de la respuesta DIST (39→73→19→10 ms con escala 1.00→0.50) es
> correcta pero su magnitud/banda está confundida por el clock bajo. El p99 GOV ≈27 ms es un
> **artefacto térmico**, no evidencia de fallo (ni de éxito) del governor.
> La Fase 1 (GATEs PASS, FREEZE T/s\*) SÍ fue térmicamente válida (15/15 a 1071, T_max 86 °C) y se
> conserva **íntegra e inmutable**. Este hallazgo NO es causa nueva: es el fenómeno conocido
> (§1B.3/N=2) confinado a Phase 2 → requiere decisión del usuario antes de sesión 2
> (propuesta v2.3, documento `EXP-F4-A-PROTOCOL-v2.3-PROPUESTA.md`).

### 1C.6 Verificaciones post-sesión v2.2

| Verificación | Resultado |
|---|---|
| GATEs Fase 1 | **TODOS PASS** (histéresis 0.26 %) |
| manifest.json / FREEZE | **generado** (T=9.168, s*=0.75, sha256 `6b6d6952…`) |
| Integridad datos | 15/15 bloques (frames.tsv + m0.txt + telemetry.csv), 8/8 trials Phase 2 |
| DPM pre↔post | idénticos (hash `ff9e8280bd…`; SCLK 214 idle) — **sin writes de sistema** |
| power1_cap | 35,000,000 µW intacto (pre y post) |
| kalm PIDs 4086/4087 | presentes y vivos pre/post |
| journal ventana 00:10–00:45 | sin eventos amdgpu/drm/sclk/power/temp (solo ruido de apps) — **sin escrituras de subsistema** |
| pre_flight/post_flight | ambos generados y firmados por el orquestador v2.2 |

### 1C.7 Conclusión de la sesión 1-v2.2

- La variación v2.2 (cooldown entre passes) **eliminó el artefacto térmico de la Fase 1 open-loop**
  (histéresis 58.3 % → 0.26 %), permitiendo el FREEZE. Clasificación del cambio de resultado:
  **procedimiento corregido por causa térmica ya caracterizada, sin alterar workload,
  thresholds, T, s*, escalas ni R1–R7/F1–F6**.
- **Phase 2 clasificada `DIAGNOSTIC / THERMALLY CONFOUNDED — NOT FOR VERDICT`** (véase §1C.5):
  contaminada por temperatura acumulada (entrada 84 °C + herencia 91–92 °C entre trials), no por
  duración de trial; R1–R7 no declarados con estos datos.
- **Propuesta v2.3 preparada** (`EXP-F4-A-PROTOCOL-v2.3-PROPUESTA.md`): cooldown telemétrico entre
  cada trial de Phase 2 (condición DN-07 ≤50 °C s30s ∧ SCLK nv0 ∧ P<4 W), FIXED/GOV enteros,
  DIST con entrada ≤40 °C o mini-test de ramp con governor activo o marcación por ventana
  (opciones 7.3-A/B/C), regla por ventana THERMALLY CONFOUNDED, sin segmentación (invalida la
  lógica de ventanas/steps). **NO EJECUTADA**; pendiente de autorización.
- **No se declaró veredicto global. Sesión 2 NO iniciada** (detención solicitada tras S1-v2.2).
- S1 original (PARADA D) intacta en `results/session1/` como diagnóstico.

---

## 2. Calibración (Fase 1) — sesión 1 y 2

### 2.1 GATEs de calibración (§6.1) — Pas/Fall

| Gate | Sesión 1 | Sesión 2 | Clasif. |
|---|---|---|---|
| P99(s) no creciente en s (s: 1.00→0.50) | TBD | TBD | VERIFIED |
| ≥2 pasos consecutivos con reducción ≥3 % | TBD | TBD | VERIFIED |
| P99(1.00) ∈ [5,200] ms | TBD (≈11 ms smoke) | TBD | VERIFIED |
| Histéresis asc↔desc ≤15 % | TBD | TBD | VERIFIED |

### 2.2 Curva P99(s) open-loop (mediana de 3 bloques/s)

| s | P99 open-loop [ms] S1 | P99 open-loop [ms] S2 | Δ% vs 1.00 |
|---|---|---|---|
| 1.00 | TBD | TBD | — |
| 0.87 | TBD | TBD | TBD |
| 0.75 | TBD | TBD | TBD |
| 0.62 | TBD | TBD | TBD |
| 0.50 | TBD | TBD | TBD |

### 2.3 T y s* congelados

| Parámetro | Sesión 1 | Sesión 2 |
|---|---|---|
| T = 0.80·P99(1.00) [ms] | TBD | TBD |
| s* (mayor s con P99_openloop ≤ T) | TBD | TBD |
| sha256 manifest (FREEZE) | TBD | TBD |

> El manifest se congeló **antes** de la primera corrida GOV (FREEZE previo por `analyze.py phase1`).

---

## 3. Resultados R1–R7 (Phase 2)

### 3.1 R1 — Concentración r = p99_settle / T en banda [0.90, 1.10]

| Trial GOV | r | ¿[0.90,1.10]? |
|---|---|---|
| S1-GOV1 | TBD | TBD |
| S1-GOV2 | TBD | TBD |
| S1-GOV3 | TBD | TBD |
| S2-GOV1 | TBD | TBD |
| S2-GOV2 | TBD | TBD |
| S2-GOV3 | TBD | TBD |

IC90 bootstrap de la mediana: TBD. Criterio: ≥5/6 ∧ IC90 ⊂ [0.90,1.10]. **Resultado: TBD**

### 3.2 R2 — Overshoot (% frames > T en ventanas settle)

| Trial | overshoot % (v5–v6) |
|---|---|
| S1-GOV1..3 | TBD |
| S2-GOV1..3 | TBD |

Criterio: ≤1 % en ≥5/6 y ≤2 % en todas. **Resultado: TBD**

### 3.3 R3 — Oscilación sostenida (reversiones)

Reversiones detectadas (acción LOWER/RAISE que re-cruza el mismo umbral ≤2 ventanas después): TBD.
Criterio: 0 reversiones en ≥5/6. **Resultado: TBD**

### 3.4 R4 — Convergencia (tiempo hasta 2 ventanas consecutivas en banda)

Ventana de convergencia por trial (1-based; ≤4 = 80 s): TBD. **Resultado: TBD**

### 3.5 R5 — Reproducibilidad

| medida | valor | criterio | OK |
|---|---|---|---|
| CV de r entre 6 trials | TBD | ≤10 % | TBD |
| Δ mediana r inter-sesión | TBD | ≤15 % | TBD |
| Predicción de dirección de acciones | TBD | ≥90 % | TBD |

**Resultado: TBD**

### 3.6 R6 — Escala asentada vs s*

| Trial | s_settled (v5–v6) | Δ pasos vs s*=TBD | OK |
|---|---|---|---|
| S1-GOV1..3 | TBD | TBD | TBD |
| S2-GOV1..3 | TBD | TBD | TBD |

Criterio: Δ=0 en ≥5/6. **Resultado: TBD**

### 3.7 R7 — Respuesta a disturbios (DIST, 4 trials)

| Trial | lat. LOWER tras +60 s | lat. RAISE tras +120 s | reincorp. banda tras +60 | reincorp. banda tras +120 |
|---|---|---|---|---|
| S1-DIST1 | TBD | TBD | TBD | TBD |
| S1-DIST2 | TBD | TBD | TBD | TBD |
| S2-DIST1 | TBD | TBD | TBD | TBD |
| S2-DIST2 | TBD | TBD | TBD | TBD |

Criterio: latencia ≤2 ventanas y reincorporación a banda ≤2 ventanas en 4/4. **Resultado: TBD**

---

## 4. Pregunta E — p99 settle GOV vs FIXED (descriptiva, pareada n=6)

| Par | p99_GOV [ms] | p99_FIXED [ms] | Δ% (GOV−FIXED)/FIXED | s_GOV | s_FIXED |
|---|---|---|---|---|---|
| 1 | TBD | TBD | TBD | TBD | 1.00 |
| 2 | TBD | TBD | TBD | TBD | 1.00 |
| 3 | TBD | TBD | TBD | TBD | 1.00 |
| 4 | TBD | TBD | TBD | TBD | 1.00 |
| 5 | TBD | TBD | TBD | TBD | 1.00 |
| 6 | TBD | TBD | TBD | TBD | 1.00 |

Wilcoxon pareado: stat=TBD, p=TBD. Bootstrap 90 % de Δ% medio: TBD.
> Cualquier lectura de "≥15 %" solo se reporta con s_GOV y area_fraction en la misma fila.

---

## 5. Potencia (METRICS-DEFINITIONS) por trial

Tabla: power_avg_full / power_avg_steady / power_max_full / power_max_steady, por trial y
por ventana en `fase2/metrics.json`. N/A si steady no alcanza los criterios.

| Trial | P_avg_full [W] | P_avg_steady [W] | P_max_full [W] | P_max_steady [W] |
|---|---|---|---|---|
| TBD | TBD | TBD | TBD | TBD |

---

## 6. Falsación F1–F6 (§13)

| F | criterio | estado |
|---|---|---|
| F1 | convergencia > N ventanas en ≥2 trials | TBD |
| F2 | r fuera de banda persistente | TBD |
| F3 | oscilación sostenida | TBD |
| F4 | sin recuperación de disturbio | TBD |
| F5 | curva plana / no monótona (Gate) | FALSE (gates OK) |
| F6 | alta varianza inter-sesión | TBD |

Falsación = F5 solo, o ≥2 de {F1,F2,F3,F4,F6}. **Resultado: TBD**

---

## 7. Limitaciones y amenazas a la validez

- TBD (rellenar tras inspección de logs: sincronización clock, boundaries de ventana,
  tamaño de muestra, régimen térmico desconocido, etc.)

---

## 8. Archivos de soporte

- `results/sessionN/fase1/manifest.json` (T, s*, curva, gates, sha256 congelado)
- `results/sessionN/fase2/order.json`, `fixedK|govK|distK/frames.tsv`, `telemetry.csv`,
  `run_m0.txt`, `governor_trace.tsv`
- `results/sessionN/pre_flight.txt`, `post_flight.txt` (verificación read-only)
- `harness/scripts/analyze.py` (phase1/phase2/final), `verdict.json`
