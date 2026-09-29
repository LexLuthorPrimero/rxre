# EXP-F4-A — PROPUESTA DE PROTOCOLO v2.3 (CONTROL TÉRMICO DE PHASE 2)

> **ADDENDA DE ESTADO D6 (2026-09-23):** este archivo conserva la **propuesta
> pre-ejecución** y su redacción histórica («NO EJECUTADA»). La corrida posterior sí
> inició S1 y S2: **S1-v2.3 EJECUTADA/COMPLETADA; S2-v2.3 PARADA D** antes de Phase 2;
> veredicto **INCONCLUSO / INCONCLUSIVE**, nunca `SUPPORTED`. Para el estado vigente y la
> trazabilidad de los artefactos temporales, ver `EXP-F4-A-RESULTADOS-v2.3.md`.

**Estado:** PROPUESTA HISTÓRICA — NO NORMATIVA PARA EL ESTADO ACTUAL. La corrida posterior
S1-v2.3 fue EJECUTADA/COMPLETADA y S2-v2.3 fue INICIADA/PARADA D; el veredicto es
INCONCLUSO/INCONCLUSIVE. No se reintenta S2-v2.3.
**Fecha:** 2026-09-23 · **Base:** S1-v2.2 (GATEs Fase 1 TODOS PASS, FREEZE T=9.168 ms / s\*=0.75 / sha256 `6b6d6952…`).
**Regla superior (invariante):** la única modificación permitida es **CONTROL TÉRMICO PROCEDIMENTAL**.
La `P` de este documento es `W_SMU` (`power1_input`), no vatímetro independiente.
T, s\*, escalas, threshold banda [0.90,1.10]·T, R1–R7, F1–F6, workload, réplicas, criterios
estadísticos, governor.py, harness y analyze.py **NO cambian**.

---

## 0. Síntesis (para decisión rápida)

> **Marcador de umbral:** cualquier entrada `≤35 °C` mencionada en §3.5/§7.3 es una
> opción histórica de esta propuesta, no un gate ejecutado ni una vía vigente. La
> corrida D6 ejecutó la entrada uniforme `≤50 °C`; no se reintenta ninguna variante.

Phase 2 de S1-v2.2 está **contaminada por temperatura acumulada**, NO por la duración de los
trials per se: la GPU entró en Phase 2 a 84 °C (calor residual de Fase 1, sin cooldown
FREEZE→fixed1) y cada trial heredó 91–92 °C del anterior. A 91–92 °C el SCLK colapsa a 551 MHz
en 3–4 s (regla conocida ≥92 °C de N=2).

Propuesta v2.3 (procedimental, cero cambios de código):
1. **Cooldown telemétrico entre CADA trial consecutivo de Phase 2**, incluido antes del primero
   (tras el FREEZE). Condición de entrada/retorno: `temp ≤50 °C sostenido ≥30 s ∧ SCLK nivel 0 ∧
   P<4 W` (idéntica a DN-07 / v2.2; real 255–270 s).
2. FIXED (60 s) y GOV (120 s): **ejecución completa sin segmentar** — caben en el presupuesto
   térmico desde ≤50 °C (≈69 °C y ≈87 °C máx. estimados; sin degradación verificada ≤90 °C en N=2).
3. DIST (200 s): **no cabe** desde ≤50 °C con ramp 0.31 °C/s (92 °C ≈ a los ~135 s; la
   re-incorporación post-retorno necesita ventanas hasta ~160 s). Opciones en §7.3 (entrada
   ≤40 °C, o mini-test de ramp con governor activo antes de fijar, o marcación por ventana).
4. Regla de validación por ventana (post-hoc, read-only): cualquier ventana de medición con
   SCLK<1071 sostenido o T>90 °C se marca `THERMALLY CONFOUNDED` y se excluye; nunca se mezcla.
5. **No se segmentan trials**: dividir una ejecución rompe el anclado de ventanas del governor a
   t0 absoluto y re-dispara los steps internos del harness DIST (+60/+120 relativos a su propio
   inicio) → invalida la lógica de ventanas de R7 (demostrado en §6-G).

---

