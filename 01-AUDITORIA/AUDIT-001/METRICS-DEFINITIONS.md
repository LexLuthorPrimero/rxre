# METRICS-DEFINITIONS.md — Definiciones Formales de Métricas de Potencia

**Fecha:** 2026-09-21  
**Versión:** 1.0  
**Estado:** OBLIGATORIO para todos los experimentos presentes y futuros

---

## 1. Definiciones Inmutables

### 1.1 `power_avg_full` — Media de Ventana Completa
> **Definición:** Media aritmética de `power1_input` (µW) sobre **TODA** la ventana de telemetría capturada, desde la primera muestra hasta la última, sin descartes.
>
> **Incluye:** idle inicial, ramp-up, warm-up, fase de medición activa, cooldown final, cualquier transiente.
>
> **Unidad:** W (watts) — `power1_input / 1_000_000`
>
> **Fórmula:** `power_avg_full = (Σ power1_input[i]) / N` para i = 1..N muestras totales

### 1.2 `power_avg_steady` — Media de Régimen Estable
> **Definición:** Media aritmética de `power1_input` **exclusivamente** en la ventana de régimen estable (steady window).
>
> **Criterios de inclusión (TODOS obligatorios):**
> - `gpu_busy_percent ≥ 95` (estado de carga sostenida)
> - `sclk_hz ≥ 1_071_000_000` (SCLK en nivel máximo DPM — nivel 7 en esta RX 550)
> - `mclk_hz ≥ 1_500_000_000` (MCLK en nivel máximo DPM — 1500 MHz)
>
> **Exclusiones obligatorias:**
> - Primeras ~5 segundos de la corrida (ramp-up, cold cache, warm-up transitorio)
> - Última muestra de la ventana (edge effects, posible inicio de cooldown)
>
> **Unidad:** W
>
> **Fórmula:** `power_avg_steady = (Σ power1_input[i]) / N_steady` para i ∈ steady_window

### 1.3 `power_max` — Máximo Observado
> **Definición:** Valor máximo de `power1_input` observado en la ventana indicada.
>
> **Nota:** Debe reportarse siempre con especificación de la ventana:
> - `power_max_full` — máximo en ventana completa
> - `power_max_steady` — máximo en ventana de régimen estable
>
> **Unidad:** W

### 1.4 `steady_window_definition` — Definición de Ventana de Régimen
> **Definición operacional:**
>
> 1. Capturar telemetría completa a 10 Hz (período = 100 ms)
> 2. Identificar `t_start_steady`: primera muestra donde `gpu_busy ≥ 95` Y `sclk ≥ 1071 MHz` Y `mclk ≥ 1500 MHz` **después** de descartar las primeras ~50 muestras (~5s)
> 3. Identificar `t_end_steady`: última muestra antes de la última donde se cumplen los criterios
> 4. Ventana steady = muestras [`t_start_steady` .. `t_end_steady`]
>
> **Criterios de validación de la ventana:**
> - Debe contener ≥ 100 muestras (≥ 10 segundos de régimen)
> - Si no se alcanza → reportar `power_avg_steady = N/A` y `power_max_steady = N/A`

---

## 2. Reglas de Uso Obligatorias

### 2.1 Reporte Unificado
**Todos** los experimentos futuros deben reportar **las 4 métricas** en sus resultados:
```
power_avg_full:    X.XX W
power_avg_steady:  Y.YY W
power_max_full:    Z.ZZ W
power_max_steady:  W.WW W
steady_window_samples: N
steady_window_duration_s: S.S
```

### 2.2 Comparación Histórica
**Regla estricta:** Al comparar resultados históricos que usen definiciones diferentes, marcar **explícitamente** en tablas y texto:

> `NOT DIRECTLY COMPARABLE`

**Ejemplo prohibido (sin etiqueta):**
> "E-03 reportó 13.40 W y el régimen estable es 15.75 W → la potencia subió 2.35 W" ❌

**Ejemplo correcto (con etiqueta):**
> "E-03 reportó `power_avg_full = 13.40 W`. El régimen estable en la misma corrida fue `power_avg_steady = 15.75 W`. **NOT DIRECTLY COMPARABLE** — definiciones diferentes." ✅

### 2.3 Referencia Histórica (E-03 Original)
Para trazabilidad, los valores originales de E-03 corregida:
- `power_avg_full`: 13.40 W (277 muestras, ventana ~27.7s)
- `power_avg_steady`: 15.75 W (218 muestras, gpu_busy≥95, SCLK=1071, MCLK=1500)
- `power_max_full`: 15.81 W
- `power_max_steady`: 15.80 W

---

## 3. Métricas Auxiliares (Opcionales pero Recomendadas)

| Métrica | Definición | Uso |
|---|---|---|
| `gpu_busy_avg_steady` | Media de `gpu_busy_percent` en ventana steady | Verificar carga real |
| `mem_busy_avg_steady` | Media de `mem_busy_percent` en ventana steady | Verificar presión memoria |
| `sclk_distribution` | Distribución de niveles `pp_dpm_sclk` en ventana steady | Verificar clocks |
| `mclk_distribution` | Distribución de niveles `pp_dpm_mclk` en ventana steady | Verificar MCLK |
| `temp_avg_steady` | Media de `temp1_input` (mC) en ventana steady | Contexto térmico |
| `vram_avg_steady` | Media de `mem_info_vram_used` en ventana steady | Contexto VRAM |
| `gtt_avg_steady` | Media de `mem_info_gtt_used` en ventana steady | Contexto GTT |

---

## 4. Historial de Cambios

| Versión | Fecha | Cambio | Autor |
|---|---|---|---|
| 1.0 | 2026-09-21 | Definición inicial formal | FASE A.2 |