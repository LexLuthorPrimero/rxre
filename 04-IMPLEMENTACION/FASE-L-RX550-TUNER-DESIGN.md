# FASE L — RX550-TUNER — Documento de Diseño

> **Archivo:** `FASE-L-RX550-TUNER-DESIGN.md`
> **Fase:** FASE R-2 — COMPLETE PROJECT DOCUMENTATION & ECOSYSTEM ARCHITECTURE (R-2.11)
> **Fecha:** 2026-09-22 — Modo SOLO DOCUMENTAL (DISEÑO; NO implementado)
> **Clasificación:** [DISEÑADO]. Interviene sobre sysfs SOLO en corrida autorizada con frame de rollback.
> **Estado global:** **PLANIFICADA** (roadmap, dependiente de FASE K). No se escribió ni ejecutó nada.

---

## 1. OBJETIVO

Diseñar el **tuner de perfiles RX 550** (evolución de rx550-torneo) que experimenta de forma controlada
sobre PowerPlay/DPM (perfiles, límite de potencia, relojes) para **buscar configuraciones** con
sustento estadístico, con **ownership, state-machine, rollback, y verificación de cambio de estado**.
Regla fundamental heredada: **WRITE SUCCESS ≠ STATE CHANGE VERIFIED** — escribir el sysfs con éxito no
prueba que el estado del SMU cambió.

## 2. Alcance y límites

- **NO reemplaza rx550-torneo**: este es el MOTOR de búsqueda de perfiles (experimental); rx550-torneo
  es el tool de operación del régimen actual (perfiles balanced/locked/25W/experimental con `--danger`).
  FASE L EVALÚA y PROPONE; la adopción la decide la gobernanza del proyecto (R1-8 Capa Transversal).
- **Sin writes permanentes**: todos los cambios son temporales en sesión, con snapshot previo y restore
  al término, idéntico al patrón ya probado en M1/E4/E5/E5b (helper root con estado registrado).
- Selección estricta de GPU (vendor=0x1002 device=0x699F), identidad por PCI y readback del estado.

## 3. Elementos que toca (interfaz sysfs amdgpu)

| Elemento | Campo sysfs | Tipo |
|---|---|---|
| Perfil de gestión | `power_dpm_force_performance_level` (auto/high/low/manual) | fuerza o libera DPM |
| Límite de potencia | `power1_cap` (µW), respetado `power1_cap_max` | escribible temporalmente |
| Relojes SCLK/MCLK (manual) | `pp_dpm_sclk`, `pp_dpm_mclk` (por nivel) | fuerzan niveles (manual) |
| Modo de perfil GPU | `pp_power_profile_mode` (3D_FULL_SCREEN/VIDEO/COMPUTE/…) | perfil de curvas |
| Runtime PM | `power/control` de la GPU (on/auto) | puede suspender GPU headless |

## 4. Diseño del estado y ownership

### 4.1 State Machine (máquina de estados del tuner)
```
 IDLE ──(detect GPU)──> OWNED (adquirido el control del rango autorizado)
                         │ inventario: read-back completo (cap, dpm, pp_dpm_*, profile, state)
                         ▼
                  PLAN (define experimento A/B sobre K)
                         ▼
               SET (aplica cambio con snapshot previo del campo)
                 ├─(readback inmediato)─> VERIFY_STATE (¿el valor CAMBIÓ? leido de vuelta)
                 │        └─ no coincide ─> REVERT / FAIL_SAFE
                 ▼
              RUN (workload con runner K, telemetría)
                 ▼
              RESTORE (devolver TODOS los campos)
                 ├─(readback)─> VERIFY_RESTORED
                 └─ no coincide ─> REVERT_forzoso + alerta (bloquea nuevo experimento)
```

### 4.2 Identidad de hardware y capacidad
- **Hardware identity:** PCI `01:00.0 0300: 1002:699f` verificado ANTES de tocar nada (nunca asumir).
- **Capability detection:** leer `power1_cap_max`, `pp_dpm_sclk/mclk` para saber qué niveles existen
  antes de proponer; si un nivel no existe, no proponer.
- **No asumir estado:** Kalm se detecta en vivo (`pgrep`), el estado de runtime PM se lee, no se asume.

### 4.3 Verificación de cambio de estado
Tras cada `write sysfs`:
1. readback inmediato (2 lecturas con pausa).
2. comparar **valor** y (si aplica) el **efecto en relojes** (pp_dpm_state / perf).
3. si el valor de vuelta ≠ objetivo → **state change NO verificado** → marcar run INVALID y revertir;
   no interpretar jamás "write OK" como "state changed".

## 5. Perfiles de partida (vienen de rx550-torneo / M1 / E-series)

| Perfil | Params | Evidencia previa | Verificación necesaria |
|---|---|---|---|
| balanced (default) | cap 35 W, DPM auto | régimen operativo actual [VERIFICADO operacional] | readback baseline |
| locked | DPM high/manual con sclk/mclk forzados | E4 (high→peor a 25 W), E5b (manual sclk) | alternar y medir A/B |
| 25W | cap 25 W | régimen histórico 17/09 NO reproducible; hoy 25 W=techo | N/A hasta nuevo régimen |
| experimental | combos pp_power_profile_mode / cap / manual | diseño FASE I (I-3/I-5) | frame completo de rollback |

## 6. Ownership / Lock
- **Lock:** un archivo de bloqueo en `/run/lock` (flock) para que haya un solo tuner activo; cualquier
  otra hernapiente de control (rx550-torneo, kalm, CoreCtrl si existiera) se detecta y NO se solapan
  writes (protocolo ownership de la Capa Transversal R1-8).
- **Protocolo GPU Ownership:** detectar→verificar→adquirir→experimentar→restaurar→liberar→verificar.

## 7. Recuperación ante fallo (Failsafe)

| Fallo | Detección | Acción |
|---|---|---|
| write falla (permission/EWOULDBLOCK) | readback ≠ target 2 lecturas | abort, restaurar snapshot, log FAIL_SAFE |
| proceso muere | manejador de señales + journal | restore forzado al salir |
| device lost / reboot | post_fail de estado perdido | reintento con estado inicial registrado; nunca escribir sin readback previo |
| thermal risk (temp > 90 °C) | telemetría continua | abort inmediato del workload (regla de seguridad) |
| lock no adquirible | O_EXCL fail | no ejecutar (espera) |

## 8. Benchmarks y A/B (con el Lab K)
- Usa el runner K (workload sintético + game/N/A) con N≥5 pareadas intercaladas; criterios de validación
  A/B idénticos a M1 (IC95%, hashes).
- Los resultados alimentan la **búsqueda controlada**: barrido de perfiles → ranking estadístico →
  recomendación a gobernanza; nunca activación automática.

## 9. Conclusión del diseño
FASE L queda **DISEÑADA** (state machine, ownership, verification, rollback, failsafe). Depende de:
FASE K (runner/validación), FASE I (interfaces/experimentos PowerPlay), y de la autorización de writes
solo dentro del frame (snapshot+readback+restore). **rx550-torneo sigue siendo la herramienta operativa;
FASE L no la toca ni la reemplaza automáticamente. Ningún cambio de estado fue ejecutado o verificable
en esta fase (read-only).**