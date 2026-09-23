# EXPERIMENT-PRIORITY-MATRIX — Matriz de Prioridad (FASE J)

> **Archivo:** `EXPERIMENT-PRIORITY-MATRIX.md`
> **Fase:** FASE R-2 — COMPLETE PROJECT DOCUMENTATION & ECOSYSTEM ARCHITECTURE (R-2.8)
> **Fecha:** 2026-09-22 — Modo SOLO DOCUMENTAL (DISEÑO; NO ejecutado)
> **Clasificación:** [DISEÑADO] — priorización de candidatos con justificación por evidencia.
> **Regla:** la matriz ordena por **interés/dependencia/riesgo** para planificar la ejecución FASE E–J;
> NO existe un "mejor experimento" sin justificación.

---

## 0. Criterios de puntuación (escala 1-3; 3 = mejor/positivo)

| Criterio | 3 | 2 | 1 |
|---|---|---|---|
| **Valor informativo** | discrimina una hipótesis abierta crítica (MASTER-RESEARCH-STATUS DESCONOCIDO/ALTA) | aporte parcial, mide un secundario | mide algo ya sabido |
| **Dependencias** | ejecutable hoy read-only | necesita workload/lab que existe o es pequeño | necesita autorización/escritura/otra fase |
| **Riesgo** (invertido: 3=bajo) | read-only o write reversible testado | write reversible en corrida con frame | write congelado / riesgo HW/térmico/rollback dudoso |
| **Reversibilidad** | sin cambio residual | cambio temporal con restore verificado | requiere blob/pptable/reboot |
| **Reproducibilidad** | carga determinista/sintética | determinista con warm-up largo | dependiente de entorno (juego, sesión) |
| **Coste** (3=bajo) | minutos read-only | horas con workload existente | instalación/autorización/ejecución compleja |
| **Calidad de métricas** | telemetría directa (FPS/frametime/power/reloj) + registro completo | proxy (mem_busy, busy%) | métrica indirecta con confounders fuertes |
| **Evidencia previa** | ya hay señal direccional local (FASE D/E3/R-15) | señal débil o externa | sin señal |
| **Capacidad discriminativa** | puede CONFIRMAR/REFUTAR Hipótesis activa | discrimina sub-hipótesis | solo correlacional |
| **Riesgo de confounders** (3=limpio) | pocos confounders controlables | confounders gestionables | confounders dominantes |

---

## 1. Candidatos (de FASE E/F/G/H/I + POLARIS12-MAP)

