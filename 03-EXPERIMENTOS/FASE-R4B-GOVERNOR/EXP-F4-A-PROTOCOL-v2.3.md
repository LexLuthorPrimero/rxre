# PROTOCOLO v2.3 — FASE R-4B / EXP-F4-A: CONTROL TÉRMICO DE PHASE 2

**Fecha de documentación:** 2026-09-23 · **Estado:** DOCUMENTADO — PENDIENTE DE
AUDITORÍA PRE-RUN Y CONFIRMACIÓN DEL USUARIO (no se ha ejecutado ninguna trial).

**Base normativa (fuentes de verdad, en orden):**
1. `EXP-F4-A-PROTOCOL.md` — protocolo v2.1: Fase 1 open-loop, GATEs (§6), orden de
   sesiones (§7), R1–R7 pre-committed (§12), F1–F6, workload, governor, duraciones.
2. `EXP-F4-A-PROTOCOL-v2.2.md` — variación procedimental autorizada: cooldown
   telemetrico entre passes de Fase 1 (DN-07, ≤50 °C). **La ENTRADA en Phase 2 de
   v2.2 NO tenía cooldown por trial** (defecto que v2.3 corrige).
3. `EXP-F4-A-PROTOCOL-v2.3-PROPUESTA.md` — análisis A–G, presupuesto térmico,
   condiciones DIST §7.3-A/B/C, diagrama de Phase 2 (§5).
4. `EXP-F4-A-MINITEST-RAMP-GOV-PLAN.md` + `RESULTADOS-MINITEST-7.3-B.md` —
   medición real de la ramp con governor activo (N=2, 2026-09-23 01:19–01:39).

---

## 1. Definición y alcance del cambio (ÚNICA variación vs v2.1/v2.2)

**v2.3 = cooldown telemétrico antes de CADA trial consecutivo de Phase 2**
(incluido el primero tras FREEZE), con umbrales de entrada **más estrictos por tipo
de trial** y registro del tiempo real de cada cooldown.**

| Elemento | v2.1 | v2.2 | **v2.3 (esta versión)** |
|---|---|---|---|
| Fase 1 open-loop (15 bloques, passes asc/desc/asc) | sí | sí | **sí, idéntico** |
| Cooldown entre passes de Fase 1 (DN-07 ≤50 °C) | no | sí | **sí, idéntico a v2.2** |
| Cooldown antes de cada trial de Phase 2 | **no** | **no (defecto)** | **SÍ, antes de cada uno** |
| Entrada FIXED/GOV | libre | libre | **≤50 °C + DN-07** |
| Entrada DIST | libre | libre | **≤50 °C + DN-07** (antes: ≤35 °C según 7.3-A; **revocado por el usuario 2026-09-23**, ver §1.1) |
| Estatus DIST en el veredicto | — | — | **DIAGNOSTIC / NOT FOR VERDICT** (opción 3 autorizada); R7 NO se evalúa |
| Registro de cooldown | no | fase1/cooldown{1,2}.tsv | **fase2/cool{idx}.tsv por trial** |
| Abort térmico ≥96 °C | — | — | **sí (monitor read-only)** |
| Todo lo demás (workload, T, s*, escalas, thresholds, R1–R7, F1–F6, orden de trials, duraciones, lógica temporal DIST, análisis) | — | — | **INVARIANTE (sin cambios)** |

---

## 2. Invariantes ABSOLUTOS (prohibido alterar)

- **T = 9.168 ms** (·0.80·P99(1.00), Fase 1 limpia de S1-v2.2, manifest `6b6d6952…`).
  En las sesiones v2.3 se **volverá a calcular T/s\* con la Fase 1 de cada sesión** y
  se **verificará** que el resultado coincide con el FREEZE congelado (GATEs +
  reachability; PARADA D si discrepa).
- **s\* = 0.75**; banda governor `[0.90·T, 1.10·T]` = [8.251, 10.085] ms.
- Escalas open-loop: 1.00 / 0.87 / 0.75 / 0.62 / 0.50.
- Workload: harness `governor_harness` (Vulkan, vendor 0x1002 / device 0x699F),
  seed `0x5EED0000`. Prohibido recompilar/modificar fuente o binario.
- Governor: `controller/governor.py` (sin modificaciones).
- El análisis `harness/scripts/analyze.py` no se modifica. `final()` usa
  `results/v23/session1` + `results/v23/session2` (ver §7).