## 1. Análisis de la contaminación térmica de Phase 2 (S1-v2.2)

### 1.1 Duración REAL de cada trial (auditoría de timestamps/telemetría/governor_trace)

Duraciones nominales (§8/§9 protocolo) = duraciones reales medidas (m0, governor_trace wb/we):

| Condición | Nominal (s) | Real (s) | Ventanas de 20 s |
|---|---|---|---|
| FIXED | 60 | **60** | 3 (v0–v2) |
| GOV | 120 | **120** | 6 (v0–v5) |
| DIST | 200 | **200** | 10 (v0–v9) |

### 1.2 Cronología térmica por trial (telemetría 10 Hz alineada a m0)

| Trial | T_inicio carga | t→90 °C | 1ª caída SCLK<1071 (≥15 m) | T≥90 °C (≈s) | % carga con SCLK<1071 | Ventanas limpias |
|---|---|---|---|---|---|---|
| fixed1 | 84 °C | 23.9 s | t=41 s (T=92 °C, sclk 1000) | 33 | 44 % | v0–v1 (sclk 1071) |
| gov1 | 91 °C | 0.9 s | t=4 s (92 °C, 980) | 100 | 98 % | ninguna |
| fixed2 | 91 °C | 0.5 s | t=3 s (92 °C, 734) | 54 | 99 % | ninguna |
| gov2 | 91 °C | 0.6 s | t=3 s (92 °C, 734) | 102 | 99 % | ninguna |
| fixed3 | 91 °C | 0.6 s | t=3 s (92 °C, 734) | 53 | 99 % | ninguna |
| gov3 | 92 °C | 0.5 s | t=3 s (92 °C, 734) | 103 | 99 % | ninguna |
| dist1 | 91 °C | 0.5 s | t=3 s (92 °C, 734) | 162 | 100 % | ninguna |
| dist2 | 92 °C | 0.5 s | t=3 s (92 °C, 734) | 165 | 100 % | ninguna |

Detalle clave por condición:

- **FIXED1** (60 s): p99 v0/v1 a SCLK 1071 (ventanas 0–40 s, T 84→92 °C), degrada en v2
  (40–60 s, SCLK 980, p99 real medido 15.2 ms a 1.00). Es el único trial con datos limpios
  parciales, porque fue el único que no heredó 91 °C.
- **GOV1–3** (120 s): entran a 91–92 °C → SCLK 551/734 desde ~v0. El governor SÍ actúa
  (1.00 → 0.87 → 0.75 → 0.62; p99 39 → 27 ms) pero la señal está **inflada por throttle**:
  27 ms ≫ banda [8.25, 10.08] ms → nunca converge por diseño, no por el lazo.
  P99 GOV settle entre 27.3 y 27.4 ms es un **artefacto térmico** (no una propiedad del governor).
- **DIST1–2** (200 s): todo el trial a 92 °C/551 MHz. Sin embargo la **respuesta estructural es
  visible**: step N:4→8 en v3 → p99 39→73 ms y bajada de escala; retorno N:8→4 en v6 → p99 55→19
  →10.2 ms con escala 0.50. La **dirección** de la respuesta del governor es correcta; la
  **magnitud/banda** está confundida por el clock bajo. Esto NO es evidencia de fallo del governor.

### 1.3 Diagnóstico: ¿duración absoluta, temperatura acumulada o ambas?

**Temperatura acumulada es el factor dominante; la duración solo importa como presupuesto físico.**

- Evidencia directa: fixed1 (60 s, el trial más corto) degrada a los 41 s porque **entró a 84 °C
  en vez de ≤50 °C**. gov1 es 2× más largo que fixed1 pero degrada en 4 s: entró a 91 °C.
- Evidencia cruzada N=2: desde 48 °C, 90 °C se alcanza a los 136 s; desde 37 °C, a los 169 s
  (ramp 0.31 °C/s). Un segmento de carga continuo partiendo de ≤50 °C tiene un presupuesto de
  ~135 s hasta 92 °C (lin. conservador), ~90 °C en ~123 s con techo de diseño 88 °C.
