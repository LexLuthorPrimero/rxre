# AUDITORÍA PRE-RUN — PROTOCOLO v2.3 (EXP-F4-A)

**Fecha:** 2026-09-23 · **Modo:** 100 % read-only (cero escrituras GPU/sistema/Mesa/
kernel/sysfs/contadores; únicos archivos creados: documentación + orquestador v23
no ejecutado). **Resultado global: INVARIANTES INTACTOS — PENDIENTE de confirmación
del usuario para ejecutar S1-v2.3.**

---

## 1. Hashes de los artefactos críticos (vs. registro del checkpoint)

| Artefacto | sha256 (verificado hoy) | mtime | Estado |
|---|---|---|---|
| `controller/governor.py` | `1aa8aa85c422…9750a` | 2026-09-22 23:13:47 | sin cambios ✓ |
| `harness/app_vulkan.c` | `51d814c51001…b5dc` | 2026-09-22 23:25:30 | sin cambios ✓ |
| `harness/scripts/analyze.py` | `28fab2cba903…ee06` | 2026-09-22 23:31:36 | sin cambios ✓ |
| `telemetry/telemetria.sh` | `922c429b9a78…2e6` | 2026-09-22 23:19:37 | sin cambios ✓ (read-only 10 Hz confirmado) |
| `run_all_v22.sh` (base) | `92c8b191476f…c69` | 2026-09-23 00:12:17 | sin cambios ✓ |

Los mtimes de governor/app_vulkan/analyze/telemetria son **anteriores al mini-test
(01:19–01:39 09-23)** → los datos crudos que sustentan el hallazgo térmico no
alteraron ningún invariante.

**Nuevos artefactos v2.3 (creados hoy, NO ejecutados):**
- `EXP-F4-A-PROTOCOL-v2.3.md` (mtime 02:13:53) — protocolo formal + anexo §9.
- `run_all_v23.sh` — sha256 `1f66bc5c67b1…e0d9`, `bash -n` OK, diff auditado.

## 2. Invariantes verificados en el código (read-only)

1. **governor.py:** banda `[0.90·T, 1.10·T]`; BAJADA si p99>1.10·T ≥2 ventanas
   consecutivas; SUBIDA si p99<0.90·T ≥2 ventanas (y s<1.00); `SCALES =
   [1.00, 0.87, 0.75, 0.62, 0.50]`; `WINDOW_S = 20.0`; ventana k = `[t0+k·20s, …)`.
2. **app_vulkan.c (líneas ~757-765):** lógica temporal DIST intacta — step N:4→8 a
   `elast≥60.0`, retorno N:8→4 a `elast≥120.0`, sin re-anclaje de ventanas.
3. **analyze.py R1–R7 literales:** R1 ≥5/6 ∧ CI 90 % ⊂ [0.90,1.10]; R2 overshoot
   ≤1 % (≥5/6) ∧ ≤2 % (todas); R3 ≥5/6 reversiones 0; R4 ≥5/6 convergencia ≤4
   ventanas; R5 CV ≤10 % ∧ mediana S1/S2 ≤15 % ∧ dirección ≥90 %; R6 ≥5/6
   Δpasos(settle vs s\*)=0; **R7 4/4** (ok_low==ok_raise==ok_reinc==4, latencias
   LOW/RAISE/reinc ≤2.0 ventanas). `final()` lee `session1`+`session2` → **los
   datos v2.3 van en `results/v23/session{1,2}`** (confirmado: no existe hoy).
4. **Manifest congelado S1-v2.2:** T=9.168, s\*=0.75, P99_curve 11.46/9.351/7.02/
   4.9/2.851, gates 100 % PASS, sha256 `6b6d69522e604529…d67ca` — **intacto.**
5. **Verificación read-only pre↔post:** DPM/kalm `ff9e8280bda6…` idénticos en
   session1-v22 (pre≡post); `power1_cap = 35000000` (35 W) intacto.