- Número de trials: 8 por sesión (`3 FIXED + 3 GOV + 2 DIST`), órdenes:
  - S1-v2.3: `fixed gov fixed gov fixed gov dist dist`
  - S2-v2.3: `gov fixed gov fixed gov fixed dist dist`
- Duraciones: FIXED 60 s, GOV 120 s, DIST 200 s, warm 5 s, telemetría 10 Hz.
- Lógica temporal DIST: step N:4→8 a `t0+60 s`, retorno N:8→4 a `t0+120 s`,
  ventanas de 20 s ancladas a `t0` (= `run_m0.txt`), corte en `end_us = t0+duration`.
  **Prohibido relanzar/segmentar el governor.**
- R1–R6 literales "≥5/6"; R7 literal "4/4"; R5 comparación inter-sesión
  S1-v2.3 vs S2-v2.3. **No se modifica ningún umbral para hacer viable el resultado.**
- **Cero writes** GPU/sistema/Mesa/kernel/PowerPlay/sysfs/registros/contadores.
  Única escritura fuera de `results/`: `control_scale.txt` dentro de cada trial.
- **Solo unions de sesiones v2.3** entran en T, s\*, R1–R7, veredicto. **TODOS los
  datos de S1-v2.1, S1-v2.2 y del mini-test quedan EXCLUIDOS del veredicto.**

---

## 3. Condición de entrada térmica (DN-07) por trial de Phase 2

Cada trial de Phase 2 (el 1º y los 7 restantes) requiere **antes de arrancar**:

```
ENTRADA OK ⟺  T ≤ UMBRAL   ∧   SCLK activo = nivel 0   ∧   P < 4 W
             (sostenido ≥30 s, muestras consecutivas de 5 s)
```

- **FIXED (60 s):** UMBRAL = **50 °C** (como v2.2).
- **GOV (120 s):** UMBRAL = **50 °C**.
- **DIST (200 s):** UMBRAL = **50 °C** (revisado por el usuario el 2026-09-23 tras el
  hallazgo térmico; sustituye la entrada ≤35 °C de 7.3-A, cuyo único propósito era
  sanear R7, hoy NOT FOR VERDICT — ver §1.1).
- Se registra en `fase2/cool{idx}.tsv`: label, inicio/fin (mono ns), `dur_ms`,
  `dur_s`, `ret_temp_mC`, `ret_sclk_nivel`, `ret_power_uW` (formato idéntico a
  `fase1/cooldown*.tsv` de v2.2).
- **Anti-deadlock:** 3600 s por cooldown. Si un trial no alcanza su umbral antes del
  tope → **NO se inicia el trial** y se registra la causa (`THERMALLY CONFOUNDED —
  ENTRY TIMEOUT`) en `fase2/omissions.json`, continuando con el siguiente trial si es
  posible.
- **Abort de seguridad:** durante la ejecución de cualquier trial, si la telemetría
  (monitor read-only, 1 Hz) detecta `temp1_input ≥ 96 °C` → SIGTERM al harness,
  el trial se marca `ABORTADO (T≥96 °C)` y se documenta el evento. No continúa la
  sesión automáticamente: se reporta y se espera decisión.

---

## 4. Secuencia exacta de cada sesión v2.3

```
[pre_flight: snapshot DPM/kalm read-only]
   → warm-up global 30 s a s=1.00 (excluido del análisis)
   → FASE 1: 15 bloques open-loop (p1 asc, cooldown1, p2 desc, cooldown2, p3 asc)
   → FREEZE(T, s*) con GATEs de §6 (PARADA D si fallan) + frozen.sha256
   → PHASE 2: por cada trial en orden de sesión:
        COOLDOWN previo (DN-07, umbral 50 °C uniforme) + cool{idx}.tsv
        run_trial (fixed/gov/dist) con telemetría + monitor de abort T≥96 °C
   → post_flight: snapshot read-only + verificación DPM/kalm pre↔post
   → analyze.py phase2 (por sesión)
```

Orden de trials:
- **S1-v2.3** (sesión 1): `FIXED₁ GOV₁ FIXED₂ GOV₂ FIXED₃ GOV₃ DIST₁ DIST₂`
- **S2-v2.3** (sesión 2, contrabalanceo): `GOV₁ FIXED₁ GOV₂ FIXED₂ GOV₃ FIXED₃ DIST₁ DIST₂`

