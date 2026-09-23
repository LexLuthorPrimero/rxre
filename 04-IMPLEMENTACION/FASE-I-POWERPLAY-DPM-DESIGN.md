# FASE I — POWERPLAY / DPM — Documento de Diseño

> **Archivo:** `FASE-I-POWERPLAY-DPM-DESIGN.md`
> **Fase:** FASE R-2 — COMPLETE PROJECT DOCUMENTATION & ECOSYSTEM ARCHITECTURE (R-2.7)
> **Fecha:** 2026-09-22 — Modo SOLO DOCUMENTAL (DISEÑO; NO ejecutado)
> **Clasificación:** [DISEÑADO]; políticas externas tomadas de `R0-2-POWERPLAY-MCLK-SMU7.md` [VERIFICADO].
> **Estado global:** **PENDIENTE**. **Toda escritura sysfs/PowerPlay sigue NO AUTORIZADA** excepto en
> corrida autorizada con snapshot+readback+restore (regla MASTER-RESEARCH-STATUS y NO HACER #1).

---

## 1. Objetivo

Diseñar la caracterización de **comportamiento PowerPlay/DPM** de Polaris12 (RX 550) en la pila Linux
actual (amdgpu/SMU7), para (a) explicar el comportamiento observado de SCLK/MCLK/power, (b) preparar el
terreno de FASE L (RX550-Tuner) y (c) saber qué interfaces existen y qué riesgo tiene cada una.

## 2. Separación estricta de categorías

| Categoría | Qué es | Qué se hace en esta fase |
|---|---|---|
| **A. DOCUMENTACIÓN EXTERNA** | whitepaper/página AMD, documentación kernel sysfs | Leída y citada (R0-1..R0-6/R0-2) |
| **B. EVIDENCIA LOCAL** | valores observados read-only en este sistema | Ya recolectados (MASTER-RESEARCH-STATUS, E-series, FASE D) |
| **C. CAPACIDAD DEL KERNEL ACTUAL** | qué interfaces existen y su semántica (documentada/código) | Analizada (R0-2; N de lectura local de código aún pendiente) |
| **D. VERIFICADA** | interfaces que se comprueban funcionando sin romper nada | Leer bitácoras existentes (ej. pp_dpm_state, DPM levels) |
| **E. CAMBIOS REVERSIBLES** | writes con snapshot+readback+restore | SOLO con autorización explícita (FASE L/L.0 Capability Audit R1-8) |
| **F. ALTO RIESGO** | ppfeaturemask, pp_table, VBIOS, reboot /no runtime | Bloqueado (CONGELADO) |

## 3. Interfaces documentadas (inventario de capabilities)

| Interface | Función | Riesgo | Estado autorización |
|---|---|---|---|
| `power1_cap` (µW) y `power1_cap_max` | límite de potencia (actual 35 W) | MEDIO (perf) | write SOLO autorizado en corrida; actual 35 W sin escribir en sesión |
| `power_dpm_force_performance_level` | `auto`/`high`/`low`/`manual` | MEDIO (SCLK/MCLK) | write autorizado temporal (M1: solo auto/LOW/high test). Uso manual = FASE L |
| `pp_dpm_sclk` / `pp_dpm_mclk` | lista y forzado de niveles (manual) | MEDIO | FASE L / experimentos específicos autorizados |
| `pp_power_profile_mode` | modos 3D_FULL_SCREEN/VIDEO/COMPUTE/CUSTOM | MEDIO | FASE L |
| `ppfeaturemask` (0xfff7bfff actual) | máscara de features PowerPlay (SMU) | **ALTO** (ROM/SMU) | **CONGELADO** — no escribir |
| `pp_od_clk_voltage` | overdrive | **ALTO** | **CONGELADO** |
| `pp_table` / VBIOS | reprogramar SMU | **ALTO** | **CONGELADO** |
| runtime PM (`power/control`, `autosuspend_delay_ms`) | suspensión ida/vuelta del GPU | MEDIO (device) | FASE L/O (evaluado, no cambiado) |

## 4. Comportamientos a explicar (evidencia local registrada)

- **E3/E5/E5b:** cap 25 W atrapa SCLK en 330-535 de 1071; con cap 35 W alcanza 600-750 (régimen térmico)
  → el techo es el presupuesto de potencia (proximal), no señal térmica.
- **R0-2 (kernel):** MCLK de Polaris12 (bus 128-bit) usa `up_hyst=5 / down_hyst=16 / activity=20`
  (gate `chip_id >= CHIP_POLARIS10`) → MCLK 1500 solo con actividad sostenida (~20 %).
- **R-15 (Superposition):** MCLK 300→1500 con presión real de memoria; sintéticos quedan en 625 tras
  picos transitorios.
- **MCLK policy R-07/R0-2:** comportamiento esperado coherente con lo medido (rumbo para no atribuir a
  "bug" lo que es política DPM).

## 5. Experimentos diseñados (FASE I/L)

### I-1: Registro de curva DPM (read-only)
- Leer `pp_dpm_sclk`, `pp_dpm_mclk`, `power_dpm_force_performance_level`, `pp_power_profile_mode` y
  `power1_cap` en cada corrida (ya es el estándar; aquí se sistematiza en tabla por workload).
- **Métrica:** distribución de SCLK/MCLK por workload (sintético vs Superposition vs meta-game).

### I-2: MCLK threshold probing (diseñado, requiere autorización)
- Serie de workloads con actividad de MCLK creciente (G-M4 lo acerca) y lectura de los niveles activos
  (pp_dpm_state). **Sin writes**: solo observar cuándo aparece 1500 en `auto`.
- **Si alguno requiere escribir** → convertir en FASE L/experimentos con snapshot.

### I-3: Power profile mode (write temporal, FASE L)
- Aplicar `POWER_SAVING`/`VIDEO`/`COMPUTE` (perfiles no-3D) en corrida autorizada de una carga fija y medir
  SCLK/MCLK/power/frametime. Criterio de resultado: ¿cambia la curva para SCLK/MCLK?

### I-4: Runtime PM (evaluado documentalmente, cambia solo con autorización)
- Comparar `power/control` actual (si es `on`) vs `auto` en el registro dir. Si está en `auto`, detectar
  si el GPU entra en suspensión entre corridas (appstart/stutter) — observación read-only probable.

### I-5: ppfeaturemask VERIFICACIÓN SOLO LECTURA (L.0 Capability Audit — R1-8)
- Registrar la máscara actual (0xfff7bfff) y los features asociados en docs; **no escribir**.
- Documentar qué features están off en la máscara y qué significaría habilitarlos → clasificar como
  alto-riesgo para FASE L (a evaluar, no a ejecutar).

## 6. Interacción
- Abastece la **Matriz J** (R-2.8) con el perfil de riesgo/reversibilidad de cada candadato de PowerPlay.
- FASE L (RX550-Tuner) ejecutará los writes **solo** con el frame de autorización y rollback; FASE I se
  mantiene read-only.
- Capa Transversal (R1-8) ya definió L.0 (ppfeaturemask), la identidad de hardware y la Capability Matrix:
  FASE I la mantiene viva sin ejecutar nada.

## 7. Conclusión del diseño
FASE I queda **DISEÑADA** y **PENDIENTE**: 5 experimentos (I-1.read-only, I-2..I-5.requieren
autorización/ejecución FASE L). La política MCLK 5/16/20 (R0-2, [VERIFICADO]) se integra como
**conocimiento explicativo** (no como cambio). **Ninguna escritura de PowerPlay se ejecutó ni se
ejecutará sin la autorización y el frame de rollback de FASE L.**