- Ambas dimensiones convergen en una sola regla: **el confusor aparece cuando temperatura de
  entrada alta + duración del tramo exceden el presupuesto**. Partiendo frío (≤50 °C), 60 s y
  120 s están dentro; 200 s no.

---

## 2. Fuentes consultadas (nada asumido)

| Fuente | Qué aporta |
|---|---|
| `FASE-R4B-THERMAL-TEST/RESULTADOS-TEST-TERMICO.md` (N=2) | ramp 0.31 °C/s (0.315/0.310, ±1.6 %), sin degradación ≤90 °C, degradación sostenida ≥92 °C, cooldown 255–270 s a ≤50 °C, cap 35 W sin ligar |
| `EXP-F4-A-RESULTADOS.md` §1B/§1C | S1 v2.1 PARADA D (58.3 % histéresis en 92 °C); S1 v2.2 GATEs 0.26 % |
| `EXP-F4-A-PROTOCOL.md` §8/§9/§10/§12.1 | duraciones 60/120/200 s, steps DIST +60/+120, banda, R1–R7, settle = últimas 2 ventanas |
| sysfs `temp1_crit` (dispositivo, read-only) | **97 °C** (edge) — tope físico absoluto, 5 °C sobre el punto de degradación sostenida |
| `governor.py` (código) | ventanas ancladas a `t0` absoluto; `we > end_us` corta; ventana sin frames → no actuar |
| `app_vulkan.c` (código) | steps DIST son **internos al harness** (`elast>=60/120 s` desde SU inicio); `--duration` corre sin pausa |
| **UNKNOWN declarado** | ramp real con governor activo bajando s (P 18.1→15.1 W en v2.2 a 551 MHz; a 1071 no medido). Solo un mini-test read-only puede convertirlo en dato (§7.3-B) |

---

## 3. Respuestas A–I a las preguntas del diseño

**A. ¿Dónde colocar los cooldowns?**
Entre **cada trial consecutivo** de Phase 2 (y antes del primero, tras FREEZE→frozen.sha256).
Justificación de los datos: fixed1 degradó a los 41 s por entrar a 84 °C; los demás degradaron en
≤4 s por heredar 91–92 °C. Con cooldown previo a cada trial, TODOS entran a ≤50 °C y CABEN
(60 s→≈69 °C, 120 s→≈87 °C). Colocar cooldown solo en algunos puntos (p.ej. solo entre pares) es
insuficiente: gov1 heredaría 69 °C de FIXED y a los 120 s llegaría a ≈106 °C (68+37).

**B. ¿Qué condición objetiva de recuperación?**
La misma ya validada (DN-07 / v2.2): `temp1_input ≤50 °C sostenido ≥30 s ∧ SCLK activo = nivel 0
∧ power1_input <4 W`. Medida: 255–270 s desde ~74 °C (N=2); reales 180/225 s entre passes v2.2.
Es operativa (no un tiempo fijo), por lo que es robusta a la ventilación PWM ambiente. Se registra
el tiempo real de cada cooldown (formato `cooldown_k.tsv`).

**C. ¿Puede un trial individual seguir calentándose hasta 92 °C?**
Con la propuesta: **FIXED y GOV no** (máx. estimado ≈69 °C y ≈87 °C desde ≤50 °C, ambos por
debajo del umbral 90 verificado). **DIST sí podría** en sus últimas ventanas (92 °C ≈ a los
~135 s desde 50 °C con ramp 0.31 en s=1.00). Solo DIST requiere tratamiento especial (§7.3).

**D. Si sí, ¿cómo evitarlo sin cambiar artificialmente la carga comparada?**
Tres palancas, las tres sin tocar el workload:
1. **Entrada más fría para DIST** (≤40 °C ⇒ 92 °C ≈ a los ~168 s, cubriendo los ~160 s de
   re-incorporación post-retorno). Coste: cooldown más largo (tiempo a medir, UNKNOWN).
2. **La propia bajada de escala del governor reduce la potencia** (medido 18.1→15.1 W entre
   s=1.00 y s=0.62 en v2.2, ~17 %), lo que aplana la ramp de DIST v(s). No medido a 1071 → UNKNOWN.
