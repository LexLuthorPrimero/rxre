# ORQUESTADOR FINAL — Documento de Diseño del Proyecto

> **Archivo:** `projects/ORCHESTRATOR/FINAL-ORCHESTRATOR-DESIGN.md`
> **Fase:** FASE R-2 — COMPLETE PROJECT DOCUMENTATION & ECOSYSTEM ARCHITECTURE (R-2.17)
> **Fecha:** 2026-09-22 — Modo SOLO DOCUMENTAL (DISEÑO; NO implementado)
> **Clasificación:** [DISEÑADO] — arquitectura de control del ecosistema. NO se ejecutó ni se escribió
> código.
> **Relación:** es la integración de K (lab) + L (tuner) + M (contadores) + O (gestores) + Q (Mesa).

---

## 1. OBJETIVO

Diseñar el **Orquestador Final**, la capa que coordina todo el ecosistema: selección de workload,
telemetría, benchmark, tuner (control), investigación de contadores, runner de experimentos, validación,
rollback, almacenamiento de artefactos, base de datos de resultados y motor de decisión. **Su autoridad
sobre hardware es CERO salvo mediada por el tuner autorizado.**

## 2. SAFETY BOUNDARY (frontera de seguridad — pieza central)

```
 OBSERVACIÓN (read-only): telemetría, catalogos, mapas, diagnóstico
     │  (sin escritura; solo lecturas sysfs/perf)
     ▼
 EXPERIMENTACIÓN: ejecuta workloads + recoge datos (runner K, validación, hashing)
     │  (sin cambios de estado HW; los cambios se solicitan al tuner)
     ▼
 MODIFICACIÓN DEL SISTEMA: ÚNICO punto capaz de escribir sysfs/control = RX550-Tuner (FASE L)
     │  (autorización + snapshot + readback + restore + lock)
     ▼
 ROLLBACK / DECISIÓN
```

Reglas:
- El Orquestador **nunca** escribe sysfs por su cuenta; envía *comandos* al tuner, que aplica el cambio
  dentro de su state machine verificada.
- Cualquier escritura por otra vía (CoreCtrl, scripts, usuario) se detecta (ownership) y bloquea la
  ejecución de experimentos (protocolo GPU Ownership, R1-8).
- Leer nunca modifica estado (JUST read).

## 3. MODULOS INTEGRADOS

| Módulo | Uso | Fuente |
|---|---|---|
| **Runner** | ejecutar una celda de experimento (workload+telemetría+metadata+validación) | FASE K (K2/estructura RUN) |
| **Selection** | elegir workload (sintético/game-E/superposition) y parámetros según hipótesis | FASE E/F/G + matriz J |
| **Telemetry collector** | recolectar y validar telemetría (schema K1) | K1 + PolarisTelemetry |
| **Benchmark set** | definir suites completas (PolarisBench) | K |
| **Tuner control** | administrar peticiones de cambio de estado al RX550-Tuner | FASE L |
| **Counter research window** | solicitar a FASE M/PolarisLens datos de contadores cuando autorizado | FASE M |
| **Validation** | validar runs (K6) y estados (L) | K6/L |
| **Rollback** | ejecutar protocolo de restauración ante cualquier fallo del tuner | L §7 |
| **Artifact storage** | almacenar `runs/` con hashes, indices | K3/K10 |
| **Results DB** | base de resultados: métricas, validación, comparativa A/B | K (result.json) |
| **Decision engine** | sugerir siguientes pasos (ranking IC95% → gobernanza) | K/Escuela J |

## 4. FLUJO DE ERRORES (diseñado)
1. error de telemetría/device lost → run INVALID → NUNCA se acumula como dato válido.
2. fallo de state → tuner fuerza restore → bloquea siguiente run (fail-safe).
3. si un cambio no se verifica (WRITE SUCCESS ≠ STATE CHANGE VERIFIED) → abort + candidato a lista negra

## 5. ESTADO DEL ARTEFACTO (solo lectura)
- Registra en `state/` el estado actual (cap, dpm, perfil, lock) para que cualquier herramienta externa
  lo vea; el Orquestador es el rostro de "estado único" del ecosistema.

## 6. SIN AUTORIDAD DE HARDWARE
El Orquestador **no posee** la BANY de hardware: su "ownership" es solo el **lock de experimentación**,
mientras que el **lock de escritura** sigue siendo exclusivo del tuner. Sin el tuner autorizado, el
Orquestador es un runner read-only.

## 7. DEPENDENCIAS
K (lab runner) → base; L (tuner) para cualquier cambio; M (contadores) para un modo avanzado; O (FASE O)
para hoja de ruta de gestores externos; Q para observaciones de Mesa. Sin K no hay orquestador real.

## 8. CONCLUSIÓN DEL DISEÑO
El Orquestador Final queda **DISEÑADO** en arquitectura (módulos, SAFETY BOUNDARY, flujo de errores,
estado), pero es **NO implementado** y **dependiente** de que el Lab K y el tuner L existan (futuro).
**No se escribió ni ejecutó nada; no tiene autoridad de hardware por diseño.**