Cooldowns por sesión: 8 (uno antes de cada trial). El COOL 6 (antes de DIST₁) usa
umbral 35 °C; el COOL 7 (antes de DIST₂) también.

---

## 5. Monitor read-only de progreso (durante S2-v2.3)

Mientras corre la sesión, se muestrea (sin escribir nada en el sistema):
`sesion | trial | fase | tiempo transcurrido | ETA | temp1_input | SCLK activo |
estado del cooldown`. Fuente: `sysfs` (`/sys/class/drm/card1/device/hwmon/hwmon2`)
y `pp_dpm_sclk`. **El monitor NUNCA escribe sysfs ni interviene en el governor.**

---

## 6. Veredicto y clasificación (inalterables)

### 6.1 R1–R7 (pre-committed, §12 de v2.1)

- **R1** r ∈ [0.90, 1.10] ∧ CI bootstrap 90 % ⊂ (≥5/6 GOV).
- **R2** overshoot ≤1 % (≥5/6) y ≤2 % (todas); 0 ventanas p99 > 1.10·T en settle.
- **R3** 0 reversiones sostenidas.
- **R4** convergencia ≤4 ventanas (80 s).
- **R5** CV ≤10 %; mediana S2-v2.3 vs S1-v2.3 difiere ≤15 %; dirección predicha ≥90 %.
- **R6** permanencia/Δ sin re-incursiones en stabilize/settle.
- **R7** 4/4 DIST con latencies LOW/RAISE/re-incorporación ≤2 ventanas.
  **PERO en v2.3 (opción 3 autorizada) los DIST son DIAGNOSTIC / NOT FOR VERDICT:
  R7 NO se evalúa para el veredicto, se reporta por separado como INCONCLUSIVE /
  NOT FOR VERDICT y NUNCA se usa para declarar PASS.**
- Settle: últimas 2 ventanas (GOV v5–v6; FIXED 2 de 3). Ventanas 20 s ancladas a t0.

### 6.2 F1–F6 (falsaciones) y veredicto
Según `analyze.py final()`: `HIPÓTESIS APOYADA` solo si **R1 ∧ R2 ∧ R3 ∧ R4 ∧ R5
∧ R6 ∧ R7** formales; sino `INCONCLUSO` o `FALSADO` según F1–F6. No se declara
SUPPORTED sin las 7 R formales. En v2.3, al ser **R7 no evaluable por diseño**, el
veredicto de la hipótesis global queda a lo sumo `INCONCLUSO` (nunca SUPPORTED),
con R1–R6 debidamente clasificados y R7 reportado por separado.

### 6.3 Regla de validación por ventana (red de seguridad térmica, pre-registrada)
Una ventana de Phase 2 se marca `THERMALLY CONFOUNDED` si en ella `T>90 °C` o
`SCLK < 1071 MHz` sostenido. Las ventanas marcadas **no entran** en R1–R6 ni en el
cálculo de medianas/CI/E. Para DIST: los trials se ejecutan íntegros (lógica
+60/+120 y 200 s intactas) pero esas ventanas no son evidencia de R7; los DIST se
declaran `DIAGNOSTIC — NOT FOR VERDICT` y **R7 queda INCONCLUSIVE / NOT FOR
VERDICT** (según decisión del usuario, opción 3).

---

## 7. Análisis y productos esperados

1. **Fase 1** por sesión: `analyze.py phase1 --session-dir results/v23/session{N}`
   → `manifest.json` (T, s\*, curva, gates, sha256) → verificación vs FREEZE.
2. **Phase 2** por sesión: `analyze.py phase2 --session-dir results/v23/session{N}
   --order <orden>` → `metrics.json`.
3. **Final (ambas sesiones v2.3):**
   `analyze.py final --results-dir results/v23`
   → `verdict.json` con R1–R7, E (Wilcoxon), F1–F6 y veredicto. `final()` lee
   `session1/` y `session2/` directamente → **los datos v2.3 van en
   `results/v23/session{1,2}`** (NO tocar `results/session1` de v2.1 ni
   `results/session1-v22`).
4. **Verificación read-only:** DPM/kalm `pre_flight` ↔ `post_flight` idénticos
   (hash `ff9e8280bd…` esperado) en ambas sesiones; `power1_cap` 35 W intacto;
   SCLK idle nivel 0 al final.