3. **Regla de aborto por ventana**: si una ventana de medición cruza T>90 °C o SCLK<1071, se
   marca CONFOUNDED y no entra en R1–R7 (nunca se mezcla un dato limpio con uno degradado).

**E. ¿Cuánto puede durar un segmento antes de que lo térmico sea confusor?**
Presupuesto (lineal conservador, ramp 0.31 °C/s y margen a 88 °C): `t_max ≈ (88 − T_entrada)/0.31 s`.
Desde ≤50 °C → **~123 s**. FIXED 60 s (69 °C) y GOV 120 s (87 °C) cumplen. DIST 200 s no.

**F. ¿Hay que dividir los trials largos en segmentos?**
No, salvo DIST (y solo él). FIXED y GOV caben enteros desde ≤50 °C. Para DIST, dividir la
ejecución en 2 tramos con cooldown en medio **no preserva la lógica** (véase G) → se usa otra
palanca (§7.3) o se autoriza una variación mínima del esquema temporal de R7 (NO recomendado:
modifica pre-committed).

**G. Si se dividen, ¿cómo preservar exactamente la lógica de P99/convergencia/overshoot/respuesta?**
Con la implementación actual **es imposible sin tocar código** (y tocar código está prohibido):
- El governor ancla las ventanas a `t0` absoluto del trial (`k*20 s` desde m0) y corta en
  `end_us = t0 + duration`; relanzarlo con t0 nuevo rompe la numeración y los streaks de R1/R3/R4.
- El harness DIST aplica los steps a `elast ≥60/120 s` desde **su propio inicio**: un segundo tramo
  re-ejecutaría N:4→8→4 desde cero → la secuencia de carga dejaría de ser la pre-committed.
- El análisis (`analyze.py`) define ventanas por trial; dos tramos = dos trials → diseño pareado
  y R7 inválidos.
Por eso la v2.3 **no segmenta**: controla la condición de entrada y la duración del tramo
(que es exactamente la variable que sí se puede proceder sin alterar workload).

**H. ¿Cómo garantizar que GOV y FIXED reciban la misma condición térmica inicial?**
Cooldown previo a cada trial con la **misma condición de retorno** (§B): tanto FIXED_i como GOV_i
entran a ≤50 °C ∧ SCLK nv0 ∧ P<4 W. Además, su comparabilidad en ventanas de medición se justifica
así: a SCLK 1071 el frametime es **insensible a T en [55, 87] °C** — Fase 1 v2.2 dio la curva
open-loop idéntica en los 3 pases (p99 = 11.46/11.45/11.46 ms a 1.00) con perfiles térmicos
distintos (ver §1.4 de RESULTADOS), y N=2 no observó degradación ≤90 °C. La única diferencia
entre GOV y FIXED en ventanas válidas es, por tanto, el controlador de escala (la variable de
estudio), no la térmica.

**I. ¿Cómo tratar DIST (respuesta del governor a cambios de carga)?**
Se preserva el trial único de 200 s (steps +60/+120, 10 ventanas, R7 intacto). La respuesta
estructural ya se observa incluso degradada (dirección correcta: bajada al step, subida al
retorno; escala 1.00→0.50; p99 39→73→19→10 ms). Para que la **magnitud y re-incorporación a
banda** sean válidas, DIST debe completar ~160 s por debajo de ~90 °C: entrada ≤40 °C (§7.3-A) o
ramp más lenta con governor activo (§7.3-B, requiere mini-test read-only N=2 antes de ejecutar
S2). Si ninguna se adopta, DIST se ejecuta igual y sus ventanas que crucen el umbral se marcan
`THERMALLY CONFOUNDED` → R7 clasificado `DIAGNOSTIC — NOT FOR VERDICT` (nunca PASS/FAIL).

---

## 4. Evaluación de los 5 esquemas de cooldown (con fundamento, no intuición)