6. **Órdenes/duraciones:** S1 `fixed gov fixed gov fixed gov dist dist`; S2
   `gov fixed gov fixed gov fixed dist dist`; fixed 60 / gov 120 / dist 200 / warm
   5 / telemetría +12 s — fieles en `run_all_v23.sh`.
7. **Exclusión NOT FOR VERDICT:** Phase 2 de S1-v2.2 (`session1-v22/fase2`) queda
   DIAGNOSTIC; `session1` (v2.1, PARADA D) y `session1-v22` no se tocan.

## 3. Hallazgo de auditoría — presupuesto térmico corregido (datos crudos)

Análisis alineado a `m0` de `runs/minitest-ramp-gov/rep{1,2}` (telemetría 10 Hz):

| Magnitud | Mini-test §4 (lineal) | **Dato real alineado a m0** |
|---|---|---|
| Ramp | 0.246–0.252 °C/s | 0.58 (0–40 s) · 0.30 (40–80) · 0.23 (80–120) · 0.20 (120–160) °C/s |
| T(m0) vs fin de cooldown | (no modelado) | **+10…11 °C** (warm 5 s + arranque) |
| t90 REP1 (cooldown 33 °C) | ~229 s | **171.9 s** (T(m0)=44 °C) |
| t90 REP2 (cooldown 45 °C) | (~181 s) | **134.8 s** (T(m0)=55 °C) |

**Implicación:** la premisa de la decisión 7.3-A (entrada DIST ≤35 °C con
t90≈221 s>200 s y 20 s de margen) **NO es válida**. Con la curva real,
`t90(entrada cooldown X) ≈ (90 − (X+11)) / 0.26`:
- FIXED 60 s desde ≤50 °C → ~80 °C final → **seguro**.
- GOV 120 s desde ≤50 °C → cruza ~90 °C a ~111 s → **ventana settle v6 (100–120 s)
  en el borde/riesgo**.
- DIST 200 s → con la entrada final decidida (≤50 °C), parte de ~61 °C en m0 y cruza
  ~90 °C en ~111–169 s (más temprano que desde 35 °C), dejando las últimas 2–4
  ventanas en zona confounded — se ejecuta como observación térmica DIAGNOSTIC / NOT
  FOR VERDICT (opción 3 del usuario).

`RESULTADOS-MINITEST-7.3-B.md` es internamente contradictorio: §3.1 mide
t90=171.9 s (cooldown 33 °C) mientras §4/§5.2 afirma ~221 s usando la rampa de
regresión 0.246–0.252 sobre T_med de ventanas limpias (arrancando en 48.5 °C),
ignorando el salto del warm-up y el tramo inicial rápido.

## 4. Qué NO se ha hecho (limitación estricta)

- **NO se ha ejecutado** S1-v2.3 ni S2-v2.3 (no existe `results/v23`, no hay logs
  v23). Nada automático tras S2.
- **NO se ha modificado** ningún invariante ni umbral (R1–R7 literales, T, s\*,
  escalas, governor, harness, analyze.py, telemetria.sh).
- Se **documenta** el hallazgo en el protocolo (§9) y la regla de validación por
  ventana como red de seguridad pre-registrada (§6.3): ventana con T>90 °C o
  SCLK<1071 → `THERMALLY CONFOUNDED`, excluida de R1–R7.

## 5. Pendiente de decisión del usuario (bloquea S1)

Ver protocolo §9.2. **DECIDIDO 2026-09-23 (opción 3):** R1–R6 se evalúan con los 6
GOV + 6 FIXED (entrada ≤50 °C + DN-07); los 4 DIST son DIAGNOSTIC / NOT FOR
VERDICT con R7 INCONCLUSIVE — nunca se usan para PASS de R7; no se modifican
ventanas, duraciones ni umbrales; no hay cambios post hoc de criterios. La corrida
queda **autorizada e inminente** (S1-v2.3 → S2-v2.3), con informe final A–D
(R1–R6 · R7 · lección térmica RX 550 · qué es sólido para IMPLEMENTACIÓN).