# ERRATA.md — Correcciones al Registro Histórico

**Fecha:** 2026-09-21  
**Versión:** 1.0  
**Alcance:** Correcciones a conclusiones previas basadas en nueva evidencia documentada en AUDIT-001

---

## ERRATUM-001: Kalm y el Régimen E1/E3/E5 (17/09/2026)

### Conclusión Original (errónea)
> "El régimen E1/E3/E5 (power1≈25W, SCLK 350-390 MHz, MCLK ~1250-1500 MHz, 74-92°C) fue causado o mediado por Kalm / gobernador de potencia."

### Nueva Evidencia (AUDIT-001, FASE A.1)
- **Journal 17/09:** `kalm-gpu.service` **inactivo** (murió TERM el 18/09 a las 14:34). Cero eventos kalm el 17/09.
- **Journal 18-19/09:** `kalm real` (`kalmd.py` PID 4087, `kalm-lite.py` PID 4086) **activo y vivo**. `kalm-gpu.service` muerto.
- **Comportamiento con Kalm activo (18-19/09):** Régimen **libre** 1071 MHz / ~10 W (sweep, Fase A, B, EP-06).
- **Comportamiento sin Kalm (17/09):** Régimen **regulatorio** E1/E3/E5-baseline (power1≈cap 25W / 360 MHz).

### Corrección
- Kalm **NO fue causa** del régimen histórico E1/E3/E5; de hecho, la evidencia apunta en dirección opuesta: el régimen "libre" (1071 MHz) ocurrió **con** Kalm activo, y el régimen "regulatorio" (360 MHz, power1≈cap) ocurrió **sin** Kalm.
- El régimen 25W / 350-390 MHz / MCLK 1250-1500 / 74-92°C **no fue un techo natural de la GPU** impuesto por Kalm.
- La causa raíz del régimen del 17/09 sigue siendo **[DESCONOCIDA]** sin autorización nueva para investigar.

### Impacto en Conclusiones Anteriores
| Conclusión Anterior | Estado | Comentario |
|---|---|---|
| "Kalm limitó a 25W" | **INVALIDADO** | Régimen 25W ocurrió SIN kalm |
| "Cap 25W liga SCLK" | **INVALIDADO** | Fase B + EP-06: cap 25W NO liga SCLK |
| "25W = techo natural" | **INVALIDADO** | Valor era power1_input (estimador SMU en estado regulatorio), no draw real medido |

---

## ERRATUM-002: Power1_input como "Potencia Real"

### Conclusión Original (ambigua)
> "power1_input reporta la potencia real de la GPU en watts."

### Corrección
- `power1_input` / `power1_average` = **estimador del firmware SMU** en µW (no un vatímetro físico).
- En dGPU representa la GPU, pero **NO incluye CPU** ni consumo de placa completo.
- En E1/E3/E5 (17/09): `power1_input ≈ power1_cap` (25W) → el estimador SMU reportaba el **target de regulación**, no draw real.
- Draw real máximo medido en sesión actual (EP-06): **13.6 W** (2560×1440 texturizado, cap 35W).
- Superposition (exploratorio): **18.8 W media / 23.7 W pico** fase activa.

### Impacto
Todas las conclusiones históricas que trataron `power1_input` como "potencia real medida" deben releerse como: **"estimador SMU en estado [regulatorio/libre]"**.

---

## ERRATUM-003: Mesa CUSTOM como Causa del Consumo E5

### Conclusión Original (EP-05 inicial)
> "La Mesa CUSTOM (`/opt/mesa-26.2.2-rx550-haswell`) fue la causa del régimen E5 (25-31 W / MCLK ~1250-1500 / 74-92°C)."

### Nueva Evidencia (EP-05 A/B controlado, 19/09)
- A/B controlado intercalado CUSTOM vs STOCK, N=2 por escena, arranque frío (42°C).
- **Resultados indistinguibles:** CUSTOM vs STOCK → ΔFPS ≤1%, ΔP ≤0.3 W, mismo SCLK/MCLK.
- **En ninguno de los 6 brazos A/B se reprodujo el régimen E5** (25-31 W, MCLK ≥1250 sostenido, 74-92°C).