| Esquema | Veredicto (datos) |
|---|---|
| 1. Antes de cada trial | **RECOMENDADO.** Es el único que garantiza entrada ≤50 °C a todos; sin él gov1 hereda ~69 °C y llega a ~106 °C (60 s FIXED + 120 s GOV sin pausa = +186 °C·s). |
| 2. Entre FIXED y GOV | **SUBSUMIDO por (1)** en orden alternado: el cooldown "entre cada trial consecutivo" ya separa FIXED_i de GOV_i y GOV_i de FIXED_{i+1}. Solo (2) sin (1) es insuficiente (fixed2 heredaría calor de gov1). |
| 3. Entre réplicas (pares i) | **Cubierto por (1)**: los pares {FIXED_i, GOV_i} ya quedan separados por cooldown. No se necesita un cooldown adicional "entre réplicas". |
| 4. Durante trials largos (segmentación) | **RECHAZADO**: invalida la lógica de ventanas/reloj y re-dispara los steps del harness (demostrado §6-G). No hay segmentación sin tocar código. |
| 5. Combinación | **El diseño v2.3 = (1)+monitor por ventana**: cooldown telemétrico entre cada trial consecutivo (incluye 2 y 3) + regla de validación por ventana + tratamiento específico de DIST. |

---

## 5. Diagrama / secuencia exacta v2.3 (Phase 2)

Orden S1 (session 1): `FIXED₁ GOV₁ FIXED₂ GOV₂ FIXED₃ GOV₃ DIST₁ DIST₂`
Orden S2 (contrabalanceo): `GOV₁ FIXED₁ GOV₂ FIXED₂ GOV₃ FIXED₃ DIST₁ DIST₂`

```
[Fin Fase 1 → FREEZE(T=9.168, s*=0.75) → frozen.sha256]
            │
            ▼  COOL 0 ── condición: T≤50 °C s30s ∧ SCLK nv0 ∧ P<4 W   (idéntica a v2.2)
    FIXED₁ [60 s, s=1.00, governor OFF]  ──► verificación por ventana (SCLK/T)
            ▼  COOL 1
    GOV₁   [120 s, governor ON]          ──► verificación por ventana (SCLK/T)
            ▼  COOL 2
    FIXED₂ ──► COOL 3 ──► GOV₂ ──► COOL 4 ──► FIXED₃ ──► COOL 5 ──► GOV₃
            ▼  COOL 6
    DIST₁  [200 s, governor ON, N:4→8→4 a +60/+120]
            ▼  COOL 7  (si DIST exige entrada ≤40 °C: condición T≤40 °C s30s ∧ SCLK nv0 ∧ P<4 W)
    DIST₂
            ▼
[post_flight → snapshot read-only → análisis Phase 2]
```

- **Condición de entrada térmica (cada trial):** `T≤50 °C sostenido ≥30 s ∧ SCLK nivel 0 ∧ P<4 W`
  (DIST: `T≤40 °C` si se adopta §7.3-A; decisión antes de ejecutar, documentada aquí o en el
  resultado del mini-test).
- **Condición de salida/recuperación:** la misma condición de retorno se usa como condición de
  recuperación entre trials (es idéntica a la de entrada; no hay "salida" distinta). Regla de
  aborto por ventana: T>90 °C o SCLK<1071 sostenido en la ventana → ventana `THERMALLY CONFOUNDED`
  (no se corta el trial; se excluye la ventana del análisis y se registra).
- **Nada más cambia:** governor.py, harness, analyze.py, workload, seed, escalas, thresholds,
  duraciones nominales, réplicas y criterios R1–R7/F1–F6 idénticos a v2.2.

---

## 6. Demostración de que GOV y FIXED siguen siendo comparables (v2.3)

1. **Misma condición inicial**: ambos entran a ≤50 °C ∧ SCLK nv0 ∧ P<4 W (cooldown previo a cada
   trial). La condición es idéntica a la que validó Fase 1 v2.2 (que dio GATEs PASS).
2. **Mismo régimen de clock en las ventanas de medición**: con entrada ≤50 °C, FIXED termina
   ≈69 °C y GOV ≈87 °C, los dos por debajo de 90 °C (límite de no-degradación verificado en N=2)
   → SCLK 1071 en las ventanas de settle (últimas 2). Verificación post-hoc por telemetría.
