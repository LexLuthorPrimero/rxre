# EXP-F4-A — PROTOCOLO v2.2 (variación procedimental autorizada)

**Fecha:** 2026-09-23 (00:10)
**Base:** `EXP-F4-A-PROTOCOL.md` = **v2.1 (FUENTE DE VERDAD, CONGELADA, no modificada)**.
**Naturaleza:** v2.2 es **ÚNICAMENTE una variación PROCEDIMENTAL** (cooldown térmico entre passes de
Fase 1). **NO modifica** workload, T, s*, render-scales, thresholds, criterios R1–R7, umbrales F1–F6,
cantidad de bloques, ni ninguna condición que pueda favorecer artificialmente al governor.
**Motivo:** la sesión 1 v2.1 terminó por **PARADA D** (histéresis asc↔desc = 58.3 % >15 %, §14-D) por
**throttling térmico** del workload (die ~92 °C, SCLK 1071→551 MHz), diagnosticado con la investigación
read-only `experiments/FASE-R4B-THERMAL-TEST/` (auditoría Kalm: no intervino; ramp 0.31 °C/s,
recuperación a ≤50 °C en 255–270 s medida; power 23.5 W < cap 35 W → throttling puramente térmico).

---

## 1. Cambio procedimental (único)

Entre los passes de Fase 1 se intercala un **cooldown pasivo** (sin writes; solo se espera):

```
p1 (asc 1.00→0.50)  →  COOLDOWN_1  →  p2 (desc 0.50→1.00)  →  COOLDOWN_2  →  p3 (asc 1.00→0.50)
```

- **No** se introduce cooldown dentro de un pass ni entre bloques individuales.
- **No** se modifican los 5 bloques por pass ni sus duraciones (warm 5 s + 20 s medidos).

### 1.1 Condición de retorno (telemétrica, no temporal)

> `temp1_input ≤ 50 °C` sostenido **≥30 s** ∧ SCLK activo = **nivel 0** (214 MHz) ∧ `power1_input < 4 W`.

- **Expectativa inicial:** ~270 s (medida REP1/REP2 del test térmico), **NO asumida como tope.**
- Si a ~270 s la condición no se cumple → **continuar enfriando hasta cumplirla** (tope de seguridad
  durísimo de 3600 s para evitar deadlock; si se excede → parada D + reporte).
- Si la condición se cumple antes → proseguir; **se registra el tiempo real** de cada cooldown
  (`fase1/cooldown{1,2}.tsv` y log).
- Justificación de 50 °C: DN-07 (decisions.md) fija cooldown a ≤50 °C para iniciar experimentos;
  margen de 42–47 °C bajo el punto de degradación sostenida observado (≥92 °C) y garantiza
  re-entrada en régimen pleno SCLK 1071 MHz.

## 2. Todo lo demás (sin cambios respecto a v2.1)

| Elemento | Estado |
|---|---|
| Workload sintético (8-tap shader, seed 0x5EED0000) | **igual** |
| Resolución / base (1920×1080) | **igual** |
| Escalas S = {1.00, 0.87, 0.75, 0.62, 0.50} | **igual** |
| T = 0.80·P99(1.00); s* = max{s: P99_openloop(s) ≤ T} | **igual**, recomputados **solo** con la nueva Fase 1 open-loop |
| GATEs §6.1.4/§6.1.5/§6.3 y histograma ≤15 % (§14-D) | **igual** |
| 15 bloques open-loop / orden p1→p2→p3 | **igual** |
| FREEZE(T, s*, sha256) en manifest antes de Phase 2 | **igual** |
| Phase 2: orden sesión 1 = `fixed gov fixed gov fixed gov dist dist` | **igual** |
| Métricas R1–R7, pregunta E, falsación F1–F6 | **igual** |
| Paradas A–D, prohibiciones §15 | **igual** |

## 3. Reglas de esta ejecución (v2.2, sesión 1)

1. La corrida se ejecuta desde `run_all_v22.sh 1` y escribe en **`results/session1-v22/`** — **no toca**
   `results/session1/` (S1 v2.1 original, PARADA D, se conserva íntegra como dato de diagnóstico).
2. **NO se reutiliza ningún resultado de S1 v2.1** para T, s*, manifest, GATEs ni veredictos: todo se
   computa exclusivamente con la nueva Fase 1 open-loop de S1-v2.2.
3. La comparación de temp/SCLK con S1 v2.1 es **solo diagnóstico** (separación de factores), nunca datos
   experimentales combinados.
4. Al terminar S1-v2.2: verificar GATEs, manifest, integridad (15/15 bloques), ausencia de writes
   (DPM/kalm/cap pre↔post), y **DETENERSE** para reportar. **NO se inicia la sesión 2 automáticamente.**
5. Si un GATE falla por causa **distinta** al problema térmico ya caracterizado → detenerse y reportar.
   No se vuelve a modificar el protocolo sin autorización.