| ID | Nombre | Valor info | Depend | Riesgo | Rev. | Repro | Coste | Métrica | Evid | Discr | Conf | Total | Prioridad |
|---|---|---|---|---|---|---|---|---|---|---|---|---|---|
| **G-M5** | fetch-latency = camino GTT? | 3 | 2 | 3 | 3 | 3 | 2 | 3 | 3 | 3 | 2 | **27** | **ALTA** |
| **G-M1** | mapa camino buffers sintéticos | 3 | 2 | 3 | 3 | 3 | 3 | 2 | 2 | 2 | 2 | **25** | **ALTA** |
| **GEO-01** | Vertex Throughput | 3 | 2 | 3 | 3 | 3 | 2 | 2 | 3 | 3 | 2 | **26** | **ALTA** |
| **GEO-02** | Primitive Throughput | 3 | 2 | 3 | 3 | 3 | 2 | 2 | 3 | 3 | 2 | **26** | **ALTA** |
| **GEO-05** | Prim small overdraw | 2 | 2 | 3 | 3 | 3 | 2 | 2 | 3 | 2 | 2 | **24** | **ALTA** |
| **GEO-07** | Geometric overdraw depth/early-Z | 2 | 2 | 3 | 3 | 3 | 2 | 2 | 3 | 2 | 2 | **24** | **ALTA** |
| **I-1** | Registro curva DPM read-only | 2 | 3 | 3 | 3 | 3 | 3 | 2 | 2 | 2 | 3 | **26** | **ALTA** |
| **F2-replica(realocado)** | ratio frametime/fetch QTY (sintético, ya medido) | 1 | 3 | 3 | 3 | 3 | 3 | 3 | 3 | 1 | 2 | **25** | **MEDIA** (ya resuelto, reusable) |
| **G-M2 (MEM-02)** | DEVICE_LOCAL vs HOST_VISIBLE | 3 | 1 | 3 | 3 | 3 | 2 | 2 | 2 | 3 | 2 | **24** | **MEDIA** |
| **G-M4** | mem_busy ↔ BW | 2 | 2 | 3 | 3 | 3 | 2 | 2 | 2 | 2 | 2 | **23** | **MEDIA** |
| **GEO-03** | Index/VBO bandwidth | 2 | 2 | 2 | 3 | 3 | 2 | 2 | 2 | 2 | 1 | **21** | **MEDIA** |
| **GEO-04** | Instancing | 2 | 2 | 3 | 3 | 3 | 2 | 2 | 2 | 2 | 2 | **23** | **MEDIA** |
| **GEO-06** | Large tris viewport cull | 1 | 2 | 3 | 3 | 3 | 3 | 2 | 1 | 2 | 2 | **22** | **MEDIA** |
| **GEO-08** | VS+FS balance | 2 | 2 | 3 | 3 | 3 | 2 | 2 | 2 | 2 | 1 | **22** | **MEDIA** |
| **G-M3 (MEM-01)** | VRAM pressure/eviction | 3 | 1 | 1 | 2 | 2 | 1 | 3 | 2 | 3 | 2 | **20** | **BAJA**(riesgo OOM alto) |
| **I-2** | MCLK threshold probing | 2 | 1 | 1 | 2 | 3 | 1 | 3 | 3 | 2 | 2 | **20** | **BAJA** |
| **I-3** | Power profile mode write | 2 | 1 | 2 | 3 | 3 | 2 | 2 | 2 | 2 | 2 | **21** | **BAJA** (requiere L) |
| **I-4** | Runtime PM | 1 | 2 | 2 | 2 | 2 | 2 | 2 | 1 | 1 | 2 | **17** | **BAJA** |
| **I-5** | ppfeaturemask lectura/audit | 2 | 3 | 3 | 3 | 3 | 3 | 2 | 2 | 1 | 3 | **25** | **ALTA** (ya en L.0/R1-8) |
| **FASE E** | Real-game baseline | 3 | 1 | 1 | 2 | 2 | 1 | 2 | 3 | 3 | 1 | **19** | **BLOQUEADO** (sin juego autorizado) |
| **PWR-02/03 FASE D et3/contadores** | writes/contadores GFX8 | 3 | 2 | 1 | 1 | 3 | 1 | 3 | 3 | 3 | 1 | **21** | **BLOQUEADO** (NO autorizado/CONGELADO) |

---

## 2. Salida consolidada

| Prioridad | Candidatos | Justificación sintética |
|---|---|---|
| **ALTA** | G-M5, G-M1, GEO-01, GEO-02, GEO-05, GEO-07, I-1, I-5 (L.0) | read-only, refrendados por señal local (fetch-latency, overdraw, DPM), máxima capacidad discriminatoria sobre hipótesis activas |
| **MEDIA** | F2-replica, G-M2, G-M4, GEO-03, GEO-04, GEO-06, GEO-08 | aportan o necesitan el Lab K/workload, confounders algo mayores |
| **BAJA** | G-M3, I-2, I-3, I-4 | requieren writes / autorización / riesgo OOM-térmico sin señal local fuerte para justificarlo ahora |
| **BLOQUEADO** | FASE E (sin juego reproducible autorizado), PWR-02/03 y FASE D etapa 3/contadores (NO autorizados), profile/writes sin frame L | dependen de autorización, CONGELADO, o de decisiones de seguridad |

## 3. Notas de gobernanza
- El **primero en ejecutarse** debería ser un **read-only ALTA** (GEO-01/02 o G-M5) — no porque sea "el
  mejor", sino porque desbloquea las piezas de FASE F/G con mínimo coste y riesgo.
- **No se descarta ningún candidato**: los BAJA/BLOQUEADO se re-evalúan si cambia la autorización o el estado.
- Los escritos (I-3, I-4, PWR-*) **no pueden ejecutarse fuera de FASE L** con su frame (snapshot+rollback).