3. **El frametime a SCLK 1071 es insensible a T en [55, 87] °C**: evidencia directa Fase 1 v2.2
   (open-loop p1/p2/p3 = 11.46/11.45/11.46 ms con perfiles térmicos diferentes). Por tanto la
   diferencia 69 vs 87 °C entre FIXED y GOV no introduce sesgo en p99: solo el controlador de
   escala diferencia las condiciones.
4. **Riesgo residual**: GOV a 87 °C tiene 3 °C de margen sobre 90 °C. Mitigación: la regla de
   aborto por ventana (si alguna ventana de settle cruza el umbral se excluye/marca) y la opción
   de exigir entrada ≤48 °C a GOV si el margen se considera insuficiente (mismo mecanismo
   telemétrico, solo se estrecha el umbral — decisión del operador, documentada).

## 7. Tratamiento de DIST (trials de 200 s) — 3 opciones

**7.3-A Entrada fría dedicada (recomendada si no se quiere más medición previa).**
DIST₁ y DIST₂ con cooldown de entrada a **≤40 °C** (misma métrica, umbral más bajo). Con
ramp 0.31, 92 °C se alcanzaría a ~168 s → las ventanas de re-incorporación post-retorno
(hasta ~160 s) quedan por debajo del umbral. Coste: cooldown más largo (UNKNOWN; el tramo
50→40 °C no está medido — se registra tiempo real, sin tope de seguridad anti-deadlock 60 min).
Riesgo: si la ventilación PWM ambiente no alcanza ≤40 °C, el cooldown no retorna → se registra y
se pasa a 7.3-C con causa documentada (no es parada, es decisión pre-registrada).

**7.3-B Mini-test read-only de ramp con governor activo (N=2) ANTES de ejecutar S2.**
Mide la ramp real a s≈0.5/0.62 con SCLK 1071 (potencia esperada ~15–18 W vs 23.5 W de N=2 a
s=1.00) y el tiempo de cooldown 50→40 °C. Si la ramp efectiva tras la bajada de escala es
≤0.21 °C/s, el DIST completo de 200 s cabe desde ≤50 °C (92 °C a ~200 s) sin entrada fría.
Convierte el UNKNOWN en dato, siguiendo el principio "no asumir". Read-only, ~15 min, no toca S1.

**7.3-C Conservadora (sin nueva medición ni entrada fría).**
DIST igual que hoy (entrada ≤50 °C). Las ventanas que crucen T>90 °C o SCLK<1071 se marcan
`THERMALLY CONFOUNDED`; R7 se evalúa solo con las válidas y se clasifica
`DIAGNOSTIC / THERMALLY CONFOUNDED — NOT FOR VERDICT` (nunca PASS/FAIL). No resuelve R7 completo,
pero es honesto con la física.

> **Recomendación:** 7.3-B si el usuario quiere R7 íntegro y científicamente limpio; 7.3-A si se
> quiere proceder ya con el mínimo cambio; 7.3-C como red de seguridad documentada.

---

## 8. Impacto esperado sobre la duración total

Estimado (lineal sobre cotas medidas):

| Componente (por sesión) | v2.2 (base real) | v2.3 estimado |
|---|---|---|
| Fase 1 + FREEZE + análisis | ~14–16 min | = (sin cambios) |
| Phase 2 trials (carga) | ~16 min | ~16 min (duraciones intactas) |
| Cooldowns Phase 2 (8 × 255–270 s) | 0 | **~34–36 min** |
| Cooldowns Phase 2 con DIST ≤40 °C | 0 | +4–6 min (2 cooldowns más largos) |
| **Total por sesión** | **~32 min** | **~65–72 min** |
| **S1 + S2** | ~64 min | **~2.2–2.4 h** |

El dominio del coste es el cooldown pasivo (física del SRP, 255–270 s por tramo 74→50 °C). No hay
forma de reducirlo sin escrituras (ventilador) o carga ajena al protocolo.

## 9. Riesgos metodológicos (declarados)

1. **Ramp estimada, no medida, en régimen de governor activo** (UNKNOWN). Mitigado por 7.3-B o por
   la regla de aborto por ventana que nunca mezcla datos degradados.