### Corrección
- La Mesa CUSTOM **NO reproduce el régimen E5 en arranque frío** con escenas disponibles.
- H8 (Mesa CUSTOM = causa del consumo E5): **NO CONFIRMADA** para arranque desde frío; se refuta como explicación por sí sola.
- El estado de E5 sigue requiriendo otro ingrediente (probablemente estado térmico previo de la sesión del 17/09 y/o empuje de MCLK que hoy no se dispara con escenas ligeras).

### Matiz importante (Regla del usuario)
> "No generalices que STOCK y CUSTOM son 'indistinguibles' para toda la RX 550 únicamente a partir de ΔFPS ≤1% y ΔP ≤0.3W en esos escenarios."

**Corrección registrada:** La indistinguibilidad es **solo para los 3 escenarios probados en EP-05** (A desktop, B jellyfish, C shading, 1080p, 15s). No se extiende a otros workloads, resoluciones, duraciones o estados térmicos.

---

## ERRATUM-004: Comparación de Métricas de Potencia Sin Etiquetado

### Problema Identificado
Múltiples informes compararon `power_avg_full` (ventana completa) con `power_avg_steady` (régimen estable) como si fueran la misma métrica.

### Ejemplos
- E-03 original: "power 13.40 W avg / 15.81 W max" (ventana completa)
- Régimen estable E-03: "power 15.75 W avg / 15.80 W max" (steady window)
- Estos valores se compararon sin etiquetar `NOT DIRECTLY COMPARABLE`

### Corrección
Todas las comparaciones históricas que mezclen definiciones deben revisarse y etiquetarse. Ver `METRICS-DEFINITIONS.md` para definiciones formales.

---

## ERRATUM-005: E1/E3 Muestrearon la iGPU

### Conclusión Original (O1-b, hipótesis)
> "E1/E3 muestrearon la tarjeta equivocada (iGPU Intel)."

### Nueva Evidencia (EP-08)
- Header E1: `ts,busy,freq_hz,power_uw,temp_mc,vram_used,gtt_used`
- `mem_info_vram_used` y `mem_info_gtt_used` existen **SOLO** en amdgpu card1. En card0 (i915) NO hay `mem_info_*` ni hwmon.
- Telemetría E1/E3 (freq 298-1029MHz, power ~25W, temp 75-79°C, vram/gtt) proviene de la **RX 550 real (amdgpu)**, NO de la iGPU.

### Corrección
- O1-b = **REFUTADA**.
- Los datos E1/E3 son de la RX 550 real.
- El régimen E1/E3 es un estado real de la tarjeta: cada run entra YA caliente (temp 76°C en primera muestra), SCLK nunca boostea, power clavada en 25W (cap) todo el run.

---

## Resumen de Cambios de Clasificación

| Conclusión Anterior | Nueva Clasificación | ERRATUM |
|---|---|---|
| "Kalm limitó a 25W" | **INVALIDADO** | 001 |
| "Cap 25W liga SCLK" | **INVALIDADO** | 001 |
| "25W = techo natural GPU" | **INVALIDADO** | 001 |
| "power1_input = potencia real" | **INVALIDADO** (es estimador SMU) | 002 |
| "Mesa CUSTOM causó E5" | **NO CONFIRMADA** / **INVALIDADA** | 003 |
| "E1/E3 midieron iGPU" | **REFUTADA** | 005 |
| "13.40 W ≈ 15.75 W comparables" | **INVALIDADO** (definiciones distintas) | 004 |

---

## Regla Anti-Sobrescritura
> "Cualquier futuro hallazgo que contradiga estas conclusiones se agregará como contradicción documentada, sin borrar estos registros." (DN-13)

Todos los errata se registran aquí; los informes originales (E1, E3, E5, EP-05, EP-06, EP-08, RESULTADOS-M1, FINAL-RESEARCH-STATUS) **no se modifican**. Las correcciones viven en este archivo y en `AUDIT-001.md`.