5. **Informe de resultados** (`EXP-F4-A-RESULTADOS-v2.3.md`) con clasificación
   R1–R7, F1–F6, condición térmica real por trial (temp de entrada + tiempo de
   cooldown + ventanas marcadas), y veredicto. **Detenerse tras presentarlo; no se
   ejecuta nada adicional automáticamente.**

---

## 8. Exclusión definitiva de Phase 2 S1-v2.2

Toda Phase 2 de S1-v2.2 (`results/session1-v22/fase2/metrics.json`) se considera
`DIAGNOSTIC / THERMALLY CONFOUNDED — NOT FOR VERDICT` (sin cooldown por trial).
**Ningún trial de esa fase entra en T, s\*, R1–R7, E o veredicto de v2.3.** Su
Fase 1 (FREEZE `6b6d6952…`) es la fuente congelada de parametrización y se verifica,
pero la Fase 1 de cada sesión v2.3 se re-deriva con sus propios datos.

---

## 9. ANEXO — HALLAZGO DE AUDITORÍA PRE-RUN (corrige la premisa de t90)

Verificado contra los **datos crudos** `runs/minitest-ramp-gov/rep{1,2}` (telemetría
10 Hz + `m0.txt` + `cooldown_prev.tsv`):

| Magnitud | RESULTADOS-MINITEST (§4, lineal) | **Dato real alineado a m0** |
|---|---|---|
| Ramp "efectiva" | 0.246–0.252 °C/s (regresión ventanas) | tramos reales: 0–40 s **0.58** · 40–80 s 0.30 · 80–120 s 0.23 · 120–160 s 0.20 °C/s |
| t90 REP1 (entrada cooldown 33 °C) | ~229 s (lineal) | **171.9 s** (T(m0)=44 °C) |
| t90 REP2 (entrada cooldown 45 °C) | (~181 s) | **134.8 s** (T(m0)=55 °C) |
| Salto entre fin de cooldown y m0 | no modelado | **+10…11 °C** (warm 5 s + arranque, p. ej. 33→44 REP1; 45→55 REP2) |

### 9.1 Consecuencias para v2.3 (presupuesto corregido)

- La extrapolación lineal "t90≈221 s desde ≤35 °C" **NO es válida**: ignora el tramo
  inicial rápido (~0.58 °C/s) y el salto cooldown→m0. Con dato alineado a m0,
  **t90(desde 35 °C) ≈ (90 − ~46) / 0.26…0.33 ≈ 130…170 s, es decir MENOR que 200 s
  en el escenario peor y marginal/borde en el mejor.**
- Consecuencia en v2.3 real (con entrada ≤50 °C para los DIST, según decisión opción
  3): **el DIST de 200 s cruza T>90 °C / SCLK<1071 más temprano aún** (parte de
  ~61 °C en m0 en lugar de ~46 °C), por lo que las últimas 2–4 ventanas pueden
  quedar marcadas — exactamente lo que se quiere DOCUMENTAR como observación del
  presupuesto térmico terminal. No es una anomalía: la regla por ventana (§6.3) lo
  marca, los DIST son DIAGNOSTIC y **no alimentan R1–R6 ni R7**.
- **No se refuerza la condición ni se retoca nada**: la entrada DIST es ≤50 °C
  (estándar), se respeta íntegra la duración de 200 s y la lógica +60/+120, y **no
  se modifica ningún threshold ni ventana** para rescatar R7.
- gobernador + workload + semántica temporal quedan VERIFICADOS en el mini-test;
  el único factor limitante es el presupuesto térmico del tramo final → manejado por
  la regla por ventana (no por cambios de código).

### 9.2 Estado de este anexo — DECISIÓN DEL USUARIO (opción 3, 2026-09-23)
El hallazgo **no cambia los invariantes** y fue presentado al usuario como parte de
la auditoría pre-run (item 11 de la autorización). El usuario autorizó la **opción
3**: R1–R6 con los 6 GOV + 6 FIXED (entrada ≤50 °C), y los 4 DIST como
DIAGNOSTIC / NOT FOR VERDICT con R7 INCONCLUSIVE — sin uso de los DIST para PASS
de R7, sin modificar ventanas ni duración. Con ello, **S1-v2.3 y S2-v2.3 quedan
autorizados para ejecutarse** conforme a este protocolo y a `run_all_v23.sh`.