2. **DIST con entrada ≤40 °C puede no alcanzarse** por ventilación ambiente. Mitigado: condición
   operativa con anti-deadlock 60 min y decisión pre-registrada de caer a 7.3-C.
3. **GOV a ~87 °C roza el umbral de 90 °C** (margen 3 °C). Mitigado: verificación por ventana +
   opción de entrada ≤48 °C; el settle GV = últimas 2 ventanas (~80–120 s, ~75–87 °C).
4. **Comparabilidad FIXED/GOV** preservada por (a) misma entrada, (b) insensibilidad del p99 a T a
   SCLK 1071 en [55,87] °C (evidencia Fase 1), (c) exclusión de ventanas fuera de umbral.
5. **No confundir "dirección correcta de R7" con "R7 cumplido"**: en fase DIAGNOSTIC, DIST muestra
   la respuesta estructural (dirección y timing) pero NO la magnitud/banda. No se declara PASS.
6. **Read-only intacto**: cooldown pasivo nunca escribe sysfs/kernel; se registra tiempo y
   telemetría como en v2.2; verificación pre/post fligth (DPM/kalm/power1_cap) igual que v2.2.

## 10. Auditoría: variables del protocolo NO modificadas por v2.3

| Variable | v2.2 (frozen) | v2.3 |
|---|---|---|
| T (congelado) | 9.168 ms (sha256 `6b6d6952…`) | **igual** |
| s\* | 0.75 | **igual** |
| Escalas | {1.00, 0.87, 0.75, 0.62, 0.50} | **igual** |
| Banda / thresholds | [0.90,1.10]·T; overshoot ≤1 %/≤2 % | **igual** |
| R1–R7 (definiciones y umbrales) | v2.1 | **igual** |
| F1–F6 (falsación) | v2.1 | **igual** |
| Workload / seed / textura / N | N=4, seed `0x5EED0000` | **igual** |
| Duraciones trials | 60/120/200 s (10 ventanas DIST) | **igual** |
| Steps DIST | +60/+120 s internos del harness | **igual** |
| Réplicas / diseño pareado | 6 pares + 4 DIST, 2 sesiones | **igual** |
| governor.py / harness / analyze.py | inmutables | **igual** |
| **Cambia SOLO** | — | **cooldown telemétrico entre trials de Phase 2 (+ umbral de entrada DIST según §7.3) y regla de validación por ventana (post-hoc)** |

## 11. Clasificaciones (tal como solicita el usuario)

- **Phase 2 de S1-v2.2 (todos los trials): `DIAGNOSTIC / THERMALLY CONFOUNDED — NOT FOR VERDICT`.**
  No se declara R1–R7 PASS ni FAIL con estos datos. Evidencia: 0 de 8 trials con ventanas de
  medición íntegras en régimen 1071 (solo fixed1 conserva v0–v1 limpias).
- **Fase 1 de S1-v2.2 (FREEZE): VERIFIED/DERIVED según RESULTADOS §1C — se conserva íntegra**
  (térmicamente válida: 15/15 bloques a 1071, histéresis 0.26 %, T_max 86 °C).
- **Estado posterior D6:** S1-v2.3 fue EJECUTADA/COMPLETADA; S2-v2.3 fue INICIADA y quedó
  PARADA D antes de Phase 2. El veredicto global es INCONCLUSO/INCONCLUSIVE. La frase
  «S2 NO iniciada» de la propuesta es únicamente un snapshot pre-run.

## 12. Archivos y estado

- Este documento: `EXP-F4-A-PROTOCOL-v2.3-PROPUESTA.md` (propuesta histórica, no normativa).
- Datos S1-v2.2: `results/session1-v22/` (íntegros e inmutables).
- Análisis: `/tmp/opencode/audit_p2_thermal.py` (duraciones/cronología térmica por trial),
  `/tmp/opencode/audit_power_win.py` (potencia por ventana).
  **Ambos PERDIDOS / NO VERIFICABLES** (artefactos volátiles no preservados; no reconstruidos).
- **No queda pendiente reintentar S2-v2.3.** Cualquier réplica futura es un protocolo
  nuevo y requiere autorización nueva; no se reactiva esta propuesta histórica.
